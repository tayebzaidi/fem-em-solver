# FEM-EM Solver — status

**Updated:** 2026-08-16, 10:30 review. Second fully-productive interval in
a row: all four implementer slots landed (`PORT-5` step 1, `ANS-3`,
`GEO-15` step 1, `PORT-10`), all four audited §4-compliant, two chunks
closed, and the birdcage-port path is now fully scoped — `PORT-9` heads
the queue. Source of truth is `PROJECT_PLAN.md`; this page is a read-only
digest for the human operator.

## Waiting on you

0. 🟢→**NEW: the `ANS-3` AED run is unblocked.** The FEM half landed this
   morning (131 s, all gates green, records reproduced to ≤ 3.7e-06).
   Your half: replicate
   `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md` in
   Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`. It is also the **independent adjudication input for
   `PORT-10`'s composition result** — worth doing before birdcage-port
   numbers start being quoted against the additive ladder.
1. 🔴 **The weekly review still hasn't run** (01:30 slot died on the
   session limit; third review-slot credit death that week). Its
   remaining scope: §10's dated assessments (still 2026-08-09 vintage —
   the "ports on the birdcage ≈ 08-19…26" pace number is now actionable
   since `PORT-9` is queued) and the examples/ health check. Run the
   weekly protocol interactively or let the 08-23 slot take it.
2. **Two operator decisions the automation cannot make** (unchanged):
   (a) **`OPS-16` unblock** — retry-on-529 is designed but
   `Edit(scripts/automation/**)` is under `ask`; move the three launcher
   files to `allow` or apply by hand (mind the `.gitignore` bare-`lib/`
   trap). (b) **Outage visibility** — nothing records a *missing* run.
3. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
4. **ANS-1 Ansys replication** — still yours; ANS-3 (item 0) is the
   second case in the same queue.
5. Housekeeping: local `main` is **73 commits ahead** of `origin/main`
   (last push 2026-08-10) — push when convenient.

## Honest current state (digest of §2 — one row moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; < 5% wire field reached (MAG-13, 3.74% at 1.5 M cells) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power to 3.63% (TH-10) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.88% (MAT-6); TH-11 step 2 attributed most of the 64 MHz deviation to mesh (+2.81% at 2.5 cells/δ); step 3 (30 MHz) queued |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus fixture only. **Both `PORT-9` prerequisites executed and closed today**: `PORT-10` — the two systematics compose additively (cross-term −0.0604 pp inside ±0.5 pp); `GEO-15` — graded conductor sizing reaches 0.967 of CAD mass (PORT-9 budgets from 98 k cells). `PORT-9` (lumped-element port BC) is now fully scoped incl. its birdcage gate (reciprocity + passivity + C4 circulant symmetry of Z) and heads the queue; §2.2's "no coil has ports" stands until it gates |

## Recent activity (2026-08-16 03:00 → 10:30)

Four completions in four consecutive slots, all audited COMPLIANT:

- **PORT-5 step 1 ✅ (chunk stays 🧪)** — sweep-level sanity metrics gate
  on the field route for the first time: σ_max matches the gated ‖S‖₂ to
  1.97e-07, reciprocity to 9e-11, warning-free; heuristic negative
  control separated by 0.139. A mis-transcribed §9 constant was
  corrected with its measurement (audit confirmed: control-premise fix,
  discriminating bound untouched).
- **ANS-3 ✅** — the two-torus 2-port AED benchmark's runnable half:
  `metrics.json` / `COMPARISON.md` (AED columns blank for you) / XDMF;
  records reproduced to ≤ 3.7e-06; raw rung asserted to *fail* the 10%
  band as the negative control. Incidental fix: `run_examples.sh` got
  the `timeout -k 30` treatment (last bare-TERM compute path retired).
- **GEO-15 → chunk closed ✅** — the 0.7091 question answered: 4.22% was
  the analytic sum double-counting junctions, the rest resolution;
  graded sizing (Distance→Threshold field) recovers 0.967 of CAD mass at
  2× cells / 2.8× mesh time, GEO-9 identities unmoved. Closed by this
  review; one latent rank-safety hazard in the ladder test filed in
  known-issues (has not fired).
- **PORT-10 ✅** — 2×2 factorial: the two PORT-1 systematics compose
  additively — cross-term −0.0604 pp inside the pre-stated ±0.5 pp by
  8.3×; both negative controls executed in-run; cost-probe-first honored.

## Automation health

- **Implementer grid: 4/4 slots productive**, tree clean at every
  handoff, no `attempt/*` or `recovered/*` branches. Both review slots
  since (03:00, 10:30) ran normally; the credit ceiling remains the
  grid's top risk (weekly slot, item 1 above).
- **Doc-reference checker signal is degraded**: 24 pre-existing stale
  artifacts force exit 1 on every run, so two chunks had to journal red
  logs as known-benign in one day. `OPS-19` commissioned this review to
  split the exit code (queue item 4); an artifact-refresh run was
  rejected as a treadmill.
- Standing weekly-review items, rolled to whichever weekly runs next:
  §10 dated assessments + pace ledger (two weeks stale), examples/
  health check, MAG-13 CG1 gate adoption, MAT-6 step 10's ≥ 5.1× solve
  anomaly, POST-4 export adoption (pending your ParaView check),
  ANS-1/ANS-3 adjudication when AED numbers land.

## On deck (§9, restocked this review; items 1–5 independent, 6 serial)

1. **PORT-9 step 1** — lumped-port formulation on the two-torus fixture
   (Jin ch. 11); lumped Z printed beside the gated gap-voltage route.
2. **TH-11 step 3** — 30 MHz mid-transition point.
3. **EX-21** — graded birdcage conductor mesh example (first birdcage
   example of any kind; GEO-15's capability in ParaView).
4. **OPS-19** — docrefs exit-code split (restore the checker's signal).
5. **OPS-17 step 1** — finiteness-only test inventory (no solves).
6. *(spare, depends on item 1)* **PORT-9 step 2** — cross-route identity
   gate.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
