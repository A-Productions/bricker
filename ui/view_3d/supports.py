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


class VIEW3D_PT_bricker_supports(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Supports"
    bl_idname      = "VIEW3D_PT_bricker_supports"
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
        layout.active = cm.calc_internals

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "internal_supports", text="")
        if cm.internal_supports == "LATTICE":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "lattice_step")
            row = col.row(align=True)
            row.active == cm.lattice_step > 1
            row.prop(cm, "lattice_height")
            row = col.row(align=True)
            right_align(row)
            row.prop(cm, "alternate_xy")
        elif cm.internal_supports == "COLUMNS":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "col_thickness")
            row = col.row(align=True)
            row.prop(cm, "col_step")
