import bpy
from bpy.props import StringProperty, EnumProperty, CollectionProperty, PointerProperty, BoolProperty, FloatProperty, IntProperty
from bpy.types import PropertyGroup, Operator, Panel, UIList
from . import MaterialTool as mt

################################################################
def used_shader_group_node_items(self, context):
    items = [("(NONE)", "(NONE)", "")]
    node_groups = set()

    for material in bpy.data.materials:
        if material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'GROUP':
                    node_groups.add(node.node_tree.name)

    for group_name in sorted(node_groups):
        items.append((group_name, group_name, ""))
    return items

def shader_group_node_items(self, context):
    items = [("(NONE)", "(NONE)", "")]
    node_groups = set()

    for group in bpy.data.node_groups:
        if group.type == 'SHADER':
            node_groups.add(group.name)
            
    for group_name in sorted(node_groups):
        items.append((group_name, group_name, ""))
    return items

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

    display_calc_specular_settings: BoolProperty(
        name='CalcSpecularSettings',
        default=True)
    ior: FloatProperty(name='IOR',
                       default=1.45,
                       min=0,
                       max=100,
                       precision=2,
                       step=1)

    display_replaceGroupNode: BoolProperty(
        name='replaceGroupNode_settings',
        default=True)
    old_group_node: EnumProperty(
        name='旧ノード',
        description="置き換え元のグループノード",
        items=used_shader_group_node_items
    )
    new_group_node: EnumProperty(
        name='新ノード',
        description="置き換え先のグループノード",
        items=shader_group_node_items
    )

    display_sortMaterialSlots_settings: BoolProperty(
        name='sortMaterialSlots_settings',
        default=True)
    orderList: CollectionProperty(
        type=DDDMT_MaterialListItem,
        name='マテリアル順指定リスト',
        description='マテリアルをソートする時に順番を指定するためのリスト',
    )
    orderList_index: IntProperty()

    materialSelectorForOrderList: PointerProperty(
        type=bpy.types.Material,
        name='マテリアル選択',
        description='マテリアル順指定リストに追加するマテリアルを選択します',
    )

################################################################
class DDDMT_OT_selectAllObjectsUsingTexture(Operator):
    bl_idname = 'dddmt.select_all_objects_using_texture'
    bl_label = 'テクスチャを使用するオブジェクトの選択'
    bl_description = '指定したテクスチャを使用しているオブジェクトを選択します'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.texture and bpy.context.active_object and bpy.context.active_object.mode=='OBJECT'

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        if prop.texture:
            mt.selectAllObjectsUsingTexture(prop.texture.name)
        return{'FINISHED'}

################################################################
class DDDMT_OT_selectAllImageNodesUsingTexture(Operator):
    bl_idname = 'dddmt.select_all_image_nodes_using_texture'
    bl_label = 'テクスチャを使用するイメージシェーダーノードの選択'
    bl_description = '指定したテクスチャを使用しているイメージシェーダーノードを選択します'
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
    bl_label = 'テクスチャを使用するマテリアルの列挙'
    bl_description = '指定したテクスチャを使用しているマテリアルをコンソールに列挙します'
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
                            f'テクスチャ"{prop.texture.name}"を使用しているマテリアルは{sorted(mats)}です')
            else:
                self.report({'INFO'},
                            f'テクスチャ"{prop.texture.name}"を使用しているマテリアルはありません')

        return{'FINISHED'}

################################################################
class DDDMT_OT_setupMaterialContainerObject(Operator):
    bl_idname = 'dddmt.setup_material_container_object'
    bl_label = 'テクスチャを使用する全マテリアルをオブジェクトに設定'
    bl_description = '指定したテクスチャを使用している全マテリアルを、アクティブなメッシュに登録します'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.texture and bpy.context.active_object and bpy.context.active_object.type == 'MESH'

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
    bl_label = 'マテリアルを使用するオブジェクトの選択'
    bl_description = '指定したマテリアルを使用しているオブジェクトを選択します'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.material and bpy.context.active_object and bpy.context.active_object.mode=='OBJECT'

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        if prop.material:
            mt.selectAllObjectsUsingMaterial(prop.material.name)
        return{'FINISHED'}

################################################################
class DDDMT_OT_listupAllObjectsUsingMaterial(Operator):
    bl_idname = 'dddmt.listup_all_objects_using_material'
    bl_label = 'マテリアルを使用するオブジェクトの列挙'
    bl_description = '指定したマテリアルを使用しているオブジェクトをコンソールに列挙します'
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
                            f'マテリアル"{prop.material.name}"を使用しているオブジェクトは{sorted(objs)}です')
            else:
                self.report({'INFO'},
                            f'マテリアル"{prop.material.name}"を使用しているオブジェクトはありません')

        return{'FINISHED'}

################################################################
class DDDMT_OT_calcSpecularFromIOR(Operator):
    bl_idname = 'dddmt.calc_specular_from_ior'
    bl_label = 'スペキュラ計算'
    bl_description = 'IOR からスペキュラを計算してクリップボードにコピーします'
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        specular = mt.calcSpecularFromIOR(prop.ior)
        self.report({'INFO'},
                    f'IOR({prop.ior})のスペキュラ({specular})をクリップボードにコピーしました')
        return {'FINISHED'}
    
################################################################
class DDDMT_OT_replaceGroupNode(Operator):
    bl_idname = 'dddmt.replace_group_node'
    bl_label = 'グループノード置換'
    bl_description = '指定したシェーダーグループノードを新しいシェーダーグループノードに置き換えます'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_mt_prop
        return prop.old_group_node != "(NONE)" and prop.new_group_node != "(NONE)" and prop.old_group_node != prop.new_group_node

    def execute(self, context):
        prop = context.scene.dddtools_mt_prop
        old_group_name = prop.old_group_node
        new_group_name = prop.new_group_node
        modified_materials = mt.replace_group_node(old_group_name, new_group_name)
        if modified_materials:
            self.report({'INFO'}, f'以下のマテリアルを修正しました: {sorted(modified_materials)}')
        else:
            self.report({'INFO'}, f'シェーダーグループ"{old_group_name}"を使用しているマテリアルはありません')

        prop.old_group_node = "(NONE)"
        prop.new_group_node = new_group_name
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        prop = context.scene.dddtools_mt_prop
        row = self.layout
        row.label(text='全マテリアルのグループノードを置き換えます')
        row.label(text='よろしいですか？')
        row.prop(prop, 'old_group_node')
        row.prop(prop, 'new_group_node')

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
    bl_label = 'マテリアル追加'
    bl_description = 'マテリアル順指定リストに、ドロップダウンで選択しているマテリアルを追加します'
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
    bl_label = 'マテリアル削除'
    bl_description = 'マテリアル順指定リストで選択中のマテリアルを削除します'
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
    bl_label = 'Move Material'
    bl_description = 'マテリアル順指定リストで選択中のマテリアルの位置を移動します'
    bl_options = {'UNDO'}

    direction: EnumProperty(items=[('UP', 'Up', '選択中のマテリアルを上に移動'),
                                   ('DOWN', 'Down', '選択中のマテリアルを下に移動'),
                                   ('TOP', 'Top', '選択中のマテリアルを一番上に移動'),
                                   ('BOTTOM', 'Bottom', '選択中のマテリアルを一番下に移動')])

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
    bl_label = 'Execute Sort'
    bl_description = '選択中のオブジェクトのマテリアルスロットを、指定順にソートします。マテリアル順指定リストに含まれるマテリアルをリストの順で→それ以外のマテリアルを名前順で、という順に並べます'
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
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        prop = context.scene.dddtools_mt_prop
        layout = self.layout

        # TextureTools
        split = layout.split(factor=0.15, align=True)
        if prop.display_texture_tools:
            split.prop(prop, 'display_texture_tools',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_texture_tools',
                       text='', icon='RIGHTARROW')
        split.label(text='テクスチャ関係')
        if prop.display_texture_tools:
            col = layout.box().column(align=True)

            col.prop_search(prop, 'texture', context.blend_data, 'images')
            col.operator(DDDMT_OT_selectAllObjectsUsingTexture.bl_idname,
                         text='selectObjects')
            col.operator(DDDMT_OT_listupAllMaterialsUsingTexture.bl_idname,
                         text='listupMaterials')
            col.operator(DDDMT_OT_setupMaterialContainerObject.bl_idname,
                         text='setupMaterialContainerObject')
            col.operator(DDDMT_OT_selectAllImageNodesUsingTexture.bl_idname,
                         text='selectNodes')


        # MaterialTools
        split = layout.split(factor=0.15, align=True)
        if prop.display_material_tools:
            split.prop(prop, 'display_material_tools',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_material_tools',
                       text='', icon='RIGHTARROW')
        split.label(text='マテリアル関係')
        if prop.display_material_tools:
            col = layout.box().column(align=True)
            col.prop_search(prop, 'material', context.blend_data, 'materials')
            col.operator(DDDMT_OT_selectAllObjectsUsingMaterial.bl_idname,
                         text='selectObjects')
            col.operator(DDDMT_OT_listupAllObjectsUsingMaterial.bl_idname,
                         text='listupObjects')

        # calcSpecularFromIOR
        split = layout.split(factor=0.15, align=True)
        if prop.display_calc_specular_settings:
            split.prop(prop, 'display_calc_specular_settings',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_calc_specular_settings',
                       text='', icon='RIGHTARROW')
        split.operator(DDDMT_OT_calcSpecularFromIOR.bl_idname,
                       text='スペキュラ計算')
        if prop.display_calc_specular_settings:
            col = layout.box().column(align=True)
            col.prop(prop, 'ior')

        # replace_group_node
        split = layout.split(factor=0.15, align=True)
        if prop.display_replaceGroupNode:
            split.prop(prop, 'display_replaceGroupNode',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_replaceGroupNode',
                       text='', icon='RIGHTARROW')
        split.operator(DDDMT_OT_replaceGroupNode.bl_idname)
        if prop.display_replaceGroupNode:
            col = layout.box().column(align=True)
            col.prop(prop, "old_group_node")
            col.prop(prop, "new_group_node")
     
        # sortMaterialSlots
        split = layout.split(factor=0.15, align=True)
        if prop.display_sortMaterialSlots_settings:
            split.prop(prop, 'display_sortMaterialSlots_settings',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_sortMaterialSlots_settings',
                       text='', icon='RIGHTARROW')
        split.operator(DDDMT_OT_sortMaterialSlots.bl_idname,
                       icon='SORTALPHA', text='マテリアルのソート')
        if prop.display_sortMaterialSlots_settings:
            col = layout.box().column(align=True)

            col.label(text='マテリアル順指定リスト')

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
    DDDMT_OT_selectAllObjectsUsingTexture,
    DDDMT_OT_selectAllImageNodesUsingTexture,
    DDDMT_OT_listupAllMaterialsUsingTexture,
    DDDMT_OT_setupMaterialContainerObject,
    DDDMT_OT_selectAllObjectsUsingMaterial,
    DDDMT_OT_listupAllObjectsUsingMaterial,
    DDDMT_OT_calcSpecularFromIOR,
    DDDMT_OT_replaceGroupNode,
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
