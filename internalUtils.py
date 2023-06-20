# -*- encoding:utf-8 -*-

import bpy
import bmesh
import gpu
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
import mathutils
from mathutils import (
    Vector,
    Matrix,
)
from contextlib import contextmanager
import traceback
import numpy as np
import uuid
import json
import re
from . import mathUtils as mu
from dataclasses import dataclass

################################################################
class ObjectWrapper:
    """
    For safety usage, this class will wrap blender's object.
    """

    _name = None

    def __init__(self, name):
        if isinstance(name, str):
            self._name = name
        elif isinstance(name, bpy.types.Object):
            self._name = name.name

    @property
    def name(self):
        return self._name

    @property
    def obj(self):
        return bpy.data.objects.get(self._name)

    def __repr__(self):
        return '<ObjectWrapper {0}>'.format(self._name)

    def select_set(self, tf):
        obj = self.obj
        if obj:
            obj.select_set(tf)

    def rename(self, newName):
        obj = self.obj
        if obj:
            obj.name = newName
            self._name = newName

    def __bool__(self):
        return isinstance(self._name, str) and self.obj is not None

################################################################
class EditBoneWrapper:
    _name = None

    def __init__(self, name):
        if isinstance(name, str):
            self._name = name
        elif isinstance(name, bpy.types.EditBone):
            self._name = name.name

    @property
    def name(self):
        return self._name

    @property
    def obj(self):
        return bpy.context.active_object.data.edit_bones.get(self._name)

    def __repr__(self):
        return '<EditBoneWrapper {0}>'.format(self._name)

    def select_set(self, tf):
        obj = self.obj
        if obj:
            obj.select = tf
            obj.select_head = tf
            obj.select_tail = tf

    def rename(self, newName):
        obj = self.obj
        if obj:
            obj.name = newName
            self._name = newName

    def __bool__(self):
        return isinstance(self._name, str) and self.obj is not None

################################################################
@contextmanager
def mode_context(obj, mode):
    safe_obj = ObjectWrapper(obj)
    prev_active = ObjectWrapper(bpy.context.view_layer.objects.active)
    prev_mode = obj.mode
    bpy.context.view_layer.objects.active = obj

    if mode == 'EDIT' and prev_mode == 'EDIT':
        print('vvvvvvvvvvvvvvvv Ensure Edit Data')
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode=mode)

    try:
        yield  # ブロック内の処理を実行
    finally:
        # 元のモードに戻す
        if safe_obj and prev_mode:
            bpy.context.view_layer.objects.active = obj
            if mode == 'EDIT' and prev_mode == 'EDIT':
                print('^^^^^^^^^^^^^^^^ Ensure Edit Data')
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode=prev_mode)

        # 元のアクティブに戻す
        if prev_active:
            bpy.context.view_layer.objects.active = prev_active.obj

################################################################
def replaceImagePath(strFrom=None , strTo=None):
    """
    Replaces the portion of all image paths matching strFrom from the beginning with strTo.

    Parameters
    ----------------
    strFrom : String
    	Path to replace from.
    strTo : String
        Path to replace to.
    """

    for image in bpy.data.images:
        if image.filepath.startswith(strFrom):
            newFilePath = image.filepath.replace(strFrom, strTo, 1)
            #print('filepath:', image.filepath, 'newFilePath:', newFilePath)
            if image.filepath != newFilePath:
                image.filepath = newFilePath
                #print('replaced')
                image.reload()
                #print('reloaded')


################################################################
def replaceTextPath(strFrom=None , strTo=None):
    """
    Replaces the portion of all text paths matching strFrom from the beginning with strTo.

    Parameters
    ----------------
    strFrom : String
    	Path to replace from.
    strTo : String
        Path to replace to.
    """

    for text in bpy.data.texts:
        if text.filepath.startswith(strFrom):
            newFilePath = text.filepath.replace(strFrom, strTo, 1)
            if text.filepath != newFilePath:
                #print('filepath:', text.filepath, 'newFilePath:', newFilePath)
                text.filepath = newFilePath


################################################################
def listupImagePath():
    """
    Returns all image paths.
    """

    return sorted([image.filepath for image in bpy.data.images])

################################################################
def listupTextPath():
    """
    Returns all text paths.
    """

    return sorted([text.filepath for text in bpy.data.texts])

################################################################
def getAllChildren(obj, types, selectable=True):
    objs = set()
    for co in obj.children_recursive:
        if co.type in types:
            if not(selectable and co not in bpy.context.selectable_objects):
                objs.add(ObjectWrapper(co))
    return objs

def getAllChildMeshes(obj, selectable=True):
    return getAllChildren(obj, ['MESH'], selectable=selectable)

def getAllChildArmatures(obj, selectable=True):
    return getAllChildren(obj, ['ARMATURE'], selectable=selectable)

################
def selectAllChildren(obj, types):
    objs = getAllChildren(obj, types, selectable=True)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)

    return objs

def selectAllChildMeshes(obj):
    return selectAllChildren(obj, ['MESH'])

def selectAllChildArmatures(obj):
    return selectAllChildren(obj, ['ARMATURE'])

################################################################
def unhideVertsAndApplyFunc(meshObj, func):
    """
    Unhide and select all vertices, and applies function.

    Parameters
    ----------------
    meshObj: Object
      Mesh object

    func : Function
      Function to apply
    """

    if not meshObj or meshObj.type != 'MESH':
        return

    with mode_context(meshObj, 'EDIT'):
        mesh = meshObj.data
        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.select_mode = set(['VERT'])

        for vtx in bm.verts:
            # save hide status
            vtx.tag = vtx.hide
            # unhide
            vtx.hide_set(False)
            # select
            vtx.select_set(True)

        bmesh.update_edit_mesh(mesh)
        func()

        for vtx in bm.verts:
            # restore hide status
            vtx.hide_set(vtx.tag)

        bmesh.update_edit_mesh(mesh)

################
def propagateShapekey(meshObj, shapekey, remove_shapekey=True):
    """
    Applies shapekey to all other shape keys.

    Parameters
    ----------------
    meshObj: Object
      Mesh object

    shapekey: String
      Name of shapekey to propagate

    remove_shapekey: Boolean
      Whether to delete the shapekey
    """

    idx = bpy.context.active_object.data.shape_keys.key_blocks.find(shapekey)
    if idx < 0:
        print(f'Failed to find shapekey({shapekey})')
    else:
        with mode_context(meshObj, 'OBJECT'):
            bpy.context.active_object.active_shape_key_index = idx
            unhideVertsAndApplyFunc(meshObj, bpy.ops.mesh.shape_propagate_to_all)

            if remove_shapekey:
                bpy.ops.object.shape_key_remove(all=False)
            
################
def blendShapekeyToBasis(meshObj, shapekey, blend=1.0, remove_shapekey=True):
    """
    Applies shapekey to basis(shapekey with index=0).

    Parameters
    ----------------
    meshObj: Object
      Mesh object

    shapekey: String
      Name of shapekey to propagate

    remove_shapekey: Boolean
      Whether to delete the shapekey
    """

    idx = bpy.context.active_object.data.shape_keys.key_blocks.find(shapekey)
    if idx < 0:
        print(f'Failed to find shapekey({shapekey})')
    else:
        with mode_context(meshObj, 'OBJECT'):
            bpy.context.active_object.active_shape_key_index = 0
            unhideVertsAndApplyFunc(meshObj,
                                    lambda: bpy.ops.mesh.blend_from_shape(shape=shapekey, blend=1.0, add=False))

            if remove_shapekey:
                bpy.context.active_object.active_shape_key_index = idx
                bpy.ops.object.shape_key_remove(all=False)

################
def remove_isolated_edges_and_vertices(obj):
    """
    Remove vertices and edges that are not part of any face.

    Parameters
    ----------
    obj : bpy.types.Object
        The active mesh object in Edit mode.
    """

    if not obj or obj.type != 'MESH':
        raise ValueError('Object should be a mesh object')

    with mode_context(obj, 'EDIT'):
        # Create a BMesh from the object's mesh data
        bm = bmesh.from_edit_mesh(obj.data)

        # Find and remove edges not part of any face
        edges_to_remove = set(e for e in bm.edges if not e.link_faces)
        bmesh.ops.delete(bm, geom=list(edges_to_remove), context='EDGES')

        # Find and remove vertices not part of any face
        vertices_to_remove = set(v for v in bm.verts if not v.link_faces)
        bmesh.ops.delete(bm, geom=list(vertices_to_remove), context='VERTS')

        # Update the mesh with the changes
        bmesh.update_edit_mesh(obj.data)

################
def image_to_alpha_array(image: bpy.types.Image, interval: int) -> np.ndarray:
    """
    Extracts the alpha channel from the input image and thins it by the specified interval.

    Parameters
    ----------
    image : bpy.types.Image
        The input image from which the alpha channel will be extracted.
    interval : int
        The interval at which the alpha channel will be thinned.
        For example, an interval of 3 will thin the image by 1/3.

    Returns
    -------
    np.ndarray
        A 2D numpy array containing the thinned alpha channel.

    Examples
    --------
    >>> image = bpy.data.images['your_image_name']
    >>> interval = 3
    >>> alpha_array = image_to_alpha_array(image, interval)
    >>> print(alpha_array)
    """
    # Convert the input image to a NumPy array and extract the alpha channel
    image_np = np.array(image.pixels[:]).reshape((image.size[1], image.size[0], 4))
    alpha_channel = image_np[:, :, 3]

    # Thin the image by the specified interval
    thinned_alpha_array = alpha_channel[::interval, ::interval]

    return thinned_alpha_array

################
def scan_face_alpha(face, uv_layer, alpha_array, alpha_threshold=0.5):
    width, height = alpha_array.shape

    st = np.array([loop[uv_layer].uv for loop in face.loops])
    st[:, 0] = width  * st[:, 0]
    st[:, 1] = height * st[:, 1]
    
    for idx in range(2, len(st)):
        triangle = np.array([st[0], st[idx - 1], st[idx]])

        s_min, t_min = np.amin(triangle, axis=0)
        s_max, t_max = np.amax(triangle, axis=0)

        s_size = int(s_max - s_min + 1)
        t_size = int(t_max - t_min + 1)

        ss, tt = np.meshgrid(np.linspace(s_min, s_max, s_size),
                             np.linspace(t_min, t_max, t_size))

        points = np.vstack((ss.ravel(), tt.ravel())).T
        indices = np.where(np.all(np.dot(triangle - points[:, None], [-1, 1]) <= 0, axis=1))

        mesh_points = np.vstack((np.array([np.mean(triangle, axis=0)]), points[indices[0]])).astype(int)
        
        if (alpha_array[np.mod(mesh_points[:, 1], height), np.mod(mesh_points[:, 0], width)] > alpha_threshold).any():
            return True
    return False

################
def collectAllVisibleObjects():
    """
    Collect all visible objects in the current view layer and all collections.

    Returns
    -------
    set
        A set of all visible objects.
    """
    result = set(bpy.context.view_layer.objects)
    for collection in bpy.data.collections:
        result.update(collection.objects)
    return result

################
def removeObject(obj):
    for collection in obj.users_collection:
        collection.objects.unlink(obj)
    bpy.data.objects.remove(obj)

################
def findCollectionIn(obj):
    for collection in obj.users_collection:
        if obj.name in collection.objects:
            return collection
        
    return None

################
def copyAttr(src, dst, attrs):
    for attr in attrs:
        setattr(dst, attr, getattr(src, attr))

################
def setupObject(obj, parent, parent_type, parent_bone, matrix_world):
    if not parent:
        matrix_parent = Matrix()
    else:
        if parent_type != 'BONE':
            matrix_parent = parent.matrix_world
        else:
            pbone = parent.pose.bones[parent_bone]
            mtx = pbone.matrix.copy()
            mtx.translation = pbone.tail
            matrix_parent = parent.matrix_world @ mtx

    # Calc matrix
    matrix_parent_inverse = matrix_parent.inverted()
    matrix_basis = matrix_world
    matrix_local = matrix_parent_inverse @ matrix_basis
    # matrix_world = matrix_parent @ matrix_local

    # Store result
    #obj.location = location
    obj.parent = parent
    if parent:
        obj.parent_type = parent_type
        obj.parent_bone = parent_bone
    obj.matrix_parent_inverse = matrix_parent_inverse
    obj.matrix_basis = matrix_basis
    obj.matrix_local = matrix_local
    obj.matrix_world = matrix_world

################
def convertEmptyToSphere(empty, u_segments=16, v_segments=8, keep_original=False):
    # 大きさを計算
    radius = empty.empty_display_size

    # 新しいメッシュデータを作成
    mesh_data = bpy.data.meshes.new('sphere_mesh')

    # BMeshオブジェクトを作成して球を生成
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm,
                              u_segments=u_segments,
                              v_segments=v_segments,
                              radius=radius)

    # BMeshをメッシュデータに変換
    bm.to_mesh(mesh_data)
    bm.free()

    # 新しいオブジェクトを作成
    new_sphere = bpy.data.objects.new(str(uuid.uuid4()), mesh_data)

    # 行列を計算
    setupObject(new_sphere,
                empty.parent,
                empty.parent_type,
                empty.parent_bone,
                empty.matrix_world)

    # オブジェクトをシーンにリンク
    collection = findCollectionIn(empty)
    collection.objects.link(new_sphere)

    nameSave = empty.name

    # 元のエンプティを削除
    if not keep_original:
        removeObject(empty)

    new_sphere.name = nameSave

    return new_sphere

################
def convertSphereToEmpty(sphere, keep_original=False):
    # 大きさを計算
    mesh = sphere.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    mtx = sphere.matrix_world
    verts = [mtx @ vtx.co for vtx in bm.verts]
    try:
        radius, center = mu.calcFit(np.array(verts))
        radius /= sphere.matrix_world.median_scale

    except Exception as e:
        traceback.print_exc()
        return

    # 新しい EMPTY を作成
    new_empty = bpy.data.objects.new(str(uuid.uuid4()), None)

    # ワールド行列を計算
    mtx = sphere.matrix_world.copy()
    mtx.translation = center

    # 行列を計算
    setupObject(new_empty,
                sphere.parent,
                sphere.parent_type,
                sphere.parent_bone,
                mtx)

    # エンプティの設定
    new_empty.empty_display_type = 'SPHERE'
    new_empty.empty_display_size = radius

    # オブジェクトをシーンにリンク
    collection = findCollectionIn(sphere)
    collection.objects.link(new_empty)

    nameSave = sphere.name

    # 元のエンプティを削除
    if not keep_original:
        removeObject(sphere)

    new_empty.name = nameSave

    return new_empty

################
def applyEmptyScale(empty):
    size = empty.empty_display_size * empty.matrix_basis.median_scale
    mtx = empty.matrix_basis.normalized()

    empty.matrix_basis = mtx
    empty.empty_display_size = size

################
# コレクションに含まれる全てのアーマチュアの名前を取得する
def get_armature_names(collection):
    collections = [collection]
    collections.extend(collection.children_recursive)

    result = []
    for col in collections:
        for obj in col.objects:
            if obj.type == 'ARMATURE':
                result.append(obj.name)
    return result

################
# インスタンスの実体化
# コレクションインスタンスでアーマチュアが実体化された場合、アクションも復元する
def instance_to_real(instance, rtol=1e-5, atol=1e-5):
    instance_name = instance.name

    # 親のコレクションを保存しておく
    collection_index = bpy.data.collections.find(instance.users_collection[0].name)
    if collection_index < 0:
        parent_collection = bpy.context.scene.collection
    else:
        parent_collection = bpy.data.collections[collection_index]

    # コレクションのインスタンスなら、元のアーマチュアの名前を控えておく
    if instance.instance_type != 'COLLECTION':
        armatures = None
    else:
        original_collection = instance.instance_collection
        armatures = get_armature_names(original_collection)

    # インスタンスを選択
    bpy.ops.object.select_all(action='DESELECT')
    instance.select_set(True)

    # インスタンス化されたオブジェクトを実体化する
    bpy.ops.object.duplicates_make_real(use_base_parent=True, use_hierarchy=True)

    # 実体化されたオブジェクトを全て選択し、個別処理を行う
    bpy.data.objects[instance_name].select_set(True)
    objects = [obj.name for obj in bpy.context.selected_objects]
    for objName in objects:
        obj = bpy.data.objects[objName]

        # コレクションを移動
        obj.users_collection[0].objects.unlink(obj)
        parent_collection.objects.link(obj)

        # アクションをコピー
        if obj.type == 'ARMATURE':
            matrix_local = np.array(obj.matrix_local)
            for armaName in armatures:
                arma = bpy.data.objects[armaName]
                # ローカル行列が十分に近いならば元のアーマチュアと見なす
                if arma.data == obj.data and\
                   np.allclose(np.array(arma.matrix_local), matrix_local, rtol=rtol, atol=atol):
                    # print("Found")
                    if arma.animation_data:
                        if not obj.animation_data:
                            obj.animation_data_create()
                        obj.animation_data.action = arma.animation_data.action
                    break
    return instance_name

################
# 選択したインスタンスオブジェクトを実体化する
# アクションも復元する
def selected_instances_to_real(rtol=1e-5, atol=1e-5):
    result = []
    objects = [ObjectWrapper(obj) for obj in bpy.context.selected_objects]
    for obj in objects:
        if obj.obj.instance_type != 'NONE':
            result.append(instance_to_real(obj.obj, rtol=rtol, atol=atol))
    return result

################
def triangulate_with_center_vertex(obj, method='AREA'):
    """
    Triangulates selected faces of a given object by adding a new vertex at the center. 

    The function works by creating a new vertex in the center of each selected face and 
    creating new triangular faces from the center vertex to each edge of the original face.

    Parameters
    ----------
    obj : bpy.types.Object
        The object to triangulate. The object should be in edit mode and have some faces selected.
    method : string
        Method for finding the center.
        'ARITHMETIC' : Find the center from the average of the coordinates of each vertex.
        'AREA' : Find the center by considering the area of the polygon.
        'MEDIAN_WEIGHTED' : Find the center of the face weighted by edge lengths.

    Returns
    -------
    integer
        Number of triangles created.
    """

    num_triangulated_faces = 0

    with mode_context(obj, 'OBJECT'):
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        faces = [f for f in bm.faces if f.select]
        for face in faces:
            # Calculate center
            if method == 'ARITHMETIC':
                coords = np.array([v.co for v in face.verts])
                center = Vector(mu.arithmetic_centroid_of_polygon(coords))

            elif method == 'AREA':
                coords = np.array([v.co for v in face.verts])
                center = Vector(mu.area_centroid_of_polygon(coords))

            elif method == 'MEDIAN_WEIGHTED':
                center = face.calc_center_median_weighted()

            else:
                raise ValueError(f'Illegal methd: {method}')

            # Split first face and make center vertex
            loop0 = face.loops[0]
            loop1 = loop0.link_loop_next
            new_face, new_loop = bmesh.utils.face_split(face,
                                                        loop0.vert,
                                                        loop1.vert,
                                                        coords=[center])
            new_loop = new_loop.link_loop_next
            center_vert = new_loop.vert
            new_face.select = True
            num_triangulated_faces += 2

            # Split new_face into triangles
            while len(new_face.verts) > 3:
                next_vert = new_loop.link_loop_next.link_loop_next.vert
                new_face, new_loop = bmesh.utils.face_split(new_face,
                                                            center_vert,
                                                            next_vert,
                                                            use_exist=False)
                new_face.select = True
                num_triangulated_faces += 1

        # Recalculate normals
        bm.normal_update()

        # Update the mesh data
        bm.to_mesh(obj.data)
        bm.free()

    return num_triangulated_faces

################
def format_list_as_string(lst, tab=4, indent_level=0):
    formatted = json.dumps(sorted(lst), indent=tab)
    indented = re.sub('^', ' ' * tab * indent_level, formatted, flags=re.MULTILINE)
    return indented

################
def findfirst_selected_object(type):
    return next((obj for obj in bpy.context.selected_objects if obj.type == type), None)

################
class BlenderGpuState:
    _state_names = {
        'blend': {'multi_args': False},
        'depth_mask': {'multi_args': False},
        'depth_test': {'multi_args': False},
        'line_width': {'multi_args': False},
        'scissor': {'multi_args': True},
        'viewport': {'multi_args': True},
    }

    def __init__(self, **kwargs):
        self._original_state = {}
        self._new_state = kwargs

    def _set_gpu_state(self, state_name, state):
        set_func = getattr(gpu.state, f'{state_name}_set')
        assert set_func
        #print(state_name, self._state_names[state_name]['multi_args'])
        if self._state_names[state_name]['multi_args']:
            set_func(*state)
        else:
            set_func(state)

    def __enter__(self):
        for state_name in self._state_names.keys():
            # Save the current GPU state
            self._original_state[state_name] = getattr(gpu.state, f'{state_name}_get')()

        for state_name, state in self._new_state.items():
            # If a new state is specified, set it
            self._set_gpu_state(state_name, state)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore the GPU state when leaving the context
        for state_name in self._state_names.keys():
            self._set_gpu_state(state_name, self._original_state[state_name])

################
def draw_circle_2d(context, center, radius, color):
    # Compute the right direction vector
    view_matrix = context.region_data.view_matrix
    right_vector = Vector((view_matrix[0][0], view_matrix[0][1], view_matrix[0][2]))

    # Compute 2D locations
    center_location_2D = view3d_utils.location_3d_to_region_2d(
        context.region, context.region_data, center)
    right_location_2D = view3d_utils.location_3d_to_region_2d(
        context.region, context.region_data, center + right_vector)

    # Compute the radius in 2D
    radius_2D = abs(right_location_2D.x - center_location_2D.x) * radius

    # Define circle vertices in 2D
    angles = np.linspace(0, 2*np.pi, 60)
    circle_verts_2D = np.stack([
        radius_2D * np.cos(angles) + center_location_2D.x,
        radius_2D * np.sin(angles) + center_location_2D.y], axis=-1)

    # Define the shader
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    shader.bind()
    shader.uniform_float('color', color)

    # Create batch and draw the circle
    cv2 = [Vector(v) for v in circle_verts_2D]
    batch = batch_for_shader(shader, 'LINE_LOOP', {'pos': cv2})
    batch.draw(shader)
    
################
def draw_line_2d(context, point, direction, color):
    # Define the shader
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    shader.bind()
    shader.uniform_float('color', color)

    # Compute 2D locations
    point1 = view3d_utils.location_3d_to_region_2d(
        context.region, context.region_data, point - direction)
    point2 = view3d_utils.location_3d_to_region_2d(
        context.region, context.region_data, point + direction)

    # Compute edge
    dir = point2 - point1
    dir.normalize()
    size = max(context.region.width, context.region.height)
    points = np.linspace(point1 - dir * size, point1 + dir * size, 10)
    coords = [Vector(v) for v in points]
    batch = batch_for_shader(shader, 'LINE_LOOP', {'pos': coords})
    batch.draw(shader)
    
################
def calculate_mouse_ray_plane_intersection(context,
                                           coord,
                                           point,
                                           normal_vector):
    # マウスカーソルの位置からビューポートへの3Dレイを取得します
    ray_origin = view3d_utils.region_2d_to_origin_3d(
        context.region, context.region_data, coord)
    ray_direction = view3d_utils.region_2d_to_vector_3d(
        context.region, context.region_data, coord)

    # レイと平面との交点を計算します
    intersection = mathutils.geometry.intersect_line_plane(
        ray_origin, ray_origin + ray_direction,
        point, normal_vector)

    return intersection

################
def calculate_mouse_ray_line_intersection(context,
                                          coord,
                                          point,
                                          direction):
    # マウスカーソルの位置からビューポートへの3Dレイを取得します
    ray_origin = view3d_utils.region_2d_to_origin_3d(
        context.region, context.region_data, coord)
    ray_direction = view3d_utils.region_2d_to_vector_3d(
        context.region, context.region_data, coord)

    # レイと直線の交点を求めます
    intersection, _ = mathutils.geometry.intersect_line_line(
        point, point + direction,
        ray_origin, ray_origin + ray_direction)

    return intersection

################
def calculate_mouse_move_unit(context, location):
    """
    Calculates how far an object at world coordinate location will move in relation to a mouse movement of 1.

    Parameters:
    -----------
    context : bpy.types.context
        The context in which the mouse is placed.

    location : Vector
        World coordinates for calculating mouse movement.

    Returns:
    --------
    float
        Distance traveled relative to mouse movement 1.

    """
    region_xy = view3d_utils.location_3d_to_region_2d(
        context.region, context.region_data, location)
    new_xy = region_xy + Vector((1, 0))
    new_location = view3d_utils.region_2d_to_location_3d(
        context.region, context.region_data, new_xy, location)
    return (new_location - location).length

################
def calculate_mouse_range_at_pivot(context):
    pivot = context.region_data.view_location
    unit = calculate_mouse_move_unit(context, pivot)
    region = context.region
    return (region.width * unit, region.height * unit)

################
class NumberInput():
    """Class supporting numerical input.
It supports simple four arithmetic operations, parentheses, and cursor movement.
  0123456789.     : Numeric input
  +/*             : Operator input
  -               : Reverse whole positive/negative
  ()              : Parentheses input
  LEFT_ARROW      : Move cursor to left
  RIGHT_ARROW     : Move cursor to right
  UP_ARROW, HOME  : Move cursor to top
  DOWN_ARROW, END : Move cursor to end
  DEL             : Delete a character behind the cursor
  BACKSPACE       : Erase a character before the cursor
"""

    def __init__(self):
        self.negative = False
        self.expression = ''
        self.cursor = 0

    def set_expression(self, exp):
        self.negative = False
        self.expression = str(exp)
        self.cursor = len(self.expression)

    def get_value(self):
        value = eval(self.expression)
        if self.negative: value = -value
        return value

    def is_processing(self):
        return self.expression != ''

    def get_display(self):
        s = f'{self.expression[:self.cursor]}|{self.expression[self.cursor:]}'
        if self.negative:
            return f'-({s})'
        else:
            return s

    def process_event(self, event):
        if event.value != 'PRESS':
            return False

        # Since the placement changes for English keyboards and other keyboards,
        # we match all possible types and check them in ascii.
        if event.type in {
                'NUMPAD_0', 'NUMPAD_1', 'NUMPAD_2', 'NUMPAD_3', 'NUMPAD_4', 
                'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 'NUMPAD_9', 
                'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 
                'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE',
                'NUMPAD_PERIOD',
                'NUMPAD_SLASH',
                'NUMPAD_ASTERIX',
                'NUMPAD_MINUS',
                'NUMPAD_PLUS',
                'SEMI_COLON',
                'PERIOD',
                'COMMA',
                'QUOTE',
                'ACCENT_GRAVE',
                'MINUS',
                'PLUS',
                'SLASH',
                'BACK_SLASH',
                'EQUAL',
                'LEFT_BRACKET',
                'RIGHT_BRACKET'} and \
                event.ascii in '0123456789.+*/()':
            char = event.ascii
            self.expression = f'{self.expression[:self.cursor]}{char}{self.expression[self.cursor:]}'
            self.cursor += len(char)
            return True

        if event.type in {'NUMPAD_MINUS', 'MINUS'}:
            self.negative = not self.negative
            return True

        if self.expression == '':
            return False

        if event.type == 'DEL':
            if self.cursor < len(self.expression):
                self.expression = self.expression[:self.cursor] +\
                    self.expression[self.cursor+1:]
            return True
            
        if event.type == 'BACK_SPACE':
            if len(self.expression) > 0 and self.cursor > 0:
                self.expression = self.expression[:self.cursor-1] +\
                    self.expression[self.cursor:]
                self.cursor -= 1
            return True

        if event.type in {'HOME', 'UP_ARROW'}:
            self.cursor = 0
            return True

        if event.type in {'END', 'DOWN_ARROW'}:
            self.cursor = len(self.expression)
            return True

        if event.type == 'LEFT_ARROW':
            if self.cursor > 0:
                self.cursor -= 1
            return True

        if event.type == 'RIGHT_ARROW':
            if self.cursor < len(self.expression):
                self.cursor += 1
            return True

        return False

################################################################
RE_NAME = re.compile(r'^((?P<side0>left|Left|LEFT|right|Right|RIGHT)(?P<sep0>[. -_]?)|(?P<side1>[lLrR])(?P<sep1>[. -_]))?(?P<main>.+?)((?P<sep2>[. -_])(?P<side2>[lLrR])|(?P<sep3>[. -_]?)(?P<side3>left|Left|LEFT|right|Right|RIGHT))?(?P<number>\.\d+)?$')

FLIP = {
    None:       '',
    'l':        'r',
    'L':        'R',
    'left':     'right',
    'Left':     'Right',
    'LEFT':     'RIGHT',
    'r':        'l',
    'R':        'L',
    'right':    'left',
    'Right':    'Left',
    'RIGHT':    'LEFT',
}

def ensure_string(s):
    return s if s else ''

def flip_side_name(name):
    """
    左右を反転した名前を得る。
    もし左右を反転した名前がなければ None を得る。
    e.g.
      hand -> None
      l_hand -> r_hand
      lefthand -> righthand
      left_hand -> right_hand
      hand_l -> hand_r
      hand.L -> hand.R
      hand.L.003 -> hand.R

    Parameters:
    -----------
    name : string
      名前

    Returns:
    --------
    string
      左右を反転した名前
    """

    mo = RE_NAME.match(name)
    if not mo: return None

    prefix =\
        FLIP[mo.group('side0')] + ensure_string(mo.group('sep0')) +\
        FLIP[mo.group('side1')] + ensure_string(mo.group('sep1'))

    main = mo.group('main')

    suffix =\
        ensure_string(mo.group('sep2')) + FLIP[mo.group('side2')] +\
        ensure_string(mo.group('sep3')) + FLIP[mo.group('side3')]

    if prefix or suffix:
        number = ensure_string(mo.group('number'))
        return prefix + main + suffix + number
    else:
        return None

################
def find_flip_side_name(names, name):
    flipped_name = flip_side_name(name)
    if flipped_name and flipped_name in names:
        return flipped_name
    else:
        return None

def find_flip_side_name_or_self(names, name):
    flipped_name = flip_side_name(name)
    if flipped_name and flipped_name in names:
        return flipped_name
    else:
        return name
