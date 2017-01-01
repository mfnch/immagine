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
import pango

from .backcaller import BackCaller

def add_close_button(label):
    hb = gtk.HBox(False, 0)
    hb.pack_start(label)

    # Make the close button for the tab.
    b = gtk.Button()
    b.set_relief(gtk.RELIEF_NONE)
    b.set_focus_on_click(False)
    close_icon = gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
    b.add(close_icon)
    hb.pack_start(b, False, False)

    # Reduce the button size as much as possible.
    style = gtk.RcStyle()
    style.xthickness = style.ythickness = 0
    b.modify_style(style)
    hb.show_all()
    return (b, hb)

class BaseTab(BackCaller, gtk.VBox):
    def __init__(self, path, toolbar_desc, tab_width_chars=25,
                 with_close_button=False, label_ellipsize_end=False,
                 **kwargs):
        gtk.VBox.__init__(self)
        BackCaller.__init__(self, **kwargs)
        self.toolbutton_fullscreen = None

        label = gtk.Label()
        label.set_width_chars(tab_width_chars)
        label.set_ellipsize(pango.ELLIPSIZE_END if label_ellipsize_end
                            else pango.ELLIPSIZE_START)
        label.set_tooltip_text(path)
        label.set_text(os.path.split(path)[-1])

        self.tab_top = label
        if with_close_button:
            # Add a close button in the tab, close to the tab label.
            self.close_button, self.tab_top = add_close_button(label)
        self.label = label

        self.toolbar = tb = gtk.Toolbar()
        tb.set_style(gtk.TOOLBAR_ICONS)
        tb.set_show_arrow(False)
        tb.set_tooltips(True)
        for item in toolbar_desc:
            if len(item) == 3:
                stock, tooltip, name = item
                toolbutton = gtk.ToolButton(stock)
                toolbutton.set_tooltip_text(tooltip)
                tb.insert(toolbutton, -1)
                fn = getattr(self, name, None)
                if fn is not None:
                    toolbutton.connect('clicked', fn)
                setattr(self, 'toolbutton_{}'.format(name), toolbutton)
            else:
                tb.insert(gtk.SeparatorToolItem(), -1)

    def set_fullscreen(self, fs):
        tb = self.toolbutton_fullscreen
        if tb is None:
            return
        tb.set_stock_id(gtk.STOCK_LEAVE_FULLSCREEN
                        if fs else gtk.STOCK_FULLSCREEN)

    def fullscreen(self, action):
        self.call('toggle_fullscreen', action)

    def on_key_press_event(self, event):
        '''Handle key press events directed to this tab.'''
