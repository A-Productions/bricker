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
from ...functions import *
from ... import addon_updater_ops


class VIEW3D_PT_bricker_customize(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Customize Model"
    bl_idname      = "VIEW3D_PT_bricker_customize"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if created_with_unsupported_version(cm):
            return False
        if not (cm.model_created or cm.animated):
            return False
        if cm.last_instance_method == "POINT_CLOUD":
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        if matrix_really_is_dirty(cm):
            layout.label(text="Matrix is dirty!")
            col = layout.column(align=True)
            col.label(text="Model must be updated to customize:")
            col.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH")
            if cm.customized and not cm.matrix_lost:
                row = col.row(align=True)
                row.label(text="Prior customizations will be lost")
                row = col.row(align=True)
                row.operator("bricker.revert_matrix_settings", text="Revert Settings", icon="LOOP_BACK")
            return
        if cm.animated:
            layout.label(text="Not available for animations")
            return
        if not cm.last_split_model:
            col = layout.column(align=True)
            col.label(text="Model must be split to customize:")
            col.operator("bricker.brickify", text="Split & Update Model", icon="FILE_REFRESH").split_before_update = True
            return
        if cm.build_is_dirty:
            col = layout.column(align=True)
            col.label(text="Model must be updated to customize:")
            col.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH")
            return
        if cm.brickifying_in_background:
            col = layout.column(align=True)
            col.label(text="Model is brickifying...")
            return
        elif not cache_exists(cm):
            layout.label(text="Matrix not cached!")
            col = layout.column(align=True)
            col.label(text="Model must be updated to customize:")
            col.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH")
            if cm.customized:
                row = col.row(align=True)
                row.label(text="Customizations will be lost")
                row = col.row(align=True)
                row.operator("bricker.revert_matrix_settings", text="Revert Settings", icon="LOOP_BACK")
            return
        # if not bpy.props.bricker_initialized:
        #     layout.operator("bricker.initialize", icon="MODIFIER")
        #     return

        # display BrickSculpt tools
        col = layout.column(align=True)
        row = col.row(align=True)
        # brickSculptInstalled = hasattr(bpy.props, "bricksculpt_module_name")
        # row.active = brickSculptInstalled
        col.active = False
        row.label(text="BrickSculpt Tools:")
        row = col.row(align=True)
        row.operator("bricker.bricksculpt", text="Draw/Cut Tool", icon="MOD_DYNAMICPAINT").mode = "DRAW"
        row = col.row(align=True)
        row.operator("bricker.bricksculpt", text="Merge/Split Tool", icon="MOD_DYNAMICPAINT").mode = "MERGE/SPLIT"
        row = col.row(align=True)
        row.operator("bricker.bricksculpt", text="Paintbrush Tool", icon="MOD_DYNAMICPAINT").mode = "PAINT"
        row.prop_search(cm, "paintbrush_mat", bpy.data, "materials", text="")
        if not BRICKER_OT_bricksculpt.bricksculpt_installed:
            row = col.row(align=True)
            row.scale_y = 0.7
            row.label(text="BrickSculpt available for purchase")
            row = col.row(align=True)
            row.scale_y = 0.7
            row.label(text="at the Blender Market:")
            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator("wm.url_open", text="View Website", icon="WORLD").url = "http://www.blendermarket.com/products/bricksculpt"
            layout.split()
            layout.split()

        col1 = layout.column(align=True)
        col1.label(text="Selection:")
        split = layout_split(col1, factor=0.5)
        # set top exposed
        col = split.column(align=True)
        col.operator("bricker.select_bricks_by_type", text="By Type")
        # set bottom exposed
        col = split.column(align=True)
        col.operator("bricker.select_bricks_by_size", text="By Size")

        col1 = layout.column(align=True)
        col1.label(text="Toggle Exposure:")
        split = layout_split(col1, factor=0.5)
        # set top exposed
        col = split.column(align=True)
        col.operator("bricker.set_exposure", text="Top").side = "TOP"
        # set bottom exposed
        col = split.column(align=True)
        col.operator("bricker.set_exposure", text="Bottom").side = "BOTTOM"

        col1 = layout.column(align=True)
        col1.label(text="Brick Operations:")
        split = layout_split(col1, factor=0.5)
        # split brick into 1x1s
        col = split.column(align=True)
        col.operator("bricker.split_bricks", text="Split")
        # merge selected bricks
        col = split.column(align=True)
        col.operator("bricker.merge_bricks", text="Merge")
        # Add identical brick on +/- x/y/z
        row = col1.row(align=True)
        row.operator("bricker.draw_adjacent", text="Draw Adjacent Bricks")
        # change brick type
        row = col1.row(align=True)
        row.operator("bricker.change_brick_type", text="Change Type")
        # change material type
        row = col1.row(align=True)
        row.operator("bricker.change_brick_material", text="Change Material")
        # additional controls
        row = col1.row(align=True)
        right_align(row)
        row.prop(cm, "auto_update_on_delete")
        # row = col.row(align=True)
        # row.operator("bricker.redraw_bricks")
