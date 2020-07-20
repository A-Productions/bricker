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
from operator import itemgetter
import json

# Blender imports
import bpy
from bpy.props import *
from mathutils import Vector, Color

# Module imports
from .common import *

# Conditional imports
if b280():
    from bpy.types import Material, Image, Object, Collection
    types = {Material:"Material", Image:"Image", Object:"Object", Collection:"Collection"}
else:
    from bpy.types import Material, Image, Object, Group
    types = {Material:"Material", Image:"Image", Object:"Object", Group:"Group"}


def dump_cm_props(cm, skip_keys=[]):
    prop_dict = {}
    pointer_dict = {}

    for item in get_annotations(cm):
        if not item.islower() or item in skip_keys:
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

def match_properties(cm_to, cm_from):
    scn = bpy.context.scene
    cm_from_props = get_collection_props(cm_from)
    # remove properties that should not be copied
    props_to_remove = (
        "name",
        "id",
        "idx",
        "source_obj",
        "bevel_added",
        "model_loc",
        "model_rot",
        "model_scale",
        "parent_obj",
        "expose_parent",
        "apply_to_source_object",
    )
    # remove properties that should not be matched
    if not cm_from.bevel_added or not cm_to.bevel_added:
        cm_from_props.pop("bevel_width")
        cm_from_props.pop("bevel_segments")
        cm_from_props.pop("bevel_profile")
    # match material properties for Random/ABS Plastic Snapping
    mat_obj_names_from = ["Bricker_{}_RANDOM_mats".format(cm_from.id), "Bricker_{}_ABS_mats".format(cm_from.id)]
    mat_obj_names_to   = ["Bricker_{}_RANDOM_mats".format(cm_to.id), "Bricker_{}_ABS_mats".format(cm_to.id)]
    for i in range(2):
        mat_obj_from = bpy.data.objects.get(mat_obj_names_from[i])
        mat_obj_to = bpy.data.objects.get(mat_obj_names_to[i])
        if mat_obj_from is None or mat_obj_to is None:
            continue
        mat_obj_to.data.materials.clear()
        for mat in mat_obj_from.data.materials:
            mat_obj_to.data.materials.append(mat)
    # match properties from 'cm_from' to 'cm_to'
    set_collection_props(cm_to, cm_from_props)
