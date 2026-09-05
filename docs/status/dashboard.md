# FEM-EM Solver — status

**Updated:** 2026-09-05 10:30 daily review. Headline: **the conductor
model's first gate is green — a perfect-conductor sphere solved as a hole
in the mesh reproduces the closed-form exterior dipole coefficient to
1.97% against a 4.9% band, with the natural cavity as a 29× control — but
it is parked, not landed, because a second pre-registered anchor (the
pointwise field miss) measured a 46% first-order discretisation floor
that converges at +1.2 in h and is still 20% on the finest rung.** This
review ruled: that anchor becomes the convergence rate (≥ 0.8, measured
1.19), nothing at 4.9% moves, and landing is the next slot's job. Two
Tier A negatives sharpened: `POST-6` step 1b showed the S-derived accepted
power and the sheet accounting are the *same* number to 1e-15, so the 11.6%
drive-level miss is the fixture's 0.98%-of-supplied systematic seen
against a 13× smaller denominator (band decision held for tomorrow's
weekly, recommendation recorded); `PORT-14` step 1b refuted its own
hypothesis — the termination-reduction residual is not monotone in mesh
resolution (×2.6 then ×0.93), and the one rung whose four sheet widths
alternated is the one that rose, so the sheet-width law is measured next
on a fixed mesh. `EX-48` landed and audited PASS: the C16 column identity
between two independently solved columns at 0.12% through the example
path. **Still a self-consistency story on one fixture family at 10 MHz at
fixed `h`: no absolute SAR, no homogeneity, no C95.3, no Larmor coil
claim, no convergence claim beyond the PEC-sphere ladder above, no
resonance or tuning claim.** Source of truth is `PROJECT_PLAN.md`; this
page is a read-only digest for the human operator.

## Weekly review digest (2026-09-02, unchanged from the weekly's own copy)

- **Pace, 08-30 → 09-02 (2.68 d):** 26 §4-✅ items (10 chunks + 16 steps),
  9.7/day, 62% physics; 30 of 32 implementer slots fired, every loss
  launcher-side (login, CLI pin), none on limits. Full ledger in §10.
- **Phase 5 exit re-assessed to ≈ 09-05…09 on F-small** — watch condition:
  `WF-6` step 3f printed by 09-06. **Met 09-02** (clause (a)); the SAR gate
  itself landed 09-02 19:30.
- **Deferred to 09-06:** the §7 archive rotation and the B1+ literature
  anchor. **New for the 09-06 weekly (from the dailies since):** `PORT-13`
  steps 1–3 landed (the 32×32 exists); `GEO-25`'s report is in and §10
  Phase 6's r³ cost paragraph and `TH-16`'s 62 GiB line need re-dating
  from the ≈ 0.84 exponent; two operator directives landed 09-04 (the
  conductor model and the Ansys feature ladder) with a §10 Phase 6 subgoal
  to own; **`ANS-4`'s adjudication** (private pre-read in `docs/private/`;
  the first XL slot is reserved for its diagnosis rung by your 09-05
  directive); **the `POWER_BALANCE_BAND` ruling** — step 1b has reported,
  the 10:30 review's recommendation is in the `POST-6` §7 entry; the
  `attempts.md` rotation, now 19 038 lines; `TH-15` step 2 scoping once
  step 1 lands (the two-torus hole needs a `MeshGenerator` route).

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
   that the row stays 🧪 until a gate step lands". **And one for
   `.claude/agents/implementer.md`, new this review:** "a slot that parks
   its item marks the §9 item BLOCKED in the same commit" — the 07:30 slot
   parked `TH-15` step 1 without marking it and the 09:00 slot spent ten
   minutes doing so; the rule is now §9 standing rule (d), but the agent
   file should carry it too.
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
8. FYI, no action — physics worth a glance. **(a)** The PEC-hole result
   is the first interior-conductor gate this solver has had; the 46%
   pointwise miss beside a 2% dipole-coefficient miss is the textbook
   picture of lowest-order edge elements one cell off a curved Dirichlet
   wall (pointwise error large and orthogonal to the moment), and the
   ladder confirms it is a floor, not a defect. **(b)** `EX-48`'s
   field-level C16 reading on the 16-leg ring rung is RMS 16.5% where the
   integral identity is 0.12% — the same estimator class; it is one more
   reason the plan makes no homogeneity claim at CG1. **(c)** The lumped
   sheet's termination-reduction residual tracks the *uniformity* of the
   four sheets' effective widths, not the mesh density — a 5% width
   alternation the `PORT-9` gates cannot see moved it 2.6×. Local `main`
   remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **measured, not landed** — every conductor on `main` is still a solved-inside volume with σ capped by the mesh (800 S/m coil) | `TH-15` step 1 (09-05 07:30): PEC sphere as a hole, β = 1.019746 vs 1 (1.97% against 4.886%), natural-cavity control 29×, cavity dofs pinned exactly; parked on `attempt/TH-15-…` pending the anchor-(ii) ruling — **ruled this review**, landing is On-deck item 1. Step 0 🧪: the two-torus meshes as a hole, 13.7% cheaper. `TH-14` (copper via Leontovich) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅, shown by `mat:1`). Larmor coil loading stays an extrapolation. `MAT-6` step 11 (the refined fixture to production, headline → 0.28%) is the spare |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only.** 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13 vs 1e-3, σ_max 0.999999452, 18 classes ≤ 0.44% vs 5%; `EX-48` shows the C16 identity between two solved columns at 0.12% — **network-level self-consistency on one fixture at 10 MHz, degree 1; no absolute accuracy, no resonance, tuning or mode-spectrum claim.** Absolute accuracy at Larmor is `ANS-4` (adjudication 09-06). **RLC sheets exist, not gated** (`PORT-14` 🟡: reduction identity 1.6e-3 / 3.4e-3 / 7.2e-4 vs 1e-3; not a resolution effect — step 1b); **the circuit layer's algebra is gated at 1e-12** (`PORT-15` step 1 ✅) and claims nothing about any meshed coil |
| Multi-port drive | 🟡 **package-level, gated on the 4-leg identities** (`POST-6` step 1, 09-04) | `ports.superpose_drives`: quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087% through the package (path equality 1e-15), linearity 1e-12, `w = e_k` bitwise. **Drive-level power identity reads 11.6% vs 1e-2 — deliberate red**; step 1b (09-05) showed `P_acc` = `supplied − sheets` to 1e-15 per drive and the single drives miss 13.0% each — it is the denominator; band ruling with the 09-06 weekly |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; shown by `mesh:10` / `mesh:11`; F-human (0.15 m) priced, 🧪 | 4-leg record 111 898; 16-leg record 270 728 at 2 and 12 ranks, 32/32 sheets exact. F-human: 504 642 cells / 112 s at fixed sizing — a probe, not a gate; `GEO-25` step 2 (the gate) queued |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 two gates registered on one fixture at 10 MHz at fixed `h`; shown by `ports:9` | twelve rotation pairs ≤ 1.52%, four mirror pairs ≤ 1.75%, both vs 5%; partition identity exact. **No absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 5 deliberate/known**, unchanged; example-artifact census `dead=0 exit=2` at `52fb1af`, 42 examples | API sweep `violations=0` on all four roots |

## Recent activity (2026-09-05 03:00 → 10:30)

- **04:30:** `EX-48` — the ring rung's quarter turn: P17 and P21 fields in
  one XDMF, C16 column identity 0.1163% vs 5%, wrong-rotation control
  338× the band, census clean both sides. 112 s at 4 ranks. ✅, audited
  PASS (nine of nine digits traced).
- **06:00:** `POST-6` step 1b — the power-wave identity holds at 1.7e-15;
  the four single drives miss the volume integral by 13.0% each and the
  superposed drive by 0.89× that mean. Band untouched, test still red by
  design. 104 s, no new solve.
- **07:30:** `TH-15` step 1 — PEC sphere as a hole: β = 1.019746 (1.97%
  vs 4.886%), control 29×, cavity dofs pinned to zero, `TH-8` unchanged;
  pointwise anchor 46% and converging — code parked, ruling requested.
  Four windows ≤ 28 s.
- **09:00:** `PORT-14` step 1b — reduction residual ×2.62 at ×0.75
  resolution, ×0.93 at ×0.6; hypothesis refuted, `sheet_width_m` named.
  149 + 136 s. Row stays 🟡. (Also marked §9 item 3 blocked, which the
  07:30 slot had not.)
- **10:30 review:** `EX-48` audited PASS; three rulings — `TH-15` anchor
  (ii) → convergence rate ≥ 0.8, `POST-6` band decision held for the
  weekly with a recommendation, `PORT-14` step 1c scoped; standing rule
  (d) added; five-item queue.

## Automation health

- **4 of 4 scheduled slots landed**, all journaled, all on the first
  attempt — 20 of 20 over the last five intervals. Container Up 44 h
  continuously.
- **Foreground-executor rule: 42 for 42** since written. No docker-socket
  denial this interval (**3 of 57** slots overall; 0 of the last 17). No
  compute-safety event, no allowlist denial.
- One item parked rather than widened, one hypothesis refuted in print,
  every digit re-read from the log — the protocol working as written. One
  process gap (the unmarked parked item) closed by §9 standing rule (d).
- Tier labels: `EX-48` standard (112 s host-runner window); `POST-6` and
  `PORT-14` heavy by ceiling (104 / 149 / 136 s); `TH-15` standard, ≤ 28 s
  per window.
- **Housekeeping:** `attempts.md` at 19 038 lines vs the 6 000 budget —
  the 2026-09-06 weekly's rotation. 1 200 logs; volume within policy.

## On deck (§9 — five items; 3 names its executor)

1. **`TH-15` step 1 landing** — cherry-pick the parked PEC-hole code,
   anchor (ii) → relative-L2 convergence rate ≥ 0.8 (measured 1.19), β to
   1.9746% reproduced to the digit, `TH-8` re-run green, branch deleted
   *(implementer; ≈ 1 min)*
2. **`GEO-25` step 2** — the F-human gate: 504 642-cell record, CAD
   identities and `CAD_MASS_GATE` as executed asserts, branch A as the
   below-gate control *(implementer; ≈ 4 min)*
3. **`EX-49`** — an asymmetric two-port drive through
   `ports.superpose_drives` beside the quadrature drive, linearity between
   the halves and the sum asserted, `P_acc` printed with its caveat
   *(`example-runner`; ≈ 150 s at `-n 2`)*
4. **`PORT-14` step 1c** — the sheet-width law perturbed on the fixed gate
   mesh (common ±5%, alternating ±5.3%), L and C residuals printed against
   step 1's record, 4×4 gates asserted per configuration *(implementer;
   ≈ 240 s)*
5. **`MAT-6` step 11** — the slab-refined Dodd–Deeds fixture to production,
   ΔR re-recorded at 0.28% within 0.05 pp *(implementer +
   `record-reconciler`; ≈ 20–25 min; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
