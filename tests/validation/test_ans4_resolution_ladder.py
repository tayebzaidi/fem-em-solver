"""`ANS-4` step 2 — the Larmor discriminator: does *our* discretisation carry the gap?

The 2026-09-06 weekly review adjudicated `ANS-4` **AGREE at 10 MHz** and
**INCONCLUSIVE at 64 / 128 MHz**: the miss against the operator's HFSS
replication grows with frequency and is several times larger than AED's own
Zero-vs-First-Order shift, which **excludes element order as the cause on the
AED side**.  Two candidates survive, and only moving *our* discretisation
separates them:

* **discretisation** — our fixed 116 085-cell mesh has never had a convergence
  ladder on this fixture (≈ 12 cells/λ and ≈ 5 cells/δ in the 800 S/m legs at
  128 MHz), and the sign of the miss is what more conductor loss resolved
  inside the legs would give;
* **the feed model** — a Larmor-frequency systematic of the lumped sheet.

This module is the pre-registered measurement (§7 `ANS-4` step 2, the first
**XL** slot under §5.1): at 128 MHz only, four degree-1 rungs at
``conductor_resolution`` ×1 / ×0.75 / ×0.6 / ×0.45 plus one **degree-2** solve
on the ×1 mesh, all on `_four_port_rung` — the same constructor the ANS-4
example used to produce the column the operator compared against, which is the
only reason these rungs are comparable with it at all.

**What is asserted** (every band imported and unmoved): on every rung the C4
class spreads against `PORT-11`'s ``ADJACENT_SPREAD_BAND``, passivity against
``PASSIVITY_SIGMA_TOLERANCE``, reciprocity against ``RECIPROCITY_BAND``; the ×1
rung reproduces `GEO-19` step B's cell record; and each finer rung actually
refines **in unknowns** (`PORT-14` step 1b's mechanical control — an ``h``
keyword or a ``degree`` knob that silently did nothing would otherwise read as
a converged ladder).

**What is printed and asserted nowhere**: the three C4 entries `S₁₁` / `S₂₁` /
`S₃₁` on every rung with their relative move from the ×1 record, and a
Richardson h → 0 estimate of those three from the three finest degree-1 rungs.
Those are the readout the ruling is made from, and the ruling is a **review's**,
not this module's — the decision rule is pre-registered in the §7 row and the
comparison against the AED column happens only in gitignored ``docs/private/``.

**No AED number appears in this file, in its log, or in anything it prints.**
Ansys licence terms restrict disclosure of benchmark results (operator
directive 2026-09-02); this module measures our side and stops there.

Run (XL tier, one window, `-n 16` against ``fem-em-solver-xl``)::

    scripts/testing/run_and_log.sh ANS-4-step2 "docker compose exec -T \\
      fem-em-solver-xl bash -lc 'cd /workspace && \\
      source /usr/local/bin/dolfinx-complex-mode && PYTHONPATH=/workspace/src \\
      FEM_EM_REQUIRE_COMPLEX=1 timeout -k 60 7200 mpiexec -n 16 python3 -m \\
      pytest tests/environment tests/validation/test_ans4_resolution_ladder.py \\
      -v -s --tb=short'"

``FEM_EM_ANS4_STEP2_RUNGS`` trims the ladder for a cheap smoke on the ordinary
container (e.g. ``1.0`` builds the ×1 rung alone); unset — the XL window's
value — runs the pre-registered four plus the degree-2 solve.
``FEM_EM_ANS4_STEP2_DEGREE2=0`` suppresses the degree-2 solve, which the rung
list alone does not: step 2a runs the four degree-1 rungs in two ordinary
windows with it off, step 2b runs the degree-2 solve in the XL slot.
``FEM_EM_ANS4_FREQUENCY_HZ`` (step 3a) sets the drive frequency of every rung;
unset is 128 MHz, bit for bit — `xl-pending.md` entry 2 runs it at 64e6.
"""

from __future__ import annotations

import os
import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.utils.instrumentation import report_peak_rss
from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_leg_offset import CONDUCTOR_RESOLUTION, RESOLUTION
from tests.mesh.test_birdcage_port_tags import LEG_COUNT
from tests.validation.test_lossy_sphere_fullwave import (
    FREQUENCY_64_HZ,
    FREQUENCY_128_HZ,
)
from tests.validation.test_port_birdcage_four_port import (
    PASSIVITY_SIGMA_TOLERANCE,
    _circulant_classes,
    _class_spread,
)
from tests.validation.test_port_birdcage_leg_offset_sweep import _four_port_rung
from tests.validation.test_port_birdcage_lumped_column import (
    ADJACENT_SPREAD_BAND,
    STEP2_CELL_COUNT,
    STEP2_CELL_COUNT_BAND,
)
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND

# The pre-registered ladder (§7 `ANS-4` step 2).  ×1 is the record rung — the
# fixture the AED replication was run against — and the three finer rungs are
# `PORT-14` step 1b's measured points (116 085 / 161 695 / 209 604 cells at
# ×1 / ×0.75 / ×0.6), plus ×0.45 which step 1b never built.
LADDER_FACTORS = (1.0, 0.75, 0.6, 0.45)

# The degree-2 solve rides the ×1 mesh: element order is the knob, so the mesh
# must not move with it.  `TH-12` step 2 priced degree 2 at 61.94 GiB on a
# 138 k-cell fixture, which is why this whole module is an XL item.
DEGREE_2_FACTOR = 1.0

RUNG_ENV = "FEM_EM_ANS4_STEP2_RUNGS"

# `ANS-4` step 2c: the **global** resolution ladder, the knob step 2a did not
# turn. 2a refined `conductor_resolution` and broke the fixture's C4 symmetry
# (class spreads 0.1012/0.0916/0.0654% -> 0.5390/0.4591/1.6886% at x0.75,
# against an imported 0.5% band that is not to be widened), so that ladder does
# not exist. The global cell size is a different knob: `GEO-28` measured this
# fixture's quadrant census as symmetric to <= 0.1% in mass, and `GEO-29`
# priced the global ladder's mesh side on this very fixture — 116 085 / 149 049
# / 197 393 / 281 728 cells at 0.015 / 0.012 / 0.0095 / 0.0075, no solve. Set
# this to a space- or comma-separated list of absolute cell sizes in metres and
# the ladder is built over `resolution` instead of `conductor_resolution`.
# Whether it *also* breaks C4 is exactly what the run measures: a break is a
# negative result under the same imported band, never a reason to widen it.
RESOLUTION_ENV = "FEM_EM_ANS4_STEP2_RESOLUTION"

# `ANS-4` step 2d: the **matched-Ansys** ladder — explicit ``h:degree`` rungs,
# because matching AED's setup means moving both knobs together and they do not
# move the same way. By the `ANS-5` correspondence our degree 2 **is** HFSS
# First Order (20 unknowns/tet), and AED's First Order run is its *converged*
# one: it needed only 0.49-0.60 M tets (3.1-3.8 M unknowns) where its Zero
# Order run took 1.28-1.53 M tets, because order buys accuracy per tet. So the
# rung that approximates the AED design is degree 2 at ~0.5 M cells
# (~3.0 M unknowns), **not** degree 2 on the Zero Order mesh — that would be
# ~9.8 M unknowns and ~1.1 TB, past the 512 GiB tier and past anything Ansys
# ran. Format: space- or comma-separated ``<cell size>:<degree>``, coarse to
# fine, e.g. "0.015:1 0.015:2 0.0075:2 0.005:2".
RUNGSPEC_ENV = "FEM_EM_ANS4_STEP2_RUNGSPEC"

# Stop rule for the degree-2 ladder, in **unknowns** rather than cells: cells
# mean different things at different orders, and memory tracks unknowns. ~4.5 M
# is ~400 GiB by the `TH-11` step 5d measurement, which leaves headroom inside
# 512 GiB for the factorisation to overshoot the extrapolation.
STOP_ABOVE_DOFS = 4_500_000

# Stop rules for the 2c cost probe, checked after each rung is built so the
# ladder abandons the next one rather than discovering the wall inside it.
# Both are deliberately generous: the point is to stop before a 7200 s kill
# throws away the rungs already measured, not to second-guess the physics.
STOP_AFTER_S = 5400.0
STOP_ABOVE_CELLS = 2_200_000

# The degree-2 solve is built **unconditionally whenever the x1 factor is in the
# ladder**, and `FEM_EM_ANS4_STEP2_RUNGS` does not suppress it — at >= 49 GiB and
# ~1 100-1 300 s it is step 2b (XL) work and blows an ordinary window.  This
# second additive knob is step 2a's only edit: default on (the XL window's
# value), set to "0" for the two ordinary degree-1 windows.
DEGREE_2_ENV = "FEM_EM_ANS4_STEP2_DEGREE2"

# `ANS-4` step 2a′: `GEO-32`'s opt-in ``c4_congruent_sheets`` lever, threaded
# test-side into every ``_four_port_rung`` call. Unset or "0" = off, which is
# every earlier window's mesh bit for bit; "1" re-runs step 2a's rungs with the
# cut asymmetry removed, to decide whether the cut also carried the x0.75 Z
# class-spread break. A flag-on mesh is not the `GEO-19` record mesh.
C4_CONGRUENT_ENV = "FEM_EM_ANS4_STEP2_C4_CONGRUENT"

# `ANS-4` step 2e (ruling (4), 2026-09-12 03:00 review): a fixed
# ``conductor_resolution`` factor applied to every rung of step 2c's **global**
# ladder, so the bulk (``h_global``) can be refined at a fixed conductor grading.
# 2a‴'s conductor-rung class moves stalled at ~0.7-0.9 % while ``h_global`` and
# ``shell`` never moved; this is the knob that turns both. Unset or empty = off,
# which passes no ``conductor_resolution`` and is every earlier 2c window bit
# for bit. Read inside the 2c loop only: with ``RESOLUTION_ENV`` set,
# ``_ladder_factors()`` is never consulted.
CONDUCTOR_FACTOR_ENV = "FEM_EM_ANS4_STEP2_CONDUCTOR_FACTOR"

# Richardson: fit S(h) = S_inf + C h^p on the three finest degree-1 rungs and
# report p with the extrapolant.  A fit outside this bracket is not an
# asymptotic reading and is reported as such rather than as a number.
RICHARDSON_P_BRACKET = (0.2, 6.0)

# `ANS-4` step 3a: the drive frequency, the knob `docs/testing/xl-pending.md`
# entry 2 (the 64 MHz order-matched rung, `xl`) names as its contract. Unset or
# empty = `FREQUENCY_128_HZ`, which is every earlier window bit for bit; read
# once at import so every rank and every rung sees the same value.
FREQUENCY_ENV = "FEM_EM_ANS4_FREQUENCY_HZ"
_FREQUENCY_RAW = os.environ.get(FREQUENCY_ENV)
if _FREQUENCY_RAW is not None and not _FREQUENCY_RAW.strip():
    _FREQUENCY_RAW = None
LADDER_FREQUENCY_HZ = (
    FREQUENCY_128_HZ if _FREQUENCY_RAW is None else float(_FREQUENCY_RAW.strip())
)

# Step 3a's control record: step 2a″ w1's x1 rung (`c4_congruent_sheets` on,
# degree 1, 128 MHz, 116 118 cells) — the driven column's three C4 classes as
# `20260911T093247Z_ANS-4-step2a-dprime-w1.log:4061-4063` printed them at
# `-n 8`. Restated, not imported: 2a″ kept them in the log only. Version-tagged:
# that commit's image and mesher. `OPS-41`: a digit record holds at its own
# width, so it is asserted at -n 8 and printed elsewhere.
STEP3A_RECORD_128MHZ_C4 = {
    "self": +4.753519992e-01 + 5.808090882e-01j,
    "adjacent": +2.276429111e-01 - 2.671465731e-01j,
    "opposite": +5.269141324e-02 - 2.216384512e-01j,
}
STEP3A_RECORD_RANK_WIDTH = 8
# A reproduction band on printed 10-digit values, pre-stated in §9 (2026-09-14).
STEP3A_RECORD_RTOL = 1.0e-6
# Anchor (b): with the knob set off 128 MHz each class must move from the record
# by more than this. `PORT-11`'s 64 vs 128 MHz records differ by 0.15-0.43 per
# class, so the floor is a mechanical "the knob reached the solve" check, not a
# physics band (§9 item, 2026-09-14).
STEP3A_KNOB_MOVE_FLOOR = 1.0e-2

# Printed only (negative control, *predicted* <= 1e-2): `PORT-11` step 2's
# 64 MHz 4x4 on the 116 085-cell record mesh (`c4_congruent_sheets` off),
# `20260826T110434Z_PORT-11-step2.log.gz:9264-9267`. A different code path and
# image from this module's, so never asserted (§9 standing rule (e)).
PORT11_S_64MHZ_RECORD = np.array(
    [
        [
            +4.488964206e-02 + 5.803022759e-01j,
            +3.665309492e-01 - 2.047414920e-01j,
            +2.179345683e-01 - 2.566177401e-01j,
            +3.666851521e-01 - 2.046184160e-01j,
        ],
        [
            +3.665309492e-01 - 2.047414920e-01j,
            +4.502611557e-02 + 5.803272622e-01j,
            +3.664836475e-01 - 2.046732440e-01j,
            +2.180174288e-01 - 2.566226721e-01j,
        ],
        [
            +2.179345683e-01 - 2.566177401e-01j,
            +3.664836475e-01 - 2.046732440e-01j,
            +4.521165287e-02 + 5.801842868e-01j,
            +3.664555549e-01 - 2.046024681e-01j,
        ],
        [
            +3.666851521e-01 - 2.046184160e-01j,
            +2.180174288e-01 - 2.566226721e-01j,
            +3.664555549e-01 - 2.046024681e-01j,
            +4.482996690e-02 + 5.802149382e-01j,
        ],
    ],
    dtype=np.complex128,
)


def _ladder_factors():
    """The pre-registered ladder, or a trimmed one for a non-XL smoke."""
    raw = os.environ.get(RUNG_ENV)
    if raw is None or not raw.strip():
        return LADDER_FACTORS
    return tuple(float(v) for v in raw.replace(",", " ").split())


def _ladder_rungspec():
    """Step 2d's explicit ``(cell size, degree)`` rungs, or ``()`` if unselected."""
    raw = os.environ.get(RUNGSPEC_ENV)
    if raw is None or not raw.strip():
        return ()
    out = []
    for token in raw.replace(",", " ").split():
        h, _, deg = token.partition(":")
        out.append((float(h), int(deg) if deg else 1))
    return tuple(out)


def _estimated_dofs(cells, degree):
    """N1curl unknowns for a tet mesh: ~1.2 N edges, ~2 N faces.

    degree 1 -> 1 per edge = 1.2 N; degree 2 -> 2 per edge + 2 per face = 6.4 N.
    The 6.4 is the same ratio AED's own matrix sizes confirmed (`ANS-4` notes,
    measured 6.34), so this is a cross-checked estimate, not a guess. Printed
    for the stop rule and the record; nothing is gated on it.
    """
    return (1.2 if degree == 1 else 6.4) * float(cells)


def _refinement_measure(rung):
    """The currency the refinement guard counts in: **estimated unknowns**.

    Cells are the wrong currency for a ladder that refines in ``h`` *and* ``p``.
    Step 2d's rungspec (``0.015:1 0.015:2 …``) deliberately holds the mesh fixed
    and raises the element order, so two consecutive rungs share a cell count by
    construction while the discretisation genuinely refines — the `ANS-4` step 3e
    window (2026-09-22) died on exactly that, 116 085 cells against 116 085 with
    ~139 302 -> ~742 944 unknowns between them.  Unknowns are the same currency
    this module's stop rule already uses (``STOP_ABOVE_DOFS``, and the comment
    above it), through the same `_estimated_dofs`; no second estimator exists.

    Counting unknowns is **strictly stronger** than counting cells here: an inert
    ``h`` keyword still gives identical meshes at a fixed degree and so identical
    unknowns, and an inert ``degree`` knob — which a cell count cannot see at all
    — is caught too.
    """
    return _estimated_dofs(rung["cells"], int(rung.get("degree", 1)))


def _check_refines(rungs):
    """Consecutive rung pairs that did **not** refine, coarse to fine.

    Pure: takes the rung dicts (only ``cells``, ``degree``, ``factor`` and the
    optional ``knob`` are read) and returns a list of
    ``(coarser, finer, dofs_coarser, dofs_finer)``.  Empty means every step of
    the ladder increased the unknown count strictly.  Strictly: no tolerance, no
    ``>=``, no exemption for equal cells.
    """
    failures = []
    for coarser, finer in zip(rungs, rungs[1:]):
        dofs_c = _refinement_measure(coarser)
        dofs_f = _refinement_measure(finer)
        if not dofs_f > dofs_c:
            failures.append((coarser, finer, dofs_c, dofs_f))
    return failures


def _ladder_resolutions():
    """Step 2c's global cell sizes in metres, or ``()`` when 2c is not selected."""
    raw = os.environ.get(RESOLUTION_ENV)
    if raw is None or not raw.strip():
        return ()
    return tuple(float(v) for v in raw.replace(",", " ").split())


def _degree2_enabled():
    """Whether to build the degree-2 solve. Default on; ``0``/``false``/``no`` off."""
    raw = os.environ.get(DEGREE_2_ENV)
    if raw is None or not raw.strip():
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _c4_congruent_enabled():
    """Whether rungs build with ``c4_congruent_sheets``. Default **off**."""
    raw = os.environ.get(C4_CONGRUENT_ENV)
    if raw is None or not raw.strip():
        return False
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _conductor_factor():
    """Step 2e's fixed conductor factor for the 2c ladder, or ``None`` when off."""
    raw = os.environ.get(CONDUCTOR_FACTOR_ENV)
    if raw is None or not raw.strip():
        return None
    return float(raw.strip())


def _require_explicit_c4_flag(factors):
    """Refuse a ``conductor_resolution`` ladder beyond x1 with the flag *unset*.

    Ruled 2026-09-11 03:00 (known-issues, the 2026-09-09 `ANS-4` step 2a
    entry): on the default flag-off mesher path any factor other than 1.0
    meshes a C2-not-C4 gap-sheet cut and breaks the imported 0.5 % `Z` class
    spread (``20260909T093534Z_ANS-4-step2a.log``). Rather than flip the
    mesher default (which would move the `GEO-19` record), this module
    requires the choice to be explicit. ``=0`` stays allowed: it is the
    documented flag-off negative control. Pure env logic, identical on every
    rank, so every rank raises and nothing hangs.
    """
    raw = os.environ.get(C4_CONGRUENT_ENV)
    if raw is not None and raw.strip():
        return
    finer = [f for f in factors if float(f) != 1.0]
    # Step 2e: the fixed conductor factor on the 2c ladder is the same knob, so
    # the same C2-not-C4 cut refuses it with the flag unset.
    conductor_factor = _conductor_factor()
    if conductor_factor is not None and conductor_factor != 1.0:
        finer.append(conductor_factor)
    if finer:
        raise ValueError(
            f"{C4_CONGRUENT_ENV} is unset but the conductor_resolution ladder "
            f"contains factor(s) {', '.join(f'x{f:g}' for f in finer)} other "
            "than x1. On the default flag-off mesher path those rungs mesh a "
            "C2-not-C4 port-sheet cut and fail the imported 0.5 % Z class "
            "spread — see docs/testing/known-issues.md, the 2026-09-09 `ANS-4` "
            f"step 2a entry. Set {C4_CONGRUENT_ENV}=1 to measure the ladder "
            f"(c4_congruent_sheets on), or {C4_CONGRUENT_ENV}=0 to run the "
            "flag-off negative control deliberately."
        )


def _report_rung_rss(comm, label):
    """`OPS-43` (c): summed peak RSS after a rung. Collective — every rank calls it."""
    report_peak_rss(comm, label=f"ANS-4 step2 after {label}")



def _control_rung(rungs):
    """The rung that must reproduce the 116 085-cell record, either ladder.

    2a's control is ``conductor_resolution`` ×1; 2c's is the fixture's own
    global ``RESOLUTION``. Both are "the fixture as every gate builds it", and
    both must land on the record — that is what makes the finer rungs of
    either ladder comparable with the AED column.
    """
    for r in rungs:
        if r.get("knob") == "resolution" and r["factor"] == float(RESOLUTION):
            return r
        if r.get("knob") != "resolution" and r["factor"] == 1.0:
            return r
    return None


def _class_entries(m):
    """The three C4 classes of a circulant 4x4: self, adjacent (90 deg), opposite.

    Verbatim the ANS-4 example's own reader, so these are the same three
    numbers the private comparison table holds for our side.
    """
    return {"self": m[0, 0], "adjacent": m[1, 0], "opposite": m[2, 0]}


def _richardson(hs, values):
    """Fit ``S(h) = S_inf + C h**p`` on three points; return (S_inf, p) or None.

    Unequal spacing, so the exponent comes from the ratio of successive
    differences rather than a fixed-refinement formula.  Returns ``None`` when
    the three points are not in an asymptotic range — a monotone-in-h
    assumption that does not hold produces no number here rather than a
    fabricated one.
    """
    if len(hs) != 3:
        return None
    h1, h2, h3 = (float(h) for h in hs)
    s1, s2, s3 = (complex(v) for v in values)
    d1, d2 = s2 - s1, s3 - s2
    if abs(d1) == 0.0 or abs(d2) == 0.0:
        return None
    ratio = abs(d2) / abs(d1)

    def residual(p):
        return (h3**p - h2**p) / (h2**p - h1**p) - ratio

    lo, hi = RICHARDSON_P_BRACKET
    f_lo, f_hi = residual(lo), residual(hi)
    if not np.isfinite(f_lo) or not np.isfinite(f_hi) or f_lo * f_hi > 0.0:
        return None
    for _ in range(200):  # bisection: no scipy dependency, and p is scalar
        mid = 0.5 * (lo + hi)
        f_mid = residual(mid)
        if f_lo * f_mid <= 0.0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    p = 0.5 * (lo + hi)
    denom = h3**p - h2**p
    if denom == 0.0:
        return None
    c = d2 / denom
    return complex(s3 - c * h3**p), float(p)


@pytest.fixture(scope="module")
def ladder():
    """Every rung of the pre-registered ladder, built once for the window."""
    comm = MPI.COMM_WORLD
    zeros = np.zeros(LEG_COUNT)
    rungspec = _ladder_rungspec()
    resolutions = () if rungspec else _ladder_resolutions()
    factors = () if (rungspec or resolutions) else _ladder_factors()
    # The known-issues guard (ruled 2026-09-11 03:00): before any mesh.
    _require_explicit_c4_flag(factors)
    rungs = []
    started = time.perf_counter()
    c4 = _c4_congruent_enabled()
    c4_tag = f"c4_congruent_sheets={'on' if c4 else 'off'}"

    # --- step 2d: the matched-Ansys ladder, explicit (h, degree) per rung.
    for res, deg in rungspec:
        rung = _four_port_rung(
            f"ANS-4 step2d h={res:g} degree {deg} {c4_tag}",
            zeros,
            LADDER_FREQUENCY_HZ,
            resolution=res,
            degree=deg,
            c4_congruent_sheets=c4,
        )
        _report_rung_rss(comm, f"step2d h={res:g} degree {deg} {c4_tag}")
        rung["factor"] = float(res)
        rung["knob"] = "resolution"
        rungs.append(rung)
        dofs = _estimated_dofs(rung["cells"], deg)
        elapsed = time.perf_counter() - started
        if comm.rank == 0:
            print(
                f"[ANS-4 step2d] rung h={res:g} degree {deg} ({c4_tag}): "
                f"{rung['cells']} cells, "
                f"~{dofs:,.0f} unknowns, mesh {rung['mesh_time']:.1f} s, four drives "
                f"{rung['sweep_time']:.1f} s at -n {comm.size}; ladder elapsed "
                f"{elapsed:.0f} s",
                flush=True,
            )
        if dofs > STOP_ABOVE_DOFS or elapsed > STOP_AFTER_S:
            if comm.rank == 0:
                print(
                    f"[ANS-4 step2d] STOP RULE fired after h={res:g} degree {deg}: "
                    f"~{dofs:,.0f} unknowns (ceiling {STOP_ABOVE_DOFS:,}), elapsed "
                    f"{elapsed:.0f} s (ceiling {STOP_AFTER_S:.0f} s). Remaining rungs "
                    "not built; the rungs above stand.",
                    flush=True,
                )
            break

    # --- step 2c: the global-resolution ladder, coarse to fine, with a stop
    # rule after each rung so a wall costs the next rung and not the ones
    # already measured.
    # Step 2e: a fixed conductor factor, read here and never through `factors`.
    conductor_factor = _conductor_factor() if resolutions else None
    h_c = (
        None if conductor_factor is None else conductor_factor * CONDUCTOR_RESOLUTION
    )
    cf_tag = "" if conductor_factor is None else f" conductor x{conductor_factor:g}"
    for res in resolutions:
        rung = _four_port_rung(
            f"ANS-4 step2c h={res:g}{cf_tag} degree 1 {c4_tag}",
            zeros,
            LADDER_FREQUENCY_HZ,
            resolution=res,
            conductor_resolution=h_c,
            c4_congruent_sheets=c4,
        )
        _report_rung_rss(comm, f"step2c h={res:g}{cf_tag} degree 1 {c4_tag}")
        rung["factor"] = float(res)
        rung["knob"] = "resolution"
        rung["conductor_factor"] = conductor_factor
        rungs.append(rung)
        elapsed = time.perf_counter() - started
        if comm.rank == 0:
            print(
                f"[ANS-4 step2c] rung h={res:g}{cf_tag} ({c4_tag}): "
                f"{rung['cells']} cells, mesh "
                f"{rung['mesh_time']:.1f} s, four drives {rung['sweep_time']:.1f} s "
                f"at -n {comm.size}; ladder elapsed {elapsed:.0f} s",
                flush=True,
            )
        if rung["cells"] > STOP_ABOVE_CELLS or elapsed > STOP_AFTER_S:
            if comm.rank == 0:
                print(
                    f"[ANS-4 step2c] STOP RULE fired after h={res:g}: "
                    f"{rung['cells']} cells (ceiling {STOP_ABOVE_CELLS}), ladder "
                    f"elapsed {elapsed:.0f} s (ceiling {STOP_AFTER_S:.0f} s). "
                    "Remaining rungs not built; the rungs above stand.",
                    flush=True,
                )
            break

    for factor in factors:
        h_c = float(factor) * CONDUCTOR_RESOLUTION
        rung = _four_port_rung(
            f"ANS-4 step2 x{factor:g} degree 1 {c4_tag}",
            zeros,
            LADDER_FREQUENCY_HZ,
            conductor_resolution=h_c,
            c4_congruent_sheets=c4,
        )
        rung["factor"] = float(factor)
        rung["knob"] = "conductor_resolution"
        rungs.append(rung)
        _report_rung_rss(comm, f"step2 x{factor:g} degree 1 {c4_tag}")
        if comm.rank == 0:
            print(
                f"[ANS-4 step2] rung x{factor:g} degree 1 ({c4_tag}): "
                f"{rung['cells']} cells, "
                f"mesh {rung['mesh_time']:.1f} s, four drives "
                f"{rung['sweep_time']:.1f} s at -n {comm.size}",
                flush=True,
            )

    # Degree 2 on the x1 mesh: reuse the record rung so the element order is
    # demonstrably the only knob turned between it and rung x1.
    base = next((r for r in rungs if r["factor"] == DEGREE_2_FACTOR), None)
    degree2 = None
    if base is not None and not _degree2_enabled():
        if comm.rank == 0:
            print(
                f"[ANS-4 step2] degree-2 solve suppressed by {DEGREE_2_ENV} — "
                "this is a step-2a degree-1 window; the degree-2 control is 2b",
                flush=True,
            )
    elif base is not None:
        degree2 = _four_port_rung(
            f"ANS-4 step2 x1 degree 2 {c4_tag}",
            zeros,
            LADDER_FREQUENCY_HZ,
            reuse=base,
            degree=2,
            c4_congruent_sheets=c4,
        )
        degree2["factor"] = float(DEGREE_2_FACTOR)
        _report_rung_rss(comm, f"step2 x1 degree 2 {c4_tag}")
        if comm.rank == 0:
            print(
                f"[ANS-4 step2] rung x1 degree 2: {degree2['cells']} cells "
                f"(reused mesh {degree2['reused_mesh']}), four drives "
                f"{degree2['sweep_time']:.1f} s at -n {comm.size}",
                flush=True,
            )

    if comm.rank == 0:
        print(
            f"[ANS-4 step2] ladder built in {time.perf_counter() - started:.1f} s "
            f"wall at -n {comm.size}, f = {LADDER_FREQUENCY_HZ:.6e} Hz "
            f"({FREQUENCY_ENV}={'unset' if _FREQUENCY_RAW is None else _FREQUENCY_RAW})",
            flush=True,
        )
    return {"rungs": rungs, "degree2": degree2}


@complex_only
def test_the_record_rung_reproduces_the_fixture(ladder):
    """The x1 rung is the fixture the AED column was replicated against.

    This is also the control on the two additive keywords: passing
    ``conductor_resolution=1.0 * CONDUCTOR_RESOLUTION`` explicitly must build
    the mesh the gate builds with the keyword absent.
    """
    comm = MPI.COMM_WORLD
    base = _control_rung(ladder["rungs"])
    if base is None:
        pytest.skip("the control rung is not in this ladder")
    base_cf = base.get("conductor_factor")
    if base_cf is not None and base_cf != 1.0:
        # Step 2e: `_control_rung` matches `resolution == RESOLUTION`, but with
        # the conductor factor on that rung is the flag-on x{factor} mesh, not
        # the 116 085 record — skip rather than widen STEP2_CELL_COUNT_BAND.
        if comm.rank == 0:
            print(
                f"[ANS-4 step2e] control rung h={base['factor']:g} conductor "
                f"x{base_cf:g}: {base['cells']} cells (not the `GEO-19` record "
                f"{STEP2_CELL_COUNT}; record check skipped)",
                flush=True,
            )
        pytest.skip(
            f"{CONDUCTOR_FACTOR_ENV}={base_cf:g}: the h={base['factor']:g} rung "
            f"meshed {base['cells']} cells at conductor x{base_cf:g}, not the "
            "116 085-cell record fixture"
        )
    ratio =base["cells"] / STEP2_CELL_COUNT
    if comm.rank == 0:
        print(
            f"[ANS-4 step2] x1 rung: {base['cells']} cells against `GEO-19` "
            f"step B's record {STEP2_CELL_COUNT}, ratio {ratio:.6f} "
            f"(band {STEP2_CELL_COUNT_BAND:.0e})",
            flush=True,
        )
    assert abs(ratio - 1.0) < STEP2_CELL_COUNT_BAND, (
        f"the x1 rung meshed {base['cells']} cells against the record "
        f"{STEP2_CELL_COUNT} (ratio {ratio:.6f}) — this is not the fixture the "
        "AED column was replicated against, so no rung below is comparable "
        "with it and the ladder measures nothing about ANS-4"
    )


@complex_only
def test_every_finer_rung_actually_refines(ladder):
    """`PORT-14` step 1b's mechanical control on the refinement knobs.

    A ``conductor_resolution`` (or ``resolution``) that silently did nothing
    would produce four identical rungs, which would read as a perfectly
    converged ladder — the most dangerous possible false positive for this
    measurement.  A ``degree`` that silently did nothing is the same false
    positive on step 2d's ``h:degree`` ladder, and the cell count is blind to
    it.  The measure is therefore **unknowns** (`_refinement_measure`, the
    ``STOP_ABOVE_DOFS`` currency), which covers both and is strictly stronger
    than the cell count it replaced (`OPS-62`, 2026-09-22).  Cells stay in the
    printed readout so an XL log still shows the mesh sizes.
    """
    comm = MPI.COMM_WORLD
    rungs = sorted(ladder["rungs"], key=lambda r: -r["factor"])
    if len(rungs) < 2:
        pytest.skip("a single-rung ladder cannot show refinement")
    if comm.rank == 0:
        for r in rungs:
            print(
                f"[ANS-4 step2] refinement: x{r['factor']:g} degree "
                f"{int(r.get('degree', 1))} -> {r['cells']} cells, "
                f"~{_refinement_measure(r):,.0f} unknowns",
                flush=True,
            )
    failures = _check_refines(rungs)
    assert not failures, "; ".join(
        f"{finer.get('knob', 'conductor_resolution')} rung {finer['factor']:g} "
        f"degree {int(finer.get('degree', 1))} gave ~{dofs_f:,.0f} unknowns, not "
        f"more than rung {coarser['factor']:g} degree "
        f"{int(coarser.get('degree', 1))}'s ~{dofs_c:,.0f} — neither the cell "
        "size nor the element order reached the solve on that step, so those two "
        "rungs are one discretisation re-solved rather than a convergence step"
        for coarser, finer, dofs_c, dofs_f in failures
    )


def _synthetic_rung(factor, cells, degree):
    """A rung dict carrying only what `_check_refines` reads."""
    return {"factor": float(factor), "cells": int(cells), "degree": int(degree)}


def test_refinement_check_controls():
    """`OPS-62` — the refinement guard's comparison logic, without a solve.

    The guard itself only runs behind the XL-scale ``ladder`` fixture, so the
    rule it enforces is tested here on synthetic rungs.  Each case is a fact
    about `_check_refines`, not about the mesher.
    """
    # 1. An inert refinement keyword: four identical rungs. Caught on every step.
    inert = [_synthetic_rung(f, 116_085, 1) for f in (0.015, 0.012, 0.0095, 0.0075)]
    assert len(_check_refines(inert)) == 3

    # 2. A p-rung: the same mesh at degree 1 then degree 2. This is the case the
    #    cell-count guard failed on in the `ANS-4` step 3e window (2026-09-22).
    p_rung = [_synthetic_rung(0.015, 116_085, 1), _synthetic_rung(0.015, 116_085, 2)]
    assert _check_refines(p_rung) == []
    assert _refinement_measure(p_rung[0]) == pytest.approx(139_302.0)
    assert _refinement_measure(p_rung[1]) == pytest.approx(742_944.0)

    # 3. An h-rung: more cells at a fixed degree.
    h_rung = [_synthetic_rung(0.015, 116_085, 1), _synthetic_rung(0.0075, 281_728, 1)]
    assert _check_refines(h_rung) == []

    # 4. The real step 3e ladder, `0.015:1 0.015:2 0.0075:2 0.005:2`, with the
    #    cell counts that window measured.
    step3e = [
        _synthetic_rung(0.015, 116_085, 1),
        _synthetic_rung(0.015, 116_085, 2),
        _synthetic_rung(0.0075, 281_728, 2),
        _synthetic_rung(0.005, 592_744, 2),
    ]
    assert _check_refines(step3e) == []

    # 5. A degree *drop* at fixed h: unknowns fall, so it is caught.
    drop = [_synthetic_rung(0.015, 116_085, 2), _synthetic_rung(0.015, 116_085, 1)]
    assert len(_check_refines(drop)) == 1

    # 6. Equal unknowns between consecutive rungs: 1600 x 1.2 == 300 x 6.4.
    tie = [_synthetic_rung(0.02, 1_600, 1), _synthetic_rung(0.015, 300, 2)]
    assert _refinement_measure(tie[0]) == _refinement_measure(tie[1])
    assert len(_check_refines(tie)) == 1

    # 7. Strictly stronger than the cell count it replaced: cells rise while the
    #    degree knob goes inert-and-backwards, so the old guard passed this and
    #    the new one does not.
    stronger = [_synthetic_rung(0.015, 100_000, 2), _synthetic_rung(0.0075, 200_000, 1)]
    assert stronger[1]["cells"] > stronger[0]["cells"]
    assert len(_check_refines(stronger)) == 1


@complex_only
def test_every_rung_passes_the_imported_port11_gates(ladder):
    """Reciprocity, passivity and C4 symmetry on every rung, bands unmoved.

    A rung that fails these is not a usable point on the ladder, whatever its
    S entries read — the refinement would have broken the port model rather
    than resolved it.
    """
    comm = MPI.COMM_WORLD
    everything = list(ladder["rungs"]) + (
        [ladder["degree2"]] if ladder["degree2"] is not None else []
    )
    for rung in everything:
        reciprocity = float(rung["reciprocity"])
        sigma_max = float(np.max(rung["sigma"]))
        spreads = rung["spreads"]
        label = f"x{rung['factor']:g} degree {rung['degree']}"
        if comm.rank == 0:
            print(
                f"[ANS-4 step2] gates {label}: ||S-S^T||/||S|| = "
                f"{reciprocity:.9e} (band {RECIPROCITY_BAND:.0e}); sigma_max = "
                f"{sigma_max:.12f} (ceiling 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e}); "
                "class spreads "
                + "  ".join(f"{k} {v * 100:.4f}%" for k, v in spreads.items())
                + f" (band {ADJACENT_SPREAD_BAND * 100:.1f}%)",
                flush=True,
            )
        assert not rung["result"].is_placeholder, f"{label}: placeholder route"
        assert reciprocity <= RECIPROCITY_BAND, (
            f"{label}: reciprocity {reciprocity:.9e} exceeds the imported, "
            f"unmoved {RECIPROCITY_BAND:.0e}"
        )
        assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
            f"{label}: sigma_max {sigma_max:.12f} exceeds passivity"
        )
        for name, value in spreads.items():
            assert value <= ADJACENT_SPREAD_BAND, (
                f"{label}: {name} class spread {value * 100:.4f}% exceeds the "
                f"imported, unmoved {ADJACENT_SPREAD_BAND * 100:.1f}%"
            )


@complex_only
def test_the_ladder_readout_is_printed(ladder):
    """The pre-registered readout. Asserts nothing about the S entries.

    Whether the moves below close the gap against the AED column is the
    **review's** ruling, made in gitignored ``docs/private/`` against the
    decision rule written in the §7 row before this ran.  Nothing here
    compares against an AED number, and nothing here may.
    """
    comm = MPI.COMM_WORLD
    rungs = sorted(ladder["rungs"], key=lambda r: -r["factor"])
    base = _control_rung(rungs)
    if comm.rank != 0:
        return
    names = ("self", "adjacent", "opposite")
    labels = {"self": "S11", "adjacent": "S21", "opposite": "S31"}

    base_entries = _class_entries(np.asarray(base["s"])) if base is not None else None
    print(
        f"\n[ANS-4 step2] === the readout: three C4 classes of S at "
        f"{LADDER_FREQUENCY_HZ / 1e6:g} MHz ===",
        flush=True,
    )
    for rung in rungs + ([ladder["degree2"]] if ladder["degree2"] else []):
        entries = _class_entries(np.asarray(rung["s"]))
        s_spreads = {
            n: _class_spread(_circulant_classes(np.asarray(rung["s"]))[n])
            for n in names
        }
        tag = f"x{rung['factor']:g} degree {rung['degree']}"
        print(f"[ANS-4 step2] rung {tag} ({rung['cells']} cells):", flush=True)
        for n in names:
            value = complex(entries[n])
            line = f"    {labels[n]} = {value.real:+.9e} {value.imag:+.9e}j"
            if base_entries is not None:
                ref = complex(base_entries[n])
                if abs(ref) > 0.0:
                    move = abs(value - ref) / abs(ref)
                    line += f"   move from control = {move * 100:9.4f}%"
            line += f"   S-class spread {s_spreads[n] * 100:.4f}%"
            print(line, flush=True)

    # Richardson on the three finest degree-1 rungs, as pre-registered.
    fine = sorted(
        (r for r in ladder["rungs"] if r["factor"] < 1.0), key=lambda r: -r["factor"]
    )
    print("\n[ANS-4 step2] Richardson h -> 0 (three finest degree-1 rungs):", flush=True)
    if len(fine) != 3:
        print(
            f"    not attempted: {len(fine)} rungs finer than x1, the estimate "
            "needs exactly three",
            flush=True,
        )
        return
    hs = [r["factor"] for r in fine]
    print(
        "    fitting S(h) = S_inf + C h^p on factors "
        + ", ".join(f"x{h:g}" for h in hs),
        flush=True,
    )
    for n in names:
        values = [_class_entries(np.asarray(r["s"]))[n] for r in fine]
        fit = _richardson(hs, values)
        if fit is None:
            print(
                f"    {labels[n]}: no estimate — the three points are not in an "
                "asymptotic range (non-monotone or the fitted exponent left "
                f"the {RICHARDSON_P_BRACKET} bracket)",
                flush=True,
            )
            continue
        s_inf, p = fit
        line = (
            f"    {labels[n]}: S_inf = {s_inf.real:+.9e} {s_inf.imag:+.9e}j   "
            f"fitted p = {p:.4f}"
        )
        if base_entries is not None:
            ref = complex(base_entries[n])
            if abs(ref) > 0.0:
                line += f"   move from control = {abs(s_inf - ref) / abs(ref) * 100:9.4f}%"
        print(line, flush=True)


def _class_of(i, j, n=LEG_COUNT):
    """C4 class of entry ``(i, j)``: 0 self, 1 adjacent, 2 opposite."""
    d = (i - j) % n
    return min(d, n - d)


@complex_only
def test_the_frequency_knob_reaches_the_solve(ladder):
    """`ANS-4` step 3a: ``FEM_EM_ANS4_FREQUENCY_HZ`` — the flag-off control and the knob.

    Unset (128 MHz) on the `c4_congruent_sheets` x1 degree-1 rung, the driven
    column reproduces step 2a″'s record at ``STEP3A_RECORD_RTOL``, asserted at
    the record's own width (`OPS-41`) — the knob's default is the old constant.
    Set to any other frequency, every C4 class must move from that record by
    more than ``STEP3A_KNOB_MOVE_FLOOR`` — a knob that never reached the solve
    would reproduce the 128 MHz digits. At 64 MHz the rung's 4x4 is printed
    beside `PORT-11` step 2's record as a *predicted* negative control.
    """
    comm = MPI.COMM_WORLD
    control = next(
        (
            r
            for r in ladder["rungs"]
            if r is _control_rung([r])
            and r["degree"] == 1
            and r.get("conductor_factor") in (None, 1.0)
        ),
        None,
    )
    if control is None:
        pytest.skip("no x1 degree-1 control rung in this ladder")
    s = np.asarray(control["s"])
    entries = {k: complex(v) for k, v in _class_entries(s).items()}
    c4 = _c4_congruent_enabled()
    is_default = LADDER_FREQUENCY_HZ == FREQUENCY_128_HZ
    moves = {
        k: abs(entries[k] - STEP3A_RECORD_128MHZ_C4[k]) for k in STEP3A_RECORD_128MHZ_C4
    }
    if comm.rank == 0:
        print(
            f"[ANS-4 step3a] f = {LADDER_FREQUENCY_HZ:.6e} Hz "
            f"({FREQUENCY_ENV}={'unset' if _FREQUENCY_RAW is None else _FREQUENCY_RAW}), "
            f"c4_congruent_sheets={'on' if c4 else 'off'}, {control['cells']} cells, "
            f"-n {comm.size} (record width -n {STEP3A_RECORD_RANK_WIDTH})",
            flush=True,
        )
        for k, label in (("self", "S11"), ("adjacent", "S21"), ("opposite", "S31")):
            ref = STEP3A_RECORD_128MHZ_C4[k]
            print(
                f"    {label} = {entries[k].real:+.9e} {entries[k].imag:+.9e}j   "
                f"2a″ record {ref.real:+.9e} {ref.imag:+.9e}j   |dS| = "
                f"{moves[k]:.9e}   rel = {moves[k] / abs(ref):.3e}",
                flush=True,
            )

    if is_default:
        if not c4:
            pytest.skip(
                "the 2a″ record is the c4_congruent_sheets mesh; this flag-off "
                "128 MHz rung is printed above, not compared"
            )
        if comm.size != STEP3A_RECORD_RANK_WIDTH:
            pytest.skip(
                f"2a″ digit record set at -n {STEP3A_RECORD_RANK_WIDTH}; this is "
                f"-n {comm.size} (OPS-41) — readings printed above"
            )
        for k, ref in STEP3A_RECORD_128MHZ_C4.items():
            rel = moves[k] / abs(ref)
            assert rel <= STEP3A_RECORD_RTOL, (
                f"flag-off control: {k} class moved {rel:.3e} from 2a″'s record "
                f"(rtol {STEP3A_RECORD_RTOL:.0e}) — the x1 rung has drifted since "
                "2026-09-11, or the knob's default is not the old constant"
            )
        return

    if comm.rank == 0 and np.isclose(LADDER_FREQUENCY_HZ, FREQUENCY_64_HZ):
        diff = np.abs(s - PORT11_S_64MHZ_RECORD)
        per_class = {
            name: max(
                float(diff[i, j])
                for i in range(LEG_COUNT)
                for j in range(LEG_COUNT)
                if _class_of(i, j) == c
            )
            for c, name in enumerate(("self", "adjacent", "opposite"))
        }
        print(
            "[ANS-4 step3a] negative control (predicted <= 1e-2, printed only): "
            "per-class max|dS| against PORT-11 step 2's 64 MHz 4x4 — "
            + "  ".join(f"{k} {v:.3e}" for k, v in per_class.items()),
            flush=True,
        )
    for k, move in moves.items():
        assert move > STEP3A_KNOB_MOVE_FLOOR, (
            f"{FREQUENCY_ENV}={_FREQUENCY_RAW}: the {k} class moved only "
            f"{move:.3e} from the 128 MHz record (floor {STEP3A_KNOB_MOVE_FLOOR:.0e})"
            " — the knob is not reaching the solve"
        )
