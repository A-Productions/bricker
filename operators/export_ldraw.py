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
import os
import json

# Blender imports
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper#, path_reference_mode

# Module imports
from ..functions import *


class BRICKER_OT_export_ldraw(Operator, ExportHelper):
    """Export active brick model to ldraw file"""
    bl_idname = "bricker.export_ldraw"
    bl_label = "Export LDR"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):
        try:
            self.write_ldraw_file()
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    #############################################
    # ExportHelper properties

    filename_ext = ".ldr"
    filter_glob = bpy.props.StringProperty(
            default="*.ldr",
            options={"HIDDEN"},
            )
    # path_mode = path_reference_mode
    check_extension = True

    #############################################
    # class variables

    # NONE!

    #############################################
    # class methods

    def write_ldraw_file(self):
        """ create and write Ldraw file """
        scn, cm, n = get_active_context_info()
        # initialize vars
        legal_bricks = get_legal_bricks()
        abs_mat_properties = bpy.props.abs_mat_properties if hasattr(bpy.props, "abs_mat_properties") else None
        trans_weight = cm.transparent_weight
        material_type = cm.material_type
        # get matrix for rotation of brick
        matrices = [" 0 0 -1 0 1 0  1 0  0",
                    " 1 0  0 0 1 0  0 0  1",
                    " 0 0  1 0 1 0 -1 0  0",
                    "-1 0  0 0 1 0  0 0 -1"]
        for frame in range(cm.start_frame, cm.stop_frame + 1) if cm.animated else [-1]:
            path = self.filepath
            f = open(path, "w")
            # write META commands
            f.write("0 %(n)s\n" % locals())
            f.write("0 Name:\n" % locals())
            f.write("0 Unofficial model\n" % locals())
            # f.write("0 Author: Unknown\n" % locals())
            bricksdict = get_bricksdict(cm, d_type="ANIM" if cm.animated else "MODEL", cur_frame=frame)
            # get small offset for model to get close to Ldraw units
            offset = vec_conv(bricksdict[list(bricksdict.keys())[0]]["co"], int)
            offset.x = offset.x % 10
            offset.y = offset.z % 8
            offset.z = offset.y % 10
            # get dictionary of keys based on z value
            keys_dict, sorted_keys = get_keys_dict(bricksdict)
            # get sorted keys for random merging
            seed_keys = sorted_keys if material_type == "RANDOM" else None
            # iterate through z locations in bricksdict (bottom to top)
            for z in sorted(keys_dict.keys()):
                for key in keys_dict[z]:
                    # skip bricks that aren't displayed
                    if not bricksdict[key]["draw"] or bricksdict[key]["parent"] != "self":
                        continue
                    # initialize brick size and typ
                    size = bricksdict[key]["size"]
                    typ = bricksdict[key]["type"]
                    if typ == "SLOPE":
                        idx = 0
                        idx -= 2 if bricksdict[key]["flipped"] else 0
                        idx -= 1 if bricksdict[key]["rotated"] else 0
                        idx += 2 if (size[:2] in ([1, 2], [1, 3], [1, 4], [2, 3]) and not bricksdict[key]["rotated"]) or size[:2] == [2, 4] else 0
                    else:
                        idx = 1
                    idx += 1 if size[1] > size[0] else 0
                    matrix = matrices[idx]
                    # get coordinate for brick in Ldraw units
                    co = self.blend_to_ldraw_units(cm, bricksdict, cm.zstep, key, idx)
                    # get color code of brick
                    mat = get_material(bricksdict, key, size, cm.zstep, material_type, cm.custom_mat.name if cm.custom_mat is not None else "z", cm.random_mat_seed, cm.material_is_dirty or cm.matrix_is_dirty or cm.build_is_dirty, seed_keys, brick_mats=get_brick_mats(cm))
                    mat_name = "" if mat is None else mat.name
                    rgba = bricksdict[key]["rgba"]
                    color = 0
                    if mat_name in get_abs_mat_names() and abs_mat_properties is not None:
                        color = abs_mat_properties[mat_name]["LDR Code"]
                    elif rgba not in (None, "") and material_type != "NONE":
                        mat_name = find_nearest_brick_color_name(rgba, trans_weight)
                    elif bpy.data.materials.get(mat_name) is not None:
                        rgba = get_material_color(mat_name)
                    # get part number and ldraw file name for brick
                    parts = legal_bricks[size[2]][typ]
                    for j,part in enumerate(parts):
                        if parts[j]["s"] in (size[:2], size[1::-1]):
                            part = parts[j]["pt2" if typ == "SLOPE" and size[:2] in ([4, 2], [2, 4], [3, 2], [2, 3]) and bricksdict[key]["rotated"] else "pt"]
                            break
                    brick_file = "%(part)s.dat" % locals()
                    # offset the coordinate and round to ensure appropriate Ldraw location
                    co += offset
                    co = Vector((round_nearest(co.x, 10), round_nearest(co.y, 8), round_nearest(co.z, 10)))
                    # write line to file for brick
                    f.write("1 {color} {x} {y} {z} {matrix} {brick_file}\n".format(color=color, x=co.x, y=co.y, z=co.z, matrix=matrix, brick_file=brick_file))
                f.write("0 STEP\n")
            f.close()
            if not cm.last_legal_bricks_only:
                self.report({"WARNING"}, "Model may contain non-standard brick sizes. Enable 'Brick Types > Legal Bricks Only' to make bricks LDraw-compatible.")
            elif abs_mat_properties is None and brick_materials_installed:
                self.report({"WARNING"}, "Materials may not have transferred successfully – please update to the latest version of 'ABS Plastic Materials'")
            else:
                self.report({"INFO"}, "Ldraw file saved to '%(path)s'" % locals())

    def blend_to_ldraw_units(self, cm, bricksdict, zstep, key, idx):
        """ convert location of brick from blender units to ldraw units """
        size = bricksdict[key]["size"]
        loc = get_brick_center(bricksdict, key, zstep)
        dimensions = get_brick_dimensions(cm.brick_height, zstep, cm.gap)
        h = 8 * zstep
        loc.x = loc.x * (20 / (dimensions["width"] + dimensions["gap"]))
        loc.y = loc.y * (20 / (dimensions["width"] + dimensions["gap"]))
        if bricksdict[key]["type"] == "SLOPE":
            if idx == 0:
                loc.x -= ((size[0] - 1) * 20) / 2
            elif idx in (1, -3):
                loc.y += ((size[1] - 1) * 20) / 2
            elif idx in (2, -2):
                loc.x += ((size[0] - 1) * 20) / 2
            elif idx in (3, -1):
                loc.y -= ((size[1] - 1) * 20) / 2
        loc.z = loc.z * (h / (dimensions["height"] + dimensions["gap"]))
        if bricksdict[key]["type"] == "SLOPE" and size == [1, 1, 3]:
            loc.z -= size[2] * 8
        if zstep == 1 and size[2] == 3:
            loc.z += 8
        # convert to right-handed co-ordinate system where -Y is "up"
        loc = Vector((loc.x, -loc.z, loc.y))
        return loc

    def rgb_to_hex(self, rgb):
        """ convert RGB list to HEX string """
        def clamp(x):
            return int(max(0, min(x, 255)))
        r, g, b = rgb
        return "{0:02x}{1:02x}{2:02x}".format(clamp(r), clamp(g), clamp(b))

    #############################################
