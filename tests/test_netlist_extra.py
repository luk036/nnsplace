"""Additional tests for nnsplace netlist module covering edge cases."""

from mywheel.array_like import RepeatArray
from netlistx.netlist import (
    Netlist,
    SimpleGraph,
    TinyGraph,
    create_inverter2,
    create_random_hgraph,
    form_graph,
    vdc,
    vdcorput,
)


def test_tiny_graph_init() -> None:
    g = TinyGraph()
    g.init_nodes(5)
    assert g.num_nodes == 5
    assert g.number_of_nodes() == 5


def test_tiny_graph_cheat_node_dict() -> None:
    g = TinyGraph()
    g.init_nodes(3)
    nd = g.cheat_node_dict()
    assert len(nd) == 3


def test_get_module_weight_repeat_array() -> None:
    graph = SimpleGraph()
    graph.add_nodes_from([0, 1, 2, 3])
    modules = [0, 1]
    nets = [2, 3]
    netlist = Netlist(graph, modules, nets)
    netlist.module_weight = RepeatArray(5, len(modules))
    assert netlist.get_module_weight(0) == 5


def test_get_module_weight_dict() -> None:
    graph = SimpleGraph()
    graph.add_nodes_from([0, 1, 2, 3])
    modules = [0, 1]
    nets = [2, 3]
    netlist = Netlist(graph, modules, nets)
    netlist.module_weight = {0: 10, 1: 20}
    assert netlist.get_module_weight(0) == 10
    assert netlist.get_module_weight(1) == 20


def test_get_module_weight_list() -> None:
    graph = SimpleGraph()
    graph.add_nodes_from([0, 1, 2, 3])
    modules = [0, 1]
    nets = [2, 3]
    netlist = Netlist(graph, modules, nets)
    netlist.module_weight = [100, 200]
    assert netlist.get_module_weight(0) == 100
    assert netlist.get_module_weight(1) == 200


def test_get_module_weight_unknown() -> None:
    graph = SimpleGraph()
    graph.add_nodes_from([0, 1, 2, 3])
    modules = [0, 1]
    nets = [2, 3]
    netlist = Netlist(graph, modules, nets)
    netlist.module_weight = "invalid"  # type: ignore[assignment]
    assert netlist.get_module_weight(0) == 1


def test_get_net_weight() -> None:
    graph = SimpleGraph()
    graph.add_nodes_from([0, 1])
    netlist = Netlist(graph, [0], [1])
    assert netlist.get_net_weight(None) == 1


def test_vdc_values() -> None:
    assert vdc(0) == 0.0
    assert vdc(1) == 0.5
    assert vdc(2) == 0.25
    assert vdc(3) == 0.75
    assert vdc(4) == 0.125


def test_vdc_base3() -> None:
    assert vdc(0, 3) == 0.0
    assert vdc(1, 3) == 1.0 / 3.0
    assert vdc(2, 3) == 2.0 / 3.0


def test_vdcorput_sequence() -> None:
    seq = vdcorput(4)
    assert seq == [0.0, 0.5, 0.25, 0.75]


def test_vdcorput_base3() -> None:
    seq = vdcorput(3, 3)
    assert seq == [0.0, 1.0 / 3.0, 2.0 / 3.0]


def test_form_graph_basic() -> None:
    graph = form_graph(5, 3, None, 0.5, seed=42)
    assert graph.number_of_nodes() == 8


def test_form_graph_no_seed() -> None:
    graph = form_graph(5, 3, None, 0.5)
    assert graph.number_of_nodes() == 8


def test_create_inverter2() -> None:
    netlist = create_inverter2()
    assert netlist.number_of_modules() == 3
    assert netlist.number_of_nets() == 2


def test_create_random_hgraph() -> None:
    netlist = create_random_hgraph(N=10, M=8, eta=0.2)
    assert netlist.number_of_modules() == 10
    assert netlist.number_of_nets() == 8


def test_create_random_hgraph_default() -> None:
    netlist = create_random_hgraph()
    assert netlist.number_of_modules() == 30
    assert netlist.number_of_nets() == 26


def test_get_module_weight_range_modules() -> None:
    """Test get_module_weight when modules is a range (line 222)."""
    graph = SimpleGraph()
    graph.add_nodes_from([0, 1, 2, 3])
    modules = range(2)
    nets = [2, 3]
    netlist = Netlist(graph, modules, nets)
    netlist.module_weight = {0: 10, 1: 20}
    assert netlist.get_module_weight(0) == 10
    assert netlist.get_module_weight(1) == 20
