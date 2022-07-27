import bpy
from . import internalUtils as iu
from . import NormalTool as nt

################################################################
class NormalTool_OT_addCustomNormals(bpy.types.Operator):
    bl_idname = 'mesh.add_custom_normals'
    bl_label = 'カスタム法線の有効化'
    bl_description = 'カスタム法線を有効化します'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj and obj.type == 'MESH' and not obj.data.has_custom_normals

    def execute(self, context):
        mesh = iu.ObjectWrapper(bpy.context.active_object)
        nt.setCustomNormals(mesh, True)
        return {'FINISHED'}

################################################################
class NormalTool_OT_clearCustomNormals(bpy.types.Operator):
    bl_idname = 'mesh.clear_custom_normals'
    bl_label = 'カスタム法線のクリア'
    bl_description = 'カスタム法線を削除します'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj and obj.type == 'MESH' and obj.data.has_custom_normals

    def execute(self, context):
        mesh = iu.ObjectWrapper(bpy.context.active_object)
        nt.setCustomNormals(mesh, False)
        return {'FINISHED'}

################################################################
class NormalTool_PT_NormalTool(bpy.types.Panel):
    bl_idname = 'NT_PT_NormalTool'
    bl_label = 'NormalTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        layout = self.layout

        layout.operator(NormalTool_OT_addCustomNormals.bl_idname)
        layout.operator(NormalTool_OT_clearCustomNormals.bl_idname)

################################################################
classes = (
    NormalTool_OT_addCustomNormals,
    NormalTool_OT_clearCustomNormals,
    NormalTool_PT_NormalTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregisterClass():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
