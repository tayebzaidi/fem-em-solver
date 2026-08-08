# FEM-EM Solver — status

**Updated:** 2026-08-08, 10:30 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. Nothing blocking. Local `main` is now **15 commits ahead** of
   `origin/main` after this review's commit — a push whenever convenient
   ships four more closed chunks and still triggers the first-ever
   GitHub-runner execution of the `validation-complex` job. No Ansys
   benchmark cases commissioned yet (the weekly review owns that; next one
   is Sunday 01:30).
2. FYI, heads-up for Sunday: the PORT-1 adjudication package is now
   **complete, with a verdict attached** — loss is exonerated, the gap
   geometry/estimator owns the ~3% deviation (see below), and the proposed
   successor (gapped-vs-closed at fixed σ = 800) changes the fixture's
   topology and needs the weekly review's licence. Exactly one `attempt/*`
   branch remains, carrying the whole estimator lineage.
3. FYI, no action needed: the `lint` CI job stays red-by-adjudication
   (pre-existing repo-wide formatting debt; reformat deferred until the
   PORT-1 branch lands).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); operator exact at 1 g/10 g (step 3); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 03:00 review)

Ninth consecutive 4/4 interval — three chunks closed, one measurement
parked exactly as scoped:

- **PORT-1 step 3b-xiv (parked, by design)** — the gapped loop driven
  toward σ = 0: the measurement Sunday's adjudication was waiting on, and
  it delivered a verdict. The σ = 0 corner itself is degenerate (an open
  circuit — the reading is a capacitive potential, 350× outside the band),
  but the non-degenerate rungs answer the question by sensitivity: a 4×
  drop in σ moves the estimator only +0.19 pp, so **loss is exonerated**
  and the ~3% estimator-vs-control deviation now belongs to the gap
  geometry/estimator — the last suspect standing. Branch decision stays
  with the weekly review.
- **OPS-13 ✅** — the rank-safe material-map validation landed on `main`
  with its own gate: red baseline first (the old check hangs a rank at the
  timeout ceiling), then a closed-form volume identity at 1e-12 asserted
  at two rank counts, byte-identical digit strings.
- **MAG-6 step 2 ✅** — the ~0.53 symmetry residual is **coarse-mesh
  discretisation, measured**: the DG0 metric falls monotonically at
  ~O(h) and meets the untouched 0.350 tolerance at h = 0.010 m for 2 s of
  solve. The test's own CG1 path does not converge on the identical
  solves. This review then made the call the measurement licensed: step 3
  re-points the test at DG0 and refines one rung — closing MAG-6 and
  retiring known-issues 4 if the record reproduces.
- **OPS-14 ✅ (diagnosis)** — the last never-diagnosed baseline failure:
  **two** independent defects, each alone fatal — a fixture whose global
  tag set is rank-count dependent, and a non-collective validation check.
  Both wholly inside the PORT-0 placeholder PORT-1 deletes, so the
  pre-registered not-to-fix branch applies: known-issues 6 re-pointed at
  PORT-1, one docstring hazard warning, nothing else touched. All three
  never-diagnosed entries have now been adjudicated; all three records
  were materially wrong.

Audits: all three ✅ flips verified §4-compliant by independent read-only
auditors — every claimed number found in the harness logs, quantitative
anchors confirmed, red baselines on record, no assertion loosened, and
OPS-14's not-to-fix disposition verified pre-registered before the run.

## Automation health

- 36 consecutive clean slots since 08-05 15:30Z; nine 4/4 implementer
  slates in a row. Tree clean at review start and end; no `recovered/*`
  branches; superseded 3b-xiii branch deleted (verified strict ancestor).
- Queue depth **3, not 5** — stated per protocol rather than padded: the
  PORT-1 critical path is frozen for Sunday's adjudication, and the other
  large items (PORT-4…8, MAT-4's C95.3 claim, POST-1's final step) are
  blocked behind it or behind a solved coil field. The fourth run before
  the 18:00 review will hit the drain instruction and journal — that is
  expected, not an outage.

## On deck (§9, refreshed this review)

1. **MAG-6 step 3** — land the adjudicated symmetry estimator: DG0
   sampling at h = 0.010 against the untouched 0.350, with a rank-spread
   gate. Closes MAG-6, retires known-issues 4.
2. **MAT-6 step 6** (carried spare, heavy) — the additivity hypothesis:
   both refinement knobs at once, memory-probed first.
3. **MAG-13 step 2** (heavy) — the < 5% wire target at the enlarged
   budget: cost-probe the ~1.1 M-cell rung the recorded rate predicts,
   then gate against the straight-wire closed form if it fits.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
