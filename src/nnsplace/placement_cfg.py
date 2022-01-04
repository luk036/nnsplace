class fpga_glocal_placement_config:
    def __init__(self, x: int = 20, y: int = 5, delta_x=20, delta_y=20):
        self.grid_x = x
        self.grid_y = y
        self.delta_x = delta_x
        self.delta_y = delta_y
