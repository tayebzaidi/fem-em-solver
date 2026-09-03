# FEM Electromagnetics Solver

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FEniCSX](https://img.shields.io/badge/FEniCSX-0.11-green.svg)](https://fenicsproject.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A FEniCSX/DolfinX finite-element toolkit for the MRI RF-safety workflow:
parametric birdcage coils and gelled-saline phantoms, complex frequency-domain
solves, lumped ports, B1+ maps, SAR, and S-parameters. The intended scope is
this MRI workflow—not general-purpose HFSS parity. Implant hot spots, coil
tuning/circuit co-simulation, and Pennes bioheat are later phases.

> **Status: alpha research software.** Several solver components have strong
> analytic or identity-based validation, but the complete safety workflow is
> not validated. Do not use its output for safety decisions. Read the
> [current dashboard](docs/status/dashboard.md) before interpreting results;
> [PROJECT_PLAN.md](PROJECT_PLAN.md) is the authoritative technical record.

## What is validated

- Magnetostatics against closed-form Helmholtz, circular-loop, and
  straight-wire results.
- The complex curl-curl formulation against manufactured and analytic
  time-harmonic problems, including lossy media and Larmor-frequency sphere
  cases.
- Coil loading against Dodd–Deeds in the 10 MHz eddy-current regime.
- SAR machinery against a lossy sphere under an imposed field.
- Field-derived ports and S-parameter self-consistency on two-loop and loaded
  birdcage fixtures.
- Loaded-birdcage B1+ symmetry and limited coil-driven SAR symmetry identities.

Important limitations remain: Larmor-frequency coil-loading accuracy is not
established; birdcage B1+ and SAR do not yet have absolute or convergence
validation; tuning, implant, and thermal workflows are incomplete. Exact
numbers and qualifications live in [the dashboard](docs/status/dashboard.md).

## Supported environment

The reproducible environment is the repository image based on DolfinX 0.11:

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml ps
```

The source tree is mounted at `/workspace`, so rebuilding is necessary only
when the image or dependencies change. Frequency-domain solves require the
complex DolfinX build; repository runners select it automatically.

## Run tests

For a quick, non-FEM feedback pass:

```bash
./run_tests.sh --smoke
```

Full verification is split into bounded validation groups because FEM jobs are
computationally expensive. The supported commands run in Docker through
`scripts/testing/run_and_log.sh`; see [CONTRIBUTING.md](CONTRIBUTING.md) for the
workflow and [the CI configuration](.github/workflows/ci.yml) for the suite
matrix.

## Run examples

```bash
./run_examples.sh --list
./run_examples.sh --example 1          # straight-wire magnetostatics
./run_examples.sh --example th:1       # analytic lossy plane wave
./run_examples.sh --example ports:4    # four-port birdcage S-matrix
./run_examples.sh --example ports:8    # B1+ at 64/128 MHz
```

Examples produce visualization artifacts for ParaView. Use `--list` as the
authoritative catalogue; it includes expected runtimes and MPI options.

## Repository layout

```text
src/fem_em_solver/
  core/       FEM formulations and linear solves
  io/         Gmsh geometry, mesh QA, and output
  materials/  Electromagnetic tissue/phantom models
  ports/      Gap-voltage and lumped-sheet ports, sweeps, Touchstone
  post/       Field evaluation, power balance, B1+, and SAR
  utils/      Constants and analytic reference models
tests/        Unit, solver, mesh, integration, and validation checks
examples/     Runnable cases and private-safe Ansys benchmark specifications
docs/         Status, validation notes, plans, and indexed test evidence
```

The public API is still evolving. Use the runnable examples as the API guide;
the package is not yet promising backward compatibility.

## Project navigation

- [Current status dashboard](docs/status/dashboard.md) — concise operational
  and capability snapshot
- [Project plan](PROJECT_PLAN.md) — authoritative claims, backlog, and
  sequencing
- [Known issues](docs/testing/known-issues.md) — deliberate and diagnosed test
  failures
- [Contributing](CONTRIBUTING.md) — environment and verification rules
- [Documentation index](docs/index.md) — validation and test-result links

## License and citation

The project is available under the [MIT License](LICENSE).

```bibtex
@software{fem_em_solver,
  author = {Awarru},
  title = {FEM Electromagnetics Solver for MRI},
  url = {https://github.com/awarru/fem-em-solver},
  year = {2026}
}
```
