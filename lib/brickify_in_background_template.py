# NOTE: Requires 'cmlist_props', 'cmlist_pointer_props' 'frame', and 'action' as variables
import sys
# redefine common functions
def b280():
    return bpy.app.version >= (2,80,0)
def load_cm_props(cm, prop_dict, pointer_dict):
    for item in prop_dict:
        setattr(cm, item, prop_dict[item])
    for item in pointer_dict:
        name = pointer_dict[item]["name"]
        typ = pointer_dict[item]["type"]
        data = getattr(bpy.data, typ.lower() + "s")[name]
        setattr(cm, item, data)
def link_object(o, scene=None):
    scene = scene or bpy.context.scene
    if b280():
        scene.collection.objects.link(o)
    else:
        scene.objects.link(o)
# create and populate new cmlist index
scn = bpy.context.scene
bpy.ops.cmlist.list_action(action="ADD")
scn.cmlist_index = 0
cm = scn.cmlist[scn.cmlist_index]
# match cm.id to source cmlist item
cm.id = cmlist_id
# Pull objects and meshes from source file
for data_block in passed_data_blocks:
    if isinstance(data_block, bpy.types.Object):
        link_object(data_block)
load_cm_props(cm, cmlist_props, cmlist_pointer_props)
# # update depsgraph
# if b280():
#     bpy.context.view_layer.depsgraph.update()
# else:
#     bpy.context.scene.update()
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
