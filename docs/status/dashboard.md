# FEM-EM Solver — status

**Updated:** 2026-09-13 18:00 daily review. Headline: **the most productive
interval on record — four slots, eight of nine queue items landed.**
`WF-6` closed ✅ (Phase 5 exits on F-small: the B₁⁺ two-rung convergence
statement is registered), `POST-6` closed ✅ (the 32-port quadrature drive
is C16-invariant), `OPS-47` closed ✅ (the plan file is 5 546 lines, down
from 9 951; the 4 000-line guide is still not met), `TH-19` step 3 found the
sheet drive identity-clean at degree 2, `TH-15` step 3 solved the birdcage
as a PEC hole through the three port gates, and `WF-7` step 0 priced a
human-scale degree-1 solve at 10.9 GiB / 37 s — well under the prediction.
The one miss, `PORT-14` step 3, was red on a mis-registered comparand that
this review has re-registered; it is item 1 of a fresh nine-item queue
(181 predicted slot-minutes against the 240 floor, shortfall stated).

**Still a self-consistency story at the Larmor frequencies for degree-1
figures:** the order-matched 4×4 is externally checked, but the degree-1
gate fixture's own 128 MHz entries sit 5–7 % from it and every identity
gate passes on them unchanged. No absolute SAR, no C95.3 figure, no
homogeneity, no resonance or tuning, no closed-form B₁⁺ claim; one
degree-1 solve has now touched the human-scale mesh (a price, not a gate).
`PROJECT_PLAN.md` is the source of truth; this page is a read-only digest
for the human operator.

## Waiting on you

1. 🔴 **The Sunday 02:15 weekly has died on the account session limit two
   Sundays running (09-06, 09-13), and this time it took the 03:00 review
   and the 04:30 and 06:00 slots with it.** *(Carried.)* The launcher logs
   read "You've hit your session limit · resets 7:10am". A 65–117-byte
   launcher log is the tell. Nothing in the repo can fix this; either the
   Sunday schedule moves past the reset or the limit does. The Wednesday
   09-09 weekly ran on schedule; the next is Wednesday 09-16 02:15.
2. 🔴 **Privacy slip in `998edf9` (ANS-4 step 2d record).** *(Carried.)* The
   ours-vs-AED gap percentages were redacted from the tracked files, but they
   are still in that commit's diff. Decide **before the next push** whether to
   rewrite that history.
3. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried; ready since 09-09.)* The
   spec reuses your `ANS-4` HFSS project
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`). The
   weekly named the AED queue the longest pole on every absolute claim in §2.
4. 🟠 **For the Wednesday 09-16 weekly, two decisions:** (a) the XL slot —
   `ANS-4` step 3 (the 64 MHz degree-2 rung) is pre-registered in §10 and
   cannot run before Thursday 09-17 02:00 because the trailing-7-day XL
   budget is spent; (b) the **XXL** slot of Saturday 09-19 — `WF-7` step 0's
   reading (10.9 GiB / 37 s for one degree-1 drive at 0.6 M unknowns) is
   the number the weekly needs to commission it or write "not spent" again.
   No action from you unless you want either slot used differently.
5. 🟡 **Codex review rollout — paused, yours.** *(Carried.)* Handoff at
   `logs/automation/codex-rollout-paused-20260910/HANDOFF.md` (gitignored).
6. 🟢 **`ANS-3` AED run** — behind item 3 (since 08-16).
7. **Information:** the commit-first checkpoint in
   `docs/automation/weekly-review.md` (08-30) still awaits your OK.
8. **One click: does ParaView open a DG1 `.bp`?** (since 2026-08-12;
   `scripts/probes/post4_step5_probe.py` regenerates.)

Nothing closed on this list this interval; nothing new is blocked on you.

## Honest current state (digest of §2 — **changed this interval**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77%, power 3.63%; degree 2 gated at 0.1405% on the sphere (`TH-12` ✅). On the coil the matched projection clears the degree-2 identity by five orders (`TH-19` 1–2); **the sheet-driven birdcage is identity-clean at degree 2 without any projection (`TH-19` step 3, 2026-09-13)** — production order to the 09-16 weekly |
| Conductor model | 🟡 PEC-hole route on `main`; **the birdcage as a hole now *solves* with its four ports and passes the three identity gates at 10/64/128 MHz (`TH-15` step 3)** | the step's power anchor is a record, not a gate (terminal-form excess 7.7e-05 W unattributed, known-issues 09-13; step 3c queued); copper (`TH-14`) starts with the cavity-Q gate, item 2 |
| Coil loading | 🟡 measured flat in f across 10–64 MHz on one XL window — a record, not a gate | `MAT-6` ✅ Dodd–Deeds at 10 MHz; `TH-11` step 5d bracket [−2.04%, −0.43%] |
| S-parameters / ports | ✅ 4-leg identities at 10/64/128 MHz; order-matched 4×4 externally checked (AGREE at 128 MHz, by mechanism at 64 MHz) | degree-1 entries at 128 MHz sit 5–7 % from the order-matched value and every identity gate passes on them; factor reuse reproduces the 4×4 exactly (`PORT-19` ✅) |
| Lumped RLC | 🟡 10 MHz floor registered; **64 MHz κ-derived route measured green on (0), (ii), (iii) — parked on a mis-registered comparand, now re-registered** | item 1 lands it; `PORT-14` → ✅ if the three windows reproduce |
| Multi-port drive | ✅ **`POST-6` closed 2026-09-13** — the 32-port ccw quadrature drive on the 16-leg fixture is C16-invariant (0.81 %) and mirror-symmetric (0.68 %) at the 5 % band, exact power identity 4e-15 | 10 MHz only; no homogeneity, absolute or Larmor claim |
| B₁⁺ | ✅ **`WF-6` closed 2026-09-13 — Phase 5 exits on F-small** on the two-rung convergence statement (5.25 % → 2.07 % C4 spread, both falls asserted) | a convergence statement only; the closed-form gate is killed (epitaph in §10); ×0.0095 rung's power residual banked OPEN |
| Coil-driven SAR | ✅ 1 g / 10 g C4-gated at 10 MHz on one fixture (`MAT-4`) | unchanged; no absolute or compliance claim |
| Human-scale mesh | 🧪 **priced (`WF-7` step 0): one degree-1 drive = 607 039 unknowns, 37 s solve, 10.9 GiB summed at 8 ranks; the mesh build (123 s) dominates** | no field asserted; the degree-2 F-human rung (≈ 250–300 GiB predicted) is the real XXL candidate |
| Test-suite trust | ✅ residual reds at `-n 2`: **3** deliberate/known | harness honours a final capture rc line (`OPS-45` ✅) |

## Recent activity (2026-09-13 10:30 → 18:00)

- **12:00:** `WF-6` step 5 landed — `WF-6` ✅. Took `PORT-14` step 3 next
  under the take-next rule: route green, anchor (i) red on the wrong
  comparand, parked on `attempt/PORT-14-step3-…` and marked BLOCKED.
- **13:30:** three items — `TH-19` step 3 (degree-2 identities green on the
  sheet drive), `POST-6` step 3 (`POST-6` ✅), `WF-7` step 0 (F-human cost
  probe, `WF-7` 🧪).
- **15:00:** three items — `OPS-47` step 1 (tooling) and step 2 (four
  narratives moved byte for byte, one commit each, `OPS-47` ✅), then
  `TH-15` step 3 (the birdcage as a PEC hole: three port gates green at
  three frequencies; power anchor red then substituted in-slot).
- **16:30:** the twelve examples crossing the 14-day census window on 09-14
  refreshed, all green, census clean; queue drained at minute 13.
- **18:00 review (this one):** three closures audited (`WF-6` PASS,
  `POST-6` PASS, `OPS-47` PASS on its anchors with one false ancillary
  sentence corrected — a stale line cite the closing commit said did not
  exist); `PORT-14` step 3's comparand re-registered and the sign error in
  §10 fixed; `TH-15` step 3's substituted power anchor ruled a record on a
  `log-pathologist` reading (an identity true by construction on a
  conductor-free mesh) and the unexplained terminal excess filed in
  known-issues; `TH-14` step 1 re-scoped into §7 as the cavity-Q gate and
  `PORT-15` steps 2–3 written into §7 from the weekly's chain; three example
  chunks opened for the three closed gates; nine items queued.

## Automation health

- **Implementer slots: 4 of 4 fired, 4 did chunk work, 8 items landed,
  1 parked.** No window died, no orphaned ranks, no masked status. The
  take-next rule carried three slots past their first item (2, 3, 3 items).
- **Reviews:** 10:30 and 18:00 both ran on `claude-fable-5-1`, no override.
  Next weekly: Wednesday 09-16 02:15.
- **Process findings, both enacted as standing rules (h) and (i) in §9:**
  an executor re-registered a red anchor's comparand in-slot with an
  identity that is true by construction (`TH-15` step 3); a step's closing
  windows ran on a tree edited after them (assert line 329 in the log vs
  352 at HEAD). Neither changed a status; both are now rules.
- **Plan file:** 5 546 lines after `OPS-47` (from 9 951); the 4 000-line
  guide is not met and is not widened — the rest is §9/§10 prose, the
  weekly's.
- **XL / XXL path:** both queue files empty. XL budget frees Thursday
  09-17 02:00; the 09-19 XXL window now has its price (`WF-7` step 0).
- **Tree:** clean. **Branches:** 5 `attempt/*` (`TH-15-step2proper`,
  `WF-6-step4b/4c/4e`, `PORT-14-step3-20260913T172330Z` — the last is
  landed by item 1). No `recovered/*`.
- **Examples:** 48 runnable, census clean; the 09-14 crossing is pre-empted
  by the refresh; next cohort due ≈ 09-27.

## On deck (§9 — nine items, 181 predicted slot-minutes, floor 240)

Unblocked now: 1, 2, 3, 7, 8, 9 (120 min); 4, 5, 6 unblock as 1 and 2 land.

1. **`PORT-14` step 3** *(land the parked branch by path, one constant;
   ≈ 9 min at 2 ranks)* — the κ-derived width route on the re-registered
   anchor; moves `PORT-14` → ✅, unblocks the circuit-layer chain.
2. **`TH-14` step 1** *(code + tests; ≈ 2 min of windows)* — the Leontovich
   wall on the `TH-9` cavity against Pozar's closed-form Q; moves `TH-14`
   → 🟡.
3. **`TH-15` step 3c** *(tests; ≈ 100 s)* — attribute the hole route's
   terminal-power excess with printed per-sheet and non-phantom terms;
   retires or re-heads the new known-issues entry.
4. **`PORT-15` step 2** *(depends on 1)* — the stored 64 MHz 4×4 and gate
   (i) from the circuit side.
5. **`PORT-15` step 3** *(depends on 4)* — the tuning sweep and the
   HFSS + Circuit self-consistency identity; moves `PORT-15` → ✅.
6. **`TH-14` step 2** *(depends on 2)* — the copper birdcage as a
   surface-impedance hole with the σ-ladder bracket to PEC; moves `TH-14`
   → ✅ (or lands the outer-box facet tag as 2a and stops).
7. **`EX-54`** — the birdcage as a PEC hole in ParaView.
8. **`EX-55`** — the 32-port quadrature drive on the 16-leg birdcage in
   ParaView.
9. **`EX-56`** — `|B₁⁺|` spread against resolution, two rungs in ParaView.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact was last republished from this file on **2026-09-11**
(18:00 review content); it lags this file whenever a scheduled review edits it,
until the next interactive session republishes it.*
