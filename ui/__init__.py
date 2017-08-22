"""
Copyright (C) 2017 Bricks Brought to Life
http://bblanimation.com/
chris@bblanimation.com

Created by Christopher Gearhart

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# system imports
import bpy
from bpy.types import Panel
from bpy.props import *
from .committed_models_list import *
from ..buttons.delete import legoizerDelete
from ..functions import *
from addon_utils import check, paths, enable
props = bpy.props

class LegoModelsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "LEGO Models"
    bl_idname      = "VIEW3D_PT_tools_LEGOizer_lego_models"
    bl_context     = "objectmode"
    bl_category    = "LEGOizer"
    COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        # if blender version is before 2.78, ask user to upgrade Blender
        if bversion() < '002.078.00':
            col = layout.column(align=True)
            col.label('ERROR: upgrade needed', icon='ERROR')
            col.label('LEGOizer requires Blender 2.78+')
            return

        # draw UI list and list actions
        rows = 3
        row = layout.row()
        row.template_list("LEGOizer_UL_items", "", scn, "cmlist", scn, "cmlist_index", rows=rows)

        col = row.column(align=True)
        col.operator("cmlist.list_action", icon='ZOOMIN', text="").action = 'ADD'
        col.operator("cmlist.list_action", icon='ZOOMOUT', text="").action = 'REMOVE'
        col.separator()
        col.operator("cmlist.list_action", icon='TRIA_UP', text="").action = 'UP'
        col.operator("cmlist.list_action", icon='TRIA_DOWN', text="").action = 'DOWN'

        if not listModalRunning():
            col = layout.column(align=True)
            col.operator("cmlist.list_action", icon='FILE_REFRESH', text="Run Auto-Select").action = 'NONE'

        # draw menu options below UI list
        if scn.cmlist_index != -1:
            cm = scn.cmlist[scn.cmlist_index]
            n = cm.source_name
            # first, draw source object text
            if cm.animated or cm.modelCreated:
                col = layout.column(align=True)
                col.label("Source Object: " + cm.source_name)
            else:
                col1 = layout.column(align=True)
                col1.label("Source Object:")
                split = col1.split(align=True, percentage=0.85)
                col = split.column(align=True)
                col.prop_search(cm, "source_name", scn, "objects", text='')
                col = split.column(align=True)
                col.operator("cmlist.set_to_active", icon="EDIT", text="")
                col = layout.column(align=True)

            obj = bpy.data.objects.get(cm.source_name)

            # if use animation is selected, draw animation options
            if cm.useAnimation:
                if cm.animated:
                    row = col.row(align=True)
                    row.operator("scene.legoizer_delete", text="Delete LEGOized Animation", icon="CANCEL").modelType = "ANIMATION"
                    if not modalRunning():
                        col = layout.column(align=True)
                        row = col.row(align=True)
                        row.operator("scene.legoizer_legoize", text="Show Animation", icon="MOD_REMESH").action = "RUN_MODAL"
                    else:
                        col = layout.column(align=True)
                        row = col.row(align=True)
                        row.operator("scene.legoizer_legoize", text="Update Animation", icon="FILE_REFRESH").action = "UPDATE_ANIM"
                else:
                    row = col.row(align=True)
                    if obj:
                        row.active = obj.type == 'MESH'
                    else:
                        row.active = False
                    row.operator("scene.legoizer_legoize", text="LEGOize Animation", icon="MOD_REMESH").action = "ANIMATE"
            # if use animation is not selected, draw modeling options
            else:
                if not cm.animated and not cm.modelCreated:
                    row = col.row(align=True)
                    if obj:
                        row.active = obj.type == 'MESH'
                    else:
                        row.active = False
                    row.operator("scene.legoizer_legoize", text="LEGOize Object", icon="MOD_REMESH").action = "CREATE"
                else:
                    row = col.row(align=True)
                    row.operator("scene.legoizer_delete", text="Delete LEGOized Model", icon="CANCEL").modelType = "MODEL"
                    col = layout.column(align=True)
                    split = col.split(align=True, percentage=.85)
                    col = split.column(align=True)
                    col.operator("scene.legoizer_legoize", text="Update Model", icon="FILE_REFRESH").action = "UPDATE_MODEL"
                    col = split.column(align=True)
                    col.operator("cmlist.select_bricks", icon="BORDER_RECT", text="")

            # sub = row.row(align=True)
            # sub.scale_x = 0.1
            # sub.operator("cgcookie.eye_dropper", icon='EYEDROPPER').target_prop = 'source_name'

            col = layout.column(align=True)
            row = col.row(align=True)
            # remove 'LEGOizer_[source name]_bricks' group if empty
            # if groupExists(LEGOizer_bricks) and len(bpy.data.groups[LEGOizer_bricks].objects) == 0:
            #     legoizerDelete.cleanUp()
            #     bpy.data.groups.remove(bpy.data.groups[LEGOizer_bricks], do_unlink=True)
        else:
            layout.operator("cmlist.list_action", icon='ZOOMIN', text="New LEGO Model").action = 'ADD'

def is_baked(mod):
    return mod.point_cache.is_baked is not False

class AnimationPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Animation"
    bl_idname      = "VIEW3D_PT_tools_LEGOizer_animation"
    bl_context     = "objectmode"
    bl_category    = "LEGOizer"
    bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        if bversion() < '002.078.00':
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if cm.modelCreated:
            return False
        # groupExistsBool = groupExists(LEGOizer_bricks) or groupExists("LEGOizer_%(n)s" % locals()) or groupExists("LEGOizer_%(n)s_refBricks" % locals())
        # if groupExistsBool:
        #     return False
        # cm = scn.cmlist[scn.cmlist_index]
        # n = cm.source_name
        # if not groupExists('LEGOizer_%(n)s' % locals()):
        #     return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]

        if not cm.animated:
            col = layout.column(align=True)
            col.prop(cm, "useAnimation")
        if cm.useAnimation:
            col1 = layout.column(align=True)
            col1.active = cm.animated or cm.useAnimation
            col1.scale_y = 0.85
            row = col1.row(align=True)
            split = row.split(align=True, percentage=0.5)
            col = split.column(align=True)
            col.prop(cm, "startFrame")
            col = split.column(align=True)
            col.prop(cm, "stopFrame")
            source = bpy.data.objects.get(cm.source_name)
            if source is not None:
                self.appliedMods = False
                for mod in source.modifiers:
                    if mod.type in ["CLOTH", "SOFT_BODY"] and mod.show_viewport:
                        self.appliedMods = True
                        t = mod.type
                        if mod.point_cache.frame_end < cm.stopFrame:
                            s = str(max([mod.point_cache.frame_end+1, cm.startFrame]))
                            e = str(cm.stopFrame)
                        elif mod.point_cache.frame_start > cm.startFrame:
                            s = str(cm.startFrame)
                            e = str(min([mod.point_cache.frame_start-1, cm.stopFrame]))
                        else:
                            s = "0"
                            e = "-1"
                        totalSkipped = int(e) - int(s) + 1
                        if totalSkipped > 0:
                            row = col1.row(align=True)
                            row.label("Frames %(s)s-%(e)s outside of %(t)s simulation" % locals())
                        numF = (int(e))-(int(s))+1
                        numF = (cm.stopFrame - cm.startFrame + 1) - totalSkipped
                        if numF == 1:
                            numTimes = "once"
                        elif numF == 2:
                            numTimes = "twice"
                        else:
                            numTimes = "%(numF)s times" % locals()
                        row = col1.row(align=True)
                        row.label("%(t)s simulation will bake %(numTimes)s" % locals())
                        # calculate number of frames to bake
                        totalFramesToBake = 0
                        for i in range(cm.startFrame, cm.stopFrame + 1):
                            totalFramesToBake += i - mod.point_cache.frame_start + 1
                        row = col1.row(align=True)
                        row.label("Num frames to bake: %(totalFramesToBake)s" % locals())
            if (cm.stopFrame - cm.startFrame > 10 and not cm.animated) or self.appliedMods:
                col = layout.column(align=True)
                # col.scale_y = 0.6
                col.label("WARNING: May take a while.")
                col.separator()

class ModelTransformationPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Model Transformation"
    bl_idname      = "VIEW3D_PT_tools_LEGOizer_model_transformation"
    bl_context     = "objectmode"
    bl_category    = "LEGOizer"
    bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        if bversion() < '002.078.00':
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if not cm.modelCreated:
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]
        n = cm.source_name

        col = layout.column(align=True)
        row = col.row(align=True)
        parent = bpy.data.objects['LEGOizer_%(n)s_parent' % locals()]
        row = layout.row()
        row.column().prop(parent, "location")
        if parent.rotation_mode == 'QUATERNION':
            row.column().prop(parent, "rotation_quaternion", text="Rotation")
        elif parent.rotation_mode == 'AXIS_ANGLE':
            row.column().prop(parent, "rotation_axis_angle", text="Rotation")
        else:
            row.column().prop(parent, "rotation_euler", text="Rotation")
        row.column().prop(parent, "scale")
        layout.prop(parent, "rotation_mode")

class ModelSettingsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Model Settings"
    bl_idname      = "VIEW3D_PT_tools_LEGOizer_model_settings"
    bl_context     = "objectmode"
    bl_category    = "LEGOizer"
    COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        if bversion() < '002.078.00':
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]

        col = layout.column(align=True)
        # set up model height variable 'h'
        if cm.modelHeight == -1:
            source = bpy.data.objects.get(cm.source_name)
            if source is not None:
                source_details = bounds(source)
                h = source_details.z.distance
            else:
                h = -1
        else:
            h = cm.modelHeight
        # draw model height if it was set
        if h != -1:
            h = round(h, 2)
            split = col.split(align=True, percentage=.625)
            col1 = split.column(align=True)
            col1.label(" Model Height:" % locals())
            col2 = split.column(align=True)
            col2.alignment = "RIGHT"
            col2.label("%(h)s" % locals())
        row = col.row(align=True)
        row.prop(cm, "brickHeight")
        row = col.row(align=True)
        row.prop(cm, "gap")
        row = col.row(align=True)
        row.prop(cm, "mergeSeed")
        col = layout.column(align=True)
        row = col.row(align=True)
        # row.prop(cm, "preHollow")
        # if cm.preHollow:

        if not cm.useAnimation:
            row = col.row(align=True)
            row.prop(cm, "splitModel")

        row = col.row(align=True)
        row.label("Randomize:")
        row = col.row(align=True)
        split = row.split(align=True, percentage=0.5)
        col1 = split.column(align=True)
        col1.prop(cm, "randomLoc", text="Location")
        col2 = split.column(align=True)
        col2.prop(cm, "randomRot", text="Rotation")

        row = col.row(align=True)
        row.label("Brick Shell:")
        row = col.row(align=True)
        row.prop(cm, "brickShell", text="")
        if cm.brickShell != "Inside Mesh":
            row = col.row(align=True)
            row.prop(cm, "calculationAxes", text="")
        row = col.row(align=True)
        row.prop(cm, "shellThickness", text="Thickness")
        obj = bpy.data.objects.get(cm.source_name)
        if obj is not None and not cm.isWaterTight and listModalRunning():
            row = col.row(align=True)
            # row.scale_y = 0.7
            row.label("(Source is NOT single closed mesh)")
            # row = col.row(align=True)
            # row.operator("scene.make_closed_mesh", text="Make Single Closed Mesh", icon="EDIT")
        row = col.row(align=True)
        row.prop(cm, "useNormals")
        row = col.row(align=True)
        row.prop(cm, "verifyExposure")

class BrickTypesPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Brick Types"
    bl_idname      = "VIEW3D_PT_tools_LEGOizer_brick_types"
    bl_context     = "objectmode"
    bl_category    = "LEGOizer"
    bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        if bversion() < '002.078.00':
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "brickType", text="")

        if cm.brickType == "Custom":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop_search(cm, "customObjectName", scn, "objects", text='')

            col = layout.column(align=True)
            col.label("Distance Offset:")
            split = col.split(align=True, percentage=0.333)

            col = split.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "distOffsetX", text="X")

            col = split.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "distOffsetY", text="Y")

            col = split.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "distOffsetZ", text="Z")
        else:
            col = layout.column(align=True)
            col.label("Max Brick Scales:")
            split = col.split(align=True, percentage=0.5)

            col1 = split.column(align=True)
            row1 = col1.row(align=True)
            row1.prop(cm, "maxBrickScale1", text="1x")

            col2 = split.column(align=True)
            row2 = col2.row(align=True)
            row2.prop(cm, "maxBrickScale2", text="2x")

            if cm.splitModel:
                col = layout.column(align=True)
                row = col.row(align=True)
                row.prop(cm, "originSet")

class MaterialsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Materials"
    bl_idname      = "VIEW3D_PT_tools_LEGOizer_materials"
    bl_context     = "objectmode"
    bl_category    = "LEGOizer"
    bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    @classmethod
    def poll(self, context):
        """ ensures operator can execute (if not, returns false) """
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        if bversion() < '002.078.00':
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "materialType", text="")

        if cm.materialType == "Custom":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop_search(cm, "materialName", bpy.data, "materials", text="")
            if "lego_materials" in bpy.context.user_preferences.addons.keys() and ("LEGO Plastic Black" not in bpy.data.materials.keys() or "LEGO Plastic Trans-Light Green" not in bpy.data.materials.keys()):
                row = col.row(align=True)
                row.operator("scene.append_lego_materials", text="Import LEGO Materials", icon="IMPORT")
            if cm.modelCreated:
                col = layout.column(align=True)
                row = col.row(align=True)
                row.operator("scene.legoizer_apply_material", icon="FILE_TICK").action = "CUSTOM"
        if cm.materialType == "Use Source Materials":
            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(cm, "mergeInconsistentMats")
            if cm.shellThickness > 1:
                col = layout.column(align=True)
                row = col.row(align=True)
                row.prop(cm, "matShellDepth")
                row = col.row(align=True)
                row.label("Internal:")
                row = col.row(align=True)
                row.prop_search(cm, "internalMatName", bpy.data, "materials", text="")
                if "lego_materials" in bpy.context.user_preferences.addons.keys() and ("LEGO Plastic Black" not in bpy.data.materials.keys() or "LEGO Plastic Trans-Light Green" not in bpy.data.materials.keys()):
                    row = col.row(align=True)
                    row.operator("scene.append_lego_materials", text="Import LEGO Materials", icon="IMPORT")
                if cm.modelCreated:
                    if cm.splitModel:
                        col = layout.column(align=True)
                        col.label("Run 'Update Model' to apply changes")
                    else:
                        col = layout.column(align=True)
                        row = col.row(align=True)
                        row.operator("scene.legoizer_apply_material", icon="FILE_TICK").action = "INTERNAL"

class DetailingPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Detailing"
    bl_idname      = "VIEW3D_PT_tools_LEGOizer_detailing"
    bl_context     = "objectmode"
    bl_category    = "LEGOizer"
    bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        if bversion() < '002.078.00':
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if cm.brickType == "Custom":
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label("Studs:")
        row = col.row(align=True)
        row.prop(cm, "studDetail", text="")
        if cm.studDetail != "None":
            row = col.row(align=True)
            row.prop(cm, "studVerts")
            col = layout.column(align=True)
        row = col.row(align=True)
        row.label("Logo:")
        row = col.row(align=True)
        row.prop(cm, "logoDetail", text="")
        if cm.logoDetail != "None":
            row = col.row(align=True)
            row.prop(cm, "logoResolution", text="Logo Resolution")
            col = layout.column(align=True)
        row = col.row(align=True)
        row.label("Underside Hidden:")
        row = col.row(align=True)
        row.prop(cm, "hiddenUndersideDetail", text="")
        row = col.row(align=True)
        row.label("Underside Exposed:")
        row = col.row(align=True)
        row.prop(cm, "exposedUndersideDetail", text="")

class SupportsPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Supports"
    bl_idname      = "VIEW3D_PT_tools_LEGOizer_supports"
    bl_context     = "objectmode"
    bl_category    = "LEGOizer"
    bl_options     = {"DEFAULT_CLOSED"}
    COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        if bversion() < '002.078.00':
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]

        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(cm, "internalSupports", text="")
        col = layout.column(align=True)
        row = col.row(align=True)
        if cm.internalSupports == "Lattice":
            row.prop(cm, "latticeStep")
            row = col.row(align=True)
            row.prop(cm, "alternateXY")
        elif cm.internalSupports == "Columns":
            row.prop(cm, "colStep")
            row = col.row(align=True)
            row.prop(cm, "colThickness")

class BevelPanel(Panel):
    bl_space_type  = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_label       = "Bevel"
    bl_idname      = "VIEW3D_PT_tools_LEGOizer_bevel"
    bl_context     = "objectmode"
    bl_category    = "LEGOizer"
    COMPAT_ENGINES = {"CYCLES", "BLENDER_RENDER"}

    @classmethod
    def poll(self, context):
        scn = context.scene
        if scn.cmlist_index == -1:
            return False
        if bversion() < '002.078.00':
            return False
        cm = scn.cmlist[scn.cmlist_index]
        if not cm.modelCreated and not cm.animated:
            return False
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        cm = scn.cmlist[scn.cmlist_index]
        n = cm.source_name

        col = layout.column(align=True)
        row = col.row(align=True)
        try:
            testBrick = bpy.data.groups['LEGOizer_%(n)s_bricks' % locals()].objects[0]
            testBrick.modifiers[testBrick.name + '_bevel']
            row.prop(cm, "bevelWidth", text="Width")
            row = col.row(align=True)
            row.prop(cm, "bevelSegments", text="Segments")
            row = col.row(align=True)
            row.prop(cm, "bevelProfile", text="Profile")
            row = col.row(align=True)
            row.operator("scene.legoizer_bevel", text="Remove Bevel", icon="CANCEL").action = "REMOVE"
        except:
            row.operator("scene.legoizer_bevel", text="Bevel bricks", icon="MOD_BEVEL").action = "CREATE"
