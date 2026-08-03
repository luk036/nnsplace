from typing import Any, Iterator

import networkx as nx
from mywheel.map_adapter import MapAdapter


# The DiGraphAdapter class is a subclass of nx.DiGraph that adds a method to return the adjacency list
# as a dictionary.
class DiGraphAdapter(nx.DiGraph):
    """
    A NetworkX DiGraph adapter that provides a dict-like items() interface.

    This class extends nx.DiGraph to provide an items() method that returns
    the adjacency list as an iterable of (node, neighbors) tuples.
    """

    def items(self) -> Iterator[tuple[Any, Any]]:


        return self.adjacency()


# The `TinyDiGraph` class is a subclass of `DiGraphAdapter` that represents a directed graph with a
# small number of nodes.
class TinyDiGraph(DiGraphAdapter):
    num_nodes = 0

    def cheat_node_dict(self) -> MapAdapter:

        return MapAdapter([dict() for _ in range(self.num_nodes)])

    def cheat_adjlist_outer_dict(self) -> MapAdapter:

        return MapAdapter([dict() for _ in range(self.num_nodes)])

    node_dict_factory = cheat_node_dict
    adjlist_outer_dict_factory = cheat_adjlist_outer_dict

    def init_nodes(self, n: int) -> None:

        self.num_nodes = n
        self._node = self.cheat_node_dict()
        self._adj = self.cheat_adjlist_outer_dict()
        self._pred = self.cheat_adjlist_outer_dict()


if __name__ == "__main__":
    ugraph = TinyDiGraph()
    ugraph.init_nodes(1000)
    ugraph.add_edge(2, 1)
    print(ugraph.number_of_nodes())
    print(ugraph.number_of_edges())

    for utx in ugraph:
        for vtx in ugraph.neighbors(utx):
            print(f"{utx}, {vtx}")

    a = MapAdapter([0] * 8)
    for i in a:
        a[i] = i * i
    for i, vtx in a.items():
        print(f"{i}: {vtx}")
    print(3 in a)
