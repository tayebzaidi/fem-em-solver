"""`TH-11` step 4: the fixed-frequency Richardson ladder at 10 and 30 MHz.

Steps 1–3 put three coil-loading points on **one** mesh rung
(``resolution_near`` = 0.005, 138 619 cells): the ΔR deviation from the
quasi-static Dodd–Deeds prediction reads **1.5834%** at 10 MHz, **+5.5912%**
at 30 MHz and **+10.2698%** at 64 MHz.  Monotone — but so is the confound:
cells per skin depth falls 3.18 → 1.84 → 1.26 across the same three points,
and step 2 measured that knob worth **−7.4635 pp** at 64 MHz on its own
(+10.2698% → +2.8063% at ``resolution_near`` = 0.0025).  A trend measured
along a line where physics and mesh error move together is not a trend.

This module walks the *other* axis: **h at fixed f**.  Each run solves the
loaded/free pair on one rung at one frequency; running the two rungs
(0.005 → 0.0025, a factor 2 in h, 138 619 → 417 914 cells) at the same
frequency gives the pair the extrapolation needs.  Everything else — fixture,
drive, solver, helpers — is step 1's, imported rather than re-declared, so the
rungs are like-for-like by construction.

**Selection is by environment, so one module serves every rung** (the §7 plan's
"two harness commands, one per f", split further to keep each command inside
one foreground window):

* ``TH11_STEP4_RUNG``      — ``baseline`` (default, 138 619 cells) or ``fine``
  (417 914 cells);
* ``TH11_STEP4_FREQ_MHZ``  — comma list, default ``10,30``.

**What is gated.**  The step-1 identity family on every rung, unchanged and
never widened: the complex-power identity at 1e-9 per solve, the σ = 0
dissipation control at exact ``+0.0``, the drive control at 1e-24, the cell
count exact per rung, and the ΔR/ΔX signs.  Plus the §7 **negative control**:
on the baseline rung the deviation must reproduce its recorded value
(1.5834% / +5.5912%) to within the `MAT-6` step-8 run-to-run floor of 0.01 pp
— a ladder that cannot reproduce its own anchors has changed the fixture
rather than refined it.

**The reading — printed, never gated.**  Two rungs fix two of the three
unknowns in ``d(h) = d₀ + C·hᵖ``, so this module prints a *bracket* rather
than a single extrapolant: Richardson at the assumed rates p = 1 and p = 2
(``d₀ = 2d_fine − d_coarse`` and ``d₀ = d_fine + (d_fine − d_coarse)/3``),
beside the effective rate ``p_eff = log₂(d_coarse/d_fine)`` the pair would
show if the true limit were zero.  The discriminating statement §7 asks for
is across the two frequencies: an extrapolated deviation ~flat in f means no
resolvable physics term below 30 MHz (the transition signal was resolution
all along), one rising in f means the term survives mesh refinement.  Neither
outcome moves §2's extrapolation sentence — that is a review's call on these
numbers, not this module's.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       TH11_STEP4_RUNG=fine TH11_STEP4_FREQ_MHZ=10 \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_coil_loading_richardson_ladder.py -v -s'
"""

from __future__ import annotations

import os
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
    NCELLS_BASELINE,
    _ohmic_power,
    _skin_depth,
    _solve_projected_at,
    _stored_magnetic_energy,
)
from tests.validation.test_coil_loading_larmor_resolution import (
    DR_DEV_64MHZ_STEP1,
    NCELLS_FINE,
    RESOLUTION_NEAR_FINE,
    RESOLUTION_NEAR_STEP1,
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

# The two rungs of the ladder: (near-field cell size, exact cell count).
RUNGS = {
    "baseline": (RESOLUTION_NEAR_STEP1, NCELLS_BASELINE),
    "fine": (RESOLUTION_NEAR_FINE, NCELLS_FINE),
}

# The baseline-rung records this ladder must reproduce, per frequency, in
# fraction: 10 MHz from `MAT-6` step 3 / `TH-11` step 1
# (`20260814T003445Z_TH-11-step1-larmor-n2.log`), 30 MHz from `TH-11` step 3
# (`20260816T183310Z_TH-11-step3-30mhz-n2.log`).
DR_DEV_BASELINE_RECORD = {10.0: 0.015834, 30.0: 0.055912}

# `MAT-6` step 8's fine-rung 10 MHz record on this drive, cited never recomputed
# (`20260811T125226Z_MAT-6-step8-gate-final.log`) — the fine 10 MHz run has an
# independent prior it can be read against.
DR_DEV_FINE_RECORD_10MHZ = 0.002829

# `MAT-6` step 8's run-to-run reality floor on ΔR, in percentage points: the
# bound the baseline reproduction is gated at.
DR_WOBBLE_FLOOR_PP = 0.01

# Step 2's 64 MHz pair, printed for context beside each frequency's bracket.
DR_DEV_64MHZ_FINE = 0.028063


def _rung() -> str:
    rung = os.environ.get("TH11_STEP4_RUNG", "baseline").strip().lower()
    if rung not in RUNGS:
        raise ValueError(f"TH11_STEP4_RUNG must be one of {sorted(RUNGS)}; got {rung!r}")
    return rung


def _frequencies_mhz() -> list[float]:
    raw = os.environ.get("TH11_STEP4_FREQ_MHZ", "10,30")
    freqs = [float(piece) for piece in raw.split(",") if piece.strip()]
    unknown = [f for f in freqs if f not in DR_DEV_BASELINE_RECORD]
    if unknown:
        raise ValueError(
            "the ladder's baseline records only cover "
            f"{sorted(DR_DEV_BASELINE_RECORD)} MHz; got {unknown}"
        )
    return freqs


def _richardson(d_coarse: float, d_fine: float, ratio: float = 2.0) -> dict:
    """Extrapolate ``d(h) = d₀ + C·hᵖ`` from two rungs at assumed rates.

    Two rungs cannot fix ``d₀``, ``C`` and ``p`` at once, so this returns the
    p = 1 and p = 2 extrapolants as a bracket plus the effective rate the pair
    would show if the limit were zero (``d_coarse/d_fine = ratioᵖ``).  Printed,
    never gated.
    """
    out = {
        f"p{int(p)}": d_fine + (d_fine - d_coarse) / (ratio**p - 1.0)
        for p in (1.0, 2.0)
    }
    ratio_of_devs = d_coarse / d_fine if d_fine != 0.0 else np.inf
    out["p_eff"] = (
        float(np.log(abs(ratio_of_devs)) / np.log(ratio))
        if np.isfinite(ratio_of_devs) and ratio_of_devs > 0.0
        else float("nan")
    )
    return out


@pytest.fixture(scope="module", params=_frequencies_mhz(), ids=lambda f: f"{f:g}MHz")
def ladder_rung(request):
    """One mesh at the selected rung, the loaded/free pair at one frequency.

    Step 1's fixture body with **two** knobs freed — ``resolution_near`` and
    the frequency — and nothing else: the solve helper, the energy helpers and
    the dissipation helper are step 1's own imports.
    """
    frequency_mhz = float(request.param)
    frequency_hz = frequency_mhz * 1.0e6
    rung = _rung()
    resolution_near, ncells_expected = RUNGS[rung]

    comm = MPI.COMM_WORLD
    comm.Barrier()
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=0.002,
        resolution_near=resolution_near,
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
        msh, cell_tags, FEM_SIGMA_SLAB, frequency_hz, comm
    )
    fields_free, j_prime_free, t_free = _solve_projected_at(
        msh, cell_tags, 0.0, frequency_hz, comm
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

    # ΔZ exactly as `MAT-6` steps 3–8 and `TH-11` steps 1–3 form it: the
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
        frequency_hz, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )

    omega = 2.0 * np.pi * frequency_hz
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

    # δ is recomputed per frequency — it is not step 3's constant.
    delta = _skin_depth(frequency_hz, FEM_SIGMA_SLAB)
    dr_dev = dz.real / dz_ref.real - 1.0
    dx_ratio = dz.imag / dz_ref.imag
    record = DR_DEV_BASELINE_RECORD[frequency_mhz]
    extrapolation = _richardson(record, dr_dev) if rung == "fine" else None

    if comm.rank == 0:
        head = (
            f"\n[TH-11 step 4 | f = {frequency_mhz:g} MHz | rung {rung} "
            f"(near {resolution_near}) ] {ncells} cells, mesh {t_mesh:.1f} s, "
            f"solves {t_loaded:.1f} s + {t_free:.1f} s at -n {comm.size}"
            f"\n[TH-11 step 4] skin depth {delta * 1e3:.2f} mm at this f "
            f"⇒ {delta / resolution_near:.2f} cells per delta on this rung "
            f"(the other rung: {delta / RUNGS['fine' if rung == 'baseline' else 'baseline'][0]:.2f})"
            f"\n[TH-11 step 4] I' = {current:.6f} A"
            f"\n[TH-11 step 4] FEM   dZ = {dz.real:+.7e} + j({dz.imag:+.7e}) Ohm"
            f"\n[TH-11 step 4] Dodd-Deeds (QUASI-STATIC, the comparison and not "
            f"the reference above 10 MHz) dZ = {dz_ref.real:+.7e} + "
            f"j({dz_ref.imag:+.7e}) Ohm"
            f"\n[TH-11 step 4] dR deviation {dr_dev:+.4%}  (baseline-rung record "
            f"at this f: {record:+.4%})"
            f"\n[TH-11 step 4] dX ratio {dx_ratio:.4f}"
            f"\n[TH-11 step 4] dR via dissipation 2P/I'^2 = {dr_dissipation:+.7e} "
            f"Ohm vs reaction {dz.real:+.7e} Ohm (reported)"
            f"\n[TH-11 step 4] complex-power identity residual: loaded "
            f"{identities['loaded']['residual']:.4e}, free "
            f"{identities['free']['residual']:.4e} (bound {IDENTITY_TOLERANCE:.0e})"
            f"\n[TH-11 step 4] sigma-blind control: P_loss loaded "
            f"{p_loaded:+.7e} W vs free {p_free:+.7e} W"
        )
        if extrapolation is not None:
            head += (
                f"\n[TH-11 step 4] RICHARDSON at f = {frequency_mhz:g} MHz, "
                f"h: {RESOLUTION_NEAR_STEP1} -> {RESOLUTION_NEAR_FINE} "
                f"({record:+.4%} -> {dr_dev:+.4%}, move "
                f"{100.0 * (dr_dev - record):+.4f} pp)"
                f"\n[TH-11 step 4]   extrapolated deviation at h -> 0: "
                f"{extrapolation['p1']:+.4%} (assumed rate p = 1), "
                f"{extrapolation['p2']:+.4%} (p = 2); effective rate if the "
                f"limit were zero: p_eff = {extrapolation['p_eff']:.3f}"
                f"\n[TH-11 step 4]   for context, the same h-pair at 64 MHz "
                f"(steps 1-2): {DR_DEV_64MHZ_STEP1:+.4%} -> "
                f"{DR_DEV_64MHZ_FINE:+.4%}"
                f"\n[TH-11 step 4]   READING (printed, never gated): compare "
                f"this bracket against the other frequency's — flat in f means "
                f"the transition signal was resolution, rising means a physics "
                f"term survives refinement."
            )
        print(head, flush=True)

    return dict(
        frequency_mhz=frequency_mhz,
        frequency_hz=frequency_hz,
        rung=rung,
        resolution_near=resolution_near,
        ncells=int(ncells),
        ncells_expected=ncells_expected,
        current=current,
        dz=dz,
        dz_ref=dz_ref,
        dr_dev=dr_dev,
        dr_dev_record=record,
        dx_ratio=dx_ratio,
        dr_dissipation=dr_dissipation,
        extrapolation=extrapolation,
        identities=identities,
        p_loaded=p_loaded,
        p_free=p_free,
        cells_per_delta=delta / resolution_near,
        t_mesh=t_mesh,
        t_loaded=t_loaded,
        t_free=t_free,
        drive_mismatch=_reduced_real(
            ufl.inner(j_prime - j_prime_free, j_prime - j_prime_free) * ufl.dx, comm
        )
        / _reduced_real(ufl.inner(j_prime, j_prime) * ufl.dx, comm),
    )


# ---------------------------------------------------------------------------
# the rung really is the rung, and only h and f moved
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_rung_has_its_recorded_cell_count(ladder_rung):
    """138 619 / 417 914 exactly — the mesh never sees the frequency.

    Both counts are twice on record (`MAT-6` step 3 and step 8).  A different
    count means the ladder's two rungs are not the two rungs whose 64 MHz move
    step 2 measured, and the extrapolation is over a different problem.
    """
    ncells, expected = ladder_rung["ncells"], ladder_rung["ncells_expected"]
    print(
        f"\n  cells: {ncells} at resolution_near = "
        f"{ladder_rung['resolution_near']} (record: {expected}); "
        f"{ladder_rung['cells_per_delta']:.2f} cells per delta at "
        f"{ladder_rung['frequency_mhz']:g} MHz"
    )
    assert ncells == expected, (
        "frequency does not reach the mesh generator, so the count must be "
        f"the rung's recorded {expected}; got {ncells}"
    )


@complex_only
@pytest.mark.integration
def test_both_solves_are_driven_by_the_same_projected_current(ladder_rung):
    """Step 3's drive control on every rung of the ladder.

    ``remove_gradient_content`` sees the mesh, ``J`` and the cell tags but
    never the material, so the loaded and free solves must use the identical
    ``J′``; otherwise the reaction difference measures the drive rather than
    the half-space.  Bounded at the family's 1e-24 — a drive that saw the
    material differs at O(1).
    """
    mismatch = ladder_rung["drive_mismatch"]
    print(f"\n  ||J'_loaded - J'_free||^2 / ||J'||^2 = {mismatch:.3e}")
    assert mismatch < 1.0e-24, f"the two solves used different drives: {mismatch}"


# ---------------------------------------------------------------------------
# the bookkeeping gates: the printed extrapolation is only as good as these
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("which", ["loaded", "free"])
def test_complex_power_identity_holds_on_this_rung(ladder_rung, which):
    """``Im Z = 4ω(W_m − W_e)/I′²`` to 1e-9 on each solve of the ladder.

    Exact for the discrete solution, so this gates bookkeeping rather than
    accuracy; steps 1–3 met it at ~1e-14.  The bound is the step-2f family's
    and is not widened for the 3× larger fine system or for the frequency —
    if either conditions differently, it shows up here first.
    """
    entry = ladder_rung["identities"][which]
    print(
        f"\n  {which}: Im Z reaction {entry['im_reaction']:.6e} Ω vs energy "
        f"{entry['im_energy']:.6e} Ω → residual {entry['residual']:.4e} "
        f"(W_m {entry['w_m']:.4e} J, W_e {entry['w_e']:.4e} J)"
    )
    assert entry["residual"] < IDENTITY_TOLERANCE, (
        f"complex-power identity broken on the {which} solve at "
        f"{ladder_rung['frequency_mhz']:g} MHz, rung {ladder_rung['rung']}: "
        f"reaction {entry['im_reaction']:.6e} Ohm vs energy "
        f"{entry['im_energy']:.6e} Ohm, relative {entry['residual']:.4e}"
    )


@complex_only
@pytest.mark.integration
def test_the_free_solve_dissipates_exactly_nothing(ladder_rung):
    """σ = 0 ⇒ ``½∫σ|E|²`` is ``+0.0`` exactly; loaded ⇒ positive.

    §7's named negative control (`EX-11`'s), carried onto every rung.  A
    σ-blind pipeline returns the loaded value for both, so the separation is
    infinite by construction and the assertion is exact equality, not a band.
    """
    loaded, free = ladder_rung["p_loaded"], ladder_rung["p_free"]
    print(f"\n  P_loss: loaded {loaded:+.7e} W, free (σ = 0) {free:+.7e} W")
    assert free == 0.0, f"a σ = 0 slab must dissipate exactly nothing, got {free!r}"
    assert loaded > 0.0, f"the loaded slab must dissipate, got {loaded!r}"


@complex_only
@pytest.mark.integration
def test_the_loaded_coil_dissipates_and_expels_flux(ladder_rung):
    """Signs only — the weakest statement that survives leaving quasi-statics.

    ΔR > 0 (the conductor dissipates) and ΔX < 0 (it expels flux) follow from
    passivity and Lenz's law, not from the Dodd–Deeds kernel, so they stay
    assertable at frequencies where that kernel is only a comparison.  The
    magnitudes and the extrapolation are printed by the fixture and
    deliberately not gated.
    """
    dz = ladder_rung["dz"]
    print(
        f"\n  ΔR = {dz.real:+.7e} Ω, ΔX = {dz.imag:+.7e} Ω; deviation "
        f"{ladder_rung['dr_dev']:+.4%}, ΔX ratio {ladder_rung['dx_ratio']:.4f}"
    )
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"


# ---------------------------------------------------------------------------
# the §7 negative control: the ladder must reproduce its own anchors
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_baseline_rung_reproduces_its_recorded_deviation(ladder_rung):
    """1.5834% at 10 MHz, +5.5912% at 30 MHz — to the `MAT-6` wobble floor.

    The extrapolation subtracts the coarse rung's *recorded* deviation from
    the freshly solved fine one, so those records are load-bearing.  This
    asserts they are still what this fixture produces: a ladder that cannot
    reproduce its own anchors has changed the problem rather than refined it.
    The bound is `MAT-6` step 8's measured run-to-run floor on ΔR, 0.01 pp —
    not a fitted tolerance; the re-solve is deterministic and is expected far
    inside it.  On the fine rung the same record is only *printed* (there is
    no fine-rung record at 30 MHz to compare against).
    """
    if ladder_rung["rung"] != "baseline":
        pytest.skip("the reproduction control is the baseline rung's")
    moved_pp = 100.0 * (ladder_rung["dr_dev"] - ladder_rung["dr_dev_record"])
    print(
        f"\n  {ladder_rung['frequency_mhz']:g} MHz baseline rung: "
        f"{ladder_rung['dr_dev']:+.4%} vs record "
        f"{ladder_rung['dr_dev_record']:+.4%} → {moved_pp:+.5f} pp "
        f"(floor {DR_WOBBLE_FLOOR_PP} pp)"
    )
    assert abs(moved_pp) <= DR_WOBBLE_FLOOR_PP, (
        f"the {ladder_rung['frequency_mhz']:g} MHz anchor moved {moved_pp:+.5f} "
        f"pp off its record {ladder_rung['dr_dev_record']:+.4%}, beyond the "
        f"{DR_WOBBLE_FLOOR_PP} pp run-to-run floor: the fixture changed"
    )
