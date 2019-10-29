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
# NONE!

# Blender imports
import bpy
from bpy.props import *

# Module imports
from ...functions.property_callbacks import *


# Create custom property group
class CreatedModelProperties(bpy.types.PropertyGroup):
    # CMLIST ITEM SETTINGS
    name = StringProperty(update=uniquify_name)
    id = IntProperty()
    idx = IntProperty()

    # NAME OF SOURCE
    source_obj = PointerProperty(
        type=bpy.types.Object,
        poll=lambda self, object: object.type == "MESH",
        name="Source Object",
        description="Name of the source object to Brickify",
        update=set_default_obj_if_empty,
    )

    # TRANSFORMATION SETTINGS
    model_loc = StringProperty(default="-1,-1,-1")
    model_rot = StringProperty(default="-1,-1,-1")
    model_scale = StringProperty(default="-1,-1,-1")
    transform_scale = FloatProperty(
        name="Scale",
        description="Scale of the brick model",
        update=update_model_scale,
        step=1,
        default=1.0)
    apply_to_source_object = BoolProperty(
        name="Apply to source",
        description="Apply transformations to source object when Brick Model is deleted",
        default=True)
    parent_obj = PointerProperty(
        type=bpy.types.Object,
        name="Parent Object",
        description="Name of the parent object used for model transformations")
    expose_parent = BoolProperty(
        name="Show Manipulator",
        description="Expose the parent object for this brick model for viewport manipulation",
        update=update_parent_exposure,
        default=False)

    # ANIMATION SETTINGS
    use_animation = BoolProperty(
        name="Use Animation",
        description="Create Brick Model for each frame, from start to stop frame (WARNING: Calculation takes time, and may result in large blend file)",
        default=False)
    start_frame = IntProperty(
        name="Start",
        description="First frame of the brick animation",
        update=dirty_anim,
        min=0, max=500000,
        default=1)
    stop_frame = IntProperty(
        name="End",
        description="Final frame of the brick animation",
        update=dirty_anim,
        min=0, max=500000,
        default=10)
    max_workers = IntProperty(
        name="Max Worker Instances",
        description="Maximum number of Blender instances allowed to run in background for Bricker calculations (larger numbers are faster at a higher CPU load; 0 for local calculation)",
        min=0, max=24,
        update=update_job_manager_properties,
        default=5)
    back_proc_timeout = FloatProperty(
        name="Timeout",
        description="Max seconds allowed for each frame's model to calculate (0 for infinite; cancels process if time exceeded)",
        subtype="TIME",
        precision=0, min=0,
        update=update_job_manager_properties,
        default=0)

    # BASIC MODEL SETTINGS
    brick_height = FloatProperty(
        name="Brick Height",
        description="Height of the bricks in the final Brick Model",
        update=dirty_matrix,
        subtype="DISTANCE",
        step=1,
        precision=3,
        min = 0.000001,
        soft_min=0.001, soft_max=10,
        default=0.1)
    gap = FloatProperty(
        name="Gap Between Bricks",
        description="Distance between bricks (relative to brick height)",
        update=dirty_matrix,
        subtype="PERCENTAGE",
        step=1,
        precision=1,
        min=0.0, max=100.0,
        default=0.5)
    merge_seed = IntProperty(
        name="Random Seed",
        description="Random seed for brick merging calculations",
        update=dirty_build,
        min=0,
        default=1000)
    connect_thresh = IntProperty(
        name="Connectivity",
        description="Quality of the model's brick connectivity (higher numbers are slower but bricks will be more interconnected)",
        update=dirty_build,
        min=1, soft_max=100,
        default=1)
    smoke_density = FloatProperty(
        name="Smoke Density",
        description="Density of brickified smoke (threshold for smoke: 1 - d)",
        update=dirty_matrix,
        min=0, max=1,
        default=0.9)
    smoke_quality = FloatProperty(
        name="Smoke Quality",
        description="Amount of data to analyze for density and color of brickified smoke",
        update=dirty_matrix,
        min=1, soft_max=100,
        default=1)
    smoke_brightness = FloatProperty(
        name="Smoke Brightness",
        description="Add brightness to smoke colors read from smoke data",
        update=dirty_matrix,
        soft_min=0, soft_max=100,
        default=1)
    smoke_saturation = FloatProperty(
        name="Smoke Saturation",
        description="Change saturation level of smoke colors read from smoke data",
        update=dirty_matrix,
        min=0, soft_max=100,
        default=1)
    flame_color = FloatVectorProperty(
        name="Hex Value",
        subtype="COLOR",
        update=dirty_matrix,
        default=[1.0, 0.63, 0.2])
    flame_intensity = FloatProperty(
        name="Flame Intensity",
        description="Intensity of the flames",
        update=dirty_matrix,
        min=1, soft_max=50,
        default=4)
    split_model = BoolProperty(
        name="Split Model",
        description="Split model into separate objects (slower)",
        update=dirty_model,
        default=False)
    random_loc = FloatProperty(
        name="Random Location",
        description="Max random location applied to each brick",
        update=dirty_model,
        step=1,
        precision=3,
        min=0, soft_max=1,
        default=0.01)
    random_rot = FloatProperty(
        name="Random Rotation",
        description="Max random rotation applied to each brick",
        update=dirty_model,
        step=1,
        precision=3,
        min=0, soft_max=1,
        default=0.025)
    brick_shell = EnumProperty(
        name="Brick Shell",
        description="Choose whether the outer shell of bricks will be inside or outside the source mesh",
        items=[("INSIDE", "Inside Mesh", "Draw brick shell inside source mesh (recommended)"),
               ("OUTSIDE", "Outside Mesh", "Draw brick shell outside source mesh"),
               ("CONSISTENT", "Consistent", "Draw brick shell on a consistent side of the source mesh topology (may fix noisy model if source mesh is not water-tight; in most situations, enable 'Verify Exposure' when using this setting)")],
        update=update_brick_shell,
        default="INSIDE")
    calculation_axes = EnumProperty(
        name="Expanded Axes",
        description="The brick shell will be drawn on the outside in these directions",
        items=[("XYZ", "XYZ", "XYZ"),
               ("XY", "XY", "XY"),
               ("YZ", "YZ", "YZ"),
               ("XZ", "XZ", "XZ"),
               ("X", "X", "X"),
               ("Y", "Y", "Y"),
               ("Z", "Z", "Z")],
        update=dirty_matrix,
        default="XY")
    shell_thickness = IntProperty(
        name="Shell Thickness",
        description="Thickness of the outer shell of bricks",
        update=dirty_build,
        min=1, max=50,
        default=1)

    # BRICK TYPE SETTINGS
    description = "Use this brick type to build the model"
    brick_type = EnumProperty(
        name="Brick Type",
        description="Type of brick used to build the model",
        items=[("BRICKS", "Bricks (fast)", description, 0),
               ("BRICKS AND PLATES", "Bricks and Plates", description, 1),
               ("CONES", "Cones", description, 2),
               ("CUSTOM", "Custom", "Use custom object to build the model", 3),
               ("CYLINDERS", "Cylinders", description, 4),
               ("PLATES", "Plates", description, 5),
               # ("SLOPES", "Slopes (fast)", description, 6),
               ("STUDS", "Studs", description, 7),
               ("STUD_HOLLOWS", "Hollow Studs", description, 8)],
        update=update_brick_type,
        default="BRICKS")
    align_bricks = BoolProperty(
        name="Align Bricks Horizontally",
        description="Keep bricks aligned horizontally, and fill the gaps with plates",
        update=dirty_build,
        default=True)
    offset_brick_layers = IntProperty(
        name="Offset Brick Layers",
        description="Offset the layers that will be merged into bricks if possible",
        update=dirty_build,
        step=1,
        min=0, max=2,
        default=0)
    max_width = IntProperty(
        name="Max Width",
        description="Maximum brick width in studs",
        update=dirty_build,
        step=1,
        min=1, soft_max=100,
        default=2)
    max_depth = IntProperty(
        name="Max Depth",
        description="Maximum brick depth in studs",
        update=dirty_build,
        step=1,
        min=1, soft_max=100,
        default=10)
    merge_type = EnumProperty(
        name="Merge Type",
        description="Type of algorithm used for merging bricks together",
        items=[
            ("NONE", "None (fast)", "Bricks are not merged"),
            ("GREEDY", "Greedy", "Creates fewest amount of bricks possible"),
            ("RANDOM", "Random", "Merges randomly for realistic build"),
        ],
        update=dirty_build,
        default="RANDOM")
    legal_bricks_only = BoolProperty(
        name="Legal Bricks Only",
        description="Construct model using only legal brick sizes",
        update=dirty_build,
        default=True)
    custom_object1 = PointerProperty(
        type=bpy.types.Object,
        poll=lambda self, object: object.type == "MESH" and object != self.source_obj and not object.name.startswith("Bricker_{}".format(self.source_obj.name)),
        name="Custom Object Name 1",
        description="Custom object to use as brick type",
    )
    custom_object2 = PointerProperty(
        type=bpy.types.Object,
        poll=lambda self, object: object.type == "MESH" and object != self.source_obj and not object.name.startswith("Bricker_{}".format(self.source_obj.name)),
        name="Custom Object Name 2",
        description="Custom object to use as brick type",
    )
    custom_object3 = PointerProperty(
        type=bpy.types.Object,
        poll=lambda self, object: object.type == "MESH" and object != self.source_obj and not object.name.startswith("Bricker_{}".format(self.source_obj.name)),
        name="Custom Object Name 3",
        description="Custom object to use as brick type",
    )
    dist_offset = FloatVectorProperty(
        name="Offset Distance",
        description="Offset distance between custom bricks (1.0 = side-by-side)",
        update=dirty_matrix,
        step=1,
        precision=3,
        subtype="TRANSLATION",
        min=0.001, soft_max=1.0,
        default=(1, 1, 1))

    # CUSTOMIZE SETTINGS
    auto_update_on_delete = BoolProperty(
        name="Auto Update on Delete",
        description="Draw newly exposed bricks when existing bricks are deleted",
        default=True)
    paintbrush_mat = PointerProperty(
        type=bpy.types.Material,
        name="Paintbrush Material",
        description="Material for the BrickSculpt paintbrush tool")

    # MATERIAL & COLOR SETTINGS
    material_type = EnumProperty(
        name="Material Type",
        description="Choose what materials will be applied to model",
        items=[("NONE", "None", "No material applied to bricks"),
               ("CUSTOM", "Single Material", "Choose one material to apply to all generated bricks"),
               ("RANDOM", "Random", "Apply a random material from Brick materials to each generated brick"),
               ("SOURCE", "Use Source Materials", "Apply material based on closest intersecting face")],
        update=dirty_material,
        default="NONE")
    custom_mat = PointerProperty(
        type=bpy.types.Material,
        name="Custom Material",
        description="Material to apply to all bricks")
    internal_mat = PointerProperty(
        type=bpy.types.Material,
        name="Internal Material",
        description="Material to apply to bricks inside material shell",
        update=dirty_material)
    mat_shell_depth = IntProperty(
        name="Shell Material Depth",
        description="Depth to which the outer materials should be applied (1 = Only exposed bricks)",
        step=1,
        min=1, max=50,
        default=1,
        update=dirty_model)
    merge_internals = EnumProperty(
        name="Merge Shell with Internals",
        description="Merge bricks on shell with internal bricks",
        items=[("NEITHER", "Neither", "Don't merge shell bricks with internals in either direction"),
               ("HORIZONTAL", "Horizontal", "Merge shell bricks with internals horizontally, but not vertically"),
               ("VERTICAL", "Vertical", "Merge shell bricks with internals vertically, but not horizontally"),
               ("BOTH", "Horizontal & Vertical", "Merge shell bricks with internals in both directions")],
        default="BOTH",
        update=dirty_build)
    random_mat_seed = IntProperty(
        name="Random Seed",
        description="Random seed for material assignment",
        min=0,
        default=1000)
    use_uv_map = BoolProperty(
        name="Use UV Map",
        description="Transfer colors from UV map (if disabled or no UV map found, brick color will be based on RGB of first shader node)",
        default=True,
        update=dirty_material)
    uv_image = PointerProperty(
        type=bpy.types.Image,
        name="UV Image",
        description="UV Image to use for UV Map color transfer (defaults to active UV if left blank)",
        update=dirty_build)
    color_snap = EnumProperty(
        name="Color Mapping",
        description="Method for mapping source material(s)/texture(s) to new materials",
        items=[("NONE", "None", "Use source material(s)"),
               ("RGB", "RGB", "Map RGB values to new materials (similar materials will merge into one material based on threshold)"),
               ("ABS", "ABS", "Map RGB values to nearest ABS Plastic Materials")],
        update=dirty_material,
        default="RGB")
    color_snap_amount = FloatProperty(
        name="Snap Threshold",
        description="Threshold for combining colors together (higher numbers for fewer unique materials generated)",
        subtype="FACTOR",
        precision=3,
        min=0.00001, max=1.0,
        default=0.001,
        update=dirty_build)
    color_snap_specular = FloatProperty(
        name="Specular",
        description="Specular value for the created materials",
        subtype="FACTOR",
        precision=3,
        min=0.0, soft_max=1.0,
        default=0.5,
        update=dirty_material)
    color_snap_roughness = FloatProperty(
        name="Roughness",
        description="Roughness value for the created materials",
        subtype="FACTOR",
        precision=3,
        min=0.0, soft_max=1.0,
        default=0.5,
        update=dirty_material)
    color_snap_sss = FloatProperty(
        name="Subsurface Sattering",
        description="Subsurface scattering value for the created materials",
        subtype="FACTOR",
        precision=3,
        min=0.0, soft_max=1.0,
        default=0.0,
        update=dirty_material)
    color_snap_sss_saturation = FloatProperty(
        name="SSS Saturation",
        description="Saturation of the subsurface scattering for the created materials (relative to base color value)",
        subtype="FACTOR",
        precision=3,
        min=0.0, soft_max=1.0,
        default=1.0,
        update=dirty_material)
    color_snap_ior = FloatProperty(
        name="IOR",
        description="IOR value for the created materials",
        precision=3,
        min=0.0, soft_max=1000.0,
        default=1.45,
        update=dirty_material)
    color_snap_transmission = FloatProperty(
        name="Transmission",
        description="Transmission value for the created materials",
        subtype="FACTOR",
        precision=3,
        min=0.0, soft_max=1.0,
        default=0.0,
        update=dirty_material)
    include_transparency = BoolProperty(
        name="Include Transparency",
        description="Include alpha value of original material color",
        default=True,
        update=dirty_matrix)
    transparent_weight = FloatProperty(
        name="Transparency Weight",
        description="How much the original material's alpha value affects the chosen ABS Plastic Material",
        precision=1,
        min=0, soft_max=2,
        default=1,
        update=dirty_material)
    target_material = StringProperty(
        name="Target Material",
        description="Add material to materials list",
        update=add_material_to_list,
        default="")

    # BRICK DETAIL SETTINGS
    stud_detail = EnumProperty(
        name="Stud Detailing",
        description="Choose where to draw brick studs",
        items=[("NONE", "None", "Don't include brick studs/logos on bricks"),
               ("EXPOSED", "Exposed Bricks", "Include brick studs/logos only on bricks with the top exposed"),
               ("ALL", "All Bricks", "Include brick studs/logos only on bricks with the top exposed")],
        update=dirty_bricks,
        default="EXPOSED")
    logo_type = EnumProperty(
        name="Logo Type",
        description="Choose logo type to draw on brick studs",
        items=[("NONE", "None", "Don't include Brick Logo on bricks", 0),
               # ("LEGO", "LEGO Logo", "Include a LEGO logo on each stud", 1),
               ("CUSTOM", "Custom Logo", "Choose a mesh object to use as the brick stud logo", 2)],
        update=dirty_bricks,
        default="NONE")
    logo_resolution = IntProperty(
        name="Resolution",
        description="Resolution of the brick logo",
        update=dirty_bricks,
        min=1, soft_max=10,
        default=2)
    logo_decimate = FloatProperty(
        name="Decimate",
        description="Decimate the brick logo (lower number for higher resolution)",
        update=dirty_bricks,
        precision=0,
        min=0, max=10,
        default=7.25)
    logo_object = PointerProperty(
        type=bpy.types.Object,
        poll=lambda self, object: object.type == "MESH" and object != self.source_obj and not object.name.startswith("Bricker_{}".format(self.source_obj.name)),
        name="Logo Object",
        description="Select a custom logo object to use on top of each stud",
        update=dirty_bricks)
    logo_scale = FloatProperty(
        name="Logo Scale",
        description="Logo scale relative to stud scale",
        subtype="PERCENTAGE",
        step=1,
        update=dirty_bricks,
        precision=1,
        min=0.0001, soft_max=100.0,
        default=78.0)
    logo_inset = FloatProperty(
        name="Logo Inset",
        description="How far to inset logo to stud",
        subtype="PERCENTAGE",
        step=1,
        update=dirty_bricks,
        precision=1,
        soft_min=0.0, soft_max=100.0,
        default=50.0)
    hidden_underside_detail = EnumProperty(
        name="Underside Detailing of Obstructed Bricks",
        description="Level of detail on underside of bricks with obstructed undersides",
        items=[("FLAT", "Flat", "draw single face on brick underside"),
               ("LOW", "Low", "Hollow out brick underside and draw tube supports"),
               ("MEDIUM", "Medium", "Draw inset tubes below studs and support beams"),
               ("HIGH", "High", "Draw support ticks on 2 by x bricks")],
        update=dirty_bricks,
        default="FLAT")
    exposed_underside_detail = EnumProperty(
        name="Underside Detailing of Exposed Bricks",
        description="Level of detail on underside of bricks with exposed undersides",
        items=[("FLAT", "Flat", "draw single face on brick underside"),
               ("LOW", "Low", "Hollow out brick underside and draw tube supports"),
               ("MEDIUM", "Medium", "Draw inset tubes below studs and support beams"),
               ("HIGH", "High", "Draw support ticks on 2 by x bricks")],
        update=dirty_bricks,
        default="FLAT")
    circle_verts = IntProperty(
        name="Vertices",
        description="Number of vertices in each circle in brick mesh",
        update=update_circle_verts,
        min=4, soft_max=64,
        default=16)
    # BEVEL SETTINGS
    bevel_added = BoolProperty(
        name="Bevel Bricks",
        description="Bevel brick edges and corners for added realism",
        default=False)
    bevel_show_render = BoolProperty(
        name="Render",
        description="Use modifier during render",
        default=True,
        update=update_bevel_render)
    bevel_show_viewport = BoolProperty(
        name="Realtime",
        description="Display modifier in viewport",
        default=True,
        update=update_bevel_viewport)
    bevel_show_edit_mode = BoolProperty(
        name="Edit Mode",
        description="Display modifier in Edit mode",
        default=True,
        update=update_bevel_edit_mode)
    bevel_width = FloatProperty(
        name="Bevel Width",
        description="Bevel amount (relative to Brick Height)",
        subtype="DISTANCE",
        step=1,
        min=0.0, soft_max=10,
        default=0.01,
        update=update_bevel)
    bevel_segments = IntProperty(
        name="Bevel Resolution",
        description="Number of segments for round edges/verts",
        step=1,
        min=1, max=100,
        default=1,
        update=update_bevel)
    bevel_profile = FloatProperty(
        name="Bevel Profile",
        description="The profile shape (0.5 = round)",
        subtype="FACTOR",
        step=1,
        min=0.0, max=1.0,
        default=0.7,
        update=update_bevel)

    # INTERNAL SUPPORTS SETTINGS
    internal_supports = EnumProperty(
        name="Internal Supports",
        description="Choose what type of brick support structure to use inside your model",
        items=[("NONE", "None", "No internal supports"),
               ("COLUMNS", "Columns", "Use columns inside model"),
               ("LATTICE", "Lattice", "Use latice inside model")],
        update=dirty_internal,
        default="NONE")
    lattice_step = IntProperty(
        name="Step",
        description="Distance between cross-beams",
        update=dirty_internal,
        step=1,
        min=2, soft_max=100,
        default=4)
    lattice_height = IntProperty(
        name="Height",
        description="Height of the cross-beams",
        update=dirty_internal,
        step=1,
        min=1, soft_max=100,
        default=1)
    alternate_xy = BoolProperty(
        name="Alternate X and Y",
        description="Alternate back-and-forth and side-to-side beams",
        update=dirty_internal,
        default=True)
    col_thickness = IntProperty(
        name="Thickness",
        description="Thickness of the columns",
        update=dirty_internal,
        min=1, soft_max=100,
        default=2)
    col_step = IntProperty(
        name="Step",
        description="Distance between columns",
        update=dirty_internal,
        step=1,
        min=1, soft_max=100,
        default=2)

    # ADVANCED SETTINGS
    insideness_ray_cast_dir = EnumProperty(
        name="Insideness Ray Cast Direction",
        description="Ray cast method for calculation of insideness",
        items=[("HIGH EFFICIENCY", "High Efficiency", "Reuses single intersection ray cast for insideness calculation"),
               ("X", "X", "Cast rays along X axis for insideness calculations"),
               ("Y", "Y", "Cast rays along Y axis for insideness calculations"),
               ("Z", "Z", "Cast rays along Z axis for insideness calculations"),
               ("XYZ", "XYZ (Best Result)", "Cast rays in all axis directions for insideness calculation (slowest; uses result consistent for at least 2 of the 3 rays)")],
        update=dirty_matrix,
        default="HIGH EFFICIENCY")
    use_normals = BoolProperty(
        name="Use Normals",
        description="Use normals to calculate insideness of bricks (WARNING: May produce inaccurate model if source is not single closed mesh)",
        default=False,
        update=dirty_matrix)
    verify_exposure = BoolProperty(
        name="Verify Exposure",
        description="Run additional insideness calculations (slower, but fixes issue where row(s)/column(s) of extra bricks are drawn)",
        default=False,
        update=dirty_matrix)
    calc_internals = BoolProperty(
        name="Calculate Internals",
        description="Calculate values for bricks inside shell (disable for faster calculation at the loss of the 'ShellThickness' and 'Supports' features)",
        default=True,
        update=dirty_matrix)
    use_local_orient = BoolProperty(
        name="Use Local Orient",
        description="Generate bricks based on local orientation of source object",
        default=False)
    instance_bricks = BoolProperty(
        name="Instance Brick Data",
        description="Use instanced brick mesh data when Split Model is enabled to save on memory and render times",
        update=dirty_build,
        default=True)

    # Deep Cache of bricksdict
    bfm_cache = StringProperty(default="")

    # Blender State for Undo Stack
    blender_undo_state = IntProperty(default=0)

    # Back-End UI Properties
    active_key = IntVectorProperty(default=(-1,-1,-1))

    # Internal Model Properties
    model_created = BoolProperty(default=False)
    brickifying_in_background = BoolProperty(default=False)
    job_progress = IntProperty(
        name="",
        description="",
        subtype="PERCENTAGE",
        default=0,
        soft_min=0,
        soft_max=100,
    )
    num_animated_frames = IntProperty(default=0)
    completed_frames = StringProperty(default="")
    frames_to_animate = IntProperty(default=1)
    stop_background_process = BoolProperty(default=False)
    animated = BoolProperty(default=False)
    armature = BoolProperty(default=False)
    zstep = IntProperty(default=3)
    parent_obj = PointerProperty(type=bpy.types.Object)
    collection = PointerProperty(type=bpy.types.Collection if b280() else bpy.types.Group)
    mat_obj_abs = PointerProperty(type=bpy.types.Object)
    mat_obj_random = PointerProperty(type=bpy.types.Object)
    customized = BoolProperty(default=True)
    brick_sizes_used = StringProperty(default="")  # list of brick_sizes used separated by | (e.g. '5,4,3|7,4,5|8,6,5')
    brick_types_used = StringProperty(default="")  # list of brick_types used separated by | (e.g. 'PLATE|BRICK|STUD')
    model_created_on_frame = IntProperty(default=-1)
    is_smoke = BoolProperty(default=False)
    has_custom_obj1 = BoolProperty(default=False)
    has_custom_obj2 = BoolProperty(default=False)
    has_custom_obj3 = BoolProperty(default=False)

    # Properties for checking of model needs updating
    anim_is_dirty = BoolProperty(default=True)
    material_is_dirty = BoolProperty(default=True)
    model_is_dirty = BoolProperty(default=True)
    build_is_dirty = BoolProperty(default=False)
    bricks_are_dirty = BoolProperty(default=True)
    matrix_is_dirty = BoolProperty(default=True)
    matrix_lost = BoolProperty(default=False)
    internal_is_dirty = BoolProperty(default=True)
    last_logo_type = StringProperty(default="NONE")
    last_split_model = BoolProperty(default=False)
    last_start_frame = IntProperty(default=-1)
    last_stop_frame = IntProperty(default=-1)
    last_source_mid = StringProperty(default="-1,-1,-1")
    last_material_type = StringProperty(default="SOURCE")
    last_shell_thickness = IntProperty(default=1)
    last_internal_supports = StringProperty(default="NONE")
    last_brick_type = StringProperty(default="BRICKS")
    last_matrix_settings = StringProperty(default="")
    last_legal_bricks_only = BoolProperty(default=False)
    last_mat_shell_depth = IntProperty(default=1)
    last_bevel_width = FloatProperty()
    last_bevel_segments = IntProperty()
    last_bevel_profile = IntProperty()
    last_is_smoke = BoolProperty()

    # Bricker Version of Model
    version = StringProperty(default="1.0.4")

    ### BACKWARDS COMPATIBILITY
    # v1.0
    maxBrickScale1 = IntProperty()
    maxBrickScale2 = IntProperty()
    # v1.3
    distOffsetX = FloatProperty()
    distOffsetY = FloatProperty()
    distOffsetZ = FloatProperty()
    # v1.4
    logoDetail = StringProperty("NONE")
    # v1.5
    source_name = StringProperty()
    parent_name = StringProperty()
    # v1.6
    modelLoc = StringProperty(default="-1,-1,-1")
    modelRot = StringProperty(default="-1,-1,-1")
    modelScale = StringProperty(default="-1,-1,-1")
    transformScale = FloatProperty(default=1)
    applyToSourceObject = BoolProperty(default=True)
    exposeParent = BoolProperty(default=False)
    useAnimation = BoolProperty(default=False)
    startFrame = IntProperty(default=1)
    stopFrame = IntProperty(default=10)
    maxWorkers = IntProperty(default=5)
    backProcTimeout = FloatProperty(default=0)
    brickHeight = FloatProperty(default=0.1)
    mergeSeed = IntProperty(default=1000)
    connectThresh = IntProperty(default=1)
    smokeDensity = FloatProperty(default=0.9)
    smokeQuality = FloatProperty(default=1)
    smokeBrightness = FloatProperty(default=1)
    smokeSaturation = FloatProperty(default=1)
    flameColor = FloatVectorProperty(default=[1.0, 0.63, 0.2])
    flameIntensity = FloatProperty(default=4)
    splitModel = BoolProperty(default=False)
    randomLoc = FloatProperty(default=0.01)
    randomRot = FloatProperty(default=0.025)
    brickShell = StringProperty(default="INSIDE")
    calculationAxes = StringProperty(default="XY")
    shellThickness = IntProperty(default=1)
    brickType = StringProperty(default="BRICKS")
    alignBricks = BoolProperty(default=True)
    offsetBrickLayers = IntProperty(default=0)
    maxWidth = IntProperty(default=2)
    maxDepth = IntProperty(default=10)
    mergeType = StringProperty(default="RANDOM")
    legalBricksOnly = BoolProperty(default=True)
    customObject1 = PointerProperty(type=bpy.types.Object)
    customObject2 = PointerProperty(type=bpy.types.Object)
    customObject3 = PointerProperty(type=bpy.types.Object)
    distOffset = FloatVectorProperty(default=(1, 1, 1))
    paintbrushMat = PointerProperty(type=bpy.types.Material)
    materialType = StringProperty(default="NONE")
    customMat = PointerProperty(type=bpy.types.Material)
    internalMat = PointerProperty(type=bpy.types.Material)
    matShellDepth = IntProperty(default=1)
    mergeInternals = StringProperty(default="BOTH")
    randomMatSeed = IntProperty(default=1000)
    useUVMap = BoolProperty(default=True)
    uvImage = PointerProperty(type=bpy.types.Image)
    colorSnap = StringProperty(default="RGB")
    colorSnapAmount = FloatProperty(default=0.001)
    colorSnapSpecular = FloatProperty(0.5)
    colorSnapRoughness = FloatProperty(0.5)
    colorSnapIOR = FloatProperty(1.45)
    colorSnapTransmission = FloatProperty(0.0)
    includeTransparency = BoolProperty(default=True)
    transparentWeight = FloatProperty(default=1)
    targetMaterial = StringProperty(default="")
    studDetail = StringProperty(default="EXPOSED")
    logoType = StringProperty(default="NONE")
    logoResolution = IntProperty(default=2)
    logoDecimate = FloatProperty(default=7.25)
    logoScale = FloatProperty(default=78.0)
    logoInset = FloatProperty(default=50.0)
    hiddenUndersideDetail = StringProperty(default="FLAT")
    exposedUndersideDetail = StringProperty(default="FLAT")
    circleVerts = IntProperty(default=16)
    bevelAdded = BoolProperty(default=False)
    bevelShowRender = BoolProperty(default=True)
    bevelShowViewport = BoolProperty(default=True)
    bevelShowEditmode = BoolProperty(default=True)
    bevelWidth = FloatProperty(default=0.01)
    bevelSegments = IntProperty(default=1)
    bevelProfile = FloatProperty(default=0.7)
    internalSupports = StringProperty(default="NONE")
    latticeStep = IntProperty(default=4)
    latticeHeight = IntProperty(default=1)
    alternateXY = BoolProperty(default=1)
    colThickness = IntProperty(default=2)
    colStep = IntProperty(default=2)
    insidenessRayCastDir = StringProperty(default="HIGH EFFICIENCY")
    useNormals = BoolProperty(default=False)
    verifyExposure = BoolProperty(default=False)
    calcInternals = BoolProperty(default=True)
    useLocalOrient = BoolProperty(default=False)
    instanceBricks = BoolProperty(default=True)
    BFMCache = StringProperty(default="")
    modelCreated = BoolProperty(default=False)
    numAnimatedFrames = IntProperty(default=0)
    framesToAnimate = IntProperty(default=0)
    modelCreatedOnFrame = IntProperty(default=-1)
