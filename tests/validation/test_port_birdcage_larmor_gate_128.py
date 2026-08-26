"""`PORT-11` step 3 — the birdcage 4x4 at **128 MHz** under `PORT-9`'s gates.

Step 2 (2026-08-26) put the gapped `GEO-19` step-B birdcage, four ``f = 0.5``
lumped sheets terminated at ``Z_p = z0 = 50 Ohm``, through `PORT-9`'s three gates
at **64 MHz** and all three held: reciprocity 2.581325834e-14 vs 1e-3,
``σ_max(S)`` 0.999721388 <= 1 + 1e-9, C4 class spreads 0.0573 / 0.0599 / 0.0370%
vs (iii')'s 0.5%.  This module is **step 2 repeated with one constant changed** —
``FREQUENCY_128_HZ``, imported from the `TH-10` module beside its 64 MHz sibling,
never restated.  The mesh, the sheets, the termination, the route
(:func:`~fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep`'s
lumped-sheet route with leg (d3)'s power-wave ``S`` assembly), the materials
(`TH-10` saline, ``σ = 0.5 S/m``, ``εᵣ = 78.0``, frequency-independent by
construction) and the rung builder are all `PORT-9` leg (d1')'s, imported rather
than copied.

**Why 128 MHz is not just "64 MHz again".**  At the `TH-10` saline values the
loss tangent ``σ/(ωε)`` falls from 11.5 (10 MHz) through 1.80 (64 MHz) to
**0.90** here: the phantom crosses from conduction-dominated to
**displacement-dominated**, which is the regime change this step exists to probe.

**Three rungs, twelve driven solves.**

* ``control_10mhz`` — undisplaced, 10 MHz.  The in-run frequency control.
* ``larmor_128mhz`` — undisplaced, 128 MHz.  The gated rung.
* ``displaced_128mhz`` — leg 1 rotated by ``LEG_OFFSET_RAD`` = 22.5 deg,
  128 MHz.  The geometric negative control, at the higher Larmor frequency.

The 64 MHz rung is **not** re-solved here.  §9 item 7 allows it as a second
control *if it fits the tier*, and it does not: step 2 measured 59 s per rung
(``17 passed in 177.48s`` for three), so a fourth rung lands at ~240 s against
§5.1's 180 s standard ceiling.  Step 2's digits are on record instead, carried
below as version-tagged constants and **printed beside every 128 MHz reading**
for the differential — printed, never gated (this module asserts against the
`PORT-9` bands, not against step 2's numbers).

**The pre-gate stop rule (pre-stated §9 item 7, binding, measured never assumed).**
The mesh is frozen by the `GEO-19` record, so raising the frequency lowers the
resolution.  Step 1's floor was phantom ``cells/δ >= 2.0`` and 64 MHz cleared it
at 5.9213; at 128 MHz δ *rises* slightly in the displacement-dominated limit, so
that floor is not what tightens.  What tightens is **cells per wavelength in the
phantom** — 21.8936 at 64 MHz, predicted ~12.5 here.  Both readings are measured
on the solved mesh and printed against their 64 MHz values **before any gate is
read**, and if ``cells/λ`` lands below ``PHANTOM_CELLS_PER_LAMBDA_FLOOR`` = 10
the three gates below **are not to be read as a pass**: they fail loudly through
:func:`_require_resolution` with the resolution as the finding.  A mesh
refinement at 128 MHz is a `GEO` sizing chunk and a review's to commission, never
an in-slot knob.

**The three gates**, as the `PORT-9` modules assert them today — imported, never
restated:

* **(i) reciprocity** — ``‖S − Sᵀ‖/‖S‖ <= 1e-3`` (``RECIPROCITY_BAND``, step 2c's);
* **(ii) passivity** — ``σ_max(S) <= 1 + 1e-9`` (``PASSIVITY_SIGMA_TOLERANCE``) and
  every column power sum ``<= 1``;
* **(iii') C4 symmetry** — each circulant class of ``Z`` spreads ``<= 0.5%``
  (``ADJACENT_SPREAD_BAND``), carrying leg (d)'s anti-noise control: the pooled
  off-diagonal spread must be at least ``POOLED_SEPARATION_FLOOR`` = 10x the
  worst intra-class spread.

**The frequency control.**  The 10 MHz rung runs in *this* command, on this mesh,
through this code path, and must reproduce leg (d)'s recorded 4x4 entry by entry
to ``FREQUENCY_CONTROL_BAND`` = 1e-6 (``LEG_D_S_MATRIX_10MHZ``, imported from the
64 MHz module where step 2 version-tagged it) and leg (d0)'s recorded terminated
column (``LEG_D0_Z_COLUMN``) at its own print-precision band.  Step 2 measured
1.158e-10 and 2.568e-10 respectively.  Per the (d3c) rule the reciprocity
*residual* is a power-wave noise reading recorded as an **order of magnitude
only**, never pinned at a print band in either direction.

**The negative control** is leg (d1')'s displaced fixture at 128 MHz: the self
and adjacent class spreads must **break** (iii') while gate (i) still holds.  Per
the rubric's rule 2 the assertion is **breakage, not a fixed factor** — the
64 MHz signature was self 12.8947% / adjacent 27.7509% with (i) at 1.252e-15, and
pinning an amplification at a new frequency would be a prediction this step has
no basis for.

**Scope.**  128 MHz only.  Green here is a self-consistency identity set on this
one fixture — reciprocity, passivity, C4 symmetry — and **no resonance, tuning or
absolute-accuracy claim** follows from it, exactly as at 64 MHz: the port model's
feed systematics are still the two-torus ones (`PORT-1` 3b-xviii, `PORT-10`).
**Negative result** (§9 item 7): a gate that fails at 128 MHz and passes at
64 MHz *on the same mesh* is the finding this step exists to surface — record the
numbers per gate against their 64 MHz values, open a known-issues entry, stop;
never widen, and never re-mesh to chase a pass.

Cost: standard tier, ``-n 2``, three meshes (~26 s each) and twelve solves
(step 1 measured MUMPS frequency-flat on this mesh: 9.49 / 6.36 s at 64 MHz
against 6.50-6.56 s at 10 MHz).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-11-step3 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 400 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_birdcage_larmor_gate_128.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_leg_offset import LEG_OFFSET_RAD, SHEET_AREA_BAND
from tests.mesh.test_birdcage_port_tags import LEG_COUNT
from tests.validation.test_lossy_sphere_fullwave import (
    FREQUENCY_64_HZ,
    FREQUENCY_128_HZ,
    SALINE_EPSILON_R,
    SALINE_SIGMA,
)
from tests.validation.test_port_birdcage_four_port import (
    LEG_D0_REPRODUCTION_BAND,
    LEG_D0_Z_COLUMN,
    PASSIVITY_SIGMA_TOLERANCE,
    POOLED_SEPARATION_FLOOR,
)
from tests.validation.test_port_birdcage_larmor_gate import (
    FREQUENCY_CONTROL_BAND,
    LEG_D_S_MATRIX_10MHZ,
    _terminal_power,
)
from tests.validation.test_port_birdcage_larmor_probe import (
    AIR_CELL_TAG,
    PHANTOM_CELLS_PER_DELTA_FLOOR,
    _propagation_constants,
    _tag_cell_size,
)
from tests.validation.test_port_birdcage_leg_offset_sweep import _four_port_rung
from tests.validation.test_port_birdcage_lumped_column import (
    ADJACENT_SPREAD_BAND,
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
    STEP2_CELL_COUNT,
    STEP2_CELL_COUNT_BAND,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND

# **The pre-gate resolution floor**, pre-stated in §9 item 7 (2026-08-26): fewer
# than this many cells per wavelength in the phantom at 128 MHz and the three
# gates below are **not to be read as a pass** — the reading is the finding and
# the follow-on is a `GEO` phantom-sizing chunk commissioned by a review.  It is
# not a band to widen and it is not a physics tolerance; the frozen `GEO-19` mesh
# is what makes it a question at all.
PHANTOM_CELLS_PER_LAMBDA_FLOOR = 10.0

# **Step 2's 64 MHz record**, version-tagged: `20260826T110434Z_PORT-11-step2.log`
# on the 116 085-cell `GEO-19` step-B mesh through leg (d3)'s power-wave `S`
# assembly, 0.11 image.  The 64 MHz rung is not re-solved here (see the module
# docstring's tier arithmetic), so these are carried as **printed comparison
# constants only** — nothing in this module is asserted against them, and the
# gates below are asserted against the `PORT-9` bands exactly as step 2 did.
STEP2_64MHZ = {
    "reciprocity": 2.581325834e-14,
    "sigma_max": 0.999721388,
    "column_power_max": 0.804704664,
    "spreads": {"self": 0.000573, "adjacent": 0.000599, "opposite": 0.000370},
    "displaced_spreads": {"self": 0.128947, "adjacent": 0.277509},
    "displaced_reciprocity": 1.252073140e-15,
    "cells_per_delta_phantom": 5.9213,
    "cells_per_lambda_phantom": 21.8936,
    "im_over_re_power": 1.755210,
}


def _resolution(rung):
    """Phantom/air cell sizes on a solved rung, and what they resolve at 10/64/128.

    ``h_mean`` is a property of the mesh and not of the frequency, so one solved
    rung supplies the cell size for every frequency in the table; the media
    constants come from :func:`_propagation_constants` (step 1's, imported — the
    full lossy-medium branch, never the good-conductor approximation, which at a
    loss tangent of 0.90 would be wrong by more than tens of percent).
    """
    comm = MPI.COMM_WORLD
    msh, cell_tags = rung["mesh"], rung["cell_tags"]
    sizes = {
        "conductor": _tag_cell_size(msh, cell_tags, CONDUCTOR_CELL_TAG, comm),
        "air": _tag_cell_size(msh, cell_tags, AIR_CELL_TAG, comm),
        "phantom": _tag_cell_size(msh, cell_tags, PHANTOM_CELL_TAG, comm),
    }
    table = {}
    for label, freq in (
        ("10 MHz", FREQUENCY_HZ),
        ("64 MHz", FREQUENCY_64_HZ),
        ("128 MHz", FREQUENCY_128_HZ),
    ):
        phantom = _propagation_constants(SALINE_EPSILON_R, SALINE_SIGMA, freq)
        air = _propagation_constants(1.0, 0.0, freq)
        table[label] = {
            "frequency_hz": float(freq),
            "phantom": phantom,
            "air": air,
            "cells_per_delta_phantom": phantom["delta"] / sizes["phantom"]["h_mean"],
            "cells_per_lambda_phantom": phantom["lambda"] / sizes["phantom"]["h_mean"],
            "cells_per_lambda_air": air["lambda"] / sizes["air"]["h_mean"],
        }
    return {"sizes": sizes, "table": table}


def _require_resolution(resolution):
    """The pre-gate stop rule, enforced mechanically before any gate is read.

    §9 item 7: "If cells/λ lands below 10 the gates are not to be read as a
    pass".  Every 128 MHz gate below calls this first, so a resolution miss makes
    the gates fail with the resolution as their message rather than reporting a
    pass nobody may quote.
    """
    row = resolution["table"]["128 MHz"]
    if row["cells_per_lambda_phantom"] < PHANTOM_CELLS_PER_LAMBDA_FLOOR:
        pytest.fail(
            f"pre-gate stop rule: at 128 MHz the phantom resolves its own "
            f"wavelength ({row['phantom']['lambda']:.6e} m) with only "
            f"{row['cells_per_lambda_phantom']:.4f} cells against the pre-stated "
            f"floor of {PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f} (64 MHz: "
            f"{STEP2_64MHZ['cells_per_lambda_phantom']:.4f}) — the gates on this "
            "rung are not to be read as a pass; this is a resolution finding and "
            "the follow-on is a `GEO` phantom-sizing chunk a review commissions, "
            "never an in-slot re-mesh (§9 item 7)"
        )


@pytest.fixture(scope="module")
def larmor_rungs():
    """Three rungs: 10 MHz control, 128 MHz gated, 128 MHz displaced control."""
    zeros = np.zeros(LEG_COUNT)
    displaced = np.zeros(LEG_COUNT)
    displaced[0] = LEG_OFFSET_RAD

    # Control first, then the knob — the frequency is the only thing that moves
    # between the first two rungs, and the geometry the only thing that moves
    # between the second and the third.
    rungs = {
        "control_10mhz": _four_port_rung("control 10 MHz", zeros, FREQUENCY_HZ),
        "larmor_128mhz": _four_port_rung("larmor 128 MHz", zeros, FREQUENCY_128_HZ),
        "displaced_128mhz": _four_port_rung(
            "displaced 128 MHz", displaced, FREQUENCY_128_HZ
        ),
    }
    resolution = _resolution(rungs["larmor_128mhz"])

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step3] three rungs at -n 2; offset "
            f"{LEG_OFFSET_RAD:.9f} rad = {np.degrees(LEG_OFFSET_RAD):.4f} deg on "
            f"leg 1 of the displaced rung only; sweeps "
            + " + ".join(f"{r['sweep_time']:.2f} s" for r in rungs.values()),
            flush=True,
        )
        for name, rung in rungs.items():
            power = _terminal_power(rung)
            print(
                f"    {name:17s} f = {rung['frequency_hz']:.6e} Hz  "
                f"P1 terminal P = {power:+.9e} VA  |Im P|/Re P = "
                f"{abs(power.imag) / abs(power.real):.6f}  "
                f"(64 MHz record {STEP2_64MHZ['im_over_re_power']:.6f}; stored "
                "energy — printed, never gated)",
                flush=True,
            )
    return {"rungs": rungs, "resolution": resolution}


@complex_only
def test_all_three_rungs_drove_four_solved_field_ports(larmor_rungs):
    """Structural: twelve driven field solves on three conforming rungs.

    None of this is a gate; all of it is what the gates need in order to mean
    anything.  ``is_placeholder=False`` separates a solved field from the retired
    `PORT-0` coupling heuristic; the two undisplaced rungs' cell counts say this
    is still the fixture `PORT-9` gated and step 2 re-gated at 64 MHz, so their
    records are comparable; and every sheet is still a clean rectangular port, so
    a class spread below cannot be blamed on a port that broke.
    """
    rungs = larmor_rungs["rungs"]
    for name, rung in rungs.items():
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

    assert rungs["control_10mhz"]["frequency_hz"] == pytest.approx(FREQUENCY_HZ)
    assert rungs["larmor_128mhz"]["frequency_hz"] == pytest.approx(FREQUENCY_128_HZ)
    assert rungs["displaced_128mhz"]["frequency_hz"] == pytest.approx(FREQUENCY_128_HZ)
    for name in ("control_10mhz", "larmor_128mhz"):
        ratio = rungs[name]["cells"] / STEP2_CELL_COUNT
        assert abs(ratio - 1.0) < STEP2_CELL_COUNT_BAND, (
            f"rung '{name}' meshed {rungs[name]['cells']} cells against "
            f"`GEO-19` step B's record {STEP2_CELL_COUNT}; this is not the fixture "
            "`PORT-9` gated, so nothing measured on it is comparable"
        )


@complex_only
def test_the_phantom_still_resolves_the_wave_at_128_mhz(larmor_rungs):
    """**The pre-gate stop rule.**  ``cells/λ`` in the phantom at 128 MHz >= 10.

    The mesh is frozen by the `GEO-19` record, so doubling the frequency halves
    the wavelength the same cells have to carry: 21.8936 cells/λ at 64 MHz
    predicts ~12.5 here.  The skin depth is *not* what tightens — in the
    displacement-dominated limit δ stops falling with frequency — so both readings
    are printed, ``cells/δ`` against step 1's floor of 2.0 and ``cells/λ`` against
    §9 item 7's floor of 10, and the second is the binding one.

    A miss is a **resolution finding about the mesh**, never a band question: the
    follow-on is a `GEO` phantom-sizing chunk a review commissions.  Nothing here
    may be widened, and no gate below may be read as a pass when this fails —
    :func:`_require_resolution` enforces that mechanically.
    """
    resolution = larmor_rungs["resolution"]
    row = resolution["table"]["128 MHz"]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step3] PRE-GATE RESOLUTION on the solved mesh "
            f"(cells/lambda floor {PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f}, cells/delta "
            f"floor {PHANTOM_CELLS_PER_DELTA_FLOOR:.1f}, both pre-stated, neither "
            f"widenable):",
            flush=True,
        )
        for name, sz in resolution["sizes"].items():
            print(
                f"    region {name:9s}: {sz['cells']:7d} owned cells  h_mean "
                f"{sz['h_mean']:.6e} m  [min {sz['h_min']:.6e}, max "
                f"{sz['h_max']:.6e}]",
                flush=True,
            )
        print(
            "    (this fixture has no separate vessel-wall region — `GEO-18`'s "
            "partition is conductor / air / phantom only, so the wavelength "
            "readings are air and phantom)",
            flush=True,
        )
        for label, r in resolution["table"].items():
            ph = r["phantom"]
            print(
                f"    {label:8s} phantom: loss tangent {ph['loss_tangent']:.4f}  "
                f"delta {ph['delta']:.6e} m  lambda {ph['lambda']:.6e} m  =>  "
                f"cells/delta {r['cells_per_delta_phantom']:.4f}  cells/lambda "
                f"{r['cells_per_lambda_phantom']:.4f}   (air cells/lambda "
                f"{r['cells_per_lambda_air']:.4f})",
                flush=True,
            )
        print(
            f"    64 MHz records for the differential: cells/delta "
            f"{STEP2_64MHZ['cells_per_delta_phantom']:.4f}, cells/lambda "
            f"{STEP2_64MHZ['cells_per_lambda_phantom']:.4f} (step 1 / step 2)\n"
            f"    128 MHz VERDICT: cells/lambda "
            f"{row['cells_per_lambda_phantom']:.4f}  "
            f"{'PASS' if row['cells_per_lambda_phantom'] >= PHANTOM_CELLS_PER_LAMBDA_FLOOR else 'MISS'}"
            f";  cells/delta {row['cells_per_delta_phantom']:.4f}  "
            f"{'PASS' if row['cells_per_delta_phantom'] >= PHANTOM_CELLS_PER_DELTA_FLOOR else 'MISS'}",
            flush=True,
        )

    assert row["cells_per_delta_phantom"] >= PHANTOM_CELLS_PER_DELTA_FLOOR, (
        f"at 128 MHz the phantom resolves its own skin depth "
        f"({row['phantom']['delta']:.6e} m) with only "
        f"{row['cells_per_delta_phantom']:.4f} cells against step 1's pre-stated "
        f"floor of {PHANTOM_CELLS_PER_DELTA_FLOOR:.1f} — a resolution finding "
        "about the mesh, not a band question"
    )
    assert row["cells_per_lambda_phantom"] >= PHANTOM_CELLS_PER_LAMBDA_FLOOR, (
        f"at 128 MHz the phantom carries only "
        f"{row['cells_per_lambda_phantom']:.4f} cells per wavelength "
        f"({row['phantom']['lambda']:.6e} m) against the pre-stated floor of "
        f"{PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f}, down from "
        f"{STEP2_64MHZ['cells_per_lambda_phantom']:.4f} at 64 MHz — the gates on "
        "this mesh are not to be read as a pass (§9 item 7): report the "
        "resolution and stop; a refinement is a `GEO` sizing chunk"
    )


@complex_only
def test_the_ten_megahertz_rung_reproduces_leg_d(larmor_rungs):
    """**The frequency control.**  10 MHz gives back leg (d)'s recorded 4x4.

    The frequency is the only knob this module turns between the first two rungs,
    so the 10 MHz one must land on the ``S`` leg (d1')'s zero rung printed when it
    closed `PORT-9` (``LEG_D_S_MATRIX_10MHZ``, imported from the 64 MHz module
    where step 2 version-tagged it, entry by entry to 1e-6) and on leg (d0)'s
    recorded terminated column (``LEG_D0_Z_COLUMN``, imported, at its own
    print-precision band).  Step 2 measured 1.158e-10 and 2.568e-10 on the same
    two comparisons.  A miss means the harness moved, not the physics, and the
    128 MHz gates below would be measuring that move.

    The reciprocity *residual* is printed for the record and deliberately not
    compared digit for digit: per the (d3c) rule power-wave readings sit at
    ~1e-16…1e-11 and reproduce in order of magnitude only.
    """
    rung = larmor_rungs["rungs"]["control_10mhz"]
    s_dev = np.abs(rung["s"] - LEG_D_S_MATRIX_10MHZ) / np.abs(LEG_D_S_MATRIX_10MHZ)
    column = rung["z"][:, 0]
    z_dev = np.abs(column - LEG_D0_Z_COLUMN) / np.abs(LEG_D0_Z_COLUMN)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step3] FREQUENCY CONTROL: the 10 MHz rung vs leg (d)'s "
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
            f"{'PASS' if float(np.max(s_dev)) < FREQUENCY_CONTROL_BAND else 'MISS'}"
            f"   (step 2 measured 1.158e-10 on this comparison)",
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
        "reads at 128 MHz is comparable to what `PORT-9` gated"
    )
    worst_z = float(np.max(z_dev))
    assert worst_z < LEG_D0_REPRODUCTION_BAND, (
        f"the 10 MHz rung's terminated column deviates {worst_z:.3e} from leg "
        f"(d0)'s record against its {LEG_D0_REPRODUCTION_BAND:.0e} "
        "print-precision band — this is not the solve `PORT-9` recorded"
    )


@complex_only
def test_the_birdcage_is_reciprocal_at_128_mhz(larmor_rungs):
    """**Gate (i) at 128 MHz.**  ``‖S − Sᵀ‖/‖S‖ <= 1e-3``.

    Four independent solves, each driving a different leg, assembled column by
    column from power waves.  The network is passive and made of reciprocal
    materials at every frequency, so ``S`` must be symmetric; what is new at
    128 MHz is that the saline load is now displacement-dominated (loss tangent
    0.90 against 1.80 at 64 MHz), not the reciprocity.  The band is step 2c's,
    imported and unmoved.  A miss at 128 MHz with the 10 MHz rung green on the
    same mesh — and 64 MHz green on record at 2.581e-14 — is precisely the finding
    step 3 exists to surface: record it and stop; never widen.
    """
    _require_resolution(larmor_rungs["resolution"])
    rungs = larmor_rungs["rungs"]
    rung = rungs["larmor_128mhz"]
    ratio = rung["reciprocity"]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step3] GATE (i) reciprocity at 128 MHz (band "
            f"{RECIPROCITY_BAND:.0e}, step 2c's, unmoved):\n"
            f"    ||S - S^T||/||S|| = {ratio:.9e}  "
            f"{'PASS' if ratio <= RECIPROCITY_BAND else 'MISS'}   "
            f"(10 MHz control on the same mesh: "
            f"{rungs['control_10mhz']['reciprocity']:.9e}; 64 MHz record "
            f"{STEP2_64MHZ['reciprocity']:.9e})\n"
            f"    ||Z - Z^T||/||Z|| = {rung['z_reciprocity']:.9e} (reported)",
            flush=True,
        )

    assert ratio <= RECIPROCITY_BAND, (
        f"at 128 MHz the birdcage 4x4 reads ||S - S^T||/||S|| = {ratio:.9e} "
        f"against the pre-stated {RECIPROCITY_BAND:.0e} band, with the 10 MHz "
        f"control on the same mesh at "
        f"{rungs['control_10mhz']['reciprocity']:.9e} and 64 MHz on record at "
        f"{STEP2_64MHZ['reciprocity']:.9e} — a finding about the lumped-sheet "
        "route in the displacement-dominated regime (§9 item 7, negative result: "
        "record per gate against its 64 MHz value, open a known-issues entry, "
        "stop; never widen)"
    )


@complex_only
def test_the_birdcage_is_passive_at_128_mhz(larmor_rungs):
    """**Gate (ii) at 128 MHz.**  ``σ_max(S) <= 1 + 1e-9``, column power sums ``<= 1``.

    A network of lossy conductors, saline and air cannot return more power to its
    ports than is fed in, and that is a statement about energy rather than about
    frequency.  At 64 MHz ``σ_max`` had already climbed to 0.999721388 from
    0.999992805-at-10-MHz's own margin structure, and the stored energy in the
    load keeps rising with frequency, which is exactly the regime in which a route
    that mishandled reactive power would show up here.  Both readings are printed
    to nine digits as the 128 MHz reproduction record.
    """
    _require_resolution(larmor_rungs["resolution"])
    rungs = larmor_rungs["rungs"]
    rung = rungs["larmor_128mhz"]
    sigma_max = float(np.max(rung["sigma"]))
    column_power = rung["column_power"]
    power_max = float(np.max(column_power))
    report = rung["result"].sanity_report

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step3] GATE (ii) passivity at 128 MHz (tolerance "
            f"{PASSIVITY_SIGMA_TOLERANCE:.0e}, pre-stated 2026-08-16, unmoved):\n"
            f"    sigma_max(S) = {sigma_max:.9f}  "
            f"{'PASS' if sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE else 'MISS'}"
            f"   (PORT-5 metric: {report.passivity_max_sigma:.9f}; 10 MHz control "
            f"{float(np.max(rungs['control_10mhz']['sigma'])):.9f}; 64 MHz record "
            f"{STEP2_64MHZ['sigma_max']:.9f})\n"
            f"    max column power sum = {power_max:.9f}  "
            f"{'PASS' if power_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE else 'MISS'}"
            f"   (PORT-5 metric: {report.passivity_max_column_power_sum:.9f}; "
            f"64 MHz record {STEP2_64MHZ['column_power_max']:.9f})",
            flush=True,
        )

    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"at 128 MHz sigma_max(S) = {sigma_max:.9f} exceeds 1 by more than "
        f"{PASSIVITY_SIGMA_TOLERANCE:.0e} (64 MHz record "
        f"{STEP2_64MHZ['sigma_max']:.9f}) — the assembled 4x4 is active, a "
        "passivity finding about the lumped-sheet route in the "
        "displacement-dominated regime (§9 item 7: record and stop)"
    )
    for k, value in enumerate(column_power, start=1):
        assert value <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
            f"at 128 MHz column {k} of S carries power sum {value:.9f} > 1 + "
            f"{PASSIVITY_SIGMA_TOLERANCE:.0e} — driving port {k} returns more "
            "power than it is fed"
        )


@complex_only
def test_the_impedance_matrix_is_c4_circulant_at_128_mhz(larmor_rungs):
    """**Gate (iii') at 128 MHz.**  Each circulant class of ``Z`` spreads ``<= 0.5%``.

    The four legs sit at 0/90/180/270 deg on a layout that is C4-invariant by
    construction, so ``Z`` must be circulant at any frequency: one self term, one
    adjacent term, one opposite term.  Taken on ``Z`` rather than ``S`` so the
    termination convention does not enter, with the band imported from leg (c) and
    (iii')-tightened, unmoved.

    Leg (d)'s own anti-noise control travels with it: the *pooled* off-diagonal
    class must spread at least 10x the worst intra-class spread, or the gate is
    passing on noise rather than resolving the adjacent/opposite structure leg
    (d0) separated.  The 10 MHz spreads on this mesh and step 2's 64 MHz ones
    (0.0573 / 0.0599 / 0.0370% at a 671.0527x separation) are both printed beside
    the 128 MHz readings, so the review can see what the frequency did to the
    margin.
    """
    _require_resolution(larmor_rungs["resolution"])
    rungs = larmor_rungs["rungs"]
    rung = rungs["larmor_128mhz"]
    control = rungs["control_10mhz"]
    spreads = rung["spreads"]
    pooled = rung["pooled"]
    worst = max(spreads.values())
    separation = pooled / worst if worst > 0.0 else np.inf

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step3] GATE (iii') C4 circulant symmetry of Z at 128 MHz "
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
                f"   (10 MHz control {control['spreads'][name] * 100:.4f}%; "
                f"64 MHz record {STEP2_64MHZ['spreads'][name] * 100:.4f}%)",
                flush=True,
            )
        print(
            f"    control: pooled off-diagonal spread {pooled * 100:.4f}% vs "
            f"worst intra-class {worst * 100:.4f}%  =>  separation "
            f"{separation:.4f}x (floor {POOLED_SEPARATION_FLOOR:.0f}x)  "
            f"{'PASS' if separation >= POOLED_SEPARATION_FLOOR else 'MISS'}"
            f"   (10 MHz control "
            f"{control['pooled'] / max(control['spreads'].values()):.4f}x; 64 MHz "
            "record 671.0527x)",
            flush=True,
        )

    for name, value in spreads.items():
        assert value <= ADJACENT_SPREAD_BAND, (
            f"at 128 MHz the {name} class of Z spreads {value * 100:.4f}% against "
            f"the pre-stated {ADJACENT_SPREAD_BAND * 100:.1f}% band (10 MHz "
            f"control on the same mesh: {control['spreads'][name] * 100:.4f}%; "
            f"64 MHz record {STEP2_64MHZ['spreads'][name] * 100:.4f}%) — on an "
            "undisplaced, C4-invariant layout that is a finding about the route "
            "or the mesh in the displacement-dominated regime (§9 item 7, "
            "negative result: record all three spreads and both controls, stop; "
            "never widen)"
        )
    assert separation >= POOLED_SEPARATION_FLOOR, (
        f"at 128 MHz the pooled off-diagonal class spreads {pooled * 100:.4f}%, "
        f"only {separation:.4f}x the worst intra-class spread "
        f"{worst * 100:.4f}%, against the pre-stated "
        f"{POOLED_SEPARATION_FLOOR:.0f}x floor — gate (iii') is not resolving the "
        "adjacent/opposite structure at this frequency, so its passing says "
        "nothing about C4 symmetry"
    )


@complex_only
def test_gate_iii_still_detects_the_broken_c4_at_128_mhz(larmor_rungs):
    """**The geometric negative control at 128 MHz.**  Displaced, (iii') breaks.

    A symmetry gate that has only ever been shown a symmetric layout *at this
    frequency* is a consistency check, not a validated gate — leg (d1') made that
    argument at 10 MHz, step 2 re-made it at 64 MHz, and it does not transfer by
    fiat to a third frequency.  So leg 1 is rotated 22.5 deg off the C4 layout at
    128 MHz and the ``{Z_ii}`` and ``{Z_i,i±1}`` classes must **exceed** the band,
    while gate (i) still holds on the same rung: reciprocity is a property of the
    materials and not of the layout, so holding it here separates "the gate
    measured geometry" from "the displaced solve fell apart".

    Per the rubric's rule 2 the assertion is **breakage, not a factor**: the
    64 MHz displaced signature was 12.8947 / 27.7509% against 0.5% with (i) at
    1.252e-15, and pinning an amplification at a new frequency would be a
    prediction this step has no basis for.  The ``{Z_i,i+2}`` opposite class stays
    **reported, not gated**, by the 2026-08-25 03:00 review's pre-ruling — it is
    physically the flattest of the three.

    A displaced self *or* adjacent spread inside the band is the pre-stated
    negative result: gate (iii') is blind at 128 MHz at this grain, the numbers
    are recorded, step 3 does not close and the review re-specifies (iii') — it is
    never a licence to widen anything.
    """
    _require_resolution(larmor_rungs["resolution"])
    rungs = larmor_rungs["rungs"]
    gated = rungs["larmor_128mhz"]["spreads"]
    rung = rungs["displaced_128mhz"]
    disp = rung["spreads"]
    sigma_max = float(np.max(rung["sigma"]))

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step3] NEGATIVE CONTROL at 128 MHz (band "
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
            record = STEP2_64MHZ["displaced_spreads"].get(cls)
            record_text = (
                f"   (64 MHz displaced record {record * 100:.4f}%)"
                if record is not None
                else ""
            )
            print(
                f"    {cls:9s} [{role:8s}]  undisplaced {gated[cls] * 100:9.4f}%   "
                f"displaced {disp[cls] * 100:9.4f}%   amplification "
                f"{disp[cls] / gated[cls]:12.2f}x   {verdict}{record_text}",
                flush=True,
            )
        print(
            f"    displaced rung gate (i): ||S - S^T||/||S|| = "
            f"{rung['reciprocity']:.9e} (band {RECIPROCITY_BAND:.0e}, 64 MHz "
            f"record {STEP2_64MHZ['displaced_reciprocity']:.9e})  "
            f"{'PASS' if rung['reciprocity'] <= RECIPROCITY_BAND else 'MISS'}"
            f";  sigma_max(S) = {sigma_max:.9f}",
            flush=True,
        )

    assert rung["reciprocity"] <= RECIPROCITY_BAND, (
        f"the displaced 128 MHz rung reads ||S - S^T||/||S|| = "
        f"{rung['reciprocity']:.9e} against the pre-stated "
        f"{RECIPROCITY_BAND:.0e} band — the class spreads below would be "
        "measuring a broken solve rather than a broken symmetry (never widen)"
    )
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"the displaced 128 MHz rung reads sigma_max(S) = {sigma_max:.9f} — the "
        "assembled 4x4 is active, so its class spreads say nothing about C4"
    )
    for cls in ("self", "adjacent"):
        assert disp[cls] > ADJACENT_SPREAD_BAND, (
            f"at 128 MHz with leg 1 rotated {np.degrees(LEG_OFFSET_RAD):.1f} deg "
            f"off the C4 layout the {cls} class of Z still spreads only "
            f"{disp[cls] * 100:.4f}%, inside the "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}% band it passes on the symmetric "
            f"layout ({gated[cls] * 100:.4f}%; the 64 MHz displaced record is "
            f"{STEP2_64MHZ['displaced_spreads'][cls] * 100:.4f}%) — gate (iii') "
            "does not detect a broken C4 at this frequency and grain, so its "
            "passing above is a consistency check and not a symmetry gate (§9 "
            "item 7, negative result: record and stop; never widen (i)-(iii'))"
        )
