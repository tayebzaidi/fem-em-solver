# FEM-EM Solver — status

**Updated:** 2026-09-10 18:00 daily review. Headline: **your `ANS-4` step 2d XL
window completed, and its record landed (`998edf9`).** The 09-13 weekly owns
the verdict. A tracked-file privacy slip in that commit is Waiting-on-you 1.

The slots: three of four did chunk work.
- **The port-sheet cut is the whole carrier of the read-back asymmetry.** The
  new opt-in `c4_congruent_sheets` mesher flag makes the four port sheets one
  congruent cut, and the read-back spread falls from up to 7e-4 to round-off.
  The next slot tests whether it also fixes the ×0.75 `Z` symmetry break.
- **The progress variable is proven bit-inert** on single-rank solves.
- **The harness can now recover a killed window's log**
  (`run_and_log.sh --capture-orphan`), with the real exit status or an explicit
  "unknown", never a false success.
- 12:00 stopped on the in-flight XL record, as the 10:30 review predicted.

**Still a self-consistency story at the Larmor frequencies:** no absolute SAR,
no C95.3 figure, no homogeneity, no Larmor coil accuracy, no resonance or
tuning, no closed-form B₁⁺ claim, and no solve on the human-scale mesh.
`PROJECT_PLAN.md` is the source of truth; this page is a read-only digest for
the human operator.

## Waiting on you

1. 🔴 **Privacy slip in `998edf9` (ANS-4 step 2d record).** It wrote the
   ours-vs-AED gap percentages into the §7 `ANS-4` row and
   `docs/testing/known-issues.md`. This review redacted both files to the
   qualitative reading. The numbers are still in `998edf9`'s diff; its commit
   message carries none. Push is manual, so decide **before the next push**
   whether that history is acceptable or needs rewriting. The privacy
   pre-commit hook did not catch percentages phrased as a gap, so it may be
   worth tightening.
2. 🟠 **Model watch — tomorrow.** The review override (`claude-opus-5`) expires
   after **2026-09-11**, so the 09-12 03:00 review falls back to Fable by
   itself. If the Fable credits are not back, move
   `REVIEW_MODEL_OVERRIDE_UNTIL`; otherwise that review dies and drains three
   slots (09-08 precedent).
3. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried.)* The spec reuses your
   `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
4. 🟡 **Codex review rollout — paused, yours.** Nothing was activated or
   committed; all reviews still run on Claude. The handoff is at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored). Its
   final all-read-only design was never validated.
5. 🟡 **Both containers were `Exited (137)` around 14:00 CDT**, cause unknown.
   The 15:00 slot restarted `fem-em-solver`. If that was you, no action.
6. 🟢 **The step-2d verdict and `TH-11` step 5d's §2 sentence are the 09-13
   weekly's.** *(No action.)*
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
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅). On the coil, degree 2 still fails the power identity; `TH-19` retests it with the matched source projection |
| Conductor model | 🟡 PEC-hole gap-volume fix on `main` (`TH-15` step 3b), default not flipped | unchanged |
| Coil loading | ⚠️ eddy-current regime only; the 64 MHz bracket sentence is the weekly's | `MAT-6` ✅ Dodd–Deeds; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; **self-consistency only**; ANS-4 AGREE at 10 MHz. At 64/128 MHz the 09-06 verdict was inconclusive; the step 2d reading favours AGREE, and the weekly decides | `GEO-32` 🧪: a congruent sheet cut removes the read-back spread entirely. Next: does it restore ×0.75 `Z` symmetry (§9 item 1) |
| B₁⁺ | 🧪 symmetry-gated at CG1; ladder on `main` 5.25% → 2.07% | unchanged |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Test-suite trust | ✅ residual reds at `-n 2`: 4 deliberate/known | the `-n 2` MUMPS 1-ULP drift is now an observation no gate depends on (2 of 34) |

## Recent activity (2026-09-10 10:30 → 18:00)

- **12:00:** stopped at preflight on the in-flight XL record (designed path).
- **13:30:** `OPS-43` (d) — landed, gate green: 8 of 8 single-rank solves give
  one bit-identical answer with the variable set or unset.
- **15:00:** `GEO-32` — landed, 🧪: the flag gives exactly congruent sheets
  (9.6e-15 m), and the read-back spread drops to ~1e-15 at all three rungs.
  The flag also changes the cell count slightly (116 085 → 116 118).
- **16:30:** `OPS-43` (a) — landed, gate green. A killed wrapper's container
  command finished by itself, and `--capture-orphan` recovered its log with
  exit 3.
- **Operator:** step 2d XL record (14/15 passed; the one failure was a
  measurement-module defect, now fixed; 290 GiB peak); `xl` → three runs a
  week plus a new Saturday `xxl` tier; `PORT-19` and `TH-19` scoped; a Codex
  rollout trialled and paused.
- **18:00 review (this one):** `GEO-32` accepted; `OPS-43` (a)/(d) disclosures
  ratified; privacy redaction; `TH-19` re-priced (step 3 void as written);
  queue refilled with three items.

## Automation health

- **Implementer slots: 4 of 4 fired**, exit 0, no denials, wedges or
  backgrounded windows. One was lost to the XL record (predicted).
- **XL path:** both queue files are empty. Referred to the weekly: step 2d ran
  25 s past its 2 h ceiling because the deadline was lifted by hand.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`); `attempt/OPS-43d` deleted (landed). No `recovered/*`.

## On deck (§9 — three takeable items; fewer than five, stated not padded)

1. **`ANS-4` step 2a′** *(implementer; 4 ranks, ≈ 5 min)* — re-run the ×1/×0.75
   four-port window with congruent sheets. Asserts the imported reciprocity,
   passivity and 0.5% C4 gates; the flag-off run must reproduce the recorded
   ×0.75 break. Also wires the memory report into the ladder module.
2. **`PORT-19` step 1** *(implementer; smoke, 2 ranks)* — prove the sweep's
   system matrix is bit-identical across the four drives, the premise for
   factorising once per sweep.
3. **`TH-19` steps 1–2** *(implementer; heavy, 8 ranks, ≈ 20 min)* — reproduce
   the degree-2 coil power-identity red, then retest with the matched source
   projection at the unmoved 1e-9 bound.
4. 🚫 `OPS-43` (c) — folded into item 1.

A fourth slot that finds nothing takeable stops and journals. That is the
rule, not a failure.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
