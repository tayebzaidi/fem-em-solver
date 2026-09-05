# FEM-EM Solver — status

**Updated:** 2026-09-05 18:00 daily review. Headline: **the conductor
model's first gate is landed on `main` — a perfect-conductor sphere solved
as a hole in the mesh reproduces the closed-form exterior dipole
coefficient to 1.97% against a 4.9% band, its field error converging at
+1.19 in h, the natural cavity a 29× control — and the human-scale coil
is a gated mesh: the 16-leg birdcage at 0.15 m ring radius meshes to
504 642 cells with every CAD identity exact and the scaled-sizing
alternative failing the conductor-mass gate by 0.057.** The lumped-RLC
sheet's termination-reduction miss now has a measured lever: perturbing
only the width the sheet law is *told* moves the residual 3.7–5.8× for a
5% change, on a mesh that did not move by one cell, and both directions
raise it — the law is ~1.1% off its optimum, a lever, not yet a
correction; the next step tests that prediction on a fourth point and
tunes nothing. An asymmetric two-port drive through the package landed as
an example with linearity at 0 vs 1e-12; its negative control fell 1.2%
short of a plan-time ≥2× guess, and this review ruled the in-slot demotion
of that guess correct while adding a standing rule so items label such
factors. **Still a self-consistency story on one fixture family at 10 MHz
at fixed `h`: no absolute SAR, no homogeneity, no C95.3, no Larmor coil
claim, no convergence claim beyond the PEC-sphere ladder, no resonance or
tuning claim, and no solve has touched the human-scale mesh.** Source of
truth is `PROJECT_PLAN.md`; this page is a read-only digest for the human
operator.

## Weekly review digest (2026-09-02, unchanged from the weekly's own copy)

- **Pace, 08-30 → 09-02 (2.68 d):** 26 §4-✅ items (10 chunks + 16 steps),
  9.7/day, 62% physics; 30 of 32 implementer slots fired, every loss
  launcher-side (login, CLI pin), none on limits. Full ledger in §10.
- **Phase 5 exit re-assessed to ≈ 09-05…09 on F-small** — watch condition:
  `WF-6` step 3f printed by 09-06. **Met 09-02** (clause (a)); the SAR gate
  itself landed 09-02 19:30.
- **Deferred to 09-06:** the §7 archive rotation and the B1+ literature
  anchor. **New for the 09-06 weekly (from the dailies since):** `PORT-13`
  steps 1–3 landed (the 32×32 exists); `GEO-25` is ✅ again and its 64 MHz
  solve cost is unpriced (the `TH-16` cost probe and the Phase 6 r³
  paragraph re-dating); two operator directives landed 09-04 (the
  conductor model and the Ansys feature ladder) with a §10 Phase 6 subgoal
  to own; **`ANS-4`'s adjudication** (private pre-read in `docs/private/`;
  the first XL slot is reserved for its diagnosis rung by your 09-05
  directive); **the `POWER_BALANCE_BAND` ruling** — step 1b has reported,
  the 10:30 review's recommendation is in the `POST-6` §7 entry; the
  `attempts.md` rotation, now 19 458 lines; `TH-15` step 2 proper
  (`Re P_in = 0`) once step 2a's mesh route lands; a note that `TH-14`
  step 1's anchor cannot be the E-driven dipole coefficient (a surface
  impedance moves it at ~1e-4 for copper).

## Waiting on you

1. ✅ **`ANS-4` replicated 2026-09-04** — both orders in the gitignored
   `aed_results/`, the private-mode run filled `COMPARISON_private.md`
   (Status 0, 128 s), the pre-read is in `docs/private/`. No AED number
   reached a tracked file. Nothing for you to do; the 2026-09-06 weekly
   review adjudicates and retires this line.
2. 🟢 **`ANS-3` AED run** — the top of your queue. Same low-order rule,
   same private-results handling. Its FEM-side records were re-based to
   the 0.11 image (`OPS-33`); the tracked table's AED cells are blank by
   construction.
3. 🟡 **Two one-line edits to `.claude/agents/example-runner.md`, if you
   agree** (the sandbox denies writes under `.claude/agents/`, so both
   rules currently live in §9 and in each queued example item): (a) "both
   census windows through `run_and_log.sh`", and (b) "guide artifact
   references carry the full filename". An interactive session can land
   both.
4. 🟡 **One line for `.claude/agents/mesh-probe.md`, same reason:** "report
   that the row stays 🧪 until a gate step lands". **One for
   `.claude/agents/implementer.md`:** "a slot that parks its item marks the
   §9 item BLOCKED in the same commit" (§9 standing rule (d)). **And one
   new this review, for both `implementer.md` and `example-runner.md`:**
   "a failing pre-registered assertion whose factor is not labelled
   asserted-or-predicted is a negative result to report, not a call to
   make in-slot" (§9 standing rule (e), from `EX-49`).
5. ✅ **Housekeeping budget — resolved by operator decision 2026-09-03:**
   gating logs are exempt from the 25 MB volume ceiling. Remaining under
   `OPS-36`: `attempts.md` rotation (the 2026-09-06 weekly's job), and a
   hand-run `--apply` must be committed by whoever runs it.
6. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
7. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
8. FYI, no action — physics worth a glance. **(a)** The lumped sheet's
   reduction residual is *linear* in the width the law is told, with the
   same slope for a capacitor and an inductor, and its zero-crossing sits
   1.1% below the area-based `A/h` — consistent with the sheet realising an
   impedance ~1% off `Z_p`, e.g. a mean terminal separation a fraction of a
   percent under the bounding-box height the law divides by. Step 1d
   measures the candidates and tests the fit's prediction; nothing gets
   tuned to fit. **(b)** The PEC-hole result is the first interior-conductor
   gate this solver has had; the 46% pointwise miss beside a 2%
   dipole-coefficient miss is the textbook picture of lowest-order edge
   elements one cell off a curved Dirichlet wall, and the ladder confirms
   it is a floor (+1.19 in h), not a defect. **(c)** Fixed absolute mesh
   sizing on the human-scale coil is now a *gated* conclusion, not a probe
   reading: scaling the sizing with the radius loses 11% of the conductor
   mass. Local `main` remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — two lines changed this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first gate landed** (`TH-15` step 1, 09-05 12:00) — every conductor in a *coil* fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%), relative-L2 miss converging at +1.19 in h, natural-cavity control 29×, 1702 cavity dofs pinned exactly, `TH-8` unchanged. Step 2a (the two-torus hole as a `MeshGenerator` route) is On-deck item 4; step 2 (`Re P_in = 0`) is the weekly's to scope. `TH-14` (copper via Leontovich) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅, shown by `mat:1`). Larmor coil loading stays an extrapolation. `MAT-6` step 11 (the refined fixture to production, headline → 0.28%) is the spare |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only.** 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13 vs 1e-3, σ_max 0.999999452, 18 classes ≤ 0.44% vs 5%; `EX-48` shows the C16 identity between two solved columns at 0.12% — **network-level self-consistency on one fixture at 10 MHz, degree 1; no absolute accuracy, no resonance, tuning or mode-spectrum claim.** Absolute accuracy at Larmor is `ANS-4` (adjudication 09-06). **RLC sheets exist, not gated** (`PORT-14` 🟡: reduction identity 1.6e-3 / 3.4e-3 / 7.2e-4 vs 1e-3; not a resolution effect — step 1b; **linear in the told sheet width with a zero-crossing ≈ −1.1% — step 1c**; step 1d is On-deck item 1); **the circuit layer's algebra is gated at 1e-12** (`PORT-15` step 1 ✅) and claims nothing about any meshed coil |
| Multi-port drive | 🟡 **package-level, gated on the 4-leg identities** (`POST-6` step 1, 09-04); shown by `ports:13` (`EX-49` ✅) | `ports.superpose_drives`: quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087% through the package (path equality 1e-15), linearity 1e-12 (0 through the example), `w = e_k` bitwise. **Drive-level power identity reads 11.6% vs 1e-2 — deliberate red**; step 1b (09-05) showed `P_acc` = `supplied − sheets` to 1e-15 per drive and the single drives miss 13.0% each — it is the denominator; band ruling with the 09-06 weekly |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; shown by `mesh:10` / `mesh:11`; **F-human (0.15 m) gated on CAD identities** (`GEO-25` ✅ 09-05) | 4-leg record 111 898; 16-leg record 270 728 at 2 and 12 ranks, 32/32 sheets exact. F-human: 504 642 cells at fixed sizing, partition exact, 32 terminal ratios in [0.95, 1.0], conductor mass 0.965 ≥ 0.95 vs the scaled-sizing control at 0.893 — **a mesh, never solved; 64 MHz cost unpriced**. `EX-51` (On-deck item 3) shows it |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 two gates registered on one fixture at 10 MHz at fixed `h`; shown by `ports:9` | twelve rotation pairs ≤ 1.52%, four mirror pairs ≤ 1.75%, both vs 5%; partition identity exact. **No absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 5 deliberate/known**, unchanged; example-artifact census `dead=0 exit=2` at `f50defd`, 43 examples | API sweep `violations=0` on all four roots |

## Recent activity (2026-09-05 10:30 → 18:00)

- **12:00:** `TH-15` step 1 landed — the parked PEC-hole code cherry-picked
  clean; β 1.9746% vs 4.886% reproduced to the digit, the field anchor
  re-scoped to a convergence rate (+1.19 ≥ 0.8), control 29×, `TH-8`
  unchanged; branch deleted. 34 + 13 + 5 s at 2 ranks. Row 🟡 (step 1 of 3).
- **13:30:** `GEO-25` step 2 — the F-human rung as a gated fixture:
  504 642 cells at 0.000e+00, partition exact, 32 terminal ratios inside
  the band, conductor-mass separation 0.893 < 0.95 ≤ 0.965. 196 s at 2
  ranks. 🧪 → ✅, audited PASS (15 of 15 digits traced).
- **15:00:** `EX-49` — the asymmetric two-port drive through
  `ports.superpose_drives` in ParaView: linearity 0 vs 1e-12, cells
  bitwise, quadrature C4 record to the digit, control 1.9754× the band
  (a plan-time ≥2× guess demoted to a printed reading in-slot; ruling
  below). 73 s at 2 ranks. ✅, audited PASS (16 of 16 digits traced).
- **16:30:** `PORT-14` step 1c — the told sheet width perturbed on the
  fixed gate mesh: residual ×5.80 / ×3.75 / ×5.63 under +5% / −5% /
  alternating ±5.3%, every 4×4 still reciprocal and passive; reading (1)
  selected, zero-crossing inside the interval at ≈ −1.1%. 258 s at 2
  ranks. Row stays 🟡, band untouched.
- **18:00 review:** two audits PASS; four rulings — the `EX-49` demotion
  stands (standing rule (e) added), `PORT-14` step 1d scoped (tests the
  fit, tunes nothing), `TH-15` step 2a scoped (the mesh route), the
  F-human solve cost left to the weekly; `EX-50` and `EX-51` opened;
  five-item queue.

## Automation health

- **4 of 4 scheduled slots landed**, all journaled, all on the first
  attempt — 24 of 24 over the last six intervals. Container Up 2 days
  continuously.
- **Foreground-executor rule: 46 for 46** since written. No docker-socket
  denial this interval (**3 of 61** slots overall; 0 of the last 21). No
  compute-safety event, no allowlist denial.
- Every digit re-read from the log by the slot owner; one slot escalated a
  ruling rather than deciding it; one measurement recorded a qualification
  its pre-registration had not anticipated and labelled its follow-on
  arithmetic as hand arithmetic — the protocol working as written. One
  wording gap in items (asserted vs predicted control factors) closed by
  §9 standing rule (e). One disclosed inefficiency: a gate module built
  around printed records ran once without `-s` and once with (2 × 195 s).
- Tier labels: `TH-15` standard (≤ 34 s per window); `GEO-25` heavy by
  ceiling (196 / 197 s); `EX-49` standard by host-runner window (73 /
  74 s); `PORT-14` heavy by ceiling (258 s vs a 240 s estimate).
- **Housekeeping:** `attempts.md` at 19 458 lines vs the 6 000 budget —
  the 2026-09-06 weekly's rotation. 1 213 logs; volume within policy.

## On deck (§9 — five items; 2 and 3 name their executor)

1. **`PORT-14` step 1d** — the origin of the 1.1%: the sheet geometry the
   fixture already measures read per port against the fitted
   zero-crossing, and the fit tested on a fourth point (told widths
   × (1 + ε\*)), residuals printed, nothing tuned *(implementer; ≈ 2 min)*
2. **`EX-50`** — the PEC sphere as a hole in ParaView beside the
   solved-inside dielectric sphere, β asserted against 1 through the
   example path *(`example-runner`; ≈ 30 s at `-n 2`)*
3. **`EX-51`** — the F-human birdcage mesh in ParaView, the 504 642-cell
   record and CAD identities asserted, the scaled-sizing rung as the
   asserted below-gate control *(`example-runner`; ≈ 220 s at `-n 2`,
   real build)*
4. **`TH-15` step 2a** — the two-torus hole as a `MeshGenerator` route,
   step 0's counts and areas as executed asserts *(implementer; ≈ 90 s)*
5. **`MAT-6` step 11** — the slab-refined Dodd–Deeds fixture to production,
   ΔR re-recorded at 0.28% within 0.05 pp *(implementer +
   `record-reconciler`; ≈ 20–25 min; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
