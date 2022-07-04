import re
import json
from collections import OrderedDict
import bpy, bmesh
from . import internalUtils as iu
from . import WeightTool as wt

################################################################
# reg-exp for Header
re_header = re.compile(r'^([a-zA-Z0-9]+)_(\w+)')

################################################################
def textblock2str(textblock):
    return "".join([line.body for line in textblock.lines])

################################################################
def mergeMeshes(arma, blendshapeJson, triangulate=True):
    """
    Based on the json, merge and triangulate the mesh.
    """

    # A dictionary to get a set of actions from mesh names.
    meshToActions = dict()

    # read json and build meshToActions
    dic = json.loads(textblock2str(bpy.data.texts[blendshapeJson]),object_pairs_hook=OrderedDict)
    for od in dic:
        binds = od.get('binds')
        if binds:
            for bind in binds:
                mesh = bind.get('mesh')
                index = bind.get('index')
                if mesh and index:
                    actions = meshToActions.get(mesh) or set()
                    actions.add(index)
                    meshToActions[mesh] = actions
                else:
                    print(f'Illegal binds in blendshape.json. mesh:{mesh} index:{index}')
    print(meshToActions)

    # For every child meshes, apply modifiers, set origin to (0,0,0) and
    # truangulate.
    cursor_location_save = bpy.context.scene.cursor.location
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in iu.getAllChildMeshes(arma.obj):
        bpy.context.view_layer.objects.active = obj.obj
        obj.select_set(True)
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='BOUNDS')
        if triangulate:
            bm = bmesh.new()
            bm.from_mesh(obj.obj.data)
            bmesh.ops.triangulate(bm, faces=bm.faces,
                                  quad_method='BEAUTY', ngon_method='BEAUTY')
            bm.to_mesh(obj.obj.data)
            bm.free()
    bpy.context.scene.cursor.location = cursor_location_save

    # clear pose
    bpy.context.view_layer.objects.active = arma.obj
    modeChanger = iu.ModeChanger(arma.obj, 'POSE')
    for bone in arma.obj.data.bones:
        bone.hide = False
        bone.select = True
    # for stretch bones, call twice
    bpy.ops.pose.transforms_clear()
    bpy.ops.pose.transforms_clear()
    del modeChanger

    result = dict()

    # Merge the meshes contained in the collection.
    for mn in meshToActions.keys():
        if mn in bpy.data.objects:
            #print(f'{mn} is already a mesh')
            continue

        collection = bpy.data.collections.get(mn)
        if not collection:
            print(f'Warning! Cannot find {mn} in bpy.data.collections')
            continue

        bpy.ops.object.select_all(action='DESELECT')
        target = None
        for obj in collection.all_objects:
            if obj.type == 'MESH':
                obj.select_set(True)
                target = obj
        if target:
            bpy.context.view_layer.objects.active = target
            bpy.ops.object.join()
            bpy.ops.object.modifier_add(type='ARMATURE')
            bpy.context.object.modifiers[-1].object = arma.obj
            target.name = mn
            result[mn] = iu.ObjectWrapper(mn)
    
    # Merge rest of meshes.
    bpy.ops.object.select_all(action='DESELECT')
    target = None
    for obj in iu.getAllChildMeshes(arma.obj):
        if obj.obj.type == 'MESH' and obj.name not in meshToActions:
            obj.select_set(True)
            target = obj.obj
    if target:
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.join()
        bpy.ops.object.modifier_add(type='ARMATURE')
        bpy.context.object.modifiers[-1].object = arma.obj
        result[None] = iu.ObjectWrapper(target.name)

    # bake pose
    anim = arma.obj.animation_data_create()
    for mn, actions in meshToActions.items():
        print(f'mesh: {mn}')
        mesh = result[mn]
        for an in sorted(actions):
            print(f'action: {an}')
            action = bpy.data.actions.get(an)
            if not action:
                print('Warning! Cannot find action {an}')
                continue

            bpy.context.view_layer.objects.active = mesh.obj

            # for stretch bones, call twice
            anim.action = action
            anim.action = action
            
            # At this point, mesh has only a 'Armature' modifier
            mod = mesh.obj.modifiers[-1]
            modName = mod.name  # save
            mod.name = an       # set to action's name
            bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=an)
            mod.name = modName  # restore
            
            # Be sure to reset pose
            anim.action=None
            bpy.context.view_layer.objects.active = arma.obj
            modeChanger = iu.ModeChanger(arma.obj, 'POSE')
            # for stretch bones, call twice
            bpy.ops.pose.transforms_clear()
            bpy.ops.pose.transforms_clear()
            del modeChanger

    return result

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
                       triangulate=False,
                       bs_json=None,
                       notExport='NotExport',
                       neutral='Neutral'):
    """
    Prepares to export.
    
    Parameters
    ----------------
    skeleton : String
        Name of skeleton to export
    bs_json : String
        Name of textblock of blendshape_group.json
    notExport : String
        Name of bone_group
    neutral : String
        Name of shapekey of basic face expression

    """

    arma = iu.ObjectWrapper(skeleton)
    mergedObjs = mergeMeshes(arma, bs_json, triangulate=triangulate)

    print('---------------- mergedObjs:')
    print(mergedObjs)

    deleteBones(arma, notExport)

    for pose, obj in mergedObjs.items():
        if pose:
            # FIXME
            #  not work...
            #setNeutralToBasis(obj, neutral=neutral)
            pass
        wt.cleanupWeights(obj)
