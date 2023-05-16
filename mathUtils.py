# -*- encoding:utf-8 -*-

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

    """シグマの計算"""
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
    dv = np.einsum("ij,ij->i", verts, verts)

    yy = np.diff(dv, axis=0)
    center = np.linalg.solve(mtx, yy)

    return (np.linalg.norm(verts[0] - center), center)
