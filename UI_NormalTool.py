# -*- encoding:utf-8 -*-

import bpy
from bpy.types import Panel, Operator

from . import internalUtils as iu
from . import NormalTool as nt

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################################################################
class DDDNT_OT_addCustomNormals(Operator):
    bl_idname = 'dddnt.add_custom_normals'
    bl_label = _('カスタム法線の有効化')
    bl_description = _('カスタム法線を有効化します')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj and obj.type == 'MESH' and not obj.data.has_custom_normals

    def execute(self, context):
        return bpy.ops.mesh.customdata_custom_splitnormals_add()

################################################################
class DDDNT_OT_clearCustomNormals(Operator):
    bl_idname = 'dddnt.clear_custom_normals'
    bl_label = _('カスタム法線のクリア')
    bl_description = _('カスタム法線を削除します')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj and obj.type == 'MESH' and obj.data.has_custom_normals

    def execute(self, context):
        return bpy.ops.mesh.customdata_custom_splitnormals_clear()

################################################################
class DDDNT_PT_NormalTool(Panel):
    bl_idname = 'NT_PT_NormalTool'
    bl_label = 'NormalTool'
    bl_category = 'DDDTools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        layout = self.layout

        obj = bpy.context.active_object
        if obj and obj.type == 'MESH' and obj.data.has_custom_normals:
            layout.operator(DDDNT_OT_clearCustomNormals.bl_idname,
                            text=iface_('カスタム法線'),
                            icon='CHECKMARK', depress=True)
        else:
            layout.operator(DDDNT_OT_addCustomNormals.bl_idname,
                            text=iface_('カスタム法線'),
                            icon='CHECKBOX_DEHLT', depress=False)

################################################################
classes = (
    DDDNT_OT_addCustomNormals,
    DDDNT_OT_clearCustomNormals,
    DDDNT_PT_NormalTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregisterClass():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
