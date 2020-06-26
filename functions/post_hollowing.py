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
import random
import time

# Blender imports
import bpy

# Module imports
from .bricksdict import *
from .brick import split_bricks
from .customize_utils import merge_bricks
from .improve_sturdiness import *
from .make_bricks_utils import *


def run_post_hollowing(bricksdict, keys, cm, zstep, brick_type, last_conn_comps, last_weak_points, remove_object=False):
    # TODO: Post-hollowing (see Section 3 of: https://lgg.epfl.ch/publications/2013/lego/lego.pdf)
    # get all parent keys of bricks exclusively inside the model
    internal_keys = get_parent_keys_internal(bricksdict, zstep, keys)
    # iterate through internal keys and attempt to remove
    removed_keys = set()
    for k in internal_keys:
        # pop the key from bricksdict
        keys_in_brick = get_keys_in_brick(bricksdict, bricksdict[k]["size"], zstep, key=k)
        popped_keys = dict()
        for k0 in keys_in_brick:
            popped_keys[k0] = bricksdict.pop(k0)
        # get connectivity data
        conn_comps, weak_points, _, _ = get_connectivity_data(bricksdict, zstep, get_neighbors=False)
        # check if conn_comps or weak_points are the same (if so, the key can stay removed)
        if len(conn_comps) <= len(last_conn_comps) and len(weak_points) <= len(last_weak_points):
            removed_keys |= popped_keys.keys()
            if remove_object:
                obj_name = popped_keys[k]["name"]
                delete(bpy.data.objects.get(obj_name))
            print("Successfully removed a brick!")
            continue
        # otherwise, put the key back
        for k1, v1 in popped_keys.items():
            bricksdict[k1] = v1

    return removed_keys
