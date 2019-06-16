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
import copy

# Blender imports
import bpy
from bpy.types import Operator

# Addon imports
from ...functions import *
from ....brickify import *
from ....brickify import *
from .....functions import *


class BRICKER_OT_select_bricks_by_size(Operator):
    """Select bricks of specified size"""
    bl_idname = "bricker.select_bricks_by_size"
    bl_label = "Select Bricks by Size"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns False) """
        return bpy.props.bricker_initialized

    def execute(self, context):
        try:
            selectBricks(self.objNamesD, self.bricksDicts, brickSize=self.brickSize, allModels=self.allModels, only=self.only, include=self.include)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def check(self, context):
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = getActiveContextInfo()

        col = layout.column(align=True)
        right_align(col)
        col.prop(self, "brickSize")
        if len(bpy.context.selected_objects) > 0:
            col.prop(self, "only")
        if len(scn.cmlist) > 1:
            col.prop(self, "allModels")
        if cm.lastShellThickness > 1 or cm.lastInternalSupports != "NONE":
            col.prop(self, "include")

    ################################################
    # initialization method

    def __init__(self):
        objs = bpy.data.objects
        self.objNamesD, self.bricksDicts = createObjNamesAndBricksDictsDs(objs)
        self.brickSize = "NONE"

    ###################################################
    # class variables

    # vars
    objNamesD = {}
    bricksDicts = {}

    # get items for brickSize prop
    def get_items(self, context):
        items = getUsedSizes()
        return items

    # define props for popup
    brickSize = bpy.props.EnumProperty(
        name="Size",
        description="Select all bricks of specified size (X, Y, Z)",
        items=get_items)
    only = bpy.props.BoolProperty(
        name="Only",
        description="Select only bricks of given size",
        default=False)
    allModels = bpy.props.BoolProperty(
        name="All Models",
        description="Select bricks of given size from all models in file",
        default=False)
    include = bpy.props.EnumProperty(
        name="Include",
        description="Include bricks on shell, inside shell, or both",
        items = [("EXT", "Externals", ""),
                 ("INT", "Internals", ""),
                 ("BOTH", "Both", "")])

    ###################################################
