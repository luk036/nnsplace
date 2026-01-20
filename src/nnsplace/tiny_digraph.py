import networkx as nx
from mywheel.map_adapter import MapAdapter


# The DiGraphAdapter class is a subclass of nx.DiGraph that adds a method to return the adjacency list
# as a dictionary.
class DiGraphAdapter(nx.DiGraph):
    def items(self):
        return self.adjacency()


# The `TinyDiGraph` class is a subclass of `DiGraphAdapter` that represents a directed graph with a
# small number of nodes.
class TinyDiGraph(DiGraphAdapter):
    num_nodes = 0

    def cheat_node_dict(self):
        """
        The function `cheat_node_dict` returns a `MapAdapter` object that contains a list of dictionaries,
        where the number of dictionaries is equal to the number of nodes in the graph.

        Returns:
            A MapAdapter object.
        """
        return MapAdapter([dict() for _ in range(self.num_nodes)])

    def cheat_adjlist_outer_dict(self):
        """
        The function `cheat_adjlist_outer_dict` returns a `MapAdapter` object that contains a list of
        dictionaries, where the number of dictionaries is equal to the number of nodes in the graph.

        Returns:
            A MapAdapter object.
        """
        return MapAdapter([dict() for _ in range(self.num_nodes)])

    node_dict_factory = cheat_node_dict
    adjlist_outer_dict_factory = cheat_adjlist_outer_dict

    def init_nodes(self, n: int):
        """
        The function initializes the number of nodes, a dictionary for nodes, and dictionaries for
        adjacency and predecessor lists.

        :param n: The parameter `n` represents the number of nodes in the graph
        :type n: int
        """
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
