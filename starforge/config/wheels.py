"""
Read wheel forging config
"""
from __future__ import absolute_import

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import yaml
from six import iteritems, string_types


DEFAULT_IMAGESET = 'default-wheel'
DEFAULT_PUREPY_IMAGESET = 'purepy-wheel'
DEFAULT_UNIVERSAL_IMAGESET = 'universal-wheel'
DEFAULT_CONFIG_FILE = 'wheels.yml'

# FIXME: dedup
UNIVERSAL = 'universal'
PUREPY = 'purepy'
C_EXTENSION = 'c-extension'


class WheelConfig(object):
    def __init__(self, name, global_config, config, imagesets, purepy=None, universal=None):
        if purepy is False and universal is True:
            fatal("ERROR: Wheel '%s' set purepy = False, universal = True, which is impossible")
        self.name = name
        self.config = config
        self.purepy = purepy if purepy is not None else universal
        self.universal = universal
        self.version = str(config['version'])
        self.sources = config.get('src', [])
        self.prebuild = config.get('prebuild', None)
        self.insert_setuptools = config.get('insert_setuptools', None)
        self.force_pythons = config.get('force_pythons', None)
        self.build_args = config.get('build_args', 'bdist_wheel')
        self.buildpy = config.get('buildpy', 'python')
        self.skip_tests = config.get('skip_tests', [])
        self.auditwheel_args = config.get('auditwheel_args', None)
        self.delocate_args = config.get('delocate_args', None)
        self.imagesets = imagesets
        self.configured_imageset = config.get('imageset')
        self.configured_wheel_type = None
        if self.universal:
            self.configured_wheel_type = UNIVERSAL
        elif self.purepy:
            self.configured_wheel_type = PUREPY
        elif self.purepy is False:
            # explicitly set to false means it's being declared as C extension
            self.configured_wheel_type = C_EXTENSION
        self.set_imageset()

    def set_imageset(self, imageset=None, force=False):
        if self.configured_imageset is not None and not force:
            # do not override configured_imageset
            imageset = self.configured_imageset
        elif imageset is None:
            if self.universal:
                imageset = DEFAULT_UNIVERSAL_IMAGESET
            elif self.purepy:
                imageset = DEFAULT_PUREPY_IMAGESET
            else:
                imageset = DEFAULT_IMAGESET
        if isinstance(imageset, string_types):
            imageset = self.imagesets[imageset]
        self.imageset = imageset
        self.images = self.imageset.images

    def set_purepy(self, purepy):
        self.purepy = purepy
        self.universal = False if purepy is False else self.universal

    def set_universal(self, universal):
        self.purepy = True if universal else self.purepy
        self.universal = universal

    def get_images(self):
        return self.images

    def get_image(self, name):
        return self.images[name]

    def get_dependencies(self, image):
        if image is None:
            return []
        pkgtool = self.images[image].pkgtool
        return self.config.get(pkgtool, [])


class WheelConfigManager(object):
    @classmethod
    def open(cls, global_config, config_file):
        return cls(global_config, config_file=config_file)

    def __init__(self, global_config, config_file=None):
        self.global_config = global_config
        self.__config_file = config_file
        self.config = None
        self.wheels = OrderedDict()
        self.load_config()

    @property
    def config_file(self):
        if self.__config_file is None:
            return DEFAULT_CONFIG_FILE
        return self.__config_file

    def load_config(self):
        self.config = yaml.safe_load(open(self.config_file).read())
        config_type = self.config.get('type', 'wheels')
        if config_type == 'wheels':
            for (name, wheel) in iteritems(self.config['packages']):
                self.wheels[name] = WheelConfig(name, self.global_config, wheel,
                                                self.global_config.imagesets,
                                                purepy=False)
            for (name, wheel) in iteritems(self.config['purepy_packages']):
                self.wheels[name] = WheelConfig(name, self.global_config, wheel,
                                                self.global_config.imagesets,
                                                purepy=True)
        elif config_type == 'wheel':
            name = self.config['name']
            self.wheels[name] = WheelConfig(name, self.global_config, self.config, self.global_config.imagesets,
                                            purepy=self.config.get('purepy', None))

    def get_wheel_config(self, name):
        return self.wheels[name]

    def get_wheel_images(self, name):
        return self.get_wheel_config(name).get_images()

    def __iter__(self):
        for name, wheel in iteritems(self.wheels):
            yield name, wheel

    def __getitem__(self, name):
        return self.wheels[name]

    def __contains__(self, name):
        return name in self.wheels
