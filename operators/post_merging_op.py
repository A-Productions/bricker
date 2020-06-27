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
import time
import os

# Blender imports
import bpy
from bpy.types import Operator

# Module imports
from ..functions import *


class BRICKER_OT_run_post_merging(Operator):
    """Grow bricks by merging nearby bricks that fit together"""
    bl_idname = "bricker.run_post_merging"
    bl_label = "Run Post Merging"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if not cm.model_created or cm.animated:
            return False
        return True

    def execute(self, context):
        try:
            # initialize vars
            scn, cm, n = get_active_context_info()
            zstep = get_zstep(cm)
            bricksdict = get_bricksdict(cm)
            keys = bricksdict.keys()
            brick_type = cm.brick_type
            legal_bricks_only = cm.legal_bricks_only
            max_length = 8  # max(cm.max_width, cm.max_depth)
            # run post merging
            updated_keys = set()
            all_engulfed_keys = set()
            for key in keys:
                # skip non-parent keys (must check each time as this is constantly changing)
                if bricksdict[key]["parent"] != "self":
                    continue
                success, engulfed_keys = attempt_post_merge(bricksdict, key, zstep, brick_type, legal_bricks_only, max_length=max_length)
                if success:
                    updated_keys.add(key)
                    all_engulfed_keys |= engulfed_keys
            # redraw merged bricks
            deselect_all()
            draw_updated_bricks(cm, bricksdict, list(updated_keys))
            # remove engulfed bricks
            for k in all_engulfed_keys:
                delete(bpy.data.objects.get(bricksdict[k]["name"]))
            # report how many keys were merged
            num_bricks_merged = len(all_engulfed_keys) + len(updated_keys)
            report_str = f"{num_bricks_merged} bricks merged!"
            self.report({"INFO"}, report_str)
            print(report_str)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ################################################
    # class methods

    # NONE!

    ################################################
