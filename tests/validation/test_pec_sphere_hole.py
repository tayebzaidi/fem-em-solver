"""`TH-15` step 1: an internal PEC body solved as a *hole*, against the closed form.

A perfectly conducting sphere of radius ``R`` in a uniform quasi-static field
``E₀ẑ`` excludes the field entirely.  Outside it the exact solution is the same
uniform-plus-dipole pair the `TH-8` dielectric gate uses, with the dipole
coefficient at its perfect-conductor value::

    E_out = E₀ẑ + β E₀ R³ (3 (ẑ·r̂) r̂ − ẑ)/r³,     β = 1

(the dielectric's ``β = (ε − 1)/(ε + 2)`` in the limit ``ε → ∞``; do **not**
reach that limit by passing ``ε = ∞`` into `TH-8`'s callable, where the
expression is ``nan``).  On the sphere surface the tangential component
``E_θ ∝ (1 − R³/r³)`` vanishes, which is what makes ``n × E = 0`` on the cavity
wall the *same* closed form and not an extra piece of data.

The fixture is `TH-8`'s middle rung with the sphere cut out of the box rather
than fragmented into it (``sphere_in_box_domain(as_hole=True)``): the sphere's
cells are absent from the mesh and its surface arrives as facet tag ``2``.  The
solve constrains the tangential trace on tags ``(1, 2)`` — outer wall and cavity
— through ``TimeHarmonicProblem.pec_facet_tags``.

**What is gated is the dipole coefficient β, not the field.**  At 10 MHz and
``k₀R = 5e-3`` the exterior field of a *lossy* sphere is the PEC one to ~1e-6
(``σ/(ωε₀) = 1.4e6`` at σ = 800 S/m), and even the `TH-8` dielectric at ε = 78
has β = 0.9625 — within 3.75% of PEC, i.e. inside the band below.  So neither is
a control here.  The control is the **natural cavity**: with no condition on the
cavity facets the curl-curl form's gradient block enforces ``n·(εE) = 0`` there,
which is a *void*, β = −½ — the far side of the ceiling ``|Δβ| = 1.5``.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_pec_sphere_hole.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI
from petsc4py import PETSc

import dolfinx
from dolfinx import fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel

from tests.complex_mode import complex_only
from tests.validation.test_dielectric_sphere import (
    BOX_HALF_WIDTH,
    E0,
    FREQUENCY_HZ,
    SPHERE_RADIUS,
    TH8_RECORD_INTERIOR_MISS,
)

# `TH-8`'s middle rung — the resolution its own negative control runs on.
RESOLUTION_SPHERE = 0.00833
RESOLUTION_FAR = 0.0167

OUTER_BOUNDARY_TAG = 1
CAVITY_TAG = 2

# Twice the fixture's own measured miss against a closed form (`TH-8`'s finest
# rung, imported).  Pre-stated: this module never restates the record and never
# widens the band.
BAND = 2.0 * TH8_RECORD_INTERIOR_MISS

# The perfect-conductor dipole coefficient.
BETA_PEC = 1.0
# The natural (void) cavity's coefficient, and hence the largest separation this
# fixture can produce: |β_void − β_PEC| = 1.5.
BETA_VOID = -0.5
CONTROL_CEILING = 2.0  # a ceiling, not a fit: the void value gives exactly 1.5.


def _pec_exterior_numpy():
    """Dirichlet data in dolfinx interpolation convention, ``x`` of shape (3, n).

    ``β = 1`` outside; zero inside, so an interpolation point that lands strictly
    inside the (absent) sphere — every quadrature point of a chord across the
    cavity wall does — contributes nothing to the tangential trace there.
    """
    R = SPHERE_RADIUS

    def field(x: np.ndarray) -> np.ndarray:
        r = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
        r_safe = np.where(r > 0.0, r, 1.0)
        z = x[2]
        common = BETA_PEC * E0 * R**3 / r_safe**5
        ex_out = common * 3.0 * z * x[0]
        ey_out = common * 3.0 * z * x[1]
        ez_out = E0 + common * (3.0 * z * z - r_safe**2)

        inside = r < R
        ex = np.where(inside, 0.0, ex_out)
        ey = np.where(inside, 0.0, ey_out)
        ez = np.where(inside, 0.0, ez_out)
        return np.array([ex, ey, ez], dtype=PETSc.ScalarType)

    return field


def _dipole_basis(points: np.ndarray) -> np.ndarray:
    """``E₀R³ (3 (ẑ·r̂) r̂ − ẑ)/r³`` at ``points`` of shape (n, 3) — the β column."""
    r = np.linalg.norm(points, axis=1)
    r_hat = points / r[:, None]
    z_hat = np.array([0.0, 0.0, 1.0])
    cos_theta = r_hat[:, 2]
    return (
        E0
        * SPHERE_RADIUS**3
        / r[:, None] ** 3
        * (3.0 * cos_theta[:, None] * r_hat - z_hat[None, :])
    )


def _uniform_field(points: np.ndarray) -> np.ndarray:
    out = np.zeros_like(points)
    out[:, 2] = E0
    return out


def _probe_shells() -> np.ndarray:
    """24 Fibonacci points on each of r = 1.2 R and 1.5 R, off any lattice plane."""
    n_per_shell = 24
    indices = np.arange(n_per_shell) + 0.5
    phi = np.arccos(1.0 - 2.0 * indices / n_per_shell)
    theta = np.pi * (1.0 + 5.0**0.5) * indices
    shells = []
    for factor in (1.2, 1.5):
        rr = factor * SPHERE_RADIUS
        shells.append(
            np.column_stack(
                [
                    rr * np.cos(theta) * np.sin(phi),
                    rr * np.sin(theta) * np.sin(phi),
                    rr * np.cos(phi),
                ]
            )
        )
    return np.vstack(shells)


_MESH_CACHE: dict = {}


def _hole_mesh():
    """The cut mesh, built once per process (three solves share it)."""
    if "mesh" not in _MESH_CACHE:
        _MESH_CACHE["mesh"] = MeshGenerator.sphere_in_box_domain(
            sphere_radius=SPHERE_RADIUS,
            box_half_width=BOX_HALF_WIDTH,
            resolution_sphere=RESOLUTION_SPHERE,
            resolution_far=RESOLUTION_FAR,
            comm=MPI.COMM_WORLD,
            as_hole=True,
        )
    return _MESH_CACHE["mesh"]


def _cavity_dofs(msh, facet_tags, v_space) -> np.ndarray:
    fdim = msh.topology.dim - 1
    msh.topology.create_connectivity(fdim, msh.topology.dim)
    facets = np.asarray(facet_tags.find(CAVITY_TAG), dtype=np.int32)
    return fem.locate_dofs_topological(v_space, fdim, facets)


def _solve(pec_facet_tags):
    """Solve on the hole mesh with the given Dirichlet facet set.

    Returns ``(beta, max_pointwise_miss, imag_ratio, cavity_dof_max, ncells,
    dirichlet_dof_count)``.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags, facet_tags = _hole_mesh()

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_pec_exterior_numpy(),
        pec_facet_tags=pec_facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    fields = solver.solve()

    points = _probe_shells()
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(f"{int((~valid).sum())} exterior probe points were not evaluated")

    e_measured = np.real(real_values[:, :3])
    e_imaginary = np.real(imag_values[:, :3])

    basis = _dipole_basis(points)
    residual = e_measured - _uniform_field(points)
    beta = float(np.sum(residual * basis) / np.sum(basis * basis))

    e_closed = _uniform_field(points) + BETA_PEC * basis
    misses = np.linalg.norm(e_measured - e_closed, axis=1) / E0
    pointwise = float(np.max(misses))
    if comm.rank == 0:
        half = points.shape[0] // 2
        worst = int(np.argmax(misses))
        r_worst = float(np.linalg.norm(points[worst]))
        print(
            f"  [diag] shell 1.2R: max {np.max(misses[:half]):.4%}, "
            f"rms {np.sqrt(np.mean(misses[:half] ** 2)):.4%}; "
            f"shell 1.5R: max {np.max(misses[half:]):.4%}, "
            f"rms {np.sqrt(np.mean(misses[half:] ** 2)):.4%}"
        )
        print(
            f"  [diag] worst point {worst} at r/R = {r_worst / SPHERE_RADIUS:.3f}, "
            f"cos(theta) = {points[worst][2] / r_worst:+.3f}: "
            f"|E| = {np.linalg.norm(e_measured[worst]):.4f} vs closed "
            f"{np.linalg.norm(e_closed[worst]):.4f}; relative-L2 over both shells = "
            f"{np.linalg.norm(e_measured - e_closed) / np.linalg.norm(e_closed):.4%}"
        )
    imag_ratio = float(
        np.max(np.linalg.norm(e_imaginary, axis=1))
        / max(float(np.max(np.linalg.norm(e_measured, axis=1))), 1e-300)
    )

    # Rank-local: the cavity dof block lives on whichever ranks own those facets.
    cavity_dofs = _cavity_dofs(msh, facet_tags, solver.function_space())
    solution = np.asarray(fields.e_complex.x.array)
    local_max = float(np.max(np.abs(solution[cavity_dofs]))) if cavity_dofs.size else 0.0
    cavity_dof_max = float(comm.allreduce(local_max, op=MPI.MAX))

    ncells = int(
        comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM)
    )
    return beta, pointwise, imag_ratio, cavity_dof_max, ncells, int(fields.dirichlet_dof_count)


@complex_only
@pytest.mark.integration
def test_pec_hole_reproduces_the_conducting_sphere_dipole_coefficient():
    """β fitted outside the hole is the perfect-conductor value 1, and the
    cavity dofs are pinned to zero."""
    comm = MPI.COMM_WORLD
    msh, _, facet_tags = _hole_mesh()

    beta, pointwise, imag_ratio, cavity_dof_max, ncells, ndirichlet = _solve((1, 2))
    beta_miss = abs(beta - BETA_PEC)

    # Rank-safety: `find` is rank-local, so the cavity's existence is a reduced
    # property of the mesh, not of this rank.
    v_space = fem.functionspace(msh, ("N1curl", 1))
    n_cavity_dofs = int(
        comm.allreduce(int(_cavity_dofs(msh, facet_tags, v_space).size), op=MPI.SUM)
    )

    if comm.rank == 0:
        print(
            f"\n[TH-15 step 1] PEC sphere as a hole, R = {SPHERE_RADIUS} m, "
            f"f = {FREQUENCY_HZ / 1e6:.4f} MHz, {ncells} cells, band = {BAND:.4%}"
        )
        print(f"  fitted beta = {beta:.6f}   |beta - 1| = {beta_miss:.4%}")
        print(f"  max pointwise |E - E_closed|/E0 on r = 1.2R, 1.5R: {pointwise:.4%}")
        print(f"  |Im E|/|Re E| = {imag_ratio:.3e}")
        print(
            f"  cavity dofs (tag {CAVITY_TAG}, reduced) = {n_cavity_dofs}, "
            f"max |E| on them = {cavity_dof_max:.3e}; total Dirichlet dofs = {ndirichlet}"
        )

    assert n_cavity_dofs > 0, (
        "no dofs were located on cavity facet tag 2 — the hole's surface group "
        "did not reach the dolfinx facet tags, so nothing was constrained"
    )
    assert cavity_dof_max < 1e-12, (
        f"max |E| on the cavity dofs is {cavity_dof_max:.3e}, not zero: the "
        "homogeneous tangential trace was not applied on the cavity wall"
    )
    assert imag_ratio < 1e-6, (
        f"|Im E|/|Re E| = {imag_ratio:.3e} on a lossless, real-data problem — "
        "the e^{+jwt} convention or the material map has leaked an imaginary part"
    )
    assert beta_miss <= BAND, (
        f"fitted dipole coefficient {beta:.6f} misses the perfect-conductor "
        f"beta = 1 by {beta_miss:.4%}, over the {BAND:.4%} band (2x the TH-8 "
        f"record miss {TH8_RECORD_INTERIOR_MISS:.4%})"
    )
    assert pointwise <= BAND, (
        f"max pointwise exterior miss {pointwise:.4%} exceeds the {BAND:.4%} band"
    )


@complex_only
@pytest.mark.integration
def test_natural_cavity_is_the_negative_control():
    """Drop tag 2 from the Dirichlet set and the cavity becomes a void, β = −½.

    The ceiling is stated before the claim: this fixture cannot separate the two
    cases by more than ``|β_void − β_PEC| = 1.5``, so nothing larger is claimed.
    """
    comm = MPI.COMM_WORLD
    beta, pointwise, _, cavity_dof_max, ncells, ndirichlet = _solve((OUTER_BOUNDARY_TAG,))
    beta_miss = abs(beta - BETA_PEC)

    if comm.rank == 0:
        print(
            f"\n[TH-15 step 1] negative control — cavity left natural "
            f"(pec_facet_tags=(1,)), {ncells} cells, {ndirichlet} Dirichlet dofs"
        )
        print(
            f"  fitted beta = {beta:.6f} (void closed form {BETA_VOID:+.4f}), "
            f"|beta - 1| = {beta_miss:.4%} = {beta_miss / BAND:.1f}x the band"
        )
        print(f"  max pointwise |E - E_closed(PEC)|/E0 = {pointwise:.4%}")
        print(f"  max |E| on the (unconstrained) cavity dofs = {cavity_dof_max:.3e}")

    assert beta_miss <= CONTROL_CEILING, (
        f"the control's |beta - 1| = {beta_miss:.4f} exceeds the ceiling "
        f"{CONTROL_CEILING} this fixture can produce (the void value is 1.5); "
        "the fitted coefficient is not measuring the same field"
    )
    assert beta_miss >= 5.0 * BAND, (
        f"an unconstrained cavity landed within {beta_miss:.4%} of the "
        f"perfect-conductor beta = 1, under 5x the {BAND:.4%} band — the gate "
        "above is not measuring the PEC condition"
    )
    assert cavity_dof_max > 1e-12, (
        f"the control's cavity dofs are zero to {cavity_dof_max:.3e}: the "
        "Dirichlet set reached the cavity even though tag 2 was not requested"
    )


@complex_only
@pytest.mark.integration
def test_cavity_facets_are_exterior_facets_of_the_hole_mesh():
    """Route equality: ``pec_facet_tags=(1, 2)`` and ``None`` are the same set.

    A hole's cavity wall *is* an exterior facet of the meshed domain, so the two
    routes must locate the identical dof index array on this mesh — which is what
    makes ``(1,)`` a real control rather than a relabelling.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags, facet_tags = _hole_mesh()
    v_space = fem.functionspace(msh, ("N1curl", 1))
    fdim = msh.topology.dim - 1
    msh.topology.create_connectivity(fdim, msh.topology.dim)

    exterior = dolfinx.mesh.exterior_facet_indices(msh.topology)
    tagged = np.unique(
        np.concatenate(
            [
                np.asarray(facet_tags.find(OUTER_BOUNDARY_TAG), dtype=np.int32),
                np.asarray(facet_tags.find(CAVITY_TAG), dtype=np.int32),
            ]
        )
    ).astype(np.int32)

    dofs_exterior = np.sort(fem.locate_dofs_topological(v_space, fdim, exterior))
    dofs_tagged = np.sort(fem.locate_dofs_topological(v_space, fdim, tagged))

    common = dict(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
        boundary_condition="pec_zero_tangential_a",
        dirichlet_e_field=_pec_exterior_numpy(),
    )
    _, _, count_default = TimeHarmonicSolver(
        TimeHarmonicProblem(**common), degree=1
    ).build_boundary_conditions()
    _, _, count_tagged = TimeHarmonicSolver(
        TimeHarmonicProblem(**common, pec_facet_tags=(1, 2)), degree=1
    ).build_boundary_conditions()
    _, _, count_wall = TimeHarmonicSolver(
        TimeHarmonicProblem(**common, pec_facet_tags=(OUTER_BOUNDARY_TAG,)), degree=1
    ).build_boundary_conditions()

    total_default = int(comm.allreduce(count_default, op=MPI.SUM))
    total_tagged = int(comm.allreduce(count_tagged, op=MPI.SUM))
    total_wall = int(comm.allreduce(count_wall, op=MPI.SUM))

    if comm.rank == 0:
        print(
            f"\n[TH-15 step 1] Dirichlet dof counts (reduced): None = {total_default}, "
            f"(1, 2) = {total_tagged}, (1,) = {total_wall}"
        )

    assert np.array_equal(dofs_exterior, dofs_tagged), (
        f"rank {comm.rank}: the tagged facet set ({dofs_tagged.size} dofs) is not "
        f"the exterior facet set ({dofs_exterior.size} dofs) — the hole's surface "
        "groups do not cover the boundary of the meshed domain"
    )
    assert total_tagged == total_default, (
        f"pec_facet_tags=(1, 2) constrained {total_tagged} dofs where the default "
        f"path constrains {total_default}"
    )
    assert total_wall < total_default, (
        f"dropping the cavity tag left {total_wall} of {total_default} dofs "
        "constrained — the control does not release the cavity"
    )
