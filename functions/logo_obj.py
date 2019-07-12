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
from os.path import dirname, abspath

# Addon imports
from .common import *
from .general import *

def remove_doubles(obj):
    select(obj, active=True, only=True)
    for v in obj.data.vertices:
        v.select = True
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.remove_doubles()
    bpy.ops.object.editmode_toggle()
    obj.data.update()


def get_lego_logo(scn, typ, res, decimate, dimensions):
    # update ref_logo
    if typ == "NONE":
        ref_logo = None
    else:
        ref_logo_name = "Bricker_LEGO_Logo_%(res)s_%(decimate)s" % locals()
        ref_logo = bpy.data.objects.get(ref_logo_name)
        if ref_logo is None:
            # get logo text reference with current settings
            logo_txt_ref = get_lego_logoTxtObj(scn, res, "Bricker_LEGO_Logo_Text")
            # convert logo_txt_ref to mesh
            ref_logo = logo_txt_ref.copy()
            ref_logo.data = logo_txt_ref.data.copy()
            ref_logo.name = ref_logo_name
            # convert text to mesh
            link_object(ref_logo, scn)
            unhide(ref_logo)
            select(ref_logo, active=True, only=True)
            bpy.ops.object.convert(target="MESH")
            # remove duplicate verts
            remove_doubles(ref_logo)
            # decimate mesh
            if decimate != 0:
                d_mod = ref_logo.modifiers.new("Decimate", type="DECIMATE")
                d_mod.ratio = 1 - (decimate / 10)
                apply_modifiers(ref_logo)
            safe_unlink(ref_logo)
    return ref_logo


def get_lego_stud_font():
    lego_stud_font = bpy.data.fonts.get("LEGO Stud Font")
    if not lego_stud_font:
        bricker_addon_path = dirname(dirname(abspath(__file__)))
        font_path = "%(bricker_addon_path)s/lib/LEGO_Stud_Font.ttf" % locals()
        lego_stud_font = bpy.data.fonts.load(font_path)
    return lego_stud_font

def get_lego_logoTxtObj(scn, res, name):
    # get logo_txt_ref from Bricker_storage scene
    logo_txt = bpy.data.objects.get(name)
    if logo_txt is None:
        # set up new logo_txt_ref
        c = bpy.data.curves.new("%(name)s_curve" % locals(), "FONT")
        logo_txt = bpy.data.objects.new(name, c)
        safe_unlink(logo_txt)
        logo_txt.name = name
        logo_txt.data.body = "LEGO"
        logo_txt.data.fill_mode = "FRONT"
        logo_txt.data.offset = -0.01
        logo_txt.data.extrude = 0.02
        logo_txt.data.bevel_depth = 0.044
        logo_txt.data.font = get_lego_stud_font()
        logo_txt.data.align_x = "CENTER"
        logo_txt.data.align_y = "CENTER"
        logo_txt.data.space_character = 0.8
    # set logo_txt_ref resolution
    logo_txt.data.resolution_u = res - 1
    logo_txt.data.bevel_resolution = res - 1
    return logo_txt
