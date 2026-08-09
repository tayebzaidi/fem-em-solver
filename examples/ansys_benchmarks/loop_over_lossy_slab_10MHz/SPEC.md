# ANS-1 — Circular loop over a lossy slab at 10 MHz (coil-loading ΔZ)

**Commissioned 2026-08-09 (weekly planning review).** First Ansys benchmark
case. The physics is gated: `MAT-6` closed 2026-07-31 with the FEM ΔR
matching the Dodd–Deeds (1968) closed form to **1.58%** (1.5834% on the
production projected drive, step 3, 2026-08-04). This case replicates that
exact fixture in Ansys Electronics Desktop so the comparison is
FEM-vs-FEM on an identical boundary-value problem, with the closed form as
the independent anchor both solvers should approach.

**Why this case:** it is the project's headline gated physics — "the phantom
loads the coil" — and AED adds information our gates cannot: our ΔX is
**not converged** in box size (5.57% still moving between W = 0.15 and 0.20)
and is gated on sign/magnitude only, so the AED ΔX number is a genuine
adjudication input, not a formality.

## Status

- [ ] Runnable half implemented (`ANS-1`, PROJECT_PLAN §7) — script, metrics
      JSON, XDMF, `COMPARISON.md` with our numbers filled in
- [ ] Operator replication in AED (goes to the dashboard Waiting-on-you list
      when the box above is checked)
- [ ] Adjudication (next weekly review after AED numbers land)

## Geometry (SI units, exactly as the gated fixture)

All coordinates in metres. Origin at the centre of the slab's top surface,
z up.

| Item | Definition |
|---|---|
| Computational box | Cube, `x, y, z ∈ [−0.15, +0.15]` |
| Slab (conductor) | The lower half-box: `z ∈ [−0.15, 0]`, full x/y extent |
| Air | The upper half-box: `z ∈ [0, +0.15]`, minus the coil |
| Coil | Circular torus centred on the z-axis: loop radius **0.04** (centreline), circular wire cross-section radius **0.0025**, centreline plane at **z = +0.020** (lift-off measured slab surface → wire centre) |

No shield, no phantom, no other bodies. The coil does **not** intersect the
slab (closest wire surface point is at z = +0.0175).

## Materials

| Region | σ (S/m) | εᵣ | μᵣ |
|---|---|---|---|
| Slab | 100 | 1 | 1 |
| Air | 0 | 1 | 1 |
| Coil interior | treated as source region, not a conductive body (see Excitation) |

Skin depth in the slab at 10 MHz: δ = 15.9 mm; the slab is 9.42 δ deep.

## Excitation

Total loop current **1 A (peak), uniform azimuthal current density over the
wire cross-section** — i.e. a stranded/impressed current, **no skin or
proximity effect inside the wire**. In Maxwell 3D eddy-current: model the
torus as a **stranded** coil, 1 conductor, 1 A, eddy effects **off** in the
coil body and **on** in the slab.

## Boundary conditions

All six outer box faces: perfect electric conductor (`n × E = 0`).
In Maxwell 3D eddy-current this is the natural/default flux-tangential
boundary on the region walls — the region must be exactly the cube above,
**not** an auto-sized padding region, so both solvers truncate identically.

## Frequency

Single frequency: **10 MHz**. (Not the Larmor frequency — this is the
eddy-current regime where the physics is gated; see PROJECT_PLAN §2.1.)

## Solve and mesh guidance

Maxwell 3D, eddy-current solver. Adaptive refinement to ≤ 0.5% energy error,
with a seeded band in the slab under the coil fine enough for ≥ 3 elements
per skin depth in the top 2 δ of the slab (our fixture resolves 3.18
near-cells per δ). Two solves, identical mesh settings:

1. σ_slab = 100 S/m (the case above)
2. σ_slab = 0 (replace slab material with air; geometry and mesh unchanged)

## Quantities to export (both solves)

| Quantity | Definition | Units |
|---|---|---|
| R | Re Z at the coil terminals (stranded coil impedance) | Ω |
| X | Im Z at the coil terminals | Ω |
| ΔR | R(σ=100) − R(σ=0) | Ω |
| ΔX | X(σ=100) − X(σ=0) | Ω |
| Solve metadata | element count, adaptive passes, final energy error | — |

Report all digits AED prints; do not round.

## Reference values

| Quantity | Dodd–Deeds closed form | Our FEM (gated) | Notes |
|---|---|---|---|
| ΔR | see `COMPARISON.md` | **+3.2770406e-01 Ω** (projected drive; +3.276882e-01 pinned) | gated to 1.58% vs closed form |
| ΔX | see `COMPARISON.md` | ratio 0.9200 of closed form (projected drive) | **not converged in our box**; sign/magnitude gate only |

The closed-form numbers and the exact provenance logs are filled into
`COMPARISON.md` by the `ANS-1` runnable-half chunk, which regenerates them
from `utils/dodd_deeds.py` rather than transcribing by hand.

## Out of scope

No S-parameters (ungated, PROJECT_PLAN §2.2), no SAR, no thermal, no
frequency sweep. One case, two solves, four numbers.
