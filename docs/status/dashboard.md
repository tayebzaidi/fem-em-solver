# FEM-EM Solver — status

**Updated:** 2026-09-11 18:00 daily review. Headline: **all four slots
since 10:30 did chunk work** — two rows closed and both passed audit, and the
queue is refilled with five items.

What the slots found:
- **`OPS-45` ✅ — the harness can no longer call a red window green.** A
  failed pytest whose command still exits 0 is now caught by its final
  `[capture] rc=` line. Checked against the pre-change harness, which still
  shows the bug.
- **`PORT-19` ✅ — one factorisation per sweep.** The 32-port birdcage sweep
  now factors once and back-substitutes 31 times. It reproduces the per-drive
  32×32 to 2e-11 relative, and its solve time fell 11× (158 s → 14 s per half
  on this fixture). This is what makes a human-scale 32-port sweep fit a
  window.
- **`PORT-14` at 64 MHz: negative result.** With a 100 pF capacitor
  terminating one port, the circuit-reduction identity misses by 1.35 %,
  above the 1 % stop line. The inductor and resistor stay under 0.1 %. No
  64 MHz record is registered, so the circuit-layer tuning gate stays closed.
- **`WF-6` ×0.0095 B₁⁺ rung: cause located.** The ≈ 2 % power-accounting
  miss is exactly the terminal-current sheet form under-counting a non-uniform
  sheet field. The review kept the gate: the exact form would make it an
  identity that cannot fail. Why the non-uniformity doubles on that mesh is
  the next item.

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
   has been Up for 27 h.
5. 🟢 **For the 09-13 weekly (no action):** the step-2d Larmor verdict;
   `TH-11` step 5d's §2 sentence; `TH-19` outcome (a); the four-point `ANS-4`
   fit if item 1 lands; `PORT-14`'s 64 MHz capacitor residual and what items 2
   and 5 read from it.
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
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; **self-consistency only** | flag-on ladder C4-clean to ×0.45 (`ANS-4` step 2a″); factor reuse reproduces the 4×4 exactly and the 32×32 to 2e-11 (`PORT-19` ✅) |
| Lumped RLC | 🟡 10 MHz floor registered; **64 MHz capacitor residual 1.35e-2, not registered** | items 2 and 5 diagnose |
| B₁⁺ | 🧪 symmetry-gated at CG1; ladder on `main` 5.25% → 2.07% | ×0.0095 power miss = terminal-form sheet deficit (located, not explained); item 3 |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Test-suite trust | ✅ residual reds at `-n 2`: **3** deliberate/known | harness now honours a final capture rc line (`OPS-45` ✅) |

## Recent activity (2026-09-11 10:30 → 18:00)

- **12:00:** `OPS-45` landed and closed. Gate 4 s; regressions 16 s and 6 s.
- **13:30:** `PORT-14` step 2 landed as a negative result. Two windows,
  115 s and 111 s.
- **15:00:** `WF-6` step 4i landed. Windows of 198 s and 104 s.
- **16:30:** `PORT-19` step 3 landed and closed the row. Windows of 133 s,
  132 s and 30 s.
- **18:00 review (this one):**
  - `OPS-45` and `PORT-19` audited: both PASS;
  - the `WF-6` exact-form accounting was declined (the gate would become
    unfalsifiable);
  - `PORT-14`'s 64 MHz result was ruled, with two diagnoses scoped;
  - five items queued.

## Automation health

- **Implementer slots: 4 of 4 fired** and all landed work. No window died, no
  ranks were orphaned, and no masked status.
- **XL path:** both queue files are empty.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`), kept. No `recovered/*`.
- **Review model:** `claude-fable-5-1`; no override set.

## On deck (§9 — five items, independent)

1. **`ANS-4` step 2a‴** *(implementer; heavy, 8 ranks, ≈ 7 min)* — a fourth
   rung at ×0.35, testing whether the Richardson fit is asymptotic.
2. **`PORT-14` step 2b** *(implementer; standard, 2 ranks, ≈ 4 min)* — fits
   the termination the field solve actually realised at 10 and 64 MHz, to
   separate a series-reactance error from the width law.
3. **`WF-6` step 4j** *(implementer; heavy, 4 ranks, ≈ 6 min)* — maps where
   on the port sheets the ×0.0095 field non-uniformity sits.
4. **`PORT-19` step 4** *(implementer; heavy, 2 ranks, ≈ 10 min)* — the three
   untested sweep-caller modules on the new reuse-on default.
5. **`PORT-14` step 2c** *(spare; heavy, 2 ranks, ≈ 4.5 min)* — the width
   lever at 64 MHz, skipped if item 2 already rules it out.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
