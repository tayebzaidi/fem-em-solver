# FEM-EM Solver — status

**Updated:** 2026-08-05, 18:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

*Nothing blocking.* No Ansys benchmark cases are commissioned yet
(`examples/ansys_benchmarks/` holds only its README — the weekly review
owns commissioning), and automation is healthy. Housekeeping only: local
`main` is 3 commits ahead of `origin/main`; push when convenient.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy now safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 10:30 review)

All four implementer slots completed and landed — the first 4/4 interval:

- **PORT-1 step 3b-iv** — port facet tags green at `-n 2` in 20 s. The hang
  was a lazily-reached collective (`create_entity_permutations()` entered on
  one rank only); known-issues 9 retired. The port-voltage step (3b-v) is
  unblocked and now tops the queue.
- **POST-1 step 3** — drop-set semantics measured on the solved TH-8 sphere:
  the guardrail is harmless for means (1.009×) but the drop layer owns both
  tag extrema. This review adjudicated: guardrail stays for means; extremum
  statistics are unsafe through it pending a planar-fixture step (queued).
  POST-1 moved ⚠️ → 🟡.
- **MAT-6 step 4** — the projected-drive ΔX finding survives a 2.17× larger
  box: the 0.11 projected-vs-pinned gap does not shrink, so it is real, not
  box error. ΔR control held at 1.57%.
- **MAG-16** — magnetostatic energy now safe in the complex build, value
  pinned across builds (imaginary part exactly zero); known-issues 8 retired;
  the test joined the `validation-complex` CI job. Audited §4-compliant.

## Automation health

- Reviews on the 90-minute grid: this one 18:00; next 03:00 / 10:30. Weekly
  planning review Sunday 01:30.
- 4/4 implementer slots landed this interval; nothing parked, tree clean.
- Parked branches: `attempt/PORT-1-step3biii-…` only (kept — queue item 1
  reuses its test file). The landed 3b-iv branch was deleted this review.
  No `recovered/*` branches.
- Standing failures are all catalogued in `docs/testing/known-issues.md`;
  entries 8 and 9 retired today. Entries 5 and 10 now have owning chunks in
  the queue (GEO-4 step 1, GEO-10).

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-v** — facet-integral port voltage vs the closed-form
   `ωM₁₂` (the S-parameter critical path).
2. **POST-1 step 4** — drop-set semantics on a planar interface (decides the
   SAR-peak extremum rule).
3. **GEO-4 step 1** — fix the off-centre domain-sizing failure
   (known-issues 5; the standing `tests/mesh` red).
4. **GEO-10** — restore the fixture's missing outer-boundary facet tag
   (known-issues 10).
5. **MAT-6 step 5** (spare, heavy) — wire refinement at fixed box to
   separate the last ~1.5% of ΔX.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
