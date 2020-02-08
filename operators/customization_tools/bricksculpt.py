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
import bmesh
import math

# Blender imports
import bpy
import bgl
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d
from bpy.types import Operator, SpaceView3D, bpy_struct
from bpy.props import *

# Module imports
try:
    from .bricksculpt_framework import *
except ModuleNotFoundError:
    from .bricksculpt_framework_backup import *
from .bricksculpt_tools import *
from .bricksculpt_drawing import *
from .draw_adjacent import *
from ..brickify import *
from ...lib.undo_stack import *
from ...functions import *
from ...operators.overrides.delete_object import OBJECT_OT_delete_override


class BRICKER_OT_bricksculpt(Operator, BricksculptFramework, BricksculptTools, BricksculptDrawing):
    """Run the BrickSculpt editing tool suite"""
    bl_idname = "bricker.bricksculpt"
    bl_label = "BrickSculpt Tools"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        if not bpy.props.bricker_initialized:
            return False
        return True

    def execute(self, context):
        try:
            # try installing BrickSculpt
            if not self.bricksculpt_installed:
                status = install_bricksculpt()
                if status:
                    self.bricksculpt_installed = True
            if self.bricksculpt_loaded:
                if not hasattr(bpy.props, "bricksculpt_module_name"):
                    self.report({"WARNING"}, "Please enable the 'BrickSculpt' addon from the 'Preferences > Addons' menu")
                    return {"CANCELLED"}
                if bpy.props.running_bricksculpt_tool:
                    return {"CANCELLED"}
                if self.mode == "DRAW" and self.brick_type == "":
                    self.report({"WARNING"}, "Please choose a target brick type")
                    return {"CANCELLED"}
                if self.mode == "PAINT" and self.mat_name == "":
                    self.report({"WARNING"}, "Please choose a material for the paintbrush")
                    return {"CANCELLED"}
                self.ui_start()
                bpy.props.running_bricksculpt_tool = True
                scn, cm, _ = get_active_context_info()
                self.undo_stack.iterate_states(cm)
                cm.customized = True
                # get fresh copy of self.bricksdict
                self.bricksdict = get_bricksdict(cm)
                # create modal handler
                wm = context.window_manager
                wm.modal_handler_add(self)
                return {"RUNNING_MODAL"}
            elif self.bricksculpt_installed and not self.bricksculpt_loaded:
                self.report({"WARNING"}, "Please reload Blender to complete the BrickSculpt installation")
                return {"CANCELLED"}
            else:
                self.report({"WARNING"}, "Please install & enable BrickSculpt from the 'Preferences > Addons' menu")
                return {"CANCELLED"}
        except:
            bricker_handle_exception()
            return {"CANCELLED"}

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, n = get_active_context_info()
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push("bricksculpt_mode", affected_ids=[cm.id])
        # initialize vars
        self.added_bricks = []
        self.added_bricks_from_delete = []
        self.parent_locs_to_merge_on_release = []
        self.keys_to_merge_on_release = []
        self.all_updated_keys = []
        self.dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
        self.obj = None
        self.cm_idx = cm.idx
        self.zstep = cm.zstep
        self.keys_to_merge_on_commit = []
        self.brick_type = get_brick_type(cm.brick_type)
        self.mat_name = cm.paintbrush_mat.name if cm.paintbrush_mat is not None else ""  # bpy.data.materials[-1].name if len(bpy.data.materials) > 0 else ""
        self.hidden_bricks = []
        self.release_time = 0
        self.vertical = False
        self.horizontal = True
        self.last_mouse = Vector((0, 0))
        self.mouse_travel = 0
        self.junk_bme = bmesh.new()
        self.parent = bpy.data.objects.get("Bricker_%(n)s_parent" % locals())
        deselect_all()
        # ui properties
        self.left_click = False
        self.double_ctrl = False
        self.ctrl_click_time = -1
        self.layer_solod = None
        self.possible_ctrl_disable = False
        # self.points = [(math.cos(d*math.pi/180.0),math.sin(d*math.pi/180.0)) for d in range(0,361,10)]
        # self.ox = Vector((1,0,0))
        # self.oy = Vector((0,1,0))
        # self.oz = Vector((0,0,1))
        # self.radius = 50.0
        # self.falloff = 1.5
        # self.strength = 0.5
        # self.scale = 0.0
        # self.color = (1,1,1)
        # self.region = bpy.context.region
        # self.r3d = bpy.context.space_data.region_3d
        # self.clear_ui_mouse_pos()

    ###################################################
    # class variables

    # # get items for brick_type prop
    # def get_items(self, context):
    #     scn, cm, _ = get_active_context_info()
    #     legal_bs = bpy.props.bricker_legal_brick_sizes
    #     items = [iter_from_type(typ) for typ in legal_bs[cm.zstep]]
    #     if cm.zstep == 1:
    #         items += [iter_from_type(typ) for typ in legal_bs[3]]
    #     # items = get_available_types(by="ACTIVE", include_sizes="ALL")
    #     return items
    #
    # # define props for popup
    # brick_type = bpy.props.EnumProperty(
    #     name="Brick Type",
    #     description="Type of brick to draw adjacent to current brick",
    #     items=get_items,
    #     default=None)

    # define props for popup
    mode = bpy.props.EnumProperty(
        items=[("DRAW", "DRAW", ""),
               ("PAINT", "PAINT", ""),
               ("MERGE/SPLIT", "MERGE/SPLIT", ""),
               ],
    )
