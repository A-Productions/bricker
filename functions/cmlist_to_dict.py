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

# # Addon imports
# from .common import *
#
# # Conditional imports
# if b280():
#     from bpy.types import Material, Image, Object, Collection
#     types = {Material:"Material", Image:"Image", Object:"Object", Collection:"Collection"}
# else:
#     from bpy.types import Material, Image, Object, Group
#     types = {Material:"Material", Image:"Image", Object:"Object", Group:"Group"}
from bpy.types import Material, Image, Object, Collection
types = {Material:"Material", Image:"Image", Object:"Object", Collection:"Collection"}


def dump_cm_props(cm):
    prop_dict = {}
    pointer_dict = {}

    for item in dir(cm):
        if item.startswith("__") or not item.islower() or item in ["bl_rna", "rna_type", "active_key", "bfm_cache"]:
            continue
        item_prop = getattr(cm, item)
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


# scn = bpy.context.scene
# cm0 = scn.cmlist[scn.cmlist_index]
# prop_dict, pointer_dict = dump_cm_props(cm0)
#
# bpy.ops.cmlist.list_action(action="ADD")
# cm1 = scn.cmlist[-1]
# load_cm_props(cm1, prop_dict, pointer_dict)

# # Print helpful information
# props = {}
# for item in cm_dict:
#     item_prop = cm_dict[item]
#     item_type = type(item_prop)
#     if type(item_prop) in props:
#         props[item_type] += 1
#     else:
#         props[item_type] = 1
# print()
# for key in props:
#     print(key, props[key])
#
# print()
# print(pointer_dict)
# print(json.dumps(prop_dict))
