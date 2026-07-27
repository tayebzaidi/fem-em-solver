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
| 0 — Infrastructure | Docker verification toolchain works. CI still runs only `tests/unit`. |
| 1 — Magnetostatics | **Solver verified to 0.04%.** Several older tests still broken. |
| 2 — Time-harmonic Maxwell | **Not started.** See the caveats below. |
| 3 — Materials & phantoms | Presets exist but do not affect solved fields. |
| 4 — Coil modeling & ports | Implemented against a placeholder coupling model. |
| 5 — Full MRI integration | Blocked on Phases 2–4. |
| 6 — Advanced features | Deferred. |

## Phase 1 — actual test status

| Test / example | Status |
|---|---|
| `examples/.../04_helmholtz_analytic_comparison.py` | **Verified.** 0.04% centre, 0.83% mean vs analytic. |
| `test_helmholtz_v2.py` | Sound. Proper point location; asserts uniformity `CV < 1%`. |
| `test_straight_wire.py` | **Broken** — bad point evaluation *and* current applied over the whole domain. Also >400 s, over budget. |
| `test_circular_loop.py` | **Broken** — bad point evaluation. |
| `test_helmholtz.py` | **Broken** — bad point evaluation. Superseded by `_v2`. |
| `test_convergence.py` | **Broken** — bad point evaluation. |
| `test_two_torus.py` | **Fails at `mpiexec -n 4`** — asserts on rank-local `cell_tags.values`; a rank owning no wire cells trips it. Pre-existing. |

The common defect is `B.eval(points, np.arange(n))`, which evaluates each point in an
arbitrary cell rather than the one containing it, producing meaningless numbers. The
correct machinery already exists in `src/fem_em_solver/post/evaluation.py`. Tracked as
`MAG-7`; example `04` is the reference pattern for the fix.

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
rather than from the solved field. Touchstone `.s2p` files the project emits are
well-formed and physically meaningless. Do not use them downstream.

Both are tracked as `TH-1` and `PORT-0`/`PORT-1` in the plan, and both are on the
critical path.

## Next work

1. `MAG-7` — route validation tests through `post/evaluation.py` instead of `np.arange`
2. `MAG-8` — restrict straight-wire current density to the wire subdomain
3. `MAG-9` — re-size validation meshes into the 3-minute `standard` budget
4. Re-run all of MAG to find out whether the solver actually matches closed-form results
5. `OPS-2` — put the repaired suite in CI
6. `PORT-0` — quarantine the placeholder port model
7. `TH-1` + `TH-6` — real complex time-harmonic formulation, landed with an analytic gate

See `PROJECT_PLAN.md` §9 for full sequencing.
