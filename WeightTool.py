# -*- encoding:utf-8 -*-

import re
import bpy
import bmesh
from . import internalUtils as iu

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

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
