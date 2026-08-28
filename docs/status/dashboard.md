# FEM-EM Solver — status

**Updated:** 2026-08-28 03:00, **daily review (scheduled, ran normally)**.
Headline: **the census's bookkeeping reds are being retired on schedule —
three chunks closed in four slots.** `OPS-27` re-recorded all ten stale
0.7.2-era constants version-tagged (seven anchor re-runs, 2 127 s, every
one green, no band moved, `src/` untouched); `OPS-28` restored the test
double behind an earlier rank-safety fix (sign-flip identity green at
1e-12); `MAG-20` measured the last sampled two-sided rate band at three
sampling counts and **kept it, validated** (rates 0.79 / 0.72 / 0.99 inside
[0.7, 1.5]). Of the 16 reds the census filed, the residual on `main` is
**five**: two pre-existing placeholder-route names (known-issues entry 3,
owned by `PORT-0`/`PORT-1`) and the three gmsh "overlapping facets" sites
(`GEO-23`, queued). Nothing in §2 moved. What this does **not** say:
nothing is compared against an external reference at 64/128 MHz, nothing
is tuned or resonant, no B1+/SAR on the coil. Source of truth is
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
4. FYI, no action: the Sunday **08-30 weekly review** owes four decisions —
   the F-human fixture directive, `ANS-4` commissioning, whether a 128 MHz
   resolution study is warranted, and whether `PORT-4`…`PORT-8` resume.
   Local `main` remains well ahead of origin (push is manual).
5. FYI, no action: **the stale-record reds are gone.** A `dR`/cell-count/
   `test_geometry_floor_discriminator.py` failure would now be new
   information, not the known 0.7.2 drift. One suspected site behind a
   > 590 s fixture (`box_truncation`) remains filed pending, unqueued.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11; the sibling sampled band **validated by measurement** (`MAG-20` ✅, thin n = 10 margin recorded) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; every Dodd–Deeds module now green on 0.11 with re-recorded, version-tagged cell counts |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads 0.06–0.10% vs 0.5%; **self-consistency identities only — absolute accuracy at Larmor is `ANS-4` (weekly review)** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ census complete (452/478 observed on 0.11); **residual reds 5, none a physics gate** — 2 placeholder-route names (entry 3, `PORT-0/1`), 3 gmsh "overlapping facets" (`GEO-23`); 26 deferrals all measured; two `OPS-27` modules re-recorded but re-run still owed | `GEO-23` step 1 is queue item 4, the owed re-runs item 5 |

## Recent activity (2026-08-27 18:00 → 2026-08-28 03:00)

- **19:30:** `OPS-27` step 1 — six names in four files re-recorded; four
  anchors green in 604 s; found the 138 619 family is **one** imported
  constant, not four (finding 38).
- **21:00:** `OPS-27` step 2 — four edits in four files (one site an import
  alias, finding 41); three anchors green in 1 523 s, all above their
  census price so the ≥ 1.5× sizing rule stays; **`OPS-27` ✅**.
- **22:30:** `OPS-28` — one `allgather` on the test double; red baseline →
  green on the identical 2-s command; known-issues entry 3 corrected: the
  placeholder's zero lands on the **off-diagonal** here, not the diagonal;
  **`OPS-28` ✅**.
- **00:00:** `MAG-20` — sampled-rate sweep at n_points 8/10/20, no edge
  crossed, band kept and validated, `E_Ω` 1.6854 reproduced; **`MAG-20` ✅**.
- **03:00 review:** all three audited COMPLIANT; one tier label corrected
  (`OPS-27` step 1 is heavy, not standard); `OPS-27` step 3 commissioned
  for the owed tail; `tests/ports` folded into `GEO-23` step 1 as a 2-s
  coverage rider; no third `MAG-20` rung, no example chunk, no invention.

## Automation health

- Four of four scheduled slots ran, all landed on `main` clean — zero
  parked branches, zero wedges, zero denied compute commands, zero exit-124
  windows this interval (first clean interval since the census began).
- 11 harness logs, 2 552 s of recorded compute; the one permission friction
  (a shell `for … python3 - <<EOF` loop) was worked around with per-copy
  `Edit`, at zero cost.
- Queue holds **five items**: `GEO-20` step 2, `EX-34`, `GEO-22`, `GEO-23`
  step 1, `OPS-27` step 3 — no serial dependencies.

## On deck (§9 — five items this review)

1. **`GEO-20` step 2** — 32 ring-gap ports at 16 legs under the per-class
   reading (standard)
2. **`EX-34`** — birdcage S-matrix across 10 / 64 / 128 MHz on one mesh
   (`PORT-11` ramp; standard)
3. **`GEO-22`** — bisect and guard the straight-wire coarse-resolution
   floor (smoke + standard)
4. **`GEO-23` step 1** — classify the three "overlapping facets" sites by
   rank width, ladder the resolution, own the dead module; `tests/ports`
   rides along (smoke + standard)
5. **`OPS-27` step 3** — re-run the two owed 418 888 modules, sweep the
   stale prose copies (heavy; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
