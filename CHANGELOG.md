# Changelog

## Version 0.2 (2026-10-09)

### Features
- **Directed Yosys routing**: Added a driver-aware flow graph and end-to-end directed Yosys routing (~80% density), with directed routing figures (pad-driven nets) and an `fir_par8` node-link testcase for C++ consumption. (#819ac1f, #7a28006, #ba80c4d)
- **`NnsConfig` tuning knobs + safety**: Added optional tuning knobs with safe defaults, guarded the reserved column, and decoupled the iteration caps (`max_rounds`). (#49b4170, #a1e4fe8, #7970fb7)
- **Line limits & legalization fallback**: Cap the per-line limit for small designs on large grids, and legalize crowded buckets via a global free-slot fallback. (#c618955, #28e5a87)
- **Infrastructure reuse**: Replaced the duplicated local infra (`netlist.py`, `neg_cycle.py`, `tiny_digraph.py`, `min_parametric.py`) with the sibling `netlistx` / `digraphx` / `physdes` packages. (#00963f9)

### Performance
- **Solver & legalizer hot paths**: Cut per-edge solver overhead and legalize without NetworkX graphs; share the flow-graph adjacency with the solver instead of copying it; eliminate `Fraction` churn. (#b167b01, #3e2bc65, #6ee4f25)
- **Strategy refactors**: Extracted a `WireLengthModel` strategy with a per-axis optimization pass and a `PlacerState` memento with legalizer strategies. (#cf38f72, #765d474, #161751b)

### Testing & Code Quality
- **Coverage raised to 96%**: Added netlist tests plus dedicated tests for `line_limit`, directed flow graphs, `placement_cfg`, and module-weight range / pick-one-only coverage. (#229b340, #df481bd, #90e2bcc, #7a28006, #49b4170)
- **NNS-vs-quadratic comparison**: Added a comparison harness and recorded the results. (#617a40c, #5bc3c98)

### Code Cleanup
- **Removed dead code & boilerplate**: Dropped the PyScaffold skeleton and the duplicated infra modules, removed the obsolete `GEMINI.md` and slides DOCX, and stripped stray blank lines and AI slop. (#77f8fac, #00963f9, #864783d, #3e64750, #f6bd989)

### Documentation
- **Fairness-centric global placement paper**: Added `paper/fairness-paper.md` with NNS algorithm, routing and evaluation sections, HPWL and history coverage, a preliminary NNS-vs-quadratic comparison, and review fixes. (#1edb9a2, #e2ab0a6, #391b3d5, #56f8af8)
- **Beamer talk + figures**: Added `paper/fairness-talk.md` plus placement/congestion figures and build targets. (#a433835, #e60bc7e, #fd52b91)
- **svgbob FPGA grid diagram**: Added to the module docstring. (#b0b4224)
- **AGENTS.md**: Added agent guidelines. (#ff79e28)

### Build & CI
- **Modern workflow**: Replaced the legacy `pythonapp` workflow with `python-app`, updated the GitHub Actions versions, and resolved the mypy errors. (#5ce8563, #0a71430, #79bc390)
- **Paper build**: Added the `paper/` Makefile + beamer config and ignored LaTeX artifacts and local `refs/`. (#fd52b91, #241d8ca)
