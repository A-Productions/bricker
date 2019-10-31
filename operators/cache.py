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

# Blender imports
import bpy
props = bpy.props

# Module imports
from ..lib.caches import *
from ..lib.undo_stack import *
from ..functions import *


class BRICKER_OT_clear_cache(bpy.types.Operator):
    """Clear brick mesh and matrix cache (Model customizations will be lost)"""
    bl_idname = "bricker.clear_cache"
    bl_label = "Clear Cache"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        if not bpy.props.bricker_initialized:
            return False
        return True

    def execute(self, context):
        try:
            scn, cm, n = get_active_context_info()
            self.undo_stack.iterate_states(cm)
            cm.matrix_is_dirty = True
            self.clear_caches()
            # clear all duplicated sources for brickified animations
            if cm.animated:
                dup_name_base = "Bricker_%(n)s_f_" % locals()
                dupes = [bpy.data.objects.get(dup_name_base + str(cf)) for cf in range(cm.last_start_frame, cm.last_stop_frame + 1)]
                delete(dupes)
        except:
            bricker_handle_exception()

        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push('clear_cache')

    #############################################
    # class methods

    @staticmethod
    def clear_cache(cm, brick_mesh=True, light_matrix=True, deep_matrix=True, images=True, dupes=True):
        """clear caches for cmlist item"""
        # clear light brick mesh cache
        if brick_mesh:
            bricker_mesh_cache[cm.id] = None
        # clear light matrix cache
        if light_matrix:
            bricker_bfm_cache[cm.id] = None
        # clear deep matrix cache
        if deep_matrix:
            cm.bfm_cache = ""
        # clear image cache
        if images:
            bricker_pixel_cache = dict()
        # remove caches of source model from data
        if dupes:
            if cm.model_created:
                delete(bpy.data.objects.get("Bricker_%(n)s__dup__"), remove_meshes=True)
            elif cm.animated:
                for cf in range(cm.last_start_frame, cm.last_stop_frame):
                    delete(bpy.data.objects.get("Bricker_%(n)s_f_%(cf)s"), remove_meshes=True)

    @staticmethod
    def clear_caches(brick_mesh=True, light_matrix=True, deep_matrix=True, images=True, dupes=True):
        """clear all caches in cmlist"""
        scn = bpy.context.scene
        for cm in scn.cmlist:
            BRICKER_OT_clear_cache.clear_cache(cm, brick_mesh=brick_mesh, light_matrix=light_matrix, deep_matrix=deep_matrix, images=images, dupes=dupes)
