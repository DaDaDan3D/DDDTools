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
def rasterize_triangle_half(alpha_array, alpha_threshold, s0_s, t0_s, s1_s, t1_s, s0_l, t0_l, s1_l, t1_l, y0_in, y1_in, is_mid_right):
    """
    Rasterize the half of the triangle.

    Parameters
    ----------
    alpha_array : numpy.ndarray
        A 2D numpy array containing the thinned alpha channel.
    alpha_threshold : float
        The alpha threshold to determine the opacity of the triangle.
    s0_s, t0_s, s1_s, t1_s : float
        Coordinates of the short edge.
    s0_l, t0_l, s1_l, t1_l : float
        Coordinates of the long edge.
    y0_in, y1_in : int
        The Y-axis range for rasterization.
    is_mid_right : bool
        True if the middle point is on the right of the lo-hi edge, False otherwise.

    Returns
    -------
    bool
        True if any pixel in the rasterized area has an alpha value greater than the alpha_threshold, False otherwise.
    """

    width, height = alpha_array.shape

    for y in range(y0_in, y1_in):
        x_l = s0_s if abs(t1_s - t0_s) <= 1e-6 else s0_s + ((s1_s - s0_s) * (y - t0_s)) / (t1_s - t0_s)
        x_r = s0_l if abs(t1_l - t0_l) <= 1e-6 else s0_l + ((s1_l - s0_l) * (y - t0_l)) / (t1_l - t0_l)

        if is_mid_right:
            x_l, x_r = x_r, x_l

        iXl = int(np.floor(x_l))
        iXr = int(np.ceil(x_r))

        uy = y % height
        for x in range(iXl, iXr):
            ux = x % width
            alpha = alpha_array[uy, ux]
            if alpha > alpha_threshold:
                return True
    return False

################
def scan_triangle_alpha(alpha_array, triangle, alpha_threshold):
    """
    Rasterize the triangle and scan the alpha values of the pixels.

    Parameters
    ----------
    alpha_array : numpy.ndarray
        A 2D numpy array containing the thinned alpha channel.
    triangle : List[Vector]
        A list of 3 Vector instances representing the UV coordinates of the triangle.
    alpha_threshold : float
        The alpha threshold to determine the opacity of the triangle.

    Returns
    -------
    bool
        True if any pixel in the rasterized area has an alpha value greater than the alpha_threshold, False otherwise.
    """
    width, height = alpha_array.shape

    st = [width * uv.uv.x - 0.5 for uv in triangle]
    tt = [height * uv.uv.y - 0.5 for uv in triangle]

    st0, st1, st2 = st[0], st[1], st[2]
    tt0, tt1, tt2 = tt[0], tt[1], tt[2]

    if (st0 == st1 and tt0 == tt1) or (st0 == st2 and tt0 == tt2) or (st1 == st2 and tt1 == tt2):
        return False

    if tt0 > tt1 and tt0 > tt2:
        st0, st2 = st2, st0
        tt0, tt2 = tt2, tt0
    elif tt1 > tt2:
        st1, st2 = st2, st1
        tt1, tt2 = tt2, tt1

    if tt0 > tt1:
        st0, st1 = st1, st0
        tt0, tt1 = tt1, tt0

    is_mid_right = (-(st2 - st0) * (tt1 - tt2) + (tt2 - tt0) * (st1 - st2)) > 0
    ylo = int(np.floor(tt0))
    yhi_beg = int(np.round(tt1))
    yhi = int(np.ceil(tt2))

    # Rasterize the triangle
    result1 = rasterize_triangle_half(
        alpha_array, alpha_threshold, st0, tt0, st1, tt1, st0, tt0, st2, tt2, ylo, yhi_beg, is_mid_right
    )
    if result1:
        return True

    result2 = rasterize_triangle_half(
        alpha_array, alpha_threshold, st1, tt1, st2, tt2, st0, tt0, st2, tt2, yhi_beg, yhi, is_mid_right
    )
    return result2

################
def scan_face_alpha(face, uv_layer, alpha_array, alpha_threshold=0.5):
    """
    Rasterize the face and scan the alpha values of the pixels.
    Parameters
    ----------
    face : bmesh.types.BMFace
        The face to rasterize and scan the alpha values.
    uv_layer : bmesh.types.BMLoopUV
        The active UV layer.
    alpha_array : numpy.ndarray
        A 2D numpy array containing the thinned alpha channel.
    alpha_threshold : float, optional
        The alpha threshold to determine the opacity of the face, by default 0.5.

    Returns
    -------
    bool
        True if any pixel in the rasterized area has an alpha value greater than the alpha_threshold, False otherwise.
    """
    uv_coords = [loop[uv_layer] for loop in face.loops]

    for idx in range(2, len(uv_coords)):
        result = scan_triangle_alpha(alpha_array,
                                     [uv_coords[0],
                                      uv_coords[idx - 1],
                                      uv_coords[idx]],
                                     alpha_threshold)
        if result:
            return True
    return False
