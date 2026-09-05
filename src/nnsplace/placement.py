"""Placement.py

This code implements a placement algorithm for electronic circuit design,
specifically for Field-Programmable Gate Arrays (FPGAs).
The purpose of the code
is to optimize the placement of circuit components (modules) on a grid-like
structure, minimizing the worst wire length between connected components.

.. svgbob::
   :align: center

      ┌────┬────┬────┬────┐
      │ M1 │    │ M2 │    │
      ├────┼────┼────┼────┤
      │    │ M3 │    │ M4 │
      ├────┼────┼────┼────┤
      │ M5 │    │ M6 │    │
      ├────┼────┼────┼────┤
      │    │ M7 │    │ M8 │
      └────┴────┴────┴────┘

The main input to this algorithm is a netlist,
which is a description of the
circuit components and their connections. It also takes configuration parameters
that define the grid size and other placement constraints. The output is an
optimized placement of the circuit components on the grid, represented as
coordinates for each module.

The code achieves its purpose through several key steps.
It starts by creating a flow graph from the input netlist,
which represents the connections between modules.
An initial random placement of modules is generated on the grid.
The algorithm then iteratively improves this placement
using a technique called the "fairness-centric" (NNS) placement method.
This involves applying Howard's algorithm to optimize module positions
along each axis, legalizing the placement to ensure modules don't overlap
and respect grid constraints, and assigning I/O pads
(input/output connections) to the edges of the grid.
The optimization process continues for a specified number of
iterations or until no further improvement is possible.

The code uses several important data structures and algorithms,
including a graph representation of the circuit (using NetworkX library),
bipartite matching for legalization, and a parametric minimum
cost flow algorithm (Howard's algorithm).



Throughout the process, the code calculates and tries to minimize the

"worst wirelength" - the longest connection between

any two connected modules.

This serves as a metric for the quality of the placement.

The main logic flow involves repeatedly applying optimization steps along both the x and y axes, then legalizing the placement to ensure it respects the grid constraints. This process is repeated until a satisfactory placement is achieved or the maximum number of iterations is reached.

In simple terms, you can think of this algorithm as trying to arrange puzzle pieces (circuit modules) on a board (the grid) in a way that minimizes the total length of strings (wires) connecting related pieces, while making sure all pieces fit within the board's boundaries.

The following diagram illustrates the FPGA grid structure with I/O pads on the
periphery.

.. svgbob::

.. svgbob::
   :align: center

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

import bisect
import logging
import math
from abc import ABC, abstractmethod
from fractions import Fraction
from random import shuffle
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
from digraphx.min_parametric_q import MinParametricAPI, MinParametricSolver
from digraphx.tiny_digraph import TinyDiGraph
from netlistx.netlist import Netlist
from networkx.algorithms import bipartite
from physdes.interval import Interval

from .placement_cfg import NnsConfig

logger = logging.getLogger(__name__)


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
        ugraph = TinyDiGraph(
            num_modules=hyprgraph.num_modules, num_pads=hyprgraph.num_pads
        )
        ugraph.init_nodes(hyprgraph.num_modules)
    else:
        ugraph = nx.DiGraph(
            num_modules=hyprgraph.num_modules, num_pads=hyprgraph.num_pads
        )
        ugraph.add_nodes_from(hyprgraph.modules)

    # Assume a list of modules = a list of cells appends with a list of pads

    for net in hyprgraph.nets:
        for v1 in hyprgraph.ugraph[net]:
            # assume return an integer
            for v2 in hyprgraph.ugraph[net]:
                if hyprgraph.module_weight[v2] == 0:  # whatever check io pad
                    continue  # ignore pad to pad connections
                ugraph.add_edge(v1, v2)
                ugraph.add_edge(v2, v1)
    return ugraph


class _HowardsCost(MinParametricAPI[Any, Any, Any]):
    """Cost model bridging NnsPlacer edge costs to MinParametricSolver.

    Each arc is a NetworkX edge attribute dict (e.g. ``{"cost": ...}``) from
    the flow graph, so the per-edge cost is read straight off the arc object.
    """

    def __init__(self, placer: "NnsPlacer", axis: int) -> None:
        self._placer = placer
        self._axis = axis
        self._delta = placer.cfg.delta[axis]

    def distance(self, ratio: Fraction, arc: Dict[Any, Any]) -> int:
        n, d = ratio.numerator, ratio.denominator
        c = arc["cost"] * d
        return (n - c) // (self._delta * d)

    def zero_cancel(self, cycle: List[Any]) -> Fraction:
        total_cost = sum(arc["cost"] for arc in cycle)
        return Fraction(total_cost, len(cycle))


class PlacerState:
    """Memento capturing a placement (coordinates + occupancy counts).

    ``optimize``/``run`` snapshot the working state before each iteration
    and restore it when the objective does not improve.
    """

    def __init__(self, place: List[Dict[Any, int]], count: List[List[int]]) -> None:
        self._place = [place[0].copy(), place[1].copy()]
        self._count = [count[0].copy(), count[1].copy()]

    def restore(self, place: List[Dict[Any, int]], count: List[List[int]]) -> None:
        """Roll ``place`` and ``count`` back to the captured state."""
        place[0] = self._place[0]
        place[1] = self._place[1]
        count[0] = self._count[0]
        count[1] = self._count[1]


class Legalizer(ABC):
    """Strategy proposing candidate slots to legalize a bucket of modules.

    A policy adds module -> slot edges to the shared bipartite graph ``B``
    and returns a full matching, or ``None`` when its search space cannot
    produce one.  The placer tries the local-window policy first and falls
    back to the global-slot policy on the very same graph, so results are
    deterministic and behaviour-preserving.
    """

    def __init__(self, placer: "NnsPlacer") -> None:
        self._placer = placer

    @abstractmethod
    def solve(
        self,
        lst: List[int],
        B: nx.Graph,
        place: List[Dict[Any, int]],
        axis: int,
    ) -> Optional[Dict[Any, int]]:
        """Add candidate edges to ``B`` and return a matching, else ``None``."""


class LocalWindowLegalizer(Legalizer):
    """Add slots reachable within a growing +/-radius window.

    Widens the window (up to ``MAX_NEIGHBORHOOD``) and retries the full
    matching until a legal assignment exists or the window is exhausted.
    This is the cheap, quality-preserving path.
    """

    neighborhood = 11  # magic number for defining the neigborhood
    MAX_NEIGHBORHOOD = 50  # Safety limit to prevent infinite loops

    def solve(
        self,
        lst: List[int],
        B: nx.Graph,
        place: List[Dict[Any, int]],
        axis: int,
    ) -> Optional[Dict[Any, int]]:
        placer = self._placer
        m = len(lst)
        data = {v: placer._module_slot_data(v, place, axis) for v in lst}

        placer._add_radius_edges(lst, B, data, axis, 1, self.neighborhood - 1)

        i = self.neighborhood
        while i < self.MAX_NEIGHBORHOOD:
            # minimum_weight_full_matching is guaranteed to raise on a
            # disconnected graph (bipartite.sets) or with fewer slots than
            # modules (unmatched modules); probe those cheaply and skip the
            # expensive scipy assignment, widening the window instead.
            if nx.is_connected(B) and B.number_of_nodes() - m >= m:
                try:
                    matches = bipartite.minimum_weight_full_matching(B)
                    for v in lst:
                        _ = matches[v]  # test if it is ok
                    return matches
                except (ValueError, KeyError, nx.exception.AmbiguousSolution):
                    pass  # connected but still infeasible; widen the window
            placer._add_radius_edges(lst, B, data, axis, i, i)
            i += 1  # if no match, increase the neighborhood
        return None


class GlobalSlotLegalizer(Legalizer):
    """Add every free slot along the axis.

    Guaranteed fallback: offers all slots so legalization succeeds whenever
    the grid has enough capacity.  Only fails if the grid genuinely lacks
    enough free slots for the bucket.
    """

    def solve(
        self,
        lst: List[int],
        B: nx.Graph,
        place: List[Dict[Any, int]],
        axis: int,
    ) -> Optional[Dict[Any, int]]:
        self._placer._add_all_slots(lst, B, place, axis)
        try:
            matches = bipartite.minimum_weight_full_matching(B)
            for v in lst:
                _ = matches[v]  # test if it is ok
            return matches
        except (ValueError, KeyError, nx.exception.AmbiguousSolution):
            return None


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
            count[0][col] - how many cells are at column col (x-coordinate)
            count[1][row] - how many cells are at row row (y-coordinate)
            grid_limit[axis] - physical per-line capacity of the core grid
            limit[axis] - per-line flow cap (capped by line_cap_ratio)
            io_limit[axis] - per-edge capacity of the I/O ring

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
        # physical per-line capacity of the core grid (col 27 is reserved)
        self.grid_limit = [cfg.grid[1], cfg.grid[0] - 1]
        ratio = getattr(cfg, "line_cap_ratio", None)
        if isinstance(ratio, (int, float)) and not isinstance(ratio, bool):
            num_cells = hyprgraph.number_of_modules() - hyprgraph.num_pads
            cap = math.ceil(math.sqrt(num_cells) * ratio)
            self.limit = [min(self.grid_limit[0], cap), min(self.grid_limit[1], cap)]
        else:
            self.limit = list(self.grid_limit)
        # I/O edge capacity: an edge needs at most half the pads (two opposite
        # edges then always suffice), bounded by the grid capacity
        num_pads = getattr(hyprgraph, "num_pads", 0)
        io_cap = math.ceil(num_pads / 2) if num_pads else max(self.grid_limit)
        self.io_limit = [
            min(self.grid_limit[0], io_cap),
            min(self.grid_limit[1], io_cap),
        ]
        self.reserved_col = cfg.reserved_col
        # assume col 27 is preserved for DSP or SRAM
        self.ugraph = create_flow_graph(hyprgraph)
        self._adj: Optional[Dict[Any, Any]] = None
        self._nbrs: Dict[Any, List[Any]] = {}
        self._local_legalizer = LocalWindowLegalizer(self)
        self._global_legalizer = GlobalSlotLegalizer(self)

    def _neighbors_of(self, v: Any) -> List[Any]:
        nbrs = self._nbrs.get(v)
        if nbrs is None:
            nbrs = list(self.ugraph.neighbors(v))
            self._nbrs[v] = nbrs
        return nbrs

    def init_placement(self, place: List[Dict[Any, int]]) -> None:
        """
        The `init_placement` function initializes the placement of nodes in a hypergraph by assigning them
        to columns and rows in a grid.

        .. svgbob::
           :align: center

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
        :type place: List[Dict[Any, int]]
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
            if col == self.reserved_col:  # assume col 27 is preserved for DSP or SRAM
                col += 1
        assert self.count[0][self.reserved_col] == 0
        assert self.count[0][1] <= self.grid_limit[0]  # e.g. 50
        assert self.count[1][1] <= self.grid_limit[1]  # e.g. 49

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
        ...         self.ugraph = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
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
        ...         self.ugraph = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
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

    def calc_worst_wirelength(self, place: List[Dict[Any, int]]) -> int:
        """
        The `calc_worst_wirelength` function calculates the worst wirelength based on the given placement of
        nodes.

        :param place: The `place` parameter is a list of dictionaries representing the coordinates of the nodes in
            a graph. Each dictionary maps module keys to their coordinates (x in place[0], y in place[1])
        :type place: List[Dict[Any, int]]
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
        ...         self.ugraph = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
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
        for u in self.ugraph:
            for v in self.ugraph.neighbors(u):
                if u > v:  # only need to calculate one of the two edges
                    continue
                gruv = self.cost(abs(place[0][v] - place[0][u]), 0) + self.cost(
                    abs(place[1][v] - place[1][u]), 1
                )
                if worst_wire < gruv:
                    worst_wire = gruv
        return worst_wire

    def calc_worst_wirelength_v(self, v: Any, place: List[Dict[Any, int]]) -> int:
        """
        The function `calc_worst_wirelength_v` calculates the worst wirelength with respect to a given
        module `v` based on its placement coordinates.

        :param v: The parameter `v` represents a module in a circuit design
        :param place: The `place` parameter is a list of dictionaries representing the placement of modules in a
            circuit. Each dictionary maps module keys to their coordinates (x in place[0], y in place[1])
        :type place: List[Dict[Any, int]]
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
        ...         self.ugraph = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
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
        for w in self.ugraph.neighbors(v):
            gruv = self.cost(abs(place[0][v] - place[0][w]), 0) + self.cost(
                abs(place[1][v] - place[1][w]), 1
            )
            if worst_wire < gruv:
                worst_wire = gruv
        return worst_wire

    def calc_total_hull_length(self, dist: Dict[Any, int], axis: int) -> int:
        """
        The function calculates the total length of the convex hull with respect to a given axis.

        :param dist: The `dist` parameter is a dictionary mapping module keys to their coordinates (distances) on the specified axis
        :type dist: Dict[Any, int]
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
        ...         self.ugraph = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
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
            adjs = iter(self.hyprgraph.ugraph[net])
            hull = Interval(1000000000000, -1000000000000)
            for v in adjs:
                hull = hull.hull_with(dist[v])
            total_hull_length += hull.measure()
        return total_hull_length * self.cfg.delta[axis]

    def calc_total_HPWL(self, place: List[Dict[Any, int]]) -> int:
        """
        The `calc_total_HPWL` function calculates the total HPWL (Half Perimeter Wirelength) based on the
        given placement.

        :param place: The `place` parameter is a list of dictionaries representing the coordinates of modules.
            place[0] maps module keys to x-coordinates, place[1] maps module keys to y-coordinates
        :type place: List[Dict[Any, int]]
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
        ...         self.ugraph = {"net1": [0, 1, 2], "net2": [2, 3, 4]}
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

    def apply_howard(self, place: List[Dict[Any, int]], axis: int) -> tuple[Any, Any]:
        """
        The `apply_howard` function applies Howard's algorithm to optimize the placement of elements in a
        grid along a specified axis.

        :param place: The `place` parameter is a list of dictionaries representing the coordinates of points in a grid.
            place[0] maps module keys to x-coordinates, place[1] maps module keys to y-coordinates
        :type place: List[Dict[Any, int]]
        :param axis: The `axis` parameter in the `apply_howard` function represents the axis along which the
            algorithm will be applied. It is an integer value that determines the axis of the coordinate system. The convex hull is calculated
            with respect to this axis
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

        # TODO: should provide an API for calling the (monotone) wire-model
        # dt[0] * abs(p[0][i] - p[0][j]) + dt[1] * abs(p[1][i] - p[1][j]) < r
        worst = 0
        for u in self.ugraph:
            for v in self.ugraph.neighbors(u):
                gruv = abs(place[oppo][v] - place[oppo][u])
                self.ugraph[u][v]["cost"] = self.cost(gruv, oppo)
                if worst < gruv:
                    worst = gruv
        # digraphx requires a dict adjacency whose arc objects are the edge
        # attr dicts; only the "cost" attrs mutate, so build it once.
        adj = self._adj
        if adj is None:
            adj = {u: dict(self.ugraph[u]) for u in self.ugraph}
            self._adj = adj
        solver = MinParametricSolver(adj, _HowardsCost(self, axis))
        return solver.run(place[axis], Fraction(worst), update_ok)

    def add_bipartite_edge(
        self,
        lst: List[int],
        B: nx.Graph,
        place: List[Dict[Any, int]],
        i: int,
        grid: int,
        axis: int,
    ) -> None:
        """Add module -> slot edges for window radius ``i`` (legacy API).

        Computes the module slot data from scratch on every call; prefer the
        hoisted ``_add_radius_edges`` when adding several radii.
        """
        data = {v: self._module_slot_data(v, place, axis) for v in lst}
        self._add_radius_edges(lst, B, data, axis, i, i)

    def _module_slot_data(
        self, v: Any, place: List[Dict[Any, int]], axis: int
    ) -> Tuple[int, List[int], List[int], List[int], int]:
        """Return ``(p0, as_, pref, suff, w0)`` so a lateral move of ``v``
        along ``axis`` can be scored in O(log deg) per candidate slot.

        ``p0`` is the current coordinate.  For each neighbor with moving-axis
        coordinate ``a`` and fixed-axis cost ``c``, the worst wire length of
        ``v`` at coordinate ``q`` is ``max(c + delta*|q - a|)``.  Sorting the
        neighbors by ``a`` and tabulating prefix/suffix maxima of the two
        linear forms makes each ``q`` an O(log deg) evaluation; ``w0`` is the
        value at ``p0``.
        """
        p0 = place[axis][v]
        nbrs = [w for w in self._neighbors_of(v) if w != v]
        if not nbrs:
            return p0, [], [], [], 0
        oppo = axis ^ 1
        pos_ax = place[axis]
        pos_op = place[oppo]
        o0 = pos_op[v]
        d_ax = self.cfg.delta[axis]
        d_op = self.cfg.delta[oppo]
        pairs = sorted((pos_ax[w], d_op * abs(o0 - pos_op[w])) for w in nbrs)
        m = len(pairs)
        as_ = [a for a, _ in pairs]
        pref = [0] * (m + 1)
        mx = pairs[0][1] - d_ax * pairs[0][0]
        pref[1] = mx
        for t in range(2, m + 1):
            c = pairs[t - 1][1] - d_ax * pairs[t - 1][0]
            if c > mx:
                mx = c
            pref[t] = mx
        suff = [0] * (m + 1)
        mx = pairs[m - 1][1] + d_ax * pairs[m - 1][0]
        suff[m - 1] = mx
        for t in range(m - 2, -1, -1):
            c = pairs[t][1] + d_ax * pairs[t][0]
            if c > mx:
                mx = c
            suff[t] = mx
        return p0, as_, pref, suff, self._worst_at(p0, as_, pref, suff, d_ax)

    @staticmethod
    def _worst_at(
        q: int,
        as_: List[int],
        pref: List[int],
        suff: List[int],
        d_ax: int,
    ) -> int:
        m = len(as_)
        t = bisect.bisect_right(as_, q)
        best = 0
        if t:
            best = d_ax * q + pref[t]
        if t < m:
            cand = suff[t] - d_ax * q
            if cand > best:
                best = cand
        return best

    def _add_radius_edges(
        self,
        lst: List[int],
        B: nx.Graph,
        data: Dict[Any, Tuple[int, List[int], List[int], List[int], int]],
        axis: int,
        r_start: int,
        r_stop: int,
    ) -> None:
        grid = self.cfg.grid[axis]
        nmod = self.hyprgraph.number_of_modules()
        d_ax = self.cfg.delta[axis]
        reserved = axis == 0
        worst_at = self._worst_at
        for i in range(r_start, r_stop + 1):
            for v in lst:
                p0, as_, pref, suff, w0 = data[v]
                q0 = p0 + nmod
                q = p0 - i
                if q > 0 and not (reserved and q == self.reserved_col):
                    w1 = 0 if not as_ else worst_at(q, as_, pref, suff, d_ax)
                    B.add_node(q0 - i, bipartite=1)
                    B.add_edge(v, q0 - i, weight=w1 - w0)
                q = p0 + i
                if q <= grid and not (reserved and q == self.reserved_col):
                    w1 = 0 if not as_ else worst_at(q, as_, pref, suff, d_ax)
                    B.add_node(q0 + i, bipartite=1)
                    B.add_edge(v, q0 + i, weight=w1 - w0)

    def _add_all_slots(
        self, lst: List[int], B: nx.Graph, place: List[Dict[Any, int]], axis: int
    ) -> None:
        """Connect every module to every free slot along `axis`.

        Fallback for when the local neighborhood search cannot spread `lst`
        (e.g. more than MAX_NEIGHBORHOOD modules crowded onto one line).
        As long as the grid offers at least as many slots along `axis` as
        there are modules, a full matching is then guaranteed to exist.
        """
        grid = self.cfg.grid[axis]
        nmod = self.hyprgraph.number_of_modules()
        for v in lst:
            p0 = place[axis][v]
            w0 = self.calc_worst_wirelength_v(v, place)
            for pos in range(1, grid + 1):
                if axis == 0 and pos == self.reserved_col:
                    continue
                place[axis][v] = pos
                w1 = self.calc_worst_wirelength_v(v, place)
                B.add_node(pos + nmod, bipartite=1)
                B.add_edge(v, pos + nmod, weight=w1 - w0)
            place[axis][v] = p0  # restore the original position

    def legalize(self, lst: List[int], place: List[Dict[Any, int]], axis: int) -> None:
        """
        The `legalize` function solves the bipartite matching problem to reassign positions in a grid based
        on a given list and placement information. It moves modules to prevent overlaps.

        .. svgbob::
           :align: center

           Before legalization (M1 and M2 overlap):
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
        :param place: The `place` parameter is a list of dictionaries that represents the positions of the elements
            in a grid. Each dictionary corresponds to a different axis (e.g., x-axis, y-axis), and contains the
            positions of the elements along that axis
        :type place: List[Dict[Any, int]]
        :param axis: The "axis" parameter in the "legalize" function represents the axis along which the
            legalization is being performed. It is an integer value that determines whether the legalization is
            being done along the x-axis (axis=0) or the y-axis (axis=1)
        :type axis: int
        """
        dist = place[axis]

        # base graph shared by both slot policies: modules + closest-position
        # nodes (weight-0 self edges), mirroring the original construction
        B = nx.Graph()
        B.add_nodes_from(lst, bipartite=0)
        for v in lst:
            q = dist[v] + self.hyprgraph.number_of_modules()  # avoid same name
            if axis == 0 and dist[v] == self.reserved_col:
                continue
            B.add_node(q, bipartite=1)
            B.add_edge(v, q, weight=0)  # closest position

        # primary strategy: local neighborhood window; fallback: all slots
        matches = self._local_legalizer.solve(lst, B, place, axis)
        if matches is None:
            matches = self._global_legalizer.solve(lst, B, place, axis)
        if matches is None:
            raise RuntimeError(
                f"Failed to legalize {len(lst)} modules on axis {axis} of "
                f"grid {self.cfg.grid}: not enough free slots for the "
                f"bucket (reserved_col={self.reserved_col})."
            )

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

    def legalize_modules(self, place: List[Dict[Any, int]], axis: int) -> None:
        """
        The `legalize_modules` function takes a `place` list and an `axis` integer as input, and it
        organizes the elements of `place` into buckets based on their distance from the `axis`. It then
        calls the `legalize` function on each non-empty bucket.

        :param place: The `place` parameter is a list of dictionaries of integers. It represents the coordinates of
            a place in a grid. Each dictionary represents the coordinates of a point in the grid. The outer list
            contains all the points in the grid
        :type place: List[Dict[Any, int]]
        :param axis: The `axis` parameter is an integer that represents the axis along which the modules are
            being legalized. It is used to determine the distance of each module from a reference point on that
            axis
        :type axis: int
        """
        bucket: List[List[int]] = [list() for _ in range(self.cfg.grid[axis ^ 1] + 2)]
        dist = place[axis ^ 1]
        for v in self.ugraph:
            bucket[dist[v]].append(v)
        for lst in filter(lambda lst: lst, bucket):  # lst is not null or empty
            self.legalize(lst, place, axis)

    def choose_nearest_iopad_vp(
        self, place: List[Dict[Any, int]], vp: int, axis: int
    ) -> Tuple[int, Optional[int], Optional[int]]:
        """
        The function `choose_nearest_iopad_vp` calculates the position and worst-case distance of the
        nearest I/O pad to a given point on a grid, based on certain conditions and calculations.

        :param place: The `place` parameter is a list of dictionaries representing the coordinates of points in a
            grid. place[0] maps module keys to x-coordinates, place[1] maps module keys to y-coordinates
        :type place: List[Dict[Any, int]]
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
        for vi in self.ugraph.neighbors(vp):
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
        full0 = self.count[axis][0] >= self.io_limit[axis]
        full1 = self.count[axis][grid_x + 1] >= self.io_limit[axis]
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

        return choose, pos, worst

    def choose_nearest_iopad(self, place: List[Dict[Any, int]]) -> None:
        """Choose the nearest iopad in phase 2

        TODO: should apply Howard algorithm because one pad can
        connect to multiple modules and one modules can connect
        to multiple pad.

        The `choose_nearest_iopad` function selects the nearest I/O pad for each module in a hypergraph
        based on their positions in a grid.

        :param place: The `place` parameter is a list of dictionaries representing the placement of modules on a
            grid. place[0] maps module keys to x-coordinates, place[1] maps module keys to y-coordinates
        :type place: List[Dict[Any, int]]
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

            if full_x:  # choose y
                if which_y == 0:
                    place[1][vp] = 0
                else:
                    place[1][vp] = grid_y + 1
                assert posx is not None
                place[0][vp] = posx
            elif full_y:  # choose x
                if which_x == 0:
                    place[0][vp] = 0
                else:
                    place[0][vp] = grid_x + 1
                assert posy is not None
                place[1][vp] = posy
            else:  # both are not full
                assert worstx is not None
                assert worsty is not None
                if worstx <= worsty:  # choose x
                    if which_x == 0:
                        place[0][vp] = 0
                    else:
                        place[0][vp] = grid_x + 1
                    assert posy is not None
                    place[1][vp] = posy
                else:  # choose y
                    if which_y == 0:
                        place[1][vp] = 0
                    else:
                        place[1][vp] = grid_y + 1
                    assert posx is not None
                    place[0][vp] = posx

            self.count[1][place[1][vp]] += 1
            self.count[0][place[0][vp]] += 1

    def legalize_iopad(self, place: List[Dict[Any, int]], axis: int) -> None:
        """
        The `legalize_iopad` function takes a `place` parameter, which is a list of dictionaries, and an `axis`
        parameter, which is an integer, and performs some operations on the `place` list based on the `axis`
        value.

        :param place: The `place` parameter is a 2D list of dictionaries representing the placement of modules
            on a grid. Each element in the list represents the position of a module on a specific axis. The
            `axis` parameter is an integer that specifies the axis along which the legalization should be
            performed
        :type place: List[Dict[Any, int]]
        :param axis: The `axis` parameter is an integer that represents the axis along which the I/O pads
            are being legalized. It is used to determine the placement of the I/O pads in the `place` list
        :type axis: int
        """
        bucket: List[List[Any]] = [list() for _ in range(2)]
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

    def io_assign(self, place: List[Dict[Any, int]]) -> None:
        """
        The `io_assign` function chooses the nearest iopad, and then legalizes it in the given place.

        :param place: The `place` parameter is a list of dictionaries of integers. Each dictionary represents the
            coordinates of an I/O pad (place[0] for x-coordinates, place[1] for y-coordinates)
        :type place: List[Dict[Any, int]]
        """
        self.choose_nearest_iopad(place)
        self.legalize_iopad(place, 0)
        self.legalize_iopad(place, 1)

    def optimize(self, place: List[Dict[Any, int]], max_iters: int) -> Tuple[int, int]:
        """
        The `optimize` function is used to iteratively improve the placement of modules in a circuit layout
        by applying various optimization techniques.

        :param place: The `place` parameter is a list of dictionaries representing the current placement of
            modules. place[0] maps module keys to x-coordinates, place[1] maps module keys to y-coordinates
        :type place: List[Dict[Any, int]]
        :param max_iters: The `max_iters` parameter is the maximum number of iterations that the
            optimization algorithm will run for. It determines how many times the algorithm will go through the
            optimization steps before stopping
        :type max_iters: int
        :return: the number of iterations performed and the worst wirelength achieved.
        """
        worst0 = self.calc_worst_wirelength(place)
        state = PlacerState(place, self.count)
        for niter in range(max_iters):
            _, _ = self.apply_howard(place, 0)
            self.legalize_modules(place, 1)
            self.choose_nearest_iopad(place)
            _, _ = self.apply_howard(place, 1)
            self.legalize_modules(place, 0)
            self.choose_nearest_iopad(place)

            # TODO: How to utilize r1, C1, r2, C2
            worst1 = self.calc_worst_wirelength(place)
            logger.debug("x-y: %d", worst1)
            # TODO: when to stop
            if worst1 >= worst0:
                state.restore(place, self.count)
                # TODO: update self.count etc.
                return niter, worst0
            worst0 = worst1
            state = PlacerState(place, self.count)
        return max_iters, worst1

    def run(
        self, place: List[Dict[Any, int]], max_iters: int = 2000
    ) -> Tuple[int, int]:
        """
        The `run` function performs an optimization algorithm on a given placement and returns the number of
        iterations and the worst wirelength achieved.

        :param place: The `place` parameter is a list of dictionaries representing the current placement of
            components. place[0] maps module keys to x-coordinates, place[1] maps module keys to y-coordinates
        :type place: List[Dict[Any, int]]
        :param max_iters: The `max_iters` parameter is an optional integer that specifies the maximum number
            of iterations for the `run` method. It determines how many iterations the optimization algorithm
            will run before stopping. The default value is 2000, but you can change it to a different integer
            value if desired, defaults to 2000 (optional)
        :return: a tuple containing the number of iterations performed and the worst wirelength achieved
            during the optimization process.
        """
        worst0 = self.calc_worst_wirelength(place)
        state = PlacerState(place, self.count)
        logger.info("init: %d", worst0)
        for niter in range(max_iters):
            _, _ = self.optimize(place, max_iters)
            self.io_assign(place)
            worst1 = self.calc_worst_wirelength(place)
            logger.info("run %d", worst1)
            if worst1 >= worst0:
                state.restore(place, self.count)
                # TODO: update self.count etc.
                return niter, worst0
            worst0 = worst1
            state = PlacerState(place, self.count)
        return max_iters, worst0
