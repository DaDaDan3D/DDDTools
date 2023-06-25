# -*- encoding:utf-8 -*-

import bpy
from bpy.props import BoolProperty, IntProperty, PointerProperty, FloatProperty, StringProperty, EnumProperty
from bpy.types import Panel, Operator, PropertyGroup
import traceback

from . import internalUtils as iu
from . import UIUtils as ui
from . import WeightTool as wt

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################################################################
class DDDWT_smooth_vertex_weights_falloff_pg(PropertyGroup):
    count: IntProperty(
        name=_('Iterations'),
        description=_('Specifies the number of times smoothing is to be performed.'),
        min=1,
        max=200,
        default=10,
    )

    radius: FloatProperty(
        name=_('Radius'),
        description=_('Specifies the range of influence of smoothing.'),
        subtype='DISTANCE',
        default=1.0,
        min=1e-9,
        precision=2,
        step=1,
        unit='LENGTH',
    )
        
    normalize: BoolProperty(
        name=_('Normalize'),
        description=_('Specifies whether the vertex weights should be normalized so that they sum to 1.0.'),
        default=False,
    )

    def draw(self, layout):
        col = layout.column(align=True)
        col.prop(self, 'count')
        col.prop(self, 'radius')
        col.prop(self, 'normalize')

    def copy_from(self, src):
        self.count = src.count
        self.radius = src.radius
        self.normalize = src.normalize

################
class DDDWT_smooth_vertex_weights_least_square_pg(PropertyGroup):
    count: IntProperty(
        name=_('Iterations'),
        description=_('Specifies the number of times smoothing is to be performed.'),
        min=1,
        max=5,
        default=1,
    )

    strength: FloatProperty(
        name=_('Strength'),
        description=_('Specifies the smoothing intensity; the closer to 1, the stronger the smoothing.'),
        #subtype='FACTOR',
        default=0.5,
        min=0,
        max=1,
        precision=2,
        step=1,
    )
        
    normalize: BoolProperty(
        name=_('Normalize'),
        description=_('Specifies whether the vertex weights should be normalized so that they sum to 1.0.'),
        default=False,
    )

    def draw(self, layout):
        col = layout.column(align=True)
        col.prop(self, 'count')
        col.prop(self, 'strength')
        col.prop(self, 'normalize')

    def copy_from(self, src):
        self.count = src.count
        self.strength = src.strength
        self.normalize = src.normalize

################
class DDDWT_propertyGroup(PropertyGroup):
    display_cleanupWeightsOfSelectedObjects: BoolProperty(
        name='cleanupWeightsOfSelectedObjects_settings',
        default=True)
    affectBoneMax: IntProperty(
        name=_('Number of influence bones'),
        description=_('Sets the number of influence bones for the weights.'),
        min=1,
        max=10,
        default=4,
    )

    display_transferWeightsForSelectedObjects: BoolProperty(
        name='transferWeightsForSelectedObjects_settings',
        default=True)
    weightObj: PointerProperty(
        name=_('Transfer From'),
        description=_('The mesh object from which the weights are transferred.'),
        type=bpy.types.Object,
        poll=lambda self, obj: obj and obj.type=='MESH',
    )
    vertexGroup: StringProperty(
        name=_('Vertex Group'),
        description=_('Vertex group name from which to select the affected range.'),
    )
    invertVertexGroup: BoolProperty(
        name=_('Inversion'),
        description=_('Inverts the influence of vertex groups.'),
        default=False,
    )
    vertMapping: EnumProperty(
        name=_('Vertex Mappings'),
        description=_('Method to find the vertex from which the transfer originates.'),
        items=[('NEAREST', _('Nearest vertex'), _('Copy from the nearest vertex.'), 'VERTEXSEL', 0),
               ('EDGEINTERP_NEAREST', _('Interpolation of nearest edge'), _('Interpolate from the perpendicular to the nearest edge.'), 'EDGESEL', 1),
               ('POLYINTERP_NEAREST', _('Interpolation of nearest face'), _('Interpolate from the perpendicular to the nearest plane.'), 'FACESEL', 2),
               ('POLYINTERP_VNORPROJ', _('Interpolation of projection surface'), _('Interpolate from the closest hit surface by projecting in the normal direction.'), 'SNAP_NORMAL', 3)],
        default='POLYINTERP_NEAREST',
    )
    maxDistance: FloatProperty(
        name=_('Maximum distance'),
        description=_('The maximum distance that can be transferred (0 for infinite).'),
        subtype='DISTANCE',
        default=0.01,
        min=0.000,
        precision=3,
        step=0.005,
        unit='LENGTH',
    )

    display_setWeightForSelectedBones: BoolProperty(
        name='setWeightForSelectedBones_settings',
        default=True)
    weight: FloatProperty(
        name=_('Vertex Weight'),
        description=_('Vertex weight to be set.'),
        #subtype='FACTOR',
        default=0.0,
        min=0.0,
        max=1.0,
        precision=3,
        step=1,
    )

    display_smooth_vertex_weights_falloff: BoolProperty(default=False)
    smooth_vertex_weights_falloff_prop: PointerProperty(
        type=DDDWT_smooth_vertex_weights_falloff_pg)

    display_smooth_vertex_weights_least_square: BoolProperty(default=False)
    smooth_vertex_weights_least_square_prop: PointerProperty(
        type=DDDWT_smooth_vertex_weights_least_square_pg)

################################################################
class DDDWT_OT_resetWeightOfSelectedObjects(bpy.types.Operator):
    bl_idname = 'dddwt.reset_weight_of_selected_objects'
    bl_label = _('Reset Vertex Weights')
    bl_description = _('Remove all vertex weights from the selected mesh.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        num = wt.resetWeightOfSelectedObjects()
        if num > 0:
            self.report({'INFO'},
                        iface_('Reset weights for {num} meshes.').format(
                            num=num))
        else:
            self.report({'INFO'},
                        iface_('No mesh is selected.'))
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

################################################################
class DDDWT_OT_cleanupWeightsOfSelectedObjects(bpy.types.Operator):
    bl_idname = 'dddwt.cleanup_weights_of_selected_objects'
    bl_label = _('Clean up weights')
    bl_description = _('Clean up the weights of the selected mesh.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_wt_prop
        num = wt.cleanupWeightsOfSelectedObjects(affectBoneMax=prop.affectBoneMax)
        if num > 0:
            self.report({'INFO'},
                        iface_('Cleaned up the vertex weights of {num} meshes.').format(
                            num=num))
        else:
            self.report({'INFO'},
                        iface_('No mesh is selected.'))
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

################################################################
class DDDWT_OT_transferWeightsForSelectedObjects(bpy.types.Operator):
    bl_idname = 'dddwt.transfer_weights_for_selected_objects'
    bl_label = _('Weight transfer')
    bl_description = _('Transfers the vertex weights of the specified mesh to the selected mesh.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        prop = context.scene.dddtools_wt_prop
        return prop.weightObj and bpy.context.selected_objects

    def execute(self, context):
        prop = context.scene.dddtools_wt_prop
        ans = wt.transferWeightsForSelectedObjects(
            iu.ObjectWrapper(prop.weightObj),
            max_distance=prop.maxDistance,
            vert_mapping=prop.vertMapping,
            vertex_group=prop.vertexGroup,
            invert_vertex_group=prop.invertVertexGroup)
        self.report({'INFO'},
                    iface_('Vertex weights were transferred to {ans} meshes.').format(
                        ans=ans))
        return {'FINISHED'}

################################################################
class DDDWT_OT_equalizeVertexWeightsForMirroredBones(bpy.types.Operator):
    bl_idname = 'dddwt.equalize_vertex_weights_for_mirrored_bones'
    bl_label = _('Equalize vertex weights to the left and right')
    bl_description = _('Assigns the weights of selected vertices of the specified mesh equally to the left and right bones.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj and obj.mode == 'EDIT' and iu.get_total_vert_sel(obj) > 0

    def execute(self, context):
        mesh = iu.ObjectWrapper(bpy.context.active_object)
        ans = wt.equalizeVertexWeightsForMirroredBones(mesh)
        self.report({'INFO'},
                    iface_('Adjusted weights for {ans} vertices of {mesh_name}.').format(
                        mesh_name=mesh.name,
                        ans=ans))
        return {'FINISHED'}

################################################################
class DDDWT_OT_dissolveWeightedBones(bpy.types.Operator):
    bl_idname = 'dddwt.dissolve_weighted_bones'
    bl_label = _('Dissolve selected bones')
    bl_description = _('After transferring the weight of the selected bone to the nearest ancestral deformed bone, dissolve .')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj and obj.type == 'ARMATURE' and obj.mode == 'EDIT' and bpy.context.selected_editable_bones

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        bones = [bone.name for bone in bpy.context.selected_editable_bones]
        ans = wt.dissolveWeightedBones(arma, bones)
        self.report({'INFO'},
                    iface_('Bone dissolved. {ans}').format(
                        ans=ans))
        return {'FINISHED'}

################################################################
class DDDWT_OT_setWeightForSelectedBones(Operator):
    bl_idname = 'dddwt.set_weight_for_selected_bones'
    bl_label = _('Batch setting of vertex weights')
    bl_description = _('Set the weights of the selected bones for the selected vertices at once.')
    bl_options = {'REGISTER', 'UNDO'}

    weight: FloatProperty(
        name=_('Vertex Weight'),
        description=_('Vertex weight to be set.'),
        #subtype='FACTOR',
        default=0.0,
        min=0.0,
        max=1.0,
        precision=3,
        step=1,
    )

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        arma = iu.findfirst_selected_object('ARMATURE')
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT' and\
            arma and arma.type == 'ARMATURE' and\
            len(bpy.context.selected_objects) == 2

    def execute(self, context):
        obj = bpy.context.active_object
        arma = iu.findfirst_selected_object('ARMATURE')
        count, bones, errormsg = wt.set_weight_for_selected_bones(obj, arma, self.weight)
        if count == 0:
            if errormsg:
                self.report({'WARNING'}, errormsg)
            else:
                self.report({'WARNING'},
                            iface_('Failed to set the weights. Please select vertices and bones.'))
            return {'CANCELLED'}
        else:
            self.report({'INFO'},
                        iface_('Set {weight:.3} to the target bones at {count} vertices. Target bones: {bone_names}').format(
                            count=count,
                            weight=self.weight,
                            bone_names=str(sorted(bones))))
            return {'FINISHED'}

    def invoke(self, context, event):
        prop = context.scene.dddtools_wt_prop
        self.weight = prop.weight
        return self.execute(context)

################################################################
class DDDWT_OT_smoothVertexWeightFalloff(Operator):
    bl_idname = 'paint.dddwt_smooth_vertex_weights_falloff'
    bl_label = _('Vertex weight smooth (range)')
    bl_description = _('Smoothes the weight of selected vertices by distance, referring to polygonal connections.')
    bl_options = {'REGISTER', 'UNDO'}

    m_prop : PointerProperty(type=DDDWT_smooth_vertex_weights_falloff_pg)

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj.mode == 'WEIGHT_PAINT' and iu.get_total_vert_sel(obj) >= 2

    def execute(self, context):
        obj = bpy.context.active_object
        wt.smooth_vertex_weights_falloff(obj,
                                         count=self.m_prop.count,
                                         radius=self.m_prop.radius,
                                         normalize=self.m_prop.normalize)
        with iu.mode_context(obj, 'OBJECT'):
            bpy.context.view_layer.update()
        prop = context.scene.dddtools_wt_prop
        prop.smooth_vertex_weights_falloff_prop.copy_from(self.m_prop)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        prop = context.scene.dddtools_wt_prop
        self.m_prop.copy_from(prop.smooth_vertex_weights_falloff_prop)
        return self.execute(context)

    def draw(self, context):
        self.m_prop.draw(self.layout)

################################################################
class DDDWT_OT_smoothVertexWeightLeastSquare(Operator):
    bl_idname = 'paint.dddwt_smooth_vertex_weights_least_square'
    bl_label = _('Vertex weight smooth (approximate)')
    bl_description = _('Smoothes the weights of selected vertices by the least-squares method, referring to the polygonal connections.')
    bl_options = {'REGISTER', 'UNDO'}

    m_prop : PointerProperty(type=DDDWT_smooth_vertex_weights_least_square_pg)

    @classmethod
    def poll(self, context):
        obj = bpy.context.active_object
        return obj.mode == 'WEIGHT_PAINT' and iu.get_total_vert_sel(obj) >= 2

    def execute(self, context):
        obj = bpy.context.active_object
        wt.smooth_vertex_weights_least_square(obj,
                                              count=self.m_prop.count,
                                              strength=self.m_prop.strength,
                                              normalize=self.m_prop.normalize,
                                              limit=1e-3)
        with iu.mode_context(obj, 'OBJECT'):
            bpy.context.view_layer.update()
        prop = context.scene.dddtools_wt_prop
        prop.smooth_vertex_weights_least_square_prop.copy_from(self.m_prop)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        prop = context.scene.dddtools_wt_prop
        self.m_prop.copy_from(prop.smooth_vertex_weights_least_square_prop)
        return self.execute(context)

    def draw(self, context):
        self.m_prop.draw(self.layout)

################################################################
class DDDWT_PT_WeightTool(bpy.types.Panel):
    bl_idname = 'WT_PT_WeightTool'
    bl_label = 'WeightTool'
    bl_category = 'DDDTools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_wt_prop
        layout = self.layout.column(align=True)

        # resetWeightOfSelectedObjects
        layout.operator(DDDWT_OT_resetWeightOfSelectedObjects.bl_idname)

        # cleanupWeightsOfSelectedObjects
        display, split = ui.splitSwitch(layout, prop, 'display_cleanupWeightsOfSelectedObjects')
        split.operator(DDDWT_OT_cleanupWeightsOfSelectedObjects.bl_idname)
        if display:
            col = layout.box().column()
            col.prop(prop, 'affectBoneMax')
        
        # transferWeightsForSelectedObjects
        display, split = ui.splitSwitch(layout, prop, 'display_transferWeightsForSelectedObjects')
        split.operator(DDDWT_OT_transferWeightsForSelectedObjects.bl_idname)
        mesh = bpy.context.active_object
        if display and mesh and mesh.type=='MESH':
            col = layout.box().column(align=True)
            col.prop_search(prop, 'weightObj', context.blend_data, 'objects')

            if mesh.vertex_groups:
                row = col.row(align=True)
                row.prop_search(prop, 'vertexGroup', mesh, 'vertex_groups')
                row.prop(prop, 'invertVertexGroup', text='', icon='ARROW_LEFTRIGHT')

            col.prop(prop, 'vertMapping')
            col.prop(prop, 'maxDistance')
        
        # equalizeVertexWeightsForMirroredBones
        layout.operator(DDDWT_OT_equalizeVertexWeightsForMirroredBones.bl_idname)

        # dissolveWeightedBones
        layout.operator(DDDWT_OT_dissolveWeightedBones.bl_idname)

        display, split = ui.splitSwitch(layout, prop, 'display_setWeightForSelectedBones')
        split.operator(DDDWT_OT_setWeightForSelectedBones.bl_idname)
        if display:
            col = layout.box().column(align=True)
            col.prop(prop, 'weight')

        display, split = ui.splitSwitch(layout, prop, 'display_smooth_vertex_weights_falloff')
        split.operator(DDDWT_OT_smoothVertexWeightFalloff.bl_idname)
        if display:
            col = layout.box().column(align=True)
            prop.smooth_vertex_weights_falloff_prop.draw(col)

        # display, split = ui.splitSwitch(layout, prop, 'display_smooth_vertex_weights_least_square')
        # split.operator(DDDWT_OT_smoothVertexWeightLeastSquare.bl_idname)
        # if display:
        #     col = layout.box().column(align=True)
        #     prop.smooth_vertex_weights_least_square_prop.draw(col)

################################################################
classes = (
    DDDWT_smooth_vertex_weights_falloff_pg,
    DDDWT_smooth_vertex_weights_least_square_pg,
    DDDWT_propertyGroup,
    DDDWT_OT_resetWeightOfSelectedObjects,
    DDDWT_OT_cleanupWeightsOfSelectedObjects,
    DDDWT_OT_transferWeightsForSelectedObjects,
    DDDWT_OT_equalizeVertexWeightsForMirroredBones,
    DDDWT_OT_dissolveWeightedBones,
    DDDWT_OT_setWeightForSelectedBones,
    DDDWT_OT_smoothVertexWeightFalloff,
    #DDDWT_OT_smoothVertexWeightLeastSquare,
    DDDWT_PT_WeightTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_wt_prop = PointerProperty(type=DDDWT_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_wt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
