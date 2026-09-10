# FEM-EM Solver — status

**Updated:** 2026-09-10 10:30 daily review. Headline: **your `ANS-4` step 2d XL
window is running now, and nothing will commit its record when it finishes.**
It started at 15:20:49Z through a direct harness call, not through
`xl-run.sh`. It returns by ≈ 17:21Z (12:21 CDT) at the latest.

In the slots, three of four did chunk work:
- the port-sheet `'+'`-side hypothesis was **excluded**: the sheets' normals
  are azimuthal, so the mechanism does not exist. The plan's premise was the
  review's misreading, and the probe's premise check caught it in under
  4 minutes;
- the harness now **refuses to start while ranks survive** in the target
  container (exit 75);
- the progress-variable gate was **blocked by its instrument**: the complex
  MUMPS smoke solve drifts by 1 ULP run-to-run at 2 ranks. A census this
  review finds no existing record tight enough to be exposed;
- the 09:00 slot found the queue drained and stopped, as the rule says.

**Still a self-consistency story at the Larmor frequencies:** no absolute SAR,
no C95.3 figure, no homogeneity, no Larmor coil accuracy, no resonance or
tuning, no closed-form B₁⁺ claim, and no solve on the human-scale mesh.
`PROJECT_PLAN.md` is the source of truth; this page is a read-only digest for
the human operator.

## Waiting on you

1. 🔴 **Commit the 15:20Z `ANS-4-step2d` window's record once it returns.**
   - **State:** the tree currently holds its harness-appended `xl-ledger.md`
     row and the untracked `docs/testing/logs/20260910T152049Z_ANS-4-step2d.log`,
     preflight only. This review left both uncommitted on purpose, because the
     log has no footer yet.
   - **Owed:**
     - commit the footered log, its test-results row and the ledger row;
     - fill the ledger's last four columns from the footer: ranks, cells,
       peak memory and elapsed, plus the readout. Check the XL container's
       creation time against the window start before attributing
       `memory.peak` (§5.1). Write no AED number;
     - stop `fem-em-solver-xl`.
   - **If it is still uncommitted at 12:00:** that implementer slot stops at
     preflight, and the 13:30 slot parks the record on `recovered/*` for the
     18:00 review. Nothing is lost, but two slots are.
   - **Context:** option (a) from the last dashboard was taken — execute bit
     restored, override re-dated to 09-11, CI check added. The queue is empty
     now, so tonight's 02:00 runs nothing.
2. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried, unchanged, still the
   highest-value AED item.)* The spec reuses your `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
   Pointwise SAR and phantom power are the adjudicating rows. Nothing is
   rescaled on either side.
3. 🟠 **`TH-11` step 5d's §2 sentence and the step-2d verdict are the 09-13
   weekly's.** *(No action.)*
4. 🟡 **Agent-definition edits.** *(Carried.)* Five one-liners for
   `example-runner.md`, `mesh-probe.md` and `implementer.md`, plus
   `implementer.md`'s missing "Last verified against" footer.
5. 🟢 **Model watch.** The review override (`claude-opus-5`) is dated through
   **2026-09-11**, and the first 09-12 session falls back to Fable by itself.
   If the Fable credits are not back by then, move
   `REVIEW_MODEL_OVERRIDE_UNTIL`; otherwise the 09-12 03:00 review dies and
   drains three slots (09-08 precedent).
6. 🟢 **`ANS-3` AED run** — behind item 2. Same low-order and private-results
   rules.
7. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
8. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12;
   `scripts/probes/post4_step5_probe.py` regenerates.)

## Honest current state (digest of §2 — **unchanged this interval**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% (`TH-12` ✅) |
| Conductor model | 🟡 PEC-hole gap-volume fix on `main` (`TH-15` step 3b), default not flipped | unchanged |
| Coil loading | ⚠️ eddy-current regime only; the 64 MHz bracket sentence is the weekly's | `MAT-6` ✅ Dodd–Deeds; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; **self-consistency only**; ANS-4 AGREE at 10 MHz, inconclusive at 64/128 | `PORT-18` 🧪 **excluded** the `'+'`-side port mechanism. The surviving lead is that a smooth field's read-back spread tracks the differently cut sheets on the broken meshes. Next: `GEO-32` makes the cut C4-congruent by construction, with no solve |
| B₁⁺ | 🧪 symmetry-gated at CG1; ladder on `main` 5.25% → 2.07% | unchanged |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Test-suite trust | ✅ residual reds at `-n 2`: 4 deliberate/known | New observation: the complex MUMPS smoke solve is not bit-reproducible at 2 ranks (1 ULP, 2 of 22). **No existing record is exposed** — the tightest solve record is 1e-9 relative |

## Recent activity (2026-09-10 03:00 → 10:30)

- **04:30:** `PORT-18` (mesh-probe, 154 + 68 s, no solve) — premise false.
  Side assignment and quadrature were both demonstrably inert. The one lead,
  a read-back spread tracking the broken rungs at 1e-4, goes to `GEO-32`.
- **06:00:** `OPS-43` (d) gate — blocked. The variable is inert wherever the
  solve is reproducible, but a single-pair bit-identity at 2 ranks is
  intermittently red for an unrelated reason. The slot correctly refused to
  close on the green windows.
- **07:30:** `OPS-43` (b) — landed, gate green: refusal exit 75 naming the
  probe PID with no row written; proceeds once the probe is gone.
- **09:00:** queue drained; stopped and journaled.
- **Operator, 10:14–10:20:** XL launcher fixed (execute bit, lock path, docker
  preflight). First hand-fired window died in 0 s (row kept); the second is
  running.
- **10:30 review (this one):**
  - `PORT-18` disposition;
  - `OPS-43` (d) anchor re-registered at child `-n 1` (still `==`, no
    tolerance);
  - exposure census, no record exposed;
  - `GEO-32` opened;
  - `OPS-43` (a) queued.

## Automation health

- **Implementer slots: 4 of 4 fired**, exit 0, no denials, wedges, orphans or
  backgrounded windows. One was lost to a drained queue — the 03:00 review had
  queued three takeable items for four slots and said so.
- **XL path:** the launcher is now executable and preflights docker. It still
  enforces no 7-day interval on the cron path — referred to the 09-13 weekly,
  as are four ledger rows in two days under the dated override.
- **Tree:** dirty with the in-flight XL record (Waiting-on-you 1), not a
  stall.
- **Branches:** 5 `attempt/*` — `OPS-43d` (new, feeds item 1), plus
  `TH-15-step2proper` and `WF-6-step4b/4c/4e`. No `recovered/*`.

## On deck (§9 — three takeable items; fewer than five, stated not padded)

1. **`OPS-43` (d) gate, re-anchored** *(implementer; smoke, ≈ 1 min)* —
   progress variable bit-inert across 8 single-rank child solves, with the
   print legs as controls.
2. **`GEO-32`** *(implementer; meshing only, 2 ranks, ≈ 3–5 min)* — gmsh
   `setPeriodic` forces the four port sheets to one congruent cut. Asserts
   the flag-off build reproduces `GEO-31`, and flag-on congruence ≤ 1e-12 m.
3. **`OPS-43` (a)** *(implementer; smoke)* — `run_and_log.sh --capture-orphan`
   turns a killed window's raw file into a footered log with the real exit
   status.
4. 🚫 `OPS-43` (c) ladder wiring — rides with the next chunk that runs the
   ladder module.
5. 🚫 `ANS-4` step 2d — in flight, yours (Waiting-on-you 1).

A fourth slot that finds nothing takeable stops and journals. That is the
rule, not a failure.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
