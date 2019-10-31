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
        if cm.model_created or (cm.animated and not cm.anim_only):
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


class CMLIST_OT_export_settings(bpy.types.Operator):
    """ export Bricker settings for linking animation in separate file """
    bl_idname = "cmlist.export_settings"
    bl_label = "Export Model Settings"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        return bpy.data.filepath

    def execute(self, context):
        cm = get_active_context_info()[1]
        bricker_addon_path = get_addon_directory()
        _, cmlist_props, cmlist_pointer_props, data_blocks_to_send = get_args_for_background_processor(cm, bricker_addon_path)
        filepath, filename = os.path.split(bpy.data.filepath)
        base_filename = filename[:filename.rfind(".")]
        # write cmlist_props to text file
        cmlist_props_filepath = os.path.join(filepath, base_filename + ".txt")
        f = open(cmlist_props_filepath, "w")
        f.write(compress_str(json.dumps(cmlist_props)) + "\n")
        f.write(compress_str(json.dumps(cmlist_pointer_props)) + "\n")
        f.close()
        # # write cmlist_pointer_props to library file
        # cmlist_pointer_props_filepath = os.path.join(filepath, base_filename + ".blend")
        # bpy.data.libraries.write(filepath=cmlist_props_filepath, datablocks=cmlist_pointer_props)
        # # zip everything up
        # with ZipFile(base_filename + ".zip", "w") as zip:
        #     # writing each file one by one
        #     for file in (cmlist_props_filepath, cmlist_pointer_props_filepath):
        #         zip.write(file)

        return{"FINISHED"}

    ################################################


class CMLIST_OT_load_settings(bpy.types.Operator):
    """ load Bricker settings from separate file for linking animations """
    bl_idname = "cmlist.load_settings"
    bl_label = "Load Model Settings"
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
        # with ZipFile(self.filepath, "r") as zip:
        #     zip.extractall()
        # filepath, filename = os.path.split(self.filepath)
        # base_filename = filename[:filename.rfind(".")]
        # # load cmlist_props
        # cmlist_props_path = os.path.join(filepath, filename + ".txt")
        # read data
        cmlist_props_path = self.filepath
        f = open(cmlist_props_path, "r")
        cmlist_props = json.loads(decompress_str(f.readline()[:-1]))
        cmlist_pointer_props = json.loads(decompress_str(f.readline()[:-1]))
        # apply cmlist_props to current model
        bpy.ops.cmlist.list_action(action="ADD")
        scn = bpy.context.scene
        scn.cmlist_index = len(scn.cmlist) - 1
        cm = scn.cmlist[scn.cmlist_index]
        for key in cmlist_props:
            setattr(cm, key, cmlist_props[key])
        # cm.loaded_from_filepath = self.filepath
        # apply relevant cmlist_pointer_props to current model
        source_name = cmlist_pointer_props["source_obj"]["name"]
        source_obj = bpy.data.objects.get(source_name)
        if source_obj is None:
            source_obj = bpy.data.objects.new(source_name, None)
            setattr(cm, "source_obj", source_obj)
        # close file
        f.close()

        # os.remove()
        # # load cmlist_pointer_props
        # cmlist_pointer_props_path = os.path.join(filepath, filename + ".blend")
        # bpy.data.libraries.load(filepath=cmlist_pointer_props_path, link=True)

        return{"FINISHED"}


    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    ###################################################
    # class variables

    filepath = StringProperty(subtype="FILE_PATH")

    ################################################


class CMLIST_OT_animate_linked_model(bpy.types.Operator):
    """ animate linked collection from external file """
    bl_idname = "cmlist.animate_linked_model"
    bl_label = "Animate Linked Frames"
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
        # create new collection
        self.collection = bpy.data.collections.new("Bricker_" + self.model_name + "_bricks")
        # get start and stop frames
        start_frame = 1048574  # max frame number for blender timeline
        stop_frame = -1
        parents = None
        for obj in bpy.data.objects:
            # if obj.instance_type == "COLLECTION" and obj.name.startswith("Bricker_" + self.model_name + "_bricks_f_"):
            if obj.name.startswith("Bricker_" + self.model_name + "_bricks_f_"):
                cur_f = int(obj.name[obj.name.rfind("_") + 1:])
                start_frame = min(cur_f, start_frame)
                stop_frame = max(cur_f, stop_frame)
                if parents is None:
                    parents = obj.users_collection
                unlink_object(obj, all=True)
                self.collection.objects.link(obj)
        update_depsgraph()
        for obj in list(self.collection.objects):
            if obj.instance_type != "COLLECTION":
                self.collection.objects.unlink(obj)
        if parents is None:
            bpy.data.collections.remove(self.collection)
            self.report({"WARNING"}, "Existing frames for '" + self.model_name + "' could not be found (e.g. 'Bricker_" + self.model_name + "_bricks_f_1')")
            return {"CANCELLED"}
        else:
            for p in parents:
                p.children.link(self.collection)
        # create new cmlist item
        bpy.ops.cmlist.list_action(action="ADD")
        scn = bpy.context.scene
        scn.cmlist_index = len(scn.cmlist) - 1
        cm = scn.cmlist[scn.cmlist_index]
        # set properties for new cmlist item
        cm.name = self.model_name
        cm.animated = True
        cm.anim_only = True
        cm.collection = self.collection
        cm.source_obj = bpy.data.objects.new(self.model_name, None)
        cm.last_start_frame = start_frame
        cm.last_stop_frame = stop_frame
        return{"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    ###################################################
    # class variables

    model_name = StringProperty(
        name="Model Name",
        description="Name of the source object of the brick model to animate linked frames for (e.g. 'Cube' if anim frame collection name is 'Bricker_Cube_bricks_f_1')",
    )

    ################################################
