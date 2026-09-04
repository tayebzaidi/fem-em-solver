# FEM-EM Solver — status

**Updated:** 2026-09-04 18:00 daily review. Headline: **the 32-ring-port
birdcage now has a full 32×32 S-matrix that is reciprocal, passive and
C16 × mirror symmetric as a matrix, and the operator's Ansys feature
ladder is queued in its order.** `PORT-13` step 3 assembled 32 drives over
two independently built meshes at 10 MHz: reciprocity 5.4e-13 against a
1e-3 band (1%-column control at 2.5× the band, the computed ceiling),
σ_max = 0.999999452 (passive, by 5.5e-7), all 18 symmetry classes inside
5% with the worst at 0.44%, every power residual inside 1e-2. `EX-47` put
the mirror pair in ParaView, `OPS-38` gave the XDMF helper facet tags so
the rung's three examples share one write path, and the `GEO-25` cost
probe **refuted the r³ scaling** the F-human plan was dated on: the 30 cm
coil meshes to 504 642 cells in 112 s at fixed sizing (exponent ≈ 0.84),
and scaling the sizing with the radius drops conductor mass recovery below
the existing 0.95 gate. Three closures audited PASS; **`GEO-25` was
demoted ✅ → 🧪** on the plan's own rule (a measurement-only probe carries
no executed assertion) with its gate step scoped and queued. **Still a
self-consistency story on one fixture family at 10 MHz at fixed `h`: no
absolute SAR, no homogeneity, no C95.3, no Larmor coil claim, no
convergence claim, no resonance or tuning claim at 16 legs.** Source of
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
  steps 1–3 landed (the 32×32 exists); the `GEO-25` report is in and §10
  Phase 6's r³ cost paragraph and `TH-16`'s 62 GiB line need re-dating from
  the ≈ 0.84 exponent; the branch-A mass-recovery finding argues for fixed
  absolute sizing as the F-human scaling; two operator directives landed
  09-04 (the conductor model `TH-15` → `TH-14` → `ANS-6`, and the Ansys
  feature ladder Tiers A/B/C) with a §10 Phase 6 subgoal to own; the
  `attempts.md` rotation is overdue at 18 306 lines.

## Waiting on you

1. 🟢 **`ANS-4` is ready to replicate — both halves exist, and the
   private-mode writer is in place** (`OPS-32` ✅): drop the AED results
   JSON into the gitignored `aed_results/`, re-run the example, and the
   filled comparison goes only to the untracked `COMPARISON_private.md`.
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/`. Run the
   **low-order pair only** (Zero Order for adjudication, default First
   Order for sensitivity; Mixed Order not) — `ANS-1` showed the
   higher-order flag is silently ignored with a winding excitation. Please
   confirm the unknowns-per-tet figure AED prints. Ranks above `ANS-3`.
2. 🟢 **`ANS-3` AED run** — still yours, behind `ANS-4`. Same low-order
   rule, same private-results handling. Its FEM-side records were re-based
   to the 0.11 image (`OPS-33`); the tracked table's AED cells are blank by
   construction.
3. 🟡 **Two one-line edits to `.claude/agents/example-runner.md`, if you
   agree** (the sandbox denies writes under `.claude/agents/`, so both
   rules currently live in §9 and in each queued example item): (a) "both
   census windows through `run_and_log.sh`", and (b) "guide artifact
   references carry the full filename". An interactive session can land
   both.
4. 🟡 **One line for `.claude/agents/mesh-probe.md`, same reason:** its
   definition says "never an assertion", which is right — but a review
   commissioned `GEO-25` with "anchors, asserted per rung" and the same
   executor, and the audit had to demote the result on the plan's own
   measurement-only rule. The §9 items now say "🧪 by the §3 rule" in the
   first line of every probe; a matching sentence in the agent file
   ("report that the row stays 🧪 until a gate step lands") would close
   the loop from the other side.
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
8. FYI, no action — physics worth a glance: **the whole 32×32 is
   C16-symmetric and passive as a matrix**, not just column by column, and
   the σ_max margin is 5.5e-7 — tight, but on the passive side, and not in
   the band the item had reserved for the known 1% accounting offset. The
   ring-to-ring path carries 89% of the incident wave to the same-azimuth
   port on the other ring at every one of the 16 azimuths (class spread
   0.046%). The F-human coil is cheap to *mesh* (half a million cells);
   what the 62 GiB wall really measures is the solve, and that estimate is
   now due a redo. Local `main` remains well ahead of origin (push is
   manual).

## Honest current state (digest of §2 — one line changed this interval: the 16-leg rung)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | ⬜ none — every conductor is a solved-inside volume with σ capped by the mesh (800 S/m coil) | `TH-15` (PEC bodies) → `TH-14` (copper via Leontovich) → `ANS-6` commissioned 09-04 by operator directive; `TH-15` step 0 (mesh probe) queued |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅, shown by `mat:1`). Larmor coil loading stays an extrapolation. `MAT-6` step 11 (the refined fixture to production, headline → 0.28%) is the spare |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; **16-leg / 32 ring ports: the full 32×32 at 10 MHz** | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only.** 16-leg (`PORT-13` step 3, 2026-09-04): 32×32 reciprocity 5.4e-13 vs 1e-3 (control 2.5×), σ_max 0.999999452 ≤ 1, 18 C16 × mirror classes ≤ 0.44% vs 5%, 32 residuals ≤ 9.7e-3 vs 1e-2 — **network-level self-consistency on one fixture at 10 MHz, degree 1; no absolute accuracy, no resonance, tuning or mode-spectrum claim.** Absolute accuracy at Larmor is `ANS-4` (Waiting-on-you 1). RLC sheets and the circuit layer (`PORT-14`, `PORT-15`) queued |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; shown by `mesh:10` / `mesh:11`; **F-human (0.15 m) priced, 🧪** | 4-leg record 111 898; 16-leg record 270 728 at 2 and 12 ranks, 32/32 sheets exact. F-human: 504 642 cells / 112 s at fixed sizing, CAD identities hold at every rung — a probe, not a gate; `GEO-25` step 2 (the gate) queued |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. Still **no homogeneity, absolute or tuning claim**. `POST-6` step 1 (the package-level multi-port drive, HFSS *Edit Sources*) queued first |
| Coil-driven SAR | 🟡 two gates registered on one fixture at 10 MHz at fixed `h`; shown by `ports:9` | twelve rotation pairs ≤ 1.52%, four mirror pairs ≤ 1.75%, both vs 5%; partition identity exact. **No absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 3 deliberate/known**; example-artifact census `dead=0 exit=2` at `604151e`, 41 examples | API sweep `violations=0` on all four roots |

## Recent activity (2026-09-04 10:30 → 18:00)

- **12:00:** `PORT-13` step 3 — the full 32×32 from two 16-drive windows
  (274 / 271 s at 8 ranks) and one assembly window: reciprocity 5.4e-13,
  σ_max 0.999999452, worst class 0.44%, step 2's four columns reproduced
  at 1e-10. Audited PASS.
- **13:30:** `EX-47` — `ports:11`, the P17 / P33 mirror pair in one file:
  2×2 reciprocity 1.4e-13, control 9.9× the band, worst mirror pair 0.03%.
  110 s at 4 ranks; no `tests/` change. Audited PASS.
- **14:46 / 14:56 (interactive):** two operator directives landed in the
  plan — the conductor model (`TH-15` → `TH-14` → `ANS-6`) and the Ansys
  feature ladder (Tiers A/B/C, ranked once so reviews queue in that order).
- **15:00:** `OPS-38` — the XDMF helper learns facet tags (unit-cube face
  area 1.0 within 1e-12 on read-back); `ports:10` / `mesh:10` / `mesh:11`
  on one write path. One disclosed `src/` guard, gated by the slot's own
  re-run. Audited PASS.
- **16:30:** `GEO-25` — the F-human cost probe: control exact, all three
  rungs on both scaling readings, r³ refuted (exponent ≈ 0.84 at fixed
  sizing), and the scaled-sizing branch fails the conductor-mass gate at
  0.15 m. Audited **DEMOTE → 🧪** (measurement-only, by the plan's rule);
  measurements untouched, gate step scoped.
- **18:00 review:** `GEO-25` → 🧪 with step 2 scoped; the ladder queued in
  order (`POST-6`, `PORT-14`, `PORT-15` step 1, `TH-15` step 0); `EX-48`
  opened (the rotation pair and the C16 column identity); one ruling on
  after-the-fact `src/` guards; seven-item queue.

## Automation health

- **4 of 4 scheduled slots landed**, all journaled, all on the first
  attempt — 12 of 12 over the last three intervals. Container Up ≈ 27 h
  continuously.
- **Foreground-executor rule: 34 for 34** since written. No docker-socket
  denial this interval (**3 of 49** slots overall; 0 of the last 9). No
  compute-safety event.
- One executor claim ("unchanged by construction") replaced by a real
  gate run by the slot; one review-side commissioning conflict
  (assert-vs-probe) caught by audit and corrected in the plan.
- Tier labels: `PORT-13` step 3 heavy as declared; `EX-47` standard;
  `OPS-38` smoke + standard; `GEO-25` heavy by ceiling, measured ≤ 127 s
  per rung.
- **Housekeeping:** `attempts.md` at 18 306 lines vs the 6 000 budget — the
  2026-09-06 weekly's rotation. Log volume within policy.

## On deck (§9 — seven items; 4, 5 and 6 name their executors)

1. **`POST-6` step 1** — `ports.superpose_drives`, the package-level
   multi-port drive: reproduces `WF-6` step 2's quadrature digits at 1e-6,
   linearity at 1e-12, accepted power vs volume loss at the fixture's 1e-2
   band *(implementer; ≈ 2–3 min at `-n 2`)*
2. **`PORT-14` step 1** — a complex `Z_p` on a terminated sheet; the
   termination-reduction identity at 1e-3 for C, L and R at 10 MHz on the
   4-leg fixture, control ceiling computed in-run *(implementer; ≈ 3–4 min)*
3. **`PORT-15` step 1** — the high-pass birdcage ladder closed form and the
   termination reduction as pure-numpy identities at 1e-12, no FEM
   *(implementer; seconds)*
4. **`TH-15` step 0** — can OCC deliver the two-torus conductor as a hole
   with the port sheet still attached? A measurement, 🧪 by rule
   *(`mesh-probe`; four windows ≈ 4 min)*
5. **`EX-48`** — the ring rung's quarter turn in ParaView: P17 and P21
   fields in one file, the C16 column identity between two solved columns,
   wrong-rotation control ≥ 14× *(`example-runner`; ≈ 200 s at `-n 4`)*
6. **`GEO-25` step 2** — the F-human gate: 504 642-cell record, CAD
   identities and `CAD_MASS_GATE` as executed asserts, branch A as the
   below-gate control *(implementer; ≈ 4 min)*
7. **`MAT-6` step 11** — the slab-refined Dodd–Deeds fixture to production,
   ΔR re-recorded at 0.28% within 0.05 pp *(implementer +
   `record-reconciler`; ≈ 20–25 min; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
