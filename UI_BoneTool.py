# -*- encoding:utf-8 -*-

import bpy
from bpy.props import StringProperty, BoolProperty, PointerProperty
from bpy.types import Panel, Operator, PropertyGroup

from . import internalUtils as iu
from . import UIUtils as ui
from . import BoneTool as bt

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################################################################
class DDDBT_propertyGroup(PropertyGroup):
    display_createArmatureFromSelectedEdges_settings: BoolProperty(
        name='createArmatureFromSelectedEdgesSettings',
        default=True,
    )
    basename: StringProperty(
        name=_('Bone Name'),
        description=_('The name of the bone to be created.'),
        default='Bone',
    )

################
class DDDBT_OT_renameChildBonesWithNumber(Operator):
    bl_idname = 'dddbt.rename_child_bones_with_number'
    bl_label = _('Rename Child Bones')
    bl_description = _('Rename all child bones with numbers.')
    bl_options = {'REGISTER', 'UNDO'}

    baseName: StringProperty(
        name=_('Basename'),
        description=_('The basename for renaming.'),
    )

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE' and bpy.context.active_object.mode=='EDIT' and bpy.context.active_bone

    def execute(self, context):
        bt.renameChildBonesWithNumber(bpy.context.active_bone, self.baseName)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.baseName = bpy.context.active_bone.name
        return context.window_manager.invoke_props_dialog(self)

################
class DDDBT_OT_resetStretchTo(Operator):
    bl_idname = 'dddbt.reset_stretch_to'
    bl_label = _('Reset Stretch')
    bl_description = _('Resets the length of all stretch modifiers in the armature to 0.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE'

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        ans = bt.resetStretchTo(arma)
        self.report({'INFO'},
                    iface_('Reset lengths of {ans} stretch modifiers of {arma_name}.').format(arma_name=arma.name, ans=ans))
        return {'FINISHED'}

################
class DDDBT_OT_applyArmatureToRestPose(Operator):
    bl_idname = 'dddbt.apply_armature_to_rest_pose'
    bl_label = _('Current to Rest Pose')
    bl_description = _('Sets the current pose of the active armature as the rest pose.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE'

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        #print(f'arma:{arma.name}')
        bt.applyArmatureToRestPose(arma)
        self.report({'INFO'},
                    iface_('{arma_name} is set as a rest pose.').format(arma_name=arma.name))
        return {'FINISHED'}

################
class DDDBT_OT_createArmatureFromSelectedEdges(Operator):
    bl_idname = 'dddbt.create_armature_from_selected_edges'
    bl_label = _('Edges to Bones')
    bl_description = _('Creates an armature such that the currently selected edge of the active mesh is the bone. The orientation and connections of the bones are automatically set by the distance from the 3D cursor.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'MESH'

    def execute(self, context):
        prop = context.scene.dddtools_bt_prop
        obj = iu.ObjectWrapper(bpy.context.active_object)
        arma = bt.createArmatureFromSelectedEdges(obj, basename=prop.basename)
        if arma:
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

################
class DDDBT_OT_createMeshFromSelectedBones(Operator):
    bl_idname = 'dddbt.create_mesh_from_selected_bones'
    bl_label = _('Bones to Edges')
    bl_description = _('A mesh is created as a child of the armature such that the bones in the active armature selection are the edges. Vertex weights are also set appropriately.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE'

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        obj = bt.createMeshFromSelectedBones(arma)
        if obj:
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

################
class DDDBT_OT_selectAncestralBones(Operator):
    bl_idname = 'dddbt.select_root_bones'
    bl_label = _('Select Ancestral Bones')
    bl_description = _('Select bones that are not related to each other by parent-child relationship. In other words, select only the bones that are closest to the ancestors of the selected bones.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bt.get_selected_bone_names()

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        selected_bones = bt.get_selected_bone_names()
        ancestral_bones = bt.get_ancestral_bones(arma, selected_bones)
        bt.select_bones(arma, ancestral_bones)
        return {'FINISHED'}

################
class DDDBT_OT_printSelectedBoneNamess(Operator):
    bl_idname = 'dddbt.print_selected_bone_names'
    bl_label = _('Print Selected Bone Names')
    bl_description = _('Enumerate the name of the selected bone in the information.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bt.get_selected_bone_names()

    def execute(self, context):
        selected_bones = bt.get_selected_bone_names()
        self.report({'INFO'},
                    iface_('Selected bones are: {selected_bones}').format(
                        selected_bones=sorted(selected_bones)))
        return {'FINISHED'}

################
class DDDBT_PT_BoneTool(Panel):
    bl_idname = 'BT_PT_BoneTool'
    bl_label = 'BoneTool'
    bl_category = 'DDDTools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_bt_prop
        layout = self.layout
        col = layout.column(align=True)
        col.operator(DDDBT_OT_selectAncestralBones.bl_idname)
        col.operator(DDDBT_OT_printSelectedBoneNamess.bl_idname)
        col.operator(DDDBT_OT_renameChildBonesWithNumber.bl_idname)
        col.operator(DDDBT_OT_resetStretchTo.bl_idname)
        col.operator(DDDBT_OT_applyArmatureToRestPose.bl_idname)
        col.operator(DDDBT_OT_createMeshFromSelectedBones.bl_idname)
        display, split = ui.splitSwitch(col, prop, 'display_createArmatureFromSelectedEdges_settings')
        split.operator(DDDBT_OT_createArmatureFromSelectedEdges.bl_idname)
        if display:
            box = col.box().column()
            box.prop(prop, 'basename')

    
################################################################
classes = (
    DDDBT_propertyGroup,
    DDDBT_OT_renameChildBonesWithNumber,
    DDDBT_OT_resetStretchTo,
    DDDBT_OT_applyArmatureToRestPose,
    DDDBT_OT_createArmatureFromSelectedEdges,
    DDDBT_OT_createMeshFromSelectedBones,
    DDDBT_OT_selectAncestralBones,
    DDDBT_OT_printSelectedBoneNamess,
    DDDBT_PT_BoneTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_bt_prop = PointerProperty(type=DDDBT_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_bt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()

