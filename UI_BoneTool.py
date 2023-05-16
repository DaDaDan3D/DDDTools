# -*- encoding:utf-8 -*-

import bpy
from bpy.props import StringProperty, BoolProperty, PointerProperty
from bpy.types import Panel, Operator, PropertyGroup

from . import internalUtils as iu
from . import UIUtils as ui
from . import BoneTool as bt

################################################################
class DDDBT_propertyGroup(PropertyGroup):
    display_createArmatureFromSelectedEdges_settings: BoolProperty(
        name='createArmatureFromSelectedEdgesSettings',
        default=True,
    )
    basename: StringProperty(
        name='ボーンの名前',
        description='作成するボーンに付ける名前です',
        default='Bone',
    )

################
class DDDBT_OT_renameChildBonesWithNumber(Operator):
    bl_idname = 'dddbt.rename_child_bones_with_number'
    bl_label = '子ボーンをリネーム'
    bl_description = '全ての子ボーンを番号付きでリネームします'
    bl_options = {'REGISTER', 'UNDO'}

    baseName: StringProperty(
        name='ベースネーム',
        description='基本となる名前',
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
    bl_label = 'リセットストレッチ'
    bl_description = 'アーマチュアに含まれる全てのストレッチモディファイアの長さを 0 にリセットします'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE'

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        ans = bt.resetStretchTo(arma)
        self.report({'INFO'},
                    f'{arma.name}の{ans}個のストレッチモディファイアの長さをリセットしました')
        return {'FINISHED'}

################
class DDDBT_OT_applyArmatureToRestPose(Operator):
    bl_idname = 'dddbt.apply_armature_to_rest_pose'
    bl_label = '現在の姿勢をレストポーズに'
    bl_description = 'アクティブなアーマチュアの現在のポーズをレストポーズとして設定します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE'

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        #print(f'arma:{arma.name}')
        bt.applyArmatureToRestPose(arma)
        self.report({'INFO'},
                    f'{arma.name}をレストポーズとして設定しました')
        return {'FINISHED'}

################
class DDDBT_OT_createArmatureFromSelectedEdges(Operator):
    bl_idname = 'dddbt.create_armature_from_selected_edges'
    bl_label = 'エッジをボーンに'
    bl_description = 'アクティブなメッシュの選択中のエッジをボーンとするようなアーマチュアを作成します。ボーンの向きと接続は 3D カーソルからの距離で自動的に設定されます'
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
    bl_label = 'ボーンをエッジに'
    bl_description = 'アクティブなアーマチュアの選択中のボーンをエッジとするようなメッシュを、アーマチュアの子として作成します。頂点ウェイトも適切に設定されます'
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
class DDDBT_PT_BoneTool(Panel):
    bl_idname = 'BT_PT_BoneTool'
    bl_label = 'BoneTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_bt_prop
        layout = self.layout
        col = layout.column()
        col.operator(DDDBT_OT_renameChildBonesWithNumber.bl_idname)
        col.operator(DDDBT_OT_resetStretchTo.bl_idname)
        col.operator(DDDBT_OT_applyArmatureToRestPose.bl_idname)
        col.operator(DDDBT_OT_createMeshFromSelectedBones.bl_idname)
        display, split = ui.splitSwitch(col, prop, 'display_createArmatureFromSelectedEdges_settings')
        split.operator(DDDBT_OT_createArmatureFromSelectedEdges.bl_idname)
        if display:
            box = col.box().column(align=True)
            box.prop(prop, 'basename')

    
################################################################
classes = (
    DDDBT_propertyGroup,
    DDDBT_OT_renameChildBonesWithNumber,
    DDDBT_OT_resetStretchTo,
    DDDBT_OT_applyArmatureToRestPose,
    DDDBT_OT_createArmatureFromSelectedEdges,
    DDDBT_OT_createMeshFromSelectedBones,
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

