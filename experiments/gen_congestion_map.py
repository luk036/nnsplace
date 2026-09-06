"""Generate congestion maps from the globally routed placement.

Counts, for every routed net tree, how many wires cross each grid-cut segment
between adjacent lattice points (the same orthogonal L-shaped branches that
gen_svg_routing.py draws).  Per core cell (x, y) the x-direction value is the
most-congested horizontal cut segment to its left or right, the y-direction
value the most-congested vertical cut segment below or above it, and the
combined value their element-wise maximum.  Each map is normalised so its own
busiest cut becomes 100% and rendered with the green-yellow-red palette used
by ``physdes.steiner_forest.congestion_map``.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from gen_svg_routing import NET_MODS, SRC, H, parse_place, route_net

GRIDS = [(30, 30), (30, 40), (32, 32), (40, 30), (50, 50), (100, 100)]


def count_edge(
    h: Dict[Tuple[int, int], int],
    v: Dict[Tuple[int, int], int],
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    vertical_first: bool,
) -> None:
    """Add one L-shaped branch between lattice points to the cut counters."""
    if x1 == x2:
        for r in range(min(y1, y2), max(y1, y2)):
            v[(x1, r)] = v.get((x1, r), 0) + 1
    elif y1 == y2:
        for c in range(min(x1, x2), max(x1, x2)):
            h[(c, y1)] = h.get((c, y1), 0) + 1
    elif vertical_first:
        for r in range(min(y1, y2), max(y1, y2)):
            v[(x1, r)] = v.get((x1, r), 0) + 1
        for c in range(min(x1, x2), max(x1, x2)):
            h[(c, y2)] = h.get((c, y2), 0) + 1
    else:
        for c in range(min(x1, x2), max(x1, x2)):
            h[(c, y1)] = h.get((c, y1), 0) + 1
        for r in range(min(y1, y2), max(y1, y2)):
            v[(x2, r)] = v.get((x2, r), 0) + 1


def count_tree(
    tree: object,
    vertical_first: bool,
    h: Dict[Tuple[int, int], int],
    v: Dict[Tuple[int, int], int],
) -> None:
    """Add every parent/child branch of a routing tree to the cut counters."""
    stack = [getattr(tree, "source")]
    while stack:
        node = stack.pop()
        for child in node.children:
            count_edge(
                h,
                v,
                node.pt.xcoord,
                node.pt.ycoord,
                child.pt.xcoord,
                child.pt.ycoord,
                vertical_first,
            )
            stack.append(child)


def count_cuts(
    place: List[Dict[int, int]], gx: int, gy: int
) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], int], int]:
    """Count wire crossings per horizontal and vertical cut segment."""
    h: Dict[Tuple[int, int], int] = {}
    v: Dict[Tuple[int, int], int] = {}
    total = 0
    for nid in H.nets:
        tree, _ = route_net(NET_MODS[nid], place, gx, gy)
        total += tree.calculate_total_wirelength()
        count_tree(tree, tree.vertical_first, h, v)  # type: ignore[attr-defined]
    return h, v, total


def build_maps(
    h: Dict[Tuple[int, int], int],
    v: Dict[Tuple[int, int], int],
    gx: int,
    gy: int,
) -> Tuple[List[List[int]], List[List[int]], List[List[int]]]:
    """Return x, y and combined raw per-cell congestion grids."""
    xm = [[0 for _ in range(gx)] for _ in range(gy)]
    ym = [[0 for _ in range(gx)] for _ in range(gy)]
    for y in range(1, gy + 1):
        for x in range(1, gx + 1):
            xm[y - 1][x - 1] = max(h.get((x - 1, y), 0), h.get((x, y), 0))
            ym[y - 1][x - 1] = max(v.get((x, y - 1), 0), v.get((x, y), 0))
    cm = [[max(xm[i][j], ym[i][j]) for j in range(gx)] for i in range(gy)]
    return xm, ym, cm


def to_percent(grid: List[List[int]]) -> List[List[int]]:
    """Scale a raw congestion grid so its busiest cut becomes 100."""
    peak = max(max(row) for row in grid)
    if peak == 0:
        return [[0 for _ in row] for row in grid]
    return [[round(100 * val / peak) for val in row] for row in grid]


def color_at(value: int) -> str:
    """Green (0) -> yellow (50) -> red (100) interpolation."""
    if value <= 50:
        return f"#{int(255 * value / 50):02x}ff00"
    return f"#ff{int(255 * (100 - value) / 50):02x}00"


def draw_map(title: str, grid: List[List[int]], peak: int, out: str) -> None:
    """Render one congestion heatmap SVG."""
    gy, gx = len(grid), len(grid[0])
    cell = min(40, max(5, 1000 // max(gx, gy)))
    padding = 24
    title_h = 70
    legend_w = 110
    width = gx * cell + 2 * padding + legend_w
    height = gy * cell + 2 * padding + title_h
    show_val = cell >= 26

    svg = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{padding}" y="{34}" font-size="22" font-family="Arial">{title}</text>',
        f'<text x="{padding}" y="{56}" font-size="14" fill="#555555" font-family="Arial">busiest cut: {peak} wires</text>',
    ]
    for i in range(gy):
        for j in range(gx):
            pct = grid[i][j]
            x = padding + j * cell
            y = title_h + padding + i * cell
            svg.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{color_at(pct)}" stroke="#cccccc" stroke-width="1"/>'
            )
            if show_val:
                svg.append(
                    f'<text x="{x + cell // 2}" y="{y + cell // 2 + 5}" font-size="14" text-anchor="middle" fill="black" font-family="Arial">{pct}</text>'
                )

    lx = padding + gx * cell + 30
    ly = title_h + padding
    bar_h = gy * cell
    svg.append(
        f'<text x="{lx}" y="{ly - 10}" font-size="16" font-family="Arial">Congestion %</text>'
    )
    svg.append(
        f'<rect x="{lx}" y="{ly}" width="30" height="{bar_h}" fill="url(#grad)"/>'
    )
    for label in range(0, 101, 25):
        yy = ly + bar_h - int(label / 100 * bar_h)
        svg.append(
            f'<text x="{lx + 38}" y="{yy + 5}" font-size="12" font-family="Arial">{label}</text>'
        )
        svg.append(
            f'<line x1="{lx - 5}" y1="{yy}" x2="{lx}" y2="{yy}" stroke="black" stroke-width="1"/>'
        )
    svg.append("<defs>")
    svg.append('<linearGradient id="grad" x1="0%" y1="100%" x2="0%" y2="0%">')
    svg.append('<stop offset="0%" style="stop-color:#00ff00"/>')
    svg.append('<stop offset="50%" style="stop-color:#ffff00"/>')
    svg.append('<stop offset="100%" style="stop-color:#ff0000"/>')
    svg.append("</linearGradient>")
    svg.append("</defs>")
    svg.append("</svg>")

    with open(out, "w", encoding="utf-8", newline="\n") as fw:
        fw.write("\n".join(svg) + "\n")


def process(gx: int, gy: int) -> None:
    """Compute and save the three congestion maps for one grid."""
    place = parse_place(f"{SRC}\\ioloop{gx}x{gy}.svg")
    h, v, total = count_cuts(place, gx, gy)
    xm, ym, cm = build_maps(h, v, gx, gy)

    peak_x = max(max(row) for row in xm)
    peak_y = max(max(row) for row in ym)
    peak_c = max(max(row) for row in cm)
    draw_map(
        f"Congestion x-direction ({gx}x{gy})",
        to_percent(xm),
        peak_x,
        f"{SRC}\\congestion{gx}x{gy}-x.svg",
    )
    draw_map(
        f"Congestion y-direction ({gx}x{gy})",
        to_percent(ym),
        peak_y,
        f"{SRC}\\congestion{gx}x{gy}-y.svg",
    )
    draw_map(
        f"Congestion combined ({gx}x{gy})",
        to_percent(cm),
        peak_c,
        f"{SRC}\\congestion{gx}x{gy}-combined.svg",
    )
    print(
        f"{gx}x{gy}: routed WL={total * 40} (cost), H+V={sum(h.values()) + sum(v.values())}, "
        f"peak_x={peak_x} peak_y={peak_y} peak_comb={peak_c}"
    )


if __name__ == "__main__":
    for gx, gy in GRIDS:
        process(gx, gy)
