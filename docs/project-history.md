# Project history — resolved defects and decisions

Archive of *why* things are the way they are. Not reviewed regularly; nothing
here is a task. Open work lives in `PROJECT_PLAN.md`.

---

## The 2026-07-27 audit — nothing had ever executed

CI ran only `tests/unit`. ~3,400 lines of test code ran nowhere, so `docs/status.md`
claimed "Phase 1 COMPLETE" and the README claimed analytic validation while the
suite was incapable of passing. Executing it surfaced six independent defects,
**none in the solver**:

| # | Defect | Evidence |
|---|---|---|
| 1 | `B.eval(points, np.arange(n))` evaluates in arbitrary cells | 7 sites; output oscillated where analytic was smooth |
| 2 | Axial current density in an xy-plane torus (both loop tests) | on-axis `B_z` ~1000× too small |
| 3 | Wire current applied over the whole domain | ~2500 A enclosed instead of 1 A |
| 4 | Convergence-rate sign inverted | reported −0.79 for convergent data |
| 5 | Analytic expectation 2× wrong | test wanted `μ₀I/(2√2a)`; correct is `μ₀I/(4√2a)` |
| 6 | Meshes mis-sized | OOM at 16 GB / >400 s |

Defect 5 is why the plan forbids loosening a failing analytic comparison: the
*test* was wrong and the *implementation* was right.

`OPS-3`/`OPS-4` had sat at `AWAITING-HUMAN-TEST` for months while being
**unrunnable** — two test files sharing a basename with no `__init__.py`, so
pytest's `prepend` import mode failed to collect the second and the smoke matrix
exited 2 every time. Fixed with `--import-mode=importlib`. That is the canonical
argument for §4's execute-it-yourself rule.

A related pathology: human-gated completion plus a "cron-safe mode forbids
solves" policy produced ~35 consecutive commits of *"record audit note: no new
human test logs found"*, and 19 byte-identical status blocks in
`pending-tests.md`. Hence §5.2.

## The air box, not mesh resolution, was the dominant magnetostatics error

`two_torus_domain` hardcoded `box_half = R + 3a`, coupling the air gap to the
*wire radius*. The natural outer condition `n×H = 0` acts as a perfect magnetic
conductor and mirrors flux inward. Because of the coupling, a *thinner* wire
shrank the box and made agreement *worse* (43.7% at `a = 0.003` vs 20.5% at
`a = 0.005`) — the inverted trend is what identified the boundary as the culprit.

Fixed with `air_padding` (decoupled from `minor_radius`) plus graded
`wire_resolution`/`far_resolution` via a gmsh Distance+Threshold field. Grading
is what makes a large box affordable: 76k cells instead of ~626k for equivalent
wire fidelity. Two convergence studies then confirmed 0.04% centre-field error
was real rather than error cancellation:

| air padding | cells | centre err | | wire `h` @ 4R pad | cells | centre err | mean err |
|---|---|---|---|---|---|---|---|
| 0.5 R | 40k | 20.42% | | 0.004 | 89k | 0.11% | 1.07% |
| 1 R | 51k | 7.43% | | 0.003 | 127k | 0.04% | 0.84% |
| 2 R | 76k | 1.73% | | 0.002 | 228k | 0.05% | 0.51% |
| 4 R | 163k | **0.01%** | | | | | |

## `MAG-10` — the gauge penalty default was silently corrupting

The degree-2 blow-up was not an element-order problem. `gauge_penalty = 1e-3`
sat below the safe window; the penalty fixes `|A_gradient| ∝ 1/gauge`, so against
`μ⁻¹ ≈ 8×10⁵` the null-space component ran ~9 orders larger than the physical
field and `B = ∇×A` lost it to cancellation. Degree 1 merely hid the problem.

| degree | gauge | L2 error | `max\|A\|` |
|---|---|---|---|
| 1 | 1e-3 | 24.84% | 4.39e+04 |
| 1 | ≥1e0 | 24.67% | 5.23e+01 |
| 2 | **1e-3** | **919.85%** | **3.46e+07** |
| 2 | ≥1e0 | **19.59%** | 4.26e+01 |

The failure was silent: with direct LU, PETSc reported *converged, residual 0.0*
for the 919% answer — the same shape as the near-resonance risk `TH-1` must guard
against. Fix: `DEFAULT_GAUGE_PENALTY = 1.0`, shared by every entry point, plus
`GaugeContaminationWarning` below the floor. `B` is insensitive across 1e0…1e6 on
two independent geometries.

A solution-based guard was **tried and rejected**: `||A||/(L·||curl A||)` reads
~5e8 for a known-good solve, so no threshold separates good from bad without false
alarms. It is still computed for diagnostics, just not a trigger.

Tree-cotree gauging is rejected outright: `TH-1`'s E-field formulation has no
static null space at ω > 0, so further magnetostatic gauge machinery has no
Phase-2 payoff.

## `MAG-15` — Lagrange-multiplier gauge, two traps

Two implementation traps, neither caught by a single-rank test:

- `p` must live in the **full `H¹`**, not `H¹₀`. Restricting the multiplier leaves
  gradients of boundary-nonzero functions unconstrained; the system stays singular
  and returns `NaN`/`inf` rather than failing loudly.
- `fem.locate_dofs_geometrical` is **collective**. Calling it under
  `if comm.rank == owner` deadlocks *rank-count dependently* — completes at 2 ranks,
  hangs at 4. `MPI.MINLOC` over a pickled tuple is likewise not reliably consistent;
  owner election uses scalar reductions only.

## `MAG-13` — the analytic Dirichlet wall, and a wrong premise

The wire's natural BC contradicts Ampère's law for net axial current, an error no
refinement removes: 35.13% → 22.19% at fixed h once the analytic wall replaced it.

For the **loop** the plan's premise was wrong in sign, and the measurement was the
deliverable. The analytic wall is ~20% *worse* at fixed h (16.23% vs 14.98% at
h = 0.0035), because the loop's natural-BC bias is only a PMC image term of order
`(a/R)³ ≈ 3.7%` — smaller than the O(h) error that degree-1 interpolation of `A_φ`
injects through the boundary data itself. What it buys is the limit:
16.23% → 10.37% → **7.07%** converges monotonically to the analytic field, while
the natural wall converges to a field that differs from it. So the bound tightened
10% → 8% *at h = 0.002*, not at the old h = 0.0025 where the analytic BC would have
needed 12% — the resolution moved, not the bound.

Convergence triples rejected on measurement: h = 0.005 gives 30.34% (5 mm cells
cannot resolve a 3 mm wire), and h = 0.0035 gives 11.77%, *below* the h = 0.0025
value, making any triple containing it non-monotone.

## Scheduled sessions could not reach the Docker daemon (resolved 2026-07-28)

Root cause was the Bash sandbox, not group membership: the sandbox's user
namespace strips the `docker` supplementary group, so nothing inside it can open
`/var/run/docker.sock`. Fixed by putting `docker *` and
`scripts/testing/run_and_log.sh *` in `sandbox.excludedCommands`; both still gated
by the permission allowlist. Automation logs also moved to `logs/automation/`.

Related, 2026-07-30: the documented preflight `cd docker && docker compose ps` is
denied in scheduled sessions — a `cd` inside a compound command prompts regardless
of the allowlist, and headless runs have nobody to approve. Use
`docker compose -f docker/docker-compose.yml ps`.

## On-deck queue drained by midday (resolved 2026-07-30)

The daily review sized "On deck" at exactly 3 items while cron runs the
implementer 6× daily, so the last three slots of the day stopped with `anomaly`
entries and no chunk work. Fixed by raising the floor to 6 items and giving the
implementer a fallback to §9's "obvious next entry" sentence.

## Superseded documents

`ROADMAP.md` merged into `PROJECT_PLAN.md`; `docs/status.md` is a generated
snapshot, not a plan. Per-chunk historical detail (files changed, pass signals,
commit hashes) is in `docs/testing/pending-tests.md`.
