# -*- encoding:utf-8 -*-

import bpy
from bpy.props import FloatProperty, PointerProperty, FloatVectorProperty, EnumProperty
from bpy.types import Panel, Operator, PropertyGroup

from . import UVTool as ut

################################################################
def getOrigin(self):
    return bpy.context.space_data.cursor_location

def setOrigin(self, value):
    bpy.context.space_data.cursor_location = value

################
class DDDUT_propertyGroup(PropertyGroup):
    origin: FloatVectorProperty(
        name='2Dカーソル座標',
        description='2Dカーソルの座標です',
        size=2,
        precision=2,
        step=1.0,
        unit='NONE',
        get=getOrigin,
        set=setOrigin,
    )
    
    offset: FloatVectorProperty(
        name='移動量',
        description='UV 座標に加える量です',
        size=2,
        default=[0.25, 0.25],
        precision=2,
        step=1.0,
        unit='NONE',
    )
    
################################################################
def canEditMesh(context):
    return context.active_object and\
        context.active_object.type == 'MESH' and\
        context.active_object.mode == 'EDIT'

################
class DDDUT_OT_alignUV(Operator):
    bl_idname = 'dddut.align_uv'
    bl_label = 'UV 整列'
    bl_description = '様々な条件で UV を整列させます'
    bl_options = {'UNDO'}

    origin: FloatVectorProperty(
        name='基点',
        description='整列の基点となる座標です',
        size=2,
        precision=2,
        step=1.0,
        unit='NONE',
    )
    mode: EnumProperty(
        items=[('ALIGN_LEFT', 'ALIGN_LEFT', 'UVの左端を基点に付けます'),
               ('ALIGN_RIGHT', 'ALIGN_RIGHT', 'UVの右端を基点に付けます'),
               ('ALIGN_TOP', 'ALIGN_TOP', 'UVの上端を基点に付けます'),
               ('ALIGN_BOTTOM', 'ALIGN_BOTTOM', 'UVの下端を基点に付けます'),
               ('ALIGN_CENTER_HORIZONTAL', 'ALIGN_CENTER_HORIZONTAL', 'UVの左右の中心を基点に付けます'),
               ('ALIGN_CENTER_VERTICAL', 'ALIGN_CENTER_VERTICAL', 'UVの上下の中心を基点に付けます')])

    @classmethod
    def poll(self, context):
        return canEditMesh(context)

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland(self.mode, self.origin[0], self.origin[1])

################
class DDDUT_OT_moveUV(Operator):
    bl_idname = 'dddut.move_uv'
    bl_label = 'UV 移動'
    bl_description = 'UV を移動させます'
    bl_options = {'REGISTER', 'UNDO'}

    offset: FloatVectorProperty(
        name='移動量',
        description='UV 座標に加える量です',
        size=2,
        precision=2,
        step=1.0,
        unit='NONE',
    )

    @classmethod
    def poll(self, context):
        return canEditMesh(context)

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('OFFSET', self.offset[0], self.offset[1])

################################################################
class DDDUT_PT_UVTool(Panel):
    bl_idname = 'UT_PT_UVTool'
    bl_label = 'UVTool'
    bl_category = "DDDTools"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_ut_prop
        layout = self.layout.column()

        def drawAlignUV(lo, text='', icon='NONE', mode=None):
            op = lo.operator(DDDUT_OT_alignUV.bl_idname, text=text, icon=icon)
            op.mode = mode
            op.origin = prop.origin

        box = layout.box()
        col = box.column(align=True)
        col.label(text='整列')
        drawAlignUV(col, icon='ANCHOR_BOTTOM', mode='ALIGN_BOTTOM')
        row = col.row(align=True)
        row.scale_y = 2.0
        drawAlignUV(row, icon='ANCHOR_RIGHT', mode='ALIGN_RIGHT')
        col_xy = row.column(align=True)
        col_xy.scale_y = 0.5
        col_xy.prop(prop, 'origin', text='')
        drawAlignUV(row, icon='ANCHOR_LEFT', mode='ALIGN_LEFT')
        drawAlignUV(col, icon='ANCHOR_TOP', mode='ALIGN_TOP')
        
        col.separator()
        drawAlignUV(col, text='←→ 水平揃え', mode='ALIGN_CENTER_HORIZONTAL')
        drawAlignUV(col, text='↑↓ 垂直揃え', mode='ALIGN_CENTER_VERTICAL')

        def drawMoveUV(lo, offsetX, offsetY, icon='NONE'):
            op = lo.operator(DDDUT_OT_moveUV.bl_idname, text='', icon=icon)
            op.offset = [offsetX, offsetY]

        box = layout.box()
        col = box.column(align=True)
        col.label(text='移動')
        drawMoveUV(col, 0, prop.offset[1], icon='TRIA_UP')
        row = col.row(align=True)
        row.scale_y = 2.0
        drawMoveUV(row, -prop.offset[0], 0, icon='TRIA_LEFT')
        col_xy = row.column(align=True)
        col_xy.scale_y = 0.5
        col_xy.prop(prop, 'offset', text='')
        drawMoveUV(row, prop.offset[0], 0, icon='TRIA_RIGHT')
        drawMoveUV(col, 0, -prop.offset[1], icon='TRIA_DOWN')
        
        

################################################################
classes = (
    DDDUT_propertyGroup,
    DDDUT_OT_alignUV,
    DDDUT_OT_moveUV,
    DDDUT_PT_UVTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_ut_prop = PointerProperty(type=DDDUT_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_ut_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
