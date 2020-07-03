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
import random
import time

# Blender imports
import bpy

# Module imports
from .bricksdict import *
from .brick import split_bricks
from .customize_utils import merge_bricks
from .improve_sturdiness import *
from .make_bricks_utils import *


def run_post_merging(bricksdict, keys, zstep, brick_type, legal_bricks_only, merge_internals_h, merge_internals_v, max_width, max_depth):
    """ attempt to merge bricks further that have already been merged, preserving structural integrity """
    # initialize vars
    updated_keys = set()
    all_engulfed_keys = set()
    # attempt post-merge for keys passed to this function
    for i, key in enumerate(keys):
        # skip non-parent keys (must check each time as this is constantly changing)
        if bricksdict[key]["parent"] != "self":
            continue
        success, engulfed_keys = attempt_post_merge(bricksdict, key, zstep, brick_type, legal_bricks_only, merge_internals_h, merge_internals_v, max_width, max_depth)
        if success:
            updated_keys.add(key)
            all_engulfed_keys |= engulfed_keys
    # return updated keys
    return updated_keys, all_engulfed_keys
