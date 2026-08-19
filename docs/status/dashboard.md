# FEM-EM Solver — status

**Updated:** 2026-08-19, 10:30 review. Headline: **a clean-sweep
interval — four slots, four closes, all audited COMPLIANT** — and the
Poynting verdict flipped: **the boundary leg is sound after all**.
Scored alone against the TH-6 closed form it reads 4.11% vs a
pre-registered 10% band (converging at O(h)); the smoke fixture's
O(100%) imbalance is the **impressed-source term ½Re∫E·J̄dV that the
balance helper omits** — restoring it drops the residual to 16.7% / 6.0%
inside the pre-registered 25%. So yesterday's "boundary-leg assembly
defect" reading is retired; the fix (teach the helper the source term)
is scoped and queued. Also this interval: the complex-hostile fixture
debt is **fully repaired** (OPS-22 + OPS-20 — the complex build now
reproduces every affected magnetostatic record to the digit, no test
marked real-only), and EX-25 landed the first two-element-order example
(degree 2: 58× the accuracy of degree 1 on the same mesh). Source of
truth is `PROJECT_PLAN.md`; this page is a read-only digest for the
human operator.

## Waiting on you

0. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. Still relevant: the measured **0.23 pp drive
   dependence** between impressed-gap and lumped-sheet drives — an AED
   lumped port is a direct external check on both.
1. **Two standing operator decisions** (unchanged): (a) **`OPS-16`
   unblock** — `Edit(scripts/automation/**)` is under `ask`, so move the
   three launcher files to `allow` or apply the retry-on-529 patch by
   hand. (b) **Outage visibility** — nothing records a *missing* run.
   No new occurrence this interval (all four slots launched).
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
4. FYI (unchanged): memory headroom on degree-2 coil runs is ~2 GiB
   (61.9 GiB at 96.8% of the cgroup cap). Local `main` is again several
   commits ahead of origin (push is manual; last push 08-18 night).

## Honest current state (digest of §2 — one row corrected this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells); since 08-19 the complex build reproduces the same records to the digit (OPS-22/OPS-20) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10); degree-2 N1curl gated on the same fixture at 0.1405% (TH-12 step 1, now also an example — EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6); degree-2 axis measured (TH-12 step 2). Adjudicated 08-18: no affordable (order, h) route to a gated 64 MHz bracket on this box. Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil. **Corrected this interval:** the "wrong-sign Poynting flux" was never an assembly defect — the boundary leg scored alone against the TH-6 closed form is **sound** (4.11% vs 10%, O(h) at rate 0.981); the O(100%) smoke imbalance is the impressed-source term the helper omits, and the sign law the chunk assumed does not exist for a driven domain. Helper fix (POST-5 step 4) scoped and queued |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only; PORT-9 step 2c reciprocal at 2.6e-11, demonstrated through the example path (EX-24). **Step 3 — birdcage ports at f = 0.5 — is the lineage front**, fully scoped in §7. §2.2's "no coil has ports" stands until it runs |

## Recent activity (2026-08-19 03:00 → 10:30)

- **OPS-22 ✅ (04:30 slot, audited COMPLIANT)** — the three loop-drive
  fixtures are complex-safe: predicates regularised per the in-repo
  precedent, plus a second, unpredicted defect layer (complex-typed
  field arrays reaching the comparisons) fixed with a new asserted
  bound `max|Im B_z| ≤ 1e-12·max|B_z|`. Complex build: 5 passed,
  412 s, footer; real-mode digits unmoved to the last printed figure.
  No test marked real-only.
- **OPS-20 ✅ (06:00 slot, audited COMPLIANT)** — the commissioned
  `ComplexComparisonError` was already dead: the coil-phantom test
  *imports* its drive from the file OPS-22 had repaired 90 minutes
  earlier, and a free grep proved it before any window was spent. Only
  the predicted second layer remained; complex now passes the same 30%
  gate at the same 17.1233%. The entry's mandatory cold-cache clear was
  deliberately skipped — journalled and adjudicated sound.
- **POST-5 step 3 ✅ (07:30 slot, audited COMPLIANT)** — the verdict
  reversal in the headline. Both pre-registered bands held; nothing
  loosened (diff purely additive, xfail unmoved at 25%/strict). The
  honest caveat is on record: under this fixture's natural BC the
  source term equals −dissipated algebraically, so the claim is
  "the omitted term accounts for the O(100%)", not "closes to
  round-off".
- **EX-25 ✅ (09:00 slot, audited COMPLIANT)** — first example at two
  element orders: one 5 866-cell sphere mesh, degree 1 vs 2, all four
  TH-12 step-1 records reproduced inside 1%, DOFs asserted exactly,
  16 s total. Docrefs stale set verified byte-identical to EX-24's —
  no new staleness.
- **Suite-growth warning, measured twice independently:** complex
  `tests/solver` ran 111 s warm on 08-18 and now overruns a 480–540 s
  window (two exit-124s from different slots). Not a defect — cold
  forms added by recent landings — but every future batch re-prices
  first, and the smoke + balance files no longer share a window.

## Automation health

- **4/4 slots launched, 4/4 closed, 4/4 audited COMPLIANT** — the first
  clean-sweep interval since the 90-minute grid began. Queue discipline
  held: each slot took the first open item and the OPS-22 → OPS-20
  hand-off note ("expect a second layer") saved the 06:00 slot its
  cold-cache window.
- Container healthy all interval (Up 33+ h): no OOM, no wedge, no
  force-recreate. Tree clean at every handoff; no `attempt/*` or
  `recovered/*` branches.
- FFCx cache warm through the repaired fixture forms, coil-phantom,
  the step-3 facet forms and the EX-25 degree pair; swept stub-free at
  every slot's exit.
- OPS-18 (DolfinX 0.7.2 → 0.11) still deferred on its dated rationale;
  its condition — OPS-17 step 3 closing — moved materially closer this
  interval: every (b2) blocker is now discharged and the resumed leg is
  queue item 1.
- Standing weekly-review items unchanged: POST-4 export adoption (your
  ParaView check), ANS-1/ANS-3 adjudication, TH-12 production-order
  decision clause (waits on step 3's mechanism reading — queue item 2).

## On deck (§9, restocked this review; item 5 is the spare)

1. **OPS-17 leg (b2), resumed** — every blocker discharged; coverage
   re-based 39 → 44/225 from completed logs; per-file accounting;
   re-price before any `tests/solver` batch.
2. **TH-12 step 3** — is the degree-2 spurious-energy explosion generic
   to incompatible drives or coil-feed-specific? Smoke + sphere
   fixtures, smoke cost; feeds the weekly production-order decision.
3. **POST-5 step 4** — teach `poynting_power_balance` the
   impressed-source term; smoke xfail → plain gate on the three-term
   identity; TH-6 source term asserted exactly 0.0 as control.
4. **OPS-21** — scalar-type-aware, rank-deterministic combined-XDMF
   test; exact name-set identity in both builds.
5. *(spare)* **EX-22** — restore the absent example artifacts (heavy);
   retires the standing stale=24 docrefs backlog.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
