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
import sys
import math
import json
import marshal

# Blender imports
import bpy
from mathutils import Matrix, Vector, Euler
from bpy.props import *

# Addon imports
from .customize.undo_stack import *
from .bevel import BRICKER_OT_bevel
from .cache import *
from .brickify import BRICKER_OT_brickify
from ..lib.bricksdict import *
from ..functions import *


class BRICKER_OT_brickify_in_background(bpy.types.Operator):
    """ Create brick sculpture from source object mesh """
    bl_idname = "bricker.brickify_in_background"
    bl_label = "Create/Update Brick Model from Source Object"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    def execute(self, context):
        # get active context info
        scn, cm, n = get_active_context_info()
        # run brickify for current frame
        if "ANIM" in self.action:
            BRICKER_OT_brickify.brickify_current_frame(self.frame, self.action, in_background=True)
        else:
            BRICKER_OT_brickify.brickify_active_frame(self.action)
        # save last cache to prop temporarily
        bpy.props.bfm_cache_bytes_hex = marshal.dumps(bricker_bfm_cache[cm.id]).hex()
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        pass

    #############################################
    # class variables

    frame = IntProperty(default=-1)
    action = StringProperty(default="CREATE")

    #############################################


class BRICKER_OT_stop_brickifying_in_background(bpy.types.Operator):
    """ Stop the background brickification process """
    bl_idname = "bricker.stop_brickifying_in_background"
    bl_label = "Stop the background brickification process"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    def execute(self, context):
        cm = get_active_context_info()[1]
        cm.stop_background_process = True
        return {"FINISHED"}

    #############################################
