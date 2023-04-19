import bpy
from . import UVTool as ut

################################################################
class UVTool_propertyGroup(bpy.types.PropertyGroup):
    originX: bpy.props.FloatProperty(
        name='原点X座標',
        description='原点のX座標',
        default=0.5,
        min=0.00,
        max=1.00,
        precision=2,
        step=0.05,
        unit='NONE',
    )
    originY: bpy.props.FloatProperty(
        name='原点Y座標',
        description='原点のY座標',
        default=0.5,
        min=0.00,
        max=1.00,
        precision=2,
        step=0.05,
        unit='NONE',
    )
    
################################################################
class UVTool_OT_alignUVLeft(bpy.types.Operator):
    bl_idname = 'object.align_uv_left'
    bl_label = '左を付ける'
    bl_description = 'UVの左端が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_LEFT', prop.originX, 0)

class UVTool_OT_alignUVRight(bpy.types.Operator):
    bl_idname = 'object.align_uv_right'
    bl_label = '右を付ける'
    bl_description = 'UVの右端が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_RIGHT', prop.originX, 0)

class UVTool_OT_alignUVTop(bpy.types.Operator):
    bl_idname = 'object.align_uv_top'
    bl_label = '上を付ける'
    bl_description = 'UVの上端が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_TOP', 0, prop.originY)

class UVTool_OT_alignUVBottom(bpy.types.Operator):
    bl_idname = 'object.align_uv_bottom'
    bl_label = '下を付ける'
    bl_description = 'UVの下端が原点になるように移動します'
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        return ut.offsetSelectedUVIsland('ALIGN_BOTTOM', 0, prop.originY)

################################################################
class UVTool_OT_setCursorToOrigin(bpy.types.Operator):
    bl_idname = 'object.set_cursor_to_origin'
    bl_label = '2Dカーソルを移動'
    bl_description = '2Dカーソルの位置を指定の位置に移動します'
    bl_options = {'UNDO'}

    def execute(self, context):
        prop = context.scene.dddtools_ut_prop
        bpy.context.space_data.cursor_location[0] = prop.originX
        bpy.context.space_data.cursor_location[1] = prop.originY
        return {'FINISHED'}
        
################################################################
class UVTool_PT_UVTool(bpy.types.Panel):
    bl_idname = 'UT_PT_UVTool'
    bl_label = 'UVTool'
    bl_category = "DDDTools"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_ut_prop
        layout = self.layout

        box = layout.column(align=True).box().column()
        col = box.column(align=True)
        col.operator(UVTool_OT_alignUVBottom.bl_idname)
        row = col.row(align=True)
        row.operator(UVTool_OT_alignUVRight.bl_idname)
        row.prop(prop, 'originX')
        row.prop(prop, 'originY')
        row.operator(UVTool_OT_alignUVLeft.bl_idname)
        col.operator(UVTool_OT_alignUVTop.bl_idname)

        col.separator()
        col.operator(UVTool_OT_setCursorToOrigin.bl_idname)
        
################################################################
classes = (
    UVTool_propertyGroup,
    UVTool_OT_alignUVLeft,
    UVTool_OT_alignUVRight,
    UVTool_OT_alignUVTop,
    UVTool_OT_alignUVBottom,
    UVTool_OT_setCursorToOrigin,
    UVTool_PT_UVTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_ut_prop = bpy.props.PointerProperty(type=UVTool_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_ut_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
