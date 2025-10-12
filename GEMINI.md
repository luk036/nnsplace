# Gemini Code Understanding

## Project Overview

This project, `nnsplace`, is a Python application for FPGA (Field-Programmable Gate Array) placement. The primary goal is to optimize the placement of electronic circuit components (modules) on a grid to minimize the worst-case wire length between connected components.

The core of the project is a placement algorithm that uses a "fairness-centric" (NNS) placement method. This involves iteratively improving an initial random placement using Howard's algorithm, legalizing the placement to avoid overlaps, and assigning I/O pads.

The project is built using Python and relies on libraries like `networkx` for graph manipulation and `scipy` for scientific computing. It also uses several custom libraries for specific functionalities.

## Building and Running

### 1. Environment Setup

The project uses a `conda` environment defined in `environment.yml`. To create and activate the environment, run:

```bash
conda env create -f environment.yml
conda activate nnsplace
```

### 2. Install Dependencies

The Python dependencies are listed in `requirements.txt` and the `requirements` directory. To install them, run:

```bash
pip install -r requirements.txt
pip install git+https://github.com/luk036/mywheel.git
pip install git+https://github.com/luk036/digraphx.git
pip install git+https://github.com/luk036/netlistx.git
pip install git+https://github.com/luk036/physdes-py.git
```

### 3. Development Installation

To install the project in development mode, run:

```bash
python setup.py develop
```

### 4. Running the Placer

The main placement logic is in `src/nnsplace/placement.py`. This file can be executed with a netlist file and configuration to run the placement algorithm.

*(TODO: Add a specific example command to run the placer with a testcase.)*

## Development Conventions

### Code Style and Quality

The project uses several tools to maintain code quality:

*   **`flake8`**: For linting and style checking.
*   **`isort`**: For sorting imports.
*   **`mypy`**: For static type checking.
*   **`pre-commit`**: To run these checks automatically before each commit. The configuration is in `.pre-commit-config.yaml`.

### Testing

The project uses `pytest` for testing. The tests are located in the `tests/` directory. To run the tests, execute:

```bash
pytest
```

## Directory Structure

*   `src/nnsplace/`: Contains the main source code for the placement algorithm.
*   `tests/`: Contains the test suite.
*   `docs/`: Contains the project documentation.
*   `requirements/`: Contains the Python dependency lists.
*   `testcases/`: Contains example netlist files for testing.
*   `outputs/`: Contains output files from placement runs, such as SVG visualizations.
