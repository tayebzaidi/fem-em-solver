# FEM-EM Solver — status

**Updated:** 2026-08-10, 10:30 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. **The first Ansys benchmark is ready to replicate in AED** (unchanged
   since 2026-08-09 18:00). `ANS-1` at
   `examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/` pins itself to
   the `MAT-6` gate (ΔR = +0.32770 Ω, **1.5834%** from Dodd–Deeds).
   `SPEC.md` box 1 is checked; the next two are yours: build the case in
   AED per `SPEC.md`, fill the blank AED columns in `COMPARISON.md` — the
   weekly review then adjudicates. Reminders: ΔX is reported, never gated;
   our Re Z(σ = 0) is exactly 0.0 by structure — disable coil eddy effects
   in AED per `SPEC.md` §Excitation before comparing.
2. **One-line decision needed — the 16 G → 64 G memory-cap raise is
   blocked on permissions, not physics.** Unchanged since 2026-08-09
   03:00. `Edit(docker/**)` sits under `permissions.ask`, which a
   headless run reads as denial. Smallest-first routes: **(a)** make the
   edit yourself (`deploy.resources.limits.memory: 16G → 64G`, then
   `docker compose -f docker/docker-compose.yml up -d`); **(b)**
   narrow-allow just that file; **(c)** move `Edit(docker/**)` to
   `allow`. Until then `MAT-6` step 7 stays 🚫.
3. **Host-side observables needed for the `MAG-13` kill.** Unchanged:
   both death phases reproduce clean on demand, so the kill is
   non-deterministic and host-side; sessions cannot see
   **`dmesg -T` / `journalctl -k` around 2026-08-08 20:15Z and
   2026-08-09 00:33Z**, WSL2 `vmmem` reclaim, or any host supervisor
   reaping process trees. Anything you can paste unblocks the step-2
   solve.
4. Local `main` will be **47 commits ahead** of `origin/main` once this
   review's commit lands (last push 2026-08-07). A push whenever
   convenient still triggers the first-ever GitHub-runner execution of
   `validation-complex`.
5. FYI, no action needed: the `lint` CI job stays red-by-adjudication
   (reformat deferred until the PORT-1 branch lands).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); operator exact at 1 g/10 g (step 3); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

No gate moved this interval. What did move: **the §5.4 example backfill
is complete everywhere** — every phase with closed gates now carries its
full example quota, each example self-asserting against the gate record —
and the ParaView export path that had silently never worked in the
straight-wire example is repaired and gated by a bit-exact round trip.

## Recent activity (since the 03:00 review)

**Four of four slots ✅ — the first clean sweep on record.**

- **EX-15 step 1 ✅ (04:30)** — every runnable example now requires a
  same-stem analysis guide, mechanically enforced by the doc checker; 5
  guides landed, both negative controls fired (missing guide and missing
  heading each named exactly).
- **EX-10 ✅ (06:00)** — penalty vs Lagrange gauge cross-check as an
  example: B-field rel diff **0.0004%** vs the 5% gate ceiling, null-space
  separation 2.774e-11 vs 1e-6. First attempt, no bound moved.
- **EX-9 ✅ (07:30)** — measured h-convergence rate **1.1009**,
  reproducing the `MAG-13` record digit for digit; found that the CG1
  export costs 7.89 error points vs the solved field (vertex averaging),
  now stated in the example rather than hidden. Tier reclassified heavy.
- **EX-14 ✅ (09:00)** — straight-wire `.bp` export repaired; round-trip
  read-back max |B| **bit-identical** (rel diff 0.000e+00 vs 1e-10). The
  freshness control exposed a second checker defect (`.bp` directory
  mtime frozen at creation — a restored artifact would have read stale
  forever), fixed in the same run.

Audit: all four closures verified against §4 by one auditor each —
harness logs, quantitative assertions, elapsed times. **No demotions.**
Two caveats recorded in the review commit: EX-9's export assertion was
re-pointed after measurement refuted its ±5% allowance (judged honest
bound-setting, but the replacement is a loose catastrophic-only guard),
and EX-14's first attempt segfaulted at teardown (exit 139, recorded,
not recurring).

## Automation health

- **Slot yield this interval: 4/4 ✅** — the first interval on record
  where all four implementer runs closed their item. Tree clean at
  review end, no `recovered/*`; both `attempt/PORT-1-*` branches stay
  parked under the weekly licence — the **weekly review (2026-08-16)
  holds the 3b-xv adjudication and the second discriminator slot**.
- **The standing freshness tax is adjudicated.** The doc checker's 1.0 h
  artifact window sat below the 90-min slot grid, so three consecutive
  runs each paid an 80–200 s refresh solve. Decision: default window
  → 48 h (`OPS-15`, queued item 2); the tight window remains the
  explicit in-slot negative control. The one genuinely dead reference
  the pass ever caught was 158 h old — still 3.3× over the new limit.
- Queue depth **5** after refresh (`EX-17` and `OPS-15` scoped this
  review); one journal error corrected (a claimed Phase-3 example
  shortfall — `EX-11` in fact closed 2026-08-09).

## On deck (§9, refreshed this review)

1. **EX-16** (standard) — converge `examples/mri/01`'s frequency-domain
   solve direct, land the gauge floor, re-measure the rank spread on a
   converged iterate (< 5% anchor vs the 23.55% unconverged record).
2. **OPS-15** (smoke, doc-tooling) — checker freshness default
   1 h → 48 h; retires the standing refresh tax.
3. **EX-17** (standard) — circular-loop VTX export repair, the one-file
   port of the EX-14 diff, same bit-exact round-trip anchor.
4. **EX-15 step 2** (standard, doc-only) — the five `th:` guides, gate
   records cited digit for digit.
5. **EX-15 step 3** (standard, doc-only) — the four `mat:`/`mri:`/`ans:`
   guides; empties `PENDING_GUIDES` and closes EX-15. If EX-16 has not
   landed, the `mri:1` guide states the unconverged-solve caveat.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
