import networkx as nx

from nnsplace.min_parametric import min_parametric


def test_min_parametric_no_cycles():
    gra = nx.DiGraph()
    gra.add_edges_from([(0, 1), (1, 2)])

    def cost(ratio, edge):
        return 1

    def zero_cancel(cycle):
        return 0.0

    def update_ok(old_dist, new_dist):
        return True

    dist = [float("inf")] * 3
    dist[0] = 0

    ratio, cycle = min_parametric(
        gra, 0.0, cost, zero_cancel, dist, update_ok, pick_one_only=True
    )
    assert ratio == 0.0
    assert cycle is None


def test_min_parametric_with_cycle():
    gra = nx.DiGraph()
    gra.add_edges_from([(0, 1), (1, 2), (2, 0)])

    def cost(ratio, edge):
        return ratio - 1

    def zero_cancel(cycle):
        return 2.0

    def update_ok(old_dist, new_dist):
        return True

    dist = [0.0, 0.0, 0.0]

    ratio, cycle = min_parametric(gra, 1.0, cost, zero_cancel, dist, update_ok)
    assert ratio >= 1.0


def test_min_parametric_pick_one_only():
    gra = nx.DiGraph()
    gra.add_edges_from([(0, 1), (1, 2), (2, 0)])

    def cost(ratio, edge):
        return ratio - 1

    def zero_cancel(cycle):
        return 2.0

    def update_ok(old_dist, new_dist):
        return True

    dist = [0.0, 0.0, 0.0]

    ratio, cycle = min_parametric(
        gra, 1.0, cost, zero_cancel, dist, update_ok, pick_one_only=True
    )
    assert ratio >= 1.0


def test_min_parametric_bidir():
    gra = nx.DiGraph()
    gra.add_edges_from([(0, 1), (1, 0)])

    def cost(ratio, edge):
        u, v = edge
        return 0.5 if u == 0 else 0

    def zero_cancel(cycle):
        return 0.5

    def update_ok(old_dist, new_dist):
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
