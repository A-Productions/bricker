"""
Copyright (C) 2019 Bricks Brought to Life
http://bblanimation.com/
chris@bblanimation.com

Created by Christopher Gearhart

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# System imports
# NONE!

# Blender imports
import bpy
from bpy.app.handlers import persistent

# Addon imports
from .app_handlers import bricker_running_blocking_op
from ..buttons.customize.undo_stack import *
from ..functions import *
from ..buttons.customize.tools import *
from ..buttons.customize.undo_stack import *


# def is_bricker_obj_visible(scn, cm, n):
#     if cm.model_created or cm.animated:
#         gn = "Bricker_%(n)s_bricks" % locals()
#         if collExists(gn) and len(bpy.data.collections[gn].objects) > 0:
#             obj = bpy.data.collections[gn].objects[0]
#         else:
#             obj = None
#     else:
#         obj = cm.source_obj
#     obj_visible = is_obj_visible_in_viewport(obj)
#     return obj_visible, obj


@persistent
def handle_selections(junk=None):
    if bricker_running_blocking_op():
        return 0.5
    scn = bpy.context.scene
    obj = bpy.context.view_layer.objects.active if b280() else scn.objects.active
    # TODO: in b280, Check if active object (with active cmlist index) is no longer visible
    # curLayers = str(list(scn.layers))
    # # if scn.layers changes and active object is no longer visible, set scn.cmlist_index to -1
    # if scn.Bricker_last_layers != curLayers:
    #     scn.Bricker_last_layers = curLayers
    #     cur_objVisible = False
    #     if scn.cmlist_index != -1:
    #         cm0, n0 = get_active_context_info()[1:]
    #         cur_objVisible, _ = is_obj_visible(scn, cm0, n0)
    #     if not cur_objVisible or scn.cmlist_index == -1:
    #         setIndex = False
    #         for i, cm in enumerate(scn.cmlist):
    #             if i != scn.cmlist_index:
    #                 nextObjVisible, obj = is_obj_visible(scn, cm, get_source_name(cm))
    #                 if nextObjVisible and hasattr(bpy.context, "active_object") and bpy.context.active_object == obj:
    #                     scn.cmlist_index = i
    #                     setIndex = True
    #                     break
    #         if not setIndex:
    #             scn.cmlist_index = -1
    # if active object changes, open Brick Model settings for active object
    if obj and scn.bricker_last_active_object_name != obj.name and len(scn.cmlist) > 0 and (scn.cmlist_index == -1 or scn.cmlist[scn.cmlist_index].source_obj is not None) and obj.type == "MESH":
        scn.bricker_last_active_object_name = obj.name
        beginning_string = "Bricker_"
        if obj.name.startswith(beginning_string):
            using_source = False
            frame_loc = obj.name.rfind("_bricks")
            if frame_loc == -1:
                frame_loc = obj.name.rfind("_parent")
                if frame_loc == -1:
                    frame_loc = obj.name.rfind("__")
            if frame_loc != -1:
                scn.bricker_active_object_name = obj.name[len(beginning_string):frame_loc]
        else:
            using_source = True
            scn.bricker_active_object_name = obj.name
        for i,cm in enumerate(scn.cmlist):
            if created_with_unsupported_version(cm) or get_source_name(cm) != scn.bricker_active_object_name or (using_source and cm.model_created):
                continue
            if scn.cmlist_index != i:
                bpy.props.manual_cmlist_update = True
                scn.cmlist_index = i
            if obj.is_brick:
                # adjust scn.active_brick_detail based on active brick
                x0, y0, z0 = str_to_list(get_dict_key(obj.name))
                cm.active_key = (x0, y0, z0)
            tag_redraw_areas("VIEW_3D")
            return 0.05
        # if no matching cmlist item found, set cmlist_index to -1
        scn.cmlist_index = -1
        tag_redraw_areas("VIEW_3D")
    return 0.05


@blender_version_wrapper(">=","2.80")
def handle_undo_stack():
    scn = bpy.context.scene
    undo_stack = UndoStack.get_instance()
    if hasattr(bpy.props, "bricker_updating_undo_state") and not undo_stack.isUpdating() and not bricker_running_blocking_op() and scn.cmlist_index != -1:
        global python_undo_state
        cm = scn.cmlist[scn.cmlist_index]
        if cm.id not in python_undo_state:
            python_undo_state[cm.id] = 0
        # handle undo
        elif python_undo_state[cm.id] > cm.blender_undo_state:
            undo_stack.undo_pop()
            tag_redraw_areas("VIEW_3D")
        # handle redo
        elif python_undo_state[cm.id] < cm.blender_undo_state:
            undo_stack.redo_pop()
            tag_redraw_areas("VIEW_3D")
    return 0.02


@persistent
@blender_version_wrapper(">=","2.80")
def register_bricker_timers(scn):
    timer_fns = (handle_selections, handle_undo_stack)
    for timer_fn in timer_fns:
        if not bpy.app.timers.is_registered(timer_fn):
            bpy.app.timers.register(timer_fn)
