# `-e mri:3` — mass-averaged 10 g SAR on the coil-driven field

Guide for `examples/mri/03_birdcage_mass_averaged_sar.py`.
Written to be followed without the source open.

## 1. What this demonstrates

**The output-quantity angle `MAT-4` step 4 opened (2026-09-06).** `mri:2`
puts the C95.3 mass-averaging operator on an *imposed* uniform field —
gating the operator alone, with no coil in the picture. `ports:9` shows the
coil-driven field's quadrant *powers*. Neither shows a mass-averaged SAR on
a **solved coil field**, and neither shows the ball placement that turns a
C4 symmetry identity into a statement about the drive rather than about the
mesh. This example is exactly that missing picture: four single-drive
F-small birdcage solves on the finer-phantom rung, four 10 g averaging balls
sitting under the four legs at half the phantom radius, and the C4
covariance identity read off the coil-driven field itself.

```
SAR(x) = sigma(x)|E(x)|^2 / (2 rho)                       pointwise
SAR_10g(c_k; drive k) = <ball centred at leg k under drive k>
```

Rotating the drive from leg `k` to leg `k+1` rotates the solved field 90 deg
about the coil axis (the fixture is C4-symmetric by construction), so the
10 g average at the correspondingly rotated ball must be the same number —
that is the identity this example asserts.

**Import, and call, never restate.** Every constant — `CENTRE_RADIUS_M`,
`WHOLE_PHANTOM_BALL_RADIUS_M`, `EXACT_IDENTITY_RTOL`, the ball masses, the
quadrature degree, `C4_COVARIANCE_BAND` through its import chain — comes
from `tests/validation/test_birdcage_sar_mass_averaged.py`. The construction
itself is not re-implemented: the example imports and calls
`_build_mass_averaged`, the module-level function the gate's own pytest
fixture now wraps (a one-line, additive-only lift under the `EX-53` rule-(a)
licence — the fixture's existing behaviour and every existing test
assertion are unchanged; four new return keys, `mesh` / `cell_tags` /
`rho_field` / `solves`, expose what an external caller needs and were not
exposed before). Calling it inside the example re-runs the gate's own four
curl-curl solves and 21 `mass_averaged_sar` calls a second time, in this
process — not a comparison against a frozen literal.

**Scope.** 10 MHz, degree 1, one mesh, four single-leg drives. No absolute
SAR claim, no C95.3 compliance or limit claim, no homogeneity claim, no
Larmor, no convergence claim, no quadrature drive. `MAT-4` stays 🟡; nothing
here changes that.

## 2. How to run it

```
./run_examples.sh -e mri:3 -n 4 -t 600
```

**Complex build required** — the `mri:` group sources it automatically, and
a real build raises. Tier: **standard**, host-runner window ≤ 600 s.
Measured **91 s** harness-wall at `-n 4`
(`20260907T140658Z_EX-53.log`, exit 0; the gate's own module rerun in the
same slot measured 113.87 s for the whole pytest file including
`tests/environment`, `20260907T140233Z_MAT-4-step4-rerun.log`).

## 3. How to analyze it, step by step

**Step 1 — the mesh and ball geometry, asserted before anything else.**

```
[containment] r0 + a_10g = 28.3650 mm < phantom radius 30.0 mm — ASSERTED
```

The mesh cell counts (`120499` / `2746` tag-3) are asserted against the
gate's own `FINE_CELL_COUNT` / `FINE_PHANTOM_CELL_COUNT` at exact equality —
a dropped `phantom_resolution` would silently rebuild the coarse default and
every reading below would belong to a different fixture. The containment
check keeps every 10 g ball inside the phantom's CAD surface, where the
integrand is continuous (`sigma` jumps at that surface).

**Step 2 — anchor (i): the whole-phantom ball, an exact identity.**

```
[anchor i] whole-phantom ball ... 5.587038273e-08 W vs tagged integral
           5.587038273e-08 W [1.688e-14 relative, budget 1e-10]
[anchor i] against step 3f's own record 5.587038273e-08 W
           [5.403e-11 relative, budget 1e-03]
```

A ball of radius 0.0501 m (bigger than the phantom's 0.05 m circumradius,
smaller than the coil's nearest conductor at 0.064 m) encloses the whole
phantom and touches no conductor. Since `sigma = 0` in air, the ball's
`sigma|E|^2` is supported exactly on the phantom cells — the same discrete
integral as `mean_sar` restricted to tag 3, written two ways. Both
quadratures are exact for the degree-2 integrand, so the round-off-level
agreement (`1.688e-14` against a `1e-10` budget) is the correct answer: a
ball that misses cells, double-counts ghosts, or fails to reduce across
ranks would land nowhere near it. The second line ties this run's P1 solve
to `WF-6` step 3f's own record of the same quantity.

**Step 3 — anchor (ii): the four cyclic 10 g C4 pairs, the gate.**

```
k=0->1  10 g    0.3303%   1 g    6.8383% (printed, not gated)   control   86.0132%
k=1->2  10 g    0.0756%   1 g    2.9297% (printed, not gated)   control   85.9249%
k=2->3  10 g    0.0574%   1 g    0.4116% (printed, not gated)   control   85.9671%
k=3->0  10 g    0.3132%   1 g    4.7159% (printed, not gated)   control   85.9582%
```

All four 10 g pairs land inside the imported, unmoved 5.0% `C4_COVARIANCE_BAND`
(worst 0.3303%) — this is the anchor this example and the gate share.
The 1 g column is **printed, not gated**: it reads well outside the same
band (worst 6.8383%) but inside the gate's own pre-registered "pointwise
class" (2-10%), verdict `(b)` — a 6.2 mm ball on a 7.5 mm phantom `h` is a
~10-cell integral, and whether 1 g is gateable on this mesh is a review
decision, never made in this example or its slot.

**Step 4 — the negative control: the mis-paired far-side ball.**

The `control` column above is `SAR_10g(c_{k+2}; k)` — the ball
diametrically opposite the driven leg, still measured under drive `k`. It
must read **outside** the 5.0% band on every drive, and does (85.9-86.0%,
all four): a single-leg drive is strongly asymmetric about the axis, so the
driven-side ball and the far-side ball cannot agree. If they did, the C4
identity in step 3 would be measuring "the field is nearly uniform over the
phantom," not covariance. Only the **sign** (control > band) is asserted;
the **size** is printed against a predicted ~90% (ceiling 100%, since the
ratio of two positive SARs cannot exceed it) — this run's 85.9-86.0% sits
just under the prediction, consistent with the gate's own measurement on
this fixture.

**Step 5 — printed only, never gated.** The kernel-mass identity against the
closed form `rho * 4/3 * pi * a^3` (0.02-1.09% against a 0.1% budget quoted
as a *prediction*, rule (e) — the sphere gate's finer `h/a` measured
0.0044-0.0120%, and that finer-mesh number does not transfer to this coil
mesh's ball-to-cell ratio); each drive's peak 10 g SAR over the four
centres, labelled explicitly **not a C95.3 compliance figure** — it is an
absolute number on one unnormalised drive amplitude, meaningless without a
power normalisation this example does not apply.

**Step 6 — open it in ParaView.**
`File → Open → examples/mri/paraview_output/mri_03_birdcage_mass_averaged_sar_combined.xdmf`.

1. Colour by `SAR` (W/kg) — the P1-drive pointwise field, computed with the
   phantom's **physical** density `PHANTOM_RHO_KG_PER_M3` (a scalar), not
   the gate's special zero-elsewhere `rho_field` (that field exists only so
   a ball's *mass* integral excludes non-phantom cells in the denominator;
   using it pointwise would divide by zero in every non-phantom cell).
2. Threshold on `AveragingBall`: `0` outside every ball, `k+1` inside the
   10 g ball at centre `k`. Four small regions appear under the four legs.
   Because `r0` (15 mm) and `a_10g` (13.365 mm) put adjacent ball edges
   close together, neighbouring balls overlap slightly; where they do, the
   higher `k` wins in this rendering (cosmetic — no anchor depends on
   non-overlap, and the operator's own ball integral, being a UFL
   conditional per-call, is never affected by how this display field
   resolves an overlap).
3. Threshold on `CellTags` (`3` = phantom) to see the balls sitting inside
   the phantom, with the coil legs and rings visible as the conducting
   tags around them.

**Step 7 — what a deviation means.** Anchor (i) off round-off → a defect in
`mass_averaged_sar`'s cell coverage (missed cells, double-counted ghosts, an
unreduced local sum) — known-issues entry, stop, never widen `1e-10`. A 10 g
C4 pair outside 5% → the ball average at this mesh is not yet a gate — a
finding for the review, never a band change in this slot. The far-side
control landing *inside* the band → the solver has lost the drive
asymmetry entirely (a much larger regression) — stop immediately. Mesh
counts off `120499`/`2746` → `phantom_resolution` was not passed through;
every reading belongs to a different fixture and nothing above is
comparable.

## Related

- The gate this example calls into: `tests/validation/test_birdcage_sar_mass_averaged.py`
  (`MAT-4` step 4), and its own harness rerun this slot,
  `20260907T140233Z_MAT-4-step4-rerun.log`.
- The averaging operator on an imposed field (no coil, no solve):
  `examples/mri/02_mass_averaged_sar.py` (`mri:2`, `MAT-4` step 3).
- The coil-driven field's quadrant *powers*, the other half of the
  output-quantity pair: `examples/ports/09_birdcage_sar_quadrant_powers.py`
  (`ports:9`).
- Why no C95.3 or coil-SAR claim is made: PROJECT_PLAN.md §2.1.
