class NnsConfig:
    def __init__(self, x: int = 32, y: int = 30, delta_x=40, delta_y=40):
        self.grid = (x, y)
        self.delta = (delta_x, delta_y)
