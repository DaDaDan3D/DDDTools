import bpy

################
def selectAllObjectsUsingTexture(textureName):
    """
    Selects all objects which are using the texture.

    Parameters
    ----------------
    textureName: name of texture
    """

    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.selectable_objects:
        for mat_slot in obj.material_slots:
            if mat_slot.material and mat_slot.material.node_tree:
                for node in mat_slot.material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image.name == textureName:
                        obj.select_set(True)
                        bpy.context.view_layer.objects.active = obj

################
def selectAllImageNodesUsingTexture(textureName):
    """
    Selects all image nodes which are using the texture.

    Parameters
    ----------------
    textureName: name of texture
    """

    #print(f'selectAllImageNodesUsingTexture({textureName})')
    for mat in bpy.data.materials:
        if mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image.name == textureName:
                    node.select = True
                    mat.node_tree.nodes.active = node
                else:
                    node.select = False
                #print(node.image.name, node.select)

################
def selectAllObjectsUsingMaterial(materialName):
    """
    Selects all objects which are using the material.

    Parameters
    ----------------
    materialName: name of material
    """

    bpy.ops.object.select_all(action='DESELECT')
    for objName in listupAllObjectsUsingMaterial(materialName):
        obj = bpy.data.objects.get(objName)
        if obj:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

################
def listupAllObjectsUsingMaterial(materialName):
    """
    Returns all objects which are using the material

    Parameters
    ----------------
    materialName: name of material
    """

    objs = set()
    for obj in bpy.context.selectable_objects:
        for mat_slot in obj.material_slots:
            if mat_slot.name == materialName:
                objs.add(obj.name)
    return objs

################
def listupAllMaterialsUsingTexture(textureName):
    """
    Returns all materials which are using the texture.

    Parameters
    ----------------
    textureName: name of texture
    """

    mats = set()
    for obj in bpy.data.objects:
        for mat_slot in obj.material_slots:
            if mat_slot.material and mat_slot.material.node_tree:
                for node in mat_slot.material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image.name == textureName:
                        mats.add(mat_slot.material.name)
    return mats

################
def setupMaterialContainerObject(textureName):
    """
    Add materials which are using the texture.

    Parameters
    ----------------
    textureName: name of texture
    """

    obj = bpy.context.active_object

    # remove all materials
    bpy.ops.object.material_slot_remove_unused()
    for idx in range(len(obj.material_slots)):
        bpy.context.object.active_material_index = 0
        bpy.ops.object.material_slot_remove()

    mats = listupAllMaterialsUsingTexture(textureName)
    idx = len(obj.material_slots)
    for mat in sorted(mats):
        bpy.ops.object.material_slot_add()
        obj.material_slots[idx].material = bpy.data.materials[mat]
        idx += 1

################
def calcSpecularFromIOR(ior):
    """
    Calculates the specular from the IOR, copies it to the clipboard, and returns it.

    Parameters
    ----------------
    ior : number (>0)
    """
    tmp = (ior - 1) / (ior + 1)
    specular = tmp * tmp / 0.08
    bpy.context.window_manager.clipboard = str(specular)
    return specular
