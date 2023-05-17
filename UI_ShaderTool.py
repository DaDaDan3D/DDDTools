# -*- encoding:utf-8 -*-

import bpy
from bpy.props import CollectionProperty, IntProperty, PointerProperty, StringProperty, FloatProperty, EnumProperty, BoolProperty
from bpy.types import Panel, UIList, Operator, PropertyGroup
from DDDTools import MaterialTool as mt

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################################################################
def used_shader_group_node_items(self, context):
    items = [('(NONE)', '(NONE)', '')]
    node_groups = set()

    for material in bpy.data.materials:
        if material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'GROUP':
                    node_groups.add(node.node_tree.name)

    for group_name in sorted(node_groups):
        items.append((group_name, group_name, ''))
    return items

def shader_group_node_items(self, context):
    items = [('(NONE)', '(NONE)', '')]
    node_groups = set()

    for group in bpy.data.node_groups:
        if group.type == 'SHADER':
            node_groups.add(group.name)
            
    for group_name in sorted(node_groups):
        items.append((group_name, group_name, ''))
    return items

################################################################
class DDDST_socketItem(PropertyGroup):
    material: PointerProperty(type=bpy.types.Material)
    nodeName: StringProperty()
    socketName: StringProperty()

    def getSocket(self):
        try:
            material = self.material
            node = material.node_tree.nodes[self.nodeName]
            socket = node.inputs[self.socketName]
            return socket
        except:
            return None

    def draw(self, context, layout):
        try:
            material = self.material
            node = material.node_tree.nodes[self.nodeName]
            socket = node.inputs[self.socketName]
            socket.draw(context, layout, node, text='')
        except:
            layout.label(text='N/A')

################
class DDDST_OT_removeFromSocketList(Operator):
    bl_idname = 'dddst.remove_from_socket_list'
    bl_label = _('取り除く')
    bl_description = _('リストから取り除きます')
    bl_options = {'UNDO'}
    
    index: IntProperty()

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        prop.socketList.remove(self.index)
        newIndex = max(0, min(self.index, len(prop.socketList) - 1))
        prop.socketListIndex = newIndex
            
        return {'FINISHED'}

################
class DDDST_OT_showSocketInEditor(Operator):
    bl_idname = 'dddst.show_socket_in_editor'
    bl_label = _('エディタで見る')
    bl_description = _('シェーダーエディタでマテリアルを開き、ノードを選択します')
    bl_options = {'UNDO'}
    
    index: IntProperty()

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        prop.socketListIndex = self.index
        item = prop.socketList[self.index]
        showMaterialInShaderEditor(context, item)
        return {'FINISHED'}

################
class DDDST_UL_socketList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.operator(DDDST_OT_showSocketInEditor.bl_idname,
                     text='', icon='HIDE_OFF').index = index
        row.label(text=item.material.name, translate=False)
        item.draw(context, row)
        row.operator(DDDST_OT_removeFromSocketList.bl_idname,
                     text='', icon='X').index = index

################
def getNodeBaseFromSocket(socket):
    node = socket.node
    if node:
        if node.type == 'GROUP':
            return node.node_tree.name
        else:
            return node.bl_idname
    else:
        return None

################
def getNodeNames(self, context):
    prop = context.scene.dddtools_st_prop

    names = set()
    matNameToSockets = collectNodeSocketsFromObjects(context.selected_objects)
    for matName, sockets in matNameToSockets.items():
        for socket in sockets:
            name = getNodeBaseFromSocket(socket)
            if name:
                names.add(name)

    items = []
    for name in sorted(names):
        items.append((name, name, ''))
    items = sorted(items)
    return items

################
def getSocketNames(self, context):
    prop = context.scene.dddtools_st_prop
    targetNode = prop.nodeName

    names = set()

    matNameToSockets = collectNodeSocketsFromObjects(context.selected_objects)
    for matName, sockets in matNameToSockets.items():
        for socket in sockets:
            if getNodeBaseFromSocket(socket) == targetNode:
                names.add(socket.name)

    items = []
    for name in sorted(names):
        items.append((name, name, ''))
    return items

################
class DDDST_propertyGroup(PropertyGroup):
    display_calcSpecular_settings: BoolProperty(
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
        name=_('旧ノード'),
        description=_('置き換え元のグループノード'),
        items=used_shader_group_node_items
    )
    new_group_node: EnumProperty(
        name=_('新ノード'),
        description=_('置き換え先のグループノード'),
        items=shader_group_node_items
    )

    display_socketList: BoolProperty(
        name=_('ソケットリストの表示'),
        default=True)
    nodeName: EnumProperty(
        name=_('ノード名'),
        description=_('一覧を作成するノード名です'),
        items=getNodeNames,
    )
    socketName: EnumProperty(
        name=_('インプット'),
        description=_('一覧を作成するノードインプットの名前です'),
        items=getSocketNames,
    )
    socketList: CollectionProperty(type=DDDST_socketItem)
    socketListIndex: IntProperty()

################################################################
class DDDST_OT_calcSpecularFromIOR(Operator):
    bl_idname = 'dddst.calc_specular_from_ior'
    bl_label = _('スペキュラ計算')
    bl_description = _('IOR からスペキュラを計算してクリップボードにコピーします')
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        specular = mt.calcSpecularFromIOR(prop.ior)
        self.report({'INFO'},
                    iface_('IOR({prop_ior})のスペキュラ({specular})をクリップボードにコピーしました').format(
                        prop_ior=prop.ior,
                        specular=specular))
        return {'FINISHED'}
    
################################################################
class DDDST_OT_replaceGroupNode(Operator):
    bl_idname = 'dddst.replace_group_node'
    bl_label = _('グループノード置換')
    bl_description = _('指定したシェーダーグループノードを新しいシェーダーグループノードに置き換えます')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_st_prop
        return prop.old_group_node != '(NONE)' and prop.new_group_node != '(NONE)' and prop.old_group_node != prop.new_group_node

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        old_group_name = prop.old_group_node
        new_group_name = prop.new_group_node
        modified_materials = mt.replace_group_node(old_group_name, new_group_name)
        if modified_materials:
            self.report({'INFO'},
                        iface_('以下のマテリアルを修正しました: {sorted_modified_materials}').format(
                            sorted_modified_materials=str(sorted(modified_materials))))
        else:
            self.report({'INFO'},
                        iface_('シェーダーグループ({old_group_name})を使用しているマテリアルはありません').format(
                            old_group_name=old_group_name))

        prop.old_group_node = '(NONE)'
        prop.new_group_node = new_group_name
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        prop = context.scene.dddtools_st_prop
        row = self.layout
        row.label(text=iface_('全マテリアルのグループノードを置き換えます'))
        row.label(text=iface_('よろしいですか？'))
        row.prop(prop, 'old_group_node')
        row.prop(prop, 'new_group_node')

################
def isSocketEditable(socket):
    return not socket.is_linked and\
        not socket.is_multi_input and\
        socket.enabled and\
        not socket.is_unavailable and\
        isinstance(socket, bpy.types.NodeSocketStandard) and\
        socket.type in ['CUSTOM',
                       'VALUE',
                       'INT',
                       'BOOLEAN',
                       'VECTOR',
                       'STRING',
                       'RGBA']

################
def collectNodeSocketsFromObjects(objs):
    result = dict()
    for obj in objs:
        for slot in obj.material_slots:
            if slot.material.name not in result:
                sockets = mt.collectNodeSocketsFromMaterial(slot.material, isSocketEditable)
                if sockets:
                    result[slot.material.name] = sockets
    return result

################
class DDDST_OT_populateNodesForSocketList(Operator):
    bl_idname = 'dddst.populate_nodes_for_socket_list'
    bl_label = _('リスト作成')
    bl_description = _('指定されたノード名とインプット名に一致するノードインプットの一覧を作成します')
    bl_options = {'UNDO'}

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        socketList = prop.socketList
        targetNode = prop.nodeName
        targetSocket = prop.socketName

        matNameToSockets = collectNodeSocketsFromObjects(context.selected_objects)
        items = []
        for matName, sockets in matNameToSockets.items():
            material = bpy.data.materials[matName]
            for socket in sockets:
                if socket and socket.name == targetSocket:
                    nodeName = getNodeBaseFromSocket(socket)
                    if nodeName == targetNode:
                        items.append((material.name,
                                      material,
                                      socket.node.name,
                                      socket.name))

        socketList.clear()        
        for item in sorted(items):
            new_item = socketList.add()
            new_item.material = item[1]
            new_item.nodeName = item[2]
            new_item.socketName = item[3]

        return {'FINISHED'}

################
class DDDST_OT_clearSocketList(Operator):
    bl_idname = 'dddst.clear_socket_list'
    bl_label = _('リストクリア')
    bl_description = _('ノードインプットの一覧をクリアします')
    bl_options = {'UNDO'}

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        socketList = prop.socketList
        socketList.clear()
        return {'FINISHED'}


################
class DDDST_OT_copyValueForAllSocketsInList(Operator):
    bl_idname = 'dddst.copy_value_for_all_sockets_in_list'
    bl_label = _('値をコピー')
    bl_description = _('カーソル位置のノードインプットの値を、リストの全てのノードインプットにコピーします')
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        prop = context.scene.dddtools_st_prop
        socketList = prop.socketList
        index = prop.socketListIndex
        return len(socketList) > 1 and index < len(socketList)

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        socketList = prop.socketList
        index = prop.socketListIndex
        if index < len(socketList):
            socketFrom = socketList[index].getSocket()
            if socketFrom:
                for item in socketList:
                    socketTo = item.getSocket()
                    if socketTo and socketTo != socketFrom:
                        socketTo.default_value = socketFrom.default_value
        return {'FINISHED'}

################
def showMaterialInShaderEditor(context, item):
    material = item.material
    socket = item.getSocket()
    if not socket:
        return
    for obj in bpy.context.selectable_objects:
        idx = obj.material_slots.find(material.name)
        if idx >= 0:
            context.view_layer.objects.active = obj
            context.object.active_material_index = idx
            for node in material.node_tree.nodes:
                if node == socket.node:
                    node.select = True
                    material.node_tree.nodes.active = node
                else:
                    node.select = False
            break

################
class DDDST_PT_mainPanel(Panel):
    bl_label = 'DDDTools'
    bl_idname = 'DDDST_PT_main_panel'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'DDDTools'

    def draw(self, context):
        prop = context.scene.dddtools_st_prop
        layout = self.layout.column()

        # calcSpecularFromIOR
        split = layout.split(factor=0.15, align=True)
        if prop.display_calcSpecular_settings:
            split.prop(prop, 'display_calcSpecular_settings',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_calcSpecular_settings',
                       text='', icon='RIGHTARROW')
        split.operator(DDDST_OT_calcSpecularFromIOR.bl_idname,
                       text=iface_('スペキュラ計算'))
        if prop.display_calcSpecular_settings:
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
        split.operator(DDDST_OT_replaceGroupNode.bl_idname)
        if prop.display_replaceGroupNode:
            col = layout.box().column(align=True)
            col.prop(prop, 'old_group_node')
            col.prop(prop, 'new_group_node')
     
        # socketList
        split = layout.split(factor=0.15, align=True)
        if prop.display_socketList:
            split.prop(prop, 'display_socketList',
                       text='', icon='DOWNARROW_HLT')
        else:
            split.prop(prop, 'display_socketList',
                       text='', icon='RIGHTARROW')
        split.label(text=iface_('ノードインプット一覧'))
        if prop.display_socketList:
            col = layout.box().column(align=True)
            col.prop(prop, 'nodeName', translate=False)
            col.prop(prop, 'socketName', translate=False)
            row = col.row(align=True)
            row.operator(DDDST_OT_populateNodesForSocketList.bl_idname)
            row.operator(DDDST_OT_clearSocketList.bl_idname, text='', icon='X')

            col.template_list('DDDST_UL_socketList', '',
                              prop, 'socketList',
                              prop, 'socketListIndex')

            col.operator(DDDST_OT_copyValueForAllSocketsInList.bl_idname)


################################################################
classes = (
    DDDST_socketItem,
    DDDST_OT_calcSpecularFromIOR,
    DDDST_OT_removeFromSocketList,
    DDDST_OT_showSocketInEditor,
    DDDST_UL_socketList,
    DDDST_propertyGroup,
    DDDST_OT_populateNodesForSocketList,
    DDDST_OT_clearSocketList,
    DDDST_OT_copyValueForAllSocketsInList,
    DDDST_OT_replaceGroupNode,
    DDDST_PT_mainPanel,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_st_prop = PointerProperty(type=DDDST_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_st_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
