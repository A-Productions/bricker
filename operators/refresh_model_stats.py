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
        if matrix_really_is_dirty(cm):
            return True
        return False

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
        cm.num_bricks_in_model = -1
        cm.num_materials_in_model = -1
        cm.real_world_dimensions = (-1, -1)

    ################################################
