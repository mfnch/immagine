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

import sys

import numpy
import gtk
import cairo
import pango
import pangocairo

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
            return gtk.gdk.pixbuf_new_from_array(data,
                                                 gtk.gdk.COLORSPACE_RGB, 8)
        return data

class TextIcon(Icon):
    def __init__(self, text, *args):
        super(TextIcon, self).__init__(*args)
        self.text = text

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
        ctx.translate(10, 50)

        pangocairo_context = pangocairo.CairoContext(ctx)
        pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

        layout = pangocairo_context.create_layout()
        fontname = "Sans"
        font = pango.FontDescription(fontname + " 10")
        layout.set_font_description(font)

        layout.set_text(self.text)
        ctx.set_source_rgb(0, 0, 0)
        pangocairo_context.update_layout(layout)
        pangocairo_context.show_layout(layout)

def generate_text_icon(text, size, cache=False,
                       out_format=FORMAT_ARRAY):
    icon = TextIcon(text, size, out_format)
    icon.draw()
    return icon.get_out_data()
