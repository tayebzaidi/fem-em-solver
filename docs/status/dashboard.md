# FEM-EM Solver — status

**Updated:** 2026-08-29 10:30, **daily review (scheduled, ran normally)**.
Headline: **four of four slots landed, the ghost-layer plumb is on `main`
and verified on every birdcage consumer at 2 and 12 ranks, and the 32-port
ring-gap fixture is green at both widths.** `GEO-24` closed (256 / 0.984183
at `-n 1/2/12`; the five validation modules reproduce every gated digit
after the plumb — the only `-n 12` movement is `Z_11` at 4.1e-9). `GEO-20`
closed: the 16-leg ring-gapped fixture's 32 sheets all read 1.000000000000
at `-n 2` and `-n 12` on 265 621 cells; the three broken sheets from
2026-08-28 are repaired exactly as the ghost-layer diagnosis predicted. The
wire-surface size field (`GEO-22` step 2) removes the gmsh fallback in
18/18 rungs — but that closure was **demoted to 🧪** here because its only
executed assertion is a did-raise property, the same clause the 08-28
audit applied to `GEO-23`; a one-assert fix is queued. Two decisions made:
the **first B₁⁺ chunk is scoped** (`WF-6` step 1 — §10 subgoal 4 was due
it on 08-25) and an example for the production high-pass topology is
commissioned (`EX-35`). Nothing in §2 moved. What this does **not** say:
nothing is compared against an external reference at 64/128 MHz, nothing
is tuned or resonant, no B1+/SAR number exists yet on the coil. Source of
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
4. FYI, no action: the Sunday **08-30 weekly review** owes nine decisions
   — the F-human fixture directive (cost probe first; facts it needs are
   in §9 ruling 4: the ring rung has 32 sheets not 48, a two-drive probe
   needs no `src/` change, measured price ~6.5 s/solve at 116 k cells),
   `ANS-4` commissioning, a 128 MHz resolution study, `PORT-4`…`PORT-8`,
   the `GEO-22` wire size-field re-record licence (now with the 18-cell
   table in hand), the `GEO-21` coarse-conductor floor, `ANS-5`
   (element-order wording), `PORT-12`'s width-qualification once the
   `-n 4`/`-n 8` table exists, and the `MAT-4` one-month stall (its fix
   is `WF-6` step 3, downstream of the B₁⁺ step queued now). Local `main`
   remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11; the sibling sampled band validated by measurement (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; every Dodd–Deeds module green on 0.11 with version-tagged cell counts (`OPS-27` ✅) |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; `EX-34` ✅ 08-28) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only. Read at `-n 2` and `-n 12` on the plumbed tree (`GEO-24` ✅ 08-29): every gated digit reproduces at both widths.** The two-torus gap-route record is a `-n 2` statement until `PORT-12` classifies its 1.3e-4 drift at `-n 12`; absolute accuracy at Larmor is `ANS-4` (weekly review) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | `GEO-18`/`19`/`20`/`24` ✅; the production high-pass layout (16 legs, 32 ring sheets, 265 621 cells) reads 1.000000000000 on every sheet at `-n 2` and `-n 12`; no solve exists on it yet |
| B₁⁺ / coil-driven SAR | ⬜ not computed | `WF-6` step 1 scoped 08-29 (10 MHz, F-small, power-accounting + C4 covariance gates); `MAT-4`'s coil route follows it |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ census complete (452/478 observed on 0.11); **residual reds on `main` at `-n 2`: 3, none a physics gate** — 2 placeholder-route names (entry 3, `PORT-0/1`) and `test_birdcage_volumes_partition_the_box` (`GEO-21`'s floor entry, weekly review). At `-n 12` only: the two-torus `PORT-12` drift (the two birdcage facet reds are repaired) | `GEO-22` 🧪 pending its one assert |

## Recent activity (2026-08-29 03:00 → 10:30)

- **04:30:** `GEO-24` step 2a′ — the plumb cherry-picked as `470f410`;
  phantom↔air 256 / 0.984183 at `-n 1`, `-n 2` and `-n 12`, `ring_gaps`
  P8 176 / 1.000000000000 at `-n 12`, no cell count moved anywhere,
  controls green. 246 s. Attempt branch deleted.
- **06:00:** `GEO-24` step 2b — five validation modules at both widths on
  the plumbed tree, complex: reconstruction digits identical to the digit,
  every solved digit inside its band, `Z_11` moves 4.1e-9 at `-n 12`.
  485 s. **Chunk ✅; known-issues entry retired. Audited COMPLIANT.**
- **07:30:** `GEO-22` step 2 — wire-surface size field: 18/18 OK, 0/18
  fallbacks; leg-C control bit-identical in its own process; leg D's cell
  count monotone in `h`. 63 s. **Demoted ✅ → 🧪 this review** (no
  quantitative assert executed); step 2c queued.
- **09:00:** `GEO-20` step 2 attempt 2 — the 32-port module green at
  `-n 2` (188 s) and `-n 12` (184 s), 265 621 cells, all 32 sheets /
  closures / volumes 1.000000000000, P30 / P37 / P45 repaired. **Chunk ✅.
  Audited COMPLIANT** (two prose corrections at the 1e-16 floor).
- **10:30 review:** three audits; `GEO-22` demoted; `WF-6` step 1 scoped
  (§10 subgoal 4's first B₁⁺ chunk); `EX-35` commissioned; Phase-6 probe
  facts recorded for the weekly review (32 sheets not 48; ~6.5 s/solve,
  not ~50 s); five independent items queued.

## Automation health

- Four of four scheduled slots ran, footered clean, all four items
  complete; zero `attempt/*` (both consumed and deleted), zero
  `recovered/*`, zero wedges, zero exit-124 windows; tree clean at review
  time. Container Up 2 days.
- 23 harness logs this interval, ≈ 1 170 s of recorded compute; `-n 12`
  costs the same wall clock as `-n 2` on every birdcage module, measured
  again on the 265 621-cell rung (67.72 vs 68.19 s mesh).
- Queue holds **five independent items**, no serial link.

## On deck (§9 — five items this review)

1. **`PORT-12` step 1** — two-torus gap ratio at `-n 4` and `-n 8` to
   classify the width drift; no band moves (standard, complex, ≈ 4 min)
2. **`WF-6` step 1** — first B₁⁺ map at 10 MHz on the loaded F-small
   birdcage; three-way power accounting to 1% and C4 covariance to 5%;
   `post/faraday.py` (standard, complex, ≈ 75 s + two example re-runs)
3. **`EX-35`** — `mesh:9`, the 16-leg ring-gapped 32-sheet fixture as an
   example with combined XDMF (standard, ≈ 150 s)
4. **`GEO-22` step 2c** — assert the size-field counts 19 823 / 21 830 ±1%
   and fallback 0 / ≥ 1; restores ✅ (smoke, ≈ 30 s)
5. **`TH-13` step 1** — degree-2 discriminator on a magnetically dominated
   loop-drive fixture: CLASS vs FEED (standard, complex, ≤ 60 s; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
