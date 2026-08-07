# FEM-EM Solver — status

**Updated:** 2026-08-07, 10:30 daily review. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. Housekeeping: local `main` is **15 commits ahead** of `origin/main` after
   this review — push when convenient (every "in CI" claim is a local
   reproduction until then). No Ansys benchmark cases commissioned yet
   (the weekly review owns that; next one is Sunday 01:30).
2. FYI, no action needed: the corrected port voltage (0.8945 × ωM₁₂) is
   validated against an independent control to 3.0% but sits 0.02 pp
   outside a bound whose premise the control itself disproved. Rather than
   moving the bound on judgement, queue item 1 buys the one measurement
   that decides it (see On deck); both outcomes are pre-decided in §7.

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; energy safe in both builds (MAG-16) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave, < 0.06% (TH-1/TH-6) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 1.58% @ 10 MHz (MAT-6); Larmor case is extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4 step 1); never gated on a coil |
| S-parameters | 🧪 heuristic | one real S-matrix, two-loop air fixture in a test (PORT-1) |

## Recent activity (since the 03:00 review)

Sixth consecutive 4/4 interval — two landed, two disciplined parks, all
four slots on or about the port-voltage thread:

- **PORT-1 step 3b-x (parked)** — the terminal-to-terminal correction
  **works**: 0.8945 × ωM₁₂ (vs the old wedge-limited 0.4937), the
  retiling identity holds to 2.7e-4, all 19 gates green. Not landed
  because the plan's second anchor (the reaction route) turned out not to
  exist on a conducting open arc — it reads the ohmic term, a factor 244
  off, for a structural reason, not a defect.
- **PORT-1 step 3b-x-b (parked)** — the missing control now exists: a
  σ = 0 closed-loop solve on the same mesh gives an independent reference
  (0.9224 × ωM₁₂, `Re Z₂₁ = 0` exactly). The estimator agrees with it to
  **3.0224%** against a pre-decided 3% bound — red by 0.02 pp — and the
  slot correctly refused to move the bound: the control measures the
  spread the bound was sized from at 2.8 pp, not the assumed 1.2 pp.
- **PORT-1 step 3b-xi ✅** — the PEC-box attribution is now a **trend,
  not a point**: deficits −8.03% / −5.03% / −3.27% at padding
  0.08 / 0.10 / 0.12, strictly monotone, all the sign a PEC wall must
  produce, 53× the mesh-resolution control. The residual on the corrected
  port voltage has a named, measured owner.
- **EX-2 ✅** — the cylindrical phantom ships as `mesh:2` through the
  runner, and the example found something: at generator defaults the
  inner cylinder meshes as a **heptagonal prism** (resolution is twice the
  inner radius), a 28% inner-volume deficit. Gated in closed form — the
  meshed cap equals the inscribed heptagon to 1.11e-16 — and this review
  audited every caller: none gates an inner-subdomain quantity, so the
  hazard is latent and recorded, not an active defect.

Audits: both ✅ flips (3b-xi, EX-2) verified §4-compliant by independent
read-only auditors — every claimed number found in the harness logs, exit
codes 0, no demotions; EX-2's one bound change was a *tightening*
(1e-3 → 1e-12). Branch hygiene: the 3b-ix and 3b-x branches deleted after
verifying both are strict ancestors of the 3b-x-b branch, which is now the
single live lineage; queue item 1 lands or adjudicates it.

## Automation health

- The grid has run clean since 08-05 15:30Z — 24 consecutive slots, six
  4/4 implementer slates in a row.
- Tree clean at review start and end; no `recovered/*` branches; one
  `attempt/*` branch (the live PORT-1 lineage, deliberate).
- The twice-failed queue item 1 was caught by the queue's own rule
  (implementers skipped it and took independent items) and is now
  rescoped as step 3b-xii with dispositions pre-decided — the blocking
  mechanism worked as designed.
- **Queue depth is 3, not 5** — that is every rubric-compliant item that
  exists; the fourth run before the 18:00 review will hit the
  stop-and-journal drain instruction. Not an outage, just honest scoping.

## On deck (§9, refreshed this review)

1. **PORT-1 step 3b-xii** — the discriminator: rebuild the gapped fixture
   at padding 0.10 and see whether estimator and control converge under
   box enlargement. If yes, the 5% re-size is pre-authorized and the
   whole branch lineage lands on `main`; if no, a real estimator bias has
   been found. Either outcome is a finding.
2. **MAT-4 step 3** — the SAR averaging operator gated at the standard
   1 g/10 g masses on a sphere that can hold them; no solve.
3. **MAT-6 step 5** (spare, heavy) — wire refinement at fixed box to
   separate the last ~1.5% of ΔX.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.*
