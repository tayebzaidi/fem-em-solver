"""`MAG-13` step 2c: a third rung for the CG1 recovery rate.

Step 2b priced continuous recovery on the solved rung and read a **two-point**
convergence rate off its own two logs: CG1 relL2 over the recorded metric span
went 7.8411% (h = 0.0025) -> 1.9557% (h = 0.00125), a ratio of 4.01, i.e.
p = 2.00, where the DG1 interpolation over the same pair read 10.9806% ->
4.7235% (ratio 2.32, p = 1.22).  Two points is a rate with no redundancy.  The
2026-08-12 18:00 review deferred the gate-adoption call pending a third point
and commissioned this step (§9 item 3).

This probe adds **one intermediate rung at h = 0.0017678** (√2 between the
recorded rungs), runs both recoveries on the recorded 45-radius grid, and
prints the three-point rates beside the two-point observations.  Every piece of
machinery — the solve, the CG1 L2 projection, the sampler, the band table —
is imported from ``mag13_step2b_recovery`` rather than restated, so a drift
between the two steps is impossible by construction.

Order of operations, deliberately:

1. **Identity first.**  The exit code of the *smoke* run is driven by
   reproducing the smoke rung's own recorded numbers (145 884 cells, DG1 span
   10.9806%, CG1 span 7.8411%) to their printed digits.  That run is this
   step's fixture identity: it proves the imported machinery still produces the
   record before any new rung is believed.  The 1 097 873-cell rung is **cited
   from record, never re-solved** (271 s of solve this step does not need).
2. **The new rung** is then a measurement, gated only on the negative control
   below — its error levels are the reading and are not gated.

Gates, by run mode (the exit code is gated on these, and on nothing else):

* **Smoke rung** (``MAG13_STEP2C_RES=0.0025``) — ``GATE 1`` cell count ==
  145 884 exactly; ``GATE 2`` DG1 relL2 over the recorded metric span
  reproduces 10.9806%; ``GATE 3`` CG1 relL2 over the same span reproduces
  7.8411%.
* **New rung** (default h = 0.0017678) — ``GATE 1`` all 45 dense radii lie
  inside the mesh for both recoveries (the sampler is sound); ``GATE 2`` the
  cell count is strictly between the two recorded rungs (this is an
  intermediate rung, not a re-solve of either); ``GATE 3`` **the negative
  control**: the CG1/DG1 gap persists at this rung (CG1 span < DG1 span) *and*
  CG1 improves on the smoke rung's 7.8411%.  If either fails, step 2b's
  finding was rung-specific and the rate reading is void.

**Pre-registered read** (§9 item 3, never gated): if the two-point p = 2.00
holds, this rung's CG1 dense relL2 reads ≈ 3.92% = 7.8411% × (1.7678/2.5)²,
and the DG1 path ≈ 7.2% at p = 1.22.  The three-point least-squares rates are
printed beside 2.00 and 1.22 either way.

**Cell-count expectation, declared as an assumption**: ~390 k cells by cube
scaling from 1 097 873 at h = 0.00125.  A large miss is itself a finding about
the mesher's response to ``resolution`` and is printed, not gated.

The verdict is decided on rank 0 and broadcast, so every rank exits with the
same code.

Run (real build, no complex mode)::

    docker compose exec -T fem-em-solver bash -lc \
      'cd /workspace && PYTHONPATH=/workspace/src timeout -k 30 590 mpiexec \
       -n 8 python3 scripts/probes/mag13_step2c_third_rung.py'
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
from mpi4py import MPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fem_em_solver.utils.analytical import (  # noqa: E402
    AnalyticalSolutions,
)
from scripts.probes.mag13_step2b_recovery import (  # noqa: E402
    PROFILE_DR,
    PROFILE_R_MAX,
    PROFILE_R_MIN,
    _bands,
    _project_curl_to_cg1,
    _sample,
    _solve_straight_wire_keep_solver,
)
from tests.validation.test_straight_wire import (  # noqa: E402
    CURRENT,
    WIRE_RADIUS,
)

# The rung under test: sqrt(2) between the two recorded rungs.
RESOLUTION = float(os.environ.get("MAG13_STEP2C_RES", "0.0017678"))

# On record, both from the step-2b slot (2026-08-12, 13:30):
#   20260812T183247Z_MAG-13-step2b-smoke.log  (h = 0.0025)
#   20260812T183329Z_MAG-13-step2b-n8.log     (h = 0.00125)
# Cite, never recompute.  The fine rung is *not* re-solved by this step.
SMOKE_H = 0.0025
SMOKE_CELLS = 145884
SMOKE_DG1_SPAN = 0.109806
SMOKE_CG1_SPAN = 0.078411

FINE_H = 0.00125
FINE_CELLS = 1097873
FINE_DG1_SPAN = 0.047235
FINE_CG1_SPAN = 0.019557

# The two-point observations step 2b read off those two logs.
TWO_POINT_P_CG1 = 2.00
TWO_POINT_P_DG1 = 1.22

# Cube scaling from the fine rung — an assumption, printed and not gated.
EXPECTED_CELLS = int(round(FINE_CELLS * (FINE_H / RESOLUTION) ** 3))


def _rate(h_values, err_values):
    """Least-squares slope of log(err) against log(h) — the observed order."""
    lh = np.log(np.asarray(h_values, dtype=float))
    le = np.log(np.asarray(err_values, dtype=float))
    return float(np.polyfit(lh, le, 1)[0])


def main() -> int:
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0
    is_smoke = f"{RESOLUTION:.6g}" == f"{SMOKE_H:.6g}"

    if rank0:
        print(
            f"[MAG-13 2c] rung h = {RESOLUTION} m at -n {comm.size} "
            f"({'SMOKE — identity run against the recorded smoke rung' if is_smoke else 'NEW RUNG — the third point'}); "
            f"expected cells ~{EXPECTED_CELLS} by cube scaling from "
            f"{FINE_CELLS} at h = {FINE_H} (assumption, not gated)",
            flush=True,
        )

    comm.Barrier()
    t0 = time.perf_counter()
    mesh, solver, b_dg1 = _solve_straight_wire_keep_solver(RESOLUTION, comm)
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    ncells = comm.allreduce(
        mesh.topology.index_map(mesh.topology.dim).size_local, op=MPI.SUM
    )
    ndofs = b_dg1.function_space.dofmap.index_map.size_global

    b_cg1, t_proj, ksp_its = _project_curl_to_cg1(solver, comm)
    n_cg1_dofs = b_cg1.function_space.dofmap.index_map.size_global * 3

    if rank0:
        print(
            f"[MAG-13 2c] mesh+solve {t_solve:.1f} s at -n {comm.size}, "
            f"{ncells} cells / {ndofs} global DG1 dofs "
            f"({ncells / EXPECTED_CELLS:.3f}x the cube-scaling expectation)",
            flush=True,
        )
        print(
            f"[MAG-13 2c] CG1 L2 projection of curl A: {t_proj:.2f} s "
            f"({t_proj / t_solve:.1%} of the solve), {ksp_its} CG iterations "
            f"(cg+gamg, rtol 1e-12), {n_cg1_dofs} global dofs",
            flush=True,
        )

    # --- both recoveries on the recorded 45-radius grid ----------------------
    n_profile = int(round((PROFILE_R_MAX - PROFILE_R_MIN) / PROFILE_DR)) + 1
    r_dense = PROFILE_R_MIN + PROFILE_DR * np.arange(n_profile)
    points = np.zeros((n_profile, 3))
    points[:, 0] = r_dense

    v_dg1, valid_dg1 = _sample(b_dg1, points, comm)
    v_cg1, valid_cg1 = _sample(b_cg1, points, comm)

    if not rank0:
        # Matching receive for rank 0's verdict broadcast at the end of main().
        return int(comm.bcast(None, root=0))

    b_ana = np.linalg.norm(
        AnalyticalSolutions.straight_wire_magnetic_field(points, CURRENT), axis=1
    )
    n_dg1 = np.linalg.norm(v_dg1, axis=1)
    n_cg1 = np.linalg.norm(v_cg1, axis=1)

    n_valid_dg1 = int(valid_dg1.sum())
    n_valid_cg1 = int(valid_cg1.sum())
    print(
        f"[MAG-13 2c] dense sample: {n_profile} radii {PROFILE_R_MIN:.4f} -> "
        f"{PROFILE_R_MAX:.4f} m, step {PROFILE_DR * 1e3:.1f} mm; inside mesh: "
        f"DG1 {n_valid_dg1}/{n_profile}, CG1 {n_valid_cg1}/{n_profile}",
        flush=True,
    )

    s_dg1 = (n_dg1 - b_ana) / b_ana
    s_cg1 = (n_cg1 - b_ana) / b_ana
    print("    r [m]     |B|_DG1      |B|_CG1      |B|_ana      DG1      CG1")
    for i in range(n_profile):
        print(
            f"    {r_dense[i]:.4f}  {n_dg1[i]:.4e}  {n_cg1[i]:.4e}  "
            f"{b_ana[i]:.4e}  {s_dg1[i]:+7.2%}  {s_cg1[i]:+7.2%}",
            flush=True,
        )

    bands_dg1 = _bands(r_dense, n_dg1, b_ana)
    bands_cg1 = _bands(r_dense, n_cg1, b_ana)
    print(
        "[MAG-13 2c] error by radial band (relL2 / mean|rel| / max|rel|), "
        "DG1 interpolation vs CG1 recovery:",
        flush=True,
    )
    labels = {
        "near-wire": "near-wire  2.0a - 3.3a",
        "mid": "mid        3.3a - 5.3a",
        "outer": "outer      5.3a - 8.0a (to 0.8R)",
        "wall": "wall band  0.8R - 0.93R",
        "span": "recorded metric span",
        "full": "full dense span",
    }
    for key, label in labels.items():
        nd, l2d, md, xd = bands_dg1[key]
        _, l2c, mc, xc = bands_cg1[key]
        print(
            f"    {label:<34s} n={nd:2d}  DG1 {l2d:.4%}/{md:.4%}/{xd:.4%}   "
            f"CG1 {l2c:.4%}/{mc:.4%}/{xc:.4%}   "
            f"delta relL2 {(l2c - l2d) * 100:+.4f} pp",
            flush=True,
        )

    dg1_span = bands_dg1["span"][1]
    cg1_span = bands_cg1["span"][1]

    # --- the three-point reading --------------------------------------------
    if is_smoke:
        print(
            "[MAG-13 2c] identity run: no third point to fit — the rate table "
            "belongs to the new-rung run.",
            flush=True,
        )
    else:
        pred_cg1 = SMOKE_CG1_SPAN * (RESOLUTION / SMOKE_H) ** TWO_POINT_P_CG1
        pred_dg1 = SMOKE_DG1_SPAN * (RESOLUTION / SMOKE_H) ** TWO_POINT_P_DG1
        hs = [SMOKE_H, RESOLUTION, FINE_H]
        cg1s = [SMOKE_CG1_SPAN, cg1_span, FINE_CG1_SPAN]
        dg1s = [SMOKE_DG1_SPAN, dg1_span, FINE_DG1_SPAN]
        p3_cg1 = _rate(hs, cg1s)
        p3_dg1 = _rate(hs, dg1s)
        # Pairwise rates: coarse->new and new->fine, each a two-point reading.
        def pw(e0, e1, h0, h1):
            return float(np.log(e0 / e1) / np.log(h0 / h1))

        print(
            "[MAG-13 2c] THREE-POINT TABLE (relL2 over the recorded metric "
            "span; the h = 0.0025 and h = 0.00125 rows are cited from the "
            "step-2b logs, not re-solved):",
            flush=True,
        )
        print("        h [m]        cells        DG1 relL2    CG1 relL2", flush=True)
        print(
            f"        {SMOKE_H:.7f}    {SMOKE_CELLS:>9d}    {SMOKE_DG1_SPAN:.4%}     "
            f"{SMOKE_CG1_SPAN:.4%}   (record)",
            flush=True,
        )
        print(
            f"        {RESOLUTION:.7f}    {ncells:>9d}    {dg1_span:.4%}     "
            f"{cg1_span:.4%}   (this run)",
            flush=True,
        )
        print(
            f"        {FINE_H:.7f}    {FINE_CELLS:>9d}    {FINE_DG1_SPAN:.4%}     "
            f"{FINE_CG1_SPAN:.4%}   (record)",
            flush=True,
        )
        print(
            f"[MAG-13 2c] PREDICTION vs MEASUREMENT at this rung: CG1 "
            f"predicted {pred_cg1:.4%} at p = {TWO_POINT_P_CG1:.2f}, measured "
            f"{cg1_span:.4%} ({(cg1_span - pred_cg1) * 100:+.4f} pp); DG1 "
            f"predicted {pred_dg1:.4%} at p = {TWO_POINT_P_DG1:.2f}, measured "
            f"{dg1_span:.4%} ({(dg1_span - pred_dg1) * 100:+.4f} pp)",
            flush=True,
        )
        print(
            f"[MAG-13 2c] RATES (least squares over three points): CG1 "
            f"p = {p3_cg1:.3f} beside the two-point observation "
            f"{TWO_POINT_P_CG1:.2f}; DG1 p = {p3_dg1:.3f} beside "
            f"{TWO_POINT_P_DG1:.2f}",
            flush=True,
        )
        print(
            f"[MAG-13 2c] pairwise rates: CG1 coarse->new "
            f"{pw(SMOKE_CG1_SPAN, cg1_span, SMOKE_H, RESOLUTION):.3f}, "
            f"new->fine {pw(cg1_span, FINE_CG1_SPAN, RESOLUTION, FINE_H):.3f}; "
            f"DG1 coarse->new "
            f"{pw(SMOKE_DG1_SPAN, dg1_span, SMOKE_H, RESOLUTION):.3f}, "
            f"new->fine {pw(dg1_span, FINE_DG1_SPAN, RESOLUTION, FINE_H):.3f}",
            flush=True,
        )

    print(
        f"[MAG-13 2c] provenance: rung h = {RESOLUTION} m, current {CURRENT} A, "
        f"wire radius {WIRE_RADIUS} m; real build, no complex mode; projection "
        f"{t_proj:.2f} s beside a {t_solve:.1f} s mesh+solve",
        flush=True,
    )

    # --- gates ---------------------------------------------------------------
    if is_smoke:
        cells_ok = ncells == SMOKE_CELLS
        dg1_ok = f"{dg1_span:.4%}" == f"{SMOKE_DG1_SPAN:.4%}"
        cg1_ok = f"{cg1_span:.4%}" == f"{SMOKE_CG1_SPAN:.4%}"
        gates = [
            (
                "GATE 1 smoke-rung cells",
                cells_ok,
                f"{ncells} vs {SMOKE_CELLS} on record -> "
                f"{'PASS' if cells_ok else 'FAIL'}",
            ),
            (
                "GATE 2 smoke DG1 span",
                dg1_ok,
                f"{dg1_span:.4%} vs {SMOKE_DG1_SPAN:.4%} on record -> "
                f"{'PASS' if dg1_ok else 'FAIL'}",
            ),
            (
                "GATE 3 smoke CG1 span",
                cg1_ok,
                f"{cg1_span:.4%} vs {SMOKE_CG1_SPAN:.4%} on record -> "
                f"{'PASS' if cg1_ok else 'FAIL'}",
            ),
        ]
    else:
        sampler_ok = n_valid_dg1 == n_profile and n_valid_cg1 == n_profile
        intermediate_ok = SMOKE_CELLS < ncells < FINE_CELLS
        gap_ok = cg1_span < dg1_span
        improves_ok = cg1_span < SMOKE_CG1_SPAN
        control_ok = gap_ok and improves_ok
        gates = [
            (
                "GATE 1 sampler validity",
                sampler_ok,
                f"DG1 {n_valid_dg1}/{n_profile}, CG1 {n_valid_cg1}/{n_profile} "
                f"radii inside mesh -> {'PASS' if sampler_ok else 'FAIL'}",
            ),
            (
                "GATE 2 intermediate rung",
                intermediate_ok,
                f"{SMOKE_CELLS} < {ncells} < {FINE_CELLS} -> "
                f"{'PASS' if intermediate_ok else 'FAIL'}",
            ),
            (
                "GATE 3 negative control",
                control_ok,
                f"CG1/DG1 gap persists: {cg1_span:.4%} < {dg1_span:.4%} -> "
                f"{'PASS' if gap_ok else 'FAIL'}; CG1 improves on the smoke "
                f"rung: {cg1_span:.4%} < {SMOKE_CG1_SPAN:.4%} -> "
                f"{'PASS' if improves_ok else 'FAIL'}",
            ),
        ]

    print("[MAG-13 2c] GATES (exit code is gated on these):", flush=True)
    for label, ok, detail in gates:
        print(f"    {label:<26s} {'PASS' if ok else 'FAIL'}  ({detail})", flush=True)
    n_failed = sum(1 for _, ok, _ in gates if not ok)
    code = 0 if n_failed == 0 else 1
    print(
        f"[MAG-13 2c] OVERALL: {len(gates) - n_failed}/{len(gates)} gates pass "
        f"-> exit {code}",
        flush=True,
    )
    return int(comm.bcast(code, root=0))


if __name__ == "__main__":
    raise SystemExit(main())
