# -*- encoding:utf-8 -*-

import bpy
import bmesh
from . import internalUtils as iu

################
def setCustomNormals(mesh, tf):
    """
    Adds custom normals.

    Parameters
    ----------------
    mesh: ObjectWrapper
    """

    if not mesh or mesh.obj.type != 'MESH' or \
       mesh.obj.data.has_custom_normals == tf:
        return

    with iu.mode_context(mesh.obj, 'OBJECT'):
        bpy.ops.object.select_all(action='DESELECT')
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh.obj
        if tf:
            bpy.ops.mesh.customdata_custom_splitnormals_add()
        else:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
