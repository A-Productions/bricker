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
import time
import os

# Blender imports
import bpy
from bpy.types import Operator

# Module imports
from ..functions import *


class BRICKER_OT_refresh_model_info(Operator):
    """Refresh all model statistics"""
    bl_idname = "bricker.refresh_model_info"
    bl_label = "Refresh Model Info"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        return True

    def execute(self, context):
        try:
            if self.bricksdict is None:
                self.report({"WARNING"}, "Could not refresh model info - model is not cached")
                return {"CANCELLED"}
            self.set_model_info()
            return{"FINISHED"}
        except:
            bricker_handle_exception()
            return {"CANCELLED"}

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, _ = get_active_context_info()
        self.bricksdict = get_bricksdict(cm, d_type="MODEL" if cm.model_created else "ANIM", cur_frame=scn.frame_current)

    ###################################################
    # class variables

    # NONE!

    ################################################
    # class methods

    def set_model_info(self, cm=None):
        scn, cm = get_active_context_info(cm)[:2]
        legal_bricks = get_legal_bricks()
        num_bricks_in_model = 0
        model_weight = 0
        mats_in_model = list()
        max_vals = (0, 0, 0)
        z_max = 0
        for k, brick_d in self.bricksdict.items():
            if not brick_d["draw"]:
                continue
            if brick_d["parent"] == "self":
                dict_loc = get_dict_loc(self.bricksdict, k)
                max_vals = (max(max_vals[0], dict_loc[0] + brick_d["size"][0] - 1), max(max_vals[1], dict_loc[1] + brick_d["size"][1] - 1), max(max_vals[2], dict_loc[2] + brick_d["size"][2] - 1))
                num_bricks_in_model += 1
                if brick_d["mat_name"] not in mats_in_model:
                    mats_in_model.append(brick_d["mat_name"])
                model_weight += get_part(legal_bricks, brick_d["size"], brick_d["type"])["wt"]
        if "" in mats_in_model:
            mats_in_model.remove("")

        dimensions = get_brick_dimensions(0.000096, cm.zstep, cm.gap)
        model_dims = (
            max_vals[0] * dimensions["width"],
            max_vals[1] * dimensions["width"],
            max_vals[2] * dimensions["height"],
        )

        cm.num_bricks_in_model = num_bricks_in_model
        cm.num_materials_in_model = len(mats_in_model)
        cm.real_world_dimensions = model_dims
        cm.model_weight = model_weight

    ################################################
