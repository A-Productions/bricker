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
import json

# Blender imports
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper#, path_reference_mode
from bpy.props import *

# Module imports
from ..functions import *


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
        try:
            pass
        except:
            bricker_handle_exception()
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

    #############################################
    # class variables

    # NONE!

    #############################################
    # class methods

    def write_ldraw_file(self):
        """ create and write Ldraw file """
        pass

    def blend_to_ldraw_units(self, cm, bricksdict, zstep, key, idx):
        """ convert location of brick from blender units to ldraw units """
        loc = Vector((1, 1, 1))
        return loc

    #############################################
