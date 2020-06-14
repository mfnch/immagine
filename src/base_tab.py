# Copyright 2016-2017, 2020 Matteo Franchin
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

from gi.repository import Gtk
from gi.repository import Pango

from .backcaller import BackCaller

def add_close_button(label):
    hb = Gtk.HBox(False, 0)
    hb.pack_start(label, True, True, 0)

    # Make the close button for the tab.
    b = Gtk.Button()
    b.set_relief(Gtk.ReliefStyle.NONE)
    b.set_focus_on_click(False)
    close_icon = Gtk.Image.new_from_stock(Gtk.STOCK_CLOSE, Gtk.IconSize.MENU)
    b.add(close_icon)
    hb.pack_start(b, False, False, 0)

    # Reduce the button size as much as possible.
    style = Gtk.RcStyle()
    style.xthickness = style.ythickness = 0
    b.modify_style(style)
    hb.show_all()
    return (b, hb)


class BaseTab(BackCaller, Gtk.VBox):
    def __init__(self, path, toolbar_desc, tab_width_chars=25,
                 with_close_button=False, label_ellipsize_end=False,
                 **kwargs):
        Gtk.VBox.__init__(self)
        BackCaller.__init__(self, **kwargs)
        self.toolbutton_fullscreen = None

        self.tab_label = label = Gtk.Label()
        label.set_width_chars(tab_width_chars)
        label.set_ellipsize(Pango.EllipsizeMode.END if label_ellipsize_end
                            else Pango.EllipsizeMode.START)
        self.update_title(path)

        if with_close_button:
            # Add a close button in the tab, close to the tab label.
            self.close_button, self.tab_top = add_close_button(label)
        self.label = label

        self.toolbar = tb = Gtk.Toolbar()
        tb.set_style(Gtk.ToolbarStyle.ICONS)
        tb.set_show_arrow(False)
        for item in toolbar_desc:
            if len(item) == 3:
                stock, tooltip, name = item
                toolbutton = Gtk.ToolButton(stock)
                toolbutton.set_tooltip_text(tooltip)
                tb.insert(toolbutton, -1)
                fn = getattr(self, name, None)
                if fn is not None:
                    toolbutton.connect('clicked', fn)
                setattr(self, 'toolbutton_{}'.format(name), toolbutton)
            else:
                tb.insert(Gtk.SeparatorToolItem(), -1)

    def update_title(self, path):
        label = self.tab_label
        label.set_tooltip_text(path)
        label.set_text(os.path.split(path)[-1])

    def set_fullscreen(self, fs):
        tb = self.toolbutton_fullscreen
        if tb is None:
            return
        tb.set_stock_id(Gtk.STOCK_LEAVE_FULLSCREEN
                        if fs else Gtk.STOCK_FULLSCREEN)

    def fullscreen(self, action):
        self.call('toggle_fullscreen', action)

    def on_key_press_event(self, event):
        '''Handle key press events directed to this tab.'''
