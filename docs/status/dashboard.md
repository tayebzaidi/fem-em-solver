# FEM-EM Solver — status

**Updated:** 2026-08-27 10:30, **daily review (scheduled, ran normally)**.
Headline: **the 0.11 execution census is at 207 of 289 on its expensive
half** — `OPS-26` step 2 took all four slots again (legs (b)–(d)) and is
now 202 green / 5 red / 82 deferred over `tests/validation` + `tests/ports`,
arithmetic reconciled at every handoff. The four reds that count are all
*bookkeeping*, none physics: a test double that an earlier rank-safety fix
outgrew (2 tests), and **two stale constants recorded on the old 0.7.2
image and never swept when the 0.11 figures were re-recorded** (a 128 MHz
error record, an exact mesh cell count). The birdcage `PORT-9`/`PORT-11`
block is 32/32 green on 0.11; two inherited "horror story" modules turned
out to run fine in the right build. Two small chunks commissioned
(`OPS-27`, `OPS-28`); the census tail is 2–3 more slots. No chunk closed;
nothing in §2 moved. What this does **not** say: nothing is compared
against an external reference at 64/128 MHz, nothing is tuned or resonant,
no B1+/SAR on the coil. Source of truth is `PROJECT_PLAN.md`; this page is
a read-only digest for the human operator.

## Waiting on you

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the
   second case in the same queue.
4. FYI, no action: the Sunday 08-30 weekly review owes three decisions —
   the F-human fixture directive, **`ANS-4` commissioning**, and whether a
   128 MHz resolution study is warranted. Local `main` remains well ahead
   of origin (push is manual).
5. FYI, no action: **three `main` reds are stale 0.7.2-era records, not
   regressions** — the solver reproduces the re-recorded 0.11 numbers; the
   tests hold the old ones. `OPS-27` re-records them version-tagged (queue
   item 2). Do not read the `test_geometry_floor_discriminator.py` failure
   as a `TH-10` problem.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); one sibling sampled band gets its own measurement (`MAG-20`, queued); `test_straight_wire.py` 7/7 green on 0.11 (314 s) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; all 32 birdcage gate tests green on 0.11, 08-27) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads 0.06–0.10% vs 0.5%; **self-consistency identities only — absolute accuracy at Larmor is `ANS-4` (weekly review)** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ⚠️ **census 391/478 repo-wide** (cheap roots 184/189 done; expensive half 207/289): **7 reds filed, none a physics gate** — 3 gmsh "overlapping facets" sites (`GEO-23`), 2 stale 0.7.2 records (`OPS-27`), 1 stale test double (`OPS-28`), 1 matched-port diagonal (entry 3); 1 dead module | `OPS-26` leg (e) is queue item 1, 82 names, 2–3 slots |

## Recent activity (2026-08-27 03:00 → 10:30)

- **04:30:** leg (b), slot 1 — denominator re-derived (289, not the
  inherited 232); `tests/ports` complete 17/17 with 3 reds; **new defect
  class**: `OPS-14`'s correct rank-safety `allgather` outgrew a test
  double, which no static sweep can see. The owed `materials` complex
  conversion landed on a fifth gmsh site, rank-divergent.
- **06:00:** slot 2 — 139/289, **117 names green, zero reds**, after
  reading the build gate before sizing (53 of 59 validation modules are
  complex-gated; the previous slot's real-build shape was scoring them as
  skips). `test_circular_loop.py`, the old JIT casualty, is green.
- **07:30:** slot 3 — 188/289; birdcage block 32/32 green at the census's
  best rate; one *manufactured* red (a magnetostatics module run in the
  complex build — the classifier keyed on a comment); one genuine red, the
  pre-`OPS-18` 128 MHz constant. The `helmholtz_v2` "hang" was the same
  build-gate artifact.
- **09:00:** slot 4 — 207/289; the exact 0.7.2 cell count vs 0.11's
  +0.032%; `third_rung`'s 174.86 s record exposed as a warm-cache price
  (cold: exit 124 at 300 s).
- **10:30 review:** nothing to audit; leg (e) queued first with leg (d)'s
  draw order; `OPS-27` (stale records) and `OPS-28` (test double)
  commissioned; the `materials` site folded into `GEO-23`'s table.

## Automation health

- Four of four scheduled slots ran, all landed on `main` clean — zero
  parked branches, zero wedges, zero denials. All four went to one item,
  by design.
- 55 harness logs, ~5 500 s of recorded compute; the real losses were one
  misclassified-build window (192 s) and two exit-124 windows (401 s,
  301 s) — all three now carry a rule or a re-price.
- Queue holds **eight items**: `OPS-26` leg (e), `OPS-27`, `OPS-28`, then
  `MAG-20`, `GEO-20` step 2, `EX-34`, `GEO-22`, `GEO-23` step 1 — no
  serial dependencies.

## On deck (§9 — eight items this review)

1. **`OPS-26` step 2 leg (e)** — the 82-name census tail in leg (d)'s
   costed order, then the chunk-level reconciliation (heavy; 2–3 slots)
2. **`OPS-27`** — re-record the two stale 0.7.2 constants version-tagged,
   sweep for siblings (standard, ~4 min compute)
3. **`OPS-28`** — give the `_DummyComm` double its `allgather`, re-read
   known-issues entry 3 (smoke)
4. **`MAG-20`** — measure-then-dispose the last sampled two-sided rate
   band (standard)
5. **`GEO-20` step 2** — 32 ring-gap ports at 16 legs under the per-class
   reading (standard)
6. **`EX-34`** — birdcage S-matrix across 10 / 64 / 128 MHz on one mesh
   (`PORT-11` ramp; standard)
7. **`GEO-22`** — bisect and guard the straight-wire coarse-resolution
   floor (smoke + standard)
8. **`GEO-23` step 1** — classify the (now four) "overlapping facets" sites
   by rank width, ladder the resolution, revive or delete the dead module
   (smoke + standard; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
