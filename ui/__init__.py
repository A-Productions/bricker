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
from addon_utils import check, paths, enable
from bpy.types import Panel
from bpy.props import *
props = bpy.props

# Addon imports
from .cmlist_attrs import *
from .cmlist_actions import *
from .app_handlers import *
from .timers import *
from .matlist_window import *
from .matlist_actions import *
from ..lib.bricksdict import *
from ..lib.brick.test_brick_generators import *
from ..lib.caches import cache_exists
from ..buttons.revert_settings import *
from ..buttons.brickify import *
from ..buttons.customize.tools.bricksculpt import *
from ..functions import *
from ..functions.brickify_utils import get_model_resolution
from .. import addon_updater_ops
if b280():
    from .other_property_groups import *


def settings_can_be_drawn():
    scn = bpy.context.scene
    if scn.cmlist_index == -1:
        return False
    if bversion() < "002.079":
        return False
    if not bpy.props.bricker_initialized:
        return False
    return True


class BRICKER_MT_specials(bpy.types.Menu):
    bl_idname      = "BRICKER_MT_specials"
    bl_label       = "Select"

    def draw(self, context):
        layout = self.layout

        layout.operator("cmlist.copy_settings_to_others", icon="COPY_ID", text="Copy Settings to Others")
        layout.operator("cmlist.copy_settings", icon="COPYDOWN", text="Copy Settings")
        layout.operator("cmlist.paste_settings", icon="PASTEDOWN", text="Paste Settings")
        layout.operator("cmlist.select_bricks", icon="RESTRICT_SELECT_OFF", text="Select Bricks").deselect = False
        layout.operator("cmlist.select_bricks", icon="RESTRICT_SELECT_ON", text="Deselect Bricks").deselect = True


class VIEW3D_PT_bricker_brick_models(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Brick Models"
    bl_idname      = "VIEW3D_PT_bricker_brick_models"
    bl_context     = "objectmode"

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        # Call to check for update in background
        # Internally also checks to see if auto-check enabled
        # and if the time interval has passed
        addon_updater_ops.check_for_update_background()
        # draw auto-updater update box
        addon_updater_ops.update_notice_box_ui(self, context)

        # if blender version is before 2.79, ask user to upgrade Blender
        if bversion() < "002.079":
            col = layout.column(align=True)
            col.label(text="ERROR: upgrade needed", icon="ERROR")
            col.label(text="Bricker requires Blender 2.79+")
            return

        # draw UI list and list actions
        rows = 2 if len(scn.cmlist) < 2 else 4
        row = layout.row()
        row.template_list("CMLIST_UL_items", "", scn, "cmlist", scn, "cmlist_index", rows=rows)

        col = row.column(align=True)
        col.operator("cmlist.list_action" if bpy.props.bricker_initialized else "bricker.initialize", text="", icon="ADD" if b280() else "ZOOMIN").action = "ADD"
        col.operator("cmlist.list_action", icon="REMOVE" if b280() else "ZOOMOUT", text="").action = "REMOVE"
        col.menu("BRICKER_MT_specials", icon="DOWNARROW_HLT", text="")
        if len(scn.cmlist) > 1:
            col.separator()
            col.operator("cmlist.list_action", icon="TRIA_UP", text="").action = "UP"
            col.operator("cmlist.list_action", icon="TRIA_DOWN", text="").action = "DOWN"

        # draw menu options below UI list
        if scn.cmlist_index == -1:
            layout.operator("cmlist.list_action" if bpy.props.bricker_initialized else "bricker.initialize", text="New Brick Model", icon="ADD" if b280() else "ZOOMIN").action = "ADD"
        else:
            cm, n = get_active_context_info()[1:]
            if not created_with_newer_version(cm):
                # first, draw source object text
                source_name = " %(n)s" % locals() if cm.animated or cm.model_created else ""
                col1 = layout.column(align=True)
                col1.label(text="Source Object:%(source_name)s" % locals())
                if not (cm.animated or cm.model_created):
                    col2 = layout.column(align=True)
                    col2.prop_search(cm, "source_obj", scn, "objects", text="")

            # initialize variables
            obj = cm.source_obj
            v_str = cm.version[:3]

            # if model created with newer version, disable
            if created_with_newer_version(cm):
                col = layout.column(align=True)
                col.scale_y = 0.7
                col.label(text="Model was created with")
                col.label(text="Bricker v%(v_str)s. Please" % locals())
                col.label(text="update Bricker in your")
                col.label(text="addon preferences to edit")
                col.label(text="this model.")
            # if undo stack not initialized, draw initialize button
            elif not bpy.props.bricker_initialized:
                row = col1.row(align=True)
                row.operator("bricker.initialize", text="Initialize Bricker", icon="MODIFIER")
                # draw test brick generator button (for testing purposes only)
                if BRICKER_OT_test_brick_generators.draw_ui_button():
                    col = layout.column(align=True)
                    col.operator("bricker.test_brick_generators", text="Test Brick Generators", icon="OUTLINER_OB_MESH")
            # if use animation is selected, draw animation options
            elif cm.use_animation:
                if cm.animated:
                    row = col1.row(align=True)
                    row.operator("bricker.delete_model", text="Delete Brick Animation", icon="CANCEL")
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    if cm.brickifying_in_background and cm.frames_to_animate > 0:
                        col.scale_y = 0.75
                        row.label(text="Animating...")
                        row.operator("bricker.stop_brickifying_in_background", text="Stop", icon="PAUSE")
                        row = col.row(align=True)
                        percentage = round(cm.num_animated_frames * 100 / cm.frames_to_animate, 2)
                        row.label(text=str(percentage) + "% completed")
                    else:
                        row.active = brickify_should_run(cm)
                        row.operator("bricker.brickify", text="Update Animation", icon="FILE_REFRESH")
                    if created_with_unsupported_version(cm):
                        v_str = cm.version[:3]
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        col.label(text="Model was created with")
                        col.label(text="Bricker v%(v_str)s. Please" % locals())
                        col.label(text="run 'Update Model' so")
                        col.label(text="it is compatible with")
                        col.label(text="your current version.")
                else:
                    row = col1.row(align=True)
                    row.active = obj is not None and obj.type == "MESH" and (obj.rigid_body is None or obj.rigid_body.type == "PASSIVE")
                    row.operator("bricker.brickify", text="Brickify Animation", icon="MOD_REMESH")
                    if obj and obj.rigid_body is not None:
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        if obj.rigid_body.type == "ACTIVE":
                            col.label(text="Bake rigid body transforms")
                            col.label(text="to keyframes (SPACEBAR >")
                            col.label(text="Bake To Keyframes).")
                        else:
                            col.label(text="Rigid body settings will")
                            col.label(text="be lost.")
            # if use animation is not selected, draw modeling options
            else:
                if not cm.animated and not cm.model_created:
                    row = col1.row(align=True)
                    row.active = obj is not None and obj.type == "MESH" and (obj.rigid_body is None or obj.rigid_body.type == "PASSIVE")
                    row.operator("bricker.brickify", text="Brickify Object", icon="MOD_REMESH")
                    if obj and obj.rigid_body is not None:
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        if obj.rigid_body.type == "ACTIVE":
                            col.label(text="Bake rigid body transforms")
                            col.label(text="to keyframes (SPACEBAR >")
                            col.label(text="Bake To Keyframes).")
                        else:
                            col.label(text="Rigid body settings will")
                            col.label(text="be lost.")
                else:
                    row = col1.row(align=True)
                    row.operator("bricker.delete_model", text="Delete Brickified Model", icon="CANCEL")
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    if cm.brickifying_in_background:
                        row.label(text="Brickifying...")
                        row.operator("bricker.stop_brickifying_in_background", text="Stop", icon="PAUSE")
                        # row = col.row(align=True)
                        # percentage = round(cm.num_animated_frames * 100 / cm.frames_to_animate, 2)
                        # row.label(text=str(percentage) + "% completed")
                    else:
                        row.active = brickify_should_run(cm)
                        row.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH")
                    if created_with_unsupported_version(cm):
                        col = layout.column(align=True)
                        col.scale_y = 0.7
                        col.label(text="Model was created with")
                        col.label(text="Bricker v%(v_str)s. Please" % locals())
                        col.label(text="run 'Update Model' so")
                        col.label(text="it is compatible with")
                        col.label(text="your current version.")
                    elif matrix_really_is_dirty(cm, include_lost_matrix=False) and cm.customized:
                        row = col.row(align=True)
                        row.label(text="Customizations will be lost")
                        row = col.row(align=True)
                        row.operator("bricker.revert_matrix_settings", text="Revert Settings", icon="LOOP_BACK")

            col = layout.column(align=True)
            row = col.row(align=True)

        if bpy.data.texts.find("Bricker log") >= 0:
            split = layout_split(layout, factor=0.9)
            col = split.column(align=True)
            row = col.row(align=True)
            row.operator("bricker.report_error", text="Report Error", icon="URL")
            col = split.column(align=True)
            row = col.row(align=True)
            row.operator("bricker.close_report_error", text="", icon="PANEL_CLOSE")


class VIEW3D_PT_bricker_animation(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Animation"
    bl_idname      = "VIEW3D_PT_bricker_animation"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, n = get_active_context_info()
        if cm.model_created:
            return False
        return True

    def draw_header(self, context):
        scn, cm, _ = get_active_context_info()
        if not cm.animated:
            self.layout.prop(cm, "use_animation", text="")

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        col1 = layout.column(align=True)
        col1.active = cm.animated or cm.use_animation
        col1.scale_y = 0.85
        row = col1.row(align=True)
        split = layout_split(row, factor=0.5)
        col = split.column(align=True)
        col.prop(cm, "start_frame")
        col = split.column(align=True)
        col.prop(cm, "stop_frame")
        source = cm.source_obj
        self.applied_mods = False
        if source:
            for mod in source.modifiers:
                if mod.type in ("CLOTH", "SOFT_BODY") and mod.show_viewport:
                    self.applied_mods = True
                    t = mod.type
                    if mod.point_cache.frame_end < cm.stop_frame:
                        s = str(max([mod.point_cache.frame_end+1, cm.start_frame]))
                        e = str(cm.stop_frame)
                    elif mod.point_cache.frame_start > cm.start_frame:
                        s = str(cm.start_frame)
                        e = str(min([mod.point_cache.frame_start-1, cm.stop_frame]))
                    else:
                        s = "0"
                        e = "-1"
                    total_skipped = int(e) - int(s) + 1
                    if total_skipped > 0:
                        row = col1.row(align=True)
                        row.label(text="Frames %(s)s-%(e)s outside of %(t)s simulation" % locals())


class VIEW3D_PT_bricker_model_transform(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Model Transform"
    bl_idname      = "VIEW3D_PT_bricker_model_transform"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if cm.model_created or cm.animated:
            return True
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, n = get_active_context_info()

        col = layout.column(align=True)
        right_align(col)
        row = col.row(align=True)

        if not (cm.animated or cm.last_split_model):
            col.scale_y = 0.7
            row.label(text="Use Blender's built-in")
            row = col.row(align=True)
            row.label(text="transformation manipulators")
            col = layout.column(align=True)
            return

        row.prop(cm, "apply_to_source_object")
        if cm.animated or (cm.last_split_model and cm.model_created):
            row = col.row(align=True)
            row.prop(cm, "expose_parent")
        row = col.row(align=True)
        parent = bpy.data.objects["Bricker_%(n)s_parent" % locals()]
        row = layout.row()
        row.column().prop(parent, "location")
        if parent.rotation_mode == "QUATERNION":
            row.column().prop(parent, "rotation_quaternion", text="Rotation")
        elif parent.rotation_mode == "AXIS_ANGLE":
            row.column().prop(parent, "rotation_axis_angle", text="Rotation")
        else:
            row.column().prop(parent, "rotation_euler", text="Rotation")
        # row.column().prop(parent, "scale")
        layout.prop(parent, "rotation_mode")
        layout.prop(cm, "transform_scale")


class VIEW3D_PT_bricker_model_settings(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Model Settings"
    bl_idname      = "VIEW3D_PT_bricker_model_settings"
    bl_context     = "objectmode"

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        source = cm.source_obj

        col = layout.column(align=True)
        # draw Brick Model dimensions to UI
        if source:
            r = get_model_resolution(source, cm)
            if cm.brick_type == "CUSTOM" and r is None:
                col.label(text="[Custom object not found]")
            else:
                split = layout_split(col, factor=0.5)
                col1 = split.column(align=True)
                col1.label(text="Dimensions:")
                col2 = split.column(align=True)
                col2.alignment = "RIGHT"
                col2.label(text="{}x{}x{}".format(int(r.x), int(r.y), int(r.z)))
        row = col.row(align=True)
        row.prop(cm, "brick_height")
        row = col.row(align=True)
        row.prop(cm, "gap")

        row = col.row(align=True)
        # if not cm.use_animation:
        col = layout.column()
        row = col.row(align=True)
        right_align(row)
        row.active = not cm.use_animation
        row.prop(cm, "split_model")

        col = layout.column()
        row = col.row(align=True)
        row.active = cm.calc_internals
        row.prop(cm, "shell_thickness")

        col = layout.column()
        row = col.row(align=True)
        row.label(text="Randomize:")
        row = col.row(align=True)
        split = layout_split(row, factor=0.5)
        col1 = split.column(align=True)
        col1.prop(cm, "random_loc", text="Loc")
        col2 = split.column(align=True)
        col2.prop(cm, "random_rot", text="Rot")


class VIEW3D_PT_bricker_customize(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Customize Model"
    bl_idname      = "VIEW3D_PT_bricker_customize"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if created_with_unsupported_version(cm):
            return False
        if not (cm.model_created or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        if matrix_really_is_dirty(cm):
            layout.label(text="Matrix is dirty!")
            col = layout.column(align=True)
            col.label(text="Model must be updated to customize:")
            col.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH")
            if cm.customized and not cm.matrix_lost:
                row = col.row(align=True)
                row.label(text="Prior customizations will be lost")
                row = col.row(align=True)
                row.operator("bricker.revert_matrix_settings", text="Revert Settings", icon="LOOP_BACK")
            return
        if cm.animated:
            layout.label(text="Not available for animations")
            return
        if not cm.last_split_model:
            col = layout.column(align=True)
            col.label(text="Model must be split to customize:")
            col.operator("bricker.brickify", text="Split & Update Model", icon="FILE_REFRESH").split_before_update = True
            return
        if cm.build_is_dirty:
            col = layout.column(align=True)
            col.label(text="Model must be updated to customize:")
            col.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH")
            return
        if cm.brickifying_in_background:
            col = layout.column(align=True)
            col.label(text="Model is brickifying...")
            return
        elif not cache_exists(cm):
            layout.label(text="Matrix not cached!")
            col = layout.column(align=True)
            col.label(text="Model must be updated to customize:")
            col.operator("bricker.brickify", text="Update Model", icon="FILE_REFRESH")
            if cm.customized:
                row = col.row(align=True)
                row.label(text="Customizations will be lost")
                row = col.row(align=True)
                row.operator("bricker.revert_matrix_settings", text="Revert Settings", icon="LOOP_BACK")
            return
        # if not bpy.props.bricker_initialized:
        #     layout.operator("bricker.initialize", icon="MODIFIER")
        #     return

        # # display BrickSculpt tools
        # col = layout.column(align=True)
        # row = col.row(align=True)
        # # brickSculptInstalled = hasattr(bpy.props, "bricksculpt_module_name")
        # # row.active = brickSculptInstalled
        # col.active = False
        # row.label(text="BrickSculpt Tools:")
        # row = col.row(align=True)
        # row.operator("bricker.bricksculpt", text="Draw/Cut Tool", icon="MOD_DYNAMICPAINT").mode = "DRAW"
        # row = col.row(align=True)
        # row.operator("bricker.bricksculpt", text="Merge/Split Tool", icon="MOD_DYNAMICPAINT").mode = "MERGE/SPLIT"
        # row = col.row(align=True)
        # row.operator("bricker.bricksculpt", text="Paintbrush Tool", icon="MOD_DYNAMICPAINT").mode = "PAINT"
        # row.prop_search(cm, "paintbrush_mat", bpy.data, "materials", text="")
        # if not BRICKER_OT_bricksculpt.bricksculpt_installed:
        #     row = col.row(align=True)
        #     row.scale_y = 0.7
        #     row.label(text="BrickSculpt available for purchase")
        #     row = col.row(align=True)
        #     row.scale_y = 0.7
        #     row.label(text="at the Blender Market:")
        #     col = layout.column(align=True)
        #     row = col.row(align=True)
        #     row.operator("wm.url_open", text="View Website", icon="WORLD").url = "http://www.blendermarket.com/products/bricksculpt"
        #     layout.split()
        #     layout.split()

        col1 = layout.column(align=True)
        col1.label(text="Selection:")
        split = layout_split(col1, factor=0.5)
        # set top exposed
        col = split.column(align=True)
        col.operator("bricker.select_bricks_by_type", text="By Type")
        # set bottom exposed
        col = split.column(align=True)
        col.operator("bricker.select_bricks_by_size", text="By Size")

        col1 = layout.column(align=True)
        col1.label(text="Toggle Exposure:")
        split = layout_split(col1, factor=0.5)
        # set top exposed
        col = split.column(align=True)
        col.operator("bricker.set_exposure", text="Top").side = "TOP"
        # set bottom exposed
        col = split.column(align=True)
        col.operator("bricker.set_exposure", text="Bottom").side = "BOTTOM"

        col1 = layout.column(align=True)
        col1.label(text="Brick Operations:")
        split = layout_split(col1, factor=0.5)
        # split brick into 1x1s
        col = split.column(align=True)
        col.operator("bricker.split_bricks", text="Split")
        # merge selected bricks
        col = split.column(align=True)
        col.operator("bricker.merge_bricks", text="Merge")
        # Add identical brick on +/- x/y/z
        row = col1.row(align=True)
        row.operator("bricker.draw_adjacent", text="Draw Adjacent Bricks")
        # change brick type
        row = col1.row(align=True)
        row.operator("bricker.change_brick_type", text="Change Type")
        # change material type
        row = col1.row(align=True)
        row.operator("bricker.change_brick_material", text="Change Material")
        # additional controls
        row = col1.row(align=True)
        right_align(row)
        row.prop(cm, "auto_update_on_delete")
        # row = col.row(align=True)
        # row.operator("bricker.redraw_bricks")


class VIEW3D_PT_bricker_smoke_settings(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Smoke Settings"
    bl_idname      = "VIEW3D_PT_bricker_smoke_settings"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        if not settings_can_be_drawn():
            return False
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        source = cm.source_obj
        if source is None:
            return False
        return is_smoke(source)

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        source = cm.source_obj

        col = layout.column(align=True)
        if is_smoke(source):
            row = col.row(align=True)
            row.prop(cm, "smoke_density", text="Density")
            row = col.row(align=True)
            row.prop(cm, "smoke_quality", text="Quality")

        if is_smoke(source):
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Smoke Color:")
            row = col.row(align=True)
            row.prop(cm, "smoke_brightness", text="Brightness")
            row = col.row(align=True)
            row.prop(cm, "smoke_saturation", text="Saturation")
            row = col.row(align=True)
            row.label(text="Flame Color:")
            row = col.row(align=True)
            row.prop(cm, "flame_color", text="")
            row = col.row(align=True)
            row.prop(cm, "flame_intensity", text="Intensity")


class VIEW3D_PT_bricker_brick_types(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Brick Types"
    bl_idname      = "VIEW3D_PT_bricker_brick_types"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "brick_type", text="")

        if mergable_brick_type(cm.brick_type):
            col = layout.column(align=True)
            col.label(text="Max Brick Size:")
            row = col.row(align=True)
            row.prop(cm, "max_width", text="Width")
            row.prop(cm, "max_depth", text="Depth")
            col = layout.column(align=True)
            row = col.row(align=True)
            right_align(row)
            row.prop(cm, "legal_bricks_only")

        if cm.brick_type == "CUSTOM":
            col = layout.column(align=True)
            col.label(text="Brick Type Object:")
        elif cm.last_split_model:
            col.label(text="Custom Brick Objects:")
        if cm.brick_type == "CUSTOM" or cm.last_split_model:
            for prop in ("custom_object1", "custom_object2", "custom_object3"):
                if prop[-1] == "2" and cm.brick_type == "CUSTOM":
                    col.label(text="Distance Offset:")
                    row = col.row(align=True)
                    row.prop(cm, "dist_offset", text="")
                    if cm.last_split_model:
                        col = layout.column(align=True)
                        col.label(text="Other Objects:")
                    else:
                        break
                split = layout_split(col, factor=0.825)
                col1 = split.column(align=True)
                col1.prop_search(cm, prop, scn, "objects", text="")
                col1 = split.column(align=True)
                col1.operator("bricker.redraw_custom_bricks", icon="FILE_REFRESH", text="").target_prop = prop


class VIEW3D_PT_bricker_merge_settings(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Merge Settings"
    bl_idname      = "VIEW3D_PT_bricker_merge_settings"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        return mergable_brick_type(cm.brick_type)

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "merge_type", expand=True)
        if cm.merge_type == "RANDOM":
            row = col.row(align=True)
            row.prop(cm, "merge_seed")
            row = col.row(align=True)
            row.prop(cm, "connect_thresh")
        if cm.shell_thickness > 1:
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "merge_internals")
        if cm.brick_type == "BRICKS AND PLATES":
            row = col.row(align=True)
            right_align(row)
            row.prop(cm, "align_bricks")
            if cm.align_bricks:
                row = col.row(align=True)
                row.prop(cm, "offset_brick_layers")


class VIEW3D_PT_bricker_materials(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Materials"
    bl_idname      = "VIEW3D_PT_bricker_materials"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        obj = cm.source_obj

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "material_type", text="")

        if cm.material_type == "CUSTOM":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "custom_mat", text="")
            if brick_materials_installed() and not brick_materials_imported():
                row = col.row(align=True)
                row.operator("abs.append_materials", text="Import Brick Materials", icon="IMPORT")
            if cm.model_created or cm.animated:
                col = layout.column(align=True)
                row = col.row(align=True)
                row.operator("bricker.apply_material", icon="FILE_TICK")
        elif cm.material_type == "RANDOM":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "random_mat_seed")
            if cm.model_created or cm.animated:
                if cm.material_is_dirty and not cm.last_split_model:
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    row.label(text="Run 'Update Model' to apply changes")
                elif cm.last_material_type == cm.material_type or (not cm.use_animation and cm.last_split_model):
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    row.operator("bricker.apply_material", icon="FILE_TICK")
        elif cm.material_type == "SOURCE" and obj:
            # internal material info
            if cm.shell_thickness > 1 or cm.internal_supports != "NONE":
                # if len(obj.data.uv_layers) <= 0 or len(obj.data.vertex_colors) > 0:
                col = layout.column(align=True)
                row = col.row(align=True)
                row.label(text="Internal Material:")
                row = col.row(align=True)
                row.prop(cm, "internal_mat", text="")
                row = col.row(align=True)
                row.prop(cm, "mat_shell_depth")
                if cm.model_created:
                    row = col.row(align=True)
                    if cm.mat_shell_depth <= cm.last_mat_shell_depth:
                        row.operator("bricker.apply_material", icon="FILE_TICK")
                    else:
                        row.label(text="Run 'Update Model' to apply changes")

            # color snapping info
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Color Mapping:")
            row = col.row(align=True)
            row.prop(cm, "color_snap", expand=True)
            if cm.color_snap == "RGB":
                row = col.row(align=True)
                row.prop(cm, "color_snap_amount")
            if cm.color_snap == "ABS":
                row = col.row(align=True)
                row.prop(cm, "transparent_weight", text="Transparent Weight")

            if not b280() and cm.color_snap != "NONE":
                col = layout.column(align=True)
                col.active = len(obj.data.uv_layers) > 0
                row = col.row(align=True)
                row.prop(cm, "use_uv_map", text="Use UV Map")
                split = layout_split(row, factor=0.75)
                # split.active = cm.use_uv_map
                if cm.use_uv_map:
                    split.prop(cm, "uv_image", text="")
                    split.operator("image.open", icon="FILEBROWSER" if b280() else "FILESEL", text="")
                if len(obj.data.vertex_colors) > 0:
                    col = layout.column(align=True)
                    col.scale_y = 0.7
                    col.label(text="(Vertex colors not supported)")


class VIEW3D_PT_bricker_use_uv_map(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Use UV Map"
    bl_parent_id   = "VIEW3D_PT_bricker_materials"
    bl_idname      = "VIEW3D_PT_bricker_use_uv_map"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        if not settings_can_be_drawn() or not b280():
            return False
        scn, cm, _ = get_active_context_info()
        obj = cm.source_obj
        if obj and len(obj.data.uv_layers) > 0 and cm.material_type == "SOURCE" and cm.color_snap != "NONE":
            return True
        return False

    def draw_header(self, context):
        scn, cm, _ = get_active_context_info()
        self.layout.prop(cm, "use_uv_map", text="")

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        obj = cm.source_obj

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "uv_image", text="Tex")
        row.operator("image.open", icon="FILEBROWSER" if b280() else "FILESEL", text="")


class VIEW3D_PT_bricker_included_materials(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Included Materials"
    bl_parent_id   = "VIEW3D_PT_bricker_materials"
    bl_idname      = "VIEW3D_PT_bricker_included_materials"
    bl_context     = "objectmode"

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if cm.material_type == "RANDOM" or (cm.material_type == "SOURCE" and cm.color_snap == "ABS"):
            return True
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        mat_obj = get_mat_obj(cm, typ=cm.material_type)
        if mat_obj is None:
            return
        col = layout.column(align=True)
        if not brick_materials_installed():
            col.label(text="'ABS Plastic Materials' not installed")
        elif scn.render.engine not in ("CYCLES", "BLENDER_EEVEE"):
            col.label(text="Switch to 'Cycles' or 'Eevee' for Brick Materials")
        else:
            # draw materials UI list and list actions
            num_mats = len(mat_obj.data.materials)
            rows = 5 if num_mats > 5 else (num_mats if num_mats > 2 else 2)
            split = layout_split(col, factor=0.85)
            col1 = split.column(align=True)
            col1.template_list("MATERIAL_UL_matslots", "", mat_obj, "material_slots", mat_obj, "active_material_index", rows=rows)
            col1 = split.column(align=True)
            col1.operator("bricker.mat_list_action", icon="REMOVE" if b280() else "ZOOMOUT", text="").action = "REMOVE"
            col1.scale_y = 1 + rows
            if not brick_materials_imported():
                col.operator("abs.append_materials", text="Import Brick Materials", icon="IMPORT")
            else:
                col.operator("bricker.add_abs_plastic_materials", text="Add ABS Plastic Materials", icon="ADD" if b280() else "ZOOMIN")
            # settings for adding materials
            if hasattr(bpy.props, "abs_mats_common"):  # checks that ABS plastic mats are at least v2.1
                col = layout.column(align=True)
                right_align(col)
                row = col.row(align=True)
                row.prop(scn, "include_transparent")
                row = col.row(align=True)
                row.prop(scn, "include_uncommon")

            col = layout.column(align=True)
            split = layout_split(col, factor=0.25)
            col = split.column(align=True)
            col.label(text="Add:")
            col = split.column(align=True)
            col.prop_search(cm, "target_material", bpy.data, "materials", text="")


class VIEW3D_PT_bricker_material_properties(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Material Properties"
    bl_idname      = "VIEW3D_PT_bricker_material_properties"
    bl_parent_id   = "VIEW3D_PT_bricker_materials"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        obj = cm.source_obj
        if cm.material_type == "SOURCE" and obj:
            if cm.color_snap == "RGB" or (cm.use_uv_map and len(obj.data.uv_layers) > 0 and cm.color_snap == "NONE"):
                return True
        return False

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        obj = cm.source_obj

        if scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane"):
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "color_snap_specular")
            row = col.row(align=True)
            row.prop(cm, "color_snap_roughness")
            row = col.row(align=True)
            row.prop(cm, "color_snap_ior")
        if scn.render.engine in ("CYCLES", "BLENDER_EEVEE"):
            row = col.row(align=True)
            row.prop(cm, "color_snap_sss")
            row = col.row(align=True)
            row.prop(cm, "color_snap_sss_saturation")
            row = col.row(align=True)
            row.prop(cm, "color_snap_transmission")
        if scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane"):
            row = col.row(align=True)
            right_align(row)
            row.prop(cm, "include_transparency")


class VIEW3D_PT_bricker_detailing(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Detailing"
    bl_idname      = "VIEW3D_PT_bricker_detailing"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        if cm.brick_type == "CUSTOM":
            col = layout.column(align=True)
            col.scale_y = 0.7
            row = col.row(align=True)
            row.label(text="(ignored for custom brick types)")
            layout.active = False
            layout.separator()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Studs:")
        row = col.row(align=True)
        row.prop(cm, "stud_detail", text="")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Logo:")
        row = col.row(align=True)
        row.prop(cm, "logo_type", text="")
        if cm.logo_type != "NONE":
            if cm.logo_type == "LEGO":
                row = col.row(align=True)
                row.prop(cm, "logo_resolution", text="Resolution")
                row.prop(cm, "logo_decimate", text="Decimate")
                row = col.row(align=True)
            else:
                row = col.row(align=True)
                row.prop_search(cm, "logo_object", scn, "objects", text="")
                row = col.row(align=True)
                row.prop(cm, "logo_scale", text="Scale")
            row.prop(cm, "logo_inset", text="Inset")
            col = layout.column(align=True)

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Underside:")
        row = col.row(align=True)
        row.prop(cm, "hidden_underside_detail", text="")
        # row = col2.row(align=True)
        row.prop(cm, "exposed_underside_detail", text="")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Circles:")
        row = col.row(align=True)
        row.prop(cm, "circle_verts", text="Vertices")

        col = layout.column(align=True)
        row = col.row(align=True)
        split = layout_split(row, factor=0.5)
        col1 = split.column(align=True)
        col1.label(text="Bevel:")
        if not (cm.model_created or cm.animated) or cm.brickifying_in_background:
            row = col.row(align=True)
            # right_align(row)
            row.prop(cm, "bevel_added", text="Bevel Bricks")
            return
        try:
            test_brick = get_bricks()[0]
            bevel = test_brick.modifiers[test_brick.name + "_bvl"]
            col2 = split.column(align=True)
            row = col2.row(align=True)
            row.prop(cm, "bevel_show_render", icon="RESTRICT_RENDER_OFF", toggle=True)
            row.prop(cm, "bevel_show_viewport", icon="RESTRICT_VIEW_OFF", toggle=True)
            row.prop(cm, "bevel_show_edit_mode", icon="EDITMODE_HLT", toggle=True)
            row = col.row(align=True)
            row.prop(cm, "bevel_width", text="Width")
            row = col.row(align=True)
            row.prop(cm, "bevel_segments", text="Segments")
            row = col.row(align=True)
            row.prop(cm, "bevel_profile", text="Profile")
            row = col.row(align=True)
            row.operator("bricker.bevel", text="Remove Bevel", icon="CANCEL")
        except (IndexError, KeyError):
            row = col.row(align=True)
            row.operator("bricker.bevel", text="Bevel bricks", icon="MOD_BEVEL")


class VIEW3D_PT_bricker_supports(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Supports"
    bl_idname      = "VIEW3D_PT_bricker_supports"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()
        layout.active = cm.calc_internals

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "internal_supports", text="")
        if cm.internal_supports == "LATTICE":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "lattice_step")
            row = col.row(align=True)
            row.active == cm.lattice_step > 1
            row.prop(cm, "lattice_height")
            row = col.row(align=True)
            right_align(row)
            row.prop(cm, "alternate_xy")
        elif cm.internal_supports == "COLUMNS":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "col_thickness")
            row = col.row(align=True)
            row.prop(cm, "col_step")


class VIEW3D_PT_bricker_advanced(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Advanced"
    bl_idname      = "VIEW3D_PT_bricker_advanced"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        return True

    def draw(self, context):
        layout = self.layout
        # right_align(layout)
        scn, cm, n = get_active_context_info()

        # Alert user that update is available
        if addon_updater_ops.updater.update_ready:
            col = layout.column(align=True)
            col.scale_y = 0.7
            col.label(text="Bricker update available!", icon="INFO")
            col.label(text="Install from Bricker addon prefs")
            layout.separator()

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("bricker.clear_cache", text="Clear Cache")

        # if not b280():
        #     VIEW3D_PT_bricker_advanced_ray_casting.draw(self, context)
        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text="Ray Casting:")
        row = col.row(align=True)
        row.prop(cm, "insideness_ray_cast_dir", text="")
        row = col.row(align=True)
        row.prop(cm, "use_normals")
        row = col.row(align=True)
        row.prop(cm, "verify_exposure")
        row = col.row(align=True)
        row.prop(cm, "calc_internals")
        row = col.row(align=True)
        row.prop(cm, "brick_shell", text="Shell")
        if cm.brick_shell == "OUTSIDE":
            row = col.row(align=True)
            row.prop(cm, "calculation_axes", text="")

        if not (cm.use_animation and cm.animated):
            # if not b280():
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Meshes:")
            row = col.row(align=True)
            row.active = not cm.use_animation and cm.split_model
            row.prop(cm, "instance_bricks")

        # model orientation preferences
        if not cm.use_animation and not (cm.model_created or cm.animated):
            # if not b280():
            col = layout.column(align=True)
            row = col.row(align=True)
            row.label(text="Model Orientation:")
            row = col.row(align=True)
            col.prop(cm, "use_local_orient", text="Use Local Orientation")

        # background processing preferences
        if cm.use_animation and get_addon_preferences().brickify_in_background != "OFF":
            col = layout.column(align=True)
            # if not b280():
            row = col.row(align=True)
            row.label(text="Background Processing:")
            row = col.row(align=True)
            row.prop(cm, "max_workers")

        # draw test brick generator button (for testing purposes only)
        if BRICKER_OT_test_brick_generators.draw_ui_button():
            col = layout.column(align=True)
            col.operator("bricker.test_brick_generators", text="Test Brick Generators", icon="OUTLINER_OB_MESH")


class VIEW3D_PT_bricker_matrix_details(Panel):
    """ Display Matrix details for specified brick location """
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Brick Details"
    bl_idname      = "VIEW3D_PT_bricker_matrix_details"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if bpy.props.bricker_developer_mode == 0:
            return False
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if created_with_unsupported_version(cm):
            return False
        if not (cm.model_created or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        if matrix_really_is_dirty(cm):
            layout.label(text="Matrix is dirty!")
            return
        if not cache_exists(cm):
            layout.label(text="Matrix not cached!")
            return

        col1 = layout.column(align=True)
        row = col1.row(align=True)
        row.prop(cm, "active_key", text="")

        if cm.animated:
            bricksdict = get_bricksdict(cm, dType="ANIM", cur_frame=get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame))
        elif cm.model_created:
            bricksdict = get_bricksdict(cm)
        if bricksdict is None:
            layout.label(text="Matrix not available")
            return
        try:
            dkey = list_to_str(tuple(cm.active_key))
            brick_d = bricksdict[dkey]
        except Exception as e:
            layout.label(text="No brick details available")
            if len(bricksdict) == 0:
                print("[Bricker] Skipped drawing Brick Details")
            elif str(e)[1:-1] == dkey:
                pass
                # print("[Bricker] Key '" + str(dkey) + "' not found")
            elif dkey is None:
                print("[Bricker] Key not set (entered else)")
            else:
                print("[Bricker] Error fetching brick_d:", e)
            return

        col1 = layout.column(align=True)
        split = layout_split(col1, factor=0.35)
        # hard code keys so that they are in the order I want
        keys = ["name", "val", "draw", "co", "near_face", "near_intersection", "near_normal", "mat_name", "custom_mat_name", "rgba", "parent", "size", "attempted_merge", "top_exposed", "bot_exposed", "type", "flipped", "rotated", "created_from"]
        # draw keys
        col = split.column(align=True)
        col.scale_y = 0.65
        row = col.row(align=True)
        row.label(text="key:")
        for key in keys:
            row = col.row(align=True)
            row.label(text=key + ":")
        # draw values
        col = split.column(align=True)
        col.scale_y = 0.65
        row = col.row(align=True)
        row.label(text=dkey)
        for key in keys:
            row = col.row(align=True)
            row.label(text=str(brick_d[key]))

class VIEW3D_PT_bricker_export(Panel):
    """ Export Bricker Model """
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Bake/Export"
    bl_idname      = "VIEW3D_PT_bricker_export"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, _ = get_active_context_info()
        if created_with_unsupported_version(cm):
            return False
        if not (cm.model_created or cm.animated):
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        col = layout.column(align=True)
        col.operator("bricker.bake_model", text="Bake Model" if cm.model_created else "Bake Current Frame", icon="OBJECT_DATA")
        if (cm.model_created or cm.animated) and cm.brick_type != "CUSTOM":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator("bricker.export_ldraw", text="Export Ldraw", icon="EXPORT")
