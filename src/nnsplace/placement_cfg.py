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
        delta_x: int = 1,
        delta_y: int = 1,
        reserved_col: Optional[int] = None,
        line_cap_ratio: Optional[float] = None,
        neighborhood: Optional[int] = None,
        max_neighborhood: Optional[int] = None,
    ):
        """
        Initialize the configuration for NNS placement.

        :param x: The width of the grid (number of columns in core)
        :type x: int
        :param y: The height of the grid (number of rows in core)
        :type y: int
        :param delta_x: Weight factor for x-axis wirelength cost (default: 1)
        :type delta_x: int
        :param delta_y: Weight factor for y-axis wirelength cost (default: 1)
        :type delta_y: int
        :param reserved_col: Column index reserved for DSP/SRAM.  When omitted
            (default), the class default ``DEFAULT_RESERVED_COL`` (27) is used
            if it fits the grid (``x >= 27``); otherwise no column is reserved.
            Pass an explicit index (``1 <= v <= x``) to override.
        :type reserved_col: int | None
        :param line_cap_ratio: If set, cap the per-line limit of the core to
            ``ceil(sqrt(num_cells) * line_cap_ratio)``.  This keeps small
            netlists from crowding too many cells onto a single line on a
            large grid.  Leave ``None`` (default) to use the grid size as the
            per-line limit.  The I/O ring keeps its own capacity, derived
            from the number of pads, independent of this value.
        :type line_cap_ratio: float | None
        :param neighborhood: Initial +/- radius of the local legalization
            window.  ``None`` (default) uses the placer's built-in default
            (11).  Raise it when a single grid line is crowded.
        :type neighborhood: int | None
        :param max_neighborhood: Safety cap on how far the legalization window
            may widen before falling back to the global free-slot search.
            ``None`` (default) uses the placer's built-in default (50).
        :type max_neighborhood: int | None

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
        if line_cap_ratio is not None and line_cap_ratio <= 0:
            raise ValueError(f"line_cap_ratio must be positive, got {line_cap_ratio}")
        if neighborhood is not None and neighborhood < 1:
            raise ValueError(f"neighborhood must be positive, got {neighborhood}")
        if max_neighborhood is not None and max_neighborhood < 1:
            raise ValueError(
                f"max_neighborhood must be positive, got {max_neighborhood}"
            )

        self._grid = (x, y)
        self._delta = (delta_x, delta_y)
        if reserved_col is not None:
            self._reserved_col: Optional[int] = reserved_col
        elif x >= self.DEFAULT_RESERVED_COL:
            self._reserved_col = self.DEFAULT_RESERVED_COL
        else:
            # The default DSP/SRAM column does not fit this grid; reserve nothing.
            self._reserved_col = None
        self._line_cap_ratio = line_cap_ratio
        self._neighborhood = neighborhood
        self._max_neighborhood = max_neighborhood

    @property
    def grid(self) -> tuple[int, int]:
        return self._grid

    @property
    def delta(self) -> tuple[int, int]:
        return self._delta

    @property
    def reserved_col(self) -> Optional[int]:
        return self._reserved_col

    @property
    def line_cap_ratio(self) -> Optional[float]:
        return self._line_cap_ratio

    @property
    def neighborhood(self) -> Optional[int]:
        return self._neighborhood

    @property
    def max_neighborhood(self) -> Optional[int]:
        return self._max_neighborhood

    # Backward compatibility: allow attribute-style access
    def __getattr__(self, name: str) -> Any:
        # For backward compatibility with code using cfg.grid[0], cfg.delta[0], etc.
        if name == "grid":
            return self._grid
        if name == "delta":
            return self._delta
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
