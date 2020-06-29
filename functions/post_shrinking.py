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


def run_post_shrinking(bricksdict, keys, zstep, brick_type, legal_bricks_only):
    """ Iterate over and shrink if part of the brick isn't connected above or below and isn't on shell """
    # get all parent keys of bricks exclusively inside the model
    parent_keys = get_parent_keys(bricksdict)
    # initialize vars
    updated_keys = set()
    num_shrunk_bricks = 0
    # initialize progress bar
    old_percent = update_progress_bars(0.0, -1, "Post-Shrinking")
    # iterate through parent keys and attempt to shrink
    for i, k in enumerate(parent_keys):
        success, removed_keys = attempt_post_shrink(bricksdict, k, zstep, brick_type, legal_bricks_only)
        if success:
            updated_keys.add(k)
            num_shrunk_bricks += 1
        # print status to terminal and cursor
        cur_percent = (i / len(parent_keys))
        old_percent = update_progress_bars(cur_percent, old_percent, "Post-Shrinking")
    # end progress bar
    update_progress_bars(1, 0, "Post-Shrinking", end=True)
    # return all removed keys (including all keys in brick) along with num shrunk bricks
    return updated_keys, num_shrunk_bricks
