# -*- coding: utf-8 -*-
"""
Negative cycle detection for weighed graphs.
1. Support Lazy evalution
"""
from typing import Dict
from .bpqueue import BPQueue
from .dllist import Dllink


class negCycleFinder:
    pred: Dict = {}
    succ: Dict = {}

    def __init__(self, G):
        """[summary]

        Arguments:
            G: Graph
        """
        self.G = G
        max_weight = 0
        for (u, v, weight) in G.edges.data('weight'):
            if max_weight < weight:
                max_weight = weight
        self.bpq = BPQueue(0, max_weight)
        for (u, v, weight) in G.edges.data('weight'):
            self.bpq.append(Dllink([0, (u, v)]), weight)

    def find_cycle(self, point_to):
        """Find a cycle on the policy graph

        Yields:
            node: a start node of the cycle
        """
        visited = {}
        for v in filter(lambda v: v not in visited, self.G):
            u = v
            while True:
                visited[u] = v
                if u not in point_to:
                    break
                u = point_to[u]
                if u in visited:
                    if visited[u] == v:
                        yield u
                    break

    def relax_pred(self, dist, get_weight, update_ok):
        """Perform a updating of dist and pred

        Arguments:
            dist (Union[List, Dict]): [description]
            get_weight (Callable): [description]

        Returns:
            [type]: [description]
        """
        changed = False
        # for e in self.G.edges():
        for vlink in self.bpq:
            e = vlink.data[1]
            wt = get_weight(e)
            u, v = e
            d = dist[u] + wt
            if dist[v] > d:
                if update_ok(dist[v], d):
                    dist[v] = d
                    self.pred[v] = u
                    changed = True
        return changed

    def relax_succ(self, dist, get_weight, update_ok):
        """Perform a updating of dist and pred

        Arguments:
            dist (Union[List, Dict]): [description]
            get_weight (Callable): [description]

        Returns:
            [type]: [description]
        """
        changed = False
        # for e in self.G.edges():
        for vlink in self.bpq:
            e = vlink.data[1]
            wt = get_weight(e)
            u, v = e
            d = dist[v] - wt
            if dist[u] < d:
                if update_ok(dist[u], d):
                    dist[u] = d
                    self.succ[u] = v
                    changed = True
        return changed

    def find_neg_cycle_pred(self, dist, get_weight, update_ok):
        """Perform a updating of dist and pred

        Arguments:
            dist (Union[List, Dict]): [description]
            get_weight (Callable): [description]

        Yields:
            list of edges: cycle list
        """
        # self.dist = list(0 for _ in self.G)
        self.pred = {}
        found = False
        while not found and self.relax_pred(dist, get_weight, update_ok):
            # v = self.find_cycle()
            for v in self.find_cycle(self.pred):
                # Will zero cycle be found???
                # assert self.is_negative(v, dist, get_weight)
                found = True
                yield self.cycle_list(v, self.pred)

    def find_neg_cycle_succ(self, dist, get_weight, update_ok):
        """Perform a updating of dist and succ

        Arguments:
            dist (Union[List, Dict]): [description]
            get_weight (Callable): [description]

        Yields:
            list of edges: cycle list
        """
        # self.dist = list(0 for _ in self.G)
        self.succ = {}
        found = False
        while not found and self.relax_succ(dist, get_weight, update_ok):
            # v = self.find_cycle()
            for v in self.find_cycle(self.succ):
                # Will zero cycle be found???
                # assert self.is_negative(v, dist, get_weight)
                found = True
                yield self.cycle_list(v, self.succ)

    def cycle_list(self, handle, point_to):
        """Cycle list started from handle

        Arguments:
            handle: graph node

        Returns:
            list of edges: cycle list
        """
        v = handle
        cycle = list()
        while True:
            u = point_to[v]
            cycle += [(u, v)]
            v = u
            if v == handle:
                break
        return cycle

    def is_negative(self, handle, dist, get_weight):
        """Check if the cycle list is negative

        Arguments:
            handle: graph node
            get_weight (Callable): [description]

        Returns:
            bool: [description]
        """
        v = handle
        # do while loop in C++
        while True:
            u = self.pred[v]
            wt = get_weight((u, v))
            if dist[v] > dist[u] + wt:
                return True
            v = u
            if v == handle:
                break
        return False
