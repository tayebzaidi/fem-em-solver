#!/usr/bin/env python3
"""Measured h-convergence rate of the straight-wire solve (`EX-9`).

Every other magnetostatics example reports an *error* at one mesh. That number
alone cannot distinguish a discretization that is converging from one that has
hit a modeling floor and will never improve — for that you need the error at
several resolutions and the slope through them. This example produces that
slope, which is the quantity no other example outputs:

* three meshes at h = 4.0 / 2.5 / 1.8 mm, each solved with the analytic
  vector potential imposed on the outer wall (`MAG-13`, ``exterior_dirichlet_bc``
  — with the natural condition the sequence has no rate to fit, see the
  fixture's docstring);
* ``|B|`` sampled on the same ten-point line each time and compared to the
  closed-form straight-wire field;
* the rate fitted as the least-squares slope of ``log(error)`` against
  ``log(h)`` — three points, because two points fit any slope exactly and a
  two-resolution "rate" is not a measurement.

**It asserts, it does not merely render.** The fixture is *imported* from the
module that closed `MAG-13` (``tests/validation/test_convergence.py``:
parameters, per-resolution solve, sample line and the rate fit itself), never
restated, and the anchor is the gate's own:

* **Anchor** — the sampled errors decay **monotonically** across the sequence
  (``test_h_refinement_straight_wire``, imported gate). Until 2026-08-25 the
  anchor here was the fitted rate inside ``0.7 < rate < 1.5`` (**1.10** on
  record in ``20260730T125522Z_MAG-13.log``, over errors 22.19% -> 12.75% ->
  9.26%); `MAG-19` ruling (i) retired that band on this statistic — it swings
  34% under its own sample count — and moved the rate duty to `MAG-18`'s
  sampler-free ``E_Omega`` ladder, which gates ``rate >= 0.7`` one-sided and is
  green on 0.11 at 1.6854. This example follows the gate it imports: the rate
  and the retired band are still **printed**, and this file re-states neither
  (`ANS-1`). The band is not widened here or anywhere.
* **Negative control, and it is solved here rather than cited** — a discretization
  blind to h shows no systematic decay, so the three errors are asserted to
  decrease **monotonically**, coarse to fine. A run that produced the right
  average slope from a non-monotone sequence would fail this and should: the
  sequence was chosen (`MAG-13`) precisely because h = 0.0035 is non-monotone
  against h = 0.0025 and had to be excluded.
* *What the export costs, measured rather than assumed* — the finest solve is
  written to XDMF as CG1, and its error is re-measured **on the exported
  function**: 17.1452% against the solved field's 9.2568% (first run). curl(A)
  is cell-wise constant for N1curl degree 1, so writing it to a continuous
  space averages at the vertices, and on a 1/r field near a conductor that
  costs 7.89 percentage points — most of what the refinement sequence bought.
  The picture is not the measurement; the example says so with a number and
  bounds it by the coarsest solved resolution.

**Does not close anything.** `MAG-13` closed 2026-07-30; this is Phase-1 §5.4
example backfill.

Real build only — magnetostatics is a real-valued solve; do not source the
complex mode for it. **Cost: heavy tier** (§5.1 names convergence studies
explicitly, and `MAG-13` is labeled heavy: ~140 s of solve at ``-n 2``, plus
meshing and one export). Do not add a fourth resolution.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from dolfinx import fem
from mpi4py import MPI

# The `MAG-13` fixture is imported rather than restated (§7 `EX-9` plan). The
# runner puts only ``src`` on PYTHONPATH, so the repo root goes on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    write_combined_paraview_output,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel  # noqa: E402
from fem_em_solver.utils.analytical import (  # noqa: E402
    AnalyticalSolutions,
    ErrorMetrics,
)
from tests.validation.test_convergence import (  # noqa: E402
    CURRENT,
    RATE_DUTY_OWNER,
    RATE_MAX,
    RATE_MIN,
    RESOLUTIONS,
    evaluation_points,
    fit_convergence_rate,
    solve_h_refinement,
)

# The (h, error) triple measured when `MAG-13` closed
# (20260730T125522Z_MAG-13.log). Printed alongside this run for comparison and
# deliberately **not** asserted on: the gate's assertion is the rate band, and
# pinning individual errors here would invent a bound `MAG-13` never gated.
ON_RECORD_ERRORS = [0.2219, 0.1275, 0.0926]
ON_RECORD_RATE = 1.10

# Export check. The first run of this example (20260810T123503Z_EX-9-run1.log)
# measured the error of the *exported* CG1 field at the same ten points as
# **17.1452%**, against **9.2568%** for the solved N1curl field it was
# interpolated from -- a 7.89-point shift, not the fraction of a point an
# "interpolation is lossless enough" assumption would predict. curl(A) is
# cell-wise constant for N1curl degree 1, so writing it to a continuous CG1
# space averages neighbouring cells at each vertex, and that averaging smooths
# the 1/r variation the probe line sits in. The number is a property of the
# export, and it is reported rather than hidden.
#
# So the bound below is NOT "the exported error equals the solved error" --
# measurement says it does not. It is the run's own coarsest resolution: the
# exported picture must still be no worse than the h = 0.004 solve, or the
# smoothing has cost more than 2.2x of mesh refinement bought and the field
# ParaView shows misrepresents the sequence this example is about. Measured
# 17.1452% against 22.1925% on the first run. Nothing here is inherited --
# MAG-13 gates no export -- and nothing here is asserted about physics.
EXPORT_ERROR_REFERENCE = "coarsest solved resolution"

OUTPUT_DIR = "paraview_output"
BASENAME = "h_convergence_rate"


def main() -> None:
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0
    t_start = time.time()

    if rank0:
        print("=" * 74)
        print("h-convergence rate of the straight-wire magnetostatic solve")
        print("=" * 74)
        print("  fixture        : tests/validation/test_convergence.py (MAG-13)")
        print(f"  current        : {CURRENT:.3f} A")
        print(f"  resolutions h  : {RESOLUTIONS} m")
        print(f"  sample points  : {len(evaluation_points())} along +x at z = 0")
        print(f"  MPI ranks      : {comm.size}")
        print(flush=True)

    errors = []
    n_cells = []
    finest = None
    for res in RESOLUTIONS:
        t0 = time.time()
        result = solve_h_refinement(res, comm)
        dt = time.time() - t0
        errors.append(result["rel_error"])
        n_cells.append(result["n_cells"])
        if rank0:
            print(
                f"  h = {res:<7.4f} {result['n_cells']:>8d} cells   "
                f"rel L2 error = {result['rel_error']:>8.4%}   ({dt:.1f} s)",
                flush=True,
            )
        # Only the finest solve is kept for export; holding all three meshes
        # would triple the peak memory for no gain.
        finest = result

    rate = fit_convergence_rate(RESOLUTIONS, errors)

    # ---- export the finest solve --------------------------------------------
    # Only the numeric field is written. The closed form the gate compares
    # against is the *exterior* wire field, valid for r > a; interpolating it
    # over the whole domain would put a 1/r singularity on the axis and an
    # invalid comparison inside the conductor, i.e. a picture whose most
    # colourful region is the one the measurement deliberately excludes. The
    # gate samples at r >= 2a for the same reason.
    mesh = finest["mesh"]
    v_cg = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    b_num_cg = fem.Function(v_cg, name="B_numeric")
    b_num_cg.interpolate(finest["b_field"])

    written_files = write_combined_paraview_output(
        OUTPUT_DIR,
        BASENAME,
        mesh,
        finest["cell_tags"],
        {"B_numeric": (b_num_cg, b_num_cg)},
        comm=comm,
    )

    # The exported field is the asserted field: re-measure the finest-mesh
    # error from the exact CG1 function handed to the writer. This catches a
    # stale or mis-interpolated export -- the N1curl solution and its CG1
    # interpolant are not identical (cell-wise constant curl(A) is averaged to
    # the vertices), so the two errors differ by the interpolation, not by a
    # solve.
    points = evaluation_points()
    b_export, valid_export = evaluate_vector_field_parallel(
        b_num_cg, points, comm=comm
    )
    assert valid_export.all(), (
        f"{(~valid_export).sum()}/{len(points)} sample points fell outside the "
        "exported mesh"
    )
    b_analytic_mag = np.linalg.norm(
        AnalyticalSolutions.straight_wire_magnetic_field(points, CURRENT), axis=1
    )
    export_error = ErrorMetrics.l2_relative_error(
        np.linalg.norm(b_export, axis=1), b_analytic_mag
    )

    if rank0:
        print()
        print("-" * 74)
        print("Convergence table")
        print("-" * 74)
        print(
            f"{'h (m)':>9} {'cells':>10} {'rel L2 error':>14} "
            f"{'MAG-13 record':>15} {'log h':>9} {'log err':>9}"
        )
        for i, h in enumerate(RESOLUTIONS):
            print(
                f"{h:>9.4f} {n_cells[i]:>10d} {errors[i]:>13.4%} "
                f"{ON_RECORD_ERRORS[i]:>14.2%} "
                f"{np.log(h):>9.4f} {np.log(errors[i]):>9.4f}"
            )
        print()
        print(
            f"  fitted rate  : {rate:.4f}   "
            f"(report only since MAG-19; retired band {RATE_MIN} < p < "
            f"{RATE_MAX}, {ON_RECORD_RATE:.2f} on record)"
        )
        print(f"  rate duty    : {RATE_DUTY_OWNER}")
        print(
            f"  error decay  : {errors[0]:.4%} -> {errors[-1]:.4%} "
            f"over a {RESOLUTIONS[0] / RESOLUTIONS[-1]:.2f}x refinement"
        )
        print(
            f"  exported fld : {export_error:.4%} at the same points "
            f"(solved field {errors[-1]:.4%}, CG1 smoothing costs "
            f"{export_error - errors[-1]:+.4%}; must stay under the "
            f"{EXPORT_ERROR_REFERENCE} {errors[0]:.4%})"
        )
        print(flush=True)

    # ---- anchor: the monotone decay the imported gate now asserts ------------
    # MAG-19 ruling (i), 2026-08-25 18:00 review: the fitted-rate assertion that
    # stood here --
    #   assert RATE_MIN < rate < RATE_MAX, "... outside the MAG-13 band ..."
    # -- retired with the band itself, because the sampled statistic it fits
    # swings 34% under its own sample count (OPS-18 step 3 attempt 5) and the
    # ladder's pairwise rates are out of band on both ends on 0.11 (MAG-19
    # step 1, 20260825T183555Z_MAG-19-step1-dualnorm-fits.log). The rate duty is
    # MAG-18's E_Omega ladder; this example asserts what its imported gate
    # asserts, which is the monotone decay checked below. Licensed alignment
    # under that ruling, not a loosening: no band moved anywhere, and this file
    # continues to restate nothing (ANS-1).
    assert export_error < errors[0], (
        f"the exported CG1 field's error {export_error:.4%} is worse than the "
        f"coarsest solved resolution's {errors[0]:.4%} (h = {RESOLUTIONS[0]}): "
        "vertex averaging has cost more than the whole refinement sequence "
        "bought, so what ParaView shows misrepresents the convergence this "
        "example measures"
    )

    # ---- anchor (MAG-19) / negative control: the decay is systematic --------
    # This assertion is unchanged; what changed is its standing. It was the
    # negative control under the retired rate band -- "the right average slope
    # from a non-monotone sequence would fail this" -- and it is now also the
    # anchor, the same one test_h_refinement_straight_wire keeps.
    for i in range(1, len(errors)):
        assert errors[i] < errors[i - 1], (
            f"error rose from {errors[i - 1]:.4%} at h = {RESOLUTIONS[i - 1]} to "
            f"{errors[i]:.4%} at h = {RESOLUTIONS[i]}: the sequence is not "
            "monotone, so the fitted slope is not measuring convergence"
        )

    if rank0:
        print("=" * 74)
        print("ParaView output (finest mesh, h = %.4f m)" % RESOLUTIONS[-1])
        print("=" * 74)
        for name, path in sorted(written_files.items()):
            print(f"  {name:>14}: {path}")
        print()
        print("  Open h_convergence_rate_combined.xdmf: it carries the mesh, the")
        print("  'CellTags' array (1 = wire, 2 = air) and the computed B field")
        print("  at the finest resolution. The closed form is deliberately not")
        print("  written beside it: valid only for r > a, it would put a 1/r")
        print("  singularity on the axis and an invalid comparison inside the")
        print("  conductor. The rate above is the output of this example; the")
        print("  field is what it was fitted from, one resolution of three.")
        print()
        print(
            f"All assertions hold. Total elapsed {time.time() - t_start:.1f} s "
            f"({comm.size} ranks, {n_cells[-1]} cells at the finest h)."
        )


if __name__ == "__main__":
    main()
