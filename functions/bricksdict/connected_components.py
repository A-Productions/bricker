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
# NONE!

# Blender imports
import bpy

# Module imports
from ..common import *
from ..general import *
from ..brick import *

# For reference on this implementation, see 2.2 of: https://lgg.epfl.ch/publications/2013/lego/lego.pdf


# @timed_call("Time Elapsed")
def get_connected_components(bricksdict:dict, zstep:int):
    cm = get_active_context_info()[1]
    conn_comps = list()
    parent_keys = set([k for k, brick_d in bricksdict.items() if brick_d["parent"] == "self" and brick_d["draw"]])
    while len(parent_keys) > 0:
        starting_key = parent_keys.pop()
        cur_conn_comp = dict()
        recurse_connected(bricksdict, starting_key, cur_conn_comp, zstep)
        # get difference of parent keys
        parent_keys -= set(cur_conn_comp.keys())
        # merge the resulting dict with the rest of the connected components
        conn_comps.append(cur_conn_comp)
        # conn_comp = {**conn_comp, **cur_conn_comp}
    return conn_comps


def recurse_connected(bricksdict:dict, key:str, conn_comp:dict, zstep:int):
    # base case
    if key in conn_comp:
        return
    # get locs in current brick
    loc = get_dict_loc(bricksdict, key)
    brick_size = bricksdict[key]["size"]
    locs_in_brick = get_locs_in_brick(bricksdict, brick_size, zstep, loc=loc)
    # find connected brick parent keys
    connected_brick_parent_keys = set()
    for loc0 in locs_in_brick:
        loc_neg = [loc0[0], loc0[1], loc0[2] - 1]
        parent_key_neg = get_parent_key(bricksdict, list_to_str(loc_neg))
        if parent_key_neg is not None and bricksdict[parent_key_neg]["draw"]:
            connected_brick_parent_keys.add(parent_key_neg)
        loc_pos = [loc0[0], loc0[1], loc0[2] + brick_size[2] // zstep]
        parent_key_pos = get_parent_key(bricksdict, list_to_str(loc_pos))
        if parent_key_pos is not None and bricksdict[parent_key_pos]["draw"]:
            connected_brick_parent_keys.add(parent_key_pos)
    # store connected bricks to new entry in 'conn_comp'
    conn_comp[key] = connected_brick_parent_keys
    # recurse through connected bricks
    for key in connected_brick_parent_keys:
        recurse_connected(bricksdict, key, conn_comp, zstep)


# @timed_call("Time Elapsed")
def get_weak_articulation_points(conn_comps:list):
    weak_points = set()
    for conn_comp in conn_comps:
        dfs_dict = dict()
        starting_key = next(iter(conn_comp.keys()))
        depth_first_search(conn_comp, weak_points, dfs_dict, 0, starting_key)
    return weak_points


# adapted from: https://emre.me/algorithms/tarjans-algorithm/
def depth_first_search(conn_comp:dict, weak_points:set, dfs_dict:dict, cur_idx:int, cur_node:str, last_node:str=""):
    if cur_node not in dfs_dict:
        dfs_dict[cur_node] = {"id": cur_idx, "low_link": cur_idx}
        cur_idx += 1
        for neighbor_node in conn_comp[cur_node]:
            cur_idx, low_link = depth_first_search(conn_comp, weak_points, dfs_dict, cur_idx, neighbor_node, cur_node)
            # add cur and neighbor nodes as weak articulation points if they bridge two non-trivial
            if dfs_dict[cur_node]["id"] < low_link and len(conn_comp[neighbor_node]) > 1:
                # weak_points.add(cur_node)
                weak_points.add(neighbor_node)
            # replace low link of current node if next node's low link is lower
            if low_link < dfs_dict[cur_node]["low_link"] and neighbor_node != last_node:
                dfs_dict[cur_node]["low_link"] = low_link
    return cur_idx, dfs_dict[cur_node]["low_link"]



# @timed_call("Time Elapsed")
def draw_connected_components(bricksdict:dict, conn_comps:list, weak_points:set, name:str="connected components"):
    bme = bmesh.new()
    # get bmesh vertices
    verts = dict()
    for conn_comp in conn_comps:
        for key in conn_comp:
            co = bricksdict[key]["co"]
            verts[key] = bme.verts.new(co)
            if key in weak_points:
                verts[key].select = True
    # get edge set
    edges = list()
    for conn_comp in conn_comps:
        for key in conn_comp:
            for conn_key in conn_comp[key]:
                edge = sorted([key, conn_key])
                if edge not in edges:
                    edges.append(edge)
    # get bmesh edges
    for k1, k2 in edges:
        bme.edges.new((verts[k1], verts[k2]))
    # create blender object from bmesh
    m = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, m)
    bme.to_mesh(m)
    # link object to scene
    bpy.context.scene.collection.objects.link(obj)