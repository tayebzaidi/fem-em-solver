# FEM Electromagnetics Solver

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FEniCSX](https://img.shields.io/badge/FEniCSX-0.7+-green.svg)](https://fenicsproject.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A finite element method (FEM) toolkit, built on
[FEniCSX/DolfinX](https://fenicsproject.org/), targeting the **MRI RF safety**
slice of what Ansys Electronics Desktop does (HFSS + circuit solver first,
Pennes bioheat thermal long-term): construct birdcage coil + gelled saline
phantom simulations (often with implants), tune the coil at 64 MHz (1.5 T) and
128 MHz (3 T), and extract the safety quantities — B1+ maps, SAR including
near-implant hot spots, and port S-parameters. The scope is deliberately that
workflow, not general-purpose HFSS parity.

> **Project status: alpha.** Magnetostatics is validated against closed forms.
> The time-harmonic path is a real complex curl-curl solve, validated against
> analytic solutions (lossy plane wave, waveguide cutoff, dielectric sphere,
> cavity resonances) and against Dodd–Deeds coil loading in the eddy-current
> regime. S-parameters from the packaged sweep path are still a placeholder;
> the first solved-field S-matrix exists on a two-loop validation fixture.
> See [PROJECT_PLAN.md](PROJECT_PLAN.md) §2 for the honest current state
> before relying on any figure.

## Features

**Working today**
- **Magnetostatics**: vector potential formulation, N1curl elements, validated against closed forms
- **Time-harmonic Maxwell**: complex curl-curl solve with lossy materials (`ε_c = εᵣ − jσ/ωε₀`), validated against analytic solutions
- **Meshing**: parametric Gmsh geometry (two-loop, coil+phantom, birdcage with port regions) with conformity identities gated in CI
- **Materials**: gelled saline phantom properties measurably drive the solved field (gated)
- **SAR**: mean and mass-averaged SAR, gated against the lossy-sphere closed form
- **Post-processing**: Poynting power balance, current-divergence residual, phasor-correct phantom field metrics, combined XDMF for ParaView

**In progress / planned** (see [PROJECT_PLAN.md](PROJECT_PLAN.md) §6 and §10)
- **Ports & S-parameters**: gap-voltage lumped ports from the solved field (`PORT-1`)
- **Birdcage tuning**: mode spectrum, lumped capacitors, circuit co-simulation at 64/128 MHz
- **Implants**: parametric implant geometry, local SAR / hot spots
- **Thermal**: Pennes bioheat driven by SAR
- **Ansys cross-validation**: benchmark cases under `examples/ansys_benchmarks/` specified for direct replication in Ansys Electronics Desktop, with returned numbers promoted into gates

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

# Run one magnetostatics example by number
./run_examples.sh --example 1

# Run multiple examples and set MPI ranks
./run_examples.sh --example 1,3 --nproc 4

# Run the MRI coil+phantom example (complex DolfinX build, sourced automatically)
./run_examples.sh --example mri:1

# Run the meshing/tagging example — no solve; asserts the GEO-8/GEO-10 identities
# and exports cell + facet tags for ParaView
./run_examples.sh --example mesh:1

# Run all magnetostatics examples / absolutely everything
./run_examples.sh --example all-mag
./run_examples.sh --example all --nproc 2
```

The script automatically targets `docker/docker-compose.yml` and runs each selected example as:
`docker compose exec fem-em-solver ... timeout <s> mpiexec -n <nproc> python3 <example>`
(MRI examples are prefixed with `source /usr/local/bin/dolfinx-complex-mode`).

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
