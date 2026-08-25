# FEM-EM Solver — status

**Updated:** 2026-08-25 10:30, **daily review (scheduled, ran normally)**.
Headline: **`PORT-9` is closed — the loaded 4-leg birdcage has a fully
gated 4×4 S-matrix at 10 MHz**, and the §10 Phase-4 box "loaded birdcage +
phantom runs end to end" ticks at 10 MHz on its own pre-stated condition
(the 64/128 MHz claim is `PORT-11`, unrun). The 16-leg cost rung is
measured (307 296 cells / 74 s — comfortably affordable). The interval
also surfaced the sharpest finding since the 0.11 merge: a
**magnetostatics convergence gate has been red on `main` unobserved since
the merge**, found by the examples layer — which is exactly the failure
class your migration-sweep directive (`OPS-26`, now queued) exists to
enumerate. Source of truth is `PROJECT_PLAN.md`; this page is a read-only
digest for the human operator.

## Waiting on you

1. ✅→📋 **Your two directives from this morning's interactive session are
   both filed and moving**: `OPS-26` (0.11 migration completeness sweep)
   is queued — step 1 runs in this interval's slots; the fixture-scale
   directive (F-small / F-human) is placed in §10 Phase 6 for the Sunday
   2026-08-30 weekly review to dispose of, cost probe first. Nothing
   needed from you unless you want to pre-empt the weekly review's
   scoping.
2. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
3. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
4. **ANS-1 Ansys replication** — still yours; ANS-3 (item 2) is the
   second case in the same queue.
5. FYI: local `main` is well ahead of origin (push is manual).

## Honest current state (digest of §2 — two changes this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ⚠️ validated, but **one rate gate red on `main`** | closed forms green (Helmholtz 0.04%, `E_Ω` ladder rate 1.6854 on 0.11); `test_h_refinement_straight_wire` fits **1.9038 vs [0.7, 1.5]** — the finest rung's sampled error collapsed on the 0.11 image; disposition chunk `MAG-19` queued with a pre-stated two-branch decision rule, no band moves either way |
| Time-harmonic curl-curl | ✅ validated, example family fully re-gated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; 128 GiB re-pricing stays a weekly-review call |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| S-parameters | ✅ **birdcage gated at 10 MHz — `PORT-9` closed 08-25** | power-wave 4×4 on the loaded gapped birdcage: reciprocity 2.259e-14 vs 1e-3 (2.466e+11× from the pre-fix broken route), σ_max 0.999992805, class spreads 0.055 / 0.035 / 0.021% vs the tightened 0.5%, and the displaced-leg negative control breaks all three classes by two orders. **No Larmor, resonance, or tuning claim** — that is `PORT-11`, next in the queue line |
| Test-suite trust | ⚠️ under systematic re-audit | two gates have now been found silently broken post-0.11 by the examples layer, not by the upgrade's re-gate; your `OPS-26` sweep (queued) re-derives the "observed in a completed run" census on 0.11 |

## Recent activity (2026-08-25 03:00 → 10:30)

- **04:30 + 06:00:** `PORT-9` leg (d1′) landed in two slots — mesh knob
  first (every `GEO-18` identity survives the 22.5° rotation), then the
  displaced 4×4 through the power-wave assembly. **Chunk ✅**; the
  (iii′) 5% → 0.5% tightening committed with all three consumer modules
  green; §2.2's "no coil or birdcage has ports" head retired; attempt
  branch deleted. Audited §4-COMPLIANT this review: every log footer and
  anchor digit verified, the only band change is the licensed tightening.
- **07:30:** `GEO-19` step C measured the 16-leg rung — 307 296 cells /
  74.18 s (2.65× / 3.24× over 4 legs), four of five gates green, parked
  on the terminal-equality gate: the 1e-5 band was measured at C4 where
  ports are exact coordinate permutations; at 16 legs the spread is
  8.4e-04 in three azimuth classes ≤ 2e-7 tight inside each. **Ruled
  this review: construction symmetry** — per-class reading, tighter
  where it overlaps the old gate, nothing widened; landing queued item 1.
- **09:00:** `EX-30` leg (root) — six of eight examples green (SAR
  closed-form identities at machine precision, Dodd–Deeds to 4e-04),
  census 47 → 26 exact and derived, and two reds: the `MAG-13` rate gate
  red on `main` (above) and `mag:1`'s mesh failing at its own coarse
  resolution — localised in a 29 s probe to a geometry-independent
  resolution floor on the 0.11 image. **Ruled this review:** the example
  moves to the nearest working rung (0.008); the gate red is `MAG-19`'s.
- **10:20/10:26:** your interactive session landed the `OPS-26`
  commission and the fixture-scale directive; both ingested above.

## Automation health

- Four slots scheduled, four ran, all four productive: one chunk close,
  one two-slot landing, two disciplined parks that asked for exactly the
  rulings this review made. No exit-124 waste except one known teardown
  trap, no wedge, no `recovered/*`, tree clean at every handoff. One
  paid trap worth naming: a rank-0 `KeyError` in a report block turned
  97 s of green pytest into a 561 s hang — the parked module now carries
  a broadcast guard.
- Branches: `attempt/GEO-19-stepC-20260825T125000Z` parked (item 1's
  payload, ruling applied at landing); the superseded 08-23 `GEO-19`
  branch deleted by this review after diff verification.
- The queue holds **six items — 1–5 independent, item 6 explicitly
  serial on item 2**. Newly commissioned, not yet queued: `EX-32` (first
  birdcage-port example) and `OPS-26` step 2 (waits on step 1's list).
  `PORT-11` step 1 is unblocked and first in line at the next review.

## On deck (§9 — six items this review)

1. **`GEO-19` step C** — land the 16-leg module under the
   construction-symmetry ruling; closes `GEO-19`, unblocks `GEO-20`
   step 2 (standard, independent)
2. **`MAG-19` step 1** — discriminate the red rate gate: anomalous rung
   vs wrong instrument, both norms on the same four-rung ladder
   (standard, independent)
3. **`OPS-26` step 1** — the static 0.11 migration sweep, introspected
   signatures, must-fail negative control (smoke, independent,
   operator-directed)
4. **`EX-30` leg (mesh)** — meshing examples, licensed re-records
   (standard, independent)
5. **`EX-30` leg (ports)** — ports + `ans` examples, licensed re-records
   (standard, independent; spare)
6. **`EX-30` leg (root) completion** — executes this review's three
   rulings; **serial on item 2**, skips with a journal entry if item 2
   did not land

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
