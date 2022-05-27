from typing import List

from random import shuffle
import networkx as nx
from networkx.algorithms import bipartite
from physdes.interval import Interval
# from physdes.point import Point
# from physdes.recti import Rect

# from .max_cycle_ratio import max_cycle_ratio
from .max_mean_cycle import max_mean_cycle
from .netlist import Netlist
from .placement_cfg import NnsConfig


def create_flow_graph(hgr: Netlist):
    """Create the flow graph

    Args:
        hgr (Netlist): _description_

    Returns:
        _type_: _description_
    """
    gr = nx.DiGraph()
    gr.add_nodes_from(v for v in hgr)
    for net in hgr.nets:
        for v1 in hgr.gr[net]:
            for v2 in hgr.gr[net]:
                if v1 == v2:
                    continue
                gr.add_edge(v1, v2)
                gr.add_edge(v2, v1)
    return gr


class NnsPlacer:
    # TODO: handle I/O pad

    def __init__(self, hgr: Netlist, cfg: NnsConfig):
        """_summary_

        Args:
            hgr (Netlist): _description_
            cfg (NnsConfig): _description_
        """
        self.hgr = hgr
        self.cfg = cfg
        self.count = ([0 for _ in range(cfg.grid[0])],
                      [0 for _ in range(cfg.grid[1])])  # two lists
        self.gr = create_flow_graph(hgr)
        # self.count[0] = [0] * cfg.grid_x
        # self.count[1] = [0] * cfg.grid_y

    def init_placement(self, place: List[List[int]]):
        """initial placement: just place one by one

        Args:
            place (List[List[int]): placement sol'n
        """
        col = 0
        row = 0
        lst = [v for v in self.hgr]
        shuffle(lst)
        for v in lst:
            place[0][v] = col
            place[1][v] = row
            self.count[0][col] += 1
            self.count[1][row] += 1
            col += 1
            if col == self.cfg.grid[0]:
                # re-begin from the next row
                col = 0
                row += 1

    def calc_worst_wirelenght(self, place: List[List[int]]):
        """Calculate the worst wirelenght

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

    def calc_worst_wirelenght_v(self, v, place: List[List[int]]):
        """Calculate the worst wirelenght w.r.t Module v

        Args:
            place (List[List[int]]): _description_

        Returns:
            _type_: _description_
        """
        worst_wire = 0
        for u in self.gr.neighbors(v):
            gruv = abs(place[0][v] - place[0][u]) * self.cfg.delta[0] \
                + abs(place[1][v] - place[1][u]) * self.cfg.delta[1]
            if worst_wire < gruv:
                worst_wire = gruv
        return worst_wire

    def calc_worst_wirelenght_axis(self, place: List[List[int]], axis):
        """Calculate the worst wirelenght w.r.t one axis

        Args:
            place (List[List[int]]): _description_
            axis (_type_): _description_

        Returns:
            _type_: _description_
        """
        worst_wire = 0
        for u, v in self.gr.edges():
            if u > v:  # only need to calculate one of the two edges
                continue
            gruv = abs(place[axis][v] - place[axis][u])
            if worst_wire < gruv:
                worst_wire = gruv
        return worst_wire * self.cfg.delta[axis]

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

    def calc_total_hull_lenght(self, dist: List[int], axis) -> int:
        """Calculate the total hull w.r.t one axis

        Args:
            dist (List[int]): _description_
            axis (int): _description_

        Returns:
            int: _description_
        """
        total_hull_lenght = 0
        for net in self.hgr.nets:
            adjs = iter(self.hgr.gr[net])
            v = next(adjs)
            p = dist[v]
            hull = Interval(p, p)
            for v in adjs:
                hull = hull.hull_with(dist[v])
            total_hull_lenght += hull.len()
        return total_hull_lenght * self.cfg.delta[axis]

    def calc_total_HPWL(self, place: List[List[int]]):
        """Calculate total HPWL

        Args:
            place (List[List[int]]): _description_

        Returns:
            int: _description_
        """
        return self.total_hull_lenght(place[0], 0) \
            + self.total_hull_lenght(place[1], 1)

    def apply_howard(self, place: List[List[int]], axis1: int):
        """_summary_

        Args:
            place (List[List[int]]): _description_
            axis1 (int): _description_

        Returns:
            _type_: _description_
        """
        # TODO: sort the criticality

        axis2 = axis1 ^ 1
        grid_axis1 = self.cfg.grid[axis1]
        grid_axis2 = self.cfg.grid[axis2]
        count = self.count[axis1]

        def update_ok(p, d):
            if d < 0 or d >= grid_axis1:
                return False
            if self.count[axis1][d] >= grid_axis2:
                return False
            count[d] += 1
            count[p] -= 1
            return True

        # set_default(self.gr, 'time', 1.0 / self.cfg.delta[dir])
        # time = 1.0 / self.cfg.delta[axis1]
        factor = self.cfg.delta[axis2] / self.cfg.delta[axis1]
        dist = place[axis2]
        worst = 0
        for u, v in self.gr.edges():
            # TODO: Find out how to formulate?
            gruv = abs(dist[v] - dist[u])
            self.gr[u][v]['weight'] = gruv
            self.gr[u][v]['cost'] = gruv * factor
            # self.gr[u][v]['cost'] = 0
            # self.gr[u][v]['time'] = time
            if worst < gruv:
                worst = gruv
        # r0 = self.calc_worst_wirelenght_axis(place, oppo)
        return max_mean_cycle(self.gr, place[axis1], update_ok, 0)

    def add_bipartite_edge(self, lst, B, place, i, grid, axis):
        # increase the number of edges if no sol'n
        for v in lst:
            # construct bipartite graph
            p = place[axis][v]
            q = p + self.hgr.number_of_modules()  # avoid same name
            weight0 = self.calc_worst_wirelenght_v(v, place)
            if p - i >= 0:
                place[axis][v] -= i  # temporily set the position
                weight1 = self.calc_worst_wirelenght_v(v, place)
                place[axis][v] += i  # reset the position
                B.add_node(q - i, bipartite=1)
                B.add_edge(v, q - i, weight=weight1 - weight0)
            if p + i < grid:
                place[axis][v] += i  # temporily set the position
                weight1 = self.calc_worst_wirelenght_v(v, place)
                place[axis][v] -= i  # reset the position
                B.add_node(q + i, bipartite=1)
                B.add_edge(v, q + i, weight=weight1 - weight0)

    def legalize(self, place: List[List[int]], axis):
        """_summary_

        Args:
            place (List[List[int]]): _description_
            axis (_type_): _description_
        """
        bucket = [list() for _ in range(self.cfg.grid[axis ^ 1])]
        dist = place[axis ^ 1]
        for v in self.hgr:
            bucket[dist[v]].append(v)

        dist = place[axis]
        count = self.count[axis]
        grid = self.cfg.grid[axis]
        for lst in filter(lambda lst: lst, bucket):
            # construct bipartite graph
            B = nx.Graph()
            # Add nodes with the node attribute "bipartite"
            B.add_nodes_from(lst, bipartite=0)

            m = 30
            for v in lst:
                # construct bipartite graph
                q = dist[v] + self.hgr.number_of_modules()  # avoid same name
                B.add_node(q, bipartite=1)
                B.add_edge(v, q, weight=0)
            for i in range(1, m):
                self.add_bipartite_edge(lst, B, place, i, grid, axis)

            # solve the matching problem
            i = m
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
                i += 1

            # reassign the results
            for v in lst:
                q = matches[v] - self.hgr.number_of_modules()
                if dist[v] == q:
                    continue
                # Update position and self.count
                count[dist[v]] -= 1
                count[q] += 1
                dist[v] = q
        return

    def run(self, place: List[List[int]], max_iter=2000):
        """_summary_

        Args:
            place (List[List[int]]): _description_

        Returns:
            _type_: _description_
        """
        worst0 = self.calc_worst_wirelenght(place)
        place0 = [place[0].copy(), place[1].copy()]
        for niter in range(1, max_iter):
            r1, C1 = self.apply_howard(place, 0)
            self.legalize(place, 1)
            r2, C2 = self.apply_howard(place, 1)
            self.legalize(place, 0)
            worst1 = self.calc_worst_wirelenght(place)
            # TODO: when to stop
            if worst1 > worst0:
                place = place0
                return niter, worst1
            worst0 = worst1
            place0 = [place[0].copy(), place[1].copy()]
        return niter, worst1
