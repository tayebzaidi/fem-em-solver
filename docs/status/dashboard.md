# FEM-EM Solver — status

**Updated:** 2026-08-26 03:00, **daily review (scheduled, ran normally)**.
Headline: **a perfect interval — four slots, four landings, zero parked
branches** — and the mission front moved: the **first Larmor-frequency
solve on the loaded birdcage exists** (`PORT-11` step 1: 64 MHz resolves
on the gated mesh, phantom resolution 5.9 cells/skin-depth vs the 2.0
floor, and the frequency costs *nothing* — MUMPS is mesh-bound, so the
full 4×4 S-matrix at 64 MHz is a ~60 s standard-tier run, now queued).
The straight-wire rate-gate red is disposed (`MAG-19` ✅, audited
compliant), both `EX-30` mesh-red rulings landed exactly as ruled, and
the one remaining 0.11 gate red (`GEO-15`'s) came back from its
measurement needing a ruling — made this review: a coarse-graded control
at `h_c = 4.8e-3`, landing queued first. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the
   second case in the same queue.
4. FYI: local `main` is well ahead of origin (push is manual). The
   fixture-scale directive still waits on the Sunday 08-30 weekly review
   as addressed. Nothing needs your input on either.

## Honest current state (digest of §2 — two changes this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ **rate-gate red disposed** (`MAG-19` ✅ 08-25, audited compliant) | closed forms green; rate duty now lives on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7 on 0.11), the unstable sampled two-sided band retired with its measured basis, nothing widened; one sibling sampled gate (green) gets its own measurement (`MAG-20`, commissioned) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10 MHz; **64 MHz now solved and priced** (`PORT-11` step 1, 08-25) | 10 MHz column reproduces the gated record to 2.6e-10 with frequency the only knob; cells/δ 5.92 ≥ 2.0 floor; **no gate claim at 64 MHz yet** — the 4×4 under the unmoved reciprocity/passivity/class gates is queue item 2 |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ⚠️ one known gate red on `main`, ruled | the `GEO-15` graded-conductor gate (baseline unmeshable on 0.11) — measured 08-26, ruled this review, landing is queue item 1; `OPS-26` step 2 (execution census) still first in line for a multi-slot interval |

## Recent activity (2026-08-25 18:00 → 08-26 03:00)

- **19:30:** `PORT-11` step 1 closed as written on the first run — one
  64 MHz lumped-sheet solve on the loaded gapped birdcage, stop rule
  cleared, 10 MHz anchor to 2.6e-10, step 2 priced at standard tier.
- **21:00:** `MAG-19` step 2 landed the duty-transfer ruling — red
  reproduced first on the pre-fix parent, disposition green on
  bit-identical errors, `MAG-18` untouched as negative control. Chunk ✅;
  audited §4-COMPLIANT this review (all four footers, every digit, zero
  edits to the control module verified).
- **22:30:** both `EX-30` mesh-red rulings landed — the `GEO-16` cell
  record re-recorded version-tagged (79 070), the `mesh:5` control
  re-chosen measure-first (0.018, margins +0.105/+0.107) as a third
  build so no gate constant moved. Census exact, both known-issues
  entries retired.
- **00:00:** `GEO-21` step 1 measured its candidate control into a third
  branch (0.9167 — inside the module's own separation guard, so the
  named branch is excluded by measurement), handed over a measured
  coarse-ward ladder, adopted nothing. **Ruled this review: control =
  4.8e-3** (separation 2× the guard width, guard unmoved; the
  cliff-adjacent 6.4e-3 rejected).

## Automation health

- Four slots scheduled, four ran, all four landed on `main` clean — two
  chunk/step closes and two disciplined stops-with-measurements. No
  wedges, no `recovered/*`, no `attempt/*`, tree clean at every handoff
  and at this review.
- The measure-first discipline keeps paying: every ruling this review
  made (GEO-21 control, MAG-20 commissioning, PORT-11 step-2 tier) was
  made from numbers already in the logs, at zero new compute.
- Queue holds **six items, all mutually independent — no serial
  dependencies this interval**. Commissioned but not queued: `MAG-20`
  (the last sampled-band residual, measure-first), `GEO-20` step 2,
  `OPS-26` step 2 (needs ≥ 2 consecutive slots).

## On deck (§9 — six items this review)

1. **`GEO-21` step 2** — land the ruled coarse-graded control
   (4.8e-3); retires the last of the three example-found 0.11 gate
   reds (standard, independent)
2. **`PORT-11` step 2** — the 4×4 S-matrix at 64 MHz under the unmoved
   `PORT-9` gates, displaced-mesh negative control (standard,
   independent; the mission's first Larmor port *gate*)
3. **`EX-30` leg (ports)** — ports + `ans` examples, licensed
   re-records (standard, independent)
4. **`EX-30` leg (root) completion** — the ruled reds + licensed guide
   tables; serial dependency discharged, now independent (standard)
5. **`EX-33`** — first 16-leg birdcage example (`GEO-19` ramp;
   standard, independent)
6. **`EX-32`** — first birdcage S-parameter example (`PORT-9` ramp;
   standard, independent; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
