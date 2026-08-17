# FEM-EM Solver — status

**Updated:** 2026-08-17, 18:00 review. All four slots productive and two
capability fronts moved: **PORT-9 step 2b — the narrowed sheet holds the
5% band** (1.8333% at half width; the sheet-averaging diagnosis
confirmed by measurement), and **TH-11 step 5a — the 2.8 M-cell mesh
cache is exact and the `-n 8` rank change is bought** with a measured
+0.00002 pp control. OPS-17's full-suite reconciliation closed its
real-mode half: all 377 real-mode tests observed, every failure named.
Both ✅ audited §4-compliant. Source of truth is `PROJECT_PLAN.md`; this
page is a read-only digest for the human operator.

## Waiting on you

0. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. Newly relevant: PORT-9 step 2b confirmed the
   lumped-vs-gap difference is the sheet's transverse average and fixed
   it by narrowing the sheet (1.8333% at f = 0.5) — an AED lumped port
   (integration *line*) is now a direct external check on that
   narrowed-width convention.
1. **Two operator decisions the automation cannot make** (unchanged):
   (a) **`OPS-16` unblock** — retry-on-529 is designed but
   `Edit(scripts/automation/**)` is under `ask`; move the three launcher
   files to `allow` or apply by hand (mind the `.gitignore` bare-`lib/`
   trap). (b) **Outage visibility** — nothing records a *missing* run.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
4. Housekeeping: local `main` is **97 commits ahead** of `origin/main`
   (last push 2026-08-10) — push when convenient.

## Honest current state (digest of §2 — two bullets moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.88% (MAT-6); the frequency "trend" is attributed to mesh resolution, but 64 MHz still has **no h→0 bracket**. TH-11 5a removed both blockers on the third rung (exact XDMF cache; rank invariance +0.00002 pp vs 0.1 pp band) — **step 5b, queued item 1, runs the 64 MHz pair off the cache**. Larmor coil loading stays labeled an extrapolation until a review adjudicates the printed bracket |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil. OPS-17's wrong-sign Poynting flux still open (POST-5 step 1, queued item 4) |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only. **PORT-9 step 2's gate is closed at the narrowed definition**: the width ladder reads 7.7095 → 3.6730 → **1.8333%** at f = 0.5 against the unmoved 5% band, confirming the transverse-averaging diagnosis; a port sheet's width is now specified as `A/h` on the filtered facet set (spec, not implementation detail). Remaining before the birdcage (step 3): **step 2c** — `run_n_port_sparameter_sweep` needs a lumped-sheet route so the reciprocity leg can run. §2.2's "no coil has ports" stands |

## Recent activity (2026-08-17 10:30 → 18:00)

- **PORT-9 step 2b ✅ (chunk stays 🟡)** — the band holds at half
  width with 2.7× margin, f = 1.0 reproduces step 2's record to < 1e-4,
  and the open-limit identity held < 1e-11 per width. One finding en
  route: the first attempt read a false 14% MISS because the filtered
  sheet's bounding box overstates its ragged edge by 14–15% — the width
  convention is now `w = A/h` (mean width), asserted equal to bbox on
  the rectangular full-width rung. No band moved in either attempt.
- **TH-11 step 5a ✅** — the third-rung mesh (2 807 309 cells)
  round-trips XDMF exactly (tag counts and names preserved; 14.8 s
  read-back replaces 126–288 s of meshing) and the fine rung at `-n 8`
  reproduces the `-n 2` record 5 000× inside the pre-stated band. One
  in-slot failure (a smoke-rung gmsh timeout from an oversized wire
  resolution) was diagnosed, fixed, and journaled — not a defect.
- **OPS-17 step 3 🟡 ×2 — leg (a) closed** — all **377** real-mode
  tests are now observed in completed legs (171 + 206, exact), every
  failure a named expected one. Attempt 1 also caught a **silent
  regression**: PORT-1 step 4's `allgather` broke `_DummyComm`, failing
  an orientation test since 08-13 (filed in known-issues). Leg (b) —
  the two complex legs — is queued item 3.

## Automation health

- **4/4 slots productive** (2 closures + 2 journaled partial attempts
  that closed leg (a) between them). Both ✅ audited COMPLIANT by
  independent auditors; every plan number checked against its log.
- **The grep-pipe trap fired a third time** (attempt 2 piped a collect
  through `tail -3`, footer recorded tail's exit) — caught in-slot and
  re-run unpiped; the trap text in the rubric stands. Watch whether it
  recurs; three trips in two days may argue for a mechanical guard.
- Tree clean at every handoff; `attempt/TH-11-step5-*` deleted this
  review (step 5a landed a strict superset, verified by diff); no
  `recovered/*`.
- Standing weekly-review items unchanged: POST-4 export adoption (your
  ParaView check) and ANS-1/ANS-3 adjudication (no AED numbers yet).

## On deck (§9, restocked this review; items 1–4 independent, 5 spare)

1. **TH-11 step 5b** — the 64 MHz third-rung pair off the cached mesh
   at `-n 8`, one solve per command (~480 s each); the Aitken ladder
   printed, never gated.
2. **PORT-9 step 2c** — the lumped-sheet route in
   `run_n_port_sparameter_sweep` + the reciprocity leg
   (`‖S−Sᵀ‖/‖S‖ ≤ 1e-3`); prerequisite of the birdcage step.
3. **OPS-17 step 3 leg (b)** — the two complex legs; counts reconciled
   against 377; the th-smoke xfail finally observed in a completed run.
4. **POST-5 step 1** — the scalar-σ one-liner + the Poynting wrong-sign
   h-ladder discriminator (`ds` orientation checked first).
5. *(spare)* **EX-22** — restore the six examples' artifacts
   (stale 24 → 0; heavy).

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
