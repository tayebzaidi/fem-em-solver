"""`MAT-6` step 6 cost probe: what do *both* knobs at once cost?

PROJECT_PLAN §7 (`MAT-6` step 6) makes this probe the point of no return.  The
combined fixture is ``box_half_width = 0.25`` (step 4's knob) **and**
``resolution_wire = 0.001`` (step 5's knob), projected drive only; the predicted
cell count is ~790 k from the two measured growth factors (366 207 at W = 0.15
fine wire × the 2.17× step-4 W-growth).  The cautionary record is step 5's
1 458 561-cell rung, OOM-killed at ``-n 4`` (signal 9).

Stage 1 meshes and prints the cell count (cheap, no solve).  Stage 2 runs
**one** projected loaded solve and times it.  §7 stop rule: OOM ⇒ one retry of
that single solve at ``-n 8`` (memory per rank halves, cap 12 respected);
still OOM or > 300 s ⇒ report the measured cost and stop — the rescope is a
smaller case, never a raised timeout (§5.1).

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \
       PYTHONPATH=/workspace/src mpiexec -n 4 python3 \
       scripts/probes/mat6_step6_probe.py'
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

# Both knobs at their measured single-knob settings.  Nothing else moves.
BOX_HALF_WIDTH_LARGE = float(os.environ.get("MAT6_STEP6_W", "0.25"))
RESOLUTION_WIRE_FINE = float(os.environ.get("MAT6_STEP6_RES_WIRE", "0.001"))
# Mesh-only mode: skip the solve entirely (stage 1 alone) when the cell count
# is the only question this command should answer.
MESH_ONLY = os.environ.get("MAT6_STEP6_MESH_ONLY", "0") == "1"


def main() -> int:
    comm = MPI.COMM_WORLD
    if np.dtype(PETSc.ScalarType).kind != "c":  # pragma: no cover
        raise SystemExit("probe requires the complex build (dolfinx-complex-mode)")

    if comm.rank == 0:
        print(
            f"[MAT-6 step 6 probe] W = {BOX_HALF_WIDTH_LARGE} m, "
            f"resolution_wire = {RESOLUTION_WIRE_FINE} m "
            f"(r_wire/h = {FEM_WIRE_RADIUS / RESOLUTION_WIRE_FINE:.2f}), "
            f"-n {comm.size}; predicted ~790 k cells",
            flush=True,
        )

    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=BOX_HALF_WIDTH_LARGE,
        resolution_wire=RESOLUTION_WIRE_FINE,
        resolution_near=0.005,
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
            f"[MAT-6 step 6 probe] mesh: {ncells} cells in {t_mesh:.1f} s "
            f"(step 5 fine wire at W = 0.15 was 366207; step 4 coarse wire at "
            f"W = 0.25 was 300591; the OOM rung was 1458561)",
            flush=True,
        )

    if MESH_ONLY:
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
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)

    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[WIRE_TAG],
        # Production default path (solve + CG1 Poisson projection) — the drive
        # the gate uses, and the expensive one.
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    ndofs = fields.e_complex.function_space.dofmap.index_map.size_global
    if comm.rank == 0:
        print(
            f"[MAT-6 step 6 probe] one projected loaded solve: {t_solve:.1f} s "
            f"at -n {comm.size}, {ncells} cells / {ndofs} global dofs",
            flush=True,
        )
        print(
            f"[MAT-6 step 6 probe] budget: the loaded/free pair the gate needs "
            f"costs ~{2 * t_solve:.0f} s + {t_mesh:.0f} s mesh = "
            f"~{2 * t_solve + t_mesh:.0f} s.  §7 stop rule is one solve > 300 s "
            f"at -n 4; the gate ceiling is 1200 s (heavy).",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
