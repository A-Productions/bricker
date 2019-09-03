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


def is_brick_exposed(bricksdict, zstep, key=None, loc=None):
    """ return top and bottom exposure of brick loc/key """
    assert key is not None or loc is not None
    # initialize vars
    key = key or list_to_str(loc)
    loc = loc or get_dict_loc(bricksdict, key)
    keys_in_brick = get_keys_in_brick(bricksdict, bricksdict[key]["size"], zstep, loc=loc)
    top_exposed, bot_exposed = False, False
    # top or bottom exposed if even one location is exposed
    for k in keys_in_brick:
        if bricksdict[k]["top_exposed"]: top_exposed = True
        if bricksdict[k]["bot_exposed"]: bot_exposed = True
    return top_exposed, bot_exposed


def set_all_brick_exposures(bricksdict, zstep, key=None, loc=None):
    """ updates top_exposed/bot_exposed for all bricks in bricksdict """
    assert key is not None or loc is not None
    # initialize vars
    key = key or list_to_str(loc)
    loc = loc or get_dict_loc(bricksdict, key)
    keys_in_brick = get_keys_in_brick(bricksdict, bricksdict[key]["size"], zstep, loc=loc)
    top_exposed, bot_exposed = False, False
    # set brick exposures
    for k in keys_in_brick:
        cur_top_exposed, cur_bot_exposed = set_brick_exposure(bricksdict, k)
        if cur_top_exposed: top_exposed = True
        if cur_bot_exposed: bot_exposed = True
    return top_exposed, bot_exposed


def set_brick_exposure(bricksdict, key=None, loc=None):
    """ set top and bottom exposure of brick loc/key """
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
    key_below = list_to_str((x, y, z - 1))
    key_above = list_to_str((x, y, z + 1))
    # check if brick top or bottom is exposed
    top_exposed = check_exposure(bricksdict, key_above, obscuring_types=get_types_obscuring_below())
    bot_exposed = check_exposure(bricksdict, key_below, obscuring_types=get_types_obscuring_above())
    brick_d["top_exposed"] = top_exposed
    brick_d["bot_exposed"] = bot_exposed
    return top_exposed, bot_exposed


def check_exposure(bricksdict, key, obscuring_types=[]):
    """ checks if brick at given key is exposed """
    try:
        val = bricksdict[key]["val"]
    except KeyError:
        return True
    parent_key = get_parent_key(bricksdict, key)
    typ = bricksdict[parent_key]["type"]
    return val == 0 or typ not in obscuring_types
