# FEM-EM Solver — status

**Updated:** 2026-08-20 18:00, **interactive session** (no review has run
since 03:00 — see below). Headline: **the implementing half of the
automation had its best day on record and the governing half failed twice.**
Eight implementer slots since the 03:00 review produced **five closes, four
of them whole chunks** — `GEO-17`, `MAG-17`, `OPS-23` and `EX-26` — plus
`GEO-18` step 1, which cuts the birdcage legs and gives the ports real
terminals (0.988616 of the π·r² closed form, identical across all four
ports to seven digits). Meanwhile the **10:30 review died on exhausted
usage credits**, a new failure class that the parked `OPS-16` retry patch
would *not* have caught, and the 18:00 review is dying the same way as this
is written. Consequence to know about: **five closes are currently
unaudited**, and the next live review is Friday 18:00. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

0. 🟡 **Fable credits exhausted — reviews are stalled until Fri 2026-08-21
   noon (acknowledged, no action wanted).** The 10:30 review died with
   `You're out of usage credits`
   (`logs/automation/20260820T153001Z_daily-review.log`); the 18:00,
   Fri 03:00 and Fri 10:30 review slots will die the same way. Logged here
   because this page is the alerting channel, not because a decision is
   open — you have already accepted the stall. **Note this is a different
   failure from item 1:** retry logic cannot recover an exhausted budget,
   and the plausible driver is the implementer grid itself consuming the
   pool the review slot then can't draw on.
1. 🔴 **`OPS-16` unblock — the review-death class it *does* fix.** The
   2026-08-19 18:00 review died at launch on an API 500 and took one
   review + three drain-fallback slots + one blocked slot with it. The
   retry design has been parked and ready since 2026-08-14 (attempts.md
   2026-08-14T02:03Z); it is blocked only by `Edit(scripts/automation/**)`
   sitting under `ask`. Options unchanged: (a) move the three launcher
   files to `allow` (keep `hooks/` gated), or (b) apply the patch by hand
   in an interactive session.
2. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. The measured **0.23 pp drive dependence** between
   impressed-gap and lumped-sheet drives makes an AED lumped port a
   direct external check on both.
3. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
4. **ANS-1 Ansys replication** — still yours; ANS-3 (item 2) is the
   second case in the same queue.
5. FYI (unchanged): memory headroom on degree-2 coil runs is ~2 GiB.
   Local `main` remains ahead of origin (push is manual; last push
   08-18 night — everything since is local only).

## Honest current state (digest of §2 — no gated capability moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells); the complex build reproduces the same records to the digit (OPS-22/OPS-20). **New:** `MAG-17` closed — the Coulomb-gauge multiplier's spread is a **discrete-source mesh residual**, converging at fitted rate 2.4476, not a defect in the constraint block |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10); degree-2 N1curl gated at 0.1405% (TH-12 step 1, also an example — EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6). Adjudicated 08-18: no affordable (order, h) route to a gated 64 MHz bracket on this box. Larmor coil loading stays an extrapolation. The degree-2 energy-identity defect is **coil-specific** (TH-12 step 3), mechanism input with the weekly review |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil. `POST-5` closed: `poynting_power_balance` scores the three-term identity at 16.7% vs the unmoved 25%. **New:** `GEO-17` closed — the region-resolution policy now actually applies (it never had), recovering **+10.7%** of coil volume; this is MAT-4's road to SAR-on-a-coil |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only; PORT-9 step 2c reciprocal at 2.6e-11 (example EX-24). Step 3 (birdcage) stays 🚫-blocked, but **the prerequisite is now half-built**: `GEO-18` step 1 gives every port a planar disk terminal, global ẑ drive, exact C4 layout. **Step 2 (the sheet mid-plane) is not yet scoped — it needs a review, so it waits for Friday.** §2.2's "no coil has ports" stands |

## Recent activity (2026-08-20 03:00 → 18:00; eight implementer slots, all fired)

- **GEO-18 step 1 ✅ (04:30)** — the fixture answer to PORT-9's double
  block. Opt-in `leg_gap_length` cuts every leg; terminal area
  2.236196e-04 m² per port = **0.988616** of the closed form, inside the
  pre-stated [0.95, 1.0]; closure and port-volume identities both
  1.000000000000; ungapped negative control bit-for-bit unchanged.
- **GEO-17 step 1 ✅, chunk closes (06:00)** — the known-issues
  hypothesis is **refuted**: per-region `setSize` was never called at all
  (`getBoundary` at default `combined=True` returns nothing for a closed
  shell), so only the length clamps ever sized the mesh. Fixed with a Min
  field over per-volume Constants: coil recovery **+10.72% / +10.79%**,
  partition identity 1.000000000000, uniform column bit-identical to record.
- **MAG-17 step 1 ✅, chunk closes (07:30)** — h-ladder 7.836781 →
  3.052022 → 1.438617, fitted rate **2.4476** vs the pre-registered ≥ 0.7:
  verdict **DISCRETE-SOURCE**. The consequence is that `OPS-17`'s old
  anchor was unphysical on any single mesh; the strict xfail is retired and
  replaced by a strictly stronger three-mesh rate gate at the *unmoved* 0.7.
- **OPS-23 ✅, chunk closes (09:00)** — the commissioned census was wrong
  **in both directions**: two of four sites were a private helper's print
  guard (not defects), and the site the commission *exempted* was real.
  Net three real sites + the helmholtz Im-bound. Red baseline: eight
  inverted predicates, messages **byte-identical across ranks**, three of
  which could not have failed on rank 1 before the fix.
- **EX-26 ✅, chunk closes (12:00)** — first example in the tree that
  audits **power** rather than a field: driven cylinder 16.7465% inside the
  unmoved 25%, the same field misread two-term asserted to **miss** it, and
  TH-6 per-leg 8.12% / 0.07%. Measured smoke, commissioned standard.
- **OPS-17 leg (b2) attempts 4–6 🟡 (13:30, 15:00, 16:30)** — coverage
  **63 → 101 of 232**, tail 129 runnable, blocked 0, and the `dodd_deeds_*`
  family **closes at 38 of 38**. The sizing rule that made it work: read
  each file's recorded rank width and elapsed time out of its own MAT-6 log
  before sizing the command — it worked first try on every command in
  attempts 5 and 6 after two windows died to exit 124 in attempt 4.

## Automation health

- **Two reviews lost in 24 h, two different mechanisms.** 08-19 18:00 =
  API 500 (the `OPS-16` class). 08-20 10:30 = **exhausted usage credits**,
  which `OPS-16` does not address. The 18:00, Fri 03:00 and Fri 10:30
  slots are expected to fail the same way; **first live review is Fri
  18:00.**
- ⚠️ **Five closes are unaudited** — `GEO-18` step 1, `GEO-17`, `MAG-17`,
  `OPS-23`, `EX-26`, plus three leg-(b2) attempts. Every one is
  self-evidenced with logs and red baselines, but none has had the
  independent subagent audit the protocol requires. Friday's review
  inherits an unusually heavy audit load.
- ⚠️ **The queue is running on one re-drawable item.** §9 items 1–5 are
  all done; only item 6 (leg (b2)) remains, and it survives by being
  re-drawn each slot. Its next block is `coil_loading_*` — 58 unpriced
  tests that include the `TH-12` memory-wall files — and there is **no
  fallback chunk** if it stalls. A flag has been added to §9 item 6 asking
  the next slot to price that family before committing a window to it.
- Container healthy all interval; no OOM, no wedge. Tree clean at every
  handoff; no `attempt/*` or `recovered/*` branches.
- `OPS-18` (DolfinX upgrade) deliberately deferred, with a written
  rationale and a binding commitment: the review that records `OPS-17`
  step 3 closed queues steps 1–3 in the same commit. Upgrading before the
  complex baseline reconciles would make migration breaks and pre-existing
  fixture debt mutually unattributable.
- Standing weekly-review items: `TH-12` production-order decision,
  `POST-4` export adoption, `ANS-1`/`ANS-3` adjudication — unchanged.

## On deck (§9 — items 1–5 consumed today; only the spare remains)

1. ~~GEO-18 step 1~~ — **done 04:30**
2. ~~GEO-17 step 1~~ — **done 06:00** (chunk closed)
3. ~~MAG-17 step 1~~ — **done 07:30** (chunk closed)
4. ~~OPS-23~~ — **done 09:00** (chunk closed)
5. ~~EX-26~~ — **done 12:00** (chunk closed)
6. *(spare, re-drawable)* **OPS-17 leg (b2) next coverage leg** — now the
   only live item. Next block is `coil_loading_*` (58 tests, unpriced,
   holds the TH-12 memory-wall files); price it before committing a window.

**Restocking needs a review**, so the queue stays this thin until Friday
evening. Highest-value items waiting for that review: **GEO-18 step 2**
(the sheet mid-plane — it unblocks `PORT-9` step 3 and the birdcage port
path), and a decision on the ~209 untriaged `if comm.rank == 0:` sites that
`OPS-23` deliberately left out of scope.

---

*Maintained by `docs/automation/daily-review.md` step 7; this interval's
refresh was done by an interactive session because no review could run. The
Waiting-on-you section above is the alerting channel — check it after each
review interval. The published artifact copy lags until an interactive
session republishes it.*
