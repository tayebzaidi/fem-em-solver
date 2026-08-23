"""`POST-3` step 3: total-current divergence residual.

Ampère's law for ``e^{+jωt}`` phasors is ``∇×H = J_imp + (σ + jωε₀εᵣ)E``, and
the divergence of a curl vanishes, so **outside any impressed source** the
total (conduction + displacement) current is divergence free:

    ∇·J_tot = 0,   J_tot = (σ(x) + jωε₀εᵣ(x)) E

Two things about this identity are easy to get wrong and are the whole design
of this module:

**It is on the total current, not on ``σE``.**  ``∇·(σE)`` is legitimately
nonzero across a conductivity interface — that is surface charge accumulating —
so scoring the residual on the conduction current alone would fail a piecewise-σ
solve for physics reasons.  The displacement term is what closes it.

**The residual must be measured against a space the solve does not already
enforce it in.**  The discrete curl-curl form tested against ``w = ∇φ`` with
``φ ∈ CG1`` vanishing on the wall has ``∇×w = 0``, and ``∇(CG1) ⊂ N1curl₁``, so
``∫ ε_c E·∇φ̄ dV`` reproduces the source term *identically by Galerkin
orthogonality*.  A CG1-weak residual is enforced, not emergent, and can never
fail — exactly the vacuous-metric class `POST-3` exists to remove.  The default
here is therefore ``degree = 2``: ``∇(CG2) ⊄ N1curl₁``, so the residual is a
genuine statement about the solved field.  ``degree = 1`` is kept reachable so
a test can *demonstrate* the vacuity rather than assert it in prose.

The number reported is the dual norm of the weak residual, normalised so it is
dimensionless and bounded by 1.  With ``V_0`` the degree-``p`` Lagrange space
whose members vanish on the boundary,

    R(v) = ∫ J_tot·∇v̄ dV,    ‖R‖ = sup_{v ∈ V_0} |R(v)| / ‖∇v‖_{L²}

and ``relative_residual = ‖R‖ / ‖J_tot‖_{L²}``, which Cauchy-Schwarz bounds by
1.  The supremum is computed exactly, not estimated: the Riesz representer
``φ ∈ V_0`` of ``R`` under the ``∫∇u·∇v̄`` inner product solves a Poisson
problem, and ``‖R‖ = ‖∇φ‖_{L²}``.  The boundary integral from integrating by
parts drops because ``v`` vanishes there, so no assumption is made about
``J_tot·n̂`` on the wall.

``fem.assemble_scalar`` is rank-local; every integral here is reduced across
``comm`` before it is used.
"""

from __future__ import annotations

from typing import Mapping, Optional, Union

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import fem, mesh as dmesh

from ..utils.constants import EPSILON_0

# CG + algebraic multigrid on a scalar Poisson problem.  `preonly`/LU (what the
# curl-curl solver uses) is not affordable here: the CG2 space on the 32³ gate
# mesh carries ~275k dofs and the operator is SPD, so AMG is both cheaper and
# the natural choice.  rtol is well below the residual levels being measured.
# `gamg`, not `hypre`: BoomerAMG setup aborts this image's MPI inside
# hypre_ParCSRCommHandleDestroy ("double free or corruption", SIGABRT at 6³ on
# two ranks — log 20260802T200303Z_POST-3-step3-probe.log), so hypre is unusable
# here regardless of mesh size.
_DEFAULT_PETSC_OPTIONS: dict[str, object] = {
    "ksp_type": "cg",
    "pc_type": "gamg",
    "ksp_rtol": 1.0e-12,
    "ksp_atol": 1.0e-50,
    "ksp_max_it": 500,
}


def current_divergence_residual(
    e_complex: fem.Function,
    *,
    omega: float,
    sigma: Union[float, fem.Function],
    epsilon_r: Union[float, fem.Function],
    degree: int = 2,
    include_sigma: bool = True,
    comm: Optional[MPI.Comm] = None,
    petsc_options: Optional[Mapping[str, object]] = None,
) -> dict[str, float]:
    """Dual norm of the weak ``∇·J_tot = 0`` residual for a time-harmonic solve.

    Parameters
    ----------
    e_complex:
        The solved complex ``E`` phasor (N1curl), as produced by
        :class:`~fem_em_solver.core.TimeHarmonicSolver`.
    omega:
        Angular frequency in rad/s.
    sigma, epsilon_r:
        Material properties, each either a uniform scalar or the DG0 field the
        solver builds (:func:`~fem_em_solver.core.build_material_fields`).  A
        field must live on the same mesh as ``e_complex``.
    degree:
        Lagrange degree of the test space the residual is measured against.
        ``2`` (the default) is the only value that measures anything: at
        ``1`` the residual is enforced by Galerkin orthogonality against a
        degree-1 N1curl solve and is round-off by construction.  See the
        module docstring.
    include_sigma:
        Drop the conduction current from ``J_tot`` when ``False``, leaving
        ``jωε₀εᵣE``.  This is the negative control — the σ interface then has
        no term to cancel its displacement-current jump — and is never what a
        real diagnostic wants.
    comm:
        Communicator to reduce over; defaults to the mesh's own.

    Returns
    -------
    dict with ``residual_dual_norm`` (``sup |R(v)|/‖∇v‖``, units A·m),
    ``current_scale`` (``‖J_tot‖_{L²}``, same units), ``relative_residual``
    (their ratio, dimensionless and ≤ 1), ``degree`` and ``ksp_iterations``.
    """
    if degree < 1:
        raise ValueError(f"degree must be >= 1, got {degree}")

    msh = e_complex.function_space.mesh
    if comm is None:
        comm = msh.comm

    for name, prop in (("sigma", sigma), ("epsilon_r", epsilon_r)):
        if isinstance(prop, fem.Function):
            if prop.function_space.mesh is not msh:
                raise ValueError(
                    f"{name} field and e_complex must live on the same mesh; got "
                    "functions from two different meshes, which would silently "
                    "score one material distribution against another field"
                )
        elif not np.isfinite(float(prop)) or float(prop) < 0.0:
            raise ValueError(f"{name} must be finite and non-negative, got {prop!r}")

    sigma_ufl: object = sigma if isinstance(sigma, fem.Function) else float(sigma)
    eps_ufl: object = (
        epsilon_r if isinstance(epsilon_r, fem.Function) else float(epsilon_r)
    )

    # J_tot = (σ + jωε₀εᵣ)E — written as the current rather than as ε_c so the
    # conduction term can be dropped for the negative control without also
    # rescaling the displacement term.
    admittivity = 1j * omega * EPSILON_0 * eps_ufl
    if include_sigma:
        admittivity = sigma_ufl + admittivity
    j_tot = admittivity * e_complex

    space = fem.functionspace(msh, ("Lagrange", degree))
    u = ufl.TrialFunction(space)
    v = ufl.TestFunction(space)

    # Riesz representer of R(v) = ∫ J_tot·∇v̄ dV under ∫∇u·∇v̄, over the
    # subspace vanishing on the boundary.  ‖∇φ‖ is then the dual norm exactly.
    a = ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
    rhs = ufl.inner(j_tot, ufl.grad(v)) * ufl.dx

    msh.topology.create_connectivity(msh.topology.dim - 1, msh.topology.dim)
    boundary_facets = dmesh.exterior_facet_indices(msh.topology)
    boundary_dofs = fem.locate_dofs_topological(
        space, msh.topology.dim - 1, boundary_facets
    )
    zero = fem.Function(space)
    zero.x.array[:] = 0.0
    bc = fem.dirichletbc(zero, boundary_dofs)

    options = dict(_DEFAULT_PETSC_OPTIONS)
    if petsc_options:
        options.update(dict(petsc_options))

    from dolfinx.fem.petsc import LinearProblem  # local: needs a PETSc build

    problem = LinearProblem(
        a,
        rhs,
        bcs=[bc],
        petsc_options=options,
        petsc_options_prefix="fem_em_current_divergence_",
    )
    phi = problem.solve()
    iterations = int(problem.solver.getIterationNumber())

    dual_sq = comm.allreduce(
        fem.assemble_scalar(
            fem.form(ufl.inner(ufl.grad(phi), ufl.grad(phi)) * ufl.dx)
        ),
        op=MPI.SUM,
    )
    scale_sq = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(j_tot, j_tot) * ufl.dx)),
        op=MPI.SUM,
    )

    dual_norm = float(np.sqrt(max(float(np.real(dual_sq)), 0.0)))
    current_scale = float(np.sqrt(max(float(np.real(scale_sq)), 0.0)))
    relative = dual_norm / current_scale if current_scale > 0.0 else float("inf")

    return {
        "residual_dual_norm": dual_norm,
        "current_scale": current_scale,
        "relative_residual": float(relative),
        "degree": int(degree),
        "ksp_iterations": iterations,
    }
