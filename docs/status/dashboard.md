# FEM-EM Solver — status

**Updated:** 2026-09-20 03:00 daily review (Sunday). Headline: **the weekly's
three chains are now a queue — five independent physics items (the `TH-17`
eigenmode hunt, the current-route S fix `PORT-20`, the driven-sweep resonance
`PORT-22`, the `S₁₁` feed-sensitivity table `PORT-21`, and our half of
`ANS-6`) plus maintenance: nine items, 325 slot-minutes, enough for today's
four slots and into Monday.** Saturday's four slots all did chunk work:
`OPS-52` ✅ and `OPS-53` ✅ (both audited PASS), 16 setup figures rendered or
re-rendered, and two cost probes that did their job — `ANS-2`'s phantom
h-halving re-priced itself to an `xl` night (queued 09-25), and `TH-17`'s
eigen pencil turned out cheap but returned no physical mode near 64 MHz.
Tonight's `xl` window ran green: on the C4-congruent cut at 64 MHz nothing
moves beyond 0.012 points, so the cut is not what separates us from the
external code there.

**Still a self-consistency story at the Larmor frequencies for degree-1
figures:** the order-matched 4×4 is externally checked at 128 MHz (AGREE
stands); **at 64 MHz and 10 MHz it disagrees on the self class (`S₁₁`) while
agreeing on the couplings — no absolute `S₁₁` / `Z_in` claim at 10 or 64 MHz**
(known-issues 2026-09-19, `PORT-21`). "Tuned" means series resonance on one
F-small fixture at one frequency. No C95.3 figure, no homogeneity, no
closed-form B₁⁺ claim, no absolute S on a copper coil. `PROJECT_PLAN.md` is
the source of truth; this page is a read-only digest for the human operator.

## Waiting on you

1. 🔴 **Privacy, before the next push — now three places.** (a) the `ANS-2`
   adjudication commits (`1f3b563`, `e4697e9`, `f5759f5`, `9315634`) state
   *relative agreement levels* against HFSS in tracked files; (b) *new:* the
   §7 `ANS-3` row's preliminary paragraph (`114db4c`, your 09-19 session)
   does the same for the mutual-coupling row; (c) *carried:* the
   ours-vs-AED gap percentages in `998edf9`'s diff. No raw AED value is in
   any tracked file. The reviews change nothing and repeat no level:
   **either confirm that a relative level is publishable (and the Privacy
   clause gets a sentence saying so) or redact to the bare verdict before
   pushing.**
2. 🟠 **`ANS-6` is ready for your AED queue (commissioned by the 09-19
   weekly).** `examples/ansys_benchmarks/ans6_copper_birdcage_four_port_10_64_128MHz/SPEC.md`
   — the `ANS-4` project with only the coil's treatment changed: a copper
   *Finite Conductivity* column and a *Perfect E* column, each at Zero and
   First Order, 10 / 64 / 128 MHz, plus phantom volume loss and coil surface
   loss for port 1. It does not wait for our runnable half — **our half is
   on `main`** (2026-09-20 07:30 slot, item 14 ✅): `metrics.json` and
   `COMPARISON.md` are ready for you to fill the AED columns beside. The PEC
   column is the discriminator for the `S₁₁` finding.
3. 🟡 **`example-runner` should not be able to spawn agents, and its "no
   deviations" is not evidence.** *(Carried.)* The durable fix is in
   `.claude/agents/example-runner.md` (not writable from scheduled reviews):
   no Agent tool, census before any file is written, never return with a
   window running, view the figure and check each caption sentence.
4. 🟡 **Two figure-style choices are yours.** *(Carried.)* Legends collapse
   more than two same-colour entries to `first … last`, and one colour per
   region class cannot show a split between two same-class regions. Say if
   you want per-tag shades or full legends; otherwise nothing changes.
5. 🟡 **The harness cannot prove "no orphans" on an XL night.** Its
   pre-window check is silent when clean and nothing checks afterwards, so
   the ledger's earlier "orphans 0 / 0" wording rests on silence (tonight's
   row says so). A one-line echo in `scripts/testing/run_and_log.sh` before
   and after the window would make it evidence. Not queued — no status
   rides on it; say if you want it as an `OPS` item.
6. 🟡 **This review's sandbox could not reach the docker socket** (one
   attempted unit-test run, denied; nothing else needed it). The 02:00 cron
   window ran normally, so docker itself is up; whether the standard
   `fem-em-solver` service is Up was not observable from here. If the 04:30 slot journals
   the same denial, that is an outage to look at.
7. 🟡 **XL / XXL windows ahead — information only.** Mon 09-21 `WF-7` step
   0c (F-human, 32 ports, degree 1); Tue 09-22 `ANS-4` step 3e (64 MHz
   four-rung ladder); Wed 09-23 step 3f (10 MHz degree 2, congruent cut);
   **Thu 09-24 step 3g (10 MHz four-rung ladder — the weekly's entry 11);
   Fri 09-25 `ANS-2` step 4 (phantom h-halving, ≈ 19 min, ≈ 41 GiB)**; Sat
   09-26 XXL `WF-7` step 0d. 3e and 3g are what the 09-26 weekly needs for
   the degree-2 default decision; 09-24 / 09-25 may each slip a night if a
   week-old row has not aged out by seconds.
8. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
9. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
10. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12.)
   `scripts/probes/post4_step5_probe.py` writes the `.bp` and reads it back
   exactly; it still ends `PROBE_RESULT FAIL` on old fixture pins until
   item 15 of the queue lands — ignore that line for this purpose.
11. **CLAUDE.md follow-up, when `PORT-20` closes:** its "two external
   findings stand open" sentence names `PORT-20`; slots do not edit
   CLAUDE.md, so the clause is yours to retire once item 17 lands.

Nothing new is blocked on you; item 1 gates only a push.

## Honest current state (digest of §2 — unchanged since the 09-19 weekly)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅) — production order: target degree 2, default not flipped, decided 09-26 on the 3e / 3g ladders |
| Conductor model | ✅ two routes gated (`TH-14` ✅ 2026-09-14): the birdcage as a PEC hole and copper as a Leontovich surface (cavity Q vs Pozar +0.010 %, Dodd–Deeds copper slab ΔR −0.30 %) | one loop, one liftoff, 10 MHz for the floor; no absolute S on a copper coil (`ANS-6`) |
| Coil loading | 🟡 measured flat in f across 10–64 MHz on one XL window — a record, not a gate | `MAT-6` ✅ Dodd–Deeds at 10 MHz; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; order-matched 4×4 externally checked: AGREE at 128 MHz; at 64 and 10 MHz couplings AGREE, **self class `S₁₁` DISAGREE, open** (`PORT-21`); the two-torus current-route `S` is not the 50 Ω S-matrix, its `Z` is right (`PORT-20`, queued) | **no absolute `S₁₁` / `Z_in` at 10 or 64 MHz at either order**; two-rung moves 4.4 / 1.4 / 1.1 % (10 MHz), 6.5 / 2.6 / 4.1 % (64 MHz, with or without the congruent cut), 5.7 / 4.5 / 6.7 % (128 MHz) |
| Lumped RLC / circuit layer | ✅ `PORT-14`, `PORT-15` — capacitors in the model, `C_tuned` from the stored 4×4, in-model tuned `S₁₁` to 8.3e-5 | series resonance on one fixture at 64 MHz, not matched; mode spectrum is `TH-17` (step 1: no physical eigenvalue found near 64 MHz yet; step 1b queued); driven-sweep fallback `PORT-22` queued |
| Multi-port drive | ✅ `POST-6` — 32-port ccw quadrature C16-invariant (0.81 %) | 10 MHz only |
| B₁⁺ | ✅ `WF-6` — two-rung convergence statement (5.25 % → 2.07 %) | a convergence statement only |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`); externally checked — `ANS-2` adjudicated AGREE, numbers private | no compliance claim; one fixture, 10 MHz; the phantom h-halving is an `xl` window, 09-25 |
| Human-scale mesh | 🧪 priced (`WF-7`): degree 2 is the human-scale order (weekly 09-19) at 3.26 M unknowns, 348 s, 106 GiB peak per drive at 16 ranks; 32 ports at degree 1 on 09-21, at degree 2 on 09-26 | no field asserted; the degree-2 terminal power residual (1.1e-2) is an unattributed record until chain step H3 asserts the exact identity |
| Examples | **54 runnable**, census clean; **20 of 54 guides have a setup figure** (`EX-57`, recurring; 34 owed); all 14 clipped-legend figures re-rendered | the figure helper now refuses an over-long title (`OPS-53` ✅) |
| Test-suite trust | ✅ residual reds at `-n 2`: 3 deliberate/known **+ 2 count pins the figure task breaks once per figure** (`OPS-59`, queued: the `OPS-44` artifact pin, red; the `OPS-53` call-site pin, red by inspection) | open: `OPS-50` (b) — re-record licensed today, queued; the `B` projection is not run-to-run reproducible below ≈ 4e-6 (known-issues, no gate reads it) |

## Recent activity (2026-09-19 03:00 → 2026-09-20 03:00)

- **04:30 slot:** `ANS-2` step 4's cost probe fired its own STOP rule (mesh
  360 s + 188 s per drive, 40.9 GiB) → `xl`; `TH-17` step 1's probe passed
  on cost (47.8 s) but the pencil shows only the gradient cluster near
  64 MHz — blocked, continued as step 1b; **`OPS-52` ✅**.
- **06:00 slot (four items):** `OPS-50` step 2 — two instruments agree
  exactly on A and E, B only to 4e-6, inside its own repeat noise;
  **`OPS-53` ✅**; all 14 clipped-legend figures re-rendered.
- **07:30 / 09:00 slots:** figures for `mesh:6` (plus a tag-label fix) and
  `mesh:7`; `ANS-2` step 4a — the resolution knob, digit-identical when
  unset; `xl` entry 10 READY.
- **Your sessions:** `ANS-3` numbers; launcher / harness / XL-isolation
  fixes; `OPS-54`…`58` from the external code review; the current-state
  rules for §9 / §10 and `START_HERE.md`; the `GEO-33` Leontovich note.
- **Weekly 21:00:** verdicts above; chains T / F / H; `ANS-6` commissioned.
- **`xl` 02:00 (09-20):** `ANS-4` step 3d — 16 passed, 1619 s, 281 GiB.
- **03:00 review (this one):** both audits PASS; `OPS-50` re-record
  licensed; `OPS-59` opened; nine items queued; two `xl` entries queued;
  `EX-55`'s stale glyph fixed; §9 cut from 71 KB to 44 KB (journal now in
  `docs/planning/reviews/2026-09-20-daily.md`).

## Automation health

- **Implementer slots: 4 of 4 fired Saturday, all did chunk work, 0
  parked.** No window died, no masked status.
- **Reviews:** this one ran on `claude-fable-5-1`, no override; the weekly
  ran in its new Saturday 21:00 window. Next daily: Monday 09-21 03:00.
- **XL: 4 of 6 windows used in the trailing 7 days, 5 entries ahead (floor
  4) — met.** **XXL: 1 ahead (09-26, floor 1) — met.** The FIFO has run five
  nights unattended.
- **Tree:** clean. **Branches:** 4 `attempt/*` (kept on the 09-09 ruling).
  No `recovered/*`.
- **§9 size:** 44 KB against a ~25 KB target — nine full-rubric items are
  ≈ 24 KB of it; the rest is standing rules (journal §8).

## On deck (§9 — nine open items, 325 predicted slot-minutes; floor 240 and ≥ 5 items: met)

10. **`TH-17` step 1b** *(heavy, ≈ 50 min)* — find the missing eigenmode or
    the defect, with a closed-form LC loop as control (chain T5).
11. **`PORT-20` steps 1–2** *(≈ 35 min)* — the current-drive route reports
    `S = z_to_s(Z)`; closed-form identity at 1e-12 (chain F1).
12. **`PORT-22` step 1** *(heavy, ≈ 50 min)* — the tuned resonance by a
    driven sweep 44–84 MHz, circuit-vs-field identity at every frequency
    (chain T5′).
13. **`PORT-21` step 1** *(heavy, ≈ 45 min)* — the public sensitivity table
    of `S₁₁` to three port conventions (chain F3).
14. **`ANS-6` runnable half** *(heavy, ≈ 45 min)* — `ans:6`, copper and PEC
    columns at three frequencies, AED columns blank (chain T9).
15. **`OPS-50` step 3** — the licensed re-record of the probe's four pins.
16. **`OPS-59`** — the two count pins become identities.
17. **`PORT-20` step 3** — re-record the current route's S-derived records
    (serial on 11).
18. **`EX-57` figure** — `meshing/08_birdcage_sixteen_legs.py`.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
