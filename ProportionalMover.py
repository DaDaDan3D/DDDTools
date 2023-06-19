# -*- encoding:utf-8 -*-
import bpy
import numpy as np
import random
from mathutils import (
    Vector,
    Matrix,
)

from . import internalUtils as iu
from . import mathUtils as mu

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

# 十分に小さい値
EPSILON = 1e-9

# 軸の方向
GLOBAL_DIRECTIONS = {
    'GLOBAL_X': np.array((1, 0, 0)),
    'GLOBAL_Y': np.array((0, 1, 0)),
    'GLOBAL_Z': np.array((0, 0, 1)),
}

# 軸のインデックス
DIRECTION_ROWS = {
    'GLOBAL_X': 0,
    'GLOBAL_Y': 1,
    'GLOBAL_Z': 2,
    'LOCAL_X': 0,
    'LOCAL_Y': 1,
    'LOCAL_Z': 2,
    'LOCAL_EACH_X': 0,
    'LOCAL_EACH_Y': 1,
    'LOCAL_EACH_Z': 2,
    'GLOBAL_YZ': 0,
    'GLOBAL_ZX': 1,
    'GLOBAL_XY': 2,
    'LOCAL_YZ': 0,
    'LOCAL_ZX': 1,
    'LOCAL_XY': 2,
}

# ローテートする場合の次のタイプ
DIRECTION_NEXT = {
    'NONE': 'VIEW_CAMERA',
    'GLOBAL_X': 'LOCAL_X',
    'GLOBAL_Y': 'LOCAL_Y',
    'GLOBAL_Z': 'LOCAL_Z',
    'LOCAL_X': 'LOCAL_EACH_X',
    'LOCAL_Y': 'LOCAL_EACH_Y',
    'LOCAL_Z': 'LOCAL_EACH_Z',
    'LOCAL_EACH_X': 'NONE',
    'LOCAL_EACH_Y': 'NONE',
    'LOCAL_EACH_Z': 'NONE',
    'GLOBAL_YZ': 'LOCAL_YZ',
    'GLOBAL_ZX': 'LOCAL_ZX',
    'GLOBAL_XY': 'LOCAL_XY',
    'LOCAL_YZ': 'NONE',
    'LOCAL_ZX': 'NONE',
    'LOCAL_XY': 'NONE',
    'VIEW_CAMERA': 'CURSOR_3D',
    'CURSOR_3D': 'OBJECT_ORIGIN',
    'OBJECT_ORIGIN': 'NONE',
}

################
# 次のタイプを得る
def get_next_direction(direction, axis, is_plane):
    if axis == 'X':
        if is_plane:
            if direction == 'GLOBAL_YZ':        return 'LOCAL_YZ'
            elif direction == 'LOCAL_YZ':       return 'NONE'
            else:                               return 'GLOBAL_YZ'
        else:
            if direction == 'GLOBAL_X':         return 'LOCAL_X'
            elif direction == 'LOCAL_X':        return 'LOCAL_EACH_X'
            elif direction == 'LOCAL_EACH_X':   return 'NONE'
            else:                               return 'GLOBAL_X'
    elif axis == 'Y':
        if is_plane:
            if direction == 'GLOBAL_ZX':        return 'LOCAL_ZX'
            elif direction == 'LOCAL_ZX':       return 'NONE'
            else:                               return 'GLOBAL_ZX'
        else:
            if direction == 'GLOBAL_Y':         return 'LOCAL_Y'
            elif direction == 'LOCAL_Y':        return 'LOCAL_EACH_Y'
            elif direction == 'LOCAL_EACH_Y':   return 'NONE'
            else:                               return 'GLOBAL_Y'
    elif axis == 'Z':
        if is_plane:
            if direction == 'GLOBAL_XY':        return 'LOCAL_XY'
            elif direction == 'LOCAL_XY':       return 'NONE'
            else:                               return 'GLOBAL_XY'
        else:
            if direction == 'GLOBAL_Z':         return 'LOCAL_Z'
            elif direction == 'LOCAL_Z':        return 'LOCAL_EACH_Z'
            elif direction == 'LOCAL_EACH_Z':   return 'NONE'
            else:                               return 'GLOBAL_Z'
    else:
        if direction == 'NONE':                 return 'VIEW_CAMERA'
        elif direction == 'VIEW_CAMERA':        return 'CURSOR_3D'
        elif direction == 'CURSOR_3D':          return 'OBJECT_ORIGIN'
        else:                                   return 'NONE'

################
def get_direction_enum():
    return bpy.props.EnumProperty(
        name=_('方向タイプ'),
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
            ('CURSOR_3D', _('3D Cursor'), _('3D Cursor Position')),
            ('OBJECT_ORIGIN', _('Object Origin'), _('Object Origin Position')),
        ],
        default='NONE',
    )

################
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
        if direction_type in GLOBAL_DIRECTIONS:
            self.directions = GLOBAL_DIRECTIONS[direction_type]
        else:
            raise ValueError(f'Illegal direction_type: {direction_type}')

    # オブジェクトの行列から LOCAL_X|Y|Z の方向を設定する
    def set_directions_local(self, direction_type, obj):
        if direction_type in {'LOCAL_X', 'LOCAL_Y', 'LOCAL_Z'}:
            row = DIRECTION_ROWS[direction_type]
            self.directions = np.array(obj.matrix_world)[:3, row]

        elif direction_type in {'LOCAL_EACH_X', 'LOCAL_EACH_Y', 'LOCAL_EACH_Z'}:
            row = DIRECTION_ROWS[direction_type]
            self.directions = np.array(
                [np.array(obj.matrix_world @ b.matrix)[:3, row]
                 for b in obj.pose.bones])

        else:
            raise ValueError(f'Illegal direction_type: {direction_type}')

    # カメラからの方向を設定する
    def set_directions_from_view_camera(self):
        locations_h = mu.append_homogeneous_coordinate(self.orig_locations)
        orig_pnt = self.view_data.compute_local_ray_origins(locations_h,
                                                            Matrix())
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
