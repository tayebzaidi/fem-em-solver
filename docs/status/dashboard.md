# FEM-EM Solver — status

**Updated:** 2026-08-25 18:00, **daily review (scheduled, ran normally)**.
Headline: **`GEO-19` is closed — the 16-leg birdcage mesh is gated** (CAD
identities, C16 sheet symmetry, a per-azimuth-class terminal reading that
collapses to the old gate at 4 legs, and Phase 6's first measured cost
rung: 307 296 cells / 74 s, comfortably affordable). Your `OPS-26` sweep's
static half came back **clean** — 434 DolfinX call sites across 159 files,
zero un-migrated survivors in `src`/`tests` with a binding negative
control — which sharpens the remaining risk to exactly one class:
**gates that no scheduled command executes**. That class now has three
confirmed members (cavity, straight-wire rate, and — found this
interval — the `GEO-15` graded-conductor gate, whose baseline no longer
meshes on 0.11), every one found by the examples layer. All three now
have rulings or dispositions queued, and the execution census (`OPS-26`
step 2) is seeded with them by name. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the
   second case in the same queue.
4. FYI: local `main` is well ahead of origin (push is manual). FYI on
   your two 08-25 directives: `OPS-26` step 1 is **done and clean** (two
   `scripts/probes/` stragglers filed); the fixture-scale directive
   waits on the Sunday 08-30 weekly review as addressed. Nothing needs
   your input on either.

## Honest current state (digest of §2 — three changes this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ⚠️ one rate gate red on `main`, **ruled — landing queued** | closed forms green (Helmholtz 0.04%, `E_Ω` ladder rate 1.6854 on 0.11); the sampled-norm two-sided rate gate measured unstable under its own sampler on **both** images — ruled: rate duty transfers to the already-green one-sided `E_Ω` gate (`MAG-19` step 2, queue item 2), nothing widened |
| Time-harmonic curl-curl | ✅ validated, example family fully re-gated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; `PORT-11` step 1 (the 64 MHz port probe) is queue item 1 |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| S-parameters | ✅ birdcage gated at 10 MHz (`PORT-9`); **16-leg mesh now gated too (`GEO-19` ✅ 08-25)** | 16 legs: identities exact, terminal classes ≤ 2e-7 tight, cost rung 2.65× cells / 3.23× time over 4 legs; **mesh only — no solve, no port, no tuning claim above 4 legs** |
| Test-suite trust | ⚠️ static half **clean**, execution half pending | `OPS-26` step 1: 434 call sites / 159 files, zero survivors in `src`/`tests`, binding negative control; the silently-non-executing-gate class has 3 confirmed members + 1 stale record — all ruled/dispositioned this review, and step 2's census is seeded with them |

## Recent activity (2026-08-25 10:30 → 18:00)

- **12:00:** `GEO-19` step C landed under the construction-symmetry
  ruling — **chunk ✅**, audited §4-COMPLIANT this review (all footers,
  every anchor digit, 645-insertion/0-deletion diff verified; two
  cosmetic observations noted in the review commit). `GEO-20` step 2
  unblocked; attempt branch deleted.
- **13:30:** `MAG-19` step 1 measured the dual-norm 4×2 table and
  honestly reported that the pre-stated rule selects **neither** branch —
  and found the constraint that decided the ruling (`E_Ω` is stable but
  fits above 1.5 everywhere, so the two-sided band cannot transfer).
  **Ruled this review: option (i), duty transfer**; landing queued.
- **15:00:** `OPS-26` step 1 closed — the static sweep is clean, the
  negative control binds (six reverted migrations all caught), two
  un-migrated `scripts/probes/` files filed not fixed.
- **16:30:** `EX-30` leg (mesh) — 4 of 7 green, census exact (13 → 6,
  no other family moved), three reds surfaced and filed without using
  its re-record licence: the `GEO-15` gate red (baseline unmeshable —
  conductor-sizing axis, localised in one 39 s probe), the `GEO-16`
  stale cell record (79 534 → 79 070, sheet exonerated), and `mesh:5`'s
  control premise thinned to 6e-6. **All three ruled this review**
  (re-choice / re-record / new chunk `GEO-21`).

## Automation health

- Four slots scheduled, four ran, all four productive: one chunk close,
  one step close, two disciplined stops that asked for exactly the
  rulings made here. No wedges, no `recovered/*`, no attempt branches
  left, tree clean at every handoff and at this review.
- The audit pipeline is working as designed: every red this interval
  was *filed with its measurement done*, so all four review rulings
  cost zero new compute to make.
- The queue holds **six items — 1, 2, 4, 5 independent; item 3 is two
  independent halves; item 6 serial on item 2**. Newly commissioned,
  not yet queued: `GEO-21` is queued (item 4); `EX-33` (first 16-leg
  example), `EX-32`, `GEO-20` step 2, and `OPS-26` step 2 (seeded) are
  first in line at the next review.

## On deck (§9 — six items this review)

1. **`PORT-11` step 1** — the 64 MHz solve on the loaded birdcage,
   priced, with the 10 MHz column as in-run anchor (standard,
   independent; the mission's first Larmor-frequency port measurement)
2. **`MAG-19` step 2** — land the duty-transfer ruling; retires the
   rate-gate red (standard, independent)
3. **`EX-30` mesh-red pair** — `GEO-16` re-record + `mesh:5` control
   re-choice, each half independent (standard)
4. **`GEO-21` step 1** — re-choose the unmeshable graded-gate baseline,
   measure-first (standard, independent)
5. **`EX-30` leg (ports)** — ports + `ans` examples, licensed
   re-records (standard, independent; spare)
6. **`EX-30` leg (root) completion** — serial on item 2, skips with a
   journal entry if item 2 did not land

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
