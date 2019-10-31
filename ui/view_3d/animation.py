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
from addon_utils import check, paths, enable
from bpy.types import Panel
from bpy.props import *

# Module imports
from ..created_model_uilist import *
from ..matslot_uilist import *
from ...lib.caches import cache_exists
from ...operators.revert_settings import *
from ...operators.brickify import *
from ...operators.customization_tools.bricksculpt import *
from ...functions import *
from ... import addon_updater_ops


class VIEW3D_PT_bricker_animation(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI" if b280() else "TOOLS"
    bl_category    = "Bricker"
    bl_label       = "Animation"
    bl_idname      = "VIEW3D_PT_bricker_animation"
    bl_context     = "objectmode"
    bl_options     = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(self, context):
        if not settings_can_be_drawn():
            return False
        scn, cm, n = get_active_context_info()
        if cm.model_created:
            return False
        return True

    def draw_header(self, context):
        scn, cm, _ = get_active_context_info()
        if not cm.animated:
            self.layout.prop(cm, "use_animation", text="")

    def draw(self, context):
        layout = self.layout
        scn, cm, _ = get_active_context_info()

        col1 = layout.column(align=True)
        col1.active = cm.animated or cm.use_animation
        # col1.scale_y = 0.85
        row = col1.row(align=True)
        row.prop(cm, "start_frame")
        row.prop(cm, "stop_frame")
        if cm.animated:
            col1 = layout.column()
            row = col1.row(align=True)
            row.enabled = False
            row.prop(cm, "last_start_frame")
            row.prop(cm, "last_stop_frame")
        source = cm.source_obj
        self.applied_mods = False
        if source:
            for mod in source.modifiers:
                if mod.type in ("CLOTH", "SOFT_BODY") and mod.show_viewport:
                    self.applied_mods = True
                    t = mod.type
                    if mod.point_cache.frame_end < cm.stop_frame:
                        s = str(max([mod.point_cache.frame_end+1, cm.start_frame]))
                        e = str(cm.stop_frame)
                    elif mod.point_cache.frame_start > cm.start_frame:
                        s = str(cm.start_frame)
                        e = str(min([mod.point_cache.frame_start-1, cm.stop_frame]))
                    else:
                        s = "0"
                        e = "-1"
                    total_skipped = int(e) - int(s) + 1
                    if total_skipped > 0:
                        row = col1.row(align=True)
                        row.label(text="Frames %(s)s-%(e)s outside of %(t)s simulation" % locals())
