# EX-19 — the lossy saline sphere at 64 and 128 MHz

The first example in this repository that **solves at the MRI Larmor
frequencies**. Everything else in the `th:` group runs where the physics is
easier: `EX-6` (`th:3`) sits at `k₀R = 5e-3`, deep in the quasi-static limit.
`TH-10` closed the Larmor-regime gates on 2026-08-13; this is that capability,
runnable.

## What this demonstrates

A 0.05 m gelled-saline sphere (`εᵣ = 78`, `σ = 0.5 S/m`) in a 0.2 m box, driven
on the wall by the exact full-wave series total field, solved at 64 MHz (1.5 T)
and 128 MHz (3 T). At these frequencies `σ/(ωε₀) = 140` dominates `εᵣ = 78`, so
`ε_c = 78 − j140` and `|m|k₀a = 0.850` (1.374 at 128 MHz): the quasi-static
interior field `3E₀/(ε_c+2)` is **not a correction away** from the truth — it is
off by 102.3% / 154.6% in max-norm (`TH-10` step 1). Three things are measured
in every run, all against the `LossySphereSeries` closed form:

1. **the interior field**, relative L2 over the probe cloud, at two mesh rungs
   per frequency — the level *and* its direction;
2. **the separation from quasi-statics** on the same solved field — the negative
   control, executed here, not cited;
3. **the SAR-relevant volume integral** `½∫σ|E|²` over the sphere, against the
   series field integrated over the same meshed cells with the same `σ`.

The fixture is *imported* from the module that closed `TH-10`
(`tests/validation/test_lossy_sphere_fullwave.py`) — geometry, materials, rung
ladders, probe cloud, series reference, power machinery and every bound. The
example and the gate cannot drift apart.

**Scope:** the interior field and the total ohmic power. No mass averaging, no
C95.3 wording, no SAR claim, nothing about a coil.

## How to run it

```bash
./run_examples.sh -e th:6 -n 2 -t 540
```

The `th:` group sources the complex DolfinX build automatically; a real build
raises immediately. Measured cost at `-n 2`: **24 s** of compute, 27 s wall
(`docs/testing/logs/20260813T200415Z_EX-19-example-n2.log`, exit 0) — five
solves, 5 866 → 55 251 cells, the 128 MHz fine rung dominating at 12.5 s.
Re-measured on the 0.11 image 2026-08-25: **55 s** wall for `th:5` + `th:6`
together, the 128 MHz fine rung 11.3 s at 55 241 cells
(`20260825T050232Z_EX-30-th-run-5to6.log`, exit 0).

## How to analyze it, step by step

### 1. Read the two field tables, coarse rung first

```
[64 MHz]  h = 0.01250 (  5866 cells): relL2 = 8.154%, separation =  8.42x
[64 MHz]  h = 0.00833 ( 17667 cells): relL2 = 3.643%, separation = 18.67x
[128 MHz] h = 0.00833 ( 17667 cells): relL2 = 3.302%, separation = 31.75x
[128 MHz] h = 0.00556 ( 55241 cells): relL2 = 1.769%, separation = 59.16x
```

*(Transcript from the DolfinX **0.11** image,
`20260825T050232Z_EX-30-th-run-5to6.log`. On 0.7.2 the same rungs meshed to
17 670 / 55 251 cells and the 128 MHz fine rung read 1.826% / 57.31× — the
record moved with its mesh at `OPS-18` step 3, and the four-digit motions in
the 64 MHz and coarse rows are that same ~5-ulp mesh tie-break.)*

The gate is the level (`< 5%`) **and** the direction (decreasing with `h`); the
example asserts both, at `TH-10`'s unmoved band. Note the cross-frequency
reading the run makes available for free: at the *same* 17 667-cell mesh,
128 MHz (3.302%) is more accurate than 64 MHz (3.643%). Whatever sets the ~3%
floor here, it is not interior-wavelength resolution — that refutation is
`GEO-14`'s question, and this example reproduces the measurement it rests on.

### 2. Check the separation column — that is the negative control

`relL2(FEM vs quasi-static)` is 68.0% at 64 MHz and 104.7% at 128 MHz, so the
solve sits 18.67× / 59.16× closer to the full-wave series than to the
quasi-static closed form, against a `> 10×` floor. A solver that had merely
reproduced `EX-6`'s physics at a higher frequency fails this by construction.

### 3. Read the power block, and the miss beside it

```
P_FEM = 1.105143e-07 W vs P_series(meshed) = 1.066439e-07 W  =>  3.629%  (band 5%)
P_quasistatic = 4.464134e-08 W                               =>  miss 58.140% (floor 50%)
```

The field gate does not imply this one: SAR is a *volume* functional of `|E|²`,
and squaring turns a signed field error into a one-signed power error. The
reference differs from `P_FEM` in `E` alone — same cells, same `σ`. The
geometry question is carried separately and printed, never folded into the band:
the meshed sphere holds 0.985949 of the exact-ball series power, computed in
numpy by Gauss product quadrature independently of dolfinx.

### 4. Confirm the run reproduced the gate, digit for digit

Every anchor is asserted against the `TH-10` record inside a **1%** reproduction
band, and the run prints the drift:

| quantity | record | this run's drift |
|---|---|---|
| 64 MHz fine relL2 | 3.643% | 4.04e-05 |
| 64 MHz separation | 18.68× | 2.96e-04 |
| 128 MHz fine relL2 | 1.769% *(0.11; 1.826% on 0.7.2)* | 2.02e-04 |
| 128 MHz separation | 59.16× *(0.11; 57.31× on 0.7.2)* | 5.45e-05 |
| 64 MHz ohmic power | 3.629% | inside band |
| 64 MHz quasi-static power miss | 58.1% | inside band |

*(Drifts measured on the 0.11 image, `20260825T050232Z_EX-30-th-run-5to6.log`.)*

Records: `20260813T093212Z_TH-10-step2-64mhz.log`,
`20260813T123211Z_TH-10-step3-128mhz.log`,
`20260813T170337Z_TH-10-step4-power-n2.log`. A run outside the band is a
regression finding about the solver or the fixture, not a tolerance question.

### 5. Open the fields

```
examples/time_harmonic/paraview_output/time_harmonic_06_larmor_sphere_64MHz_combined.xdmf
examples/time_harmonic/paraview_output/time_harmonic_06_larmor_sphere_128MHz_combined.xdmf
```

Colour by `E_magnitude`; `Threshold` on `CellTags` (1 = sphere, 2 = surrounding
box) isolates the saline. Unlike `EX-6`'s uniform interior, this one carries
structure, and the 128 MHz file carries more of it — `|m|k₀a` grows from 0.850
to 1.374, so the interior wavelength approaches the sphere diameter. `Glyph` on
`E_real` in a `y = 0` clip shows the interior field is no longer a single
direction times a constant, which is precisely why the quasi-static formula
misses by 100%+.

**The picture is qualitative; the numbers are not.** XDMF cannot carry N1curl,
so the export interpolates the solved field into Lagrange P1 — and `POST-4`
step 4 measured that interpolant disagreeing with the solved field at
O(20–52%) inside the cell (see `docs/testing/known-issues.md`). Every asserted
quantity above is read from the solved N1curl field, never from the exported
one.
