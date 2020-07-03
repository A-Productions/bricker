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
from ..lib.undo_stack import *


class BRICKER_OT_run_post_hollowing(Operator):
    """Remove internal bricks that don't introduce new weak points/connected components"""
    bl_idname = "bricker.run_post_hollowing"
    bl_label = "Run Post Hollowing"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if not cm.model_created:
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
            parent_keys = get_parent_keys(bricksdict)
            brick_type = cm.brick_type
            merge_seed = cm.merge_seed
            connect_thresh = cm.connect_thresh
            # run post hollowing
            _, num_removed_bricks = run_post_hollowing(bricksdict, keys, parent_keys, cm, zstep, brick_type, remove_object=True, subgraph_radius=cm.post_hollow_subgraph_radius)
            # report how many keys were removed
            report_str = f"{num_removed_bricks} unnecessary internal bricks removed"
            self.report({"INFO"}, report_str)
            print(report_str)
            # set last_post_hollowing to True
            cm.last_post_hollowing = True
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
