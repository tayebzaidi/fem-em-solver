"""`TH-8`: dielectric sphere in a uniform quasi-static field, against the closed form.

A sphere of radius ``R`` and relative permittivity ``ε`` placed in a uniform
field ``E₀ẑ`` polarises uniformly.  In the quasi-static limit (``kR ≪ 1`` both
inside and outside) the electrostatic solution is exact::

    Φ_in  = −3/(ε + 2) · E₀ z                      (r < R)
    Φ_out = −E₀ z + β E₀ R³ z/r³,   β = (ε − 1)/(ε + 2)   (r > R)

so that

    E_in  = 3/(ε + 2) · E₀ ẑ                       — uniform, and *smaller*
                                                     than E₀ by the depolarisation
                                                     factor
    E_out = E₀ ẑ + β E₀ R³ (3 (ẑ·r̂) r̂ − ẑ)/r³     — uniform + a point dipole

Both are curl-free, so the pair is an exact source-free solution of
``∇×∇×E − k² E = 0`` up to the ``O((kR)²)`` retardation the quasi-static limit
drops.  The gate imposes ``E_out`` as Dirichlet data on the wall of a cubic air
box (exact there, because the exterior solution above holds on any surface
outside the sphere) and measures the **interior** field, which the solver is
entirely free to get wrong: nothing in the boundary data states the interior
value.  ``3/(ε + 2)`` is produced by ``ε`` acting through the mass term
``−k₀² ε_c E`` and by the normal-``D`` jump at the sphere surface.  Delete the
sphere from the material map and the interior field goes to ``≈ E₀``, which at
``ε = 78`` is a factor of ~27 out — that is the negative control below.

Why this is a real discriminator and not a restatement of the boundary data:
the dipole term at the box wall (``|r| ≥ W = 2R``) contributes at most
``2βR³/W³ ≈ 24%`` of ``E₀``, while the quantity asserted is an interior value
26.7× smaller than ``E₀``.  A solver that ignored the sphere entirely would sit
within a few percent of ``E₀``.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_dielectric_sphere.py -v'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI
from petsc4py import PETSc

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.constants import EPSILON_0, MU_0

from tests.complex_mode import complex_only

SPHERE_RADIUS = 0.05
BOX_HALF_WIDTH = 0.10
E0 = 1.0
EPSILON_R_SPHERE = 78.0
SPHERE_TAG = 1

# Quasi-static means kR ≪ 1 on *both* sides.  k₀R = 5e-3 puts the interior at
# k_in R = √78 · 5e-3 = 4.4e-2, so the retardation correction the closed form
# drops is O((k_in R)²) ≈ 0.2% — an order of magnitude under the discretisation
# error, which is what the gate is actually measuring.
K0_R = 5.0e-3
SPEED_OF_LIGHT = 1.0 / np.sqrt(MU_0 * EPSILON_0)
FREQUENCY_HZ = float(K0_R / SPHERE_RADIUS * SPEED_OF_LIGHT / (2.0 * np.pi))


def interior_field_closed_form(epsilon_r: float) -> float:
    """``E_in = 3/(ε + 2) · E₀`` — the whole point of the gate."""
    return 3.0 / (epsilon_r + 2.0) * E0


def _exact_exterior_numpy(epsilon_r: float):
    """Dirichlet data in dolfinx interpolation convention, ``x`` of shape (3, n).

    Evaluated only on the box wall, but written for all ``r`` (piecewise) so the
    same callable can be probed anywhere for diagnostics.
    """
    beta = (epsilon_r - 1.0) / (epsilon_r + 2.0)
    e_in = interior_field_closed_form(epsilon_r)
    R = SPHERE_RADIUS

    def field(x: np.ndarray) -> np.ndarray:
        r = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
        # Guard r = 0: the interior branch is used there and does not read r.
        r_safe = np.where(r > 0.0, r, 1.0)
        z = x[2]
        common = beta * E0 * R**3 / r_safe**5
        ex_out = common * 3.0 * z * x[0]
        ey_out = common * 3.0 * z * x[1]
        ez_out = E0 + common * (3.0 * z * z - r_safe**2)

        inside = r < R
        ex = np.where(inside, 0.0, ex_out)
        ey = np.where(inside, 0.0, ey_out)
        ez = np.where(inside, e_in, ez_out)
        return np.array([ex, ey, ez], dtype=PETSc.ScalarType)

    return field


def _interior_probe_points() -> np.ndarray:
    """Points strictly inside the sphere, off any mesh lattice plane.

    A Fibonacci spiral on two shells (0.3 R, 0.55 R) plus a deliberately
    off-centre point: uniformity is a *spatial* claim, so the probe has to span
    the interior rather than sample one line through it.
    """
    n_per_shell = 12
    points = [np.array([0.0031, -0.0027, 0.0043]) * SPHERE_RADIUS]
    indices = np.arange(n_per_shell) + 0.5
    phi = np.arccos(1.0 - 2.0 * indices / n_per_shell)
    theta = np.pi * (1.0 + 5.0**0.5) * indices
    for shell in (0.30, 0.55):
        rr = shell * SPHERE_RADIUS
        points.append(
            np.column_stack(
                [
                    rr * np.cos(theta) * np.sin(phi),
                    rr * np.sin(theta) * np.sin(phi),
                    rr * np.cos(phi),
                ]
            )
        )
    return np.vstack([np.atleast_2d(points[0]), points[1], points[2]])


def _solve_sphere(
    resolution_sphere: float,
    resolution_far: float,
    *,
    epsilon_r_sphere: float = EPSILON_R_SPHERE,
    blind: bool = False,
):
    """Solve the sphere-in-uniform-field problem and probe the interior.

    ``blind=True`` drops the sphere from the material map (vacuum everywhere)
    while keeping the *same* Dirichlet data — the negative control.

    Returns ``(ez_mean, ez_spread, transverse_ratio, imag_ratio, ncells)``.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.sphere_in_box_domain(
        sphere_radius=SPHERE_RADIUS,
        box_half_width=BOX_HALF_WIDTH,
        resolution_sphere=resolution_sphere,
        resolution_far=resolution_far,
        comm=comm,
    )

    material_map = (
        None
        if blind
        else {SPHERE_TAG: HomogeneousMaterial(sigma=0.0, epsilon_r=epsilon_r_sphere)}
    )
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0),
        cell_tags=cell_tags,
        material_map=material_map,
        boundary_condition="pec_zero_tangential_a",
        # The Dirichlet trace always carries the true exterior solution, so the
        # blind control is handed the same data and differs only in ε.
        dirichlet_e_field=_exact_exterior_numpy(epsilon_r_sphere),
    )
    fields = TimeHarmonicSolver(problem, degree=1).solve()

    points = _interior_probe_points()
    real_values, valid_real = evaluate_vector_field_parallel(fields.e_real, points, comm)
    imag_values, valid_imag = evaluate_vector_field_parallel(fields.e_imag, points, comm)
    valid = valid_real & valid_imag
    if not np.all(valid):
        raise RuntimeError(f"{int((~valid).sum())} interior probe points were not evaluated")

    ez = np.real(real_values[:, 2])
    ez_imag = np.real(imag_values[:, 2])
    transverse = np.hypot(np.real(real_values[:, 0]), np.real(real_values[:, 1]))

    ez_mean = float(np.mean(ez))
    ez_spread = float(np.max(np.abs(ez - ez_mean)) / abs(ez_mean))
    transverse_ratio = float(np.max(transverse) / abs(ez_mean))
    imag_ratio = float(np.max(np.abs(ez_imag)) / abs(ez_mean))

    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    return ez_mean, ez_spread, transverse_ratio, imag_ratio, int(ncells)


@complex_only
@pytest.mark.integration
def test_dielectric_sphere_interior_field_matches_closed_form():
    """Interior ``E_z`` equals ``3/(ε+2)E₀``, is uniform, and improves with h."""
    comm = MPI.COMM_WORLD
    expected = interior_field_closed_form(EPSILON_R_SPHERE)

    resolutions = [(0.0125, 0.025), (0.00833, 0.0167), (0.00625, 0.0125)]
    runs = [_solve_sphere(hs, hf) for hs, hf in resolutions]
    errors = [abs(m[0] - expected) / expected for m in runs]
    coarse, fine = runs[0], runs[-1]
    err_coarse, err_fine = errors[0], errors[-1]

    # Rate fitted over three resolutions rather than a two-point ratio, so one
    # lucky mesh cannot manufacture it (MAG-13 precedent).
    h = np.array([hs for hs, _ in resolutions])
    rate = float(np.polyfit(np.log(h), np.log(errors), 1)[0])

    if comm.rank == 0:
        print(
            f"\n[TH-8] dielectric sphere, R = {SPHERE_RADIUS} m, eps_r = {EPSILON_R_SPHERE}, "
            f"f = {FREQUENCY_HZ / 1e6:.4f} MHz (k0*R = {K0_R:.1e})"
        )
        print(f"  closed form: E_in/E0 = 3/(eps+2) = {expected:.6f}")
        for (hs, _), m, err in zip(resolutions, runs, errors):
            print(
                f"  h_sphere = {hs:.5f} ({m[4]:6d} cells): E_z = {m[0]:.6f} "
                f"({err:.3%}), spread = {m[1]:.3%}, "
                f"transverse = {m[2]:.3%}, |Im|/|Re| = {m[3]:.3e}"
            )
        print(f"  fitted convergence rate in h: {rate:.4f}")

    # Bounds stated from the measurement recorded in PROJECT_PLAN §7 TH-8; the
    # mesh moves, not the bound, if a change pushes these up.
    assert err_fine < err_coarse, (
        f"refinement did not improve the interior field: {err_coarse:.4%} -> {err_fine:.4%}"
    )
    assert rate > 0.9, (
        f"fitted convergence rate {rate:.3f} in h is below O(h) — the interior "
        "field is not converging to the closed form"
    )
    assert err_fine < 0.05, (
        f"interior field {fine[0]:.6f} V/m differs from the closed form "
        f"{expected:.6f} V/m by {err_fine:.2%}, over the 5% MVP criterion "
        "(PROJECT_PLAN §10)"
    )
    assert fine[1] < 0.01, (
        f"interior field is not uniform: spread {fine[1]:.2%} across probe points "
        "inside 0.55 R, where the closed form is constant (measured 0.34% at the "
        "middle resolution, so 1% is a bound, not a fit)"
    )
    assert fine[2] < 0.01, (
        f"transverse interior field is {fine[2]:.2%} of E_z; the closed-form "
        "interior field is purely z-directed"
    )
    assert fine[3] < 1e-6, (
        f"|Im E_z|/|Re E_z| = {fine[3]:.3e} on a lossless, real-data problem — "
        "the e^{+jωt} convention or the material map has leaked an imaginary part"
    )


@complex_only
@pytest.mark.integration
def test_sphere_permittivity_is_what_sets_the_interior_field():
    """Negative control: drop ε from the material map and the gate must fail.

    Same mesh, same Dirichlet data, sphere left as vacuum.  The interior field
    then has to sit near ``E₀`` rather than ``3/(ε+2)E₀`` — if it did not, the
    gate above would be measuring its own boundary data.
    """
    comm = MPI.COMM_WORLD
    expected = interior_field_closed_form(EPSILON_R_SPHERE)

    # Middle resolution: the coarse mesh is 9.5% off the closed form, which is
    # outside the 5% MVP bar the loaded leg asserts below.
    loaded = _solve_sphere(0.00833, 0.0167)
    blind = _solve_sphere(0.00833, 0.0167, blind=True)

    err_loaded = abs(loaded[0] - expected) / expected
    err_blind = abs(blind[0] - expected) / expected

    if comm.rank == 0:
        print(f"\n[TH-8] negative control (closed form E_in/E0 = {expected:.6f}):")
        print(f"  with eps_r = {EPSILON_R_SPHERE} in the sphere: E_z = {loaded[0]:.6f} ({err_loaded:.3%})")
        print(f"  eps-blind (vacuum sphere):                     E_z = {blind[0]:.6f} ({err_blind:.3%})")

    assert err_loaded < 0.05, (
        f"the loaded solve missed the closed form by {err_loaded:.2%}; the control "
        "says nothing until the positive case works"
    )
    assert err_blind > 1.0, (
        f"an eps-blind solve landed within {err_blind:.2%} of the closed form — "
        "the interior field is being set by the boundary data, not by the sphere"
    )
    assert abs(blind[0] - E0) < 0.3 * E0, (
        f"eps-blind interior field {blind[0]:.6f} V/m is not near E0 = {E0} V/m; "
        "the control is not the field the uniform-drive boundary data implies"
    )
