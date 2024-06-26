# -*- encoding:utf-8 -*-

import sys
import re
import json
from collections import OrderedDict
from dataclasses import dataclass
import bpy, bmesh
import math
from mathutils import (
    Vector,
    Matrix,
)
import statistics
from . import internalUtils as iu
from . import mathUtils as mu
from . import WeightTool as wt
from . import MaterialTool as mt
from . import BoneTool as bt
import numpy as np

################
# reg-exp for _L, _R
re_name_LR = re.compile(r'(.*[._-])([LR])$')

################################################################
def textblock2str(textblock):
    return ''.join([line.body for line in textblock.lines])

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
def addColliderToBone(mesh,
                      arma,
                      boneName,
                      t_from=0,
                      t_to=None,
                      t_step=0.05,
                      numberOfRays=32,
                      radius=0.3,
                      insideToOutside=True):
    if not mesh or not arma:
        raise ValueError(f'Error: no mesh or no arma in addCollider({mesh}, {arma}, {bone})')

    bone = arma.pose.bones[boneName]
    length = (bone.tail - bone.head).length

    mtx = bone.matrix.copy()
    mtx.translation = bone.tail
    matrix_parent = arma.matrix_world @ mtx # 親のワールド行列
    matrix_parent_inverse = matrix_parent.inverted()

    # ボーン空間からメッシュ空間への変換行列を作成
    mtxB2M = mesh.matrix_world.inverted() @ matrix_parent
    mtxB2M_rot = mtxB2M.to_3x3()

    # メッシュ空間からボーン空間への変換行列を作成
    mtxM2B = matrix_parent_inverse @ mesh.matrix_world

    # 全てのレイを作成する
    if not t_from:
        t_from = 0
    if not t_to:
        t_to = max(t_from, length - t_step)
    # print(t_from, t_to, t_step)
    t_values = np.arange(t_from, t_to, t_step) - length
    angle_values = np.linspace(0, math.tau, numberOfRays, endpoint=False)

    # meshgridでX, Y, Z座標を生成
    T, Angle = np.meshgrid(t_values, angle_values, indexing='ij')
    xx = np.cos(Angle)
    yy = T
    zz = np.sin(Angle)
    zeros = np.zeros(T.shape)
    ones = np.ones(T.shape)

    if insideToOutside:
        # 内から外へ
        dirs = np.stack((xx, zeros, zz), axis=-1)
        origs = np.stack((zeros, yy, zeros), axis=-1)
    else:
        # 外から内へ
        dirs = np.stack((-xx, zeros, -zz), axis=-1)
        origs = np.stack((xx * radius, yy, zz * radius), axis=-1)

    cylindricalRays = np.stack((origs, dirs), axis=-2)
    # print(cylindricalRays)

    params = []
    for rays in cylindricalRays:
        hits = np.array([mesh.ray_cast(mtxB2M @ Vector(od[0]),
                                       mtxB2M_rot @ Vector(od[1]),
                                       distance=radius) for od in rays])
        hits = hits[hits[:, 0] == True]
        # print(hits)
        if len(hits) >= 3:
            points = np.array([np.array(mtxM2B @ hit[1]) for hit in hits])
            points2D = points[:, [0, 2]]
            size, center = mu.calcFit(points2D)
            center = np.array([center[0], points[0][1], center[1]])
            #center = np.array([0, points[0][1], 0])
            params.append((size, center))

    # print(params)
    for size, center in params:
        emptyName = f'Collider_{bone.name}'
        empty_obj = bpy.data.objects.new(emptyName, None)
        empty_obj.parent = arma
        empty_obj.parent_type = 'BONE'
        empty_obj.parent_bone = bone.name
        empty_obj.matrix_parent_inverse = matrix_parent_inverse
        matrix_basis = matrix_parent.copy()
        matrix_basis.translation = matrix_parent @ Vector(center)
        empty_obj.matrix_basis = matrix_basis
        empty_obj.matrix_local = matrix_parent_inverse @ matrix_basis
        empty_obj.matrix_world = matrix_basis
        empty_obj.empty_display_type = 'SPHERE'
        empty_obj.empty_display_size = size

        bpy.context.scene.collection.objects.link(empty_obj)

################
def getSelectedEditableBones():
    return [iu.EditBoneWrapper(eb) for eb in bpy.context.selected_editable_bones]

################
def addCollider(meshObj,
                armaObj,
                t_from=0,
                t_to=None,
                t_step=0.05,
                numberOfRays=32,
                radius=0.3,
                insideToOutside=True):
    """
    Adds a collision sphere to the selected bones for the selected mesh.
    You should select one mesh and one armature.

    Parameters
    ----------------
    meshObj : mesh object
      Mesh to determine the size of the collider.

    armaObj : armature object
      Armature to which the collider is added.

    t_from : number
      Start offset (meter)

    t_to : number
      End offset (meter). None to fit bone-length.

    t_step : number
      Step distance (meter)

    numberOfRays : number
      Number of rays emitted from the circle.

    radius : number
      The radius of the circle that emits rays.

    insideToOutside : bool
      If true, emits rays from the center of the circle outward.
      If false, emits rays from the edge of the circle towards the center.
    """

    #print('----------------')
    mesh = iu.ObjectWrapper(meshObj)
    arma = iu.ObjectWrapper(armaObj)
    if not mesh or not arma:
        return {'CANCELLED'}, 'Please select Armature and Mesh'
    #print('mesh:', mesh.name, 'arma:', arma.name)

    with iu.mode_context(arma.obj, 'POSE'):
        selected_bones = bt.get_selected_bone_names()
        if not selected_bones:
            return {'CANCELLED'}, 'Please select a bone'

        for bone in selected_bones:
            addColliderToBone(mesh.obj, arma.obj, bone,
                              t_from=t_from,
                              t_to=t_to,
                              t_step=t_step,
                              numberOfRays=numberOfRays,
                              radius=radius,
                              insideToOutside=insideToOutside)

    return{'FINISHED'}
    
################
def duplicateColliderAsMirror(emptyObj):
    if not emptyObj.obj.parent:
        raise ValueError(f'{emptyObj} does not have a parent.')

    boneName = emptyObj.obj.parent_bone
    if not boneName:
        raise ValueError(f'{emptyObj} does not have a parent-bone.')

    mo = re_name_LR.match(boneName)
    if not mo:
        #print(f'{boneName} is not a mirror bone.')
        mirrorBoneName = boneName
    else:
        if mo.group(2) == 'L':
            lr = 'R'
        else:
            lr = 'L'
        mirrorBoneName = mo.group(1) + lr

    # Change to EDIT-mode to reset pose
    with iu.mode_context(emptyObj.obj.parent, 'EDIT'):
        empty_org = emptyObj.obj
        parent = empty_org.parent

        # Get a mirror bone
        mirrorBone = parent.pose.bones.get(mirrorBoneName)
        if not mirrorBone:
            raise ValueError(f'{boneName} does not have a mirror bone.')

        # Create an empty object
        newName = f'Collider_{mirrorBoneName}'
        empty_new = bpy.data.objects.new(newName, None)

        # Calc mirrored location
        location = parent.matrix_world.inverted() @ empty_org.matrix_world.translation
        location.x *= -1
        matrix_world = Matrix.Translation(parent.matrix_world @ location)

        # Set parameters
        iu.setupObject(empty_new,
                       parent,
                       'BONE',
                       mirrorBoneName,
                       matrix_world)

        pbone = parent.pose.bones[boneName]
        empty_new.empty_display_type = 'SPHERE'
        empty_new.empty_display_size = empty_org.empty_display_size * empty_org.matrix_world.median_scale

        # Link to scene
        collection = iu.findCollectionIn(empty_org)
        collection.objects.link(empty_new)

        empty_org.select_set(True)
        empty_new.select_set(True)

################
def setEmptyAsCollider(emptyObj, armaObj, boneName, rename=True, symmetrize=False):
    empty = emptyObj.obj
    arma = armaObj.obj

    if not empty or not arma:
        raise ValueError(f'setEmptyAsCollider({emptyObj}, {armaObj}, {boneName})')
    
    if empty.type != 'EMPTY':
        raise ValueError(f'{empty} is not EMPTY.')

    if arma.data.bones.find(boneName) < 0:
        raise ValueError(f'bone {boneName} is not found.')

    newName = f'Collider_{boneName}'
    if rename:
        empty.name = newName
        emptyObj = iu.ObjectWrapper(empty)

    # setup
    size = empty.empty_display_size * empty.matrix_world.median_scale
    matrix_world = Matrix.Translation(empty.matrix_world.translation)
    empty.empty_display_type = 'SPHERE'
    empty.empty_display_size = size
    iu.setupObject(empty, arma, 'BONE', boneName, matrix_world)

    if symmetrize:
        duplicateColliderAsMirror(emptyObj)

################################################################
@dataclass
class MaterialInfo:
    material_name: str
    alpha_array: np.ndarray
    alpha_threshold: float

################################################################
def buildRemoveMatDic(interval, alphaThreshold, excludeMaterials):
    """
    Returns material dictionary to remove polygons
    """

    result = dict()

    # get VRM_Addon_for_Blender
    va = getAddon()
    if not va:
        raise ValueError('VRM addon is not found')
    shader = va.common.shader
    search = va.editor.search

    for mat in bpy.data.materials:
        # Skip opaque and excludeMaterials
        if mat.blend_method == 'OPAQUE' or mat.name in excludeMaterials:
            continue

        if mat.blend_method == 'CLIP':
            alpha_threshold = mat.alpha_threshold
        else:
            alpha_threshold = alphaThreshold

        # Skip non-VRM-shader material
        node = search.vrm_shader_node(mat)
        if not isinstance(node, bpy.types.Node):
            continue

        # Skip auto_scroll material
        if shader.get_float_value(node, 'UV_Scroll_X') != 0 or\
           shader.get_float_value(node, 'UV_Scroll_Y') != 0 or\
               shader.get_float_value(node, 'UV_Scroll_Rotation') != 0:
            continue

        # Find MainTextureAlpha image
        image = None
        img_wt_ft = shader.get_image_name_and_sampler_type(node,
                                                           'MainTextureAlpha')
        image_name, wrap_type, filter_type = img_wt_ft
        image = bpy.data.images.get(image_name)
        if not image:
            print(f'Material({mat.name}): MainTextureAlpha is not linked to a image. ')
            continue

        # This material is transparent and has alpha-image.
        result[mat] = MaterialInfo(mat.name,
                                   iu.image_to_alpha_array(image, interval),
                                   alpha_threshold)
    #print(result)
    return result
    
################################################################
def delete_transparent_faces(obj, removeMatDic):
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv.active

    faces_to_remove = []

    # Initialize progress bar
    bpy.context.window_manager.progress_begin(0, 100)

    for face_idx, face in enumerate(bm.faces):
        mat_idx = face.material_index
        material = obj.material_slots[mat_idx].material

        info = removeMatDic.get(material)
        if not info:
            continue

        if not iu.scan_face_alpha(face, uv_layer,
                                  info.alpha_array, info.alpha_threshold):
            faces_to_remove.append(face)
            #print(f'remove face {face_idx} in {obj.name}')

        # Update progress bar
        face_total = len(bm.faces)
        progress = face_idx / face_total * 100
        bpy.context.window_manager.progress_update(progress)

    # Remove transparent faces
    for face in faces_to_remove:
        bm.faces.remove(face)

    bm.to_mesh(mesh)
    bm.free()

    print(f'Removed {len(faces_to_remove)} polygons from {obj.name}')
    return len(faces_to_remove)

################################################################
def removeTransparentPolygons(obj,
                              interval=4,
                              alphaThreshold=0.01,
                              excludeMaterials=set()):
    removeMatDic = buildRemoveMatDic(interval, alphaThreshold, excludeMaterials)
    delete_transparent_faces(obj, removeMatDic)
    iu.remove_isolated_edges_and_vertices(obj)

################################################################
def mergeMeshes(arma, bs_dic, triangulate=True, removeMatDic=None):
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

    removeMatDic : dict of MaterialInfo
      Material informations to remove transparent polygons.
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
        if removeMatDic:
            delete_transparent_faces(obj.obj, removeMatDic)
            iu.remove_isolated_edges_and_vertices(obj.obj)

    bpy.context.scene.cursor.location = cursor_location_save

    # clear pose
    with iu.mode_context(arma.obj, 'POSE'):
        for bone in arma.obj.data.bones:
            bone.hide = False
            bone.select = True
        # for stretch bones, call twice
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.transforms_clear()

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
        mesh = result.get(mn)
        if not mesh:
            print(f'Warning! Mesh {mn} is not merged')
            continue

        for an in sorted(actions):
            #print(f'action: {an}')
            action = bpy.data.actions.get(an)
            if not action:
                print(f'Warning! Cannot find action {an}')
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
            with iu.mode_context(arma.obj, 'POSE'):
                # for stretch bones, call twice
                bpy.ops.pose.transforms_clear()
                bpy.ops.pose.transforms_clear()

    return result

################################################################
def deleteBones(arma, boneGroupName):
    """
    Deletes all bones which belongs to bone_groups[boneGroupName].
    """

    print('---------------- deleteBones')

    # listup all bones to be deleted
    with iu.mode_context(arma.obj, 'POSE'):
        bc = arma.data.collections.get(boneGroupName)
        if not bc:
            print(f'Warning! Armature({arma.name}) does not have collection({boneGroupName})')
            return

        bones = [b.name for b in bc.bones]
        print(bones)

    wt.dissolveWeightedBones(arma, bones)

################################################################
def removeAllUneditableEmptyChildren(obj):
    """
    Remove all EMPTY objects that are children of the given ARMATURE object and
    not present in any collection or the current view layer.

    Parameters
    ----------
    obj : bpy.types.Object
        The ARMATURE object whose EMPTY children should be removed.

    Returns
    -------
    list
        A list of names of the removed EMPTY objects.
    """
    result = []

    if not obj or obj.type != 'ARMATURE':
        return result

    allObjects = iu.collectAllVisibleObjects()
    for child in obj.children_recursive:
        if child.type == 'EMPTY' and child not in allObjects:
            result.append(child.name)
            bpy.data.objects.remove(child)

    return result

################################################################
def applyCollidersScale(arma):
    for obj in arma.children_recursive:
        if obj.type == 'EMPTY' and obj.empty_display_type == 'SPHERE':
            iu.applyEmptyScale(obj)

################################################################
def migrateSpringBone(arma, sb_json, removeEmpty):
    va = getAddon()
    if not va:
        raise ValueError('VRM addon is not found')
    ext = arma.obj.data.vrm_addon_extension
    
    # clear old data
    ext.vrm0.secondary_animation.bone_groups.clear()
    ext.vrm0.secondary_animation.collider_groups.clear()
    if removeEmpty:
        removed = removeAllUneditableEmptyChildren(arma.obj)
        if removed:
            print(f'Removed {len(removed)} empty objects: {removed}')

    applyCollidersScale(arma.obj)

    # migrate
    sb_dic = json.loads(textblock2str(bpy.data.texts[sb_json]),object_pairs_hook=OrderedDict)
    va.editor.vrm0.migration.migrate_vrm0_secondary_animation(
        ext.vrm0.secondary_animation,
        sb_dic,
        arma.obj,
        arma.obj.data)

################################################################
def checkBrendShape(bs_dic):
    has_error = False
    meshes = set()
    for bs in bs_dic:
        binds = bs.get('binds')
        if binds:
            for bind in binds:
                mesh = bind.get('mesh')
                index = bind.get('index')
                if mesh:
                    meshes.add(mesh)
                    mesh_obj = bpy.data.objects.get(mesh)
                    if mesh_obj and mesh_obj.type == 'MESH' and\
                       mesh_obj.data.shape_keys and\
                       index not in mesh_obj.data.shape_keys.key_blocks:
                        has_error = True
                        print(f'Warning! Cannot find shapekey({index}) in mesh({mesh}).')

    for mesh in meshes:
        mesh_obj = bpy.data.objects.get(mesh)
        if not mesh_obj:
            has_error = True
            print(f'Warning! Cannot find object({mesh}).')
        elif mesh_obj.type != 'MESH':
            has_error = True
            print(f'Warning! Object({mesh}) is not a mesh.')
        elif not mesh_obj.data.shape_keys:
            has_error = True
            print(f'Warning! Object({mesh}) does not have shepe_keys')

    return not has_error

################################################################
def migrateBlendShape(armature, bs_json):
    va = getAddon()
    if not va:
        raise ValueError('VRM addon is not found')

    ext = armature.data.vrm_addon_extension

    # clear old data
    ext.vrm0.blend_shape_master.blend_shape_groups.clear()
    bs_dic = json.loads(textblock2str(bpy.data.texts[bs_json]),object_pairs_hook=OrderedDict)
    
    # migrate blendshape_group.json
    if checkBrendShape(bs_dic):
        va.editor.vrm0.migration.migrate_vrm0_blend_shape_groups(
            ext.vrm0.blend_shape_master,
            bs_dic)

################################################################
def prepareToExportVRM(skeleton='skeleton',
                       triangulate=False,
                       removeTransparentPolygons=True,
                       interval=4,
                       alphaThreshold=0.01,
                       excludeMaterials=set(),
                       bs_json=None,
                       notExport='NotExport',
                       materialOrderList=None,
                       removeUnusedMaterialSlots=False,
                       neutral='Neutral',
                       sb_json=None,
                       removeEmpty=True):
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
    sb_json : String
        Name of textblock of spring_bone.json
    """

    arma = iu.ObjectWrapper(skeleton)

    va = getAddon()
    if not va:
        raise ValueError('VRM addon is not found')

    ext = arma.obj.data.vrm_addon_extension

    # clear old data
    ext.vrm0.blend_shape_master.blend_shape_groups.clear()
    bs_dic = json.loads(textblock2str(bpy.data.texts[bs_json]),object_pairs_hook=OrderedDict)

    if removeTransparentPolygons:
        removeMatDic = buildRemoveMatDic(interval, alphaThreshold, excludeMaterials)
    else:
        removeMatDic = None

    mergedObjs = mergeMeshes(arma, bs_dic, triangulate=triangulate, removeMatDic=removeMatDic)

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

        if removeUnusedMaterialSlots:
            print(f'removeUnusedMaterialSlots obj:{obj.name}')
            with iu.mode_context(obj.obj, 'OBJECT'):
                bpy.ops.object.material_slot_remove_unused()

        if materialOrderList:
            print(f'sort_material_slots obj:{obj.name}')
            mt.sort_material_slots(obj.obj, materialOrderList)

    # migrate blendshape_group.json
    if checkBrendShape(bs_dic):
        va.editor.vrm0.migration.migrate_vrm0_blend_shape_groups(
            ext.vrm0.blend_shape_master,
            bs_dic)

    # migrate spring_bone.json
    if sb_json:
        migrateSpringBone(arma, sb_json, removeEmpty)

    return mergedObjs
