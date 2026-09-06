# FEM-EM Solver — status

**Updated:** 2026-09-06 weekly review, run interactively by the operator's
session (the scheduled 02:15 weekly died on the account session limit after
its rotation commit). Headline: **`ANS-4` is adjudicated — AGREE at 10 MHz,
inconclusive at 64 / 128 MHz, and element order is excluded as the cause;
the first XL slot goes to the discriminating run.** Phase 5 exits on
F-small one item from now (`MAT-4` step 2). Phase 6 has started on the
feature ladder with its mesh prerequisites all gated and the r³ cost premise
dead. The §7 archive rotation the cut-off weekly owed is done (nine
narratives, 1 872 lines). **Still a self-consistency story at the Larmor
frequencies: no absolute SAR, no homogeneity, no C95.3, no Larmor coil
accuracy claim, no resonance or tuning claim, and no solve has touched the
human-scale mesh.** Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

## Weekly review digest (2026-09-06, interactive)

- **Pace, 09-02 → 09-06 (4.33 d):** 34 §4-✅ items (23 chunks + 11 steps),
  7.9/day, 44 % physics; 2 of 14 governing sessions died on the account
  limit (the weekly and the 03:00 review), 2 implementer slots with them.
  Full ledger in §10.
- **`ANS-4` adjudicated:** AGREE at 10 MHz, INCONCLUSIVE at 64/128 MHz;
  the miss grows with frequency and is several times HFSS's own
  order-sensitivity, so it is not element order — our unconverged 116 k
  mesh is the first suspect. Numeric ruling in `docs/private/`; nothing
  promoted at Larmor. `ANS-1` AGREE survives the `MAT-6` step 11 landing
  (arithmetic in the private file).
- **XL slot spent:** `ANS-4` step 2 — four conductor-resolution rungs plus
  one degree-2 solve at 128 MHz in one window at `-n 16`, Richardson h→0
  printed, decision rule pre-registered (§7 `ANS-4`, §9 item 5). **It needs
  `fem-em-solver-xl` Up** — see Waiting-on-you.
- **Phase 5:** watch condition met on 09-02 (the SAR gate landed); exit on
  F-small ≈ 09-07…08, one item (`MAT-4` step 2; its stall rule trips 09-07,
  the 18:00 review queues it). The B1+ literature target is replaced by a
  computable closed form (`WF-6` step 4, the unloaded-coil line-current
  superposition).
- **Phase 6:** started on the feature ladder; r³ cost model given its
  epitaph (`GEO-25`: 504 642 cells, exponent 0.84); `TH-16`'s "62 GiB wall"
  re-dated to an 11–33 GiB bracket for the first F-human solve; `PORT-14`
  ruled — the 3.4e-3 single-mode floor becomes a fixture record and a named
  systematic, `REDUCTION_BAND` not widened; `POST-6` (iii) re-registered
  common-mode, `PORT-16` opened for the 1 %-of-supplied gap; `TH-17` first
  mode number ≈ 09-12…14 if slots fire; no completion date.
- **Examples:** 45/45 green within 6 days; Phase 3 one short → `EX-52`.
  Agents: all six stay; pathologist stays at opus (it ran 0 times — the
  limit deaths were at session start, not agent-side).

## Waiting on you

1. 🔴 **The account session limit ate four scheduled sessions on 09-06
   (02:15 weekly, 03:00 review, 04:30 and 06:00 slots) — schedule
   decision, yours only.** They died *at start*, in the band right after
   the 02:00 reset, so the limit was consumed by the preceding implementer
   slots, not by the reviews. Two options, either is fine: move the
   02:15 / 03:00 pair later (e.g. 07:15 / 08:00, after the 07:10 reset —
   `scripts/automation/crontab`, then `crontab scripts/automation/crontab`)
   or thin the 21:00 / 22:30 / 00:00 implementer slots that drain the
   window before it. The weekly review's plan work was completed
   interactively today, so nothing is lost this time.
2. 🟠 **Bring the XL service up for `ANS-4` step 2 (§9 item 5, `xl`)** —
   `docker compose -f docker/docker-compose.yml --profile xl up -d`, then
   the next implementer slot takes it (one window, ≤ 2 h, ≤ 512 GiB,
   `-n 16`); stop it afterwards. If the profile is on the allowlist the
   slot brings it up itself and skips otherwise. The ledger row is
   appended by the harness at start.
3. ✅ **`ANS-4` adjudicated 2026-09-06** — AGREE at 10 MHz, inconclusive at
   Larmor pending item 2's run; nothing for you to do. The private ruling
   is `docs/private/ans4-adjudication-2026-09-06.md`.
4. 🟢 **`ANS-3` AED run** — the top of your queue. Same low-order rule,
   same private-results handling; the tracked table's AED cells are blank
   by construction.
5. 🟡 **`ANS-1` note, no action yet:** the refined Dodd–Deeds fixture
   lands next slot and moves our ΔR column by ~1.8% relative (the pin
   follows the fixture — ruled today, nothing on the AED side changes).
   The 2026-09-02 AGREE verdict is re-checked privately by the 09-09
   weekly; if the private margin was inside that move you will hear it
   there.
6. 🟡 **Agent-definition edits — still open, and you declined one today.**
   The interactive session's edit to `implementer.md` (rules (d) and (e))
   was denied at the permission prompt, so all five one-liners remain:
   two for `example-runner.md` (census windows through the harness,
   pre-census before any file is written; full-filename guide
   references), one for `mesh-probe.md` (row stays 🧪 until a gate step
   lands), one for `implementer.md` (parking marks the §9 item BLOCKED —
   rule (d)), and rule (e) for both. Say which you want and an interactive
   session applies them; the auditor and log-pathologist edits from 09-03
   did land. `implementer.md` also has no "Last verified against" footer.
7. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). It is what saved
   the rotation today; revert only if you want the single-commit form.
8. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
9. FYI, no action — physics worth a glance. **(a)** The lumped sheet's
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
