# FEM-EM Solver — status

**Updated:** 2026-08-15, 18:00 review — **the first review to execute since
2026-08-13 10:30**, so this page digests a two-day interval: four landings,
two chunk closes, one blocked chunk, two outages, and twelve idle slots.
Source of truth is `PROJECT_PLAN.md`; this page is a read-only digest for
the human operator.

## Waiting on you

0. 🔴 **The Fable 5 credit question is now half-answered: this review ran.**
   The 18:00 daily review executed normally (this page is its output), so
   the review model has balance again — whether restored by you or by a
   billing-cycle reset, the loop's refill half is alive as of 18:00 local.
   The queue is restocked to six items; the 19:30 implementer slot is the
   first in twelve with real work. **Watch the 2026-08-16 01:30 weekly
   planning review** — same model; if it produces another 98-byte log the
   balance is marginal rather than restored. For the record, the two
   failure modes in the log archive are told apart by size: **98-byte log
   = no credits; absent log = host off** (the box was off ~23.8 h,
   2026-08-14 20:01Z → 2026-08-15 19:50Z — 14 sessions never ran; if this
   box sleeps, the grid stops with it).
1. **Two operator decisions the automation cannot make for itself:**
   (a) **`OPS-16` unblock** — retry-on-529 in the launchers is fully
   designed (2026-08-14T02:03Z attempts.md entry) but `.claude/settings.json`
   puts `Edit(scripts/automation/**)` under `ask`, a headless denial. Either
   move *only* the three launcher files to `allow`, or apply the change by
   hand; also note the `.gitignore` bare-`lib/` trap recorded in the §7
   entry. (b) **Outage visibility** — nothing records a *missing* run, so
   the 23.8 h gap was findable only by noticing absent files. A launcher
   "last run" heartbeat needs the same allowlist decision; until then this
   stays a known blind spot.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12). `POST-4` step 5 measured the DG1/VTX route bit-faithful
   where the current P1 path is 20–52% off pointwise. Blocked only on you
   opening a `.bp` (ADIOS2/VTX reader) and confirming it renders;
   `scripts/probes/post4_step5_probe.py` regenerates the files.
3. **ANS-1 Ansys replication** — the FEM half is complete
   (`examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/`); the AED run
   is yours. Our ΔX is genuinely unconverged, so the AED number is
   informative, not a formality.
4. Housekeeping: local `main` is **~50 commits ahead** of `origin/main`
   (`b6e994f`, 2026-08-10) — push when convenient.

## Honest current state (digest of §2 — two rows moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10); **the ~3% residual is proven resolution, not a geometry floor — GEO-14 closed ✅ this review (1.78% at the finer mesh, rate 1.77)** |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.88% (MAT-6); at 64 MHz the quasi-static deviation grows to +10.27% (TH-11 step 1) — **unattributed between physics and mesh until the resolution rung runs (queue item 1)** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4) + the Larmor power integral (TH-10); never on a coil |
| S-parameters | 🟡→✅ **package path now field-derived — PORT-1 closed ✅ this review** | `run_n_port_sparameter_sweep` reads the solved field; reciprocity 2.5e-05 vs the 1e-3 gate, ‖S‖₂ = 0.861; heuristic deprecated, kept only as a negative control. **Two-torus fixture only — no coil or birdcage has ports; that hold is the weekly review's** |

## Recent activity (2026-08-13 10:30 → now)

Four landings in four consecutive slots before the queue drained at 08-13
21:00; all audited §4-compliant this review (one subagent auditor per
landing), no demotions:

- **PORT-1 step 4 → chunk closed ✅** — the package S-parameter path reads
  the solved field and reproduces the gated record; the `excitation.py`
  heuristic is retired to a deprecated kwarg whose output is asserted to
  *differ*. §2.2 retitled; CLAUDE.md's summary corrected.
- **EX-19 ✅** — first example solving at 64/128 MHz; all four TH-10 gate
  records reproduced through the example path to 1.7e-04 drift.
- **GEO-14 step 1 → chunk closed ✅** — the pre-registered discriminator
  read RESOLUTION: 64 MHz error falls 3.64% → 1.78% at the finer mesh, so
  the shared-faceting-floor hypothesis is refuted; the wire re-aim was
  declined because MAG-13's own rung ladder already attributes its residual
  to resolution.
- **TH-11 step 1 ✅ (chunk stays 🟡)** — 64 MHz coil loading costs the same
  as 10 MHz; identities to 1e-14; the quasi-static ΔR deviation grows
  1.58% → +10.27%, deliberately unattributed until the resolution rung.
- **OPS-16 🚫** — unexecutable by any scheduled session (allowlist); see
  Waiting-on-you 1a.

## Automation health

- **Outage ledger for the interval:** three review slots died on exhausted
  Fable 5 credits (98-byte logs: 08-13 18:00, 08-14 03:00, 08-14 10:30);
  then the host was off ~23.8 h, killing 11 implementer slots and 3 more
  reviews with no log at all; **twelve implementer slots idled** on the
  drained queue between 08-13 22:31 and 08-15 16:30, every one journalled
  per the drain instruction. The 08-15 15:00 slot restarted the container
  after the reboot — the grid was mechanically green again before this
  review ran.
- **This review executed normally at 18:00** — the credit outage is over
  for the daily review at least; the weekly review (01:30 tonight) is the
  remaining test.
- Discipline held throughout: no improvised work in twelve drained slots,
  tree clean at every check, no `attempt/*` or `recovered/*` branches, and
  the idle-slot journals correctly separated the two outage causes.
- Standing weekly-review items (tonight): the two-systematics composition
  question (3b-xviii), MAG-13 CG1 gate adoption, MAT-6 step 10's ≥ 5.1×
  solve anomaly, POST-4 export adoption (pending your ParaView check), the
  birdcage-ports/B1+ hold — **plus, flagged this review: §6's Phase-4 row
  and §10's target checkboxes predate the PORT-1 close and need their
  weekly-owned refresh.**

## On deck (§9, restocked this review; six items, mutually independent)

1. **TH-11 step 2** — the resolution rung at 64 MHz (417 914 cells): bound
   the mesh term inside the +10.27% deviation before anyone calls it
   physics.
2. **Hygiene pair** — TH-10's monotonicity assert + MAG-13's exit-gate
   smoke, the two ride-alongs twelve drained slots watched sit idle.
3. **EX-18 doc repairs** — retire the docrefs known-issues entry (guide
   headings; gate on the guide pass, not exit 0).
4. **EX-20** — first example calling the package S-parameter sweep
   (§5.4 ramp for the PORT-1 close).
5. **PORT-5 step 1** — sweep-level sanity metrics on the field-route
   S-matrix (§10 target 3's named gap).
6. *(spare)* **TH-11 step 3** — 30 MHz mid-transition point.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
