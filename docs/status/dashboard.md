# FEM-EM Solver — status

**Updated:** 2026-09-04 03:00 daily review. Headline: **the first field on
the 16-leg, 32-ring-port birdcage exists, and all four scheduled slots
landed on the first try.** `PORT-13` step 1 solved one driven ring port on
the 270 728-cell longitudinal rung at 10 MHz: the three-way power accounting
closes inside its imported 1e-2 band (residual 9.68e-3 — the same place the
4-leg fixture sits), the two ports diametrically opposite the driven one
agree to 0.35%, and a solve costs 28 s at 8 ranks — so a 4×4 sub-block
(reciprocity, passivity, the top/bottom mirror) is affordable in one window
and is queued as step 2; the full 32×32 is a later step. `GEO-26` closed
(the 16-leg rung's terminal-area band registered exactly as ruled, control
first, `[16]` green again), `OPS-34` found the two-torus example's records
2.6e-4 stale and re-based them with a 1e-6 control (measured scatter ~1e-9),
and `EX-44` put the longitudinal ring sheet in ParaView. All three closures
audited PASS. **Still a self-consistency story on one fixture family at
10 MHz at fixed `h`: no absolute SAR, no homogeneity, no C95.3, no Larmor
coil claim, no convergence claim, and at 16 legs one column is not a
network.** Source of truth is `PROJECT_PLAN.md`; this page is a read-only
digest for the human operator.

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
  step 1 landed and step 2 is queued — the 32×32 (step 3) needs column
  caching across windows and is the weekly's to rung; the retention
  policy's open questions under `OPS-36`; the `attempts.md` rotation is
  overdue at 17 615 lines.

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
3. 🟡 **One small permission, if you agree:** the 03:00 review wanted to
   add one line to `.claude/agents/example-runner.md` step 5 — "both
   census windows through `run_and_log.sh`" — because `EX-44`'s pre-census
   ran on the host and left no log. The sandbox denies writes under
   `.claude/agents/`, so the rule is written into the two queued example
   items instead. Landing it in the agent definition is a one-line edit
   for an interactive session.
4. ✅ **Housekeeping budget — resolved by operator decision 2026-09-03:**
   gating logs are exempt from the 25 MB volume ceiling. Remaining under
   `OPS-36`: `attempts.md` rotation (the 2026-09-06 weekly's job), and a
   hand-run `--apply` must be committed by whoever runs it.
5. ✅ **The 16-leg terminal-triangulation ruling landed as designed** (FYI
   from the 18:00 review, now closed): `GEO-26` step 3 registered the
   per-rung record band, the control pointed back at the old band failed
   exactly as pre-registered, and the census confirmed 10 of 32 terminals
   on the low state at both rank counts. No action unless you want the
   ring-port geometry changed instead.
6. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
7. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
8. FYI, no action — physics worth a glance: on the 32-ring-port coil at
   10 MHz, driving one bottom-ring gap puts **89% of the incident wave
   amplitude onto the top-ring gap at the same azimuth** (the P17 → P33
   entry of `S`, read from the printed currents), with every other port
   near 6%. That is the high-pass ring-to-ring path through the legs
   below resonance; step 2's mirror identity will test it. Local `main`
   remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — one line changed this interval: the 16-leg rung)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅, shown by `mat:1`). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; **16-leg: one column only** | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only.** 16-leg / 32 ring ports (`PORT-13` step 1, 2026-09-04): power accounting 9.68e-3 vs 1e-2, opposite pair 0.35% vs 5%, 28 s per solve; **no 32×32, no reciprocity, no C16 gate, no resonance or tuning claim** at 16 legs. Absolute accuracy at Larmor is `ANS-4` (Waiting-on-you 1). `ans:3` / `ports:1` / `ports:2` reproduction controls at 1e-6 on the 0.11 image (`OPS-33`, `OPS-34` ✅) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; the ring gap has a drivable (longitudinal) sheet mode on both rungs (`GEO-26` ✅) | 4-leg: 8/8 sheets at closed form to 1e-9, record 111 898. 16-leg: 32/32 sheets exact to 1e-12, record 270 728 at 2 and 12 ranks, terminal-area record band 2.0e-4 for that rung only (two-state triangulation, 10 of 32 low, ruled and measured) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. The C4 identities improve 2.19% → 0.62% when the phantom's `h` is halved; the sample set is *not* the mechanism (ring-set control within 1.06 pp, step 3f′). Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 two gates registered on one fixture at 10 MHz at fixed `h`: C4 rotation of quadrant powers (3h) and the single-drive mirror identity (3i); shown in ParaView by `ports:9` (`EX-43` ✅) | twelve rotation pairs ≤ 1.5200%, four mirror pairs ≤ 1.7527%, both vs the unmoved 5% band; mirror control 38% (≥ 21.8×), rotation control 89–159×; partition identity exact. Pointwise readings stay records. **No absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 3 deliberate/known** (`[16]` re-greened by `GEO-26` step 3); example-artifact census `dead=0 exit=2` at `2758f4b`, 38 examples | API sweep `violations=0` on all four roots |

## Recent activity (2026-09-03 18:00 → 2026-09-04 03:00)

- **19:30:** `OPS-34` — the `ports:1` terminated-`Z` records measured
  2.6e-4 stale against the 0.11 image, re-based at `repr()` precision,
  reproduction control tightened 2e-3 → 1e-6 with the old digits asserted
  to fail it; run-to-run scatter measured ~1e-9. Three windows, 143 s
  each. Audited PASS.
- **21:00:** `EX-44` — `mesh:10`, the longitudinal ring sheet on the 4-leg
  rung in ParaView, both cell records exact, eight sheets at
  1.000000000000, the transverse control fourteen decades away. 59 s.
  Audited PASS (caveat: its pre-census ran outside the harness).
- **22:30:** `GEO-26` step 3 — control first (`[16]` at the old band fails
  to the digit), then the 2.0e-4 band registered for the 16-leg rung only,
  green at 2 and 12 ranks, census 10 of 32 low; known-issues entry
  retired; **`GEO-26` ✅**. Four windows, 221–226 s (heavy). Audited PASS.
- **00:00:** `PORT-13` step 1 — **the first solve on the 32-ring-port
  coil**: 270 728 cells, `h` = the gap chord, power accounting 9.68e-3 vs
  1e-2, opposite pair 0.35%, 28 s per solve at 8 ranks, 5.7 GiB. 329 s.
  `PORT-13` → 🟡.
- **03:00 review:** §2's stale "no solve at 16 legs" sentence replaced;
  `PORT-13` step 2 scoped (4×4 sub-block, one window) with a ruling that
  the 0.97-of-band residual gets no new band; `OPS-37` opened for the gate
  module's stale records; two example chunks opened (`EX-45`, `EX-46`);
  three audits PASS; queue rebuilt to five items.

## Automation health

- **4 of 4 scheduled slots landed**, all journaled, all §4-complete on the
  first attempt — the first interval with no lost or stopped slot since the
  90-minute grid started. Container Up ≈ 13 h continuously.
- **Foreground-executor rule: 26 for 26** since written. No docker-socket
  denial this interval (**3 of 41** slots overall). No compute-safety
  event.
- Tier labels: `GEO-26` step 3 priced ≈ 160 s and measured 221–226 s
  (heavy) — the review's estimate was a two-case footer and the module
  now runs four cases; `PORT-13` step 1's executor sized its window to
  570 s rather than the item's 1200 s (which does not fit one foreground
  window) — the right call, and step 2 is sized to 600 s.
- **Housekeeping:** `attempts.md` at 17 615 lines vs the 6 000 budget — the
  2026-09-06 weekly's rotation. Log volume within policy after the
  operator's gating-log exemption.

## On deck (§9 — five items; 3 and 4 have specialist executors)

1. **`PORT-13` step 2** — four drives over one mesh (P17, its top-ring
   partner, the two opposites): 4×4 reciprocity at 1e-3, column passivity,
   the top/bottom mirror at 5%, power accounting per column; `S` read
   directly from the matched drives, no `Z` inversion *(implementer; ≈ 430 s
   at `-n 8`)*
2. **`OPS-37`** — the `PORT-1` step-4 gate module's two v0.7.2 ratios
   re-based onto 0.11 and its reproduction control tightened to 1e-6, the
   heuristic control keeping its 2e-3 floor *(implementer; two windows
   ≈ 155 s)*
3. **`EX-45`** — the 16-leg longitudinal rung in ParaView with the two-state
   terminal triangulation as a per-port field; free control = the 5× band
   separation *(`example-runner`; ≈ 150 s)*
4. **`EX-46`** — the first field on the 32-ring-port coil in ParaView:
   `|E|` on the sheets and phantom for the P17 drive, records imported
   from the step-1 module *(`example-runner`; ≈ 250 s at `-n 4`)*
5. **`GEO-25` rungs 1–2** — the 30 cm coil cost probe at 0.07 and 0.10 m,
   rung 3 only if rung 2 prices it under 600 s *(`mesh-probe`; ≈ 5 + 12
   min; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
