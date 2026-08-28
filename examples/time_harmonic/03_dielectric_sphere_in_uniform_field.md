# `-e th:3` — a dielectric sphere in a uniform field: *solved*, not imposed

Guide for `examples/time_harmonic/03_dielectric_sphere_in_uniform_field.py`.
Written to be followed without the source open.

## 1. What this demonstrates

**A material setting a field, rather than being weighted by one.** This is the
distinction `EX-3` deliberately does not test: `EX-3` computes mass-averaged SAR
on a sphere whose field is **imposed** analytically, so the material never acts
on the field. Here the same kind of sphere sits in a solved time-harmonic
problem and `ε` *produces* the interior value — it comes out of the assembly,
not out of the input.

A sphere of radius `R` and relative permittivity `ε` in a uniform field `E₀ẑ`
polarises uniformly, and in the quasi-static limit (`k₀R = 5e-3` here) the
electrostatic solution is exact:

```
E_in  = 3/(ε + 2) · E₀ ẑ                                     (r < R)
E_out = E₀ ẑ + β E₀ R³ (3 (ẑ·r̂) r̂ − ẑ)/r³,  β = (ε−1)/(ε+2)   (r > R)
```

At **ε = 78** — water/saline, the phantom material this whole project is built
around — the interior field is **26.7× smaller** than the drive. The example
imposes `E_out` as Dirichlet data on the box wall (exact there, since the
exterior branch holds on any surface outside the sphere) and measures the
**interior**, which nothing in the boundary data states. `3/(ε+2)` is produced
by `ε` acting through the mass term `−k₀²ε_c E` and by the normal-`D` jump at
the sphere surface. That jump is what ParaView shows.

The fixture is *imported* from the module that closed `TH-8`
(`tests/validation/test_dielectric_sphere.py` — geometry, frequency, probe
cloud, and the exterior Dirichlet callable).

On record at `-n 2` (`20260810T003510Z_EX-6-gate.log`, 9 s harness-wall / 7.8 s
in-example, 2026-08-09 19:30 slot; identical to the `TH-8` finest-mesh record
`20260731T200457Z_TH-8-gate-final.log`):

| Quantity | Closed form | Measured | Bound |
| --- | --- | --- | --- |
| Interior `E_z` (probe average) | 0.037500 V/m | **0.038416** V/m | **2.443%** vs 5% |
| Interior `E_z` (volume integral) | — | **0.038411** V/m | **0.014%** from the probe average, vs 3% |
| Spread across the probe cloud | 0 (uniform) | **0.080%** | 1% |
| Transverse / `E_z` | 0 (z-directed) | **0.085%** | 1% |
| `|Im|/|Re|` | 0 (real data) | **0.0e+00** | 1e-6 |
| Tagged sphere volume | 4/3πR³ = 5.235988e-04 m³ | **5.206270e-04** m³ | **0.568%** (faceted ball under-fills) |
| Jump `E_out/E_in`, pole | 56.27× | **59.20×** | 10% |
| Jump `E_out/E_in`, equator | 11.83× | **11.46×** | 10% |
| Mesh | — | 39 693 cells | 7.3 s of solve |

The gate is `TH-8` (✅ 2026-07-31) and the 5% interior ceiling is the gate's own
(§10 MVP criterion) — **never tightened, never loosened**. This example closes
nothing; Phase-2 §5.4 backfill.

## 2. How to run it

```
./run_examples.sh -e th:3 -n 2 -t 180
```

**Complex build required** — the `th:` group sources it automatically, and a
real build raises. Tier: **standard**; 9 s harness-wall on record, 7.3 s of it
the single solve on 39 693 cells.

## 3. How to analyze it, step by step

**Step 1 — the interior field against `3/(ε+2)E₀`.** This is the anchor:

```
  interior E_z : 0.038416 V/m   (closed form 3/(eps+2)*E0 = 0.037500)
                 2.443%, ceiling 5%
```

The number to internalise is the **ratio**, not the volt-per-metre: the interior
is 26.7× below the drive because ε = 78 screens it. A solve that got the sphere
material wrong does not produce a slightly different number here, it produces
one off by an order of magnitude (step 4). 2.443% at the finest mesh is the
gate's own record, reproduced digit for digit.

**Step 2 — the three shape claims, which the single anchor cannot make.** The
closed-form interior field is uniform, purely `z`-directed, and real. So:

```
  spread over the probe cloud : 0.080%   (bound 1%)
  transverse / E_z            : 0.085%   (bound 1%)
  |Im| / |Re|                 : 0.0e+00  (bound 1e-6)
```

An average can land on the right value while the field underneath it is wrong;
these three say it did not. The `|Im|/|Re|` line is the cheapest of the three
and the most diagnostic: the problem is lossless and its data real, so a nonzero
imaginary part means a complex quantity entered where it should not have.

**Step 3 — the exported field is the asserted field, measured two independent
ways.** The interior average is re-measured as a **volume integral**
`∫_sphere E_z dx / ∫_sphere dx` over the tagged cells: **0.038411 V/m**,
**0.014%** from the probe average. The probe cloud samples two shells inside
`0.55R`; the integral samples the whole ball out to `r = R`. Their agreement is
therefore two things at once — evidence that ParaView is colouring the field the
anchor was read from, *and* independent evidence that the interior really is
uniform.

The tagged region is also confirmed to **be** the sphere: assembled volume
**5.206270e-04 m³** against `4/3πR³` = 5.235988e-04, **0.568%** low. A faceted
tetrahedral ball under-fills its smooth counterpart, so a small negative bias is
the correct reading here; a *positive* excess or a percent-level miss would mean
the cell tags are not the sphere.

**Step 4 — the negative control, cited rather than recomputed.** Drop the sphere
from the `material_map` under the *same* Dirichlet data and the interior lands
at `E_z = 0.918143` V/m — **2348%** off the closed form, a factor **23.9 above**
this run's error. That is the check that matters most for a Dirichlet-driven
problem: it proves the gate cannot pass by reading back its own boundary data.
The example prints the separation and asserts that the cited control and this
run's error still straddle 100%; it does not re-run the ε-blind solve.

**Step 5 — the interface jump, which is a number and not just a picture.** The
exterior field is probed just outside the pole and the equator:

```
  pole    : E_out/E_in = 59.20x   (closed form 56.27x)
  equator : E_out/E_in = 11.46x   (closed form 11.83x)
```

The two together are the dipole lobe: the field is enhanced over the pole and
reduced at the equator, and the sign reversal between them is the dipole
pattern in one pair of numbers. **These two probes are held to 10%, not 5%, and
that bound was set from measurement rather than inherited** — they sit at
r = 1.2 R in the *far* mesh (h_far = 0.0125 m = 0.25 R, twice the sphere's h and
unrefined by the fixture) where the dipole falls as 1/r³, and they read 7.782%
(pole) / 0.756% (equator) against their closed form. `TH-8` gates the interior
only, so no gated bound existed to inherit. The interior anchor was **not**
touched — it stands at the gate's own 5%.

**Step 6 — open it in ParaView.**
`File → Open → examples/time_harmonic/paraview_output/time_harmonic_03_dielectric_sphere_combined.xdmf`,
then colour by `E_magnitude`.

1. **What to look at first:** a dark ball inside a bright box. That contrast
   *is* `3/(ε+2)` — the 26.7× of step 1, made visible.
2. **Threshold** on `CellTags` (1 = sphere, 2 = air) to isolate either region.
   Thresholding to the sphere and checking the range is the visual form of
   step 3's volume integral.
3. **Glyph** on `E_real` in a clip through `y = 0`: the dipole pattern outside —
   arrows converging over the poles, reversed at the equator — and a uniform,
   `z`-directed field inside. The abruptness at the surface is the normal-`D`
   jump; step 5 is the same fact as two numbers.

**Step 7 — what a deviation means.** Interior field near the drive value (~1
V/m) rather than 26.7× below → the material map is not reaching the assembly at
all; compare against the 0.918143 control of step 4, which is that exact
failure. Interior value right but spread or transverse ratio percent-level →
mesh resolution at the sphere surface, or a probe cloud that has drifted outside
`0.55R`. Nonzero `|Im|/|Re|` → a complex quantity in a lossless problem, look at
the material map before the solver. Volume integral and probe average
disagreeing by more than 3% → the cell tags and the probe cloud are describing
different regions, and neither number should be trusted. Any of these is a
regression finding against `TH-8`: report and stop, do not move the 5%.

## Related

- The gate this example runs: `tests/validation/test_dielectric_sphere.py`
  (`TH-8`), and PROJECT_PLAN.md §7 for its record.
- The same material as an **imposed** field instead of a solved one — the
  contrast this example exists to draw: `examples/mri/02_mass_averaged_sar.py`
  (`mri:2`, `EX-3`).
- The same lossy-medium physics on a plane wave:
  `examples/time_harmonic/01_lossy_plane_wave.py` (`th:1`).
