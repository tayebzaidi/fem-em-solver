# FEM-EM Solver — status

**Updated:** 2026-08-12, 03:00 daily review. Source of truth is
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
   in AED per `SPEC.md` §Excitation before comparing. *(The production
   fixture and the SPEC stay deliberately frozen until your comparison is
   adjudicated. Nothing changes on your side.)*
2. **What did the GitHub runner say?** `origin/main` is still at the
   2026-08-10 18:00 review commit (`b6e994f`); a runner execution of
   `validation-complex` should exist by now. Sessions have no network
   access and cannot see the result; anything you can paste (pass/fail,
   log excerpt) is new information. Local `main` is **24 ahead** once this
   review's commit lands — a follow-up push whenever convenient.
3. **Your uncommitted PORT-1 adjudication was landed for you.** The 03:00
   review found the interactive session's Jin-grounded adjudication (step
   3b-xvi, decisions 1–6) sitting uncommitted in PROJECT_PLAN.md and
   committed it verbatim (`bc93f49`); 3b-xvi is now queue item 1. If any
   of it was still draft, say so and it can be amended — otherwise no
   action needed.
4. FYI, no action needed: the `lint` CI job stays red-by-adjudication;
   and a small future ask is queued — when `POST-4` step 5 runs, it will
   produce a DG1 `.bp` export whose ParaView rendering only you can
   eyeball (headless sessions cannot).

## Honest current state (digest of §2 — headline gates unmoved)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

New under the headlines: ΔX's residual is **attributed to box truncation**
(extrapolates to r∞ = 1.0023 with the dipolar 1/W³ exponent recovered
blind), ΔR carries a newly measured ~0.38 pp truncation term of its own,
and every field export that ships a Lagrange-P1 interpolant of a
Nédélec/DG source is now **measured 20–52% off pointwise** — qualitative
pictures, not data (known-issues has the table; no gate cites them).

## Recent activity (since the 18:00 review)

**Four slots: three landed, one decisive stop-rule finding.**

- **POST-4 closed** (19:30): the export-path P1 artifact is bounded —
  and the localization hypothesis **refuted** (interiors noisier than
  vertices; a DG1 target reproduces all three fields to round-off, so
  the artifact is 100% the continuity constraint). Fourth chunk closure
  of the week.
- **MAG-13 step 2 profile** (21:00): error ∝ 1/r (slope −1.069), and the
  profile is a per-cell **staircase** — curl of the lowest-order edge
  element is cell-wise constant, which also explains the ~1.1 global
  rate. *Audit demoted this step ✅ → 🧪: the probe's checks are
  print-only (exit 0 regardless). The numbers are log-faithful; a
  one-slot re-gate is queue item 2.*
- **MAT-6 step 9** (22:30): the ΔX residual is **owned by truncation** —
  three-rung trend 0.9200 → 0.9849 → 0.9960, free-exponent fit lands
  r∞ = 1.0023 at p = 3.045 without being told the 1/W³ physics.
- **MAT-6 step 10** (00:00): the composed fixture meshes (895 974 cells)
  and then **does not solve** — ≥ 1 700 s at `-n 8`, ~9× the cost for
  1.5× the cells, not memory. Rescoped as step 10a with a review
  correction: the solver is direct LU, so the run's proposed
  iteration-count probe cannot exist; MUMPS analysis statistics are the
  right instrument.

Audits: POST-4 closure and MAT-6 step 9 **compliant** (step 9's
re-pointed control reviewed and signed off — band unwidened, failing run
committed); MAG-13 profile **demoted** as above.

## Automation health

- **Slot yield: 4/4 informative** — three items landed, one stop-rule
  negative that priced its own rescope. No lost slots in three intervals.
- Two harness defects found and repaired: container-side `timeout`
  without `-k` does not stop an `mpiexec` job (all recipes now read
  `timeout -k 30 <s>`), and an overrun can wedge the container
  (recovery recipe in known-issues; the 00:00 slot left the machine
  verified clean).
- An interactive operator session adjudicated the PORT-1 lineage
  overnight (Jin-grounded); its uncommitted edit was landed by this
  review. The `attempt/MAT-6-step10-*` branch was landed and deleted;
  both `attempt/PORT-1-*` branches stay parked per the adjudication.
- Queue depth **6** after refresh; all items mutually independent.

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-xvi** (standard) — gap-region h-refinement of the
   terminal-to-terminal estimator; operator-inserted, pre-registered
   0.5 pp bands, either outcome proceeds.
2. **MAG-13 profile re-gate** (heavy) — make the map's checks bite and
   restore the demoted ✅; the old smoke log becomes the negative control.
3. **MAT-6 step 10a** (heavy) — attribute the 9× composed-fixture solve
   cost via MUMPS analysis stats; exit 124 with stats in-log is the
   measurement.
4. **MAG-13 step 2b** (heavy) — price CG1 recovery of B on the solved
   rung; may reach < 5% with no new mesh.
5. **POST-4 step 5** (standard) — price the faithful DG1/VTX export
   route; decision table for the P1-vs-DG1 call.
6. **MAG-13 rung 3** (heavy, spare) — the < 5% wire by brute force;
   exit 124 is itself the reading.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy is refreshed by interactive sessions only and may
lag this file; `docs/status/dashboard.md` on `main` is always current.*
