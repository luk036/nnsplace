from typing import List

import networkx as nx
from networkx.algorithms import bipartite
from physdes.interval import Interval
from physdes.point import Point
from physdes.recti import Rect

from .min_cycle_ratio import min_cycle_ratio
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
        """_summary_

        Args:
            place (Union[List[Tuple[int, int]], Dict]): _description_
        """
        col = 0
        row = 0
        for v in self.hgr:
            place[0][v] = col
            place[1][v] = row
            self.count[0][col] += 1
            self.count[1][row] += 1
            col += 1
            if col == self.cfg.grid[0]:
                col = 0
                row += 1

    def calc_worst_wirelenght(self, place: List[List[int]]):
        """_summary_

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

    def calc_worst_wirelenght_axis(self, place: List[List[int]], dir):
        """_summary_

        Args:
            place (List[List[int]]): _description_
            dir (_type_): _description_

        Returns:
            _type_: _description_
        """
        worst_wire = 0
        for u, v in self.gr.edges():
            if u > v:  # only need to calculate one of the two edges
                continue
            gruv = abs(place[dir][v] - place[dir][u]) * self.cfg.delta[dir]
            if worst_wire < gruv:
                worst_wire = gruv
        return worst_wire

    def calc_total_hpwl(self, place: List[List[int]]):
        """_summary_

        Args:
            place (List[List[int]]): _description_

        Returns:
            _type_: _description_
        """
        total_hpwl_x = 0
        total_hpwl_y = 0
        for net in self.hgr.nets:
            adjs = iter(self.hgr.gr[net])
            v = next(adjs)
            p = Point(place[0][v], place[1][v])
            bbox = Rect(Interval(p.x, p.x), Interval(p.y, p.y))
            for v in adjs:
                q = Point(place[0][v], place[1][v])
                bbox = bbox.hull_with(q)
            total_hpwl_x += self.cfg.delta[0] * bbox.width()
            total_hpwl_y += self.cfg.delta[1] * bbox.height()
        return total_hpwl_x, total_hpwl_y

    def apply_howard(self, place: List[List[int]], dir):
        """_summary_

        Args:
            place (List[List[int]]): _description_
            dir (_type_): _description_

        Returns:
            _type_: _description_
        """
        ops = dir ^ 1
        grid_dir = self.cfg.grid[dir]
        grid_ops = self.cfg.grid[ops]

        def update_ok(p, d):
            if d < 0 or d >= grid_dir:
                return False
            if self.count[dir][d] >= grid_ops:
                return False
            self.count[dir][d] += 1
            self.count[dir][p] -= 1
            return True

        # set_default(self.gr, 'time', 1.0 / self.cfg.delta[dir])
        time = 1.0 / self.cfg.delta[dir]
        factor = self.cfg.delta[ops] / self.cfg.delta[dir]
        for u, v in self.gr.edges():
            # TODO: Find out how to formulate?
            gruv = abs(place[ops][v] - place[ops][u])
            self.gr[u][v]['cost'] = -gruv * factor
            # self.gr[u][v]['cost'] = 0
            self.gr[u][v]['time'] = time
        # r0 = -self.calc_worst_wirelenght_axis(place, ops)
        res, _ = min_cycle_ratio(self.gr, place[dir], update_ok, -1)

        return -res

    def legalize(self, place: List[List[int]], dir):
        """_summary_

        Args:
            place (List[List[int]]): _description_
            dir (_type_): _description_
        """
        ops = dir ^ 1
        bucket = [list() for _ in range(self.cfg.grid[ops])]
        for v in self.hgr:
            bucket[place[ops][v]].append(v)

        for lst in bucket:
            if not lst:
                continue
            # construct bipartite graph
            B = nx.Graph()
            # Add nodes with the node attribute "bipartite"
            B.add_nodes_from(lst, bipartite=0)

            m = 30
            for v in lst:
                # construct bipartite graph
                p = place[dir][v]
                q = p + self.hgr.number_of_modules()  # avoid same name
                B.add_node(q, bipartite=1)
                B.add_edge(v, q, weight=0)
                for i in range(1, m):  # TODO: increase m if no sol'n
                    if p - i >= 0:
                        B.add_node(q - i, bipartite=1)
                        B.add_edge(v, q - i, weight=i)
                    if p + i < self.cfg.grid[dir]:
                        B.add_node(q + i, bipartite=1)
                        B.add_edge(v, q + i, weight=i)

            # solve the matching problem
            i = m
            matched = False
            while not matched:
                try:
                    matches = bipartite.minimum_weight_full_matching(B)
                    for v in lst:
                        _ = matches[v]
                    matched = True
                    break
                except ValueError:
                    pass
                except KeyError:
                    pass

                # increase the number of edges if no sol'n
                for v in lst:
                    # construct bipartite graph
                    p = place[dir][v]
                    q = p + self.hgr.number_of_modules()  # avoid same name
                    if p - i >= 0:
                        B.add_node(q - i, bipartite=1)
                        B.add_edge(v, q - i, weight=i)
                    if p + i < self.cfg.grid[dir]:
                        B.add_node(q + i, bipartite=1)
                        B.add_edge(v, q + i, weight=i)
                i += 1

            # reassign the results
            for v in lst:
                q = matches[v] - self.hgr.number_of_modules()
                if place[dir][v] == q:
                    continue
                # Update position and self.count
                self.count[dir][place[dir][v]] -= 1
                self.count[dir][q] += 1
                place[dir][v] = q
        return

    def run(self, place: List[List[int]]):
        """_summary_

        Args:
            place (List[List[int]]): _description_

        Returns:
            _type_: _description_
        """
        dir = 0
        ops = 1
        worst0 = self.calc_worst_wirelenght(place)
        max_iter = 2000
        for niter in range(1, max_iter):
            _ = self.apply_howard(place, dir)
            self.legalize(place, ops)
            worst1 = self.calc_worst_wirelenght(place)
            # TODO: when to stop
            if worst1 > worst0:
                return niter, worst1
            worst0 = worst1
            dir, ops = ops, dir
        return niter, worst1
