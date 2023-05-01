import bpy
from bpy.props import FloatProperty, PointerProperty
from bpy.types import Panel, Operator, PropertyGroup

from . import UVTool as ut

################################################################
def getOriginX(self):
    return bpy.context.space_data.cursor_location[0]

def setOriginX(self, value):
    bpy.context.space_data.cursor_location[0] = value

def getOriginY(self):
    return bpy.context.space_data.cursor_location[1]

def setOriginY(self, value):
    bpy.context.space_data.cursor_location[1] = value

################
class DDDUT_propertyGroup(PropertyGroup):
    originX: FloatProperty(
        name='2DカーソルX',
        description='2DカーソルのX座標',
        default=0.5,
        min=0.00,
        max=1.00,
        precision=2,
        step=1.0,
        unit='NONE',
        get=getOriginX,
        set=setOriginX,
    )
    originY: FloatProperty(
        name='2DカーソルY',
        description='2DカーソルのY座標',
        default=0.5,
        min=0.00,
        max=1.00,
        precision=2,
        step=1.0,
        unit='NONE',
        get=getOriginY,
        set=setOriginY,
    )
    
################################################################
def canEditMesh(context):
    return context.active_object and\
        context.active_object.type == 'MESH' and\
        context.active_object.mode == 'EDIT'

################
class DDDUT_OT_alignUVLeft(Operator):
    bl_idname = 'dddut.align_uv_left'
    bl_label = '→'
    bl_description = 'UVの左端が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return canEditMesh(context)

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_LEFT', prop.originX, 0)

class DDDUT_OT_alignUVRight(Operator):
    bl_idname = 'dddut.align_uv_right'
    bl_label = '←'
    bl_description = 'UVの右端が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return canEditMesh(context)

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_RIGHT', prop.originX, 0)

class DDDUT_OT_alignUVTop(Operator):
    bl_idname = 'dddut.align_uv_top'
    bl_label = '↓'
    bl_description = 'UVの上端が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return canEditMesh(context)

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_TOP', 0, prop.originY)

class DDDUT_OT_alignUVBottom(Operator):
    bl_idname = 'dddut.align_uv_bottom'
    bl_label = '↑'
    bl_description = 'UVの下端が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return canEditMesh(context)

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_BOTTOM', 0, prop.originY)

class DDDUT_OT_alignUVCenterHorizontal(Operator):
    bl_idname = 'dddut.align_uv_center_horizontal'
    bl_label = '←→中央揃え'
    bl_description = 'UVの左右の中心が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return canEditMesh(context)

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_CENTER_HORIZONTAL', prop.originX, 0)

class DDDUT_OT_alignUVCenterVertical(Operator):
    bl_idname = 'dddut.align_uv_center_vertical'
    bl_label = '↑↓中央揃え'
    bl_description = 'UVの上下の中心が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return canEditMesh(context)

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_CENTER_VERTICAL', 0, prop.originY)

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

        box = layout.box()
        col = box.column(align=True)
        col.operator(DDDUT_OT_alignUVBottom.bl_idname,
                     text='', icon='ANCHOR_BOTTOM')
        row = col.row(align=True)
        row.scale_y = 2.0
        row.operator(DDDUT_OT_alignUVRight.bl_idname,
                     text='', icon='ANCHOR_RIGHT')
        col_xy = row.column(align=True)
        col_xy.scale_y = 0.5
        col_xy.prop(prop, 'originX', text='X')
        col_xy.prop(prop, 'originY', text='Y')
        row.operator(DDDUT_OT_alignUVLeft.bl_idname,
                     text='', icon='ANCHOR_LEFT')
        col.operator(DDDUT_OT_alignUVTop.bl_idname,
                     text='', icon='ANCHOR_TOP')


        col.separator()
        col.operator(DDDUT_OT_alignUVCenterHorizontal.bl_idname)
        col.operator(DDDUT_OT_alignUVCenterVertical.bl_idname)


################################################################
classes = (
    DDDUT_propertyGroup,
    DDDUT_OT_alignUVLeft,
    DDDUT_OT_alignUVRight,
    DDDUT_OT_alignUVTop,
    DDDUT_OT_alignUVBottom,
    DDDUT_OT_alignUVCenterHorizontal,
    DDDUT_OT_alignUVCenterVertical,
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
