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
import os
import json

# Blender imports
import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper#, path_reference_mode
from bpy.props import *

# Module imports
from ..functions import *
from ..functions.property_callbacks import get_build_order_items


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
            if self.build_order == "LAYERS":
                self.write_ldraw_file_layers(context)
            elif self.build_order == "CONN_COMPS":
                self.write_ldraw_file_conn_comps(context)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    #############################################
    # ExportHelper properties

    filename_ext = ".ldr"
    filter_glob = StringProperty(
        default="*.ldr",
        options={"HIDDEN"},
    )
    # path_mode = path_reference_mode
    check_extension = True
    model_author = StringProperty(
        name="Author",
        description="Author name for the file's metadata",
        default="",
    )
    build_order = EnumProperty(
        name="Build Order",
        description="Build order for the model steps",
        # options={"HIDDEN"},
        items=get_build_order_items,
    )

    ################################################
    # initialization method

    def __init__(self):
        # get matrix for rotation of brick
        self.matrices = [
            " 0 0 -1 0 1 0  1 0  0",
            " 1 0  0 0 1 0  0 0  1",
            " 0 0  1 0 1 0 -1 0  0",
            "-1 0  0 0 1 0  0 0 -1"
        ]
        # get other vars
        self.legal_bricks = get_legal_bricks()
        self.abs_mat_properties = bpy.props.abs_mat_properties if hasattr(bpy.props, "abs_mat_properties") else None
        # initialize vars
        scn, cm, _ = get_active_context_info()
        self.trans_weight = cm.transparent_weight
        self.material_type = cm.material_type
        self.custom_mat = cm.custom_mat
        self.random_mat_seed = cm.random_mat_seed
        self.brick_height = cm.brick_height
        self.offset_brick_layers = cm.offset_brick_layers
        self.gap = cm.gap
        self.zstep = get_zstep(cm)
        self.brick_materials_installed = brick_materials_installed()

    #############################################
    # class variables

    # NONE!

    #############################################
    # class methods

    @timed_call()
    def write_ldraw_file_conn_comps(self, context):
        """ create and write Ldraw file """
        # open file for read and write
        self.filelines = list()
        self.submodel_count = 1
        # initialize vars
        scn, cm, n = get_active_context_info(context)
        blendfile_name = bpy.path.basename(context.blend_data.filepath)
        submodel_start_lines = dict()
        # iterate through models (if not animated, just executes once)
        for frame in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame) if cm.animated else [-1]:
            # write META commands
            self.filelines.append(f"0 FILE {blendfile_name}\n")
            self.filelines.append(f"0 {n}\n")
            self.filelines.append(f"0 Name: {n}\n")
            self.filelines.append("0 Unofficial model\n")
            self.filelines.append(f"0 Author: {self.model_author}\n")
            self.filelines.append("0 CustomBrick\n")
            self.filelines.append("0 NOFILE\n")
            bricksdict = get_bricksdict(cm, d_type="ANIM" if cm.animated else "MODEL", cur_frame=frame)
            if bricksdict is None:
                self.report({"ERROR"}, "The model's data is not cached – please update the model")
                return
            # get small offset for model to get close to Ldraw units
            offset = vec_conv(bricksdict[list(bricksdict.keys())[0]]["co"], int)
            offset.x = offset.x % 10
            offset.y = offset.z % 8
            offset.z = offset.y % 10
            # get dictionary of keys based on z value
            p_keys_dict = get_keys_dict(bricksdict, parents_only=True)
            starting_keys = dict()
            for z in p_keys_dict.keys():
                starting_keys[z] = set()
            # get sorted keys for random merging
            # initialize vars
            sorted_z_vals = sorted(p_keys_dict.keys())
            lowest_z_val = sorted_z_vals[0]
            layer_num = 1
            # iterate through z locations in bricksdict (bottom to top)
            for z in sorted_z_vals:
                # skip 2 out of every 3 layers, intentionally out of sync with brick_layer offset
                if (z + self.offset_brick_layers) % 3 != 2:
                    continue
                print(z)
                # reset starting_keys for all levels
                for z2 in p_keys_dict.keys():
                    starting_keys[z2] = set()
                # if this is the top z value, add bricks in one step
                if z == sorted_z_vals[-1]:
                    # start a submodel
                    submodel_name = f"Submodel {self.submodel_count}"
                    self.start_submodel(submodel_start_lines, submodel_name)
                    # add all bricks on this top layer
                    starting_keys[z] = p_keys_dict[z].copy()
                    self.add_build_step(bricksdict, p_keys_dict, starting_keys[z], cm, offset)
                    # end submodel
                    self.end_submodel(submodel_start_lines, submodel_name)
                # go up and down iteratively to find connected bricks
                else:
                    # start looking for connected bricks starting on active layer that are a single layer tall, moving up/down/up/down/etc
                    starter_keys_to_skip = set()
                    while True:
                        # start a submodel
                        submodel_name = f"Submodel {self.submodel_count}"
                        self.start_submodel(submodel_start_lines, submodel_name)
                        # choose a new brick on the active layer
                        valid_p_keys = (k for k in p_keys_dict[z] if bricksdict[k]["size"][2] // self.zstep < 3 and k not in starter_keys_to_skip)
                        key = next(valid_p_keys, None)
                        if key is None:
                            break
                        # start with all parent keys at and neighboring current brick
                        iters = 1  # reduces frustration in juggling many disconnected bricks for first step
                        starting_keys[z] = self.get_bricks_neighbored_by_above_connection(bricksdict, key, iters=1, min_studs=2)
                        starting_keys[z].intersection_update(valid_p_keys)
                        starting_keys[z].add(key)
                        # # if low enough on model, may want to skip this starting key
                        # if len(sorted_z_vals) > 3 and z < sorted_z_vals[-6]:
                        # accumulate keys connected below starter keys
                        last_keys = starting_keys[z]
                        for i in range(3):
                            lowest_conn_keys = set()
                            for k0 in last_keys:
                                lowest_conn_keys |= get_connected_keys(bricksdict, k0, self.zstep, check_above=False)
                            last_keys = lowest_conn_keys
                        # skip this starter key if no connected keys below
                        if len(lowest_conn_keys) == 0:
                            starter_keys_to_skip.add(key)
                            continue
                        # reset starting keys for 2 layers above active layer
                        starting_keys[z + 1] = set()
                        starting_keys[z + 2] = set()
                        # add first step with the starting keys
                        self.add_build_step(bricksdict, p_keys_dict, starting_keys[z], cm, offset)
                        while True:
                            # move up to bricks connected to it
                            new_bricks = self.iterate_connections(bricksdict, z, starting_keys, p_keys_dict, cm, offset, direction="UP")
                            # if we can keep going up, do so one more time
                            if z + 2 <= sorted_z_vals[-1]:
                                # move up to bricks connected to those
                                new_bricks |= self.iterate_connections(bricksdict, z + 1, starting_keys, p_keys_dict, cm, offset, direction="UP")
                                # move down to bricks connected to those
                                new_bricks |= self.iterate_connections(bricksdict, z + 2, starting_keys, p_keys_dict, cm, offset, direction="DOWN")
                            # move down to bricks connected to those
                            new_bricks |= self.iterate_connections(bricksdict, z + 1, starting_keys, p_keys_dict, cm, offset, direction="DOWN")
                            # break loop if no new bricks found
                            if len(new_bricks) == 0:
                                break
                        # add bricks above the top layer that are not connected to anything else but these below
                        if z + 3 in p_keys_dict.keys():
                            j = z + 2
                            while True:
                                isolated_bricks_above = self.get_isolated_keys(bricksdict, starting_keys[j], p_keys_dict, direction="UP")
                                if not isolated_bricks_above:
                                    break
                                self.add_build_step(bricksdict, p_keys_dict, isolated_bricks_above, cm, offset)
                                starting_keys[j + 1] = isolated_bricks_above
                                j += 1
                        # get any unconnected bricks below these
                        self.add_steps_for_all_connected_below(bricksdict, starting_keys, z, p_keys_dict, cm, offset)
                        # end submodel
                        submodel_created = self.end_submodel(submodel_start_lines, submodel_name)
                        if submodel_created:
                            self.submodel_count += 1
            # select bricks not exported
            if cm.last_split_model:
                deselect_all()
                for z in sorted_z_vals:
                    if len(p_keys_dict[z]) > 0:
                        print(z, p_keys_dict[z])
                    for k in p_keys_dict[z]:
                        select(bpy.data.objects[bricksdict[k]["name"]])
            # close the file
            self.file = open(self.filepath, "w")
            self.file.writelines(self.filelines)
            self.file.close()
            self.report_export_status(cm, bricksdict)

    def write_ldraw_file_layers(self, context):
        """ create and write Ldraw file """
        # open file for read and write
        self.filelines = list()
        # initialize vars
        scn, cm, n = get_active_context_info(context)
        blendfile_name = bpy.path.basename(context.blend_data.filepath)
        submodel_start_lines = dict()
        # iterate through models (if not animated, just executes once)
        for frame in range(cm.last_start_frame, cm.last_stop_frame + 1, cm.last_step_frame) if cm.animated else [-1]:
            path = self.filepath
            f = open(path, "w")
            # write META commands
            self.filelines.append(f"0 FILE {blendfile_name}\n")
            self.filelines.append(f"0 {n}\n")
            self.filelines.append(f"0 Name: {n}\n")
            self.filelines.append("0 Unofficial model\n")
            self.filelines.append(f"0 Author: {self.model_author}\n")
            self.filelines.append("0 CustomBrick\n")
            self.filelines.append("0 NOFILE\n")
            bricksdict = get_bricksdict(cm, d_type="ANIM" if cm.animated else "MODEL", cur_frame=frame)
            if bricksdict is None:
                self.report({"ERROR"}, "The model's data is not cached – please update the model")
                return
            # get small offset for model to get close to Ldraw units
            offset = vec_conv(bricksdict[list(bricksdict.keys())[0]]["co"], int)
            offset.x = offset.x % 10
            offset.y = offset.z % 8
            offset.z = offset.y % 10
            # get dictionary of keys based on z value
            p_keys_dict = get_keys_dict(bricksdict, parents_only=True)
            # initialize vars
            sorted_z_vals = sorted(p_keys_dict.keys())
            # iterate through layers and add submodel + single step
            for i, z in enumerate(sorted_z_vals):
                self.start_submodel(submodel_start_lines,  f"Layer {i + 1}")
                self.add_build_step(bricksdict, p_keys_dict, p_keys_dict[z], cm, offset, run_diff_update=False)
                self.end_submodel(submodel_start_lines,  f"Layer {i + 1}")
            # end the single submodel
            # close the file
            self.file = open(self.filepath, "w")
            self.file.writelines(self.filelines)
            self.file.close()
            self.report_export_status(cm, bricksdict)

    def report_export_status(self, cm, bricksdict):
        # report the status of the export
        if not cm.last_legal_bricks_only:
            self.report({"WARNING"}, "Model may contain non-standard brick sizes. Enable 'Brick Types > Legal Bricks Only' to make bricks LDraw-compatible.")
        elif self.abs_mat_properties is None and self.brick_materials_installed:
            self.report({"WARNING"}, "Materials may not have transferred successfully – please update to the latest version of 'ABS Plastic Materials'")
        else:
            self.report({"INFO"}, f"Ldraw file saved to '{self.filepath}'")
            # print num bricks exported
            initial_idx = self.filelines.index("0 NOFILE\n")  # get first end of file line
            num_bricks_exported = len(tuple(val for val in self.filelines[initial_idx:] if val.startswith("1")))
            total_bricks = len(get_parent_keys(bricksdict))
            print()
            print(f"{num_bricks_exported} / {total_bricks} bricks exported")
            # print num submodels exported
            num_submodels_exported = len(tuple(val for val in self.filelines if val.startswith("0 FILE"))) - 1
            print(f"{num_submodels_exported} submodels exported")
            # print num sub-steps exported
            num_steps_exported = len(tuple(val for val in self.filelines if val.startswith("0 ROTSTEP")))
            print(f"{num_steps_exported} steps exported")

    def iterate_connections(self, bricksdict, z, starting_keys, p_keys_dict, cm, offset, direction, append_by_lowest_z=False):
        conn_keys = set()
        # get keys to move up/down from
        cur_starting_keys = starting_keys[z]
        # go up or down to connected keys
        for k0 in cur_starting_keys:
            conn_keys |= get_connected_keys(bricksdict, k0, self.zstep, check_below=direction == "DOWN", check_above=direction == "UP")
            # if going up, remove bricks above taller than 3 layers that have unchosen bricks below them
            if direction == "UP" and bricksdict[k0]["size"][2] // self.zstep >= 3:
                for k1 in conn_keys.copy():
                    if not self.only_chosen_bricks(bricksdict, k1, p_keys_dict, direction="DOWN"):
                        conn_keys.remove(k1)
        # get only keys that haven't already been chosen
        conn_keys = self.get_unchosen(bricksdict, conn_keys, p_keys_dict)
        # if unchosen connections were found, update relative data structs
        if conn_keys:
            # add build step
            self.add_build_step(bricksdict, p_keys_dict, conn_keys, cm, offset, direction=direction)
            # add keys to starting_keys
            if append_by_lowest_z:
                z_vals = self.add_based_on_lowest_z(bricksdict, conn_keys, starting_keys)
            else:
                next_z = (z + 1) if direction == "UP" else (z - 1)
                starting_keys[next_z] |= conn_keys
        return conn_keys

    def add_based_on_lowest_z(self, bricksdict, keys, starting_keys):
        """add passed keys to the list of starting_keys according to their z level"""
        z_vals = set()
        for k2 in keys:
            cur_z = get_dict_loc(bricksdict, k2)[2]
            z_vals.add(cur_z)
            starting_keys[cur_z].add(k2)
        return z_vals

    def get_unchosen(self, bricksdict, conn_keys, p_keys_dict):
        # get keys from various connected z levels that were already chosen
        z_vals = [get_dict_loc(bricksdict, k1)[2] for k1 in conn_keys]
        unchosen_keys = set()
        for z1 in z_vals:
            unchosen_keys |= p_keys_dict[z1]
        # intersect with unchosen keys
        conn_keys.intersection_update(unchosen_keys)
        return conn_keys

    def add_steps_for_all_connected_below(self, bricksdict, starting_keys, z0, p_keys_dict, cm, offset):
        # # reset starting_keys for all levels
        # for z in p_keys_dict.keys():
        #     if z == z0:
        #         continue
        #     starting_keys[z] = set()
        # iterate downwards from starting keys
        while z0 - 1 in p_keys_dict.keys():  # and p_keys_dict[z0 - 1]:
            # skip this layer if no starting keys here
            if not starting_keys[z0]:
                z0 -= 1
                continue
            # add bricks below the z0 layer
            self.iterate_connections(bricksdict, z0, starting_keys, p_keys_dict, cm, offset, direction="DOWN", append_by_lowest_z=True)
            z_vals = {z0 - 1}  # all down connections from above iter fall into this z val

            # get keys above those that are isolated above
            for i in range(2):  # NOTE: bricks could be missed here, since we only go up twice but there could be unconnected bricks stacked up another layer higher than that (just holding off on switching to 3 for a use case)
                isolated_keys_above = self.get_isolated_keys(bricksdict, starting_keys[z0 - 1 + i], p_keys_dict, direction="UP", ensure_unchosen=True)
                # check if keys above not connected above found
                if isolated_keys_above:
                    # add the keys found to their appropriate starting_keys level
                    z_vals |= self.add_based_on_lowest_z(bricksdict, isolated_keys_above, starting_keys)
                    # add build step for the keys found
                    self.add_build_step(bricksdict, p_keys_dict, isolated_keys_above, cm, offset, direction="UP")

            # # get keys above those that aren't connected above
            # conn_keys = set()
            # for k0 in starting_keys[z0 - 1]:
            #     conn_keys |= get_connected_keys(bricksdict, k0, self.zstep, check_below=False)
            #     conn_keys = self.get_unchosen(bricksdict, conn_keys, p_keys_dict)
            # keys_above_last_iteration_to_build = set()
            # for k1 in conn_keys:
            #     conn_keys_2 = get_connected_keys(bricksdict, k1, self.zstep, check_below=False)
            #     conn_keys_2 = self.get_unchosen(bricksdict, conn_keys_2, p_keys_dict)
            #     if not conn_keys_2:
            #         keys_above_last_iteration_to_build.add(k1)
            # # check if keys above not connected above found
            # if keys_above_last_iteration_to_build:
            #     # add build step for the keys found
            #     z_vals.add(z0)
            #     starting_keys[z0 - 1] |= keys_above_last_iteration_to_build
            #     self.add_build_step(bricksdict, p_keys_dict, keys_above_last_iteration_to_build, cm, offset, direction="UP")
            #     # NOTE: bricks could be missed here, since we don't check for unconnected bricks connected above these

            # next iter should be maximum among bricks found (if no isolated_keys_above found, goes down 1 layer)
            z0 = max(z_vals)

    def get_bricks_neighbored_by_above_connection(self, bricksdict, key, iters=3, min_studs=1):
        # initialize neighboring bricks set
        neighboring_bricks = set()
        # get keys above passed brick
        conn_keys = get_connected_keys(bricksdict, key, self.zstep, check_below=False)
        for i in range(iters):
            # no need to iterate if no keys above
            if not conn_keys:
                return neighboring_bricks
            # # get keys above those
            # conn_keys1 = set()
            # for k0 in conn_keys:
            #     conn_keys1 |= get_connected_keys(bricksdict, k0, self.zstep, check_below=False)
            # # get keys below those
            # for k0 in conn_keys1:
            #     conn_keys |= get_connected_keys(bricksdict, k0, self.zstep, check_above=False)
            # get keys below those
            for k0 in conn_keys:
                neighboring_bricks |= get_connected_keys(bricksdict, k0, self.zstep, check_above=False)
            # get keys above those
            conn_keys0 = set()
            for k0 in neighboring_bricks:
                conn_keys0 |= get_connected_keys(bricksdict, k0, self.zstep, check_below=False)
            # set conn_keys to new keys above
            conn_keys = conn_keys0.difference(conn_keys)
        neighboring_bricks = set(k for k in neighboring_bricks if self.num_studs(bricksdict, k) >= min_studs)
        return neighboring_bricks

    def num_studs(self, bricksdict, k):
        return bricksdict[k]["size"][0] * bricksdict[k]["size"][1]

    def recurse_connected(self, bricksdict, keys, p_keys_dict, cm, offset, direction="UP"):
        conn_keys = set()
        for k0 in keys:
            conn_keys |= get_connected_keys(bricksdict, k0, self.zstep, check_below=direction == "DOWN", check_above=direction == "UP")
        conn_keys = self.get_unchosen(bricksdict, conn_keys, p_keys_dict)
        # none connected this direction
        if not conn_keys:
            return
        # add build step for the new connected bricks
        self.add_build_step(bricksdict, p_keys_dict, conn_keys, cm, offset, direction="UP")
        # move up
        self.recurse_connected(bricksdict, conn_keys, p_keys_dict, cm, offset, direction="UP")
        # move down
        self.recurse_connected(bricksdict, conn_keys, p_keys_dict, cm, offset, direction="DOWN")

    def get_isolated_keys(self, bricksdict, cur_starting_keys, p_keys_dict, direction, ensure_unchosen=False):
        conn_keys = set()
        for k0 in cur_starting_keys:
            conn_keys |= get_connected_keys(bricksdict, k0, self.zstep, check_below=direction == "DOWN", check_above=direction == "UP")
        isolated_keys = set()
        for k1 in conn_keys:
            other_direction = "UP" if direction == "DOWN" else "DOWN"
            if self.only_chosen_bricks(bricksdict, k1, p_keys_dict, direction=other_direction):
                isolated_keys.add(k1)
        if ensure_unchosen:
            isolated_keys = self.get_unchosen(bricksdict, isolated_keys, p_keys_dict)
        return isolated_keys

    def only_chosen_bricks(self, bricksdict, key, p_keys_dict, direction):
        """ verifies that all bricks below brick have already been chosen (returns true if no bricks below) """
        conn_keys = get_connected_keys(bricksdict, key, self.zstep, check_below=direction == "DOWN", check_above=direction == "UP")
        if not conn_keys:
            return True
        unchosen_keys = self.get_unchosen(bricksdict, conn_keys, p_keys_dict)
        return len(unchosen_keys) == 0

    def add_build_step(self, bricksdict, p_keys_dict, keys, cm, offset, run_diff_update=True, direction="UP"):
        # remove keys in this step from p_keys_dict
        if run_diff_update:
            z_vals = [get_dict_loc(bricksdict, k1)[2] for k1 in keys]
            for z in z_vals:
                p_keys_dict[z].difference_update(keys)
        # iterate through keys
        for key in keys:
            brick_d = bricksdict[key]
            # # skip bricks that aren't displayed
            # if not brick_d["draw"] or brick_d["parent"] != "self":
            #     continue
            # initialize brick size and typ
            size = brick_d["size"]
            typ = brick_d["type"]
            idx = self.get_brick_idx(brick_d, size, typ)
            matrix = self.matrices[idx]
            # get coordinate for brick in Ldraw units
            co = self.blend_to_ldraw_units(bricksdict, self.zstep, key, idx)
            # get color code of brick
            abs_mat_names = get_abs_mat_names()
            mat = get_material(bricksdict, key, size, self.zstep, self.material_type, self.custom_mat, self.random_mat_seed, brick_mats=get_brick_mats(cm))
            mat_name = "" if mat is None else mat.name
            rgba = brick_d["rgba"]
            if mat_name in abs_mat_names and self.abs_mat_properties is not None:
                abs_mat_name = mat_name
            elif rgba not in (None, "") and self.material_type != "NONE":
                abs_mat_name = find_nearest_color_name(rgba, trans_weight=self.trans_weight)
            elif bpy.data.materials.get(mat_name) is not None:
                rgba = get_material_color(mat_name)
                abs_mat_name = find_nearest_color_name(rgba, trans_weight=self.trans_weight)
            elif not mat_name and cm.internal_mat and cm.internal_mat.name in abs_mat_names:
                abs_mat_name = cm.internal_mat.name
            else:
                abs_mat_name = ""
            color = self.abs_mat_properties[abs_mat_name]["LDR Code"] if abs_mat_name else 0
            # get part number and ldraw file name for brick
            part = get_part(self.legal_bricks, size, typ)["pt2" if typ == "SLOPE" and size[:2] in ([4, 2], [2, 4], [3, 2], [2, 3]) and brick_d["rotated"] else "pt"]
            brick_file = "%(part)s.dat" % locals()
            # offset the coordinate and round to ensure appropriate Ldraw location
            co += offset
            co = Vector((round_nearest(co.x, 10), round_nearest(co.y, 8), round_nearest(co.z, 10)))
            # write line to file for brick
            self.filelines.append("1 {color} {x} {y} {z} {matrix} {brick_file}\n".format(color=color, x=co.x, y=co.y, z=co.z, matrix=matrix, brick_file=brick_file))
        # add step info to end
        if direction == "UP":
            self.filelines.append("0 ROTSTEP 40 45 0 ABS\n")
        else:
            self.filelines.append("0 ROTSTEP -40 45 0 ABS\n")

    def get_brick_idx(self, brick_d, size, typ):
        if typ == "SLOPE":
            idx = 0
            idx -= 2 if brick_d["flipped"] else 0
            idx -= 1 if brick_d["rotated"] else 0
            idx += 2 if (size[:2] in ([1, 2], [1, 3], [1, 4], [2, 3]) and not brick_d["rotated"]) or size[:2] == [2, 4] else 0
        else:
            idx = 1
        idx += 1 if size[1] > size[0] else 0
        return idx

    def start_submodel(self, submodel_start_lines, submodel_name):
        submodel_start_lines[submodel_name] = len(self.filelines)

    def end_submodel(self, submodel_start_lines, submodel_name):
        # if no bricks were added to this submodel, do nothing
        if submodel_start_lines[submodel_name] == len(self.filelines):
            return False
        # add submodule information to beginning of file
        initial_idx = self.filelines.index("0 NOFILE\n")  # get first end of file line
        init_string_lst = [
            "1 {color} {x} {y} {z} {matrix} {submodel_name}\n".format(color=0, x=0, y=0, z=0, matrix=self.matrices[0], submodel_name=submodel_name.lower()),
            "0 STEP\n",
        ]
        self.filelines[initial_idx:initial_idx] = init_string_lst
        # update submodel start lines that occur after these new lines
        for s_name in submodel_start_lines:
            if submodel_start_lines[s_name] > initial_idx:
                submodel_start_lines[s_name] += len(init_string_lst)
        # get submodule start line
        index = submodel_start_lines.pop(submodel_name)
        # count number of bricks since submodel start line
        num_bricks = 0
        for line in self.filelines[index:]:
            if line.startswith("1"):
                num_bricks += 1
        # build submodel start string
        new_string_lst = [
            f"0 FILE {submodel_name}\n",
            f"0 {submodel_name}\n",
            f"0 Name:  {submodel_name}\n",
            "0 Author:\n",
            "0 CustomBrick\n",
            f"0 NumOfBricks:  {num_bricks}\n",
        ]
        # insert submodel start string at submodel start line
        self.filelines[index:index] = new_string_lst
        # update submodel start lines that occur after these new lines
        for s_name in submodel_start_lines:
            if submodel_start_lines[s_name] > index:
                submodel_start_lines[s_name] += len(new_string_lst)
        # write end of submodel
        self.filelines.append("0 NOFILE\n")
        return True

    def blend_to_ldraw_units(self, bricksdict, zstep, key, idx):
        """ convert location of brick from blender units to ldraw units """
        brick_d = bricksdict[key]
        size = brick_d["size"]
        loc = get_brick_center(bricksdict, key, zstep)
        dimensions = get_brick_dimensions(self.brick_height, zstep, self.gap)
        h = 8 * zstep
        loc.x = loc.x * (20 / (dimensions["width"] + dimensions["gap"]))
        loc.y = loc.y * (20 / (dimensions["width"] + dimensions["gap"]))
        if brick_d["type"] == "SLOPE":
            if idx == 0:
                loc.x -= ((size[0] - 1) * 20) / 2
            elif idx in (1, -3):
                loc.y += ((size[1] - 1) * 20) / 2
            elif idx in (2, -2):
                loc.x += ((size[0] - 1) * 20) / 2
            elif idx in (3, -1):
                loc.y -= ((size[1] - 1) * 20) / 2
        loc.z = loc.z * (h / (dimensions["height"] + dimensions["gap"]))
        if brick_d["type"] == "SLOPE" and size == [1, 1, 3]:
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
