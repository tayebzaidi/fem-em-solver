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
refines (`PORT-14` step 1b's mechanical control — a keyword that silently did
nothing would otherwise read as a converged ladder).

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
"""

from __future__ import annotations

import os
import time

import numpy as np
import pytest
from mpi4py import MPI

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_leg_offset import CONDUCTOR_RESOLUTION, RESOLUTION
from tests.mesh.test_birdcage_port_tags import LEG_COUNT
from tests.validation.test_lossy_sphere_fullwave import FREQUENCY_128_HZ
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

# Richardson: fit S(h) = S_inf + C h^p on the three finest degree-1 rungs and
# report p with the extrapolant.  A fit outside this bracket is not an
# asymptotic reading and is reported as such rather than as a number.
RICHARDSON_P_BRACKET = (0.2, 6.0)


def _ladder_factors():
    """The pre-registered ladder, or a trimmed one for a non-XL smoke."""
    raw = os.environ.get(RUNG_ENV)
    if raw is None or not raw.strip():
        return LADDER_FACTORS
    return tuple(float(v) for v in raw.replace(",", " ").split())


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
    resolutions = _ladder_resolutions()
    factors = () if resolutions else _ladder_factors()
    rungs = []
    started = time.perf_counter()

    # --- step 2c: the global-resolution ladder, coarse to fine, with a stop
    # rule after each rung so a wall costs the next rung and not the ones
    # already measured.
    for res in resolutions:
        rung = _four_port_rung(
            f"ANS-4 step2c h={res:g} degree 1",
            zeros,
            FREQUENCY_128_HZ,
            resolution=res,
        )
        rung["factor"] = float(res)
        rung["knob"] = "resolution"
        rungs.append(rung)
        elapsed = time.perf_counter() - started
        if comm.rank == 0:
            print(
                f"[ANS-4 step2c] rung h={res:g}: {rung['cells']} cells, mesh "
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
            f"ANS-4 step2 x{factor:g} degree 1",
            zeros,
            FREQUENCY_128_HZ,
            conductor_resolution=h_c,
        )
        rung["factor"] = float(factor)
        rung["knob"] = "conductor_resolution"
        rungs.append(rung)
        if comm.rank == 0:
            print(
                f"[ANS-4 step2] rung x{factor:g} degree 1: {rung['cells']} cells, "
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
            "ANS-4 step2 x1 degree 2",
            zeros,
            FREQUENCY_128_HZ,
            reuse=base,
            degree=2,
        )
        degree2["factor"] = float(DEGREE_2_FACTOR)
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
            f"wall at -n {comm.size}, f = {FREQUENCY_128_HZ:.6e} Hz",
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
    ratio = base["cells"] / STEP2_CELL_COUNT
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
    """`PORT-14` step 1b's mechanical control on the keyword.

    A ``conductor_resolution`` that silently did nothing would produce four
    identical rungs, which would read as a perfectly converged ladder — the
    most dangerous possible false positive for this measurement.
    """
    comm = MPI.COMM_WORLD
    rungs = sorted(ladder["rungs"], key=lambda r: -r["factor"])
    if len(rungs) < 2:
        pytest.skip("a single-rung ladder cannot show refinement")
    if comm.rank == 0:
        for r in rungs:
            print(
                f"[ANS-4 step2] refinement: x{r['factor']:g} -> {r['cells']} cells",
                flush=True,
            )
    for coarser, finer in zip(rungs, rungs[1:]):
        assert finer["cells"] > coarser["cells"], (
            f"conductor_resolution x{finer['factor']:g} gave {finer['cells']} "
            f"cells, not more than x{coarser['factor']:g}'s {coarser['cells']} — "
            "the keyword did not refine anything, so the ladder below is four "
            "re-runs of one mesh rather than a convergence measurement"
        )


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
        "\n[ANS-4 step2] === the readout: three C4 classes of S at 128 MHz ===",
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
