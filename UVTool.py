import bpy
import bmesh

def offsetSelectedUVIsland(mode, paramX, paramY):
    """
    Moves selected UVs.

    Parameters
    ----------------
    mode : 'OFFSET', 'ALIGN_LEFT', 'ALIGN_RIGHT', 'ALIGN_TOP', 'ALIGN_BOTTOM'
    paramX : parameter of x
    paramY : parameter of y
    """

    # Ensure we are in edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Get the active mesh object
    obj = bpy.context.active_object
    me = obj.data
    
    # Get the mesh data in edit mode
    bm = bmesh.from_edit_mesh(me)
    uv_layer = bm.loops.layers.uv.verify()
    
    # Store the selected UV coordinates
    selected_uv_coords = [loop[uv_layer].uv for face in bm.faces for loop in face.loops if loop[uv_layer].select]

    if not selected_uv_coords:
        return {'CANCELLED'}


    if mode == 'OFFSET':
        offset_x = paramX
        offset_y = paramY

    elif mode == 'ALIGN_LEFT':
        offset_x = paramX - min(uv_coord.x for uv_coord in selected_uv_coords)
        offset_y = 0
        
    elif mode == 'ALIGN_RIGHT':
        offset_x = paramX - max(uv_coord.x for uv_coord in selected_uv_coords)
        offset_y = 0
        
    elif mode == 'ALIGN_TOP':
        offset_x = 0
        offset_y = paramY - max(uv_coord.y for uv_coord in selected_uv_coords)

    elif mode == 'ALIGN_BOTTOM':
        offset_x = 0
        offset_y = paramY - min(uv_coord.y for uv_coord in selected_uv_coords)

    else:
        return {'CANCELLED'}

    # Apply the offset to the selected UV coordinates
    for uv_coord in selected_uv_coords:
        uv_coord.x += offset_x
        uv_coord.y += offset_y

    # Update the mesh and redraw the view
    bmesh.update_edit_mesh(me)
    bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)

    return{'FINISHED'}
