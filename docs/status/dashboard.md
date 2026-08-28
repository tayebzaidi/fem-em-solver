# FEM-EM Solver — status

**Updated:** 2026-08-28 10:30, **daily review (scheduled, ran normally)**.
Headline: **one example closed, three measured negatives, and the
"overlapping facets" story flipped.** `EX-34` put the birdcage 4-port
S-matrix across 10 / 64 / 128 MHz on one mesh (twelve solves, three gates
green on every rung, 139 s). `GEO-23` step 1 showed that **none** of the
gmsh "overlapping facets" sites is partition-dependent — all four fail at
one rank, the earlier "passes on one rank" readings were interleaved-log
artifacts, and the `-n 2` deadlock is a raise-path property with a cheap
fix. `GEO-22` measured the straight-wire resolution floor and found it
**non-monotone and bit-reproducible** — no guard value is writable.
`GEO-20`'s 16-leg ring-gap fixture builds (265 621 cells, 32 ring ports)
but three sheets fail to reconstruct at two ranks while all pass at one;
parked, unexplained, discriminator queued. Nothing in §2 moved. What this
does **not** say: nothing is compared against an external reference at
64/128 MHz, nothing is tuned or resonant, no B1+/SAR on the coil. Source
of truth is `PROJECT_PLAN.md`; this page is a read-only digest for the
human operator.

## Waiting on you

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the
   second case in the same queue.
4. FYI, no action: the Sunday **08-30 weekly review** now owes six
   decisions — the F-human fixture directive, `ANS-4` commissioning, a
   128 MHz resolution study, `PORT-4`…`PORT-8`, **plus two re-record
   licences this interval surfaced**: the `_interface_facet_tags` fix
   behind `GEO-20`'s 32-port sheets (touches every sheet-reconstructing
   module) and a wire-surface size field in `straight_wire_domain`
   (`GEO-22`, would move `mag:1`'s 21 830 cells). Local `main` remains
   well ahead of origin (push is manual).
5. FYI, no action: a new example landed — `ports:5`
   (`examples/ports/05_birdcage_larmor_frequency_ladder.py`), combined
   XDMF at 128 MHz opens in ParaView. Identities only, nothing absolute.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11; the sibling sampled band validated by measurement (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; every Dodd–Deeds module green on 0.11 with version-tagged cell counts |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; `EX-34` ✅ 08-28 demonstrates all three on one mesh) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only — absolute accuracy at Larmor is `ANS-4` (weekly review)** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ census complete (452/478 observed on 0.11); **residual reds 5, none a physics gate** — 2 placeholder-route names (entry 3, `PORT-0/1`), 3 gmsh "overlapping facets" sites, now **diagnosed** (geometry-deterministic, one 0.8-step too coarse each) and owned by `GEO-23` step 2a/2b, queue items 1–2 | `tests/ports` is now inside a scheduled command (finding 44 discharged) |

## Recent activity (2026-08-28 03:00 → 10:30)

- **04:30:** `GEO-20` step 2 — 16-leg ring-gap fixture builds; 29/32 ring
  sheets exact, **3 broken at `-n 2` only** (P30/P37 0 facets, P45 5);
  everything not routed through a sheet exact at both widths; ring
  terminals show **no** azimuth-class split (spread 2.6e-7); cost rung
  110 786 → 265 621 cells (2.40×), mesh 23.3 → 72.2 s. Parked, no band.
- **06:00:** `EX-34` — `ports:5` green, 139 s: reciprocity ≤ 1.7e-14,
  σ_max ≤ 0.99999, C4 spreads ≤ 0.10%, 64/128 MHz records inside 1%,
  cells/λ 12.5024, heuristic control separated by 1.585; **`EX-34` ✅**.
- **07:30:** `GEO-22` step 1 — nine-rung sweep on two geometries,
  **non-monotone** (0.00875 fails, 0.009 meshes), bit-identical on
  repeat; no guard written, `src/` untouched. Negative result.
- **09:00:** `GEO-23` step 1 — 2 × 4 Status table, all sites red at
  `-n 1`; rank-divergence claims withdrawn; deadlock is the raise path;
  ladders monotone (`cylindrical` 0.040 → 0.032 / 1 213 cells,
  `coil_phantom` 0.030 → 0.024 / 5 464); dead module → one asserting
  test; `tests/ports` rider read exactly `2 failed, 15 passed`.
- **10:30 review:** `EX-34` audited COMPLIANT; `GEO-23` step 2 split and
  commissioned (raise-path + sizing); `GEO-22` guard shape ruled (wrap
  adopted via `GEO-23` 2a, allowlist rejected, size field → probe now,
  licence to the weekly review); `GEO-20` discriminator queued, fix
  withheld; attempt branch kept; no example chunk owed, no invention.

## Automation health

- Four of four scheduled slots ran and footered clean — one parked
  `attempt/*` branch (by design, a pre-authorised negative), zero
  `recovered/*`, zero wedges, zero denied compute commands; two exit-124
  windows were *measurements* (`GEO-23`'s 120-s deadlock cells), not
  overruns.
- 21 harness logs, ≈ 975 s of recorded compute this interval.
- Queue holds **five items**, mutually independent: `GEO-23` 2a, `GEO-23`
  2b, `GEO-20` 2a, `OPS-27` step 3, `GEO-22` probe (spare).

## On deck (§9 — five items this review)

1. **`GEO-23` step 2a** — wrap the rank-0 gmsh throw in three generators
   so deadlocks footer in seconds; `GEO-22` gate rides along (standard)
2. **`GEO-23` step 2b** — move three call sites to the measured coarsest
   meshing rung; retires four census reds if physics stays green (standard)
3. **`GEO-20` step 2a** — `-n 4`/`-n 8` broken-port discriminator with
   per-port rank ownership, no `src/` (standard)
4. **`OPS-27` step 3** — re-run the two owed 418 888 modules, sweep the
   stale prose copies (heavy)
5. **`GEO-22` step 2** — wire-surface size-field probe, 18 cells, no
   `src/` (smoke; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
