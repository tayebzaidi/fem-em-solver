"""`MAG-6` step 1 probe: is the coil+phantom symmetry metric a boundary-mirror artifact?

PROJECT_PLAN §7 (`MAG-6` step 1) and known-issues 4.  The revised symmetry test
has never executed; its on-record failure is ``max_rel_diff = 0.557`` against a
``0.350`` tolerance, and the known-issues note asks for a boundary-mirror
artifact to be ruled out *before* the tolerance is touched.

This probe is a measurement, not a fix.  It recomputes the test's own metric —
byte-for-byte the same probe grid, the same solve settings, the same
``evaluate_vector_field_parallel`` sampling path — at two air paddings:

* the fixture default ``air_padding = 0.04`` (the known-issues 4 comparison
  point: reproduce 0.557 within ±10% or the fixture has drifted, and *that*
  is the finding), and
* ``1.5 x`` it, ``air_padding = 0.06`` (nothing else moves).

The geometry is mirror-symmetric about the plane ``x = 0`` by construction and
``mu`` is uniform, so the exact metric is **0**: every digit measured is error.
Pre-decided readings (§7):

* metric drops by >= 2x under the padding growth  => boundary-mirror confirmed;
* metric moves by < 20%                            => boundary exonerated, the
  metric/sampling path becomes the suspect;
* in between                                       => mixed, report both.

**Negative control:** an off-centre phantom (asymmetric by construction) must
*increase* the metric.  Directional only — the factor is printed so a review can
size a band from measurement; nothing is asserted on it here.

Stage 1 (``--stage mesh``) meshes the three configurations and prints cell
counts only — the cost probe §7 requires before a tier is committed.
Stage 2 (``--stage solve``) runs the solves.

Run (real build)::

    docker compose exec -T fem-em-solver bash -lc \
      'cd /workspace && PYTHONPATH=/workspace/src mpiexec -n 2 python3 \
       scripts/probes/mag6_step1_probe.py --stage mesh'
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Optional, Tuple

import numpy as np
import ufl
from mpi4py import MPI
from dolfinx import fem

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fem_em_solver.core.solvers import (  # noqa: E402
    MagnetostaticProblem,
    MagnetostaticSolver,
)
from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402
from fem_em_solver.post import evaluate_vector_field_parallel  # noqa: E402
from fem_em_solver.utils.constants import MU_0  # noqa: E402
from tests.tolerances import FIELD_SCALE_FLOOR  # noqa: E402

# Fixture constants, copied from
# tests/validation/test_coil_phantom_bfield_metrics.py so the metric is the
# test's and not a re-derivation.
COIL_MAJOR_RADIUS = 0.08
COIL_MINOR_RADIUS = 0.01
COIL_SEPARATION = 0.08
PHANTOM_RADIUS = 0.04
PHANTOM_HEIGHT = 0.10
RESOLUTION = 0.015
DEFAULT_AIR_PADDING = 0.04
COIL_CURRENT_A = 1.0
GAUGE_PENALTY = 1e-3


def _symmetry_points() -> np.ndarray:
    """The test's ±x probe grid, verbatim (depends on no padding-sensitive term)."""
    sample_clearance = max(0.75 * RESOLUTION, 0.004)
    safe_radius = PHANTOM_RADIUS - sample_clearance
    safe_half_height = (PHANTOM_HEIGHT / 2.0) - sample_clearance

    x_probe_positions = np.array([0.35, 0.60, 0.85], dtype=np.float64) * safe_radius
    z_probe_positions = np.array([-0.60, 0.0, 0.60], dtype=np.float64) * safe_half_height
    y_probe_offset = 0.15 * sample_clearance

    return np.array(
        [
            [sx * x_val, y_probe_offset, z_val]
            for z_val in z_probe_positions
            for x_val in x_probe_positions
            for sx in (1.0, -1.0)
        ],
        dtype=np.float64,
    )


def _mesh(
    air_padding: float,
    phantom_offset_xy: Optional[Tuple[float, float]],
    comm: MPI.Intracomm,
):
    return MeshGenerator.coil_phantom_domain(
        coil_major_radius=COIL_MAJOR_RADIUS,
        coil_minor_radius=COIL_MINOR_RADIUS,
        coil_separation=COIL_SEPARATION,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        air_padding=air_padding,
        resolution=RESOLUTION,
        phantom_placement_preset="centered" if phantom_offset_xy is None else "off_center",
        phantom_offset_xy=phantom_offset_xy,
        comm=comm,
    )


def _global_cell_count(mesh, comm: MPI.Intracomm) -> int:
    local = mesh.topology.index_map(mesh.topology.dim).size_local
    return int(comm.allreduce(local, op=MPI.SUM))


def measure(
    label: str,
    air_padding: float,
    phantom_offset_xy: Optional[Tuple[float, float]],
    comm: MPI.Intracomm,
    solve: bool,
    gauge_penalty: float = GAUGE_PENALTY,
) -> dict:
    """Mesh (and optionally solve) one configuration; return its metrics."""
    t0 = time.time()
    mesh, cell_tags, facet_tags = _mesh(air_padding, phantom_offset_xy, comm)
    mesh_s = time.time() - t0
    cells = _global_cell_count(mesh, comm)

    record = {
        "label": label,
        "gauge_penalty": gauge_penalty,
        "air_padding_m": air_padding,
        "phantom_offset_xy": phantom_offset_xy,
        "cells": cells,
        "mesh_s": mesh_s,
    }
    if not solve:
        return record

    problem = MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, facet_tags=facet_tags, mu=MU_0)
    solver = MagnetostaticSolver(problem, degree=1)

    current_density_magnitude = COIL_CURRENT_A / (np.pi * COIL_MINOR_RADIUS**2)

    def current_density(x):
        return ufl.as_vector([0.0, 0.0, current_density_magnitude])

    t1 = time.time()
    solver.solve(
        current_density=current_density,
        subdomain_ids=[1, 2],
        gauge_penalty=gauge_penalty,
    )
    solve_s = time.time() - t1

    b_field = solver.compute_b_field()
    v_lagrange = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    b_lagrange = fem.Function(v_lagrange, name="B")
    b_lagrange.interpolate(b_field)

    # Rank-invariant handle on the *solution* itself: an assembled integral is
    # a global reduction, so it cannot depend on the partition beyond solver
    # tolerance.  Compared across rank counts this separates "the solve moved"
    # from "only the point-evaluation path moved".
    b_l2_local = fem.assemble_scalar(
        fem.form(ufl.inner(b_lagrange, b_lagrange) * ufl.dx)
    )
    b_l2 = float(np.sqrt(comm.allreduce(b_l2_local, op=MPI.SUM)))

    # Centerline |B| max, the test's absolute scale for the metric.
    centerline_points = np.array(
        [[0.0, 0.0, z] for z in np.linspace(-0.03, 0.03, 9)], dtype=np.float64
    )
    centerline_b, centerline_valid = evaluate_vector_field_parallel(
        b_lagrange, centerline_points, comm=comm
    )
    centerline_mag = np.linalg.norm(centerline_b, axis=1)

    points = _symmetry_points()
    symmetry_b, symmetry_valid = evaluate_vector_field_parallel(b_lagrange, points, comm=comm)

    # Second sampling path, same field, same points.  ``curl A`` for N1curl
    # degree 1 is cell-wise constant, so interpolating it into CG1 asks for a
    # nodal value where the field has a jump; which cell supplies that node is
    # a property of the *partition*, not the physics.  DG0 keeps the cell-wise
    # value, so a metric that is rank-dependent through CG1 and rank-stable
    # through DG0 localises the defect to the interpolation, not the solve.
    v_dg0 = fem.functionspace(mesh, ("DG", 0, (3,)))
    b_dg0 = fem.Function(v_dg0, name="B_dg0")
    b_dg0.interpolate(b_field)
    dg0_b, dg0_valid = evaluate_vector_field_parallel(b_dg0, points, comm=comm)
    dg0_mag = np.linalg.norm(dg0_b, axis=1).reshape(-1, 2)
    dg0_abs = np.abs(dg0_mag[:, 0] - dg0_mag[:, 1])
    dg0_ref = np.maximum(np.maximum(dg0_mag[:, 0], dg0_mag[:, 1]), FIELD_SCALE_FLOOR)
    dg0_rel = dg0_abs / dg0_ref

    b_dg0_l2_local = fem.assemble_scalar(fem.form(ufl.inner(b_dg0, b_dg0) * ufl.dx))
    b_dg0_l2 = float(np.sqrt(comm.allreduce(b_dg0_l2_local, op=MPI.SUM)))

    symmetry_mag = np.linalg.norm(symmetry_b, axis=1).reshape(-1, 2)
    pair_abs_diff = np.abs(symmetry_mag[:, 0] - symmetry_mag[:, 1])
    pair_ref = np.maximum(np.maximum(symmetry_mag[:, 0], symmetry_mag[:, 1]), FIELD_SCALE_FLOOR)
    pair_rel_diff = pair_abs_diff / pair_ref

    record.update(
        {
            "solve_s": solve_s,
            "b_l2": b_l2,
            "b_dg0_l2": b_dg0_l2,
            "dg0_max_rel_diff": float(np.max(dg0_rel)),
            "dg0_mean_rel_diff": float(np.mean(dg0_rel)),
            "dg0_all_valid": bool(dg0_valid.all()),
            "pair_plus": symmetry_mag[:, 0].tolist(),
            "pair_minus": symmetry_mag[:, 1].tolist(),
            "pair_rel_diff": pair_rel_diff.tolist(),
            "centerline_mag": centerline_mag.tolist(),
            "all_valid": bool(centerline_valid.all() and symmetry_valid.all()),
            "n_valid": int(np.count_nonzero(symmetry_valid)),
            "n_points": int(points.shape[0]),
            "b_max_centerline": float(np.max(centerline_mag)),
            "max_rel_diff": float(np.max(pair_rel_diff)),
            "mean_rel_diff": float(np.mean(pair_rel_diff)),
            "max_abs_diff": float(np.max(pair_abs_diff)),
            "mean_abs_diff": float(np.mean(pair_abs_diff)),
        }
    )
    return record


def _report(rec: dict, comm: MPI.Intracomm) -> None:
    if comm.rank != 0:
        return
    print(f"[{rec['label']}] air_padding={rec['air_padding_m']:.4f} m  "
          f"offset={rec['phantom_offset_xy']}  gauge={rec['gauge_penalty']:g}")
    print(f"    cells (global): {rec['cells']}   mesh {rec['mesh_s']:.1f} s")
    if "max_rel_diff" in rec:
        print(f"    solve {rec['solve_s']:.1f} s   "
              f"points valid {rec['n_valid']}/{rec['n_points']} (all_valid={rec['all_valid']})")
        print(f"    |B| max on centerline: {rec['b_max_centerline']:.6e} T")
        print(f"    max_rel_diff  = {rec['max_rel_diff']:.6f}   "
              f"mean_rel_diff = {rec['mean_rel_diff']:.6f}")
        print(f"    max_abs_diff  = {rec['max_abs_diff']:.6e}   "
              f"mean_abs_diff = {rec['mean_abs_diff']:.6e}")
        print(f"    ||B||_L2 (assembled, rank-invariant): {rec['b_l2']:.12e}")
        print(f"    DG0 path: max_rel_diff = {rec['dg0_max_rel_diff']:.6f}  "
              f"mean = {rec['dg0_mean_rel_diff']:.6f}  "
              f"||B_dg0||_L2 = {rec['b_dg0_l2']:.12e}  "
              f"(all_valid={rec['dg0_all_valid']})")
        print("    per-pair |B(+x)| / |B(-x)| / rel:")
        for i, (bp, bm, rd) in enumerate(
            zip(rec["pair_plus"], rec["pair_minus"], rec["pair_rel_diff"])
        ):
            print(f"      pair {i}: {bp:.6e} / {bm:.6e} / {rd:.6f}")
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("mesh", "solve"), default="mesh")
    parser.add_argument(
        "--gauge",
        type=float,
        default=GAUGE_PENALTY,
        help=(
            "gauge penalty for the solve. The test hard-codes 1e-3, which is "
            "1000x below the validated floor DEFAULT_GAUGE_PENALTY = 1.0 and "
            "raises GaugeContaminationWarning (MAG-10: 920%% field error at "
            "1e-3, degree 2). Pass 1.0 to ask whether the gauge owns the metric."
        ),
    )
    args = parser.parse_args()
    solve = args.stage == "solve"

    comm = MPI.COMM_WORLD
    if comm.rank == 0:
        print(f"MAG-6 step 1 probe — stage={args.stage}, ranks={comm.size}, "
              f"gauge_penalty={args.gauge:g}")
        print("mirror plane x = 0; exact metric is 0 by construction (uniform mu,")
        print("symmetric coils, centred phantom) — every digit below is error.")
        sys.stdout.flush()

    configs = [
        ("default", DEFAULT_AIR_PADDING, None),
        ("padding-1.5x", 1.5 * DEFAULT_AIR_PADDING, None),
        ("offset-control", DEFAULT_AIR_PADDING, (0.35 * PHANTOM_RADIUS, 0.0)),
    ]

    records = {}
    for label, padding, offset in configs:
        rec = measure(label, padding, offset, comm, solve, gauge_penalty=args.gauge)
        records[label] = rec
        _report(rec, comm)

    if solve and comm.rank == 0:
        base = records["default"]["max_rel_diff"]
        grown = records["padding-1.5x"]["max_rel_diff"]
        control = records["offset-control"]["max_rel_diff"]
        print("")
        print("MAG-6 step 1 readings")
        print(f"  known-issues 4 on record : 0.557 at default padding")
        print(f"  reproduced               : {base:.6f}  "
              f"(ratio to record {base / 0.557:.4f}; band 0.9-1.1)")
        print(f"  padding 1.5x             : {grown:.6f}")
        drop = base / grown if grown > 0.0 else float("inf")
        move = abs(grown - base) / base if base > 0.0 else float("inf")
        print(f"  drop factor base/grown   : {drop:.4f}   (>= 2 => boundary-mirror confirmed)")
        print(f"  relative move            : {move * 100:.2f}%  (< 20% => boundary exonerated)")
        if drop >= 2.0:
            band = "(mirror confirmed) boundary owns it"
        elif move < 0.20:
            band = "(mirror exonerated) suspect the metric/sampling path"
        else:
            band = "(mixed) report both values"
        print(f"  band                     : {band}")
        print(f"  offset-phantom control   : {control:.6f}  "
              f"(factor vs default {control / base:.4f}; must be > 1, directional only)")
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
