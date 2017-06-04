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

def get_config():
    fp = Config.get_file_name()
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
    @staticmethod
    def get_file_name():
        # For now we only support configurations on Unix.
        if sys.platform in ('win32', 'darwin'):
            return None
        base = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        return os.path.join(base, 'immagine', 'settings.json')

    @staticmethod
    def _unused_kwargs(**kwargs):
        raise TypeError('Unexpected keyword arguments {}'
                        .format(', '.join(kwargs.keys())))

    def __init__(self, config_dict=None, file_name=None):
        self._file_name = file_name
        self._config_dict = config_dict or {}
        self._override_dict = {}

    def _build_config_dict(self, attrs, name=()):
        out = {}
        for key, val in attrs.items():
            if '.' not in key:
                new_name = name + (key,)
                if isinstance(val, dict):
                    out[key] = self._build_config_dict(val, new_name)
                else:
                    v = self.get('.'.join(new_name))
                    if v is not None:
                        out[key] = v
        return out

    def save(self):
        d = self._build_config_dict(self._config_dict)
        out = json.dumps(d, sort_keys=True, indent=4, separators=(',', ': '))
        fn = self.get_file_name()
        parent_dir = os.path.dirname(fn)
        try:
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            with open(fn, 'w') as f:
                f.write(out)
        except Exception as exc:
            logging.warning('Cannot save configuration to {}: {}'
                            .format(fn, str(exc)))

    def _error(self, msg):
        if self._file_name is not None:
            msg = ('Error while reading {}: {}'
                   .format(self._file_name, msg))
        logging.warning(msg)

    def override(self, name, getter, setter=None):
        assert getter is not None or setter is not None
        if '.' not in name:
            raise ValueError('Nothing to override')
        parent_name, attr_name = name.rsplit('.', 1)
        parent = self.get_container(parent_name)
        if getter is not None:
            parent[attr_name + '.get'] = getter
        if setter is not None:
            parent[attr_name + '.set'] = setter

    def get_container(self, name):
        container = self._config_dict
        args = name.split('.')
        for i, arg in enumerate(args):
            if (arg + '.get') in arg:
                raise ValueError("Cannot override `{}' of overriden "
                                 "container `{}'".format(name, args[:i]))
            container = container.setdefault(arg, {})
        return container

    def get(self, name, default=None, of=None):
        attrs = self._config_dict
        args = name.split('.')
        for i, arg in enumerate(args):
            overrider = attrs.get(arg + '.get')
            if overrider is not None:
                return overrider(attrs, args[i:])
            else:
                attrs = attrs.get(arg)
            if attrs is None:
                return default

        if (of is None or isinstance(attrs, of)):
            return attrs

        self._error('Invalid object for {}'.format(name))
        return default

    def set(self, name, value):
        attrs = self._config_dict
        args = name.split('.')
        last_arg = len(args) - 1
        for i, arg in enumerate(args):
            overrider = attrs.get(arg + '.set')
            if overrider is not None:
                overrider(attrs, args[i:], value)
                return
            if i == last_arg:
                attrs[arg] = value
                return
            attrs = attrs.setdefault(arg, {})
