import pytest
from nnsplace.neg_cycle import NegCycleFinder

# Mock Graph class for testing
class MockGraph:
    def __init__(self, edges):
        self._edges = edges

    def edges(self):
        return self._edges

    def __iter__(self):
        nodes = set()
        for u, v in self._edges:
            nodes.add(u)
            nodes.add(v)
        return iter(sorted(list(nodes)))

def test_find_cycle_simple():
    edges = [('A', 'B'), ('B', 'C'), ('C', 'A')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)
    
    point_to = {'A': 'B', 'B': 'C', 'C': 'A'}
    cycles = list(finder.find_cycle(point_to))
    assert 'A' in cycles or 'B' in cycles or 'C' in cycles

def test_find_cycle_no_cycle():
    edges = [('A', 'B'), ('B', 'C')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)
    
    point_to = {'A': 'B', 'B': 'C'}
    cycles = list(finder.find_cycle(point_to))
    assert not cycles

def test_find_cycle_multiple_cycles():
    edges = [('A', 'B'), ('B', 'A'), ('C', 'D'), ('D', 'C')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)
    
    point_to = {'A': 'B', 'B': 'A', 'C': 'D', 'D': 'C'}
    cycles = list(finder.find_cycle(point_to))
    assert len(cycles) == 2
    assert ('A' in cycles and 'C' in cycles) or ('B' in cycles and 'D' in cycles)

def test_cycle_list():
    edges = [('A', 'B'), ('B', 'C'), ('C', 'A')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)
    
    point_to = {'A': 'B', 'B': 'C', 'C': 'A'}
    cycle = finder.cycle_list('A', point_to)
    assert set(cycle) == set([('B', 'A'), ('C', 'B'), ('A', 'C')])

def test_relax_pred():
    edges = [('A', 'B'), ('B', 'C'), ('C', 'A')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)

    dist = {'A': 0, 'B': float('inf'), 'C': float('inf')}
    
    def get_weight(edge):
        u, v = edge
        if u == 'A' and v == 'B': return 1
        if u == 'B' and v == 'C': return 1
        if u == 'C' and v == 'A': return 1
        return 0

    def update_ok(old_dist, new_dist):
        return True

    changed = finder.relax_pred(dist, get_weight, update_ok)
    assert changed == True
    assert dist == {'A': 0, 'B': 1, 'C': 2}
    assert finder.pred == {'B': 'A', 'C': 'B'}

def test_relax_succ():
    edges = [('A', 'B'), ('B', 'A')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)

    dist = {'A': 0, 'B': 0}
    
    def get_weight(edge):
        u, v = edge
        if u == 'A' and v == 'B': return -1
        if u == 'B' and v == 'A': return -1
        return 0

    def update_ok(old_dist, new_dist):
        return True

    changed = finder.relax_succ(dist, get_weight, update_ok)
    assert changed == True
    assert dist == {'A': 1, 'B': 2} or dist == {'A': 2, 'B': 1} # Depending on edge iteration order
def test_find_neg_cycle_pred_with_cycle():
    edges = [('A', 'B'), ('B', 'C'), ('C', 'A')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)

    dist = {'A': 0, 'B': 0, 'C': 0}
    
    def get_weight(edge):
        u, v = edge
        if u == 'A' and v == 'B': return -1
        if u == 'B' and v == 'C': return -1
        if u == 'C' and v == 'A': return -1
        return 0

    def update_ok(old_dist, new_dist):
        return True

    cycles = list(finder.find_neg_cycle_pred(dist, get_weight, update_ok))
    assert len(cycles) == 1
    assert set(cycles[0]) == set([('C', 'A'), ('B', 'C'), ('A', 'B')])

def test_find_neg_cycle_pred_no_cycle():
    edges = [('A', 'B'), ('B', 'C')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)

    dist = {'A': 0, 'B': 0, 'C': 0}
    
    def get_weight(edge):
        u, v = edge
        if u == 'A' and v == 'B': return -1
        if u == 'B' and v == 'C': return -1
        return 0

    def update_ok(old_dist, new_dist):
        return True

    cycles = list(finder.find_neg_cycle_pred(dist, get_weight, update_ok))
    assert not cycles

def test_find_neg_cycle_succ_with_cycle():
    edges = [('A', 'B'), ('B', 'C'), ('C', 'A')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)

    dist = {'A': 0, 'B': 0, 'C': 0}
    
    def get_weight(edge):
        u, v = edge
        if u == 'A' and v == 'B': return -1
        if u == 'B' and v == 'C': return -1
        if u == 'C' and v == 'A': return -1
        return 0

    def update_ok(old_dist, new_dist):
        return True

    cycles = list(finder.find_neg_cycle_succ(dist, get_weight, update_ok))
    assert len(cycles) == 1
    assert set(cycles[0]) == set([('B', 'A'), ('C', 'B'), ('A', 'C')])

def test_find_neg_cycle_succ_no_cycle():
    edges = [('A', 'B'), ('B', 'C')]
    graph = MockGraph(edges)
    finder = NegCycleFinder(graph)

    dist = {'A': 0, 'B': 0, 'C': 0}
    
    def get_weight(edge):
        u, v = edge
        if u == 'A' and v == 'B': return -1
        if u == 'B' and v == 'C': return -1
        return 0

    def update_ok(old_dist, new_dist):
        return True

    cycles = list(finder.find_neg_cycle_succ(dist, get_weight, update_ok))
    assert not cycles
