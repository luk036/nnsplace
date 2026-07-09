from typing import Any

import networkx as nx

from nnsplace.min_parametric import min_parametric


def test_min_parametric_no_cycles() -> None:
    gra = nx.DiGraph()
    gra.add_edges_from([(0, 1), (1, 2)])

    def cost(ratio: Any, edge: Any) -> int:
        return 1

    def zero_cancel(cycle: Any) -> float:
        return 0.0

    def update_ok(old_dist: Any, new_dist: Any) -> bool:
        return True

    dist = [float("inf")] * 3
    dist[0] = 0

    ratio, cycle = min_parametric(
        gra, 0.0, cost, zero_cancel, dist, update_ok, pick_one_only=True
    )
    assert ratio == 0.0
    assert cycle is None


def test_min_parametric_with_cycle() -> None:
    gra = nx.DiGraph()
    gra.add_edges_from([(0, 1), (1, 2), (2, 0)])

    def cost(ratio: Any, edge: Any) -> float:
        return ratio - 1

    def zero_cancel(cycle: Any) -> float:
        return 2.0

    def update_ok(old_dist: Any, new_dist: Any) -> bool:
        return True

    dist = [0.0, 0.0, 0.0]

    ratio, cycle = min_parametric(gra, 1.0, cost, zero_cancel, dist, update_ok)
    assert ratio >= 1.0


def test_min_parametric_pick_one_only() -> None:
    gra = nx.DiGraph()
    gra.add_edges_from([(0, 1), (1, 2), (2, 0)])

    def cost(ratio: Any, edge: Any) -> float:
        return ratio - 2  # negative when ratio < 2, guarantees cycles

    def zero_cancel(cycle: Any) -> float:
        return 2.0

    def update_ok(old_dist: Any, new_dist: Any) -> bool:
        return True

    dist = [0.0, 0.0, 0.0]

    ratio, cycle = min_parametric(
        gra, 0.0, cost, zero_cancel, dist, update_ok, pick_one_only=True
    )
    assert ratio >= 0.0


def test_min_parametric_bidir() -> None:
    gra = nx.DiGraph()
    gra.add_edges_from([(0, 1), (1, 0)])

    def cost(ratio: Any, edge: Any) -> float:
        u, v = edge
        return 0.5 if u == 0 else 0

    def zero_cancel(cycle: Any) -> float:
        return 0.5

    def update_ok(old_dist: Any, new_dist: Any) -> bool:
        return True

    dist = [0.0, 0.0]

    ratio, cycle = min_parametric(gra, 0.2, cost, zero_cancel, dist, update_ok)
    assert ratio >= 0.2


if __name__ == "__main__":
    test_min_parametric_no_cycles()
    test_min_parametric_with_cycle()
    test_min_parametric_pick_one_only()
    test_min_parametric_bidir()
    print("All min_parametric tests passed!")
