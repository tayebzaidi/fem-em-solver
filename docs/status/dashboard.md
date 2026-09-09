# FEM-EM Solver — status

**Updated:** 2026-09-08 10:30 daily review; **Waiting-on-you refreshed
2026-09-09 02:15 by the weekly planning review** (items 1, 4, 5 and 6 —
the XL split, the `ANS-1` re-check, the new `ANS-2` case, and the dirty
tree). The headline below is the 09-08 10:30 review's and has not been
re-taken; the 03:00 daily review refreshes it. Headline: **the birdcage B₁⁺
closed-form comparison will not be rescued by fixing the comparand. The
image-lattice acceleration queued at 03:00 worked on the interior field
(drift 0.2% at order 6) but broke the PEC-wall identity (3.3% vs 1%),
and the shell terms it measured settle the sign of the truncation: the
converged lattice sits *below* the order-3 sum the gate used, so every
miss grows — about 3% at the centre and 5–8% at half radius along +y,
predicted. The comparand is finished with an odd-order sum whose own
error is bounded under 1%; the residual is the FEM's (a first-order
solve on 1.5 cm air cells, never refined on this fixture), and the
resolution ladder is priced next. Elsewhere the day was green: the 2%
impedance asymmetry on the PEC-hole port is now *measured* to be the
point-sampled gap voltage (rebuilding Z on a volume-averaged voltage
collapses it 134×), the same reading carries the two-torus package
module's width sensitivity (voltage moves at 3e-4, current at 6e-11),
those digit records are now declared 2-rank records with the 4-rank
miss pinned as a strict expected failure, and on the 2.5 mm phantom rung
the 1 g SAR pairs land at 0.10–0.13% against the 5% band that the 10 g
column is gated at — a 1 g gate is queued.** All four slots fired and
journaled; three complete, one at its pre-registered exit; two audits,
both PASS. **Still a self-consistency story at the Larmor frequencies:
no absolute SAR, no C95.3 compliance figure, no homogeneity, no Larmor
coil accuracy claim, no resonance or tuning claim, no closed-form B₁⁺
claim, and no solve has touched the human-scale mesh.** Source of truth
is `PROJECT_PLAN.md`; this page is a read-only digest for the human
operator.

## Waiting on you

1. 🟠 **One interactive run, when you have 25 minutes: `ANS-4` step 2b on
   the XL service.** *Answered by the 2026-09-09 02:15 weekly — it took
   option (b) and then some.* The weekly **split the item**: the four
   degree-1 mesh rungs turn out **not to need XL at all** (≈ 21 GiB at the
   finest rung, priced from `PORT-14` step 1b's measured cell counts and
   `TH-12`'s own memory exponent), so they become **step 2a** and run
   headless in two ordinary heavy windows — no action from you, and they
   carry the 64/128 MHz diagnosis on their own. What is left for you is
   **step 2b**, the single degree-2 solve: it needs ≳ 49 GiB against the
   ordinary service's ~64 GiB wall and runs ≈ 1 100–1 300 s, which no
   headless slot can hold. So this is genuinely an interactive run —
   one window, `-n 16` against `fem-em-solver-xl`, `timeout -k 60 7200`,
   then stop the service; `run_and_log.sh` writes the ledger row itself.
   Full spec, readout and decision rule: §10 "XL slot, 2026-09-09".
   **Heads-up so the result does not look like a failure:** the degree-2
   complex-power identity **will go red** — `TH-12` step 3 measured that
   as coil-specific and common-mode, it is pre-registered, and the band
   must not be touched. Leaving the service Up costs nothing while idle;
   it has now been idle 28 h.
2. 🟡 **Agent-definition edits — still pending, still less urgent.** The
   foreground rule has held on sixteen consecutive spawns with the rule
   carried verbatim; the five one-liners (two for `example-runner.md`,
   one for `mesh-probe.md`, one for `implementer.md` — rule (d) — and
   rule (e) for both) would make the workaround unnecessary. Say which
   you want and an interactive session applies them.
3. 🟢 **Session-limit watch, closed:** every scheduled session since the
   09-06 outage has fired (five reviews and twenty slots).
4. 🟢 **`ANS-1` re-check, done, no action:** the 09-09 weekly re-checked
   the AGREE verdict against the column `MAT-6` step 11 moved. The landed
   digit matches the arithmetic the 09-06 adjudication had already
   pre-written, so **AGREE stands, tighter than before** — no
   re-adjudication, nothing reopened. Numbers stay in `docs/private/`.
5. 🔵 **New benchmark commissioned, not yet yours: `ANS-2` — coil-driven
   SAR in the loaded four-leg birdcage at 10 MHz.** The spec is written
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`)
   and it deliberately **reuses your `ANS-4` HFSS project** — same
   geometry, materials, ports and boundary condition; one frequency, plus
   a phantom mass density (1000 kg/m³) and a field-calculator export. It
   is the first thing that can give this repo an *absolute* check on
   coil-driven SAR: every SAR number we have on a coil today is a
   four-quadrant symmetry identity, which a computation wrong by a
   constant factor would pass. **Do not start it yet** — our runnable half
   does not exist, and sending you a spec without it would waste an AED
   session. It moves to the top of this list when that box is checked.
   Worth reading the spec's "which rows adjudicate" section when you do:
   our averaging ball is a sphere and IEC 62704-1's is a cube, so the
   mass-averaged rows carry a known systematic and the *pointwise* SAR and
   phantom power are the rows that decide.
6. 🟠 **Your uncommitted `ANS-4` step-2 work is sitting in the tree.**
   Three files from 01:58 tonight — the additive `conductor_resolution` /
   `degree` keywords and the 390-line ladder module. This review is
   documentation-only and left them exactly as found, but a dirty tree
   **stops the next scheduled implementer slot** and gets parked on a
   `recovered/*` branch by the one after, so it costs two slots if nobody
   disposes of it. The 03:00 daily review is flagged to handle it; landing
   it is what unblocks step 2a. (Good news: the module's own
   `FEM_EM_ANS4_STEP2_RUNGS` knob makes the 2a/2b split above mechanical —
   nothing needs rewriting.)
7. 🟢 **`ANS-3` AED run** — still the top of your *AED* queue (`ANS-2`
   above is commissioned but not yet ready for you). Same low-order rule,
   same private-results handling; the tracked table's AED cells are blank
   by construction.
8. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert only if you
   want the single-commit form. *(It earned its keep this session: three
   checkpoint commits, none of them lost.)*
9. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
10. FYI, no action — physics worth a glance. **(a)** The image-lattice
   sum for a coil in a PEC box has two different convergence behaviours
   at once: the interior field's shells alternate in sign and fall as
   1/N (so averaging consecutive orders converges fast), but the
   wall-normal residual has an even/odd parity in the truncation order
   — odd orders satisfy the PEC condition, even orders barely move — so
   averaging an odd order with an even one inherits the even order's
   error. The fix is to use odd orders only, at order 11. **(b)** The
   measured shell terms also settle which way the truncation error
   points: the true lattice sum is lower than the order-3 comparand, so
   the FEM overshoots the closed form by about 3% at the centre, not 2%,
   and by more near the legs. With the coil's own currents measured to
   within 1% of the terminal currents, the overshoot is now a statement
   about the discretisation, not the comparand — the 1.5 cm air mesh
   has never been refined on this fixture. **(c)** On the PEC-hole port
   the 2% Z asymmetry is entirely the *reading*: a volume average of the
   gap field is reciprocal to 1.5e-4 where the arc-sampled voltage
   differs by 2% between drives. But that average is off by 50–100% in
   magnitude because the gap box is bigger than the wire and longer than
   the gap; the calibration is measured next (item 4) before any solver
   code changes. Local `main` remains well ahead of origin (push is
   manual).

## Honest current state (digest of §2 — changed this interval: B₁⁺ and SAR rows)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first hole port solved, loss-free to the bit; the driven-port displacement current is on `main`** (`TH-15` steps 1, 2a, 2d, 3a ✅; step 2 proper parked on a 2% `Z` asymmetry that is now *measured* to be the point-sampled gap-voltage reading, step 2f) — every conductor in a *solved* coil fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%). Two-torus hole 161 461 cells, `max |Re Z_ij|/|Z_ij| = 0` exactly, mutual on the ratified inner-edge comparand **0.989641 inside the unmoved 10%** (gated, step 2f), symmetrised-S identity 4.4e-16, raw-S unitarity 7.5e-3 (red, unmoved); Z rebuilt on a gap-averaged voltage is reciprocal to 1.5e-4 (hole) / 1.9e-4 (solid) vs 2.0e-2 / 2.2e-2 on the path sample — but that average is uncalibrated by 50–100%, item 4 measures the calibration. Step 3 proper is the weekly's. `TH-14` (copper) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.2747% against the filament form, 0.3895% against the finite-wire-corrected form, 418 888 cells (`MAT-6` ✅); `ANS-1` AGREE (numbers private, re-checked 09-09); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only**; externally **AGREE at 10 MHz, inconclusive at 64 / 128 MHz** (`ANS-4`, private; the XL run is the discriminator, held for an interactive session). 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%. **RLC sheets exist, not gated** (`PORT-14` 🟡); the circuit layer's algebra gated at 1e-12 (`PORT-15` step 1 ✅). The two-torus package module's three digit records are **declared `-n 2` records** (`OPS-41` ✅, audited PASS): the `-n 4` miss is a pinned strict xfail, attributed to the point-sampled voltage (`|ΔV|/|V|` 3.2e-4 vs `|ΔI|/|I|` ≤ 3.6e-9); physics bands green at every width |
| Multi-port drive | ✅ **package-level, gated on the 4-leg identities and on the exact power identity** (`POST-6` step 1, `PORT-16` ✅, audited PASS); shown by `ports:13` (`EX-49` ✅) | quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087%, linearity 1e-12; `P_src,exact = P_vol + P_sheet,exact` at 5.9e-15 / 1.4e-14 on the superposed drive |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; F-human (0.15 m) gated on CAD identities (`GEO-25` ✅), shown by `mesh:12` | 4-leg record 111 898 / 116 085 (ports) / 80 181 as a hole; 16-leg 270 728; F-human 504 642 cells — **a mesh, never solved; 64 MHz cost unpriced**. Phantom 1 g rung 199 920 cells, now repeated to the integer on three windows (`GEO-27` 🧪; item 3 pins it). **The global air resolution (1.5 cm) has never been refined on the port fixture** — `GEO-29` (item 5) prices that ladder |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; **closed-form gate parked, and now known not to land on comparand work**: against the order-3 boxed lattice the FEM reads 2.3% at the centre and 7.1% at half radius (+y); the converged lattice sits 0.84% *below* that comparand (step 4d's shell terms), so a converged comparand widens every miss to ≈ 3% / ≈ 8%, predicted | `WF-6` steps 1–2b, 4a ✅; 4b parked, 4c measured (currents within 1% of terminal at mid-leg, Kirchhoff to 2%), 4d parked (interior acceleration works, wall identity breaks — even/odd parity). Item 1 (step 4e) lands the odd-order comparand and measures the eleven points against it with two predicted reds; the `h`-ladder follows (`GEO-29` → step 4f). Still **no homogeneity, absolute, closed-form or tuning claim** |
| Coil-driven SAR | ✅ **mass-averaged 10 g, C4-gated on one fixture at 10 MHz at fixed `h`** (`MAT-4` ✅); shown by `mri:3` (`EX-53` ✅, audited PASS) | 10 g C4 pairs 0.3303 / 0.0756 / 0.0574 / 0.3132% on the 7.5 mm rung and **0.0309 / 0.0060 / 0.0394 / 0.0644% on the 2.5 mm rung** (step 5 ✅, audited PASS); whole-phantom identity 8.1e-14. **The 1 g column: 6.84% on 1.65 cells across the ball, 0.0957–0.1305% on 4.96 cells** — printed on the finer rung, gated by item 3. **No absolute SAR, no C95.3 compliance or limit figure, no Larmor, no convergence claim** (two rungs are not a rate) |
| SAR, imposed field | ✅ lossy sphere 3.5% (`MAT-4` step 1); its example `mat:2` (`EX-52` ✅) | — |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 4 deliberate/known** (unchanged); example-artifact census `dead=0 stale=81 exit=2` at `f700f5e`, 47 examples | API sweep `violations=0`; `OPS-40` ✅ guards the collective; the 09-07 width-sensitivity known-issues entry **retired** by `OPS-41`; two open entries (`WF-6` step 4, `TH-15` step 2) each with their 10:30 ruling row and the item that moves them named |

## Recent activity (2026-09-08 03:00 → 10:30)

- **04:30:** `WF-6` step 4d — the shell terms alternate exactly as
  ruled and the averaged interior drift lands at 0.22%, but the
  shell-averaged lattice leaves 3.3% of the source field normal to a
  PEC wall (band 1%): the wall residual has an even/odd parity in the
  order, not an alternating sign. No solve spent; parked, item marked.
  **Ruled this review:** odd orders only (step 4e, item 1), and the
  truncation's measured sign means the miss grows, not shrinks.
- **06:00:** `TH-15` step 2f — the mutual is gated on the ratified
  inner-edge comparand (−1.04% vs 10%), and rebuilding Z on a
  gap-averaged voltage collapses the 2% asymmetry 134× (hole) / 116×
  (solid): the arc-sampled voltage is the asymmetry. The average is
  uncalibrated by 50–100% (box bigger than the wire, longer than the
  gap). 350 s at 4 ranks, code on the branch. **Ruled this review:**
  measure the calibration (step 2g, item 4) before the solver change.
- **07:30:** `OPS-41` — the package module's three digit records
  declared 2-rank records, the 4-rank miss pinned as a strict expected
  failure reproducing the original digits, and the sensitivity
  attributed by measurement to the sampled voltage (3.2e-4) against the
  integrated current (≤ 3.6e-9); 181 / 136 / 142 s; landed; **audited
  PASS**.
- **09:00:** `MAT-4` step 5 — on the 2.5 mm phantom rung the 10 g C4
  pairs assert at 0.03–0.06% and the 1 g pairs read 0.10–0.13%, both
  inside the 5% band; the 199 920-cell mesh repeats to the integer;
  251 / 114 / 245 s at 4 ranks; landed; **audited PASS**. **Ruled this
  review:** register the 1 g gate and pin the mesh (step 5b, item 3).
- **10:30 review:** two audits PASS; seven rulings; `GEO-29` opened;
  `WF-6` step 4e, `TH-15` step 2g and `MAT-4` step 5b scoped; five
  ordinary items queued; the XL item held; `-s` made a standing rule.

## Automation health

- **Four of four scheduled slots fired and journaled**; three complete,
  one at its pre-registered exit (rule (d), eighth consecutive).
  First-run streak 51 of 51 over the slots that fired since 09-03 18:00.
  Container Up 4 days continuously; the XL service Up 14 h, idle.
- **Foreground-executor rule: held on all four slots** (16 since the
  break). The 09:00 slot sized a 900 s container timeout *down* to fit
  the 660 s host window rather than background it — correct; the item's
  pricing was wrong and is fixed in the successor item. No docker-socket
  denial (0 of the last 51); no allowlist denial; no compute-safety
  event; no wedge.
- **Two windows (≈ 9 min) lost to swallowed prints** (pytest without
  `-s`) — now standing rule (g): every pytest window runs `-s`.
- Tier labels: 4d smoke by measurement (24 / 12 s); 2f heavy by ceiling,
  350 s (priced ≈ 200 s); `OPS-41` standard by measurement (181 s is
  1 s over the standard ceiling — the auditor's caveat); step 5 heavy
  by ceiling, 251 / 245 s.
- **Housekeeping:** `attempts.md` at 17 541 lines vs the 6 000 budget —
  the Wednesday weekly's call, tomorrow. 1 248 logs. Example census not
  re-run this interval (`stale=81`).

## On deck (§9 — five ordinary items, all independent, plus the held XL item)

1. **`WF-6` step 4e** — the odd-order image lattice at order 11: its
   wall identity and Leibniz bound asserted first, then the eleven
   points measured against it with reds *predicted* at two half-radius
   points; the comparand lands on `main` either way, the gate lands only
   if the prediction is wrong *(implementer; heavy by ceiling, 4 ranks,
   ≈ 71 s of solves + 2–4 min of lattice)*
2. **`GEO-28`** — per-quadrant census of the unloaded birdcage mesh
   (cells, volumes, cell sizes at half radius, per-leg conductor cells):
   is quadrant 2 different? *(mesh-probe, foreground; ≈ 30 s at 2 ranks)*
3. **`MAT-4` step 5b** — the 1 g SAR C4 pairs asserted at the unmoved
   5% on the 2.5 mm rung, and the rung's cell counts pinned as records
   at the imported 1% band *(implementer; heavy by ceiling, 4 ranks,
   ≈ 250 s)*
4. **`TH-15` step 2g** — the gap-averaged voltage restricted to the wire
   footprint and the gap chord, Z and the mutual rebuilt on each, the
   whole-box reciprocity asserted at 1e-3 *(implementer; ≈ 350 s at
   4 ranks, on the branch)*
5. **`GEO-29`** — the global-resolution cost ladder of the port fixture
   (0.015 → 0.0075 m): cells, mesh time, interior cell size per rung —
   the price of the `h`-ladder both `WF-6` and `ANS-4` need
   *(mesh-probe, foreground; ≤ 5 min at 1 rank)*
6. **`ANS-4` step 2 (`xl`)** — **held**: cannot run headless
   (Waiting-on-you item 1); slots skip it unmarked

The 16:30 slot drains by protocol only if all five ordinary items land or
block; the 18:00 review refills and scopes `WF-6` step 4f from items 1
and 5.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
