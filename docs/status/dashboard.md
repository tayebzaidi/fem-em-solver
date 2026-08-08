# FEM-EM Solver — status

**Updated:** 2026-08-08, 03:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. Nothing blocking. Local `main` is **10 commits ahead** of `origin/main`
   (which still sits at the 08-07 10:30 review) after this review's commit —
   a push whenever convenient ships two closed chunks and the first SAR
   example, and still triggers the first-ever GitHub-runner execution of the
   `validation-complex` job. No Ansys benchmark cases commissioned yet (the
   weekly review owns that; next one is Sunday 01:30).
2. FYI, no action needed: the `lint` CI job is **red on `main` and
   adjudicated expected-red** — pre-existing formatting debt repo-wide, no
   recent chunk added any. The reformat is deliberately deferred until the
   big PORT-1 branch lands so it doesn't turn that landing into a conflict
   festival.
3. FYI, heads-up for Sunday: the port-voltage question escalated to the
   weekly review. The σ ladder disproved its own premise — a *closed* lossy
   loop is a shorted turn (induced current up to 87% of the drive), so that
   control can't separate loss from gap at any σ. Queue item 1 runs the
   reciprocal, non-degenerate half (the *gapped* loop at σ → 0) so Sunday's
   review adjudicates the branch with the ladder in hand.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); operator exact at 1 g/10 g (step 3); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 18:00 review)

Eighth consecutive 4/4 interval — two chunks closed, one measurement landed,
one disciplined park:

- **PORT-1 step 3b-xiii (parked)** — the σ ladder ran clean and monotone,
  then disproved the experiment it served: a closed lossy loop shorts
  itself, so the loss-vs-gap question is unanswerable on that control. The
  ~3% residual is untouched; the strategic call escalates to Sunday. A real
  rank-safety defect in material-map validation was found and fixed en route
  (parked with the branch; now scoped to land on `main` as OPS-13).
- **EX-3 ✅** — `examples/mri/02_mass_averaged_sar.py` is the first SAR
  quantity any example produces: point vs 1 g/10 g mass-averaged SAR plus a
  ParaView-colourable field, byte-matching the gated MAT-4 step-3 record
  through the runner. Imposed field, stated three ways; no C95.3 claim.
- **MAG-6 step 1 (measurement; chunk stays 🧪)** — the coil+phantom symmetry
  metric is **rank-dependent by 3×**: it fails at 1 rank and passes at 2,
  on the same mesh. CI's green was a partition lottery, not physics. Located
  to the test's CG1 sampling of a discontinuous field; the solve, the
  boundary, and the gauge are all exonerated. The rank-stable reading
  (~0.53) sits *above* tolerance — the historical record was never wrong.
- **OPS-12 ✅** — the residual-trend classifier adjudication went against
  the code on all three counts: undocumented asymmetric thresholds, a
  misrecorded symptom (the real one: an under-resourced iteration cap), and
  a classifier that production could never reach because the history was
  never armed. Known-issues 2 retired; the file is back in CI.

Audits: both ✅ flips verified §4-compliant by independent read-only
auditors — every claimed number found in the harness logs, exact-equality
anchors confirmed in source, no assertion loosened. Branch hygiene: the
superseded 3b-xii branch deleted (verified strict ancestor); exactly one
`attempt/*` branch remains, the live PORT-1 lineage.

## Automation health

- 32 consecutive clean slots since 08-05 15:30Z; eight 4/4 implementer
  slates in a row. Tree clean at review start and end; no `recovered/*`
  branches.
- Two of the three never-diagnosed baseline entries are now adjudicated
  (entries 2 and 4); both had materially wrong records. The last one
  (entry 6) is queued for the same treatment (OPS-14), with its recorded
  symptom explicitly distrusted.
- Queue depth 5, all items mutually independent; one is the standing heavy
  spare.

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-xiv** — the non-degenerate half of the sweep: the
   *gapped* loop at σ → 0. Measurement only; every outcome parks and
   reports so Sunday's weekly review adjudicates the branch with data.
2. **OPS-13** — land the rank-safe material-map validation fix on `main`
   with its own gate (the defect that cost a run 601 s of hang).
3. **MAG-6 step 2** — the DG0 symmetry metric's h-convergence: is ~0.53
   coarse-mesh error or a real defect? Decides estimator-vs-tolerance.
4. **OPS-14** — diagnose the last never-diagnosed baseline failure
   (known-issues 6, rank-dependent port-excitation test); pre-registered
   not-to-fix disposition if it's wholly inside the placeholder PORT-1
   deletes.
5. **MAT-6 step 6** (spare, heavy) — the additivity hypothesis: both
   refinement knobs at once, memory-probed first.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
