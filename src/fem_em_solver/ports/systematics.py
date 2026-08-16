"""The measured systematics that stand between a gap-voltage ``Im Z₁₂`` and the
filamentary closed form, and the ladder that applies them.

Lifted verbatim out of ``tests/validation/test_port_gap_voltage_impedance.py``
by `EX-18` so the example and the gate share one definition rather than two
copies of three constants.  The test now imports from here and asserts the
ladder it imports is bit-identical to the numbers its own gate was measured on
(``test_gap_voltage_port_pair_mutual_carries_its_systematics``).

Neither correction is a fitted knob adjusted to make a gate green: both were
fixed by `PORT-1` steps 3b-xi/3b-xvii, before step 3b-xviii's gate existed.

  * **PEC box.**  The truncation box at ``air_padding = 0.08`` costs the mutual
    ``D_inf = +1.69 pp`` of ratio, from step 3b-xi/decision-(4)'s free-exponent
    fit ``ratio = r_inf - C*W^(-p)`` to three padding rungs, at **p = 1.657** —
    an *effective-range* extrapolation, never to be quoted without its exponent
    (pinning the dipolar ``p = 3`` moves the term to ``-1.43 pp``; the model
    uncertainty is ~840x the data uncertainty, PROJECT_PLAN §7 3b-xi note).
  * **Gap physics.**  The gapped fixture reads ``-3.0224e-02`` against its own
    ``sigma = 0`` *closed* control (``-2.9674e-02`` under 1.57x feed
    refinement) — the gap-generator feed model's documented,
    gap-geometry-dependent impedance error (Jin, *The FEM in Electromagnetics*
    3rd ed., §10.4.2.1).  Step 3b-xvi excluded feed discretisation as its owner
    by measurement (``+0.0508 pp`` under refinement against a 0.5 pp band), and
    3b-xvii's matched-topology gate is what licenses calling it a topology term
    rather than an estimator defect.

**The composition is measured, not assumed** (`PORT-10`, 2026-08-16).  Each
term above was measured with the other at its baseline, and
:func:`mutual_systematics_ladder` then applies them in sequence — separability
no measurement had tested.  The 2×2 factorial
(``tests/validation/test_port_systematics_composition.py``: ``air_padding``
0.08/0.10 × gap-box ``h_box`` baseline/6.0e-4, four solves) reads the
cross-term at **−0.0604 pp** against a pre-stated ±0.5 pp band — the two knobs'
effects add, so the sequential ladder carries no interaction error resolvable
at 3b-xvi's grain.  The factorial tests the separability of the two
*measurements*; it is silent on the extrapolations layered on them (``D∞`` is a
``W → ∞`` limit, and the padding rung there is one finite step of it).

Both are specific to the two-torus gapped fixture at ``air_padding = 0.08``,
``gap_angle = 0.30``, ``gap_burial = 1e-3``, ``f = 10 MHz``.  They are *not*
general-purpose corrections and must not be applied to another geometry
without re-measuring them there.
"""

from __future__ import annotations

__all__ = [
    "GAP_PHYSICS_SYSTEMATIC",
    "PEC_BOX_SYSTEMATIC",
    "PEC_BOX_SYSTEMATIC_EXPONENT",
    "mutual_systematics_ladder",
]

PEC_BOX_SYSTEMATIC = +1.69e-2
PEC_BOX_SYSTEMATIC_EXPONENT = 1.657
GAP_PHYSICS_SYSTEMATIC = -3.0224e-02


def mutual_systematics_ladder(im_z12_ohm: float, omega_m12: float) -> dict:
    """The 3b-xviii ladder: raw ratio → PEC-box corrected → gap-physics corrected.

    A pure function of one measured number, so a gate it drives can be executed
    on the blind fixture's ``Z₁₂ ≡ 0`` as a negative control without a second
    solve.  The two corrections are applied in the order they were measured, and
    each is *additive in the same units it was measured in*:

      * the PEC box moved the **ratio** by ``+D_inf`` pp (a padding
        extrapolation of ``|Im Z₁₂|/ωM₁₂`` itself), so it adds to the ratio;
      * the gap-physics term is a **relative** deviation of the gapped fixture
        against its own closed control, so removing it divides by
        ``1 + GAP_PHYSICS_SYSTEMATIC``.

    Returns every rung, not just the last, so the caller can print the raw
    number beside the corrected one rather than hide it behind the correction.
    ``passes`` is deliberately absent: the band belongs to the caller's gate,
    not to the ladder.
    """
    raw = abs(im_z12_ohm) / omega_m12
    box_corrected = raw + PEC_BOX_SYSTEMATIC
    corrected = box_corrected / (1.0 + GAP_PHYSICS_SYSTEMATIC)
    return {
        "raw": raw,
        "raw_deviation": raw - 1.0,
        "box_corrected": box_corrected,
        "box_deviation": box_corrected - 1.0,
        "corrected": corrected,
        "deviation": corrected - 1.0,
    }
