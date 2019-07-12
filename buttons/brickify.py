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
from ..lib.bricksdict import *
from ..lib.background_processing.classes.job_manager import JobManager
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
        # return brickify_should_run(cm)
        return True

    def modal(self, context, event):
        if event.type == "TIMER":
            try:
                scn, cm, n = get_active_context_info(cm=self.cm)
                remaining_jobs = self.job_manager.num_pending_jobs() + self.job_manager.num_running_jobs()
                for job in self.jobs.copy():
                    # cancel if model was deleted before process completed
                    if scn in self.source.users_scene:
                        break
                    animAction = "ANIM" in self.action
                    frame = int(job.split("__")[-1]) if animAction else None
                    objFrameStr = "_f_%(frame)s" % locals() if animAction else ""
                    self.job_manager.process_job(job, debug_level=self.debug_level, overwrite_data=True)
                    if self.job_manager.job_complete(job):
                        if animAction: self.report({"INFO"}, "Completed frame %(frame)s of model '%(n)s'" % locals())
                        # cache bricksdict
                        retrieved_data = self.job_manager.get_retrieved_python_data(job)
                        bricksdict = None if retrieved_data["bricksdict"] in ("", "null") else marshal.loads(bytes.fromhex(retrieved_data["bricksdict"]))
                        cm.brick_sizes_used = retrieved_data["brick_sizes_used"]
                        cm.brick_types_used = retrieved_data["brick_types_used"]
                        if bricksdict is not None: cache_bricks_dict(self.action, cm, bricksdict[str(frame)] if animAction else bricksdict, cur_frame=frame)
                        # process retrieved bricker data
                        bricker_parent = bpy.data.objects.get("Bricker_%(n)s_parent%(objFrameStr)s" % locals())
                        safe_link(bricker_parent) # updates stale bricker_parent location
                        safe_unlink(bricker_parent) # adds fake user to parent
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
                                safe_link(brick)
                                if animAction:
                                    # hide obj unless on scene current frame
                                    adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame)
                                    brick.hide        = frame != adjusted_frame_current
                                    brick.hide_render = frame != adjusted_frame_current
                        if animAction:
                            bricker_parent.parent = cm.parent_obj
                            if b280():
                                # link animation frames to animation collection and hide if not active
                                anim_coll = get_anim_coll(n)
                                if bricker_bricks_coll.name not in anim_coll.children:
                                    anim_coll.children.link(bricker_bricks_coll)
                                # hide obj unless on scene current frame
                                adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame)
                                bricker_bricks_coll.hide_viewport = frame != adjusted_frame_current
                                bricker_bricks_coll.hide_render   = frame != adjusted_frame_current
                            # incriment run_animated_frames and remove job
                            cm.run_animated_frames += 1
                            self.completed_frames.append(frame)
                            if not b280(): [safe_link(obj) for obj in bricker_bricks_coll.objects]
                        else:
                            link_brick_collection(cm, bricker_bricks_coll)
                        self.jobs.remove(job)
                    elif self.job_manager.job_dropped(job):
                        errormsg = self.job_manager.get_issue_string(job)
                        print_exception("Bricker log", errormsg=errormsg)
                        reportFrameStr = " frame %(frame)s of" % locals() if animAction else ""
                        self.report({"WARNING"}, "Dropped%(reportFrameStr)s model '%(n)s'" % locals())
                        tag_redraw_areas("VIEW_3D")
                        if animAction: cm.run_animated_frames += 1
                        self.jobs.remove(job)
                # cancel and save finished frames if stopped
                if cm.stop_background_process:
                    if "ANIM" in self.action and self.job_manager.num_completed_jobs() > 0:
                        updatedStopFrame = False
                        # set end frame to last consecutive completed frame and toss non-consecutive frames
                        for frame in range(cm.last_start_frame, cm.last_stop_frame + 1):
                            if frame not in self.completed_frames and not updatedStopFrame:
                                # set end frame to last consecutive completed frame
                                updatedStopFrame = True
                                cm.last_stop_frame = frame - 1
                                cm.stop_frame = frame - 1
                            if frame in self.completed_frames and updatedStopFrame:
                                # remove frames that cannot be saved
                                bricker_parent = bpy.data.objects.get("Bricker_%(n)s_parent_f_%(frame)s" % locals())
                                delete(bricker_parent)
                                bricker_bricks_coll = bpy_collections().get("Bricker_%(n)s_bricks_f_%(frame)s" % locals())
                                delete(bricker_bricks_coll.objects)
                                bpy_collections().remove(bricker_bricks_coll)
                        for frame in range(cm.last_start_frame, cm.last_stop_frame + 1):
                            bricker_bricks_coll = bpy_collections().get("Bricker_%(n)s_bricks_f_%(frame)s" % locals())
                            # hide obj unless on scene current frame
                            adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.last_start_frame, cm.last_stop_frame)
                            if b280():
                                bricker_bricks_coll.hide_viewport = frame != adjusted_frame_current
                                bricker_bricks_coll.hide_render   = frame != adjusted_frame_current
                            elif frame != adjusted_frame_current:
                                [hide(obj) for obj in bricker_bricks_coll.objects]
                            else:
                                [unhide(obj) for obj in bricker_bricks_coll.objects]
                        # finish animation and kill running jobs
                        finish_animation(self.cm)
                    else:
                        bpy.ops.bricker.delete_model()
                    cm.stop_background_process = False
                    self.cancel(context)
                    return {"CANCELLED"}
                # cancel if model was deleted before process completed
                if scn in self.source.users_scene:
                    self.cancel(context)
                    return {"CANCELLED"}
                # finish if all jobs completed
                elif self.job_manager.jobs_complete() or (remaining_jobs == 0 and self.job_manager.num_completed_jobs() > 0):
                    if "ANIM" in self.action:
                        finish_animation(self.cm)
                    self.report({"INFO"}, "Brickify background process complete for model '%(n)s'" % locals())
                    stopwatch("Total Time Elapsed", self.start_time, precision=2)
                    self.finish(context, cm)
                    return {"FINISHED"}
                elif remaining_jobs == 0:
                    self.report({"WARNING"}, "Background process failed for model '%(n)s'. Try disabling background processing in the Bricker addon preferences." % locals())
                    cm.stop_background_process = True
            except:
                bricker_handle_exception()
                return {"CANCELLED"}
        return {"PASS_THROUGH"}

    def execute(self, context):
        scn, cm, _ = get_active_context_info()
        wm = bpy.context.window_manager
        wm.bricker_running_blocking_operation = True
        try:
            if self.splitBeforeUpdate:
                cm.split_model = True
            if cm.brickifying_in_background:
                if cm.animated or cm.model_created:
                    bpy.ops.bricker.delete_model()
                self.action = "CREATE" if self.action == "UPDATE_MODEL" else "ANIMATE"
            cm.version = bpy.props.bricker_version
            previously_animated = cm.animated
            previously_model_created = cm.model_created
            success = self.runBrickify(context)
            if not success: return {"CANCELLED"}
        except KeyboardInterrupt:
            if self.action in ("CREATE", "ANIMATE"):
                for obj_n in self.created_objects:
                    obj = bpy.data.objects.get(obj_n)
                    if obj:
                        bpy.data.objects.remove(obj, do_unlink=True)
                for cn in get_collections(cm, typ="MODEL" if self.action == "CREATE" else "ANIM"):
                    if cn: bpy_collections().remove(cn, do_unlink=True)
                if self.source:
                    self.source.protected = False
                    select(self.source, active=True)
                cm.animated = previously_animated
                cm.model_created = previously_model_created
            self.report({"WARNING"}, "Process forcably interrupted with 'KeyboardInterrupt'")
        except:
            bricker_handle_exception()
        wm.bricker_running_blocking_operation = False
        if self.brickify_in_background:
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
        cm.brickifying_in_background = False

    def cancel(self, context):
        scn, cm, n = get_active_context_info(self.cm)
        self.finish(context, cm)
        if self.job_manager.num_running_jobs() + self.job_manager.num_pending_jobs() > 0:
            self.job_manager.kill_all()
            print("Background processes for '%(n)s' model killed" % locals())

    ################################################
    # initialization method

    def __init__(self):
        scn, cm, _ = get_active_context_info()
        # push to undo stack
        self.undo_stack = UndoStack.get_instance()
        self.undo_stack.undo_push("brickify", affected_ids=[cm.id])
        # initialize vars
        self.created_objects = list()
        self.action = get_action(cm)
        self.source = cm.source_obj
        self.origFrame = scn.frame_current
        self.start_time = time.time()
        # initialize important vars
        self.job_manager = JobManager.get_instance(cm.id)
        self.job_manager.timeout = cm.back_proc_timeout
        self.job_manager.max_workers = cm.max_workers
        self.job_manager.max_attempts = 1
        self.debug_level = 0 if "ANIM" in self.action else 1 # or bpy.props.Bricker_developer_mode == 0 else 1
        self.completed_frames = []
        self.bricker_addon_path = get_addon_directory()
        self.jobs = list()
        self.cm = cm
        # set up model dimensions variables sX, sY, and sZ
        r = get_model_resolution(self.source, cm)
        if get_addon_preferences().brickify_in_background == "AUTO" and r is not None:
            self.brickify_in_background = should_brickify_in_background(cm, r, self.action)
        else:
            self.brickify_in_background = get_addon_preferences().brickify_in_background == "ON"

    ###################################################
    # class variables

    splitBeforeUpdate = BoolProperty(default=False)

    #############################################
    # class methods

    def runBrickify(self, context):
        # set up variables
        scn, cm, n = get_active_context_info(self.cm)
        self.undo_stack.iterate_states(cm)

        # ensure that Bricker can run successfully
        if not self.isValid(scn, cm, n, self.source):
            return False

        # initialize variables
        self.source.cmlist_id = cm.id
        matrix_dirty = matrix_really_is_dirty(cm)
        if self.brickify_in_background:
            cm.brickifying_in_background = True

        if b280():
            # store parent collections to source
            self.source.stored_parents.clear()
            if len(self.source.users_collection) > 0:
                # use parent collections of source
                linkedColls = self.source.users_collection
            else:
                # use parent collections of brick collection
                brick_coll = cm.collection
                linkedColls = [cn for cn in bpy.data.collections if brick_coll.name in cn.children]
            for cn in linkedColls:
                self.source.stored_parents.add().collection = cn

        # # check if source object is smoke simulation domain
        cm.is_smoke = is_smoke(self.source)
        if cm.is_smoke != cm.last_is_smoke:
            cm.matrix_is_dirty = True

        # clear cache if updating from previous version
        if created_with_unsupported_version(cm) and "UPDATE" in self.action:
            BRICKER_OT_clear_cache.clear_cache(cm)
            cm.matrix_is_dirty = True

        # make sure matrix really is dirty
        if cm.matrix_is_dirty:
            if not matrix_dirty and get_bricksdict(cm) is not None:
                cm.matrix_is_dirty = False

        if b280():
            # TODO: potentially necessary to ensure current View Layer includes collection with self.source
            # TODO: potentially necessary to ensure self.source (and its parent collections) are viewable?
            pass
        else:
            # set layers to source layers
            oldLayers = list(scn.layers)
            sourceLayers = list(self.source.layers)
            if oldLayers != sourceLayers:
                set_layers(sourceLayers)

        if "ANIM" not in self.action:
            self.brickifyModel(scn, cm, n, matrix_dirty)
        else:
            self.brickifyAnimation(scn, cm, n, matrix_dirty)
            anim_coll = get_anim_coll(n)
            link_brick_collection(cm, anim_coll)
            cm.anim_is_dirty = False

        # set cmlist_id for all created objects
        for obj_name in self.created_objects:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                obj.cmlist_id = cm.id

        # # set final variables
        cm.lastlogo_type = cm.logo_type
        cm.last_split_model = cm.split_model
        cm.last_brick_type = cm.brick_type
        cm.last_legal_bricks_only = cm.legal_bricks_only
        cm.last_material_type = cm.material_type
        cm.last_shell_thickness = cm.shell_thickness
        cm.last_internal_supports = cm.internal_supports
        cm.last_mat_shell_depth = cm.mat_shell_depth
        cm.last_matrix_settings = get_matrix_settings()
        cm.last_is_smoke = cm.is_smoke
        cm.material_is_dirty = False
        cm.model_is_dirty = False
        cm.build_is_dirty = False
        cm.bricks_are_dirty = False
        cm.matrix_is_dirty = False
        cm.matrix_lost = False
        cm.internal_is_dirty = False
        cm.model_created = "ANIM" not in self.action
        cm.animated = "ANIM" in self.action
        cm.expose_parent = False

        if cm.animated and not self.brickify_in_background:
            finish_animation(self.cm)

        # unlink source from scene
        safe_unlink(self.source)
        if not b280():
            # reset layers
            if oldLayers != sourceLayers:
                set_layers(oldLayers)

        disable_relationship_lines()

        return True

    def brickifyModel(self, scn, cm, n, matrix_dirty):
        """ create brick model """
        # set up variables
        source = None

        if self.action == "CREATE":
            # set model_created_on_frame
            cm.model_created_on_frame = scn.frame_current
        else:
            if self.origFrame != cm.model_created_on_frame:
                scn.frame_set(cm.model_created_on_frame)

        # if there are no changes to apply, simply return "FINISHED"
        if self.action == "UPDATE_MODEL" and not update_can_run("MODEL"):
            return{"FINISHED"}

        if (matrix_dirty or self.action != "UPDATE_MODEL") and cm.customized:
            cm.customized = False

        # delete old bricks if present
        if self.action.startswith("UPDATE") and (matrix_dirty or cm.build_is_dirty or cm.last_split_model != cm.split_model or self.brickify_in_background):
            # skip source, dupes, and parents
            skip_trans_and_anim_data = cm.animated or (cm.split_model or cm.last_split_model) and (matrix_dirty or cm.build_is_dirty)
            bpy.props.bricker_trans_and_anim_data = BRICKER_OT_delete_model.cleanUp("MODEL", skipDupes=True, skipParents=True, skipSource=True, skip_trans_and_anim_data=skip_trans_and_anim_data)[4]
        else:
            store_transform_data(cm, None)
            bpy.props.bricker_trans_and_anim_data = []

        if self.action == "CREATE":
            # duplicate source
            source_dup = duplicate(self.source, link_to_scene=True)
            source_dup.name = self.source.name + "__dup__"
            if cm.use_local_orient:
                source_dup.rotation_mode = "XYZ"
                source_dup.rotation_euler = Euler((0, 0, 0))
            self.created_objects.append(source_dup.name)
            deselect(self.source)
            # remove modifiers and constraints
            for mod in source_dup.modifiers:
                source_dup.modifiers.remove(mod)
            for constraint in source_dup.constraints:
                source_dup.constraints.remove(constraint)
            # remove source_dup parent
            if source_dup.parent:
                parent_clear(source_dup)
            # send to new mesh
            if not cm.is_smoke:
                source_dup.data = new_mesh_from_object(self.source)
            # apply transformation data
            apply_transform(source_dup)
            source_dup.animation_data_clear()
            update_depsgraph()
        else:
            # get previously created source duplicate
            source_dup = bpy.data.objects.get(n + "__dup__")
        # if duplicate not created, source_dup is just original source
        source_dup = source_dup or self.source

        # link source_dup if it isn't in scene
        if source_dup.name not in scn.objects.keys():
            safe_link(source_dup)
            update_depsgraph()

        # get parent object
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        parent = bpy.data.objects.get(Bricker_parent_on)
        # if parent doesn't exist, get parent with new location
        source_dup_details = bounds(source_dup)
        parentLoc = source_dup_details.mid
        if parent is None:
            parent = get_new_parent(Bricker_parent_on, parentLoc)
            cm.parent_name = parent.name
        cm.parent_obj = parent
        parent["loc_diff"] = self.source.location - parentLoc
        self.created_objects.append(parent.name)

        # create, transform, and bevel bricks
        if self.brickify_in_background:
            filename = bpy.path.basename(bpy.data.filepath)[:-6]
            curJob = "%(filename)s__%(n)s" % locals()
            script = os.path.join(self.bricker_addon_path, "lib", "brickify_in_background_template.py")
            jobAdded, msg = self.job_manager.add_job(curJob, script=script, passed_data={"frame":None, "cmlist_index":scn.cmlist_index, "action":self.action}, use_blend_file=True)
            if not jobAdded: raise Exception(msg)
            self.jobs.append(curJob)
        else:
            bcoll = self.brickifyActiveFrame(self.action)
            link_brick_collection(cm, bcoll)
            # select the bricks object unless it's massive
            if not cm.split_model and len(bcoll.objects) > 0:
                obj = bcoll.objects[0]
                if len(obj.data.vertices) < 500000:
                    select(obj, active=True)

        # unlink source duplicate if created
        if source_dup != self.source:
            safe_unlink(source_dup)

        # set active frame to original active frame
        if self.action != "CREATE" and scn.frame_current != self.origFrame:
            scn.frame_set(self.origFrame)

        cm.last_source_mid = vec_to_str(parentLoc)

    def brickifyAnimation(self, scn, cm, n, matrix_dirty):
        """ create brick animation """
        # set up variables
        scn, cm, n = get_active_context_info()
        objs_to_select = []

        if self.action == "UPDATE_ANIM":
            safe_link(self.source)
            self.source.name = n  # fixes issue with smoke simulation cache

        # if there are no changes to apply, simply return "FINISHED"
        self.updatedFramesOnly = False
        if self.action == "UPDATE_ANIM" and not update_can_run("ANIMATION"):
            if cm.anim_is_dirty:
                self.updatedFramesOnly = True
            else:
                return {"FINISHED"}

        if self.brickify_in_background:
            cm.run_animated_frames = 0
            cm.frames_to_animate = (cm.stop_frame - cm.start_frame + 1)

        if (self.action == "ANIMATE" or cm.matrix_is_dirty or cm.anim_is_dirty) and not self.updatedFramesOnly:
            BRICKER_OT_clear_cache.clear_cache(cm, brick_mesh=False)

        if cm.split_model:
            cm.split_model = False

        # delete old bricks if present
        if self.action.startswith("UPDATE") and (matrix_dirty or cm.build_is_dirty or cm.last_split_model != cm.split_model or self.updatedFramesOnly):
            preserved_frames = None
            if self.updatedFramesOnly:
                # preserve duplicates, parents, and bricks for frames that haven't changed
                preserved_frames = [cm.start_frame, cm.stop_frame]
            BRICKER_OT_delete_model.cleanUp("ANIMATION", skipDupes=not self.updatedFramesOnly, skipParents=not self.updatedFramesOnly, preserved_frames=preserved_frames, source_name=self.source.name)

        # get parent object
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        self.parent0 = bpy.data.objects.get(Bricker_parent_on)
        if self.parent0 is None:
            self.parent0 = get_new_parent(Bricker_parent_on, self.source.location)
            cm.parent_obj = self.parent0
        self.created_objects.append(self.parent0.name)

        # begin drawing status to cursor
        wm = bpy.context.window_manager
        wm.progress_begin(0, cm.stop_frame + 1 - cm.start_frame)

        # prepare duplicate objects for animation
        duplicates = get_duplicate_objects(scn, cm, self.action, cm.start_frame, cm.stop_frame)

        filename = bpy.path.basename(bpy.data.filepath)[:-6]
        overwrite_blend = True
        # iterate through frames of animation and generate Brick Model
        for cur_frame in range(cm.start_frame, cm.stop_frame + 1):
            if self.updatedFramesOnly and cm.last_start_frame <= cur_frame and cur_frame <= cm.last_stop_frame:
                print("skipped frame %(cur_frame)s" % locals())
                self.completed_frames.append(cur_frame)
                cm.frames_to_animate -= 1
                continue
            if self.brickify_in_background:
                curJob = "%(filename)s__%(n)s__%(cur_frame)s" % locals()
                script = os.path.join(self.bricker_addon_path, "lib", "brickify_in_background_template.py")
                jobAdded, msg = self.job_manager.add_job(curJob, script=script, passed_data={"frame":cur_frame, "cmlist_index":scn.cmlist_index, "action":self.action}, use_blend_file=True, overwrite_blend=overwrite_blend)
                if not jobAdded: raise Exception(msg)
                self.jobs.append(curJob)
                overwrite_blend = False
            else:
                success = self.brickifyCurrentFrame(cur_frame, self.action)
                if not success:
                    break

        # unlink source duplicates
        for obj in duplicates.values():
            safe_unlink(obj)

        cm.last_start_frame = cm.start_frame
        cm.last_stop_frame = cm.stop_frame

    @staticmethod
    def brickifyCurrentFrame(cur_frame, action, inBackground=False):
        scn, cm, n = get_active_context_info()
        wm = bpy.context.window_manager
        Bricker_parent_on = "Bricker_%(n)s_parent" % locals()
        parent0 = bpy.data.objects.get(Bricker_parent_on)
        origFrame = scn.frame_current
        if inBackground and cm.is_smoke:
            smoke_mod = [mod for mod in cm.source_obj.modifiers if mod.type == "SMOKE"][0]
            point_cache = smoke_mod.domain_settings.point_cache
            point_cache.name = str(cur_frame)
            for frame in range(point_cache.frame_start, cur_frame):
                scn.frame_set(frame)
        scn.frame_set(origFrame)
        # get duplicated source
        source = bpy.data.objects.get("Bricker_%(n)s_f_%(cur_frame)s" % locals())
        # get source info to update
        if inBackground and scn not in source.users_scene:
            safe_link(source)
            update_depsgraph()

        # get source_details and dimensions
        source_details, dimensions = get_details_and_bounds(source)

        # update ref_logo
        logo_details, ref_logo = get_logo(scn, cm, dimensions)

        # set up parent for this layer
        # TODO: Remove these from memory in the delete function, or don't use them at all
        p_name = "%(Bricker_parent_on)s_f_%(cur_frame)s" % locals()
        parent = bpy.data.objects.get(p_name)
        if parent is None:
            parent = bpy.data.objects.new(p_name, None)
            parent.location = source_details.mid - parent0.location
            parent.parent = parent0
            parent.use_fake_user = True
            parent.update_tag()  # TODO: is it necessary to update this?

        # create new bricks
        try:
            coll_name, _ = create_new_bricks(source, parent, source_details, dimensions, ref_logo, logo_details, action, split=cm.split_model, cur_frame=cur_frame, clear_existing_collection=False, orig_source=cm.source_obj, select_created=False)
        except KeyboardInterrupt:
            if cur_frame != cm.start_frame:
                wm.progress_end()
                cm.last_start_frame = cm.start_frame
                cm.last_stop_frame = cur_frame - 1
                cm.animated = True
            return False

        # get collection with created bricks
        cur_frame_coll = bpy_collections().get(coll_name)
        if cur_frame_coll is not None and len(cur_frame_coll.objects) > 0:
            # get all_bricks_object
            obj = cur_frame_coll.objects[0]
            # hide collection/obj unless on scene current frame
            adjusted_frame_current = get_anim_adjusted_frame(scn.frame_current, cm.start_frame, cm.stop_frame)
            if cur_frame != adjusted_frame_current:
                hide(cur_frame_coll if b280() else obj)
            else:
                unhide(cur_frame_coll if b280() else obj)
            # lock location, rotation, and scale of created bricks
            obj.lock_location = (True, True, True)
            obj.lock_rotation = (True, True, True)
            obj.lock_scale    = (True, True, True)
            # add bevel if it was previously added
            if cm.bevel_added:
                BRICKER_OT_bevel.run_bevel_action([obj], cm)

        wm.progress_update(cur_frame-cm.start_frame)
        print("-"*100)
        print("completed frame " + str(cur_frame))
        print("-"*100)
        return True

    @staticmethod
    def brickifyActiveFrame(action):
        # initialize vars
        scn, cm, n = get_active_context_info()
        parent = cm.parent_obj
        source_dup = bpy.data.objects.get(cm.source_obj.name + "__dup__")
        source_dup_details, dimensions = get_details_and_bounds(source_dup)

        # update ref_logo
        logo_details, ref_logo = get_logo(scn, cm, dimensions)

        # create new bricks
        coll_name, _ = create_new_bricks(source_dup, parent, source_dup_details, dimensions, ref_logo, logo_details, action, split=cm.split_model, cur_frame=None)

        bcoll = bpy_collections().get(coll_name)
        if bcoll:
            # transform bricks to appropriate location
            transform_bricks(bcoll, cm, parent, cm.source_obj, source_dup_details, action)
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
        if cm.bevel_added:
            bricks = get_bricks(cm, typ="MODEL")
            BRICKER_OT_bevel.run_bevel_action(bricks, cm)

        return bcoll

    def isValid(self, scn, cm, source_name, source):
        """ returns True if brickify action can run, else report WARNING/ERROR and return False """
        # ensure custom object(s) are valid
        if (cm.brick_type == "CUSTOM" or cm.has_custom_obj1 or cm.has_custom_obj2 or cm.has_custom_obj3):
            warning_msg = custom_valid_object(cm)
            if warning_msg is not None:
                self.report({"WARNING"}, warning_msg)
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
        if self.brickify_in_background and bpy.data.filepath == "":
            self.report({"WARNING"}, "Please save the file first")
            return False
        # ensure custom material exists
        if cm.material_type == "CUSTOM" and cm.custom_mat is None:
            self.report({"WARNING"}, "Please choose a material in the 'Bricker > Materials' tab")
            return False
        if cm.material_type == "SOURCE" and cm.color_snap == "ABS":
            # ensure ABS Plastic materials are installed
            if not brick_materials_installed():
                self.report({"WARNING"}, "ABS Plastic Materials must be installed from Blender Market")
                return False
            # ensure ABS Plastic materials is updated to latest version
            if not hasattr(bpy.props, "abs_mat_properties"):
                self.report({"WARNING"}, "Requires ABS Plastic Materials v2.1.1 or later – please update via the addon preferences")
                return False
            # ensure ABS Plastic materials UI list is populated
            mat_obj = get_mat_obj(cm.id, typ="ABS")
            if mat_obj is None:
                mat_obj = create_new_mat_objs(cm.id)[1]
            if len(mat_obj.data.materials) == 0:
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
            if source.is_brick or source.is_brickified_object:
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
            if cm.start_frame > cm.stop_frame:
                self.report({"ERROR"}, "Start frame must be less than or equal to stop frame (see animation tab below).")
                return False

        if self.action == "UPDATE_MODEL":
            # make sure 'Bricker_[source name]_bricks' collection exists
            if brick_coll_name not in bpy_collections().keys():
                self.report({"WARNING"}, "Brickified Model doesn't exist. Create one with the 'Brickify Object' button.")
                return False

        # check that custom logo object exists in current scene and is of type "MESH"
        if cm.logo_type == "CUSTOM" and cm.brick_type != "CUSTOM":
            if cm.logo_object is None:
                self.report({"WARNING"}, "Custom logo object not specified.")
                return False
            elif cm.logo_object.name == source_name:
                self.report({"WARNING"}, "Source object cannot be its own logo.")
                return False
            elif cm.logo_object.name.startswith("Bricker_%(source_name)s" % locals()):
                self.report({"WARNING"}, "Bricker object cannot be used as its own logo.")
                return False
            elif cm.logo_object.type != "MESH":
                self.report({"WARNING"}, "Custom logo object is not of type 'MESH'. Please select another object (or press 'ALT-C to convert object to mesh).")
                return False

        return True

    #############################################
