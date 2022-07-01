import bpy
from . import internalUtils as iu
from . import BoneTool as bt

################################################################
class BoneTool_OT_renameChildBonesWithNumber(bpy.types.Operator):
    bl_idname = 'object.rename_child_bones_with_number'
    bl_label = '子ボーンをリネーム'
    bl_description = '全ての子ボーンを番号付きでリネームします'
    bl_options = {'REGISTER', 'UNDO'}

    baseName: bpy.props.StringProperty(
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
class BoneTool_OT_resetStretchTo(bpy.types.Operator):
    bl_idname = 'object.reset_stretch_to'
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
class BoneTool_OT_applyArmatureToRestPose(bpy.types.Operator):
    bl_idname = 'object.apply_armature_to_rest_pose'
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
class BoneTool_PT_BoneTool(bpy.types.Panel):
    bl_idname = 'BT_PT_BoneTool'
    bl_label = 'BoneTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        layout = self.layout
        layout.operator(BoneTool_OT_renameChildBonesWithNumber.bl_idname)
        layout.operator(BoneTool_OT_resetStretchTo.bl_idname)
        layout.operator(BoneTool_OT_applyArmatureToRestPose.bl_idname)
    
################################################################
classes = (
    BoneTool_OT_renameChildBonesWithNumber,
    BoneTool_OT_resetStretchTo,
    BoneTool_OT_applyArmatureToRestPose,
    BoneTool_PT_BoneTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregisterClass():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()

