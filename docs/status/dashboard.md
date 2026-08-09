# FEM-EM Solver — status

**Updated:** 2026-08-09, 10:30 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. **One-line decision needed — the 16 G → 64 G memory-cap raise is
   blocked on permissions, not physics.** Unchanged since 03:00. The
   implementer run that was to edit `docker/docker-compose.yml` cannot:
   `Edit(docker/**)` sits under `permissions.ask` in
   `.claude/settings.json`, and an `ask` rule in a headless run is a
   denial. Three routes, smallest first: **(a)** make the one-line edit
   yourself (`deploy.resources.limits.memory: 16G → 64G`, then
   `docker compose -f docker/docker-compose.yml up -d`) and the next
   review re-queues the measurement; **(b)** narrow-allow just that file;
   **(c)** move `Edit(docker/**)` to `allow` (widest — hands scheduled
   runs shared infrastructure). Until one happens, `MAT-6` step 7 stays 🚫
   and the additivity measurement stays open. The 16 G cap is confirmed at
   the kernel (`/sys/fs/cgroup/memory.max = 17179869184`).
2. **Host-side observables needed — the harness kill is now confirmed to
   belong to no stage.** The 07:30 diagnostic ran the mesh stage that one
   of the two deaths occurred *inside*, and it reproduced digit for digit
   (1 097 873 cells, 185.7 s vs the 192.7 s record, clean exit; container
   never restarted). One death in the mesh phase, one in the solve, both
   phases clean on demand ⇒ a non-deterministic host-side kill of the
   process tree; the physics is exonerated and the in-container diagnostic
   budget is spent (three data points). What sessions cannot see:
   **`dmesg -T` / `journalctl -k` around 2026-08-08 20:15Z and 2026-08-09
   00:33Z**, WSL2 `vmmem` memory reclaim, and any host cron/session
   supervisor that could reap a long process tree. Anything you can paste
   from those unblocks the `MAG-13` step 2 solve.
3. Local `main` is now **30 commits ahead** of `origin/main` (last push
   2026-08-07) — a push whenever convenient still triggers the first-ever
   GitHub-runner execution of `validation-complex`. The first Ansys
   benchmark's runnable half (`ANS-1`) is now **queued** (its compute path
   was priced end to end by `EX-11` this interval); when it closes, this
   section will tell you the case is ready to replicate in AED.
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

Two capabilities became *runnable examples* this interval (coil loading:
`./run_examples.sh -e mat:1`; time-harmonic: `-e th:1`), each reproducing
its gate record digit for digit — demonstration, not new physics; the
table above is unchanged.

## Recent activity (since the 03:00 review)

**Four of four slots produced — the first clean interval since
2026-08-07.**

- **PORT-1 step 3b-xv (04:30) — band (mixed), and the finding is the
  answer's shape.** Holding topology fixed and moving only where σ sits
  swings the closed route's estimator by 11.4× either side of its own
  σ = 0 control: the closed route has **no σ-independent estimator**, so
  it cannot serve as the fixed endpoint the discriminator needed. All four
  corners of the σ/topology square are now measured; none is a clean
  reference. Parked per plan; the adjudication and the second licensed
  slot belong to the **weekly review** (2026-08-16), which also holds the
  run's proposed successor (loss on the driven wire only, keeping the
  reaction test region lossless).
- **EX-11 ✅ (06:00)** — Dodd–Deeds coil loading as a runnable example
  (`mat:` runner group): ΔR 1.5834% vs the closed form, every figure
  byte-matching the MAT-6 gate record, σ = 0 control at exactly 0.0 W /
  0.0 A/m², eddy-current |J| in ParaView. Audited §4-compliant.
- **MAG-13 step 2 diag ✅ (07:30)** — see Waiting-on-you 2: no stage owns
  the kill; physics exonerated; host observables are now the ask.
- **EX-4 ✅ (09:00)** — the first time-harmonic example in the repo
  (`th:` runner group): decay/phase constants to 0.0185% / 0.0593%,
  byte-matching the TH-6 gate record; the gate itself re-run green
  (6 passed) against the one additive kwarg the example needed. Audited
  §4-compliant.

Audit: both chunks that flipped ✅ (`EX-11`, `EX-4`) verified against §4 —
harness logs, closed-form assertions, exact-zero negative controls, no
bound touched. No demotions.

## Automation health

- **Slot yield this interval: 4/4** (two ✅, one complete diagnostic, one
  parked-by-plan measurement — parking on a pre-registered band is the
  plan working, not a failure). Tree clean at review end, no `recovered/*`
  branches; both `attempt/PORT-1-*` branches stay parked under the weekly
  licence.
- The reliability risk the weekly review named is now sharper: the
  unexplained kill is host-side and non-deterministic (Waiting-on-you 2),
  and both open Waiting-on-you items remain reliability items, not
  physics.
- Queue depth **5** after refresh (four consumed, three added:
  `ANS-1`, `EX-5`, spare `EX-6`).

## On deck (§9, refreshed this review)

1. **MAG-6 step 5** (standard) — re-point the gate fixture at the
   validated gauge floor (`gauge_penalty=1e-3 → 1.0`, one argument);
   bounds untouched.
2. **ANS-1** (standard) — runnable half of the first commissioned AED
   benchmark, sharing EX-11's now-priced compute path; on closure it
   lands at the top of Waiting-on-you as ready-to-replicate.
3. **EX-5** (standard) — PEC cavity resonances as an example (TH-9
   machinery; fundamental vs closed form; first eigen-analysis example).
4. **EX-12** (smoke) — examples hygiene: stale claims, dead references,
   the 2026-02 PNG.
5. *(spare)* **EX-6** (standard) — the TH-8 sphere, solved (not imposed)
   material contrast vs the quasi-static closed form.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
