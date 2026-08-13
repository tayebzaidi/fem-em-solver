"""`MAG-13` step 2 cost probe and gate: the < 5% wire at h ~ 0.00125.

PROJECT_PLAN §7 (`MAG-13` step 2) makes this probe the point of no return.
`MAG-13` closed at wire 12.75% (h = 0.0025, 145.9 k cells) with a measured
two-rung rate of 1.10 over h = 0.004 / 0.0025 / 0.0018 (22.19% / 12.75% /
9.26%).  Extrapolating that rate puts the < 5% crossing at h ~ 0.00125,
~1.1 M cells.

Stage 1 meshes and prints the cell count (cheap, no solve).  Stage 2 runs
**one** solve, samples the same annulus the gate test samples (2a -> 0.8 R,
via ``evaluate_vector_field_parallel``), and reports the relative L2 error
against ``straight_wire_magnetic_field`` beside the 12.75% on record, with
the new two-rung observed rate beside the 1.10 on record.

§7 stop rule: OOM ⇒ one retry of the single solve at ``-n 8``; still OOM or
> 600 s ⇒ report the measured cost and stop.  The cautionary record is
`MAT-6` step 5's 1 458 561-cell rung, OOM-killed at ``-n 4`` (complex build;
this real-build solve is lighter, but that is a hope, not a measurement).

Run (real build)::

    docker compose exec -T fem-em-solver bash -lc \
      'cd /workspace && PYTHONPATH=/workspace/src mpiexec -n 4 python3 \
       scripts/probes/mag13_step2_probe.py'
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
from mpi4py import MPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fem_em_solver.utils.analytical import AnalyticalSolutions, ErrorMetrics  # noqa: E402
from tests.validation.test_straight_wire import (  # noqa: E402
    CURRENT,
    R_MAX_BC,
    R_MIN,
    _sample_radial,
    _solve_straight_wire,
)

# The extrapolated rung.  Nothing else about the fixture moves.
RESOLUTION_FINE = float(os.environ.get("MAG13_STEP2_RES", "0.00125"))
# Mesh-only mode: stage 1 alone, when the cell count is the only question.
MESH_ONLY = os.environ.get("MAG13_STEP2_MESH_ONLY", "0") == "1"

# On record (MAG-13, log 20260730T034614Z_MAG-13-probe2, -n 2, analytic
# Dirichlet wall, sampling 2a -> 0.8 R): cite, never recompute.
REF_H = 0.0025
REF_ERR = 0.1275
REF_RATE = 1.10
N_POINTS = 10

# Rung 2, on record (MAG-13 step 2, log 20260811T200040Z_MAG-13-step2-solve-n8,
# exit 0, -n 8, 1 097 873 cells): cite, never recompute.  Used for the
# three-rung rate the §7 step-2-rung-3 entry asks to print beside 1.174/1.10.
REF2_H = 0.00125
REF2_ERR = 0.056494
REF2_RATE = 1.174

# The gate the §7 entry pre-registers for rung 3.  Neither bound moves.
TARGET_ERR = 0.0500
AZIMUTHALITY_BOUND = 0.10


def main() -> int:
    comm = MPI.COMM_WORLD

    if MESH_ONLY:
        from fem_em_solver.io.mesh import MeshGenerator
        from tests.validation.test_straight_wire import (
            DOMAIN_RADIUS,
            WIRE_LENGTH,
            WIRE_RADIUS,
        )

        if comm.rank == 0:
            print(
                f"[MAG-13 step 2 probe] mesh-only, h = {RESOLUTION_FINE} m, "
                f"-n {comm.size}; predicted ~1.1 M cells "
                f"(h = 0.0025 was 145 900)",
                flush=True,
            )
        comm.Barrier()
        t0 = time.perf_counter()
        mesh, _, _ = MeshGenerator.straight_wire_domain(
            wire_length=WIRE_LENGTH,
            wire_radius=WIRE_RADIUS,
            domain_radius=DOMAIN_RADIUS,
            resolution=RESOLUTION_FINE,
            comm=comm,
        )
        comm.Barrier()
        t_mesh = time.perf_counter() - t0
        ncells = comm.allreduce(
            mesh.topology.index_map(mesh.topology.dim).size_local, op=MPI.SUM
        )
        if comm.rank == 0:
            print(
                f"[MAG-13 step 2 probe] mesh: {ncells} cells in {t_mesh:.1f} s",
                flush=True,
            )
        return 0

    if comm.rank == 0:
        print(
            f"[MAG-13 step 2 probe] solve at h = {RESOLUTION_FINE} m, "
            f"-n {comm.size}; target < 5% vs {REF_ERR:.2%} on record at "
            f"h = {REF_H}",
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

    r_test, b_num_mag, b_ana_mag, values = _sample_radial(
        b_field, N_POINTS, comm, R_MIN, R_MAX_BC
    )
    rel_error = ErrorMetrics.l2_relative_error(b_num_mag, b_ana_mag)
    b_z_max = float(np.max(np.abs(values[:, 2])))
    b_ref = float(np.max(b_ana_mag))

    # Two-rung observed rate against the recorded h = 0.0025 / 12.75% rung.
    rate = np.log(REF_ERR / rel_error) / np.log(REF_H / RESOLUTION_FINE)
    # Pairwise rate against the recorded rung 2, and the three-rung least
    # squares fit over (REF_H, REF2_H, this h) -- the §7 entry asks for the
    # three-rung number beside the recorded 1.174 and 1.10.
    rate_pair2 = np.log(REF2_ERR / rel_error) / np.log(REF2_H / RESOLUTION_FINE)
    hs = np.array([REF_H, REF2_H, RESOLUTION_FINE])
    errs = np.array([REF_ERR, REF2_ERR, rel_error])
    rate3 = float(np.polyfit(np.log(hs), np.log(errs), 1)[0])

    # Quantitative gate (§7 step-2-rung-3): the exit code carries the result.
    passed_err = rel_error < TARGET_ERR
    passed_azi = b_z_max / b_ref <= AZIMUTHALITY_BOUND

    if comm.rank == 0:
        print(
            f"[MAG-13 step 2 probe] mesh+solve: {t_solve:.1f} s at "
            f"-n {comm.size}, {ncells} cells / {ndofs} global dofs",
            flush=True,
        )
        print(f"[MAG-13 step 2 probe] relative L2 error: {rel_error:.4%} "
              f"(target < 5.00%; record {REF_ERR:.2%} at h = {REF_H})",
              flush=True)
        print(f"[MAG-13 step 2 probe] two-rung observed rate "
              f"{REF_H} -> {RESOLUTION_FINE}: {rate:.3f} "
              f"(record 1.10 over 0.004 -> 0.0018)", flush=True)
        print(f"[MAG-13 step 2 probe] pairwise rate {REF2_H} -> "
              f"{RESOLUTION_FINE}: {rate_pair2:.3f}; three-rung fit over "
              f"{REF_H}/{REF2_H}/{RESOLUTION_FINE}: {rate3:.3f} "
              f"(record 1.174 two-rung, 1.10 landed)", flush=True)
        print(f"[MAG-13 step 2 probe] B_z max {b_z_max:.3e} vs |B|_ref "
              f"{b_ref:.3e} (azimuthality check, bound "
              f"{AZIMUTHALITY_BOUND})", flush=True)
        for r, bn, ba in zip(r_test, b_num_mag, b_ana_mag):
            print(f"    r={r:.4f}  |B|_num={bn:.4e}  |B|_ana={ba:.4e}  "
                  f"rel={abs(bn - ba) / ba:.2%}", flush=True)
        _ = AnalyticalSolutions  # imported for provenance of the reference
        print(f"[MAG-13 step 2 probe] current {CURRENT} A, "
              f"sampling {R_MIN:.4f} -> {R_MAX_BC:.4f} m", flush=True)
        verdict = "PASS" if passed_err else "FAIL"
        print(f"[MAG-13 step 2 probe] GATE relative L2 {verdict}: "
              f"{rel_error:.4%} vs target < {TARGET_ERR:.2%}", flush=True)
        verdict = "PASS" if passed_azi else "FAIL"
        print(f"[MAG-13 step 2 probe] GATE azimuthality {verdict}: "
              f"{b_z_max / b_ref:.3e} vs bound <= "
              f"{AZIMUTHALITY_BOUND}", flush=True)
    return 0 if (passed_err and passed_azi) else 1


if __name__ == "__main__":
    raise SystemExit(main())
