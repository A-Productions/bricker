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
import time
import numpy as np

# Blender imports
import bpy
from bpy.types import Object
from mathutils import Matrix, Vector

# Addon imports
from .functions import *
from ...functions.common import *
from ...functions.general import *
from ...functions.generate_lattice import generateLattice
from ...functions.wrappers import *
from ...functions.smoke_sim import *
from ..Brick import Bricks

accs = [0, 0, 0, 0, 0]


def cast_rays(obj_eval:Object, point:Vector, direction:Vector, mini_dist:float, round_type:str="CEILING", edge_len:int=0):
    """
    obj_eval   -- source object to test intersections for
    point      -- starting point for ray casting
    direction  -- cast ray in this direction
    mini_dist  -- Vector with miniscule amount to add after intersection
    round_type -- round final intersection location Vector with this type
    edge_len   -- distance to test for intersections
    """
    # initialize variables
    first_direction = False
    first_intersection = None
    next_intersection_loc = None
    last_intersection = None
    edge_intersects = False
    edge_len2 = round(edge_len + 0.000001, 6)
    starting_point = point
    intersections = 0
    # cast rays until no more rays to cast
    while True:
        _,location,normal,index = obj_eval.ray_cast(starting_point, direction)#distance=edge_len*1.00000000001)
        if index == -1: break
        if intersections == 0:
            first_direction = direction.dot(normal)
        if edge_len != 0:
            dist = (location - point).length
            # get first and last intersection (used when getting materials of nearest (first or last intersected) face)
            if dist <= edge_len2:
                if intersections == 0:
                    edge_intersects = True
                    first_intersection = {"idx":index, "dist":dist, "loc":location, "normal":normal}
                last_intersection = {"idx":index, "dist":edge_len - dist, "loc":location, "normal":normal}

            # set next_intersection_loc
            if next_intersection_loc is None:
                next_intersection_loc = location.copy()
        intersections += 1
        location = vec_round(location, precision=6, round_type=round_type)
        starting_point = location + mini_dist

    if edge_len != 0:
        return intersections, first_direction, first_intersection, next_intersection_loc, last_intersection, edge_intersects
    else:
        return intersections, first_direction


def ray_obj_intersections(scn, point, direction, mini_dist:Vector, edge_len, obj, useNormals, insidenessRayCastDir, brickShell):
    """
    cast ray(s) from point in direction to determine insideness and whether edge intersects obj within edge_len

    returned:
    - not outside       - 'point' is inside object 'obj'
    - edge_intersects    - ray from 'point' in 'direction' of length 'edge_len' intersects object 'obj'
    - intersections     - number of ray-obj intersections from 'point' in 'direction' to infinity
    - next_intersection_loc  - second ray intersection from 'point' in 'direction'
    - first_intersection - dictionary containing 'idx':index of first intersection and 'distance:distance from point to first intersection within edge_len
    - last_intersection  - dictionary containing 'idx':index of last intersection and 'distance:distance from point to last intersection within edge_len

    """

    # initialize variables
    intersections = 0
    outsideL = []
    if b280():
        depsgraph = bpy.context.view_layer.depsgraph
        obj_eval = obj.evaluated_get(depsgraph)
    else:
        obj_eval = obj
    # set axis of direction
    axes = "XYZ" if direction[0] > 0 else ("YZX" if direction[1] > 0 else "ZXY")
    # run initial intersection check
    intersections, first_direction, first_intersection, next_intersection_loc, last_intersection, edge_intersects = cast_rays(obj_eval, point, direction, mini_dist, edge_len=edge_len)

    if brickShell == "CONSISTENT" and edge_intersects:
        # skip insideness checks if brick shell doesn't take insideness into account
        outside = True
    else:
        # run initial insideness check(s)
        if insidenessRayCastDir == "HIGH EFFICIENCY" or axes[0] in insidenessRayCastDir:
            outsideL.append(0)
            if intersections%2 == 0 and not (useNormals and first_direction > 0):
                outsideL[0] = 1
            else:
                # double check vert is inside mesh
                # NOTE: no longer optional because this is almost always necessary
                count, first_direction = cast_rays(obj_eval, point, -direction, -mini_dist, round_type="FLOOR")
                if count%2 == 0 and not (useNormals and first_direction > 0):
                    outsideL[0] = 1

        # run more insideness checks
        if insidenessRayCastDir != "HIGH EFFICIENCY":
            dir0 = Vector((direction[2], direction[0], direction[1]))
            dir1 = Vector((direction[1], direction[2], direction[0]))
            mini_dist0 = Vector((mini_dist[2], mini_dist[0], mini_dist[1]))
            mini_dist1 = Vector((mini_dist[1], mini_dist[2], mini_dist[0]))
            dirs = ((dir0, mini_dist0), (dir1, mini_dist1))
            for i in range(2):
                if axes[i+1] in insidenessRayCastDir:
                    outsideL.append(0)
                    direction = dirs[i][0]
                    mini_dist = dirs[i][1]
                    count, first_direction = cast_rays(obj_eval, point, direction, mini_dist)
                    if count%2 == 0 and not (useNormals and first_direction > 0):
                        outsideL[len(outsideL) - 1] = 1
                    else:
                        # double check vert is inside mesh
                        # NOTE: no longer optional because this is almost always necessary
                        count, first_direction = cast_rays(obj_eval, point, -direction, -mini_dist, round_type="FLOOR")
                        if count%2 == 0 and not (useNormals and first_direction > 0):
                            outsideL[len(outsideL) - 1] = 1

        # find average of outsideL and set outside accordingly (<0.5 is False, >=0.5 is True)
        outside = sum(outsideL)/len(outsideL) >= 0.5

    # return helpful information
    return not outside, edge_intersects, intersections, next_intersection_loc, first_intersection, last_intersection

def updateBFMatrix(scn, x0, y0, z0, coordMatrix, ray, edge_len, faceIdxMatrix, brickFreqMatrix, brickShell, source, x1, y1, z1, mini_dist, useNormals, insidenessRayCastDir):
    """ update brickFreqMatrix[x0][y0][z0] based on results from ray_obj_intersections """
    point = coordMatrix[x0][y0][z0]
    point_inside, edge_intersects, intersections, next_intersection_loc, first_intersection, last_intersection = ray_obj_intersections(scn, point, ray, mini_dist, edge_len, source, useNormals, insidenessRayCastDir, brickShell)

    if point_inside and brickFreqMatrix[x0][y0][z0] == 0:
        # define brick as inside shell
        brickFreqMatrix[x0][y0][z0] = -1
    if edge_intersects:
        if (brickShell in ("INSIDE", "CONSISTENT") and point_inside) or (brickShell == "OUTSIDE" and not point_inside):
            # define brick as part of shell
            brickFreqMatrix[x0][y0][z0] = 1
            # set or update nearest face to brick
            if type(faceIdxMatrix[x0][y0][z0]) != dict or faceIdxMatrix[x0][y0][z0]["dist"] > first_intersection["dist"]:
                faceIdxMatrix[x0][y0][z0] = first_intersection
        if (brickShell in ("INSIDE", "CONSISTENT") and not point_inside) or (brickShell == "OUTSIDE" and point_inside):
            try:
                # define brick as part of shell
                brickFreqMatrix[x1][y1][z1] = 1
            except IndexError:
                return -1, None, True
            # set or update nearest face to brick
            if type(faceIdxMatrix[x1][y1][z1]) != dict or faceIdxMatrix[x1][y1][z1]["dist"] > last_intersection["dist"]:
                faceIdxMatrix[x1][y1][z1] = last_intersection

    return intersections, next_intersection_loc, edge_intersects

def isInternal(bricksDict, key):
    """ check if brick entry in bricksDict is internal """
    val = bricksDict[key]["val"]
    return (val > 0 and val < 1) or val == -1

def addColumnSupports(bricksDict, keys, thickness, step):
    """ update bricksDict internal entries to draw columns
    bricksDict -- dictionary with brick information at each lattice coordinate
    keys       -- keys to test in bricksDict
    thickness  -- thickness of the columns
    step       -- distance between columns
    """
    step = step + thickness
    for key in keys:
        if not isInternal(bricksDict, key):
            continue
        x,y,z = getDictLoc(bricksDict, key)
        if (x % step < thickness and
            y % step < thickness):
            bricksDict[key]["draw"] = True

def addLatticeSupports(bricksDict, keys, step, height, alternateXY):
    """ update bricksDict internal entries to draw lattice supports
    bricksDict  -- dictionary with brick information at each lattice coordinate
    keys        -- keys to test in bricksDict
    step        -- distance between lattice supports
    alternateXY -- alternate x-beams and y-beams for each Z-axis level
    """
    for key in keys:
        if not isInternal(bricksDict, key):
            continue
        x,y,z = getDictLoc(bricksDict, key)
        z0 = (floor(z / height) if alternateXY else z) % 2
        if x % step == 0 and (not alternateXY or z0 == 0):
            bricksDict[key]["draw"] = True
        elif y % step == 0 and (not alternateXY or z0 == 1):
            bricksDict[key]["draw"] = True

def updateInternal(bricksDict, cm, keys="ALL", clearExisting=False):
    """ update bricksDict internal entries
    cm            -- active cmlist object
    bricksDict    -- dictionary with brick information at each lattice coordinate
    keys          -- keys to test in bricksDict
    clearExisting -- set draw for all internal bricks to False before adding supports
    """
    if keys == "ALL": keys = bricksDict.keys()
    # clear extisting internal structure
    if clearExisting:
        # set all bricks as unmerged
        Bricks.splitAll(bricksDict, cm.zStep, keys=keys)
        # clear internal
        for key in keys:
            if isInternal(bricksDict, key):
                bricksDict[key]["draw"] = False
    # Draw column supports
    if cm.internalSupports == "COLUMNS":
        addColumnSupports(bricksDict, keys, cm.colThickness, cm.colStep)
    # draw lattice supports
    elif cm.internalSupports == "LATTICE":
        addLatticeSupports(bricksDict, keys, cm.latticeStep, cm.latticeHeight, cm.alternateXY)

def getBrickMatrix(source, faceIdxMatrix, coordMatrix, brickShell, axes="xyz", printStatus=True, cursorStatus=False):
    """ returns new brickFreqMatrix """
    scn, cm, _ = getActiveContextInfo()
    brickFreqMatrix = deepcopy(faceIdxMatrix)
    axes = axes.lower()
    dist = coordMatrix[1][1][1] - coordMatrix[0][0][0]
    highEfficiency = cm.insidenessRayCastDir in ("HIGH EFFICIENCY", "XYZ")
    # runs update functions only once
    verifyExposure = cm.verifyExposure
    useNormals = cm.useNormals
    insidenessRayCastDir = cm.insidenessRayCastDir
    # initialize Matix sizes
    xL = len(brickFreqMatrix)
    yL = len(brickFreqMatrix[0])
    zL = len(brickFreqMatrix[0][0])


    # initialize values used for printing status
    denom = (len(brickFreqMatrix[0][0]) + len(brickFreqMatrix[0]) + len(brickFreqMatrix))/100
    if cursorStatus:
        wm = bpy.context.window_manager
        wm.progress_begin(0, 100)

    def printCurStatus(percentStart, num0, denom0, lastPercent):
        # print status to terminal
        percent = percentStart + (len(brickFreqMatrix)/denom * (num0/(denom0-1))) / 100
        update_progress_bars(printStatus, cursorStatus, percent, 0, "Shell")
        return percent

    percent0 = 0
    if "x" in axes:
        xRay = coordMatrix[1][0][0] - coordMatrix[0][0][0]
        xEdgeLen = xRay.length
        xmini_dist = Vector((0.00015, 0.0, 0.0))
        for z in range(zL):
            # print status to terminal
            percent0 = printCurStatus(0, z, zL, percent0)
            for y in range(yL):
                next_intersection_loc = None
                i = 0
                for x in range(xL):
                    # skip current loc if casting ray is unnecessary (sets outside vals to last found val)
                    if i == 2 and highEfficiency and next_intersection_loc is not None and coordMatrix[x][y][z].x + dist.x + xmini_dist.x < next_intersection_loc.x:
                        brickFreqMatrix[x][y][z] = val
                        continue
                    # cast rays and update brickFreqMatrix
                    intersections, next_intersection_loc, edge_intersects = updateBFMatrix(scn, x, y, z, coordMatrix, xRay, xEdgeLen, faceIdxMatrix, brickFreqMatrix, brickShell, source, x+1, y, z, xmini_dist, useNormals, insidenessRayCastDir)
                    i = 0 if edge_intersects else (2 if i == 1 else 1)
                    val = brickFreqMatrix[x][y][z]
                    if intersections == 0:
                        break

    percent1 = percent0
    if "y" in axes:
        yRay = coordMatrix[0][1][0] - coordMatrix[0][0][0]
        yEdgeLen = yRay.length
        ymini_dist = Vector((0.0, 0.00015, 0.0))
        for z in range(zL):
            # print status to terminal
            percent1 = printCurStatus(percent0, z, zL, percent1)
            for x in range(xL):
                next_intersection_loc = None
                i = 0
                for y in range(yL):
                    # skip current loc if casting ray is unnecessary (sets outside vals to last found val)
                    if i == (3 if verifyExposure else 2) and highEfficiency and next_intersection_loc is not None and coordMatrix[x][y][z].y + dist.y + ymini_dist.y < next_intersection_loc.y:
                        if brickFreqMatrix[x][y][z] == 0:
                            brickFreqMatrix[x][y][z] = val
                        if brickFreqMatrix[x][y][z] == val:
                            continue
                    # cast rays and update brickFreqMatrix
                    intersections, next_intersection_loc, edge_intersects = updateBFMatrix(scn, x, y, z, coordMatrix, yRay, yEdgeLen, faceIdxMatrix, brickFreqMatrix, brickShell, source, x, y+1, z, ymini_dist, useNormals, insidenessRayCastDir)
                    i = 0 if edge_intersects else (2 if i == 1 else 1)
                    val = brickFreqMatrix[x][y][z]
                    if intersections == 0:
                        break

    percent2 = percent1
    if "z" in axes:
        zRay = coordMatrix[0][0][1] - coordMatrix[0][0][0]
        zEdgeLen = zRay.length
        zmini_dist = Vector((0.0, 0.0, 0.00015))
        for x in range(xL):
            # print status to terminal
            percent2 = printCurStatus(percent1, x, xL, percent2)
            for y in range(yL):
                next_intersection_loc = None
                i = 0
                for z in range(zL):
                    # skip current loc if casting ray is unnecessary (sets outside vals to last found val)
                    if i == (3 if verifyExposure else 2) and highEfficiency and next_intersection_loc is not None and coordMatrix[x][y][z].z + dist.z + zmini_dist.z < next_intersection_loc.z:
                        if brickFreqMatrix[x][y][z] == 0:
                            brickFreqMatrix[x][y][z] = val
                        if brickFreqMatrix[x][y][z] == val:
                            continue
                    # cast rays and update brickFreqMatrix
                    intersections, next_intersection_loc, edge_intersects = updateBFMatrix(scn, x, y, z, coordMatrix, zRay, zEdgeLen, faceIdxMatrix, brickFreqMatrix, brickShell, source, x, y, z+1, zmini_dist, useNormals, insidenessRayCastDir)
                    i = 0 if edge_intersects else (2 if i == 1 else 1)
                    val = brickFreqMatrix[x][y][z]
                    if intersections == 0:
                        break

    # mark inside freqs as internal (-1) and outside next to outsides for removal
    adjustBFM(brickFreqMatrix, matShellDepth=cm.matShellDepth, calcInternals=cm.calcInternals, faceIdxMatrix=faceIdxMatrix, axes=axes)

    # print status to terminal
    update_progress_bars(printStatus, cursorStatus, 1, 0, "Shell", end=True)

    return brickFreqMatrix


def getBrickMatrixSmoke(faceIdxMatrix, brickShell, source_details, printStatus=True, cursorStatus=False):
    cm = getActiveContextInfo()[1]
    source = cm.source_obj
    density_grid, flame_grid, color_grid, domain_res, max_res, adapt = getSmokeInfo(source)
    brickFreqMatrix = deepcopy(faceIdxMatrix)
    colorMatrix = deepcopy(faceIdxMatrix)
    old_percent = 0
    brightness = Vector([(cm.smokeBrightness - 1) / 5]*3)
    sat_mat = get_saturation_matrix(cm.smokeSaturation)
    quality = cm.smokeQuality

    # get starting and ending idx
    if adapt:
        source_details_adapt = bounds(source)
        adapt_min = source_details_adapt.min
        adapt_max = source_details_adapt.max
        full_min = source_details.min
        full_max = source_details.max
        full_dist = full_max - full_min
        if 0 in full_dist:
            return brickFreqMatrix, colorMatrix
        start_percent = vec_div(adapt_min - full_min, full_dist)
        end_percent   = vec_div(adapt_max - full_min, full_dist)
        s_idx = (len(faceIdxMatrix) * start_percent.x, len(faceIdxMatrix[0]) * start_percent.y, len(faceIdxMatrix[0][0]) * start_percent.z)
        e_idx = (len(faceIdxMatrix) * end_percent.x,   len(faceIdxMatrix[0]) * end_percent.y,   len(faceIdxMatrix[0][0]) * end_percent.z)
    else:
        s_idx = (0, 0, 0)
        e_idx = (len(faceIdxMatrix), len(faceIdxMatrix[0]), len(faceIdxMatrix[0][0]))

    # get number of iterations from s_idx to e_idx for x, y, z
    d = Vector((e_idx[0] - s_idx[0], e_idx[1] - s_idx[1], e_idx[2] - s_idx[2]))
    # verify bounding box is larger than 0 in all directions
    if 0 in d:
        return brickFreqMatrix, colorMatrix
    # get x/y/z distances
    xn0 = domain_res[0] / d.x
    yn0 = domain_res[1] / d.y
    zn0 = domain_res[2] / d.z
    denom = d.x

    # initialize variables
    flameIntensity = cm.flameIntensity
    flameColor = cm.flameColor
    smokeDensity = cm.smokeDensity

    # set up brickFreqMatrix values
    for x in range(int(s_idx[0]), int(e_idx[0])):
        # print status to terminal
        old_percent = update_progress_bars(printStatus, cursorStatus, x / denom, old_percent, "Shell")
        for y in range(int(s_idx[1]), int(e_idx[1])):
            for z in range(int(s_idx[2]), int(e_idx[2])):
                d_acc = 0
                f_acc = 0
                cs_acc = Vector((0, 0, 0))
                cf_acc = Vector((0, 0, 0))
                # get indices for
                x0 = x - s_idx[0]
                y0 = y - s_idx[1]
                z0 = z - s_idx[2]
                xn = [int(xn0 * x0), int(xn0 * (x0 + 1))]
                yn = [int(yn0 * y0), int(yn0 * (y0 + 1))]
                zn = [int(zn0 * z0), int(zn0 * (z0 + 1))]
                xn[1] += 1 if xn[1] == xn[0] else 0
                yn[1] += 1 if yn[1] == yn[0] else 0
                zn[1] += 1 if zn[1] == zn[0] else 0
                step_x = math.ceil((xn[1] - xn[0]) / quality)
                step_y = math.ceil((yn[1] - yn[0]) / quality)
                step_z = math.ceil((zn[1] - zn[0]) / quality)
                ave_denom = 0
                for x1 in range(xn[0], xn[1], step_x):
                    for y1 in range(yn[0], yn[1], step_y):
                        for z1 in range(zn[0], zn[1], step_z):
                            cur_idx = (z1 * domain_res[1] + y1) * domain_res[0] + x1
                            _d = density_grid[cur_idx]
                            f = flame_grid[cur_idx]
                            d_acc += _d
                            f_acc += f
                            cur_idx_ext = cur_idx * 4
                            cs_acc += _d * Vector((color_grid[cur_idx_ext], color_grid[cur_idx_ext + 1], color_grid[cur_idx_ext + 2]))
                            cf_acc += Vector(f * flameIntensity * f * flameColor)
                            ave_denom += 1
                d_ave = d_acc / ave_denom
                f_ave = f_acc / ave_denom
                alpha = d_ave + f_ave
                cs_ave = cs_acc / (ave_denom * (d_ave if d_ave != 0 else 1))
                cf_ave = cf_acc / (ave_denom * (f_ave if f_ave != 0 else 1))
                c_ave = (cs_ave + cf_ave)
                # add brightness
                c_ave += brightness
                # add saturation
                c_ave = mathutils_mult(c_ave, sat_mat)
                brickFreqMatrix[x][y][z] = 0 if alpha < (1 - smokeDensity) else 1
                colorMatrix[x][y][z] = list(c_ave) + [alpha]

    # mark inside freqs as internal (-1) and outside next to outsides for removal
    adjustBFM(brickFreqMatrix, matShellDepth=cm.matShellDepth, calcInternals=cm.calcInternals, axes=False)

    # end progress bar
    update_progress_bars(printStatus, cursorStatus, 1, 0, "Shell", end=True)

    return brickFreqMatrix, colorMatrix


def adjustBFM(brickFreqMatrix, matShellDepth, calcInternals, faceIdxMatrix=None, axes=""):
    """ adjust brickFreqMatrix values """
    shellVals = []
    xL = len(brickFreqMatrix)
    yL = len(brickFreqMatrix[0])
    zL = len(brickFreqMatrix[0][0])

    # if generating shell outside mesh with less than three axes
    if axes != "xyz":
        for x in range(xL):
            for y in range(yL):
                for z in range(zL):
                    # if current location is inside (-1) and adjacent location is out of bounds, current location is shell (1)
                    if (brickFreqMatrix[x][y][z] == -1 and
                        (("z" not in axes and
                          (z in (0, zL-1) or
                           brickFreqMatrix[x][y][z+1] == 0 or
                           brickFreqMatrix[x][y][z-1] == 0)) or
                         ("y" not in axes and
                          (y in (0, yL-1) or
                           brickFreqMatrix[x][y+1][z] == 0 or
                           brickFreqMatrix[x][y-1][z] == 0)) or
                         ("x" not in axes and
                          (x in (0, xL-1) or
                           brickFreqMatrix[x+1][y][z] == 0 or
                           brickFreqMatrix[x-1][y][z] == 0))
                      )):
                        brickFreqMatrix[x][y][z] = 1
                        # TODO: set faceIdxMatrix value to nearest shell value using some sort of built in nearest poly to point function

    # # iterate through all values except boundaries
    # for x in range(1, xL - 1):
    #     for y in range(1, yL - 1):
    #         for z in range(1, zL - 1):
    #             # If inside location (-1) intersects outside location (0), make it ouside (0)
    #             if (brickFreqMatrix[x][y][z] == -1 and
    #                 (brickFreqMatrix[x+1][y][z] == 0 or
    #                  brickFreqMatrix[x-1][y][z] == 0 or
    #                  brickFreqMatrix[x][y+1][z] == 0 or
    #                  brickFreqMatrix[x][y-1][z] == 0 or
    #                  brickFreqMatrix[x][y][z+1] == 0 or
    #                  brickFreqMatrix[x][y][z-1] == 0)):
    #                 brickFreqMatrix[x][y][z] = 0

    trash_vals = [0] if calcInternals else [0, -1]
    all_shell_vals = []
    # iterate through all values
    for x in range(xL):
        for y in range(yL):
            for z in range(zL):
                # mark outside and unused inside brickFreqMatrix values for removal
                if brickFreqMatrix[x][y][z] in trash_vals:
                    brickFreqMatrix[x][y][z] = None
                # get shell values for next calc
                elif brickFreqMatrix[x][y][z] == 1:
                    all_shell_vals.append((x, y, z))

    if not calcInternals:
        return

    # iterate through all shell values
    for x, y, z in all_shell_vals:
        # If shell location (1) does not intersect outside/trashed location (0, None), make it inside (-1)
        if brickFreqMatrix[x][y][z] == 1:
            if all((brickFreqMatrix[x+1][y][z],
                    brickFreqMatrix[x-1][y][z],
                    brickFreqMatrix[x][y+1][z],
                    brickFreqMatrix[x][y-1][z],
                    brickFreqMatrix[x][y][z+1],
                    brickFreqMatrix[x][y][z-1])):
                brickFreqMatrix[x][y][z] = -1
            else:
                shellVals.append((x, y, z))


    # Update internals
    j = 1
    setNF = True
    for i in range(50):
        j = round(j-0.01, 2)
        gotOne = False
        newShellVals = []
        if setNF:
            setNF = (1 - j) * 100 < matShellDepth
        for x, y, z in shellVals:
            idxsToCheck = ((x+1, y, z),
                           (x-1, y, z),
                           (x, y+1, z),
                           (x, y-1, z),
                           (x, y, z+1),
                           (x, y, z-1))
            for idx in idxsToCheck:
                # print("*"*25)
                # print(str(idx))
                # print(str(len(brickFreqMatrix)), str(len(brickFreqMatrix[0])), str(len(brickFreqMatrix[0][0])))
                # print("*"*25)
                curVal = brickFreqMatrix[idx[0]][idx[1]][idx[2]]
                if curVal == -1:
                    newShellVals.append(idx)
                    brickFreqMatrix[idx[0]][idx[1]][idx[2]] = j
                    if faceIdxMatrix and setNF: faceIdxMatrix[idx[0]][idx[1]][idx[2]] = faceIdxMatrix[x][y][z]
                    gotOne = True
        if not gotOne:
            break
        shellVals = newShellVals


def getThreshold(cm):
    """ returns threshold (draw bricks if returned val >= threshold) """
    return 1.01 - (cm.shellThickness / 100)


def createBricksDictEntry(name:str, loc:list, val:float=0, draw:bool=False, co:tuple=(0, 0, 0), near_face:int=None, near_intersection:str=None, near_normal:tuple=None, rgba:tuple=None, mat_name:str="", custom_mat_name:bool=False, parent:str=None, size:list=None, attempted_merge:bool=False, top_exposed:bool=None, bot_exposed:bool=None, obscures:list=[False]*6, bType:str=None, flipped:bool=False, rotated:bool=False, created_from:str=None):
    """
    create an entry in the dictionary of brick locations

    Keyword Arguments:
    name              -- name of the brick object
    loc               -- strToList(key)
    val               -- location of brick in model (0: outside of model, 0.00-1.00: number of bricks away from shell / 100, 1: on shell)
    draw              -- draw the brick in 3D space
    co                -- 1x1 brick centered at this location
    near_face         -- index of nearest face intersection with source mesh
    near_intersection -- coordinate location of nearest intersection with source mesh
    near_normal       -- normal of the nearest face intersection
    rgba              -- [red, green, blue, alpha] values of brick color
    mat_name          -- name of material attributed to bricks at this location
    custom_mat_name   -- mat_name was set with 'Change Material' customization tool
    parent            -- key into brick dictionary with information about the parent brick merged with this one
    size              -- 3D size of brick (e.g. standard 2x4 brick -> [2, 4, 3])
    attempted_merge   -- attempt has been made in makeBricks function to merge this brick with nearby bricks
    top_exposed       -- top of brick is visible to camera
    bot_exposed       -- bottom of brick is visible to camera
    obscures          -- obscures neighboring locations [+z, -z, +x, -x, +y, -y]
    type              -- type of brick
    flipped           -- brick is flipped over non-mirrored axis
    rotated           -- brick is rotated 90 degrees about the Z axis
    created_from      -- key of brick this brick was created from in drawAdjacent

    """
    return {"name":name,
            "loc":loc,
            "val":val,
            "draw":draw,
            "co":co,
            "near_face":near_face,
            "near_intersection":near_intersection,
            "near_normal":near_normal,
            "rgba":rgba,
            "mat_name":mat_name,
            "custom_mat_name":custom_mat_name,
            "parent":parent,
            "size":size,
            "attempted_merge":attempted_merge,
            "top_exposed":top_exposed,
            "bot_exposed":bot_exposed,
            "obscures":obscures,
            "type":bType,
            "flipped":flipped,
            "rotated":rotated,
            "created_from":created_from,
           }

@timed_call('Time Elapsed')
def makeBricksDict(source, source_details, brickScale, uv_images, cursorStatus=False):
    """ make dictionary with brick information at each coordinate of lattice surrounding source
    source         -- source object to construct lattice around
    source_details -- object details with subattributes for distance and midpoint of x, y, z axes
    brickScale     -- scale of bricks
    cursorStatus   -- update mouse cursor with status of matrix creation
    """
    scn, cm, n = getActiveContextInfo()
    # get lattice bmesh
    print("\ngenerating blueprint...")
    lScale = source_details.dist
    offset = source_details.mid
    if source.parent:
        offset = offset - source.parent.location
    # get coordinate list from intersections of edges with faces
    coordMatrix = generateLattice(brickScale, lScale, offset)
    if len(coordMatrix) == 0:
        coordMatrix.append(source_details.mid)
    # set calculationAxes
    calculationAxes = cm.calculationAxes if cm.brickShell == "OUTSIDE" else "XYZ"
    # set up faceIdxMatrix and brickFreqMatrix
    faceIdxMatrix = np.zeros((len(coordMatrix), len(coordMatrix[0]), len(coordMatrix[0][0])), dtype=int).tolist()
    if cm.isSmoke:
        brickFreqMatrix, smokeColors = getBrickMatrixSmoke(faceIdxMatrix, cm.brickShell, source_details, cursorStatus=cursorStatus)
    else:
        brickFreqMatrix = getBrickMatrix(source, faceIdxMatrix, coordMatrix, cm.brickShell, axes=calculationAxes, cursorStatus=cursorStatus)
        smokeColors = None
    # initialize active keys
    cm.activeKey = (-1, -1, -1)

    # create bricks dictionary with brickFreqMatrix values
    bricksDict = {}
    threshold = getThreshold(cm)
    brickType = cm.brickType  # prevents cm.brickType update function from running over and over in for loop
    uvImage = cm.uvImage
    buildIsDirty = cm.buildIsDirty
    drawnKeys = []
    sourceMats = cm.materialType == "SOURCE"
    noOffset = vec_round(offset, precision=5) == Vector((0, 0, 0))
    for x in range(len(coordMatrix)):
        for y in range(len(coordMatrix[0])):
            for z in range(len(coordMatrix[0][0])):
                # skip brickFreqMatrix values set to None
                if brickFreqMatrix[x][y][z] is None:
                    continue

                # initialize variables
                bKey = listToStr((x, y, z))

                co = coordMatrix[x][y][z].to_tuple() if noOffset else (coordMatrix[x][y][z] - source_details.mid).to_tuple()

                # get material from nearest face intersection point
                nf = faceIdxMatrix[x][y][z]["idx"] if type(faceIdxMatrix[x][y][z]) == dict else None
                ni = faceIdxMatrix[x][y][z]["loc"].to_tuple() if type(faceIdxMatrix[x][y][z]) == dict else None
                nn = faceIdxMatrix[x][y][z]["normal"] if type(faceIdxMatrix[x][y][z]) == dict else None
                norm_dir = getNormalDirection(nn, slopes=True)
                bType = getBrickType(brickType)
                flipped, rotated = getFlipRot("" if norm_dir is None else norm_dir[1:])
                if sourceMats:
                    rgba = smokeColors[x][y][z] if smokeColors else getUVPixelColor(scn, source, nf, ni if ni is None else Vector(ni), uv_images, uvImage)
                else:
                    rgba = (0, 0, 0, 1)
                draw = brickFreqMatrix[x][y][z] >= threshold
                # create bricksDict entry for current brick
                bricksDict[bKey] = createBricksDictEntry(
                    name= 'Bricker_%(n)s__%(bKey)s' % locals(),
                    loc= [x, y, z],
                    val= brickFreqMatrix[x][y][z],
                    draw= draw,
                    co= co,
                    near_face= nf,
                    near_intersection= ni,
                    near_normal= norm_dir,
                    rgba= rgba,
                    # mat_name= "",  # defined in 'updateMaterials' function
                    # obscures= [brickFreqMatrix[x][y][z] != 0]*6,
                    bType= bType,
                    flipped= flipped,
                    rotated= rotated,
                )
                if buildIsDirty and draw:
                    drawnKeys.append(bKey)

    # if buildIsDirty, this is done in drawBrick
    if not cm.buildIsDirty:
        # set exposure of brick locs
        for key in drawnKeys:
            setBrickExposure(bricksDict, key)

    # return list of created Brick objects
    return bricksDict
