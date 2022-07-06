from collections import namedtuple
import math
import bpy
import bmesh

################################################################

SelectDividingLoopsResult = namedtuple('SelectDividingLoopsResult',
                                       ['selected', 'found'])

################
class DividingLoopFinder:
    """
    Class to find dividing loops.

    Parameters
    ----------------
    exclude_face_angle : float
      Do not include edges with a face angle of this value or more.    

    exclude_seam : boolean
      Do not include edges marked as SEAM.

    exclude_sharp : boolean
      Do not include edges marked as SHARP.

    exclude_bevel_weight : float
      Do not include edges with a bevel-weight value greater than or equal to this.

    exclude_crease : float
      Do not include edges with a crease value greater than or equal to this.
    """

    exclude_face_angle=math.tau
    exclude_seam=False
    exclude_sharp=False
    exclude_bevel_weight=1.1
    exclude_crease=1.1

    _bevel_weight=None          # BMLayerItem for bevel_weight
    _crease=None                # BMLayerItem for crease

    ################
    def __init__(self,
                 exclude_face_angle=math.tau,
                 exclude_seam=False,
                 exclude_sharp=False,
                 exclude_bevel_weight=1.1,
                 exclude_crease=1.1):
        self.exclude_face_angle = exclude_face_angle
        self.exclude_seam = exclude_seam
        self.exclude_sharp = exclude_sharp
        self.exclude_bevel_weight = exclude_bevel_weight
        self.exclude_crease = exclude_crease

    ################
    def _getDividingLoopSide(self, loop, edge, from_v_index):
        """
        Get one side of loop.

        Parameters
        ----------------
        loop : set (input and output)
          set of edges

        edge : BMEdge
          edge to check

        from_v_index : integer
          index of vertex determines a direction to traverse.
        """

        from_v = edge.verts[from_v_index]
        result = True
        while True:
            loop.add(edge)
            to_v = edge.other_vert(from_v)

            # 通常の頂点と辺で、かつ、辺が二つの四角形に接していなければダメ
            if not(to_v.is_valid and to_v.is_manifold and not to_v.is_wire and\
                   edge.is_valid and edge.is_manifold and not edge.is_wire and\
                   len(edge.link_faces) == 2 and\
                   len(edge.link_faces[0].edges) == 4 and\
                   len(edge.link_faces[1].edges) == 4):
                #print('abnormal')
                return False

            # 隠れている辺などの条件が一つでも含まれるならば
            # ループ全体を不可にする
            if edge.hide or\
               self.exclude_face_angle <= edge.calc_face_angle() or\
               self.exclude_seam and edge.seam or\
               self.exclude_sharp and not edge.smooth or\
               self._bevel_weight and self.exclude_bevel_weight <= edge[self._bevel_weight] or\
               self._crease and self.exclude_crease <= edge[self._crease]:
                #print(f'edge:{edge.index} crease:{edge[self._crease]}')
                result = False

            # to_v が端点なら終了
            len_link_edges = len(to_v.link_edges)
            if to_v.is_boundary and len_link_edges == 3:
                #print(f'Endpoint vert {to_v.index}')
                return result

            if len_link_edges != 4:
                return False
            else:
                # link_edges の中から edge と面を共有しない辺を探して次へ
                face0 = edge.link_faces[0]
                face1 = edge.link_faces[1]
                for le in to_v.link_edges:
                    if face0 not in le.link_faces and\
                       face1 not in le.link_faces:
                        if le in loop:
                            #print(f'Circling edge {edge.index}')
                            return result
                        edge = le
                        break
                else:
                    print(f'Illegal link_edges. edge:{edge.index}')
                    return False

                from_v = to_v

        print('Unknown flow')
        return False

    ################
    def _getDividingLoop(self, edge):
        """
        Parameters
        ----------------
        edge : BMEdge
          edge to check
        """

        loop = set()
        ans0 = self._getDividingLoopSide(loop, edge, 0)
        ans1 = self._getDividingLoopSide(loop, edge, 1)
        return ans0 and ans1, frozenset(loop)

    ################
    def selectDividingLoops(self, meshObj, choose=None):
        """
        Select all dividing loops.
        A "dividing loop" is an edge loop that simply bisects a rectangular face strip.
        Returns tuple of (selected count, found count) of dividing loops.

        Parameters
        ----------------
        choose : Function
          Function to decide if select dividing loops.
          bool function(index, set_of_edges, selected_count, found_count)
        """

        if not meshObj or meshObj.type != 'MESH':
            return None

        if not choose:
            choose = lambda a,b,c,d: True

        # Determine the mesh state
        bpy.context.view_layer.objects.active = meshObj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        bpy.ops.mesh.select_all(action='DESELECT')
        mesh = meshObj.data
        mesh.update()

        # initialize
        bm = bmesh.from_edit_mesh(mesh)
        bm.edges.ensure_lookup_table()

        # Ensure custom data exists.
        bm.edges.layers.bevel_weight.verify()
        self._bevel_weight = bm.edges.layers.bevel_weight.active

        bm.edges.layers.crease.verify()
        self._crease = bm.edges.layers.crease.active

        # scan all edges
        edgeTotal = len(bm.edges)
        edgeToLoop = [None] * edgeTotal
        foundLoops = []
        for edge in bm.edges:
            if edgeToLoop[edge.index] == None:
                ans, loop = self._getDividingLoop(edge)
                if ans:
                    foundLoops.append(loop)
                for le in loop:
                    edgeToLoop[le.index] = loop

        # decide whether to select loop
        foundCount = len(foundLoops)
        selectedCount = 0
        index = 0
        for index, loop in enumerate(foundLoops):
            if choose(index, loop, selectedCount, foundCount):
                selectedCount += 1
                for le in loop:
                    le.select_set(True)

        bmesh.update_edit_mesh(mesh)

        self._bevel_weight = None
        self._crease = None

        return SelectDividingLoopsResult(selectedCount, foundCount)
