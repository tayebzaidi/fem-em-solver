# FEM-EM Solver — status

**Updated:** 2026-08-07, 03:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. Housekeeping: local `main` is **9 commits ahead** of `origin/main` after
   this review — push when convenient (every "in CI" claim is a local
   reproduction until then). No Ansys benchmark cases commissioned yet
   (the weekly review owns that; next one is Sunday 01:30).
2. FYI, no action needed: **the port-voltage factor-2 mystery is solved**
   (see Recent activity) — it was the estimator integrating the wrong arc
   segment, not physics. The fix is queued for the next implementer slot.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 18:00 review)

Fifth consecutive 4/4 interval — three landed, one disciplined park, and
the park is the headline:

- **PORT-1 step 3b-ix** — the factor-2 question is **answered**. Closing
  the Faraday loop around the wire recovers 0.896 × the closed form, and
  the missing half of the port voltage was never in the wire (finite-σ
  penetration measures 200× too small and falls with σ, killing that
  suspect). It sits in the 1 mm of gap dielectric per side that the
  fixture buries *outside* the nominal wedge — 0.8% of the loop's length
  carrying 45% of its EMF, which the estimator never integrated. Terminal
  to terminal the voltage is 0.8936 × ωM₁₂, not 0.49. Parked on its
  branch; the one-line-of-substance fix (step 3b-x) is queue item 1, and
  whether the remaining −10.6% is the PEC box is item 2's padding sweep.
- **PORT-1 step 3b-viii** — the closed-form ωM₁₂ reference exonerated:
  two independent derivations agree to 1.5e-15, and the finite-wire
  correction is +0.481% — far too small for a factor 2, and the wrong
  sign to help. Both suspects the previous review named are now dead,
  which is exactly what let 3b-ix's finding stand alone.
- **GEO-13** — closed. `cylindrical_domain`'s wall tolerance is now a
  geometric fraction of the annulus, not the mesh size; all four fixtures
  under the classification-margin identity assert live, and the probe
  reproduced the predicted failure (old predicate swallows the inner
  cylinder whole at coarse resolution). Known-issues 13 retired — the
  last open classification-margin defect.
- **EX-1** — restored ✅. The runner path is on record: `./run_examples.sh
  -e mesh:1` reproduces every geometric identity at every printed digit.

Audits: both ✅ flips (GEO-13, EX-1) verified §4-compliant by independent
read-only auditors — every claimed number found in the harness logs; no
demotions. Branch hygiene: the superseded 3b-vii branch deleted (the 3b-ix
branch carries a verified strict superset); only
`attempt/PORT-1-step3bix-…` remains, and queue item 1 lands it.

## Automation health

- The grid has run clean since 08-05 15:30Z — 20 consecutive slots, five
  4/4 implementer slates in a row.
- Tree clean at review start and end; no `recovered/*` branches.
- Known-issues: entry 13 retired by GEO-13; entry 3 (S-parameters) gained
  the 3b-viii/3b-ix findings and the 3b-x/3b-xi scoping — it is the target
  of queue items 1 and 2.
- New plan work this review: PORT-1 steps 3b-x/3b-xi, MAT-4 step 3, and
  example chunk EX-2 (cylindrical phantom in ParaView, from GEO-13's
  closure) all scoped into §7.

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-x** — correct the gap-voltage estimator's limits
   (terminal-to-terminal, read off the port facet tags) and land the
   parked branch.
2. **PORT-1 step 3b-xi** — padding sweep on the ungapped fixture: is the
   residual −10.6% the PEC box? Independent of item 1.
3. **EX-2** — cylindrical phantom domain, classified and tagged, in
   ParaView (§5.4 ramp for GEO-13).
4. **MAT-4 step 3** — the SAR averaging operator gated at the standard
   1 g/10 g masses on a sphere that can hold them; no solve.
5. **MAT-6 step 5** (spare, heavy) — wire refinement at fixed box to
   separate the last ~1.5% of ΔX.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
