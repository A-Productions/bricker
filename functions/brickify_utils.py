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

# Blender imports
from mathutils import Vector, Euler, Matrix

# Addon imports
from .common import *
from .general import *
from .logo_obj import *
from .makeBricks import *
from .point_cache import *
from .transformData import *
from ..lib.Brick import Bricks
from ..lib.bricksDict import *


def getNewParent(name, loc):
    parent = bpy.data.objects.new(name, None)
    parent.location = loc
    parent.use_fake_user = True
    return parent


def getLogo(scn, cm, dimensions):
    typ = cm.logoType
    if cm.brickType == "CUSTOM" or typ == "NONE":
        refLogo = None
        logo_details = None
    else:
        if typ == "LEGO":
            refLogo = getLegoLogo(scn, typ, cm.logoResolution, cm.logoDecimate, dimensions)
        else:
            refLogo = cm.logoObject
        # apply transformation to duplicate of logo object and normalize size/position
        logo_details, refLogo = prepareLogoAndGetDetails(scn, refLogo, typ, cm.logoScale, dimensions)
    return logo_details, refLogo


def getAnimColl(n):
    anim_coll_name = "Bricker_%(n)s_bricks" % locals()
    anim_coll = bpy_collections().get(anim_coll_name)
    if anim_coll is None:
        anim_coll = bpy_collections().new(anim_coll_name)
    return anim_coll


def getAction(cm):
    """ gets current action type from passed cmlist item """
    if cm.useAnimation:
        return "UPDATE_ANIM" if cm.animated else "ANIMATE"
    else:
        return "UPDATE_MODEL" if cm.modelCreated else "CREATE"


def getDuplicateObjects(scn, cm, action, startFrame, stopFrame):
    """ returns list of duplicates from source with all traits applied """
    source = cm.source_obj
    n = source.name
    origFrame = scn.frame_current
    soft_body = False
    smoke = False

    # set cm.armature and cm.physics
    for mod in source.modifiers:
        if mod.type == "ARMATURE":
            cm.armature = True
        elif mod.type in ("CLOTH", "SOFT_BODY"):
            soft_body = True
            point_cache = mod.point_cache
        elif mod.type == "SMOKE":
            smoke = True
            point_cache = mod.domain_settings.point_cache

    # step through uncached frames to run simulation
    if soft_body or smoke:
        firstUncachedFrame = getFirstUncachedFrame(source, point_cache)
        for curFrame in range(firstUncachedFrame, startFrame):
            scn.frame_set(curFrame)

    denom = stopFrame - startFrame
    update_progress("Applying Modifiers", 0.0)

    duplicates = {}
    for curFrame in range(startFrame, stopFrame + 1):
        sourceDupName = "Bricker_%(n)s_f_%(curFrame)s" % locals()
        # retrieve previously duplicated source if possible
        if action == "UPDATE_ANIM":
            sourceDup = bpy.data.objects.get(sourceDupName)
            if sourceDup is not None:
                duplicates[curFrame] = sourceDup
                safeLink(sourceDup)
                continue
        # set active frame for applying modifiers
        scn.frame_set(curFrame)
        # duplicate source for current frame
        sourceDup = duplicate(source, link_to_scene=True)
        sourceDup.use_fake_user = True
        sourceDup.name = sourceDupName
        # remove modifiers and constraints
        for mod in sourceDup.modifiers:
            sourceDup.modifiers.remove(mod)
        for constraint in sourceDup.constraints:
            sourceDup.constraints.remove(constraint)
        # apply parent transformation
        if sourceDup.parent:
            parent_clear(sourceDup)
        # apply animated transform data
        sourceDup.matrix_world = source.matrix_world
        sourceDup.animation_data_clear()
        # send to new mesh
        if not cm.isSmoke: sourceDup.data = new_mesh_from_object(source)
        # apply transform data
        apply_transform(sourceDup)
        duplicates[curFrame] = sourceDup
        # update progress bar
        percent = (curFrame - startFrame + 1) / (denom + 2)
        if percent < 1:
            update_progress("Applying Modifiers", percent)
    # update progress bar
    scn.frame_set(origFrame)
    update_depsgraph()
    update_progress("Applying Modifiers", 1)
    return duplicates


def getModelResolution(source, cm):
    res = None
    source_details = bounds(source, use_adaptive_domain=False)
    s = Vector((round(source_details.dist.x, 2),
                round(source_details.dist.y, 2),
                round(source_details.dist.z, 2)))
    if cm.brickType != "CUSTOM":
        dimensions = Bricks.get_dimensions(cm.brickHeight, cm.zStep, cm.gap)
        full_d = Vector((dimensions["width"],
                         dimensions["width"],
                         dimensions["height"]))
        res = vec_div(s, full_d)
    else:
        customObj = cm.customObject1
        if customObj and customObj.type == "MESH":
            custom_details = bounds(customObj)
            if 0 not in custom_details.dist.to_tuple():
                mult = cm.brickHeight / custom_details.dist.z
                full_d = Vector((custom_details.dist.x * mult,
                                 custom_details.dist.y * mult,
                                 cm.brickHeight))
                full_d_offset = vec_mult(full_d, cm.distOffset)
                res = vec_div(s, full_d_offset)
    return res


def shouldBrickifyInBackground(cm, r, action):
    matrixDirty = matrixReallyIsDirty(cm)
    source = cm.source_obj
    return ("ANIM" in action or
             # checks if model is simple enough to run
             (((# model resolution
                r.x * r.y * r.z *
                # accounts for shell thickness
                math.sqrt(cm.shellThickness) *
                # accounts for internal supports
                (1.35 if cm.internalSupports != "NONE" else 1) *
                # accounts for costly ray casting
                (3 if cm.insidenessRayCastDir != "HIGH EFFICIENCY" else 1) *
                # accounts for additional ray casting
                (1.5 if cm.verifyExposure and matrixDirty else 1) *
                # accounts for merging algorithm
                (1.5 if mergableBrickType(cm.brickType) else 1) *
                # accounts for additional merging calculations for connectivity
                (math.sqrt(cm.connectThresh) if mergableBrickType(cm.brickType) and cm.mergeType == "RANDOM" else 1) *
                # accounts for source object resolution
                len(source.data.vertices)**(1/20)) >= (20000 if matrixDirty else 40000)) or
              # no logos
              cm.logoType != "NONE" or
              # accounts for intricacy of custom object
              (cm.brickType == "CUSTOM" and (not b280() or len(cm.customObject1.evaluated_get(bpy.context.view_layer.depsgraph).data.vertices) > 50)) or
              # low exposed underside detail
              cm.exposedUndersideDetail not in ("FLAT", "LOW") or
              # no hidden underside detail
              cm.hiddenUndersideDetail != "FLAT" or
              # not using source materials
              (cm.materialType == "SOURCE" and cm.useUVMap and len(source.data.uv_layers) > 0)))


def createNewBricks(source, parent, source_details, dimensions, refLogo, logo_details, action, split=True, cm=None, curFrame=None, bricksDict=None, keys="ALL", clearExistingCollection=True, selectCreated=False, printStatus=True, tempBrick=False, redraw=False, origSource=None):
    """ gets/creates bricksDict, runs makeBricks, and caches the final bricksDict """
    scn, cm, n = getActiveContextInfo(cm=cm)
    brickScale, customData = getArgumentsForBricksDict(cm, source=source, dimensions=dimensions)
    updateCursor = action in ("CREATE", "UPDATE_MODEL")
    uv_images = getUVImages(source) if cm.materialType == "SOURCE" and cm.useUVMap and len(source.data.uv_layers) > 0 else {}  # get uv_layer image and pixels for material calculation
    if bricksDict is None:
        # load bricksDict from cache
        bricksDict = getBricksDict(cm, dType=action, curFrame=curFrame)
        loadedFromCache = bricksDict is not None
        # if not loaded, new bricksDict must be created
        if not loadedFromCache:
            # multiply brickScale by offset distance
            brickScale2 = brickScale if cm.brickType != "CUSTOM" else vec_mult(brickScale, Vector(cm.distOffset))
            # create new bricksDict
            bricksDict = makeBricksDict(source, source_details, brickScale2, uv_images, cursorStatus=updateCursor)
    else:
        loadedFromCache = True
    # reset all values for certain keys in bricksDict dictionaries
    if cm.buildIsDirty and loadedFromCache:
        threshold = getThreshold(cm)
        shellThicknessChanged = cm.lastShellThickness != cm.shellThickness
        for kk in bricksDict:
            bD = bricksDict[kk]
            if keys == "ALL" or kk in keys:
                bD["size"] = None
                bD["parent"] = None
                bD["top_exposed"] = None
                bD["bot_exposed"] = None
                if shellThicknessChanged:
                    bD["draw"] = bD["val"] >= threshold
            else:
                # don't merge bricks not in 'keys'
                bD["attempted_merge"] = True
    elif redraw:
        for kk in keys:
            bricksDict[kk]["attempted_merge"] = False
    if (not loadedFromCache or cm.internalIsDirty) and cm.calcInternals:
        updateInternal(bricksDict, cm, keys, clearExisting=loadedFromCache)
        cm.buildIsDirty = True
    # update materials in bricksDict
    if cm.materialType != "NONE" and (cm.materialIsDirty or cm.matrixIsDirty or cm.animIsDirty): bricksDict = updateMaterials(bricksDict, source, uv_images, keys, curFrame)
    # make bricks
    coll_name = "Bricker_%(n)s_bricks_f_%(curFrame)s" % locals() if curFrame is not None else "Bricker_%(n)s_bricks" % locals()
    bricksCreated, bricksDict = makeBricks(source, parent, refLogo, logo_details, dimensions, bricksDict, action, cm=cm, split=split, brickScale=brickScale, customData=customData, coll_name=coll_name, clearExistingCollection=clearExistingCollection, frameNum=curFrame, cursorStatus=updateCursor, keys=keys, printStatus=printStatus, tempBrick=tempBrick, redraw=redraw)
    if selectCreated and len(bricksCreated) > 0:
        select(bricksCreated)
    # store current bricksDict to cache
    cacheBricksDict(action, cm, bricksDict, curFrame=curFrame)
    return coll_name, bricksCreated


def transformBricks(bColl, cm, parent, source, sourceDup_details, action):
    # if using local orientation and creating model for first time
    if cm.useLocalOrient and action == "CREATE":
        obj = parent if cm.splitModel else bColl.objects[0]
        source_details = bounds(source)
        lastMode = source.rotation_mode
        obj.rotation_mode = "XYZ"
        source.rotation_mode = obj.rotation_mode
        obj.rotation_euler = source.rotation_euler
        obj.rotation_mode = lastMode
        source["local_orient_offset"] = source_details.mid - sourceDup_details.mid
        obj.location += Vector(source["local_orient_offset"])
    # if model was split but isn't now
    if cm.lastSplitModel and not cm.splitModel:
        # transfer transformation of parent to object
        parent.rotation_mode = "XYZ"
        for obj in bColl.objects:
            obj.location = parent.location
            obj.rotation_mode = parent.rotation_mode
            obj.rotation_euler.rotate(parent.rotation_euler)
            obj.scale = parent.scale
        # reset parent transformation
        parent.location = (0, 0, 0)
        parent.rotation_euler = Euler((0, 0, 0))
        cm.transformScale = 1
        parent.scale = (1, 1, 1)
    # if model is not split
    elif not cm.splitModel:
        # apply stored transformation to bricks
        applyTransformData(cm, bColl.objects)
    # if model wasn't split but is now
    elif not cm.lastSplitModel:
        # apply stored transformation to parent of bricks
        applyTransformData(cm, parent)
    obj = bColl.objects[0] if len(bColl.objects) > 0 else None
    if obj is None:
        return
    # if model contains armature, lock the location, rotation, and scale of created bricks object
    if not cm.splitModel and cm.armature:
        obj.lock_location = (True, True, True)
        obj.lock_rotation = (True, True, True)
        obj.lock_scale    = (True, True, True)


def finishAnimation(cm):
    scn, cm, n = getActiveContextInfo(cm=cm)
    wm = bpy.context.window_manager
    wm.progress_end()

    # link animation frames to animation collection
    anim_coll = getAnimColl(n)
    for cn in getCollections(cm, typ="ANIM"):
        if b280():
            if cn.name not in anim_coll.children:
                anim_coll.children.link(cn)
        else:
            for obj in cn.objects:
                safeLink(obj)
                if obj.name not in anim_coll.objects.keys():
                    anim_coll.objects.link(obj)
    return anim_coll


def linkBrickCollection(cm, coll):
    cm.collection = coll
    source = cm.source_obj
    if b280():
        for item in source.stored_parents:
            if coll.name not in item.collection.children:
                item.collection.children.link(coll)
    else:
        [safeLink(obj) for obj in coll.objects]
