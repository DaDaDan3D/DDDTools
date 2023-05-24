# -*- encoding:utf-8 -*-

import bpy
from bpy.types import Panel, Operator, PropertyGroup, UIList, Object, Text
from bpy.props import PointerProperty, CollectionProperty, StringProperty, EnumProperty, BoolProperty, IntProperty, FloatProperty
import os
import traceback
from . import internalUtils as iu
from . import UIUtils as ui
from . import VRMTool as vt

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################################################################
class DDDVT_MaterialListItem(PropertyGroup):
    material: PointerProperty(type=bpy.types.Material)

################
class DDDVT_propertyGroup(PropertyGroup):
    display_registerSpringBone_settings: BoolProperty(
        name='RegisterSpringBoneSettings',
        default=True)

    display_colliderTools: BoolProperty(
        name='ColliderTools',
        default=True)

    display_setEmptyAsCollider_settings: BoolProperty(
        name='SetEmptyAsColliderSettings',
        default=True)
    rename: BoolProperty(
        name=_('Rename'),
        description=_('Rename it to an appropriate name as a collider.'),
        default=True)
    symmetrize: BoolProperty(
        name=_('Create Mirror'),
        description=_('Create additional mirror for the collider.'),
        default=True)

    display_addCollider_settings: BoolProperty(
        name='AddColliderSettings',
        default=True)
    mesh: PointerProperty(
        name=_('Target Mesh'),
        description=_('Specifies the mesh for which the radius of the collider is calculated.'),
        type=Object,
        poll=lambda self, obj: obj and obj.type=='MESH',
    )

    display_prepareToExportVRM: BoolProperty(
        name='prepareToExportVRM_settings',
        default=True)

    skeleton: PointerProperty(
        name='Skeleton',
        description=_('Armature of VRM'),
        type=Object,
        poll=lambda self, obj: obj and obj.type=='ARMATURE',
    )

    triangulate: BoolProperty(
        name=_('Triangulate'),
        description=_('Triangulates polygons.'),
        default=False,
    )

    bs_json: PointerProperty(
        name='blendshape',
        description=_('Blendshape.json'),
        type=Text,
    )

    sb_json: PointerProperty(
        name='springBone',
        description=_('Springbone.json'),
        type=Text,
    )

    notExportBoneGroup: StringProperty(
        name=_('Not Export Bone Groups'),
        description=_('The specified bone group is not output and is dissolved.'),
    )

    mergedName: StringProperty(
        name=_('Name for merged mesh'),
        description=_('Specifies the name to give the merged mesh for the remaining meshes not included in the blendshape.'),
        default='MergedBody',
    )

    saveAsExport: BoolProperty(
        name=_('Post-execution save'),
        description=_('After execution, the file is automatically saved as *.export.blend.'),
        default=True)

    sortMaterialSlot: BoolProperty(
        name=_('Sort Materials'),
        description=_('Sorts materials in the order specified in the list. The material order list is located in the MaterialTool panel.'),
        default=False)
    removeUnusedMaterialSlots: BoolProperty(
        name=_('Remove unused materials'),
        description=_('Remove unused materials from the slot.'),
        default=False)

    display_removePolygons_settings: BoolProperty(
        name='RemovePolygonsSettings',
        default=False)
    removePolygons: BoolProperty(
        name=_('Remove Polygons'),
        description=_('Remove polygons according to the condition.'),
        default=False)
    interval: IntProperty(
        name=_('Judgment coarseness'),
        description=_('Specifies what fraction of the size of the texture to work with when determining transparent polygons. Larger sizes are faster, but result in coarser judgments.'),
        min=1,
        max=16,
        default=4,
    )
    alphaThreshold: FloatProperty(
        name=_('Alpha Threshold'),
        description=_('Specifies what fraction of the size of the texture to work with when determining transparent polygons. Larger sizes are faster, but result in coarser judgments.'),
        #subtype='FACTOR',
        default=0.05,
        min=0.00,
        max=1.00,
        precision=2,
        step=1,
    )
    excludeMaterials: CollectionProperty(
        name=_('Exclusion Materials List'),
        description=_('A list of materials that are transparent but not removed when transparent polygons are removed.'),
        type=DDDVT_MaterialListItem)
    excludeMaterialsIndex: IntProperty(
        name=_('Exclusion Material List Index')
    )
    excludeMaterialSelector: PointerProperty(
        name=_('Material Selector'),
        description=_('Select the material to be added to the list of exclusion material list.'),
        type=bpy.types.Material)


################################################################
class DDDVT_OT_addCollider(Operator):
    bl_idname = 'dddvt.add_collider'
    bl_label = _('Add Colliders')
    bl_description = _('Adds colliders to match the size of the mesh.')
    bl_options = {'REGISTER', 'UNDO'}

    t_from: FloatProperty(
        name=_('Start Position'),
        description=_('Specify the starting position as distance (m) from the bone head.'),
        subtype='DISTANCE',
        default=0,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    auto_t_to: BoolProperty(
        name=_('Automatic calculation of end position'),
        description=_('The end position is automatically calculated according to the bone.'),
        default=True)
    t_to: FloatProperty(
        name=_('End position'),
        description=_('Specify the end position as distance (m) from the head of the bone.'),
        subtype='DISTANCE',
        default=0.5,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    t_step: FloatProperty(
        name=_('Interval'),
        description=_('Specify the interval (m) between colliders.'),
        subtype='DISTANCE',
        default=0.03,
        min=0.01,
        max=0.5,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    numberOfRays: IntProperty(
        name=_('Number of Rays'),
        description=_('Sets the number of rays to project.'),
        min=3,
        max=100,
        default=32,
    )
    radius: FloatProperty(
        name=_('Maximum radius of ray'),
        description=_('Sets the maximum radius of the circle from which the ray is projected.'),
        subtype='DISTANCE',
        default=0.3,
        min=0.000,
        max=1.000,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    insideToOutside: EnumProperty(
        name=_('Ray Direction'),
        description=_('Sets the direction of ray projection.'),
        items=[('IN_TO_OUT', _('Spread'), _('Project the ray from the inside to the outside.')),
               ('OUT_TO_IN', _('Gather'), _('Project the ray from the outside to the inside.'))],
        default='IN_TO_OUT',
    )

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return prop.mesh and prop.mesh.type=='MESH' and\
            bpy.context.active_object and\
            bpy.context.active_object.type == 'ARMATURE' and\
            bpy.context.active_object.mode=='POSE' and\
            bpy.context.active_bone

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        if self.auto_t_to:
            t_to = None
        else:
            t_to = self.t_to
        return vt.addCollider(self.mesh, bpy.context.active_object,
                              t_from=self.t_from,
                              t_to=t_to,
                              t_step=self.t_step,
                              numberOfRays=self.numberOfRays,
                              radius=self.radius,
                              insideToOutside=(self.insideToOutside=='IN_TO_OUT'))

    def invoke(self, context, event):
        prop = context.scene.dddtools_vt_prop
        self.mesh = prop.mesh
        return self.execute(context)
      
    def draw(self, context):
        col = self.layout.column()

        col.prop(self, 't_from')
        col.prop(self, 'auto_t_to')
        col2 = col.column()
        col2.enabled = not self.auto_t_to
        col2.prop(self, 't_to')
        col.prop(self, 't_step')
        col.separator()
        col.prop(self, 'numberOfRays')
        col.prop(self, 'radius')
        col.prop(self, 'insideToOutside')

################
class DDDVT_OT_setEmptyAsCollider(Operator):
    bl_idname = 'dddvt.set_empty_as_collider'
    bl_label = _('Empty to Collider')
    bl_description = _('Sets the currently selected empties as children of the currently selected bones of the active skeleton.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        arma = context.active_object
        bone = context.active_bone
        objs = context.selected_objects
        return arma and arma.type=='ARMATURE' and bone and len(objs) > 1

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        arma = iu.ObjectWrapper(context.active_object)
        boneName = context.active_bone.name
        for obj in context.selected_objects:
            if obj.type == 'EMPTY':
                try:
                    vt.setEmptyAsCollider(iu.ObjectWrapper(obj), arma, boneName,
                                          rename=prop.rename,
                                          symmetrize=prop.symmetrize)
                except:
                    traceback.print_exc()
                    self.report({'ERROR'},
                                iface_('An error has occurred. See console for details.'))
                    return {'CANCELLED'}
                    
        return {'FINISHED'}

################
class DDDVT_OT_duplicateColliderAsMirror(Operator):
    bl_idname = 'dddvt.duplicate_collider_as_mirror'
    bl_label = _('Create a mirror of the collider')
    bl_description = _('Creates a mirror of the currently selected collider.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        objs = context.selected_objects
        return objs

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'EMPTY':
                try:
                    vt.duplicateColliderAsMirror(iu.ObjectWrapper(obj))
                except:
                    traceback.print_exc()
                    self.report({'ERROR'},
                                iface_('An error has occurred. See console for details.'))
                    return {'CANCELLED'}
                    
        return {'FINISHED'}

################
class DDDVT_OT_registerSpringBone(Operator):
    bl_idname = 'dddvt.register_spring_bone'
    bl_label = _('Register Spring Bone')
    bl_description = _("Registers the collider and swing object settings to the skeleton based on the information in the specified springbone.json. Since this function is automatically called in 'Preparation before VRM export', it is usually not necessary to use this function.")
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return prop.skeleton and prop.skeleton.type=='ARMATURE' and\
            vt.getAddon() and prop.sb_json

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        try:
            vt.migrateSpringBone(iu.ObjectWrapper(prop.skeleton), prop.sb_json.name)
            self.report({'INFO'},
                        iface_('{sb_json} information has been registered.').format(
                            sb_json=prop.sb_json.name))

        except:
            traceback.print_exc()
            self.report({'ERROR'},
                        iface_('An error has occurred. See console for details.'))
            return {'CANCELLED'}

        return {'FINISHED'}

################
class DDDVT_OT_prepareToExportVRM(Operator):
    bl_idname = 'dddvt.prepare_to_export_vrm'
    bl_label = _('Preparation before VRM export')
    bl_description = _('To export the VRM, merge the meshes, dissolve unwanted bones, clean up the weights, and set the blendshapes.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return vt.getAddon() and\
            prop.skeleton and prop.skeleton.type=='ARMATURE' and\
            prop.bs_json and\
            bpy.context.mode == 'OBJECT'

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        excludeMaterials = set([mat.material.name for mat in prop.excludeMaterials])
        print(excludeMaterials)

        mt_prop = context.scene.dddtools_mt_prop
        if prop.sortMaterialSlot and mt_prop.orderList:
            materialOrderList = [item.material.name for item in mt_prop.orderList]

        else:
            materialOrderList = None

        if prop.sb_json:
            sb_json = prop.sb_json.name
        else:
            sb_json = None
        mergedObjs = vt.prepareToExportVRM(skeleton=prop.skeleton.name,
                                           triangulate=prop.triangulate,
                                           removeTransparentPolygons=prop.removePolygons,
                                           interval=prop.interval,
                                           alphaThreshold=prop.alphaThreshold,
                                           excludeMaterials=excludeMaterials,
                                           bs_json=prop.bs_json.name,
                                           sb_json=sb_json,
                                           notExport=prop.notExportBoneGroup,
                                           materialOrderList=materialOrderList,
                                           removeUnusedMaterialSlots=prop.removeUnusedMaterialSlots)
        
        if mergedObjs:
            if None in mergedObjs:
                mergedObjs[None].rename(prop.mergedName)

            base, ext = os.path.splitext(bpy.data.filepath)
            filepath = f'{base}.export{ext}'
            return bpy.ops.wm.save_as_mainfile(filepath=filepath)
        else:
            return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

################
class DDDVT_OT_openAddonPage(Operator):
    bl_idname = 'dddvt.url_open_vrm_addon_for_blender'
    bl_label = _('Open VRM_Addon_for_Blender page')
    bl_description = _('Open the VRM_Addon_for_Blender site page.')
    bl_options = {'INTERNAL'}

    def execute(self, context):
        bpy.ops.wm.url_open(url='https://vrm-addon-for-blender.info')
        return {'FINISHED'}

################
class DDDVT_UL_MaterialList(UIList):
    bl_idname = 'DDDVT_UL_MaterialList'

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        material = item.material
        if material:
            split = layout.split(factor=0.9)
            split.label(text=material.name, translate=False)
            split.operator(DDDVT_OT_RemoveExcludeMaterial.bl_idname,
                           text='', icon='X').index = index

################
class DDDVT_OT_AddExcludeMaterial(Operator):
    bl_idname = 'dddvt.add_exclude_material'
    bl_label = 'Add'
    bl_description = _('Add a material to the exclusion material list.')
    
    @classmethod
    def poll(cls, context):
        prop = context.scene.dddtools_vt_prop
        selected_material = prop.excludeMaterialSelector
        return selected_material and\
            selected_material.name not in [mat.material.name for mat in prop.excludeMaterials]
    
    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        selected_material = prop.excludeMaterialSelector
        new_item = prop.excludeMaterials.add()
        new_item.material = bpy.data.materials[selected_material.name]
        
        return {'FINISHED'}

class DDDVT_OT_RemoveExcludeMaterial(Operator):
    bl_idname = 'dddvt.remove_exclude_material'
    bl_label = 'Remove Exclude Material'
    bl_description = _('Removes a material from the exclusion material list.')
    
    index: IntProperty()

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        prop.excludeMaterials.remove(self.index)
        return {'FINISHED'}

################
class DDDVT_OT_RemoveTransparentPolygons(Operator):
    bl_idname = 'dddvt.remove_transparent_polygons'
    bl_label = _('Execute Remove')
    bl_description = _('Removes transparent polygons from specified objects that use VRM materials.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_vt_prop
        return vt.getAddon() and bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_vt_prop
        excludeMaterials = set([mat.material.name for mat in prop.excludeMaterials])
        print(excludeMaterials)
        for obj in bpy.context.selected_objects:
            vt.removeTransparentPolygons(obj,
                                         interval=prop.interval,
                                         alphaThreshold=prop.alphaThreshold,
                                         excludeMaterials=excludeMaterials)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

################
class DDDVT_PT_VRMTool(Panel):
    bl_idname = 'VT_PT_VRMTool'
    bl_label = 'VRMTool'
    bl_category = 'DDDTools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_vt_prop
        layout = self.layout

        layout.prop_search(prop, 'skeleton', context.blend_data, 'objects')

        # コライダーツール
        display, split = ui.splitSwitch(layout, prop, 'display_colliderTools')
        split.label(text=iface_('Collider related'))
        if display:
            col = layout.box().column(align=True)

            # setEmptyAsCollider
            display, split = ui.splitSwitch(col, prop, 'display_setEmptyAsCollider_settings')
            split.operator(DDDVT_OT_setEmptyAsCollider.bl_idname)
            if display:
                box = col.box().column(align=True)
                box.prop(prop, 'rename')
                box.prop(prop, 'symmetrize')

            # addCollider
            display, split = ui.splitSwitch(col, prop, 'display_addCollider_settings')
            split.operator(DDDVT_OT_addCollider.bl_idname)
            if display:
                box = col.box().column()
                box.prop_search(prop, 'mesh', context.blend_data, 'objects')

            col.operator(DDDVT_OT_duplicateColliderAsMirror.bl_idname)

        # prepareToExportVRM
        display, split = ui.splitSwitch(layout, prop, 'display_prepareToExportVRM')
        split.operator(DDDVT_OT_prepareToExportVRM.bl_idname)
        if display:
            col = layout.box().column(align=True)
            if vt.getAddon():
                col.prop_search(prop, 'bs_json', context.blend_data, 'texts')
                if prop.skeleton:
                    col.prop_search(prop, 'notExportBoneGroup', prop.skeleton.pose,
                                    'bone_groups')
                col.prop(prop, 'mergedName')
                col.prop(prop, 'triangulate')
                col.prop(prop, 'saveAsExport')
                col.prop(prop, 'sortMaterialSlot')
                col.prop(prop, 'removeUnusedMaterialSlots')
                
                # removePolygons
                col.separator()
                display, split = ui.splitSwitch(col, prop, 'display_removePolygons_settings')
                split.prop(prop, 'removePolygons')
                if display:
                    box = col.box().column(align=True)
                    box.prop(prop, 'interval')
                    box.prop(prop, 'alphaThreshold')

                    box.separator()
                    box.label(text=iface_('Exclusion Materials List'))
                    box.template_list(DDDVT_UL_MaterialList.bl_idname, '',
                                      prop, 'excludeMaterials',
                                      prop, 'excludeMaterialsIndex')
                    
                    box.prop_search(prop, 'excludeMaterialSelector',
                                    bpy.data, 'materials', text='')
                    box.operator(DDDVT_OT_AddExcludeMaterial.bl_idname,
                                 text='Add', icon='ADD')

                    box.separator()
                    box.operator(DDDVT_OT_RemoveTransparentPolygons.bl_idname)

                # スプリングボーンツール
                col.separator
                display, split = ui.splitSwitch(col, prop, 'display_registerSpringBone_settings')
                split.operator(DDDVT_OT_registerSpringBone.bl_idname)
                if display:
                    box = col.box().column()
                    box.prop_search(prop, 'sb_json', context.blend_data, 'texts')

            else:
                col.label(text=iface_('VRM_Addon_for_Blender is not installed.'),
                          icon='INFO')
                col.operator(DDDVT_OT_openAddonPage.bl_idname)

################
classes = (
    DDDVT_MaterialListItem,
    DDDVT_propertyGroup,
    DDDVT_OT_addCollider,
    DDDVT_OT_setEmptyAsCollider,
    DDDVT_OT_duplicateColliderAsMirror,
    DDDVT_OT_registerSpringBone,
    DDDVT_OT_prepareToExportVRM,
    DDDVT_OT_openAddonPage,
    DDDVT_UL_MaterialList,
    DDDVT_OT_AddExcludeMaterial,
    DDDVT_OT_RemoveExcludeMaterial,
    DDDVT_OT_RemoveTransparentPolygons,
    DDDVT_PT_VRMTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_vt_prop = PointerProperty(type=DDDVT_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_vt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
