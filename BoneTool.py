# -*- encoding:utf-8 -*-

import bpy
import uuid
import bmesh
from mathutils import (
    Vector,
    Matrix,
)
import traceback
import numpy as np
import math
from dataclasses import dataclass
from . import internalUtils as iu
from . import mathUtils as mu

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

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
    with iu.mode_context(arma.obj, 'POSE'):
        for bone in arma.obj.pose.bones:
            for cn in bone.constraints:
                #print(bone.name, cn.name, cn.type)
                if cn.type == 'STRETCH_TO':
                    #print(cn.rest_length)
                    cn.rest_length = 0
                    result += 1
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
    with iu.mode_context(arma.obj, 'OBJECT'):
        for co in arma.obj.children_recursive:
            if co in bpy.context.selectable_objects:
                #print(co.name)
                bpy.context.view_layer.objects.active = co

                # find ARMATURE modifier
                for mod in co.modifiers:
                    if mod.type == 'ARMATURE':
                        nameSave = mod.name
                        mod.name = str(uuid.uuid4())
                        try:
                            bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=mod.name)
                            iu.blendShapekeyToBasis(co, mod.name, blend=1.0, remove_shapekey=True)
                        except RuntimeError as e:
                            print(f'******** Error has occured. object:{co.name} mod:{nameSave} ********')
                            traceback.print_exc()

                        mod.name = nameSave
                        break
            
    # apply pose
    with iu.mode_context(arma.obj, 'POSE'):
        bpy.ops.pose.armature_apply(selected=False)

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
    with iu.mode_context(meshObj.obj, 'OBJECT'): 
        pass

    # アーマチュアを作成
    arm_data = bpy.data.armatures.new('Armature')
    armature = bpy.data.objects.new('Armature', arm_data)
    iu.setupObject(armature, None, 'OBJECT', '', meshObj.obj.matrix_world)
    bpy.context.collection.objects.link(armature)

    # ボーンを作成するために編集モードにする
    with iu.mode_context(armature, 'EDIT'):
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
def get_sorted_bone_names(arma):
    """
    親から子の順にソートしたボーン名の配列を得る
    """
    sorted_list = []
    for bone in arma.data.bones:
        if not bone.parent:
            sorted_list.append(bone.name)
            sorted_list.extend([b.name for b in bone.children_recursive])
    return sorted_list

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
    with iu.mode_context(armaObj.obj, 'POSE'):
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
    with iu.mode_context(arma.obj, 'EDIT'):
        for bone in arma.obj.data.edit_bones:
            iu.EditBoneWrapper(bone).select_set(bone.name in selectBoneNames)

################
# boneNames の中で、最も先祖に近い骨達だけを得る
def get_ancestral_bones(arma, boneNames):
    bones_left = set(boneNames)
    result = set(boneNames)

    while bones_left:
        boneName = bones_left.pop()
        bone = arma.obj.data.bones.get(boneName)
        if not bone:
            print(f'Cannot find {boneName} in {arma}')
            print([b.name for b in arma.obj.data.bones])
            result.discard(boneName)
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
    outward_shift : float
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
    dirs = np.dot(np.stack((-xx, zeros, -zz), axis=-1), mtxB2M_rot.T) * params.radius
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
            rad = np.linalg.norm(dir)
            hit, location, normal, index = mesh.ray_cast(orig, dir, distance=rad)
            if hit:
                #print(hit, location, normal, index)
                dists_mesh[i,j] = 1 - np.dot(np.array(location) - orig, dir) / (rad * rad)

    # 平滑化
    if params.window_size > 1:
        dists_mesh = mu.convolve_tube(dists_mesh, params.window_size, params.std_dev)

    # 座標を計算
    points = origs - dirs * (dists_mesh - 1 + params.outward_shift)[..., np.newaxis]

    # ワールド座標に変換
    oneones = ones.reshape((ones.shape[0], ones.shape[1], 1))
    points = np.concatenate((points, oneones), axis=-1)
    points = np.dot(points, np.array(mesh.matrix_world).T)[:, :, :3]

    return points

################
# 骨を、接続ごとに分離した構造を返す
# use_connect が False ならば、親はないと見なす
def getBranches(arma):
    branches = []
    bones = set(arma.pose.bones)

    # ボーン名 -> 親 の辞書と、親のセットを作成する
    bone_to_parent = dict()
    parents = set()
    for bone in bones:
        if bone.parent and bone.bone.use_connect:
            parent = bone.parent
            bone_to_parent[bone.name] = parent
            parents.add(parent.name)

    # 子のないボーンのリストを作成し、それぞれの枝を検索する
    leaf_bones = [bone for bone in bones if bone.name not in parents]
    for bone in leaf_bones:
        branch = []

        # 親へ遡りながら枝を保存していく
        while bones:
            bones.remove(bone)
            branch.append(bone)

            parent = bone_to_parent.get(bone.name)
            if parent and parent in bones:
                bone = parent
            else:
                break
                
        branches.append(reversed(branch))

    assert not bones

    return branches

################
def createEncasedSkin(mesh,
                      arma,
                      t_step=0.05,
                      numberOfRays=32,
                      radius=0.3,
                      window_size=3,
                      std_dev=1/6,
                      outward_shift=0.1,
                      phase=0):
    if not mesh or not arma:
        raise ValueError(f'Error: no mesh or no arma in makeSkin({mesh}, {arma})')

    with iu.mode_context(arma.obj, 'POSE'):
        params = SkinMeshParams(t_step,
                                numberOfRays,
                                radius,
                                window_size,
                                std_dev,
                                outward_shift,
                                phase)

        # メッシュデータを格納する配列
        bone_to_indices = dict()
        index_from = 0
        verts = np.empty((0, 3))
        faces = []

        # 枝ごとにチューブを作っていく
        branches = getBranches(arma.obj)
        for branch in branches:
            #print('New branch ----------------')
            index_base = index_from

            # ボーンの周りをスキャンしてチューブ状の頂点群を作る
            # 頂点インデックスも同時に保存していく
            tube = np.empty((0, numberOfRays, 3))
            for bone in branch:
                #print(f' {bone.name}')
                points = getSkinMesh(mesh.obj, arma.obj, bone, params)
                tube = np.vstack((tube, points))
                index_to = index_from + points.shape[0] * points.shape[1]
                bone_to_indices[bone.name] = range(index_from, index_to)
                index_from = index_to
            #print(tube)

            # tube をメッシュにするためのデータを作成
            vs = tube.reshape((-1, 3))
            verts = np.vstack((verts, vs))

            indices_0_0 = np.arange(index_base, index_base + vs.shape[0]).reshape((-1, tube.shape[1]))
            indices_1_0 = np.roll(indices_0_0, -1, axis=1)
            indices_0_1 = np.roll(indices_0_0, -1, axis=0)
            indices_1_1 = np.roll(indices_0_1, -1, axis=1)

            face_sides = np.stack((indices_0_0, indices_0_1, indices_1_1, indices_1_0),
                                  axis=2)[:-1].reshape((-1, 4))
            face_top = indices_0_0[0]
            face_bottom = indices_0_0[-1][::-1]

            faces.extend(face_sides)
            faces.append(face_top)
            faces.append(face_bottom)

        # メッシュオブジェクトを作成
        name = f'{arma.name}_skin'
        new_mesh = bpy.data.meshes.new(name=name)
        new_mesh.from_pydata(verts, [], faces)
        new_mesh.update()

        new_obj = bpy.data.objects.new(name, new_mesh)

        # ウェイト設定
        for name, indices in bone_to_indices.items():
            vg = new_obj.vertex_groups.new(name=name)
            vg.add(indices, 1, type='REPLACE')

        # シーンに追加
        collection = iu.findCollectionIn(arma.obj)
        collection.objects.link(new_obj)

        # アーマチュアの子にする
        iu.setupObject(new_obj,
                       arma.obj,
                       'OBJECT',
                       '',
                       Matrix())

        # アーマチュアモディファイアを追加
        modifier = new_obj.modifiers.new('ArmatureMod', 'ARMATURE')
        modifier.object = arma.obj
        modifier.use_vertex_groups = True

    return new_obj

################
def getDirection(axis, length=1):
    if   axis == 'POS_X': return Vector((length, 0, 0))
    elif axis == 'POS_Y': return Vector((0, length, 0))
    elif axis == 'POS_Z': return Vector((0, 0, length))
    elif axis == 'NEG_X': return Vector((-length, 0, 0))
    elif axis == 'NEG_Y': return Vector((0, -length, 0))
    elif axis == 'NEG_Z': return Vector((0, 0, -length))
    else:
        raise ValueError(f'Illegal axis: {axis}')

################
def buildHandleFromVertices(bone_length=0.1,
                            set_parent=False,
                            axis='NEG_Y',
                            basename='handle'):
    selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    created_bones = []

    # Create new armature
    arm_data = bpy.data.armatures.new('Armature')
    armature = bpy.data.objects.new('Armature', arm_data)
    iu.setupObject(armature, None, 'OBJECT', '', Matrix())
    bpy.context.collection.objects.link(armature)

    with iu.mode_context(armature, 'EDIT'):
        for obj in selected_objects:
            with iu.mode_context(obj, 'OBJECT'):
                # For each vertex, create a new bone
                for vertex in obj.data.vertices:
                    if vertex.select:
                        new_bone = armature.data.edit_bones.new(f"{basename}_{obj.name}_{vertex.index}")
                        new_bone.head = obj.matrix_world @ vertex.co
                        new_bone.tail = new_bone.head + getDirection(axis, length=bone_length)
                        created_bones.append(new_bone.name)

    if not created_bones:
        # When no bones are created, remove armature
        iu.removeObject(armature)
        return None

    if set_parent:
        for obj in selected_objects:
            with iu.mode_context(obj, 'OBJECT'):
                # Parent the mesh to the armature
                obj.parent = armature

                # Add armature modifier to the object
                armature_mod = obj.modifiers.new(name="ArmatureMod", type='ARMATURE')
                armature_mod.object = armature

                # Add new bone to vertex group and set the weight to 1
                for vertex in obj.data.vertices:
                    if vertex.select:
                        group_name = f"{basename}_{obj.name}_{vertex.index}"
                        if group_name not in obj.vertex_groups:
                            obj.vertex_groups.new(name=group_name)
                        obj.vertex_groups[group_name].add([vertex.index], 1.0, 'REPLACE')

    return armature

################
def buildHandleFromBones(bone_length=0.1, axis='NEG_Y', pre='handle'):
    armature = bpy.context.object
    selected_bones = get_selected_bone_names()
    if not selected_bones:
        return None
    
    with iu.mode_context(armature, 'EDIT'):
        # Find parent
        ans = get_ancestral_bones(iu.ObjectWrapper(armature), selected_bones)
        if ans:
            parent = armature.data.edit_bones[ans.pop()].parent
        else:
            parent = None

        # Clear all selections
        bpy.ops.armature.select_all(action='DESELECT')

        created_bones = []
        for boneName in selected_bones:
            bone = armature.data.edit_bones[boneName]
            new_bone = armature.data.edit_bones.new(f'{pre}_{boneName}')
            new_bone.head = bone.tail
            new_bone.tail = bone.tail + getDirection(axis, length=bone_length)
            new_bone.parent = parent
            new_bone.use_connect = False
            new_bone.select = True
            created_bones.append(new_bone.name)
    
    # Add 'stretch-to' modifier
    with iu.mode_context(armature, 'POSE'):
        for boneName in selected_bones:
            pbone = armature.pose.bones[boneName]
            constraint = pbone.constraints.new('STRETCH_TO')
            constraint.target = armature
            constraint.subtarget = f'{pre}_{boneName}'

    return created_bones

################
def changeBoneLengthDirection(armature, length, local_direction):
    with iu.mode_context(armature, 'EDIT'):
        direction = Vector(local_direction).normalized() * length
        selected_bones = [b for b in armature.data.edit_bones if b.select]
        for bone in selected_bones:
            bone.tail = bone.head + direction

################
def is_bone_visible(bone, armature):
    if bone.hide or bone.hide_select:
        return False

    for layer_visible, layer_belongs in zip(armature.layers, bone.layers):
        if layer_visible and layer_belongs:
            return True    

    return False

################
def find_flip_side_bone_name(arma, bone_name):
    names = [b.name for b in arma.data.bones]
    return iu.find_flip_side_name(names, bone_name)

################
def get_flip_side_indices(arma):
    """
    Get an array of flipped left and right bone indices.
    For example, if the sequence of bones is
    ['chest', 'arm_L', 'hand_L', 'arm_R', 'hand_R'], then
    [0, 3, 4, 1, 2] is obtained.

    Parameters:
    -----------
    arma : bpy.types.Object
      Armature object.

    Returns:
    --------
    list
      Indices of flipped left and right bone.
    """
    names = [b.name for b in arma.data.bones]
    flipped_names = [iu.find_flip_side_name_or_self(names, n) for n in names]
    name_to_index = dict(zip(names, range(len(names))))
    flipped_indices = [name_to_index[n] for n in flipped_names]
    return flipped_indices

################
def pose_mirror_x_translations(arma, translations, selection):
    #print(selection)
    flipped_indices = np.array(get_flip_side_indices(arma))
    has_mirror = flipped_indices != np.arange(flipped_indices.size)

    # ミラーを持ち、かつ、ミラーが選択されていない骨を対象とする
    target = selection & has_mirror
    target_indices = np.where(target)[0]
    mirror_indices = flipped_indices[target_indices]
    target[mirror_indices] = False

    # 再度取得
    target_indices = np.where(target)[0]
    mirror_indices = flipped_indices[target_indices]
    #print(target_indices, mirror_indices)

    # Compute mirror translation
    mirror_translations = translations.copy()
    mirror_translations[mirror_indices] = translations[target_indices]
    mirror_translations[mirror_indices, 0] *= -1

    # 見えている骨のみ移動する
    visible_bones = np.array([is_bone_visible(b.bone, arma.data)
                              for b in arma.pose.bones], dtype=bool)
    new_translations = np.where(visible_bones[:, np.newaxis],
                                mirror_translations,
                                translations)
    return new_translations

################
def convert_local_to_pose_safe(bone, mtx, invert=False):
    """
    bone.convert_local_to_pose() のラッパー。
    親がいてもいなくても計算できる。
    convert_local_to_pose(bone.matrix_basis) は bone.matrix と一致する
    """
    if bone.parent:
        matrix = bone.bone.convert_local_to_pose(
            mtx,
            bone.bone.matrix_local,
            parent_matrix=bone.parent.matrix,
            parent_matrix_local=bone.parent.bone.matrix_local,
            invert=invert)
    else:
        matrix = bone.bone.convert_local_to_pose(
            mtx,
            bone.bone.matrix_local,
            invert=invert)
    return matrix

################
def set_translations(arma, translations, which_to_move):
    """
    ポーズボーンのローカル座標を設定する。

    Parameters:
    -----------
    arma : bpy.types.Object
      アーマチュアオブジェクト
    translations : np.ndarray
      ローカル座標の配列。移動しない骨も必ず設定しておくこと
    which_to_move : np.ndarray
      移動するかどうかを指定する bool の配列
    """

    # 骨の名前 -> index の辞書
    bone_indices = {b.name: i for i, b in enumerate(arma.pose.bones)}

    # データを親から子の順に作成していくことで、
    # 移動後の bone.matrix をまとめて計算する
    @dataclass
    class BoneData():
        moved : bool
        matrix : Matrix
        matrix_local : Matrix

    # 計算した骨のデータを保存しておく
    bone_data = dict()

    # 親→子の順にソートした骨の名前
    sorted_bone_names = get_sorted_bone_names(arma)
    for bn in sorted_bone_names:
        idx = bone_indices[bn]
        bone = arma.pose.bones[idx]
        has_child = bone.bone.children is not None
        has_parent = bone.parent is not None
        if has_parent:
            parent_data = bone_data[bone.parent.name]
        else:
            parent_data = None

        # 移動するボーン、及び、変更のあったボーンの子を全て設定する
        moving = which_to_move[idx] or has_parent and parent_data.moved
        if not moving:
            new_matrix = bone.matrix
        else:
            translation_matrix_p = Matrix.Translation(translations[idx])

            # ボーンの location を計算する
            if has_parent:
                translation_matrix_l = bone.bone.convert_local_to_pose(
                    translation_matrix_p,
                    bone.bone.matrix_local,
                    parent_matrix = parent_data.matrix,
                    parent_matrix_local = parent_data.matrix_local,
                    invert = True)
            else:
                translation_matrix_l = bone.bone.convert_local_to_pose(
                    translation_matrix_p,
                    bone.bone.matrix_local,
                    invert = True)

            translation_l = translation_matrix_l.translation
            new_matrix_basis = bone.matrix_basis.copy()
            new_matrix_basis.translation = translation_l
            
            # 子のために新しい matrix を計算
            if not has_child:
                new_matrix = None
            else:
                if has_parent:
                    new_matrix = bone.bone.convert_local_to_pose(
                        new_matrix_basis,
                        bone.bone.matrix_local,
                        parent_matrix = parent_data.matrix,
                        parent_matrix_local = parent_data.matrix_local)
                else:
                    new_matrix = bone.bone.convert_local_to_pose(
                        new_matrix_basis,
                        bone.bone.matrix_local)

            # 設定する
            bone.location = translation_matrix_l.translation

        # 子のためにデータを保存しておく
        if has_child:
            bone_data[bn] = BoneData(moving, new_matrix, bone.bone.matrix_local)
