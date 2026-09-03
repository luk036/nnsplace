from random import seed
from typing import Any

from netlistx.netlist import create_inverter
from physdes.interval import Interval  # type: ignore[import-untyped]
from physdes.point import Point  # type: ignore[import-untyped]
from physdes.recti import Rectangle  # type: ignore[import-untyped]

from nnsplace.placement import NnsPlacer
from nnsplace.placement_cfg import NnsConfig

# def test_drawf() -> None:
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


def test_placement() -> None:
    seed(831)
    H = create_inverter()
    n = H.number_of_modules()
    placer = NnsPlacer(H, NnsConfig(32, 32, 40, 40))  # type: ignore[arg-type]
    place: list[dict[Any, int]] = [dict(), dict()]
    # place[0] = [0 for _ in range(n)]  # x-direction
    # place[1] = [0 for _ in range(n)]  # y-direction
    placer.init_placement(place)
    placer.io_assign(place)
    hpwl_x = placer.calc_total_hull_length(place[0], 0)
    hpwl_y = placer.calc_total_hull_length(place[1], 1)
    print("Total HPWL before = {} + {} = {}".format(hpwl_x, hpwl_y, hpwl_x + hpwl_y))
    print("Worst wirelength before = {}".format(placer.calc_worst_wirelength(place)))

    niter, worst = placer.run(place, 2000)
    print("Number of iterations = {}".format(niter))
    hpwl_x = placer.calc_total_hull_length(place[0], 0)
    hpwl_y = placer.calc_total_hull_length(place[1], 1)
    print("Total HPWL after = {} + {} = {}".format(hpwl_x, hpwl_y, hpwl_x + hpwl_y))
    print("Worst wirelength after = {}".format(worst))

    num_cells = n - H.num_pads
    for i in range(0, num_cells):
        v = H.modules[i]
        print(
            '<use x="{}" y="{}" href="#r1"/>'.format(place[0][v] * 40, place[1][v] * 40)
        )
    for i in range(num_cells, n):
        vp = H.modules[i]
        print(
            '<use x="{}" y="{}" href="#io"/>'.format(
                place[0][vp] * 40, place[1][vp] * 40
            )
        )
    # for i in range(num_cells, n):
    #     vp = H.modules[i]
    #     # nbrs = list(placer.ugraph.neighbors(vp))
    #     # v = nbrs[0]
    #     for vi in placer.ugraph[vp]:
    #         # if vi >= num_cells:  # only non-io modules
    #         #     continue
    #         print("<line x1=\"{}\" y1=\"{}\" x2=\"{}\" y2=\"{}\"/>".format(
    #               place[0][vp] * 40 + 20, place[1][vp] * 40 + 20,
    #               place[0][vi] * 40 + 20, place[1][vi] * 40 + 20))

    for net in H.nets:
        adjs = iter(H.ugraph[net])
        v = next(adjs)
        px = place[0][v]
        py = place[1][v]
        bbox = Rectangle(Interval(px, px), Interval(py, py))
        for v in adjs:
            q = Point(place[0][v], place[1][v])
            bbox = bbox.hull_with(q)  # type: ignore[assignment, arg-type]
        x = bbox.xcoord.lb * 40 + 10
        y = bbox.ycoord.lb * 40 + 10
        width = bbox.width() * 40
        height = bbox.height() * 40
        print(
            '<rect class="net" x="{}" y="{}" width="{}" \
height="{}"/>'.format(
                x, y, width, height
            )
        )

    assert place[1]["a0"] == 1
