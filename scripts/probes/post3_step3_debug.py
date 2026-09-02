"""Minimal isolation of the `POST-3` step-3 Poisson dual-norm solve."""

from __future__ import annotations

import sys

import numpy as np
import ufl
from mpi4py import MPI
from dolfinx import fem, mesh as dmesh
from dolfinx.fem.petsc import LinearProblem


def say(*a):
    if MPI.COMM_WORLD.rank == 0:
        print(*a)
        sys.stdout.flush()


comm = MPI.COMM_WORLD
msh = dmesh.create_box(
    comm,
    [np.array([0.0, 0.0, 0.0]), np.array([1.0, 1.0, 1.0])],
    [6, 6, 6],
    cell_type=dmesh.CellType.tetrahedron,
)
say("mesh ok")

nc = fem.functionspace(msh, ("N1curl", 1))
e = fem.Function(nc)
e.interpolate(lambda x: np.array([x[1] + 0j, x[2] + 0j, x[0] + 0j]))
say("field ok")

space = fem.functionspace(msh, ("Lagrange", 2))
u, v = ufl.TrialFunction(space), ufl.TestFunction(space)
a = ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
rhs = ufl.inner((0.1 + 1j) * e, ufl.grad(v)) * ufl.dx
say("forms ok")

msh.topology.create_connectivity(msh.topology.dim - 1, msh.topology.dim)
facets = dmesh.exterior_facet_indices(msh.topology)
dofs = fem.locate_dofs_topological(space, msh.topology.dim - 1, facets)
zero = fem.Function(space)
zero.x.array[:] = 0.0
bc = fem.dirichletbc(zero, dofs)
say("bc ok", dofs.size)

for opts in (
    {"ksp_type": "cg", "pc_type": "hypre", "pc_hypre_type": "boomeramg", "ksp_rtol": 1e-12},
    {"ksp_type": "cg", "pc_type": "gamg", "ksp_rtol": 1e-12},
    {"ksp_type": "preonly", "pc_type": "lu"},
):
    say("trying", opts)
    try:
        problem = LinearProblem(
            a,
            rhs,
            bcs=[bc],
            petsc_options_prefix="fem_em_probe_post3_step3_",
            petsc_options=opts,
        )
        phi = problem.solve()
        its = problem.solver.getIterationNumber()
        val = comm.allreduce(
            fem.assemble_scalar(fem.form(ufl.inner(ufl.grad(phi), ufl.grad(phi)) * ufl.dx)),
            op=MPI.SUM,
        )
        say("   ok:", its, "its, dual^2 =", val)
    except Exception as exc:  # noqa: BLE001
        say("   FAILED:", type(exc).__name__, exc)
say("done")
