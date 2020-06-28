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
from .customize_utils import merge_bricks, reset_bricksdict_entries
from .improve_sturdiness import *
from .make_bricks_utils import *


# Reference: Section 3 of https://lgg.epfl.ch/publications/2013/lego/lego.pdf
def run_post_hollowing(bricksdict, keys, cm, zstep, brick_type, remove_object=False, subgraph_radius=4):
    """ Iterate over keys to remove any keys that don't create new disconnected componenets or weak points in a subgraph """
    # NOTE: Subgraphs larger than default of 4 are slower and may produce similar (or even worse) results. Smaller than 4 is inaccurate.
    # get all parent keys of bricks exclusively inside the model
    internal_keys = get_parent_keys_internal(bricksdict, zstep, keys)
    num_removed_bricks = 0
    # initialize progress bar
    old_percent = update_progress_bars(0.0, -1, "Post-Hollowing")
    # iterate through internal keys and attempt to remove
    removed_keys = set()
    for i, k in enumerate(internal_keys):
        # reset the key in bricksdict (and store vals before reset to popped_keys)
        keys_in_brick = get_keys_in_brick(bricksdict, bricksdict[k]["size"], zstep, key=k)
        popped_keys = dict()
        for k0 in keys_in_brick:
            popped_keys[k0] = bricksdict[k0].copy()
        # find key connected to this brick to start subgraph from
        conn_keys = get_connected_keys(bricksdict, k, zstep)
        if conn_keys:
            k1 = conn_keys.pop()
            # get connectivity data starting at current key
            last_conn_comp = iterative_get_connected(bricksdict, k1, zstep, max_dist=subgraph_radius)
            last_weak_points = get_bridges([last_conn_comp])
            # reset entries in bricksdict
            reset_bricksdict_entries(bricksdict, keys_in_brick)
            # get connectivity data again starting at current key
            conn_comp = iterative_get_connected(bricksdict, k1, zstep, max_dist=subgraph_radius)
            weak_points = get_bridges([conn_comp])
        # check if conn_comps or weak_points are the same (if so, the key can stay removed)
        if conn_keys and (len(conn_comp) >= len(last_conn_comp) - 1 and len(weak_points) <= len(last_weak_points)):
            removed_keys |= popped_keys.keys()
            num_removed_bricks += 1
            if remove_object:
                obj_name = popped_keys[k]["name"]
                delete(bpy.data.objects.get(obj_name))
        # else, the keys must be put back
        else:
            for k0 in popped_keys:
                bricksdict[k0] = popped_keys[k0]
        # print status to terminal and cursor
        cur_percent = (i / len(internal_keys))
        old_percent = update_progress_bars(cur_percent, old_percent, "Post-Hollowing")
    # end progress bar
    update_progress_bars(1, 0, "Post-Hollowing", end=True)
    # return all removed keys (including all keys in brick) along with num removed bricks
    return removed_keys, num_removed_bricks
