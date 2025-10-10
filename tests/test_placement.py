import pytest
from unittest.mock import Mock
from nnsplace.placement import create_flow_graph, NnsPlacer
from fractions import Fraction
from digraphx.tiny_digraph import TinyDiGraph
import networkx as nx


# Mock Netlist class for testing
class MockNetlist:
    def __init__(self, modules, num_modules, num_pads, gr, nets, module_weight):
        self.modules = modules
        self.num_modules = num_modules
        self.num_pads = num_pads
        self.gr = gr
        self.nets = nets
        self.module_weight = module_weight

    def __iter__(self):
        return iter(self.modules)


def test_create_flow_graph_tiny_digraph():
    # Test case where modules is a range, should return TinyDiGraph
    modules = range(5)
    num_modules = 5
    num_pads = 1
    gr_mock = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
    nets = ["net1", "net2"]
    module_weight = {0: 1, 1: 1, 2: 1, 3: 1, 4: 0}  # 4 is a pad

    netlist = MockNetlist(modules, num_modules, num_pads, gr_mock, nets, module_weight)
    flow_graph = create_flow_graph(netlist)

    assert isinstance(flow_graph, TinyDiGraph)
    assert flow_graph.graph["num_modules"] == num_modules
    assert flow_graph.graph["num_pads"] == num_pads
    assert (0, 1) in flow_graph.edges()
    assert (1, 0) in flow_graph.edges()
    assert (2, 3) in flow_graph.edges()
    assert (3, 2) in flow_graph.edges()
    assert (4, 3) in flow_graph.edges()


def test_create_flow_graph_networkx_digraph():
    # Test case where modules is a list, should return nx.DiGraph
    modules = ["m0", "m1", "m2", "m3", "p0"]
    num_modules = 5
    num_pads = 1
    gr_mock = {"net1": ["m0", "m1", "m2"], "net2": ["m2", "m3", "p0"]}
    nets = ["net1", "net2"]
    module_weight = {"m0": 1, "m1": 1, "m2": 1, "m3": 1, "p0": 0}  # p0 is a pad

    netlist = MockNetlist(modules, num_modules, num_pads, gr_mock, nets, module_weight)
    flow_graph = create_flow_graph(netlist)

    assert isinstance(flow_graph, nx.DiGraph)
    assert flow_graph.graph["num_modules"] == num_modules
    assert flow_graph.graph["num_pads"] == num_pads
    assert ("m0", "m1") in flow_graph.edges()
    assert ("m1", "m0") in flow_graph.edges()
    assert ("m2", "m3") in flow_graph.edges()
    assert ("m3", "m2") in flow_graph.edges()
    assert ("p0", "m3") in flow_graph.edges()
    assert ("m3", "p0") in flow_graph.edges()


class TestNnsPlacer:
    @pytest.fixture
    def mock_netlist(self):
        modules = range(5)
        num_modules = 5
        num_pads = 1
        gr_mock = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
        nets = ["net1", "net2"]
        module_weight = {0: 1, 1: 1, 2: 1, 3: 1, 4: 0}
        return MockNetlist(modules, num_modules, num_pads, gr_mock, nets, module_weight)

    @pytest.fixture
    def mock_nnsconfig(self):
        cfg = Mock()
        cfg.grid = [30, 10]  # x_grid, y_grid
        cfg.delta = [1, 2]  # x_cost_factor, y_cost_factor
        return cfg

    def test_nnsplacer_init(self, mock_netlist, mock_nnsconfig):
        placer = NnsPlacer(mock_netlist, mock_nnsconfig)
        assert placer.hyprgraph == mock_netlist
        assert placer.cfg == mock_nnsconfig
        assert placer.count == [
            [0 for _ in range(mock_nnsconfig.grid[0] + 2)],
            [0 for _ in range(mock_nnsconfig.grid[1] + 2)],
        ]
        assert placer.limit == [10, 29]
        assert isinstance(placer.gr, TinyDiGraph)

    def test_cost(self, mock_netlist, mock_nnsconfig):
        placer = NnsPlacer(mock_netlist, mock_nnsconfig)
        assert placer.cost(5, 0) == 5 * mock_nnsconfig.delta[0]
        assert placer.cost(10, 1) == 10 * mock_nnsconfig.delta[1]

    def test_cost_inv(self, mock_netlist, mock_nnsconfig):
        placer = NnsPlacer(mock_netlist, mock_nnsconfig)
        assert placer.cost_inv(5, 0) == Fraction(5, mock_nnsconfig.delta[0])
        assert placer.cost_inv(10, 1) == Fraction(10, mock_nnsconfig.delta[1])

    def test_calc_worst_wirelength(self, mock_netlist, mock_nnsconfig):
        placer = NnsPlacer(mock_netlist, mock_nnsconfig)
        place = [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4]]  # x_coords, y_coords
        # Edges in flow_graph: (0,1), (1,0), (0,2), (2,0), (1,2), (2,1), (2,3), (3,2), (2,4), (4,2), (3,4), (4,3)
        # Let's check (0,2): x_diff = 2, y_diff = 2. cost = 2*1 + 2*2 = 6
        # Let's check (2,3): x_diff = 1, y_diff = 1. cost = 1*1 + 1*2 = 3
        # Let's check (2,4): x_diff = 2, y_diff = 2. cost = 2*1 + 2*2 = 6
        # Let's check (3,4): x_diff = 1, y_diff = 1. cost = 1*1 + 1*2 = 3
        # Worst wirelength should be 6
        assert placer.calc_worst_wirelength(place) == 6

    def test_calc_worst_wirelength_v(self, mock_netlist, mock_nnsconfig):
        NnsPlacer(mock_netlist, mock_nnsconfig)
        # For v=0, neighbors are 1, 2
        # (0,1): x_diff = 1, y_diff = 1. cost = 1*1 + 1*2 = 3
        # (0,2): x_diff = 2, y_diff = 2. cost = 2*1 + 2*2 = 6
        # Worst for v=0 should be 6

    def test_init_placement(self, mock_netlist, mock_nnsconfig, mocker):
        placer = NnsPlacer(mock_netlist, mock_nnsconfig)
        place = [[0] * mock_netlist.num_modules, [0] * mock_netlist.num_modules]

        # Mock shuffle to make placement deterministic
        mocker.patch(
            "nnsplace.placement.shuffle", side_effect=lambda x: None
        )  # No actual shuffling

        placer.init_placement(place)

        # Assuming modules are 0, 1, 2, 3, 4 and grid is 10x10
        # The placement should be sequential if shuffle does nothing
        # col 27 is skipped
        expected_place_x = [1, 2, 3, 4, 5]
        expected_place_y = [1, 1, 1, 1, 1]

        assert place[0] == expected_place_x
        assert place[1] == expected_place_y
        assert placer.count[0][1] == 1  # module 0 at col 1
        assert placer.count[0][2] == 1  # module 1 at col 2
        assert placer.count[0][3] == 1  # module 2 at col 3
        assert placer.count[0][4] == 1  # module 3 at col 4
        assert placer.count[0][5] == 1  # module 4 at col 5
        assert placer.count[1][1] == 5  # all modules at row 1

    def test_calc_total_hull_length(self, mock_netlist, mock_nnsconfig):
        placer = NnsPlacer(mock_netlist, mock_nnsconfig)
        # dist represents coordinates along one axis
        dist = [0, 1, 2, 3, 4]  # module 0 to 4
        # net1: [0, 1, 2]. hull: [0, 2]. length = 2. cost = 2 * delta[0] = 2 * 1 = 2
        # net2: [2, 3, 4]. hull: [2, 4]. length = 2. cost = 2 * delta[0] = 2 * 1 = 2
        # Total = 2 + 2 = 4
        assert placer.calc_total_hull_length(dist, 0) == 4

    def test_calc_total_HPWL(self, mock_netlist, mock_nnsconfig):
        placer = NnsPlacer(mock_netlist, mock_nnsconfig)
        place = [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4]]  # x_coords, y_coords
        # x-axis: net1 hull length = 2, net2 hull length = 2. total_x = 2*1 + 2*1 = 4
        # y-axis: net1 hull length = 2, net2 hull length = 2. total_y = 2*2 + 2*2 = 8
        # Total HPWL = 4 + 8 = 12
        assert placer.calc_total_HPWL(place) == 12
