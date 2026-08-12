"""`MAT-6` step 10 cost probe: what does the *composed* fixture cost?

PROJECT_PLAN §7 (`MAT-6` step 10) makes this probe the point of no return.  The
fixture is step 7 Part 2c's combined mesh (``box_half_width`` = 0.25,
``resolution_wire`` = 0.001, 697 401 cells on record) **plus** step 8's slab
knob (``resolution_near`` 0.005 → 0.0025).  The composed cell count is
unmeasured: step 8's knob added ~208 k near-region cells to a 210 k fixture, so
~1 M is an estimate, and an OOM at the 64 G cap is itself a per-cell memory
reading.

Stage 1 meshes and prints the cell count, cheap and solve-free
(``MAT6_STEP10_MESH_ONLY=1``).  Stage 2 runs **one** projected loaded solve and
times it.  §7 stop rule: OOM, or one solve > 300 s ⇒ report the measured cost
and stop; the rescope is a coarser rung, never a raised timeout (§5.1).

Run (complex build only, **foreground** — implementer-run.md's allowlist
section: a backgrounded harness call is SIGKILLed when the session's turn
ends)::

    docker compose exec -T fem-em-solver bash -lc \
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \
       PYTHONPATH=/workspace/src mpiexec -n 8 python3 \
       scripts/probes/mat6_step10_probe.py'
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
from mpi4py import MPI
from petsc4py import PETSc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fem_em_solver.core import (  # noqa: E402
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402
from tests.validation.test_dodd_deeds_impedance import (  # noqa: E402
    FEM_CURRENT_A,
    FEM_FREQUENCY_HZ,
    FEM_LIFTOFF,
    FEM_LOOP_RADIUS,
    FEM_SIGMA_SLAB,
    FEM_WIRE_RADIUS,
    SLAB_TAG,
    WIRE_TAG,
    _azimuthal_current_density,
)

# The composed fixture: step 7 Part 2c's two knobs plus step 8's.
BOX_HALF_WIDTH = 0.25
RESOLUTION_WIRE = 0.001
RESOLUTION_NEAR = float(os.environ.get("MAT6_STEP10_RESOLUTION_NEAR", "0.0025"))
MESH_ONLY = os.environ.get("MAT6_STEP10_MESH_ONLY", "0") == "1"
# Step 10a knobs.  `ROLE` selects which rung of the attribution ladder this run
# is: "baseline" (resolution_near = 0.005, the un-composed box+wire fixture,
# 178-196 s on record at -n 8) also carries the step's negative control, an
# enforced wall-clock band; "intermediate" (0.0035) and "composed" (0.0025) are
# measurement-only.  `MUMPS_VERBOSE` turns on ICNTL(4) = 2 so the analysis
# phase prints its statistics *before* numeric factorization starts, which is
# the only reading run (3) can produce — it is killed mid-factorization by
# design and `exit 124 with the stats in the log` is the measurement.
ROLE = os.environ.get("MAT6_STEP10_ROLE", "composed")
MUMPS_VERBOSE = os.environ.get("MAT6_STEP10_MUMPS_VERBOSE", "0") == "1"
# §7 step 10a negative control: the baseline's own wall clock must land on its
# 178-196 s record at ±25%, else the environment moved and every ratio this
# probe reports is void.
BASELINE_SOLVE_BAND_S = (178.0 * 0.75, 196.0 * 1.25)
# On record for the un-composed fixtures, for the growth line.
NCELLS_COMBINED = 697_401  # W = 0.25, wire 0.001, slab 0.005 (step 7 Part 2c)
NCELLS_SLAB_FINE = 417_914  # W = 0.15, wire 0.002, slab 0.0025 (step 8)
SKIN_DEPTH_M = 0.0159


def main() -> int:
    comm = MPI.COMM_WORLD
    if np.dtype(PETSc.ScalarType).kind != "c":  # pragma: no cover
        raise SystemExit("probe requires the complex build (dolfinx-complex-mode)")

    if comm.rank == 0:
        print(
            f"[MAT-6 step 10 probe] role = {ROLE}, mumps_verbose = "
            f"{int(MUMPS_VERBOSE)}; W = {BOX_HALF_WIDTH} m, "
            f"resolution_wire = {RESOLUTION_WIRE} m, resolution_near = "
            f"{RESOLUTION_NEAR:g} m ({SKIN_DEPTH_M / RESOLUTION_NEAR:.2f} cells "
            f"per skin depth) at -n {comm.size}; on record {NCELLS_COMBINED} "
            f"(box+wire) and {NCELLS_SLAB_FINE} (slab alone)",
            flush=True,
        )

    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=BOX_HALF_WIDTH,
        resolution_wire=RESOLUTION_WIRE,
        resolution_near=RESOLUTION_NEAR,
        resolution_far=0.025,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    comm.Barrier()
    t_mesh = time.perf_counter() - t0
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    if comm.rank == 0:
        print(
            f"[MAT-6 step 10 probe] {ncells} cells "
            f"({ncells / NCELLS_COMBINED:.2f}x the box+wire fixture, "
            f"{ncells / 138619:.2f}x the step-2b baseline), meshed in "
            f"{t_mesh:.1f} s on {comm.size} ranks",
            flush=True,
        )

    if MESH_ONLY:
        if comm.rank == 0:
            print("[MAT-6 step 10 probe] mesh-only mode: no solve", flush=True)
        return 0

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FEM_FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SLAB_TAG: HomogeneousMaterial(
                sigma=FEM_SIGMA_SLAB, epsilon_r=1.0, mu_r=1.0
            )
        },
        boundary_condition="pec_zero_tangential_a",
        solver_petsc_options={"mat_mumps_icntl_4": 2} if MUMPS_VERBOSE else None,
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)

    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[WIRE_TAG],
        # Production default path (solve + CG1 Poisson projection), the only
        # drive step 10 reads.
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    ndofs = fields.e_complex.function_space.dofmap.index_map.size_global
    if comm.rank == 0:
        print(
            f"[MAT-6 step 10 probe] one projected loaded solve: {t_solve:.1f} s "
            f"at -n {comm.size}, {ncells} cells / {ndofs} global dofs",
            flush=True,
        )
        print(
            f"[MAT-6 step 10 probe] budget: the gate's loaded/free pair costs "
            f"~{2 * t_solve + t_mesh:.0f} s including mesh.  §7 stop rule is one "
            f"solve > 300 s or OOM.",
            flush=True,
        )

    _report_mumps_stats(comm, solver, ncells, ndofs)

    failures = []
    if ROLE == "baseline":
        lo, hi = BASELINE_SOLVE_BAND_S
        ok = lo <= t_solve <= hi
        if comm.rank == 0:
            print(
                f"[MAT-6 step 10a control] baseline solve {t_solve:.1f} s vs the "
                f"178-196 s record at +-25% ([{lo:.1f}, {hi:.1f}] s): "
                f"{'PASS' if ok else 'FAIL'}",
                flush=True,
            )
        if not ok:
            failures.append(
                f"baseline solve {t_solve:.1f} s outside [{lo:.1f}, {hi:.1f}] s "
                "— the environment moved and the step-10a ratios are void"
            )

    failures = comm.bcast(failures, root=0)
    if failures:
        if comm.rank == 0:
            for message in failures:
                print(f"[MAT-6 step 10a control] FAIL: {message}", flush=True)
        return 1
    return 0


def _report_mumps_stats(comm, solver, ncells: int, ndofs: int) -> None:
    """Print MUMPS's own factorization statistics for this solve.

    The anchor of step 10a is the ratio of *estimated factor flops*
    (``RINFOG(1)``) between the composed 0.0025 fixture and the box+wire
    baseline, read against the 1.28x cell ratio.  MUMPS also prints these
    during the analysis phase when ``ICNTL(4) = 2`` — that printed copy is what
    a killed run leaves behind; this query is the exact reading for the runs
    that finish.  ``INFOG(20)`` is the estimated number of entries in the
    factors, negative when expressed in millions (MUMPS convention).
    """
    lp = getattr(solver, "_linear_problem", None)
    if lp is None:  # pragma: no cover — solver API changed
        if comm.rank == 0:
            print(
                "[MAT-6 step 10a] no LinearProblem handle: MUMPS stats "
                "unavailable from Python; read the ICNTL(4) printout instead",
                flush=True,
            )
        return
    try:
        factor = lp.solver.getPC().getFactorMatrix()
        flops = factor.getMumpsRinfog(1)
        nnz_raw = factor.getMumpsInfog(20)
        ordering = factor.getMumpsInfog(7)
    except Exception as exc:  # pragma: no cover — not a MUMPS factor
        if comm.rank == 0:
            print(f"[MAT-6 step 10a] MUMPS stats query failed: {exc}", flush=True)
        return
    nnz = -nnz_raw * 1e6 if nnz_raw < 0 else float(nnz_raw)
    if comm.rank == 0:
        print(
            f"[MAT-6 step 10a] MUMPS estimated factor flops RINFOG(1) = "
            f"{flops:.6e}, estimated factor entries INFOG(20) = {nnz:.6e} "
            f"(raw {nnz_raw}), ordering INFOG(7) = {ordering}; "
            f"{ncells} cells / {ndofs} dofs, "
            f"flops per dof = {flops / max(ndofs, 1):.4e}",
            flush=True,
        )


if __name__ == "__main__":
    raise SystemExit(main())
