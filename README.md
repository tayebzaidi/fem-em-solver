# FEM Electromagnetics Solver

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FEniCSX](https://img.shields.io/badge/FEniCSX-0.7+-green.svg)](https://fenicsproject.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A finite element method (FEM) solver for electromagnetic simulations of MRI coils with gelled saline phantoms, built on [FEniCSX/DolfinX](https://fenicsproject.org/).

> **Project status: early alpha.** Magnetostatics is implemented and validated
> against analytic solutions. The time-harmonic path is currently a **proxy**
> (`E = -jωA`), not a Maxwell solve — material properties do not yet affect computed
> fields, and exported S-parameters come from a placeholder coupling model rather
> than the solved field. See [PROJECT_PLAN.md](PROJECT_PLAN.md) §2 before relying on
> any frequency-domain output.

## Features

**Working today**
- **Magnetostatics**: magnetic vector potential formulation, N1curl elements, gauge penalty
- **Meshing**: parametric Gmsh geometry generation with region tagging and mesh QA
- **Validation**: field uniformity in a Helmholtz configuration (`CV < 1%`). The
  analytic wire/loop comparisons are currently **broken** — see
  [PROJECT_PLAN.md](PROJECT_PLAN.md) §2.3b

**Planned** (see [PROJECT_PLAN.md](PROJECT_PLAN.md))
- **Time-Harmonic**: full Maxwell equations for frequency-domain analysis
- **Coil Models**: loop coils, birdcage coils, TEM coils
- **Material Models**: complex permittivity, dispersion models, gelled saline phantoms
- **MRI-Focused**: B1+ mapping, SAR calculation, coil loading analysis
- **HFSS comparison**: quantitative benchmarking against commercial solvers

## Quick Start

### Installation

#### Option 1: Using Docker (Recommended)

```bash
# Build and start the container
cd docker
docker compose up -d

# Enter the container
docker compose exec fem-em-solver bash
```

**Prerequisites:**
- Docker installed and running
- Your user in the `docker` group (to avoid sudo)

**To add your user to docker group:**
```bash
sudo usermod -aG docker $USER
# IMPORTANT: Log out and log back in for changes to take effect
```

**Test if Docker works:**
```bash
docker ps  # Should show containers without sudo
```

**If you get permission errors** after adding to the docker group, your shell's
process credentials predate the group edit (check: `getent group docker` lists you,
but `id` doesn't show it). Log out and back in, or pick the group up in place:

```bash
sg docker -c 'docker ps'     # runs one command with the group applied
newgrp docker                # or start a subshell with the group applied
```

**Note:** Modern Docker uses `docker compose` (space). Older versions use `docker-compose` (hyphen).

### Running tests

```bash
cd docker && docker compose up -d          # start the service (once per session)
docker compose ps                          # confirm STATUS is "Up"

# from the repo root — logs to docs/testing/
scripts/testing/run_and_log.sh <CHUNK-ID> \
  "docker compose exec -T fem-em-solver bash -lc 'cd /workspace && ./run_tests.sh --smoke'"
```

The repo is bind-mounted at `/workspace`, so source edits take effect without a
rebuild. Use `exec -T` for scripted runs. See
[PROJECT_PLAN.md](PROJECT_PLAN.md) §5 for runtime budget tiers and the full chunk
verification workflow.

#### Option 2: Conda Environment

```bash
conda create -n femem python=3.11
conda activate femem
conda install -c conda-forge fenics-dolfinx gmsh pyvista
pip install -e ".[dev,docs]"
```

### Run Examples (without entering Docker)

```bash
# List available examples
./run_examples.sh --list

# Run one example by number
./run_examples.sh --example 1

# Run multiple examples and set MPI ranks
./run_examples.sh --example 1,3 --nproc 4

# Run all examples
./run_examples.sh --example all --nproc 2
```

The script automatically targets `docker/docker-compose.yml` and runs each selected example as:
`docker compose exec fem-em-solver ... mpiexec -n <nproc> python3 <example>`

### Python API Example

```python
from fem_em_solver import MagnetostaticSolver
from fem_em_solver.coils import CircularLoop

# Create a circular loop coil
coil = CircularLoop(radius=0.05, current=1.0, position=(0, 0, 0))

# Set up solver
solver = MagnetostaticSolver(mesh_resolution=0.005)
solver.add_coil(coil)

# Solve
A = solver.solve()
B = solver.compute_b_field(A)

# Visualize
solver.plot_field(B, component='z')
```

## Project Structure

```
fem-em-solver/
├── src/fem_em_solver/     # Main package
│   ├── core/              # FEM formulations and solvers
│   ├── coils/             # Coil geometry definitions
│   ├── materials/         # Material property models
│   ├── post/              # Post-processing and analysis
│   └── io/                # Mesh and data I/O
├── examples/              # Tutorial notebooks and scripts
├── tests/                 # Test suite
├── docs/                  # Documentation
└── meshes/                # Pre-generated mesh files
```

## Development Phases

| Phase | Scope | State |
|---|---|---|
| 0 | Infrastructure & setup | Partial |
| 1 | Magnetostatics foundation | **Complete** |
| 2 | Time-harmonic Maxwell equations | Not started |
| 3 | Material models & phantoms | Inert presets only |
| 4 | Coil modeling & ports | Placeholder-backed |
| 5 | Full MRI system integration | Blocked on 2–4 |
| 6 | Advanced features | Deferred |

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the chunk backlog, sequencing, and
definition of done.

## Validation

**Current state: one sound check.** `tests/validation/test_helmholtz_v2.py` verifies
central-region field uniformity (`CV < 1%`).

The analytic comparisons for straight wire, circular loop, and h-convergence are
present but **do not work** — they evaluate fields in arbitrary mesh cells rather
than the cells containing the sample points, so their numbers are meaningless. This
is tracked as `MAG-7` and is the project's top priority. Do not cite these tests as
validation until it is fixed.

Planned: closed-form magnitude comparison, commercial-software comparison (Ansys
HFSS), and literature/measured data.

See `docs/status.md` for the per-test breakdown.

## Citation

If you use this software in your research, please cite:

```bibtex
@software{fem_em_solver,
  author = {Awarru},
  title = {FEM Electromagnetics Solver for MRI},
  url = {https://github.com/awarru/fem-em-solver},
  year = {2026}
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [FEniCS Project](https://fenicsproject.org/) for the excellent FEM framework
- [Gmsh](https://gmsh.info/) for mesh generation
- MRI research community for validation data and phantom specifications
