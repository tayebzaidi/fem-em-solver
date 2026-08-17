"""Smoke test for minimal time-harmonic E-field scaffold."""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI
from dolfinx import fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.post import evaluate_vector_field_parallel
from fem_em_solver.post.power_balance import poynting_power_balance

from tests.complex_mode import complex_only

# The fixture's material, in one place — the same lossy saline the `TH-6`
# plane-wave gate uses, so the two tests exercise one material model.
SIGMA = 0.7
EPSILON_R = 78.0
FREQUENCY_HZ = 127.74e6

# Pre-stated; see test_time_harmonic_smoke_solve_conserves_real_power.
POYNTING_IMBALANCE_MAX = 0.25
BLIND_SEPARATION = 10.0
SIGMA_BLIND = 1.0e-12 * SIGMA


@complex_only
@pytest.mark.xfail(
    strict=True,
    reason=(
        "known-issues 2026-08-17 (OPS-17 step 2): real Poynting power does not "
        "balance on this smoke fixture — dissipated 1.199162e-06 W against a "
        "net inward flux of -2.008179e-07 W (imbalance 116.7465%, and the flux "
        "has the wrong SIGN). Band left strict so a fix shows as XPASS."
    ),
)
def test_time_harmonic_smoke_solve_conserves_real_power():
    """Solve a small frequency-domain case; real Poynting power balances.

    **This test is a finding, not a pass** (`OPS-17` step 2, 2026-08-17).
    Measured at `-n 2`, ``20260817T112448Z_OPS-17-step2-th-smoke2-n2.log``:

        dissipated  = +1.199162e-06 W   (1/2 int sigma |E|^2 dV)
        net inward  = -2.008179e-07 W   (-oint 1/2 Re(E x conj(H)).n dS)
        relative imbalance: 116.7465%   (pre-stated band 25%)

    The sign is the interesting part: real power leaves through the boundary
    while the medium dissipates, which the identity forbids for any solution of
    Maxwell's equations regardless of boundary condition. Two candidates, and
    the timebox did not allow separating them:

    1. **Resolution.** 0.16 m domain at h = 0.03 m is ~9 cells per in-medium
       wavelength, and the boundary leg is a curl trace — the least accurate
       quantity a degree-1 N1curl solution has. ``test_poynting_balance`` needs
       a refined mesh to reach 5%, and gates the *convergence* of this
       imbalance for exactly that reason.
    2. **The source.** The drive is an axial current in the inner cylinder that
       terminates on the end caps, so ``J.n != 0`` there — the same
       incompatibility ``test_gauge_lagrange`` measures on its wire fixture.

    An h-ladder distinguishes them in one command and belongs to a `TH`/`POST`
    chunk, not to `OPS-17` test hygiene. The band stays at the pre-stated value
    and the marker is ``strict=True``.

    `OPS-17` step 2 (2026-08-17). This was the step-1 table's second archetype
    of the finiteness-only pattern: solve, then assert ``isfinite(|E|)`` and
    ``max|E|`` above a floor.

    The table named "attenuation constant alpha from |E| at two depths vs the
    `TH-1`/`TH-6` lossy plane wave" as the anchor, with a standing instruction
    to delete instead if step 2 found that only duplicates the `TH-6` gate.
    Step 2's finding is the stronger version of that: **alpha is not
    measurable on this fixture at all.** There is no plane wave here — the
    source is an interior axial current in a cylinder, so the field decays by
    geometric spreading as well as by absorption, and the two are not separable
    from |E| at two depths. Building a fixture on which alpha *is* measurable
    means rebuilding ``tests/validation/test_lossy_plane_wave.py``, which
    already gates alpha to 5% at exactly this material and frequency
    (sigma = 0.7 S/m, eps_r = 78, f = 127.74 MHz).

    So the test was neither deleted nor given a duplicate anchor. It keeps the
    one thing it uniquely covers — the time-harmonic solver driven by an
    interior current on a *tagged cylindrical* mesh, the only such solve in the
    tree — and gates it on a conservation identity that is valid on any
    geometry and has no free parameters (`POST-3`):

        -oint 1/2 Re(E x conj(H)).n dS  =  1/2 int sigma |E|^2 dV

    The band is pre-stated. ``test_poynting_balance`` holds this identity to 5%
    on a refined mesh; this fixture is a 0.16 m domain at h = 0.03 m, roughly 9
    cells per in-medium wavelength (lambda = c/(f sqrt(78)) = 0.266 m), so 25%
    is the honest ceiling here. What makes a loose band meaningful is the
    negative control below it: the same field scored blind to sigma must miss
    the identity by an order of magnitude, which is what proves the metric is
    live on this fixture rather than trivially satisfied.
    """
    comm = MPI.COMM_WORLD

    mesh, cell_tags, facet_tags = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(
            sigma=SIGMA,
            epsilon_r=EPSILON_R,
            mu_r=1.0,
        ),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    def current_density(x):
        return ufl.as_vector([0.0, 0.0, 1.0])

    fields = solver.solve(current_density=current_density, subdomain_id=1, gauge_penalty=1e-3)

    # Interpolate to Lagrange space for robust point sampling.
    v_lagrange = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    e_imag_lagrange = fem.Function(v_lagrange, name="E_imag_lagrange")
    e_imag_lagrange.interpolate(fields.e_imag)

    sample_points = np.array(
        [
            [0.0, 0.0, -0.02],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.02],
            [0.005, 0.0, 0.0],
            [0.0, 0.005, 0.0],
        ],
        dtype=np.float64,
    )

    e_samples, valid_mask = evaluate_vector_field_parallel(e_imag_lagrange, sample_points, comm=comm)

    assert valid_mask.all(), (
        "Expected all smoke-test sample points to be evaluable, "
        f"but got {np.count_nonzero(valid_mask)}/{len(valid_mask)}"
    )

    e_mag = np.linalg.norm(e_samples, axis=1)
    max_mag = float(np.max(e_mag))
    mean_mag = float(np.mean(e_mag))

    # The real gate: a conservation identity on the solved phasor. Both sides
    # come from the same E but through different operators (a volume mass term
    # against a boundary curl trace), so this is a check on the solution, not
    # an algebraic tautology. Every integral inside is reduced across comm.
    honest = poynting_power_balance(
        fields.e_complex, omega=fields.omega, sigma=SIGMA, comm=comm
    )
    # Negative control: score the same field as if the medium were lossless.
    # The boundary flux is unchanged and the volume leg collapses to ~zero, so
    # a solve that is genuinely balanced must fail this by an order of
    # magnitude. If it does not, the identity is not live on this fixture and
    # the band above means nothing.
    #
    # SIGMA_BLIND is 1e-12 * SIGMA rather than exactly 0.0 because
    # poynting_power_balance raises on a scalar sigma of 0.0 — UFL folds
    # `0.5 * 0.0 * inner(E, E)` to a domain-less zero and `* ufl.dx` then
    # raises "This integral is missing an integration domain". That module's
    # own docstring advertises the sigma-blind control, so this is a defect in
    # the helper, not in the control; recorded in known-issues 2026-08-17
    # (`OPS-17` step 2). Twelve orders down is lossless for this purpose.
    blind = poynting_power_balance(
        fields.e_complex, omega=fields.omega, sigma=SIGMA_BLIND, comm=comm
    )

    if comm.rank == 0:
        print("\n[OPS-17] time-harmonic smoke diagnostics:")
        print(f"  frequency [Hz]: {problem.frequency_hz:.6e}")
        print(f"  |E_imag| min/max/mean at {len(sample_points)} points: "
              f"{np.min(e_mag):.6e} / {max_mag:.6e} / {mean_mag:.6e}")
        print(f"  dissipated  = {honest['dissipated_power_w']:.6e} W")
        print(f"  net inward  = {honest['net_inward_power_w']:.6e} W")
        print(f"  reactive    = {honest['reactive_inward_power_var']:.6e} var")
        print(f"  relative imbalance: honest {honest['relative_imbalance']:.4%}, "
              f"sigma-blind {blind['relative_imbalance']:.4%}", flush=True)

    assert honest["relative_imbalance"] < POYNTING_IMBALANCE_MAX, (
        f"real power in through the boundary "
        f"({honest['net_inward_power_w']:.6e} W) and Ohmic dissipation "
        f"({honest['dissipated_power_w']:.6e} W) disagree by "
        f"{honest['relative_imbalance']:.4%}, outside the pre-stated "
        f"{POYNTING_IMBALANCE_MAX:.0%} band for this coarse fixture"
    )
    assert blind["relative_imbalance"] > BLIND_SEPARATION * honest["relative_imbalance"], (
        f"scoring the same field with sigma = 0 gave an imbalance of only "
        f"{blind['relative_imbalance']:.4%} against the honest solve's "
        f"{honest['relative_imbalance']:.4%} — the identity is not sensitive "
        "to the loss it is supposed to be accounting for"
    )


def test_time_harmonic_solver_rejects_non_hz_frequency_unit_before_solve():
    """API should fail fast when users pass non-Hz units to avoid silent mistakes."""
    comm = MPI.COMM_WORLD

    mesh, _, _ = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=127.74e6,
        frequency_unit="rad/s",
        material=HomogeneousMaterial(sigma=0.7, epsilon_r=78.0, mu_r=1.0),
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    with pytest.raises(ValueError, match="frequency_unit"):
        solver.solve()


def test_time_harmonic_solver_rejects_material_map_without_cell_tags_before_solve():
    """Material-map API should explain that cell tags are required for tag assignments."""
    comm = MPI.COMM_WORLD

    mesh, _, _ = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=127.74e6,
        material=HomogeneousMaterial(sigma=0.7, epsilon_r=78.0, mu_r=1.0),
        material_map={3: HomogeneousMaterial(sigma=1.2, epsilon_r=68.0, mu_r=1.0)},
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    with pytest.raises(ValueError, match="material_map requires problem.cell_tags"):
        solver.solve()


def test_time_harmonic_solver_rejects_unknown_material_map_tag_before_solve():
    """Material-map API should report unknown tags with known-tag diagnostics."""
    comm = MPI.COMM_WORLD

    mesh, cell_tags, facet_tags = MeshGenerator.cylindrical_domain(
        inner_radius=0.01,
        outer_radius=0.08,
        length=0.12,
        resolution=0.03,
        comm=comm,
    )

    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=127.74e6,
        material=HomogeneousMaterial(sigma=0.7, epsilon_r=78.0, mu_r=1.0),
        material_map={999: HomogeneousMaterial(sigma=1.2, epsilon_r=68.0, mu_r=1.0)},
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    with pytest.raises(ValueError, match="material_map references tags"):
        solver.solve()
