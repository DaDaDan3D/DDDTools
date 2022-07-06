import bpy
import uuid
from . import internalUtils as iu

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
                newName = "{0}.{1:03d}".format(baseName, count)
            else:
                newName = baseName
        print(count, ':', name, '->', newName)
        bone.name = newName

################
def applyScaleAndRotationToArmature(arma):
    """
    Applies scale and rotation to the armature's child meshes and empties.

    Parameters
    ----------------
    arma : Object Wrapper
        Skeleton Object
    """

    # 1st step
    # listup and select all child empties
    bpy.ops.object.select_all(action='DESELECT')
    boneToEmpties = dict()
    for co in arma.obj.children:
        if co.type == 'EMPTY' and co in bpy.context.selectable_objects:
            bone = co.parent_bone
            if bone:
                if bone not in boneToEmpties:
                    boneToEmpties[bone] = set()
                boneToEmpties[bone].add(co.name)
                co.select_set(True)

    # 2nd step
    # clear parent of empties
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    # 3rd step
    # apply scale and rotation to empties and skeleton
    for co in arma.obj.children:
        if co in bpy.context.selectable_objects:
            co.select_set(True)
    arma.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # 4th step
    # restore parent of empties
    for key, value in boneToEmpties.items():
        print(key, ":", value)

        bpy.ops.object.select_all(action='DESELECT')
        for en in value:
            empty = iu.ObjectWrapper(en)
            empty.select_set(True)
        arma.select_set(True)
        bpy.context.view_layer.objects.active = arma.obj

        modeChanger = iu.ModeChanger(arma.obj, 'EDIT')
        bpy.ops.armature.select_all(action='DESELECT')
        bone = EditBoneWrapper(key)
        bone.select_set(True)
        arma.obj.data.edit_bones.active = bone.obj
        del modeChanger

        bpy.ops.object.parent_set(type='BONE', keep_transform=True)

    # 5th step
    # reset StretchTo
    resetStretchTo(arma)

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
    modeChanger = iu.ModeChanger(arma.obj, 'POSE')
    for bone in arma.obj.pose.bones:
        for cn in bone.constraints:
            #print(bone.name, cn.name, cn.type)
            if cn.type == "STRETCH_TO":
                #print(cn.rest_length)
                cn.rest_length = 0
                result += 1
    del modeChanger
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
    modeChanger = iu.ModeChanger(arma.obj, 'OBJECT')
    for co in arma.obj.children_recursive:
        if co in bpy.context.selectable_objects:
            #print(co.name)
            bpy.context.view_layer.objects.active = co

            # find ARMATURE modifier
            for mod in co.modifiers:
                if mod.type == 'ARMATURE':
                    nameSave = mod.name
                    mod.name = str(uuid.uuid4())
                    bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=mod.name)
                    iu.blendShapekeyToBasis(co, mod.name, blend=1.0, remove_shapekey=True)
                    mod.name = nameSave
                    break
    del modeChanger
            
    # apply pose
    bpy.context.view_layer.objects.active = arma.obj
    modeChanger = iu.ModeChanger(arma.obj, 'POSE')
    bpy.ops.pose.armature_apply(selected=False)
    del modeChanger

    # reset StretchTo
    resetStretchTo(arma)
