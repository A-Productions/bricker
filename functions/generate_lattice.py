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

# Blender imports
import bpy
from mathutils import Vector

# Rebrickr imports
from .common import drawBMesh


def tupleAdd(p1, p2):
    """ returns linear sum of two given tuples """
    return tuple(x+y for x,y in zip(p1, p2))


# R = resolution tuple, s = 3D scale tuple, o = offset lattice center from origin
def generateLattice(R, s, o=(0, 0, 0)):
    """ returns matrix with lattice vert coords given R, s, and o """
    # bme = bmesh.new()

    # initialize variables
    coordMatrix = []
    xR, yR, zR = R
    xS, yS, zS = s
    o = (o[0] - (o[0] % xR), o[1] - (o[1] % yR), o[2] - (o[2] % zR))
    xN = (xS/(2*xR))
    yN = (yS/(2*yR))
    zN = (zS/(2*zR))
    xL = int(round((xS)/xR))+2
    yL = int(round((yS)/yR))+2
    zL = int(round((zS)/zR))+2
    if yL != 1:
        yL += 2
    if xL != 1:
        xL += 2
    if zL != 1:
        zL += 2
    # iterate through x,y,z dimensions and create verts/connect with edges
    for x in range(xL):
        coordList1 = []
        xCO = (x-xN)*xR
        xCO -= xCO % R[0]
        for y in range(yL):
            coordList2 = []
            yCO = (y-yN)*yR
            yCO -= yCO % R[1]
            for z in range(zL):
                # create verts
                zCO = (z-zN)*zR
                zCO -= zCO % R[2]
                p = Vector((o[0] + xCO, o[1] + yCO, o[2] + zCO))
                # bme.verts.new(p)
                coordList2.append(p)
            coordList1.append(coordList2)
        coordMatrix.append(coordList1)
    # drawBMesh(bme)
    # return coord matrix
    return coordMatrix
