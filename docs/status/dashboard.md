# FEM-EM Solver — status

**Updated:** 2026-08-18, 10:30 review. Headline: **your TH-12 directive
paid off on its first measurement** — degree-2 elements on the Larmor
sphere read **0.1405%** interior error, 25.9× the degree-1 fine-rung
accuracy at 3× fewer cells, for 4.3× time and 2.7× memory. That matters
because the degree-1 route to a 64 MHz h→0 bracket is now **closed as a
measured negative** (the memory wall is superlinear: 0.99 M cells pegs
the 64 GiB ceiling, not just the 2.8 M rung) — TH-11 is closed, and the
coil at degree 2 (TH-12 step 2) is queued first. OPS-17's complex-mode
bookkeeping leg also closed, overturning two of its own earlier calls
and surfacing two real defects, now commissioned as chunks. Source of
truth is `PROJECT_PLAN.md`; this page is a read-only digest for the
human operator.

## Waiting on you

0. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. Still relevant: step 2c measured **0.23 pp of drive
   dependence** between the impressed-gap and lumped-sheet drives — an
   AED lumped port is a direct external check on both.
1. **Two operator decisions the automation cannot make** (unchanged):
   (a) **`OPS-16` unblock** — retry-on-529 is designed but
   `Edit(scripts/automation/**)` is under `ask`; move the three launcher
   files to `allow` or apply by hand (mind the `.gitignore` bare-`lib/`
   trap). (b) **Outage visibility** — nothing records a *missing* run.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
4. Housekeeping: local `main` is **114 commits ahead** of `origin/main`
   (last push 2026-08-10) — push when convenient.

## Honest current state (digest of §2 — two bullets moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10). **New: degree-2 N1curl gated on the same fixture** — 0.1405% relL2 on the coarse rung, power error 0.0058% (TH-12 step 1, audited) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6); 64 MHz still has **no h→0 bracket**, and the degree-1 ladder to one is now a **closed measured negative** (TH-11 ✅-closed): the wall is superlinear in cells — 0.42 M fine, **0.99 M pegs 64 GiB**, 2.8 M OOMs — so no affordable third rung exists at degree 1. The live axis is **TH-12 step 2** (the coil at degree 2, queued item 1); if it holds the sphere's accuracy-per-cell, a degree-2 rung replaces the infeasible one. Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil. The wrong-sign Poynting flux still open (POST-5 step 1, queued item 2) |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only; PORT-9 step 2c reciprocal at 2.6e-11, lumped readings carry 0.23 pp drive dependence (quoted with drive stated). **Step 3 — birdcage ports at f = 0.5 — is the lineage front**, fully scoped in §7. §2.2's "no coil has ports" stands until it runs |

## Recent activity (2026-08-18 03:00 → 10:30)

- **TH-12 step 1 ✅ (06:00 slot, audited COMPLIANT)** — degree 2 vs
  degree 1 on the identical 5 866-cell sphere mesh in one process:
  0.1405% vs 8.15% field error, 0.0058% vs 8.39% power error; cost
  5.2× DOFs but only 4.3× wall / 2.7× memory (sublinear). The degree-1
  control reproduced its record to 0.0001 pp. Production element order
  stays a weekly-review decision, per your directive's decision clause.
- **TH-11 step 5c 🚫 → chunk closed (04:30 slot + this review)** — §7's
  own stop condition fired at 0.99 M cells (30% below the sized rung):
  the loaded solve completed with identities green but pegged
  `memory.peak` at exactly 64.00 GiB; the same-size free solve then
  spent its window in memory reclaim and timed out. Adjudicated: the
  wall is MUMPS-fill-in-superlinear, every remaining rung is either
  unaffordable or statistically useless (ratio ≈ 1.2 vs a 0.01 pp
  noise floor) — **step 5 closed as a measured negative, TH-11 closed**
  on the GEO-14 precedent (its question was answered by step 4: the
  "frequency trend" was mesh resolution). Both parked branches deleted;
  the corrected non-uniform Richardson fit is recorded as a formula in
  §7.
- **OPS-17 step 3 leg (b1) ✅ (07:30 + 09:00 slots, audited COMPLIANT)**
  — every non-validation complex test now observed in completed legs,
  counts reconciled exactly (171 = real mode's 171; 209 left for leg
  b2). Two of the lineage's own prior calls overturned on evidence:
  the coil-phantom FAILED is **not** a cache artifact but a real
  complex-mode defect (`ComplexComparisonError`, masked by the
  poisoned cache), and attempt 1's ">12× real" cost rule was itself a
  cold-cache FFCx artifact — warm complex is ~2.7× real, and the new
  standing rule is **compilation and measurement never share a
  window**.
- **Two defects filed → two chunks commissioned this review**:
  `OPS-20` (localize the `ComplexComparisonError` with one `--tb=long`
  cold-cache command, then fix or mark `@real_only`; its raise also
  hangs `mpiexec` ~300 s on exit, so probes cost full windows) and
  `OPS-21` (a combined-XDMF test that hard-codes real-mode attribute
  names *and* returns different verdicts on different ranks). Plus
  `EX-25` (§5.4 ramp: first example at any element order other than 1).

## Automation health

- **4/4 slots productive, 2 closures** — and the two 🚫/🟡 outcomes were
  the designed kind: a stop condition firing exactly as §7 pre-registered
  it, and a bookkeeping leg that corrected its own prior adjudications
  with measurements.
- Container healthy all interval: one clean SIGTERM kill (the -k 30
  worked), no wedge, no force-recreate. FFCx cache deliberately left
  **warm** for the next slot (annotated in queue item 4).
- Tree clean at every handoff; no `recovered/*`; both TH-11 attempt
  branches disposed of by adjudication (deleted, content captured).
- Instrument correction now on record: container `memory.peak` is a
  lifetime high-water mark (reads 64 GiB forever after one TH-11-scale
  run) — per-run memory is summed `ru_maxrss` from here on.
- Standing weekly-review items unchanged: POST-4 export adoption (your
  ParaView check) and ANS-1/ANS-3 adjudication (no AED numbers yet).

## On deck (§9, restocked this review; all six independent, item 6 is the spare)

1. **TH-12 step 2** — the coil at degree 2, 10 MHz: MUMPS in-core
   estimate printed *before* solving (over-cap ⇒ stop, that is the
   result); ΔR printed beside the degree-1 h→0 bracket; degree-1
   record reproduced in-run as control.
2. **POST-5 step 1** — the scalar-σ one-liner + the Poynting wrong-sign
   h-ladder discriminator (`ds` orientation checked first).
3. **EX-24** — the lumped-sheet port example, width ladder + the
   sweep-route leg (records imported from the tests, none restated).
4. **OPS-17 leg (b2)** — complex validation: the 448 s impedance test
   alone, then a cost-probe of the rest; cache is warm but validation
   forms are cold — first command pays JIT.
5. **OPS-20** — the `ComplexComparisonError` disposition: one
   `--tb=long` cold-cache command, then fix or `@real_only`; real-mode
   record re-asserted unmoved either way.
6. *(spare)* **EX-25** — degree-2 sphere example: both orders side by
   side through the example path, records inside a 1% drift band.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
