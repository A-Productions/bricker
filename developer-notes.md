* Add Features
    * SNOT (studs not on top) functionality
    * Add 'exclusion' functionality so that one model doesn’t create bricks where another model already did
    * Generate model with bricks and slopes to more closely approximate original mesh (USER REQUESTED)
    * Add customization for custom object offset, size, and brick scale (amount of bricksDict locations it takes up), default to scale/offset for 1x1 brick with stud
    * Add more brick types
    * Improve brick topology for 3D printing
    * Use shader-based bevel as opposed to geometry-based bevel
    * When switching to Bricker v1.7, update the following properties to be of subtype 'percentage' (and update values from outdated versions of Bricker):
        * cm.gap
        * cm.logoScale
        * cm.logoInset
    * improve intelligence of `getFirstImgTexNodes` function
        * choose prominent textures
        * ignore normal/bump textures
    * improve speed of `getFirstNode` function
        * store first nodes of materials so it doesn't have to recalculate every time
    * Custom UV unwrapper designed specifically for LEGO bricks
    * Improve model connectivity
        * Store each brick parent as a BMVert, with vert.co being the dictLoc
        * connect each BMVert with an edge if the two bricks are connected
    * (EASY) New animation types (loop, boomerang, etc)
        * this would be implemented in the `handle_animation` function
* Fixes
    * when brickified model's parent is rotated, bricks drawn by customizing model are often not rotated correctly



# Blender 2.80 Notes


[Blender 2.80 Python API Changes](https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Python_API)

[GPU Shader Module](https://docs.blender.org/api/blender2.8/gpu.html)

[GPU Types](https://docs.blender.org/api/blender2.8/gpu.types.html)

[Updating Scripts from 2.7x](https://en.blender.org/index.php/Dev:2.8/Source/Python/UpdatingScripts)

[UI Design](https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Python_API/UI_DESIGN)

[Update Addons with both Blender 2.8 and 2.7 Supoport | Moo-Ack!](https://theduckcow.com/2019/update-addons-both-blender-28-and-27-support/)
