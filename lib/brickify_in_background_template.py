# NOTE: Requires 'cmlist_index', 'frame', and 'action' as variables
# Pull objects and meshes from source file
import sys
scn = bpy.context.scene
if bpy.app.version < (2,80,0):
    scn.objects.active = None
else:
    bpy.context.window.view_layer.objects.active = None
scn.cmlist_index = cmlist_index
cm = scn.cmlist[cmlist_index]
n = cm.source_obj.name
bpy.ops.bricker.brickify_in_background(frame=frame if frame is not None else -1, action=action)
frame_str = "_f_%(frame)s" % locals() if cm.use_animation else ""
bpy_collections = bpy.data.groups if bpy.app.version < (2,80,0) else bpy.data.collections
target_coll = bpy_collections.get("Bricker_%(n)s_bricks%(frame_str)s" % locals())
parent_obj = bpy.data.objects.get("Bricker_%(n)s_parent%(frame_str)s" % locals())

### SET 'data_blocks' EQUAL TO LIST OF OBJECT DATA TO BE SEND BACK TO THE BLENDER HOST ###

data_blocks = [target_coll, parent_obj]

### PYTHON DATA TO BE SEND BACK TO THE BLENDER HOST ###

python_data = {"bricksdict":bpy.props.bfm_cache_bytes_hex, "brick_sizes_used":cm.brick_sizes_used, "brick_types_used":cm.brick_types_used}
