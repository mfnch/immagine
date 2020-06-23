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

import sys

import numpy
import gi
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Pango, PangoCairo, GdkPixbuf, GLib
import cairo

(FORMAT_PIXBUF, FORMAT_ARRAY) = range(2)


class Icon(object):
    def __init__(self, size, out_format):
        self.width, self.height = size
        self.surface = s = cairo.ImageSurface(cairo.FORMAT_RGB24,
                                              self.width, self.height)
        self.context = cairo.Context(s)
        self.out_format = out_format

    def draw(self):
        pass

    def get_out_data(self):
        data = self.surface.get_data()
        data = numpy.array(data)
        data = numpy.fliplr(data.reshape(-1, 4))
        data = data.reshape(self.height, self.width, -1)
        data = data[:, :, 1:]
        if self.out_format == FORMAT_PIXBUF:
            data = GLib.Bytes.new(data.tobytes())
            return GdkPixbuf.Pixbuf.new_from_bytes(
                data, GdkPixbuf.Colorspace.RGB, False, 8,
                self.width, self.height, self.width * 3)
        return data


class TextIcon(Icon):
    def __init__(self, text, color, *args):
        super(TextIcon, self).__init__(*args)
        self.text = text
        self.color = color
        assert len(color) == 3, 'color should be a triple of float'

    def draw(self):
        ctx = self.context

        # Fill the image with white solid color.
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill_preserve()
        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(1)
        ctx.stroke()

        # Translates context so that desired text upperleft corner is at 0,0
        ctx.move_to(self.width // 10, self.height // 3)
        scale_factor = min(self.width, self.height) / 150.0
        ctx.scale(scale_factor, scale_factor)

        pangocairo_context = PangoCairo.create_context(ctx)
        #pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

        layout = PangoCairo.create_layout(ctx)
        fontname = "Sans"
        font = Pango.FontDescription(fontname + " 10")
        layout.set_font_description(font)

        layout.set_text(self.text)
        lg = cairo.LinearGradient(0, 0, self.width / scale_factor, 0)
        r, g, b = self.color
        lg.add_color_stop_rgba( 0.0, r, g, b, 0.0)
        lg.add_color_stop_rgba(0.05, r, g, b, 1.0)
        lg.add_color_stop_rgba(0.95, r, g, b, 1.0)
        lg.add_color_stop_rgba( 1.0, r, g, b, 0.0)
        ctx.set_source(lg)

        PangoCairo.update_layout(ctx, layout)
        PangoCairo.show_layout(ctx, layout)


def generate_text_icon(text, size, cache=False, color=(0, 0, 0),
                       out_format=FORMAT_ARRAY):
    icon = TextIcon(text, color, size, out_format)
    icon.draw()
    return icon.get_out_data()
