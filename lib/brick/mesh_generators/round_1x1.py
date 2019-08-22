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
import bpy
import bmesh
import math
import numpy as np

# Blender imports
from mathutils import Vector

# Addon imports
from .generator_utils import *
from ....functions import *


def make_round_1x1(dimensions:dict, brick_type:str, circle_verts:int=None, type:str="CYLINDER", detail:str="LOW", bme:bmesh=None):
    """
    create round 1x1 brick with bmesh

    Keyword Arguments:
        dimensions  -- dictionary containing brick dimensions
        brick_type   -- cm.brick_type
        circle_verts -- number of vertices per circle of cylinders
        type        -- type of round 1x1 brick in ("CONE", "CYLINDER", "STUD", "STUD_HOLLOW")
        detail      -- level of brick detail (options: ("FLAT", "LOW", "MEDIUM", "HIGH"))
        bme         -- bmesh object in which to create verts

    """
    # ensure type argument passed is valid
    assert type in ("CONE", "CYLINDER", "STUD", "STUD_HOLLOW")
    # create new bmesh object
    bme = bmesh.new() if not bme else bme

    # store original detail amount
    orig_detail = detail
    # cap detail level to medium detail
    detail = "MEDIUM" if "HIGH" else detail
    # if making cone, detail should always be high
    detail = "MEDIUM" if type == "CONE" else detail
    # if making stud, detail should never get beyond low
    detail = "LOW" if type == "STUD" and detail == "MEDIUM" else detail
    # if making hollow stud, detail should never get below medium
    detail = "MEDIUM" if type == "STUD_HOLLOW" else detail

    # set brick height and thickness
    height = dimensions["height"] if not flat_brick_type(brick_type) or "STUD" in type else dimensions["height"] * 3
    thick = Vector([dimensions["thickness"]] * 3)

    # create outer cylinder
    r = dimensions["width"] / 2
    h = height - dimensions["stud_height"]
    z = dimensions["stud_height"] / 2
    bme, verts_outer_cylinder = make_cylinder(r, h, circle_verts, co=Vector((0, 0, z)), bot_face=False, top_face=False, bme=bme)
    # update upper cylinder verts for cone shape
    if type == "CONE":
        new_radius = dimensions["stud_radius"] * 1.075
        factor = new_radius / (dimensions["width"] / 2)
        for vert in verts_outer_cylinder["top"]:
            vert.co.xy = vec_mult(vert.co.xy, [factor]*2)

    # create lower cylinder
    r = dimensions["stud_radius"]
    h = dimensions["stud_height"]
    t = (dimensions["width"] / 2 - r) / 2
    z = - (height / 2) + (dimensions["stud_height"] / 2)
    if detail == "FLAT":
        bme, lower_cylinder_verts = make_cylinder(r + t, h, circle_verts, co=Vector((0, 0, z)), top_face=False, bme=bme)
    else:
        bme, lower_tube_verts = make_tube(r, h, t, circle_verts, co=Vector((0, 0, z)), top_face=False, bme=bme)
        # remove unnecessary upper inner verts from tube
        for vert in lower_tube_verts["inner"]["top"]:
            bme.verts.remove(vert)
        lower_tube_verts["inner"]["top"] = []

    # add stud
    # stud_verts = add_studs(dimensions, height, [1, 1, 1], type, circle_verts, bme, hollow=detail in ("MEDIUM", "HIGH"))
    stud_verts = add_studs(dimensions, height, [1, 1, 1], type, circle_verts, bme, hollow=detail in ("MEDIUM", "HIGH"), bot_face=True)

    # make pointers to appropriate vertex lists
    stud_verts_outer = stud_verts if detail in ("FLAT", "LOW") else stud_verts["outer"]
    stud_verts_inner = stud_verts if detail in ("FLAT", "LOW") else stud_verts["inner"]
    lower_tube_verts_outer = lower_cylinder_verts if detail == "FLAT" else lower_tube_verts["outer"]

    # create faces connecting bottom of stud to top of outer cylinder
    connect_circles(verts_outer_cylinder["top"], stud_verts_outer["bottom"][::-1], bme, select=False)

    # create faces connecting bottom of outer cylinder with top of lower tube
    connect_circles(lower_tube_verts_outer["top"], verts_outer_cylinder["bottom"][::-1], bme, select=False)

    # add detailing inside brick
    if detail != "FLAT":
        # create faces for cylinder inside brick
        _,faces = connect_circles(lower_tube_verts["inner"]["bottom"], stud_verts_outer["bottom"], bme)
        for f in faces:
            f.edges[1].select = True
        smooth_bm_faces(faces)
        # create small inner cylinder inside stud for medium/high detail
        if type == "STUD" and orig_detail in ("MEDIUM", "HIGH"):
            # make small inner cylinders
            r = dimensions["stud_radius"]-(2 * thick.x)
            h = thick.z * 0.99
            z = thick.z + h / 2
            bme, inner_cylinder_verts = make_cylinder(r, h, circle_verts, co=Vector((0, 0, z)), bot_face=False, flip_normals=True, bme=bme)
            # create faces connecting bottom of inner cylinder with bottom of stud
            connect_circles(stud_verts_inner["bottom"], inner_cylinder_verts["bottom"], bme, offset=circle_verts // 2)
        # create face at top of cylinder inside brick
        elif detail == "LOW":
            bme.faces.new(stud_verts_outer["bottom"])

    return bme
