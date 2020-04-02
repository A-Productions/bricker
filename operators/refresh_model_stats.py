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


class BRICKER_OT_refresh_model_stats(Operator):
    """Refresh all model statistics"""
    bl_idname = "bricker.refresh_model_stats"
    bl_label = "Refresh Model Stats"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if not (cm.model_created or cm.animated):
            return False
        return True

    def execute(self, context):
        try:
            self.refresh_model_stats()
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ################################################
    # class methods

    def refresh_model_stats(self, cm=None):
        scn, cm = get_active_context_info(cm)[:2]
        bricksdict = get_bricksdict(cm, d_type="MODEL" if cm.model_created else "ANIM", cur_frame=scn.frame_current)
        legal_bricks = get_legal_bricks()
        num_bricks_in_model = 0
        model_weight = 0
        mats_in_model = list()
        max_vals = (0, 0, 0)
        z_max = 0
        for k in bricksdict.keys():
            brick_d = bricksdict[k]
            if brick_d["draw"] and brick_d["parent"] == "self":
                num_bricks_in_model += 1
                if brick_d["mat_name"] not in mats_in_model:
                    mats_in_model.append(brick_d["mat_name"])
                    dict_loc = get_dict_loc(bricksdict, k)
                    max_vals = (max(max_vals[0], dict_loc[0]), max(max_vals[1], dict_loc[1]), max(max_vals[2], dict_loc[2]))
                model_weight += get_part(legal_bricks, brick_d["size"], brick_d["type"])["wt"]

        # min_co = Vector(brick_d["0,0,0"]["co"])
        # max_co = Vector((
        #     brick_d["{},0,0".format(z_max)]["co"].x,
        #     brick_d["0,{},0".format(z_max)]["co"].y,
        #     brick_d["0,0,{}".format(z_max)]["co"].z,
        # ))
        dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
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
