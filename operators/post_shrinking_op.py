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


class BRICKER_OT_run_post_shrinking(Operator):
    """Shrink internal bricks, removing locs that are exposed above and below"""
    bl_idname = "bricker.run_post_shrinking"
    bl_label = "Run Post Shrinking"
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
            self.undo_stack.iterate_states(cm)
            zstep = get_zstep(cm)
            bricksdict = get_bricksdict(cm)
            keys = bricksdict.keys()
            brick_type = cm.brick_type
            legal_bricks_only = cm.legal_bricks_only
            material_type = cm.material_type
            custom_mat = cm.custom_mat
            random_mat_seed = cm.random_mat_seed
            # run post merging
            updated_keys, num_shrunk_bricks = run_post_shrinking(bricksdict, keys, zstep, brick_type, legal_bricks_only)
            parent_keys = get_parent_keys(bricksdict, keys)
            update_bricksdict_after_updated_build(bricksdict, parent_keys, zstep, cm, material_type, custom_mat, random_mat_seed)
            # redraw merged bricks
            deselect_all()
            draw_updated_bricks(cm, bricksdict, updated_keys)
            # report how many keys were merged
            report_str = f"{num_shrunk_bricks} bricks shrunk"
            self.report({"INFO"}, report_str)
            print(report_str)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, n = get_active_context_info()
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.cached_bfm = self.undo_stack.undo_push("post-hollowing", affected_ids=[cm.id])

    ################################################
    # class methods

    # NONE!

    ################################################
