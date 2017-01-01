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
import gobject


class AutoHideWindow(gtk.Window):
    '''Popup window which auto-hides when the user does not interact with it.
    '''

    def __init__(self, parent=None, auto_hide_delay=3000, proximity=(0, 0),
                 role='toolbox'):
        super(AutoHideWindow, self).__init__(gtk.WINDOW_TOPLEVEL)
        self.proximity = proximity

        # Auto-hide timer.
        self.timer = None
        self.hide_at_timeout = True
        self.default_timeout = auto_hide_delay

        # Window position.
        self.preferred_position = None

        # Set some window attributes.
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_role(role)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_TOOLBAR)
        self.set_skip_taskbar_hint(True)
        self.set_deletable(False)
        self.set_events(gtk.gdk.POINTER_MOTION_MASK)
        self.set_accept_focus(False)

        # Closing this window only hides it.
        self.connect("motion_notify_event", self.on_motion_notify_event)
        self.connect("delete_event", self.on_delete_event)

    def hide(self, *args):
        if self.timer is not None:
            gobject.source_remove(self.timer)
            self.timer = None
        self.preferred_position = self.get_position()
        super(AutoHideWindow, self).hide()

    def mouse_is_nearby(self):
        '''Return whether the mouse pointer is near the window.'''
        x_proximity, y_proximity = self.proximity
        x, y = self.get_pointer()
        if x < -x_proximity or y < -y_proximity:
            return False
        dx, dy = self.get_size()
        if x > dx + x_proximity or y > dy + y_proximity:
            return False
        return True

    def on_motion_notify_event(self, *args):
        self.show_with_auto_hide()
        return True

    def on_hide_timer(self):
        if self.hide_at_timeout:
            self.hide()
            return False
        else:
            self.hide_at_timeout = not self.mouse_is_nearby()
            return True

    def on_delete_event(self, *args):
        self.hide()
        return True

    def show_with_auto_hide(self, timeout=None):
        if self.timer is None:
            self.timer = gobject.timeout_add(timeout or self.default_timeout,
                                             self.on_hide_timer)
            self.hide_at_timeout = True
            if self.preferred_position is not None:
                self.move(*self.preferred_position)
            self.show_all()
        else:
            # Timer already running, let's just delay it.
            self.hide_at_timeout = False


class ToolbarWindow(object):
    '''Object used to popup the toolbar when in fullscreen mode.'''

    def __init__(self):
        self.window = AutoHideWindow()
        self.toolbar = None
        self.container = gtk.HBox(homogeneous=False, spacing=0)
        self.window.add(self.container)
        self.move_button = gtk.Button('Move')
        self.move_button.connect('button-press-event', self.on_move_toolbar)

    def on_move_toolbar(self, widget, event):
        self.window.begin_move_drag(event.button, int(event.x_root),
                                    int(event.y_root), event.time)

    def begin(self, toolbar):
        self.toolbar = toolbar
        hbox = self.container
        hbox.pack_start(self.toolbar, expand=False, fill=False)
        hbox.pack_end(self.move_button, expand=False, fill=False)
        self.window.show_with_auto_hide()

    def end(self):
        self.window.hide()
        tb = self.toolbar
        hbox = self.container
        hbox.remove(self.move_button)
        hbox.remove(tb)
        self.toolbar = None
        return tb

    def show_if_mouse_nearby(self):
        '''Show the toolbar if the mouse pointer is close enough.'''
        if self.window.mouse_is_nearby():
            self.window.show_with_auto_hide()
