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
# NONE!

# Blender imports
import bpy
from bpy.types import Operator
from bpy.props import *

# Module imports
from ..delete_model import BRICKER_OT_delete_model
from ...functions import *
from ...lib.undo_stack import *


class OBJECT_OT_delete_override(Operator):
    """OK?"""
    bl_idname = "object.delete"
    bl_label = "Delete"
    bl_options = {"REGISTER"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        # return context.active_object is not None
        return True

    def execute(self, context):
        try:
            self.run_delete(context)
        except:
            bricker_handle_exception()
        return {"FINISHED"}

    def invoke(self, context, event):
        # Run confirmation popup for delete action
        # TODO: support 'self.confirm'
        return context.window_manager.invoke_confirm(self, event)

    ################################################
    # initialization method

    def __init__(self):
        self.undo_stack = UndoStack.get_instance()
        self.iterated_states_at_least_once = False
        self.objs_to_delete = bpy.context.selected_objects
        self.warn_initialize = False
        self.undo_pushed = False

    ###################################################
    # class variables

    use_global = BoolProperty(default=False)
    update_model = BoolProperty(default=True)
    undo = BoolProperty(default=True)
    confirm = BoolProperty(default=True)

    ################################################
    # class methods

    def run_delete(self, context):
        if bpy.props.bricker_initialized:
            for obj in self.objs_to_delete:
                if obj.is_brick:
                    self.undo_stack.undo_push("delete_override")
                    self.undo_pushed = True
                    break
        else:
            # initialize obj_names_dict (key:cm_id, val:list of brick objects)
            obj_names_dict = create_obj_names_dict(self.objs_to_delete)
            # remove brick type objects from selection
            for obj_names_list in obj_names_dict.values():
                if len(obj_names_list) > 0:
                    for obj_name in obj_names_list:
                        self.objs_to_delete.remove(bpy.data.objects.get(obj_name))
                    if not self.warn_initialize:
                        self.report({"WARNING"}, "Please initialize the Bricker [shift+i] before attempting to delete bricks")
                        self.warn_initialize = True
        # run delete_unprotected
        protected = self.delete_unprotected(context, self.use_global, self.update_model)
        # alert user of protected objects
        if len(protected) > 0:
            self.report({"WARNING"}, "Bricker is using the following object(s): " + str(protected)[1:-1])
        # push delete action to undo stack
        if self.undo:
            bpy.ops.ed.undo_push(message="Delete")
        tag_redraw_areas("VIEW_3D")

    def delete_unprotected(self, context, use_global=False, update_model=True):
        scn = context.scene
        protected = []
        obj_names_to_delete = [obj.name for obj in self.objs_to_delete]
        prefs = get_addon_preferences()

        # initialize obj_names_dict (key:cm_id, val:list of brick objects)
        obj_names_dict = create_obj_names_dict(self.objs_to_delete)

        # update matrix
        for i, cm_id in enumerate(obj_names_dict.keys()):
            cm = get_item_by_id(scn.cmlist, cm_id)
            if created_with_unsupported_version(cm):
                continue
            last_blender_state = cm.blender_undo_state
            # get bricksdict from cache
            bricksdict = get_bricksdict(cm)
            if not update_model:
                continue
            if bricksdict is None:
                self.report({"WARNING"}, "Adjacent bricks in model '" + cm.name + "' could not be updated (matrix not cached)")
                continue
            keys_to_update = []
            cm.customized = True
            # store cmlist props for quick calling
            last_split_model = cm.last_split_model
            zstep = cm.zstep

            for obj_name in obj_names_dict[cm_id]:
                # get dict key details of current obj
                dkey = get_dict_key(obj_name)
                x0, y0, z0 = get_dict_loc(bricksdict, dkey)
                # get size of current brick (e.g. [2, 4, 1])
                obj_size = bricksdict[dkey]["size"]

                # for all locations in bricksdict covered by current obj
                for x in range(x0, x0 + obj_size[0]):
                    for y in range(y0, y0 + obj_size[1]):
                        for z in range(z0, z0 + (obj_size[2] // zstep)):
                            cur_key = list_to_str((x, y, z))
                            # make adjustments to adjacent bricks
                            if prefs.auto_update_on_delete and last_split_model:
                                self.update_adj_bricksdicts(bricksdict, zstep, cur_key, [x, y, z], keys_to_update)
                            # reset bricksdict values
                            cur_brick_d = bricksdict[cur_key]
                            cur_brick_d["draw"] = False
                            cur_brick_d["val"] = 0
                            cur_brick_d["parent"] = None
                            cur_brick_d["created_from"] = None
                            cur_brick_d["flipped"] = False
                            cur_brick_d["rotated"] = False
                            cur_brick_d["top_exposed"] = False
                            cur_brick_d["bot_exposed"] = False
            # dirty_build if it wasn't already
            last_build_is_dirty = cm.build_is_dirty
            if not last_build_is_dirty:
                cm.build_is_dirty = True
            # merge and draw modified bricks
            if len(keys_to_update) > 0:
                # split up bricks before draw_updated_bricks calls attempt_merge
                keys_to_update = uniquify1(keys_to_update)
                for k0 in keys_to_update.copy():
                    keys_to_update += split_brick(bricksdict, k0, cm.zstep, cm.brick_type)
                keys_to_update = uniquify1(keys_to_update)
                # remove duplicate keys from the list and delete those objects
                for k2 in keys_to_update:
                    brick = bpy.data.objects.get(bricksdict[k2]["name"])
                    delete(brick)
                # create new bricks at all keys_to_update locations (attempts merge as well)
                draw_updated_bricks(cm, bricksdict, keys_to_update, select_created=False)
            if not last_build_is_dirty:
                cm.build_is_dirty = False
            # if undo states not iterated above
            if last_blender_state == cm.blender_undo_state:
                # iterate undo states
                self.undo_stack.iterate_states(cm)
            self.iterated_states_at_least_once = True

        # if nothing was done worth undoing but state was pushed
        if not self.iterated_states_at_least_once and self.undo_pushed:
            # pop pushed value from undo stack
            self.undo_stack.undo_pop_clean()

        # delete bricks
        for obj_name in obj_names_to_delete:
            obj = bpy.data.objects.get(obj_name)
            if obj is None:
                continue
            if obj.is_brickified_object or obj.is_brick:
                self.delete_brick_object(context, obj, update_model, use_global)
            elif not obj.protected:
                obj_users_scene = len(obj.users_scene)
                if use_global or obj_users_scene == 1:
                    bpy.data.objects.remove(obj, do_unlink=True)
            else:
                print(obj.name + ' is protected')
                protected.append(obj.name)

        tag_redraw_areas("VIEW_3D")

        return protected

    @staticmethod
    def update_adj_bricksdicts(bricksdict, zstep, cur_key, cur_loc, keys_to_update):
        x, y, z = cur_loc
        new_bricks = []
        brick_d = bricksdict[cur_key]
        adj_keys = get_adj_keys_and_brick_vals(bricksdict, key=cur_key)[0]
        # set adjacent bricks to shell if deleted brick was on shell
        for k0 in adj_keys:
            brick_d0 = bricksdict[k0]
            if brick_d0["val"] != 0:  # if adjacent brick not outside
                brick_d0["val"] = 1
                if not brick_d0["draw"]:
                    brick_d0["draw"] = True
                    brick_d0["size"] = [1, 1, zstep]
                    brick_d0["parent"] = "self"
                    brick_d0["type"] = brick_d["type"]
                    brick_d0["flipped"] = brick_d["flipped"]
                    brick_d0["rotated"] = brick_d["rotated"]
                    brick_d0["mat_name"] = brick_d["mat_name"]
                    brick_d0["near_face"] = brick_d["near_face"]
                    ni = brick_d["near_intersection"]
                    brick_d0["near_intersection"] = tuple(ni) if type(ni) in [list, tuple] else ni
                    # add key to list for drawing
                    keys_to_update.append(k0)
                    new_bricks.append(k0)
        # top of bricks below are now exposed
        k0 = list_to_str((x, y, z - 1))
        if k0 in bricksdict and bricksdict[k0]["draw"]:
            k1 = k0 if bricksdict[k0]["parent"] == "self" else bricksdict[k0]["parent"]
            if not bricksdict[k1]["top_exposed"]:
                bricksdict[k1]["top_exposed"] = True
                # add key to list for drawing
                keys_to_update.append(k1)
        # bottom of bricks above are now exposed
        k0 = list_to_str((x, y, z + 1))
        if k0 in bricksdict and bricksdict[k0]["draw"]:
            k1 = k0 if bricksdict[k0]["parent"] == "self" else bricksdict[k0]["parent"]
            if not bricksdict[k1]["bot_exposed"]:
                bricksdict[k1]["bot_exposed"] = True
                # add key to list for drawing
                keys_to_update.append(k1)
        return keys_to_update, new_bricks

    def delete_brick_object(self, context, obj, update_model=True, use_global=False):
        scn = context.scene
        cm = None
        for cm_cur in scn.cmlist:
            n = get_source_name(cm_cur)
            if not obj.name.startswith("Bricker_%(n)s_brick" % locals()):
                continue
            if obj.is_brickified_object:
                cm = cm_cur
                break
            elif obj.is_brick:
                cur_bricks = cm_cur.collection
                if cur_bricks is not None and len(cur_bricks.objects) < 2:
                    cm = cm_cur
                    break
        if cm and update_model:
            BRICKER_OT_delete_model.run_full_delete(cm=cm)
            deselect(context.active_object)
        else:
            obj_users_scene = len(obj.users_scene)
            if use_global or obj_users_scene == 1:
                bpy.data.objects.remove(obj, do_unlink=True)

    ################################################
