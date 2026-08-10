# FEM-EM Solver — status

**Updated:** 2026-08-10, 18:00 daily review. Source of truth is
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
2. **Host-side observables needed for the `MAG-13` kill.** Unchanged:
   both death phases reproduce clean on demand, so the kill is
   non-deterministic and host-side; sessions cannot see
   **`dmesg -T` / `journalctl -k` around 2026-08-08 20:15Z and
   2026-08-09 00:33Z**, WSL2 `vmmem` reclaim, or any host supervisor
   reaping process trees. Anything you can paste unblocks the step-2
   solve.
3. Local `main` will be **54 commits ahead** of `origin/main` once this
   review's commit lands (last push 2026-08-07). A push whenever
   convenient still triggers the first-ever GitHub-runner execution of
   `validation-complex`.
4. FYI, no action needed: the `lint` CI job stays red-by-adjudication
   (reformat deferred until the PORT-1 branch lands).

**Resolved since last interval:** the 16 G → 64 G memory-cap decision —
you made the edit interactively and the cap is verified at the kernel
(`memory.max` = 68719476736). Thank you; the blocked measurement
(`MAT-6` step 7 Part 2) is now queue item 1.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); operator exact at 1 g/10 g (step 3); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

No gate moved this interval. What did move: a long-suspected defect got a
decisive attribution — the mri demo's 23% rank instability is in the
**centerline point-evaluation path**, not the solver (the solve now
converges direct and the spread didn't budge, while a different sampler on
the same fields agrees to 0.007%). A fix chunk (`POST-4`) is scoped and
queued.

## Recent activity (since the 10:30 review)

**Four of four slots landed their item — the second consecutive sweep;
one is a decisive negative.**

- **EX-16 🚫 (12:00)** — the convergence hypothesis refuted, and that is
  the deliverable: the demo now solves direct (`preonly`/LU, `reason=4`)
  at the validated gauge floor, and the centerline rank spread stays at
  **23.5539%** (was 23.5545% unconverged — 1.0000×). The added positive
  control: the 493-point phantom-region sampler on the same fields agrees
  across ranks to **0.007326%**, 3215× tighter. Same solve, two samplers
  ⇒ the sampler owns the defect. Fix landed anyway (converged > truncated
  iterate); known-issues entry stays open, now assigned `POST-4`.
- **OPS-15 ✅ (13:30)** — the checker's freshness default 1 h → 48 h. The
  standing ~80–200 s per-slot refresh tax is retired; the branch is
  retuned, not disabled — it still flags at 72 h (shown on a backdated
  fixture) and `--max-age-s 1` still fires as the in-slot control.
- **EX-17 ✅ (15:00)** — circular-loop `.bp` export repaired (the EX-14
  port); round-trip read-back max |B| **bit-identical** (rel diff
  0.000e+00 vs 1e-10), analytic numbers unmoved digit for digit.
  Known-issues entry retired. First `-e` slot to pay zero freshness tax.
- **EX-15 step 2 ✅ (16:30)** — the five `th:` analysis guides; **12 of
  16** runnable examples now guide-checked, all numbers cited by log
  name; heading negative control re-fired and was restored byte-identical.
  Step 3 (four guides) closes the directive — queue item 2.
- **Interactive session (operator + agent, between slots)** — `MAT-6`
  step 7 Part 1 landed by hand (memory cap 16 G → 64 G, kernel-verified)
  and `MAT-6` step 8 (ΔR error budget: slab-resolution knob) scoped at
  operator direction; both measurements are queued.

Audit: all three ✅ closures verified against §4 by one auditor each —
harness logs, quantitative assertions, elapsed times. **No demotions.**
Two minor caveats recorded in the review commit (a log-list bookkeeping
omission in the OPS-15 journal; EX-15's negctl exit evidenced by sentinel
echo, restore verified host-side).

## Automation health

- **Slot yield this interval: 4/4** — second consecutive sweep. Tree
  clean at review end, no `recovered/*`; both `attempt/PORT-1-*` branches
  stay parked under the weekly licence — the **weekly review (2026-08-16)
  holds the 3b-xv adjudication and the second discriminator slot**.
- The `EX-16` negative result worked exactly as designed: the anchor
  failed, the report-and-stop clause fired, and the added positive
  control converted the failed hour into an attribution. Follow-up
  (`POST-4`) scoped this review with a diagnosis-before-fix split.
- Queue depth **5** after refresh; items 4–5 are an explicit serial pair
  (fix runs only if the diagnosis confirms), everything else independent.

## On deck (§9, refreshed this review)

1. **MAT-6 step 7 Part 2** (heavy) — the additivity measurement your cap
   raise unblocked: one `-n 4` solve of the 697 401-cell combined case,
   additivity defect vs 0.9843.
2. **EX-15 step 3** (standard, doc-only) — the last four guides; empties
   `PENDING_GUIDES` and closes the directive.
3. **MAT-6 step 8** (heavy, probe-first) — slab-resolution knob:
   attributes the remaining ~1.06% ΔR error to skin-depth resolution or
   the filamentary reference.
4. **POST-4 step 1** (standard) — diagnose the centerline sampler's rank
   dependence (claim multiplicity, cross-cell disagreement, ε-nudge
   discriminator).
5. **POST-4 step 2** (standard, only if step 1 confirms) — deterministic
   min-global-cell tie-break in `evaluate_vector_field_parallel`;
   anchor: 23.5539% → ≤ 0.1% across rank counts.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
