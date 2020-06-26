# Copyright (C) 2020 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# System imports
import importlib.util as getutil
import os
import subprocess
import sys
from os.path import dirname, exists, join

# Blender imports
# NONE!

# Module imports
from .blender import get_addon_directory, b280


def get_blend_python_path():
    python_dir = join(os.__file__.split("lib" + os.sep)[0], "bin")
    python_name = next((f for f in os.listdir(python_dir) if f.startswith("python")), None)
    assert python_name is not None
    return join(python_dir, python_name)


def install_package(package_name:str, ensure_pip:bool=False, version:str=None):
    """ Install package via pip (use specific version number if passed) """
    python_path = get_blend_python_path()
    if ensure_pip and b280():
        subprocess.call([python_path, "-m", "ensurepip"])
    try:
        # target_folder = [p for p in sys.path if p.endswith("site-packages")][0]
        target_folder = join(dirname(get_addon_directory()), "modules")
        if not exists(target_folder):
            os.makedirs(target_folder)
        package_param = package_name + ("=={}".format(version) if version is not None else "")
        subprocess.call([python_path, "-m", "pip", "install", "--disable-pip-version-check", "--target={}".format(target_folder), package_param, "--ignore-install"])
    except:
        if b280() and not ensure_pip:
            install_package(package_name, ensure_pip=True)


def uninstall_package(package_name):
    python_path = get_blend_python_path()
    subprocess.call([python_path, "-m", "pip", "uninstall", "-y", package_name])
