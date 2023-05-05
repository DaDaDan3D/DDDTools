import bpy
import bmesh
import numpy as np

################################################################
class ObjectWrapper:
    """
    For safety usage, this class will wrap blender's object.
    """

    _name = None

    def __init__(self, name):
        if isinstance(name, str):
            self._name = name
        elif isinstance(name, bpy.types.Object):
            self._name = name.name

    @property
    def name(self):
        return self._name

    @property
    def obj(self):
        return bpy.data.objects.get(self._name)

    def __repr__(self):
        return '<ObjectWrapper {0}>'.format(self._name)

    def select_set(self, tf):
        obj = self.obj
        if obj:
            obj.select_set(tf)

    def rename(self, newName):
        obj = self.obj
        if obj:
            obj.name = newName
            self._name = newName

    def __bool__(self):
        return isinstance(self._name, str) and self.obj is not None

################################################################
class EditBoneWrapper:
    _name = None

    def __init__(self, name):
        if isinstance(name, str):
            self._name = name
        elif isinstance(name, bpy.types.EditBone):
            self._name = name.name

    @property
    def name(self):
        return self._name

    @property
    def obj(self):
        return bpy.context.active_object.data.edit_bones.get(self._name)

    def __repr__(self):
        return '<EditBoneWrapper {0}>'.format(self._name)

    def select_set(self, tf):
        obj = self.obj
        if obj:
            obj.select = True
            obj.select_head = True
            obj.select_tail = True

    def rename(self, newName):
        obj = self.obj
        if obj:
            obj.name = newName
            self._name = newName

    def __bool__(self):
        return isinstance(self._name, str) and self.obj is not None

################################################################
class ModeChanger:
    """
    Changes mode of viewport and restores original mode when destructed.

    """

    _obj = None
    _mode_org = None

    def __init__(self, obj, mode):
        """
        Constructor
            Activate object and change mode.

        Parameters
        ----------------
        obj : object
            main object to operate

        mode : string
            mode to change

        """

        self._obj = ObjectWrapper(obj)
        self._mode_org = obj.mode
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode=mode)
        #print('ModeChanger: obj:({0}) mode:{1} -> {2}'.format(obj.name, self._mode_org, mode))

    def __del__(self):
        #print('ModeChanger: obj:({0}) restore mode {1}'.format(self._obj.name, self._mode_org))
        if self._obj and self._mode_org:
            bpy.context.view_layer.objects.active = self._obj.obj
            bpy.ops.object.mode_set(mode=self._mode_org)
            self._mode_org = None
            self._obj = None

    def __repr__(self):
        return '<ModeChanger _mode_org:{0}>'.format(self._mode_org)

    def __bool__(self):
        return isinstance(self._mode_org, str) and self._obj is not None


################################################################
def replaceImagePath(strFrom=None , strTo=None):
    """
    Replaces the portion of all image paths matching strFrom from the beginning with strTo.

    Parameters
    ----------------
    strFrom : String
    	Path to replace from.
    strTo : String
        Path to replace to.
    """

    for image in bpy.data.images:
        if image.filepath.startswith(strFrom):
            newFilePath = image.filepath.replace(strFrom, strTo, 1)
            #print('filepath:', image.filepath, 'newFilePath:', newFilePath)
            if image.filepath != newFilePath:
                image.filepath = newFilePath
                #print('replaced')
                image.reload()
                #print('reloaded')


################################################################
def replaceTextPath(strFrom=None , strTo=None):
    """
    Replaces the portion of all text paths matching strFrom from the beginning with strTo.

    Parameters
    ----------------
    strFrom : String
    	Path to replace from.
    strTo : String
        Path to replace to.
    """

    for text in bpy.data.texts:
        if text.filepath.startswith(strFrom):
            newFilePath = text.filepath.replace(strFrom, strTo, 1)
            if text.filepath != newFilePath:
                #print('filepath:', text.filepath, 'newFilePath:', newFilePath)
                text.filepath = newFilePath


################################################################
def listupImagePath():
    """
    Returns all image paths.
    """

    return sorted([image.filepath for image in bpy.data.images])

################################################################
def listupTextPath():
    """
    Returns all text paths.
    """

    return sorted([text.filepath for text in bpy.data.texts])

################################################################
def getAllChildren(obj, types, selectable=True):
    objs = set()
    for co in obj.children_recursive:
        if co.type in types:
            if not(selectable and co not in bpy.context.selectable_objects):
                objs.add(ObjectWrapper(co))
    return objs

def getAllChildMeshes(obj, selectable=True):
    return getAllChildren(obj, ['MESH'], selectable=selectable)

def getAllChildArmatures(obj, selectable=True):
    return getAllChildren(obj, ['ARMATURE'], selectable=selectable)

################
def selectAllChildren(obj, types):
    objs = getAllChildren(obj, types, selectable=True)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)

    return objs

def selectAllChildMeshes(obj):
    return selectAllChildren(obj, ['MESH'])

def selectAllChildArmatures(obj):
    return selectAllChildren(obj, ['ARMATURE'])

################################################################
def unhideVertsAndApplyFunc(meshObj, func):
    """
    Unhide and select all vertices, and applies function.

    Parameters
    ----------------
    meshObj: Object
      Mesh object

    func : Function
      Function to apply
    """

    if not meshObj or meshObj.type != 'MESH':
        return

    modeChanger = ModeChanger(meshObj, 'EDIT')

    mesh = meshObj.data
    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.select_mode = set(['VERT'])

    for vtx in bm.verts:
        # save hide status
        vtx.tag = vtx.hide
        # unhide
        vtx.hide_set(False)
        # select
        vtx.select_set(True)

    bmesh.update_edit_mesh(mesh)
    func()

    for vtx in bm.verts:
        # restore hide status
        vtx.hide_set(vtx.tag)

    bmesh.update_edit_mesh(mesh)

    del modeChanger

################
def propagateShapekey(meshObj, shapekey, remove_shapekey=True):
    """
    Applies shapekey to all other shape keys.

    Parameters
    ----------------
    meshObj: Object
      Mesh object

    shapekey: String
      Name of shapekey to propagate

    remove_shapekey: Boolean
      Whether to delete the shapekey
    """

    idx = bpy.context.active_object.data.shape_keys.key_blocks.find(shapekey)
    if idx < 0:
        print(f'Failed to find shapekey({shapekey})')
    else:
        modeChanger = ModeChanger(meshObj, 'OBJECT')
        bpy.context.active_object.active_shape_key_index = idx
        unhideVertsAndApplyFunc(meshObj, bpy.ops.mesh.shape_propagate_to_all)

        if remove_shapekey:
            bpy.ops.object.shape_key_remove(all=False)

        del modeChanger
            
################
def blendShapekeyToBasis(meshObj, shapekey, blend=1.0, remove_shapekey=True):
    """
    Applies shapekey to basis(shapekey with index=0).

    Parameters
    ----------------
    meshObj: Object
      Mesh object

    shapekey: String
      Name of shapekey to propagate

    remove_shapekey: Boolean
      Whether to delete the shapekey
    """

    idx = bpy.context.active_object.data.shape_keys.key_blocks.find(shapekey)
    if idx < 0:
        print(f'Failed to find shapekey({shapekey})')
    else:
        modeChanger = ModeChanger(meshObj, 'OBJECT')
        bpy.context.active_object.active_shape_key_index = 0
        unhideVertsAndApplyFunc(meshObj,
                                lambda: bpy.ops.mesh.blend_from_shape(shape=shapekey, blend=1.0, add=False))

        if remove_shapekey:
            bpy.context.active_object.active_shape_key_index = idx
            bpy.ops.object.shape_key_remove(all=False)
            
        del modeChanger

################
def remove_isolated_edges_and_vertices(obj):
    """
    Remove vertices and edges that are not part of any face.

    Parameters
    ----------
    obj : bpy.types.Object
        The active mesh object in Edit mode.
    """

    if not obj or obj.type != 'MESH':
        raise ValueError("Object should be a mesh object")

    modeChanger = ModeChanger(obj, 'EDIT')

    # Create a BMesh from the object's mesh data
    bm = bmesh.from_edit_mesh(obj.data)

    # Find and remove edges not part of any face
    edges_to_remove = set(e for e in bm.edges if not e.link_faces)
    bmesh.ops.delete(bm, geom=list(edges_to_remove), context='EDGES')

    # Find and remove vertices not part of any face
    vertices_to_remove = set(v for v in bm.verts if not v.link_faces)
    bmesh.ops.delete(bm, geom=list(vertices_to_remove), context='VERTS')

    # Update the mesh with the changes
    bmesh.update_edit_mesh(obj.data)

    del modeChanger

################
def image_to_alpha_array(image: bpy.types.Image, interval: int) -> np.ndarray:
    """
    Extracts the alpha channel from the input image and thins it by the specified interval.

    Parameters
    ----------
    image : bpy.types.Image
        The input image from which the alpha channel will be extracted.
    interval : int
        The interval at which the alpha channel will be thinned.
        For example, an interval of 3 will thin the image by 1/3.

    Returns
    -------
    np.ndarray
        A 2D numpy array containing the thinned alpha channel.

    Examples
    --------
    >>> image = bpy.data.images['your_image_name']
    >>> interval = 3
    >>> alpha_array = image_to_alpha_array(image, interval)
    >>> print(alpha_array)
    """
    # Convert the input image to a NumPy array and extract the alpha channel
    image_np = np.array(image.pixels[:]).reshape((image.size[1], image.size[0], 4))
    alpha_channel = image_np[:, :, 3]

    # Thin the image by the specified interval
    thinned_alpha_array = alpha_channel[::interval, ::interval]

    return thinned_alpha_array

################
def scan_face_alpha(face, uv_layer, alpha_array, alpha_threshold=0.5):
    width, height = alpha_array.shape

    st = np.array([loop[uv_layer].uv for loop in face.loops])
    st[:, 0] = width  * st[:, 0]
    st[:, 1] = height * st[:, 1]
    
    for idx in range(2, len(st)):
        triangle = np.array([st[0], st[idx - 1], st[idx]])

        s_min, t_min = np.amin(triangle, axis=0)
        s_max, t_max = np.amax(triangle, axis=0)

        s_size = int(s_max - s_min + 1)
        t_size = int(t_max - t_min + 1)

        ss, tt = np.meshgrid(np.linspace(s_min, s_max, s_size),
                             np.linspace(t_min, t_max, t_size))

        points = np.vstack((ss.ravel(), tt.ravel())).T
        indices = np.where(np.all(np.dot(triangle - points[:, None], [-1, 1]) <= 0, axis=1))

        mesh_points = np.vstack((np.array([np.mean(triangle, axis=0)]), points[indices[0]])).astype(int)
        
        if (alpha_array[np.mod(mesh_points[:, 1], height), np.mod(mesh_points[:, 0], width)] > alpha_threshold).any():
            return True
    return False

################
def collectAllVisibleObjects():
    """
    Collect all visible objects in the current view layer and all collections.

    Returns
    -------
    set
        A set of all visible objects.
    """
    result = set(bpy.context.view_layer.objects)
    for collection in bpy.data.collections:
        result.update(collection.objects)
    return result
