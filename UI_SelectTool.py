import bpy
import math
from random import Random
from . import SelectTool as st

################################################################
class SelectTool_OT_selectDividingLoops(bpy.types.Operator):
    bl_idname = 'select.select_dividing_loops'
    bl_label = '分割線の選択'
    bl_description = '選択メッシュの分割線を選択します'
    bl_options = {'REGISTER', 'UNDO'}

    excludeSeam: bpy.props.BoolProperty(
        name='シーム',
        description='シームは選択しません',
        default=True,
    )

    excludeSharp: bpy.props.BoolProperty(
        name='シャープ',
        description='シャープは選択しません',
        default=True,
    )

    excludeBevelWeight: bpy.props.BoolProperty(
        name='ベベルウェイト',
        description='ベベルウェイトを除外するかどうか',
        default=False,
    )
    bevelWeight: bpy.props.FloatProperty(
        name='ベベルウェイト',
        description='ベベルウェイトがこれ以上の辺は選択しません',
        default=1.0,
        min=0.0,
        max=1.0,
        precision=2,
        step=10,
        subtype = 'FACTOR',
    )

    excludeCrease: bpy.props.BoolProperty(
        name='クリース',
        description='クリースを除外するかどうか',
        default=True,
    )
    crease: bpy.props.FloatProperty(
        name='クリース',
        description='クリースがこれ以上の辺は選択しません',
        default=1.0,
        min=0.0,
        max=1.0,
        precision=2,
        step=10,
        subtype = 'FACTOR',
    )

    excludeFaceAngle: bpy.props.BoolProperty(
        name='面の角度',
        description='鋭角な面を除外するかどうか',
        default=False,
    )
    faceAngle: bpy.props.FloatProperty(
        name='面の角度',
        description='面の角度がこれ以上の辺は選択しません',
        default=math.radians(30),
        min=0.0,
        max=math.pi,
        precision=2,
        step=5,
        subtype = 'ANGLE',
    )

    randomSeed: bpy.props.IntProperty(
        name = 'Random Seed',
        description = '選択に使う乱数の種です',
        default=0,
        min=0
    )

    ratio: bpy.props.FloatProperty(
        name='選択率',
        description='分割線を選択する割合です',
        default=1.0,
        min=0.0,
        max=1.0,
        precision=2,
        step=5,
        subtype = 'FACTOR',
    )

    mirrorX: bpy.props.BoolProperty(
        name='X',
        description='ループ決定後、X方向のミラー選択を追加で実行します',
        default=False,
    )
    mirrorY: bpy.props.BoolProperty(
        name='Y',
        description='ループ決定後、Y方向のミラー選択を追加で実行します',
        default=False,
    )
    mirrorZ: bpy.props.BoolProperty(
        name='Z',
        description='ループ決定後、Z方向のミラー選択を追加で実行します',
        default=False,
    )

    dissolve: bpy.props.BoolProperty(
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
class SelectTool_PT_SelectTool(bpy.types.Panel):
    bl_idname = 'ST_PT_WeightTool'
    bl_label = 'SelectTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        layout = self.layout
        layout.operator(SelectTool_OT_selectDividingLoops.bl_idname)
    
################################################################
def menu_fn(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(SelectTool_OT_selectDividingLoops.bl_idname)

################################################################
classes = (
    SelectTool_OT_selectDividingLoops,
    SelectTool_PT_SelectTool,
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
