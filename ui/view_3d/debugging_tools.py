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
# NONE!

# Blender imports
import bpy
from bpy.types import Panel
from bpy.props import *

# Module imports
from ...functions import *


class VIEW3D_PT_bricker_debugging_tools(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Debugging Tools"
    bl_idname      = "VIEW3D_PT_bricker_debugging_tools"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        if bpy.props.bricker_developer_mode == 0:
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, n = get_active_context_info()

        layout.operator("bricker.generate_brick", icon="MOD_BUILD")
        layout.operator("bricker.debug_toggle_view_source", icon="RESTRICT_VIEW_OFF" if cm.source_obj.name in scn.collection.objects else "RESTRICT_VIEW_ON")
