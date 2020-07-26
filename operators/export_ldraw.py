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
import json

# Blender imports
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper#, path_reference_mode
from bpy.props import *

# Module imports
from ..functions import *
from ..functions.property_callbacks import get_build_order_items


class BRICKER_OT_export_ldraw(Operator, ExportHelper):
    """Export active brick model to ldraw file"""
    bl_idname = "bricker.export_ldraw"
    bl_label = "Export LDR"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        return False

    def execute(self, context):
        return{"FINISHED"}

    #############################################
    # ExportHelper properties

    filename_ext = ".ldr"
    filter_glob = StringProperty(
        default="*.ldr",
        options={"HIDDEN"},
    )
    # path_mode = path_reference_mode
    check_extension = True
    model_author = StringProperty(
        name="Author",
        description="Author name for the file's metadata",
        default="",
    )
    build_order = EnumProperty(
        name="Build Order",
        description="Build order for the model steps",
        # options={"HIDDEN"},
        items=get_build_order_items,
    )

    ################################################
    # initialization method

    def __init__(self):
        # get matrix for rotation of brick
        self.matrices = [
            " 0 0 -1 0 1 0  1 0  0",
            " 1 0  0 0 1 0  0 0  1",
            " 0 0  1 0 1 0 -1 0  0",
            "-1 0  0 0 1 0  0 0 -1"
        ]
        # get other vars
        self.legal_bricks = get_legal_bricks()
        self.abs_mat_properties = bpy.props.abs_mat_properties if hasattr(bpy.props, "abs_mat_properties") else None
        # initialize vars
        scn, cm, _ = get_active_context_info()
        self.trans_weight = cm.transparent_weight
        self.material_type = cm.material_type
        self.custom_mat = cm.custom_mat
        self.random_mat_seed = cm.random_mat_seed
        self.brick_height = cm.brick_height
        self.offset_brick_layers = cm.offset_brick_layers
        self.gap = cm.gap
        self.zstep = get_zstep(cm)
        self.brick_materials_installed = brick_materials_installed()

    #############################################
    # class variables

    # NONE!

    #############################################
    # class methods

    @timed_call()
    def write_ldraw_file_conn_comps(self, context):
        """ create and write Ldraw file """
        pass

    def blend_to_ldraw_units(self, bricksdict, zstep, key, idx):
        """ convert location of brick from blender units to ldraw units """
        loc = Vector((1, 1, 1))
        return loc

    #############################################
