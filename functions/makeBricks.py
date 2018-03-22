"""
Copyright (C) 2017 Bricks Brought to Life
http://bblanimation.com/
chris@bblanimation.com

Created by Christopher Gearhart

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# System imports
import bmesh
import math
import time
import sys
import random
import json
import numpy as np

# Blender imports
import bpy
from mathutils import Vector, Matrix

# Bricker imports
from .hashObject import hash_object
from ..lib.Brick import Bricks
from ..lib.bricksDict import *
from .common import *
from .wrappers import *
from .general import bounds
from ..lib.caches import bricker_bm_cache
from ..lib.abs_plastic_materials import getAbsPlasticMaterialNames
from .makeBricks_utils import *


@timed_call('Time Elapsed')
def makeBricks(source, parent, logo, logo_details, dimensions, bricksDict, cm=None, split=False, brickScale=None, customData=None, customObj_details=None, group_name=None, replaceExistingGroup=True, frameNum=None, cursorStatus=False, keys="ALL", printStatus=True):
    # set up variables
    scn = bpy.context.scene
    cm = cm or scn.cmlist[scn.cmlist_index]
    n = cm.source_name
    zStep = getZStep(cm)

    # reset brickSizes/TypesUsed
    if keys == "ALL":
        cm.brickSizesUsed = ""
        cm.brickTypesUsed = ""

    mergeVertical = keys != "ALL" or cm.brickType == "BRICKS AND PLATES"

    # get bricksDict dicts in seeded order
    if keys == "ALL":
        keys = list(bricksDict.keys())
    keys.sort()
    random.seed(cm.mergeSeed)
    random.shuffle(keys)
    # sort the list by the first character only
    keys.sort(key=lambda x: strToList(x)[2])
    # get dictionary of keys based on z value
    keysDict = {}
    for k0 in keys:
        z = strToList(k0)[2]
        if bricksDict[k0]["draw"]:
            if z in keysDict:
                keysDict[z].append(k0)
            else:
                keysDict[z] = [k0]

    # get brick group
    group_name = group_name or 'Bricker_%(n)s_bricks' % locals()
    bGroup = bpy.data.groups.get(group_name)
    # create new group if no existing group found
    if bGroup is None:
        bGroup = bpy.data.groups.new(group_name)
    # else, replace existing group
    elif replaceExistingGroup:
        bpy.data.groups.remove(group=bGroup, do_unlink=True)
        bGroup = bpy.data.groups.new(group_name)

    brick_mats = []
    brick_materials_installed = hasattr(scn, "isBrickMaterialsInstalled") and scn.isBrickMaterialsInstalled
    if cm.materialType == "RANDOM" and brick_materials_installed:
        mats0 = bpy.data.materials.keys()
        brick_mats = [color for color in bpy.props.abs_plastic_materials if color in mats0 and color in getAbsPlasticMaterialNames()]

    # initialize progress bar around cursor
    old_percent = updateProgressBars(printStatus, cursorStatus, 0, -1, "Building")

    # initialize random states
    randS1 = np.random.RandomState(cm.mergeSeed)  # for brickSize calc
    randS2 = np.random.RandomState(0)  # for random colors, seed will be changed later
    randS3 = np.random.RandomState(cm.mergeSeed+1)
    randS4 = np.random.RandomState(cm.mergeSeed+2)

    mats = []
    allBrickMeshes = []
    lowestZ = -1
    curZ = -1
    availableKeys = []
    maxBrickHeight = 1 if zStep == 3 else max(legalBricks.keys())
    # set up internal material for this object
    internalMat = None if len(source.data.materials) == 0 else bpy.data.materials.get(cm.internalMatName) or bpy.data.materials.get("Bricker_%(n)s_internal" % locals()) or bpy.data.materials.new("Bricker_%(n)s_internal" % locals())
    if internalMat is not None and cm.materialType == "SOURCE" and cm.matShellDepth < cm.shellThickness:
        mats.append(internalMat)
    # initialize supportBrickDs
    supportBrickDs = []
    bricksCreated = []
    keysNotChecked = keys.copy()
    # set number of times to run through all keys
    numIters = 2 if "PLATES" in cm.brickType else 1
    for timeThrough in range(numIters):
        # iterate through locations in bricksDict from bottom to top
        for i, key in enumerate(keys):
            brickD = bricksDict[key]
            # skip keys that are already drawn or have attempted merge
            if not brickD["draw"] or brickD["attempted_merge"] or brickD["parent"] not in [None, "self"]:
                # remove ignored keys from keysNotChecked (for attemptMerge)
                if key in keysNotChecked:
                    keysNotChecked.remove(key)
                if key in availableKeys:
                    availableKeys.remove(key)
                continue

            # initialize vars
            loc = strToList(key)

            if loc[2] != curZ:
                curZ = loc[2]
                availableKeys = [keysDict[curZ + ii] for ii in range(maxBrickHeight)]
                # initialize lowestZ if not done already
                if lowestZ == -1:
                    lowestZ = loc[2]

            # skip second and third rows on first time through
            if numIters == 2 and cm.alignBricks and skipThisRow(cm, timeThrough, lowestZ, loc[2]):
                continue

            # merge current brick with available adjacent bricks
            brickSize = mergeWithAdjacentBricks(cm, brickD, bricksDict, key, keysNotChecked, [1, 1, zStep], zStep, randS1, mergeVertical=mergeVertical)
            # add brickSize to cm.brickSizesUsed if not already there
            brickSizeStr = listToStr(sorted(brickSize[:2]) + [brickSize[2]])
            cm.brickSizesUsed += brickSizeStr if cm.brickSizesUsed == "" else ("|" + brickSizeStr if brickSizeStr not in cm.brickSizesUsed.split("|") else "")
            cm.brickTypesUsed += brickD["type"] if cm.brickTypesUsed == "" else ("|" + str(brickD["type"]) if brickD["type"] not in cm.brickTypesUsed.split("|") else "")

            # create brick based on the current brickD information
            drawBrick(cm, bricksDict, brickD, key, loc, keys, i, dimensions, brickSize, split, customData, customObj_details, brickScale, bricksCreated, supportBrickDs, allBrickMeshes, logo, logo_details, mats, brick_mats, internalMat, randS1, randS2, randS3, randS4)

            # print build status to terminal
            cur_percent = 1 - (len(keysNotChecked) / len(keys))
            old_percent = updateProgressBars(printStatus, cursorStatus, cur_percent, old_percent, "Building")

            # remove keys in new brick from keysNotChecked (for attemptMerge)
            updateKeysLists(brickSize, loc, keysNotChecked, availableKeys, key)


    # remove duplicate of original logoDetail
    if cm.logoDetail != "LEGO" and logo is not None:
        bpy.data.objects.remove(logo)
    # end progress bars
    updateProgressBars(printStatus, cursorStatus, 1, 0, "Building")

    # combine meshes, link to scene, and add relevant data to the new Blender MESH object
    if split:
        # iterate through keys
        old_percent = 0
        for i, key in enumerate(keys):
            old_percent = updateProgressBars(printStatus, False, i/len(bricksDict), old_percent, "Linking to Scene")

            if bricksDict[key]["parent"] == "self" and bricksDict[key]["draw"]:
                name = bricksDict[key]["name"]
                brick = bpy.data.objects.get(name)
                # create vert group for bevel mod (assuming only logo verts are selected):
                vg = brick.vertex_groups.new("%(name)s_bevel" % locals())
                vertList = [v.index for v in brick.data.vertices if not v.select]
                vg.add(vertList, 1, "ADD")
                # set up remaining brick info
                bGroup.objects.link(brick)
                brick.parent = parent
                scn.objects.link(brick)
                brick.isBrick = True
        updateProgressBars(printStatus, False, 1, 0, "Linking to Scene")
    else:
        m = combineMeshes(allBrickMeshes, printStatus)
        name = 'Bricker_%(n)s_bricks_combined' % locals()
        if frameNum:
            name = "%(name)s_frame_%(frameNum)s" % locals()
        allBricksObj = bpy.data.objects.new(name, m)
        allBricksObj.cmlist_id = cm.id
        if cm.brickType != "CUSTOM":
            # create vert group for bevel mod (assuming only logo verts are selected):
            vg = allBricksObj.vertex_groups.new("%(name)s_bevel" % locals())
            vertList = [v.index for v in allBricksObj.data.vertices if not v.select]
            vg.add(vertList, 1, "ADD")
            # add edge split modifier
            addEdgeSplitMod(allBricksObj)
        if cm.materialType == "CUSTOM":
            mat = bpy.data.materials.get(cm.materialName)
            if mat is not None:
                allBricksObj.data.materials.append(mat)
        elif cm.materialType == "SOURCE" or (cm.materialType == "RANDOM" and len(brick_mats) > 0):
            for mat in mats:
                allBricksObj.data.materials.append(mat)
        # set parent
        allBricksObj.parent = parent
        # add bricks obj to scene, bGroup, and bricksCreated
        bGroup.objects.link(allBricksObj)
        scn.objects.link(allBricksObj)
        bricksCreated.append(allBricksObj)
        # protect allBricksObj from being deleted
        allBricksObj.isBrickifiedObject = True

    # reset 'attempted_merge' for all items in bricksDict
    for key0 in bricksDict:
        bricksDict[key0]["attempted_merge"] = False

    return bricksCreated, bricksDict
