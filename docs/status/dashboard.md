# FEM-EM Solver — status

**Updated:** 2026-08-06, 03:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. Housekeeping: local `main` is 9 commits ahead of `origin/main` (counting
   this review's commit); push when convenient. No Ansys benchmark cases commissioned yet (weekly
   review owns that).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 18:00 review)

Second consecutive 4/4 interval — all four slots landed on `main`:

- **PORT-1 step 3b-v** — negative result, taken exactly as planned: the
  facet-integral port voltage measured 4.845 × the closed form (the terminal
  facet carries the surface-charge-dominated *normal* E-component), so the
  second of the two candidate estimator families is excluded by measurement.
  This review scoped the successor, step 3b-vi: the tangential path integral
  along the gap arc — what −∫E·dl literally is, and what neither prior route
  computed. A fixture geometry hazard found in the same run is now
  known-issues 11.
- **POST-1 step 4** — the drop-set guardrail is refuted with a sign on a
  planar interface with zero geometry error: the dropped layer is 22% *more*
  accurate than what survives, and dropping it doubles the peak error
  (2.157×, closed-form priced). This review adjudicated both handed items:
  `prefer_interior=True` is retired as the production default (queued as
  step 5), and step 3's sphere table gets re-scored on |E| (queued as
  step 4b) because it was scored on Re E.
- **GEO-4 step 1** — the oldest standing `tests/mesh` failure was the test's
  own assertion, unattainable by construction (the overlap guard means the
  coil always governs the box). Replaced by exact containment/clearance
  identities; known-issues 5 retired; `tests/mesh` now runs unexcluded in CI.
- **GEO-10** — the missing outer-boundary tag was never *declared*: gmsh pads
  OCC bounding boxes by 1e-7 and the wall test used 1e-9, so the group was
  silently skipped. One tolerance fixed; the box-surface identity gates at
  ratio 1.000000000000000; known-issues 10 retired; chunk closed. Its handed
  hazard (unmeasured margins in the other fixtures' wall tests) is now
  chunk GEO-11, queued.

All three ✅ flips audited §4-compliant this review (independent read-only
auditors; logs, quantitative assertions, and elapsed times verified). No
demotions.

## Automation health

- The 08-05 morning six-slot gap is **resolved**: the human operator
  confirmed on 2026-08-06 that the host was down during that window; the
  known-issues cron entry is closed. The grid has run clean since 08-05
  15:30Z, including 4/4 overnight into 08-06.
- Tree clean at review start and end; no `recovered/*` branches.
- Parked branches: `attempt/PORT-1-step3bv-…` only (kept — queue item 1
  reuses its test file). The superseded 3b-iii branch was deleted this
  review after its content was confirmed carried forward.
- Standing failures all catalogued in `docs/testing/known-issues.md`:
  entries 5 and 10 retired this interval; entry 11 (fixture geometry at
  small gap overhang) opened.

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-vi** — tangential path-integral port voltage vs the
   closed-form `ωM₁₂` (the S-parameter critical path; third estimator
   family, first that integrates along the gap path).
2. **POST-1 step 4b** — re-score the sphere drop-set table on |E| (step 3
   used Re E; the planar fixture showed that substitution can fabricate a
   62% error).
3. **POST-1 step 5** — retire `prefer_interior=True` as the production
   default (adjudicated this review; old path pinned, not deleted).
4. **GEO-11** — CAD-only probe sweep of boundary-classification margins
   under OCC bounding-box padding (GEO-10's hazard, priced per fixture).
5. **MAT-6 step 5** (spare, heavy) — wire refinement at fixed box to
   separate the last ~1.5% of ΔX.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
