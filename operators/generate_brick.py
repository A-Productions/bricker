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

# system imports
import random
import time
import bmesh
import os
from os.path import dirname, abspath
import sys
import math
import shutil
import json
import marshal
import numpy as np

# Blender imports
import bpy
from mathutils import Matrix, Vector, Euler
from bpy.props import *

# Module imports
from .delete_model import BRICKER_OT_delete_model
from .bevel import BRICKER_OT_bevel
from .cache import *
from ..lib.undo_stack import *
from ..subtrees.background_processing.classes.job_manager import JobManager
from ..functions import *


class BRICKER_OT_generate_brick(bpy.types.Operator):
    """ Generate a single brick from model settings """
    bl_idname = "bricker.generate_brick"
    bl_label = "Generate Brick"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        if context.scene.cmlist_index == -1:
            return False
        scn, cm, n = get_active_context_info()
        if cm.brick_type == "CUSTOM":
            return False
        return True

    def execute(self, context):
        try:
            brick = generate_brick_object(self.brick_name, (self.brick_width, self.brick_depth, self.brick_height))
            safe_link(brick)
            return {"FINISHED"}
        except:
            bricker_handle_exception()
            return {"CANCELLED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_popup(self, event)

    ################################################
    # initialization method

    def __init__(self):
        pass

    ###################################################
    # class variables

    brick_name = StringProperty(
        name="Brick Name",
        description="Name of brick to be generated",
        default="New Brick",
    )
    brick_width = IntProperty(
        name="Width",
        description="",
        default=1,
    )
    brick_depth = IntProperty(
        name="Depth",
        description="",
        default=1,
    )
    brick_height = IntProperty(
        name="Height",
        description="",
        default=1,
    )

    #############################################
    # class methods

    # NONE!

    #############################################
