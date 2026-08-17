"""`TH-11` step 5: the 64 MHz third rung — an h → 0 bracket at Larmor.

Step 4 walked the h-ladder at **fixed f** and read **flat in f**: refining
``resolution_near`` 0.005 → 0.0025 moves the ΔR deviation from quasi-static
Dodd–Deeds by −1.8663 pp at 10 MHz and −4.4793 pp at 30 MHz, and the h → 0
brackets overlap at ~−1% with no rise in f.  But those brackets are 10/30 MHz
only.  64 MHz — the frequency §2's headline caveat is about — has **two** rungs
on record (**+10.2698%** at 1.26 cells/δ, step 1; **+2.8063%** at 2.52 cells/δ,
step 2) and no extrapolation at all, because two rungs cannot fix ``d₀``, ``C``
and ``p`` at once and step 4 declined the third rung as unaffordable in its own
slot.

This module buys that rung: ``resolution_near`` = **0.00125** at 64 MHz, 5.04
cells/δ, on the same W = 0.15 / ``resolution_wire`` 0.002 fixture as every
other rung — imported from step 1's module rather than re-declared, so the
three readings are like-for-like by construction.  With three rungs at a fixed
refinement ratio of 2 the fit is determined: ``d₀``, ``C`` and ``p`` all come
out of the triple, and the p = 1 / p = 2 bracket step 4 printed becomes a
bracket *plus* a measured rate.

**Cost-probe binding (§7 step 5).**  The rung is unpriced, so selection is by
environment and the first command is a probe:

* ``TH11_STEP5_RUNG`` — ``third`` (default, ``near`` = 0.00125) or ``fine``
  (0.0025, 417 914 cells — the negative-control rung);
* ``TH11_STEP5_MODE`` — ``probe`` (mesh + the **loaded** solve only, no ΔZ and
  no ladder) or ``full`` (default: the loaded/free pair, ΔZ, and the ladder).

In ``probe`` mode the cell count is gated against ``NCELLS_THIRD_CEILING``
(3.4 M, 8× the fine rung): a mesh past that ceiling is §7's stop condition, and
shrinking the rung is a review's decision, not a run's.

**What is gated** — the step-1/2/4 identity family, unchanged and never
widened: the complex-power identity ``Im Z = 4ω(W_m − W_e)/I′²`` at 1e-9 per
solve, the σ = 0 dissipation control at exact ``+0.0``, the drive control at
1e-24, the ΔR/ΔX signs, and — on the ``fine`` rung — §7's **negative control**:
step 2's **+2.8063%** reproduced to the `MAT-6` step-8 run-to-run floor of
0.01 pp.  Dodd–Deeds at 64 MHz is the *comparison*, not the reference, so no
band is drawn around the physics.

**The reading — printed, never gated.**  The three-rung extrapolation and its
bracket, beside step 4's 10/30 MHz brackets.  A 64 MHz bracket that overlaps
them says the eddy→displacement signal was resolution all the way up to
Larmor; one that does not overlap is the more informative outcome — a genuine
frequency-dependent term that survives refinement.  Neither moves §2's
extrapolation sentence: that is a review's call on these numbers.

Run (complex build only)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       TH11_STEP5_RUNG=third TH11_STEP5_MODE=probe \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_coil_loading_larmor_third_rung.py -v -s'
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
    LARMOR_FREQUENCY_HZ,
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
from tests.validation.test_coil_loading_richardson_ladder import (
    DR_DEV_64MHZ_FINE,
    DR_WOBBLE_FLOOR_PP,
    _richardson,
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

# The third rung: one more factor of 2 in h below step 2's fine rung.
RESOLUTION_NEAR_THIRD = 0.00125

# §7's stop condition, as a literal so the gate cannot drift from the wording:
# 8× the 417 914-cell fine rung.  A count past this means the rung is not
# affordable in a scheduled slot and shrinking it is the review's call.
NCELLS_THIRD_CEILING = 3_400_000

# The 64 MHz ladder as it stands before this step, cited never recomputed:
# step 1 (`20260814T003445Z_TH-11-step1-larmor-n2.log`, near 0.005) and step 2
# (`20260816T003251Z_TH-11-step2-resolution-n2.log`, near 0.0025).  Both are
# magnitudes of a *positive* deviation — the sign is explicit here so the
# printed ladder cannot silently flip it (§7 step-5 trap list).
DR_DEV_64MHZ_LADDER = {
    RESOLUTION_NEAR_STEP1: +DR_DEV_64MHZ_STEP1,
    RESOLUTION_NEAR_FINE: +DR_DEV_64MHZ_FINE,
}

# Step 4's printed h → 0 brackets at the two affordable frequencies
# (`20260817T033547Z_TH-11-step4-fine-10mhz.log`,
# `20260817T034258Z_TH-11-step4-fine-30mhz.log`), for the overlap comparison
# §7 step 5 asks for.  Fractions, signed.
STEP4_BRACKET_10MHZ = (-0.021492, -0.009050)
STEP4_BRACKET_30MHZ = (-0.033675, -0.003812)

# `TH-11` step 5a's rank-invariance band.  Every 64 MHz record on the ladder was
# measured at `-n 2`; step 5a buys `-n 8` for the third rung (the 10:30 review's
# decision (b)), which changes the domain decomposition and therefore the
# assembly and solve *arithmetic order* — not the discretisation.  The review
# pre-stated the band before any -n 8 number existed: one order above the
# `MAT-6` step-8 same-rank run-to-run floor of 0.01 pp, and 28× below the
# 2.8 pp signal.  This is a band on a *different* comparison than
# `DR_WOBBLE_FLOOR_PP` (same ranks, repeat run), never a widening of it: at
# `-n 2` the 0.01 pp floor still applies, unchanged.
RANK_INVARIANCE_BAND_PP = 0.1

# The rank count every 64 MHz record on the ladder was measured at.
RECORD_NRANKS = 2

# The rungs this module can mesh: near-field cell size → expected cell count
# (``None`` where there is no record yet, i.e. the rung being priced).
RUNGS = {
    "fine": (RESOLUTION_NEAR_FINE, NCELLS_FINE),
    "third": (RESOLUTION_NEAR_THIRD, None),
}


def _rung() -> str:
    rung = os.environ.get("TH11_STEP5_RUNG", "third").strip().lower()
    if rung not in RUNGS:
        raise ValueError(f"TH11_STEP5_RUNG must be one of {sorted(RUNGS)}; got {rung!r}")
    return rung


def _mode() -> str:
    mode = os.environ.get("TH11_STEP5_MODE", "full").strip().lower()
    if mode not in ("probe", "full"):
        raise ValueError(f"TH11_STEP5_MODE must be 'probe' or 'full'; got {mode!r}")
    return mode


def _three_rung_fit(d_coarse: float, d_mid: float, d_fine: float, ratio: float = 2.0):
    """Fit ``d(h) = d₀ + C·hᵖ`` on three rungs at a fixed refinement ratio.

    With ``h`` halved twice the system closes: the differences satisfy
    ``(d_coarse − d_mid)/(d_mid − d_fine) = ratioᵖ``, which fixes ``p``, and
    then ``d₀ = d_fine − (d_mid − d_fine)²/(d_coarse − 2d_mid + d_fine)``
    (Aitken's Δ²).  Returns ``None`` for the fit when the three points are not
    monotonically converging — the denominator vanishing or the difference
    ratio being non-positive both mean the triple does not describe a single
    power law, and inventing a rate from it would be worse than printing none.
    Printed, never gated.
    """
    num, den = d_coarse - d_mid, d_mid - d_fine
    curvature = d_coarse - 2.0 * d_mid + d_fine
    out = {"num": num, "den": den, "curvature": curvature, "p": None, "d0": None}
    if den != 0.0 and curvature != 0.0 and num / den > 0.0:
        out["p"] = float(np.log(num / den) / np.log(ratio))
        out["d0"] = float(d_fine - den**2 / curvature)
    return out


@pytest.fixture(scope="module")
def third_rung():
    """One mesh at the selected rung; the loaded solve, and the free one unless probing.

    Step 1's fixture body with ``resolution_near`` freed and the free solve made
    optional — in ``probe`` mode the point of the command is the price of the
    mesh and one solve, and buying the second before that price is known is what
    §7 forbids.
    """
    rung, mode = _rung(), _mode()
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
    delta = _skin_depth(LARMOR_FREQUENCY_HZ, FEM_SIGMA_SLAB)
    if comm.rank == 0:
        print(
            f"\n[TH-11 step 5 | PROBE | rung {rung} (near {resolution_near})] "
            f"{ncells} cells, mesh {t_mesh:.1f} s at -n {comm.size}; "
            f"{delta / resolution_near:.2f} cells per delta at 64 MHz "
            f"(ceiling for the third rung: {NCELLS_THIRD_CEILING} cells)",
            flush=True,
        )

    fields_loaded, j_prime, t_loaded = _solve_projected_at(
        msh, cell_tags, FEM_SIGMA_SLAB, LARMOR_FREQUENCY_HZ, comm
    )
    if comm.rank == 0:
        print(
            f"[TH-11 step 5 | PROBE] loaded solve {t_loaded:.1f} s at "
            f"-n {comm.size} on {ncells} cells",
            flush=True,
        )
    e_loaded = fields_loaded.e_complex

    x = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    current = _reduced_real(ufl.inner(j_prime, phi_hat) * dx_wire, comm) / (
        2.0 * np.pi * FEM_LOOP_RADIUS
    )

    # ΔZ exactly as steps 1–4 form it: the reaction integral over the WHOLE
    # domain (J' has support everywhere), reduced before the division.  J' is
    # real, so inner()'s conjugation of its second argument is a no-op.
    def _reaction_z(e_field):
        reaction = comm.allreduce(
            fem.assemble_scalar(fem.form(ufl.inner(e_field, j_prime) * ufl.dx)),
            op=MPI.SUM,
        )
        return complex(-reaction / current**2)

    z_loaded = _reaction_z(e_loaded)
    omega = 2.0 * np.pi * LARMOR_FREQUENCY_HZ

    def _identity(fields_, z_reaction):
        w_e = stored_electric_energy(fields_, comm=comm)
        w_m = _stored_magnetic_energy(fields_.e_complex, omega, comm)
        im_energy = 4.0 * omega * (w_m - w_e) / current**2
        return dict(
            w_e=w_e,
            w_m=w_m,
            im_energy=im_energy,
            im_reaction=z_reaction.imag,
            residual=abs(z_reaction.imag - im_energy) / abs(z_reaction.imag),
        )

    identities = {"loaded": _identity(fields_loaded, z_loaded)}
    p_loaded = _ohmic_power(msh, cell_tags, e_loaded, FEM_SIGMA_SLAB, comm)

    out = dict(
        rung=rung,
        mode=mode,
        nranks=int(comm.size),
        resolution_near=resolution_near,
        ncells=int(ncells),
        ncells_expected=ncells_expected,
        cells_per_delta=delta / resolution_near,
        current=current,
        identities=identities,
        p_loaded=p_loaded,
        p_free=None,
        dz=None,
        dz_ref=None,
        dr_dev=None,
        dx_ratio=None,
        dr_dissipation=None,
        drive_mismatch=None,
        ladder=None,
        t_mesh=t_mesh,
        t_loaded=t_loaded,
        t_free=None,
    )
    if mode == "probe":
        if comm.rank == 0:
            print(
                f"[TH-11 step 5 | PROBE] stopping after the loaded solve as §7 "
                f"directs: mesh {t_mesh:.1f} s + solve {t_loaded:.1f} s = "
                f"{t_mesh + t_loaded:.1f} s of the priced pair; the free solve "
                f"and the ladder are the second command's.",
                flush=True,
            )
        return out

    fields_free, j_prime_free, t_free = _solve_projected_at(
        msh, cell_tags, 0.0, LARMOR_FREQUENCY_HZ, comm
    )
    z_free = _reaction_z(fields_free.e_complex)
    identities["free"] = _identity(fields_free, z_free)
    p_free = _ohmic_power(msh, cell_tags, fields_free.e_complex, 0.0, comm)

    dz = z_loaded - z_free
    dz_ref = coil_impedance_change(
        LARMOR_FREQUENCY_HZ, FEM_LOOP_RADIUS, FEM_LIFTOFF, FEM_SIGMA_SLAB
    )
    dr_dev = dz.real / dz_ref.real - 1.0
    dx_ratio = dz.imag / dz_ref.imag
    dr_dissipation = 2.0 * p_loaded / current**2

    ladder = None
    if rung == "third":
        d_coarse = DR_DEV_64MHZ_LADDER[RESOLUTION_NEAR_STEP1]
        d_mid = DR_DEV_64MHZ_LADDER[RESOLUTION_NEAR_FINE]
        ladder = dict(
            d_coarse=d_coarse,
            d_mid=d_mid,
            d_fine=dr_dev,
            # Step 4's two-rung bracket, on the finest available pair so the
            # 64 MHz number is comparable with the 10/30 MHz ones.
            bracket=_richardson(d_mid, dr_dev),
            fit=_three_rung_fit(d_coarse, d_mid, dr_dev),
        )

    out.update(
        p_free=p_free,
        dz=dz,
        dz_ref=dz_ref,
        dr_dev=dr_dev,
        dx_ratio=dx_ratio,
        dr_dissipation=dr_dissipation,
        ladder=ladder,
        t_free=t_free,
        drive_mismatch=_reduced_real(
            ufl.inner(j_prime - j_prime_free, j_prime - j_prime_free) * ufl.dx, comm
        )
        / _reduced_real(ufl.inner(j_prime, j_prime) * ufl.dx, comm),
    )

    if comm.rank == 0:
        head = (
            f"\n[TH-11 step 5 | f = {LARMOR_FREQUENCY_HZ / 1e6:.1f} MHz | rung "
            f"{rung} (near {resolution_near})] {ncells} cells, mesh "
            f"{t_mesh:.1f} s, solves {t_loaded:.1f} s + {t_free:.1f} s at "
            f"-n {comm.size}"
            f"\n[TH-11 step 5] skin depth {delta * 1e3:.2f} mm at 64 MHz "
            f"⇒ {delta / resolution_near:.2f} cells per delta on this rung"
            f"\n[TH-11 step 5] I' = {current:.6f} A"
            f"\n[TH-11 step 5] FEM   dZ = {dz.real:+.7e} + j({dz.imag:+.7e}) Ohm"
            f"\n[TH-11 step 5] Dodd-Deeds (QUASI-STATIC, the comparison and not "
            f"the reference at this f) dZ = {dz_ref.real:+.7e} + "
            f"j({dz_ref.imag:+.7e}) Ohm"
            f"\n[TH-11 step 5] dR deviation {dr_dev:+.4%}"
            f"\n[TH-11 step 5] dX ratio {dx_ratio:.4f}"
            f"\n[TH-11 step 5] dR via dissipation 2P/I'^2 = "
            f"{dr_dissipation:+.7e} Ohm vs reaction {dz.real:+.7e} Ohm (reported)"
            f"\n[TH-11 step 5] complex-power identity residual: loaded "
            f"{identities['loaded']['residual']:.4e}, free "
            f"{identities['free']['residual']:.4e} (bound {IDENTITY_TOLERANCE:.0e})"
            f"\n[TH-11 step 5] sigma-blind control: P_loss loaded "
            f"{p_loaded:+.7e} W vs free {p_free:+.7e} W"
        )
        if rung == "fine":
            head += (
                f"\n[TH-11 step 5] NEGATIVE CONTROL (gated): step 2's fine-rung "
                f"record {DR_DEV_64MHZ_FINE:+.4%} vs this run's {dr_dev:+.4%} "
                f"⇒ {100.0 * (dr_dev - DR_DEV_64MHZ_FINE):+.5f} pp "
                f"(floor {DR_WOBBLE_FLOOR_PP} pp)"
            )
        if ladder is not None:
            fit = ladder["fit"]
            rate = "not a single power law" if fit["p"] is None else f"{fit['p']:.3f}"
            limit = (
                "unavailable (the triple is not monotonically converging)"
                if fit["d0"] is None
                else f"{fit['d0']:+.4%}"
            )
            head += (
                f"\n[TH-11 step 5] LADDER at 64 MHz, h: "
                f"{RESOLUTION_NEAR_STEP1} -> {RESOLUTION_NEAR_FINE} -> "
                f"{RESOLUTION_NEAR_THIRD} ({ladder['d_coarse']:+.4%} -> "
                f"{ladder['d_mid']:+.4%} -> {ladder['d_fine']:+.4%}; moves "
                f"{100.0 * (ladder['d_mid'] - ladder['d_coarse']):+.4f} pp then "
                f"{100.0 * (ladder['d_fine'] - ladder['d_mid']):+.4f} pp)"
                f"\n[TH-11 step 5]   three-rung fit d(h) = d0 + C*h^p: measured "
                f"rate p = {rate}, extrapolated deviation d0 = {limit}"
                f"\n[TH-11 step 5]   two-rung bracket on the finest pair (step "
                f"4's form): {ladder['bracket']['p1']:+.4%} (assumed p = 1), "
                f"{ladder['bracket']['p2']:+.4%} (p = 2); p_eff = "
                f"{ladder['bracket']['p_eff']:.3f}"
                f"\n[TH-11 step 5]   step 4's brackets for comparison: 10 MHz "
                f"[{STEP4_BRACKET_10MHZ[0]:+.4%}, {STEP4_BRACKET_10MHZ[1]:+.4%}], "
                f"30 MHz [{STEP4_BRACKET_30MHZ[0]:+.4%}, "
                f"{STEP4_BRACKET_30MHZ[1]:+.4%}]"
                f"\n[TH-11 step 5]   READING (printed, never gated): a 64 MHz "
                f"bracket overlapping those two says the eddy->displacement "
                f"signal was resolution all the way to Larmor; one that does "
                f"not overlap is a frequency-dependent term surviving "
                f"refinement."
            )
        print(head, flush=True)
    return out


# ---------------------------------------------------------------------------
# the probe's own gate: is this rung affordable at all
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_rung_is_inside_the_priced_ceiling(third_rung):
    """§7's stop condition for the third rung: ≤ 3.4 M cells (8× the fine rung).

    The count is the whole point of the probe command — the third rung has no
    record, and everything downstream (solve time, memory, whether the pair
    fits one foreground window) scales off it.  On the ``fine`` rung the count
    is instead gated against its exact record, twice on record via `MAT-6`
    step 8; the mesh never sees the frequency, so a different count there means
    the negative control is being run on a different problem.
    """
    ncells, expected = third_rung["ncells"], third_rung["ncells_expected"]
    print(
        f"\n  cells: {ncells} at resolution_near = {third_rung['resolution_near']}"
        f" ({third_rung['cells_per_delta']:.2f} cells per delta at 64 MHz); "
        + (f"record {expected}" if expected else f"ceiling {NCELLS_THIRD_CEILING}")
    )
    if expected is not None:
        assert ncells == expected, (
            "frequency does not reach the mesh generator, so the count must be "
            f"the rung's recorded {expected}; got {ncells}"
        )
    else:
        assert ncells <= NCELLS_THIRD_CEILING, (
            f"the third rung meshed to {ncells} cells, past §7's "
            f"{NCELLS_THIRD_CEILING} ceiling: it is not affordable in a "
            "scheduled slot, and shrinking it is the review's decision"
        )


# ---------------------------------------------------------------------------
# the bookkeeping gates: the printed ladder is only as good as these
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("which", ["loaded", "free"])
def test_complex_power_identity_holds_on_this_rung(third_rung, which):
    """``Im Z = 4ω(W_m − W_e)/I′²`` to 1e-9 on each solve of this rung.

    Exact for the discrete solution, so this gates bookkeeping rather than
    accuracy; steps 1–4 met it at ≤ 8.16e-14 across nine solves.  The bound is
    the step-2f family's and is not widened for the third rung's larger system
    — if 8× the unknowns condition differently, it shows up here first.
    """
    if which not in third_rung["identities"]:
        pytest.skip("the free solve is the second command's, not the probe's")
    entry = third_rung["identities"][which]
    print(
        f"\n  {which}: Im Z reaction {entry['im_reaction']:.6e} Ω vs energy "
        f"{entry['im_energy']:.6e} Ω → residual {entry['residual']:.4e} "
        f"(W_m {entry['w_m']:.4e} J, W_e {entry['w_e']:.4e} J)"
    )
    assert entry["residual"] < IDENTITY_TOLERANCE, (
        f"complex-power identity broken on the {which} 64 MHz solve, rung "
        f"{third_rung['rung']}: reaction {entry['im_reaction']:.6e} Ohm vs "
        f"energy {entry['im_energy']:.6e} Ohm, relative {entry['residual']:.4e}"
    )


@complex_only
@pytest.mark.integration
def test_the_free_solve_dissipates_exactly_nothing(third_rung):
    """σ = 0 ⇒ ``½∫σ|E|²`` is ``+0.0`` exactly; loaded ⇒ positive.

    §7's named negative control (`EX-11`'s), carried onto the third rung.  A
    σ-blind pipeline returns the loaded value for both, so the separation is
    infinite by construction and the assertion is exact equality, not a band.
    """
    loaded, free = third_rung["p_loaded"], third_rung["p_free"]
    print(f"\n  P_loss: loaded {loaded:+.7e} W, free (σ = 0) {free!r} W")
    assert loaded > 0.0, f"the loaded slab must dissipate, got {loaded!r}"
    if free is None:
        pytest.skip("the free solve is the second command's, not the probe's")
    assert free == 0.0, f"a σ = 0 slab must dissipate exactly nothing, got {free!r}"


@complex_only
@pytest.mark.integration
def test_both_solves_are_driven_by_the_same_projected_current(third_rung):
    """The drive control on this rung: identical ``J′`` for loaded and free.

    ``remove_gradient_content`` sees the mesh, ``J`` and the cell tags but
    never the material, so the reaction *difference* measures the half-space
    rather than the drive.  Bounded at the family's 1e-24 — a drive that saw
    the material differs at O(1).
    """
    mismatch = third_rung["drive_mismatch"]
    if mismatch is None:
        pytest.skip("the free solve is the second command's, not the probe's")
    print(f"\n  ||J'_loaded - J'_free||^2 / ||J'||^2 = {mismatch:.3e}")
    assert mismatch < 1.0e-24, f"the two solves used different drives: {mismatch}"


@complex_only
@pytest.mark.integration
def test_the_loaded_coil_dissipates_and_expels_flux(third_rung):
    """Signs only — the weakest statement that survives leaving quasi-statics.

    ΔR > 0 (the conductor dissipates) and ΔX < 0 (it expels flux) follow from
    passivity and Lenz's law, not from the Dodd–Deeds kernel, so they stay
    assertable at a frequency where that kernel is only a comparison.  The
    magnitudes and the whole ladder are printed by the fixture and deliberately
    not gated.
    """
    dz = third_rung["dz"]
    if dz is None:
        pytest.skip("ΔZ needs the free solve — the second command's, not the probe's")
    print(
        f"\n  ΔR = {dz.real:+.7e} Ω, ΔX = {dz.imag:+.7e} Ω; deviation "
        f"{third_rung['dr_dev']:+.4%}, ΔX ratio {third_rung['dx_ratio']:.4f}"
    )
    assert dz.real > 0.0, f"the conductor must dissipate, got ΔR = {dz.real}"
    assert dz.imag < 0.0, f"the conductor must expel flux, got ΔX = {dz.imag}"


# ---------------------------------------------------------------------------
# the §7 negative control: the ladder must reproduce its own middle rung
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_fine_rung_reproduces_step2s_recorded_deviation(third_rung):
    """+2.8063% at 64 MHz, ``near`` = 0.0025 — to the `MAT-6` wobble floor.

    The three-rung fit subtracts step 1's and step 2's *recorded* deviations
    from the freshly solved third rung, so both records are load-bearing; this
    asserts the middle one is still what this fixture produces.  A ladder that
    cannot reproduce its own middle rung has changed the problem rather than
    refined it.  At the record's own ``-n 2`` the bound is `MAT-6` step 8's
    measured run-to-run floor on ΔR, 0.01 pp — not a fitted tolerance; the
    re-solve is deterministic and is expected far inside it.

    At any other rank count this is instead step 5a's **rank-invariance
    control**, and the bound is the review's pre-stated
    ``RANK_INVARIANCE_BAND_PP`` = 0.1 pp: a different decomposition changes the
    order of the assembly and Krylov arithmetic, which the same-rank floor was
    never a measurement of.  Both bands are pre-stated; neither widens the
    other, and the run prints which one it is being held to.
    """
    if third_rung["rung"] != "fine":
        pytest.skip("the reproduction control is the fine (middle) rung's")
    if third_rung["dr_dev"] is None:
        pytest.skip("the reproduction control needs the pair, not the probe")
    nranks = third_rung["nranks"]
    same_ranks = nranks == RECORD_NRANKS
    band = DR_WOBBLE_FLOOR_PP if same_ranks else RANK_INVARIANCE_BAND_PP
    kind = (
        f"run-to-run floor at the record's own -n {RECORD_NRANKS}"
        if same_ranks
        else f"step 5a rank-invariance band at -n {nranks} (record is -n {RECORD_NRANKS})"
    )
    moved_pp = 100.0 * (third_rung["dr_dev"] - DR_DEV_64MHZ_FINE)
    print(
        f"\n  64 MHz fine rung at -n {nranks}: {third_rung['dr_dev']:+.4%} vs step "
        f"2's record {DR_DEV_64MHZ_FINE:+.4%} → {moved_pp:+.5f} pp "
        f"(band {band} pp — {kind})"
    )
    assert abs(moved_pp) <= band, (
        f"the 64 MHz fine-rung anchor moved {moved_pp:+.5f} pp off step 2's "
        f"record {DR_DEV_64MHZ_FINE:+.4%}, beyond the {band} pp {kind}: "
        "the reading is rank-dependent, which blocks step 5b"
    )
