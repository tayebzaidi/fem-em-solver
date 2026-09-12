# FEM-EM Solver — status

**Updated:** 2026-09-12 03:00 daily review. Headline: **all four slots since
18:00 did chunk work** — no row closed, four measurements landed, two review
rulings banked, and the queue is refilled with five independent items.

What the slots found:
- **`ANS-4` ×0.35 rung: negative result.** The finer conductor rung passes
  every gate, but the four-rung Richardson fit returns no estimate: the
  step-to-step moves stop shrinking after ×0.6. The old three-point
  extrapolant is retired as a converged reference. The review's reading is
  that the unrefined bulk (fixed 15 mm global size) sets the floor; item 1
  tests exactly that before the 09-13 weekly.
- **`PORT-14` at 64 MHz: one number explains all three residuals.** The
  termination the field solve realises differs from the one it was told by a
  single proportional factor κ ≈ 1.06 % at both 10 and 64 MHz, and the same
  three-figure number appears as the sheet-field non-uniformity `PORT-16`
  measured at 10 MHz. Items 3 and 4 test whether κ *is* that non-uniformity
  and whether the width lever undoes it at 64 MHz. If both hold, a single
  multiplicative correction is the candidate route to the first 64 MHz
  circuit-layer record.
- **`WF-6` ×0.0095 B₁⁺ rung: the excess is located.** Two thirds of it is
  in-plane transverse field, and 42 % of the drive-component variance sits on
  one mid-gap rim facet covering 7 % of the sheet. A no-solve mesh census of
  that facet is queued (item 5); the rung's power gate stays unruled.
- **`PORT-19` regression record: callers green, one intermittent red.** All
  three untested sweep-caller modules pass on the reuse-on default. The
  field half of the reuse test is red at 2 ranks (~4e-11 vs a 1e-12 band) and
  bit-identical at 1 rank. The review ruled it a width re-anchoring, not a
  loosened bound: the comparand itself is not bit-reproducible at 2 ranks
  (MUMPS drift, known since 09-10). Item 2 lands it.

**Still a self-consistency story at the Larmor frequencies:** no absolute SAR,
no C95.3 figure, no homogeneity, no Larmor coil accuracy, no resonance or
tuning, no closed-form B₁⁺ claim, and no solve on the human-scale mesh.
`PROJECT_PLAN.md` is the source of truth; this page is a read-only digest for
the human operator.

## Waiting on you

1. 🔴 **Privacy slip in `998edf9` (ANS-4 step 2d record).** *(Carried.)* The
   ours-vs-AED gap percentages were redacted from the tracked files, but they
   are still in that commit's diff. Decide **before the next push** whether to
   rewrite that history.
2. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried.)* The spec reuses your
   `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
3. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
4. 🟡 **Both containers were `Exited (137)` around 14:00 CDT on 09-10**, cause
   unknown. *(Carried; referred to the weekly.)* No recurrence: `fem-em-solver`
   has been Up for 36 h.
5. 🟢 **For the 09-13 weekly (no action):** the step-2d Larmor verdict, now
   with the ×0.35 negative and (if item 1 lands) the global-size reading;
   `TH-11` step 5d's §2 sentence; `TH-19` outcome (a); `PORT-14`'s κ and the
   multiplicative-correction route to a 64 MHz record (items 3–4); the second
   exposure of the 2-rank MUMPS drift (`PORT-19` step 4).
6. 🟡 **Agent-definition edits.** *(Carried.)* Five one-liners for
   `example-runner.md`, `mesh-probe.md` and `implementer.md`, plus
   `implementer.md`'s missing "Last verified against" footer.
7. 🟢 **`ANS-3` AED run** — behind item 2.
8. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
9. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12;
   `scripts/probes/post4_step5_probe.py` regenerates.)

## Honest current state (digest of §2 — **unchanged this interval**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅). On the coil, degree 2 passes the power identity **only under `"matched"`** (`TH-19`) |
| Conductor model | 🟡 PEC-hole gap-volume fix on `main` (`TH-15` step 3b), default not flipped | unchanged |
| Coil loading | ⚠️ eddy-current regime only; the 64 MHz bracket sentence is the weekly's | `MAT-6` ✅ Dodd–Deeds; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; **self-consistency only** | flag-on conductor ladder C4-clean to ×0.35 (`ANS-4` step 2a‴) but **not in its asymptotic range**; factor reuse reproduces the 4×4 exactly and the 32×32 to 2e-11 (`PORT-19` ✅) |
| Lumped RLC | 🟡 10 MHz floor registered; **64 MHz capacitor residual 1.35e-2, not registered** — a single proportional κ ≈ 1.06 % carries it | items 3 and 4 test κ's origin and the width lever |
| B₁⁺ | 🧪 symmetry-gated at CG1; ladder on `main` 5.25% → 2.07% | ×0.0095 power miss located on one rim facet (not explained); item 5 |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Test-suite trust | ✅ residual reds at `-n 2`: **3** deliberate/known **+ 1 intermittent** (`PORT-19` field half, item 2 retires it) | harness honours a final capture rc line (`OPS-45` ✅) |

## Recent activity (2026-09-11 18:00 → 2026-09-12 03:00)

- **19:30:** `ANS-4` step 2a‴ landed as a negative result. One window, 247 s
  at 8 ranks.
- **21:00:** `PORT-14` step 2b landed. Four windows of 116–122 s.
- **22:30:** `WF-6` step 4j landed. Windows of 199 s and 101 s.
- **00:00:** `PORT-19` step 4 landed. Five windows, 119–217 s; one
  intermittent red isolated to the 2-rank width.
- **02:00:** the Saturday `xxl` slot fired with an empty queue and ran nothing.
- **03:00 review (this one):**
  - no row turned ✅, so nothing to audit;
  - the `PORT-19` field-half red was ruled (re-anchor at 1 rank);
  - the `PORT-14` width-lever item was re-pointed at κ instead of blocked;
  - five independent items queued.

## Automation health

- **Implementer slots: 4 of 4 fired** and all landed work. No window died, no
  ranks were orphaned, and no masked status.
- **XL / XXL path:** both queue files are empty; the `xxl` slot ran nothing.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`), kept. No `recovered/*`.
- **Review model:** `claude-fable-5-1`; no override set.

## On deck (§9 — five items, independent)

1. **`ANS-4` step 2e** *(implementer; heavy, 8 ranks, ≈ 5 min)* — refine the
   global mesh size at fixed ×0.45 conductor grading, to test whether the
   unrefined bulk is the convergence floor.
2. **`PORT-19` step 5** *(implementer; standard, 1 and 2 ranks, ≈ 4.5 min)* —
   land the field-half ruling: assert bit-identity at 1 rank, print at 2.
3. **`PORT-14` step 2d** *(implementer; standard, 2 ranks, ≈ 5 min)* — the
   sheet-field non-uniformity at 64 MHz beside κ: is κ that deficit?
4. **`PORT-14` step 2c** *(implementer; heavy, 2 ranks, ≈ 4.5 min)* — the
   width lever at 64 MHz, now predicted to read −κ.
5. **`WF-6` step 4k** *(mesh-probe; smoke, 1 rank, ≈ 3 min)* — a no-solve
   quality census of the mid-gap rim facet across the three flag-on rungs.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
