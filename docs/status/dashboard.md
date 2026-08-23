# FEM-EM Solver — status

**Updated:** 2026-08-23 10:30, **daily review (scheduled, ran normally)**.
Headline: **the birdcage has its first 4×4 network — and its negative
control found that the port route has only ever been tested where
symmetry hides its error.** `PORT-9` leg (d) solved the loaded, gapped
birdcage as a four-port at 10 MHz on the first run: reciprocity
2.5e-05, passive (σ_max 0.863), C4 class spreads ≤ 0.02% — every gate
hundreds of times inside. Then leg (d1) rotated one leg by 22.5° and the
network **lost reciprocity 223×** (5.6e-03 vs 1e-3). The implementer
blamed a 1.9% sheet-width asymmetry; this review checked that against the
printed Z and it does not hold — the worst asymmetric pair is between two
ports that did not move. The residual is a global discretisation-order
systematic: the voltage readout is not the source's adjoint, so `Z − Zᵀ`
cancels only when every port sees the same local mesh, which is every
fixture the route had been measured on. A decisive two-torus probe with
unequal sheet widths is queued; the C4 gate is tightened to 0.5%. `OPS-18`
3a is one ten-minute write from closing. `main` still boots 0.7.2 by
design. Source of truth is `PROJECT_PLAN.md`; this page is a read-only
digest for the human operator.

## Waiting on you

**Nothing new is blocked on you this interval.** Both decisions owed
(`OPS-18` ruling (1)'s extension; `PORT-9` gate (iii) and the reciprocity
finding) were the review's and are made.

1. 🟢 **The `ANS-3` AED run is unblocked** (unchanged since 08-16). Your
   half: replicate `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`
   in Ansys Electronics Desktop and fill the blank AED columns in
   `COMPARISON.md`.
2. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
3. **ANS-1 Ansys replication** — still yours; ANS-3 (item 1) is the second
   case in the same queue.
4. FYI, a finding worth knowing: **the lumped-sheet port route's
   reciprocity had only been measured on symmetric fixtures** (two
   identical tori, the C4 birdcage), where a non-adjoint readout's error
   cancels exactly. On an asymmetric layout it reads 0.2–1.6% per port
   pair. No gated number is wrong — every record was taken on a symmetric
   fixture — but if the probe confirms the reading, the readout fix will
   move the two-torus and birdcage port records by ~that much, and a
   class re-record will be ruled then. `PORT-11` (64 MHz ports) stays
   serial on this.
5. FYI: local `main` is well ahead of origin (push is manual; last push
   08-18 night).
6. FYI, standing: the `docker-compose.yml` allow is used only for
   `environment:` keys; `volumes:`, the mount and the 64 G limit are
   untouched. Every `OPS-18` slot has restored 0.7.2 and probed it.

## Honest current state (digest of §2 — one line changed)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms; Helmholtz 0.04%, loop 7.07%; wire `E_Ω` = 10.73% at h = 0.0025, rate 1.68 on the ladder (`MAG-18` ✅ 08-23); MAG-17 rate 2.4476 |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.83% + power 3.63% (TH-10); degree-2 gated at 0.1405% (TH-12/EX-25) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (MAT-6); no affordable 64 MHz bracket on this box (adjudicated 08-18); Larmor coil loading stays an extrapolation |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (MAT-4); never on a coil |
| S-parameters | ✅ package path field-derived (PORT-1) | two-torus only; **the gapped birdcage has a solved 4×4 at 10 MHz on the symmetric mesh** (PORT-9 leg (d), 0.7.2): reciprocity 2.5e-05, σ_max 0.863, C4 spreads ≤ 0.02% — but **the geometric control showed the route loses reciprocity (5.6e-03) on an asymmetric layout**, under investigation (leg (d2)); §2.2's "no coil has ports" stands |
| Test-suite trust | ✅ reconciled | OPS-17 closed 08-21. **On 0.11 (branch only): TH-6, TH-10, MAT-4, MAT-6 reproduce; PORT-1's gates hold; `MAG-18` green (rate 1.6854); four records written, two more ruled writable this review** |

## Recent activity (2026-08-23 03:00 → 10:30)

- **04:30:** `PORT-9` leg (d) closed — `9 passed` / 64.23 s / `-n 2`,
  reproduced digit for digit by a second run. Four driven solves at
  50 Ω on the 116 416-cell gapped birdcage: `‖S−Sᵀ‖/‖S‖` 2.495e-05 vs
  1e-3; σ(S) = 0.863 / 0.800 / 0.800 / 0.187, column power sums ≤ 0.515
  (about half the incident power absorbed by legs + saline); C4 class
  spreads self 0.0199% / adjacent 0.0180% / opposite 0.0108% vs 5%; P1
  column reproduces leg (d0) to 1.9e-10; pooled-vs-intra separation 466×.
- **06:00:** `OPS-18` 3a attempt 7 — all four licensed records written
  and confirmed by two runs; leg 2 closes (`11 passed, 4 skipped`, rate
  1.6854; loop + mutual files green on their existing bands). Leg 1 stays
  `1 failed` because the same assertion loop unmasked two more records
  (0.828893, 0.077431) the ruling had not enumerated — correctly not
  written in-slot.
- **07:30:** `PORT-9` leg (d1) attempt 1 — the `leg_azimuth_offsets_rad`
  mesh knob lands exact (`5 passed`; zero offsets reproduce the baseline
  digit for digit; the rotated port's sheet area = analytic to 1e-12).
  Solve half not reached. Two convention findings recorded (the
  half-plane rule is not C4-covariant; sheets must be built on-axis and
  rotated).
- **09:00:** `PORT-9` leg (d1) attempt 2 — `2 failed, 7 passed` / 119 s.
  Zero rung reproduces leg (d)'s 4×4 to ≤ 3e-10 (the knob does not move
  the solve). Displaced: spreads 5.18% / 7.11% / **1.65%** vs 5% (the
  opposite class is blind), and `‖S−Sᵀ‖/‖S‖` **5.57e-03** vs 1e-3.
  Parked on `attempt/PORT-9-d1-20260823T124500Z`; nothing widened.
- **This review:** leg (d) audited compliant; **ruling (1\*)** — the
  re-record licence restated as a class rule so further unmasked records
  need no review; **the width hypothesis refuted** from the log's own Z
  (`|Z_ij/Z_ji|` worst on P2–P4 at 1.0104, no common factor on row 1);
  **gate (iii) → 0.5%** (25× above the measured floor, 3.3× below the
  weakest displaced class; a tightening); **leg (d2)** scoped with
  pre-registered predictions (A: O(1e-2), B: ≤ 1e-9); (d1′) serial on it.
  Old §9 block archived.

## Automation health

- Four slots, four useful outcomes: one first-run close, one correct
  ruling-stop, two attempts that delivered a mesh feature exact and a
  negative control that found a real systematic. No drain, no exit 124,
  no wedge, no permission denial. Tree clean at every handoff; no
  `recovered/*`.
- `attempt/OPS-18` is the sanctioned worksite at `66aaf69` and persists
  until item 3 merges it. `attempt/PORT-9-d1-*` at `bbe657f` holds the
  mesh knob + sweep module and lands with (d1′).
- The queue holds **five** items: four independent (three on 0.7.2
  `main`, one on the upgrade branch), one serial on the upgrade. Two
  items are deliberately *not* queued (`PORT-11` step 1, `PORT-9` (d1′))
  because their prerequisite is a number only a review may read.

## On deck (§9 — five open items this review)

1. **`OPS-18` 3a under (1\*)** — write the two unmasked records, confirm
   `19 passed` twice (branch, standard, ~12 min compute)
2. **`PORT-9` leg (d2)** — asymmetric two-torus (`f` = 0.5 / 0.735):
   does the route stay reciprocal when the ports differ? Predictions
   pre-registered either way (0.7.2, standard, ~250 s, independent)
3. **`OPS-18` 3b** — §5.3 table, drift disposal, confirming run,
   **merge** (serial on item 1)
4. **`GEO-19`** — the birdcage at 16 legs: identity family re-gated at
   C16, first measured cost for the 32-port target (mesh only, heavy,
   stop rule at 1 M cells / 600 s; independent)
5. **`GEO-20` step 1** — high-pass ring-gap ports at 4 legs, `GEO-18`'s
   identities in the ring frame (mesh only, standard; independent, spare)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
