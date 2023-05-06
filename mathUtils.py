import numpy as np

################################################################
# 点郡の球面近似
# Dr.レオさん作
# https://programming-surgeon.com/script/sphere-fit/

def sphere_fit(point_cloud):
    """
    入力
        point_cloud: 点群のxyz座標のリスト　numpyのarray形式で3x3xN行列
    出力
        radius : 近似球の半径 スカラー
        sphere_center : 球の中心座標 xyz numpyのarray
    """

    A_1 = np.zeros((3,3))
    #Aのカッコの中の１項目用に変数A_1をおく
    v_1 = np.array([0.0,0.0,0.0])
    v_2 = 0.0
    v_3 = np.array([0.0,0.0,0.0])
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
def calcCenterOfCircleFromThreeVertices(verts):
    """
    Function to find the coordinates of the outer center from three given 2D position vectors.
    
    Parameters
    ----------
    verts : list of numpy.ndarray
        List of 3 2D position vectors.

    Returns
    -------
    tuple of (float, numpy.ndarray)
        A float number representing the radius of circle.
        A 2D vector (numpy.ndarray) representing the coordinates of the outer center.
    """
    if len(verts) != 3:
        return None

    mtx = 2 * np.array([verts[0] - verts[1],
                        verts[1] - verts[2]])

    if np.linalg.det(mtx) == 0:
        return None
    
    # Calc dot products of each vertex
    dv = np.array([vtx.dot(vtx) for vtx in verts])

    yy = np.array([dv[0] - dv[1], dv[1] - dv[2]])
    center = np.linalg.solve(mtx, yy)

    return (np.linalg.norm(verts[0] - center), center)

################
def calcCenterOfSphereFromFourVertices(verts):
    """
    Function to find the coordinates of the outer center from three given 3D position vectors.
    
    Parameters
    ----------
    verts : list of numpy.ndarray
        List of 3 3D position vectors.

    Returns
    -------
    tuple of (float, numpy.ndarray)
        A float number representing the radius of sphere.
        A 2D vector (numpy.ndarray) representing the coordinates of the outer center.
    """
    if len(verts) != 4:
        return None

    mtx = 2 * np.array([verts[0] - verts[1],
                        verts[1] - verts[2],
                        verts[2] - verts[3]])

    if np.linalg.det(mtx) == 0:
        return None
    
    # Calc dot products of each vertex
    dv = np.array([vtx.dot(vtx) for vtx in verts])

    yy = np.array([dv[0] - dv[1], dv[1] - dv[2], dv[2] - dv[3]])
    center = np.linalg.solve(mtx, yy)

    return (np.linalg.norm(verts[0] - center), center)
