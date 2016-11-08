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

import os
import pygtk
pygtk.require('2.0')
import gtk

from .base_tab import BaseTab
from .image_browser import ImageBrowser

class BrowserTab(BaseTab):
    def __init__(self, directory_path):
        toolbar_desc = \
          ((gtk.STOCK_OPEN, 'Select a new directory to browse', 'on_open'),
           (gtk.STOCK_GO_UP, 'Parent directory', 'go_up'),
           (gtk.STOCK_GO_BACK, 'Go back to previous directory', 'go_back'),
           (gtk.STOCK_GO_FORWARD, 'Go to next directory', 'go_forward'),
           (),
           (gtk.STOCK_FULLSCREEN, 'Enter full-screen mode', 'fullscreen'))

        super(BrowserTab, self).__init__(directory_path,
                                         toolbar_desc,
                                         toggle_fullscreen=None,
                                         directory_changed=None,
                                         image_clicked=None,
                                         open_location=None)
        # Tab setup.
        self.path = os.path.realpath(directory_path)

        # Image browser widget.
        self.image_browser = ib = ImageBrowser(directory_path)
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

    def on_directory_changed(self, new_directory):
        self.label.set_text(new_directory)
        ib = self.image_browser
        self.toolbutton_go_back.set_sensitive(ib.has_previous_directory())
        self.toolbutton_go_forward.set_sensitive(ib.has_next_directory())
        self.call('directory_changed', new_directory)

    def on_image_clicked(self, *args):
        self.call('image_clicked', *args)

    def on_open(self, action):
        self.call('open_location')

    def on_key_press_event(self, event):
        name = gtk.gdk.keyval_name(event.keyval).lower()
        if event.state & gtk.gdk.CONTROL_MASK:
            if name == 'up':
                self.go_up()
                return True
            elif name == 'left':
                self.go_back()
                return True
            elif name == 'right':
                self.go_forward()
                return True
        if name == 'escape':
            self.go_back()
            return True
        return False

    def go_up(self, action=None):
        self.image_browser.go_to_parent_directory()

    def go_back(self, action=None):
        self.image_browser.go_to_previous_directory()

    def go_forward(self, action=None):
        self.image_browser.go_to_next_directory()

    def go_to_directory(self, directory):
        self.image_browser.go_to_directory(directory)
