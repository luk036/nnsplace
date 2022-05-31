from math import floor

import networkx as nx

from .min_parametric import min_parametric


def set_default(G: nx.DiGraph, weight, value):
    """[summary]

    Arguments:
        G (nx.DiGraph): directed graph
        weight ([type]): [description]
        value ([type]): [description]
    """
    for u, v in G.edges:
        if G[u][v].get(weight, None) is None:
            G[u][v][weight] = value


def max_mean_cycle(G: nx.DiGraph, dist, update_ok, r0, care_io=False):
    """[summary]

    Arguments:
        G ([type]): [description]

    Returns:
        [type]: [description]
    """
    # mu = 'cost'
    # sigma = 'time'
    # set_default(G, mu, 1)
    # set_default(G, sigma, 1)
    # T = type(dist[next(iter(G))])

    def calc_weight(r, e):
        """[summary]

        Arguments:
            r ([type]): [description]
            e ([type]): [description]

        Returns:
            [type]: [description]
        """
        u, v = e
        return floor(r - G[u][v]['cost'])

    def calc_ratio(C):
        """Calculate the ratio of the cycle

        Arguments:
            C {list}: cycle list

        Returns:
            cycle ratio
        """
        total_cost = sum(G[u][v]['cost'] for (u, v) in C)
        return floor(total_cost / len(C))

    # C0 = nx.find_cycle(G)
    # r0 = calc_ratio(C0)
    return min_parametric(G, r0, calc_weight, calc_ratio, dist, update_ok,
                          io=care_io)
