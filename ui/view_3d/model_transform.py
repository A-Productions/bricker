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
from addon_utils import check, paths, enable
from bpy.types import Panel
from bpy.props import *

# Module imports
from ..created_model_uilist import *
from ..matslot_uilist import *
from ...lib.caches import cache_exists
from ...operators.revert_settings import *
from ...operators.brickify import *
from ...functions import *
from ... import addon_updater_ops


class VIEW3D_PT_bricker_model_transform(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Model Transform"
    bl_idname      = "VIEW3D_PT_bricker_model_transform"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if cm.model_created or cm.animated:
            return True
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, n = get_active_context_info()

        col = layout.column(align=True)
        right_align(col)
        row = col.row(align=True)

        if not (cm.animated or cm.last_split_model):
            col.scale_y = 0.7
            row.label(text="Use Blender's built-in")
            row = col.row(align=True)
            row.label(text="transformation manipulators")
            col = layout.column(align=True)
            return

        row.prop(cm, "apply_to_source_object")
        if cm.animated or (cm.last_split_model and cm.model_created):
            row = col.row(align=True)
            row.prop(cm, "expose_parent")
        row = col.row(align=True)
        parent = bpy.data.objects["Bricker_%(n)s_parent" % locals()]
        row = layout.row()
        row.column().prop(parent, "location")
        if parent.rotation_mode == "QUATERNION":
            row.column().prop(parent, "rotation_quaternion", text="Rotation")
        elif parent.rotation_mode == "AXIS_ANGLE":
            row.column().prop(parent, "rotation_axis_angle", text="Rotation")
        else:
            row.column().prop(parent, "rotation_euler", text="Rotation")
        # row.column().prop(parent, "scale")
        layout.prop(parent, "rotation_mode")
        layout.prop(cm, "transform_scale")
