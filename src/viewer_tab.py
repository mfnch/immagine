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

import pygtk
pygtk.require('2.0')
import gtk

from .base_tab import BaseTab

class ViewerTab(BaseTab):
    def __init__(self, image_path, file_list=None, file_index=None):
        toolbar_desc = \
         ((gtk.STOCK_ZOOM_IN, 'Zoom in', 'zoom_in'),
          (gtk.STOCK_ZOOM_FIT, 'Zoom to fit', 'zoom_fit'),
          (gtk.STOCK_ZOOM_OUT, 'Zoom out', 'zoom_out'),
          (gtk.STOCK_ZOOM_100, 'Zoom to 100%', 'zoom_100'),
          (),
          (gtk.STOCK_MEDIA_PREVIOUS, 'Previous picture', 'change_previous'),
          (gtk.STOCK_MEDIA_NEXT, 'Next picture', 'change_next'),
          (gtk.STOCK_CLOSE, 'Close tab', 'close_tab'),
          (),
          (gtk.STOCK_FULLSCREEN, 'Enter full-screen mode', 'fullscreen'))
        super(ViewerTab, self).__init__(image_path, toolbar_desc,
                                        with_close_button=True,
                                        label_ellipsize_end=True,
                                        toggle_fullscreen=None,
                                        close_tab=None)
        self.file_list = file_list
        self.file_index = file_index
        self.max_zoom = 4.0        # Maximum zoom factor.
        self.min_zoom = 0.02       # Minimum zoom factor.
        self.zoom_increment = 1.5  # Zoom magnification when doing a "zoom in".
        self.image_path = image_path
        self.image = image = gtk.Image()
        self.size = None
        pixbuf = gtk.gdk.pixbuf_new_from_file(image_path)
        image.set_from_pixbuf(pixbuf)

        eb = gtk.EventBox()
        eb.add(image)

        self.scrolled_window = sw = gtk.ScrolledWindow()
        sw.add_with_viewport(eb)
        self.pack_start(self.toolbar, expand=False)
        self.pack_start(sw)

        eb.connect('size-allocate', self.on_size_allocate)
        self.close_button.connect('clicked', self.close_tab)

    def on_size_allocate(self, widget, allocation):
        if self.size == None:
            self.size = (allocation.width, allocation.height)
            self.zoom_fit(None)

    def on_key_press_event(self, event):
        name = ''
        if event.state & gtk.gdk.CONTROL_MASK:
            name += 'ctrl+'
        name += gtk.gdk.keyval_name(event.keyval).lower()
        if name in ('ctrl+minus', 'up'):
            self.zoom_out()
        elif name in ('ctrl+plus', 'down'):
            self.zoom_in()
        elif name in ('ctrl+0', 'right'):
            self.zoom_fit()
        elif name in ('ctrl+9', 'left'):
            self.zoom_100()
        elif name == 'page_up':
            self.change_previous()
        elif name == 'page_down':
            self.change_next()
        elif name == 'escape':
            self.close_tab()
        else:
            return False
        return True

    def close_tab(self, action=None):
        self.call('close_tab', self)

    def zoom_in(self, action=None):
        self.zoom_by_factor(self.zoom_increment)

    def zoom_out(self, action=None):
        self.zoom_by_factor(1.0 / self.zoom_increment)

    def zoom_by_factor(self, factor):
        pixbuf = self.image.get_pixbuf()
        new_width = int(pixbuf.get_width() * factor)
        new_height = int(pixbuf.get_height() * factor)
        self.zoom_to_size(new_width, new_height)

    def zoom_to_size(self, width, height, check_zoom_factor=True):
        pixbuf = gtk.gdk.pixbuf_new_from_file(self.image_path)
        pixbuf_width = pixbuf.get_width()
        pixbuf_height = pixbuf.get_height()

        if width / float(height) >= pixbuf_width / float(pixbuf_height):
            factor = height / float(pixbuf_height)
            new_width = pixbuf_width * height // pixbuf_height
            new_height = height
        else:
            factor = width / float(pixbuf_width)
            new_width = width
            new_height = pixbuf_height * width // pixbuf_width

        if check_zoom_factor:
            norm_factor = min(self.max_zoom, max(self.min_zoom, factor))
            if factor != norm_factor:
                self.zoom_to_size(int(pixbuf_width * norm_factor),
                                  int(pixbuf_height * norm_factor),
                                  check_zoom_factor=False)
                return

        pixbuf = pixbuf.scale_simple(new_width, new_height,
                                     gtk.gdk.INTERP_BILINEAR)
        self.image.clear()
        self.image.set_from_pixbuf(pixbuf)

    def zoom_fit(self, action=None):
        rect = self.scrolled_window.get_allocation()
        if rect.x < 0 or rect.y < 0 or rect.width < 1 or rect.height < 1:
            return

        # TODO: Find a proper way of getting the maximum image size we can put
        # in the scrolled window.
        self.zoom_to_size(rect.width - 2, rect.height - 2)

    def zoom_100(self, action=None):
        pixbuf = gtk.gdk.pixbuf_new_from_file(self.image_path)
        self.image.clear()
        self.image.set_from_pixbuf(pixbuf)

    def change_picture(self, delta_index):
        idx = self.file_index + delta_index
        if idx < 0 or idx >= len(self.file_list):
            return False
        self.image_path = self.file_list[idx].full_path
        self.file_index = idx
        self.zoom_fit()

    def change_previous(self, *ignore):
        self.change_picture(-1)

    def change_next(self, *ignore):
        self.change_picture(1)
