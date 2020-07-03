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

bl_info = {
    "name"        : "Bricker",
    "author"      : "Christopher Gearhart <chris@bblanimation.com>",
    "version"     : (2, 1, 0),
    "blender"     : (2, 83, 0),
    "description" : "Turn any mesh into a 3D brick sculpture or simulation with the click of a button",
    "location"    : "View3D > Tools > Bricker",
    "warning"     : "Demo Version – Full version available at the Blender Market!",  # used for warning icon and text in addons panel
    "wiki_url"    : "https://www.blendermarket.com/products/bricker/",
    "doc_url"     : "https://www.blendermarket.com/products/bricker/",  # 2.83+
    "tracker_url" : "https://www.blendermarket.com/products/bricker/",
    "category"    : "Object",
}

developer_mode = 1  # NOTE: Set to 0 for release, 1 for developer mode
# NOTE: Remove beta warning from bl_info

# System imports
# NONE!

# Blender imports
import bpy
from bpy.props import *
from bpy.types import WindowManager, Object, Scene, Material
from bpy.utils import register_class, unregister_class

# Module imports
from .functions.brick import get_legal_brick_sizes
from .functions.common import b280, make_annotations
from .functions.app_handlers import *
from .functions.timers import register_bricker_timers, handle_selections, handle_undo_stack
from .functions.property_callbacks import select_source_model
from .lib import keymaps, classes_to_register
from .lib.property_groups import BRICKER_UL_collections_tuple, CreatedModelProperties
from .lib.mat_properties import mat_properties

# store keymaps here to access after registration
addon_keymaps = []


def register():
    for cls in classes_to_register.classes:
        make_annotations(cls)
        bpy.utils.register_class(cls)

    bpy.props.bricker_module_name = __name__
    bpy.props.bricker_version = str(bl_info["version"])[1:-1].replace(", ", ".")

    bpy.props.bricker_initialized = b280()  # automatically initialized (uses timer) in b280
    bpy.props.bricker_updating_undo_state = False
    bpy.props.bricker_developer_mode = developer_mode
    bpy.props.bricker_last_selected = []
    bpy.props.bricker_trans_and_anim_data = []
    bpy.props.manual_cmlist_update = False
    bpy.props.bfm_cache_bytes_hex = None
    bpy.props.abs_mat_properties = mat_properties  # duplicate from ABS Plastic Mats, necessary for exporting to ldraw from non-abs mats

    Object.protected = BoolProperty(
        name="protected",
        default=False,
    )
    Object.is_brickified_object = BoolProperty(
        name="Is Brickified Object",
        default=False,
    )
    Object.is_brick = BoolProperty(
        name="Is Brick",
        default=False,
    )
    Object.cmlist_id = IntProperty(
        name="Custom Model ID",
        description="ID of cmlist entry to which this object refers",
        default=-1,
    )
    Object.smoke_data = StringProperty(
        name="Smoke Data",
        description="Smoke data stored for brickify operation",
        default="",
    )
    # if b280():
    Object.stored_parents = CollectionProperty(type=BRICKER_UL_collections_tuple)
    Material.num_averaged = IntProperty(
        name="Colors Averaged",
        description="Number of colors averaged together",
        default=0,
    )

    WindowManager.bricker_running_blocking_operation = BoolProperty(default=False)

    Scene.bricker_last_layers = StringProperty(default="")
    Scene.bricker_active_object_name = StringProperty(default="")
    Scene.bricker_last_active_object_name = StringProperty(default="")

    Scene.bricker_copy_from_id = IntProperty(default=-1)

    # define legal brick sizes (key:height, val:[width,depth])
    bpy.props.bricker_legal_brick_sizes = get_legal_brick_sizes()

    # Add attribute for Bricker Instructions addon
    Scene.is_bricker_installed = BoolProperty(default=True)

    Scene.include_transparent = BoolProperty(
        name="Include Transparent",
        description="Include transparent ABS Plastic materials",
        default=False,
    )
    Scene.include_uncommon = BoolProperty(
        name="Include Uncommon",
        description="Include uncommon ABS Plastic materials",
        default=False,
    )

    # Scene.bricker_snapping = BoolProperty(
    #     name="Bricker Snap",
    #     description="Snap to brick dimensions",
    #     default=False,
    # )
    # bpy.types.VIEW3D_HT_header.append(Bricker_snap_button)

    # other things (UI List)
    Scene.cmlist = CollectionProperty(type=CreatedModelProperties)
    Scene.cmlist_index = IntProperty(default=-1, update=select_source_model)

    # handle the keymaps
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon: # check this to avoid errors in background case
        km = wm.keyconfigs.addon.keymaps.new(name="Object Mode", space_type="EMPTY")
        keymaps.add_keymaps(km)
        addon_keymaps.append(km)

    # register app handlers and timers
    bpy.app.handlers.frame_change_post.append(handle_animation)
    if not bpy.app.background:
        if b280():
            bpy.app.handlers.load_post.append(register_bricker_timers)
        else:
            bpy.app.handlers.scene_update_pre.append(handle_selections)
    bpy.app.handlers.load_pre.append(clear_bfm_cache)
    bpy.app.handlers.load_post.append(handle_loading_to_light_cache)
    bpy.app.handlers.save_pre.append(handle_storing_to_deep_cache)
    bpy.app.handlers.load_post.append(handle_upconversion)
    bpy.app.handlers.load_post.append(reset_properties)


def unregister():
    # unregister app handlers
    bpy.app.handlers.load_post.remove(reset_properties)
    bpy.app.handlers.load_post.remove(handle_upconversion)
    bpy.app.handlers.save_pre.remove(handle_storing_to_deep_cache)
    bpy.app.handlers.load_post.remove(handle_loading_to_light_cache)
    bpy.app.handlers.load_pre.remove(clear_bfm_cache)
    if b280():
        if bpy.app.timers.is_registered(handle_selections):
            bpy.app.timers.unregister(handle_selections)
        if bpy.app.timers.is_registered(handle_undo_stack):
            bpy.app.timers.unregister(handle_undo_stack)
        if not bpy.app.background:
            bpy.app.handlers.load_post.remove(register_bricker_timers)
    elif not bpy.app.background:
        bpy.app.handlers.scene_update_pre.remove(handle_selections)
    bpy.app.handlers.frame_change_post.remove(handle_animation)

    # handle the keymaps
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()

    del Scene.cmlist_index
    del Scene.cmlist
    # bpy.types.VIEW3D_HT_header.remove(Bricker_snap_button)
    # del Scene.bricker_snapping
    del Scene.include_uncommon
    del Scene.include_transparent
    del Scene.is_bricker_installed
    del Scene.bricker_copy_from_id
    del Scene.bricker_last_active_object_name
    del Scene.bricker_active_object_name
    del Scene.bricker_last_layers
    del WindowManager.bricker_running_blocking_operation
    del Material.num_averaged
    if hasattr(Object, "stored_parents"):
        del Object.stored_parents
    del Object.smoke_data
    del Object.cmlist_id
    del Object.is_brick
    del Object.is_brickified_object
    del Object.protected
    if hasattr(bpy.props, "abs_mat_properties"):
        del bpy.props.abs_mat_properties
    del bpy.props.bfm_cache_bytes_hex
    del bpy.props.manual_cmlist_update
    del bpy.props.bricker_trans_and_anim_data
    del bpy.props.bricker_last_selected
    del bpy.props.bricker_developer_mode
    del bpy.props.bricker_updating_undo_state
    del bpy.props.bricker_initialized
    del bpy.props.bricker_version
    del bpy.props.bricker_module_name

    for cls in reversed(classes_to_register.classes):
        bpy.utils.unregister_class(cls)
