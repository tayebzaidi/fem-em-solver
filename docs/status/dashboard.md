# FEM-EM Solver — status

**Updated:** 2026-08-24 03:00, **daily review (scheduled, ran normally)**.
Headline: **the port reciprocity fix is in and proven at its own
mechanism, and the 0.11 re-gate is complete.** `PORT-9` leg (d3) landed
the power-wave S assembly: on the asymmetric two-torus the fixed route's
reciprocity residual is 3e-15 while the old conversion — computed from the
same solve — reads 3e-03, a **12-orders-of-magnitude separation** against
the required 100×. `MAG-18` re-gated the magnetostatics ladder on 0.11
(all three anchors, nothing re-recorded), discharging the last upgrade
caveat: **every §2.1 family is now validated on the image `main` boots.**
The `GEO-19` local-frame mesh rewrite is written and green but parked —
landing it moves the birdcage mesh by 0.2% (measured to be ulp-level gmsh
tie-breaking, not geometry), which moves `PORT-9`'s recorded digits; this
review ruled the sequencing so each re-record has exactly one cause.
Source of truth is `PROJECT_PLAN.md`; this page is a read-only digest for
the human operator.

## Waiting on you

1. 🟡 **A geometry decision is coming your way: 32 legs do not fit
   `ring_radius = 0.07 m` with 14 mm port boxes.** The layout clearance
   floor (1.25 × box width = 17.5 mm) caps the leg count at **N ≤ 25**;
   32 legs need `ring_radius ≥ 0.0876 m` or narrower boxes. Measured by
   `GEO-19` attempt 1, recorded, not worked around. The weekly review
   owns §10 and will propose a disposition Sunday — if you have a
   preference (bigger ring vs narrower boxes vs 16 legs as the
   production count), leave it in the plan or say so.
2. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
3. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
4. **ANS-1 Ansys replication** — still yours; ANS-3 (item 2) is the
   second case in the same queue.
5. FYI: **one implementer slot (00:00) was lost to an API 529** before
   any work — the wrapper log holds the one-line error, no tree damage.
   You ruled `OPS-16` (retry-on-529) WON'T FIX on 2026-08-22; this is
   what that costs when it fires: one slot per incident. No action
   needed unless you want to revisit.
6. FYI: expect the birdcage port records to move twice in the next
   interval — once for the power-wave route (single cause, unmoved
   mesh), once when the mesh rewrite lands (single cause, mesh) — both
   licensed re-records with no band loosened. `PORT-11` (64 MHz ports)
   stays serial on `PORT-9` closing.
7. FYI: local `main` is well ahead of origin (push is manual).

## Honest current state (digest of §2 — MAG and S-parameter lines changed)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated **on 0.11** | closed forms; Helmholtz 0.04%; wire `E_Ω` = 10.62% at h = 0.0025, rate 1.6854, cross-width 4.9e-07 (`MAG-18`, re-gated 08-23 — the gate moved 7e-04 across the version change, which is what it was built to show) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power 3.63% (TH-10, reproduced on 0.11); degree-2 gated at 0.1405% (TH-12/EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6, re-gated on 0.11); no affordable 64 MHz bracket on this box (adjudicated 08-18); Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4, re-gated on 0.11); never on a coil |
| S-parameters | ✅ field-derived, **assembly fixed on the two-torus** | S now assembled from power waves on both gated routes; asymmetric-fixture reciprocity 3e-15 vs the old conversion's 3e-03 in the same run; `z_matrix` demoted to a documented terminated-transimpedance diagnostic. Birdcage class re-record is queue item 1; §2.2's "no coil has ports" stands |
| Test-suite trust | ✅ reconciled, on 0.11 | 437 collected / 0 errors both modes; `OPS-18` ✅ with its scope caveat discharged by the `MAG-18` re-gate |

## Recent activity (2026-08-23 18:00 → 2026-08-24 03:00)

- **19:30:** `MAG-18` re-gated on 0.11 — all three anchors green twice
  in-slot (rate 1.6854, cross-width 4.86e-07 ≤ 1e-6, natural-BC wall
  strictly worse at ratio 0.3285). The pre-registered re-record turned
  out unnecessary: `OPS-18` had already version-tagged the records, and
  they reproduce to 2.9e-09 of band. Last upgrade caveat discharged.
- **21:00:** `PORT-9` leg (d3) — power-wave S assembly landed on both
  gated routes with the mechanism's own in-run negative control
  (9.5e+11× separation); two gap-voltage records re-recorded
  route-tagged, bands unmoved; one journaled shortfall (consumer set
  green once in-slot, not twice).
- **22:30:** `GEO-19` step B — the local-frame sheet rewrite written and
  green twice in-slot, then **parked as designed**: the mesh moves 0.2%
  (measured to be ~5-ulp input differences amplified by gmsh
  tie-breaking — the CAD is digit-identical and every analytic identity
  exact), and on the moved mesh three `PORT-9` birdcage assertions go
  red, one of them a gate changing sense. Handed to this review.
- **00:00:** slot lost to an API 529 before any work (see Waiting-on-you
  item 5).
- **This review:** ruling (4\*) — step B adjudicated correct, the
  digit-for-digit cell-count expectation ruled unsatisfiable, sequencing
  set ((d3b) on the unmoved mesh first, then step B lands with a
  mesh-tagged re-record), and the flipped degeneracy gate's disposition
  pre-registered so no implementer makes that call in-slot. Queue
  rebuilt to five items; old §9 block archived.

## Automation health

- Four slots scheduled, **three ran, three useful outcomes**: two closes
  and one blocked attempt that measured its blocker to the ulp and
  wrote the ruling request. The fourth slot died on a server-side 529
  (WON'T FIX per operator decision). No drain, no exit 124, no wedge,
  tree clean at every handoff, no `recovered/*`.
- Branches: `attempt/PORT-9-d1-*` parked (lands with (d1′));
  `attempt/GEO-19-20260823T214500Z` parked (queue item 5's payload);
  `attempt/GEO-19-stepB-20260824T034500Z` parked (queue item 2 lands
  and deletes it).
- The queue holds **five** items — three independent, two serial with
  explicit skip instructions. Still unqueued by design: `PORT-11`
  step 1, `PORT-9` (d1′), `EX-30` (its `ports:1` gate asserts a record
  the route fix just moved; needs a licence after the re-records
  settle).

## On deck (§9 — five open items this review)

1. **`PORT-9` leg (d3b)** — birdcage class re-record on the fixed
   route, unmoved mesh (standard, complex, independent)
2. **`GEO-19` step B lands** + mesh-cause re-record and the
   pre-registered degeneracy disposition (standard, serial on item 1)
3. **`EX-29`** — fix the doc-reference checker so all 27 examples are
   freshness-gated, not 5 (smoke, independent)
4. **`GEO-20` step 1** — ring-gap ports at 4 legs (standard,
   independent)
5. **`GEO-19` step C** — the parked 16-leg gates module + first
   measured cost (heavy, serial on item 2; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
