"""Regenerate placement SVG visualizations from testcases/p1.json.

Reproduces the historical outputs/*.svg pipeline: run the NNS placer on a
(gx x gy) grid, then emit the placement as an SVG (cells = #r1 rects,
io pads = #io rects, green pad-to-module connection lines).  The line
drawing mirrors the commented-out code in tests/test_place.py.
"""

from __future__ import annotations

import random
from typing import Any

from netlistx.readwrite import read_json

from nnsplace.placement import NnsPlacer
from nnsplace.placement_cfg import NnsConfig

OUT = r"D:\github\py\nnsplace\outputs"
P = 40  # historical pixel size


def header(gx: int, gy: int) -> list[str]:
    """Byte-exact clone of the historical ioloop*.svg header."""
    w, h = (gx + 2) * P, (gy + 2) * P
    iw, ih = gx * P, gy * P
    ox, oy = (gx + 1) * P, (gy + 1) * P
    return [
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">',
        '  <style type="text/css">',
        '    @import "mysvg.css"',
        '  </style>',
        "",
        "  <!-- Create mask that we'll use to define a slight gradient -->",
        '  <mask maskUnits="userSpaceOnUse" id="fade">',
        "    <!-- Here's that slight gradient -->",
        '    <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="100%">',
        '      <stop offset ="0" style="stop-color: #FFFFFF" />',
        '      <stop offset ="1" style="stop-color: #000000" />',
        '    </linearGradient>',
        '    <!-- The canvas for our mask -->',
        '    <rect fill="url(#gradient)" width="100%" height="100%" />',
        '  </mask>',
        "",
        "  <!-- Let's define the pattern -->",
        "  <!-- The width and height should be double the circle radius we plan to use -->",
        f'  <pattern id="pattern-circles" x="0" y="0" width="{P}" height="{P}" patternUnits="userSpaceOnUse">',
        "    <!-- Now let's draw the circle -->",
        "    <!-- We're going to define the `fill` in the CSS for flexible use -->",
        f'    <circle class="cell" opacity="0.2" cx="20" cy="20" r="15" />',
        '  </pattern>',
        "",
        "  <!-- Let's define the pattern -->",
        "  <!-- The width and height should be double the circle radius we plan to use -->",
        f'  <pattern id="pattern-io" x="0" y="0" width="{P}" height="{P}" patternUnits="userSpaceOnUse">',
        "    <!-- Now let's draw the circle -->",
        "    <!-- We're going to define the `fill` in the CSS for flexible use -->",
        '    <circle class="iopad" opacity="0.2" cx="20" cy="20" r="15" />',
        '  </pattern>',
        "",
        "  <!-- The canvas with our applied pattern -->",
        f'  <rect x="{P}" y="{P}" width="{iw}" height="{ih}" fill="url(#pattern-circles)" />',
        f'  <rect x="{P}" y="0" width="{iw}" height="{P}" fill="url(#pattern-io)" />',
        f'  <rect x="{P}" y="{oy}" width="{iw}" height="{P}" fill="url(#pattern-io)" />',
        f'  <rect x="0" y="{P}" width="{P}" height="{ih}" fill="url(#pattern-io)" />',
        f'  <rect x="{ox}" y="{P}" width="{P}" height="{ih}" fill="url(#pattern-io)" />',
        '  <defs>',
        "    <!-- A circle of radius 200 -->",
        '    <circle id = "s1" cx = "200" cy = "200" r = "200" fill = "yellow" stroke = "black" stroke-width = "3"/>',
        "    <!-- An ellipse (rx=200,ry=150) -->",
        '    <ellipse id = "s2" cx = "200" cy = "150" rx = "200" ry = "150" fill = "salmon" stroke = "black" stroke-width = "3"/>',
        '    <rect id = "r1" width="35" height="35" fill = "#FF00A7" opacity="0.2" stroke = "black" stroke-width = "3"/>',
        '    <rect id = "io" width="35" height="35" fill = "#00E7FF" opacity="0.2" stroke = "black" stroke-width = "3"/>',
        '  </defs>',
    ]


def gen(gx: int, gy: int, seed: int = 831, max_iters: int = 200) -> None:
    """Run the placer and write outputs/ioloop{gx}x{gy}.svg with connections."""
    H = read_json(r"D:\github\py\nnsplace\testcases\p1.json")
    random.seed(seed)
    n = H.number_of_modules()
    num_cells = n - H.num_pads
    placer = NnsPlacer(H, NnsConfig(gx, gy, P, P))
    place: list[dict[Any, int]] = [{}, {}]
    place[0] = {i: 0 for i in range(n)}
    place[1] = {i: 0 for i in range(n)}
    placer.init_placement(place)
    placer.io_assign(place)
    niter, worst = placer.run(place, max_iters)
    print(f"iters={niter} worst={worst}")

    body: list[str] = []
    for i in range(0, num_cells):
        v = H.modules[i]
        body.append(f'<use x="{place[0][v]*P}" y="{place[1][v]*P}" href="#r1"/>')
    for i in range(num_cells, n):
        vp = H.modules[i]
        body.append(f'<use x="{place[0][vp]*P}" y="{place[1][vp]*P}" href="#io"/>')
    for i in range(num_cells, n):
        vp = H.modules[i]
        for vi in placer.ugraph[vp]:
            if vi >= num_cells:
                continue
            body.append(
                f'<line x1="{place[0][vp]*P+20}" y1="{place[1][vp]*P+20}" '
                f'x2="{place[0][vi]*P+20}" y2="{place[1][vi]*P+20}" '
                f'stroke="#00a200" stroke-width="4" stroke-opacity="0.4"/>'
            )
    with open(f"{OUT}\\ioloop{gx}x{gy}.svg", "w", encoding="utf-8", newline="\n") as fw:
        fw.write("\n".join(header(gx, gy) + body) + "\n</svg>\n")
    print(
        f"wrote ioloop{gx}x{gy}.svg: cells={num_cells} pads={H.num_pads} "
        f"lines={sum(1 for b in body if b.startswith('<line'))}"
    )


if __name__ == "__main__":
    gen(50, 50)
