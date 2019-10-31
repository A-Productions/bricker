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
# NONE!

# Blender imports
import bpy
from bpy.app.handlers import persistent
from mathutils import Vector, Euler

# Module imports
from .common import *
from .general import *
from .bricksdict import *
from .brickify_utils import finish_animation
from .matlist_utils import create_mat_objs
from ..lib.caches import bricker_bfm_cache
from ..lib.undo_stack import UndoStack, python_undo_state


def bricker_running_blocking_op():
    wm = bpy.context.window_manager
    return hasattr(wm, "bricker_running_blocking_operation") and wm.bricker_running_blocking_operation


@persistent
def handle_animation(scn):
    if bricker_running_blocking_op():
        return
    for i, cm in enumerate(scn.cmlist):
        if not cm.animated:
            continue
        n = get_source_name(cm)
        for cf in range(cm.last_start_frame, cm.last_stop_frame + 1):
            cur_bricks = bpy_collections().get("Bricker_%(n)s_bricks_f_%(cf)s" % locals())
            if cur_bricks is None:
                continue
            adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame)
            on_cur_f = adjusted_frame_current == cf
            if b280():
                # hide bricks from view and render unless on current frame
                if cur_bricks.hide_render == on_cur_f:
                    cur_bricks.hide_render = not on_cur_f
                if cur_bricks.hide_viewport == on_cur_f:
                    cur_bricks.hide_viewport = not on_cur_f
                if hasattr(bpy.context, "active_object"):
                    obj = bpy.context.active_object
                    if obj and obj.name.startswith("Bricker_%(n)s_bricks" % locals()) and on_cur_f:
                        select(cur_bricks.objects, active=True)
            else:
                for brick in cur_bricks.objects:
                    # hide bricks from view and render unless on current frame
                    if on_cur_f:
                        unhide(brick)
                    else:
                        hide(brick)
                    if hasattr(bpy.context, "active_object") and bpy.context.active_object and bpy.context.active_object.name.startswith("Bricker_%(n)s_bricks" % locals()) and on_cur_f:
                        select(brick, active=True)
                    # prevent bricks from being selected on frame change
                    else:
                        deselect(brick)


@blender_version_wrapper("<=","2.79")
def is_obj_visible(scn, cm, n):
    obj_visible = False
    if cm.model_created or cm.animated:
        g = bpy_collections().get("Bricker_%(n)s_bricks" % locals())
        if g is not None and len(g.objects) > 0:
            obj = g.objects[0]
        else:
            obj = None
    else:
        obj = cm.source_obj
    if obj:
        obj_visible = False
        for i in range(20):
            if obj.layers[i] and scn.layers[i]:
                obj_visible = True
    return obj_visible, obj


def find_3dview_space():
    # Find 3D_View window and its scren space
    area = next((a for a in bpy.data.window_managers[0].windows[0].screen.areas if a.type == "VIEW_3D"), None)

    if area:
        space = area.spaces[0]
    else:
        space = bpy.context.space_data

    return space


# clear light cache before file load
@persistent
def clear_bfm_cache(dummy):
    for key in bricker_bfm_cache.keys():
        bricker_bfm_cache[key] = None


@persistent
def reset_properties(dummy):
    scn = bpy.context.scene
    # reset undo stack on load
    undo_stack = UndoStack.get_instance(reset=True)
    # if file was saved in the middle of a brickify process, reset necessary props
    for cm in scn.cmlist:
        if cm.brickifying_in_background and cm.source_obj is not None:
            cm.brickifying_in_background = False
            n = cm.source_obj.name
            for cf in range(cm.last_start_frame, cm.last_stop_frame):
                cur_bricks_coll = bpy_collections().get("Bricker_%(n)s_bricks_f_%(cf)s" % locals())
                if cur_bricks_coll is None:
                    cm.last_stop_frame = max(cm.last_start_frame, cf - 1)
                    # cm.stop_frame = max(cm.last_start_frame, cf - 1)
                    cm.stop_frame = cm.stop_frame  # run updater to allow 'update_model'
                    # hide obj unless on scene current frame
                    if scn.frame_current > cm.last_stop_frame and cf > cm.last_start_frame:
                        set_frame_visibility(cm.last_stop_frame)
                    break


@persistent
def handle_loading_to_light_cache(dummy):
    deep_to_light_cache(bricker_bfm_cache)
    # verify caches loaded properly
    for scn in bpy.data.scenes:
        for cm in scn.cmlist:
            if not (cm.model_created or cm.animated):
                continue
            # reset undo states
            cm.blender_undo_state = 0
            python_undo_state[cm.id] = 0
            # load bricksdict
            bricksdict = get_bricksdict(cm)
            if bricksdict is None:
                cm.matrix_lost = True
                cm.matrix_is_dirty = True


# push dicts from light cache to deep cache on save
@persistent
def handle_storing_to_deep_cache(dummy):
    light_to_deep_cache(bricker_bfm_cache)


# @persistent
# def undo_bricksdict_changes(scene):
#     scn = bpy.context.scene
#     if scn.cmlist_index == -1:
#         return
#     undo_stack = UndoStack.get_instance()
#     global python_undo_state
#     cm = scn.cmlist[scn.cmlist_index]
#     if cm.id not in python_undo_state:
#         python_undo_state[cm.id] = 0
#     # handle undo
#     if python_undo_state[cm.id] > cm.blender_undo_state:
#         self.undo_stack.undo_pop()
#
#
# bpy.app.handlers.undo_pre.append(undo_bricksdict_changes)
#
#
# @persistent
# def redo_bricksdict_changes(scene):
#     scn = bpy.context.scene
#     if scn.cmlist_index == -1:
#         return
#     undo_stack = UndoStack.get_instance()
#     global python_undo_state
#     cm = scn.cmlist[scn.cmlist_index]
#     if cm.id not in python_undo_state:
#         python_undo_state[cm.id] = 0
#     # handle redo
#     elif python_undo_state[cm.id] < cm.blender_undo_state:
#         self.undo_stack.redo_pop()
#
#
# bpy.app.handlers.redo_pre.append(redo_bricksdict_changes)


@persistent
def handle_upconversion(dummy):
    # remove storage scene
    sto_scn = bpy.data.scenes.get("Bricker_storage (DO NOT MODIFY)")
    if sto_scn is not None:
        for obj in sto_scn.objects:
            obj.use_fake_user = True
        bpy.data.scenes.remove(sto_scn)
    for scn in bpy.data.scenes:
        # update cmlist indices to reflect updates to Bricker
        for cm in scn.cmlist:
            if created_with_unsupported_version(cm):
                # normalize cm.version
                cm.version = cm.version.replace(", ", ".")
                # convert from v1_0 to v1_1
                if int(cm.version[2]) < 1:
                    cm.brickWidth = 2 if cm.maxBrickScale2 > 1 else 1
                    cm.brick_depth = cm.maxBrickScale2
                # convert from v1_2 to v1_3
                if int(cm.version[2]) < 3:
                    if cm.color_snap_amount == 0:
                        cm.color_snap_amount = 0.001
                    for obj in bpy.data.objects:
                        if obj.name.startswith("Rebrickr"):
                            obj.name = obj.name.replace("Rebrickr", "Bricker")
                    for scn in bpy.data.scenes:
                        if scn.name.startswith("Rebrickr"):
                            scn.name = scn.name.replace("Rebrickr", "Bricker")
                    for coll in bpy_collections():
                        if coll.name.startswith("Rebrickr"):
                            coll.name = coll.name.replace("Rebrickr", "Bricker")
                # convert from v1_3 to v1_4
                if int(cm.version[2]) < 4:
                    # update "_frame_" to "_f_" in brick and group names
                    n = cm.source_name
                    bricker_bricks_cn = "Bricker_%(n)s_bricks" % locals()
                    if cm.animated:
                        for i in range(cm.last_start_frame, cm.last_stop_frame + 1):
                            bricker_bricks_curf_cn = bricker_bricks_cn + "_frame_" + str(i)
                            bcoll = bpy_collections().get(bricker_bricks_curf_cn)
                            if bcoll is not None:
                                bcoll.name = rreplace(bcoll.name, "frame", "f")
                                for obj in bcoll.objects:
                                    obj.name = rreplace(obj.name, "combined_frame" if "combined_frame" in obj.name else "frame", "f")
                    elif cm.model_created:
                        bcoll = bpy_collections().get(bricker_bricks_cn)
                        if bcoll is not None:
                            for obj in bcoll.objects:
                                if obj.name.endswith("_combined"):
                                    obj.name = obj.name[:-9]
                    # remove old storage scene
                    sto_scn_old = bpy.data.scenes.get("Bricker_storage (DO NOT RENAME)")
                    if sto_scn_old is not None:
                        for obj in sto_scn_old.objects:
                            if obj.name.startswith("Bricker_refLogo"):
                                bpy.data.objects.remove(obj, do_unlink=True)
                            else:
                                obj.use_fake_user = True
                        bpy.data.scenes.remove(sto_scn_old)
                    # create "Bricker_cm.id_mats" object for each cmlist idx
                    create_mat_objs(cm)
                    # update names of Bricker source objects
                    old_source = bpy.data.objects.get(cm.source_name + " (DO NOT RENAME)")
                    if old_source is not None:
                        old_source.name = cm.source_name
                    # transfer dist offset values to new prop locations
                    if cm.distOffsetX != -1:
                        cm.dist_offset = (cm.distOffsetX, cm.distOffsetY, cm.distOffsetZ)
                # convert from v1_4 to v1_5
                if int(cm.version[2]) < 5:
                    if cm.logoDetail != "":
                        cm.logo_type = cm.logoDetail
                    cm.matrix_is_dirty = True
                    cm.matrix_lost = True
                    remove_colls = list()
                    for coll in bpy_collections():
                        if coll.name.startswith("Bricker_") and (coll.name.endswith("_parent") or coll.name.endswith("_dupes")):
                            remove_colls.append(coll)
                    for coll in remove_colls:
                        bpy_collections().remove(coll)
                # convert from v1_5 to v1_6
                if int(cm.version[2]) < 6:
                    for cm in scn.cmlist:
                        cm.zstep = get_zstep(cm)
                    if cm.source_obj is None: cm.source_obj = bpy.data.objects.get(cm.source_name)
                    if cm.parent_obj is None: cm.parent_obj = bpy.data.objects.get(cm.parent_name)
                    n = get_source_name(cm)
                    if cm.animated:
                        coll = finish_animation(cm)
                    else:
                        coll = bpy_collections().get("Bricker_%(n)s_bricks" % locals())
                    if cm.collection is None: cm.collection = coll
                    dup = bpy.data.objects.get(n + "_duplicate")
                    if dup is not None: dup.name = n + "__dup__"
                # convert from v1_6 to v1_7
                if int(cm.version[2]) < 7:
                    cm.mat_obj_abs = bpy.data.objects.get("Bricker_{}_RANDOM_mats".format(cm.id))
                    cm.mat_obj_random = bpy.data.objects.get("Bricker_{}_ABS_mats".format(cm.id))
                    # transfer props from 1_6 to 1_7 (camel to snake case)
                    for prop in get_annotations(cm):
                        if prop.islower():
                            continue
                        snake_prop = camel_to_snake_case(prop)
                        if hasattr(cm, snake_prop) and hasattr(cm, prop):
                            setattr(cm, snake_prop, getattr(cm, prop))

            # ensure parent object has no users
            if cm.parent_obj is not None:
                # TODO: replace with this line when the function is fixed in 2.8
                cm.parent_obj.user_clear()
                cm.parent_obj.use_fake_user = True
                # for coll in cm.parent_obj.users_collection:
                #     coll.objects.unlink(cm.parent_obj)
