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
def find_existing_armature(obj):
    # Check parent
    if obj.parent and obj.parent.type == 'ARMATURE':
        return obj.parent

    # Find ARMATURE modifier
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE':
            return mod.object

    return None

################
def createBonesFromSelectedEdges(meshObj,
                                 basename='Bone',
                                 suffix='',
                                 create_root=False,
                                 create_handle=False,
                                 bbone_segments=1,
                                 use_existing_armature=True,
                                 set_weight=True):
    """
    Create bones such that the selected edge of the object is the bone. The bone's orientation and connections are automatically calculated based on its distance from the 3D cursor.

    Parameters
    ----------------
    meshObj: ObjectWrapper
      Mesh object

    basename: string
      Base name of bones.
      Bone names will be like these: Bone_Root, Bone_2.2, Bone_12.5, ...

    suffix: string
      Suffix to be added to the name.

    create_root: bool
      Create root bone.

    create_handle: bool
      Create handle bone.

    bbone_segments: int
      Number of subdivisions of bone for B-Bones.

    use_existing_armature: bool
      Search Parent → Armature Modifier, and if there is an existing armature, create a bone in it.

    set_weight: bool
      Set vertex weights on the mesh.

    handle_vector: Vector
      Specify the direction and length of the handle.
    

    Returns
    ----------------
    ObjectWrapper
      Armature object.
    """

    # メッシュが選択されていることを確認
    if meshObj.obj.type != 'MESH':
        print(f'{meshObj.obj} is not a mesh.')
        return None, None

    # 明示的に OBJECT モードにすることで EditMesh を確定させる
    with iu.mode_context(meshObj.obj, 'OBJECT'): 
        pass

    # 辺ストリップを得る
    strips = iu.get_selected_edge_strips(meshObj.obj)
    if not strips:
        return None, None

    if use_existing_armature:
        existing_arma = iu.ObjectWrapper(find_existing_armature(meshObj.obj))
        if existing_arma and existing_arma.obj not in bpy.context.selectable_objects:
            print(f'Warning: Armature({existing_arma.name}) is not selectable.')
            existing_arma = None
    else:
        existing_arma = None

    # アーマチュアを作成
    # Blender のバグで、メッシュが EDIT モードの時に、
    # 既存のアーマチュアを EDIT モードにしてボーンを追加すると
    # Undo ができなくなってしまう(おそらくメモリリークしている)
    # そのため、まず強制的に新規アーマチュアを作る
    arm_data = bpy.data.armatures.new('Armature')
    armature = bpy.data.objects.new('Armature', arm_data)
    iu.setupObject(armature, None, 'OBJECT', '', Matrix())
    bpy.context.collection.objects.link(armature)
    if set_weight:
        meshObj.obj.parent = armature
    if bbone_segments > 1:
        armature.data.display_type = 'BBONE'
    arma = iu.ObjectWrapper(armature)

    # アーマチュアローカル座標に変換
    mtx = arma.obj.matrix_world.inverted()
    mesh_to_arma =  mtx @ meshObj.obj.matrix_world

    # ボーンを作成するために編集モードにする
    with iu.mode_context(arma.obj, 'EDIT'):
        mesh = meshObj.obj.data

        # 新規作成したボーン
        created_bones = []
        
        # 新規作成した変形ボーン
        created_deform_bones = []

        # メッシュローカル座標 head, tail の位置に new_name で骨を作成する
        def create_bone(new_name, head, tail,
                        parent=None,
                        use_connect=False,
                        use_deform=False):
            nonlocal arma, created_bones, created_deform_bones
            new_bone = arma.obj.data.edit_bones.new(new_name)
            new_bone.head = mesh_to_arma @ head
            new_bone.tail = mesh_to_arma @ tail
            new_bone.parent = parent
            new_bone.use_connect = use_connect
            new_bone.use_deform = use_deform
            created_bones.append(new_bone.name)
            if use_deform:
                created_deform_bones.append(new_bone.name)
            return new_bone

        # メッシュローカル座標での 3D カーソルの位置を計算
        mtx = meshObj.obj.matrix_world.inverted()
        cursor_loc = mtx @ bpy.context.scene.cursor.location

        # 3D カーソルの位置にルートボーンを作成
        if create_root:
            root_bone = create_bone(f'{basename}_Root{suffix}',
                                    cursor_loc,
                                    cursor_loc + handle_vector)
        else:
            root_bone = None

        # 辺ストリップからハンドルの長さと向きを計算する
        if create_root or create_handle:
            vectors = np.array([])
            normals = np.array([])
            for strip in strips:
                coords = np.array([list(mesh.vertices[v].co) for v in strip])
                vectors = np.append(
                    vectors,
                    (np.roll(coords, -1, axis=0) - coords)[:-1])
                normals = np.append(
                    normals,
                    np.array([list(mesh.vertices[v].normal) for v in strip]))

            vectors = np.reshape(vectors, (-1, 3))
            handle_length = np.median(np.linalg.norm(vectors, axis=-1)) * 0.5

            normals = np.reshape(normals, (-1, 3))
            normal = np.mean(normals, axis=0)
            handle_vector = Vector(mu.closest_axis(normal) * handle_length)

        # 頂点インデックス→頂点グループ のリスト
        vert_to_boneNames = dict()
        def vert_to_boneNames_add(vert, bone):
            nonlocal vert_to_boneNames
            lst = vert_to_boneNames.get(vert.index, [])
            lst.append(bone.name)
            vert_to_boneNames[vert.index] = lst

        strip_bones = []
        strip_handles = []

        # strip に基づいてボーンを作成
        for strip_count, strip in enumerate(strips):
            # 近い方を始点にする
            if (mesh.vertices[strip[0]].co - cursor_loc).length >\
               (mesh.vertices[strip[-1]].co - cursor_loc).length:
                strip.reverse()

            parent = root_bone
            vert_head = mesh.vertices[strip[0]]
            bones = []
            handles = []
            for bone_count, vert_idx in enumerate(strip[1:]):
                vert_tail = mesh.vertices[vert_idx]
                bone = create_bone(f'{basename}_{strip_count}.{bone_count}{suffix}',
                                   vert_head.co,
                                   vert_tail.co,
                                   parent = parent,
                                   use_connect = (bone_count > 0),
                                   use_deform = True)
                bone.bbone_segments = bbone_segments
                bone.bbone_handle_use_scale_start[0] = True
                bone.bbone_handle_use_scale_start[2] = True
                bone.bbone_handle_use_scale_end[0] = True
                bone.bbone_handle_use_scale_end[2] = True
                bone.use_inherit_rotation = False
                bone.inherit_scale = 'NONE'

                bones.append(bone.name)

                # ウェイトを乗せる頂点を設定
                # 最初の骨は head と tail、ほかは tail のみ
                if bone_count == 0:
                    vert_to_boneNames_add(vert_head, bone)
                vert_to_boneNames_add(vert_tail, bone)

                # ハンドルの作成
                if create_handle:
                    if bone_count == 0:
                        # 開始ハンドルの作成
                        vec = (vert_tail.co - vert_head.co) * 0.5
                        handle = create_bone(f'handle_head_{bone.name}',
                                             vert_head.co,
                                             vert_head.co + vec,
                                             parent = root_bone)
                        bone.bbone_custom_handle_start = handle
                        bone.bbone_handle_type_start = 'TANGENT'

                        # 開始ハンドルは handles に保存せず、
                        # bbone_custom_handle_start から参照する

                    if bone_count < len(strip) - 2:
                        # 途中ハンドルの作成
                        handle = create_bone(f'handle_{bone.name}',
                                             vert_tail.co,
                                             vert_tail.co + handle_vector,
                                             parent = root_bone)
                    else:
                        # 終了ハンドルの作成
                        vec = vert_tail.co - vert_head.co
                        vec = vec.normalized() * handle_length
                        handle = create_bone(f'handle_{bone.name}',
                                             vert_tail.co,
                                             vert_tail.co + vec,
                                             parent = root_bone)
                        bone.bbone_custom_handle_end = handle
                        bone.bbone_handle_type_end = 'TANGENT'

                    handles.append(handle.name)

                # 次へ
                vert_head = vert_tail
                parent = bone

            strip_bones.append(bones)
            strip_handles.append(handles)


    # ハンドル絡みのコンストレイントの設定
    if create_handle:
        with iu.mode_context(arma.obj, 'POSE'):
            for bones, handles in zip(strip_bones, strip_handles):
                bone = arma.obj.pose.bones[bones[0]]

                # 最初のボーンの前のハンドルを取得
                prev_hn = bone.bbone_custom_handle_start.name

                first_bone = True
                for bn, hn in zip(bones, handles):
                    bone = arma.obj.pose.bones[bn]

                    # 位置に応じてコピーコンストレイントを追加
                    if first_bone:
                        cst = bone.constraints.new('COPY_TRANSFORMS')
                        cst.target = arma.obj
                        cst.subtarget = prev_hn
                        cst.target_space = 'POSE'
                        cst.owner_space = 'POSE'

                    else:
                        cst = bone.constraints.new('COPY_SCALE')
                        cst.target = arma.obj
                        cst.subtarget = prev_hn
                        cst.use_x = True
                        cst.use_y = False
                        cst.use_z = True
                        cst.target_space = 'LOCAL'
                        cst.owner_space = 'LOCAL'

                        cst = bone.constraints.new('COPY_ROTATION')
                        cst.target = arma.obj
                        cst.subtarget = prev_hn
                        cst.use_x = False
                        cst.use_y = True
                        cst.use_z = False
                        cst.mix_mode = 'ADD'
                        cst.target_space = 'LOCAL'
                        cst.owner_space = 'LOCAL'
                        
                    # stretch-to コンストレイントを追加
                    cst = bone.constraints.new('STRETCH_TO')
                    cst.target = arma.obj
                    cst.subtarget = hn
                    cst.volume = 'NO_VOLUME'

                    # 次へ
                    first_bone = False
                    prev_hn = hn

    # ベンディボーンのサイズを自動調整
    # FIXME サイズを指定できるようにする？
    adjust_bendy_bone_size(arma.obj, created_bones, 0.1, 0.1)

    # 既存のアーマチュアにマージする
    if existing_arma:
        merge_armatures(existing_arma.name, arma.name)
        arma = existing_arma

    # 頂点ウェイトの設定
    if set_weight:
        with iu.mode_context(meshObj.obj, 'OBJECT'):
            obj = meshObj.obj

            # # 対象の頂点のウェイトをまずは全て削除
            # verts = list(vert_to_boneNames.keys())
            # for vertex_group in obj.vertex_groups:
            #     vertex_group.remove(verts)

            # 新しい頂点グループの作成とリセット
            all_verts = list(range(len(obj.data.vertices)))
            for bn in created_deform_bones:
                vertex_group = obj.vertex_groups.get(bn)
                if not vertex_group:
                    vertex_group = obj.vertex_groups.new(name=bn)
                vertex_group.remove(all_verts)

            # 対象の頂点のウェイトを設定
            for v_idx, bone_names in vert_to_boneNames.items():
                # print(f'v[{v_idx}] -> {bone_names}')
                weight = 1 / len(bone_names)
                for bn in bone_names:
                    vertex_group = obj.vertex_groups[bn]
                    vertex_group.add([v_idx], weight, 'ADD')

            # アーマチュアモディファイアの設定
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE':
                    break
            else:
                # Add armature modifier to the object
                mod = obj.modifiers.new(name="Armature", type='ARMATURE')
            mod.object = arma.obj

    return arma, created_bones

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
def buildHandleFromVertices(prefix='handle',
                            handle_factor=0.1,
                            handle_align_axis=True,
                            use_existing_armature=True,
                            set_weight=True):
    selected_objects = [iu.ObjectWrapper(o) for o in bpy.context.selected_objects if o.type == 'MESH']

    # 頂点情報
    @dataclass
    class VertInfo:
        v_idx : int
        location : Vector       # 座標(ワールド)
        normal : Vector         # 法線(ワールド)
        bone_name : str

    # ボーンを作成すべき頂点のリストを作成する
    vert_infos = dict()
    for mo in selected_objects:
        # オブジェクトモードにすることでメッシュを確定する
        with iu.mode_context(mo.obj, 'OBJECT'):
            mesh = mo.data
            mtx = mo.obj.matrix_world
            mtx_rot = mtx.to_3x3().normalized()
            vis = [
                VertInfo(v.index, mtx @ v.co, mtx_rot @ v.normal, '') \
                for v in mesh.vertices if v.select]
            if vis:
                vert_infos[mo.name] = vis
    if not vert_infos:
        return None, None

    # ポリゴン面積の中央値からハンドルの長さを計算
    areas = np.array([
        p.area for mo in selected_objects for p in mo.data.polygons])
    handle_length = math.sqrt(np.median(areas)) * handle_factor

    # アーマチュアを作成
    # Blender のバグで、メッシュが EDIT モードの時に、
    # 既存のアーマチュアを EDIT モードにしてボーンを追加すると
    # Undo ができなくなってしまう(おそらくメモリリークしている)
    # そのため、まず強制的に新規アーマチュアを作る
    arm_data = bpy.data.armatures.new('Armature')
    armature = bpy.data.objects.new('Armature', arm_data)
    iu.setupObject(armature, None, 'OBJECT', '', Matrix())
    bpy.context.collection.objects.link(armature)
    arma = iu.ObjectWrapper(armature)

    # ボーンを作成
    created_bones = []
    with iu.mode_context(arma.obj, 'EDIT'):
        edit_bones = arma.data.edit_bones
        for obj_name, vis in vert_infos.items():
            for vi in vis:
                # For each vertex, create a new bone
                if handle_align_axis:
                    vec = Vector(mu.closest_axis(np.array(vi.normal)))
                else:
                    vec = vi.normal
                new_name = f"{prefix}_{obj_name}_{vi.v_idx}"
                new_bone = edit_bones.new(new_name)
                new_bone.head = vi.location
                new_bone.tail = vi.location + vec * handle_length
                created_bones.append(new_bone.name)
                vi.bone_name = new_bone.name

    # ベンディボーンのサイズを自動調整
    # FIXME サイズを指定できるようにする？
    adjust_bendy_bone_size(arma.obj, created_bones, 0.1, 0.1)

    # 既存のアーマチュアを検索してマージ
    if use_existing_armature:
        for obj_name in vert_infos.keys():
            obj = bpy.data.objects[obj_name]
            existing_armature = find_existing_armature(obj)
            if existing_armature:
                if existing_armature not in bpy.context.selectable_objects:
                    print(f'Warning: Armature({existing_armature.name}) is not selectable.')
                else:
                    merge_armatures(existing_armature.name, arma.name)
                    arma = iu.ObjectWrapper(existing_armature)
                    break

    # 頂点ウェイトを設定
    if set_weight:
        for obj_name, vis in vert_infos.items():
            obj = bpy.data.objects[obj_name]
            with iu.mode_context(obj, 'OBJECT'):
                # Parent the mesh to the armature
                obj.parent = arma.obj

                all_verts = list(range(len(obj.data.vertices)))
                for vi in vis:
                    # 新しい頂点グループの作成とリセット
                    vertex_group = obj.vertex_groups.get(vi.bone_name)
                    if not vertex_group:
                        vertex_group = obj.vertex_groups.new(name=vi.bone_name)
                    vertex_group.remove(all_verts)
                
                    # 対象の頂点のウェイトを設定
                    vertex_group.add([vi.v_idx], 1, 'REPLACE')

                # アーマチュアモディファイアの設定
                for mod in obj.modifiers:
                    if mod.type == 'ARMATURE':
                        break
                else:
                    # Add armature modifier to the object
                    mod = obj.modifiers.new(name="Armature", type='ARMATURE')
                mod.object = arma.obj

    # メッシュを選択状態にする
    for mo in selected_objects:
        mo.select_set(True)

    return arma, created_bones

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
            constraint.volume = 'NO_VOLUME'

    # ベンディボーンのサイズを自動調整
    # FIXME サイズを指定できるようにする？
    adjust_bendy_bone_size(armature, created_bones, 0.1, 0.1)

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
def find_mirror_bone(armature, bone_name, epsilon=1e-10):
    """
    Find bone at flipped side location.

    Parameters:
    -----------
    armature : bpy.types.Object
      Armature object.

    bone_name : string
      Bone name to find mirrored-bone.

    epsilon : float
      Distance that can be considered close enough.

    Returns:
    --------
    string
      Mirror bone name.
    """
    bone = armature.data.bones[bone_name]

    mirror_head = Vector((-bone.head_local.x, bone.head_local.y, bone.head_local.z))
    mirror_tail = Vector((-bone.tail_local.x, bone.tail_local.y, bone.tail_local.z))

    for b in armature.data.bones:
        if b != bone and (b.head_local - mirror_head).length < epsilon and (b.tail_local - mirror_tail).length < epsilon:
            return b.name

    return None

################
def find_mirror_bones(armature, bone_names, epsilon=1e-10):
    """
    Find bones at flipped side location.

    Parameters:
    -----------
    armature : bpy.types.Object
      Armature object.

    bone_names : list of strings
      Bone names to find mirrored-bones.

    epsilon : float
      Distance that can be considered close enough.

    Returns:
    --------
    list of strings
      Mirror bone names.
    """
    mirror_bones = [find_mirror_bone(armature, bn, epsilon=epsilon) for bn in bone_names]
    return mirror_bones

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

    # どの骨を移動するかのマスクを作成
    mirror_bones = np.full_like(selection, False)
    mirror_bones[mirror_indices] = True

    # 見えている骨のみ移動する
    visible_bones = np.array([is_bone_visible(b.bone, arma.data)
                              for b in arma.pose.bones], dtype=bool)
    mirror_bones &= visible_bones
    new_translations = np.where(mirror_bones[:, np.newaxis],
                                mirror_translations,
                                translations)
    return new_translations, mirror_bones

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

            new_location = translation_matrix_l.translation
            new_matrix_basis = bone.matrix_basis.copy()
            new_matrix_basis.translation = new_location
            
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
            bone.location = new_location

        # 子のためにデータを保存しておく
        if has_child:
            bone_data[bn] = BoneData(moving, new_matrix, bone.bone.matrix_local)

################
def adjust_bendy_bone_size(arma, bone_names, ratio_z, ratio_x):
    with iu.mode_context(arma, 'OBJECT'):
        for bn in bone_names:
            bone = arma.data.bones[bn]
            size = bone.vector.length
            bone.bbone_z = size * ratio_z
            bone.bbone_x = size * ratio_x
        
################
def compute_bone_epsilon(arma):
    # Using list comprehension to collect all coordinates
    all_coords = [coord for bone in arma.data.bones for coord in (bone.head_local, bone.tail_local)]

    # Convert the list into a numpy array
    all_coords = np.array(all_coords)

    # Calculate the absolute values
    abs_coords = np.abs(all_coords)

    # Find the maximum value
    max_value = np.max(abs_coords)

    # Calculate a very small value compared to max_value
    epsilon = max_value * 1e-3

    return epsilon

################
def rename_bones_for_symmetry(arma, bone_names, epsilon=None):
    """
    指定した骨を、左右対称の位置の骨の名前を考慮しつつリネームする
    """

    # 明示的に OBJECT モードにすることで EditBone を確定させる
    with iu.mode_context(arma, 'OBJECT'):
        pass

    if not bone_names:
        return []

    all_bones = [b.name for b in arma.data.bones]

    # epsilon の計算
    if not epsilon:
        epsilon = compute_bone_epsilon(arma)

    # 狙い通りにリネームするための仕組み
    rename_dic = dict()
    used_names = set(all_bones)
    def rename(bone, new_name):
        nonlocal rename_dic, used_names
        if bone.name == new_name: return
        used_names.discard(bone.name)

        if new_name in used_names:
            basename = new_name
            # (総数 + 1) 回チェックすることで必ず未使用の番号が見つかる
            for idx in range(len(used_names) + 1):
                new_name = f'{basename}.{idx:03d}'
                if new_name not in used_names:
                    break
        used_names.add(new_name)
        rename_dic[bone.name] = new_name

    # 骨のペアに一度に名前を付ける
    def rename_pair(bone_0, bone_1, new_name_0):
        nonlocal rename_dic, used_names
        new_name_1 = iu.flip_side_name(new_name_0)
        if bone_0.name == new_name_0 and bone_1.name == new_name_1: return
        used_names.discard(bone_0.name)
        used_names.discard(bone_1.name)
        #print(f'rename_pair({bone_0.name}, {bone_1.name}, {new_name_0})')

        if new_name_0 in used_names or new_name_1 in used_names:
            basename = iu.plain_name(new_name_0)
            side = 'L' if iu.get_side(new_name_0) > 0 else 'R'
            # (総数 + 1) 回チェックすることで必ず未使用の番号が見つかる
            for idx in range(len(used_names) + 1):
                new_name_0 = f'{basename}.{side}.{idx:03d}'
                new_name_1 = iu.flip_side_name(new_name_0)
                if new_name_0 not in used_names and new_name_1 not in used_names:
                    break
        used_names.add(new_name_0)
        used_names.add(new_name_1)
        rename_dic[bone_0.name] = new_name_0
        rename_dic[bone_1.name] = new_name_1


    # 骨→反対側の骨 の名前の辞書を作る
    other_bone = dict()
    for bn in bone_names:
        bone = arma.data.bones.get(bn)
        if not bone:
            raise ValueError(f'Armature({arma.name}) does not have a bone({bn})')

        if bn in other_bone:
            # 既に登録済みなら何もしない
            continue

        flipped_bone = iu.find_flip_side_name(all_bones, bn)
        if flipped_bone:
            # お互い.L.Rが付いているなら何もしない
            #print(f'Already flipped: {bn} {flipped_bone}')
            continue

        mirrored_bone = find_mirror_bone(arma, bn, epsilon=epsilon)
        if mirrored_bone:
            # 対称位置の骨を発見したので登録する
            #print(f'Find mirror: {bn} {mirrored_bone}')
            other_bone[bn] = mirrored_bone
            continue

        if iu.get_side(bn) != 0:
            # 反対側の骨がないのに .L.R が付いているなら削る
            #print(f'Not mirror: {bn}')
            rename(bone, iu.plain_name(bn))
            
    # それぞれのペアについて、適切な名前を付ける
    for bn_0, bn_1 in other_bone.items():
        bn = [bn_0, bn_1]
        bone = [arma.data.bones[n] for n in bn]

        for side in range(2):
            if bone[side].head_local.x * iu.get_side(bn[side]) > 0 or\
               bone[side].tail_local.x * iu.get_side(bn[side]) > 0:
                # bone[side] に正しい名前が付いている
                basename = iu.plain_name(bn[side])
                break
        else:
            # どちらも正しい名前ではなかったら、1 を元にする
            basename = iu.plain_name(bn[1])

        # 1 の位置を元に適切な名前を付ける
        if (bone[1].head_local.x + bone[1].tail_local.x) * 0.5 < 0:
            rename_pair(bone[1], bone[0], f'{basename}.R')
        else:
            rename_pair(bone[1], bone[0], f'{basename}.L')

    # 一気にリネームする
    result = []
    with iu.mode_context(arma, 'EDIT'):
        # まず、リネームする骨の名前を全てユニークにする
        uuid_dic = dict()
        for bn, new_name in rename_dic.items():
            if bn != new_name:
                #print(f' {bn} -> {new_name}')
                bone = arma.data.edit_bones[bn]
                uuid_name = str(uuid.uuid4())
                uuid_dic[uuid_name] = new_name
                bone.name = uuid_name

        # そして最終的にリネームする
        for uuid_name, new_name in uuid_dic.items():
            bone = arma.data.edit_bones[uuid_name]
            bone.name = new_name
            result.append(new_name)

    # 明示的に OBJECT モードにすることで EditBone を確定させる
    with iu.mode_context(arma, 'OBJECT'):
        pass

    return result

################
def merge_armatures(armature_name0, armature_name1):
    #print(f'Merge {armature_name0} + {armature_name1}')

    arma_0 = iu.ObjectWrapper(armature_name0)
    arma_1 = iu.ObjectWrapper(armature_name1)
    with iu.mode_context(arma_0.obj, 'OBJECT'):
        # Store original names and rename bones of arma_0 using UUID
        original_names = dict()
        for bone in arma_0.obj.data.bones:
            if bone.name in arma_1.obj.data.bones:
                new_name = str(uuid.uuid4())
                original_names[new_name] = bone.name
                #print(f'{new_name} <- {bone.name}')
                bone.name = new_name

        # Join armatures
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = arma_0.obj
        arma_0.select_set(True)
        arma_1.select_set(True)
        bpy.ops.object.join()

        # Rename bones of merged armature back to original names
        for bone in arma_0.obj.data.bones:
            original_name = original_names.get(bone.name)
            if original_name:
                #print(f'{bone.name} -> {original_name}')
                bone.name = original_name
