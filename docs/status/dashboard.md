# FEM-EM Solver — status

**Updated:** 2026-08-18, 03:00 review. Headline: **PORT-9 step 2c closed
the reciprocity leg** — the lumped-sheet sweep route is reciprocal at
2.6e-11 against 1e-3, and the birdcage step's last named prerequisite is
discharged. **TH-11's 2.8 M-cell rung does not fit this box**: two runs
measured a 64 GiB memory wall at both legal rank counts, so the ladder
is rescoped to a ~1.4 M rung (step 5c). Your two directives landed and
are in motion: **TH-12 (second-order elements) is scoped and queued**,
and the 32-port 1.5 T target is recorded as Phase-6's production case.
Source of truth is `PROJECT_PLAN.md`; this page is a read-only digest
for the human operator.

## Waiting on you

0. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). The
   FEM half is on record; your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. Newly relevant: step 2c measured **0.23 pp of drive
   dependence** between the impressed-gap and lumped-sheet drives at the
   same width — an AED lumped port is a direct external check on both.
1. **Two operator decisions the automation cannot make** (unchanged):
   (a) **`OPS-16` unblock** — retry-on-529 is designed but
   `Edit(scripts/automation/**)` is under `ask`; move the three launcher
   files to `allow` or apply by hand (mind the `.gitignore` bare-`lib/`
   trap). (b) **Outage visibility** — nothing records a *missing* run.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
4. Housekeeping: local `main` is **108 commits ahead** of `origin/main`
   (last push 2026-08-10) — push when convenient.

## Honest current state (digest of §2 — two bullets moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.88% (MAT-6); 64 MHz still has **no h→0 bracket**, and the third rung meant to supply one is now **measured infeasible** — 2 807 309 cells drives `memory.peak` to exactly the 64 GiB cgroup ceiling at `-n 8` and OOM-kills the container at `-n 12`. Two routes forward, both queued: **step 5c** (a ~1.4 M rung the fit's `ratio` argument already accepts) and **TH-12 degree-2 elements** (your directive — fewer cells at matched accuracy, measured not assumed). Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil. OPS-17's wrong-sign Poynting flux still open (POST-5 step 1, queued item 4) |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only. **PORT-9 step 2c closed the reciprocity leg**: the lumped-sheet route in `run_n_port_sparameter_sweep` reads `‖S−Sᵀ‖/‖S‖ = 2.574e-11` (band 1e-3, unmoved), cross-route 1.61/1.60% inside 5%, and the lumped reading carries **0.23 pp of drive dependence** — so lumped figures are quoted with the drive stated. Step 3 (birdcage ports at f = 0.5) is now unblocked on its gate (i). §2.2's "no coil has ports" stands until it runs |

## Recent activity (2026-08-17 18:00 → 2026-08-18 03:00)

- **PORT-9 step 2c ✅ (chunk stays 🟡)** — the third excitation route
  landed; reciprocity essentially exact on the symmetric fixture (so on
  the birdcage it will measure meshing asymmetry, not the BC — the C4
  spread is the discriminating gate). Audited §4-COMPLIANT; the two
  anchor legs not runnable as written are disclosed substitutions (the
  1e-4 reproduction is a different quantity under a sheet drive;
  multi-tag `GapVoltagePortSpec` is named missing functionality), no
  band widened.
- **TH-11 step 5b 🟡 ×2 — the wall is measured, and it is memory** —
  attempt 1: `-n 12` OOM-killed the container at 518 s; attempt 2:
  `-n 8` drove `memory.peak` to 64.00 GiB = `memory.max` (to four
  bytes) and timed out. Same wall, two failure modes; no rank count
  fits 2.8 M cells. Bought en route: the loaded/free two-command split
  is **exact** (fine rung reproduced to the last digit) and the mesh
  cache reads back exactly at three rank counts. Rescoped → **step 5c**
  (~1.4 M cells, queued item 1).
- **OPS-17 step 3 🟡 (attempt 3) — both complex legs exit 124** —
  complex mode is **~2.6× real mode** on the same tests (now a recorded
  sizing rule); the one scary FAILED (coil-phantom closed form) is a
  **stale FFCx-lock artifact** of the first kill, filed in known-issues,
  no chunk opened. Leg (b) rescoped → (b1) remainder + (b2) validation,
  queued items 3 and 6.
- **Interactive session mid-interval**: your two directives + the
  DolfinX 0.11 migration pack landed; OPS-18's trigger fires (target
  v0.11.0.post0). One process wobble — the interactive commit swept the
  22:30 slot's staged files and was unwound in-slot; scheduled commits
  now always use pathspecs.

## Automation health

- **4/4 slots productive** (1 closure + 3 journaled attempts that each
  produced a decisive measurement — a memory ceiling read to four
  bytes, and the complex-mode cost factor). The ✅ audited COMPLIANT.
- **Container OOM recovery worked twice as documented** (known-issues
  `up -d --force-recreate`); new process datum — under memory pressure
  a 560 s container ceiling can outrun the 660 s tool window, so
  **480 s is the standing foreground ceiling**.
- Tree clean at every handoff; `attempt/TH-11-step5b-…004000Z` deleted
  this review (attempt 2's branch is a verified strict superset; that
  branch is kept as step 5c's base). No `recovered/*`.
- The grep-pipe trap did **not** fire this interval (first clean
  interval since it was named).
- Standing weekly-review items unchanged: POST-4 export adoption (your
  ParaView check) and ANS-1/ANS-3 adjudication (no AED numbers yet).

## On deck (§9, restocked this review; items 1–5 independent, 6 spare)

1. **TH-11 step 5c** — the shrunk ~1.4 M-cell third rung end to end off
   the parked branch: cache, loaded, free + Aitken fit; `memory.peak`
   printed every command; 480 s ceilings.
2. **TH-12 step 1** — degree-2 N1curl on the sphere's coarse rung: beat
   the degree-1 fine-rung 3.643% at strictly fewer cells, or record
   that it doesn't; accuracy- and cost-per-DOF printed (your directive).
3. **OPS-17 leg (b1)** — the complex remainder in two commands, split
   at `tests/solver`; FFCx cache cleared first; finally reads the
   th-smoke xfail from a completed run.
4. **POST-5 step 1** — the scalar-σ one-liner + the Poynting wrong-sign
   h-ladder discriminator (`ds` orientation checked first).
5. **EX-24** — the lumped-sheet port example, width ladder + the new
   sweep-route leg (records imported from the tests, none restated).
6. *(spare)* **OPS-17 leg (b2)** — complex validation: the 448 s
   impedance test alone, then a cost-probe of the rest; the padding
   sibling stays deferred until priced.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
