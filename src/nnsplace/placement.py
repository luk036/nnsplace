from typing import Dict, List, Union, Tuple

# from physdes.point import Point

from .netlist import Netlist
from .placement_cfg import NnsConfig
import networkx as nx


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
        self.gr = create_flow_graph(hgr)
        self.col_count = [0] * cfg.grid_x
        self.row_count = [0] * cfg.grid_y

    def init_placement(self, place: Union[List[Tuple[int, int]], Dict]):
        """_summary_

        Args:
            place (Union[List[Tuple[int, int]], Dict]): _description_
        """
        col = 0
        row = 0
        for v in self.hgr:
            place[v] = (col, row)
            self.col_count[col] += 1
            self.row_count[row] += 1
            col += 1
            if col >= self.cfg.grid_x:
                col = 0
                row += 1
