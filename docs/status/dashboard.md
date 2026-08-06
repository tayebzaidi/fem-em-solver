# FEM-EM Solver — status

**Updated:** 2026-08-06, 10:30 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. Housekeeping: local `main` is well ahead of `origin/main` (this review
   makes 18 unpushed commits); push when convenient. No Ansys benchmark
   cases commissioned yet (the weekly review owns that).
2. Your 10:12/10:17 examples-bar change (five per phase, accruing with gate
   closures) is now wired in: the first §5.4 ramp chunk (`EX-1`, a two-torus
   mesh/tags example) is queued this interval. No action needed unless the
   ramp rule isn't what you intended.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 03:00 review)

Third consecutive 4/4 interval — three landed, one disciplined park:

- **PORT-1 step 3b-vi** — the tangential path-integral port voltage measured
  ~0.48 × the closed form: a *third* distinct estimator value, and the four
  families now span a factor 15 off one solved field. Parked, not landed —
  correctly, because the plan's own quadrature-convergence precondition
  fails structurally: only ~5 mesh cells span the gap arc and the integrand
  jumps at every cell crossing, so no node count can resolve it. This
  review's rescope (step 3b-vii, queue item 1) refines the mesh along the
  arc; if ~0.48 survives refinement, the sampling-geometry question is
  settled and suspicion moves to the field scale in the gap or the closed-
  form reference itself.
- **POST-1 step 4b** — the sphere drop-set table re-scored on |E| is
  *digit-identical* (2e-16) to the Re E table, because the lossless
  real-data fixture's phasor is exactly real (max|Im E| = 0). Step 3's
  conclusions transfer unchanged, and the reason is now a 1e-12 gate that
  fails the moment a fixture acquires a phase — which is exactly when the
  Re E substitution becomes the 62% error step 4 measured on the planar
  fixture.
- **POST-1 step 5** — `prefer_interior=False` is now the production default
  at all four entry points; the retired guardrail's 2.157× peak penalty is
  pinned as the negative control, measured through production. The drop-set
  thread (steps 1–5) is complete; a cheap parity gate on the CSV export
  path is queued as step 6.
- **GEO-11** — the CAD-only margin sweep closed the chunk and found GEO-10's
  defect **live in two more fixtures**: `loop_over_half_space_domain` and
  `sphere_in_box_domain` never declare their outer-boundary group
  (tolerance 100× below the OCC padding). Latent — every caller discards
  the tags — but real; known-issues 12/13 opened. This review took the
  reserved tolerance decision: chunk **GEO-12** (queued) widens both to
  1e-6 and finally gates the group's existence.

All three ✅ flips (GEO-11, POST-1 steps 4b and 5) audited §4-compliant this
review by independent read-only auditors — logs, quantitative assertions,
elapsed times verified; pinned assertions confirmed to execute before their
skips. No demotions. One audit catch fixed in this commit: a mis-transcribed
digit string in a GEO-11 test comment.

## Automation health

- The grid has now run clean since 08-05 15:30Z — 12 consecutive slots,
  including three 4/4 implementer slates in a row.
- Tree clean at review start and end; no `recovered/*` branches.
- Parked branches: `attempt/PORT-1-step3bvi-…` only (kept — queue item 1
  continues on it). The superseded 3b-v branch was deleted this review
  after confirming its content was carried forward.
- Known-issues: entries 12 and 13 opened this interval (boundary-group
  classification, both latent); entry 12's fix is queued as GEO-12; the
  08-05 cron-gap entry closed after you confirmed host downtime.

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-vii** — the path-integral port voltage on an
   arc-refined mesh (critical path; ≥ 40 cells across the gap arc so the
   quadrature can converge).
2. **GEO-12** — widen the two 1e-9 wall tolerances to 1e-6 and gate the
   outer-boundary group's existence (fixes known-issues 12).
3. **POST-1 step 6** — CSV-export/stats sampling parity gate (integer count
   identity both modes).
4. **EX-1** — first §5.4 ramp example: the two-torus port fixture's mesh,
   cell tags, and facet tags in ParaView.
5. **MAT-6 step 5** (spare, heavy) — wire refinement at fixed box to
   separate the last ~1.5% of ΔX.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
