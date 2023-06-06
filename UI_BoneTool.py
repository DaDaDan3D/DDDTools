# -*- encoding:utf-8 -*-

import bpy
from bpy.props import PointerProperty, CollectionProperty, StringProperty, EnumProperty, BoolProperty, IntProperty, FloatProperty
from bpy.types import Panel, Operator, PropertyGroup
import math

from . import internalUtils as iu
from . import UIUtils as ui
from . import BoneTool as bt

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################################################################
class DDDBT_createEncasedSkip_propertyGroup(PropertyGroup):
    t_step: FloatProperty(
        name=_('Ring spacing'),
        description=_('Specifies the interval (in meters) to create a ring around the target mesh.'),
        subtype='DISTANCE',
        default=0.03,
        min=0.001,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    numberOfRays: IntProperty(
        name=_('Number of ring divisions'),
        description=_('Specifies the number of ring edges surrounding the target mesh.'),
        min=3,
        max=256,
        default=16,
    )
    radius: FloatProperty(
        name=_('Ring radius'),
        description=_('Specify the approximate radius of the ring around the target mesh. Note that if the radius is smaller than the target mesh, the skin will not be created properly and will be a line.'),
        subtype='DISTANCE',
        default=3.0,
        min=0.000,
        precision=3,
        step=1,
        unit='LENGTH',
    )
    window_size: IntProperty(
        name=_('Smoothing range'),
        description=_('Specifies the range of the Gaussian window when smoothing the skin. The larger the window, the wider the area considered and the more smoothing will be done.'),
        #subtype='FACTOR',
        min=1,
        max=256,
        default=3,
    )
    std_dev: FloatProperty(
        name=_('Standard Deviation'),
        description=_('Specifies the standard deviation of the Gaussian window when smoothing the skin. The larger the value, the stronger the smoothing.'),
        #subtype='FACTOR',
        default=1/6,
        min=0.00,
        max=1.00,
        precision=2,
        step=1,
    )
    outward_shift: FloatProperty(
        name=_('Ring dilation'),
        description=_('Specifies the amount by which the ring is fattened outward.'),
        #subtype='FACTOR',
        default=0,
        precision=3,
        step=1,
    )
    phase: FloatProperty(
        name=_('Ring rotation'),
        description=_('Specifies the amount of subtle rotation by which the ring is phased.'),
        #subtype='FACTOR',
        default=0,
        min=0.00,
        max=1.00,
        precision=2,
        step=1,
    )

    def draw(self, layout):
        col = layout.column(align=True)
        col.prop(self, 'radius')
        col.prop(self, 't_step')
        col.prop(self, 'numberOfRays')
        col.prop(self, 'phase')
        col.prop(self, 'outward_shift')
        col.prop(self, 'window_size')
        col.prop(self, 'std_dev')

    def copy_from(self, src):
        self.t_step = src.t_step
        self.numberOfRays = src.numberOfRays
        self.radius = src.radius
        self.window_size = src.window_size
        self.std_dev = src.std_dev
        self.outward_shift = src.outward_shift
        self.phase = src.phase

################
def get_axis_enum():
    return EnumProperty(
        name=_('Bone Axis'),
        description=_('Specifies the direction of the axis of the handle bone.'),
        items=[('POS_X', _('Local +X'), _('The bone axis is oriented in the positive direction of the local X-axis.')),
               ('POS_Y', _('Local +Y'), _('The bone axis is oriented in the positive direction of the local Y-axis.')),
               ('POS_Z', _('Local +Z'), _('The bone axis is oriented in the positive direction of the local Z-axis.')),
               ('NEG_X', _('Local -X'), _('The bone axis is oriented in the negaitive direction of the local X-axis.')),
               ('NEG_Y', _('Local -Y'), _('The bone axis is oriented in the negaitive direction of the local Y-axis.')),
               ('NEG_Z', _('Local -Z'), _('The bone axis is oriented in the negaitive direction of the local Z-axis.'))],
        default='NEG_Y')

################
class DDDBT_buildHandleFromVertices_propertyGroup(PropertyGroup):
    bone_length: FloatProperty(
        name=_('Bone Length'),
        description=_('Specify the length of the handle bone (m).'),
        subtype='DISTANCE',
        default=0.1,
        min=0.001,
        precision=2,
        step=1,
        unit='LENGTH',
    )
    set_parent: BoolProperty(
        name=_('Set Parent'),
        description=_('Make the created armature the parent of the mesh and set the vertex group and armature deformation modifier.'),
        default=True,
    )
    axis: get_axis_enum()

    def draw(self, layout):
        col = layout.column(align=True)
        col.prop(self, 'axis')
        col.prop(self, 'bone_length')
        col.prop(self, 'set_parent')

    def copy_from(self, src):
        self.bone_length = src.bone_length
        self.set_parent = src.set_parent
        self.axis = src.axis

################
class DDDBT_buildHandleFromBones_propertyGroup(PropertyGroup):
    bone_length: FloatProperty(
        name=_('Bone Length'),
        description=_('Specify the length of the handle bone (m).'),
        subtype='DISTANCE',
        default=0.1,
        min=0.001,
        precision=2,
        step=1,
        unit='LENGTH',
    )
    axis: get_axis_enum()

    def draw(self, layout):
        col = layout.column(align=True)
        col.prop(self, 'axis')
        col.prop(self, 'bone_length')

    def copy_from(self, src):
        self.bone_length = src.bone_length
        self.axis = src.axis

################
class DDDBT_propertyGroup(PropertyGroup):
    display_createArmatureFromSelectedEdges: BoolProperty(default=False)
    objNameToBasename: BoolProperty(
        name=_('Object Name to Bone Name'),
        description=_('The object name is automatically set as the bone name.'),
        default=True,
    )
    basename: StringProperty(
        name=_('Bone Name'),
        description=_('The name of the bone to be created.'),
        default='Bone',
    )

    display_createEncasedSkin: BoolProperty(default=False)
    createEncasedSkinProp: PointerProperty(
        type=DDDBT_createEncasedSkip_propertyGroup)

    display_buildHandleFromVertices: BoolProperty(default=False)
    buildHandleFromVerticesProp: PointerProperty(
        type=DDDBT_buildHandleFromVertices_propertyGroup)

    display_buildHandleFromBones: BoolProperty(default=False)
    buildHandleFromBonesProp: PointerProperty(
        type=DDDBT_buildHandleFromBones_propertyGroup)

################
class DDDBT_OT_renameChildBonesWithNumber(Operator):
    bl_idname = 'dddbt.rename_child_bones_with_number'
    bl_label = _('Rename Child Bones')
    bl_description = _('Rename all child bones with numbers.')
    bl_options = {'REGISTER', 'UNDO'}

    baseName: StringProperty(
        name=_('Basename'),
        description=_('The basename for renaming.'),
    )

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE' and bpy.context.active_object.mode=='EDIT' and bpy.context.active_bone

    def execute(self, context):
        bt.renameChildBonesWithNumber(bpy.context.active_bone, self.baseName)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.baseName = bpy.context.active_bone.name
        return context.window_manager.invoke_props_dialog(self)

################
class DDDBT_OT_resetStretchTo(Operator):
    bl_idname = 'dddbt.reset_stretch_to'
    bl_label = _('Reset Stretch')
    bl_description = _('Resets the length of all stretch modifiers in the armature to 0.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE'

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        ans = bt.resetStretchTo(arma)
        self.report({'INFO'},
                    iface_('Reset lengths of {ans} stretch modifiers of {arma_name}.').format(arma_name=arma.name, ans=ans))
        return {'FINISHED'}

################
class DDDBT_OT_applyArmatureToRestPose(Operator):
    bl_idname = 'dddbt.apply_armature_to_rest_pose'
    bl_label = _('Current to Rest Pose')
    bl_description = _('Sets the current pose of the active armature as the rest pose.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE'

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        #print(f'arma:{arma.name}')
        bt.applyArmatureToRestPose(arma)
        self.report({'INFO'},
                    iface_('{arma_name} is set as a rest pose.').format(arma_name=arma.name))
        return {'FINISHED'}

################
class DDDBT_OT_createArmatureFromSelectedEdges(Operator):
    bl_idname = 'dddbt.create_armature_from_selected_edges'
    bl_label = _('Edges to Bones')
    bl_description = _('Creates an armature such that the currently selected edge of the active mesh is the bone. The orientation and connections of the bones are automatically set by the distance from the 3D cursor.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'MESH'

    def execute(self, context):
        prop = context.scene.dddtools_bt_prop
        obj = iu.ObjectWrapper(bpy.context.active_object)
        if prop.objNameToBasename:
            basename = obj.name
        else:
            basename = prop.basename
        arma = bt.createArmatureFromSelectedEdges(obj, basename=basename)
        if arma:
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

################
class DDDBT_OT_createMeshFromSelectedBones(Operator):
    bl_idname = 'dddbt.create_mesh_from_selected_bones'
    bl_label = _('Bones to Edges')
    bl_description = _('A mesh is created as a child of the armature such that the bones in the active armature selection are the edges. Vertex weights are also set appropriately.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE'

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        obj = bt.createMeshFromSelectedBones(arma)
        if obj:
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

################
class DDDBT_OT_selectAncestralBones(Operator):
    bl_idname = 'dddbt.select_root_bones'
    bl_label = _('Select Ancestral Bones')
    bl_description = _('Select bones that are not related to each other by parent-child relationship. In other words, select only the bones that are closest to the ancestors of the selected bones.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bt.get_selected_bone_names()

    def execute(self, context):
        arma = iu.ObjectWrapper(bpy.context.active_object)
        selected_bones = bt.get_selected_bone_names()
        ancestral_bones = bt.get_ancestral_bones(arma, selected_bones)
        bt.select_bones(arma, ancestral_bones)
        return {'FINISHED'}

################
class DDDBT_OT_printSelectedBoneNamess(Operator):
    bl_idname = 'dddbt.print_selected_bone_names'
    bl_label = _('Print Selected Bone Names')
    bl_description = _('Enumerate the name of the selected bone in the information.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bt.get_selected_bone_names()

    def execute(self, context):
        selected_bones = bt.get_selected_bone_names()
        self.report({'INFO'},
                    iface_('Selected bones are: {selected_bones}').format(
                        selected_bones=sorted(selected_bones)))
        bpy.context.window_manager.clipboard = iu.format_list_as_string(
            selected_bones, indent_level=0)
        return {'FINISHED'}

################
class DDDBT_OT_createEncasedSkin(Operator):
    bl_idname = 'dddbt.create_encased_skin'
    bl_label = _('Create Encased Skin')
    bl_description = _('Create a skin that encases the active armature with reference to the selected mesh.')
    bl_options = {'REGISTER', 'UNDO'}

    m_prop: PointerProperty(type=DDDBT_createEncasedSkip_propertyGroup)
    
    @classmethod
    def poll(self, context):
        arma = bpy.context.active_object
        mesh = iu.findfirst_selected_object('MESH')
        return arma and arma.type == 'ARMATURE' and mesh and len(bpy.context.selected_objects) == 2

    def execute(self, context):
        prop = context.scene.dddtools_bt_prop
        arma = bpy.context.active_object
        mesh = iu.findfirst_selected_object('MESH')
        numberOfRays = self.m_prop.numberOfRays
        if self.m_prop.std_dev < 1e-5:
            window_size = 0
        else:
            window_size = min(self.m_prop.window_size, numberOfRays)
        phase = math.tau / numberOfRays * self.m_prop.phase
        skin = bt.createEncasedSkin(iu.ObjectWrapper(mesh),
                                    iu.ObjectWrapper(arma),
                                    t_step=self.m_prop.t_step,
                                    numberOfRays=numberOfRays,
                                    radius=self.m_prop.radius,
                                    window_size=window_size,
                                    std_dev=self.m_prop.std_dev,
                                    outward_shift=self.m_prop.outward_shift,
                                    phase=phase)
        self.report({'INFO'},
                    iface_('Created {skin_name}').format(
                        skin_name=skin.name))
        prop.createEncasedSkinProp.copy_from(self.m_prop)
        return {'FINISHED'}

    def invoke(self, context, event):
        prop = context.scene.dddtools_bt_prop
        self.m_prop.copy_from(prop.createEncasedSkinProp)
        return self.execute(context)

    def draw(self, context):
        self.m_prop.draw(self.layout)

################
class DDDBT_OT_buildHandleFromVertices(Operator):
    bl_idname = 'dddbt.build_handle_from_vertices'
    bl_label = _('Create vertex handles')
    bl_description = _('Creates the rig handles from the selected vertices of the selected objects.')
    bl_options = {'REGISTER', 'UNDO'}

    m_prop: PointerProperty(type=DDDBT_buildHandleFromVertices_propertyGroup)
    
    @classmethod
    def poll(self, context):
        return iu.findfirst_selected_object('MESH')

    def execute(self, context):
        prop = context.scene.dddtools_bt_prop
        prop.buildHandleFromVerticesProp.copy_from(self.m_prop)
        arma = bt.buildHandleFromVertices(bone_length=self.m_prop.bone_length,
                                          set_parent=self.m_prop.set_parent,
                                          axis=self.m_prop.axis)
        if arma:
            self.report({'INFO'},
                        iface_('Created {arma_name}').format(
                            arma_name=arma.name))
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        iface_('Failed to build armature.'))
            return {'CANCELLED'}

    def invoke(self, context, event):
        prop = context.scene.dddtools_bt_prop
        self.m_prop.copy_from(prop.buildHandleFromVerticesProp)
        return self.execute(context)

    def draw(self, context):
        self.m_prop.draw(self.layout)

################
class DDDBT_OT_buildHandleFromBones(Operator):
    bl_idname = 'dddbt.build_handle_from_bones'
    bl_label = _('Create rig handles')
    bl_description = _('Creates the rig handles from the selected bones.')
    bl_options = {'REGISTER', 'UNDO'}

    m_prop: PointerProperty(type=DDDBT_buildHandleFromBones_propertyGroup)
    
    @classmethod
    def poll(self, context):
        return bt.get_selected_bone_names()

    def execute(self, context):
        prop = context.scene.dddtools_bt_prop
        prop.buildHandleFromBonesProp.copy_from(self.m_prop)
        bones = bt.buildHandleFromBones(bone_length=self.m_prop.bone_length,
                                        axis=self.m_prop.axis)
        if bones:
            self.report({'INFO'},
                        iface_('Created {sorted_bones}').format(
                            sorted_bones=sorted(bones)))
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        iface_('Failed to build bone rigs.'))
            return {'CANCELLED'}

    def invoke(self, context, event):
        prop = context.scene.dddtools_bt_prop
        self.m_prop.copy_from(prop.buildHandleFromVerticesProp)
        return self.execute(context)

    def draw(self, context):
        self.m_prop.draw(self.layout)

################
class DDDBT_PT_BoneTool(Panel):
    bl_idname = 'BT_PT_BoneTool'
    bl_label = 'BoneTool'
    bl_category = 'DDDTools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
  
    def draw(self, context):
        prop = context.scene.dddtools_bt_prop
        layout = self.layout
        col = layout.column(align=True)
        col.operator(DDDBT_OT_selectAncestralBones.bl_idname)
        col.operator(DDDBT_OT_printSelectedBoneNamess.bl_idname)
        col.operator(DDDBT_OT_renameChildBonesWithNumber.bl_idname)
        col.operator(DDDBT_OT_resetStretchTo.bl_idname)
        col.operator(DDDBT_OT_applyArmatureToRestPose.bl_idname)
        col.operator(DDDBT_OT_createMeshFromSelectedBones.bl_idname)
        display, split = ui.splitSwitch(col, prop, 'display_createArmatureFromSelectedEdges')
        split.operator(DDDBT_OT_createArmatureFromSelectedEdges.bl_idname)
        if display:
            box = col.box().column()
            box.prop(prop, 'objNameToBasename')
            col2 = box.column(align=True)
            col2.enabled = not prop.objNameToBasename
            col2.prop(prop, 'basename')
    
        display, split = ui.splitSwitch(col, prop, 'display_createEncasedSkin')
        split.operator(DDDBT_OT_createEncasedSkin.bl_idname)
        if display:
            box = col.box()
            prop.createEncasedSkinProp.draw(box)

        display, split = ui.splitSwitch(col, prop, 'display_buildHandleFromVertices')
        split.operator(DDDBT_OT_buildHandleFromVertices.bl_idname)
        if display:
            box = col.box()
            prop.buildHandleFromVerticesProp.draw(box)

        display, split = ui.splitSwitch(col, prop, 'display_buildHandleFromBones')
        split.operator(DDDBT_OT_buildHandleFromBones.bl_idname)
        if display:
            box = col.box()
            prop.buildHandleFromBonesProp.draw(box)

################################################################
classes = (
    DDDBT_createEncasedSkip_propertyGroup,
    DDDBT_buildHandleFromVertices_propertyGroup,
    DDDBT_buildHandleFromBones_propertyGroup,
    DDDBT_propertyGroup,
    DDDBT_OT_renameChildBonesWithNumber,
    DDDBT_OT_resetStretchTo,
    DDDBT_OT_applyArmatureToRestPose,
    DDDBT_OT_createArmatureFromSelectedEdges,
    DDDBT_OT_createMeshFromSelectedBones,
    DDDBT_OT_selectAncestralBones,
    DDDBT_OT_printSelectedBoneNamess,
    DDDBT_OT_createEncasedSkin,
    DDDBT_OT_buildHandleFromVertices,
    DDDBT_OT_buildHandleFromBones,
    DDDBT_PT_BoneTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_bt_prop = PointerProperty(type=DDDBT_propertyGroup)

def unregisterClass():
    del bpy.types.Scene.dddtools_bt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()

