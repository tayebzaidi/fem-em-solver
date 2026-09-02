# FEM-EM Solver — status

**Updated:** 2026-09-02 03:00 daily review (the first scheduled session to
run since the CLI login expired overnight; the operator restored it and
ran the Wednesday weekly interactively at 02:15–02:55).
Headline: **the restricted `E` estimator is packaged
(`post.project_to_cg1_restricted`, `WF-6` step 3e) and the two filed 0.11
probe survivors are migrated (`OPS-30`); two overnight slots were lost to
the expired login, and the queue is rebuilt from the weekly's rulings —
eight items.** The weekly's finer-phantom rung (`WF-6` step 3f) could not be
queued as written: the birdcage constructor has no phantom-sizing knob, so
a mesh-only plumbing step (3f₀) is queued first and 3f follows it. **No SAR
claim exists and no band moved.** Source of truth is `PROJECT_PLAN.md`;
this page is a read-only digest for the human operator.

## Weekly review digest (2026-09-02, unchanged from the weekly's own copy)

- **Pace, 08-30 → 09-02 (2.68 d):** 26 §4-✅ items (10 chunks + 16 steps),
  9.7/day, 62% physics; 30 of 32 implementer slots fired, every loss
  launcher-side (login, CLI pin), none on limits. Full ledger in §10.
- **Phase 5 exit re-assessed to ≈ 09-05…09 on F-small** — watch condition:
  `WF-6` step 3f printed by 09-06 (now behind 3f₀, §9 items 4 and 7).
- **Rulings landed in §7:** `GEO-25` and `PORT-13` re-scoped with anchors
  and prices; `TH-12` closed ✅ on the re-affirmed production-order clause;
  `ANS-1` **adjudicated AGREE** (numbers private); `MAT-6` step 11 and
  `MAT-8` scoped; `WF-6` step 3f scoped; `OPS-32`, `EX-41` opened;
  `MAG-20` third rung killed; `ANS-2` not commissioned.
- **Agent value, first measurement:** 0 demotions / 6 audits (now 0 / 8
  after this review's two), pathologist 5 confirmed / 1 overruled,
  navigator 0 citation errors, example-runner 4/4 footered.
- **Deferred to 09-06:** the §7 archive rotation and the B1+ literature
  anchor.

## Waiting on you

1. 🟢 **`ANS-4` is ready to replicate — both halves exist.**
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/`. Run the
   **low-order pair only** (Zero Order for adjudication, default First
   Order for sensitivity; Mixed Order not) — `ANS-1` showed the
   higher-order flag is silently ignored with a winding excitation. Please
   confirm the unknowns-per-tet figure AED prints. Ranks above `ANS-3`.
   Results stay in the gitignored `aed_results/`; `OPS-32` (§9 item 5)
   gives this example the private-mode writer **before** numbers arrive —
   if you run AED before that lands, keep the JSON out of the tree until
   it has.
2. 🟢 **`ANS-3` AED run** — still yours, behind `ANS-4`. Same low-order
   rule, same private-results handling.
3. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
4. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
5. 🟡 FYI, watch item — **the CLI login expired overnight and cost three
   sessions** (22:30 and 00:00 implementer slots, the 02:15 weekly; all
   died at launch with `OAuth session expired and could not be refreshed`).
   You re-logged in and this 03:00 review ran normally, so nothing is
   needed now — but if the expiry is periodic, the next one lands on a
   weekend of unattended slots. Worth knowing the refresh interval.
6. ✅ FYI, no action — **`ANS-1` AED replication landed and was adjudicated
   AGREE** by the weekly (numbers held privately under Ansys licence terms;
   qualitative verdict in §7). Two follow-ons are scoped: `MAT-6` step 11
   (promote the 0.28% fixture) and `MAT-8` (finite-wire term, §9 item 3).
7. FYI, no action — **`GEO-25` (the 30 cm coil cost probe) is held off the
   queue** by this review: the weekly's third rung is predicted at 30 min
   of gmsh, past the 20-minute command ceiling. The 09-06 weekly should
   re-rung it (0.07 / 0.10 / 0.125 m) or give the 0.15 m rung its own
   slot. Local `main` remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — no quantitative row moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅ 09-02, production order: degree 1 coil-fed, degree 2 imposed-field). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 — the re-opening condition |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), **now bracketed from the other side by Maxwell 3D** (`ANS-1` AGREE, numbers private); Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` (Waiting-on-you 1) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated | production high-pass layout is an example (`EX-35` ✅); first solve on it is `PORT-13` step 1, now queued as the spare (§9 item 8) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅; these gates project **`B`** on the whole mesh (0.38%) and are untouched by the SAR findings. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🔴 **measured, not gateable; estimator exonerated and now packaged** | primal point SAR misses the five identities at 25–41%; the phantom-restricted CG1 `E` estimator (step 3d, packaged 3e as `post.project_to_cg1_restricted`) is honest — residual 18.72%, phantom power −3.51% — and the identities still miss at **6.1–9.5%**, verdict (c): the ~1.5 cm phantom cells. Next: estimator degree (3e′, item 2) and phantom h (3f₀ + 3f, items 4 and 7). Five deliberate reds on `main`, band unmoved. **No SAR claim exists** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never gated on a coil |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 8 deliberate/known** | example-artifact census `dead=0 guide=0 stale=0 exit=0` (09-01); `OPS-30` closed the last filed 0.11 migration gap — the API sweep reads `violations=0` on all four roots |

## Recent activity (2026-09-01 18:00 → 2026-09-02 03:00)

- **19:30:** `WF-6` step 3e — `post.project_to_cg1_restricted` packaged;
  every step-3d anchor reproduced to every printed digit through the
  packaged path (18.7238% vs 1876.1871%, 100.20× separation; phantom power
  5.440097168e-08 W; identities 8.2868 / 9.4743 / 7.3477 / 6.8146 /
  6.1185%). `5 failed, 69 passed` / Status 1 / **122 s**. No gate
  registered. 🟡.
- **21:00:** `OPS-30` — two `petsc_options_prefix` arguments; the API sweep
  went 2 → 0 violations on `examples`+`scripts` with the census unchanged
  (82 / 320 / 22) and `src`+`tests` unmoved (177 / 484 / 30,
  `violations=0`); the pin strengthened, not deleted. 12 + 37 s. ✅.
- **22:30, 00:00, 02:15:** all three launchers died on the expired login.
  No compute, no journal, nothing parked.
- **02:15–02:55, operator:** the weekly review run interactively
  (`f9462f0` … `944be5a`) plus `ANS-1`'s AED half (`14305c5`).
- **03:00 review:** `OPS-30` audited — `auditor` PASS on seven checks,
  DEMOTE on tier (37 s under a "smoke" label); ruled a scoping mislabel,
  **re-tiered to standard, stays ✅** (the `OPS-27` precedent). `TH-12`
  audited **PASS**. The step-3f knob gap found and 3f₀ scoped. The
  implementer protocol's stale `git commit -F` guidance corrected. Queue
  rebuilt: eight items.

## Automation health

- **2 of 4 scheduled slots fired**; both losses launcher-side (expired
  OAuth login), none on limits. Zero parked branches, tree clean at every
  preflight. Container Up 6 days.
- **Foreground-executor rule: 5 for 5** since written. No docker-socket
  denial this interval (**3 of 22** slots overall).
- Login restored; this 03:00 review is the first scheduled session since.
  CLI 2.1.258 ≥ 2.1.251 for the Fable 5.1 pin; live crontab carries
  `15 2 * * 0,3`. The tracked crontab file's header comment still says
  "Sunday 02:15" (folded into `OPS-31`, §9 item 1).

## On deck (§9 — eight items; 1–6 independent, 7 serial on 2 and 4, 8 the spare)

1. **`OPS-31`** — re-record the `ports:3` cross-route narrative to the
   0.11 image's **7.7431 → 1.0986 → 1.9222%** *(`record-reconciler`;
   ≈ 230 s)*
2. **`WF-6` step 3e′** — the estimator-degree rung: the five SAR identities
   off a **CG2**-restricted `E` through the packaged helper plus a
   `degree=` keyword; anchors are theorems *(implementer; ≈ 250–400 s)*
3. **`MAT-8`** — the finite-wire correction to the Dodd–Deeds closed form;
   filament limit to 1e-8, PEC limit to 1e-6, the 5 mm-wire correction
   printed beside the FEM 1.58% / 0.28% *(implementer; < 60 s)*
4. **`WF-6` step 3f₀** — `phantom_resolution` on `birdcage_port_domain`
   and its passthroughs; the no-op control (116 085 cells / 537 phantom
   cells at 0.000e+00) is the anchor *(implementer; mesh only, ≈ 60–120 s)*
5. **`OPS-32`** — private-mode comparison writers for `ANS-3`/`ANS-4`,
   reproduction controls re-registered at 1e-6 *(implementer; two runner
   windows ≈ 8–9 min)*
6. **`EX-41`** — `mesh:6` and `mesh:7` get a footered run *(`example-runner`
   foreground; ≈ 160 s)*
7. **`WF-6` step 3f** — the finer-phantom rung at `phantom_resolution =
   0.0075`, verdict (a)/(b)/(c) pre-registered *(implementer; serial on 2
   and 4; ≈ 150–200 s)*
8. **`PORT-13` step 1** — first single-port solve on the 32-ring-port
   layout, power accounting to 1e-2 *(implementer; heavy, `-n 8`, 590 s
   stop rule; spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
