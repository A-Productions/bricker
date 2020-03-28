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


class VIEW3D_PT_bricker_brick_types(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Brick Types"
    bl_idname      = "VIEW3D_PT_bricker_brick_types"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "brick_type", text="")

        if mergable_brick_type(cm.brick_type):
            col = layout.column(align=True)
            col.active = cm.instance_method != "POINT_CLOUD"
            col.label(text="Max Brick Size:")
            row = col.row(align=True)
            row.prop(cm, "max_width", text="Width")
            row.prop(cm, "max_depth", text="Depth")
            col.active = cm.instance_method != "POINT_CLOUD"
            row = col.row(align=True)
            right_align(row)
            row.prop(cm, "legal_bricks_only")

        col = layout.column(align=True)
        if cm.brick_type == "CUSTOM":
            col.label(text="Brick Type Object:")
        elif cm.last_split_model:
            col.label(text="Custom Brick Objects:")
        if cm.brick_type == "CUSTOM" or cm.last_split_model:
            for prop in ("custom_object1", "custom_object2", "custom_object3"):
                if prop[-1] == "2" and cm.brick_type == "CUSTOM":
                    col.label(text="Distance Offset:")
                    row = col.row(align=True)
                    row.prop(cm, "dist_offset", text="")
                    if cm.last_split_model:
                        col = layout.column(align=True)
                        col.label(text="Other Objects:")
                    else:
                        break
                split = layout_split(col, factor=0.825)
                col1 = split.column(align=True)
                col1.prop_search(cm, prop, scn, "objects", text="")
                col1 = split.column(align=True)
                col1.operator("bricker.redraw_custom_bricks", icon="FILE_REFRESH", text="").target_prop = prop
