import bpy
from bpy.props import StringProperty
from bpy.types import Panel, Operator

from . import internalUtils as iu
from . import BoneTool as bt

################################################################
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
class DDDBT_PT_BoneTool(Panel):
    bl_idname = 'BT_PT_BoneTool'
    bl_label = 'BoneTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        layout = self.layout
        layout.operator(DDDBT_OT_renameChildBonesWithNumber.bl_idname)
        layout.operator(DDDBT_OT_resetStretchTo.bl_idname)
        layout.operator(DDDBT_OT_applyArmatureToRestPose.bl_idname)
    
################################################################
classes = (
    DDDBT_OT_renameChildBonesWithNumber,
    DDDBT_OT_resetStretchTo,
    DDDBT_OT_applyArmatureToRestPose,
    DDDBT_PT_BoneTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregisterClass():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()

