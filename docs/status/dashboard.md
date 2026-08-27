# FEM-EM Solver — status

**Updated:** 2026-08-27 18:00, **daily review (scheduled, ran normally)**.
Headline: **the 0.11 execution census is finished and `OPS-26` is ✅** —
repo-wide **452 of 478 collected tests (94.6%) observed in a footered run
on the 0.11 image: 436 green, 16 red, 26 deferred**, every deferral a
measured cost or a filed defect. The question the operator asked on
08-25 — did the 0.11 transition actually work — is answered **yes**: every
physics gate behind a §2 claim was seen executing and passing, including
the h-refinement gate that was red when the census was commissioned. The
16 reds are bookkeeping, not physics, in three owned families: **ten stale
constants recorded on the old 0.7.2 image** (five distinct mesh cell counts
plus one 128 MHz error record — the solver reproduces the new numbers, the
tests hold the old ones; `OPS-27`, split into two queue items), three gmsh
"overlapping facets" sites (`GEO-23`), and one test double an earlier
rank-safety fix outgrew (`OPS-28`). Nothing in §2 moved. What this does
**not** say: nothing is compared against an external reference at 64/128
MHz, nothing is tuned or resonant, no B1+/SAR on the coil. Source of truth
is `PROJECT_PLAN.md`; this page is a read-only digest for the human
operator.

## Waiting on you

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the
   second case in the same queue.
4. FYI, no action: **your 08-25 directive is closed** — `OPS-26` found no
   formulation or solver break on 0.11; `OPS-18`'s close stands. The Sunday
   08-30 weekly review owes three decisions — the F-human fixture
   directive, **`ANS-4` commissioning**, and whether a 128 MHz resolution
   study is warranted — and now also whether `PORT-4`…`PORT-8` resume.
   Local `main` remains well ahead of origin (push is manual).
5. FYI, no action: **ten `main` reds are stale 0.7.2-era records, not
   regressions** — do not read a `dR`/cell-count/`test_geometry_floor_discriminator.py`
   failure as a physics problem. `OPS-27` steps 1–2 re-record them
   version-tagged (queue items 1–2). One more suspected site sits behind a
   fixture too expensive to reach (`box_truncation`, > 590 s at two rank
   widths) and is filed pending.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate **executes and passes on 0.11** (census, 141 s); one sibling sampled band gets its own measurement (`MAG-20`, queued) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; all Dodd–Deeds physics readings reproduce on 0.11 — only recorded cell counts drifted |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; all 32 birdcage gate tests green on 0.11) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads 0.06–0.10% vs 0.5%; **self-consistency identities only — absolute accuracy at Larmor is `ANS-4` (weekly review)** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ **census complete: 452/478 observed on 0.11 (436 green)**; 16 reds, none a physics gate — 10 stale 0.7.2 records (`OPS-27`), 3 gmsh "overlapping facets" (`GEO-23`), 3 stale test double (`OPS-28`); 26 deferrals all measured (14 on the `TH-12` memory wall, 7 behind > 590 s module fixtures, 5 `GEO-23`) | `OPS-27` is queue items 1–2, `OPS-28` item 3, `GEO-23` step 1 item 8 |

## Recent activity (2026-08-27 10:30 → 18:00)

- **12:00:** leg (e) — 214/289; the warm-cache ordering fix for
  `third_rung` confirmed; a **poisoned 0-byte FFCx stub** from an earlier
  killed window produced a footered run with every name in ERROR — now a
  mandatory pre-window sweep; a fourth stale record (+0.233%).
- **13:30:** leg (f) — 255/289, 41 names in one slot; the stale-record
  class **collapses to shared meshes** (nine names, four cell counts);
  two "unpriced" modules turned out to be priced in the journal.
- **15:00:** leg (g) — 264/289; `gap_voltage_padding` ruled a measured
  structural deferral (module fixture > 590 s); `wire_resolution` complete
  6/6 by running its two recorded halves; a tenth stale record, a fifth
  mesh, this one with no sibling.
- **16:30:** leg (h) — **268/289, census closed**; `box_size` 4/4 green on
  its halves; `box_truncation` a permanent measured deferral at two widths;
  chunk-level reconciliation written; **`OPS-26` ✅**.
- **18:00 review:** `OPS-26` audited COMPLIANT (18 footers re-read, all
  arithmetic reproduces; one reds-vs-sites wording defect fixed); `OPS-27`
  re-scoped from two constants to the census's eleven-name / five-mesh
  site list and split into two independent halves; no new chunk invented.

## Automation health

- Four of four scheduled slots ran, all landed on `main` clean — zero
  parked branches, zero wedges, zero denials. Eight consecutive slots on
  one item, by design, and it closed.
- 18 harness logs this interval, 6 939 s of recorded compute over 18
  windows; 6 exit-124 windows, every one now either a re-price, a rule
  (stub sweep, journal-grep-before-sizing), or a measured structural
  deferral.
- Queue holds **eight items**: `OPS-27` step 1, `OPS-27` step 2, `OPS-28`,
  then `MAG-20`, `GEO-20` step 2, `EX-34`, `GEO-22`, `GEO-23` step 1 — no
  serial dependencies.

## On deck (§9 — eight items this review)

1. **`OPS-27` step 1** — re-record the cheap half of the stale records by
   mesh value (128 MHz error record, the 138 619 mesh ×4, `mesh_cache`);
   ≈ 570 s of anchor re-runs (standard)
2. **`OPS-27` step 2** — the expensive half (the 417 914 mesh ×3,
   `combined_knobs`, `wire_resolution`); ≈ 1 440 s (heavy; independent
   of step 1)
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
8. **`GEO-23` step 1** — classify the five "overlapping facets" sites by
   rank width, ladder the resolution, revive or delete the dead module
   (smoke + standard; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
