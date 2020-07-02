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

# Blender imports
import bpy

# Module imports
from .bricksdict import *
from .brick import split_bricks
from .customize_utils import merge_bricks
from .make_bricks_utils import get_parent_keys


def improve_sturdiness(bricksdict, keys, cm, zstep, brick_type, merge_seed, iterations):
    # initialize last connectivity data
    iters_before_consistent = 3
    last_weak_points = [-1, -1]
    last_conn_comps = [-1, -1]
    print()
    # run sturdiness improvement iteratively
    for i in range(iterations):
        # reset 'attempted_merge' for all items in bricksdict
        for key0 in bricksdict:
            bricksdict[key0]["attempted_merge"] = False
        # get connectivity data
        conn_comps, weak_points, weak_point_neighbors, parent_keys = get_connectivity_data(bricksdict, zstep, keys, verbose=True)
        # set last connectivity vals
        last_weak_points.append(len(weak_points))
        last_conn_comps.append(len(conn_comps))
        # break if sturdy, or consistent for 3 iterations
        is_sturdy = len(conn_comps) == 1 and len(weak_points) == 0
        consistent_sturdiness = len(set(last_weak_points[-iters_before_consistent:])) <= 1 and len(set(last_conn_comps[-iters_before_consistent:])) <= 1
        if is_sturdy or consistent_sturdiness:
            break
        # get component interfaces
        # print("getting component interfaces...", end="")
        component_interfaces = get_component_interfaces(bricksdict, conn_comps, parent_keys, zstep)
        # print(len(component_interfaces))
        print()
        # improve sturdiness
        # split up bricks
        split_keys = set()
        for k in weak_points | weak_point_neighbors | component_interfaces:
            split_keys |= split_brick(bricksdict, k, zstep, brick_type)
        # get merge direction and sort order
        new_merge_seed = merge_seed + i + 1
        rand_state = np.random.RandomState(new_merge_seed)
        direction_mult = (int(rand_state.choice((1, -1))), int(rand_state.choice((1, -1))), int(rand_state.choice((1, -1))))
        axis_sort_order = [0, 1, 2]
        rand_state.shuffle(axis_sort_order)
        # sort_fn = lambda k: (str_to_list(k)[axis_sort_order[0]] * direction_mult[axis_sort_order[0]], str_to_list(k)[axis_sort_order[1]] * direction_mult[axis_sort_order[1]], str_to_list(k)[axis_sort_order[2]] * direction_mult[axis_sort_order[2]])
        sort_fn = lambda k: (str_to_list(k)[axis_sort_order[0]] * direction_mult[axis_sort_order[0]], str_to_list(k)[axis_sort_order[1]] * direction_mult[axis_sort_order[1]], str_to_list(k)[axis_sort_order[2]] * direction_mult[axis_sort_order[2]])

        # merge split bricks
        merged_keys = merge_bricks(bricksdict, split_keys, cm, merge_seed=new_merge_seed, target_type="BRICK" if brick_type == "BRICKS_AND_PLATES" else brick_type, any_height=brick_type == "BRICKS_AND_PLATES", direction_mult=direction_mult, sort_fn=sort_fn)

    # print the result
    if iterations > 0 and len(conn_comps) == 1 and len(weak_points) == 0:
        print("\nModel is fully stable!")
    else:
        # get the final components data
        print("\nResult:")
        conn_comps, weak_points, _, _ = get_connectivity_data(bricksdict, zstep, keys, get_neighbors=False, verbose=True)
        
    return conn_comps, weak_points


def get_connectivity_data(bricksdict, zstep, keys=None, get_neighbors=True, verbose=False):
    parent_keys = get_parent_keys(bricksdict, keys)
    # get connected components
    if verbose:
        print("getting connected components...", end="")
    conn_comps = get_connected_components(bricksdict, zstep, parent_keys)
    if verbose:
        print(len(conn_comps))
    # get weak articulation points
    if verbose:
        print("getting weak articulation points...", end="")
    # weak_points = get_bridges_recursive(conn_comps)
    weak_points = get_bridges(conn_comps)
    if verbose:
        print(len(weak_points))
    # get weak point neighbors
    if get_neighbors:
        # if verbose:
        #     print("getting weak point neighbors...", end="")
        weak_point_neighbors = get_weak_point_neighbors(bricksdict, weak_points, parent_keys, zstep)
        # if verbose:
        #     print(len(weak_point_neighbors))
    else:
        weak_point_neighbors = list()
    return conn_comps, weak_points, weak_point_neighbors, parent_keys
