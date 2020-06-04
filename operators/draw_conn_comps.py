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
import time

# Blender imports
import bpy
props = bpy.props

# Module imports
from ..functions import *


class BRICKER_OT_draw_connected_components(bpy.types.Operator):
    """Delete brickified model (restores original source object)"""
    bl_idname = "bricker.draw_connected_components"
    bl_label = "Draw Connected Components"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if not cm.model_created or cm.animated:
            return False
        return True

    def execute(self, context):
        scn, cm, n = get_active_context_info(context)
        bricksdict = get_bricksdict(cm, d_type="ANIM" if cm.animated else "MODEL", cur_frame=scn.frame_current)
        if bricksdict is None:
            self.report({"ERROR"}, "The model's data is not cached – please update the model")
            return {"CANCELLED"}

        # get connected components & weak points
        parent_keys = get_parent_keys(bricksdict)
        conn_comps = get_connected_components(bricksdict, get_zstep(cm), parent_keys)
        weak_points, weak_point_neighbors = get_weak_articulation_points(bricksdict, conn_comps)

        # draw connected components
        print("drawing connected components...")
        draw_connected_components(bricksdict, cm, conn_comps, weak_points, name="Bricker_{n}_conn_comps".format(n=cm.source_obj.name))

        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        pass

    #############################################
    # class methods

    # NONE!

    #############################################
