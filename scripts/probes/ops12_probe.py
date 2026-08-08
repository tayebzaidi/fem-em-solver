"""`OPS-12` probe: which KSP configuration lets the diagnostics fixture converge?

The `test_time_harmonic_solver_emits_optional_solve_health_diagnostics` fixture
asserts `diagnostics.converged` while requesting gmres + jacobi with
`ksp_max_it = 300`; on record that stalls at `converged_reason = -3`
(`KSP_DIVERGED_ITS`) with 300 iterations and `residual_norm = 1.4999e-06`. The
assertion is a claim about the *fixture's* solver options, not about the
diagnostics contract under test, so the fix is to give the fixture a
configuration that genuinely converges rather than to drop the assertion.

This probe re-solves the same fixture under a few candidate option sets and
prints, for each: converged reason, iteration count, residual norm, the length
of the collected convergence history, and the trend label. Run under the
complex build.
"""

from __future__ import annotations

import time

import ufl
from mpi4py import MPI

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator

CANDIDATES = {
    "gmres+jacobi (on record, max_it 300)": {
        "ksp_type": "gmres",
        "pc_type": "jacobi",
        "ksp_rtol": 1e-8,
        "ksp_max_it": 300,
    },
    "gmres+jacobi, max_it 5000": {
        "ksp_type": "gmres",
        "pc_type": "jacobi",
        "ksp_rtol": 1e-8,
        "ksp_max_it": 5000,
    },
    "gmres+bjacobi/ilu, max_it 1000": {
        "ksp_type": "gmres",
        "pc_type": "bjacobi",
        "sub_pc_type": "ilu",
        "ksp_rtol": 1e-8,
        "ksp_max_it": 1000,
    },
    "gmres+lu/mumps, max_it 1000": {
        "ksp_type": "gmres",
        "pc_type": "lu",
        "pc_factor_mat_solver_type": "mumps",
        "ksp_rtol": 1e-8,
        "ksp_max_it": 1000,
    },
}


def current_density(_x):
    return ufl.as_vector([0.0, 0.0, 1.0])


def main() -> None:
    comm = MPI.COMM_WORLD

    mesh, cell_tags, facet_tags = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )
    n_cells = comm.allreduce(
        mesh.topology.index_map(mesh.topology.dim).size_local, op=MPI.SUM
    )
    if comm.rank == 0:
        print(f"[probe] fixture mesh: {n_cells} cells", flush=True)

    for label, options in CANDIDATES.items():
        problem = TimeHarmonicProblem(
            mesh=mesh,
            frequency_hz=127.74e6,
            material=HomogeneousMaterial(sigma=0.7, epsilon_r=78.0, mu_r=1.0),
            cell_tags=cell_tags,
            facet_tags=facet_tags,
            solver_petsc_options=options,
            collect_solver_diagnostics=True,
        )
        solver = TimeHarmonicSolver(problem, degree=1)

        t0 = time.perf_counter()
        fields = solver.solve(
            current_density=current_density, subdomain_id=1, gauge_penalty=1e-3
        )
        elapsed = time.perf_counter() - t0

        d = fields.solve_diagnostics
        if comm.rank == 0:
            print(
                f"[probe] {label}: reason={d.converged_reason} "
                f"converged={d.converged} its={d.iterations} "
                f"resid={d.residual_norm:.6e} history_len={len(d.residual_history)} "
                f"trend={d.residual_trend} elapsed={elapsed:.2f}s",
                flush=True,
            )


if __name__ == "__main__":
    main()
