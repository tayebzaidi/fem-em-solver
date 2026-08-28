#!/usr/bin/env python3
"""Gauge cross-check: the penalty and Lagrange-multiplier Coulomb gauges (`EX-10`).

The curl-curl operator of magnetostatics has a gradient null space. Two ways of
removing it are implemented, and this example runs **both on one mesh** and asks
whether they produce the same physics:

* ``GaugeMethod.PENALTY`` — the default: a ``gauge * (div A, div v)`` term prices
  the null space instead of removing it, so ``A`` keeps a gradient component of
  magnitude ~1/gauge and ``B = curl(A)`` is recovered by cancellation.
* ``GaugeMethod.LAGRANGE`` — the (A, p) saddle point in N1curl x H1, which
  enforces ``div A = 0`` weakly and *removes* the null space.

The angle no other example covers: **formulation cross-validation**. Every other
magnetostatics example compares one formulation against a closed form; this one
compares two formulations against each other, which is the check that catches a
gauge-treatment defect a closed form would absorb into its modeling floor.

**It asserts, it does not merely render.** The fixture is *imported* from the
module that closed `MAG-15` (``tests/solver/test_gauge_lagrange.py``: geometry,
resolution and the same eight sample points), never restated, and the anchors are
the gate's own:

* **Anchor** — ``ErrorMetrics.l2_relative_error(b_lag, b_pen)`` under the gate's
  **5%** ceiling (``test_penalty_and_lagrange_agree_on_b_field``; on record in
  ``20260728T193524Z_MAG-15.log`` the two gauges give an identical analytic error
  to 4 significant figures at h = 0.003 — the rel-diff scalar itself is not
  printed in that log, so the number this example prints becomes the record).
* **Negative control, and it is not the same computation** — ``max|A|`` for the
  Lagrange solve must sit below ``1e-6`` times the penalty's
  (``test_lagrange_removes_null_space_component``; 1.6e-09 vs 5.2e+01 on record,
  eleven orders). The two paths agreeing on ``B`` while disagreeing on ``A`` by
  orders of magnitude is the whole point: they are genuinely different solves,
  so their agreement on the physical field carries information.
* *The exported field is the asserted field* — the probe-point agreement is
  re-measured as a **volume integral** over the whole air region,
  ``sqrt(int |B_lag - B_pen|^2 dx / int |B_pen|^2 dx)``, on the exact CG1
  functions written to XDMF. Eight probe points on one line agreeing says little
  about what ParaView colours; the field-wide norm does.

**Does not close anything.** `MAG-15` closed 2026-07-28; this is Phase-1 §5.4
example backfill.

Real build only — magnetostatics is a real-valued solve; do not source the
complex mode for it. Cost: two solves on a deliberately coarse h = 0.006 mesh,
a few seconds each at ``-n 2`` (the seven-test `MAG-15` gate costs 13 s).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from dolfinx import fem
from mpi4py import MPI

# The `MAG-15` fixture is imported rather than restated (§7 `EX-10` plan). The
# runner puts only ``src`` on PYTHONPATH, so the repo root goes on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.core.solvers import (  # noqa: E402
    GaugeMethod,
    MagnetostaticProblem,
    MagnetostaticSolver,
)
from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    write_combined_paraview_output,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel  # noqa: E402
from fem_em_solver.utils.analytical import ErrorMetrics  # noqa: E402
from fem_em_solver.utils.constants import MU_0  # noqa: E402
from tests.solver.test_gauge_lagrange import (  # noqa: E402
    _POINTS as SAMPLE_POINTS,
    DOMAIN_RADIUS,
    RESOLUTION,
    WIRE_LENGTH,
    WIRE_RADIUS,
)

# The gate's own ceiling (test_penalty_and_lagrange_agree_on_b_field). Tolerances
# here cite the gate they come from and may be looser, never tighter — this one
# is equal.
AGREEMENT_RTOL = 0.05

# The gate's null-space bound (test_lagrange_removes_null_space_component):
# max|A|_lagrange < 1e-6 * max|A|_penalty. On record 1.6e-09 vs 5.2e+01.
NULLSPACE_RATIO_MAX = 1e-6

# Field-wide check on the *exported* functions. Not a gated bound — there is no
# `MAG-15` assertion on a volume norm — so it is set from the probe anchor it
# corroborates: the same 5%. If the two disagree it means the eight probe points
# are unrepresentative of what ParaView shows, which is a finding either way.
VOLUME_AGREEMENT_RTOL = 0.05

OUTPUT_DIR = "paraview_output"
BASENAME = "magnetostatics_05_gauge_cross_check"


def solve_with(gauge, mesh, cell_tags, current_density, comm):
    """One magnetostatic solve on the shared mesh; returns diagnostics + fields."""
    t0 = time.time()
    solver = MagnetostaticSolver(
        MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0), degree=1
    )
    a_field = solver.solve(
        current_density=current_density, subdomain_id=1, gauge=gauge
    )
    b_field = solver.compute_b_field()
    t_solve = time.time() - t0

    # max|A| is rank-local until reduced.
    local_max = float(np.max(np.abs(a_field.x.array))) if a_field.x.array.size else 0.0
    max_a = comm.allreduce(local_max, op=MPI.MAX)

    b_vals, valid = evaluate_vector_field_parallel(b_field, SAMPLE_POINTS, comm=comm)

    return {
        "a": a_field,
        "b": b_field,
        "b_probe": b_vals,
        "valid": valid,
        "max_a": max_a,
        "multiplier_spread": solver.gauge_multiplier_spread(),
        "t_solve": t_solve,
    }


def main() -> None:
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0
    t_start = time.time()

    if rank0:
        print("=" * 74)
        print("Gauge cross-check: penalty vs Lagrange-multiplier Coulomb gauge")
        print("=" * 74)
        print("  fixture        : tests/solver/test_gauge_lagrange.py (MAG-15)")
        print(f"  wire radius    : {WIRE_RADIUS:.4f} m")
        print(f"  domain radius  : {DOMAIN_RADIUS:.4f} m")
        print(f"  wire length    : {WIRE_LENGTH:.4f} m")
        print(f"  resolution h   : {RESOLUTION:.4f} m")
        print(f"  MPI ranks      : {comm.size}")
        print(flush=True)

    t0 = time.time()
    mesh, cell_tags, _ = MeshGenerator.straight_wire_domain(
        wire_length=WIRE_LENGTH,
        wire_radius=WIRE_RADIUS,
        domain_radius=DOMAIN_RADIUS,
        resolution=RESOLUTION,
        comm=comm,
    )
    t_mesh = time.time() - t0
    n_cells = mesh.topology.index_map(mesh.topology.dim).size_global

    # Unit total current spread over the wire cross-section, as in the fixture.
    j = 1.0 / (np.pi * WIRE_RADIUS**2)

    def current_density(x):
        return ufl.as_vector([0.0, 0.0, j])

    if rank0:
        print(f"mesh: {n_cells} cells in {t_mesh:.1f} s", flush=True)

    results = {}
    for gauge in (GaugeMethod.PENALTY, GaugeMethod.LAGRANGE):
        results[gauge] = solve_with(
            gauge, mesh, cell_tags, current_density, comm
        )
        if rank0:
            r = results[gauge]
            print(
                f"  {gauge.value:<9} solve {r['t_solve']:.1f} s   "
                f"max|A| = {r['max_a']:.3e}   "
                f"multiplier spread = {r['multiplier_spread']:.3e}",
                flush=True,
            )

    pen = results[GaugeMethod.PENALTY]
    lag = results[GaugeMethod.LAGRANGE]

    for gauge, r in results.items():
        assert r["valid"].all(), (
            f"{gauge.value}: {(~r['valid']).sum()}/{len(SAMPLE_POINTS)} sample "
            "points fell outside the mesh"
        )

    # ---- anchor: the two gauges agree on B ----------------------------------
    rel_diff = ErrorMetrics.l2_relative_error(lag["b_probe"], pen["b_probe"])

    # ---- export, then re-measure agreement on what was exported -------------
    v_lag = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    a_pen_cg = fem.Function(v_lag, name="A_penalty")
    a_pen_cg.interpolate(pen["a"])
    a_lag_cg = fem.Function(v_lag, name="A_lagrange")
    a_lag_cg.interpolate(lag["a"])
    b_pen_cg = fem.Function(v_lag, name="B_penalty")
    b_pen_cg.interpolate(pen["b"])
    b_lag_cg = fem.Function(v_lag, name="B_lagrange")
    b_lag_cg.interpolate(lag["b"])
    b_diff_cg = fem.Function(v_lag, name="B_difference")
    b_diff_cg.x.array[:] = b_lag_cg.x.array - b_pen_cg.x.array
    b_diff_cg.x.scatter_forward()

    written_files = write_combined_paraview_output(
        OUTPUT_DIR,
        BASENAME,
        mesh,
        cell_tags,
        {
            "A_penalty": (a_pen_cg, a_pen_cg),
            "A_lagrange": (a_lag_cg, a_lag_cg),
            "B_penalty": (b_pen_cg, b_pen_cg),
            "B_lagrange": (b_lag_cg, b_lag_cg),
            "B_difference": (b_diff_cg, b_diff_cg),
        },
        comm=comm,
    )

    # assemble_scalar is rank-local; reduce both integrals before dividing.
    dx = ufl.dx(domain=mesh)
    num_local = fem.assemble_scalar(
        fem.form(ufl.inner(b_diff_cg, b_diff_cg) * dx)
    )
    den_local = fem.assemble_scalar(
        fem.form(ufl.inner(b_pen_cg, b_pen_cg) * dx)
    )
    num = comm.allreduce(float(num_local), op=MPI.SUM)
    den = comm.allreduce(float(den_local), op=MPI.SUM)
    volume_rel_diff = float(np.sqrt(num / den))

    ratio = lag["max_a"] / pen["max_a"] if pen["max_a"] > 0.0 else float("inf")

    if rank0:
        print()
        print("-" * 74)
        print("Probe-point comparison (8 points, 2a <= x <= 0.4 R_domain)")
        print("-" * 74)
        print(f"{'x (m)':>10} {'|B| penalty (T)':>18} {'|B| Lagrange (T)':>18} {'rel diff':>10}")
        b_pen_mag = np.linalg.norm(pen["b_probe"], axis=1)
        b_lag_mag = np.linalg.norm(lag["b_probe"], axis=1)
        for i in range(len(SAMPLE_POINTS)):
            d = (
                abs(b_lag_mag[i] - b_pen_mag[i]) / b_pen_mag[i]
                if b_pen_mag[i] > 0.0
                else float("nan")
            )
            print(
                f"{SAMPLE_POINTS[i, 0]:>10.5f} {b_pen_mag[i]:>18.6e} "
                f"{b_lag_mag[i]:>18.6e} {d:>9.3%}"
            )
        print()
        print(f"  vector L2 rel diff (probe) : {rel_diff:.4%}  "
              f"(ceiling {AGREEMENT_RTOL:.0%}, MAG-15 gate)")
        print(f"  volume L2 rel diff (export): {volume_rel_diff:.4%}  "
              f"(ceiling {VOLUME_AGREEMENT_RTOL:.0%})")
        print(f"  max|A| Lagrange / penalty  : {ratio:.3e}  "
              f"(ceiling {NULLSPACE_RATIO_MAX:.0e}, MAG-15 gate)")
        print(flush=True)

    assert rel_diff < AGREEMENT_RTOL, (
        f"penalty and Lagrange B fields disagree by {rel_diff:.2%} at the probe "
        f"points, over the MAG-15 gate's {AGREEMENT_RTOL:.0%} ceiling"
    )
    assert volume_rel_diff < VOLUME_AGREEMENT_RTOL, (
        f"the exported B fields disagree by {volume_rel_diff:.2%} in the volume "
        f"L2 norm, over the {VOLUME_AGREEMENT_RTOL:.0%} ceiling — what ParaView "
        "shows is not what the probe anchor measured"
    )
    assert pen["max_a"] > 0.0, "penalty solve produced an identically zero A"
    assert ratio < NULLSPACE_RATIO_MAX, (
        f"Lagrange max|A| = {lag['max_a']:.3e} is not far below the penalty's "
        f"{pen['max_a']:.3e} (ratio {ratio:.3e}); the null space was not removed, "
        "so the two solves are not independent and their agreement proves nothing"
    )
    # The penalty path has no multiplier: the diagnostic must say so rather than
    # return a number (MAG-15's third test).
    assert np.isnan(pen["multiplier_spread"]), (
        "penalty solve reported a multiplier spread; the diagnostic is not "
        "distinguishing the two formulations"
    )
    assert np.isfinite(lag["multiplier_spread"]), (
        "Lagrange multiplier spread is not finite"
    )

    if rank0:
        print("=" * 74)
        print("ParaView output")
        print("=" * 74)
        for name, path in sorted(written_files.items()):
            print(f"  {name:>14}: {path}")
        print()
        print("  Open magnetostatics_05_gauge_cross_check_combined.xdmf: it carries the mesh, the")
        print("  'CellTags' array (1 = wire, 2 = air), both A fields, both B")
        print("  fields, and their difference on one grid. A_penalty and")
        print("  A_lagrange look nothing alike; B_penalty and B_lagrange do, and")
        print("  B_difference is the residue between them.")
        print()
        print(
            f"All assertions hold. Total elapsed {time.time() - t_start:.1f} s "
            f"({comm.size} ranks, {n_cells} cells)."
        )


if __name__ == "__main__":
    main()
