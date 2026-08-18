# FEM-EM Solver — status

**Updated:** 2026-08-18, 18:00 review. Headline: **the degree-2 coil
measurement landed, and it settles the 64 MHz question for this box** —
degree 2 walks the coarse coil mesh's ΔR essentially to the h→0 answer
(−0.85% vs the [−2.15, −0.91]% bracket, from +1.58% at degree 1), but at
**61.9 GiB (96.8% of the memory cap)** it hits the same wall that closed
the degree-1 ladder. Adjudicated this review: **no affordable route to a
gated 64 MHz h→0 bracket exists on this box at any (order, mesh) pair**;
Larmor coil loading stays an extrapolation, now with the strongest
corroborating evidence yet from the order axis. Second close: the
wrong-sign Poynting flux is **h-independent — it is the source or the
assembly, not the mesh** (POST-5 step 1), and the scalar-σ raise is
fixed. One real defect en route: the complex-power identity stops
discriminating at degree 2 (99.6% spurious electric energy; the ΔR
reading survives because it cancels in the difference). Source of truth
is `PROJECT_PLAN.md`; this page is a read-only digest for the human
operator.

## Waiting on you

0. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. Still relevant: step 2c measured **0.23 pp of drive
   dependence** between the impressed-gap and lumped-sheet drives — an
   AED lumped port is a direct external check on both.
1. **Two operator decisions the automation cannot make — and (a) just
   cost a slot**: (a) **`OPS-16` unblock** — the 12:00 implementer slot
   today was lost to an **API 529 at launch** (one line in
   `logs/automation/20260818T170002Z_implementer.log`, no session ever
   started) — exactly the failure retry-on-529 was designed for.
   `Edit(scripts/automation/**)` is under `ask`; move the three launcher
   files to `allow` or apply by hand (mind the `.gitignore` bare-`lib/`
   trap). (b) **Outage visibility** — nothing records a *missing* run;
   today's was caught only because the review counts slots.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
4. Housekeeping: local `main` is **117 commits ahead** of `origin/main`
   (last push 2026-08-10) — push when convenient.
5. FYI, memory headroom on future degree-2 coil runs is ~2 GiB: the
   61.9 GiB solve ran at 96.8% of the cgroup cap. Nothing to do unless
   you can raise the cap; recorded so the number doesn't surprise you.

## Honest current state (digest of §2 — one bullet moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10); degree-2 N1curl gated on the same fixture at 0.1405% (TH-12 step 1) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6). **Moved this interval:** the degree-2 axis is now measured too (TH-12 step 2, audited) — ΔR −0.8508% on the unrefined coil mesh, h→0 quality, but at 61.94 GiB = 96.8% of the cap. **Adjudicated: no affordable (order, h) route to a gated 64 MHz bracket on this box** — a gated bracket now needs more memory or an out-of-core/iterative solver path, neither scoped. Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil. The wrong-sign Poynting flux is now **attributed to source/assembly, not resolution** (POST-5 step 1: imbalance h-independent at rate 0.029 vs ≥ 0.7, sign never corrects); the closed-drive discriminator is queued (item 3) |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only; PORT-9 step 2c reciprocal at 2.6e-11, lumped readings carry 0.23 pp drive dependence (quoted with drive stated). **Step 3 — birdcage ports at f = 0.5 — is the lineage front**, fully scoped in §7. §2.2's "no coil has ports" stands until it runs |

## Recent activity (2026-08-18 10:30 → 18:00)

- **TH-12 step 2 ✅ (13:30 + 15:00 slots, audited COMPLIANT)** — the
  13:30 slot refused to trust a guessed memory exponent whose two ends
  straddled the go/no-go threshold, and measured it instead (p = 1.271
  on the TH-11 rung pair); the 15:00 slot then ran the 882 296-DOF
  degree-2 solve: ΔR deviation −0.8508% (a −2.434 pp move off degree 1
  on the identical mesh, landing 0.054 pp past the h→0 bracket's upper
  edge), all controls green. The cost model was optimistic in both
  axes: 61.94 GiB actual vs 48.04 projected (the cells-axis exponent
  under-predicts the order axis) and ~20× wall vs the expected ~4×.
- **The degree-2 identity defect — found, diagnosed, left failing** —
  the complex-power identity reads 3–5e-9 vs its 1e-9 bound at degree 2
  while degree 1 sits at 8e-15 in the same process: spurious electric
  energy (`W_e` up 3.5e7×, the ungauged operator's richer second-order
  gradient null space) makes the gated quantity 99.6% non-physical. It
  cancels in loaded−free, so the ΔR reading stands. The bound was NOT
  widened; the review commissioned **TH-12 step 3** to discriminate the
  mechanism (generic to incompatible drives vs coil-feed-specific) at
  smoke cost.
- **POST-5 step 1 ✅ (16:30 slot, audited COMPLIANT)** — the scalar-σ
  raise is fixed (σ-blind control now exactly 0.0 W, asserted `== 0.0`),
  the `ds` orientation is excluded exactly (divergence-theorem ratio
  1.000000000000), and the h-ladder read the pre-registered
  SOURCE/ASSEMBLY verdict: imbalance 116.7 → 114.4% over 3.3× the
  cells, rate 0.029 vs ≥ 0.7, sign never corrects. The xfail keeps its
  25% band. Step 2 (a closed azimuthal drive — `J·n = 0`) is queued.
- **One new paid-for trap** appended to the protocol list: an unpinned
  `SpatialCoordinate` facet integral on a gmsh mesh can stall FFCx
  \>9 min and poison its cache entry on kill (burned two windows;
  `quadrature_degree` pin fixes it).

## Automation health

- **3/4 slots productive, 2 closures, both audited COMPLIANT.** The
  12:00 slot was **lost at launch to an API 529** — no session started,
  no work lost, but see Waiting-on-you item 1(a): the designed retry
  would have saved it.
- Container healthy all interval: no OOM, no wedge, no force-recreate —
  though the degree-2 solve peaked at 96.8% of the memory cap (~2 GiB
  headroom); the 20% guard fraction is what kept the slot safe.
- Tree clean at every handoff; no `attempt/*` or `recovered/*` branches.
- FFCx cache warm through the smoke-fixture and degree-2 coil forms;
  the azimuthal-drive and degree-2 smoke/sphere energy forms are cold
  (annotated per queue item).
- Standing weekly-review items unchanged: POST-4 export adoption (your
  ParaView check), ANS-1/ANS-3 adjudication, and now the TH-12
  production-order decision clause (waits on step 3's mechanism
  reading).

## On deck (§9, restocked this review; item 6 is the spare)

1. **EX-24** — the lumped-sheet port example, width ladder + the
   sweep-route leg (records imported from the tests, none restated).
2. **OPS-17 leg (b2)** — complex validation: the 448 s impedance test
   alone, then a cost-probe of the rest; validation forms are cold —
   first command pays JIT.
3. **POST-5 step 2** — the closed-drive discriminator: re-drive the
   smoke fixture with a divergence-free azimuthal loop; imbalance
   collapse + sign flip ⇒ the source, persistence ⇒ the assembly.
4. **OPS-20** — the `ComplexComparisonError` disposition: one
   `--tb=long` cold-cache command, then fix or `@real_only`; real-mode
   record re-asserted unmoved either way.
5. **EX-25** — degree-2 sphere example: both orders side by side
   through the example path, records inside a 1% drift band.
6. *(spare)* **TH-12 step 3** — is the degree-2 spurious-energy
   explosion generic to incompatible drives or coil-feed-specific?
   Smoke + sphere fixtures at both orders, smoke cost.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
