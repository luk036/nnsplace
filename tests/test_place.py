from nnsplace.netlist import read_json
from nnsplace.placement import NnsPlacer
from nnsplace.placement_cfg import NnsConfig
from random import seed

# def test_drawf():
#     H = create_drawf()
#     placer = NnsPlacer(H, NnsConfig(10, 10, 40, 40))
#     place = [dict(), dict()]
#     placer.init_placement(place)
#     for v in H:
#         col, row = place[0][v], place[1][v]
#         print("<rect x=\"{}\" y=\"{}\" width=\"40\" height=\"35\" />"
#               .format(col * 40, row * 40))
#     # assert place[0]["a1"] == 1
#     # assert place[1]["a1"] == 0


def test_placement():
    seed(831)
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
    n = H.number_of_modules()
    placer = NnsPlacer(H, NnsConfig(50, 50, 40, 40))
    place = [[], []]
    place[0] = [0 for _ in range(n)]  # x-direction
    place[1] = [0 for _ in range(n)]  # y-direction
    placer.init_placement(place)
    # assert place[0][1] == 1
    # assert place[1][1] == 0
    # assert placer.count[1][0] == 32
    # assert placer.count[1][26] == 1
    # assert placer.count[1][27] == 0
    # assert placer.count[0][0] == 27
    # assert placer.count[0][1] == 26
    hpwl_x = placer.calc_total_hull_length(place[0], 0)
    hpwl_y = placer.calc_total_hull_length(place[1], 1)
    print("Total HPWL before = {} + {} = {}".format(
        hpwl_x, hpwl_y, hpwl_x + hpwl_y))
    print("Worst wirelength before = {}".format(
        placer.calc_worst_wirelength(place)))

    # placer.io_assign(place)
    # placer.choose_nearest_iopad(place)

    niter, worst = placer.run(place, 1)
    print("Number of iterations = {}".format(niter))
    hpwl_x = placer.calc_total_hull_length(place[0], 0)
    hpwl_y = placer.calc_total_hull_length(place[1], 1)
    print("Total HPWL after = {} + {} = {}".format(
        hpwl_x, hpwl_y, hpwl_x + hpwl_y))
    print("Worst wirelength after = {}".format(worst))

    num_cells = n - H.num_pads
    for i in range(0, num_cells):
        v = H.modules[i]
        print("<use x=\"{}\" y=\"{}\" href=\"#r1\"/>"
              .format(place[0][v] * 40, place[1][v] * 40))
    for i in range(num_cells, n):
        vp = H.modules[i]
        print("<use x=\"{}\" y=\"{}\" href=\"#io\"/>"
              .format(place[0][vp] * 40, place[1][vp] * 40))
    for i in range(num_cells, n):
        vp = H.modules[i]
        # nbrs = list(placer.gr.neighbors(vp))
        # v = nbrs[0]
        for vi in placer.gr[vp]:
            # if vi >= num_cells:  # only non-io modules
            #     continue
            print("<line x1=\"{}\" y1=\"{}\" x2=\"{}\" y2=\"{}\"/>".format(
                  place[0][vp] * 40 + 20, place[1][vp] * 40 + 20,
                  place[0][vi] * 40 + 20, place[1][vi] * 40 + 20))

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
