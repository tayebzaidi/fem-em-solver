# `-e th:1` — a solved lossy plane wave: decay and phase vs the closed form

Guide for `examples/time_harmonic/01_lossy_plane_wave.py`. Written to be
followed without the source open.

## 1. What this demonstrates

**The first time-harmonic solve anywhere under `examples/`** — everything older
is magnetostatic, a mesh fixture, or an ungated demo. The complex curl-curl
solver that `TH-1`/`TH-6` closed on 2026-07-31 had no runnable demonstration
until this one.

In the `e^{+jωt}` convention, a wave travelling in `+x` and polarised along `z`
in a homogeneous lossy medium is `E = ẑ exp(−j k x)` with `k = k₀√(ε_c)`,
`ε_c = εᵣ − jσ/(ωε₀)`, on the branch with `Im k < 0`. Writing `k = β − jα`, the
amplitude falls as `e^{−αx}` and the phase advances as `−βx`. Material here is
the phantom: **σ = 0.7 S/m, εᵣ = 78, at 127.74 MHz** (the 3 T Larmor line).

What makes it a measurement rather than a rendering: the analytic field is
imposed as Dirichlet data on the **whole** boundary of the box, and the two
constants are fitted from the **interior**. Nothing in the boundary data tells
the interior how fast to decay — α and β are the solver's own output. The
constants, the fixture and the solve are *imported* from the module that closed
`TH-6` (`tests/validation/test_lossy_plane_wave.py`), so the example and the
gate run one computation, not two copies of it.

On record at `-n 2` (`20260809T140510Z_EX-4-gate.log`, 2026-08-09; every figure
byte-matching the gate log `20260731T020427Z_TH-6-gate3.log`):

| Quantity | Closed form | Measured | Bound |
| --- | --- | --- | --- |
| Decay constant α | 13.067043 Np/m | **13.069460** Np/m | **0.0185%** vs 1% |
| Phase constant β | 27.015150 rad/m | **27.031165** rad/m | **0.0593%** vs 1% |
| Sign of α | > 0 | holds | asserted (convention trap) |
| Rel. L2, coarse 12³ (10 368 cells) | — | 7.217852e-02 | — |
| Rel. L2, fine 24³ (82 944 cells) | — | 3.609441e-02 | — |
| Measured L2 rate in `h` | 1.0 (N1curl deg 1) | **0.9998** | asserted O(h) |
| Exported `|E|` span | — | 2.707108e-01 … 1.001903e+00 V/m | — |
| Amplitude drop across the box | `e^{αL}` = 3.694× | **3.701×** | — |

Skin depth δ = 76.53 mm, so `αL = 1.307` and `βL = 2.702` across the box —
about one skin depth and a little over half a wavelength, which is why both
constants are visible in one picture.

The gate is `TH-6` (✅ 2026-07-31). This example closes nothing; it is Phase-2
§5.4 backfill. Its 1% ceiling is the §7 `EX-4` plan's and is **tighter** than
the gate's own 5% (§10 MVP criterion) — it is what the fixture actually
delivers, and a miss is a regression finding, not a tolerance question.

## 2. How to run it

```
./run_examples.sh -e th:1 -n 2 -t 180
```

**Complex build required** — the runner sources
`/usr/local/bin/dolfinx-complex-mode` for the `th:` group automatically and the
log line reads `(complex build)`. A real build raises rather than producing a
wrong number. Tier: **standard**. 16 s harness-wall / 14.8 s example-internal at
`-n 2` on record, dominated by the two solves (12³ and 24³). Exit status 0 with
every assertion holding, or the run fails loudly.

The refinement pair is the point: a single mesh can match a closed form by
coincidence, and the O(h) rate is what rules that out. Do not drop the coarse
solve to save 4 s.

## 3. How to analyze it, step by step

**Step 1 — the two constants against their closed forms.** This is the anchor,
and it is the first block printed:

```
  alpha : 13.069460 Np/m   (closed form 13.067043)  0.0185% against the 1% ceiling
  beta  : 27.031165 rad/m  (closed form 27.015150)  0.0593% against the 1% ceiling
```

Both are fitted from the interior sample line, not read from the boundary data.
Four-digit agreement with the closed form is what a correct complex curl-curl
assembly produces here; the `TH-6` record carries 0.019% / 0.059% and this run
reproduces it.

**Step 2 — the sign of α, which is a convention check, not a physics check.**
`α > 0` is asserted separately. A conjugated `e^{−jωt}` convention — the single
most common way to get this problem subtly wrong — flips exactly this sign and
produces a wave *growing* into the absorber while every magnitude still looks
plausible. `ufl.inner` conjugates its first argument; that is where the sign
lives.

**Step 3 — the refinement, which rules out a lucky mesh.**

```
  coarse 12^3 (10368 cells)  rel L2 7.217852e-02
  fine   24^3 (82944 cells)  rel L2 3.609441e-02   rate 0.9998
```

Halving `h` halves the error: rate 0.9998 against the 1.0 that N1curl degree 1
owes for this quantity. A fitted α that matched at one mesh and did not improve
under refinement would be a coincidence, and this line is what catches it.

**Step 4 — the negative control, cited rather than recomputed.** At σ = 0 the
same closed form gives **α ≡ 0.0 Np/m exactly** — asserted `== 0.0` with no
tolerance, because a zero loss tangent makes the radical identically zero —
against the 13.069460 measured here. The *solved-field* version of that
separation is on record as `MAT-2` in the same gate log: σ = 0.1 → α = 2.1193
Np/m, σ = 1.4 → α = 21.878 Np/m, a ratio of 10.3232 against the closed-form
10.3116 (**0.113%**). This example prints the separation and does not re-run
those solves.

**Step 5 — the exported array, checked before it is looked at.** The `|E|` array
ParaView colours by spans **2.707108e-01 … 1.001903e+00 V/m**, a **3.701×** drop
against the closed form's `e^{αL}` = **3.694×**. The decay is therefore in the
written array and not only in the fit — the picture and the measurement agree to
0.2%.

**Step 6 — open it in ParaView.**
`File → Open → examples/time_harmonic/paraview_output/time_harmonic_01_lossy_plane_wave_combined.xdmf`,
then colour by `E_magnitude`.

1. **What to look at first:** brightest on the `x = 0` face, fading by ~3.7×
   across the box. That fade *is* `e^{−αx}`.
2. **Plot Over Line** along `x` through the middle of the box, log scale on the
   y-axis. A straight line, and its slope is the α of step 1 — the fit made
   visible.
3. **Glyph** or a colour map on `E_real` / `E_imag` separately: the phase
   winding underneath the envelope, a little over half a period across the box
   (`βL = 2.702`).

**Step 7 — what a deviation means.** α off by more than 1% while β is fine →
the imaginary part of `ε_c` (the conductivity path into the mass term), not the
curl operator. Both constants off together → `k₀` or the material map. **α
negative** → the sign convention of step 2, and no amount of mesh refinement
will fix it. The constants right but the rate collapsing toward 0 → the boundary
data is leaking into the fit window; check that the sample line stays interior.
Any of these is a regression finding against `TH-6`: report and stop, do not
raise the 1% ceiling.

## Related

- The gate this example runs: `tests/validation/test_lossy_plane_wave.py`
  (`TH-6`), and PROJECT_PLAN.md §7 for its record.
- A field decaying with **no loss anywhere** — geometry instead of absorption:
  `examples/time_harmonic/04_evanescent_waveguide_decay.py` (`th:4`).
- The same material acting on a *solved* field instead of a plane wave:
  `examples/time_harmonic/03_dielectric_sphere_in_uniform_field.py` (`th:3`).
