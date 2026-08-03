"""
Netlist data structures and utilities for circuit netlist manipulation.

Provides classes and functions for representing and working with netlists
(module-net bipartite graphs), including factory functions for creating test
netlists, random hypergraphs, and JSON I/O utilities.
"""

import json
import random
from typing import Any, Dict, Iterator, List, Optional, Union

import networkx as nx
from mywheel.array_like import RepeatArray  # type: ignore
from mywheel.map_adapter import MapAdapter  # type: ignore
from networkx.algorithms import bipartite
from networkx.readwrite import json_graph


class SimpleGraph(nx.Graph):
    r"""
    The `SimpleGraph` class is a subclass of `nx.Graph` that defines default attributes for edges and
    nodes.

    .. svgbob::
       :align: center

          o-----o
         / \   /
        /   \ /
       o-----o

    """

    all_edge_dict = {"weight": 1}

    def single_edge_dict(self) -> Dict:
        return self.all_edge_dict

    edge_attr_dict_factory = single_edge_dict
    node_attr_dict_factory = single_edge_dict


# The TinyGraph class is a subclass of nx.Graph that initializes a graph with a specified number of
# nodes and provides methods for creating node dictionaries and adjacency list dictionaries.
class TinyGraph(nx.Graph):
    r"""
    The `TinyGraph` class is a subclass of `nx.Graph` that initializes a graph with a specified number
    of nodes and provides methods for creating node dictionaries and adjacency list dictionaries.

    .. svgbob::
       :align: center

          o-o
         / /
        o-o

    """

    num_nodes = 0

    def cheat_node_dict(self) -> "MapAdapter":
        return MapAdapter([dict() for _ in range(self.num_nodes)])

    def cheat_adjlist_outer_dict(self) -> "MapAdapter":
        return MapAdapter([dict() for _ in range(self.num_nodes)])

    node_dict_factory = cheat_node_dict
    adjlist_outer_dict_factory = cheat_adjlist_outer_dict

    def init_nodes(self, n: int) -> None:
        """
        Initialize the graph with ``n`` nodes.

        Creates empty node and adjacency dictionaries for all nodes.

        :param n: Number of nodes to initialize.
        :type n: int
        """
        self.num_nodes = n
        self._node = self.cheat_node_dict()
        self._adj = self.cheat_adjlist_outer_dict()


# The `Netlist` class represents a netlist, which is a collection of modules and nets in a graph
# structure, and provides various properties and methods for working with the netlist.
#
# .. svgbob::
#
#    +---+     +---+
#    | M1|-----| N1|
#    +---+     +---+
#      |         |
#      +---------+
#      |         |
#    +---+     +---+
#    | M2|-----| N2|
#    +---+     +---+
#
class Netlist:
    num_pads: int = 0
    cost_model: int = 0

    def __init__(
        self,
        ugraph: nx.Graph,
        modules: Union[range, List[Any]],
        nets: Union[range, List[Any]],
    ) -> None:
        r"""
        The function initializes an object with a graph, modules, and nets, and calculates some properties
        of the graph.

        :param ugraph: The parameter `ugraph` is a graph object of type `nx.Graph`. It represents the graph
            structure of the system
        :type ugraph: nx.Graph
        :param modules: The `modules` parameter is a list or range object that represents the modules in the
            graph. Each module is a node in the graph
        :type modules: Union[range, List[Any]]
        :param nets: The `nets` parameter is a list or range that represents the nets in the graph. A net is
            a connection between two or more modules
        :type nets: Union[range, List[Any]]

        .. svgbob::
           :align: center

              +---+
              | M |
              +---+
                |
              +---+
              | N |
              +---+

        """
        self.ugraph = ugraph
        self.modules = modules
        self.nets = nets

        self.num_modules = len(modules)
        self.num_nets = len(nets)
        self.module_weight: Union[RepeatArray, Dict, List[int]] = RepeatArray(
            1, self.num_modules
        )
        self.module_fixed: set = set()
        self.net_weight: Optional[Union[Dict, List[int]]] = None

        self.max_degree = max(self.ugraph.degree[cell] for cell in modules)

    def number_of_modules(self) -> int:
        return self.num_modules

    def number_of_nets(self) -> int:
        return self.num_nets

    def number_of_nodes(self) -> int:
        return self.ugraph.number_of_nodes()

    def number_of_pins(self) -> int:
        return self.ugraph.number_of_edges()

    def get_max_degree(self) -> int:
        return max(self.ugraph.degree[cell] for cell in self.modules)

    def get_module_weight(self, v: int) -> int:
        """
        The function `get_module_weight` returns the weight of a module given its index.

        :param v: The parameter `v` in the `get_module_weight` function is of type `size_t`. It represents
            the index or key of the module weight that you want to retrieve
        :return: the value of `self.module_weight[v]`.
        """
        if isinstance(self.module_weight, RepeatArray):
            return self.module_weight[v]
        elif isinstance(self.module_weight, dict):
            # If module_weight is a dictionary, we need to handle it differently
            # Convert the modules list to get the value by index
            if isinstance(self.modules, list):
                module_key = self.modules[v]
                return self.module_weight.get(
                    module_key, 1
                )  # default to 1 if not found
            else:
                # If modules is a range, assume direct indexing
                return self.module_weight.get(v, 1)
        elif isinstance(self.module_weight, list):
            return self.module_weight[v]
        else:
            return 1  # default value

    # def get_module_weight_by_id(self, v):
    #     """[summary]

    #     Arguments:
    #         v (size_t):  description

    #     Returns:
    #         [size_t]:  description
    #     """
    #     return 1 if self.module_weight is None \
    #         else self.module_weight[v]

    def get_net_weight(self, _: Any) -> int:

        return 1

    def __iter__(self) -> Iterator:
        return iter(self.modules)


def read_json(filename: str) -> Netlist:
    """
    The function `read_json` reads a JSON file, converts it into a graph, and creates a netlist object
    with module and net weights.

    :param filename: The filename parameter is the name of the JSON file that contains the data you want
        to read
    :return: an object of type `Netlist`.
    """
    with open(filename, "r") as fr:
        data = json.load(fr)

    ugraph = json_graph.node_link_graph(data, edges="edges")
    num_modules = ugraph.graph["num_modules"]
    num_nets = ugraph.graph["num_nets"]
    num_pads = ugraph.graph["num_pads"]
    hyprgraph = Netlist(
        ugraph, range(num_modules), range(num_modules, num_modules + num_nets)
    )
    hyprgraph.num_pads = num_pads
    return hyprgraph


def create_inverter() -> Netlist:
    """
    Create a simple inverter netlist.

    The inverter netlist consists of:
    - 3 modules: 'a0' (main inverter cell), 'p1' (input pad), 'p2' (output pad)
    - 2 nets: 'n0' (input net), 'n1' (output net)

    The connections are:
    - n0: p1 (input) -> a0 (inverter input)
    - n1: a0 (output) -> p2 (output)

    :return: A Netlist object representing the inverter circuit.
    """
    graph = SimpleGraph()
    graph.add_nodes_from(["a0", "p1", "p2", "n0", "n1"])
    nets = ["n0", "n1"]
    modules = ["a0", "p1", "p2"]
    module_weight = {"a0": 1, "p1": 0, "p2": 0}

    graph.add_edges_from(
        [
            ("n0", "p1", {"dir": "I"}),
            ("n0", "a0", {"dir": "O"}),
            ("n1", "a0", {"dir": "I"}),
            ("n1", "p2", {"dir": "O"}),
        ]
    )
    graph.graph["num_modules"] = 3
    graph.graph["num_nets"] = 2
    graph.graph["num_pads"] = 2
    hyprgraph = Netlist(graph, modules, nets)
    hyprgraph.module_weight = module_weight  # type: ignore[assignment]
    hyprgraph.net_weight = RepeatArray(1, len(nets))  # type: ignore[assignment]
    hyprgraph.num_pads = 2
    return hyprgraph


def create_inverter2() -> Netlist:
    """
    Create a simple inverter netlist using integer node IDs.

    This is an alternative version of create_inverter() that uses integer node IDs
    instead of string names. The netlist consists of:
    - 3 modules: 0, 1, 2 (where 1=p1 input pad, 2=p2 output pad, 0=inverter cell)
    - 2 nets: 3, 4 (where 3=input net, 4=output net)

    :return: A Netlist object representing the inverter circuit.
    """
    graph = SimpleGraph()
    graph.add_nodes_from([0, 1, 2, 3, 4])
    nets = range(3, 5)
    modules = range(3)
    module_weight = [1, 0, 0]

    graph.add_edges_from(
        [
            (3, 1, {"dir": "I"}),
            (3, 0, {"dir": "O"}),
            (4, 0, {"dir": "I"}),
            (4, 2, {"dir": "O"}),
        ]
    )
    graph.graph["num_modules"] = 3
    graph.graph["num_nets"] = 2
    graph.graph["num_pads"] = 2
    hyprgraph = Netlist(graph, modules, nets)
    hyprgraph.module_weight = module_weight  # type: ignore[assignment]
    hyprgraph.net_weight = RepeatArray(1, len(nets))  # type: ignore[assignment]
    hyprgraph.num_pads = 2
    return hyprgraph


def create_drawf() -> Netlist:
    """
    The function `create_drawf` creates a graph and netlist object with specified nodes, edges, and
    weights.

    :return: an instance of the Netlist class, which is created using the SimpleGraph class and some
        predefined modules and nets.
    """
    ugraph = SimpleGraph()
    ugraph.add_nodes_from(
        [
            "a0",
            "a1",
            "a2",
            "a3",
            "p1",
            "p2",
            "p3",
            "n0",
            "n1",
            "n2",
            "n3",
            "n4",
            "n5",
        ]
    )
    nets = [
        "n0",
        "n1",
        "n2",
        "n3",
        "n4",
        "n5",
    ]
    modules = ["a0", "a1", "a2", "a3", "p1", "p2", "p3"]
    module_weight = {"a0": 1, "a1": 3, "a2": 4, "a3": 2, "p1": 0, "p2": 0, "p3": 0}

    ugraph.add_edges_from(
        [
            ("n0", "p1", {"dir": "I"}),
            ("n0", "a0", {"dir": "I"}),
            ("n0", "a1", {"dir": "O"}),
            ("n1", "a0", {"dir": "I"}),
            ("n1", "a2", {"dir": "I"}),
            ("n1", "a3", {"dir": "O"}),
            ("n2", "a1", {"dir": "I"}),
            ("n2", "a2", {"dir": "I"}),
            ("n2", "a3", {"dir": "O"}),
            ("n3", "a2", {"dir": "I"}),
            ("n3", "p2", {"dir": "O"}),
            ("n4", "a3", {"dir": "I"}),
            ("n4", "p3", {"dir": "O"}),
            ("n5", "p2", {"dir": "B"}),
        ]
    )
    ugraph.graph["num_modules"] = 7
    ugraph.graph["num_nets"] = 6
    ugraph.graph["num_pads"] = 3
    hyprgraph = Netlist(ugraph, modules, nets)
    hyprgraph.module_weight = module_weight  # type: ignore[assignment]
    hyprgraph.net_weight = RepeatArray(1, len(nets))  # type: ignore[assignment]
    hyprgraph.num_pads = 3
    return hyprgraph


def create_test_netlist() -> Netlist:
    """
    The function `create_test_netlist` creates a test netlist with nodes, edges, module weights, and net
    weights.
    :return: an instance of the `Netlist` class, which represents a netlist with modules and nets.
    """
    ugraph = SimpleGraph()
    ugraph.add_nodes_from(["a0", "a1", "a2", "a3", "a4", "a5"])
    module_weight = {"a0": 533, "a1": 543, "a2": 532}
    ugraph.add_edges_from(
        [
            ("a3", "a0"),
            ("a3", "a1"),
            ("a4", "a0"),
            ("a4", "a1"),
            ("a4", "a2"),
            ("a5", "a0"),  # self-loop
        ]
    )

    ugraph.graph["num_modules"] = 3
    ugraph.graph["num_nets"] = 3
    modules = ["a0", "a1", "a2"]
    nets = ["a3", "a4", "a5"]
    net_weight = RepeatArray(1, len(nets))

    hyprgraph = Netlist(ugraph, modules, nets)
    hyprgraph.module_weight = module_weight  # type: ignore[assignment]
    hyprgraph.net_weight = net_weight  # type: ignore[assignment]
    return hyprgraph


def vdc(n: int, base: int = 2) -> float:
    """
    Compute the n-th value of the Van der Corput sequence in the given base.

    The Van der Corput sequence is a low-discrepancy sequence over the
    unit interval [0, 1), commonly used for quasi-Monte Carlo methods.

    :param n: Non-negative integer index into the sequence.
    :type n: int
    :param base: Base of the sequence (default: 2).
    :type base: int
    :return: The n-th Van der Corput value in [0, 1).
    :rtype: float

    Examples:
        >>> vdc(0)
        0.0
        >>> vdc(1)
        0.5
        >>> vdc(2)
        0.25
        >>> vdc(3)
        0.75
    """
    vdc, denom = 0.0, 1.0
    while n:
        denom *= base
        n, remainder = divmod(n, base)
        vdc += remainder / denom
    return vdc


def vdcorput(n: int, base: int = 2) -> List[float]:
    """
    Generate the first ``n`` values of the Van der Corput sequence.

    :param n: Number of sequence values to generate.
    :type n: int
    :param base: Base of the sequence (default: 2).
    :type base: int
    :return: A list of the first n Van der Corput values.
    :rtype: List[float]

    Examples:
        >>> vdcorput(4)
        [0.0, 0.5, 0.25, 0.75]
    """
    return [vdc(i, base) for i in range(n)]


def form_graph(
    N: int, M: int, _: Any, eta: float, seed: Optional[int] = None
) -> nx.Graph:
    """Form N by M bipartite random graph and connect nodes within eta.

    Arguments:
        N (int): Number of nodes in first bipartite set
        M (int): Number of nodes in second bipartite set
        _ (Any): Unused parameter
        eta (float): Probability of edge creation between nodes

    Keyword Arguments:
        seed (Optional[int]): Random seed for reproducibility (default: {None})

    Returns:
        nx.Graph: A bipartite random graph

    Examples:
        >>> graph = form_graph(10, 5, None, 0.1, seed=42)
    """
    if seed:
        random.seed(seed)

    # connect nodes with edges
    ugraph = bipartite.random_graph(N, M, eta)
    return ugraph


def create_random_hgraph(N: int = 30, M: int = 26, eta: float = 0.1) -> Netlist:
    """
    Create a random hypergraph netlist with N modules and M nets.

    Module and net positions are initialized using a Van der Corput sequence
    for reproducible pseudo-random placement.

    :param N: Number of modules (default: 30).
    :type N: int
    :param M: Number of nets (default: 26).
    :type M: int
    :param eta: Edge probability for the bipartite random graph (default: 0.1).
    :type eta: float
    :return: A Netlist object representing the random hypergraph.
    :rtype: Netlist
    """
    T = N + M
    xbase = 2
    ybase = 3
    x = [i for i in vdcorput(T, xbase)]
    y = [i for i in vdcorput(T, ybase)]
    pos = zip(x, y)
    ugraph = form_graph(N, M, pos, eta, seed=5)

    ugraph.graph["num_modules"] = N
    ugraph.graph["num_nets"] = M
    hyprgraph = Netlist(ugraph, range(N), range(N, N + M))
    hyprgraph.module_weight = RepeatArray(1, N)  # type: ignore[assignment]
    hyprgraph.net_weight = RepeatArray(1, M)  # type: ignore[assignment]
    return hyprgraph
