# FEM-EM Solver — status

**Updated:** 2026-09-09 18:00 daily review. Headline: **the interval's big
result came from your XL session, not from a slot — the 64 MHz coil rung that
has been "unaffordable on this box" since August ran to completion.** It gives
a convergence bracket that overlaps the 10 MHz and 30 MHz ones, which is the
pre-registered signature that the apparent eddy→displacement trend was mesh
coarseness all the way up to Larmor. **This review deliberately did not move
the §2 claim on it** — that sentence belongs to the 09-13 weekly, and three
honest caveats stand in the way. In the slots, four for four: the B₁⁺ mesh
ladder **landed on `main`** with both re-registered anchors green (spread
5.25% → 2.07%), the geometric census came back with a *negative* that is more
useful than a positive would have been, one ops threshold closed ✅, and one
item was correctly stopped rather than fudged. The census's negative is the
thing to read: the birdcage mesh is **not** the reason two different
refinements broke its four-fold symmetry — masses and port-sheet *areas* stay
symmetric everywhere — but the port sheets' *triangulation* splits into
exactly the same two-fold pattern on exactly the two meshes that failed. Same
surface area, different cut. That is the next run, and it solves nothing.
**Still a self-consistency story at the Larmor frequencies: no absolute SAR,
no C95.3 compliance figure, no homogeneity, no Larmor coil accuracy claim, no
resonance or tuning claim, no closed-form B₁⁺ claim, and no solve has touched
the human-scale mesh.** Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

## Waiting on you

1. 🟠 **Ready for an AED session: `ANS-2` step 3 — coil-driven SAR in the
   loaded four-leg birdcage at 10 MHz.** *(Carried from last interval,
   unchanged and still the highest-value thing on your queue.)* Our runnable
   half exists and ran green, so the session would not be wasted. The spec
   reuses your existing `ANS-4` HFSS project — same geometry, materials,
   ports and boundary condition; one frequency, plus a phantom mass density
   (1000 kg/m³) and a field-calculator export
   (`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`). Read
   its "which rows adjudicate" section first: our averaging ball is a sphere
   and IEC 62704-1's is a cube, so the mass-averaged rows carry a known
   systematic and the **pointwise SAR and phantom power** are the rows that
   decide. **One thing to carry into the comparison:** our drive is 1 V behind
   50 Ω, i.e. 5 mW incident, against HFSS's default 1 W. We print both and
   rescale **nothing**; do not match the normalisation silently on either
   side.
2. 🟠 **Your `TH-11` step 5d run succeeded, and it puts a §2 sentence in
   play — but the ruling is the 09-13 weekly's and this review left it
   alone.** The 2 808 204-cell 64 MHz rung solved: Status 0, 4838 s at 8
   ranks, 263.4 GiB peak, 17 passed / 1 skipped. The ladder reads **+10.27%
   → +2.81% → +0.38%** and the two-rung bracket **[−2.04%, −0.43%]**
   overlaps both the 10 MHz and 30 MHz brackets. §2.1 currently says a gated
   64 MHz bracket "requires either more memory or an out-of-core solver,
   neither scoped" — more memory arrived, so that premise is now measured
   false. **What this review did:** added a dated pointer under that bullet
   recording the measurement and naming the weekly as its owner, so no reader
   takes the paragraph as current; it did **not** rewrite the claim. **No
   action from you** — you already assigned it correctly in `f5071f6`. The
   three caveats the weekly has to weigh are in your own commit message and
   are not glossed anywhere.
3. 🟢 **`ANS-4` step 2d runs itself tonight at 02:00 — no launch needed, and
   only the ledger row is owed afterwards.** Since `b4fffa3` the XL window is
   driven from cron via `scripts/automation/xl-run.sh` reading
   `scripts/automation/xl-queue.env`, which is loaded with the full command
   (four rungs `0.015:1 0.015:2 0.0075:2 0.005:2`, `-n 16`, 7200 s, durable
   capture, progress reporting on) and is cleared by the launcher afterwards
   so it cannot silently repeat. It is due by 2026-09-10 15:50Z, inside the
   dated override. **What is left for you:** fill the ledger row's last four
   columns from the footer, commit them with the log, stop the service — and
   **never write an AED number**; the verdict is the weekly's, in
   `docs/private/`. *(If the 02:00 log comes back footerless, tell the 03:00
   review — a queued §9 item is explicitly told to stand off that module in
   that case.)*
4. 🟡 **Agent-definition edits — still pending, still less urgent.** The
   foreground rule has now held on twenty-nine consecutive spawns with the
   rule carried verbatim; the five one-liners (two for `example-runner.md`,
   one for `mesh-probe.md`, one for `implementer.md` — rule (d) — and rule
   (e) for both) would make the workaround unnecessary. Say which you want
   and an interactive session applies them. *(Related: `implementer.md` is the
   one agent file with no "Last verified against" footer, and it is the
   most-invoked of the seven.)*
5. 🟢 **Session-limit and model watch — quiet again.** All four implementer
   launchers fired and ended `exit=0`, and this review's launcher logged
   `review-model override active until 2026-09-11: claude-opus-5` as
   designed. The override in `scripts/automation/review-model.env` is dated
   and self-expiring, so nothing has to be remembered to revert it. No action
   unless you want the window extended past 09-11.
6. 🟢 **`ANS-3` AED run** — still on your AED queue, behind `ANS-2` step 3
   (item 1), which is the higher-value case. Same low-order rule, same
   private-results handling; the tracked table's AED cells stay blank by
   construction.
7. **Information — automation fix from the 08-30 10:30 review, still awaiting
   your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert only if you want
   the single-commit form.
8. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
9. FYI, no action — three things worth a glance. **(a)** The B₁⁺ ladder is now
   **on `main`**, not on a branch: refining the air mesh drops the field's
   four-fold asymmetry 5.25% → 2.07% at unmoved bands, so roughly 60% of it
   was mesh coarseness and the surviving ~2% is the first-order element, the
   way we estimate the curl, or the port sheet. That is the measured
   convergence statement the 09-13 roadmap decision needs, and it is handed
   to that review rather than converted into a gate here. **(b)** The
   symmetry census is a good example of a negative result paying for itself.
   It set out to find an asymmetric mesh and did not: conductor masses agree
   to 0.33% and the four port-sheet *areas* to fifteen decimal places, at
   every refinement. But the sheets' *facet counts* — how many triangles each
   is cut into — read 58/58/58/58 and 62/62/62/62 on the two meshes that
   behaved and **80/74/80/74** and **70/76/70/76** on the two that broke:
   opposite ports equal, adjacent ports differing, the exact pattern both
   failures show. Four surfaces of identical area, cut differently. **(c)**
   The PEC-hole factor-2 fix is written, green, and deliberately **not** on
   `main` yet: the measurement confirmed both gap halves sum to the CAD box
   exactly, and the change is additive so today's behaviour cannot move — but
   the mandatory re-run that proves that turned out to need windows longer
   than a scheduled slot can hold, so the code is parked until the cheaper
   re-tiering is tried. Local `main` remains well ahead of origin (push is
   manual).

## Honest current state (digest of §2 — **one bullet gained a dated pointer this interval; no capability claim moved**)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; h-refinement gate passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere (`TH-12` ✅). The coil's two degree-2 identity reds stay open at 3.8990e-09 / 3.7235e-09 vs 1e-9 |
| Conductor model | 🟡 **first hole port solved, loss-free to the bit** (`TH-15` steps 1, 2a, 2d, 3a ✅) — step 2 proper parked on a 2% `Z` asymmetry now *measured* to be the point-sampled gap-voltage reading (step 2f); every conductor in a *solved* coil fixture is still a solved-inside volume with σ capped by the mesh (800 S/m) | PEC sphere as a hole: β = 1.019746 vs 1 (1.97% against 4.886%). Two-torus hole 161 461 cells, `max \|Re Z_ij\|/\|Z_ij\| = 0` exactly, mutual on the ratified inner-edge comparand **0.989641 inside the unmoved 10%**, symmetrised-S identity 4.4e-16, raw-S unitarity 7.5e-3 (red, unmoved). **Step 3's measurement is green** — both gap halves sum to the CAD box, ratio 0.500000 → **1.000000**, summed/single **2.000000000** — but the change is **parked, not landed**: its mandatory re-run needs windows longer than a scheduled slot can hold (§9 item 3 re-tiers it). Default unflipped; no gated digit has moved. `TH-14` (copper) → `ANS-6` serial on it |
| Coil loading | ⚠️ eddy-current regime only — **and the "no affordable 64 MHz rung" premise is now measured false; the sentence itself is the 09-13 weekly's to move** | Dodd–Deeds ΔR 0.2747% against the filament form, 0.3895% against the finite-wire-corrected form, 418 888 cells (`MAT-6` ✅); `ANS-1` AGREE (numbers private); finite-wire term +0.115% on ΔR (`MAT-8` ✅). **`TH-11` step 5d solved the 2 808 204-cell 64 MHz third rung on the 512 GiB XL service** — Status 0, 4838 s at `-n 8`, peak 263.4 GiB, 17 passed / 1 skipped: ladder **+10.2698% → +2.8063% → +0.3824%**, three-rung fit p = 1.623, two-rung bracket **[−2.0415%, −0.4256%]** overlapping the 10 MHz [−2.15, −0.91] and 30 MHz [−3.37, −0.38]. §2.1 carries a dated pointer, not a rewrite: Dodd–Deeds is quasi-static and is the *comparison* at 64 MHz, the two-rung `p_eff` 2.876 disagrees with the three-rung 1.623, and `d₀` sits just outside the 10 MHz bracket. **Larmor coil loading is still labelled an extrapolation until a review says otherwise** |
| S-parameters / ports | ✅ 4-leg birdcage gated at 10, 64 and 128 MHz; 16-leg / 32 ring ports: the full 32×32 at 10 MHz | 4-leg: reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5% — **self-consistency identities only**; externally **AGREE at 10 MHz, inconclusive at 64 / 128 MHz** (`ANS-4`, private). Both halves of the discriminator have run: degree 2 moves the three C4 classes by 5.4–6.7% (step 2b), while the degree-1 conductor ladder **does not exist as specified** — the ×0.75 rung fails the imported 0.5% spread band at 1.69% (step 2a, known-issues 🔴). `GEO-30` measured why *not*: the mesh is symmetric in mass and in sheet area at every rung. `GEO-31` (item 1) now reads the sheet triangulation. The matched-Ansys rung `ANS-4` step 2d runs from cron at 02:00. 16-leg (`PORT-13` step 3): 32×32 reciprocity 5.4e-13, 18 classes ≤ 0.44% vs 5%. **RLC sheets exist, not gated** (`PORT-14` 🟡); circuit algebra gated at 1e-12 (`PORT-15` step 1 ✅) |
| Multi-port drive | ✅ **package-level, gated on the 4-leg identities and on the exact power identity** (`POST-6` step 1, `PORT-16` ✅, audited PASS); shown by `ports:13` (`EX-49` ✅) | quadrature weights reproduce `WF-6`'s C4 0.9818% / mirror 0.8087%, linearity 1e-12; `P_src,exact = P_vol + P_sheet,exact` at 5.9e-15 / 1.4e-14 on the superposed drive |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated; F-human (0.15 m) gated on CAD identities (`GEO-25` ✅), shown by `mesh:12` | 4-leg record 111 898 / 116 085 (ports) / 80 181 as a hole; 16-leg 270 728; F-human 504 642 cells — **a mesh, never solved; 64 MHz cost unpriced**. Phantom 1 g rung 199 920 / 58 866 cells asserted as version-tagged records (`MAT-4` step 5b ✅). Global air resolution priced (`GEO-29` 🧪). **`GEO-30` 🧪 answers the C4-under-refinement question with a negative:** conductor masses ≤ 0.33% and gap-sheet areas to 1e-15 at all four rungs, mis-paired control 1043×. **One ungated lead:** gap-sheet facet counts go C2 (80/74/80/74, 70/76/70/76) on exactly the two rungs that broke — `GEO-31` measures it |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; the closed-form gate stays **set aside** (nothing widened: `CLOSED_FORM_BAND` 5.0e-2, `WALL_NORMAL_BAND` 1.0e-2, `IMAGE_ORDER` 3 unmoved). **The convergence question is answered by measurement, and the answer is on `main`** | `WF-6` steps 1–2b, 4a, **4g** ✅ (`49432f9`, `20260909T200431Z_WF-6.log`, Status 0, 204 s, 28 passed / 2 skipped). Two-rung ladder: four-copy C4 spread **5.2506% → 2.0719%** (ratio 0.3946) at unmoved bands, `size_global` 116 085 / 149 049 at ratio 1.000000, power residuals 9.796e-03 / 8.113e-03 (≤ 1e-2), C4 covariance 3.6159% / 1.6815% (≤ 5%), cw-vs-ccw separation 9.53× / 19.52× against a 5× bar re-sized off a measured 9.53× ceiling. 4f's third rung stays **out** (its symmetry defect was reproduced by `GEO-30` on a second quantity, not cleared). **Refinement owns ≈ 60%; the residual ≈ 2% is not `h`'s.** Still **no homogeneity, absolute, closed-form or tuning claim** |
| Coil-driven SAR | ✅ **mass-averaged 1 g *and* 10 g, C4-gated on one fixture at 10 MHz at fixed `h`** (`MAT-4` ✅); shown by `mri:3` (`EX-53` ✅) | 10 g C4 pairs 0.3303 / 0.0756 / 0.0574 / 0.3132% on the 7.5 mm rung and 0.0309 / 0.0060 / 0.0394 / 0.0644% on the 2.5 mm rung; the 1 g pairs 0.0957 / 0.1199 / 0.1305 / 0.1065% at the same unmoved 5% band (step 5b ✅, audited PASS), mis-paired control 87.0%; whole-phantom identity 8.1e-14. `ANS-2` step 1 ✅ reproduces all eight pairs to the digit inside a benchmark example, incident power printed against HFSS's 1 W with **nothing rescaled** — the runnable half only. **No absolute SAR, no C95.3 compliance or limit figure, no Larmor, no convergence claim** |
| SAR, imposed field | ✅ lossy sphere 3.5% (`MAT-4` step 1); its example `mat:2` (`EX-52` ✅) | — |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 5** — four deliberate/known plus one new record-staleness red | API sweep `violations=0`. The new red is `test_the_in_tree_exemption_cannot_silently_widen`: two `ans:` `metrics.json` were committed without being added to the pinned exempt set, which is exactly what that pin exists to make loud — `OPS-44` (item 2) re-pins it and retires the row. Example-artifact census now reads **`dead=0 guide=0 stale=0`** of 89 artifacts age-checked (`OPS-42` ✅ moved the window 48 h → 14 days; at the old window it was 88 stale across 56 of 63 guides). Eleven open known-issues entries in all; **four** of them are the live front and each carries its 2026-09-09 ruling row (`OPS-42`'s new red, `ANS-4` step 2a, `WF-6` step 4, `TH-15` step 2) |

## Recent activity (2026-09-09 10:30 → 18:00)

- **12:00:** `GEO-30` (mesh probe) — **executed, all three anchors green, and
  the answer is the negative one.** 133 s at 2 ranks, no solve. Conductor
  masses stay C4-symmetric to ≤ 0.33% at every rung and the four gap-sheet
  areas agree to 1e-15, so the mesh is **not** the mechanism for either
  failure; the mis-paired control read 1043× against a 10× bar. It handed
  back one ungated lead — the sheets' facet counts split C2 on exactly the
  two broken rungs — which is now `GEO-31`.
- **13:30:** `TH-15` step 3 — **the measurement is green and the item is
  correctly blocked.** Both gap halves sum to the CAD box (ratio 0.500000 →
  1.000000, summed/single 2.000000000), confirming the mechanism. But the
  mandatory re-run of the two importing gate modules turned out to be
  heavy-tier: both returned `Status 124` at 501 s with **no failure, only an
  undersized window**, and a 1200 s window is longer than a headless slot can
  hold. The slot stopped and parked rather than raise a timeout. Structural
  finding, not an overrun.
- **15:00:** `WF-6` step 4g — **complete and landed on `main`**, 204 s at 4
  ranks, first ladder run green. Both re-registered anchors and the re-sized
  control hold; every 4f number on the two kept rungs reproduces to the
  printed digit. The slot also declined to delete branches on an instruction
  that did not resolve against the branches that existed, and returned the
  disposition here — which was right, and is done below.
- **16:30:** `OPS-42` — **complete and green**, ✅, 7 s. The example-corpus
  staleness window moved 48 h → 14 days with the stale set independently
  recomputed as the anchor and a backdated artifact as an exactly-+1 negative
  control. The signal went from firing on 85% of the corpus to firing on 0%.
  It surfaced one unrelated red on `main` and journalled it rather than
  editing a record it did not own.
- **09:13–12:01, your interactive session:** `TH-11` step 5d attempt 2
  returned **Status 0 after 4838 s** — the first time that rung has ever
  solved — with both ledger rows filled including the killed attempt's, and
  the peak's attribution caveat recorded honestly. XL windows then moved to
  cron at 02:00.
- **18:00 review (this one):** one audit (`OPS-42`, **PASS**, evidence
  re-read independently). Four rulings banked: `GEO-30`'s facet-count lead
  becomes `GEO-31`; the ×0.0095 rung stays out of `WF-6`'s ladder because
  `GEO-30` reproduced its defect rather than clearing it; the stale artifact
  pin is re-pinned as a path set rather than replaced by a pattern
  (`OPS-44`); and `TH-15` step 3's rule-(c) evidence is **re-tiered, not
  waived**. Nine parked branches reduced to five, with the reachability
  argument recorded. Queue refilled to five takeable items, all independent.

## Automation health

- **Four of four scheduled slots fired, ended `exit=0`, and all four did
  chunk work** — the second full interval in a row. Foreground-executor rule
  held on all four (29 since the break). No docker-socket denial, no
  allowlist denial, no compute-safety event, no container wedge, no orphaned
  ranks. Standing rule (g) (`-s` on every pytest window) held everywhere.
- Tier labels honest on every window: `GEO-30` standard (133 s), `TH-15`
  step 3 heavy by ceiling (222 s + two 501 s timeouts that were the
  container-side `timeout -k 30` firing as designed), `WF-6` 4g heavy by
  ceiling (204 s), `OPS-42` smoke (7 s ×2).
- **The XL tier now launches itself.** `scripts/automation/xl-run.sh` runs the
  single queued window at 02:00 from cron with durable capture, and the
  launcher clears the queue file afterwards. That closes the *launching* half
  of the structural gap this review named last interval; **the reading half is
  still open** — no scheduled session can witness an XL footer, and a killed
  XL run still spends the week's slot. Referred to the weekly, unchanged.
- **Branch hygiene done, not deferred.** Nine `attempt/*` branches were
  audited against `main` and reduced to **five**. The four deleted
  (`TH-15-step2`, `WF-6-step4`, `WF-6-step4d`, `WF-6-step4f`) were each
  verified to be a strict ancestor or byte-identical subset of a branch that
  is kept; four log files that existed only on branches were landed on `main`
  first, so every citation in `known-issues.md` now resolves there.
- **Housekeeping:** 1 283 logs. The example census reads `stale=0` for the
  first time. Plan and attempts files remain over budget; the next rotation is
  the weekly's.

## On deck (§9 — five takeable items, all independent, plus the cron-driven XL window)

1. **`GEO-31`** *(mesh-probe, no solve; one window, 2 ranks, ≈ 135 s)* — do
   the four port gap-sheets have the **same triangulation** under the C4
   rotation, or only the same area? Sorted per-facet areas, facet-centroid
   and boundary-vertex sets under the 90° rotation map, at all four rungs.
   Anchored on reproducing `GEO-30`'s exact facet counts and 1e-15 area
   agreement, with a by-construction probe self-test as the control. Answers
   the surviving unblock condition of **both** red known-issues entries.
2. **`OPS-44`** *(implementer; smoke, 1 rank, ≈ 7 s)* — re-pin
   `COMMITTED_EXAMPLE_ARTIFACTS` to the five artifacts git tracks, clearing
   the one new red on `main` and retiring its known-issues row. Anchored on a
   set-equality identity against an independent re-derivation, not a count.
3. **`TH-15` step 3b** *(implementer; two windows, 4 ranks, ≈ 20 min)* —
   re-tier the parked change's mandatory re-run from `-n 2` to `-n 4` and
   land it if it holds. **Whether the modules fit at 4 ranks is itself the
   measurement**, and a second overrun is a finding, not a wasted slot.
4. **`OPS-43` (c)** *(implementer; smoke, 2 ranks)* — a per-run memory figure
   a second run in the same container cannot forge: summed `ru_maxrss`
   calibrated against a known allocation, with `memory.peak`'s inability to
   separate the two runs as the asserted control. Both existing XL ledger
   rows carry a memory caveat this removes for future runs.
5. **`OPS-43` (d) gate** *(implementer; smoke, 2 ranks)* — **the spare.**
   Prove the progress-reporting variable is inert on the result (bit-identity,
   not a tolerance) and visible only when set.
6. **`ANS-4` step 2d (`xl`)** — **not takeable headless and not owed to you
   either: it runs from cron at 02:00.** Only the ledger row is yours
   afterwards (Waiting-on-you item 3).

Items 1–5 touch disjoint files and can be taken in order without waiting on
each other's results. Item 4 carries one ordering note: it edits the module
tonight's 02:00 XL window reads, so it stands off if that window came back
without a footer.

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags this file until the next interactive
session republishes it.*
