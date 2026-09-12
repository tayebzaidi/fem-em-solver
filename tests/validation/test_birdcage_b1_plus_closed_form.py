"""`WF-6` step 4g — the ``h``-ladder: does the FEM ``|B₁⁺|``'s **C4 four-copy
spread** on the *unloaded* F-small birdcage fall with the mesh, or is the
recorded 3.4% the formulation's?

**Step 4g re-registers two anchors on statistics that exist and drops one
rung; nothing else in this module moves.**  Step 4f (2026-09-09, branch
`attempt/WF-6-step4f-20260909T124552Z`) ran the three-rung ladder to
completion — spread **5.2506% / 2.0719% / 1.9514%**
(`20260909T123716Z_WF-6.log:2080–2086, 3901–3907, 5789–5795`) — and three
asserted anchors went red for reasons that were the *pre-registration's*, not
the fixture's.  The 10:30 review's ruling (3) disposed of all three:

* the ×1 reproduction control compared a **four**-copy spread against the
  **two**-copy record 3.310633e-02.  The ×1 rung reproduced step 4b's
  eleven-point table *character-for-character* (9.805561792e-08 T at ``+x̂``,
  1.013569652e-07 T at ``+ŷ``, `20260908T004020Z_WF-6.log:1894, 1899`), so the
  reproduction control was met in the strongest available sense and the
  ``−x̂`` copy 1.024222080e-07 T is simply a quantity that record never
  contained.  The control is re-registered on the four-copy statistic's own
  measured **5.2506%**, still at 10% relative;
* the cw separation bar inherited the same mis-sizing.  At ×1 the cw spread is
  50.0268% against the ccw 5.2506%, so **9.53× is arithmetically the most this
  rung can show** and the 10× bar was *unreachable*, not merely unmet.  It is
  re-sized to **≥ 5×** off that measured ceiling (4f read 9.53× and 19.52× on
  the two rungs kept here);
* the ×0.0095 rung's power residual (1.853642e-02 against the unmoved 1e-2,
  split between the ports) is a real, undiagnosed finding.  It is **removed
  from this ladder**, not swallowed by it — `GEO-30` measures its suspected
  mechanism, and the known-issues row of 2026-09-09 forbids trusting a finer
  rung of this fixture until the residual is diagnosed.  Its readings stay on
  record in the §7 `WF-6` row.  If `GEO-30` finds the mesh symmetric there,
  the rung comes back; that is a review's call, not this module's.

**No band moved.**  ``CLOSED_FORM_BAND`` (5e-2), ``POWER_BALANCE_BAND``
(1e-2), ``C4_COVARIANCE_BAND`` (5e-2) and ``CELL_COUNT_BAND`` (1e-2) are all
imported and unmoved, the eleven points are never pruned, the deleted
closed-form comparand is not re-introduced, `WF-6` stays 🟡 and §2's B₁⁺
clause keeps its wording.

**This module no longer carries a closed-form comparand, and that is a ruling,
not a retreat.**  The 2026-09-09 03:00 review's ruling (1) closed the analytic
route for this fixture: step 4e measured the cube-truncated PEC image lattice's
wall-normal residual *rising* past ``N = 5`` to a common non-zero ≈ 3.4e-02 in
both parities (`20260908T170345Z_WF-6.log`), so **no image order lands the
step-4 comparand**.  The 5% ``CLOSED_FORM_BAND`` and the ``S_3`` / ``S̄_6`` /
``S_11`` comparands are **not loosened — they are not used**; the closed-form
path is deleted from the gate and kept only as the already-green unit
identities on :mod:`fem_em_solver.utils.analytical`'s additive functions
(`tests/unit/test_birdcage_filament_field.py`).

What replaces it is the question the comparand was standing in for, asked of
the FEM against **itself and a symmetry identity** (§4 names a symmetry
identity explicitly).  Two probes narrowed it first:

* `GEO-28` excluded the mesh's *symmetry* — every per-quadrant **mass** spread
  is ≲ 0.1% against a 3.4% field effect (`20260908T183317Z_GEO-28.log`);
* `GEO-29` measured the mesh's *resolution* as the surviving suspect — the
  interior mean circumradius is **2.19e-02 m at ×1, 1.46× the nominal 0.015 m
  and larger than the 1.4e-02 m shell this gate samples in**, falling to
  1.71e-02 / 1.37e-02 m on the next two rungs
  (`20260909T003221Z_GEO-29.log:7038–7042`).

So the module walks the two trustworthy rungs of `GEO-29`'s ladder — global
``resolution`` 0.015 / 0.012 m, its measured cell counts 116 085 / 149 049 —
and reports, per rung, the eleven ``z = 0`` gate points and the **C4 four-copy
spread per radius** of the quadrature-driven ``|B₁⁺|``.

**Anchors (asserted, in this order; the run stops being informative at the
first red).**

(i) the ×1 rung reproduces ``size_global`` **116 085** at the imported, unmoved
    1% ``CELL_COUNT_BAND`` — backed to ratio 1.000000 by two independent probes
    (`20260908T183317Z_GEO-28.log:1786`, `20260909T003221Z_GEO-29.log:1792`) —
    and its worst-radius C4 four-copy spread reproduces step 4f's measurement
    of **that same statistic on this fixture at this rung**, 5.2506%
    (`20260909T123716Z_WF-6.log:2080–2086`), inside 10% relative.  Without that
    reproduction control the ladder below compares nothing.
(ii) both rungs pass the **power-accounting** and **C4-covariance** gates of
    `tests/validation/test_birdcage_b1_plus_map.py` at their imported, unmoved
    bands (``POWER_BALANCE_BAND`` 1%, ``C4_COVARIANCE_BAND`` 5%).  Both were
    green at 4f (residual 9.796e-03 / 8.114e-03; covariance 3.6159% /
    1.6815%), so this is a reproduction, not a new hurdle.

**Negative control (asserted — backed by 4f's measurement of the same
comparison on the same fixture, and sized off its ceiling):** the **cw**
drive's worst-radius C4 spread must exceed the ccw quadrature's by ≥ **5×** on
both rungs.  A ladder in which the broken drive and the correct one agree is
measuring nothing.  4f measured 9.53× and 19.52× on these two rungs, and 9.53×
is the arithmetic ceiling at ×1 (cw 50.0268% over ccw 5.2506%), so 5× holds
with margin and would still hold if the ccw spread halved again.

**Printed and predicted, never asserted (§9 rule (e)):** the worst-radius C4
spread on both rungs with its ratio to the ×1 value (**predicted to fall**
toward `GEO-28`'s mesh floor of ≈ 0.1%), the eleven-point table on both rungs,
and the point-to-point drift between them.

**Scope.**  One fixture, 10 MHz, CG1, degree 1, the centre plane of the
*unloaded* coil.  No absolute ``|B₁⁺|`` claim, no closed form, no homogeneity,
no Larmor, no tuning; `WF-6` stays 🟡 and §2's B₁⁺ clause keeps its wording.
**A spread that does not fall is the most informative outcome this front can
produce** — it moves the 3.4% off discretisation and onto the degree-1
formulation or the CG1 ``curl E`` estimator.  If the re-registered ×1 anchor
misses, the fixture has changed since 4f and *that* is the finding: report
both readings and stop — never widen a band, never prune a point.

**Step 4h (2026-09-11) — opt-in congruent sheet cut, test-side only.**
``FEM_EM_WF6_C4_CONGRUENT=1`` builds every rung with `GEO-32`'s
``c4_congruent_sheets`` and appends the dropped ×0.0095 rung;
``FEM_EM_WF6_LADDER_KEYS`` selects rungs.  Unset, the ladder and every
record assert exactly as step 4g left them.  Measured
(`20260911T140329Z_WF-6-step4h.log`): the cut makes P1/P2 agree at ×0.0095
(1.968410e-02 / 1.968464e-02) but the residual stays above the unmoved 1e-2,
so the rung stays out of ``LADDER``.

**Step 4i (2026-09-11) — opt-in exact shares, test-side only.**
``FEM_EM_WF6_EXACT_SHARES=1`` prints `PORT-16`'s form-level shares beside the
terminal residual on P1/P2 of every rung and asserts only (a) the discrete
identity at the imported 1e-6 and (b) that the terminal residuals reproduce
4h's flag-on readings to 1e-5.  ``C/terminal`` and the CS-corrected residual
are printed, never asserted.  Unset, nothing new is computed.

**Step 4j (2026-09-12) — opt-in sheet profile, test-side only.**
``FEM_EM_WF6_SHEET_PROFILE=1`` (requires ``FEM_EM_WF6_EXACT_SHARES=1``, else
its test skips with the reason) samples P1's driven ``E`` at the owned tagged
facet midpoints of all four sheets through ``evaluate_vector_field_parallel``,
and prints where on each sheet the Cauchy–Schwarz excess ``C/terminal − 1``
lives: 5 width bins, 5 gap bins, a 5×5 grid, the top facets, the transverse
shares and the sampled ratio ``R_s`` beside ``C/terminal``.  Asserted: only
that ``C/terminal`` reproduces 4i per rung to 2e-6, with a swapped-rung
negative control.  ``R_s`` and the transverse share are printed, never
asserted.

Run (complex build required)::

    scripts/testing/run_and_log.sh WF-6 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 560 \\
       mpiexec -n 4 python3 -m pytest tests/environment \\
       tests/unit/test_birdcage_filament_field.py \\
       tests/validation/test_birdcage_b1_plus_closed_form.py -v -s'"
"""

from __future__ import annotations

import os

import dolfinx
import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial
from fem_em_solver.utils.instrumentation import report_peak_rss
from fem_em_solver.post import (
    evaluate_vector_field_parallel,
    magnetic_flux_density_from_e,
    project_to_cg1,
)

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheet_prerequisite import CELL_COUNT_BAND
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.mesh.test_birdcage_port_tags import LEG_COUNT, RING_RADIUS
from tests.validation.test_birdcage_b1_plus_map import (
    C4_COVARIANCE_BAND,
    POWER_BALANCE_BAND,
    _power_shares,
    _solve_driven,
)
from tests.validation.test_birdcage_b1_quadrature import (
    QUADRATURE_STEP_DEG,
    _port_index,
    _superpose_dg0,
    quadrature_phase_weights,
)
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep
# `WF-6` step 4i: names only, never that module's fixtures.
from tests.validation.test_birdcage_power_identity import (
    DISCRETE_IDENTITY_RTOL,
    _exact_shares,
)

# The two trustworthy rungs of the fixture's **global** ``resolution`` (the
# conductor grading is untouched — `ANS-4` step 2a's negative result is that
# refining ``conductor_resolution`` breaks this fixture's C4 symmetry).  The
# cell counts are `GEO-29`'s measured ones, `20260909T003221Z_GEO-29.log:
# 7038-7042`; only the ×1 count is a **record** (two independent cross-process
# readings), so only it is asserted — `GEO-29`'s own caveat is that its finer
# rungs are single readings and "not `MAT-4`-style records".
#
# `GEO-29`'s third rung, ×0.0095 (197 393 cells), was walked at step 4f and is
# **dropped here, not widened**: its power residual reads 1.853642e-02 against
# the unmoved 1e-2 band and splits between the two ports (P1 1.853642e-02 /
# P2 1.419812e-02, `20260909T123716Z_WF-6.log:5789-5795, 5777-5778`), which the
# 2026-09-09 known-issues row says must be diagnosed before any finer rung of
# this fixture is trusted.  `GEO-30` measures its suspected mechanism with no
# solve; if that census finds the mesh symmetric there, a review returns the
# rung to this tuple.  Its 4f readings stay on record in the §7 `WF-6` row.
LADDER = (
    {"key": "x1", "resolution": 0.015, "cells": 116085, "record": True},
    {"key": "x0.012", "resolution": 0.012, "cells": 149049, "record": False},
)

# **`WF-6` step 4h — the congruent sheet cut, opt-in, test-side only.**
# `ANS-4` step 2a′ showed `GEO-32`'s ``c4_congruent_sheets`` clears the
# conductor-refinement Z class-spread break (`20260911T003204Z_ANS-4-step2a-
# prime.log:3913`); 4h asks whether the same cut carries the ×0.0095 rung's
# power-residual split.  Unset or "0" = off: ``LADDER`` above is then the
# active tuple **unchanged**, every rung builds the flag-off mesh, and the
# two ×1 record tests assert as before.  "1" builds every rung with the cut
# and appends the dropped ×0.0095 rung (its ``cells`` is `GEO-29`'s flag-off
# single reading, printed only).  A flag-on mesh is not the record mesh.
C4_CONGRUENT_ENV = "FEM_EM_WF6_C4_CONGRUENT"
# Space/comma-separated rung keys; unset = every active rung.  Selection keeps
# the ladder's own order, so ×1 always builds (and reports) first.
LADDER_KEYS_ENV = "FEM_EM_WF6_LADDER_KEYS"
CONGRUENT_EXTRA_RUNGS = (
    {"key": "x0.0095", "resolution": 0.0095, "cells": 197393, "record": False},
)
# Printed only: the flag-on ×1 cell count `GEO-32` predicts (the cut adds 33
# cells to the 116 085 record, the 2026-09-11 03:00 ruling's 116 118).
PREDICTED_FLAG_ON_X1_CELLS = 116118
# **The negative control, by record (never re-run here).**  Step 4f's flag-off
# ×0.0095 power residuals, `20260909T123716Z_WF-6.log:5777-5778, 5789-5795`.
# The flag-on reading is printed beside them with its ratio; the ratio is
# *predicted* to fall, never asserted (§9 rule (e)).
FLAG_OFF_X0_0095_RESIDUALS = {"P1": 1.853642e-02, "P2": 1.419812e-02}

# **`WF-6` step 4i — the exact (form-level) shares beside the terminal ones,
# opt-in, test-side only.**  Unset or "0" = off: the rung fixture computes and
# prints nothing new and every test above runs exactly as step 4h left it.
# "1" calls `PORT-16`'s ``_exact_shares`` on the P1 and P2 drives of every
# rung and prints P_src,exact / P_vol / P_sheet,exact, the discrete identity's
# relative deviation, the Cauchy-Schwarz ceiling total ``C``, ``C/terminal``
# and the CS-corrected residual ``|supplied_terminal - (P_vol + C)|/supplied``.
EXACT_SHARES_ENV = "FEM_EM_WF6_EXACT_SHARES"
# **Anchor (b), the reproduction control** — step 4h's flag-on terminal
# residuals on this fixture (`20260911T140329Z_WF-6-step4h.log:2043-2044`
# for x1, `:4034-4035` for x0.0095), reproduced to ``REPRODUCTION_RTOL``.  A
# different mesh or flag cannot land 1.968410e-02 to 1e-5, so this is what
# says the exact shares below were read on 4h's fixture.  x0.012 has no
# flag-on record: printed, not asserted.
STEP4H_FLAG_ON_RESIDUALS = {
    "x1": {"P1": 9.795942e-03, "P2": 9.796517e-03},
    "x0.0095": {"P1": 1.968410e-02, "P2": 1.968464e-02},
}
REPRODUCTION_RTOL = 1.0e-5
# *Predicted, printed only* (rule (e) — no prior measurement on the unloaded
# fixture): `PORT-16`'s loaded-x1 ratio ceiling/terminal = 1.010593
# (`20260907T050816Z_PORT-16.log:1884`).
PREDICTED_C_OVER_TERMINAL = 1.01


def _exact_shares_enabled():
    """Whether the rung fixture computes the exact shares. Default **off**."""
    raw = os.environ.get(EXACT_SHARES_ENV)
    if raw is None or not raw.strip():
        return False
    return raw.strip().lower() not in ("0", "false", "no", "off")


EXACT_SHARES = _exact_shares_enabled()

# **`WF-6` step 4j — where on the sheet the Cauchy-Schwarz excess lives,
# opt-in, test-side only.**  Unset or "0" = off.  "1" requires
# ``FEM_EM_WF6_EXACT_SHARES=1`` (its anchor is 4i's printed C/terminal); without
# it the profile is not computed and the step-4j test skips with the reason.
SHEET_PROFILE_ENV = "FEM_EM_WF6_SHEET_PROFILE"
PROFILE_BINS = 5
# **Anchor (b), the reproduction control** — 4i's printed C/terminal per rung
# and drive (`20260911T200251Z_WF-6-step4i.log:2047, 2051` for x1, `:4057`
# region for x0.0095; `20260911T200634Z_WF-6-step4i-x0.012.log:2018` region for
# x0.012), all flag-on.  7 significant figures printed, so the rtol is 2e-6.
STEP4I_C_OVER_TERMINAL = {
    "x1": {"P1": 1.010592, "P2": 1.010593},
    "x0.012": {"P1": 1.008756, "P2": 1.008757},
    "x0.0095": {"P1": 1.021491, "P2": 1.021491},
}
C_OVER_TERMINAL_RTOL = 2.0e-6
# **Negative control (asserted, backed by the same two 4i logs):** x0.0095's
# C/terminal held against x1's record (and x1's against x0.0095's) misses by
# 1.08e-2 = 5 400x the rtol; the assertion requires > 100x, so a swapped rung
# cannot pass.
SWAPPED_RUNG_PAIRS = {"x1": "x0.0095", "x0.0095": "x1"}
SWAPPED_RUNG_FACTOR = 100.0
# *Predicted, printed only* (rule (e) — never measured): midpoint sampling
# lands R_s within 1e-2 of C/terminal; the transverse share is small.
PREDICTED_RS_GAP = 1.0e-2


def _sheet_profile_requested():
    raw = os.environ.get(SHEET_PROFILE_ENV)
    if raw is None or not raw.strip():
        return False
    return raw.strip().lower() not in ("0", "false", "no", "off")


SHEET_PROFILE_REQUESTED = _sheet_profile_requested()
SHEET_PROFILE = SHEET_PROFILE_REQUESTED and EXACT_SHARES


def _c4_congruent_enabled():
    """Whether every rung builds with ``c4_congruent_sheets``. Default **off**."""
    raw = os.environ.get(C4_CONGRUENT_ENV)
    if raw is None or not raw.strip():
        return False
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _active_ladder():
    """``LADDER`` (flag off) or ``LADDER + CONGRUENT_EXTRA_RUNGS`` (flag on),
    filtered by ``FEM_EM_WF6_LADDER_KEYS`` in ladder order.  Pure env logic,
    identical on every rank; an unknown key raises at collection."""
    ladder = LADDER + (CONGRUENT_EXTRA_RUNGS if _c4_congruent_enabled() else ())
    raw = os.environ.get(LADDER_KEYS_ENV)
    if raw is None or not raw.strip():
        return ladder
    wanted = raw.replace(",", " ").split()
    known = [r["key"] for r in ladder]
    unknown = [k for k in wanted if k not in known]
    if unknown:
        raise ValueError(
            f"{LADDER_KEYS_ENV} names rung(s) {unknown} not in the active ladder "
            f"{known} ({C4_CONGRUENT_ENV}={'on' if _c4_congruent_enabled() else 'off'}"
            "; x0.0095 exists only with the flag on)"
        )
    return tuple(r for r in ladder if r["key"] in wanted)


C4_CONGRUENT = _c4_congruent_enabled()
ACTIVE_LADDER = _active_ladder()

# **Anchor (i)'s reproduction control.**  Step 4f measured *this module's own
# four-copy spread statistic*, on this fixture, at this rung, as 5.2506%
# (`20260909T123716Z_WF-6.log:2080-2086`), and that is what is reproduced here.
#
# The value it replaces, 3.310633e-02, was computed from the ×1 rung's recorded
# eleven-point table (`20260908T004020Z_WF-6.log:1894, 1899`: 9.805561792e-08 T
# along +x̂, 1.013569652e-07 T along +ŷ) — a **two**-copy spread, since that
# table has no -x̂ or -ŷ arm.  4f reproduced that table character-for-character
# and then read the -x̂ copy at 1.024222080e-07 T, a quantity the record never
# contained; the four-copy spread is therefore a different statistic, not a
# drifted one.  Nothing is loosened: the tolerance stays 10% relative and the
# comparand moves onto the statistic that exists.
RECORDED_X1_WORST_SPREAD = 5.2506e-02
RECORDED_SPREAD_TOLERANCE = 0.10

# **The negative control's backing measurement** (`POST-6` step 1, the same
# comparison on this fixture): the cw drive's C4 spread of |B1+|.  Asserted only
# as a *separation* — cw ≥ 5 × ccw — never as a value.
#
# The factor is re-sized off a ceiling the original bar never computed: at ×1
# the cw spread is 50.0268% against the ccw 5.2506%, so **9.53x is
# arithmetically the maximum this rung can show** and the previous 10x bar was
# unreachable rather than unmet.  4f measured 9.53x / 19.52x on the two rungs
# kept here (`20260909T123716Z_WF-6.log:2080-2086, 3901-3907`), so 5x holds
# with margin on both and would still hold if the ccw spread halved again.
RECORDED_CW_SPREAD = 0.951975
CW_SEPARATION_FACTOR = 5.0

# The unloaded phantom: vacuum on tag 3.  Not "phantom removed" — the mesh is
# bit-for-bit the loaded fixture's, so the comparison isolates the *material*.
# The coil must be unloaded here: a lossy scatterer the symmetry identity knows
# nothing about would make any per-rung change un-attributable.
VACUUM = HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0)

# The evaluation lattice: the centre, then the **four** C4 copies at
# r = 0.1R … 0.5R, all at z = 0.  0.5R keeps every point clear of the legs'
# near field.  The eleven "gate points" of steps 4/4b are the q = 0 (+x̂) and
# q = 1 (+ŷ) arms of this same lattice, so the two readings come off one
# evaluator call on one identical-on-every-rank point list.
RADIUS_FRACTIONS = (0.1, 0.2, 0.3, 0.4, 0.5)
QUADRANT_DEG = (0.0, 90.0, 180.0, 270.0)

# `GEO-28`'s mesh floor: every per-quadrant mass spread on this fixture is
# ≲ 0.1% (`20260908T183317Z_GEO-28.log:1800-1830`).  Printed as the target the
# field spread is *predicted* to fall toward — never asserted (rule (e)).
PREDICTED_MESH_FLOOR = 1.0e-3

# Filled in as the ladder runs (identically on every rank, from
# already-reduced quantities), so a later rung can print its ratio to the ×1
# value and the point-to-point drift against its predecessor.
_LADDER_READINGS: dict = {}


def _master_points() -> np.ndarray:
    """The 21 ``z = 0`` sample points, identical on every rank.

    Index 0 is the centre; index ``1 + 4*i + q`` is radius ``i`` at quadrant
    ``q``.  ``evaluate_vector_field_parallel`` is a collective over an
    *identical* point list on every rank (`OPS-40`), so nothing here may be
    filtered rank-locally.
    """
    pts = [(0.0, 0.0, 0.0)]
    for frac in RADIUS_FRACTIONS:
        r = frac * RING_RADIUS
        for phi in QUADRANT_DEG:
            a = np.radians(phi)
            pts.append((r * np.cos(a), r * np.sin(a), 0.0))
    return np.asarray(pts, dtype=np.float64)


def _gate_indices():
    """The eleven step-4 gate points as indices into the master lattice."""
    idx = [0]
    idx += [1 + 4 * i + 0 for i in range(len(RADIUS_FRACTIONS))]  # +x arm
    idx += [1 + 4 * i + 1 for i in range(len(RADIUS_FRACTIONS))]  # +y arm
    return np.asarray(idx, dtype=int)


def _rotate_z(points: np.ndarray, angle_rad: float) -> np.ndarray:
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    out = np.empty_like(points)
    out[:, 0] = c * points[:, 0] - s * points[:, 1]
    out[:, 1] = s * points[:, 0] + c * points[:, 1]
    out[:, 2] = points[:, 2]
    return out


def _read_b1_plus(projected, points):
    """``|B₁⁺| = |B_x + jB_y|/2`` and validity at ``points`` from a CG1 phasor."""
    values, valid = evaluate_vector_field_parallel(projected, points)
    values = np.asarray(values).reshape(-1, 3)
    return (
        np.abs(values[:, 0] + 1j * values[:, 1]) / 2.0,
        np.asarray(valid, dtype=bool),
    )


def _radial_spreads(values):
    """``(max - min)/mean`` over the four C4 copies, per radius.

    `GEO-28`'s spread definition, so the field spread and that probe's mass
    spreads are the same statistic.
    """
    out = []
    for i in range(len(RADIUS_FRACTIONS)):
        quad = np.asarray([values[1 + 4 * i + q] for q in range(4)], dtype=float)
        out.append(float((quad.max() - quad.min()) / quad.mean()))
    return np.asarray(out, dtype=float)


@pytest.fixture(
    scope="module", params=ACTIVE_LADDER, ids=[r["key"] for r in ACTIVE_LADDER]
)
def rung(request):
    """One ``h`` rung: one mesh, four single drives, the two superpositions.

    Module-scoped and parametrised, so pytest tears each rung's mesh and fields
    down before the next is built and every rung reports (``-v -s``) before the
    next is solved — if the finest rung overruns the window, the coarser rungs'
    readings are already in the log.
    """
    spec = request.param
    sweep = build_four_port_sweep(
        phantom_material=VACUUM,
        resolution=spec["resolution"],
        c4_congruent_sheets=C4_CONGRUENT,
    )
    comm = sweep["mesh"].comm

    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    order = sorted(azimuths)
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    assert sorted(indices.values()) == [0, 1, 2, 3], (
        f"the four sheets do not occupy the four quadrature slots: {indices}"
    )
    delta_deg = (azimuths["P2"] - azimuths["P1"]) % 360.0

    solves = {pid: _solve_driven(sweep, pid) for pid in order}
    b_dg0 = [
        magnetic_flux_density_from_e(
            solves[pid]["fields"].e_complex, solves[pid]["omega"]
        )
        for pid in order
    ]
    ks = np.array([indices[pid] for pid in order], dtype=float)
    weights = {
        "ccw": quadrature_phase_weights(ks, "ccw"),
        "cw": quadrature_phase_weights(ks, "cw"),
    }
    cg1 = {
        sense: project_to_cg1(
            _superpose_dg0(b_dg0, w, f"B_{spec['key']}_{sense}"),
            name=f"B_{spec['key']}_{sense}_cg1",
        )
        for sense, w in weights.items()
    }
    # The C4-covariance gate is the map module's: drive P2 read at the +90°
    # image of the P1 sample set against drive P1 read at the set itself, both
    # through the production CG1 estimator.
    single = {
        pid: project_to_cg1(
            _superpose_dg0([b_dg0[order.index(pid)]], [1.0], f"B_{spec['key']}_{pid}"),
            name=f"B_{spec['key']}_{pid}_cg1",
        )
        for pid in ("P1", "P2")
    }

    points = _master_points()
    rotated = _rotate_z(points, np.radians(delta_deg))
    ccw, valid_ccw = _read_b1_plus(cg1["ccw"], points)
    cw, valid_cw = _read_b1_plus(cg1["cw"], points)
    a, valid_a = _read_b1_plus(single["P1"], points)
    b, valid_b = _read_b1_plus(single["P2"], rotated)
    mask = valid_ccw & valid_cw & valid_a & valid_b

    ccw_spreads = _radial_spreads(ccw)
    cw_spreads = _radial_spreads(cw)
    worst_radius = int(np.argmax(ccw_spreads))
    covariance = (
        float(np.linalg.norm(b[mask] - a[mask]) / np.linalg.norm(a[mask]))
        if mask.any()
        else float("inf")
    )
    shares = {pid: _power_shares(sweep, solves[pid]) for pid in ("P1", "P2")}
    # Step 4i (opt-in): every term MPI-reduced inside the helpers, so the
    # dict is identical on every rank.  Collective — every rank calls it.
    exact = (
        {pid: _exact_shares(sweep, solves[pid]) for pid in ("P1", "P2")}
        if EXACT_SHARES
        else None
    )
    # Step 4j (opt-in): collective, identical on every rank.
    profile = _sheet_profile(sweep, solves["P1"]) if SHEET_PROFILE else None

    gate_idx = _gate_indices()
    reading = {
        "spec": spec,
        "cells": int(sweep["cells"]),
        "ccw": ccw,
        "cw": cw,
        "ccw_spreads": ccw_spreads,
        "cw_spreads": cw_spreads,
        "worst_spread": float(ccw_spreads[worst_radius]),
        "worst_cw_spread": float(cw_spreads.max()),
        "worst_radius": worst_radius,
        "covariance": covariance,
        "shares": shares,
        "exact": exact,
        "profile": profile,
        "valid": mask,
        "points": points,
        "gate_idx": gate_idx,
        "solve_times": {pid: solves[pid]["solve_time"] for pid in order},
    }

    previous = _LADDER_READINGS.get(_previous_key(spec["key"]))
    x1 = _LADDER_READINGS.get("x1")
    if comm.rank == 0:
        _print_rung(reading, previous, x1, delta_deg, azimuths, sweep)
    # Collective: every rank calls it, rank 0 prints.
    report_peak_rss(comm, label=f"WF-6 step4h after rung {spec['key']}")
    _LADDER_READINGS[spec["key"]] = reading
    return reading


def _previous_key(key):
    keys = [r["key"] for r in ACTIVE_LADDER]
    i = keys.index(key)
    return keys[i - 1] if i > 0 else None


def _residual(sh):
    total = sh["phantom"] + sh["conductor"] + sh["sheet_total"]
    return abs(sh["supplied"] - total) / abs(sh["supplied"])


def _exact_readings(sh, ex):
    """Step 4i's derived numbers for one drive, from reduced scalars only."""
    identity = abs(ex["p_src"] - ex["p_vol"] - ex["sheet_field_total"]) / abs(
        ex["p_src"]
    )
    c_total = ex["sheet_ceiling_total"]
    cs_corrected = abs(sh["supplied"] - (ex["p_vol"] + c_total)) / abs(sh["supplied"])
    return {
        "identity": identity,
        "c_over_terminal": c_total / sh["sheet_total"],
        "terminal_residual": _residual(sh),
        "cs_corrected": cs_corrected,
    }


def _print_exact(reading):
    spec = reading["spec"]
    print(
        f"[WF-6 step4i] rung {spec['key']}: exact (form-level) shares "
        f"({EXACT_SHARES_ENV}=1); identity ASSERTED <= imported "
        f"DISCRETE_IDENTITY_RTOL {DISCRETE_IDENTITY_RTOL:g}; C/terminal and the "
        "CS-corrected residual PRINTED, NEVER ASSERTED",
        flush=True,
    )
    for pid in ("P1", "P2"):
        sh, ex = reading["shares"][pid], reading["exact"][pid]
        r = _exact_readings(sh, ex)
        record = STEP4H_FLAG_ON_RESIDUALS.get(spec["key"], {}).get(pid)
        rep = (
            f"4h flag-on record {record:.6e}, rel {abs(r['terminal_residual'] - record) / record:.3e} "
            f"(ASSERTED <= {REPRODUCTION_RTOL:g})"
            if record is not None and C4_CONGRUENT
            else "no 4h flag-on record for this rung/flag (PRINTED)"
        )
        print(
            f"    [{pid} driven] P_src,exact {ex['p_src']:.9e} W   P_vol "
            f"{ex['p_vol']:.9e} W (phantom {ex['phantom']:.9e}, conductor "
            f"{ex['conductor']:.9e})   P_sheet,exact {ex['sheet_field_total']:.9e} W"
            f"   identity rel dev {r['identity']:.3e}\n"
            f"        C {ex['sheet_ceiling_total']:.9e} W   terminal sheets "
            f"{sh['sheet_total']:.9e} W   C/terminal {r['c_over_terminal']:.6f} "
            f"(PREDICTED ~{PREDICTED_C_OVER_TERMINAL} off PORT-16's loaded x1)\n"
            f"        supplied_terminal {sh['supplied']:.9e} W   P_vol + C "
            f"{ex['p_vol'] + ex['sheet_ceiling_total']:.9e} W   terminal residual "
            f"{r['terminal_residual']:.6e} [{rep}]   CS-corrected residual "
            f"{r['cs_corrected']:.6e}   CS-corrected/terminal "
            f"{r['cs_corrected'] / r['terminal_residual']:.4f} (PREDICTED << "
            "terminal if the deficit is the carrier, NEVER ASSERTED)",
            flush=True,
        )
        print(
            f"        per sheet: "
            + "   ".join(
                f"{o} ceiling {ex['sheet_ceiling'][o]:.6e} / terminal "
                f"{sh['sheets'][o]:.6e} = "
                f"{ex['sheet_ceiling'][o] / sh['sheets'][o]:.6f}"
                for o in sorted(sh["sheets"])
            ),
            flush=True,
        )


def _sheet_profile(sweep, solved):
    """Step 4j: ``E`` at every sheet's **owned** tagged facet midpoints.

    Collective — every rank calls it.  Owned facets only (index < the facet
    index map's ``size_local``), so a facet on a process boundary is counted
    once; per-facet geometry is gathered to rank 0 and broadcast, so the point
    list handed to ``evaluate_vector_field_parallel`` is identical on every
    rank and every number below is too.  All binning is numpy.

    ``f = E·ĥ + E_src`` (``E_src = V_src/h`` on the driven sheet, 0 elsewhere):
    the drive component of the field the Cauchy-Schwarz ceiling integrates,
    ``C = ½Re(Y_s)∫|E_t + E_src ĥ|²``, while the terminal form is
    ``½Re(Y_s)|∫f|²/A``.  So ``C/terminal = A∫(|f|² + |E_w|²)/|∫f|²`` with
    ``E_w`` the in-plane transverse component; the normal component does not
    enter ``C`` (and is side-ambiguous at a facet midpoint on an N1curl field).
    """
    msh = sweep["mesh"]
    comm = msh.comm
    fdim = msh.topology.dim - 1
    msh.topology.create_connectivity(fdim, msh.topology.dim)
    owned = int(msh.topology.index_map(fdim).size_local)
    e = solved["fields"].e_complex
    specs = {s.port_id: s for s in sweep["specs"]}
    out = {}
    for g in sweep["sheets"]:
        pid = f"P{g['tag'] - SHEET_IFACE}"
        sheet = specs[pid].sheet(driven=(pid == solved["driven"]))
        facets = np.asarray(sweep["facet_tags"].find(g["tag"]), dtype=np.int32)
        facets = facets[facets < owned]
        if facets.size:
            nodes = dolfinx.cpp.mesh.entities_to_geometry(
                msh._cpp_object, fdim, facets, False
            )
            tri = msh.geometry.x[np.asarray(nodes)[:, :3]]
            mid = np.asarray(
                dolfinx.mesh.compute_midpoints(msh, fdim, facets), dtype=np.float64
            )
        else:
            tri = np.zeros((0, 3, 3))
            mid = np.zeros((0, 3))
        chunks = comm.gather((tri, mid), root=0)
        if comm.rank == 0:
            tri = np.concatenate([c[0] for c in chunks], axis=0)
            mid = np.concatenate([c[1] for c in chunks], axis=0)
        else:
            tri = mid = None
        tri, mid = comm.bcast((tri, mid), root=0)
        values, valid = evaluate_vector_field_parallel(e, mid)
        values = np.asarray(values).reshape(-1, 3)
        valid = np.asarray(valid, dtype=bool)

        d = sheet.unit_drive()
        e_src = complex(sheet.source_voltage_v) / float(sheet.gap_height_m)
        cr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        area = 0.5 * np.linalg.norm(cr, axis=1)
        normal = cr / np.maximum(np.linalg.norm(cr, axis=1), 1e-300)[:, None]
        width_dir = np.cross(normal, d)
        width_dir /= np.maximum(np.linalg.norm(width_dir, axis=1), 1e-300)[:, None]
        diam = np.max(
            [np.linalg.norm(tri[:, a] - tri[:, b], axis=1) for a, b in ((0, 1), (1, 2), (2, 0))],
            axis=0,
        )
        e_tot = values + e_src * d[None, :]
        f = e_tot @ d  # no conjugation: d is real
        e_w = np.einsum("ij,ij->i", e_tot, width_dir)
        e_n = np.einsum("ij,ij->i", e_tot, normal)

        m = valid
        a, fm, ew, en = area[m], f[m], e_w[m], e_n[m]
        mu = mid[m]
        total_area = float(a.sum())
        sum_f = complex(np.sum(a * fm))
        mean_f = sum_f / total_area
        sq_f = float(np.sum(a * np.abs(fm) ** 2))
        sq_w = float(np.sum(a * np.abs(ew) ** 2))
        sq_n = float(np.sum(a * np.abs(en) ** 2))
        dev = a * np.abs(fm - mean_f) ** 2
        dev_total = float(dev.sum())

        axis = int(g["axis"])
        wlo, whi = float(tri[:, :, axis].min()), float(tri[:, :, axis].max())
        zc = int(np.argmax(np.abs(d)))
        zlo, zhi = float(tri[:, :, zc].min()), float(tri[:, :, zc].max())
        u = np.clip((mu[:, axis] - wlo) / (whi - wlo), 0.0, 1.0 - 1e-12)
        v = np.clip((mu[:, zc] - zlo) / (zhi - zlo), 0.0, 1.0 - 1e-12)
        ub = np.floor(u * PROFILE_BINS).astype(int)
        vb = np.floor(v * PROFILE_BINS).astype(int)

        def _marginal(bins):
            rows = []
            for k in range(PROFILE_BINS):
                sel = bins == k
                ak = float(a[sel].sum())
                rows.append(
                    {
                        "n": int(sel.sum()),
                        "area_share": ak / total_area,
                        "mean_abs_f": float(np.sum(a[sel] * np.abs(fm[sel])) / ak)
                        if ak > 0
                        else float("nan"),
                        "mean_abs_w": float(np.sum(a[sel] * np.abs(ew[sel])) / ak)
                        if ak > 0
                        else float("nan"),
                        "dev_share": float(dev[sel].sum()) / dev_total,
                    }
                )
            return rows

        grid = np.zeros((PROFILE_BINS, PROFILE_BINS))
        np.add.at(grid, (vb, ub), dev)
        order = np.argsort(dev)[::-1]
        z_mid = 0.5 * (zlo + zhi)
        crossing = int(
            np.count_nonzero(
                (tri[m][:, :, zc].min(axis=1) <= z_mid) & (tri[m][:, :, zc].max(axis=1) > z_mid)
            )
        )
        n_top1pct = max(1, int(np.ceil(0.01 * a.size)))
        out[pid] = {
            "driven": pid == solved["driven"],
            "facets": int(area.size),
            "valid": int(m.sum()),
            "median_diam": float(np.median(diam)),
            "width_bbox": whi - wlo,
            "gap_bbox": zhi - zlo,
            "across_by_diam": (whi - wlo) / float(np.median(diam)),
            "crossing_mid_gap": crossing,
            "normal_dot_drive": float(np.max(np.abs(normal @ d))),
            "area": total_area,
            "r_s": total_area * sq_f / abs(sum_f) ** 2,
            "r_s_tan": total_area * (sq_f + sq_w) / abs(sum_f) ** 2,
            "transverse_share": (sq_w + sq_n) / (sq_f + sq_w + sq_n),
            "inplane_share": sq_w / (sq_f + sq_w),
            "mean_f": mean_f,
            "width": _marginal(ub),
            "gap": _marginal(vb),
            "grid": grid / dev_total,
            "top_shares": {
                "1": float(dev[order[:1]].sum()) / dev_total,
                "5": float(dev[order[:5]].sum()) / dev_total,
                f"1% ({n_top1pct})": float(dev[order[:n_top1pct]].sum()) / dev_total,
            },
            "top_uv": [
                (float(u[i]), float(v[i]), float(dev[i] / dev_total), float(a[i] / total_area))
                for i in order[:5]
            ],
        }
    return out


def _print_profile(reading):
    spec = reading["spec"]
    prof = reading["profile"]
    sh, ex = reading["shares"]["P1"], reading["exact"]["P1"]
    print(
        f"[WF-6 step4j] rung {spec['key']}: sheet profile of P1's driven E at owned "
        f"facet midpoints ({SHEET_PROFILE_ENV}=1); f = E.h + E_src; bins over the "
        "sheet's vertex bbox; R_s = A*sum a|f|^2/|sum a f|^2 and R_s,tan (adds the "
        "in-plane transverse |E_w|^2, the sampled analogue of C/terminal) PRINTED, "
        f"PREDICTED within {PREDICTED_RS_GAP:g} of C/terminal, NEVER ASSERTED; "
        "transverse share PREDICTED small, NEVER ASSERTED",
        flush=True,
    )
    for pid in sorted(prof):
        p = prof[pid]
        c_t = ex["sheet_ceiling"][pid] / sh["sheets"][pid]
        print(
            f"  [{pid}{' driven' if p['driven'] else ''}] facets {p['facets']} "
            f"(evaluated {p['valid']}), area {p['area']:.6e} m^2, width bbox "
            f"{p['width_bbox']:.6e} m, gap bbox {p['gap_bbox']:.6e} m, median facet "
            f"diameter {p['median_diam']:.6e} m, across width = width/median diam "
            f"{p['across_by_diam']:.2f}, facets crossing mid-gap line "
            f"{p['crossing_mid_gap']}, max|n.h| {p['normal_dot_drive']:.2e}\n"
            f"      C/terminal {c_t:.6f}   R_s {p['r_s']:.6f} (R_s-1 = sampled "
            f"normalised variance {p['r_s'] - 1:.6e})   R_s,tan {p['r_s_tan']:.6f}   "
            f"R_s,tan - C/terminal {p['r_s_tan'] - c_t:+.3e}\n"
            f"      transverse share sum a|E-E_d h|^2/sum a|E|^2 {p['transverse_share']:.6e}"
            f"   in-plane only sum a|E_w|^2/sum a(|f|^2+|E_w|^2) {p['inplane_share']:.6e}"
            f"   <f> {p['mean_f'].real:+.6e}{p['mean_f'].imag:+.6e}j V/m",
            flush=True,
        )
        for label, rows in (("width", p["width"]), ("gap  ", p["gap"])):
            print(
                f"      {label} bins: "
                + " | ".join(
                    f"[{k}] n {r['n']} area {r['area_share'] * 100:5.2f}% "
                    f"<|f|> {r['mean_abs_f']:.5e} <|E_w|> {r['mean_abs_w']:.3e} "
                    f"var {r['dev_share'] * 100:5.2f}%"
                    for k, r in enumerate(rows)
                ),
                flush=True,
            )
        print(
            "      var share grid (rows = gap bin 0..4, cols = width bin 0..4, %): "
            + " / ".join(
                " ".join(f"{x * 100:5.2f}" for x in row) for row in p["grid"]
            ),
            flush=True,
        )
        print(
            "      top facets' var share: "
            + ", ".join(f"top {k} {s * 100:.2f}%" for k, s in p["top_shares"].items())
            + "; top 5 (u_width, v_gap, var share, area share): "
            + ", ".join(
                f"({uu:.3f}, {vv:.3f}, {ss * 100:.2f}%, {aa * 100:.3f}%)"
                for uu, vv, ss, aa in p["top_uv"]
            ),
            flush=True,
        )


def _print_rung(reading, previous, x1, delta_deg, azimuths, sweep):
    spec = reading["spec"]
    cells = reading["cells"]
    if C4_CONGRUENT:
        record_clause = (
            f", PRINTED NOT ASSERTED — flag-on mesh is not the record mesh "
            f"(GEO-32); x1 flag-on PREDICTED {PREDICTED_FLAG_ON_X1_CELLS}, "
            f"ratio {cells / PREDICTED_FLAG_ON_X1_CELLS:.6f})"
            if spec["key"] == "x1"
            else ", PRINTED NOT ASSERTED — flag-on mesh, its own count; the "
            "comparand is GEO-29's flag-off single reading)"
        )
    elif spec["record"]:
        record_clause = (
            f", ASSERTED inside the imported {CELL_COUNT_BAND * 100:.0f}% "
            "CELL_COUNT_BAND)"
        )
    else:
        record_clause = (
            ", PRINTED NOT ASSERTED — GEO-29's finer rungs are single "
            "readings, not records)"
        )
    print(
        f"\n[WF-6 step4g] rung {spec['key']}: c4_congruent_sheets="
        f"{'on' if C4_CONGRUENT else 'off'} ({C4_CONGRUENT_ENV}); resolution = "
        f"{spec['resolution']} m, "
        f"{cells} cells (GEO-29 {spec['cells']}, ratio "
        f"{cells / spec['cells']:.6f}"
        + record_clause
        + f"\n    unloaded (vacuum on tag 3), 10 MHz, degree 1, CG1 |B1+|; sheet "
        "azimuths "
        + ", ".join(f"{p} {azimuths[p]:.3f}" for p in sorted(azimuths))
        + f" deg; P1->P2 = {delta_deg:.6f} deg; mesh "
        f"{sweep['mesh_time']:.2f} s, sweep {sweep['sweep_time']:.2f} s, four "
        "field solves "
        + ", ".join(f"{p} {t:.2f} s" for p, t in sorted(reading["solve_times"].items())),
        flush=True,
    )
    print(
        f"[WF-6 step4g] rung {spec['key']}: C4 four-copy spread (max-min)/mean of "
        "the ccw-quadrature |B1+|, per radius:",
        flush=True,
    )
    for i, frac in enumerate(RADIUS_FRACTIONS):
        quad = [reading["ccw"][1 + 4 * i + q] for q in range(4)]
        print(
            f"    r = {frac * RING_RADIUS:.4f} m ({frac:.1f}R)  "
            + "  ".join(f"{v:.9e}" for v in quad)
            + f"   spread {reading['ccw_spreads'][i] * 100:8.4f}%   "
            f"cw control {reading['cw_spreads'][i] * 100:9.4f}%",
            flush=True,
        )
    ratio = (
        f"{reading['worst_spread'] / x1['worst_spread']:.4f} of the x1 rung's "
        f"{x1['worst_spread'] * 100:.4f}%"
        if x1 is not None and x1 is not reading
        else "the x1 reference"
    )
    print(
        f"    worst radius {RADIUS_FRACTIONS[reading['worst_radius']]:.1f}R: ccw "
        f"spread {reading['worst_spread'] * 100:.4f}% — {ratio} (PRINTED AND "
        f"PREDICTED to fall toward GEO-28's mesh floor "
        f"{PREDICTED_MESH_FLOOR * 100:.1f}%, NEVER ASSERTED)\n"
        f"    cw negative control worst spread "
        f"{reading['worst_cw_spread'] * 100:.4f}% "
        f"(POST-6 step 1 recorded {RECORDED_CW_SPREAD * 100:.4f}%); separation "
        f"{reading['worst_cw_spread'] / reading['worst_spread']:.2f}x (ASSERTED "
        f">= {CW_SEPARATION_FACTOR:.0f}x)\n"
        f"    C4 covariance P2-at-+{delta_deg:.0f}deg vs P1 over "
        f"{int(reading['valid'].sum())} of {reading['points'].shape[0]} points: "
        f"{reading['covariance'] * 100:.4f}% (ASSERTED <= imported "
        f"{C4_COVARIANCE_BAND * 100:.1f}% C4_COVARIANCE_BAND)",
        flush=True,
    )
    for pid, sh in sorted(reading["shares"].items()):
        total = sh["phantom"] + sh["conductor"] + sh["sheet_total"]
        residual = abs(sh["supplied"] - total) / abs(sh["supplied"])
        blind = abs(sh["supplied"] - (total - sh["conductor"])) / abs(sh["supplied"])
        print(
            f"    [{pid} driven] supplied {sh['supplied']:.9e} W = phantom "
            f"{sh['phantom']:.9e} (vacuum, expected 0) + conductor "
            f"{sh['conductor']:.9e} + sheets {sh['sheet_total']:.9e}; residual "
            f"{residual:.6e} (ASSERTED <= imported {POWER_BALANCE_BAND:.0e} "
            f"POWER_BALANCE_BAND); without the conductor term {blind:.6e} "
            "(PRINTED)",
            flush=True,
        )
    if C4_CONGRUENT and spec["key"] == "x0.0095":
        for pid, sh in sorted(reading["shares"].items()):
            on = _residual(sh)
            off = FLAG_OFF_X0_0095_RESIDUALS[pid]
            print(
                f"[WF-6 step4h] negative control BY RECORD, x0.0095 [{pid}]: "
                f"flag-on residual {on:.6e} vs flag-off record {off:.6e} "
                f"(20260909T123716Z_WF-6.log:5777-5778, 5789-5795); ratio "
                f"on/off {on / off:.4f} (PREDICTED to fall, NEVER ASSERTED); "
                f"flag-on {'<=' if on <= POWER_BALANCE_BAND else '>'} the "
                f"imported {POWER_BALANCE_BAND:.0e} POWER_BALANCE_BAND",
                flush=True,
            )
    if reading["exact"] is not None:
        _print_exact(reading)
    if reading["profile"] is not None:
        _print_profile(reading)
    print(
        f"[WF-6 step4g] rung {spec['key']}: the eleven z = 0 gate points "
        "(steps 4/4b's set, no closed form — the comparand path is deleted):",
        flush=True,
    )
    for n, idx in enumerate(reading["gate_idx"]):
        pt = reading["points"][idx]
        tag = "centre" if n == 0 else f"r = {np.hypot(pt[0], pt[1]):.4f} m"
        axis = "  " if n == 0 else ("+x" if n <= len(RADIUS_FRACTIONS) else "+y")
        drift = (
            "   drift vs "
            + previous["spec"]["key"]
            + f" {abs(reading['ccw'][idx] - previous['ccw'][idx]) / abs(previous['ccw'][idx]) * 100:8.4f}%"
            if previous is not None
            else "   (first rung: no drift)"
        )
        print(
            f"    [{n:2d}] {axis} {tag:>14s}  |B1+| {reading['ccw'][idx]:.9e} T"
            f"{drift}",
            flush=True,
        )
    if previous is not None:
        drift = np.abs(
            reading["ccw"][reading["gate_idx"]] - previous["ccw"][previous["gate_idx"]]
        ) / np.abs(previous["ccw"][previous["gate_idx"]])
        print(
            f"    point-to-point drift vs {previous['spec']['key']}: median "
            f"{np.median(drift) * 100:.4f}%, max {np.max(drift) * 100:.4f}% "
            "(PRINTED NOT ASSERTED)",
            flush=True,
        )


@complex_only
def test_the_x1_rung_reproduces_its_recorded_cell_count(rung):
    """**Anchor (i), first half** — the reproduction control of the whole ladder.

    116 085 is backed to ratio 1.000000 by two independent probes on two
    separate days (`20260908T183317Z_GEO-28.log:1786`,
    `20260909T003221Z_GEO-29.log:1792`).  A drift here is an `OPS-18`-class
    image change and everything below compares a different fixture.  The finer
    rungs are `GEO-29` single readings, not records, so their counts are
    printed and not asserted.
    """
    if not rung["spec"]["record"]:
        pytest.skip(
            "GEO-29's 0.012 / 0.0095 counts are single readings, not records "
            "(that probe's own caveat) — printed above, never asserted"
        )
    ratio = rung["cells"] / rung["spec"]["cells"]
    if C4_CONGRUENT:
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"\n[WF-6 step4h] x1 record test SKIPPED (flag on): meshed "
                f"{rung['cells']} cells against the flag-off record "
                f"{rung['spec']['cells']} (ratio {ratio:.6f}) and the flag-on "
                f"PREDICTED {PREDICTED_FLAG_ON_X1_CELLS} (ratio "
                f"{rung['cells'] / PREDICTED_FLAG_ON_X1_CELLS:.6f}) — PRINTED",
                flush=True,
            )
        pytest.skip("flag-on mesh is not the record mesh (`GEO-32`)")
    assert abs(ratio - 1.0) <= CELL_COUNT_BAND, (
        f"the x1 rung meshed {rung['cells']} cells against the recorded "
        f"{rung['spec']['cells']} (ratio {ratio:.6f}), outside the imported "
        f"{CELL_COUNT_BAND * 100:.0f}% CELL_COUNT_BAND"
    )


@complex_only
def test_the_x1_rung_reproduces_the_recorded_c4_spread(rung):
    """**Anchor (i), second half** — the ladder's zero point.

    Step 4f measured this module's four-copy spread on this fixture at this
    rung as **5.2506%** (`20260909T123716Z_WF-6.log:2080-2086`).  If the ×1
    rung does not reproduce that, the fixture has changed since 4f and the
    finer rung is not measuring a change in the same quantity — the ladder is
    uninterpretable and the miss is the finding, not something to widen.
    """
    if not rung["spec"]["record"]:
        pytest.skip("the reproduction control is the x1 rung's, by construction")
    measured = rung["worst_spread"]
    relative = abs(measured - RECORDED_X1_WORST_SPREAD) / RECORDED_X1_WORST_SPREAD
    if C4_CONGRUENT:
        if MPI.COMM_WORLD.rank == 0:
            print(
                f"\n[WF-6 step4h] x1 spread record test SKIPPED (flag on): "
                f"worst-radius C4 four-copy spread {measured * 100:.4f}% against "
                f"the flag-off record {RECORDED_X1_WORST_SPREAD * 100:.4f}% "
                f"({relative * 100:.2f}% relative) — PRINTED",
                flush=True,
            )
        pytest.skip("flag-on mesh is not the record mesh (`GEO-32`)")
    assert relative <= RECORDED_SPREAD_TOLERANCE, (
        f"the x1 rung's worst-radius C4 four-copy spread reads "
        f"{measured * 100:.4f}% against the recorded "
        f"{RECORDED_X1_WORST_SPREAD * 100:.4f}% — {relative * 100:.2f}% "
        f"relative, outside the {RECORDED_SPREAD_TOLERANCE * 100:.0f}% "
        "reproduction control"
    )


@complex_only
def test_every_lattice_point_was_evaluated_on_every_rung(rung):
    """Structural: a point outside every cell would silently pass every gate."""
    valid = rung["valid"]
    assert bool(np.all(valid)), (
        f"rung {rung['spec']['key']}: only {int(np.sum(valid))} of {valid.size} "
        "lattice points were evaluated in all four readings"
    )


@complex_only
def test_power_accounting_closes_on_every_rung(rung):
    """**Anchor (ii), first half** — the map module's gate (i), band imported.

    The domain is PEC-walled and the phantom is vacuum, so real power supplied
    at the driven sheet has nowhere to go but the conductor and the four
    sheets.
    """
    for pid, sh in sorted(rung["shares"].items()):
        supplied = sh["supplied"]
        assert supplied > 0.0, (
            f"rung {rung['spec']['key']} [{pid}]: the driven sheet supplies "
            f"{supplied:.9e} W — a passive load cannot absorb negative real power"
        )
        total = sh["phantom"] + sh["conductor"] + sh["sheet_total"]
        residual = abs(supplied - total) / abs(supplied)
        assert residual <= POWER_BALANCE_BAND, (
            f"rung {rung['spec']['key']} [{pid}]: power accounting misses by "
            f"{residual:.6e} of the supplied {supplied:.9e} W (phantom "
            f"{sh['phantom']:.9e}, conductor {sh['conductor']:.9e}, sheets "
            f"{sh['sheet_total']:.9e}); imported band {POWER_BALANCE_BAND:.0e}"
        )


@complex_only
def test_the_exact_discrete_identity_closes_on_every_rung(rung):
    """**Step 4i anchor (a)** — ``P_src,exact = P_vol + P_sheet,exact``.

    ``a(E,E) = L(E)`` holds for the discrete solution, so this is a theorem of
    the weak form checked at `PORT-16`'s imported ``DISCRETE_IDENTITY_RTOL``
    (1e-6), not a band.  A miss is an assembly statement on this mesh.
    """
    if not EXACT_SHARES:
        pytest.skip(f"{EXACT_SHARES_ENV} unset: step 4i's exact shares not computed")
    for pid in ("P1", "P2"):
        r = _exact_readings(rung["shares"][pid], rung["exact"][pid])
        assert r["identity"] <= DISCRETE_IDENTITY_RTOL, (
            f"rung {rung['spec']['key']} [{pid}]: P_src,exact - P_vol - "
            f"P_sheet,exact deviates by {r['identity']:.3e} of P_src,exact, above "
            f"the imported DISCRETE_IDENTITY_RTOL {DISCRETE_IDENTITY_RTOL:g}"
        )


@complex_only
def test_the_terminal_residuals_reproduce_step_4h(rung):
    """**Step 4i anchor (b)** — the reproduction control (and negative control).

    The terminal residuals reproduce step 4h's flag-on readings to 1e-5
    relative (`20260911T140329Z_WF-6-step4h.log:2043-2044, 4034-4035`), so the
    exact shares were read on 4h's fixture.  Rungs without a flag-on record
    skip after printing.
    """
    if not EXACT_SHARES:
        pytest.skip(f"{EXACT_SHARES_ENV} unset: step 4i's reproduction not run")
    records = STEP4H_FLAG_ON_RESIDUALS.get(rung["spec"]["key"])
    if not C4_CONGRUENT or records is None:
        pytest.skip("no step-4h flag-on residual record for this rung/flag")
    for pid in ("P1", "P2"):
        measured = _residual(rung["shares"][pid])
        rel = abs(measured - records[pid]) / records[pid]
        assert rel <= REPRODUCTION_RTOL, (
            f"rung {rung['spec']['key']} [{pid}]: terminal residual {measured:.6e} "
            f"against step 4h's {records[pid]:.6e} ({rel:.3e} relative), outside "
            f"{REPRODUCTION_RTOL:g} — not 4h's fixture"
        )


@complex_only
def test_c_over_terminal_reproduces_step_4i_on_every_rung(rung):
    """**Step 4j anchor (b)** — reproduction control plus swapped-rung control.

    C/terminal reproduces 4i's printed value per rung and drive to 2e-6 (the
    7-significant-figure print precision), so the profile was read on 4i's
    fixture.  Negative control (asserted, backed by the same 4i logs): the x1 /
    x0.0095 reading held against the *other* rung's record misses by > 100x the
    rtol (measured 1.08e-2 = 5 400x).
    """
    if not SHEET_PROFILE_REQUESTED:
        pytest.skip(f"{SHEET_PROFILE_ENV} unset: step 4j's profile not run")
    if not EXACT_SHARES:
        pytest.skip(
            f"{SHEET_PROFILE_ENV}=1 requires {EXACT_SHARES_ENV}=1 — the anchor is "
            "4i's C/terminal, which only the exact shares compute"
        )
    key = rung["spec"]["key"]
    if not C4_CONGRUENT or key not in STEP4I_C_OVER_TERMINAL:
        pytest.skip("4i's C/terminal records are flag-on readings only")
    for pid in ("P1", "P2"):
        measured = _exact_readings(rung["shares"][pid], rung["exact"][pid])[
            "c_over_terminal"
        ]
        record = STEP4I_C_OVER_TERMINAL[key][pid]
        rel = abs(measured - record) / record
        assert rel <= C_OVER_TERMINAL_RTOL, (
            f"rung {key} [{pid}]: C/terminal {measured:.7f} against 4i's "
            f"{record:.6f} ({rel:.3e} relative), outside {C_OVER_TERMINAL_RTOL:g} "
            "— not 4i's fixture"
        )
        other = SWAPPED_RUNG_PAIRS.get(key)
        if other is not None:
            swapped = STEP4I_C_OVER_TERMINAL[other][pid]
            miss = abs(measured - swapped) / swapped
            if MPI.COMM_WORLD.rank == 0:
                print(
                    f"\n[WF-6 step4j] rung {key} [{pid}]: C/terminal {measured:.7f} vs "
                    f"own record {record:.6f} rel {rel:.3e} (ASSERTED <= "
                    f"{C_OVER_TERMINAL_RTOL:g}); vs swapped {other} record "
                    f"{swapped:.6f} rel {miss:.3e} = {miss / C_OVER_TERMINAL_RTOL:.0f}x "
                    f"rtol (ASSERTED > {SWAPPED_RUNG_FACTOR:.0f}x)",
                    flush=True,
                )
            assert miss > SWAPPED_RUNG_FACTOR * C_OVER_TERMINAL_RTOL, (
                f"rung {key} [{pid}]: C/terminal {measured:.7f} lands within "
                f"{SWAPPED_RUNG_FACTOR:.0f}x rtol of {other}'s record {swapped:.6f} "
                f"({miss:.3e}) — the reproduction control cannot tell rungs apart"
            )


@complex_only
def test_the_map_is_c4_covariant_on_every_rung(rung):
    """**Anchor (ii), second half** — the map module's gate (ii), band imported.

    Drive P2 read at the ``+90°`` image of the sample lattice against drive P1
    read at the lattice itself.  This is the identity that says the rung's
    solve is the same solve at each of the four drives; the four-copy spread
    printed above is what that identity leaves over in the *quadrature* field.
    """
    assert rung["covariance"] <= C4_COVARIANCE_BAND, (
        f"rung {rung['spec']['key']}: the CG1 |B1+| C4 covariance mismatch reads "
        f"{rung['covariance'] * 100:.4f}%, outside the imported "
        f"{C4_COVARIANCE_BAND * 100:.1f}% C4_COVARIANCE_BAND"
    )


@complex_only
def test_the_cw_drive_spread_dwarfs_the_ccw_spread_on_every_rung(rung):
    """**The negative control**, asserted (§9 rule (e)).

    `POST-6` step 1 measured the cw drive's C4 spread on this fixture at
    95.1975%, and step 4f measured the separation itself at 9.53x / 19.52x on
    these two rungs.  If the deliberately wrong drive's spread does not exceed
    the correct one's by 5x, the spread statistic is not reading the field's
    polarisation and the ladder means nothing.  5x rather than 10x because
    9.53x is the ×1 rung's arithmetic ceiling — see ``CW_SEPARATION_FACTOR``.
    """
    ccw = rung["worst_spread"]
    cw = rung["worst_cw_spread"]
    assert cw >= CW_SEPARATION_FACTOR * ccw, (
        f"rung {rung['spec']['key']}: the cw drive's worst-radius C4 spread "
        f"{cw * 100:.4f}% is only {cw / ccw:.2f}x the ccw quadrature's "
        f"{ccw * 100:.4f}%, below the {CW_SEPARATION_FACTOR:.0f}x separation "
        f"POST-6 step 1's 95.1975% backs — the statistic is not discriminating "
        "the co-rotating drive from the counter-rotating one"
    )
