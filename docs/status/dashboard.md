# FEM-EM Solver — status

**Updated:** 2026-08-12, 18:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. **New, one click: does ParaView open a DG1 `.bp`?** `POST-4` step 5
   measured the DG1/VTX export route **bit-faithful** (round-trip exactly
   0.0 against a 1e-14 bound) where the current P1 path is 20–52% off
   pointwise; cost is 10.5× disk, zero wall clock. The review's call is to
   adopt it — blocked only on you opening a `.bp` in ParaView (ADIOS2/VTX
   reader) and confirming it renders. Heads-up on what you'll see: in the
   complex build each field arrives as **two real arrays**, `<name>_real`
   and `<name>_imag`, not one complex field. Any probe run of
   `scripts/probes/post4_step5_probe.py` regenerates the files; until you
   confirm, no example switches its export.
2. **The first Ansys benchmark is ready to replicate in AED** (unchanged
   since 2026-08-09 18:00). `ANS-1` at
   `examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/` pins itself to
   the `MAT-6` gate (ΔR = +0.32770 Ω, **1.5834%** from Dodd–Deeds).
   `SPEC.md` box 1 is checked; the next two are yours: build the case in
   AED per `SPEC.md`, fill the blank AED columns in `COMPARISON.md` — the
   weekly review then adjudicates. Reminders: ΔX is reported, never gated;
   our Re Z(σ = 0) is exactly 0.0 by structure — disable coil eddy effects
   in AED per `SPEC.md` §Excitation before comparing.
3. **What did the GitHub runner say?** `origin/main` is still at the
   2026-08-10 18:00 review commit (`b6e994f`); a runner execution of
   `validation-complex` should exist by now. Sessions have no network
   access and cannot see the result; anything you can paste (pass/fail,
   log excerpt) is new information. Local `main` is **33 ahead** once this
   review's commit lands — a follow-up push whenever convenient.
4. FYI, no action needed: the `lint` CI job stays red-by-adjudication, and
   your Jin-grounded PORT-1 adjudication has now fully executed — see
   below.

## Honest current state (digest of §2 — headline gates unmoved)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

New under the headlines: the two-torus port estimator's ~3% offset is now
**fully diagnosed** — feed discretisation exonerated by measurement
(Δ = +0.05 pp under 1.57× feed refinement vs a 0.5 pp band), the offset is
**gap physics**, and the PEC-box term is a stated number
(+1.69 pp, effective-range exponent 1.657). The port-pair gate is queued.
Also: continuous (CG1) B recovery reaches the < 5% wire target at the
existing `MAG-13` mesh for 1% of the solve time, and the faithful DG1/VTX
export is measured bit-exact (adoption on your ParaView check, item 1).

## Recent activity (since the 10:30 review)

**Four slots: four items landed; all three ✅ flips audited compliant.
This interval cleared the PORT-1 diagnosis lineage.**

- **PORT-1 step 3b-xvi, third attempt** (12:00, ✅): the review-re-pointed
  locality control passes (−0.17% vs < 5%), the solve was bought, and the
  refined estimator moved **one tenth of the band** (Δ = +0.0508 pp) —
  feed discretisation exonerated; the −3.02e-02 offset is gap physics
  (Jin §10.4.2.1), the label now earned by measurement. The twice-failed
  item closed on its third attempt.
- **MAG-13 step 2b** (13:30, ✅): CG1-projected `curl A` reads **1.9557%**
  against DG1's 4.7235% and the < 5.00% mark, for 2.71 s on a 271 s
  solve; the sampling staircase breaks 8/8 and the error floor left is
  band-flat ≈ 2% at an observed second-order rate. Gate adoption goes to
  the weekly review once a third rung confirms the rate (queued).
- **POST-4 step 5** (15:00, ✅): DG1/VTX export round-trips **exactly**
  (0.0 vs a 1e-14 bound) where P1 reads 51/52/20% in the same run; the
  price is 10.49× disk and the writer is *faster*. The adoption call is
  made pending your ParaView check (Waiting-on-you 1).
- **PORT-1 decision-(4) padding fit** (16:30): the box term is a number —
  **D∞ = +1.69 pp at p = 1.657** — but it is an effective-range
  extrapolation (pinning p = 3 flips it to −1.43 pp), so the pair gate
  quotes it with its exponent, never as a converged value. No fourth
  padding rung commissioned: the 10% gate dwarfs the 3.1 pp model spread.

Audits: all three ✅ flips **compliant** (quantitative gates drive every
exit code; negative controls genuinely fired; failed runs committed, not
hidden). Housekeeping: 3b-xvi's two logs lived only on the attempt
branch — copied to `main` with this review.

## Automation health

- **Slot yield: 4/4 landing** — the first fully-landing interval since
  the harness repairs; one item was the twice-failed 3b-xvi closing on
  the recipe the 10:30 review rescoped.
- Tree clean at review time; no `recovered/*` branches. Three
  `attempt/PORT-1-*` branches parked by design (adjudication decision 6);
  they land with §9 item 1, the lineage's first ✅ gate.
- Queue depth **5** after refresh; one declared serial pair (items 1 → 2),
  the rest independent. `TH-10` opened — the first Larmor-regime chunk,
  per §10 subgoal 3's standing instruction.

## On deck (§9, refreshed this review)

1. **PORT-1 decision-(3) re-pointing** (standard) — land the lineage
   branch and re-aim the consistency gate at matched topology; the only
   tolerance-licensed commit, expected to move nothing.
2. **PORT-1 port-pair gate** (standard, serial on 1) — two-torus
   gap-voltage Z₁₂ vs ωM₁₂ at 10%, both systematics stated by name.
3. **MAG-13 step 2c** (heavy) — third rung for the CG1 recovery rate;
   the weekly review's adoption call waits on this number.
4. **TH-10 step 1** (smoke, zero-solve) — author the Larmor anchor:
   lossy-sphere series with quasi-static-limit identity against TH-8.
5. **MAG-13 rung 3** (heavy, spare) — the < 5% wire by brute force;
   runs only if slots outlast items 1–4.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy is refreshed by interactive sessions only and may
lag this file; `docs/status/dashboard.md` on `main` is always current.*
