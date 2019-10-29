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

# Module imports
from .common import *
from .general import *
from .colors import *
from .brick.legal_brick_sizes import *
# from .brick.bricks import Bricks
from ..lib.caches import *


def clear_existing_materials(obj, from_idx=0, from_data=False):
    if from_data:
        brick.data.materials.clear(update_data=True)
    else:
        select(obj, active=True)
        obj.active_material_index = from_idx
        for i in range(from_idx, len(obj.material_slots)):
            # remove material slots
            bpy.ops.object.material_slot_remove()


def set_material(obj, mat, to_data=False, overwrite=True):
    if len(obj.data.materials) == 1 and overwrite:
        if obj.data.materials[0] != mat:
            obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    if not to_data:
        link_material_to_object(obj, mat)


def link_material_to_object(obj, mat, index=-1):
    obj.material_slots[index].link = "OBJECT"
    if obj.material_slots[index].material != mat:
        obj.material_slots[index].material = mat


def brick_materials_installed():
    """ checks that 'ABS Plastic Materials' addon is installed and enabled """
    return hasattr(bpy.props, "abs_plastic_materials_module_name")
    # NOTE: The following method was replaced as it was far too slow
    # for mod in addon_utils.modules():
    #     if mod.bl_info["name"] == "ABS Plastic Materials":
    #         return addon_utils.check(mod.__name__)[1]
    # return False


def get_abs_mat_names(all:bool=True):
    """ returns list of ABS Plastic Material names """
    if not brick_materials_installed():
        return []
    scn = bpy.context.scene
    materials = list()
    # get common names (different properties for different versions)
    materials += bpy.props.abs_mats_common if hasattr(bpy.props, "abs_mats_common") else bpy.props.abs_plastic_materials
    # get transparent/uncommon names
    if all or scn.include_transparent:
        materials += bpy.props.abs_mats_transparent
    if all or scn.include_uncommon:
        materials += bpy.props.abs_mats_uncommon
    return materials


def brick_materials_imported():
    scn = bpy.context.scene
    # make sure abs_plastic_materials addon is installed
    if not brick_materials_installed():
        return False
    # check if any of the colors haven't been loaded
    mats = bpy.data.materials.keys()
    for mat_name in get_abs_mat_names():
        if mat_name not in mats:
            return False
    return True


def get_mat_at_face_idx(obj, face_idx):
    """ get material at target face index of object """
    if len(obj.material_slots) == 0:
        return ""
    face = obj.data.polygons[face_idx]
    slot = obj.material_slots[face.material_index]
    mat = slot.material
    mat_name = mat.name if mat else ""
    return mat_name


def get_uv_layer_data(obj):
    """ returns data of active uv texture for object """
    obj_uv_layers = obj.data.uv_layers if b280() else obj.data.uv_textures
    if len(obj_uv_layers) == 0:
        return None
    active_uv = obj_uv_layers.active
    if active_uv is None:
        obj_uv_layers.active = obj_uv_layers[0]
        active_uv = obj_uv_layers.active
    return active_uv.data


def get_first_node(mat, types:list=None):
    """ get first node in material of specified type """
    scn = bpy.context.scene
    if types is None:
        # get material type(s) based on render engine
        if scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
            types = ("BSDF_PRINCIPLED", "BSDF_DIFFUSE")
        elif scn.render.engine == "octane":
            types = ("OCT_DIFFUSE_MAT")
        # elif scn.render.engine == "LUXCORE":
        #     types = ("CUSTOM")
        else:
            types = ()
    # get first node of target type
    mat_nodes = mat.node_tree.nodes
    for node in mat_nodes:
        if node.type in types:
            return node
    # get first node of any BSDF type
    for node in mat_nodes:
        if len(node.inputs) > 0 and node.inputs[0].type == "RGBA":
            return node
    # no valid node was found
    return None


def create_new_material(model_name, rgba, rgba_vals, sss, sat_mat, specular, roughness, ior, transmission, color_snap, color_snap_amount, include_transparency, cur_frame=None):
    """ create new material with specified rgba values """
    scn = bpy.context.scene
    # get or create material with unique color
    min_diff = float("inf")
    snap_amount = 0.000001 if color_snap == "NONE" else color_snap_amount
    if rgba is None:
        return ""
    r0, g0, b0, a0 = rgba
    for i in range(len(rgba_vals)):
        diff = rgba_distance(rgba, rgba_vals[i])
        if diff < min_diff and diff < snap_amount:
            min_diff = diff
            r0, g0, b0, a0 = rgba_vals[i]
            break
    mat_name_end_string = "".join((str(round(r0, 5)), str(round(g0, 5)), str(round(b0, 5)), str(round(a0, 5))))
    mat_name_hash = str(hash_str(mat_name_end_string))[:14]
    mat_name = "Bricker_{n}{f}_{hash}".format(n=model_name, f="_f_%(cur_frame)s" % locals() if cur_frame is not None else "", hash=mat_name_hash)
    mat = bpy.data.materials.get(mat_name)
    mat_is_new = mat is None
    mat = mat or bpy.data.materials.new(name=mat_name)
    # set diffuse and transparency of material
    if mat_is_new:
        mat.diffuse_color = rgba if b280() else rgba[:3]
        if scn.render.engine == "BLENDER_RENDER":
            mat.diffuse_intensity = 1.0
            if a0 < 1.0:
                mat.use_transparency = True
                mat.alpha = rgba[3]
        elif scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane"):
            mat.use_nodes = True
            mat_nodes = mat.node_tree.nodes
            mat_links = mat.node_tree.links
            if scn.render.engine in ("CYCLES", "BLENDER_EEVEE"):
                if b280():
                    # get principled material node
                    principled = mat_nodes.get("Principled BSDF")
                else:
                    # a new material node tree already has a diffuse and material output node
                    output = mat_nodes["Material Output"]
                    # remove default Diffuse BSDF
                    diffuse = mat_nodes["Diffuse BSDF"]
                    mat_nodes.remove(diffuse)
                    # add Principled BSDF
                    principled = mat_nodes.new("ShaderNodeBsdfPrincipled")
                    # link Principled BSDF to output node
                    mat_links.new(principled.outputs["BSDF"], output.inputs["Surface"])
                # set values for Principled BSDF
                principled.inputs[0].default_value = rgba
                principled.inputs[1].default_value = sss
                principled.inputs[3].default_value[:3] = mathutils_mult(Vector(rgba[:3]), sat_mat).to_tuple()
                principled.inputs[5].default_value = specular
                principled.inputs[7].default_value = roughness
                principled.inputs[14].default_value = ior
                principled.inputs[15].default_value = transmission
                if include_transparency:
                    if b280():
                        principled.inputs[18].default_value = 1 - rgba[3]
                    else:
                        # a new material node tree already has a diffuse and material output node
                        output = mat_nodes["Material Output"]
                        # create transparent and mix nodes
                        transparent = mat_nodes.new("ShaderNodeBsdfTransparent")
                        mix = mat_nodes.new("ShaderNodeMixShader")
                        # link these nodes together
                        mat_links.new(principled.outputs["BSDF"], mix.inputs[1])
                        mat_links.new(transparent.outputs["BSDF"], mix.inputs[2])
                        mat_links.new(mix.outputs["Shader"], output.inputs["Surface"])
                        # set mix factor to 1 - alpha
                        mix.inputs[0].default_value = 1 - rgba[3]
            elif scn.render.engine == "octane":
                # a new material node tree already has a diffuse and material output node
                output = mat_nodes["Material Output"]
                # remove default Diffuse shader
                diffuse = mat_nodes["Octane Diffuse Mat"]
                mat_nodes.remove(diffuse)
                # add Octane Glossy shader
                oct_glossy = mat_nodes.new("ShaderNodeOctGlossyMat")
                # set values for Octane Glossy shader
                oct_glossy.inputs[0].default_value = rgba
                oct_glossy.inputs["Specular"].default_value = specular
                oct_glossy.inputs["Roughness"].default_value = roughness
                oct_glossy.inputs["Index"].default_value = ior
                oct_glossy.inputs["Opacity"].default_value = rgba[3]
                oct_glossy.inputs["Smooth"].default_value = True
                mat_links.new(oct_glossy.outputs["OutMat"], output.inputs["Surface"])
            # elif scn.render.engine == "LUXCORE":
            #     # get default Matte shader
            #     matte = mat_nodes["Matte Material"]
            #     # set values for Matte shader
            #     matte.inputs[0].default_value = rgba
            #     matte.inputs["Opacity"].default_value = rgba[3]
    else:
        if scn.render.engine == "BLENDER_RENDER":
            # make sure 'use_nodes' is disabled
            mat.use_nodes = False
            # update material color
            if b280():
                r1, g1, b1, a1 = mat.diffuse_color
            else:
                r1, g1, b1 = mat.diffuse_color
                a1 = mat.alpha
            r2, g2, b2, a2 = get_average(Vector(rgba), Vector((r1, g1, b1, a1)), mat.num_averaged)
            mat.diffuse_color = [r2, g2, b2]
            mat.alpha = a2
        # if scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane", "LUXCORE"):
        if scn.render.engine in ("CYCLES", "BLENDER_EEVEE", "octane"):
            # make sure 'use_nodes' is enabled
            mat.use_nodes = True
            # get first node
            first_node = get_first_node(mat, types=("BSDF_PRINCIPLED", "BSDF_DIFFUSE"))
            # update first node's color
            if first_node:
                rgba1 = first_node.inputs[0].default_value
                new_rgba = get_average(Vector(rgba), Vector(rgba1), mat.num_averaged)
                first_node.inputs[0].default_value = new_rgba
                first_node.inputs[3].default_value[:3] = mathutils_mult(Vector(new_rgba[:3]), sat_mat).to_tuple()
    mat.num_averaged += 1
    return mat_name


def get_material_color(mat_name):
    """ get RGBA value of material """
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        return None
    if mat.use_nodes:
        node = get_first_node(mat)
        if not node:
            return None
        r, g, b = node.inputs[0].default_value[:3]
        if node.type in ("BSDF_GLASS", "BSDF_TRANSPARENT", "BSDF_REFRACTION"):
            a = 0.25
        elif node.type in ("VOLUME_SCATTER", "VOLUME_ABSORPTION", "PRINCIPLED_VOLUME"):
            a = node.inputs["Density"].default_value
        else:
            a = node.inputs[0].default_value[3]
    else:
        if b280():
            r, g, b, a = mat.diffuse_color
        else:
            intensity = mat.diffuse_intensity
            r, g, b = Vector((mat.diffuse_color)) * intensity
            a = mat.alpha if mat.use_transparency else 1.0
    return [r, g, b, a]


def get_brick_rgba(scn, obj, face_idx, point, uv_image=None):
    """ returns RGBA value for brick """
    if face_idx is None:
        return None, None
    # get material based on rgba value of UV image at face index
    image = get_uv_image(scn, obj, face_idx, uv_image)
    if image is not None:
        orig_mat_name = ""
        rgba = get_uv_pixel_color(scn, obj, face_idx, point, image)
    else:
        # get closest material using material slot of face
        orig_mat_name = get_mat_at_face_idx(obj, face_idx)
        rgba = get_material_color(orig_mat_name) if orig_mat_name is not None else None
    return rgba, orig_mat_name
