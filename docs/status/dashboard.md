# FEM-EM Solver — status

**Updated:** 2026-09-12 10:30 daily review. Headline: **all four slots since
03:00 did chunk work** — no row closed, four measurements landed, four review
rulings banked, and the queue is refilled with five independent items, two of
them inputs to tomorrow's weekly Larmor verdict.

What the slots found:
- **`ANS-4` global ladder: the unrefined bulk is a real contributor.** Holding
  the conductor grading fixed and refining the global mesh size moves every
  S-parameter class by more than the conductor rungs did, and the moves halve
  per rung. The fit's exponent (≈ 3) is higher than degree-1 elements usually
  give, and a three-point fit on this fixture has been refuted once already.
  Two more windows are queued before the weekly: a fourth global rung (item 1)
  and the same ladder at a finer conductor grading (item 3).
- **`PORT-14`: κ is the sheet-field non-uniformity, to 0.3 %.** At 64 MHz the
  ratio the power identity measures agrees with the proportional factor κ to
  −0.3 %; its shift from 10 to 64 MHz has κ's sign at a third of κ's size. The
  width lever at 64 MHz reads −κ to +3 % (C) / −4 % (L), but the C fit is not
  quite of the assumed form. One window (item 2) re-measures the zero point
  and a corrected-width configuration together; if both elements land under
  the band, the weekly has a candidate route to the first 64 MHz circuit-layer
  record.
- **`PORT-19` field half ruled and landed.** The reuse test asserts
  bit-identity at 1 rank and prints at 2 ranks; the intermittent red is
  retired. Nothing is open on the chunk. The last two untested example callers
  get a regression window (item 5).

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
   has been Up for 44 h.
5. 🟢 **For the 09-13 weekly (no action):** the Larmor verdict, now with the
   global-ladder reading and (if items 1 and 3 land) the two-knob picture;
   `TH-11` step 5d's §2 sentence; `TH-19` outcome (a); `PORT-14`'s κ at 64 MHz
   and the multiplicative-correction route (item 2 is its direct read); the
   third draw of the 2-rank MUMPS drift.
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
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; **self-consistency only** | flag-on conductor ladder C4-clean to ×0.35 and global ladder C4-clean to h = 9.5 mm (`ANS-4` steps 2a‴, 2e), **neither in a proven asymptotic range**; factor reuse reproduces the 4×4 exactly and the 32×32 to 2e-11 (`PORT-19` ✅) |
| Lumped RLC | 🟡 10 MHz floor registered; **64 MHz capacitor residual 1.35e-2, not registered** — κ ≈ 1.06 % is the sheet-field non-uniformity to 0.3 % (step 2d) and the width lever reads −κ to a few % (step 2c) | item 2 measures the corrected width at 64 MHz |
| B₁⁺ | 🧪 symmetry-gated at CG1; ladder on `main` 5.25% → 2.07% | ×0.0095 power miss located on one rim facet (not explained); item 4 |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Test-suite trust | ✅ residual reds at `-n 2`: **3** deliberate/known (the intermittent `PORT-19` red retired 09-12) | harness honours a final capture rc line (`OPS-45` ✅) |

## Recent activity (2026-09-12 03:00 → 10:30)

- **04:30:** `ANS-4` step 2e landed. One window, 328 s at 8 ranks; the bulk
  is a real contributor.
- **06:00:** `PORT-19` step 5 landed. Two windows, 111 s and 90 s; known-issues
  entry retired.
- **07:30:** `PORT-14` step 2d landed. Two windows of 93 s and 92 s.
- **09:00:** `PORT-14` step 2c landed. One window, 185 s.
- **10:30 review (this one):**
  - no row turned ✅, so nothing to audit;
  - the four measurements were accepted and their follow-ups scoped;
  - five independent items queued; the 03:00 narrative archived.

## Automation health

- **Implementer slots: 4 of 4 fired** and all landed work. No window died, no
  ranks were orphaned, and no masked status. One slot piped the host-side
  wrapper output (`| tail -3`); the container side was durable-capture and the
  log is intact — disclosed, rule restated in the queue.
- **XL / XXL path:** both queue files are empty.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`), kept. No `recovered/*`.
- **Review model:** `claude-fable-5-1`; no override set.

## On deck (§9 — five items, independent)

1. **`ANS-4` step 2f** *(implementer; heavy, 8 ranks, ≈ 7 min, runs only)* —
   a fourth global rung (h = 7.5 mm) at fixed ×0.45 conductor grading: does
   the fitted exponent hold?
2. **`PORT-14` step 2e** *(implementer; heavy by expectation, 2 ranks,
   ≈ 4.5 min)* — configuration D (κ-corrected widths) at 64 MHz beside an
   in-window zero-point re-measurement.
3. **`ANS-4` step 2g** *(implementer; heavy, 8 ranks, ≈ 7–8 min, runs only)* —
   the same three global rungs at ×0.35: are the two refinement knobs
   separable?
4. **`WF-6` step 4k** *(mesh-probe; smoke, 1 rank, ≈ 3 min)* — a no-solve
   quality census of the mid-gap rim facet across the three flag-on rungs.
5. **`PORT-19` step 6** *(implementer; ≈ 6 min, 2 ranks, runs only)* — the two
   unrun example callers (`ports:3`, `ports:13`) on the reuse-on default.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
