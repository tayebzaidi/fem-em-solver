# FEM-EM Solver — status

**Updated:** 2026-09-03 18:00 daily review. Headline: **the 16-leg ring-gap
mesh the first 32-port solve needs now exists, and that solve is unblocked.**
`GEO-26` step 2 built the longitudinal ring-gap sheet on the 16-leg rung:
all 32 sheets reconstruct at their closed forms to 1e-12, both port halves at
closed-form volumes, a new 270 728-cell record identical at 2 and 12 ranks —
and it stopped, as pre-registered, on one terminal-area reading (two
azimuth classes at 1.0e-4 against a 2.0e-5 record band). **This review ruled
the reading acceptable**: it is a mesh-reproducibility record on the terminal
disks, not a physics band; the sheet the port model integrates over is exact;
the fix is a per-rung record band (queue item 3) and `PORT-13` step 1, the
first solve on that layout, is unblocked (queue item 4). `EX-42` landed
(`mat:1` prints the finite-wire Dodd–Deeds correction, reproducing `MAT-8`)
and its logged census restored `EX-43` to ✅ (both audited PASS). Interactive
work landed a README/CI consolidation (`OPS-35`, audited PASS) and a log
retention policy with its first sweep (`OPS-36`; 111 → 61 MB of logs). Two of
four implementer slots were lost: one to a host reboot, one to that sweep
sitting staged and uncommitted — landed by this review. **Still a
self-consistency story on one fixture at 10 MHz at fixed `h`: no absolute
SAR, no homogeneity, no C95.3, no Larmor, no convergence claim.** Source of
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
  private); `MAT-6` step 11 and `MAT-8` scoped; `OPS-32`, `EX-41` opened.
- **Deferred to 09-06:** the §7 archive rotation and the B1+ literature
  anchor. **New for the 09-06 weekly (from the dailies since):** `PORT-13`
  is unblocked on the longitudinal sheets (first solve queued); the
  retention policy's three open questions under `OPS-36` (below); the
  `attempts.md` rotation is overdue at 17 271 lines.

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
3. 🟡 **Housekeeping over budget — a policy question, not a cleanup:** the
   retention policy you adopted today sets a 25 MB ceiling on tracked logs,
   but after the first sweep the volume is 61.1 MB and cannot go lower —
   824 of the 1 130 logs are cited by the plan, the archive, known-issues
   or an example guide, and the policy (rightly) never deletes those. So
   `housekeeping.py --check` will report a breach every week. Either raise
   the ceiling to what gating logs cost (≈ 60 MB today, growing with every
   closure), or say that gating logs are exempt from the volume budget.
   Nothing is lost either way; this is only about what the tripwire means.
   Two smaller items under the same `OPS-36` row: `attempts.md` is at
   17 271 lines against a 6 000 ceiling (the Sunday weekly's rotation, no
   action from you), and a hand-run `housekeeping.py --apply` leaves its
   sweep staged and uncommitted — that cost one implementer slot today
   before this review landed it. If you run it by hand again, commit it.
4. 🟡 **FYI, a design decision made for you — say so if you disagree:**
   the 16-leg longitudinal ring-gap rung's terminal disks triangulate in
   one of two ways (two discrete areas 1.0e-4 apart, five of sixteen gap
   azimuths on the low one). This review ruled it acceptable for the port
   model — every terminal is inside its closed-form band, the sheet the
   port integrates over is exact, and 1e-4 is a decade under the loosest
   port-level band — and gave the 16-leg rung its own record band (2.0e-4)
   rather than widening the 4-leg one. The alternative, classifying the
   terminals by the measured two-state partition, was rejected as fitting
   the test to the artifact. No action unless you want the ring-port
   geometry changed instead.
5. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
6. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
7. FYI, no action — **`OPS-35`'s verification logs came from a second
   machine** (`Host: unknown`, a hardened-kernel Linux box, a clone under a
   different path) — the first logs in the corpus not from the shared box.
   The in-container run matches the canonical image, so the audit passed;
   noting it so the provenance is on record. Also FYI: the 13:30 slot was
   lost to a host reboot (≈ 13:44 local), the first loss below cron; the
   next slot restarted the container itself. Local `main` remains well
   ahead of origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval; one queue pointer refreshed)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅, now shown by `mat:1`). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` (Waiting-on-you 1). `ans:3` / `ports:2` reproduction controls at 1e-6 on the 0.11 image (`OPS-33` ✅) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; the ring gap has a drivable (longitudinal) sheet mode on **both** rungs (`GEO-26` steps 1–2) | 4-leg: 8/8 sheets at closed form to 1e-9, record 111 898. 16-leg: 32/32 sheets exact to 1e-12, record **270 728** at 2 and 12 ranks; one terminal-area record band pending (queue item 3, ruled). `PORT-13` (first 32-port solve) **unblocked** — queue item 4 |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. The C4 identities improve 2.19% → 0.62% when the phantom's `h` is halved; the sample set is *not* the mechanism (ring-set control within 1.06 pp, step 3f′). Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🟡 **two gates registered on one fixture at 10 MHz at fixed `h`: C4 rotation of quadrant powers (3h) and the single-drive mirror identity (3i)**; shown in ParaView by `ports:9` (`EX-43` ✅) | twelve rotation pairs ≤ **1.5200%**, four mirror pairs ≤ **1.7527%**, both vs the unmoved 5% band; mirror control 38% (≥ 21.8×), rotation control 89–159×; partition identity exact. Pointwise readings stay records. **No absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); the coil case above is a symmetry identity, not an accuracy gate |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 4 deliberate/known** (the new one is `GEO-26`'s `[16]` terminal band, ruled, queue item 3 re-greens it); example-artifact census `dead=0 exit=2` at `2730af3` | API sweep `violations=0` on all four roots |

## Recent activity (2026-09-03 10:30 → 18:00)

- **12:00:** `GEO-26` step 2 — the longitudinal ring sheet at 16 legs:
  32 sheets exact, C32 spread 6.0e-16, record 270 728 at both widths, the
  default control at 265 621 exactly; **stopped, as pre-registered**, on two
  terminal classes at 1.0e-4 vs the 2.0e-5 band (160 / 158 s). Known-issues
  entry filed, band not widened; a deliberate red on `main`.
- **13:30:** slot lost — host reboot ≈ 13:44 local; no launcher log.
- **13:43 (interactive, second machine):** `OPS-35` — README, CONTRIBUTING,
  MkDocs, CI and Dockerfile consolidation; smoke suite 16 passed. Audited
  PASS.
- **14:30 / 16:13 (interactive):** `OPS-RETENTION` → §7 `OPS-36` — retention
  policy, harness chatter filter (verified on a synthetic log), weekly cron
  sweep; the first sweep run by hand and left staged.
- **15:00:** `EX-42` — `mat:1` prints the finite-wire Dodd–Deeds correction
  +0.115237% ΔR / +0.144814% ΔX, reproducing `MAT-8` at 1e-6; its pre-census
  (`dead=0`, logged) restored `EX-43` to ✅. 64 s. Both audited PASS.
- **16:30:** slot stopped on the staged sweep (1 930 index entries) —
  journaled, nothing touched, `OPS-34` not attempted.
- **18:00 review:** landed the sweep as `ce64659` after checking every
  plan-cited log survives; ruled the terminal bistability; unblocked
  `PORT-13`; opened `OPS-36`; three audits (PASS / PASS / PASS); queue
  rebuilt: five independent items.

## Automation health

- **2 of 4 scheduled slots landed**, both journaled. One lost to a host
  reboot (no launcher log — the first loss below cron), one stopped
  correctly on a dirty tree (first encounter, journal only). Container was
  down at the 15:00 preflight and restarted cleanly.
- **Foreground-executor rule: 22 for 22** since written. No docker-socket
  denial this interval (**3 of 37** slots overall).
- Tier labels: `GEO-26` step 2 declared heavy, measured 158–160 s (inside
  standard — over-declared, not mislabelled); `EX-42` 64 s standard. No
  compute-safety event.
- **Housekeeping:** first retention sweep landed (821 compressed, 287
  deleted, 111.3 → 61.1 MB). `--check` still breaches log volume and
  `attempts.md` — see Waiting-on-you 3.

## On deck (§9 — five items, all independent; 1, 2 and 5 have specialist executors)

1. **`OPS-34`** — measure `ports:1`'s terminated-`Z` records against the
   0.11 image; re-base only if stale *(`record-reconciler`; ≈ 3 min per
   window)*
2. **`EX-44`** — the longitudinal ring-gap sheet on the 4-leg rung in
   ParaView, inner/outer halves tagged, records imported from the gate
   module *(`example-runner`; ≈ 70 s)*
3. **`GEO-26` step 3** — the 16-leg rung's own terminal-area record band
   (2.0e-4, `[16]` only; 4-leg bands unmoved), low-state count printed,
   control pointed back at 2.0e-5 must fail; on green the chunk closes
   *(implementer; ≈ 160 s per window, three windows)*
4. **`PORT-13` step 1** — the first solve on the 32-ring-port layout with
   the longitudinal sheets, `h` = the gap chord, cell control 270 728;
   power accounting at 1e-2 and the opposite-port pair at 5%
   *(implementer; ≈ 3–6 min at `-n 8`; unblocked)*
5. **`GEO-25` rungs 1–2** — the 30 cm coil cost probe at 0.07 and 0.10 m,
   rung 3 only if rung 2 prices it under 600 s *(`mesh-probe`; ≈ 5 + 12
   min; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
