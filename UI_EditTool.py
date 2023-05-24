# -*- encoding:utf-8 -*-

import bpy
import bmesh
from bpy.props import BoolProperty, FloatProperty, IntProperty
from bpy.types import Panel, Operator

import math
from random import Random
from mathutils import Vector, Matrix
import traceback
import numpy as np
from . import internalUtils as iu
from . import mathUtils as mu
from . import SelectTool as st

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################################################################
class DDDET_OT_selectDividingLoops(Operator):
    bl_idname = 'dddet.select_dividing_loops'
    bl_label = _('Select Dividing Loops')
    bl_description = _('Select the dividing loops of the active mesh.')
    bl_options = {'REGISTER', 'UNDO'}

    excludeSeam: BoolProperty(
        name=_('Seam'),
        description=_('Seams will no longer be selected.'),
        default=True,
    )

    excludeSharp: BoolProperty(
        name=_('Sharp'),
        description=_('Sharps will no longer be selected.'),
        default=True,
    )

    excludeBevelWeight: BoolProperty(
        name=_('Bevel Weight'),
        description=_('Whether to refer to bevel weights.'),
        default=False,
    )
    bevelWeight: FloatProperty(
        name=_('Bevel Weight'),
        description=_('If the bevel weights of the edges are higher than this, they are not selected.'),
        default=1.0,
        min=0.0,
        max=1.0,
        precision=2,
        step=10,
        subtype = 'FACTOR',
    )

    excludeCrease: BoolProperty(
        name=_('Crease'),
        description=_('Whether to refer to crease.'),
        default=True,
    )
    crease: FloatProperty(
        name=_('Crease'),
        description=_('If the crease of the edges are higher than this, they are not selected.'),
        default=1.0,
        min=0.0,
        max=1.0,
        precision=2,
        step=10,
        subtype = 'FACTOR',
    )

    excludeFaceAngle: BoolProperty(
        name=_('Face Angle'),
        description=_('Whether to exclude sharp-edged surfaces.'),
        default=False,
    )
    faceAngle: FloatProperty(
        name=_('Face Angle'),
        description=_('No edge with a face angle larger than this will be selected.'),
        default=math.radians(30),
        min=0.0,
        max=math.pi,
        precision=2,
        step=5,
        subtype = 'ANGLE',
    )

    randomSeed: IntProperty(
        name = 'Random Seed',
        description = _('Random number seeds for selection.'),
        default=0,
        min=0
    )

    ratio: FloatProperty(
        name=_('Selection Rate'),
        description=_('The rate at which the dividing line is selected.'),
        default=1.0,
        min=0.0,
        max=1.0,
        precision=2,
        step=5,
        subtype = 'FACTOR',
    )

    mirrorX: BoolProperty(
        name='X',
        description=_('After loop determination, perform additional mirror selection in X direction.'),
        default=False,
    )
    mirrorY: BoolProperty(
        name='Y',
        description=_('After loop determination, perform additional mirror selection in Y direction.'),
        default=False,
    )
    mirrorZ: BoolProperty(
        name='Z',
        description=_('After loop determination, perform additional mirror selection in Z direction.'),
        default=False,
    )

    dissolve: BoolProperty(
        name=_('Dissolve Edge'),
        description=_('After selection, the edges are automatically dissolved.'),
        default=False,
    )

    lastSelected: 0.0
    lastFound: 0.0

    @classmethod
    def poll(self, context):
        mesh = bpy.context.active_object
        return mesh and mesh.type == 'MESH'

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text=iface_('Exclude'))
        column = box.column()
        row = column.row()
        row.prop(self, 'excludeSeam')
        row.prop(self, 'excludeSharp')

        column.separator()

        split = column.split(factor=0, align=True)
        split.prop(self, 'excludeCrease')
        row = split.row()
        row.enabled = self.excludeCrease
        row.prop(self, 'crease', text='')

        split = column.split(factor=0, align=True)
        split.prop(self, 'excludeBevelWeight')
        row = split.row()
        row.enabled = self.excludeBevelWeight
        row.prop(self, 'bevelWeight', text='')

        split = column.split(factor=0, align=True)
        split.prop(self, 'excludeFaceAngle')
        row = split.row()
        row.enabled = self.excludeFaceAngle
        row.prop(self, 'faceAngle', text='', slider=True)

        layout.separator()

        box = layout.box()
        box.label(text=iface_('Selection'))
        column = box.column()
        column.prop(self, 'randomSeed')
        column.prop(self, 'ratio')
        row = column.row()
        row.label(text=iface_('{self_lastSelected} / {self_lastFound} dividing loops are selected.').format(self_lastSelected=self.lastSelected, self_lastFound=self.lastFound), icon='INFO')

        layout.separator()

        box = layout.box()
        box.label(text=iface_('Auto-Execution'))
        column = box.column()
        split = column.split(factor=0, align=True)
        split.label(text=iface_('Mirror Select'))
        row = split.row()
        row.prop(self, 'mirrorX')
        row.prop(self, 'mirrorY')
        row.prop(self, 'mirrorZ')
        column.prop(self, 'dissolve')

    def execute(self, context):
        rng = Random(self.randomSeed)
        def choose(index, loop, selected, found):
            toBeSelected = int(found * self.ratio + 0.5) - selected
            rest = found - index
            #print(f'index:{index} s/f:{selected}/{found} t/r:{toBeSelected}/{rest}')
            if rest <= 0 or toBeSelected <= 0:
                return False
            elif toBeSelected >= rest:
                return True
            else:
                rr = toBeSelected / rest
                #print(f'rr:{rr}')
                return rng.random() < rr
        
        mesh = bpy.context.active_object
        faceAngle = self.faceAngle if self.excludeFaceAngle else math.tau
        bevelWeight = self.bevelWeight if self.excludeBevelWeight else 1.1
        crease = self.crease if self.excludeCrease else 1.1
        finder = st.DividingLoopFinder(exclude_face_angle=faceAngle,
                                       exclude_seam=self.excludeSeam,
                                       exclude_sharp=self.excludeSharp,
                                       exclude_bevel_weight=bevelWeight,
                                       exclude_crease=crease)
                                       
                                       
        ans = finder.selectDividingLoops(mesh, choose=choose)
        if ans:
            self.lastSelected = ans.selected
            self.lastFound = ans.found
            if self.mirrorX or self.mirrorY or self.mirrorZ:
                axis = set()
                if self.mirrorX: axis.add('X')
                if self.mirrorY: axis.add('Y')
                if self.mirrorZ: axis.add('Z')
                bpy.ops.mesh.select_mirror(axis=axis, extend=True)

            if self.dissolve:
                bpy.ops.mesh.dissolve_edges()
                bpy.ops.mesh.reveal()
                bpy.ops.mesh.hide(unselected=False)

            return {'FINISHED'}
        else:
            return {'CANCELLED'}

################################################################
def calcCenterOfSphereFromSelectedVertices():
    """
    Returns the radius and center of the sphere that approximates the selected vertices.
    
    """

    mesh = bpy.context.active_object
    if not mesh or mesh.type != 'MESH':
        return None

    bme = bmesh.from_edit_mesh(bpy.context.active_object.data)
    mtx = bpy.context.active_object.matrix_world
    verts = [mtx @ vtx.co for vtx in bme.verts if vtx.select]
    #print(verts)
    
    try:
        if len(verts) < 4:
            raise ValueError(iface_('Please select 4 or more vertices. Currently {len_verts} vertices are selected.').format(len_verts=len(verts)))
        elif len(verts) == 4:
            result = mu.calcCircumcenter(np.array(verts))
        else:
            result = mu.calcFit(np.array(verts))
    except Exception as e:
        traceback.print_exc()
        result = None

    return result
    
class DDDET_OT_addApproximateSphere(Operator):
    bl_idname = 'dddet.add_approximate_sphere'
    bl_label = _('Add Approximate Sphere')
    bl_description = _('Adds a sphere approximating the selected vertices.')
    bl_options = {'REGISTER', 'UNDO'}

    segments: IntProperty(
        name=_('Segments'),
        description=_('Specifies the number of sphere segments to be added.'),
        min=3,
        max=500,
        default=32,
    )

    ring_count: IntProperty(
        name=_('Rings'),
        description=_('Specifies the number of sphere rings to be added.'),
        min=3,
        max=500,
        default=16,
    )

    @classmethod
    def poll(self, context):
        mesh = bpy.context.active_object
        return mesh and mesh.type=='MESH' and mesh.mode=='EDIT'

    def execute(self, context):
        if self.sphere:
            mesh = iu.ObjectWrapper(bpy.context.active_object)
            modeChanger = iu.ModeChanger(mesh.obj, 'OBJECT')
            bpy.ops.mesh.primitive_uv_sphere_add(enter_editmode=False,
                                                 align='WORLD',
                                                 segments=self.segments,
                                                 ring_count=self.ring_count,
                                                 radius=self.sphere[0],
                                                 location=self.sphere[1],
                                                 scale=(1, 1, 1))
            del modeChanger
            bpy.context.view_layer.objects.active = mesh.obj
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        iface_('Could not add sphere. See log for details.'))
            return {'CANCELLED'}

    def invoke(self, context, event):
        self.sphere = calcCenterOfSphereFromSelectedVertices()
        return self.execute(context)

################################################################
class DDDET_OT_addApproximateEmpty(Operator):
    bl_idname = 'dddet.add_approximate_empty'
    bl_label = _('Add Empty Sphere')
    bl_description = _('Adds an EMPTY sphere that approximates the selected vertices.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        mesh = bpy.context.active_object
        return mesh and mesh.type=='MESH' and mesh.mode=='EDIT'

    def execute(self, context):
        sphere = calcCenterOfSphereFromSelectedVertices()
        if sphere:
            mesh = iu.ObjectWrapper(bpy.context.active_object)
            empty_obj = bpy.data.objects.new(f'EmptySphere_{mesh.name}', None)
            empty_obj.empty_display_type = 'SPHERE'
            empty_obj.empty_display_size = sphere[0]
            empty_obj.location = sphere[1]
            context.scene.collection.objects.link(empty_obj)
            return {'FINISHED'}
        else:
            self.report({'WARNING'},
                        iface_('Empty sphere could not be added. See log for details.'))
            return {'CANCELLED'}

################################################################
class DDDET_OT_convertEmptyAndSphere(Operator):
    bl_idname = 'dddet.convert_empty_and_sphere'
    bl_label = _('Inter-Convert Mesh and Empty')
    bl_description = _('Converts the selected object to an empty sphere if it is a mesh, or to a mesh if it is an empty sphere.')
    bl_options = {'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects

    def execute(self, context):
        emptyObjects = []
        sphereObjects = []
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                empty = iu.convertSphereToEmpty(obj)
                if empty:
                    emptyObjects.append(empty)
            elif obj.type == 'EMPTY' and obj.empty_display_type == 'SPHERE':
                sphere = iu.convertEmptyToSphere(obj)
                if sphere:
                    sphereObjects.append(sphere)
        if sphereObjects or emptyObjects:
            self.report({'INFO'},
                        iface_('Converted {len_sphereObjects} empties and {len_emptyObjects} meshes: {sphereObjects} {emptyObjects}.').format(
                            len_sphereObjects=len(sphereObjects),
                            len_emptyObjects=len(emptyObjects),
                            sphereObjects=str(sphereObjects),
                            emptyObjects=str(emptyObjects)))
            for obj in sphereObjects + emptyObjects:
                obj.select_set(True)
            return {'FINISHED'}
        else:
            self.report({'INFO'},
                        iface_('No objects were found that could be converted.'))
            return {'CANCELLED'}

################################################################
class DDDET_PT_main(Panel):
    bl_idname = 'DDDET_PT_main'
    bl_label = 'EditTool'
    bl_category = 'DDDTools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator(DDDET_OT_selectDividingLoops.bl_idname)
        col.operator(DDDET_OT_addApproximateSphere.bl_idname)
        col.operator(DDDET_OT_addApproximateEmpty.bl_idname)
        col.operator(DDDET_OT_convertEmptyAndSphere.bl_idname)

################################################################
def menu_fn(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(DDDET_OT_selectDividingLoops.bl_idname)

################################################################
classes = (
    DDDET_OT_selectDividingLoops,
    DDDET_OT_addApproximateSphere,
    DDDET_OT_addApproximateEmpty,
    DDDET_OT_convertEmptyAndSphere,
    DDDET_PT_main,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_select_edit_mesh.append(menu_fn)

def unregisterClass():
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(menu_fn)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
