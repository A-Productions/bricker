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
import numpy as np
import colorsys

# Module imports
from .general import *


def get_colors():
    if not hasattr(get_colors, "colors"):
        colors = {}
        mat_properties = bpy.props.abs_mat_properties
        for key in mat_properties.keys():
            colors[key] = mat_properties[key]["Color" if "Trans-" in key else "Diffuse Color"]
        get_colors.colors = colors
    return get_colors.colors


def find_nearest_brick_color_name(rgba, trans_weight, mat_obj=None):
    if rgba is None:
        return ""
    colors = get_colors().copy()
    if mat_obj is not None:
        for k in list(colors.keys()):  # copy keys list as it will change during iteration
            if k not in mat_obj.data.materials.keys():
                colors.pop(k, None)
    return find_nearest_color_name(rgba, trans_weight, colors)


def find_nearest_color_name(rgba, trans_weight, colors):
    mindiff = None
    mincolorname = ""
    for color_name in colors:
        diff = distance(rgba, colors[color_name], trans_weight)
        if mindiff is None or diff < mindiff:
            mindiff = diff
            mincolorname = color_name
    return mincolorname


def get_first_img_from_nodes(obj, mat_slot_idx):
    """ return first image texture found in a material slot """
    mat = obj.material_slots[mat_slot_idx].material
    if mat is None or not mat.use_nodes:
        return None
    nodes_to_check = list(mat.node_tree.nodes)
    active_node = mat.node_tree.nodes.active
    if active_node is not None: nodes_to_check.insert(0, active_node)
    img = None
    for node in nodes_to_check:
        if node.type != "TEX_IMAGE":
            continue
        img = verify_img(node.image)
        if img is not None:
            break
    return img


def get_uv_image(scn, obj, face_idx, uv_image=None):
    """ returns UV image (priority to passed image, then face index, then first one found in material nodes) """
    image = verify_img(uv_image)
    # TODO: Reinstate this functionality for b280()
    if not b280() and image is None and obj.data.uv_textures.active:
        image = verify_img(obj.data.uv_textures.active.data[face_idx].image)
    if image is None:
        try:
            mat_idx = obj.data.polygons[face_idx].material_index
            image = verify_img(get_first_img_from_nodes(obj, mat_idx))
        except IndexError:
            mat_idx = 0
            while image is None and mat_idx < len(obj.material_slots):
                image = verify_img(get_first_img_from_nodes(obj, mat_idx))
                mat_idx += 1
    return image


def get_pixels(image):
    if image.name in bricker_pixel_cache:
        return bricker_pixel_cache[image.name]
    else:
        pixels = image.pixels[:]
        bricker_pixel_cache[image.name] = pixels
        return pixels


def get_uv_pixel_color(scn, obj, face_idx, point, pixels, uv_image=None):
    """ get RGBA value for point in UV image at specified face index """
    if face_idx is None:
        return None
    # get closest material using UV map
    face = obj.data.polygons[face_idx]
    # get uv_layer image for face
    image = get_uv_image(scn, obj, face_idx, uv_image)
    if image is None:
        return None
    # get uv coordinate based on nearest face intersection
    uv_coord = get_uv_coord(obj.data, face, point, image)
    # retrieve rgba value at uv coordinate
    pixels = get_pixels(image)
    rgba = get_pixel(pixels, image.size[0], uv_coord)
    return rgba
