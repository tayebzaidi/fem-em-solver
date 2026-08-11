# FEM-EM Solver — status

**Updated:** 2026-08-11, 10:30 daily review. Source of truth is
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
   in AED per `SPEC.md` §Excitation before comparing. *(Related decision
   this review: a refinement study just took ΔR to **0.2829%** on a finer
   slab mesh, but the production fixture — and therefore the SPEC you are
   replicating — is deliberately frozen until your comparison is
   adjudicated. Nothing changes on your side.)*
2. **What did the GitHub runner say?** `origin/main` is at the 2026-08-10
   18:00 review commit, so a runner execution of `validation-complex`
   should exist by now. Sessions have no network access and cannot see the
   result; anything you can paste (pass/fail, log excerpt) is new
   information. Local `main` is 8 ahead once this review's commit lands —
   a follow-up push whenever convenient.
3. FYI, no action needed: the `lint` CI job stays red-by-adjudication
   (reformat deferred until the PORT-1 branch lands).
4. **Withdrawn:** the ask for host-side observables around the 2026-08-08
   `MAG-13` kills. The wrapper logs settle it — both sessions ended their
   turn while their solve ran *backgrounded*, which in a headless session
   exits the CLI and kills the run; the same trap that cost three slots on
   08-10/11. No host mystery, nothing to dig up; `dmesg`/`journalctl`
   archaeology is off your list. `MAG-13` step 2 is re-queued under the
   foreground recipe.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); operator exact at 1 g/10 g (step 3); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

Headline gates unmoved, but two error budgets closed underneath them (see
below) — the coil-loading fixture is now demonstrably sub-1%-capable on ΔR.

## Recent activity (since the 03:00 review)

**Four of four slots landed their item — a clean sweep.**

- **MAT-6 step 7 Part 2** (04:30): the foreground recipe worked first
  time; the solve three slots died for is priced — **372.9 s at `-n 4`,
  no OOM at 64 G** on the 697 401-cell combined case. The additivity
  reading itself still needs a wider window; this review routed it
  through an `-n 8` cost probe (queue items 1 + 4).
- **EX-15 closed** (06:00): all 16 runnable examples now carry a
  step-by-step analysis guide, checker green, negative control fired.
  Your guide directive is done.
- **MAT-6 step 8** (07:30): the ΔR error budget is closed — doubling
  slab resolution at fixed wire takes ΔR **1.5834% → 0.2829%**, so the
  residual was skin-depth resolution, not the coil model. Promoting the
  finer fixture to production is deferred pending your ANS-1 comparison
  (see Waiting-on-you item 1).
- **POST-4 step 1** (09:00): decisive negative — the suspected ownership
  tie-break in the parallel point evaluator is **refuted** (0/120 on
  every counter). The mri demo's 23% rank spread enters at the
  Lagrange-P1 interpolation the example prints (source fields agree to
  0.008426% — an 11 630× separation). Fix re-scoped onto the real locus
  (queue item 2).

All three ✅ steps were audited against the §4 bar (one auditor each):
compliant, no demotions. Also this review: the 2026-08-08 "unexplained
harness termination" known-issues entry is **retired** — same
background-run trap, proven from the wrapper logs — which un-blocks
`MAG-13` step 2.

## Automation health

- **Slot yield this interval: 4/4** — best interval on record, directly
  after the worst (0/4). The foreground-recipe fix held in all four
  slots; the trap list now carries it.
- Tree stayed clean the whole interval; no `recovered/*` branches; all
  slots committed their own work.
- Both `attempt/PORT-1-*` branches stay parked under the weekly licence —
  the **weekly review (2026-08-16) holds the 3b-xv adjudication and the
  second discriminator slot**.
- Queue depth **5** after refresh; items 1, 2, 3, 5 independent, item 4
  serial on item 1 with an explicit skip clause.

## On deck (§9, refreshed this review)

1. **MAT-6 step 7 Part 2b** (heavy) — `-n 8` cost probe of the combined
   fixture; decides whether the additivity gate fits one foreground call
   (solve ≤ ~240 s).
2. **POST-4 step 3** (standard) — the mri demo's centerline table samples
   the solved fields instead of the P1 interpolants; anchor: 23.5539% →
   ≤ 0.1% across rank counts.
3. **MAG-13 step 2** (heavy, un-blocked) — the < 5% wire rung at `-n 8`
   under the foreground recipe; exit 124 is itself the cost reading.
4. **MAT-6 step 7 Part 2c** (heavy, serial on item 1) — the additivity
   gate vs 0.9843, first run of the drafted module; skip clause if item 1
   priced it out.
5. **POST-4 step 4** (standard, spare) — bound the P1-interpolant artifact
   on the export paths; measurement + caveat only.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
