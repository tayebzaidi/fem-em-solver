# FEM-EM Solver — status

**Updated:** 2026-08-13, 03:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. **One click: does ParaView open a DG1 `.bp`?** (unchanged since the
   2026-08-12 18:00 review). `POST-4` step 5 measured the DG1/VTX export
   route **bit-faithful** (round-trip exactly 0.0 against a 1e-14 bound)
   where the current P1 path is 20–52% off pointwise; cost is 10.5× disk,
   zero wall clock. Adoption is blocked only on you opening a `.bp` in
   ParaView (ADIOS2/VTX reader) and confirming it renders — in the complex
   build each field arrives as two real arrays, `<name>_real` and
   `<name>_imag`. `scripts/probes/post4_step5_probe.py` regenerates the
   files; until you confirm, no example switches its export.
2. **The first Ansys benchmark is ready to replicate in AED** (unchanged
   since 2026-08-09). `ANS-1` at
   `examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/` pins itself to
   the `MAT-6` gate (ΔR = +0.32770 Ω, **1.5834%** from Dodd–Deeds). Build
   the case in AED per `SPEC.md`, fill the blank AED columns in
   `COMPARISON.md`; the weekly review then adjudicates. ΔX is reported,
   never gated; disable coil eddy effects in AED per `SPEC.md` §Excitation.
3. **What did the GitHub runner say?** `origin/main` is still at the
   2026-08-10 18:00 review commit (`b6e994f`); local `main` is **37
   ahead** once this review's commit lands. Sessions have no network
   access — anything you can paste (pass/fail, log excerpt) is new
   information, and a push whenever convenient.

## Honest current state (digest of §2)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic in the package | first real gated S from a solved Z landed this interval — two-torus fixture, in a test (PORT-1 3b-xviii); the sweep path still calls the heuristic |

New under the headlines: the port lineage is **on `main` and gated** —
matched-topology Faraday closure at 11× margin (3b-xvii) and the
port-pair mutual inside the unmoved 10% band with both systematics
named (3b-xviii; raw −10.57% is on the record as a miss, corrected
−6.04%). And the Larmor gap now has a number: the first Larmor-regime
anchor (`TH-10`, lossy-sphere Mie series) shows the saline sphere's
full-wave interior field departs from quasi-static by **102% at 64 MHz
and 155% at 128 MHz** — the quasi-static answer at Larmor is not a
correction away from truth, it is the wrong answer. Gating the actual
solver against that anchor is now queue item 1.

## Recent activity (since the 18:00 review)

**Four slots: four items landed; all four ✅ flips audited compliant.**

- **PORT-1 step 3b-xvii** (19:30, ✅): the lineage branch landed on
  `main` by path (a merge would have reverted 100+ main-side commits);
  the consistency gate re-aimed at matched topology reads **−2.7e-03 /
  −2.6e-03 vs the unmoved 3% bound** (11× margin). Neither tolerance
  moved.
- **PORT-1 step 3b-xviii** (21:00, ✅): the port-pair gate — raw
  0.894283 (−10.57%, a recorded miss) → two named systematics →
  **0.939581 (−6.04%)** inside the unmoved 10%; blind control −98.26%
  asserted to fail; first S-matrix from this Z: symmetry 2.5e-05,
  ‖S‖₂ = 0.86 (passive). Caveat for the weekly review: the two
  corrections' independent composition is untested.
- **MAG-13 step 2c** (22:30, ✅): third rung, 408 k cells — three-point
  CG1 rate **p = 2.003**, but pairwise 2.204/1.803, so the honest claim
  is "second order ±10%", not a converged 2.00. Gate adoption stays the
  weekly review's call.
- **TH-10 step 1** (00:00, ✅): the Larmor anchor exists —
  `LossySphereSeries`, 6/6 gates including quasi-static tie to TH-8 at
  rate 1.97 and a conjugated-convention control that misses by 2.1e+04×.
  Zero-solve; the solver has not yet been gated against it.

Audits: all four flips **compliant** (quantitative gates drive every
exit code; TH-10's failing first run was re-aimed at TH-8's own gated
quantity with *more* gates, not looser ones). Housekeeping: the three
`attempt/PORT-1-*` branches are deleted — content verified on `main`
first; the two 3b-xv logs lived only on their branch and were copied
over with their result rows.

## Automation health

- **Slot yield: 4/4 landing, second interval in a row.** Tree clean at
  review time; no `recovered/*`; attempt-branch list now empty.
- Queue depth **5** after refresh: TH-10's solve gates (items 1, 3, 5 —
  the last two serial on item 1, skip rules stated), the first ports
  example `EX-18` (item 2, §5.4 ramp), MAG-13 brute-force rung (item 4).
- `PORT-1`'s next move (birdcage ports / B1+) is deliberately held for
  the weekly review: the correction-ladder composition question comes
  first.

## On deck (§9, refreshed this review)

1. **TH-10 step 2** (standard) — first Larmor-regime full-wave solve
   gate: sphere-in-box at 64 MHz vs the Mie series, < 5% interior relL2;
   quasi-static misses by 102% on the same fixture (the negative
   control).
2. **EX-18** (standard) — first ports example: two-torus pair → Z → S,
   reproducing the 3b-xviii gated digits, XDMF for ParaView.
3. **TH-10 step 3** (standard, serial on 1) — the same gate at 128 MHz,
   where quasi-static misses by 155%.
4. **MAG-13 rung 3** (heavy) — the < 5% wire by brute force; exit 124 is
   itself the measurement.
5. **TH-10 step 4** (standard, serial on 1, spare) — ½∫σ|E|² vs the
   series: the SAR-relevant volume integral.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy is refreshed by interactive sessions only and may
lag this file; `docs/status/dashboard.md` on `main` is always current.*
