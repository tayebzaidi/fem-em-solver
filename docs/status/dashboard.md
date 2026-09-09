# FEM-EM Solver — status

**Updated:** 2026-09-09 03:00 daily review (covering two intervals — the
09-08 18:00 review never ran). Headline: **the birdcage B₁⁺ closed-form
comparison is over, and it ended in a measurement rather than a guess.
The image-lattice comparand does not converge at all: its PEC-wall
residual bottoms at order 5 and then *rises*, both parities settling on a
common non-zero ~3.4% — the sum is conditionally convergent and no
truncation order satisfies the wall condition. So the analytic comparand
is set aside (not widened — the 5% band and the order-3 default are
untouched on `main`), and the question moves where two mesh probes have
now cornered it: the quadrant census cleared the mesh's *symmetry* (every
quadrant agrees to 0.1% against a 3.4% field effect) and the resolution
ladder measured its *coarseness* — the air cells inside the coil average
2.2 cm across, 1.5× their nominal size and wider than the 1.4 cm shell the
gate samples in. The next run refines that mesh and asks whether the
field's own four-fold symmetry tightens with it; that answer, either way,
is the honest end of this thread. Elsewhere: the 1 g SAR column is now a
**gate** at 0.10–0.13% against 5% on the fine phantom rung (audited PASS),
and on the PEC-hole port the calibrated gap reading is the wire-footprint
one — it reproduces the mutual to 3.7%, and one geometry measurement now
stands between it and a solver fix.** Eight slots fired; five did work,
**three were lost to the missed 18:00 review** — that outage, not the
physics, is the interval's largest cost. **Still a self-consistency story
at the Larmor frequencies: no absolute SAR, no C95.3 compliance figure, no
homogeneity, no Larmor coil accuracy claim, no resonance or tuning claim,
no closed-form B₁⁺ claim, and no solve has touched the human-scale mesh.**
Source of truth is `PROJECT_PLAN.md`; this page is a read-only digest for
the human operator.

## Waiting on you

1. 🟠 **One interactive run, when you have 25 minutes: `ANS-4` step 2b on
   the XL service.** Unchanged from the 02:15 weekly, and now the *only*
   thing on this list that needs you. The weekly split the item: the four
   degree-1 rungs do not need XL (≈ 21 GiB at the finest) and are
   **queued headless as step 2a — the very next slot takes them**, so the
   64/128 MHz diagnosis proceeds without you. What is left is **step 2b**,
   the single degree-2 solve: ≳ 49 GiB and ≈ 1 100–1 300 s, which no
   headless slot can hold (the tooling caps a foreground window at 660 s).
   One window, `-n 16` against `fem-em-solver-xl`, `timeout -k 60 7200`,
   then stop the service; `run_and_log.sh` writes the ledger row itself.
   Full spec, readout and decision rule: §10 "XL slot, 2026-09-09" and §9
   item 6. **Heads-up so the result does not look like a failure:** the
   degree-2 complex-power identity **will go red** — `TH-12` step 3
   measured that as coil-specific and common-mode, it is pre-registered,
   and the band must not be touched. *Honest note the weekly wrote and
   this review carries: if step 2a alone closes most of the private gap,
   2b becomes a bound on our own order sensitivity rather than the
   discriminator, and the 09-13 weekly may re-commission the slot. Still
   worth running — nobody has measured our order sensitivity on a
   coil-fed birdcage at a Larmor frequency.* The service has now been idle
   ≈ 31 h; leaving it Up costs nothing.
2. 🟢 **Your uncommitted `ANS-4` step-2 work — landed, nothing owed.**
   The three files from 01:58 last night are committed (`d6cd0fb`): the
   390-line ladder module and the two additive keywords. This review read
   them before landing — the module asserts only imported, unmoved bands,
   prints the S entries and the Richardson fit without asserting them,
   contains no AED number, and every cross-module import resolves; the two
   keyword defaults are behaviour-preserving by inspection (`degree=1` is
   already the sweep's own signature default). They are **committed
   unexecuted**, so the queued step-2a run re-runs both touched gate
   modules green in its own slot before trusting them. One thing your
   module does that the split did not anticipate, now handled in the item:
   it builds the degree-2 solve *unconditionally* whenever the ×1 rung is
   in the ladder, and `FEM_EM_ANS4_STEP2_RUNGS` does not suppress it — so
   step 2a adds a second knob rather than accidentally running a 49 GiB
   solve on the ordinary service.
3. 🟡 **Agent-definition edits — still pending, still less urgent.** The
   foreground rule has now held on twenty-one consecutive spawns with the
   rule carried verbatim; the five one-liners (two for `example-runner.md`,
   one for `mesh-probe.md`, one for `implementer.md` — rule (d) — and
   rule (e) for both) would make the workaround unnecessary. Say which you
   want and an interactive session applies them. *(Related, found by the
   09-09 weekly: `implementer.md` is the one agent file with no "Last
   verified against" footer, and it is the most-invoked of the seven.)*
4. 🟠 **Session-limit watch, reopened — it cost three slots yesterday.**
   The 09-08 18:00 daily review died on usage credits (a 146-byte launcher
   log is the tell), and because that review is the only session that
   refills the work queue, the 21:00, 22:30 and 00:00 slots all found an
   empty queue and stopped. Everything else fired normally, so the outage
   was transient and confined to one session. Mitigation already in place
   and self-expiring: the scheduled reviews run on Opus through 2026-09-11
   (`scripts/automation/review-model.env`). No action needed unless you
   want the window extended.
5. 🟢 **`ANS-1` re-check, done, no action:** the 09-09 weekly re-checked
   the AGREE verdict against the column `MAT-6` step 11 moved. The landed
   digit matches the arithmetic the 09-06 adjudication had already
   pre-written, so **AGREE stands, tighter than before** — no
   re-adjudication, nothing reopened. Numbers stay in `docs/private/`.
6. 🔵 **New benchmark commissioned, not yet yours: `ANS-2` — coil-driven
   SAR in the loaded four-leg birdcage at 10 MHz.** The spec is written
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`)
   and it deliberately **reuses your `ANS-4` HFSS project** — same
   geometry, materials, ports and boundary condition; one frequency, plus
   a phantom mass density (1000 kg/m³) and a field-calculator export. It
   is the first thing that can give this repo an *absolute* check on
   coil-driven SAR: every SAR number we have on a coil today is a
   four-quadrant symmetry identity, which a computation wrong by a
   constant factor would pass. **Do not start it yet** — our runnable half
   is now *queued* (§9 item 4, scoped to the pointwise-SAR and
   phantom-power rows that actually adjudicate) but does not exist yet.
   It moves to the top of this list when that box is checked. Worth
   reading the spec's "which rows adjudicate" section when you do: our
   averaging ball is a sphere and IEC 62704-1's is a cube, so the
   mass-averaged rows carry a known systematic and the *pointwise* SAR and
   phantom power are the rows that decide.
7. 🟢 **`ANS-3` AED run** — still the top of your *AED* queue (`ANS-2`
   above is commissioned but not yet ready for you). Same low-order rule,
   same private-results handling; the tracked table's AED cells are blank
   by construction.
8. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert only if you
   want the single-commit form. *(It earned its keep again on 09-09: four
   checkpoint commits, none lost.)*
9. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
10. FYI, no action — physics worth a glance. **(a)** The image-lattice
   comparand for a coil in a PEC box is a genuinely *conditionally
   convergent* sum: how much of it satisfies the box's own boundary
   condition depends on the shape you truncate it with, not on how far you
   go. Truncating at a cube leaves one unpaired outer shell that subtends
   the same solid angle at each wall for every order, so the wall error
   tends to a constant (~3.4%) instead of to zero, and the order-5
   crossing that looked like convergence was an accident of the two
   parities passing each other. Gating on it would have been fitting.
   **(b)** Two mesh probes then agreed by independent routes about where
   the remaining ~3% actually lives: the quadrant census found the mesh
   symmetric to 0.1% (so the field's 3.4% four-fold asymmetry is not the
   mesh's shape), and the resolution ladder found the air cells inside the
   coil averaging 2.2 cm — wider than the 1.4 cm shell the gate samples
   in. That is a resolution story, and the next run tests it directly.
   **(c)** On the PEC-hole port, restricting the gap-voltage average to
   the *wire footprint* reproduces the closed-form mutual to 3.7% where
   the whole-box average misses by 34% and the chord-restricted one by
   54%. The remaining puzzle is arithmetic, not physics: the gap's cell
   tag reads exactly half the volume its CAD box should have, and that
   factor 2 divides into every normalisation on the fixture — so one
   geometry-only measurement runs before any solver code changes. Local
   `main` remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — **unchanged this interval: no gate changed hands**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first hole port solved, loss-free to the bit; the driven-port displacement current is on `main`** (`TH-15` steps 1, 2a, 2d, 3a ✅; step 2 proper parked on a 2% `Z` asymmetry that is now *measured* to be the point-sampled gap-voltage reading, step 2f) — every conductor in a *solved* coil fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%). Two-torus hole 161 461 cells, `max \|Re Z_ij\|/\|Z_ij\| = 0` exactly, mutual on the ratified inner-edge comparand **0.989641 inside the unmoved 10%** (gated, step 2f), symmetrised-S identity 4.4e-16, raw-S unitarity 7.5e-3 (red, unmoved). Step 2g measured the calibration: the **wire-footprint** average reproduces the mutual at −3.67% / +0.80% inside 10% where the whole-box read misses 34% and the chord-restricted read 54%. Item 2 (step 2h) settles the gap tag's half-domain factor 2 before the `src/` fix is specified. Step 3 proper is the weekly's. `TH-14` (copper) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.2747% against the filament form, 0.3895% against the finite-wire-corrected form, 418 888 cells (`MAT-6` ✅); `ANS-1` AGREE (numbers private, re-checked 09-09); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only**; externally **AGREE at 10 MHz, inconclusive at 64 / 128 MHz** (`ANS-4`, private). The discriminator is now **split**: its cheap degree-1 half (step 2a) is queued headless as item 1, and only the degree-2 solve (step 2b) still needs the XL slot. 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%. **RLC sheets exist, not gated** (`PORT-14` 🟡); the circuit layer's algebra gated at 1e-12 (`PORT-15` step 1 ✅). The two-torus package module's three digit records are **declared `-n 2` records** (`OPS-41` ✅, audited PASS): the `-n 4` miss is a pinned strict xfail, attributed to the point-sampled voltage (`\|ΔV\|/\|V\|` 3.2e-4 vs `\|ΔI\|/\|I\|` ≤ 3.6e-9); physics bands green at every width |
| Multi-port drive | ✅ **package-level, gated on the 4-leg identities and on the exact power identity** (`POST-6` step 1, `PORT-16` ✅, audited PASS); shown by `ports:13` (`EX-49` ✅) | quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087%, linearity 1e-12; `P_src,exact = P_vol + P_sheet,exact` at 5.9e-15 / 1.4e-14 on the superposed drive |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; F-human (0.15 m) gated on CAD identities (`GEO-25` ✅), shown by `mesh:12` | 4-leg record 111 898 / 116 085 (ports) / 80 181 as a hole; 16-leg 270 728; F-human 504 642 cells — **a mesh, never solved; 64 MHz cost unpriced**. Phantom 1 g rung 199 920 / 58 866 cells, now **asserted as version-tagged records** at the imported 1% band (`MAT-4` step 5b ✅). The global air resolution is **now priced** (`GEO-29` 🧪): 116 085 → 281 728 cells over a nominal 8× refinement, interior mean cell 2.19 → 1.07 cm, mesh side affordable on all four rungs; the **solve** side is unmeasured and item 3 measures it |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; **the closed-form gate is set aside, and the reason is now measured rather than suspected**: the image-lattice comparand's PEC-wall residual bottoms at order 5 and rises thereafter, both parities converging on a common non-zero ≈ 3.4% (step 4e), so no truncation order satisfies the identity and the comparand route is refuted. Nothing was widened — `CLOSED_FORM_BAND` 5.0e-2, `WALL_NORMAL_BAND` 1.0e-2 and `IMAGE_ORDER` 3 are unmoved on `main` | `WF-6` steps 1–2b, 4a ✅; 4b, 4d, 4e parked. The residue is a degree-1 solve on 1.5 cm air cells read through a CG1 `curl E` projection, and two probes have narrowed it: `GEO-28` cleared the mesh's symmetry (quadrant spreads ≲ 0.1% against a 3.4% field effect), `GEO-29` measured its coarseness (interior mean cell 2.19 cm, 1.46× nominal, wider than the 1.4 cm shell the gate samples in). Item 3 (step 4f) measures the field's own C4 spread across three `h` rungs — predicted to fall, never asserted to. Still **no homogeneity, absolute, closed-form or tuning claim** |
| Coil-driven SAR | ✅ **mass-averaged 1 g *and* 10 g, C4-gated on one fixture at 10 MHz at fixed `h`** (`MAT-4` ✅); shown by `mri:3` (`EX-53` ✅, audited PASS) | 10 g C4 pairs 0.3303 / 0.0756 / 0.0574 / 0.3132% on the 7.5 mm rung and 0.0309 / 0.0060 / 0.0394 / 0.0644% on the 2.5 mm rung; **the 1 g pairs 0.0957 / 0.1199 / 0.1305 / 0.1065% are now *asserted* at the same unmoved 5% band on the 2.5 mm rung** (step 5b ✅, audited PASS this review), mis-paired control 87.0%; whole-phantom identity 8.1e-14. **No absolute SAR, no C95.3 compliance or limit figure, no Larmor, no convergence claim** (two rungs are not a rate). `ANS-2` (item 4) is the first thing that can attack the absolute claim |
| SAR, imposed field | ✅ lossy sphere 3.5% (`MAT-4` step 1); its example `mat:2` (`EX-52` ✅) | — |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 4 deliberate/known** (unchanged); example-artifact census `dead=0 stale=81 exit=2` at `f700f5e`, 47 examples | API sweep `violations=0`; `OPS-40` ✅ guards the collective. Two open known-issues entries (`WF-6` step 4, `TH-15` step 2), each with its 2026-09-09 ruling row and the item that moves it named. The `stale=81` reading now covers 40 of 47 examples — this review ruled the 48 h window is measuring the run cadence, not staleness, and queued `OPS-42` |

## Recent activity (2026-09-08 10:30 → 2026-09-09 03:00, two intervals)

- **12:00:** `WF-6` step 4e — the comparand route is **refuted**, not just
  missed: the wall residual bottoms at order 5 (0.60%) and rises to 2.1%
  by order 11, both parities converging on a common ~3.4%. No solve
  spent; parked, item marked. **Ruled this review:** set the analytic
  comparand aside — nothing is widened — and measure the FEM's own C4
  symmetry across a mesh ladder instead (step 4f, item 3).
- **13:30:** `GEO-28` (mesh probe) — the quadrant census answers **no**:
  every mass spread is ≲ 0.1% (air ≤ 0.7%), an order below the 3.4% field
  effect, and quadrant 2 is never the outlier. The mesh's symmetry is
  cleared. Two windows, 30 s each, character-identical.
- **15:00:** `MAT-4` step 5b — the four 1 g C4 pairs are now **asserted**
  at 0.0957 / 0.1199 / 0.1305 / 0.1065% against the unmoved 5% band, and
  the rung's mesh is pinned as two version-tagged records (199 920 /
  58 866 cells at the imported 1% band); 316 s at 4 ranks; landed;
  **audited PASS this review** (27 of 27 digits traced; two
  finiteness-only asserts *replaced* by quantitative ones — a tightening).
- **16:30:** `TH-15` step 2g — the calibrated gap reading is **B**, the
  wire footprint: it reproduces the ratified mutual at −3.7% / +0.8%
  inside the unmoved 10% where the whole-box read misses 34% and the
  chord-restricted read misses 54%, so the item's own clause fired on C.
  386 s at 4 ranks, code on the branch. **Ruled this review:** settle the
  gap tag's half-domain factor 2 by geometry first (step 2h, item 2),
  then specify the solver fix from B.
- **19:30:** `GEO-29` (mesh probe) — the resolution ladder runs to
  completion and the answer is **yes**, the interior cell size falls with
  the global setting: 116 085 → 281 728 cells over a nominal 8×
  refinement (only 2.4× the cells) with the interior mean cell dropping
  2.19 → 1.07 cm. The ×1 mesh's 2.19 cm interior cell is 1.46× nominal
  and *wider than the 1.4 cm shell the B₁⁺ gate samples in* — the number
  that made step 4f scopable. 145 s, one rank.
- **21:00 / 22:30 / 00:00:** **no chunk work** — the queue was empty
  because the 18:00 review never ran. Each slot correctly stopped and
  journaled rather than improvising.
- **02:15 weekly:** archive rotation (plan −1 335 lines, attempts −3 162),
  the XL slot spent and `ANS-4` step 2 split, `ANS-2` commissioned with a
  full spec, the examples ramp formula *tightened*, and a measured pace
  drop recorded plainly (4.68 closures/day, down 41%, with both active
  physics fronts in multi-attempt spirals).
- **03:00 review (this one):** the dirty tree disposed of and committed;
  one audit PASS; the `PORT-16` stable-ID collision fixed (the ladder
  entry becomes `PORT-17`); six rulings; `TH-15` step 2h, `WF-6` step 4f,
  `ANS-2` step 1 and `OPS-42` scoped; **the queue refilled with five
  independent items**, restoring throughput.

## Automation health

- **Eight of eight scheduled slots fired and journaled** — but only five
  did chunk work. **The 09-08 18:00 daily review never ran** (146-byte
  launcher log, the usage-credit tell), and since it is the only session
  that refills the queue, the 21:00, 22:30 and 00:00 slots were lost to
  it. That is the interval's single largest cost and it is Waiting-on-you
  item 4. Everything else fired: the 02:15 weekly (22 min) and this
  03:00 review both landed.
- First-run streak **56 of 56** over the slots that fired since 09-03
  18:00. Container Up 5 days continuously; the XL service Up ≈ 31 h,
  **still never used by any slot**.
- **Foreground-executor rule: held on all five working slots** (21 since
  the break). No docker-socket denial (0 of the last 56); no allowlist
  denial; no compute-safety event; no wedge.
- Standing rule (g) (`-s` on every pytest window) held everywhere; no
  window was lost to swallowed prints this interval.
- Tier labels all honest: 4e smoke by measurement (130 s at 1 rank);
  `GEO-28` standard (30 s); step 5b heavy by ceiling, 316 s; 2g heavy,
  386 s; `GEO-29` heavy by ceiling, 145 s. Every window inside both its
  container timeout and the host window.
- **Housekeeping:** the weekly's rotation took `attempts.md` 18 218 →
  15 056 lines and the plan 10 311 → 8 976 — both still over budget and
  both structurally unable to reach it while two open chunks carry
  thousand-line live narratives. 1 251 logs. The example census still
  reads `stale=81` covering 40 of 47 examples; this review ruled the 48 h
  threshold is measuring the run cadence rather than staleness, and
  queued the fix (`OPS-42`, item 5).

## On deck (§9 — five ordinary items, all independent, plus the held XL item)

1. **`ANS-4` step 2a** — the four degree-1 conductor rungs at 128 MHz on
   the ordinary service: the Larmor discriminator's cheap half, now that
   the module is on `main`. Asserts only imported bands plus the control
   that each finer rung actually refines; prints the S entries and the
   h→0 fit for a review to rule on privately. Carries the mandatory
   re-run of the two gate modules last night's keywords touched
   *(implementer; two heavy windows, 4 ranks)*
2. **`TH-15` step 2h** — is the gap cell tag a half-domain? Its meshed
   volume against two CAD candidates that differ by a factor 2, so a 5%
   assertion decides it; no solve *(mesh-probe, foreground; ≈ 30 s at
   2 ranks)*
3. **`WF-6` step 4f** — the `h`-ladder: the field's C4 four-copy spread
   across three mesh rungs, against the mesh's own 0.1% floor, with the
   cw drive (95%) as the asserted negative control. Predicted to fall,
   never asserted to — and a spread that does *not* fall is the more
   informative result *(implementer; one heavy window, 4 ranks, ≈ 250 s)*
4. **`ANS-2` step 1** — the runnable half of the coil-driven SAR
   benchmark, scoped to the pointwise-SAR, phantom-power and metadata
   rows that adjudicate; mass-averaged rows held for a step 2 because of
   the sphere-vs-cube systematic *(implementer; one heavy window, 4 ranks
   + a census)*
5. **`OPS-42`** — the corpus census's 48 h staleness window moved to 14
   days, with the stale set recomputed independently as the anchor and a
   deliberately backdated artifact as the negative control *(implementer;
   smoke, 1 rank)*
6. **`ANS-4` step 2b (`xl`)** — **held**: cannot run headless
   (Waiting-on-you item 1); slots skip it unmarked

Items 1–5 are independent and touch disjoint files, so the four slots
before the next review can take them in order without waiting on each
other's results.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
