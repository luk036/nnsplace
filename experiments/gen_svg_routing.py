"""Regenerate placement SVG figures with global-routing trees.

Takes the historical ``ioloop{gx}x{gy}.svg`` figures (produced by gen_svg.py)
as a starting point, keeps the placed cells/pads byte-identical, replaces the
straight green pad-to-module lines with the orthogonal branches of the
routing trees computed by ``physdes.router.GlobalRouter`` for every net, and
writes the result to a new ``ioloop{gx}x{gy}-routed.svg`` file.

Every net is routed (so the reported total wirelength covers the whole
netlist); only nets that touch an I/O pad are drawn, matching the readability
choice of the original figures.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Dict, List, Tuple

from netlistx.readwrite import read_json
from physdes.point import Point
from physdes.router.global_router import GlobalRouter

P = 40
SRC = r"D:\github\luk036.github.io\phys_des\fairness-placer.files"
H = read_json(r"D:\github\py\nnsplace\testcases\p1.json")
N_MOD = H.number_of_modules()
NUM_CELLS = N_MOD - H.num_pads
RAW = json.load(open(r"D:\github\py\nnsplace\testcases\p1.json", encoding="utf-8"))
EDGES = RAW.get("links") or RAW.get("edges")
NET_MODS: Dict[int, List[int]] = defaultdict(list)
for e in EDGES:
    NET_MODS[e["target"]].append(e["source"])


def parse_place(path: str) -> List[Dict[int, int]]:
    """Recover the placement grid coordinates from the use tags of a figure."""
    place: List[Dict[int, int]] = [{}, {}]
    i = 0
    for line in open(path, encoding="utf-8"):
        if not line.startswith("<use"):
            continue
        place[0][i] = int(line.split('x="')[1].split('"')[0]) // P
        place[1][i] = int(line.split('y="')[1].split('"')[0]) // P
        i += 1
    return place


def draw_edge(
    acc: List[str],
    ux: int,
    uy: int,
    vx: int,
    vy: int,
    vertical_first: bool,
) -> None:
    """Emit an orthogonal (L-shaped) branch from pixel point u to pixel point v."""
    if ux == vx or uy == vy:
        acc.append(f'<line x1="{ux}" y1="{uy}" x2="{vx}" y2="{vy}"/>')
        return
    if vertical_first:
        acc.append(f'<line x1="{ux}" y1="{uy}" x2="{ux}" y2="{vy}"/>')
        acc.append(f'<line x1="{ux}" y1="{vy}" x2="{vx}" y2="{vy}"/>')
    else:
        acc.append(f'<line x1="{ux}" y1="{uy}" x2="{vx}" y2="{uy}"/>')
        acc.append(f'<line x1="{vx}" y1="{uy}" x2="{vx}" y2="{vy}"/>')


def route_net(
    ms: List[int],
    place: List[Dict[int, int]],
    gx: int,
    gy: int,
) -> Tuple[object, bool]:
    """Route one net with the physdes global router.

    The source is the I/O pad when the net has one, else the first module.
    Returns the routing tree and whether the net touches a pad.
    """
    pads = [m for m in ms if m >= NUM_CELLS]
    src = pads[0] if pads else ms[0]
    terms = [m for m in ms if m != src]
    router = GlobalRouter(
        Point(place[0][src], place[1][src]),
        [Point(place[0][t], place[1][t]) for t in terms],
    )
    router.route_with_steiners()
    px, py = place[0][src], place[1][src]
    vertical_first = (py == 0 or py == gy + 1) and not (px == 0 or px == gx + 1)
    router.tree.vertical_first = vertical_first  # type: ignore[attr-defined]
    return router.tree, bool(pads)


def emit_tree_lines(tree: object, acc: List[str], vertical_first: bool) -> None:
    """Append orthogonal branches for every parent/child edge of a tree."""
    src_node = getattr(tree, "source")
    stack = [src_node]
    while stack:
        node = stack.pop()
        for child in node.children:
            ux = node.pt.xcoord * P + 20
            uy = node.pt.ycoord * P + 20
            vx = child.pt.xcoord * P + 20
            vy = child.pt.ycoord * P + 20
            draw_edge(acc, ux, uy, vx, vy, vertical_first)
            stack.append(child)


def process(gx: int, gy: int) -> None:
    """Rebuild one figure replacing straight lines with routing trees."""
    path = f"{SRC}\\ioloop{gx}x{gy}.svg"
    text = open(path, encoding="utf-8").read()
    lines = [s for s in text.split("\n") if not s.startswith("<line")]
    while lines and lines[-1].strip() == "":
        lines.pop()
    assert lines[-1] == "</svg>"
    lines.pop()

    place = parse_place(path)
    acc: List[str] = []
    total_wl = 0
    for nid in H.nets:
        tree, has_pad = route_net(NET_MODS[nid], place, gx, gy)
        total_wl += tree.calculate_total_wirelength()
        if has_pad:
            emit_tree_lines(tree, acc, tree.vertical_first)  # type: ignore[attr-defined]

    out = f"{SRC}\\ioloop{gx}x{gy}-routed.svg"
    with open(out, "w", encoding="utf-8", newline="\n") as fw:
        fw.write("\n".join(lines + acc + ["</svg>"]) + "\n")
    print(
        f"{gx}x{gy}: routed WL={total_wl * 40} (cost units), {total_wl} grid units, "
        f"segments={len(acc)}"
    )


if __name__ == "__main__":
    for gx, gy in [(30, 30), (30, 40), (32, 32), (40, 30), (50, 50), (100, 100)]:
        process(gx, gy)
