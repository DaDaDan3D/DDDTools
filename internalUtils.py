import bpy

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
def getAllChildMeshes(obj, selectable=True):
    objs = set()
    for co in obj.children:
        if co.type == 'MESH':
            if not(selectable and co not in bpy.context.selectable_objects):
                objs.add(ObjectWrapper(co))
        else:
            objs |= getAllChildMeshes(co)
    return objs

def selectAllChildMeshes(obj):
    objs = getAllChildMeshes(obj)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)

    return objs

################################################################
def getAllChildArmatures(obj):
    objs = set()
    for co in obj.children:
        if co.type == 'ARMATURE':
            objs.add(co)
    return objs

def selectAllChildArmatures(obj):
    objs = getAllChildArmatures(obj)
    objs &= set(bpy.context.selectable_objects)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)

    return objs
