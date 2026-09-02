# FEM-EM Solver — status

**Updated:** 2026-09-02 10:30 daily review. Headline: **four of four slots
landed green; the finite-wire term under Dodd–Deeds is +0.115% on ΔR
(`MAT-8` ✅), the phantom-sizing knob exists and is a measured no-op
(`WF-6` step 3f₀ ✅), and the estimator-degree rung came back with the
result nobody scoped for — a strictly better CG2 fit of `E` makes the
five coil-driven SAR identities *worse* (8–9% → 11–19%).** The projector
and the estimator degree are now both excluded as the mechanism; the
finer-phantom rung (3f) runs next and a new integral-form rung (3g) tests
the construction itself. **No SAR claim exists and no band moved.** Source
of truth is `PROJECT_PLAN.md`; this page is a read-only digest for the
human operator.

## Weekly review digest (2026-09-02, unchanged from the weekly's own copy)

- **Pace, 08-30 → 09-02 (2.68 d):** 26 §4-✅ items (10 chunks + 16 steps),
  9.7/day, 62% physics; 30 of 32 implementer slots fired, every loss
  launcher-side (login, CLI pin), none on limits. Full ledger in §10.
- **Phase 5 exit re-assessed to ≈ 09-05…09 on F-small** — watch condition:
  `WF-6` step 3f printed by 09-06 (now unblocked and §9 item 1).
- **Rulings landed in §7:** `GEO-25` and `PORT-13` re-scoped with anchors
  and prices; `TH-12` closed ✅; `ANS-1` **adjudicated AGREE** (numbers
  private); `MAT-6` step 11 and `MAT-8` scoped; `WF-6` step 3f scoped;
  `OPS-32`, `EX-41` opened; `MAG-20` third rung killed; `ANS-2` not
  commissioned.
- **Agent value:** 0 demotions-that-stuck / 11 audits (two tier re-labels,
  both the scoping review's estimate), pathologist 5 confirmed / 1
  overruled, navigator 0 citation errors, example-runner 4/4 footered,
  record-reconciler 1/1.
- **Deferred to 09-06:** the §7 archive rotation and the B1+ literature
  anchor.

## Waiting on you

1. 🟢 **`ANS-4` is ready to replicate — both halves exist.**
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/`. Run the
   **low-order pair only** (Zero Order for adjudication, default First
   Order for sensitivity; Mixed Order not) — `ANS-1` showed the
   higher-order flag is silently ignored with a winding excitation. Please
   confirm the unknowns-per-tet figure AED prints. Ranks above `ANS-3`.
   Results stay in the gitignored `aed_results/`; `OPS-32` (§9 item 2)
   gives this example the private-mode writer **before** numbers arrive —
   if you run AED before that lands, keep the JSON out of the tree until
   it has.
2. 🟢 **`ANS-3` AED run** — still yours, behind `ANS-4`. Same low-order
   rule, same private-results handling.
3. 🟡 FYI, no action — **your `ANS-1` private comparison file trips the
   example census.** The docrefs checker scans every `*.md` under
   `examples/`, gitignored or not, so `COMPARISON_private.md` is read as a
   guide with a dead reference and the census exits 1 on `main`. A
   checker-scope defect, filed in known-issues and folded into `OPS-32`;
   nothing for you to move or delete.
4. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
5. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
6. 🟡 FYI, watch item — **the CLI login expired overnight 09-01/02 and
   cost three sessions.** All four slots since ran normally; if the expiry
   is periodic, the next one lands on a weekend of unattended slots. Worth
   knowing the refresh interval.
7. FYI, no action — **`MAT-8`'s finite-wire term has the opposite sign to
   what the slot's journal said.** The 5 mm wire *raises* the closed form
   by 0.115%, and the slab-refined FEM (step 8) already sits 0.28% *below*
   the filament value, so the corrected residual is ≈ −0.40%, not ≈ 0.17%.
   §2.1 and `MAT-6` step 11 now say so; nothing changes for `ANS-1`.
8. FYI, no action — **`GEO-25` (the 30 cm coil cost probe) stays off the
   queue** (third rung predicted at 30 min of gmsh). Local `main` remains
   well ahead of origin (push is manual).

## Honest current state (digest of §2 — the coil-loading row moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅, production order: degree 1 coil-fed, degree 2 imposed-field). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private). **New (`MAT-8` ✅):** the filament-vs-5 mm-wire modelling term is **+0.115% on ΔR** — the floor under any sub-0.5% claim on this fixture, and it *widens* the refined FEM's gap to ≈ −0.40%. Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` (Waiting-on-you 1) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated | `phantom_resolution` knob landed (3f₀): `None` is an exact no-op, 0.0075 grows the phantom 5.11× for +4 414 cells. First solve on the 16-leg layout is `PORT-13` step 1 (§9 item 5) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅; these gates project **`B`** on the whole mesh (0.38%) and are untouched by the SAR findings. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🔴 **measured, not gateable; mechanism narrowed to `h` or the construction** | primal point SAR misses the five identities at 25–41%; restricted CG1 `E` reads 6.1–9.5%; **restricted CG2 `E` — a strictly better fit — reads 11.3–19.3%** (3e′). Projector and degree excluded. Next: phantom `h` (3f, item 1) and integral-form identities off the primal field (3g, item 4). Five deliberate reds on `main`, band unmoved. **No SAR claim exists** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never gated on a coil |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 8 deliberate/known** | example-artifact census `exit=1` on `main` — a checker-scope defect (scans a gitignored private file), not a corpus one; fix in `OPS-32`. API sweep `violations=0` on all four roots |

## Recent activity (2026-09-02 03:00 → 10:30)

- **04:30:** `OPS-31` — `ports:3` narrative re-recorded to the 0.11 ladder
  7.7431 → 1.0986 → 1.9222% by the `record-reconciler`; bands untouched.
  235 s. ✅ (re-tiered to heavy by this review; the label was the scoping
  estimate).
- **06:00:** `WF-6` step 3e′ — CG2-restricted `E`: residual 14.47% vs
  CG1's 18.72%, `x² ê_x` reproduced to 1.5e-12 where CG1 left 6.7e-2, all
  anchors green — and the five identities **worse** (19.35 / 17.21 / 16.07
  / 14.41 / 11.32%). Verdict (γ) with its stated cause excluded. 125 s.
  🟡.
- **07:30:** `MAT-8` — finite-wire Dodd–Deeds: +0.115237% on ΔR, +0.144814%
  on ΔX at the `MAT-6` fixture; filament limit to 2.2e-10 with an exact r²
  rate, PEC limit to 5.8e-8, lift-off limit `r²/(2a²)` to 0.38%. 4 s. ✅.
- **09:00:** `WF-6` step 3f₀ — `phantom_resolution` on
  `birdcage_port_domain`; `None` and 0.015 both reproduce 116 085 / 537 at
  0.000e+00; 0.0075 gives 120 499 / 2 746; CAD identities hold. 86 s. ✅.
- **10:30 review:** three audits (PASS, PASS, DEMOTE-on-tier → re-tiered);
  3e′'s (γ) adjudicated — 3f runs anyway, 3g scoped; `MAT-8`'s sign
  corrected in §2.1 and `MAT-6` step 11; census-scope defect filed and
  folded into `OPS-32`; `EX-42` opened. Queue rebuilt: six items.

## Automation health

- **4 of 4 scheduled slots fired, all green on the first run**, none
  parked, tree clean at every preflight. Container Up 6 days.
- **Foreground-executor rule: 9 for 9** since written. No docker-socket
  denial this interval (**3 of 26** slots overall).
- Two tier labels in two reviews were the scoping review's estimate, not
  the slot's (`OPS-30` 37 s under smoke, `OPS-31` 235 s under standard);
  both re-tiered, neither demoted. Queue items now state the tier the
  ceiling implies.

## On deck (§9 — six items, all independent; 5 the first heavy item, 6 the spare)

1. **`WF-6` step 3f** — the finer-phantom rung at `phantom_resolution =
   0.0075` (2 746 phantom cells, measured), five identities printed,
   verdict (a)/(b)/(c) pre-registered — a *rise* is (c), not a defect
   *(implementer; ≈ 150–200 s)*
2. **`OPS-32`** — the docrefs checker skips gitignored `*_private.md`, then
   private-mode comparison writers for `ANS-3`/`ANS-4` with reproduction
   controls at 1e-6 *(implementer; two runner windows ≈ 8–9 min)*
3. **`EX-41`** — `mesh:6` and `mesh:7` get a footered run *(`example-runner`
   foreground; ≈ 160 s)*
4. **`WF-6` step 3g** — the C4 SAR identities as *integrals* of the primal
   `σ|E|²` over a smooth azimuthal partition of unity; partition sum is
   an exact anchor, no estimator *(implementer; ≈ 100–125 s)*
5. **`PORT-13` step 1** — first single-port solve on the 32-ring-port
   layout, power accounting to 1e-2 *(implementer; heavy, `-n 8`, 590 s
   stop rule)*
6. **`EX-42`** — `mat:1` prints the finite-wire-corrected Dodd–Deeds
   beside the filament form and the FEM ΔR *(`example-runner`; ≈ 60 s;
   spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
