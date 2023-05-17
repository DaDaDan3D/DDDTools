# -*- encoding:utf-8 -*-

import re
import bpy
import bmesh
from . import internalUtils as iu

################
# reg-exp for _L
re_name_L = re.compile(r'(.*[._-])L$')

################
def getSelectedEditableBones():
    return [iu.EditBoneWrapper(eb) for eb in bpy.context.selected_editable_bones]

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
    modeChanger = iu.ModeChanger(mesh.obj, 'WEIGHT_PAINT')
    vertices = [vtx.index for vtx in mesh.obj.data.vertices]
    for vg in mesh.obj.vertex_groups:
        try:
            vg.remove(vertices)
        except:
            result = False
    del modeChanger
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

    print('MoveWeight() mesh:{0} from:{1} to:{2}'.format(mesh.name, boneFrom.name, boneTo.name))

    # Select mesh and switch to weight-paint-mode
    modeChanger = iu.ModeChanger(mesh.obj, 'WEIGHT_PAINT')

    # Move firstBone's weight to parent
    vgFrom = mesh.obj.vertex_groups.get(boneFrom.name)
    vgTo = mesh.obj.vertex_groups.get(boneTo.name)
    print(vgFrom)
    print(vgTo)

    if vgFrom and vgTo:
        for vtx in mesh.obj.data.vertices:
            #print(vtx.index)
            try:
                weight = vgFrom.weight(vtx.index)
                #print('weight:', weight)
                vgTo.add([vtx.index], weight, type='ADD')
                #print('added')
                vgFrom.remove([vtx.index])
                #print('removed')
            except: pass

    # Restore mode
    del modeChanger

################
def removeVertexGroup(arma, vgName):
    """
    Removes vertexGroup named vgName from mesh which is a child of the armature arma.

    Parameters
    ----------------
    arma : ObjectWrapper
        armature

    vgName : string
        name of vertexGroup

    """
    print('removeVertexGroup() arma:{0} vgName:{1}'.format(arma.name, vgName))

    for obj in bpy.context.editable_objects:
        if obj.type == 'MESH' and obj.parent == arma.obj:
            mesh = iu.ObjectWrapper(obj)
            modeChanger = iu.ModeChanger(mesh.obj, 'EDIT')
            vg = mesh.obj.vertex_groups.get(vgName)
            if vg:
                print('remove {0}(idx:{1}) from {2}'.format(vgName, vg.index, mesh.name))
                mesh.obj.vertex_groups.active_index = vg.index
                bpy.ops.object.vertex_group_remove(all=False)
            del modeChanger

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

################
def setWeightForTailPoll(context):
    meshes, armas = getSelectedObjs()
    return meshes and armas
    
################
def setWeightForTail():
    """
    Sets vertex weight automatically, tipically for tail or hair.
    Select armature first and select meshes, and call this function.
    In armature-edit-mode, be sure to select bones from tail to head.
    """

    print('----------------')
    meshes, armas = getSelectedObjs()
    if not meshes or not armas:
        return {'CANCELLED'}, 'Please select Armature and Meshes'

    arma = armas[0]
    print('meshes:', meshes, 'arma:', arma.name)

    ################
    # 1st step
    # Split first bone
    print('---- 1st step ----')

    # Select armature and switch to edit-mode
    modeChanger_org = iu.ModeChanger(arma.obj, 'EDIT')

    # Select the first bone and split
    firstBone = None
    secondBone = None
    parentBone = None
    print(bpy.context.selected_editable_bones)
    if bpy.context.selected_editable_bones:
        # Store selected_editable_bones
        selection = getSelectedEditableBones()
        print(selection)

        firstBone = iu.EditBoneWrapper(bpy.context.active_bone)
        print('firstBone:', firstBone.name)
        bpy.ops.armature.select_all(action='DESELECT')
        
        firstBone.select_set(True)
        bpy.ops.armature.subdivide(1)
    
        firstBone, secondBone = getSelectedEditableBones()
        print('firstBone:', firstBone.name)
        print('secondBone:', secondBone.name)

        # rename
        savedName = firstBone.name
        firstBone.rename('tmpBone')
        secondBone.rename(savedName)
        print('firstBone:', firstBone.name)
        print('secondBone:', secondBone.name)

        parentBone = iu.EditBoneWrapper(firstBone.obj.parent)
        print('parentBone:', parentBone.name)

        if parentBone and parentBone.name in selection:
            print('Please select bones from tail to head')
            firstBone = None
            secondBone = None
            parentBone = None

        # Restore selected_editable_bones
        for bone in selection:
            bone.select_set(True)

    # Restore mode
    del modeChanger

    if firstBone and secondBone and parentBone:
        ################
        # 2nd step
        # Set and move weight
        print('---- 2nd step ----')
        for mesh in meshes:
            resetWeight(mesh)
            modeChanger = iu.ModeChanger(mesh.obj, 'WEIGHT_PAINT')
            bpy.ops.paint.weight_from_bones(type='AUTOMATIC')
            del modeChanger
            moveWeight(mesh, firstBone, parentBone)

        ################
        # 3rd step
        # remove firstBone
        print('---- 3rd step ----')

        # Select armature and switch to edit-mode
        modeChanger = iu.ModeChanger(arma.obj, 'EDIT')
        
        # Store selected_editable_bones
        selection = [iu.EditBoneWrapper(bone) for bone in bpy.context.selected_editable_bones if bone != firstBone.obj]
        bpy.ops.armature.select_all(action='DESELECT')
        firstBone.select_set(True)
        bpy.ops.armature.delete()

        # Restore selected_editable_bones
        for bone in selection:
            bone.select_set(True)

        # Restore mode
        del modeChanger
        
    ################
    # 4th step
    # remove vertexGroup of vanished firstBone
    if firstBone:
        print('---- 4th step ----')
        removeVertexGroup(arma, firstBone.name)

    # Restore mode
    del modeChanger_org

    print('---- finished ----')

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

    print(f'transferWeights({mesh.name}, {weightObj.name}, max_distance={max_distance}, vertex_group={vertex_group}({invert_vertex_group}), vert_mapping={vert_mapping})')

    bpy.context.view_layer.objects.active = mesh.obj
    modeChanger = iu.ModeChanger(mesh.obj, 'OBJECT')

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
    
    del modeChanger

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
    bpy.context.view_layer.objects.active = mesh.obj
    modeChanger = iu.ModeChanger(mesh.obj, 'WEIGHT_PAINT')

    bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=0.001)
    bpy.ops.object.vertex_group_limit_total(limit=affectBoneMax)
    bpy.ops.object.vertex_group_normalize_all()
    bpy.ops.object.vertex_group_sort(sort_type='BONE_HIERARCHY')

    del modeChanger

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

    bpy.context.view_layer.objects.active = mesh.obj
    modeChanger = iu.ModeChanger(mesh.obj, 'OBJECT')

    # Make Left_to_Right_dictionary from vertex groups
    # eg. leftToRight[vertex_groups['hoge_L'].index] -> vertex_groups['hoge_R'].index
    leftToRight = dict()
    for vg in mesh.obj.vertex_groups:
        mo = re_name_L.match(vg.name)
        if mo:
            rightName = f'{mo.group(1)}R'
            rightVG = mesh.obj.vertex_groups.get(rightName)
            if rightVG:
                leftToRight[vg.index] = rightVG.index
    #print(leftToRight)

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
            for idx_L, idx_R in leftToRight.items():
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

    del modeChanger

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
    bpy.context.view_layer.objects.active = arma.obj
    modeChanger = iu.ModeChanger(arma.obj, 'POSE')
    targetBones = dict()
    for boneName in boneNames:
        bone = arma.obj.pose.bones[boneName]
        toBone = findAncestorDeformerBone(bone.parent, boneNames)
        if toBone:
            targetBones[boneName] = toBone.name
        else:
            print(f'Warning: Failed to find ancestor bone of {boneName}!')
            return None
    print(targetBones)
    del modeChanger

    # 2nd step
    # move weights
    print('---------------- 2nd step')
    objs = iu.getAllChildMeshes(arma.obj)
    for obj in objs:
        for boneFrom, boneTo in targetBones.items():
            if boneTo:
                moveWeight(obj,
                           iu.EditBoneWrapper(boneFrom),
                           iu.EditBoneWrapper(boneTo))

    # 3rd step
    # delete targetBones
    print('---------------- 3rd step')
    bpy.context.view_layer.objects.active = arma.obj
    modeChanger = iu.ModeChanger(arma.obj, 'EDIT')
    bpy.ops.armature.reveal()
    bpy.ops.armature.select_all(action='DESELECT')
    for bone in targetBones:
        print(bone)
        iu.EditBoneWrapper(bone).select_set(True)
    bpy.ops.armature.delete()

    print('---------------- finished')
    
    return targetBones
