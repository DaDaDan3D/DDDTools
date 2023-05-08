import bpy
from bpy.props import BoolProperty, IntProperty, PointerProperty, FloatProperty, StringProperty, EnumProperty
from bpy.types import Panel, Operator, PropertyGroup

from . import internalUtils as iu
from . import UIUtils as ui
from . import WeightTool as wt

################################################################
class DDDWT_propertyGroup(PropertyGroup):
    display_cleanupWeightsOfSelectedObjects: BoolProperty(
        name='cleanupWeightsOfSelectedObjects_settings',
        default=True)
    affectBoneMax: IntProperty(
        name='影響ボーンの数',
        description='ウェイトの影響ボーンの数を設定します',
        min=1,
        max=10,
        default=4,
    )

    display_transferWeightsForSelectedObjects: BoolProperty(
        name='transferWeightsForSelectedObjects_settings',
        default=True)
    weightObj: PointerProperty(
        name='転送元',
        description='ウェイトの転送元のメッシュオブジェクト',
        type=bpy.types.Object,
        poll=lambda self, obj: obj and obj.type=='MESH',
    )
    vertexGroup: StringProperty(
        name='頂点グループ',
        description='影響する範囲を選択する頂点グループ名',
    )
    invertVertexGroup: BoolProperty(
        name='反転',
        description='頂点グループの影響を反転します',
        default=False,
    )
    vertMapping: EnumProperty(
        name='頂点マッピング',
        description='頂点を探す方法',
        items=[('NEAREST', '最も近い頂点', '一番近い頂点からコピーします', 'VERTEXSEL', 0),
               ('EDGEINTERP_NEAREST', '最も近い辺の補間', '一番近い辺に降ろした足から補間します', 'EDGESEL', 1),
               ('POLYINTERP_NEAREST', '最も近い面の補間', '一番近い面に降ろした足から補間します', 'FACESEL', 2),
               ('POLYINTERP_VNORPROJ', '投影面の補間', '法線方向に投影して一番近くにヒットした面から補間します', 'SNAP_NORMAL', 3)],
        default='POLYINTERP_NEAREST',
    )
    maxDistance: FloatProperty(
        name='最大距離',
        description='転送できる最大距離(0で無限)',
        subtype='DISTANCE',
        default=0.01,
        min=0.000,
        precision=3,
        step=0.005,
        unit='LENGTH',
    )


################################################################
class DDDWT_OT_resetWeightOfSelectedObjects(bpy.types.Operator):
    bl_idname = 'dddwt.reset_weight_of_selected_objects'
    bl_label = 'ウェイトのリセット'
    bl_description = '選択メッシュのウェイトを取り除きます'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        num = wt.resetWeightOfSelectedObjects()
        if num > 0:
            self.report({'INFO'},
                        f'{num}個のメッシュのウェイトをリセットしました')
        else:
            self.report({'INFO'},
                        f'メッシュが選択されていません')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

################################################################
class DDDWT_OT_cleanupWeightsOfSelectedObjects(bpy.types.Operator):
    bl_idname = 'dddwt.cleanup_weights_of_selected_objects'
    bl_label = 'ウェイトのクリーンアップ'
    bl_description = '選択メッシュのウェイトをクリーンアップします'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_wt_prop
        num = wt.cleanupWeightsOfSelectedObjects(affectBoneMax=prop.affectBoneMax)
        if num > 0:
            self.report({'INFO'},
                        f'{num}個のメッシュのウェイトをクリーンアップしました')
        else:
            self.report({'INFO'},
                        f'メッシュが選択されていません')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

################################################################
class DDDWT_OT_transferWeightsForSelectedObjects(bpy.types.Operator):
    bl_idname = 'dddwt.transfer_weights_for_selected_objects'
    bl_label = 'ウェイトの転送'
    bl_description = '指定したメッシュのウェイトを選択メッシュに転送します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_wt_prop
        return prop.weightObj and bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_wt_prop
        ans = wt.transferWeightsForSelectedObjects(
            iu.ObjectWrapper(prop.weightObj),
            max_distance=prop.maxDistance,
            vert_mapping=prop.vertMapping,
            vertex_group=prop.vertexGroup,
            invert_vertex_group=prop.invertVertexGroup)
        self.report({'INFO'},
                    f'{ans}個のメッシュに転送しました')
        return {'FINISHED'}

################################################################
class DDDWT_OT_equalizeVertexWeightsForMirroredBones(bpy.types.Operator):
    bl_idname = 'dddwt.equalize_vertex_weights_for_mirrored_bones'
    bl_label = '頂点の左右ウェイト均一化'
    bl_description = '指定したメッシュの選択された頂点のウェイトを左右のボーンに対して均等に割り振る'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        mesh = iu.ObjectWrapper(bpy.context.active_object)
        ans = wt.equalizeVertexWeightsForMirroredBones(mesh)
        self.report({'INFO'},
                    f'{mesh.name}の{ans}個の頂点のウェイトを調整しました')
        return {'FINISHED'}

################################################################
class DDDWT_OT_dissolveWeightedBones(bpy.types.Operator):
    bl_idname = 'dddwt.dissolve_weighted_bones'
    bl_label = '選択した骨の溶解'
    bl_description = '選択した骨のウェイトを直近祖先の変形ボーンに移した後、溶解する'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj and obj.type == 'ARMATURE' and obj.mode == 'EDIT' and bpy.context.selected_editable_bones

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        bones = [bone.name for bone in bpy.context.selected_editable_bones]
        ans = wt.dissolveWeightedBones(arma, bones)
        self.report({'INFO'},
                    f'骨を溶解しました。{ans}')
        return {'FINISHED'}

################################################################
class DDDWT_PT_WeightTool(bpy.types.Panel):
    bl_idname = 'WT_PT_WeightTool'
    bl_label = 'WeightTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_wt_prop
        layout = self.layout

        # resetWeightOfSelectedObjects
        layout.operator(DDDWT_OT_resetWeightOfSelectedObjects.bl_idname)

        # cleanupWeightsOfSelectedObjects
        display, split = ui.splitSwitch(layout, prop, 'display_cleanupWeightsOfSelectedObjects')
        split.operator(DDDWT_OT_cleanupWeightsOfSelectedObjects.bl_idname)
        if display:
            box = layout.column(align=True).box().column()
            col = box.column(align=True)
            col.prop(prop, 'affectBoneMax')
        
        # transferWeightsForSelectedObjects
        display, split = ui.splitSwitch(layout, prop, 'display_transferWeightsForSelectedObjects')
        split.operator(DDDWT_OT_transferWeightsForSelectedObjects.bl_idname)
        mesh = bpy.context.active_object
        if display and mesh and mesh.type=='MESH':
            box = layout.column(align=True).box().column()
            col = box.column(align=True)
            col.prop_search(prop, 'weightObj', context.blend_data, 'objects')

            if mesh.vertex_groups:
                row = col.row(align=True)
                row.prop_search(prop, 'vertexGroup', mesh, 'vertex_groups')
                row.prop(prop, 'invertVertexGroup', text='', icon='ARROW_LEFTRIGHT')

            col.prop(prop, 'vertMapping')
            col.prop(prop, 'maxDistance')
        
        # equalizeVertexWeightsForMirroredBones
        layout.operator(DDDWT_OT_equalizeVertexWeightsForMirroredBones.bl_idname)

        # dissolveWeightedBones
        layout.operator(DDDWT_OT_dissolveWeightedBones.bl_idname)
    
################################################################
classes = (
    DDDWT_propertyGroup,
    DDDWT_OT_resetWeightOfSelectedObjects,
    DDDWT_OT_cleanupWeightsOfSelectedObjects,
    DDDWT_OT_transferWeightsForSelectedObjects,
    DDDWT_OT_equalizeVertexWeightsForMirroredBones,
    DDDWT_OT_dissolveWeightedBones,
    DDDWT_PT_WeightTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_wt_prop = PointerProperty(type=DDDWT_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_wt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
