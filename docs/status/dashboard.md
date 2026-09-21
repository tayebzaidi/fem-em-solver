# FEM-EM Solver — status

**Updated:** 2026-09-21 03:00 daily review (Monday). Headline: **Sunday's four
slots closed two chain steps and half-closed two more — `PORT-22` ✅ (the tuned
resonance by a driven sweep, circuit-vs-field to 8.3e-5 at all 11 frequencies
44–84 MHz) and `PORT-20` ✅ (the current-drive route now reports the real
S-matrix), both audited PASS; our half of `ANS-6` is on `main`; two items were
parked on questions only a review could answer, and both are ruled and
re-queued today.** Tonight's `xl` window priced the human-scale 32-port solve
at degree 1: one factorisation plus 31 back-substitutions, under four minutes
and 14 GiB — so the first *gated* human-scale item (`WF-7` step 1) is an
ordinary heavy slot, queued first among the physics. Thirteen open items, 425
slot-minutes.

**Still a self-consistency story at the Larmor frequencies for degree-1
figures:** the order-matched 4×4 is externally checked at 128 MHz (AGREE
stands); **at 64 MHz and 10 MHz it disagrees on the self class (`S₁₁`) while
agreeing on the couplings — no absolute `S₁₁` / `Z_in` claim at 10 or 64 MHz**
(known-issues 2026-09-19, `PORT-21`). "Tuned" means series resonance on one
F-small fixture. No C95.3 figure, no homogeneity, no closed-form B₁⁺ claim, no
absolute S on a copper coil. `PROJECT_PLAN.md` is the source of truth; this
page is a read-only digest for the human operator.

## Waiting on you

1. 🔴 **Privacy, before the next push — now four places.** (a) the `ANS-2`
   adjudication commits (`1f3b563`, `e4697e9`, `f5759f5`, `9315634`) state
   *relative agreement levels* against HFSS in tracked files; (b) the §7
   `ANS-3` row's preliminary paragraph (`114db4c`); (c) the ours-vs-AED gap
   percentages in `998edf9`'s diff; (d) *new:* the `OPS-61` row and
   yesterday's version of this page (`9a1f37a`) give a relative size for the
   `ANS-4` / `ANS-6` self-class offset. No raw AED value is in any tracked
   file. The reviews change nothing and repeat no level: **either confirm
   that a relative level is publishable (and the Privacy clause gets a
   sentence saying so) or redact to the bare verdict before pushing.**
2. 🟠 **Rebuild the image when `OPS-60` lands** (`docker compose build`,
   outside the sandbox). The first slot today pins `scikit-rf` in the
   Dockerfile and shows the import failing on the current image; `PORT-23`
   (item 20) cannot start until the rebuilt image passes that test.
3. 🟠 **`ans:3` needs one interactive re-run.** `PORT-20` fixed the
   current-route S-matrix, but `ans:3`'s tracked `metrics.json` /
   `COMPARISON.md` still show the old S table: the script rewrites the
   gitignored private comparison, so no slot may run it (known-issues
   2026-09-20). Also yours when convenient: **CLAUDE.md's "two external
   findings stand open" sentence still names `PORT-20`** — it is closed.
4. 🟠 **`ANS-6` — adjudication is the 09-26 weekly's.** Your AED numbers
   landed 09-20; the daily was not asked to adjudicate and did not open the
   private notes. A degree knob for `ans:6` and the first degree-2 price on
   its mesh are queued (item 23); a private-mode comparison writer for this
   example does not exist yet — say if you want one.
5. 🟠 **For the 09-26 weekly to commission: `OPS-61`, Palace as a second
   independent reference** (your directive 09-20; §7 row written). Also
   waiting on that weekly: `GEO-34` step 1 (STEP import) is not queued yet —
   as written it is more than one slot; the next daily splits and costs it.
6. 🟡 **A reading for the weekly, not a defect:** `TH-17`'s eigen solve finds
   nothing below 129.6 MHz while `PORT-22` finds the tuned zero at
   63.9986 MHz. The eigen module loads all four ports with `C_tuned`; the
   driven sweep feeds port 1. Those are different circuits, so the numbers do
   not conflict — but it means the `TH-17` row's gate "mode 1 at 64 MHz" may
   be mis-posed. No slot re-scopes it.
7. 🟡 **`example-runner` should not be able to spawn agents, and its "no
   deviations" is not evidence.** *(Carried.)* The durable fix is in
   `.claude/agents/example-runner.md` (not writable from scheduled reviews).
   Yesterday a delegated executor parked `TH-17` on a one-second docker
   denial that the slot owner then disproved — same family.
8. 🟡 **Two figure-style choices are yours.** *(Carried.)* Legends collapse
   more than two same-colour entries to `first … last`, and one colour per
   region class cannot show a split between two same-class regions.
9. 🟡 **The harness cannot prove "no orphans" on an XL night** unless the
   command carries its own check (tonight's did: 0 before, 0 after). A
   one-line echo in `scripts/testing/run_and_log.sh` would make it uniform.
   Not queued — no status rides on it.
10. 🟡 **XL / XXL windows ahead — information only.** Tue 09-22 `ANS-4` step
    3e (64 MHz four-rung ladder); Wed 09-23 step 3f (10 MHz degree 2,
    congruent cut); Thu 09-24 step 3g (10 MHz four-rung ladder); Fri 09-25
    `ANS-2` step 4 (phantom h-halving); Sat 09-26 XXL `WF-7` step 0d. Each
    night finds five rows in its trailing week, so none is budget-tight.
11. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
    `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
12. **Information:** the commit-first checkpoint in
    `docs/automation/weekly-review.md` (08-30) still awaits your OK.
13. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12.)
    `scripts/probes/post4_step5_probe.py` writes the `.bp` and reads it back
    exactly; it still ends `PROBE_RESULT FAIL` on an old fixture pin until
    item 26 lands — ignore that line for this purpose.

Nothing new is blocked on you except item 2, which gates only `PORT-23`.
Claude connectors for Gmail, Microsoft 365 and PubMed are unauthorised in
this headless session; nothing here needs them.

## Honest current state (digest of §2 — §2.1 gained two sentences 09-20)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅) — production order: target degree 2, default not flipped, decided 09-26 on the 3e / 3g ladders |
| Conductor model | ✅ two routes gated (`TH-14` ✅): the birdcage as a PEC hole and copper as a Leontovich surface | one loop, one liftoff, 10 MHz for the floor; no absolute S on a copper coil — `ANS-6` both halves landed, adjudication 09-26 |
| Coil loading | 🟡 measured flat in f across 10–64 MHz on one XL window — a record, not a gate | `MAT-6` ✅ Dodd–Deeds at 10 MHz; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; order-matched 4×4 externally checked: AGREE at 128 MHz; at 64 and 10 MHz couplings AGREE, **self class `S₁₁` DISAGREE, open** (`PORT-21`, sensitivity table measured, one variant re-queued); **the two-torus current route now reports `S = z_to_s(Z)`, closed form exact (`PORT-20` ✅ 09-20)** | **no absolute `S₁₁` / `Z_in` at 10 or 64 MHz at either order**; `ans:3`'s tracked tables still pre-fix (Waiting-on-you 3) |
| Lumped RLC / circuit layer | ✅ `PORT-14`, `PORT-15`; **`PORT-22` ✅ 09-20 — the circuit reduction matches the in-model tuned `S₁₁` to ≤ 8.3e-5 at 11 frequencies 44–84 MHz, one `Im Z_in` zero in [60, 64] MHz** | series resonance on one fixture, not matched; the mode spectrum (`TH-17`) has its floor at 129.6 MHz under a different termination — see Waiting-on-you 6; `scikit-rf` engine (`PORT-23`) waits on the image |
| Multi-port drive | ✅ `POST-6` — 32-port ccw quadrature C16-invariant (0.81 %) | 10 MHz only |
| B₁⁺ | ✅ `WF-6` — two-rung convergence statement (5.25 % → 2.07 %) | a convergence statement only |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`); externally checked — `ANS-2` adjudicated AGREE, numbers private | no compliance claim; one fixture, 10 MHz; the phantom h-halving is an `xl` window, 09-25 |
| Human-scale mesh | 🧪 priced (`WF-7`): **degree-1 32-port set = 1 factorisation + 31 held solves, 224 s, 13.8 GiB, 32×32 reciprocity 1.1e-14 (09-21)**; degree 2 is the human-scale order at 3.26 M unknowns, 348 s, 106 GiB per drive; 32 ports at degree 2 on 09-26 | no field asserted; the first gated identities are item 21 (chain H3); degree 1 carries a 5.5 % order caveat |
| Examples | **55 runnable**, census clean; **22 of 55 guides have a setup figure** (`EX-57`, recurring; 33 owed); `EX-61` (the resonance curve) opened | the figure helper refuses an over-long title (`OPS-53` ✅) |
| Test-suite trust | ✅ residual reds at `-n 2`: 3 deliberate/known **+ the artifact pin** (one undeclared `ans6` file; ruled, item 25 closes it). The call-site pin is fixed (`OPS-59` (b)) | open: `OPS-50` (b) — fifth pin ruled today, item 26; the `B` projection is not run-to-run reproducible below ≈ 4e-6 (no gate reads it) |

## Recent activity (2026-09-20 03:00 → 2026-09-21 03:00)

- **04:30 slot:** `TH-17` step 1b — the capacitor sheets do reach the eigen
  pencil, and the loaded spectrum simply has nothing below 129.6 MHz; the
  closed-form loop control could not run as written. **`PORT-20` steps 1–2.**
- **06:00 slot:** **`PORT-22` ✅.** `PORT-21` step 1 measured and parked: the
  sensitivity table is complete, but the halved-grading variant re-meshed
  without the congruent cut and lost C4 symmetry (spread up to 2.4 % against
  the 0.5 % band) — the band was not touched.
- **07:30 slot:** **`ANS-6` runnable half** (PEC cross-check to 3e-13);
  `OPS-50` re-record green on its four pins, stopped on a fifth; `OPS-59`
  call-site pin fixed, artifact pin down from 22 extras to 1.
- **09:00 slot:** **`PORT-20` ✅**; `EX-57` figure for `mesh:8`.
- **Your sessions:** `ANS-6` AED numbers; `PORT-23` / `OPS-60`, `OPS-61`,
  `GEO-34`, `ARCH-1` rows.
- **`xl` 02:00 (09-21):** `WF-7` step 0c — Status 0, 228 s, 12 GiB.
- **03:00 review (this one):** both audits PASS; four rulings (`PORT-21`,
  `TH-17`, `OPS-50`, `OPS-59`); twelve items written; `EX-61` opened; one
  superseded attempt branch deleted. Journal:
  `docs/planning/reviews/2026-09-21-daily.md`.

## Automation health

- **Implementer slots: 4 of 4 fired Sunday, all did chunk work; 9 items
  attempted, 5 complete, 2 half-landed, 2 parked with measurements.** No
  window died, no masked status. One false outage: a delegated executor
  parked on an intermittent one-second docker denial (piped harness calls
  cause it — known-issues 2026-09-20).
- **Reviews:** this one ran on `claude-fable-5-1`, no override. Tuesday is
  off; next daily Wednesday 09-23 03:00.
- **XL: 5 of 6 windows used in the trailing 7 days, 4 entries ahead (floor
  4) — met exactly.** **XXL: 1 ahead (09-26, floor 1) — met.** The FIFO has
  run six nights unattended.
- **Tree:** clean. **Branches:** 6 `attempt/*` (4 kept on the 09-09 ruling, 2
  consumed by items 22 / 26). No `recovered/*`.
- **§9 size:** 53 KB against a ~25 KB target — worse than yesterday; five
  new full-grain items each carry a ruling (journal §8).

## On deck (§9 — thirteen open items, 425 predicted slot-minutes; floor 240 and ≥ 5 items: met)

19. **`OPS-60`** — pin `scikit-rf` in the Dockerfile (then your rebuild).
21. **`WF-7` step 1** *(heavy, ≈ 45 min)* — the human-scale 32×32 gated on
    reciprocity, passivity, the 18 symmetry classes and the exact power
    identity (chain H3).
22. **`PORT-21` step 1b** *(heavy)* — land the `S₁₁` sensitivity table, the
    grading variant rebuilt on the congruent cut (chain F3).
23. **`ANS-6` step 2** *(heavy)* — degree knob, unset digit-identical, first
    degree-2 price on the hole mesh (chain T9b).
24. **`TH-17` step 1c** *(heavy)* — the closed-form LC control on the
    two-torus hole fixture, `L` from the fixture's own driven route (chain T5).
25. **`OPS-59` (a)** · 26. **`OPS-50` step 3b** — the two closers ruled today.
27–30. **`OPS-55` / `-56` / `-57` / `-58`** — the external-review rows:
    collective point-list guard, sweep endpoints, S↔Z singularity, the
    private-leak check on commit messages.
31. **`EX-61`** — the tuned birdcage's resonance curve.
32. **`EX-57` figure** — `meshing/09_birdcage_sixteen_ring_gaps.py`.

*(Item 20, `PORT-23` step 1, waits on the image rebuild and is not counted.)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
