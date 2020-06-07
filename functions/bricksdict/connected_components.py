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
# NONE!

# Blender imports
import bpy

# Module imports
from ..common import *
from ..general import *
from ..brick import *

# For reference on this implementation, see 2.2 of: https://lgg.epfl.ch/publications/2013/lego/lego.pdf
# For additional reference, see the following article: https://dl.acm.org/doi/pdf/10.1145/2739480.2754667


# @timed_call("Time Elapsed")
def get_connected_components(bricksdict:dict, zstep:int, parent_keys:list):
    # initialize variables
    conn_comps = list()
    parent_keys = set(parent_keys)
    # start at a node and build connected components, iteratively, till all nodes visited
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
                keys_connected_to_k0 = get_connected_keys(bricksdict, k0, bricksdict[k0]["size"], zstep)
                cur_conn_comp[k0] = keys_connected_to_k0
                next_parent_keys += keys_connected_to_k0
        # remove keys in current conn_comp list from parent_keys
        parent_keys -= set(cur_conn_comp.keys())
        # add current conn_comp to list of conn_comps
        conn_comps.append(cur_conn_comp)
        # conn_comp = {**conn_comp, **cur_conn_comp}
    return conn_comps


def get_connected_keys(bricksdict:dict, key:str, brick_size:list, zstep:int, require_merge_attempt:bool=False):
    # get locs in current brick
    loc = get_dict_loc(bricksdict, key)
    lowest_locs_in_brick = get_lowest_locs_in_brick(brick_size, loc)
    # find connected brick parent keys
    connected_brick_parent_keys = set()
    for loc0 in lowest_locs_in_brick:
        # check locations below current brick
        loc_neg = [loc0[0], loc0[1], loc0[2] - 1]
        parent_key_neg = get_parent_key(bricksdict, list_to_str(loc_neg))
        if parent_key_neg is not None and bricksdict[parent_key_neg]["draw"] and (not require_merge_attempt or bricksdict[parent_key_neg]["attempted_merge"]):
            connected_brick_parent_keys.add(parent_key_neg)
        # make sure key doesn't reference itself as neighbor (for debugging purposes)
        # NOTE: if assertion hit, that probably means that the 'bricksdict[list_to_str(loc_neg)]["size"]' was set improperly before entering this function
        assert parent_key_neg != key
        # check locations above current brick
        loc_pos = [loc0[0], loc0[1], loc0[2] + brick_size[2] // zstep]
        parent_key_pos = get_parent_key(bricksdict, list_to_str(loc_pos))
        if parent_key_pos is not None and bricksdict[parent_key_pos]["draw"] and (not require_merge_attempt or bricksdict[parent_key_pos]["attempted_merge"]):
            connected_brick_parent_keys.add(parent_key_pos)
        # make sure key doesn't reference itself as neighbor (for debugging purposes)
        # NOTE: if assertion hit, that probably means that the 'bricksdict[list_to_str(loc_pos)]["size"]' was set improperly before entering this function
        assert parent_key_pos != key
    return connected_brick_parent_keys


# adapted from code written by Dr. Jon Denning
def get_bridges(conn_comps:list):
    # bridges = []
    weak_points = set()
    for conn_comp in conn_comps:
        # get starting node
        starting_node = next(iter(conn_comp.keys()))
        # initialize visited list
        visited = {}
        for node in conn_comp:
            visited[node] = False

        # use iterative (recursion-free) DFS using explicit stack
        order   = []  # order of visiting during DFS
        working = [(None, starting_node)]  # from node, to node
        while working:
            node_prev, node_current = working.pop()
            # record order of visiting
            order.append((node_prev, node_current, not visited[node_current]))
            # check if already visited here
            if visited[node_current]:
                continue
            # add to visited
            visited[node_current] = True
            # add neighbors to stack
            working += [
                (node_current, node_next) for node_next in conn_comp[node_current]
                if node_next != node_prev
            ]

        # use DFS traversal info to solve problem!

        # label nodes
        node_infos = dict()
        id_current = 1
        for (node_prev, node_current, visit) in order:
            if not visit: continue  # only update data when visiting
            node_infos[node_current] = {"id": id_current, "low_link": id_current}
            id_current += 1

        # pop the first item in order (with 'None' as the from node)
        order.pop(0)

        # note: need to process in reverse order to propagate low_links and ids from leaves to root
        for (node_current, node_next, visit) in reversed(order):
            if visit:
                # we visited node_next from node_current during DFS
                node_infos[node_current]["low_link"] = min(node_infos[node_current]["low_link"], node_infos[node_next]["low_link"])
                if node_infos[node_current]["id"] < node_infos[node_next]["low_link"] and len(conn_comp[node_next]) > 1:
                    # found the bridge!
                    # bridges.append((node_current, node_next))  # changed to tuple
                    weak_points.add(node_current)
                    weak_points.add(node_next)
            else:
                # we visited node_next from some other node (not node_current)
                node_infos[node_current]["low_link"] = min(node_infos[node_current]["low_link"], node_infos[node_next]["id"])

    # done processing
    return weak_points


def get_bridges_recursive(conn_comps:list):
    """ get one of the nodes at each bridge connecting two non-trivial components """
    weak_points = set()
    for conn_comp in conn_comps:
        node_infos = dict()
        starting_key = next(iter(conn_comp.keys()))
        depth_first_search(conn_comp, weak_points, node_infos, 0, starting_key)
    return weak_points


# adapted from: https://emre.me/algorithms/tarjans-algorithm/
def depth_first_search(conn_comp:dict, weak_points:set, node_infos:dict, cur_idx:int, cur_node:str, last_node:str=""):
    """ recursive implementation of DFS to discover weak points in connected components data structure """
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
            weak_points.add(cur_node)
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


def get_component_interfaces(bricksdict:dict, zstep:int, conn_comps:list, test=False):
    """ get parent keys of neighboring bricks between two connected components """
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
            if test:
                component_interfaces.add(k)
                component_interfaces |= set(neighboring_bricks)
                continue
            for k0 in neighboring_bricks:
                pkey = get_parent_key(bricksdict, k0)
                if pkey not in conn_comp and pkey is not None:
                    component_interfaces.add(k)
                    component_interfaces.add(pkey)
                    # also add neighbors to this neighbor brick in another conn_comp
                    neighboring_bricks_1 = get_neighboring_bricks(bricksdict, bricksdict[pkey]["size"], zstep, get_dict_loc(bricksdict, pkey))
                    for k1 in neighboring_bricks_1:
                        component_interfaces.add(k1)

    return component_interfaces


def draw_connected_components(bricksdict:dict, cm, conn_comps:list, weak_points:set, component_interfaces:set=set(), name:str="connected components"):
    """ draw connected component grid for model in 3D space """
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
