""" setuptools/distutils hackery
"""
import json
import sys
import tempfile
from os import (
    getcwd,
    rename
)
from os.path import (
    exists,
    join
)
from subprocess import (
    CalledProcessError,
    check_call,
    check_output
)

try:
    from tempfile import TemporaryDirectory
except ImportError:
    from backports.tempfile import TemporaryDirectory

from ..io import (
    debug,
    error,
    info,
    warn
)
from ..util import (
    Archive,
    stringify_cmd
)


IMPORT_INTERFACE_WHEEL = 'import starforge.interface.wheel'
IMPORT_SETUPTOOLS = 'import setuptools'
WRAPPED_FILENAME = '__setup_wrapped_by_starforge.py'
SETUP_PY_WRAPPER = '''#!/usr/bin/env python
{import_interface_wheel}
{import_setuptools}
with open('{wrapped}') as f:
    code = compile(f.read(), '{wrapped}', 'exec')
exec(code)
'''

# FIXME: dedup
UNIVERSAL = 'universal'
PUREPY = 'purepy'
C_EXTENSION = 'c-extension'


def wrap_setup(package_dir=None, import_interface_wheel=False, import_setuptools=True):
    setup = 'setup.py'
    wrapped = WRAPPED_FILENAME
    if package_dir:
        setup = join(package_dir, setup)
        wrapped = join(package_dir, wrapped)
    if exists(wrapped):
        warn("Wrapped setup.py already exists, not overwriting: %s", wrapped)
        return
    rename(setup, wrapped)
    info("Wrapping setup.py: import_interface_wheel=%s, import_setuptools=%s", import_interface_wheel,
         import_setuptools)
    with open(setup, 'w') as fh:
        fh.write(SETUP_PY_WRAPPER.format(
            import_interface_wheel=IMPORT_INTERFACE_WHEEL if import_interface_wheel else '',
            import_setuptools=IMPORT_SETUPTOOLS if import_setuptools else '',
            wrapped=WRAPPED_FILENAME,
        ))


def check_setup(package_dir=None):
    package_dir = package_dir or getcwd()
    cmd = [sys.executable, 'setup.py', '--help-commands']
    out = _check_output(cmd, cwd=package_dir)
    for line in out.splitlines():
        try:
            if line.strip().split()[0] == 'bdist_wheel':
                debug("Package uses setuptools")
                return True
        except IndexError:
            pass
    return False


def wheel_type(package_dir=None):
    info = wheel_info(package_dir=package_dir)
    if not info:
        return None
    if info['purepy']:
        if info['universal']:
            return UNIVERSAL
        else:
            return PUREPY
    else:
        return C_EXTENSION


def wheel_info(package_dir=None):
    package_dir = package_dir or getcwd()
    wheel_info = None
    try:
        with tempfile.NamedTemporaryFile(mode='w+') as tfh:
            cmd = [sys.executable, 'setup.py', '-q', 'wheel_info', '--json', '--output', tfh.name]
            debug('Executing in %s: %s', package_dir, stringify_cmd(cmd))
            check_call(cmd, cwd=package_dir)
            wheel_info = json.load(tfh)
    except (CalledProcessError, ValueError) as exc:
        error("Failed to get wheel info: %s", exc)
    return wheel_info


def _check_output(cmd, cwd):
    debug('Executing in %s: %s', cwd, stringify_cmd(cmd))
    out = check_output(cmd, cwd=cwd)
    return out.decode('UTF-8')


class PythonSdist(Archive):
    @property
    def wheel_type(self):
        with TemporaryDirectory(prefix='starforge_sdist_wheel_type_') as td:
            debug("Extracting '%s' to '%s'", self._arcfile, td)
            self.extractall(td)
            root = join(td, self.root)
            return wheel_type(root)
