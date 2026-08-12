"""`MAG-13` step 2 profile: where does the 5.65% live?

PROJECT_PLAN §7 (`MAG-13` step 2 profile) scopes this as a *measurement only*
step: re-solve the h ~ 0.00125 rung exactly as measured on 2026-08-11
(`20260811T200040Z_MAG-13-step2-solve-n8.log`: 1 097 873 cells, 5.6494%
relative L2, 275.3 s at ``-n 8``) and replace the ten sample radii on record
with a dense error-vs-radius profile, so the review can scope a graded mesh
against a map instead of ten points.

Order of operations, deliberately:

1. **Fixture identity first.**  Cell count must be digit-identical to
   1 097 873 and the ten-point relative L2 must reproduce 5.6494% to its
   printed digits.  Neither is asserted as a gate here (this step moves no
   bound, and `MAG-13` stays ✅ either way) but both are printed with an
   explicit PASS/FAIL verdict, and the profile claim is only meaningful if
   they hold.
2. **Dense profile**: 45 radii, r = 0.006 -> 0.028 m in 0.5 mm steps, through
   ``evaluate_vector_field_parallel``.  The grid is chosen to contain the four
   radii the coarse table on record names (0.0080 / 0.0100 / 0.0200 / 0.0240,
   reading 9.46% / 6.33% / 0.33% / 1.40%), which are the step's declared
   negative control: a dense profile that contradicts its own coarse sample is
   a bug, not a finding.

Note the span runs past the ten-point sampler's outer limit
(``R_MAX_BC`` = 0.8 R = 0.024 m) out to 0.028 m = 0.933 R, as §7 asks; those
last radii sit in the wall-perturbed region the fixture normally avoids, and
are reported separately from the [0.006, 0.024] band the recorded metric uses.

Run (real build, no complex mode)::

    docker compose exec -T fem-em-solver bash -lc \
      'cd /workspace && PYTHONPATH=/workspace/src timeout 590 mpiexec -n 8 \
       python3 scripts/probes/mag13_step2_profile.py'
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
from mpi4py import MPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fem_em_solver.post.evaluation import (  # noqa: E402
    evaluate_vector_field_parallel,
)
from fem_em_solver.utils.analytical import (  # noqa: E402
    AnalyticalSolutions,
    ErrorMetrics,
)
from tests.validation.test_straight_wire import (  # noqa: E402
    CURRENT,
    R_MAX_BC,
    R_MIN,
    _sample_radial,
    _solve_straight_wire,
)

RESOLUTION_FINE = float(os.environ.get("MAG13_STEP2_RES", "0.00125"))

# On record (20260811T200040Z_MAG-13-step2-solve-n8.log): cite, never recompute.
REF_CELLS = 1097873
REF_REL_L2 = 0.056494
REF_H = 0.0025
REF_ERR = 0.1275
# The coarse table's four named radii, the declared negative control.
CONTROL = {0.0080: 0.0946, 0.0100: 0.0633, 0.0200: 0.0033, 0.0240: 0.0140}

# Dense grid: 45 radii, 0.5 mm apart, containing every control radius.
PROFILE_R_MIN = 0.006
PROFILE_R_MAX = 0.028
PROFILE_DR = 0.0005


def main() -> int:
    comm = MPI.COMM_WORLD
    rank0 = comm.rank == 0

    if rank0:
        print(
            f"[MAG-13 profile] re-solve h = {RESOLUTION_FINE} m at "
            f"-n {comm.size}; identity targets {REF_CELLS} cells / "
            f"{REF_REL_L2:.4%} relative L2",
            flush=True,
        )

    comm.Barrier()
    t0 = time.perf_counter()
    mesh, b_field = _solve_straight_wire(RESOLUTION_FINE, comm)
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    ncells = comm.allreduce(
        mesh.topology.index_map(mesh.topology.dim).size_local, op=MPI.SUM
    )
    ndofs = b_field.function_space.dofmap.index_map.size_global

    # --- 1. fixture identity ------------------------------------------------
    r10, b10_num, b10_ana, values10 = _sample_radial(
        b_field, 10, comm, R_MIN, R_MAX_BC
    )
    rel_l2_10 = ErrorMetrics.l2_relative_error(b10_num, b10_ana)
    cells_ok = ncells == REF_CELLS
    l2_ok = f"{rel_l2_10:.4%}" == f"{REF_REL_L2:.4%}"

    if rank0:
        print(
            f"[MAG-13 profile] mesh+solve {t_solve:.1f} s at -n {comm.size}, "
            f"{ncells} cells / {ndofs} global dofs",
            flush=True,
        )
        print(
            f"[MAG-13 profile] IDENTITY cells: {ncells} vs {REF_CELLS} "
            f"on record -> {'PASS' if cells_ok else 'FAIL'}",
            flush=True,
        )
        print(
            f"[MAG-13 profile] IDENTITY relative L2 (10 pts, "
            f"{R_MIN:.4f} -> {R_MAX_BC:.4f} m): {rel_l2_10:.4%} vs "
            f"{REF_REL_L2:.4%} on record -> "
            f"{'PASS' if l2_ok else 'FAIL'}",
            flush=True,
        )
        b_z10 = float(np.max(np.abs(values10[:, 2])))
        print(
            f"[MAG-13 profile] azimuthality control: B_z max {b_z10:.3e} vs "
            f"|B|_ref {float(np.max(b10_ana)):.3e} = "
            f"{b_z10 / float(np.max(b10_ana)):.1e} (bound 0.10)",
            flush=True,
        )

    # --- 2. dense profile ---------------------------------------------------
    n_profile = int(round((PROFILE_R_MAX - PROFILE_R_MIN) / PROFILE_DR)) + 1
    r_dense = PROFILE_R_MIN + PROFILE_DR * np.arange(n_profile)
    points = np.zeros((n_profile, 3))
    points[:, 0] = r_dense  # midplane, +x, exactly as the ten-point sampler

    values, valid = evaluate_vector_field_parallel(b_field, points, comm=comm)
    b_num = np.linalg.norm(values, axis=1)
    b_ana_vec = AnalyticalSolutions.straight_wire_magnetic_field(points, CURRENT)
    b_ana = np.linalg.norm(b_ana_vec, axis=1)

    if not rank0:
        return 0

    n_invalid = int((~valid).sum())
    print(
        f"[MAG-13 profile] dense sample: {n_profile} radii "
        f"{PROFILE_R_MIN:.4f} -> {PROFILE_R_MAX:.4f} m, step "
        f"{PROFILE_DR * 1e3:.1f} mm; {n_invalid} point(s) outside mesh",
        flush=True,
    )

    signed = (b_num - b_ana) / b_ana
    rel = np.abs(signed)
    print("    r [m]     |B|_num      |B|_ana      rel      signed    B_z")
    for i in range(n_profile):
        flag = ""
        if not valid[i]:
            flag = "  OUTSIDE-MESH"
        for rc, ref in CONTROL.items():
            if abs(r_dense[i] - rc) < 1e-9:
                flag = f"  CONTROL(record {ref:.2%})"
        print(
            f"    {r_dense[i]:.4f}  {b_num[i]:.4e}  {b_ana[i]:.4e}  "
            f"{rel[i]:6.2%}  {signed[i]:+7.2%}  {values[i, 2]:+.2e}{flag}",
            flush=True,
        )

    # Negative control verdict: the dense profile must reproduce the four
    # recorded radii.  Same solve, same sampler, same points -> the tolerance
    # is round-off-ish, not physics; 0.05 pp is generous and stated as such.
    print("[MAG-13 profile] NEGATIVE CONTROL vs the ten-point table on record:",
          flush=True)
    control_ok = True
    for rc, ref in sorted(CONTROL.items()):
        i = int(np.argmin(np.abs(r_dense - rc)))
        delta_pp = (rel[i] - ref) * 100.0
        ok = abs(delta_pp) <= 0.05
        control_ok = control_ok and ok
        print(
            f"    r={rc:.4f}  dense {rel[i]:.2%}  record {ref:.2%}  "
            f"delta {delta_pp:+.3f} pp -> {'PASS' if ok else 'FAIL'}",
            flush=True,
        )
    print(
        f"[MAG-13 profile] negative control overall: "
        f"{'PASS' if control_ok else 'FAIL'}",
        flush=True,
    )

    # --- 3. where the error lives -------------------------------------------
    def band(lo, hi):
        m = (r_dense >= lo - 1e-12) & (r_dense <= hi + 1e-12)
        return (
            int(m.sum()),
            ErrorMetrics.l2_relative_error(b_num[m], b_ana[m]),
            float(rel[m].mean()),
            float(rel[m].max()),
        )

    print("[MAG-13 profile] error by radial band (n, relL2, mean|rel|, max|rel|):",
          flush=True)
    for lo, hi, label in [
        (0.006, 0.010, "near-wire  2.0a - 3.3a"),
        (0.010, 0.016, "mid        3.3a - 5.3a"),
        (0.016, 0.024, "outer      5.3a - 8.0a (to 0.8R)"),
        (0.024, 0.028, "wall band  0.8R - 0.93R"),
        (0.006, 0.024, "recorded metric span"),
        (0.006, 0.028, "full dense span"),
    ]:
        n, l2, mean, mx = band(lo, hi)
        print(
            f"    {label:<34s} n={n:2d}  relL2={l2:.4%}  "
            f"mean={mean:.4%}  max={mx:.4%}",
            flush=True,
        )

    i_max = int(np.argmax(rel))
    print(
        f"[MAG-13 profile] worst radius r={r_dense[i_max]:.4f} m "
        f"({r_dense[i_max] / 0.003:.2f} a), rel {rel[i_max]:.4%}",
        flush=True,
    )
    # Does the error decay with radius?  Fit log|rel| vs log r over the span
    # inside 0.8 R, excluding non-positive residuals.
    m = (r_dense <= R_MAX_BC + 1e-12) & (rel > 0)
    slope = float(np.polyfit(np.log(r_dense[m]), np.log(rel[m]), 1)[0])
    print(
        f"[MAG-13 profile] log-log slope of |rel| vs r over "
        f"[{PROFILE_R_MIN:.4f}, {R_MAX_BC:.4f}] m: {slope:+.3f} "
        f"(negative = error concentrates near the wire)",
        flush=True,
    )
    print(
        f"[MAG-13 profile] provenance: record rung h = {REF_H} m at "
        f"{REF_ERR:.2%}; current {CURRENT} A; wire radius 0.003 m; "
        f"real build, no complex mode",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
