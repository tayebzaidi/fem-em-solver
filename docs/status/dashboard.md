# FEM-EM Solver — status

**Updated:** 2026-08-24 10:30, **daily review (scheduled, ran normally)**.
Headline: **the birdcage now has ring-gap ports, the example-freshness
instrument is honest, and the one blocker of the morning — a 0.11-image
mesh drift under the birdcage port records — was measured to its cause by
the 04:30 slot and adjudicated by this review** (ruling (5\*): re-record
granted, image-tagged, using the slot's twice-reproduced digits). `GEO-20`
step 1 closed: all 8 ring ports green with exact closed-form identities,
and the combined leg+ring mesh is the project's first 12-port dual-family
port mesh. `EX-29` closed: the doc-reference checker now freshness-gates
every example's own output directory, and the stale census jumped 24 → 55
— the old figure was a census of 5 examples. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

0. ✅ **You raised the container memory ceiling 64 GiB → 128 GiB
   (2026-08-24, interactive session).** Applied, container recreated, and
   verified: `/sys/fs/cgroup/memory.max` reads 137438953472 = 128.0 GiB
   exactly, both dolfinx modes boot (0.11.0.post0 / py3.12.3). Host is
   754 GiB, so this is ~17% of a shared box. **Nothing owed by you** — this
   item is a receipt. *For the reviews:* four adjudicated negatives were
   measured against the old wall and are now unmeasured rather than false —
   `TH-11` step 5, `TH-12`'s degree-2 wall, `OPS-17`'s
   `coil_loading_degree2` deferral, and the §10 coil-trend epitaph. None is
   auto-reopened; §5.1 and the epitaph carry the caveat, and re-pricing any
   of them is a review call. Next review: delete this item.
1. 🟡 **A geometry decision is coming your way: 32 legs do not fit
   `ring_radius = 0.07 m` with 14 mm port boxes.** The layout clearance
   floor caps the leg count at **N ≤ 25**; 32 legs need
   `ring_radius ≥ 0.0876 m` or narrower boxes. The weekly review owns
   §10 and will propose a disposition Sunday — if you have a preference
   (bigger ring vs narrower boxes vs 16 legs as the production count),
   leave it in the plan or say so.
2. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
3. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
4. **ANS-1 Ansys replication** — still yours; ANS-3 (item 2) is the
   second case in the same queue.
5. FYI: local `main` is well ahead of origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated on 0.11 | closed forms; Helmholtz 0.04%; wire ladder re-gated 08-23 (`MAG-18`) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); no affordable 64 MHz bracket on this box; Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| S-parameters | ✅ field-derived, assembly fixed on the two-torus | power-wave S on both gated routes; birdcage gates green on the fixed route (04:30 slot), records re-record this interval under ruling (5\*); §2.2's "no coil has ports" stands until `PORT-9` (d1′) |
| Test-suite trust | ✅ reconciled, on 0.11 | 437 collected / 0 errors both modes |

## Recent activity (2026-08-24 03:00 → 10:30)

- **04:30:** `PORT-9` leg (d3b) — the three birdcage modules ran twice on
  the power-wave route and **all three gates are green** (reciprocity
  ~1e-14, ~2.5e+9× below the old conversion; σ_max 0.999993391; class
  spreads ≤ 0.0617% vs 0.5%). The slot then found the 0.11 image moved
  the mesh under the records (116 368 vs 116 416 cells), proved the
  route and tag-encoding are not the cause, **re-recorded nothing**, and
  filed the ruling request. Exemplary stop.
- **06:00:** `EX-29` closed — the doc-reference checker resolves each
  example's artifacts in that example's own `paraview_output/`; the
  stale census went **24 → 55** (32 of 58 references were exempted by a
  basename rule). Two findings: three legitimately committed artifacts
  are now pinned by path, and in-container `git` needs
  `-c safe.directory=`.
- **07:30:** `GEO-20` step 1 closed — 8 ring-gap ports at 4 legs, every
  closed-form identity exact (closure/volume/sheet 1.000000000000,
  terminal 0.974455 of `2πr²`), and the leg+ring **12-port** mesh green
  with both port families' identities holding.
- **09:00:** queue drained — items 2 and 5 were serial behind the ruling
  request, so the slot journaled and stopped, exactly as the drain
  instruction requires. Cost: one slot, as the journal predicted.
- **This review:** ruling (5\*) grants the image-tagged birdcage
  re-record (the cause is measured and the 0.10 image is gone, so
  refusal buys nothing); both closes audited §4-COMPLIANT (two recorded
  digits in `GEO-20`'s write-up corrected, nothing demoted); `EX-30`
  re-scoped to four legs from the honest census; `EX-31` (ring-gap mesh
  example) commissioned; queue rebuilt to five items.

## Automation health

- Four slots scheduled, **four ran, four correct outcomes**: two closes,
  one blocked-with-measurement, one clean drain. Tree clean at every
  handoff, no exit 124, no wedge, no `recovered/*`.
- Branches: `attempt/PORT-9-d1-*` parked (lands with (d1′));
  `attempt/GEO-19-20260823T214500Z` parked (queue item 5's payload);
  `attempt/GEO-19-stepB-20260824T034500Z` parked (queue item 2 lands
  and deletes it).
- The queue holds **five** items — three independent, two serial with
  explicit skip instructions. Still unqueued by design: `PORT-11`
  step 1, `PORT-9` (d1′), `GEO-20` step 2, `EX-30`'s three gated legs.

## On deck (§9 — five open items this review)

1. **`PORT-9` leg (d3c)** — execute ruling (5\*): the image-tagged
   birdcage re-record at 116 368 (standard, complex, independent)
2. **`GEO-19` step B lands** + mesh-cause re-record and the
   pre-registered degeneracy disposition (standard, serial on item 1)
3. **`EX-31`** — ring-gapped birdcage mesh example, 12-port dual-family
   (standard, mesh-only, independent)
4. **`EX-30` leg (th)** — refresh the `time_harmonic` stale set, doubles
   as the example layer's 0.11 re-gate (heavy, independent)
5. **`GEO-19` step C** — the parked 16-leg gates module + first measured
   cost (heavy, serial on item 2; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
