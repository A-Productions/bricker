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

# Module imports
from ..functions import *
from .cmlist_actions import *


class BRICKER_OT_bake_model(bpy.types.Operator):
    """Convert model from Bricker model to standard Blender object (applies transformation and clears Bricker data associated with the model; source object will be lost)"""
    bl_idname = "bricker.bake_model"
    bl_label = "Bake Model"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        try:
            scn, cm, n = get_active_context_info(context)
        except IndexError:
            return False
        if (cm.model_created or cm.animated) and not cm.brickifying_in_background:
            return True
        return False

    def execute(self, context):
        return {"FINISHED"}

    ################################################
