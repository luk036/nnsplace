from physdes.point import Point

from nnsplace.netlist import read_json
from nnsplace.placement import NnsPlacer
from nnsplace.placement_cfg import NnsConfig

# from physdes.recti import Rect
# from physdes.interval import Interval


def test_placement():
    H = read_json("testcases/p1.json")
    placer = NnsPlacer(H, NnsConfig(32, 30, 40, 40))
    place = [[], []]
    place[0] = [0 for _ in range(H.number_of_modules())]  # x-direction
    place[1] = [0 for _ in range(H.number_of_modules())]  # y-direction
    placer.init_placement(place)
    assert place[0][1] == 1
    assert place[1][1] == 0
    assert placer.count[1][0] == 32
    assert placer.count[1][26] == 1
    assert placer.count[1][27] == 0
    assert placer.count[0][0] == 27
    assert placer.count[0][1] == 26
    print("Total HPWL before = {}".format(
              placer.calc_total_hpwl(place)))
    print("Worst wirelenght before = {}".format(
              placer.calc_worst_wirelenght(place)))
    # placer.run(place)

    # for v in H:
    #     print("  <use x=\"{}\" y=\"{}\" href=\"#r1\"/>"
    #           .format(place[0][v] * 40, place[1][v] * 40))

#     for net in H.nets:
#         adjs = iter(H.gr[net])
#         v = next(adjs)
#         p = Point(place[0][v], place[1][v])
#         bbox = Rect(Interval(p.x, p.x), Interval(p.y, p.y))
#         for v in adjs:
#             q = Point(place[0][v], place[1][v])
#             bbox = bbox.hull_with(q)
#         x = bbox.x.lb * 40 + 10
#         y = bbox.y.lb * 40 + 10
#         width = bbox.width() * 40
#         height = bbox.height() * 40
#         print("<rect class=\"net\" x=\"{}\" y=\"{}\" width=\"{}\" \
# height=\"{}\"/>".format(x, y, width, height))

    print("Total HPWL after = {}".format(
              placer.calc_total_hpwl(place)))
    print("Worst wirelenght after = {}".format(
              placer.calc_worst_wirelenght(place)))

    placer.apply_howard(place, 0)
    placer.legalize(place, 1)
    placer.apply_howard(place, 1)
    placer.legalize(place, 0)


if __name__ == "__main__":
    test_placement()
