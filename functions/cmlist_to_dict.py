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
else:
    from bpy.types import Material, Image, Object, Group


scn = bpy.context.scene
cm0 = scn.cmlist[scn.cmlist_index]


if b280():
    types = {Material:"Material", Image:"Image", Object:"Object", Collection:"Collection"}
else:
    types = {Material:"Material", Image:"Image", Object:"Object", Group:"Group"}

def build_dict(cm):
    cm_dict = {}
    objs = {}

    for item in dir(cm):
        if item in ["__annotations__", "__dict__", "__doc__", "__module__", "__weakref__", "bl_rna", "rna_type", "active_key", "bfm_cache"]:
            continue
        item_prop = getattr(cm, item)
        item_type = type(item_prop)
        if item_type in types.keys():
            objs[item] = {"name":item_prop.name, "type":types[item_type]}
            continue
        if item_type in (Vector, Color):
            item_prop = tuple(item_prop)
        cm_dict[item] = item_prop
    return cm_dict, objs

cm_dict, objs = build_dict(cm0)

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


print()
print(objs)
print(json.dumps(cm_dict))
