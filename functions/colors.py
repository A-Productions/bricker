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

# Addon imports
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


def distance(c1, c2, awt=1):
    r1, g1, b1, a1 = c1
    r2, g2, b2, a2 = c2
    # a1 = c1[3]
    # # r1, g1, b1 = rgb_to_lab(c1[:3])
    # r1, g1, b1 = colorsys.rgb_to_hsv(r1, g1, b1)
    # a2 = c2[3]
    # # r2, g2, b2 = rgb_to_lab(c2[:3])
    # r2, g2, b2 = colorsys.rgb_to_hsv(r1, g1, b1)
    # diff =  0.33 * ((r1 - r2)**2)
    # diff += 0.33 * ((g1 - g2)**2)
    # diff += 0.33 * ((b1 - b2)**2)
    # diff += 1.0 * ((a1 - a2)**2)
    diff =  0.30 * ((r1 - r2)**2)
    diff += 0.59 * ((g1 - g2)**2)
    diff += 0.11 * ((b1 - b2)**2)
    diff += awt * ((a1 - a2)**2)
    return diff


def find_nearest_color_name(rgba, trans_weight, colors):
    mindiff = None
    mincolorname = ""
    for color_name in colors:
        diff = distance(rgba, colors[color_name], trans_weight)
        if mindiff is None or diff < mindiff:
            mindiff = diff
            mincolorname = color_name
    return mincolorname
