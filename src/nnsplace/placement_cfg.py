class NnsConfig:
    def __init__(self, x: int, y: int, delta_x: int, delta_y: int):
        self.grid = (x, y)
        self.delta = (delta_x, delta_y)
