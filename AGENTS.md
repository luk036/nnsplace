# AGENTS.md - Agent Guidelines for nnsplace

## Build/Lint/Test Commands

### Testing
```bash
# Run all tests
pytest
# Or via tox (isolated environment)
tox

# Run single test
pytest tests/test_placement.py::test_cost

# Run with verbose output (default) and coverage (default addopts)
pytest --cov nnsplace --cov-report term-missing --verbose

# Doctests are enabled by default (--doctest-modules in setup.cfg)
```

### Linting & Formatting
```bash
# Run all pre-commit hooks (recommended before committing)
pre-commit run --all-files

# Individual tools
black src/nnsplace tests/     # Format code (line length 188)
isort src/nnsplace tests/     # Sort imports (Black profile)
flake8 src/nnsplace tests/    # Lint (max_line_length=188)
mypy src/                     # Type check (Python 3.14 target)
```

### Build
```bash
tox -e build                  # Build sdist + wheel
tox -e clean                  # Remove build artifacts
python -m build .             # Alternative build
```

### Docs
```bash
tox -e docs                   # Build HTML docs
tox -e doctests               # Run doctests via sphinx
tox -e linkcheck              # Check for broken links
```

## Code Style Guidelines

### Project Structure
- Source: `src/nnsplace/` (namespace package)
- Tests: `tests/` mirroring source modules (test_placement.py -> placement.py)
- Test data: `testcases/*.json` (netlists in node-link format)
- Version managed via setuptools_scm (version_scheme=no-guess-dev)

### Naming Conventions
- **Classes**: PascalCase (e.g., `NnsPlacer`, `Netlist`, `SimpleGraph`, `TinyGraph`)
- **Functions/Methods**: snake_case (e.g., `create_flow_graph`, `read_json`, `legalize_modules`)
- **Variables**: lowercase_with_underscores
- **Constants**: UPPER_CASE (e.g., `MAX_NEIGHBORHOOD`)
- **Private methods**: Prefix with underscore (e.g., `_count`, `_adj`)

### Type Hints
- Required on all function signatures
- Mix of `typing` module and modern builtin generics:
  ```python
  from typing import Any, Dict, List, Optional, Tuple, Union

  def calc_worst_wirelength(self, place: List[Dict[Any, int]]) -> int:
  def apply_howard(self, place: List[Dict[Any, int]], axis: int) -> tuple[Any, Any]:
  ```
- Use `# type: ignore` for untyped external deps (mywheel, digraphx, netlistx, physdes)

### Docstrings
- **Primary style**: Sphinx/reStructuredText with `:param:`, `:type:`, `:return:`
- Include `>>>` doctest examples in method docstrings (using Mock netlists)
- Use `.. svgbob::` for ASCII-art diagrams (grids, legalization before/after)
- Module-level docstrings explain the placement algorithm

### Imports
- **Order**: stdlib → third-party → local (isort with Black profile)
- Local imports use relative form: `from .placement_cfg import NnsConfig`
- Third-party: `networkx`, `digraphx`, `netlistx`, `physdes`, `mywheel`

### Error Handling
- Use `assert` for invariants and preconditions (grid/count limits)
- Raise `ValueError`/`RuntimeError` for algorithmic failures (e.g., legalization exceeding neighborhood limit)
- Catch specific exceptions (`ValueError`, `KeyError`, `nx.exception.AmbiguousSolution`) when expanding the bipartite matching search

### Testing Patterns
- **Framework**: pytest with doctest support, coverage required
- Use simple `Mock` classes (e.g., `MockNetlist`) and `Mock()` configs instead of heavy mocking
- Use pytest fixtures grouped in a `TestNnsPlacer` class
- Test functions use `test_` prefix and return `-> None`

### Python Version
- CI targets Python 3.10 (python-app) and 3.10/3.11 (multi-platforms)
- mypy configured for Python 3.14

### Pre-commit Hooks (Active)
- trailing-whitespace
- check-added-large-files
- check-ast
- check-json / check-yaml / check-xml
- check-merge-conflict
- debug-statements
- end-of-file-fixer
- requirements-txt-fixer
- mixed-line-ending (auto-fix)
- isort
- black
- flake8

### Configuration Files
- `setup.cfg`: Package metadata, pytest options (--cov nnsplace, --verbose, --doctest-modules), flake8 (max_line_length=188)
- `.flake8`: Formatting rules disabled (extends setup.cfg)
- `pyproject.toml`: Build system (setuptools_scm)
- `tox.ini`: Test environments (default, build, clean, docs, doctests, linkcheck, publish)
- `.isort.cfg`: Import sorting (Black profile, known_first_party=nnsplace)
- `mypy.ini`: Type checking (Python 3.14, ignores for external deps)
- `.coveragerc`: Coverage reporting (branch coverage, excludes repr/debug/asserts)

## Key Project Context

nnsplace is an affordable placement library for FPGA designs:
- **Placement**: "No-nonsense" (NNS) iterative placer optimizing module positions on a grid to minimize worst wirelength (HPWL)
- **Optimization**: Uses Howard's algorithm (parametric minimum-cost flow via digraphx's `MinParametricSolver`/`neg_cycle_q`) and bipartite matching for legalization
- **Netlists**: Provided by netlistx (`read_json`, `create_inverter`, `create_drawf`, `create_random_hgraph`); infrastructure (TinyDiGraph, Netlist, Interval) lives in sibling repos digraphx/netlistx/physdes-py — do not re-implement locally
- **Key dependencies**: `networkx` (graphs, bipartite matching), `mywheel` (RepeatArray, MapAdapter), `digraphx` (TinyDiGraph, MinParametricSolver), `netlistx` (Netlist), `physdes-py` (Interval for hulls)
