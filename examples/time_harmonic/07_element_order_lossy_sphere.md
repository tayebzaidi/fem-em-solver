# EX-25 — element order as an accuracy knob: N1curl degree 1 vs degree 2

Every other example in this repository solves at **element order 1**. That is a
habit, not a choice: `TimeHarmonicSolver(problem, degree=2)` has existed since
`TH-1` and was first gated on 2026-08-18 (`TH-12` step 1). This example is that
capability made runnable — the **discretization** angle no other example covers.

## What this demonstrates

`TH-10`'s lossy saline sphere (`a = 0.05 m`, `εᵣ = 78`, `σ = 0.5 S/m`, in a
0.2 m box, wall-driven by the exact full-wave series total field) at 64 MHz, on
the **coarse** rung of its own ladder — 5 866 cells. One run solves that *same
mesh* twice, once at each element order, and prints the accuracy-per-cost table
side by side.

The point is that the two orders are not two nearby answers:

| order | cells | DOFs | interior relL2 | ohmic-power error | `\|Im P\|/Re P` | solve wall | peak RSS |
|---|---|---|---|---|---|---|---|
| 1 | 5 866 | 7 591 | 8.1541% | 8.3869% | 0.000e+00 | 3.75 s | 376.8 MiB |
| 2 | 5 866 | 39 634 | **0.1405%** | **0.0058%** | 0.000e+00 | 7.59 s | 1032.8 MiB |

The ohmic power is the volume integral a SAR number routes through, so this is
the accuracy axis the MRI slice actually cares about — and it improves by
1 444× on an unchanged mesh.

The fixture is *imported* from the gates that closed it
(`tests/validation/test_lossy_sphere_degree2.py`, and through it
`tests/validation/test_lossy_sphere_fullwave.py`) — the rung, the probe cloud,
the `LossySphereSeries` reference, the power machinery, the degree-1 records and
every bound. The example and the gate cannot drift apart.

**Scope:** the sphere fixture, one frequency, one rung. **No production-order
claim** — that decision belongs to the weekly review under `TH-12`'s decision
clause — no coil, no mass averaging, no SAR wording.

## How to run it

```bash
./run_examples.sh -e th:7 -n 2 -t 400
```

The `th:` group sources the complex DolfinX build automatically; a real build
raises immediately. Measured cost at `-n 2`: **13.4 s** in-script, 16 s wall
(`docs/testing/logs/20260819T140334Z_EX-25-example-n2.log`, exit 0) — two mesh
builds and two solves, the degree-2 solve dominating at 7.59 s.

## How to analyze it, step by step

### 1. Read the table across, not down

Both rows are the *same 5 866 tetrahedra*. Nothing about the geometry, the
material, the boundary data or the probe cloud differs between them; the only
change is the element. So the 58× move in `relL2` is attributable to the
discretization and to nothing else — which is the whole reason this example
exists on a fixture with a closed form.

### 2. Check the negative control — it *is* the capability statement

```
[control] degree 1 misses the degree-1 fine-rung record (8.1541% > 3.643% at 17670 cells)
          while degree 2 beats it on 5866 cells (0.1405%) — 3.01x fewer cells at 25.9x the accuracy
```

This is the `EX-18` inverted-assertion pattern, and both halves are asserted.
The *miss* is what makes the beat mean something: without asserting that degree
1 on this rung fails to reach the fine rung's 3.643%, "degree 2 reaches
fine-rung accuracy on a coarse mesh" would be indistinguishable from "this rung
was always that good". `TH-12` step 1 gated exactly this pair; the example
re-executes it rather than quoting it.

### 3. Read the cost line honestly

```
[cost] degree 2 buys 58.0x the field accuracy and 1444x the power accuracy for
       5.22x the DOFs, 2.02x the solve wall and 2.74x the peak RSS
```

Sublinear in DOFs on both cost axes — the good case. **Do not generalize it.**
`TH-12` step 2 ran the same order change on the *coil* fixture and measured
~20× the solve wall for 5.42× the DOFs, at 61.94 GiB summed peak RSS, i.e.
96.8% of the container's memory cap. Element order is cheap here and expensive
there; the production-order decision needs both numbers and is not made by this
example.

Two instrument notes worth carrying:

* peak RSS is **summed `ru_maxrss` over ranks**, not `/sys/fs/cgroup/memory.peak`
  — that file is the container's *lifetime* high-water mark and is not
  resettable from inside a run, so on a box where a `TH-11`-scale job has
  already touched the cap it reads 64 GiB for everything afterwards and measures
  nothing (`TH-12` step 1's substitution).
* the solve wall includes mesh generation and assembly, not just the MUMPS
  factorization, so the 2.02× here is a coarser number than step 1's 4.32× on
  the solve alone. Both are on this log; neither is gated.

### 4. Check the identity line

```
[identity] |Im P|/Re P = 0.000e+00 (degree 1) and 0.000e+00 (degree 2)
```

`½σE·conj(E)` is real by construction — `ufl.inner` conjugates its second
argument — so a nonzero imaginary ohmic power is the signature of a conjugation
slip in the assembled form (the `TH-1` `ufl.dot` trap), at either order. It
reads exactly 0.0 here, against the family's unchanged 1e-9 bound.

This fixture is **not** subject to the degree-2 complex-power identity defect
`TH-12` step 2 found on the coil (`W_e` exploding 3.5e7× through the ungauged
gradient null space): the identity `Im Z = 4ω(W_m − W_e)/I′²` needs a driven
port, and this fixture has no source at all — it is driven by imposed Dirichlet
total field. See the known-issues entry before reading across.

### 5. Open both XDMF files together

```
examples/time_harmonic/paraview_output/element_order_sphere_degree1_combined.xdmf
examples/time_harmonic/paraview_output/element_order_sphere_degree2_combined.xdmf
```

In the **complex build** the DolfinX XDMF writer splits every attribute into
`real_<name>` / `imag_<name>` — correct writer behaviour, and the reason the
field names in ParaView are `real_E_magnitude`, `real_E_real`, `imag_E_imag`,
`real_CellTags` and so on (see the `OPS-21` known-issues entry; a test that
hard-codes the real-mode names is the build-mode-blind one, not the writer).

Colour by `real_E_magnitude` and `Threshold` on `real_CellTags` (1 = sphere,
2 = surrounding box) to isolate the saline. Both files export through the *same*
CG1 vector space on the *same* tetrahedra — N1curl cannot be carried by XDMF at
any order — so the pictures are directly comparable, and the degree-1 interior
carries its 8% error as faceting the degree-2 interior does not have.

## What would make this example fail

* **A drift outside the 1% reproduction band** on any of the four records
  (relL2 and power error at each order). The example runs the gate's fixture on
  the gate's mesh at the gate's rank count, so agreement to round-off is
  expected; measured drifts on the recorded run are 4.0e-06 / 1.2e-05 (degree 1)
  and 5.5e-05 / 1.5e-03 (degree 2). A drift larger than the band means the
  example path and the gate are no longer the same computation — a finding about
  one of them, not a band to widen.
* **A DOF count that moves.** 7 591 and 39 634 are deterministic given the mesh
  and the order, and are asserted exactly; a move means the space is not the one
  `TH-12` step 1 priced.
* **A cell count other than 5 866**, which would mean the fixture moved under
  the records and nothing else in the run is comparing against what it names.
