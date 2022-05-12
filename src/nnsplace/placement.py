from typing import Dict, List, Union

from physdes.point import Point

from .netlist import Netlist
from .placement_cfg import NnsConfig


class NnsPlacer:
    def __init__(self, H: Netlist, cfg: NnsConfig):
        self.H = H
        self.cfg = cfg

    def init_placement(self, place: Union[List[Point], Dict]):
        x = 0
        y = 0
        col = 0
        row = 0
        grid_x = round(self.cfg.grid_x * 0.9)
        for v in self.H:
            place[v] = Point(x, y)
            col += 1
            x += self.cfg.delta_x
            if col >= grid_x:
                col = 0
                x = 0
                row += 1
                y += self.cfg.delta_y
