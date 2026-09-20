# ANS-6 — Copper four-leg birdcage, phantom-loaded, four lumped ports: 4×4 S-matrix and loss partition at 10 / 64 / 128 MHz

**Commissioned 2026-09-19 (weekly planning review)**, under the operator
directive of 2026-09-04 and §10's tuned-birdcage chain step 9. Fifth Ansys
benchmark case, on the physics gated by `TH-15` (the coil as a PEC hole) and
`TH-14` ✅ 2026-09-14 (the Leontovich surface-impedance boundary: cavity Q
against Pozar to +0.010 %, the copper Dodd–Deeds floor to −0.299 %, and the
copper F-small birdcage's `PORT-9`/`PORT-11` identities and surface-loss
identity at all three frequencies, `20260914T021500Z_TH-14.log`).

**Why this case.** (1) Every absolute statement so far is on a σ = 800 S/m
"conductor" solved inside; this is the first external check of a realistic
coil, and the first of the **loss partition** `P_coil / P_in`, which is the
reason the conductor model exists. (2) It carries a **PEC-coil column on both
sides**, and that column is a discriminator the 2026-09-19 `ANS-4` reading
needs: `ANS-4`'s order-matched comparison disagrees on the **self class**
toward low frequency (qualitative verdict only — PROJECT_PLAN §10,
2026-09-19). With a PEC coil neither code resolves a conductor interior, so a
self-class disagreement that survives here is the lumped-port model's, and
one that vanishes was the resolved σ = 800 interior's.

## Status

- [x] Runnable half (`ANS-6`, §7) — ✅ 2026-09-20. Script in this directory
      dispatching through `./run_examples.sh -e ans:6`, importing every
      constant from `tests/validation/test_th14_birdcage_copper.py` (lifted
      to a module-level `_build_ladder()`, rule (a)) and cross-checking the
      PEC column against `tests/validation/test_th15_birdcage_pec_hole.py`'s
      own `_hole_rung`, writing `metrics.json`, `COMPARISON.md` (our columns
      filled, AED columns blank) and combined XDMF. Details: PROJECT_PLAN.md
      §7 `ANS-6` row; guide:
      `06_copper_birdcage_four_port_10_64_128MHz.md`.
- [x] Operator replication in AED — **landed 2026-09-20** (HFSS 2026 R1, Cu and
      PEC columns × Zero and First Order, `aed/ans6_hfss_pyaedt.py`; numbers in
      the gitignored `aed_results/`; Linux half re-run
      `20260920T175038Z_ANS-6-aed-compare.log`; by-hand reading in
      `docs/private/ans6-operator-notes-2026-09-20.md` — the example has no
      private-mode writer yet)
- [ ] Adjudication (next weekly review after AED numbers land)

## Geometry (SI units)

**Identical to `ANS-4`** —
`../ans4_birdcage_four_port_10_64_128MHz/SPEC.md` § Geometry, every solid,
coordinate and the computational box `x, y ∈ [−0.120, +0.120]`,
`z ∈ [−0.100, +0.100]` unchanged: two end-ring tori (major radius 0.070, tube
radius 0.004, at `z = ±0.055`), four legs of radius 0.006 at azimuths 0°, 90°,
180°, 270° on radius 0.070 spanning `z ∈ [−0.070, +0.070]` minus the gap
`|z| ≤ 0.004`, phantom cylinder radius 0.030, `z ∈ [−0.040, +0.040]`. Re-use
the `ANS-4` AED project's geometry; **only the coil's material treatment
changes.** On our side the coil is a *hole* in the mesh
(`birdcage_port_domain(..., as_hole=True)`): its surface is a boundary, its
interior is not meshed.

## Materials and the two coil columns

| Region | Treatment |
|---|---|
| Phantom | σ = **0.5** S/m, εᵣ = **78**, μᵣ = 1 (as `ANS-4`) |
| Air, port-box interiors | σ = 0, εᵣ = 1, μᵣ = 1 |
| Coil — **column Cu** | HFSS **Finite Conductivity** boundary on every coil face, σ = **5.8e7** S/m, μᵣ = 1, no roughness, no layered option, **Solve Inside off** (or the coil subtracted from the region with the boundary on the resulting faces — say which). Ours: `Z_s = (1 + j)/(σδ)` on the coil-surface facets, Jin §1.5.3 (1.54)–(1.56). |
| Coil — **column PEC** | **Perfect E** on every coil face, Solve Inside off. Ours: `n × E = 0` on the same facets (`TH-15` step 3). |

Skin depth in copper: 20.9 µm / 8.26 µm / 5.84 µm at 10 / 64 / 128 MHz —
10²–10³ below every radius of curvature, so the impedance condition is valid
on both sides and nothing inside the metal is to be meshed.

## Ports, boundary conditions, frequencies

**Identical to `ANS-4`:** four lumped ports, one per leg gap, the interior-half
sheet (width 0.007 × height 0.008) in the plane containing the leg axis and
its radial direction, integration line along **+ẑ** on every port, reference
**50 Ω**, undriven ports terminated in 50 Ω; all six box faces **Perfect E**;
discrete solves at **10, 64 and 128 MHz**. The port sheets' top and bottom
edges lie on the stub cut faces, which are now boundary faces (Cu or PEC) —
the sheet must touch them.

## Basis order and mesh

Per the `ANS-5` ruling run **each coil column at both orders**: **Zero Order**
(= our degree 1, the adjudication column for our standard-tier half) and
**First Order** (the AED default = our degree 2, the column an order-matched
`xl` rung of ours is read against). Mixed Order forbidden. Four designs ×
three frequencies. Adaptive refinement to ΔS ≤ 0.002 at each frequency
(adapt at each frequency, or adapt at 128 MHz and reuse — say which), seeded
with ≥ 2 elements across each gap along ẑ. Confirm unknowns-per-tet from the
matrix statistics as on `ANS-4`.

## Quantities to export (all digits AED prints; do not round)

| Quantity | Definition | Units |
|---|---|---|
| S (4×4), all 16 complex entries | renormalized to 50 Ω; per column, order, frequency | — |
| Z (4×4) | complex Z-matrix at the four lumped ports | Ω |
| Accepted power, port 1 driven | per column, order, frequency | W |
| **Phantom volume loss**, port 1 driven | Fields calculator: ∫ volume-loss density over the phantom | W |
| **Coil surface loss**, port 1 driven (column Cu only) | Fields calculator: ∫ surface-loss density over all coil faces | W |
| Solve metadata | tets, passes, final ΔS, wall time, order, unknowns/tet | — |

**Primary adjudication rows:** (a) the three C4 classes `S₁₁`, `S₂₁`, `S₃₁`
per column and frequency; (b) the **loss partition**
`P_coil / (P_coil + P_phantom)` on column Cu per frequency — a ratio, so the
two codes' incident-power conventions cancel (the `ANS-2` normalisation
lesson, 2026-09-18); (c) the **column difference** `S(Cu) − S(PEC)` per
class — small, and the quantity the conductor model actually adds.
Secondary: `Z₁₁`.

## Reference values (ours, gated, degree 1; regenerated by the runnable half, never transcribed from here)

| Frequency | `‖S−Sᵀ‖/‖S‖` (gate 1e-3) | `σ_max(S)` | worst class spread (gate 0.5 %) | surface-loss identity residual (gate 1e-6) | `P_coil/P_in` (printed) |
|---|---|---|---|---|---|
| 10 MHz | 1.85e-14 | 0.999994231 | 0.0190 % | 1.575e-13 | 0.929 |
| 64 MHz | 3.68e-15 | 0.999813505 | 0.0496 % | 2.963e-13 | 0.448 |
| 128 MHz | 1.16e-15 | 0.999500814 | 0.0734 % | 7.024e-14 | 0.219 |

Source: `20260914T021500Z_TH-14.log:1037–1347`. These are identities and a
printed share, not absolute claims.

## Out of scope

No tuning capacitors (that is `ANS-7`, HFSS + Circuit, after this case is
adjudicated), no resonance or mode claim, no B₁⁺, no SAR, no 16-leg or
F-human layout, no roughness or plating models.
