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

################
def replace_group_node(old_group_name, new_group_name):
    """
    Replaces shader_group, and returns modified material names.

    Parameters
    ----------------
    old_group_name : string
      The name of ShaderGroupNode to be replaced.
    
    new_group_name : string
      The name of ShaderGroupNode to replace.
    """

    modified_materials = set()

    for material in bpy.data.materials:
        if material.use_nodes:
            nodes = material.node_tree.nodes
            links = material.node_tree.links
            old_group_nodes = [node for node in nodes if node.type == 'GROUP' and node.node_tree.name == old_group_name]

            for old_group_node in old_group_nodes:
                new_group_node = nodes.new('ShaderNodeGroup')
                new_group_node.node_tree = bpy.data.node_groups[new_group_name]

                # Copy location and width
                new_group_node.location = old_group_node.location
                new_group_node.width = old_group_node.width

                # Copy input connections and values
                for input_socket, old_input in zip(new_group_node.inputs, old_group_node.inputs):
                    if old_input.is_linked:
                        old_link = old_input.links[0]
                        links.new(old_link.from_socket, input_socket)
                    else:
                        input_socket.default_value = old_input.default_value

                # Copy output connections
                for output_socket, old_output in zip(new_group_node.outputs, old_group_node.outputs):
                    for old_link in old_output.links:
                        links.new(output_socket, old_link.to_socket)

                # Remove old group node
                nodes.remove(old_group_node)

                modified_materials.add(material.name)

    return modified_materials

################################################################
def sort_material_slots(obj, material_order, remove_unused_slots=False):
    """
    Sort the material slots of the specified object according to the given material_order list and optionally remove unused material slots.

    Parameters
    ----------
    obj : bpy.types.Object
        The object whose material slots need to be sorted.
    material_order : list of str
        List of material names in the desired order.
    remove_unused_slots : bool, optional
        Whether to remove unused material slots, by default False.

    Returns
    -------
    None
    """

    # Remove unused material slots if specified
    if remove_unused_slots:
        bpy.ops.object.material_slot_remove_unused()

    # Ensure the object has material slots
    if len(obj.material_slots) == 0:
        print("No material slots found in the object.")
        return

    # Sort material slots according to the material_order list
    sorted_slots = []
    for material_name in material_order:
        if obj.material_slots.find(material_name) >= 0:
            sorted_slots.append(material_name)

    # Find and sort the remaining material slots not in material_order
    remaining_slots = sorted([slot.material.name for slot in obj.material_slots if slot.material.name not in sorted_slots])

    # Combine sorted lists
    sorted_slots.extend(remaining_slots)
    #print(sorted_slots)

    # Reorder the material slots using bpy.ops.object.material_slot_move()
    for idx, material_name in enumerate(sorted_slots):
        obj.active_material_index = obj.material_slots.find(material_name)
        while obj.active_material_index < idx:
            bpy.ops.object.material_slot_move(direction='DOWN')
            #print(f'down {obj.active_material_index}')
        while obj.active_material_index > idx:
            bpy.ops.object.material_slot_move(direction='UP')
            #print(f'up {obj.active_material_index}')
