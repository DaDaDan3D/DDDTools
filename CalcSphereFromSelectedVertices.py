import bpy
import bmesh
from mathutils import Vector, Matrix
import numpy as np
from . import internalUtils as iu
from . import fitting

################
def calcCenterOfSphereFromFourVertices(verts):
    #print(verts)
    if len(verts) != 4:
        return None

    mtx = 2 * Matrix([verts[0] - verts[1],
                      verts[1] - verts[2],
                      verts[2] - verts[3]])
    #print(mtx)
    try:
        mtx_I = mtx.inverted()
    except ValueError as e:
        #print(e)
        return None
    
    # Calc dot products of each vertex
    dv = [vtx.dot(vtx) for vtx in verts]
    #print(dv)
    
    center = mtx_I @ Vector([dv[0] - dv[1],
                             dv[1] - dv[2],
                             dv[2] - dv[3]])
    return ((verts[0] - center).length, center)
    
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
    
    if len(verts) < 4:
        print(f'4つ以上の頂点を選択してください。現在{len(verts)}個の頂点が選択されています。')
        return None
    elif len(verts) == 4:
        #print('calcCenterOfSphereFromFourVertices()')
        return calcCenterOfSphereFromFourVertices(verts)
    else:
        #print('fitting.sphere_fit()')
        return fitting.sphere_fit(np.array(verts))
    
################
class CSFSV_OT_addApproximateSphere(bpy.types.Operator):
    bl_idname = 'object.add_approximate_sphere'
    bl_label = '近似球の追加'
    bl_description = '選択した頂点群に近似した球を追加します'
    bl_options = {'REGISTER', 'UNDO'}

    segments: bpy.props.IntProperty(
        name='セグメント',
        description='追加する球のセグメントの数を指定します',
        min=3,
        max=500,
        default=32,
    )

    ring_count: bpy.props.IntProperty(
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
class CSFSV_PT_tool(bpy.types.Panel):
    bl_idname = 'CSFSV_PT_tool'
    bl_label = 'Aproximate'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        layout = self.layout
        layout.operator('object.add_approximate_sphere')

################

classes = (
    CSFSV_OT_addApproximateSphere,
    CSFSV_PT_tool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregisterClass():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
