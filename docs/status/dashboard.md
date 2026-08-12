# FEM-EM Solver — status

**Updated:** 2026-08-12, 10:30 daily review. Source of truth is
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
   log excerpt) is new information. Local `main` is **28 ahead** once this
   review's commit lands — a follow-up push whenever convenient.
3. FYI, no action needed: the `lint` CI job stays red-by-adjudication;
   your Jin-grounded PORT-1 adjudication is now executing (step 3b-xvi
   has run twice and re-runs next slot under a review-repointed control);
   and when `POST-4` step 5 runs it will produce a DG1 `.bp` export whose
   ParaView rendering only you can eyeball (headless sessions cannot).

## Honest current state (digest of §2 — headline gates unmoved)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

New under the headlines: ΔX's residual is **attributed to box truncation**
(r∞ = 1.0023 with the dipolar exponent recovered blind), every P1 field
export of a Nédélec/DG source is **measured 20–52% off pointwise**
(qualitative pictures, not data), and the composed MAT-6 fixture's 9×
solve blow-up is now **attributed away from fill-in** — the matrix is
ordinary for its size; the surviving suspects are cgroup memory pressure
and MUMPS parallel load balancing (weekly review commissions the
discriminator).

## Recent activity (since the 03:00 review)

**Four slots: two items landed and audited compliant; the other two were
both spent on PORT-1 step 3b-xvi's mesh arm without buying its solve.**

- **PORT-1 step 3b-xvi** (04:30 + 06:00): the scoped refinement factor
  was **refuted by measurement** (the feed region is already graded —
  24.7 cells across the arc, not "~5"), and at the corrected refinement
  the pre-registered locality control fires on gmsh's mandatory
  gradation collar rather than on any real leak (outside a 5 mm-dilated
  box the mesh moves −0.17%). The slot correctly refused to move its own
  pre-registered control and handed the decision up. **This review
  re-pointed the control to the 5 mm-dilated gap boxes (band unchanged)**
  and re-queued the step, now including the solve arm.
- **MAG-13 step 2 re-gate** (07:30, ✅): the profile probe's checks now
  bite — smoke rung exits 1 at 0/4 gates, real rung 4/4 at exit 0
  reproducing the record digit-identically. The 03:00 audit demotion is
  discharged; the profile step is restored ✅.
- **MAT-6 step 10a** (09:00, ✅): the 9× attribution is **negative —
  fill-in exonerated** (factor flops grow 1.693× for 1.28× cells, vs the
  ≥ 4× verdict threshold); ≥ 5.1× lives in the numeric phase. Two leads:
  MUMPS estimates 69 894 MB in-core against the 65 536 MiB container
  cap, and the kill stack sits in MUMPS's parallel load-balancing
  receive. Step 10 goes to the weekly review with a scoped discriminator.

Audits: both ✅ flips **compliant** (gates enforced in exit codes, no
bounds loosened; two advisory nits folded into the plan — a digit
transcription fix and a factor-retention memory caveat added to the
step-10 hand-off).

## Automation health

- **Slot yield: 4/4 informative, 2/4 landing** — no lost slots, but one
  item consumed half the interval; it is re-queued with the blocking
  decision made rather than left to fail a third time the same way.
- The `timeout -k 30` harness repair survived its first live composed-
  fixture kill: clean SIGTERM at 299.7 s, footer written, container Up,
  no force-recreate. The 00:00 wedge has a verified counter-case.
- Tree clean at review time; no `recovered/*` branches. Three
  `attempt/PORT-1-*` branches parked by design (adjudication decision 6;
  the newest carries item 1's work-in-progress).
- Queue depth **5** after refresh; all items mutually independent.

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-xvi, third attempt** (standard) — mesh arm under the
   re-pointed locality control, then buy the solve; 0.5 pp bands, either
   outcome proceeds; exit 124 on the solve is itself a finding.
2. **MAG-13 step 2b** (heavy) — price CG1 recovery of B on the solved
   rung; may reach < 5% with no new mesh.
3. **POST-4 step 5** (standard) — price the faithful DG1/VTX export
   route; decision table for the P1-vs-DG1 call.
4. **PORT-1 padding fit** (smoke, zero-solve) — extrapolate the box term
   from the three recorded padding rungs so the port-pair gate states a
   number, not "the suspect".
5. **MAG-13 rung 3** (heavy, spare) — the < 5% wire by brute force;
   exit 124 is itself the reading.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy is refreshed by interactive sessions only and may
lag this file; `docs/status/dashboard.md` on `main` is always current.*
