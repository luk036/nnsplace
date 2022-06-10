# Notes

# Inputs

- configuration:
  e.g. 50 x 50
- netlist with I/O cells
- cost/wire-length function m(s1, s2)
  - homogeneous
  - monotonic, but not necessary linear or convex

# Outputs:

- position of cells and I/O's 

# Objective:

- minimize the worst wire-length
- Why not the total wire-length?
  - fairness

# Technique

- Network-flow like algorithms
- Legalization-assisted optimization


# TODO: 

- More experiments
- ASIC placement
- C++ porting





## View Profile and Call Tree

```bash
> sudo apt install kcachegrind
> sudo apt install kcachegrind-converters
> easy_install pyprof2calltree
> python -m cProfile -o profile_data.pyprof nnsplace/tests/test_FDBiPartMgr.py
> pyprof2calltree -i profile_data.pyprof -k
```
