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
import bmesh
import math
import time
import sys
import random
import json
import copy
import numpy as np

# Blender imports
import bpy
from mathutils import Vector, Matrix

# Module imports
from .brick import *
from .bricksdict import *
from .common import *
from .general import *
from .hash_object import hash_object
from .mat_utils import *
from ..lib.caches import bricker_mesh_cache


def draw_brick(cm_id, bricksdict, key, loc, seed_keys, bcoll, clear_existing_collection, parent, dimensions, zstep, brick_size, brick_type, split, last_split_model, custom_object1, custom_object2, custom_object3, mat_dirty, custom_data, brick_scale, bricks_created, all_meshes, logo, mats, brick_mats, internal_mat, brick_height, logo_resolution, logo_decimate, build_is_dirty, material_type, custom_mat, random_mat_seed, stud_detail, exposed_underside_detail, hidden_underside_detail, random_rot, random_loc, logo_type, logo_scale, logo_inset, circle_verts, instance_method, rand_s2, rand_s3):
    brick_d = bricksdict[key]
    # check exposure of current [merged] brick
    if brick_d["top_exposed"] is None or brick_d["bot_exposed"] is None or build_is_dirty:
        top_exposed, bot_exposed = set_all_brick_exposures(bricksdict, zstep, key)
    else:
        top_exposed, bot_exposed = is_brick_exposed(bricksdict, zstep, key)

    # get brick material
    mat = get_material(bricksdict, key, brick_size, zstep, material_type, custom_mat, random_mat_seed, mat_dirty, seed_keys, brick_mats=brick_mats)

    # set up arguments for brick mesh
    use_stud = (top_exposed and stud_detail != "NONE") or stud_detail == "ALL"
    logo_to_use = logo if use_stud else None
    underside_detail = exposed_underside_detail if bot_exposed else hidden_underside_detail

    ### CREATE BRICK ###

    # add brick with new mesh data at original location
    if brick_d["type"].startswith("CUSTOM"):
        m = custom_data[int(brick_d["type"][-1]) - 1]
    else:
        # get brick mesh
        m = get_brick_data(brick_d, dimensions, brick_type, brick_size, circle_verts, underside_detail, use_stud, logo_to_use, logo_type, logo_inset, logo_scale, logo_resolution, logo_decimate, rand_s3)
    # duplicate data if not instancing by mesh data
    m = m if instance_method == "LINK_DATA" else m.copy()
    # apply random rotation to edit mesh according to parameters
    random_rot_matrix = get_random_rot_matrix(random_rot, rand_s2, brick_size)
    # get brick location
    loc_offset = get_random_loc(random_loc, rand_s2, dimensions["half_width"], dimensions["half_height"])
    brick_loc = get_brick_center(bricksdict, key, zstep, loc) + loc_offset

    if split:
        brick = bpy.data.objects.get(brick_d["name"])
        if brick:
            # NOTE: last brick object is left in memory (faster)
            # set brick.data to new mesh (resets materials)
            brick.data = m
        else:
            # create new object with mesh data
            brick = bpy.data.objects.new(brick_d["name"], m)
            brick.cmlist_id = cm_id
        # rotate brick by random rotation
        if random_rot_matrix is not None:
            # resets rotation_euler in case object is reused
            brick.rotation_euler = (0, 0, 0)
            brick.rotation_euler.rotate(random_rot_matrix)
        # set brick location
        brick.location = brick_loc
        # set brick material
        mat = mat or internal_mat
        set_material(brick, mat)
        if mat:
            keys_in_brick = get_keys_in_brick(bricksdict, brick_size, zstep, loc)
            for k in keys_in_brick:
                bricksdict[k]["mat_name"] = mat.name
        # append to bricks_created
        bricks_created.append(brick)
        # set remaining brick info if brick object just created
        brick.parent = parent
        if not brick.is_brick:
            brick.is_brick = True
        # link bricks to brick collection
        if clear_existing_collection or brick.name not in bcoll.objects.keys():
            bcoll.objects.link(brick)
    else:
        # duplicates mesh – prevents crashes in 2.79 (may need to add back if experiencing crashes in b280)
        if not b280():
            m = m.copy()
        # apply rotation matrices to edit mesh
        if random_rot_matrix is not None:
            m.transform(random_rot_matrix)
        # transform brick mesh to coordinate on matrix
        m.transform(Matrix.Translation(brick_loc))

        # set to internal mat if material not set
        internal = False
        if mat is None:
            mat = internal_mat
            internal = True

        # keep track of mats already used
        if mat in mats:
            mat_idx = mats.index(mat)
        elif mat is not None:
            mats.append(mat)
            mat_idx = len(mats) - 1

        # set material
        if mat is not None:
            # set material name in dictionary
            if not internal:
                brick_d["mat_name"] = mat.name
            # point all polygons to target material (index will correspond in all_meshes object)
            for p in m.polygons:
                p.material_index = mat_idx

        # append mesh to all_meshes bmesh object
        all_meshes.from_mesh(m)

        # remove mesh in 2.79 (mesh was duplicated above to prevent crashes)
        if not b280():
            bpy.data.meshes.remove(m)
        # NOTE: The following lines clean up the mesh if not duplicated
        else:
            # reset polygon material mapping
            if mat is not None:
                for p in m.polygons:
                    p.material_index = 0

            # reset transformations for reference mesh
            m.transform(Matrix.Translation(-brick_loc))
            if random_rot_matrix is not None:
                random_rot_matrix.invert()
                m.transform(random_rot_matrix)

    return bricksdict


def merge_with_adjacent_bricks(brick_d, bricksdict, key, loc, keys_not_checked, default_size, zstep, rand_s1, build_is_dirty, brick_type, max_width, max_depth, legal_bricks_only, merge_internals_h, merge_internals_v, material_type, merge_vertical=True):
    brick_size = brick_d["size"]
    if brick_size is None or build_is_dirty:
        prefer_largest = 0 < brick_d["val"] < 1
        brick_size, keys_in_brick = attempt_merge(bricksdict, key, keys_not_checked, default_size, zstep, rand_s1, brick_type, max_width, max_depth, legal_bricks_only, merge_internals_h, merge_internals_v, material_type, loc=loc, prefer_largest=prefer_largest, merge_vertical=merge_vertical, height_3_only=brick_d["type"] in get_brick_types(height=3))
    else:
        keys_in_brick = get_keys_in_brick(bricksdict, brick_size, zstep, loc=loc)
    return brick_size, keys_in_brick


def skip_this_row(time_through, lowest_z, z, offset_brick_layers):
    if time_through == 0:  # first time
        if (z - offset_brick_layers - lowest_z) % 3 in (1, 2):
            return True
    else:  # second time
        if (z - offset_brick_layers - lowest_z) % 3 == 0:
            return True
    return False


def get_random_loc(random_loc, rand, half_width, half_height):
    """ get random location between (0,0,0) and (width/2, width/2, height/2) """
    loc = Vector((0,0,0))
    if random_loc > 0:
        loc.xy = [rand.uniform(-half_width * random_loc, half_width * random_loc)] * 2
        loc.z = rand.uniform(-half_height * random_loc, half_height * random_loc)
    return loc


def get_random_rot_matrix(random_rot, rand, brick_size):
    """ get rotation matrix randomized by random_rot """
    if random_rot == 0:
        return None
    x, y, z = get_random_rot_angle(random_rot, rand, brick_size)
    # get rotation matrix
    x_mat = Matrix.Rotation(x, 4, "X")
    y_mat = Matrix.Rotation(y, 4, "Y")
    z_mat = Matrix.Rotation(z, 4, "Z")
    combined_mat = mathutils_mult(x_mat, y_mat, z_mat)
    return combined_mat


def get_random_rot_angle(random_rot, rand, brick_size):
    """ get rotation angles randomized by random_rot """
    if random_rot == 0:
        return None
    denom = 0.75 if max(brick_size) == 0 else brick_size[0] * brick_size[1]
    mult = random_rot / denom
    # calculate rotation angles in radians
    x = rand.uniform(-math.radians(11.25) * mult, math.radians(11.25) * mult)
    y = rand.uniform(-math.radians(11.25) * mult, math.radians(11.25) * mult)
    z = rand.uniform(-math.radians(45)    * mult, math.radians(45)    * mult)
    return x, y, z


def apply_brick_mesh_settings(m):
    # set texture space
    m.use_auto_texspace = False
    m.texspace_size = (1, 1, 1)
    # use auto normal smoothing (equivalent to edge split modifier)
    m.use_auto_smooth = True
    m.auto_smooth_angle = math.radians(44)
    m.update()


def get_brick_data(brick_d, dimensions, brick_type, brick_size=(1, 1, 1), circle_verts=16, underside_detail="FLAT", use_stud=True, logo_to_use=None, logo_type=None, logo_inset=None, logo_scale=None, logo_resolution=None, logo_decimate=None, rand=None):
    # get bm_cache_string
    bm_cache_string = ""
    if "CUSTOM" not in brick_type:
        custom_logo_used = logo_to_use is not None and logo_type == "CUSTOM"
        bm_cache_string = marshal.dumps((
            dimensions["height"], brick_size, underside_detail,
            logo_resolution if logo_to_use is not None else None,
            logo_decimate if logo_to_use is not None else None,
            logo_inset if logo_to_use is not None else None,
            hash_object(logo_to_use) if custom_logo_used else None,
            logo_scale if custom_logo_used else None,
            logo_type, use_stud, circle_verts,
            brick_d["type"], dimensions["gap"],
            brick_d["flipped"] if brick_d["type"] in ("SLOPE", "SLOPE_INVERTED") else None,
            brick_d["rotated"] if brick_d["type"] in ("SLOPE", "SLOPE_INVERTED") else None,
        )).hex()

    # NOTE: Stable implementation for Blender 2.79
    # check for bmesh in cache
    bms = bricker_mesh_cache.get(bm_cache_string)
    # if not found create new brick mesh(es) and store to cache
    if bms is None:
        # create new brick bmeshes
        bms = new_brick_mesh(dimensions, brick_type, size=brick_size, type=brick_d["type"], flip=brick_d["flipped"], rotate90=brick_d["rotated"], logo=logo_to_use, logo_type=logo_type, logo_scale=logo_scale, logo_inset=logo_inset, all_vars=logo_to_use is not None, underside_detail=underside_detail, stud=use_stud, circle_verts=circle_verts)
        # store newly created meshes to cache
        if brick_type != "CUSTOM":
            bricker_mesh_cache[bm_cache_string] = bms
    # create edit mesh for each bmesh
    meshes = []
    for i,bm in enumerate(bms):
        # check for existing edit mesh in blendfile data
        bmcs_hash = hash_str(bm_cache_string)
        mesh_name = "%(bmcs_hash)s_%(i)s" % locals()
        m = bpy.data.meshes.get(mesh_name)
        # create new edit mesh and send bmesh data to it
        if m is None:
            m = bpy.data.meshes.new(mesh_name)
            bm.to_mesh(m)
            # center mesh origin
            center_mesh_origin(m, dimensions, brick_size)
            # apply brick mesh settings
            apply_brick_mesh_settings(m)
        meshes.append(m)
    # # TODO: Try the following code instead in Blender 2.8 – see if it crashes with the following steps:
    # #     Open new file
    # #     Create new bricker model and Brickify with default settings
    # #     Delete the brickified model with the 'x > OK?' shortcut
    # #     Undo with 'ctrl + z'
    # #     Enable 'Update Model' button by clicking on and off of 'Gap Between Bricks'
    # #     Press 'Update Model'
    # # check for bmesh in cache
    # meshes = bricker_mesh_cache.get(bm_cache_string)
    # # if not found create new brick mesh(es) and store to cache
    # if meshes is None:
    #     # create new brick bmeshes
    #     bms = new_brick_mesh(dimensions, brick_type, size=brick_size, type=brick_d["type"], flip=brick_d["flipped"], rotate90=brick_d["rotated"], logo=logo_to_use, logo_type=logo_type, logo_scale=logo_scale, logo_inset=logo_inset, all_vars=logo_to_use is not None, underside_detail=underside_detail, stud=use_stud, circle_verts=circle_verts)
    #     # create edit mesh for each bmesh
    #     meshes = []
    #     for i,bm in enumerate(bms):
    #         # check for existing edit mesh in blendfile data
    #         bmcs_hash = hash_str(bm_cache_string)
    #         mesh_name = "%(bmcs_hash)s_%(i)s" % locals()
    #         m = bpy.data.meshes.get(mesh_name)
    #         # create new edit mesh and send bmesh data to it
    #         if m is None:
    #             m = bpy.data.meshes.new(mesh_name)
    #             bm.to_mesh(m)
    #             # center mesh origin
    #             center_mesh_origin(m, dimensions, brick_size)
    #         meshes.append(m)
    #     # store newly created meshes to cache
    #     if brick_type != "CUSTOM":
    #         bricker_mesh_cache[bm_cache_string] = meshes

    # pick edit mesh randomly from options
    rand = np.random.RandomState(0) if rand is None else rand
    m0 = meshes[rand.randint(0, len(meshes))] if len(meshes) > 1 else meshes[0]

    return m0


def get_material(bricksdict, key, size, zstep, material_type, custom_mat, random_mat_seed, mat_dirty, seed_keys, brick_mats=None):
    mat = None
    highest_val = 0
    mats_L = []
    if bricksdict[key]["custom_mat_name"]:
        mat = bpy.data.materials.get(bricksdict[key]["mat_name"])
    elif material_type == "CUSTOM":
        mat = custom_mat
    elif material_type == "SOURCE":
        # get most frequent material in brick size
        mat_name = ""
        keys_in_brick = get_keys_in_brick(bricksdict, size, zstep, key=key)
        for key0 in keys_in_brick:
            cur_brick_d = bricksdict[key0]
            if cur_brick_d["val"] >= highest_val:
                highest_val = cur_brick_d["val"]
                mat_name = cur_brick_d["mat_name"]
                if cur_brick_d["val"] == 1:
                    mats_L.append(mat_name)
        # if multiple shell materials, use the most frequent one
        if len(mats_L) > 1:
            mat_name = most_common(mats_L)
        mat = bpy.data.materials.get(mat_name)
    elif material_type == "RANDOM" and brick_mats is not None and len(brick_mats) > 0:
        if len(brick_mats) > 1:
            rand_state = np.random.RandomState(0)
            seed_inc = seed_keys.index(key)  # keeps materials consistent accross all calculations regardless of where material is set
            rand_state.seed(random_mat_seed + seed_inc)
            rand_idx = rand_state.randint(0, len(brick_mats))
        else:
            rand_idx = 0
        mat_name = brick_mats[rand_idx]
        mat = bpy.data.materials.get(mat_name)
    return mat

def update_brick_sizes_and_types_used(cm, sz, typ):
    bsu = cm.brick_sizes_used
    btu = cm.brick_types_used
    cm.brick_sizes_used += sz if bsu == "" else ("|%(sz)s" % locals() if sz not in bsu else "")
    cm.brick_types_used += typ if btu == "" else ("|%(typ)s" % locals() if typ not in btu else "")
