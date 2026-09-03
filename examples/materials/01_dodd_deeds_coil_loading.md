# `-e mat:1` — coil loading by a conductive half-space: ΔR against Dodd–Deeds

Guide for `examples/materials/01_dodd_deeds_coil_loading.py`.
Written to be followed without the source open.

## 1. What this demonstrates

**The only loaded-coil number this project has ever gated.** Every other
example either imposes its field (`mri:2`) or solves a problem in which no
conductor reacts back on the source. Here a 1-turn loop is driven above a
conducting half-space, the half-space carries eddy currents, and those currents
change the *coil's own terminal impedance*. That change is what an MRI RF
engineer means by "loading".

The measured quantity is the **impedance change**, loaded minus free:

```
ΔZ = R_loaded − R_free + j(X_loaded − X_free)
```

extracted from the reaction integral `ΔZ = −(1/I′²) ∫ (E_loaded − E_free)·J′ dV`
over the whole domain, with `J′` the projected drive (real, and supported
everywhere, which is why the integral is over `dx` and not over the wire). The
closed form is Dodd–Deeds — the standard eddy-current solution for a circular
coil over a layered conductor — evaluated at run time from
`src/fem_em_solver/utils/dodd_deeds.py`, never transcribed.

The fixture is `MAT-6`'s: `a = 50` mm loop, wire radius 2 mm, liftoff
`h = 20` mm, half-space `σ = 100` S/m at `f = 10` MHz, box half-width
`W = 0.15` m. At those numbers the skin depth is `δ = 1/√(πfμ₀σ)` ≈ **1.59 mm**
≈ **0.032 a** — the loss lives in a thin surface layer, and the whole difficulty
of the case is resolving it.

Every constant, the mesh, the azimuthal drive and the solve itself are
**imported** from the modules that closed `MAT-6` steps 2b/3
(`tests/validation/test_dodd_deeds_impedance.py`,
`tests/validation/test_dodd_deeds_projected_drive.py`), so the example and the
landed gate cannot drift apart.

**10 MHz, eddy-current regime — no Larmor claim.** PROJECT_PLAN §2.1 is explicit
that the saline/Larmor case is an extrapolation, not a result. This example
inherits that boundary exactly: it is a quantitative statement about a
conductive half-space at 10 MHz and about nothing else. The example's own report
text says so on screen.

On record at `-n 2` (`20260809T110326Z_EX-11-gate.log`, exit 0, 74 s
harness-wall / 70.8 s example-internal, 2026-08-09 06:00 slot; every figure
byte-matching the `MAT-6` step-3 gate record):

| Quantity | Closed form (filament) | Closed form (finite wire) | Measured | Bound |
| --- | --- | --- | --- | --- |
| ΔR | +3.2259615e-01 Ω | +3.2296790e-01 Ω (+0.115237%) | **+3.2770406e-01** Ω | **1.5838%** vs filament (2%); 1.4669% vs finite wire, *not gated* |
| ΔX | −6.1586749e-01 Ω | −6.1675934e-01 Ω (+0.144814%) | **−5.6657895e-01** Ω | ratio **0.9200** vs filament, *not gated* |
| Sign of ΔR | > 0 (a conductor dissipates) | — | **+** | asserted |
| Sign of ΔX | < 0 (induced currents expel flux) | — | **−** | asserted |
| Finite-wire correction, r_wire = 0 | equals filament exactly | — | **1.785e-16** rel. diff | `< 1e-12`, asserted (negative control) |
| Drive current `I′` | 1.0 A nominal | **0.919666** A | reported |
| Ohmic power in slab, from the field | — | **1.385836e-01** W | — |
| Same, as ½ΔR·I′² from the reaction integral | — | **1.385836e-01** W | ratio **1.0000**, reported |
| Ohmic power, σ = 0 control | 0 exactly | **0.0** W | `== 0.0`, no tolerance |
| max \|J\|, σ = 0 control | 0 exactly | **0.0** A/m² | `== 0.0`, no tolerance |
| max \|J\|, loaded | — | **6.8396e+02** A/m² | — |
| Mesh | — | 138 619 cells, 10.8 s | solves 29.4 s + 26.9 s |

The gate is `MAT-6` step 3 (✅ 2026-07-31, step 3 record 2026-08-04). Its own
ceiling on ΔR is **5%**; the example gates at **2%**, which is what this fixture
actually delivers. That is tighter than the gate and **is not a knob** — a run
outside 2% is a regression finding, not a tolerance question.

**`EX-42`, from `MAT-8`: the finite-wire correction *raises* the closed form,
it does not absorb the FEM discrepancy.** The filament form used above ignores
the wire's own cross-section; `utils/dodd_deeds.coil_impedance_change_finite_wire`
adds that back at this fixture's `r_wire = 2.5` mm and shifts both ΔR and ΔX
**up** in magnitude by +0.115237% / +0.144814% — moving the closed form *toward*
the FEM measurement on ΔR (from 1.5838% away down to 1.4669%), which is
reported here but not gated: `MAT-6` still stays at 1.5834% against the
filament form until step 11.

This example closes nothing; Phase-3 §5.4 backfill.

## 2. How to run it

```
./run_examples.sh -e mat:1 -n 2 -t 180
```

**Complex build required** — the `mat:` group sources it automatically, and a
real build raises with a message naming
`/usr/local/bin/dolfinx-complex-mode`. Tier: **standard**; 74 s harness-wall on
record, of which 10.8 s is meshing and 56.3 s is the two solves. This is the
most expensive example in the tree, and the cost is the 138 619-cell graded mesh
that resolves a 1.59 mm skin depth under a 50 mm loop.

## 3. How to analyze it, step by step

**Step 1 — ΔR against the closed form. This is the anchor.**

```
  [ΔZ]    FEM   = +3.2770406e-01 + j(-5.6657895e-01) Ω
  [ΔZ]    exact = +3.2259615e-01 + j(-6.1586749e-01) Ω
  [ΔR]    relative error 1.5834% against the 2% ceiling
```

Read the **ΔR** column and ignore ΔX for the moment. 1.5834% is the `MAT-6`
step-3 record reproduced through the example path, digit for digit; the example
and the gate are the same computation, which is the point of importing rather
than restating. A number that has moved at this fixture means the gate has
regressed — report it, do not adjust the 2%.

**Step 2 — the two signs, which the single anchor cannot make.** A conductor
must *dissipate* and must *expel flux*:

```
  ΔR > 0     asserted
  ΔX < 0     asserted
```

These cost nothing and catch the class of error a percentage cannot: a
sign-flipped reaction integral or a swapped loaded/free pair can land near the
right magnitude while describing a physically impossible material.

**Step 3 — ΔX, which is printed and deliberately not gated.**

```
  [ΔX]    ratio 0.9200 — reported, never gated
```

The reactive part is **8% low against Dodd–Deeds and that is not a defect in the
solver**: ΔX is not converged in box size on this fixture — `MAT-6` step 4
measured 5.57% still moving between `W = 0.15` and `W = 0.20`, because the
reactive term samples the field far from the loop where a finite PEC box
truncates it. ΔR converges much faster because dissipation is local to the skin
layer. Do not quote the 0.9200 as a physics result, and do not "fix" it by
tightening the mesh; the fix is a bigger box, which costs more than the gate is
worth. This is exactly the row `ANS-1` commissions an Ansys number for.

**Step 4 — the independent energy identity.** Dissipated power can be computed
two ways that share no arithmetic:

```
  [control] ½ ΔR I'² = 1.385836e-01 W from the reaction integral
            vs        1.385836e-01 W from the field  [ratio 1.0000]
```

The right-hand number is `∫_slab (σ/2)|E|² dV` assembled from the **solved
field**; the left-hand one comes from the reaction integral ΔZ was extracted
from. They are analytically equivalent, so the agreement is a cross-check on the
extraction path, not new physics — which is why it is reported and not gated. A
ratio away from 1.0000 would mean the reaction integral and the Poynting-side
integral disagree about where the power went.

**Step 5 — the negative control, in-fixture and free.** The σ = 0 solve is the
other half of the same pair, so it shares the mesh, the drive, the solver and
every constant:

```
  [control] ohmic power in the slab: loaded 1.385836e-01 W, free 0.000000e+00 W
  [paraview] max |J| = 6.8396e+02 A/m² loaded, 0.000000e+00 A/m² in the control
```

Both control values are asserted `== 0.0` with **no tolerance**. That is
deliberate and not sloppiness: with σ identically zero cell by cell the
integrand is zero cell by cell, so anything but exactly `0.0` means the σ field
is not what the example thinks it is. Total separation, no bound to argue about.

**Step 6 — the drive current, which is not 1.0 A.**

```
  [drive] I' = 0.919666 A against the nominal 1.0 A
```

The drive is *projected* — a CG1 Poisson projection of the azimuthal current
density onto the discrete divergence-free space — and the projection does not
conserve the nominal amplitude exactly on this mesh. That is why ΔZ is
normalised by the **measured** `I′` and not by 1.0 A: normalising by the nominal
value would put an 8% error straight into ΔR. If this number drifts far from
0.92 at the same mesh, suspect the drive or the wire tagging before the solver.

**Step 7 — open it in ParaView.**
`File → Open → examples/materials/paraview_output/materials_01_dodd_deeds_coil_loading_combined.xdmf`,
then colour by `J_magnitude` (A/m²).

1. **Threshold** on `CellTags` — `3` is the lossy slab, `1` is the wire. Keep
   only tag 3 first; that isolates where the loss lives.
2. **What to look at:** an annular bright band on the slab's top surface,
   directly under the loop, decaying downward. The decay length is the printed
   skin depth δ ≈ 1.59 mm; the band's *radius* tracks the loop radius, 50 mm.
   That picture is the physical content of ΔR — the coil is loaded because
   current is flowing there.
3. **Clip** through `y = 0` and colour by `J_magnitude` on a log scale to see
   the exponential fall-off with depth. Peak magnitude should agree with the
   printed `max |J| = 6.84e+02` A/m²; the array ParaView reads is the array the
   run checked, not a separately written one.

**Step 8 — what a deviation means.** ΔR outside 2% at this fixture → a
regression against `MAT-6` step 3; report both numbers and stop, do not move the
ceiling. ΔR near **zero** → the slab's σ is not reaching the assembly; compare
against the σ = 0 control of step 5, which is that exact failure. ΔR *negative*
→ the loaded and free solves are swapped, or the reaction integral's sign
convention has been changed. Energy ratio away from 1.0000 → the extraction path
and the field disagree; trust neither ΔR nor the picture. Control power or
control `max |J|` not exactly `0.0` → the σ field is not identically zero
outside the slab, and every number above is suspect. `max |J|` far from 6.84e+02
with ΔR intact → the mesh under the loop has changed and the skin layer is
under-resolved even though the integrated quantity survived.

## Related

- The gates this example runs: `tests/validation/test_dodd_deeds_impedance.py`
  and `tests/validation/test_dodd_deeds_projected_drive.py` (`MAT-6` steps
  2b/3), and PROJECT_PLAN.md §7 for their records.
- The same compute path published as an Ansys benchmark, with `SPEC.md` for the
  operator to replicate:
  `examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/01_loop_over_lossy_slab_10MHz.py`
  (`ans:1`, `ANS-1`).
- The lossy-medium time-harmonic formulation this rests on, as a plane wave:
  `examples/time_harmonic/01_lossy_plane_wave.py` (`th:1`, `TH-6`).
- Why the saline/Larmor case is **not** claimed here: PROJECT_PLAN.md §2.1.
