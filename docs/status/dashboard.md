# FEM-EM Solver — status

**Updated:** 2026-09-06 10:30 daily review. Headline: **the account session
limit cost four scheduled sessions overnight — the weekly review lost its
plan work after committing the archive rotation, the 03:00 review never
ran, and two implementer slots never started — and the queue then drained
at 09:00.** The slots that did fire all landed: the lumped-RLC sheet's
1.1% is now fully diagnosed as a field effect of the sheet, not a
mis-measured geometry (no constant enters the law); the PEC sphere as a
hole and the human-scale coil mesh are both in ParaView as examples; the
two-torus hole is a `MeshGenerator` route with every count and area
identity asserted; and the refined Dodd–Deeds fixture reproduced its
0.28% on the current image but parked on two questions this review has
now ruled — it lands next slot. **Still a self-consistency story on one
fixture family at 10 MHz at fixed `h`: no absolute SAR, no homogeneity,
no C95.3, no Larmor coil claim, no convergence claim beyond the
PEC-sphere ladder, no resonance or tuning claim, and no solve has touched
the human-scale mesh.** Source of truth is `PROJECT_PLAN.md`; this page
is a read-only digest for the human operator.

## Weekly review digest (2026-09-02; the 2026-09-06 session was cut off)

- **Pace, 08-30 → 09-02 (2.68 d):** 26 §4-✅ items (10 chunks + 16 steps),
  9.7/day, 62% physics; 30 of 32 implementer slots fired, every loss
  launcher-side (login, CLI pin), none on limits. Full ledger in §10.
- **Phase 5 exit re-assessed to ≈ 09-05…09 on F-small** — watch condition
  met 09-02; the SAR gate itself landed 09-02 19:30.
- **2026-09-06 weekly (02:15):** committed the `attempts.md` rotation
  (4 448 lines archived, the rotation tool landed) and then hit the
  session limit. **Everything else carries to 2026-09-09:** the
  `POWER_BALANCE_BAND` ruling; `ANS-4`'s adjudication and the first XL
  slot; the `GEO-25` re-dating and `TH-16` cost probe; the `PORT-14` band
  re-registration on step 1d's evidence; `TH-15` step 3 proper; the
  `TH-14` step 1 anchor (annotated in §7 by this review); the §7 archive
  rotation and the `attempts.md` window (15 559 lines vs 6 000); and,
  new, re-confirming the `ANS-1` AGREE verdict once the promoted fixture
  lands.

## Waiting on you

1. 🔴 **The account session limit ate four scheduled sessions between
   02:15 and 06:00 today** (`logs/automation/…` for the weekly review, the
   03:00 review and the 04:30 / 06:00 slots all read `You've hit your
   session limit · resets 7:10am`). Nothing broke and nothing was left
   dirty — the weekly's commit-first checkpoint did its job — but the
   weekly's plan work is lost until Wednesday and the schedule's densest
   window (the weekly at 02:15 plus the 03:00 review) sits right where the
   limit bites. Two things only you can decide: whether the 02:15 / 03:00
   pair should move later in the reset cycle, and whether the plan
   allowance is the constraint to relax.
2. ✅ **`ANS-4` replicated 2026-09-04** — both orders in the gitignored
   `aed_results/`, the private-mode run filled `COMPARISON_private.md`,
   the pre-read is in `docs/private/`. No AED number reached a tracked
   file. Nothing for you to do; the 2026-09-09 weekly adjudicates (it was
   the 09-06 weekly's job and was lost with it).
3. 🟢 **`ANS-3` AED run** — the top of your queue. Same low-order rule,
   same private-results handling; the tracked table's AED cells are blank
   by construction.
4. 🟡 **`ANS-1` note, no action yet:** the refined Dodd–Deeds fixture
   lands next slot and moves our ΔR column by ~1.8% relative (the pin
   follows the fixture — ruled today, nothing on the AED side changes).
   The 2026-09-02 AGREE verdict is re-checked privately by the 09-09
   weekly; if the private margin was inside that move you will hear it
   there.
5. 🟡 **Agent-definition edits the sandbox cannot make** (unchanged): two
   lines for `.claude/agents/example-runner.md` (census windows through
   the harness; full-filename guide references), one for `mesh-probe.md`
   (row stays 🧪 until a gate step lands), one for `implementer.md`
   (parking marks the §9 item BLOCKED in the same commit — rule (d)), and
   one for both (an unlabelled failing factor is a negative to report,
   not a call to make in-slot — rule (e); honoured correctly by the 07:30
   slot today).
6. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). It is what saved
   the rotation today; revert only if you want the single-commit form.
7. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
8. FYI, no action — physics worth a glance. **(a)** The lumped sheet's
   1.1% termination-reduction miss is not geometric: every measured sheet
   ratio misses the fitted zero-crossing by ≥ 3.3× the window, and the
   told gap length is reproduced exactly. It is edge fringing — the
   single-mode residual proper. The fit held on a fourth point (residual
   ×0.036), but that number was fitted and closes nothing; whether the
   1e-3 band is re-registered is the weekly's call. **(b)** A hollow
   conductor is 13.7% cheaper to mesh than a solved-inside one on the
   two-torus, and every sheet and surface identity survives the cut to
   1e-7 or better. **(c)** The refined Dodd–Deeds fixture sits 0.28%
   *below* the filament closed form; the finite-wire correction raises
   the closed form by 0.115%, so the honest discrepancy is ≈ −0.40% and
   no claim tighter than 0.5% exists on this fixture. Local `main`
   remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first gate landed** (`TH-15` step 1, 09-05) and **the two-torus hole is a `MeshGenerator` route** (step 2a, 09-06 00:00) — every conductor in a *coil* fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%), field miss converging at +1.19 in h, natural-cavity control 29×, shown by `th:9` (`EX-50` ✅). Two-torus hole: 161 461 cells, sheets at 1e-16, surface area vs the solid interface 3.7e-7. Step 2 (`Re Z = 0`, the lossless identity) is On-deck item 2; step 3a (the birdcage as a hole) item 4. `TH-14` (copper via Leontovich) → `ANS-6` serial on it; `TH-14` step 1 needs a new anchor (§7 annotation) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅). **The refined fixture (0.28% / ≈ −0.40% corrected, 418 888 cells) reproduced on 09-06 and lands as On-deck item 1** — the headline moves with it. Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only.** 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%; `EX-48` shows the C16 identity at 0.12% — **network-level self-consistency on one fixture at 10 MHz, degree 1; no absolute accuracy, no resonance, tuning or mode-spectrum claim.** Absolute accuracy at Larmor is `ANS-4` (adjudication 09-09). **RLC sheets exist, not gated** (`PORT-14` 🟡: reduction identity 1.6e-3 / 3.4e-3 / 7.2e-4 vs 1e-3; not a resolution effect; linear in the told sheet width; **step 1d: not geometric — a field effect of the sheet, no constant enters the law**; band re-registration is the weekly's); **the circuit layer's algebra is gated at 1e-12** (`PORT-15` step 1 ✅) and claims nothing about any meshed coil |
| Multi-port drive | 🟡 **package-level, gated on the 4-leg identities** (`POST-6` step 1); shown by `ports:13` (`EX-49` ✅) | `ports.superpose_drives`: quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087% through the package, linearity 1e-12. **Drive-level power identity reads 11.6% vs 1e-2 — deliberate red**; it is the denominator (step 1b); band ruling with the 09-09 weekly |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; **F-human (0.15 m) gated on CAD identities** (`GEO-25` ✅), shown by `mesh:12` (`EX-51` ✅) | 4-leg record 111 898 / 116 085 (ports); 16-leg 270 728; F-human 504 642 cells at fixed sizing, conductor mass 0.965 ≥ 0.95 vs the scaled-sizing control at 0.893 — **a mesh, never solved; 64 MHz cost unpriced** |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 two gates registered on one fixture at 10 MHz at fixed `h`; shown by `ports:9` | twelve rotation pairs ≤ 1.52%, four mirror pairs ≤ 1.75%, both vs 5%; partition identity exact. **No absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 5 deliberate/known**, unchanged; example-artifact census `dead=0 exit=2` at `79ef902`, 45 examples | API sweep `violations=0` on all four roots; one new known-issues entry (a measurement-only probe is unsafe at width > 1 — `OPS-39`) |

## Recent activity (2026-09-05 18:00 → 2026-09-06 10:30)

- **19:30:** `PORT-14` step 1d — the fit holds on a fourth point
  (residual ×0.036, printed not asserted) and no measured geometric ratio
  predicts the zero-crossing: reading (2), a field effect of the sheet.
  137 s at 2 ranks. Row 🟡, band untouched, no step 1e.
- **21:00:** `EX-50` — the PEC sphere as a hole in ParaView; β 1.9746% vs
  4.886% and the 29× control reproduce the gate's own digits. 4 s. ✅,
  audited PASS (11 of 12 digits verbatim; the "30× ceiling" is arithmetic).
- **22:30:** `EX-51` — the F-human birdcage mesh in ParaView; 504 642
  cells, every CAD identity, the scaled-sizing control below the gate.
  196 s at 2 ranks. ✅, audited PASS (15 of 15 digits).
- **00:00:** `TH-15` step 2a — `two_torus_domain(as_hole=True)` landed;
  161 461 cells, surface area vs the solid interface 3.7e-7, sheets at
  1e-16. 130 + 126 s at 2 ranks. Step ✅, row 🟡, audited PASS (10 of 10).
  The first window failed on the step-0 probe's ghost-double-counting
  census — fixed in the gate module, filed for the probe (`OPS-39`).
- **01:45:** housekeeping sweep. **02:15:** weekly review — rotation
  committed, then session limit. **03:00 / 04:30 / 06:00:** session
  limit, nothing ran.
- **07:30:** `MAT-6` step 11 — the refined fixture reproduced 0.27998% vs
  0.2829% (0.0029 pp) at 418 888 cells, σ = 0 control 2.5e-07; parked on
  `attempt/MAT-6-step11-…` because `ans:1`'s fixture-identity pin fired
  and the no-op figure had no asserted/predicted label. Three windows
  399 / 299 / 248 s at 8 ranks. Correct escalation under rule (e).
- **09:00:** queue drained — journaled, no compute.
- **10:30 review:** three audits PASS; six rulings — the `ans:1` pin
  follows the fixture, the no-op figure was a prediction and clears,
  `TH-15` step 2 and step 3a scoped by the daily since the weekly was
  lost, `TH-14` step 1's anchor annotated, `OPS-39` opened; four-item
  queue (no fifth item can state its anchor today).

## Automation health

- **Six of eight scheduled slots fired; four lost sessions to the account
  limit** (weekly review, 03:00 review, 04:30, 06:00). Of the six that
  fired: four landed first-run, one parked correctly, one drained by
  protocol. First-run streak 28 of 28 over the slots that fired since
  09-03 18:00. Container Up 2 days continuously.
- **Foreground-executor rule: 50 for 50** since written. No docker-socket
  denial this interval (**3 of 67** slots overall; 0 of the last 27). No
  compute-safety event, no allowlist denial.
- Every digit re-read from the log by the slot owner; one slot escalated
  two rulings rather than deciding either (rule (e) as written); one slot
  disclosed collapsing a two-executor split into one and noted what the
  split would have caught. Tier labels: `PORT-14` heavy by ceiling
  (137 s); `EX-50` standard (4 s); `EX-51` standard by host-runner window
  (196 s); `TH-15` standard (126 s); `MAT-6` heavy by ceiling (399 / 299 /
  248 s at 8 ranks, all inside 600 s).
- **Housekeeping:** `attempts.md` at 15 559 lines vs the 6 000 budget
  after the 14-day rotation — the window is the weekly's call. 1 224
  logs; volume within policy.

## On deck (§9 — four items, not five; all independent; no spare)

1. **`MAT-6` step 11 — land it:** cherry-pick the parked branch, re-run
   `ans:1` and `mat:1` at 8 ranks and the census, move the §2 headline to
   0.28% / ≈ −0.40% corrected *(implementer; ≈ 10 min of compute)*
2. **`TH-15` step 2** — the lossless identity on the hollow two-torus:
   `Re Z = 0` to 1e-9 through the `PORT-1` package, the σ = 800 solid as
   the dissipating control *(implementer; ≈ 300 s at 4 ranks)*
3. **`OPS-39`** — the step-0 probe's census made rank-safe, gated on the
   exact count identity at 1 and 2 ranks *(implementer; smoke + ≈ 50 s)*
4. **`TH-15` step 3a** — the birdcage as a hole: `birdcage_port_domain(as_hole=True)`
   with the sheet, partition and surface-area identities asserted
   *(implementer; ≈ 60 s at 2 ranks, real build)*

The 16:30 slot drains by protocol if all four land; the next review
refills.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
