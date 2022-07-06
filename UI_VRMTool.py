import os
import bpy
from . import VRMTool as vt

################################################################
class VRMTool_propertyGroup(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(
        name='Mesh',
        description='幅を計算するメッシュ',
        type=bpy.types.Object,
        poll=lambda self, obj: obj and obj.type=='MESH',
    )

    display_prepareToExportVRM: bpy.props.BoolProperty(
        name='prepareToExportVRMの設定',
        default=True)

    skeleton: bpy.props.PointerProperty(
        name='Skeleton',
        description='VRMのスケルトン',
        type=bpy.types.Object,
        poll=lambda self, obj: obj and obj.type=='ARMATURE',
    )

    triangulate: bpy.props.BoolProperty(
        name='三角化',
        description='ポリゴンを三角化します',
        default=False,
    )

    bs_json: bpy.props.PointerProperty(
        name='blendshape',
        description='ブレインドシェイプを定義する.jsonテキスト',
        type=bpy.types.Text,
    )

    notExportBoneGroup: bpy.props.StringProperty(
        name='出力しないボーングループ',
        description='指定したボーングループを溶解します',
    )

    mergedName: bpy.props.StringProperty(
        name='マージしたメッシュに付ける名前',
        description='blendshape に含まれない残りのメッシュをマージしたメッシュに付ける名前を指定します',
        default='MergedBody',
    )

    saveAsExport: bpy.props.BoolProperty(
        name='実行後セーブ',
        description='実行後、*.export.blend として自動的に保存します',
        default=True)

################################################################
class VRMTool_OT_addCollider(bpy.types.Operator):
    bl_idname = 'object.add_collider'
    bl_label = 'コライダ追加'
    bl_description = 'メッシュの大きさに合わせたコライダを追加します'
    bl_options = {'REGISTER', 'UNDO'}

    numberOfColliders: bpy.props.IntProperty(
        name='コライダの数',
        description='追加するコライダの数を設定します',
        min=1,
        max=16,
        default=4,
    )

    numberOfRays: bpy.props.IntProperty(
        name='レイの本数',
        description='レイを投射する本数を設定します',
        min=1,
        max=100,
        default=8,
    )

    radius: bpy.props.FloatProperty(
        name='レイの最大半径',
        description='レイを投射する円の最大半径を設定します',
        subtype='DISTANCE',
        default=0.3,
        min=0.000,
        max=3.000,
        precision=3,
        step=0.005,
        unit='LENGTH',
    )
    
    insideToOutside: bpy.props.EnumProperty(
        name='レイの方向',
        description='レイを投射する向きを設定します',
        items=[('IN_TO_OUT', '内から広がる', 'レイを内側から外側へ投射します'),
               ('OUT_TO_IN', '外から集まる', 'レイを外側から内側へ投射します')],
        default='IN_TO_OUT',
    )

    fitMode: bpy.props.EnumProperty(
        name='算出方法',
        description='コライダの大きさの算出方法を設定します',
        items=[('MIN', 'min', '最小'),
               ('MAX', 'max', '最大'),
               ('MEAN', 'mean', '平均'),
               ('HARMONIC_MEAN', 'harmonic_mean', '調和平均'),
               ('MEDIAN', 'median', '中央値')],
        default='MEDIAN',
    )

    offset: bpy.props.FloatProperty(
        name='オフセット',
        description='コライダの大きさを全体的にオフセット調整します',
        subtype='DISTANCE',
        default=0,
        min=-0.1,
        max=0.1,
        precision=3,
        step=0.001,
        unit='LENGTH',
    )

    scale: bpy.props.FloatProperty(
        name='倍率',
        description='コライダの大きさを全体的に倍率調整します',
        #subtype='FACTOR',
        default=1.0,
        min=0.5,
        max=2.0,
        precision=2,
        step=1,
    )

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return prop.mesh and prop.mesh.type=='MESH' and bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE' and bpy.context.active_object.mode=='EDIT' and bpy.context.active_bone

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        return vt.addCollider(prop.mesh, bpy.context.active_object,
                              numberOfColliders=self.numberOfColliders,
                              numberOfRays=self.numberOfRays,
                              radius=self.radius,
                              insideToOutside=(self.insideToOutside=='IN_TO_OUT'),
                              fitMode=self.fitMode,
                              offset=self.offset,
                              scale=self.scale)
      
################
class VRMTool_OT_prepareToExportVRM(bpy.types.Operator):
    bl_idname = 'object.prepare_to_export_vrm'
    bl_label = 'VRM 出力前の準備'
    bl_description = 'VRM を出力するために、メッシュをマージし、不要な骨を溶解し、ウェイトのクリーンアップを行い、ブレンドシェイプの設定を行います'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return vt.getAddon() and\
            prop.skeleton and prop.skeleton.type=='ARMATURE' and prop.bs_json

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        mergedObjs = vt.prepareToExportVRM(skeleton=prop.skeleton.name,
                                           triangulate=prop.triangulate,
                                           bs_json=prop.bs_json.name,
                                           notExport=prop.notExportBoneGroup)
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
class VRMTool_OT_openAddonPage(bpy.types.Operator):
    bl_idname = 'object.url_open_vrm_addon_for_blender'
    bl_label = 'VRM_Addon_for_Blender のページを開く'
    bl_description = 'VRM_Addon_for_Blender のサイトページを開きます'
    bl_options = {'INTERNAL'}

    def execute(self, context):
        bpy.ops.wm.url_open(url="https://vrm-addon-for-blender.info")
        return {'FINISHED'}

################
class VRMTool_PT_VRMTool(bpy.types.Panel):
    bl_idname = 'VT_PT_VRMTool'
    bl_label = 'VRMTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_vt_prop
        layout = self.layout
        layout.prop_search(prop, 'mesh', context.blend_data, 'objects')
        self.layout.operator('object.add_collider')

        layout.separator()
        # prepareToExportVRM
        split = layout.split(factor=0.15, align=True)
        if prop.display_prepareToExportVRM:
            split.prop(prop, 'display_prepareToExportVRM',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_prepareToExportVRM',
                       text='', icon='RIGHTARROW')
        split.operator(VRMTool_OT_prepareToExportVRM.bl_idname)
        if prop.display_prepareToExportVRM:
            col = layout.column(align=True).box().column(align=True)
            if vt.getAddon():
                col.prop_search(prop, 'skeleton', context.blend_data, 'objects')
                col.prop(prop, 'triangulate')
                col.prop_search(prop, 'bs_json', context.blend_data, 'texts')
                if prop.skeleton:
                    col.prop_search(prop, 'notExportBoneGroup', prop.skeleton.pose,
                                    'bone_groups')
                col.prop(prop, 'mergedName')
                col.prop(prop, 'saveAsExport')
            else:
                col.label(text='VRM_Addon_for_Blender がインストールされていません。',
                          icon='INFO')
                col.operator(VRMTool_OT_openAddonPage.bl_idname)

################
classes = (
    VRMTool_propertyGroup,
    VRMTool_OT_addCollider,
    VRMTool_OT_prepareToExportVRM,
    VRMTool_OT_openAddonPage,
    VRMTool_PT_VRMTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_vt_prop = bpy.props.PointerProperty(type=VRMTool_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_vt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
