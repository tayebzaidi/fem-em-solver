"""`MAT-6` step 5 cost probe: what does refining the *wire* cost at fixed box?

PROJECT_PLAN §7 (`MAT-6` step 5) requires a mesh + single-solve cost probe
before a tier is committed to.  The knob is ``resolution_wire`` at fixed
``box_half_width = 0.15`` and fixed ``resolution_near/far`` — step 2b's
"``h/r_wire >= 16``" target, read as cells across the wire *radius*:
``r_wire = 0.0025`` m, so the landed ``resolution_wire = 0.002`` gives
``r_wire/h = 1.25`` and the target needs ``h <= 1.5625e-4`` m.

The geometry is *not* moved — ``FEM_WIRE_RADIUS`` stays 0.0025 m so that
``_solve_loop``/``_solve_projected``/``_reaction_impedance`` (which hard-code
the current density from it) are importable verbatim and the only difference
from the recorded W = 0.15 numbers is the mesh.

Stage 1 meshes the ladder and prints cell counts (cheap, no solve).  Stage 2
solves once at the finest rung whose cell count is under the ceiling the §7
stop rule implies.  §7 stop rule: one solve > ~300 s at ``-n 4`` ⇒ report the
measured cost and stop; the rescope is a smaller ``h/r_wire``, never a raised
timeout (§5.1).

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \
       PYTHONPATH=/workspace/src mpiexec -n 4 python3 \
       scripts/probes/mat6_step5_probe.py'
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

# The landed rung is 0.002 (r_wire/h = 1.25).  The ladder doubles the wire
# resolution twice; 1.5625e-4 (the literal h/r_wire >= 16 target) is only
# meshed if the cheaper rungs say it is affordable.
LADDER = [float(v) for v in os.environ.get("MAT6_STEP5_LADDER", "0.002,0.001,0.0005").split(",")]
SOLVE_AT = float(os.environ.get("MAT6_STEP5_SOLVE_AT", "0.0005"))
CELL_CEILING = int(os.environ.get("MAT6_STEP5_CELL_CEILING", "400000"))


def _mesh(comm, resolution_wire):
    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=resolution_wire,
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
    return msh, cell_tags, float(t_mesh), int(ncells)


def main() -> int:
    comm = MPI.COMM_WORLD
    if np.dtype(PETSc.ScalarType).kind != "c":  # pragma: no cover
        raise SystemExit("probe requires the complex build (dolfinx-complex-mode)")

    if comm.rank == 0:
        print(
            f"[MAT-6 step 5 probe] W = {FEM_BOX_HALF_WIDTH} m fixed, "
            f"r_wire = {FEM_WIRE_RADIUS} m fixed; sweeping resolution_wire",
            flush=True,
        )

    meshed = {}
    for h in LADDER:
        msh, cell_tags, t_mesh, ncells = _mesh(comm, h)
        meshed[h] = (msh, cell_tags, ncells)
        if comm.rank == 0:
            print(
                f"[MAT-6 step 5 probe] resolution_wire = {h:g} m "
                f"(r_wire/h = {FEM_WIRE_RADIUS / h:.2f}): {ncells} cells, "
                f"meshed in {t_mesh:.1f} s on {comm.size} ranks",
                flush=True,
            )
        if ncells > CELL_CEILING:
            if comm.rank == 0:
                print(
                    f"[MAT-6 step 5 probe] {ncells} cells exceeds the "
                    f"{CELL_CEILING} ceiling — ladder stops here",
                    flush=True,
                )
            break

    if SOLVE_AT not in meshed:
        if comm.rank == 0:
            print(
                f"[MAT-6 step 5 probe] no solve: {SOLVE_AT:g} was not meshed",
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
        # expensive one.  The pinned path is strictly cheaper.
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    ndofs = fields.e_complex.function_space.dofmap.index_map.size_global
    if comm.rank == 0:
        print(
            f"[MAT-6 step 5 probe] one projected loaded solve at "
            f"resolution_wire = {SOLVE_AT:g}: {t_solve:.1f} s at -n {comm.size}, "
            f"{ncells} cells / {ndofs} global dofs",
            flush=True,
        )
        print(
            f"[MAT-6 step 5 probe] budget: a loaded/free pair costs "
            f"~{2 * t_solve:.0f} s + mesh; four solves ~{4 * t_solve:.0f} s.  "
            f"§7 stop rule is one solve > 300 s at -n 4.",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
