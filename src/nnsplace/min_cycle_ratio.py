# -*- coding: utf-8 -*-
from __future__ import print_function

import networkx as nx

from .parametric import max_parametric


def set_default(G: nx.Graph, weight, value):
    """[summary]

    Arguments:
        G (nx.Graph): directed graph
        weight ([type]): [description]
        value ([type]): [description]
    """
    for u, v in G.edges:
        if G[u][v].get(weight, None) is None:
            G[u][v][weight] = value


def min_cycle_ratio(G: nx.Graph, dist):
    """[summary] todo: parameterize cost and time

    Arguments:
        G ([type]): [description]

    Returns:
        [type]: [description]
    """
    mu = 'cost'
    sigma = 'time'
    set_default(G, mu, 1)
    set_default(G, sigma, 1)
    T = type(dist[next(iter(G))])

    def calc_weight(r, e):
        """[summary]

        Arguments:
            r ([type]): [description]
            e ([type]): [description]

        Returns:
            [type]: [description]
        """
        u, v = e
        return G[u][v]['cost'] - r * G[u][v]['time']

    def calc_ratio(C):
        """Calculate the ratio of the cycle

        Arguments:
            C {list}: cycle list

        Returns:
            cycle ratio
        """
        total_cost = sum(G[u][v]['cost'] for (u, v) in C)
        total_time = sum(G[u][v]['time'] for (u, v) in C)
        return T(total_cost) / total_time

    C0 = nx.find_cycle(G)
    r0 = calc_ratio(C0)
    return max_parametric(G, r0, C0, calc_weight, calc_ratio, dist)
