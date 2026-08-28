"""`MAT-6`: the Dodd–Deeds closed form, and the FEM solve against it.

Two halves, in order:

* **step 1** — gates :mod:`fem_em_solver.utils.dodd_deeds`, the reference
  solution only, against independent limits.  No dolfinx; runs in either build.
* **step 2b** — the loading gate itself: solve a filamentary loop over a lossy
  half-space with :class:`TimeHarmonicSolver`, extract ΔZ by the reaction
  integral, and compare it with the closed form.  ``@complex_only``, one mesh
  and three solves, ~2 minutes at ``-n 2`` (heavy tier).

A closed form nobody has checked is worth exactly as much as the proxy solver
was (PROJECT_PLAN §2), so every assertion below is against something derived a
different way:

* **σ = 0** — a non-conducting, non-magnetic half-space must be *exactly*
  invisible, because Γ(α) ≡ 0 identically, not merely small.  This is what
  forced the module to the consistent eddy-current kernel: a first draft kept
  displacement current in the half-space while using the magnetoquasistatic
  free-space kernel above it, and vacuum reflected Γ = −1 at α = 0
  (log ``20260731T050326Z_MAT-6-step1.log``).
* **σ → ∞** — the reactance change must equal ``−ω M_image``, with the image
  mutual inductance computed from the elliptic-integral ``A_φ`` in
  ``AnalyticalSolutions``.  The Hankel integral of eq. (1) and Maxwell's
  elliptic-integral mutual inductance share no algebra beyond ``μ₀``, so this
  pins both the ``jωπμ₀a²`` prefactor and the sign of Γ.
* **thin skin** — ``Γ + 1 ≈ αδ(1−j)`` makes the departure from the perfect
  conductor equal in its real and imaginary parts, so ``ΔR = ΔX − ΔX_pec``
  to leading order, and ``ΔR ∝ √ω`` at fixed σ.  Both are asymptotic identities
  the integral is free to violate if the branch of ``α₁`` is wrong.

Geometry throughout: a 5 cm loop 1 cm above the surface — the same length
scales as the MRI surface-coil-over-phantom case this chunk exists to gate.

Run (the step-2b tests need the complex build)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_dodd_deeds_impedance.py -v'
"""

from __future__ import annotations

import time

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
from fem_em_solver.utils.constants import EPSILON_0, MU_0
from fem_em_solver.utils.dodd_deeds import (
    coil_impedance_change,
    half_space_reflection_coefficient,
    image_limit_inductance_change,
    skin_depth,
)
from tests.complex_mode import complex_only

COIL_RADIUS = 0.05
LIFTOFF = 0.01
FREQUENCY_HZ = 127.74e6  # 3 T proton Larmor, as everywhere else in the project


def test_nonconducting_half_space_is_exactly_invisible():
    """σ = 0, εᵣ = μᵣ = 1 ⇒ Γ ≡ 0 ⇒ ΔZ = 0, identically."""
    alphas = np.linspace(0.0, 500.0, 50)
    gamma = half_space_reflection_coefficient(alphas, FREQUENCY_HZ, sigma=0.0)
    assert np.max(np.abs(gamma)) < 1e-14, f"Γ not identically zero: {gamma}"

    dz = coil_impedance_change(
        FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, sigma=0.0
    )
    # Scale against the perfect-conductor reactance, which is what "small"
    # means here: the vacuum answer is ~14 orders of magnitude below it.
    scale = abs(
        2.0
        * np.pi
        * FREQUENCY_HZ
        * image_limit_inductance_change(COIL_RADIUS, LIFTOFF)
    )
    assert abs(dz) / scale < 1e-12, f"vacuum half-space gave ΔZ = {dz}"


def test_perfect_conductor_limit_matches_image_mutual_inductance():
    """σ → ∞: ΔX = −ω M_image from the elliptic-integral A_φ, and ΔR → 0.

    This is the quantitative anchor of the whole module.  ``M_image`` is the
    mutual inductance between the loop and its mirror at z = −h, evaluated
    from Jackson 5.37 with complete elliptic integrals; ``coil_impedance_change``
    reaches the same number through a Hankel integral of Bessel functions.
    """
    omega = 2.0 * np.pi * FREQUENCY_HZ
    delta_l_image = image_limit_inductance_change(COIL_RADIUS, LIFTOFF)
    assert delta_l_image < 0.0, "image theory must *reduce* the inductance"

    dz = coil_impedance_change(
        FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, sigma=1.0e12
    )
    delta_l_hankel = dz.imag / omega

    rel = abs(delta_l_hankel - delta_l_image) / abs(delta_l_image)
    print(
        f"\n  ΔL image (elliptic) = {delta_l_image:.6e} H"
        f"\n  ΔL Hankel (σ=1e12)  = {delta_l_hankel:.6e} H"
        f"\n  relative difference = {rel:.4%}"
    )
    # Measured 0.0002% (log 20260731T050449Z_MAT-6-step1b.log): the residual is
    # the σ = 1e12 S/m approach to Γ = −1 plus the α-panel truncation, and the
    # bound is set an order of magnitude above it rather than at a round number.
    # Two independent derivations agreeing to 2e-6 is the anchor for eq. (1).
    assert rel < 2e-5, f"image limit off by {rel:.4%}"

    # A perfect conductor dissipates nothing: the residual loss must be a
    # vanishing fraction of the reactive part.
    assert abs(dz.real) / abs(dz.imag) < 1e-4, f"spurious loss: ΔZ = {dz}"


def test_lossy_half_space_dissipates_and_expels_flux():
    """A real conductor: ΔR > 0 (loss) and ΔX < 0 (flux expelled)."""
    dz = coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, sigma=1.0e6)
    print(f"\n  ΔZ(σ=1e6 S/m) = {dz.real:.6e} + {dz.imag:.6e}j Ω")
    assert dz.real > 0.0, f"conductor must dissipate, got ΔR = {dz.real}"
    assert dz.imag < 0.0, f"conductor must expel flux, got ΔX = {dz.imag}"


def test_thin_skin_departure_from_perfect_conductor_is_equal_parts():
    """δ ≪ h ⇒ Γ + 1 ≈ αδ(1−j) ⇒ ΔR = ΔX − ΔX_pec to leading order.

    The identity is asymptotic in δ/h, so it is checked as a *limit*: the
    ratio must approach 1 as σ rises, and it must do so monotonically.
    """
    omega = 2.0 * np.pi * FREQUENCY_HZ
    dx_pec = omega * image_limit_inductance_change(COIL_RADIUS, LIFTOFF)

    ratios = []
    print()
    for sigma in (1.0e5, 1.0e6, 1.0e7, 1.0e8):
        dz = coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, LIFTOFF, sigma=sigma)
        ratio = dz.real / (dz.imag - dx_pec)
        ratios.append(ratio)
        print(
            f"  σ = {sigma:8.1e} S/m  δ = {skin_depth(FREQUENCY_HZ, sigma):.3e} m"
            f"  ΔR = {dz.real:.5e} Ω  ΔR/(ΔX−ΔX_pec) = {ratio:.5f}"
        )

    errors = [abs(r - 1.0) for r in ratios]
    assert all(
        b < a for a, b in zip(errors, errors[1:])
    ), f"departure ratio not converging to 1: {ratios}"
    assert errors[-1] < 0.02, f"thin-skin identity off by {errors[-1]:.3%}"


def test_loss_scales_as_sqrt_frequency_in_the_thin_skin_regime():
    """ΔR ∝ ω^{1/2} once δ ≪ h, because ΔR ≈ ωδ·C and δ ∝ ω^{−1/2}.

    Measured as a log-log slope over a decade, so it cannot be satisfied by a
    wrong constant — only by the right power law.
    """
    sigma = 1.0e7
    freqs = np.array([1.0e7, 3.0e7, 1.0e8])
    resistances = np.array(
        [
            coil_impedance_change(f, COIL_RADIUS, LIFTOFF, sigma=sigma).real
            for f in freqs
        ]
    )
    for f in freqs:
        assert skin_depth(f, sigma) < 0.1 * LIFTOFF, "not in the thin-skin regime"

    slope = float(np.polyfit(np.log(freqs), np.log(resistances), 1)[0])
    print(f"\n  ΔR(f) = {resistances}\n  log-log slope = {slope:.4f} (expect 0.5)")
    assert abs(slope - 0.5) < 0.02, f"ΔR power law is ω^{slope:.3f}, not ω^0.5"


def test_liftoff_reduces_the_coupling_monotonically():
    """e^{−2αh} in eq. (1): more liftoff, less of everything."""
    magnitudes = [
        abs(coil_impedance_change(FREQUENCY_HZ, COIL_RADIUS, h, sigma=1.0e6))
        for h in (0.005, 0.01, 0.02, 0.04)
    ]
    assert all(
        b < a for a, b in zip(magnitudes, magnitudes[1:])
    ), f"|ΔZ| not decreasing with liftoff: {magnitudes}"
    # μ₀ is the only dimensional constant in the module; a units slip would
    # show up as an absurd impedance for a centimetre-scale loop at 128 MHz.
    assert 1e-6 < magnitudes[0] < 1e4, f"|ΔZ| implausible: {magnitudes[0]} Ω"
    assert MU_0 > 0.0


# =============================================================================
# `MAT-6` step 2b — the FEM loading gate
# =============================================================================
#
# The configuration below is *not* free: it was fixed by the step-2a probe
# (`scripts/probes/mat6_step2a_probe.py`, logs
# ``20260731T094211Z_MAT-6-step2a-boxprobe.log`` and ``…-w20.log``) and every
# number in it is a measurement.  Three constraints have to hold at once for the
# 1968 eddy-current kernel of `MAT-6` step 1 to be the right reference:
#
#   * loss tangent σ/(ωε₀) = 1.80e5 ≫ 10²   (displacement current negligible),
#   * δ = √(2/(ωμ₀σ)) = 15.9 mm, i.e. 3.18 near-cells per skin depth, with the
#     slab 9.42 δ deep at W = 0.15 — so the PEC floor sits where the field is
#     already dead,
#   * k₀ · (box diagonal) = 0.109 at W = 0.15 ≪ 1  (no air-side retardation).
#
# Low f with high σ is what satisfies "δ resolvable" and "k₀·box small" at the
# same time: δ ∝ 1/√(fσ) but k₀ ∝ f.
FEM_FREQUENCY_HZ = 10.0e6
FEM_SIGMA_SLAB = 100.0
FEM_LOOP_RADIUS = 0.04
FEM_LIFTOFF = 0.020
FEM_WIRE_RADIUS = 0.0025
FEM_CURRENT_A = 1.0
# W = 0.15 m: 138 490 cells on 0.11 (0.7.2: 138 619), ~27 s per solve at -n 2.
# ΔR moves 0.268% between
# W = 0.15 and W = 0.20, so ΔR is converged in box size here; ΔX is not (5.57%
# still moving), which is why ΔX is gated only on sign and magnitude below.
FEM_BOX_HALF_WIDTH = 0.15

WIRE_TAG = 1
SLAB_TAG = 3


def _azimuthal_current_density(j_magnitude: float):
    """Uniform azimuthal current about the z-axis."""

    def current_density(x):
        # Regularised inside the sqrt rather than with ufl.max_value: in complex
        # mode UFL refuses conditionals on complex-valued operands, so the
        # magnetostatic loop fixture's max_value form does not compile here.
        rho_safe = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
        return ufl.as_vector([
            -x[1] / rho_safe * j_magnitude,
            x[0] / rho_safe * j_magnitude,
            0.0,
        ])

    return current_density


def _solve_loop(msh, cell_tags, sigma_slab, comm, *, tag_the_slab=True):
    """One time-harmonic solve of the loop over the half-space.

    ``tag_the_slab=False`` drops the material map entirely, so the whole box is
    the default air material.  With ``sigma_slab=0`` the two spellings describe
    physically identical media and must therefore give the same field — that is
    the null control in :func:`test_zero_conductivity_slab_is_invisible`.
    """
    material_map = (
        {SLAB_TAG: HomogeneousMaterial(sigma=sigma_slab, epsilon_r=1.0, mu_r=1.0)}
        if tag_the_slab
        else None
    )
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FEM_FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map=material_map,
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[WIRE_TAG],
        # `MAT-6`'s landed 1.58% agreement with Dodd-Deeds was measured on the
        # unprojected drive.  Step 2f pins it there rather than silently
        # re-baselining a gated result on a drive nobody has re-verified here;
        # re-gating this fixture under the projection is its own chunk.
        project_source=False,
    )
    comm.Barrier()
    return fields.e_complex, time.perf_counter() - t0


def _reaction_impedance(msh, cell_tags, e_a, e_b, current_a, comm) -> complex:
    """``ΔZ = −(1/I²) ∫_wire (E_a − E_b)·J dV``, reduced across ranks.

    Taking the *difference* of two solves is what makes this tractable: the
    loop's own self-impedance and most of the PEC-truncation error are common to
    both and cancel.  ``current_a`` is the current the *meshed* torus carries,
    not the nominal 1 A — ΔZ goes as 1/I², so the discretised torus's volume
    deficit would otherwise show up as an impedance error with nothing to do
    with the field solve.
    """
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    x = ufl.SpatialCoordinate(msh)
    j_vec = _azimuthal_current_density(j_magnitude)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    # J is real, so inner()'s conjugation of its second argument is a no-op:
    # this is the reaction integral ∫ΔE·J, not ∫ΔE·J̄.
    local = fem.assemble_scalar(fem.form(ufl.inner(e_a - e_b, j_vec) * dx_wire))
    # assemble_scalar is rank-local.
    return complex(-comm.allreduce(local, op=MPI.SUM) / current_a**2)


@pytest.fixture(scope="module")
def fem_impedance_change():
    """Mesh once, solve three times, return the two reaction integrals.

    Module-scoped because the mesh is 138 490 cells on 0.11 (0.7.2: 138 619)
    and each solve is ~27 s at
    ``-n 2``: the gate, the ΔX check and the null control share one fixture.
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=0.002,
        resolution_near=0.005,
        resolution_far=0.025,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)

    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    one = fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
    v_wire = float(
        np.real(comm.allreduce(fem.assemble_scalar(fem.form(one * dx_wire)), op=MPI.SUM))
    )
    # ∫J_φ dV = I·2πa for an ideal torus, so the meshed volume fixes the current
    # the solver actually sees.
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    current_meshed = j_magnitude * v_wire / (2.0 * np.pi * FEM_LOOP_RADIUS)

    e_loaded, t_loaded = _solve_loop(msh, cell_tags, FEM_SIGMA_SLAB, comm)
    e_free, t_free = _solve_loop(msh, cell_tags, 0.0, comm)
    e_untagged, t_untagged = _solve_loop(
        msh, cell_tags, 0.0, comm, tag_the_slab=False
    )

    dz = _reaction_impedance(msh, cell_tags, e_loaded, e_free, current_meshed, comm)
    dz_null = _reaction_impedance(
        msh, cell_tags, e_free, e_untagged, current_meshed, comm
    )
    dz_ref = coil_impedance_change(
        FEM_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )

    if comm.rank == 0:
        print(
            f"\n  mesh: {ncells} cells at W = {FEM_BOX_HALF_WIDTH} m;"
            f" meshed loop current {current_meshed:.6f} A"
            f"\n  solve wall clock [s]: loaded {t_loaded:.1f}, free {t_free:.1f},"
            f" untagged {t_untagged:.1f}"
            f"\n  FEM   ΔZ = {dz.real:+.6e} + j({dz.imag:+.6e}) Ω"
            f"\n  exact ΔZ = {dz_ref.real:+.6e} + j({dz_ref.imag:+.6e}) Ω"
            f"\n  null control ΔZ = {dz_null.real:+.3e} + j({dz_null.imag:+.3e}) Ω"
        )
    return dict(dz=dz, dz_null=dz_null, dz_ref=dz_ref, ncells=int(ncells))


def test_fem_regime_constraints_hold_for_the_eddy_current_kernel():
    """The reference is only valid where these three inequalities hold."""
    omega = 2.0 * np.pi * FEM_FREQUENCY_HZ
    loss_tangent = FEM_SIGMA_SLAB / (omega * EPSILON_0)
    delta = skin_depth(FEM_FREQUENCY_HZ, FEM_SIGMA_SLAB)
    k0_box = omega * np.sqrt(MU_0 * EPSILON_0) * 2 * FEM_BOX_HALF_WIDTH * np.sqrt(3.0)
    print(
        f"\n  loss tangent = {loss_tangent:.4g}; δ = {delta:.6f} m"
        f" ({delta / 0.005:.2f} near-cells, slab {FEM_BOX_HALF_WIDTH / delta:.2f} δ deep);"
        f" k₀·diag = {k0_box:.4f}"
    )
    assert loss_tangent > 1.0e2, f"displacement current not negligible: {loss_tangent}"
    assert delta / 0.005 > 3.0, f"skin depth under-resolved: {delta / 0.005} cells"
    assert FEM_BOX_HALF_WIDTH / delta > 3.0, "slab shallower than 3 δ"
    assert k0_box < 0.2, f"air-side retardation not negligible: k₀·diag = {k0_box}"


@complex_only
@pytest.mark.integration
def test_fem_resistance_change_matches_dodd_deeds(fem_impedance_change):
    """**The `MAT-6` gate.** ΔR from the solved field against the closed form.

    This is the chunk's whole point: the FEM coil impedance *change* caused by a
    conductive body, against a published closed form.  A solver that ignored σ
    would return ΔZ = 0 identically and fail by 100%.

    The 5% bound is sized from the step-2a measurement, not chosen: the offset
    measured 1.58% at W = 0.15 and 1.85% at W = 0.20, and ΔR moves 0.268%
    between those two boxes.  5% covers the offset plus the remaining box
    motion with room to spare, and would still catch a sign error, a factor of
    2, or a σ-blind solve.
    """
    dz, dz_ref = fem_impedance_change["dz"], fem_impedance_change["dz_ref"]
    rel = abs(dz.real / dz_ref.real - 1.0)
    print(f"\n  ΔR: FEM {dz.real:.6e} Ω vs exact {dz_ref.real:.6e} Ω → {rel:.2%}")
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert rel < 0.05, f"ΔR off the closed form by {rel:.2%}"


@complex_only
@pytest.mark.integration
def test_fem_reactance_change_has_the_right_sign_and_magnitude(fem_impedance_change):
    """ΔX: sign and order of magnitude only — deliberately, and here is why.

    ΔX is **not** gated at ΔR's tolerance because it is not converged and the
    step-2a probe could not attribute the residual.  Measured against the
    closed form: −35.3% at W = 0.10, −18.8% at W = 0.15, −14.3% at W = 0.20 —
    monotonically approaching the reference with 5.57% of box motion still left
    at the largest box.  Two unseparated contributions: PEC-wall imaging of the
    induced currents, and the **finite wire section** — the reference is
    filamentary, and re-evaluating it at h ± r_wire spreads ΔX by 30%, so a fat
    torus is a first-order modelling error here, not a rounding one.

    Widening a tolerance until it swallows that 14% would be exactly the move
    the `MAG` defect-5 note forbids (PROJECT_PLAN §7): it would produce a green
    test that cannot fail for the right reason.  ΔX is therefore gated on what
    *is* established — the sign (flux expelled) and the order of magnitude —
    and the tolerance follows the physics once the wire is thinned to
    h/r_wire ≥ 16 or the box reaches W ≥ 0.25.
    """
    dz, dz_ref = fem_impedance_change["dz"], fem_impedance_change["dz_ref"]
    ratio = dz.imag / dz_ref.imag
    print(f"\n  ΔX: FEM {dz.imag:.6e} Ω vs exact {dz_ref.imag:.6e} Ω → ratio {ratio:.4f}")
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
    assert 0.5 < ratio < 2.0, f"ΔX is not within an order of magnitude: {ratio}"


@complex_only
@pytest.mark.integration
def test_zero_conductivity_slab_is_invisible(fem_impedance_change):
    """Null control: with σ = 0 the tagged slab is not a body at all.

    The same mesh is solved with the lower half tagged as a σ = 0 material and
    with no material map at all.  Both describe vacuum, so the reaction
    integral between them must vanish — anything else would mean the tagging,
    the material map, or the extraction is manufacturing impedance on its own,
    which would also inflate the loaded ΔZ the gate above compares.
    """
    dz, dz_null = fem_impedance_change["dz"], fem_impedance_change["dz_null"]
    rel = abs(dz_null) / abs(dz)
    print(f"\n  |ΔZ_null| / |ΔZ_loaded| = {abs(dz_null):.3e} / {abs(dz):.3e} = {rel:.3e}")
    assert rel < 1.0e-3, f"σ = 0 slab is not invisible: {dz_null} vs {dz}"
