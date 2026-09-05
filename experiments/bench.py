"""Run the (grid x seed) regression matrix in parallel.

The individual scenarios are embarrassingly parallel, so the matrix is
dispatched over a process pool.  Results are appended (one JSON line per
finished scenario) to ``bench_results.jsonl`` next to this script;
already-recorded (grid, seed) pairs are skipped on re-runs.

Usage::

    python experiments/bench.py                # 6 grids x 5 seeds
    python experiments/bench.py 32x32,100x100  # chosen grids, all seeds
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import random
import sys
import time

from netlistx.readwrite import read_json

from nnsplace.placement import NnsPlacer
from nnsplace.placement_cfg import NnsConfig

GRIDS = [(30, 30), (30, 40), (32, 32), (40, 30), (50, 50), (100, 100)]
SEEDS = [0, 1, 2, 3, 831]
_HERE = os.path.dirname(os.path.abspath(__file__))
_NETLIST = os.path.normpath(os.path.join(_HERE, "..", "testcases", "p1.json"))
_OUT = os.path.join(_HERE, "bench_results.jsonl")


def run_scenario(args: tuple) -> dict:
    gx, gy, seed = args
    random.seed(seed)
    H = read_json(_NETLIST)
    n = H.number_of_modules()
    placer = NnsPlacer(H, NnsConfig(gx, gy, 40, 40))
    place: list[dict[int, int]] = [{i: 0 for i in range(n)} for _ in range(2)]
    placer.init_placement(place)
    placer.io_assign(place)
    t0 = time.perf_counter()
    niter, worst = placer.run(place, 2000)
    elapsed = time.perf_counter() - t0
    digest = hashlib.sha256()
    for v in range(n):
        digest.update(f"{place[0][v]},{place[1][v]};".encode())
    return {
        "grid": f"{gx}x{gy}",
        "seed": seed,
        "niter": niter,
        "worst": worst,
        "time": round(elapsed, 3),
        "place_hash": digest.hexdigest()[:16],
    }


def main(grids: list, seeds: list) -> None:
    done = set()
    if os.path.exists(_OUT):
        with open(_OUT, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add((r["grid"], r["seed"]))
                except (json.JSONDecodeError, KeyError):
                    pass
    jobs = [(gx, gy, s) for (gx, gy) in grids for s in seeds]
    jobs = [j for j in jobs if (f"{j[0]}x{j[1]}", j[2]) not in done]
    if not jobs:
        print("all scenarios already recorded; nothing to do")
        return
    workers = min(len(jobs), os.cpu_count() or 1)
    print(f"running {len(jobs)} scenarios on {workers} workers -> {_OUT}")
    with open(_OUT, "a", encoding="utf-8") as f:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
            for r in ex.map(run_scenario, jobs):
                f.write(json.dumps(r) + "\n")
                f.flush()
                print(
                    f"{r['grid']} seed={r['seed']} niter={r['niter']} "
                    f"worst={r['worst']} t={r['time']}s hash={r['place_hash']}"
                )


if __name__ == "__main__":
    grids = GRIDS
    if len(sys.argv) > 1:
        grids = [
            (int(a.split("x")[0]), int(a.split("x")[1])) for a in sys.argv[1].split(",")
        ]
    main(grids, SEEDS)
