# FEM-EM Solver — status

**Updated:** 2026-09-03 03:00 daily review. Headline: **the repo has its
first coil-driven SAR gate, and the 32-ring-port layout turned out to have
no port height.** `WF-6` step 3h registered a C4 symmetry identity of
quadrant powers of the primal `σ|E|²` on the loaded birdcage at 10 MHz —
twelve integral pairs ≤ 1.52% against the unmoved 5% band — and step 3f′
showed the identity's headroom *grows* 5× when the phantom's cell size is
halved (0.30% worst on the fine mesh). Both audited. The pointwise SAR
asserts are retired to records that still assert they miss. **This is a
self-consistency identity on one fixture at fixed `h`: no absolute SAR, no
homogeneity, no C95.3, no Larmor, no convergence claim.** Separately,
`PORT-13` step 1 (first solve on the 16-leg / 32-ring-port high-pass mesh)
is **blocked**: `GEO-20`'s ring sheets are transverse sections with zero
extent along the drive, so the lumped-sheet model has no `h` — a geometry
gap, not a solver bug. `GEO-26` (longitudinal ring sheets) is opened and
queued first. `OPS-33` closed ✅ (audited; re-tiered to heavy). Source of
truth is `PROJECT_PLAN.md`; this page is a read-only digest for the human
operator.

## Weekly review digest (2026-09-02, unchanged from the weekly's own copy)

- **Pace, 08-30 → 09-02 (2.68 d):** 26 §4-✅ items (10 chunks + 16 steps),
  9.7/day, 62% physics; 30 of 32 implementer slots fired, every loss
  launcher-side (login, CLI pin), none on limits. Full ledger in §10.
- **Phase 5 exit re-assessed to ≈ 09-05…09 on F-small** — watch condition:
  `WF-6` step 3f printed by 09-06. **Met 09-02** (clause (a)); the SAR gate
  itself landed 09-02 19:30.
- **Rulings landed in §7:** `GEO-25` and `PORT-13` re-scoped with anchors
  and prices; `TH-12` closed ✅; `ANS-1` **adjudicated AGREE** (numbers
  private); `MAT-6` step 11 and `MAT-8` scoped; `OPS-32`, `EX-41` opened;
  `MAG-20` third rung killed; `ANS-2` not commissioned.
- **Deferred to 09-06:** the §7 archive rotation and the B1+ literature
  anchor. **New for the 09-06 weekly:** `PORT-13`'s re-scope assumed a
  port model the ring layout cannot support (see Waiting-on-you 3); Phase
  6's first solve now sits behind `GEO-26` steps 1–2.

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
   to the 0.11 image overnight (`OPS-33`); the tracked table's AED cells are
   blank by construction.
3. 🟡 **FYI, a design decision made for you — say so if you disagree:**
   the 32-ring-port high-pass layout's port sheets were emitted as the
   gap's *transverse* section (the `GEO-18` leg pattern copied to the
   rings). The lumped-sheet port model needs a sheet spanning the gap
   *along* the current, so those ports cannot be driven or terminated.
   The review ruled a new `ring_sheet_orientation="longitudinal"` mode
   (default unchanged, all existing records frozen) using the planar
   rectangle in the plane `u = R` — chord `2R·tan α` along the ring, `w`
   along `z`. The alternative (the horizontal trapezoid) was rejected
   because its height varies ±7% across the sheet. No action needed unless
   you want a different port geometry for the high-pass rings.
4. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
5. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
6. 🟡 FYI, watch item — **the CLI login expired overnight 09-01/02 and
   cost three sessions.** All twelve slots since ran normally; if the
   expiry is periodic, the next one lands on a weekend of unattended
   slots. Worth knowing the refresh interval.
7. FYI, no action — **`GEO-25` (the 30 cm coil cost probe) stays off the
   queue** (third rung predicted at 30 min of gmsh). Local `main` remains
   well ahead of origin (push is manual).

## Honest current state (digest of §2 — the coil-driven SAR row changed)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` (Waiting-on-you 1). `ans:3` / `ports:2` reproduction controls now at 1e-6 on the 0.11 image (`OPS-33` ✅) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated — **but the ring-gap sheets are transverse** | `mesh:6` / `mesh:7` re-footered on 0.11 (`EX-41` ✅). The 32-ring-port layout has no usable port sheet for the lumped model (`h = 0` measured, `PORT-13` 🚫); `GEO-26` (queue item 1) adds the longitudinal sheet as a non-default mode |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. The C4 identities improve 2.19% → 0.62% when the phantom's `h` is halved; the sample set is *not* the mechanism (ring-set control within 1.06 pp, step 3f′) and the anchor is one-sided with the fine reading recorded beside the coarse one. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 **one gate registered (`WF-6` step 3h, 09-02): C4 symmetry of quadrant powers, one fixture, 10 MHz, fixed `h`** | twelve integral pairs of the primal `σ\|E\|²` ≤ **1.5200%** vs the unmoved 5% band (coarse mesh), **≤ 0.2998%** on the 0.0075 phantom (3f′, printed); partition identity exact; mis-paired control 89–159× larger. Pointwise readings (25–41% primal, 2.5–9.5% estimator) are records, not gates. **No mirror identity (step 3i queued), no absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 3 deliberate/known** (was 11 — eight retired by 3h / 3f′ as predicted) | example-artifact census `dead=0 … exit=2` on `main` (staleness only). API sweep `violations=0` on all four roots |

## Recent activity (2026-09-02 18:00 → 2026-09-03 03:00)

- **19:30:** `WF-6` step 3h — the first coil-driven SAR gate: twelve
  integral C4 pairs (worst 1.5200%) and the quadrature spread (0.4641%)
  asserted at the unmoved 5% band; five pointwise asserts → records that
  still assert `> band`. `109 passed` / 194 s. Step ✅, chunk 🟡. Audited
  PASS (tier label corrected to heavy by measurement).
- **21:00:** `WF-6` step 3f′ — ring-set control on the 0.0075 phantom
  (eight identities within ±1.06 pp of the centroid set), one-sided
  `|B₁⁺|` anchor with fine records beside coarse, integral pairs on the
  fine mesh 0.022–0.300% (clause (a), headroom grows 5.1×). `54 passed` /
  117 s; three deliberate reds retired. Audited PASS; the one-sided re-read
  ratified by this review.
- **22:30:** `PORT-13` step 1 — **blocked, measured:** all 8 ring sheets on
  the 4-leg rung span ≤ 1.43e-17 m along the drive direction (29 s, no
  solve). Test parked on `attempt/PORT-13-20260903T033437Z`. Ruled
  SUPPORTED by a `log-pathologist` (with the "cannot terminate" clause
  softened to "no well-posed `h`; the model would run and integrate a
  normal trace"). 🚫.
- **00:00:** `OPS-33` — `ans:3`'s four records re-based to the 0.11 image,
  1e-6 reproduction control registered (misses ≤ 6.5e-10 on an independent
  solve; superseded digits fail by 2.98e-05 / 2.92e-05). 165 + 206 + 1 s.
  ✅ (audited PASS; re-tiered to heavy on the 206 s window).
- **03:00 review:** three audits (PASS / PASS / PASS, two tier relabels);
  the `PORT-13` ruling and `GEO-26` opened; the one-gate ruling (no second
  SAR gate on the estimator; mirror identity as integrals → step 3i; the
  quadrature mirror integral declared empty by ceiling); `EX-43` and
  `OPS-34` opened; queue rebuilt: five items.

## Automation health

- **4 of 4 scheduled slots fired**, three complete on the first window, one
  blocked on a measured prerequisite and correctly parked. Tree clean at
  every preflight. Container Up 7 days.
- **Foreground-executor rule: 17 for 17** since written. No docker-socket
  denial this interval (**3 of 32** slots overall).
- Two windows over the 180 s standard band (194 s, 206 s), both inside
  their wrapped ceilings; both relabelled by this review, no compute-safety
  event.
- Standing rule from `OPS-32`: an anchor on a generated artifact never says
  "unchanged" — it names what must be absent from the diff.

## On deck (§9 — five items, all independent; 3, 4 and 5 have specialist executors)

1. **`GEO-26` step 1** — `ring_sheet_orientation="longitudinal"` on
   `birdcage_port_domain`: the `u = R` rectangle per ring gap, five
   closed-form identities at `-n 2` and `-n 12` on the 4-leg rung, default
   unchanged; the parked `PORT-13` module becomes its control *(implementer;
   ≈ 40–70 s per width; step 2 at 16 legs if time allows)*
2. **`WF-6` step 3i** — the mirror identity as quadrant integrals on the
   four single drives, pre-computed from 3h's table at 1.75 / 1.53 / 0.34 /
   0.96% vs a 38% control; drops the stale printer clause *(implementer;
   ≈ 110 s)*
3. **`EX-43`** — quadrant powers of the primal `σ|E|²` on the loaded
   birdcage in ParaView, records imported from the gate module
   *(`example-runner`; ≈ 130 s)*
4. **`EX-42`** — `mat:1` prints the finite-wire-corrected Dodd–Deeds
   beside the filament form and the FEM ΔR *(`example-runner`; ≈ 60 s)*
5. **`OPS-34`** — measure `ports:1`'s terminated-`Z` records against the
   0.11 image; re-base only if stale *(`record-reconciler`; ≈ 3 min per
   window; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
