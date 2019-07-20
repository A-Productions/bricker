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
import bpy
import bmesh
import random
import time
import numpy as np

# Blender imports
from mathutils import Vector, Matrix

# Addon imports
from .mesh_generators import *
from .get_brick_dimensions import *
from ...functions import *

class Bricks:
    @staticmethod
    def new_mesh(dimensions:list, brick_type:str, size:list=[1,1,3], type:str="BRICK", flip:bool=False, rotate90:bool=False, logo=False, logo_type="NONE", logo_scale=100, logo_inset=None, all_vars=False, underside_detail:str="FLAT", stud:bool=True, circle_verts:int=16):
        """ create unlinked Brick at origin """
        # create brick mesh
        if type in ("BRICK", "PLATE") or "CUSTOM" in type:
            brick_bm = make_standard_brick(dimensions, size, type, brick_type, circle_verts=circle_verts, detail=underside_detail, stud=stud)
        elif type in get_round_brick_types():
            brick_bm = make_round_1x1(dimensions, brick_type, circle_verts=circle_verts, type=type, detail=underside_detail)
        elif type in ("TILE", "TILE_GRILL"):
            brick_bm = make_tile(dimensions, brick_type, brick_size=size, circle_verts=circle_verts, type=type, detail=underside_detail)
        elif type in ("SLOPE", "SLOPE_INVERTED", "TALL_SLOPE"):
            # determine brick direction
            directions = ["X+", "Y+", "X-", "Y-"]
            max_idx = size.index(max(size[:2]))
            max_idx -= 2 if flip else 0
            max_idx += 1 if rotate90 else 0
            # make slope brick bmesh
            if type == "SLOPE_INVERTED":
                brick_bm = make_inverted_slope(dimensions, size, brick_type, circle_verts=circle_verts, direction=directions[max_idx], detail=underside_detail, stud=stud)
            else:
                brick_bm = make_slope(dimensions, size, brick_type, circle_verts=circle_verts, direction=directions[max_idx], detail=underside_detail, stud=stud)
        else:
            raise ValueError("'new_mesh' function received unrecognized value for parameter 'type': '" + str(type) + "'")

        # send brick mesh to junk edit mesh
        junk_mesh = bpy.data.meshes.get('Bricker_junk_mesh')
        if junk_mesh is None:
            junk_mesh = bpy.data.meshes.new('Bricker_junk_mesh')
        brick_bm.to_mesh(junk_mesh)

        # set bevel weights
        junk_mesh.use_customdata_edge_bevel = True
        for e in junk_mesh.edges:
            e.bevel_weight = 0.0 if e.select else 1.0

        # create list of bmesh variations (logo only, for now)
        if logo and stud and (type in ("BRICK", "PLATE", "STUD", "SLOPE_INVERTED") or type == "SLOPE" and max(size[:2]) != 1):
            bms = make_logo_variations(dimensions, size, brick_type, directions[max_idx] if type.startswith("SLOPE") else "", all_vars, logo, logo_inset, logo_type, logo_scale)
        else:
            bms = [bmesh.new()]

        # append brick mesh to each bmesh variation
        for bm in bms:
            bm.from_mesh(junk_mesh)

        # return bmesh objects
        return bms

    @staticmethod
    def split_all(bricksdict, zstep, keys=None):
        keys = keys or list(bricksdict.keys())
        for key in keys:
            # set all bricks as unmerged
            if bricksdict[key]["draw"]:
                bricksdict[key]["parent"] = "self"
                bricksdict[key]["size"] = [1, 1, zstep]

    def split(bricksdict, key, zstep, brick_type, loc=None, v=True, h=True):
        """split brick vertically and/or horizontally

        Keyword Arguments:
        bricksdict -- Matrix of bricks in model
        key        -- key for brick in matrix
        loc        -- xyz location of brick in matrix
        v          -- split brick vertically
        h          -- split brick horizontally
        """
        # set up unspecified paramaters
        loc = loc or get_dict_loc(bricksdict, key)
        # initialize vars
        size = bricksdict[key]["size"]
        new_size = [1, 1, size[2]]
        if flat_brick_type(brick_type):
            if not v:
                zstep = 3
            else:
                new_size[2] = 1
        if not h:
            new_size[0] = size[0]
            new_size[1] = size[1]
            size[0] = 1
            size[1] = 1
        # split brick into individual bricks
        keys_in_brick = get_keys_in_brick(bricksdict, size, zstep, loc=loc)
        for cur_key in keys_in_brick:
            bricksdict[cur_key]["size"] = new_size.copy()
            bricksdict[cur_key]["type"] = "BRICK" if new_size[2] == 3 else "PLATE"
            bricksdict[cur_key]["parent"] = "self"
            bricksdict[cur_key]["top_exposed"] = bricksdict[key]["top_exposed"]
            bricksdict[cur_key]["bot_exposed"] = bricksdict[key]["bot_exposed"]
        return keys_in_brick

    @staticmethod
    def get_dimensions(height=1, z_scale=1, gap_percentage=0.01):
        return get_brick_dimensions(height, z_scale, gap_percentage)


def get_num_rots(direction, size):
    return 1 if direction != "" else (4 if size[0] == 1 and size[1] == 1 else 2)


def get_rod_add(direction, size):
    if direction != "":
        directions = ["X+", "Y+", "X-", "Y-"]
        rot_add = 90 * (directions.index(direction) + 1)
    else:
        rot_add = 180 if (size[0] == 2 and size[1] > 2) or (size[0] == 1 and size[1] > 1) else 90
    return rot_add


def make_logo_variations(dimensions, size, brick_type, direction, all_vars, logo, logo_inset, logo_type, logo_scale):
    # get logo rotation angle based on size of brick
    rot_vars = get_num_rots(direction, size)
    rot_mult = 90 if size[0] == 1 and size[1] == 1 else 180
    rot_add = get_rod_add(direction, size)
    # set z_rot to random rotation angle
    if all_vars:
        z_rots = [i * rot_mult + rot_add for i in range(rot_vars)]
    else:
        random_seed = int(time.time()*10**6) % 10000
        rand_s0 = np.random.RandomState(random_seed)
        z_rots = [rand_s0.randint(0,rot_vars) * rot_mult + rot_add]
    # get duplicate of logo mesh
    m = logo.data.copy()

    # create new bmeshes for each logo variation
    bms = [bmesh.new() for z_rot in z_rots]
    # get loc offsets
    z_offset = dimensions["logo_offset"] + (dimensions["height"] if flat_brick_type(brick_type) and size[2] == 3 else 0)
    lw = dimensions["logo_width"] * (0.78 if logo_type == "LEGO" else (logo_scale / 100))
    dist_max = max(logo.dimensions.xy)
    z_offset += ((logo.dimensions.z * (lw / dist_max)) / 2) * (1 - logo_inset / 50)
    xy_offset = dimensions["width"] + dimensions["gap"]
    # cap x/y ranges so logos aren't created over slopes
    x_range_start = size[0] - 1 if direction == "X-" else 0
    y_range_start = size[1] - 1 if direction == "Y-" else 0
    x_range_end = 1 if direction == "X+" else size[0]
    y_range_end = 1 if direction == "Y+" else size[1]
    # add logos on top of each stud
    for i,z_rot in enumerate(z_rots):
        m0 = m.copy()
        # rotate logo around stud
        if z_rot != 0: m0.transform(Matrix.Rotation(math.radians(z_rot), 4, 'Z'))
        # create logo for each stud and append to bm
        gap_base = dimensions["gap"] * Vector(((x_range_end - x_range_start - 1) / 2, (y_range_end - y_range_start - 1) / 2))
        for x in range(x_range_start, x_range_end):
            for y in range(y_range_start, y_range_end):
                # create duplicate of rotated logo
                m1 = m0.copy()
                # adjust gap based on distance from first stud
                gap = gap_base + dimensions["gap"] * Vector((x / x_range_end, y / y_range_end))
                # translate logo into place
                m1.transform(Matrix.Translation((x * xy_offset - gap.x, y * xy_offset - gap.y, z_offset)))
                # add transformed mesh to bm mesh
                bms[i].from_mesh(m1)
                bpy.data.meshes.remove(m1)
        bpy.data.meshes.remove(m0)
    return bms
