# ANS-2 step 1 — coil-driven SAR in the loaded four-leg birdcage at 10 MHz

Guide to `02_birdcage_coil_driven_sar_10MHz.py`, the **runnable half** of the
fourth commissioned Ansys Electronics Desktop benchmark (PROJECT_PLAN §5.4,
§7 `ANS-2`). `SPEC.md` beside this file is the authority for the
boundary-value problem the human operator replicates in AED; this script
produces *our* half of it and nothing else.

## 1. What this demonstrates

Every coil-driven SAR number this repository holds is a **C4 symmetry
identity** — four quadrant values agreeing to a fraction of a percent. A SAR
computation wrong by a *constant factor* (a density, a factor of two in the
time-average, a normalisation) passes that identity exactly. The only absolute
check on record is `MAT-4` step 1 against the lossy-sphere closed form on an
**imposed uniform field** — never on a coil. This case is the first thing that
can attack the absolute claim.

## Scope — SPEC export rows 1–3, 7 and 8 only

| Row | Quantity | Here? |
|---|---|---|
| 1 | Pointwise SAR `σ\|E\|²/(2ρ)` at four named points | ✅ |
| 2 | Whole-phantom dissipated power `½∫σ\|E\|² dV` | ✅ |
| 3 | Whole-phantom average SAR | ✅ |
| 4–6 | 1 g / 10 g mass-averaged SAR, peak over phantom | **held for step 2** |
| 7 | Excitation metadata | ✅ |
| 8 | Solve metadata | ✅ |

Rows 1–3 are **shape-free**: no averaging volume enters them, so both codes
compute the same functional of the same field and a disagreement is a
disagreement about the physics or the normalisation. Rows 4–6 carry a
*pre-registered* systematic — our operator averages over a **sphere** of equal
mass, IEC 62704-1 (hence HFSS) over a **cube** — and the SPEC forbids reading a
rows-4–6 miss as a finding until rows 1–3 have agreed. Shipping the
adjudicating rows first is the whole point of the split.

## Normalisation — read this twice

Our drive is `V_src` = 1 V behind 50 Ω, i.e. `V_src²/(4Z₀)` = **5.0e-03 W**
incident. HFSS's default is **1 W**. SAR is quadratic in the field and
therefore *linear* in incident power.

The script prints and exports the incident, supplied and accepted power per
solve; it does **not** match HFSS's normalisation and does **not** rescale
anything silently. The ratio is carried explicitly and applied by the
adjudicating review. A silent normalisation mismatch is the single most likely
way this case produces a wrong "answer" that passes every self-check on both
sides.

## What is imported, and what is asserted

Nothing is re-implemented and no band or record is restated (`ANS-1`'s rule —
a benchmark cannot drift from the gate):

* the fixture is `MAT-4` step 4's own `_build_mass_averaged`, called at
  `PHANTOM_RESOLUTION_1G_RUNG` = 0.0025 m (`GEO-27`'s rung);
* the mis-paired 1 g control is `MAT-4` step 5b's own `_add_one_gram_control`;
* the ParaView bundle is `EX-34`'s `_paraview_fields`;
* `C4_COVARIANCE_BAND` (5 %), `EXACT_IDENTITY_RTOL` (1e-10), `CELL_COUNT_BAND`
  (1 %) and both cell records come from the gate modules.

Asserted, all of it against those imported bands:

| Anchor | Reading (2026-09-09 run) | Band |
|---|---|---|
| Four cyclic **10 g** C4 pairs | 0.0309 / 0.0060 / 0.0394 / 0.0644 % | 5 % |
| Four cyclic **1 g** C4 pairs | 0.0957 / 0.1199 / 0.1305 / 0.1065 % | 5 % |
| Whole-phantom coverage identity, power | 7.771561e-14 | 1e-10 |
| Whole-phantom coverage identity, mass | 5.284662e-14 | 1e-10 |
| Mesh, total / phantom | 199 920 / 58 866, ratio 1.000000 | 1 % |
| **Negative control** — mis-paired 1 g `(c_{k+2}; k)` | 87.0143 / 87.0546 / 87.0506 / 87.0592 % | asserted **≥ 10×** the 5 % band |

The negative control is what stops the C4 identity being vacuous: the
*far-side* ball under the same drive misses by ~87 % where the cyclic pair
misses by ~0.1 %, a separation of ≈ 17×. It is asserted as a **floor** (10× the
band) rather than against step 5b's measured 87.01–87.06 %, because an example
must never re-record a gate digit.

An imported anchor going red on a regenerated fixture means the example and the
gate have **diverged** — report both readings and open a known-issues row;
never widen a band here.

## 2. How to run it

```
./run_examples.sh -e ans:2 -n 4 -t 560
```

The `ans:` group sources the complex DolfinX build automatically; the script
raises in real mode. Measured 2026-09-09 at `mpiexec -n 4`:
**233 s** wall (`20260909T140558Z_ANS-2-step1.log`, `Status: 0`), of which
four drives at 18.15 / 17.59 / 17.06 / 17.41 s; the rest is the 199 920-cell
mesh, 21 mass-averaging integrals and the XDMF export. **Heavy** tier.

## 3. How to analyze it, step by step

Read the three outputs below in this order: the run's own stdout block (the
anchors and their imported bands), then `COMPARISON.md` (the SPEC's export
tables, our columns filled), then `metrics.json` if a figure needs more digits
or a field the tables do not carry. Open the XDMF last — it is context for the
terminal numbers, not evidence about them.

## Outputs

* `metrics.json` — rows 1–3, 7 and 8 in full, every anchor reading, and the
  imported band values, so the numbers a review reads are the numbers the run
  asserted on.
* `COMPARISON.md` — the SPEC's export tables, **our columns regenerated by the
  script** and the **AED columns verbatim blank** for the operator. If the
  operator's gitignored AED results file exists in `aed_results/`, the script
  additionally writes the gitignored `COMPARISON_private.md` with those columns
  filled; neither path is produced by this run and neither is tracked.
* `paraview_output/ans2_birdcage_coil_driven_sar_10mhz_combined.xdmf` — mesh,
  `CellTags` (1 = conductor, 3 = phantom), `E_real`/`E_imag`/`E_magnitude`
  (CG1) and `B_magnitude` (DG0) for the port-1 drive. Unlike `ANS-3`/`ANS-4`
  this costs **no extra solve**: the construction already holds all four
  phasors.

## Rank safety

`assemble_scalar` and local max/min are rank-local. Every number written into
`metrics.json` is MPI-reduced before it leaves the routine that produced it
(`mass_averaged_sar` and `mean_sar` reduce over `comm` internally); point
evaluation goes through `post.evaluation.evaluate_vector_field_parallel`, which
is collective and broadcasts, never `f.eval(points, arange(n))`.

## Privacy — a hard rule

AED numbers from this case **never enter a tracked file** (operator directive
2026-09-02; Ansys licence terms). They live in this directory's gitignored
`aed_results/` and `COMPARISON_private.md` and in `docs/private/`. Tracked
files, journals, dashboards and commit messages carry only the qualitative
verdict — agree / disagree / inconclusive.

## What this closes, and what it does not

It closes the **runnable half only**. `ANS-2` stays 🟡 pending SPEC rows 4–6
(step 2) and the operator's AED replication (step 3). It licenses **no**
absolute-SAR or compliance claim: PROJECT_PLAN §2's absolute-SAR clause does
not move, and nothing here says anything about 64 / 128 MHz, homogeneity, B₁⁺,
an implant, a thermal result, or a quadrature drive.
