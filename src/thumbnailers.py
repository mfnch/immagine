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
import numpy
import PIL.Image
import gtk

from . import icons
from .file_utils import pick_files
from .config import logger

def open_image(file_name, load=False):
    try:
        img = PIL.Image.open(file_name)
        if load:
            img.load()
        return img
    except:
        return None

def build_empty_thumbnail(size):
    sx, sy = size
    pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, sx, sy)
    pixbuf.fill(0x7f7f7f7f)
    pixbuf.subpixbuf(1, 1, sx - 2, sy - 2).fill(0xffffffff)
    return pixbuf

def to_rgb(image, bg=(127, 127, 127)):
    if image.mode != 'RGB':
        image = image.convert('RGBA')
        background = PIL.Image.new('RGBA', image.size, bg)
        image = PIL.Image.alpha_composite(background, image).convert('RGB')
    return image

def build_image_thumbnail(image_path, size):
    try:
        image = PIL.Image.open(image_path)
        image.thumbnail(size)
    except:
        return None

    if image.size != size:
        logger.debug('got {}, required {}'.format(image.size, size))
    return numpy.array(to_rgb(image))

def build_directory_thumbnail(dir_path, size, **kwargs):
    kwargs.setdefault('show_hidden_files', False)
    num_picks = kwargs.setdefault('num_picks', 4)

    tx, ty = (100, 100)
    thumbnail_aspect = float(tx)/ty
    scale_factor = (float(size[0])/tx if thumbnail_aspect > 1.0
                    else float(size[1])/ty)
    images = []
    for image_path in pick_files(dir_path, **kwargs):
        orig_image = open_image(image_path, load=True)
        if orig_image is None:
            continue

        images.append(to_rgb(orig_image))
        if len(images) == num_picks:
            break

    if len(images) == 0:
        dir_name = os.path.split(dir_path)[-1]
        return icons.generate_text_icon(dir_name, size, cache=True)

    layouts = \
      [[],
       [((0, 0), (100, 100))],
       [((0, 0), (100, 50)),
        ((0, 50), (100, 50))],
       [((0, 0), (100, 50)),
        ((0, 50), (50, 50)),
        ((50, 50), (50, 50))],
       [((0, 0), (50, 50)),
        ((50, 0), (50, 50)),
        ((0, 50), (50, 50)),
        ((50, 50), (50, 50))]]
    layout = layouts[len(images)]
    out = build_empty_thumbnail(size)
    for i, image in enumerate(images):
        dest_pos, dest_size = layout[i]
        dx = int(round(dest_size[0]*scale_factor))
        dy = int(round(dest_size[1]*scale_factor))
        dpx = int(round(dest_pos[0]*scale_factor))
        dpy = int(round(dest_pos[1]*scale_factor))
        dest_aspect = float(dest_size[0])/dest_size[1]

        ox, oy = image.size
        orig_aspect = float(ox)/oy

        # Cut a part of the original image which has the same aspect ratio
        # as our destination space in the thumbnail and is as big as
        # possible.
        cut_size = ((ox, int(round(dy*ox/dx)))
                    if dest_aspect >= orig_aspect
                    else (int(round(dx*oy/dy)), oy))
        cut_pos = ((ox - cut_size[0])//2, (oy - cut_size[1])//2)
        cut_image = image.crop((cut_pos[0], cut_pos[1],
                                cut_pos[0] + cut_size[0],
                                cut_pos[1] + cut_size[1]))
        cut_image.thumbnail((dx, dy))
        arr = numpy.array(cut_image)
        if arr.ndim != 3 or arr.dtype != numpy.uint8 or arr.shape[-1] != 3:
            continue
        cut_pixmap = \
          gtk.gdk.pixbuf_new_from_array(arr, gtk.gdk.COLORSPACE_RGB, 8)
        width = min(cut_pixmap.get_width(), size[0] - dpx)
        height = min(cut_pixmap.get_height(), size[1] - dpy)
        cut_pixmap.copy_area(0, 0, width, height, out, dpx, dpy)

    return out.get_pixels_array().copy()
