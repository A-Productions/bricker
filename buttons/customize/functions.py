"""
    Copyright (C) 2018 Bricks Brought to Life
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
# NONE!

# Blender imports
import bpy
from bpy.types import Operator

# Addon imports
from ...functions import *
from ..brickify import *
from ..brickify import *
from ...lib.bricksDict.functions import getDictKey
from ...lib.Brick.legal_brick_sizes import *
from .undo_stack import *


def drawUpdatedBricks(cm, bricksDict, keysToUpdate, selectCreated=True):
    if len(keysToUpdate) == 0: return
    if not isUnique(keysToUpdate): raise ValueError("keysToUpdate cannot contain duplicate values")
    print("[Bricker] redrawing...")
    # get arguments for createNewBricks
    n = cm.source_name
    source = bpy.data.objects.get(n)
    source_details, dimensions = getDetailsAndBounds(source, cm)
    Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
    parent = bpy.data.objects.get(Bricker_parent_on)
    logo_details, refLogo = BrickerBrickify.getLogo(bpy.context.scene, cm, dimensions)
    action = "UPDATE_MODEL"
    # actually draw the bricks
    BrickerBrickify.createNewBricks(source, parent, source_details, dimensions, refLogo, logo_details, action, cm=cm, bricksDict=bricksDict, keys=keysToUpdate, clearExistingGroup=False, selectCreated=selectCreated, printStatus=False, redraw=True)
    # add bevel if it was previously added
    if cm.bevelAdded:
        bricks = getBricks(cm)
        BrickerBevel.runBevelAction(bricks, cm)


def getAdjKeysAndBrickVals(bricksDict, loc=None, key=None):
    assert loc or key
    keyError = False
    x, y, z = loc or getDictLoc(bricksDict, key)
    adjKeys = [listToStr((x+1, y, z)),
               listToStr((x-1, y, z)),
               listToStr((x, y+1, z)),
               listToStr((x, y-1, z)),
               listToStr((x, y, z+1)),
               listToStr((x, y, z-1))]
    adjBrickVals = []
    for key in adjKeys.copy():
        try:
            adjBrickVals.append(bricksDict[key]["val"])
        except KeyError:
            adjKeys.remove(key)
            keyError = True
    return adjKeys, adjBrickVals, keyError


def setCurBrickVal(bricksDict, loc, action="ADD"):
    _, adjBrickVals, keyError = getAdjKeysAndBrickVals(bricksDict, loc=loc)
    if action == "ADD" and (keyError or 0 in adjBrickVals or len(adjBrickVals) == 0 or min(adjBrickVals) == 1):
        newVal = 1
    elif action == "REMOVE" and 0 in adjBrickVals:
        newVal = 0
    elif action == "REMOVE":
        newVal = max(adjBrickVals)
    else:
        highestAdjVal = max(adjBrickVals)
        newVal = highestAdjVal - 0.01
    bricksDict[listToStr(loc)]["val"] = newVal


def verifyBrickExposureAboveAndBelow(scn, zStep, origLoc, bricksDict, decriment=0, zNeg=False, zPos=False):
    dictLocs = []
    if not zNeg:
        dictLocs.append((origLoc[0], origLoc[1], origLoc[2] + decriment))
    if not zPos:
        dictLocs.append((origLoc[0], origLoc[1], origLoc[2] - 1))
    # double check exposure of bricks above/below new adjacent brick
    for dictLoc in dictLocs:
        k = listToStr(dictLoc)
        if k not in bricksDict:
            continue
        parent_key = k if bricksDict[k]["parent"] == "self" else bricksDict[k]["parent"]
        if parent_key is not None:
            setAllBrickExposures(bricksDict, zStep, parent_key)
    return bricksDict


def getUsedSizes():
    scn = bpy.context.scene
    items = [("NONE", "None", "")]
    for cm in scn.cmlist:
        sortBy = lambda k: (strToList(k)[2], strToList(k)[0], strToList(k)[1])
        items += [(s, s, "") for s in sorted(cm.brickSizesUsed.split("|"), reverse=True, key=sortBy) if (s, s, "") not in items]
    return items


def getUsedTypes():
    scn = bpy.context.scene
    items = [("NONE", "None", "")]
    for cm in scn.cmlist:
        items += [(t.upper(), t.title(), "") for t in sorted(cm.brickTypesUsed.split("|")) if (t.upper(), t.title(), "") not in items]
    return items


def getAvailableTypes(by="SELECTION", includeSizes=[]):
    items = []
    legalBS = bpy.props.Bricker_legal_brick_sizes
    scn = bpy.context.scene
    objs = bpy.context.selected_objects if by == "SELECTION" else [scn.objects.active]
    objNamesD, bricksDicts = createObjNamesAndBricksDictsDs(objs)
    invalidItems = []
    for cm_id in objNamesD.keys():
        cm = getItemByID(scn.cmlist, cm_id)
        brickType = cm.brickType
        bricksDict = bricksDicts[cm_id]
        objSizes = []
        # check that customObjects are valid
        for idx in range(3):
            targetType = "CUSTOM " + str(idx + 1)
            warningMsg = customValidObject(cm, targetType=targetType, idx=idx)
            if warningMsg is not None and itemFromType(targetType) not in invalidItems:
                invalidItems.append(itemFromType(targetType))
        # build items list
        for obj_name in objNamesD[cm_id]:
            dictKey = getDictKey(obj_name)
            objSize = bricksDict[dictKey]["size"]
            if objSize in objSizes:
                continue
            objSizes.append(objSize)
            if objSize[2] not in (1, 3): raise Exception("Custom Error Message: objSize not in (1, 3)")
            # build items
            items += [itemFromType(typ) for typ in legalBS[3] if includeSizes == "ALL" or objSize[:2] in legalBS[3][typ] + includeSizes]
            if flatBrickType(brickType):
                items += [itemFromType(typ) for typ in legalBS[1] if includeSizes == "ALL" or objSize[:2] in legalBS[1][typ] + includeSizes]
    # uniquify items
    items = uniquify2(items, innerType=tuple)
    # remove invalid items
    for item in invalidItems:
        remove_item(items, item)
    # sort items
    items.sort(key=lambda k: k[0])
    # return items, or null if items was empty
    return items if len(items) > 0 else [("NULL", "Null", "")]


def itemFromType(typ):
    return (typ.upper(), typ.title().replace("_", " "), "")

def updateBrickSizeAndDict(dimensions, source_name, bricksDict, brickSize, key, loc, dec=0, curHeight=None, curType=None, targetHeight=None, targetType=None, createdFrom=None):
    brickD = bricksDict[key]
    assert targetHeight is not None or targetType is not None
    targetHeight = targetHeight or (1 if targetType in getBrickTypes(height=1) else 3)
    assert curHeight is not None or curType is not None
    curHeight = curHeight or (1 if curType in getBrickTypes(height=1) else 3)
    # adjust brick size if changing type from 3 tall to 1 tall
    if curHeight == 3 and targetHeight == 1:
        brickSize[2] = 1
        for x in range(brickSize[0]):
            for y in range(brickSize[1]):
                for z in range(1, curHeight):
                    newLoc = [loc[0] + x, loc[1] + y, loc[2] + z - dec]
                    newKey = listToStr(newLoc)
                    bricksDict[newKey]["parent"] = None
                    bricksDict[newKey]["draw"] = False
                    setCurBrickVal(bricksDict, newLoc, action="REMOVE")
    # adjust brick size if changing type from 1 tall to 3 tall
    elif curHeight == 1 and targetHeight == 3:
        brickSize[2] = 3
        full_d = Vector((dimensions["width"], dimensions["width"], dimensions["height"]))
        # update bricks dict entries above current brick
        for x in range(brickSize[0]):
            for y in range(brickSize[1]):
                for z in range(1, targetHeight):
                    newLoc = [loc[0] + x, loc[1] + y, loc[2] + z]
                    newKey = listToStr(newLoc)
                    # create new bricksDict entry if it doesn't exist
                    if newKey not in bricksDict:
                        bricksDict = createAddlBricksDictEntry(source_name, bricksDict, key, newKey, full_d, x, y, z)
                    # update bricksDict entry to point to new brick
                    bricksDict[newKey]["parent"] = key
                    bricksDict[newKey]["created_from"] = createdFrom
                    bricksDict[newKey]["draw"] = True
                    bricksDict[newKey]["mat_name"] = brickD["mat_name"] if bricksDict[newKey]["mat_name"] == "" else bricksDict[newKey]["mat_name"]
                    bricksDict[newKey]["near_face"] = bricksDict[newKey]["near_face"] or brickD["near_face"]
                    bricksDict[newKey]["near_intersection"] = bricksDict[newKey]["near_intersection"] or tuple(brickD["near_intersection"])
                    if bricksDict[newKey]["val"] == 0:
                        setCurBrickVal(bricksDict, newLoc)
    return brickSize


def createAddlBricksDictEntry(source_name, bricksDict, source_key, key, full_d, x, y, z):
    brickD = bricksDict[source_key]
    newName = "Bricker_%(source_name)s_brick__%(key)s" % locals()
    newCO = (Vector(brickD["co"]) + vec_mult(Vector((x, y, z)), full_d)).to_tuple()
    bricksDict[key] = createBricksDictEntry(
        name=              newName,
        loc=               strToList(key),
        co=                newCO,
        near_face=         brickD["near_face"],
        near_intersection= tuple(brickD["near_intersection"]),
        mat_name=          brickD["mat_name"],
    )
    return bricksDict

def createObjNamesD(objs):
    scn = bpy.context.scene
    # initialize objNamesD
    objNamesD = {}
    # fill objNamesD with selected_objects
    for obj in objs:
        if obj is None or not obj.isBrick:
            continue
        # get cmlist item referred to by object
        cm = getItemByID(scn.cmlist, obj.cmlist_id)
        if cm is None: continue
        # add object to objNamesD
        if cm.id not in objNamesD:
            objNamesD[cm.id] = [obj.name]
        else:
            objNamesD[cm.id].append(obj.name)
    return objNamesD


def createObjNamesAndBricksDictsDs(objs):
    bricksDicts = {}
    objNamesD = createObjNamesD(objs)
    # initialize bricksDicts
    scn = bpy.context.scene
    for cm_id in objNamesD.keys():
        cm = getItemByID(scn.cmlist, cm_id)
        if cm is None: continue
        # get bricksDict from cache
        bricksDict, _ = getBricksDict(cm=cm)
        # add to bricksDicts
        bricksDicts[cm_id] = bricksDict
    return objNamesD, bricksDicts


def selectBricks(objNamesD, bricksDicts, brickSize="NULL", brickType="NULL", allModels=False, only=False, include="EXT"):
    scn = bpy.context.scene
    # split all bricks in objNamesD[cm_id]
    for cm_id in objNamesD.keys():
        cm = getItemByID(scn.cmlist, cm_id)
        if not (cm.idx == scn.cmlist_index or allModels):
            continue
        bricksDict = bricksDicts[cm_id]
        selectedSomething = False
        zStep = getZStep(cm)

        for obj_name in objNamesD[cm_id]:
            # get dict key details of current obj
            dictKey = getDictKey(obj_name)
            dictLoc = getDictLoc(bricksDict, dictKey)
            siz = bricksDict[dictKey]["size"]
            typ = bricksDict[dictKey]["type"]
            onShell = isOnShell(bricksDict, dictKey, loc=dictLoc, zStep=zStep)

            # get current brick object
            curObj = bpy.data.objects.get(obj_name)
            # if curObj is None:
            #     continue
            # select brick
            sizeStr = listToStr(sorted(siz[:2]) + [siz[2]])
            if (sizeStr == brickSize or typ == brickType) and (include == "BOTH" or (include == "INT" and not onShell) or (include == "EXT" and onShell)):
                selectedSomething = True
                curObj.select = True
            elif only:
                curObj.select = False

        # if no brickSize bricks exist, remove from cm.brickSizesUsed or cm.brickTypesUsed
        removeUnusedFromList(cm, brickType=brickType, brickSize=brickSize, selectedSomething=selectedSomething)


def removeUnusedFromList(cm, brickType="NULL", brickSize="NULL", selectedSomething=True):
    item = brickType if brickType != "NULL" else brickSize
    # if brickType/brickSize bricks exist, return None
    if selectedSomething or item == "NULL":
        return None
    # turn brickTypesUsed into list of sizes
    lst = (cm.brickTypesUsed if brickType != "NULL" else cm.brickSizesUsed).split("|")
    # remove unused item
    if item in lst:
        lst.remove(item)
    # convert bTU back to string of sizes split by '|'
    newLst = listToStr(lst, separate_by="|")
    # store new list to current cmlist item
    if brickSize != "NULL":
        cm.brickSizesUsed = newLst
    else:
        cm.brickTypesUsed = newLst
