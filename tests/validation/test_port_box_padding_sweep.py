"""`PORT-1` step 3b-xi: is the mutual-coupling deficit the PEC box?

Every `PORT-1` step since step 1 has attributed the residual gap between the
FEM ``Im Z₁₂`` and the closed-form ``ωM₁₂`` to the PEC truncation box, and the
attribution rests on **one measurement made at two points**: step 1 recorded
that enlarging the air padding 0.08 → 0.12 m moved the deficit 5.20% toward
the closed form while refining ``h_far`` 0.02 → 0.03 m moved it 0.09% — 58×
smaller, on the same fixture.  That is enough to say the deficit is not the
mesh; it is not enough to say it *is* the box, because two points cannot
distinguish a trend from a coincidence, and the number the whole gap-port
lineage now wants to explain (3b-x's corrected terminal-to-terminal port
voltage, ~−10.6% of ``ωM₁₂``) is being charged to the same account.

This module measures the trend instead of the point.  It solves the **ungapped**
two-torus pair at ``d = 0.04``, ``h_far = 0.03``, projected drive — step 2f's
production path, which is why the reference deficit here is **−8.03%** and not
step 1's unprojected −9.35% — at three air paddings, and asserts:

  * **monotone shrinkage.**  ``|Im Z₁₂/ωM₁₂ − 1|`` is strictly decreasing over
    padding 0.08 → 0.10 → 0.12.  A PEC wall at finite distance *shorts out* the
    field it truncates, so it can only ever remove flux from the pickup loop;
    a box-owned deficit therefore has one sign and one direction under
    enlargement.  A deficit that wanders, or shrinks non-monotonically, is not
    a box effect and the attribution dies here.
  * **the size of the move.**  The 0.08 → 0.12 shrinkage must land in the band
    **3–7%**, i.e. bracketing step 1's 5.20% with roughly ±35%.  The band is
    not tight because step 1's number was measured on the *unprojected* drive
    and this sweep runs the projected one; what is being tested is that the
    same box move produces the same order of correction, not that it
    reproduces a digit.

**Negative control**, on record rather than re-run: the ``h_far`` 0.02 → 0.03
refinement on this identical fixture moved the deficit 0.09%
(`PORT-1` step 1, `20260802T183045Z…184031Z_PORT-1-step1-*.log`).  If the
padding sweep below lands in the 3–7% band it is 33–78× that, so the two
knobs are cleanly separated and the mesh is not masquerading as the box.

**What this does not do.**  It does not close known-issues 3, does not flip any
symbol, and does not touch ``MUTUAL_TOLERANCE`` — the 10% mutual bound in
`test_port_reaction_impedance.py` is measurement-justified by the filamentary
reference's own 66.5% spread and stays exactly where it is regardless of what
this sweep finds.  Nor does it extrapolate to a converged answer: three
paddings inside a factor 1.5 cannot support a Richardson fit, and none is
attempted.  The claim is directional.

Cost: heavy tier.  Three meshes (16.4 / 18.0 / 20.1 s, 119 738 / 135 542 /
154 493 cells — `20260807T123435Z_PORT-1-step3bxi-probe.log`, all well under
the 250 000-cell line where padding 0.12 / ``h_far`` 0.02 once died in MUMPS)
and **one** solve each: only ``Z₂₁`` is read, and reciprocity is 3.06e-13 on
this fixture, so the second column buys nothing — the same trade step 2c's
doubling pair made.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_box_padding_sweep.py -v -s'
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only
from tests.validation.test_port_reaction_impedance import (
    MAJOR_RADIUS,
    OMEGA,
    SEPARATION,
    TORUS_TAGS,
    _solve_reaction_z,
    mutual_inductance,
)

# The three boxes.  0.08 is step 2's production padding and the one every
# landed `PORT-1` number was measured in; 0.12 is step 2c's, whose cost is on
# record; 0.10 is the interior point that turns two measurements into a trend.
PADDINGS = (0.08, 0.10, 0.12)

# Step 2f's projected-drive deficit at padding 0.08, PROJECT_PLAN §7: the
# sweep's first point must reproduce it, or the fixture is not the one the
# attribution was made on.  Printed to four figures there, so the pin is loose
# enough to survive partition-order arithmetic at -n 2.
STEP2F_DEFICIT_AT_008 = -0.0803
STEP2F_DEFICIT_TOLERANCE = 0.003

# Step 1's measured 0.08 -> 0.12 move, and the band this sweep must land in.
STEP1_PADDING_MOVE = 0.0520
SHRINKAGE_BAND = (0.03, 0.07)

# The negative control, cited not re-run: h_far 0.02 -> 0.03 on this fixture.
STEP1_HFAR_MOVE = 0.0009


@pytest.fixture(scope="module")
def padding_sweep():
    """``Im Z₁₂/ωM₁₂ − 1`` at each padding — three meshes, three solves.

    Module-scoped so both assertions share the solves; every rank runs the
    fixture, so the collective calls inside ``_solve_reaction_z`` stay matched.
    ``driven_tags`` is torus 1 alone: the returned matrix has column 0 filled
    and ``Z₂₁`` is the entry read.
    """
    omega_m12 = OMEGA * mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    deficits = {}
    for padding in PADDINGS:
        z_matrix = _solve_reaction_z(
            SEPARATION,
            (TORUS_TAGS[0],),
            f"PORT-1 step 3b-xi pad {padding}",
            air_padding=padding,
        )
        z21 = z_matrix[1, 0]
        deficits[padding] = z21.imag / omega_m12 - 1.0
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"[PORT-1 step 3b-xi] padding {padding} m: Im Z21 = "
                f"{z21.imag:+.6e} Ohm, omega*M12 = {omega_m12:+.6e} Ohm, "
                f"ratio {z21.imag / omega_m12:.6f} ({deficits[padding]:+.4%})",
                flush=True,
            )
    if MPI.COMM_WORLD.rank == 0:
        print(
            "[PORT-1 step 3b-xi] deficits "
            + ", ".join(f"{p} m: {deficits[p]:+.4%}" for p in PADDINGS),
            flush=True,
        )
    return deficits


@complex_only
def test_padding_sweep_reproduces_the_landed_deficit(padding_sweep):
    """Padding 0.08 must return step 2f's −8.03%.

    A fixture check, not a physics one: the sweep's whole argument is that the
    other two paddings differ from the landed configuration *only* in the box,
    so the landed configuration has to come back unchanged.
    """
    measured = padding_sweep[PADDINGS[0]]
    delta = abs(measured - STEP2F_DEFICIT_AT_008)
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3b-xi] padding 0.08 deficit {measured:+.4%} vs step 2f's "
            f"{STEP2F_DEFICIT_AT_008:+.4%} (delta {delta:.2e})",
            flush=True,
        )
    assert delta < STEP2F_DEFICIT_TOLERANCE, (
        f"padding {PADDINGS[0]} m gives {measured:+.4%}, not step 2f's landed "
        f"{STEP2F_DEFICIT_AT_008:+.4%}: this is not the fixture the box "
        f"attribution was made on"
    )


@complex_only
def test_deficit_shrinks_monotonically_with_padding(padding_sweep):
    """The sign-definite statement: a bigger box can only help, and always does.

    Strict monotonicity in ``|deficit|``.  This is the assertion that a
    non-box cause fails — a mesh-resolution artefact or a reference error has
    no reason to track the wall distance at all, and a *sign*-indefinite
    numerical wobble has no reason to track it in one direction three times
    running.
    """
    magnitudes = [abs(padding_sweep[p]) for p in PADDINGS]
    if MPI.COMM_WORLD.rank == 0:
        print(
            "[PORT-1 step 3b-xi] |deficit| "
            + " > ".join(f"{m:.4%}" for m in magnitudes),
            flush=True,
        )
    assert all(a > b for a, b in zip(magnitudes, magnitudes[1:])), (
        "|Im Z12/omega*M12 - 1| is not strictly decreasing in air padding: "
        + ", ".join(f"{p} m: {abs(padding_sweep[p]):.4%}" for p in PADDINGS)
        + " — the PEC-box attribution of the residual deficit does not hold"
    )
    assert all(d < 0.0 for d in padding_sweep.values()), (
        "a PEC wall removes flux from the pickup loop, so every deficit must be "
        "negative: " + ", ".join(f"{p} m: {padding_sweep[p]:+.4%}" for p in PADDINGS)
    )


@complex_only
def test_padding_move_is_the_size_step_1_measured(padding_sweep):
    """The 0.08 → 0.12 move lands in the 3–7% band around step 1's 5.20%.

    And is at least an order of magnitude above the ``h_far`` control: the
    ratio to step 1's 0.09% mesh move is printed so the separation between the
    two knobs is a measured number in the log, not a claim in a docstring.
    """
    move = abs(padding_sweep[PADDINGS[0]]) - abs(padding_sweep[PADDINGS[-1]])
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"[PORT-1 step 3b-xi] padding 0.08 -> 0.12 move {move:+.4%} vs step 1's "
            f"{STEP1_PADDING_MOVE:+.4%}, band {SHRINKAGE_BAND[0]:.2%}-"
            f"{SHRINKAGE_BAND[1]:.2%}; {move / STEP1_HFAR_MOVE:.1f}x the h_far "
            f"control ({STEP1_HFAR_MOVE:.2%})",
            flush=True,
        )
    low, high = SHRINKAGE_BAND
    assert low < move < high, (
        f"the padding 0.08 -> 0.12 move is {move:+.4%}, outside the {low:.0%}-"
        f"{high:.0%} band step 1's {STEP1_PADDING_MOVE:.2%} sized"
    )
    assert move > 10.0 * STEP1_HFAR_MOVE, (
        f"the padding move {move:+.4%} is not an order above the h_far control "
        f"{STEP1_HFAR_MOVE:.2%}; the two knobs are not separated"
    )
    assert np.isfinite(move)
