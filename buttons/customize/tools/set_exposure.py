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
import marshal

# Blender imports
import bpy
from bpy.types import Operator

# Addon imports
from ..undo_stack import *
from ..functions import *
from ...brickify import *
from ...brickify import *
from ....lib.bricksdict.functions import get_dict_key
from ....functions import *


class BRICKER_OT_set_exposure(Operator):
    """Set exposure of bricks to correct insideness calculation (consider setting ‘Advanced > Insideness Ray Cast Direction’ to ‘XYZ’ instead)"""
    bl_idname = "bricker.set_exposure"
    bl_label = "Set Exposure"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns False) """
        scn = bpy.context.scene
        objs = bpy.context.selected_objects
        # check that at least 1 selected object is a brick
        for obj in objs:
            if not obj.is_brick:
                continue
            # get cmlist item referred to by object
            cm = get_item_by_id(scn.cmlist, obj.cmlist_id)
            if cm.last_brick_type != "CUSTOM":
                return True
        return False

    def execute(self, context):
        try:
            scn = bpy.context.scene
            selected_objects = bpy.context.selected_objects
            active_obj = bpy.context.active_object
            initial_active_obj_name = active_obj.name if active_obj else ""
            objs_to_select = []

            # iterate through cm_ids of selected objects
            for cm_id in self.obj_names_dict.keys():
                cm = get_item_by_id(scn.cmlist, cm_id)
                self.undo_stack.iterate_states(cm)
                bricksdict = marshal.loads(self.cached_bfm[cm_id])
                keys_to_update = []
                cm.customized = True
                zstep = cm.zstep

                # iterate through names of selected objects
                for obj_name in self.obj_names_dict[cm_id]:
                    # get dict key details of current obj
                    dkey = get_dict_key(obj_name)
                    # get size of current brick (e.g. [2, 4, 1])
                    obj_size = bricksdict[dkey]["size"]

                    keys_in_brick = get_keys_in_brick(bricksdict, obj_size, zstep, key=dkey)
                    for key in keys_in_brick:
                        # set top as exposed
                        if self.side in ("TOP", "BOTH"):
                            bricksdict[key]["top_exposed"] = not bricksdict[key]["top_exposed"]
                        # set bottom as exposed
                        if self.side in ("BOTTOM", "BOTH"):
                            bricksdict[key]["bot_exposed"] = not bricksdict[key]["bot_exposed"]
                    # add cur_key to keys_to_update
                    keys_to_update.append(dkey)

                # draw modified bricks
                draw_updated_bricks(cm, bricksdict, keys_to_update)
                # add selected objects to objects to select at the end
                objs_to_select += bpy.context.selected_objects
            # select the new objects created
            select(objs_to_select)
            orig_obj = bpy.data.objects.get(initial_active_obj_name)
            set_active_obj(orig_obj)
        except:
            bricker_handle_exception()
        return {"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        scn = bpy.context.scene
        # initialize bricksdicts
        selected_objects = bpy.context.selected_objects
        self.obj_names_dict = create_obj_names_dict(selected_objects)
        self.bricksdicts = get_bricksdicts_from_objs(self.obj_names_dict.keys())
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.cached_bfm = self.undo_stack.undo_push("exposure", affected_ids=list(self.obj_names_dict.keys()))

    ###################################################
    # class variables

    # variables
    bricksdicts = {}
    obj_names_dict = {}

    # properties
    side = bpy.props.EnumProperty(
        items=(("TOP", "Top", ""),
               ("BOTTOM", "Bottom", ""),
               ("BOTH", "Both", ""),),
        default="TOP")

    #############################################
