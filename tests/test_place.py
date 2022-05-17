from nnsplace.netlist import create_drawf, read_json
from nnsplace.placement import NnsPlacer
from nnsplace.placement_cfg import NnsConfig

# from physdes.point import Point
# from physdes.recti import Rect
# from physdes.interval import Interval


def test_drawf():
    H = create_drawf()
    placer = NnsPlacer(H, NnsConfig(10, 10, 40, 40))
    place = [dict(), dict()]
    placer.init_placement(place)
    for v in H:
        col, row = place[0][v], place[1][v]
        print("<rect x=\"{}\" y=\"{}\" width=\"40\" height=\"35\" />"
              .format(col * 40, row * 40))
    assert place[0]["a1"] == 1
    assert place[1]["a1"] == 0


def test_placement():
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
    placer = NnsPlacer(H, NnsConfig(50, 50, 40, 40))
    place = [[], []]
    place[0] = [0 for _ in range(H.number_of_modules())]  # x-direction
    place[1] = [0 for _ in range(H.number_of_modules())]  # y-direction
    placer.init_placement(place)
    # assert place[0][1] == 1
    # assert place[1][1] == 0
    # assert placer.count[1][0] == 32
    # assert placer.count[1][26] == 1
    # assert placer.count[1][27] == 0
    # assert placer.count[0][0] == 27
    # assert placer.count[0][1] == 26
    hpwl_x, hpwl_y = placer.calc_total_hpwl(place)
    print("Total HPWL before = {} + {} = {}".format(
              hpwl_x, hpwl_y, hpwl_x + hpwl_y))
    print("Worst wirelenght before = {}".format(
              placer.calc_worst_wirelenght(place)))

    niter, worst = placer.run(place)
    # placer.apply_howard(place, 0)
    # placer.legalize(place, 1)
    # worst = placer.calc_worst_wirelenght(place)

    print("Number of iterations = {}".format(niter))
    hpwl_x, hpwl_y = placer.calc_total_hpwl(place)
    print("Total HPWL after = {} + {} = {}".format(
              hpwl_x, hpwl_y, hpwl_x + hpwl_y))
    print("Worst wirelenght after = {}".format(worst))

    for v in H:
        print("<use x=\"{}\" y=\"{}\" href=\"#r1\"/>"
              .format(place[0][v] * 40, place[1][v] * 40))
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

    assert(place[0][1] < 0)
