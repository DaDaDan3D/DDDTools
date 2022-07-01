import re
import json
from collections import OrderedDict
import bpy
from . import internalUtils as iu
from . import WeightTool as wt

################################################################
# reg-exp for Header
re_header = re.compile(r'^([a-zA-Z0-9]+)_(\w+)')

################################################################
def textblock2str(textblock):
    return "".join([line.body for line in textblock.lines])

################################################################
def mergeForEachPose(arma, weightObj=None, triangulate=True):
    """
    Merge all child meshes of armature.
    Also triangulate and apply all modifiers.
    """

    print('---------------- mergeForEachPose')

    poses = bpy.data.actions.keys()
    poses.append(None)          # for any
    result = dict()

    # save cursor and set location to origin
    cursor_location_save = bpy.context.scene.cursor.location
    bpy.context.scene.cursor.location = (0, 0, 0)

    # 1st step
    # get child meshes
    print('---------------- 1st step')
    bpy.ops.object.select_all(action='DESELECT')
    objs = iu.getAllChildMeshes(arma.obj)
    if objs:
        # 2nd step
        # apply all modifiers and set origin to cursor
        print('---------------- 2nd step')
        for obj in objs:
            bpy.context.view_layer.objects.active = obj.obj
            obj.select_set(True)
            bpy.ops.object.convert(target='MESH')
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='BOUNDS')

        # 3rd step
        # join objects for each pose
        print('---------------- 3rd step')
        for pose in poses:
            mergedObj = None
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objs:
                print(obj.name)
                if weightObj and obj.name == weightObj.name:
                    continue

                # check header
                ans = re_header.match(obj.name)
                if ans:
                    header = ans.group(1)
                else:
                    header = None
                print(header)

                if header == pose:
                    obj.select_set(True)
                    if mergedObj is None:
                        bpy.context.view_layer.objects.active = obj.obj
                        mergedObj = obj
                        result[pose] = mergedObj

            if mergedObj:
                bpy.ops.object.join()
                print(mergedObj, mergedObj.obj, bpy.context.active_object)
    
                # triangulate
                if triangulate:
                    print('---------------- triangulate')
                    modeChanger = iu.ModeChanger(mergedObj.obj, 'EDIT')
                    bpy.ops.mesh.reveal()
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY',
                                                       ngon_method='BEAUTY')
                    del modeChanger

                # add armature modifier
                print('---------------- add armature modifier')
                bpy.ops.object.modifier_add(type='ARMATURE')
                bpy.context.object.modifiers[-1].object = arma.obj


        # apply pose to default
        print('---------------- apply pose to default')
        bpy.context.view_layer.objects.active = arma.obj
        modeChanger = iu.ModeChanger(arma.obj, 'POSE')
        bpy.ops.pose.armature_apply(selected=False)
        del modeChanger

    # restore cursor
    bpy.context.scene.cursor.location = cursor_location_save

    print('---------------- finished')
    return result

################################################################
def bakePose(arma, mergedObj, pose=None):
    """
    Bakes all poselibs to shapekeys.
    """
    if not arma or not mergedObj:
        return
    
    print('---------------- bakePose start')
    if pose:
        bpy.context.view_layer.objects.active = arma.obj
        bpy.context.active_object.pose_library = bpy.data.actions[pose]

    bpy.context.view_layer.objects.active = mergedObj.obj
    modeChanger = iu.ModeChanger(mergedObj.obj, 'OBJECT')
    bpy.ops.pose.to_morph()
    del modeChanger
    print('---------------- bakePose finished')

################################################################
def deleteBones(arma, boneGroupName):
    """
    Deletes all bones which belongs to bone_groups[boneGroupName].
    """

    print('---------------- deleteBones')

    # listup all bones to be deleted
    bpy.context.view_layer.objects.active = arma.obj
    modeChanger = iu.ModeChanger(arma.obj, 'POSE')
    bones = []
    for bone in arma.obj.pose.bones:
        if bone.bone_group and bone.bone_group.name == boneGroupName:
            bones.append(bone.name)
    del modeChanger

    wt.dissolveWeightedBones(arma, bones)

################################################################
def setNeutralToBasis(mergedObj, neutral='Neutral'):
    """
    Sets neutral shape key to the basis.
    """

    if not mergedObj:
        return

    modeChanger = iu.ModeChanger(mergedObj.obj, 'OBJECT')

    # move neutral to [1]
    idx = bpy.context.active_object.data.shape_keys.key_blocks.find(neutral)
    if idx < 0:
        print('Failed to find shapekey(', neutral, ')')
    else:
        bpy.context.active_object.active_shape_key_index = idx
        bpy.ops.object.shape_key_move(type='TOP')
        bpy.ops.object.shape_key_move(type='DOWN')

        # delete Basis
        bpy.context.active_object.active_shape_key_index = 0
        bpy.ops.object.shape_key_remove(all=False)
        # At this point, neutral becomes the basis without breaking
        # any other shapekeys.

        # copy neutral and rename to 'Basis'
        bpy.ops.object.shape_key_add(from_mix=True)
        # run twice to get to top
        bpy.ops.object.shape_key_move(type='TOP')
        bpy.ops.object.shape_key_move(type='TOP')
        bpy.context.active_object.active_shape_key.name = 'Basis'

    del modeChanger

################################################################
def prepareToExportVRM(skeleton='skeleton',
                       weightForJoint='WeightForJoint',
                       notExport='NotExport',
                       neutral='Neutral'):
    """
    Prepares to export.
    
    Parameters
    ----------------
    skeleton : String
        Name of skeleton to export
    weightForJoint : String
        Name of object which contains weight data for joint mesh
    notExport : String
        Name of bone_group
    neutral : String
        Name of shapekey of basic face expression

    """

    arma = iu.ObjectWrapper(skeleton)
    weightObj = iu.ObjectWrapper(weightForJoint)
    mergedObjs = mergeForEachPose(arma, weightObj=weightObj, triangulate=True)

    print('---------------- mergedObjs:')
    print(mergedObjs)

    for pose, obj in mergedObjs.items():
        if pose:
            obj.rename('Merged' + pose)
        else:
            obj.rename('MergedBody')

    print('---------------- renamed:')
    print(mergedObjs)

    for pose, obj in mergedObjs.items():
        if pose:
            bakePose(arma, obj, pose)

    deleteBones(arma, notExport)

    for pose, obj in mergedObjs.items():
        if pose:
            # FIXME
            #  not work...
            #setNeutralToBasis(obj, neutral=neutral)
            pass
        else:
            wt.transferWeights(obj, weightObj)
        wt.cleanupWeights(obj)
