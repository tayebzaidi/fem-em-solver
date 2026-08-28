# `-e th:4` — a waveguide below cutoff: decay set by geometry, not by loss

Guide for `examples/time_harmonic/04_evanescent_waveguide_decay.py`. Written to
be followed without the source open.

## 1. What this demonstrates

**A field dying in a medium that absorbs nothing.** This is the counterpart to
`th:1`: there, the wave decays because `Im ε_c` acts through the mass term. Here
`σ = 0`, `εᵣ = μᵣ = 1` — nothing in the problem dissipates anything — and the
field still falls off exponentially, purely because the guide is too narrow for
the frequency. The decay is transverse geometry acting through the operator's
**real** part.

In an `a × b` PEC guide the TE₁₀ mode has transverse profile `sin(πx/a)` and
cutoff wavenumber `k_c = π/a` (cutoff `f_c = c/2a = 2.998 GHz` at `a = 0.05 m`).
Driven *below* cutoff the axial dependence is a real exponential rather than a
travelling wave:

```
E(x, y, z) = ŷ · sin(πx/a) · e^{−γz},    γ = √(k_c² − k₀²)   [Np/m]
```

At 2.4 GHz that is `γ = 37.652670 Np/m`, so the amplitude falls **6.6×** over
the `L = a` guide.

Why the number is a measurement and not a restatement: the exact field is
imposed on the whole boundary — which pins both end faces — and the **slope in
between** is fitted. That slope is `k₀²` reaching the mass term. A solver that
dropped `k₀²ε` entirely would still decay, and would still look completely
plausible, but at `γ = k_c = 62.83`, **67% too fast, at every frequency**. That
is the failure this example is shaped to catch.

The fixture is *imported* from the module that closed `TH-7`
(`tests/validation/test_waveguide_cutoff.py` — geometry, frequency, the
exact-field factory, the probe line and its fit window).

On record at `-n 2` (`20260810T020355Z_EX-7-gate.log`, 7 s harness-wall / 5.1 s
in-example, 2026-08-09 21:00 slot; identical to the `TH-7` finer-mesh record
`20260731T123411Z_TH-7-gate-final.log`):

| Quantity | Closed form | Measured | Bound |
| --- | --- | --- | --- |
| Decay constant γ | 37.652670 Np/m | **37.650399** Np/m | **0.006%** vs 5% |
| Whole-domain rel. L2 | — | **4.406648e-02** | 5% |
| Residual `|Im E_y|/|Re E_y|` | 0 | **0.000e+00** | 1e-10 |
| γ refitted from the *exported* CG1 array | — | **37.606274** Np/m | **0.117%** vs 0.5% |
| Transverse profile RMS vs `sin(πx/a)` | 0 | **0.200%** | 2% |
| γ vs `k_c` | γ < k_c | **1.67× below** | asserted |
| Exported `|E|` span | — | 5.147567e-17 … 1.000725e+00 V/m | — |
| Mesh | — | 41 472 cells | 5.1 s in-example |

The gate is `TH-7` (✅ 2026-07-31) and the 5% ceiling is the gate's own (§10 MVP
criterion) — never tightened, never loosened. **Scope note the §9 item made
explicit:** `TH-7` gates the **evanescent TE₁₀ decay below cutoff**, and no line
impedance or S-parameter claim is made or implied here. `PORT-1` owns that, and
per PROJECT_PLAN §2 the package's S-parameters are still a heuristic. This
example closes nothing; Phase-2 §5.4 backfill.

## 2. How to run it

```
./run_examples.sh -e th:4 -n 2 -t 180
```

**Complex build required** — the `th:` group sources it automatically, and a
real build raises. Tier: **standard**; 7 s harness-wall / 5.1 s in-example on
record for the single 41 472-cell solve.

## 3. How to analyze it, step by step

**Step 1 — γ against `√(k_c² − k₀²)`.** This is the anchor:

```
  gamma : 37.650399 Np/m   (closed form 37.652670)   0.006%, ceiling 5%
```

Four-digit agreement. Note how much margin there is: the bound is 5% and the
measurement is 0.006%, nearly three orders inside it. That is not slack to be
spent — it is the reason a *drift* of even 1% here would be a real finding long
before the assertion fired.

**Step 2 — the two shape claims.** The anchor is a slope through one line of
probes; these two say the rest of the field is right as well:

```
  whole-domain rel L2      : 4.406648e-02   (bound 5%)
  |Im E_y| / |Re E_y|      : 0.000e+00      (bound 1e-10)
```

The imaginary-part check is the sharp one. Lossless material and real boundary
data give a real operator and a real right-hand side, so the phasor must be real
to round-off. An exactly-zero imaginary part is what a correctly assembled real
problem produces in a complex build; anything else means a complex quantity
entered where none belongs.

**Step 3 — γ sits strictly below `k_c`, which is the in-run half of the negative
control.** `k_c = 62.83` and the measured γ is **1.67× below** it. A `k₀`-blind
solver — one that dropped the `k₀²ε` mass term — returns `γ ≡ k_c` exactly, at
any mesh and any frequency. This assertion is therefore not a sanity check but
the discriminator: it cannot be satisfied by a solver with that defect no matter
how fine the mesh.

**Step 4 — the cited half of the negative control.** The gate swept three
below-cutoff frequencies on one mesh and measured a **γ ratio of 2.6373** across
the band against the closed form's 2.6383 (**0.038%**), asserted `> 2.0`. The
`k₀`-blind solver of step 3 gives a ratio of exactly **1** — its γ does not
respond to frequency at all. This example prints the separation and does not
re-run the sweep.

**Step 5 — the exported field is the asserted field, and the mode profile is a
number.** Two checks, both on the CG1 array actually written to XDMF, and
**both bounds were set from measurement rather than inherited** (`TH-7` gates
neither):

```
  gamma refitted from the CG1 export : 37.606274 Np/m  (0.117% from the N1curl fit, bound 0.5%)
  profile RMS vs sin(pi x/a)         : 0.200%          (bound 2%)
```

The first says ParaView is colouring the mode the anchor was measured on. The
second says the TE₁₀ half-arch is genuinely in the exported array — 25 points
across the guide at mid-length, peak-normalised, 0.200% RMS from the closed-form
profile. Each constant carries its measurement and the reason for its margin in
the source. The anchor itself was **not** touched; it stands at the gate's 5%.

The exported `|E|` spans **5.147567e-17 … 1.000725e+00** V/m, so the PEC
side-wall zero is visible in the array, not merely in the formulation.

**Step 6 — open it in ParaView.**
`File → Open → examples/time_harmonic/paraview_output/time_harmonic_04_evanescent_waveguide_combined.xdmf`,
then colour by `E_magnitude`.

1. **What to look at first:** the bright end is the drive face at `z = 0`, and
   the field fades along `+z`. That fade *is* `e^{−γz}` — 6.6× over the guide.
2. **Plot Over Line** along `z`, log scale on the y-axis: the straight line
   whose slope step 1 fitted. Curvature in that line means the fit window is
   picking up the pinned end faces rather than the interior.
3. **Plot Over Line** along `x` at fixed `z`: the `sin(πx/a)` half-arch, pinned
   to zero on both PEC side walls. This is step 5's 0.200% RMS as a picture.

**Step 7 — what a deviation means.** γ near 62.8 rather than 37.65 → the `k₀²ε`
mass term is missing; that is step 3's failure and it is the single most likely
defect this example exists to find. γ right but the whole-domain L2 above 5% →
the transverse profile, not the axial decay; look at step 6's second plot.
Nonzero `|Im E_y|/|Re E_y|` → a complex quantity in a lossless real problem.
The CG1 refit drifting past 0.5% from the N1curl fit → the export path, not the
solve; the anchor is still good but the picture no longer represents it. Any of
these is a regression finding against `TH-7`: report and stop, do not raise a
bound.

## Related

- The gate this example runs: `tests/validation/test_waveguide_cutoff.py`
  (`TH-7`), and PROJECT_PLAN.md §7 for its record.
- The same exponential decay caused by **absorption** instead of geometry — the
  contrast this example is built to draw:
  `examples/time_harmonic/01_lossy_plane_wave.py` (`th:1`).
- The eigenfrequencies of a closed PEC box, the same `k_c` physics with no
  drive: `examples/time_harmonic/02_pec_cavity_resonances.py` (`th:2`).
