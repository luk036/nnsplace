class NnsConfig:
    def __init__(self, x: int, y: int, delta_x, delta_y):
        self.grid = (x, y)
        self.delta = (delta_x, delta_y)
