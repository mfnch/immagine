#!/usr/bin/env python

# Copyright 2017 Matteo Franchin
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
import sys
import logging
import json

def get_config_file_name():
    # For now we only support configurations on Unix.
    if sys.platform in ('win32', 'darwin'):
        return None
    base = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    return os.path.join(base, 'immagine', 'settings.json')

def get_config():
    fp = get_config_file_name()
    if not os.path.exists(fp):
        return Config()
    try:
        with open(fp, 'r') as f:
            content = f.read()
        return Config(json.loads(content), file_name=fp)
    except Exception as exc:
        logging.warn('Error while loading configuration from {}: {}'
                     .format(fp, str(exc)))
        return Config()


class Config(object):
    def __init__(self, config_dict=None, file_name=None):
        self.file_name = file_name
        self.config_dict = config_dict or {}

    @staticmethod
    def _unused_kwargs(**kwargs):
        raise TypeError('Unexpected keyword arguments {}'
                        .format(', '.join(kwargs.keys())))

    def _error(self, msg):
        if self.file_name is not None:
            msg = ('Error while reading {}: {}'
                   .format(self.file_name, msg))
        logging.warning(msg)

    def get(self, *args, **kwargs):
        default_value = kwargs.pop('default', None)
        of = kwargs.pop('of', None)
        if kwargs:
            self._unused_kwargs(kwargs)

        attrs = self.config_dict
        for arg in args:
            attrs = attrs.get(arg)
            if attrs is None:
                return default_value

        if (of is None or isinstance(attrs, of)):
            return attrs

        self._error('Invalid object for {}'.format('.'.join(args)))
        return default_value
