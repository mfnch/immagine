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
from setuptools import setup

script_path = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(script_path, 'README.rst')
with open(readme_path, 'r') as f:
    long_description = f.read()

setup(name='immagine',
      version='0.3',
      description='Image viewer and browser with directory thumbnails',
      long_description=long_description,
      author='Matteo Franchin',
      author_email='fnch@users.sf.net',
      license='Apache License, Version 2.0',
      url='https://github.com/mfnch/immagine',
      keywords=['image viewer', 'image browser', 'thumbnail'],
      classifiers=['Programming Language :: Python :: 2',
                   'Programming Language :: Python :: 2.7',
                   'Development Status :: 3 - Alpha',
                   'Topic :: Multimedia :: Graphics :: Viewers',
                   'License :: OSI Approved :: Apache Software License'],
      package_dir={'immagine': 'src'},
      packages=['immagine'],
      scripts=['scripts/immagine'])
