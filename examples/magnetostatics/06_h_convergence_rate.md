# `-e 6` — measured h-convergence rate of the straight-wire solve

Guide for `examples/magnetostatics/06_h_convergence_rate.py`. Written to be
followed without the source open.

## 1. What this demonstrates

**A convergence rate**, which no other example outputs. Every other
magnetostatics example reports an error at one mesh, and a single error cannot
tell you whether the discretisation is converging or has hit a modeling floor
it will never improve past. For that you need the error at several resolutions
and the slope through them.

Three meshes at h = 4.0 / 2.5 / 1.8 mm, each solved with the analytic vector
potential imposed on the outer wall (`MAG-13`, `exterior_dirichlet_bc`); `|B|`
sampled on the same ten-point line at the midplane, `2a ≤ x ≤ 0.8·R_domain`;
the error against `μ₀I/2πr` fitted as the least-squares slope of `log(error)`
against `log(h)`. Three points, not two: two points fit any slope exactly, so a
two-resolution "rate" is not a measurement.

The outer boundary condition is what makes this a gate at all. With the natural
condition `n × H = 0` the continuum limit is *not* the analytic field — the wall
forces the very azimuthal component being compared to zero, contradicting
Ampère's law for a net axial current — so the error plateaus at a modeling floor
and the fitted rate decays toward zero as h shrinks. That is the failure mode
this example is shaped to make visible.

The fixture is **imported** from the module that closed `MAG-13`
(`tests/validation/test_convergence.py`) — parameters, the per-resolution solve,
the sample line and the rate fit itself — never restated here. The example and
the gate therefore run the same measurement, not two copies of it.

On record at `-n 2` (`20260810T124317Z_EX-9-run-final.log`, 2026-08-10):

| h (m) | Cells | Rel. L2 error | `MAG-13` record |
| --- | --- | --- | --- |
| 0.0040 | 38 750 | **22.1925%** | 22.19% |
| 0.0025 | 145 884 | **12.7485%** | 12.75% |
| 0.0018 | 383 248 | **9.2568%** | 9.26% |

| Quantity | Value | Bound |
| --- | --- | --- |
| Fitted rate `p` | **1.1009** | `0.7 < p < 1.5` (`MAG-13` gate; 1.10 on record) |
| Monotone decrease, coarse → fine | holds | asserted (negative control) |
| Error of the *exported* CG1 field | **17.1451%** | < coarsest solved, 22.1925% |
| Elapsed | 130 s (three solves) | heavy tier |

The gate is `MAG-13` (✅ 2026-07-30, `20260730T125522Z_MAG-13.log`). This
example closes nothing; it is Phase-1 §5.4 backfill. N1curl degree 1 predicts
~1.0 for this quantity, and the measured 1.1009 reproduces the record to four
digits.

## 2. How to run it

```
./run_examples.sh -e 6 -n 2 -t 600
```

Real DolfinX build; the runner selects it. Magnetostatics does not solve in the
frequency domain, so do **not** source the complex mode for it. Tier: **heavy**
— §5.1 names convergence studies explicitly, and `MAG-13` is a heavy-tier chunk.
130 s at `-n 2`, dominated by the 383 k-cell mesh (~47 s of Netgen optimisation
alone) and its solve. Exit status 0 and every assertion holds, or the run fails
loudly; it never merely renders.

**Do not add a fourth resolution.** The triple is chosen, not convenient: at
h = 0.005 (23.2 k cells) the error is 30.34% because 5 mm cells cannot resolve
the 3 mm wire — a geometry-resolution artifact that inflates the fitted rate —
and at h = 0.0035 (61.3 k) the error is 11.77%, *below* the h = 0.0025 value,
because cell-wise constant `curl(A)` gives each resolution O(h) sampling noise.
A sequence containing 0.0035 is non-monotone and fails the negative control
below for a reason that has nothing to do with the solver.

## 3. How to analyze it, step by step

**Step 1 — read the table top to bottom before looking at the rate.**

```
    h (m)      cells   rel L2 error   MAG-13 record     log h   log err
   0.0040      38750      22.1925%         22.19%   -5.5215   -1.5054
   0.0025     145884      12.7485%         12.75%   -5.9915   -2.0598
   0.0018     383248       9.2568%          9.26%   -6.3200   -2.3798
```

The middle column against the fourth is the reproduction check: this run agrees
with the `MAG-13` record to every digit that record carries. The last two
columns are the fit's actual inputs — the rate is a straight line through those
three `(log h, log err)` pairs, and you can check it by hand: the slope from the
first to the last point is `(−2.3798 + 1.5054)/(−6.3200 + 5.5215) = 1.095`.

**Step 2 — the monotone decrease, which is the negative control.** The three
errors must fall coarse to fine, and the example asserts it. This is the check a
solver blind to `h` fails: an implementation whose error is dominated by
something other than the mesh still produces *some* least-squares slope, and
that slope can land inside the band by accident. Only a systematic decay makes
the fitted number mean "convergence". Note that this control is solved here,
not cited — the three solves are the run.

**Step 3 — the rate against its band.**

```
  fitted rate  : 1.1009   (band 0.7 < p < 1.5, MAG-13 gate; 1.10 on record)
```

The lower edge catches loss of convergence. The **upper edge matters just as
much**: a rate well above 1.5 is not "better than theory", it means one
resolution in the sequence is anomalous — a mesh whose cells happen to straddle
the sample points favourably — and the band is two-sided precisely because the
older `rate > 0.5` check would have kept passing while the fixture drifted.
1.1009 against a theoretical 1.0 for N1curl degree 1 is the expected result; the
0.1 excess is the O(h) sampling noise described in step 1's discussion.

**Step 4 — what the export costs, which this example measures rather than
assumes.**

```
  exported fld : 17.1451% at the same points (solved field 9.2568%,
                 CG1 smoothing costs +7.8884%; must stay under the
                 coarsest solved resolution 22.1925%)
```

`curl(A)` is cell-wise constant for N1curl degree 1, so writing `B` to a
continuous CG1 space averages neighbouring cells at each vertex. On a 1/r field
near a conductor that averaging costs **7.89 percentage points** of accuracy —
most of what the whole refinement sequence bought. This is a property of the
export, not of the solve, and it is the reason the picture is not the
measurement. The assertion bounds it by the run's own coarsest resolution: if
smoothing ever costs more than 2.2× of refinement gained, what ParaView shows
misrepresents the sequence. Do not read the exported field as if it were the
9.26% one.

**Step 5 — open the field in ParaView.**
`File → Open → paraview_output/h_convergence_rate_combined.xdmf` — one grid at
the finest resolution carrying `CellTags` (1 = wire, 2 = air) and `B_numeric`.

1. **Stream Tracer** or **Glyph** on `B_numeric`. What to look at: azimuthal
   loops around the wire, magnitude falling as 1/r outside the conductor.
2. **Plot Over Line** from `(0.006, 0, 0)` to `(0.024, 0, 0)` — the sample
   window itself. What to look at: a smooth 1/r decay. Steps or staircasing in
   this curve are the vertex averaging of step 4 made visible, not a solver
   defect.
3. **Threshold** on `CellTags = 1` to isolate the conductor. The closed form is
   deliberately **not** exported beside the numeric field: it is the exterior
   wire solution, valid only for `r > a`, so interpolating it over the whole
   domain would put a 1/r singularity on the axis and an invalid comparison
   inside the wire — the most colourful region of the picture would be the one
   the measurement excludes on purpose.

**Step 6 — what a deviation means.** A rate below 0.7 with the errors still
monotone → the boundary condition, first: check that `exterior_dirichlet_bc` is
being applied, because the natural condition produces exactly this signature.
A rate above 1.5, or a non-monotone sequence → one resolution is anomalous;
report it against `MAG-13` rather than adjusting the triple, since the triple is
itself a measured choice. Errors that no longer match the fourth column → the
fixture has drifted (mesh generator, source term, sample line), and the rate
being in-band does not excuse it. Any of these is a regression finding against
`MAG-13`: report and stop, do not move the band.

## Related

- The gate this example runs: `tests/validation/test_convergence.py`
  (`MAG-13`), and PROJECT_PLAN.md §7 for its record.
- The same wire compared against the closed form at one resolution:
  `examples/magnetostatics/01_straight_wire.py`.
- The same wire solved two ways instead of at three resolutions:
  `examples/magnetostatics/05_gauge_cross_check.py`.
- ParaView workflow for this group: `examples/magnetostatics/PARAVIEW_GUIDE.md`.
- Combined-file layout: `examples/magnetostatics/COMBINED_XDMF_README.md`.
