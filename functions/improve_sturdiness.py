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
import math

# Blender imports
import bpy

# Module imports
from .bricksdict import *
from .brick import split_bricks
from .customize_utils import merge_bricks
from .make_bricks_utils import get_parent_keys


def improve_sturdiness(bricksdict, keys, cm, zstep, brick_type, merge_seed, iterations=42, model_subdivisions=0):
    # initialize last connectivity data
    iters_before_consistent = 4
    last_weak_points = [-1, -1]
    last_conn_comps = [-1, -1]
    # initialize vars
    lowest_conn_data = {"disconnected_parts": inf, "weak_points": inf}
    sturdiest_bricksdict = None
    keys_dict = get_keys_dict(bricksdict, keys)
    sorted_z_vals = sorted(keys_dict.keys())
    z_dist = math.ceil(len(sorted_z_vals) / (model_subdivisions + 1))
    print()
    # run sturdiness improvement iteratively
    for cur_iter in range(iterations + 1):
        # start iter
        component_interfaces = set()
        visited_zs = list()
        conn_comps, weak_points, weak_point_neighbors, parent_keys = get_connectivity_data(bricksdict, zstep, keys, verbose=True)
        print("getting component interfaces...", end="")
        for z in sorted_z_vals:
            if z in visited_zs:
                continue
            cur_keys = set()
            for j in range(z_dist):
                if z + j not in sorted_z_vals:
                    break
                cur_keys |= keys_dict[z + j]
                visited_zs.append(z + j)
            cur_parent_keys = get_parent_keys(bricksdict, cur_keys)
            bounds = lambda: None
            bounds.min = Vector((-1000, -1000, z))
            bounds.max = Vector((1000, 1000, visited_zs[-1]))
            # get component interfaces
            cur_conn_comps = get_connected_components(bricksdict, zstep, cur_parent_keys, subgraph_bounds=bounds)
            cur_component_interfaces = get_component_interfaces(bricksdict, cur_conn_comps, cur_parent_keys, zstep)
            # accumulate the component interfaces
            component_interfaces |= cur_component_interfaces
        print(len(cur_component_interfaces))
        print()
        # get ratios of current connectivity data to last connectivity data
        num_disconnected_parts = len(component_interfaces)  #get_num_disconnected_parts(conn_comps)
        disconnected_parts_ratio = 1 if num_disconnected_parts == lowest_conn_data["disconnected_parts"] == 0 else (num_disconnected_parts / max(0.5, lowest_conn_data["disconnected_parts"]))
        weak_points_ratio = 1 if len(weak_points) == lowest_conn_data["weak_points"] == 0 else len(weak_points) / max(0.5, lowest_conn_data["weak_points"])
        # check if this is the sturdiest model thusfar
        if cur_iter > min(100, iterations / 2) and (
            (disconnected_parts_ratio <= 1 and weak_points_ratio <= 1 and not weak_points_ratio == disconnected_parts_ratio == 1) or
            (weak_points_ratio > disconnected_parts_ratio and disconnected_parts_ratio < 0.95 / weak_points_ratio) or
            (disconnected_parts_ratio > weak_points_ratio and weak_points_ratio < 0.9 / disconnected_parts_ratio)
        ):
            print("cached...")
            lowest_conn_data["disconnected_parts"] = num_disconnected_parts
            lowest_conn_data["weak_points"] = len(weak_points)
            sturdiest_bricksdict = deepcopy(bricksdict)
        # set last connectivity vals
        last_weak_points.append(len(weak_points))
        last_conn_comps.append(len(conn_comps))
        # break if sturdy, or consistent for 3 iterations
        is_sturdy = len(conn_comps) == 1 and len(weak_points) == 0
        consistent_sturdiness = len(set(last_weak_points[-iters_before_consistent:])) <= 1 and len(set(last_conn_comps[-iters_before_consistent:])) <= 1
        if is_sturdy or consistent_sturdiness:  # (consistent_sturdiness and i > (iterations / 2 + iters_before_consistent)):
            break
        # break if we're at the last iteration (we don't want to do yet another merge if we're not going to check the connectivity data)
        if cur_iter == iterations:
            break
        # improve sturdiness
        # reset 'attempted_merge' for all items in bricksdict
        for key0 in bricksdict:
            bricksdict[key0]["attempted_merge"] = False
        # split up bricks
        split_keys = set()
        for k in weak_points | weak_point_neighbors | component_interfaces:
            split_keys |= split_brick(bricksdict, k, zstep, brick_type)
        # get merge direction and sort order
        new_merge_seed = merge_seed + cur_iter + 1
        rand_state = np.random.RandomState(new_merge_seed)
        direction_mult = (int(rand_state.choice((1, -1))), int(rand_state.choice((1, -1))), int(rand_state.choice((1, -1))))
        axis_sort_order = [0, 1, 2]
        rand_state.shuffle(axis_sort_order)
        # sort_fn = lambda k: (str_to_list(k)[axis_sort_order[0]] * direction_mult[axis_sort_order[0]], str_to_list(k)[axis_sort_order[1]] * direction_mult[axis_sort_order[1]], str_to_list(k)[axis_sort_order[2]] * direction_mult[axis_sort_order[2]])
        sort_fn = lambda k: (str_to_list(k)[axis_sort_order[0]] * direction_mult[axis_sort_order[0]], str_to_list(k)[axis_sort_order[1]] * direction_mult[axis_sort_order[1]], str_to_list(k)[axis_sort_order[2]] * direction_mult[axis_sort_order[2]])

        # merge split bricks
        merged_keys = merge_bricks(bricksdict, split_keys, cm, merge_seed=new_merge_seed, target_type="BRICK" if brick_type == "BRICKS_AND_PLATES" else brick_type, any_height=brick_type == "BRICKS_AND_PLATES", direction_mult=direction_mult, sort_fn=sort_fn)

    # replace bricksdict with the sturdiest one found
    if sturdiest_bricksdict is not None:
        # modify bricksdict in place so the pointer remains the same
        bricksdict.clear()
        bricksdict.update(sturdiest_bricksdict)

    # print the result
    if iterations > 0 and len(conn_comps) == 1 and len(weak_points) == 0:
        print("\nModel is fully stable!")
    else:
        # get the final components data
        print("\nResult:")
        conn_comps, weak_points, _, _ = get_connectivity_data(bricksdict, zstep, keys, get_neighbors=False, verbose=True)

    return conn_comps, weak_points


def get_num_disconnected_parts(conn_comps):
    return sum(len(cc) for cc in conn_comps) - max(len(cc) for cc in conn_comps)


def get_connectivity_data(bricksdict, zstep, keys=None, get_neighbors=True, subgraph_bounds=None, verbose=False):
    parent_keys = get_parent_keys(bricksdict, keys)
    # get connected components
    if verbose:
        print("getting connected components...", end="")
    conn_comps = get_connected_components(bricksdict, zstep, parent_keys, subgraph_bounds=subgraph_bounds)
    if verbose:
        print(len(conn_comps))
    # get weak articulation points
    if verbose:
        print("getting weak articulation points...", end="")
    weak_points = get_bridges(conn_comps, bricksdict, bounds=subgraph_bounds)
    if verbose:
        print(len(weak_points))
    # get weak point neighbors
    weak_point_neighbors = set()
    if get_neighbors:
        # if verbose:
        #     print("getting weak point neighbors...", end="")
        weak_point_neighbors |= get_weak_point_neighbors(bricksdict, weak_points, parent_keys, zstep)
        # if verbose:
        #     print(len(weak_point_neighbors))
    return conn_comps, weak_points, weak_point_neighbors, parent_keys
