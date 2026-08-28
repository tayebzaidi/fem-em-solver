# FEM-EM Solver — status

**Updated:** 2026-08-28 18:00, **daily review (scheduled, ran normally)**.
Headline: **the queue drained clean, and the 32-port sheet defect is
diagnosed to one missing keyword.** `GEO-23` landed both levers — the
gmsh deadlocks now fail in 2–3 s instead of 120 s, and the three census
"overlapping facets" reds are green on a measured coarsest-meshing rung
(1213 / 5464 cells reproduced exactly at two widths) — but the review
**demoted it to 🧪**: the cell-count anchor is printed, not asserted, and
the one new test only checks "raised on every rank"; a one-slot assert
returns it. `GEO-20`'s discriminator confirmed the broken-sheet set moves
with the rank width and equals the set of ports straddling a partition —
and an interactive session then found the cause: `birdcage_port_domain`
is built with **no ghost layer**, so the 4-leg fixture itself loses one
facet at `-n 12`; the `shared_facet` plumb returns every port to
1.000000000000 at the same cell count. That fix is `GEO-24`, now split
into four slots because four chunks' records were taken on that fixture
and must be read before and after. `OPS-27` closed its owed tail
(`17 passed` / `18 passed`), and `OPS-29` fixed a rank-local material
check that broke `mri:1` at `-n 12`. Nothing in §2 moved. What this does
**not** say: nothing is compared against an external reference at 64/128
MHz, nothing is tuned or resonant, no B1+/SAR on the coil. Source of
truth is `PROJECT_PLAN.md`; this page is a read-only digest for the human
operator.

## Waiting on you

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. **Note `ANS-5` before you do:** our production
   `degree 1` corresponds to HFSS **Zero Order**, not its default **First
   Order** — the specs do not yet say so; the weekly review rules on the
   wording, but a default-settings AED run is a different discretization.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the
   second case in the same queue.
4. FYI, no action: the Sunday **08-30 weekly review** owes seven
   decisions — the F-human fixture directive, `ANS-4` commissioning, a
   128 MHz resolution study, `PORT-4`…`PORT-8`, the `GEO-22` wire
   size-field re-record licence, the `GEO-21` coarse-conductor floor on
   `birdcage_port_domain` (the last "overlapping facets" red on `main`),
   and **`ANS-5`** (element-order wording in every ANS spec). The
   `_interface_facet_tags` fix listed last interval is **withdrawn** — the
   diagnosis put the defect elsewhere. Local `main` remains well ahead of
   origin (push is manual).
5. FYI, no action: every example's output artifacts are now prefixed with
   group and number (`docs(examples)`, this interval).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11; the sibling sampled band validated by measurement (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; every Dodd–Deeds module green on 0.11 with version-tagged cell counts (`OPS-27` ✅, tail closed 08-28) |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; `EX-34` ✅ 08-28) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only, recorded at `-n 2` on a fixture with no ghost layer — `GEO-24` re-reads them at `-n 12` before the plumb lands; absolute accuracy at Larmor is `ANS-4` (weekly review)** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ census complete (452/478 observed on 0.11); **residual reds 3, none a physics gate** — 2 placeholder-route names (entry 3, `PORT-0/1`) and `test_birdcage_volumes_partition_the_box` (`GEO-21`'s floor entry, weekly review) | the three `GEO-23` sites and the two `OPS-27` stale records went green this interval |

## Recent activity (2026-08-28 10:30 → 18:00)

- **12:00:** `GEO-23` step 2a — one helper wraps the rank-0 gmsh build in
  three generators (`git diff -w` +76 lines); the three 120-s deadlocks
  footer Status 1 in 2–3 s; collective-raise gate green at `-n 2`; every
  control unmoved (`mag:1` 21 830 cells). 72 s.
- **13:30:** `GEO-23` step 2b — three call sites moved to the measured
  coarsest meshing rung; all three census reds green at `-n 1` and `-n 2`,
  printed counts 1213 / 5464 / 5464 = step 1's ladder exactly; no physics
  assertion moved. 40 s. **Review audit: 🧪, not ✅ — the count is printed,
  not asserted; step 2c queued.**
- **15:00:** `GEO-20` step 2a — broken-sheet set moves with the width
  ({P30,P37,P45} → 5 ports at `-n 4` → 7 at `-n 8`) and equals the
  straddling set, 32 × 2 ports, no exception; volumes, closures, Pappus
  all 1.000000000000. Confirmed ⇒ stop. 378 s.
- **16:30:** `OPS-27` step 3 — `larmor_resolution` `17 passed` / 424 s,
  `third_rung` `18 passed` / 291 s; 19 of 33 prose copies swept, the
  other 14 named. Both known-issues entries retired. 719 s.
- **Interactive (between slots):** `OPS-29` ✅ (rank-local `phantom_material`
  empty-tag check, `6 passed` at `-n 2` and `-n 12`, rel 1e-12 DG0
  identities; audited COMPLIANT); `GEO-20` cause diagnosed (`GhostMode.none`
  at `io/mesh.py:3356`; 4-leg P8 closure 0.990103697427 at `-n 12`, one
  facet; plumb probe 1.000000000000 on all 12, reverted); `GEO-24`
  commissioned; `ANS-5` opened; example artifacts renamed.
- **18:00 review:** `GEO-23` demoted 🧪 (step 2c queued); `GEO-24` split
  1a / 1b / 2a / 2b with the consumer list and price rung on the entry;
  `_interface_facet_tags` fix withdrawn; `GEO-20` step 2 becomes a re-run
  after `GEO-24`; attempt branch kept as the fixture; no example chunk
  owed; no new chunk ID.

## Automation health

- Four of four scheduled slots ran, footered clean, all four items
  complete; zero `attempt/*` additions, zero `recovered/*`, zero wedges,
  zero exit-124 windows (the 12:00 slot's Status 1 footers were the
  measurement).
- 40 harness logs this interval (25 scheduled + 15 interactive),
  ≈ 1 700 s of recorded compute.
- Queue holds **five items**, one serial link: `GEO-23` 2c, `GEO-24` 1a,
  `GEO-24` 1b, `GEO-24` 2a (needs 1a), `GEO-22` probe (spare).

## On deck (§9 — five items this review)

1. **`GEO-23` step 2c** — assert the 1213 / 5464 cell counts at ±1% at the
   three moved sites; chunk back to ✅ on green (smoke)
2. **`GEO-24` step 1a** — read seven `tests/mesh/` birdcage-sheet modules
   at `-n 2` and `-n 12` before any `src/` change; `-n 12` reds are the
   measurement (standard, real)
3. **`GEO-24` step 1b** — the same two-width read for five
   `tests/validation/` birdcage-port modules against the `PORT-9`/`PORT-11`
   records (standard, complex)
4. **`GEO-24` step 2a** — land the `shared_facet` plumb, re-read the mesh
   family; every cell count and `-n 2` digit identical, every `-n 12` red
   now green — **depends on item 2** (standard)
5. **`GEO-22` step 2** — wire-surface size-field probe, 18 cells, no
   `src/` (smoke; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
