# FEM-EM Solver — status

**Updated:** 2026-08-26 18:00, **daily review (scheduled, ran normally)**.
Headline: **the loaded birdcage now passes its port gates at both Larmor
frequencies** — `PORT-11` closed today: the 4×4 S-matrix at 64 MHz and at
128 MHz satisfies reciprocity, passivity and C4 symmetry on imported,
unmoved bands, with frequency demonstrably the only knob (the in-run
10 MHz rung reproduces the gated record to 1e-10). At 128 MHz the phantom
crosses to displacement-dominated and the mesh still resolves the wave
(12.5 cells/λ against a pre-stated floor of 10, checked before any gate is
read). **Seven slots ran, seven landed clean, five chunks closed** — the
example corpus is fully fresh for the first time since `EX-29`, the last
example-found 0.11 gate red is disposed, and the first 16-leg and first
birdcage-S-parameter examples exist. All five closures audited §4-compliant.
What this does **not** say: nothing is compared against an external
reference at 64/128 MHz, nothing is tuned or resonant, no B1+/SAR on the
coil. Source of truth is `PROJECT_PLAN.md`; this page is a read-only digest
for the human operator.

## Waiting on you

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the
   second case in the same queue.
4. FYI, no action: **the 10:30 review and the 09:00 implementer slot did
   not run today** (host/WSL relocation — no log, no commit). The 18:00
   review ran normally and nothing was lost except the two slots; an
   interactive session bridged the drained queue in between. If the
   relocation recurs, cron on the new host is the thing to check.
5. FYI: the Sunday 08-30 weekly review now owes three decisions — the
   F-human fixture directive (unchanged), **`ANS-4` commissioning** (the
   birdcage 4-port at the Larmor frequencies is now gated physics; only
   the weekly review may commission ANS cases), and whether a 128 MHz
   resolution study is warranted (C4 spreads grow ~1.7× per Larmor step,
   still 5× inside the band). Local `main` remains well ahead of origin
   (push is manual).

## Honest current state (digest of §2 — one change this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); one sibling sampled band gets its own measurement (`MAG-20`, queued) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ **birdcage gated at 10, 64 and 128 MHz** (`PORT-11` ✅ 08-26, audited compliant) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads 0.06–0.10% vs 0.5% at each frequency; displaced-leg control breaks the gate by 100–400×; **self-consistency identities only — absolute accuracy at Larmor is `ANS-4` (weekly review)** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ⚠️ **no known gate red on `main`**; systematic census not yet run | all three example-found 0.11 reds disposed (`OPS-24`, `MAG-19`, `GEO-21`); `OPS-26` step 2 (execution census) is queue items 1–2 — the first interval with the consecutive slots it needs |

## Recent activity (2026-08-26 03:00 → 18:00)

- **04:30:** `GEO-21` step 2 — ruled coarse-graded control landed, gate
  green at unmoved bands, chunk ✅.
- **06:00:** `PORT-11` step 2 — **first Larmor-frequency port gate**, 4×4
  at 64 MHz green on the first run, displaced control breaks as required.
- **07:30 / 12:00:** `EX-30` legs (ports) and (root) — chunk ✅; corpus-wide
  census `stale=0 dead=0 guide=0` for the first time since `EX-29`; the
  one re-record licence used exactly once, on a record the gate had moved.
- **13:30:** `EX-33` ✅ — first 16-leg birdcage example, green first run.
- **15:00:** `EX-32` ✅ — first birdcage S-parameter example, green first
  run. Queue drained.
- **~16:15:** interactive session (operator instruction) queued the 128 MHz
  step after the 10:30 review failed to run.
- **16:30:** `PORT-11` step 3 — 128 MHz green on the first run, chunk ✅.
- **18:00 review:** all five closures audited compliant; §2/§10/CLAUDE.md
  brought current (four stale "PORT-11 unrun" sentences, one stale 🟡);
  `EX-34` (Larmor frequency-ladder example) and `GEO-22` (straight-wire
  resolution guard) commissioned; `OPS-26` census split into two legs
  and queued first.

## Automation health

- Seven of eight scheduled slots ran (09:00 lost with the 10:30 review to
  the host relocation); all seven landed on `main` clean — five chunk
  closes, two step closes, zero parked branches, zero wedges.
- The interactive bridge worked as designed: item 7 was appended with the
  full rubric and this review confirmed the commissioning was correct.
- Queue holds **six items**: two census legs (independent, disjoint
  directories), then `MAG-20`, `GEO-20` step 2, `EX-34`, `GEO-22` — no
  serial dependencies.

## On deck (§9 — six items this review)

1. **`OPS-26` step 2 leg (a)** — execution census, cheap test directories
   (heavy tier, fail-closed dispositions; operator directive of 08-25)
2. **`OPS-26` step 2 leg (b)** — execution census, `validation` + `ports`
   (heavy; may not finish in one slot by design — the unreached tail is
   named, not hidden)
3. **`MAG-20`** — measure-then-dispose the last sampled two-sided rate
   band (standard)
4. **`GEO-20` step 2** — 32 ring-gap ports at 16 legs under the per-class
   reading (standard)
5. **`EX-34`** — birdcage S-matrix across 10 / 64 / 128 MHz on one mesh
   (`PORT-11` ramp; standard)
6. **`GEO-22`** — bisect and guard the straight-wire coarse-resolution
   floor (spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
