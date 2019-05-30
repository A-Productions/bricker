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

# Addon imports
from ..functions import *
from ..ui.cmlist_actions import *
from ..ui.app_handlers import handle_animation


class BRICKER_OT_bake_model(bpy.types.Operator):
    """Convert model from Bricker model to standard Blender object (applies transformation and clears Bricker data associated with the model; source object will be lost)"""
    bl_idname = "bricker.bake_model"
    bl_label = "Bake Model"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        try:
            scn, cm, n = getActiveContextInfo()
        except IndexError:
            return False
        if (cm.modelCreated or cm.animated) and not cm.brickifyingInBackground:
            return True
        return False

    def execute(self, context):
        scn, cm, n = getActiveContextInfo()
        cur_f = getAnimAdjustedFrame(scn.frame_current, cm.lastStartFrame, cm.lastStopFrame)
        # set isBrick/isBrickifiedObject to False
        bricks = getBricks()
        # apply object transformation
        parent_clear(bricks)
        if cm.lastSplitModel:
            for brick in bricks:
                brick.isBrick = False
                brick.name = brick.name[8:]
        else:
            active_brick = bricks[0] if cm.modelCreated else bpy.data.objects.get("Bricker_%(n)s_bricks_f_%(cur_f)s" % locals())
            active_brick.isBrickifiedObject = False
            active_brick.name = "%(n)s_bricks" % locals()
        # delete parent/source/dup
        objsToDelete = [bpy.data.objects.get("Bricker_%(n)s_parent" % locals()), cm.source_obj]
        if cm.modelCreated:
            objsToDelete.append(bpy.data.objects.get("Bricker_%(n)s_parent" % locals()))
        else:
            for f in range(cm.lastStartFrame, cm.lastStopFrame + 1):
                objsToDelete.append(bpy.data.objects.get("Bricker_%(n)s_f_%(f)s" % locals()))
                objsToDelete.append(bpy.data.objects.get("Bricker_%(n)s_parent_f_%(f)s" % locals()))
                if f != cur_f:
                    objsToDelete.append(bricks.pop(0 if f < cur_f else 1))
        for obj in objsToDelete:
            bpy.data.objects.remove(obj, do_unlink=True)
        # delete brick collection
        brickColl = cm.collection
        if b280():
            linkedColls = [cn for cn in bpy.data.collections if brickColl.name in cn.children]
            for col in linkedColls:
                for brick in bricks:
                    col.objects.link(brick)
        if brickColl is not None:
            bpy_collections().remove(brickColl, do_unlink=True)
        # remove current cmlist index
        cm.modelCreated = False
        cm.animated = False
        CMLIST_OT_list_action.removeItem(self, scn.cmlist_index)
        scn.cmlist_index = -1
        return{"FINISHED"}
