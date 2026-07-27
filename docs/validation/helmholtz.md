# Helmholtz Coil Validation (Phase 1)

## Objective
Validate that the FEM magnetostatic solver reproduces the analytic on-axis field
of a Helmholtz coil pair, quantitatively.

## Status

**Validated to 0.04% against the closed-form solution** (2026-07-27).

An earlier version of this page concluded "Phase 1 Helmholtz validation is
complete" on the strength of a *uniformity* check alone (`CV < 1%`). Uniformity
is a necessary but far weaker condition than agreement with an analytic
magnitude — a solver can produce a beautifully uniform field of entirely the
wrong strength. The quantitative comparison below is what actually closes this.

## Geometry and setup
- Coil model: two torus wire volumes
- Major radius `R`: `0.02 m`
- Minor radius `a`: `0.005 m`
- Coil separation: `0.02 m` (Helmholtz spacing, equal to `R`)
- Mesh generator: `MeshGenerator.two_torus_domain(...)`
- Material: `mu = MU_0`
- Current: azimuthal current density in both torus volumes, unit magnitude, so
  the current per loop is `I = |J| * pi * a^2`

## Quantitative validation

```bash
mpiexec -n 8 python3 examples/magnetostatics/04_helmholtz_analytic_comparison.py \
  --major-radius 0.02 --minor-radius 0.005 \
  --air-padding 0.08 --far-resolution 0.010 --resolutions 0.003 --points 21
```

Reference: the filamentary on-axis Helmholtz field,

```
B_z(z) = sum_i  mu_0 * I * R^2 / (2 * (R^2 + (z - z_i)^2)^{3/2})
```

Result (log `docs/testing/logs/20260727T171928Z_MAG-4.log`, 127k cells, 26 s):

| Metric | Value |
|---|---|
| Centre `B_z`, FEM | `3.529697e-09 T` |
| Centre `B_z`, analytic | `3.531057e-09 T` |
| **Centre relative error** | **0.04%** |
| Mean on-axis relative error | 0.83% |
| Central uniformity `CV` | 0.003% |

This clears the project's `<5%` MVP criterion by two orders of magnitude.

## The air box dominates accuracy — not mesh resolution

The single most important result from this validation is *why* it initially
disagreed. At the historical domain size the error was **20.5% and did not
improve across a 7x refinement** (10k → 70k cells). It is not a discretization
error.

The outer boundary carries the natural condition `n x (mu^-1 curl A) = 0`, i.e.
`n x H = 0`. That is a perfect **magnetic** conductor: it mirrors flux back into
the domain and inflates the on-axis field. `two_torus_domain` originally
hardcoded `box_half = R + 3a`, tying the air gap to the *wire radius*, so making
the wire thinner shrank the air box. That inverted trend — a thinner wire giving
*worse* agreement, 43.7% at `a = 0.003` versus 20.5% at `a = 0.005` — is what
identified the boundary as the cause.

| Air padding | Cells | Centre error |
|---|---|---|
| 0.5 R | 40k | 20.42% |
| 1 R | 51k | 7.43% |
| 2 R | 76k | 1.73% |
| **4 R** | 163k | **0.01%** |

Two independent convergence studies confirm the result is real rather than error
cancellation — boundary error falls monotonically with domain size, and
discretization error falls monotonically with `h`:

| Wire `h` at 4R padding | Cells | Centre error | Mean error |
|---|---|---|---|
| 0.004 | 89k | 0.11% | 1.07% |
| 0.003 | 127k | 0.04% | 0.84% |
| 0.002 | 228k | 0.05% | 0.51% |

**Use `air_padding >= 2 * major_radius` for any free-space comparison.** Pair it
with `wire_resolution`/`far_resolution` graded sizing, or cost becomes
prohibitive: grading gives ~76k cells where a uniform mesh of equivalent wire
fidelity needs ~626k.

## Uniformity check

`tests/validation/test_helmholtz_v2.py` remains as a cheap regression guard:

```bash
mpiexec -n 2 python3 -m pytest tests/validation/test_helmholtz_v2.py -v
```

- Evaluate `Bz` on axis for `z in [-0.1R, +0.1R]`
- Require `CV = std(Bz)/|mean(Bz)| < 1%`

Note this test previously located sample points with a per-rank collision
search asserting `len(links) > 0`, which passed at 1–4 ranks and failed at 8. It
now uses `post.evaluation.evaluate_vector_field_parallel`.

## Conclusion

The magnetostatic formulation in `core/solvers.py` — the N1curl weak form
`∫ mu^-1 (curl A)·(curl v) dx = ∫ J·v dx` with gauge penalty — reproduces the
closed-form Helmholtz field to 0.04%. This is the project's one quantitatively
validated component and the foundation the time-harmonic work (`TH-1`) builds on.

Caveat for higher order: N1curl degree 2 was measured on the straight-wire
fixture and **diverged** (2724% error at `h = 0.003`), which points at the
gauge-penalty formulation rather than element order. Do not raise the element
degree without re-validating.
