# FEM-EM Solver — status

**Updated:** 2026-08-22 10:30, **daily review (scheduled, ran normally)**.
Headline: **the DolfinX upgrade went from "blocked" to "four of five gate
families green on 0.11" in four slots.** `OPS-18` step 1 (build + boot
`0.11.0.post0`) and step 2 (API migration: `418 collected / 0 errors` in
both modes, the whole migration one module) closed; step 3's re-gate has
`TH-6`, `TH-10`, `MAT-4` and `MAT-6` reproducing their records, and
`PORT-1` blocked on a one-line defect of ours that numpy 2 exposed. Nothing
on `main` has changed physics-wise — `main` still boots 0.7.2 by design
until step 3 is green. Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

## Waiting on you

**⛔ NEW, top of the queue — the `OPS-18` upgrade is stuck on two rulings,
not on any measurement** (added by the 2026-08-22 16:30 implementer slot).
§9 item 3a is now marked ⛔. Every experiment its own text named has been
run across four slots; what is owed is a *decision*, and no implementer may
make it because both options touch a recorded band:
1. **Leg 1 — may a solved-field record be re-recorded across a version
   bump?** The two-torus mesh moved 184 919 → 184 176 cells (−4.017e-03) on
   dolfinx 0.11, 24–40× the three records' misses, with every physics
   identity in the same run intact (reciprocity 3.112128e-05 inside 1e-3,
   passivity σ_max 0.8614 < 1).
2. **Leg 2 — what disposes of the `MAG` wire-field gate?** Not "loosen 15%"
   and not "fix 0.11": the 10-point radial L2 swings 34% of its own value
   under the sampler count **on 0.7.2**, and the 15% band already fails on
   0.7.2 at `n_points = 8` (15.8028%) — the gate has been passing on a
   sampler choice, not a margin. The likely honest answer is a new `MAG`
   chunk gating a sampler-independent statistic, with `OPS-18` merging
   behind it.

Until both are ruled on, `main` keeps booting 0.7.2 and `attempt/OPS-18`
stays parked. The other queue items are unaffected — the 16:30 slot fell
through and closed `PORT-9` step 3 leg (c) on `main`.

Otherwise nothing is blocked on you on the automation side this interval.
The upgrade slots hit no permission denial worth an ask (one note: `docker
image tag` is not allowlisted; the rollback used a cached rebuild from
`main`'s Dockerfile instead, which works).

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the second
   case in the same queue.
4. FYI (unchanged): degree-2 coil memory headroom ~2 GiB. Local `main` is
   well ahead of origin (push is manual; last push 08-18 night).
5. FYI, standing: the `docker-compose.yml` allow is used only for
   `environment:` keys (the `PYTHONPATH` literal — Python moved 3.10 → 3.12);
   `volumes:`, the mount and the 64 G limit are untouched, as §9 requires.
6. FYI, new: two sandbox facts the upgrade surfaced, for whenever you next
   touch permissions — `git checkout` cannot swap `docker/Dockerfile` or
   `docker-compose.yml` (they are bind-mounted by the sandbox, so a branch
   switch silently keeps the old content; slots now move them with Edit),
   and the Docker Hub tag is `v0.11.0`, not `v0.11.0.post0` (the image
   reports `0.11.0.post0`). Neither needs action from you.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field (MAG-13, 3.74%); complex build reproduces the records to the digit; MAG-17: multiplier spread is a discrete-source residual, rate 2.4476 |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power 3.63% (TH-10); degree-2 gated at 0.1405% (TH-12/EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6); no affordable 64 MHz bracket on this box (adjudicated 08-18); Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil; GEO-17's region policy (+10.7% coil recovery) is the meshing leg of the road there |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus only; the birdcage mesh has terminals and port sheets (GEO-18 ✅ 08-22) but no port has been solved on it — PORT-9 step 3 leg (c) is §9 item 4; §2.2's "no coil has ports" stands |
| Test-suite trust | ✅ reconciled | OPS-17 closed 08-21: 216/232 runnable validation tests observed in the complex build. **On 0.11 (branch only): TH-6, TH-10, MAT-4, MAT-6 reproduce; PORT-1 pending the numpy-2 fix** |

## Recent activity (2026-08-22 03:00 → 10:30)

- **04:30:** **`OPS-18` step 1 closed** — `0.11.0.post0` builds and boots in
  both modes, `-n 2`, real `3 passed, 1 skipped` / complex `4 passed`;
  negative control (`FEM_EM_REQUIRE_COMPLEX=1` in real mode) fires. New
  gate `tests/environment/test_dolfinx_version.py`. Red baseline for step 2
  banked: `124 collected / 75 errors`, 71 of them one `gmshio` import.
- **06:00:** **`OPS-18` step 2 closed in one slot** — `418 collected / 0
  errors` in both modes, reconciled to 412 + 4 + 2 with validation unmoved
  at 232. One module (`io/mesh.py`: `gmshio` → `dolfinx.io.gmsh`, six-field
  `MeshData`, 11 call sites, one shim). One new-gmsh volume drift
  (4.251e-04 relative) filed to known-issues, not fixed.
- **07:30:** step 3 attempt 1 — the pack's second wave fired under a solve
  (`petsc_options_prefix` ×7, `functionspace`, undocumented
  `interpolate(cells0=)`), fixed; `TH-6`, `TH-10`, `MAT-4` reproduce
  (128 MHz 1.826% → 1.769% *with* its cell count — a gmsh re-record, 64 MHz
  bit-identical). 108 s of compute.
- **09:00:** step 3 attempt 2 — `MAT-4` clean log, `MAT-6` re-gates (+1.3%
  on record), fourth undocumented break fixed (`create_cell_partitioner`
  needs `max_facet_to_cell_links`); **`PORT-1` blocked**: numpy 2.4.6
  renders `!r` of a numpy scalar as `np.float64(…)` inside a gmsh
  `MathEval` string → SIGABRT. Two probes separate grammar from literals;
  fix is a `float()` coercion. 224 s of compute. 0.7.2 restored.
- **This review:** steps 1–2 audited from their footers (compliant as step
  closes; chunk stays 🟡); the numpy-2 defect given its known-issues entry;
  step 3 split into §9 items 3a / 3b; `attempt/OPS-18` kept as the
  worksite (`3cbd5b5`, six logs ahead of `main`).

## Automation health

- Container Up on **0.7.2 / Python 3.10.12** (probed this review after the
  09:00 slot's restore); no OOM, no wedge, no exit 124 all interval. Tree
  clean at every handoff; no `recovered/*`.
- `attempt/OPS-18` is the sanctioned worksite and will persist until item
  3b merges it. Container round-trip each way is ~2 min (109 s build +
  14 s recreate), ~4 min fixed overhead per OPS-18 slot.
- The queue holds **four** ready items, not five — the fifth slot before
  18:00 drains by rule; the review does not invent work to fill it.
- Standing weekly-review items unchanged: `TH-12` production-order
  decision, `POST-4` export adoption, `ANS-1`/`ANS-3` adjudication.

## On deck (§9 — four open items this review)

1. **`OPS-18` step 3a** — `float()` the numpy scalars feeding gmsh
   `MathEval` + sweep `src/` for `!r` into parsers; re-gate `PORT-1`
   (reciprocity 2.5494e-05 vs 1e-3) and the real-mode `MAG`/`MAT-6` leg
2. **`OPS-18` step 3b** — §5.3 environment table, re-record the two gmsh
   drifts, confirming run, **merge to `main`** (depends on 3a)
3. **`PORT-9` step 3 leg (c)** — first port solve on the gapped birdcage:
   priced, one driven port, C4 adjacent-pair identity on one column of Z
   (0.7.2, independent of the upgrade)
4. **`EX-28`** — gapped-birdcage mesh example with terminals and port
   sheets (0.7.2, independent)

Items 1–2 are strictly serial; 3–4 run on whatever container `main` boots.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
