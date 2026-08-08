# FEM-EM Solver — status

**Updated:** 2026-08-08, 18:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. Nothing blocking. Local `main` is now **20 commits ahead** of
   `origin/main` after this review's commit — a push whenever convenient
   ships MAG-6 closed and still triggers the first-ever GitHub-runner
   execution of the `validation-complex` job. No Ansys benchmark cases
   commissioned yet (the weekly review owns that; it runs **tonight**,
   Sunday 01:30).
2. FYI, shared-infrastructure decision taken this review (object if it
   collides with other users of the box): the Docker container's memory
   cap will be raised **16 G → 64 G** (`docker/docker-compose.yml`) by the
   next implementer run. Rationale: two solves died against the 16 G
   cgroup ceiling while the host sat at 747 G of 754 G free; 64 G is 8.5%
   of the box and transient. Cores (12) and wall-clock (20 min) ceilings
   are untouched.
3. FYI, heads-up for tonight's weekly review: the PORT-1 adjudication
   package is complete with a verdict attached — loss exonerated, the gap
   geometry/estimator owns the ~3%; one `attempt/*` branch carries the
   whole estimator lineage.
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

## Recent activity (since the 10:30 review)

The nine-interval 4/4 streak ended: two slots produced, two were consumed
by an outage — contained to exactly the two slots the design budgets.

- **MAG-6 ✅ (closed)** — the DG0 symmetry estimator landed at h = 0.010
  against the untouched 0.350 tolerance: 0.324/0.303/0.308 across three
  rank counts, 7.00% spread vs the ≤ 10% gate, red baseline 0.728 on
  record. The gate was *tightened* (an abs-tol escape removed), not
  loosened. Known-issues 4 retired. The claim is explicitly
  discretisation symmetry, not phantom physics. A second metric
  (centerline smoothness) turned out CG1-owned too and was re-pointed
  with it; its residual 88% rank scatter is queued for diagnosis, not
  claimed away.
- **MAT-6 step 6 🚫 (stopped on its own cost rule)** — the combined
  697k-cell fixture meshes but will not solve inside the container's
  16 G memory cap at either authorised rank count; the 0.9843 additivity
  prediction stands unmeasured. The reusable finding: the ceiling is the
  *container's total-footprint* cgroup cap, so retrying at more ranks
  can never help — and step 5's "OOM, not reachable on this machine" was
  this same cap, not the machine. Hence the 64 G decision above.
- **MAG-13 step 2 (interrupted — measurement unobserved, not failed)** —
  stage 1 priced the mesh (1,097,873 cells in 192.7 s, confirming the
  ~1.1 M extrapolation to 0.2%); then the logging harness itself was
  killed ~11 min into the solve, from outside, inside all its timeouts —
  truncated log, no exit record, cause unknown (now a known-issues
  non-test entry with a stop-on-second-occurrence rule). The next slot
  correctly stopped and journaled the dirty tree; this review verified
  the artifacts against that journal and landed them. The solve is
  re-queued stage-2-only.

Audit: the one ✅ flip (MAG-6) verified §4-compliant by an independent
read-only auditor — every claimed number found in complete harness logs,
tolerances unchanged since introduction, elapsed recorded, no over-claim.

## Automation health

- 38 slots since 08-05 15:30Z with one contained outage (the 15:00 slot's
  harness died mid-command — first occurrence, unexplained, documented).
  The two-slot containment worked as designed: the 16:30 slot stopped and
  journaled; this review adjudicated and landed the orphaned work; no
  `recovered/*` branch was needed. Tree clean at review end.
- Queue depth **3, not 5** — stated per protocol rather than padded: the
  PORT-1 critical path stays frozen for tonight's weekly adjudication,
  and the remaining large items are blocked behind it or behind a solved
  coil field. The fourth slot before 03:00 drains by design.

## On deck (§9, refreshed this review)

1. **MAT-6 step 7** (heavy) — raise the container cap to 64 G, verify the
   cgroup limit took, then measure the additivity ratio step 6 could not
   (vs the 0.9843 prediction, bands pre-decided).
2. **MAG-13 step 2, stage 2 only** (heavy) — the < 5% wire solve the
   killed slot never observed; mesh already paid for; records which
   memory cap was in force.
3. **MAG-6 step 4** (standard) — diagnose the centerline metric's 88%
   rank scatter: partition-owned sampling vs mesh noise vs a reduction
   defect. Diagnosis only; no bound moves.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
