# Copyright 2016 Matteo Franchin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
Module responsible of prioritising and carrying out the creation of thumbnails.

The work is carried out by the Orchestrator object, which collects requests
for thumbnail generation and sends them to a separate process. The work is
prioritised such that the last thumbnail request is carried out first.
'''

import os
from threading import Thread
from multiprocessing import Process, Queue
from collections import namedtuple
from Queue import Empty

from .backcaller import BackCaller
from .thumbnailers import build_image_thumbnail, build_directory_thumbnail

def comment(s): pass

# State returned after a thumbnail request.
(THUMBNAIL_LOADING,
 THUMBNAIL_DAMAGED,
 THUMBNAIL_DONE) = range(3)

class Thumbnail(object):
    def __init__(self, file_name, size, state, request_id, data=None):
        self.file_name = file_name
        self.size = size
        self.state = state
        self.request_id = request_id
        self.data = data

    def match(self, size):
        # TODO: For now we tolerate slight errors in the resize.
        return size[0] == self.size[0] or size[1] == self.size[1]

class Worker(Process):
    def __init__(self, cmd_queue, out_queue):
        self.cmd_queue = cmd_queue
        self.out_queue = out_queue
        self.local_queue = []
        self.idx_from_req = {}
        super(Worker, self).__init__()

    def run(self):
        '''The main worker loop.'''

        while True:
            # Move all items from cmd_queu to local queue.
            # Block during get if the local queue is empty.
            comment('Move work to local queue')
            if self.move_work_to_local_queue():
                self.out_queue.put(('STOP',))
                return

            # Now process at most one command from the local queue.
            if len(self.local_queue) > 0:
                self.process_item_from_local_queue()

    def move_work_to_local_queue(self):
        '''Move all commands to the local queue (in reverse order).

        Also handle the queue management commands (CLEARQ, ...).
        Return whether the worker process should terminate as a result of
        a STOP command.
        '''

        local_queue = self.local_queue
        idx_from_req = self.idx_from_req
        while True:
            # If the local queue is empty, then block the get() on cmd_queue,
            # as there is no work we could do anyway.
            block = (len(local_queue) == 0)

            try:
                args = self.cmd_queue.get(block)
            except Empty:
                return False
            else:
                cmd  = args[0]
                if cmd == 'STOP':
                    # Exit the worker process.
                    return True
                if cmd == 'CLEARQ':
                    # Clear all jobs queued before this command.
                    self.local_queue = local_queue = []
                    self.idx_from_req = idx_from_req = {}
                elif cmd == 'CANCEL':
                    # Cancel a MAKETHUMB command in the queue.
                    request_id = args[1]
                    idx = idx_from_req.get(request_id)
                    if idx is not None:
                        local_queue[idx] = ('NOP',)
                    else:
                        comment('CANCEL: Cannot find request {}'
                                .format(request_id))
                else:
                    assert cmd == 'MAKETHUMB', 'Unknown command {}'.format(cmd)
                    # Queue the MAKETHUMB command in the local queue. The
                    # order is reversed (most recent request are dealt with
                    # first).
                    request_id = args[1]
                    idx_from_req[request_id] = len(local_queue)
                    local_queue.append(args)

    def process_item_from_local_queue(self):
        '''Process one item in the local queue and remove it.'''

        # Remove the top command from local_queue and idx_from_req map.
        # NOP commands are removed and ignored.
        while len(self.local_queue) > 0:
            idx_from_req = self.idx_from_req
            args = self.local_queue.pop()
            if args[0] != 'NOP':
                assert args[0] == 'MAKETHUMB'
                request_id, file_name, size = args[1:]
                self.idx_from_req.pop(request_id)

                comment('Received MAKETHUMB command with ID {}'
                        .format(request_id))
                state, data = self.make_thumb(file_name, size)

                comment('MAKETHUMB processed: sending result')
                self.out_queue.put(('MAKETHUMB', file_name, size, request_id,
                                    state, data))
                return

    def make_thumb(self, file_name, size):
        if os.path.isdir(file_name):
            arr = build_directory_thumbnail(file_name, size)
        else:
            arr = build_image_thumbnail(file_name, size)
        state = (THUMBNAIL_DONE if arr is not None else THUMBNAIL_DAMAGED)
        return (state, arr)

def listener_main(orchestrator):
    '''Listener thread main loop.

    The listener thread is responsible for taking the thumbnails produced by
    the worker process and putting them back into the orchestrator thumbnail
    cache (by calling Orchestrator.thumbnail_read()).
    '''

    while True:
        args = orchestrator.out_queue.get()
        out_item = args[0]
        if out_item == 'STOP':
            return
        if out_item == 'MAKETHUMB':
            orchestrator.thumbnail_ready(*args[1:])
        else:
            raise ValueError('Listener received unknown output: {}'
                             .format(out_item))

class Orchestrator(BackCaller):
    def __init__(self, soft_limit=500, hard_limit=550):
        super(Orchestrator, self).__init__(thumbnail_available=None)
        self.thumbnails = {}
        self.request_id = 0
        self.thumbnail_soft_limit = soft_limit
        self.thumbnail_hard_limit = hard_limit
        self.cmd_queue = Queue()
        self.out_queue = Queue()

        # Separate process doing all the hard work.
        self.worker = Worker(self.cmd_queue, self.out_queue)
        self.worker.daemon = True
        self.worker.start()

        # Thread listening to out_queue and calling back when items are
        # available.
        self.out_listener = t = Thread(target=listener_main, args=(self,))
        t.daemon = True
        t.start()

    def request_thumbnail(self, file_name, size):
        '''Request a thumbnail with the given size in a non-blocking way.'''

        comment('Request thumbnail {} with size {}'.format(file_name, size))
        tn = self.thumbnails.get(file_name)
        if tn is not None:
            # A thumbnail already exists. Unless it has the wrong size return
            # this.
            if tn.state == THUMBNAIL_DAMAGED or tn.match(size):
            #    (tn.state == THUMBNAIL_DONE and tn.size == size)):
                comment('Returning cached thumbnail')
                return tn

            # If tn.state == THUMBNAIL_LOADING we re-submit the command to
            # ensure it gets a higher priority over the other requests.
            # This is important to ensure we render first the area of the
            # screen the user is looking at.
            self.cmd_queue.put(('CANCEL', tn.request_id))
            comment('Replacing thumbnail {} != {}'.format(size, tn.size))
        else:
            if len(self.thumbnails) >= self.thumbnail_hard_limit:
                comment('Too many thumbnails ({}): removing old thumbnails...'
                        .format(len(self.thumbnails)))
                all_tns = [(tn.file_name, tn.request_id)
                           for tn in self.thumbnails.itervalues()]
                all_tns.sort(lambda a, b: cmp(b[1], a[1]))
                for file_name_to_remove, _ in \
                  all_tns[self.thumbnail_soft_limit:]:
                    comment('Rm thumb {}'.format(file_name_to_remove))
                    self.thumbnails.pop(file_name_to_remove)

        # Create or replace the thumbnail.
        comment('Storing LOADING-thumbnail for {}'.format(file_name))
        request_id = self.request_id
        self.request_id += 1
        self.thumbnails[file_name] = tn = \
          Thumbnail(file_name, size, THUMBNAIL_LOADING, request_id)

        # Send a request for the thumbnail.
        comment('Queuing MAKETHUMB command, request {}'.format(request_id))
        self.cmd_queue.put(('MAKETHUMB', request_id, file_name, size))
        return tn

    def thumbnail_ready(self, file_name, size, request_id, state, data=None):
        '''Internal. Used to provide thumbnail data, once it ready.'''

        tn = self.thumbnails.get(file_name)
        if tn is None:
            comment('Received thumbnail for unknown request {}'
                    .format(request_id))
            return
        if request_id != tn.request_id:
            comment('request_id {} != {} for {}'
                    .format(request_id, tn.request_id, file_name))
            if size != tn.size:
                comment('Size mismatch: discarding thumbnail')
                return

        comment('Accepting thumbnail for {}'.format(file_name))
        tn.state = state
        tn.data = data

        # Alert that a new thumbnail is now available.
        self.call('thumbnail_available', file_name, size, state, data)

    def clear_queue(self):
        '''Abort all the work in progress and clear the queue.'''

        # Need to remove LOADING-thumbnails from the cache.
        tn_to_remove = [tn.file_name for tn in self.thumbnails.itervalues()
                        if tn.state == THUMBNAIL_LOADING]
        for tn in tn_to_remove:
            self.thumbnails.pop(tn)

        self.cmd_queue.put(('CLEARQ',))

if __name__ == '__main__':
    import time

    def got_it(*args):
        print('Got it ' + ', '.join(map(str, args)))

    t = Orchestrator()
    t.set_callback('thumbnail_available', got_it)
    t.request_thumbnail('/tmp/image00.jpg', (100, 100))
    t.request_thumbnail('/tmp/image01.jpg', (100, 100))
    t.request_thumbnail('/tmp/image02.jpg', (100, 100))
    t.request_thumbnail('/tmp/image00.jpg', (100, 100))
    time.sleep(10)
