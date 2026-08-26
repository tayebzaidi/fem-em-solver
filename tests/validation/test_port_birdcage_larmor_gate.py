"""`PORT-11` step 2 — the birdcage 4x4 at **64 MHz** under `PORT-9`'s gates.

`PORT-9` closed on 2026-08-25 at 10 MHz: on the gapped `GEO-19` step-B birdcage
with four ``f = 0.5`` lumped sheets terminated at ``Z_p = z0 = 50 Ohm``, the
assembled 4x4 is reciprocal, passive and C4-circulant, and gate (iii') notices a
22.5 deg single-leg rotation.  `PORT-11` step 1 (2026-08-25, 19:30 slot) then
showed the **same fixture at 64 MHz is affordable and resolved**: phantom
cells/delta 5.9213 against a pre-stated floor of 2.0, and no MUMPS frequency
penalty (9.49 / 6.36 s per solve at 64 MHz against 6.56 / 6.50 s at 10 MHz on
this mesh), which is why this module is **standard tier and not heavy**.

This module turns exactly one knob — the frequency — and asks the three gates
whether they still hold where the mission's ports actually are.  Nothing is
reformulated: the mesh, the sheets, the termination, the route
(:func:`~fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep`'s
lumped-sheet route with leg (d3)'s power-wave ``S`` assembly) and the rung
builder are `PORT-9` leg (d1')'s, imported rather than copied
(``_four_port_rung``, which grew a ``frequency_hz`` parameter for this and
defaults to 10 MHz so every `PORT-9` rung is unmoved).

**Three rungs, twelve driven solves.**

* ``control_10mhz`` — undisplaced, 10 MHz.  The in-run frequency control.
* ``larmor_64mhz`` — undisplaced, 64 MHz.  The gated rung.
* ``displaced_64mhz`` — leg 1 rotated by ``LEG_OFFSET_RAD`` = 22.5 deg, 64 MHz.
  The geometric negative control, at the Larmor frequency.

**The three gates**, as the `PORT-9` modules assert them today — imported, never
restated (§7 `PORT-11` step 2; the entry's own 08-23 "<= 5% on Z" text predates
the 2026-08-23 10:30 (iii') tightening and leg (d3)'s power-wave assembly, and
the modules' live bands rule):

* **(i) reciprocity** — ``‖S − Sᵀ‖/‖S‖ <= 1e-3`` (``RECIPROCITY_BAND``, step 2c's);
* **(ii) passivity** — ``σ_max(S) <= 1 + 1e-9`` (``PASSIVITY_SIGMA_TOLERANCE``) and
  every column power sum ``<= 1``;
* **(iii') C4 symmetry** — each circulant class of ``Z`` spreads
  ``<= 0.5%`` (``ADJACENT_SPREAD_BAND``), carrying leg (d)'s own anti-noise
  control: the pooled off-diagonal spread must be at least
  ``POOLED_SEPARATION_FLOOR`` = 10x the worst intra-class spread.

**The frequency control.**  The 10 MHz rung runs in *this* command, on this
mesh, through this code path, and must reproduce leg (d)'s recorded 4x4 to
``1e-6`` entry by entry (``LEG_D_S_MATRIX_10MHZ``, version-tagged below) and leg
(d0)'s recorded terminated column (``LEG_D0_Z_COLUMN``, imported) at its own
print-precision band.  If it does not, the harness moved rather than the
frequency, and nothing the 64 MHz rung reads is comparable to anything `PORT-9`
gated.  Per the (d3c) rule the reciprocity *residual* is a power-wave noise
reading and is recorded as an **order of magnitude only** — never pinned at a
print band, in either direction.

**The negative control** is leg (d1')'s displaced fixture at 64 MHz: the self
and adjacent class spreads must **break** (iii') while gate (i) still holds, so
that a green gated rung means "this layout is C4" rather than "this gate cannot
see geometry at 64 MHz".  Its 10 MHz signature is on record (6.2219 / 7.1142 /
2.8474% displaced against 0.5%, reciprocity 2.259e-14); per the rubric's rule 2
the assertion here is **breakage**, not a fixed amplification factor — the
displaced 10 MHz spreads run 5-14x the band and pinning a factor at a new
frequency would be a prediction this chunk has no basis for.

**Scope.**  64 MHz only; 128 MHz is step 3 and runs only if this gates.  Green
here is a self-consistency identity set on this fixture — reciprocity, passivity
and C4 symmetry — **not** an absolute-accuracy claim: the port model's feed
systematics are still the two-torus ones (`PORT-1` 3b-xviii, `PORT-10`), and no
resonance, tuning or B1+/SAR claim follows from it.  **Negative result** (§7
step 2): a gate that fails at 64 MHz and passes at 10 MHz on the same mesh is
the finding this chunk exists to surface — record the numbers per gate, open a
known-issues entry, stop; never widen.

Cost: standard tier, ``-n 2``, three meshes (~26 s each) and twelve solves
(step 1 priced ~6-9 s each on this mesh at either frequency).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-11-step2 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 400 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_birdcage_larmor_gate.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_leg_offset import LEG_OFFSET_RAD, SHEET_AREA_BAND
from tests.mesh.test_birdcage_port_tags import LEG_COUNT
from tests.validation.test_lossy_sphere_fullwave import FREQUENCY_64_HZ
from tests.validation.test_port_birdcage_four_port import (
    LEG_D0_REPRODUCTION_BAND,
    LEG_D0_Z_COLUMN,
    PASSIVITY_SIGMA_TOLERANCE,
    POOLED_SEPARATION_FLOOR,
)
from tests.validation.test_port_birdcage_leg_offset_sweep import _four_port_rung
from tests.validation.test_port_birdcage_lumped_column import (
    ADJACENT_SPREAD_BAND,
    STEP2_CELL_COUNT,
    STEP2_CELL_COUNT_BAND,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND

# **The frequency control's record**: leg (d)'s 10 MHz 4x4 on `GEO-19` step B's
# 116 085-cell mesh through leg (d3)'s power-wave `S` assembly, as the zero rung
# of leg (d1') printed it — `20260825T110438Z_PORT-9-step3d1.log` lines
# 4661-4665, the run that closed `PORT-9`.  Restated here rather than imported
# because leg (d1') keeps its 4x4 in the log and not in a constant (its own
# anchors are `LEG_D0_Z_COLUMN` and `STEP_B_SIGMA_MAX`, both of which this module
# also checks through the imported column).  Version-tagged: mesh 116 085 cells,
# power-wave route, 0.11 image.
LEG_D_S_MATRIX_10MHZ = np.array(
    [
        [
            -3.712480826e-01 + 1.417750480e-01j,
            +4.671024075e-01 - 4.177746779e-02j,
            +4.369287932e-01 - 7.151541641e-02j,
            +4.671206518e-01 - 4.178189148e-02j,
        ],
        [
            +4.671024075e-01 - 4.177746779e-02j,
            -3.712238083e-01 + 1.417532071e-01j,
            +4.670287303e-01 - 4.174583652e-02j,
            +4.369981460e-01 - 7.153035556e-02j,
        ],
        [
            +4.369287932e-01 - 7.151541641e-02j,
            +4.670287303e-01 - 4.174583652e-02j,
            -3.710071039e-01 + 1.417279925e-01j,
            +4.669559516e-01 - 4.176521967e-02j,
        ],
        [
            +4.671206518e-01 - 4.178189148e-02j,
            +4.369981460e-01 - 7.153035556e-02j,
            +4.669559516e-01 - 4.176521967e-02j,
            -3.711728984e-01 + 1.417796843e-01j,
        ],
    ],
    dtype=np.complex128,
)

# **The frequency control's band**, pre-stated in §7 `PORT-11` step 2 and §9
# item 2: the 10 MHz rung must land on the record above to this relative
# deviation, entry by entry.  It is a reproduction band on a recorded matrix,
# not a physics tolerance, and it does not widen — a miss says the harness moved
# and the 64 MHz readings are uninterpretable, which is a finding, not a licence.
FREQUENCY_CONTROL_BAND = 1.0e-6


def _terminal_power(rung, port_id="P1"):
    """``P = ½·V·conj(I)`` at one port of its own driven solve, for printing.

    Step 1's named limitation applies unchanged: this is the **terminal complex
    power** of the driven port, not the `TH-11` family's volume integral
    ``½∫σE·Ē`` — ``run_n_port_sparameter_sweep`` returns no fields.  At 64 MHz
    the reactive part is physics (the coil's stored energy; step 1 read
    ``|Im P|/Re P`` = 1.755 against 0.337 at 10 MHz), so it is **printed and
    never gated**.
    """
    response = rung["result"].excitation_results[port_id].responses[port_id]
    return 0.5 * complex(response.voltage_v) * np.conjugate(complex(response.current_a))


@pytest.fixture(scope="module")
def larmor_rungs():
    """Three rungs: 10 MHz control, 64 MHz gated, 64 MHz displaced control."""
    zeros = np.zeros(LEG_COUNT)
    displaced = np.zeros(LEG_COUNT)
    displaced[0] = LEG_OFFSET_RAD

    # Control first, then the knob — the frequency is the only thing that moves
    # between the first two rungs, and the geometry the only thing that moves
    # between the second and the third.
    rungs = {
        "control_10mhz": _four_port_rung("control 10 MHz", zeros, FREQUENCY_HZ),
        "larmor_64mhz": _four_port_rung("larmor 64 MHz", zeros, FREQUENCY_64_HZ),
        "displaced_64mhz": _four_port_rung(
            "displaced 64 MHz", displaced, FREQUENCY_64_HZ
        ),
    }

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step2] three rungs at -n 2; offset "
            f"{LEG_OFFSET_RAD:.9f} rad = {np.degrees(LEG_OFFSET_RAD):.4f} deg on "
            f"leg 1 of the displaced rung only; sweeps "
            + " + ".join(f"{r['sweep_time']:.2f} s" for r in rungs.values()),
            flush=True,
        )
        for name, rung in rungs.items():
            power = _terminal_power(rung)
            print(
                f"    {name:16s} f = {rung['frequency_hz']:.6e} Hz  "
                f"P1 terminal P = {power:+.9e} VA  |Im P|/Re P = "
                f"{abs(power.imag) / abs(power.real):.6f}  "
                "(printed, never gated — step 1's limitation (a))",
                flush=True,
            )
    return rungs


@complex_only
def test_all_three_rungs_drove_four_solved_field_ports(larmor_rungs):
    """Structural: twelve driven field solves on three conforming rungs.

    None of this is a gate; all of it is what the gates need in order to mean
    anything.  ``is_placeholder=False`` separates a solved field from the retired
    `PORT-0` coupling heuristic; the two undisplaced rungs' cell counts say this
    is still the fixture `PORT-9` gated, so its records are comparable; and every
    sheet is still a clean rectangular port, so a class spread below cannot be
    blamed on a port that broke.
    """
    for name, rung in larmor_rungs.items():
        r = rung["result"]
        assert not r.is_placeholder, (
            f"rung '{name}': the sweep returned is_placeholder=True — it fell "
            "back to the PORT-0 coupling heuristic, so no impedance here came "
            "off a field"
        )
        assert rung["z"].shape == (LEG_COUNT, LEG_COUNT)
        assert rung["s"].shape == (LEG_COUNT, LEG_COUNT)
        assert np.all(np.isfinite(rung["z"].real))
        assert np.all(np.isfinite(rung["z"].imag))
        assert set(r.excitation_results) == {f"P{i}" for i in range(1, LEG_COUNT + 1)}
        for driven, response in r.excitation_results.items():
            assert response.responses[driven].is_driven
            for pid, est in response.responses.items():
                if pid != driven:
                    assert not est.is_driven
        for s in rung["sheets"]:
            assert abs(s["area_ratio_full"] - 1.0) < SHEET_AREA_BAND, (
                f"rung '{name}' sheet {s['tag']}: the full sheet reads "
                f"{s['area_ratio_full']:.12f} of the closed-form dx*g against the "
                f"{SHEET_AREA_BAND:.0e} band — this port is not the clean "
                "`GEO-18` construction"
            )
            assert s["out_of_plane"] < 1.0e-12, (
                f"rung '{name}' sheet {s['tag']}: spreads {s['out_of_plane']:.3e} "
                "m along its own azimuthal direction — the narrowed facet set is "
                "not a plane"
            )
            assert s["w"] < s["w_full"], (
                f"rung '{name}' sheet {s['tag']}: A/h = {s['w']:.9e} m is not "
                f"below the full sheet's radial extent {s['w_full']:.9e} m — the "
                "interior-width filter did not run"
            )

    assert larmor_rungs["control_10mhz"]["frequency_hz"] == pytest.approx(FREQUENCY_HZ)
    assert larmor_rungs["larmor_64mhz"]["frequency_hz"] == pytest.approx(
        FREQUENCY_64_HZ
    )
    assert larmor_rungs["displaced_64mhz"]["frequency_hz"] == pytest.approx(
        FREQUENCY_64_HZ
    )
    for name in ("control_10mhz", "larmor_64mhz"):
        ratio = larmor_rungs[name]["cells"] / STEP2_CELL_COUNT
        assert abs(ratio - 1.0) < STEP2_CELL_COUNT_BAND, (
            f"rung '{name}' meshed {larmor_rungs[name]['cells']} cells against "
            f"`GEO-19` step B's record {STEP2_CELL_COUNT}; this is not the fixture "
            "`PORT-9` gated, so nothing measured on it is comparable"
        )


@complex_only
def test_the_ten_megahertz_rung_reproduces_leg_d(larmor_rungs):
    """**The frequency control.**  10 MHz gives back leg (d)'s recorded 4x4.

    The frequency is the only knob this module turns between the first two
    rungs, so the 10 MHz one must land on the ``S`` leg (d1')'s zero rung printed
    when it closed `PORT-9` (``LEG_D_S_MATRIX_10MHZ``, entry by entry to 1e-6)
    and on leg (d0)'s recorded terminated column (``LEG_D0_Z_COLUMN``, imported,
    at its own print-precision band).  A miss means the harness moved, not the
    physics, and the 64 MHz gates below would be measuring that move.

    The reciprocity *residual* is printed for the record but deliberately not
    compared digit for digit: per the (d3c) rule power-wave readings sit at
    ~1e-16…1e-11 and reproduce in order of magnitude only.
    """
    rung = larmor_rungs["control_10mhz"]
    s_dev = np.abs(rung["s"] - LEG_D_S_MATRIX_10MHZ) / np.abs(LEG_D_S_MATRIX_10MHZ)
    column = rung["z"][:, 0]
    z_dev = np.abs(column - LEG_D0_Z_COLUMN) / np.abs(LEG_D0_Z_COLUMN)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step2] FREQUENCY CONTROL: the 10 MHz rung vs leg (d)'s "
            f"record (`20260825T110438Z_PORT-9-step3d1.log`), band "
            f"{FREQUENCY_CONTROL_BAND:.0e} relative on every S entry:",
            flush=True,
        )
        for row in range(LEG_COUNT):
            print(
                f"    S_{row + 1}k rel. deviation  "
                + "  ".join(f"{d:.3e}" for d in s_dev[row]),
                flush=True,
            )
        print(
            f"    worst S deviation {float(np.max(s_dev)):.3e}  "
            f"{'PASS' if float(np.max(s_dev)) < FREQUENCY_CONTROL_BAND else 'MISS'}",
            flush=True,
        )
        for k, (z, rec, dev) in enumerate(zip(column, LEG_D0_Z_COLUMN, z_dev), start=1):
            print(
                f"    Z_{k}1 {z:+.9e}  leg (d0) record {rec:+.9e}  rel. deviation "
                f"{dev:.3e}  "
                f"{'PASS' if dev < LEG_D0_REPRODUCTION_BAND else 'MISS'}",
                flush=True,
            )
        print(
            f"    ||S - S^T||/||S|| = {rung['reciprocity']:.9e} (order of "
            "magnitude only, the (d3c) rule — reported, not compared)",
            flush=True,
        )

    worst_s = float(np.max(s_dev))
    assert worst_s < FREQUENCY_CONTROL_BAND, (
        f"the 10 MHz rung deviates {worst_s:.3e} from leg (d)'s recorded 4x4 "
        f"against the pre-stated {FREQUENCY_CONTROL_BAND:.0e} band — the mesh or "
        "the code path moved rather than the frequency, so nothing this module "
        "reads at 64 MHz is comparable to what `PORT-9` gated"
    )
    worst_z = float(np.max(z_dev))
    assert worst_z < LEG_D0_REPRODUCTION_BAND, (
        f"the 10 MHz rung's terminated column deviates {worst_z:.3e} from leg "
        f"(d0)'s record against its {LEG_D0_REPRODUCTION_BAND:.0e} "
        "print-precision band — this is not the solve `PORT-9` recorded"
    )


@complex_only
def test_the_birdcage_is_reciprocal_at_64_mhz(larmor_rungs):
    """**Gate (i) at 64 MHz.**  ``‖S − Sᵀ‖/‖S‖ <= 1e-3``.

    Four independent solves, each driving a different leg, assembled column by
    column from power waves.  The network is passive and made of reciprocal
    materials at every frequency, so ``S`` must be symmetric; the displacement
    current in the saline load is what is new here, not the reciprocity.  The
    band is step 2c's, imported and unmoved.  A miss at 64 MHz with the 10 MHz
    rung green on the same mesh is precisely the finding `PORT-11` exists to
    surface — record it and stop; never widen.
    """
    rung = larmor_rungs["larmor_64mhz"]
    ratio = rung["reciprocity"]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step2] GATE (i) reciprocity at 64 MHz (band "
            f"{RECIPROCITY_BAND:.0e}, step 2c's, unmoved):\n"
            f"    ||S - S^T||/||S|| = {ratio:.9e}  "
            f"{'PASS' if ratio <= RECIPROCITY_BAND else 'MISS'}   "
            f"(10 MHz control on the same mesh: "
            f"{larmor_rungs['control_10mhz']['reciprocity']:.9e})\n"
            f"    ||Z - Z^T||/||Z|| = {rung['z_reciprocity']:.9e} (reported)",
            flush=True,
        )

    assert ratio <= RECIPROCITY_BAND, (
        f"at 64 MHz the birdcage 4x4 reads ||S - S^T||/||S|| = {ratio:.9e} "
        f"against the pre-stated {RECIPROCITY_BAND:.0e} band, with the 10 MHz "
        f"control on the same mesh at "
        f"{larmor_rungs['control_10mhz']['reciprocity']:.9e} — a finding about "
        "the lumped-sheet route in the displacement-current regime (§7 "
        "`PORT-11` step 2, negative result: record per gate, open a "
        "known-issues entry, stop; never widen)"
    )


@complex_only
def test_the_birdcage_is_passive_at_64_mhz(larmor_rungs):
    """**Gate (ii) at 64 MHz.**  ``σ_max(S) <= 1 + 1e-9``, column power sums ``<= 1``.

    A network of lossy conductors, saline and air cannot return more power to its
    ports than is fed in, and that is a statement about energy rather than about
    frequency.  At 64 MHz the load stores substantially more of what it is fed
    (step 1: ``|Im P|/Re P`` 1.755 against 0.337 at 10 MHz), which is exactly the
    regime in which a route that mishandled reactive power would show up here.
    Both readings are printed to nine digits as the 64 MHz reproduction record.
    """
    rung = larmor_rungs["larmor_64mhz"]
    sigma_max = float(np.max(rung["sigma"]))
    column_power = rung["column_power"]
    power_max = float(np.max(column_power))
    report = rung["result"].sanity_report

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step2] GATE (ii) passivity at 64 MHz (tolerance "
            f"{PASSIVITY_SIGMA_TOLERANCE:.0e}, pre-stated 2026-08-16, unmoved):\n"
            f"    sigma_max(S) = {sigma_max:.9f}  "
            f"{'PASS' if sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE else 'MISS'}"
            f"   (PORT-5 metric: {report.passivity_max_sigma:.9f}; 10 MHz control "
            f"{float(np.max(larmor_rungs['control_10mhz']['sigma'])):.9f})\n"
            f"    max column power sum = {power_max:.9f}  "
            f"{'PASS' if power_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE else 'MISS'}"
            f"   (PORT-5 metric: {report.passivity_max_column_power_sum:.9f})",
            flush=True,
        )

    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"at 64 MHz sigma_max(S) = {sigma_max:.9f} exceeds 1 by more than "
        f"{PASSIVITY_SIGMA_TOLERANCE:.0e} — the assembled 4x4 is active, a "
        "passivity finding about the lumped-sheet route in the "
        "displacement-current regime (§7 `PORT-11` step 2: record and stop)"
    )
    for k, value in enumerate(column_power, start=1):
        assert value <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
            f"at 64 MHz column {k} of S carries power sum {value:.9f} > 1 + "
            f"{PASSIVITY_SIGMA_TOLERANCE:.0e} — driving port {k} returns more "
            "power than it is fed"
        )


@complex_only
def test_the_impedance_matrix_is_c4_circulant_at_64_mhz(larmor_rungs):
    """**Gate (iii') at 64 MHz.**  Each circulant class of ``Z`` spreads ``<= 0.5%``.

    The four legs sit at 0/90/180/270 deg on a layout that is C4-invariant by
    construction, so ``Z`` must be circulant at any frequency: one self term, one
    adjacent term, one opposite term.  Taken on ``Z`` rather than ``S`` so the
    termination convention does not enter, with the band imported from leg (c)
    and (iii')-tightened, unmoved.

    Leg (d)'s own anti-noise control travels with it: the *pooled* off-diagonal
    class must spread at least 10x the worst intra-class spread, or the gate is
    passing on noise rather than resolving the adjacent/opposite structure leg
    (d0) separated.  The three 10 MHz spreads on this mesh are 0.0553 / 0.0353 /
    0.0214% at a separation of 166.7x, and both are printed beside the 64 MHz
    readings so the review can see what the frequency did to the margin.
    """
    rung = larmor_rungs["larmor_64mhz"]
    control = larmor_rungs["control_10mhz"]
    spreads = rung["spreads"]
    pooled = rung["pooled"]
    worst = max(spreads.values())
    separation = pooled / worst if worst > 0.0 else np.inf

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step2] GATE (iii') C4 circulant symmetry of Z at 64 MHz "
            f"(band {ADJACENT_SPREAD_BAND * 100:.1f}%, leg (c)'s as tightened "
            f"2026-08-23, unmoved):",
            flush=True,
        )
        for name in ("self", "adjacent", "opposite"):
            members = rung["classes"][name]
            print(
                f"    {name:9s} n = {members.size}  mean |Z| = "
                f"{np.mean(np.abs(members)):.9e} Ohm  spread "
                f"{spreads[name] * 100:.4f}%  "
                f"{'INSIDE' if spreads[name] <= ADJACENT_SPREAD_BAND else 'MISS'}"
                f"   (10 MHz control {control['spreads'][name] * 100:.4f}%)",
                flush=True,
            )
        print(
            f"    control: pooled off-diagonal spread {pooled * 100:.4f}% vs "
            f"worst intra-class {worst * 100:.4f}%  =>  separation "
            f"{separation:.4f}x (floor {POOLED_SEPARATION_FLOOR:.0f}x)  "
            f"{'PASS' if separation >= POOLED_SEPARATION_FLOOR else 'MISS'}"
            f"   (10 MHz control "
            f"{control['pooled'] / max(control['spreads'].values()):.4f}x)",
            flush=True,
        )

    for name, value in spreads.items():
        assert value <= ADJACENT_SPREAD_BAND, (
            f"at 64 MHz the {name} class of Z spreads {value * 100:.4f}% against "
            f"the pre-stated {ADJACENT_SPREAD_BAND * 100:.1f}% band (10 MHz "
            f"control on the same mesh: {control['spreads'][name] * 100:.4f}%) — "
            "on an undisplaced, C4-invariant layout that is a finding about the "
            "route or the mesh in the displacement-current regime (§7 `PORT-11` "
            "step 2, negative result: record all three spreads and both "
            "controls, stop; never widen)"
        )
    assert separation >= POOLED_SEPARATION_FLOOR, (
        f"at 64 MHz the pooled off-diagonal class spreads {pooled * 100:.4f}%, "
        f"only {separation:.4f}x the worst intra-class spread "
        f"{worst * 100:.4f}%, against the pre-stated "
        f"{POOLED_SEPARATION_FLOOR:.0f}x floor — gate (iii') is not resolving the "
        "adjacent/opposite structure at this frequency, so its passing says "
        "nothing about C4 symmetry"
    )


@complex_only
def test_gate_iii_still_detects_the_broken_c4_at_64_mhz(larmor_rungs):
    """**The geometric negative control at 64 MHz.**  Displaced, (iii') breaks.

    A symmetry gate that has only ever been shown a symmetric layout *at this
    frequency* is a consistency check, not a validated gate — leg (d1') made that
    argument at 10 MHz and it does not transfer by fiat.  So leg 1 is rotated
    22.5 deg off the C4 layout at 64 MHz and the ``{Z_ii}`` and ``{Z_i,i±1}``
    classes must **exceed** the band, while gate (i) still holds on the same
    rung: reciprocity is a property of the materials and not of the layout, so
    holding it here separates "the gate measured geometry" from "the displaced
    solve fell apart".

    Per the rubric's rule 2 the assertion is **breakage, not a factor**: the
    displaced 10 MHz signature ran 5-14x the band (6.2219 / 7.1142 / 2.8474%),
    and pinning an amplification at a new frequency would be a prediction this
    chunk has no basis for.  The ``{Z_i,i+2}`` opposite class stays **reported,
    not gated**, by the 2026-08-25 03:00 review's pre-ruling — it is physically
    the flattest of the three.

    A displaced self *or* adjacent spread inside the band is the pre-stated
    negative result: gate (iii') is blind at 64 MHz at this grain, the numbers
    are recorded, step 2 does not close and the review re-specifies (iii') — it
    is never a licence to widen anything.
    """
    gated = larmor_rungs["larmor_64mhz"]["spreads"]
    disp = larmor_rungs["displaced_64mhz"]["spreads"]
    rung = larmor_rungs["displaced_64mhz"]
    sigma_max = float(np.max(rung["sigma"]))

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step2] NEGATIVE CONTROL at 64 MHz (band "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}% — the displaced rung must EXCEED "
            f"it on self and adjacent; opposite is reported only):",
            flush=True,
        )
        for cls in ("self", "adjacent", "opposite"):
            role = "gated" if cls in ("self", "adjacent") else "reported"
            verdict = (
                "EXCEEDS (detected)"
                if disp[cls] > ADJACENT_SPREAD_BAND
                else "inside (blind)"
            )
            print(
                f"    {cls:9s} [{role:8s}]  undisplaced {gated[cls] * 100:9.4f}%   "
                f"displaced {disp[cls] * 100:9.4f}%   amplification "
                f"{disp[cls] / gated[cls]:12.2f}x   {verdict}",
                flush=True,
            )
        print(
            f"    displaced rung gate (i): ||S - S^T||/||S|| = "
            f"{rung['reciprocity']:.9e} (band {RECIPROCITY_BAND:.0e})  "
            f"{'PASS' if rung['reciprocity'] <= RECIPROCITY_BAND else 'MISS'}"
            f";  sigma_max(S) = {sigma_max:.9f}",
            flush=True,
        )

    assert rung["reciprocity"] <= RECIPROCITY_BAND, (
        f"the displaced 64 MHz rung reads ||S - S^T||/||S|| = "
        f"{rung['reciprocity']:.9e} against the pre-stated "
        f"{RECIPROCITY_BAND:.0e} band — the class spreads below would be "
        "measuring a broken solve rather than a broken symmetry (never widen)"
    )
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"the displaced 64 MHz rung reads sigma_max(S) = {sigma_max:.9f} — the "
        "assembled 4x4 is active, so its class spreads say nothing about C4"
    )
    for cls in ("self", "adjacent"):
        assert disp[cls] > ADJACENT_SPREAD_BAND, (
            f"at 64 MHz with leg 1 rotated {np.degrees(LEG_OFFSET_RAD):.1f} deg "
            f"off the C4 layout the {cls} class of Z still spreads only "
            f"{disp[cls] * 100:.4f}%, inside the "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}% band it passes on the symmetric "
            f"layout ({gated[cls] * 100:.4f}%) — gate (iii') does not detect a "
            "broken C4 at this frequency and grain, so its passing above is a "
            "consistency check and not a symmetry gate (§7 `PORT-11` step 2, "
            "negative result: record and stop; never widen (i)-(iii'))"
        )
