# EX-26 — the Poynting power-balance audit: where the watts go

Every other example in this repository reports a **field** — a magnitude, an
error against a closed form, an S-parameter, a mesh. None of them audits
**power**. This one does, and power is the output quantity the MRI-RF-safety
slice ultimately routes through: SAR is a volume power integral, coil loading is
a resistance, and both are only as trustworthy as the solve's power accounting.

## What this demonstrates

`fem_em_solver.post.poynting_power_balance` — gated by `POST-3` (2026-07-31) and
extended by `POST-5` step 4 (2026-08-19) to the **driven** case. Poynting's
theorem for `e^{+jωt}` phasors, real part:

```
−∮ ½Re(E×H̄)·n̂ dS  =  ½∫σ|E|²dV  +  ½Re∫E·J̄ dV
   boundary flux        Ohmic loss     impressed source
```

The run audits **two fixtures**, chosen because they sit on opposite sides of the
distinction that third term makes.

### The driven cylinder — three terms

The time-harmonic smoke fixture: an axial `J = ẑ A/m²` in the inner conductor of
a saline cylinder (`σ = 0.7 S/m`, `εᵣ = 78`, 127.74 MHz, 1 405 cells at
`h = 0.03 m`, roughly 9 cells per in-medium wavelength).

| term | value |
|---|---|
| boundary flux `−∮½Re(E×H̄)·n̂ dS` | −2.008179e−07 W |
| Ohmic loss `½∫σ|E|²dV` | 1.199162e−06 W |
| impressed source `½Re∫E·J̄ dV` | −1.199162e−06 W |
| reactive flux (reported, not scored) | 1.616955e−07 var |
| **residual, three-term** | **16.7465%** — inside the unmoved 25% band |
| residual, two-term | 116.7465% — asserted to *miss* that band |

### The `TH-6` plane wave — two terms

The lossy plane wave in a 0.1 m box at 12³ (10 368 cells), wall-driven by the
exact closed form. `J = 0` everywhere, so the source-free two-term identity is
the right one and is the stronger check.

| term | value |
|---|---|
| boundary flux | 1.140318e−04 W |
| Ohmic loss | 1.241984e−04 W |
| **residual** | **8.185716%** |
| boundary leg vs *its own* closed form | 8.1205% (band 10%) |
| Ohmic leg vs *its own* closed form | 0.0711% (band 10%) |

Everything gated is **imported** from the tests that closed it
(`tests/solver/test_time_harmonic_smoke.py`,
`tests/validation/test_poynting_balance.py`, and the `TH-6` module beneath it):
the fixtures, the drives, the bands, the σ-blind separation factor and the
analytic legs. Only the residuals the gates hold as *printed* output rather than
as named constants are restated in the script, with provenance and unloosened.

**Scope:** a demonstration of the audit, not an explanation of it. The driven
fixture's remaining 16.7465% is quoted as gated, not explained. No SAR number, no
coil, no loading claim, and no band moves.

## How to run it

```bash
./run_examples.sh -e th:8 -n 2 -t 400
```

The `th:` group sources the complex DolfinX build automatically; a real build
raises immediately. Measured cost at `-n 2`: **4.7 s** in-script, 8 s wall
(`docs/testing/logs/20260820T170422Z_EX-26-example-n2.log`, exit 0) — two solves,
both small. That is a **smoke**-tier cost against a commission written for
standard; the compute is two coarse fixtures the gates already priced at 8 s and
152 s, and the 152 s belonged to the `TH-6` file's *other* tests (the 24³ rung
and the piecewise-σ / piecewise-μᵣ families), not to the 12³ rung this example
audits.

## How to analyze it, step by step

### 1. Read the driven table as a sum, not as three numbers

`−2.008179e−07 = 1.199162e−06 + (−1.199162e−06)` to within 16.7% of the largest
term. The impressed source is **negative**: the field does work *on* the source,
which is what an interior driven current in a lossy medium looks like when the
Ohmic loss is being supplied from inside rather than through the wall. The
boundary flux is small and negative — real power leaves this box — and that is
not a defect here, because the theorem forbidding it (`net inward > 0` on a
passive box) is a theorem *only for a source-free domain*. That sentence used to
be in the helper's docstring without the qualifier, and it was false as written;
the `POST-5` step-4 entry records the correction.

### 2. Check the negative control — it *is* the capability statement

```
[control] the SAME solved field scored two ways: three-term 16.7465% (inside the
          unmoved 25% band) against two-term 116.7465% (asserted to miss it) —
          the impressed source carries 100.0% of the largest term in the
          identity, so omitting it is not a correction, it is the whole reading
```

This is the `EX-18` inverted-assertion pattern, and both halves are asserted. The
two-term reading of the *same solved field* stays computable by design
(`two_term_relative_imbalance`), and asserting that it **fails** the very band the
three-term reading passes is what makes "the missing source term was the whole
imbalance" a measurement rather than a story. It is also the history of this
fixture: the gate carried that 116.7465% as a strict `xfail` from 2026-08-17
until `POST-5` step 4, while three separate discriminators (an h-ladder, a closed
azimuthal drive, a per-leg closed-form scoring) each excluded a candidate cause.
What was wrong was the identity, not the solve.

### 3. Check the second control — the audit is sensitive to the physics

```
[control] sigma-blind (lossless medium, same field): volume leg exactly 0.0 W,
          residual 83.2535% = 4.97x the honest reading, against the
          pre-registered 3.0x floor
```

Score the same field as if the medium were lossless and the volume leg vanishes
*identically* — `0.0 W`, not twelve orders down. A loose band (25%) means nothing
without this: the σ-blind reading must be rejected by the band the honest solve
passes, and by a factor. The 3.0× floor is `POST-5` step 4's, re-derived for the
three-term score; note the arithmetic ceiling is 5.97× (with the volume leg
forced to zero the residual is `|flux − source|/max(|flux|,|source|) ≤ 1`, capped
by the honest solve's own 16.7465%), so the measured 4.97× sits between the floor
and the ceiling with no room for a coincidence.

### 4. Read the plane-wave legs, then the `J = 0` control

On the source-free fixture each leg is scored against **its own** closed form,
not just against the other leg:

```
[legs] analytic flux = 1.241101e-04 W, analytic dissipation = 1.241101e-04 W
       (equal identically, by 2*alpha*beta = omega*mu0*sigma)
  boundary flux error 8.1205%, Ohmic loss error 0.0711%, band 10%
```

The volume leg is the *control* for the boundary leg: a boundary-leg reading
attributes nothing unless the volume leg hits its own closed form first. Both are
asserted. This is what says the 8.185716% residual is the boundary curl trace's
discretisation error rather than two wrong legs cancelling — and by extension it
is why the driven fixture's 16.7465% is quoted as discretisation too.

Then:

```
[control] J = 0 passed explicitly: source term 0.0 W exactly, and all 7 other
          quantities bit-identical to the source-free call (8.185716% both ways).
```

Passing an explicit zero drive to the extended helper must move **no digit** of
a source-free solve, and must report exactly `0.0` W rather than round-off. The
zero is a `fem.Constant`, not a literal `ufl.as_vector` of zeros — a literal folds
to a domain-less UFL zero which the helper short-circuits, and the point of the
control is that the integral is *assembled* (known-issues 2026-08-17, `OPS-17`
step-2 defect 4). This is what keeps "the source term explained the driven
fixture" a statement about drives rather than a licence the helper now grants
every solve.

### 5. Open the XDMF and glyph the power flow

```
examples/time_harmonic/paraview_output/time_harmonic_08_poynting_audit_driven_smoke_combined.xdmf
examples/time_harmonic/paraview_output/time_harmonic_08_poynting_audit_th6_plane_wave_combined.xdmf
```

In the **complex build** the DolfinX XDMF writer splits every attribute into
`real_<name>` / `imag_<name>` — correct writer behaviour, and the reason the
ParaView field names are `real_E_magnitude`, `real_B_real`, `real_S_poynting` and
`real_CellTags` (see the `OPS-21` known-issues entry).

`real_S_poynting` is the real Poynting vector `½Re(E×H̄)` — the integrand of the
boundary leg, exported over the whole volume. It is a **cell** field, not a vertex
one, because `curl E` of a degree-1 N1curl field is cell-wise constant and
smoothing it onto vertices would be inventing resolution the solve does not have;
`real_B_real` is exported the same way, from the same `curl E`. Apply a `Glyph`
filter to `real_S_poynting`: on the plane-wave box the arrows point inward through
the wall everywhere (the box absorbs), and in the driven cylinder they point away
from the conductor — which is the sign structure the table in step 1 is summing.

## What would make this example fail

* **A drift outside the 1% reproduction band** on any of the eight records (the
  driven fixture's three terms and two residuals; the `TH-6` residual and two leg
  errors). Measured drifts on the recorded run are 1.4e−06 / 2.0e−07 / 3.4e−07 /
  1.1e−07 / 3.4e−07 (driven) and 3.7e−08 / 5.4e−06 / 3.0e−04 (`TH-6`). The example
  runs the gates' own fixtures on the gates' own meshes at the gates' own rank
  count, so a drift this large means the example path and the gate are no longer
  the same computation — a finding about one of them, not a band to widen.
* **The two-term reading falling inside the 25% band** on the driven fixture. The
  two identities would have stopped being distinguishable and the example would
  demonstrate nothing.
* **The σ-blind separation dropping under 3.0×**, which would mean the audit is
  not sensitive to the loss it is accounting for.
* **A `TH-6` cell count other than 10 368**, or a non-zero source term at
  `J = 0`, or any of the seven other dict keys moving between the source-free and
  zero-drive calls.
