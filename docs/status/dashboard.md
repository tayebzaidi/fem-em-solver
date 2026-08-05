# FEM-EM Solver — status

**Updated:** 2026-08-05 (interactive setup — subsequent updates come from the
scheduled daily review). Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

## Waiting on you

*Nothing pending.* No Ansys benchmark cases are commissioned yet
(`examples/ansys_benchmarks/` holds only its README), and automation is
healthy. When something lands here, it is the thing to do next.

## Honest current state (digest of §2)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (last ~24 h)

- **PORT-1 step 3b-iv landed** — port facet tags green at `-n 2` in 20 s;
  the hang was a rank-asymmetric `create_entity_permutations()`; known-issues
  9 retired. Item 5's dependency is satisfied.
- **POST-1 step 3 landed** — drop-set semantics on the solved TH-8 sphere;
  green at `-n 2` (4.42 s), bit-identical at `-n 4`; layer separates in
  spread (1.334×) but not in mean.
- **POST-3 step 5 landed** — piecewise μᵣ through both legs of the Poynting
  balance.

## Automation health

- Last daily review: 2026-08-05 10:30 (next: 18:00 / 03:00 / 10:30 grid).
- Parked branches: `attempt/PORT-1-step3biii-…` (kept for item 5's test
  file), `attempt/PORT-1-step3biv-…` (superseded once 3b-iv landed — next
  review disposes). No `recovered/*` branches.
- Open known-issues entries: see `docs/testing/known-issues.md`.
- Origin push is manual: local `main` is ahead of `origin/main` until the
  operator pushes.

## On deck (§9, top of queue)

1. ~~PORT-1 step 3b-iv (ghost cells)~~ — **done 2026-08-05**
2. ~~POST-1 step 3 (drop-set semantics)~~ — **done 2026-08-05**
3. –5. remaining §9 items — see PROJECT_PLAN.md §9 (item 5, the port gap
   voltage/impedance test, is now unblocked by item 1).

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
