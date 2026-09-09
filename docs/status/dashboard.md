# FEM-EM Solver — status

**Updated:** 2026-09-09 10:30 daily review. Headline: **four slots, four
honest results, and zero new ✅ — which is the system working, not stalling.**
The interval's real finding is that two *different* refinements of the *same*
birdcage fixture broke its four-fold symmetry on the same day. Refining the
conductor mesh pushed the S-matrix class spreads from 0.10% to 1.69% past a
0.5% gate; refining the *global* mesh split the power-balance residual between
the two ports — identical to five figures on the two coarser meshes, then
1.85% vs 1.42% on the finest. Two axes, one fixture, one symptom. That fixture
is load-bearing for **both** open fronts (the 64/128 MHz S-parameter
discriminator and the B₁⁺ convergence question), so every finer mesh of it is
untrustworthy until this is measured, and the next run is a **no-solve
geometric census** that both blocked items had independently asked for.
Elsewhere the news is good: the B₁⁺ mesh ladder **ran to completion** and
produced the measured convergence statement the roadmap was waiting for — the
field's four-fold spread falls 5.25% → 2.07% → 1.95%, so mesh coarseness owns
about 60% of the effect and then stops, leaving ~2% that belongs to the
formulation rather than the mesh. And the coil-driven SAR benchmark's runnable
half landed green, which is the first construction that can attack an
*absolute* SAR claim. **Still a self-consistency story at the Larmor
frequencies: no absolute SAR, no C95.3 compliance figure, no homogeneity, no
Larmor coil accuracy claim, no resonance or tuning claim, no closed-form B₁⁺
claim, and no solve has touched the human-scale mesh.** Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. 🟠 **`TH-11` step 5d attempt 2 is running — fill its ledger row when it
   returns.** You have already handled the hard part; this is the residue.
   Attempt 1 (09:55) was killed on the wrapper side at ≈ 40 min with **eight
   ranks left running on 260 GiB with nothing reading their output**, you
   diagnosed and fixed it as `OPS-43` at 10:48, and attempt 2 relaunched at
   10:39 with the redirect fix. **What is left:** when it returns (its
   `timeout -k 60 7200` puts the latest possible finish at **12:39**), fill
   the last four columns of **both** `docs/testing/xl-ledger.md` rows from the
   footers — ranks, cells, peak memory, elapsed, readout — and stop the XL
   service. *(Attempt 1's row stays and stays blank-ish by design: §5.1 counts
   a killed XL run as having spent the slot, so the row is the honest record
   of a spent window that produced nothing.)* **One reading note so the next
   person does not repeat this review's 20 minutes of uncertainty:** attempt
   2's harness log stays ≈ 2 KB and static until the run finishes, because the
   fix buffers output to a file inside the container — **size and mtime now
   say nothing about liveness, and only the footer settles it.** *What is
   known so far:* the third rung **meshed** — 2 808 204 cells, 173.3 s at 8
   ranks, 5.03 cells per skin depth at 64 MHz — which is already more than
   step 5 ever achieved against the old 64 GiB ceiling. No result has been
   read from either log and none is claimed. The ruling on what it means is a
   review's, not the run's: even the favourable branch only makes §2.1's
   "coil-at-Larmor is an extrapolation" caveat *revisitable*, it does not
   move it.
2. 🟠 **Newly eligible for an AED session: `ANS-2` step 3 — coil-driven SAR
   in the loaded four-leg birdcage at 10 MHz.** The blocker named last
   interval is gone: our runnable half now **exists and ran green**
   (09:00 slot, 233 s at 4 ranks), so an AED session would not be wasted.
   The spec deliberately reuses your `ANS-4` HFSS project — same geometry,
   materials, ports and boundary condition; one frequency, plus a phantom
   mass density (1000 kg/m³) and a field-calculator export
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`).
   Worth reading its "which rows adjudicate" section first: our averaging
   ball is a sphere and IEC 62704-1's is a cube, so the mass-averaged rows
   carry a known systematic and the **pointwise SAR and phantom power** are
   the rows that decide — those are exactly the rows we shipped. **One thing
   to carry into the comparison:** our drive is 1 V behind 50 Ω, i.e. 5 mW
   incident, against HFSS's default 1 W. We print both explicitly and rescale
   **nothing**; do not match the normalisation silently on either side.
3. 🟢 **`ANS-4` step 2b — done, no action, and it produced a finding about
   the tiering rather than the physics.** You ran it interactively at 09:44:
   Status 0, 249 s, 14 passed / 1 skipped, and degree 2 moves the three C4
   classes of S at 128 MHz by 6.09 / 5.38 / 6.70% off the degree-1 record,
   with the degree-2 class spreads *tighter* than degree-1's. The pre-registered
   red did not need to be forgiven. **The finding:** it measured ~16.6 GiB
   against a predicted ≳ 49 GiB — an eighth of the *ordinary* service's own
   128 G limit — so the case never needed the XL tier at all and the item's
   pricing was arithmetically wrong. Recorded in the ledger with an honest
   note that the 16.6 GiB is a `docker stats` reading, not an instrumented
   peak.
4. 🟠 **A structural gap worth your ruling, referred to the 09-13 weekly.**
   An XL window is allowed 7200 s; a scheduled implementer slot is killed at
   65 minutes. **So no scheduled slot can ever run an XL item to its footer** —
   which is why both XL items so far have been held for you, and why item 1
   above exists at all. XL runs are effectively launchable only from your
   interactive sessions, and "who reads the footer" currently has no owner in
   any protocol. This review named it rather than patching around it, because
   §5.1 is the weekly review's to change. No action needed now; the weekly
   will propose something.
5. 🟡 **Agent-definition edits — still pending, still less urgent.** The
   foreground rule has now held on twenty-five consecutive spawns with the
   rule carried verbatim; the five one-liners (two for `example-runner.md`,
   one for `mesh-probe.md`, one for `implementer.md` — rule (d) — and rule (e)
   for both) would make the workaround unnecessary. Say which you want and an
   interactive session applies them. *(Related: `implementer.md` is the one
   agent file with no "Last verified against" footer, and it is the
   most-invoked of the seven.)*
6. 🟢 **Session-limit watch — quiet this interval, mitigation working.** All
   four implementer launchers fired and ended `exit=0`, and this review's
   launcher logged its model choice as designed (`review-model override
   active until 2026-09-11: claude-opus-5`). The override in
   `scripts/automation/review-model.env` is **dated and self-expiring**, so
   nothing has to be remembered to revert it. No action unless you want the
   window extended past 09-11.
7. 🟢 **`ANS-3` AED run** — still on your AED queue, now behind `ANS-2` step 3
   (item 2), which is the higher-value case. Same low-order rule, same
   private-results handling; the tracked table's AED cells stay blank by
   construction.
8. **Information — automation fix from the 08-30 10:30 review, still awaiting
   your OK:** `docs/automation/weekly-review.md` has a commit-first checkpoint
   (rotation committed before plan edits). Revert only if you want the
   single-commit form.
9. **One click: does ParaView open a DG1 `.bp`?** (unchanged since 2026-08-12;
   `scripts/probes/post4_step5_probe.py` regenerates.)
10. FYI, no action — physics worth a glance. **(a)** The B₁⁺ mesh ladder is
   the interval's most useful result and it is a *partial* yes. Refining the
   air mesh three times drops the field's four-fold asymmetry 5.25% → 2.07% →
   1.95%: the second rung buys most of it and the third buys almost nothing,
   stalling an order above the mesh's own 0.1% symmetry floor. So roughly 60%
   of the discrepancy was mesh coarseness and the surviving ~2% is not — it
   belongs to the first-order element or to the way we project the curl. That
   is a narrower and more honest position than "the mesh is probably too
   coarse", and it is exactly the input the 09-13 roadmap decision needs.
   **(b)** The symmetry story in the headline is worth one more sentence,
   because the tell was subtle: the power-balance residual is not just larger
   on the finest mesh, it stopped being *equal between the two ports*. Two
   ports that are identical by construction agreeing to five figures and then
   disagreeing by 30% is a geometry symptom, not a physics one — which is why
   the next run measures leg cell counts and port sheet areas and solves
   nothing at all. **(c)** On the PEC-hole port, the factor-2 puzzle is
   settled: the gap's cell tag really is exactly half its CAD box, because the
   mesh generator splits each gap box at its mid-plane and its own docstring
   says a caller must take both halves. The fix is now specified — and
   deliberately written as an *additive* option that leaves today's behaviour
   untouched, so that correcting the factor cannot quietly move a gated
   number in the same commit that introduces it. Local `main` remains well
   ahead of origin (push is manual).

## Honest current state (digest of §2 — **unchanged this interval: no gate changed hands, and no status marker moved at all**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first hole port solved, loss-free to the bit; the driven-port displacement current is on `main`** (`TH-15` steps 1, 2a, 2d, 3a ✅; step 2 proper parked on a 2% `Z` asymmetry that is now *measured* to be the point-sampled gap-voltage reading, step 2f) — every conductor in a *solved* coil fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%). Two-torus hole 161 461 cells, `max \|Re Z_ij\|/\|Z_ij\| = 0` exactly, mutual on the ratified inner-edge comparand **0.989641 inside the unmoved 10%** (gated, step 2f), symmetrised-S identity 4.4e-16, raw-S unitarity 7.5e-3 (red, unmoved). The **half-domain factor 2 is now settled** (step 2h 🧪): `V_tag`/box = 0.500000 exactly, the generator's own documented mid-plane split. Item 2 (step 3) spends it **additively** — new optional selection, default unflipped, no gated digit moves. `TH-14` (copper) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR 0.2747% against the filament form, 0.3895% against the finite-wire-corrected form, 418 888 cells (`MAT-6` ✅); `ANS-1` AGREE (numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅). Larmor coil loading stays an extrapolation. `TH-11` step 5d (the 2.81 M-cell 64 MHz rung) has run twice on the XL service 09-09: attempt 1 (09:55) was **killed at ≈ 40 min, orphaned, no footer, no result**; attempt 2 (10:39) was in flight at this review. **Nothing is claimed from either**, and even a favourable footer only makes §2.1's extrapolation caveat *revisitable* — the ruling is a review's |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only**; externally **AGREE at 10 MHz, inconclusive at 64 / 128 MHz** (`ANS-4`, private). Both halves of the discriminator have now run: degree-2 moves the three C4 classes by 5.4–6.7% (step 2b, operator-interactive), while the degree-1 **conductor ladder does not exist as specified** — the ×0.75 rung fails the imported 0.5% spread band at 1.69% (step 2a, known-issues 🔴). `GEO-30` (item 1) measures why, with no solve. 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%. **RLC sheets exist, not gated** (`PORT-14` 🟡); the circuit layer's algebra gated at 1e-12 (`PORT-15` step 1 ✅) |
| Multi-port drive | ✅ **package-level, gated on the 4-leg identities and on the exact power identity** (`POST-6` step 1, `PORT-16` ✅, audited PASS); shown by `ports:13` (`EX-49` ✅) | quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087%, linearity 1e-12; `P_src,exact = P_vol + P_sheet,exact` at 5.9e-15 / 1.4e-14 on the superposed drive |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; F-human (0.15 m) gated on CAD identities (`GEO-25` ✅), shown by `mesh:12` | 4-leg record 111 898 / 116 085 (ports) / 80 181 as a hole; 16-leg 270 728; F-human 504 642 cells — **a mesh, never solved; 64 MHz cost unpriced**. Phantom 1 g rung 199 920 / 58 866 cells asserted as version-tagged records at the imported 1% band (`MAT-4` step 5b ✅). Global air resolution priced (`GEO-29` 🧪): 116 085 → 281 728 cells, interior mean cell 2.19 → 1.07 cm. **New and open:** the fixture's C4 symmetry under refinement is in question on *both* axes — `GEO-30` (item 1) censuses it, no solve |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; the closed-form gate stays **set aside** (the image-lattice comparand's wall residual converges to a non-zero ≈ 3.4%, step 4e) — nothing widened: `CLOSED_FORM_BAND` 5.0e-2, `WALL_NORMAL_BAND` 1.0e-2, `IMAGE_ORDER` 3 unmoved on `main`. **The convergence question is now answered by measurement** | `WF-6` steps 1–2b, 4a ✅; 4b, 4d, 4e, 4f parked. Step 4f's `h`-ladder ran to completion: the C4 four-copy spread falls **5.2506% → 2.0719% → 1.9514%** (ratios 1.0000 / 0.3946 / 0.3717) and then stalls an order above `GEO-28`'s ≈ 0.1% mesh floor — refinement owns ≈ 60% of the effect, and the residual ≈ 2% is the degree-1 solve's or the CG1 `curl E` estimator's, not `h`'s. Two anchors were RED for **pre-registration** errors (a four-copy spread compared against a two-copy record; a 10× control bar whose arithmetic ceiling was 9.53×), both re-registered by this review off measured numbers; the third red — a power residual that *degrades* on the finest rung — is a real finding and that rung is **dropped from the ladder** rather than absorbed (item 3). Still **no homogeneity, absolute, closed-form or tuning claim** |
| Coil-driven SAR | ✅ **mass-averaged 1 g *and* 10 g, C4-gated on one fixture at 10 MHz at fixed `h`** (`MAT-4` ✅); shown by `mri:3` (`EX-53` ✅) | 10 g C4 pairs 0.3303 / 0.0756 / 0.0574 / 0.3132% on the 7.5 mm rung and 0.0309 / 0.0060 / 0.0394 / 0.0644% on the 2.5 mm rung; the 1 g pairs 0.0957 / 0.1199 / 0.1305 / 0.1065% asserted at the same unmoved 5% band (step 5b ✅, audited PASS), mis-paired control 87.0%; whole-phantom identity 8.1e-14. **`ANS-2` step 1 ✅ this interval** reproduces all eight pairs to the digit inside a benchmark example, with incident power printed against HFSS's 1 W and **nothing rescaled** — the runnable half only. **No absolute SAR, no C95.3 compliance or limit figure, no Larmor, no convergence claim** |
| SAR, imposed field | ✅ lossy sphere 3.5% (`MAT-4` step 1); its example `mat:2` (`EX-52` ✅) | — |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 4 deliberate/known** (unchanged); example-artifact census `dead=0 guide=0 stale=87 exit=2`, 47 examples | API sweep `violations=0`; `OPS-40` ✅ guards the collective. Three open known-issues entries (`WF-6` step 4, `TH-15` step 2, `ANS-4` step 2a), each carrying its 2026-09-09 ruling row; the first and third are now **formally the same question**, with `GEO-30` as the shared next measurement. `stale=87` has risen from 81 — `OPS-42` (item 5) moves the 48 h window that is measuring run cadence rather than staleness |

## Recent activity (2026-09-09 03:00 → 10:30)

- **04:30:** `ANS-4` step 2a — **executed negative.** The mandatory re-run of
  the two gate modules your 01:58 keywords touched is **green** (22 passed),
  so those defaults are now verified by execution rather than inspection. But
  the ladder itself does not exist as specified: refining
  `conductor_resolution` to ×0.75 moves the S-matrix class spreads from
  0.10 / 0.09 / 0.07% to 0.54 / 0.46 / **1.69%** past the imported 0.5% gate.
  Reciprocity (1e-15) and passivity (0.9989) are untouched, which points at
  the *mesh's* symmetry rather than the solve. The item's own clause fired:
  the second window was not run and nothing was fixed in-slot.
- **06:00:** `TH-15` step 2h (mesh probe) — **CONFIRMED, and exactly by
  design.** The gap cell tag is precisely half its CAD box (0.500000, with the
  `z` extent half and `x`, `y` full); the third candidate turned out not to be
  a guess at all — the generator splits each gap box at its mid-plane and says
  so in its own docstring. Two windows, ~57 s each, character-identical, no
  solve. This unblocked the solver-side specification.
- **07:30:** `WF-6` step 4f — **the `h`-ladder ran to completion**, all three
  rungs, 453 s at 4 ranks. The spread falls 5.25% → 2.07% → 1.95% and stalls.
  Three asserted anchors came back red; this review found two of them to be
  errors in the *pre-registration* (including a control bar whose arithmetic
  ceiling made it unreachable) and one to be a genuine new finding. Code
  parked; no band was moved and none was re-introduced.
- **09:00:** `ANS-2` step 1 — **complete and green**, 233 s at 4 ranks. The
  coil-driven SAR benchmark's runnable half, reproducing `MAT-4`'s eight C4
  pairs to the digit, coverage identity at 7.8e-14 against 1e-10, mis-paired
  control ≈ 17× the band. AED columns verbatim blank. Closes the runnable
  half only.
- **09:13–10:49, your interactive session:** `ANS-4` step 2b run on the XL
  service (Status 0, 249 s) with the **mis-tiering finding**; the dated
  self-expiring interval override written; `TH-11` step 5d commissioned and
  launched at 09:55 as the tier's genuinely memory-bound case; that window
  **killed and orphaned at ≈ 40 min**, diagnosed, and the three long-window
  defects landed as `OPS-43` at 10:48 with attempt 2 relaunched at 10:39.
- **10:30 review (this one):** no audit owed — **no chunk status moved this
  interval**, which is itself the finding. Three rulings banked: the two reds
  are one question and get one no-solve census (`GEO-30`, new); the `TH-15`
  solver fix is specified *additively* so it cannot move a gated digit; and
  `WF-6`'s two mis-specified anchors are re-registered off measured numbers
  while the real red is scoped **out** of the ladder rather than absorbed.
  Queue refilled with four independent items — fewer than the usual five, and
  said so rather than padded.

## Automation health

- **Four of four scheduled slots fired, ended `exit=0`, and all four did
  chunk work** — the first full interval since the 09-08 drain. First-run
  streak **60 of 60** since 09-03 18:00.
- **Foreground-executor rule: held on all four working slots** (25 since the
  break). No docker-socket denial; no allowlist denial; no compute-safety
  event; no container wedge. Standing rule (g) (`-s` on every pytest window)
  held everywhere.
- Tier labels honest on every window: 2a heavy by ceiling (205 s + 132 s),
  2h standard (~57 s), 4f heavy by ceiling (453 s), `ANS-2` step 1 heavy by
  ceiling (233 s). Every window inside both its container timeout and the
  host window.
- **The model override is working as designed:** this review's launcher log
  records `review-model override active until 2026-09-11: claude-opus-5`. It
  expires by date on its own.
- **One compute-safety event, outside the slots, and it was caught and fixed
  inside the hour.** The 09:55 XL window was killed on the wrapper side at
  ≈ 40 min while eight ranks kept running at ≈ 85% CPU on 260 GiB with nothing
  consuming their output. This review saw the symptom (a footerless, static
  log against a sustained ~6.0 host load) and correctly refused to read a
  result from it, but a scheduled session cannot inspect the XL container —
  `docker stats` is denied by the allowlist and `docker exec` by the guard
  hook, both correctly. You diagnosed and fixed it as `OPS-43` at 10:48: a
  long window must survive its own client, so container-side output is
  redirected to a file and echoed back rather than piped (`tee` takes
  `SIGPIPE` when the client dies and kills the run with it). Two rules added
  to CLAUDE.md. **The standing gap remains Waiting-on-you item 4:** no
  scheduled session can witness an XL footer, and a killed XL run still spends
  the week's slot.
- **Housekeeping:** 1 258 logs. The example census now reads `stale=87` across
  47 examples, up from 81 — which strengthens rather than weakens the case for
  `OPS-42` (item 5). Plan and attempts files remain over budget; the next
  rotation is the weekly's.

## On deck (§9 — four ready items, all independent, plus the operator's XL run held last)

1. **`GEO-30`** — does the four-port birdcage fixture stay C4-symmetric when
   you refine it? One geometric census across **both** refinement axes: leg
   and quadrant cell counts, quadrant volumes and port sheet areas at the
   conductor rungs ×1 / ×0.75 and the global rungs 0.015 / 0.012 / 0.0095.
   Anchored on reproducing `GEO-28`'s 0.1% and the 116 085-cell record, with
   a mis-paired-quadrant negative control at ≥ 10×. **No solve.** Answers the
   unblock condition of *both* red items above *(mesh-probe, foreground;
   one window, 2 ranks)*
2. **`TH-15` step 3** — spend the factor 2: an **additive** both-halves gap
   selection whose default is not flipped, so no gated digit can move.
   Asserts the geometric identity (0.500000 → 1.000000 against the CAD box)
   and prints `V̄`, the mutual and reciprocity computed both ways, which is
   what a review flips the default from *(implementer; one window, 4 ranks,
   plus two re-run windows)*
3. **`WF-6` step 4g** — the same ladder with the two mis-specified anchors
   re-registered on statistics that exist (the four-copy spread's own 5.2506%;
   the cw bar re-sized to ≥ 5× off a measured 9.53× ceiling), over the **two**
   rungs that are trustworthy. The finest rung is dropped, not widened —
   its power residual is under diagnosis at item 1 *(implementer; one heavy
   window, 4 ranks, ≈ 300 s)*
4. **`OPS-42`** — the corpus census's 48 h staleness window moved to 14 days,
   with the stale set recomputed independently as the anchor and a
   deliberately backdated artifact as the negative control *(implementer;
   smoke, 1 rank)*
5. **`TH-11` step 5d (`xl`)** — **yours, held, never takeable headless**:
   attempt 1 killed and orphaned at ≈ 40 min, attempt 2 relaunched 10:39 and
   in flight; headless slots skip it (Waiting-on-you item 1)

Items 1–4 are independent and touch disjoint files, so the four slots before
the 18:00 review can take them in order without waiting on each other's
results. This is **four items rather than the usual five, stated rather than
padded**: the two chunks blocked this interval are both waiting on item 1's
*measurement*, and rescoping them before it reports would be inventing work.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
