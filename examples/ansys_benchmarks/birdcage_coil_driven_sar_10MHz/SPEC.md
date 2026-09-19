# ANS-2 — Coil-driven SAR in the loaded four-leg birdcage at 10 MHz: pointwise SAR, mass-averaged SAR, and the phantom power budget

**Commissioned 2026-09-09 (weekly planning review).** Fourth Ansys benchmark
case. §10 has reserved `ANS-2` for "the future B1+/SAR case" since
2026-08-16; the trigger written into that reservation — Phase-5 subgoal 4's
SAR half closing on a **gated** quantity — fired on 2026-09-06 (`MAT-4`
step 4: the C95.3 mass-averaging operator on the *coil-driven* field, 10 g
C4 quadrant identity inside the unmoved 5 % band) and again on 2026-09-08
(`MAT-4` step 5b: the same identity gated at 1 g on `GEO-27`'s
`h_p` = 0.0025 m rung). This case is the commission that reservation
promised.

**Why this case, stated as the gap it closes.** Every SAR number this
repository has produced on a *coil-driven* field is a **symmetry identity**
— four quadrant values agreeing with each other to ≤ 0.14 %. A SAR
computation wrong by a constant factor (a density, a factor of two in the
time-average, a normalisation) passes that identity exactly. The repo's only
*absolute* SAR check is against the lossy-sphere closed form on an **imposed
uniform field** (`MAT-4` step 1, 3.5 %) — never on a coil. PROJECT_PLAN §2
says so in as many words: "the absolute / compliance claim is still open".
This case is the first independent absolute check of coil-driven SAR, and it
is cheap for the operator because **the geometry, materials, ports and
boundary condition are byte-for-byte `ANS-4`'s** — the same HFSS project,
one frequency, plus a mass density and a field-calculator export.

## Status

- [ ] Runnable half implemented (§7 chunk `ANS-2`, to be scoped by the daily
      review; script in this directory dispatching through
      `./run_examples.sh -e ans:2`, importing every constant and band from
      the `MAT-4` gate modules — `ANS-1`'s rule, nothing restated — and
      writing `metrics.json`, `COMPARISON.md` with our columns filled and
      the AED columns verbatim blank, and combined XDMF)
- [x] Operator replication in AED — **landed 2026-09-18** (HFSS 2026 R1, Zero
      and First Order, via the untracked `aed/ans2_hfss_pyaedt.py`; numbers in
      the gitignored `aed_results/` and `COMPARISON_private.md`, written by
      `20260918T235648Z_ANS-2-aed-private.log`; preliminary reading in
      `docs/private/ans2-operator-notes-2026-09-18.md`)
- [ ] Adjudication (next weekly review after AED numbers land; numeric
      ruling to gitignored `docs/private/ans2-adjudication-<date>.md`, only
      the qualitative verdict into tracked files)

## Geometry (SI units — identical to `ANS-4`; reuse that project)

**Copy `ANS-4`'s geometry exactly.** It is reproduced here so this file
stands alone, but if the two ever disagree, `ANS-4`'s SPEC.md is
authoritative and the disagreement is a defect in this file.

All coordinates in metres. Origin at the coil centre; **ẑ** is the coil
axis. Every solid below is what `MeshGenerator.birdcage_port_domain` builds
with `leg_count=4, ring_radius=0.07, leg_width=0.012, leg_spacing=0.11,
coil_length=0.14, ring_minor_radius=0.004, phantom_radius=0.03,
phantom_height=0.08, leg_gap_length=0.008, port_clearance=1e-3,
emit_port_sheets=True, air_padding=0.03`.

| Item | Definition |
|---|---|
| Computational box | `x, y ∈ [−0.120, +0.120]`, `z ∈ [−0.100, +0.100]` |
| End ring, top | Full torus centred `(0, 0, +0.055)`, axis ẑ, major (centreline) radius **0.070**, tube radius **0.004** |
| End ring, bottom | Same torus centred `(0, 0, −0.055)` |
| Legs (4) | Circular cylinders of radius **0.006**, axis parallel to ẑ, centred at `(0.070, 0)`, `(0, 0.070)`, `(−0.070, 0)`, `(0, −0.070)` (azimuths 0°, 90°, 180°, 270° — leg *i* at `90°·(i−1)`), spanning `z ∈ [−0.070, +0.070]` **minus the gap** `\|z\| ≤ 0.004` — two stubs per leg, each ending in a planar disk of area `π·0.006² = 1.130973e-04 m²` |
| Coil conductor | Boolean union of both rings and all eight stubs |
| Port box *i* (4) | Axis-aligned box centred on leg *i*'s axis at `z = 0`: transverse **0.014 × 0.014**, axial **0.008** |
| Phantom | Circular cylinder, radius **0.030**, `z ∈ [−0.040, +0.040]`, on the coil axis |

No shield, no capacitors, no implant, no other bodies. Everything not listed
is air.

## Materials — **one row is new relative to `ANS-4`: the phantom's mass density**

| Region | σ (S/m) | εᵣ | μᵣ | ρ (kg/m³) |
|---|---|---|---|---|
| Coil conductor (rings + stubs) | **800** | 1 | 1 | (irrelevant — SAR is reported on the phantom only) |
| Phantom | **0.5** | **78** | 1 | **1000** |
| Air (box minus the above), and the port-box interiors | 0 | 1 | 1 | — |

`ρ = 1000 kg/m³` is not cosmetic: it is the density our C95.3 averaging
operator assumes, it sets the 1 g and 10 g ball radii below, and it is the
denominator of `SAR = σ|E|²/(2ρ)`. **HFSS will not compute SAR at all unless
the phantom material carries a mass density; set it to exactly 1000.** Skin
depth in the conductor at 10 MHz is 5.63 mm against the 6 mm leg radius, so
**solve fields inside the conductor** (bulk conductivity, *Solve Inside* on;
no impedance boundary, no PEC wires). The phantom's loss tangent
`σ/(ωε₀εᵣ)` is 11.5 — conduction-dominated, which is why 10 MHz is the
frequency this gate was taken at.

## Ports and drive

Four lumped ports, one per leg gap, reference impedance **Z₀ = 50 Ω**,
sheets and integration lines **exactly as `ANS-4`'s SPEC.md §Ports** (the
interior half of each port box's mid-plane, width 0.007 centred on the leg
axis, height 0.008; all four integration lines point **+ẑ**).

**Four separate single-drive solves, one per port.** In solve *k*, port *k*
is excited and the other three are terminated in 50 Ω. This is *not* a
quadrature drive — the repo's gate has no quadrature SAR claim and this case
must not create one.

### Normalisation — read this twice; it is the one thing that can make the
### comparison meaningless without failing any check

Our side drives the excited port with a source amplitude `V_src = 1 V`
behind a 50 Ω source impedance (`V = V_src − I·Z_p`). The solver's phasors
are **peak** amplitudes (`ports/superposition.py`), so the available
incident-wave power is `|V_src|²/(8Z₀) = 1/400 =` **2.5000000e-03 W**.
*(Corrected 2026-09-18: this clause said `V²/(4Z₀) = 5.0e-03 W`, the RMS
form, a factor of two high — the exact "silent normalisation mismatch" the
next paragraph warns about, caught by the first AED comparison because our
reported accepted power matched `1 − |S₁₁|²` only of the halved figure.
The ratio to HFSS's 1 W is therefore 400, not 200.)*

**You do not have to reproduce that.** Export at whatever excitation HFSS
uses — its default is 1 W incident per port — and **report the incident
power (or incident voltage) AED actually applied, per solve, in
`aed_results/`.** SAR is quadratic in the field and therefore *linear* in
incident power, so we rescale on our side by the reported ratio. Reporting
the number is mandatory; matching it is not. A silent normalisation
mismatch is the single most likely way this case produces a wrong "answer"
that passes every self-check on both sides, which is why the ratio is
carried explicitly rather than assumed.

## Boundary conditions

All six outer box faces: **perfect electric conductor** (`n × E = 0`). The
region must be exactly the box above — not an auto-sized region, not a
radiation boundary — so both solvers truncate identically.

## Frequency and solver

**10 MHz only**, one driven solve per port (four solves). Direct solver
preferred.

**Basis / element order (`ANS-5` ruling, 2026-08-30):** our side is
`degree = 1` Nédélec (6 unknowns per tetrahedron) = HFSS **Zero Order**.
Per the `ANS-4` adjudication (2026-09-06), **10 MHz is the frequency at
which our port model already agrees with AED**, so this case does not need
the order-sensitivity column that `ANS-4` needed: run **Zero Order** as the
adjudication column, and **First Order** only if it is free (same project,
one extra setup). Mixed Order is forbidden.

## Mesh guidance

Adaptive refinement to ΔS ≤ 0.002, seeded with ≥ 3 elements across the leg
diameter and ≥ 2 across each gap along ẑ, **and additionally ≥ 4 elements
across the 1 g averaging ball diameter inside the phantom** (ball diameter
12.40 mm ⇒ phantom elements ≤ 3.1 mm). That last clause is the one mesh
instruction that is specific to this case: our own 1 g column was **not
gateable** until `GEO-27` measured the rung that puts 4.96 cells across that
ball (`h_p` = 0.0025 m, 199 920 total / 58 866 phantom cells) — a 1 g
average over ~1.7 cells is a mesh statement, not a physics one, and the same
trap exists on the AED side. Report the final element count, the element
count inside the phantom, and the adaptive passes.

## Quantities to export (all digits AED prints; do not round)

Report every row **per driven port** (four sets), on the **phantom only**.

| # | Quantity | Definition | Units |
|---|---|---|---|
| 1 | **Pointwise SAR at four named points** | `σ\|E\|²/(2ρ)` evaluated at `(±0.015, 0, 0)` and `(0, ±0.015, 0)` — the four ball centres below | W/kg |
| 2 | **Whole-phantom dissipated power** | `½∫_phantom σ\|E\|² dV` over the phantom volume | W |
| 3 | **Whole-phantom average SAR** | row 2 divided by the phantom mass (`ρ·V`, `V = π·0.03²·0.08 = 2.261947e-04 m³`, mass 0.2261947 kg) | W/kg |
| 4 | **1 g mass-averaged SAR at the four named points** | IEEE C95.3 / IEC 62704-1 averaged SAR, averaging mass 1 g, evaluated at the four points of row 1 | W/kg |
| 5 | **10 g mass-averaged SAR at the four named points** | same, averaging mass 10 g | W/kg |
| 6 | **Peak 1 g and peak 10 g averaged SAR over the whole phantom**, with the location of each peak | the C95.3 quantity a compliance statement would use | W/kg, m |
| 7 | Excitation metadata | incident power (or incident voltage) applied per solve, accepted power, driven-port `Im P / Re P` | W, — |
| 8 | Solve metadata | element count, phantom element count, adaptive passes, final ΔS, solve time, basis order and unknowns/tet | — |
| 9 | Averaging metadata | **which averaging volume shape and standard HFSS used** (cube per IEC 62704-1, or sphere), and the averaging algorithm setting | — |

The four named points are the ball centres our gate uses: radius
`r₀ = 0.015 m` on the four port azimuths (0°, 90°, 180°, 270°), i.e.
`(0.015, 0, 0)`, `(0, 0.015, 0)`, `(−0.015, 0, 0)`, `(0, −0.015, 0)`, all at
`z = 0`.

### Which rows adjudicate, and which carry a known systematic

**Rows 1, 2 and 3 are the primary adjudication rows.** Pointwise SAR and
integrated phantom power are **shape-free**: they involve no averaging
volume, so the two codes are computing the same functional of the same
field, and a disagreement there is a disagreement about the physics or the
normalisation. Row 2 in particular is the cleanest single number in the
case — one volume integral, no sampling, no averaging convention.

**Rows 4, 5 and 6 are secondary and carry a named systematic.** Our operator
averages over a **sphere** of equal mass (radii **6.20e-03 m** at 1 g,
**1.337e-02 m** at 10 g, at ρ = 1000); HFSS's averaged SAR follows
IEC 62704-1 and averages over a **cube**. A sphere and a cube of the same
mass are not the same operator, and in a field with curvature they do not
give the same average. **Do not treat a few-percent miss on rows 4–6 as a
finding until rows 1–3 have agreed** — if rows 1–3 agree and rows 4–6 miss
by a few percent, the answer is the averaging-volume shape and it belongs in
the case's systematics list, not in known-issues. This is why row 9 is
mandatory: without knowing which shape AED used, rows 4–6 are
uninterpretable.

## Reference values (ours, gated; regenerated into `COMPARISON.md` by the runnable half, never transcribed here — `ANS-1`'s rule)

What is *gated* on our side, and what this case can therefore promote:

| Our gated quantity | Reading | Band | Source |
|---|---|---|---|
| 10 g C4 quadrant identity, four cyclic pairs | 0.3303 / 0.0756 / 0.0574 / 0.3132 % | `C4_COVARIANCE_BAND` = 5 % (imported, unmoved) | `MAT-4` step 4, 2026-09-06 |
| 1 g C4 quadrant identity, four cyclic pairs, on the `h_p` = 0.0025 m rung | 0.0957 / 0.1199 / 0.1305 / 0.1065 % | same 5 % band | `MAT-4` step 5b, 2026-09-08 |
| Whole-phantom coverage identity | 1.58e-14 | machine | `MAT-4` step 4 |
| The rung's mesh, version-tagged record | 199 920 / 58 866 cells | `CELL_COUNT_BAND` = 1 % | `MAT-4` step 5b |

Our **absolute** SAR values (per-drive 1 g and 10 g averages at the four
centres, whole-phantom power) are *printed and asserted nowhere* — that is
precisely the hole this case exists to fill. The runnable half regenerates
them so the benchmark cannot drift from the gate.

## What an agreement would license, and what it would not

**Would license:** the first absolute, externally checked statement about
coil-driven SAR in this repository — "the coil-driven pointwise SAR and
phantom power budget of the loaded four-leg F-small birdcage at 10 MHz agree
with HFSS to X %" — and, with it, promotion of the `MAT-4` C4 identity from
a self-consistency gate to a gate with an external absolute anchor.

**Would not license:** nothing about 64 or 128 MHz (`ANS-4`'s Larmor verdict
is INCONCLUSIVE and this case does not touch it); no C95.3 *compliance*
statement (a compliance figure needs a whole-body or head model, a real
input power and a real coil, none of which exist here); no homogeneity or
B₁⁺ claim; no implant, no thermal; nothing about the quadrature drive.

## Out of scope

One frequency, one fixture, four driven solves per side. No tuning, no
resonance, no capacitors, no quadrature, no 16-leg or ring-gap layout, no
F-human scale, no implant, no B₁⁺ map, no Larmor rung.

## Privacy

**AED numbers from this case never enter a tracked file** (operator
directive 2026-09-02; Ansys licence terms). They live in this directory's
gitignored `aed_results/` and `COMPARISON_private.md` and in
`docs/private/`. Tracked files, journals, dashboards and commit messages
carry only the qualitative verdict — agree / disagree / inconclusive — and
what it decides.
