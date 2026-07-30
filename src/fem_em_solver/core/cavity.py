"""PEC rectangular-cavity eigenmodes (TH-9).

A lossless, source-free cavity bounded by a perfect electric conductor is the
purest available check of the curl-curl and mass assembly: the eigenproblem

    ∫ (∇×E)·(∇×v) dx = k² ∫ E·v dx,   n × E = 0 on ∂Ω

is real symmetric — no materials, no sources, no complex scalar type — and its
eigenvalues have a closed form on a box of edges ``a × b × d``:

    f_mnp = (c/2)·√((m/a)² + (n/b)² + (p/d)²)

with at most one of ``m, n, p`` equal to zero. Any sign or scaling error in
either bilinear form moves every eigenvalue, so this gate fails loudly.

Two implementation points that are easy to get wrong:

* **Gradient (null-space) modes.** ``∇×∇φ = 0``, so every discrete gradient is
  an eigenvector with ``k² = 0``. They are physical for the discretisation, not
  numerical noise, and they must be *counted and discarded* against a stated
  cutoff rather than silently skipped — the count is a diagnostic of the N1curl
  null space. See :func:`smallest_cavity_eigenvalues`.
* **Constrained dofs.** The PEC rows are eliminated by assembling ``A`` with a
  large diagonal (``bc_diagonal``, far above the spectrum of interest) and
  ``B`` with unit diagonal. That keeps ``B`` symmetric positive definite — so
  the problem stays a true GHEP — and parks the spurious eigenvalues at
  ``bc_diagonal``, where the cutoff in :func:`solve_pec_cavity_modes` drops
  them.

The shift-and-invert target is derived from the analytic spectrum. That is a
preconditioning choice, not an input to the answer: the returned eigenvalues
are the Rayleigh quotients of the assembled pencil and are compared against the
closed form independently.
"""

from dataclasses import dataclass, field
from typing import Sequence, Tuple

import numpy as np
import ufl
from mpi4py import MPI
from petsc4py import PETSc
from slepc4py import SLEPc

import dolfinx
from dolfinx import fem, mesh as dmesh
from dolfinx.fem.petsc import assemble_matrix

from ..utils.constants import C_0


def analytic_cavity_frequencies(
    edges: Sequence[float],
    n_modes: int,
    max_index: int = 4,
) -> np.ndarray:
    """Closed-form PEC rectangular-cavity resonances, ascending [Hz].

    ``edges`` is ``(a, b, d)``. Modes with two or more zero indices do not
    exist (the field vanishes identically), so they are excluded; degenerate
    modes are returned with their multiplicity, because the solver returns them
    that way too.
    """

    a, b, d = edges
    values = []
    for m in range(max_index + 1):
        for n in range(max_index + 1):
            for p in range(max_index + 1):
                if [m, n, p].count(0) > 1:
                    continue
                values.append(
                    0.5 * C_0 * np.sqrt((m / a) ** 2 + (n / b) ** 2 + (p / d) ** 2)
                )
    values = np.sort(np.asarray(values))
    if values.size < n_modes:
        raise ValueError(
            f"max_index={max_index} yields only {values.size} modes; "
            f"{n_modes} were requested"
        )
    return values[:n_modes]


def frequency_from_eigenvalue(eigenvalue: float) -> float:
    """``k² -> f`` [Hz]. ``k = ω/c``, so ``f = c√(k²)/(2π)``."""

    return C_0 * np.sqrt(max(eigenvalue, 0.0)) / (2.0 * np.pi)


@dataclass
class CavitySpectrum:
    """Result of one cavity eigen-solve."""

    frequencies_hz: np.ndarray
    eigenvalues: np.ndarray
    null_mode_count: int
    null_cutoff: float
    n_converged: int
    n_dofs: int
    n_cells: int
    cell_size: float
    degree: int
    diagnostics: dict = field(default_factory=dict)


def _cavity_forms(V, bc_diagonal: float):
    """Assemble the stiffness/mass pencil with PEC tangential-E constraints."""

    msh = V.mesh
    u = ufl.TrialFunction(V)
    v = ufl.TestFunction(V)

    stiffness = fem.form(ufl.inner(ufl.curl(u), ufl.curl(v)) * ufl.dx)
    mass = fem.form(ufl.inner(u, v) * ufl.dx)

    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    boundary_facets = dmesh.exterior_facet_indices(msh.topology)
    boundary_dofs = fem.locate_dofs_topological(V, tdim - 1, boundary_facets)
    zero = fem.Function(V)
    zero.x.array[:] = 0.0
    bc = fem.dirichletbc(zero, boundary_dofs)

    A = assemble_matrix(stiffness, bcs=[bc], diagonal=bc_diagonal)
    A.assemble()
    B = assemble_matrix(mass, bcs=[bc], diagonal=1.0)
    B.assemble()
    return A, B, boundary_dofs.size


def _solve_pencil(A, B, target: float, nev: int, comm) -> Tuple[np.ndarray, int]:
    """Shift-and-invert GHEP solve; returns (ascending eigenvalues, n_converged)."""

    eps = SLEPc.EPS().create(comm)
    eps.setOperators(A, B)
    eps.setProblemType(SLEPc.EPS.ProblemType.GHEP)
    eps.setWhichEigenpairs(SLEPc.EPS.Which.TARGET_MAGNITUDE)
    eps.setTarget(target)
    eps.setDimensions(nev=nev, ncv=max(4 * nev, 20))
    eps.setTolerances(tol=1e-10, max_it=200)

    st = eps.getST()
    st.setType(SLEPc.ST.Type.SINVERT)
    ksp = st.getKSP()
    ksp.setType("preonly")
    pc = ksp.getPC()
    pc.setType("lu")
    pc.setFactorSolverType("mumps")

    eps.setFromOptions()
    eps.solve()

    n_converged = eps.getConverged()
    values = np.array(
        [np.real(eps.getEigenvalue(i)) for i in range(n_converged)], dtype=float
    )
    eps.destroy()
    return np.sort(values), n_converged


def solve_pec_cavity_modes(
    edges: Sequence[float] = (1.0, 0.8, 0.6),
    divisions: Sequence[int] = (8, 7, 5),
    degree: int = 2,
    n_modes: int = 4,
    comm: MPI.Comm = None,
    null_cutoff_fraction: float = 1e-4,
) -> CavitySpectrum:
    """Solve for the lowest ``n_modes`` physical resonances of a PEC box.

    ``null_cutoff_fraction`` is expressed as a fraction of the analytic
    fundamental ``k²``: eigenvalues below it are gradient (null-space) modes and
    are counted, reported, and discarded.
    """

    comm = MPI.COMM_WORLD if comm is None else comm
    a, b, d = edges
    nx, ny, nz = divisions

    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([a, b, d])],
        [nx, ny, nz],
        cell_type=dmesh.CellType.tetrahedron,
    )
    V = fem.functionspace(msh, ("N1curl", degree))

    analytic = analytic_cavity_frequencies(edges, n_modes)
    lam = (2.0 * np.pi * analytic / C_0) ** 2

    # Park the constrained rows well above the band of interest, and target the
    # middle of that band so every requested physical mode is closer to the
    # shift than the gradient cluster at zero is.
    bc_diagonal = 1.0e4 * lam[-1]
    target = 0.5 * (lam[0] + lam[-1])

    A, B, n_bc = _cavity_forms(V, bc_diagonal)
    values, n_converged = _solve_pencil(A, B, target, nev=n_modes + 4, comm=comm)

    null_cutoff = null_cutoff_fraction * lam[0]
    spurious_cutoff = 0.5 * bc_diagonal
    null_modes = values[values < null_cutoff]
    physical = values[(values >= null_cutoff) & (values < spurious_cutoff)]

    if physical.size < n_modes:
        raise RuntimeError(
            f"only {physical.size} physical eigenvalues converged in the band "
            f"[{null_cutoff:.3e}, {spurious_cutoff:.3e}); requested {n_modes}"
        )
    physical = physical[:n_modes]

    n_dofs = V.dofmap.index_map.size_global * V.dofmap.index_map_bs
    n_cells = msh.topology.index_map(msh.topology.dim).size_global
    cell_size = float(max(a / nx, b / ny, d / nz))

    A.destroy()
    B.destroy()

    return CavitySpectrum(
        frequencies_hz=np.array([frequency_from_eigenvalue(v) for v in physical]),
        eigenvalues=physical,
        null_mode_count=int(null_modes.size),
        null_cutoff=float(null_cutoff),
        n_converged=int(n_converged),
        n_dofs=int(n_dofs),
        n_cells=int(n_cells),
        cell_size=cell_size,
        degree=degree,
        diagnostics={
            "analytic_frequencies_hz": analytic,
            "target_eigenvalue": float(target),
            "bc_diagonal": float(bc_diagonal),
            "n_constrained_dofs_local": int(n_bc),
        },
    )


def smallest_cavity_eigenvalues(
    edges: Sequence[float] = (1.0, 0.8, 0.6),
    divisions: Sequence[int] = (6, 5, 4),
    degree: int = 1,
    n_values: int = 8,
    comm: MPI.Comm = None,
) -> Tuple[np.ndarray, float]:
    """Return the ``n_values`` eigenvalues nearest zero, and the analytic ``k₁²``.

    This is the null-space diagnostic: the gradient modes must come back as a
    cluster at machine zero, cleanly separated from the first physical mode. A
    curl-curl assembly with a sign error, or a mass matrix that is not the plain
    ``L²`` form, generally contaminates this cluster.
    """

    comm = MPI.COMM_WORLD if comm is None else comm
    a, b, d = edges
    nx, ny, nz = divisions

    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([a, b, d])],
        [nx, ny, nz],
        cell_type=dmesh.CellType.tetrahedron,
    )
    V = fem.functionspace(msh, ("N1curl", degree))

    lam_1 = float((2.0 * np.pi * analytic_cavity_frequencies(edges, 1)[0] / C_0) ** 2)
    bc_diagonal = 1.0e4 * lam_1

    A, B, _ = _cavity_forms(V, bc_diagonal)
    # Target just above zero: the gradient cluster is the nearest spectrum.
    values, _ = _solve_pencil(A, B, 1e-6 * lam_1, nev=n_values, comm=comm)
    A.destroy()
    B.destroy()
    return values[:n_values], lam_1
