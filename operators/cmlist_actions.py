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
import os
import json
from zipfile import ZipFile

# Blender imports
import bpy
from bpy.props import *
from bpy.types import Operator

# Module imports
from ..functions import *


# ui list item actions
class CMLIST_OT_list_action(Operator):
    bl_idname = "cmlist.list_action"
    bl_label = "Brick Model List Action"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    # @classmethod
    # def poll(self, context):
    #     scn = context.scene
    #     for cm in scn.cmlist:
    #         if cm.animated:
    #             return False
    #     return True

    def execute(self, context):
        try:
            scn = context.scene
            idx = scn.cmlist_index

            try:
                item = scn.cmlist[idx]
            except IndexError:
                pass

            if self.action == "REMOVE" and len(scn.cmlist) > 0 and idx >= 0:
                self.remove_item(idx)

            elif self.action == "ADD":
                self.add_item()

            elif self.action == "DOWN" and idx < len(scn.cmlist) - 1:
                self.move_down(item)

            elif self.action == "UP" and idx >= 1:
                self.move_up(item)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    ###################################################
    # class variables

    action = EnumProperty(
        items=(
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
            ("REMOVE", "Remove", ""),
            ("ADD", "Add", ""),
        )
    )

    #############################################
    # class methods

    @staticmethod
    def add_item():
        scn = bpy.context.scene
        active_object = bpy.context.active_object
        if active_object:
            # if active object isn't on visible layer, don't set it as default source for new model
            if not is_obj_visible_in_viewport(active_object):
                active_object = None
            # if active object is already the source for another model, don't set it as default source for new model
            elif any([cm.source_obj is active_object for cm in scn.cmlist]):
                active_object = None
        item = scn.cmlist.add()
        # initialize source object and name for item
        if active_object and active_object.type == "MESH" and not active_object.name.startswith("Bricker_"):
            item.source_obj = active_object
            item.name = active_object.name
        else:
            item.source_obj = None
            item.name = "<New Model>"
        # switch to new cmlist item
        scn.cmlist_index = len(scn.cmlist) - 1
        # set brick height based on Bricker preferences
        prefs = get_addon_preferences()
        if prefs.brick_height_default == "ABSOLUTE":
            # set absolute brick height
            item.brick_height = prefs.absolute_brick_height
        else:
            # set brick height based on model height
            source = item.source_obj
            if source:
                source_details = bounds(source, use_adaptive_domain=False)
                h = max(source_details.dist)
                item.brick_height = h / prefs.relative_brick_height
        # set other item properties
        item.id = max([cm.id for cm in scn.cmlist]) + 1
        item.idx = scn.cmlist_index
        item.version = bpy.props.bricker_version
        item.start_frame = scn.frame_start
        item.stop_frame = scn.frame_end
        # create new mat_obj for current cmlist id
        create_mat_objs(item)

    def remove_item(self, idx):
        scn, cm, sn = get_active_context_info()
        n = cm.name
        if cm.linked_from_external:
            bpy.data.collections.remove(cm.collection)
        if cm.model_created or (cm.animated and not cm.linked_from_external):
            self.report({"WARNING"}, "Please delete the Brickified model before attempting to remove this item." % locals())
            return
        for idx0 in range(idx + 1, len(scn.cmlist)):
            scn.cmlist[idx0].idx -= 1
        if len(scn.cmlist) - 1 == scn.cmlist_index:
            scn.cmlist_index -= 1
        # remove mat_obj for current cmlist id
        remove_mat_objs(cm.id)
        scn.cmlist.remove(idx)
        if scn.cmlist_index == -1 and len(scn.cmlist) > 0:
            scn.cmlist_index = 0
        else:
            # run update function of the property
            scn.cmlist_index = scn.cmlist_index

    def move_down(self, item):
        scn = bpy.context.scene
        scn.cmlist.move(scn.cmlist_index, scn.cmlist_index+1)
        scn.cmlist_index += 1
        self.update_idxs(scn.cmlist)

    def move_up(self, item):
        scn = bpy.context.scene
        scn.cmlist.move(scn.cmlist_index, scn.cmlist_index-1)
        scn.cmlist_index -= 1
        self.update_idxs(scn.cmlist)

    def update_idxs(self, cmlist):
        for i,cm in enumerate(cmlist):
            cm.idx = i

    #############################################


# copy settings from current index to all other indices
class CMLIST_OT_copy_settings_to_others(Operator):
    bl_idname = "cmlist.copy_settings_to_others"
    bl_label = "Copy Settings to Other Brick Models"
    bl_description = "Copies the settings from the current model to all other Brick Models"
    bl_options = {"UNDO"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        if len(scn.cmlist) == 1:
            return False
        return True

    def execute(self, context):
        try:
            scn, cm0, _ = get_active_context_info()
            for cm1 in scn.cmlist:
                if cm0 != cm1:
                    match_properties(cm1, cm0, override_idx=cm1.idx)
        except:
            bricker_handle_exception()
        return{"FINISHED"}


# copy settings from current index to memory
class CMLIST_OT_copy_settings(Operator):
    bl_idname = "cmlist.copy_settings"
    bl_label = "Copy Settings from Current Brick Model"
    bl_description = "Stores the ID of the current model for pasting"

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        return True

    def execute(self, context):
        try:
            scn, cm, _ = get_active_context_info()
            scn.bricker_copy_from_id = cm.id
        except:
            bricker_handle_exception()
        return{"FINISHED"}


# paste settings from index in memory to current index
class CMLIST_OT_paste_settings(Operator):
    bl_idname = "cmlist.paste_settings"
    bl_label = "Paste Settings to Current Brick Model"
    bl_description = "Pastes the settings from stored model ID to the current index"
    bl_options = {"UNDO"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        return True

    def execute(self, context):
        try:
            scn, cm0, _ = get_active_context_info()
            for cm1 in scn.cmlist:
                if cm0 != cm1 and cm1.id == scn.bricker_copy_from_id:
                    match_properties(cm0, cm1)
                    break
        except:
            bricker_handle_exception()
        return{"FINISHED"}


# select bricks from current model
class CMLIST_OT_select_bricks(Operator):
    bl_idname = "cmlist.select_bricks"
    bl_label = "Select All Bricks in Current Brick Model"
    bl_description = "Select all bricks in the current model"

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        return cm.animated or cm.model_created

    deselect = BoolProperty(default=False)

    def execute(self, context):
        try:
            if self.deselect:
                deselect(self.bricks)
            else:
                select(self.bricks)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    def __init__(self):
        self.bricks = get_bricks()


class CMLIST_OT_link_animated_model(bpy.types.Operator):
    """ link animated Bricker model from external file (preserves animation data) """
    bl_idname = "cmlist.link_animated_model"
    bl_label = "Link Animated Model"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        # scn = bpy.context.scene
        # if scn.cmlist_index == -1:
        #     return False
        return True

    def execute(self, context):
        scn = bpy.context.scene
        if not (self.filename.startswith("Bricker_") and self.filename.endswith("_bricks")):
            self.report({"ERROR"}, "Collection was not Bricker model. Bricker model collection names are formatted like this: 'Bricker_{source object name}_bricks'")
            return {"CANCELLED"}
        data_attr = os.path.basename(os.path.normpath(self.directory))
        if data_attr != "Collection":
            self.report({"ERROR"}, "Selected file must be collection data block")
            return {"CANCELLED"}
        # load brick model collection
        blendfile_path = self.directory[:self.directory.rfind(".blend") + 6]
        # data_attr = os.path.basename(os.path.normpath(self.directory)).lower() + "s"
        collection = load_from_library(blendfile_path, "collections", filenames=[self.filename], overwrite_data=False, action="LINK")[0]
        # check if a similarly named model already exists
        model_name = collection.name[collection.name.find("_") + 1:collection.name.rfind("_")]
        source_names = [cm0.source_obj.name for cm0 in scn.cmlist if cm0.source_obj is not None]
        if model_name in source_names:
            existing_model_index = source_names.index(model_name)
            cm1 = scn.cmlist[existing_model_index]
            # if a similarly named model exists and both are animated, add the new frames to the existing model
            if cm1.animated and len(collection.children) > 0:
                cm = cm1
                new_frame = False
                # try:
                #     children = sorted(list(collection.children), key=lambda cn: int(cn.name[cn.name.rfind("_") + 1:]))
                # except ValueError:
                #     children = list(collection.children)
                children = list(collection.children)
                for subcoll in children:
                    if subcoll.name in [cn.name for cn in cm.collection.children]:
                        bpy.data.collections.remove(subcoll)
                        continue
                    cm.collection.children.link(subcoll)
                    new_frame = True
                if new_frame:
                    collection = cm.collection
                    scn.cmlist_index = cm.idx
                    self.report({"INFO"}, "Linked new frames to existing Brick model")
                else:
                    self.report({"WARNING"}, "Local Bricker animation contains all frames from external animation")
                    return {"CANCELLED"}
            else:
                self.report({"ERROR"}, "Bricker model with the same name exists in current scene")
                return {"CANCELLED"}
        else:
            # link new collection to scene
            parent_coll = bpy.context.collection or scn.collection
            parent_coll.children.link(collection)
            # create new cmlist item
            bpy.ops.cmlist.list_action(action="ADD")
            scn.cmlist_index = len(scn.cmlist) - 1
            cm = scn.cmlist[scn.cmlist_index]
            cm.name = model_name
            cm.collection = collection
            cm.collection.make_local()
            cm.source_obj = bpy.data.objects.new(cm.name, None)
            cm.linked_from_external = True
        # set specific properties for anim/model
        if len(collection.children) > 0:
            cm.animated = True
            # get start and stop frames
            start_frame = 1048574  # max frame number for blender timeline
            stop_frame = -1
            for subcoll in collection.children:
                cur_f = subcoll.name[subcoll.name.rfind("_") + 1:]
                try:
                    cur_f = int(cur_f)
                except ValueError:
                    continue
                start_frame = min(cur_f, start_frame)
                stop_frame = max(cur_f, stop_frame)
            # set properties for new cmlist item
            cm.last_start_frame = start_frame if cm.last_start_frame == -1 else min(start_frame, cm.last_start_frame)
            cm.last_stop_frame = max(stop_frame, cm.last_stop_frame)
        else:
            cm.model_created = True

        return{"FINISHED"}


    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    ###################################################
    # class variables

    filter_folder = bpy.props.BoolProperty(default=True, options={"HIDDEN"})
    filter_blender = bpy.props.BoolProperty(default=True, options={"HIDDEN"})
    filter_blenlib  = bpy.props.BoolProperty(default=True, options={"HIDDEN"})
    filemode = bpy.props.IntProperty(default=1, options={"HIDDEN"})
    directory = StringProperty(subtype="DIR_PATH")
    filename = StringProperty(subtype="FILE_NAME")

    ################################################


class CMLIST_OT_link_frames(bpy.types.Operator):
    """ link frames for active Bricker model from external file (preserves animation data) """
    bl_idname = "cmlist.link_frames"
    bl_label = "Link Frames"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        return True

    def execute(self, context):
        scn, cm, n = get_active_context_info()
        filenames = [file.name for file in self.files]
        for fn in filenames:
            if not (fn.startswith("Bricker_") and "_bricks_f_" in fn):
                self.report({"ERROR"}, "Collection was not Bricker model frame. Bricker model frame collection names are formatted like this: 'Bricker_{source object name}_bricks_f_{frame number}'")
                return {"CANCELLED"}
        data_attr = os.path.basename(os.path.normpath(self.directory))
        if data_attr != "Collection":
            self.report({"ERROR"}, "Selected file must be collection data block")
            return {"CANCELLED"}
        # load brick model collection
        blendfile_path = self.directory[:self.directory.rfind(".blend") + 6]
        # data_attr = os.path.basename(os.path.normpath(self.directory)).lower() + "s"
        collections = load_from_library(blendfile_path, "collections", filenames=filenames, overwrite_data=False, action="LINK")
        # ensure a similarly named model already exists
        model_name = collections[0].name[collections[0].name.find("_") + 1:collections[0].name.rfind("_bricks")]
        if model_name != cm.source_obj.name:
            self.report({"ERROR"}, "Bricker animation frame source name does not match that of the active Bricker animation")
            return {"CANCELLED"}

        new_frame = False
        for subcoll in collections:
            if subcoll.name in [cn.name for cn in cm.collection.children]:
                continue
            cm.collection.children.link(subcoll)
            new_frame = True
        if not new_frame:
            self.report({"WARNING"}, "Local Bricker animation contains all frames from external animation")
            return {"CANCELLED"}
        # set properties for anim
        collection = cm.collection
        scn.cmlist_index = cm.idx
        self.report({"INFO"}, "Linked new frames to existing Brick model")
        cm.linked_from_external = True
        cm.animated = True
        # get start and stop frames
        start_frame = 1048574  # max frame number for blender timeline
        stop_frame = -1
        for subcoll in collection.children:
            cur_f = subcoll.name[subcoll.name.rfind("_") + 1:]
            try:
                cur_f = int(cur_f)
            except ValueError:
                continue
            start_frame = min(cur_f, start_frame)
            stop_frame = max(cur_f, stop_frame)
        # set properties for new cmlist item
        cm.last_start_frame = start_frame if cm.last_start_frame == -1 else min(start_frame, cm.last_start_frame)
        cm.last_stop_frame = max(stop_frame, cm.last_stop_frame)

        return{"FINISHED"}


    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    ###################################################
    # class variables

    filter_folder = BoolProperty(default=True, options={"HIDDEN"})
    filter_blender = BoolProperty(default=True, options={"HIDDEN"})
    filter_blenlib  = BoolProperty(default=True, options={"HIDDEN"})
    filemode = IntProperty(default=1, options={"HIDDEN"})
    directory = StringProperty(subtype="DIR_PATH")
    files = CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    ################################################
