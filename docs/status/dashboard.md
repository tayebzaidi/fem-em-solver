# FEM-EM Solver — status

**Updated:** 2026-08-24 18:00, **daily review (scheduled, ran normally)**.
Headline: **the birdcage port records now live on the image `main` boots,
the ring-gap mesh example closed first-try, and the afternoon surfaced two
pieces of 0.11 migration debt — one of them a validation gate that has
been silently dead since the merge.** The `TH-9` cavity gate and the
resonance guard have produced no number since 2026-08-23
(`core/cavity.py` was missed by the migration; nothing scheduled runs
those tests, so the tree looked green). A fix chunk is queued first-class
(`OPS-24`). Separately, this review closed the "`th:6` 3.14% drift"
mystery **from documentation** — the `TH-10` 128 MHz record was already
re-recorded 1.769% on 0.11 (2026-08-22) and the example's copy was never
updated; not a physics motion. Source of truth is `PROJECT_PLAN.md`; this
page is a read-only digest for the human operator.

## Waiting on you

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
5. FYI: local `main` is well ahead of origin (push is manual). The memory
   ceiling you raised (64 → 128 GiB, 12:41) is applied and verified;
   receipt closed, caveats recorded in §5.1 and the §10 epitaph.

## Honest current state (digest of §2 — two changes this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated on 0.11, **one dead gate** | closed forms; Helmholtz 0.04%; wire ladder re-gated 08-23; ⚠️ the PEC-cavity 0.0436% figure is **non-executing since the 0.11 merge** (`OPS-24` queued) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / **1.77%** (0.11 re-record; was 1.83%) + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; the 64 GiB "no affordable bracket" negatives are **unmeasured** since the 128 GiB raise, revival is a weekly-review call |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| S-parameters | ✅ field-derived, two-torus + birdcage gates on the fixed route | records image-tagged at 116 368 (leg (d3c), 12:00 slot); open-limit `Z₁₁` found **not mesh-converged** and retired as a record under ruling (6\*); §2.2's "no coil has ports" stands until `PORT-9` (d1′) |
| Test-suite trust | ✅ reconciled, on 0.11 | 437 collected / 0 errors both modes — but see the dead cavity gate above: collect-clean ≠ executing |

## Recent activity (2026-08-24 10:30 → 18:00)

- **12:00:** `PORT-9` leg (d3c) closed — ruling (5\*) executed exactly,
  the birdcage records re-recorded image-tagged at 116 368 cells,
  `19 passed` twice, every digit matching (d3b)'s bit-identical pair.
  One durable fact: `‖S−Sᵀ‖/‖S‖` only ever re-records as an order of
  magnitude (4.6e-15–1.2e-14 across four runs).
- **12:41 (you, interactive):** memory ceiling 64 → 128 GiB, verified in
  the running container.
- **13:30:** `GEO-19` step B attempt 2 — merge clean, invariance green
  from `main` (116 085 cells, predictions hit exactly), but the slot
  found the open-limit (1e6 Ω) `Z₁₁` moves **40.6% under a 0.24% mesh
  change** (a conditioning finding: `I₁` is a ~1e-9 A cancellation
  residual there), re-recorded nothing, parked, and asked for a ruling.
  Meanwhile every *terminated*-fixture gate improves on the new mesh
  (margin 253× → 2257×). Exemplary stop.
- **15:00:** `EX-31` closed first-try — `mesh:7`, the ring-gapped
  birdcage + the first 12-port dual-family mesh, every figure
  reproducing `GEO-20`'s log to the printed digit, records hoisted into
  the gate module. **Audited §4-COMPLIANT by this review** (footers,
  digits, and the purely-additive test diff all verified).
- **16:30:** `EX-30` leg (th) — 5 of 8 `time_harmonic` examples
  refreshed and reproducing; three reds with three distinct causes
  journaled, nothing re-recorded: the dead cavity gate (above), `th:7`'s
  lone un-migrated `interpolate(cells=)` call, and `th:6`'s stale
  128 MHz constant.
- **This review:** ruling (6\*) — open-limit column retired as a record
  (replacement, not loosening: its duties move to quantities with
  demonstrated mesh stability, all green and improved); `th:6`
  diagnosed from documentation (no run needed — the "missing"
  measurement had existed since 08-22); `OPS-24`/`OPS-25` commissioned;
  `EX-31` audited COMPLIANT; queue rebuilt to five items, three
  independent.

## Automation health

- Four slots scheduled, **four ran, four correct outcomes**: two closes,
  two measured-stopped-and-asked. Tree clean at every handoff, no
  exit 124 overruns (one exit 124 was a diagnosed MPI teardown hang
  after an assertion, container fine), no wedge, no `recovered/*`.
- The interval's standout: two implementer slots in a row hit
  unpredicted findings and both stopped at measurement instead of
  forcing a landing — the ruling-request pattern is working.
- Branches: `attempt/GEO-19-stepB-20260824T183000Z` is queue item 1's
  payload (lands, then both step-B branches delete);
  `attempt/GEO-19-20260823T214500Z` parked (item 5's payload);
  `attempt/PORT-9-d1-*` parked (lands with the re-scoped (d1′)).
- The queue holds **five** items — three independent, two serial with
  explicit skip/partial instructions. Still unqueued by design:
  `PORT-11` step 1, `PORT-9` (d1′), `GEO-20` step 2, `EX-30`'s three
  other legs.

## On deck (§9 — five open items this review)

1. **`GEO-19` step B lands under ruling (6\*)** — open-limit column
   retired, records mesh-tagged at 116 085 (standard, independent)
2. **`OPS-24`** — migrate `core/cavity.py`, turn the `TH-9` gates back
   on (standard, independent)
3. **`OPS-25`** — re-join `th:7` to its gate, hoist-and-import
   (standard, independent)
4. **`EX-30` leg (th) re-run** + the licensed `th:6` record alignment
   (heavy, serial on items 2–3)
5. **`GEO-19` step C** — the parked 16-leg gates module + first measured
   cost (heavy, serial on item 1; spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
