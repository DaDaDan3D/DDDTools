# -*- encoding:utf-8 -*-

import bpy
import math
from mathutils import (
    Vector,
    Matrix,
)
import numpy as np

################################################################
# 点郡の球面近似
# Dr.レオさん作の関数を多次元に拡張したもの
# https://programming-surgeon.com/script/sphere-fit/

def calcFit(point_cloud):
    """
    入力
        point_cloud: 点群の座標のリスト　numpyのarray形式
    出力
        radius : 近似球の半径 スカラー
        sphere_center : 球の中心座標  numpyのarray
    """

    dimension = point_cloud.shape[1]
    A_1 = np.zeros((dimension, dimension))

    #Aのカッコの中の１項目用に変数A_1をおく
    v_1 = np.zeros(dimension)
    v_2 = 0.0
    v_3 = np.zeros(dimension)
    #ベクトルの１乗、２乗、３乗平均の変数をv_1, v_2, v_3とする
    #１乗、３乗はベクトル、２乗はスカラーとなる

    N = len(point_cloud)
    #Nは点群の数

    # シグマの計算
    for v in point_cloud:
        v_1 += v
        v_2 += np.dot(v, v)
        v_3 += np.dot(v, v) * v

        A_1 += np.dot(np.array([v]).T, np.array([v]))

    v_1 /= N
    v_2 /= N
    v_3 /= N
    A = 2 * (A_1 / N - np.dot(np.array([v_1]).T, np.array([v_1])))
    # 式②
    b = v_3 - v_2 * v_1
    # 式③
    sphere_center = np.dot(np.linalg.inv(A), b)
    #　式①
    radius = (sum(np.linalg.norm(np.array(point_cloud) - sphere_center, axis=1))
              /len(point_cloud))

    return(radius, sphere_center)

################################################################
def calcCircumcenter(verts):
    """
    Function to find the coordinates of the outer center from given position vectors.
    
    Parameters
    ----------
    verts : numpy.ndarray
        List of position vectors.

    Returns
    -------
    tuple of (float, numpy.ndarray)
        A float number representing the radius of sphere(circle).
        A position vector (numpy.ndarray) representing the coordinates of the outer center.
    """
    if verts.shape[0] != verts.shape[1] + 1:
        raise ValueError(f'Dimension of vertex is {verts.shape[1]}, so need just {verts.shape[1] + 1} vertices.')

    mtx = 2 * np.diff(verts, axis=0)
    
    # Calc dot products of each vertex
    dv = np.einsum('ij,ij->i', verts, verts)

    yy = np.diff(dv, axis=0)
    center = np.linalg.solve(mtx, yy)

    return (np.linalg.norm(verts[0] - center), center)

################################################################
# 点群の平面近似の多次元対応版
def calcFitPlane(points):
    """
    Fit a plane to a set of points using PCA.

    Parameters
    ----------
    points : ndarray
        An array of coordinates.

    Returns
    -------
    ndarray, ndarray
        The normal vector of the plane and a point on the plane.

    Raises
    ------
    ValueError
        If the input points array does not shape a point cloud.
    """
    if points.ndim != 2:
        raise ValueError('Input points must be 2-dim point array.')

    # Compute the mean of the points
    mean = np.mean(points, axis=0)

    # Center the points
    centered_points = points - mean

    # Compute the covariance matrix
    cov_matrix = np.cov(centered_points.T)

    # Compute the eigenvalues and eigenvectors of the covariance matrix
    eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)

    # The plane's normal vector is the eigenvector associated with the smallest eigenvalue
    normal = eigenvectors[:, np.argmin(eigenvalues)]

    return normal, mean

################################################################
# 点から平面に降ろした垂線の足を計算する
# 多次元対応版
def perpendicular_foot_on_plane(point, plane_normal, plane_point):
    if point.shape != plane_point.shape or point.shape != plane_normal.shape:
        raise ValueError('Vector dimensions are differ.')

    point_to_plane_vector = point - plane_point
    distance_to_plane = np.dot(point_to_plane_vector, plane_normal)
    perpendicular_foot = point - distance_to_plane * plane_normal

    return perpendicular_foot

################################################################
# 中心を計算する関数各種

################
# 与えられたポリゴンの幾何中心を計算する
def arithmetic_centroid_of_polygon(verts):
    return np.mean(verts, axis=0)

################
# 与えられたポリゴンの面積中心を計算する
def area_centroid_of_polygon(verts):
    """
    Compute the area centroid of a polygon.

    Parameters
    ----------
    verts : ndarray
        An array of the positions of the vertices.

    Returns
    -------
    ndarray
        The position of the area centroid.

    Raises
    ------
    ValueError
        If the input vertices array does not shape a polygon.
    """
    if verts.ndim != 2 or len(verts) < 3:
        raise ValueError('Input verts must be 2-dim vector array and must have at least 3 vertices.')

    # Pairwise vertices
    v1 = np.roll(verts, -1, axis=0) - verts
    v2 = np.roll(verts, -2, axis=0) - verts

    # Pairwise triangle areas (1/2 * cross product magnitudes)
    pairwise_areas = 0.5 * np.linalg.norm(np.cross(v1, v2), axis=-1)

    # Pairwise centroids
    pairwise_centroids = (v1 + v2) / 3 + verts

    # Polygon area
    total_area = np.sum(pairwise_areas)

    # Area-weighted sum of pairwise centroids
    area_centroid = np.sum(pairwise_centroids.T * pairwise_areas, axis=1) / total_area

    return area_centroid

################
# 与えられたポリゴンの球面近似と平面近似を使って中心を計算する
# 中心というか外心なので、使えるケースが限られる
def fit_centroid_of_polygon(verts):
    if verts.shape[1] not in (2, 3):
        raise ValueError('verts must be 2D or 3D points.')

    # 2D の場合
    if verts.shape[1] == 2:
        try:
            radius, center = calcFit(verts)
            return center
        except:
            return np.mean(verts, axis=0)

    # 3D の場合
    # 平面に全ての点を投影して calcFit() をかける
    normal, mean = calcFitPlane(verts)
    normal /= np.linalg.norm(normal)

    # 平面のローカル空間を求める
    forward = np.cross(normal, np.array((1, 0, 0)))
    if np.linalg.norm(forward) > 1e-2:
        right = np.cross(forward, normal)
    else:
        right = np.cross(np.array((0, 1, 0)), normal)
        forward = np.cross(normal, right)
    right /= np.linalg.norm(right)
    forward /= np.linalg.norm(forward)

    matrix_world = np.array((forward, right, normal, mean)).T
    matrix_world = np.append(matrix_world, [(0, 0, 0, 1)], axis=0)
    matrix_world_inv = np.linalg.inv(matrix_world)

    # verts に同次座標を追加し、ローカル座標に変換する
    homogeneous = np.ones((verts.shape[0], 1))
    verts_homogeneous = np.hstack((verts, homogeneous))
    v2d = np.dot(verts_homogeneous, matrix_world_inv.T)
    v2d = v2d[:, :2]

    try:
        radius, center = calcFit(v2d)
    except:
        return mean

    # 座標の次元を拡張し、ワールド座標に変換
    center = np.append(center, (0, 1))
    center = np.dot(center, matrix_world.T)

    return center[:3]

################
def gaussian_window(window_size, std_dev):
    """ガウス分布を使用したウィンドウを生成します。

    Args:
        window_size (int): ウィンドウのサイズ
        std_dev (float): ガウス分布の標準偏差

    Returns:
        numpy array: ガウスウィンドウ。
    """
    
    # 標準偏差を設定
    std_dev *= window_size

    # ウィンドウの中心（平均値）を設定
    mean = (window_size - 1) / 2.0

    # ガウスウィンドウを生成
    window = np.exp(-0.5 * ((np.arange(window_size) - mean) / std_dev) ** 2)

    # ウィンドウを正規化（合計が1になるように）
    window /= np.sum(window)

    return window

################
def circular_convolve(y, window):
    # フィルタの半分のサイズを計算
    pad_size = len(window) // 2

    # 配列の最初と最後に要素をパディング
    padded_y = np.pad(y, pad_width=pad_size, mode='wrap')

    # convolveを実行
    result = np.convolve(padded_y, window, mode='same')

    # 追加したパディングを取り除く
    result = result[pad_size:-pad_size]

    return result

################
def edge_padded_convolve(y, window):
    # フィルタの半分のサイズを計算
    pad_size = len(window) // 2

    # 配列の最初と最後に要素をパディング
    padded_y = np.pad(y, pad_width=pad_size, mode='edge')

    # convolveを実行
    result = np.convolve(padded_y, window, mode='same')

    # 追加したパディングを取り除く
    result = result[pad_size:-pad_size]

    return result

################
def convolve_tube(mesh, window_size, std_dev):
    window = gaussian_window(window_size, std_dev)

    # 出力のメッシュを初期化
    smooth_mesh = np.copy(mesh)

    # 横方向（行ごと）にピーク保持平滑化を適用
    if mesh.shape[1] >= window_size:
        for i in range(mesh.shape[0]):
            smooth_mesh[i, :] = circular_convolve(mesh[i, :], window)

    # 縦方向（列ごと）にピーク保持平滑化を適用
    if mesh.shape[0] >= window_size:
        for j in range(mesh.shape[1]):
            smooth_mesh[:, j] = edge_padded_convolve(smooth_mesh[:, j], window)

    return smooth_mesh

################
def falloff_smooth(val, _):
    return 1 - 3 * val**2 + 2 * val**3

def falloff_sphere(val, _):
    return math.sqrt(1 - val**2)

def falloff_root(val, _):
    return math.sqrt(1 - val)

def falloff_inverse_square(val, _):
    return 1 - val**2

def falloff_sharp(val, _):
    return (1 - val)**2

def falloff_linear(val, _):
    return 1 - val

def falloff_constant(val, _):
    return 1

def falloff_random(val, rng):
    return (1 - val) * (1 - (2 * rng() - 1) * val)

falloff_funcs = {
    'SMOOTH'            : falloff_smooth,
    'SPHERE'            : falloff_sphere,
    'ROOT'              : falloff_root,
    'INVERSE_SQUARE'    : falloff_inverse_square,
    'SHARP'             : falloff_sharp,
    'LINEAR'            : falloff_linear,
    'CONSTANT'          : falloff_constant,
    'RANDOM'            : falloff_random,
}

def get_falloff_enum():
    return bpy.props.EnumProperty(
        name='Falloff Type',
        items=[
            ('SMOOTH', 'Smooth', 'Smooth falloff', 'SMOOTHCURVE', 0),
            ('SPHERE', 'Sphere', 'Spherical falloff', 'SPHERECURVE', 1),
            ('ROOT', 'Root', 'Root falloff', 'ROOTCURVE', 2),
            ('INVERSE_SQUARE', 'Inverse Square', 'Inverse Square falloff', 'INVERSESQUARECURVE', 3),
            ('SHARP', 'Sharp', 'Sharp falloff', 'SHARPCURVE', 4),
            ('LINEAR', 'Linear', 'Linear falloff', 'LINCURVE', 5),
            ('CONSTANT', 'Constant', 'Constant falloff', 'NOCURVE', 6),
            ('RANDOM', 'Random', 'Random falloff', 'RNDCURVE', 7),
        ],
        default='SMOOTH',
    )

################
def normalize_vectors(vectors, epsilon=1e-10):
    magnitudes = np.linalg.norm(vectors, axis=-1)
    normalized_vectors = vectors / (magnitudes[:, np.newaxis] + epsilon)
    return normalized_vectors

################
def append_homogeneous_coordinate(vectors):
    """
    Appends a homogeneous coordinate to a numpy array of vectors.
    
    Parameters
    ----------
    vectors : np.ndarray
        A numpy array of vectors. The vectors should be the last dimension. 
        For instance, a 3D vector array should have shape (n, 3), 
        where n is the number of vectors.
    
    Returns
    -------
    np.ndarray
        The original array of vectors with an additional homogeneous coordinate 
        appended. The appended coordinate has value 1 for all vectors. 
        For instance, if the input is a 3D vector array with shape (n, 3),
        the output will be a 4D vector array with shape (n, 4).
    """
    return np.concatenate((vectors, np.ones(vectors.shape[:-1] + (1,))), axis=-1)

################
class ViewData():
    """
    SpaceView3D からカメラの情報を保存したもの
    """
    def __init__(self, sv3d):
        rv3d = sv3d.region_3d
        self.is_perspective = rv3d.is_perspective
        self.view_matrix = rv3d.view_matrix.copy()
        self.view_location = rv3d.view_location.copy()
        self.clip_end = sv3d.clip_end

    def compute_local_ray_origins(self, locations_homo, matrix_world):
        """
        カメラから locations へ向かうレイの、ローカルな基点を計算する
        """
        if self.is_perspective:
            camera_pos = self.view_matrix.inverted().translation
            l_camera_pos = np.array(matrix_world.inverted() @ camera_pos)
            l_ray_origins = np.tile(l_camera_pos, (locations_homo.shape[0], 1))
        else:
            mtx = np.array(self.view_matrix).T
            l_locations_homo = locations_homo @ mtx
            l_locations_homo[:, 2] = self.clip_end * 0.5
            mtx = np.array((self.view_matrix @ matrix_world).inverted()).T
            l_ray_origins = (l_locations_homo @ mtx)[:, :3]
        return l_ray_origins

################
def project_onto_mesh(locations,
                      mesh,
                      view_data,
                      which_to_use=True,
                      mesh_thickness=0,
                      backface_culling=False,
                      epsilon=1e-10):
    """
    カメラから locations のレイを飛ばし、メッシュ上の当たり位置を計算する。

    Parameters:
    -----------
    locations : np.ndarray
      調べる点のワールド座標
    mesh : bpy.types.Object
      当たり判定を調べるメッシュオブジェクト
    view_data : ViewData
      3D ビューポートの情報
    which_to_use : np.ndarray
      どの点について調べるかの bool の配列
    mesh_thickness : float
      メッシュの厚み
    backface_culling : bool
      裏面を無視するかどうか
    epsilon : float
      ゼロ除算を回避するための、十分に小さい数

    Returns:
    --------
    np.ndarray, np.ndarray
      当たったかどうかの bool の配列と、新しい位置
    """

    if locations.size == 0 or not np.any(which_to_use):
        # Do nothing
        return False, locations

    # Compute mesh-local locations
    locations_homo = append_homogeneous_coordinate(locations)
    world_to_mesh = np.array(mesh.matrix_world.inverted()).T
    l_locations = (locations_homo @ world_to_mesh)[:, :3]

    # Compute mesh-local ray-origin
    l_ray_origins = view_data.compute_local_ray_origins(locations_homo,
                                                        mesh.matrix_world)

    # Compute directions
    l_directions = l_locations - l_ray_origins
    l_directions_norm = np.linalg.norm(l_directions, axis=-1)
    l_directions /= (l_directions_norm + epsilon)[:, np.newaxis]

    dt = np.dtype([('hit', bool),
                   ('location', object),
                   ('normal', object),
                   ('index', int)])
    zero = Vector()
    hits = np.array([
        mesh.ray_cast(orig, dir) if use else (False, zero, zero, -1)
        for orig, dir, use in zip(l_ray_origins, l_directions, which_to_use)], dtype=dt)

    # Compute hit locations
    l_hit_locations = np.array([np.array(l[:]) for l in hits['location']])
    dists = np.linalg.norm(l_hit_locations - l_ray_origins, axis=-1)
    dists = np.maximum(0, dists - mesh_thickness)
    l_new_locations = l_ray_origins + l_directions * dists[:, np.newaxis]
    l_new_locations_homo = append_homogeneous_coordinate(l_new_locations)
    mesh_to_world = np.array(mesh.matrix_world).T
    new_locations = (l_new_locations_homo @ mesh_to_world)[:, :3]

    # Compute if rays are hit on surface
    hits_on_surface = hits['hit']
    if backface_culling:
        l_hit_normals = np.array([np.array(n[:]) for n in hits['normal']])
        dot_products = np.sum(l_hit_normals * l_directions, axis=-1)
        hits_on_surface = np.logical_and(hits_on_surface, dot_products < 0)

    # Decide new locations
    new_locations = np.where(hits_on_surface[:, np.newaxis],
                             new_locations, locations)
    return hits_on_surface, new_locations

################
def block_with_mesh(orig_locations,
                    prev_locations,
                    next_locations,
                    mesh,
                    which_to_use=True,
                    mesh_thickness=0,
                    epsilon=1e-10):
    """
    元々 orig_locations の位置にあった点が prev_locations から next_locations に
    移動する時、mesh によって移動をブロックする

    Parameters:
    -----------
    orig_locations : np.ndarray
      点群の元のワールド座標
    prev_locations : np.ndarray
      点群の移動前のワールド座標
    next_locations : np.ndarray
      点群の移動先のワールド座標
    mesh : bpy.types.Object
      当たり判定を調べるメッシュオブジェクト
    which_to_use : np.ndarray
      どの点について調べるかの bool の配列
    mesh_thickness : float
      メッシュの厚み
    epsilon : float
      ゼロ除算を回避するための、十分に小さい数

    Returns:
    --------
    np.ndarray, np.ndarray
      当たったかどうかの bool の配列と、新しい位置
    """

    if next_locations.size == 0 or not np.any(which_to_use):
        # Do nothing
        return False, locations

    # Compute local locations
    mtx = np.array(mesh.matrix_world.inverted()).T[:, :3]
    l_orig_locations = append_homogeneous_coordinate(orig_locations) @ mtx
    l_prev_locations = append_homogeneous_coordinate(prev_locations) @ mtx
    l_next_locations = append_homogeneous_coordinate(next_locations) @ mtx

    # Compute mesh-local directions
    l_directions = l_next_locations - l_prev_locations
    l_directions_norm = np.linalg.norm(l_directions, axis=-1)
    l_directions /= (l_directions_norm + epsilon)[:, np.newaxis]

    l_orig_to_next = l_next_locations - l_orig_locations

    dt = np.dtype([('hit', bool),
                   ('location', object),
                   ('normal', object),
                   ('index', int)])
    zero = Vector()
    hits = np.array([
        mesh.ray_cast(loc, dir) if use else (False, zero, zero, -1)
        for loc, dir, use in zip(l_prev_locations, l_directions, which_to_use)], dtype=dt)

    # Compute hit location
    locations = np.array([np.array(l[:]) for l in hits['location']])
    normals = np.array([np.array(n[:]) for n in hits['normal']])
    dists = np.linalg.norm(locations - l_prev_locations, axis=-1)
    dists = np.minimum(dists - mesh_thickness, l_directions_norm)
    dot_products = np.sum(l_orig_to_next * l_directions, axis=-1)
    hits_on_surface = np.logical_and(hits['hit'], dot_products > 0)
    l_hit_locations = l_prev_locations + l_directions * dists[:, np.newaxis]

    # Compute world locations
    mtx = np.array(mesh.matrix_world).T[:, :3]
    hit_locations = append_homogeneous_coordinate(l_hit_locations) @ mtx

    # Decide new locations
    new_locations = np.where(hits_on_surface[:, np.newaxis],
                             hit_locations, next_locations)
    return hits_on_surface, new_locations
