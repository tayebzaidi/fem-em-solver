# FEM-EM Solver — status

**Updated:** 2026-09-16 03:00 daily review (Wednesday; Tuesday was an off
day). Headline: **Monday's four slots consumed the whole eight-item queue —
`TH-14` closed ✅ on the Dodd–Deeds copper floor, five examples landed
(`EX-55`, `EX-56`, `EX-58`, `EX-59`, `EX-60`), three setup figures drawn —
and the first cron-queued XL window ran this morning: `ANS-4` step 3, the
64 MHz order-matched degree-2 rung, 16 passed in 1658 s at 281 GiB.** All
six closures audited PASS. The 64 MHz result is recorded, not adjudicated:
the private comparison against your AED column and the pre-registered
decision rule are the Saturday 09-19 weekly's. Under the new XL backlog
licence this review queued three priced variants of that window (09-17,
09-18, 09-20) and wrote one cost probe behind a knob item, so the XL floor
(≥ 4 ahead) is met for the first time.

**Still a self-consistency story at the Larmor frequencies for degree-1
figures:** the order-matched 4×4 is externally checked at 128 MHz; at
64 MHz the order-matched rung now exists (degree 1 → 2 moves 6.5 / 2.6 /
4.1 % by class) but the AED comparison is not yet read. "Tuned" means
series resonance on one F-small fixture at one frequency. No absolute SAR,
no C95.3 figure, no homogeneity, no closed-form B₁⁺ claim, no absolute S on
a copper coil. `PROJECT_PLAN.md` is the source of truth; this page is a
read-only digest for the human operator.

## Waiting on you

1. 🔴 **Privacy slip in `998edf9` (ANS-4 step 2d record).** *(Carried.)* The
   ours-vs-AED gap percentages were redacted from the tracked files, but they
   are still in that commit's diff. Decide **before the next push** whether to
   rewrite that history.
2. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried; ready since 09-09.)* The
   spec reuses your `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
3. 🟠 **For the Saturday 09-19 21:00 weekly, now four things it owns:**
   (a) **adjudicate `ANS-4` step 3** (the 64 MHz degree-2 rung,
   `20260916T070008Z_ANS-4-step3.log`) against the private AED column under
   the pre-registered rule, plus whatever the 09-17 / 09-18 variant windows
   return; (b) `TH-17` step 1 (birdcage eigenmodes) — the first Phase 6
   physics step; (c) `ANS-6`'s SPEC (the copper birdcage in AED) — unblocked
   now that `TH-14` is ✅; (d) the Tier B ladder (`TH-5`) — the daily queue
   is **160 slot-minutes and one item short of its floor** with nothing else
   it may queue, so slots drain into setup figures until the weekly opens
   more physics. No action from you unless you want the order changed.
4. 🟡 **XL / XXL windows this week — information only.** Thu 09-17 `ANS-4`
   step 3b (128 MHz degree 2 on the C4-congruent cut), Fri 09-18 step 3c
   (10 MHz degree 2), Sat 09-19 **XXL** `WF-7` step 0b (F-human degree 2,
   ≈ 235 GiB predicted), Sun 09-20 step 3d (64 MHz degree 2 on the congruent
   cut). Each ≈ 30 min at ≈ 280 GiB except the XXL. A fourth XL entry
   (`WF-7` step 0c, the F-human 32-port cost probe) waits on today's §9
   item 1.
5. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
6. 🟢 **`ANS-3` AED run** — behind item 2 (since 08-16).
7. **Information — for an interactive session, not urgent:** the
   `example-runner` spawn template (`.claude/agents/example-runner.md`,
   not writable from scheduled reviews) should say "census **before** any
   file is written" and "never return with a window still running" — the
   07:30 slot's `EX-59` run broke both and the slot repaired it.
8. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
9. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12;
   `scripts/probes/post4_step5_probe.py` regenerates.)

Nothing new is blocked on you.

## Honest current state (digest of §2 — **changed this interval**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅) — production order to the weekly |
| Conductor model | ✅ **two routes gated (`TH-14` ✅ 2026-09-14):** the birdcage as a **PEC hole** (three port gates at 10/64/128 MHz, terminal-power excess attributed, `TH-15` 🟡 on step 2 only) and **copper as a Leontovich surface** — cavity Q vs Pozar +0.010 %, the copper birdcage's identities with a σ-ladder onto PEC, and the **Dodd–Deeds copper slab as a Leontovich floor: ΔR −0.30 % from the closed form, thin-skin identity 1.00097 vs 1.00095** | one loop, one liftoff, 10 MHz for the floor; no absolute S on a copper coil (`ANS-6`) |
| Coil loading | 🟡 measured flat in f across 10–64 MHz on one XL window — a record, not a gate | `MAT-6` ✅ Dodd–Deeds at 10 MHz; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; order-matched 4×4 externally checked (AGREE at 128 MHz, by mechanism at 64 MHz) — **the 64 MHz order-matched rung now exists** (degree 1 → 2 move 6.51 / 2.60 / 4.11 % by class; 128 MHz read 6.09 / 5.38 / 6.70 %), adjudication 09-19 | degree-1 entries at 128 MHz sit 5–7 % from the order-matched value; factor reuse exact (`PORT-19` ✅) |
| Lumped RLC / circuit layer | ✅ `PORT-14`, `PORT-15` — capacitors in the model, `C_tuned` from the stored 4×4, in-model tuned `S₁₁` to 8.3e-5 | series resonance on one fixture at 64 MHz, not matched; mode spectrum is `TH-17` |
| Multi-port drive | ✅ `POST-6` — 32-port ccw quadrature C16-invariant (0.81 %) | 10 MHz only |
| B₁⁺ | ✅ `WF-6` — two-rung convergence statement (5.25 % → 2.07 %) | a convergence statement only |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | no absolute or compliance claim |
| Human-scale mesh | 🧪 priced (`WF-7` step 0): one degree-1 drive 37 s / 10.9 GiB at 8 ranks; **degree 2 queued for the 09-19 XXL window; the full 32-port set behind today's item 1** | no field asserted |
| Examples | **54 runnable**, census clean; **9 of 54 guides have a setup figure** (`EX-57`, recurring; 45 owed) — five new examples this interval: 16-leg quadrature `B₁⁺`, the `B₁⁺` resolution ladder, the tuned birdcage, the copper birdcage's surface loss, the lossy-wall cavity Q | two helper defects found by them: the `adios2` 2.12 read-back break (`OPS-48`) and the single-timestep XDMF helper (`OPS-49`), both queued |
| Test-suite trust | ✅ residual reds at `-n 2`: 3 deliberate/known | **one silently disabled gate found:** `mag:1`/`mag:2`'s VTX read-back has not executed on the 0.11 image (`OPS-48`, item 2) |

## Recent activity (2026-09-14 03:00 → 2026-09-16 03:00)

- **04:30 slot (three items):** `ANS-4` step 3a — the frequency knob, flag-off
  control to 8e-11 (62 + 63 s); **`TH-14` step 2 → ✅** — the copper slab as
  a Leontovich floor, ΔR −0.299 % vs Dodd–Deeds, identity 1.3e-8, ratio
  9.991, thin-skin 1.00097 (340 s); **`EX-55` ✅** (C16 spread 0.81 %, 168 s).
- **06:00 slot (two + a stop):** **`EX-56` ✅** (spread 5.25 % → 2.07 %,
  142 s); **`EX-58` ✅** (tuned `S₁₁` residual 8.3e-5, 58 s); `EX-59` stopped
  at minute 29 with the facet-field route unresolved, no code, no branch.
- **07:30 slot (four items):** **`EX-59` ✅** (per-adjacent-cell loss, identity
  1.6e-13, 35 s); **`EX-60` ✅** (Q/Q_c +0.010 %, √σ ratio 9.995, 11 s);
  setup figures for `mag:1` and `mag:2` (census 48 → 46); found the `adios2`
  read-back break.
- **09:00 slot (fallback):** setup figure for `mag:4` (census → 45).
- **Operator (09-14/15):** `checkin.sh`; the XL queue became a nightly FIFO
  with a daily backlog floor; `GEO-33` (32-leg F-human rung) filed as
  future work; the `ANS-4` step 3 window queued for 09-16.
- **XL 02:00 (09-16):** `ANS-4` step 3 — 16 passed, 1658 s, 280.8 GiB,
  committed by cron (`1fcb2a8`).
- **03:00 review (this one):** six closures audited PASS; the XL row filled
  and the pending entry marked RUN; §2.1's conductor-model line rewritten
  for `TH-14` ✅; `OPS-48` / `OPS-49` opened from the two helper defects;
  three XL variants queued and one cost probe written; four items queued,
  shortfall stated.

## Automation health

- **Implementer slots: 4 of 4 fired Monday, all did chunk work, 10 commits,
  0 parked.** No window died, no orphaned ranks, no masked status. Take-next
  carried 04:30 through three items, 06:00 through two, 07:30 through four.
  One `example-runner` protocol slip (`EX-59`: post-write census, background
  return) was repaired in-slot — Waiting-on-you item 7.
- **Reviews:** this one ran on `claude-fable-5-1`, no override. Next: Friday
  09-18 03:00 daily; the weekly is Saturday 09-19 21:00.
- **XL:** **2 of 6 windows used in the trailing 7 days (09-10, 09-16), 4
  entries ahead (floor 4) — met:** 3 queued (09-17, 09-18, 09-20) + 1
  pending a knob. **XXL:** 1 ahead (09-19) — met. The FIFO worked on its
  first night: file taken, run, consumed, committed.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`, kept on the 09-09 ruling). No `recovered/*`.
- **Examples:** 54 runnable, census clean; setup figures 9 / 54.

## On deck (§9 — four items, 80 predicted slot-minutes, floor 240 and ≥ 5 items: shortfall 160 min and one item)

All four are independent.

1. **`WF-7` step 0c** *(probe only; ≈ 7 min)* — the `FEM_EM_WF7_PORTS` knob
   with the flag-off control and a two-drive reciprocity assert; unblocks
   the F-human 32-port XL cost probe (the implementer marks the pending
   entry READY in the same commit).
2. **`OPS-48`** *(≈ 3 min)* — restore the `EX-14` VTX read-back gate on
   `mag:1` / `mag:2` for `adios2` 2.12; retires the known-issues entry.
3. **`OPS-49`** *(≈ 1 min)* — a time-series XDMF writer beside
   `write_xdmf_with_tags`, gated on a count identity and an `h5py` round
   trip; retires the known-issues entry.
4. **`EX-57` figure** — `magnetostatics/05_gauge_cross_check.py` (the
   recurring setup-figure item; every drained slot draws the next).

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
