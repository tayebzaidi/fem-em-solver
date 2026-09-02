# `ports:3` — the lumped-element port sheet: width ladder and S-matrix

Guide for `examples/ports/03_lumped_sheet_port_widths.py` (`EX-24`).
Written to be followed without the source open.

## 1. What this demonstrates

The first example instantiating the **lumped-element port boundary condition**.
`ports:1` (`EX-18`) and `ports:2` (`EX-20`) both drive this same two-torus
fixture through the **gap-voltage** route: an impressed current in the gap
cells, and a terminal-to-terminal path integral read off the solved field
afterwards. The port is post-processing there. Here it is part of the operator:
a sheet impedance `R = Z_p · w / h` on an interior surface enters the
**bilinear form**, so changing the port changes the matrix and every width is
its own solve (`PORT-9` steps 1–2c, Jin ch. 11 §11.3).

Two angles no other example covers, in that order:

1. **Drive/BC** — the width ladder. The port sheet is narrowed to interior
   width fractions `f ∈ {1.0, 0.735, 0.5}` of the gap box's half-width, and the
   cross-route deviation between the two feed models is measured at each.
2. **Output quantity** — the sweep. At the gated width, a two-port S-matrix is
   assembled through `run_n_port_sparameter_sweep` on the *lumped-sheet* route
   (`ports:2` takes the gap-voltage route through the same function).

### Why the width matters

The lumped port reads `V = −(1/w)∫_S E·ĥ dS` — the gap voltage averaged
**across the width of the gap box** — while the gap route integrates the
centreline alone. On the full mid-plane sheet those two disagree by **7.7431%**,
outside the 5% band pre-stated at scoping, and `PORT-9` step 2 diagnosed the
whole miss as that transverse average: 7.7783 pp of it, against a
path/projection residual of 0.0763 pp. The review's decision was to **narrow the
sheet**, not widen the band — which is also the honest model, since a real feed
strap is narrower than the gap box it sits in.

The narrowing is a facet-**midpoint** filter on `GEO-16`'s already
dolfinx-side-rebuilt `21x` tags, so there is no gmsh change and no re-mesh: the
mesh is bit-identical across the ladder, which is exactly what makes `f = 1.0`
a control on the fixture rather than on a second mesh.

### The trap: `w = A/h`, never the bbox extent

The midpoint filter leaves a **ragged** edge — a facet is kept whole when its
midpoint clears the threshold, so its nodes reach past it — and the kept region
is not a rectangle. `R = Z_p·w/h` counts squares between the terminal edges, so
it wants the strip's *mean* width; the bounding-box extent is its *maximum*. On
this ladder the two differ by 15.3% (`f = 0.735`) and 14.2% (`f = 0.5`), and
taking the bbox extent put step 2b's first attempt at 16.39% / 14.04% instead of
~1%. `A/h` is the mean width by definition; on a rectangle it *is* the bbox
extent, which the example asserts on the `f = 1.0` rung — that is what leaves
the negative control untouched by the choice.

### What it asserts

Every band and record below is **imported** from the gate modules (the `ANS-1`
rule); nothing is restated, so this example cannot drift from the gates it
demonstrates.

| Assertion | Gate | Measured 2026-08-18 |
| --- | --- | --- |
| cross-route at `f = 0.5` ≤ `CROSS_ROUTE_BAND` (5%) | `PORT-9` step 2b | **1.9222%** |
| `f = 1.0` reproduces `STEP1_CROSS_ROUTE_RECORD` to `REPRODUCTION_BAND` (1e-4) | control (i) | **7.7431%** |
| gap ratio flat at `STEP1_GAP_RATIO_RECORD` (0.894310 × ω·M₁₂), every rung, to 1e-4 | control (ii) | 0.894310 / 0.894324 / 0.894349 |
| `f = 1.0` asserted to **MISS** the 5% band | control (iii), inverted | 7.7431% > 5% |
| open-limit identity `V = −(1/w_f)∫_S E·ĥ dS` < `DECOMPOSITION_IDENTITY_BAND` (1e-11), per width | exact arithmetic | 1.8e-15 / 8.5e-16 / 2.1e-16 |
| sweep reciprocity ‖S−Sᵀ‖/‖S‖ ≤ `RECIPROCITY_BAND` (1e-3) | `PORT-9` step 2c | **2.574296e-11** |
| cross-route through the sweep ≤ 5%, both driven columns | `PORT-9` step 2b/2c | 1.6079% / 1.5950% |
| meshed/analytic gap-box volume = 1 to 1e-9 | `PORT-1` 3b-i | 1.000000000000 |
| sheet non-empty, strictly narrowing, still planar (< 1e-12) | structural | 1585 → 1511 → 1375 facets |
| terminal path integral converged in quadrature < 1e-3 | `PORT-1` 3b-x | held at every width |

Control (iii) is the `EX-18` inverted-assertion pattern and is the one worth
understanding: if the full-width sheet ever passed the 5% band, the ladder would
demonstrate nothing, because the width would not be what the gate turns on.

**Scope: two-torus only.** No birdcage, no `PORT-9` step 3 claim. The
reciprocity *record* (2.574249e-11) is step 2c's; this example reproduces it.

## 2. How to run it

```
./run_examples.sh -e ports:3
```

Complex DolfinX build required; the runner sources it automatically for the
`ports:` group. Tier: **standard**. On record at `-n 2`: mesh **184 919 cells in
40.1 s**, three ladder solves **26.9 / 24.1 / 24.1 s**, the two-port sweep
**52.3 s**, **237.5 s** in-script total including the ParaView export — 239 s of
harness wall clock, measured 2026-08-18, log
`20260819T003401Z_EX-24-example-n2.log`. Both legs share one mesh. Add `-n <k>`
to change rank count and `-t <s>` to lower the per-example timeout.

Exit status 0 means every row of the table above held. A non-zero exit is an
assertion failure, not a rendering problem.

## 3. How to analyze it, step by step

**Step 1 — check the fixture before reading any port number.** The header
prints the meshed/analytic gap-box volume (`1.000000000000`) and
`ω·M₁₂ = 1.241755` Ω, the closed-form Maxwell mutual inductance every ratio
below is normalised by. The drive normalises through that gap volume, so if it
has moved, the rungs are not one fixture and nothing further is comparable.

**Step 2 — read the geometry table, not the physics, first.** For each `f` the
script prints facet count, area, `w = A/h`, the bbox extent, and what
`f × w_full` *would* have been:

- `f = 1.000`: `A/h = 1.040000000e-02` m and the bbox extent agree to
  round-off — the full sheet is the rectangle both definitions assume.
- `f = 0.735`: `A/h = 7.616677977e-03` m against a bbox extent of
  `8.780489185e-03` m. That 15.3% gap is the ragged edge; if you ever see the
  bbox number used as `w`, the ladder is measuring the mis-scaling and not the
  width.
- Facet counts fall `1585 → 1511 → 1375` and areas fall monotonically. Counts
  that do not fall mean the filter did not run.

**Step 3 — the open-limit identity, before the ladder.** `V_lumped` from
`ports.lumped` against an independently assembled `−(1/w_f)∫_S E·ĥ dS`, at
1e-15 or below on every rung. This is algebra on one solved field, so it holds
to round-off or the code is wrong; its specific job is to catch the port model's
sheet and the width it is scaled by coming from *different* facet sets, which
would silently rescale every voltage below.

**Step 4 — the ladder.** `7.7431% → 1.0986% → 1.9222%`, tagged `MISS` /
`INSIDE` / `INSIDE` against the 5% band. Read it as one measurement with three
readings:

1. The `f = 1.0` rung is step 2's own number, reproduced to 1e-4. It must miss.
2. The deviation is **not monotone** in `f`: it reaches step 2's transverse
   profile prediction (~1.1% at interior width) at `f = 0.735` (1.0986%), then
   rises again at `f = 0.5` (1.9222%) rather than continuing to fall. Both
   readings stay inside the 5% band; the non-monotonicity is itself the
   informative result the old (monotone) triple silently misrepresented, and
   the band still would not widen.
3. The **gap** ratio stays at 0.894310 × ω·M₁₂ across the whole ladder (drift
   3.9e-5). The gap route cannot see the port BC's sheet, so a gap ratio that
   moved with `f` would mean the narrowing perturbed the field itself, and the
   difference the ladder reports would be an artifact.

**Step 5 — the sweep.** Two solves, one per driven port, both sheets narrowed to
`f = 0.5`. Read in this order:

1. `is_placeholder` is asserted `False`. A placeholder S-matrix is the `PORT-0`
   coupling heuristic (known-issues 3), not a field-derived result, and the
   number would mean nothing.
2. `‖S − Sᵀ‖/‖S‖ = 2.574296e-11` against 1e-3. The network is passive and made
   of reciprocal materials, so the S-matrix assembled column by column from two
   independent solves must be symmetric. This is the identity that catches a
   route wiring the wrong port's sheet, the wrong width, or the source into the
   bilinear form.
3. `S11 = S22 = 0.9869` to five figures and `|S12| ≈ 2.3e-6`: the near-open
   probe termination (`Z_p = 1e6` Ω) makes both ports reflect almost everything,
   and the two tori are weakly coupled at 10 MHz. That is a property of the
   fixture, not a defect.
4. The cross-route reading carried *through* the sweep — 1.6079% and 1.5950% —
   sits ~0.23 pp below step 2b's 1.9222% at the same width. Expected: the drive
   differs (an impressed **sheet** source here, an impressed **gap current**
   there), so the comparison is reported and gated only at the 5% band, never at
   1e-4.

**Step 6 — open the field in ParaView.**
`examples/ports/paraview_output/ports_03_lumped_sheet_port_widths_combined.xdmf` carries
the `f = 0.5` solved phasor (`E_real`, `E_imag`, `E_magnitude`) on the same grid
as `CellTags` (`1`/`2` wires, `3` air, `101`/`111` and `102`/`112` the gap-box
halves). Open `ports_03_lumped_sheet_port_widths_facets.xdmf` alongside it and threshold
`mesh_tags` on `211`/`212` — those are the port sheets the BC lives on. The
picture worth looking at is `E_magnitude` clipped through `z = +0.025` m: the
field concentrates in the *undriven* gap, which is the coupling `Z₁₂` measures.

**Step 7 — what a deviation means.**

- **`f = 1.0` off 7.7431% by more than 1e-4** — the example path changed the
  fixture rather than the sheet. Everything downstream is then measuring that
  change; known-issues entry, report, stop.
- **`f = 0.5` above 5%** — a regression against the `PORT-9` step 2b gate. The
  band is never widened to admit it (PROJECT_PLAN §7, MAG table, defect 5).
- **Open-limit identity above 1e-11** — the sheet and its `w` are different
  facet sets. Look at the filter, not at the physics.
- **Reciprocity above 1e-3** — a finding about the lumped BC's reciprocity
  through the sweep, which is `PORT-9` step 3's gate (i) prerequisite; it blocks
  step 3 rather than this example.
- **Hang at `-n 2`, no output** — the interior-facet assembly needs
  `create_entity_permutations` called on *every* rank, not only ranks owning
  tagged facets (known-issues 9). The example hoists it right after the mesh.

## Related

- The gates themselves: `tests/validation/test_port_lumped_narrowed_sheet.py`
  (`PORT-9` step 2b) and `tests/validation/test_port_lumped_sheet_sweep.py`
  (step 2c); the step-1 constants live in
  `tests/validation/test_port_lumped_two_torus.py`.
- The mesh this stands on: `examples/meshing/04_two_torus_port_sheet.md`
  (`mesh:4`, `GEO-16`) — the sheet as a geometry object, no solve.
- The other feed model: `examples/ports/01_two_torus_port_pair.md` (`ports:1`,
  gap voltage → `Z` → `S`) and `examples/ports/02_package_sparameter_sweep.md`
  (`ports:2`, the same sweep function on the gap-voltage route).
- What the sheet is *for* next: `PORT-9` step 3 in PROJECT_PLAN.md §7 —
  birdcage lumped-sheet ports, reciprocity, passivity, C4 circulant symmetry.
- Group-level ParaView workflow: `examples/magnetostatics/PARAVIEW_GUIDE.md`.
