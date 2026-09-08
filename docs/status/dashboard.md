# FEM-EM Solver — status

**Updated:** 2026-09-08 03:00 daily review. Headline: **the birdcage B₁⁺
closed-form comparison went from a 26.6% miss to 2.3% at the centre once
the coil was told where its rings are and that it sits in a PEC box —
ten of eleven points are inside the unmoved 5% band, and the one that
is not (7.1% at half radius) is against a comparand whose own
truncation error is 3–5%; the review has a convergent fix (average the
image lattice's consecutive partial sums) and it is queue item 1. The
coil's conduction currents were measured directly and are the port's
current to 3%, flat along the legs to 3%, with Kirchhoff closing at
every ring junction to 2%. On the PEC-hole port, the 2% impedance
asymmetry is *not* a current-reading calibration — it survives both
current routes on both fixtures with gap geometry identical to twelve
digits — and the hole's mutual matches the inner-edge filament form to
0.01%, now ratified as its comparand; the voltage reading is the
surviving candidate and is measured next. The 1 g SAR rung is priced:
2.5 mm phantom cells, 200 k cells, 1.66× the cost.** All four slots
fired and journaled; three complete, one at its pre-registered exit.
**Still a self-consistency story at the Larmor frequencies: no absolute
SAR, no C95.3 compliance figure, no homogeneity, no Larmor coil accuracy
claim, no resonance or tuning claim, and no solve has touched the
human-scale mesh.** Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

## Waiting on you

1. 🟠 **The XL service is Up (since ≈ 20:00 on 09-07) but `ANS-4` step 2
   cannot run from a scheduled slot.** The window is ≈ 15 min of
   degree-1 rungs plus an uncosted degree-2 solve under a 2 h stop rule;
   a headless slot's harness window is capped at 11 min by the tool and
   a backgrounded run is killed at 10 min — both traps already paid for.
   Two ways forward, yours or the 09-09 weekly's: **(a)** run it from an
   interactive session (the §7 `ANS-4` step-2 command, one window,
   `-n 16`, then stop the service and fill the ledger row); **(b)** let
   the weekly split the four degree-1 rungs into heavy-tier windows on
   the ordinary service and keep only the degree-2 solve for XL. The
   item is held in §9 (last, marked do-not-take-headless) so no slot
   spends itself on it. Leaving the service Up costs nothing while idle.
2. 🟡 **Agent-definition edits — still pending, still less urgent.** The
   foreground rule has held on twelve consecutive spawns with the rule
   carried verbatim; the five one-liners (two for `example-runner.md`,
   one for `mesh-probe.md`, one for `implementer.md` — rule (d) — and
   rule (e) for both) would make the workaround unnecessary. Say which
   you want and an interactive session applies them.
3. 🟢 **Session-limit watch, closed:** every scheduled session since the
   09-06 outage has fired (four reviews and sixteen slots).
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
8. FYI, no action — physics worth a glance. **(a)** The image-lattice
   comparand for a coil in a PEC box is only conditionally convergent:
   each shell of images falls as 1/N and alternates in sign, so the
   truncated sum straddles the limit by 3–5% at the orders a test can
   afford, while the mean of two consecutive partial sums converges as
   1/N². The FEM was never the problem — the comparand's own error bar
   was the size of the band. **(b)** The FEM's own field at half radius
   differs by 3.4% between the +x and +y directions on a C4-symmetric
   CAD; the same quadrant shows the worst Kirchhoff junction (2.2%) and
   the only leg whose current rises along its length. A mesh census by
   quadrant is queued (item 5). **(c)** On the hole port, the asymmetry
   is common to the hole and the solid, to the displacement and the
   conduction current, and the two gaps are identical to twelve digits —
   it lives in the voltage reading or the field, not in how current is
   counted. Separately, the wave-assembled S-matrix carries 6× more
   non-unitarity than the Z-matrix asymmetry explains, which nobody has
   attributed yet. Local `main` remains well ahead of origin (push is
   manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first hole port solved, loss-free to the bit; the driven-port displacement current is on `main`** (`TH-15` steps 1, 2a, 2d, 3a ✅; step 2 proper parked on a 2% `Z` asymmetry that is *not* a current calibration) — every conductor in a *solved* coil fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%). Two-torus hole 161 461 cells, `max |Re Z_ij|/|Z_ij| = 0` exactly, S-reciprocity 4.3e-4, unitarity 7.5e-3 (red — 6× the asymmetry's share), mutual on the ratified inner-edge comparand 0.9999 (symmetrised) / 0.9896 (`Z₂₁`) — gated by item 2. Step 3 proper is the weekly's. `TH-14` (copper) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.2747% against the filament form, 0.3895% against the finite-wire-corrected form, 418 888 cells (`MAT-6` ✅); `ANS-1` AGREE (numbers private, re-checked 09-09); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only**; externally **AGREE at 10 MHz, inconclusive at 64 / 128 MHz** (`ANS-4`, private; the XL run is the discriminator, held for an interactive session). 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%. **RLC sheets exist, not gated** (`PORT-14` 🟡); the circuit layer's algebra gated at 1e-12 (`PORT-15` step 1 ✅). The two-torus package module's three digit records are `-n 2` records (1e-4 width sensitivity, `OPS-41` item 3) — physics bands green at every width |
| Multi-port drive | ✅ **package-level, gated on the 4-leg identities and on the exact power identity** (`POST-6` step 1, `PORT-16` ✅, audited PASS); shown by `ports:13` (`EX-49` ✅) | quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087%, linearity 1e-12; `P_src,exact = P_vol + P_sheet,exact` at 5.9e-15 / 1.4e-14 on the superposed drive |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; F-human (0.15 m) gated on CAD identities (`GEO-25` ✅), shown by `mesh:12` | 4-leg record 111 898 / 116 085 (ports) / 80 181 as a hole; 16-leg 270 728; F-human 504 642 cells — **a mesh, never solved; 64 MHz cost unpriced**. Phantom 1 g rung priced at 199 920 cells (`GEO-27` 🧪) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; **the boxed closed form lands on the FEM to 2.3% at the centre, 10 of 11 points inside the unmoved 5%; the 11th (7.1%) is against a comparand truncated at the band's size — item 1 accelerates the lattice** | `WF-6` steps 1–2b, 4a ✅; 4b parked at its exit, 4c measured (currents to 3%, Kirchhoff to 2%); step 4d (item 1) lands step 4 if the averaged lattice converges as predicted. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | ✅ **mass-averaged 10 g, C4-gated on one fixture at 10 MHz at fixed `h`** (`MAT-4` ✅); shown by `mri:3` (`EX-53` ✅, audited PASS) | four 10 g C4 pairs 0.3303 / 0.0756 / 0.0574 / 0.3132% vs 5%; whole-phantom identity 1.7e-14. **The 1 g column misses at 6.84% on 1.65 cells across the ball**; the 2.5 mm rung gives 4.96 cells at 1.66× the cost and item 4 measures the column there. **No absolute SAR, no C95.3 compliance or limit figure, no Larmor, no convergence claim** |
| SAR, imposed field | ✅ lossy sphere 3.5% (`MAT-4` step 1); its example `mat:2` (`EX-52` ✅) | — |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 4 deliberate/known** (unchanged); example-artifact census `dead=0 stale=81 exit=2` at `f700f5e`, 47 examples | API sweep `violations=0`; `OPS-40` ✅ guards the collective; three open known-issues entries dated 2026-09-07, each with its 03:00 ruling row and its retiring item named |

## Recent activity (2026-09-07 18:00 → 2026-09-08 03:00)

- **19:30:** `WF-6` step 4b — the boxed comparand collapses the miss from
  26.6% to 2.3% at the centre and every review prediction lands, but
  the half-radius exit fires on one point (7.1%) and the lattice's own
  drift is 3.3% at order 4; parked, band unmoved, item marked. **Ruled
  this review:** average consecutive partial sums (item 1).
- **21:00:** `TH-15` step 2e — the symmetrised-S identity is exact to
  1e-17, the solid's conduction route reads the same 2.2% asymmetry as
  the displacement route and the hole, the gaps are identical to twelve
  digits, and the hole's symmetrised mutual is the inner-edge filament
  form to 0.01%; 306 s at 4 ranks, code on the branch. **Ruled this
  review:** comparand ratified; the voltage reading is next (item 2).
- **22:30:** `GEO-27` — four-rung phantom ladder, control reproduced to
  the integer; 2.5 mm cells give 4.96 cells across the 1 g ball at
  199 920 cells and 36 s to mesh; landed, 132 s at 2 ranks.
- **00:00:** `WF-6` step 4c — leg currents are the sheet's to 3.1%, flat
  along z to 3.4%, ring arcs on the Kirchhoff sum to 1.3%, junctions to
  2.2% with the bottom ring's mirror sign; the first window died at
  400 s on a `sqrt` inside a UFL comparison (now in the trap list);
  146 s at 4 ranks, code on the branch.
- **03:00 review:** no audit due; six rulings; `GEO-28` opened, `MAT-4`
  step 5, `WF-6` step 4d and `TH-15` step 2f scoped; five ordinary items
  queued; the XL item held.

## Automation health

- **Four of four scheduled slots fired and journaled**; three complete,
  one at its pre-registered exit (rule (d), seventh consecutive).
  First-run streak 47 of 47 over the slots that fired since 09-03 18:00.
  Container Up 4 days continuously; the XL service Up 7 h, idle.
- **Foreground-executor rule: held on all four slots** (12 since the
  break); the mesh-probe spawn returned inside its slot. No docker-socket
  denial (0 of the last 47); no allowlist denial; one benign
  compute-safety event — a 400 s `timeout -k 30` returned a footer on a
  stuck compile and the executor smoked the fix before re-solving.
- Tier labels: 4b heavy by ceiling, measured 71 / 102 s; 2e heavy by
  ceiling, 306 s; `GEO-27` heavy by ceiling, 132 s; 4c heavy by ceiling,
  146 s plus the 400 s abort.
- **Housekeeping:** `attempts.md` at 17 171 lines vs the 6 000 budget —
  the Wednesday weekly's call. 1 237 logs. Example census not re-run
  this interval (`stale=81`).

## On deck (§9 — five ordinary items, all independent, plus the held XL item)

1. **`WF-6` step 4d** — the shell-averaged image lattice at order 6: its
   own drift asserted below 1% first, the wall identity re-asserted, the
   eleven points at the unmoved 5%, the FEM's C4 spread at four rotated
   copies of each point printed; lands step 4 *(implementer; heavy by
   ceiling, 4 ranks, ≈ 71 s + the two gate re-runs)*
2. **`TH-15` step 2f** — the gap voltage read two ways (path sample vs
   gap average) on both ports and both fixtures, `Z` rebuilt on the
   average, the mutual gated on the ratified inner-edge comparand, the
   wave-vs-Z non-unitarity gap printed *(implementer; ≈ 200 s at 4 ranks)*
3. **`OPS-41`** — the two-torus package module's three digit records
   declared `-n 2` records, the `-n 4` miss pinned, `V` / `I` printed at
   both widths to attribute the 1e-4 *(implementer; ≈ 188 + 147 s)*
4. **`MAT-4` step 5** — the 1 g SAR column on the 2.5 mm phantom rung, the
   10 g identity asserted at the unmoved band, the 1 g pairs printed
   against a < 5% prediction, the rung's cell count repeated
   *(implementer; heavy, 4 ranks, ≈ 350 s)*
5. **`GEO-28`** — per-quadrant census of the unloaded birdcage mesh
   (cells, volumes, cell sizes at half radius, per-leg conductor cells):
   is quadrant 2 different? *(mesh-probe, foreground; ≈ 30 s at 2 ranks)*
6. **`ANS-4` step 2 (`xl`)** — **held**: cannot run headless
   (Waiting-on-you item 1); slots skip it unmarked

The 09:00 slot drains by protocol only if all five ordinary items land or
block; the 10:30 review refills.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
