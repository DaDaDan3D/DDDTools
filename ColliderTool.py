import bpy
import math
from mathutils.bvhtree import BVHTree
from mathutils import (
    Vector,
    Matrix,
)
import statistics
from . import internalUtils as iu

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

    print('----------------')
    mesh = iu.ObjectWrapper(meshObj)
    arma = iu.ObjectWrapper(armaObj)
    if not mesh or not arma:
        return {'CANCELLED'}, "Please select Armature and Mesh"
    print('mesh:', mesh.name, 'arma:', arma.name)

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
    print(selection)

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


    print(params)
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
    
