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

# Module imports
from .bricksdict import *
from .brick.bricks import get_brick_dimensions
from .brick.types import mergable_brick_type
from .common import *
from .general import *
from .cmlist_utils import *
from .logo_obj import *
from .make_bricks import *
from .point_cache import *
from .transform_data import *


def get_action(cm):
    """ gets current action type from passed cmlist item """
    if cm.use_animation:
        return "UPDATE_ANIM" if cm.animated else "ANIMATE"
    else:
        return "UPDATE_MODEL" if cm.model_created else "CREATE"


def get_duplicate_object(cm, n, source, created_objects=None):
    source_dup = bpy.data.objects.get(n + "__dup__")
    if source_dup is None:
        # duplicate source
        source_dup = duplicate(source, link_to_scene=True)
        source_dup.name = n + "__dup__"
        source_dup.stored_parents.clear()
        if cm.use_local_orient:
            source_dup.rotation_mode = "XYZ"
            source_dup.rotation_euler = Euler((0, 0, 0))
        if created_objects is not None:
            created_objects.append(source_dup.name)
        # remove modifiers and constraints
        for mod in source_dup.modifiers:
            source_dup.modifiers.remove(mod)
        for constraint in source_dup.constraints:
            source_dup.constraints.remove(constraint)
        # remove source_dup parent
        if source_dup.parent:
            parent_clear(source_dup)
        # handle smoke
        if cm.is_smoke:
            store_smoke_data(source, source_dup)
        else:
            # send to new mesh
            source_dup.data = new_mesh_from_object(source)
        # apply transformation data
        apply_transform(source_dup)
        source_dup.animation_data_clear()
    # if duplicate not created, source_dup is just original source
    return source_dup or source


def get_duplicate_objects(scn, cm, action, start_frame, stop_frame, updated_frames_only):
    """ returns list of duplicates from source with all traits applied """
    source = cm.source_obj
    n = source.name
    orig_frame = scn.frame_current
    soft_body = False
    smoke = False

    # set cm.armature and cm.physics
    for mod in source.modifiers:
        if mod.type == "ARMATURE":
            cm.armature = True
        elif mod.type in ("CLOTH", "SOFT_BODY"):
            soft_body = True
            point_cache = mod.point_cache
        elif is_smoke_domain(mod):
            smoke = True
            point_cache = mod.domain_settings.point_cache

    # step through uncached frames to run simulation
    if soft_body or smoke:
        first_uncached_frame = get_first_uncached_frame(source, point_cache)
        for cur_frame in range(first_uncached_frame, start_frame):
            scn.frame_set(cur_frame)

    denom = stop_frame - start_frame
    update_progress("Applying Modifiers", 0.0)

    duplicates = {}
    for cur_frame in range(start_frame, stop_frame + 1):
        source_dup_name = "Bricker_%(n)s_f_%(cur_frame)s" % locals()
        # retrieve previously duplicated source if possible
        if action == "UPDATE_ANIM":
            source_dup = bpy.data.objects.get(source_dup_name)
            if source_dup is not None:
                duplicates[cur_frame] = source_dup
                link_object(source_dup)
                continue
        # skip unchanged frames
        if frame_unchanged(updated_frames_only, cm, cur_frame):
            continue
        # set active frame for applying modifiers
        scn.frame_set(cur_frame)
        # duplicate source for current frame
        source_dup = duplicate(source, link_to_scene=True)
        # source_dup.use_fake_user = True
        source_dup.name = source_dup_name
        source_dup.stored_parents.clear()
        # remove modifiers and constraints
        for mod in source_dup.modifiers:
            source_dup.modifiers.remove(mod)
        for constraint in source_dup.constraints:
            source_dup.constraints.remove(constraint)
        # apply parent transformation
        if source_dup.parent:
            parent_clear(source_dup)
        # apply animated transform data
        source_dup.matrix_world = source.matrix_world
        source_dup.animation_data_clear()
        # handle smoke
        if smoke:
            store_smoke_data(source, source_dup)
        else:
            # send to new mesh
            source_dup.data = new_mesh_from_object(source)
        # apply transform data
        apply_transform(source_dup)
        # store duplicate to dictionary of dupes
        duplicates[cur_frame] = source_dup
        # update progress bar
        percent = (cur_frame - start_frame + 1) / (denom + 2)
        if percent < 1:
            update_progress("Applying Modifiers", percent)
    # update progress bar
    scn.frame_set(orig_frame)
    depsgraph_update()
    update_progress("Applying Modifiers", 1)
    return duplicates


def frame_unchanged(updated_frames_only, cm, cur_frame):
    return updated_frames_only and cm.last_start_frame <= cur_frame and cur_frame <= cm.last_stop_frame


def get_model_resolution(source, cm):
    res = None
    source_details = bounds(source, use_adaptive_domain=False)
    s = Vector((
        round(source_details.dist.x, 6),
        round(source_details.dist.y, 6),
        round(source_details.dist.z, 6),
    ))
    if cm.brick_type != "CUSTOM":
        dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
        full_d = Vector((
            dimensions["width"],
            dimensions["width"],
            dimensions["height"],
        ))
        res = vec_div(s, full_d)
    else:
        custom_obj = cm.custom_object1
        if custom_obj and custom_obj.type == "MESH":
            custom_details = bounds(custom_obj)
            if 0 not in custom_details.dist.to_tuple():
                mult = cm.brick_height / custom_details.dist.z
                full_d = Vector((
                    custom_details.dist.x * mult,
                    custom_details.dist.y * mult,
                    cm.brick_height,
                ))
                full_d_offset = vec_mult(full_d, cm.dist_offset)
                res = vec_div(s, full_d_offset)
    return res


def should_brickify_in_background(cm, r, action):
    brickify_in_background = get_addon_preferences().brickify_in_background
    if brickify_in_background != "AUTO" or r is None:
        return brickify_in_background == "ON"
    matrix_dirty = matrix_really_is_dirty(cm)
    source = cm.source_obj
    # due to mantaflow issue, force local if is_smoke
    if is_smoke(cm.source_obj):
        return False
    # return False if model is simple enough to run in active session
    return (
                (   # model resolution
                    r.x * r.y * r.z
                    # accounts for shell thickness
                    * math.sqrt(cm.shell_thickness)
                    # accounts for internal supports
                    * (1.35 if cm.internal_supports != "NONE" else 1)
                    # accounts for costly ray casting
                    * (3 if cm.insideness_ray_cast_dir != "HIGH_EFFICIENCY" else 1)
                    # accounts for merging algorithm
                    * (1.5 if mergable_brick_type(cm.brick_type) else 1)
                    # accounts for additional merging calculations for connectivity
                    * (math.sqrt(cm.connect_thresh) if mergable_brick_type(cm.brick_type) and cm.merge_type == "RANDOM" else 1)
                    # accounts for source object resolution
                    * len(source.data.vertices)**(1/20)
                    # multiplies per frame
                    * (abs(cm.stop_frame - cm.start_frame) if cm.use_animation else 1)
                    # if using cached matrix, divide by 2
                    / (1 if matrix_dirty else 2)
                ) >= 30000 or
                # no logos
                cm.logo_type != "NONE" or
                # accounts for intricacy of custom object
                (cm.brick_type == "CUSTOM" and (not b280() or len(cm.custom_object1.evaluated_get(bpy.context.view_layer.depsgraph).data.vertices) > 50)) or
                # low exposed underside detail
                cm.exposed_underside_detail not in ("FLAT", "LOW") or
                # no hidden underside detail
                cm.hidden_underside_detail != "FLAT" or
                # not using source materials
                (cm.material_type == "SOURCE" and cm.use_uv_map and len(source.data.uv_layers) > 0)
    )


def get_args_for_background_processor(cm, bricker_addon_path, source_dup=None):
    script = os.path.join(bricker_addon_path, "lib", "brickify_in_background_template.py")

    cmlist_props, cmlist_pointer_props = dump_cm_props(cm)

    data_blocks_to_send = set()
    for item in cmlist_pointer_props:
        name = cmlist_pointer_props[item]["name"]
        typ = cmlist_pointer_props[item]["type"]
        data = getattr(bpy.data, typ.lower() + "s")[name]
        data_blocks_to_send.add(data)
    data_blocks_to_send.add(source_dup)

    return script, cmlist_props, cmlist_pointer_props, data_blocks_to_send


def get_bricksdict_for_model(cm, source, source_details, action, cur_frame, brick_scale, bricksdict, keys, redraw, update_cursor):
    if bricksdict is None:
        # load bricksdict from cache
        bricksdict = get_bricksdict(cm, d_type=action, cur_frame=cur_frame)
        loaded_from_cache = bricksdict is not None
        # if not loaded, new bricksdict must be created
        if not loaded_from_cache:
            # multiply brick_scale by offset distance
            brick_scale2 = brick_scale if cm.brick_type != "CUSTOM" else vec_mult(brick_scale, Vector(cm.dist_offset))
            # create new bricksdict
            bricksdict = make_bricksdict(source, source_details, brick_scale2, cursor_status=update_cursor)
    else:
        loaded_from_cache = True
    # reset all values for certain keys in bricksdict dictionaries
    if cm.build_is_dirty and loaded_from_cache:
        threshold = getThreshold(cm)
        shell_thickness_changed = cm.last_shell_thickness != cm.shell_thickness
        for kk in bricksdict:
            brick_d = bricksdict[kk]
            if keys == "ALL" or kk in keys:
                brick_d["size"] = None
                brick_d["parent"] = None
                brick_d["top_exposed"] = None
                brick_d["bot_exposed"] = None
                if shell_thickness_changed:
                    brick_d["draw"] = brick_d["val"] >= threshold
            else:
                # don't merge bricks not in 'keys'
                brick_d["attempted_merge"] = True
    elif redraw:
        for kk in keys:
            bricksdict[kk]["attempted_merge"] = False
    if (not loaded_from_cache or cm.internal_is_dirty) and cm.calc_internals:
        update_internal(bricksdict, cm, keys, clear_existing=loaded_from_cache)
        cm.build_is_dirty = True
    # update materials in bricksdict
    if cm.material_type != "NONE" and (cm.material_is_dirty or cm.matrix_is_dirty or cm.anim_is_dirty):
        bricksdict = update_materials(bricksdict, source, keys, cur_frame=cur_frame, action=action)
    return bricksdict, brick_scale


def create_new_bricks(source_dup, parent, source_details, dimensions, action, split=True, cm=None, cur_frame=None, bricksdict=None, keys="ALL", clear_existing_collection=True, select_created=False, print_status=True, temp_brick=False, redraw=False, orig_source=None):
    """ gets/creates bricksdict, runs make_bricks, and caches the final bricksdict """
    ct = time.time()
    scn, cm, n = get_active_context_info(cm=cm)
    ref_logo = None if temp_brick else get_logo(scn, cm, dimensions)  # update ref_logo
    brick_scale, custom_data = get_arguments_for_bricksdict(cm, source=source_dup, dimensions=dimensions)
    update_cursor = action in ("CREATE", "UPDATE_MODEL")
    # get bricksdict
    bricksdict, brick_scale = get_bricksdict_for_model(cm, source_dup, source_details, action, cur_frame, brick_scale, bricksdict, keys, redraw, update_cursor)
    # make bricks
    if cm.instance_method == "POINT_CLOUD":
        # generate point cloud
        model_name = "Bricker_%(n)s_bricks_f_%(cur_frame)s" % locals() if cur_frame is not None else "Bricker_%(n)s_bricks" % locals()
        instancer_name = "Bricker_%(n)s_instancer_f_%(cur_frame)s" % locals() if cur_frame is not None else "Bricker_%(n)s_instancer" % locals()
        bricker_parent = bpy.data.objects.get("Bricker_%(n)s_parent" % locals())
        point_cloud = bpy.data.meshes.new(instancer_name)
        point_cloud_obj = bpy.data.objects.new(instancer_name, point_cloud)
        # get brick collection
        bcoll = get_brick_collection(model_name, clear_existing_collection=True)
        # add point cloud to collection
        bcoll.objects.link(point_cloud_obj)
        # set point cloud location
        try:
            link_object(parent)
        except RuntimeError:
            pass
        depsgraph_update()
        point_cloud_obj.location = source_details.mid - parent.matrix_world.to_translation()
        # initialize vars
        keys = list(bricksdict.keys())
        rand_s2 = np.random.RandomState(cm.merge_seed + 1)
        random_rot = cm.random_rot
        random_loc = cm.random_loc
        zstep = get_zstep(cm)
        keys_dict, sorted_keys = get_keys_dict(bricksdict, keys)
        i = 0
        # create points in cloud
        point_cloud.vertices.add(len(bricksdict))
        # set coordinates and normals for points in cloud
        for z in sorted(keys_dict.keys()):
            for key in keys_dict[z]:
                brick_d = bricksdict[key]
                brick_d["size"] = (1, 1, 1)
                # apply random rotation to edit mesh according to parameters
                random_rot_angle = get_random_rot_angle(random_rot * 2, rand_s2, brick_d["size"])
                # get brick location
                loc_offset = get_random_loc(random_loc, rand_s2, dimensions["half_width"], dimensions["half_height"])
                brick_loc = get_brick_center(bricksdict, key, zstep, str_to_list(key)) + loc_offset
                # set vert
                v = point_cloud.vertices[i]
                v.co = brick_loc
                if random_rot_angle:
                    v.normal.x = 1
                    v.normal.y = random_rot_angle[0]
                    v.normal.z = random_rot_angle[1]
                i += 1
        bricks_created = point_cloud_obj
        # set up point cloud as instancer
        point_cloud_obj.instance_type = "VERTS"
        point_cloud_obj.show_instancer_for_viewport = True
        point_cloud_obj.show_instancer_for_render = False
        point_cloud_obj.use_instance_vertices_rotation = True
        # create instance obj
        brick = generate_brick_object(model_name)
        if cm.material_type == "CUSTOM":
            set_material(brick, cm.custom_mat)
        bcoll.objects.link(brick)
        brick.parent = point_cloud_obj
        point_cloud_obj.parent = parent
    else:
        model_name = "Bricker_%(n)s_bricks_f_%(cur_frame)s" % locals() if cur_frame is not None else "Bricker_%(n)s_bricks" % locals()
        # make bricks
        bricks_created, bricksdict = make_bricks(source_dup, parent, ref_logo, dimensions, bricksdict, action, cm=cm, split=split, brick_scale=brick_scale, custom_data=custom_data, coll_name=model_name, clear_existing_collection=clear_existing_collection, frame_num=cur_frame, cursor_status=update_cursor, keys=keys, print_status=print_status, temp_brick=temp_brick, redraw=redraw)
        # select bricks
        if select_created and len(bricks_created) > 0:
            select(bricks_created)
    # remove duplicated logo
    if ref_logo is not None:
        bpy.data.objects.remove(ref_logo)
    # store current bricksdict to cache
    cache_bricks_dict(action, cm, bricksdict, cur_frame=cur_frame)
    # reset some of the dirty attributes
    cm.build_is_dirty = False
    cm.material_is_dirty = False
    cm.model_is_dirty = False
    cm.bricks_are_dirty = False
    return model_name, bricks_created


def generate_brick_object(brick_name="New Brick", brick_size=(1, 1, 1)):
    scn, cm, n = get_active_context_info()
    brick_d = create_bricksdict_entry(
        name=brick_name,
        loc=(1, 1, 1),
        val=1,
        draw=True,
        b_type=get_brick_type(cm.brick_type),
    )
    rand = np.random.RandomState(cm.merge_seed)
    dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
    use_stud = cm.stud_detail != "NONE"
    logo_to_use = get_logo(scn, cm, dimensions) if use_stud and cm.logo_type != "NONE" else None
    m = get_brick_data(brick_d, dimensions, cm.brick_type, brick_size, cm.circle_verts, cm.exposed_underside_detail, use_stud, logo_to_use, cm.logo_type, cm.logo_inset, None, cm.logo_resolution, cm.logo_decimate, rand)
    brick = bpy.data.objects.new(brick_name, m)
    return brick



def get_arguments_for_bricksdict(cm, source=None, dimensions=None, brick_size=[1, 1, 3]):
    """ returns arguments for make_bricksdict function """
    source = source or cm.source_obj
    split_model = cm.split_model
    custom_data = [None] * 3
    if dimensions is None:
        dimensions = get_brick_dimensions(cm.brick_height, cm.zstep, cm.gap)
    for i, custom_info in enumerate([[cm.has_custom_obj1, cm.custom_object1], [cm.has_custom_obj2, cm.custom_object2], [cm.has_custom_obj3, cm.custom_object3]]):
        has_custom_obj, custom_obj = custom_info
        if (i == 0 and cm.brick_type == "CUSTOM") or has_custom_obj:
            scn = bpy.context.scene
            # duplicate custom object
            # TODO: remove this object on delete action
            custom_obj_name = custom_obj.name + "__dup__"
            m = new_mesh_from_object(custom_obj)
            custom_obj0 = bpy.data.objects.get(custom_obj_name)
            if custom_obj0 is not None:
                custom_obj0.data = m
            else:
                custom_obj0 = bpy.data.objects.new(custom_obj_name, m)
            # remove UV layers if not split (for massive performance improvement when combining meshes in `draw_brick` fn)
            if b280() and not split_model:
                for uv_layer in m.uv_layers:
                    m.uv_layers.remove(uv_layer)
            # apply transformation to custom object
            safe_link(custom_obj0)
            apply_transform(custom_obj0)
            depsgraph_update()
            safe_unlink(custom_obj0)
            # get custom object details
            cur_custom_obj_details = bounds(custom_obj0)
            # set brick scale
            scale = cm.brick_height/cur_custom_obj_details.dist.z
            brick_scale = cur_custom_obj_details.dist * scale + Vector([dimensions["gap"]] * 3)
            # get transformation matrices
            t_mat = Matrix.Translation(-cur_custom_obj_details.mid)
            max_dist = max(cur_custom_obj_details.dist)
            s_mat_x = Matrix.Scale((brick_scale.x - dimensions["gap"]) / cur_custom_obj_details.dist.x, 4, Vector((1, 0, 0)))
            s_mat_y = Matrix.Scale((brick_scale.y - dimensions["gap"]) / cur_custom_obj_details.dist.y, 4, Vector((0, 1, 0)))
            s_mat_z = Matrix.Scale((brick_scale.z - dimensions["gap"]) / cur_custom_obj_details.dist.z, 4, Vector((0, 0, 1)))
            # apply transformation to custom object dup mesh
            custom_obj0.data.transform(t_mat)
            custom_obj0.data.transform(mathutils_mult(s_mat_x, s_mat_y, s_mat_z))
            # center mesh origin
            center_mesh_origin(custom_obj0.data, dimensions, brick_size)
            # store fresh data to custom_data variable
            custom_data[i] = custom_obj0.data
    if cm.brick_type != "CUSTOM":
        brick_scale = Vector((
            dimensions["width"] + dimensions["gap"],
            dimensions["width"] + dimensions["gap"],
            dimensions["height"]+ dimensions["gap"],
        ))
    return brick_scale, custom_data


def transform_bricks(bcoll, cm, parent, source, source_dup_details, action):
    # if using local orientation and creating model for first time
    if cm.use_local_orient and action == "CREATE":
        obj = parent if cm.split_model else bcoll.objects[0]
        source_details = bounds(source)
        last_mode = source.rotation_mode
        obj.rotation_mode = "XYZ"
        source.rotation_mode = obj.rotation_mode
        obj.rotation_euler = source.rotation_euler
        obj.rotation_mode = last_mode
        source["local_orient_offset"] = source_details.mid - source_dup_details.mid
        obj.location += Vector(source["local_orient_offset"])
    # if model was split but isn't now
    if cm.last_split_model and not cm.split_model:
        # transfer transformation of parent to object
        parent.rotation_mode = "XYZ"
        for obj in bcoll.objects:
            obj.location = parent.location
            obj.rotation_mode = parent.rotation_mode
            obj.rotation_euler.rotate(parent.rotation_euler)
            obj.scale = parent.scale
        # reset parent transformation
        parent.location = (0, 0, 0)
        parent.rotation_euler = Euler((0, 0, 0))
        cm.transform_scale = 1
        parent.scale = (1, 1, 1)
    # if model is not split
    elif not cm.split_model:
        # apply stored transformation to bricks
        apply_transform_data(cm, bcoll.objects)
    # if model wasn't split but is now
    elif not cm.last_split_model:
        # apply stored transformation to parent of bricks
        apply_transform_data(cm, parent)
    obj = bcoll.objects[0] if len(bcoll.objects) > 0 else None
    if obj is None:
        return
    # if model contains armature, lock the location, rotation, and scale of created bricks object
    if not cm.split_model and cm.armature:
        obj.lock_location = (True, True, True)
        obj.lock_rotation = (True, True, True)
        obj.lock_scale    = (True, True, True)


def store_parent_collections_to_source(cm, source):
    if not b280():
        return
    # clear outdated stored_parents
    source.stored_parents.clear()
    # store parent collections to source
    if len(source.users_collection) > 0:
        # use parent collections of source
        linked_colls = source.users_collection
    else:
        # use parent collections of brick collection
        brick_coll = cm.collection
        if brick_coll is None:
            return
        all_collections = list(bpy_collections()) + [bpy.context.scene.collection]
        linked_colls = [cn for cn in all_collections if brick_coll.name in cn.children]
    for cn in linked_colls:
        source.stored_parents.add().collection = cn


def get_new_parent(name, loc):
    parent = bpy.data.objects.new(name, None)
    parent.location = loc
    return parent


def link_brick_collection(cm, coll):
    cm.collection = coll
    source = cm.source_obj
    if cm.parent_obj.name not in coll.objects:
        coll.objects.link(cm.parent_obj)
    if b280():
        for item in source.stored_parents:
            if coll.name not in item.collection.children:
                item.collection.children.link(coll)
    else:
        [safe_link(obj) for obj in coll.objects]


def get_anim_coll(n):
    anim_coll_name = "Bricker_%(n)s_bricks" % locals()
    anim_coll = bpy_collections().get(anim_coll_name)
    if anim_coll is None:
        anim_coll = bpy_collections().new(anim_coll_name)
    return anim_coll


def finish_animation(cm):
    scn, cm, n = get_active_context_info(cm=cm)
    wm = bpy.context.window_manager
    wm.progress_end()

    # link animation frames to animation collection
    anim_coll = get_anim_coll(n)
    for cn in get_collections(cm, typ="ANIM"):
        if b280():
            if cn.name not in anim_coll.children:
                anim_coll.children.link(cn)
        else:
            for obj in cn.objects:
                safe_link(obj)
                if obj.name not in anim_coll.objects.keys():
                    anim_coll.objects.link(obj)
    return anim_coll


def add_completed_frame(cm, frame):
    if cm.completed_frames != "":
        cm.completed_frames += ", "
    cm.completed_frames += str(frame)
