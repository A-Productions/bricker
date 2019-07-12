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

# system imports
import time
import bmesh
import os
import math

# Blender imports
import bpy
from bpy.types import Object
from mathutils import Matrix, Vector
props = bpy.props

# Addon imports
from ..functions import *


class BRICKER_OT_bevel(bpy.types.Operator):
    """Bevel brick edges and corners for added realism"""
    bl_idname = "bricker.bevel"
    bl_label = "Bevel Bricks"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        try:
            scn, cm, n = get_active_context_info()
        except IndexError:
            return False
        if cm.model_created or cm.animated:
            return True
        return False

    def execute(self, context):
        try:
            cm = get_active_context_info()[1]
            # set bevel action to add or remove
            try:
                test_brick = get_bricks()[0]
                test_brick.modifiers[test_brick.name + "_bvl"]
                action = "REMOVE" if cm.bevel_added else "ADD"
            except:
                action = "ADD"
            # get bricks to bevel
            bricks = get_bricks()
            # create or remove bevel
            BRICKER_OT_bevel.run_bevel_action(bricks, cm, action, setBevel=True)
        except:
            bricker_handle_exception()
        return{"FINISHED"}

    #############################################
    # class methods

    @staticmethod
    def run_bevel_action(bricks, cm, action="ADD", setBevel=False):
        """ chooses whether to add or remove bevel """
        if action == "REMOVE":
            BRICKER_OT_bevel.removeBevelMods(bricks)
            cm.bevel_added = False
        elif action == "ADD":
            BRICKER_OT_bevel.create_bevel_mods(cm, bricks)
            cm.bevel_added = True

    @classmethod
    def removeBevelMods(self, objs):
        """ removes bevel modifier 'obj.name + "_bvl"' for objects in 'objs' """
        objs = confirm_iter(objs)
        for obj in objs:
            bvlMod = obj.modifiers.get(obj.name + "_bvl")
            if bvlMod is None:
                continue
            obj.modifiers.remove(bvlMod)

    @classmethod
    def create_bevel_mods(self, cm, objs):
        """ runs 'createBevelMod' on objects in 'objs' """
        # get objs to bevel
        objs = confirm_iter(objs)
        # initialize vars
        segments = cm.bevel_segments
        profile = cm.bevel_profile
        show_render = cm.bevel_show_render
        show_viewport = cm.bevel_show_viewport
        show_in_editmode = cm.bevel_show_edit_mode
        # create bevel modifiers for each object
        for obj in objs:
            self.createBevelMod(obj=obj, width=cm.bevel_width * cm.brick_height, segments=segments, profile=profile, limitMethod="WEIGHT", offsetType="OFFSET", angleLimit=1.55334, show_render=show_render, show_viewport=show_viewport, show_in_editmode=show_in_editmode)

    @classmethod
    def createBevelMod(self, obj:Object, width:float=1, segments:int=1, profile:float=0.5, onlyVerts:bool=False, limitMethod:str="NONE", angleLimit:float=0.523599, vertexGroup:str=None, offsetType:str="OFFSET", show_render:bool=True, show_viewport:bool=True, show_in_editmode:bool=True):
        """ create bevel modifier for 'obj' with given parameters """
        d_mod = obj.modifiers.get(obj.name + "_bvl")
        if not d_mod:
            d_mod = obj.modifiers.new(obj.name + "_bvl", "BEVEL")
            e_mod = obj.modifiers.get("Edge Split")
            if e_mod:
                obj.modifiers.remove(e_mod)
                add_edge_split_mod(obj)
        # only update values if necessary (prevents multiple updates to mesh)
        if d_mod.use_only_vertices != onlyVerts:
            d_mod.use_only_vertices = onlyVerts
        if d_mod.width != width:
            d_mod.width = width
        if d_mod.segments != segments:
            d_mod.segments = segments
        if d_mod.profile != profile:
            d_mod.profile = profile
        if d_mod.limit_method != limitMethod:
            d_mod.limit_method = limitMethod
        if vertexGroup and d_mod.vertex_group != vertexGroup:
            try:
                d_mod.vertex_group = vertexGroup
            except Exception as e:
                print("[Bricker]", e)
                d_mod.limit_method = "ANGLE"
        if d_mod.angle_limit != angleLimit:
            d_mod.angle_limit = angleLimit
        if d_mod.offset_type != offsetType:
            d_mod.offset_type = offsetType
        # update visibility of bevel modifier
        if d_mod.show_render != show_render:
            d_mod.show_render = show_render
        if d_mod.show_viewport != show_viewport:
            d_mod.show_viewport = show_viewport
        if d_mod.show_in_editmode != show_in_editmode:
            d_mod.show_in_editmode = show_in_editmode


    #############################################
