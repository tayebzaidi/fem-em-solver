"""`TH-11` step 3: the 30 MHz mid-transition point on the step-1 baseline.

`MAT-6` gated ΔR against the **quasi-static** Dodd–Deeds kernel at 10 MHz
(1.5834% on the production projected drive, step 3's baseline fixture).  Step 1
carried the same fixture and drive to 64 MHz and read **+10.2698%**; step 2's
resolution rung then attributed most of that move to the under-resolved ohmic
layer (**+2.8063%** at 2.52 cells/δ, a −7.4635 pp move into the pre-registered
RESOLUTION-DOMINATED band), so **no gated trend claim is scopeable** on this
evidence and none is attempted here.

What is still missing is a *third point* between the two ends of the
eddy→displacement transition.  This module is that point: step 1's module at
**f = 30 MHz**, on step 1's own fixture (W = 0.15, ``resolution_wire`` 0.002,
``resolution_near`` 0.005, **138 619 cells**), everything else pinned and every
helper imported from step 1 rather than re-declared, so the three readings are
like-for-like by construction.

**This is a trend *point*, not a trend *claim*.**  δ = 9.19 mm at 30 MHz for
σ = 100 S/m against the 5 mm near-field cell size is **1.84 cells per δ** —
between step 1's 1.26 and the 10 MHz rung's 3.18, and still under the 2.52 at
which step 2 saw a 2.81% residual.  So this point carries the same unattributed
resolution term as step 1, stated in the print.  Reading the three deviations
as a physics trend would be exactly the inference step 2 refuted.

**What is gated** is the solver's own bookkeeping, exactly as steps 1–2: the
complex-power identity ``Im Z = 4ω(W_m − W_e)/I′²`` on each solve at the
step-2f family bound of 1e-9, the σ = 0 dissipation control at exact ``+0.0``,
the drive control at 1e-24, and the cell count at step 1's exact 138 619.
Dodd–Deeds at 30 MHz is the *comparison*, not the reference — its deviation is
never called an error (§7 trap list) — so no band is drawn around the physics.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_coil_loading_transition_30mhz.py -v -s'
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core.resonance import stored_electric_energy
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.dodd_deeds import coil_impedance_change
from tests.complex_mode import complex_only
from tests.validation.test_coil_loading_larmor_probe import (
    DR_REL_10MHZ,
    DX_RATIO_10MHZ,
    IDENTITY_TOLERANCE,
    LARMOR_FREQUENCY_HZ,
    NCELLS_BASELINE,
    _ohmic_power,
    _skin_depth,
    _solve_projected_at,
    _stored_magnetic_energy,
)
from tests.validation.test_coil_loading_larmor_resolution import (
    DR_DEV_64MHZ_STEP1,
    DX_RATIO_64MHZ_STEP1,
)
from tests.validation.test_dodd_deeds_impedance import (
    FEM_BOX_HALF_WIDTH,
    FEM_FREQUENCY_HZ,
    FEM_LIFTOFF,
    FEM_LOOP_RADIUS,
    FEM_SIGMA_SLAB,
    FEM_WIRE_RADIUS,
    WIRE_TAG,
    _azimuthal_current_density,
)
from tests.validation.test_dodd_deeds_projected_drive import _reduced_real

# The one thing that moves against step 1: a mid-transition frequency, roughly
# geometric between the 10 MHz gate and the 64 MHz probe (√(10·64) = 25.3 MHz).
TRANSITION_FREQUENCY_HZ = 30.0e6

# Step 1's near-field cell size — the rung this point is taken on.
RESOLUTION_NEAR_STEP1 = 0.005


@pytest.fixture(scope="module")
def transition_loading():
    """One 138 619-cell mesh, the loaded/free pair at 30 MHz, solved once.

    Step 1's fixture body with ``LARMOR_FREQUENCY_HZ`` replaced by
    ``TRANSITION_FREQUENCY_HZ``; the solve helper, the energy helpers and the
    dissipation helper are step 1's own imports, so **only the frequency**
    differs between step 1's reading and this one.
    """
    comm = MPI.COMM_WORLD
    comm.Barrier()
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=0.002,
        resolution_near=RESOLUTION_NEAR_STEP1,
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
        msh, cell_tags, FEM_SIGMA_SLAB, TRANSITION_FREQUENCY_HZ, comm
    )
    fields_free, j_prime_free, t_free = _solve_projected_at(
        msh, cell_tags, 0.0, TRANSITION_FREQUENCY_HZ, comm
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

    # ΔZ exactly as `MAT-6` steps 3–8 and `TH-11` steps 1–2 form it: the
    # reaction integral over the WHOLE domain (J' has support everywhere),
    # reduced before the division.  J' is real, so inner()'s conjugation of its
    # second argument is a no-op.
    def _reaction_z(e_field):
        reaction = comm.allreduce(
            fem.assemble_scalar(fem.form(ufl.inner(e_field, j_prime) * ufl.dx)),
            op=MPI.SUM,
        )
        return complex(-reaction / current**2)

    z_loaded, z_free = _reaction_z(e_loaded), _reaction_z(e_free)
    dz = z_loaded - z_free
    dz_ref = coil_impedance_change(
        TRANSITION_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )
    dz_ref_10mhz = coil_impedance_change(
        FEM_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )

    omega = 2.0 * np.pi * TRANSITION_FREQUENCY_HZ
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
    dr_dissipation = 2.0 * p_loaded / current**2

    delta_30 = _skin_depth(TRANSITION_FREQUENCY_HZ, FEM_SIGMA_SLAB)
    delta_10 = _skin_depth(FEM_FREQUENCY_HZ, FEM_SIGMA_SLAB)
    delta_64 = _skin_depth(LARMOR_FREQUENCY_HZ, FEM_SIGMA_SLAB)
    dr_dev = dz.real / dz_ref.real - 1.0
    dx_ratio = dz.imag / dz_ref.imag

    if comm.rank == 0:
        print(
            f"\n[TH-11 step 3 | f = {TRANSITION_FREQUENCY_HZ / 1e6:.1f} MHz | "
            f"W = {FEM_BOX_HALF_WIDTH} m, wire 0.002, near "
            f"{RESOLUTION_NEAR_STEP1}] {ncells} cells, mesh {t_mesh:.1f} s, "
            f"solves {t_loaded:.1f} s + {t_free:.1f} s at -n {comm.size}"
            f"\n[TH-11 step 3] RESOLUTION CAVEAT: skin depth "
            f"{delta_30 * 1e3:.2f} mm = "
            f"{delta_30 / RESOLUTION_NEAR_STEP1:.2f} cells per delta on this "
            f"rung, between 10 MHz ({delta_10 / RESOLUTION_NEAR_STEP1:.2f}) and "
            f"64 MHz ({delta_64 / RESOLUTION_NEAR_STEP1:.2f}), and still under "
            f"the 2.52 at which step 2 read +2.8063% — this point carries the "
            f"same unattributed resolution term as step 1"
            f"\n[TH-11 step 3] I' = {current:.6f} A"
            f"\n[TH-11 step 3] FEM   dZ = {dz.real:+.7e} + j({dz.imag:+.7e}) Ohm"
            f"\n[TH-11 step 3] Dodd-Deeds (QUASI-STATIC, the comparison and not "
            f"the reference at this f) dZ = {dz_ref.real:+.7e} + "
            f"j({dz_ref.imag:+.7e}) Ohm"
            f"\n[TH-11 step 3] dR deviation from the quasi-static prediction "
            f"{dr_dev:+.4%}"
            f"\n[TH-11 step 3] THE THREE POINTS on this same rung (cited, never "
            f"re-solved): 10 MHz {DR_REL_10MHZ:+.4%}, 30 MHz {dr_dev:+.4%}, "
            f"64 MHz {DR_DEV_64MHZ_STEP1:+.4%} — a trend POINT, not a trend "
            f"CLAIM (step 2 attributed most of the 64 MHz figure to mesh)"
            f"\n[TH-11 step 3] dX ratio {dx_ratio:.4f}  (same rung: 10 MHz "
            f"{DX_RATIO_10MHZ:.4f}, 64 MHz {DX_RATIO_64MHZ_STEP1:.4f})"
            f"\n[TH-11 step 3] quasi-static dZ scaling 10 -> 30 MHz: "
            f"dR x{dz_ref.real / dz_ref_10mhz.real:.3f}, "
            f"dX x{dz_ref.imag / dz_ref_10mhz.imag:.3f}"
            f"\n[TH-11 step 3] dR via dissipation 2P/I'^2 = {dr_dissipation:+.7e} "
            f"Ohm vs reaction {dz.real:+.7e} Ohm (reported)"
            f"\n[TH-11 step 3] complex-power identity residual: loaded "
            f"{identities['loaded']['residual']:.4e}, free "
            f"{identities['free']['residual']:.4e} (bound {IDENTITY_TOLERANCE:.0e})"
            f"\n[TH-11 step 3] sigma-blind control: P_loss loaded "
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
        cells_per_delta=delta_30 / RESOLUTION_NEAR_STEP1,
        identities=identities,
        p_loaded=p_loaded,
        p_free=p_free,
        t_mesh=t_mesh,
        t_loaded=t_loaded,
        t_free=t_free,
        drive_mismatch=_reduced_real(
            ufl.inner(j_prime - j_prime_free, j_prime - j_prime_free) * ufl.dx, comm
        )
        / _reduced_real(ufl.inner(j_prime, j_prime) * ufl.dx, comm),
    )


# ---------------------------------------------------------------------------
# the fixture really is step 1's baseline, and only the frequency moved
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_mesh_is_the_step1_baseline(transition_loading):
    """138 619 cells: the same mesh steps 1 and `MAT-6` step 3 were read on.

    The mesh is deterministic and frequency never reaches the generator, so a
    different count would mean the 10 MHz (1.5834%) and 64 MHz (+10.2698%)
    figures printed beside this point belong to a different problem, and the
    three-point comparison is not like-for-like.
    """
    ncells = transition_loading["ncells"]
    print(f"\n  cells: {ncells} (step 1 / MAT-6 step 3 record: {NCELLS_BASELINE})")
    assert ncells == NCELLS_BASELINE, (
        "frequency does not reach the mesh generator, so the count must be the "
        f"step-1 baseline's {NCELLS_BASELINE}; got {ncells}"
    )


@complex_only
@pytest.mark.integration
def test_both_solves_are_driven_by_the_same_projected_current(transition_loading):
    """`MAT-6` step 3's drive control, re-asserted at 30 MHz.

    ``remove_gradient_content`` sees the mesh, ``J`` and the cell tags but never
    the material, so the loaded and free solves must use the identical ``J′``;
    otherwise the reaction difference measures the drive, not the half-space.
    Bounded at step 3's 1e-24 — a drive that saw the material differs at O(1).
    """
    mismatch = transition_loading["drive_mismatch"]
    print(f"\n  ||J'_loaded - J'_free||^2 / ||J'||^2 = {mismatch:.3e}")
    assert mismatch < 1.0e-24, f"the two solves used different drives: {mismatch}"


# ---------------------------------------------------------------------------
# the bookkeeping gates: the printed physics is only as good as these
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("which", ["loaded", "free"])
def test_complex_power_identity_holds_at_30mhz(transition_loading, which):
    """``Im Z = 4ω(W_m − W_e)/I′²`` to 1e-9 on each 30 MHz solve.

    Exact for the discrete solution, so this gates bookkeeping rather than
    accuracy: the reaction route integrates ``E·J′`` over the whole domain and
    the energy route never sees ``J′`` at all, so a wrong ``I′`` cancels (it
    divides both) while a load on the wrong measure, a missed projection term
    or an unreduced rank does not.  The bound is the step-2f family's, met at
    1.05e-14 / 4.25e-14 by step 1 on this exact mesh; it is not widened for a
    third frequency.
    """
    entry = transition_loading["identities"][which]
    print(
        f"\n  {which}: Im Z reaction {entry['im_reaction']:.6e} Ω vs energy "
        f"{entry['im_energy']:.6e} Ω → residual {entry['residual']:.4e} "
        f"(W_m {entry['w_m']:.4e} J, W_e {entry['w_e']:.4e} J)"
    )
    assert entry["residual"] < IDENTITY_TOLERANCE, (
        f"complex-power identity broken on the {which} 30 MHz solve: reaction "
        f"{entry['im_reaction']:.6e} Ohm vs energy {entry['im_energy']:.6e} "
        f"Ohm, relative {entry['residual']:.4e}"
    )


@complex_only
@pytest.mark.integration
def test_the_free_solve_dissipates_exactly_nothing_at_30mhz(transition_loading):
    """σ = 0 ⇒ ``½∫σ|E|²`` is ``+0.0`` exactly; loaded ⇒ positive.

    §7's named negative control (`EX-11`'s), carried to the third frequency.  A
    σ-blind pipeline returns the loaded value for both, so the separation is
    infinite by construction and the assertion is exact equality, not a band.
    """
    loaded, free = transition_loading["p_loaded"], transition_loading["p_free"]
    print(f"\n  P_loss: loaded {loaded:+.7e} W, free (σ = 0) {free:+.7e} W")
    assert free == 0.0, f"a σ = 0 slab must dissipate exactly nothing, got {free!r}"
    assert loaded > 0.0, f"the loaded slab must dissipate, got {loaded!r}"


# ---------------------------------------------------------------------------
# the reading: printed, never gated
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_loaded_coil_still_dissipates_and_expels_flux_at_30mhz(transition_loading):
    """Signs only — the weakest statement that survives leaving quasi-statics.

    ΔR > 0 (the conductor dissipates) and ΔX < 0 (it expels flux) follow from
    passivity and Lenz's law, not from the Dodd–Deeds kernel, so they remain
    assertable at a frequency where that kernel is only a comparison.  The
    *magnitudes* are printed by the fixture and deliberately not gated: their
    deviation is the measurement `TH-11` exists for, and at 1.84 cells/δ this
    rung cannot separate the physics term from the resolution term anyway.
    """
    dz = transition_loading["dz"]
    print(
        f"\n  ΔR = {dz.real:+.7e} Ω, ΔX = {dz.imag:+.7e} Ω; deviation from the "
        f"quasi-static prediction {transition_loading['dr_dev']:+.4%}, ΔX ratio "
        f"{transition_loading['dx_ratio']:.4f} — reported, not gated, at "
        f"{transition_loading['cells_per_delta']:.2f} cells/δ"
    )
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
