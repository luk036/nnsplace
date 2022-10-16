from typing import List
from math import floor

import networkx as nx
from random import shuffle
from networkx.algorithms import bipartite
from physdes.interval import Interval

from .min_parametric import min_parametric
from .netlist import Netlist
from .placement_cfg import NnsConfig
from .lict import TinyDiGraph


def create_flow_graph(hgr: Netlist) -> TinyDiGraph:
    """Create the flow graph

    TODO: Utilize pin directions of a net (in-to-out)

    Args:
        hgr (Netlist): _description_

    Returns:
        TinyDiGraph: _description_
    """
    gr = TinyDiGraph(num_modules=hgr.num_modules, num_pads=hgr.num_pads)
    num_cells = hgr.num_modules - hgr.num_pads
    gr.init_nodes(hgr.num_modules)
    for net in hgr.nets:
        for v1 in hgr.gr[net]:
            # assume return an integer
            for v2 in hgr.gr[net]:
                if v1 >= num_cells:
                    continue   # ignore pad to pad connections
                gr.add_edge(v1, v2)
                gr.add_edge(v2, v1)
    return gr


class NnsPlacer:
    # TODO: handle optimization aware of I/O pad, DSP, SRAM
    # TODO: handle ASIC placement

    def __init__(self, hgr: Netlist, cfg: NnsConfig):
        """_summary_

        Notes:
            0 - x-axis
            1 - y-axis
            count[0] - how many cells on each row, including 2 I/O rows
            count[1] - how many cells on each column, including 2 I/O columns

        Args:
            hgr (Netlist): _description_
            cfg (NnsConfig): _description_
        """
        self.hgr = hgr
        self.cfg = cfg
        self.count = ([0 for _ in range(cfg.grid[0]+2)],  # plus 2 I/O
                      [0 for _ in range(cfg.grid[1]+2)])  # two lists
        self.gr = create_flow_graph(hgr)
        self.num_cells = hgr.num_modules - hgr.num_pads

    def init_placement(self, place: List[List[int]]):
        """initial placement: just place one by one including I/O pad

        Args:
            place (List[List[int]): placement sol'n
        """
        col = 1
        row = 1
        lst = [v for v in self.hgr]
        shuffle(lst)
        for v in lst:
            place[0][v] = col
            place[1][v] = row
            self.count[0][col] += 1
            self.count[1][row] += 1
            if col == self.cfg.grid[0]:
                # re-begin from the next row
                col = 1
                row += 1
            else:
                col += 1

    def calc_worst_wirelength(self, place: List[List[int]]):
        """Calculate the worst wirelength

        Args:
            place (List[List[int]]): _description_

        Returns:
            _type_: _description_
        """
        worst_wire = 0
        for u, v in self.gr.edges():
            if u > v:  # only need to calculate one of the two edges
                continue
            gruv = abs(place[0][v] - place[0][u]) * self.cfg.delta[0] \
                + abs(place[1][v] - place[1][u]) * self.cfg.delta[1]
            if worst_wire < gruv:
                worst_wire = gruv
        return worst_wire

    # def calc_worst_wirelength_v(self, v, place: List[List[int]]):
    #     """Calculate the worst wirelength w.r.t Module v
    #
    #     Args:
    #         place (List[List[int]]): _description_
    #
    #     Returns:
    #         _type_: _description_
    #     """
    #     worst_wire = 0
    #     for u in self.gr.neighbors(v):
    #         gruv = abs(place[0][v] - place[0][u]) * self.cfg.delta[0] \
    #             + abs(place[1][v] - place[1][u]) * self.cfg.delta[1]
    #         if worst_wire < gruv:
    #             worst_wire = gruv
    #     return worst_wire

    # def calc_worst_wirelength_axis(self, place: List[List[int]], axis):
    #     """Calculate the worst wirelength w.r.t one axis

    #     Args:
    #         place (List[List[int]]): _description_
    #         axis (_type_): _description_

    #     Returns:
    #         _type_: _description_
    #     """
    #     worst_wire = 0
    #     for u, v in self.gr.edges():
    #         if u > v:  # only need to calculate one of the two edges
    #             continue
    #         gruv = abs(place[axis][v] - place[axis][u])
    #         if worst_wire < gruv:
    #             worst_wire = gruv
    #     return worst_wire * self.cfg.delta[axis]

    # def calc_total_hpwl(self, place: List[List[int]]):
    #     """_summary_
    #
    #     Args:
    #         place (List[List[int]]): _description_
    #
    #     Returns:
    #         _type_: _description_
    #     """
    #     total_hpwl_x = 0
    #     total_hpwl_y = 0
    #     for net in self.hgr.nets:
    #         adjs = iter(self.hgr.gr[net])
    #         v = next(adjs)
    #         p = Point(place[0][v], place[1][v])
    #         bbox = Rect(Interval(p.x, p.x), Interval(p.y, p.y))
    #         for v in adjs:
    #             q = Point(place[0][v], place[1][v])
    #             bbox = bbox.hull_with(q)
    #         total_hpwl_x += bbox.width()
    #         total_hpwl_y += bbox.height()
    #     return total_hpwl_x * self.cfg.delta[0], \
    #         total_hpwl_y * self.cfg.delta[1]

    def calc_total_hull_length(self, dist: List[int], axis) -> int:
        """Calculate the total hull w.r.t one axis

        Args:
            dist (List[int]): _description_
            axis (int): _description_

        Returns:
            int: _description_
        """
        total_hull_length = 0
        for net in self.hgr.nets:
            adjs = iter(self.hgr.gr[net])
            # v = next(adjs)
            # p = dist[v]
            # hull = Interval(p, p)
            hull = Interval(1000000000000, -1000000000000)
            for v in adjs:
                hull = hull.hull_with(dist[v])
            total_hull_length += hull.length()
        return total_hull_length * self.cfg.delta[axis]

    def calc_total_HPWL(self, place: List[List[int]]):
        """Calculate total HPWL

        Args:
            place (List[List[int]]): _description_

        Returns:
            int: _description_
        """
        return self.calc_total_hull_length(place[0], 0) \
            + self.calc_total_hull_length(place[1], 1)

    def apply_howard(self, place: List[List[int]], axis1: int):
        """_summary_

        Args:
            place (List[List[int]]): _description_
            axis1 (int): _description_

        Returns:
            _type_: _description_
        """
        axis2 = axis1 ^ 1

        def update_ok(p, d):
            if d <= 0 or d > self.cfg.grid[axis1]:
                # don't outside the place area
                return False
            if self.count[axis1][d] >= self.cfg.grid[axis2]:
                # don't over-crowd in one line
                return False
            self.count[axis1][d] += 1
            self.count[axis1][p] -= 1
            return True

        def calc_weight(r, e):
            """[summary]

            Arguments:
                r ([type]): [description]
                e ([type]): [description]

            Returns:
                [type]: [description]
            """
            u, v = e
            return floor((r - self.gr[u][v]['cost']) / self.cfg.delta[axis1])

        def zero_cancel(C):
            """Calculate the zero cancelation of the cycle

            Arguments:
                C {list}: cycle list

            Returns:
                cycle ratio
            """
            total_cost = sum(self.gr[u][v]['cost'] for (u, v) in C)
            return total_cost / len(C)

        # TODO: should provide an API for calling the (monotone) wire-model
        # TODO: should use `Fraction` to avoid floating point arithmetic
        # floating point arithmetic???

        # dt[0] * abs(p[0][i] - p[0][j]) + dt[1] * abs(p[1][i] - p[1][j]) < r
        worst = 0
        for u, v in self.gr.edges():
            # TODO: Find out how to formulate?
            gruv = abs(place[axis2][v] - place[axis2][u])
            # self.gr[u][v]['weight'] = gruv  # for bpq in NegCycleFinder ???
            self.gr[u][v]['cost'] = gruv * self.cfg.delta[axis2]
            if worst < gruv:
                worst = gruv
        # initial worst/2 or 0 or others?
        return min_parametric(self.gr, 0, calc_weight, zero_cancel,
                              place[axis1], update_ok)

    def add_bipartite_edge(self, lst: List[int], B: nx.Graph,
                           place: List[List[int]], i: int,
                           grid: int, axis: int):
        """_summary_

        Args:
            lst (List[int]): _description_
            B (nx.Graph): _description_
            place (List[List[int]]): _description_
            i (int): _description_
            grid (int): _description_
            axis (int): _description_
        """
        # increase the number of edges if no sol'n
        for v in lst:
            # construct bipartite graph
            p = place[axis][v]
            q = p + self.hgr.number_of_modules()  # avoid same name
            # weight0 = self.calc_worst_wirelength_v(v, place)
            if p - i > 0:
                # place[axis][v] -= i  # temporily set the position
                # weight1 = self.calc_worst_wirelength_v(v, place)
                # place[axis][v] += i  # reset the position
                B.add_node(q - i, bipartite=1)
                B.add_edge(v, q - i, weight=i)
                # B.add_edge(v, q - i, weight=weight1 - weight0)
            if p + i <= grid:
                # place[axis][v] += i  # temporily set the position
                # weight1 = self.calc_worst_wirelength_v(v, place)
                # place[axis][v] -= i  # reset the position
                B.add_node(q + i, bipartite=1)
                B.add_edge(v, q + i, weight=i)
                # B.add_edge(v, q + i, weight=weight1 - weight0)

    def legalize(self, lst: List[int], place: List[List[int]], axis: int):
        """Legalization by solving the bipartite matching problem

        Args:
            lst (List[int]): _description_
            place (List[List[int]]): _description_
            axis (int): _description_
            io (bool, optional): _description_. Defaults to False.
        """
        dist = place[axis]
        # count = self.count[axis]
        grid = self.cfg.grid[axis]

        # construct bipartite graph
        B = nx.Graph()
        # Add nodes with the node attribute "bipartite"
        B.add_nodes_from(lst, bipartite=0)

        neighborhood = 15  # magic number for defining the neigborhood
        for v in lst:
            # construct bipartite graph
            q = dist[v] + self.hgr.number_of_modules()  # avoid same name
            B.add_node(q, bipartite=1)
            B.add_edge(v, q, weight=0)  # closest position
        for i in range(1, neighborhood):
            self.add_bipartite_edge(lst, B, place, i, grid, axis)

        # solve the matching problem
        i = neighborhood
        matched = False
        while not matched:
            try:
                matches = bipartite.minimum_weight_full_matching(B)
                for v in lst:
                    _ = matches[v]
                matched = True
            except ValueError:
                self.add_bipartite_edge(lst, B, place, i, grid, axis)
            except KeyError:
                self.add_bipartite_edge(lst, B, place, i, grid, axis)
            except nx.exception.AmbiguousSolution:
                self.add_bipartite_edge(lst, B, place, i, grid, axis)
            i += 1  # if no match, increase the neigborhood

        # reassign the results
        for v in lst:
            q = matches[v] - self.hgr.number_of_modules()
            if dist[v] == q:
                continue
            # Update position and self.count
            self.count[axis][dist[v]] -= 1
            self.count[axis][q] += 1
            dist[v] = q

    def legalize_modules(self, place: List[List[int]], axis: int):
        """_summary_

        Args:
            place (List[List[int]]): _description_
            axis (int): _description_
        """
        bucket = [list() for _ in range(self.cfg.grid[axis ^ 1] + 2)]
        # bucket = self.bucket[axis]
        # for lst in bucket:
        #     lst.clear()
        dist = place[axis ^ 1]
        # if care_io:
        #     for v in self.hgr:
        #         if v < self.hgr.num_modules - self.hgr.num_pads:
        #             bucket[dist[v]].append(v)
        # else:
        #     for v in self.hgr:
        #         bucket[dist[v]].append(v)
        for v in self.gr:
            bucket[dist[v]].append(v)
        for lst in filter(lambda lst: lst, bucket):  # lst is not null or empty
            self.legalize(lst, place, axis)

    def calc_average_position(self, vp: int, place: List[List[int]]):
        posx = 0
        posy = 0
        count = 0
        for vi in self.gr[vp]:
            # if vi >= self.num_cells:  # only non-io modules
            #     continue
            posx += place[0][vi]
            posy += place[1][vi]
            count += 1
        posx //= count
        posy //= count
        return posx, posy

    def choose_nearest_iopad(self, place: List[List[int]]):
        """Choose the nearest iopad in phase 2

           TODO: should apply Howard algorithm because one pad can
           connect to multiple modules and one modules can connect
           to multiple pad.

        Args:
            place (List[List[int]]): _description_
        """
        # choose the nearest I/O
        grid_x = self.cfg.grid[0]
        half_x = grid_x // 2
        grid_y = self.cfg.grid[1]
        half_y = grid_y // 2
        n = self.hgr.number_of_modules()
        for i in range(n - self.hgr.num_pads, n):
            # loop through io pad
            vp = self.hgr.modules[i]
            posx, posy = self.calc_average_position(vp, place)
            # nbrs = list(self.gr.neighbors(vp))
            # TODO: pad attached to more than one node
            # v = nbrs[0]  # workaround: take the first one only

            if posx <= half_x and self.count[0][0] < grid_y:
                which_x = 0  # left
                len_x = posx
            else:  # if self.count[0][grid_x + 1] < grid_y:
                # assume enough empty IOs
                which_x = 1  # right
                len_x = grid_x - posx

            if posy <= half_y and self.count[1][0] < grid_x:
                which_y = 0  # top
                len_y = posy
            else:  # if self.count[1][grid_y + 1] < grid_x:
                # assume enough empty IOs
                which_y = 1  # bottom
                len_y = grid_y - posy

            self.count[0][place[0][vp]] -= 1  # ???
            self.count[1][place[1][vp]] -= 1  # ???
            if len_x * self.cfg.delta[0] < len_y * self.cfg.delta[1]:
                if which_x == 0:
                    place[0][vp] = 0
                else:
                    place[0][vp] = grid_x + 1
                place[1][vp] = posy
            else:
                if which_y == 0:
                    place[1][vp] = 0
                else:
                    place[1][vp] = grid_y + 1
                place[0][vp] = posx

            self.count[1][place[1][vp]] += 1
            self.count[0][place[0][vp]] += 1

    # def choose_nearest_iopad(self, place: List[List[int]]):
    #     """_summary_
    #
    #     Args:
    #         place (List[List[int]]): _description_
    #     """
    #     # choose the nearest I/O
    #     n = self.hgr.number_of_modules()
    #     grid_x = self.cfg.grid[0]
    #     half_x = grid_x // 2
    #     grid_y = self.cfg.grid[1]
    #     half_y = grid_y // 2
    #     which_x = None
    #     which_y = None
    #     len_x = grid_x
    #     len_y = grid_y
    #     for i in range(n - self.hgr.num_pads, n):
    #         v = self.hgr.modules[i]
    #         if place[0][v] <= half_x and self.count[0][0] < grid_y:
    #             which_x = 0  # left
    #             len_x = place[0][v]
    #         elif self.count[0][grid_x + 1] < grid_y:
    #             which_x = 1  # right
    #             len_x = grid_x - place[0][v]
    #
    #         if place[1][v] <= half_y and self.count[1][0] < grid_x:
    #             which_y = 0  # top
    #             len_y = place[1][v]
    #         elif self.count[1][grid_y + 1] < grid_x:
    #             which_y = 1  # bottom
    #             len_y = grid_y - place[1][v]
    #
    #         self.count[0][place[0][v]] -= 1
    #         self.count[1][place[1][v]] -= 1
    #         if len_x * self.cfg.delta[0] < len_y * self.cfg.delta[1]:
    #             if which_x == 0:
    #                 place[0][v] = 0
    #             else:
    #                 place[0][v] = grid_x + 1
    #             self.count[0][place[0][v]] += 1
    #         else:
    #             if which_y == 0:
    #                 place[1][v] = 0
    #             else:
    #                 place[1][v] = grid_y + 1
    #             self.count[1][place[1][v]] += 1

    def legalize_iopad(self, place: List[List[int]], axis: int):
        """_summary_

        Args:
            place (List[List[int]]): _description_
        """
        bucket: List[List] = [list() for _ in range(2)]
        n = self.hgr.number_of_modules()
        for i in range(n - self.hgr.num_pads, n):
            v = self.hgr.modules[i]
            if place[axis][v] == 0:
                bucket[0].append(v)
            elif place[axis][v] == self.cfg.grid[axis] + 1:
                bucket[1].append(v)
        if bucket[0]:
            self.legalize(bucket[0], place, axis ^ 1)
        if bucket[1]:
            self.legalize(bucket[1], place, axis ^ 1)

    def io_assign(self, place: List[List[int]]):
        """_summary_

        Args:
            place (List[List[int]]): _description_
        """
        self.choose_nearest_iopad(place)
        self.legalize_iopad(place, 0)
        self.legalize_iopad(place, 1)

    # def io_reassign(self, place: List[List[int]]):
    #     """_summary_
    #
    #     Args:
    #         place (List[List[int]]): _description_
    #     """
    #     self.choose_nearest_iopad(place)
    #     self.legalize_iopad(place)

    def optimize(self, place: List[List[int]], max_iter: int):
        """_summary_

        Args:
            place (List[List[int]]): _description_
            max_iter (int): _description_

        Returns:
            _type_: _description_
        """
        worst0 = self.calc_worst_wirelength(place)
        place0 = [place[0].copy(), place[1].copy()]
        for niter in range(max_iter):
            r1, C1 = self.apply_howard(place, 0)
            self.legalize_modules(place, 1)
            self.choose_nearest_iopad(place)
            r2, C2 = self.apply_howard(place, 1)
            self.legalize_modules(place, 0)
            self.choose_nearest_iopad(place)

            # TODO: How to utilize r1, C1, ...
            worst1 = self.calc_worst_wirelength(place)
            print(f"    x-y: {worst1}")
            # TODO: when to stop
            if worst1 > worst0:
                place = [place0[0].copy(), place0[1].copy()]
                return niter, worst0
            worst0 = worst1
            place0 = [place[0].copy(), place[1].copy()]
        return max_iter, worst1

    def run(self, place: List[List[int]], max_iter=200):
        """_summary_

        Args:
            place (List[List[int]]): _description_
            max_iter (int, optional): _description_. Defaults to 2000.

        Returns:
            _type_: _description_
        """
        # niter, worst = self.optimize(place, max_iter)
        # self.init_placement(place)
        # _, worst0 = self.optimize(place, max_iter)
        self.io_assign(place)
        worst0 = self.calc_worst_wirelength(place)
        place0 = [place[0].copy(), place[1].copy()]
        print(f"init: {worst0}")
        for niter in range(max_iter):
            _, _ = self.optimize(place, max_iter)
            # self.io_assign(place)
            worst1 = self.calc_worst_wirelength(place)
            print(f"run {worst1}")
            if worst1 > worst0:
                place = [place0[0].copy(), place0[1].copy()]
                return niter, worst0
            worst0 = worst1
            place0 = [place[0].copy(), place[1].copy()]
        return max_iter, worst0
