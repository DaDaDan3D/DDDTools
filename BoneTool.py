# -*- encoding:utf-8 -*-

import bpy
import uuid
import bmesh
from mathutils import (
    Vector,
    Matrix,
)
import numpy as np
import math
from dataclasses import dataclass
from . import internalUtils as iu
from . import mathUtils as mu

################
def renameChildBonesAsUnique(bone):
    """
    Renames all child bones as unique names.

    Parameters
    ----------------
    bone: EditBone
    
    """

    for child in bone.children:
        renameChildBonesAsUnique(child)

    bone.name = str(uuid.uuid4())

################
def countChildBones(bone, nameList, count):
    nameList[bone.name] = count
    count += 1
    for child in bone.children:
        count = countChildBones(child, nameList, count)
    return count

################
def renameChildBonesWithNumber(bone, baseName):
    """
    Renames all child bones with baseName + numbers.

    Parameters
    ----------------
    bone: EditBone
    baseName: str
    
    """

    renameChildBonesAsUnique(bone)

    nameList = dict()
    count = countChildBones(bone, nameList, 0)

    for name, count in nameList.items():
        bone = bpy.context.active_object.data.edit_bones.get(name)
        if bone:
            if count > 0:
                newName = '{0}.{1:03d}'.format(baseName, count)
            else:
                newName = baseName
        print(count, ':', name, '->', newName)
        bone.name = newName

################
def applyScaleAndRotationToArmature(arma):
    """
    Applies scale and rotation to the armature's child meshes and empties.

    Parameters
    ----------------
    arma : Object Wrapper
        Skeleton Object
    """

    # 1st step
    # listup and select all child empties
    bpy.ops.object.select_all(action='DESELECT')
    boneToEmpties = dict()
    for co in arma.obj.children:
        if co.type == 'EMPTY' and co in bpy.context.selectable_objects:
            bone = co.parent_bone
            if bone:
                if bone not in boneToEmpties:
                    boneToEmpties[bone] = set()
                boneToEmpties[bone].add(co.name)
                co.select_set(True)

    # 2nd step
    # clear parent of empties
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    # 3rd step
    # apply scale and rotation to empties and skeleton
    for co in arma.obj.children:
        if co in bpy.context.selectable_objects:
            co.select_set(True)
    arma.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # 4th step
    # restore parent of empties
    for key, value in boneToEmpties.items():
        print(key, ':', value)

        bpy.ops.object.select_all(action='DESELECT')
        for en in value:
            empty = iu.ObjectWrapper(en)
            empty.select_set(True)
        arma.select_set(True)
        bpy.context.view_layer.objects.active = arma.obj

        modeChanger = iu.ModeChanger(arma.obj, 'EDIT')
        bpy.ops.armature.select_all(action='DESELECT')
        bone = iu.EditBoneWrapper(key)
        bone.select_set(True)
        arma.obj.data.edit_bones.active = bone.obj
        del modeChanger

        bpy.ops.object.parent_set(type='BONE', keep_transform=True)

    # 5th step
    # reset StretchTo
    resetStretchTo(arma)

################
def resetStretchTo(arma):
    """
    Resets all 'Stretch-to' modifiers .
    Returns number of modifiers.

    Parameters
    ----------------
    arma : Object Wrapper
        Skeleton Object
    """
    
    result = 0
    modeChanger = iu.ModeChanger(arma.obj, 'POSE')
    for bone in arma.obj.pose.bones:
        for cn in bone.constraints:
            #print(bone.name, cn.name, cn.type)
            if cn.type == 'STRETCH_TO':
                #print(cn.rest_length)
                cn.rest_length = 0
                result += 1
    del modeChanger
    return result

################
def applyArmatureToRestPose(arma):
    """
    Applies armature's current pose to rest pose.

    Parameters
    ----------------
    arma : Object Wrapper
        Skeleton Object
    """

    #print(f'---------------- applyArmatureToRestPose({arma.name})')

    # copy and apply armature modifier
    modeChanger = iu.ModeChanger(arma.obj, 'OBJECT')
    for co in arma.obj.children_recursive:
        if co in bpy.context.selectable_objects:
            #print(co.name)
            bpy.context.view_layer.objects.active = co

            # find ARMATURE modifier
            for mod in co.modifiers:
                if mod.type == 'ARMATURE':
                    nameSave = mod.name
                    mod.name = str(uuid.uuid4())
                    bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=mod.name)
                    iu.blendShapekeyToBasis(co, mod.name, blend=1.0, remove_shapekey=True)
                    mod.name = nameSave
                    break
    del modeChanger
            
    # apply pose
    bpy.context.view_layer.objects.active = arma.obj
    modeChanger = iu.ModeChanger(arma.obj, 'POSE')
    bpy.ops.pose.armature_apply(selected=False)
    del modeChanger

    # reset StretchTo
    resetStretchTo(arma)

################
def createArmatureFromSelectedEdges(meshObj,  basename='Bone'):
    """
    Create an armature such that the selected edge of the object is the bone. The bone's orientation and connections are automatically calculated based on its distance from the 3D cursor.

    Parameters
    ----------------
    meshObj: ObjectWrapper
      Mesh object

    basename: string
      Base name of bones.
      Bone names should be like these: Bone_Root, Bone_012, Bone_012.001, ...

    Returns
    ----------------
    Armature object

    """

    # メッシュが選択されていることを確認
    if meshObj.obj.type != 'MESH':
        print(f'{meshObj.obj} is not a mesh.')
        return None

    # 明示的に OBJECT モードにすることで EditMesh を確定させる
    bpy.ops.object.mode_set(mode='OBJECT')

    # アーマチュアを作成
    arm_data = bpy.data.armatures.new('Armature')
    armature = bpy.data.objects.new('Armature', arm_data)
    iu.setupObject(armature, None, 'OBJECT', '', meshObj.obj.matrix_world)
    bpy.context.collection.objects.link(armature)

    # ボーンを作成するために編集モードにする
    modeChanger = iu.ModeChanger(armature, 'EDIT')
    edit_bones = armature.data.edit_bones
    
    obj = meshObj.obj
    cursor_loc = obj.matrix_world.inverted() @ bpy.context.scene.cursor.location

    # 3D カーソルの位置にルートボーンを作成
    root_bone = edit_bones.new(f'{basename}_Root')
    root_bone.head = cursor_loc
    root_bone.tail = cursor_loc + Vector((0, 0, 1))

    # メッシュの選択したエッジに基づいてボーンを作成
    mesh = obj.data
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.edges.ensure_lookup_table()

    # 選択されたエッジから頂点を取得
    edges = [[edge.verts[0], edge.verts[1]] for edge in bm.edges if edge.select]

    # 3D カーソルからの距離で頂点及びエッジをソート
    for idx in range(len(edges)):
        edges[idx].sort(key=lambda vert:(vert.co - cursor_loc).length)
    edges.sort(key=lambda edge: ((edge[0].co + edge[1].co) / 2 - cursor_loc).length)

    # 近い順にボーンを作成し、接続できるならしていく
    vert_to_bone = dict()
    count = 0
    for edge in edges:
        vert_head, vert_tail = edge
        parent = vert_to_bone.get(vert_head)
        if parent:
            newName = parent.name
        else:
            newName = f'{basename}_{count:03d}'
            count += 1
            parent = root_bone
        
        bone = edit_bones.new(newName)
        bone.head = vert_head.co
        bone.tail = vert_tail.co
        bone.parent = parent
        bone.use_connect = (parent != root_bone)
        if vert_tail not in vert_to_bone:
            vert_to_bone[vert_tail] = bone

    # 元のモードに戻る
    del modeChanger

    return armature

################
# ボーンのツリーごとの、ルートを 0 としたインデックスを取得する
# インデックスは親より子が必ず大きいことが保証されている
def getBoneIndexDictionary(arma):
    result = dict()
    for bone in arma.data.bones:
        if not bone.parent:
            result[bone.name] = 0
            for idx, child in enumerate(bone.children_recursive):
                result[child.name] = idx + 1
    return result

################
def createMeshFromSelectedBones(armaObj):
    """
    Create the mesh such that the selected bones of the armature are the edges.
Vertex weights are also set appropriately.

    Parameters
    ----------------
    armaObj: ObjectWrapper
      Armature object

    Returns
    ----------------
      Mesh object
    """

    # ポーズモードでボーンの情報を取得
    modeChanger = iu.ModeChanger(armaObj.obj, 'POSE')
    armature = armaObj.obj

    # 選択されたボーンを取得
    bones = [bone for bone in armature.data.bones if bone.select]
    if not bones:
        print('No bones are selected.')
        return None

    # 親から子の順になるようにソート
    boneIndexDic = getBoneIndexDictionary(armature)
    bones.sort(key=lambda bone: boneIndexDic[bone.name])

    # メッシュを作成
    mesh = bpy.data.meshes.new('Mesh')
    obj = bpy.data.objects.new('Mesh', mesh)
    bm = bmesh.new()
    bm.from_mesh(mesh)

    # エッジを作成
    boneToTail = dict()
    weights = []
    for bone in bones:
        tail = bm.verts.new(bone.tail_local)
        boneToTail[bone] = tail
        if bone.parent in boneToTail and bone.use_connect:
            head = boneToTail[bone.parent]
            verts = [tail]
        else:
            head = bm.verts.new(bone.head_local)
            verts = [head, tail]
        bm.edges.new((head, tail))
        weights.append((bone, verts))

    # 頂点インデックスを確定し、weights を安全なデータに変換
    bm.verts.index_update()
    weightsEx = []
    for bone, verts in weights:
        index = [vert.index for vert in verts]
        weightsEx.append((bone.name, index))
        
    # メッシュを反映
    bm.to_mesh(mesh)
    bm.free()

    # 頂点グループを作成
    for boneName, index in weightsEx:
        vg = obj.vertex_groups.new(name=boneName)
        vg.add(index, 1.0, type='REPLACE')

    # アーマチュアと同じ位置に配置
    iu.setupObject(obj, armature, 'OBJECT', '', armature.matrix_world)

    # シーンにメッシュを追加
    bpy.context.collection.objects.link(obj)

    # アーマチュアモディファイアを追加
    modifier = obj.modifiers.new('ArmatureMod', 'ARMATURE')
    modifier.object = armature
    modifier.use_vertex_groups = True

    del modeChanger

    return obj

################
# 現在選択されているボーンの名前を得る
def get_selected_bone_names():
    armature = bpy.context.active_object
    if not armature or armature.type != 'ARMATURE':
        return None

    if armature.mode == 'POSE':
        return [b.name for b in armature.data.bones if b.select]
    elif armature.mode == 'EDIT':
        return [b.name for b in armature.data.edit_bones if b.select]
    else:
        return None

################
# 指定したボーンだけを選択した状態にする
def select_bones(arma, selectBoneNames):
    modeChanger = iu.ModeChanger(arma.obj, 'EDIT')
    for bone in arma.obj.data.edit_bones:
        iu.EditBoneWrapper(bone).select_set(bone.name in selectBoneNames)
    del modeChanger

################
# boneNames の中で、最も先祖に近い骨達だけを得る
def get_ancestral_bones(arma, boneNames):
    bones_left = set(boneNames)
    result = set(boneNames)

    while bones_left:
        boneName = bones_left.pop()
        bone = arma.obj.data.bones.get(boneName)
        if not bone:
            result -= boneName
        else:
            children = set([b.name for b in bone.children_recursive])
            result -= children
            bones_left -= children

    return result

################
@dataclass
class SkinMeshParams:
    t_step : float
    numberOfRays : int
    radius : float
    window_size : int
    std_dev : float
    padding : float
    phase : float

################
def getSkinMesh(mesh,
                arma,
                bone,
                params):
    length = (bone.tail - bone.head).length

    mtx = bone.matrix.copy()
    mtx.translation = bone.tail
    matrix_parent = arma.matrix_world @ mtx # 親のワールド行列

    # ボーン空間からメッシュ空間への変換行列を作成
    mtxB2M = np.array(mesh.matrix_world.inverted() @ matrix_parent)
    mtxB2M_rot = mtxB2M[:3, :3]

    # 全てのレイを作成する
    t_from = -length
    t_to = max(t_from, 0)
    t_values = np.arange(t_from, t_to, params.t_step)
    angle_values = np.linspace(params.phase, params.phase + math.tau,
                               params.numberOfRays, endpoint=False)

    # meshgridでX, Y, Z座標を生成
    T, Angle = np.meshgrid(t_values, angle_values, indexing='ij')
    xx = np.cos(Angle)
    yy = T
    zz = np.sin(Angle)
    zeros = np.zeros(T.shape)
    ones = np.ones(T.shape)

    # 外から内へ
    dirs = np.dot(np.stack((-xx, zeros, -zz), axis=-1), mtxB2M_rot.T)
    dirs = dirs / np.linalg.norm(dirs, axis=-1, keepdims=True)
    origs = np.dot(
        np.stack((xx * params.radius, yy, zz * params.radius, ones), axis=-1),
        mtxB2M.T)[:, :, :3]
    cylindricalRays = np.stack((origs, dirs), axis=-2)
    #print(cylindricalRays)

    # レイを飛ばし、当たった点と軸との距離を配列として作成する
    # 0 で初期化しておく
    dists_mesh = np.zeros((cylindricalRays.shape[0], cylindricalRays.shape[1]))
    for i, rays in enumerate(cylindricalRays):
        for j, (orig, dir) in enumerate(rays):
            hit, location, normal, index = mesh.ray_cast(orig, dir, distance=params.radius)
            if hit:
                dists_mesh[i,j] = params.radius - np.linalg.norm(np.array(location) - orig)

    # 平滑化
    if params.window_size > 1:
        dists_mesh = mu.convolve_tube(dists_mesh, params.window_size, params.std_dev)

    dists_mesh += params.padding

    # 座標を計算
    points = origs + dirs * (params.radius - dists_mesh)[..., np.newaxis]

    # ワールド座標に変換
    oneones = ones.reshape((ones.shape[0], ones.shape[1], 1))
    points = np.concatenate((points, oneones), axis=-1)
    points = np.dot(points, np.array(mesh.matrix_world).T)[:, :, :3]
    return points

################
def makeSkin(mesh,
             arma,
             t_step=0.05,
             numberOfRays=32,
             radius=0.3,
             window_size=3,
             std_dev=1/6,
             padding=0.1,
             phase=0):
    if not mesh or not arma:
        raise ValueError(f'Error: no mesh or no arma in makeSkin({mesh}, {arma})')

    params = SkinMeshParams(t_step,
                            numberOfRays,
                            radius,
                            window_size,
                            std_dev,
                            padding,
                            phase)

    tube = np.empty((0, numberOfRays, 3))
    for bone in arma.pose.bones:
        points = getSkinMesh(mesh, arma, bone, params)
        tube = np.vstack((tube, points))
    #print(tube)

    # リングを繋いでメッシュを作成する
    new_mesh = bpy.data.meshes.new(name="New_Mesh")
    new_obj = bpy.data.objects.new("New_Object", new_mesh)

    scene = bpy.context.scene
    scene.collection.objects.link(new_obj)
    bpy.context.view_layer.objects.active = new_obj
    new_obj.select_set(True)

    bm = bmesh.new()

    prev_ring_verts = None
    prev_ring_verts_roll = None
    for ring in tube:
        ring_verts = np.array([bm.verts.new(pt) for pt in ring])
        ring_verts_roll = np.roll(ring_verts, -1)

        # connect the vertices with the previous ring
        if prev_ring_verts is None:
            bmesh.ops.contextual_create(bm, geom=ring_verts)
        else:
            for i in range(len(ring_verts)):
                bmesh.ops.contextual_create(bm,
                                            geom=[prev_ring_verts[i],
                                                  ring_verts[i],
                                                  ring_verts_roll[i],
                                                  prev_ring_verts_roll[i]])
        prev_ring_verts = ring_verts
        prev_ring_verts_roll = ring_verts_roll

    if prev_ring_verts is not None:
        bmesh.ops.contextual_create(bm, geom=prev_ring_verts)

    bm.to_mesh(new_mesh)
    bm.free()

