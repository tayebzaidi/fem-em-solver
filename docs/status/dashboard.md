# FEM-EM Solver — status

**Updated:** 2026-09-04 10:30 daily review. Headline: **the 32-ring-port
birdcage now has a reciprocal, passive, mirror-symmetric 4×4 sub-block,
and all four scheduled slots landed on the first try for the second
interval running.** `PORT-13` step 2 drove four ring ports over one
270 728-cell mesh at 10 MHz: the sub-block is reciprocal to 4e-13 against a
1e-3 band (with a 1%-column control at 7× the band to prove the gate has
teeth), every column is passive with an 8% margin, the top-ring drive is
the z-mirror of the bottom-ring drive to 0.03% on all 32 pairs, and the
power accounting closes at the same 9.68e-3 on all four drives. `OPS-37`
found the gate module's two-torus records 2.6e-4 stale on the 0.11 image
and re-based them under a 1e-6 control; `EX-45` and `EX-46` put the 16-leg
longitudinal rung and its first solved field in ParaView. All four
closures audited PASS. The full 32×32 is queued next, sized off the slower
of the two measured solve prices. **Still a self-consistency story on one
fixture family at 10 MHz at fixed `h`: no absolute SAR, no homogeneity, no
C95.3, no Larmor coil claim, no convergence claim, and at 16 legs four
columns are not a network.** Source of truth is `PROJECT_PLAN.md`; this
page is a read-only digest for the human operator.

## Weekly review digest (2026-09-02, unchanged from the weekly's own copy)

- **Pace, 08-30 → 09-02 (2.68 d):** 26 §4-✅ items (10 chunks + 16 steps),
  9.7/day, 62% physics; 30 of 32 implementer slots fired, every loss
  launcher-side (login, CLI pin), none on limits. Full ledger in §10.
- **Phase 5 exit re-assessed to ≈ 09-05…09 on F-small** — watch condition:
  `WF-6` step 3f printed by 09-06. **Met 09-02** (clause (a)); the SAR gate
  itself landed 09-02 19:30.
- **Rulings landed in §7:** `GEO-25` and `PORT-13` re-scoped with anchors
  and prices; `TH-12` closed ✅; `ANS-1` **adjudicated AGREE** (numbers
  private); `MAT-6` step 11 and `MAT-8` scoped; `OPS-32`, `EX-41` opened.
- **Deferred to 09-06:** the §7 archive rotation and the B1+ literature
  anchor. **New for the 09-06 weekly (from the dailies since):** `PORT-13`
  steps 1 and 2 landed and step 3 (the 32×32) is queued by the 09-04 10:30
  daily, sized to two cached-column windows; `MAT-6` step 11 is queued as a
  spare; the retention policy's open questions under `OPS-36`; the
  `attempts.md` rotation is overdue at 17 964 lines.

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
   census windows through `run_and_log.sh`" (from the 03:00 review;
   `EX-44`'s pre-census left no log), and (b) "guide artifact references
   carry the full filename" — `EX-44` and `EX-45` each spent a census
   window on a bare `_facets.xdmf` reference read as dead. An interactive
   session can land both.
4. ✅ **Housekeeping budget — resolved by operator decision 2026-09-03:**
   gating logs are exempt from the 25 MB volume ceiling. Remaining under
   `OPS-36`: `attempts.md` rotation (the 2026-09-06 weekly's job), and a
   hand-run `--apply` must be committed by whoever runs it.
5. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
6. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
7. FYI, no action — physics worth a glance: the 03:00 note that driving one
   bottom-ring gap puts **89% of the incident wave onto the top-ring gap at
   the same azimuth** held up under step 2's mirror test — the top-ring
   drive's column is the z-mirror of the bottom-ring drive's to 0.03% on
   every one of the 32 pairs, so the ring-to-ring path through the legs
   is symmetric to the digit the mesh allows. The 32×32 (queued) will say
   whether the whole matrix is C16-symmetric and passive as a matrix, not
   just column by column. Local `main` remains well ahead of origin (push
   is manual).

## Honest current state (digest of §2 — one line changed this interval: the 16-leg rung)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅, shown by `mat:1`). Larmor coil loading stays an extrapolation. `MAT-6` step 11 (the refined fixture to production, headline → 0.28%) is queued as the spare |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; **16-leg: a 4×4 sub-block of 32** | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only.** 16-leg / 32 ring ports (`PORT-13` step 2, 2026-09-04): 4×4 reciprocity 4.1e-13 vs 1e-3 (control 7×), column passivity 0.916 ≤ 1, mirror identity 0.03% vs 5%, power accounting 9.68e-3 vs 1e-2 on all four columns; **no 32×32, no σ_max on a full matrix, no C16 gate, no resonance or tuning claim** at 16 legs — step 3 queued. Absolute accuracy at Larmor is `ANS-4` (Waiting-on-you 1). `ans:3` / `ports:1` / `ports:2` and the `PORT-1` gate module's reproduction controls at 1e-6 on the 0.11 image (`OPS-33`, `OPS-34`, `OPS-37` ✅) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; the ring gap has a drivable (longitudinal) sheet mode on both rungs (`GEO-26` ✅); shown by `mesh:10` / `mesh:11` | 4-leg: 8/8 sheets at closed form to 1e-9, record 111 898. 16-leg: 32/32 sheets exact to 1e-12, record 270 728 at 2 and 12 ranks, terminal-area record band 2.0e-4 for that rung only (two-state triangulation, 10 of 32 low, ruled, measured, and visible as a per-port field in `mesh:11`) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. The C4 identities improve 2.19% → 0.62% when the phantom's `h` is halved; the sample set is *not* the mechanism (ring-set control within 1.06 pp, step 3f′). Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 two gates registered on one fixture at 10 MHz at fixed `h`: C4 rotation of quadrant powers (3h) and the single-drive mirror identity (3i); shown in ParaView by `ports:9` (`EX-43` ✅) | twelve rotation pairs ≤ 1.5200%, four mirror pairs ≤ 1.7527%, both vs the unmoved 5% band; mirror control 38% (≥ 21.8×), rotation control 89–159×; partition identity exact. Pointwise readings stay records. **No absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 3 deliberate/known**; example-artifact census `dead=0 exit=2` at `40b7be3`, 40 examples | API sweep `violations=0` on all four roots |

## Recent activity (2026-09-04 03:00 → 10:30)

- **04:30:** `PORT-13` step 2 — four drives over one mesh: 4×4 reciprocity
  4.1e-13 vs 1e-3 (1%-column control 7.045× the band), column passivity
  0.916 with 8.4% margin, top/bottom mirror worst pair 0.0308% vs 5%,
  power residual 9.68e-3 on all four columns to six digits. One window,
  149 s at 8 ranks (the box was light: a solve took 9 s, not 28). Audited
  PASS.
- **06:00:** `OPS-37` — the `PORT-1` gate module's v0.7.2 mutual ratios
  measured 2.6e-4 stale on 0.11 (its own digits agree with the example's
  to 2e-10), re-based, reproduction control tightened 2e-3 → 1e-6 with the
  old digits asserted to fail it by 260×; the heuristic control kept its
  2e-3 floor. Two windows, 179 / 173 s. Audited PASS (179 s is 1 s under
  the standard ceiling — flagged).
- **07:30:** `EX-45` — `mesh:11`, the 16-leg longitudinal rung with the
  two-state terminal triangulation as a per-port cell field; 270 728 cells
  exact, 10 of 32 low, free control 9.99e-5 inside (2e-5, 2e-4). 82 s. One
  census catch (a guide reference without its filename prefix), fixed.
  Audited PASS.
- **09:00:** `EX-46` — `ports:10`, the first field on the 32-ring-port coil
  in ParaView: residual 9.68e-3, supplied power reproducing step 1 to
  3e-11, opposite pair 0.35%, control 4.14×. 103 s at 4 ranks. Audited
  PASS with one disclosed scope breach: an additive return key in the gate
  module, re-verified by a real gate re-run after the executor's "re-ran
  green" claim was found unsupported.
- **10:30 review:** §2's 16-leg sentence now carries the 4×4; `PORT-13`
  step 3 scoped (two cached-column windows + assembly, sized off the slower
  price); `OPS-38` opened (the XDMF helper learns facet tags; three
  examples stop improvising); `EX-47` opened (the mirror pair in ParaView);
  `MAT-6` step 11 queued as spare; two standing rules written (the
  additive licence for examples, full-filename guide references); four
  audits PASS; queue rebuilt to five items.

## Automation health

- **4 of 4 scheduled slots landed**, all journaled, all §4-complete on the
  first attempt — 8 of 8 over the last two intervals. Container Up ≈ 18 h
  continuously.
- **Foreground-executor rule: 30 for 30** since written. No docker-socket
  denial this interval (**3 of 45** slots overall). No compute-safety
  event.
- One executor report claimed a gate re-run that had not happened; the
  slot caught it and ran the gate itself. That is the verification rule
  working as intended, and it is why item 1 makes the step-2 re-run
  explicit.
- Tier labels: `PORT-13` step 2 and `EX-46` heavy by ceiling, measured
  standard (machine load — the prices stand); `OPS-37` standard with 1 s
  of headroom.
- **Housekeeping:** `attempts.md` at 17 964 lines vs the 6 000 budget — the
  2026-09-06 weekly's rotation. Log volume within policy.

## On deck (§9 — five items; 2 and 4 have specialist executors)

1. **`PORT-13` step 3** — the full 32×32: two 16-drive solve windows with
   cached columns (sized 215–560 s each off step 1's price), one assembly
   window asserting reciprocity at 1e-3, `σ_max ≤ 1`, the 18-class C16 ×
   mirror identity at 5%, and the step-2 column sums at 1e-6; 1%-column
   control at 2.5× (bar 2×) *(implementer; ≈ 8–20 min at `-n 8`)*
2. **`EX-47`** — the ring rung's mirror pair in ParaView: `|E|` for the
   P17 and P33 drives in one file, the 2×2 sub-block and its reciprocity;
   control ceiling 9.3× *(`example-runner`; ≈ 200 s at `-n 4`)*
3. **`OPS-38`** — `write_xdmf_with_tags` learns facet tags, gated by a
   unit-cube round-trip (tagged face area 1.000000000000); `ports:10`,
   `mesh:10`, `mesh:11` move onto it *(implementer; ≈ 6 min)*
4. **`GEO-25` rungs 1–2** — the 30 cm coil cost probe at 0.07 and 0.10 m,
   rung 3 only if rung 2 prices it under 600 s *(`mesh-probe`; ≈ 5 + 12
   min)*
5. **`MAT-6` step 11** — the slab-refined Dodd–Deeds fixture to production,
   ΔR re-recorded at 0.28% within 0.05 pp, §2's headline moved in the same
   commit *(implementer + `record-reconciler`; ≈ 20–25 min; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
