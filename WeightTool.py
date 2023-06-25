# -*- encoding:utf-8 -*-

import re
import bpy
import bmesh
import numpy as np
from . import internalUtils as iu
from . import mathUtils as mu

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

################
def getSelectedEditableBones():
    return [iu.EditBoneWrapper(eb) for eb in bpy.context.selected_editable_bones]

################
def get_vertex_weights(mesh_obj):
    """
    Get an array of vertex weights.
    The array can be accessed by [vertex index, vertex group index].

    Parameters:
    -----------
    mesh_obj : bpy.types.Object
      Mesh object

    Returns:
    --------
    np.ndarray
      Array of vertex-weights
    """

    number_of_vertices = len(mesh_obj.data.vertices)
    number_of_vertex_groups = len(mesh_obj.vertex_groups)
    vertex_weights = np.zeros((number_of_vertices, number_of_vertex_groups))

    for ii, vertex_group in enumerate(mesh_obj.vertex_groups):
        for jj in range(number_of_vertices):
            try:
                weight = vertex_group.weight(jj)
                vertex_weights[jj, ii] = weight
            except RuntimeError:
                pass

    return vertex_weights

################
def set_vertex_weights(mesh_obj, vertex_weights,
                       which_to_set=None,
                       normalize=False, limit=1e-8, epsilon=1e-10):
    """
    Set vertex weights.

    Parameters:
    -----------
    mesh_obj : bpy.types.Object
      Mesh object

    vertex_weights : np.ndarray
      An array of vertex weights where shape is (number of vertices, number of vertex groups).

    which_to_set : np.ndarray
      Array of bool indicating which vertices to set.
      If None, set all.

    normalize : bool
      Whether to normalize the vertex weights so that they sum to 1.

    limit : float
      Weights less than this are considered 0.

    epsilon : float
      Number sufficiently close to 0 (to avoid division by zero).
    """

    # Limit weights and normalize.
    if normalize:
        vertex_weights = np.where(vertex_weights < limit, 0, vertex_weights)

        total_weights = np.sum(vertex_weights, axis=1)
        vertex_weights = np.where(
            total_weights[:, np.newaxis] < epsilon,
            vertex_weights,
            vertex_weights / (total_weights[:, np.newaxis] + epsilon))

    if which_to_set is None:
        which_to_set = np.full((vertex_weights.shape), True)

    # Clip values in [0..1]
    vertex_weights = np.clip(vertex_weights, 0, 1)

    # Remove vertices with a weight of 0 from the vertex group.
    for jj, vertex_group in enumerate(mesh_obj.vertex_groups):
        zero_verts = vertex_weights[:, jj] < limit
        target = np.logical_and(zero_verts, which_to_set)
        zero_indices = np.where(target)[0].tolist()
        if zero_indices:
            try:
                vertex_group.remove(zero_indices)
            except RuntimeError:
                pass
        
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    bm.verts.ensure_lookup_table()

    # Ensure custom data exists.
    bm.verts.layers.deform.verify()
    deform = bm.verts.layers.deform.active

    # Set each vertex weights.
    nonzero_verts = vertex_weights >= limit
    target = np.logical_and(nonzero_verts, which_to_set)
    nonzero_indices = np.where(target)
    for ii, jj in zip(*nonzero_indices):
        bm.verts[ii][deform][jj] = vertex_weights[ii, jj]

    bm.to_mesh(mesh_obj.data)
    bm.free()

################
def resetWeight(mesh):
    """
    Removes all weights from all vertexGroup.
    Returns if succeeded.

    Parameters
    ----------------
    mesh: ObjectWrapper
    """
    
    #print('resetWeight() mesh:{0}'.format(mesh.name))
    if not mesh or mesh.obj.type != 'MESH':
        return False
    
    result = True
    with iu.mode_context(mesh.obj, 'WEIGHT_PAINT'):
        vertices = [vtx.index for vtx in mesh.obj.data.vertices]
        for vg in mesh.obj.vertex_groups:
            try:
                vg.remove(vertices)
            except:
                result = False
    return result

################################################################
def resetWeightOfSelectedObjects():
    """
    Removes all weights from all vertexGroup of selected objects.
    Returns number of objects.
    """

    result = 0
    for obj in bpy.context.selected_objects:
        mesh = iu.ObjectWrapper(obj)
        if resetWeight(mesh):
            result += 1
    return result

################
def moveWeight(mesh, boneFrom, boneTo):
    """
    Move weight of mesh from boneFrom to boneTo.

    Parameters
    ----------------
    mesh: ObjectWrapper
    boneFrom: EditBoneWrapper or EditBone or Bone
    boneTo: EditBoneWrapper or EditBone or Bone

    """

    # Select mesh and switch to weight-paint-mode
    with iu.mode_context(mesh.obj, 'WEIGHT_PAINT'):
        # Move firstBone's weight to parent
        vgFrom = mesh.obj.vertex_groups.get(boneFrom.name)
        if not vgFrom: return

        vgTo = mesh.obj.vertex_groups.get(boneTo.name)
        if not vgTo: vgTo = mesh.obj.vertex_groups.new(name=boneTo.name)

        indices = []
        for vtx in mesh.obj.data.vertices:
            try:
                weight = vgFrom.weight(vtx.index)
                if weight != 0:
                    vgTo.add([vtx.index], weight, type='ADD')
                    indices.append(vtx.index)
            except: pass
        vgFrom.remove(indices)

################
def getSelectedObjs():
    meshes = []
    armas = []
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            meshes.append(iu.ObjectWrapper(obj))
        elif obj.type == 'ARMATURE':
            armas.append(iu.ObjectWrapper(obj))
    return [meshes, armas]

################################################################
def transferWeights(mesh,
                    weightObj,
                    vertex_group='',
                    invert_vertex_group=False,
                    max_distance=0.01,
                    vert_mapping='POLYINTERP_NEAREST'):
    """
    Transfers vertex weight from weightObj to mesh.
    Returns if succeeded.

    Parameters
    ----------------
    mesh : ObjectWrapper
      Object to which weights are transferred.

    weightObj : ObjectWrapper
      The original object from which the weights are transferred.

    vertex_group : String(never None)
      Vertex group name for selecting the affected areas

    invert_vertex_group : boolean
      Invert vertex group influence

    vert_mapping : String
      Method used to map source vertices to destination ones.
      enum in ['TOPOLOGY', 'NEAREST', 'EDGE_NEAREST', 'EDGEINTERP_NEAREST', 'POLY_NEAREST', 'POLYINTERP_NEAREST', 'POLYINTERP_VNORPROJ'], default 'POLYINTERP_NEAREST'

    max_distance : Number
      Max distance to transfer weights.
    """

    if not mesh or mesh.obj.type != 'MESH' or \
       not weightObj or weightObj.obj.type != 'MESH' or \
           mesh.obj == weightObj:
        return False

    #print(f'transferWeights({mesh.name}, {weightObj.name}, max_distance={max_distance}, vertex_group={vertex_group}({invert_vertex_group}), vert_mapping={vert_mapping})')

    with iu.mode_context(mesh.obj, 'OBJECT'):
        bpy.ops.object.modifier_add(type='DATA_TRANSFER')
        mname = bpy.context.object.modifiers[-1].name
        mod = bpy.context.object.modifiers[mname]
        bpy.ops.object.modifier_move_to_index(modifier=mname, index=0)

        mod.object = weightObj.obj
        mod.use_vert_data = True
        mod.data_types_verts = {'VGROUP_WEIGHTS'}
        mod.vertex_group = vertex_group
        mod.invert_vertex_group = invert_vertex_group
        mod.vert_mapping = vert_mapping
        if max_distance:
            mod.use_max_distance = True
            mod.max_distance = max_distance
        bpy.ops.object.datalayout_transfer(modifier=mname)
        bpy.ops.object.modifier_apply(modifier=mname)

    return True

################################################################
def transferWeightsForSelectedObjects(weightObj,
                                      vertex_group='',
                                      invert_vertex_group=False,
                                      max_distance=0.01,
                                      vert_mapping='POLYINTERP_NEAREST'):
    """
    Transfers vertex weight from weightObj to selected mesh.
    Returns number of meshes.    

    Parameters
    ----------------
    weightObj : ObjectWrapper
      The original object from which the weights are transferred.

    vertex_group : String(never None)
      Vertex group name for selecting the affected areas

    invert_vertex_group : boolean
      Invert vertex group influence

    vert_mapping : String
      Method used to map source vertices to destination ones.
      enum in ['TOPOLOGY', 'NEAREST', 'EDGE_NEAREST', 'EDGEINTERP_NEAREST', 'POLY_NEAREST', 'POLYINTERP_NEAREST', 'POLYINTERP_VNORPROJ'], default 'POLYINTERP_NEAREST'

    max_distance : Number
      Max distance to transfer weights.
    """

    result = 0
    for obj in bpy.context.selected_objects:
        if obj != weightObj.obj:
            mesh = iu.ObjectWrapper(obj)
            if transferWeights(mesh, weightObj, max_distance=max_distance, vert_mapping=vert_mapping, vertex_group=vertex_group, invert_vertex_group=invert_vertex_group):
                result += 1
    return result

################################################################
def cleanupWeights(mesh, affectBoneMax=4):
    """
    Cleanups vertex weight.
    Returns if succeeded.

    Parameters
    ----------------
    mesh : ObjectWrapper
      Object to modify weights.

    affectBoneMax : Integer
      Number of bones affecting.

    """

    if not mesh or mesh.obj.type != 'MESH':
        return False

    # delete unnecessary vertex groups before normalize
    cleanupVertexGroups(mesh)

    # cleanup vertex weight
    with iu.mode_context(mesh.obj, 'WEIGHT_PAINT'):
        bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0.001)
        bpy.ops.object.vertex_group_limit_total(limit=affectBoneMax)
        bpy.ops.object.vertex_group_normalize_all()
        bpy.ops.object.vertex_group_sort(sort_type='BONE_HIERARCHY')

    return True

################################################################
def cleanupWeightsOfSelectedObjects(affectBoneMax=4):
    """
    Cleanups vertex weight of selected mesh.
    Returns number of meshes.    

    Parameters
    ----------------
    affectBoneMax : Integer
      Number of bones affecting.

    """

    result = 0
    for obj in bpy.context.selected_objects:
        mesh = iu.ObjectWrapper(obj)
        if cleanupWeights(mesh, affectBoneMax=affectBoneMax):
            result += 1
    return result

################################################################
def equalizeVertexWeightsForMirroredBones(mesh):
    """
    Equalizes the weights of the selected vertices to the left and right.
    Returns number of equalized vertices.

    Parameters
    ----------------
    mesh : ObjectWrapper
      mesh object to operate

    """

    if not mesh or mesh.obj.type != 'MESH':
        return 0

    with iu.mode_context(mesh.obj, 'OBJECT'):
        # Make sides_dictionary from vertex groups
        # eg. vg_sides[vertex_groups['hoge_L'].index] -> vertex_groups['hoge_R'].index
        vg_sides = dict()
        vg_names = mesh.obj.vertex_groups.keys()
        for vg in mesh.obj.vertex_groups:
            if vg.index not in vg_sides:
                flip_name = iu.find_flip_side_name(vg_names, vg.name)
                if flip_name:
                    flip_vg = mesh.obj.vertex_groups[flip_name]
                    vg_sides[flip_vg.index] = vg.index
        #print(vg_sides)

        bm = bmesh.new()
        bm.from_mesh(mesh.obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # Ensure custom data exists.
        bm.verts.layers.deform.verify()
        deform = bm.verts.layers.deform.active

        result = 0

        for vtx in bm.verts:
            if vtx.select:
                equalized = False
                gr = vtx[deform]
                for idx_L, idx_R in vg_sides.items():
                    value_L = gr.get(idx_L)
                    value_R = gr.get(idx_R)
                    if value_L:
                        if value_R:
                            gr[idx_L] = gr[idx_R] = (value_L + value_R) * 0.5
                            equalized = True
                        else:
                            gr[idx_L] = gr[idx_R] = value_L * 0.5
                            equalized = True
                    else:
                        if value_R:
                            gr[idx_L] = gr[idx_R] = value_R * 0.5
                            equalized = True
                if equalized:
                    result += 1

        bm.to_mesh(mesh.obj.data)
        bm.free()

    return result

################################################################
def cleanupVertexGroups(mesh):
    """
    Deletes vertex groups that have no corresponding bones.
    Returns names of the deleted vertex groups.

    Parameters
    ----------------
    mesh : ObjectWrapper
      mesh object to operate

    """

    if not mesh or mesh.obj.type != 'MESH' or not mesh.obj.parent or mesh.obj.parent.type != 'ARMATURE':
        return []

    result = []
    bones = mesh.obj.parent.data.bones
    vgs = mesh.obj.vertex_groups

    for vg in vgs:
        if not bones.get(vg.name):
            result.append(vg.name)

    for vgName in result:
        vgs.remove(vgs[vgName])

    print('Deleted vertex groups: ', sorted(result))

    return result

################################################################
def findAncestorDeformerBone(bone, excludeBones):
    if not excludeBones:
        excludeBones = dict()
    result = None
    while bone:
        if bone.bone.use_deform and bone.name not in excludeBones:
            return bone
        bone = bone.parent

################################################################
def dissolveWeightedBones(arma, boneNames):
    """
    Transfers the weight of the specified bones to the parent and dissolves them.
    Returns dictionary of bone to ancestor bone.

    Parameters
    ----------------
    arma : ObjectWrapper
        armature

    boneNames : Array of String
        Names of bones to be dissolved.

    """
    
    # 1st step
    # find ancestor bone to which vertex-weight to be moved
    with iu.mode_context(arma.obj, 'POSE'):
        targetBones = dict()
        for boneName in boneNames:
            bone = arma.obj.pose.bones[boneName]
            toBone = findAncestorDeformerBone(bone.parent, boneNames)
            if toBone:
                targetBones[boneName] = toBone.name
            else:
                print(f'Warning: Failed to find ancestor bone of {boneName}!')
                return None
        #print(targetBones)

    # 2nd step
    # move weights
    #print('---------------- 2nd step')
    objs = iu.getAllChildMeshes(arma.obj)
    for obj in objs:
        for boneFrom, boneTo in targetBones.items():
            if boneTo:
                moveWeight(obj,
                           iu.EditBoneWrapper(boneFrom),
                           iu.EditBoneWrapper(boneTo))

    # 3rd step
    # delete targetBones
    #print('---------------- 3rd step')
    bpy.context.view_layer.objects.active = arma.obj
    with iu.mode_context(arma.obj, 'EDIT'):
        bpy.ops.armature.reveal()
        bpy.ops.armature.select_all(action='DESELECT')
        for bone in targetBones:
            #print(bone)
            iu.EditBoneWrapper(bone).select_set(True)
        bpy.ops.armature.delete()

    #print('---------------- finished')
    
    return targetBones

################################################################
def set_weight_for_selected_bones(mesh_object, armature_object, weight):
    # Ensure the objects are of the correct type
    assert mesh_object.type == 'MESH'
    assert armature_object.type == 'ARMATURE'
    assert mesh_object.mode == 'EDIT'

    # Get the vertex groups corresponding to the selected bones
    vg_indices = []
    bone_names = []
    for bone in armature_object.data.bones:
        if bone.select:
            if not bone.use_deform:
                return 0, None, iface_('{bone_name} is not a deform bone.').format(bone_name=bone.name)
            vg = mesh_object.vertex_groups.get(bone.name)
            if not vg:
                vg = mesh_object.vertex_groups.new(name=bone.name)
            vg_indices.append(vg.index)
            bone_names.append(bone.name)

    if not vg_indices:
        return 0, None, iface_('No bones to be set in vertex group.')

    # Create a BMesh from the mesh
    bm = bmesh.from_edit_mesh(mesh_object.data)
    bm.verts.ensure_lookup_table()

    # Ensure custom data exists.
    bm.verts.layers.deform.verify()
    deform = bm.verts.layers.deform.active

    # Set the weight of each selected vertex
    count_verts = 0
    for vert in bm.verts:
        if vert.select:
            count_verts += 1
            gr = vert[deform]
            for vg_index in vg_indices:
                gr[vg_index] = weight

    # Write the BMesh back to the mesh
    bmesh.update_edit_mesh(mesh_object.data)

    return count_verts, bone_names, ''

################
# FIXME
# mathUtils の falloff を ndarray に対応させて使いたい
def calculate_factors(distances, radius):
    values = distances / radius
    factors = np.where(values <= 1, (1 - values) ** 2, 0)
    return factors

################
def calculate_vertex_distances_by_poligon_connections(mesh_obj,
                                                      which_to_use=None,
                                                      inf=1e10):
    """
    Calculates the distance between vertices on the same polygon.

    Parameters:
    -----------
    mesh_obj : bpy.types.Object
      Mesh object

    which_to_use : np.ndarray
      Array of bools indicating which vertices to use.

    inf : float
      A sufficiently large value.

    Returns:
    --------
    np.ndarray
      Distance between vertices.
      Accessible via [vertex_index, vertex_index].
    """

    # Get the mesh data from the object
    mesh = mesh_obj.data
    
    # Create a bmesh from the object mesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    
    number_of_vertices = len(mesh.vertices)
    
    # Initialize the distances array with infinite distances
    distances = np.full((number_of_vertices, number_of_vertices), inf)
    
    # Set the diagonal to zero
    np.fill_diagonal(distances, 0)
    
    max_distance = 0

    if which_to_use is None:
        which_to_use = np.full((number_of_vertices,), True)

    # Iterate over each face in the mesh
    for face in bm.faces:
        # Calculate the distances between each pair of vertices in the face
        for ii in range(len(face.verts)):
            vert_i = face.verts[ii]
            if which_to_use[vert_i.index]:
                for jj in range(ii + 1, len(face.verts)):
                    vert_j = face.verts[jj]
                    if which_to_use[vert_j.index]:
                        # Compute the distance between the two vertices
                        distance = (vert_i.co - vert_j.co).length

                        # If the computed distance is less than the
                        # current distance in the array, update the array
                        if distance < distances[vert_i.index, vert_j.index]:
                            distances[vert_i.index, vert_j.index] = distance
                            distances[vert_j.index, vert_i.index] = distance
                            max_distance = max(max_distance, distance)
    
                            # Clear and free the bmesh
    bm.free()
    
    return distances, max_distance

################
def smooth_vertex_weights_falloff(mesh_obj,
                                  count=1,
                                  radius=1.0,
                                  normalize=False,
                                  limit=1e-8,
                                  epsilon=1e-10):
    """
    選択した頂点の頂点ウェイトを、ポリゴンの接続を考慮した上で、
    falloff 関数を使って平滑化する。

    Parameters:
    -----------
    mesh_obj : bpy.types.Object
      メッシュオブジェクト

    radius : float
      falloff をかける範囲(m)

    count : int
      平滑化をかける回数

    normalize : bool
      最終的に正規化するかどうか

    limit : float
      頂点ウェイトがこれ以下になった頂点を頂点グループから外す

    epsilon : float
      十分に小さい値(ゼロ除算回避用)
    """

    # 選択された頂点を得る
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    bm.verts.ensure_lookup_table()
    selected_verts = np.array([v.select for v in bm.verts])
    bm.free()

    # パラメータの設定
    distances, max_distance =\
        calculate_vertex_distances_by_poligon_connections(
            mesh_obj, which_to_use=selected_verts)
    #radius = max_distance * radius_factor + epsilon
    factors = calculate_factors(distances, radius)
    vertex_weights = get_vertex_weights(mesh_obj)

    # スムージング処理
    for _ in range(count):
        vertex_weights = np.max(
            vertex_weights * factors[:, None, :, None],
            axis=-2)
        vertex_weights = np.squeeze(vertex_weights, axis=1)

    set_vertex_weights(mesh_obj, vertex_weights,
                       which_to_set=selected_verts[:, np.newaxis],
                       normalize=normalize,
                       limit=limit,
                       epsilon=epsilon)
    
################
def smooth_vertex_weights_least_square(mesh_obj,
                                       count=1,
                                       strength=0.5,
                                       normalize=False,
                                       limit=1e-8,
                                       epsilon=1e-10):
    """
    選択した頂点の頂点ウェイトを、ポリゴンの接続を考慮した上で、
    最小二乗法を使って平滑化する。

    Parameters:
    -----------
    mesh_obj : bpy.types.Object
      メッシュオブジェクト

    strength : float
      平滑化の強さ

    count : int
      平滑化をかける回数

    normalize : bool
      最終的に正規化するかどうか

    limit : float
      頂点ウェイトがこれ以下になった頂点を頂点グループから外す

    epsilon : float
      十分に小さい値(ゼロ除算回避用)
    """

    orig_vertex_weights = get_vertex_weights(mesh_obj)

    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    number_of_vertex_groups = len(mesh_obj.vertex_groups)
    number_of_vertices = len(bm.verts)
    number_of_faces = len(bm.faces)

    # 選択していない頂点のウェイトを 0 にする
    selected_verts = np.array([v.select for v in bm.verts])
    vertex_weights = np.where(selected_verts[:, np.newaxis],
                              orig_vertex_weights, 0)

    # 計算用の配列を一旦全て確保
    vert_points_h = mu.append_homogeneous_coordinate(
        np.array([np.array(v.co) for v in bm.verts]))
    centroids_h = np.zeros((number_of_faces, 4))
    weight_at_centroids = np.zeros((number_of_faces,))
    new_vertex_weights = vertex_weights.copy()

    for _ in range(count):
        # 面ごとの頂点ウェイトの重心位置を計算する
        for vg_idx in range(number_of_vertex_groups):
            # ポリゴンごとに、頂点ウェイトの重心とその値を計算する
            for face_idx in range(number_of_faces):
                face = bm.faces[face_idx]
                indices = np.array([v.index for v in face.verts])
                points_h = vert_points_h[indices]
                weights = vertex_weights[indices, vg_idx]

                try:
                    centroid_h = np.average(points_h, axis=0, weights=weights)
                except ZeroDivisionError:
                    centroid_h = np.append(
                        np.array(face.calc_center_median_weighted()), 1)

                try:
                    weight = mu.calc_weight_least_squares(
                        points_h, weights, centroid_h)
                except ZeroDivisionError:
                    weight = np.average(weights, axis=0)

                centroids_h[face_idx] = centroid_h
                weight_at_centroids[face_idx] = weight

            # 頂点ごとに、含まれるポリゴンの平均からウェイトを計算する
            for vert in bm.verts:
                face_indices = np.array([f.index for f in vert.link_faces])
                face_centroids_h = centroids_h[face_indices]
                face_weights = weight_at_centroids[face_indices]
                point_h = vert_points_h[vert.index]

                try:
                    weight = mu.calc_weight_least_squares(
                        face_centroids_h, face_weights, point_h)
                except (ZeroDivisionError, ValueError):
                    weight = np.average(face_weights, axis=0)

                new_vertex_weights[vert.index, vg_idx] = weight

        # 新しい頂点ウェイトを前の頂点ウェイトと補間して計算
        smooth_strength = (strength, 1 - strength)
        new_vertex_weights = np.average((new_vertex_weights, vertex_weights),
                                        weights=smooth_strength,
                                        axis=0)
        vertex_weights = np.where(selected_verts[:, np.newaxis],
                                  new_vertex_weights, 0)
        
    set_vertex_weights(mesh_obj, vertex_weights,
                       which_to_set=selected_verts[:, np.newaxis],
                       normalize=normalize,
                       limit=limit,
                       epsilon=epsilon)

    bm.free()
