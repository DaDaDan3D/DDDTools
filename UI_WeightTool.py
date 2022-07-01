import bpy
from . import internalUtils as iu
from . import WeightTool as wt

################################################################
class WeightTool_propertyGroup(bpy.types.PropertyGroup):
    display_cleanupWeightsOfSelectedObjects: bpy.props.BoolProperty(
        name='cleanupWeightsOfSelectedObjects_settings',
        default=True)
    affectBoneMax: bpy.props.IntProperty(
        name='影響ボーンの数',
        description='ウェイトの影響ボーンの数を設定します',
        min=1,
        max=10,
        default=4,
    )

    display_transferWeightsForSelectedObjects: bpy.props.BoolProperty(
        name='transferWeightsForSelectedObjects_settings',
        default=True)
    weightObj: bpy.props.PointerProperty(
        name='転送元',
        description='ウェイトの転送元のメッシュオブジェクト',
        type=bpy.types.Object,
        poll=lambda self, obj: obj and obj.type=='MESH',
    )
    vertexGroup: bpy.props.StringProperty(
        name='頂点グループ',
        description='影響する範囲を選択する頂点グループ名',
    )
    invertVertexGroup: bpy.props.BoolProperty(
        name='反転',
        description='頂点グループの影響を反転します',
        default=False,
    )
    vertMapping: bpy.props.EnumProperty(
        name='頂点マッピング',
        description='頂点を探す方法',
        items=[('NEAREST', '最も近い頂点', '一番近い頂点からコピーします', 'VERTEXSEL', 0),
               ('EDGEINTERP_NEAREST', '最も近い辺の補間', '一番近い辺に降ろした足から補間します', 'EDGESEL', 1),
               ('POLYINTERP_NEAREST', '最も近い面の補間', '一番近い面に降ろした足から補間します', 'FACESEL', 2),
               ('POLYINTERP_VNORPROJ', '投影面の補間', '法線方向に投影して一番近くにヒットした面から補間します', 'SNAP_NORMAL', 3)],
        default='POLYINTERP_NEAREST',
    )
    maxDistance: bpy.props.FloatProperty(
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
class WeightTool_OT_resetWeightOfSelectedObjects(bpy.types.Operator):
    bl_idname = 'object.reset_weight_of_selected_objects'
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
class WeightTool_OT_cleanupWeightsOfSelectedObjects(bpy.types.Operator):
    bl_idname = 'object.cleanup_weights_of_selected_objects'
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
class WeightTool_OT_transferWeightsForSelectedObjects(bpy.types.Operator):
    bl_idname = 'object.transfer_weights_for_selected_objects'
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
class WeightTool_OT_equalizeVertexWeightsForMirroredBones(bpy.types.Operator):
    bl_idname = 'object.equalize_vertex_weights_for_mirrored_bones'
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
class WeightTool_OT_dissolveWeightedBones(bpy.types.Operator):
    bl_idname = 'object.dissolve_weighted_bones'
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
class WeightTool_PT_WeightTool(bpy.types.Panel):
    bl_idname = 'WT_PT_WeightTool'
    bl_label = 'WeightTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_wt_prop
        layout = self.layout

        # resetWeightOfSelectedObjects
        layout.operator(WeightTool_OT_resetWeightOfSelectedObjects.bl_idname)

        # cleanupWeightsOfSelectedObjects
        split = layout.split(factor=0.15, align=True)
        if prop.display_cleanupWeightsOfSelectedObjects:
            split.prop(prop, 'display_cleanupWeightsOfSelectedObjects',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_cleanupWeightsOfSelectedObjects',
                       text='', icon='RIGHTARROW')
        split.operator(WeightTool_OT_cleanupWeightsOfSelectedObjects.bl_idname)
        if prop.display_cleanupWeightsOfSelectedObjects:
            box = layout.column(align=True).box().column()
            col = box.column(align=True)
            col.prop(prop, 'affectBoneMax')
        
        # transferWeightsForSelectedObjects
        split = layout.split(factor=0.15, align=True)
        if prop.display_transferWeightsForSelectedObjects:
            split.prop(prop, 'display_transferWeightsForSelectedObjects',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_transferWeightsForSelectedObjects',
                       text='', icon='RIGHTARROW')
        split.operator(WeightTool_OT_transferWeightsForSelectedObjects.bl_idname)
        mesh = bpy.context.active_object
        if prop.display_transferWeightsForSelectedObjects and mesh and mesh.type=='MESH':
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
        layout.operator(WeightTool_OT_equalizeVertexWeightsForMirroredBones.bl_idname)

        # dissolveWeightedBones
        layout.operator(WeightTool_OT_dissolveWeightedBones.bl_idname)
    
################################################################
classes = (
    WeightTool_propertyGroup,
    WeightTool_OT_resetWeightOfSelectedObjects,
    WeightTool_OT_cleanupWeightsOfSelectedObjects,
    WeightTool_OT_transferWeightsForSelectedObjects,
    WeightTool_OT_equalizeVertexWeightsForMirroredBones,
    WeightTool_OT_dissolveWeightedBones,
    WeightTool_PT_WeightTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_wt_prop = bpy.props.PointerProperty(type=WeightTool_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_wt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
