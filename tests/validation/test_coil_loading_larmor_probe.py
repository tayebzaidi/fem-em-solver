"""`TH-11` step 1: coil loading at 64 MHz — feasibility/cost probe.

`MAT-6` gated ΔR against Dodd–Deeds at **10 MHz** (1.5834% on the production
projected drive, `20260804T213600Z_MAT-6-step3-gate-final.log`).  Dodd–Deeds is
a **quasi-static** kernel, and §2.1's remaining extrapolation sentence is the
claim that the same machinery still means something at the Larmor frequency.
This module is the first measurement of that: the *same* `MAT-6` fixture,
solved at **64 MHz**, everything else pinned.

**Nothing about the physics is gated here** (§7 `TH-11` step 1, "measurement
only").  What is gated is the solver's own bookkeeping, so that the printed
physics is trustworthy as a *reading*:

* the complex-power identity ``Im Z = 4ω(W_m − W_e)/I′²`` on each solve, at the
  step-2f family bound of 1e-9 — the reaction route integrates ``E·J′`` over
  the whole domain while the energy route never sees ``J′``, so a load on the
  wrong measure or an unreduced rank shows up here and a wrong ``I′`` cancels;
* the σ = 0 negative control (`EX-11`'s): the free solve's ohmic dissipation
  ``½∫σ|E|²`` must be ``+0.0`` **exactly**, not small — a σ-blind pipeline
  would return the loaded value;
* mesh determinism: the same 138 490 cells `MAT-6` step 3 solved.

ΔR and ΔX at 64 MHz are **printed beside the Dodd–Deeds prediction and never
asserted**.  At 64 MHz that closed form is the *comparison*, not the reference
— its own quasi-static assumption is what is under measurement — so the
deviation is the reading this chunk exists for and calling it an "error" would
be a category mistake (§7 trap list).  The deviation is expected to *grow*
with frequency; a large one is the finding.

**Which fixture, and why this rung.**  The §7 entry names "the `MAT-6`
W = 0.25 / ``resolution_near`` 0.0025 fixture (ΔR 0.8835% on record at
10 MHz)" but prices step 1 at "``-n 2`` first at the 10 MHz price (70–75 s on
record)".  Those two are different fixtures: 0.8835% is the *combined-knobs*
mesh (W = 0.25, ``resolution_wire`` = 0.001, 697 401 cells, 178–196 s **per
solve at -n 8**, step 7 Part 2c), while 70–75 s at ``-n 2`` is the step-3
**baseline** (W = 0.15, ``resolution_wire`` = 0.002, 138 490 cells).  A cost
probe is priced from the cheap rung up (implementer.md, "cost-probe unmeasured
cases first"), and 64 MHz on this fixture is unmeasured in every respect, so
this module runs the priced rung — the step-3 baseline at ``-n 2``, whose
10 MHz ΔR record (1.5834%) is the like-for-like comparison for everything
printed below.  Whether the finer fixtures are reachable at 64 MHz is a cost
question this run's timing answers.

**Skin depth is the reason to expect trouble.**  δ = 1/√(π f μ₀ σ) is 15.9 mm
at 10 MHz and 6.3 mm at 64 MHz for σ = 100 S/m, against ``resolution_near`` =
5 mm: ~3.2 cells per δ becomes ~1.3.  If the identity residual blows past 1e-6
that under-resolution (or the conditioning) *is* the step-1 finding — report
and stop, do not refine in-slot (§7).

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_coil_loading_larmor_probe.py -v -s'
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
from fem_em_solver.core.resonance import stored_electric_energy
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.dodd_deeds import coil_impedance_change
from tests.complex_mode import complex_only
from tests.validation.test_dodd_deeds_impedance import (
    FEM_BOX_HALF_WIDTH,
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
from tests.validation.test_dodd_deeds_projected_drive import _reduced_real

# The one thing that moves: 1H at 1.5 T, the frequency `TH-10` gated the lossy
# sphere at (`test_lossy_sphere_fullwave.FREQUENCY_64_HZ`).
LARMOR_FREQUENCY_HZ = 64.0e6

MU_0 = 4.0e-7 * np.pi

# The step-3 baseline mesh, deterministic and on record at this parameter set.
# Re-recorded on the **0.11 image** (dolfinx 0.11 / gmsh 4.15.2) by `OPS-27`
# step 1: 138 490 cells at `-n 2` in
# ``20260827T183121Z_OPS-26-step2f-richardson.log`` and
# ``20260827T185143Z_OPS-26-step2f-probe-30mhz.log``.  It read 138 619 until
# 2026-08-27 — measured on the **0.7.2** image / gmsh 4.11.1 in
# ``20260804T213600Z_MAT-6-step3-gate-final.log`` and step 8's probe ladder —
# and that digit is stale, not a regression: the drift is −0.093%, it is the
# gmsh version bump, and every *physics* reading on this fixture (the ΔR/ΔX
# deviations, the complex-power identities) reproduced its record in the same
# runs.  This one constant is the record for four names in three modules
# (`richardson_ladder` ×2 params, this module, `transition_30mhz`), which is
# why it is held here and imported, never restated.  Version-tag it again if
# the image moves.
NCELLS_BASELINE = 138_490

# `MAT-6` step 3's 10 MHz reading on this exact fixture and drive — the
# like-for-like comparison for everything printed here, cited never recomputed.
DR_REL_10MHZ = 0.015834
DX_RATIO_10MHZ = 0.9200

# Step 2b's house bound for the complex-power identity (1.8128e-10 measured
# there; `PORT-1` step 2e re-ran it on the projected drive).  Both routes are
# built from the same solved field, so this is solve accuracy plus quadrature
# agreement.  §7 names 1e-6 as the level at which a blow-up becomes the
# step-1 finding; the gate stays at the family bound and is not pre-widened.
IDENTITY_TOLERANCE = 1e-9


def _skin_depth(frequency_hz: float, sigma: float) -> float:
    return 1.0 / np.sqrt(np.pi * frequency_hz * MU_0 * sigma)


def _stored_magnetic_energy(e_complex, omega: float, comm) -> float:
    """``W_m = (1/(4μ₀ω²))∫|∇×E|² dV`` [J], peak-phasor, reduced across ranks.

    `PORT-1` step 2b's helper (``test_port_self_impedance_energy``) with ``ω``
    passed in: that copy closes over its own module's 10 MHz ``OMEGA``, which
    is exactly the constant this chunk varies.  μᵣ = 1 everywhere on this
    fixture, so the 1/μ₀ prefactor is the whole material dependence.
    """
    local = fem.assemble_scalar(
        fem.form(ufl.inner(ufl.curl(e_complex), ufl.curl(e_complex)) * ufl.dx)
    )
    total = comm.allreduce(local, op=MPI.SUM)
    return float(np.real(total) / (4.0 * MU_0 * omega**2))


def _solve_projected_at(msh, cell_tags, sigma_slab, frequency_hz, comm, degree: int = 1):
    """``test_dodd_deeds_projected_drive._solve_projected`` with ``f`` freed.

    That helper pins ``FEM_FREQUENCY_HZ``, which is the one thing this chunk
    varies; it is copied rather than parameterised so the `MAT-6` modules keep
    their 10 MHz provenance untouched.  Everything else — the production
    default drive (``project_source`` left on), degree 1, the PEC box — is
    verbatim.

    ``degree`` defaults to 1, so every `TH-11` caller and every recorded number
    is untouched; `TH-12` step 2 passes 2 to run the same fixture at
    second-order N1curl.
    """
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=frequency_hz,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            SLAB_TAG: HomogeneousMaterial(sigma=sigma_slab, epsilon_r=1.0, mu_r=1.0)
        },
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=degree)
    j_magnitude = FEM_CURRENT_A / (np.pi * FEM_WIRE_RADIUS**2)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[WIRE_TAG],
    )
    comm.Barrier()
    elapsed = time.perf_counter() - t0
    projection = solver.projection()
    assert projection is not None, "the default path must have projected the drive"
    return fields, projection.current, elapsed


def _ohmic_power(msh, cell_tags, e_field, sigma_slab, comm) -> float:
    """``½∫_slab σ|E|² dx`` [W] — the dissipation the σ = 0 control zeroes."""
    dx_slab = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(SLAB_TAG,)
    )
    return 0.5 * sigma_slab * _reduced_real(
        ufl.inner(e_field, e_field) * dx_slab, comm
    )


@pytest.fixture(scope="module")
def larmor_loading():
    """One mesh, the loaded/free pair at 64 MHz on the production drive."""
    comm = MPI.COMM_WORLD
    comm.Barrier()
    t_mesh = time.perf_counter()
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
    comm.Barrier()
    t_mesh = time.perf_counter() - t_mesh
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )

    fields_loaded, j_prime, t_loaded = _solve_projected_at(
        msh, cell_tags, FEM_SIGMA_SLAB, LARMOR_FREQUENCY_HZ, comm
    )
    fields_free, j_prime_free, t_free = _solve_projected_at(
        msh, cell_tags, 0.0, LARMOR_FREQUENCY_HZ, comm
    )
    e_loaded, e_free = fields_loaded.e_complex, fields_free.e_complex

    x = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    current = _reduced_real(ufl.inner(j_prime, phi_hat) * dx_wire, comm) / (
        2.0 * np.pi * FEM_LOOP_RADIUS
    )

    # ΔZ exactly as steps 3–8 form it: the reaction integral over the WHOLE
    # domain (J' has support everywhere), reduced before the division.  J' is
    # real, so inner()'s conjugation of its second argument is a no-op.
    def _reaction_z(e_field):
        reaction = comm.allreduce(
            fem.assemble_scalar(fem.form(ufl.inner(e_field, j_prime) * ufl.dx)),
            op=MPI.SUM,
        )
        return complex(-reaction / current**2)

    z_loaded, z_free = _reaction_z(e_loaded), _reaction_z(e_free)
    dz = z_loaded - z_free
    dz_ref = coil_impedance_change(
        LARMOR_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )
    dz_ref_10mhz = coil_impedance_change(
        FEM_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )

    # The bookkeeping gate, per solve: Im Z = 4ω(W_m − W_e)/I'².  W_e uses the
    # REAL epsilon_r field (resonance.stored_electric_energy), so the loss sits
    # in Re Z and this identity is untouched by sigma.
    omega = 2.0 * np.pi * LARMOR_FREQUENCY_HZ
    identities = {}
    for name, fields_, z_reaction in (
        ("loaded", fields_loaded, z_loaded),
        ("free", fields_free, z_free),
    ):
        w_e = stored_electric_energy(fields_, comm=comm)
        w_m = _stored_magnetic_energy(fields_.e_complex, omega, comm)
        im_energy = 4.0 * omega * (w_m - w_e) / current**2
        identities[name] = dict(
            w_e=w_e,
            w_m=w_m,
            im_energy=im_energy,
            im_reaction=z_reaction.imag,
            residual=abs(z_reaction.imag - im_energy) / abs(z_reaction.imag),
        )

    p_loaded = _ohmic_power(msh, cell_tags, e_loaded, FEM_SIGMA_SLAB, comm)
    p_free = _ohmic_power(msh, cell_tags, e_free, 0.0, comm)
    # The dissipation route to ΔR: Re ΔZ = 2P/I'².  Reported, not gated — the
    # reaction route is the one `MAT-6` gated, and whether the two agree at
    # 64 MHz is itself part of the reading.
    dr_dissipation = 2.0 * p_loaded / current**2

    delta_64 = _skin_depth(LARMOR_FREQUENCY_HZ, FEM_SIGMA_SLAB)
    delta_10 = _skin_depth(FEM_FREQUENCY_HZ, FEM_SIGMA_SLAB)
    dr_dev = dz.real / dz_ref.real - 1.0
    dx_ratio = dz.imag / dz_ref.imag

    if comm.rank == 0:
        print(
            f"\n[TH-11 step 1 | f = {LARMOR_FREQUENCY_HZ / 1e6:.1f} MHz | "
            f"W = {FEM_BOX_HALF_WIDTH} m, wire 0.002, near 0.005] {ncells} cells, "
            f"mesh {t_mesh:.1f} s, solves {t_loaded:.1f} s + {t_free:.1f} s at "
            f"-n {comm.size}"
            f"\n[TH-11 step 1] skin depth {delta_64 * 1e3:.2f} mm "
            f"({delta_64 / 0.005:.2f} cells per delta) vs 10 MHz "
            f"{delta_10 * 1e3:.2f} mm ({delta_10 / 0.005:.2f} per delta)"
            f"\n[TH-11 step 1] I' = {current:.6f} A"
            f"\n[TH-11 step 1] FEM   dZ = {dz.real:+.7e} + j({dz.imag:+.7e}) Ohm"
            f"\n[TH-11 step 1] Dodd-Deeds (QUASI-STATIC, the comparison and not "
            f"the reference at this f) dZ = {dz_ref.real:+.7e} + "
            f"j({dz_ref.imag:+.7e}) Ohm"
            f"\n[TH-11 step 1] dR deviation from the quasi-static prediction "
            f"{dr_dev:+.4%}  (same fixture at 10 MHz: {DR_REL_10MHZ:.4%})"
            f"\n[TH-11 step 1] dX ratio {dx_ratio:.4f}  (same fixture at "
            f"10 MHz: {DX_RATIO_10MHZ:.4f})"
            f"\n[TH-11 step 1] quasi-static dZ scaling 10 -> 64 MHz: "
            f"dR x{dz_ref.real / dz_ref_10mhz.real:.3f}, "
            f"dX x{dz_ref.imag / dz_ref_10mhz.imag:.3f}"
            f"\n[TH-11 step 1] dR via dissipation 2P/I'^2 = {dr_dissipation:+.7e} "
            f"Ohm vs reaction {dz.real:+.7e} Ohm (reported)"
            f"\n[TH-11 step 1] complex-power identity residual: loaded "
            f"{identities['loaded']['residual']:.4e}, free "
            f"{identities['free']['residual']:.4e} (bound {IDENTITY_TOLERANCE:.0e})"
            f"\n[TH-11 step 1] sigma-blind control: P_loss loaded "
            f"{p_loaded:+.7e} W vs free {p_free:+.7e} W",
            flush=True,
        )
    return dict(
        ncells=int(ncells),
        current=current,
        dz=dz,
        dz_ref=dz_ref,
        dr_dev=dr_dev,
        dx_ratio=dx_ratio,
        dr_dissipation=dr_dissipation,
        identities=identities,
        p_loaded=p_loaded,
        p_free=p_free,
        t_loaded=t_loaded,
        t_free=t_free,
        drive_mismatch=_reduced_real(
            ufl.inner(j_prime - j_prime_free, j_prime - j_prime_free) * ufl.dx, comm
        )
        / _reduced_real(ufl.inner(j_prime, j_prime) * ufl.dx, comm),
    )


# ---------------------------------------------------------------------------
# the fixture really is `MAT-6`'s, and only the frequency moved
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_mesh_is_the_mat6_step3_baseline(larmor_loading):
    """138 490 cells: the same mesh the 10 MHz record was measured on.

    The mesh is deterministic and frequency never reaches the generator, so a
    different count would mean the comparison against `MAT-6`'s 1.5834% is not
    like-for-like and every number printed above is about a different problem.
    """
    ncells = larmor_loading["ncells"]
    print(f"\n  cells: {ncells} (10 MHz record: {NCELLS_BASELINE})")
    assert ncells == NCELLS_BASELINE, (
        "frequency does not reach the mesh generator, so the count must be the "
        f"step-3 baseline's {NCELLS_BASELINE}; got {ncells}"
    )


@complex_only
@pytest.mark.integration
def test_both_solves_are_driven_by_the_same_projected_current(larmor_loading):
    """Step 3's drive control, re-asserted at 64 MHz.

    ``remove_gradient_content`` sees the mesh, ``J`` and the cell tags but never
    the material, so the loaded and free solves must use the identical ``J′``;
    otherwise the reaction difference measures the drive, not the half-space.
    Bounded at step 3's 1e-24 — a drive that saw the material differs at O(1).
    """
    mismatch = larmor_loading["drive_mismatch"]
    print(f"\n  ||J'_loaded - J'_free||^2 / ||J'||^2 = {mismatch:.3e}")
    assert mismatch < 1.0e-24, f"the two solves used different drives: {mismatch}"


# ---------------------------------------------------------------------------
# the bookkeeping gates: the printed physics is only as good as these
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("which", ["loaded", "free"])
def test_complex_power_identity_holds_at_the_larmor_frequency(larmor_loading, which):
    """``Im Z = 4ω(W_m − W_e)/I′²`` to 1e-9 on each 64 MHz solve.

    Exact for the discrete solution, so this gates bookkeeping rather than
    accuracy: the reaction route integrates ``E·J′`` over the whole domain and
    the energy route never sees ``J′`` at all, so a wrong ``I′`` cancels (it
    divides both) while a load on the wrong measure, a missed projection term
    or an unreduced rank does not.  The bound is the step-2f family's, met at
    1.8128e-10 there; it is not pre-widened for this frequency, because §7
    makes a residual past 1e-6 the step-1 *finding*.
    """
    entry = larmor_loading["identities"][which]
    print(
        f"\n  {which}: Im Z reaction {entry['im_reaction']:.6e} Ω vs energy "
        f"{entry['im_energy']:.6e} Ω → residual {entry['residual']:.4e} "
        f"(W_m {entry['w_m']:.4e} J, W_e {entry['w_e']:.4e} J)"
    )
    assert entry["residual"] < IDENTITY_TOLERANCE, (
        f"complex-power identity broken on the {which} 64 MHz solve: reaction "
        f"{entry['im_reaction']:.6e} Ohm vs energy {entry['im_energy']:.6e} "
        f"Ohm, relative {entry['residual']:.4e}"
    )


@complex_only
@pytest.mark.integration
def test_the_free_solve_dissipates_exactly_nothing_at_64mhz(larmor_loading):
    """σ = 0 ⇒ ``½∫σ|E|²`` is ``+0.0`` exactly; loaded ⇒ positive.

    §7's named negative control (`EX-11`'s), carried up in frequency.  A
    σ-blind pipeline returns the loaded value for both, so the separation is
    infinite by construction and the assertion is exact equality, not a band.
    """
    loaded, free = larmor_loading["p_loaded"], larmor_loading["p_free"]
    print(f"\n  P_loss: loaded {loaded:+.7e} W, free (σ = 0) {free:+.7e} W")
    assert free == 0.0, f"a σ = 0 slab must dissipate exactly nothing, got {free!r}"
    assert loaded > 0.0, f"the loaded slab must dissipate, got {loaded!r}"


# ---------------------------------------------------------------------------
# the reading: printed, never gated
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_loaded_coil_still_dissipates_and_expels_flux_at_64mhz(larmor_loading):
    """Signs only — the weakest statement that survives leaving quasi-statics.

    ΔR > 0 (the conductor dissipates) and ΔX < 0 (it expels flux) are
    consequences of passivity and Lenz's law, not of the Dodd–Deeds kernel, so
    they remain assertable at a frequency where that kernel is only a
    comparison.  The *magnitudes* against Dodd–Deeds are printed by the fixture
    and deliberately not gated: their deviation is the measurement `TH-11`
    exists for, and a band drawn here would assert the thing under test.
    """
    dz = larmor_loading["dz"]
    print(
        f"\n  ΔR = {dz.real:+.7e} Ω, ΔX = {dz.imag:+.7e} Ω; deviation from the "
        f"quasi-static prediction {larmor_loading['dr_dev']:+.4%} (ΔR), ratio "
        f"{larmor_loading['dx_ratio']:.4f} (ΔX) — reported, not gated"
    )
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
