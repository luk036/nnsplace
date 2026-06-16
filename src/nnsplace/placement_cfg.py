# The NnsConfig class represents the configuration for No-Nonsense Placement, including grid size and
# delta values.
from typing import Any, Optional


class NnsConfig:
    """No-Nonsense Placement configuration"""

    DEFAULT_RESERVED_COL: int = 27  # Column reserved for DSP/SRAM

    def __init__(
        self,
        x: int,
        y: int,
        delta_x: int,
        delta_y: int,
        reserved_col: Optional[int] = None,
    ):
        """
        Initialize the configuration for NNS placement.

        :param x: The width of the grid (number of columns in core)
        :type x: int
        :param y: The height of the grid (number of rows in core)
        :type y: int
        :param delta_x: Weight factor for x-axis wirelength cost
        :type delta_x: int
        :param delta_y: Weight factor for y-axis wirelength cost
        :type delta_y: int
        :param reserved_col: Column index reserved for DSP/SRAM (default: 27)
        :type reserved_col: int | None

        :raises ValueError: If grid dimensions or delta values are invalid
        """
        # Validate configuration
        if x < 3:
            raise ValueError(f"Grid width must be at least 3, got {x}")
        if y < 3:
            raise ValueError(f"Grid height must be at least 3, got {y}")
        if delta_x <= 0:
            raise ValueError(f"delta_x must be positive, got {delta_x}")
        if delta_y <= 0:
            raise ValueError(f"delta_y must be positive, got {delta_y}")
        if reserved_col is not None and (reserved_col < 1 or reserved_col > x):
            raise ValueError(
                f"reserved_col must be between 1 and {x}, got {reserved_col}"
            )

        self._grid = (x, y)
        self._delta = (delta_x, delta_y)
        self._reserved_col = (
            reserved_col if reserved_col is not None else self.DEFAULT_RESERVED_COL
        )

    @property
    def grid(self) -> tuple[int, int]:
        """Get the grid dimensions (width, height)."""
        return self._grid

    @property
    def delta(self) -> tuple[int, int]:
        """Get the delta values (delta_x, delta_y)."""
        return self._delta

    @property
    def reserved_col(self) -> int:
        """Get the column reserved for DSP/SRAM."""
        return self._reserved_col

    # Backward compatibility: allow attribute-style access
    def __getattr__(self, name: str) -> Any:
        # For backward compatibility with code using cfg.grid[0], cfg.delta[0], etc.
        if name == "grid":
            return self._grid
        if name == "delta":
            return self._delta
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
