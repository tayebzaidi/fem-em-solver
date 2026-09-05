# FEM-EM Solver — status

**Updated:** 2026-09-05 03:00 daily review. Headline: **the operator's
Ansys feature ladder is three rows deep after one night — the package-level
multi-port drive exists and is gated on the quadrature and linearity
identities, RLC sheets and the circuit layer's algebra exist, and two of
the three came back with honest negatives that are now diagnoses with a
measurement queued behind each.** `POST-6` step 1 reproduces `WF-6`'s
quadrature records through the package to 1e-15 on the same solves, but
the drive-level power identity reads 11.6% against a 1% band. The review's
arithmetic on the logs says that is the fixture's known ~1% accounting gap
seen against a 13× smaller denominator, and step 1b asserts the one
identity that decides it. `PORT-14` step 1 puts a capacitor on a lumped
sheet and solves; the field-side termination-reduction identity misses
1e-3 at 1.6e-3 / 3.4e-3 for the two lossless elements (the lossy one is
inside), so a resolution rung is queued. `PORT-15` step 1 closed the ladder
closed form and the S/Z reduction at machine precision, audited PASS.
`TH-15` step 0 found the two-torus conductor meshes as a hole, 13.7%
cheaper, sheets still attached — and the review corrected step 1's
negative control before it runs (a σ = 800 sphere is a PEC in a
quasi-static E field; the control is the natural cavity). Your `ANS-4`
replication landed; the tracked diff and log were checked for AED digits
and carry none. **Still a self-consistency story on one fixture family at
10 MHz at fixed `h`: no absolute SAR, no homogeneity, no C95.3, no Larmor
coil claim, no convergence claim, no resonance or tuning claim, and the
new capabilities are gated only where the digest below says so.** Source
of truth is `PROJECT_PLAN.md`; this page is a read-only digest for the
human operator.

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
  directive); the `POWER_BALANCE_BAND` denominator decision once `POST-6`
  step 1b reports; the `attempts.md` rotation, now 18 684 lines.

## Waiting on you

1. ✅ **`ANS-4` replicated 2026-09-04** — both orders in the gitignored
   `aed_results/`, the private-mode run filled `COMPARISON_private.md`
   (Status 0, 128 s), the pre-read is in `docs/private/`. This review
   confirmed no AED number reached a tracked file. Nothing for you to do;
   the 2026-09-06 weekly review adjudicates and retires this line.
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
   that the row stays 🧪 until a gate step lands" — the §9 items now say
   "🧪 by the §3 rule" in every probe's first line (`TH-15` step 0 did it
   right this interval); the agent file should say it from the other side.
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
8. FYI, no action — physics worth a glance: **the lumped sheet is
   single-mode to about 3e-3, not 1e-3**, and the miss orders by |Γ| (worst
   for the lossless terminations that return everything to the sheet),
   which is what "the sheet has a little higher-order content" predicts
   and what an arithmetic bug would not. And a correction the review made
   to a plan you directed: a σ = 800 S/m sphere in a quasi-static
   *electric* field is a PEC to one part in a million (σ/ωε₀ = 1.4e6 at
   10 MHz — skin depth is the wrong scale there), so `TH-15` step 1's
   control is now the natural cavity (β = −½) rather than the lossy
   volume, and the gate is on the dipole coefficient rather than the field
   (the ε = 78 dielectric is within 3.75% of a PEC, too close for a 5%
   field band). Local `main` remains well ahead of origin (push is
   manual).

## Honest current state (digest of §2 — one bullet added this interval: the multi-port drive)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | ⬜ none — every conductor is a solved-inside volume with σ capped by the mesh (800 S/m coil) | `TH-15` step 0 🧪 (09-05): the two-torus conductor meshes as a hole, 161 461 vs 184 176 cells, sheets attached, cavity surface tagged. Step 1 (PEC sphere, dipole coefficient β = 1 vs the natural-cavity β = −½ control) queued; `TH-14` (copper via Leontovich) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅, shown by `mat:1`). Larmor coil loading stays an extrapolation. `MAT-6` step 11 (the refined fixture to production, headline → 0.28%) is the spare |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only.** 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13 vs 1e-3, σ_max 0.999999452, 18 classes ≤ 0.44% vs 5% — **network-level self-consistency on one fixture at 10 MHz, degree 1; no absolute accuracy, no resonance, tuning or mode-spectrum claim.** Absolute accuracy at Larmor is `ANS-4` (adjudication 09-06). **RLC sheets exist, not gated** (`PORT-14` 🟡: reduction identity 1.6e-3 / 3.4e-3 / 7.2e-4 vs 1e-3); **the circuit layer's algebra is gated at 1e-12** (`PORT-15` step 1 ✅) and claims nothing about any meshed coil |
| Multi-port drive | 🟡 **package-level, gated on the 4-leg identities** (`POST-6` step 1, 09-04) | `ports.superpose_drives`: quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087% through the package (path equality 1e-15), linearity 1e-12, `w = e_k` bitwise. **Drive-level power identity reads 11.6% vs 1e-2 — deliberate red**; step 1b (the power-wave identity at 1e-6) queued to settle whether it is the denominator |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; shown by `mesh:10` / `mesh:11`; F-human (0.15 m) priced, 🧪 | 4-leg record 111 898; 16-leg record 270 728 at 2 and 12 ranks, 32/32 sheets exact. F-human: 504 642 cells / 112 s at fixed sizing — a probe, not a gate; `GEO-25` step 2 (the gate) queued |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 two gates registered on one fixture at 10 MHz at fixed `h`; shown by `ports:9` | twelve rotation pairs ≤ 1.52%, four mirror pairs ≤ 1.75%, both vs 5%; partition identity exact. **No absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 5 deliberate/known** (two new this interval, both by their items' negative-result protocol); example-artifact census `dead=0 exit=2` at `604151e`, 41 examples | API sweep `violations=0` on all four roots |

## Recent activity (2026-09-04 18:00 → 2026-09-05 03:00)

- **19:30:** `POST-6` step 1 — `ports.superpose_drives` lands; quadrature
  records reproduced through the package (path equality 1e-15), linearity
  1e-12, unit weights bitwise; the drive-level power identity 11.6% vs
  1e-2, filed as a deliberate red. 146 s at 2 ranks. Row 🟡.
- **21:00:** `PORT-14` step 1 — complex `Z_p` on a sheet and the circuit
  reduction; 50 Ω baseline reproduces `PORT-9` (1.5e-14, σ_max 0.99999);
  termination identity 1.6e-3 (C) / 3.4e-3 (L) / 7.2e-4 (R) vs 1e-3, band
  not widened, second deliberate red. 105 s, 13 solves. Row 🟡.
- **22:30:** `PORT-15` step 1 — ladder closed form vs mesh-matrix
  eigenvalues 5e-16 / 2e-15, S-route vs Z-route reduction ~2e-16, one
  detuned leg moves the worst mode 4.1e-3 under its 5e-3 ceiling. 4 s.
  Audited PASS.
- **23:17 / 23:37 (interactive):** `ANS-4`'s AED half replicated (numbers
  private); the XL tier written into §5.1, the compose file, the bash
  guard and `docs/testing/xl-ledger.md`.
- **00:00:** `TH-15` step 0 — the two-torus conductor as a hole: 161 461
  vs 184 176 cells, sheets at nominal area to 1e-16, cavity surface 7642
  facets matching the solid interface area to 3.7e-7; one mechanism
  finding (derive the surface group from the meshed boundary, not the
  retained tool). 🧪 by rule.
- **03:00 review:** `PORT-15` step 1 audited PASS; `POST-6`'s in-slot
  rtol substitution ratified as arithmetic; three diagnoses banked
  (denominator, |Γ| ordering, the `TH-15` control correction); §2.1
  gains the multi-port-drive bullet; `POST-6` step 1b, `TH-15` step 1,
  `PORT-14` step 1b and `EX-49` opened; seven-item queue.

## Automation health

- **4 of 4 scheduled slots landed**, all journaled, all on the first
  attempt — 16 of 16 over the last four intervals. Container Up ≈ 36 h
  continuously.
- **Foreground-executor rule: 38 for 38** since written. No docker-socket
  denial this interval (**3 of 53** slots overall; 0 of the last 13). No
  compute-safety event, no allowlist denial.
- Two negative results journaled as negatives with their bands untouched
  and the tests left deliberately red — the protocol working as written;
  every slot re-read its digits from the log rather than the executor's
  report.
- Tier labels: `POST-6` and `PORT-14` heavy by ceiling (146 / 105 s);
  `PORT-15` smoke (4 s; the §7 tier column corrected); `TH-15` step 0
  standard, ≤ 48 s per window.
- **Housekeeping:** `attempts.md` at 18 684 lines vs the 6 000 budget —
  the 2026-09-06 weekly's rotation. 1 188 logs; volume within policy.

## On deck (§9 — seven items; 1, 5 and 6 name their executors)

1. **`EX-48`** — the ring rung's quarter turn in ParaView: P17 and P21
   fields in one file, the C16 column identity between two solved columns,
   wrong-rotation control ≥ 14× *(`example-runner`; ≈ 200 s at `-n 4`)*
2. **`POST-6` step 1b** — the power-wave identity `P_acc,k = supplied −
   sheets` per single drive at 1e-6, the single-drive form of the
   drive-level identity printed beside the superposed one *(implementer;
   ≈ 150 s, no new solve)*
3. **`TH-15` step 1** — the PEC sphere as a hole: `n × E = 0` on a tagged
   cavity, gated on the exterior dipole coefficient β = 1 within 4.9%,
   natural cavity (β = −½, 30× ceiling) as the control *(implementer;
   ≈ 1 min)*
4. **`PORT-14` step 1b** — the L and C terminations re-measured on two
   conductor-resolution rungs, residuals printed, band unmoved
   *(implementer; one rung per window, ≤ 600 s each)*
5. **`GEO-25` step 2** — the F-human gate: 504 642-cell record, CAD
   identities and `CAD_MASS_GATE` as executed asserts, branch A as the
   below-gate control *(implementer; ≈ 4 min)*
6. **`EX-49`** — an asymmetric two-port drive through
   `ports.superpose_drives` beside the quadrature drive, linearity between
   the halves and the sum asserted, `P_acc` printed with its caveat
   *(`example-runner`; ≈ 150 s at `-n 2`)*
7. **`MAT-6` step 11** — the slab-refined Dodd–Deeds fixture to production,
   ΔR re-recorded at 0.28% within 0.05 pp *(implementer +
   `record-reconciler`; ≈ 20–25 min; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
