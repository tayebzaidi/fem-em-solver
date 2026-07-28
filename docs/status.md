# Project Status

> **Planning lives in [PROJECT_PLAN.md](https://github.com/awarru/fem-em-solver/blob/main/PROJECT_PLAN.md).**
> This page is a human-readable snapshot. When the two disagree, the plan wins.

Snapshot date: 2026-07-27.

## Where the project actually stands

**The magnetostatic solver is validated against a closed-form solution: 0.04%
centre-field error on a Helmholtz coil** (2026-07-27, log
`docs/testing/logs/20260727T171928Z_MAG-4.log`). That is the project's one solid
result. Most of the surrounding test suite is still broken or unverified.

| Phase | State |
|---|---|
| 0 — Infrastructure | Docker toolchain works; CI now runs the real validation suite. |
| 1 — Magnetostatics | **Complete and verified to 0.04%.** Full suite green. |
| 2 — Time-harmonic Maxwell | **Not started.** See the caveats below. |
| 3 — Materials & phantoms | Presets exist but do not affect solved fields. |
| 4 — Coil modeling & ports | Placeholder coupling model, now quarantined. |
| 5 — Full MRI integration | Blocked on Phases 2–4. |
| 6 — Advanced features | Deferred. |

## Phase 1 — actual test status

The full magnetostatics suite now runs green — `10 passed, 2 skipped` in 150 s on
8 ranks (`docs/testing/logs/20260727T190008Z_MAG-7.log`). It had never completed
before, and repairing it surfaced six independent defects, **none in the solver**:
broken point evaluation at 7 sites; an axial current density driving a torus that
lies in the xy-plane (on-axis `B_z` came out ~1000× too small); current applied
over the whole domain instead of the wire; an inverted convergence-rate sign; an
analytic expectation that was 2× wrong (the *test*, not the implementation); and
meshes that exhausted 16 GB or ran past 400 s.

| Test / example | Status |
|---|---|
| `examples/.../04_helmholtz_analytic_comparison.py` | ✅ 0.04% centre, 0.83% mean vs analytic |
| `test_helmholtz_v2.py` | ✅ uniformity `CV < 1%` |
| `test_straight_wire.py` | ✅ 18.3%, converging ~O(h) — see caveat below |
| `test_circular_loop.py` | ✅ 8.9% on-axis vs analytic |
| `test_convergence.py` | ✅ h-convergence rate +0.81 |
| `test_two_cylinder.py`, `test_two_torus.py` | ✅ pass at 1/2/4/8 ranks |
| `test_helmholtz.py`, `examples/03` | deleted — superseded by `_v2` and example `04` |

Straight-wire sits at ~18% by design: resolving a `1/r` field near a thin
conductor on a uniform mesh is intrinsically hard, and the same solver reproduces
the smooth Helmholtz field to 0.04%. That test checks the `1/r` trend and
azimuthal direction; the Helmholtz comparison carries the quantitative claim.

### Getting a meaningful analytic comparison

Domain size dominates accuracy here, not mesh resolution. The outer boundary imposes
`n×H = 0`, a perfect magnetic conductor that mirrors flux inward and inflates the
field. Use `air_padding >= 2*major_radius` together with graded sizing
(`wire_resolution`/`far_resolution`), or results will be tens of percent high
regardless of refinement:

| air padding | centre error |
|---|---|
| 0.5 R | 20.4% |
| 1 R | 7.4% |
| 2 R | 1.7% |
| 4 R | 0.01% |

## Important caveats

**The time-harmonic solver is a proxy, not a Maxwell solve.**
`core/time_harmonic.py` computes `E = -jωA` from the magnetostatic vector potential.
There is no `ω²εE` term and no `jωσ` term. Phantom conductivity and permittivity
currently have **no effect on any computed field**, so no phantom-loading, SAR, or
B1+ figure produced today is physically meaningful.

**Exported S-parameters are not simulation output.**
`ports/excitation.py` derives port voltages from a hardcoded coupling heuristic
rather than from the solved field. As of `PORT-0` this is quarantined: the entry
point is named `run_placeholder_port_coupling_case`, it warns on every call, and
Touchstone export refuses such data unless you pass `allow_placeholder=True` —
in which case the file is stamped `PLACEHOLDER DATA — NOT A SIMULATION RESULT`.
The numbers are unchanged and still meaningless; `PORT-1` is the real fix.

Both are tracked as `TH-1` and `PORT-1` in the plan, and both are on the critical
path.

## Known failing tests

Nine tests fail on `main` for reasons predating current work — stale test doubles, a
classifier/expectation disagreement, assertions against the placeholder port model,
and two undiagnosed cases. Each is catalogued with its symptom, the commit it was
verified failing at, and its cause in
[Known Issues](testing/known-issues.md). **Check there before debugging a failure.**

## Solver defaults worth knowing

`gauge_penalty` defaults to **1.0** (`DEFAULT_GAUGE_PENALTY` in `core/solvers.py`).
It was `1e-3`, which sits below the numerically safe window and silently corrupts
higher-order solves: at N1curl degree 2 the field error was **920%** while PETSc
reported *converged, residual 0.0*, because the default solver is a direct LU that
always "succeeds". `B` is insensitive across 1e0–1e6, so there is no accuracy
reason to lower it. Passing anything below 1.0 raises
`GaugeContaminationWarning`. See `PROJECT_PLAN.md` §7 `MAG-10`.

## Next work

1. `TH-1` + `TH-6` — real complex time-harmonic formulation, landed with an analytic gate
2. `MAT-2` — prove materials measurably affect solved fields
3. `PORT-1` — real port excitation derived from the solved field
4. Generalize the air-box/graded-meshing fix to the remaining `io/mesh.py` fixtures
5. Consider proper gauging (tree-cotree or A-V saddle point) before `TH-1` hardens —
   the penalty is a workaround, and the time-harmonic solver inherits it

See `PROJECT_PLAN.md` §9 for full sequencing.
