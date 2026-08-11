# FEM-EM Solver — status

**Updated:** 2026-08-11, 03:00 daily review. Source of truth is
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
2. **What did the GitHub runner say?** You pushed (thank you — `origin/main`
   is at the 2026-08-10 18:00 review commit), which should have triggered
   the first-ever runner execution of `validation-complex`. Sessions have
   no network access and cannot see the result; anything you can paste
   (pass/fail, log excerpt) is new information. Local `main` is 3 ahead
   again once this review's commit lands — a follow-up push whenever
   convenient.
3. **Host-side observables needed for the `MAG-13` kill.** Unchanged:
   both death phases reproduce clean on demand, so the kill is
   non-deterministic and host-side; sessions cannot see
   **`dmesg -T` / `journalctl -k` around 2026-08-08 20:15Z and
   2026-08-09 00:33Z**, WSL2 `vmmem` reclaim, or any host supervisor
   reaping process trees. Anything you can paste unblocks the step-2
   solve. (Note: last night's outage is *not* this — it is fully
   diagnosed, see below, and dmesg was checked in the process.)
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

No gate moved this interval — no chunk work landed at all (see below).

## Recent activity (since the 18:00 review)

**Three of four slots lost to one harness trap; root cause found and
fenced this review.** The 19:30, 22:30, and 00:00 slots each attempted
`MAT-6` step 7 Part 2 (the measurement your cap raise unblocked) and each
died identically: the session started the 20-minute solve as a
*background* task and ended its turn — which, in a headless scheduled
session, exits the CLI and kills the run. Footerless log, no journal
entry, dirty tree; the 21:00 slot stopped correctly on the dirt, per
protocol. Ruled out with evidence: not OOM (no memcg kill in dmesg since
the old 16 G records), not the 65-minute backstop (every session exited 0
within five minutes), not the cap (64 G verified in all three preflights).

What the night still bought: the 64 G cap holds at the kernel, the
697 401-cell combined mesh reproduced byte-identically three more times,
and the combined-knob gate test module was drafted (landed on main,
explicitly unverified). The solve's cost at 64 G remains unmeasured.

Fixes landed this review: the trap is written into the implementer
protocol and the review rubric (harness runs go foreground, sized to
return inside the tool's 11-minute window), and queue item 1 is rescoped
so a too-slow solve returns a *recorded* cost bound (exit 124 = "solve
> 530 s") instead of a lost slot. Full forensics: attempts.md
2026-08-11T08:00Z.

## Automation health

- **Slot yield this interval: 0/4 chunk-wise; 1/4 behaved correctly**
  (21:00's stop-on-dirty-tree). Worst interval since automation started —
  but a single mechanism, now diagnosed from the wrapper logs and fenced
  in two protocol documents.
- The park-and-continue design half-worked: each slot correctly parked
  its predecessor's dirt, then died the same death itself. Both
  `recovered/*` branches are adjudicated and deleted; orphaned artifacts
  landed in their own commit; tree clean at review end.
- Both `attempt/PORT-1-*` branches stay parked under the weekly licence —
  the **weekly review (2026-08-16) holds the 3b-xv adjudication and the
  second discriminator slot**.
- Queue depth **5** after refresh; item 1 rescoped (third listing, first
  with the foreground recipe); items 4–5 remain an explicit serial pair.

## On deck (§9, refreshed this review)

1. **MAT-6 step 7 Part 2** (heavy, rescoped) — the additivity probe,
   foreground recipe: one `-n 4` solve of the 697 401-cell combined case
   in a ≤ 590 s container window; additivity defect vs 0.9843, or a
   recorded cost bound if the window is too small.
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
