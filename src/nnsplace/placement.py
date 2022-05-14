from typing import Dict, List, Union, Tuple
from .min_cycle_ratio import min_cycle_ratio, set_default

# from physdes.point import Point

from .netlist import Netlist
from .placement_cfg import NnsConfig
import networkx as nx
# from math import abs


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
        self.count = ([0] * cfg.grid[0], [0] * cfg.grid[1])  # two lists
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

    def run(self, place: Union[List[Tuple[int, int]], Dict]):
        # TODO add constraints
        dir = 0
        ops = 1

        def constraints_ok(p, d):
            if d < 0 or d > self.cfg.grid[dir]:
                return False
            if self.count[dir][d] >= self.cfg.grid[ops]:
                return False
            self.count[dir][d] += 1
            self.count[dir][p] -= 1
            return True

        finish = False
        while not finish:
            dist = [place[v][dir] for v in self.gr]
            # set_default(self.gr, 'time', 1.0 / self.cfg.delta[dir])
            for u, v in self.gr.edges():
                # gruv = abs(place[v][ops] - place[u][ops]) * self.cfg.delta[ops]
                # self.gr[u][v]['cost'] = -gruv / self.cfg.delta[dir]
                self.gr[u][v]['cost'] = 0.0
                self.gr[u][v]['time'] = 1.0 / self.cfg.delta[dir]
            res, _ = min_cycle_ratio(self.gr, dist, constraints_ok)
            for v in self.gr:
                place[v][dir] = dist[v]
            dir, ops = ops, dir
            finish = True  # TODO: when to stop?
        return
