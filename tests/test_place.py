from nnsplace.placement import NnsPlacer
from nnsplace.placement_cfg import NnsConfig
from physdes.point import Point
from physdes.recti import Rect
from physdes.interval import Interval

from nnsplace.netlist import create_drawf, read_json


def test_drawf():
    H = create_drawf()
    placer = NnsPlacer(H, NnsConfig(10, 10, 40, 40))
    place = dict()
    placer.init_placement(place)
    for v in H:
        col, row = place[v]
        print("<rect x=\"{}\" y=\"{}\" width=\"40\" height=\"35\" />"
              .format(col * 40, row * 40))
    assert place["a1"] == (1, 0)


def test_readjson():
    H = read_json("testcases/p1.json")
    # count_2 = 0
    # count_3 = 0
    # count_rest = 0
    # for net in H.nets:
    #     deg = H.G.degree(net)
    #     if deg == 2:
    #         count_2 += 1
    #     elif deg == 3:
    #         count_3 += 1
    #     else:
    #         count_rest += 1
    # print(count_2, count_3, count_rest)
    # assert count_2 == 494
    # 00321C
    # EC0000
    placer = NnsPlacer(H, NnsConfig(32, 32, 40, 40))
    place = [Point(0, 0)] * H.number_of_modules()
    placer.init_placement(place)
    # for v in H:
    #     p = place[v]
    #     print("<use x=\"{}\" y=\"{}\" href=\"#r1\"/>"
    #           .format(p.x, p.y))
    for net in H.nets:
        adjs = iter(H.gr[net])
        col, row = place[next(adjs)]
        p = Point(40 * col, 40 * row)
        bbox = Rect(Interval(p.x, p.x), Interval(p.y, p.y))
        for v in adjs:
            col, row = place[v]
            q = Point(40 * col, 40 * row)
            bbox = bbox.hull_with(q)
        print("<rect class=\"net\" x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\"/>"
              .format(bbox.x.lb+10, bbox.y.lb+10, bbox.width(), bbox.height()))
    assert place[1] == (1, 0)
