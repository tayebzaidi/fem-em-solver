# FEM-EM Solver — status

**Updated:** 2026-08-19, 03:00 review. Headline: **the wrong-sign
Poynting flux is now cornered — it is the boundary leg's assembly, not
the drive** (POST-5 step 2: a divergence-free closed-loop drive with
`J·n = 0` everywhere still reads 106% imbalance with the sign unmoved,
so source compatibility joins resolution and `ds` orientation as
excluded), and **the complex-suite JIT blockage is diagnosed as fixture
debt, not a solver defect** — three validation fixtures' own
`current_density` callables use `ufl.max_value`/`<=` predicates UFL
forbids on complex operands; `src/` is clean and the fix is a
~15-line mechanical change with in-repo precedent (commissioned as
OPS-22). Also closed: EX-24, the lumped-sheet port example (gate
1.8333% vs 5%, sweep reciprocal to 2.6e-11). The fired OPS-18 upgrade
trigger now has its required disposition: a **dated deferral** until
OPS-17 step 3 closes, so post-upgrade complex failures stay
attributable. Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

## Waiting on you

0. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. Still relevant: the measured **0.23 pp drive
   dependence** between impressed-gap and lumped-sheet drives — an AED
   lumped port is a direct external check on both.
1. **Two standing operator decisions** (unchanged): (a) **`OPS-16`
   unblock** — the 08-18 12:00 slot was lost to an API 529 at launch,
   exactly what retry-on-529 was designed for; `Edit(scripts/automation/**)`
   is under `ask`, so move the three launcher files to `allow` or apply
   by hand. (b) **Outage visibility** — nothing records a *missing*
   run. No new occurrence this interval (all four slots launched).
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
4. ✅ Housekeeping cleared: you pushed through `c612920` last night —
   local `main` is now only the newest few commits ahead. Thank you;
   the 08-10 backlog note is retired.
5. FYI (unchanged): memory headroom on degree-2 coil runs is ~2 GiB
   (61.9 GiB at 96.8% of the cgroup cap). The OPS-18 deferral note is
   also worth a skim if you expected the upgrade queued this week —
   the rationale is baseline attributability, with the queueing
   commitment written into the §7 entry.

## Honest current state (digest of §2 — one bullet sharpened this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10); degree-2 N1curl gated on the same fixture at 0.1405% (TH-12 step 1) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6); degree-2 axis measured (TH-12 step 2). Adjudicated 08-18: no affordable (order, h) route to a gated 64 MHz bracket on this box. Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil. **Sharpened this interval:** the wrong-sign Poynting flux is attributed past the drive — a closed `J·n = 0` loop still reads ~106% imbalance, sign unmoved (POST-5 step 2, audited), so the defect is the **boundary-leg assembly itself**; step 3 scores that leg against the TH-6 closed form by itself, with a small-denominator alternative (net flux ~6× below dissipation on this fixture) checked first |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only; PORT-9 step 2c reciprocal at 2.6e-11, now also demonstrated through the example path (EX-24: gate 1.8333% vs 5%, reciprocity 2.6e-11). **Step 3 — birdcage ports at f = 0.5 — is the lineage front**, fully scoped in §7. §2.2's "no coil has ports" stands until it runs |

## Recent activity (2026-08-18 18:00 → 2026-08-19 03:00)

- **EX-24 ✅ (19:30 slot, audited COMPLIANT)** — `ports:3` lands the
  width ladder and the sweep route on one shared mesh: f = 0.5 gate
  1.8333% vs 5% with the f = 1.0 control asserted to miss, open-limit
  identity ≤ 1.8e-15, sweep reciprocity 2.574296e-11 vs 1e-3, gap route
  asserted flat (drift 3.9e-5 — the control the tests themselves don't
  have); 239 s at `-n 2`, combined XDMF written.
- **POST-5 step 2 ✅ (00:00 slot, audited COMPLIANT)** — the
  pre-registered closed-drive discriminator read **ASSEMBLY**: both
  halves of the SOURCE band failed (imbalance 116.7% → 106.0%, sign
  never turns), axial control reproduced at `rtol=1e-6`, σ-blind
  exactly 0.0 W. Nothing loosened. One rode-along repair: step 1 had
  dropped a test's `def` line; restored, the file collects 11 again.
- **OPS-17 leg (b2), two 🟡 slots (21:00, 22:30) — two windows lost,
  one diagnosis gained.** Both batch windows died on complex-build JIT
  failures; the second slot named the cause: `ufl.max_value` / `<=`
  predicates in three fixtures' own `current_density` callables
  (ComplexComparisonError in 13 s for helmholtz; a swallowed FFCx
  root-node failure for circular_loop). `src/` has none — fixture debt,
  precedented fix, same family as OPS-20. The review commissioned
  **OPS-22** (the fix, queued first) and rescoped (b2) to per-file
  completed-run accounting so one bad file can never zero a window
  again. Coverage 39/225, 5 tests blocked until OPS-22 lands.
- **Two paid-for traps folded into the protocol list**: a 0-byte FFCx
  `.c` stub is a *live lock* (three windows over two nights) — sweep
  `find -size 0` and delete stubs only, never clear the cache
  wholesale; and the complex-hostile-predicate class above.
- **Bookkeeping settled:** the +1 collect delta flagged by the 21:00
  slot is attributed benign (POST-5 step 1 added 2 tests, dropped 1
  `def`; net expectation now 398 total / 225 validation / 173
  non-validation).

## Automation health

- **4/4 slots launched and journaled; 2 closures, both audited
  COMPLIANT; 2 slots 🟡 on the same (now-diagnosed) defect.** The 00:00
  slot correctly skipped the blocked item 2 per protocol rather than
  reinterpreting it — the queue discipline worked as designed.
- Container healthy all interval: no OOM, no wedge, no force-recreate.
- Tree clean at every handoff; no `attempt/*` or `recovered/*` branches.
- FFCx cache warm through the impedance file, azimuthal-drive smoke
  forms and subset-1 validation files; swept stub-free at last exit.
- OPS-18 (DolfinX 0.7.2 → 0.11) is **deferred, not dropped**: dated
  rationale + queueing commitment in its §7 entry; condition is OPS-17
  step 3 closing (~4–6 slots of queued tails).
- Standing weekly-review items unchanged: POST-4 export adoption (your
  ParaView check), ANS-1/ANS-3 adjudication, TH-12 production-order
  decision clause (waits on step 3's mechanism reading).

## On deck (§9, restocked this review; item 6 is the spare)

1. **OPS-22** — make the three loop-drive fixtures complex-safe
   (regularise-inside-`sqrt`, in-repo precedent); real-mode records
   asserted unmoved; unblocks 5 tests.
2. **OPS-20** — the coil-phantom `ComplexComparisonError` disposition,
   re-pointed to start at the test's own drive callable.
3. **POST-5 step 3** — score the boundary Poynting leg against the
   TH-6 closed form by itself; conditioning vs assembly, either reading
   is the finding.
4. **EX-25** — degree-2 sphere example: both orders side by side
   through the example path, records inside a 1% drift band.
5. **TH-12 step 3** — is the degree-2 spurious-energy explosion generic
   to incompatible drives or coil-feed-specific? Smoke + sphere
   fixtures, smoke cost.
6. *(spare)* **OPS-17 leg (b2), resumed** — per-file accounting,
   anchor re-based to 225 validation; batches only from fixtures
   without their own `current_density` callable until item 1 lands.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
