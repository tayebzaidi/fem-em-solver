# `-e mri:2` — mass-averaged SAR: point vs 1 g vs 10 g

Guide for `examples/mri/02_mass_averaged_sar.py`.
Written to be followed without the source open.

## 1. What this demonstrates

**The averaging operator, not a SAR number.** IEEE C95.3 states RF exposure
limits as SAR averaged over 1 g and 10 g of tissue, so every safety figure this
project will ever produce passes through a mass-averaging kernel. This example
puts that kernel on screen and gates it — and gates *only* it.

The identity it tests is the one that holds regardless of mesh, radius or
placement: **on a uniform field, mass-averaged SAR equals pointwise SAR
exactly.** Averaging a constant returns the constant, whatever ball you average
over. So a uniform interior phasor is *imposed* on the N1curl space (degree-1
Nédélec contains the constants exactly, so the imposed field carries no
interpolation error) and every residual below belongs to the kernel: to its
quadrature, to its mass bookkeeping, to its treatment of `σ(x)`.

```
SAR(x) = σ(x)|E(x)|² / (2 ρ(x))            pointwise
SAR_avg = ∫_B σ|E|²/2 dV  /  ∫_B ρ dV      averaged over a ball B of mass m
```

**Imposed field, no solve — and no C95.3 claim.** An IEEE-conformant 1 g/10 g
SAR *number* needs a solved coil+phantom field, which stays unlicensed
(PROJECT_PLAN §2.1). SAR-on-a-coil is not gated, `MAT-4` stays 🟡, and nothing
here changes that. The example's report text says so twice.

Every constant is imported from the gate
(`tests/validation/test_mass_averaged_sar_standard_masses.py` and
`tests/validation/test_lossy_sphere_sar.py`) — geometry, masses, both budgets,
`σ`, `ρ`, and `QUADRATURE_DEGREE` — so the example and the test cannot drift.

**Quadrature degree 16, and it is not a free parameter.** Degree 12 (the library
default) is measured *insufficient* at this ball-to-mesh ratio: 0.3008% kernel
mass error at 1 g, three times the budget. The `MAT-4` step-3 sweep picked 16 as
the smallest degree at which every ball placement sits an order of magnitude
inside the 0.1% budget.

On record at `-n 2` (`20260808T020414Z_EX-3-gate.log`, exit 0, 14 s
harness-wall / 13.4 s example-internal, 2026-08-08 21:00 slot; every figure
byte-matching the `MAT-4` step-3 gate record):

| Quantity | Exact | Measured | Bound |
| --- | --- | --- | --- |
| Closed-form SAR, `σ\|E\|²/(2ρ)` | **8.00835406e-08** W/kg | — | — |
| Pointwise SAR at the origin | closed form | agrees to **4.96e-16** | 1e-12 |
| DG0 `SAR` array, sphere-averaged | closed form | agrees to **1.32e-15** | 1e-12 |
| `SAR_avg/SAR_point`, 1 g | 1 exactly | **1.00000000** | 0.5% |
| `SAR_avg/SAR_point`, 10 g | 1 exactly | **1.00000000** | 0.5% |
| Kernel mass, 1 g | `m_avg` | **0.0120%** off | 0.1% |
| Kernel mass, 10 g | `m_avg` | **0.0044%** off | 0.1% |
| Surface-placement separation | 1/f = **2.1681** | **2.1894** (**0.98%**) | floor 1.5, ceiling ±5% |
| Mesh | — | 74 216 cells, 7.1 s | — |

The gate is `MAT-4` step 3. Both budgets — 0.5% on the identity, 0.1% on kernel
mass — are the gate's own, never tightened, never loosened.

## 2. How to run it

```
./run_examples.sh -e mri:2 -n 2 -t 180
```

**Complex build required** — the `mri:` group sources it automatically, and a
real build raises. Tier: **standard**; 14 s harness-wall on record, 7.1 s of it
meshing. There is **no solve** in this example: the field is imposed, so the
cost is entirely mesh plus quadrature.

## 3. How to analyze it, step by step

**Step 1 — the two paths to the closed form, before any averaging.** On a
uniform field `σ|E|²/(2ρ)` is known exactly, with no discretisation in it:

```
  [closed form] sigma|E|^2/(2 rho) = 8.00835406e-08 W/kg
  [point]  SAR_point(0,0,0) = ...  vs closed form [4.96e-16 relative]
  [field]  DG0 SAR averaged over the sphere = ...  vs closed form [1.32e-15 relative]
```

Both are at **round-off**, and that is the only acceptable answer here — a
uniform field has no mesh error in it, so anything above 1e-12 is an
evaluation-path defect, not a discretisation effect. The second line matters
for a different reason: it checks the **DG0 array ParaView actually colours
by**, not merely that a file was written. A rendering that disagrees with the
integrated quantity cannot ship silently.

**Step 2 — the anchor: the averaging identity at both standard masses.**

```
  [1 g]   SAR_avg = ...  SAR_point = ...  ratio = 1.00000000  [0.000% vs the 0.5% budget]
  [10 g]  SAR_avg = ...  SAR_point = ...  ratio = 1.00000000  [0.000% vs the 0.5% budget]
```

Two masses, not one, and for a reason: the 1 g ball is ~2.5× smaller in radius
than the 10 g ball, so it sees a coarser ball-to-mesh ratio and is the harder of
the two. Passing at 10 g and failing at 1 g is the signature of a quadrature
degree that no longer resolves the ball; passing at both is the identity.

**Step 3 — kernel mass conservation, which is what actually catches truncation.**

```
  [1 g]   kernel: meshed mass = ... vs m_avg 1.000000e-03 kg [0.0120% vs 0.1%]
  [10 g]  kernel: meshed mass = ... vs m_avg 1.000000e-02 kg [0.0044% vs 0.1%]
```

The ratio in step 2 can survive an averaging region that has silently truncated
at a mesh or rank boundary, because truncation removes numerator and denominator
together on a uniform field. `∫_B ρ dV` against `m_avg` does not: it says the
ball the kernel integrated over is the ball it was asked for. The printed
`V_kernel/V_exact` on the same line is the same statement in volume terms. This
check is why the quadrature degree is pinned at 16.

**Step 4 — the negative control: the 1 g ball moved to the surface.** Every
check above is satisfied by a kernel that ignores `σ(x)` entirely and just
returns the pointwise value. So the 1 g ball is re-centred on `(0, 0, R)`, where
roughly half of it lies in the lossless exterior:

```
  [control] separation = 2.1894 against the recomputed lens ceiling
            1/f = 2.1681 (f = 0.4612)  [0.98%], floor 1.5
  [control] surface ball mass ... (uniform rho, so the denominator does not move)
```

Two things are asserted, and the second is the interesting one. **Floor 1.5:**
the separation must be well above 1, because a `σ`-blind kernel returns exactly
**1.0**. **Ceiling ±5%:** it must also match the *geometrically correct* share —
a ball of radius `a` centred on the surface of a sphere of radius `R` keeps
`f = (8 − 3a/R)/16` of its volume inside, so the separation must be `1/f`. That
fraction is **recomputed for this geometry inside the example**, not carried
over from the gate. Uniform `ρ` means the denominator does not move, so the
entire 2.19× comes from the numerator losing its exterior share — which is
precisely the statement "the kernel respects `σ(x)`".

**Step 5 — open it in ParaView.**
`File → Open → examples/mri/paraview_output/mass_averaged_sar_combined.xdmf`,
then colour by `SAR` (W/kg).

1. **What to look at first:** a uniformly coloured ball in a black box. Outside
   the sphere `σ = 0`, so SAR is *identically* zero — the contrast is total, not
   gradual. That black region is the same fact as step 4's negative control.
2. **Threshold** on `CellTags` (`1` = the lossy sphere) and check the range: it
   should be a single value, `8.00835406e-08` W/kg, to display precision. A
   visible gradient inside the sphere would mean the imposed field is not
   uniform, which would invalidate every identity above.
3. The interesting picture here is deliberately boring. That is the point: the
   example gates an operator, and the operator's correctness looks like
   uniformity.

**Step 6 — what a deviation means.** Pointwise or DG0 error above 1e-12 → an
evaluation-path defect (the imposed field, the DG interpolation, or `point_sar`
itself); the mesh is not a suspect, because a uniform field has no mesh error.
Ratio off at 1 g but fine at 10 g → the quadrature degree no longer resolves the
smaller ball; check that `QUADRATURE_DEGREE` is still imported and still 16, and
do **not** relax the 0.5%. Kernel mass outside 0.1% with the ratio still
1.00000000 → the ball is truncating against a mesh or rank boundary and the
identity is hiding it. Surface separation at exactly **1.0** → the kernel is
blind to `σ(x)`; it is averaging a constant everywhere. Separation well above
1.5 but missing `1/f` by more than 5% → the kernel loses *a* share of its
numerator but not the geometrically correct one, so the ball's intersection with
the phantom is wrong. Any of these is a regression finding against `MAT-4`
step 3: report and stop.

## Related

- The gate this example runs:
  `tests/validation/test_mass_averaged_sar_standard_masses.py` (`MAT-4` step 3),
  with `tests/validation/test_lossy_sphere_sar.py` supplying the closed-form
  interior field; PROJECT_PLAN.md §7 for the records.
- The same material acting on a **solved** field instead of an imposed one — the
  contrast this pair exists to draw:
  `examples/time_harmonic/03_dielectric_sphere_in_uniform_field.py` (`th:3`,
  `TH-8`).
- Why no C95.3 or coil-SAR claim is made: PROJECT_PLAN.md §2.1.
