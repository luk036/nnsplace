"""Cap the per-line limit for small designs on large grids.

This exercises the *Future Directions* item of the fairness-placer talk:
instead of letting a small netlist crowd an entire grid line (``limit`` =
grid size), cap the core per-line limit to ``ceil(sqrt(num_cells) * 1.2)``
(opt-in via ``NnsConfig(line_cap_ratio=1.2)``).  The I/O ring keeps its own
pad-based capacity (``ceil(num_pads / 2)``) so pads are never starved.

Each grid runs the full placer twice (uncapped vs capped), so the suite is
slow on purpose and is marked ``slow``.
"""

import random
from typing import Any, Dict, List

import pytest
from netlistx.readwrite import read_json

from nnsplace.placement import NnsPlacer
from nnsplace.placement_cfg import NnsConfig

H = read_json("testcases/p1.json")
N = H.number_of_modules()
NUM_PADS = H.num_pads
NUM_CELLS = N - NUM_PADS

RATIO = 1.2


def _run(gx: int, gy: int, seed: int, ratio: float) -> tuple[list[int], int]:
    """Run the placer and return the placed coordinates + worst wire length."""
    kw = {} if ratio is None else dict(line_cap_ratio=ratio)
    random.seed(seed)
    placer = NnsPlacer(H, NnsConfig(gx, gy, 40, 40, **kw))
    place: List[Dict[Any, int]] = [{i: 0 for i in range(N)}, {i: 0 for i in range(N)}]
    placer.init_placement(place)
    placer.io_assign(place)
    niter, worst = placer.run(place, 2000)
    assert niter >= 0
    return place, worst


def _check_legal(place: List[Dict[Any, int]], gx: int, gy: int) -> None:
    """Verify no overlaps, cells off-grid or in the reserved column, pads on ring."""
    occupied: set = set()
    for v in range(N):
        x, y = place[0][v], place[1][v]
        assert (x, y) not in occupied, f"overlap at ({x}, {y})"
        occupied.add((x, y))
        if v < NUM_CELLS:
            assert 1 <= x <= gx and 1 <= y <= gy
            assert x != 27  # reserved DSP/SRAM column
        else:  # pad must sit on the I/O ring
            assert x in (0, gx + 1) or y in (0, gy + 1)


@pytest.mark.slow
@pytest.mark.parametrize(
    "gx,gy,seed",
    [(50, 50, 831), (100, 100, 831), (50, 50, 0), (100, 100, 3)],
)
def test_capped_stays_legal(gx: int, gy: int, seed: int) -> None:
    """Capped placement must stay legal on any seed (improvement is seed-dependent)."""
    place_cap, _ = _run(gx, gy, seed, RATIO)
    _check_legal(place_cap, gx, gy)


@pytest.mark.slow
@pytest.mark.parametrize("gx,gy", [(50, 50), (100, 100)])
def test_line_limit_small_grid(gx: int, gy: int) -> None:
    """Capped runs stay legal and beat the uncapped baseline (seed 831)."""
    place_base, worst_base = _run(gx, gy, 831, None)
    place_cap, worst_cap = _run(gx, gy, 831, RATIO)
    _check_legal(place_base, gx, gy)
    _check_legal(place_cap, gx, gy)
    assert worst_cap < worst_base, f"{gx}x{gy}: {worst_cap} >= {worst_base}"
    print(f"{gx}x{gy}: worst {worst_base} -> {worst_cap}")


def test_expected_capped_limit() -> None:
    """Cap must equal ceil(sqrt(num_cells) * ratio) bounded by the grid."""
    import math

    cap = math.ceil(math.sqrt(NUM_CELLS) * RATIO)
    placer = NnsPlacer(H, NnsConfig(100, 100, 40, 40, line_cap_ratio=RATIO))
    assert placer.limit == [min(100, cap), min(99, cap)]
    # I/O ring keeps pad-based capacity (two opposite edges always suffice)
    io_cap = math.ceil(NUM_PADS / 2)
    assert placer.io_limit == [min(100, io_cap), min(99, io_cap)]
