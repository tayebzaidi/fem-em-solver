# FEM-EM Solver — status

**Updated:** 2026-09-14 03:00 daily review (the first under the wind-down
schedule: one review and four slots per active day, Tuesday and Thursday
off, the weekly on Saturday 21:00). Headline: **the nine-item queue of the
09-13 18:00 review was consumed in two slots — seven items landed, two
examples remain.** `PORT-14` closed ✅ (capacitors in the model at 64 MHz on
the κ-derived sheet width), `PORT-15` closed ✅ (the HFSS + Circuit identity:
a tuning sweep on the stored 4×4 picks `C_tuned` and one in-model solve
reproduces the circuit's tuned `S₁₁` to 8e-5), `TH-15` step 3c attributed the
hole route's terminal-power excess to the sheets' own Cauchy–Schwarz deficit
(the known-issues entry is retired), `EX-54` landed the birdcage-as-hole
example, and the copper birdcage solved as a Leontovich surface through the
three port gates at 10 / 64 / 128 MHz with a σ-ladder that converges onto
PEC. **`TH-14` is back at 🟡, not ✅:** the slot closed it on the §9 item's
letter, but the row's own done-when still needs the Dodd–Deeds copper-slab
step, which is now item 2 of the queue. The operator's interactive session
rewired the schedule, opened the recurring setup-figure task (`EX-57`, 48 of
49 guides still owe a figure) and queued the F-human degree-2 probe for the
Saturday 09-19 XXL window.

**Still a self-consistency story at the Larmor frequencies for degree-1
figures:** the order-matched 4×4 is externally checked, but the degree-1
gate fixture's own 128 MHz entries sit 5–7 % from it and every identity
gate passes on them unchanged. "Tuned" means series resonance on one
F-small fixture at one frequency (`R_in` 6.8 Ω, `|S₁₁|` 0.76 — not matched).
No absolute SAR, no C95.3 figure, no homogeneity, no closed-form B₁⁺ claim,
no absolute S on a copper coil. `PROJECT_PLAN.md` is the source of truth;
this page is a read-only digest for the human operator.

## Waiting on you

1. 🔴 **Privacy slip in `998edf9` (ANS-4 step 2d record).** *(Carried.)* The
   ours-vs-AED gap percentages were redacted from the tracked files, but they
   are still in that commit's diff. Decide **before the next push** whether to
   rewrite that history.
2. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried; ready since 09-09.)* The
   spec reuses your `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`). The
   weekly named the AED queue the longest pole on every absolute claim in §2.
3. 🟠 **For the Saturday 09-19 21:00 weekly, three things it now owns:**
   (a) `TH-17` step 1 (birdcage eigenmodes) — §10 chain steps 1–3 are done,
   so the first Phase 6 physics step is the weekly's to write; (b) `ANS-6`'s
   SPEC (the copper birdcage in AED) once `TH-14`'s slab step lands;
   (c) the Tier B ladder (`TH-5` radiation boundary) — the daily queue is
   **76 slot-minutes short of its 240 floor** with nothing else it may
   queue, so the four slots will drain into setup figures (by design) until
   the weekly opens more physics. No action from you unless you want the
   order changed.
4. 🟡 **XXL window Saturday 09-19 02:00 is queued** (`WF-7` step 0b, the
   F-human rung at degree 2, ≈ 235 GiB predicted). The XL budget is open;
   the `ANS-4` 64 MHz degree-2 rung is queued behind a one-slot knob (item 1)
   and goes in on the first review after that lands. Information only.
5. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
6. 🟢 **`ANS-3` AED run** — behind item 2 (since 08-16).
7. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
8. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12;
   `scripts/probes/post4_step5_probe.py` regenerates.)

Closed on this list: the Sunday session-limit item — the weekly moved to
Saturday 21:00 by your directive, so the failure mode it described no longer
exists on the schedule. Nothing new is blocked on you.

## Honest current state (digest of §2 — **changed this interval**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅); the sheet-driven birdcage is identity-clean at degree 2 (`TH-19` step 3) — production order to the weekly |
| Conductor model | 🟡 two routes on `main`: the birdcage as a **PEC hole** passes the three port gates at 10/64/128 MHz and its terminal-power excess is attributed (`TH-15` step 3c — the sheets' 1.06 % Cauchy–Schwarz deficit, known-issues retired); **copper as a Leontovich surface** is gated on the lossy-wall cavity Q (Pozar, +0.010 %) and on the same birdcage's identities with a σ-ladder converging onto PEC (`TH-14` steps 1 and 3) | `TH-14` 🟡 pending the Dodd–Deeds copper slab (item 2); no absolute S on a copper coil (`ANS-6`) |
| Coil loading | 🟡 measured flat in f across 10–64 MHz on one XL window — a record, not a gate | `MAT-6` ✅ Dodd–Deeds at 10 MHz; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; order-matched 4×4 externally checked (AGREE at 128 MHz, by mechanism at 64 MHz) | degree-1 entries at 128 MHz sit 5–7 % from the order-matched value; factor reuse exact (`PORT-19` ✅) |
| Lumped RLC | ✅ **`PORT-14` closed 2026-09-13** — capacitors and inductors in the model at 10 and 64 MHz on the κ-derived sheet width (64 MHz residuals 5.4e-5 / 2.0e-6 under 1e-3) | κ ≈ 1.06 % is the sheet's named systematic; 128 MHz printed only |
| Circuit layer / tuning | ✅ **`PORT-15` closed 2026-09-14** — the HFSS + Circuit identity: `C_tuned` = 15.6 pF from the stored 4×4, in-model tuned `S₁₁` reproduces the circuit's to 8.3e-5 | series resonance on one fixture at 64 MHz, `|S₁₁|` 0.76 — not matched; mode spectrum is `TH-17` |
| Multi-port drive | ✅ `POST-6` — 32-port ccw quadrature C16-invariant (0.81 %) | 10 MHz only; no homogeneity, absolute or Larmor claim |
| B₁⁺ | ✅ `WF-6` — Phase 5 exits on F-small on the two-rung convergence statement (5.25 % → 2.07 %) | a convergence statement only; closed-form gate killed |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Human-scale mesh | 🧪 priced (`WF-7` step 0): one degree-1 drive 37 s / 10.9 GiB at 8 ranks; **degree 2 queued for the 09-19 XXL window** | no field asserted |
| Examples | 49 runnable, census clean; **1 of 49 guides has a setup figure** (`EX-57`, recurring) | one figure per active day plus every drained slot |
| Test-suite trust | ✅ residual reds at `-n 2`: 3 deliberate/known | harness honours a final capture rc line (`OPS-45` ✅) |

## Recent activity (2026-09-13 18:00 → 2026-09-14 03:00)

- **19:30 slot (four items):** `PORT-14` step 3 landed the parked κ route —
  `PORT-14` ✅; `TH-14` step 1 gated the Leontovich wall on the cavity Q
  (+0.010 % vs Pozar, `Q ∝ √σ` to 0.05 %); `TH-15` step 3c attributed the
  terminal excess to `C − terminal` to every digit; `PORT-15` step 2 stored
  the 64 MHz records and gate (i).
- **21:00 slot (three items):** `PORT-15` step 3 — tuning sweep, one
  in-model solve, `PORT-15` ✅; `TH-14`'s copper birdcage — three port
  gates, surface-loss identity to 3e-13, σ-ladder 5.8e7 → 5.8e11 falls 10×
  per 100× σ, coil-loss share 0.93 / 0.45 / 0.22 at 10 / 64 / 128 MHz;
  `EX-54` — the hole example, 34 s. Stopped at minute 34 with `EX-55` next.
- **Operator session (≈ 19:00–21:50):** wind-down crontab; XL budget six
  per week nightly, 4 h ceiling; XL clerk role and `xl-pending.md`; the
  XXL window queued; `EX-57` step 0 (setup-figure infrastructure, census,
  the `mesh:3` exemplar).
- **03:00 review (this one):** four closures audited — `PORT-14` PASS,
  `PORT-15` PASS, `EX-54` PASS, **`TH-14` DEMOTE → 🟡** (its own done-when
  unmet: the Dodd–Deeds slab and the §2.1 line); the slab step queued as
  item 2 and the §2.1 conductor-model line written; `TH-15`'s power
  sentence re-registered on the attributed term; §2.1's RLC / circuit-layer
  sentence rewritten from "not gated" to the two closures; three example
  chunks opened for the closed gates; eight items queued, shortfall stated.

## Automation health

- **Implementer slots: 2 of 2 fired (the last two of the old schedule), both
  did chunk work, 7 items landed, 0 parked.** No window died, no orphaned
  ranks, no masked status. Take-next carried the 19:30 slot through four
  items and the 21:00 slot through three.
- **Reviews:** this one ran on `claude-fable-5-1`, no override. Next: the
  Wednesday 09-16 03:00 daily; the weekly is now **Saturday 09-19 21:00**.
- **Schedule:** the new crontab is installed and the 02:00 XL entry fired
  empty on schedule (`20260914T070001Z_xl-run.log`).
- **Process finding:** a slot flipped a chunk ✅ on its §9 item's letter
  while the §7 row's done-when said more — the executor flagged it, the
  review demoted it. The §9 item, not the executor, was wrong: item 6 said
  "(a)–(c) move `TH-14` → ✅" without reconciling the row. Reviews now
  check the row's done-when before writing a "status it can move" line
  (rule (j) in §9).
- **XL / XXL path:** XL queue empty, budget open (three charged rows in the
  trailing 7 days against six), nothing `READY` to queue — entry 2 waits on
  item 1. XXL queued for 09-19 02:00.
- **Tree:** clean. **Branches:** 4 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e` — kept on the 09-09 ruling; the `PORT-14` branch was
  deleted by its landing commit). No `recovered/*`.
- **Examples:** 49 runnable, census clean; setup figures 1 / 49.

## On deck (§9 — eight items, 164 predicted slot-minutes, floor 240, shortfall 76)

All eight are independent.

1. **`ANS-4` step 3a** *(tests only; ≈ 2.5 min)* — the frequency knob the
   XL command needs, proved by the flag-off control; unblocks the 64 MHz
   degree-2 XL window.
2. **`TH-14` step 2** *(code + tests; ≈ 6 min)* — the copper Dodd–Deeds
   slab as a Leontovich floor under `MAT-6`'s loop; moves `TH-14` → ✅.
3. **`EX-55`** — the 32-port quadrature drive on the 16-leg birdcage in
   ParaView.
4. **`EX-56`** — `|B₁⁺|` spread against resolution, two rungs in ParaView.
5. **`EX-58`** — the tuned birdcage: sweep, `C_tuned`, the in-model field.
6. **`EX-59`** — the copper birdcage: surface loss density on the coil.
7. **`EX-60`** — the lossy-wall cavity: Q against σ beside Pozar.
8. **`EX-57` figure** — `magnetostatics/01_straight_wire.py` (the recurring
   setup-figure item; every drained slot draws the next).

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
