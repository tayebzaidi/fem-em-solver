# FEM-EM Solver — status

**Updated:** 2026-08-07, 18:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. Nothing blocking. Thanks for the push — `origin/main` now sits at the
   10:30 review commit; local `main` is **5 commits ahead** after this
   review (today's afternoon results). The first GitHub-runner CI
   execution of the `validation-complex` job still lands whenever you next
   push; no Ansys benchmark cases commissioned yet (the weekly review owns
   that; next one is Sunday 01:30).
2. FYI, no action needed: the corrected port voltage (0.8945 × ωM₁₂)
   survived the box test — enlarging the domain moved the estimator and
   its control *together*, so the ~3% gap between them is real and now has
   exactly one suspect left (lossy-gapped vs lossless-closed loop). Queue
   item 1 buys the σ ladder that decides it; landing the branch is
   pre-authorized only under the favourable outcome.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); operator now exact at 1 g/10 g (step 3); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 10:30 review)

Seventh consecutive 4/4 interval — two landed, one disciplined park, one
protocol-correct drain stop:

- **PORT-1 step 3b-xii (parked)** — the pre-decided box discriminator ran
  and answered: growing the PEC box moves the estimator (+2.96 pp) and
  the independent control (+3.05 pp) **together**, leaving their 3%
  disagreement untouched. The box is exonerated as the owner of the
  residual; what remains is the one structural difference between the two
  routes — the production loop is gapped and conducting, the control's is
  closed and lossless. No tolerance moved.
- **MAT-4 step 3 ✅** — the mass-averaged SAR operator is **exact at the
  standard 1 g and 10 g masses** (ratio 1.00000000 vs a 0.5% budget) on a
  sphere sized for IEEE C95.3, with kernel mass conserved to 0.012%. The
  first run failed a gate honestly; a quadrature sweep showed why
  (the averaging ball's surface was under-resolved), and the fix raised
  resolution rather than loosening any budget. Still not a C95.3 claim —
  that needs a solved coil+phantom field.
- **MAT-6 step 5 ✅** — wire refinement at fixed box **withdraws** step
  4's attribution of the drive gap: the projected-vs-pinned ΔX offset was
  finite-wire discretisation error (collapses 215× under refinement), and
  roughly a third of the landed 1.58% ΔR error was the wire. The landed
  claim doesn't move; its error budget is now attributed. The `h/r_wire ≥ 16`
  target is measured unreachable on this machine (OOM at 1.46M cells).
- **16:30 slot — drain stop.** All three queue items were done, so the
  slot stopped and journalled per protocol. It also found that §9's intro
  promised a fallback sentence that never existed (fixed this review) and
  did the branch-content homework below.

Audits: both ✅ flips (MAT-4 step 3, MAT-6 step 5) verified §4-compliant by
independent read-only auditors — every claimed number found in the harness
logs, elapsed recorded, no gate loosened; the one failing log and the OOM
probe are preserved in the record, which is how it should look. Branch
hygiene: the superseded 3b-x-b branch deleted after an in-review content
check (+852/−3, strictly additive — ancestry alone would have wrongly said
"keep both"); the 3b-xii branch stays as the single live PORT-1 lineage.

## Automation health

- The grid has run clean since 08-05 15:30Z — 28 consecutive slots, seven
  4/4 implementer slates in a row.
- Tree clean at review start and end; no `recovered/*` branches; one
  `attempt/*` branch (the live PORT-1 lineage, deliberate).
- The 16:30 drain was the queue's own honesty rule working: the 10:30
  review listed 3 ready items rather than inventing 5, and the fourth
  slot stopped cleanly rather than improvising held-back work.
- **Queue depth is back to 5** — two successors scoped from today's
  measurements, one example obligation, two diagnosis steps on old
  baseline debt. All five mutually independent.

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-xiii** — the σ ladder on the control: make loss or
   gap own the 3% residual. Lands the whole port-voltage branch onto
   `main` if loss owns it; escalates to the weekly review if not. Either
   outcome is a finding.
2. **EX-3** — first SAR example: point vs 1 g/10 g mass-averaged SAR in
   ParaView, asserting today's gated record through the runner path.
3. **MAG-6 step 1** — finally execute the never-run coil+phantom symmetry
   metric, as a discriminator for the boundary-mirror hypothesis
   (known-issues 4). In-phase: this is the B1+ fixture.
4. **OPS-12** — adjudicate the residual-trend classifier (known-issues 2,
   one of the last two never-diagnosed baseline failures) and return its
   file to CI.
5. **MAT-6 step 6** (spare, heavy) — test the additivity hypothesis step
   5 raised: both knobs at once, memory-probed first.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
