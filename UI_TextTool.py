# -*- encoding:utf-8 -*-
import bpy
from bpy.props import StringProperty
from bpy.types import PropertyGroup, Operator, Panel
from . import TextTool as tt

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

class DDDTT_OT_checkJson(Operator):
    bl_idname = 'dddmt.check_json'
    bl_label = _('Check JSON text')
    bl_description = _('Checks if the currently active text is correct as JSON.')

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):
        text = bpy.context.space_data.text
        error_msg = tt.check_json(text)
        if error_msg:
            self.report({'WARNING'}, error_msg)
        else:
            self.report({'INFO'}, iface_('No problem with {text_name}.').format(
                text_name=text.name))

        return{'FINISHED'}
    
class DDDTT_PT_MainPanel(Panel):
    bl_idname = 'TT_PT_MainPanel'
    bl_label = 'TextTool'
    bl_category = 'DDDTools'
    bl_space_type = 'TEXT_EDITOR'
    bl_region_type = 'UI'

    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator(DDDTT_OT_checkJson.bl_idname)

################################################################
classes = (
    DDDTT_OT_checkJson,
    DDDTT_PT_MainPanel,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregisterClass():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
        
