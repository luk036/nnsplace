class NnsConfig:
    def __init__(self, x: int = 32, y: int = 32, delta_x=40, delta_y=40):
        self.grid_x = x
        self.grid_y = y
        self.delta_x = delta_x
        self.delta_y = delta_y
