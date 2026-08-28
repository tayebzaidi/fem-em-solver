# `ports:4` — the birdcage's 4-port power-wave S-matrix at 10 MHz

*(`EX-32`; the §5.4 example ramp `PORT-9` ✅ owes. Complex build.)*

## 1. What this demonstrates

**The first example in this repo that solves a port on the coil.** Every other
S-parameter example drives the **two-torus** pair — `ports:1` (`EX-18`, the
gap-voltage route), `ports:2` (`EX-20`, the package sweep and its heuristic
control), `ports:3` (`EX-24`, the lumped-element sheet) — and both birdcage
examples, `EX-28` (leg gaps) and `EX-31` (ring gaps), are mesh-only. This one
puts four driven lumped-element ports on `GEO-18`'s gapped, sheeted,
phantom-loaded four-leg birdcage and reads the assembled 4×4.

What runs, in one command:

- `GEO-19` step B's mesh of the gapped + sheeted birdcage, phantom loaded
  (conductor, saline phantom, air — this fixture has **no vessel wall**);
- four ``f = 0.5`` lumped-element port sheets, one per leg, at
  ``Z_p = 50 Ω``, the termination `PORT-9` leg (d0) found by measurement;
- four driven solves through `run_n_port_sparameter_sweep`'s lumped-sheet
  route at 10 MHz, assembled into ``S`` by the **power-wave** route
  (leg (d3)) with the terminated ``Z`` retained beside it;
- one extra P1-driven solve, purely for the ParaView picture — the sweep
  returns readings, not fields.

### What it asserts

Nothing here is a render-and-hope. Every band is **imported** from the gate
modules (`ANS-1`), and the sweep itself is built by calling `PORT-9` leg (d)'s
own `build_four_port_sweep()` rather than a copy of its construction — the
`EX-33` reading of that rule, which makes the `EX-30` class of divergence (an
example restating a record the gate has since moved) impossible here by
construction.

| Reading | Band | Source |
| --- | --- | --- |
| **(i)** ``‖S − Sᵀ‖/‖S‖`` | ≤ 1e-3 | `RECIPROCITY_BAND`, step 2c's |
| **(ii)** ``σ_max(S)``, column power sums | ≤ 1 + 1e-9 | `PASSIVITY_SIGMA_TOLERANCE` |
| **(iii′)** each C4 class spread of ``Z`` | ≤ 0.5% | `ADJACENT_SPREAD_BAND` |
| **(iii′) control** pooled/worst separation | ≥ 10× | `POOLED_SEPARATION_FLOOR` |
| **anchor** P1-driven column vs leg (d0) | < 1e-9 rel. | `LEG_D0_Z_COLUMN` |

### What it read on the run that landed it

Green on the first run (`20260826T200545Z_EX-32-run1.log`, Status 0, 88 s at
`-n 2`, commit `dff04fa`). **Every gate-module record reproduced exactly** —
116 085 cells at ratio 1.000000, ``σ_max`` 0.999992805, max column power sum
0.793823974, class means 2.338160261e+01 / 1.700854304e+01 / 1.606048044e+01 Ω
with spreads 0.0553 / 0.0353 / 0.0214%, separation 166.6766×; the anchor
column misses leg (d0)'s record by 1.071e-10 … 2.568e-10 against the 1e-9
band. The heuristic control separates at 6.446452e-01 against the 2e-3 floor
and prints an **identically zero** off-diagonal.

The one reading that moved is the one the gate module declares
non-reproducible: ``‖S − Sᵀ‖/‖S‖`` = 4.183068067e-13 here against its recorded
~2.152e-14 — same construction, same mesh, every other digit bit-identical.
That is the (d3c) rule earning its keep rather than a divergence: both sit
about eleven decades under the 1e-3 gate.

The reciprocity residual is printed **as an order of magnitude only**. That is
the (d3c) rule: power-wave reciprocity on this fixture is noise over noise
(leg (d) records 2.152e-14 on this mesh, 2.049e-14 on the pre-step-B one), so
no digit of it is a record and the example gates only on the imported 1e-3
band, with a floor under it to catch a suspiciously exact matrix.

### The negative control

The deprecated `PORT-0` coupling heuristic is run on the same problem and the
same mesh, its `DeprecationWarning` is shown, `is_placeholder` is asserted
**True**, and its S-matrix is asserted to be separated from the field-derived
one by more than 2e-3 (the `EX-20` floor and rationale).

It is handed the **gap-box halves** rather than the port sheets, because it
validates terminal tags against *cell* tags and has never known what a port
sheet is. That is as much of the control's content as the numbers: the retired
route reads regions and a ring-distance rule, the gated route reads a field.

### Scope — read this before quoting a number

**10 MHz only**, the port model's frequency. No Larmor frequency, no
resonance, no tuning claim, and no loaded-coil claim: 64/128 MHz is `PORT-11`,
and nothing in this example licenses a figure there. The feed systematics on
record are the two-torus ones (PROJECT_PLAN §2.2). The cell count is a
**print**, never an assert — the mesh regenerates whole.

## 2. How to run it

```
./run_examples.sh -e ports:4 -n 2 -t 400
```

The runner sources the complex DolfinX build for the `ports:` group
automatically. Standard tier; budget ~400 s of container time at `-n 2`.

Through the logging harness, as every verification run must be:

```
scripts/testing/run_and_log.sh EX-32 "docker compose exec -T fem-em-solver \
  bash -lc 'cd /workspace && ./run_examples.sh -e ports:4 -n 2 -t 400'"
```

## 3. How to analyze it, step by step

1. **Check the fixture first.** The `[sweep]` line prints the cell count
   against `GEO-19` step B's record and the ratio between them. A ratio that
   is not 1.000000 means the mesh moved, and every record below is measured on
   a different structure than the one the gates were taken on — that is a
   finding for `GEO-19`, not a reason to re-record here.

2. **Read the anchor before the gates.** The `[anchor]` block compares the
   P1-driven column of ``Z`` with leg (d0)'s recorded terminated column at
   1e-9 relative. This is what makes the network claim comparable to the
   one-column record: if it misses, the 4×4 is not built on the solve that
   record came from and nothing after it means what it says.

3. **Then the three gates, in order.** `[gate i]` prints the reciprocity
   decade; `[gate ii]` prints all four singular values and all four column
   power sums beside the `PORT-5` metrics computed independently inside the
   package; `[gate iii']` prints the three circulant classes of ``Z`` — self,
   adjacent (90°), opposite (180°) — with their means, their spreads, and the
   pooled-vs-worst separation.

   The separation is the one to look at hardest. A C4 gate that passes because
   *every* off-diagonal happens to be close is a consistency check, not a
   symmetry measurement; the separation says the reading resolves the
   adjacent/opposite structure rather than passing on noise.

4. **The control.** `[control]` prints the heuristic 4×4, its warnings, and
   `max|S_heuristic − S_field|`. The heuristic matrix is the shape of the
   thing this whole line of work replaced: a ring-distance rule with no field
   in it. The separation is orders of magnitude above the floor, which is the
   point — the two are not the same kind of object.

5. **The picture.** Open
   `paraview_output/ports_04_birdcage_four_port_sparameters_combined.xdmf`:

   - colour by `E_magnitude` and clip to see the driven leg's gap;
   - colour by `B_magnitude` (DG0, ``B = ∇×E/(−jω)`` from Faraday's law) for
     the field the coil exists to make;
   - threshold `CellTags` to isolate the conductor and the phantom.

   Then open `paraview_output/ports_04_birdcage_four_port_sparameters_facets.xdmf` and
   threshold `mesh_tags` on 211–214 to see the four port sheets the
   lumped-element boundary condition lives on. Only port 1 is driven in the
   exported case; the other three sheets are in the operator and terminated,
   which is why the field is not C4-symmetric even though ``Z`` is circulant.

## Related

- `ports:3` (`EX-24`) — the lumped-element port sheet itself, on the two-torus
  fixture: the width ladder that gated ``f = 0.5``.
- `ports:2` (`EX-20`) — the package sweep and the heuristic control pattern
  this example reuses.
- `mesh:3`, `mesh:7`, `mesh:8` — the birdcage meshes, including the 16-leg
  build (`EX-33`) that has no solve behind it.
- PROJECT_PLAN.md §2.2 for what an S-parameter figure from this repo does and
  does not claim; §7 `PORT-9` for the gates, `PORT-11` for the Larmor
  frequencies.
