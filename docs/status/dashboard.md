# FEM-EM Solver — status

**Updated:** 2026-09-03 10:30 daily review. Headline: **the ring-gap port
sheet the lumped model can drive now exists, and the coil-driven SAR gate
has a second, independent identity.** `GEO-26` step 1 landed the
longitudinal ring-gap sheet as a non-default mesh mode on the 4-leg rung —
eight sheets reconstruct at their closed forms to 1e-9, both port halves at
their closed-form volumes, the default mesh byte-for-byte unchanged (audited
PASS). `WF-6` step 3i gated the mirror identity of quadrant SAR powers on
each single drive (four pairs ≤ 1.76% against the unmoved 5% band, control
at 38%) — a single-drive statement, so independent evidence rather than a
re-reading of step 3h's rotation identity (audited PASS). `EX-43` (quadrant
SAR powers in ParaView) ran green on every physics anchor but was
**demoted to 🧪 on audit**: its census figures are in no harness log; one
logged census restores it, and that ride is on the next queue item.
**Still a self-consistency story on one fixture at 10 MHz at fixed `h`: no
absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim.**
The 09:00 implementer slot was lost to an API overload at launch (no
session, nothing touched). Source of truth is `PROJECT_PLAN.md`; this page
is a read-only digest for the human operator.

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
  port model the ring layout cannot support; Phase 6's first solve now
  sits behind `GEO-26` step 2 (queue item 1) and is pre-queued as item 5.

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
3. 🟡 **FYI, a design decision made for you — say so if you disagree:**
   the longitudinal ring-gap sheet (the `u = R` rectangle, chord along the
   ring, `w` along `z`) is now the non-default `ring_sheet_orientation`
   mode; the transverse default and every existing record are frozen. The
   one measured side effect: the new sheet's edges are diameters of the
   terminal disks, so the terminal triangulation's C4 covariance reads
   1.6e-05 instead of 4e-08. **This review ruled it acceptable** — every
   terminal is inside its band, every exact identity is unmoved, and
   1.6e-05 is four decades under any port-level band. Recorded, not
   absorbed; the 16-leg rung re-measures it with the band unmoved. No
   action needed unless you want a different ring-port geometry.
4. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
5. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
6. 🟡 FYI, watch item — **the 09:00 slot today was lost to `API Error:
   529 Overloaded` at launch**, the first API-side loss on record (the
   09-01/02 losses were login and CLI-pin). One slot, no retry logic in
   the launcher; if it recurs the launcher could re-try once after a
   minute. No action unless you want that added.
7. FYI, no action — **`GEO-25` (the 30 cm coil cost probe) stays off the
   queue** (third rung predicted at 30 min of gmsh). Local `main` remains
   well ahead of origin (push is manual).

## Honest current state (digest of §2 — the coil-driven SAR row and the birdcage-mesh row changed)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` (Waiting-on-you 1). `ans:3` / `ports:2` reproduction controls at 1e-6 on the 0.11 image (`OPS-33` ✅) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; **the ring gap now has a drivable (longitudinal) sheet mode on the 4-leg rung** (`GEO-26` step 1 ✅, audited) | `mesh:6` / `mesh:7` re-footered on 0.11 (`EX-41` ✅). Longitudinal sheets: 8/8 at closed form to 1e-9 at `-n 2` and `-n 12`, default frozen at its 110 786-cell record. The 16-leg longitudinal record is queue item 1; `PORT-13` (first 32-port solve) stays 🚫 until it exists |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. The C4 identities improve 2.19% → 0.62% when the phantom's `h` is halved; the sample set is *not* the mechanism (ring-set control within 1.06 pp, step 3f′). Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 **two gates registered on one fixture at 10 MHz at fixed `h`: C4 rotation of quadrant powers (3h, 09-02) and the single-drive mirror identity (3i, 09-03)** | twelve rotation pairs ≤ **1.5200%**, four mirror pairs ≤ **1.7527%**, both vs the unmoved 5% band; mirror control 38% (≥ 21.8×), rotation control 89–159×; partition identity exact; ≤ 0.2998% on the 0.0075 phantom (3f′). Pointwise readings stay records. **No absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 3 deliberate/known**; example-artifact census **unmeasured since `8bf4d96`** (the `EX-43` gap — queue item 2's pre-census re-measures it) | API sweep `violations=0` on all four roots |

## Recent activity (2026-09-03 03:00 → 10:30)

- **04:30:** `GEO-26` step 1 — `ring_sheet_orientation="longitudinal"` on
  `birdcage_port_domain`: 8 sheets at chord × `w` to 1e-9, half volumes at
  closed form, C8 spread 4.3e-16, at `-n 2` (51 s) and `-n 12` (50 s); the
  default control reproduces 110 786 at ratio 1.000000; `GEO-20` regression
  3 passed (262 s). New record 111 898. Step ✅, chunk 🟡. Audited PASS.
  The parked `PORT-13` branch absorbed as the control and deleted.
- **06:00:** `WF-6` step 3i — the mirror identity as quadrant integrals on
  the four single drives: 1.7527 / 1.5261 / 0.3438 / 0.9563% vs 5%,
  flank-vs-opposite control 38%, every 3h anchor unmoved in the same
  window. `37 passed` / 96 s. Step ✅, chunk 🟡. Audited PASS.
- **07:30:** `EX-43` — `ports:9`, quadrant powers of the coil-driven SAR
  in ParaView; every imported record reproduced (partition residual
  1.6e-14, P1 total to 4e-11, C4 and mirror pairs to the printed digit),
  both negative controls asserted. 77 s. **Audited DEMOTE → 🧪**: the
  census figures were claimed but never logged. Re-closes on one logged
  census (queue item 2).
- **09:00:** slot lost — `API Error: 529 Overloaded` at launch, no session.
- **10:30 review:** three audits (PASS / PASS / DEMOTE); the terminal-
  triangulation ruling; §2's SAR bullet now carries both identities;
  `GEO-26` step 2 queued, `EX-44` opened, `PORT-13` step 1 pre-queued as
  the serial spare; queue rebuilt: five items.

## Automation health

- **3 of 4 scheduled slots fired**, all three complete on the first window
  and journaled. One slot lost API-side at launch (first such loss). Tree
  clean at every preflight. Container Up 7 days.
- **Foreground-executor rule: 20 for 20** since written. No docker-socket
  denial this interval (**3 of 35** slots overall).
- Tier labels honest on every landed window this interval (51/50, 96, 77 s
  standard by measurement); no compute-safety event.
- Standing rule from `OPS-32`: an anchor on a generated artifact never says
  "unchanged" — it names what must be absent from the diff. New this
  review: a census claimed in a journal without a harness log is not
  evidence (`EX-43`).

## On deck (§9 — five items; 1–4 independent, 5 serial on 1; 2, 3 and 4 have specialist executors)

1. **`GEO-26` step 2** — the longitudinal ring-gap sheet on the 16-leg
   rung: 32 sheets, C16, four terminal classes asserted under the unmoved
   2.0e-5 band, new cell record; the default reproduces 265 621
   *(implementer; ≈ 200 s per window, three windows)*
2. **`EX-42`** — `mat:1` prints the finite-wire-corrected Dodd–Deeds beside
   the filament form and the FEM ΔR; **its pre-census also restores
   `EX-43` to ✅ if it reads `dead=0`, `exit != 1`** *(`example-runner`;
   ≈ 60 s)*
3. **`OPS-34`** — measure `ports:1`'s terminated-`Z` records against the
   0.11 image; re-base only if stale *(`record-reconciler`; ≈ 3 min per
   window)*
4. **`EX-44`** — the longitudinal ring-gap sheet on the 4-leg rung in
   ParaView, inner/outer halves tagged, records imported from the gate
   module *(`example-runner`; ≈ 70 s)*
5. **`PORT-13` step 1** — the first solve on the 32-ring-port layout with
   the longitudinal sheets, `h` = the gap chord; **skip if item 1's record
   is not on `main`** *(implementer; ≈ 3–6 min at `-n 8`; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
