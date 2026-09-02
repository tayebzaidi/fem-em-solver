"""``B`` from a time-harmonic ``E``, and the rotating component ``B₁⁺``.

Faraday's law in the frequency domain, ``∇×E = −jωB``, is the only route from
the solved N1curl phasor to a magnetic field; ``B`` lands on DG0, the natural
home of a curl of an N1curl field (`WF-6` step 1, 2026-08-29 — lifted from the
private copies `examples/ports/04` and `examples/ports/05` each carried).

``B₁⁺`` is the circularly polarised component that rotates *with* the nuclear
precession — the one an MRI transmit coil is judged on.  In the peak-phasor
convention the solver works in, it is ``|B_x + jB_y|/2``.

The DG0 field is the *raw* curl and stays that way.  For anything that reads
``B`` at points — a map, a gate, an example — go through
:func:`project_to_cg1` first: the 2026-08-30 weekly review's `WF-6` ruling made
the L²-projected CG1 field the production estimator, on the measurement that
the DG0 cell scatter alone misses the C4 covariance identity by 8.6516 /
9.5808 / 8.5970% where CG1 reads 2.1870 / 2.1146 / 1.8911% (steps 1b and 1c).
"""

from __future__ import annotations

import numpy as np
import ufl
from dolfinx import fem
from mpi4py import MPI

__all__ = [
    "magnetic_flux_density_from_e",
    "b1_plus",
    "b1_minus",
    "project_to_cg1",
    "project_to_cg1_restricted",
]


def _require_complex(function, what: str) -> None:
    if not np.iscomplexobj(np.asarray(function.x.array)):
        raise ValueError(
            f"{what} needs the complex DolfinX build: the field handed in has "
            f"dtype {np.asarray(function.x.array).dtype}, and ∇×E/(−jω) is not "
            "representable in real mode (source /usr/local/bin/dolfinx-complex-mode)"
        )


def magnetic_flux_density_from_e(e_complex, omega_rad_per_s, *, name: str = "B_phasor"):
    """``B = ∇×E / (−jω)`` as a DG0 vector ``Function`` on ``e_complex``'s mesh.

    ``e_complex`` is the solved phasor (N1curl, peak convention);
    ``omega_rad_per_s`` is ``2πf``.  The result is ghost-updated, so a caller
    may read ``x.array`` on any rank.
    """
    omega = float(omega_rad_per_s)
    if not np.isfinite(omega) or omega <= 0.0:
        raise ValueError(f"omega_rad_per_s must be finite and positive, got {omega_rad_per_s!r}")
    _require_complex(e_complex, "magnetic_flux_density_from_e")

    msh = e_complex.function_space.mesh
    w_dg = fem.functionspace(msh, ("DG", 0, (3,)))
    b_fn = fem.Function(w_dg, name=name)
    b_fn.interpolate(
        fem.Expression(
            ufl.curl(e_complex) / (-1j * omega), w_dg.element.interpolation_points
        )
    )
    b_fn.x.scatter_forward()
    return b_fn


def project_to_cg1(
    b_dg0,
    *,
    name: str = "B_phasor_cg1",
    ksp_rtol: float = 1.0e-12,
    return_diagnostics: bool = False,
):
    """L² projection of the DG0 vector phasor onto ``("Lagrange", 1, (3,))``.

    A mass-matrix solve, never ``interpolate``: a DG0 field has no vertex value,
    so interpolating it into CG1 picks whichever incident cell the interpolation
    machinery visits last, which is neither the cell average nor reproducible.
    The mass matrix is Hermitian positive definite in the complex build, so CG
    with Jacobi is the right solver; ``ksp_rtol`` defaults well below any
    difference a covariance or homogeneity reading is trying to measure.

    Landed by `WF-6` step 1d (2026-08-30) out of step 1b's fixture, where it was
    the estimator that took the C4 covariance mismatch from ~9% to ~2%.  The
    caller forms ``|B_x + jB_y|/2`` from the *evaluated* projection, not from a
    projected scalar — ``|·|`` is not linear.

    ``return_diagnostics`` (opt-in, default off so every existing ``B`` caller is
    untouched) returns ``(projected, diagnostics)`` instead of the bare
    ``Function``, where ``diagnostics`` carries the mass solve's PETSc
    ``converged_reason`` and ``iterations``.  The helper otherwise *discards* its
    solver, so a silently non-converged mass solve would look exactly like a
    converged one — `WF-6` step 3c (2026-09-01) added this to tell those two
    apart on an N1curl input.  A positive reason is convergence
    (``KSP_CONVERGED_RTOL`` is 2); ``-3`` is ``DIVERGED_ITS``.

    .. warning::

       This is a **global** L² fit, and a global L² fit is *not* a field
       estimator inside a low-field subdomain of a fixture that also carries a
       high-field region.  `WF-6` step 3c (2026-09-01) measured the domain
       table on the loaded birdcage's ``E``: ``‖P E − E‖/‖E‖`` reads
       **32.7802%** over the whole mesh but **1876.1871%** over the phantom
       (and 838.8978% over the phantom core), because ``‖E‖`` lives on the
       lumped sheets and the conductor edges and the phantom — orders of
       magnitude lower ``|E|`` — receives only that fit's tail.  The projector
       itself is sound (step 3c: ``a + b × x`` reproduced to 1.326607e-13,
       mass solve reason 2 in 26 its); the *use* is what fails.  To read a
       field over a subdomain, use :func:`project_to_cg1_restricted`, which
       leaves 18.7238% on that same phantom.  ``B`` callers are unaffected:
       they project on the whole mesh, where no comparable field-magnitude
       contrast exists, and the projection moves ``|B₁⁺|`` by 0.38%.
    """
    from dolfinx.fem.petsc import LinearProblem  # local: needs a PETSc build

    _require_complex(b_dg0, "project_to_cg1")
    if b_dg0.function_space.element.value_shape != (3,):
        raise ValueError(
            "project_to_cg1 wants the 3-vector B phasor, got value shape "
            f"{b_dg0.function_space.element.value_shape}"
        )

    msh = b_dg0.function_space.mesh
    space = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    trial, test = ufl.TrialFunction(space), ufl.TestFunction(space)
    problem = LinearProblem(
        ufl.inner(trial, test) * ufl.dx,
        ufl.inner(b_dg0, test) * ufl.dx,
        bcs=[],
        petsc_options={
            "ksp_type": "cg",
            "pc_type": "jacobi",
            "ksp_rtol": float(ksp_rtol),
            "ksp_atol": 1.0e-30,
        },
        petsc_options_prefix="fem_em_b_cg1_mass_",
    )
    projected = problem.solve()
    projected.name = name
    projected.x.scatter_forward()
    if return_diagnostics:
        ksp = problem.solver
        return projected, {
            "converged_reason": int(ksp.getConvergedReason()),
            "iterations": int(ksp.getIterationNumber()),
            "ksp_rtol": float(ksp_rtol),
            "dofs": int(space.dofmap.index_map.size_global * space.dofmap.index_map_bs),
        }
    return projected


def project_to_cg1_restricted(
    field,
    cell_tags,
    *,
    name: str,
    tag: int,
    degree: int = 1,
    ksp_rtol: float = 1.0e-12,
    return_diagnostics: bool = False,
):
    """L² projection onto ``CG1³`` **restricted to a tagged subdomain**.

    The sibling of :func:`project_to_cg1` — same ``("Lagrange", 1, (3,))``
    space, same CG + Jacobi at ``ksp_rtol`` 1e-12, same opt-in diagnostics —
    differing in exactly one thing: both the mass matrix and the load are
    integrated over ``dx(tag)`` instead of ``dx``, so the fit minimises
    ``‖· − field‖`` over the tagged cells alone and cannot be dragged by
    whatever dominates the global norm outside them.  ``field`` may be any
    vector field the forms can integrate — the N1curl ``E`` phasor included,
    which is what it was built for.

    Everything stays on the **parent** mesh: no submesh, and therefore no
    cross-mesh N1curl interpolation.  The restricted mass matrix is singular on
    every dof with no tagged-cell support (an all-zero row), so those dofs are
    pinned to zero by a ``dirichletbc``, which makes the assembled matrix
    identity there and leaves it SPD overall.  Three traps live in that one
    sentence, all paid for by `WF-6` step 3d:

    * ``locate_dofs_topological`` on a **blocked** space returns *block*
      indices, so the bc is built from a zero ``fem.Function`` on the space
      (which dolfinx indexes by block) and never from a scalar ``Constant``.
    * the complement is taken over ``size_local + num_ghosts`` blocks.  Over
      owned blocks only, a ghost row on the far side of a partition cut goes
      unpinned and the two-rank answer differs from the one-rank one.
    * ``cell_tags.find`` is rank-local and returns the local view *including
      ghost cells*; that is what is wanted here, since a tagged cell ghosted
      onto this rank still supports dofs this rank owns.

    Landed by `WF-6` step 3d (2026-09-01) as a test-local helper and promoted
    here by step 3e on its measurements: on the loaded birdcage's phantom it
    leaves ``‖P_Ω E − E‖_Ω/‖E‖_Ω`` = **18.7238%** against the global fit's
    **1876.1871%** over the same cells (a 100.20× separation of the
    best-approximation inequality), and reproduces the primal phantom power to
    **−3.51%** (5.440097168e-08 W vs 5.637745667e-08 W) where the global fit
    reads +35 198.9%.  It is an *estimator*, not a gate: no SAR claim rests on
    it.

    ``return_diagnostics`` (opt-in, default off, matching
    :func:`project_to_cg1`) returns ``(projected, diagnostics)`` with the mass
    solve's PETSc ``converged_reason`` and ``iterations``, the global dof
    count, the globally reduced free/pinned owned-block counts, and
    ``pinned_max_abs`` — the max ``|value|`` left on a pinned block, reduced
    over all ranks, which ``set_bc`` writes as an exact zero and which is
    therefore a defect indicator, not a tolerance.

    ``degree`` selects the Lagrange degree of the target space (default **1**,
    so every caller and every record predating `WF-6` step 3e′ is untouched).
    ``degree=2`` fits the same field over the same cells in ``CG2³``; because
    ``CG1³ ⊂ CG2³`` on one mesh, the restricted residual it leaves cannot
    *exceed* the ``degree=1`` residual on the same input — that inequality is
    a theorem about this function, and step 3e′ asserts it.  Everything else
    (the pinning of unsupported blocks, the ghost-inclusive complement, the
    solver and its prefix) is degree-independent; the space and the bc's zero
    ``Function`` are both built from ``degree``, so no CG1 object leaks into a
    CG2 solve.
    """
    from dolfinx.fem.petsc import LinearProblem  # local: needs a PETSc build

    msh = field.function_space.mesh
    comm = msh.comm
    tdim = msh.topology.dim
    if int(degree) < 1:
        raise ValueError(f"project_to_cg1_restricted wants degree >= 1, got {degree}")
    space = fem.functionspace(msh, ("Lagrange", int(degree), (3,)))
    trial, test = ufl.TrialFunction(space), ufl.TestFunction(space)
    dx_tag = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)(tag)

    cells = np.sort(np.asarray(cell_tags.find(tag), dtype=np.int32))
    supported = np.asarray(
        fem.locate_dofs_topological(space, tdim, cells), dtype=np.int32
    )
    imap = space.dofmap.index_map
    n_blocks = int(imap.size_local + imap.num_ghosts)
    pinned = np.setdiff1d(np.arange(n_blocks, dtype=np.int32), supported)

    zero = fem.Function(space, name=f"{name}_zero")
    zero.x.array[:] = 0.0
    bc = fem.dirichletbc(zero, pinned)

    problem = LinearProblem(
        ufl.inner(trial, test) * dx_tag,
        ufl.inner(field, test) * dx_tag,
        bcs=[bc],
        petsc_options={
            "ksp_type": "cg",
            "pc_type": "jacobi",
            "ksp_rtol": float(ksp_rtol),
            "ksp_atol": 1.0e-30,
        },
        petsc_options_prefix="fem_em_restricted_cg1_mass_",
    )
    projected = problem.solve()
    projected.name = name
    projected.x.scatter_forward()

    if not return_diagnostics:
        return projected

    ksp = problem.solver
    owned = int(imap.size_local)
    blocks = np.asarray(projected.x.array).reshape(-1, 3)
    pinned_max = comm.allreduce(
        float(np.max(np.abs(blocks[pinned]))) if pinned.size else 0.0, op=MPI.MAX
    )
    diagnostics = {
        "converged_reason": int(ksp.getConvergedReason()),
        "iterations": int(ksp.getIterationNumber()),
        "ksp_rtol": float(ksp_rtol),
        "degree": int(degree),
        "dofs": int(imap.size_global * space.dofmap.index_map_bs),
        "free_blocks": comm.allreduce(
            int(supported[supported < owned].size), op=MPI.SUM
        ),
        "pinned_blocks": comm.allreduce(int(pinned[pinned < owned].size), op=MPI.SUM),
        "pinned_max_abs": pinned_max,
    }
    return projected, diagnostics


def _rotating_component(b_complex, sign: float, what: str, name: str):
    _require_complex(b_complex, what)
    msh = b_complex.function_space.mesh
    if b_complex.function_space.element.value_shape != (3,):
        raise ValueError(
            f"{what} wants the 3-vector B phasor, got value shape "
            f"{b_complex.function_space.element.value_shape}"
        )

    s_dg = fem.functionspace(msh, ("DG", 0))
    out = fem.Function(s_dg, name=name)
    components = np.asarray(b_complex.x.array).reshape(-1, 3)
    out.x.array[:] = np.abs(components[:, 0] + sign * 1j * components[:, 1]) / 2.0
    out.x.scatter_forward()
    return out


def b1_plus(b_complex, *, name: str = "B1_plus"):
    """``|B₁⁺| = |B_x + jB_y| / 2`` as a DG0 scalar ``Function``.

    Takes the DG0 vector phasor :func:`magnetic_flux_density_from_e` returns.
    The value is a real magnitude; in the complex build it is stored in a
    complex array with zero imaginary part, so read ``.real`` after a point
    evaluation.
    """
    return _rotating_component(b_complex, +1.0, "b1_plus", name)


def b1_minus(b_complex, *, name: str = "B1_minus"):
    """``|B₁⁻| = |B_x − jB_y| / 2``, the counter-rotating component, as DG0.

    The partner of :func:`b1_plus`: the circularly polarised component that
    rotates *against* the nuclear precession and therefore does no transmit
    work.  Their ratio is the polarisation purity a quadrature birdcage is
    judged on — ideally ``|B₁⁺| ≫ |B₁⁻|`` in one drive sense and the reverse in
    the other, and ``|B₁⁺| ≈ |B₁⁻|`` for a linearly polarised (single-port)
    drive.  Added by `WF-6` step 2 (2026-08-30) with the quadrature
    superposition that first needed it.

    Same conventions as :func:`b1_plus`: DG0 vector phasor in, real magnitude
    stored in a complex array out.
    """
    return _rotating_component(b_complex, -1.0, "b1_minus", name)
