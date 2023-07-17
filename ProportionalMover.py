# -*- encoding:utf-8 -*-
import bpy
from bpy.types import Object, PropertyGroup
from bpy.props import PointerProperty, FloatProperty, BoolProperty, StringProperty
import numpy as np
import random
from mathutils import (
    Vector,
    Matrix,
)
from dataclasses import dataclass

from . import internalUtils as iu
from . import mathUtils as mu

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

# 十分に小さい値
EPSILON = 1e-9

################
@dataclass
class DirectionInfo:
    """
    Information of each Direction.

    Parameters:
    -----------
    uniform_direction : bool
      (Read-only) Whether it directs in a uniform direction, regardless of the position.

    constant_direction : bool
      (Read-only) Whether it directs in the constant direction in any context.

    normal_direction : bool
      (Read-only) Whether it's a normal vector or not.

    global_direction : bool
      (Read-only) Whether it directs in the direction of global coordinates.

    row_index : int
      (Read-only) Index of Vector. (If exists)


    Attributes:
    -----------
    vector : Vector
      (Read-only) The direction vector.
      Vector associated with Direction.
      It can be a direction vector or a normal vector.

    ndarray : np.ndarray
      (Read-only) The direction vector.
      np.ndarray version of vector.
      See 'vector' information above.
    """

    _uniform_direction : bool
    _constant_direction : bool
    _normal_direction : bool
    _global_direction : bool
    _row_index : int

    def __post_init__(self):
        self._list = [0] * 3
        if self._row_index >= 0:
            self._list[self._row_index] = 1

    @property
    def uniform_direction(self):
        return self._uniform_direction

    @property
    def constant_direction(self):
        return self._constant_direction

    @property
    def global_direction(self):
        return self._global_direction

    @property
    def normal_direction(self):
        return self._normal_direction

    @property
    def row_index(self):
        return self._row_index

    @property
    def vector(self):
        return Vector(self._list)

    @property
    def ndarray(self):
        return np.array(self._list)

DIRECTION_INFO = {
    'NONE':             DirectionInfo(True, False, False, True, -1),
    'GLOBAL_X':         DirectionInfo(True, True, False, True, 0),
    'GLOBAL_Y':         DirectionInfo(True, True, False, True, 1),
    'GLOBAL_Z':         DirectionInfo(True, True, False, True, 2),
    'LOCAL_X':          DirectionInfo(True, False, False, False, 0),
    'LOCAL_Y':          DirectionInfo(True, False, False, False, 1),
    'LOCAL_Z':          DirectionInfo(True, False, False, False, 2),
    'LOCAL_EACH_X':     DirectionInfo(False, False, False, False, 0),
    'LOCAL_EACH_Y':     DirectionInfo(False, False, False, False, 1),
    'LOCAL_EACH_Z':     DirectionInfo(False, False, False, False, 2),
    'GLOBAL_YZ':        DirectionInfo(True, True, True, True, 0),
    'GLOBAL_ZX':        DirectionInfo(True, True, True, True, 1),
    'GLOBAL_XY':        DirectionInfo(True, True, True, True, 2),
    'LOCAL_YZ':         DirectionInfo(True, False, True, False, 0),
    'LOCAL_ZX':         DirectionInfo(True, False, True, False, 1),
    'LOCAL_XY':         DirectionInfo(True, False, True, False, 2),
    'VIEW_CAMERA':      DirectionInfo(False, False, False, True, -1),
    'VIEW_PIVOT':       DirectionInfo(False, False, False, True, -1),
    'CURSOR_3D':        DirectionInfo(False, False, False, True, -1),
    'OBJECT_ORIGIN':    DirectionInfo(False, False, False, True, -1),
}

################
# 次のタイプを得る
def get_next_direction(direction, key):
    if key == 'X':
        if direction == 'GLOBAL_YZ':            return 'LOCAL_YZ'
        elif direction == 'LOCAL_YZ':           return 'NONE'
        else:                                   return 'GLOBAL_YZ'
    elif key == 'Y':
        if direction == 'GLOBAL_ZX':            return 'LOCAL_ZX'
        elif direction == 'LOCAL_ZX':           return 'NONE'
        else:                                   return 'GLOBAL_ZX'
    elif key == 'Z':
        if direction == 'GLOBAL_XY':            return 'LOCAL_XY'
        elif direction == 'LOCAL_XY':           return 'NONE'
        else:                                   return 'GLOBAL_XY'
    elif key == 'x':
        if direction == 'GLOBAL_X':             return 'LOCAL_X'
        elif direction == 'LOCAL_X':            return 'LOCAL_EACH_X'
        elif direction == 'LOCAL_EACH_X':       return 'NONE'
        else:                                   return 'GLOBAL_X'
    elif key == 'y':
        if direction == 'GLOBAL_Y':             return 'LOCAL_Y'
        elif direction == 'LOCAL_Y':            return 'LOCAL_EACH_Y'
        elif direction == 'LOCAL_EACH_Y':       return 'NONE'
        else:                                   return 'GLOBAL_Y'
    elif key == 'z':
        if direction == 'GLOBAL_Z':             return 'LOCAL_Z'
        elif direction == 'LOCAL_Z':            return 'LOCAL_EACH_Z'
        elif direction == 'LOCAL_EACH_Z':       return 'NONE'
        else:                                   return 'GLOBAL_Z'
    elif key == 'v':
        if direction == 'VIEW_PIVOT':           return 'VIEW_CAMERA'
        elif direction == 'VIEW_CAMERA':        return 'NONE'
        else:                                   return 'VIEW_PIVOT'
    elif key == 'c':
        if direction == 'CURSOR_3D':            return 'OBJECT_ORIGIN'
        elif direction == 'OBJECT_ORIGIN':      return 'NONE'
        else:                                   return 'CURSOR_3D'
    else:                                       return 'NONE'

################
def get_direction_enum():
    return bpy.props.EnumProperty(
        name=_('Direction Axis'),
        description=_('Specify axes or planes to restrict movement.'),
        items=[
            ('NONE', 'None', 'No limitation'),
            ('GLOBAL_X', 'Global X', 'Global X axis'),
            ('GLOBAL_Y', 'Global Y', 'Global Y axis'),
            ('GLOBAL_Z', 'Global Z', 'Global Z axis'),
            ('LOCAL_X', 'Local X', 'Local X axis'),
            ('LOCAL_Y', 'Local Y', 'Local Y axis'),
            ('LOCAL_Z', 'Local Z', 'Local Z axis'),
            ('LOCAL_EACH_X', 'Local Each X', 'Local Each X axis'),
            ('LOCAL_EACH_Y', 'Local Each Y', 'Local Each Y axis'),
            ('LOCAL_EACH_Z', 'Local Each Z', 'Local Each Z axis'),
            ('GLOBAL_YZ', 'Global YZ', 'Global YZ plane'),
            ('GLOBAL_ZX', 'Global ZX', 'Global ZX plane'),
            ('GLOBAL_XY', 'Global XY', 'Global XY plane'),
            ('LOCAL_YZ', 'Local YZ', 'Local YZ plane'),
            ('LOCAL_ZX', 'Local ZX', 'Local ZX plane'),
            ('LOCAL_XY', 'Local XY', 'Local XY plane'),
            ('VIEW_CAMERA', _('View Camera'), _('View Camera Position')),
            ('VIEW_PIVOT', _('View Pivot'), _('View Pivot Position')),
            ('CURSOR_3D', _('3D Cursor'), _('3D Cursor Position')),
            ('OBJECT_ORIGIN', _('Object Origin'), _('Object Origin Position')),
        ],
        default='NONE',
    )

################
# ProportionalMover のモディファイアの基底クラス
class ProportionalMoverModifier():
    def modify(self, pm, new_locations, which_to_move):
        """
        移動時に呼ばれ、移動先の座標や、どの点を動かすかを調整する

        Parameters:
        -----------
        pm : ProportionalMover
          呼び出し元
        new_locations : np.ndarray
          移動先の座標の配列
        which_to_move : np.ndarray
          移動するかどうかを示す bool の配列

        Returns:
        --------
        np.ndarray, np.ndarray
          新しい移動先の座標の配列と、移動するかどうかを示す新しい bool の配列
        """

        # do something
        return new_locations, which_to_move

    def draw(self, context, layout):
        # draw properties
        pass

################################################################
class ProportionalMover():
    def __init__(self):
        # 元のワールド座標
        self.__orig_locations = None

        # 前回のワールド座標
        self.__prev_locations = None

        # ワールド移動方向(単位ベクトル)
        self.__directions = None

        # 選択の中心座標
        self.__center_location = None

        # カメラ情報
        self.__view_data = None

        # 影響を与える距離
        self.__influence_radius = None

        # スムースのタイプ
        self.__falloff_type = None

        # 選択した点との最短距離(ワールド座標)
        self.__distances = None

        # 移動量にかける係数
        self.__factors = None

        # 移動先の座標決定時に呼ばれるモディファイア
        self.modifiers = []

    ################
    # Read-only properties
    @property
    def orig_locations(self):
        return self.__orig_locations

    @property
    def prev_locations(self):
        return self.__prev_locations

    @property
    def center_location(self):
        return self.__center_location

    @property
    def view_data(self):
        return self.__view_data

    @property
    def influence_radius(self):
        return self.__influence_radius

    @property
    def falloff_type(self):
        return self.__falloff_type

    @property
    def distances(self):
        return self.__distances

    ################
    def setup(self, sv3d, locations, selection):
        self.__view_data = mu.ViewData(sv3d)
        self.__orig_locations = locations

        # Compute center
        selected_locations = locations[selection]
        self.__center_location = np.mean(selected_locations, axis=0)

        # Save distances for each bone
        diff_grid = locations[:, np.newaxis] - selected_locations
        self.__distances = np.min(np.linalg.norm(diff_grid, axis=2), axis=1)

        self.reset_movement()

    ################
    # 移動していない状態にする
    def reset_movement(self):
        self.__prev_locations = self.__orig_locations

        # Initialize directions
        self.__directions = np.zeros_like(self.__orig_locations)

        # Invalidate parameters
        self.__factors = None

    ################
    @property
    def directions(self):
        return self.__directions

    @directions.setter
    def directions(self, directions):
        self.__directions = mu.normalize_vectors(directions, epsilon=EPSILON)

    # GLOBAL_X|Y|Z の方向を設定する
    def set_directions_global(self, direction_type):
        di = DIRECTION_INFO[direction_type]
        assert di.constant_direction, f'Illegal direction_type: {direction_type}'
        self.directions = di.ndarray

    # オブジェクトの行列から LOCAL_X|Y|Z の方向を設定する
    def set_directions_local(self, direction_type, obj):
        di = DIRECTION_INFO[direction_type]
        row = di.row_index
        assert row >= 0, f'Illegal direction_type: {direction_type}'
        if di.uniform_direction:
            assert not di.constant_direction, f'Illegal direction_type: {direction_type}'
            self.directions = np.array(obj.matrix_world)[:3, row]

        else:
            self.directions = np.array(
                [np.array(obj.matrix_world @ b.matrix)[:3, row]
                 for b in obj.pose.bones])

    # カメラからの方向を設定する
    def set_directions_from_view_camera(self):
        locations_h = mu.append_homogeneous_coordinate(self.orig_locations)
        orig_pnt = self.view_data.compute_local_ray_origins(locations_h,
                                                            Matrix())
        self.directions = self.orig_locations - orig_pnt

    # カメラ注視点からの方向を設定する
    def set_directions_from_view_pivot(self):
        orig_pnt = np.array(self.view_data.view_location)
        self.directions = self.orig_locations - orig_pnt

    # 3D カーソルからの方向を設定する
    def set_directions_from_cursor_3d(self, context):
        pnt = np.array(context.scene.cursor.location)
        self.directions = self.orig_locations - pnt

    # オジェクト原点からの方向を設定する
    def set_directions_from_object_origin(self, obj):
        pnt = np.array(obj.matrix_world.translation)
        self.directions = self.orig_locations - pnt

    ################
    @property
    def influence_radius(self):
        return self.__influence_radius

    @influence_radius.setter
    def influence_radius(self, influence_radius):
        new_value = max(EPSILON, influence_radius)
        if self.__influence_radius != new_value:
            self.__influence_radius = new_value
        
            # Invalidate parameters
            self.__factors = None

    ################
    @property
    def falloff_type(self):
        return self.__falloff_type

    @falloff_type.setter
    def falloff_type(self, falloff_type):
        if self.__falloff_type != falloff_type:
            self.__falloff_type = falloff_type
        
            # Invalidate parameters
            self.__factors = None

    ################
    @property
    def factors(self):
        # Compute factors
        if self.__factors is None:
            falloff = mu.falloff_funcs[self.falloff_type]
            rng = random.Random(0)
            values = self.distances / self.influence_radius
            self.__factors =\
                np.array([0 if val > 1 else falloff(val, rng.random)
                          for val in values])
        return self.__factors

    def compute_move(self, amount, which_to_move=True):
        """
        移動計算を行う。modifiers が設定されている場合、順番に適用される。

        Parameters:
        -----------
        amount : float
          移動量(m)
        which_to_move : np.ndarray
          移動するかどうかを決定する bool の配列

        Returns:
        --------
        np.ndarray, np.ndarray
        新しいワールド座標と、移動したかどうかを示す bool の配列
        """
        factors = self.factors * amount
        move_vectors = self.directions * factors[:, np.newaxis]
        new_locations = self.orig_locations + move_vectors
        which_to_move = np.logical_and(which_to_move, self.factors > EPSILON)
        for mod in self.modifiers:
            new_locations, which_to_move =\
                mod.modify(self, new_locations, which_to_move)
        new_locations = np.where(which_to_move[:, np.newaxis],
                                 new_locations,
                                 self.orig_locations)
        return new_locations, which_to_move

################################################################
def get_target_mesh_name_prop():
    return StringProperty(
        name=_('Target Mesh'),
        description=_('Specifies the mesh to be checked.'),
    )

################
def get_mesh_thickness_prop():
    return FloatProperty(
        name=_('Mesh Thickness'),
        description=_('Specifies the thickness of the mesh.'),
        subtype='DISTANCE',
        min=0,
        default=0.01,
        precision=2,
        step=1,
        unit='LENGTH',
    )

################
def get_snap_onto_backface_prop():
    return BoolProperty(
        name=_('Snap on Backface'),
        description=_('Specifies that it will snap even if it hits the back face of the mesh.'),
        default=True)

################################################################
class DDDPM_MeshSnapModifier_pg(PropertyGroup):
    target_mesh_name: get_target_mesh_name_prop()
    mesh_thickness: get_mesh_thickness_prop()
    snap_onto_backface: get_snap_onto_backface_prop()

    def draw(self, context, layout):
        col = layout.column(align=False)
        col.prop_search(self, 'target_mesh_name', context.blend_data, 'objects')

        box = col.box().column()
        mesh = bpy.data.objects.get(self.target_mesh_name)
        box.enabled = (mesh is not None and mesh.type == 'MESH')
        box.prop(self, 'mesh_thickness')
        box.prop(self, 'snap_onto_backface')

    def copy_from(self, src):
        self.target_mesh_name = src.target_mesh_name
        self.mesh_thickness = src.mesh_thickness
        self.snap_onto_backface = src.snap_onto_backface

################
class MeshSnapModifier(ProportionalMoverModifier):
    def __init__(self, prop):
        self.m_prop = prop
    
    def modify(self, pm, new_locations, which_to_move):
        mesh = bpy.data.objects.get(self.m_prop.target_mesh_name)
        if not mesh or mesh.type != 'MESH' or not mesh.visible_get():
            return new_locations, which_to_move

        hits, new_locations = mu.project_onto_mesh(
            new_locations,
            mesh,
            pm.view_data,
            which_to_move,
            self.m_prop.mesh_thickness,
            not self.m_prop.snap_onto_backface)

        return new_locations, which_to_move

    def draw(self, context, layout):
        m_prop.draw(context, layout)

################################################################
class DDDPM_MeshBlockModifier_pg(PropertyGroup):
    target_mesh_name: get_target_mesh_name_prop()
    mesh_thickness: get_mesh_thickness_prop()

    def draw(self, context, layout):
        col = layout.column(align=False)
        col.prop_search(self, 'target_mesh_name', context.blend_data, 'objects')

        box = col.box().column()
        mesh = bpy.data.objects.get(self.target_mesh_name)
        box.enabled = (mesh is not None and mesh.type == 'MESH')
        box.prop(self, 'mesh_thickness')

    def copy_from(self, src):
        self.target_mesh_name = src.target_mesh_name
        self.mesh_thickness = src.mesh_thickness

################
class MeshBlockModifier(ProportionalMoverModifier):
    def __init__(self, prop):
        self.m_prop = prop
    
    def modify(self, pm, new_locations, which_to_move):
        mesh = bpy.data.objects.get(self.m_prop.target_mesh_name)
        if not mesh or mesh.type != 'MESH' or not mesh.visible_get():
            return new_locations, which_to_move

        hits, new_locations = mu.block_with_mesh(
            pm.orig_locations,
            pm.prev_locations,
            new_locations,
            mesh,
            which_to_move,
            self.m_prop.mesh_thickness)

        return new_locations, which_to_move

    def draw(self, context, layout):
        m_prop.draw(context, layout)

################################################################
classes = (
    DDDPM_MeshSnapModifier_pg,
    DDDPM_MeshBlockModifier_pg,
)

def registerClass():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregisterClass():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    registerClass()
