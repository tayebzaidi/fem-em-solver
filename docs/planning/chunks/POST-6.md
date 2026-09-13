# POST-6 — Arbitrary multi-port drive superposition

 **Arbitrary multi-port drive superposition** — HFSS *Edit Sources*: complex amplitude + phase per port over the stored single-drive solves, package-level and N-port (`WF-6` step 2's fixed 4-port quadrature is the special case) — **feature ladder A1** (operator directive 2026-09-04; first in the ladder; serial on nothing) | 🟡 *(**step 1 executed 2026-09-04, 19:30 implementer slot — the entry point exists and three of its four anchors are gated; the drive-level power identity is a documented red.** `ports.superpose_drives` + `run_n_port_sparameter_sweep(keep_fields=True)` + `run_lumped_sheet_port_case(return_fields=True)`, gated by `tests/validation/test_port_drive_superposition.py`, heavy tier, `-n 2`, complex, 146 s, `20260905T004202Z_POST-6.log`. **(i) green:** the ccw quadrature weights through the package reproduce `WF-6` step 2's identities — C4 **0.9818%**, mirror **0.8087%**, cw control **95.1975%** — at rel dev 9.619e-06 / 3.585e-05 / 5.248e-07 (`:1911–1913`), and the package path (superpose `E` on N1curl, then curl) agrees with step 2's fixture path (curl, then superpose DG0 `B`) on the *same four solves* to **1.2e-15 / 1.9e-15 / 1.2e-16**. That last number is the item's "rtol 1e-6" made executable: the records are stored to four significant digits, so no measurement — not even a bit-identical re-run — can meet 1e-6 against the literal (±5.1e-5 by rounding alone); the literals are asserted at the imported `CG1_RECORD_RTOL` (1e-3) and the path equality at 1e-12. **(ii) green:** `w = e_k` returns drive k's dof array bit for bit (`np.array_equal`), `S(w₁)+S(w₂) = S(w₁+w₂)` and the terminal weighted sums at 1e-12, mapping and sequence spellings identical. **(iv) green:** all four single-drive residuals reproduce step 1's 9.795751e-03 — 9.795751 / 9.796209 / 9.794985 / 9.795283 e-03 (`:1914`), P3 and P4 read for the first time. **(iii) RED, per the item's negative-result protocol:** `P_acc = ½aᴴ(I − SᴴS)a` = 3.014424803e-03 W against ½∫σ|E_w|² = 2.663302665e-03 W, residual **1.164806e-01** vs the imported 1e-2 band (`:1915–1917`); cross-term share 40.4652%, blind sum 1.794631250e-03 W. Nothing widened. The log's own arithmetic makes the denominator the leading hypothesis — the same fixture's *single*-drive form of this identity, `supplied − sheets` vs volume loss, is a **13.0%** miss, so the four-port drive reproduces the single-drive miss rather than adding to it — but that figure is computed by hand from a log, not asserted in-run. Known-issues entry carries both readings and the two candidate mechanisms. **Step 1b is the next move:** measure the single-drive `P_acc` in-run beside the superposed one and let a review re-point or keep the band on that evidence. **Scoping note kept from the queueing review:** identity (iii) was pre-stated at ≤ 1e-3, which is below this fixture's own 9.795751e-03 accounting floor (`20260831T033704Z_WF-6-step2.log:4684`), so 1e-3 is printed against and the imported 1e-2 is asserted — scoped before measurement.) **Step 1b executed 2026-09-05, 06:00 slot — the denominator question is answered.** `20260905T110305Z_POST-6.log`, `1 failed, 21 passed … 102.66s` (`:2034`), 104 s (`:2112`), heavy by ceiling, `-n 2`, complex, tests-only, no new solve. The power-wave identity `P_acc,k = ½|a_k|²(1 − Σ_i|S_ik|²) = supplied_k − Σ_i sheets_ik` holds to **1.7e-15 / 0 / 1.7e-15 / 0** against the pre-registered 1e-6 (`:1924–1939`), so the S-derived accepted power and the sheet accounting are the same number and the 11.6% is not a normalisation disagreement; the four single-drive volume residuals read **1.303004e-01 / 1.302723e-01 / 1.300031e-01 / 1.302052e-01** (mean 1.301952e-01) and the superposed 1.164806e-01 is **0.8947×** their mean (`:1940`). Negative control (S diagonal zeroed) misses by 7.66e-01, equal to its pre-computed ceiling `|S_kk|²/(1 − Σ|S_ik|²)`, against a 1e-3 floor. `POWER_BALANCE_BAND` untouched, the (iii) test still red by design, and the ~6.7e-05 W absolute gap common to every drive is still undiagnosed — the next review owns the re-pointing.)* **Ruled 2026-09-06 (weekly review): identity (iii)'s drive-level use of `POWER_BALANCE_BAND` is retired, not widened — the band was pre-registered against supplied power and the fixture's own single drives carry a ~0.98 %-of-supplied accounting gap (the four agree to 0.23 %), so an identity that re-reads that gap against a 13× smaller denominator measures the denominator. Step 2 (tests only, standard): re-register (iii) as the common-mode form `g_w = (P_acc,w − P_vol,w)/P_supplied,w` against `mean_k g_k` from the four single drives in the same run, asserted `|g_w − mean g_k| ≤ 0.1 · mean g_k` (the single drives' own scatter is 0.23 % of g, 40× inside; a superposition defect would be O(cross-term) ≈ 40 %, 400× outside), with the cw/mis-paired weights as the negative control and `POWER_BALANCE_BAND` kept imported and unmoved for the single-drive form; the deliberate red retires in the same commit. The ~6.7e-05 W gap itself is a finding, not a band problem, and gets its own chunk — `PORT-16`.**

**Step 3 EXECUTED 2026-09-13, 13:30 implementer slot (§9 item 4, the re-scoped closing step) — the 32-port ccw quadrature drive through `superpose_drives` is C16-invariant; (i)–(iii) green ⇒ `POST-6` ✅.** Tests only, `src/` untouched: a step-3 block at the end of `tests/validation/test_port_drive_superposition.py`. The 16-leg / 32-ring-port high-pass fixture is `PORT-13` step 3's `_build_ring_context` (`test_port_birdcage_ring_matrix.py`, imported, never copied); 32 drives solve once via `run_n_port_sparameter_sweep(keep_fields=True)` under `PORT-19`'s reuse default, then `superpose_drives` with ccw weights from `quadrature_phase_weights` at fractional index (slot × 22.5/90 ⇒ `e^{∓jφ}`); slots from measured azimuths, ring from measured sign of z, bottom ring ×(−1) (m = 1 odd under z → −z; does not enter (i)–(iii), stated in a comment, not gated). Import cycle (`b1_plus_closed_form` → `power_identity` → half-loaded superposition module) resolved by a lazy `_step3_imports()` on the existing `_step1()` pattern; the collection-error window `20260913T184909Z_POST-6-step3.log` (Status 4, 4 s, no solve) is kept as the record. The 32-port tests run only under `FEM_EM_POST6_STEP3=1`. Bands imported: `C4_COVARIANCE_BAND` 5 % (`test_birdcage_b1_plus_map.py:120`, `WF-6`'s, already imported by this module), `DISCRETE_IDENTITY_RTOL` 1e-6, `MIN_SAMPLE_POINTS` 50. **Gate window** `20260913T185043Z_POST-6-step3.log` — `-n 8`, complex, env on, `tests/environment` first, `-v -s`, `timeout -k 30 590`, durable capture: **15 passed (11 + 4), Status 0, 191 s**, `[capture] rc=0` `:12347`. **(i)** worst C16 spread of the CG1 `|B₁⁺|_ccw` over 15 rotations **0.8102 %** at R₆ (range 0.4906–0.8102 %, `:11783–11798`) ≤ 5 %; **(ii)** mirror `|B₁⁻|_cw(Mx)` vs `|B₁⁺|_ccw(x)` **0.6769 %** ≤ 5 % (`:11799`); **(iii)** exact identity rel dev **3.961e-15** ≤ 1e-6 — `P_src,exact` 7.226844584e-03 W = `P_vol` 3.854418256e-03 W + `P_sheet,exact` 3.372426328e-03 W; package `P_acc` 6.871501158e-03 W printed only (`:11800`). **Negative control:** on the 32-port fixture *predicted*, printed, never asserted — cw mis-paired 98.9915 % measured vs 99.0609 % predicted, 122.17× vs 122.26× the worst C16 spread (`:11801`); *asserted by record* on the 4-leg fixture — **regression window** `20260913T185405Z_POST-6-step3.log` (`-n 2`, whole module, env off: **24 passed / 4 skipped, Status 0, 76 s**, `:2118`) reproduces `RECORDED_CW_SPREAD` 95.1975 % at rel 5.248e-07 against ccw C4 0.9818 % (≈ 97×, bar 5×; `:1911–1913`, test `:1988`), every pre-existing step-1 anchor green. **Price:** ring build 81.8 s, 32-drive sweep 30.3 s, two CG1 projections 0.7 s, 17 point evaluations 1.0 s, identity 44.0 s; summed `ru_maxrss` 9.32 GiB (`:11802`) — the item's ≈ 14 min estimate was ~4× high. **Caveats for the review:** the r ≤ 0.02 m, |z| ≤ 0.02 m sample cylinder holds exactly **50** points = `MIN_SAMPLE_POINTS` (`:11780`), valid on all rotated and mirrored images (`:11782`) — a zero-margin `≥`; the gate window's 191 s is heavy-tier by 11 s. **Scope:** 10 MHz, one fixture; no homogeneity, absolute or Larmor claim. 

## Narrative — moved verbatim from PROJECT_PLAN.md §7 (OPS-47)

**`POST-6` — arbitrary multi-port drive superposition (HFSS *Edit
Sources*)** ⬜ *(**feature ladder A1** — the first item of the ladder,
operator directive 2026-09-04, §9 item 5; serial on nothing.)* **Why.**
Quadrature drive is the MRI excitation and every B₁⁺/SAR quantity in §1 step
3 is defined under it. `WF-6` step 2 built it once, for four ports at fixed
`e^{∓jkπ/2}`, inside a test module; `EX-39` shows it. Nothing package-level
takes *N* stored single-drive solves and a complex weight vector, which is
what a tuned 32-port drive (`PORT-15`) and any asymmetric drive need.
> * **Step 1.** `ports.superpose_drives(sweep_result, weights)` → the
>   combined `E` (and `B` via `post.magnetic_flux_density_from_e`), the
>   combined port voltages/currents, and the combined accepted power. Gates,
>   all identities: (i) the four-port quadrature weights reproduce `WF-6`
>   step 2's C4-invariance and mirror digits **verbatim** (imported, never
>   restated); (ii) linearity — the superposed port voltages equal the
>   weighted sums of the single-drive ones to 1e-12; (iii) power —
>   `P_acc = wᴴ(I − SᴴS)w` from the S-matrix equals the volume loss integral
>   of the superposed field to ≤ 1e-3 (the first drive-level power identity).
>   Standard tier on the 116 085-cell 4-leg mesh.
>   **Review 2026-09-05 (03:00), two rulings on the slot's disclosures.**
>   (a) **Ratified:** anchor (i)'s pre-registered rtol 1e-6 against
>   `STEP2_IDENTITY_RECORDS` was arithmetically unreachable — the records
>   are four-significant-digit literals (`0.9818e-2`), so even a
>   bit-identical re-run agrees with them only to ±5.1e-5 — and the
>   substituted pair (literals at the imported `CG1_RECORD_RTOL` = 1e-3,
>   package-vs-fixture path equality at 1e-12, measured 1.2e-15) is
>   strictly tighter on the quantity that carries the information. Not a
>   loosening; the 1e-6 was the queueing review's error. (b) **The
>   denominator hypothesis is arithmetic on the log, adopted as the
>   working diagnosis, not as a finding:** `WF-6` step 1's single-drive
>   accounting misses by 9.795751e-03 × 6.856240413e-03 W =
>   **6.716e-05 W absolute** (`20260831T033704Z_WF-6-step2.log:4684–4688`);
>   `supplied − sheets` is 5.154401e-04 W, so that same absolute gap is
>   **13.0%** of the single-drive accepted power, and the superposed drive
>   reads 3.511e-04 W absolute on 3.014e-03 W = 11.6% — the same fraction
>   within the cross-term share. Whether the S-derived `P_acc` *equals*
>   `supplied − sheets` per drive is the one thing not measured; that is
>   an identity of the power-wave definition at `z0 = Re Z_p` and is
>   step 1b's assertion.
> * **Step 1b (the denominator, measured in-run; queued 2026-09-05 03:00
>   review as §9 item 2).** In the existing module, for each single drive
>   k: `P_acc,k = ½|a_k|² (1 − Σ_i |S_ik|²)` from the assembled 4×4 beside
>   the fixture's `supplied − sheets` accounting, asserted equal at rtol
>   **1e-6** (the power-wave identity; both are already computed in the
>   module, `test_port_drive_superposition.py:248` and the `_power_waves`
>   route); then the single-drive form of identity (iii) `P_acc,k` vs
>   `½∫σ|E_k|²`, **printed** with its residual, and the ratio
>   (superposed residual) / (mean single-drive residual) printed. Gate:
>   the rtol 1e-6 identity only. **Disposition rule, pre-stated:** if it
>   holds and the four single-drive residuals read ≈ 13%, the drive-level
>   red is the fixture's ~1% accounting offset against a 13× smaller
>   denominator — the *next* review re-points `POWER_BALANCE_BAND`'s
>   drive-level use to `supplied` (or opens a chunk for the 1% offset
>   itself), and the test stays red until it does; if the identity fails,
>   the S-matrix's power-wave normalisation disagrees with the sheet
>   accounting — known-issues entry with both numbers, stop.
>   **Executed 2026-09-05, 06:00 implementer slot — the identity holds at
>   machine precision.** `tests/validation/test_port_drive_superposition.py`
>   only, three new tests on the existing `superposition_case` fixture, no
>   new solve; `20260905T110305Z_POST-6.log`, `1 failed, 21 passed … 102.66s`
>   (`:2034`), Elapsed **104 s** (`:2112`), heavy by ceiling
>   (`timeout -k 30 600`), `-n 2`, complex. The one failure is the
>   *deliberate* step-1 red `test_the_drive_level_power_identity_closes`,
>   untouched. **(1b-i) green:** `P_acc,k = ½|a_k|²(1 − Σ_i|S_ik|²)` equals
>   `supplied_k − Σ_i sheets_ik` to **1.683e-15 / 0.000e+00 / 1.679e-15 /
>   0.000e+00** for P1–P4 against the pre-registered 1e-6 (`:1924–1939`) —
>   the power-wave normalisation and the sheet accounting are one number, so
>   "the two accountings disagree" is excluded and the 11.6% is **not** a
>   normalisation story. **(1b-ii) green:** the superposed ccw `P_acc`
>   reproduces 3.014424803e-03 W at rtol 1e-9 — same solves, same path.
>   **Printed, not asserted:** the four `|P_acc,k − P_vol,k|/P_acc,k` read
>   **1.303004e-01 / 1.302723e-01 / 1.300031e-01 / 1.302052e-01**, mean
>   **1.301952e-01**, and the superposed 1.164806e-01 is **0.8947×** that
>   mean (`:1940`) — the four-port drive misses *slightly less* than its own
>   single drives, so the superposition adds nothing. **Negative control,
>   ceiling first:** deleting `S_kk` from drive k's column misses by
>   7.659732e-01 / 7.656687e-01 / 7.634896e-01 / 7.652279e-01, each equal to
>   the closed form `|S_kk|²/(1 − Σ_i|S_ik|²)` computed from the assembled
>   4×4 *before* the assertion, against a claimed floor of 1e-3 (1000× the
>   band); nothing above the computed value claimed. **The disposition rule
>   fires as written:** the identity held and the four residuals read ≈ 13%,
>   so the drive-level red is the fixture's ~1%-of-`supplied` accounting
>   offset read against a 13× smaller denominator. `POWER_BALANCE_BAND` was
>   **not** touched in-slot and the test stays red; the next review is the
>   actor. **What step 1b does not settle:** the ~6.7e-05 W absolute gap
>   common to every drive is still unexplained — it is 0.98% of supplied and
>   13.0% of accepted, and candidate (b) "a real un-accounted loss channel"
>   survives at that same absolute size. Known-issues entry carries both.
>   **Review 2026-09-05 10:30 — the disposition is held for the 2026-09-06
>   weekly, with a recommendation.** The 03:00 review listed this decision
>   for the weekly explicitly ("a decision the dailies cannot make") before
>   step 1b ran, and step 1b's result sharpens rather than removes the
>   reason: re-pointing the drive-level band at `supplied` makes the test a
>   restatement of `WF-6` step 1's single-drive gate (0.98% of supplied,
>   already green) and gates nothing about the *superposition*, whose own
>   contribution step 1b measured at 0.8947× the single-drive mean. The
>   recommendation this review records: **(a)** re-scope the drive-level
>   test to the relative identity the data actually supports — the
>   superposed residual against the mean single-drive residual, both
>   computed in-run, ratio asserted ≤ 1 + `CG1_RECORD_RTOL`-class slack
>   (measured 0.8947; a superposition that *adds* power error is what it
>   would catch); **(b)** the 6.7e-05 W absolute gap becomes its own chunk
>   with a mechanism list (sheet-loss vs volume-integral double count in
>   the gap cells; Poynting flux through the outer wall under the natural
>   BC; the `_loss_power_w` quadrature on DG0 σ) — `POST-5`'s
>   three-term identity is the instrument, and a fixed-`h` gap that is
>   0.98% of supplied on every drive is a systematic, not noise. The test
>   stays red and `POWER_BALANCE_BAND` stays 1e-2 until the weekly rules;
>   the known-issues entry leaves with that commit.
> * **Step 2.** The same on `PORT-13`'s 32-ring-port fixture with the
>   16-fold quadrature weights; the C16 invariance of `|B₁⁺|` is the gate.
> * **Done-when (§4).** Both steps asserted; `WF-6` step 3 and `WF-7` are
>   re-pointed to consume this entry point rather than their own sums.
