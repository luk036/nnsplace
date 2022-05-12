# -*- coding: utf-8 -*-
from .neg_cycle import negCycleFinder


def max_parametric(G, r, C, d, zero_cancel, dist, pick_one_only=False):
    """maximum parametric problem:

        max  r
        s.t. dist[v] - dist[v] <= d(u, v, r)
             for all (u, v) in G

    Arguments:
        G ([type]): directed graph
        r {float}: parameter to be maximized, initially a big number!!!
        d ([type]): monotone decreasing function w.r.t. r
        zero_cancel ([type]): [description]
        pick_one_only {bool}: [description]

    Returns:
        r: optimal value
        C: Most critial cycle
        dist: optimal sol'n
    """
    def get_weight(e):
        return d(r, e)

    S = negCycleFinder(G)
    r_min = r

    while True:
        for Ci in S.find_neg_cycle(dist, get_weight):
            ri = zero_cancel(Ci)
            if r_min > ri:
                r_min = ri
                C_min = Ci
                if pick_one_only:
                    break
        if r_min >= r:
            break

        C = C_min
        r = r_min
    return r, C

# if __name__ == "__main__":
#     from __future__ import print_function
#     from pprint import pprint
#     import networkx as nx
#     from neg_cycle import *
#     from networkx.utils import generate_unique_node

#     G = create_test_case1()
#     G[1][2]['cost'] = 5
#     r, c, dist = min_cycle_ratio(G)
#     assert c != None
#     print(r)
#     print(c)
#     print(dist.items())

#     G = nx.cycle_graph(5, create_using=nx.DiGraph())
#     G[1][2]['cost'] = -6.
#     newnode = generate_unique_node()
#     G.add_edges_from([(newnode, n) for n in G])
#     r, c, dist = min_cycle_ratio(G)
#     assert c != None
#     print(r)
#     print(c)
#     print(dist.items())
