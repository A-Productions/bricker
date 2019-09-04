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
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d
from bpy.types import Operator, SpaceView3D, bpy_struct
from bpy.props import *

# Module imports
from .draw_adjacent import *
from ..brickify import *
from ...functions import *
from ...operators.overrides.delete_object import OBJECT_OT_delete_override


class BricksculptTools:

    #############################################

    def add_brick(self, cm, n, cur_key, cur_loc, obj_size):
        # get difference between intersection loc and object loc
        loc_diff = self.loc - transform_to_world(Vector(self.bricksdict[cur_key]["co"]), self.parent.matrix_world, self.junk_bme)
        loc_diff = transform_to_local(loc_diff, self.parent.matrix_world)
        next_loc = get_nearby_loc_from_vector(loc_diff, cur_loc, self.dimensions, cm.zstep, width_divisor=3.2 if self.brick_type in get_round_brick_types() else 2.05)
        if self.layer_solod is not None and next_loc[2] not in range(self.layer_solod, self.layer_solod + 3 // cm.zstep):
            return
        # draw brick at next_loc location
        next_key, adj_brick_d = BRICKER_OT_draw_adjacent.get_brick_d(self.bricksdict, next_loc)
        if not adj_brick_d or self.bricksdict[next_key]["val"] == 0:
            self.adj_locs = get_adj_locs(cm, self.bricksdict, cur_key, self.obj)
            # add brick at next_key location
            status = BRICKER_OT_draw_adjacent.toggle_brick(cm, n, self.bricksdict, self.adj_locs, [[False]], self.dimensions, next_loc, cur_key, cur_loc, obj_size, self.brick_type, 0, 0, self.keys_to_merge_on_commit, is_placeholder_brick=True)
            if not status["val"]:
                self.report({status["report_type"]}, status["msg"])
            self.added_bricks.append(self.bricksdict[next_key]["name"])
            self.keys_to_merge_on_release.append(next_key)
            self.all_updated_keys.append(cur_key)
            # draw created bricks
            draw_updated_bricks(cm, self.bricksdict, [next_key], action="adding new brick", select_created=False, temp_brick=True)

    def remove_brick(self, cm, n, event, cur_key, cur_loc, obj_size):
        shallow_delete = cur_key in self.keys_to_merge_on_release and self.mode == "DRAW"
        deep_delete = event.shift and self.mode == "DRAW" and self.obj.name not in self.added_bricks_from_delete
        if shallow_delete or deep_delete:
            # split bricks and update adjacent brick_ds
            brick_keys, cur_key = self.split_brick_and_get_nearest_1x1(cm, n, cur_key, cur_loc, obj_size)
            cur_loc = get_dict_loc(self.bricksdict, cur_key)
            keys_to_update, only_new_keys = OBJECT_OT_delete_override.update_adj_bricksdicts(self.bricksdict, cm.zstep, cur_key, cur_loc, [])
            if deep_delete:
                self.added_bricks_from_delete += [self.bricksdict[k]["name"] for k in only_new_keys]
            # reset bricksdict values
            self.bricksdict[cur_key]["draw"] = False
            self.bricksdict[cur_key]["val"] = 0
            self.bricksdict[cur_key]["parent"] = None
            self.bricksdict[cur_key]["created_from"] = None
            self.bricksdict[cur_key]["flipped"] = False
            self.bricksdict[cur_key]["rotated"] = False
            self.bricksdict[cur_key]["top_exposed"] = False
            self.bricksdict[cur_key]["bot_exposed"] = False
            brick = bpy.data.objects.get(self.bricksdict[cur_key]["name"])
            if brick is not None:
                delete(brick)
            tag_redraw_areas("VIEW_3D")
            # draw created bricks
            draw_updated_bricks(cm, self.bricksdict, uniquify(brick_keys + keys_to_update), action="updating surrounding bricks", select_created=False, temp_brick=True)
            self.keys_to_merge_on_commit += brick_keys + only_new_keys

    def change_material(self, cm, n, cur_key, cur_loc, obj_size):
        if max(obj_size[:2]) > 1 or obj_size[2] > cm.zstep:
            brick_keys, cur_key = self.split_brick_and_get_nearest_1x1(cm, n, cur_key, cur_loc, obj_size)
        else:
            brick_keys = [cur_key]
        self.bricksdict[cur_key]["mat_name"] = self.mat_name
        self.bricksdict[cur_key]["custom_mat_name"] = True
        self.added_bricks.append(self.bricksdict[cur_key]["name"])
        self.keys_to_merge_on_commit += brick_keys
        # draw created bricks
        draw_updated_bricks(cm, self.bricksdict, brick_keys, action="updating material", select_created=False, temp_brick=True)

    def split_brick(self, cm, event, cur_key, cur_loc, obj_size):
        brick = bpy.data.objects.get(self.bricksdict[cur_key]["name"])
        if (event.alt and max(self.bricksdict[cur_key]["size"][:2]) > 1) or (event.shift and self.bricksdict[cur_key]["size"][2] > 1):
            brick_keys = split_brick(self.bricksdict, cur_key, cm.zstep, cm.brick_type, loc=cur_loc, v=event.shift, h=event.alt)
            self.all_updated_keys += brick_keys
            # remove large brick
            brick = bpy.data.objects.get(self.bricksdict[cur_key]["name"])
            delete(brick)
            # draw split bricks
            draw_updated_bricks(cm, self.bricksdict, brick_keys, action="splitting bricks", select_created=True, temp_brick=True)
        else:
            select(brick)

    def merge_brick(self, cm, source_name, cur_key=None, cur_loc=None, obj_size=None, mode="DRAW", state="DRAG"):
        if state == "DRAG":
            # TODO: Light up bricks as they are selected to be merged
            self.parent_locs_to_merge_on_release.append(cur_loc)
            self.added_bricks.append(self.bricksdict[cur_key]["name"])
            select(self.obj)
        elif state == "RELEASE":
            # assemble keys_to_merge_on_release
            for pl in self.parent_locs_to_merge_on_release:
                brick_keys = get_keys_in_brick(self.bricksdict, self.bricksdict[pk]["size"], cm.zstep, loc=pl)
                self.keys_to_merge_on_release += brick_keys
            self.parent_locs_to_merge_on_release = []
            self.keys_to_merge_on_release = uniquify(self.keys_to_merge_on_release)
            # merge those keys
            if len(self.keys_to_merge_on_release) > 1:
                # delete outdated bricks
                for key in self.keys_to_merge_on_release:
                    brick_name = "Bricker_%(source_name)s__%(key)s" % locals()
                    delete(bpy.data.objects.get(brick_name))
                # split up bricks
                split_bricks(self.bricksdict, cm.zstep, keys=self.keys_to_merge_on_release)
                # merge bricks after they've been split
                merged_keys = BRICKER_OT_merge_bricks.merge_bricks(self.bricksdict, self.keys_to_merge_on_release, cm, any_height=True)
                self.all_updated_keys += merged_keys
                # draw merged bricks
                draw_updated_bricks(cm, self.bricksdict, merged_keys, action="merging bricks", select_created=False, temp_brick=True)
                # re-solo layer
                if self.layer_solod is not None:
                    zstep = cm.zstep
                    for key in merged_keys:
                        loc = get_dict_loc(self.bricksdict, key)
                        self.hide_if_on_layer(key, loc, self.layer_solod, zstep)
            else:
                deselect_all()
            # reset lists
            if mode == "MERGE/SPLIT":
                self.keys_to_merge_on_release = []
            self.added_bricks = []

    def solo_layer(self, cm, cur_key, cur_loc, obj_size):
        brick_keys = get_keys_in_brick(self.bricksdict, obj_size, cm.zstep, loc=cur_loc)
        assert type(brick_keys) is list
        cur_key = self.get_nearest_loc_to_cursor(brick_keys)
        curZ = get_dict_loc(self.bricksdict, cur_key)[2]
        zstep = cm.zstep
        for key in self.bricksdict.keys():
            if self.bricksdict[key]["parent"] != "self":
                continue
            loc = get_dict_loc(self.bricksdict, key)
            self.hide_if_on_layer(key, loc, curZ, zstep)
        return curZ

    def hide_if_on_layer(self, key, loc, curZ, zstep):
        if loc[2] > curZ or loc[2] + self.bricksdict[key]["size"][2] / zstep <= curZ:
            brick = bpy.data.objects.get(self.bricksdict[key]["name"])
            if brick is None:
                return
            hide(brick, render=False)
            self.hidden_bricks.append(brick)

    def unsolo_layer(self):
        [unhide(brick) for brick in self.hidden_bricks]
        self.hidden_bricks = []

    def split_brick_and_get_nearest_1x1(self, cm, n, cur_key, cur_loc, obj_size):
        brick_keys = split_brick(self.bricksdict, cur_key, cm.zstep, cm.brick_type, loc=cur_loc, v=True, h=True)
        brick = bpy.data.objects.get(self.bricksdict[cur_key]["name"])
        delete(brick)
        cur_key = self.get_nearest_loc_to_cursor(brick_keys)
        return brick_keys, cur_key

    def get_nearest_loc_to_cursor(self, keys):
        # get difference between intersection loc and object loc
        min_diff = None
        for k in keys:
            brick_loc = transform_to_world(Vector(self.bricksdict[k]["co"]), self.parent.matrix_world, self.junk_bme)
            loc_diff = abs(self.loc[0] - brick_loc[0]) + abs(self.loc[1] - brick_loc[1]) + abs(self.loc[2] - brick_loc[2])
            if min_diff is None or loc_diff < min_diff:
                min_diff = loc_diff
                cur_key = k
        return cur_key

    def commit_changes(self):
        scn, cm, _ = get_active_context_info()
        # deselect any objects left selected, and show all objects
        deselect_all()
        self.unsolo_layer()
        # attempt to merge bricks queued for merge on commit
        self.keys_to_merge_on_commit = uniquify(self.keys_to_merge_on_commit)
        if mergable_brick_type(self.brick_type) and len(self.keys_to_merge_on_commit) > 1:
            # split up bricks
            split_bricks(self.bricksdict, cm.zstep, keys=self.keys_to_merge_on_commit)
            # merge split bricks
            merged_keys = BRICKER_OT_merge_bricks.merge_bricks(self.bricksdict, self.keys_to_merge_on_commit, cm, target_type="BRICK" if cm.brick_type == "BRICKS AND PLATES" else self.brick_type, any_height=cm.brick_type == "BRICKS AND PLATES")
        else:
            merged_keys = self.keys_to_merge_on_commit
        # remove 1x1 bricks merged into another brick
        for k in self.keys_to_merge_on_commit:
            delete(None if k in merged_keys else bpy.data.objects.get(self.bricksdict[k]["name"]))
        # set exposure of created/updated bricks
        keys_to_update = uniquify(merged_keys + self.all_updated_keys)
        for k in keys_to_update:
            set_all_brick_exposures(self.bricksdict, cm.zstep, k)
        # draw updated bricks
        draw_updated_bricks(cm, self.bricksdict, keys_to_update, action="committing changes", select_created=False)

    #############################################
