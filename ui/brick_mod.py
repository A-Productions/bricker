"""
Copyright (C) 2017 Bricks Brought to Life
http://bblanimation.com/
chris@bblanimation.com

Created by Christopher Gearhart

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# System imports
# NONE!

# Blender imports
import bpy
from addon_utils import check, paths, enable
from bpy.types import Panel
from bpy.props import *
props = bpy.props

# Rebrickr imports
from .cmlist import *
from .app_handlers import *
from .buttons import *
from ..lib.bricksDict import *
from ..buttons.delete import RebrickrDelete
from ..functions import *
from ..lib.caches import rebrickr_bfm_cache

# updater import
from .. import addon_updater_ops

class RebrickrBrickModPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Brick Mods"
    bl_idname      = "VIEW3D_PT_tools_Rebrickr_brick_mods"
    # bl_context     = "objectmode"
    bl_category    = "Rebrickr"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if not (cm.modelCreated or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]

        if cm.matrixIsDirty and cm.lastMatrixSettings != getMatrixSettings():
            layout.label("Matrix is dirty!")
            return
        if cm.animated:
            layout.label("Not available for animations")
            return
        if not cm.lastSplitModel:
            layout.label("Split model for brick mods")
            return
        if cm.buildIsDirty:
            layout.label("Run 'Update Model' for brick mods")
            return

        col1 = layout.column(align=True)
        col1.label("Toggle Exposure:")
        split = col1.split(align=True, percentage=0.5)
        # set top exposed
        col = split.column(align=True)
        col.operator("rebrickr.set_exposure", text="Top").side = "TOP"
        # set bottom exposed
        col = split.column(align=True)
        col.operator("rebrickr.set_exposure", text="Bottom").side = "BOTTOM"

        col1 = layout.column(align=True)
        col1.label("Brick Operations:")
        split = col1.split(align=True, percentage=0.5)
        # split brick into 1x1s
        col = split.column(align=True)
        col.operator("rebrickr.split_bricks", text="Split")
        # merge selected bricks
        col = split.column(align=True)
        col.operator("rebrickr.merge_bricks", text="Merge")
        # Add identical brick on +/- x/y/z
        row = col1.row(align=True)
        row.operator("rebrickr.draw_adjacent", text="Draw Adjacent Bricks")
        # change brick type
        row = col1.row(align=True)
        row.operator("rebrickr.change_brick_type", text="Change Type")
        # additional controls
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "autoUpdateExposed")
        row = col.row(align=True)
        row.operator("rebrickr.redraw_bricks")


        # next level:
        # enter brick sculpt mode
        # add brick at selected vertex

class RebrickrBrickDetailsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Brick Details"
    bl_idname      = "VIEW3D_PT_tools_Rebrickr_brick_details"
    # bl_context     = "objectmode"
    bl_category    = "Rebrickr"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if not (cm.modelCreated or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]

        if cm.matrixIsDirty and cm.lastMatrixSettings != getMatrixSettings():
            layout.label("Matrix is dirty!")
            return
        if rebrickr_bfm_cache.get(cm.id) is None and cm.BFMCache == "":
            layout.label("Matrix not cached!")
            return

        col1 = layout.column(align=True)
        split = col1.split(align=True, percentage=0.33)
        col = split.column(align=True)
        col.prop(cm, "activeKeyX", text="x")
        col = split.column(align=True)
        col.prop(cm, "activeKeyY", text="y")
        col = split.column(align=True)
        col.prop(cm, "activeKeyZ", text="z")

        if cm.animated:
            bricksDict,_ = getBricksDict("UPDATE_ANIM", cm=cm, curFrame=getAnimAdjustedFrame(cm, scn.frame_current), restrictContext=True)
        elif cm.modelCreated:
            bricksDict,_ = getBricksDict("UPDATE_MODEL", cm=cm, restrictContext=True)
        if bricksDict is None:
            layout.label("Matrix not available")
            return
        aKX = cm.activeKeyX
        aKY = cm.activeKeyY
        aKZ = cm.activeKeyZ
        try:
            dictKey = listToStr([aKX, aKY, aKZ])
            brickD = bricksDict[dictKey]
        except Exception as e:
            layout.label("No brick details available")
            if len(bricksDict) == 0:
                print("Skipped drawing Brick Details")
            elif str(e)[1:-1] == dictKey:
                print("Key '" + str(dictKey) + "' not found")
                # try:
                #     print("Num Keys:", str(len(bricksDict)))
                # except:
                #     pass
            elif dictKey is None:
                print("Key not set (entered else)")
            else:
                print("Error fetching brickD:", e)
            return

        col1 = layout.column(align=True)
        split = col1.split(align=True, percentage=0.35)
        # hard code keys so that they are in the order I want
        keys = ["name", "val", "draw", "co", "nearest_face_idx", "mat_name", "parent_brick", "size", "attempted_merge", "top_exposed", "bot_exposed", "type"]
        # draw keys
        col = split.column(align=True)
        col.scale_y = 0.65
        row = col.row(align=True)
        row.label("key:")
        for key in keys:
            row = col.row(align=True)
            row.label(key + ":")
        # draw values
        col = split.column(align=True)
        col.scale_y = 0.65
        row = col.row(align=True)
        row.label(dictKey)
        for key in keys:
            row = col.row(align=True)
            row.label(str(brickD[key]))
