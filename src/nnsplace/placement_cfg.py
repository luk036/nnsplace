# The NnsConfig class represents the configuration for No-Nonsense Placement, including grid size and
# delta values.
class NnsConfig:
    "No-Nonsense Placement configuration"

    def __init__(self, x: int, y: int, delta_x: int, delta_y: int):
        """
        The function initializes an object with grid coordinates and delta values.
        
        :param x: The x parameter represents the initial x-coordinate of the grid. It is an integer value
        :type x: int
        :param y: The `y` parameter represents the initial y-coordinate of the grid
        :type y: int
        :param delta_x: The `delta_x` parameter represents the change in the x-coordinate of the grid. It
        determines how much the x-coordinate will be incremented or decremented when moving in the grid
        :type delta_x: int
        :param delta_y: The `delta_y` parameter represents the change in the y-coordinate of an object's
        position. It determines how much the object moves up or down on the grid
        :type delta_y: int
        """
        self.grid = (x, y)
        self.delta = (delta_x, delta_y)
