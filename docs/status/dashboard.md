# FEM-EM Solver — status

**Updated:** 2026-09-19 03:00 daily review (Saturday). Headline: **your
evening session adjudicated `ANS-2` AGREE — coil-driven SAR is now
externally checked — and the XXL window priced a human-scale degree-2 solve
at a third of what was predicted: 3.26 M unknowns, 348 s, 106 GiB peak. It
fits the ordinary `xl` service.** On the one driven port `S` moves 5.5 %
between degree 1 and 2; whether that makes degree 2 the human-scale
production order is tonight's weekly's call. Friday's four slots all did
work, but again only the first had a queue to take: `OPS-51` ✅, `OPS-50`
🟡 (half closed; the other half is a probe whose old fixture pins no longer
reproduce), and four setup figures. Both ✅ changes were audited; one
carries a privacy question for you (item 1).

**Still a self-consistency story at the Larmor frequencies for degree-1
figures:** the order-matched 4×4 is externally checked at 128 MHz; the
64 MHz and 10 MHz order-matched rungs exist but their AED comparisons are
not yet read. "Tuned" means series resonance on one F-small fixture at one
frequency. No C95.3 figure, no homogeneity, no closed-form B₁⁺ claim, no
absolute S on a copper coil. `PROJECT_PLAN.md` is the source of truth; this
page is a read-only digest for the human operator.

## Waiting on you

1. 🔴 **Privacy, before the next push — two items.** (a) *New:* the `ANS-2`
   adjudication commits (`1f3b563`, `e4697e9`, `f5759f5`, `9315634`) state
   *relative agreement levels* against HFSS in tracked files — §2.2, §6,
   the §7 `ANS-2` row, §9 item 1, `docs/planning/chunks/ANS-2.md` and the
   case's `SPEC.md` status block — while that same `SPEC.md`'s Privacy
   section, CLAUDE.md and the `ANS-1` / `ANS-4` rows carry only the word
   AGREE with "numbers private". No raw AED value is in any tracked file
   (the auditor checked; `COMPARISON.md`'s AED columns are blank). You wrote
   those lines in session, so the review changed nothing and repeats none of
   them: **either confirm that a relative level is publishable (and the
   Privacy clause gets a sentence saying so) or redact to the bare verdict
   before pushing.** (b) *Carried:* the ours-vs-AED gap percentages still in
   `998edf9`'s diff — the same decision, on history.
2. 🟠 **For tonight's 21:00 weekly — what it now owns:** (a) adjudicate the
   three `ANS-4` XL windows (64 MHz; 128 MHz on the congruent cut; 10 MHz,
   self spread at 89 % of its band); (b) **read the `WF-7` step 0b XXL
   window** — branch (c) is excluded, (a)-vs-(b) compares 5.5 % with
   F-small's 64 MHz moves (6.5 / 2.6 / 4.1 %) — and note the degree-2
   power-accounting residual being worse than degree 1; place `GEO-33`;
   (c) the production-order decision (`TH-19` step 3 has been green since
   09-13 with the ruling owed), `ANS-6`'s SPEC, any amendment of `ANS-2`
   (step 2 was re-classed "optional record" in the closing commit;
   `SPEC.md:28`'s box is unticked). The daily queued an XXL variant for
   09-26 (degree 2, all 32 ports) so the floor holds — rename or delete the
   queue file to replace it.
3. 🟡 **`example-runner` should not be able to spawn agents, and its "no
   deviations" is not evidence.** *(Carried, stronger.)* Four consecutive
   figure slots found a false caption, title or comment the runner had
   passed — each time only because the slot viewed the PNG. The queue items
   carry the instructions; the durable fix is in
   `.claude/agents/example-runner.md` (not writable from scheduled
   reviews): no Agent tool, census before any file is written, never return
   with a window running, view the figure and check each caption sentence.
4. 🟡 **Two figure-style choices are yours.** Legends collapse more than two
   same-colour entries to `first … last`, and one colour per region class
   means a figure cannot show a split between two same-class regions
   (`mesh:4`'s whole subject). Captions cover it today. Say if you want
   per-tag shades or full legends; otherwise nothing changes.
5. 🟡 **XL / XXL windows ahead — information only.** Sun 09-20 `ANS-4` step
   3d (64 MHz degree 2, congruent cut); Mon 09-21 `WF-7` step 0c (F-human,
   32 ports, degree 1); Tue 09-22 `ANS-4` step 3e (64 MHz four-rung ladder);
   Wed 09-23 step 3f (10 MHz degree 2, congruent cut — may slip a night if
   the 09-16 row has not aged out by seconds); **Sat 09-26 XXL `WF-7` step
   0d** (degree 2, all 32 ports; predicted 10–20 min, 105–130 GiB).
6. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
7. 🟢 **`ANS-3` AED run** — next in your AED queue now that `ANS-2` is back
   (ready since 08-16).
8. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
9. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12.) The
   regenerator works again — `scripts/probes/post4_step5_probe.py` writes
   the `.bp` and reads it back exactly — but it ends `PROBE_RESULT FAIL` on
   its old fixture pins; ignore that line for this purpose.

Nothing new is blocked on you; item 1 gates only a push.

## Honest current state (digest of §2 — one clause changed 2026-09-18: `MAT-4` externally anchored by `ANS-2`)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅) — production order to the weekly |
| Conductor model | ✅ two routes gated (`TH-14` ✅ 2026-09-14): the birdcage as a PEC hole and copper as a Leontovich surface (cavity Q vs Pozar +0.010 %, Dodd–Deeds copper slab ΔR −0.30 %) | one loop, one liftoff, 10 MHz for the floor; no absolute S on a copper coil (`ANS-6`) |
| Coil loading | 🟡 measured flat in f across 10–64 MHz on one XL window — a record, not a gate | `MAT-6` ✅ Dodd–Deeds at 10 MHz; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; order-matched 4×4 externally checked (AGREE at 128 MHz, by mechanism at 64 MHz); order-matched rungs exist at all three frequencies (two-rung moves 4.4 / 1.4 / 1.1 % at 10 MHz, 6.5 / 2.6 / 4.1 % at 64 MHz, 5.7 / 4.5 / 6.7 % at 128 MHz on the congruent cut), adjudication tonight | degree-1 entries at 128 MHz sit 5–7 % from the order-matched value; the 10 MHz degree-2 self spread is at 89 % of its C4 band (cut off) |
| Lumped RLC / circuit layer | ✅ `PORT-14`, `PORT-15` — capacitors in the model, `C_tuned` from the stored 4×4, in-model tuned `S₁₁` to 8.3e-5 | series resonance on one fixture at 64 MHz, not matched; mode spectrum is `TH-17` (queued, item 2) |
| Multi-port drive | ✅ `POST-6` — 32-port ccw quadrature C16-invariant (0.81 %) | 10 MHz only |
| B₁⁺ | ✅ `WF-6` — two-rung convergence statement (5.25 % → 2.07 %) | a convergence statement only |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`); **externally checked 2026-09-18 — `ANS-2` adjudicated AGREE against HFSS, numbers private** | no compliance claim; one fixture, 10 MHz; the phantom h-halving diagnostic (`ANS-2` step 4) is queued |
| Human-scale mesh | 🧪 priced (`WF-7`): degree 1 one drive 37 s / 10.9 GiB at 8 ranks, a held-factor drive 0.59 s; **degree 2 priced 2026-09-19: 3.26 M unknowns, 348 s, 106 GiB peak at 16 ranks — `xl`-sized; `S` moves 5.5 % from degree 1 on the one driven port**; 32 ports at degree 1 on 09-21, at degree 2 on 09-26 | no field asserted; the degree-2 power-accounting residual is *worse* than degree 1 (1.1e-2 vs 4.2e-3), unattributed |
| Examples | **54 runnable**, census clean; **18 of 54 guides have a setup figure** (`EX-57`, recurring; 36 owed) | 14 older figures carry clipped legends and are queued for re-render; the figure helper has no title-length guard (`OPS-53`) |
| Test-suite trust | ✅ residual reds at `-n 2`: 3 deliberate/known; the VTX read-back gate now also raises on a writer failure (`OPS-50` (a)); log labels state the real width and frequency (`OPS-51` ✅) | open: `OPS-50` (b) — the DG1 probe runs again but fails its v0.7.2 fixture pins on the 0.11 image; the F-human probe's labels mislead at degree 2 (`OPS-52`) |

## Recent activity (2026-09-18 03:00 → 2026-09-19 03:00)

- **04:30 slot (three items):** **`OPS-50` 🟡** — a `B` writer failure now
  raises in `mag:1` / `mag:2` (control: exit 1 now, exit 0 at the pinned
  pre-change file); the probe port runs but fails its step-4 pins on 0.11
  (9 291 vs 9 261 cells, medians 8–11 % off an untouched 2 % guard).
  **`OPS-51` ✅** — six hardcoded log labels gone, count identity 6 → 0,
  the `-n 8` record control green (68 s). Figure for `mesh:1`, plus a fix
  to the shared helper: every legend it had ever drawn was clipped.
- **06:00 / 07:30 / 09:00 slots (fallback):** figures for `mesh:2`,
  `mesh:4`, `mesh:5` (census 39 → 36), each corrected in-slot after the
  PNG was viewed.
- **Operator session (evening):** `ANS-2` AED numbers landed; a printed-only
  incident-power normalisation fixed; **`ANS-2` ✅ adjudicated AGREE**;
  `ANS-2` step 4 and `TH-17` step 1 queued; the daily review licensed to
  execute enumerated §10 chain steps.
- **XXL 02:00 (09-19):** `WF-7` step 0b — both legs rc 0, 673 s, 106.1 GiB
  peak. Committed by cron.
- **03:00 review (this one):** `OPS-51` audited PASS; `ANS-2`'s evidence
  passes, its privacy question is item 1; the XXL row filled from a
  `log-pathologist` reading; `OPS-50`'s residue ruled *not*
  `record-reconciler`'s (its own 0.5 % drift gate forbids it) and re-scoped
  as a two-instrument measurement; `OPS-52` (probe labels) and `OPS-53`
  (figure title guard) opened with known-issues entries; eight items
  queued, floor met; one XXL variant queued.

## Automation health

- **Implementer slots: 4 of 4 fired Friday, all did chunk work, 6 commits,
  0 parked.** No window died, no orphaned ranks, no masked status. Three of
  four slots again had no queue to take and drew the one-figure fallback —
  today's queue is sized to last the four.
- **Reviews:** this one ran on `claude-fable-5-1`, no override. Next: the
  weekly tonight 21:00, then Sunday 09-20 03:00 daily.
- **XL:** **3 of 6 windows used in the trailing 7 days (09-16, 09-17,
  09-18), 4 entries ahead (floor 4) — met.** **XXL:** tonight's window ran;
  **1 ahead (09-26, floor 1) — met**, written under the daily licence. The
  FIFO has run four nights unattended.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`, kept on the 09-09 ruling). No `recovered/*`.
- **Examples:** 54 runnable, census clean; setup figures 18 / 54.

## On deck (§9 — eight items, 240 predicted slot-minutes; floor 240 and ≥ 5 items: met)

1. **`ANS-2` step 4** *(heavy, cost probe first; ≈ 45 min)* — the phantom
   h-halving diagnostic: does our driven-point C4 sampling scatter collapse
   on a halved phantom rung, and does the integral move.
2. **`TH-17` step 1** *(heavy, cost probe first; ≈ 60 min)* — eigenmodes of
   the loaded F-small birdcage with the PEC coil and the tuned capacitor
   sheets: **the internal "tuned birdcage" milestone** (§10 chain step 5).
3. **`OPS-52`** — the F-human probe's labels say what ran (before the 09-21
   window if a slot can).
4. **`OPS-50` step 2** — run the original step-4 probe beside the step-5
   probe on the 0.11 image; two instruments agreeing is what licenses a
   re-record.
5. **`OPS-53`** — `write_setup_figure` refuses a title it cannot draw.
6. **`EX-57` re-render, leg A** — the five magnetostatics figures.
7. **`EX-57` re-render, leg B** — `mesh:3`, `th:10`, `mri:1–3`,
   `ports:15–18`.
8. **`EX-57` figure** — `meshing/06_birdcage_leg_gaps_port_sheets.py`.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
