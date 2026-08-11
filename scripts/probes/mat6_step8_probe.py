"""`MAT-6` step 8 cost probe: what does refining the *slab* cost?

PROJECT_PLAN §7 (`MAT-6` step 8) makes this probe the point of no return.  The
knob is ``resolution_near`` — cell size inside the near box that holds the
ohmic boundary layer — at **fixed** ``resolution_wire = 0.002``,
``resolution_far = 0.025``, ``box_half_width = 0.15`` and fixed near-region
extents.  The landed rung ``resolution_near = 0.005`` gives ~3.2 cells per
skin depth (δ = 15.9 mm at 10 MHz, σ = 100 S/m); the step's target rung
0.0025 gives ~6.4.  The naive bound in the §7 entry is ~8× growth of the near
region's cells against a 138 619-cell baseline.

Stage 1 (``MAT6_STEP8_MESH_ONLY=1``) meshes the ladder and prints cell counts,
cheap and solve-free.  Stage 2 runs **one** projected loaded solve at
``MAT6_STEP8_SOLVE_AT`` and times it.  §7 stop rule: OOM or one solve > 300 s
at ``-n 4`` ⇒ report the measured cost and stop; the rescope is a smaller
refinement ratio (0.005 → 0.0035), never a raised timeout (§5.1).

Run (complex build only, **foreground** — implementer-run.md's allowlist
section: a backgrounded harness call is SIGKILLed when the session's turn
ends)::

    docker compose exec -T fem-em-solver bash -lc \
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \
       PYTHONPATH=/workspace/src mpiexec -n 4 python3 \
       scripts/probes/mat6_step8_probe.py'
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
    FEM_BOX_HALF_WIDTH,
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

# 0.005 is the landed rung; 0.0035 is the §7 rescope rung; 0.0025 is the target.
LADDER = [
    float(v)
    for v in os.environ.get("MAT6_STEP8_LADDER", "0.005,0.0035,0.0025").split(",")
]
SOLVE_AT = float(os.environ.get("MAT6_STEP8_SOLVE_AT", "0.0025"))
MESH_ONLY = os.environ.get("MAT6_STEP8_MESH_ONLY", "0") == "1"
# Skin depth at the step-2b fixture's 10 MHz / 100 S/m, for cells-per-δ.
SKIN_DEPTH_M = 0.0159


def _mesh(comm, resolution_near):
    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=0.002,
        resolution_near=resolution_near,
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
    return msh, cell_tags, float(t_mesh), int(ncells)


def main() -> int:
    comm = MPI.COMM_WORLD
    if np.dtype(PETSc.ScalarType).kind != "c":  # pragma: no cover
        raise SystemExit("probe requires the complex build (dolfinx-complex-mode)")

    if comm.rank == 0:
        print(
            f"[MAT-6 step 8 probe] W = {FEM_BOX_HALF_WIDTH} m, "
            f"resolution_wire = 0.002 m fixed; sweeping resolution_near "
            f"{LADDER} at -n {comm.size}; baseline 138619 cells at 0.005",
            flush=True,
        )

    meshed = {}
    for h in LADDER:
        msh, cell_tags, t_mesh, ncells = _mesh(comm, h)
        meshed[h] = (msh, cell_tags, ncells)
        if comm.rank == 0:
            print(
                f"[MAT-6 step 8 probe] resolution_near = {h:g} m "
                f"({SKIN_DEPTH_M / h:.2f} cells per skin depth): {ncells} cells, "
                f"{ncells / 138619:.2f}x the landed mesh, meshed in {t_mesh:.1f} s "
                f"on {comm.size} ranks",
                flush=True,
            )

    if MESH_ONLY:
        if comm.rank == 0:
            print("[MAT-6 step 8 probe] mesh-only mode: no solve", flush=True)
        return 0

    if SOLVE_AT not in meshed:
        if comm.rank == 0:
            print(
                f"[MAT-6 step 8 probe] no solve: {SOLVE_AT:g} was not meshed",
                flush=True,
            )
        return 0

    msh, cell_tags, ncells = meshed[SOLVE_AT]
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
        # Production default path (solve + CG1 Poisson projection): the
        # expensive one, and the only drive step 8 gates.
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    ndofs = fields.e_complex.function_space.dofmap.index_map.size_global
    if comm.rank == 0:
        print(
            f"[MAT-6 step 8 probe] one projected loaded solve at "
            f"resolution_near = {SOLVE_AT:g}: {t_solve:.1f} s at -n {comm.size}, "
            f"{ncells} cells / {ndofs} global dofs",
            flush=True,
        )
        print(
            f"[MAT-6 step 8 probe] budget: the gate's loaded/free pair costs "
            f"~{2 * t_solve:.0f} s + mesh.  §7 stop rule is one solve > 300 s "
            f"at -n 4.",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
