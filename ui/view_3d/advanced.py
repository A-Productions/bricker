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
from ...operators.customization_tools.bricksculpt import *
from ...operators.test_brick_generators import *
from ...functions import *
from ... import addon_updater_ops


class VIEW3D_PT_bricker_advanced(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Advanced"
    bl_idname      = "VIEW3D_PT_bricker_advanced"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        # right_align(layout)
        scn, cm, n = get_active_context_info()

        # Alert user that update is available
        if addon_updater_ops.updater.update_ready:
            col = layout.column(align=True)
            col.scale_y = 0.7
            col.label(text="Bricker update available!", icon="INFO")
            col.label(text="Install from Bricker addon prefs")
            layout.separator()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("bricker.clear_cache", text="Clear Cache")

        # if not b280():
        #     VIEW3D_PT_bricker_advanced_ray_casting.draw(self, context)
        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Ray Casting:")
        row = col.row(align=True)
        row.prop(cm, "insideness_ray_cast_dir", text="")
        row = col.row(align=True)
        row.prop(cm, "use_normals")
        row = col.row(align=True)
        row.prop(cm, "verify_exposure")
        row = col.row(align=True)
        row.prop(cm, "calc_internals")
        row = col.row(align=True)
        row.prop(cm, "brick_shell", text="Shell")
        if cm.brick_shell == "OUTSIDE":
            row = col.row(align=True)
            row.prop(cm, "calculation_axes", text="")

        # if not cm.animated:
        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Meshes:")
        row = col.row(align=True)
        row.prop(cm, "instance_method", text="")

        # model orientation preferences
        if not cm.use_animation and not (cm.model_created or cm.animated):
            # if not b280():
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Model Orientation:")
            row = col.row(align=True)
            col.prop(cm, "use_local_orient", text="Use Local Orientation")

        # background processing preferences
        if cm.use_animation and get_addon_preferences().brickify_in_background != "OFF":
            col = layout.column(align=True)
            # if not b280():
            row = col.row(align=True)
            row.label(text="Background Processing:")
            row = col.row(align=True)
            row.prop(cm, "max_workers")

        # draw test brick generator button (for testing purposes only)
        if BRICKER_OT_test_brick_generators.draw_ui_button():
            col = layout.column(align=True)
            col.operator("bricker.test_brick_generators", text="Test Brick Generators", icon="OUTLINER_OB_MESH")
