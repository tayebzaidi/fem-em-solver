# FEM-EM Solver — status

**Updated:** 2026-08-09, 03:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. **One-line decision needed — the 16 G → 64 G memory-cap raise is
   blocked on permissions, not physics.** The implementer run that was to
   edit `docker/docker-compose.yml` cannot: `Edit(docker/**)` sits under
   `permissions.ask` in `.claude/settings.json`, and an `ask` rule in a
   headless run is a denial. Three routes, smallest first: **(a)** make the
   one-line edit yourself (`deploy.resources.limits.memory: 16G → 64G`,
   then `docker compose -f docker/docker-compose.yml up -d`) and the next
   review re-queues the measurement; **(b)** narrow-allow just that file;
   **(c)** move `Edit(docker/**)` to `allow` (widest — hands scheduled runs
   shared infrastructure). Until one happens, `MAT-6` step 7 stays 🚫 and
   the additivity measurement stays open. The 16 G cap is confirmed at the
   kernel (`/sys/fs/cgroup/memory.max = 17179869184`).
2. **FYI, reliability — the unexplained harness kill struck twice** (same
   command, ~660 s then ~99 s in, no exit record, no OOM signature; the
   container never restarted, so the kill is host-side, outside Docker).
   A diagnostic slot is queued (item 3) that runs a stage that has already
   completed once; if *that* also dies, the next review will ask you for
   host-side observables (dmesg/journalctl, WSL2 memory reclaim) that
   sessions cannot see from inside the container.
3. Local `main` is now ~25 commits ahead of `origin/main` — a push
   whenever convenient still triggers the first-ever GitHub-runner
   execution of `validation-complex`. First Ansys benchmark case is
   commissioned (`examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/`,
   SPEC.md committed) but its runnable half (`ANS-1`) has not been built
   yet — nothing to replicate in AED until it closes.
4. FYI, no action needed: the `lint` CI job stays red-by-adjudication
   (reformat deferred until the PORT-1 branch lands).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); operator exact at 1 g/10 g (step 3); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 18:00 review)

Zero of four slots produced chunk work — one permission block, one
harness death, and the two-slot containment of the resulting dirty tree —
but the interval still ended with a real finding:

- **MAG-6 step 4 ✅ (completed, and its first pass reversed)** — the
  suspected "rank-safety defect on the DG0 evaluation path" was a **√3 bug
  in the diagnostic probe itself** (`Function.eval` squeezes its return
  for a single claimed point; the probe broadcast a scalar into three
  components — measured as 1.7320508 to 8 digits at both affected points).
  The production evaluation path is immune by construction; nothing under
  `src/` was ever wrong. With the probe fixed, the gate's centerline
  metric is rank-stable to **0.341%** across `-n 1/2/4` at the validated
  gauge penalty; the 88% scatter lives only at the fixture's sub-floor
  penalty setting, and re-pointing that fixture is now a queued one-line
  chunk (bounds untouched).
- **MAT-6 step 7 🚫** — blocked before any compute; see Waiting-on-you 1.
- **MAG-13 step 2 (second harness death)** — the stage-2 solve died again,
  ~99 s in, same signature as the first (truncated log, no exit block, no
  OOM). Its pre-registered escalation fired: no third solve attempt; a
  cheap MESH_ONLY discriminator is queued instead. The < 5% target remains
  unmeasured, not missed. The dirty tree the dying slot left was journaled
  (21:00), parked (22:30), and landed by this review with the branch
  deleted.
- **Weekly review (01:30)** restocked the backlog: licence granted for the
  PORT-1 endgame discriminator (gapped vs closed at matched σ, two-slot
  budget, disposition pre-registered), nine example chunks (`EX-4`…`EX-12`)
  to backfill the §5.4 ramp, and the first Ansys benchmark case (`ANS-1`).

Audit: no chunk flipped ✅ this interval (step 4 completed inside
already-✅ `MAG-6`); no demotions.

## Automation health

- **Slot yield this interval: 0/4**, all non-physics causes: one
  permissions denial (headless `ask` = deny), one host-side harness kill
  (second occurrence, now under diagnosis), and the budgeted two-slot
  dirty-tree containment, which worked exactly as designed
  (journal → park → review lands and deletes `recovered/*`). Tree clean,
  no `recovered/*` branches at review end.
- The weekly review's pace ledger names **reliability, not physics** as
  the top risk: at the measured 65% slot-completion rate, one lost day
  ≈ 7 gated items. The two Waiting-on-you items above are both
  reliability items.
- Queue depth back to **6** (from 3) — the weekly restock plus this
  review's scoping.

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-xv** (standard) — the weekly-licensed discriminator:
   gapped vs closed at fixed σ = 800; pre-decided quarter-spread bands;
   every outcome parks and reports.
2. **EX-11** (standard) — Dodd–Deeds coil loading as a runnable example
   (ΔR vs closed form, eddy currents in ParaView); feeds ANS-1.
3. **MAG-13 step 2 diag** (heavy envelope, ~200 s) — MESH_ONLY harness
   discriminator: separates the unexplained kill from the solve.
4. **EX-4** (standard) — lossy plane wave: the first time-harmonic example
   (decay/phase vs closed form).
5. **MAG-6 step 5** (standard) — re-point the gate fixture at the
   validated gauge floor; bounds untouched.
6. *(spare)* **EX-12** (smoke) — examples hygiene: stale claims, dead
   references, the 2026-02 PNG.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
