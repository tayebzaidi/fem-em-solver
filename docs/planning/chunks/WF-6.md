# WF-6 — B1+ field mapping and homogeneity (CV)

 B1+ field mapping and homogeneity (CV) — **step 1 scoped 2026-08-29 10:30 review (§10 subgoal 4's first B1+ chunk): `\|B₁⁺\| = \|B_x + jB_y\|/2` on the loaded F-small birdcage at 10 MHz from the `PORT-9` single-drive field, gated on a three-way power accounting and C4 covariance of the map; see entry. Step 1 executed 2026-08-29 13:30 slot — the `post/` helpers landed and gate (i) closed at 9.80e-3 of supplied power (band 1e-2), gate (ii) **red at 8.65% against its 5% band** (known-issues), so the chunk is 🧪 and no B1+ claim exists. Step 1b executed 2026-08-29 19:30 — the CG1-projected estimator reads 2.19 / 2.11 / 1.89% at +90 / −90 / 180° against DG0's 8.65 / 9.58 / 8.60%, with the mis-rotated control surviving at 23.3%: the pre-registered verdict is **(a), the DG0 estimator floor**. No band moved; gate (ii) stays red and re-registering it is a review's call. Step 1c executed 2026-08-29 22:30 — the DG0 reading on a 96-point rotation-invariant ring set is 9.93 / 9.95 / 8.47% against the centroid set's 8.65 / 9.58 / 8.60%, every angle inside ±2 pp: **the sample set is not the mechanism**, corroborating 1b's estimator-floor verdict from the other side. Still no band moved. Step 1d executed 2026-08-30 12:00 — the ruling landed in the code: `post.project_to_cg1` is the packaged production estimator and gate (ii) is the CG1 covariance identity at all three angles, **2.1870 / 2.1146 / 1.8911%** against the unmoved 5% band, controls holding (mis-rotated 23.2642%, DG0 column unmoved at 8.6516 / 9.5808 / 8.5970%). `19 passed` / Status 0 / 97 s; **step 1 is ✅ and the chunk is 🟡** — a symmetry identity only, no CV / homogeneity / absolute claim; steps 2–3 are a review's to scope. **Step 2 scoped 2026-08-30 18:00 review** — the quadrature drive by exact superposition of the four solved fields at 10 MHz, two symmetry identities (C4-invariance; the co/counter-rotating mirror identity `\|B₁⁺\|_ccw(x) = \|B₁⁻\|_cw(Mx)`) at the measured CG1 floor, and the first *ungated* CV / polarisation-purity figures; §9 item 3. Step 2 executed 2026-08-31 22:30 slot — **both identities green at the CG1 floor: (a) C4-invariance of the quadrature `\|B₁⁺\|` map **0.9818%** and (b) the mirror identity `\|B₁⁻\|_cw(Mx)` vs `\|B₁⁺\|_ccw(x)` **0.8087%**, against the unmoved imported 5% band, with the mis-paired control at **95.1975%**; `17 passed` / Status 0 / 96 s. Ungated and labelled: centre purity `\|B₁⁺\|/\|B₁⁻\|` **127.91** (ccw) / **0.0081** (cw) / **1.0006** (P1 linear), mean `\|B₁⁺\|` 7.976427e-08 T at 1 V per port, CV **2.7563%** (51 centroids) / **2.4577%** (96 ring points). `post.b1_minus` landed. **Steps 1–2 ✅, chunk stays 🟡** — symmetry identities on one fixture at 10 MHz, no homogeneity, absolute, tuning or Larmor claim. **Step 2b executed 2026-08-31 09:00 slot, green on the first run** — the same five identities at **64 and 128 MHz** on one mesh through `build_four_port_sweep(frequency_hz=…, reuse=…)`: gate (ii) **2.2187 / 2.1667 / 1.9574%** (64) and **2.1315 / 2.1735 / 1.9511%** (128), quadrature (a)/(b) **0.9570 / 0.7570%** and **0.9106 / 0.6968%**, gate (i) 9.5231e-03 / 9.2445e-03 — all inside the unmoved imported 5% / 1e-2 bands, controls 24.75 / 25.26% and 95.11%, and the 10 MHz rung reproducing all five records at rtol 1e-3. Phantom cells/λ 69.14 / 21.89 / **12.50** against `PORT-11`'s floor of 10: the pre-registered 128 MHz resolution question reads **no miss**. First Larmor B₁⁺ figures on record, ungated: centre purity 141.81 / 171.94 (ccw), mean `\|B₁⁺\|` 6.500452e-08 / 4.936577e-08 T at 1 V per port, CV 2.7738 / 3.0177%. `16 passed` / Status 0 / 202 s. **Steps 1–2b ✅, chunk stays 🟡** — identities on one unconverged fixture, still no homogeneity, absolute, tuning or SAR claim. **Step 3 (coil-driven SAR symmetry identities, 10 MHz) scoped 2026-08-31 10:30 review — see entry, §9 item 2. Step 3 executed 2026-08-31 13:30 slot — the pre-registered negative result: the point-SAR map read off the primal N1curl `E` misses all five C4/mirror identities at **25.11 / 40.55 / 30.01 / 38.61 / 28.15%** against the unmoved imported 5% band, while both controls hold (129.82 / 334.58%, asserted > band), the phantom-σ premise holds (0.5 S/m over 537 cells) and `mean_sar`'s phantom power reproduces gate (i)'s record **5.637745667e-08 W** to every printed digit. The three single-drive misses use only step 1's fields and step 1d's image sets, so the finding is the **pointwise-`E` estimator floor** (no CG1 projection in this path; squaring doubles it), not the new code. Five deliberate reds on `main` + known-issues entry; `20260831T183526Z_WF-6-step3.log`, `5 failed, 16 passed` / Status 1 / 96 s. **No SAR claim exists**; step 3b (the same identities off an L²-projected CG1 `E`) is a review's to scope. **Step 3b scoped 2026-08-31 18:00 review** — primal readings become asserted records, CG1 readings printed beside them with a pre-registered (a)/(b)/(c) verdict, no band moves in-slot; see entry, §9 item 1. **Step 3b executed 2026-08-31 19:30 slot — verdict (c) prints, but the run's own diagnostics relocate the finding: the primal column reproduced step 3's five identities and both controls to every digit (anchor held, now exported as `STEP3_PRIMAL_*`), the CG1 column read **worse** at every identity (152.05 / 109.78 / 169.51 / 53.19 / 40.84% vs primal 25.11 / 40.55 / 30.01 / 38.61 / 28.15%) with both CG1 controls surviving (163.61 / 75.91%), and the two projection diagnostics — CG1 phantom power **+35 198.9%** against the primal record, `‖E_cg1 − E‖/‖E‖` over the phantom **1876.19%** — say `post.project_to_cg1` does not fit the N1curl `E` at all. The measured finding is about the projector on `E`, **not** about phantom resolution; the `|B₁⁺|` gates (which project `B`, 0.38%) are untouched. `5 failed, 25 passed` / Status 1 / 105 s and 100 s. No band moved, no assert loosened, **no SAR claim exists**. **Step 3c executed 2026-09-01 07:30 — the projector is a projector: mass solve `converged_reason` 2 in 26 its on 64 191 dofs, `a + b × x` reproduced to 1.326607e-13, and the domain table (whole mesh 32.7802%, phantom 1876.1871%, phantom core 838.8978%) names candidate 1 — a *global* L² fit of a fixture whose `‖E‖` lives on the sheets is not an `E` estimator inside the low-field phantom. `5 failed, 38 passed` / Status 1 / 103 s. **Step 3d executed 2026-09-01 13:30, every anchor green on the first run: the phantom-restricted estimator** (mass + load over `dx(3)` on the parent mesh, 170 free of 21 397 owned CG1 blocks, the rest pinned to exactly 0) **cuts the phantom residual from 1876.1871% to 18.7238% (100.20× separation, the best-approximation inequality asserted) and brings the phantom power to 5.440097168e-08 W, −3.51% from the primal record against the global projection's +35 199%** — so it is an honest `E` estimator, `a + b × x` restricted-projects to 4.385695e-13, `x² ê_x` to 3.741459e-01, all six solves reason 2. The five identities (printed, not gated) improve 3–6× to **8.2868 / 9.4743 / 7.3477 / 6.8146 / 6.1185%** with both restricted controls surviving (123.6255 / 333.0778%) — and **still miss the 5% band at all five**, so the pre-registered verdict is **(c)**, now uncontradicted: with the projector exonerated and the global-fit tail removed, the residual miss is the fixture's ~1 cm phantom cells reading a quadratic-in-`E` map, and a finer rung is the weekly review's. `5 failed, 52 passed` / Status 1 / 123 s. **No band moved, nothing under `src/`, no SAR claim exists**. **Step 3e executed 2026-09-02 00:30 slot, green on the first run — the restricted estimator is packaged as `post.project_to_cg1_restricted` (`return_diagnostics` default off, prefix `fem_em_restricted_cg1_mass_`) and every step-3d anchor reproduced through it to every printed digit: 18.7238% against the same-run global fit's 1876.1871% (separation 100.20× vs the pre-registered 50× floor), 4.385695e-13 / 3.741459e-01, pinned max 0.000e+00 with 170 free of 21 397 blocks on 64 191 dofs, six solves reason 2 in 21–25 its, phantom power 5.440097168e-08 W, identities 8.2868 / 9.4743 / 7.3477 / 6.8146 / 6.1185% and controls 123.6255 / 333.0778%. 17 new items, all green; `5 failed, 69 passed` / Status 1 / 122 s, the 5 being step 3's unmoved primal reds. `project_to_cg1` gained 3c's domain-table warning in its docstring. **This packages an estimator, it does not register a gate — no band moved, no SAR claim exists**, `WF-6` stays 🟡. **Step 3e′ executed 2026-09-02 06:00 — the estimator-degree rung, every anchor green and the pre-registered (γ) printing with its own stated cause excluded by the same run:** `project_to_cg1_restricted` gained a keyword-only `degree: int = 1` (default unchanged) and was driven at 2 — `‖P²_Ω E − E‖_Ω/‖E‖_Ω` **14.4724%** ≤ CG1's 18.7238% (degree monotonicity, asserted), the pre-registered flip landing at **10.6 decades** (`x² ê_x` 6.659346e-02 at degree 1 → **1.505524e-12** at degree 2 on one exact source), `a + b × x` 1.363313e-12, pinned max **0.000e+00** (1 004 free of 160 537 owned CG2 blocks, 481 611 dofs), six solves reason 2 in 39–48 its, both controls surviving at 123.2927 / 327.6543% — **and the five identities *worse* at 19.3491 / 17.2097 / 16.0699 / 14.4087 / 11.3230%** against CG1's 8.2868 / 9.4743 / 7.3477 / 6.8146 / 6.1185%, while the phantom power *improved* to 5.519662942e-08 W (−2.09% from the primal record). A globally better L² fit of `E` is pointwise worse for these C4 identities at these 51 points: the projector **and** the estimator's degree are both excluded as the mechanism, and the identity-from-a-fitted-field construction is a review's to adjudicate. `5 failed, 82 passed` / Status 1 / **125 s**, standard. **No band moved, no SAR gate registered, `WF-6` stays 🟡*** **Step 3f executed 2026-09-02 15:00 — the finer-phantom rung, and it prints (a): on `build_four_port_sweep(phantom_resolution=0.0075)` (**120 499** cells / **2 746** tag-3, step 3f₀'s numbers reproduced at exact equality) the five SAR identities off `post.project_to_cg1_restricted` read **3.3600 / 3.4442 / 3.4525 / 3.0332 / 2.5465%** — all five **inside** the unmoved 5% band, ratios 0.36–0.47 of the coarse mesh's 8.2868 / 9.4743 / 7.3477 / 6.8146 / 6.1185%, both controls surviving (121.0800 / 384.1297%). **Verdict (c)'s attribution to the phantom's `h` is confirmed**, the projector (3c) and the degree (3e′) having been excluded. Estimator anchors all green on the new mesh: same-mesh best approximation **12.5225% ≤ 1626.2098%** (129.86×), `a + b × x` 9.947634e-13, `x² ê_x` 2.142147e-01, pinned max 0.000e+00 (722 free of 22 147 blocks, 66 441 dofs), six solves reason 2 in 20–25 its, restricted phantom power 5.499426495e-08 W (−1.5681% from this mesh's primal). Gate (i) unmoved at 9.795780e-03 / 9.796465e-03. **The one red: the `|B₁⁺|` C4 identities moved −1.57 / −1.52 / −1.33 pp (2.19 / 2.11 / 1.89% → 0.6177 / 0.5966 / 0.5647%), outside the pre-registered 0.5 pp anchor — an *improvement*, so gate (ii) is not invalidated but its "converged ~2% floor" provenance is; three deliberate reds on `main` + known-issues, and it is the deferred absolute-convergence rung's first data point.** `3 failed, 27 passed` / Status 1 / **175 s**, standard. **No band moved, no SAR gate registered, `WF-6` stays 🟡 — registering the first coil-driven SAR gate on this rung is a review's ruling, and clause (a) is its evidence.** **Step 3g executed 2026-09-02 16:30 — the integral-form rung, every anchor green on the first run and clause (a) printing at *fixed* `h`: the twelve C4 pairs of `P_j^{(k)} = ½∫_{tag 3} σ w_j |E^{(k)}|²` off the **primal** N1curl `E` on the default 116 085-cell mesh read **0.7149 / 1.1908 / 1.4417 / 0.9703 | 1.5200 / 0.2132 / 0.3377 / 0.9086 | 1.0569 / 0.8355 / 0.2780 / 0.2302%** (worst **1.5200%**, means 1.0794 / 0.7449 / 0.6002%), all inside the unmoved imported 5% band against the pointwise primal 25.11–40.55% and the pointwise restricted-estimator 6.1–9.5% on the *same* mesh; quadrature four-quadrant spread **0.4641%**. The partition identity `Σ_j P_j^{(k)} = P_phantom^{(k)}` holds to every printed digit for all five drives (asserted rtol 1e-10) and the gate-(i) drive's total is **5.637745667e-08 W**, step 1's record digit-for-digit; the mis-paired 180° control is asserted larger at **96.1655 / 97.4944 / 95.5869%**, ratios **89.09 / 130.89 / 159.27×**. So the fourth candidate — reading a quadratic identity from a field at *sampled points* — is worth 4–6× at fixed `h`, with no estimator in the path. `20 passed` / Status 0 / **106 s**, standard. **No band moved, no SAR gate registered, `WF-6` stays 🟡 — registering the first coil-driven SAR gate on the integral construction is a review's ruling.** **Step 3h executed 2026-09-02 19:30, green on the first run and `WF-6` step 3 is now ✅: the twelve integral C4 pairs and the quadrature four-quadrant spread are **asserted** `≤ C4_COVARIANCE_BAND` (5%, imported from step 1d and *unmoved*) as one parametrised test per `(k, j)`, and against step 3g's table at rtol 1e-3 — 0.7149 / 1.1908 / 1.4417 / 0.9703 \| 1.5200 / 0.2132 / 0.3377 / 0.9086 \| 1.0569 / 0.8355 / 0.2780 / 0.2302%, spread 0.4641%, every digit reproduced. The three pre-existing anchors are unmoved and green (partition identity at rtol 1e-10 for all five drives, P1 total **5.637745667e-08 W** = step 1's record digit-for-digit, mis-paired 180° control asserted larger at 96.1655 / 97.4944 / 95.5869%, ratios 89.09 / 130.89 / 159.27×). In the same window the five pointwise asserts in `test_birdcage_sar_map.py` became `STEP3_PRIMAL_IDENTITY_RECORDS` reproductions at rtol 1e-3 (25.1096 / 40.5462 / 30.0142 / 38.6120 / 28.1459%) **each paired with a one-line assert that the pointwise reading still *exceeds* the band** — the quantity retired as a gate with its measurement kept, so a change that silently made the pointwise map pass is visible, not absorbed; the two pointwise negative controls and every 3b–3e′ record test are untouched. `20260903T003309Z_WF-6-step3h.log`, **`109 passed` / Status 0 / 194 s** at `-n 2` complex with `tests/environment` (collect-only smoke first, `20260903T003258Z_WF-6-step3h-collect.log`, 98 items, 5 s): `test_birdcage_sar_integral.py` 22 items (was 9 + 12 pairs + 1 spread), `test_birdcage_sar_map.py` 76 items with **0 failed** (was 5 failed), no other count moved. **`grep -n "C4_COVARIANCE_BAND ="` still hits exactly one definition.** **This registers the repo's first coil-driven SAR gate and it is exactly one thing — a C4 symmetry identity of quadrant powers on one fixture at 10 MHz at fixed `h`: no mirror identity, no absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim. `WF-6` step 3 ✅, the chunk stays 🟡** (homogeneity / CV still open); the step-3 known-issues entry is retired by this commit. **Step 3f′ executed 2026-09-02 21:00, green on the first run — the ring-set control, the one-sided anchor and the integral column's first `h` data point, all on step 3f's same four solves (no new solve): (A) step 1c's 96-point rotation-invariant ring set, read on the 0.0075 mesh for **both** columns, agrees with the 373 tag-3 centroids within **+0.1117 / +0.0932 / +0.0538 pp** on the `\|B₁⁺\|` C4 identities and **+0.2420 / −1.0548 / −0.7113 / −1.0082 / −0.4078 pp** on the five restricted-CG1 SAR identities — all eight inside step 1c's measured ±2 pp bar, asserted, worst 1.0548 pp, so **the sample set is not the mechanism on this rung and step 3f's readings are an `h` rung after all**; all three negative controls survive on the ring set (24.1868% mis-rotated `\|B₁⁺\|`, 123.3351 / 375.0478% SAR). (B) Anchor (i) is now **one-sided** — `reading ≤ coarse record + 0.5 pp`, an identity may not get *worse* under refinement while a fall is the convergence measurement — green at all three angles (0.6177 / 0.5966 / 0.5647% against ceilings 2.6870 / 2.6146 / 2.3911%), with those three figures recorded as `STEP3F_B1_PLUS_FINE_RECORDS` at rtol 1e-3 **beside** the unmoved `STEP1B_CG1_RECORDS`; **the 0.5 pp ceiling was not widened, the 5% band was not moved and no `\|B₁⁺\|` figure was replaced**. (C) Step 3g/3h's twelve integral C4 pairs formed on **this** mesh's four primal fields, **printed not gated**: **0.1550 / 0.2786 / 0.0220 / 0.1466 \| 0.0276 / 0.2370 / 0.1754 / 0.1177 \| 0.0457 / 0.0621 / 0.1952 / 0.2998%**, worst **0.2998%** against the coarse mesh's 1.5200% — the pre-registered clause reads **(a): the integral gate's headroom does not shrink with `h`** (5.1× more headroom on the finer phantom, mis-paired control means 93.58–94.26%), with the partition identity asserted exact at rtol 1e-10 on all four drives and the P1 total **5.587038273e-08 W** agreeing both with `mean_sar`'s independent assembly and with step 3f's record. Every step-3f record reproduced unmoved (120 499 / 2 746 cells, 12.5225% ≤ 1626.2098%, 9.947634e-13, the five SAR identities 3.3600 / 3.4442 / 3.4525 / 3.0332 / 2.5465%, primal phantom power) and the module went **`3 failed, 27 passed` → `54 passed` / Status 0 / 117 s** (43 items, `-n 2` complex with `tests/environment`, standard tier under the 600 s ceiling; collect-only smoke first). `20260903T020607Z_WF-6-step3f-prime.log`; **no band moved, no gate registered here — step 3h owns the SAR gate and it remains a fixed-`h` statement, with 3f′ as one corroborating `h` point and no convergence claim — and `WF-6` stays 🟡**; the step-3f `\|B₁⁺\|` known-issues entry is retired by this commit. *Audited 2026-09-03 03:00 review — **step 3h** (`642bfc5`): `auditor` PASS on seven checks and DEMOTE on tier honesty — the merged two-module window measured **194 s** under `timeout -k 30 600` (`20260903T003309Z_WF-6-step3h.log:12`, footer `:9712`, re-traced) against the "standard" label the step's prose used; the label is corrected to **heavy by measurement** (this chunk's tier cell already reads heavy), no wrapped ceiling was exceeded, the gate stands; digits re-traced `:4689–4693`. **Step 3f′** (`4ec574d`): PASS on all eight, the one-sided re-read of the three former reds **ratified by this review** — the 0.5 pp ceiling and the 5% band are unchanged in `test_birdcage_sar_fine_phantom.py:1020–1034`, the fall is favourable and pinned at rtol 1e-3, the disposition was pre-registered 18:00; digits re-traced `…020607Z_WF-6-step3f-prime.log:4735–4739, 4746–4748`. **Rulings on the two slots' flags:** (1) no second SAR gate on the restricted-CG1 estimator at the fine rung — the gate is the integral construction and only it (rulings blockquote); the estimator's 3.36–2.55% stay records; (2) no convergence language enters §2 — 3f′ is one `h` data point; (3) the stale printer clause at `test_birdcage_sar_integral.py:239` is dropped by **step 3i** (§9 item 2), which also registers the mirror identity as quadrant integrals on the four single drives — pre-computed from 3h's own table at 1.7527 / 1.5261 / 0.3438 / 0.9563% against a 37.8–39.0% flank-vs-opposite control.* **Step 3i executed 2026-09-03 06:00, green on the first run and the review's pre-computed table verified rather than assumed: the mirror through the coil axis and drive `k`'s own azimuth fixes quadrants `k` and `k+2` and exchanges the flanks, so `P_{k−1}^{(k)} = P_{k+1}^{(k)}` is **asserted** `≤ C4_COVARIANCE_BAND` (5%, imported from step 1d and *unmoved* — `grep -n "C4_COVARIANCE_BAND ="` still one hit) as one parametrised test per `k`, reading **1.7527 / 1.5261 / 0.3438 / 0.9563%** against `STEP3I_MIRROR_RECORDS` at rtol 1e-3 (the 03:00 review's arithmetic off `…003309Z_WF-6-step3h.log:4682–4685` reproduced to every printed digit; the `k = 1` record is carried as 1.5262e-2, the exact quotient). The flank-vs-opposite control — pairing the same flank with the quadrant the mirror *fixes* rather than the one it exchanges — is asserted strictly larger and reads **38.2741 / 38.6261 / 37.8418 / 38.9935%**, separations **21.84 / 25.31 / 110.07 / 40.78×**. This is a **single-drive** statement, so it is independent evidence rather than a re-reading of 3h's rotation identity: an error common to all four solves cancels out of the twelve C4 pairs and does not cancel out of this one. Every 3h anchor unmoved and green in the same window (the twelve C4 pairs 0.7149 / 1.1908 / 1.4417 / 0.9703 \| 1.5200 / 0.2132 / 0.3377 / 0.9086 \| 1.0569 / 0.8355 / 0.2780 / 0.2302%, spread 0.4641%, mis-paired controls 96.1655 / 97.4944 / 95.5869% at 89.09 / 130.89 / 159.27×, partition identity rtol 1e-10 on all five drives, P1 total **5.637745667e-08 W**). The module went **22 → 26 items**, `20260903T110244Z_WF-6-step3i.log`, **`37 passed` / Status 0 / 96 s**, standard, `-n 2` complex with `tests/environment` under `timeout -k 30 560` (collect-only smoke first, `20260903T110234Z_WF-6-step3i-collect.log`, 26 items, 4 s); the stale "is the NEXT REVIEW's ruling, never in-slot" clause is dropped from the verdict printer. **No new solve, no new partition, no band moved, no absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim — a second symmetry identity on the same fixture at 10 MHz at fixed `h`, and `WF-6` stays 🟡.** **Step 4a executed 2026-09-07 07:30 slot, `7 passed` / Status 0 / 4 s (smoke, `-n 1`, real build, `20260907T123926Z_WF-6.log`) — the closed-form anchor step 4 proper needs now exists: `utils.analytical.birdcage_filament_field(points, *, ring_radius, coil_length, leg_currents, ring_currents=None)`, pure numpy (no `dolfinx` in the module), `N` legs at `2πn/N` plus two end rings of `N` arcs each, the ring currents solved from Kirchhoff at every leg–ring node as the unique zero-mean `J = cumsum(I) − mean(cumsum(I))` (raising unless `Σ I_n = 0`), the bottom ring `−J`, finite segments in closed form and arcs by 64-point Gauss–Legendre. All six pre-registered identities asserted and green on the first run, every one of them at or below its band by decades: (i) infinite-line limit at `L = 10³R` **9.999875e-07** (band 1e-5), (ii) ring limit vs `circular_loop_magnetic_field_on_axis` **2.830785e-16** axial / 2.653861e-17 transverse (band 1e-10), (iii) `∇·B` on the mode-1 F-small pattern **4.510963e-10** `|B|/R` over 20 interior points (band 1e-8), (iv) C4 covariance **2.431697e-16** (band 1e-12), (v) the finite-length factor **0.707106781** against `L/√(L²+4R²)` = 0.707106781 (band 1e-6), (vi) the mode-2 transverse zero at the centre **1.048150e-16** of the mode-1 centre field `|B| = 6.060915e-06` T at 1 A (band 1e-12). **Two of the item's own clauses were measured wrong and are corrected in the code, not absorbed:** (a) the item asserted the end rings contribute *zero* transverse field at the centre "by symmetry" — they do not; the two rings' transverse contributions **add** (reflection through `z = 0` flips a transverse source's transverse field and the bottom ring carries `−J`), and the correct closed form `B_ring(0) = (0, −μ₀IRh/(πρ³), 0)`, `h = L/2`, `ρ = √(R²+h²)`, is derived in the test docstring and **asserted instead**, reading **−2.020305089e-06 T** against it at rel dev 4.192599e-16, i.e. exactly `R²/ρ² = 0.500000000` of the legs' own centre field on F-small — a 50% end-ring contribution that step 4 must not omit; (b) the item's negative control (legs without rings reading ≥ 100× the closed pattern's `∇·B`) **cannot hold**: Biot–Savart is `curl A` for an open filament as much as a closed one, so `∇·B ≡ 0` either way, and the run prints both readings side by side (**4.510963e-10** closed vs **7.300842e-10** open `|B|/R`) as the evidence. The control is replaced by the identity an open circuit *does* break — Ampère's law: on a 0.2 R contour about leg 0 in the `z = 0` plane the closed coil reads `∮B·dl = μ₀I₀` to **1.887379e-15** (asserted ≤ 1e-9, an exact identity in its own right) while the legs alone read **1.761971e-02** — **9.34e+12×**, asserted ≥ 100×, and inside the **computed O(1) ceiling** `1 − L/√(L²+4a²)` = **1.941932e-02** (0.907× of it; the residual is the other three open legs' own `grad(div A)` flux through the same disc), asserted in a [0.5, 1.5]× bracket. **Scope: the closed form and its identities only — no FEM, no `|B₁⁺|` comparison, no homogeneity or absolute claim, nothing under `src/` beyond the one additive function, no band moved, §2 unchanged and `WF-6` stays 🟡.** **Step 4f executed 2026-09-09 07:30 slot — the `h`-ladder ran to completion at all three rungs and it answers the 03:00 ruling's question with a *partial* yes: the field's C4 four-copy spread **falls 2.5× with the mesh and then stalls, an order above `GEO-28`'s mesh floor**. One window, `-n 4`, complex build, `timeout -k 30 560`, harness elapsed **453 s** (`20260909T123716Z_WF-6.log`; collect-only smoke `20260909T123702Z_WF-6.log`, 40 items / 4 s), **4 failed / 32 passed / 4 skipped**; **all code is parked on `attempt/WF-6-step4f-20260909T124552Z` (`ab2a2cf`) and `main` carries only the two logs, this annotation and the known-issues row.** **The measurement (printed, never asserted — no prior `h`-ladder on this fixture backs it):** worst-radius (0.5R) C4 four-copy spread of the ccw-quadrature `\|B₁⁺\|` **5.2506% → 2.0719% → 1.9514%** at `resolution` 0.015 / 0.012 / 0.0095 m (ratios to ×1 **1.0000 / 0.3946 / 0.3717**; `GEO-29`'s interior mean `h` 2.19e-2 / 1.71e-2 / 1.37e-2 m), with the gated C4 covariance falling alongside it **3.6159% → 1.6815% → 1.5029%** (imported, unmoved 5% band, green on all three rungs) and the point-to-point drift of the eleven gate points **median 0.36% / 0.91%, max 2.46% / 1.84%**. All three rungs reproduced `GEO-29`'s cell counts to ratio **1.000000** (116 085 / 149 049 / 197 393). **So refinement owns roughly 60% of the effect and stops**: the ×0.012 → ×0.0095 step buys 0.12 pp on a 2 pp spread, which does not extrapolate to `GEO-28`'s ≈ 0.1% mass floor, and the residual ≈ 2% sits with the degree-1 N1curl solve or the CG1 `curl E` estimator, not with `h`. **Three asserted reds, none absorbed and none re-tuned in-slot.** (1) **Anchor (i)'s second half**: the ×1 four-copy spread reads 5.2506% against the pre-registered **3.310633e-02** recorded value, 58.60% relative, outside the 10% reproduction control — but the *reproduction itself is exact*: the ×1 rung reproduces step 4b's eleven-point table **character-for-character** (9.805561792e-08 T at +x̂ and 1.013569652e-07 T at +ŷ, `20260908T004020Z_WF-6.log:1894, 1899`). The anchor's **number** was mis-specified, not the fixture — the pre-registration equated a *four*-copy spread with a *two*-copy record, and the `−x̂` copy (1.024222080e-07 T) is the maximum that record never contained. Re-registering it on the two-copy statistic (or on the four-copy one with its own measured value) is a review's, not a slot's. (2) **The negative control at ×1**: the cw drive's worst spread 50.0268% is **9.53×** the ccw's, just under the pre-registered 10× bar — whose arithmetic (95.2/3.4 = 28×) was sized against the same mis-specified 3.4%; it passes on both finer rungs at **19.52×** and **58.38×**. (3) **A new finding — power accounting degrades under refinement**: the residual is 9.796e-03 at ×1 and 8.114e-03 at ×0.012, both inside the imported, unmoved 1% `POWER_BALANCE_BAND`, but **1.853642e-02 (P1) / 1.419812e-02 (P2) at ×0.0095**, outside it; on the same rung the sweep's own `Z` class spreads print **1.3475 / 0.4544 / 0.9165%** against `PORT-9`'s 0.5% (ungated here). Refining the *global* resolution therefore degrades this fixture's port-side conservation the way `ANS-4` step 2a found refining `conductor_resolution` degrades its C4 symmetry — two independent refinements, the same class of symptom, and neither is diagnosed. **The closed-form comparand path is deleted from the gate per ruling (1); the 5% `CLOSED_FORM_BAND` and the `S_3`/`S̄_6`/`S_11` comparands were not loosened and not used.** Additive keywords only (`resolution` on `_build` and `build_four_port_sweep`, `phantom_material` on `build_four_port_sweep`), every default bit-for-bit unchanged. **Closes nothing: no absolute `\|B₁⁺\|` claim, §2's B₁⁺ clause keeps its wording, `WF-6` stays 🟡**, and the 2026-09-13 weekly's Phase-5 exit decision now has its measured convergence statement rather than a gate.** **Step 4g executed 2026-09-09 15:00 slot, green on the first ladder run — the two re-registered anchors and the re-sized negative control all hold, and every one of 4f's numbers on the two kept rungs reproduces to the printed digit.** One window, `-n 4`, complex build, `timeout -k 30 500`, `-s`, `20260909T200431Z_WF-6.log` — **`28 passed, 2 skipped` in 202.58 s, `Status: 0` (`:3917, 4116`), harness elapsed 204 s** (collect-only smoke `20260909T200247Z_WF-6.log`, 12 items / 5 s, `Status: 0`). **The ladder, now two rungs** (`:1982–1994, 3803–3815, 3828`): `resolution` 0.015 → 0.012, `size_global` **116 085 / 149 049** at ratio **1.000000** (the ×1 count asserted at the imported, unmoved 1% `CELL_COUNT_BAND`), worst-radius (0.5R) C4 four-copy spread **5.2506% → 2.0719%**, ratio to ×1 **0.3946**; C4 covariance **3.6159% / 1.6815%** against the imported, unmoved 5% band; power residuals **9.795836e-03 / 9.796294e-03** (×1, P1/P2) and **8.113516e-03 / 8.111819e-03** (×0.012) against the imported, unmoved 1e-2 band, phantom power exactly 0 on both rungs as vacuum requires; point-to-point drift median **0.9482%**, max **2.9092%** (printed, never asserted). **Anchor (i) re-registered and green:** the ×1 four-copy spread reads 5.2506% against 4f's measurement of *that same statistic on this fixture at this rung*, 5.2506% (`20260909T123716Z_WF-6.log:2080–2086`), inside 10% relative — and the eleven-point table reproduces step 4b's **character-for-character** (9.805561792e-08 T at +x̂, 1.013569652e-07 T at +ŷ, `20260908T004020Z_WF-6.log:1894, 1899`; `…200431Z:2000, 2005`). The comparand it replaces, 3.310633e-02, was a **two**-copy spread the record never extended to four copies — the statistic was mis-specified, not the tolerance, which stays 10%. **The negative control re-sized off a measured ceiling and green on both rungs:** the cw drive's worst-radius spread **50.0268% / 40.4425%**, separations **9.53× / 19.52×** against the new ≥ **5×** bar. The old 10× bar was *arithmetically unreachable* at ×1 — 50.0268/5.2506 = 9.53 is that rung's maximum — so this is a ceiling-first re-sizing of a bar that was never a band or a green record, not a loosening. **The ×0.0095 rung is dropped, not absorbed:** its 1.853642e-02 / 1.419812e-02 power residual is under diagnosis (2026-09-09 known-issues row; `GEO-30` measured the mesh and excluded it), its 4f readings stay on record above, and returning it is a review's call. **`CLOSED_FORM_BAND` (5e-2), `POWER_BALANCE_BAND` (1e-2), `C4_COVARIANCE_BAND` (5e-2) and `CELL_COUNT_BAND` (1e-2) are all imported and unmoved; the eleven points were never pruned and the deleted closed-form comparand was not re-introduced.** Three files land, two of them the additive keywords 4f needed and `main` never carried (`resolution` on `tests/mesh/test_birdcage_port_sheets._build` and on `build_four_port_sweep`, `phantom_material` on the latter — all defaulting `None` to the gates' existing values; the first run of this slot, `20260909T200300Z_WF-6.log`, is the `TypeError` that proved they were missing). **Closes nothing: no absolute `\|B₁⁺\|` claim, no closed-form B₁⁺ gate, §2's B₁⁺ clause keeps its wording, `WF-6` stays 🟡** — what lands is a two-rung monotone-fall measurement carried by asserted symmetry, power and reproduction anchors on `main` rather than on a branch.  **Step 4h (2026-09-11, 09:00 implementer slot) — NEGATIVE RESULT: the C4-congruent sheet cut removes the ×0.0095 rung's P1/P2 *split* but not its power *residual*; the rung stays dropped.** Test-side keywords only, defaults bit-identical: `c4_congruent_sheets=False` added to `tests/mesh/test_birdcage_port_sheets._build` (forwarded to `birdcage_port_domain`, whose own default it is) and to `build_four_port_sweep` (forwarded through `_build(True, …)`, ignored under `reuse`); in `test_birdcage_b1_plus_closed_form.py` env `FEM_EM_WF6_C4_CONGRUENT` (unset/`0` = off) and `FEM_EM_WF6_LADDER_KEYS` (ladder-order selection, unknown key raises at collection), ×0.0095 joining `ACTIVE_LADDER` only with the flag on, the two ×1 record tests skipping under the flag with "flag-on mesh is not the record mesh (`GEO-32`)" after printing their readings, and `report_peak_rss` wired collectively after each rung. **Collect-only smoke** (`20260911T140308Z_WF-6-step4h-collect.log`, 6 s): flag off collects `x1` + `x0.012` (the default `LADDER`, unchanged), flag on with keys `x1 x0.0095` collects `x1` + `x0.0095`. **The window** (`20260911T140329Z_WF-6-step4h.log`, flag `=1`, keys `x1 x0.0095`, `-n 4`, complex, `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first, `timeout -k 30 590`, `-v -s`, durable capture): **1 failed / 18 passed / 4 skipped in 196.74 s**, harness elapsed **199 s**, `[capture] rc=1` (`:4149, :4372`; the footer's `Status: 0` is the `cat`'s, not pytest's). **×1 flag-on, all anchors green:** **116 118** cells — the predicted 116 118 at ratio 1.000000, 1.000284 of the flag-off record 116 085 (`:2032`); power residual P1 **9.795942e-03** / P2 **9.796517e-03** ≤ 1e-2 (`:2043–2044`); C4 covariance **3.5271%** ≤ 5% (`:2042`); cw 55.1215% over ccw **3.6668%** (worst radius 0.4R) = **15.03×** ≥ 5× (`:2040–2041`); 21 of 21 points; `[mem]` 2.6326 GiB over 4 ranks (`:2057`). The ×1 spread record test skipped and printed 3.6668% against the flag-off 5.2506% (30.16% relative, `:2076`) — printed, not re-registered. **×0.0095 flag-on:** **197 284** cells (`GEO-29`'s flag-off single reading 197 393, ratio 0.999448, `:4023`); covariance **1.3181%** (`:4033`), ccw worst spread **1.7707%** at 0.5R = 0.4829 of ×1, cw 94.0085% = **53.09×** (`:4031–4032`), 21 of 21 points — green; **power residual P1 1.968410e-02 / P2 1.968464e-02 against the unmoved 1e-2 — red** (`:4034–4035, :4147`). **Negative control by record:** flag-off P1 1.853642e-02 / P2 1.419812e-02 (`20260909T123716Z_WF-6.log:5777–5778, 5789–5795`) ⇒ on/off ratio **1.0619 / 1.3864** (`:4036–4037`) — *predicted* to fall, printed not asserted, and it **rose**. **Reading:** the congruent cut was the carrier of the *port-to-port split* — P1 and P2 now agree to 2.7e-05 relative, as on both coarser rungs — but the residual itself is common-mode ≈ 1.97e-02 on both ports, so it is not a sheet-cut asymmetry and the cut does not return the rung. `[mem]` 4.6873 GiB over 4 ranks (`:4051`). **Flag-off default control** (`20260911T140714Z_WF-6-step4h-flagoff-x1.log`, keys `x1`, `-n 4`, `timeout -k 30 300`, `-v -s`): **6 passed in 50.93 s**, elapsed 52 s, `[capture] rc=0` (`:1914, :1924`) — 116 085 at ratio 1.000000, spread 5.2506%, 9.53×, covariance 3.6159%, residuals 9.795836e-03 / 9.796294e-03 (`:1866–1878`), reproducing 4f/4g, so the keyword threading leaves the default path green. **Not changed:** the default `LADDER`, every `WF-6` record, every band; no rung re-registered on the flag-on mesh. Known-issues 🟡 2026-09-11 `WF-6` step 4h entry opened (the 2026-09-09 `ANS-4` entry was retired at 04:30). Returning ×0.0095 needs a diagnosis of the common-mode ≈ 2e-2 residual first — a review's scoping. **Step 4i (2026-09-11 15:00 slot) — the common-mode residual IS the terminal-form Cauchy–Schwarz deficit, on all three flag-on rungs (§9 item 3).** Test-side only: env `FEM_EM_WF6_EXACT_SHARES` in `tests/validation/test_birdcage_b1_plus_closed_form.py` calls `PORT-16`'s `_exact_shares` (imported with `DISCRETE_IDENTITY_RTOL`, names only) on the P1/P2 drives of each rung. Unset, nothing new is computed. There are two new tests, and both skip unless the flag is set. No `src/` change. Collect-only `20260911T200221Z_WF-6-step4i-collect.log` (27 items, 4 s). **Window 1** `20260911T200251Z_WF-6-step4i.log` (flags `FEM_EM_WF6_C4_CONGRUENT=1 FEM_EM_WF6_EXACT_SHARES=1`, keys `x1 x0.0095`, `-n 4`, `timeout -k 30 590`, `-v -s`, durable capture with `exit $rc`): **1 failed / 22 passed / 4 skipped in 196.11 s**, elapsed 198 s, `[capture] rc=1`, `Status: 1` (`:4183, :4406, :4409–4410`). The one failure is the by-design `test_power_accounting_closes_on_every_rung[x0.0095]` (`:4181`). Cells 116 118 / 197 284 (`:2032, :4040`), `[mem]` 2.6241 / 4.7248 GiB (`:2066, :4077`). **Anchor (a), asserted, green:** the identity rel dev is ×1 2.345e-15 / 1.048e-14 and ×0.0095 4.727e-15 / 3.647e-15 (P1/P2, `:2046, :2050, :4056, :4060`), against 1e-6. **Anchor (b), asserted, green:** the terminal residuals reproduce 4h to rel 6.504e-09 / 3.162e-08 (×1 9.795942e-03 / 9.796517e-03, `:2048, :2052`) and 3.388e-08 / 2.444e-07 (×0.0095 1.968410e-02 / 1.968464e-02, `:4058, :4062`), against 1e-5. **Printed (rule (e)), never asserted:** ×1 P1 has P_src,exact 3.143735084e-03, P_vol 4.482387309e-04, P_sheet,exact 2.695496354e-03, C 6.408026185e-03 and terminal 6.340862612e-03 W, so **C/terminal 1.010592**; P2 reads 1.010593 (`:2047, :2051`). ×0.0095 P1 has P_src,exact 3.210984733e-03, P_vol 4.371025298e-04, P_sheet,exact 2.773882203e-03, C 6.351912737e-03 and terminal 6.218277077e-03 W, so **C/terminal 1.021491** on both ports and on all four sheets to ±1e-6 (`:4057, :4059, :4061, :4063`). **CS-corrected residual:** ×1 1.012e-15 / 4.681e-15, ×0.0095 1.661e-15 / 1.150e-15 (`:2048, :2052, :4058, :4062`), so `supplied_terminal = P_vol + C` to machine precision, as on `PORT-16`'s loaded ×1. **Window 2** `20260911T200634Z_WF-6-step4i-x0.012.log` (same flags, key `x0.012`, `timeout -k 30 400`): **16 passed / 3 skipped in 101.95 s**, elapsed 104 s, `[capture] rc=0` (`:2134, :2330, :2334`). 148 988 cells (`:2003`), `[mem]` 3.3857 GiB (`:2037`). Identity 2.215e-15 / 1.384e-15 (`:2017, :2021`). Terminal residual 8.113595e-03 / 8.111880e-03 (no 4h flag-on record, so reproduction skips). **C/terminal 1.008756 / 1.008757** (`:2018, :2022`), CS-corrected 7.578e-16 / 5.053e-16 (`:2019, :2023`). **Reading:** the terminal residual is exactly `(C − terminal)/supplied`. The deficit is uniform across sheets, and C/terminal − 1 reads 1.059 % / 0.876 % / 2.149 % at ×1 / ×0.012 / ×0.0095 — **non-monotone in h**. The ×0.0095 rung doubles it, which says the sheet field's non-uniformity across the gap (not an assembly leak, not the conductor term) grows on that mesh. **Caveat for the review:** `supplied_terminal = P_vol + C` closes to 1e-15 on every rung, so it is an algebraic identity of the discrete solve and could not have come out otherwise. The discriminating number is C/terminal, not the CS-corrected residual. No band, record or `LADDER` moved, no `PORT-16` re-disposition; whether the fixture's accounting should use the exact form is the review's ruling. **Ruled 2026-09-11 18:00 review — not switched.** The exact-form closure is algebraic on the discrete solve (the slot's own caveat), so as a gate it could not fail. The terminal residual stays the power gate, ×0.0095 stays out of `LADDER`, and the known-issues entry stays OPEN with its cause row updated. The open question is the mechanism behind C/terminal − 1 doubling on ×0.0095 while ×0.012 lowers it; step 4j (§9) localises the sheet-field non-uniformity across the width and along the gap. Step 4j (2026-09-11 22:30 slot) — **the ×0.0095 excess is not in the gap ends and not a resolved strip edge: two-thirds of its growth is the in-plane transverse field, and the drive-component part sits on a single mid-gap rim facet.** Test-side opt-in `FEM_EM_WF6_SHEET_PROFILE=1` (requires `FEM_EM_WF6_EXACT_SHARES=1`), P1's driven `E` at the owned tagged facet midpoints through `evaluate_vector_field_parallel`. Anchors green: 4i's discrete identity (unchanged test), and C/terminal reproduces 4i to ≤ 3.5e-7 against rtol 2e-6 on every rung and drive; swapped-rung control misses by 5 335× / 5 392× the rtol against the asserted 100× (`20260912T033518Z_WF-6-step4j.log:2126–2128, 4179–4181`; `20260912T033918Z_WF-6-step4j-x0.012.log`). Readings (P1 sheet; P2–P4 agree, mirrored u → 1−u; ×1 / ×0.012 / ×0.0095): facets per sheet **26 / 26 / 29**, width/median facet diameter **3.53 / 3.80 / 3.66**, so no rung resolves the strip edge. The sampled `R_s,tan = A Σa(\|f\|²+\|E_w\|²)/\|Σa f\|²` reproduces C/terminal to ≤ 3e-8 on all twelve sheet-rungs, which splits C/terminal − 1 exactly. The drive-component variance `R_s − 1` is **8.145e-3 / 6.691e-3 / 1.2045e-2**. The in-plane transverse term `R_s,tan − R_s` is **2.447e-3 / 2.065e-3 / 9.446e-3**. So ×1 → ×0.0095 grows by +1.090e-2, of which the transverse term carries +7.00e-3 (64 %) and the drive component +3.90e-3 (`:2056, 4103`; x0.012 `:2027`). Location at ×0.0095 (`:4105–4108`): gap-end bins 0 + 4 carry 17.3 % of the drive variance on 40.8 % of the area, and mid-gap bin 2 carries 47.4 % on 17.7 %. **One facet** (u 0.164, v 0.422, 6.7 % of area, alone in width bin 0) carries 42.25 %, with `<\|f\|>` 61.9 against ≈ 87 V/m elsewhere and `<\|E_w\|>` 20.9 against 3–8. The top 5 facets carry 75 %. ×1 and ×0.012 show the same pattern at lower amplitude (top facet 33.3 % / 27.6 %, top 5 90 % / 88 %). Predicted and printed only: R_s within 1e-2 of C/terminal **held** (gap 2.4e-3 / 2.1e-3 / 9.4e-3, the last near the bound); transverse share small **held** (≤ 1.5e-2). Of the two readings, the evidence favours *a handful of rim facets*, specifically a mid-gap edge facet whose in-plane transverse field quadruples on this mesh; it does not favour gap ends at the terminals or a resolved strip edge. No band, record, `LADDER` or accounting change; WF-6 stays 🟡. **Ruled 2026-09-12 03:00 review:** 4j accepted (re-read `20260912T033518Z_WF-6-step4j.log:4104–4108`); step 4k — a no-solve `mesh-probe` census of that facet's aspect ratio, adjacent-tet quality and rim adjacency across the three flag-on rungs — is §9 item 5; the rung's power gate is not ruled until it reads. **Step 4k (2026-09-12 16:30 slot, `mesh-probe`, no solve, nothing asserted) — the sliver hypothesis is REFUTED on shape; the rim clause is not met literally.** New `tests/mesh/probe_wf6_sheet_facet_census.py`, one fresh `-n 1` complex process per rung: `20260912T213317Z_WF-6-step4k-x1.log`, `…-x0.012.log`, `…-x0.0095.log`, `…-x0.0095-repeat.log` (Status 0, 29 / 32 / 39 / 38 s, sequential). Anchors reproduced: 116 118 / 148 988 / 197 284 cells, P1 facets 26 / 26 / 29; the 4j top-5 found on every rung at |Δuv| ≤ 6e-4. Negative control held: the (0.164, 0.422) facet on ×0.0095 reads area share 6.726 % (`…-x0.0095.log:1928`). The repeat build carries the same sheet-geometry hash and all census lines (`:2007` both logs), so the reading is deterministic. On ×0.0095 that facet is among the **best-shaped** on P1's sheet: edge ratio 1.195 and R/r 2.047 both rank 5/29 (below Q1), worse adjacent tet 3r/R 0.7864 and min dihedral 46.08° both rank 23/29 (above Q3). It is the **largest** facet (area/median 2.174, 29/29), has a lateral-rim edge (8/29 facets do; 26/29 touch the boundary at a vertex), and no terminal edge (`:1928–1933`). The ×0.0095 sheet is the best-shaped of the three rungs (R/r max 2.711 against 4.311 / 3.406), so facet quality does not track the ×0.0095 variance doubling. The top-1 facet on every rung is the same kind — the sheet's largest or near-largest, mid-gap, lateral-rim edge, u ≈ 0.16–0.19, v ≈ 0.39–0.42 — with adjacent-tet quality below Q1 on ×1 (0.6224, 34.42°) and at ×0.012 (dihedral 33.97°, rank 2/26), but not on ×0.0095. "Rim" here is the narrowed sheet's stepped f = 0.5 midpoint-filter cut, not the CAD edge. The in-plane field on that facet now needs a field-side reading (the N1curl trace on its adjacent cells), which a review scopes; whether "large lateral-rim facet on a ≈ 3.5-facet-wide sheet" is the explanation is the review's ruling. No band, `LADDER` or accounting change; ×0.0095 stays out. **Ruled 2026-09-12 18:00 review — 4k accepted (re-read `20260912T213439Z_WF-6-step4k-x0.0095.log:1928–1933`); the step-4 family is FROZEN and the ×0.0095 question is closed as a measured negative.** Since 4g's green (the last sub-step that landed a gate) the family has run 4h, 4i, 4j and 4k — four attempts, the cap the operator directive of 2026-09-12 sets — and every one of them diagnosed a rung the 2026-09-09 ruling had already taken out of `LADDER`, so none could move a status by construction. The banked reading, in one sentence: on the flag-on ×0.0095 mesh the power residual is the terminal form's Cauchy–Schwarz deficit (C/terminal − 1 = 2.15 %, non-monotone in h), two-thirds of its growth is in-plane transverse field, the drive-component part sits on one large, well-shaped, mid-gap lateral-rim facet, and the mechanism is **not explained**. The field-side reading 4k proposes (the N1curl trace on that facet's adjacent cells) is **declined**: it could not return ×0.0095 to `LADDER` on its own, and the row's status does not depend on that rung. What would move `WF-6` is the homogeneity / CV subgoal on the two-rung ladder `main` carries (4g), or a weekly decision to put ×0.0095 back on the ladder with the residual re-registered by measurement under rule (f) — either is a numbered step 5, scoped by the weekly (2026-09-13 02:15), not a 4l. The known-issues entry stays OPEN with this ruling appended; no band, `LADDER` or accounting change. **Step 5 (2026-09-13 12:00 slot, §9 item 1) — the two-rung convergence statement is registered and `WF-6` is ✅ on the re-scoped subgoal-4 target (2026-09-13 weekly, §10 Phase-5 exit decision).** Tests only, `tests/validation/test_birdcage_b1_plus_closed_form.py`, default `LADDER` (×1, ×0.012), every flag off. Two new tests: `test_step5_the_worst_spread_reproduces_its_4g_record` (per rung, rtol 1e-3 against `STEP5_RECORDED_SPREADS` = 5.2506e-02 / 2.0719e-02, additional to the 10 % ×1 control, which stays) and `test_step5_the_ladder_falls_monotonically` (on ×0.012 with ×1 read in the same process: spread and C4 covariance both strictly fall). One window, `20260913T170259Z_WF-6-step5.log`: `tests/environment` + the module, `-n 4`, complex, `FEM_EM_REQUIRE_COMPLEX=1`, `timeout -k 30 590`, `-v -s` — **24 passed / 9 skipped / 0 failed in 154.10 s, `Status: 0`, harness elapsed 156 s** (`:3904, :4102–4103`); the 9 skips are the opt-in 4h–4j tests and the by-construction record skips. **Anchor (i), asserted, green:** worst-radius C4 four-copy spread **5.250630 %** (rel 5.709e-06) and **2.071886 %** (rel 6.912e-06) against 4g's records (`:1987, :3831`). **Anchor (ii), asserted, green:** spread 5.2506 → 2.0719 % (ratio 0.3946), covariance 3.6159 → 1.6815 % as resolution 0.015 → 0.012 m (`:3836`). **Anchor (iii):** every existing test green in the same window — ×1 116 085 cells at the imported 1 % band, covariance ≤ 5 %, power residuals ≤ 1e-2, cw separation ≥ 5×. **Printed, never asserted (rule (e)):** the 21-point interior CV of `\|B₁⁺\|` **8.1710 %** (×1) / **6.6430 %** (×0.012) beside the free-space filament closed form's (step 4a's function, legs + Kirchhoff rings, no PEC shield) **3.5703 %** on the same points (`:1988, :3832`) — context, not a comparand, since the FEM domain is shielded and the filament is not; and §10's record of the ×1 eleven-point miss against `S₁₁` (≈ 3.2 % centre, ≈ 5.3 / 7.9 % at 0.4R / 0.5R, `:3837`). **Not changed:** every band (`POWER_BALANCE_BAND`, `C4_COVARIANCE_BAND`, `CELL_COUNT_BAND`, `CLOSED_FORM_BAND`), `LADDER`, `RECORDED_X1_WORST_SPREAD` and its 10 % tolerance; ×0.0095 stays out and its known-issues entry stays OPEN. **Scope:** a convergence statement on F-small at 10 MHz, CG1 — no closed-form, homogeneity, absolute, C95.3, Larmor or human-scale B₁⁺ claim. §2.2's B₁⁺ clause is re-worded to it in the same commit. | ✅ 

## Narrative — moved verbatim from PROJECT_PLAN.md §7 (OPS-47)

**`WF-6` — B1+ field mapping and homogeneity** 🟡 *(steps 1, 2 and 2b ✅ — step 1
2026-08-30 with step 1d, **step 2 ✅ 2026-08-31 22:30 slot** (0.9818% / 0.8087%
against 5%, control 95.1975%, log `20260831T033704Z_WF-6-step2.log`),
**step 2b ✅ 2026-08-31 09:00 slot** — the same five identities at 64 and
128 MHz on one mesh, all inside the unmoved bands at 21.89 / 12.50 phantom
cells/λ, log `20260831T140418Z_WF-6-step2b.log`; **step 3 executed 2026-08-31
13:30 slot and delivered its pre-registered negative result** — the coil-driven
point-SAR map misses all five identities at 25–41% against the same unmoved 5%
band, controls and the power-record reproduction holding, five deliberate reds
on `main` and a known-issues entry, log `20260831T183526Z_WF-6-step3.log`; **no
SAR claim exists** and step 3b (a CG1-`E` estimator leg) is a review's to scope.

**Step 3e executed 2026-09-02 00:30 slot — the promotion landed and every
step-3d anchor reproduced through the packaged path, to every printed digit.**
`_project_to_cg1_restricted` moved verbatim out of
`tests/validation/test_birdcage_sar_map.py` into
`src/fem_em_solver/post/faraday.py` as **`post.project_to_cg1_restricted`**,
signature `(field, cell_tags, *, name, tag, ksp_rtol=1e-12,
return_diagnostics=False)` — `return_diagnostics` default flipped **off** to
match `project_to_cg1`, PETSc prefix renamed off the step-scoped name to
`fem_em_restricted_cg1_mass_`, exported from `post/__init__.py` and both
`__all__`s; the test module is its first caller with
`return_diagnostics=True`. Log `20260902T003813Z_WF-6-step3e-table.log`,
`5 failed, 69 passed` / Status 1 / **122 s** at `-n 2` complex with
`tests/environment` (11 passed) in the same window; the module-only run is
`20260902T003518Z_WF-6-step3e.log`, `5 failed, 58 passed` / Status 1 / 98 s,
and `tests/environment` alone `20260902T003443Z_WF-6-step3e-env.log`,
`11 passed` / Status 0 / 29 s. The 5 failures are step 3's five primal SAR
asserts, unmoved to the digit (25.1096 / 40.5462 / 30.0142 / 38.6120 /
28.1459%). **17 new test items, all green, every one a step-3d record
re-measured through `post/`:** (i) `‖P_Ω E − E‖_Ω/‖E‖_Ω` = **18.7238%** at
`CG1_RECORD_RTOL`, with the **negative control** — the *global*
`post.project_to_cg1` on the same field over the same phantom, measured in the
same run at **1876.1871%** — giving a separation of **100.20×** against the
pre-registered **50×** floor (a promotion that kept integrating over `dx`
would read 1.0×); (ii) `a + b × x` **4.385695e-13** (anchor 1e-10) and
`x² ê_x` **3.741459e-01** (floor 1e-4), both bounds unmoved and the records
now printed beside them; (iii) pinned max |value| **0.000e+00** over owned
**and** ghost blocks at `-n 2`, census asserted at **170** free of **21 397**
owned blocks / **64 191** dofs (globally reduced, rank-count independent);
(iv) all six restricted solves `converged_reason` **2** in **25 / 25 / 25 /
25 / 21 / 25** its, now asserted as `== 2`, `21 ≤ its ≤ 25`, 64 191 dofs
(strengthened from the pre-existing `> 0`, which stays); (v) restricted
phantom power **5.440097168e-08 W** (−3.5058% from the primal record) and the
five identity readings **8.2868 / 9.4743 / 7.3477 / 6.8146 / 6.1185%** with
both controls **123.6255%** / **333.0778%**, all at `CG1_RECORD_RTOL`.
**Collateral:** the `project_to_cg1` docstring now carries 3c's finding as a
`.. warning::` — a *global* L² fit is not a field estimator inside a low-field
subdomain, with the 32.7802 / 1876.1871 / 838.8978% domain table and a pointer
at the restricted sibling — so it no longer lives only in known-issues.
**Scope, unchanged:** this packages an estimator, it does **not** register a
gate. The five primal asserts stay exactly as written and red, the module
still exits 1, no band, tolerance or record moved, no SAR claim comes into
existence, verdict (c) is unaffected, and `WF-6` stays **🟡**. `B` callers are
untouched by construction: no signature, default, band or record of
`project_to_cg1` moved.

**Step 3e′ executed 2026-09-02 06:00 slot — the estimator-degree rung, every
anchor green and the pre-registered clause (γ) printing with its own stated
cause excluded by the same run.** `post.project_to_cg1_restricted` gained a
keyword-only `degree: int = 1` (default unchanged; nothing CG1 moved) and was
driven at `degree=2` for six restricted mass solves on the same mesh, same four
fields, same 51 points, **no curl-curl solve**. Anchors: the degree-monotonicity
theorem holds — `‖P²_Ω E − E‖_Ω/‖E‖_Ω` **14.4724%** ≤ CG1's **18.7238%**; the
pre-registered flip landed at **10.6 decades** (`x² ê_x` 6.659346e-02 at degree
1 → **1.505524e-12** at degree 2 on one exact source), `a + b × x`
1.363313e-12; pinned max **0.000e+00** with 1 004 free of 160 537 owned CG2
blocks on 481 611 dofs; six solves reason **2** in 39–48 its; both controls
survive at 123.2927 / 327.6543%. **And the five identities got worse** —
**19.3491 / 17.2097 / 16.0699 / 14.4087 / 11.3230%** against CG1's 8.2868 /
9.4743 / 7.3477 / 6.8146 / 6.1185% (+5.2 to +11.1 pp) — while the phantom power
*improved* to 5.519662942e-08 W (−2.09% from the primal record vs CG1's
−3.51%). Since a mis-assembled restriction is excluded by the anchors, what is
measured is that **a globally better L² fit of `E` is pointwise worse for these
C4 identities at these 51 points**: the projector and the estimator's degree are
both now excluded as the mechanism, and the identity-from-a-fitted-field
construction itself is what a review must adjudicate (candidates in the
known-issues step-3d row). `20260902T110503Z_WF-6-step3e-prime.log`,
**`5 failed, 82 passed` / Status 1 / 125 s** at `-n 2` complex with
`tests/environment`, standard tier, well inside the 600 s ceiling so the
cost-wall fallback was never needed; printed table
`20260902T111000Z_WF-6-step3e-prime-verdict.log` (121 s). **No band moved, no
SAR gate registered, no SAR claim exists, the five primal asserts stay red and
`WF-6` stays 🟡.**

Step 1 scoped 2026-08-29
10:30 review. §10 subgoal 4 said the first B1+ chunk "can be scoped by the
daily review the day `PORT-9` closes" — that was 08-25, `PORT-11` followed
08-26, and the 08-25 operator directive says "do not block subgoal 4 on
F-human". Nothing in the repo computes B from a time-harmonic E outside two
copy-pasted example helpers, and nothing anywhere computes B₁⁺; the step is
therefore one small `post/` addition plus a gate module. Degree 1, per the
§10 production-order decision.)*
> * **Step 1 — the map at 10 MHz on the loaded F-small birdcage, from the
>   `PORT-9` single-drive field.** Standard tier, complex build, `-n 2`,
>   `main`. **Build:** (a) `src/fem_em_solver/post/faraday.py` —
>   `magnetic_flux_density_from_e(e_complex, omega)` = the
>   `curl(E)/(−jω)` DG0-vector interpolation that
>   `examples/ports/04_birdcage_four_port_sparameters.py:140-182`
>   (`_paraview_fields`) and `examples/ports/05_…:192-236` each carry a
>   private copy of, and `b1_plus(b_complex)` = `|B_x + jB_y|/2` (peak
>   phasor convention, the one `e_complex` is in); export both from
>   `post/__init__.py`, and make the two examples import the helper (their
>   guides do not change and the census must read `dead=0`). (b)
>   `tests/validation/test_birdcage_b1_plus_map.py`: reuse
>   `build_four_port_sweep` from `test_port_birdcage_four_port.py` for the
>   mesh/problem/specs (116 085 cells, one C4-symmetric phantom of tag 3,
>   `r = 0.03`, `z ∈ [−0.04, 0.04]`, on the coil axis) and the
>   `_solve_driven_p1` re-solve pattern from `examples/ports/04` — the sweep
>   returns no fields — for drives **P1 and P2** (two solves, undriven
>   ports at 50 Ω as in leg (d)). **Anchor (i), a conservation identity,
>   asserted:** three-way power accounting for each drive —
>   `½ Re(V_src · Ī)` at the driven sheet **=** `mean_sar(e, sigma=fields.sigma_field, rho=any, cell_tags, subdomain_ids=3)['dissipated_power_w']`
>   (phantom, ½∫σ|E|²) **+** the same integral over conductor tag 1 **+**
>   `Σ_i ½ |I_i|² Re Z_p,i` over all four sheets (driven included), pre-registered
>   band **1%** of the supplied power. The `TH-11` family reads
>   its complex-power identity at 1e-9, but the sheet-resistance term has
>   never been closed on this fixture, so 1% is the honest first band; the
>   measured residual is the record either way. **Anchor (ii), a symmetry
>   identity, asserted:** C4 covariance of the map — on a fixed set of
>   sample points in the phantom (cell centroids of tag 3 in `z ∈ [−0.02,
>   0.02]`, `r ≤ 0.02`, via `evaluate_vector_field_parallel`, never
>   `f.eval`), `|B₁⁺|` from the P2 drive at the point rotated by +90° about
>   z equals `|B₁⁺|` from the P1 drive at the point: assert the relative
>   ℓ² mismatch over the set **≤ 5%**, pre-registered as a *discretisation*
>   band — B is DG0 on a gmsh mesh that is not itself C4-symmetric, so the
>   ceiling is cell-to-cell scatter, not the 0.5% `ADJACENT_SPREAD_BAND`
>   the S-matrix classes meet. Print the mismatch, the centre-point
>   `|B₁⁺|`, and the phantom/conductor/sheet power shares. **Negative
>   control:** drop the conductor term from (i) — the identity must then
>   miss by the conductor share (σ = 800 S/m against the phantom's 0.5),
>   asserted `>` the 1% band; and rotate by +90° against the **P3** drive
>   (180° apart) for the covariance — must **exceed** the 5% band, since
>   the map from the opposite port is the 180° image, not the 90° one.
>   **Cost:** mesh ~22 s + three solves ~8 s each + integrals; the
>   `PORT-9` step 3d module is 66 s for four solves, so **≈ 75 s**,
>   `timeout -k 30 300`; the two examples re-run for the import change
>   through `./run_examples.sh` (`ports:4` 88 s, `ports:5` 139 s, host
>   side, docrefs `exit != 1`). **Traps:** complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; DG0 interpolation
>   of a UFL `curl` needs `fem.Expression` with the DG0 space's
>   interpolation points, complex dtype; `mean_sar` needs a `rho` — pass
>   `1000.0`, it does not enter `dissipated_power_w`; `sheet_terminal_current`
>   returns every port's `I_i`, read them from the case result, do not
>   re-derive; the `column power sum 0.793823974` is `Σ|S_ij|²`,
>   dimensionless — not a watt and not this gate; `run_examples.sh` runs on
>   the **host** (the `EX-32` trap); rank-safety on every integral
>   (`assemble_scalar` is rank-local). **Scope:** 10 MHz, F-small, single
>   drives, degree 1 — **no** quadrature drive, **no** homogeneity/CV number,
>   **no** 64/128 MHz, **no** literature or AED comparison, no SAR claim
>   (the phantom integral is a power term here, not a SAR map); on green
>   the chunk is **🟡** with step 1 ✅ — steps 2 (the quadrature-driven map
>   and its CV at 64/128 MHz on the `PORT-11` ladder) and 3 (`MAT-4`'s
>   coil-driven SAR through the same field, its one-month-stall fix) are
>   scoped by a review from step 1's shares. **Negative result:** (i)
>   missing by more than 1% is the finding — record the three shares and
>   the residual in a new known-issues entry, keep the assert, chunk stays
>   ⬜/🧪, stop (a sheet-power bookkeeping error and a real solver defect
>   look identical here and only a review separates them); (ii) above 5% is
>   reported the same way — never widen either band in-slot.
> * **Step 1 executed, 2026-08-29 13:30 implementer slot — built as written,
>   gate (i) green, gate (ii) red; the step's own negative-result clause
>   applied, so the chunk is 🧪 and `main` carries one deliberate red.**
>   `src/fem_em_solver/post/faraday.py` landed with
>   `magnetic_flux_density_from_e` and `b1_plus`, exported from `post/`, and
>   both `examples/ports/04`,`05` now import the helper instead of carrying a
>   private copy (each re-run green through the harness: `ports:4` 78 s Status 0
>   `…183919Z_WF-6-step1-examples.log`, `ports:5` 128 s Status 0
>   `…184042Z_WF-6-step1-examples-05.log`; the doc-reference census finds
>   **no dead reference to either example's artifacts**,
>   `…184303Z_WF-6-step1-docrefs.log`, its `dead=53 stale=2` being entirely
>   examples this slot did not run).
>   `tests/validation/test_birdcage_b1_plus_map.py` solves **four** single
>   drives on `build_four_port_sweep`'s 116 085-cell fixture (5.6–6.0 s each)
>   and reads:
>   **Gate (i) ✅** — the three-way accounting closes to **9.795751e-03** of the
>   supplied 6.856240413e-03 W at the P1 drive and **9.796209e-03** at P2,
>   inside the pre-registered 1e-2, with shares **0.0008% phantom /
>   6.5374% conductor / 92.4822% sheets** and the conductor-blind negative
>   control missing by 7.517001e-02 (7.7× the band). The sheet term dominating
>   at 92% is the honest reading of a 50 Ω termination on every port and is why
>   1% rather than 1e-9 was the right first band.
>   **Gate (ii) ❌ 8.6516% against 5%** on 51 tag-3 centroids
>   (`r ≤ 0.02`, `|z| ≤ 0.02`); `|B₁⁺|` mean 2.077398e-08 T at `V_src = 1 V`.
>   The 180° negative control **holds at 27.3161%** (3.2× the failing reading),
>   so the estimator resolves the drive azimuth; the ungated diagnostics say
>   the miss is *systematic* — pointwise deviation median 6.7395%, p90
>   15.0357%, max 17.5662%, and the **second 90° instance (P4 at −90°) reads
>   9.5808%**, alike to P2's. Both 90° instances agreeing rules out anything
>   peculiar to P2 and points at DG0 cell-scatter on a mesh that is not itself
>   C4-symmetric. Logs `…183450Z_WF-6-step1.log` (89 s, with
>   `tests/environment`) and `…183728Z_WF-6-step1-diagnostic.log` (87 s).
>   **No band was widened and no assert removed**, per the clause above.
>   **Step 1b is a review's call**, with two candidates already separated in the
>   known-issues entry: (a) the 5% band underestimated the DG0 scatter floor —
>   the remedy is a better estimator (CG1-projected `B`, volume-weighted
>   comparison, or a rotation-invariant sample set), not a looser band; (b) a
>   real C4 asymmetry in the field, which the fixture's ≤ 0.5% `Z` class spreads
>   bound an order of magnitude below this at the terminals. Steps 2 and 3 keep
>   their prerequisite: step 1's shares are now on record, but the map itself is
>   not gated until (ii) closes.
> * **Steps 1b and 1c — scoped 2026-08-29 18:00 review: separate candidate (a),
>   the DG0 estimator floor, from candidate (b), a real C4 asymmetry, by
>   measurement; neither moves the 5% band.** One fact the 10:30 scoping
>   missed and step 1 exposed: the sample set is **51 centroids** in a
>   0.02 m-radius × 0.04 m cylinder, i.e. ≈ 1 cm phantom cells on the 116 085-cell
>   fixture — a DG0 curl is piecewise constant over cells that size, so
>   cell-to-cell scatter of order 10% is not surprising, and the 5% band was a
>   guess against a floor nobody had measured. Both steps reuse
>   `tests/validation/test_birdcage_b1_plus_map.py`'s fixture (`b1_plus_map`,
>   four solves P1–P4, 5.6–6.0 s each, mesh ~22 s) and change nothing about
>   the module's asserts; each adds a new module or a new test function with
>   its own pre-registered assert. Two independent slots, ≈ 100–120 s each.
>   * **Step 1b — the estimator leg: CG1-projected `B` on the same 51 points.**
>     Standard, complex, `-n 2`, `main`. L²-project the DG0 `B_phasor`
>     (complex vector) onto `("Lagrange", 1, (3,))` with a mass-matrix
>     `LinearProblem` (not `interpolate` — DG0 → CG1 interpolation is
>     ill-defined at vertices), apply `b1_plus` to the projection, and read
>     it at the same 51 points and their ±90° / 180° images through
>     `evaluate_vector_field_parallel`. Print the DG0 and CG1 relative ℓ²
>     mismatches side by side for **P2 at +90°, P4 at −90°, P3 at 180°**
>     (the 180° identity is *also* a covariance identity — P3 is the 180°
>     image of P1 — and step 1 never read it; it is the sharpest discriminator
>     here: a DG0 scatter floor is the same at 90° and 180°, a C2-preserving
>     C4-breaking field asymmetry is not) and the pointwise median / p90 for
>     each. **Anchors, asserted:** (1) the DG0 P2-at-+90° reading reproduces
>     step 1's **8.6516%** at rtol 1e-4 (same mesh, same points — a record
>     reproduction, and the proof the projection leg reads the same field);
>     (2) gate (i)'s P1 residual reproduces **9.795751e-03** at rtol 1e-4;
>     (3) the mis-rotated control P3-at-+90° stays **> 5%** under *both*
>     estimators (the estimator must still resolve azimuth — a CG1
>     projection that smooths the 27.3% control below 5% has smoothed the
>     map away, and that is a negative result, not a pass). **Verdict bands,
>     pre-registered, recorded not asserted:** CG1 mismatch ≤ 5% at all three
>     covariance angles ⇒ candidate (a) — the review re-registers gate (ii)
>     on the CG1 estimator with the measured floor as its band's provenance;
>     CG1 90° readings stay ≥ 7% while CG1 180° reads ≤ 5% ⇒ candidate (b),
>     a C4-breaking asymmetry in the field — the review commissions a
>     field-side hunt (per-port sheet current phases, the phantom's
>     off-axis fit); all three stay ≥ 7% under CG1 ⇒ neither — the map's
>     azimuthal structure at these points is not resolved at ~1 cm cells and
>     step 1c's sample set decides. **Negative control:** anchor (3) above,
>     plus `evaluate_vector_field_parallel`'s `valid` mask must be all-true on
>     the images (a point outside the mesh silently drops out of the ℓ²).
>     **Cost:** mesh 22 s + four solves 24 s + one complex CG1 mass solve on
>     116 085 cells (≈ 5 s) + evaluations ≈ **100 s**, `-k 30 400`, one
>     window plus `tests/environment`. **Traps:** complex build +
>     `FEM_EM_REQUIRE_COMPLEX=1`; the mass-matrix `LinearProblem` needs
>     `petsc_options={"ksp_type": "cg", "pc_type": "jacobi"}` or it defaults
>     to LU on a 3-vector CG1 space (fine at this size, slow); rank-safety on
>     the ℓ² (gather values, the helper returns global arrays — check before
>     reducing twice); `-s`; do not touch the existing asserts or the 5%
>     constant. **Scope:** measurement only — no band moves, gate (ii) stays
>     red, the chunk stays 🧪, no CV, no 64/128 MHz. **Negative result:** any
>     reading is the finding — the three-angle × two-estimator table goes into
>     the known-issues `WF-6` entry and the slot stops; a CG1 that fails
>     anchor (3) is recorded as "the projection over-smooths at this
>     resolution" and the review looks at step 1c.
>   * **Step 1b executed, 2026-08-29 19:30 implementer slot — ✅ as scoped, and
>     the verdict is (a), the estimator floor. No band moved; gate (ii) is
>     still red and the chunk is still 🧪.** Built as written on
>     `test_birdcage_b1_plus_map.py`'s own `b1_plus_map` fixture (nothing in
>     `src/` changed, so no example re-run was owed): a `cg1_estimator_table`
>     module fixture L²-projects each drive's DG0 `B_phasor` onto
>     `("Lagrange", 1, (3,))` through a Hermitian mass-matrix `LinearProblem`
>     (CG/Jacobi, `ksp_rtol` 1e-12, `petsc_options_prefix` per 0.11) and forms
>     `|B_x + jB_y|/2` from the **evaluated** projected vector at the same 51
>     points — the magnitude is taken after the point evaluation, `|·|` being
>     non-linear. Log `20260830T003238Z_WF-6-step1b.log`, `1 failed, 15 passed`
>     / Status 1 / **98 s** with `tests/environment`; the single failure is
>     gate (ii) itself, untouched.
>     **Anchors, all three green:** DG0 P2-at-+90° reproduces **8.6516%** and
>     gate (i)'s P1 residual reproduces **9.795751e-03**, both at rtol 1e-4;
>     the mis-rotated control P3-at-+90° stays outside 5% under *both*
>     estimators (DG0 **27.3161%**, CG1 **23.2642%**); `valid` all-true, 51 of
>     51, on every rotated image.
>     **The table (recorded, in the known-issues entry too):** `+90°` DG0
>     8.6516% │ CG1 **2.1870%**; `−90°` DG0 9.5808% │ CG1 **2.1146%**;
>     `180°` DG0 8.5970% │ CG1 **1.8911%**. CG1 is inside 5% at all three
>     covariance angles ⇒ the pre-registered **candidate (a)** branch. The
>     sharpest single reading is the 180° column, which step 1 never had: DG0
>     misses by 8.5970% there, the *same* as at +90°, which is what a
>     scatter floor looks like and is not what a C2-preserving, C4-breaking
>     field asymmetry would produce — candidate (b) is unsupported by any
>     reading on this fixture. The projection moves the mean `|B₁⁺|` by 0.38%
>     (2.077398e-08 → 2.069556e-08 T), so it smooths the scatter and not the
>     map.
>     **What is owed next, and to whom:** re-registering gate (ii) on the CG1
>     estimator with this table as the band's provenance is a **review's
>     call**, explicitly not the slot's. Step 1c stays worth running as
>     scoped — it is independent, and a ring-set DG0 reading near 8–9% would
>     confirm the floor is the DG0 scatter itself rather than the centroid
>     sampling, which is the one thing this leg cannot distinguish.
>   * **Step 1c — the sample-set leg: a rotation-invariant point set at DG0.**
>     Standard, complex, `-n 2`, `main`; **independent of 1b** (it does not
>     need 1b's result and must not wait for it). Replace the centroid sample
>     with a set closed under the C4 rotation: rings at `r ∈ {0.005, 0.010,
>     0.015, 0.020}` m, `z ∈ {−0.015, 0, +0.015}` m, **8 azimuths** (45°
>     steps) — 96 points, every point's ±90° and 180° image a member of the
>     set, all inside the tag-3 phantom (radius 0.03, `|z| ≤ 0.04`). Read the
>     DG0 `|B₁⁺|` map from P1 on the set once, and the P2 / P4 / P3 maps on
>     the rotated set, and print the relative ℓ² mismatch at +90°, −90° and
>     180°, plus the mismatch **per ring** (each `(r, z)` separately) so the
>     radial structure of the scatter is on record. **Anchors, asserted:** (1)
>     `valid` all-true on all 96 points and every image (the set is inside
>     the phantom by construction — a false here is a geometry mistake);
>     (2) the P1 map on the set is itself **C4-invariant as a set of values
>     only if the mesh were symmetric — it is not, so assert nothing on that;
>     instead** assert the record reproduction of gate (i)'s **9.795751e-03**
>     at rtol 1e-4 and of the centroid-set DG0 **8.6516%** at rtol 1e-4 (the
>     module's existing reading, re-printed from the same fixture); (3) the
>     mis-rotated control P3-at-+90° **> 5%** on the ring set. **Verdict
>     bands, recorded not asserted:** the ring-set +90° / −90° / 180°
>     mismatches against the centroid set's 8.65 / 9.58 / (1b's 180°)
>     figures — agreement within ±2 pp says the sample set is not the
>     mechanism and the floor is the DG0 scatter itself; a per-ring
>     pattern (inner rings ≤ 5%, outer ≥ 10%, or the reverse) is a
>     structure the review reads against the coil geometry. **Cost:** same
>     fixture, no projection ≈ **90 s**, `-k 30 400`. **Traps:** the ring
>     points must not sit exactly on a cell facet — jitter the azimuth start
>     by 3.7° (a point on a facet returns whichever cell the locator finds
>     first, rank-dependently); the rotation must be the *fixture's* P1→P2
>     angle read from the sheet frames as `b1_plus_map` already does, not a
>     literal 90°; complex build, `-s`, `evaluate_vector_field_parallel`
>     only. **Scope / negative result:** as 1b — table into the known-issues
>     entry, chunk stays 🧪, no band moves.
>   * **Step 1c executed, 2026-08-29 22:30 implementer slot — ✅ as scoped, and
>     the verdict is "the sample set is not the mechanism". No band moved;
>     gate (ii) is still red and the chunk is still 🧪.** Built as written on
>     `test_birdcage_b1_plus_map.py`'s own `b1_plus_map` fixture (nothing in
>     `src/` changed, no example re-run owed, no new solve — only the points
>     changed): a `ring_set_table` module fixture reads the DG0 `|B₁⁺|` of the
>     four existing drives on 96 points closed under the C4 rotation — `r ∈
>     {0.005, 0.010, 0.015, 0.020}` m × `z ∈ {−0.015, 0, +0.015}` m × 8
>     azimuths in 45° steps, start jittered 3.7° so no point sits on a
>     coordinate plane (and so plausibly on a cell facet, where the locator's
>     answer is rank-dependent). The rotation is again the fixture's own
>     P1→P2 sheet separation, 90.000000°. Log
>     `20260830T033147Z_WF-6-step1c.log`, `1 failed, 18 passed` / Status 1 /
>     **97 s** with `tests/environment`; the single failure is gate (ii)
>     itself, untouched.
>     **Anchors, all three green:** `valid` **96 of 96** on all four drives
>     and every rotated image (the set is interior by construction);
>     centroid-set DG0 P2-at-+90° reproduces **8.6516%** and gate (i)'s P1
>     residual **9.795751e-03**, both at rtol 1e-4; the mis-rotated control
>     P3-at-+90° reads **25.8213%** on the ring set, asserted outside 5%.
>     **The table (recorded, in the known-issues entry too), ring set vs the
>     centroid set:** `+90°` **9.9271%** vs 8.6516% (**+1.28 pp**); `−90°`
>     **9.9519%** vs 9.5808% (**+0.37 pp**); `180°` **8.4706%** vs 1b's
>     8.5970% (**−0.13 pp**). Every angle inside ±2 pp ⇒ the pre-registered
>     **"sample set is not the mechanism"** branch: the centroid set's lack of
>     closure under the rotation was not manufacturing the miss, and the ~9%
>     floor is the DG0 scatter itself. Together with 1b this is a two-sided
>     result — change the estimator and the miss falls 4–5×, change the sample
>     set and it does not move.
>     **Per-ring structure, for the review:** no monotone radial trend
>     (6.33…11.65% across the `r = 0.010` rings, 4.61…12.63% across
>     `r = 0.020`); lowest ring `r = 0.020, z = +0.015` at 4.61 / 6.21 /
>     3.96%, highest `r = 0.005, z = −0.015` at 11.25 / 12.27 / 6.52%. A
>     ring-to-ring spread of the same order as the overall figure is what a
>     per-cell scatter looks like. `|B₁⁺|` over the ring set, P1 driven: mean
>     2.023327e-08 T, max 3.263326e-08, min 1.419703e-08.
>     **What is owed next:** unchanged from 1b — re-registering gate (ii) on
>     the CG1 estimator with 1b's table as provenance is a **review's call**,
>     now with 1c's corroboration that the sampling is not the confound.
>   * **Step 1d — re-register gate (ii) on the CG1-projected estimator
>     (ruled 2026-08-30 02:15 weekly review; ruling text in the known-issues
>     `WF-6` entry — that session died before writing this bullet, the 10:30
>     daily review wrote it from the ruling).** Standard, complex, `-n 2`,
>     `main`. **Build:** (a) `post/faraday.py` gains
>     `project_to_cg1(b_dg0)` — the Hermitian mass-matrix `LinearProblem`
>     (CG/Jacobi, `ksp_rtol` 1e-12, `petsc_options_prefix`) step 1b's
>     `cg1_estimator_table` fixture already carries, moved into the package
>     and exported from `post/__init__.py`; the test fixture calls it. The DG0
>     `magnetic_flux_density_from_e` is kept as the raw curl. (b) In
>     `test_birdcage_b1_plus_map.py`,
>     `test_b1_plus_map_is_c4_covariant_under_the_drive_rotation` becomes the
>     CG1 covariance identity at **all three angles** (+90°, −90°, 180°) on
>     the 51 centroids against the **unchanged** `C4_COVARIANCE_BAND = 5e-2`;
>     the DG0 readings are printed and cited in-comment with their records
>     (8.6516 / 9.5808 / 8.5970%), not gated — gating a DG0 curl on a
>     non-symmetric mesh gates the mesh, not the map (`GEO-19` step-C
>     precedent). **Anchors, asserted:** CG1 mismatches reproduce step 1b's
>     **2.1870 / 2.1146 / 1.8911%** at rtol 1e-3 (a record reproduction with
>     2.3× headroom under 5%; p90 ≤ 3.47%); gate (i)'s **9.795751e-03**
>     unchanged at rtol 1e-4; the mis-rotated control P3-at-+90° stays
>     **> 5%** under CG1 (record **23.2642%**); `valid` 51/51 on every
>     image. **Negative control:** the mis-rotated control, plus the DG0
>     print must still read 8.6516% — a DG0 column that moved means the
>     projection changed the field, not the estimator. **Cost:** the module
>     is 98 s with the CG1 fixture (`20260830T003238Z`); `-k 30 400`; the
>     `src/` change owes `ports:4` (78 s) and `ports:5` (128 s) re-runs via
>     `./run_examples.sh` on the host (docker-socket denial ⇒ the §9 runner
>     substitution), docrefs `exit != 1`. **Traps:** the projection is
>     applied to the complex 3-vector and `|B_x + jB_y|/2` is formed from
>     the **evaluated** projection (`|·|` is non-linear); helper returns
>     global arrays — do not reduce twice; `-s`; complex build +
>     `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first. **Scope:** on
>     green the chunk is **🟡 with step 1 ✅** (a symmetry identity — no CV,
>     homogeneity or absolute-accuracy claim follows); steps 2–3 stay serial
>     on it and are scoped by a review; the known-issues entry and `main`'s
>     deliberate red retire with the landing. **Negative result:** CG1 not
>     reproducing 1b's table at rtol 1e-3 is a finding about the projection
>     path — record the new column in the known-issues entry, keep the old
>     DG0 gate red, stop; never widen the 5%.
>   * **Step 1d executed, 2026-08-30 12:00 implementer slot — ✅ as scoped.
>     Gate (ii) closes on the CG1 estimator, `main`'s deliberate red retires,
>     and `WF-6` is 🟡 with step 1 ✅.** Built as written. (a)
>     `post/faraday.py` gained `project_to_cg1(b_dg0)` — step 1b's Hermitian
>     mass-matrix `LinearProblem` (CG/Jacobi, `ksp_rtol` 1e-12, local PETSc
>     import per the `current_divergence` precedent), exported from
>     `post/__init__.py`, with the DG0 `magnetic_flux_density_from_e` kept
>     untouched as the raw curl; the test module's fixture-local
>     `_project_to_cg1` is gone and the fixture calls the package function.
>     (b) `test_b1_plus_map_is_c4_covariant_under_the_drive_rotation` is now
>     the CG1 covariance identity at **all three** angles against the
>     **unchanged** `C4_COVARIANCE_BAND = 5e-2`, each angle *also* asserted
>     against step 1b's record at rtol 1e-3 (a drifting reading would slip
>     through 2.3× of headroom otherwise); the DG0 column is printed and cited
>     in-comment, never gated.
>     **Anchors, all green:** CG1 **2.1870 / 2.1146 / 1.8911%** at +90° /
>     −90° / 180°, reproducing 1b exactly; gate (i)'s **9.795751e-03** at
>     rtol 1e-4; mis-rotated control P3-at-+90° **23.2642%** under CG1,
>     outside the band; `valid` 51/51 on every image. **Negative control:**
>     the DG0 print still reads **8.6516 / 9.5808 / 8.5970%** (asserted at
>     rtol 1e-4) — the projection changed the estimator, not the field.
>     Log `20260830T170242Z_WF-6-step1d.log`, **19 passed / Status 0 / 97 s**
>     with `tests/environment`, complex, `-n 2`.
>     **The `src/` change's owed re-runs, both green:** `ports:4` 76 s
>     Status 0 (`20260830T170431Z_WF-6-step1d-examples.log`), `ports:5` 127 s
>     Status 0 (`20260830T170559Z_WF-6-step1d-examples-05.log`) — the runner's
>     docker-socket denial recurred and the §9 substitution was used for both.
>     Doc-reference census `exit=1`, `dead=53 guide=0 stale=2`
>     (`20260830T170816Z_WF-6-step1d-docrefs.log`): no `ports_04_*` or
>     `ports_05_*` artifact among the dead, so these two examples' references
>     are live and the 53 are `EX-36`'s, unchanged.
>     **What this does and does not claim:** gate (ii) is a **symmetry
>     identity** on one fixture at 10 MHz. No B₁⁺ homogeneity, CV or
>     absolute-accuracy claim follows, and §2 is not moved by it. Steps 2–3
>     stay serial on step 1 and are a review's to scope.
>   * **Step 2 — scoped 2026-08-30 18:00 review: the quadrature drive by
>     exact superposition, at 10 MHz on the same fixture; two symmetry
>     identities and the first (ungated) homogeneity figures.** The four
>     single-drive solves already in `b1_plus_map` share one mesh, one
>     `V_src`, and the same linear sheet law on every port in every solve
>     (`V = V_src − I·Z_p`, `Z_p = 50 Ω`), so the field of all four ports
>     driven at once with phases `φ_k` is **exactly** `Σ_k e^{iφ_k} E_k` —
>     no new solve, no new plumbing. **Build:** `post/faraday.py` gains
>     `b1_minus` (`|B_x − jB_y|/2`, the counter-rotating component) beside
>     `b1_plus`, exported; a new module
>     `tests/validation/test_birdcage_b1_quadrature.py` forms the two
>     rotation senses `B_ccw = Σ e^{+ikπ/2} B_k`, `B_cw = Σ e^{−ikπ/2} B_k`
>     in port order, projects each through `post.project_to_cg1`, and reads
>     `|B₁⁺|` / `|B₁⁻|` on the 51 centroids through
>     `evaluate_vector_field_parallel`. **Anchors, asserted:** (a)
>     **C4-invariance** — advancing the phase pattern by one port is a 90°
>     rotation of the drive and multiplies the superposed field by a global
>     phase, so `|B₁⁺|_ccw(R₉₀ x) = |B₁⁺|_ccw(x)`: relative L² ≤ **5e-2**
>     (`C4_COVARIANCE_BAND`, whose CG1 provenance is step 1d's 2.19 / 2.11 /
>     1.89% — a superposition of four fields each inside the floor is inside
>     it); (b) **the mirror identity** — a 4-leg birdcage has a mirror plane
>     through each port and `B` is a pseudovector, so reversing the rotation
>     sense equals reflecting: `|B₁⁺|_ccw(x) = |B₁⁻|_cw(M x)`, `M` the
>     reflection in the plane through port 1's azimuth, at the 51 centroids'
>     mirror images, relative L² ≤ **5e-2** (the same floor — a
>     non-symmetric mesh enters at the same order as in (a)); (c) step 1's
>     records reproduce — gate (i) **9.795751e-03** at rtol 1e-4, the three
>     CG1 covariance readings at rtol 1e-3. **Reported, not gated (no
>     closed form; §2 does not move):** the centre-point polarisation purity
>     `|B₁⁺|/|B₁⁻|` for each sense (an ideal quadrature birdcage gives ∞ for
>     one and 0 for the other — the number MRI cares about), mean `|B₁⁺|`
>     at 1 V per port, and the **CV** of `|B₁⁺|_ccw` over the 51 centroids
>     and over step 1c's 96-point ring set — the first homogeneity figures,
>     labelled as such. **Negative controls:** the mis-paired comparison
>     `|B₁⁺|_ccw(x)` vs `|B₁⁺|_cw(M x)` must **miss** the 5% band (an ideal
>     birdcage makes one of them ≈ 0 at the centre; assert > 5% only, as
>     step 1d's 23.26% control does); the P1 single drive's centre purity is
>     printed as the "what a non-rotating field reads" line (linear
>     polarisation ⇒ `|B₁⁺| ≈ |B₁⁻|`). **Cost:** the map fixture is 97 s
>     (mesh ~22 s, four solves 5.6–6.0 s); two extra CG1 projections and the
>     point reads add ≤ 15 s — **≤ 120 s**, standard, `-n 2`, `-k 30 400`,
>     complex + `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first. The
>     `src/` change owes `ports:4` (76 s) and `ports:5` (127 s) re-runs and
>     the docrefs census (`exit 1` from `EX-36`'s 53 is not this step's).
>     **Traps:** the reflection plane goes through a **port** — read its
>     azimuth off the fixture, the legs need not sit on the coordinate axes;
>     magnitudes are taken *after* the point evaluation; the mirrored
>     centroids are fresh points — assert `valid` 51/51 on them too; the
>     phase sign convention only has to be consistent between the two
>     senses; helper returns global arrays; runner on the host,
>     docker-socket substitution. **Scope:** 10 MHz, F-small, degree 1,
>     superposition only — no simultaneous-source solve, **no 64/128 MHz**
>     (step 2b on the `PORT-11` ladder, serial on this landing), no
>     homogeneity *claim* (CV is a printed number), no SAR (step 3), no
>     literature or AED comparison; on green the chunk stays **🟡** with
>     steps 1–2 ✅. **Negative result:** (a) or (b) missing 5% is a finding
>     about the superposition path or the mirror assumption — record both
>     readings in a known-issues entry, keep the assert, stop; never widen
>     the band.
>
>     **Executed 2026-08-31, 22:30 slot — ✅, both identities green at the
>     CG1 floor.** `post.b1_minus` landed beside `b1_plus` (shared private
>     `_rotating_component`, exported from `post`), and
>     `tests/validation/test_birdcage_b1_quadrature.py` built the two senses
>     by superposing the four DG0 curls and projecting each through
>     `project_to_cg1`. **17 passed / Status 0 / 96 s**, log
>     `20260831T033704Z_WF-6-step2.log`.
>     * **(a) C4-invariance 0.9818%** and **(b) mirror identity 0.8087%**,
>       both against the **unmoved, imported** `C4_COVARIANCE_BAND = 5e-2` —
>       i.e. inside step 1d's single-drive floor (2.19 / 2.11 / 1.89%) rather
>       than merely inside the band, which is the right expectation for a sum
>       of four fields each inside that floor. 51/51 points valid on all three
>       image sets (`x`, `Rx`, `Mx`).
>     * **Negative controls, both fired.** The mis-paired
>       `|B₁⁺|_cw(Mx)` vs `|B₁⁺|_ccw(x)` reads **95.1975%** (asserted `> 5%`
>       only); the P1 single drive's centre purity is **1.0006**, a linear
>       polarisation splitting evenly between the senses exactly as it must.
>     * **Reported, ungated, and labelled in the log as such:** centre
>       `|B₁⁺|/|B₁⁻|` = **127.9083** (ccw) and **0.0081** (cw) — the
>       polarisation-purity number MRI cares about, on one unconverged
>       fixture; mean `|B₁⁺|_ccw` **7.976427e-08 T** at 1 V per port; **CV
>       2.7563%** over the 51 centroids and **2.4577%** over step 1c's 96-point
>       ring set. No homogeneity *claim* is made or entered in §2.
>     * **The premise is asserted, not assumed:** a separate test reads the
>       four specs' `port_impedance_ohm` and `drive_voltage_v` and the four
>       solves' `source_voltage_v` and requires one value each — superposition
>       is exact only because the operator is shared.
>     * **A sign-convention error was made, measured and fixed before the
>       commit, and the band never moved.** The first run
>       (`20260831T033416Z_WF-6-step2.log`, Status 1) paired `e^{+jkπ/2}` with
>       an azimuth-*increasing* `k`, which makes the gated sense the
>       counter-rotating one: its centre purity read **0.0081** against the
>       other sense's **127.91**, and both identities came back at **18.8192%
>       / 20.2202%** — ~10× the CG1 floor, the signature of a ~2%
>       discretisation error on a quantity suppressed ~120× by cancellation.
>       In the `e^{jωt}` convention the sense `B₁⁺` reads is driven by a
>       pattern that *lags* with azimuth, so the exponent sign was corrected by
>       that derivation (the measurement is the confirmation, not the reason).
>       Both readings are recorded in the module and in `attempts.md`.
>     * **Owed re-runs, all green:** `ports:4` 76 s Status 0
>       (`20260831T033900Z_…-examples-04.log`), `ports:5` 127 s Status 0
>       (`…034019Z_…-examples-05.log`), doc-reference census `dead=53 guide=0
>       stale=10` unmoved (`…034237Z_…-docrefs.log`; the `exit=1` is `EX-36`'s
>       53, not this step's).
>     * **Scope held.** 10 MHz, F-small, degree 1, superposition only. No
>       simultaneous-source solve, no 64/128 MHz, no SAR, no absolute or
>       tuning claim; §2 is not moved. Steps 1–2 ✅ and the chunk stays 🟡.
>
> * **Step 2b — the same identities at the Larmor frequencies, 64 and
>   128 MHz, on the `PORT-11` mesh (scoped 2026-08-31 03:00 review).**
>   Standard tier, complex build, `-n 2`, `main`; no `src/` change. Every
>   B₁⁺ number on record is 10 MHz: the fixtures hard-code it —
>   `build_four_port_sweep()` takes no frequency
>   (`tests/validation/test_port_birdcage_four_port.py:219–300`, `FREQUENCY_HZ`
>   imported at `:114`) — while the identical construction already runs at
>   64/128 MHz through `_four_port_rung(name, offsets, frequency_hz=…,
>   reuse=…)` (`tests/validation/test_port_birdcage_leg_offset_sweep.py:199–455`),
>   the `PORT-11` / `EX-34` / `ANS-4` route, at **5.6–5.7 s per solve,
>   frequency-flat** (`ANS-4`'s `metrics.json`: 22.7 / 22.9 / 22.5 s per
>   four-solve rung). **Build:** `build_four_port_sweep(frequency_hz=
>   FREQUENCY_HZ)` — one keyword argument with the existing default, so the
>   10 MHz fixture is bit-identical — and a new
>   `tests/validation/test_birdcage_b1_larmor.py` that builds the sweep once
>   per frequency (module-scoped, mesh built once and reused across the two
>   frequencies as `ANS-4` does; **only floats and numpy arrays escape the
>   solve helper** — the `TH-13` step-2 teardown deadlock), then runs the
>   step-1d and step-2 readings unchanged in *form*: gate (i) at P1, the
>   single-drive CG1 covariance at +90 / −90 / 180°, the quadrature (a)
>   C4-invariance and (b) mirror identity, the mis-paired control, purity and
>   CV printed. **Anchors (imported, unmoved):** gate (i) ≤ 1e-2 of supplied
>   power at each frequency; (ii) and (a)/(b) ≤ `C4_COVARIANCE_BAND` = 5% at
>   each frequency; `valid` 51/51 on all image sets; cell count = 116 085
>   (`STEP2_CELL_COUNT`) with ratio 1.000000; the 10 MHz rows of the same
>   module reproduce 2.1870 / 2.1146 / 1.8911% and 0.9818 / 0.8087% at rtol
>   1e-3 (the control that the frequency argument is the only thing that
>   moved). **What is unknown, and why this item is informative either
>   way:** the 5% band's provenance is a **10 MHz** floor measurement (CG1
>   2.19 / 2.11 / 1.89%, 2.3× headroom); nobody has measured whether the CG1
>   floor holds at 64 MHz (cells/λ phantom 21.89) or at 128 MHz (12.50, the
>   `PORT-11` step-3 floor of 10). A miss at 128 MHz with 64 MHz green is a
>   resolution finding about the B₁⁺ estimator, not a formulation defect.
>   **Negative controls:** the mis-paired `|B₁⁺|_cw(Mx)` vs `|B₁⁺|_ccw(x)`
>   > 5% at each frequency (10 MHz reads 95.20%); the P1 linear purity ≈ 1
>   printed. **Reported, ungated, labelled:** centre `|B₁⁺|/|B₁⁻|` per sense,
>   mean `|B₁⁺|` at 1 V per port, CV over the 51 centroids and the 96-point
>   ring, at each frequency, beside the 10 MHz record (127.91 / 0.0081 /
>   7.976427e-08 T / 2.7563%) — the first Larmor-frequency B₁⁺ numbers in
>   the repo, and **still identities on one unconverged fixture**, not a
>   homogeneity claim. **Cost:** mesh ~22 s + 8 solves ≈ 46 s + 8 curls and
>   CG1 projections (step 2's module ran 96 s for four) ≈ **200–260 s**;
>   `timeout -k 30 600`; if the 10 MHz rows are included for the reproduction
>   control, 12 solves ≈ 300 s — still one command. **Traps:** the CG1
>   projection is a mass-matrix `LinearProblem` (CG/Jacobi, rtol 1e-12), keep
>   it; `|B₁⁺|` is real stored complex — magnitudes after the point
>   evaluation; `PHANTOM_CELLS_PER_LAMBDA_FLOOR = 10` is `PORT-11`'s gate,
>   import it and print cells/λ at each rung rather than re-deriving; the
>   superposition premise (shared `Z_p`, `V_src`) is asserted per frequency.
>   **Scope:** degree 1, F-small, the two Larmor frequencies, symmetry
>   identities only; no SAR (step 3), no absolute, tuning or homogeneity
>   claim; §2.2's "every 64/128 MHz claim is an identity on one fixture"
>   stands. Steps 1–2b ✅ leaves the chunk 🟡. **Negative result:** any
>   identity missing the band at either frequency — known-issues entry with
>   every reading and the cells/λ beside it, keep the assert, stop; **never
>   widen the band, never re-register it in-slot** (that is what step 1d's
>   ruling was for, and it was a review's).
>
>   **Executed 2026-08-31 (09:00 slot) — green on the first run, chunk
>   stays 🟡.** Built as written: `build_four_port_sweep(frequency_hz=…,
>   reuse=…)` — two additive keywords on the `_four_port_rung` precedent,
>   both defaulting to today's behaviour, no `src/` change — and
>   `tests/validation/test_birdcage_b1_larmor.py`, which imports every
>   helper, band and record from steps 1/1c/1d/2 and restates none.
>   **One mesh, 116 085 cells (ratio 1.000000), three rungs, 12 solves at
>   5.44–5.99 s each; `16 passed` / Status 0 / 202 s at `-n 2`**
>   (`20260831T140418Z_WF-6-step2b.log`), against the 200–260 s estimate.
>     * **Every identity inside the unmoved, imported 5% band at all three
>       frequencies.** Gate (ii) at +90 / −90 / 180°: **2.1870 / 2.1146 /
>       1.8911%** (10 MHz), **2.2187 / 2.1667 / 1.9574%** (64 MHz),
>       **2.1315 / 2.1735 / 1.9511%** (128 MHz). Quadrature (a) C4 /
>       (b) mirror: **0.9818 / 0.8087%**, **0.9570 / 0.7570%**,
>       **0.9106 / 0.6968%**. Gate (i) P1 residual **9.7958e-03 /
>       9.5231e-03 / 9.2445e-03** against 1e-2, its conductor-blind
>       control 10.19 / 10.19 / 13.05% (P2 rows within 4e-5 of the P1
>       rows at every rung).
>     * **Controls all held**, and are the reason the readings mean
>       something: mis-rotated `P3@+90deg` **23.2642 / 24.7535 / 25.2589%**
>       and mis-paired `|B₁⁺|_cw(Mx)` **95.1975 / 95.1118 / 95.1161%**,
>       both asserted strictly outside the band; `valid` 51/51 on every
>       drive and image set and 96/96 on the ring set; the shared
>       `Z_p` = 50 Ω / `V_src` = 1 V premise asserted per rung.
>     * **The reproduction control is exact.** The 10 MHz rung of the new
>       module reproduced all five step-1d/step-2 records at rtol 1e-3 —
>       so the two Larmor columns differ from it by the frequency keyword
>       and nothing else.
>     * **The pre-registered 128 MHz resolution question is answered, and
>       the answer is "no miss".** Phantom cells/λ **69.1393 / 21.8936 /
>       12.5024** against `PORT-11`'s imported floor of 10; the five
>       identities are flat in frequency to ≈ 0.1 pp across a 12.8×
>       frequency span and a 5.5× resolution span. The CG1 floor the 5%
>       band rests on — a 10 MHz measurement — therefore survives at
>       12.5 cells/λ **on this fixture, for these symmetry quantities**.
>       That is a statement about the estimator, not about accuracy: a
>       symmetry identity is blind to any error the C4 rotation shares.
>     * **First Larmor-frequency B₁⁺ figures in the repo — reported,
>       ungated, labelled.** Centre purity `|B₁⁺|/|B₁⁻|` ccw **127.91 /
>       141.81 / 171.94**, cw 0.0081 / 0.0087 / 0.0092, P1 linear
>       1.0006 / 1.0024 / 1.0031 (the "what a non-rotating field reads"
>       line, ≈ 1 at every frequency). Mean `|B₁⁺|` at 1 V per port
>       **7.976427e-08 / 6.500452e-08 / 4.936577e-08 T**, falling with
>       frequency as the loaded coil's terminal current does. CV
>       **2.7563 / 2.7738 / 3.0177%** over the 51 centroids and 2.4577 /
>       2.3847 / 2.5400% over the 96 ring points. **None of these is a
>       homogeneity claim**: no converged mesh, no real drive, no tuning —
>       §2.2's "every 64/128 MHz claim is an identity on one fixture"
>       stands unchanged.
>     * **Scope held.** Degree 1, F-small, symmetry identities only; no
>       SAR, no absolute, tuning or homogeneity claim; §2 did not move.
>       Steps 1, 2 and 2b ✅ and the chunk stays **🟡** — step 3 (SAR) is
>       a review's to scope.
>
> **Step 3 scoped 2026-08-31 10:30 review — coil-driven SAR symmetry
> identities at 10 MHz (§9 item 2).** The subgoal-4 SAR route goes through
> the same solved field as B₁⁺, and `_power_shares` already calls
> `post.mean_sar` for gate (i)'s phantom term — this step changes what is
> *read*, not what is computed. New
> `tests/validation/test_birdcage_sar_map.py`, importing every helper, band
> and record from `test_birdcage_b1_plus_map.py` /
> `test_birdcage_b1_quadrature.py` (`ANS-1`'s rule): the point-SAR map
> `σ|E|²/(2ρ)` via `post.point_sar` on the 51 phantom centroids (E is the
> primal N1curl field — no curl, no DG0/CG1 projection chain, so the CG1
> floor story does not transfer and nobody has measured this estimator's
> floor). **Anchors (bands imported, unmoved):** (i) C4 covariance of the
> single-drive SAR map P1 → P2/P3/P4 at +90/−90/180° ≤ the imported 5%
> band; (ii) the quadrature SAR map (superpose the four `E` fields with
> the step-2 phase convention, *then* square) is C4-invariant ≤ 5% and
> satisfies the mirror identity `SAR_ccw(x) = SAR_cw(Mx)` ≤ 5%; (iii)
> `mean_sar`'s `dissipated_power_w` on P1 reproduces gate (i)'s phantom
> share record at rtol 1e-3 (conservation cross-check against the step-1
> record, not a new band). **Pre-registered ceiling note (rubric #2):** SAR
> is quadratic in `E`, so a symmetric-error argument allows ~2× the B₁⁺
> map's ~2.2% covariance floor — 5% is therefore a real bar, not a
> giveaway, and the mis-rotated control (B₁⁺ analogue read 23–25%) is the
> separation. **Negative controls:** the mis-rotated single-drive
> comparison > 5%; the mis-paired quadrature sense > 5%; the σ-blind
> `mean_sar` control (score against σ = 0 in the conductor tag) from the
> `MAT-4` machinery where cheap. **Recorded, ungated, labelled:** peak and
> mean point-SAR at 1 V per port, peak-to-mean ratio, for both the P1 and
> the quadrature drive. **Cost:** mesh ~22 s + four solves ~24 s + point
> evaluations ≈ **120 s**, standard, complex, `-n 2`, `-k 30 400`.
> **Traps:** `point_sar` takes the *split* `e_real`/`e_imag` fields and a
> scalar σ — assert the phantom-σ-uniform premise before using it;
> magnitudes after point evaluation; only floats/arrays escape the solve
> helper; no `<=` on complex operands. **Scope:** 10 MHz, F-small,
> degree 1, symmetry identities plus one reproduction — **no** SAR10g /
> C95.3 (that is `MAT-4` step 2 + `WF-7`), no mass-averaged claim, no
> Larmor SAR (a later step mirrors 2b's rung pattern), no absolute claim;
> chunk stays 🟡. **Negative result:** an identity missing is an estimator
> finding exactly like step 1's DG0 floor — known-issues entry with every
> reading, keep the assert, stop; whether point-SAR needs its own
> re-registered band is the next review's ruling, never in-slot.
>
> **Step 3 executed 2026-08-31 13:30 slot — the pre-registered negative
> result: every SAR identity misses, the controls and the reproduction
> hold, and the finding is the estimator.** New
> `tests/validation/test_birdcage_sar_map.py`, everything imported
> (fixture, sample set, band, records, phase convention);
> `20260831T183526Z_WF-6-step3.log`, **`5 failed, 16 passed` / Status 1 /
> 96 s** at `-n 2` complex with `tests/environment`, against the ≈ 120 s
> estimate.
>
>   * **The five identities, band 5% imported and unmoved:** single-drive
>     C4 `SAR_P2(Rx)` **25.1096%**, `SAR_P4(−Rx)` **40.5462%**,
>     `SAR_P3(180°)` **30.0142%**; quadrature C4 **38.6120%**; mirror
>     `SAR_cw(Mx)` vs `SAR_ccw(x)` **28.1459%**. The `|B₁⁺|` analogues on
>     the *same* points, same drives, same band read 2.19 / 2.11 / 1.89%
>     and 0.98 / 0.81%.
>   * **Everything that could have made it a defect instead passes.**
>     Controls: mis-rotated `SAR_P3(Rx)` **129.8187%**, quadrature vs
>     single drive **334.5786%**, both asserted `> 5%`. Anchor (iii):
>     `mean_sar`'s phantom `dissipated_power_w` on P1 =
>     **5.637745667e-08 W**, reproducing gate (i)'s record to every
>     printed digit. Premise: phantom σ flat at **0.5 S/m** over 537
>     tag-3 cells, asserted before a scalar σ is handed to `point_sar`;
>     all 51 points of every image set evaluated (`point_sar` raises
>     rather than zero-filling).
>   * **The diagnosis is in the run, not in a hypothesis.** The three
>     single-drive readings use only step 1's solved fields and step 1d's
>     own image sets — no superposition, no mirror, no code this step
>     introduced — and they already miss by 25–40%. What changed is the
>     estimator: `|B₁⁺|` is read off an L²-projected CG1 `B`, SAR
>     pointwise off the **primal N1curl `E`** with no projection. A
>     Whitney `E` is normally discontinuous, so its centroid value carries
>     an O(h) per-cell error the C4 rotation does not share, and squaring
>     doubles it — 25–40% ≈ 2× a ~13–20% pointwise `|E|` floor. Step 1's
>     8.65% DG0 curl, one estimator further out.
>   * **One scoped control was degenerate and is reported instead of
>     asserted.** The mirror-omitted comparison `SAR_ccw(Mx)` vs
>     `SAR_ccw(x)` reads **28.1445%** against identity (iii)'s 28.1459% —
>     the mirror moves it by 1.4e-3 pp. SAR is a magnitude-squared with no
>     ± senses to mis-pair, so step 2's `|B₁⁺|_cw(Mx)` analogy does not
>     carry; the module prints this ungated (docstring says why) and
>     asserts the two controls that do separate. Disposition is the
>     review's.
>   * **Reported, ungated, labelled:** point SAR at 1 V per port — P1
>     peak **7.630679e-07** W/kg, mean **1.453536e-07** W/kg, peak/mean
>     **5.2497**; quadrature peak **2.065442e-06** W/kg, mean
>     **7.706353e-07** W/kg, peak/mean **2.6802**. Not safety figures.
>   * **Collateral, verified:** the phase convention now lives in one
>     place — `quadrature_phase_weights` in
>     `test_birdcage_b1_quadrature.py`, called by that module's fixture
>     and by this one, so the two legs cannot drift on the thing step 2
>     paid a run to get right. Step 2 re-ran green and unmoved:
>     `20260831T183734Z_WF-6-step3-step2-regression.log`, **`6 passed` /
>     Status 0 / 80 s**, identities 0.9818 / 0.8087%, control 95.1975%.
>   * **Five deliberate reds on `main`** with a known-issues entry
>     carrying every reading (🔴 OPEN 2026-08-31). **No band moved**,
>     `WF-6` stays **🟡**, and **no SAR claim exists** — the step measured
>     that the coil-driven point-SAR map is not yet gateable at the B₁⁺
>     band, which is a finding, not a gate. **Resolves with** a step-3b
>     estimator leg on step 1b's pattern: the same identities off an
>     L²-projected CG1 `E` beside the primal column, no new solve, ≈ 96 s
>     — a review's to scope.
>
> **Step 3b scoped 2026-08-31 18:00 review — the estimator comparison,
> on step 1b's pattern (§9 item 1 carries the executable plan).** A
> second module fixture `sar_map_cg1`: `post.project_to_cg1` on each
> solve's `e_complex` (its check is value shape `(3,)`, which N1curl
> satisfies — the same mass projection 1d used on `B`), split on the
> projection's own space, `point_sar` on exactly step 3's image sets, the
> quadrature senses by superposing the CG1 dof arrays with the imported
> phase weights (linear, so equal to projecting the superposition).
> **Asserted:** the primal column reproduces step 3's five readings
> (25.1096 / 40.5462 / 30.0142 / 38.6120 / 28.1459%) and both controls
> (129.8187 / 334.5786%) at `CG1_RECORD_RTOL`, exported as
> `STEP3_PRIMAL_*` records; the CG1 column's two controls stay `> 5%`
> (the projection must not smooth them away); the `mean_sar` record; the
> five primal asserts untouched and red. **Printed, not gated:** the five
> CG1 identity readings with a pre-registered verdict — **(a)** all ≤ 5%
> with controls surviving → pointwise-`E` estimator floor, the next review
> re-registers the SAR gate on CG1 as 1d did; **(b)** 180° in, ±90° out →
> something rotation-specific in the field, a review reads it; **(c)** all
> out → the ~1 cm phantom cells do not resolve a quadratic-in-`E` map at
> this band, a finer-rung question for the weekly review. The
> mis-paired-sense comparison is **struck** from SAR scopings (degenerate
> at 1.4e-3 pp, measured). Collateral, constants only: the module's step-2
> literals switch to `EX-39`'s exported `STEP2_*`. ≈ 130 s, `-n 2`,
> standard. **No band moves in-slot; `WF-6` stays 🟡 under every
> verdict.**
>
> **Step 3b executed 2026-08-31 19:30 slot — verdict (c) prints, and the
> run's own diagnostics say (c)'s pre-registered *reason* is the wrong
> one: the finding is `project_to_cg1` on an N1curl `E`, not the
> phantom's resolution.** `20260901T003300Z_WF-6-step3b.log` (105 s) and
> `20260901T003548Z_WF-6-step3b-diagnostic.log` (100 s, the added
> projection diagnostic), both **`5 failed, 25 passed` / Status 1** at
> `-n 2` complex with `tests/environment`, against the ≈ 130 s estimate.
>
>   * **The anchor held to every digit.** The primal column reproduced
>     step 3's five identities — 25.1096 / 40.5462 / 30.0142 / 38.6120 /
>     28.1459% — and both controls — 129.8187 / 334.5786% — at
>     `CG1_RECORD_RTOL`, now exported as `STEP3_PRIMAL_IDENTITY_RECORDS` /
>     `STEP3_PRIMAL_CONTROL_RECORDS` with the log line as provenance. The
>     five primal asserts are untouched and are the run's five failures.
>   * **The CG1 column is worse than the primal one everywhere**
>     (printed, never gated): **152.0459 / 109.7797 / 169.5050 / 53.1869 /
>     40.8440%**. Both CG1 controls survive the projection and are
>     asserted — 163.6144 / 75.9135% against the 5% band — so the
>     pre-registered verdict evaluates, in code, to **(c)**.
>   * **(c)'s pre-registered reading does not survive the same run.** The
>     CG1 phantom power `½∫σ|E_cg1|²` reads **1.990062891e-05 W** against
>     the primal record 5.637745667e-08 W (**+35 198.9%**; step 1d's `B`
>     projection moved its mean by 0.38%), and the diagnostic re-run's
>     `‖E_cg1 − E‖/‖E‖` over the phantom reads **1876.1871%**. A
>     projection cannot be 19× its own argument in the region being read
>     *and* be a coarse-but-honest estimator of it, so the measurement is
>     about the projector applied to `E`, not about ~1 cm phantom cells
>     failing to resolve a quadratic map. The estimator step 1d registered
>     for the DG0 `B` phasor is **not, as landed, a usable `E`
>     estimator on this fixture**; the `|B₁⁺|` gates are untouched, since
>     they project `B` and its 0.38% figure is unchanged.
>   * **Nothing moved that a negative result may not move.** No band, no
>     tolerance, no assert; the mis-paired-sense comparison stayed struck;
>     the module carries no step-2 numeric literals, so the scoped
>     `STEP2_*` collateral was a no-op (recorded so the next review does
>     not re-scope it). Five deliberate reds on `main`, unchanged in count
>     and in value. **No SAR claim exists** and `WF-6` stays **🟡**.
>   * **Owed next, for a review to scope (in known-issues' new "Resolves
>     with"):** separate the three candidates for the projector finding —
>     a global L² fit dominated by the sheet/conductor-edge `E`
>     singularities; a non-converged CG/Jacobi mass solve at `ksp_rtol`
>     1e-12 on a vector CG1 space over 116 085 cells, which the helper
>     never checks; or an element-side mismatch that the value-shape
>     `(3,)` guard does not catch. One slot: print the KSP converged
>     reason and iteration count, and read `‖E_cg1 − E‖/‖E‖` over the
>     whole mesh beside the phantom-restricted figure.
> **Step 3c scoped 2026-09-01 03:00 review — the projector diagnosis, §9
> item 6.** Separate the three candidates in one slot, on the step-3b
> module (`tests/validation/test_birdcage_sar_map.py`, the `sar_map_cg1`
> fixture), no new solve. **(i)** The mass solve's convergence:
> `post.project_to_cg1` builds a `LinearProblem` and discards its solver —
> expose it behind an opt-in kwarg (default off, the `B` callers untouched)
> and assert `getConvergedReason()` **> 0** with `getIterationNumber()`
> printed; the expected value is `KSP_CONVERGED_RTOL` (2) at `ksp_rtol`
> 1e-12 / `ksp_atol` 1e-30, and `DIVERGED_ITS` (−3) at PETSc's 10 000-step
> default is what candidate 2 looks like. **(ii)** The exact-reproduction
> control: interpolate `f = a + b × x` — in `N1curl₁ ∩ CG1³` — into the
> solve's own N1curl space on the fixture mesh (as a complex `Function`;
> the helper refuses real inputs), project it, and assert
> `‖P f − f‖_{L²(Ω)}/‖f‖ ≤ 1e-10`: a pass refutes candidate 3 (an
> element-side mismatch), a fail confirms it. The control's control is
> `f = x² ê_x` (∉ CG1³), whose residual must read **> 1e-3**. **(iii)**
> Printed, not gated: `‖E_cg1 − E‖/‖E‖` over the **whole mesh** beside the
> phantom figure (1876.1871%, re-asserted at rtol 1e-3 as a record) and
> over a **phantom core** — phantom cells none of whose vertices lie on the
> phantom boundary (cell→vertex connectivity, rank-local; reduce every norm
> with `assemble_scalar` + `allreduce`). A whole-mesh figure ≪ the phantom's
> says the global fit is dominated elsewhere (candidate 1, the sheet /
> conductor-edge `E`); a core figure ≪ the phantom's says the mechanism is
> the CG1 smear of the normal-`E` jump at the σ interface — which no
> vertex-continuous space represents — and the honest `E` estimator is
> phantom-restricted or cellwise, a review's step 3d to scope. **Anchors:**
> (i), (ii); every step-3b record (primal and CG1 columns, both control
> sets, phantom power, the 1876% figure) reproducing at `CG1_RECORD_RTOL`;
> the five deliberate reds kept exactly. **Negative control:** the `x²`
> field's residual, and the mis-rotated CG1 control still asserted > 5%.
> **Cost:** step 3b ran 100–105 s; two extra 116 085-cell vector mass solves
> ≈ 10 s → **≈ 130 s**, `timeout -k 30 400`, `tests/environment` first.
> **Traps:** no `<=` on complex operands; `project_to_cg1`'s default `name`
> — pass one per field; the module's five primal asserts stay red and the
> run's exit stays 1 — the anchors are read from the log, as 3b's were.
> **Scope:** a diagnosis of the projector — no band, no SAR gate, no
> re-registration, nothing in `src/` beyond the opt-in diagnostics return;
> `WF-6` stays 🟡 whatever prints. **Negative result:** (ii) failing or (i)
> ≤ 0 *is* the finding — known-issues "Resolves with" row, keep every
> assert, do not raise the iteration cap in-slot, stop.
>
> **Step 3c executed 2026-09-01 07:30 slot — the projector is a projector;
> candidates 2 and 3 are refuted and candidate 1 is what the domain table
> says.** `20260901T123421Z_WF-6-step3c.log`, standard tier, complex, `-n 2`
> with `tests/environment`, **`5 failed, 38 passed` / Status 1 / 103 s**
> against the ≈ 130 s estimate. The five failures are step 3's five primal
> asserts, unmoved to the digit (25.1096 / 40.5462 / 30.0142 / 38.6120 /
> 28.1459%); every step-3b record — primal and CG1 identity columns, both
> control sets, the CG1 phantom power 1.990062891e-05 W, the 1876.1871%
> phantom residual — reproduced at `CG1_RECORD_RTOL` and is now asserted.
>
>   * **(i) The mass solve converges.** `converged_reason` **2**
>     (`KSP_CONVERGED_RTOL`) in **26** iterations on **64 191** CG1 dofs at
>     `ksp_rtol` 1e-12 — **candidate 2 (a non-converged Jacobi/CG mass solve
>     the helper never checks) is refuted.** The solver is now readable
>     through an opt-in `return_diagnostics` kwarg on `post.project_to_cg1`
>     (default off; every `B` caller untouched).
>   * **(ii) The projector reproduces what `CG1³` contains, exactly.**
>     `f = a + b × x`, interpolated into the solve's own N1curl space as a
>     complex `Function` and projected, leaves `‖P f − f‖/‖f‖` =
>     **1.326607e-13** against the 1e-10 anchor (reason 2, 23 its); the
>     control's control `x² ê_x` leaves **9.882703e-02**, above the 1e-3
>     floor (reason 2, 26 its). **Candidate 3 (an element-side mismatch the
>     value-shape `(3,)` guard misses) is refuted:** `project_to_cg1` *is*
>     the L² projection it documents, on N1curl input.
>   * **(iii) The domain table says candidate 1.** `‖E_cg1 − E‖/‖E‖` reads
>     **32.7802%** over the **whole mesh**, **1876.1871%** over the
>     **phantom** and **838.8978%** over the **phantom core** (33 of 537
>     owned tag-3 cells, no vertex on the phantom boundary). The whole-mesh
>     figure is **57× below** the phantom's: the global L² fit is a fit of
>     the regions that dominate `‖E‖` — the sheets and conductor edges — and
>     the phantom, whose `|E|` is orders of magnitude smaller, is a
>     rounding-error corner of it. That is **candidate 1, measured.** The
>     σ-interface smear is present but secondary: excluding every cell that
>     touches the phantom boundary halves the residual (1876 → 839%) and
>     leaves it O(10), so the interface jump is not the mechanism either.
>   * **What this closes and what it does not.** `post.project_to_cg1`
>     needs no fix — the `|B₁⁺|` gates that use it are untouched and remain
>     correct (they read `B` where `B` is not 10³ times larger elsewhere).
>     What is wrong is the *use*: a **global** L² projection is not an `E`
>     estimator inside a low-field subdomain of a fixture with a huge-field
>     region. The honest estimator is phantom-restricted (project on the
>     phantom submesh) or cellwise; scoping that is **step 3d**, a review's
>     call, not this slot's. **No band moved, no assert loosened, nothing
>     re-registered, no SAR claim exists** and `WF-6` stays **🟡**.
>
> **Step 3d — scoped 2026-09-01 10:30 review from 3c's three readings (§9
> item 9): the phantom-restricted CG1 `E` estimator, and the five identities
> read off it.** 3c's domain table said the *use* is wrong, not the
> projector: a global L² fit on this fixture is a fit of the sheet /
> conductor-edge `E`, and the low-`|E|` phantom gets its tail (whole mesh
> 32.78% vs phantom 1876.19%, 57× apart). The two routes 3c named are not
> equal. **Cellwise is struck by derivation, not run:** a degree-1
> first-kind N1curl function is `a + b × x` on every cell, which `DG1³`
> contains, so a per-cell L² projection onto `DG1³` reproduces the primal
> `E` exactly and its point readings *are* the primal column (25.11 /
> 40.55 / 30.01 / 38.61 / 28.15%); a per-cell projection onto `DG0³` is the
> cell average, which discards the in-cell variation and keeps every
> inter-cell jump — neither is an estimator, and the slot does not spend a
> window confirming what the polynomial degrees already say. **The
> phantom-restricted route, on the parent mesh** — no submesh, no
> cross-mesh interpolation of an N1curl field (an unpaid trap): in the
> step-3b module, a sibling of `post.project_to_cg1` (test-local first;
> `post/` only if a review later promotes it) whose mass matrix and load
> are `ufl.inner(u, v) * dx(3)` / `ufl.inner(E, v) * dx(3)` with
> `dx = Measure("dx", subdomain_data=cell_tags)` on the **same**
> `("Lagrange", 1, (3,))` space, and every CG1 dof with no phantom-cell
> support pinned to zero through a `dirichletbc` (dofs =
> complement of `fem.locate_dofs_topological(space, tdim,
> phantom_cells)`, taken over owned **and ghost** dofs so the pin is
> consistent across ranks; `phantom_cells` from `cell_tags.find(3)`
> including ghosts — the restricted mass matrix is SPD on the phantom
> vertex set, so CG + Jacobi at `ksp_rtol` 1e-12 stands; read the
> `converged_reason` through the same opt-in diagnostics pattern 3c
> landed). Four restricted projections (P1–P4), the two quadrature senses
> by superposing dof arrays (linear, as 3b), `point_sar` on exactly the 51
> points, the two controls (mis-rotated `SAR_P3(Rx)`; quadrature vs single
> drive) exactly as 3b built them. **Anchors (asserted):** (i) the
> best-approximation inequality — `P_Ω` minimises `‖· − E‖_Ω` over all of
> `CG1³|_Ω`, and the global projection restricted to the phantom is one
> member of that set, so `‖P_Ω E − E‖_Ω / ‖E‖_Ω ≤ 1876.1871%` (3b/3c's
> record, `STEP3B_PHANTOM_PROJECTION_RESIDUAL`) is a theorem about the
> code, and a violation is a bug in the restriction, not a finding about
> SAR; the separation factor is printed; (ii) the exact-reproduction
> control under the restriction — `f = a + b × x` (`PROJECTOR_FIELD_A/B`)
> interpolated complex into the solve's N1curl space and restricted-
> projected leaves `‖P_Ω f − f‖_Ω / ‖f‖_Ω ≤ 1e-10` (`PROJECTOR_EXACT_
> RESIDUAL`), and outside the phantom the pinned dofs read exactly 0;
> (iii) `converged_reason > 0` on all six restricted solves; (iv) every
> 3b/3c record reproduced at `CG1_RECORD_RTOL` — primal identities and
> controls, the global-CG1 identities and controls, the CG1 phantom power
> 1.990062891e-05 W, the 1876.1871% residual, the whole-mesh 32.7802%
> and core 838.8978% — and the five primal asserts kept **exactly as
> written and red**. **Negative controls:** the restricted CG1 column's
> two controls asserted `> C4_COVARIANCE_BAND` (the primal ceilings are
> 129.8 / 334.6%, 3b's global-CG1 read 163.6 / 75.9% — a restricted
> control landing under 5% is itself the finding); the control's control
> `x² ê_x` under the restriction, printed and asserted `> 1e-4` — the
> global reading was 9.882703e-02, the restricted one is a quadratic's
> CG1 fit error over the phantom, of order `(h/D)²`, and no phantom this
> mesh resolves at ~1 cm cells has `D/h` above 100, so 1e-4 is the
> arithmetic floor, not a tuned one. **Printed, journaled, NOT gated:** the
> five restricted-CG1 identity readings and the restricted phantom power
> `½∫_Ω σ|E_Ω|²` beside the primal 5.637745667e-08 W and the global-CG1
> 1.990062891e-05 W (+35 199%), with 3b's **pre-registered three-way
> verdict** printed beside them, unchanged: **(a)** all five ≤ 5% with both
> restricted controls > 5% → a pointwise-`E` estimator floor exists on
> this fixture, and the next review re-registers the SAR gate on the
> restricted estimator exactly as 1d did for `|B₁⁺|`; **(b)** the 180°
> column ≤ 5% but a ±90° column misses → something the rotation does not
> share in the field itself (sheet / mesh asymmetry) — a review reads it;
> **(c)** all five miss → with the projector exonerated (3c) and the
> global-fit tail removed (this step's (i)), the residual miss is the
> fixture's resolution of a quadratic-in-`E` map at ~1 cm phantom cells,
> and a finer rung is the weekly review's question, costed against
> `TH-11`'s memory wall. **Cost:** 3c ran 103 s; six restricted mass
> solves on a matrix that is identity outside the phantom add ≈ 20 s →
> **≈ 130 s**, standard tier, complex, `-n 2`, `tests/environment` first,
> `timeout -k 30 400`. **Traps:** the helper refuses real inputs —
> interpolate the controls as complex; `locate_dofs_topological` on a
> blocked space returns block indices — build the zero BC from a zero
> `fem.Function(space)` and those indices, never a scalar `Constant`; the
> complement must be taken over `size_local + num_ghosts` blocks or the
> ghost rows go unpinned and the two-rank solve differs from the one-rank
> one (this is what `-n 2` is for); `cell_tags.find` and every norm are
> rank-local — `assemble_scalar` + `allreduce` on every figure; `point_sar`
> takes `np.real` of each split field — split the complex CG1 arrays as
> 3b did, never hand the complex function twice; do **not** add the
> mis-paired-sense comparison (degenerate for a magnitude-squared, step 3);
> the module's exit stays 1 (five deliberate reds) — read the anchors from
> the log as 3b/3c did; no `<=` on complex operands. **Scope:** an
> estimator comparison on one fixture at 10 MHz — **no band moves
> in-slot, no SAR gate is registered, nothing re-registered, no
> homogeneity / absolute / C95.3 claim, `WF-6` stays 🟡 whatever prints**;
> nothing under `src/` unless the review promotes the helper afterwards.
> **Negative result:** whichever verdict prints is the deliverable —
> journal it in this bullet and the known-issues "Resolves with (step 3c's
> finding)" row, keep every assert, stop; anchor (i) *failing* is a defect
> in the restriction (pinning or measure), to be journaled as such and
> not read as physics; a 3b/3c record not reproducing is a fixture
> finding, not a rescope.
>
> **Step 3d executed 2026-09-01 13:30 slot, every anchor green on the first
> run — the restricted estimator is an honest `E` estimator and it takes the
> five identities from 25–40% to 6.1–9.5%, but all five still miss 5%, so the
> pre-registered verdict prints (c).**
> `20260901T183416Z_WF-6-step3d.log`, standard tier, complex, `-n 2` with
> `tests/environment`, **`5 failed, 52 passed` / Status 1 / 123 s** against the
> ≈ 130 s estimate. The five failures are step 3's five primal asserts,
> unmoved to the digit (25.1096 / 40.5462 / 30.0142 / 38.6120 / 28.1459%); every
> 3b/3c record reproduced at `CG1_RECORD_RTOL`, and step 3c's other two domain
> figures (whole mesh 32.7802%, phantom core 838.8978%) are now asserted too.
>
>   * **(i) The best-approximation inequality holds, with room to spare.**
>     `‖P_Ω E − E‖_Ω/‖E‖_Ω` = **18.7238%** against the global fit's
>     **1876.1871%** on the same phantom — a **100.20×** separation, not a
>     marginal pass. 3c's diagnosis is thereby confirmed constructively: the
>     1876% was the global fit's tail, and restricting the fit to the region it
>     is read over removes it.
>   * **(ii)/(iii) The restriction is a projection.** `f = a + b × x`
>     restricted-projected leaves **4.385695e-13** over `dx(3)` (anchor 1e-10);
>     the control's control `x² ê_x` leaves **3.741459e-01**, two orders above
>     the arithmetic `(h/D)² ≳ 1e-4` floor (the *global* figure was 9.88e-02 —
>     the restriction makes the quadratic *harder* to fit, as a smaller domain
>     with the same `h` should). Pinned dofs read **exactly 0.000e+00** on owned
>     and ghost blocks at `-n 2`; **170** of 21 397 owned CG1 blocks are free.
>     All six restricted mass solves return `converged_reason` **2**
>     (`KSP_CONVERGED_RTOL`) in 21–25 iterations on 64 191 dofs.
>   * **The restricted phantom power corroborates it independently.**
>     `½∫_Ω σ|E_Ω|²` = **5.440097168e-08 W**, i.e. **−3.51%** against the primal
>     record 5.637745667e-08 W — against the *global* CG1 projection's
>     +35 198.9% (1.990062891e-05 W, −99.73% from here). A projection does not
>     conserve power, so −3.5% is the size an honest `E` fit over this phantom
>     has; +35 199% was not.
>   * **The five identities, printed and NOT gated:** **8.2868 / 9.4743 /
>     7.3477 / 6.8146 / 6.1185%** (primal 25.11 / 40.55 / 30.01 / 38.61 /
>     28.15%; global CG1 152.05 / 109.78 / 169.51 / 53.19 / 40.84%). Both
>     restricted controls survive and are asserted: **123.6255%** (mis-rotated)
>     and **333.0778%** (quadrature vs single drive) — the fit did not smooth the
>     azimuthal structure away, it removed the estimator noise. So the estimator
>     column improved by 3–6× at every identity and by 20× against the global
>     one, and **still misses the 5% band at every one of the five**: the
>     pre-registered verdict evaluates to **(c)**, all five outside.
>   * **What (c) means now, with 3c and this step's (i) both in hand.** The
>     projector is exonerated (3c) and the global-fit tail is removed (this step,
>     100× separation, power to −3.5%), so the residual 6.1–9.5% is what is left
>     when the estimator is right: **the fixture's ~1 cm phantom cells reading a
>     quadratic-in-`E` map**. That is (c)'s pre-registered reading, and this time
>     the diagnostics do not contradict it — unlike step 3b, where they relocated
>     the finding. A finer phantom rung is **the weekly review's question, costed
>     against `TH-11`'s memory wall**; it is not this bullet's to scope. The
>     restricted helper stays test-local (`_project_to_cg1_restricted` in
>     `tests/validation/test_birdcage_sar_map.py`); promoting it into `post/` is a
>     review's call. **No band moved, no assert loosened, no SAR gate registered,
>     nothing re-registered, nothing under `src/`, no SAR claim exists** and
>     `WF-6` stays **🟡**.
>
> **Steps 3e and 3e′ scoped 2026-09-01 18:00 review** — the two questions
> step 3d left that are a *daily* review's, both named by the step-3d
> known-issues "Resolves with" row and neither of them the finer-mesh rung
> (that stays the weekly's, costed against `TH-11`).
>
>   * **Step 3e — promote `_project_to_cg1_restricted` into `post/`**
>     (§9 item 1). Its best-approximation anchor (18.7238% vs the global
>     fit's 1876.1871%, 100.20×), its exact-reproduction control
>     (4.385695e-13) and its ghost-safe pinning (170 free of 21 397 owned
>     blocks, pinned max \|value\| exactly 0.000e+00 at `-n 2`) are all
>     measured and asserted, which is the bar step 1d cleared before
>     `project_to_cg1` was packaged for `B`. It is the only `E` estimator
>     this repo has that reproduces the phantom power to 3.5%. Collateral:
>     a docstring warning on `post.project_to_cg1` that a *global* L² fit
>     is not an `E` estimator inside a low-field subdomain — 3c's finding,
>     which currently lives only in known-issues. **No gate is registered
>     and no band moves**; `WF-6` stays 🟡.
>   * **Step 3e′ — the estimator-degree rung** (§9 item 4). Verdict (c)
>     attributes the residual 6.1–9.5% to the fixture's ~1 cm phantom cells
>     reading a quadratic-in-`E` map, but nothing has separated *estimator
>     degree* from *mesh h* on this fixture. A CG2³ restricted projection
>     of the same four solved fields on the same mesh separates them for
>     the cost of six mass solves and no curl-curl solve, and it is a
>     different axis from the weekly's finer-mesh question, not a
>     pre-emption of it. The anchor is a theorem — the restricted
>     best-approximation residual cannot *increase* with degree — and the
>     control's control flips sign of difficulty: `x² ê_x` lies in CG2³
>     exactly, so where CG1 left 3.741459e-01 the CG2 fit must reproduce it
>     to ~1e-10, a 9-decade pre-registered separation. **A null result (the
>     five identities do not move) is the informative outcome**: it
>     corroborates (c) and hands the weekly a question about h alone.
>
> **Step 3e′ executed 2026-09-02 06:00 slot — every anchor green on the first
> run, and the pre-registered clause that printed is (γ), whose own stated
> cause the same run excludes.** `post.project_to_cg1_restricted` gained a
> keyword-only `degree: int = 1` (default unchanged, so no CG1 caller, record or
> band moved; the space and the bc's zero `Function` are both built from it, and
> `degree < 1` raises), and the test module drives it at `degree=2` for six
> restricted mass solves on the same 116 085-cell mesh, the same four solved
> fields, the same 51 points, the same pinning — **no curl-curl solve**.
>
>   * **Anchors, all asserted, all green.** (i) *Degree monotonicity*, a theorem
>     about the code: `‖P²_Ω E − E‖_Ω/‖E‖_Ω` = **14.4724%** against the imported
>     CG1 bound **18.7238%** — the CG2³ fit is strictly *better* in the norm it
>     minimises, as `CG1³ ⊂ CG2³` requires. (ii) The pre-registered **flip**
>     landed: `x² ê_x` restricted-projects at degree 2 to **1.505524e-12**
>     (bound 1e-10) where the **same exact source** at degree 1 reads
>     **6.659346e-02** — a measured separation of **10.6 decades**, one source,
>     one operator, one difference. (iii) `a + b × x` **1.363313e-12**.
>     (iv) Pinned max |value| exactly **0.000e+00** over owned *and* ghost
>     blocks at `-n 2`; census **1 004 free of 160 537** owned CG2 blocks on
>     **481 611** dofs (reported, not asserted — no CG2 record exists) against
>     CG1's 170 / 21 397 / 64 191. (v) All six CG2 solves `converged_reason`
>     **2**, in **48 / 48 / 48 / 48 / 39 / 47** its (reported, not gated).
>     (vi) Every step-3d/3e CG1 record reproduced unmoved in the same window.
>     Negative control: both step-3b controls **survive** the higher-degree fit
>     at **123.2927%** and **327.6543%** (CG1: 123.6255 / 333.0778%).
>   * **The printed verdict, which is the deliverable: (γ).** The five
>     identities off the CG2-restricted `E` read **19.3491 / 17.2097 / 16.0699 /
>     14.4087 / 11.3230%** against CG1's **8.2868 / 9.4743 / 7.3477 / 6.8146 /
>     6.1185%** and primal's 25.11 / 40.55 / 30.01 / 38.61 / 28.15% — every one
>     **worse** than CG1 by **+11.06 / +7.74 / +8.72 / +7.59 / +5.20 pp**, so
>     the pre-registered arithmetic selects (γ). CG2-restricted phantom power
>     **5.519662942e-08 W**, **−2.0945%** from the primal record 5.637745667e-08 W
>     — *closer* than CG1's −3.51%.
>   * **But (γ)'s pre-registered cause — "the CG2 restriction is mis-assembled,
>     and anchors (i)/(ii) should have caught it" — is excluded by this run's
>     own anchors**, which are green with orders of room, and the log says so on
>     its own line rather than leaving a reviewer to act on the clause's prose.
>     What is actually measured is that **a globally better L² fit of `E` over
>     the phantom is pointwise *worse* for these C4 identities at these 51
>     points**: the CG1 fit's extra smoothing was flattering the identities, not
>     resolving them. Both of the mechanisms this fixture has named — the
>     projector (3b/3c) and now the estimator's **degree** — are excluded, and
>     verdict (c)'s attribution to mesh `h` is neither confirmed nor refuted:
>     step 3f will now be read knowing a better estimator can *raise* these
>     numbers. **This is a finding about the identity-from-a-fitted-field
>     construction and it is a review's to adjudicate, not a slot's** — the
>     candidates are written into the known-issues step-3d row (read the
>     identities as phantom *integrals* rather than at 51 sampled points; or
>     re-run step 1c's sample-set control on this column; or run 3f anyway).
>   * **Scope, unchanged and observed:** no band moved, no tolerance moved, **no
>     SAR gate registered**, no homogeneity / absolute / C95.3 claim, the five
>     primal asserts stay exactly as written and red, the module still exits 1,
>     and **`WF-6` stays 🟡**. 13 new test items, all green.
>     `20260902T110503Z_WF-6-step3e-prime.log`, **`5 failed, 82 passed` /
>     Status 1 / 125 s** at `-n 2` complex with `tests/environment` (11 passed)
>     in the same window — **standard tier, against the item's 250–400 s
>     estimate and its 600 s ceiling, so the pre-registered cost-wall fallback
>     (drop to the four single drives) was never needed**; the printed table is
>     `20260902T111000Z_WF-6-step3e-prime-verdict.log` (same content, `-s`,
>     121 s) and the pre-caveat table run is
>     `20260902T110734Z_WF-6-step3e-prime-table.log` (module only, 99 s).
>     Cost note for the weekly: CG2³ was **7.50×** the CG1 dofs and cost about
>     **2×** the CG1 iterations, and the whole window still fits in 125 s
>     because the restricted mass matrix is identity outside 537 cells.
>
> **Step 3f scoped 2026-09-02 weekly review — the finer-phantom rung, costed
> against `TH-11` and found cheap.** The `TH-11` memory wall was 2.81 M cells
> on a *coil* refinement; the phantom here is a few hundred ~1 cm cells inside
> a 116 085-cell mesh, so halving the phantom sizing alone (`phantom_resolution`
> 0.01 → 0.005, ≈ 8× phantom cells) adds **≈ 5–10 k cells**, not millions, and
> the four-drive sweep stays standard tier (`PORT-11` step 1 priced 116 k
> cells at ≈ 25 s/solve at `-n 2`; budget ≈ 150 s for four solves + six
> restricted mass solves, `timeout -k 30 600`). Execute after step 3e′ (they
> answer different axes; if 3e′ printed (α), stop and re-plan instead).
> **Anchors:** (i) the coil-side records must not move — gate (i) power
> accounting and the `|B₁⁺|` C4 identities reproduce at `CG1_RECORD_RTOL`
> on the new mesh (they are mesh-converged at the ~2% floor; a move > 0.5 pp
> is a fixture finding); (ii) the restricted estimator's best-approximation
> inequality and exact-reproduction control hold on the new mesh (≤ the
> 18.7238% / 1e-10 records); (iii) the five SAR identities off the
> restricted `E` are **printed, not gated**, with the verdict pre-registered
> here: **(a)** all five ≤ 5% ⇒ (c) confirmed, and the daily review may then
> register the coil-driven SAR gate on the restricted estimator at the finer
> rung — the first coil-driven SAR gate in the repo; **(b)** they fall but
> stay > 5% ⇒ report the ratio (one halving should roughly quarter a
> second-order residual, 6–9.5% → 1.5–2.5%; a ratio near 1 says h is not the
> mechanism either) and stop; **(c)** unchanged ⇒ neither degree nor h — a
> review re-reads the identities themselves. **Negative control:** both
> step-3b controls asserted to survive on the new mesh. Scope: one rung on
> F-small at 10 MHz; no band moves in-slot; `WF-6` stays 🟡 whatever prints.
> Negative result: the printed verdict is the deliverable — journal, stop.
>
> **Annotation, 2026-09-02 03:00 daily review — the knob named above does not
> exist yet, so step 3f is not queueable as written.** `birdcage_port_domain`
> (`src/fem_em_solver/io/mesh.py:3069`) takes one global `resolution`
> (0.015, a gmsh `setSize` everywhere) and an optional `conductor_resolution`
> Threshold field; `phantom_resolution` is a parameter of the *coil+phantom*
> family's `coil_phantom_region_resolution_policy` (`mesh.py:2378`), not of
> the birdcage constructor, and `build_four_port_sweep` reaches the mesh only
> through `tests/mesh/test_birdcage_port_sheets._build`, which passes the
> module constants `RESOLUTION` / `CONDUCTOR_RESOLUTION` and nothing else. The
> phantom's ~1 cm cells are simply the global 0.015 (537 cells in a
> π·0.03²·0.08 m³ cylinder ⇒ h ≈ 1.5 cm). Halving the *global* resolution
> would refine air and coil too and is not the cheap rung the weekly costed.
> **Step 3f₀ (scoped by this review, §9 item 4)** adds the knob:
> `phantom_resolution: Optional[float] = None` on `birdcage_port_domain`, a
> gmsh Constant/Box field over the phantom cylinder taken into the existing
> `Min` of size fields, and a `phantom_resolution=` passthrough on `_build`
> and `build_four_port_sweep` — mesh-only, real mode, with the no-op control
> as the anchor (parameter absent ⇒ the 116 085-cell mesh reproduces at
> 0.000e+00). Step 3f then runs at `phantom_resolution=0.0075` (one halving,
> ≈ 8× ⇒ ≈ 4 300 phantom cells, +≈ 4 k cells overall, inside the weekly's
> 5–10 k budget) and is serial on 3f₀ **and** 3e′ (§9 item 7). The
> weekly's "0.01 → 0.005" is re-read as "0.015 → 0.0075"; the cost estimate
> and the pre-registered (a)/(b)/(c) verdict are unchanged.
>
> **Step 3f₀ ✅ 2026-09-02, 09:00 slot — the knob exists, its `None` path is a
> measured no-op, and step 3f's mesh is priced.** `phantom_resolution:
> Optional[float] = None` on `birdcage_port_domain` (`io/mesh.py`) and on
> `_build_birdcage_port_model`: a gmsh `Box` field over the phantom's own
> bounding box (`VIn = phantom_resolution`, `VOut = resolution`, margin
> 1e-3 of the extent, `Thickness = 0`) combined with the existing conductor
> `Distance→Threshold` through a new `Min` field. The conductor branch is
> otherwise untouched (the `GEO-21` 4.8 mm floor ruling), and with one field
> in the list the tail reduces to the single `setAsBackgroundMesh(threshold)`
> this code has always made, so `None` creates **no field at all**. Additive
> `phantom_resolution=` passthroughs on `tests/mesh/test_birdcage_port_sheets.
> _build` and `…test_port_birdcage_four_port.build_four_port_sweep`
> (`frequency_hz` / `reuse` precedent; ignored under `reuse`, which builds no
> mesh). New module `tests/mesh/test_birdcage_phantom_resolution.py`, `1
> passed in 83.94s`, `-n 2` real, standard tier, harness elapsed **86 s**,
> Status 0 (`20260902T140410Z_WF-6-step3f0.log`) — three builds, ≈ 24–25 s of
> gmsh each. **Every pre-registered anchor met.** *(i) The no-op control, the
> anchor:* parameter absent ⇒ **116 085** cells and **537** tag-3 cells, both
> at **0.000e+00** relative to the record, asserted at exact equality — no
> existing record, gate or example moved. *(i′) Negative control:*
> `phantom_resolution = 0.015`, equal to the global sizing, gives **116 085 /
> 537** as well, so gmsh is not honouring the field's mere presence. *(ii) The
> knob turned:* at `phantom_resolution = 0.0075` the tag-3 count goes **537 →
> 2 746 = 5.1136×** (band [5, 12] around the (h/hₚ)³ = 8× prediction — the
> shortfall is the Box's sharp transition and Netgen's optimise pass, not a
> mis-sized field) with the cells *outside* tag 3 moving **1.9083%** (ceiling
> 10%): total **116 085 → 120 499**, i.e. **+4 414 cells**, inside the
> weekly's 5–10 k budget and confirming step 3f stays standard tier. *(iii)
> Scale-free CAD identities on the refined mesh:* `GEO-18` sheet area
> **1.120000000e-04 m² on all four ports** (1e-9 band) and the `GEO-19`
> partition + air-box closure **1.000000000000**, on the negative control too;
> the cell-tag set is unchanged. Tag-3 counts are `size_local`-restricted and
> `MPI.SUM`-reduced (the reason for `-n 2`). No default moved, no band
> touched, nothing solved; `WF-6` stays 🟡. **Step 3f is unblocked on the mesh
> side** and remains serial on step 3e′.
>
> **Rulings of the 2026-09-02 10:30 review on steps 3e′ and 3f₀, and step 3g
> scoped.** *(1) Step 3e′'s clause (γ) is read as the run read it, not as it
> was written:* the CG2 restriction is not mis-assembled (every anchor green
> with orders of room), and what the rung measured is that a better L² fit
> of `E` over the phantom is *pointwise worse* at the 51 sample points.
> With the projector (3b/3c) and the degree (3e′) both excluded, the
> remaining candidates are mesh `h` and the construction itself — reading a
> quadratic-in-`E` identity from a fitted field at points inherits the fit's
> pointwise error, which no norm bound controls. **Ruling: run step 3f
> anyway (it is now unblocked on both halves and is queued first), and read
> its verdict knowing a better-resolved `E` can raise these numbers; and
> scope the integral-form construction as step 3g, independent of 3f and
> on the coarse mesh.** *(2) Step 3f₀'s 5.11× growth against the naive 8×*
> is accepted as measured: the band held, the CAD identities held, and the
> outside-tag-3 change was 1.9%; a thicker transition would buy cells, not
> information. Step 3f's expectation is re-recorded from 3f₀'s measurement
> — **2 746** phantom cells, 120 499 total — and no field parameter moves.
> *(3) Step 3f's anchor (ii) is sharpened, not loosened:* the weekly's
> "residual ≤ 18.7238%" compared two different meshes' primal fields and is
> not a theorem; the theorem is the same-mesh best-approximation inequality
> (restricted residual ≤ the global fit's residual on the *new* mesh), which
> is what is asserted, with the 18.7238% comparison printed.
>
> **Step 3g scoped 2026-09-02 10:30 review — the integral-form SAR
> identities, off the primal field, no estimator.** Let the coil axis be
> `z` and `θ_j = jπ/2`. Define the smooth azimuthal partition of unity
> `w_j(x) = ((c_j + √(c_j² + ε²))/2)²` with
> `c_j = (x cos θ_j + y sin θ_j)/√(x² + y² + ε²)`, `ε = 1e-9 m` — at each
> point only two adjacent `w_j` are non-zero and they sum to
> `cos² + sin² = 1`, so `Σ_j w_j = 1` identically and `w_{j+1}(x) =
> w_j(R⁻¹x)` exactly under the 90° rotation `R` (the regularised-`sqrt`
> form exists because `ufl.max_value` is the `OPS-22` complex-build trap).
> Read `P_j^{(k)} = ½ ∫_{dx(3)} σ w_j |E^{(k)}|² dx` for the four single
> drives `k` and the four quadrants `j` — sixteen cell integrals of the
> **primal** N1curl `E`, `assemble_scalar` reduced with `MPI.SUM`,
> `quadrature_degree` pinned — plus the same four integrals for the
> step-2 quadrature drive. **Anchors, asserted:** (i) the partition
> identity `Σ_j P_j^{(k)} = P_phantom^{(k)}` at rtol 1e-10 for every drive,
> with the gate-(i) drive's total reproducing the record **5.637745667e-08
> W** at `CG1_RECORD_RTOL` — an exact identity of the construction, so a
> miss is a defect in the integrals; (ii) the negative control — pairing
> quadrant `j` under drive `k` with quadrant `j+2` (180°) under drive `k+1`
> — reads *strictly larger* than the C4 pairing `j+1` for every `k`
> (an ordering, no factor: nobody has measured this ceiling), ratio
> printed. **Printed, not gated, verdict pre-registered:** the twelve C4
> pairs `|P_{j+1}^{(k+1)} − P_j^{(k)}| / P_j^{(k)}` (rotation sense taken
> from the pairing that made `test_birdcage_sar_map`'s `|B₁⁺|` gate green,
> never re-derived in-slot) and the quadrature drive's four-quadrant
> spread: **(a)** all ≤ 5% ⇒ the integral construction is the gateable one
> and a review registers the first coil-driven SAR gate on it; **(b)**
> between 5% and the pointwise primal 25–41% ⇒ report; **(c)** at or above
> the pointwise readings ⇒ the sample set was not the mechanism and the
> phantom's `h` is the last candidate standing (3f decides). Standard,
> `-n 2` complex, four solves and no mass solves ⇒ ≈ 100–125 s (3e′'s 125
> s carried six mass solves), `timeout -k 30 600`; new module
> `tests/validation/test_birdcage_sar_integral.py` importing the sweep
> builder, so its window can exit 0 beside the five primal reds. Scope:
> C4 only, no mirror identity, no band, no gate, no SAR claim, `WF-6`
> stays 🟡. Negative result: journal the verdict here and in the
> known-issues step-3d row, keep every assert, stop.
>
> **Rulings on the two rungs the 10:30 review carried to this weekly:** the
> *absolute-convergence rung* (an h-ladder for the `|B₁⁺|` map itself) is
> **deferred behind step 3f** — it turns the same knob, and 3f's anchor (i)
> is its first data point for free; scope it only if (i) moves. A `MAG-20`
> third rung is **killed** (epitaph in §10): Phase 1 is closed and a sharper
> magnetostatic rate is not on the mission's path this quarter.
>
> **Step 3f executed 2026-09-02 15:00 slot — the finer-phantom rung prints
> (a), and the coil-side anchor it was given goes red in the favourable
> direction.** New module `tests/validation/test_birdcage_sar_fine_phantom.py`
> runs the whole four-drive sweep through
> `build_four_port_sweep(phantom_resolution=0.0075)` — no `reuse=`, which
> hands back the coarse mesh — and re-reads every column of step 3e on it.
> `20260902T170559Z_WF-6-step3f.log`, **`3 failed, 27 passed` / Status 1 /
> 175 s** at `-n 2` complex with `tests/environment`, standard tier against
> the item's 150–200 s estimate; a collect-only smoke ran first
> (`20260902T170546Z_WF-6-step3f-collect.log`, 19 items, 5 s).
>
>   * **(iii) The knob reached the constructor**, asserted at exact equality:
>     **120 499** cells, **2 746** tag-3 cells, reproducing step 3f₀'s
>     measurement (coarse 116 085 / 537, **5.1136×** the phantom cells).
>   * **The deliverable — the five identities off
>     `post.project_to_cg1_restricted` (degree 1), printed not gated:
>     3.3600 / 3.4442 / 3.4525 / 3.0332 / 2.5465%** against the coarse mesh's
>     8.2868 / 9.4743 / 7.3477 / 6.8146 / 6.1185% — **−4.93 / −6.03 / −3.90 /
>     −3.78 / −3.57 pp, ratios 0.4055 / 0.3635 / 0.4699 / 0.4451 / 0.4162**
>     (mean **0.42** against the 0.25 a purely second-order residual would
>     give for one halving of `h`). All five are **inside** the imported,
>     unmoved 5% band, so the pre-registered clause evaluates to **(a)**:
>     **verdict (c)'s attribution to the phantom's ~1 cm cells is confirmed**,
>     the mechanism the projector (3c) and the estimator's degree (3e′) were
>     both excluded from. Both negative controls survive and are asserted —
>     mis-rotated **121.0800%**, quadrature-vs-single-drive **384.1297%**
>     (coarse 123.6255 / 333.0778%).
>   * **(ii) The estimator is still an estimator on the new mesh**, every
>     anchor green: the **same-mesh** best-approximation inequality
>     **12.5225% ≤ 1626.2098%** over the same phantom cells (129.86×, both
>     measured in this run — the 10:30 review's sharpening; the coarse
>     18.7238% is printed beside it, not asserted), `a + b × x`
>     **9.947634e-13** with `x² ê_x` at **2.142147e-01**, pinned max |value|
>     **0.000e+00** over owned *and* ghost blocks (**722** free of 22 147
>     owned CG1 blocks, **66 441** dofs, vs the coarse 170 / 21 397 / 64 191),
>     all six restricted solves reason **2** in 20–25 its. Restricted phantom
>     power **5.499426495e-08 W**, **−1.5681%** from this mesh's primal
>     5.587038273e-08 W (coarse: −3.5058%).
>   * **(i) Gate (i) is unmoved and gate (ii)'s anchor is not.** The power
>     accounting closes at **9.795780e-03** / **9.796465e-03** inside the
>     unmoved 1e-2 band (the P1 figure agreeing with the coarse record
>     9.795751e-03 to 3e-6 relative), conductor-drop control 7.52e-02. But the
>     three CG1 `|B₁⁺|` C4 identities read **0.6177 / 0.5966 / 0.5647%**
>     against their records 2.1870 / 2.1146 / 1.8911% — **−1.5693 / −1.5180 /
>     −1.3264 pp**, outside the pre-registered **0.5 pp** ceiling, so the three
>     parametrised asserts are **red on `main`** with a known-issues entry, per
>     the item's own "a larger move is a fixture finding" clause. The move is
>     an **improvement** (4× further inside the 5% band, control still at
>     25.4563%), so gate (ii) is not invalidated — what is invalidated is the
>     claim that 2.19% was a *converged* floor with 2.3× of headroom. **This is
>     the deferred absolute-convergence rung's first data point, arriving for
>     free exactly as the weekly said it would**, and its disposition (re-read
>     the anchor one-sided / run step 1c's ring-set control on this mesh /
>     a third rung at 0.00375) is a **review's**, not a slot's.
>   * **Caveat the module prints and no one should read past:** the sample set
>     is the mesh's own tag-3 centroids, so it grew **51 → 373** points with
>     the refinement; `h` and the sample set moved together. Step 1c
>     separated them for the coarse DG0 `|B₁⁺|` column (±2 pp, centroid vs
>     rotation-invariant ring set) and found the set was not the mechanism,
>     which is why this is read as an `h` rung — but a review minded to
>     register the SAR gate on clause (a) should want that control re-run on
>     this column first.
>   * **Scope, observed:** no band moved, no tolerance moved, **no SAR gate
>     registered**, no homogeneity / absolute / C95.3 claim, the five primal
>     asserts in `test_birdcage_sar_map.py` untouched and still red, nothing
>     under `src/`, and **`WF-6` stays 🟡**. Registering the first coil-driven
>     SAR gate in the repo — on the restricted estimator at this rung, with
>     this table as its provenance — is now a live and evidenced option for a
>     review, and it is the only thing clause (a) authorises anyone to
>     consider.
>
> **Step 3g executed 2026-09-02 16:30 slot — every anchor green on the first
> run, and the pre-registered clause that prints is (a): the *construction*
> was the mechanism.** New module `tests/validation/test_birdcage_sar_integral.py`,
> `build_four_port_sweep()` at the **default** resolution (116 085 cells —
> deliberately step 3's own mesh, so "integral vs pointwise" is the only thing
> that differs from step 3's window and the rung is independent of 3f), four
> curl-curl solves and **no** mass solves.
> `20260902T213441Z_WF-6-step3g.log`, **`20 passed` / Status 0 / 106 s** at
> `-n 2` complex with `tests/environment` first, standard tier against the
> item's 100–125 s estimate; a collect-only smoke ran first
> (`20260902T213431Z_WF-6-step3g-collect.log`, 9 items, 4 s).
>
>   * **The deliverable — the twelve C4 pairs `|P_{j+1}^{(k+1)} − P_j^{(k)}| /
>     P_j^{(k)}`, printed not gated: 0.7149 / 1.1908 / 1.4417 / 0.9703 |
>     1.5200 / 0.2132 / 0.3377 / 0.9086 | 1.0569 / 0.8355 / 0.2780 / 0.2302%**
>     (means 1.0794 / 0.7449 / 0.6002%, worst **1.5200%**) — **all twelve
>     inside the unmoved imported 5% band**, against the pointwise primal
>     column's 25.11–40.55% and the pointwise *restricted-estimator* column's
>     6.1–9.5% on this same coarse mesh. The pre-registered clause is
>     therefore **(a)**. The quadrature drive's four-quadrant spread is
>     **0.4641%**.
>   * **(i) The partition identity is exact.** `Σ_j P_j^{(k)}` reproduces
>     `P_phantom^{(k)}` to every printed digit for all five drives (asserted at
>     rtol 1e-10): 5.637745667e-08 / 5.630901879e-08 / 5.646798644e-08 /
>     5.621308271e-08 W for k = 0…3 and 3.796523707e-07 W for the quadrature
>     drive. The gate-(i) drive's total is **5.637745667e-08 W** — step 1's
>     record reproduced **digit-for-digit**, not merely inside
>     `CG1_RECORD_RTOL`, which ties these twenty integrals to step 1's gated
>     three-way power accounting on the same solve, measure and σ.
>   * **(ii) The mis-paired (180°) control is asserted and enormous**:
>     **96.1655 / 97.4944 / 95.5869%** against the C4 means, ratios
>     **89.09× / 130.89× / 159.27×**. The ordering the item asked for holds by
>     two orders of magnitude, so the twelve readings above are not passing on
>     an azimuthally structureless map.
>   * **What this measures, stated narrowly.** Steps 3c / 3e′ / 3f excluded the
>     projector, the estimator's degree and (3f) implicated `h`. This rung
>     shows the *fourth* candidate — reading a quadratic identity from a field
>     at sampled points, which inherits the pointwise error squared — is worth
>     4–6× on this fixture at **fixed** `h`: the same four solves that read
>     25–41% pointwise and 6.1–9.5% through the best available estimator read
>     **≤ 1.52%** as integrals, with no estimator in the path at all. 3f's `h`
>     finding is not contradicted (it is a different knob on a different mesh);
>     what is new is that the coarse mesh was never the binding constraint for
>     an *integral* statement.
>   * **Scope, observed:** C4 only — no mirror identity, no band moved, no
>     tolerance moved, **no gate registered**, no §2 claim, no homogeneity /
>     absolute / C95.3 claim, the five primal asserts in
>     `test_birdcage_sar_map.py` untouched and still red, nothing under `src/`,
>     and **`WF-6` stays 🟡**. Registering the first coil-driven SAR gate on
>     the *integral* construction is a **review's** ruling and clause (a) is
>     its evidence; it is the only thing this run authorises anyone to
>     consider.
>
> **Ruling, 2026-09-02 18:00 review — the integral construction is the one
> the repo gates; the pointwise five become records; the `|B₁⁺|` reds get
> their control.** Two constructions printed (a) today and the review had to
> pick one. **Step 3g's integral construction wins**, for three reasons that
> do not depend on its number being smaller: (1) it is a statement about the
> **primal** field — no estimator, no projector, no sample set in the path,
> so none of the three mechanisms steps 3b–3e′ spent five slots excluding can
> re-enter; (2) its partition identity is an **exact** anchor of the
> construction (`Σ_j P_j = P_phantom` to every digit), so a broken integral
> cannot hide behind a physics band; (3) it is cheaper by a whole mesh (106 s
> on the coarse fixture, four solves, no mass solves). Step 3f's
> pointwise-restricted 2.5–3.5% is **corroboration** — it says the same
> physics converges toward the same identity under `h` — but it carries the
> caveat its own module prints (51 → 373 centroids moved with `h`) and a
> 1.6× larger worst case on a mesh that costs 175 s. **What this ruling does
> to the five pointwise primal asserts** in `test_birdcage_sar_map.py`
> (`test_single_drive_sar_map_is_c4_covariant` ×3,
> `test_quadrature_sar_map_is_c4_invariant`,
> `test_reversing_the_rotation_sense_equals_reflecting_the_sar_map`): they
> assert a 5% band on a quantity the repo has now measured, through six rungs
> (3b/3c/3d/3e/3e′/3g), to be the *wrong statement* of the identity — a
> quadratic in `E` read at points inherits the pointwise error squared. They
> are **re-stated as record reproductions** of the `STEP3_PRIMAL_*` values
> (rtol 1e-3, the same licence step 3b used when it exported them), labelled
> in the docstring as the pointwise floor, with the 5% band **removed from
> those five and not moved anywhere**. This is not the loosening §7 forbids:
> the bound is not widened on the same quantity, the quantity is retired as a
> gate with its measurement kept, and the gate moves to the construction the
> identity is actually a theorem about. The two pointwise negative controls
> stay asserted `> band` exactly as they are (they still separate). **Step
> 3h** (§9 item 1) does exactly this and registers the twelve integral C4
> pairs at the unmoved imported 5% band, worst measured 1.5200% (3.3×
> headroom — *not* claimed converged: 3f just showed a "converged ~2% floor"
> claim on this fixture does not survive one `h` rung, so 3h states the
> headroom as measured-at-fixed-`h`, and step 3f′ prints the integral pairs
> on the 0.0075 rung beside it). **On the three `|B₁⁺|` reds** (3f's
> known-issues entry, options 1–3): option (2) is taken — the ring-set control
> is the one thing that answers both 3f caveats at once (does the sample set
> or `h` move the `|B₁⁺|` identities; does it move the SAR column) and it is
> a `_ring_points` call the repo already has. **Step 3f′** (§9 item 2) runs
> it on the 0.0075 mesh, re-reads anchor (i) **one-sided** (an identity may
> not get *worse* than its coarse record by more than 0.5 pp; getting better
> is the convergence measurement it is) and re-records the fine-rung `|B₁⁺|`
> figures as a second-rung record beside the coarse ones, never replacing
> them. Option (3), a 0.00375 rung, is **not** queued: 3f₀ priced one halving
> at +4 414 cells and 5.1× the phantom, so the next halving is ≈ 8× the tag-3
> cells again and needs a cost probe before anyone lists it — the weekly's
> call. Neither step moves a band. **Registering the gate is 3h's and only
> 3h's; if 3h's first window shows any integral pair above 5% on the same
> mesh that read 1.52% today, that is a stop, not a re-band.**

> **Ruling, 2026-09-03 03:00 review — one gate, a second identity on it,
> and the empty one named.** Both items landed green (3h `109 passed` /
> 194 s, 3f′ `54 passed` / 117 s) and 3f′'s slot asked whether the
> restricted-CG1 estimator's 3.36–2.55% at the 0.0075 rung, now with a
> ring-set control behind it, earns a *second* SAR gate. **No.** The gate
> is the statement the identity is a theorem about — quadrant powers of the
> primal field — and a second gate on an estimator-mediated pointwise
> quantity would re-admit exactly the three mechanisms (projector, degree,
> sample set) that six rungs spent excluding; the estimator figures stay
> asserted records in `test_birdcage_sar_fine_phantom.py`, which is where a
> future change to `project_to_cg1_restricted` will show. What the integral
> construction *can* still carry is the **mirror identity** step 3 retired
> from the pointwise map: on drive `k` the mirror through the coil axis and
> the port's azimuth fixes quadrants `k` and `k+2` and swaps the flanks, so
> `P_{k−1}^{(k)} = P_{k+1}^{(k)}` — and 3h's own table
> (`20260903T003309Z_WF-6-step3h.log:4682–4685`) already gives the four
> readings, **1.7527 / 1.5261 / 0.3438 / 0.9563%**, against a
> flank-vs-opposite control of **37.8–39.0%** (≥ 21× separation). **Step
> 3i** (§9 item 2) asserts those four at the unmoved 5% band on the same
> four solves. The ccw/cw quadrature mirror identity as quadrant integrals
> is **not** queued and should not be: on a C4-symmetric partition the
> quadrature quadrant powers agree to 0.4641% under *any* pairing, so the
> ceiling rubric says no control can separate a right pairing from a wrong
> one at a 5% band — an identity that cannot fail is not a gate. No
> convergence language enters §2 from 3f′; it is one `h` data point on a
> gate that is stated at fixed `h`.

> **Steps 4a / 4 — the B1+ closed-form gate (the weekly's 2026-09-06 §10
> target, split by the 18:00 daily review, ruling (4)).** The weekly
> wrote the target as *N infinitely long line currents*; on F-small
> (`coil_length` 0.14 m, `ring_radius` 0.07 m) the finite-length factor
> at the centre plane is `L/√(L² + 4R²)` = **0.7071**, so the 2D form
> misses the centre field by 29% and cannot anchor a ~2% band. The
> closed form is therefore the Biot–Savart superposition of **finite
> legs plus ring arcs**, still "evaluated numerically rather than
> transcribed". **Step 4a (§9 item 5, smoke, pure numpy, no FEM):**
> `utils.analytical.birdcage_filament_field(points, *, ring_radius,
> coil_length, leg_currents, ring_currents=None)` — finite segments in
> closed form, arcs by Gauss–Legendre, ring-arc currents from Kirchhoff
> with zero mean (raise unless `Σ I_n = 0`); gated on exact identities:
> the infinite-line limit against the imported
> `straight_wire_magnetic_field` (1e-5 at `L = 10³R`), the ring limit
> against the imported `circular_loop_magnetic_field_on_axis` (1e-10),
> `∇·B = 0` at 1e-8 for the closed mode-1 circuit with the ring-less
> pattern as the ≥ 100× control, C4 covariance at 1e-12, the 0.7071
> factor at 1e-6, and the mode-2 (`cos 2φ_n`) centre field exactly zero —
> step 4's negative control, closed-form side. **Step 4 (queued by the
> review after 4a lands):** one unloaded F-small sweep (phantom σ = 0,
> εᵣ = 1) on `birdcage_port_domain`, the quadrature `|B₁⁺|` radial
> profile at r ≤ 0.5 R against 4a's function with the leg current read
> from the FEM's driven-sheet current, asserted within the CG1 band `WF-6`
> measured (≈ 2%), the loaded map's profile printed beside it never
> asserted, the mode-2 drive as the ≥ 10× control (rule (e): asserted
> for its sign — the closed form is exactly zero — predicted for its
> size). Standard tier, `-n 2`, the 116 085-cell fixture. No homogeneity
> or literature claim enters §2 from either step.
>
> **Step 4 — scoped 2026-09-07 10:30 review (§9 item 3), with step 4a's
> correction (1) built in: on F-small the end rings contribute exactly
> `R²/ρ² = 0.5` of the legs' own centre field (`−μ₀IRh/(πρ³)`,
> `20260907T123926Z_WF-6.log:51`), so the anchor is the full
> `birdcage_filament_field` (legs + rings) and a legs-only comparison
> reads ~33% low by construction.** New module
> `tests/validation/test_birdcage_b1_plus_closed_form.py`. **Fixture:**
> `build_four_port_sweep` gains one additive keyword
> `phantom_material=None` (default: today's saline; rule (c), gate module
> re-run green in the same slot); the unloaded sweep passes
> `HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0)` on the same
> 116 085-cell mesh at 10 MHz. Four single-drive solves through the map
> module's `_solve_driven` (fields + `sheet_terminal_current` per sheet),
> the quadrature weights through `ports.superpose_drives` (`POST-6`), the
> superposed leg currents by the same linearity, `I_w,j = Σ_k w_k I_j^(k)`,
> projected onto zero mean before they enter the closed form
> (`|mean I| / max|I|` printed — predicted the C4-spread class ~1e-2,
> never asserted; 4a raises on a non-zero sum). **Anchor (asserted):** the
> CG1 `|B₁⁺|` of `WF-6` step 1b's estimator at eleven points in `z = 0` —
> `r = 0, 0.1R … 0.5R` along `x̂`, and `0.1R … 0.5R` along `ŷ` — against
> `|B₁⁺|` of `birdcage_filament_field(points, ring_radius=0.07,
> coil_length=0.14, leg_currents=I_w)` (both `(B_x + jB_y)/2`), every
> point inside a new pre-registered `CLOSED_FORM_BAND = 5.0e-2` —
> predicted 2–3% (the CG1 map's own C4 record 0.9818%, the filament vs
> the 2.5 mm wire ≈ (a/d)² ≲ 0.5% at `r ≤ 0.5R`, and the terminal-vs-
> volume current split the two-torus measured at 2.2%), the worst point
> printed. **Negative controls (rule (e) labels):** (α) the legs-only
> closed form (`ring_currents` forced to zero) misses the FEM centre
> field by more than `CLOSED_FORM_BAND` — **asserted** for its sign,
> backed by 4a's exact identity at `…123926Z:51`; size **predicted**
> ~33%, printed; (β) the mode-2 drive `w = (1, −1, 1, −1)` — the closed
> form's centre `B₁⁺` is exactly zero (4a's (vi)), so the FEM's mode-2
> centre `|B₁⁺|` is **asserted** ≤ `CLOSED_FORM_BAND` × the mode-1 centre
> value; size **predicted** ~1e-2, ratio printed. The loaded (saline)
> profile at the same points is printed beside the unloaded one, never
> asserted. **Tier / ranks / cost:** four unloaded + four loaded solves on
> 116 085 cells — `MAT-4` step 4 measured 132 s for four solves at `-n 4`
> on the 120 499-cell rung (`20260907T003548Z_MAT-4-step4.log:2260`) ⇒
> one window `-n 4`, `timeout -k 30 600`, heavy by ceiling, ≈ 270 s
> class; the gate re-run `test_port_birdcage_four_port.py` at `-n 4`,
> `timeout -k 30 400` (the same four solves, ≈ 115 s class per
> `20260907T140233Z_MAT-4-step4-rerun.log`). **Traps already paid for:**
> the leg azimuths and the leg-current sign are conventions — assert first
> that the generator's leg azimuths (`tests/mesh/test_birdcage_port_tags.py`,
> the constants 4a imported) equal 4a's `2πn/N` up to one common offset,
> and rotate the evaluation points, never the currents, if they differ;
> the sheet's terminal current is signed along the sheet's drive direction
> — map it to "+ẑ along the leg" explicitly; the port gap is bridged by
> the sheet's own surface current, so the closed form's leg is the full
> `coil_length`, not the leg minus the gap (an 8 mm gap at the centre
> plane is ~8% of the centre field — dropping it is the first wrong
> answer); `evaluate_vector_field_parallel` is a collective over an
> identical point list on every rank; `assemble_scalar` is rank-local;
> `-k a or b`; complex build + `FEM_EM_REQUIRE_COMPLEX=1`,
> `tests/environment` first; no `run_in_background`. **Scope:** the
> closed-form gate at the centre plane of the *unloaded* coil at 10 MHz,
> fixed `h`, CG1 — no homogeneity, CV, literature, absolute or Larmor
> claim; `WF-6` stays 🟡 (its homogeneity target is still open); §2's B₁⁺
> row gains one clause, "closed-form-gated at the centre plane of the
> unloaded coil", only when this lands. **Negative result:** the centre
> point missing by > 50% is a convention error — re-check azimuths and
> sign before anything is committed (4a's (v) clause); the centre inside
> the band with `r = 0.5R` outside is a statement about the CG1 map at
> the wire's near field — known-issues with the eleven-point table, park,
> stop; the centre missing with conventions verified is the finding that
> the FEM's leg current is not the filament's (non-uniform along the
> conductor) — known-issues, park, stop. `CLOSED_FORM_BAND` is never
> widened.
>
> **Step 4 executed 2026-09-07 15:00 slot — the third pre-registered exit
> fired, and the run's own control names the mechanism more precisely than
> the exit did.** `11 failed, 16 passed` / Status 1 / **93 s** at `-n 4`
> complex (`20260907T200630Z_WF-6.log`, wrapped `timeout -k 30 570`,
> collect-only smoke first at `…200619Z`, 16 items, 5 s). The eleven
> centre-plane points miss the unmoved `CLOSED_FORM_BAND = 5.0e-2` at
> **26.6201% (centre) / 26.2742 / 26.4648 / 24.5583 / 21.6815 / 19.4760
> (+x̂, r = 0.1R…0.5R) / 26.9033 / 27.3560 / 24.9922 / 21.2489 / 16.7641
> (+ŷ)** — FEM centre **8.097478100e-08 T** against the closed form's
> **1.103500413e-07 T** (`:1924–1934, :2499–2520`). **The band was not
> widened and nothing landed on `main`.** *Exit 1 (a convention error) is
> excluded by the run itself:* the fixture's leg azimuths are
> **360.0000 / 90.0000 / 180.0000 / 270.0000 deg**, the closed form's
> `2πn/N` lattice up to one common offset whose spread over the four legs
> is **0.000e+00 deg** (`:1919–1920`); every sheet's `drive_direction` is
> asserted `(0, 0, 1)`, the closed form's `+ẑ` leg convention; and control
> (β), the mode-2 drive, is **green** at **7.743627e-03** of the mode-1
> centre against 5.00e-02 (`:1938`) — the FEM reproduces step 4a's exact
> centre zero, so it is tracking the closed form's *structure*. *What the
> miss is:* control (α) reads the legs-only closed form at
> **7.356669419e-08 T**, so the filament's Kirchhoff rings add exactly
> **50%** at the centre (step 4a's `R²/ρ² = 0.5`) while the FEM's coil adds
> only **10.07%** — **FEM/legs-only 1.1007 against the filament's 1.500**,
> the FEM sitting far closer to an *open* coil than to a closed one. The
> four superposed leg currents are equal to four digits
> (1.820730e-02 / 1.820756e-02 / 1.820518e-02 / 1.820726e-02 A, `:1921`),
> so the terminal leg current is not the discrepancy; the **ring** current
> the FEM's coil carries is ~5× below `cumsum(I) − mean(cumsum(I))` on
> those same currents, and that is the next measurement. Rule (c) held: the
> additive `phantom_material` keyword is a no-op on the gate module,
> `5 passed / 44.01 s` at `-n 4`, Status 0, 46 s
> (`20260907T200858Z_WF-6.log:84, 96–97`). **No absolute `|B₁⁺|` claim
> exists, §2's B₁⁺ row does not gain the authorized clause, and `WF-6`
> stays 🟡** — the chunk's existing gates are symmetry identities, every
> one of them invariant to a uniform 27% scale, which is why this
> comparison was scoped in the first place. Parked on
> `attempt/WF-6-step4-20260907T205600Z` (`499c527`), known-issues entry
> filed, §9 item 3 marked 🚫 in the same commit (rule (d)). **Sizing
> correction:** the item's "four unloaded + four loaded solves" missed that
> `build_four_port_sweep` runs its own four-drive S-parameter sweep before
> the module's four field solves, so each rung costs **eight**; the loaded
> print sits behind `WF6_STEP4_LOADED` (default off) and was not solved.
>
> **Ruled 2026-09-07 18:00 review — the comparand was wrong twice, both
> errors the 10:30 review's, and together they account for the miss to
> first order; the ring current is not implicated by anything measured.**
> *(1) The rings are not where the closed form was told.* `birdcage_port_domain`
> places the end rings at `z = ±leg_spacing/2 = ±55 mm` (`io/mesh.py:3772,
> 3821`) and the legs run the full `coil_length`, `±70 mm`, with 15 mm
> dead-end stubs beyond each ring (`:3858`); the item passed
> `coil_length=0.14`, so the filament had its rings at ±70 mm and its
> current-carrying legs 27% longer than the fixture's. With the rings at
> ±55 mm the legs' centre field is 0.874 of 4a's value and the rings are
> `R²/ρ² = 0.618` of *that* (not 0.5): the free-space form's 1.50 L
> becomes **1.414 L**. *(2) The coil is not in free space.* The generator
> closes the air in a **PEC** box (`:4092–4101`) of half-extents
> `ring_radius + max(leg_radius_eff, ring_minor_radius) + port_dy +
> air_padding` radially and `max(coil_length/2, …) + air_padding`
> axially — with `AIR_PADDING = 0.03`, about ±0.11 m in x, y and
> ±0.10 m in z, so the rings sit **4.5 cm** from the end walls and the
> legs **4 cm** from the side walls. At 10 MHz the box is ≪ λ and a PEC
> wall imposes `B_n = 0`: every current has an image of equal magnitude
> with tangential components reversed and normal components kept. First-
> order images at the centre, from the same segment and arc formulas 4a
> asserted: each ring's near end-wall image cancels 0.45 of it
> (`h′ = 145 mm`, `ρ′³ = 4.2e-3` against `h = 55`, `ρ³ = 7.1e-4`), so the
> rings' 0.54 L become ≈ **0.30 L**; each leg loses 0.26 to its nearest
> side wall and 0.07 to the two perpendicular walls, gains 0.07 from the
> far wall and 0.10 from the end-wall leg images, so the legs' 0.874 L
> become ≈ **0.74 L**; total ≈ **1.04 L** against the measured
> **1.1007 L** (`…200630Z:1937`), the residual being the corner (second-
> order) images, which add. The free-space form at ±70 mm is ~27% above
> what a filament coil in *this* box at *these* ring planes produces, and
> the measured 26.62% deficit is the geometry and the box, not the coil.
> Control (α)'s reading "the FEM's rings add 10%" compared a boxed FEM
> with an unboxed, mis-positioned legs-only form and is not a statement
> about the ring current. **What this does not settle:** the displacement
> current a ~1 V coil pushes into a PEC wall 4 cm away (C ~ 20 pF,
> ωC ~ 1e-3 S, ≲ 6% of the 18 mA leg current) is inside the 5% band's
> margin and unmeasured, so the ring-current measurement the slot asked
> for stays worth one window — as a Kirchhoff check, not as the
> diagnosis. **Disposition (rule (f)):** the comparand is re-registered —
> the same filament form with `coil_length = LEG_SPACING` (the ring
> plane, which is also the current-carrying leg length) summed over the
> PEC box's image lattice, an exact construction for a rectangular box —
> and `CLOSED_FORM_BAND = 5.0e-2` is unmoved, asserted against the boxed
> form (step 4b, §9 item 1); the currents are measured directly (step 4c,
> §9 item 4). Nothing in the run's eleven readings, conventions or
> controls is disputed; 4a's identities stand as free-space identities at
> the `h = R` it was given.
>
> **Step 4b — the boxed closed form at the fixture's ring planes (scoped
> 2026-09-07 18:00 review, §9 item 1).** From
> `attempt/WF-6-step4-20260907T205600Z` (`499c527`) by path checkout onto
> `main` (the module, the four-port keyword, the three logs and their
> `test-results.md` rows). **Add** to `utils/analytical.py` one additive
> function `birdcage_filament_field_in_pec_box(points, *, ring_radius,
> coil_length, leg_currents, box_half_extents, image_order)` returning
> `Σ_{(i,j,k) ∈ [−N, N]³} birdcage_filament_field(points − c_ijk, …,
> leg_currents=P_ij I)` with `c_ijk = (2iX_b, 2jY_b, 2kZ_b)` and `P_ij` the
> leg-current map for the parity of `i` and `j`: an x-mirror sends leg `n`
> (azimuth `2πn/N`) to `N/2 − n mod N`, a y-mirror to `−n mod N`, and each
> mirror negates the currents (`(−1)^{i+j}` overall); a z-mirror changes
> no argument — the end-wall image is the translated coil with kept leg
> currents, and the function's own top/bottom ring convention supplies
> the reversed ring. `(0,0,0)` is the free-space term. **Read the box from
> the mesh, never assume it:** `allreduce` of min/max of `mesh.geometry.x`
> per axis (predicted ±0.11 / ±0.11 / ±0.10); read the ring plane as
> `LEG_SPACING / 2` from `tests/mesh/test_birdcage_port_tags.py` and pass
> `coil_length=LEG_SPACING`. **Anchors (asserted):** (i) the eleven
> centre-plane points against the boxed form at `N = 3`, every point
> inside the unmoved `CLOSED_FORM_BAND = 5.0e-2` — predicted ≲ 3%
> (first-order 1.04 L against 1.10 L measured, the corner images adding);
> worst point printed; (ii) pure-numpy identities on the new function,
> smoke tier `-n 1`: the `N = 0` term equals `birdcage_filament_field` bit
> for bit, and at each of the six wall-centre points the lattice sum's
> normal component satisfies `|B_n|/|B| ≤ 1e-2` at `N = 3` and decreases
> from `N = 2` — the check that the parity map is right (a wrong sign
> gives O(1); the truncation tail bounds it at ~(X_b/2NX_b)³); (iii) 4a's
> module re-run unchanged (4 s). **Controls (rule (e)):** (α′) the
> *original* free-space form at `coil_length = 0.14` misses the FEM centre
> by more than `CLOSED_FORM_BAND` — **asserted**, backed by this run's
> 26.62% (`…200630Z:1924`); the free-space form at `LEG_SPACING` and the
> boxed legs-only form printed beside (predicted 1.414 L and ≈ 0.74 L);
> (β) mode-2 as before, asserted; the lattice drift
> `|B(N) − B(N−1)|/|B(N)|` at `N = 1, 2, 3, 4` printed — the sum is
> conditionally convergent, so the drift is the honest error bar
> (predicted ≤ 1e-2 at `N = 3`; if it exceeds the band's margin at
> `N = 4`, report it as the finding). **Tier / ranks / cost:** the
> unloaded rung measured 93 s at `-n 4` (`…200630Z`, eight solves); the
> lattice sum is 343 filament evaluations at 11 points, seconds ⇒ one
> window `-n 4`, `timeout -k 30 400`; the numpy identities `-n 1` smoke;
> rule (c) for the additive `phantom_material` keyword —
> `test_port_birdcage_four_port.py` at `-n 4`, `timeout -k 30 400`,
> ≈ 46 s (`…200858Z:97`). **Traps:** those of step 4; the image map is a
> permutation *and* a sign — assert `sum(P_ij I) = 0` before each call
> (4a raises otherwise); an x-mirror composed with a y-mirror is the
> rotation by π, so `P_11 I` must equal the currents rotated two legs — a
> free check; the wall `B_n` identity is the one that catches a wrong
> parity; the stubs beyond the rings carry no current and are not in the
> form. **Scope:** closes step 4 with the clause "closed-form-gated at the
> centre plane of the unloaded coil *in its PEC box*" for §2's B₁⁺ row;
> `WF-6` stays 🟡; the landing keeps `attempt/WF-6-step4-…` until step 4c
> lands or parks (4c reads the same branch). **Negative result:** the
> centre inside the band and `r = 0.5R` outside is the CG1 near-field
> statement — known-issues with the table, park, stop; every point still
> ~20% low with the wall identity green is the finding that the box and
> ring planes are *not* the mechanism — known-issues, park, 4c becomes
> the diagnosis, stop. `CLOSED_FORM_BAND` never widens.
>
> **Step 4b executed 2026-09-07 19:30 slot — the 18:00 ruling is confirmed by
> measurement (26.62% → 2.33% at the centre, every predicted comparand landing
> on the nose), and the pre-registered `r = 0.5R` exit fires on one point of
> eleven; the binding uncertainty is now the comparand's own truncation.**
> `20260908T004020Z_WF-6.log`, **1 failed / 15 passed in 68.81 s** at `-n 4`
> complex, elapsed **71 s**, `Status: 1` (`:1881–1909` the table, `:1998` the
> footer); the same module with `tests/environment` at
> `20260908T003808Z_WF-6.log`, **1 failed / 26 passed in 100.06 s**, elapsed
> **102 s** (`:176–177`, `:473`). **Anchor (i):** centre **2.3345%**, `+x̂`
> 2.5175 / 1.3374 / 2.3495 / 3.8483 / 3.5983%, `+ŷ` 1.6429 / 0.1095 / 1.7611 /
> 4.4223 / **7.0875%**; median 2.3495%, worst point [10] = `r = 0.5R` along
> `+ŷ` (`:1889–1900`). Ten of eleven inside the unmoved 5%; **the band was not
> widened and nothing landed on `main`**. **The re-registration is vindicated
> quantitatively:** in units of `L` = the free-space legs-only centre field at
> `COIL_LENGTH` (7.356669419e-08 T), free space at `COIL_LENGTH` reads
> **1.5000 L** (review 1.500), free space at `LEG_SPACING` **1.4140 L** (review
> 1.414), boxed legs-only **0.7321 L** (review ≈ 0.74), boxed legs + rings
> **1.0756 L** against the FEM's **1.1007 L** (review ≈ 1.04 + corners) —
> `:1902–1907`. Control (α′) **asserted green**: the step-4 free-space comparand
> still misses by **26.6201%** (`:1901`), `…200630Z:1924` to the digit, so the
> gate discriminates between the two comparands. Control (β) green at
> **7.743627e-03** (`:1909`). **Three unpredicted readings.** (a) The PEC box
> measured off the mesh is **±0.120 / ±0.120 / ±0.100 m**, not the predicted
> ±0.11 / ±0.11 / ±0.10 (`:1882–1883`); the review's radial arithmetic was 1 cm
> short. (b) **The lattice truncation drift is 4.642e-02 at `N = 3` and
> 3.297e-02 at `N = 4`** against the predicted ≤ 1e-2 (`:1908`) — the
> comparand's own error bar is the size of the band, which the item's clause
> pre-registers as the finding, and a 7.09% point against a ±3–5% comparand is
> not evidence about the FEM. (c) The FEM's own `+x̂` / `+ŷ` pair at `r = 0.5R`
> differ by **3.4%**, a C4 asymmetry of the same order as the miss.
> **Anchor (ii)** (`20260908T003713Z_WF-6.log`, `-n 1`, 1 failed / 9 passed in
> 5.44 s, elapsed 7 s): (ii-a) `N = 0` equals `birdcage_filament_field` bit for
> bit (`np.array_equal`) — green; (ii-b) `P_11 I` = the currents rotated two
> legs, each mirror an involution with zero sum — green; (ii-c) the wall-normal
> identity converges by 9.3× (max **9.990e-02** at `N = 2` → **1.077e-02** at
> `N = 3`, `:60–61`) but lands **above** its pre-registered 1e-2 — the same
> truncation as (b). One disclosed definition correction: the item's literal
> `|B_n|/|B_total|` is degenerate (at the `+ŷ` wall of a mode-1 drive the field
> is purely normal by symmetry and the ratio reads 1.000e+00 at every `N`,
> `20260908T003604Z_WF-6.log:60–61`), so the denominator is the source coil's
> own `N = 0` field and the drive is `(1, 2, −3, 0)`. **Anchor (iii) and the
> rule-(c) window were not run** — the slot ended at the exit. Parked on
> `attempt/WF-6-step4b-20260908T004458Z`; §9 item 1 marked 🚫 in the same
> commit (rule (d)). §2's B₁⁺ row gains nothing; `WF-6` stays 🟡. **What a
> review must rule on next:** the comparand's truncation, not the coil — either
> accelerate the lattice (or raise `N`) until the drift is asserted below the
> band, or re-register the gate as "band + measured drift"; the FEM's own 3.4%
> C4 asymmetry at `r = 0.5R` is a second, independent candidate for the last
> point and `WF-6` step 2's C4 record (0.9818%) is the comparison to make.
>
> **Step 4c — the coil's conduction currents measured, a Kirchhoff check
> (scoped 2026-09-07 18:00 review, §9 item 4).** Independent of 4b (it
> does not consume the boxed form). On `main` if 4b landed, else on the
> branch — `git diff 499c527 main -- tests/validation/test_port_birdcage_four_port.py`
> empty means the keyword landed. New module
> `tests/validation/test_birdcage_conductor_currents.py`: the four
> unloaded single-drive solves as step 4, the mode-1 superposition; then,
> per leg, the volume-average axial current over three 10 mm slabs
> centred at `z = 11, 26, 41 mm` — `I(z) = (1/ℓ) ∫_{slab ∩ coil} J·ẑ dV`,
> `J = (σ + jωε)E` from the material map — clear of the port box (ends at
> ±5 mm) and of the ring junction (inner face at 51 mm); and per end
> ring, the volume-average azimuthal current `(1/(R Δφ)) ∫_{sector ∩ ring}
> J·φ̂ dV` over the middle half of each quarter arc (`φ ∈ [22.5°, 67.5°]
> + n·90°`, `Δφ = π/4`, `φ̂ = (−y, x)/r`), the ring's cells selected by
> `|z| > 51 mm` when the mesh has no separate ring tag. Indicators as
> `ufl.conditional` on products of the (real) `SpatialCoordinate` — the
> ordering-comparison trap's *allowed* form (**no `sqrt` inside the
> comparison** — UFL types `Sqrt` as complex whatever its operand,
> ruled 2026-09-08 03:00 from 4c's aborted first window); sector
> membership by `x cos φ_c + y sin φ_c > r cos(Δφ/2)`, no `atan2`;
> `quadrature_degree` pinned; `assemble_scalar` reduced with `MPI.SUM`.
> **Printed, all predicted — rule (e), none has a prior measurement on
> this fixture:** (1) `I_leg(11 mm)` against the sheet's
> `sheet_terminal_current` per leg — predicted the two-torus continuity
> class, 2% (`…093741Z:1013`); (2) `I_leg(z)` at the three stations per
> leg — predicted flat to a few % (the displacement bound ≲ 6%); (3) each
> ring's four arc currents against `cumsum(I) − mean(cumsum(I))` on the
> measured leg currents (top ring `+`, bottom `−`) — predicted within
> ~6%; (4) the Kirchhoff residual at each of the eight junctions,
> `|I_arc,n − I_arc,n−1 − I_leg,n(41 mm)| / max|I_leg|`. **Asserted:**
> nothing — a measurement step (🧪 by the §3 rule); the review reads the
> table and scopes any gate from it. **Tier / ranks / cost:** the same
> eight solves, 93 s at `-n 4`; twelve slabs + eight sectors = twenty
> scalar assembles, seconds ⇒ one window `-n 4`, `timeout -k 30 400`.
> **Traps:** `σ` on the coil tag is 800 S/m and `ε` there is ε₀ — form `J`
> from the material map, not a constant; the sheet current is signed
> along `drive_direction` (asserted `(0,0,1)` by step 4); a slab is
> `ufl.conditional(ufl.And(ufl.gt(z, z₀ − ℓ/2), ufl.lt(z, z₀ + ℓ/2)), 1, 0)`
> restricted to the coil `dx(tag)`; `-k a or b`; complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; no
> `run_in_background`. **Scope:** measurement only; no band, no §2 change;
> closes nothing; the record goes into this bullet with its log lines.
> **Negative result:** there is none — every reading is informative: ring
> currents ≈ `cumsum` to a few % retire hypothesis (b) of the 15:00 slot's
> entry; a leg current falling along `z` by more than the 6% bound is the
> finding that the PEC box takes displacement current at a level that
> matters for the 5% band — known-issues with the table.
>
> **Step 4c EXECUTED (2026-09-08 00:00 slot) — the coil's conduction
> currents are the sheet's to 3.1%, flat along `z` to 3.4%, and Kirchhoff
> closes at every junction to 2.2%.** One record window, `-n 4`, complex,
> **12 passed in 144.07 s**, footer `Status: 0` / `Elapsed (s): 146`
> (`20260908T051300Z_WF-6.log`, on the branch). Nothing asserted — 🧪 as
> pre-registered; no band, no `src/`, no §2 change. Fixture header
> (`:1918–1921`): the step-4 unloaded F-small birdcage, **116 085 cells**,
> ω = 6.283185e+07 rad/s, mode-1 (ccw) superposition, `J = (σ + jωε)E`
> off the DG0 material map on tag 1; legs at 360 / 90 / 180 / 270°, arc
> centres 405 / 135 / 225 / 315°, slabs at (0.011, 0.026, 0.041) m ×
> 10 mm, ring cells `|z| > 0.051 m`, arc span 45°, `quadrature_degree` 2.
> **(1) `I_leg(11 mm)` vs `sheet_terminal_current`** (predicted 2%;
> `:1922–1926`): **0.6053 / 2.5672 / 0.6384 / 3.0871 %** on legs 0–3,
> volume `|I|` 1.829947e-02 / 1.867466e-02 / 1.831125e-02 /
> 1.876886e-02 A against a terminal `|I|` flat at 1.8205–1.8208e-02 A,
> phases agreeing to ≤ 0.2°. **(2) `I_leg(z)`** (predicted flat to a few
> %, displacement bound ≲ 6%; `:1927–1931`): fall 11 → 41 mm
> **1.2217 / 2.7207 / −1.5808 / 3.3921 %**, every reading inside the
> bound — the PEC-box displacement finding did **not** fire and no
> known-issues entry opens. **(3) ring arcs vs `cumsum(I) − mean`**
> (predicted ~6%; `:1932–1940`): `|diff|/max|I_leg|` = top
> **1.1433 / 1.1477 / 1.0683 / 1.2382 %**, bottom
> **1.0288 / 1.0419 / 1.1235 / 1.2734 %** — measured arc `|I|`
> 1.2837–1.2885e-02 A against a comparand 1.2987–1.3014e-02 A. This
> **retires hypothesis (b) of the 15:00 slot's entry**: the rings carry
> the current the leg currents predict. **(4) Kirchhoff residual**
> (`max|I_leg|` = 1.876886e-02 A; `:1941–1949`): top junctions
> **0.6203 / 0.1032 / 2.1877 / 0.3636 %**; the bottom ring reads
> **193.24 / 193.67 / 196.05 / 193.43 %** under the item's *literal*
> sign and **0.6334 / 0.0900 / 2.1635 / 0.2467 %** with the leg sign
> flipped — both printed, neither chosen. **For the review, three
> readings to rule on:** (i) the bottom ring is the top's `z`-mirror, so
> its Kirchhoff statement is `I_arc,n − I_arc,n−1 + I_leg,n = 0`; the
> 193% is the item's recipe, not the fixture — adopt the flipped sign
> before any gate is scoped from this table. (ii) **A disclosed
> correction to the recipe:** the literal sector test
> `proj > sqrt(x²+y²)·cos(Δφ/2)` raises `ComplexComparisonError` even on
> purely real `SpatialCoordinate` operands, because UFL types `Sqrt` as
> complex unconditionally (`20260908T050511Z_WF-6.log:1983`, the aborted
> first window, Status 124); the executed module uses the equivalent
> squared form `proj > 0 ∧ proj² > r² cos²(Δφ/2)`, exact for `r ≥ 0` and
> `cos(Δφ/2) > 0`, smoked standalone at `20260908T051248Z_WF-6.log`
> (`Status: 0`, 6 s) before the second solve window was spent — the
> ordering-comparison trap note wants "no `sqrt` in the comparison", not
> "real operands". (iii) Index **2** is the worst on both rings
> (2.19% / 2.16%) and leg 2 is the only leg whose current *rises* with
> `z` (−1.58%); a leg-2-quadrant mesh asymmetry is a candidate shared
> with step 4b's `r = 0.5R` miss, checkable against `WF-6` step 2's C4
> record (0.9818%) before any comparand is blamed. Code + four logs on
> `attempt/WF-6-step4c-20260908T050135Z` (`0ac18d7`), based on
> `attempt/WF-6-step4-20260907T205600Z` (item 1 never landed the
> `phantom_material` keyword on `main`). `WF-6` stays 🟡.
>
> **Ruled 2026-09-08 03:00 review — step 4b's miss is the comparand's
> truncation, and the honest gate is the accelerated lattice, not a wider
> band; step 4c's table is adopted with the bottom ring's sign flipped.**
> (1) The cube-truncated image sum's drift falls as **1/N** (5.249e-02 /
> 4.642e-02 / 3.297e-02 at `N = 2, 3, 4`, ratios ≈ 0.88 / 0.71 against
> 2/3 and 3/4), which is the signature of shell sums of a dipole lattice
> whose faces alternate in sign with `N` — a Leibniz series, whose partial
> sums oscillate around the limit. For such a series the *mean of two
> consecutive partial sums* `S̄_N = (S_N + S_{N−1})/2` cancels the leading
> `1/N` term and converges as `1/N²`, so the drift of `S̄` at `N = 6` is
> predicted below **3e-3** (against 1.4e-2 for the plain sum at the same
> order) — a comparand whose own error bar is inside the band's margin.
> The wall identity (ii-c) measures the same truncation from the boundary
> side and is bounded by the same argument. The FEM's own **3.4%** `+x̂` /
> `+ŷ` asymmetry at `r = 0.5R` is a separate, mesh-side candidate for the
> 7.09% point: step 2's C4 record (0.9818%) is the *quadrature map's*
> invariance under a 90° rotation (`20260831T033704Z_WF-6-step2.log:
> 4698`, the loaded fixture), so 3.4% at one radius on the unloaded mesh
> is not already excluded by it and has to be measured on the four
> rotated copies of each point. (2) Step 4c: the bottom ring is the top's
> `z`-mirror, so its Kirchhoff statement is `I_arc,n − I_arc,n−1 + I_leg,n
> = 0`; the **0.6334 / 0.0900 / 2.1635 / 0.2467 %** column is the
> fixture's reading and the 193% column is the recipe's sign — adopted.
> The disclosed `sqrt`-in-comparison correction is ratified: the trap note
> at step 4c's "Indicators" sentence read "real operands only" and now
> reads "no `sqrt` inside the comparison" (UFL types `Sqrt` as complex
> unconditionally, `20260908T050511Z_WF-6.log:1983`); the rubric's trap
> list in `docs/automation/daily-review.md` carries it too. Junction 2's
> 2.19 / 2.16% and leg 2's rising current (−1.58%) name the same quadrant
> as the `r = 0.5R` `+ŷ` miss's neighbour; the mesh-side census is
> `GEO-28` (mesh-probe, §9 item 5), the field-side spread is step 4d's
> print. Nothing in (1) or (2) moves a band.
>
> **Step 4d — the accelerated image lattice, and step 4 lands (scoped
> 2026-09-08 03:00 review, §9 item 1).** From
> `attempt/WF-6-step4b-20260908T004458Z` by path checkout onto `main`: the
> two `analytical.py` functions, the module, the four-port keyword, the
> unit identities, the four `20260908T0036…–0040…Z_WF-6.log` files and
> their `test-results.md` rows (plus step 4's three, `499c527`). **The
> change:** (a) `birdcage_filament_field_in_pec_box` gains
> `return_partial_sums=False`; when true it returns the cube partial sums
> `S_0 … S_N` (shape `(N+1, n, 3)`) so one call at `N = 6` serves every
> order — 2 197 filament evaluations at 11 points, seconds; the default
> path is unchanged and (ii-a)'s bit-for-bit identity is re-asserted on it.
> (b) A pure-numpy helper `shell_averaged_lattice_sum(partial_sums)`
> returning `S̄_N = (S_N + S_{N−1})/2` for `N ≥ 1`. (c) The gate's comparand
> becomes `S̄_6`; `IMAGE_ORDER = 6`, `CLOSED_FORM_BAND = 5.0e-2` **unmoved**.
> **Anchors (asserted):** (i) the comparand's own convergence —
> `max_points |S̄_6 − S̄_5| / |S̄_6| ≤ 1e-2` (predicted ≤ 3e-3; the plain
> drift `|S_6 − S_5|/|S_6|` printed beside, predicted ≈ 1.4e-2) — *this
> assert runs first and the module stops at it if it fails*; (ii) the
> wall-normal identity on `S̄_6` at the six wall centres, drive
> `(1, 2, −3, 0)`, `|B_n|/|B_{N=0}| ≤ 1e-2` (predicted ≤ 3e-3; the (ii-c)
> value on the plain sum at `N = 3`, 1.077e-02, is the asserted negative
> control — backed by `20260908T003713Z_WF-6.log:60–61`); (iii) the eleven
> centre-plane points against `S̄_6` inside the unmoved 5% — predicted:
> centre ≈ 2.3%, the `+ŷ` `r = 0.5R` point moves by the comparand's
> correction only, so if it still misses it is the FEM side; (iv) (ii-a),
> (ii-b), 4a's module (4 s) and the four-port module under rule (c) for the
> keyword (`-n 4`, ≈ 46 s, `…200858Z:97`), all unchanged. **Controls (rule
> (e)):** (α′) and (β) exactly as 4b, both asserted (26.6201% at
> `…004020Z:1901`, 7.743627e-03 at `:1909`). **Printed (rule (e), no
> prior measurement):** the signed shell terms `(S_N − S_{N−1})·ŷ` at the
> centre in units of `L` for `N = 1 … 6` — the alternation is the ruling's
> premise and this is its check; the FEM `|B₁⁺|` at the four C4-rotated
> copies of each radial point (`±x̂`, `±ŷ` at the five radii — 20 points
> through one `evaluate_vector_field_parallel` call), the spread
> `(max − min)/mean` per radius (the 3.4% at `r = 0.5R` is the record,
> `…004020Z:1894, 1899`), and the C4-averaged FEM against `S̄_6` per radius.
> **Tier / ranks / cost:** the unloaded rung 93 s at `-n 4` (eight solves,
> `…200630Z`); 71 s for the whole 4b window; `N = 6` adds ≈ 6× the lattice
> work of `N = 3`, seconds ⇒ one window `-n 4`, `timeout -k 30 400`; the
> numpy identities `-n 1`, `timeout -k 30 60`; the two rule-(c) windows as
> 4b priced them. **Traps already paid for:** those of 4b; the partial-sum
> path must accumulate shells in the *same* order the default path sums
> (assert `S_N[-1] == default(N)` bit for bit, the (ii-a) pattern); a
> 1-based `S̄` index; `-k a or b`; complex build + `FEM_EM_REQUIRE_COMPLEX=1`,
> `tests/environment` first; no `run_in_background`. **Scope:** closes step
> 4 with §2's B₁⁺ clause "closed-form-gated at the centre plane of the
> unloaded coil in its PEC box, against the shell-averaged image lattice at
> `N = 6`" in the landing commit only; `WF-6` stays 🟡; retires the `WF-6`
> step-4 known-issues entry; deletes `attempt/WF-6-step4-…` and
> `…step4b-…` (both fully landed); keeps `…step4c-…` (its module lands in a
> later item). **Negative result:** (i) failing — the averaged sequence
> still drifts above 1e-2 — means the shell terms do not alternate and
> cube-shell averaging is not the acceleration: print the signed shell
> terms, known-issues with them, park, mark 🚫 (rule (d)), stop (the next
> route is a point-dipole tail for `N > 3`, a review's to scope); (iii)
> failing on the `r = 0.5R` `+ŷ` point alone with the C4 spread there ≥ the
> miss is the mesh finding — known-issues with the 20-point table, park,
> mark 🚫, stop, `GEO-28` becomes the diagnosis. `CLOSED_FORM_BAND` never
> widens.
>
> **Step 4d executed 2026-09-08, 04:30 implementer slot — 🚫 the premise is
> confirmed and anchor (i) would pass at 2.242e-03, but anchor (ii) is red at
> 3.292e-02: cube-shell averaging accelerates the *interior* field and
> *destroys* the PEC wall identity.** Two harness windows, no FEM window spent
> (the module stops at the red anchor and (iii)/(iv) were not measured).
> (1) The 03:00 ruling's premise is now measurement: the signed shell terms
> `(S_N − S_{N−1})·ŷ` at the box centre, in units of the free-space `S_0`
> centre field, are **+1.737937e-01, −2.954646e-02, +2.496714e-02,
> −1.833887e-02, +1.468487e-02, −1.222862e-02** for `N = 1 … 6` —
> strict alternation, magnitudes ≈ 1/N (`20260908T093332Z_WF-6.log:40–46`,
> measurement-only probe `scripts/probes/wf6_step4d_lattice_probe.py`,
> `Status: 0`, elapsed **24 s**, the `N = 6` ladder itself 13.46 s at 22
> points).  (2) At the interior points the acceleration is real: plain drift
> 3.259e-01 / 5.249e-02 / 4.642e-02 / 3.297e-02 / 2.712e-02 / **2.208e-02**
> at `N = 1 … 6` (4b's 4.642e-02 and 3.297e-02 reproduced to the digit),
> shell-averaged **2.242e-03** at `N = 6` — 9.8× better and inside both the
> ≤ 1e-2 anchor and the ≤ 3e-3 prediction (`:38–39`).  (3) **Anchor (ii)
> fails**: `|B_n|/|B_(N=0)|` on `S̄_6` at the six wall centres is
> **3.292e-02** against the unmoved 1e-02 (`20260908T093523Z_WF-6.log:78`,
> `1 failed / 10 passed in 10.08 s` at `-n 1` complex, elapsed **12 s**,
> `Status: 1`).  The plain sums show why: max **7.508e-02 / 9.990e-02 /
> 1.077e-02 / 7.082e-02 / 6.046e-03 / 5.980e-02** at `N = 1 … 6` (`:66–71`) —
> the wall residual has an **even/odd parity**, not an alternating tail, so
> averaging pairs a converging odd order with a stalled even one and `S̄_6`
> inherits half of `S_6` (`:72–77`).  The three supporting identities are green
> in the same run — (ii-a) bit for bit, (ii-a′) `ladder[m]` equals the default
> path at `image_order = m` bit for bit with `S̄` 1-based, (ii-b) the `P_11`
> rotation.  No band moved; `IMAGE_ORDER` stays 3 on `main`.  Code parked on
> `attempt/WF-6-step4d-20260908T094500Z` (the two `analytical.py` additions —
> `return_partial_sums` and `shell_averaged_lattice_sum` — the step-4b material
> path-checked out of `…step4b-…`, and the probe); `main` carries this record,
> the known-issues row and the two logs.  **The cheap next route the
> measurement names:** the odd-order cube sums alone — `S_5` reads 6.046e-03 on
> the wall, *inside* the band, and an odd-parity average `(S_N + S_{N−2})/2`
> keeps the interior cancellation while never mixing parities.  A review's to
> scope, and it must assert the interior drift **and** the wall identity
> together, because this slot's finding is that the two disagree about which
> truncation is good.
>
> **Ruled 2026-09-08 10:30 review — the sign of the truncation is now
> measured, and it goes the wrong way for step 4: the converged lattice
> sits *below* `S_3`, so no comparand fix lands the eleven points; the
> comparand is finished with the odd-order sum and the miss becomes the
> FEM's to explain.** From 4d's signed shell terms at the centre
> (`…093332Z:41–46`), `S_∞ − S_3 = Σ_{N≥4} t_N ≈ (S_5 + S_6)/2 − S_3 =
> t_4 + t_5 + t_6/2 = −0.00977` in units of the free-space `S_0` centre
> field, against `S_3 = 1 + t_1 + t_2 + t_3 = 1.16929` in the same units:
> the converged comparand is **0.84% lower** than the `N = 3` sum 4b gated
> against, so the centre miss under any converged comparand is ≈ **3.2%**,
> not 2.3%, and the two `+ŷ` points at `r = 0.4R` / `0.5R` (4.4223% /
> 7.0875% against `S_3`, `…004020Z:1898–1899`) move to ≈ **5.3% / 7.9%**
> (the 22-point plain drift at `N = 6` is 2.208e-02 against the centre's
> 1.05e-02, so off-centre shell terms are up to twice the centre's and the
> shift there may be nearer 1.6% — [10] ≈ 8.8%, [9] ≈ 6.1% on that
> reading; [4] at 3.8483% is marginal either way). The 03:00 ruling's
> "the `+ŷ` `r = 0.5R` point moves by the comparand's correction only, so
> if it still misses it is the FEM side" stands, and the correction is
> *away* from the band — the shell-averaged `S̄_6` 4d computed would have
> failed (iii) on [9] and [10] even had (ii) been green. **Step 4c's
> currents do not absorb it:** the legs' volume currents at 11 mm are
> +0.61 / +2.57 / +0.64 / +3.09% above the terminal currents but the
> 26 mm and 41 mm stations average +0.3% / +0.2%
> (`20260908T051300Z_WF-6.log:1923–1930`, on the branch), and the ring
> arcs read 1.0–1.3% *below* the Kirchhoff comparand (`:1932–1939`) — a
> comparand driven by measured currents would move the centre by well
> under 1% and in no consistent direction. **What is left is the FEM
> side:** a degree-1 N1curl solve on a 0.015 m air mesh (116 085 cells,
> never `h`-refined on this fixture — the same gap the `ANS-4`
> known-issues entry names) read through a CG1 projection of `curl E`,
> whose discretisation error at the centre nobody has bounded below 3%,
> and a 3.4% C4 spread at `r = 0.5R` on a C4-symmetric CAD (`GEO-28`, §9
> item 2). **Disposition.** (1) The comparand: **the odd-order cube sum
> `S_11`** — odd orders satisfy the wall identity by measurement
> (7.508e-02 / 1.077e-02 / **6.046e-03** at `N = 1 / 3 / 5`,
> `…093523Z:66–70`, falling monotonically) while the interior series is
> Leibniz-alternating with `|t_N| ∝ 1/N`, so `|S_∞ − S_11| ≤ |t_12| ≈
> 6.1e-03` at the centre (≈ 0.5% of `S_11`) and ≈ 1.1% at the worst
> interior point — a comparand bar a quarter of the band, which is not
> the "band + drift" the 03:00 review rejected (a 3–5% bar). Odd-parity
> averaging `(S_N + S_{N−2})/2` is **rejected**: both odd sums sit on
> the same side of the limit (`S_3 − S_∞ ≈ +0.0098`, `S_5 − S_∞ ≈
> +0.0061`), so their mean is *farther* from `S_∞` than `S_N` alone. Cost
> is the only price: `Σ_{m≤12}(2m+1)³ = 56 953` filament evaluations for
> the re-summed ladder to `N = 12` (≈ 230 s at 31 points from 4d's
> 13.46 s for 4 753 at 22), or 27 792 for the two direct sums `S_11`,
> `S_12` (≈ 110 s). (2) **Step 4e** (§9 item 1) lands the comparand and
> *measures* the eleven points against it with anchor (iii) **predicted
> red** at [9] and [10]; its landing rule is written for that outcome and
> for the other, and the `src/` half lands either way. (3) The `h`
> question is priced first (`GEO-29`, §9 item 5, mesh-probe: the
> global-`resolution` ladder's cells and mesh time on this fixture — the
> axis no ladder has touched) and solved second (**step 4f**, scoped by
> the 18:00 review from `GEO-29`'s table and 4e's table, serial on both,
> not queued). "Band + measured drift" stays rejected; `CLOSED_FORM_BAND`
> never widens; the eleven points are never pruned.
>
> **Step 4e — the odd-order comparand `S_11`, its two health anchors, and
> the eleven points measured against a converged lattice (scoped
> 2026-09-08 10:30 review, §9 item 1).** New branch by path checkout from
> `attempt/WF-6-step4d-20260908T094500Z` (`c7f6533`, which carries 4b's
> and 4's material): `analytical.py`'s `return_partial_sums` ladder and
> `shell_averaged_lattice_sum`, the unit module, the gate module, the
> four-port keyword, the probe, the nine `WF-6` logs of 2026-09-07/08 and
> their `test-results.md` rows. **The change:** `IMAGE_ORDER = 11`; the
> gate's comparand `S_11` by the default path (`image_order=11`); `S_12`
> computed once beside it for anchor (ii); `shell_averaged_lattice_sum`
> dropped from the gate (the helper and its (ii-a′)/1-based identity are
> kept — a measured negative worth keeping callable); `CLOSED_FORM_BAND =
> 5.0e-2` and `WALL_NORMAL_BAND = 1.0e-2` **unmoved**. **Anchors
> (asserted, in this order; the module stops at the first red):** (i) the
> wall-normal identity on `S_11` at the six wall centres, drive
> `(1, 2, −3, 0)`, `|B_n|/|B_{N=0}| ≤ 1e-2` — predicted ≤ 3e-3 (the odd
> sequence 7.508e-02 / 1.077e-02 / 6.046e-03 extrapolates below it),
> backed at `N = 5` by `…093523Z:70`; the full odd/even ladder to `N = 12`
> printed beside (six points, cheap) — the parity finding's check; (ii)
> the Leibniz bound at the eleven gate points: the shell terms `t_N = S_N
> − S_{N−1}` for `N = 2 … 12` alternate (`t_N · t_{N+1} < 0`) with `|t_N|`
> decreasing, asserted per point, and `max_points |S_12 − S_11| / |S_11|
> ≤ 1.5e-2` — predicted ≈ 1.1e-2 (2.208e-02 at `N = 6`, `…093332Z:38`,
> scaled by 6/12), the centre ≈ 5.2e-3; (iii) the eleven points against
> `S_11` inside the unmoved 5% — **predicted red at [10] (≈ 7.9–8.8%) and
> [9] (≈ 5.3–6.1%), [4] marginal (≈ 4.7–5.5%), the centre ≈ 3.2%, the
> other seven inside**; (iv) (ii-a), (ii-a′), (ii-b), 4a's module (4 s) —
> unchanged; the four-port keyword's rule-(c) re-run (`-n 4`, ≈ 46 s,
> `…200858Z:97`) only on the landing branch that lands the keyword.
> **Controls (rule (e)):** (α′) and (β) exactly as 4b, both asserted
> (26.6201% at `…004020Z:1901`, 7.743627e-03 at `:1909`). **Printed (rule
> (e)):** the eleven-point table with `S_3`, `S̄_6` and `S_11` side by
> side — the same FEM numbers, three comparands, so the ruling's
> arithmetic above is checked by one line; the C4 four-copy spread per
> radius (4d's print, never yet measured — 20 points, one collective
> call); the signed centre shell terms to `N = 12`; the lattice timing.
> **Tier / ranks / cost:** 4b's window 71 s at `-n 4` (eight solves + the
> `N = 3` lattice, `…004020Z:1998`); the lattice ≈ 110 s for the two
> direct sums or ≈ 230 s for the re-summed ladder (above) ⇒ one window
> `-n 4`, `timeout -k 30 560`; the unit module `-n 1`, `timeout -k 30
> 300` (the wall ladder to 12 at six points ≈ 45 s). **Traps already
> paid for:** 4d's — the ladder re-sums each order for bit-for-bit
> (FP addition is not associative), `S̄` 1-based; 4b's — the parity map
> is a permutation *and* a sign, `sum(P_ij I) = 0` per image, the box
> read off the mesh (±0.120 / ±0.120 / ±0.100 m); a 2–4 minute lattice
> inside a pytest fixture is silent — print the timing so a hung window is
> distinguishable from a slow one; `evaluate_vector_field_parallel` is a
> collective over an identical point list; `-k a or b`; complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first, `-s`; no
> `run_in_background`. **Landing rule (both branches pre-registered):**
> *if (iii) is green on all eleven* (the prediction is wrong — the
> overshoot was the comparand's after all): step 4 lands as 4d scoped it,
> §2's B₁⁺ clause "closed-form-gated at the centre plane of the unloaded
> coil in its PEC box against the odd-order image lattice at `N = 11`" in
> the landing commit only, the known-issues entry retired,
> `attempt/WF-6-step4-…`, `…step4b-…` and `…step4d-…` deleted,
> `…step4c-…` kept. *If (iii) is red as predicted:* land on `main`
> **only** `analytical.py`'s additive functions and
> `tests/unit/test_birdcage_filament_field.py` with (i), (ii-a), (ii-a′),
> (ii-b) green — the comparand is then finished and on `main` — and park
> the gate module, the four-port keyword and the eleven-point table on
> `attempt/WF-6-step4e-…`; the table into this entry and the known-issues
> row; delete `…step4-…`, `…step4b-…`, `…step4d-…` (their material is on
> 4e's branch, the `src/` half on `main`); mark the item per rule (d) with
> the unblock condition "step 4f"; `WF-6` stays 🟡. **Negative result:**
> (i) red on `S_11` means odd-order wall convergence stalls past `N = 5`
> — print the ladder, known-issues, park, stop (the point-dipole tail is
> then the only comparand route left, a review's to scope); (ii) red
> means the 1/N alternation breaks past `N = 6` — same disposition; (iii)
> red *beyond* the predicted points (the `+x̂` column too) is still the
> second landing branch, with the table. Nothing loosens; the eleven
> points are never pruned.
>
> **Step 4e executed 2026-09-08 12:00 slot — anchor (i) is RED at the
> pre-registered first stop, and the finding is larger than the anchor:
> the cube-truncated image lattice's wall-normal residual does not go to
> zero at all. The odd orders bottom at `N = 5` and turn around, the even
> orders fall, and the two parities converge on a common limit of
> ≈ 3.4e-02 — three times the unmoved 1e-02 band.** No FEM window was
> spent (the module stops at the first red, rule (e)); nothing landed on
> `main` beyond this record, the log and the known-issues row; the code
> is parked on `attempt/WF-6-step4e-20260908T170345Z`.
> `20260908T170345Z_WF-6.log`, **1 failed / 21 passed in 128.05 s** at
> `-n 1` complex with `tests/environment`, elapsed **130 s**, `Status: 1`.
> **The measurement** (`:86–99`) — max over the six wall centres of
> `|B_n|/|B_(N=0)|`, drive `(1, 2, −3, 0)`, box ±0.11 / ±0.11 / ±0.10, one
> `N = 12` ladder call (56 953 filament evaluations, **113.9 s**, `:85`):
>
> | `N` | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
> |---|---|---|---|---|---|---|---|---|---|---|---|---|
> | max `\|B_n\|/\|B_(N=0)\|` | 7.508e-02 | 9.990e-02 | 1.077e-02 | 7.082e-02 | **6.046e-03** | 5.980e-02 | 1.384e-02 | 5.399e-02 | 1.834e-02 | 5.040e-02 | **2.127e-02** | 4.796e-02 |
>
> `N = 1 … 6` reproduce 4d's `…093523Z:66–71` to the digit. **The odd
> sub-sequence is not monotone**: 7.508e-02 → 1.077e-02 → 6.046e-03 →
> 1.384e-02 → 1.834e-02 → **2.127e-02**, i.e. it has a *minimum at
> `N = 5`* and rises thereafter with increments +7.79e-03 / +4.50e-03 /
> +2.93e-03 that are themselves decaying like ≈ 1/N². The even
> sub-sequence falls monotonically with decrements −5.81e-03 / −3.59e-03 /
> −2.44e-03 of the same size and opposite sign. Both parities are
> therefore converging, from below and from above, on a **common non-zero
> limit ≈ 3.2–3.5e-02** — which is exactly where the shell averages sit
> and stay (`S̄_N` maxima 3.682e-02 / 3.392e-02 / 3.617e-02 / 3.437e-02 /
> 3.584e-02 / 3.462e-02 at `N = 7 … 12`, `:98`). **`S_5`'s 6.046e-03 was
> a crossing, not a convergence**, and the 10:30 review's extrapolation
> "the odd sequence extrapolates below 3e-3" is refuted by measurement.
> **Cause — measured, one mechanism named, not proved.** The lattice is
> only *conditionally* convergent (copies fall as `1/d³`, shells grow as
> `d²`), so its sum depends on the *summation order*, and a symmetric
> cube is a choice. The wall-normal functional is the one that sees that
> choice: `B·n̂ = 0` at `x = +X_b` comes from pairing image `i` with image
> `1 − i` about that wall, and a cube truncated at `|i| ≤ N` never pairs
> the ends — the unpaired outermost shell subtends a *fixed* solid angle
> at the wall no matter how large `N` is, so its contribution tends to a
> constant rather than to zero. That is consistent with every number
> above: a constant limit approached from both sides with `1/N²`
> oscillation. **Consequence.** The comparand question is **not** closed
> by a bigger `N` in any parity: there is no cube order at which the
> lattice satisfies the PEC identity to 1e-02 except the accidental
> crossing at `N = 5`, and gating on an accidental crossing is fitting.
> Step 4 does not land; §2's B₁⁺ row gains nothing; `WF-6` stays 🟡;
> `CLOSED_FORM_BAND` 5.0e-2, `WALL_NORMAL_BAND` 1.0e-2 and `IMAGE_ORDER`
> 3 are all unmoved on `main`. §9 item 1 marked 🚫 in this commit (rule
> (d)). **Resolves with** a review scoping a summation whose order is not
> a free choice — the two candidates the measurement leaves are (a) the
> **point-dipole tail** the 03:00 review already named (sum the near
> images exactly, replace the far lattice by its multipole limit, which is
> summed as an absolutely convergent integral), and (b) an **Ewald-style
> split** of the same lattice. Both are real work and neither is a
> one-slot fix; a third, cheaper option a review may prefer is to
> **abandon the closed-form comparand for this fixture** and gate `|B₁⁺|`
> by `h`-convergence instead (`GEO-29` prices the ladder). What is *not*
> available is widening a band or picking `N = 5`.

**Steps 4f and 4g — the `h`-convergence route was taken, and it landed.**
*(Folded into this entry by the 2026-09-09 18:00 daily review; until then
these two steps existed only in the §9 journal, which the weekly rotates
into `docs/planning/plan-archive.md`, so the §7 entry had gone stale
against its own chunk.)* The 03:00 review's third option above is what the
chunk actually did: the closed-form comparand stayed **set aside** and
`|B₁⁺|` was measured against a **C4 symmetry identity** across an `h`
ladder instead. **Step 4f (2026-09-09 07:30 slot,
`20260909T123716Z_WF-6.log`)** ran all three rungs to completion in 453 s
at `-n 4`: the field's four-copy worst-radius C4 spread falls **5.2506% →
2.0719% → 1.9514%** (ratios 1.0000 / 0.3946 / 0.3717) and then stalls, an
order above `GEO-28`'s ≈ 0.1% mesh floor. Three asserted anchors came back
red; the 10:30 review ruled two of them **pre-registration errors** (a
four-copy spread compared against a two-copy record; a 10× control bar
whose arithmetic ceiling on this fixture is 9.53×, i.e. unreachable rather
than unmet) and the third — the finest rung's power residual splitting
between the ports, P1 **1.853642e-02** / P2 **1.419812e-02** against
five-figure P1/P2 agreement on both coarser rungs — a **real, undiagnosed
finding**. Code parked, nothing widened. **Step 4g (2026-09-09 15:00 slot,
`20260909T200431Z_WF-6.log`, `49432f9`)** re-registered the two
mis-specified anchors off measured numbers, dropped the finest rung rather
than absorbing it, and **landed green on `main`**: `Status 0`, elapsed
**204 s**, `28 passed, 2 skipped`, `-n 4`, complex. Anchor (i) the ×1 rung
reproduces its own measured spread **5.2506%** inside 10% relative with
`size_global` **116 085 / 149 049** at ratio 1.000000 against the imported,
unmoved 1% `CELL_COUNT_BAND`; anchor (ii) both rungs pass the module's
existing gates at unmoved bands — power residual 9.795836e-03 /
9.796294e-03 then 8.113516e-03 / 8.111819e-03 (≤ 1e-2), C4 covariance
3.6159% / 1.6815% (≤ 5%); negative control **9.53× / 19.52×** against the
re-sized 5× bar. The eleven-point table reproduces step 4b
character-for-character (9.805561792e-08 T at `+x̂`, 1.013569652e-07 T at
`+ŷ`). **The measured statement, which is what §10's Phase-5 exit decision
was waiting for:** refinement owns ≈ 60% of the four-fold asymmetry and
then stops, so **the surviving ≈ 2% is not `h`'s** — it belongs to the
degree-1 N1curl solve, the CG1 `curl E` estimator, or the port-sheet
reconstruction (`GEO-31`). **Nothing else moved:** `CLOSED_FORM_BAND`
5.0e-2, `WALL_NORMAL_BAND` 1.0e-2, `POWER_BALANCE_BAND` 1e-2,
`C4_COVARIANCE_BAND` 5e-2, `CELL_COUNT_BAND` 1e-2 and `IMAGE_ORDER` 3 are
all unmoved on `main`, the eleven points are never pruned, the deleted
closed-form comparand stayed deleted, and the ×0.0095 rung stays **out**
(2026-09-09 18:00 ruling (2) — `GEO-30` reproduced that rung's symmetry
defect on a second, independent quantity rather than clearing it). **`WF-6`
stays 🟡**: this is a convergence *statement*, not a homogeneity,
absolute, closed-form or tuning claim, and §2's B₁⁺ clause does not move.
The 2026-09-13 weekly holds the dated Phase-5 exit decision against it.
