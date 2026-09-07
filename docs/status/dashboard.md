# FEM-EM Solver — status

**Updated:** 2026-09-07 18:00 daily review. Headline: **the first PEC-hole
port has been solved and is loss-free to the bit (`Re Z ≡ 0` on the
two-torus hole), the gap-displacement port current is on `main` gated on
the open-circuit condition (`TH-15` step 2d), the point-evaluation
collective now refuses a rank-dependent point list (`OPS-40` ✅), and the
two negative results this interval are both the plan's, not the solver's:
the birdcage B₁⁺ closed form was told the rings sit 15 mm from where the
generator puts them and was never told the coil is in a PEC box 4 cm
away — first-order images account for the 26.6% miss — and the hole
port's non-unitarity is entirely a 2% asymmetry in how the two gaps'
currents are read, with the mutual's miss the filament comparand a PEC
tube cannot meet.** All four implementer slots fired and journaled; two
landed first-run, two took their pre-registered exits. **Still a
self-consistency story at the Larmor frequencies: no absolute SAR, no
C95.3 compliance figure, no homogeneity, no Larmor coil accuracy claim,
no resonance or tuning claim, and no solve has touched the human-scale
mesh.** Source of truth is `PROJECT_PLAN.md`; this page is a read-only
digest for the human operator.

## Waiting on you

1. 🟠 **Bring the XL service up for `ANS-4` step 2 (§9 item 6, `xl`)** —
   `docker compose -f docker/docker-compose.yml --profile xl up -d`, then
   the next implementer slot takes it (one window, ≤ 2 h, ≤ 512 GiB,
   `-n 16`); stop it afterwards. Not Up at 18:00; the slot skips it
   unmarked until it is.
2. 🟡 **Agent-definition edits — still pending, still less urgent.** The
   foreground rule has now held on eight consecutive spawns with the
   rule carried verbatim in the spawn prompt; the five one-liners (two
   for `example-runner.md`, one for `mesh-probe.md`, one for
   `implementer.md` — rule (d) — and rule (e) for both) would make the
   workaround unnecessary. Say which you want and an interactive session
   applies them.
3. 🟢 **Session-limit watch, closed:** every scheduled session since the
   09-06 outage has fired (three reviews and twelve slots). Re-opens only
   if a session dies again.
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
8. FYI, no action — physics worth a glance. **(a)** The birdcage
   generator places the end rings at `z = ±55 mm` (half the leg spacing)
   and runs the legs to `±70 mm` with dead-end stubs; the closed form
   was given `coil_length = 0.14` and so had its rings at ±70 mm on legs
   27% too long. The same fixture is closed by a PEC box only 4 cm from
   the legs and 4.5 cm from the rings, and at 10 MHz that box images
   every current: first-order images take the rings' contribution from
   0.54 to 0.30 of the legs' and the legs themselves down by 15%, so a
   filament coil in *this* box at *these* planes reads ≈ 1.04× the
   legs-only value against the FEM's 1.10× — the 26.6% "miss" is the
   comparand. Nothing about the coil's current is implicated; it is
   still measured directly (queue item 4) because a ~1 V coil 4 cm from a
   PEC wall can push a few % of its current into the wall as displacement
   current, inside the 5% band's margin. **(b)** The PEC-hole two-torus
   `Z` is purely imaginary to the last bit — the first exact lossless
   identity on a solved hole — but 2.07% asymmetric, and for a lossless
   reciprocal network that can only be the ratio of how much of each
   port's current its facet integral captures; the S-matrix reciprocity
   gate passed on the same matrix because near-total reflection dilutes
   it ~50×. **(c)** A PEC tube links the flux through its inner-edge disc
   (35 mm on a 40 mm ring), which alone is a −13% correction to a
   filament mutual; the hole reads −9% against the solid. Local `main`
   remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first hole port solved, loss-free to the bit; the driven-port displacement current is on `main`** (`TH-15` steps 1, 2a, 2d, 3a ✅; step 2 proper parked on a 2% current-calibration asymmetry) — every conductor in a *solved* coil fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%). Two-torus hole 161 461 cells, `max |Re Z_ij|/|Z_ij| = 0` exactly, S-reciprocity 4.3e-4, unitarity 7.5e-3 (red — the asymmetry), mutual −17% (red — the comparand). Undriven port open at 1.5e-6 of the drive on solid and hole alike. Step 2e (item 2) attributes; step 3 proper is the weekly's. `TH-14` (copper) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.2747% against the filament form, 0.3895% against the finite-wire-corrected form, 418 888 cells (`MAT-6` ✅); `ANS-1` AGREE (numbers private, re-checked 09-09); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only**; externally **AGREE at 10 MHz, inconclusive at 64 / 128 MHz** (`ANS-4`, private; the XL run is the discriminator). 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%. **RLC sheets exist, not gated** (`PORT-14` 🟡); the circuit layer's algebra gated at 1e-12 (`PORT-15` step 1 ✅). The two-torus package module's three digit records are `-n 2` records (1e-4 width sensitivity, `OPS-41` item 5) — physics bands green at every width |
| Multi-port drive | ✅ **package-level, gated on the 4-leg identities and on the exact power identity** (`POST-6` step 1, `PORT-16` ✅, audited PASS); shown by `ports:13` (`EX-49` ✅) | quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087%, linearity 1e-12; `P_src,exact = P_vol + P_sheet,exact` at 5.9e-15 / 1.4e-14 on the superposed drive |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; F-human (0.15 m) gated on CAD identities (`GEO-25` ✅), shown by `mesh:12` | 4-leg record 111 898 / 116 085 (ports) / 80 181 as a hole; 16-leg 270 728; F-human 504 642 cells — **a mesh, never solved; 64 MHz cost unpriced** |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; **the closed-form comparison ran and missed by 26.6% — ruled a comparand error (ring planes + PEC box), re-registered, unmoved 5% band** | `WF-6` steps 1–2b, 4a ✅; step 4 parked; step 4b (item 1) is the boxed form at the true ring planes, first-order arithmetic already inside the band. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | ✅ **mass-averaged 10 g, C4-gated on one fixture at 10 MHz at fixed `h`** (`MAT-4` ✅); shown by `mri:3` (`EX-53` ✅, audited PASS) | four 10 g C4 pairs 0.3303 / 0.0756 / 0.0574 / 0.3132% vs 5%; whole-phantom identity 1.7e-14. **The 1 g column misses at 6.84% and is a printed record** — its cost probe is item 3 (`GEO-27`). **No absolute SAR, no C95.3 compliance or limit figure, no Larmor, no convergence claim** |
| SAR, imposed field | ✅ lossy sphere 3.5% (`MAT-4` step 1); its example `mat:2` (`EX-52` ✅) | — |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 4 deliberate/known** (unchanged); example-artifact census `dead=0 stale=81 exit=2` at `f700f5e`, 47 examples | API sweep `violations=0`; `OPS-40` ✅ guards the collective (audited PASS); three open known-issues entries dated 2026-09-07, each with its ruling and its retiring item named |

## Recent activity (2026-09-07 10:30 → 18:00)

- **12:00:** `TH-15` step 2d landed — the gap-displacement port current
  on the driven-port definition; undriven port open at 1.5e-6 of the
  drive, separation 783× / 1097×, the older readings unchanged to the
  digit; 136 s at 4 ranks. Rule (c)'s package gate was green at 2 ranks
  after three digit records missed at 4 ranks by 1e-4 — a new
  known-issues entry, ruled this review (`OPS-41`).
- **13:30:** `OPS-40` landed — the collective raises on every rank for a
  rank-dependent point list and not at all at 1 rank; `EX-52`'s gate and
  example green with bounds unmoved. ✅, audited PASS.
- **15:00:** `WF-6` step 4 — the unloaded coil's `|B₁⁺|` reads 26.6% below
  the free-space filament form with every convention verified; parked,
  band unmoved, §9 item marked in the same commit. **Ruled this review:**
  the comparand, twice — ring planes and the PEC box.
- **16:30:** `TH-15` step 2 proper — the hole port solves, `Re Z = 0`
  exactly, 217 s at 4 ranks; `Z` 2.07% asymmetric, so unitarity and the
  mutual miss; stopped under rule (e), parked, item marked. **Ruled this
  review:** a per-port current calibration and a comparand a PEC tube
  cannot meet; step 2e measures both.
- **18:00 review:** one audit PASS; six rulings; `OPS-41` opened; five
  ordinary items queued, three of them rescopes of this interval's two
  negative results.

## Automation health

- **Four of four scheduled slots fired and journaled**; two landed
  first-run, two took their pre-registered exits correctly (rule (d),
  fifth and sixth consecutive). First-run streak 43 of 43 over the slots
  that fired since 09-03 18:00. Container Up 4 days continuously; all
  three reviews today fired on schedule.
- **Foreground-executor rule: held on all four slots** (8 since the
  break). No docker-socket denial (0 of the last 43); no allowlist
  denial; no compute-safety event.
- Tier labels: `TH-15` step 2d heavy by ceiling, measured 136 / 147 /
  188 s; `OPS-40` smoke + standard (4 / 2 / 57 / 47 s — smoke wrappers
  were sized at 120 s, a process nit); `WF-6` step 4 heavy by ceiling,
  93 / 46 s; `TH-15` step 2 proper heavy by ceiling, 217 s.
- **Housekeeping:** `attempts.md` at 16 922 lines vs the 6 000 budget —
  the Wednesday weekly's call. 1 232 logs. Example census not re-run
  this interval (`stale=81`).

## On deck (§9 — five ordinary items plus the XL item; 1, 2, 3, 5 independent, 4 reads item 1's branch in either state)

1. **`WF-6` step 4b** — the FEM `|B₁⁺|` of the unloaded coil against the
   filament form at the fixture's ring planes summed over the PEC box's
   image lattice, eleven points at the unmoved 5%; the old free-space form
   is the asserted negative control *(implementer; heavy by ceiling, 4
   ranks, ≈ 93 s + the two gate re-runs)*
2. **`TH-15` step 2e** — prove the hole's non-unitarity is entirely the
   2% `Z` asymmetry (symmetrised-`S` unitarity at 1e-9), print the solid's
   `Z₁₂/Z₂₁` on both routes and the two gaps' `A/g`, and the mutual against
   the inner-edge comparands *(implementer; ≈ 350 s at 4 ranks)*
3. **`GEO-27`** — phantom-resolution cost ladder for the 1 g SAR rung,
   four rungs, cells / mesh time / cells-across-the-ball, asserts nothing
   *(mesh-probe, foreground; ≈ 200 s at 2 ranks)*
4. **`WF-6` step 4c** — the coil's leg current at three stations, ring
   current on eight arcs, Kirchhoff residual at eight junctions, all
   printed *(implementer; ≈ 93 s at 4 ranks)*
5. **`OPS-41`** — the two-torus package module's three digit records
   declared `-n 2` records, the `-n 4` miss pinned, `V` / `I` printed at
   both widths to attribute the 1e-4 *(implementer; ≈ 188 + 147 s)*
6. **`ANS-4` step 2 (`xl`)** — skipped unmarked until `fem-em-solver-xl`
   is Up (Waiting-on-you item 1)

The 00:00 slot drains by protocol only if all five ordinary items land or
block; the 03:00 review refills.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
