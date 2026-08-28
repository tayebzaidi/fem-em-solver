"""`TH-11` step 2: the resolution rung at 64 MHz — bounding the mesh term.

Step 1 measured coil loading at 64 MHz on the `MAT-6` step-3 baseline mesh
(138 490 cells on 0.11 / 138 619 on 0.7.2, ``resolution_near`` = 0.005) and
found ΔR **+10.2698%** away
from the Dodd–Deeds quasi-static prediction, against **1.5834%** at 10 MHz on
the same fixture and drive.  That deviation is *not yet attributable*: skin
depth falls from 15.9 mm to 6.29 mm between the two frequencies, so the same
5 mm near-field cell size goes from 3.18 to **1.26 cells per δ**, and `MAT-6`
step 8 already showed that knob alone worth **−1.3005 pp** at 10 MHz
(1.5834% → 0.2829%, `20260811T125226Z_MAT-6-step8-gate-final.log`).  The
+10.27% is therefore the sum of the physics `TH-11` is after (displacement
current, retardation — Dodd–Deeds assumes neither) and an under-resolved ohmic
boundary layer.

This module runs step 1's measurement **once more with one knob moved**:
``resolution_near`` 0.005 → 0.0025 on the same W = 0.15 / ``resolution_wire``
0.002 fixture — the `MAT-6` step-8 ladder rung, **418 888 cells** on 0.11
(0.7.2: 417 914), δ/h = 2.52
at 64 MHz.  Everything else is step 1's, imported from its module rather than
re-declared, so the two readings are like-for-like by construction.

**The 10 MHz pair is not re-solved.**  Step 8's projected-drive record on this
exact mesh — ΔR ``+3.2168355e-01`` Ω, 0.2829% off Dodd–Deeds, ΔX ratio 0.9160
— is cited, never recomputed.

**Pre-registered reading (§7 `TH-11` step 2, printed and never asserted; all
three outcomes are findings).**  At 10 MHz this knob moved ΔR by −1.3005 pp.

* deviation stays **> 8%** (moves ≲ 2 pp from +10.27%) ⇒ physics-dominated,
  and a gated trend step becomes scopeable;
* deviation **collapses below 3%** ⇒ the resolution term owned most of it and
  the trend needs finer rungs before any claim;
* in between ⇒ **mixed**, report both terms.

**What is gated** is the solver's own bookkeeping, exactly as step 1: the
complex-power identity on each solve at the step-2f family bound of 1e-9, the
σ = 0 dissipation control at exact ``+0.0``, the drive control at 1e-24, and
the cell count at step 8's rung, exact — 418 888 on 0.11 (0.7.2: 417 914).
Dodd–Deeds at 64 MHz is the
*comparison*, not the reference — its deviation is never called an error
(§7 trap list) — so no band is drawn around the physics.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_coil_loading_larmor_resolution.py -v -s'
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
    IDENTITY_TOLERANCE,
    LARMOR_FREQUENCY_HZ,
    _ohmic_power,
    _skin_depth,
    _solve_projected_at,
    _stored_magnetic_energy,
)
from tests.validation.test_dodd_deeds_impedance import (
    FEM_BOX_HALF_WIDTH,
    FEM_LIFTOFF,
    FEM_LOOP_RADIUS,
    FEM_SIGMA_SLAB,
    FEM_WIRE_RADIUS,
    WIRE_TAG,
    _azimuthal_current_density,
)
from tests.validation.test_dodd_deeds_projected_drive import _reduced_real

# The one knob that moves against step 1.
RESOLUTION_NEAR_FINE = 0.0025
RESOLUTION_NEAR_STEP1 = 0.005

# `MAT-6` step 8's probe count on this exact parameter set, twice on record
# (`test_dodd_deeds_resistance_slab_resolution.NCELLS_FINE`).
# Re-recorded for the dolfinx-0.11 image (`OPS-27` step 2): the 0.7.2 mesher read
# 417 914; 0.11 meshes the same fixture at 418 888 (+0.233%), measured by the
# `OPS-26` census in `20260827T185422Z_OPS-26-step2f-larmor-resolution.log` (and
# again in the slab-resolution log — it is the same mesh).  Exact equality, no band.
# `test_coil_loading_larmor_third_rung` imports this name, so this one edit also
# re-records its `fine` rung (step 1 finding 38's import-graph rule).
NCELLS_FINE = 418_888

# Step 8's 10 MHz reading on this mesh and this drive — cited, not recomputed
# (`20260811T125226Z_MAT-6-step8-gate-final.log`).
DR_REL_10MHZ_FINE = 0.002829
DX_RATIO_10MHZ_FINE = 0.9160
# The same quantities on step 1's coarser rung, for the 2×2 the reading needs
# (`20260814T003445Z_TH-11-step1-larmor-n2.log` and `MAT-6` step 3).
DR_REL_10MHZ_STEP1 = 0.015834
DR_DEV_64MHZ_STEP1 = 0.102698
DX_RATIO_64MHZ_STEP1 = 0.9690

# The pre-registered bands, as literals so the printed classification cannot
# drift from §7's wording.  Printed only — nothing here is asserted.
BAND_PHYSICS_DOMINATED = 0.08
BAND_RESOLUTION_DOMINATED = 0.03


@pytest.fixture(scope="module")
def larmor_loading_fine():
    """One 418 888-cell mesh (0.7.2: 417 914), the loaded/free pair at 64 MHz,
    solved once.

    Step 1's fixture body with ``resolution_near`` moved; the solve helper,
    the energy helpers and the dissipation helper are step 1's own imports, so
    only the mesh parameter differs between the two readings.
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
        resolution_near=RESOLUTION_NEAR_FINE,
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

    # ΔZ as steps 3–8 and step 1 form it: the reaction integral over the WHOLE
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
    dr_dissipation = 2.0 * p_loaded / current**2

    delta_64 = _skin_depth(LARMOR_FREQUENCY_HZ, FEM_SIGMA_SLAB)
    dr_dev = dz.real / dz_ref.real - 1.0
    dx_ratio = dz.imag / dz_ref.imag
    move_pp = 100.0 * (dr_dev - DR_DEV_64MHZ_STEP1)

    if abs(dr_dev) > BAND_PHYSICS_DOMINATED:
        band = "PHYSICS-DOMINATED (> 8%): a gated trend step becomes scopeable"
    elif abs(dr_dev) < BAND_RESOLUTION_DOMINATED:
        band = "RESOLUTION-DOMINATED (< 3%): the trend needs finer rungs first"
    else:
        band = "MIXED (3-8%): both terms material, report both"

    if comm.rank == 0:
        print(
            f"\n[TH-11 step 2 | f = {LARMOR_FREQUENCY_HZ / 1e6:.1f} MHz | "
            f"W = {FEM_BOX_HALF_WIDTH} m, wire 0.002, near "
            f"{RESOLUTION_NEAR_FINE}] {ncells} cells, mesh {t_mesh:.1f} s, "
            f"solves {t_loaded:.1f} s + {t_free:.1f} s at -n {comm.size}"
            f"\n[TH-11 step 2] skin depth {delta_64 * 1e3:.2f} mm "
            f"({delta_64 / RESOLUTION_NEAR_FINE:.2f} cells per delta; step 1's "
            f"rung: {delta_64 / RESOLUTION_NEAR_STEP1:.2f})"
            f"\n[TH-11 step 2] I' = {current:.6f} A"
            f"\n[TH-11 step 2] FEM   dZ = {dz.real:+.7e} + j({dz.imag:+.7e}) Ohm"
            f"\n[TH-11 step 2] Dodd-Deeds (QUASI-STATIC, the comparison and not "
            f"the reference at this f) dZ = {dz_ref.real:+.7e} + "
            f"j({dz_ref.imag:+.7e}) Ohm"
            f"\n[TH-11 step 2] dR deviation from the quasi-static prediction "
            f"{dr_dev:+.4%}  (step 1's coarse rung at 64 MHz: "
            f"{DR_DEV_64MHZ_STEP1:+.4%}; move {move_pp:+.4f} pp)"
            f"\n[TH-11 step 2] the 10 MHz 2x2 for the same knob, cited never "
            f"re-solved: {DR_REL_10MHZ_STEP1:.4%} (near 0.005) -> "
            f"{DR_REL_10MHZ_FINE:.4%} (near 0.0025), i.e. "
            f"{100.0 * (DR_REL_10MHZ_FINE - DR_REL_10MHZ_STEP1):+.4f} pp"
            f"\n[TH-11 step 2] PRE-REGISTERED READING: {band}"
            f"\n[TH-11 step 2] dX ratio {dx_ratio:.4f}  (step 1 at 64 MHz: "
            f"{DX_RATIO_64MHZ_STEP1:.4f}; this mesh at 10 MHz: "
            f"{DX_RATIO_10MHZ_FINE:.4f})"
            f"\n[TH-11 step 2] dR via dissipation 2P/I'^2 = {dr_dissipation:+.7e} "
            f"Ohm vs reaction {dz.real:+.7e} Ohm (reported)"
            f"\n[TH-11 step 2] complex-power identity residual: loaded "
            f"{identities['loaded']['residual']:.4e}, free "
            f"{identities['free']['residual']:.4e} (bound {IDENTITY_TOLERANCE:.0e})"
            f"\n[TH-11 step 2] sigma-blind control: P_loss loaded "
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
        band=band,
        move_pp=move_pp,
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
# the fixture really is step 8's fine rung, and only the frequency moved
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_mesh_is_the_mat6_step8_fine_rung(larmor_loading_fine):
    """418 888 cells (0.7.2: 417 914): the mesh step 8's 10 MHz record was
    measured on.

    The mesh is deterministic and frequency never reaches the generator, so a
    different count means the 0.2829% baseline being cited belongs to a
    different problem and the −1.3005 pp knob move is not the one being
    carried up in frequency.
    """
    ncells = larmor_loading_fine["ncells"]
    print(f"\n  cells: {ncells} (step 8 record: {NCELLS_FINE})")
    assert ncells == NCELLS_FINE, (
        "frequency does not reach the mesh generator, so the count must be "
        f"step 8's {NCELLS_FINE}; got {ncells}"
    )


@complex_only
@pytest.mark.integration
def test_both_solves_are_driven_by_the_same_projected_current(larmor_loading_fine):
    """Step 3's drive control, re-asserted on the fine rung at 64 MHz.

    ``remove_gradient_content`` sees the mesh, ``J`` and the cell tags but
    never the material, so the loaded and free solves must use the identical
    ``J′``; otherwise the reaction difference measures the drive, not the
    half-space.  Bounded at step 3's 1e-24 — a drive that saw the material
    differs at O(1).
    """
    mismatch = larmor_loading_fine["drive_mismatch"]
    print(f"\n  ||J'_loaded - J'_free||^2 / ||J'||^2 = {mismatch:.3e}")
    assert mismatch < 1.0e-24, f"the two solves used different drives: {mismatch}"


# ---------------------------------------------------------------------------
# the bookkeeping gates: the printed physics is only as good as these
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("which", ["loaded", "free"])
def test_complex_power_identity_holds_on_the_fine_rung(larmor_loading_fine, which):
    """``Im Z = 4ω(W_m − W_e)/I′²`` to 1e-9 on each 64 MHz solve.

    Exact for the discrete solution, so this gates bookkeeping rather than
    accuracy — step 1 met it at 1.05e-14 / 4.25e-14 on the coarse rung.  The
    bound is the step-2f family's and is not widened for the 3× larger system:
    if the finer mesh conditions differently, that shows up here first.
    """
    entry = larmor_loading_fine["identities"][which]
    print(
        f"\n  {which}: Im Z reaction {entry['im_reaction']:.6e} Ω vs energy "
        f"{entry['im_energy']:.6e} Ω → residual {entry['residual']:.4e} "
        f"(W_m {entry['w_m']:.4e} J, W_e {entry['w_e']:.4e} J)"
    )
    assert entry["residual"] < IDENTITY_TOLERANCE, (
        f"complex-power identity broken on the {which} 64 MHz fine-rung solve: "
        f"reaction {entry['im_reaction']:.6e} Ohm vs energy "
        f"{entry['im_energy']:.6e} Ohm, relative {entry['residual']:.4e}"
    )


@complex_only
@pytest.mark.integration
def test_the_free_solve_dissipates_exactly_nothing_on_the_fine_rung(
    larmor_loading_fine,
):
    """σ = 0 ⇒ ``½∫σ|E|²`` is ``+0.0`` exactly; loaded ⇒ positive.

    §7's named negative control (`EX-11`'s), carried onto the fine rung.  A
    σ-blind pipeline returns the loaded value for both, so the separation is
    infinite by construction and the assertion is exact equality, not a band.
    """
    loaded, free = larmor_loading_fine["p_loaded"], larmor_loading_fine["p_free"]
    print(f"\n  P_loss: loaded {loaded:+.7e} W, free (σ = 0) {free:+.7e} W")
    assert free == 0.0, f"a σ = 0 slab must dissipate exactly nothing, got {free!r}"
    assert loaded > 0.0, f"the loaded slab must dissipate, got {loaded!r}"


# ---------------------------------------------------------------------------
# the reading: printed, never gated
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_loaded_coil_still_dissipates_and_expels_flux_on_the_fine_rung(
    larmor_loading_fine,
):
    """Signs only — the weakest statement that survives leaving quasi-statics.

    ΔR > 0 (the conductor dissipates) and ΔX < 0 (it expels flux) follow from
    passivity and Lenz's law, not from the Dodd–Deeds kernel, so they remain
    assertable at a frequency where that kernel is only a comparison.  The
    *magnitudes* are printed by the fixture and deliberately not gated: their
    deviation is the measurement `TH-11` exists for, and the pre-registered
    band classification is a reading, not a gate.
    """
    dz = larmor_loading_fine["dz"]
    print(
        f"\n  ΔR = {dz.real:+.7e} Ω, ΔX = {dz.imag:+.7e} Ω; deviation from the "
        f"quasi-static prediction {larmor_loading_fine['dr_dev']:+.4%} "
        f"({larmor_loading_fine['move_pp']:+.4f} pp vs step 1's coarse rung), "
        f"ΔX ratio {larmor_loading_fine['dx_ratio']:.4f} — reported, not gated"
        f"\n  pre-registered reading: {larmor_loading_fine['band']}"
    )
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"
