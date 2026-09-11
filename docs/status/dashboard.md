# FEM-EM Solver — status

**Updated:** 2026-09-11 03:00 daily review. Headline: **the review model
override expires tonight.** If the Fable credits are not back, tomorrow's
03:00 review dies and the day's slots drain (Waiting-on-you 1).

The slots: three of four did chunk work, and the fourth found the queue empty.
- **The `ANS-4` refinement ladder exists with congruent port sheets.** With
  the `c4_congruent_sheets` flag on, the ×0.75 rung that broke C4 symmetry on
  09-09 passes every imported gate, and the flag-off control reproduces the
  old break to the digit. The next slot walks the ladder to ×0.45 for the
  Richardson estimate.
- **Factorisation reuse is safe on the four-port sweep:** the system matrix is
  bit-identical across the four drives. The next step is to implement it.
- **On the coil, the matched source projection removes degree 2's energy
  explosion**: the power identity passes at 1e-9 on both σ-halves. The
  default path is unchanged; the 09-13 weekly decides.
- `OPS-43` (long-window robustness) is closed ✅ by this review.

**Still a self-consistency story at the Larmor frequencies:** no absolute SAR,
no C95.3 figure, no homogeneity, no Larmor coil accuracy, no resonance or
tuning, no closed-form B₁⁺ claim, and no solve on the human-scale mesh.
`PROJECT_PLAN.md` is the source of truth; this page is a read-only digest for
the human operator.

## Waiting on you

1. 🔴 **Model override — today is the last day.**
   `scripts/automation/review-model.env` returns the reviews to
   `claude-fable-5-1` from the **2026-09-12 03:00** review. If the Fable
   credits are not back, move `REVIEW_MODEL_OVERRIDE_UNTIL` before midnight.
   Otherwise that review dies and three slots drain (09-08 precedent).
2. 🔴 **Privacy slip in `998edf9` (ANS-4 step 2d record).** *(Carried.)* The
   ours-vs-AED gap percentages were redacted from the tracked files at 18:00,
   but they are still in that commit's diff. Decide **before the next push**
   whether to rewrite that history. The pre-commit hook did not catch
   percentages phrased as a gap.
3. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried.)* The spec reuses your
   `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
4. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
5. 🟡 **Both containers were `Exited (137)` around 14:00 CDT on 09-10**, cause
   unknown. *(Carried; referred to the weekly.)* No recurrence this interval.
6. 🟢 **For the 09-13 weekly (no action):** the step-2d Larmor verdict;
   `TH-11` step 5d's §2 sentence; `TH-19` outcome (a), i.e. whether
   `"matched"` becomes the degree-2 default.
7. 🟡 **Agent-definition edits.** *(Carried.)* Five one-liners for
   `example-runner.md`, `mesh-probe.md` and `implementer.md`, plus
   `implementer.md`'s missing "Last verified against" footer.
8. 🟢 **`ANS-3` AED run** — behind item 3.
9. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
10. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12;
    `scripts/probes/post4_step5_probe.py` regenerates.)

## Honest current state (digest of §2 — **unchanged this interval**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅). On the coil, degree 2 passes the power identity **only under `"matched"`** (`TH-19`); the default path still fails |
| Conductor model | 🟡 PEC-hole gap-volume fix on `main` (`TH-15` step 3b), default not flipped | unchanged |
| Coil loading | ⚠️ eddy-current regime only; the 64 MHz bracket sentence is the weekly's | `MAT-6` ✅ Dodd–Deeds; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; **self-consistency only**; ANS-4 AGREE at 10 MHz; the 64/128 MHz verdict is the weekly's | congruent sheets restore C4 at ×0.75 (`ANS-4` step 2a′); next, the ladder to ×0.45 |
| B₁⁺ | 🧪 symmetry-gated at CG1; ladder on `main` 5.25% → 2.07% | item 4 tests whether congruent sheets return the dropped ×0.0095 rung |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Test-suite trust | ✅ residual reds at `-n 2`: 4 deliberate/known | unchanged |

## Recent activity (2026-09-10 18:00 → 2026-09-11 03:00)

- **19:30:** `ANS-4` step 2a′ landed. Flag on: ×1 and ×0.75 green, 147 s.
  Flag off: the old red reproduced to the digit, 137 s. The memory report is
  now wired into the ladder.
- **21:00:** `PORT-19` step 1 landed. The four drives' port matrices differ by
  exactly 0.0; both controls are live. 62 + 81 s.
- **22:30:** `TH-19` steps 1–2 landed. Default red reproduced; `"matched"`
  passes loaded (2.04e-14) and free (5.94e-15). Three windows of about 8 min
  each at `-n 8`.
- **00:00:** queue drained; stopped and journaled.
- **02:00 XL launcher:** empty queue, nothing ran.
- **03:00 review (this one):**
  - `OPS-43` closed ✅. The auditor flagged only a mis-declared tier (smoke →
    standard), which is corrected.
  - The `ANS-4` known-issues entry is ruled: the flag is required beyond ×1,
    and the mesher default is not flipped.
  - `PORT-19` step 2's negative control is re-specified as a stale factor.
  - A `pgrep` trap is added to the rubric.
  - The queue is refilled with four items.

## Automation health

- **Implementer slots: 4 of 4 fired**, exit 0, no wedges or backgrounded
  windows. One pre-execution denial (a trailing `echo`), retried. One
  orphan-check `pgrep` was denied by the guard; that is now in the rubric.
- **XL path:** both queue files are empty.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`), kept. No `recovered/*`.
- **Review model:** `claude-opus-5` override, last day (Waiting-on-you 1).

## On deck (§9 — four takeable items; fewer than five, stated not padded)

1. **`ANS-4` step 2a″** *(implementer; heavy, 8 ranks, ≈ 10 min)* — land the
   flag guard with its own control, probe ×0.6's cost, then walk
   ×0.75/×0.6/×0.45 with the flag on under the imported gates, and print the
   Richardson estimate.
2. **`PORT-19` step 2** *(implementer; standard, 2 ranks; `src/`)* — factor
   once per sweep. The reused sweep must agree with per-drive to 1e-12, factor
   exactly once, and keep the four-port record at 1e-9; a stale-factor control
   must be caught.
3. **`PORT-14` step 1e** *(implementer; standard, 2 ranks; tests only)* —
   register the weekly-ruled single-mode floor as a record, and retire the
   deliberate red.
4. **`WF-6` step 4h** *(implementer; heavy, 4 ranks, ≈ 6 min)* — re-run the
   dropped ×0.0095 B₁⁺ rung with congruent sheets, against the unmoved 1e-2
   power band.

A fifth slot that finds nothing takeable stops and journals. That is the
rule, not a failure.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
