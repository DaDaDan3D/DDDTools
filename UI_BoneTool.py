# -*- encoding:utf-8 -*-

import bpy
from bpy.props import PointerProperty, CollectionProperty, StringProperty, EnumProperty, BoolProperty, IntProperty, FloatProperty, FloatVectorProperty
from bpy.types import Menu, Panel, Operator, PropertyGroup
import gpu
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
import math
from mathutils import (
    Vector,
    Matrix,
)
import numpy as np
import random

from . import internalUtils as iu
from . import mathUtils as mu
from . import UIUtils as ui
from . import BoneTool as bt
from . import ProportionalMover as pm

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################################################################
class DDDBT_createEncasedSkin_propertyGroup(PropertyGroup):
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
class DDDBT_createBonesFromSelectedEdges_propertyGroup(PropertyGroup):
    obj_name_to_basename: BoolProperty(
        name=_('Object Name to Bone Name'),
        description=_('The object name is automatically set as the bone name.'),
        default=True,
    )
    basename: StringProperty(
        name=_('Bone Name'),
        description=_('The name of the bone to be created.'),
        default='Lip',
    )
    suffix: StringProperty(
        name=_('Suffix'),
        description=_('Specify a suffix.'),
        default='L',
    )
    create_handle: BoolProperty(
        name=_('To Rig'),
        description=_('If checked, handles are created for use as rigs. It also automatically creates Stretch-to-constraints, transform copy-constraints, etc. This allows the handles created before and after the bones to be manipulated as a rig.'),
        default=False,
    )
    bbone_segments: IntProperty(
        name=_('Number of Bendy Bone segments'),
        description=_('Specifies the number of bendy bone segments; if set to 2 or more, the bones will become bendy bones.'),
        min=1,
        max=32,
        default=1,
    )
    set_weight: BoolProperty(
        name=_('Add vertex weights'),
        description=_('Add vertex weights to the edge vertices, corresponding to the bones created.'),
        default=True,
    )

    def draw(self, layout):
        col = layout.column(align=True)
        col.prop(self, 'obj_name_to_basename')
        col2 = col.box().column(align=True)
        col2.enabled = not self.obj_name_to_basename
        col2.prop(self, 'basename')
        col2.prop(self, 'suffix')

        col.prop(self, 'set_weight')
        col.prop(self, 'create_handle')
        col.prop(self, 'bbone_segments')

    def copy_from(self, src):
        self.obj_name_to_basename = src.obj_name_to_basename
        self.basename = src.basename
        self.suffix = src.suffix
        self.create_handle = src.create_handle
        self.bbone_segments = src.bbone_segments
        self.set_weight = src.set_weight

################
class DDDBT_buildHandleFromVertices_propertyGroup(PropertyGroup):
    handle_factor: FloatProperty(
        name=_('Handle Length'),
        description=_('Specifies the approximate length of the handle. The length is automatically calculated from the median of the area of the polygons.'),
        subtype='FACTOR',
        default=0.5,
        min=0.01,
        max=2.00,
        precision=2,
        step=1,
    )
    handle_align_axis: BoolProperty(
        name=_('Axial direction'),
        description=_('Specifies whether the handles to be aligned in the direction of the axis.'),
        default=True,
    )
    set_weight: BoolProperty(
        name=_('Add vertex weights'),
        description=_('Add vertex weights to the edge vertices, corresponding to the bones created.'),
        default=True,
    )

    def draw(self, layout):
        col = layout.column(align=True)
        col.prop(self, 'handle_factor')
        col.prop(self, 'handle_align_axis')
        col.prop(self, 'set_weight')

    def copy_from(self, src):
        self.handle_factor = src.handle_factor
        self.handle_align_axis = src.handle_align_axis
        self.set_weight = src.set_weight

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
class DDDBT_changeBoneLengthDirection_propertyGroup(PropertyGroup):
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
    direction: FloatVectorProperty(
        name=_('Bone Direction'),
        description=_('Specifies the direction of the bone.'),
        size=3,
        default=[0, -1, 0],
        precision=2,
        step=1.0,
        unit='NONE',
    )

    def draw(self, layout):
        col = layout.column(align=False)
        col.prop(self, 'direction')
        col.prop(self, 'bone_length')

    def copy_from(self, src):
        self.bone_length = src.bone_length
        self.direction = src.direction

################
class DDDBT_adjustBendyBoneSize_propertyGroup(PropertyGroup):
    ratio_z: FloatProperty(
        name=_('Ratio Z'),
        description=_('Sets the ratio of the bendy bone size to the length of the bone in the Z direction.'),
        subtype='FACTOR',
        default=0.1,
        min=0.01,
        max=2.00,
        precision=2,
        step=1,
    )
    ratio_x: FloatProperty(
        name=_('Ratio X'),
        description=_('Sets the ratio of the bendy bone size to the length of the bone in the X direction.'),
        subtype='FACTOR',
        default=0.1,
        min=0.01,
        max=2.00,
        precision=2,
        step=1,
    )

    def draw(self, layout):
        col = layout.column(align=False)
        col.prop(self, 'ratio_x')
        col.prop(self, 'ratio_z')

    def copy_from(self, src):
        self.ratio_z = src.ratio_z
        self.ratio_x = src.ratio_x

################
class DDDBT_poseProportionalMove_propertyGroup(PropertyGroup):
    use_proportional: BoolProperty(
        name=_('Use Proportional'),
        description=_('Specifies whether to move proportionally. If unchecked, no proportional movement is performed and only the selected bone is moved.'),
        default=True,
    )

    falloff_type: mu.get_falloff_enum()
    
    influence_radius: FloatProperty(
        name=_('Influence Radius'),
        description=_('Specify the range of influence of the proportional move.'),
        min=1e-9,
        default=1.0,
    )

    use_block_with_mesh: BoolProperty(
        name=_('Block with mesh'),
        description=_('Specifies whether to stop at the surface of the specified mesh.'),
        default=False)
    display_block_with_mesh: BoolProperty(default=False)
    block_with_mesh_prop: PointerProperty(type=pm.DDDPM_MeshBlockModifier_pg)

    use_snap_onto_mesh: BoolProperty(
        name=_('Snap to mesh'),
        description=_('Specifies whether to fly rays from the camera and snap them to the surface of the specified mesh.'),
        default=False)
    display_snap_onto_mesh: BoolProperty(default=False)
    snap_onto_mesh_prop: PointerProperty(type=pm.DDDPM_MeshSnapModifier_pg)

    def draw(self, context, layout):
        col = layout.column(align=False)
        col.prop(self, 'use_proportional')
        box = col.box()
        box.enabled = self.use_proportional
        box.prop(self, 'falloff_type')
        box.prop(self, 'influence_radius')

        display, split = ui.splitSwitch(col, self, 'display_block_with_mesh')
        split.prop(self, 'use_block_with_mesh')
        if display:
            box = col.box()
            box.enabled = self.use_block_with_mesh
            self.block_with_mesh_prop.draw(context, box)
    
        display, split = ui.splitSwitch(col, self, 'display_snap_onto_mesh')
        split.prop(self, 'use_snap_onto_mesh')
        if display:
            box = col.box()
            box.enabled = self.use_snap_onto_mesh
            self.snap_onto_mesh_prop.draw(context, box)
    
    def copy_from(self, src):
        self.use_proportional = src.use_proportional
        self.falloff_type = src.falloff_type
        self.influence_radius = src.influence_radius

        self.use_block_with_mesh = src.use_block_with_mesh
        #self.display_block_with_mesh = src.display_block_with_mesh
        self.block_with_mesh_prop.copy_from(src.block_with_mesh_prop)

        self.use_snap_onto_mesh = src.use_snap_onto_mesh
        #self.display_snap_onto_mesh = src.display_snap_onto_mesh
        self.snap_onto_mesh_prop.copy_from(src.snap_onto_mesh_prop)

################
class DDDBT_propertyGroup(PropertyGroup):
    display_createBonesFromSelectedEdges: BoolProperty(default=False)
    createBonesFromSelectedEdgesProp: PointerProperty(
        type=DDDBT_createBonesFromSelectedEdges_propertyGroup)

    display_createEncasedSkin: BoolProperty(default=False)
    createEncasedSkinProp: PointerProperty(
        type=DDDBT_createEncasedSkin_propertyGroup)

    display_buildHandleFromVertices: BoolProperty(default=False)
    buildHandleFromVerticesProp: PointerProperty(
        type=DDDBT_buildHandleFromVertices_propertyGroup)

    display_buildHandleFromBones: BoolProperty(default=False)
    buildHandleFromBonesProp: PointerProperty(
        type=DDDBT_buildHandleFromBones_propertyGroup)

    display_changeBoneLengthDirection: BoolProperty(default=False)
    changeBoneLengthDirectionProp: PointerProperty(
        type=DDDBT_changeBoneLengthDirection_propertyGroup)

    display_adjustBendyBoneSize: BoolProperty(default=False)
    adjustBendyBoneSizeProp: PointerProperty(
        type=DDDBT_adjustBendyBoneSize_propertyGroup)

    display_poseProportionalMove: BoolProperty(default=False)
    poseProportionalMoveProp: PointerProperty(
        type=DDDBT_poseProportionalMove_propertyGroup)

################
class DDDBT_OT_renameChildBonesWithNumber(Operator):
    bl_idname = 'dddbt.rename_child_bones_with_number'
    bl_label = _('Rename Child Bones')
    bl_description = _('Renames all child bones of the active bone with a number.')
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
class DDDBT_OT_renameBonesForSymmetry(Operator):
    bl_idname = 'armature.dddbt_rename_bones_for_symmetry'
    bl_label = _('Rename Symmetry')
    bl_description = _('Rename the selected bones to account for left-right symmetry.')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return bt.get_selected_bone_names()

    def execute(self, context):
        arma = bpy.context.active_object
        selected_bones = bt.get_selected_bone_names()
        renamed_bones = bt.rename_bones_for_symmetry(arma, selected_bones)
        if renamed_bones:
            self.report({'INFO'},
                        iface_('Renamed {len_renamed_bones} bones.').format(len_renamed_bones=len(renamed_bones)))
            bt.select_bones(iu.ObjectWrapper(arma), renamed_bones)
            return {'FINISHED'}
        else:
            self.report({'INFO'}, iface_('No bones renamed.'))
            return {'CANCELLED'}

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
class DDDBT_OT_createBonesFromSelectedEdges(Operator):
    bl_idname = 'dddbt.create_armature_from_selected_edges'
    bl_label = _('Edges to Bones')
    # FIXME
    bl_description = _('Creates bones based on the currently selected edges of the active mesh. The orientation of the bone is automatically set by the distance from the 3D cursor. Searches for an armature by looking at the parent and armature modifiers and creates a new armature if there is none.')
    bl_options = {'REGISTER', 'UNDO'}

    m_prop: PointerProperty(type=DDDBT_createBonesFromSelectedEdges_propertyGroup)

    @classmethod
    def poll(self, context):
        return bpy.context.mode == 'EDIT_MESH' and iu.get_total_edge_sel(bpy.context.active_object) > 0

    def execute(self, context):
        prop = context.scene.dddtools_bt_prop
        prop.createBonesFromSelectedEdgesProp.copy_from(self.m_prop)
        obj = iu.ObjectWrapper(bpy.context.active_object)
        if self.m_prop.obj_name_to_basename:
            basename = obj.name
        else:
            basename = self.m_prop.basename
        suffix = self.m_prop.suffix
        if suffix: suffix = f'.{suffix}'

        arma, created_bones = bt.createBonesFromSelectedEdges(
            obj,
            basename=basename,
            suffix=suffix,
            use_existing_armature=True,
            create_handle=self.m_prop.create_handle,
            bbone_segments=self.m_prop.bbone_segments,
            set_weight=self.m_prop.set_weight)
        
        if arma:
            self.report({'INFO'},
                        iface_('Created bones ({created_bones}) on armature ({arma_name}).').\
                        format(arma_name=arma.name,
                               created_bones=sorted(created_bones)))
            bt.select_bones(arma, created_bones)
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, iface_('No bones were created.'))
            return {'CANCELLED'}

    def invoke(self, context, event):
        prop = context.scene.dddtools_bt_prop
        self.m_prop.copy_from(prop.createBonesFromSelectedEdgesProp)
        return self.execute(context)

    def draw(self, context):
        self.m_prop.draw(self.layout)

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

    m_prop: PointerProperty(type=DDDBT_createEncasedSkin_propertyGroup)
    
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
    bl_description = _('Creates a rig handle from selected vertices of the selected object. Searches for parent and armature modifiers and creates a new armature if there is none.')
    bl_options = {'REGISTER', 'UNDO'}

    m_prop: PointerProperty(type=DDDBT_buildHandleFromVertices_propertyGroup)
    
    @classmethod
    def poll(self, context):
        return bpy.context.mode == 'EDIT_MESH' and iu.findfirst_selected_object('MESH')

    def execute(self, context):
        prop = context.scene.dddtools_bt_prop
        prop.buildHandleFromVerticesProp.copy_from(self.m_prop)
        arma, created_bones = bt.buildHandleFromVertices(
            handle_factor=self.m_prop.handle_factor,
            handle_align_axis=self.m_prop.handle_align_axis,
            use_existing_armature=True,
            set_weight=self.m_prop.set_weight)
            
        if arma:
            self.report({'INFO'},
                        iface_('Created bones ({created_bones}) on armature ({arma_name}).').\
                        format(arma_name=arma.name,
                               created_bones=sorted(created_bones)))
            bt.select_bones(arma, created_bones)
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        iface_('No bones were created.'))
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
        self.m_prop.copy_from(prop.buildHandleFromBonesProp)
        return self.execute(context)

    def draw(self, context):
        self.m_prop.draw(self.layout)

################
class DDDBT_OT_changeBoneLengthDirection(Operator):
    bl_idname = 'dddbt.change_bone_length_direction'
    bl_label = _('Set bone length and direction')
    bl_description = _('Forces the length and direction of the selected bone.')
    bl_options = {'REGISTER', 'UNDO'}

    m_prop: PointerProperty(type=DDDBT_changeBoneLengthDirection_propertyGroup)
    
    @classmethod
    def poll(self, context):
        return bt.get_selected_bone_names()

    def execute(self, context):
        arma = bpy.context.active_object
        prop = context.scene.dddtools_bt_prop
        prop.changeBoneLengthDirectionProp.copy_from(self.m_prop)
        bt.changeBoneLengthDirection(arma,
                                     length=self.m_prop.bone_length,
                                     local_direction=self.m_prop.direction)
        return {'FINISHED'}

    def invoke(self, context, event):
        prop = context.scene.dddtools_bt_prop
        self.m_prop.copy_from(prop.changeBoneLengthDirectionProp)
        return self.execute(context)

    def draw(self, context):
        self.m_prop.draw(self.layout)

################
class DDDBT_OT_adjustBendyBoneSize(Operator):
    bl_idname = 'armature.dddbt_adjust_bendy_bone_size'
    bl_label = _('Adjust Bendy Bone Size')
    bl_description = _('Adjusts the size of the selected bone when it is displayed as a B-bone.')
    bl_options = {'REGISTER', 'UNDO'}

    m_prop: PointerProperty(type=DDDBT_adjustBendyBoneSize_propertyGroup)
    
    @classmethod
    def poll(self, context):
        return bt.get_selected_bone_names()

    def execute(self, context):
        arma = bpy.context.active_object
        bone_names = bt.get_selected_bone_names()
        prop = context.scene.dddtools_bt_prop
        prop.adjustBendyBoneSizeProp.copy_from(self.m_prop)
        bt.adjust_bendy_bone_size(arma,
                                  bone_names,
                                  self.m_prop.ratio_z,
                                  self.m_prop.ratio_x)
        return {'FINISHED'}

    def invoke(self, context, event):
        prop = context.scene.dddtools_bt_prop
        self.m_prop.copy_from(prop.adjustBendyBoneSizeProp)
        return self.execute(context)

    def draw(self, context):
        self.m_prop.draw(self.layout)

################
class DDDBT_OT_poseProportionalMove(Operator):
    bl_idname = 'pose.dddbt_pose_proportional_move'
    bl_label = _('Pose Proportional Move')
    bl_description = _('Proportionally move the pose bone.')
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    m_prop: PointerProperty(type=DDDBT_poseProportionalMove_propertyGroup)

    move_vector: FloatVectorProperty(
        name=_('Move Vector'),
        description=_('Specifies the amount (in meters) by which the bone is to be moved.'),
        size=3,
        default=[0, 0, 0],
        precision=2,
        step=1.0,
        unit='LENGTH',
    )

    direction: pm.get_direction_enum()

    ################
    def __init__(self):
        # プロポーショナル移動するクラス
        self.pm = pm.ProportionalMover()

        # bone.matrix.translation の保存
        self.bone_translations = None

        # 描画ハンドル
        self._handle = None

        # context.area.show_menus の保存
        self.prev_show_menus = None

        # center_location のあるべき位置をマウス座標に変換したもの
        self.mouse_xy = None

        # center_location のあるべき位置の保存
        self.prev_center_location = None

        # 数値入力
        self.number_input = iu.NumberInput()

        # 数値入力開始時の move_vector
        self.save_move_vector = None

    ################
    # 方向ベクトルまたは法線ベクトルを得る
    def get_direction_vector(self, context):
        di = pm.DIRECTION_INFO[self.direction]
        if di.constant_direction:
            return di.vector

        elif di.uniform_direction:
            row = di.row_index
            assert row >= 0, f'Illegal direction: {self.direction}'
            mtx = np.array(context.active_object.matrix_world)
            return Vector(mtx[:3, row])

        else:
            raise RuntimeError()

    ################
    # 基本の単位ベクトルを得る
    def get_direction_unit(self, context):
        di = pm.DIRECTION_INFO[self.direction]

        if not di.uniform_direction:    return Vector((0, 0, 1))
        if di.normal_direction:         return Vector()
        if di.constant_direction:       return di.vector

        if self.direction in {'LOCAL_X', 'LOCAL_Y', 'LOCAL_Z'}:
            mtx = np.array(context.active_object.matrix_world)
            return Vector(mtx[:3, di.row])

        return Vector()

    ################
    def compute_mouse_move(self, context, mouse_diff):
        self.mouse_xy += mouse_diff
        center_location = Vector(self.pm.center_location)

        # Get the 3D location that corresponds to the new mouse position
        if self.direction == 'NONE':
            new_location = view3d_utils.region_2d_to_location_3d(
                context.region, context.region_data,
                self.mouse_xy, center_location)

        elif self.direction in {'GLOBAL_YZ', 'GLOBAL_ZX', 'GLOBAL_XY',
                                'LOCAL_YZ', 'LOCAL_ZX', 'LOCAL_XY'}:
            vec = self.get_direction_vector(context)
            new_location = iu.calculate_mouse_ray_plane_intersection(
                context, self.mouse_xy, center_location, vec)

        elif self.direction in {'GLOBAL_X', 'GLOBAL_Y', 'GLOBAL_Z',
                                'LOCAL_X', 'LOCAL_Y', 'LOCAL_Z'}:
            vec = self.get_direction_vector(context)
            new_location = iu.calculate_mouse_ray_line_intersection(
                context, self.mouse_xy, center_location, vec)

        elif self.direction in {'LOCAL_EACH_X', 'LOCAL_EACH_Y', 'LOCAL_EACH_Z',
                                'VIEW_CAMERA', 'VIEW_PIVOT',
                                'CURSOR_3D', 'OBJECT_ORIGIN'}:
            unit = iu.calculate_mouse_move_unit(context, center_location)
            vec = Vector((0, 0, mouse_diff.y * unit))
            if self.prev_center_location:
                new_location = self.prev_center_location + vec
            else:
                new_location = view3d_utils.region_2d_to_location_3d(
                    context.region, context.region_data,
                    self.mouse_xy, center_location) + vec

        else:
            raise RuntimeError()

        if self.prev_center_location:
            diff = new_location - self.prev_center_location
        else:
            diff = Vector()

        self.prev_center_location = new_location
        return diff

    ################
    @staticmethod
    def draw_callback_pv(self, context):
        # Set the header text
        move_vector = Vector(self.move_vector)
        if self.number_input.is_processing():
            length = self.number_input.get_display()
        else:
            length = f'{move_vector.length:.4f}'
        move_vector.normalize()
        txt = f'({move_vector.x:.4f}, {move_vector.y:.4f}, {move_vector.z:.4f}) ({length} m)   Direction: {self.direction}'
        if self.m_prop.use_proportional:
            txt += f'   Falloff: {self.m_prop.falloff_type}   Radius: {self.m_prop.influence_radius:.4f} m'
        if self.m_prop.use_block_with_mesh:
            txt += f'   Block({self.m_prop.block_with_mesh_prop.target_mesh_name})'
        if self.m_prop.use_snap_onto_mesh:
            txt += f'   Snap({self.m_prop.snap_onto_mesh_prop.target_mesh_name})'

        context.area.header_text_set(txt)
        context.area.tag_redraw()

        # Define the shader
        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        shader.bind()

        if not self.number_input.is_processing():
            arma = context.active_object
            center_location = self.pm.center_location

            colors = []
            locations = np.empty((0, 3))
            directions = np.empty((0, 3))

            di = pm.DIRECTION_INFO[self.direction]

            if not di.uniform_direction:
                COLOR_TABLE = {
                    'LOCAL_EACH_X': (1, 0, 0, 0.3),
                    'LOCAL_EACH_Y': (0, 1, 0, 0.3),
                    'LOCAL_EACH_Z': (0, 0, 1, 0.3),
                    'VIEW_CAMERA':  (0, 1, 1, 0.3),
                    'VIEW_PIVOT':   (1, 0, 1, 0.3),
                    'CURSOR_3D':    (1, 1, 1, 0.3),
                    'OBJECT_ORIGIN':(1, 1, 0, 0.3),
                }
                locations = self.pm.orig_locations
                directions = self.pm.directions
                colors = np.tile(COLOR_TABLE[self.direction],
                                 (locations.shape[0], 1))

                which_to_move = np.logical_and(self.pm.factors > pm.EPSILON,
                                               self.get_which_to_move(context))
                locations = locations[which_to_move]
                directions = directions[which_to_move]
                colors = colors[which_to_move].tolist()

            if self.direction in {'GLOBAL_X', 'GLOBAL_ZX', 'GLOBAL_XY'}:
                colors.append((1, 0, 0, 0.5))
                locations = np.append(locations, [center_location])
                directions = np.append(directions, [np.array((1, 0, 0))])
                
            if self.direction in {'GLOBAL_Y', 'GLOBAL_XY', 'GLOBAL_YZ'}:
                colors.append((0, 1, 0, 0.5))
                locations = np.append(locations, [center_location])
                directions = np.append(directions, [np.array((0, 1, 0))])
                
            if self.direction in {'GLOBAL_Z', 'GLOBAL_YZ', 'GLOBAL_ZX'}:
                colors.append((0, 0, 1, 0.5))
                locations = np.append(locations, [center_location])
                directions = np.append(directions, [np.array((0, 0, 1))])

            mtx = np.array(arma.matrix_world)

            if self.direction in {'LOCAL_X', 'LOCAL_ZX', 'LOCAL_XY'}:
                colors.append((1, 0, 0, 0.5))
                locations = np.append(locations, [center_location])
                directions = np.append(directions, [mtx[:3, 0]])
                
            if self.direction in {'LOCAL_Y', 'LOCAL_XY', 'LOCAL_YZ'}:
                colors.append((0, 1, 0, 0.5))
                locations = np.append(locations, [center_location])
                directions = np.append(directions, [mtx[:3, 1]])
                
            if self.direction in {'LOCAL_Z', 'LOCAL_YZ', 'LOCAL_ZX'}:
                colors.append((0, 0, 1, 0.5))
                locations = np.append(locations, [center_location])
                directions = np.append(directions, [mtx[:3, 2]])
            
            if colors:
                # (n, 1, 3) の形状にリシェイプ
                locations = np.reshape(locations, (-1, 1, 3))
                directions = np.reshape(directions, (-1, 1, 3))

                unit = max(iu.calculate_mouse_range_at_pivot(context))
                weights = np.linspace(-unit, unit, 10)

                # weights を (1, m, 1) の形状にリシェイプ
                weights = np.reshape(weights, (1, -1, 1))

                # locations[i] + directions[i] * weights の計算
                points = locations + directions * weights  # (n, m, 3) の配列

                with iu.BlenderGpuState(blend='ALPHA', line_width=2.0):
                    for strip, color in zip(points.tolist(), colors):
                        shader.uniform_float('color', color)
                        batch = batch_for_shader(shader,
                                                 'LINE_STRIP',
                                                 {'pos': strip})
                        batch.draw(shader)

            # Draw influence_radius
            if self.m_prop.use_proportional:
                view_matrix = np.array(context.region_data.view_matrix)
                angles = np.linspace(0, 2*np.pi, 60)
                radius = self.m_prop.influence_radius
                circle_verts = np.stack(
                    [radius * np.cos(angles),
                     radius * np.sin(angles),
                     np.zeros_like(angles)], axis=-1)
                inv = np.linalg.inv(view_matrix)
                points = center_location + circle_verts @ inv.T[:3, :3]
                with iu.BlenderGpuState(blend='ALPHA', line_width=4.0):
                    shader.uniform_float('color', (0.1, 0.1, 0.1, 0.8))
                    batch = batch_for_shader(shader, 'LINE_LOOP',
                                             {'pos': points.tolist()})
                    batch.draw(shader)

    ################
    @staticmethod
    def status_text_fn(self, context):
        row = self.layout.row(align=True)

        row.label(text='Confirm', icon='MOUSE_LMB')
        row.label(text='Cancel', icon='MOUSE_RMB')

        row.label(text='X Axis', icon='EVENT_X')
        row.label(text='Y Axis', icon='EVENT_Y')
        row.label(text='Z Axis', icon='EVENT_Z')

        row.label(icon='EVENT_SHIFT')
        row.label(text='X Plane', icon='EVENT_X')

        row.label(icon='EVENT_SHIFT')
        row.label(text='Y Plane', icon='EVENT_Y')

        row.label(icon='EVENT_SHIFT')
        row.label(text='Z Plane', icon='EVENT_Z')

        row.label(text='Cursor / Origin', icon='EVENT_C')
        row.label(text='Pivot / Camera', icon='EVENT_V')

        row.label(icon='MOUSE_MMB')
        row.label(icon='EVENT_W')
        row.label(icon='EVENT_A')
        row.label(icon='EVENT_D', text='Radius')

        row.label(text='Proportional On/Off', icon='EVENT_O')

        row.label(icon='EVENT_SHIFT')
        row.label(text='Falloff type', icon='EVENT_O')

        row.label(icon='EVENT_SHIFT')
        row.label(text='Snap On/Off', icon='EVENT_S')

        row.label(icon='EVENT_SHIFT')
        row.label(text='Block On/Off', icon='EVENT_B')

        row.label(text='Precision Mode', icon='EVENT_SHIFT')

        row.label(text='Move', icon='EVENT_G')
        row.label(text='Rotate', icon='EVENT_R')
        row.label(text='Resize', icon='EVENT_S')

    ################
    def reset_movement(self, context):
        self.pm.reset_movement()
        self.set_directions(context)
        self.mouse_xy = view3d_utils.location_3d_to_region_2d(
            context.region, context.region_data, self.pm.center_location)
        self.prev_center_location = None
        self.move_vector = Vector()

    ################
    def set_directions(self, context):
        di = pm.DIRECTION_INFO[self.direction]
        if di.uniform_direction:
            self.pm.directions = np.array(self.move_vector)[np.newaxis]

        elif not di.global_direction:
            armature = context.active_object
            self.pm.set_directions_local(self.direction, armature)

        elif self.direction == 'VIEW_CAMERA':
            self.pm.set_directions_from_view_camera()

        elif self.direction == 'VIEW_PIVOT':
            self.pm.set_directions_from_view_pivot()

        elif self.direction == 'CURSOR_3D':
            self.pm.set_directions_from_cursor_3d(context)

        elif self.direction == 'OBJECT_ORIGIN':
            armature = context.active_object
            self.pm.set_directions_from_object_origin(armature)

        else:
            raise RuntimeError()

    ################
    def update_directions(self):
        di = pm.DIRECTION_INFO[self.direction]
        if di.uniform_direction:
            self.pm.directions = np.array(self.move_vector)[np.newaxis]

    ################
    def set_cursor(self, context):
        di = pm.DIRECTION_INFO[self.direction]
        if di.uniform_direction:
            context.window.cursor_modal_set('CROSS')
        else:
            context.window.cursor_modal_set('MOVE_Y')

    ################
    def get_which_to_move(self, context):
        armature = context.active_object
        visible_bones = np.array([bt.is_bone_visible(b.bone, armature.data)
                                  for b in armature.pose.bones], dtype=bool)
        if self.m_prop.use_proportional:
           which_to_move = visible_bones
        else:
            selected_bones = np.array(
                [b.bone.select for b in armature.pose.bones], dtype=bool)
            which_to_move = np.logical_and(visible_bones, selected_bones)
        return which_to_move

    ################
    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, 'View3D not found, cannot run operator')
            return {'CANCELLED'}

        armature = context.active_object
        if not armature or armature.type != 'ARMATURE':
            self.report({'WARNING'}, 'Armature is not active.')
            return {'CANCELLED'}

        # Get if bone is selected
        is_selected_bones = np.array(
            [b.bone.select and bt.is_bone_visible(b.bone, armature.data)
             for b in armature.pose.bones], dtype=bool)
        if not np.any(is_selected_bones):
            self.report({'WARNING'}, 'No bones selected')
            return {'CANCELLED'}

        # Start a new Undo step
        bpy.ops.ed.undo_push(message='Proportional Pose Editing')
        
        # Setup
        prop = context.scene.dddtools_bt_prop
        self.m_prop.copy_from(prop.poseProportionalMoveProp)
        self.direction = 'NONE'
        self.number_input.set_expression('')
        self.save_move_vector = None

        # Set mouse cursor
        self.set_cursor(context)

        # Save translations
        self.bone_translations = np.array([
            np.array(bone.matrix.translation)
            for bone in armature.pose.bones
        ])

        # Compute current locations in world coordinate
        bone_translations_homo = \
            mu.append_homogeneous_coordinate(self.bone_translations)
        locations =\
            (bone_translations_homo @ np.array(armature.matrix_world).T)[:, :3]
        
        # setup ProportionalMover
        mesh = iu.findfirst_selected_object('MESH')
        if mesh:
            self.m_prop.block_with_mesh_prop.target_mesh_name = mesh.name
            self.m_prop.snap_onto_mesh_prop.target_mesh_name = mesh.name
        self.pm.setup(context.space_data, locations, is_selected_bones)
        self.reset_movement(context)

        # Register the drawing callback
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback_pv, args, 'WINDOW', 'POST_VIEW'
        )

        self.prev_show_menus = context.area.show_menus

        context.workspace.status_text_set(self.status_text_fn)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    ################
    @classmethod
    def poll(self, context):
        return bt.get_selected_bone_names() and bpy.context.mode == 'POSE'

    ################
    def execute(self, context):
        prop = context.scene.dddtools_bt_prop
        prop.poseProportionalMoveProp.copy_from(self.m_prop)

        self.pm.influence_radius = self.m_prop.influence_radius
        self.pm.falloff_type = self.m_prop.falloff_type
        self.update_directions()

        self.pm.modifiers = []
        if self.m_prop.use_block_with_mesh:
            mod = pm.MeshBlockModifier(self.m_prop.block_with_mesh_prop)
            self.pm.modifiers.append(mod)

        if self.m_prop.use_snap_onto_mesh:
            mod = pm.MeshSnapModifier(self.m_prop.snap_onto_mesh_prop)
            self.pm.modifiers.append(mod)

        move_vector = Vector(self.move_vector)
        di = pm.DIRECTION_INFO[self.direction]
        if di.uniform_direction:
            amount = move_vector.length
        else:
            amount = move_vector.z

        # Compute locations
        which_to_move = self.get_which_to_move(context)
        locations, which_to_move = self.pm.compute_move(amount, which_to_move)

        # Compute local translations
        armature = context.active_object
        locations_homo = mu.append_homogeneous_coordinate(locations)
        translations = \
            (locations_homo @ np.array(armature.matrix_world.inverted()).T)[:, :3]

        translations = np.where(which_to_move[:, np.newaxis],
                                translations,
                                self.bone_translations)

        # Mirror copy
        if context.object.pose.use_mirror_x:
            translations, mirror_bones = bt.pose_mirror_x_translations(
                armature,
                translations,
                which_to_move)
            which_to_move |= mirror_bones

        # Set translation
        bt.set_translations(armature, translations, which_to_move)

        armature.pose.bones.update()
        return {'FINISHED'}

    ################
    def cancel(self, context):
        bpy.ops.ed.undo()
        self.finish(context)
        return {'CANCELLED'}

    ################
    def finish(self, context):
        if context.area:
            context.area.header_text_set(None)
            context.area.show_menus = self.prev_show_menus
            context.area.tag_redraw()

        assert self._handle
        bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        self._handle = None
        context.window.cursor_modal_restore()
        context.workspace.status_text_set(None)

    ################
    def modal(self, context, event):
        context.area.tag_redraw()

        ####
        # Process NumberInput and confirm/cancel

        if self.number_input.process_event(event):
            if self.save_move_vector is None:
                self.save_move_vector = Vector(self.move_vector)
            try:
                amount = self.number_input.get_value()
                norm = self.save_move_vector.length
                if norm < 1e-8:
                    move_vector = self.get_direction_unit(context) * amount
                else:
                    move_vector = self.save_move_vector * amount / norm
                self.move_vector = move_vector
            except:
                if not self.number_input.is_processing():
                    self.move_vector = self.save_move_vector

            self.execute(context)
            return {'RUNNING_MODAL'}

        elif event.type in {'LEFTMOUSE', 'SPACE', 'RET', 'NUMPAD_ENTER'}:
            self.finish(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            return self.cancel(context)

        elif self.number_input.is_processing():
            return {'RUNNING_MODAL'}

        self.save_move_vector = None

        pressed = not event.is_repeat and event.value == 'PRESS'

        ####
        # Process menus/tools

        if event.type == 'O' and event.shift and pressed:
            bpy.ops.wm.call_menu_pie(name='DDDBT_MT_Falloff')
            return {'RUNNING_MODAL'}

        elif event.type == 'G' and not event.shift and pressed:
            self.cancel(context)
            bpy.ops.transform.translate('INVOKE_DEFAULT')
            return {'CANCELLED'}

        elif event.type == 'R' and not event.shift and pressed:
            self.cancel(context)
            bpy.ops.transform.rotate('INVOKE_DEFAULT')
            return {'CANCELLED'}

        elif event.type == 'S' and not event.shift and pressed:
            self.cancel(context)
            bpy.ops.transform.resize('INVOKE_DEFAULT')
            return {'CANCELLED'}

        ####
        # Process others

        prop = context.scene.dddtools_bt_prop
        falloff_type = prop.poseProportionalMoveProp.falloff_type
        if self.m_prop.falloff_type != falloff_type:
            self.m_prop.falloff_type = falloff_type
            update = True
        else:
            update = False

        if event.type == 'MOUSEMOVE':
            update = True

        elif event.type in {'WHEELDOWNMOUSE', 'PAGE_UP', 'D'} and event.value == 'PRESS':
            self.m_prop.influence_radius *= 1.1
            update = True

        elif event.type in {'WHEELUPMOUSE', 'PAGE_DOWN', 'A'} and event.value == 'PRESS':
            self.m_prop.influence_radius /= 1.1
            update = True

        elif event.type in {'MIDDLEMOUSE', 'W'} and pressed:
            range = iu.calculate_mouse_range_at_pivot(context)
            self.m_prop.influence_radius = min(range) * .3
            update=True

        elif event.type in {'X', 'Y', 'Z', 'V', 'C'} and pressed:
            self.direction = pm.get_next_direction(self.direction, event.ascii)
            self.set_cursor(context)
            self.reset_movement(context)
            update = True

        elif event.type == 'O' and not event.shift and pressed:
            self.m_prop.use_proportional ^= True
            update = True

        elif event.type == 'S' and event.shift and pressed:
            self.m_prop.use_snap_onto_mesh ^= True
            update = True

        elif event.type == 'B' and event.shift and pressed:
            self.m_prop.use_block_with_mesh ^= True
            update = True

        if update:
            mouse_diff = Vector((event.mouse_x - event.mouse_prev_x,
                                 event.mouse_y - event.mouse_prev_y))

            # Compute mouse movement and get move vector
            vec = self.compute_mouse_move(context, mouse_diff)
            if event.shift: vec *= 0.1
            self.move_vector = Vector(self.move_vector) + vec

            self.execute(context)

        return {'RUNNING_MODAL'}

    def draw(self, context):
        mesh = iu.findfirst_selected_object('MESH')
        col = self.layout.column(align=False)
        self.m_prop.draw(context, col)
        col.prop(self, 'move_vector')

################
# パイメニューの項目を選択するためのオペレーター
class DDDBT_OT_Falloff(Operator):
    bl_idname = "scene.dddbt_select_falloff"
    bl_label = "Select Falloff"
    bl_options = {'INTERNAL'}
    falloff_type: StringProperty()

    def execute(self, context):
        prop = context.scene.dddtools_bt_prop
        prop.poseProportionalMoveProp.falloff_type = self.falloff_type
        return {'FINISHED'}

################
class DDDBT_MT_Falloff(Menu):
    bl_label = "Select Falloff Type"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        falloff_items = mu.get_falloff_enum().keywords['items']
        for falloff_item in falloff_items:
            op = pie.operator(DDDBT_OT_Falloff.bl_idname,
                              text=falloff_item[1],
                              icon=falloff_item[3])
            op.falloff_type = falloff_item[0]

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
        col.operator(DDDBT_OT_renameBonesForSymmetry.bl_idname)

        col.separator()

        col.operator(DDDBT_OT_resetStretchTo.bl_idname)

        display, split = ui.splitSwitch(col, prop, 'display_changeBoneLengthDirection')
        split.operator(DDDBT_OT_changeBoneLengthDirection.bl_idname)
        if display:
            box = col.box()
            prop.changeBoneLengthDirectionProp.draw(box)

        display, split = ui.splitSwitch(col, prop, 'display_adjustBendyBoneSize')
        split.operator(DDDBT_OT_adjustBendyBoneSize.bl_idname)
        if display:
            box = col.box()
            prop.adjustBendyBoneSizeProp.draw(box)

        col.operator(DDDBT_OT_applyArmatureToRestPose.bl_idname)

        display, split = ui.splitSwitch(col, prop, 'display_poseProportionalMove')
        split.operator(DDDBT_OT_poseProportionalMove.bl_idname)
        if display:
            box = col.box()
            prop.poseProportionalMoveProp.draw(context, box)

        col.separator()

        display, split = ui.splitSwitch(col, prop, 'display_createBonesFromSelectedEdges')
        split.operator(DDDBT_OT_createBonesFromSelectedEdges.bl_idname)
        if display:
            box = col.box().column()
            prop.createBonesFromSelectedEdgesProp.draw(box)
    
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

        col.separator()

        display, split = ui.splitSwitch(col, prop, 'display_createEncasedSkin')
        split.operator(DDDBT_OT_createEncasedSkin.bl_idname)
        if display:
            box = col.box()
            prop.createEncasedSkinProp.draw(box)

        col.operator(DDDBT_OT_createMeshFromSelectedBones.bl_idname)

################
def draw_pose_menu(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(DDDBT_OT_poseProportionalMove.bl_idname)

################################################################
classes = (
    DDDBT_createBonesFromSelectedEdges_propertyGroup,
    DDDBT_createEncasedSkin_propertyGroup,
    DDDBT_buildHandleFromVertices_propertyGroup,
    DDDBT_buildHandleFromBones_propertyGroup,
    DDDBT_changeBoneLengthDirection_propertyGroup,
    DDDBT_adjustBendyBoneSize_propertyGroup,
    DDDBT_poseProportionalMove_propertyGroup,
    DDDBT_propertyGroup,
    DDDBT_OT_renameChildBonesWithNumber,
    DDDBT_OT_renameBonesForSymmetry,
    DDDBT_OT_resetStretchTo,
    DDDBT_OT_applyArmatureToRestPose,
    DDDBT_OT_createBonesFromSelectedEdges,
    DDDBT_OT_createMeshFromSelectedBones,
    DDDBT_OT_selectAncestralBones,
    DDDBT_OT_printSelectedBoneNamess,
    DDDBT_OT_createEncasedSkin,
    DDDBT_OT_buildHandleFromVertices,
    DDDBT_OT_buildHandleFromBones,
    DDDBT_OT_changeBoneLengthDirection,
    DDDBT_OT_adjustBendyBoneSize,
    DDDBT_OT_poseProportionalMove,
    DDDBT_OT_Falloff,
    DDDBT_MT_Falloff,
    DDDBT_PT_BoneTool,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dddtools_bt_prop = PointerProperty(type=DDDBT_propertyGroup)
    bpy.types.VIEW3D_MT_pose_context_menu.append(draw_pose_menu)

def unregisterClass():
    bpy.types.VIEW3D_MT_pose_context_menu.remove(draw_pose_menu)
    del bpy.types.Scene.dddtools_bt_prop
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()

