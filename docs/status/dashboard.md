# FEM-EM Solver — status

**Updated:** 2026-08-11, 18:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. **The first Ansys benchmark is ready to replicate in AED** (unchanged
   since 2026-08-09 18:00). `ANS-1` at
   `examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/` pins itself to
   the `MAT-6` gate (ΔR = +0.32770 Ω, **1.5834%** from Dodd–Deeds).
   `SPEC.md` box 1 is checked; the next two are yours: build the case in
   AED per `SPEC.md`, fill the blank AED columns in `COMPARISON.md` — the
   weekly review then adjudicates. Reminders: ΔX is reported, never gated;
   our Re Z(σ = 0) is exactly 0.0 by structure — disable coil eddy effects
   in AED per `SPEC.md` §Excitation before comparing. *(Refinement studies
   have since taken ΔR to 0.28–0.88% by two independent routes, and their
   composition is queued as a measurement — but the production fixture,
   and therefore the SPEC you are replicating, stays deliberately frozen
   until your comparison is adjudicated. Nothing changes on your side.)*
2. **What did the GitHub runner say?** `origin/main` is still at the
   2026-08-10 18:00 review commit (`b6e994f`), so a runner execution of
   `validation-complex` should exist by now. Sessions have no network
   access and cannot see the result; anything you can paste (pass/fail,
   log excerpt) is new information. Local `main` is **14 ahead** once this
   review's commit lands — a follow-up push whenever convenient.
3. FYI, no action needed: the `lint` CI job stays red-by-adjudication
   (reformat deferred until the PORT-1 branch lands); and the 2026-08-08
   `MAG-13` host-observables ask stays withdrawn — the foreground recipe
   has now completed that exact profile twice, confirming the
   background-run trap as the whole story.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); operator exact at 1 g/10 g (step 3); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

Headline gates unmoved. Underneath them: mesh-knob **additivity tested
green** on the coil-loading fixture (−0.080 pp defect), and the combined
box+wire mesh is **sub-1% on ΔR** (0.8835%) by a second route.

## Recent activity (since the 10:30 review)

**Four of four slots landed their item — the second consecutive clean
sweep.**

- **MAT-6 step 7 Part 2b** (12:00): the `-n 8` cost probe priced the
  loaded solve at **179.3 s** — inside the pre-committed band, so the
  additivity gate fit one foreground call.
- **POST-4 step 3 closed** (13:30): the mri demo's centerline table now
  samples the solved fields; rank spread **23.5539% → 0.008613%** (a
  2735× collapse). The known-issues centerline entry is retired; the
  `mri:1` guide is rewritten.
- **MAG-13 step 2** (15:00): the < 5% wire rung is **measured and missed
  on-rate** — 5.6494% at h = 0.00125, where the record rate had already
  predicted 5.95%. The convergence is as good as advertised (rate 1.174
  vs 1.10); the target was optimistic at this rung. The error looks
  concentrated near the wire; a cheap profile measurement is queued
  before any graded mesh is committed.
- **MAT-6 step 7 closed** (16:30): the additivity gate ran green first
  time — **the two mesh knobs are additive** (defect −0.080 pp against a
  0.5 pp band), ΔR 0.8835% on the combined fixture under the unwidened 5%
  ceiling, O(h²) wire control reproduced.

Both ✅ flips were audited against the §4 bar (one auditor each):
compliant, no demotions; minor wording drift in the POST-4 entry corrected.

## Automation health

- **Slot yield this interval: 4/4** — two consecutive clean sweeps since
  the foreground-recipe fix; the trap has not recurred in eight slots.
- Tree stayed clean the whole interval; no `recovered/*` branches; all
  slots committed their own work.
- Both `attempt/PORT-1-*` branches stay parked under the weekly licence —
  the **weekly review (2026-08-16) holds the 3b-xv adjudication and the
  second discriminator slot**.
- Queue depth **5** after refresh; items 1–4 independent, item 5 is the
  declared spare (brute-force route on the same question as item 2).

## On deck (§9, refreshed this review)

1. **POST-4 step 4** (standard) — bound the P1-interpolant artifact on the
   export paths; measurement + caveat only.
2. **MAG-13 step 2 profile** (heavy) — re-solve the measured rung and map
   error-vs-radius densely; decides where a graded mesh would spend its
   cells before one is built.
3. **MAT-6 step 9** (heavy) — third box rung (W = 0.35): turn the ΔX
   truncation trend into a W → ∞ extrapolation; the input a future ΔX
   gate needs.
4. **MAT-6 step 10** (heavy) — do the two sub-1% ΔR routes compose? One
   solve pair on the combined fixture + the fine slab knob.
5. **MAG-13 step 2 rung 3** (heavy, spare) — the < 5% wire by brute force
   (~1.5 M cells); exit 124 is itself the reading.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy is refreshed by interactive sessions only and may
lag this file; `docs/status/dashboard.md` on `main` is always current.*
