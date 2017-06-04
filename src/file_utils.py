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

'''Generic utility for file sorting.'''

import os


class FileListItem(object):
    def __init__(self, index, is_dir, dir_path, name):
        self.index = index
        self.is_dir = is_dir
        self.dir_path = dir_path
        self.name = name
        self.full_path = os.path.join(dir_path, name)


class FileList(object):
    (SORT_BY_FILE_NAME,
     SORT_BY_MOD_DATE,
     SORT_BY_FILE_EXT,
     SORT_BY_FILE_SIZE,
     SORT_BY_IS_DIR) = range(5)

    @classmethod
    def build_key_generator(cls, sort_types, case_sensitive=False):
        adj = ((lambda x: x) if case_sensitive else (lambda x: x.lower()))

        gns = []
        for sort_type in sort_types:
            if sort_type == cls.SORT_BY_FILE_NAME:
                gn = lambda is_dir, fn: adj(os.path.split(fn)[-1])
            elif sort_type == cls.SORT_BY_FILE_EXT:
                gn = lambda is_dir, fn: adj(os.path.splitext(fn)[-1])
            elif sort_type == cls.SORT_BY_MOD_DATE:
                gn = lambda is_dir, fn: os.path.getmtime(fn)
            elif sort_type == cls.SORT_BY_FILE_SIZE:
                gn = lambda is_dir, fn: os.path.getsize(fn)
            elif sort_type == cls.SORT_BY_IS_DIR:
                gn = lambda is_dir, fn: (0 if is_dir else 1)
            else:
                continue
            gns.append(gn)

        def key_generator(item):
            return tuple(gn(*item) for gn in gns)
        return key_generator

    def __init__(self, dir_path, **kwargs):
        self.callbacks = []
        self.full_path = dir_path = os.path.realpath(dir_path)
        self.file_items = items = []
        for i, args in enumerate(get_files_in_dir(dir_path, **kwargs)):
            is_dir, name = args
            items.append(FileListItem(i, is_dir, dir_path, name))

    def __iter__(self):
        return iter(self.file_items)

    def __len__(self):
        return len(self.file_items)

    def __getitem__(self, idx):
        return self.file_items[idx]

    def register_callback(self, update_callback):
        self.callbacks.append(update_callback)


image_file_extensions = ('.jpeg', '.jpg', '.png', '.tif', '.xpm', '.bmp')

def list_dir(directory_path):
    '''Return the files in the directory or an empty list if the directory
    access fails.'''

    assert isinstance(directory_path, str)
    try:
        entries = os.listdir(directory_path)
    except Exception as x:
        return []
    return [os.path.join(directory_path, entry) for entry in entries]

def get_files_in_dir(directory_path, **kwargs):
    '''Return tuples (isdir, full_path) where isdir is a boolean indicating
    whether the item is a directory and full_path is the path to it.
    The following keyword arguments can be used:

    `file_extensions`: list of extensions of files to consider. Files with
      different extension are ignored.

    `sort_type`: how the files are sorted. Can be FileList.SORT_BY_FILE_NAME
      or another value of the same enumeration.

    `reversed_sort`: whether the sort order should be reversed. Default order
      is from smaller to bigger.
    '''
    return categorize_files(list_dir(directory_path), **kwargs)

def is_hidden(full_path):
    '''Whether the given file is hidden.'''
    return os.path.split(full_path)[-1].startswith('.')

def categorize_files(file_list, file_extensions=None, sort_type=None,
                     reversed_sort=False, show_hidden_files=True):
    '''Similar to get_files_in_dir, but uses the files in the list given as
    first argument, rather than obtaining the file list from a directory path.
    '''

    exts = file_extensions or image_file_extensions
    isdir_file_tuples = []
    for full_path in file_list:
        if not show_hidden_files and is_hidden(full_path):
            continue

        if not os.path.exists(full_path):
            continue

        isdir = os.path.isdir(full_path)
        if not isdir:
            ext = os.path.splitext(full_path)[1]
            if ext.lower() not in exts:
                continue
        isdir_file_tuples.append((isdir, full_path))

    # For now we only provide one sort type. Later we may want to provide a
    # tuple of sort types from the one which has the higher precedence to the
    # one which has the lowest precedence. Infrastructure for this is already
    # in place. Here we map the single sort order to a tuple which makes sense.
    if sort_type is not None:
        if sort_type == FileList.SORT_BY_FILE_NAME:
            sort_types = (sort_type,)
        else:
            sort_types = (sort_type, FileList.SORT_BY_FILE_NAME)

        key = FileList.build_key_generator(sort_types)
        isdir_file_tuples.sort(key=key, reverse=reversed_sort)
    return isdir_file_tuples

def pick_file_from_dir(directory_path, out_list, file_extensions=None,
                       **kwargs):
    '''Pick the first file in the given directory with the required extension.
    If a file is found, it is appended to out_list and True is returned.
    Otherwise False is returned.'''

    exts = file_extensions or image_file_extensions
    entries = get_files_in_dir(directory_path, **kwargs)
    for is_dir, entry_name in entries:
        if not is_dir:
            out_list.append(entry_name)
            return True
    for is_dir, entry_name in entries:
        assert is_dir
        if pick_file_from_dir(entry_name, out_list, **kwargs):
            return True
    return False

def choose_representatives(directory_path, num=4, **kwargs):
    if num < 1:
        return []

    file_list = list_dir(directory_path)
    all_entries = categorize_files(file_list, **kwargs)
    all_dirs = [entry for is_dir, entry in all_entries if is_dir]
    all_images = [entry for is_dir, entry in all_entries if not is_dir]

    # First, we want to determine whether this is a folder mostly containing
    # images or whether this folder contains all sorts of files. We want to
    # avoid scanning huge directories looking for images that they don't
    # contain. For example, if `directory_path` is the home folder, then we
    # want to avoid scanning any of its subfolders.
    n = len(file_list) - len(all_dirs)  # Num of non-image files.
    tol = 2                             # Num of non-image files we tolerate.
    image_content_ratio = ((len(all_images) + tol) * 100) // (n + tol)
    is_image_folder = (image_content_ratio > 60)

    # Pick at least one image from this directory.
    out = []
    if len(all_images) > 0:
        out.append(all_images.pop(0))
        if num == 1:
            return out

    if is_image_folder:
        # If available, pick all the other images from separate directories.
        step = max(1, len(all_dirs) // (num - len(out)))
        index = 0
        while len(all_dirs) > 0:
            index = index % len(all_dirs)
            candidate_dir = all_dirs.pop(index)
            index += step
            if (pick_file_from_dir(candidate_dir, out, **kwargs) and
                len(out) >= num):
                return out

    # Not enough directories, then pick the other images from this dir.
    assert num >= 1 and len(out) < num
    step = max(1, len(all_images) // (num - len(out)))
    index = step
    while len(all_images) > 0 and len(out) < num:
        index = index % len(all_images)
        out.append(all_images.pop(index))
        index += step
    return out
