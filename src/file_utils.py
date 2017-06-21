# Copyright 2016, 2017 Matteo Franchin
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

'''Generic utility for file sorting.'''

import os
from collections import deque


class FileListItem(object):
    def __init__(self, index, is_dir, dir_path, name):
        self.index = index
        self.is_dir = is_dir
        self.dir_path = dir_path
        self.name = name
        self.full_path = os.path.join(dir_path, name)


class FileList(object):
    (SORT_BY_FILE_NAME,
     SORT_BY_MOD_DATE,
     SORT_BY_FILE_EXT,
     SORT_BY_FILE_SIZE,
     SORT_BY_IS_DIR) = range(5)

    @classmethod
    def build_key_generator(cls, sort_types, case_sensitive=False):
        adj = ((lambda x: x) if case_sensitive else (lambda x: x.lower()))

        gns = []
        for sort_type in sort_types:
            if sort_type == cls.SORT_BY_FILE_NAME:
                gn = lambda is_dir, fn: adj(os.path.split(fn)[-1])
            elif sort_type == cls.SORT_BY_FILE_EXT:
                gn = lambda is_dir, fn: adj(os.path.splitext(fn)[-1])
            elif sort_type == cls.SORT_BY_MOD_DATE:
                gn = lambda is_dir, fn: os.path.getmtime(fn)
            elif sort_type == cls.SORT_BY_FILE_SIZE:
                gn = lambda is_dir, fn: os.path.getsize(fn)
            elif sort_type == cls.SORT_BY_IS_DIR:
                gn = lambda is_dir, fn: (0 if is_dir else 1)
            else:
                continue
            gns.append(gn)

        def key_generator(item):
            return tuple(gn(*item) for gn in gns)
        return key_generator

    def __init__(self, dir_path, **kwargs):
        self.callbacks = []
        self.full_path = dir_path = os.path.realpath(dir_path)
        self.file_items = items = []
        for i, args in enumerate(get_files_in_dir(dir_path, **kwargs)):
            is_dir, name = args
            items.append(FileListItem(i, is_dir, dir_path, name))

    def __iter__(self):
        return iter(self.file_items)

    def __len__(self):
        return len(self.file_items)

    def __getitem__(self, idx):
        return self.file_items[idx]

    def register_callback(self, update_callback):
        self.callbacks.append(update_callback)


image_file_extensions = ('.jpeg', '.jpg', '.png', '.tif', '.xpm', '.bmp')

def list_dir(directory_path, check_cancelled=None):
    '''Return the files in the directory or an empty list if the directory
    access fails.'''

    if check_cancelled is not None and check_cancelled():
        return []

    assert isinstance(directory_path, str)
    try:
        entries = os.listdir(directory_path)
    except Exception as x:
        return []
    return [os.path.join(directory_path, entry) for entry in entries]

def get_files_in_dir(directory_path, check_cancelled=None, **kwargs):
    '''Return tuples (isdir, full_path) where isdir is a boolean indicating
    whether the item is a directory and full_path is the path to it.
    The following keyword arguments can be used:

    `file_extensions`: list of extensions of files to consider. Files with
      different extension are ignored.

    `sort_type`: how the files are sorted. Can be FileList.SORT_BY_FILE_NAME
      or another value of the same enumeration.

    `reversed_sort`: whether the sort order should be reversed. Default order
      is from smaller to bigger.

    `out`: dict-like object. Of provided, this is populated with extra
      statistics from the search. The following fields are written:
      out['num_skipped'] number of files ignored due to their extension.
    '''
    return categorize_files(list_dir(directory_path, check_cancelled), **kwargs)

def is_hidden(full_path):
    '''Whether the given file is hidden.'''
    return os.path.split(full_path)[-1].startswith('.')

def categorize_files(file_list, file_extensions=None, sort_type=None,
                     reversed_sort=False, show_hidden_files=True, out=None):
    '''Similar to get_files_in_dir, but uses the files in the list given as
    first argument, rather than obtaining the file list from a directory path.
    '''

    exts = file_extensions or image_file_extensions
    isdir_file_tuples = []
    num_skipped = 0
    for full_path in file_list:
        if not show_hidden_files and is_hidden(full_path):
            continue

        if not os.path.exists(full_path):
            num_skipped += 1
            continue

        isdir = os.path.isdir(full_path)
        if not isdir:
            ext = os.path.splitext(full_path)[1]
            if ext.lower() not in exts:
                num_skipped += 1
                continue
        isdir_file_tuples.append((isdir, full_path))

    # Return extra output if required.
    if out is not None:
        out['num_skipped'] = num_skipped

    # For now we only provide one sort type. Later we may want to provide a
    # tuple of sort types from the one which has the higher precedence to the
    # one which has the lowest precedence. Infrastructure for this is already
    # in place. Here we map the single sort order to a tuple which makes
    # sense.
    if sort_type is not None:
        if sort_type == FileList.SORT_BY_FILE_NAME:
            sort_types = (sort_type,)
        else:
            sort_types = (sort_type, FileList.SORT_BY_FILE_NAME)

        key = FileList.build_key_generator(sort_types)
        isdir_file_tuples.sort(key=key, reverse=reversed_sort)
    return isdir_file_tuples

def sparse_iterator(items, num_steps):
    '''Sparse iteration over `items`. Every element of the list `items` is
    returned exactly once, but with a different order which can be tweaked by
    changing `num_steps`. The i-th invocation of the iterator roughly returns
    items[i*len(items)//num_steps].
    '''
    assert num_steps >= 1
    items = list(items)
    idx = 0
    while items:
        if idx >= len(items):
            idx = idx % len(items)
        yield items[idx]
        items.pop(idx)
        idx += len(items) // num_steps


def pick_files(path, num_picks=4, follow_links=False,
               dig_stability=2, dig_strength=10, **kwargs):
    '''Traverse the `path` and its subdirectories with the aim of picking
    `num_picks` files as sparsely as possible. `follow_links` decides whether
    symlinks should be followed or ignored in the directory traversal.
    Keyword arguments in `kwargs` are passed to `get_files_in_dir` and can
    be used to restrict the file extensions, provide a cancel check, decide
    the sort order or decide whether hidden files should be ignored or not.

    `dig_strength` determines how deep the search for images should be. A big
    value (e.g. 15 or 20) causes the function to search deep into the
    subdirectories, even when the parent directories contain files which are
    not images. A small value (e.g. 2 or 5) causes the function to stop when
    looking into directories that contain mostly files that are not images.
    `dig_stability` decides how stable the directory evaluation should be.
    When this is zero a directory containing many subdirectories but one
    single file will be skipped if the file is not an image. Increasing
    `dig_stability` can counteract this. A big value (e.g. 10) will cause a
    directory to be skipped only when it contains many files and enough of
    these are not images.
    '''

    assert dig_stability >= 1
    assert dig_strength >= 1

    # We try to pick one file per location, but if we don't find more files
    # in other locations we may go back to locations from which we picked
    # some files already. We use this queue to remember those.
    remaining_file_iters = deque()

    # visited_already ensures we don't end up following circular symlinks.
    visited_already = set()

    # Do a breadth first search starting from the given directory.
    paths_to_visit = deque()
    if os.path.isdir(path):
        paths_to_visit.append((0, path))

    while paths_to_visit:
        score, p = paths_to_visit.popleft()
        out = {}
        entries = get_files_in_dir(p, out=out, **kwargs)
        n = out['num_skipped']
        files = [name for is_dir, name in entries if not is_dir]
        dirs = [name for is_dir, name in entries if is_dir]

        # Update the score for this directory.
        score += (10 * n + dig_stability) // (len(files) + dig_stability)

        # Pick one file from this location and save the iterator in case we
        # later needs to pick more files.
        file_iter = sparse_iterator(files, num_picks)
        candidate = next(file_iter, None)
        if candidate is not None:
            yield candidate
        remaining_file_iters.append(file_iter)

        # Skip subdirectories if this directory's score is above the threshold.
        if score > dig_strength:
            continue

        # Append other directories in a sparse order so that we can continue
        # to explore the hierarchy.
        for dir_name in sparse_iterator(dirs, num_picks):
            rp = os.path.realpath(dir_name)
            if rp not in visited_already:
                if rp == dir_name or follow_links:
                    paths_to_visit.append((score, dir_name))
                    visited_already.add(rp)

    # We get here when we didn't manage to pick all the files from different
    # locations. So here we go back to the previous locations to pick more
    # files.
    while remaining_file_iters:
        file_iter = remaining_file_iters.popleft()
        candidate = next(file_iter, None)
        if candidate is not None:
            yield candidate
            remaining_file_iters.append(file_iter)
