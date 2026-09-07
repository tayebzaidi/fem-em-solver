# FEM-EM Solver — status

**Updated:** 2026-09-07 10:30 daily review. Headline: **the 1% power-
accounting gap on the 4-leg coil is closed as a gated identity (`PORT-16`
✅), the birdcage's mode-1 Biot–Savart closed form exists and is exact to
machine precision (`WF-6` step 4a), the coil-driven 10 g SAR has its
ParaView example (`EX-53` ✅), and the PEC-hole port current has its
definition by ruling: the package's impedance matrix has always used only
the driven port's current, so the gap-displacement route that "failed" on
the undriven port was measuring a quantity nothing consumes — it lands
today as queue item 1 and the first solved hole port follows as item 4.**
All four implementer slots this interval fired and journaled; three landed
first-run, one took its pre-registered negative-result exit. **Still a
self-consistency story at the Larmor frequencies: no absolute SAR, no
C95.3 compliance figure, no homogeneity, no Larmor coil accuracy claim,
no resonance or tuning claim, and no solve has touched the human-scale
mesh.** Source of truth is `PROJECT_PLAN.md`; this page is a read-only
digest for the human operator.

## Waiting on you

1. 🟠 **Bring the XL service up for `ANS-4` step 2 (§9 item 6, `xl`)** —
   `docker compose -f docker/docker-compose.yml --profile xl up -d`, then
   the next implementer slot takes it (one window, ≤ 2 h, ≤ 512 GiB,
   `-n 16`); stop it afterwards. Not Up at 10:30; the slot skips it
   unmarked until it is.
2. 🟡 **Agent-definition edits — still pending, now less urgent.** The
   `example-runner` held the foreground rule this interval when the spawn
   prompt carried it verbatim (`EX-53`, 09:00 slot), so the workaround
   works; the five one-liners (two for `example-runner.md`, one for
   `mesh-probe.md`, one for `implementer.md` — rule (d) — and rule (e) for
   both) would make it unnecessary. Say which you want and an interactive
   session applies them.
3. 🟢 **Session-limit watch, closed for now:** every scheduled session
   since the 09-06 outage has fired (the 03:00 and 10:30 reviews and the
   eight slots between). No schedule change made; re-opens only if a
   session dies again.
4. 🟡 **`ANS-1` note, no action yet:** the refined Dodd–Deeds fixture
   moved our ΔR column on 09-06; the 2026-09-02 AGREE verdict is
   re-checked privately by the 09-09 weekly.
5. 🟢 **`ANS-3` AED run** — the top of your queue. Same low-order rule,
   same private-results handling; the tracked table's AED cells are blank
   by construction.
6. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert only if you
   want the single-commit form.
7. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
8. FYI, no action — physics worth a glance. **(a)** The undriven port of
   the two-torus fixture is open at its terminals to 1.5 µA against a 1 A
   drive; the 1.2 mA the conduction reading sees on that ring is the
   induced current closing through the ring's own stray capacitance, not
   a terminal current. That is why two "current" definitions disagreed by
   100% and no mesh refinement could reconcile them — and why the
   impedance matrix, which only ever used the driven current, was never
   affected. **(b)** On the F-small birdcage the end rings contribute
   exactly half of what the legs contribute to the centre field (the
   closed form `R²/ρ²`), so any "N line currents" model of B₁⁺ reads
   ~33% low on this coil; the queued FEM comparison (item 3) uses legs +
   rings. **(c)** The drive-level power identity on the quadrature drive
   closes at 1e-14 in its exact form; the 11.6% the terminal form missed
   is entirely the sheet's Cauchy–Schwarz deficit, now measured on the
   superposed drive too. Local `main` remains well ahead of origin (push
   is manual).

## Honest current state (digest of §2 — the multi-port row moved)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first gate + both hole meshes landed; the hole port current has its definition by ruling** (`TH-15` steps 1, 2a, 3a ✅; 2b / 2c parked, 2d queued) — every conductor in a *solved* coil fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%), field miss converging at +1.19 in h. Two-torus hole 161 461 cells, birdcage hole 80 181 cells. **The gap-displacement current on the driven port is what `Z` consumes** (driven continuity 2.2%, reciprocity 5.3e-4, mutual inside 10% on the solid, all on the parked branch); step 2d lands it (item 1), step 2 proper solves the first hole port (item 4), step 3 proper is the weekly's. `TH-14` (copper) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.2747% against the filament form, 0.3895% against the finite-wire-corrected form, 418 888 cells (`MAT-6` ✅); `ANS-1` AGREE (numbers private, re-checked 09-09); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only**; externally **AGREE at 10 MHz, inconclusive at 64 / 128 MHz** (`ANS-4`, private; the XL run is the discriminator). 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%. **RLC sheets exist, not gated** (`PORT-14` 🟡: single-mode to 3.4e-3, ruled a fixture record by the weekly); the circuit layer's algebra gated at 1e-12 (`PORT-15` step 1 ✅) and claims nothing about any meshed coil |
| Multi-port drive | ✅ **package-level, gated on the 4-leg identities and on the exact power identity** (`POST-6` step 1, `PORT-16` ✅ 2026-09-07, audited PASS); shown by `ports:13` (`EX-49` ✅) | quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087%, linearity 1e-12; `P_src,exact = P_vol + P_sheet,exact` at 5.9e-15 / 1.4e-14 on the superposed drive, attribution at 9.9e-14 / 1.6e-13; the terminal form's 11.648% is a printed record of its own Cauchy–Schwarz deficit, `POWER_BALANCE_BAND` unmoved |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; F-human (0.15 m) gated on CAD identities (`GEO-25` ✅), shown by `mesh:12` | 4-leg record 111 898 / 116 085 (ports) / 80 181 as a hole; 16-leg 270 728; F-human 504 642 cells — **a mesh, never solved; 64 MHz cost unpriced** |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; **the closed-form anchor now exists** (`WF-6` step 4a: legs + rings, six exact identities at ≤ 1e-6, the rings exactly half the legs' centre field on F-small) | `WF-6` steps 1–2b, 4a ✅. The FEM comparison on the unloaded coil is item 3, pre-registered at 5% with legs-only and mode-2 as controls. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | ✅ **mass-averaged 10 g, C4-gated on one fixture at 10 MHz at fixed `h`** (`MAT-4` ✅); shown by `mri:3` (`EX-53` ✅, audited PASS) beside `ports:9` | four 10 g C4 pairs 0.3303 / 0.0756 / 0.0574 / 0.3132% vs 5%; whole-phantom identity 1.7e-14; far-side control ~86%. **The 1 g column misses at 6.84% and is a printed record** (a 6.2 mm ball on a 7.5 mm mesh) — its cost probe is item 5 (`GEO-27`). **No absolute SAR, no C95.3 compliance or limit figure, no Larmor, no convergence claim** |
| SAR, imposed field | ✅ lossy sphere 3.5% (`MAT-4` step 1); its example `mat:2` (`EX-52` ✅) | — |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 4 deliberate/known** (5 → 4, the drive-level power test is green since `7a82688`); example-artifact census `dead=0 stale=81 exit=2` at `f700f5e`, 47 examples | API sweep `violations=0` on all four roots; no new known-issues entry this interval (the step-2c entry gained its ruling and retires with item 1); `OPS-40` (item 2) guards the collective that cost the 09-06 22:30 slot its first window |

## Recent activity (2026-09-07 03:00 → 10:30)

- **04:30:** `TH-15` step 2c — the gap-displacement current lands as code
  but its undriven anchor misses by 100% and its control fails; parked
  with nothing loosened, §9 items marked in the same commit. 131 + 103 s
  at 4 ranks. **Ruled this review:** the anchor measured a quantity the
  impedance matrix never uses; the route is admissible on the driven
  port and lands as item 1.
- **06:00:** `PORT-16` step 2 landed — the exact power identity and its
  attribution on the superposed quadrature drive at 1e-14 / 1e-13, the
  deliberate red re-pointed, `POWER_BALANCE_BAND` unmoved. `PORT-16` ✅;
  104 s at 2 ranks. Audited PASS (10 of 10 digits).
- **07:30:** `WF-6` step 4a landed — the birdcage filament closed form,
  six exact identities green at 4 s; two of the item's own clauses were
  wrong and the corrections are stronger (rings half the legs' centre
  field; Ampère replaces `∇·B` as the open-circuit control).
- **09:00:** `EX-53` landed — `mri:3`, 10 g mass-averaged SAR on the
  coil-driven field in ParaView, gate reproduced through the example path
  at 1.7e-14, 91 s at 4 ranks; the spawned runner held the foreground
  rule. ✅, audited PASS (25 of 25 digits).
- **10:30 review:** two audits PASS; six rulings (the hole port current's
  definition, `WF-6` step 4 scoped with the ring correction, `GEO-27`
  opened, `PORT-16` step 3 left to the weekly, the XL item kept, no
  example chunk); five ordinary items queued.

## Automation health

- **Four of four scheduled slots fired and journaled**; three landed
  first-run, one took its negative-result exit correctly (rule (d),
  fourth consecutive). First-run streak 39 of 39 over the slots that
  fired since 09-03 18:00. Container Up 3 days continuously; both reviews
  today fired on schedule.
- **Foreground-executor rule: held on all four slots**, including the
  `example-runner` spawn that had broken it twice before. No
  docker-socket denial (0 of the last 39); no allowlist denial; no
  compute-safety event.
- Tier labels: `TH-15` step 2c heavy by ceiling, measured 131 / 103 s;
  `PORT-16` step 2 standard (104 s); `WF-6` step 4a smoke (4 s); `EX-53`
  standard (91 s inside a 600 s runner window).
- **Housekeeping:** `attempts.md` at 16 600 lines vs the 6 000 budget —
  the window is the Wednesday weekly's call. 1 218 logs. Example census
  `stale` drifted 79 → 81 (age-based, ~2 names per interval, severity
  `report`), the weekly's refresh.

## On deck (§9 — five ordinary items plus the XL item; 1, 2, 3, 5 independent, 4 serial on 1)

1. **`TH-15` step 2d** — land the gap-displacement port current from the
   parked branch with the undriven anchor replaced by the open-circuit
   condition (`|I_undriven|/I_drive ≤ 1e-4`, measured 1.5e-6) and the
   conduction volume average asserted ≥ 100× above it as the control;
   driven continuity, reciprocity and the mutual unchanged and already
   green *(implementer; heavy by ceiling, 4 ranks, ≈ 131 s + the package
   gate re-run)*
2. **`OPS-40`** — the point-evaluation collective refuses a rank-dependent
   point list, on every rank; `EX-52`'s gate and example re-run green
   *(implementer; smoke + two standard re-runs)*
3. **`WF-6` step 4** — the FEM `|B₁⁺|` of the *unloaded* F-small coil
   against the legs + rings closed form at eleven centre-plane points,
   pre-registered at 5%, legs-only and mode-2 as labelled controls
   *(implementer; heavy by ceiling, 4 ranks, ≈ 270 s + the four-port gate
   re-run)*
4. **`TH-15` step 2 proper** — the parked PEC-hole 2×2 module on the
   displacement route (`Re Z = 0`, reciprocity, unitarity, mutual) —
   **skip unmarked if item 1 did not land** *(implementer; ≈ 220 s at 4
   ranks)*
5. **`GEO-27`** — phantom-resolution cost ladder for the 1 g SAR rung,
   four rungs, cells / mesh time / cells-across-the-ball, asserts nothing
   *(mesh-probe, foreground; ≈ 200 s at 2 ranks)*
6. **`ANS-4` step 2 (`xl`)** — skipped unmarked until `fem-em-solver-xl`
   is Up (Waiting-on-you item 1)

The 16:30 slot drains by protocol only if all five ordinary items land or
block; the 18:00 review refills.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
