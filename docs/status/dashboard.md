# FEM-EM Solver — status

**Updated:** 2026-08-10, 03:00 daily review. Source of truth is
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
4. Local `main` will be **42 commits ahead** of `origin/main` once this
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

No gate moved this interval. What did move: **Phase 2's example
shortfall is fully discharged** (`EX-4`…`EX-8`, 5 of 5 — every gated
time-harmonic capability now has a runnable, self-asserting example),
and the one demo that was rank-unstable now has a diagnosis and a fix
chunk (below).

## Recent activity (since the 18:00 review)

**Three of four slots ✅, and the fourth a clean negative executed in
full.**

- **EX-6 ✅ (19:30)** — dielectric sphere with the interior field
  *solved*, not imposed: 2.443% vs the 3/(ε+2) closed form at the gate's
  5% ceiling, the `TH-8` record digit for digit; interface jump asserted
  numerically (59.20× pole / 11.46× equator).
- **EX-7 ✅ (21:00)** — evanescent TE₁₀ decay below cutoff in a lossless
  medium: γ = 37.650399 Np/m, **0.006%** from the closed form, the `TH-7`
  record digit for digit; exported CG1 field re-fitted to 0.117%.
- **EX-8 ✅ (22:30)** — the resonance guard firing as an example: fires
  at implied detuning 1.454%, quiet arm silent (separation 6.267×),
  energy rise 16.505× vs the |f−f₀|⁻² pole law's 16.0×.
- **EX-13 negative, executed in full (00:00)** — the gauge-floor change
  on `examples/mri/01` moves nothing: floor rank spread **23.55%** vs the
  < 5% anchor, sub-floor 23.30% (ratio 0.99× vs the ≥ 2× discrimination
  bar). Root cause found: the demo overrides the solver's direct path
  with GMRES that **never converges** (`reason=-3` at `ksp_max_it`), and
  the time-harmonic solver ignores `gauge_penalty` entirely — the 23% is
  partition dependence of an unconverged iterate, not a gauge effect.

Audit: all three flipped chunks verified against §4 — harness logs,
quantitative assertions, elapsed times. **No demotions.** Review
decisions on `EX-13`: closed 🚫; the floor change and the re-measurement
ride the new `EX-16` (converge the demo's solve direct, then re-measure
the spread on a converged iterate).

Also this interval: the operator directive landed as `EX-15` — every
runnable example gets a same-stem step-by-step analysis guide, enforced
by the doc-reference checker; step 1 is now the top of the queue.

## Automation health

- **Slot yield this interval: 4/4 executed** (3 ✅ + 1 complete
  negative) — 12/12 across the day's three intervals. Tree clean at
  review end, no `recovered/*`; both `attempt/PORT-1-*` branches stay
  parked under the weekly licence — the **weekly review (2026-08-16)
  holds the 3b-xv adjudication and the second discriminator slot**, and
  owes the next AED benchmark commission.
- The `EX-12` doc-reference checker's freshness branch fired in four
  consecutive slots at its default 1.0 h window (examples' scratch
  artifacts age between slots); whether "checker green" is achievable
  outside the slot that ran the examples is `EX-14`'s question to
  settle.
- Queue depth **6** after refresh (`EX-15` steps 1–2 and `EX-16`
  created/queued; `EX-9` promoted from backlog).

## On deck (§9, refreshed this review)

1. **EX-15 step 1** (standard, doc-only; operator directive) — guide
   checker pass + template + the five `mesh:`/magnetostatics guides.
2. **EX-10** (standard) — penalty vs Lagrange-multiplier gauge
   cross-check as an example.
3. **EX-9** (standard, ~167 s — at the tier ceiling) — measured
   h-convergence rate as an example output.
4. **EX-14** (standard) — straight-wire VTX export repair + the
   checker's freshness branch exercised.
5. **EX-16** (standard) — converge `examples/mri/01`'s frequency-domain
   solve, land the gauge floor, re-measure the rank spread.
6. *(spare)* **EX-15 step 2** (standard, doc-only; needs item 1 landed) —
   the five `th:` guides.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
