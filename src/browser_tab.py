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

import os

import gtk

from .base_tab import BaseTab
from .image_browser import ImageBrowser


class BrowserTab(BaseTab):
    def __init__(self, directory_path, **kwargs):
        toolbar_desc = \
          ((gtk.STOCK_OPEN, 'Select a new directory to browse', 'on_open'),
           (gtk.STOCK_GO_UP, 'Parent directory', 'go_up'),
           (gtk.STOCK_GO_BACK, 'Go back to previous directory', 'go_back'),
           (gtk.STOCK_GO_FORWARD, 'Go to next directory', 'go_forward'),
           (),
           (gtk.STOCK_ZOOM_IN, 'Increase thumbnail size', 'zoom_in'),
           (gtk.STOCK_ZOOM_OUT, 'Decrease thumbnail size', 'zoom_out'),
           (gtk.STOCK_ZOOM_100, 'Default thumbnail size', 'zoom_100'),
           (),
           (gtk.STOCK_FULLSCREEN, 'Enter full-screen mode', 'fullscreen'))

        super(BrowserTab, self).__init__(directory_path,
                                         toolbar_desc,
                                         toggle_fullscreen=None,
                                         directory_changed=None,
                                         image_clicked=None,
                                         open_location=None)
        self.config = kwargs.get('config')

        # Tab setup.
        self.path = os.path.realpath(directory_path)

        # Image browser widget.
        self._image_browser = ib = ImageBrowser(directory_path, **kwargs)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(ib)

        # Add the two widgets (toolbar and image browser) to the main vbox.
        self.pack_start(self.toolbar, expand=False)
        self.pack_start(sw)

        # Set up signals.
        ib.set_callback('directory_changed', self.on_directory_changed)
        ib.set_callback('image_clicked', self.on_image_clicked)

        # Activate buttons properly.
        self.on_directory_changed(self.path)

        self._image_browser.grab_focus()

    def on_directory_changed(self, new_directory):
        self.label.set_text(new_directory)
        ib = self._image_browser
        self.toolbutton_go_back.set_sensitive(ib.has_previous_directory())
        self.toolbutton_go_forward.set_sensitive(ib.has_next_directory())
        self.call('directory_changed', new_directory)

    def on_image_clicked(self, *args):
        self.call('image_clicked', *args)

    def on_open(self, action):
        self.call('open_location')

    def on_key_press_event(self, event):
        name = ''
        if event.state & gtk.gdk.CONTROL_MASK:
            name += 'ctrl+'
        name += gtk.gdk.keyval_name(event.keyval).lower()
        if name == 'ctrl+minus':
            self.zoom_out()
        elif name == 'ctrl+plus':
            self.zoom_in()
        elif name in ('ctrl+0', 'ctrl+9', 'right'):
            self.zoom_100()
        if name == 'ctrl+up':
            self.go_up()
        elif name == 'ctrl+left':
            self.go_back()
        elif name == 'ctrl+right':
            self.go_forward()
        elif name == 'escape':
            self.go_back()
        else:
            return False
        return True

    def zoom_in(self, obj=None):
        self._image_browser.zoom(1.0)

    def zoom_out(self, obj=None):
        self._image_browser.zoom(-1.0)

    def zoom_100(self, *args):
        self._image_browser.zoom(0.0, relative=False)

    def go_up(self, action=None):
        self._image_browser.go_to_parent_directory()

    def go_back(self, action=None):
        self._image_browser.go_to_previous_directory()

    def go_forward(self, action=None):
        self._image_browser.go_to_next_directory()

    def go_to_directory(self, directory):
        self._image_browser.go_to_directory(directory)

    def update_album(self):
        '''Regenerate the album after a change of configuration.'''
        self._image_browser.update_album()
