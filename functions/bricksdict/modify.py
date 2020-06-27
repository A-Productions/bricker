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
from .connected_components import *
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


def update_brick_sizes(bricksdict, key, loc, brick_sizes, zstep, max_L, height_3_only, merge_internals_h, merge_internals_v, material_type, merge_inconsistent_mats=False, merge_vertical=False, mult=(1, 1, 1)):
    """ update 'brick_sizes' with available brick sizes surrounding bricksdict[key] """
    if not merge_vertical:
        max_L[2] = 1
    new_max1 = max_L[1]
    new_max2 = max_L[2]
    break_outer1 = False
    break_outer2 = False
    brick_mat_name = bricksdict[key]["mat_name"]
    # iterate in x direction
    for i in range(max_L[0]):
        # iterate in y direction
        for j in range(max_L[1]):
            # break case 1
            if j >= new_max1: break
            # break case 2
            key1 = list_to_str((loc[0] + (i * mult[0]), loc[1] + (j * mult[1]), loc[2]))
            brick_available, brick_mat_name = brick_avail(bricksdict, key1, brick_mat_name, merge_internals_h, material_type, merge_inconsistent_mats)
            if not brick_available:
                if j == 0: break_outer2 = True
                else:      new_max1 = j
                break
            # else, check vertically
            for k in range(0, max_L[2], zstep):
                # break case 1
                if k >= new_max2: break
                # break case 2
                key2 = list_to_str((loc[0] + (i * mult[0]), loc[1] + (j * mult[1]), loc[2] + (k * mult[2])))
                brick_available, brick_mat_name = brick_avail(bricksdict, key2, brick_mat_name, merge_internals_v, material_type, merge_inconsistent_mats)
                if not brick_available:
                    if k == 0: break_outer1 = True
                    else:      new_max2 = k
                    break
                # bricks with 2/3 height can't exist
                elif k == 1: continue
                # else, append current brick size to brick_sizes
                else:
                    new_size = [(i+1) * mult[0], (j+1) * mult[1], (k+zstep) * mult[2]]
                    if new_size in brick_sizes:
                        continue
                    if not (abs(new_size[2]) == 1 and height_3_only):
                        brick_sizes.append(new_size)
            if break_outer1: break
        break_outer1 = False
        if break_outer2: break


def attempt_merge(bricksdict, key, default_size, zstep, brick_type, max_width, max_depth, legal_bricks_only, merge_internals_h, merge_internals_v, material_type, loc=None, axis_sort_order=(2, 0, 1), merge_inconsistent_mats=False, prefer_largest=False, direction_mult=(1, 1, 1), merge_vertical=True, target_type=None, height_3_only=False):
    """ attempt to merge bricksdict[key] with adjacent bricks """
    # get loc from key
    loc = loc or get_dict_loc(bricksdict, key)
    brick_sizes = [default_size]
    brick_size = default_size
    tall_type = get_tall_type(bricksdict[key], target_type)
    short_type = get_short_type(bricksdict[key], target_type)

    if brick_type != "CUSTOM":
        # check width-depth and depth-width
        for i in (1, -1) if max_width != max_depth else [1]:
            # iterate through adjacent locs to find available brick sizes
            update_brick_sizes(bricksdict, key, loc, brick_sizes, zstep, [max_width, max_depth][::i] + [3], height_3_only, merge_internals_h, merge_internals_v, material_type, merge_inconsistent_mats, merge_vertical=merge_vertical, mult=direction_mult)
        # get largest (legal, if checked) brick size found
        brick_sizes.sort(key=lambda v: -abs(v[0] * v[1] * v[2]) if prefer_largest else (-abs(v[axis_sort_order[0]]), -abs(v[axis_sort_order[1]]), -abs(v[axis_sort_order[2]])))
        target_brick_size = next((sz for sz in brick_sizes if not legal_bricks_only or is_legal_brick_size(size=[abs(v) for v in sz], type=tall_type if abs(sz[2]) == 3 else short_type)), None)
        assert target_brick_size is not None
        # get new brick_size, loc, and key for largest brick size
        key, brick_size = get_new_parent_key_and_size(target_brick_size, loc, zstep)
        loc = get_dict_loc(bricksdict, key)

    # update bricksdict for keys merged together
    keys_in_brick = get_keys_in_brick(bricksdict, brick_size, zstep, loc=loc)
    update_merged_keys_in_bricksdict(bricksdict, key, keys_in_brick, brick_size, brick_type, short_type, tall_type)

    return brick_size, key, keys_in_brick


def attempt_post_merge(bricksdict, key, zstep, brick_type, legal_bricks_only, max_length=8, loc=None, merge_inconsistent_mats=False, merge_vertical=True):
    # get loc from key
    starting_size = bricksdict[key]["size"].copy()
    loc = loc or get_dict_loc(bricksdict, key)
    target_type = "BRICK" if brick_type == "BRICKS_AND_PLATES" else brick_type
    tall_type = get_tall_type(bricksdict[key], target_type)
    short_type = get_short_type(bricksdict[key], target_type)
    brick_sizes = [starting_size]

    # go in the x direction
    for axis in range(3):
        cur_size = starting_size.copy()
        while True:
            loc1 = loc.copy()
            loc1[axis] += cur_size[axis]
            key0 = list_to_str(loc1)
            # check key is not parent key
            brick_d = bricksdict.get(key0)
            if brick_d is None or brick_d["parent"] != "self":
                break
            next_size = brick_d["size"]
            # ensure next brick's size on other 2 axes line up with current brick
            other_axes = ((axis + 1) % 3, (axis + 2) % 3)
            if next_size[other_axes[0]] != starting_size[other_axes[0]] or next_size[other_axes[1]] != starting_size[other_axes[1]]:
                break
            # create new cur_size
            cur_size[axis] += next_size[axis]
            # enforce max width/depth cap, and for Z axis enforce max height of 3
            if cur_size[axis] > (max_length if axis < 2 else 3):
                break
            # skip height of 2 for Z axis
            if axis == 2 and cur_size[2] == 2:
                continue
            # ensure new size is legal brick size
            if legal_bricks_only and not is_legal_brick_size(size=cur_size, type=tall_type if abs(cur_size[2]) == 3 else short_type):
                continue
            # if successful, add this to the possible brick sizes
            brick_sizes.append(cur_size.copy())

    # get target brick size (weight X/Y a bit more heavily as this increases stability)
    new_size = sorted(brick_sizes, key=lambda v: ((v[0] * v[1] * 1.5) * v[2]))[-1]

    # update bricksdict for keys of bricks merged together
    keys_in_brick = get_keys_in_brick(bricksdict, new_size, zstep, loc=loc)
    engulfed_keys = set(k for k in keys_in_brick if bricksdict[k]["parent"] == "self" and k != key)
    update_merged_keys_in_bricksdict(bricksdict, key, keys_in_brick, new_size, brick_type, short_type, tall_type)

    # return whether successful and keys that were engulfed
    return new_size != starting_size, engulfed_keys


def update_merged_keys_in_bricksdict(bricksdict, key, merged_keys, brick_size, brick_type, short_type, tall_type):
    # store the best brick size to origin brick
    brick_d = bricksdict[key]
    brick_d["size"] = brick_size

    # set attributes for merged brick keys
    for k in merged_keys:
        brick_d0 = bricksdict[k]
        brick_d0["attempted_merge"] = True
        brick_d0["parent"] = "self" if k == key else key
        # set brick type if necessary
        if flat_brick_type(brick_type):
            brick_d0["type"] = short_type if brick_size[2] == 1 else tall_type
    # set flipped and rotated
    if brick_d["type"] == "SLOPE":
        set_flipped_and_rotated(brick_d, bricksdict, keys_in_brick)
        if brick_type == "SLOPES":
            set_brick_type_for_slope(brick_d, bricksdict, keys_in_brick)


def get_new_parent_key_and_size(size, loc, zstep):
    # switch to origin brick
    loc = loc.copy()
    if size[0] < 0:
        loc[0] -= abs(size[0]) - 1
    if size[1] < 0:
        loc[1] -= abs(size[1]) - 1
    if size[2] < 0:
        loc[2] -= abs(size[2] // zstep) - 1
    new_key = list_to_str(loc)

    # store the biggest brick size to origin brick
    new_size = [abs(v) for v in size]

    return new_key, new_size


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


def brick_avail(bricksdict, target_key, brick_mat_name, merge_with_internals, material_type, merge_inconsistent_mats):
    """ check brick is available to merge """
    brick_d = bricksdict.get(target_key)
    # ensure brick exists and should be drawn
    if brick_d is None or not brick_d["draw"]:
        return False, brick_mat_name
    # ensure brick hasn't already been merged and is available for merging
    if brick_d["attempted_merge"] or not brick_d["available_for_merge"]:
        return False, brick_mat_name
    # ensure brick materials can be merged (same material or one of the mats is "" (internal)
    mats_mergable = brick_mat_name == brick_d["mat_name"] or (merge_with_internals and "" in (brick_mat_name, brick_d["mat_name"])) or merge_inconsistent_mats
    if not mats_mergable:
        return False, brick_mat_name
    # set brick material name if it wasn't already set
    elif brick_mat_name == "":
        brick_mat_name = brick_d["mat_name"]
    # ensure brick type is mergable
    if not mergable_brick_type(brick_d["type"], up=False):
        return False, brick_mat_name
    # passed all the checks; brick is available!
    return True, brick_mat_name


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
