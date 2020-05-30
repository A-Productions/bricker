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
from .exposure import *
from ..mat_utils import *
from ..matlist_utils import *
from ..brick import *


def update_materials(bricksdict, source_dup, keys, cur_frame=None, action="CREATE"):
    """ sets all mat_names in bricksdict based on near_face """
    scn, cm, n = get_active_context_info()
    use_uv_map = cm.use_uv_map and (len(source_dup.data.uv_layers) > 0 or cm.uv_image is not None)
    # initialize variables
    if keys == "ALL": keys = sorted(list(bricksdict.keys()))  # sort so materials are consistent for multiple frames of the same model
    is_smoke = cm.is_smoke
    material_type = cm.material_type
    color_snap = cm.color_snap
    uv_image = cm.uv_image
    include_transparency = cm.include_transparency
    trans_weight = cm.transparent_weight
    sss = cm.color_snap_sss
    sssSat = cm.color_snap_sss_saturation
    sat_mat = get_saturation_matrix(sssSat)
    specular = cm.color_snap_specular
    roughness = cm.color_snap_roughness
    ior = cm.color_snap_ior
    transmission = cm.color_snap_transmission
    displacement = cm.color_snap_displacement
    color_depth = cm.color_depth if color_snap == "RGB" else 0
    blur_radius = cm.blur_radius if color_snap == "RGB" else 0
    use_abs_template = cm.use_abs_template and brick_materials_installed()
    last_use_abs_template = cm.last_use_abs_template and brick_materials_installed()
    rgba_vals = []
    # get original mat_names, and populate rgba_vals
    for key in keys:
        brick_d = bricksdict[key]
        # skip irrelevant bricks
        nf = brick_d["near_face"]
        if not brick_d["draw"] or (nf is None and not is_smoke) or brick_d["custom_mat_name"]:
            continue
        # get RGBA value at nearest face intersection
        if is_smoke:
            rgba = brick_d["rgba"]
            mat_name = ""
        else:
            ni = Vector(brick_d["near_intersection"])
            rgba, mat_name = get_brick_rgba(source_dup, nf, ni, uv_image, color_depth=color_depth, blur_radius=blur_radius)

        if material_type == "SOURCE":
            # get material with snapped RGBA value
            if rgba is None and use_uv_map:
                mat_name = ""
            elif color_snap == "ABS":
                # if original material was ABS plastic, keep it
                if rgba is None and mat_name in get_colors().keys():
                    pass
                # otherwise, find nearest ABS plastic material to rgba value
                else:
                    mat_obj = get_mat_obj(cm, typ="ABS")
                    assert len(mat_obj.data.materials) > 0
                    mat_name = find_nearest_brick_color_name(rgba, trans_weight, mat_obj)
            elif color_snap == "RGB" or is_smoke:# or use_uv_map:
                mat_name = create_new_material(n, rgba, rgba_vals, sss, sat_mat, specular, roughness, ior, transmission, displacement, use_abs_template, last_use_abs_template, include_transparency, cur_frame)
            if rgba is not None:
                rgba_vals.append(rgba)
        elif material_type == "CUSTOM":
            mat_name = cm.custom_mat.name
        brick_d["mat_name"] = mat_name
    # clear unused materials (left over from previous model)
    mat_name_start = "Bricker_{n}{f}".format(n=n, f="f_%(cur_frame)s" % locals() if cur_frame else "")
    cur_mats = [mat for mat in bpy.data.materials if mat.name.startswith(mat_name_start)]
    # for mat in cur_mats:
    #     if mat.users == 0:
    #         bpy.data.materials.remove(mat)
    #     # else:
    #     #     rgba_vals.append(mat.diffuse_color)
    return bricksdict


def update_brick_sizes(bricksdict, key, available_keys, loc, brick_sizes, zstep, max_L, height_3_only, legal_bricks_only, merge_internals_h, merge_internals_v, material_type, merge_inconsistent_mats=False, merge_vertical=False, tall_type="BRICK", short_type="PLATE"):
    """ update 'brick_sizes' with available brick sizes surrounding bricksdict[key] """
    if not merge_vertical:
        max_L[2] = 1
    new_max1 = max_L[1]
    new_max2 = max_L[2]
    break_outer1 = False
    break_outer2 = False
    # iterate in x direction
    for i in range(max_L[0]):
        # iterate in y direction
        for j in range(max_L[1]):
            # break case 1
            if j >= new_max1: break
            # break case 2
            key1 = list_to_str((loc[0] + i, loc[1] + j, loc[2]))
            if not brick_avail(bricksdict, key, key1, merge_internals_h, material_type, merge_inconsistent_mats) or key1 not in available_keys:
                if j == 0: break_outer2 = True
                else:      new_max1 = j
                break
            # else, check vertically
            for k in range(0, max_L[2], zstep):
                # break case 1
                if k >= new_max2: break
                # break case 2
                key2 = list_to_str((loc[0] + i, loc[1] + j, loc[2] + k))
                if not brick_avail(bricksdict, key, key2, merge_internals_v, material_type, merge_inconsistent_mats) or key2 not in available_keys:
                    if k == 0: break_outer1 = True
                    else:      new_max2 = k
                    break
                # bricks with 2/3 height can't exist
                elif k == 1: continue
                # else, append current brick size to brick_sizes
                else:
                    new_size = [i+1, j+1, k+zstep]
                    if new_size in brick_sizes:
                        continue
                    if not (new_size[2] == 1 and height_3_only) and (not legal_bricks_only or is_legal_brick_size(size=new_size, type=tall_type if new_size[2] == 3 else short_type)):
                        brick_sizes.append(new_size)
            if break_outer1: break
        break_outer1 = False
        if break_outer2: break


def attempt_merge(bricksdict, key, available_keys, default_size, zstep, rand_state, brick_type, max_width, max_depth, legal_bricks_only, merge_internals_h, merge_internals_v, material_type, loc=None, merge_inconsistent_mats=False, prefer_largest=False, merge_vertical=True, target_type=None, height_3_only=False):
    """ attempt to merge bricksdict[key] with adjacent bricks """
    # get loc from key
    loc = loc or get_dict_loc(bricksdict, key)
    brick_sizes = [default_size]
    brick_d = bricksdict[key]
    tall_type = get_tall_type(brick_d, target_type)
    short_type = get_short_type(brick_d, target_type)

    if brick_type != "CUSTOM":
        # check width-depth and depth-width
        for i in (1, -1) if max_width != max_depth else [1]:
            # iterate through adjacent locs to find available brick sizes
            update_brick_sizes(bricksdict, key, available_keys, loc, brick_sizes, zstep, [max_width, max_depth][::i] + [3], height_3_only, legal_bricks_only, merge_internals_h, merge_internals_v, material_type, merge_inconsistent_mats, merge_vertical=merge_vertical, tall_type=tall_type, short_type=short_type)
        # sort brick types from smallest to largest
        order = rand_state.randint(0,2)
        brick_sizes.sort(key=lambda x: (x[0] * x[1] * x[2]) if prefer_largest else (x[2], x[order], x[(order + 1) % 2]))

    # grab the biggest brick size and store to origin brick
    brick_size = brick_sizes[-1]
    brick_d["size"] = brick_size

    # set attributes for merged brick keys
    keys_in_brick = get_keys_in_brick(bricksdict, brick_size, zstep, loc=loc)
    for k in keys_in_brick:
        brick_d0 = bricksdict[k]
        brick_d0["attempted_merge"] = True
        brick_d0["parent"] = "self" if k == key else key
        # set brick type if necessary
        if flat_brick_type(brick_type):
            brick_d0["type"] = short_type if brick_size[2] == 1 else tall_type
    # set flipped and rotated
    set_flipped_and_rotated(brick_d, bricksdict, keys_in_brick)
    if brick_d["type"] == "SLOPE" and brick_type == "SLOPES":
        set_brick_type_for_slope(brick_d, bricksdict, keys_in_brick)

    return brick_size, keys_in_brick


def get_num_aligned_edges(bricksdict, size, key, loc, bricks_and_plates=False):
    num_aligned_edges = 0
    locs = get_locs_in_brick(size, 1, loc)
    got_one = False

    for l in locs:
        # # factor in height of brick (encourages)
        # if bricks_and_plates:
        #     k0 = list_to_str(l)
        #     try:
        #         p_brick0 = bricksdict[k0]["parent"]
        #     except KeyError:
        #         continue
        #     if p_brick0 == "self":
        #         p_brick0 = k
        #     if p_brick0 is None:
        #         continue
        #     p_brick_sz0 = bricksdict[p_brick0]["size"]
        #     num_aligned_edges -= p_brick_sz0[2] / 3
        # check number of aligned edges
        l[2] -= 1
        k = list_to_str(l)
        try:
            p_brick_key = bricksdict[k]["parent"]
        except KeyError:
            continue
        if p_brick_key == "self":
            p_brick_key = k
        if p_brick_key is None:
            continue
        got_one = True
        p_brick_sz = bricksdict[p_brick_key]["size"]
        p_brick_loc = get_dict_loc(bricksdict, p_brick_key)
        # -X side
        if l[0] == loc[0] and p_brick_loc[0] == l[0]:
            num_aligned_edges += 1
        # -Y side
        if l[1] == loc[1] and p_brick_loc[1] == l[1]:
            num_aligned_edges += 1
        # +X side
        if l[0] == loc[0] + size[0] - 1 and p_brick_loc[0] + p_brick_sz[0] - 1 == l[0]:
            num_aligned_edges += 1
        # +Y side
        if l[1] == loc[1] + size[1] - 1 and p_brick_loc[1] + p_brick_sz[1] - 1 == l[1]:
            num_aligned_edges += 1

    if not got_one:
        num_aligned_edges = size[0] * size[1] * 4

    return num_aligned_edges


def brick_avail(bricksdict, source_key, target_key, merge_with_internals, material_type, merge_inconsistent_mats):
    """ check brick is available to merge """
    brick = bricksdict.get(target_key)
    if brick is None:
        return False
    source_brick = bricksdict[source_key]
    # checks if brick materials can be merged (same material or one of the mats is "" (internal)
    mats_mergable = source_brick["mat_name"] == brick["mat_name"] or (merge_with_internals and "" in (source_brick["mat_name"], brick["mat_name"])) or merge_inconsistent_mats
    # returns True if brick is present, brick isn't drawn already, and brick materials can be merged
    return brick["draw"] and not brick["attempted_merge"] and mats_mergable and mergable_brick_type(brick["type"], up=False)


def get_most_common_dir(i_s, i_e, norms):
    return most_common([n[i_s:i_e] for n in norms])

def set_brick_type_for_slope(parent_brick_d, bricksdict, keys_in_brick):
    norms = [bricksdict[k]["near_normal"] for k in keys_in_brick if bricksdict[k]["near_normal"] is not None]
    dir0 = get_most_common_dir(0, 1, norms) if len(norms) != 0 else ""
    if (dir0 == "^" and is_legal_brick_size(size=parent_brick_d["size"], type="SLOPE") and parent_brick_d["top_exposed"]):
        typ = "SLOPE"
    elif (dir0 == "v" and is_legal_brick_size(size=parent_brick_d["size"], type="SLOPE_INVERTED") and parent_brick_d["bot_exposed"]):
        typ = "SLOPE_INVERTED"
    else:
        typ = "BRICK"
    parent_brick_d["type"] = typ


def set_flipped_and_rotated(parent_brick_d, bricksdict, keys_in_brick):
    norms = [bricksdict[k]["near_normal"] for k in keys_in_brick if bricksdict[k]["near_normal"] is not None]

    dir1 = get_most_common_dir(1, 3, norms) if len(norms) != 0 else ""
    flip, rot = get_flip_rot(dir1)

    # set flipped and rotated
    parent_brick_d["flipped"] = flip
    parent_brick_d["rotated"] = rot
