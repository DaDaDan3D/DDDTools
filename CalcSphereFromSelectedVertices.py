import bpy
import bmesh
from bpy.props import IntProperty
from bpy.types import Panel, Operator

from mathutils import Vector, Matrix
import traceback
import numpy as np
from . import internalUtils as iu
from . import mathUtils as mu

################
def calcCenterOfSphereFromSelectedVertices():
    """
    Returns the radius and center of the sphere that approximates the selected vertices.
    
    """

    mesh = bpy.context.active_object
    if not mesh or mesh.type != 'MESH':
        return None

    bme = bmesh.from_edit_mesh(bpy.context.active_object.data)
    mtx = bpy.context.active_object.matrix_world
    verts = [mtx @ vtx.co for vtx in bme.verts if vtx.select]
    #print(verts)
    
    try:
        if len(verts) < 4:
            raise ValueError(f'4つ以上の頂点を選択してください。現在{len(verts)}個の頂点が選択されています。')
        elif len(verts) == 4:
            result = mu.calcCircumcenter(np.array(verts))
        else:
            result = mu.calcFit(np.array(verts))
    except Exception as e:
        print(f'エラーが発生しました: {e} {type(e)}')
        traceback.print_exc()
        result = None

    return result
    
################
class DDD_OT_addApproximateSphere(Operator):
    bl_idname = 'ddd.add_approximate_sphere'
    bl_label = '近似球の追加'
    bl_description = '選択した頂点群に近似した球を追加します'
    bl_options = {'REGISTER', 'UNDO'}

    segments: IntProperty(
        name='セグメント',
        description='追加する球のセグメントの数を指定します',
        min=3,
        max=500,
        default=32,
    )

    ring_count: IntProperty(
        name='リング',
        description='追加する球のリングの数を指定します',
        min=3,
        max=500,
        default=16,
    )

    @classmethod
    def poll(self, context):
        mesh = bpy.context.active_object
        return mesh and mesh.type=='MESH' and mesh.mode=='EDIT'

    def execute(self, context):
        if self.sphere:
            mesh = iu.ObjectWrapper(bpy.context.active_object)
            modeChanger = iu.ModeChanger(mesh.obj, 'OBJECT')
            bpy.ops.mesh.primitive_uv_sphere_add(enter_editmode=False,
                                                 align='WORLD',
                                                 segments=self.segments,
                                                 ring_count=self.ring_count,
                                                 radius=self.sphere[0],
                                                 location=self.sphere[1],
                                                 scale=(1, 1, 1))
            del modeChanger
            bpy.context.view_layer.objects.active = mesh.obj
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        '球を追加できませんでした。詳細はログを参照してください')
            return {'CANCELLED'}

    def invoke(self, context, event):
        self.sphere = calcCenterOfSphereFromSelectedVertices()
        return self.execute(context)

################
class DDD_OT_addApproximateEmpty(Operator):
    bl_idname = 'ddd.add_approximate_empty'
    bl_label = 'エンプティ球の追加'
    bl_description = '選択した頂点群に近似したEMPTY球を追加します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        mesh = bpy.context.active_object
        return mesh and mesh.type=='MESH' and mesh.mode=='EDIT'

    def execute(self, context):
        sphere = calcCenterOfSphereFromSelectedVertices()
        if sphere:
            mesh = iu.ObjectWrapper(bpy.context.active_object)
            empty_obj = bpy.data.objects.new(f'EmptySphere_{mesh.name}', None)
            empty_obj.empty_display_type = 'SPHERE'
            empty_obj.empty_display_size = sphere[0]
            empty_obj.location = sphere[1]
            context.scene.collection.objects.link(empty_obj)
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        'エンプティ球を追加できませんでした。詳細はログを参照してください')
            return {'CANCELLED'}

################
class DDD_PT_tool(Panel):
    bl_idname = 'DDD_PT_tool'
    bl_label = 'Aproximate'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator(DDD_OT_addApproximateSphere.bl_idname)
        col.operator(DDD_OT_addApproximateEmpty.bl_idname)

################

classes = (
    DDD_OT_addApproximateSphere,
    DDD_OT_addApproximateEmpty,
    DDD_PT_tool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregisterClass():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
