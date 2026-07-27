# Project Status

> **Planning lives in [PROJECT_PLAN.md](https://github.com/awarru/fem-em-solver/blob/main/PROJECT_PLAN.md).**
> This page is a human-readable snapshot. When the two disagree, the plan wins.

Snapshot date: 2026-07-27.

## Where the project actually stands

**Nothing is validated against a closed-form solution yet.** This page previously
claimed "Phase 1 — COMPLETE"; running the tests on 2026-07-27 did not support that.

| Phase | State |
|---|---|
| 0 — Infrastructure | Docker verification toolchain works. CI still runs only `tests/unit`. |
| 1 — Magnetostatics | Solver plausible; **its analytic validation tests are broken.** |
| 2 — Time-harmonic Maxwell | **Not started.** See the caveats below. |
| 3 — Materials & phantoms | Presets exist but do not affect solved fields. |
| 4 — Coil modeling & ports | Implemented against a placeholder coupling model. |
| 5 — Full MRI integration | Blocked on Phases 1–4. |
| 6 — Advanced features | Deferred. |

## Phase 1 — actual test status

| Test | Status |
|---|---|
| `test_helmholtz_v2.py` | Sound. Proper point location; asserts uniformity `CV < 1%`. |
| `test_straight_wire.py` | **Broken** — bad point evaluation *and* current applied over the whole domain. Also >400 s, over budget. |
| `test_circular_loop.py` | **Broken** — bad point evaluation. |
| `test_helmholtz.py` | **Broken** — bad point evaluation. Superseded by `_v2`. |
| `test_convergence.py` | **Broken** — bad point evaluation. |

The common defect is `B.eval(points, np.arange(n))`, which evaluates each point in an
arbitrary cell rather than the one containing it, producing meaningless numbers. The
correct machinery already exists in `src/fem_em_solver/post/evaluation.py` and is used
by `test_helmholtz_v2.py`. Tracked as `MAG-7`.

The magnetostatic formulation in `src/fem_em_solver/core/solvers.py` implements the
N1curl weak form `∫μ⁻¹(∇×A)·(∇×v) dx = ∫J·v dx` with a gauge penalty and produces a
uniform central field in a Helmholtz configuration. It is plausible — and unproven
against any analytic magnitude.

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
