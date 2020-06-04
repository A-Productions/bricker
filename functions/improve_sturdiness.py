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
import random

# Blender imports
import bpy

# Module imports
from .bricksdict import *
from .brick import split_bricks
from .customize_utils import merge_bricks
from .make_bricks_utils import get_parent_keys


def improve_sturdiness(bricksdict, cm, zstep, brick_type, merge_seed, iterations):
    keys = bricksdict.keys()
    if iterations == 0:
        parent_keys = get_parent_keys(bricksdict, keys)
        conn_comps = get_connected_components(bricksdict, zstep, parent_keys)
        weak_points, weak_point_neighbors = get_weak_articulation_points(bricksdict, conn_comps)
        return len(conn_comps), len(weak_points)
    num_last_weak_points = 0
    num_last_conn_comps = 0
    j = 0
    for i in range(iterations):
        # reset 'attempted_merge' for all items in bricksdict
        for key0 in bricksdict:
            bricksdict[key0]["attempted_merge"] = False
        # get all parent keys
        parent_keys = get_parent_keys(bricksdict, keys)
        # get connected components
        print("\ngetting connected components...", end="")
        conn_comps = get_connected_components(bricksdict, zstep, parent_keys)
        print(len(conn_comps))
        # get weak articulation points
        print("getting weak articulation points...", end="")
        weak_points, weak_point_neighbors = get_weak_articulation_points(bricksdict, conn_comps)
        print(len(weak_points))
        # get weak point neighbors
        weak_point_neighbors = set()
        for k in weak_points:
            neighboring_bricks = get_neighboring_bricks(bricksdict, bricksdict[k]["size"], zstep, get_dict_loc(bricksdict, k))
            weak_point_neighbors |= set(neighboring_bricks)
        # break if sturdy or consistent for 2 iterations
        is_sturdy = len(conn_comps) == 1 and len(weak_points) == 0
        consistent_sturdiness = len(weak_points) == num_last_weak_points and len(conn_comps) == num_last_conn_comps
        if is_sturdy or consistent_sturdiness:
            break
        # get component interfaces
        print("getting component interfaces...", end="")
        component_interfaces = get_component_interfaces(bricksdict, zstep, conn_comps)
        print(len(component_interfaces))
        # improve sturdiness
        # split up bricks
        split_keys = list()
        for k in weak_points | weak_point_neighbors | component_interfaces:
            split_keys += split_brick(bricksdict, k, zstep, brick_type)
        # get sort order
        new_merge_seed = merge_seed + i + 1
        direction_mult = (random.choice((1, -1)), random.choice((1, -1)), random.choice((1, -1)))
        sort_fn = lambda k: (str_to_list(k)[0] * direction_mult[0], str_to_list(k)[1] * direction_mult[1], str_to_list(k)[2] * direction_mult[2])
        # merge split bricks
        ct = time.time()
        merged_keys = merge_bricks(bricksdict, split_keys, cm, merge_seed=new_merge_seed, target_type="BRICK" if brick_type == "BRICKS_AND_PLATES" else brick_type, any_height=brick_type == "BRICKS_AND_PLATES", direction_mult=direction_mult, sort_fn=sort_fn)
        ct = stopwatch("merge", ct)
        # set last connectivity vals
        num_last_weak_points = len(weak_points)
        num_last_conn_comps = len(conn_comps)
    # return sturdiness info
    return len(conn_comps), len(weak_points)
