"""Tests for the direction-aware create_flow_graph (driver -> sink arcs only)."""
from typing import Dict, List, Optional

from nnsplace.placement import create_flow_graph


class MockNetlist:
    """Minimal netlist with an optional per-net driver map."""

    def __init__(
        self,
        modules: List[int],
        ugraph: Dict[object, List[int]],
        module_weight: Dict[int, int],
        net_driver: Optional[Dict[object, int]] = None,
    ) -> None:
        self.modules = modules
        self.num_modules = len(modules)
        self.num_pads = 0
        self.nets = list(ugraph)
        self.ugraph = ugraph
        self.module_weight = module_weight
        if net_driver is not None:
            self.net_driver = net_driver

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.modules)


def test_directed_flow_graph_omits_sink_to_sink_arcs() -> None:
    """With a known driver only driver <-> sink arcs may exist."""
    netlist = MockNetlist(
        modules=[0, 1, 2, 3],
        ugraph={"n0": [0, 1, 2], "n1": [3, 0]},
        module_weight={0: 1, 1: 1, 2: 1, 3: 0},
        net_driver={"n0": 0, "n1": 3},
    )
    flow = create_flow_graph(netlist)
    assert flow.has_edge(0, 1) and flow.has_edge(1, 0)
    assert flow.has_edge(0, 2) and flow.has_edge(2, 0)
    assert not flow.has_edge(1, 2) and not flow.has_edge(2, 1)
    assert flow.has_edge(3, 0) and flow.has_edge(0, 3)


def test_undirected_flow_graph_stays_clique_without_net_driver() -> None:
    """Without net_driver the original all-pairs clique is preserved."""
    netlist = MockNetlist(
        modules=[0, 1, 2, 3],
        ugraph={"n0": [0, 1, 2]},
        module_weight={0: 1, 1: 1, 2: 1, 3: 0},
    )
    flow = create_flow_graph(netlist)
    assert flow.has_edge(1, 2) and flow.has_edge(2, 1)
    assert flow.has_edge(0, 1)
