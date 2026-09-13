# PORT-14

## Narrative — moved verbatim from PROJECT_PLAN.md §7 (OPS-47)

**`PORT-14` — lumped RLC sheets (HFSS *Lumped RLC*)** 🟡 *(step 1 executed
2026-09-05, 21:00 implementer slot — **the code lands, the gate does not
close.** `series_rlc_impedance` and a complex `Z_p` on the sheet, plus
`src/fem_em_solver/ports/circuit.py::reduce_terminated_ports`, are in and
solve; the 50 Ω baseline reproduces `PORT-9` on the run's own mesh
(`‖S−Sᵀ‖/‖S‖ = 1.464324816e-14`, `σ_max = 0.999992805`); the reduction
identity reads **1.595580e-03 (C = 100 pF), 3.370512e-03 (L = 1 µH),
7.249519e-04 (R = 200 Ω)** against the pre-stated **1e-3**, i.e. the lumped
sheet is single-mode to 3.4e-03, not 1e-3. Band **not** widened, per §9
item 2's negative-result protocol; known-issues 🟡, test deliberately red on
`main`. The ceiling-first Γ = 0 control passes with room (Δ = 0.322 / 0.325 /
0.211, misses 0.322 / 0.327 / 0.212 = 200–330× the band), so the gate is
resolving the termination. The residual **tracks |Γ|**, not the element type —
the hypothesis a step 1b would test is sheet/interior-width resolution, not
the complex arithmetic. `20260905T020428Z_PORT-14.log`, heavy tier by ceiling,
`-n 2`, 105 s, 13 solves on one 116 085-cell mesh.)* *(**feature ladder
A2**, operator directive 2026-09-04; serial on nothing; `TH-17` is serial on
it.)* The `PORT-9` sheet term carries `Z_p = 50 Ω`; let it carry
`Z_p(ω) = R + jωL + 1/(jωC)` per sheet, so a capacitor in a ring gap is a
boundary condition rather than a circuit afterthought. Gate (an algebraic
identity, no closed form needed): **the field-solved S-matrix with port *k*
terminated in `Z_p` equals the circuit reduction of the 50 Ω S-matrix by
that termination** (`S' = S_aa + S_ab Γ (I − S_bb Γ)⁻¹ S_ba`, Γ the
termination's reflection coefficient) to ≤ 1e-3 on the 4-leg fixture at 10
and 64 MHz, for a capacitor, an inductor and a resistor each. That is also
`PORT-15`'s gate seen from the field side, which is why the two are one
lineage. Standard tier.
> * **Step 1b (the |Γ| ordering, measured on resolution; scoped
>   2026-09-05 03:00 review, §9 item 4).** The slot's hypothesis — the
>   residual tracks |Γ| (1.6e-3 and 3.4e-3 at |Γ| = 1, 7.2e-4 at
>   |Γ| = 0.6), i.e. total reflection re-excites the sheet's non-single-mode
>   content — predicts that the residual falls with sheet resolution and
>   is indifferent to the element type. Measure it on the **L = 1 µH**
>   case (the worst) and the **C = 100 pF** case, on two refined rungs of
>   the same fixture: `conductor_resolution` × 0.75 and × 0.5 through an
>   additive `conductor_resolution=None` keyword on
>   `tests/mesh/test_birdcage_port_sheets.py::_build` (the `WF-6` step 3f₀
>   `phantom_resolution` precedent — `None` leaves every gate's mesh
>   bit-identical, and `test_port_birdcage_four_port.py` is re-run green
>   in the same slot as its gate). Per rung: the 50 Ω 4×4 (4 solves) with
>   the imported reciprocity / passivity asserts, then the two terminated
>   3×3s (6 solves), residuals **printed** beside the 116 085-cell record
>   with the cell count. **Pre-registered readings:** monotone decrease on
>   both cases is the hypothesis confirmed and step 2 (64 MHz) is queued
>   on the finer rung; flat or rising residuals refute it and the next
>   suspect is the sheet law's `sheet_width_m` (the area-based effective
>   width, `lumped.py:353`) — a `PORT-14` step 1c, not a band change.
>   `REDUCTION_BAND` stays 1e-3 either way; the row stays 🟡; nothing is
>   asserted on the residuals in this step. Heavy by ceiling.
> * **Step 1b executed 2026-09-05, 09:00 implementer slot — the hypothesis is
>   REFUTED, and the refutation names the next suspect.** Two refined rungs,
>   one window each, band untouched, row still 🟡. The residual is **not**
>   monotone in sheet resolution:
>
>   | `conductor_resolution` | cells | `sheet_width_m` per port | C = 100 pF | L = 1 µH |
>   |---|---|---|---|---|
>   | ×1 (step 1's record) | 116 085 | 7.294123600e-03 ×4 | 1.595580e-03 | 3.370512e-03 |
>   | ×0.75 | 161 695 | **6.884098695e-03 / 7.649794837e-03 alternating** | 4.187955e-03 (×2.6247) | 8.875487e-03 (×2.6333) |
>   | ×0.6 | 209 604 | 7.674817764e-03 ×4 | 1.490415e-03 (×0.9341) | 3.144877e-03 (×0.9331) |
>
>   (`20260905T140449Z_PORT-14-step1b-r075.log:1886–1888, 1892–1893, 1897–1898`,
>   Status 0, 149 s, `-n 2`; `20260905T140738Z_PORT-14-step1b-r060.log:1877–1879,
>   1885–1886, 1892–1893`, Status 0, 136 s, `-n 4` — licensed because the first
>   window came in under 300 s. Both heavy by ceiling; a `--collect-only`
>   import smoke first, `20260905T140432Z_PORT-14-step1b-smoke.log:76–77`,
>   Status 0, 5 s.) **Asserted and green on both rungs** (imported bands, none
>   moved): reciprocity `‖S−Sᵀ‖/‖S‖` = **2.392912949e-14** (×0.75) and
>   **1.574340894e-14** (×0.6) against 1e-3; `σ_max` = **0.999992054** and
>   **0.999992924** against 1 + 1e-9; cell count strictly above the record on
>   both; and the ceiling-first Γ = 0 control asserted on both terminations of
>   both rungs (Δ = 0.3202 / 0.3232 and 0.3217 / 0.3252, missing by 0.3204 /
>   0.3267 and 0.3218 / 0.3264 — 200–330× the band, as step 1). So each rung is
>   a valid 4×4 and its residual means something.
>   **Reading.** The residual rises 2.6× on the ×0.75 rung and falls 0.93× on
>   the finer ×0.6 rung — not monotone, so the slot's |Γ|-plus-resolution
>   hypothesis is refuted; and step 2 (64 MHz) is **not** queued on "the finer
>   rung" as the pre-registration would have had it. What the residual *does*
>   track is the pre-registered next suspect, `sheet_width_m` (`lumped.py:353`,
>   the area-based effective width off the **measured** extents): the ×0.75
>   rung is the only one whose four narrowed sheets do not share one width —
>   they alternate 6.884e-03 / 7.650e-03, a C4 break of ±5.3% — and it is the
>   only rung whose residual rises. The two elements move by the *same* factor
>   on each rung to 4 significant figures (2.6247 / 2.6333; 0.9341 / 0.9331),
>   i.e. the residual is a common geometric factor times a per-element
>   constant, not an element-type effect — which is the same conclusion step 1
>   drew from the |Γ| ordering, now with the geometry named.
>   **`PORT-14` step 1c is therefore the live branch:** the sheet law's
>   effective width, not mesh density. Note the C4 break is invisible to
>   `PORT-9`'s reciprocity/passivity/C4 gates — all three pass on the ×0.75
>   rung — so it is a defect only the reduction identity can see. Code from
>   this step is additive and gate-neutral: `conductor_resolution=None` on
>   `tests/mesh/test_birdcage_port_sheets.py::_build` and on
>   `build_four_port_sweep` (`None` ⇒ the module `CONDUCTOR_RESOLUTION`, every
>   gate's mesh bit-identical), and three rung tests in
>   `tests/validation/test_port_lumped_rlc_termination.py` that **skip** unless
>   `FEM_EM_PORT14_CONDUCTOR_RESOLUTION_FACTOR` is set, so the gate rung (and
>   its deliberately red gate test) is untouched and was not re-run here.
> * **Step 1c (the width law, measured on a fixed mesh; scoped 2026-09-05
>   10:30 review, §9 item 4).** Step 1b's table has one clean discriminator
>   in it: the ×0.75 rung is the only rung whose four `sheet_width_m` values
>   are not equal (6.884e-03 / 7.650e-03 alternating, ±5.3% about their
>   mean) and the only rung whose residual *rose*. Hold the **×1 mesh**
>   (116 085 cells, the gate rung — no new mesh) fixed and perturb the width
>   the sheet law is *told*, per port, through the `LumpedSheetPortSpec`
>   rebuild the module already does in `_terminated_three_port`
>   (`test_port_lumped_rlc_termination.py:101–125`): three configurations,
>   each a full 50 Ω 4×4 (4 solves) plus the L and C terminated 3×3s (6
>   solves) with the 4×4 reduced by the *nominal* Γ exactly as step 1 —
>   **(A) common +5%**, **(B) common −5%**, **(C) alternating ±5.3%**
>   (P1, P3 at +5.3%, P2, P4 at −5.3% — step 1b's ×0.75 rung reproduced on
>   the gate mesh). Baseline is step 1's record (1.595580e-03 / 3.370512e-03),
>   imported not re-run. **The pre-stated readings.** The sheet resistivity
>   is `Z_p · w/h` (`lumped.py:111`), so a *common* factor `(1+ε)` on `w`
>   scales every sheet's effective `Z` by `(1+ε)` while the reduction's Γ is
>   built from the nominal `Z_p/z0` ratio, which the common factor leaves
>   invariant; the field-solved S is referenced to the nominal `z0 = 50`
>   through `_power_waves`, which it does not. Hence: (1) if the residual
>   under (A)/(B) moves **linearly in ε and in opposite directions** with
>   a common zero-crossing `ε*` for C and L (both elements moved by the
>   same factor per rung in step 1b to 4 s.f., so the crossing must be
>   common), the width law is the lever and `(1+ε*)` is the correction
>   the area-based `A/h` is missing — a step 1d re-derives the effective
>   width (edge-based, or from the sheet's own 50 Ω self-consistency) and
>   then, and only then, re-runs the gate; (2) if (A)/(B) leave the
>   residual **flat** (< 10% change) while (C) moves it by the step 1b
>   factor (×2.6-class), the *uniformity* of the widths is what the
>   identity sees and the law's absolute value is exonerated — the suspect
>   becomes the sheet's non-single-mode content itself, which is a
>   resolution-of-the-*sheet* question the ×0.75 rung's C4 break masked,
>   and step 2 (64 MHz) waits on a sheet-refinement rung, not a conductor
>   one; (3) if none of (A)/(B)/(C) moves the residual by more than 10%,
>   `sheet_width_m` is exonerated entirely, the ×0.75 rise is a mesh
>   artefact, and the next suspect is the reduction's assumption that the
>   terminated sheet is the *same* port (same `I`, same `V` definition) the
>   50 Ω sweep measured — a `sheet_terminal_current` question. **Anchors
>   (asserted, all imported, none moved):** per configuration, reciprocity
>   ≤ `RECIPROCITY_BAND` and `σ_max ≤ 1 + PASSIVITY_SIGMA_TOLERANCE` on the
>   4×4 — a perturbed width must still give a valid passive reciprocal
>   network or its residual means nothing; cell count = the 116 085 record
>   (same mesh, bitwise). **Negative control, ceiling first:** the Γ = 0
>   control on each configuration as step 1 did (Δ from the 4×4 first,
>   assert ≥ 5× the band only where Δ ≥ 5e-3; step 1 measured 0.32 / 0.33).
>   **Printed, not asserted:** the six residuals, each beside the record
>   and as a factor of it; the per-port `sheet_width_m` actually passed.
>   **Tier / ranks / cost:** 30 solves on the gate mesh; step 1's 13 solves
>   ran 105 s at `-n 2` ⇒ ≈ 240 s, one window, `timeout -k 30 600`, `-n 2`
>   (this is a fixed-mesh measurement, so `-n 4` is licensed if the first
>   configuration passes 100 s — split into two windows rather than
>   overrun). **Traps:** step 1's list; the width goes into the spec and
>   *only* the spec — the mesh, the facet tags and the measured extents are
>   untouched, so print the widths passed per port and per configuration;
>   the gate rung's red test is not re-run here; `abs`/`.real` before any
>   comparison; `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first,
>   pytest `-s`; the new tests **skip** unless `FEM_EM_PORT14_WIDTH_SWEEP`
>   is set, so `main`'s red set does not change. **Scope:** a measurement
>   on the gate mesh at 10 MHz; `REDUCTION_BAND` stays 1e-3, the row stays
>   🟡, no record moves, no §2 change, no `src/` change. **Negative result:**
>   reading (3) is itself the finding — §7 annotation naming the
>   `sheet_terminal_current` suspect, stop; a configuration whose 4×4 fails
>   reciprocity/passivity is a fixture finding (known-issues with its
>   widths, stop).
> * **Step 1c executed 2026-09-05, 21:30 implementer slot — the data select
>   pre-registered reading (1): `sheet_width_m` IS the lever, and the
>   zero-crossing is common to both elements.** One window, one mesh, band
>   untouched, row still 🟡, no record moved, no `src/` change.
>   `20260905T213322Z_PORT-14-step1c.log`, heavy tier by ceiling
>   (`timeout -k 30 570`), `-n 2`, complex build, **`9 passed, 6 deselected
>   in 230.46s`, Status 0, 258 s** (`:2132`, `:2138–2139`) — 34 solves on the
>   one 116 085-cell gate mesh (baseline 4×4 + 3 × (4 + 3 + 3)); a
>   `--collect-only` import smoke first, `20260905T213309Z_PORT-14-step1c-smoke.log:55`
>   (`9/15 tests collected (6 deselected)`), Status 0, 4 s.
>
>   The baseline rung reproduces step 1b's ×1 row exactly: **116 085 cells**,
>   `sheet_width_m` = **7.294123600e-03 m ×4** (`:1924`). Per configuration,
>   the residuals **printed, not asserted**, beside step 1's record:
>
>   | config | ε per port (P1…P4) | widths told (m) | C = 100 pF | L = 1 µH |
>   |---|---|---|---|---|
>   | — (step 1's record) | 0 | 7.294123600e-03 ×4 | 1.595580e-03 | 3.370512e-03 |
>   | **A** common +5% | +.05 ×4 | 7.658829780e-03 ×4 | **9.260556e-03 (×5.803881)** | **1.965102e-02 (×5.830276)** |
>   | **B** common −5% | −.05 ×4 | 6.929417420e-03 ×4 | **5.980286e-03 (×3.748033)** | **1.255208e-02 (×3.724086)** |
>   | **C** alt. ±5.3% | +.053/−.053/+.053/−.053 | 7.680712151e-03 / 6.907535049e-03 alternating | **8.990276e-03 (×5.634488)** | **1.914418e-02 (×5.679903)** |
>
>   (`:1976–1981, 1985–1986` (A); `:2045–2050, 2054–2055` (B);
>   `:2114–2119, 2123–2124` (C).)
>   **Asserted and green on all three** (imported bands, none moved, all nine
>   tests pass): cell count **116 085 bitwise** on every configuration — the
>   perturbation enters the `LumpedSheetPortSpec` and nothing else, through
>   `build_four_port_sweep`'s existing `reuse` route with `sheets[k]["w"]`
>   scaled; reciprocity `‖S−Sᵀ‖/‖S‖` = **1.891254889e-14 / 4.829117353e-15 /
>   7.780907717e-15** against 1e-3; `σ_max` = **0.999988336 / 0.999997273 /
>   0.999996814** against 1 + 1e-9 — so each perturbed 4×4 is a valid passive
>   reciprocal network and its residual means something. The ceiling-first
>   Γ = 0 control is asserted on all six terminations (Δ = 0.3254 / 0.3281,
>   0.3177 / 0.3221, 0.3060 / 0.3081, all above the 5e-3 floor; misses 0.3259 /
>   0.3361, 0.3175 / 0.3173, 0.3064 / 0.3157 — 200–330× the band, as step 1)
>   (`:1990–1991`, `:2059–2060`, `:2128–2129`).
>
>   **Reading — outcome (1), with one qualification.** (A) and (B) both move
>   the residual by far more than the 10% the pre-registration set as "flat":
>   ×5.80 and ×3.75. So outcomes (2) and (3) are excluded and `sheet_width_m`
>   is **not** exonerated: the width the law is told is the lever, on a mesh
>   that did not move by a single cell. The qualification is that the two
>   directions do **not** move the residual in opposite directions — both
>   *raise* it — so the zero-crossing lies **inside** ±5%, not outside it, and
>   the nominal `A/h` is already near the optimum rather than off by a
>   discoverable factor. Post-hoc arithmetic on the three printed residuals
>   (*a three-point fit done by hand on the log's numbers, not a measurement,
>   and nothing in code depends on it*): modelling the residual as
>   `|r₀ + kε|` and solving for the vertex of `r²(ε)` gives
>   **ε\* = −0.01074 (C = 100 pF)** and **ε\* = −0.01097 (L = 1 µH)** with a
>   fitted minimum of **zero to within the fit's own error** (both `r²(ε*)`
>   come out marginally negative, −1.4e-07 and −1.2e-06 in `r²`). That is
>   exactly the pre-registered signature of reading (1): a **common**
>   zero-crossing for the two elements — the two agree to 2% of each other —
>   at an effective width ≈ **1.1% below** the area-based `A/h`, and the
>   sensitivity `|k|` is 0.153 (C) / 0.323 (L) per unit ε, i.e. a 1% width
>   error alone produces a residual of order the whole 1.6e-03 / 3.4e-03 miss.
>   As in step 1b, the two elements move by the **same factor** on each
>   configuration to 3 s.f. (5.804 / 5.830; 3.748 / 3.724; 5.634 / 5.680) — a
>   common geometric factor times a per-element constant, not an element-type
>   effect.
>
>   **Step 1b's "uniformity" framing is superseded by this.** Configuration
>   (C) — the ×0.75 rung's C4 break reproduced on the gate mesh, mean width
>   nominal — is **not** distinguishable from the common +5% configuration (A)
>   at the 3% level (5.634 / 5.680 vs 5.804 / 5.830), so the *uniformity* of
>   the four widths is not what the identity sees; the ×0.75 rung's ×2.6 rise
>   is the width **magnitude** effect, as its ∓5.6% / +4.9% departures from
>   nominal predict. Consistent with the terminated port P1's own width
>   dominating the sensitivity (it is the port whose sheet law and whose Γ
>   both enter the reduction), though these three configurations do not
>   separate the four ports and no per-port claim is made here.
>
>   **Not claimed.** `REDUCTION_BAND` stays **1e-3** and is not widened; the
>   gate test stays deliberately red on `main` and **was not re-run in this
>   slot** (`-k width_sweep`, 6 deselected); the row stays 🟡; no §2 change; no
>   `src/` change; 10 MHz only. The ε\* arithmetic above is a reading of three
>   points, not a re-derived width law — what would license a step 1d is a
>   review's call, not this slot's.
>   Code is additive and gate-neutral: `tests/validation/test_port_lumped_rlc_termination.py`
>   gains `WIDTH_CONFIGURATIONS`, a `width_sweep_baseline` fixture, a
>   parametrised `width_sweep_case` fixture and three tests, all of which
>   **skip** unless `FEM_EM_PORT14_WIDTH_SWEEP` is set.
> * **Step 1d (the origin of ε\*, measured; scoped 2026-09-05 18:00 review
>   under step 1c's own pre-registration — "linear with a common
>   zero-crossing ⇒ the `A/h` law needs a correction" — and it tunes
>   nothing).** Step 1c's fit says the sheet law closes the reduction
>   identity if told a width **1.07–1.10% below** the area-based `A/h`,
>   one number common to C and L. Step 1d does two things on the fixed
>   116 085-cell gate mesh. **(a) Name a geometric origin.**
>   `build_four_port_sweep` already measures per sheet `area`, `h` (the
>   bounding-box extent along the drive, `h_bbox`), `w_bbox`,
>   `w = area/h`, `facets`, `out_of_plane`
>   (`tests/validation/test_port_birdcage_four_port.py:319–337`). Print,
>   per port: `w/w_bbox − 1` (the ragged-edge fraction step 2b measured at
>   14–15% on the *full* width), `area/(w_bbox·h) − 1`, the reduced *mean*
>   height `area/w_bbox` against `h_bbox`, and the gap length the
>   generator was told beside `h_bbox`. The law uses
>   `R = Z_p·w/h = Z_p·A/h_bbox²`, so a facet set whose mean terminal
>   separation is 0.5% under its bounding box already produces a 1%
>   impedance offset — to first order `Z_eff = Z_p·h_actual/h_bbox`, from
>   `I = (1/R)∫(E·ĥ)dS/h` with `E ≈ V/h_actual`. Each candidate ratio is a
>   **prediction of ε\***; the pre-registered comparison is
>   `|ε_geom − ε\*| ≤ 0.3·|ε\*|` (≈ 0.3 pp) for *one* candidate — none there
>   means the origin is not geometric. **(b) Test the fit on a fourth
>   point.** Carry step 1c's six residuals as constants
>   (`STEP1C_RESIDUALS`, the log's printed digits: C 1.595580e-03 /
>   9.260556e-03 / 5.980286e-03 and L 3.370512e-03 / 1.965102e-02 /
>   1.255208e-02 at ε = 0 / +0.05 / −0.05), recompute ε\* per element in
>   code from the `|r₀ + kε|` model (never typed in), then run the two
>   lossless terminated 3×3s once more through the existing `reuse` route
>   with every told width scaled by `(1 + ε\*)` (configuration **D**, 10
>   solves) and print the residuals beside step 1's record *and* beside
>   `REDUCTION_BAND`. The fit predicts ≈ 0; whether both land ≤ 1e-3 is
>   **printed, not asserted**, because the width was fitted to the
>   residual — asserting it would be circular. **Anchors (asserted,
>   imported, unmoved):** D's 4×4 reciprocity ≤ `RECIPROCITY_BAND`,
>   `σ_max ≤ 1 + PASSIVITY_SIGMA_TOLERANCE`, cells 116 085 bitwise.
>   **Negative control (asserted — backed by step 1 / 1c's measurement of
>   the same comparison on this mesh, Δ = 0.31–0.33):** Γ = 0 on D, Δ
>   from the 4×4 first, the miss asserted ≥ 5× the band only where
>   Δ ≥ 5e-3. **Pre-registered readings (constants in code, printed, none
>   asserted):** (1) D ≤ 1e-3 on both *and* one `ε_geom` within 0.3 pp of
>   ε\* ⇒ **step 1e**, review-scoped: the fixture — geometry belongs to
>   the fixture, `lumped.py:351–357` — supplies the law that geometric
>   quantity instead of `h_bbox`, the red gate is re-run, and a residual
>   ≤ 1e-3 on *unfitted* input is what closes step 1; (2) D ≤ 1e-3 but no
>   geometric candidate predicts ε\* ⇒ the offset is a field effect of the
>   sheet (edge fringing — the single-mode residual proper); the
>   known-issues entry records it and **no** constant enters the law —
>   re-registering the band on measured evidence is the weekly's call;
>   (3) D not ≤ 1e-3 ⇒ the linear model fails beyond three points — print
>   `r(ε\*)` and stop. **Tier / ranks / cost:** step 1c's 34 solves took
>   258 s at `-n 2` (`20260905T213322Z_PORT-14-step1c.log:2138`); (b) is
>   14 solves (baseline 4 + 10) ≈ 110 s and (a) is geometry on the built
>   mesh ⇒ heavy by ceiling, one window, `timeout -k 30 400`, `-n 2`,
>   complex build, `tests/environment` first, pytest `-s`, behind
>   `FEM_EM_PORT14_WIDTH_SWEEP` like 1c with `-k step1d` so 1c's nine tests
>   are deselected. **Traps already paid for:** 1c's list —
>   `sheets[k]["w"]` is the only thing `reuse` reads, perturb it and
>   nothing else; `abs`/`.real` before `<=`; the red gate test is not
>   re-run; a mean-height candidate needs the facet *vertices* gathered
>   across ranks, not one rank's bounding box. **Scope:** a measurement at
>   10 MHz; `REDUCTION_BAND` stays 1e-3, the row stays 🟡, no `src/`
>   change, no §2 change. **Negative result:** every reading is
>   pre-registered — record it in this entry and in the known-issues
>   disposition and stop; a D whose 4×4 fails reciprocity/passivity is a
>   fixture finding (known-issues with its widths, stop).
> * **Step 1d executed 2026-09-05, 19:30 implementer slot — the data select
>   pre-registered reading (2): the three-point fit holds on a fourth point,
>   and the origin of ε\* is *not* one of the measured geometric ratios.**
>   One window, one mesh, band untouched, row still 🟡, no record moved, no
>   `src/` change. `20260906T003627Z_PORT-14-step1d.log`, heavy tier by
>   ceiling (`timeout -k 30 400`), `-n 2`, complex build,
>   `FEM_EM_PORT14_WIDTH_SWEEP=1`, `-k step1d`: `tests/environment`
>   **`11 passed … 24.23s`** (`:116`) then **`4 passed, 15 deselected in
>   110.42s`, Status 0, 137 s** (`:2114`, `:2120–2121`) — 14 solves on the
>   one 116 085-cell gate mesh (baseline 4×4 + D's 4×4 + 2 × 3 terminated);
>   a `--collect-only` smoke first, `20260906T003614Z_PORT-14-step1d-smoke.log`
>   (`4/19 tests collected (15 deselected)`), Status 0, 4 s.
>
>   **(b) The fit on a fourth point.** ε\* is recomputed **in code** from
>   `STEP1C_RESIDUALS` (step 1c's six printed digits) by solving the exact
>   parabola through the three `(ε, r²)` points — never typed in:
>   **ε\* = −0.010735 (C = 100 pF)**, **−0.010970 (L = 1 µH)**, fitted minima
>   −1.375055e-07 / −1.178493e-06 in `r²`, mean **ε\* = −0.010852**
>   (`:2005–2007`). Configuration **D** — all four told widths
>   7.294123600e-03 → **7.214965819e-03 m**, ratio **0.989147732**
>   (`:2094–2098`) — through the same `reuse` route on the same mesh gives,
>   **printed not asserted** (the width was fitted *to* these residuals, so
>   asserting them would be circular):
>
>   | element | residual at ε\* | vs step 1's record | vs `REDUCTION_BAND` = 1e-3 |
>   |---|---|---|---|
>   | C = 100 pF | **5.756561e-05** | 1.595580e-03 → **×0.036078** | **0.057566×** the band |
>   | L = 1 µH | **1.196780e-04** | 3.370512e-03 → **×0.035507** | **0.119678×** the band |
>
>   (`:2103–2105`.) The linear model predicted ≈ 0 at a point 5% outside the
>   fitted interval's centre and the measurement lands 17× / 28× below the
>   record — **reading (3) is excluded**: `|r₀ + kε|` holds beyond step 1c's
>   three points. It does not go to zero (5.8e-05 / 1.2e-04 remain), which is
>   the residual the width constant cannot explain.
>
>   **(a) No geometric origin.** Every sheet is identical to nine digits
>   (26 facets, area 5.835298880e-05 m², `h_bbox` 8.000000000e-03 m,
>   `w = A/h` 7.294123600e-03 m, `w_bbox` 9.167340025e-03 m, mean height
>   `A/w_bbox` 6.365313018e-03 m, out-of-plane 0.0) (`:2001–2004`, all from
>   `build_four_port_sweep`'s own comm-reduced `area`/`_sheet_extents`, so
>   nothing rank-local is read). Against the pre-registered window
>   **±0.003256** (0.3 × |ε\*|), the candidates read (`:2008–2040`, the same
>   on all four ports): `area/(w_bbox·h_bbox) − 1` = `w/w_bbox − 1` =
>   `h_mean/h_bbox − 1` = **−0.204336** (miss 0.193484; step 2b's ragged edge,
>   here 20.4% on the narrowed sheet), its inverse **+0.256812** (miss
>   0.267664), `h_bbox/port_box_z_told − 1` = **−0.200000** / **+0.250000**,
>   and the told gap length **matched exactly** — `h_bbox` = the generator's
>   `leg_gap_length` = 8.000000000e-03 m to nine digits, ε_geom = **+0.000000**,
>   miss **0.010852**. Nearest candidate 0.010852 = 3.3× the window. So the
>   1.09% is **not** a mis-measured terminal separation and not the ragged
>   edge: **reading (2)** — a field effect of the sheet (edge fringing, the
>   single-mode residual proper). Per the pre-registration **no constant
>   enters the law**, there is no step 1e, and re-registering the band on this
>   evidence is the weekly's call.
>
>   **Asserted and green** (imported bands, none moved): cells **116 085
>   bitwise**, reciprocity **9.998294990e-15** vs 1e-3, `σ_max` =
>   **0.999993774** vs 1 + 1e-9 (`:2099`) — D is a valid passive reciprocal
>   four-port, so its residual means something. The ceiling-first Γ = 0
>   control is asserted on both terminations: Δ = **0.321025 / 0.324791**
>   (above the 5e-3 floor), miss **0.321023 / 0.324743** = 321× / 325× the
>   band (`:2110–2111`) — the same 0.31–0.33 step 1 and 1c measured.
>
>   **Not claimed.** `REDUCTION_BAND` stays **1e-3**; the gate test stays
>   deliberately red on `main` and **was not re-run** (15 deselected); the row
>   stays 🟡; no §2 change; no `src/` change; 10 MHz only. D's residual is a
>   **fitted** number and closes nothing — what would close step 1 is a
>   residual ≤ 1e-3 on *unfitted* input. Code is additive and gate-neutral:
>   `tests/validation/test_port_lumped_rlc_termination.py` gains
>   `STEP1C_RESIDUALS`, `_epsilon_star`, `_geometric_candidates`, three
>   fixtures and four `step1d` tests, all skipping unless
>   `FEM_EM_PORT14_WIDTH_SWEEP` is set.
> * **Step 1e executed 2026-09-11, 07:30 implementer slot — F-small's
>   single-mode floor registered as a (1\*) record; the deliberate red
>   retires.** The 2026-09-06 weekly ruling (§10 Phase 6), tests only, no
>   `src/`. `REDUCTION_BAND` = 1e-3 keeps its value and comment and is **not**
>   re-registered. `tests/validation/test_port_lumped_rlc_termination.py`
>   gains `REDUCTION_FLOOR_F_SMALL` (C 1.595580e-03 / L 3.370512e-03 / R
>   7.249519e-04, cited to `20260905T020428Z_PORT-14.log:1858, 1865, 1872`),
>   `REDUCTION_FLOOR_RTOL` = 1e-3 and `RECORD_RANK_WIDTH` = 2. On the `OPS-41`
>   precedent the record assertion skips off `-n 2`, after the readings are
>   printed. The gate now asserts `|r/record − 1| ≤ 1e-3` per element and
>   prints each residual against the band as "systematic, not gated".
>   `STEP1_RESIDUAL_RECORD` takes its C/L entries from the new dict; R stays
>   out so `STEP1B_TERMINATIONS` is unchanged. `c4_congruent_sheets` off; the
>   `GEO-19` record mesh.
>   `20260911T123334Z_PORT-14-step1e.log`, standard tier (`timeout -k 30 300`),
>   `-n 2`, complex build, `-s`, no step 1b/1c/1d env var set:
>   **`15 passed, 16 skipped … 110.80s`** (`:2050`), **Status 0, 113 s**
>   (`:2118–2119`). Collect-only smoke first,
>   `20260911T123311Z_PORT-14-step1e-smoke.log` (31 collected `:81`, Status 0,
>   4 s).
>
>   | element | residual | record | ratio | `|ratio − 1|` | vs band (printed) |
>   |---|---|---|---|---|---|
>   | C = 100 pF | 1.595580e-03 | 1.595580e-03 | 0.999999762 | **2.380e-07** | 1.595580× |
>   | L = 1 µH | 3.370512e-03 | 3.370512e-03 | 1.000000106 | **1.065e-07** | 3.370512× |
>   | R = 200 Ω | 7.249519e-04 | 7.249519e-04 | 0.999999966 | **3.391e-08** | 0.724952× |
>
>   (`:1888, :1895, :1902`.) Every record reproduces ≥ 4 000× inside the rtol.
>   **Negative control (asserted, backed by the step 1 log):** held against
>   another element's record, each residual fails reproduction.
>   `|r_C/rec_L − 1|` = **0.526606** (pre-registered 0.527), and
>   `|r_R/rec_C − 1|` = **0.545650** (pre-registered 0.546) (`:1913, :1917`).
>   Every off-diagonal pair is asserted > 100× the rtol, so a swapped or
>   mis-keyed record cannot pass.
>   **Unmoved anchors, green:**
>   - 50 Ω baseline: reciprocity 1.044255156e-14 vs 1e-3, σ_max 0.999992805
>     vs 1 + 1e-9 (`:1884`; step 1 read 1.464e-14, the 1-ULP class).
>   - Γ = 0 control: Δ = 0.3218888 / 0.3254627 / 0.2112830, miss
>     0.3219520 / 0.3267853 / 0.2120063 (`:1922–1924`), step 1's digits
>     exactly.
>
>   **Not claimed:** no absolute-accuracy or single-mode-accuracy claim. The
>   residual *is* the sheet's named systematic (edge fringing, step 1d
>   reading (2)) on F-small at 10 MHz. `TH-17` may not gate a mode frequency
>   tighter than it without saying so. The row stays 🟡: step 2 (64 MHz) is
>   open and now unblocked. Known-issues 2026-09-05 `PORT-14` step 1 entry
>   retired in the same commit.
>
> **Step 2 executed 2026-09-11 (13:30 slot) — negative result: at 64 MHz the
> capacitor's residual is above the item's 1e-2 stop line.** Env
> `FEM_EM_PORT14_STEP2_64MHZ=1` drives the same fixture, sweep and
> terminations at 64 MHz on the 116 085-cell record mesh (`c4_congruent_sheets`
> off). The 10 MHz record tests print their readings and then skip. The default
> path is unchanged. Anchor `20260911T183201Z_PORT-14-step2.log`, `-n 2`, standard:
> 13 passed, 18 skipped in 113.60 s (`:2053`), Status 0, Elapsed 115 s (`:2122`).
>
> | Element | Z_p at 64 MHz | Γ | residual | × 10 MHz record | × band |
> |---|---|---|---|---|---|
> | C = 100 pF | −j24.86796 Ω | −0.603378−0.797455j | **1.354202e-02** | 8.487 | 13.54 |
> | L = 1 µH | +j402.1239 Ω | +0.969550+0.244893j | 5.021261e-04 | 0.149 | 0.50 |
> | R = 200 Ω | 200 Ω | +0.600000 | 7.445387e-04 | 1.027 | 0.74 |
>
> (`:1882–1884, :1891, :1898, :1905`.)
> - **Anchors (asserted, imported, unmoved), green.** 50 Ω reciprocity
>   9.950176195e-16 against 1e-3, σ_max 0.999721388 against 1 + 1e-9 (`:1885`).
>   Γ = 0 control asserted on all three: Δ = 0.4806 / 0.2390 / 0.1829, miss
>   0.4940 / 0.2393 / 0.1836 (`:1924–1926`). The identity is resolved and no
>   coupling skip fired.
> - **Proof the sweep was rebuilt.** S₁₁ is +4.488964206e-02+5.803022759e-01j
>   against 10 MHz −3.712480826e-01+1.417750480e-01j, and S₂₁ moved by 1.915e-01
>   (`:1886–1887`). The `reuse=` route is mesh-only and the problem is rebuilt at
>   `frequency_hz`.
> - **Routes.** The 50 Ω 4×4 rides `PORT-19`'s reuse-on default; the terminated
>   3×3s go through `run_lumped_sheet_port_case` directly.
> - **Default-path control.** `20260911T183421Z_PORT-14-step2-default.log`
>   (flag unset): 15 passed, 16 skipped, Status 0, 111 s. The 10 MHz records
>   reproduce to |ratio − 1| = 2.380e-07 / 1.065e-07 / 3.391e-08
>   (`:1888, :1895, :1903`).
>
> **Reading.** L and R stay under the 1e-3 band; C does not, and it is above
> 1e-2. Both C and L have |Γ| = 1, yet C rose ×8.5 while L fell ×0.15, so
> 10 MHz's ordering does not carry over. Per the item's negative-result clause
> the three residuals are recorded here and the step stopped.
>
> **Not changed.** No 64 MHz record is registered, no band moves, and `PORT-15`
> gate (i) is not opened. `PORT-15` gate (i) and `TH-17` must not assume a 64 MHz
> floor ≤ 1e-2 for a capacitive termination. The row stays 🟡.
>
> **Hypothesis for the next step (unqueued).** The residual may follow the
> terminated sheet's current. −j24.9 Ω may partly cancel the leg reactance and
> re-excite the sheet's fringing content. The next step would print |I_P1| per
> element and cond(I − S_bb Γ) at 10 and 64 MHz from the solves the module
> already returns.
>
> **Ruled and scoped 2026-09-11 18:00 review — steps 2b and 2c (§9 items 2
> and 5), both measure-only.** The review's arithmetic on step 2's printed
> 64 MHz S₁₁ (`:1886`) gives `|D| = |1 − S₁₁Γ|` = 0.6837 / 1.2393 / 1.0335 for
> C / L / R. So the reduction's first-order sensitivity to the terminated
> column, `|Γ|²/|D|²` = 2.1395 / 0.6511 / 0.3371, spreads C:L by only 3.3×
> against the measured 27× residual spread. *Predicted:* amplification through
> S₁₁ does not carry the C residual, and the slot's cond(I − S_bb Γ) reading
> alone would not discriminate. **Step 2b** therefore fits the termination the
> field solve actually realised. For one terminated port the reduction is
> `S′ − S_aa = t·M` with the rank-1 `M = S_a1 S_1a` and `t = Γ/(1 − S₁₁Γ)`.
> The least-squares `t` is a closed-form projection, `Γ_eff = t/(1 + S₁₁t)`,
> and `Z_eff = z0(1 + Γ_eff)/(1 − Γ_eff)`. Printed at 10 and 64 MHz per
> element: `ΔZ = Z_eff − Z_p`, `Z_eff/Z_p − 1`, and the non-rank-1 remainder.
> A **common ΔZ** across C/L/R that scales with ω would read as unmodelled
> series reactance. A **common Z_eff/Z_p − 1** would read as step 1c's
> proportional width law. **Step 2c** runs step 1c's width configurations at
> 64 MHz. Neither step registers a record or moves a band, and `PORT-15` gate
> (i) stays closed until a 64 MHz record exists.
>
> **Step 2b executed 2026-09-11 (21:00 slot). One realised termination carries
> the whole residual at both frequencies.** Tests only, no `src/` change:
> `_realised_termination` and `test_step2b_the_realised_termination_is_printed`
> were added, and the fixture now keeps `results`. Four windows, all `-n 2`,
> standard, `timeout -k 30 300`, each Status 0:
> - `20260912T020247Z_PORT-14-step2b.log` (64 MHz, 14 passed / 18 skipped,
>   122 s);
> - `20260912T020500Z_PORT-14-step2b-default.log` (10 MHz, 16 / 16, 118 s);
> - the same two re-run with one added post-hoc κ print:
>   `20260912T020824Z_PORT-14-step2b-w2.log` (116 s) and
>   `20260912T021021Z_PORT-14-step2b-default-w2.log` (118 s).
>
> The nominal residuals, `Z_eff` and `t` reproduced to every printed digit in the
> re-runs, and the remainders to ≤ 3e-6 relative. Readings (w2 logs, 64 MHz
> `:1927–1954`, 10 MHz `:1927–1955`):
>
> | Element | f | \|Z_eff/Z_p − 1\| | Re ΔZ (Ω) | Im ΔZ/ω (H) | remainder / nominal | κ_k = ΔZ/(Z_p − z0) | \|I_P1\|/\|I_drive\| (P2/P3/P4) |
> |---|---|---|---|---|---|---|---|
> | C | 10 MHz | 1.109475e-02 | −0.5294121 | −2.681e-08 | 2.2e-7 | 1.058471e-02 | 0.180 / 0.166 / 0.180 |
> | L | 10 MHz | 1.353422e-02 | −0.5292585 | +1.059e-08 | 2.3e-7 | 1.059024e-02 | 0.355 / 0.338 / 0.355 |
> | R | 10 MHz | 7.941857e-03 | +1.588371 | −1.543e-11 | 2.5e-7 | 1.058914e-02 | 0.120 / 0.112 / 0.120 |
> | C | 64 MHz | 2.374962e-02 | −0.5295059 | −6.506e-10 | 1.7e-6 | 1.057617e-02 | 0.811 / 0.727 / 0.811 |
> | L | 64 MHz | 1.073146e-02 | −0.5278062 | +1.065e-08 | 2.1e-6 | 1.064945e-02 | 0.084 / 0.064 / 0.084 |
> | R | 64 MHz | 7.940094e-03 | +1.588007 | −1.527e-11 | 2.1e-6 | 1.058671e-02 | 0.159 / 0.120 / 0.159 |
>
> The κ_k imaginary parts are ≤ 4.1e-05. Pooled post-hoc κ is
> 1.058709e-02 − 3.6e-06j at 10 MHz (per-element misfit ≤ 3.4e-4, `:1948–1951`)
> and 1.064081e-02 − 1.5e-05j at 64 MHz (misfit ≤ 6.2e-3, `:1947–1950`).
> - **Anchors (asserted), green in all four windows.**
>   - (a) Recovery from the exact (C2) reduction: ≤ 1.227e-15 against 1e-9.
>   - (b) The ×1.01 reduction: ≤ 7.856e-16 against 1e-6.
>   - (c) Reproduction of step 2's 64 MHz residuals: 2.827e-07 / 7.581e-08 /
>     4.728e-08 against rtol 1e-5. *Disclosed extension:* the same assertion
>     also runs at 10 MHz against `REDUCTION_FLOOR_F_SMALL` (2.380e-07 /
>     1.065e-07 / 3.391e-08). That is additive and backed by
>     `20260911T183421Z_PORT-14-step2-default.log:1888, :1895, :1903`.
> - **Negative control (asserted).** Held against the other frequency's reading,
>   every residual misses by ≥ 2 631× the rtol (R, 10 MHz) against the 100× bar.
> - **Pre-registered predictions (printed only).**
>   - Remainder ≪ nominal: **held**, ≤ 2.5e-6 of nominal everywhere, so no
>     error lives in the kept block.
>   - Common `Im ΔZ/ω` within 2×: **failed** at both frequencies (signs differ).
>     The unmodelled-series-inductance reading is refuted.
>   - Common `Z_eff/Z_p − 1` within 2×: **held at 10 MHz** (1.70×), **failed
>     at 64 MHz** (2.99×; C:L 2.21×).
> - **Observation, not asserted.** The six nominal residuals order exactly as
>   `|I_P1|/|I_drive|` does. C at 64 MHz carries 0.81 of the drive current and
>   the largest residual.
>
> **Reading: slot derivation, a hypothesis for the review.** The post-hoc fit
> `ΔZ = κ(Z_p − z0)` with a single real κ holds on all six readings. Suppose
> every sheet realises `(1+κ)·Z_told` while the port voltage is still reported
> as `V_src − I·Z_told`. Then the 50 Ω 4×4 is the network plus a series `κ·z0`
> at each port, and a terminated sheet presents `Z_p + κ(Z_p − z0)` to it. That
> is the printed form. So step 1c's proportional law, applied to *all four*
> sheets, would explain C's 64 MHz jump as the same κ reached through a larger
> sheet current, not a new mechanism. It would also explain why the literal
> `Z_eff/Z_p − 1` test is not common, since that quantity is `κ(1 − z0/Z_p)`.
> Three independent numbers agree to about three figures:
> - κ at 10 MHz, 1.0587e-2;
> - step 1c's −ε\* ≈ 1.07 / 1.10e-2;
> - `PORT-16`'s C/terminal − 1 = 1.0592e-2 on the same `build_four_port_sweep()`
>   fixture (`20260907T051231Z_PORT-16.log:1895–1910`).
>
> That points at the Cauchy–Schwarz sheet-field non-uniformity as κ's origin.
> This is unproven here.
>
> **§9 item 5 (step 2c).** Its literal skip condition fires: at 64 MHz C and
> L's `Z_eff/Z_p − 1` differ by 2.21× > 2×. But the reading above says that
> observable is the wrong test of the proportional law, so whether 2c is
> BLOCKED or re-pointed at κ is the review's ruling. **Not changed:** no
> record, no band, no `Z_p` correction; `PORT-15` gate (i) stays closed and the
> row stays 🟡.
>
> **Ruled 2026-09-12 03:00 review.** Step 2b accepted (re-read
> `…step2b-w2.log:1947–1951`, `…step2b-default-w2.log:1948–1951`). Step 2c is
> **re-pointed at κ, not BLOCKED**: `Z_eff/Z_p − 1` is `κ(1 − z0/Z_p)` under
> the proportional law, so the 18:00 skip condition tested the wrong
> observable. 2c now predicts ε\* = −κ_k at 64 MHz (§9 item 4). Step 2d (§9
> item 3) tests κ's origin: the `PORT-16` module driven at 64 MHz through the
> existing `frequency_hz` keyword prints C/terminal − 1 beside κ(64 MHz) =
> 1.0641e-2. If they agree as they do at 10 MHz (1.0592e-2 against 1.0587e-2),
> a single multiplicative correction on the told sheet impedance is the
> candidate route to a 64 MHz record for `PORT-15` gate (i) — the weekly's to
> scope, never an in-slot change.
>
> **Step 2d executed 2026-09-12 (07:30 slot). At 64 MHz, C/terminal − 1 reads
> κ(64) to −0.3 %.** Tests only, in the `PORT-16` module
> (`test_birdcage_power_identity.py`), additive: env `FEM_EM_PORT16_64MHZ`, and
> new `test_step2d_c_over_terminal_is_printed`. When the flag is on, (iv) prints
> and skips. Two windows, `-n 2`, standard, `timeout -k 30 300`, `rc=0`:
> - `20260912T123236Z_PORT-14-step2d-64mhz.log`: 16 passed / 1 skipped, 93 s;
> - `20260912T123429Z_PORT-14-step2d-10mhz.log`: 17 passed, 92 s.
>
> - **Anchors (asserted).**
>   - (i) closes at 64 MHz: 3.3e-15 to 7.0e-15 on P1–P4 and 4.3e-15 on the ×2
>     control, against 1e-6 (`…64mhz.log:1882–1891, :1922`). (ii) and (iii)
>     are green at 64 MHz.
>   - Flag off, C/terminal − 1 reproduces the 10 MHz readings to ≤ 1.45e-10
>     against rtol 1e-5 (`…10mhz.log:1938–1944`). The references are computed
>     from the ten-digit C and gap values at `20260907T051231Z_PORT-16.log:1917–1920`.
> - **Negative control (asserted).** S₁₁ at 64 MHz sits 6.045e-01 from
>   `STEP1E_S11_S21_10MHZ` (`…64mhz.log:1940`), so the sweep was rebuilt.
> - **Readings (printed, `…64mhz.log:1942–1949`).** C/terminal − 1 =
>   1.060762e-02 / 1.060916e-02 / 1.061032e-02 / 1.060766e-02 on P1–P4.
>   - Against pooled κ(64) = 1.064081e-02, that is 0.99688–0.99714×. The
>     predicted 5 % window holds; the 20 % negative-result bar is far away.
>   - The readings sit between κ_C (+0.30 %) and κ_L (−0.39 %).
>   - The per-sheet spread is 1.06040e-02 to 1.06123e-02.
> - **Frequency shift (printed).** From 10 to 64 MHz, C/terminal − 1 moves by
>   +0.15 % (1.059204e-02 → 1.060762e-02 on P1), while κ moves by +0.51 %
>   (1.058709e-02 → 1.064081e-02). The predicted sign held; the size is
>   ≈ 0.3× κ's. So κ − (C/terminal − 1) grows from ≈ 5e-6 at 10 MHz to
>   ≈ 3.3e-5 at 64 MHz.
> - **Other printed readings.** The ×2 control's sheet factor at 64 MHz is
>   0.349799, outside the predicted [0.5, 2]. That window is printed only.
>
> **Reading.** κ is the terminal form's Cauchy–Schwarz deficit to ≤ 0.5 % at
> both frequencies. A frequency-growing ≈ 0.3 % remainder is not in that
> deficit. **Not changed:** no record, no band, no `Z_p` correction. The row
> stays 🟡, `PORT-16` stays ✅, and `PORT-15` gate (i) stays closed. The
> multiplicative-correction route is the weekly's to scope; item 4 (step 2c's
> width lever at 64 MHz) is the independent read.
>
> **Step 2c (re-pointed) executed 2026-09-12 (09:00 slot). At 64 MHz the told
> width's zero-crossing reads −κ_k to +3.1 % (C) and −4.2 % (L).** Tests only,
> additive, in `test_port_lumped_rlc_termination.py`. `width_sweep_baseline` and
> `width_sweep_case` take `_rlc_frequency_hz()` for both
> `build_four_port_sweep` and `series_rlc_impedance` (flag unset ⇒
> `FREQUENCY_HZ`, bit-identical arithmetic); the step-1c print lines name the
> frequency; new `test_the_width_sweep_epsilon_star_fit_is_printed` fits
> through (0, step 2's ε = 0 residual), (+5 %, A), (−5 %, B) once all three
> configurations are in. One window:
> `20260912T140430Z_PORT-14-step2c.log`, `FEM_EM_PORT14_WIDTH_SWEEP=1
> FEM_EM_PORT14_STEP2_64MHZ=1`, `-n 2`, `-s`, `-k "width_sweep or
> environment"`, `timeout -k 30 590`, durable capture: **23 passed,
> 12 deselected in 183.45 s** (`:2163`), `[capture] rc=0` (`:2229`), Status 0,
> **185 s** (`:2232–2233`). Heavy by ceiling.
>
> - **Anchors (asserted, unmoved), green.** f = 6.400000e+07 Hz on every line
>   (`:1880, :1932, :2003, :2074`); 116 085 cells bitwise on A / B / C;
>   reciprocity 1.351536152e-15 / 2.238321049e-15 / 1.934662477e-15 against
>   1e-3; σ_max 0.999535567 / 0.999907252 / 0.999839277 against 1 + 1e-9
>   (`:1937, :2008, :2079`).
> - **Negative control (asserted).** Γ = 0 on all six terminations: Δ =
>   0.4671 / 0.2400, 0.4928 / 0.2377, 0.4516 / 0.2319; misses 0.5454 / 0.2416,
>   0.4431 / 0.2366, 0.5331 / 0.2335 — ≥ 234× the band against the 5× bar
>   (`:1946–1947, :2017–2018, :2088–2089`).
>
> | config | C = 100 pF residual (× ε = 0) | L = 1 µH residual (× ε = 0) |
> |---|---|---|
> | ε = 0 (step 2, `…step2.log:1891, :1898`) | 1.354202e-02 | 5.021261e-04 |
> | A common +5 % | 7.879573e-02 (×5.818610) | 2.862518e-03 (×5.700796) |
> | B common −5 % | 5.047888e-02 (×3.727574) | 1.895173e-03 (×3.774297) |
> | C alt. ±5.3 % | 8.205738e-02 (×6.059464) | 2.859601e-03 (×5.694986) |
>
> (`:1941–1942, :2012–2013, :2083–2084`.)
> - **Fit (printed, `:2093–2098`).** ε\*(C) = **−0.010908** (10 MHz −0.010735),
>   ε\*/(−κ_C) = **1.031340**; ε\*(L) = **−0.010199** (10 MHz −0.010970),
>   ε\*/(−κ_L) = **0.957693**.
> - **Predictions (printed only).** Within 10 % of −κ_k: **held** on both
>   (3.1 %, 4.2 %). C/L within 2 %: **failed**, ε\*(C)/ε\*(L) = 1.069490.
>   Both ±5 % directions raise L's residual: **held** (×5.70, ×3.77).
> - **Negative-result bars: none fires.** Off −κ_k by > 30 %: clear. C vs L by
>   > 2×: clear. All residuals within ±10 % of ε = 0: clear (factors 3.7–6.1).
> - **Observation, not asserted.** C's parabola dips below zero,
>   r²(ε\*) = −1.626e-05 against r₀² = 1.834e-04 (≈ 9 %; at 10 MHz it was
>   −1.4e-07). So C's three 64 MHz points are not exactly `|r₀ + kε|`. L's
>   minimum is +1.74e-08 against 2.52e-07. The ε = 0 point comes from step 2's
>   window, which reproduced to ≤ 3e-7 across runs (step 2b anchor (c)).
>
> **Reading.** The width lever reaches the proportional law at 64 MHz. Each
> element's zero-crossing sits within 5 % of its own −κ_k, as at 10 MHz. The
> C/L split grew from 2 % at 10 MHz to 7 % at 64 MHz, and that is the only
> pre-registered prediction that missed. It is the same order as C's
> departure from the linear model above. **Not changed:** no record, no band,
> no `Z_p` correction. The row stays 🟡 and `PORT-15` gate (i) stays closed.
> Whether a `(1+κ)` correction becomes a registered route is the weekly's.
>
> **Step 2e executed 2026-09-12 (13:30 slot). Configuration D at 64 MHz takes
> both lossless residuals under `REDUCTION_BAND`.** Tests only, additive, same
> module. Under `FEM_EM_PORT14_STEP2_64MHZ`, `step1d_baseline` and
> `step1d_configuration_d` take `_rlc_frequency_hz()`, and `step1d_fit` fits
> `STEP2C_RESIDUALS` (step 2's ε = 0 plus 2c's A/B). Two new tests skip with the
> flag off: `test_step1d_step2e_the_64mhz_fit_reproduces_step2c` and
> `test_step1d_step2e_the_baseline_was_built_at_64mhz`. The terminated-solve
> test stores its in-window ε = 0 residuals before its 64 MHz skip. One window:
> `20260912T183330Z_PORT-14-step2e.log`, `WIDTH_SWEEP=1 STEP2_64MHZ=1`,
> `-n 2`, `-s`, `-k "step1d or terminated_solve_matches or environment"`,
> `timeout -k 30 590`, durable capture: **17 passed, 1 skipped, 19 deselected
> in 189.13 s** (`:3897`), `[capture] rc=0` (`:3963`), Status 0, **191 s**
> (`:3966–3967`). Heavy by ceiling.
>
> - **Anchors and controls (asserted), green.**
>   - The fit reproduces 2c's printed ε\* to 3.38e-05 (C) and 9.36e-06 (L)
>     against rtol 1e-4 (`:3756–3757`). The mean is −0.010553268 against the
>     09:00 journal's hand-rounded −0.010554 (6.94e-05, `:3758`).
>   - The baseline was rebuilt at 64 MHz: S₁₁ sits 6.045467e-01 from the
>     10 MHz record (`:3762`), equal to step 2d's to every printed digit.
>   - D (widths × 0.989446732): 116 085 cells bitwise, reciprocity
>     1.897246132e-15, σ_max 0.999760614 (`:3816–3821`).
>   - Γ = 0 on D: Δ 0.4833 / 0.2388, misses 0.4832 / 0.2388, ≥ 239× the band
>     (`:3831–3832`).
> - **Negative control by reproduction (predicted rtol 1e-6): held.** In-window
>   ε = 0 is 1.354202e-02 / 5.021261e-04, |ratio − 1| = 2.827e-07 / 7.581e-08
>   against step 2 (`:1886, :1893, :3825–3826`). 2c's mixed-window fit is not
>   undermined by drift.
>
> | element | D residual | D/(ε = 0), 64 MHz | step 1d D/(ε = 0), 10 MHz | fit's prediction at the mean ε\* | vs band 1e-3 |
> |---|---|---|---|---|---|
> | C = 100 pF | 1.190127e-04 | 0.008788 | 0.036078 | ≈ 0 (r² = −1.605e-05) | 0.119×, UNDER |
> | L = 1 µH | 9.581734e-07 | 0.001908 | 0.035507 | 1.331180e-04 | 0.00096×, UNDER |
>
> (`:3825–3827`; printed, never asserted — the width was fitted to these.)
>
> **Reading.** The negative-result table selects "both under ⇒ record".
> The (1 + mean ε\*(64)) width undoes κ at 64 MHz on the gate mesh by a larger
> factor than at 10 MHz. L's residual lands 139× below its own fit's floor and
> C's ≈ 4× below what a zero at 2c's ε\*(C) would give (slot arithmetic,
> k = √a). So both true zero-crossings sit nearer the common mean than the
> three-point fits placed them. 2c's 7 % C/L split is within those fits'
> resolution (~3e-4 in ε\*), not evidence of element-dependent physics.
> **Not changed:** no record, no band, no `src/`, no `Z_p` correction. The
> row stays 🟡 and `PORT-15` gate (i) stays closed. Whether a κ-derived (not
> fitted) width becomes a registered route is the weekly's; 128 MHz would be
> its out-of-sample point.
>
> **Ruled 2026-09-12 18:00 review — step 2e accepted; the step-2 family is
> frozen under the four-attempt rule and its question is closed as
> measured.** Re-read `20260912T183330Z_PORT-14-step2e.log:3825–3827` (D
> residuals 1.190127e-04 / 9.581734e-07) and `:1886, :1893` (the in-window
> ε = 0 reproduction). Step 2 has now run five attempts (2, 2b, 2c, 2d, 2e)
> and none registered a record or moved a band, so under §9's family cap (the
> operator directive of 2026-09-12, enacted by this review) no 2f is queued.
> The banked reading: at 64 MHz on the gate mesh, κ is the terminal form's
> Cauchy–Schwarz deficit to 0.3 % (2d) and a (1 + κ)-corrected width takes
> both lossless residuals under 1e-3 (2e). What would move the row from 🟡
> is a **registered** 64 MHz route — a κ-*derived* width, not a fitted one,
> with 128 MHz as its out-of-sample point — and that is the 2026-09-13
> weekly's to specify as a numbered step 3, not a sixth letter under step 2.
>
> **Step 3 scoped 2026-09-13 (weekly review) — the κ-derived width route,
> registered at 64 MHz, out-of-sample at 128 MHz.** One additive opt-in on
> the sheet law scaling the told width by `(1 + κ)` with κ computed in-run
> from the ε = 0 solve's `C/terminal − 1` (`PORT-16`'s `_exact_shares`),
> never fitted; asserted: κ(64) reproduces 2d's 1.0641e-2 at rtol 1e-3, both
> 64 MHz lossless residuals ≤ `REDUCTION_BAND` 1e-3 on the gate mesh, the
> uncorrected 10 MHz floor record unmoved; negative control by record the
> uncorrected 64 MHz miss (1.354202e-02); the corrected 10 MHz pair and the
> 128 MHz pair with in-run κ(128) printed and *predicted* under, never
> asserted. Moves the row 🟡 → ✅ with κ carried as the sheet's named
> systematic. Full item in §10 (the three frozen families).
>
> **Step 3 executed 2026-09-13 12:00 slot — 🚫 incomplete on a
> mis-registered anchor; code parked on
> `attempt/PORT-14-step3-20260913T172330Z` (`86c93f6`).** (0) lifted
> `C/terminal − 1` = test helper bitwise; (ii) corrected 64 MHz lossless
> residuals **5.359129e-05 / 1.998404e-06** ≤ 1e-3; (iii) the 10 MHz floor
> reproduces unmoved; negative control green; printed κ(128)
> 1.064828193e-02 with corrected 4.013e-05 / 5.599e-06 under 1e-3. **(i)
> red:** derived κ(64) 1.060762155e-02 vs "2d's 1.0641e-2" misses by
> 3.119e-03 — but 1.0641e-2 is 2b's *pooled fit*; 2d's `C/terminal − 1` is
> 1.060762e-02 on P1 (reproduced to 1.457e-07), and the step-2d text above
> already records the 0.99688–0.99714× gap. The comparand, not the route,
> is wrong. **Sign:** 2e's fitted ×0.989446732 is `1/(1 + κ)`, not
> `(1 + κ)`; the parked code implements `1/(1 + κ)`. Not loosened; a review
> re-registers (i). Logs `20260913T171434Z_PORT-14-step3-64mhz.log`
> (Status 1, 114 s), `…171649Z_…-10mhz.log` (197 s),
> `…172026Z_…-128mhz.log` (114 s), all `-n 2`.

## Ruling appended 2026-09-13 18:00 daily review — step 3 anchor (i) re-registered

The parked step-3 run (`attempt/PORT-14-step3-20260913T172330Z`, `86c93f6`) is
ruled correct in its route and wrong only in its comparand: anchor (i) named
step 2b's pooled fit 1.064081e-02, which the step-2d record above
(`:602–605`) already puts at 0.99688–0.99714× the `C/terminal − 1` the
derived κ actually computes. (i) is re-registered as *the in-run derived
κ(64) reproduces 2d's P1 `C/terminal − 1` record 1.060762e-02 at rtol 1e-3*
(`20260912T123236Z_PORT-14-step2d-64mhz.log:1942–1949`; the parked window
read 1.457e-07). The scoping text's "scale the told width by `(1 + κ)`" is
sign-inverted — 2e's fitted ×0.989446732 is `1/(1 + κ)`, which the parked
code implements; the §10 sentence is corrected, this history is not
rewritten. No band moved. Re-queued as §9 item 1 of the 18:00 review.
