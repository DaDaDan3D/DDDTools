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
# from AppData/Roaming/Blender Foundation/Blender/2.83/scripts/addons/VRM_IMPORTER_for_Blender2_8-master/V_Types.py
class HumanBones(object):
    center_req = ["hips","spine","chest","neck","head"]
    left_leg_req = ["leftUpperLeg","leftLowerLeg","leftFoot"]
    left_arm_req = ["leftUpperArm","leftLowerArm","leftHand"]
    right_leg_req = ["rightUpperLeg","rightLowerLeg","rightFoot"]
    right_arm_req = ["rightUpperArm","rightLowerArm","rightHand"]

    requires= [
        *center_req[:],
        *left_leg_req[:],*right_leg_req[:],
        *left_arm_req[:],*right_arm_req[:]   
    ]

    left_arm_def = ["leftShoulder",
                    "leftThumbProximal","leftThumbIntermediate","leftThumbDistal","leftIndexProximal",
                    "leftIndexIntermediate","leftIndexDistal","leftMiddleProximal","leftMiddleIntermediate",
                    "leftMiddleDistal","leftRingProximal","leftRingIntermediate","leftRingDistal",
                    "leftLittleProximal","leftLittleIntermediate","leftLittleDistal"]

    right_arm_def = ["rightShoulder",
                        "rightThumbProximal","rightThumbIntermediate","rightThumbDistal",
                        "rightIndexProximal","rightIndexIntermediate","rightIndexDistal",
                        "rightMiddleProximal","rightMiddleIntermediate","rightMiddleDistal",
                        "rightRingProximal","rightRingIntermediate","rightRingDistal",
                        "rightLittleProximal","rightLittleIntermediate","rightLittleDistal"]
    center_def = ["upperChest","jaw"]
    left_leg_def = ["leftToes"]
    right_leg_def = ["rightToes"]
    defines =  [
        "leftEye","rightEye",
        *center_def[:],
        *left_leg_def[:],
        *right_leg_def[:],
        *left_arm_def[:],
        *right_arm_def[:]
                ]
    #child:parent
    hierarchy = {
        #ëÃä≤
        "leftEye":"head",
        "rightEye":"head",
        "jaw":"head",
        "head":"neck",
        "neck":"upperChest",
        "upperChest":"chest",
        "chest":"spine",
        "spine":"hips", #root
        #âEè„
        "rightShoulder":"chest",
        "rightUpperArm":"rightShoulder",
        "rightLowerArm":"rightUpperArm",
        "rightHand":"rightLowerArm",
        "rightThumbProximal":"rightHand",
        "rightThumbIntermediate":"rightThumbProximal",
        "rightThumbDistal":"rightThumbIntermediate",
        "rightIndexProximal":"rightHand",
        "rightIndexIntermediate":"rightIndexProximal",
        "rightIndexDistal":"rightIndexIntermediate",
        "rightMiddleProximal":"rightHand",
        "rightMiddleIntermediate":"rightMiddleProximal",
        "rightMiddleDistal":"rightMiddleIntermediate",
        "rightRingProximal":"rightHand",
        "rightRingIntermediate":"rightRingProximal",
        "rightRingDistal":"rightRingIntermediate",
        "rightLittleProximal":"rightHand",
        "rightLittleIntermediate":"rightLittleProximal",
        "rightLittleDistal":"rightLittleIntermediate",
        #ç∂è„
        "leftShoulder":"chest",
        "leftUpperArm":"leftShoulder",
        "leftLowerArm":"leftUpperArm",
        "leftHand":"leftLowerArm",
        "leftThumbProximal":"leftHand",
        "leftThumbIntermediate":"leftThumbProximal",
        "leftThumbDistal":"leftThumbIntermediate",
        "leftIndexProximal":"leftHand",
        "leftIndexIntermediate":"leftIndexProximal",
        "leftIndexDistal":"leftIndexIntermediate",
        "leftMiddleProximal":"leftHand",
        "leftMiddleIntermediate":"leftMiddleProximal",
        "leftMiddleDistal":"leftMiddleIntermediate",
        "leftRingProximal":"leftHand",
        "leftRingIntermediate":"leftRingProximal",
        "leftRingDistal":"leftRingIntermediate",
        "leftLittleProximal":"leftHand",
        "leftLittleIntermediate":"leftLittleProximal",
        "leftLittleDistal":"leftLittleIntermediate",

        #ç∂ë´
        "leftUpperLeg":"hips",
        "leftLowerLeg":"leftUpperLeg",
        "leftFoot":"leftLowerLeg",
        "leftToes":"leftFoot",
        #âEë´
        "rightUpperLeg":"hips",
        "rightLowerLeg":"rightUpperLeg",
        "rightFoot":"rightLowerLeg",
        "rightToes":"rightFoot"
    }

def textblock2str(textblock):
    return "".join([line.body for line in textblock.lines])

################################################################

# reg-exp for temporary bones
re_tmpbones = re.compile(r'(HANDLE|RIG|IK|tmp)[._]', re.I)




################################################################
def getBones(arma):
    """
    Returns names of bones.

    Parameters
    ----------------
    arma : Object Wrapper
        Skeleton Object
    """

    ans = set()
    for val in arma.obj.data.values():
        if val:
            ans.add(val)
    return ans

################################################################
def getSpringBones(arma):
    """
    Returns names of spring bones.

    Parameters
    ----------------
    arma : Object Wrapper
        Skeleton Object
    """

    ans = set()
    spring_bone = arma.obj.get('spring_bone')
    if spring_bone and spring_bone in bpy.data.texts:
        dic = json.loads(textblock2str(bpy.data.texts[spring_bone]),object_pairs_hook=OrderedDict)
        for od in dic:
            bones = od.get('bones')
            if bones:
                ans |= set(bones)
    return ans

################################################################
class BoneChecker():

    def __init__(self, arma):
        """
        Parameters
        ----------------
        arma : Object Wrapper
            Skeleton Object
        """
        self._arma = arma
        self._bones = getBones(arma)
        self._springBones = getSpringBones(arma)
        
    def isNecessaryBone(self, boneName):
        """
        Returns if the bone is necessary for VRM.

        Parameters
        ----------------
        boneName : String
            Name of bone to check.
        """

        if boneName in self._bones:
            return True

        if boneName in self._springBones:
            return True

        if re_tmpbones.match(boneName):
            return False

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
