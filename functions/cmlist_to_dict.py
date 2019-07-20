# Copyright (C) 2019 Christopher Gearhart
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
import json

# Blender imports
import bpy
from mathutils import Vector, Color

# Addon imports
from .common import *

# Conditional imports
if b280():
    from bpy.types import Material, Image, Object, Collection
    types = {Material:"Material", Image:"Image", Object:"Object", Collection:"Collection"}
else:
    from bpy.types import Material, Image, Object, Group
    types = {Material:"Material", Image:"Image", Object:"Object", Group:"Group"}


def dump_cm_props(cm):
    prop_dict = {}
    pointer_dict = {}

    for item in get_annotations(cm):
        if not item.islower() or item in ["active_key", "bfm_cache"]:
            continue
        try:
            item_prop = getattr(cm, item)
        except:
            continue
        item_type = type(item_prop)
        if item_type in types.keys():
            pointer_dict[item] = {"name":item_prop.name, "type":types[item_type]}
            continue
        if item_type in (Vector, Color):
            item_prop = tuple(item_prop)
        prop_dict[item] = item_prop
    return prop_dict, pointer_dict


def load_cm_props(cm, prop_dict, pointer_dict):
    for item in prop_dict:
        setattr(cm, item, prop_dict[item])
    for item in pointer_dict:
        name = pointer_dict[item]["name"]
        typ = pointer_dict[item]["type"]
        data = getattr(bpy.data, typ.lower() + "s")[name]
        setattr(cm, item, data)
