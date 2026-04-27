"""
Unit tests for tiny_digraph module - provides DiGraphAdapter and TinyDiGraph classes.
"""

from nnsplace.tiny_digraph import DiGraphAdapter, TinyDiGraph
from mywheel.map_adapter import MapAdapter


def test_digraph_adapter_items():
    """Test DiGraphAdapter.items() returns adjacency as iterable."""
    gra = DiGraphAdapter()
    gra.add_nodes_from([0, 1, 2])
    gra.add_edge(0, 1)
    gra.add_edge(1, 2)
    gra.add_edge(2, 0)

    # items() should return adjacency iterable
    items = list(gra.items())
    assert len(items) == 3

    # Each item is (node, adjacency_dict)
    adj_dict = dict(gra.items())
    assert 0 in adj_dict
    assert 1 in adj_dict
    assert 2 in adj_dict


def test_digraph_adapter_add_edge():
    """Test DiGraphAdapter edge addition."""
    gra = DiGraphAdapter()
    assert gra.number_of_edges() == 0

    gra.add_edge(0, 1)
    assert gra.number_of_edges() == 1

    gra.add_edge(0, 1)  # no-op for MultiDiGraph
    assert gra.number_of_edges() == 1


def test_tiny_digraph_init_nodes():
    """Test TinyDiGraph.init_nodes() initializes graph with n nodes."""
    gra = TinyDiGraph()
    gra.init_nodes(5)
    assert gra.number_of_nodes() == 5


def test_tiny_digraph_node_dict_factory():
    """Test TinyDiGraph uses custom node_dict_factory."""
    gra = TinyDiGraph()
    gra.init_nodes(3)

    # node_dict_factory should return MapAdapter with dicts
    node_dict = gra._node
    assert isinstance(node_dict, MapAdapter)
    assert len(node_dict) == 3


def test_tiny_digraph_adjlist_outer_dict_factory():
    """Test TinyDiGraph uses custom adjlist_outer_dict_factory."""
    gra = TinyDiGraph()
    gra.init_nodes(3)

    adj = gra._adj
    assert isinstance(adj, MapAdapter)
    assert len(adj) == 3


def test_tiny_digraph_add_edge():
    """Test TinyDiGraph edge addition."""
    gra = TinyDiGraph()
    gra.init_nodes(3)
    gra.add_edge(0, 1)
    gra.add_edge(1, 2)

    assert gra.number_of_edges() == 2
    assert 1 in gra.neighbors(0)
    assert 2 in gra.neighbors(1)


def test_tiny_digraph_neighbors():
    """Test TinyDiGraph.neighbors() returns neighbor nodes."""
    gra = TinyDiGraph()
    gra.init_nodes(4)
    gra.add_edge(0, 1)
    gra.add_edge(0, 2)
    gra.add_edge(0, 3)

    neighbors = list(gra.neighbors(0))
    assert len(neighbors) == 3
    assert 1 in neighbors
    assert 2 in neighbors
    assert 3 in neighbors


def test_tiny_digraph_iteration():
    """Test iteration over TinyDiGraph nodes."""
    gra = TinyDiGraph()
    gra.init_nodes(3)
    gra.add_edge(0, 1)
    gra.add_edge(1, 2)

    nodes = list(gra)
    assert len(nodes) == 3


def test_tiny_digraph_number_of_nodes():
    """Test number_of_nodes() returns correct count."""
    gra = TinyDiGraph()
    gra.init_nodes(10)
    assert gra.number_of_nodes() == 10


def test_tiny_digraph_number_of_edges():
    """Test number_of_edges() returns correct count."""
    gra = TinyDiGraph()
    gra.init_nodes(3)
    gra.add_edge(0, 1)
    gra.add_edge(1, 2)
    gra.add_edge(2, 0)

    assert gra.number_of_edges() == 3


def test_tiny_digraph_in_degree():
    """Test in_degree() works correctly."""
    gra = TinyDiGraph()
    gra.init_nodes(3)
    gra.add_edge(0, 1)
    gra.add_edge(1, 1)

    assert gra.in_degree(1) == 2
    assert gra.in_degree(0) == 0


def test_tiny_digraph_out_degree():
    """Test out_degree() works correctly."""
    gra = TinyDiGraph()
    gra.init_nodes(3)
    gra.add_edge(0, 1)
    gra.add_edge(0, 2)

    assert gra.out_degree(0) == 2
    assert gra.out_degree(1) == 0


if __name__ == "__main__":
    test_digraph_adapter_items()
    test_digraph_adapter_add_edge()
    test_tiny_digraph_init_nodes()
    test_tiny_digraph_node_dict_factory()
    test_tiny_digraph_adjlist_outer_dict_factory()
    test_tiny_digraph_add_edge()
    test_tiny_digraph_neighbors()
    test_tiny_digraph_iteration()
    test_tiny_digraph_number_of_nodes()
    test_tiny_digraph_number_of_edges()
    test_tiny_digraph_in_degree()
    test_tiny_digraph_out_degree()
    print("All tiny_digraph tests passed!")
