# FEM-EM Solver — status

**Updated:** 2026-08-09, 18:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. **NEW — the first Ansys benchmark is ready to replicate in AED.**
   `ANS-1` closed this interval: the case at
   `examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/` solves the
   loop-over-lossy-slab at 10 MHz and pins itself to the `MAT-6` gate
   (ΔR = +0.32770 Ω, **1.5834%** from the Dodd–Deeds closed form; 1.4e-08
   from the gate's pin). `SPEC.md` box 1 is checked; the next two boxes
   are yours: build the case in AED per `SPEC.md`, export the same
   quantities, and fill the blank AED columns in `COMPARISON.md` — the
   weekly review then adjudicates. Two things to know before comparing:
   ΔX is **reported, never gated** (unconverged in box size — that
   disagreement is *why* the case was commissioned), and our
   Re Z(σ = 0) is exactly 0.0 by structure (real operator, real drive);
   AED's will not be, since the AED coil carries body loss unless eddy
   effects are disabled in the coil, which `SPEC.md` §Excitation
   specifies.
2. **One-line decision needed — the 16 G → 64 G memory-cap raise is
   blocked on permissions, not physics.** Unchanged since 2026-08-09
   03:00. `Edit(docker/**)` sits under `permissions.ask`, which a
   headless run reads as denial. Smallest-first routes: **(a)** make the
   edit yourself (`deploy.resources.limits.memory: 16G → 64G`, then
   `docker compose -f docker/docker-compose.yml up -d`); **(b)**
   narrow-allow just that file; **(c)** move `Edit(docker/**)` to
   `allow`. Until then `MAT-6` step 7 stays 🚫.
3. **Host-side observables needed for the `MAG-13` kill.** Unchanged
   since 10:30: both death phases reproduce clean on demand, so the kill
   is non-deterministic and host-side; sessions cannot see
   **`dmesg -T` / `journalctl -k` around 2026-08-08 20:15Z and
   2026-08-09 00:33Z**, WSL2 `vmmem` reclaim, or any host supervisor
   reaping process trees. Anything you can paste unblocks the step-2
   solve.
4. Local `main` will be **36 commits ahead** of `origin/main` once this
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

No gate moved this interval — the table is unchanged. What did move:
the `MAG-6` B-field gate now solves in its validated gauge regime
(metrics within 0.008% of prediction, bounds untouched), eigen-analysis
became a runnable example (`./run_examples.sh -e th:2`), and the first
commissioned AED benchmark is delivered on our side (Waiting-on-you 1).

## Recent activity (since the 10:30 review)

**Four of four slots ✅ — the second consecutive clean interval, and the
first in which every slot closed its item outright.**

- **MAG-6 step 5 ✅ (12:00)** — the coil+phantom B-field gate re-pointed
  at the validated gauge floor (`gauge_penalty 1e-3 → 1.0`, one
  argument): centerline 0.250414, mirror 0.311170, each within 0.008% of
  step 4's predictions, rank spread ≤ 0.024%, both bounds untouched.
  Finding filed for review: eight other sub-floor call sites, none a
  physics gate; the one that mattered (`examples/mri/01`) is now `EX-13`,
  queued.
- **ANS-1 ✅ (13:30)** — see Waiting-on-you 1. σ = 0 control exactly
  0.0 W / 0.0 A/m²; energy identity ratio 1.0000; 70 s.
- **EX-5 ✅ (15:00)** — PEC cavity resonances as the first eigenproblem
  example (`th:2`): all four modes at the 0.5% ceiling (worst 0.0436%),
  and the exported mode verified against the reported eigenvalue by
  Rayleigh quotient to 3.5e-15 — ParaView colours the asserted mode, not
  a look-alike. `TH-9` re-ran green against the one additive kwarg.
- **EX-12 ✅ (16:30)** — examples hygiene, gated by a new doc-reference
  checker (16 references, 7 guides; negative control flags 5, exit 1),
  which also found the straight-wire VTX/`.bp` export has *never* worked
  (known-issues entry; repair queued as `EX-14`).

Audit: all four flipped chunks verified against §4 — harness logs,
quantitative assertions, elapsed times, no bound loosened. **No
demotions.** One caveat (the checker's freshness branch is untested)
folded into `EX-14`. One plan correction: `EX-9`'s scoped fixture did not
exist; its §7 bullet now names the real one.

## Automation health

- **Slot yield this interval: 4/4, all ✅** — 8/8 across the day's two
  intervals. Tree clean at review end, no `recovered/*`; both
  `attempt/PORT-1-*` branches stay parked under the weekly licence — the
  **weekly review (2026-08-16) holds the 3b-xv adjudication and the
  second discriminator slot**, and also owes the next AED benchmark
  commission now that §5.4's table is fully delivered on our side.
- Both standing Waiting-on-you blockers remain reliability items, not
  physics; the new top item is the first operator-side *physics* task
  (AED replication).
- Queue depth **6** after refresh (four consumed; `EX-13`/`EX-14`
  created, `EX-10` promoted from backlog).

## On deck (§9, refreshed this review)

1. **EX-6** (standard) — the TH-8 sphere: solved (not imposed) material
   contrast vs the quasi-static closed form.
2. **EX-7** (standard) — evanescent TE₁₀ waveguide decay vs closed form
   (γ to 0.006% on record).
3. **EX-8** (standard) — the resonance guard firing at 1.45% detuning,
   pole-law energy rise within 10%.
4. **EX-13** (standard) — `examples/mri/01` to the validated gauge
   floor; rank spread measured floor vs sub-floor.
5. **EX-10** (standard) — penalty vs Lagrange-multiplier gauge
   cross-check as an example.
6. *(spare)* **EX-14** (standard) — straight-wire VTX export repair +
   the checker's freshness branch exercised.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
