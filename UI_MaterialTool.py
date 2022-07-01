import bpy
from . import MaterialTool as mt

################################################################
class MaterialTool_propertyGroup(bpy.types.PropertyGroup):
    texture: bpy.props.PointerProperty(name='Texture', type=bpy.types.Image)
    material: bpy.props.PointerProperty(name='Material', type=bpy.types.Material)

################################################################
class MaterialTool_OT_selectAllObjectsUsingTexture(bpy.types.Operator):
    bl_idname = 'object.select_all_objects_using_texture'
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
class MaterialTool_OT_selectAllImageNodesUsingTexture(bpy.types.Operator):
    bl_idname = 'object.select_all_image_nodes_using_texture'
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
class MaterialTool_OT_listupAllMaterialsUsingTexture(bpy.types.Operator):
    bl_idname = 'object.listup_all_materials_using_texture'
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
class MaterialTool_OT_setupMaterialContainerObject(bpy.types.Operator):
    bl_idname = 'object.setup_material_container_object'
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
class MaterialTool_OT_selectAllObjectsUsingMaterial(bpy.types.Operator):
    bl_idname = 'object.select_all_objects_using_material'
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
class MaterialTool_OT_listupAllObjectsUsingMaterial(bpy.types.Operator):
    bl_idname = 'object.listup_all_objects_using_material'
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
class MaterialTool_PT_MaterialTool(bpy.types.Panel):
    bl_idname = 'MT_PT_MaterialTool'
    bl_label = 'MaterialTool'
    bl_category = "DDDTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        prop = context.scene.dddtools_mt_prop
        layout = self.layout
        layout.prop_search(prop, 'texture', context.blend_data, 'images')
        layout.operator(MaterialTool_OT_selectAllObjectsUsingTexture.bl_idname,
                        text='selectObjects')
        layout.operator(MaterialTool_OT_listupAllMaterialsUsingTexture.bl_idname,
                        text='listupMaterials')
        layout.operator(MaterialTool_OT_setupMaterialContainerObject.bl_idname,
                        text='setupMaterialContainerObject')
        layout.operator(MaterialTool_OT_selectAllImageNodesUsingTexture.bl_idname,
                        text='selectNodes')
        layout.separator()
        layout.prop_search(prop, 'material', context.blend_data, 'materials')
        layout.operator(MaterialTool_OT_selectAllObjectsUsingMaterial.bl_idname,
                        text='selectObjects')
        layout.operator(MaterialTool_OT_listupAllObjectsUsingMaterial.bl_idname,
                        text='listupObjects')
        

################################################################
classes = (
    MaterialTool_propertyGroup,
    MaterialTool_OT_selectAllObjectsUsingTexture,
    MaterialTool_OT_selectAllImageNodesUsingTexture,
    MaterialTool_OT_listupAllMaterialsUsingTexture,
    MaterialTool_OT_setupMaterialContainerObject,
    MaterialTool_OT_selectAllObjectsUsingMaterial,
    MaterialTool_OT_listupAllObjectsUsingMaterial,
    MaterialTool_PT_MaterialTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_mt_prop = bpy.props.PointerProperty(type=MaterialTool_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_mt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
