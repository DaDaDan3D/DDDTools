import bpy
from . import ColliderTool as ct

################################################################
class ColliderTool_propertyGroup(bpy.types.PropertyGroup):
    mesh: bpy.props.PointerProperty(
        name='Mesh',
        description='幅を計算するメッシュ',
        type=bpy.types.Object,
        poll=lambda self, obj: obj and obj.type=='MESH',
    )        

################################################################
class ColliderTool_OT_addCollider(bpy.types.Operator):
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
        prop = context.scene.dddtools_ct_prop
        return prop.mesh and prop.mesh.type=='MESH' and bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE' and bpy.context.active_object.mode=='EDIT' and bpy.context.active_bone

    def execute(self, context):
        prop = context.scene.dddtools_ct_prop
        return ct.addCollider(prop.mesh, bpy.context.active_object,
                              numberOfColliders=self.numberOfColliders,
                              numberOfRays=self.numberOfRays,
                              radius=self.radius,
                              insideToOutside=(self.insideToOutside=='IN_TO_OUT'),
                              fitMode=self.fitMode,
                              offset=self.offset,
                              scale=self.scale)
      
class ColliderTool_PT_ColliderTool(bpy.types.Panel):
    bl_idname = 'CT_PT_ColliderTool'
    bl_label = 'ColliderTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_ct_prop
        layout = self.layout
        layout.prop_search(prop, 'mesh', context.blend_data, 'objects')
        self.layout.operator('object.add_collider')

classes = (
    ColliderTool_propertyGroup,
    ColliderTool_OT_addCollider,
    ColliderTool_PT_ColliderTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_ct_prop = bpy.props.PointerProperty(type=ColliderTool_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_ct_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
