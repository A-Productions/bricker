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
from operator import itemgetter

# Blender imports
import bpy
from bpy.props import *
from bpy.types import Panel, UIList
props = bpy.props

# Addon imports
from ..functions import *
from ..buttons.bevel import *
from ..subtrees.background_processing.classes.job_manager import JobManager


def uniquify_name(self, context):
    """ if Brick Model exists with name, add '.###' to the end """
    scn, cm, _ = get_active_context_info()
    name = cm.name
    while scn.cmlist.keys().count(name) > 1:
        if name[-4] == ".":
            try:
                num = int(name[-3:])+1
            except ValueError:
                num = 1
            name = name[:-3] + "%03d" % (num)
        else:
            name = name + ".001"
    if cm.name != name:
        cm.name = name


def set_default_obj_if_empty(self, context):
    scn = context.scene
    last_cmlist_index = scn.cmlist_index
    cm0 = scn.cmlist[last_cmlist_index]
    # verify model doesn't exist with that name
    if cm0.source_obj is not None:
        for i, cm1 in enumerate(scn.cmlist):
            if cm1 != cm0 and cm1.source_obj is cm0.source_obj:
                cm0.source_obj = None
                scn.cmlist_index = i


def update_bevel(self, context):
    # get bricks to bevel
    try:
        scn, cm, n = get_active_context_info()
        if cm.last_bevel_width != cm.bevel_width or cm.last_bevel_segments != cm.bevel_segments or cm.last_bevel_profile != cm.bevel_profile:
            bricks = get_bricks()
            BRICKER_OT_bevel.create_bevel_mods(cm, bricks)
            cm.last_bevel_width = cm.bevel_width
            cm.last_bevel_segments = cm.bevel_segments
            cm.last_bevel_profile = cm.bevel_profile
    except Exception as e:
        raise Exception("[Bricker] ERROR in update_bevel():", e)
        pass


def update_parent_exposure(self, context):
    scn, cm, _ = get_active_context_info()
    if not (cm.model_created or cm.animated):
        return
    parent_ob = cm.parent_obj
    if parent_ob:
        if cm.expose_parent:
            safe_link(parent_ob, protect=True)
            select(parent_ob, active=True, only=True)
        else:
            try:
                safe_unlink(parent_ob)
            except RuntimeError:
                pass


def update_model_scale(self, context):
    scn, cm, _ = get_active_context_info()
    if not (cm.model_created or cm.animated):
        return
    _, _, s = get_transform_data(cm)
    parent_ob = cm.parent_obj
    if parent_ob:
        parent_ob.scale = Vector(s) * cm.transform_scale


def update_circle_verts(self, context):
    scn, cm, _ = get_active_context_info()
    if (cm.circle_verts - 2) % 4 == 0:
        cm.circle_verts += 1
    cm.bricks_are_dirty = True


def update_job_manager_properties(self, context):
    scn, cm, _ = get_active_context_info()
    job_manager = JobManager.get_instance(cm.id)
    job_manager.timeout = cm.back_proc_timeout
    job_manager.max_workers = cm.max_workers


def update_brick_shell(self, context):
    scn, cm, _ = get_active_context_info()
    if cm.brick_shell == "CONSISTENT":
        cm.verify_exposure = True
    cm.matrix_is_dirty = True


def dirty_anim(self, context):
    scn, cm, _ = get_active_context_info()
    cm.anim_is_dirty = True


def dirty_material(self, context):
    scn, cm, _ = get_active_context_info()
    cm.material_is_dirty = True


def dirty_model(self, context):
    scn, cm, _ = get_active_context_info()
    cm.model_is_dirty = True


# NOTE: Any prop that calls this function should be added to get_matrix_settings()
def dirty_matrix(self=None, context=None):
    scn, cm, _ = get_active_context_info()
    cm.matrix_is_dirty = True


def dirty_internal(self, context):
    scn, cm, _ = get_active_context_info()
    cm.internal_is_dirty = True
    cm.build_is_dirty = True


def dirty_build(self, context):
    scn, cm, _ = get_active_context_info()
    cm.build_is_dirty = True


def dirty_bricks(self, context):
    scn, cm, _ = get_active_context_info()
    cm.bricks_are_dirty = True


def update_brick_type(self, context):
    scn, cm, _ = get_active_context_info()
    cm.zstep = get_zstep(cm)
    cm.matrix_is_dirty = True


def update_bevel_render(self, context):
    scn, cm, _ = get_active_context_info()
    show_render = cm.bevel_show_render
    for brick in get_bricks():
        bevel = brick.modifiers.get(brick.name + "_bvl")
        if bevel: bevel.show_render = show_render


def update_bevel_viewport(self, context):
    scn, cm, _ = get_active_context_info()
    show_viewport = cm.bevel_show_viewport
    for brick in get_bricks():
        bevel = brick.modifiers.get(brick.name + "_bvl")
        if bevel: bevel.show_viewport = show_viewport


def update_bevel_edit_mode(self, context):
    scn, cm, _ = get_active_context_info()
    show_in_editmode = cm.bevel_show_edit_mode
    for brick in get_bricks():
        bevel = brick.modifiers.get(brick.name + "_bvl")
        if bevel: bevel.show_in_editmode = show_in_editmode


def get_cm_props():
    """ returns list of important cmlist properties """
    return ["shell_thickness",
            "brick_height",
            "stud_detail",
            "logo_type",
            "logo_resolution",
            "logo_decimate",
            "logo_object",
            "logo_scale",
            "logo_inset",
            "hidden_underside_detail",
            "exposed_underside_detail",
            "circle_verts",
            "gap",
            "merge_seed",
            "connect_thresh",
            "random_loc",
            "random_rot",
            "brick_type",
            "align_bricks",
            "offset_brick_layers",
            "dist_offset",
            "custom_object1",
            "custom_object2",
            "custom_object3",
            "max_width",
            "max_depth",
            "merge_type",
            "legal_bricks_only",
            "split_model",
            "internal_supports",
            "mat_shell_depth",
            "lattice_step",
            "alternate_xy",
            "col_thickness",
            "color_snap",
            "color_snap_amount",
            "transparent_weight",
            "col_step",
            "smoke_density",
            "smoke_saturation",
            "smoke_brightness",
            "flame_color",
            "flame_intensity",
            "material_type",
            "custom_mat",
            "internal_mat",
            "mat_shell_depth",
            "random_mat_seed",
            "use_uv_map",
            "uv_image",
            "use_normals",
            "verify_exposure",
            "insideness_ray_cast_dir",
            "start_frame",
            "stop_frame",
            "use_animation",
            "auto_update_on_delete",
            "brick_shell",
            "calculation_axes",
            "use_local_orient",
            "brick_height",
            "bevel_width",
            "bevel_segments",
            "bevel_profile"]


def match_properties(cm_to, cm_from, override_idx=-1):
    scn = bpy.context.scene
    cm_attrs = get_cm_props()
    # remove properties that should not be matched
    if not cm_from.bevel_added or not cm_to.bevel_added:
        cm_attrs.remove("bevel_width")
        cm_attrs.remove("bevel_segments")
        cm_attrs.remove("bevel_profile")
    # match material properties for Random/ABS Plastic Snapping
    mat_obj_names_from = ["Bricker_{}_RANDOM_mats".format(cm_from.id), "Bricker_{}_ABS_mats".format(cm_from.id)]
    mat_obj_names_to   = ["Bricker_{}_RANDOM_mats".format(cm_to.id), "Bricker_{}_ABS_mats".format(cm_to.id)]
    for i in range(2):
        mat_obj_from = bpy.data.objects.get(mat_obj_names_from[i])
        mat_obj_to = bpy.data.objects.get(mat_obj_names_to[i])
        if mat_obj_from is None or mat_obj_to is None:
            continue
        mat_obj_to.data.materials.clear(update_data=True)
        for mat in mat_obj_from.data.materials:
            mat_obj_to.data.materials.append(mat)
    # match properties from 'cm_from' to 'cm_to'
    if override_idx >= 0:
        orig_idx = scn.cmlist_index
        scn.cmlist_index = override_idx
    for attr in cm_attrs:
        old_val = getattr(cm_from, attr)
        setattr(cm_to, attr, old_val)
    if override_idx >= 0:
        scn.cmlist_index = orig_idx
