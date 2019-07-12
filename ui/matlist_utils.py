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

# Addon imports
from ..functions import *


def add_material_to_list(self, context):
    scn, cm, n = get_active_context_info()
    typ = "RANDOM" if cm.material_type == "RANDOM" else "ABS"
    mat_obj = get_mat_obj(cm.id, typ=typ)
    num_mats = len(mat_obj.data.materials)
    mat = bpy.data.materials.get(cm.target_material)
    if mat is None:
        return
    elif mat.name in mat_obj.data.materials.keys():
        cm.target_material = "Already in list!"
    elif typ == "ABS" and mat.name not in get_abs_mat_names():
        cm.target_material = "Not ABS Plastic material"
    elif mat_obj is not None:
        mat_obj.data.materials.append(mat)
        cm.target_material = ""
    if num_mats < len(mat_obj.data.materials) and not cm.last_split_model:
        cm.material_is_dirty = True
