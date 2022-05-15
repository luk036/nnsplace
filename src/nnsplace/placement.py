from typing import Dict, List, Union, Tuple
from .min_cycle_ratio import min_cycle_ratio
from .netlist import Netlist
from .placement_cfg import NnsConfig
import networkx as nx
from physdes.point import Point
from physdes.recti import Rect
from physdes.interval import Interval
from networkx.algorithms import bipartite


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

    def init_placement(self, place: Union[List[Tuple[int, int]], Dict]):
        """_summary_

        Args:
            place (Union[List[Tuple[int, int]], Dict]): _description_
        """
        col = 0
        row = 0
        for v in self.hgr:
            place[v] = [col, row]
            self.count[0][col] += 1
            self.count[1][row] += 1
            col += 1
            if col == self.cfg.grid[0]:
                col = 0
                row += 1

    def calc_worst_wirelenght(self, place: Union[List[Tuple[int, int]], Dict]):
        worst_wire = 0
        for u, v in self.gr.edges():
            if u > v:  # only need to calculate one of the two edges
                continue
            gruv = abs(place[v][0] - place[u][0]) * self.cfg.delta[0] \
                + abs(place[v][1] - place[u][1]) * self.cfg.delta[1]
            if worst_wire < gruv:
                worst_wire = gruv
        return worst_wire

    def calc_total_hpwl(self, place: Union[List[Tuple[int, int]], Dict]):
        total_hpwl = 0
        for net in self.hgr.nets:
            adjs = iter(self.hgr.gr[net])
            col, row = place[next(adjs)]
            p = Point(col, row)
            bbox = Rect(Interval(p.x, p.x), Interval(p.y, p.y))
            for v in adjs:
                col, row = place[v]
                q = Point(col, row)
                bbox = bbox.hull_with(q)
            total_hpwl += self.cfg.delta[0] * bbox.width() \
                + self.cfg.delta[1] * bbox.height()
        return total_hpwl

    def apply_howard(self, place: List[Tuple[int, int]], dir):
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

        dist = [place[v][dir] for v in self.gr]
        # set_default(self.gr, 'time', 1.0 / self.cfg.delta[dir])
        time = 1.0 / self.cfg.delta[dir]
        factor = self.cfg.delta[ops] / self.cfg.delta[dir]
        for u, v in self.gr.edges():
            # TODO: Find out how to formulate?
            gruv = abs(place[v][ops] - place[u][ops])
            self.gr[u][v]['cost'] = -gruv * factor
            # self.gr[u][v]['cost'] = 0
            self.gr[u][v]['time'] = time
        res, _ = min_cycle_ratio(self.gr, dist, update_ok)
        for v in self.gr:
            place[v][dir] = dist[v]

        return res

    def legalize(self, place: Union[List[Tuple[int, int]], Dict], dir):
        ops = dir ^ 1
        bucket = [list() for _ in range(self.cfg.grid[ops])]
        for v in self.hgr:
            bucket[place[v][ops]].append(v)
        for lst in bucket:
            if not lst:
                continue
            # construct bipartite graph
            B = nx.Graph()
            # Add nodes with the node attribute "bipartite"
            B.add_nodes_from(lst, bipartite=0)
            for v in lst:
                # construct bipartite graph
                p = place[v][dir]
                q = p + self.hgr.number_of_modules()  # avoid same name
                B.add_node(q, bipartite=1)
                B.add_edge(v, q, weight=0)
                m = 12
                for i in range(1, m):  # TODO: increase m if no sol'n
                    if p - i >= 0:
                        B.add_node(q - i, bipartite=1)
                        B.add_edge(v, q - i, weight=i)
                    if p + i < self.cfg.grid[dir]:
                        B.add_node(q + i, bipartite=1)
                        B.add_edge(v, q + i, weight=i)
            # solve the matching problem
            matches = bipartite.minimum_weight_full_matching(B)
            # reassign the results
            for v in lst:
                q = matches[v] - self.hgr.number_of_modules()
                if place[v][dir] == q:
                    continue
                # Update position and self.count
                self.count[dir][place[v][dir]] -= 1
                self.count[dir][q] += 1
                place[v][dir] = q
        return

    def run(self, place: Union[List[Tuple[int, int]], Dict]):
        dir = 0
        ops = 1
        for _ in range(20):
            _ = self.apply_howard(place, dir)
            self.legalize(place, ops)
            dir, ops = ops, dir
        # TODO: when to stop
        return
