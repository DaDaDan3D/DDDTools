import bpy
from bpy.props import CollectionProperty, IntProperty, PointerProperty, StringProperty, FloatProperty, EnumProperty
from bpy.types import Panel, UIList, Operator, PropertyGroup
from DDDTools import MaterialTool as mt

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
    bl_label = '取り除く'
    bl_description = 'リストから取り除きます'
    bl_options = {'UNDO'}
    
    index: IntProperty()

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        prop.socket_list.remove(self.index)
        newIndex = max(0, min(self.index, len(prop.socket_list) - 1))
        prop.socket_list_index = newIndex
            
        return {'FINISHED'}

################
class DDDST_OT_showSocketInEditor(Operator):
    bl_idname = 'dddst.show_socket_in_editor'
    bl_label = 'エディタで見る'
    bl_description = 'シェーダーエディタでマテリアルを開き、ノードを選択します'
    bl_options = {'UNDO'}
    
    index: IntProperty()

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        prop.socket_list_index = self.index
        item = prop.socket_list[self.index]
        showMaterialInShaderEditor(context, item)
        return {'FINISHED'}

################
class DDDST_UL_socketList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        row.operator(DDDST_OT_showSocketInEditor.bl_idname,
                     text='', icon='VIEWZOOM').index = index
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
    nodeName: EnumProperty(
        name='ノード名',
        description='一覧を作成するノード名です',
        items=getNodeNames,
    )
    socketName: EnumProperty(
        name='インプット',
        description='一覧を作成するノードインプットの名前です',
        items=getSocketNames,
    )
    socket_list: CollectionProperty(type=DDDST_socketItem)
    socket_list_index: IntProperty()

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
    bl_label = 'リスト作成'
    bl_description = '指定されたノード名とインプット名に一致するノードインプットの一覧を作成します'
    bl_options = {'UNDO'}

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        socket_list = prop.socket_list
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

        socket_list.clear()        
        for item in sorted(items):
            new_item = socket_list.add()
            new_item.material = item[1]
            new_item.nodeName = item[2]
            new_item.socketName = item[3]

        return {'FINISHED'}

################
class DDDST_OT_clearSocketList(Operator):
    bl_idname = 'dddst.clear_socket_list'
    bl_label = 'リストクリア'
    bl_description = 'ノードインプットの一覧をクリアします'
    bl_options = {'UNDO'}

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        socket_list = prop.socket_list
        socket_list.clear()
        return {'FINISHED'}


################
class DDDST_OT_copyValueForAllSocketsInList(Operator):
    bl_idname = 'dddst.copy_value_for_all_sockets_in_list'
    bl_label = '値をコピー'
    bl_description = 'カーソル位置のノードインプットの値を、リストの全てのノードインプットにコピーします'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        prop = context.scene.dddtools_st_prop
        socket_list = prop.socket_list
        index = prop.socket_list_index
        return len(socket_list) > 1 and index < len(socket_list)

    def execute(self, context):
        prop = context.scene.dddtools_st_prop
        socket_list = prop.socket_list
        index = prop.socket_list_index
        if index < len(socket_list):
            socketFrom = socket_list[index].getSocket()
            if socketFrom:
                for item in socket_list:
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
        col = self.layout.column(align=True)
        prop = context.scene.dddtools_st_prop

        col.prop(prop, 'nodeName', translate=False)
        col.prop(prop, 'socketName', translate=False)
        row = col.row()
        row.operator(DDDST_OT_populateNodesForSocketList.bl_idname)
        row.operator(DDDST_OT_clearSocketList.bl_idname, text='', icon='X')

        col.template_list('DDDST_UL_socketList', '',
                          prop, 'socket_list',
                          prop, 'socket_list_index')

        col.operator(DDDST_OT_copyValueForAllSocketsInList.bl_idname)


################################################################
classes = (
    DDDST_socketItem,
    DDDST_OT_removeFromSocketList,
    DDDST_OT_showSocketInEditor,
    DDDST_UL_socketList,
    DDDST_propertyGroup,
    DDDST_OT_populateNodesForSocketList,
    DDDST_OT_clearSocketList,
    DDDST_OT_copyValueForAllSocketsInList,
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
