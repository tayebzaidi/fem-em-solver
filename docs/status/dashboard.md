# FEM-EM Solver — status

**Updated:** 2026-08-23 18:00, **daily review (scheduled, ran normally)**.
Headline: **the dolfinx upgrade is done — `main` now boots 0.11.0.post0 —
and the port route's reciprocity mystery is solved.** `OPS-18` closed both
remaining steps in one day: every §2.1 gate family reproduced green on the
new image and the 0.7.2 container is retired. In between, `PORT-9` leg
(d2) ran the decisive asymmetric probe and refuted the review's own
leading hypothesis at its stated mechanism: the voltage readout **is** the
source's adjoint (symmetric to 1.3e-10); what breaks reciprocity is one
level up — the impedance assembly normalises each column by the driven
port's own current, producing a *terminated* transimpedance that the
open-circuit Z→S conversion was never valid for. The fix (S straight from
power waves) is ruled and queued, with a licensed re-record of every port
record it moves. The 16-leg birdcage attempt found the mesh generator
cannot build sheets off the coordinate axes (fix scoped) — and measured
that **the 32-leg directive does not fit the production ring** (ceiling
N ≤ 25). Source of truth is `PROJECT_PLAN.md`; this page is a read-only
digest for the human operator.

## Waiting on you

1. 🟡 **A geometry decision is coming your way: 32 legs do not fit
   `ring_radius = 0.07 m` with 14 mm port boxes.** The layout clearance
   floor (1.25 × box width = 17.5 mm) caps the leg count at **N ≤ 25**;
   32 legs need `ring_radius ≥ 0.0876 m` or narrower boxes. Measured by
   `GEO-19` attempt 1, recorded, not worked around. The weekly review
   owns §10 and will propose a disposition Sunday — if you have a
   preference (bigger ring vs narrower boxes vs 16 legs as the
   production count), leave it in the plan or say so.
2. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
3. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
4. **ANS-1 Ansys replication** — still yours; ANS-3 (item 2) is the
   second case in the same queue.
5. FYI: **`main` now boots dolfinx 0.11.0.post0** (Python 3.12, numpy
   2.4.6, gmsh 4.15.2). The upgrade merged with every §2.1 family
   re-gated green except one owed leg (the real-mode `MAG` ladder, queued
   first). The compose allow was used only for `environment:` keys
   throughout; `volumes:` and the 64 G limit untouched.
6. FYI: expect port S-parameter records (two-torus and birdcage) to move
   by ~0.25% when the ruled assembly fix lands — a licensed, route-tagged
   class re-record, no band loosened. `PORT-11` (64 MHz ports) stays
   serial on it.
7. FYI: local `main` is well ahead of origin (push is manual).

## Honest current state (digest of §2 — S-parameter and suite lines changed)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated, **0.11 re-gate owed** | closed forms; Helmholtz 0.04%, loop 7.07%; wire `E_Ω` = 10.73% at h = 0.0025, rate 1.68 (`MAG-18`); digits are 0.7.2 — the `E_Ω` ladder on 0.11 is queue item 1 |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power 3.63% (TH-10, reproduced on 0.11); degree-2 gated at 0.1405% (TH-12/EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6, re-gated on 0.11); no affordable 64 MHz bracket on this box (adjudicated 08-18); Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4, re-gated on 0.11); never on a coil |
| S-parameters | ✅ field-derived (PORT-1), **assembly fix ruled** | two-torus + a solved birdcage 4×4 at 10 MHz — but leg (d2) proved the sweep's `Z` is a *terminated transimpedance*: reciprocity figures on symmetric fixtures partly measured the symmetry (0.25% per-pair asymmetry otherwise). Fix = power-wave S, queued with a licensed class re-record; §2.2's "no coil has ports" stands |
| Test-suite trust | ✅ reconciled, **on 0.11** | 437 collected / 0 errors both modes; `OPS-18` ✅ audited compliant (red→green same-command pair, volume records re-derived on the untouched 1e-9 band, partition identity 1.000000000000) |

## Recent activity (2026-08-23 10:30 → 18:00)

- **12:00:** `OPS-18` 3a closed (attempt 8) — the two unmasked records
  written version-tagged under (1\*); `19 passed` / exit 0 twice
  (238.64 / 238.73 s), records identical to six digits across runs, no
  further record unmasked.
- **13:30:** `PORT-9` leg (d2) — the asymmetric two-torus probe. Both
  pre-registered hypotheses beaten by the measurement: the readout is
  adjoint (`I₁(d2)` = `I₂(d1)` to 1.33e-10) and the whole `Z` asymmetry
  collapses to the per-column current normalisation (`Z₁₂/Z₂₁` =
  `I₁(d1)/I₂(d2)` to 1.33e-10). Per-pair asymmetry 0.25%, hidden at
  1e6 Ω, surfaced at 50 Ω — (d1)'s birdcage miss explained without a
  birdcage defect.
- **15:00:** `OPS-18` 3b closed ⇒ **chunk ✅, `main` boots 0.11**.
  Same-command red→green anchor, both-mode collects at 437/0, volume
  drift re-recorded on the untouched band, three known-issues entries
  closed, `attempt/OPS-18` merged (and deleted by this review).
- **16:30:** `GEO-19` attempt 1 — 16 legs cannot mesh: a tag-encoding
  ceiling at 9 legs (fixed on `main`, verified inert digit-for-digit)
  and axis-aligned-only sheets (open, fix scoped as step B). The gates
  module is parked ready; the `N ≤ 25` layout ceiling measured en route.
- **This review:** `OPS-18` audited COMPLIANT from the footers; ruling
  (2\*) power-wave S assembly (open-circuit `Z` rejected on measured
  near-degeneracy); ruling (3\*) `MAG-18`-on-0.11 queued first; `GEO-19`
  rescoped into steps B/C; queue rebuilt to six items; old §9 block
  archived.

## Automation health

- Four slots, four useful outcomes: **three closes** (`OPS-18` 3a, 3b,
  `PORT-9` (d2) — the last a scoped diagnostic that landed its finding)
  and one blocked attempt that converted its hour into two named
  blockers, one fix, and a production-geometry ceiling. No drain, no
  exit 124, no wedge, tree clean at every handoff, no `recovered/*`.
- Branches: `attempt/OPS-18` **deleted** (fully merged);
  `attempt/PORT-9-d1-*` parked (lands with (d1′));
  `attempt/GEO-19-*` parked (its module is queue item 5).
- The queue holds **six** items, four independent, two explicitly serial
  with skip instructions. All on the 0.11 `main`. Still unqueued by
  design: `PORT-11` step 1, `PORT-9` (d1′).

## On deck (§9 — six open items this review)

1. **`MAG-18` `E_Ω` ladder on 0.11** — the one §2.1 family the upgrade
   did not re-gate (heavy, real, independent)
2. **`PORT-9` leg (d3)** — power-wave S assembly + two-torus class
   re-record, with the 50 Ω asymmetric fixture as its own negative
   control (standard, complex, independent)
3. **`GEO-19` step B** — sheets built in the leg's local frame; 4-leg
   invariance control digit-for-digit (standard, real, independent)
4. **`PORT-9` leg (d3b)** — birdcage class re-record on the fixed route
   (serial on item 2)
5. **`GEO-19` step C** — the parked 16-leg gates module + first
   measured cost (heavy, serial on item 3)
6. **`GEO-20` step 1** — ring-gap ports at 4 legs (standard,
   independent, spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
