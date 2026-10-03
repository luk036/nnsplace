"""Placement-objective comparison harness: min-max fairness (NNS) vs an aggregate placer.

Scaffold for the head-to-head evaluation called out in the paper's "Limitations
and Threats to Validity" section.  It runs two placers on the same netlist and
reports the same metrics for each: worst per-arc wire length (the NNS min-max
objective), total HPWL (the aggregate objective), the busiest routed grid cut
(the fairness-relevant quantity), total routed wire length, legality, and time.

``nns`` uses :mod:`nnsplace.placement`.  ``quadratic`` is a deliberately simple
aggregate baseline -- quadratic (Laplacian) wirelength via SciPy, then row-based
legalization -- a foil for the aggregate objective, not a SOTA placer; wiring in
RePlAce/DREAMPlace behind the same signature is the intended extension.

Routed wire length is a proxy from physdes orthogonal routing trees over the
bins.  A true sign-off number needs a detailed router such as TritonRoute inside
OpenROAD; when it is unavailable this harness records that explicitly rather
than fabricating a number.

Usage::

    python experiments/compare.py testcases/p1.json --grids 32x32,50x50
    python experiments/compare.py path/to/ibm01.net

"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import numpy as np
import scipy.sparse as sp
from netlistx.netlist import Netlist
from netlistx.readwrite import read_are, read_json, read_netd
from physdes.point import Point
from physdes.router.global_router import GlobalRouter
from scipy.sparse.linalg import spsolve

from nnsplace.placement import NnsPlacer
from nnsplace.placement_cfg import NnsConfig

Place = List[Dict[Any, int]]


def load_netlist(path: str) -> Netlist:
    if path.endswith(".json"):
        return read_json(path)
    if path.endswith(".net"):
        hyprgraph = read_netd(path)
        are = path[: -len(".net")] + ".are"
        if os.path.exists(are):
            read_are(hyprgraph, are)
        return hyprgraph
    raise ValueError(f"unsupported netlist format: {path}")


def cells_and_pads(hyprgraph: Netlist) -> Tuple[int, int]:
    n = hyprgraph.number_of_modules()
    return n - hyprgraph.num_pads, n


def _count_edge(
    h: Dict[Tuple[int, int], int],
    v: Dict[Tuple[int, int], int],
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    vertical_first: bool,
) -> None:
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


def _count_tree(
    tree: Any, h: Dict[Tuple[int, int], int], v: Dict[Tuple[int, int], int]
) -> None:
    vertical_first = getattr(tree, "vertical_first", False)
    stack = [tree.source]
    while stack:
        node = stack.pop()
        for child in node.children:
            _count_edge(
                h,
                v,
                node.pt.xcoord,
                node.pt.ycoord,
                child.pt.xcoord,
                child.pt.ycoord,
                vertical_first,
            )
            stack.append(child)


def congestion(
    hyprgraph: Netlist, place: Place, gx: int, gy: int
) -> Tuple[int, int, int]:
    """Route every net with physdes and count grid-cut crossings.

    Returns ``(peak_cut, routed_wirelength, num_nonzero_cuts)``; this is the
    same counting as ``experiments/gen_congestion_map.py``, so ``peak_cut`` is
    the quantity the paper's congestion maps visualize.
    """
    num_cells, _ = cells_and_pads(hyprgraph)
    h: Dict[Tuple[int, int], int] = {}
    v: Dict[Tuple[int, int], int] = {}
    for nid in hyprgraph.nets:
        members = list(hyprgraph.ugraph[nid])
        pads = [m for m in members if m >= num_cells]
        src = pads[0] if pads else members[0]
        terms = [m for m in members if m != src]
        if not terms:
            continue
        router = GlobalRouter(
            Point(place[0][src], place[1][src]),
            [Point(place[0][t], place[1][t]) for t in terms],
        )
        router.route_with_steiners()
        px, py = place[0][src], place[1][src]
        router.tree.vertical_first = (py == 0 or py == gy + 1) and not (  # type: ignore[attr-defined]
            px == 0 or px == gx + 1
        )
        _count_tree(router.tree, h, v)
    routed = sum(h.values()) + sum(v.values())
    peak = max([0] + list(h.values()) + list(v.values()))
    return peak, routed, len(h) + len(v)


def is_legal(hyprgraph: Netlist, place: Place, gx: int, gy: int, reserved: int) -> bool:
    num_cells, n = cells_and_pads(hyprgraph)
    seen: set = set()
    for v in range(num_cells):
        x, y = place[0][v], place[1][v]
        if not (1 <= x <= gx and 1 <= y <= gy) or x == reserved:
            return False
        if (x, y) in seen:
            return False
        seen.add((x, y))
    for v in range(num_cells, n):
        x, y = place[0][v], place[1][v]
        if not (x in (0, gx + 1) or y in (0, gy + 1)):
            return False
    return True


def place_nns(
    hyprgraph: Netlist, cfg: NnsConfig, max_rounds: int
) -> Tuple[Place, dict]:
    n = hyprgraph.number_of_modules()
    placer = NnsPlacer(hyprgraph, cfg)
    place: Place = [{i: 0 for i in range(n)}, {i: 0 for i in range(n)}]
    placer.init_placement(place)
    placer.io_assign(place)
    t0 = time.perf_counter()
    niter, worst = placer.run(place, max_rounds)
    return place, {
        "placer": "nns",
        "iters": niter,
        "worst_reported": worst,
        "time": time.perf_counter() - t0,
    }


def _arc_weights(hyprgraph: Netlist) -> Dict[Tuple[int, int], float]:
    num_cells, _ = cells_and_pads(hyprgraph)
    weights: Dict[Tuple[int, int], float] = defaultdict(float)
    for nid in hyprgraph.nets:
        members = list(hyprgraph.ugraph[nid])
        cells = [m for m in members if m < num_cells]
        pads = [m for m in members if m >= num_cells]
        for c in cells:
            for p in pads:
                weights[(min(c, p), max(c, p))] += 1.0
        for i, a in enumerate(cells):
            for b in cells[i + 1 :]:
                weights[(min(a, b), max(a, b))] += 1.0
    return weights


def _ring_slots(gx: int, gy: int) -> List[Tuple[int, int]]:
    slots: List[Tuple[int, int]] = []
    slots += [(x, 0) for x in range(1, gx + 1)]
    slots += [(gx + 1, y) for y in range(1, gy + 1)]
    slots += [(x, gy + 1) for x in range(gx, 0, -1)]
    slots += [(0, y) for y in range(gy, 0, -1)]
    return slots


def _place_pads(pads: List[int], gx: int, gy: int) -> Dict[int, Tuple[int, int]]:
    slots = _ring_slots(gx, gy)
    return {
        p: slots[(i * len(slots)) // max(1, len(pads)) % len(slots)]
        for i, p in enumerate(pads)
    }


def _legalize_rows(
    place: Place, num_cells: int, gx: int, gy: int, reserved: int
) -> None:
    rows: Dict[int, List[int]] = defaultdict(list)
    for v in range(num_cells):
        rows[min(gy, max(1, place[1][v]))].append(v)
    occupied: set = set()
    overflow: List[int] = []
    for y in range(1, gy + 1):
        col = 1
        for v in sorted(rows[y], key=lambda w: (place[0][w], w)):
            while col <= gx and (col == reserved or (col, y) in occupied):
                col += 1
            if col > gx:
                overflow.append(v)
                continue
            place[0][v], place[1][v] = col, y
            occupied.add((col, y))
            col += 1
    for v in overflow:
        free = next(
            (
                (x, y)
                for y in range(1, gy + 1)
                for x in range(1, gx + 1)
                if x != reserved and (x, y) not in occupied
            ),
            None,
        )
        if free is None:
            raise RuntimeError(f"grid {gx}x{gy} lacks capacity for the baseline")
        place[0][v], place[1][v] = free
        occupied.add(free)


def _scale(arr: np.ndarray, lo: int, hi: int) -> np.ndarray:
    a, b = float(arr.min()), float(arr.max())
    if b - a < 1e-9:
        return np.full_like(arr, (lo + hi) / 2.0)
    return lo + (arr - a) / (b - a) * (hi - lo)


def place_quadratic(hyprgraph: Netlist, cfg: NnsConfig) -> Tuple[Place, dict]:
    gx, gy = cfg.grid
    num_cells, n = cells_and_pads(hyprgraph)
    pads = list(range(num_cells, n))
    pad_xy = _place_pads(pads, gx, gy)
    weights = _arc_weights(hyprgraph)

    t0 = time.perf_counter()
    lap = sp.lil_matrix((num_cells, num_cells))
    bx = np.zeros(num_cells)
    by = np.zeros(num_cells)
    for (a, b), w in weights.items():
        a_is_cell, b_is_cell = a < num_cells, b < num_cells
        if a_is_cell and b_is_cell:
            lap[a, a] += w
            lap[b, b] += w
            lap[a, b] -= w
            lap[b, a] -= w
        elif a_is_cell:
            lap[a, a] += w
            bx[a] += w * pad_xy[b][0]
            by[a] += w * pad_xy[b][1]
        elif b_is_cell:
            lap[b, b] += w
            bx[b] += w * pad_xy[a][0]
            by[b] += w * pad_xy[a][1]

    # Tikhonov term: sub-nets with no pad path would otherwise leave the
    # Laplacian singular; anchor them weakly to the grid centroid.
    eps = 1e-6
    lap = (lap + sp.identity(num_cells) * eps).tocsr()
    bx = bx + eps * (gx + 1) / 2.0
    by = by + eps * (gy + 1) / 2.0
    cx = spsolve(lap, bx) if num_cells else np.zeros(0)
    cy = spsolve(lap, by) if num_cells else np.zeros(0)

    place: Place = [{}, {}]
    tx, ty = _scale(cx, 1, gx), _scale(cy, 1, gy)
    for v in range(num_cells):
        place[0][v] = int(round(tx[v]))
        place[1][v] = int(round(ty[v]))
    for p in pads:
        place[0][p], place[1][p] = pad_xy[p]
    _legalize_rows(place, num_cells, gx, gy, cfg.reserved_col)
    return place, {
        "placer": "quadratic",
        "iters": 1,
        "worst_reported": None,
        "time": time.perf_counter() - t0,
    }


def evaluate(hyprgraph: Netlist, place: Place, cfg: NnsConfig, meta: dict) -> dict:
    gx, gy = cfg.grid
    probe = NnsPlacer(hyprgraph, cfg)
    peak, routed, cuts = congestion(hyprgraph, place, gx, gy)
    return {
        **meta,
        "grid": f"{gx}x{gy}",
        "worst": probe.calc_worst_wirelength(place),
        "hpwl": probe.calc_total_HPWL(place),
        "peak": peak,
        "routed": routed,
        "cuts": cuts,
        "mean": round(routed / cuts, 3) if cuts else 0.0,
        "legal": is_legal(hyprgraph, place, gx, gy, cfg.reserved_col),
        "time": round(float(meta["time"]), 3),
    }


def signoff(router: str) -> dict:
    """Report the detailed-router status, never a fabricated routed number."""
    if router == "none":
        return {"router": "none", "status": "skipped"}
    tool = "openroad" if router == "tritonroute" else router
    path = shutil.which(tool)
    if path is None:
        return {
            "router": router,
            "status": f"skipped: '{tool}' not found on PATH",
            "note": "install OpenROAD/TritonRoute and provide LEF/DEF for sign-off",
        }
    return {
        "router": router,
        "status": "available",
        "tool": path,
        "note": "run TritonRoute on the exported DEF for the sign-off wirelength",
    }


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="compare NNS vs an aggregate placer")
    ap.add_argument("netlists", nargs="+", help="path(s) to .json or IBM .net")
    ap.add_argument("--grids", default="32x32", help="comma-separated gxXgy list")
    ap.add_argument("--max-rounds", type=int, default=10, help="outer rounds")
    ap.add_argument("--delta", type=int, default=40, help="per-axis cost weight")
    ap.add_argument("--router", default="tritonroute", help="tritonroute|none")
    ap.add_argument("--out", default="experiments/compare_results.json")
    args = ap.parse_args(argv)

    grids = [tuple(int(t) for t in g.split("x")) for g in args.grids.split(",")]
    results: List[dict] = []
    for path in args.netlists:
        hyprgraph = load_netlist(path)
        num_cells, n = cells_and_pads(hyprgraph)
        print(
            f"\n=== {os.path.basename(path)}: {num_cells} cells + "
            f"{n - num_cells} pads, {hyprgraph.number_of_nets()} nets ==="
        )
        for gx, gy in grids:
            cfg = NnsConfig(gx, gy, args.delta, args.delta)
            for placer_fn in (place_nns, place_quadratic):
                if placer_fn is place_nns:
                    place, meta = placer_fn(hyprgraph, cfg, args.max_rounds)
                else:
                    place, meta = placer_fn(hyprgraph, cfg)
                row = evaluate(hyprgraph, place, cfg, meta)
                row["netlist"] = os.path.basename(path)
                results.append(row)
                print(
                    f"  {row['grid']:>8} {meta['placer']:>10}: "
                    f"worst={row['worst']:>6} hpwl={row['hpwl']:>8} "
                    f"peak={row['peak']:>4} routed={row['routed']:>7} "
                    f"legal={row['legal']} t={row['time']}s"
                )

    status = signoff(args.router)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fw:
        json.dump({"results": results, "signoff": status}, fw, indent=2)
        fw.write("\n")
    print(f"\nwrote {args.out}\nsignoff: {status['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
