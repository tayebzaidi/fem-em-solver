"""`MAT-6` step 4 cost probe: what does the W = 0.25 box actually cost?

PROJECT_PLAN §7 (`MAT-6` step 4) requires a mesh + single-solve cost probe
before any tier is committed to: W = 0.15 is 138 619 cells at 24-28 s per solve
at ``-n 2``, and W = 0.25 scales the box volume ~4.6x, so the expectation is
~600 k cells and *minutes* per MUMPS solve.  If one solve exceeds ~300 s at
``-n 4`` the adjudication does not happen this way at all: the rescope is
``h/r_wire >= 16`` local refinement, never a raised timeout (§5.1).

The fixture is *imported* from ``test_dodd_deeds_impedance.py`` (step 3's
method) so there is exactly one definition of the geometry, the current density
and the tags; only ``box_half_width`` moves.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \
       PYTHONPATH=/workspace/src mpiexec -n 4 python3 \
       scripts/probes/mat6_step4_probe.py'
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

W_PROBE = float(os.environ.get("MAT6_STEP4_W", "0.25"))


def main() -> int:
    comm = MPI.COMM_WORLD
    if np.dtype(PETSc.ScalarType).kind != "c":  # pragma: no cover
        raise SystemExit("probe requires the complex build (dolfinx-complex-mode)")

    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=W_PROBE,
        resolution_wire=0.002,
        resolution_near=0.005,
        resolution_far=0.025,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    comm.Barrier()
    t_mesh = time.perf_counter() - t0
    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    ndofs_note = "Nedelec degree 1 on tets: ~ #edges"

    if comm.rank == 0:
        print(
            f"[MAT-6 step 4 probe] W = {W_PROBE} m: {ncells} cells meshed in "
            f"{t_mesh:.1f} s on {comm.size} ranks ({ndofs_note})",
            flush=True,
        )

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
        # The production default path, i.e. the expensive one (solve + CG1
        # Poisson projection); the pinned path is strictly cheaper.
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    ndofs = fields.e_complex.function_space.dofmap.index_map.size_global
    if comm.rank == 0:
        print(
            f"[MAT-6 step 4 probe] one projected loaded solve: {t_solve:.1f} s "
            f"at -n {comm.size}, {ndofs} global dofs",
            flush=True,
        )
        print(
            f"[MAT-6 step 4 probe] budget: a loaded/free pair costs "
            f"~{2 * t_solve:.0f} s + {t_mesh:.0f} s mesh; four solves "
            f"~{4 * t_solve:.0f} s.  §7 stop rule is one solve > 300 s at -n 4.",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
