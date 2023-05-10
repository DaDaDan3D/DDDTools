import bpy
import bmesh
import numpy as np

################################################################
def offsetUVCoords(uv_coords, mode, paramX, paramY, selected=None):
    """
    Moves selected UVs using numpy.

    Parameters
    ----------------
    uv_coords : numpy array of UV coordinates (Nx2)
    mode : 'OFFSET', 'ALIGN_LEFT', 'ALIGN_RIGHT', 'ALIGN_TOP', 'ALIGN_BOTTOM', 'ALIGN_CENTER_HORIZONTAL', 'ALIGN_CENTER_VERTICAL'
    paramX : parameter of x
    paramY : parameter of y
    selected : boolean numpy array of selected UVs (Nx1)
    """

    if selected is None:
        selected = np.ones(len(uv_coords), dtype=bool)

    selected_uv_coords = uv_coords[selected]

    if len(selected_uv_coords) == 0:
        return uv_coords, False

    if mode == 'OFFSET':
        offset_x = paramX
        offset_y = paramY

    elif mode == 'ALIGN_LEFT':
        offset_x = paramX - np.min(selected_uv_coords[:, 0])
        offset_y = 0

    elif mode == 'ALIGN_RIGHT':
        offset_x = paramX - np.max(selected_uv_coords[:, 0])
        offset_y = 0

    elif mode == 'ALIGN_TOP':
        offset_x = 0
        offset_y = paramY - np.max(selected_uv_coords[:, 1])

    elif mode == 'ALIGN_BOTTOM':
        offset_x = 0
        offset_y = paramY - np.min(selected_uv_coords[:, 1])

    elif mode == 'ALIGN_CENTER_HORIZONTAL':
        min_x = np.min(selected_uv_coords[:, 0])
        max_x = np.max(selected_uv_coords[:, 0])
        offset_x = paramX - (min_x + max_x) / 2
        offset_y = 0

    elif mode == 'ALIGN_CENTER_VERTICAL':
        offset_x = 0
        min_y = np.min(selected_uv_coords[:, 1])
        max_y = np.max(selected_uv_coords[:, 1])
        offset_y = paramY - (min_y + max_y) / 2

    else:
        raise ValueError(f'Illegal mode: {mode}')
        return uv_coords, False

    uv_coords[selected] += np.array([offset_x, offset_y])

    return uv_coords, True

################################################################
def blender_to_numpy_uv_coords(bm, uv_layer):
    uv_coords = np.array([loop[uv_layer].uv for face in bm.faces for loop in face.loops])
    selected = np.array([loop[uv_layer].select and loop.vert.select for face in bm.faces for loop in face.loops], dtype=bool)
    return uv_coords, selected

################################################################
def numpy_to_blender_uv_coords(bm, uv_layer, uv_coords):
    for loop, uv_coord in zip((loop for face in bm.faces for loop in face.loops), uv_coords):
        loop[uv_layer].uv = uv_coord

################################################################
def offsetSelectedUVIslandOfObject(obj, mode, paramX, paramY):
    """
    Moves selected UVs.

    Parameters
    ----------------
    mode : 'OFFSET', 'ALIGN_LEFT', 'ALIGN_RIGHT', 'ALIGN_TOP', 'ALIGN_BOTTOM', 'ALIGN_CENTER_HORIZONTAL', 'ALIGN_CENTER_VERTICAL'
    paramX : parameter of x
    paramY : parameter of y
    """

    # Ensure we are in edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Get the active mesh object
    me = obj.data
    
    # Get the mesh data in edit mode
    bm = bmesh.from_edit_mesh(me)
    bm.faces.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.verify()

    # Get the UV coordinates and selected information as numpy arrays
    uv_coords, selected = blender_to_numpy_uv_coords(bm, uv_layer)

    # Call the numpy-based offset function
    new_uv_coords, success = offsetUVCoords(uv_coords, mode, paramX, paramY, selected)

    if not success:
        return False

    # Update the UV coordinates in Blender
    numpy_to_blender_uv_coords(bm, uv_layer, new_uv_coords)

    # Update the mesh
    bmesh.update_edit_mesh(me)

    return True

################################################################
def offsetSelectedUVIsland(mode, paramX, paramY):
    result = False
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            result |= offsetSelectedUVIslandOfObject(obj, mode, paramX, paramY)
    if result:
        return {'FINISHED'}
    else:
        return {'CANCELLED'}
