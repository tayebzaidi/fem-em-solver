# ANS-3 — Two coaxial gapped loops at 10 MHz: 2-port Z and S matrices

**Commissioned 2026-08-16 (weekly planning review).** Second Ansys benchmark
case, on the physics `PORT-1` gated 2026-08-15: field-derived S-parameters
through `run_n_port_sparameter_sweep` on the two-torus fixture, reciprocity
`‖S−Sᵀ‖/‖S‖ = 4.7586e-05` against the 1e-3 gate (2.5494e-05 until 2026-08-26;
the `PORT-9` leg (d3) power-wave assembly moved it — the **gate** is unmoved).
(`ANS-2` is reserved by
§10 for the future B1+/SAR-map case; the numbering gap is deliberate.)

**Why this case:** `PORT-1` closed carrying **two named systematics**
(PROJECT_PLAN §2.1) — the PEC-box correction, an effective-range
extrapolation from three padding rungs; and the gap-generator feed-model
correction (Jin 3e §10.4.2.1). Both are *corrections we apply*, not gated
physics, and their independent composition is untested (§7 `PORT-1`
standing cautions). AED replicates the identical boundary-value problem
with its own lumped-port feed model, so the AED `Z₁₂` arbitrates the
feed-model systematic directly, and the AED-vs-ours residual pattern is an
adjudication input for the composition question — information no closed
form can give us, since the filamentary reference itself spans 66.5% of
nominal over ±r_wire.

## Status

- [x] Runnable half implemented (`ANS-3`, PROJECT_PLAN §7) — script, metrics
      JSON, XDMF, `COMPARISON.md` with our numbers filled in
      *(2026-08-16, `03_two_torus_gap_ports_10MHz.py`, log
      `20260816T110354Z_ANS-3-runnable-half-n2.log`)*
- [ ] Operator replication in AED (goes to the dashboard Waiting-on-you list
      when the box above is checked)
- [ ] Adjudication (next weekly review after AED numbers land)

## Geometry (SI units, exactly as the gated fixture)

All coordinates in metres. Origin at the midpoint between the two loop
centres, z the common axis.

| Item | Definition |
|---|---|
| Computational box | `x, y ∈ [−0.125, +0.125]`, `z ∈ [−0.105, +0.105]` |
| Loop 1 (port 1) | Torus centred `(0, 0, −0.020)`, axis ẑ, major (centreline) radius **0.04**, circular wire cross-section radius **0.005**, **minus Gap box 1** |
| Loop 2 (port 2) | Torus centred `(0, 0, +0.020)`, same radii, **minus Gap box 2** |
| Gap box 1 | `x ∈ [0.0348, 0.0452]`, `y ∈ [−0.0069775, +0.0069775]`, `z ∈ [−0.0252, −0.0148]` |
| Gap box 2 | same x/y, `z ∈ [+0.0148, +0.0252]` |

Each loop is the **Boolean subtraction** full torus − gap box. This
reproduces the gated fixture's conductor exactly: the gap faces are the box
walls at `y = ±0.0069775`, planar and parallel. Everything else in the box
is air (vacuum). No shield, no other bodies.

## Materials

| Region | σ (S/m) | εᵣ | μᵣ |
|---|---|---|---|
| Both loops | **800** | 1 | 1 |
| Air (box minus loops) | 0 | 1 | 1 |

Skin depth in the wire at 10 MHz: δ = 5.63 mm = 1.13 × the wire radius —
the current fills the cross-section. **Solve fields inside the conductors**
(HFSS: material with bulk conductivity 800 S/m, *Solve Inside* on; do not
use an impedance boundary or PEC wires — the interior current distribution
is part of what is being compared).

## Ports

Two lumped ports, one per gap, reference impedance **Z₀ = 50 Ω**:

| Port | Sheet (planar rectangle) | Integration line |
|---|---|---|
| 1 | plane `z = −0.020`: `x ∈ [0.0348, 0.0452]`, `y ∈ [−0.0069775, +0.0069775]` | along ŷ, from `(0.04, −0.0069775, −0.020)` to `(0.04, +0.0069775, −0.020)` |
| 2 | plane `z = +0.020`, same x/y rectangle | along ŷ at `z = +0.020`, same direction |

Each sheet lies in the loop's centreline plane, spans the gap along ŷ, and
its `y = ±0.0069775` edges touch the two planar conductor gap faces along
their full diameter. Both integration lines point in **+ŷ** so the port
sign convention is identical.

## Boundary conditions

All six outer box faces: **perfect electric conductor** (`n × E = 0`).
The region must be exactly the box above — not an auto-sized padding
region, not a radiation boundary — so both solvers truncate identically.
(The PEC-box truncation is itself one of the two systematics under test;
matching it exactly is the point.)

## Frequency and solver

Single frequency: **10 MHz**. HFSS driven solve with the two lumped ports
above (structure is ~λ/120 — electrically small is expected and fine; the
comparison is FEM-vs-FEM on an identical problem, not a radiation study).
Direct solver preferred.

## Mesh guidance

Adaptive refinement at 10 MHz to ΔS ≤ 0.001, with initial seeding fine
enough for ≥ 4 elements across the wire diameter on both loops and ≥ 2
elements across the gap along ŷ (our fixture meshes the wires at
h = 2.5 mm against the 10 mm wire diameter and resolves the gap boxes to
0.3 mm near the arcs).

## Quantities to export (all digits AED prints; do not round)

| Quantity | Definition | Units |
|---|---|---|
| Z₁₁, Z₁₂, Z₂₁, Z₂₂ | complex Z-matrix at the two lumped ports | Ω |
| S₁₁, S₁₂, S₂₁, S₂₂ | complex S-matrix renormalized to 50 Ω | — |
| ‖S−Sᵀ‖/‖S‖ | reciprocity residual (Frobenius) — computable from the S entries; export the entries and we compute it | — |
| Solve metadata | element count, adaptive passes, final ΔS, solve time | — |

The primary adjudication rows are **Im Z₁₂** (against the filamentary
closed form ωM₁₂ = +1.241755 Ω and against our corrected estimate) and the
S-matrix entries at 50 Ω. `Z₁₁` is a secondary row: our diagonal carries
the unprojected electric-energy caveat (§7 `PORT-1` standing cautions), so
an AED `Z₁₁` disagreement is expected to be informative about *our* feed
model, not alarming.

## Reference values

| Quantity | Closed form (filamentary) | Our FEM (gated) | Notes |
|---|---|---|---|
| Im Z₁₂ | ωM₁₂ = +1.241755 Ω (spans 66.5% of nominal over ±r_wire — an anchor, not a gate) | corrected ratio 0.939849 × ωM₁₂ (−6.02%); raw 0.894543 × ωM₁₂ before the two systematic corrections | both printed; the 10% mutual band is the gate |
| ‖S−Sᵀ‖/‖S‖ | 0 (reciprocity) | 4.7586e-05 (2.5494e-05 before the leg (d3) power-wave assembly) | gated at 1e-3 |
| ‖S‖₂ | ≤ 1 (passivity) | 0.864809 (0.861449 before leg (d3)) | inequality + reproduction |

Exact values, logs, and provenance are filled into `COMPARISON.md` by the
`ANS-3` runnable-half chunk, which regenerates them through
`run_n_port_sparameter_sweep` (the `EX-20` path) rather than transcribing
by hand.

## Out of scope

No frequency sweep, no coil or birdcage claim, no SAR, no B1+. One
frequency, two solves inside AED's adaptive loop, eight complex numbers.
