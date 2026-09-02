# FEM-EM Solver — status

**Updated:** 2026-09-02 18:00 daily review. Headline: **four of four slots
landed; the coil-driven SAR puzzle broke open twice in one afternoon.**
Halving the phantom's cell size brings the five pointwise SAR identities
inside the 5% band (8–9% → 2.5–3.5%, `WF-6` step 3f), and — on the
*coarse* mesh, with no estimator at all — reading the same identities as
**integrals** of the primal `σ|E|²` over four azimuthal quadrants lands
all twelve C4 pairs at ≤ 1.52% (step 3g). The construction, not the
mesh, was the binding mechanism. **This review ruled the integral
construction the gate**: step 3h (queued first) registers the first
coil-driven SAR gate in the repo and retires the five pointwise asserts
to records. **No gate is registered yet and no band moved.** `OPS-32`
(private-mode AED writers + census fix) and `EX-41` are ✅ and audited.
Source of truth is `PROJECT_PLAN.md`; this page is a read-only digest for
the human operator.

## Weekly review digest (2026-09-02, unchanged from the weekly's own copy)

- **Pace, 08-30 → 09-02 (2.68 d):** 26 §4-✅ items (10 chunks + 16 steps),
  9.7/day, 62% physics; 30 of 32 implementer slots fired, every loss
  launcher-side (login, CLI pin), none on limits. Full ledger in §10.
- **Phase 5 exit re-assessed to ≈ 09-05…09 on F-small** — watch condition:
  `WF-6` step 3f printed by 09-06. **Met 09-02** (clause (a)).
- **Rulings landed in §7:** `GEO-25` and `PORT-13` re-scoped with anchors
  and prices; `TH-12` closed ✅; `ANS-1` **adjudicated AGREE** (numbers
  private); `MAT-6` step 11 and `MAT-8` scoped; `WF-6` step 3f scoped;
  `OPS-32`, `EX-41` opened; `MAG-20` third rung killed; `ANS-2` not
  commissioned.
- **Deferred to 09-06:** the §7 archive rotation and the B1+ literature
  anchor.

## Waiting on you

1. 🟢 **`ANS-4` is ready to replicate — both halves exist, and the
   private-mode writer is now in place** (`OPS-32` ✅ 13:30): drop the AED
   results JSON into the gitignored `aed_results/`, re-run the example,
   and the filled comparison goes only to the untracked
   `COMPARISON_private.md`. `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/`.
   Run the **low-order pair only** (Zero Order for adjudication, default
   First Order for sensitivity; Mixed Order not) — `ANS-1` showed the
   higher-order flag is silently ignored with a winding excitation. Please
   confirm the unknowns-per-tet figure AED prints. Ranks above `ANS-3`.
2. 🟢 **`ANS-3` AED run** — still yours, behind `ANS-4`. Same low-order
   rule, same private-results handling (writer in place).
3. ✅ Resolved, no action — the census no longer trips on your `ANS-1`
   private comparison file: the checker skips `*_private.md` since
   `OPS-32`, and `main` reads `dead=0`.
4. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
5. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
6. 🟡 FYI, watch item — **the CLI login expired overnight 09-01/02 and
   cost three sessions.** All eight slots since ran normally; if the expiry
   is periodic, the next one lands on a weekend of unattended slots. Worth
   knowing the refresh interval.
7. FYI, no action — **`GEO-25` (the 30 cm coil cost probe) stays off the
   queue** (third rung predicted at 30 min of gmsh). Local `main` remains
   well ahead of origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval; the SAR row's *prospect* moved)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% (`MAT-6`), bracketed by Maxwell 3D (`ANS-1` AGREE, numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` (Waiting-on-you 1) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated | `mesh:6` / `mesh:7` re-footered on the 0.11 image, digit-identical to 08-25 (`EX-41` ✅). First solve on the 16-leg layout is `PORT-13` step 1 (§9 item 3) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated | `WF-6` steps 1–2b ✅. **New (3f):** the C4 identities are *not* mesh-converged — halving the phantom's `h` takes them 2.19% → 0.62%, an improvement outside a 0.5 pp no-move anchor; three deliberate reds until step 3f′ (item 2) re-reads the anchor one-sided with the ring-set control. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🔴 **measured, not yet gated — mechanism found (the construction), gate ruled and queued** | pointwise primal 25–41%; restricted CG1 6.1–9.5% coarse → **2.5–3.5% on the 0.0075 phantom** (3f, clause (a)); **integral C4 pairs of the primal `σ\|E\|²` ≤ 1.52% on the coarse mesh** (3g, clause (a), partition identity exact). Step 3h (item 1) registers the integral gate. Until it lands: five deliberate reds, band unmoved, **no SAR claim exists** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never gated on a coil |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 11 deliberate/known** (8 + the three 3f `\|B₁⁺\|` no-move asserts; expected 3 after items 1–2) | example-artifact census `dead=0 … exit=2` on `main` (staleness only, `OPS-32` fixed the checker scope). API sweep `violations=0` on all four roots |

## Recent activity (2026-09-02 10:30 → 18:00)

- **12:00:** `WF-6` step 3f — finer phantom (120 499 cells, 2 746 tag-3):
  five SAR identities 3.3600 / 3.4442 / 3.4525 / 3.0332 / 2.5465%, all
  inside 5% (clause (a)); `|B₁⁺|` identities improved 1.3–1.6 pp past a
  0.5 pp no-move anchor → 3 deliberate reds + known-issues. 175 s. 🟡.
- **13:30:** `OPS-32` — private-mode `COMPARISON_private.md` writers for
  `ANS-3`/`ANS-4`, tracked tables blank by construction; docrefs checker
  skips `*_private.md`, census `dead=0 exit=2`. The 1e-6 control half is
  a fixture finding (records vs image, not scatter) → `OPS-33` (item 4).
  171 + 172 + 1 s. ✅ (audited PASS; anchor-wording flag ratified).
- **15:00:** `EX-41` — `mesh:6` / `mesh:7` footered on the 0.11 image,
  every cell count identical to the 08-25 reference. 54 + 85 s. ✅
  (audited PASS).
- **16:30:** `WF-6` step 3g — C4 SAR identities as cell integrals of the
  primal `E` on the coarse mesh: twelve pairs, worst 1.5200%, partition
  identity exact, mis-paired control 89–159× larger. 106 s, `20 passed`.
  🟡.
- **18:00 review:** two audits (PASS, PASS); the SAR-construction ruling
  (integral gate → step 3h); the `|B₁⁺|` reds → step 3f′ (ring-set
  control, one-sided anchor); `OPS-33` opened; queue rebuilt: five items.

## Automation health

- **4 of 4 scheduled slots fired, all complete on the first window**,
  none parked, tree clean at every preflight. Container Up 7 days.
- **Foreground-executor rule: 13 for 13** since written. No docker-socket
  denial this interval (**3 of 28** slots overall).
- Every measured window sat inside its declared tier this interval; no
  re-tiering.
- Standing rule from `OPS-32`'s flag: an anchor on a generated artifact
  never says "unchanged" — it names what must be absent from the diff.

## On deck (§9 — five items, all independent; 3 the first heavy item, 5 the spare)

1. **`WF-6` step 3h** — register the first coil-driven SAR gate: the
   twelve integral C4 pairs asserted at the unmoved 5% band; the five
   pointwise asserts become record reproductions *(implementer; ≈ 230 s)*
2. **`WF-6` step 3f′** — ring-set control on the 0.0075 phantom for both
   the `|B₁⁺|` and SAR columns (±2 pp), one-sided `|B₁⁺|` anchor, fine
   records beside coarse, integral pairs printed on the fine mesh
   *(implementer; ≈ 190–210 s)*
3. **`PORT-13` step 1** — first single-port solve on the 32-ring-port
   layout, power accounting to 1e-2 *(implementer; heavy, `-n 8`, 590 s
   stop rule)*
4. **`OPS-33`** — re-base `ans:3`'s four records to the 0.11 image, then a
   1e-6 reproduction control with the symmetry residual on an absolute
   band *(implementer; two runner windows ≈ 6 min)*
5. **`EX-42`** — `mat:1` prints the finite-wire-corrected Dodd–Deeds
   beside the filament form and the FEM ΔR *(`example-runner`; ≈ 60 s;
   spare)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
