import os
import bpy
from bpy.types import Panel, Operator, PropertyGroup, UIList, Object, Text
from bpy.props import PointerProperty, CollectionProperty, StringProperty, EnumProperty, BoolProperty, IntProperty, FloatProperty

from . import UIUtils as ui
from . import VRMTool as vt

################################################################
class DDDVT_MaterialListItem(PropertyGroup):
    material: PointerProperty(type=bpy.types.Material)

################
class DDDVT_propertyGroup(PropertyGroup):
    display_colliderTools: BoolProperty(
        name='ColliderTools',
        default=True)

    display_add_collider_settings: BoolProperty(
        name='AddColliderSettings',
        default=True)
    mesh: PointerProperty(
        name='対象メッシュ',
        description='コライダーの幅を計算するメッシュを指定します',
        type=Object,
        poll=lambda self, obj: obj and obj.type=='MESH',
    )

    display_prepareToExportVRM: BoolProperty(
        name='prepareToExportVRMの設定',
        default=True)

    skeleton: PointerProperty(
        name='Skeleton',
        description='VRMのスケルトン',
        type=Object,
        poll=lambda self, obj: obj and obj.type=='ARMATURE',
    )

    triangulate: BoolProperty(
        name='三角化',
        description='ポリゴンを三角化します',
        default=False,
    )

    bs_json: PointerProperty(
        name='blendshape',
        description='ブレインドシェイプを定義する.jsonテキスト',
        type=Text,
    )

    sb_json: PointerProperty(
        name='springBone',
        description='スプリングボーンを定義する.jsonテキスト',
        type=Text,
    )

    notExportBoneGroup: StringProperty(
        name='出力しないボーングループ',
        description='指定したボーングループを溶解します',
    )

    mergedName: StringProperty(
        name='マージしたメッシュに付ける名前',
        description='blendshape に含まれない残りのメッシュをマージしたメッシュに付ける名前を指定します',
        default='MergedBody',
    )

    saveAsExport: BoolProperty(
        name='実行後セーブ',
        description='実行後、*.export.blend として自動的に保存します',
        default=True)

    sortMaterialSlot: BoolProperty(
        name='マテリアルをソート',
        description='マテリアルをリストで指定した順番にソートします。マテリアル順指定リストは MaterialTool パネルにあります',
        default=False)
    removeUnusedMaterialSlots: BoolProperty(
        name='未使用マテリアルを削除',
        description='未使用のマテリアルをスロットから削除します',
        default=False)

    display_removePolygons_settings: BoolProperty(
        name='RemovePolygonsSettings',
        default=False)
    removePolygons: BoolProperty(
        name='ポリゴン削除',
        description='条件によってポリゴンを削除します',
        default=False)
    interval: IntProperty(
        name='判定の粗さ',
        description='透明ポリゴン判定時に何分の一のサイズのテクスチャで作業するかを指定します。大きくすると高速になりますが、判定が粗くなります',
        min=1,
        max=16,
        default=4,
    )
    alphaThreshold: FloatProperty(
        name='アルファ値の閾値',
        description='透明ポリゴン判定時に、この値以下のアルファ値を透明と見なします',
        #subtype='FACTOR',
        default=0.05,
        min=0.00,
        max=1.00,
        precision=2,
        step=1,
    )
    excludeMaterials: CollectionProperty(
        name='除外マテリアルリスト',
        description='透明ポリゴンを削除する際、透明でも削除しないマテリアルのリストです',
        type=DDDVT_MaterialListItem)
    excludeMaterialsIndex: IntProperty(
        name='除外マテリアルリストインデックス'
    )
    excludeMaterialSelector: PointerProperty(
        name='マテリアル選択',
        description='除外マテリアルリストに追加するマテリアルを選択します',
        type=bpy.types.Material)


################################################################
class DDDVT_OT_addCollider(Operator):
    bl_idname = 'dddvt.add_collider'
    bl_label = 'コライダ追加'
    bl_description = 'メッシュの大きさに合わせたコライダを追加します'
    bl_options = {'REGISTER', 'UNDO'}

    t_from: FloatProperty(
        name='開始位置',
        description='開始位置をボーンのヘッドからの距離(m)として指定します',
        subtype='DISTANCE',
        default=0,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    auto_t_to: BoolProperty(
        name='終了位置を自動計算',
        description='終了位置をボーンに合わせて自動的に計算します',
        default=True)
    t_to: FloatProperty(
        name='終了位置',
        description='終了位置をボーンのヘッドからの距離(m)として指定します',
        subtype='DISTANCE',
        default=0.5,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    t_step: FloatProperty(
        name='間隔',
        description='コライダ同士の間隔(m)を指定します',
        subtype='DISTANCE',
        default=0.03,
        min=0.01,
        max=0.5,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    numberOfRays: IntProperty(
        name='レイの本数',
        description='レイを投射する本数を設定します',
        min=3,
        max=100,
        default=32,
    )
    radius: FloatProperty(
        name='レイの最大半径',
        description='レイを投射する円の最大半径を設定します',
        subtype='DISTANCE',
        default=0.3,
        min=0.000,
        max=1.000,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    insideToOutside: EnumProperty(
        name='レイの方向',
        description='レイを投射する向きを設定します',
        items=[('IN_TO_OUT', '内から広がる', 'レイを内側から外側へ投射します'),
               ('OUT_TO_IN', '外から集まる', 'レイを外側から内側へ投射します')],
        default='IN_TO_OUT',
    )

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return prop.mesh and prop.mesh.type=='MESH' and\
            bpy.context.active_object and\
            bpy.context.active_object.type == 'ARMATURE' and\
            bpy.context.active_object.mode=='POSE' and\
            bpy.context.active_bone

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        if self.auto_t_to:
            t_to = None
        else:
            t_to = self.t_to
        return vt.addCollider(self.mesh, bpy.context.active_object,
                              t_from=self.t_from,
                              t_to=t_to,
                              t_step=self.t_step,
                              numberOfRays=self.numberOfRays,
                              radius=self.radius,
                              insideToOutside=(self.insideToOutside=='IN_TO_OUT'))

    def invoke(self, context, event):
        prop = context.scene.dddtools_vt_prop
        self.mesh = prop.mesh
        return self.execute(context)
      
    def draw(self, context):
        col = self.layout.column()

        col.prop(self, 't_from')
        col.prop(self, 'auto_t_to')
        col2 = col.column()
        col2.enabled = not self.auto_t_to
        col2.prop(self, 't_to')
        col.prop(self, 't_step')
        col.separator()
        col.prop(self, 'numberOfRays')
        col.prop(self, 'radius')
        col.prop(self, 'insideToOutside')

################
class DDDVT_OT_removeAllUneditableEmptyChildren(Operator):
    bl_idname = 'dddvt.remove_all_uneditable_empty_children'
    bl_label = '不要EMPTY削除'
    bl_description = '指定したスケルトンの子の、手動で削除しても消えない EMPTY を強制的に削除します。'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return prop.skeleton and prop.skeleton.type=='ARMATURE'

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        removed = vt.removeAllUneditableEmptyChildren(prop.skeleton)
        if removed:
            self.report({'INFO'},
                        f'{len(removed)} 個の EMPTY を削除しました: {removed}')
            return {'FINISHED'}
        else:
            self.report({'INFO'},
                        '不要な EMPTY はありませんでした')
            return {'CANCELLED'}

################
class DDDVT_OT_prepareToExportVRM(Operator):
    bl_idname = 'dddvt.prepare_to_export_vrm'
    bl_label = 'VRM 出力前の準備'
    bl_description = 'VRM を出力するために、メッシュをマージし、不要な骨を溶解し、ウェイトのクリーンアップを行い、ブレンドシェイプの設定を行います'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return vt.getAddon() and\
            prop.skeleton and prop.skeleton.type=='ARMATURE' and\
            prop.bs_json and\
            bpy.context.mode == 'OBJECT'

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        excludeMaterials = set([mat.material.name for mat in prop.excludeMaterials])
        print(excludeMaterials)

        mt_prop = context.scene.dddtools_mt_prop
        if prop.sortMaterialSlot and mt_prop.orderList:
            materialOrderList = [item.material.name for item in mt_prop.orderList]

        else:
            materialOrderList = None

        if prop.sb_json:
            sb_json = prop.sb_json.name
        else:
            sb_json = None
        mergedObjs = vt.prepareToExportVRM(skeleton=prop.skeleton.name,
                                           triangulate=prop.triangulate,
                                           removeTransparentPolygons=prop.removePolygons,
                                           interval=prop.interval,
                                           alphaThreshold=prop.alphaThreshold,
                                           excludeMaterials=excludeMaterials,
                                           bs_json=prop.bs_json.name,
                                           sb_json=sb_json,
                                           notExport=prop.notExportBoneGroup,
                                           materialOrderList=materialOrderList,
                                           removeUnusedMaterialSlots=prop.removeUnusedMaterialSlots)
        
        if mergedObjs:
            if None in mergedObjs:
                mergedObjs[None].rename(prop.mergedName)

            base, ext = os.path.splitext(bpy.data.filepath)
            filepath = f'{base}.export{ext}'
            return bpy.ops.wm.save_as_mainfile(filepath=filepath)
        else:
            return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

################
class DDDVT_OT_openAddonPage(Operator):
    bl_idname = 'dddvt.url_open_vrm_addon_for_blender'
    bl_label = 'VRM_Addon_for_Blender のページを開く'
    bl_description = 'VRM_Addon_for_Blender のサイトページを開きます'
    bl_options = {'INTERNAL'}

    def execute(self, context):
        bpy.ops.wm.url_open(url='https://vrm-addon-for-blender.info')
        return {'FINISHED'}

################
class DDDVT_UL_MaterialList(UIList):
    bl_idname = 'DDDVT_UL_MaterialList'

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        material = item.material
        if material:
            split = layout.split(factor=0.9)
            split.label(text=material.name, translate=False)
            split.operator(DDDVT_OT_RemoveExcludeMaterial.bl_idname,
                           text='', icon='X').index = index

################
class DDDVT_OT_AddExcludeMaterial(Operator):
    bl_idname = 'dddvt.add_exclude_material'
    bl_label = 'Add'
    bl_description = '除外マテリアルリストにマテリアルを追加します'
    
    @classmethod
    def poll(cls, context):
        prop = context.scene.dddtools_vt_prop
        selected_material = prop.excludeMaterialSelector
        return selected_material and\
            selected_material.name not in [mat.material.name for mat in prop.excludeMaterials]
    
    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        selected_material = prop.excludeMaterialSelector
        new_item = prop.excludeMaterials.add()
        new_item.material = bpy.data.materials[selected_material.name]
        
        return {'FINISHED'}

class DDDVT_OT_RemoveExcludeMaterial(Operator):
    bl_idname = 'dddvt.remove_exclude_material'
    bl_label = 'Remove Exclude Material'
    bl_description = '除外マテリアルリストからマテリアルを削除します'
    
    index: IntProperty()

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        prop.excludeMaterials.remove(self.index)
        return {'FINISHED'}

################
class DDDVT_OT_RemoveTransparentPolygons(Operator):
    bl_idname = 'dddvt.remove_transparent_polygons'
    bl_label = '削除実行'
    bl_description = 'VRM のマテリアルを使用している指定したオブジェクトから、透明なポリゴンを削除します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return vt.getAddon() and bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        excludeMaterials = set([mat.material.name for mat in prop.excludeMaterials])
        print(excludeMaterials)
        for obj in bpy.context.selected_objects:
            vt.removeTransparentPolygons(obj,
                                         interval=prop.interval,
                                         alphaThreshold=prop.alphaThreshold,
                                         excludeMaterials=excludeMaterials)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

################
class DDDVT_PT_VRMTool(Panel):
    bl_idname = 'VT_PT_VRMTool'
    bl_label = 'VRMTool'
    bl_category = 'DDDTools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_vt_prop
        layout = self.layout

        layout.prop_search(prop, 'skeleton', context.blend_data, 'objects')

        # コライダーツール
        display, split = ui.splitSwitch(layout, prop, 'display_colliderTools')
        split.label(text='コライダー関連')
        if display:
            col = layout.box().column()
            col.operator(DDDVT_OT_removeAllUneditableEmptyChildren.bl_idname)

            # addCollider
            display, split = ui.splitSwitch(col, prop, 'display_add_collider_settings')
            split.operator(DDDVT_OT_addCollider.bl_idname)
            if display:
                col.prop_search(prop, 'mesh', context.blend_data, 'objects')

        # prepareToExportVRM
        display, split = ui.splitSwitch(layout, prop, 'display_prepareToExportVRM')
        split.operator(DDDVT_OT_prepareToExportVRM.bl_idname)
        if display:
            col = layout.box().column(align=True)
            if vt.getAddon():
                col.prop(prop, 'triangulate')
                col.prop_search(prop, 'bs_json', context.blend_data, 'texts')
                col.prop_search(prop, 'sb_json', context.blend_data, 'texts')
                if prop.skeleton:
                    col.prop_search(prop, 'notExportBoneGroup', prop.skeleton.pose,
                                    'bone_groups')
                col.prop(prop, 'mergedName')
                col.prop(prop, 'saveAsExport')
                col.prop(prop, 'sortMaterialSlot')
                col.prop(prop, 'removeUnusedMaterialSlots')
                
                # removePolygons
                col.separator()
                display, split = ui.splitSwitch(col, prop, 'display_removePolygons_settings')
                split.prop(prop, 'removePolygons')
                if display:
                    box = col.box().column(align=True)
                    box.prop(prop, 'interval')
                    box.prop(prop, 'alphaThreshold')

                    box.separator()
                    box.label(text='除外マテリアルリスト')
                    box.template_list(DDDVT_UL_MaterialList.bl_idname, '',
                                      prop, 'excludeMaterials',
                                      prop, 'excludeMaterialsIndex')
                    
                    box.prop_search(prop, 'excludeMaterialSelector',
                                    bpy.data, 'materials', text='')
                    box.operator(DDDVT_OT_AddExcludeMaterial.bl_idname,
                                 text='Add', icon='ADD')

                    box.separator()
                    box.operator(DDDVT_OT_RemoveTransparentPolygons.bl_idname)

            else:
                col.label(text='VRM_Addon_for_Blender がインストールされていません。',
                          icon='INFO')
                col.operator(DDDVT_OT_openAddonPage.bl_idname)

################
classes = (
    DDDVT_MaterialListItem,
    DDDVT_propertyGroup,
    DDDVT_OT_addCollider,
    DDDVT_OT_removeAllUneditableEmptyChildren,
    DDDVT_OT_prepareToExportVRM,
    DDDVT_OT_openAddonPage,
    DDDVT_UL_MaterialList,
    DDDVT_OT_AddExcludeMaterial,
    DDDVT_OT_RemoveExcludeMaterial,
    DDDVT_OT_RemoveTransparentPolygons,
    DDDVT_PT_VRMTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_vt_prop = PointerProperty(type=DDDVT_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_vt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
