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
import logging as L

from gi.repository import GObject, Gtk, Gdk, GdkPixbuf, GLib

from . import layout
from . import icons
from .thumbnailers import build_empty_thumbnail
from .orchestrator import Orchestrator, THUMBNAIL_DONE
from .backcaller import BackCaller
from .file_utils import FileList
from .config import logger, INT2, COLOR


class Location(object):
    def __init__(self, full_path, y_pos=0):
        self.path = os.path.realpath(full_path)
        self.y = y_pos


class ImageBrowser(Gtk.DrawingArea, Gtk.Scrollable, BackCaller):
    def __init__(self, start_dir, hadjustment=None, vadjustment=None,
                 config=None):
        Gtk.DrawingArea.__init__(self)
        BackCaller.__init__(self,
                            directory_changed=None,
                            image_clicked=None)

        assert config is not None
        self._config = config
        config.override('thumb.final_size', self._thumb_final_size_getter)

        # Directory this object is browsing.
        self.location = Location(start_dir)
        self.file_list = None
        self.album = None
        self.previous_locations = []
        self.next_locations = []

        # Adjustment objects to control the scrolling.
        self._hadjustment = hadjustment
        self._vadjustment = vadjustment

        self.orchestrator = Orchestrator()
        self.orchestrator.set_callback('thumbnail_available',
                                       self.on_thumbnail_available)

        self.last_tooltip_shown = None
        self.props.has_tooltip = True

        # Allow the object to receive scroll events and other events.
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.SCROLL_MASK)

        self.connect('draw', self.on_draw_event)
        self.connect('configure-event', self.on_size_change)
        self.connect('button-press-event', self.on_button_press_event)
        self.connect('query-tooltip', self.on_query_tooltip)

    def _thumb_final_size_getter(self, parent=None, attr_name=None):
        cfg = self._config
        min_x, min_y = cfg.get('thumb.min_abs_size', (32, 32), INT2)
        scr_x, scr_y = cfg.get('screen.size', (1366, 768), INT2)
        scale_exp = cfg.get('thumb.scale_exp', 0.0, float)
        scale_base = cfg.get('thumb.scale_base', 1.25, float)
        scale_base_adjusted = max(1.05, min(2.0, scale_base))
        scale = scale_base_adjusted**scale_exp
        thumb_x, thumb_y = cfg.get('thumb.size')
        return (int(max(min_x, min(scr_x // 2, thumb_x*scale))),
                int(max(min_y, min(scr_y // 2, thumb_y*scale))))

    def get_widget_size(self):
        return (self.get_allocated_width(), self.get_allocated_height())

    def set_hadjustment(self, adjustment):
        self._hadjustment = ha = adjustment
        if ha is None:
            return
        ha.set_lower(0.0)
        ha.set_upper(1.0)
        ha.set_value(0.0)
        ha.set_page_size(1.0)
        ha.set_page_increment(0.0)
        ha.set_step_increment(0.05)
        ha.connect("value-changed", self._adjustments_changed)

    def get_hadjustment(self):
        return self._hadjustment

    hadjustment = GObject.Property(type=Gtk.Adjustment,
                                   default=None,
                                   getter=get_hadjustment,
                                   setter=set_hadjustment)

    def get_vadjustment(self):
        return self._vadjustment

    def set_vadjustment(self, adjustment):
        self._vadjustment = va = adjustment
        if va is None:
            return
        va.set_lower(0.0)
        va.set_upper(1.0)
        va.set_value(0.0)
        va.set_page_size(1.0)
        va.set_page_increment(0.0)
        va.set_step_increment(0.05)
        va.connect("value-changed", self._adjustments_changed)

    vadjustment = GObject.Property(type=Gtk.Adjustment,
                                   default=None,
                                   getter=get_vadjustment,
                                   setter=set_vadjustment)

    hscroll_policy = GObject.Property(type=Gtk.ScrollablePolicy,
                                      default=Gtk.ScrollablePolicy.NATURAL)

    vscroll_policy = GObject.Property(type=Gtk.ScrollablePolicy,
                                      default=Gtk.ScrollablePolicy.NATURAL)

    def _lay_out_album(self, width=None):
        if width is None:
            width, _ = self.get_widget_size()

        # Create the file list based on the current configuration.
        cfg = self._config
        self.file_list = file_list = \
          FileList(
            self.location.path,
            show_hidden_files=cfg.get('browser.show_hidden_files', True),
            reversed_sort=cfg.get('browser.reversed_sort', False),
            sort_type=cfg.get('browser.sort_type', FileList.SORT_BY_MOD_DATE)
          )

        self.album = layout.ImageAlbum(file_list,
                                       max_width=width,
                                       max_size=cfg.get('thumb.final_size'),
                                       border=cfg.get('thumb.border', (5, 5)))

    def _set_y_location(self):
        value = self._vadjustment.get_value()
        upper = self._vadjustment.get_upper()
        self.location.y = (value / float(upper) if upper != 0 else 0)

    def _get_y_location(self):
        return int(self.location.y * self._vadjustment.get_upper())

    def _adjustments_changed(self, adjustment):
        va = self._vadjustment
        self._set_y_location()
        self.queue_draw()

    def scroll_adjustment(self, hadjustment, vadjustment):
        self._hadjustment = hadjustment
        self._vadjustment = vadjustment
        if isinstance(hadjustment, Gtk.Adjustment):
            self._hadj_valchanged_handler = \
                hadjustment.connect("value-changed", self._adjustments_changed)

    def _update_scrollbars(self):
        '''(internal) Update the ranges and positions of the scrollbars.'''

        window_size = self.get_widget_size()
        window_height = window_size[1]

        # When resizing the window we want to make sure we view roughly the
        # same images we saw before the resize.
        va = self._vadjustment
        old_album_height = va.get_upper()
        new_album_height = self.album.get_height() + 5
        relative_pos = va.get_value() / float(old_album_height)
        new_value = relative_pos * new_album_height

        # Set the new view, making sure it is within the interval.
        va.set_lower(0.0)
        va.set_upper(new_album_height)
        va.set_page_size(window_height)
        va.set_page_increment(0.9 * window_height)
        va.set_step_increment(0.3 * window_height)
        va.set_value(max(0, min(new_value, new_album_height - window_height)))

    def get_thumbnail_pixbuf(self, thumbnail):
        '''Get the pixbuf (possibly from the cache) for the given Thumbnail
        object.
        '''

        file_item = thumbnail.get_file_item()
        if not thumbnail.damaged:
            tn = self.orchestrator.request_thumbnail(file_item.full_path,
                                                     thumbnail.size)
            if tn.state is THUMBNAIL_DONE:
                height, width, num_components = tn.data.shape
                rowstride = width * num_components
                # TODO: avoid doing so many copies of the data.
                data = GLib.Bytes.new(tn.data.tobytes())
                return GdkPixbuf.Pixbuf.new_from_bytes(
                    data, GdkPixbuf.Colorspace.RGB, False, 8,
                    width, height, rowstride)
            text = 'Loading...\n' + os.path.basename(file_item.name)
            icon_color = self._config.get_color_triple('thumb.color.loading',
                                                       '#ff0000')
        else:
            text = os.path.basename(file_item.name) + '\n(Damaged)'
            icon_color = self._config.get_color_triple('thumb.color.damaged',
                                                       '#a00000')

        return icons.generate_text_icon(text, thumbnail.size, cache=True,
                                        color=icon_color,
                                        out_format=icons.FORMAT_PIXBUF)

    def on_thumbnail_available(self, *args):
        '''Called by the orchestrator when thumbnails become available.'''

        # As this function is called by a separate thread, we take the lock.
        try:
            Gdk.threads_enter()
            self.queue_draw()
        finally:
            Gdk.threads_leave()

    def on_draw_event(self, widget, context):
        '''Function responsible for the rendering of the widget.'''

        ok, r = Gdk.cairo_get_clip_rectangle(context)
        if not ok:
            L.error('Failed getting clip rectangle in ZoomableArea.draw')
            return False

        dy = self._get_y_location()

        # Compute viewport coordinates.
        vp_x0, vp_y0 = (r.x, r.y + dy)
        vp_width, vp_height = (r.width, r.height)
        vp_x1 = vp_x0 + vp_width
        vp_y1 = vp_y0 + vp_height

        for tn in self.album.get_thumbnails(vp_x0, vp_y0, vp_width, vp_height):
            x, y = tn.pos
            pixbuf = self.get_thumbnail_pixbuf(tn)
            x0 = max(x, vp_x0)
            y0 = max(y, vp_y0)
            x1 = min(x + pixbuf.get_width(), vp_x1)
            y1 = min(y + pixbuf.get_height(), vp_y1)
            sx = x1 - x0
            sy = y1 - y0
            if sx <= 0 or sy <= 0:
                logger.debug('Error: sx={}, sy={}'.format(sx, sy))
                continue
            buf_area = pixbuf.new_subpixbuf(x0 - x, y0 - y, sx, sy)

            Gdk.cairo_set_source_pixbuf(context, buf_area, x0, y0 - dy)
            context.paint()

        return True

    def on_size_change(self, myself, event):
        '''Called when the size of the object changes.'''
        self._lay_out_album(event.width)
        self._update_scrollbars()
        self.orchestrator.clear_queue()

    def on_button_press_event(self, eventbox, event):
        x, y = event.get_coords()
        y += self._get_y_location()
        thumbnail = self.album.find_thumbnail_at_pos((x, y))
        if thumbnail is None:
            return
        file_item = thumbnail.get_file_item()
        self.call('image_clicked', self.file_list, file_item)
        if file_item.is_dir:
            self.previous_locations.append(self.location)
            self.next_locations = []
            self._change_directory(Location(file_item.full_path))

    def on_query_tooltip(self, widget, x, y, keyboard_tip, tooltip):
        '''Called before rendering the tooltip.'''

        y += self._get_y_location()
        thumbnail = self.album.find_thumbnail_at_pos((x, y))
        if thumbnail is None:
            return False

        file_item = thumbnail.get_file_item()
        if (self.last_tooltip_shown is not None and
            self.last_tooltip_shown != file_item.full_path):
            self.last_tooltip_shown = None
            return False

        self.last_tooltip_shown = file_item.full_path
        tooltip.set_text(file_item.name)
        return True

    def has_next_directory(self):
        '''Whether the list of next directories contains any elements.'''

        return len(self.next_locations) > 0

    def has_previous_directory(self):
        '''Whether the list of previous directories contains any elements.'''

        return len(self.previous_locations) > 0

    def go_to_next_directory(self):
        '''Go to the next directory, undoing the effect of
        go_to_previous_directory().'''

        if len(self.next_locations) > 0:
            self.previous_locations.append(self.location)
            self._change_directory(self.next_locations.pop())

    def go_to_previous_directory(self):
        '''Return back to the previous directory.'''

        if len(self.previous_locations) > 0:
            self.next_locations.append(self.location)
            self._change_directory(self.previous_locations.pop())

    def go_to_parent_directory(self):
        '''Add the current location to the previous list and go to the parent
        directory.
        '''

        parent_directory = os.path.join(self.location.path, os.path.pardir)
        self.next_locations = []
        self.previous_locations.append(self.location)
        self._change_directory(Location(parent_directory))

    def go_to_directory(self, location):
        '''Go to a new directory.'''

        self.next_locations = []
        self.previous_locations.append(self.location)
        self._change_directory(Location(location))

    def _change_directory(self, location):
        '''Internal function. Change directory without updating the previous
        and next lists.
        '''

        # Abort current rendering jobs. The user won't necessarily come back to
        # the parent directory and it may be too time consuming to generate all
        # the thumbnails in there.
        self.orchestrator.clear_queue()

        if not isinstance(location, Location):
            location = Location(location)

        self.location = location
        self._vadjustment.value = self._get_y_location()
        self._lay_out_album()
        self._update_scrollbars()
        self.call('directory_changed', location.path)
        self.queue_draw()

    def update_album(self):
        '''Redraw the browser view.'''
        self._lay_out_album()
        self._update_scrollbars()
        self.queue_draw()

    def zoom(self, new_exp, relative=True):
        '''Change the scale exponent used to scale thumbnails.'''
        cfg = self._config
        prev_scale_exp = cfg.get('thumb.scale_exp', 0.0, float)
        scale_exp = (prev_scale_exp if relative else 0.0) + new_exp
        prev_size = cfg.get('thumb.final_size')
        cfg.set('thumb.scale_exp', scale_exp)
        new_size = cfg.get('thumb.final_size')
        if new_size[0] == prev_size[0] or new_size[1] == prev_size[1]:
            # Scale had no effect: maybe scale is too small or too big.
            # Restore previous scale exponent and quit.
            cfg.set('thumb.scale_exp', prev_scale_exp)
            return
        self.update_album()
