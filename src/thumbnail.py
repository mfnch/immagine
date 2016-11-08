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
import math

from .thumbnailers import open_image

class ThumbnailBase(object):
    def __init__(self, file_list_item):
        self.pos = None
        self.orig_size = None
        self.size = None
        self.file_list_item = file_list_item
        self.damaged = False

    def get_file_item(self):
        return self.file_list_item

    def contains(self, pos):
        '''Whether the given pixel is contained inside this thumbnail.'''
        return (self.pos[0] <= pos[0] < self.pos[0] + self.size[0] and
                self.pos[1] <= pos[1] < self.pos[1] + self.size[1])

    def compute_size(self, max_size):
        assert self.orig_size is not None
        x, y = self.orig_size
        mx, my = max_size
        ratio_x = mx/float(x)
        ratio_y = my/float(y)
        sz = ((int(math.ceil(x*ratio_y)), my) if ratio_x > ratio_y
              else (mx, int(math.ceil(y*ratio_x))))
        self.size = sz
        return sz

    def scale_to_width(self, new_width):
        '''Scale the image so that it has the specified with and keeps the same
        aspect ratio.'''
        new_height = new_width*self.size[1]/float(self.size[0])
        self.size = (int(round(new_width)), int(round(new_height)))

class ImageThumbnail(ThumbnailBase):
    def __init__(self, file_list_item):
        super(ImageThumbnail, self).__init__(file_list_item)

    def obtain_image_info(self):
        image = open_image(self.file_list_item.full_path)
        if image is not None:
            orig_size = image.size
            del image
        else:
            self.damaged = True
            orig_size = (100, 100)
        self.orig_size = orig_size

class DirectoryThumbnail(ThumbnailBase):
    '''Thumbnails for directories.
    In order to generate a thumbnail for a directory we do as follows:

    1. A directory thumbnail is a collage of the the thumbnails for the files
       contained in the directory.
    2. Up to 4 files are picked from the directory and are used to assemble the
       directory thumbnail. We may decide to use different criteria to select
       these pictures, from taking them randomly in the alphabetically or
       chronologically ordered list or even asking the user.
    3. The size of the thumbnail is decided before the directory content is
       accessed. This helps greatly to improve rendering speeds.
    4. In order to create the thumbnail we both scale and cut the pictures.
    '''
    def __init__(self, file_list_item):
        super(DirectoryThumbnail, self).__init__(file_list_item)

    def obtain_image_info(self):
        self.orig_size = (100, 100)
