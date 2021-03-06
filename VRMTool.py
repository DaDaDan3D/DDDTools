import sys
import re
import json
from collections import OrderedDict
import bpy, bmesh
import math
from mathutils.bvhtree import BVHTree
from mathutils import (
    Vector,
    Matrix,
)
import statistics
from . import internalUtils as iu
from . import WeightTool as wt

################################################################
def textblock2str(textblock):
    return "".join([line.body for line in textblock.lines])

################
def getAddon(version=(2, 3, 26)):
    """
    Get add-on if specified version or later of VRM_Addon_for_Blender are installed.

    Parameters
    ----------------
    version : tuple
    """

    va = sys.modules.get('VRM_Addon_for_Blender-release')
    if va and va.bl_info['version'] >= version:
        return va
    else:
        return None

################
# from Blender/2.83/scripts/add_curve_ivygen.py
def bvhtree_from_object(ob):
    import bmesh
    bm = bmesh.new()

    depsgraph = bpy.context.evaluated_depsgraph_get()
    ob_eval = ob.evaluated_get(depsgraph)
    mesh = ob_eval.to_mesh()
    bm.from_mesh(mesh)
    bm.transform(ob.matrix_world)

    bvhtree = BVHTree.FromBMesh(bm)
    ob_eval.to_mesh_clear()
    return bvhtree

################
def getColliderSizeBVH(bvhtree, matrixWorld, radius, insideToOutside, numberOfRays):
    result = []
    theta = math.pi * 2 / numberOfRays
    center = matrixWorld.translation
    for idx in range(numberOfRays):
        th = theta * idx
        direction = matrixWorld.to_3x3() @ Vector([math.cos(th) * radius, 0.0, math.sin(th) * radius])
        if insideToOutside:
            pos = center
        else:
            pos = center + direction
            direction.negate()
        hit_location, *_ = bvhtree.ray_cast(pos, direction, radius)
        if hit_location:
            length = (hit_location - center).length
            result.append(length)
    return result

################
def getSelectedEditableBones():
    return [iu.EditBoneWrapper(eb) for eb in bpy.context.selected_editable_bones]

################
def addCollider(meshObj,
                armaObj,
                numberOfColliders=4,
                numberOfRays=8,
                radius=0.3,
                insideToOutside=True,
                fitMode='STDEV',
                offset=0.0,
                scale=1.0):
    """
    Adds a collision sphere to the selected bone for the selected mesh.
    You should select one mesh and one armature.

    Parameters
    ----------------
    meshObj : mesh object
      Mesh to determine the size of the collider.

    armaObj : armature object
      Armature to which the collider is added.

    numberOfColliders : number
      Number of colliders to be added.

    numberOfRays : number
      Number of rays emitted from the circle.

    radius : number
      The radius of the circle that emits rays.

    insideToOutside : bool
      If true, emits rays from the center of the circle outward.
      If false, emits rays from the edge of the circle towards the center.

    fitMode : string
      Specify the criteria for selecting the size of the collision ball.
      'MIN', 'MAX', 'MEAN', 'HARMONIC_MEAN', 'MEDIAN', 'STDEV'

    offset : number
      The amount of offset to adjust the size of all colliders.

    scale : number
      The scale to adjust the size of all colliders.
    
    """

    #print('----------------')
    mesh = iu.ObjectWrapper(meshObj)
    arma = iu.ObjectWrapper(armaObj)
    if not mesh or not arma:
        return {'CANCELLED'}, "Please select Armature and Mesh"
    #print('mesh:', mesh.name, 'arma:', arma.name)

    if fitMode == 'MIN':
        fitFunc = min
    elif fitMode == 'MAX':
        fitFunc = max
    elif fitMode == 'MEAN':
        fitFunc = statistics.mean
    elif fitMode == 'HARMONIC_MEAN':
        fitFunc = statistics.harmonic_mean
    elif fitMode == 'MEDIAN':
        fitFunc = statistics.median
    elif fitMode == 'STDEV':
        fitFunc = statistics.stdev
    else:
        return {'CANCELLED'}, f'Unknown fitMode{fitMode}'

    bvhtree = bvhtree_from_object(mesh.obj)

    modeChanger = iu.ModeChanger(arma.obj, 'EDIT')
    selection = getSelectedEditableBones()
    #print(selection)

    params = []

    for bone in selection:
        direction = bone.obj.head - bone.obj.tail
        length = direction.length
        direction.normalize()
        for idx in range(numberOfColliders):
            ypos = length * idx / numberOfColliders
            matrix = bone.obj.matrix
            matrix.translation = bone.obj.tail + direction * ypos
            ans = getColliderSizeBVH(bvhtree, matrix, radius, insideToOutside, numberOfRays)
            if not ans:
                size = radius
            else:
                size = fitFunc(ans)
            size = min(max(0.002, size * scale + offset), 3.0)
            param = {'bone':bone, 'ypos':ypos, 'size':size, 'index':idx}
            params.append(param)

    del modeChanger


    #print(params)
    modeChanger = iu.ModeChanger(arma.obj, 'OBJECT')
    for param in params:
        bone = param['bone']
        ypos = param['ypos']
        size = param['size']
        index = param['index']

        # Add Empty
        empty_obj = bpy.data.objects.new('Collider_{0}_{1}'.format(bone.name, index), None)
        bpy.context.scene.collection.objects.link(empty_obj)

        # Parent to bone
        empty_obj.parent = arma.obj
        empty_obj.parent_type = "BONE"
        empty_obj.parent_bone = bone.name

        # Move to ypos
        empty_obj.location = Vector([0.0, -ypos, 0.0])
        
        # Set parameters
        empty_obj.empty_display_type = 'SPHERE'
        empty_obj.empty_display_size = size
        
    del modeChanger

    return{'FINISHED'}
    
################################################################
def mergeMeshes(arma, bs_dic, triangulate=True):
    """
    Based on the json, merge and triangulate the mesh.

    Parameters
    ----------------
    arma : ObjectWrapper
      Armature to export

    bs_dic : dict
      Dictionary of blendshape_group.json

    triangulate : Boolean
      Whether to triangulate meshes
    """

    # A dictionary to get a set of actions from mesh names.
    meshToActions = dict()

    # read json and build meshToActions
    for od in bs_dic:
        binds = od.get('binds')
        if binds:
            for bind in binds:
                mesh = bind.get('mesh')
                index = bind.get('index')
                if mesh and index:
                    actions = meshToActions.get(mesh) or set()
                    actions.add(index)
                    meshToActions[mesh] = actions
                else:
                    print(f'Illegal binds in blendshape.json. mesh:{mesh} index:{index}')
    #print(meshToActions)

    # For every child meshes, apply modifiers, set origin to (0,0,0),
    # ensure custom normals, and truangulate.
    cursor_location_save = bpy.context.scene.cursor.location
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.context.view_layer.objects.active = arma.obj
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in iu.getAllChildren(arma.obj, ['MESH', 'CURVE'], selectable=True):
        bpy.context.view_layer.objects.active = obj.obj
        obj.select_set(True)
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='BOUNDS')
        bpy.ops.mesh.customdata_custom_splitnormals_add()
        obj.obj.data.use_auto_smooth = True
        if triangulate:
            bm = bmesh.new()
            bm.from_mesh(obj.obj.data)
            bmesh.ops.triangulate(bm, faces=bm.faces,
                                  quad_method='BEAUTY', ngon_method='BEAUTY')
            bm.to_mesh(obj.obj.data)
            bm.free()
    bpy.context.scene.cursor.location = cursor_location_save

    # clear pose
    bpy.context.view_layer.objects.active = arma.obj
    modeChanger = iu.ModeChanger(arma.obj, 'POSE')
    for bone in arma.obj.data.bones:
        bone.hide = False
        bone.select = True
    # for stretch bones, call twice
    bpy.ops.pose.transforms_clear()
    bpy.ops.pose.transforms_clear()
    del modeChanger

    result = dict()

    # Merge the meshes contained in the collection.
    for mn in meshToActions.keys():
        if mn in bpy.data.objects:
            #print(f'{mn} is already a mesh')
            continue

        collection = bpy.data.collections.get(mn)
        if not collection:
            print(f'Warning! Cannot find {mn} in bpy.data.collections')
            continue

        bpy.ops.object.select_all(action='DESELECT')
        target = None
        for obj in collection.all_objects:
            if obj.type == 'MESH':
                obj.select_set(True)
                target = obj
        if target:
            bpy.context.view_layer.objects.active = target
            bpy.ops.object.join()
            bpy.ops.object.modifier_add(type='ARMATURE')
            bpy.context.object.modifiers[-1].object = arma.obj
            target.name = mn
            result[mn] = iu.ObjectWrapper(mn)
    
    # Merge rest of meshes.
    bpy.ops.object.select_all(action='DESELECT')
    target = None
    for obj in iu.getAllChildMeshes(arma.obj):
        if obj.name not in meshToActions:
            obj.select_set(True)
            target = obj.obj
    if target:
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.join()
        bpy.ops.object.modifier_add(type='ARMATURE')
        bpy.context.object.modifiers[-1].object = arma.obj
        result[None] = iu.ObjectWrapper(target.name)

    # bake pose
    anim = arma.obj.animation_data_create()
    for mn, actions in meshToActions.items():
        #print(f'mesh: {mn}')
        mesh = result[mn]
        for an in sorted(actions):
            #print(f'action: {an}')
            action = bpy.data.actions.get(an)
            if not action:
                #print('Warning! Cannot find action {an}')
                continue

            bpy.context.view_layer.objects.active = mesh.obj

            # for stretch bones, call twice
            anim.action = action
            anim.action = action
            
            # At this point, mesh has only a 'Armature' modifier
            mod = mesh.obj.modifiers[-1]
            modName = mod.name  # save
            mod.name = an       # set to action's name
            bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=an)
            mod.name = modName  # restore
            
            # Be sure to reset pose
            anim.action=None
            bpy.context.view_layer.objects.active = arma.obj
            modeChanger = iu.ModeChanger(arma.obj, 'POSE')
            # for stretch bones, call twice
            bpy.ops.pose.transforms_clear()
            bpy.ops.pose.transforms_clear()
            del modeChanger

    return result

################################################################
def deleteBones(arma, boneGroupName):
    """
    Deletes all bones which belongs to bone_groups[boneGroupName].
    """

    #print('---------------- deleteBones')

    # listup all bones to be deleted
    bpy.context.view_layer.objects.active = arma.obj
    modeChanger = iu.ModeChanger(arma.obj, 'POSE')
    bones = []
    for bone in arma.obj.pose.bones:
        if bone.bone_group and bone.bone_group.name == boneGroupName:
            bones.append(bone.name)
    del modeChanger

    wt.dissolveWeightedBones(arma, bones)

################################################################
def prepareToExportVRM(skeleton='skeleton',
                       triangulate=False,
                       bs_json=None,
                       notExport='NotExport',
                       neutral='Neutral'):
    """
    Prepares to export.
    
    Parameters
    ----------------
    skeleton : String
        Name of skeleton to export
    bs_json : String
        Name of textblock of blendshape_group.json
    notExport : String
        Name of bone_group
    neutral : String
        Name of shapekey of basic face expression

    """

    arma = iu.ObjectWrapper(skeleton)
    bs_dic = json.loads(textblock2str(bpy.data.texts[bs_json]),object_pairs_hook=OrderedDict)
    mergedObjs = mergeMeshes(arma, bs_dic, triangulate=triangulate)

    #print('---------------- mergedObjs:')
    #print(mergedObjs)

    deleteBones(arma, notExport)

    for pose, obj in mergedObjs.items():
        if pose:
            # FIXME
            #  not work...
            #iu.setShapekeyToBasis(obj, shapekey=neutral)
            pass
        wt.cleanupWeights(obj)

    # migrate blendshape_group.json
    va = getAddon()
    if va:
        ext = arma.obj.data.vrm_addon_extension
        ext.vrm0.blend_shape_master.blend_shape_groups.clear()
        va.editor.vrm0.migration.migrate_vrm0_blend_shape_groups(
            ext.vrm0.blend_shape_master.blend_shape_groups,
            bs_dic)

    return mergedObjs
