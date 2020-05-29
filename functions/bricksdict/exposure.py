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


def set_brick_exposure(bricksdict, zstep, key=None, loc=None):
    assert key is not None or loc is not None
    # initialize vars
    key = key or list_to_str(loc)
    loc = loc or get_dict_loc(bricksdict, key)
    keys_in_brick = get_keys_in_brick(bricksdict, bricksdict[key]["size"], zstep, loc=loc)
    top_exposed, bot_exposed = False, False
    # set brick exposures
    for k in keys_in_brick:
        cur_top_exposed, cur_bot_exposed = check_brickd_exposure(bricksdict, k)
        if cur_top_exposed: top_exposed = True
        if cur_bot_exposed: bot_exposed = True
    bricksdict[key]["top_exposed"] = top_exposed
    bricksdict[key]["bot_exposed"] = bot_exposed
    return top_exposed, bot_exposed


def check_brickd_exposure(bricksdict, key=None, loc=None):
    """ check top and bottom exposure of single bricksdict loc/key """
    assert key is not None or loc is not None
    # initialize parameters unspecified
    loc = loc or get_dict_loc(bricksdict, key)
    key = key or list_to_str(loc)
    # get size of brick and break conditions
    try:
        brick_d = bricksdict[key]
    except KeyError:
        return None, None
    # get keys above and below
    x, y, z = loc
    key_above = list_to_str((x, y, z + 1))
    key_below = list_to_str((x, y, z - 1))
    # check if brickd top or bottom is exposed
    top_exposed = check_if_brick_obscures(bricksdict, key_above, direction="BELOW")
    bot_exposed = check_if_brick_obscures(bricksdict, key_below, direction="ABOVE")
    return top_exposed, bot_exposed


def check_if_brick_obscures(bricksdict, key, direction="ABOVE"):
    """ checks if brick obscures the bricks either above or below it """
    try:
        val = bricksdict[key]["val"]
    except KeyError:
        return True
    parent_key = get_parent_key(bricksdict, key)
    typ = bricksdict[parent_key]["type"]
    return val == 0 or typ not in get_obscuring_types(direction)
