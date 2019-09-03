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


class BRICKER_OT_revert_settings(Operator):
    """Revert Matrix settings to save model customizations"""
    bl_idname = "bricker.revert_matrix_settings"
    bl_label = "Revert Matrix Settings"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns False) """
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if matrix_really_is_dirty(cm):
            return True
        return False

    def execute(self, context):
        try:
            self.revert_matrixSettings()
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ################################################
    # class methods

    def revert_matrixSettings(self, cm=None):
        cm = cm or get_active_context_info()[1]
        settings = cm.last_matrix_settings.split(",")
        cm.brick_height = float(settings[0])
        cm.gap = float(settings[1])
        cm.brick_type = settings[2]
        cm.dist_offset[0] = float(settings[3])
        cm.dist_offset[1] = float(settings[4])
        cm.dist_offset[2] = float(settings[5])
        cm.include_transparency = str_to_bool(settings[6])
        cm.custom_object1 = bpy.data.objects.get(settings[7])
        cm.custom_object2 = bpy.data.objects.get(settings[8])
        cm.custom_object3 = bpy.data.objects.get(settings[9])
        cm.use_normals = str_to_bool(settings[10])
        cm.verify_exposure = str_to_bool(settings[11])
        cm.insideness_ray_cast_dir = settings[12]
        cm.brick_shell = settings[14]
        cm.calculation_axes = settings[15]
        if cm.last_is_smoke:
            cm.smoke_density = settings[16]
            cm.smoke_quality = settings[17]
            cm.smoke_brightness = settings[18]
            cm.smoke_saturation = settings[19]
            cm.flame_color[0] = settings[20]
            cm.flame_color[1] = settings[21]
            cm.flame_color[2] = settings[22]
            cm.flame_intensity = settings[23]
        cm.matrix_is_dirty = False

    ################################################
