#!/usr/bin/env python

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

'''Simple image viewer.'''

import os
import pygtk
pygtk.require('2.0')
import gobject
import gtk

from browser_tab import BrowserTab
from viewer_tab import ViewerTab
import file_utils

def create_action_tuple(name=None, stock_id=None, label=None, accel=None,
                        tooltip=None, fn=None):
    if accel is None and tooltip is None and fn is None:
        return (name, stock_id, label)
    return (name, stock_id, label, accel, tooltip, fn)

def create_toggle_tuple(name=None, stock_id=None, label=None, accel=None,
                        tooltip=None, fn=None, value=None):
    return (name, stock_id, label, accel, tooltip, fn, value)

class ApplicationMainWindow(gtk.Window):
    application_name = 'Immagine image viewer'

    def __init__(self, start_path, parent=None):
        super(ApplicationMainWindow, self).__init__()
        self.fullscreen_mode = False
        self.open_dialog = None

        try:
            self.set_screen(parent.get_screen())
        except AttributeError:
            self.connect('destroy', lambda *w: gtk.main_quit())

        self.set_title(self.application_name)
        self.set_default_size(800, 600)

        merge = gtk.UIManager()
        self.set_data('ui-manager', merge)
        ui_info, action_group = self.__create_action_group()
        merge.insert_action_group(action_group, 0)
        self.add_accel_group(merge.get_accel_group())

        try:
            mergeid = merge.add_ui_from_string(ui_info)
        except gobject.GError as msg:
            print('Error doing add_ui_from_string: %s' % msg)

        # The menu is shared across all tabs.
        bar = merge.get_widget("/MenuBar")
        bar.show()

        # Below the menu, we place the notebook.
        self.notebook = nb = gtk.Notebook()
        nb.set_scrollable(True)
        nb.set_tab_pos(gtk.POS_TOP)

        # When given a directory open a browsing tab. When given a file open
        # the parent directory and the file in two separate tabs.
        start_file = None
        if start_path is None:
            start_dir = os.getcwd()
        elif os.path.isdir(start_path):
            start_dir = start_path
        else:
            start_dir = os.path.dirname(start_path) or os.getcwd()
            if not os.path.isdir(start_dir):
                start_dir = os.getcwd()
            elif os.path.exists(start_path):
                start_file = os.path.split(start_path)[1]
        self.browser_tab = self.open_tab(start_dir)
        if start_file is not None:
            self.open_tab(start_file)

        # Place menu and notebook in a VBox. Add this to the window.
        vbox = gtk.VBox()
        vbox.pack_start(bar, expand=False)
        vbox.pack_start(nb)
        self.add(vbox)

        self.connect('window_state_event', self.on_window_state_event)
        self.show_all()

    def __create_action_group(self):
        ui_info = \
          '''<ui>
            <menubar name='MenuBar'>
              <menu action='FileMenu'>
                <menuitem action='Open'/>
                <separator/>
                <menuitem action='Quit'/>
              </menu>
              <menu action='ViewMenu'>
                <menuitem action='CloseTab'/>
                <menuitem action='Fullscreen'/>
                <menuitem action='ShowHidden'/>
              </menu>
              <menu action='HelpMenu'>
                <menuitem action='About'/>
              </menu>
            </menubar>
          </ui>'''

        action = create_action_tuple
        action_entries = \
          (action(name='FileMenu', label='_File'),
           action(name='ViewMenu', label='_View'),
           action(name='HelpMenu', label='_Help'),
           action(name='Quit', stock_id=gtk.STOCK_QUIT, label='Quit',
                  accel='<control>Q', tooltip='Quit',
                  fn=self.quit_action),
           action(name='Open', stock_id=gtk.STOCK_OPEN,
                  label='_Open directory', accel='<control>O',
                  tooltip='Open a directory', fn=self.on_open_location),
           action(name='CloseTab', label='_Close current tab',
                  accel='<control>W', tooltip='Toggle fullscreen mode',
                  fn=self.close_tab_action),
           action(name='Fullscreen', label='_Fullscreen', accel='F11',
                  tooltip='Toggle fullscreen mode',
                  fn=self.fullscreen_action),
           action(name='About', label='_About', accel='<control>A',
                  tooltip='About', fn=self.about_action))

        toggle = create_toggle_tuple
        toggle_entries = \
          (toggle(name='ShowHidden', label='_Show hidden files',
                  accel='<control>H', tooltip='Show hidden files',
                  fn=self.on_hide_toggle, value=True),)

        action_group = gtk.ActionGroup("AppWindowActions")
        action_group.add_actions(action_entries)
        action_group.add_toggle_actions(toggle_entries)
        return (ui_info, action_group)

    def quit_action(self, action):
        gtk.main_quit()

    def open_tab(self, path):
        if os.path.isdir(path):
            return self.open_browser_tab(path)
        else:
            return self.open_viewer_tab(path)

    def open_browser_tab(self, path):
        if not os.path.isdir(path):
            return None

        bt = BrowserTab(path)
        bt.set_callback('toggle_fullscreen', self.fullscreen_action)
        bt.set_callback('directory_changed', self.on_directory_changed)
        bt.set_callback('image_clicked', self.on_image_clicked)
        bt.set_callback('open_location', self.on_open_location)
        bt.image_browser.grab_focus()
        bt.show_all()

        self.notebook.append_page(bt, tab_label=bt.label)
        self.notebook.set_tab_reorderable(bt, True)
        self.notebook.set_current_page(-1)
        return bt

    def open_viewer_tab(self, path):
        vt = ViewerTab(path)
        vt.set_callback('close_tab', self.on_close_tab)
        vt.set_callback('toggle_fullscreen', self.fullscreen_action)
        vt.show_all()

        self.notebook.append_page(vt, tab_label=vt.tab_top)
        self.notebook.set_tab_reorderable(vt, True)
        self.notebook.set_current_page(-1)

    def about_action(self, action):
        dialog = gtk.AboutDialog()
        dialog.set_name('Immagine Image Viewer')
        dialog.set_copyright('\302\251 Copyright 2016 Matteo Franchin')
        dialog.set_website('https://github.com/mfnch/immagine')
        dialog.connect('response', lambda d, r: d.destroy())
        dialog.show()

    def close_tab_action(self, action):
        n = self.notebook.get_current_page()
        if isinstance(self.notebook.get_nth_page(n), ViewerTab):
            self.notebook.remove_page(n)

    def get_fullscreen_mode(self):
        return self.fullscreen_mode

    def fullscreen_action(self, action):
        if self.fullscreen_mode:
            self.unfullscreen()
        else:
            self.fullscreen()

    def on_directory_changed(self, new_directory):
        self.set_title(new_directory + ' - ' + self.application_name)

    def on_image_clicked(self, image_path):
        if not os.path.isdir(image_path):
            self.open_viewer_tab(image_path)

    def on_close_tab(self, viewer):
        if isinstance(viewer, ViewerTab):
            n = self.notebook.page_num(viewer)
            self.notebook.remove_page(n)

    def on_window_state_event(self, widget, event):
        mask = gtk.gdk.WINDOW_STATE_MAXIMIZED | gtk.gdk.WINDOW_STATE_FULLSCREEN
        self.fullscreen_mode = fs = \
          (event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN) != 0
        nb = self.notebook
        for page in range(nb.get_n_pages()):
            tab = nb.get_nth_page(page)
            tab.set_fullscreen(fs)

    def on_open_location(self, *action):
        if self.open_dialog is None:
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                       gtk.STOCK_OPEN, gtk.RESPONSE_OK)
            self.open_dialog = fc = gtk.FileChooserDialog(
                title='Choose directory',
                parent=None,
                action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                buttons=buttons, backend=None)
            fc.set_default_response(gtk.RESPONSE_OK)

            f = gtk.FileFilter()
            f.set_name('All files')
            f.add_pattern("*")
            fc.add_filter(f)

            f = gtk.FileFilter()
            f.set_name("Images")
            f.add_mime_type("image/png")
            f.add_mime_type("image/jpeg")
            f.add_mime_type("image/gif")
            for ext in file_utils.image_file_extensions:
                f.add_pattern('*' + ext)
            fc.add_filter(f)

        fc = self.open_dialog
        response = fc.run()
        choice = (fc.get_filename() if response == gtk.RESPONSE_OK else None)
        fc.hide()

        if choice is not None:
            self.browser_tab.go_to_directory(choice)

    def on_hide_toggle(self, action):
        pass


def main(args):
    start_path = (args[1] if len(args) >= 2 else None)
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    ApplicationMainWindow(start_path)
    gtk.main()
    gtk.gdk.threads_leave()

if __name__ == '__main__':
    import sys
    main(sys.argv)
