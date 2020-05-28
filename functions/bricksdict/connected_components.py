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
import math
import colorsys

# Blender imports
import bpy

# Module imports
from ..common import *
from ..general import *
from ..brick import *


def get_connected_components(bricksdict:dict, zstep:int):
    cm = get_active_context_info()[1]
    conn_comp = dict()
    parent_keys = set([k for k, brick_d in bricksdict.items() if brick_d["parent"] == "self" and brick_d["draw"]])
    while len(parent_keys) > 0:
        starting_key = parent_keys.pop()
        cur_conn_comp = dict()
        recurse_connected(bricksdict, starting_key, cur_conn_comp, zstep)
        # get difference of parent keys
        parent_keys.difference(cur_conn_comp.keys())
        # merge the resulting dict with the rest of the connected components
        conn_comp = {**conn_comp, **cur_conn_comp}
    return conn_comp


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
        loc_pos = [loc0[0], loc0[1], loc0[2] + brick_size[2] / zstep]
        parent_key_pos = get_parent_key(bricksdict, list_to_str(loc_pos))
        if parent_key_pos is not None and bricksdict[parent_key_pos]["draw"]:
            connected_brick_parent_keys.add(parent_key_pos)
    # store connected bricks to new entry in 'conn_comp'
    conn_comp[key] = connected_brick_parent_keys
    # recurse through connected bricks
    for key in connected_brick_parent_keys:
        recurse_connected(bricksdict, key, conn_comp, zstep)


def draw_connected_components(bricksdict:dict, conn_comp:dict, name:str="connected components"):
    bme = bmesh.new()
    # get bmesh vertices
    verts = dict()
    for key in conn_comp:
        co = bricksdict[key]["co"]
        verts[key] = bme.verts.new(co)
    # get edge set
    edges = list()
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
