from .neg_cycle import NegCycleFinder


def min_parametric(gr, r, d, zero_cancel, dist,
                   update_ok, pick_one_only=False):
    """minimum parametric problem:

        min  r
        s.t. dist[v] - dist[v] <= d(u, v, r)
             for all (u, v) in G

    Arguments:
        G ([type]): directed graph
        r {float}: parameter to be minimized, initially a big number!!!
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

    S = NegCycleFinder(gr)
    r_max = r
    C = None
    # reverse = True

    while True:
        # if reverse:
        #     cycles = S.find_neg_cycle_succ(dist, get_weight, update_ok)
        # else:
        #     cycles = S.find_neg_cycle_pred(dist, get_weight, update_ok)
        cycles = S.find_neg_cycle_pred(dist, get_weight, update_ok)

        for Ci in cycles:
            ri = zero_cancel(Ci)
            if r_max < ri:
                r_max = ri
                C_max = Ci
                if pick_one_only:
                    break
        if r_max <= r:
            break

        C = C_max
        r = r_max
        # reverse = not reverse
    return r, C

# if __name__ == "__main__":
#     from __future__ import print_function
#     from pprint import pprint
#     import networkx as nx
#     from neg_cycle import *
#     from networkx.utils import generate_unique_node

#     G = create_test_case1()
#     G[1][2]['cost'] = 5
#     r, c, dist = max_cycle_ratio(G)
#     assert c != None
#     print(r)
#     print(c)
#     print(dist.items())

#     G = nx.cycle_graph(5, create_using=nx.DiGraph())
#     G[1][2]['cost'] = -6.
#     newnode = generate_unique_node()
#     G.add_edges_from([(newnode, n) for n in G])
#     r, c, dist = max_cycle_ratio(G)
#     assert c != None
#     print(r)
#     print(c)
#     print(dist.items())
