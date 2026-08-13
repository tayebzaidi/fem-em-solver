# FEM-EM Solver — status

**Updated:** 2026-08-13, 10:30 review (run interactively — the scheduled
slot died on an API 529; see Automation health). Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. **One click: does ParaView open a DG1 `.bp`?** (unchanged since the
   2026-08-12 18:00 review). `POST-4` step 5 measured the DG1/VTX export
   route bit-faithful (round-trip exactly 0.0) where the current P1 path is
   20–52% off pointwise; cost is 10.5× disk, zero wall clock. Adoption is
   blocked only on you opening a `.bp` in ParaView (ADIOS2/VTX reader) and
   confirming it renders — each field arrives as `<name>_real` /
   `<name>_imag`. `scripts/probes/post4_step5_probe.py` regenerates the
   files.
2. **ANS-1 Ansys replication** — the FEM half is complete
   (`examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/`, `SPEC.md`
   box 1 checked); the AED run is yours. Our ΔX is genuinely unconverged,
   so the AED number is informative, not a formality.
3. Housekeeping: local `main` is **~45 commits ahead** of `origin/main`
   (`b6e994f`, 2026-08-10) — push when convenient; every "in CI" claim is
   a local reproduction until then.

## Honest current state (digest of §2 — two rows moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; the < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; **Larmor-regime sphere now gated: 3.64% (64 MHz) / 1.83% (128 MHz) + ½∫σ\|E\|² to 3.63% — TH-10 closed ✅ this review** |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.88% on the combined fixture (MAT-6); **coil-at-Larmor is the remaining extrapolation → TH-11 commissioned** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4) + the Larmor power integral (TH-10); never on a coil |
| S-parameters | 🟡 test path real, package path heuristic | port-pair gate green at the unmoved 10% (3b-xviii, systematics named); **PORT-1 step 4 (package path) is queue item 1** |

## Recent activity (03:00 → 10:30 interval)

Five slots, five landings; all audited §4-compliant (one subagent auditor
per landing), no demotions:

- **TH-10 closed ✅** — the interior field gated against the Mie series at
  both Larmor frequencies and the SAR-relevant power integral at 64 MHz;
  the quasi-static route misses by 58%, so the gate measures genuinely
  full-wave physics. §2.1's long-standing extrapolation caveat narrows to
  coil-at-Larmor only.
- **EX-18** — first ports example (`ports:` runner group); the correction
  ladder now has a single source in `ports/systematics.py`, asserted
  bit-identical to the gate module.
- **MAG-13 rung 3** — the < 5% wire target reached by brute force (3.74%,
  1.52 M cells, 423 s); rung 2's near-wire error-map pattern refuted as
  mesh-realization noise and the §2 bullet corrected.
- New chunks from the findings: **TH-11** (coil loading across the
  eddy→displacement transition), **GEO-14** (the shared ~3% geometry-floor
  discriminator), **EX-19** (Larmor sphere example, §5.4 ramp), **OPS-16**
  (retry-on-529 in the launchers, spare).

## Automation health

- **The 10:30 review slot died on an API 529** (empty log, exit 1; an
  interactive relaunch attempt hit the same). This review was then run
  interactively at the operator's direction, ~6.5 h late — the drained
  queue was restocked before any implementer slot idled, so the outage
  cost zero slots. `OPS-16` (one guarded retry in the launchers) is queued
  to absorb this class in future.
- Grid otherwise clean: nine consecutive landing slots across the last two
  intervals; tree clean; no `attempt/*` or `recovered/*` branches — the
  three PORT-1 lineage branches were landed and deleted 2026-08-13.
- Standing weekly-review items (2026-08-16): the two-systematics
  composition question (3b-xviii), MAG-13 CG1 gate adoption, MAT-6
  step 10's ≥ 5.1× solve anomaly (memory-headroom lead), POST-4 export
  adoption (pending your ParaView check), and the birdcage-ports/B1+
  hold.

## On deck (§9, rebuilt this review; items mutually independent)

1. **PORT-1 step 4** — the package path reads the solved field: retire the
   `excitation.py` heuristic on the two-torus fixture. The §10 subgoal-2
   critical path; §2's "every packaged S-parameter is a heuristic"
   sentence falls only when this lands.
2. **EX-19** — Larmor lossy-sphere example, both frequencies, gate digits
   reproduced through the example path.
3. **GEO-14 step 1** — one-command discriminator: is the ~3% residual a
   geometry floor or resolution?
4. **TH-11 step 1** — coil loading at 64 MHz, cost/feasibility probe,
   measurement only, stop rule 300 s/solve.
5. *(spare)* **OPS-16** — retry-on-529 in the automation launchers.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
