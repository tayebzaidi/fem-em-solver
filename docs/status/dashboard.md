# FEM-EM Solver — status

**Updated:** 2026-09-11 10:30 daily review. Headline: **the review model
override still expires tonight** (Waiting-on-you 1). All four slots since
03:00 did chunk work, and the queue is refilled with five items.

What the slots found:
- **The `ANS-4` refinement ladder now runs with congruent sheets down to
  ×0.45.** A new guard stops anyone building it without the flag. The ×0.75,
  ×0.6 and ×0.45 rungs all pass the C4 gates, and a three-point Richardson fit
  is printed. That fit is a reading, not a converged value.
- **Factorisation reuse landed.** The four-port sweep factors once and
  reproduces the per-drive `S` exactly (0.0 relative). A deliberately stale
  factor is caught at 1e-2, and the sweep's solve time fell from 23.7 s to
  6.7 s.
- **`PORT-14`'s single-mode floor is now a registered record.** It reproduced
  to ≤ 2.4e-7, and one deliberate red is retired. 64 MHz is next.
- **`WF-6` ×0.0095 B₁⁺ rung: negative result.** Congruent sheets remove the
  split between the two ports, but not the ≈ 2 % common power residual. The
  rung stays out of the ladder.
- **Exit-status slip caught.** That `WF-6` window's log footer says Status 0
  over a failed test, because the capture command dropped `exit $rc`. A
  sweep of all logs shows this is the only record affected. `OPS-45` makes the
  harness catch it.

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
   ours-vs-AED gap percentages were redacted from the tracked files, but they
   are still in that commit's diff. Decide **before the next push** whether to
   rewrite that history.
3. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried.)* The spec reuses your
   `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
4. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
5. 🟡 **Both containers were `Exited (137)` around 14:00 CDT on 09-10**, cause
   unknown. *(Carried; referred to the weekly.)* No recurrence: `fem-em-solver`
   has been Up for 20 h.
6. 🟢 **For the 09-13 weekly (no action):** the step-2d Larmor verdict;
   `TH-11` step 5d's §2 sentence; `TH-19` outcome (a); the four-point `ANS-4`
   fit if item 5 lands.
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
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅). On the coil, degree 2 passes the power identity **only under `"matched"`** (`TH-19`) |
| Conductor model | 🟡 PEC-hole gap-volume fix on `main` (`TH-15` step 3b), default not flipped | unchanged |
| Coil loading | ⚠️ eddy-current regime only; the 64 MHz bracket sentence is the weekly's | `MAT-6` ✅ Dodd–Deeds; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; **self-consistency only** | flag-on ladder C4-clean to ×0.45 (`ANS-4` step 2a″); factor reuse exact on the 4-leg sweep (`PORT-19` step 2) |
| Lumped RLC | 🟡 10 MHz reduction floor registered as a record (`PORT-14` step 1e) | 64 MHz is §9 item 2 |
| B₁⁺ | 🧪 symmetry-gated at CG1; ladder on `main` 5.25% → 2.07% | ×0.0095 still misses power accounting with congruent sheets; item 3 diagnoses |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Test-suite trust | ✅ residual reds at `-n 2`: **3** deliberate/known | one masked footer found (`WF-6` step 4h); `OPS-45` opened |

## Recent activity (2026-09-11 03:00 → 10:30)

- **04:30:** `ANS-4` step 2a″ landed: the guard, then the flag-on ladder to
  ×0.45. Windows took 31 + 141 + 250 s.
- **06:00:** `PORT-19` step 2 landed: factor once per sweep. 92 s gate, with
  regression and caller checks green.
- **07:30:** `PORT-14` step 1e landed: floor record registered, red retired.
  113 s.
- **09:00:** `WF-6` step 4h landed as a negative result. 199 s window.
- **10:30 review (this one):**
  - all four slot results accepted;
  - no ✅ to audit;
  - `OPS-45` opened, with a rubric trap added for the exit-status slip;
  - the `WF-6` known-issues entry ruled;
  - five items queued.

## Automation health

- **Implementer slots: 4 of 4 fired** and all landed work. No window died and
  no ranks were orphaned. One process slip: a capture command without
  `exit $rc` (above).
- **XL path:** both queue files are empty.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`), kept. No `recovered/*`.
- **Review model:** `claude-opus-5` override, last day (Waiting-on-you 1).

## On deck (§9 — five items, independent)

1. **`OPS-45`** *(implementer; smoke, host-only)* — the harness footer honours
   a final `[capture] rc=` line. It is checked against a pinned pre-change
   harness.
2. **`PORT-14` step 2** *(implementer; standard, 2 ranks)* — the
   termination-reduction identity at 64 MHz. It is measured and not
   registered.
3. **`WF-6` step 4i** *(implementer; heavy, 4 ranks, ≈ 4–6 min)* — exact
   power shares on the flag-on rungs, testing whether the ≈ 2 % residual is
   the terminal-form deficit.
4. **`PORT-19` step 3** *(implementer; heavy, 8 ranks, ≈ 5 min)* — the 32-port
   sweep under reuse, matched against the cached per-drive 32×32 to 1e-6.
   Passing it can close `PORT-19`.
5. **`ANS-4` step 2a‴** *(implementer; heavy, 8 ranks, ≈ 7 min)* — a fourth
   rung at ×0.35, testing whether the Richardson fit is asymptotic.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
