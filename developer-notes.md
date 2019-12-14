* Add Features
    * SNOT (studs not on top) functionality
    * Add 'exclusion' functionality so that one model doesn’t create bricks where another model already did
    * Generate model with bricks and slopes to more closely approximate original mesh (USER REQUESTED)
    * Add customization for custom object offset, size, and brick scale (amount of bricksdict locations it takes up), default to scale/offset for 1x1 brick with stud
    * Add more brick types
    * Improve brick topology for 3D printing
    * Use shader-based bevel as opposed to geometry-based bevel
    * improve intelligence of `get_first_img_from_nodes` function
        * choose prominent textures
        * ignore normal/bump textures
    * improve speed of `get_first_bsdf_node` function
        * store first nodes of materials so it doesn't have to recalculate every time
    * Improve model connectivity
        * Store each brick parent as a BMVert, with vert.co being the dloc
        * connect each BMVert with an edge if the two bricks are connected
    * (EASY) New animation types (loop, boomerang, etc)
        * this would be implemented in the `handle_animation` function
    * apply modifier to bricker model group instead of each object (requires Blender 2.81)
    * switch `use_blend_file` to `False` for backproc calls (saves memory and time)
        * Use `dump_cm_props()` and `load_cm_props()` code to convert cmlist item to and from dictionaries
        * Figure out a way to maintain parented matrix_world info, etc. for objects appended to background blender instance
    * Switch `calculation_axes` property to expanded bools in user interface

* Fixes
    * when brickified model's parent is rotated, bricks drawn by customizing model are often not rotated correctly
    * Custom object rotation is not maintained when instanced for in bricker model (is this behavior desired?)


# Blender 2.80 Notes


[Blender 2.80 Python API Changes](https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Python_API)

[GPU Shader Module](https://docs.blender.org/api/blender2.8/gpu.html)

[GPU Types](https://docs.blender.org/api/blender2.8/gpu.types.html)

[Updating Scripts from 2.7x](https://en.blender.org/index.php/Dev:2.8/Source/Python/UpdatingScripts)

[UI Design](https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Python_API/UI_DESIGN)

[Update Addons with both Blender 2.8 and 2.7 Support | Moo-Ack!](https://theduckcow.com/2019/update-addons-both-blender-28-and-27-support/)
