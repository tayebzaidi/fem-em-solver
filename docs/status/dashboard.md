# FEM-EM Solver — status

**Updated:** 2026-09-18 03:00 daily review (Friday; Thursday was an off
day). Headline: **Wednesday's first slot consumed the whole four-item queue
by itself — the F-human port-set knob, `OPS-48` ✅ (the silently disabled
VTX read-back gate restored) and `OPS-49` ✅ (a time-series XDMF writer) —
and the other three slots each drew one setup figure. Two unattended XL
windows ran and passed: `ANS-4` step 3b (128 MHz, degree 2, congruent cut;
1539 s, 273 GiB) and step 3c (10 MHz, degree 2; 1603 s, 285 GiB).** Both
closures audited PASS. One reading to flag from the 10 MHz window: every
gate passes, but the degree-2 **self-class C4 spread reads 0.445 % against
its 0.5 % band** (0.199 % on the same mesh at 64 MHz) — not red, not
attributed; the discriminating window is queued for 09-23. The XL results
are recorded, not adjudicated: the private comparisons and the decision
rules are the Saturday 09-19 weekly's.

**Still a self-consistency story at the Larmor frequencies for degree-1
figures:** the order-matched 4×4 is externally checked at 128 MHz; the
64 MHz and 10 MHz order-matched rungs now exist but the AED comparisons are
not yet read. "Tuned" means series resonance on one F-small fixture at one
frequency. No absolute SAR, no C95.3 figure, no homogeneity, no closed-form
B₁⁺ claim, no absolute S on a copper coil. `PROJECT_PLAN.md` is the source
of truth; this page is a read-only digest for the human operator.

## Waiting on you

1. 🔴 **Privacy slip in `998edf9` (ANS-4 step 2d record).** *(Carried.)* The
   ours-vs-AED gap percentages were redacted from the tracked files, but they
   are still in that commit's diff. Decide **before the next push** whether to
   rewrite that history.
2. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried; ready since 09-09.)* The
   spec reuses your `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
3. 🟠 **For the Saturday 09-19 21:00 weekly — what it now owns:**
   (a) **adjudicate three `ANS-4` XL windows** against the private AED
   columns under their pre-registered rules — step 3 (64 MHz), step 3b
   (128 MHz on the congruent cut: class spreads an order tighter, 0.006–0.009 %),
   step 3c (10 MHz: two-rung move 4.4 / 1.4 / 1.1 %, self spread at 89 % of
   its band); (b) read tonight's **XXL** `WF-7` step 0b window (F-human
   degree 2) and commission the next XXL — **0 XXL entries ahead after
   tonight**; (c) `TH-17` step 1, `ANS-6`'s SPEC, the Tier B decision — the
   daily queue is **178 slot-minutes and two items short of its floor** with
   nothing else it may queue, so slots drain into setup figures until the
   weekly opens more physics. No action from you unless you want the order
   changed.
4. 🟡 **`example-runner` should not be able to spawn agents — an
   agent-definition change only you (or an interactive session) can make.**
   On 09-16 07:30 a runner *delegated* to a background runner and returned
   in 46 s; the slot caught it and resumed it as the executor. On 09-16
   09:00 a runner reported "no deviations" over a figure whose caption made a
   false geometric claim — caught only because the slot viewed the PNG. The
   queue item now says "do not spawn" and "Read the PNG before committing";
   the durable fix is in `.claude/agents/example-runner.md` (not writable
   from scheduled reviews): no Agent tool, "census **before** any file is
   written", "never return with a window still running", "view the figure".
5. 🟡 **XL / XXL windows ahead — information only.** Sat 09-19 **XXL** `WF-7`
   step 0b (F-human degree 2, ≈ 235 GiB predicted); Sun 09-20 `ANS-4` step 3d
   (64 MHz degree 2 on the congruent cut); Mon 09-21 `WF-7` step 0c (F-human,
   all 32 ports, cost probe — the two-drive window extrapolates to ≈ 3.5 min
   and ≈ 17 GiB); Tue 09-22 `ANS-4` step 3e (64 MHz on the four-rung ladder,
   the *h*-convergence statement under the 64 MHz rung, ≈ 35–60 min); Wed
   09-23 step 3f (10 MHz degree 2 on the congruent cut — the discriminator
   for the near-band self spread). The weekly may reorder by renaming files.
6. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
7. 🟢 **`ANS-3` AED run** — behind item 2 (since 08-16).
8. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
9. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12.) **Its
   regenerator is broken on the current image** — `scripts/probes/post4_step5_probe.py`
   still calls the removed `adios2.ADIOS()`; `OPS-50` (today's item 1) ports
   it. Wait for that before regenerating.

Nothing new is blocked on you.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅) — production order to the weekly |
| Conductor model | ✅ two routes gated (`TH-14` ✅ 2026-09-14): the birdcage as a PEC hole and copper as a Leontovich surface (cavity Q vs Pozar +0.010 %, Dodd–Deeds copper slab ΔR −0.30 %) | one loop, one liftoff, 10 MHz for the floor; no absolute S on a copper coil (`ANS-6`) |
| Coil loading | 🟡 measured flat in f across 10–64 MHz on one XL window — a record, not a gate | `MAT-6` ✅ Dodd–Deeds at 10 MHz; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; order-matched 4×4 externally checked (AGREE at 128 MHz, by mechanism at 64 MHz); order-matched rungs now exist at all three frequencies (two-rung moves 4.4 / 1.4 / 1.1 % at 10 MHz, 6.5 / 2.6 / 4.1 % at 64 MHz, 5.7 / 4.5 / 6.7 % at 128 MHz on the congruent cut), adjudication 09-19 | degree-1 entries at 128 MHz sit 5–7 % from the order-matched value; the 10 MHz degree-2 self spread is at 89 % of its C4 band (cut off) |
| Lumped RLC / circuit layer | ✅ `PORT-14`, `PORT-15` — capacitors in the model, `C_tuned` from the stored 4×4, in-model tuned `S₁₁` to 8.3e-5 | series resonance on one fixture at 64 MHz, not matched; mode spectrum is `TH-17` |
| Multi-port drive | ✅ `POST-6` — 32-port ccw quadrature C16-invariant (0.81 %) | 10 MHz only |
| B₁⁺ | ✅ `WF-6` — two-rung convergence statement (5.25 % → 2.07 %) | a convergence statement only |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | no absolute or compliance claim |
| Human-scale mesh | 🧪 priced (`WF-7` step 0): one degree-1 drive 37 s / 10.9 GiB at 8 ranks; a second drive on the held factor costs 0.59 s (step 0c); degree 2 runs in tonight's XXL window; the full 32-port set 09-21 | no field asserted |
| Examples | **54 runnable**, census clean; **14 of 54 guides have a setup figure** (`EX-57`, recurring; 40 owed) | a time-series XDMF writer now exists (`OPS-49` ✅); `EX-56` cannot use it (two meshes) |
| Test-suite trust | ✅ residual reds at `-n 2`: 3 deliberate/known; the VTX read-back gate executes again (`OPS-48` ✅) | two defects found by this review's reading, neither live-red: the same gate is still skipped if the *writer* fails (`OPS-50`), and six log labels hardcode "-n 2" / "128 MHz" (`OPS-51`) |

## Recent activity (2026-09-16 03:00 → 2026-09-18 03:00)

- **04:30 slot (five items):** `WF-7` step 0c — the `FEM_EM_WF7_PORTS` knob,
  flag-off control reproduces step 0's digits, 2×2 reciprocity 9.8e-16
  (158 + 155 s); **`OPS-48` ✅** — read-back rel 0.000e+00 on `mag:1` /
  `mag:2`, control 1.000e+00, the failure path now raises (7 + 136 s);
  **`OPS-49` ✅** — `write_xdmf_time_series`, count identity and `h5py` round
  trip exact, 186 lines added, 0 deleted (2 s); figures for `mag:5`, `mag:6`.
- **06:00 / 07:30 / 09:00 slots (fallback):** figures for `mri:1`, `mri:2`,
  `mri:3` (census 45 → 40). Two runner defects caught in-slot (item 4 above).
- **Operator (09-16):** `checkin.sh` lists the XL FIFO.
- **XL 02:00 (09-17):** `ANS-4` step 3b — 15 passed / 1 skipped by design,
  1539 s, 273.1 GiB. **XL 02:00 (09-18):** step 3c — 16 passed, 1603 s,
  284.8 GiB. Both committed by cron.
- **03:00 review (this one):** two closures audited PASS; both XL rows
  filled from `log-pathologist` readings and the pending entries marked RUN;
  the `adios2` survey `OPS-48` left open was done (three files; two
  findings → `OPS-50`); the label defects → `OPS-51`; three XL windows
  queued (one READY entry, two new priced variants); three items queued,
  shortfall stated.

## Automation health

- **Implementer slots: 4 of 4 fired Wednesday, all did chunk work, 9
  commits, 0 parked.** No window died, no orphaned ranks (`pgrep -c python3`
  = 0 recorded after the heavy windows), no masked status. Take-next carried
  04:30 through five items; the other three slots ran the one-figure
  fallback and stopped, as designed — **three of four slots had no physics
  to take.**
- **Reviews:** this one ran on `claude-fable-5-1`, no override. Shell `grep`
  on log files is denied in the review sandbox; log readings went through
  `log-pathologist`. Next: Saturday 09-19 03:00 daily; the weekly is
  Saturday 09-19 21:00.
- **XL:** **3 of 6 windows used in the trailing 7 days (09-16, 09-17,
  09-18), 4 entries ahead (floor 4) — met:** queued 09-20, 09-21, 09-22,
  09-23. **XXL:** 1 ahead (tonight, 09-19) — met; 0 after it runs. The FIFO
  has now run three nights unattended: file taken, run, consumed, committed.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`, kept on the 09-09 ruling). No `recovered/*`.
- **Examples:** 54 runnable, census clean; setup figures 14 / 54.

## On deck (§9 — three items, 62 predicted slot-minutes, floor 240 and ≥ 5 items: shortfall 178 min and two items)

All three are independent.

1. **`OPS-50`** *(≈ 7 min of windows)* — a `B` writer failure raises in
   `mag:1` / `mag:2` (proved by a monkeypatched-writer control: non-zero now,
   exit 0 at the pinned pre-change file), and `post4_step5_probe.py` ported
   to `adios2.bindings`; retires the known-issues entry.
2. **`OPS-51`** *(≈ 1–2 min)* — the six hardcoded "-n 2" / "128 MHz" log
   labels print the real values; a unit guard (6 → 0) and the ladder's
   `-n 8` record control; retires the known-issues entry.
3. **`EX-57` figure** — `meshing/01_two_torus_ports.py` (the recurring
   setup-figure item; every drained slot draws the next).

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
