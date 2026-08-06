# FEM-EM Solver — status

**Updated:** 2026-08-06, 18:00 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. Housekeeping: thanks for the push — `origin/main` caught up today; after
   this review, local `main` is 5 commits ahead. Push when convenient. No
   Ansys benchmark cases commissioned yet (the weekly review owns that).
2. FYI, no action needed: the first §5.4 ramp example landed —
   `./run_examples.sh -e mesh:1` shows the two-torus port fixture's mesh
   and tags in ParaView (`examples/meshing/paraview_output/`). Marked 🟡
   pending one formality (see Recent activity).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 10:30 review)

Fourth consecutive 4/4 interval — three landed, one disciplined park:

- **PORT-1 step 3b-vii** — the decisive negative the plan asked for.
  Refining the mesh to 40 cells across the gap arc fixed everything a
  discretization artifact would explain (reciprocity 6.3e-2 → 3.9e-3) and
  the port voltage **did not move**: still ~0.49 × the closed form. Four
  sampling geometries now give four answers off one solved field, so the
  deficit is not how we sample. This review adjudicated the two remaining
  suspects: the closed-form reference itself is *bounded* to ~10% by an
  independent estimator, so it cannot explain a factor 2 — the stronger
  suspect is that at skin depth ≈ wire radius, a large share of the loop
  EMF drops inside the wire instead of across the gap. Both tests are
  queued: a free closed-form audit (no solve) and a loop-closure + σ-sweep
  measurement.
- **GEO-12** — closed. Both wall tolerances widened to 1e-6; the
  outer-boundary group now exists and its meshed area equals the analytic
  box surface to 15 digits on both fixtures; every downstream landed number
  re-run and digit-identical. Known-issues 12 retired; its sibling 13 is
  now chunked as **GEO-13** (queued).
- **POST-1 step 6** — CSV export and the stats path proven to share one
  sampling rule: row counts equal in both modes, and the CSV's min/max/mean
  round-trip the float64 bits *exactly* (0.000e+00 relative). Gate-only; no
  divergence found, nothing patched.
- **EX-1** — the two-torus example landed and every geometric identity
  holds to the printed digit, but the audit demoted it ✅ → 🟡 on a real
  gap: no log on record shows `./run_examples.sh` itself dispatching the
  new `mesh:` group (both runs called the inner command directly). The
  remedy is one logged runner invocation — queue item 1, minutes of work.

Audits: GEO-12 and POST-1 step 6 verified §4-compliant by independent
read-only auditors — every claimed number found verbatim in the harness
logs. EX-1 demoted as above. Branch hygiene: the superseded 3b-vi branch
was deleted after a diff confirmed the 3b-vii branch carries a strict
superset; only `attempt/PORT-1-step3bvii-…` remains (queue item 4 continues
on it).

## Automation health

- The grid has run clean since 08-05 15:30Z — 16 consecutive slots, four
  4/4 implementer slates in a row.
- Tree clean at review start and end; no `recovered/*` branches.
- Known-issues: entry 12 retired by GEO-12; entry 13 re-owned by new chunk
  GEO-13 (queued); entry 3 (S-parameters heuristic) gained 3b-vii's
  progress row and is the target of queue items 2 and 4.

## On deck (§9, refreshed this review)

1. **EX-1 closure** — run `./run_examples.sh --list` / `-e mesh:1` through
   the harness; restores the ✅.
2. **PORT-1 step 3b-viii** — closed-form audit of the ωM₁₂ reference
   (elliptic-integral reimplementation + finite-wire correction; no solve).
3. **GEO-13** — decouple `cylindrical_domain`'s wall tolerance from mesh
   resolution (fixes known-issues 13, the last margin defect).
4. **PORT-1 step 3b-ix** — loop-closure decomposition + σ scaling: does
   the missing half of the port voltage drop inside the wire?
5. **MAT-6 step 5** (spare, heavy) — wire refinement at fixed box to
   separate the last ~1.5% of ΔX.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
