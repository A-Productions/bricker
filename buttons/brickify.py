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
import random
import time
import bmesh
import os
from os.path import dirname, abspath
import sys
import math
import shutil
import json
import marshal

# Blender imports
import bpy
from mathutils import Matrix, Vector, Euler
from bpy.props import *

# Addon imports
from .customize.undo_stack import *
from .delete_model import BRICKER_OT_delete_model
from .bevel import BRICKER_OT_bevel
from .cache import *
from ..lib.bricksDict import *
from ..lib.background_processing.classes.JobManager import JobManager
from ..functions import *
from ..functions.brickify_utils import *


class BRICKER_OT_brickify(bpy.types.Operator):
    """Create brick sculpture from source object mesh"""
    bl_idname = "bricker.brickify"
    bl_label = "Create/Update Brick Model from Source Object"
    bl_options = {"REGISTER", "UNDO"}

    ################################################
    # Blender Operator methods

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        scn = bpy.context.scene
        if scn.cmlist_index == -1:
            return False
        cm = scn.cmlist[scn.cmlist_index]
        # return brickifyShouldRun(cm)
        return True

    def modal(self, context, event):
        if event.type == "TIMER":
            try:
                scn, cm, n = getActiveContextInfo(cm=self.cm)
                remaining_jobs = self.JobManager.num_pending_jobs() + self.JobManager.num_running_jobs()
                for job in self.jobs.copy():
                    # cancel if model was deleted before process completed
                    if scn in self.source.users_scene:
                        break
                    animAction = "ANIM" in self.action
                    frame = int(job.split("__")[-1]) if animAction else None
                    objFrameStr = "_f_%(frame)s" % locals() if animAction else ""
                    self.JobManager.process_job(job, debug_level=self.debug_level, overwrite_data=True)
                    if self.JobManager.job_complete(job):
                        if animAction: self.report({"INFO"}, "Completed frame %(frame)s of model '%(n)s'" % locals())
                        # cache bricksDict
                        retrieved_data = self.JobManager.get_retrieved_python_data(job)
                        bricksDict = None if retrieved_data["bricksDict"] in ("", "null") else marshal.loads(bytes.fromhex(retrieved_data["bricksDict"]))
                        cm.brickSizesUsed = retrieved_data["brickSizesUsed"]
                        cm.brickTypesUsed = retrieved_data["brickTypesUsed"]
                        if bricksDict is not None: cacheBricksDict(self.action, cm, bricksDict[str(frame)] if animAction else bricksDict, curFrame=frame)
                        # process retrieved bricker data
                        bricker_parent = bpy.data.objects.get("Bricker_%(n)s_parent%(objFrameStr)s" % locals())
                        safeLink(bricker_parent) # updates stale bricker_parent location
                        safeUnlink(bricker_parent) # adds fake user to parent
                        bricker_bricks_coll = bpy_collections()["Bricker_%(n)s_bricks%(objFrameStr)s" % locals()]
                        for brick in bricker_bricks_coll.objects:
                            brick.parent = bricker_parent
                            # for i,mat_slot in enumerate(brick.material_slots):
                            #     mat = mat_slot.material
                            #     if mat is None:
                            #         continue
                            #     origMat = bpy.data.materials.get(mat.name[:-4])
                            #     if origMat is not None:
                            #         brick.material_slots[i].material = origMat
                            #         mat.user_remap(origMat)
                            #         bpy.data.materials.remove(mat)
                            if not b280():
                                safeLink(brick)
                                if animAction:
                                    # hide obj unless on scene current frame
                                    adjusted_frame_current = getAnimAdjustedFrame(scn.frame_current, cm.lastStartFrame, cm.lastStopFrame)
                                    brick.hide        = frame != adjusted_frame_current
                                    brick.hide_render = frame != adjusted_frame_current
                        if animAction:
                            bricker_parent.parent = cm.parent_obj
                            if b280():
                                # link animation frames to animation collection and hide if not active
                                anim_coll = getAnimColl(n)
                                if bricker_bricks_coll.name not in anim_coll.children:
                                    anim_coll.children.link(bricker_bricks_coll)
                                # hide obj unless on scene current frame
                                adjusted_frame_current = getAnimAdjustedFrame(scn.frame_current, cm.lastStartFrame, cm.lastStopFrame)
                                bricker_bricks_coll.hide_viewport = frame != adjusted_frame_current
                                bricker_bricks_coll.hide_render   = frame != adjusted_frame_current
                            # incriment numAnimatedFrames and remove job
                            cm.numAnimatedFrames += 1
                            self.completed_frames.append(frame)
                            if not b280(): [safeLink(obj) for obj in bricker_bricks_coll.objects]
                        else:
                            linkBrickCollection(cm, bricker_bricks_coll)
                        self.jobs.remove(job)
                    elif self.JobManager.job_dropped(job):
                        errormsg = self.JobManager.get_issue_string(job)
                        print_exception("Bricker log", errormsg=errormsg)
                        reportFrameStr = " frame %(frame)s of" % locals() if animAction else ""
                        self.report({"WARNING"}, "Dropped%(reportFrameStr)s model '%(n)s'" % locals())
                        tag_redraw_areas("VIEW_3D")
                        if animAction: cm.numAnimatedFrames += 1
                        self.jobs.remove(job)
                # cancel and save finished frames if stopped
                if cm.stopBackgroundProcess:
                    if "ANIM" in self.action and self.JobManager.num_completed_jobs() > 0:
                        updatedStopFrame = False
                        # set end frame to last consecutive completed frame and toss non-consecutive frames
                        for frame in range(cm.lastStartFrame, cm.lastStopFrame + 1):
                            if frame not in self.completed_frames and not updatedStopFrame:
                                # set end frame to last consecutive completed frame
                                updatedStopFrame = True
                                cm.lastStopFrame = frame - 1
                                cm.stopFrame = frame - 1
                            if frame in self.completed_frames and updatedStopFrame:
                                # remove frames that cannot be saved
                                bricker_parent = bpy.data.objects.get("Bricker_%(n)s_parent_f_%(frame)s" % locals())
                                delete(bricker_parent)
                                bricker_bricks_coll = bpy_collections().get("Bricker_%(n)s_bricks_f_%(frame)s" % locals())
                                delete(bricker_bricks_coll.objects)
                                bpy_collections().remove(bricker_bricks_coll)
                        for frame in range(cm.lastStartFrame, cm.lastStopFrame + 1):
                            bricker_bricks_coll = bpy_collections().get("Bricker_%(n)s_bricks_f_%(frame)s" % locals())
                            # hide obj unless on scene current frame
                            adjusted_frame_current = getAnimAdjustedFrame(scn.frame_current, cm.lastStartFrame, cm.lastStopFrame)
                            if b280():
                                bricker_bricks_coll.hide_viewport = frame != adjusted_frame_current
                                bricker_bricks_coll.hide_render   = frame != adjusted_frame_current
                            elif frame != adjusted_frame_current:
                                [hide(obj) for obj in bricker_bricks_coll.objects]
                            else:
                                [unhide(obj) for obj in bricker_bricks_coll.objects]
                        # finish animation and kill running jobs
                        finishAnimation(self.cm)
                    else:
                        bpy.ops.bricker.delete_model()
                    cm.stopBackgroundProcess = False
                    self.cancel(context)
                    return {"CANCELLED"}
                # cancel if model was deleted before process completed
                if scn in self.source.users_scene:
                    self.cancel(context)
                    return {"CANCELLED"}
                # finish if all jobs completed
                elif self.JobManager.jobs_complete() or (remaining_jobs == 0 and self.JobManager.num_completed_jobs() > 0):
                    if "ANIM" in self.action:
                        finishAnimation(self.cm)
                    self.report({"INFO"}, "Brickify background process complete for model '%(n)s'" % locals())
                    stopwatch("Total Time Elapsed", self.start_time, precision=2)
                    self.finish(context, cm)
                    return {"FINISHED"}
                elif remaining_jobs == 0:
                    self.report({"WARNING"}, "Background process failed for model '%(n)s'. Try disabling background processing in the Bricker addon preferences." % locals())
                    cm.stopBackgroundProcess = True
            except:
                bricker_handle_exception()
                return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def execute(self, context):
        scn, cm, _ = getActiveContextInfo()
        wm = bpy.context.window_manager
        wm.Bricker_runningBlockingOperation = True
        try:
            if self.splitBeforeUpdate:
                cm.splitModel = True
            if cm.brickifyingInBackground:
                if cm.animated or cm.modelCreated:
                    bpy.ops.bricker.delete_model()
                self.action = "CREATE" if self.action == "UPDATE_MODEL" else "ANIMATE"
            cm.version = bpy.props.bricker_version
            previously_animated = cm.animated
            previously_model_created = cm.modelCreated
            success = self.runBrickify(context)
            if not success: return {"CANCELLED"}
        except KeyboardInterrupt:
            if self.action in ("CREATE", "ANIMATE"):
                for obj_n in self.createdObjects:
                    obj = bpy.data.objects.get(obj_n)
                    if obj:
                        bpy.data.objects.remove(obj, do_unlink=True)
                for cn in getCollections(cm, typ="MODEL" if self.action == "CREATE" else "ANIM"):
                    if cn: bpy_collections().remove(cn, do_unlink=True)
                if self.source:
                    self.source.protected = False
                    select(self.source, active=True)
                cm.animated = previously_animated
                cm.modelCreated = previously_model_created
            self.report({"WARNING"}, "Process forcably interrupted with 'KeyboardInterrupt'")
        except:
            bricker_handle_exception()
        wm.Bricker_runningBlockingOperation = False
        if self.brickifyInBackground:
            # create timer for modal
            self._timer = wm.event_timer_add(0.5, window=bpy.context.window)
            wm.modal_handler_add(self)
            return {"RUNNING_MODAL"}
        else:
            stopwatch("Total Time Elapsed", self.start_time, precision=2)
            return {"FINISHED"}

    def finish(self, context, cm):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        cm.brickifyingInBackground = False

    def cancel(self, context):
        scn, cm, n = getActiveContextInfo(self.cm)
        self.finish(context, cm)
        if self.JobManager.num_running_jobs() + self.JobManager.num_pending_jobs() > 0:
            self.JobManager.kill_all()
            print("Background processes for '%(n)s' model killed" % locals())

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, _ = getActiveContextInfo()
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push('brickify', affected_ids=[cm.id])
        # initialize vars
        self.createdObjects = list()
        self.action = getAction(cm)
        self.source = cm.source_obj
        self.origFrame = scn.frame_current
        self.start_time = time.time()
        # initialize important vars
        self.JobManager = JobManager.get_instance(cm.id)
        self.JobManager.timeout = cm.backProcTimeout
        self.JobManager.max_workers = cm.maxWorkers
        self.JobManager.max_attempts = 1
        self.debug_level = 0 if "ANIM" in self.action else 1 # or bpy.props.Bricker_developer_mode == 0 else 1
        self.completed_frames = []
        self.brickerAddonPath = get_addon_directory()
        self.jobs = list()
        self.cm = cm
        # set up model dimensions variables sX, sY, and sZ
        r = getModelResolution(self.source, cm)
        if get_addon_preferences().brickifyInBackground == "AUTO" and r is not None:
            self.brickifyInBackground = shouldBrickifyInBackground(cm, r, self.action)
        else:
            self.brickifyInBackground = get_addon_preferences().brickifyInBackground == "ON"

    ###################################################
    # class variables

    splitBeforeUpdate = BoolProperty(default=False)

    #############################################
    # class methods

    def runBrickify(self, context):
        # set up variables
        scn, cm, n = getActiveContextInfo(self.cm)
        self.undo_stack.iterateStates(cm)

        # ensure that Bricker can run successfully
        if not self.isValid(scn, cm, n, self.source):
            return False

        # initialize variables
        self.source.cmlist_id = cm.id
        matrixDirty = matrixReallyIsDirty(cm)
        if self.brickifyInBackground:
            cm.brickifyingInBackground = True

        if b280():
            # store parent collections to source
            self.source.stored_parents.clear()
            if len(self.source.users_collection) > 0:
                # use parent collections of source
                linkedColls = self.source.users_collection
            else:
                # use parent collections of brick collection
                brickColl = cm.collection
                linkedColls = [cn for cn in bpy.data.collections if brickColl.name in cn.children]
            for cn in linkedColls:
                self.source.stored_parents.add().collection = cn

        # # check if source object is smoke simulation domain
        cm.isSmoke = is_smoke(self.source)
        if cm.isSmoke != cm.lastIsSmoke:
            cm.matrixIsDirty = True

        # clear cache if updating from previous version
        if createdWithUnsupportedVersion(cm) and "UPDATE" in self.action:
            BRICKER_OT_clear_cache.clearCache(cm)
            cm.matrixIsDirty = True

        # make sure matrix really is dirty
        if cm.matrixIsDirty:
            if not matrixDirty and getBricksDict(cm) is not None:
                cm.matrixIsDirty = False

        if b280():
            # TODO: potentially necessary to ensure current View Layer includes collection with self.source
            # TODO: potentially necessary to ensure self.source (and its parent collections) are viewable?
            pass
        else:
            # set layers to source layers
            oldLayers = list(scn.layers)
            sourceLayers = list(self.source.layers)
            if oldLayers != sourceLayers:
                setLayers(sourceLayers)

        if "ANIM" not in self.action:
            self.brickifyModel(scn, cm, n, matrixDirty)
        else:
            self.brickifyAnimation(scn, cm, n, matrixDirty)
            anim_coll = getAnimColl(n)
            linkBrickCollection(cm, anim_coll)
            cm.animIsDirty = False

        # set cmlist_id for all created objects
        for obj_name in self.createdObjects:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                obj.cmlist_id = cm.id

        # # set final variables
        cm.lastlogoType = cm.logoType
        cm.lastSplitModel = cm.splitModel
        cm.lastBrickType = cm.brickType
        cm.lastLegalBricksOnly = cm.legalBricksOnly
        cm.lastMaterialType = cm.materialType
        cm.lastShellThickness = cm.shellThickness
        cm.lastInternalSupports = cm.internalSupports
        cm.lastMatShellDepth = cm.matShellDepth
        cm.lastMatrixSettings = getMatrixSettings()
        cm.lastIsSmoke = cm.isSmoke
        cm.materialIsDirty = False
        cm.modelIsDirty = False
        cm.buildIsDirty = False
        cm.bricksAreDirty = False
        cm.matrixIsDirty = False
        cm.matrixLost = False
        cm.internalIsDirty = False
        cm.modelCreated = "ANIM" not in self.action
        cm.animated = "ANIM" in self.action
        cm.exposeParent = False

        if cm.animated and not self.brickifyInBackground:
            finishAnimation(self.cm)

        # unlink source from scene
        safeUnlink(self.source)
        if not b280():
            # reset layers
            if oldLayers != sourceLayers:
                setLayers(oldLayers)

        disableRelationshipLines()

        return True

    def brickifyModel(self, scn, cm, n, matrixDirty):
        """ create brick model """
        # set up variables
        source = None

        if self.action == "CREATE":
            # set modelCreatedOnFrame
            cm.modelCreatedOnFrame = scn.frame_current
        else:
            if self.origFrame != cm.modelCreatedOnFrame:
                scn.frame_set(cm.modelCreatedOnFrame)

        # if there are no changes to apply, simply return "FINISHED"
        if self.action == "UPDATE_MODEL" and not updateCanRun("MODEL"):
            return{"FINISHED"}

        if (matrixDirty or self.action != "UPDATE_MODEL") and cm.customized:
            cm.customized = False

        # delete old bricks if present
        if self.action.startswith("UPDATE") and (matrixDirty or cm.buildIsDirty or cm.lastSplitModel != cm.splitModel or self.brickifyInBackground):
            # skip source, dupes, and parents
            skipTransAndAnimData = cm.animated or (cm.splitModel or cm.lastSplitModel) and (matrixDirty or cm.buildIsDirty)
            bpy.props.bricker_trans_and_anim_data = BRICKER_OT_delete_model.cleanUp("MODEL", skipDupes=True, skipParents=True, skipSource=True, skipTransAndAnimData=skipTransAndAnimData)[4]
        else:
            storeTransformData(cm, None)
            bpy.props.bricker_trans_and_anim_data = []

        if self.action == "CREATE":
            # duplicate source
            sourceDup = duplicate(self.source, link_to_scene=True)
            sourceDup.name = self.source.name + "__dup__"
            if cm.useLocalOrient:
                sourceDup.rotation_mode = "XYZ"
                sourceDup.rotation_euler = Euler((0, 0, 0))
            self.createdObjects.append(sourceDup.name)
            deselect(self.source)
            # remove modifiers and constraints
            for mod in sourceDup.modifiers:
                sourceDup.modifiers.remove(mod)
            for constraint in sourceDup.constraints:
                sourceDup.constraints.remove(constraint)
            # remove sourceDup parent
            if sourceDup.parent:
                parent_clear(sourceDup)
            # send to new mesh
            if not cm.isSmoke:
                sourceDup.data = new_mesh_from_object(self.source)
            # apply transformation data
            apply_transform(sourceDup)
            sourceDup.animation_data_clear()
            update_depsgraph()
        else:
            # get previously created source duplicate
            sourceDup = bpy.data.objects.get(n + "__dup__")
        # if duplicate not created, sourceDup is just original source
        sourceDup = sourceDup or self.source

        # link sourceDup if it isn't in scene
        if sourceDup.name not in scn.objects.keys():
            safeLink(sourceDup)
            update_depsgraph()

        # get parent object
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        parent = bpy.data.objects.get(Bricker_parent_on)
        # if parent doesn't exist, get parent with new location
        sourceDup_details = bounds(sourceDup)
        parentLoc = sourceDup_details.mid
        if parent is None:
            parent = getNewParent(Bricker_parent_on, parentLoc)
            cm.parent_name = parent.name
        cm.parent_obj = parent
        parent["loc_diff"] = self.source.location - parentLoc
        self.createdObjects.append(parent.name)

        # create, transform, and bevel bricks
        if self.brickifyInBackground:
            filename = bpy.path.basename(bpy.data.filepath)[:-6]
            curJob = "%(filename)s__%(n)s" % locals()
            script = os.path.join(self.brickerAddonPath, "lib", "brickify_in_background_template.py")
            jobAdded, msg = self.JobManager.add_job(curJob, script=script, passed_data={"frame":None, "cmlist_index":scn.cmlist_index, "action":self.action}, use_blend_file=True)
            if not jobAdded: raise Exception(msg)
            self.jobs.append(curJob)
        else:
            bColl = self.brickifyActiveFrame(self.action)
            linkBrickCollection(cm, bColl)
            # select the bricks object unless it's massive
            if not cm.splitModel and len(bColl.objects) > 0:
                obj = bColl.objects[0]
                if len(obj.data.vertices) < 500000:
                    select(obj, active=True)

        # unlink source duplicate if created
        if sourceDup != self.source:
            safeUnlink(sourceDup)

        # set active frame to original active frame
        if self.action != "CREATE" and scn.frame_current != self.origFrame:
            scn.frame_set(self.origFrame)

        cm.lastSourceMid = vecToStr(parentLoc)

    def brickifyAnimation(self, scn, cm, n, matrixDirty):
        """ create brick animation """
        # set up variables
        scn, cm, n = getActiveContextInfo()
        objsToSelect = []

        if self.action == "UPDATE_ANIM":
            safeLink(self.source)
            self.source.name = n  # fixes issue with smoke simulation cache

        # if there are no changes to apply, simply return "FINISHED"
        self.updatedFramesOnly = False
        if self.action == "UPDATE_ANIM" and not updateCanRun("ANIMATION"):
            if cm.animIsDirty:
                self.updatedFramesOnly = True
            else:
                return {"FINISHED"}

        if self.brickifyInBackground:
            cm.numAnimatedFrames = 0
            cm.framesToAnimate = (cm.stopFrame - cm.startFrame + 1)

        if (self.action == "ANIMATE" or cm.matrixIsDirty or cm.animIsDirty) and not self.updatedFramesOnly:
            BRICKER_OT_clear_cache.clearCache(cm, brick_mesh=False)

        if cm.splitModel:
            cm.splitModel = False

        # delete old bricks if present
        if self.action.startswith("UPDATE") and (matrixDirty or cm.buildIsDirty or cm.lastSplitModel != cm.splitModel or self.updatedFramesOnly):
            preservedFrames = None
            if self.updatedFramesOnly:
                # preserve duplicates, parents, and bricks for frames that haven't changed
                preservedFrames = [cm.startFrame, cm.stopFrame]
            BRICKER_OT_delete_model.cleanUp("ANIMATION", skipDupes=not self.updatedFramesOnly, skipParents=not self.updatedFramesOnly, preservedFrames=preservedFrames, source_name=self.source.name)

        # get parent object
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        self.parent0 = bpy.data.objects.get(Bricker_parent_on)
        if self.parent0 is None:
            self.parent0 = getNewParent(Bricker_parent_on, self.source.location)
            cm.parent_obj = self.parent0
        self.createdObjects.append(self.parent0.name)

        # begin drawing status to cursor
        wm = bpy.context.window_manager
        wm.progress_begin(0, cm.stopFrame + 1 - cm.startFrame)

        # prepare duplicate objects for animation
        duplicates = getDuplicateObjects(scn, cm, self.action, cm.startFrame, cm.stopFrame)

        filename = bpy.path.basename(bpy.data.filepath)[:-6]
        overwrite_blend = True
        # iterate through frames of animation and generate Brick Model
        for curFrame in range(cm.startFrame, cm.stopFrame + 1):
            if self.updatedFramesOnly and cm.lastStartFrame <= curFrame and curFrame <= cm.lastStopFrame:
                print("skipped frame %(curFrame)s" % locals())
                self.completed_frames.append(curFrame)
                cm.framesToAnimate -= 1
                continue
            if self.brickifyInBackground:
                curJob = "%(filename)s__%(n)s__%(curFrame)s" % locals()
                script = os.path.join(self.brickerAddonPath, "lib", "brickify_in_background_template.py")
                jobAdded, msg = self.JobManager.add_job(curJob, script=script, passed_data={"frame":curFrame, "cmlist_index":scn.cmlist_index, "action":self.action}, use_blend_file=True, overwrite_blend=overwrite_blend)
                if not jobAdded: raise Exception(msg)
                self.jobs.append(curJob)
                overwrite_blend = False
            else:
                success = self.brickifyCurrentFrame(curFrame, self.action)
                if not success:
                    break

        # unlink source duplicates
        for obj in duplicates.values():
            safeUnlink(obj)

        cm.lastStartFrame = cm.startFrame
        cm.lastStopFrame = cm.stopFrame

    @staticmethod
    def brickifyCurrentFrame(curFrame, action, inBackground=False):
        scn, cm, n = getActiveContextInfo()
        wm = bpy.context.window_manager
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        parent0 = bpy.data.objects.get(Bricker_parent_on)
        origFrame = scn.frame_current
        if inBackground and cm.isSmoke:
            smokeMod = [mod for mod in cm.source_obj.modifiers if mod.type == "SMOKE"][0]
            point_cache = smokeMod.domain_settings.point_cache
            point_cache.name = str(curFrame)
            for frame in range(point_cache.frame_start, curFrame):
                scn.frame_set(frame)
        scn.frame_set(origFrame)
        # get duplicated source
        source = bpy.data.objects.get("Bricker_%(n)s_f_%(curFrame)s" % locals())
        # get source info to update
        if inBackground and scn not in source.users_scene:
            safeLink(source)
            update_depsgraph()

        # get source_details and dimensions
        source_details, dimensions = getDetailsAndBounds(source)

        # update refLogo
        logo_details, refLogo = getLogo(scn, cm, dimensions)

        # set up parent for this layer
        # TODO: Remove these from memory in the delete function, or don't use them at all
        p_name = "%(Bricker_parent_on)s_f_%(curFrame)s" % locals()
        parent = bpy.data.objects.get(p_name)
        if parent is None:
            parent = bpy.data.objects.new(p_name, None)
            parent.location = source_details.mid - parent0.location
            parent.parent = parent0
            parent.use_fake_user = True
            parent.update_tag()  # TODO: is it necessary to update this?

        # create new bricks
        try:
            coll_name, _ = createNewBricks(source, parent, source_details, dimensions, refLogo, logo_details, action, split=cm.splitModel, curFrame=curFrame, clearExistingCollection=False, origSource=cm.source_obj, selectCreated=False)
        except KeyboardInterrupt:
            if curFrame != cm.startFrame:
                wm.progress_end()
                cm.lastStartFrame = cm.startFrame
                cm.lastStopFrame = curFrame - 1
                cm.animated = True
            return False

        # get collection with created bricks
        cur_frame_coll = bpy_collections().get(coll_name)
        if cur_frame_coll is not None and len(cur_frame_coll.objects) > 0:
            # get allBricksObject
            obj = cur_frame_coll.objects[0]
            # hide collection/obj unless on scene current frame
            adjusted_frame_current = getAnimAdjustedFrame(scn.frame_current, cm.startFrame, cm.stopFrame)
            if curFrame != adjusted_frame_current:
                hide(cur_frame_coll if b280() else obj)
            else:
                unhide(cur_frame_coll if b280() else obj)
            # lock location, rotation, and scale of created bricks
            obj.lock_location = (True, True, True)
            obj.lock_rotation = (True, True, True)
            obj.lock_scale    = (True, True, True)
            # add bevel if it was previously added
            if cm.bevelAdded:
                BRICKER_OT_bevel.runBevelAction([obj], cm)

        wm.progress_update(curFrame-cm.startFrame)
        print('-'*100)
        print("completed frame " + str(curFrame))
        print('-'*100)
        return True

    @staticmethod
    def brickifyActiveFrame(action):
        # initialize vars
        scn, cm, n = getActiveContextInfo()
        parent = cm.parent_obj
        sourceDup = bpy.data.objects.get(cm.source_obj.name + "__dup__")
        sourceDup_details, dimensions = getDetailsAndBounds(sourceDup)

        # update refLogo
        logo_details, refLogo = getLogo(scn, cm, dimensions)

        # create new bricks
        coll_name, _ = createNewBricks(sourceDup, parent, sourceDup_details, dimensions, refLogo, logo_details, action, split=cm.splitModel, curFrame=None)

        bColl = bpy_collections().get(coll_name)
        if bColl:
            # transform bricks to appropriate location
            transformBricks(bColl, cm, parent, cm.source_obj, sourceDup_details, action)
            # apply old animation data to objects
            for d0 in bpy.props.bricker_trans_and_anim_data:
                obj = bpy.data.objects.get(d0["name"])
                if obj is not None:
                    obj.location = d0["loc"]
                    obj.rotation_euler = d0["rot"]
                    obj.scale = d0["scale"]
                    if d0["action"] is not None:
                        obj.animation_data_create()
                        obj.animation_data.action = d0["action"]

        # add bevel if it was previously added
        if cm.bevelAdded:
            bricks = getBricks(cm, typ="MODEL")
            BRICKER_OT_bevel.runBevelAction(bricks, cm)

        return bColl

    def isValid(self, scn, cm, source_name, source):
        """ returns True if brickify action can run, else report WARNING/ERROR and return False """
        # ensure custom object(s) are valid
        if (cm.brickType == "CUSTOM" or cm.hasCustomObj1 or cm.hasCustomObj2 or cm.hasCustomObj3):
            warningMsg = customValidObject(cm)
            if warningMsg is not None:
                self.report({"WARNING"}, warningMsg)
                return False
        # ensure source is defined
        if source is None:
            self.report({"WARNING"}, "Source object '%(source_name)s' could not be found" % locals())
            return False
        # ensure source name isn't too long
        if len(source_name) > 39:
            self.report({"WARNING"}, "Source object name too long (must be <= 39 characters)")
            return False
        # verify Blender file is saved if running in background
        if self.brickifyInBackground and bpy.data.filepath == "":
            self.report({"WARNING"}, "Please save the file first")
            return False
        # ensure custom material exists
        if cm.materialType == "CUSTOM" and cm.customMat is None:
            self.report({"WARNING"}, "Please choose a material in the 'Bricker > Materials' tab")
            return False
        if cm.materialType == "SOURCE" and cm.colorSnap == "ABS":
            # ensure ABS Plastic materials are installed
            if not brick_materials_installed():
                self.report({"WARNING"}, "ABS Plastic Materials must be installed from Blender Market")
                return False
            # ensure ABS Plastic materials is updated to latest version
            if not hasattr(bpy.props, "abs_mat_properties"):
                self.report({"WARNING"}, "Requires ABS Plastic Materials v2.1.1 or later – please update via the addon preferences")
                return False
            # ensure ABS Plastic materials UI list is populated
            matObj = getMatObject(cm.id, typ="ABS")
            if matObj is None:
                matObj = createNewMatObjs(cm.id)[1]
            if len(matObj.data.materials) == 0:
                self.report({"WARNING"}, "No ABS Plastic Materials found in Materials to be used")
                return False

        brick_coll_name = "Bricker_%(source_name)s_bricks" % locals()
        if self.action in ("CREATE", "ANIMATE"):
            # verify function can run
            if brick_coll_name in bpy_collections().keys():
                self.report({"WARNING"}, "Brickified Model already created.")
                return False
            # verify source exists and is of type mesh
            if source_name == "":
                self.report({"WARNING"}, "Please select a mesh to Brickify")
                return False
            # ensure source is not bricker model
            if source.isBrick or source.isBrickifiedObject:
                self.report({"WARNING"}, "Please bake the 'Bricker' source model before brickifying (Bricker > Bake/Export > Bake Model).")
                return False
            # ensure source exists
            if source is None:
                self.report({"WARNING"}, "'%(source_name)s' could not be found" % locals())
                return False
            # ensure object data is mesh
            if source.type != "MESH":
                self.report({"WARNING"}, "Only 'MESH' objects can be Brickified. Please select another object (or press 'ALT-C to convert object to mesh).")
                return False
            # verify source is not a rigid body
            if source.rigid_body is not None and source.rigid_body.type == "ACTIVE":
                self.report({"WARNING"}, "First bake rigid body transformations to keyframes (SPACEBAR > Bake To Keyframes).")
                return False

        if self.action in ("ANIMATE", "UPDATE_ANIM"):
            # verify start frame is less than stop frame
            if cm.startFrame > cm.stopFrame:
                self.report({"ERROR"}, "Start frame must be less than or equal to stop frame (see animation tab below).")
                return False

        if self.action == "UPDATE_MODEL":
            # make sure 'Bricker_[source name]_bricks' collection exists
            if brick_coll_name not in bpy_collections().keys():
                self.report({"WARNING"}, "Brickified Model doesn't exist. Create one with the 'Brickify Object' button.")
                return False

        # check that custom logo object exists in current scene and is of type "MESH"
        if cm.logoType == "CUSTOM" and cm.brickType != "CUSTOM":
            if cm.logoObject is None:
                self.report({"WARNING"}, "Custom logo object not specified.")
                return False
            elif cm.logoObject.name == source_name:
                self.report({"WARNING"}, "Source object cannot be its own logo.")
                return False
            elif cm.logoObject.name.startswith("Bricker_%(source_name)s" % locals()):
                self.report({"WARNING"}, "Bricker object cannot be used as its own logo.")
                return False
            elif cm.logoObject.type != "MESH":
                self.report({"WARNING"}, "Custom logo object is not of type 'MESH'. Please select another object (or press 'ALT-C to convert object to mesh).")
                return False

        return True

    #############################################
