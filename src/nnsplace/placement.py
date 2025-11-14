"""Placement.py

This code implements a placement algorithm for electronic circuit design,
specifically for Field-Programmable Gate Arrays (FPGAs).
The purpose of the code
is to optimize the placement of circuit components (modules) on a grid-like
structure, minimizing the worst wire length between connected components.

The main input to this algorithm is a netlist,
which is a description of the
circuit components and their connections. It also takes configuration parameters
that define the grid size and other placement constraints. The output is an
optimized placement of the circuit components on the grid, represented as
coordinates for each module.

The code achieves its purpose through several key steps:

1. It starts by creating a flow graph from the input netlist,
   which represents the connections between modules.

2. An initial random placement of modules is generated on the grid.

3. The algorithm then iteratively improves this placement
   using a technique called the "fairness-centric" (NNS) placement method.
   This involves:
    - Applying Howard's algorithm to optimize module positions along each axis.
    - Legalizing the placement to ensure modules don't overlap
      and respect grid constraints.
    - Assigning I/O pads (input/output connections) to the edges of the grid.

4. The optimization process continues for a specified number of iterations or until no further improvement is possible.

The code uses several important data structures and algorithms:

- A graph representation of the circuit (using NetworkX library)
- Bipartite matching for legalization
- A parametric minimum cost flow algorithm (Howard's algorithm)

Throughout the process, the code calculates and tries to minimize the
"worst wirelength" - the longest connection between any two connected modules.
This serves as a metric for the quality of the placement.

The main logic flow involves repeatedly applying optimization steps along both the x and y axes, then legalizing the placement to ensure it respects the grid constraints. This process is repeated until a satisfactory placement is achieved or the maximum number of iterations is reached.

In simple terms, you can think of this algorithm as trying to arrange puzzle pieces (circuit modules) on a board (the grid) in a way that minimizes the total length of strings (wires) connecting related pieces, while making sure all pieces fit within the board's boundaries.

The following diagram illustrates the FPGA grid structure with I/O pads on the
periphery. (This diagram can be rendered with svgbob)

        .--------------------------------.
        | I/O Pads                       |
        | .--. .--. .--. .--. .--. .--. |
        | |P | |P | |P | |P | |P | |P | |
        | '--' '--' '--' '--' '--' '--' |
        | .--.--------------------.--. |
        | |P |  Core Grid         |P | |
        | '--'--------------------'--' |
        | .--.--------------------.--. |
        | |P |                    |P | |
        | '--'--------------------'--' |
        | .--.--------------------.--. |
        | |P |                    |P | |
        | '--'--------------------'--' |
        | .--. .--. .--. .--. .--. .--. |
        | |P | |P | |P | |P | |P | |P | |
        | '--' '--' '--' '--' '--' '--' |
        '--------------------------------'
"""

from fractions import Fraction
from random import shuffle
from typing import List, Tuple, Optional

import networkx as nx
from digraphx.tiny_digraph import TinyDiGraph
from netlistx.netlist import Netlist
from networkx.algorithms import bipartite
from physdes.interval import Interval

from .min_parametric import min_parametric
from .placement_cfg import NnsConfig


def create_flow_graph(hyprgraph: Netlist) -> TinyDiGraph:
    """
    The function `create_flow_graph` takes a netlist and creates a flow graph by adding edges between
    modules based on their connections in the netlist.

    TODO: Utilize pin directions of a net (in-to-out)

    :param hyprgraph: The `hyprgraph` parameter is of type `Netlist`. It represents a netlist, which is a
        description of the connections between different modules or cells in a circuit design. The `Netlist`
        class likely has attributes such as `modules`, `num_modules`, `num_pads`.
    :type hyprgraph: Netlist
    :return: a flow graph, which is represented as a TinyDiGraph object.

    """
    if isinstance(hyprgraph.modules, range):
        gr = TinyDiGraph(num_modules=hyprgraph.num_modules, num_pads=hyprgraph.num_pads)
        gr.init_nodes(hyprgraph.num_modules)
    else:
        gr = nx.DiGraph(num_modules=hyprgraph.num_modules, num_pads=hyprgraph.num_pads)
        gr.add_nodes_from(hyprgraph.modules)

    # Assume a list of modules = a list of cells appends with a list of pads
    # num_cells = hyprgraph.num_modules - hyprgraph.num_pads

    for net in hyprgraph.nets:
        for v1 in hyprgraph.gr[net]:
            # assume return an integer
            for v2 in hyprgraph.gr[net]:
                if hyprgraph.module_weight[v2] == 0:  # whatever check io pad
                    continue  # ignore pad to pad connections
                gr.add_edge(v1, v2)
                gr.add_edge(v2, v1)
    return gr


class NnsPlacer:
    """No non-sense placer (NNS Placer)

    This class implements the core placement algorithm for FPGA designs.
    It takes a netlist and configuration, then iteratively optimizes module
    placement on a grid to minimize wire length, handles legalization,
    and assigns I/O pads.
    """

    # TODO: handle optimization aware of I/O pad, DSP, SRAM
    # TODO: handle ASIC placement

    def __init__(self, hyprgraph: Netlist, cfg: NnsConfig) -> None:
        """
        The function initializes an object with a hypergraph, configuration, count, limit, and flow graph
        attributes.

        Notes:
            0 - x-axis
            1 - y-axis
            count[0] - how many cells on each row, including 2 I/O rows
            count[1] - how many cells on each column, including 2 I/O columns

        :param hyprgraph: The `hyprgraph` parameter is a Netlist object, which represents the
            hypergraph of the circuit design. It contains information about the modules and
            connections in the circuit.
        :type hyprgraph: Netlist
        :param cfg: The `cfg` parameter is an instance of the `NnsConfig` class. It contains
            configuration settings for the neural network system.
        :type cfg: NnsConfig
        """
        self.hyprgraph = hyprgraph
        self.cfg = cfg
        self.count = [
            [0 for _ in range(cfg.grid[0] + 2)],  # plus 2 I/O
            [0 for _ in range(cfg.grid[1] + 2)],
        ]  # two lists
        self.limit = [cfg.grid[1], cfg.grid[0] - 1]
        # assume col 27 is preserved for DSP or SRAM
        self.gr = create_flow_graph(hyprgraph)

    def init_placement(self, place: List[List[int]]) -> None:
        """
        The `init_placement` function initializes the placement of nodes in a hypergraph by assigning them
        to columns and rows in a grid.

        The modules are placed one by one, filling the grid row by row.
        (This diagram can be rendered with svgbob)

        .. svgbob::
            :align: center
            :font-family: Arial
            :font-size: 12

            Grid (e.g., 4x4)
            +---+---+---+---+
            | M | M | M | M |
            +---+---+---+---+
            | M | M | M | M |
            +---+---+---+---+
            | M | M |...|   |
            +---+---+---+---+
            |   |   |   |   |
            +---+---+---+---+

        :param place: The "place" parameter is a 2D list representing the placement solution. It has two
            rows and each column represents the placement of a vertex in the hypergraph. The first row
            represents the column index of the placement and the second row represents the row index of the
            placement
        :type place: List[List[int]]
        """
        col = 1
        row = 1
        lst = [v for v in self.hyprgraph]
        shuffle(lst)
        for v in lst:
            place[0][v] = col
            place[1][v] = row
            self.count[0][col] += 1
            self.count[1][row] += 1
            if col == self.cfg.grid[0]:
                # re-begin from the next row
                col = 1
                row += 1
            else:
                col += 1
            if col == 27:  # assume col 27 is preserved for DSP or SRAM
                col += 1
        assert self.count[0][27] == 0
        assert self.count[0][1] <= self.limit[0]  # e.g. 50
        assert self.count[1][1] <= self.limit[1]  # e.g. 49

    def cost(self, length: int, axis: int) -> int:
        """
        The `cost` function calculates the cost based on the length and axis provided.

        :param length: The `length` parameter represents the length of something, such as the length of a
            line or the number of elements in a list
        :type length: int
        :param axis: The `axis` parameter represents the axis along which the cost is calculated. It is an
            integer value that specifies the axis
        :type axis: int
        :return: an integer value.

        >>> from unittest.mock import Mock
        >>> cfg = Mock()
        >>> cfg.delta = [1, 2]
        >>> cfg.grid = [10, 10] # Add grid attribute to mock config
        >>> class MockNetlist:
        ...     def __init__(self):
        ...         self.modules = range(5)
        ...         self.num_modules = 5
        ...         self.num_pads = 1
        ...         self.gr = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
        ...         self.nets = ["net1", "net2"]
        ...         self.module_weight = {0: 1, 1: 1, 2: 1, 3: 1, 4: 0}
        ...     def __iter__(self):
        ...         return iter(self.modules)
        >>> netlist = MockNetlist()
        >>> placer = NnsPlacer(netlist, cfg)
        >>> placer.cost(5, 0)
        5
        >>> placer.cost(10, 1)
        20
        """
        return length * self.cfg.delta[axis]

    def cost_inv(self, cost: int, axis: int) -> Fraction:
        """
        The `cost_inv` function calculates the inverse of a cost value based on a given axis.

        :param cost: The `cost` parameter represents the cost value that you want to convert into a
            `Fraction` object
        :type cost: int
        :param axis: The `axis` parameter represents the axis along which the cost is being calculated. It
            is of type `int`
        :type axis: int
        :return: a `Fraction` object.

        >>> from unittest.mock import Mock
        >>> from fractions import Fraction
        >>> cfg = Mock()
        >>> cfg.delta = [1, 2]
        >>> cfg.grid = [10, 10] # Add grid attribute to mock config
        >>> class MockNetlist:
        ...     def __init__(self):
        ...         self.modules = range(5)
        ...         self.num_modules = 5
        ...         self.num_pads = 1
        ...         self.gr = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
        ...         self.nets = ["net1", "net2"]
        ...         self.module_weight = {0: 1, 1: 1, 2: 1, 3: 1, 4: 0}
        ...     def __iter__(self):
        ...         return iter(self.modules)
        >>> netlist = MockNetlist()
        >>> placer = NnsPlacer(netlist, cfg)
        >>> placer.cost_inv(5, 0)
        Fraction(5, 1)
        >>> placer.cost_inv(10, 1)
        Fraction(5, 1)
        """
        return Fraction(cost, self.cfg.delta[axis])

    def calc_worst_wirelength(self, place: List[List[int]]) -> int:
        """
        The `calc_worst_wirelength` function calculates the worst wirelength based on the given placement of
        nodes.

        :param place: The `place` parameter is a list of lists representing the coordinates of the nodes in
            a graph. Each inner list contains two integers representing the x and y coordinates of a node
        :type place: List[List[int]]
        :return: an integer, which represents the worst wirelength calculated.

        >>> from unittest.mock import Mock
        >>> cfg = Mock()
        >>> cfg.delta = [1, 2]
        >>> cfg.grid = [10, 10]
        >>> class MockNetlist:
        ...     def __init__(self):
        ...         self.modules = range(5)
        ...         self.num_modules = 5
        ...         self.num_pads = 1
        ...         self.gr = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
        ...         self.nets = ["net1", "net2"]
        ...         self.module_weight = {0: 1, 1: 1, 2: 1, 3: 1, 4: 0}
        ...     def __iter__(self):
        ...         return iter(self.modules)
        >>> netlist = MockNetlist()
        >>> placer = NnsPlacer(netlist, cfg)
        >>> place = [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4]]
        >>> placer.calc_worst_wirelength(place)
        6
        """
        worst_wire = 0
        for u in self.gr:
            for v in self.gr.neighbors(u):
                if u > v:  # only need to calculate one of the two edges
                    continue
                gruv = self.cost(abs(place[0][v] - place[0][u]), 0) + self.cost(
                    abs(place[1][v] - place[1][u]), 1
                )
                if worst_wire < gruv:
                    worst_wire = gruv
        return worst_wire

    def calc_worst_wirelength_v(self, v, place: List[List[int]]) -> int:
        """
        The function `calc_worst_wirelength_v` calculates the worst wirelength with respect to a given
        module `v` based on its placement coordinates.

        :param v: The parameter `v` represents a module in a circuit design
        :param place: The `place` parameter is a list of lists representing the placement of modules in a
            circuit. Each inner list contains the x and y coordinates of a module's position
        :type place: List[List[int]]
        :return: the worst wirelength with respect to Module v.

        >>> from unittest.mock import Mock
        >>> cfg = Mock()
        >>> cfg.delta = [1, 2]
        >>> cfg.grid = [10, 10]
        >>> class MockNetlist:
        ...     def __init__(self):
        ...         self.modules = range(5)
        ...         self.num_modules = 5
        ...         self.num_pads = 1
        ...         self.gr = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
        ...         self.nets = ["net1", "net2"]
        ...         self.module_weight = {0: 1, 1: 1, 2: 1, 3: 1, 4: 0}
        ...     def __iter__(self):
        ...         return iter(self.modules)
        >>> netlist = MockNetlist()
        >>> placer = NnsPlacer(netlist, cfg)
        >>> place = [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4]]
        >>> placer.calc_worst_wirelength_v(2, place)
        6
        """
        worst_wire = 0
        for w in self.gr.neighbors(v):
            gruv = self.cost(abs(place[0][v] - place[0][w]), 0) + self.cost(
                abs(place[1][v] - place[1][w]), 1
            )
            if worst_wire < gruv:
                worst_wire = gruv
        return worst_wire

    # def calc_worst_wirelength_axis(self, place: List[List[int]], axis):
    #     """Calculate the worst wirelength w.r.t one axis

    #     Args:
    #         place (List[List[int]]): _description_
    #         axis (_type_): _description_

    #     Returns:
    #         _type_: _description_
    #     """
    #     worst_wire = 0
    #     for u, v in self.gr.edges():
    #         if u > v:  # only need to calculate one of the two edges
    #             continue
    #         gruv = abs(place[axis][v] - place[axis][u])
    #         if worst_wire < gruv:
    #             worst_wire = gruv
    #     return worst_wire * self.cfg.delta[axis]

    # def calc_total_hpwl(self, place: List[List[int]]):
    #     """_summary_
    #
    #     Args:
    #         place (List[List[int]]): _description_
    #
    #     Returns:
    #         _type_: _description_
    #     """
    #     total_hpwl_x = 0
    #     total_hpwl_y = 0
    #     for net in self.hyprgraph.nets:
    #         adjs = iter(self.hyprgraph.gr[net])
    #         v = next(adjs)
    #         p = Point(place[0][v], place[1][v])
    #         bbox = Rect(Interval(p.x, p.x), Interval(p.y, p.y))
    #         for v in adjs:
    #             q = Point(place[0][v], place[1][v])
    #             bbox = bbox.hull_with(q)
    #         total_hpwl_x += bbox.width()
    #         total_hpwl_y += bbox.height()
    #     return total_hpwl_x * self.cfg.delta[0], \
    #         total_hpwl_y * self.cfg.delta[1]

    def calc_total_hull_length(self, dist: List[int], axis: int) -> int:
        """
        The function calculates the total length of the convex hull with respect to a given axis.

        :param dist: The `dist` parameter is a list of integers representing the distances between nodes in
            a hypergraph
        :type dist: List[int]
        :param axis: The `axis` parameter represents the axis along which the convex hull is calculated. It
            is an integer value that determines the axis of the coordinate system. The convex hull is calculated
            with respect to this axis
        :type axis: int
        :return: The function `calc_total_hull_length` returns an integer value, which represents the total
            hull length multiplied by `self.cfg.delta[axis]`.

        >>> from unittest.mock import Mock
        >>> cfg = Mock()
        >>> cfg.delta = [1, 2]
        >>> cfg.grid = [10, 10]
        >>> class MockNetlist:
        ...     def __init__(self):
        ...         self.modules = range(5)
        ...         self.num_modules = 5
        ...         self.num_pads = 1
        ...         self.gr = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
        ...         self.nets = ["net1", "net2"]
        ...         self.module_weight = {0: 1, 1: 1, 2: 1, 3: 1, 4: 0}
        ...     def __iter__(self):
        ...         return iter(self.modules)
        >>> netlist = MockNetlist()
        >>> placer = NnsPlacer(netlist, cfg)
        >>> dist = [0, 1, 2, 3, 4]
        >>> placer.calc_total_hull_length(dist, 0)
        4
        >>> placer.calc_total_hull_length(dist, 1)
        8
        """
        total_hull_length = 0
        for net in self.hyprgraph.nets:
            adjs = iter(self.hyprgraph.gr[net])
            # v = next(adjs)
            # p = dist[v]
            # hull = Interval(p, p)
            hull = Interval(1000000000000, -1000000000000)
            for v in adjs:
                hull = hull.hull_with(dist[v])
            total_hull_length += hull.measure()
        return total_hull_length * self.cfg.delta[axis]

    def calc_total_HPWL(self, place: List[List[int]]) -> int:
        """
        The `calc_total_HPWL` function calculates the total HPWL (Half Perimeter Wirelength) based on the
        given placement.

        :param place: The `place` parameter is a list of lists. Each inner list represents the coordinates
            of a point in a two-dimensional space. The first inner list represents the x-coordinates of the
            points, and the second inner list represents the y-coordinates of the points
        :type place: List[List[int]]
        :return: the sum of the total hull length for two different lists within the `place` list.

        >>> from unittest.mock import Mock
        >>> cfg = Mock()
        >>> cfg.delta = [1, 2]
        >>> cfg.grid = [10, 10]
        >>> class MockNetlist:
        ...     def __init__(self):
        ...         self.modules = range(5)
        ...         self.num_modules = 5
        ...         self.num_pads = 1
        ...         self.gr = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
        ...         self.nets = ["net1", "net2"]
        ...         self.module_weight = {0: 1, 1: 1, 2: 1, 3: 1, 4: 0}
        ...     def __iter__(self):
        ...         return iter(self.modules)
        >>> netlist = MockNetlist()
        >>> placer = NnsPlacer(netlist, cfg)
        >>> place = [[0, 1, 2, 3, 4], [0, 1, 2, 3, 4]]
        >>> placer.calc_total_HPWL(place)
        12
        """
        return self.calc_total_hull_length(place[0], 0) + self.calc_total_hull_length(
            place[1], 1
        )

    def apply_howard(self, place: List[List[int]], axis: int):
        """
        The `apply_howard` function applies Howard's algorithm to optimize the placement of elements in a
        grid along a specified axis.

        :param place: The `place` parameter is a 2D list representing the coordinates of points in a grid.
            Each inner list represents the coordinates of a point, where the first element is the x-coordinate
            and the second element is the y-coordinate
        :type place: List[List[int]]
        :param axis: The `axis` parameter in the `apply_howard` function represents the axis along which the
            algorithm will be applied. It is an integer value that determines whether the algorithm will be
            applied along the x-axis (0) or the y-axis (1)
        :type axis: int
        :return: A tuple containing two `Fraction` objects: the iteration count and the worst wirelength achieved.
        :rtype: Tuple[Fraction, Fraction]
        """
        oppo = axis ^ 1  # opposite axis

        def update_ok(from_where: int, to_where: int) -> bool:
            """
            The function `update_ok` checks additional constraints before updating the count of elements in a
            specific axis.

            :param from_where: The starting position from where the update is being made
            :type from_where: int
            :param to_where: The `to_where` parameter represents the position where an update is being made. It
                is an integer value indicating the new position
            :type to_where: int
            :return: The function `update_ok` returns a boolean value.
            """
            if to_where <= 0 or to_where > self.cfg.grid[axis]:
                # don't outside the place area
                return False
            if self.count[axis][to_where] >= self.limit[axis]:
                # don't over-crowd in one line
                return False
            # update the count
            self.count[axis][to_where] += 1
            self.count[axis][from_where] -= 1
            return True

        def calc_weight(beta: Fraction, edge: Tuple[int, int]) -> int:
            """
            The function `calc_weight` calculates the weight based on the given beta value and edge.

            :param beta: The beta parameter represents a fraction value. It is used in the calculation of the weight
            :type beta: Fraction
            :param edge: The `edge` parameter is a tuple of two integers representing the nodes in a graph. It
                represents an edge between the two nodes `u` and `v`
            :type edge: Tuple[int, int]
            :return: The function `calc_weight` returns an integer value.
            """
            u, v = edge
            temp = self.cost_inv(beta - self.gr[u][v]["cost"], axis)
            return temp.numerator // temp.denominator

        def zero_cancel(cycle: List[Tuple[int, int]]) -> Fraction:
            """
            The function calculates the zero cancellation of a cycle by summing the costs of the edges in the
            cycle and dividing by the number of edges.

            Note: Assume linear cost here

            :param cycle: The `cycle` parameter is a list of tuples representing a cycle. Each tuple contains
                two integers `u` and `v`, representing the nodes in the cycle
            :type cycle: List[Tuple[int, int]]
            :return: The function `zero_cancel` returns a `Fraction` object, which represents the ratio of the
                total cost of the cycle to the length of the cycle.
            """
            total_cost = sum(self.gr[u][v]["cost"] for (u, v) in cycle)
            return Fraction(total_cost, len(cycle))

        # TODO: should provide an API for calling the (monotone) wire-model
        # dt[0] * abs(p[0][i] - p[0][j]) + dt[1] * abs(p[1][i] - p[1][j]) < r
        worst = 0
        for u in self.gr:
            for v in self.gr.neighbors(u):
                gruv = abs(place[oppo][v] - place[oppo][u])
                self.gr[u][v]["cost"] = self.cost(gruv, oppo)
                if worst < gruv:
                    worst = gruv
        # initial worst/2 or 0 or others?
        return min_parametric(
            self.gr, Fraction(worst), calc_weight, zero_cancel, place[axis], update_ok
        )

    def add_bipartite_edge(
        self,
        lst: List[int],
        B: nx.Graph,
        place: List[List[int]],
        i: int,
        grid: int,
        axis: int,
    ):
        """
        The `add_bipartite_edge` function adds edges to a bipartite graph based on certain conditions and
        weights.

        :param lst: A list of integers representing the vertices in the bipartite graph
        :type lst: List[int]
        :param B: `B` is a graph object of type `nx.Graph`. It represents a bipartite graph
        :type B: nx.Graph
        :param place: The `place` parameter is a 2D list that represents the positions of the modules in a
            grid. Each element in the list represents a module, and its value is a list of two integers
            representing its position on the grid. The first integer represents the x-coordinate, and the second
            integer represents
        :type place: List[List[int]]
        :param i: The parameter `i` represents the distance by which the position of a vertex is shifted in
            the bipartite graph. It is used to create edges between the original vertex and its shifted
            positions in the bipartite graph
        :type i: int
        :param grid: The `grid` parameter represents the size of the grid. It is an integer value that
            determines the maximum position value for each axis in the grid
        :type grid: int
        :param axis: The `axis` parameter represents the axis along which the bipartite edges are being
            added. It is an integer value that indicates the axis direction
        :type axis: int
        """
        # increase the number of edges if no sol'n
        for v in lst:
            # construct bipartite graph
            p = place[axis][v]
            q = p + self.hyprgraph.number_of_modules()  # avoid same name
            weight0 = self.calc_worst_wirelength_v(v, place)
            if p - i > 0 and not (axis == 0 and p - i == 27):
                place[axis][v] -= i  # temporily set the position
                weight1 = self.calc_worst_wirelength_v(v, place)
                place[axis][v] += i  # reset the position
                B.add_node(q - i, bipartite=1)
                # B.add_edge(v, q - i, weight=i)
                B.add_edge(v, q - i, weight=weight1 - weight0)
            if p + i <= grid and not (axis == 0 and p + i == 27):
                place[axis][v] += i  # temporily set the position
                weight1 = self.calc_worst_wirelength_v(v, place)
                place[axis][v] -= i  # reset the position
                B.add_node(q + i, bipartite=1)
                # B.add_edge(v, q + i, weight=i)
                B.add_edge(v, q + i, weight=weight1 - weight0)

    def legalize(self, lst: List[int], place: List[List[int]], axis: int):
        """
        The `legalize` function solves the bipartite matching problem to reassign positions in a grid based
        on a given list and placement information. It moves modules to prevent overlaps.
        (This diagram can be rendered with svgbob)

        Before legalization (M1 and M2 overlap):

        .. svgbob::
            :align: center
            :font-family: Arial
            :font-size: 12

                .-------------.
                | .--.        |
                | |M1| .--.   |
                | '--' |M2|   |
                |   '--'      |
                | .--.        |
                | |M3|        |
                | '--'        |
                '-------------'

        After legalization:

        .. svgbob::
            :align: center
            :font-family: Arial
            :font-size: 12

                .-------------.
                | .--. .--.   |
                | |M1| |M2|   |
                | '--' '--'   |
                |             |
                | .--.        |
                | |M3|        |
                | '--'        |
                '-------------'

        :param lst: lst is a list of integers. It represents a set of elements that need to be matched with
            positions in the bipartite graph
        :type lst: List[int]
        :param place: The `place` parameter is a list of lists that represents the positions of the elements
            in a grid. Each inner list corresponds to a different axis (e.g., x-axis, y-axis), and contains the
            positions of the elements along that axis
        :type place: List[List[int]]
        :param axis: The "axis" parameter in the "legalize" function represents the axis along which the
            legalization is being performed. It is an integer value that determines whether the legalization is
            being done along the x-axis (axis=0) or the y-axis (axis=1)
        :type axis: int
        """
        dist = place[axis]
        grid = self.cfg.grid[axis]

        # construct bipartite graph
        B = nx.Graph()
        # Add nodes with the node attribute "bipartite"
        B.add_nodes_from(lst, bipartite=0)

        neighborhood = 11  # magic number for defining the neigborhood
        for v in lst:
            # construct bipartite graph
            q = dist[v] + self.hyprgraph.number_of_modules()  # avoid same name
            if axis == 0 and dist[v] == 27:
                continue
            B.add_node(q, bipartite=1)
            B.add_edge(v, q, weight=0)  # closest position
        for i in range(1, neighborhood):
            self.add_bipartite_edge(lst, B, place, i, grid, axis)

        # solve the matching problem
        i = neighborhood
        matched = False
        while not matched:
            try:
                matches = bipartite.minimum_weight_full_matching(B)
                for v in lst:
                    _ = matches[v]  # test if it is ok
                matched = True
            except ValueError:
                self.add_bipartite_edge(lst, B, place, i, grid, axis)
            except KeyError:
                self.add_bipartite_edge(lst, B, place, i, grid, axis)
            except nx.exception.AmbiguousSolution:
                self.add_bipartite_edge(lst, B, place, i, grid, axis)
            i += 1  # if no match, increase the neigborhood

        # reassign the results
        for v in lst:
            q = matches[v] - self.hyprgraph.number_of_modules()
            if dist[v] == q:
                continue
            # Update position and self.count
            self.count[axis][dist[v]] -= 1
            self.count[axis][q] += 1
            # Why not check limit?
            dist[v] = q

    def legalize_modules(self, place: List[List[int]], axis: int):
        """
        The `legalize_modules` function takes a `place` list and an `axis` integer as input, and it
        organizes the elements of `place` into buckets based on their distance from the `axis`. It then
        calls the `legalize` function on each non-empty bucket.

        :param place: The `place` parameter is a list of lists of integers. It represents the coordinates of
            a place in a grid. Each inner list represents the coordinates of a point in the grid. The outer list
            contains all the points in the grid
        :type place: List[List[int]]
        :param axis: The `axis` parameter is an integer that represents the axis along which the modules are
            being legalized. It is used to determine the distance of each module from a reference point on that
            axis
        :type axis: int
        """
        bucket: List[List[int]] = [list() for _ in range(self.cfg.grid[axis ^ 1] + 2)]
        dist = place[axis ^ 1]
        for v in self.gr:
            bucket[dist[v]].append(v)
        for lst in filter(lambda lst: lst, bucket):  # lst is not null or empty
            self.legalize(lst, place, axis)

    # def calc_average_position(self, vp: int, place: List[List[int]]):
    #     """_summary_
    #
    #     Args:
    #         vp (int): _description_
    #         place (List[List[int]]): _description_
    #
    #     Returns:
    #         _type_: _description_
    #     """
    #     posx = 0
    #     posy = 0
    #     count = 0
    #     for vi in self.gr[vp]:
    #         # if vi >= self.num_cells:  # only non-io modules
    #         #     continue
    #         posx += place[0][vi]
    #         posy += place[1][vi]
    #         count += 1
    #     posx //= count
    #     posy //= count
    #     return posx, posy

    # def choose_nearest_iopad2(self, place: List[List[int]]):
    #     """Choose the nearest iopad in phase 2
    #
    #        TODO: should apply Howard algorithm because one pad can
    #        connect to multiple modules and one modules can connect
    #        to multiple pad.
    #
    #     Args:
    #         place (List[List[int]]): _description_
    #     """
    #     # choose the nearest I/O
    #     grid_x = self.cfg.grid[0]
    #     half_x = grid_x // 2
    #     grid_y = self.cfg.grid[1]
    #     half_y = grid_y // 2
    #     n = self.hyprgraph.number_of_modules()
    #     for i in range(n - self.hyprgraph.num_pads, n):
    #         # loop through io pad
    #         vp = self.hyprgraph.modules[i]
    #         posx, posy = self.calc_average_position(vp, place)
    #         # nbrs = list(self.gr.neighbors(vp))
    #         # TODO: pad attached to more than one node
    #         # v = nbrs[0]  # workaround: take the first one only
    #
    #         if self.count[0][0] < grid_y:
    #             if self.count[0][grid_x + 1] < grid_y:
    #                 if posx <= half_x:
    #                     which_x = 0  # left
    #                     len_x = posx
    #                 else:
    #                     which_x = 1  # right
    #                     len_x = grid_x - posx
    #             else:
    #                 which_x = 0  # left
    #                 len_x = posx
    #         else:
    #             if self.count[0][grid_x + 1] < grid_y:
    #                 which_x = 1  # right
    #                 len_x = grid_x - posx
    #             else:
    #                 which_x = None  # no choice
    #
    #         if self.count[1][0] < grid_x:
    #             if self.count[1][grid_y + 1] < grid_x:
    #                 if posy <= half_y:
    #                     which_y = 0  # left
    #                     len_y = posy
    #                 else:
    #                     which_y = 1  # right
    #                     len_y = grid_y - posy
    #             else:
    #                 which_y = 0  # left
    #                 len_y = posy
    #         else:
    #             if self.count[1][grid_y + 1] < grid_x:
    #                 which_y = 1  # right
    #                 len_y = grid_y - posy
    #             else:
    #                 which_y = None  # no choice
    #
    #         self.count[0][place[0][vp]] -= 1  # ???
    #         self.count[1][place[1][vp]] -= 1  # ???
    #         if which_x is not None:
    #             if which_y is not None:
    #                 if len_x * self.cfg.delta[0] < len_y * self.cfg.delta[1]:
    #                     if which_x == 0:
    #                         place[0][vp] = 0
    #                     else:
    #                         place[0][vp] = grid_x + 1
    #                     place[1][vp] = posy
    #                 else:
    #                     if which_y == 0:
    #                         place[1][vp] = 0
    #                     else:
    #                         place[1][vp] = grid_y + 1
    #                     place[0][vp] = posx
    #             else:
    #                 if which_x == 0:
    #                     place[0][vp] = 0
    #                 else:
    #                     place[0][vp] = grid_x + 1
    #                 place[1][vp] = posy
    #         else:
    #             if which_y is not None:
    #                 if which_y == 0:
    #                     place[1][vp] = 0
    #                 else:
    #                     place[1][vp] = grid_y + 1
    #                 place[0][vp] = posx
    #             else:
    #                 # Not enough I/O area!!!
    #                 raise ValueError
    #         self.count[1][place[1][vp]] += 1
    #         self.count[0][place[0][vp]] += 1

    def choose_nearest_iopad_vp(
        self, place: List[List[int]], vp: int, axis: int
    ) -> Tuple[int, Optional[int], Optional[int]]:
        """
        The function `choose_nearest_iopad_vp` calculates the position and worst-case distance of the
        nearest I/O pad to a given point on a grid, based on certain conditions and calculations.

        :param place: The `place` parameter is a list of lists representing the coordinates of points in a
            grid. Each inner list contains two integers representing the x and y coordinates of a point
        :type place: List[List[int]]
        :param vp: The parameter `vp` represents the index of the current I/O pad that we are considering
        :type vp: int
        :param axis: The `axis` parameter represents the axis along which the calculations are being
            performed. It is an integer value that can be either 0 or 1
        :type axis: int
        :return: The function `choose_nearest_iopad_vp` returns a tuple containing three values: `choose`,
            `pos`, and `worst`.
        """
        # Assume working on 0 or grid[axis]
        # p[0][vp] = 0 or grid[0]
        # cx * |p[0][vp] - p[0][vi]| + cy * |p[1][vp] - p[1][vi]| <= t
        # cx * |p[1][vp] - p[1][vi]| <= t  - cy * |p[0][vp] - p[0][vi]| (li)
        # -t + li <= cx * (p[1][vp] - p[1][vi]) <= t - li
        # -(t - li) / cx <= p[1][vp] - p[1][vi] <= (t - li) / cx
        # -(t - li) / cx + p[1][vi] <= p[1][vp] <= (t - li) / cx + p[1][vi]
        # -t + max(cx*p[1][vi]+li) <= cx*p[1][vp] <= t + min(cx*p[1][vi]-li)
        # t >= (max(cx*p[1][vi] + li) - min(cx*p[1][vi] - li)) / 2
        # p[1][vp] = cx^-1 * (max(cx*p[1][vi]+li) + min(cx*p[1][vi]-li)) / 2

        oppo = axis ^ 1
        dx = self.cfg.delta[axis]
        dy = self.cfg.delta[oppo]
        grid = self.cfg.grid[axis]

        max0 = -1000000000000
        min0 = 1000000000000
        max1 = -1000000000000
        min1 = 1000000000000
        for vi in self.gr.neighbors(vp):
            li0 = dx * place[axis][vi]
            li1 = dx * (grid - place[axis][vi])
            ui = dy * place[oppo][vi]
            tem_max0 = ui + li0
            tem_min0 = ui - li0
            tem_max1 = ui + li1
            tem_min1 = ui - li1
            max0 = max(tem_max0, max0)
            min0 = min(tem_min0, min0)
            max1 = max(tem_max1, max1)
            min1 = min(tem_min1, min1)
        worst0 = (max0 - min0 + 1) // 2
        pos0 = (max0 + min0) // (2 * dx)
        worst1 = (max1 - min1 + 1) // 2
        pos1 = (max1 + min1) // (2 * dx)

        pos = None
        worst = None
        grid_x = self.cfg.grid[axis]
        full0 = self.count[axis][0] >= self.limit[axis]
        full1 = self.count[axis][grid_x + 1] >= self.limit[axis]
        if full0 and full1:
            choose = 2  # no choice
        else:
            if (full0, worst0) <= (full1, worst1):
                choose = 0  # left (or top)
                pos = pos0
                worst = worst0
            else:
                choose = 1  # right (or bottom)
                pos = pos1
                worst = worst1

        # if self.count[axis][0] < grid_y:
        #     if self.count[axis][grid_x + 1] < grid_y and worst0 > worst1:
        #         choose = 1  # right (or bottom)
        #         pos = pos1
        #         worst = worst1
        #     else:
        #         choose = 0  # left (or top)
        #         pos = pos0
        #         worst = worst0
        # else:
        #     if self.count[axis][grid_x + 1] < grid_y:
        #         choose = 1  # right (or bottom)
        #         pos = pos1
        #         worst = worst1
        #     else:
        #         choose = None  # no choice
        return choose, pos, worst # type: ignore

    def choose_nearest_iopad(self, place: List[List[int]]) -> None:
        """Choose the nearest iopad in phase 2

        TODO: should apply Howard algorithm because one pad can
        connect to multiple modules and one modules can connect
        to multiple pad.

        The `choose_nearest_iopad` function selects the nearest I/O pad for each module in a hypergraph
        based on their positions in a grid.

        :param place: The `place` parameter is a list of lists representing the placement of modules on a
            grid. Each inner list represents the x and y coordinates of a module. The `choose_nearest_iopad`
            function is used to choose the nearest I/O pad for each module in the placement
        :type place: List[List[int]]
        """
        # choose the nearest I/O
        n = self.hyprgraph.number_of_modules()
        grid_x = self.cfg.grid[0]
        grid_y = self.cfg.grid[1]
        for i in range(n - self.hyprgraph.num_pads, n):
            # loop through io pad
            vp = self.hyprgraph.modules[i]
            which_x, posy, worstx = self.choose_nearest_iopad_vp(place, vp, 0)
            which_y, posx, worsty = self.choose_nearest_iopad_vp(place, vp, 1)

            self.count[0][place[0][vp]] -= 1
            self.count[1][place[1][vp]] -= 1

            full_x = which_x == 2
            full_y = which_y == 2

            if full_x and full_y:
                # Not enough I/O area!!!
                raise ValueError
            else:
                if (full_x, worstx) <= (full_y, worsty):
                    if which_x == 0:
                        place[0][vp] = 0
                    else:
                        place[0][vp] = grid_x + 1
                    place[1][vp] = posy
                else:
                    if which_y == 0:
                        place[1][vp] = 0
                    else:
                        place[1][vp] = grid_y + 1
                    place[0][vp] = posx

            # if which_x is not None:
            #     if which_y is not None and worstx >= worsty:
            #         if which_y == 0:
            #             place[1][vp] = 0
            #         else:
            #             place[1][vp] = grid_y + 1
            #         place[0][vp] = posx
            #     else:
            #         if which_x == 0:
            #             place[0][vp] = 0
            #         else:
            #             place[0][vp] = grid_x + 1
            #         place[1][vp] = posy
            # else:
            #     if which_y is not None:
            #         if which_y == 0:
            #             place[1][vp] = 0
            #         else:
            #             place[1][vp] = grid_y + 1
            #         place[0][vp] = posx
            #     else:
            #         # Not enough I/O area!!!
            #         raise ValueError

            self.count[1][place[1][vp]] += 1
            self.count[0][place[0][vp]] += 1

    # def choose_nearest_iopad(self, place: List[List[int]]):
    #     """_summary_
    #
    #     Args:
    #         place (List[List[int]]): _description_
    #     """
    #     # choose the nearest I/O
    #     n = self.hyprgraph.number_of_modules()
    #     grid_x = self.cfg.grid[0]
    #     half_x = grid_x // 2
    #     grid_y = self.cfg.grid[1]
    #     half_y = grid_y // 2
    #     which_x = None
    #     which_y = None
    #     len_x = grid_x
    #     len_y = grid_y
    #     for i in range(n - self.hyprgraph.num_pads, n):
    #         v = self.hyprgraph.modules[i]
    #         if place[0][v] <= half_x and self.count[0][0] < grid_y:
    #             which_x = 0  # left
    #             len_x = place[0][v]
    #         elif self.count[0][grid_x + 1] < grid_y:
    #             which_x = 1  # right
    #             len_x = grid_x - place[0][v]
    #
    #         if place[1][v] <= half_y and self.count[1][0] < grid_x:
    #             which_y = 0  # top
    #             len_y = place[1][v]
    #         elif self.count[1][grid_y + 1] < grid_x:
    #             which_y = 1  # bottom
    #             len_y = grid_y - place[1][v]
    #
    #         self.count[0][place[0][v]] -= 1
    #         self.count[1][place[1][v]] -= 1
    #         if len_x * self.cfg.delta[0] < len_y * self.cfg.delta[1]:
    #             if which_x == 0:
    #                 place[0][v] = 0
    #             else:
    #                 place[0][v] = grid_x + 1
    #             self.count[0][place[0][v]] += 1
    #         else:
    #             if which_y == 0:
    #                 place[1][v] = 0
    #             else:
    #                 place[1][v] = grid_y + 1
    #             self.count[1][place[1][v]] += 1

    def legalize_iopad(self, place: List[List[int]], axis: int) -> None:
        """
        The `legalize_iopad` function takes a `place` parameter, which is a list of lists, and an `axis`
        parameter, which is an integer, and performs some operations on the `place` list based on the `axis`
        value.

        :param place: The `place` parameter is a 2D list of integers. It represents the placement of modules
            on a grid. Each element in the list represents the position of a module on a specific axis. The
            `axis` parameter is an integer that specifies the axis along which the legalization should be
            performed
        :type place: List[List[int]]
        :param axis: The `axis` parameter is an integer that represents the axis along which the I/O pads
            are being legalized. It is used to determine the placement of the I/O pads in the `place` list
        :type axis: int
        """
        bucket: List[List] = [list() for _ in range(2)]
        n = self.hyprgraph.number_of_modules()
        for i in range(n - self.hyprgraph.num_pads, n):
            v = self.hyprgraph.modules[i]
            if place[axis][v] == 0:
                bucket[0].append(v)
            elif place[axis][v] == self.cfg.grid[axis] + 1:
                bucket[1].append(v)
        if bucket[0]:
            self.legalize(bucket[0], place, axis ^ 1)
        if bucket[1]:
            self.legalize(bucket[1], place, axis ^ 1)

    def io_assign(self, place: List[List[int]]) -> None:
        """
        The `io_assign` function chooses the nearest iopad, and then legalizes it in the given place.

        :param place: The `place` parameter is a list of lists of integers. Each inner list represents the
            coordinates of an I/O pad. The first integer in each inner list represents the x-coordinate, and the
            second integer represents the y-coordinate
        :type place: List[List[int]]
        """
        self.choose_nearest_iopad(place)
        self.legalize_iopad(place, 0)
        self.legalize_iopad(place, 1)

    # def io_reassign(self, place: List[List[int]]):
    #     """_summary_
    #
    #     Args:
    #         place (List[List[int]]): _description_
    #     """
    #     self.choose_nearest_iopad(place)
    #     self.legalize_iopad(place)

    def optimize(self, place: List[List[int]], max_iters: int):
        """
        The `optimize` function is used to iteratively improve the placement of modules in a circuit layout
        by applying various optimization techniques.

        :param place: The `place` parameter is a list of lists representing the current placement of
            modules. Each inner list represents the coordinates of a module in the form `[x, y]`. The `place`
            parameter is used to store the current placement of modules during the optimization process
        :type place: List[List[int]]
        :param max_iters: The `max_iters` parameter is the maximum number of iterations that the
            optimization algorithm will run for. It determines how many times the algorithm will go through the
            optimization steps before stopping
        :type max_iters: int
        :return: the number of iterations performed and the worst wirelength achieved.
        """
        worst0 = self.calc_worst_wirelength(place)
        place0 = [place[0].copy(), place[1].copy()]
        count0 = [self.count[0].copy(), self.count[1].copy()]
        for niter in range(max_iters):
            _, _ = self.apply_howard(place, 0)
            self.legalize_modules(place, 1)
            self.choose_nearest_iopad(place)
            _, _ = self.apply_howard(place, 1)
            self.legalize_modules(place, 0)
            self.choose_nearest_iopad(place)

            # TODO: How to utilize r1, C1, r2, C2
            worst1 = self.calc_worst_wirelength(place)
            print(f"    x-y: {worst1}")
            # TODO: when to stop
            if worst1 >= worst0:
                place[0] = place0[0]
                place[1] = place0[1]
                self.count[0] = count0[0]
                self.count[1] = count0[1]
                # TODO: update self.count etc.
                return niter, worst0
            worst0 = worst1
            place0 = [place[0].copy(), place[1].copy()]
            count0 = [self.count[0].copy(), self.count[1].copy()]
        return max_iters, worst1

    def run(self, place: List[List[int]], max_iters=2000):
        """
        The `run` function performs an optimization algorithm on a given placement and returns the number of
        iterations and the worst wirelength achieved.

        :param place: The `place` parameter is a list of lists representing the current placement of
            components. Each inner list represents the coordinates of a component in the form [x, y]. The outer
            list contains two inner lists, one for the x-coordinates and one for the y-coordinates of the
            components
        :type place: List[List[int]]
        :param max_iters: The `max_iters` parameter is an optional integer that specifies the maximum number
            of iterations for the `run` method. It determines how many iterations the optimization algorithm
            will run before stopping. The default value is 2000, but you can change it to a different integer
            value if desired, defaults to 2000 (optional)
        :return: a tuple containing the number of iterations performed and the worst wirelength achieved
            during the optimization process.
        """
        # niter, worst = self.optimize(place, max_iters)
        # self.init_placement(place)
        # _, worst0 = self.optimize(place, max_iters)
        # self.io_assign(place)
        worst0 = self.calc_worst_wirelength(place)
        place0 = [place[0].copy(), place[1].copy()]
        count0 = [self.count[0].copy(), self.count[1].copy()]
        print(f"init: {worst0}")
        for niter in range(max_iters):
            _, _ = self.optimize(place, max_iters)
            self.io_assign(place)
            worst1 = self.calc_worst_wirelength(place)
            print(f"run {worst1}")
            if worst1 >= worst0:
                place[0] = place0[0]
                place[1] = place0[1]
                self.count[0] = count0[0]
                self.count[1] = count0[1]
                # TODO: update self.count etc.
                return niter, worst0
            worst0 = worst1
            place0 = [place[0].copy(), place[1].copy()]
            count0 = [self.count[0].copy(), self.count[1].copy()]
        return max_iters, worst0
