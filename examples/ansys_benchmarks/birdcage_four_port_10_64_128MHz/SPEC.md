# ANS-4 — Gapped four-leg birdcage, phantom-loaded, four lumped ports: 4×4 S-matrix at 10 / 64 / 128 MHz

**Commissioned 2026-08-30 (weekly planning review).** Third Ansys benchmark
case, on the physics gated by `PORT-9` ✅ 2026-08-25 (10 MHz) and `PORT-11`
✅ 2026-08-26 (64 and 128 MHz): the loaded birdcage's four-port power-wave
S-matrix, passing reciprocity (`‖S−Sᵀ‖/‖S‖ ≤ 1e-3`), passivity
(`σ_max(S) ≤ 1 + 1e-9`) and C4 class symmetry (≤ 0.5%) at all three
frequencies on one 116 085-cell mesh (`EX-34`, `ports:5`). (`ANS-2` stays
reserved by §10 for the future B1+/SAR-map case.)

**Why this case:** those three gates are **self-consistency identities** — a
port model wrong by a constant factor passes all of them (PROJECT_PLAN
§2.2). Nothing in this repository has compared a Larmor-frequency figure
against anything outside the code; this case is the first independent
absolute check of the coil-fed port model at 64/128 MHz, and it is the
fixture every Phase-5 deliverable (B1+, coil-driven SAR) is computed on.
Two readings gated by nothing are also on record and worth AED's opinion:
the C4 class spreads grow ~1.7× per Larmor step (0.055 → 0.057 → 0.101%)
and `|Im P|/Re P` at the driven port rises 0.34 → 1.76 → 2.66.

## Status

- [x] Runnable half implemented (`ANS-4` ✅ 2026-08-30,
      `docs/testing/logs/20260830T213415Z_ANS-4-run1.log`, Status 0, 125 s at
      `-n 2`) — script in this
      directory dispatching through `./run_examples.sh -e ans:4`, importing
      every constant from the `PORT-9`/`PORT-11` gate modules and
      `examples/ports/05_birdcage_larmor_frequency_ladder.py`, writing
      `metrics.json`, `COMPARISON.md` (our columns filled, AED columns
      blank) and combined XDMF
- [ ] Operator replication in AED (goes to the top of the dashboard's
      Waiting-on-you list when the box above is checked)
- [ ] Adjudication (next weekly review after AED numbers land)

## Geometry (SI units, exactly as the gated fixture)

All coordinates in metres. Origin at the coil centre; **ẑ** is the coil
axis. Every solid below is what `MeshGenerator.birdcage_port_domain`
builds with `leg_count=4, ring_radius=0.07, leg_width=0.012,
leg_spacing=0.11, coil_length=0.14, ring_minor_radius=0.004,
phantom_radius=0.03, phantom_height=0.08, leg_gap_length=0.008,
port_clearance=1e-3, emit_port_sheets=True, air_padding=0.03`.

| Item | Definition |
|---|---|
| Computational box | `x, y ∈ [−0.120, +0.120]`, `z ∈ [−0.100, +0.100]` |
| End ring, top | Full torus centred `(0, 0, +0.055)`, axis ẑ, major (centreline) radius **0.070**, tube radius **0.004** |
| End ring, bottom | Same torus centred `(0, 0, −0.055)` |
| Legs (4) | Circular cylinders of radius **0.006**, axis parallel to ẑ, centred at `(0.070, 0)`, `(0, 0.070)`, `(−0.070, 0)`, `(0, −0.070)` (azimuths 0°, 90°, 180°, 270° — leg *i* at `90°·(i−1)`), spanning `z ∈ [−0.070, +0.070]` **minus the gap** `|z| ≤ 0.004` — i.e. two stubs per leg, `z ∈ [−0.070, −0.004]` and `z ∈ [+0.004, +0.070]`, each ending in a planar disk of area `π·0.006² = 1.130973e-04 m²` |
| Coil conductor | Boolean union of both rings and all eight stubs (the legs pass through the tori at `z = ±0.055`; the union is one connected metal body per stub set) |
| Port box *i* (4) | Axis-aligned box centred on leg *i*'s axis at `z = 0`: transverse **0.014 × 0.014** (`2·0.006 + 2·0.001`), axial **0.008** — exactly spanning the gap, so its two z-faces contain the stubs' cut disks |
| Phantom | Circular cylinder, radius **0.030**, `z ∈ [−0.040, +0.040]`, on the coil axis |

The legs are "uncut" high-pass-wise — this is a **low-pass-style gapped**
fixture with the gap (and port) in each leg's centre; the rings are whole.
No shield, no capacitors, no other bodies. Everything not listed is air.

## Materials

| Region | σ (S/m) | εᵣ | μᵣ |
|---|---|---|---|
| Coil conductor (rings + stubs) | **800** | 1 | 1 |
| Phantom | **0.5** | **78** | 1 |
| Air (box minus the above), and the port-box interiors | 0 | 1 | 1 |

Skin depth in the conductor: 5.63 mm at 10 MHz, 2.22 mm at 64 MHz,
1.57 mm at 128 MHz — comparable to or below the 6 mm leg radius, so **solve
fields inside the conductor** (HFSS: bulk conductivity, *Solve Inside* on;
no impedance boundary, no PEC wires). The phantom's loss tangent
`σ/(ωε₀εᵣ)` is 11.5 / 1.80 / 0.90 at the three frequencies — it crosses
from conduction- to displacement-dominated across the ladder, which is why
all three frequencies are asked for.

## Ports

Four lumped ports, one per leg gap, reference impedance **Z₀ = 50 Ω**, and
**every port not being driven is terminated in 50 Ω** (our sweep solves
one driven port at a time with the other three sheets carrying their
lumped 50 Ω law; AED's driven-terminal solve with all four ports defined at
50 Ω is the same boundary-value problem).

| Port | Sheet (planar rectangle) | Integration line |
|---|---|---|
| 1 | in the plane `y = 0` (contains leg 1's axis and its radial direction): `x ∈ [0.0665, 0.0735]`, `z ∈ [−0.004, +0.004]` | along **+ẑ** from `(0.070, 0, −0.004)` to `(0.070, 0, +0.004)` |
| 2 | plane `x = 0`: `y ∈ [0.0665, 0.0735]`, `z ∈ [−0.004, +0.004]` | +ẑ at `(0, 0.070)` |
| 3 | plane `y = 0`: `x ∈ [−0.0735, −0.0665]`, same z | +ẑ at `(−0.070, 0)` |
| 4 | plane `x = 0`: `y ∈ [−0.0735, −0.0665]`, same z | +ẑ at `(0, −0.070)` |

The sheet is the **interior half** (`f = 0.5`, `PORT-9` step 2b) of the
port box's mid-plane: width 0.007 centred on the leg axis, height 0.008
equal to the gap, its top and bottom edges on the two stub cut faces. All
four integration lines point **+ẑ**, so the sign convention is identical
on every port and the S-matrix is C4-circulant by construction.

## Boundary conditions

All six outer box faces: **perfect electric conductor** (`n × E = 0`). The
region must be exactly the box above — not an auto-sized region, not a
radiation boundary — so both solvers truncate identically.

## Frequency and solver

Three discrete frequencies, **10 MHz, 64 MHz, 128 MHz**, each a separate
driven solve on the same geometry (a discrete sweep with the mesh adapted
at 128 MHz and reused is acceptable; say which). Direct solver preferred.

**Basis / element order (`ANS-5` ruling, 2026-08-30):** our side is
`degree = 1` Nédélec (6 unknowns per tetrahedron) = HFSS **Zero Order**.
Run AED **twice** and report both columns: (a) **Zero Order** — the matched
discretization, the adjudication column; (b) **First Order** (the AED
default, 20 unknowns/tet) — the order-sensitivity column. **Mixed Order is
forbidden** (we have no per-element order and could not reproduce it).
Please confirm the unknowns-per-tet figure AED prints in its matrix
statistics for each run; the 6 / 20 correspondence is the standard basis
definition and has not yet been confirmed against AED's own output.

## Mesh guidance

Adaptive refinement to ΔS ≤ 0.002 at each frequency, seeded with ≥ 3
elements across the leg diameter and ≥ 2 across each gap along ẑ. Our
mesh grades the conductor surfaces to 1.6 mm inside a 12 mm shell and is
15 mm elsewhere, 116 085 tetrahedra; at 128 MHz that is 12.5 cells per
in-phantom wavelength and 5.2 per in-phantom skin depth. Report the final
element count and passes per frequency.

## Quantities to export (all digits AED prints; do not round)

| Quantity | Definition | Units |
|---|---|---|
| S (4×4), all 16 complex entries | S-matrix renormalized to 50 Ω, at each of the three frequencies | — |
| Z (4×4) | complex Z-matrix at the four lumped ports, at each frequency | Ω |
| `‖S−Sᵀ‖/‖S‖`, `σ_max(S)` | computable from S — export the entries and we compute them | — |
| Accepted power and driven-port `Im P / Re P` | per driven port, at each frequency | W, — |
| Solve metadata | element count, adaptive passes, final ΔS, solve time, **basis order and unknowns/tet**, per frequency | — |

The primary adjudication rows are the **three C4 classes** of the S-matrix
at each frequency — `S₁₁` (self), `S₂₁` (adjacent, 90°), `S₃₁` (opposite,
180°) — nine complex numbers, and the reciprocity/passivity/C4-spread
figures derived from the full 4×4. `Z₁₁` is a secondary row (our diagonal
carries the sheet-width convention `w = A/h`, `PORT-9` step 2b).

## Reference values (ours, gated; to be regenerated into `COMPARISON.md` by the runnable half)

| Frequency | `‖S−Sᵀ‖/‖S‖` (gate 1e-3) | `σ_max(S)` (gate ≤ 1 + 1e-9) | C4 class spreads self / adjacent / opposite (gate 0.5%) | log |
|---|---|---|---|---|
| 10 MHz | 2.259e-14 | 0.999992805 | 0.0553 / 0.0353 / 0.0214% | `PORT-9` leg (d1′), 2026-08-25 |
| 64 MHz | 2.581325834e-14 | 0.999721388 | 0.0573 / 0.0599 / 0.0370% | `20260826T110434Z_PORT-11-step2.log` |
| 128 MHz | 7.030990825e-15 | 0.998974779 | 0.1012 / 0.0916 / 0.0654% | `PORT-11` step 3, 2026-08-26 |

The complex S entries themselves are **not** transcribed here: the
runnable half regenerates them through `run_n_port_sparameter_sweep` (the
`ports:5` path) so the benchmark cannot drift from the gate — `ANS-1`'s
rule.

## Out of scope

No tuning, no resonance or mode claim, no capacitors, no B1+, no SAR, no
16-leg or ring-gap layout, no F-human scale. Three frequencies, twelve
driven solves on our side, three AED solves per basis order, 48 complex
numbers per column.
