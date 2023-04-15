"""
Generalized Howard algorithm Solve minimum parametric network problems

"""

from .neg_cycle import NegCycleFinder


def min_parametric(gra, ratio, cost, zero_cancel, dist, update_ok, pick_one_only=False):
    """minimum parametric problem:

        min  r
        s.t. dist[v] - dist[v] ≤ cost(u, v, r)
             for all (u, v) in gra

    Arguments:
        gra ([type]): directed graph
        ratio {Any}: parameter to be minimized, initially a small number!!!
        cost ([type]): monotone increasing function w.r.t. r
        zero_cancel ([type]): [description]
        pick_one_only {bool}: [description]

    Returns:
        r: optimal value
        C: Most critial cycle
        dist: optimal sol'n
    """

    def get_weight(edge):
        return cost(ratio, edge)

    omega = NegCycleFinder(gra)
    r_max = ratio
    cycle = None
    reverse = True

    while True:
        if reverse:
            cycles = omega.find_neg_cycle_succ(dist, get_weight, update_ok)
        else:
            cycles = omega.find_neg_cycle_pred(dist, get_weight, update_ok)
        # cycles = S.find_neg_cycle_pred(dist, get_weight, update_ok)

        for c_i in cycles:
            r_i = zero_cancel(c_i)
            if r_max < r_i:
                r_max = r_i
                c_max = c_i
                if pick_one_only:
                    break
        if r_max <= ratio:
            break

        cycle = c_max
        ratio = r_max
        reverse = not reverse
    return ratio, cycle


# if __name__ == "__main__":
#     from __future__ import print_function
#     from pprint import pprint
#     import networkx as nx
#     from neg_cycle import *
#     from networkx.utils import generate_unique_node

#     gra = create_test_case1()
#     gra[1][2]['cost'] = 5
#     r, c, dist = max_cycle_ratio(gra)
#     assert c != None
#     print(r)
#     print(c)
#     print(dist.items())

#     gra = nx.cycle_graph(5, create_using=nx.DiGraph())
#     gra[1][2]['cost'] = -6.
#     newnode = generate_unique_node()
#     gra.add_edges_from([(newnode, n) for n in gra])
#     r, c, dist = max_cycle_ratio(gra)
#     assert c != None
#     print(r)
#     print(c)
#     print(dist.items())
