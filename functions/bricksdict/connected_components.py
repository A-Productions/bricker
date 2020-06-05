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
def get_connected_components(bricksdict:dict, zstep:int, parent_keys:list):
    cm = get_active_context_info()[1]
    conn_comps = list()
    parent_keys = set(parent_keys)
    while len(parent_keys) > 0:
        # get a starting key from the list
        starting_key = parent_keys.pop()
        # get connected components for that starting key
        cur_conn_comp = dict()
        next_parent_keys = [starting_key]
        while len(next_parent_keys) > 0:
            connected_parent_keys = next_parent_keys
            next_parent_keys = list()
            for k0 in connected_parent_keys:
                if k0 in cur_conn_comp:
                    continue
                keys_connected_to_k0 = get_connected_keys(bricksdict, k0, cur_conn_comp, zstep)
                cur_conn_comp[k0] = keys_connected_to_k0
                next_parent_keys += keys_connected_to_k0
        # remove keys in current conn_comp list from parent_keys
        parent_keys -= set(cur_conn_comp.keys())
        # add current conn_comp to list of conn_comps
        conn_comps.append(cur_conn_comp)
        # conn_comp = {**conn_comp, **cur_conn_comp}
    return conn_comps


def get_connected_keys(bricksdict:dict, key:str, conn_comp:dict, zstep:int):
    # get locs in current brick
    loc = get_dict_loc(bricksdict, key)
    brick_size = bricksdict[key]["size"]
    lowest_locs_in_brick = get_lowest_locs_in_brick(brick_size, loc)
    # find connected brick parent keys
    connected_brick_parent_keys = set()
    for loc0 in lowest_locs_in_brick:
        loc_neg = [loc0[0], loc0[1], loc0[2] - 1]
        parent_key_neg = get_parent_key(bricksdict, list_to_str(loc_neg))
        if parent_key_neg is not None and bricksdict[parent_key_neg]["draw"]:
            connected_brick_parent_keys.add(parent_key_neg)
        # make sure key doesn't reference itself as neighbor (for debugging purposes)
        # NOTE: if assertion hit, that probably means that the 'bricksdict[list_to_str(loc_neg)]["size"]' was set improperly before entering this function
        assert parent_key_neg != key
        loc_pos = [loc0[0], loc0[1], loc0[2] + brick_size[2] // zstep]
        parent_key_pos = get_parent_key(bricksdict, list_to_str(loc_pos))
        if parent_key_pos is not None and bricksdict[parent_key_pos]["draw"]:
            connected_brick_parent_keys.add(parent_key_pos)
        # make sure key doesn't reference itself as neighbor (for debugging purposes)
        # NOTE: if assertion hit, that probably means that the 'bricksdict[list_to_str(loc_pos)]["size"]' was set improperly before entering this function
        assert parent_key_pos != key
    return connected_brick_parent_keys


# # @timed_call("Time Elapsed")
# def get_weak_articulation_points(bricksdict:dict, conn_comps:list):
#     weak_points = set()
#     weak_point_neighbors = set()
#     for conn_comp in conn_comps:
#         # get starting key from the list
#         starting_key = next(iter(conn_comp.keys()))
#         # visit nearby verts for that starting key
#         i = 0
#         node_infos = dict()  # used to find weak points then discarded
#         visited = [starting_key]
#         while len(visited) > 0:
#             queued = visited
#             visited = list()
#             for cur_node in queued:
#                 if neighbor not in node_infos:
#                     node_infos[cur_node] = {"id": cur_idx, "low_link": cur_idx}
#                     i += 1
#                     for neighbor_node in conn_comp[cur_node]:
#                         i, low_link = depth_first_search(bricksdict, conn_comp, weak_points, weak_point_neighbors, node_infos, i, neighbor_node, cur_node)
#     return weak_points, weak_point_neighbors
#
#
# # adapted from: https://emre.me/algorithms/tarjans-algorithm/
# def depth_first_search(bricksdict:dict, conn_comp:dict, weak_points:set, weak_point_neighbors:set, node_infos:dict, cur_idx:int, cur_node:str, last_node:str=""):
#     # add cur and neighbor nodes as weak articulation points if they bridge two non-trivial components
#     if node_infos[cur_node]["id"] < low_link and len(conn_comp[neighbor_node]) > 1:
#         # weak_points.add(cur_node)
#         weak_points.add(neighbor_node)
#         # # get verts neighboring weak point
#         # neighboring_bricks = get_neighboring_bricks(bricksdict, bricksdict[neighbor_node]["size"], zstep, get_dict_loc(bricksdict, neighbor_node))
#         # for k in neighboring_bricks:
#         #     if k not in conn_comp:
#         #         weak_point_neighbors.add(k)
#     # replace low link of current node if next node's low link is lower
#     if low_link < node_infos[cur_node]["low_link"] and neighbor_node != last_node:
#         node_infos[cur_node]["low_link"] = low_link
#     return cur_idx, node_infos[cur_node]["low_link"]


def get_weak_articulation_points(conn_comps:list):
    """ get both 'nodes' at each bridge connecting two non-trivial components """
    weak_points = set()
    for conn_comp in conn_comps:
        node_infos = dict()
        starting_key = next(iter(conn_comp.keys()))
        depth_first_search(conn_comp, weak_points, node_infos, 0, starting_key)
    return weak_points


# adapted from: https://emre.me/algorithms/tarjans-algorithm/
def depth_first_search(conn_comp:dict, weak_points:set, node_infos:dict, cur_idx:int, cur_node:str, last_node:str=""):
    # trying to visit an already visited node, which may have a lower id than the current low link value
    if cur_node in node_infos:
        return cur_idx, node_infos[cur_node]["low_link"]
    # initialize info for current node
    node_infos[cur_node] = {"id": cur_idx, "low_link": cur_idx}
    cur_idx += 1
    # iterate through nodes connected to current node
    for neighbor_node in conn_comp[cur_node]:
        # skip if checking last node
        if neighbor_node == last_node:
            continue
        # recurse dfs
        cur_idx, low_link = depth_first_search(conn_comp, weak_points, node_infos, cur_idx, neighbor_node, cur_node)
        # found a weak bridge between two non-trivial components
        if node_infos[cur_node]["id"] < low_link and len(conn_comp[neighbor_node]) > 1:
            # weak_points.add(cur_node)
            weak_points.add(neighbor_node)
        # replace low link of current node if next node's low link is lower
        node_infos[cur_node]["low_link"] = min(low_link, node_infos[cur_node]["low_link"])
    return cur_idx, node_infos[cur_node]["low_link"]


def get_weak_point_neighbors(bricksdict:dict, weak_points:set, zstep:int):
    """ get verts neighboring weak points """
    weak_point_neighbors = set()
    for k in weak_points:
        # get all bricks (parent keys) neighboring current brick (starting at parent key 'k')
        neighboring_bricks = get_neighboring_bricks(bricksdict, bricksdict[k]["size"], zstep, get_dict_loc(bricksdict, k))
        # add neighboring bricks (parent keys) to weak point neighbors
        weak_point_neighbors |= set(neighboring_bricks)
    weak_point_neighbors.difference_update(weak_points)
    return weak_point_neighbors


def get_component_interfaces(bricksdict:dict, zstep:int, conn_comps:list):
    component_interfaces = set()
    # get largest conn comp
    conn_comp_lengths = [len(comp) for comp in conn_comps]
    largest_conn_comp_idx = conn_comp_lengths.index(max(conn_comp_lengths))
    # find interfaces between smaller conn_comps and each other/larger conn comp
    for i, conn_comp in enumerate(conn_comps):
        if i == largest_conn_comp_idx:
            continue
        for k in conn_comp:
            neighboring_bricks = get_neighboring_bricks(bricksdict, bricksdict[k]["size"], zstep, get_dict_loc(bricksdict, k))
            # neighboring_keys = get_neighbored_keys(bricksdict, bricksdict[k]["size"], zstep, get_dict_loc(bricksdict, k))
            for k0 in neighboring_bricks:
                pkey = get_parent_key(bricksdict, k0)
                if pkey not in conn_comp:
                    component_interfaces.add(k)
                    component_interfaces.add(k0)
    return component_interfaces


# @timed_call("Time Elapsed")
def draw_connected_components(bricksdict:dict, cm, conn_comps:list, weak_points:set, component_interfaces:set=set(), name:str="connected components"):
    print(type(cm))
    bme = bmesh.new()
    # get bmesh vertices
    verts = dict()
    for conn_comp in conn_comps:
        for key in conn_comp:
            co = bricksdict[key]["co"]
            verts[key] = bme.verts.new(co)
            if key in weak_points or key in component_interfaces:
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
    obj.parent = cm.parent_obj
    bme.to_mesh(m)
    # link object to scene
    cm.collection.objects.link(obj)
    return obj
