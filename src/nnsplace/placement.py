from typing import Dict, List, Union

from physdes.point import point

from .netlist import Netlist
from .placement_cfg import fpga_glocal_placement_config


class nnsplace:
    def __init__(self, H: Netlist, cfg: fpga_glocal_placement_config):
        self.H = H
        self.cfg = cfg

    def init_placement(self, place: Union[List[point], Dict]):
        x = 0
        y = 0
        col = 0
        row = 0
        for v in self.H:
            place[v] = point(x, y)
            col += 1
            x += self.cfg.delta_x
            if col >= self.cfg.grid_x:
                col = 0
                x = 0
                row += 1
                y += self.cfg.delta_y
