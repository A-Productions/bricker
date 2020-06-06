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
import time

# Blender imports
import bpy
props = bpy.props

# Module imports
from ..functions import *


class BRICKER_OT_select_disconnected_components(bpy.types.Operator):
    """ Select all disconnected components """
    bl_idname = "bricker.select_disconnected"
    bl_label = "Select Disconnected Components"
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
        conn_comps, weak_points, weak_point_neighbors = get_connectivity_data(bricksdict, cm)

        # select disconnected components
        print("select disconnected components...")
        largest_conn_comp = max(len(cc) for cc in conn_comps)
        objs_to_select = []
        for cc in conn_comps:
            if len(cc) == largest_conn_comp:
                continue
            for k in cc:
                brick_obj = bpy.data.objects.get(bricksdict[k]["name"])
                objs_to_select.append(brick_obj)
        select(objs_to_select, only=True, active=True)

        self.report({"INFO"}, "Disconnected components selected!")
        return{"FINISHED"}

    ################################################
    # initialization method

    def __init__(self):
        pass

    #############################################
    # class methods

    # NONE!

    #############################################
