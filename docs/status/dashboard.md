# FEM-EM Solver — status

**Updated:** 2026-08-29 03:00, **daily review (scheduled, ran normally)**.
Headline: **four of four slots landed their item, the ghost-layer plumb is
measured correct on every birdcage consumer, and one ruling was owed — it
is now made.** `GEO-23` returned to ✅ (the three cell-count anchors are
asserted, 0.00% off, negative control footered red). `GEO-24` read the
whole birdcage-fixture record set at `-n 2` and `-n 12` before and after
the one-keyword `shared_facet` plumb: cell counts never move, both `-n 12`
reds repair to 1.000000000000 / 256 facets, and the validation family pays
**nothing** for the missing ghost layer. The slot stopped on its own clause
because one `-n 2` digit moved (255 → 256 facets) — and then proved with a
`-n 1` control on `main` that 256 is the serial truth, i.e. the *record*
was one facet short. **Ruling: defect repair, not re-baseline; land it.**
The plumb is queued to land first thing, the validation re-read and the
32-port `GEO-20` re-run follow it. New finding, now its own chunk
(`PORT-12`): the two-torus gap-route record — on a fixture that already
has the ghost layer — drifts 1.33e-4 at `-n 12` against a 1e-4 band, in a
*solved* line integral, not a reconstruction. Nothing in §2 moved. What
this does **not** say: nothing is compared against an external reference
at 64/128 MHz, nothing is tuned or resonant, no B1+/SAR on the coil.
Source of truth is `PROJECT_PLAN.md`; this page is a read-only digest for
the human operator.

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
4. FYI, no action: the Sunday **08-30 weekly review** owes eight
   decisions — the F-human fixture directive, `ANS-4` commissioning, a
   128 MHz resolution study, `PORT-4`…`PORT-8`, the `GEO-22` wire
   size-field re-record licence, the `GEO-21` coarse-conductor floor on
   `birdcage_port_domain` (the last "overlapping facets" red on `main`),
   `ANS-5` (element-order wording), and **new: `PORT-12`** — whether the
   two-torus 1e-4 reproduction band is width-qualified once the
   `-n 4`/`-n 8` table exists. Local `main` remains well ahead of origin
   (push is manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11; the sibling sampled band validated by measurement (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; every Dodd–Deeds module green on 0.11 with version-tagged cell counts (`OPS-27` ✅) |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; `EX-34` ✅ 08-28) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only. Now read at `-n 12` too (`GEO-24` step 1b): every gated digit identical at both widths, before the plumb.** The two-torus gap-route record is a `-n 2` statement until `PORT-12` classifies its 1.3e-4 drift at `-n 12`; absolute accuracy at Larmor is `ANS-4` (weekly review) |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ census complete (452/478 observed on 0.11); **residual reds on `main` at `-n 2`: 3, none a physics gate** — 2 placeholder-route names (entry 3, `PORT-0/1`) and `test_birdcage_volumes_partition_the_box` (`GEO-21`'s floor entry, weekly review). At `-n 12` only: two birdcage facet reds (repaired by the plumb landing as §9 item 1) and the two-torus `PORT-12` drift | `GEO-23` back to ✅ with asserted anchors |

## Recent activity (2026-08-28 18:00 → 2026-08-29 03:00)

- **19:30:** `GEO-23` step 2c — `N_CELLS_REF` asserted at the three moved
  sites (1213 / 5464 / 5464, 0.00% at `-n 1` and `-n 2`); negative control
  (ref 1300) footered Status 1 on both ranks, restored green. 44 s.
  **Chunk back to ✅ — audited COMPLIANT this review** (harness logs, agent
  execution, quantitative anchor against a documented prior-run reference,
  elapsed recorded, nothing loosened). The step-2b `allreduce(size_local)`
  was removed, not wrapped — `size_global` is already global.
- **21:00:** `GEO-24` step 1a — seven `tests/mesh/` consumers at `-n 2` and
  `-n 12` on `main`: every cell count identical; `-n 2` green ×7; two
  `-n 12` reds, both facet reconstruction — `ring_gaps` P8 closure
  0.990103697427 (the predicted digit exactly) and `port_terminals`'
  phantom↔air interface 245 facets / 0.935322. So the ghost-layer gap hits
  any interior interface, not only port sheets. `port_scaleup` at `-n 12`
  108 s — nothing unmeasured. 668 s.
- **22:30:** `GEO-24` step 1b — five `tests/validation/` consumers at both
  widths, complex: all green, every gated digit identical (`Z_ij` at
  ≤ 2.6e-10, σ_max 0.999992805, C4 spreads 0.0553 / 0.0353 / 0.0214 %).
  **Negative control failed:** the already-plumbed two-torus module is
  red at `-n 12` (gap ratio 0.894274 vs 0.894141, 1.33e-4 vs 1e-4) at an
  unchanged 184 176 cells. 660 s.
- **00:00:** `GEO-24` step 2a — plumb applied, seven modules re-read at both
  widths: cell counts identical, both `-n 12` reds repaired (P8 back to
  176 / 1.000000000000; phantom↔air back to 256), all seven green at both
  widths. Stopped on the item's own clause — one `-n 2` digit moved
  (255 / 0.979885 → 256 / 0.984183) — reverted and parked on
  `attempt/GEO-24-step2a-20260829T052300Z`; then diagnosed: `-n 1` on
  `main` reads 256 / 0.984183, so the record was short. ≈ 870 s.
- **03:00 review:** ruled defect-repair-not-re-baseline; `GEO-24` step 2a′
  (land + re-read) queued first, 2b second; `GEO-20` step 2 re-run queued
  after the plumb; `PORT-12` opened (two-torus width drift) with its own
  known-issues entry; the `GEO-20`/`GEO-24` entry retires with 2b; no
  example chunk owed (`GEO-23`'s closed gate is test hygiene, not a
  capability); nothing demoted.

## Automation health

- Four of four scheduled slots ran, footered clean, all four items
  complete or stopped on their own pre-stated clause; one `attempt/*`
  addition (the measured-good plumb, by design), zero `recovered/*`, zero
  wedges, zero exit-124 windows; tree clean at review time.
- 53 harness logs this interval, ≈ 2 240 s of recorded compute; `-n 12`
  costs the same wall clock as `-n 2` on every birdcage module (mesh built
  on rank 0), measured three times.
- Queue holds **five items**, one serial hinge: `GEO-24` 2a′ (land) →
  {`GEO-24` 2b, `GEO-20` step 2 re-run}; `GEO-22` probe and `PORT-12`
  step 1 are independent. Two `attempt/*` branches, both consumed by
  items 1 and 4.

## On deck (§9 — five items this review)

1. **`GEO-24` step 2a′** — cherry-pick `e1dede8`, re-read `port_terminals`
   at `-n 1/2/12` and `ring_gaps` at `-n 2/12`; 256 / 0.984183 and
   1.000000000000 at every width; annotate the defective 255 (standard,
   ≈ 5 min)
2. **`GEO-24` step 2b** — validation family on the plumbed tree at both
   widths; reconstruction digits to the digit, solved digits to their
   bands; on green the chunk closes and the known-issues entry retires —
   **depends on item 1** (standard, complex, ≈ 12 min)
3. **`GEO-22` step 2** — wire-surface size-field probe, 18 cells, no
   `src/` (smoke; independent)
4. **`GEO-20` step 2 re-run** — the parked 32-port module at `-n 2` and
   `-n 12` on the plumbed tree; 32 × 1.000000000000 predicted —
   **depends on item 1** (standard, ≈ 8 min)
5. **`PORT-12` step 1** — two-torus gap ratio at `-n 4` and `-n 8` to
   classify the width drift; no band moves (standard, complex, ≈ 4 min;
   spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
