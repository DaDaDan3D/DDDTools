# -*- encoding:utf-8 -*-

import bpy
import bmesh
from bpy.props import BoolProperty, FloatProperty, IntProperty
from bpy.types import Panel, Operator

import math
from random import Random
from mathutils import Vector, Matrix
import traceback
import numpy as np
from . import internalUtils as iu
from . import mathUtils as mu
from . import SelectTool as st

################################################################
class DDDET_OT_selectDividingLoops(Operator):
    bl_idname = 'dddet.select_dividing_loops'
    bl_label = '分割線の選択'
    bl_description = '選択メッシュの分割線を選択します'
    bl_options = {'REGISTER', 'UNDO'}

    excludeSeam: BoolProperty(
        name='シーム',
        description='シームは選択しません',
        default=True,
    )

    excludeSharp: BoolProperty(
        name='シャープ',
        description='シャープは選択しません',
        default=True,
    )

    excludeBevelWeight: BoolProperty(
        name='ベベルウェイト',
        description='ベベルウェイトを除外するかどうか',
        default=False,
    )
    bevelWeight: FloatProperty(
        name='ベベルウェイト',
        description='ベベルウェイトがこれ以上の辺は選択しません',
        default=1.0,
        min=0.0,
        max=1.0,
        precision=2,
        step=10,
        subtype = 'FACTOR',
    )

    excludeCrease: BoolProperty(
        name='クリース',
        description='クリースを除外するかどうか',
        default=True,
    )
    crease: FloatProperty(
        name='クリース',
        description='クリースがこれ以上の辺は選択しません',
        default=1.0,
        min=0.0,
        max=1.0,
        precision=2,
        step=10,
        subtype = 'FACTOR',
    )

    excludeFaceAngle: BoolProperty(
        name='面の角度',
        description='鋭角な面を除外するかどうか',
        default=False,
    )
    faceAngle: FloatProperty(
        name='面の角度',
        description='面の角度がこれ以上の辺は選択しません',
        default=math.radians(30),
        min=0.0,
        max=math.pi,
        precision=2,
        step=5,
        subtype = 'ANGLE',
    )

    randomSeed: IntProperty(
        name = 'Random Seed',
        description = '選択に使う乱数の種です',
        default=0,
        min=0
    )

    ratio: FloatProperty(
        name='選択率',
        description='分割線を選択する割合です',
        default=1.0,
        min=0.0,
        max=1.0,
        precision=2,
        step=5,
        subtype = 'FACTOR',
    )

    mirrorX: BoolProperty(
        name='X',
        description='ループ決定後、X方向のミラー選択を追加で実行します',
        default=False,
    )
    mirrorY: BoolProperty(
        name='Y',
        description='ループ決定後、Y方向のミラー選択を追加で実行します',
        default=False,
    )
    mirrorZ: BoolProperty(
        name='Z',
        description='ループ決定後、Z方向のミラー選択を追加で実行します',
        default=False,
    )

    dissolve: BoolProperty(
        name='辺の溶解',
        description='選択後、自動的に辺を溶解します',
        default=False,
    )

    lastSelected: 0.0
    lastFound: 0.0

    @classmethod
    def poll(self, context):
        mesh = bpy.context.active_object
        return mesh and mesh.type == 'MESH'

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text='除外')
        column = box.column()
        row = column.row()
        row.prop(self, 'excludeSeam')
        row.prop(self, 'excludeSharp')

        column.separator()

        split = column.split(factor=0, align=True)
        split.prop(self, 'excludeCrease')
        row = split.row()
        row.enabled = self.excludeCrease
        row.prop(self, 'crease', text='')

        split = column.split(factor=0, align=True)
        split.prop(self, 'excludeBevelWeight')
        row = split.row()
        row.enabled = self.excludeBevelWeight
        row.prop(self, 'bevelWeight', text='')

        split = column.split(factor=0, align=True)
        split.prop(self, 'excludeFaceAngle')
        row = split.row()
        row.enabled = self.excludeFaceAngle
        row.prop(self, 'faceAngle', text='', slider=True)

        layout.separator()

        box = layout.box()
        box.label(text='選択')
        column = box.column()
        column.prop(self, 'randomSeed')
        column.prop(self, 'ratio')
        row = column.row()
        row.label(text=f'{self.lastSelected} / {self.lastFound} の分割線を選択しました', icon='INFO')

        layout.separator()

        box = layout.box()
        box.label(text='自動実行')
        column = box.column()
        split = column.split(factor=0, align=True)
        split.label(text='ミラー選択')
        row = split.row()
        row.prop(self, 'mirrorX')
        row.prop(self, 'mirrorY')
        row.prop(self, 'mirrorZ')
        column.prop(self, 'dissolve')

    def execute(self, context):
        rng = Random(self.randomSeed)
        def choose(index, loop, selected, found):
            toBeSelected = int(found * self.ratio + 0.5) - selected
            rest = found - index
            #print(f'index:{index} s/f:{selected}/{found} t/r:{toBeSelected}/{rest}')
            if rest <= 0 or toBeSelected <= 0:
                return False
            elif toBeSelected >= rest:
                return True
            else:
                rr = toBeSelected / rest
                #print(f'rr:{rr}')
                return rng.random() < rr
        
        mesh = bpy.context.active_object
        faceAngle = self.faceAngle if self.excludeFaceAngle else math.tau
        bevelWeight = self.bevelWeight if self.excludeBevelWeight else 1.1
        crease = self.crease if self.excludeCrease else 1.1
        finder = st.DividingLoopFinder(exclude_face_angle=faceAngle,
                                       exclude_seam=self.excludeSeam,
                                       exclude_sharp=self.excludeSharp,
                                       exclude_bevel_weight=bevelWeight,
                                       exclude_crease=crease)
                                       
                                       
        ans = finder.selectDividingLoops(mesh, choose=choose)
        if ans:
            self.lastSelected = ans.selected
            self.lastFound = ans.found
            if self.mirrorX or self.mirrorY or self.mirrorZ:
                axis = set()
                if self.mirrorX: axis.add('X')
                if self.mirrorY: axis.add('Y')
                if self.mirrorZ: axis.add('Z')
                bpy.ops.mesh.select_mirror(axis=axis, extend=True)

            if self.dissolve:
                bpy.ops.mesh.dissolve_edges()
                bpy.ops.mesh.reveal()
                bpy.ops.mesh.hide(unselected=False)

            return {'FINISHED'}
        else:
            return {'CANCELLED'}

################################################################
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
    
class DDDET_OT_addApproximateSphere(Operator):
    bl_idname = 'dddet.add_approximate_sphere'
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

################################################################
class DDDET_OT_addApproximateEmpty(Operator):
    bl_idname = 'dddet.add_approximate_empty'
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

################################################################
class DDDET_OT_convertEmptyAndSphere(Operator):
    bl_idname = 'dddet.convert_empty_and_sphere'
    bl_label = 'エンプティとメッシュの相互変換'
    bl_description = '選択中のオブジェクトがメッシュならエンプティ球に、エンプティ球ならメッシュに変換します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        emptyObjects = []
        sphereObjects = []
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                empty = iu.convertSphereToEmpty(obj)
                if empty:
                    emptyObjects.append(empty)
            elif obj.type == 'EMPTY' and obj.empty_display_type == 'SPHERE':
                sphere = iu.convertEmptyToSphere(obj)
                if sphere:
                    sphereObjects.append(sphere)
        if sphereObjects or emptyObjects:
            self.report({'INFO'},
                        f'{len(sphereObjects)} 個のエンプティと {len(emptyObjects)} 個のメッシュを変換しました: {sphereObjects} {emptyObjects}')
            for obj in sphereObjects + emptyObjects:
                obj.select_set(True)
            return {'FINISHED'}
        else:
            self.report({'INFO'},
                        '変換できるオブジェクトはありませんでした')
            return {'CANCELLED'}

################################################################
class DDDET_PT_main(Panel):
    bl_idname = 'DDDET_PT_main'
    bl_label = 'EditTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        col = self.layout.column()
        col.operator(DDDET_OT_selectDividingLoops.bl_idname)
        col.operator(DDDET_OT_addApproximateSphere.bl_idname)
        col.operator(DDDET_OT_addApproximateEmpty.bl_idname)
        col.operator(DDDET_OT_convertEmptyAndSphere.bl_idname)

################################################################
def menu_fn(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(DDDET_OT_selectDividingLoops.bl_idname)

################################################################
classes = (
    DDDET_OT_selectDividingLoops,
    DDDET_OT_addApproximateSphere,
    DDDET_OT_addApproximateEmpty,
    DDDET_OT_convertEmptyAndSphere,
    DDDET_PT_main,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_select_edit_mesh.append(menu_fn)

def unregisterClass():
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(menu_fn)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
