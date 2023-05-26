# -*- encoding:utf-8 -*-

import bpy
from bpy.props import StringProperty, EnumProperty, CollectionProperty, PointerProperty, BoolProperty, FloatProperty, IntProperty
from bpy.types import PropertyGroup, Operator, Panel, UIList
from . import internalUtils as iu
from . import UIUtils as ui
from . import MaterialTool as mt

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################################################################
class DDDMT_MaterialListItem(PropertyGroup):
    material: PointerProperty(type=bpy.types.Material)

################
class DDDMT_propertyGroup(PropertyGroup):
    display_texture_tools: BoolProperty(
        name='TextureTools',
        default=True)
    texture: PointerProperty(name='Texture', type=bpy.types.Image)

    display_material_tools: BoolProperty(
        name='MaterialTools',
        default=True)
    material: PointerProperty(name='Material', type=bpy.types.Material)

    display_sortMaterialSlots_settings: BoolProperty(
        name='sortMaterialSlots_settings',
        default=True)
    orderList: CollectionProperty(
        type=DDDMT_MaterialListItem,
        name=_('Material Order Specification List'),
        description=_('A list to specify the order when sorting materials.'),
    )
    orderList_index: IntProperty()

    materialSelectorForOrderList: PointerProperty(
        type=bpy.types.Material,
        name=_('Material Selector'),
        description=_('Select the material to be added to the material order list.'),
    )

################################################################
class DDDMT_OT_reloadTexture(Operator):
    bl_idname = 'dddmt.reload_texture'
    bl_label = _('Reload Texture')
    bl_description = _('Reloads the specified texture.')

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.texture

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        if prop.texture:
            prop.texture.reload()
        return{'FINISHED'}

################################################################
class DDDMT_OT_selectAllObjectsUsingTexture(Operator):
    bl_idname = 'dddmt.select_all_objects_using_texture'
    bl_label = _('Select Objects')
    bl_description = _('Selects objects that use the specified texture.')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.texture and bpy.context.mode == 'OBJECT'

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        if prop.texture:
            mt.selectAllObjectsUsingTexture(prop.texture.name)
        return{'FINISHED'}

################################################################
class DDDMT_OT_selectAllImageNodesUsingTexture(Operator):
    bl_idname = 'dddmt.select_all_image_nodes_using_texture'
    bl_label = _('Select Shader Nodes')
    bl_description = _('Makes the image shader node that uses the specified texture selected.')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.texture

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        if prop.texture:
            mt.selectAllImageNodesUsingTexture(prop.texture.name)
        return{'FINISHED'}

################################################################
class DDDMT_OT_listupAllMaterialsUsingTexture(Operator):
    bl_idname = 'dddmt.listup_all_materials_using_texture'
    bl_label = _('Enumerate Materials')
    bl_description = _('Enumerates the materials using the specified texture in the console.')
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.texture

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        if prop.texture:
            mats = mt.listupAllMaterialsUsingTexture(prop.texture.name)
            if mats:
                self.report({'INFO'},
                            iface_('Material using texture ({prop_texture_name}) is {sorted_mats}.').format(
                                prop_texture_name=prop.texture.name,
                                sorted_mats=str(sorted(mats))))
                bpy.context.window_manager.clipboard = iu.format_list_as_string(
                    mats, indent_level=0)
            else:
                self.report({'INFO'},
                            iface_('No material using texture ({prop_texture_name}).').format(
                                prop_texture_name=prop.texture.name))

        return{'FINISHED'}

################################################################
class DDDMT_OT_setupMaterialContainerObject(Operator):
    bl_idname = 'dddmt.setup_material_container_object'
    bl_label = _('Setup All Materials')
    bl_description = _('Sets all materials using the specified texture to the active mesh object.')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.texture and bpy.context.active_object and bpy.context.active_object.type == 'MESH' and bpy.context.mode == 'OBJECT'

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        if prop.texture:
            mt.setupMaterialContainerObject(prop.texture.name)
            return{'FINISHED'}
        else:
            return{'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

################################################################
class DDDMT_OT_selectAllObjectsUsingMaterial(Operator):
    bl_idname = 'dddmt.select_all_objects_using_material'
    bl_label = _('Select Objects')
    bl_description = _('Selects objects using the specified material.')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.material and bpy.context.mode == 'OBJECT'

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        if prop.material:
            mt.selectAllObjectsUsingMaterial(prop.material.name)
        return{'FINISHED'}

################################################################
class DDDMT_OT_listupAllObjectsUsingMaterial(Operator):
    bl_idname = 'dddmt.listup_all_objects_using_material'
    bl_label = _('Enumerate Objects')
    bl_description = _('Enumerates objects using the specified material in the console.')
    bl_options = {'REGISTER'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.material

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        if prop.material:
            objs = mt.listupAllObjectsUsingMaterial(prop.material.name)
            if objs:
                self.report({'INFO'},
                            iface_('Objects using material ({prop_material_name}) are {sorted_objs}.').format(
                                prop_material_name=prop.material.name,
                                sorted_objs=str(sorted(objs))))
                bpy.context.window_manager.clipboard = iu.format_list_as_string(
                    objs, indent_level=0)

            else:
                self.report({'INFO'},
                            iface_('No objects using material ({prop_material_name}).').format(
                                prop_material_name=prop.material.name))
        return{'FINISHED'}

################################################################
class DDDMT_UL_materialList(UIList):
    bl_idname = 'DDDMT_UL_materialList'

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        material = item.material
        if material:
            layout.label(text=material.name, translate=False)

################
class DDDMT_OT_addMaterialToOrderList(Operator):
    bl_idname = 'dddmt.add_material_to_order_list'
    bl_label = _('Add Material')
    bl_description = _('Add the material selected in the drop-down to the material order list.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        prop = context.scene.dddtools_mt_prop
        material = prop.materialSelectorForOrderList
        return material and material.name not in [x.material.name for x in prop.orderList]

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        material = prop.materialSelectorForOrderList
        if material:
            orderList = prop.orderList
            new_item = orderList.add()
            new_item.material = material
        return {'FINISHED'}

################
class DDDMT_OT_removeMaterialFromOrderList(Operator):
    bl_idname = 'dddmt.remove_material_from_order_list'
    bl_label = _('Remove Material')
    bl_description = _('Removes the currently selected material in the material order list.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        prop = context.scene.dddtools_mt_prop
        orderList = prop.orderList
        index = prop.orderList_index
        return index < len(orderList)

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        orderList = prop.orderList
        index = prop.orderList_index
        if index < len(orderList):
            orderList.remove(index)
        return {'FINISHED'}

################
class DDDMT_OT_moveMaterialInOrderList(Operator):
    bl_idname = 'dddmt.move_material_in_order_list'
    bl_label = _('Move Material')
    bl_description = _('Moves the position of the currently selected material in the material order list.')
    bl_options = {'UNDO'}

    direction: EnumProperty(items=[('UP', 'Up', _('Move selected material up.')),
                                   ('DOWN', 'Down', _('Move selected material down.')),
                                   ('TOP', 'Top', _('Move selected material to the top.')),
                                   ('BOTTOM', 'Bottom', _('Move selected material to the bottom.'))])

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        orderList = prop.orderList
        index = prop.orderList_index
        if self.direction == 'UP':
            orderList.move(index, index-1)
            prop.orderList_index = max(0, index-1)
        elif self.direction == 'DOWN':
            orderList.move(index, index+1)
            prop.orderList_index = min(len(orderList)-1, index+1)
        elif self.direction == 'TOP':
            orderList.move(index, 0)
            prop.orderList_index = 0
        elif self.direction == 'BOTTOM':
            orderList.move(index, len(orderList)-1)
            prop.orderList_index = len(orderList)-1
        return {'FINISHED'}

################
class DDDMT_OT_sortMaterialSlots(Operator):
    bl_idname = 'dddmt.sort_material_slots'
    bl_label = _('Sort Materials')
    bl_description = _('Sorts the material slots of the selected object in the order specified. Materials in the material order list are sorted in the order of the list, other materials are sorted by name, and so on.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        prop = context.scene.dddtools_mt_prop
        return bpy.context.selected_objects and prop.orderList

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        obj = bpy.context.active_object
        material_order = [item.material.name for item in prop.orderList]
        mt.sort_material_slots(obj, material_order)
        return {'FINISHED'}

################################################################
class DDDMT_PT_MaterialTool(Panel):
    bl_idname = 'MT_PT_MaterialTool'
    bl_label = 'MaterialTool'
    bl_category = 'DDDTools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        prop = context.scene.dddtools_mt_prop
        layout = self.layout.column(align=True)

        # TextureTools
        display, split = ui.splitSwitch(layout, prop, 'display_texture_tools')
        split.label(text=iface_('Texture related'))
        if display:
            col = layout.box().column(align=True)

            split = col.split(factor=0.8, align=True)
            split.prop_search(prop, 'texture', context.blend_data, 'images')
            split.operator(DDDMT_OT_reloadTexture.bl_idname,
                           text='', icon='FILE_REFRESH')
            col.operator(DDDMT_OT_selectAllObjectsUsingTexture.bl_idname)
            col.operator(DDDMT_OT_listupAllMaterialsUsingTexture.bl_idname)
            col.operator(DDDMT_OT_setupMaterialContainerObject.bl_idname)
            col.operator(DDDMT_OT_selectAllImageNodesUsingTexture.bl_idname)


        # MaterialTools
        display, split = ui.splitSwitch(layout, prop, 'display_material_tools')
        split.label(text=iface_('Material related'))
        if display:
            col = layout.box().column(align=True)
            col.prop_search(prop, 'material', context.blend_data, 'materials')
            col.operator(DDDMT_OT_selectAllObjectsUsingMaterial.bl_idname)
            col.operator(DDDMT_OT_listupAllObjectsUsingMaterial.bl_idname)

        # sortMaterialSlots
        display, split = ui.splitSwitch(layout, prop, 'display_sortMaterialSlots_settings')
        split.operator(DDDMT_OT_sortMaterialSlots.bl_idname, icon='SORTALPHA')
        if display:
            col = layout.box().column(align=True)

            col.label(text=iface_('Material Order Specification List'))

            # Draw material list
            row = col.row()
            row.template_list(DDDMT_UL_materialList.bl_idname, '',
                              prop, 'orderList',
                              prop, 'orderList_index',
                              sort_lock=True)

            # Draw move buttons
            move_col = row.column(align=True)
            move_col.operator(DDDMT_OT_moveMaterialInOrderList.bl_idname,
                              icon='TRIA_UP_BAR', text='').direction = 'TOP'
            move_col.operator(DDDMT_OT_moveMaterialInOrderList.bl_idname,
                              icon='TRIA_UP', text='').direction = 'UP'
            move_col.operator(DDDMT_OT_moveMaterialInOrderList.bl_idname,
                              icon='TRIA_DOWN', text='').direction = 'DOWN'
            move_col.operator(DDDMT_OT_moveMaterialInOrderList.bl_idname,
                              icon='TRIA_DOWN_BAR', text='').direction = 'BOTTOM'

            # Draw remove button
            move_col.separator()
            move_col.operator(DDDMT_OT_removeMaterialFromOrderList.bl_idname,
                              icon='REMOVE', text='')

            # Draw material dropdown and add button
            split = col.split(factor=0.8)
            split.prop_search(prop, 'materialSelectorForOrderList',
                              context.blend_data, 'materials',
                              text='')
            split.operator(DDDMT_OT_addMaterialToOrderList.bl_idname,
                           icon='ADD', text='')

################################################################
classes = (
    DDDMT_MaterialListItem,
    DDDMT_propertyGroup,
    DDDMT_OT_reloadTexture,
    DDDMT_OT_selectAllObjectsUsingTexture,
    DDDMT_OT_selectAllImageNodesUsingTexture,
    DDDMT_OT_listupAllMaterialsUsingTexture,
    DDDMT_OT_setupMaterialContainerObject,
    DDDMT_OT_selectAllObjectsUsingMaterial,
    DDDMT_OT_listupAllObjectsUsingMaterial,
    DDDMT_PT_MaterialTool,
    DDDMT_UL_materialList,
    DDDMT_OT_addMaterialToOrderList,
    DDDMT_OT_removeMaterialFromOrderList,
    DDDMT_OT_moveMaterialInOrderList,
    DDDMT_OT_sortMaterialSlots,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_mt_prop = PointerProperty(type=DDDMT_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_mt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
