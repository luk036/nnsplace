# -*- coding: utf-8 -*-
"""
Negative cycle detection for weighed graphs.
1. Support Lazy evalution
"""
from typing import Dict, Generator

# from .bpqueue import BPQueue
# from .dllist import Dllink


class NegCycleFinder:
    pred: Dict = {}
    succ: Dict = {}

    def __init__(self, gra) -> None:
        """[summary]

        Arguments:
            gra: Graph
        """
        self.gra = gra
        # self.num_cells = gra.graph['num_modules'] - gra.graph['num_pads']
        # max_weight = 0
        # for (u, v, weight) in gra.edges.data('weight'):
        #     if max_weight < weight:
        #         max_weight = weight
        # self.bpq_pred = BPQueue(0, max_weight)
        # self.bpq_succ = BPQueue(0, max_weight)
        # if care_io:  # don't process I/O pad
        #     for (u, v, weight) in gra.edges.data('weight'):
        #         if v < gra.graph['num_modules'] - gra.graph['num_pads']:
        #             self.bpq_pred.append(Dllink([0, (u, v)]), weight)
        #         if u < gra.graph['num_modules'] - gra.graph['num_pads']:
        #             self.bpq_succ.append(Dllink([0, (u, v)]), weight)
        # else:
        #     for (u, v, weight) in gra.edges.data('weight'):
        #         self.bpq_pred.append(Dllink([0, (u, v)]), weight)
        #         # self.bpq_succ.append(Dllink([0, (u, v)]), weight)
        #     self.bpq_succ = self.bpq_pred

    def find_cycle(self, point_to):
        """Find a cycle on the policy graph

        Args:
            point_to (_type_): _description_

        Yields:
            _type_: _description_
        """
        visited = {}
        for vtx_v in filter(lambda vtx_v: vtx_v not in visited, self.gra):
            vtx_u = vtx_v
            while True:
                visited[vtx_u] = vtx_v
                if vtx_u not in point_to:
                    break
                vtx_u = point_to[vtx_u]
                if vtx_u in visited:
                    if visited[vtx_u] == vtx_v:
                        yield vtx_u
                    break

    def relax_pred(self, dist, get_weight, update_ok) -> bool:
        """Perform a updating of dist and pred

        Args:
            dist (_type_): _description_
            get_weight (_type_): _description_
            update_ok (_type_): _description_

        Returns:
            bool: _description_
        """
        changed = False
        # for vlink in self.bpq_pred:
        #     e = vlink.data[1]
        for e in self.gra.edges():
            vtx_u, vtx_v = e
            # if v >= self.num_cells:
            #     continue  # don't move IO pad
            weight = get_weight(e)
            d = dist[vtx_u] + weight
            if dist[vtx_v] > d and update_ok(dist[vtx_v], d):
                dist[vtx_v] = d
                self.pred[vtx_v] = vtx_u
                changed = True
        return changed

    def relax_succ(self, dist, get_weight, update_ok) -> bool:
        """Perform a updating of dist and succ

        Args:
            dist (_type_): _description_
            get_weight (_type_): _description_
            update_ok (_type_): _description_

        Returns:
            bool: _description_
        """
        changed = False
        # for vlink in self.bpq_succ:
        #     e = vlink.data[1]
        for e in self.gra.edges():
            vtx_u, vtx_v = e
            # if vtx_u >= self.num_cells:
            #     continue  # don't move IO pad
            weight = get_weight(e)
            d = dist[vtx_v] - weight
            if dist[vtx_u] < d and update_ok(dist[vtx_u], d):
                dist[vtx_u] = d
                self.succ[vtx_u] = vtx_v
                changed = True
        return changed

    def find_neg_cycle_pred(self, dist, get_weight, update_ok) -> Generator:
        """Perform a updating of dist and pred

        Arguments:
            dist (Union[List, Dict]): [description]
            get_weight (Callable): [description]

        Yields:
            list of edges: cycle list
        """
        self.pred = {}
        found = False
        while not found and self.relax_pred(dist, get_weight, update_ok):
            # vtx_v = self.find_cycle()
            for vtx_v in self.find_cycle(self.pred):
                # Will zero cycle be found???
                # assert self.is_negative(vtx_v, dist, get_weight)
                found = True
                yield self.cycle_list(vtx_v, self.pred)

    def find_neg_cycle_succ(self, dist, get_weight, update_ok) -> Generator:
        """Perform a updating of dist and succ

        Arguments:
            dist (Union[List, Dict]): [description]
            get_weight (Callable): [description]

        Yields:
            list of edges: cycle list
        """
        # self.dist = list(0 for _ in self.gra)
        self.succ = {}
        found = False
        while not found and self.relax_succ(dist, get_weight, update_ok):
            # vtx_v = self.find_cycle()
            for vtx_v in self.find_cycle(self.succ):
                # Will zero cycle be found???
                # assert self.is_negative(vtx_v, dist, get_weight)
                found = True
                yield self.cycle_list(vtx_v, self.succ)

    def cycle_list(self, handle, point_to) -> list:
        """Cycle list started from handle

        Arguments:
            handle: graph node

        Returns:
            list of edges: cycle list
        """
        vtx_v = handle
        cycle = list()
        while True:
            vtx_u = point_to[vtx_v]
            cycle += [(vtx_u, vtx_v)]
            vtx_v = vtx_u
            if vtx_v == handle:
                break
        return cycle

    def is_negative(self, handle, dist, get_weight) -> bool:
        """Check if the cycle list is negative

        Arguments:
            handle: graph node
            get_weight (Callable): [description]

        Returns:
            bool: [description]
        """
        vtx_v = handle
        # do while loop in C++
        while True:
            vtx_u = self.pred[vtx_v]
            wt = get_weight((vtx_u, vtx_v))
            if dist[vtx_v] > dist[vtx_u] + wt:
                return True
            vtx_v = vtx_u
            if vtx_v == handle:
                break
        return False
