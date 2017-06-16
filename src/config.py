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

from .version import version

# Whether this is a development version of the app.
is_dev_version = version.rsplit('.', 1)[-1].startswith('dev')

# The main logger for the Immagine app.
logging.basicConfig()
logger = logging.getLogger('Immagine')

def setup_logging(loglevel=None):
    if loglevel is None:
        ll = (logging.DEBUG if is_dev_version else logging.WARNING)
    else:
        loglevel = loglevel.upper()
        if loglevel == 'SILENT':
            # Disable all logging.
            logging.disable(logging.CRITICAL)
            return
        ll = getattr(logging, loglevel, logging.WARN)
    logger.setLevel(ll)


class TypeChecker(object):
    '''Base class for checking types of configuration values.

    Type checkers can be given to Config.get() to check the value which is
    being retrieved from the configuration file. They should be given to the
    `of` keyword argument like this:

      v = cfg.get('a.b', of=TupleTypeChecker(2, float), default=(0, 0))

    If the configuration a.b has not the correct type, then a warning message
    is printed and the default value is returned.
    '''

    @staticmethod
    def wrap(v):
        if v is None:
            return (lambda instance: None)
        return (v if isinstance(v, TypeChecker) else PlainTypeChecker(v))

    def __call__(self, instance):
        return self.check(instance)


class PlainTypeChecker(TypeChecker):
    def __init__(self, expected_type, name=None):
        self._expected_type = expected_type
        self._name = name or expected_type.__name__
        super(PlainTypeChecker, self).__init__()

    def check(self, instance):
        if isinstance(instance, self._expected_type):
            return None
        return 'not a {}'.format(self._name)


class TupleTypeChecker(TypeChecker):
    def __init__(self, of=None, size=None, min_size=None, max_size=None):
        super(TupleTypeChecker, self).__init__()
        self._of = of
        self._min_size = (min_size if min_size is None else size)
        self._max_size = (max_size if max_size is None else size)

    def check(self, instance):
        if not isinstance(instance, (tuple, list)):
            return 'not a tuple'
        n = len(instance)
        if self._min_size is not None and n < self._min_size:
            return ('tuple is too short (len should be >= {})'
                    .format(self._min_size))
        if self._max_size is not None and n > self._max_size:
            return ('tuple is too long (len should be <= {})'
                    .format(self._max_size))
        checker = TypeChecker.wrap(self._of)
        for i, item in enumerate(instance):
            if checker(item) is not None:
                return ('wrong type for tuple item at pos {}'.format(i))
        return None


class ColorTypeChecker(TypeChecker):
    '''Type checker for color with form #rrggbb where rgb are hex digits.'''

    def __init__(self):
        super(ColorTypeChecker, self).__init__()

    def check(self, instance):
        if (isinstance(instance, (str, unicode)) and len(instance) == 7 and
            instance[0] == '#' and all(c in '0123456789abcdef'
                                       for c in instance[1:].lower())):
            return None
        return ('invalid color (expecting "#rrggbb" where rgb are hex '
                'digits for the red, green, blue components')


# Common type checker.
SCALAR = PlainTypeChecker((int, float), 'scalar')
SCALAR2 = TupleTypeChecker(SCALAR, 2)
INT2 = TupleTypeChecker(int, 2)
COLOR = ColorTypeChecker()


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

    def __init__(self):
        self._file_name = self.get_file_name()
        self._config_dict = {}
        self._override_dict = {}

    def load(self, file_name=None):
        fn = file_name or Config.get_file_name()
        if not os.path.exists(fn):
            logger.debug('File {} not found'.format(fn))
            return

        try:
            with open(fn, 'r') as f:
                content = f.read()
            config_dict = json.loads(content)
        except Exception as exc:
            logger.error('Cannot load configuration from {}: {}'
                         .format(fn, str(exc)))
            return

        self._file_name = file_name
        self._config_dict = config_dict

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
            logger.error('Cannot save configuration to {}: {}'
                         .format(fn, str(exc)))

    def _error(self, msg):
        if self._file_name is not None:
            msg = ('Error while reading {}: {}'
                   .format(self._file_name, msg))
        logger.error(msg)

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

        checker = TypeChecker.wrap(of)
        msg = checker(attrs)
        if msg is None:
            return attrs
        self._error('Invalid object for {}: {}'.format(name, msg))
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

    def get_color_triple(self, name, default=None, max_value=255.0):
        color_str = self.get(name, default, COLOR)
        if color_str is None:
            return color_str
        r = int(color_str[1:3], 16) / max_value
        g = int(color_str[3:5], 16) / max_value
        b = int(color_str[5:7], 16) / max_value
        return (r, g, b)
