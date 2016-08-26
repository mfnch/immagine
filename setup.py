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

import os
from distutils.core import setup

setup(name='immagine',
      version='0.2',
      description='Image viewer and browser with directory thumbnails',
      author='Matteo Franchin',
      author_email='fnch@users.sf.net',
      license='Apache License, Version 2.0',
      url='https://github.com/mfnch/immagine',
      keywords=['image viewer', 'image browser', 'thumbnail'],
      classifiers=['Development Status :: 3 - Alpha',
                   'Topic :: Multimedia :: Graphics :: Viewers',
                   'License :: OSI Approved :: Apache Software License'],
      package_dir={'immagine': 'src'},
      packages=['immagine'],
      scripts=['scripts/immagine'])
