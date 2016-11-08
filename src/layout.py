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
import itertools

from .file_utils import get_files_in_dir
from .thumbnail import ImageThumbnail, DirectoryThumbnail

class ImageAlbumRow(object):
    def __init__(self, max_width, image=None):
        self.pos = None
        self.size = None
        self.images = []
        self.row_width = 0
        self.max_width = max_width
        self.borders = []

        if image is not None:
            self.images.append(image)
            self.row_width += image.size[0]

    def __iter__(self):
        return iter(self.images)

    def empty(self):
        return len(self.images) == 0

    def try_add(self, image, border=0):
        image_width = image.size[0]
        gap = (0 if len(self.images) == 0 else border)
        new_row_width = self.row_width + gap + image_width
        if new_row_width > self.max_width:
            return False
        self.row_width = new_row_width
        self.borders.append(border)
        self.images.append(image)
        return True

    def expand(self):
        if len(self.images) == 0 or self.row_width < 1:
            return

        n = len(self.images)
        total_border = sum(self.borders)
        scale_factor = \
          (self.max_width - total_border)/float(self.row_width - total_border)

        # Rescale all images.
        row_width = 0
        for image in self.images:
            new_width = scale_factor*image.size[0]
            image.scale_to_width(new_width)
            row_width += new_width
        self.row_width = row_width

        # Compute the new borders.
        num_borders_left = len(self.borders)
        total_border = self.max_width - row_width
        borders = []
        while num_borders_left > 0:
            border = int(round(total_border/num_borders_left))
            borders.append(border)
            total_border -= border
            num_borders_left -= 1
        self.borders = borders

    def lay_out(self, pos):
        x, y = self.pos = pos
        width = 0
        height = 0
        for i, image in enumerate(self.images):
            image.pos = (x + width, y)
            height = max(height, image.size[1])
            width += image.size[0] + (self.borders[i] if i < len(self.borders)
                                      else 0)
        self.size = (width, height)

class ImageAlbum(object):
    def __init__(self, file_list, max_width=1200, border=(5, 5)):
        self.rows = []
        self.border = border
        for row in lay_out_images(file_list,
                                  max_width=max_width,
                                  border=border[0]):
            self.add(row)

    def get_height(self):
        if len(self.rows) == 0:
            return 0.0
        last_row = self.rows[-1]
        return ((last_row.pos[1] + last_row.size[1] - self.rows[0].pos[1])
                if len(self.rows) > 0 else None)

    def add(self, row):
        if len(self.rows) > 0:
            last_row = self.rows[-1]
            pos = (last_row.pos[0],
                   last_row.pos[1] + last_row.size[1] + self.border[1])
        else:
            pos = (0, 0)
        row.lay_out(pos)
        self.rows.append(row)

    def find_row_at_y(self, y):
        '''Find the row containing the given y coordinate. Return the index of
        the row or None if no row was found.'''
        rows = self.rows
        if len(rows) < 1:
            return None

        last_row = rows[-1]
        if not (rows[0].pos[1] <= y < last_row.pos[1] + last_row.size[1]):
            return None

        # Bisection search.
        lo = 0
        hi = len(rows)
        while lo + 1 < hi:
            mid = (lo + hi)//2
            if y < rows[mid].pos[1]:
                hi = mid
            else:
                lo = mid
        return lo

    def find_thumbnail_at_pos(self, pos):
        '''Find the thumbnail at the give position. Return None in case the
        thumbnail is not found.'''
        row_index = self.find_row_at_y(pos[1])
        if row_index is None:
            return None
        for thumbnail in self.rows[row_index]:
            if thumbnail.contains(pos):
                return thumbnail
        return None

    def get_rows(self, y, height):
        '''Get a list of rows inside the interval [y, y + height[.'''
        first_row = self.find_row_at_y(y)
        if first_row is None:
            return []
        last_row = first_row
        rows = self.rows
        y_end = y + height
        while last_row < len(rows):
            lr = rows[last_row]
            if lr.pos[1] + lr.size[1] >= y_end:
                break
            last_row += 1
        return rows[first_row:last_row + 1]

    def get_thumbnails(self, x, y, width, height):
        '''Get a list of images inside the given region.'''
        images = []
        x_end = x + width
        for row in self.get_rows(y, height):
            for image in row.images:
                ix = image.pos[0]
                if ix + image.size[0] >= x and ix < x_end:
                    images.append(image)
        return images

def lay_out_images(file_list, border=2, max_width=1200, max_size=(400, 150)):
    subdirs = []
    images = []

    # Find all images and subdirectories that we will have to display.
    for file_item in file_list:
        # Deal with directories separately.
        if file_item.is_dir:
            subdirs.append(DirectoryThumbnail(file_item))
        else:
            # Filter files by extension.
            images.append(ImageThumbnail(file_item))

    # Create the image layout, row by row.
    row = ImageAlbumRow(max_width)
    for image in itertools.chain(subdirs, images):
        # Get the size of the image and compute the thumbnail size.
        image.obtain_image_info()
        image.compute_size(max_size)

        # Try adding the image to the row, or send the old row via the call
        # back and create a new row.
        if not row.try_add(image, border=border):
            row.expand()
            yield row
            row = ImageAlbumRow(max_width, image)

    if not row.empty():
        yield row
