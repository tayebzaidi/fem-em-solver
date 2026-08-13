"""`PORT-1` step 3b-xii — the box discriminator at ``air_padding = 0.10``.

Step 3b-x-b left one number red by 0.02 pp and two dispositions open.  The
corrected terminal-to-terminal port voltage on the gapped fixture reads
0.894543 × ωM₁₂; the σ = 0 closed-footprint reaction control on the *same*
mesh reads 0.922423 × ωM₁₂; the deviation between the two independent routes
is −3.0224e-02 against ``REACTION_CONSISTENCY_TOLERANCE = 0.03``.  The bound
was sized for a ~1.2 pp gapped/ungapped spread and the control measured that
spread at **2.8 pp**, so what the measurement contradicts is the bound's
premise, not necessarily the estimator.

The two open readings were:

(a) the residual is the **PEC truncation box**, which both routes see but see
    slightly differently, in which case enlarging the box must pull them
    together; or
(b) the residual is a **real estimator bias** the wedge correction did not
    remove, in which case enlarging the box moves the two together and leaves
    the deviation where it is.

Step 3b-xi made (a) quantitatively plausible without testing it: on the
*ungapped* pair the box is worth 4.8 pp of ``Im Z₂₁/ωM₁₂`` deficit over
padding 0.08 → 0.12 (−8.0324% / −5.0256% / −3.2733%, strictly monotone, 52.9×
the h_far mesh control).  That is a statement about a *shared* residual,
though — it does not say whether the two routes' *difference* closes.

This module buys the discriminating measurement.  It rebuilds the gapped
fixture at ``air_padding = 0.10`` — nothing else moves; same wedge, same
burial, same overhang, same ``h_far``/``h_wire``, same σ, same drive, same
``project_source`` choices — and computes both routes on it, through the very
same ``_solve_gap_ports`` the 0.08 gates use.  Sharing the machinery is the
point: a difference between the two paddings can then only be the box.

**The gate is pre-decided** (§9 item 1 / §7 step 3b-xii, 2026-08-07 10:30
review), so nothing here is adjudicated in-slot:

* deviation(0.10) ≤ 2.5% — a ≥ 0.5 pp move, 5× the 0.09% h_far mesh floor —
  ⇒ reading (a): the box owns the spread.
* deviation(0.10) > 2.5%, including the ambiguous band up to 3.02% ⇒ reading
  (b): park and report; never tune toward (a).

**Nothing is pinned here.**  Every digit-string in
``test_port_gap_voltage_impedance.py`` is padding-0.08-specific — cell count,
disc areas, closure numbers, the two route values.  This module prints its
0.10 numbers and asserts only the deviation, which is the one quantity the
plan predicts should move.

Cost: standard tier, ``-n 2``, one mesh (194 985 cells, measured mesh-only
first — ``20260807T170143Z_PORT-1-step3bxii-probe.log``, 1.0951× the 178 055
at padding 0.08, under the plan's 230 000 stop rule) and the same five solves
3b-x-b's 298.6 s bought at 0.08.
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only
from tests.validation.test_port_gap_voltage_impedance import (
    GAP_TAGS,
    REACTION_CONSISTENCY_TOLERANCE,
    _solve_gap_ports,
)

# The enlarged box.  The landed fixture is 0.08; 3b-xi's ungapped sweep read
# the deficit at 0.08 / 0.10 / 0.12 and 0.10 is the one this step rebuilds
# gapped, because it is the smallest step that clears the mesh floor (3.0 pp of
# ungapped deficit) at a cell count the standard tier can afford.
DISCRIMINATOR_AIR_PADDING = 0.10

# Pre-decided by the 2026-08-07 10:30 review, before the measurement existed.
# 2.5% is a >= 0.5 pp move off the 3.0224% on record at padding 0.08, i.e. 5x
# the 0.09% h_far mesh floor step 3b-xi measured on this geometry, so a pass
# cannot be mesh noise wearing the box's clothes.
CONVERGENCE_THRESHOLD = 0.025

# Step 3b-x-b's record at padding 0.08, for the delta this module reports.
# Printed for comparison only -- never asserted here; the 0.08 gates in
# test_port_gap_voltage_impedance.py own those digits.
DEVIATION_AT_008 = -3.0224e-02
ESTIMATOR_AT_008 = 0.894543
CONTROL_AT_008 = 0.922423

# The negative control, on record from 3b-x-b's own log: the *uncorrected*
# wedge-only estimator (0.493653 x omega*M12, i.e. the integral over the
# nominal 0.30 rad wedge that misses the buried gap arc) against the same
# control reference.  It must stay far outside the threshold at this padding
# too, or the gate is passing everything.
WEDGE_ONLY_ESTIMATOR = 0.493653
WEDGE_ONLY_FLOOR = 0.20


@pytest.fixture(scope="module")
def gap_ports_padded():
    """One gapped mesh at padding 0.10, five solves.  Module-scoped: the two
    routes must share a mesh or their difference is mesh noise, which is the
    whole quantity this step measures."""
    return _solve_gap_ports(
        MPI.COMM_WORLD,
        "PORT-1 step 3b-xii",
        air_padding=DISCRIMINATOR_AIR_PADDING,
    )


def _routes(record_set):
    """(estimator, control) as multiples of ωM₁₂, per driven column."""
    omega_m = record_set["omega_m"]
    z_ref = record_set["control"]["z21"].imag
    out = []
    for tag, record in sorted(record_set["currents"].items()):
        col = GAP_TAGS.index(tag)
        z_gap = record["voltages"][1 - col] / record["driven"]
        out.append(
            {
                "tag": tag,
                "estimator": abs(z_gap.imag) / omega_m,
                "control": abs(z_ref) / omega_m,
                "ratio": abs(z_gap.imag) / abs(z_ref),
                "z_gap_imag": z_gap.imag,
                "z_ref_imag": z_ref,
            }
        )
    return out


@complex_only
def test_the_enlarged_box_is_the_fixture_it_claims_to_be(gap_ports_padded):
    """The box moved and nothing else did.

    Cheap structural gate before the discriminator reads anything physical: the
    padding the solve used is the one this module asked for, the mesh is the
    size the mesh-only probe measured, and the control is a *lossless* mutual —
    ``Re Z₂₁ = 0`` exactly, as an impressed current in a σ = 0 domain must give.
    A non-zero real part would mean the control picked up conduction from
    somewhere, and its reference value could not be trusted as the second route.
    """
    assert gap_ports_padded["air_padding"] == DISCRIMINATOR_AIR_PADDING
    control = gap_ports_padded["control"]
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-1 step 3b-xii] padding "
            f"{gap_ports_padded['air_padding']} m, "
            f"{gap_ports_padded['cells']} cells (probe measured 194985 at this "
            f"padding, 178055 at 0.08); control Re Z21 = "
            f"{control['z21'].real:+.6e} Ohm, I'/I_prescribed = "
            f"{control['current_prime'] / control['current_prescribed']:.6f}, "
            f"projection imag_ratio = {control['imag_ratio']:.3e}",
            flush=True,
        )
    # Re Z21 is identically zero here by construction, not to a tolerance: the
    # only loss mechanism in the control problem is absent.  3b-x-b measured it
    # exactly zero at padding 0.08.
    assert control["z21"].real == 0.0, (
        f"the sigma = 0 control returned Re Z21 = {control['z21'].real:+.6e} "
        "Ohm; an impressed-current mutual in a lossless domain must be purely "
        "imaginary, so the control is not the problem it is supposed to be"
    )


@complex_only
def test_box_enlargement_discriminates_between_the_two_routes(gap_ports_padded):
    """**The step.**  Estimator vs control at padding 0.10, against the 2.5%
    threshold the review pre-decided.

    Both routes are recomputed from scratch on the enlarged box: the corrected
    terminal-to-terminal line integral of ``E·φ̂`` between the port terminals
    (the production, gapped, σ = 800 S/m problem) and the volume reaction
    integral over conductor 2 driven by an impressed azimuthal current on
    loop 1's closed wire ∪ gap footprint at σ = 0.  They share the mesh and the
    PEC box and nothing else.

    Passing means the deviation between them shrank by at least 0.5 pp when the
    box grew — the signature of a shared truncation residual that the two
    routes weight differently, i.e. disposition (a).  Failing means the
    deviation is insensitive to the box, which is disposition (b): a real
    estimator bias, and a finding in its own right.
    """
    omega_m = gap_ports_padded["omega_m"]
    routes = _routes(gap_ports_padded)
    deviations = []
    for r in routes:
        deviation = r["ratio"] - 1.0
        deviations.append(deviation)
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 3b-xii] gap {r['tag']} driven at padding "
                f"{DISCRIMINATOR_AIR_PADDING}: estimator Im Z_gap = "
                f"{r['z_gap_imag']:+.9e} Ohm ({r['estimator']:.6f} x omega*M) "
                f"vs same-mesh sigma=0 control Im Z21 = "
                f"{r['z_ref_imag']:+.9e} Ohm ({r['control']:.6f} x omega*M): "
                f"ratio {r['ratio']:.6f}, deviation {deviation:+.4e} "
                f"(threshold {CONVERGENCE_THRESHOLD:.1%}); at padding 0.08 the "
                f"same three read {ESTIMATOR_AT_008:.6f}, {CONTROL_AT_008:.6f}, "
                f"{DEVIATION_AT_008:+.4e}",
                flush=True,
            )
    worst = max(abs(d) for d in deviations)
    # The negative control, on the *enlarged* box's own reference: the
    # uncorrected wedge-only estimator must still miss by far more than the
    # threshold, or this gate would pass an estimator that never found the
    # buried gap arc at all.
    wedge_ratio = WEDGE_ONLY_ESTIMATOR / routes[0]["control"]
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3b-xii] worst |deviation| over both driven columns "
            f"{worst:.6e} vs threshold {CONVERGENCE_THRESHOLD:.3e}; move off "
            f"the padding-0.08 record {abs(DEVIATION_AT_008) - worst:+.4e} "
            f"({(abs(DEVIATION_AT_008) - worst) * 100:+.3f} pp). Negative "
            f"control: the uncorrected wedge-only estimator "
            f"{WEDGE_ONLY_ESTIMATOR:.6f} x omega*M against this box's own "
            f"control gives ratio {wedge_ratio:.4f}, deviation "
            f"{wedge_ratio - 1.0:+.4f}",
            flush=True,
        )
    assert abs(wedge_ratio - 1.0) > WEDGE_ONLY_FLOOR, (
        f"the uncorrected wedge-only estimator gives ratio {wedge_ratio:.4f} "
        f"against this box's control — within {WEDGE_ONLY_FLOOR:.0%}, so the "
        "discriminator below cannot distinguish the corrected estimator from "
        "the one that misses the buried gap arc"
    )
    assert np.isfinite(worst)
    assert worst <= CONVERGENCE_THRESHOLD, (
        f"the estimator/control deviation at air_padding = "
        f"{DISCRIMINATOR_AIR_PADDING} is {worst:.6e}, above the pre-decided "
        f"{CONVERGENCE_THRESHOLD:.1%}: enlarging the PEC box from 0.08 did not "
        f"pull the two routes together (padding 0.08 read "
        f"{abs(DEVIATION_AT_008):.6e}). That is disposition (ii) — a real "
        "estimator bias the step-3b-x wedge correction did not remove, not a "
        "truncation artefact. Report both deviations and all four route "
        "values; do not move REACTION_CONSISTENCY_TOLERANCE "
        f"(unmoved at {REACTION_CONSISTENCY_TOLERANCE:.0%})."
    )
