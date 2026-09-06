"""Place a Yosys netlist and emit driver-rooted routed figures + congestion maps.

End-to-end driver-aware pipeline for one Yosys ``write_json`` module:

1. convert the module to a directed node-link JSON (``directed_netlist.py``)
2. read it back into a ``Netlist`` whose ``net_driver`` map says who drives each net
3. run the NNS placer (the flow graph now contains only driver <-> sink arcs)
4. route every net with ``route_with_constraints()`` from its driver
5. draw the orthogonal trees and the x / y / combined congestion maps.

Run:  python experiments/gen_yosys_figures.py [yosys.json] [module] [gx] [gy]
"""

from __future__ import annotations

import json
import random
import sys
from typing import List, Tuple

from physdes.point import Point
from physdes.router.global_router import GlobalRouter

sys.path.insert(0, r"D:\github\py\nnsplace")
sys.path.insert(0, r"D:\github\py\nnsplace\src")
sys.path.insert(0, r"D:\github\py\nnsplace\experiments")
from directed_netlist import read_directed_json, yosys_file_to_node_link  # noqa: E402

P = 40


def choose_grid(num_cells: int, num_pads: int) -> Tuple[int, int]:
    slots = num_cells + num_pads
    for gx in range(16, 61):
        for gy in range(12, 61):
            if (gx - 1) * gy >= slots:
                return gx, gy
    return 60, 60


def route_net(members: List[int], driver, place, gx: int, gy: int):
    src_x = int(place[0][driver])
    src_y = int(place[1][driver])
    router = GlobalRouter(
        Point(src_x, src_y),
        [Point(int(place[0][m]), int(place[1][m])) for m in members if m != driver],
    )
    router.route_with_constraints()
    vertical_first = (src_y in (0, gy + 1)) and src_x not in (0, gx + 1)
    router.tree.vertical_first = vertical_first
    return router.tree


def analyse(netlist, place, gx: int, gy: int):
    hseg: List[Tuple[int, int, int, int]] = []
    vseg: List[Tuple[int, int, int, int]] = []
    h = [[0] * (gx + 1) for _ in range(gy + 2)]
    v = [[0] * (gy + 1) for _ in range(gx + 2)]
    total_wl = 0

    for net in netlist.nets:
        members = list(netlist.ugraph[net])
        driver = netlist.net_driver.get(net)
        if driver is None:
            pads = [m for m in members if m >= netlist.number_of_modules() - netlist.num_pads]
            driver = pads[0] if pads else members[0]
        if len(members) < 2 or driver not in members:
            continue
        tree = route_net(members, driver, place, gx, gy)
        total_wl += tree.calculate_total_wirelength()
        stack = [tree.source]
        while stack:
            node = stack.pop()
            for child in node.children:
                x1, y1, x2, y2 = (
                    node.pt.xcoord, node.pt.ycoord,
                    child.pt.xcoord, child.pt.ycoord,
                )
                if x1 == x2:
                    for r in range(min(y1, y2), max(y1, y2)):
                        v[x1][r] += 1
                    vseg.append((x1, y1, x2, y2))
                elif y1 == y2:
                    for c in range(min(x1, x2), max(x1, x2)):
                        h[y1][c] += 1
                    hseg.append((x1, y1, x2, y2))
                elif tree.vertical_first:
                    for r in range(min(y1, y2), max(y1, y2)):
                        v[x1][r] += 1
                    for c in range(min(x1, x2), max(x1, x2)):
                        h[y2][c] += 1
                    vseg.append((x1, y1, x1, y2))
                    hseg.append((x1, y2, x2, y2))
                else:
                    for c in range(min(x1, x2), max(x1, x2)):
                        h[y1][c] += 1
                    for r in range(min(y1, y2), max(y1, y2)):
                        v[x2][r] += 1
                    hseg.append((x1, y1, x2, y1))
                    vseg.append((x2, y1, x2, y2))
                stack.append(child)
    return h, v, hseg, vseg, total_wl


def build_maps(h, v, gx: int, gy: int):
    xm = [[0] * gx for _ in range(gy)]
    ym = [[0] * gx for _ in range(gy)]
    for y in range(1, gy + 1):
        for x in range(1, gx + 1):
            xm[y - 1][x - 1] = max(h[y][x - 1], h[y][x])
            ym[y - 1][x - 1] = max(v[x][y - 1], v[x][y])
    cm = [[max(xm[i][j], ym[i][j]) for j in range(gx)] for i in range(gy)]
    peaks = (max(max(r) for r in xm), max(max(r) for r in ym), max(max(r) for r in cm))
    return xm, ym, cm, peaks


def to_percent(grid):
    peak = max(max(row) for row in grid)
    if peak == 0:
        return [[0] * len(row) for row in grid]
    return [[round(100 * value / peak) for value in row] for row in grid]


def color_at(value: int) -> str:
    if value <= 50:
        return f"#{int(255 * value / 50):02x}ff00"
    return f"#ff{int(255 * (100 - value) / 50):02x}00"


def congestion_svg(title, grid, peak) -> str:
    gy, gx = len(grid), len(grid[0])
    cell = max(5, min(40, 1000 // max(gx, gy)))
    pad = 24
    th = 70
    width = gx * cell + 2 * pad + 110
    height = gy * cell + 2 * pad + th
    svg = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{pad}" y="34" font-size="22" font-family="Arial">{title}</text>',
        f'<text x="{pad}" y="56" font-size="14" fill="#555555" font-family="Arial">busiest cut: {peak} wires</text>',
    ]
    for r in range(gy):
        for c in range(gx):
            pct = grid[r][c]
            x = pad + c * cell
            y = th + pad + r * cell
            svg.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="#{color_at(pct)}" stroke="#cccccc" stroke-width="1"/>'
            )
    lx = pad + gx * cell + 30
    ly = th + pad
    bar = gy * cell
    svg.append(f'<text x="{lx}" y="{ly - 10}" font-size="16" font-family="Arial">Congestion %</text>')
    svg.append('<defs><linearGradient id="grad" x1="0%" y1="100%" x2="0%" y2="0%">'
               '<stop offset="0%" style="stop-color:#00ff00"/>'
               '<stop offset="50%" style="stop-color:#ffff00"/>'
               '<stop offset="100%" style="stop-color:#ff0000"/>'
               '</linearGradient></defs>')
    svg.append(f'<rect x="{lx}" y="{ly}" width="30" height="{bar}" fill="url(#grad)"/>')
    for label in range(0, 101, 25):
        yy = ly + bar - int(label / 100 * bar)
        svg.append(f'<text x="{lx + 38}" y="{yy + 5}" font-size="12" font-family="Arial">{label}</text>')
        svg.append(f'<line x1="{lx - 5}" y1="{yy}" x2="{lx}" y2="{yy}" stroke="black" stroke-width="1"/>')
    svg.append("</svg>")
    return "\n".join(svg)


def routed_svg(netlist, place, gx, gy, hseg, vseg) -> str:
    n = netlist.number_of_modules()
    num_cells = n - netlist.num_pads
    w, h = (gx + 2) * P, (gy + 2) * P
    iw, ih = gx * P, gy * P
    ox, oy = (gx + 1) * P, (gy + 1) * P
    svg = [
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">',
        '  <style type="text/css">',
        "    circle.cell { fill: #0062ff; }",
        "    circle.iopad { fill: #ec0000; }",
        "    line { stroke: #00a200; stroke-width: 4; stroke-opacity: 0.4; }",
        "  </style>",
        f'  <pattern id="pattern-circles" x="0" y="0" width="{P}" height="{P}" patternUnits="userSpaceOnUse">',
        '    <circle class="cell" opacity="0.2" cx="20" cy="20" r="15"/>',
        "  </pattern>",
        f'  <pattern id="pattern-io" x="0" y="0" width="{P}" height="{P}" patternUnits="userSpaceOnUse">',
        '    <circle class="iopad" opacity="0.2" cx="20" cy="20" r="15"/>',
        "  </pattern>",
        f'  <rect x="{P}" y="{P}" width="{iw}" height="{ih}" fill="url(#pattern-circles)"/>',
        f'  <rect x="{P}" y="0" width="{iw}" height="{P}" fill="url(#pattern-io)"/>',
        f'  <rect x="{P}" y="{oy}" width="{iw}" height="{P}" fill="url(#pattern-io)"/>',
        f'  <rect x="0" y="{P}" width="{P}" height="{ih}" fill="url(#pattern-io)"/>',
        f'  <rect x="{ox}" y="{P}" width="{P}" height="{ih}" fill="url(#pattern-io)"/>',
        '  <defs>',
        '    <rect id="r1" width="35" height="35" fill="#FF00A7" opacity="0.2" stroke="black" stroke-width="3"/>',
        '    <rect id="io" width="35" height="35" fill="#00E7FF" opacity="0.2" stroke="black" stroke-width="3"/>',
        "  </defs>",
    ]
    for i in range(n):
        px = int(place[0][i]) * P
        py = int(place[1][i]) * P
        svg.append(f'  <use x="{px}" y="{py}" href="#{"r1" if i < num_cells else "io"}"/>')
    for x1, y1, x2, y2 in hseg + vseg:
        svg.append(
            f'  <line x1="{x1 * P + P // 2}" y1="{y1 * P + P // 2}" x2="{x2 * P + P // 2}" y2="{y2 * P + P // 2}"/>'
        )
    svg.append("</svg>")
    return "\n".join(svg)


def main() -> None:
    from netlistx.netlist import Netlist

    import nnsplace.placement_cfg as cfg_module
    from nnsplace.placement import NnsPlacer

    filename = sys.argv[1] if len(sys.argv) > 1 else r"yosys_testcases/sphere3hopf_netlist_simple.json"
    module = sys.argv[2] if len(sys.argv) > 2 else "cordic_trig_16bit_simple_fixed"

    with open(filename, encoding="utf-8") as file:
        data = json.load(file)
    if module not in data["modules"]:
        module = list(data["modules"].keys())[0]
    netlist = read_directed_json(yosys_file_to_node_link(filename, module))

    n = netlist.number_of_modules()
    num_cells = n - netlist.num_pads
    gx = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    gy = int(sys.argv[4]) if len(sys.argv) > 4 else 20

    random.seed(831)
    placer = NnsPlacer(netlist, cfg_module.NnsConfig(gx, gy, P, P, reserved_col=3))
    place = [{i: 0 for i in range(n)}, {i: 0 for i in range(n)}]
    placer.init_placement(place)
    placer.io_assign(place)
    niter, worst = placer.run(place, 200)

    h, v, hseg, vseg, total_wl = analyse(netlist, place, gx, gy)
    xm, ym, cm, peaks = build_maps(h, v, gx, gy)
    check = sum(sum(r) for r in h) + sum(sum(r) for r in v)
    outdir = r"D:\github\py\nnsplace\outputs"
    prefix = f"{outdir}\\yosys_{module.split()[0]}"
    for suffix, grid, peak, title in (
        ("-x.svg", xm, peaks[0], f"Congestion x-direction ({module})"),
        ("-y.svg", ym, peaks[1], f"Congestion y-direction ({module})"),
        ("-combined.svg", cm, peaks[2], f"Congestion combined ({module})"),
    ):
        with open(prefix + suffix, "w", encoding="utf-8") as file:
            file.write(congestion_svg(title, to_percent(grid), peak))
    with open(prefix + "-routed.svg", "w", encoding="utf-8") as file:
        file.write(routed_svg(netlist, place, gx, gy, hseg, vseg))

    print(f"module={module} grid={gx}x{gy} cells={num_cells} pads={netlist.num_pads}")
    print(f"iterations={niter} worst(driver->sink)={worst}")
    print(f"routed_wirelength(cost)={total_wl * P} routed_wirelength(grid)={total_wl}")
    print(f"H+V={check} match={check == total_wl}")
    print(f"peak_x={peaks[0]} peak_y={peaks[1]} peak_combined={peaks[2]}")
    print(f"branches={len(hseg) + len(vseg)} -> {prefix}")


if __name__ == "__main__":
    main()
