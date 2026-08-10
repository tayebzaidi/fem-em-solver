# `-e 5` — gauge cross-check: penalty vs Lagrange-multiplier Coulomb gauge

Guide for `examples/magnetostatics/05_gauge_cross_check.py`. Written to be
followed without the source open.

## 1. What this demonstrates

**Formulation cross-validation**, which no other example does. Every other
magnetostatics example compares one formulation against a closed form; this one
solves the *same* fixture on the *same* mesh two different ways and asks whether
they agree.

The curl-curl operator has a gradient null space, and the two implemented
treatments of it are genuinely different computations:

- `GaugeMethod.PENALTY` (the default) adds `gauge·(div A, div v)`. That **prices**
  the null space rather than removing it: the potential keeps a gradient
  component of size ~1/gauge, and `B = curl(A)` survives only by cancellation.
- `GaugeMethod.LAGRANGE` solves the (A, p) saddle point in N1curl × H1, enforcing
  `div A = 0` weakly. The null space is **removed**.

So the two solves disagree about `A` by eleven orders of magnitude while agreeing
about `B` to four decimal places — and that is the point. Agreement between two
paths that share a discretisation but not a null-space treatment is evidence a
closed-form comparison cannot give you, because a modeling floor (this fixture
carries one: a PMC side wall and a source with `J·n ≠ 0` on the end caps) hides
gauge defects inside its own error budget.

The fixture is **imported** from the module that closed `MAG-15`
(`tests/solver/test_gauge_lagrange.py`) — geometry, resolution and the same eight
sample points — never restated here.

On record at `-n 2` (`20260810T110311Z_EX-10-run1.log`, 2026-08-10):

| Quantity | Value | Ceiling |
| --- | --- | --- |
| Mesh | **14 055 cells** (h = 0.006 m) | — |
| Probe-point vector L2 rel. difference `‖B_lag − B_pen‖/‖B_pen‖` | **0.0004%** | 5% (`MAG-15` gate) |
| Volume L2 rel. difference of the *exported* fields | **0.0033%** | 5% |
| max&#124;A&#124;, penalty | **5.073e+01** | — |
| max&#124;A&#124;, Lagrange | **1.407e-09** | — |
| Ratio Lagrange/penalty | **2.774e-11** | 1e-6 (`MAG-15` gate) |
| Multiplier spread (Lagrange) | **2.083e+02** | reported, not asserted |
| Multiplier spread (penalty) | **nan** (no multiplier exists) | asserted `nan` |
| Solve time | 0.5 s penalty, 2.3 s Lagrange | — |

The gate is `MAG-15` (✅ 2026-07-28, `20260728T193524Z_MAG-15.log`): both gauges
give an identical analytic error to 4 significant figures at h = 0.003, and
max&#124;A&#124; is 1.6e-09 (Lagrange) against 5.2e+01 (penalty). The rel-diff scalar
itself is **not** printed in that log — the 0.0004% above is this example's own
contribution to the record. This example closes nothing; it is Phase-1 §5.4
backfill.

## 2. How to run it

```
./run_examples.sh -e 5 -n 2 -t 180
```

Real DolfinX build; the runner selects it. Magnetostatics does not solve in the
frequency domain, so do **not** source the complex mode for it. Tier:
**standard**, but the case is deliberately coarse — 5.1 s in the example, 8 s of
harness wall on the 2026-08-10 record. Exit status 0 and every assertion holds,
or the run fails loudly; it never merely renders.

## 3. How to analyze it, step by step

**Step 1 — read the two `max|A|` lines first, before any agreement number.**

```
  penalty   solve 0.5 s   max|A| = 5.073e+01   multiplier spread = nan
  lagrange  solve 2.3 s   max|A| = 1.407e-09   multiplier spread = 2.083e+02
```

This is the negative control, and it comes first because it establishes that the
two solves are not the same computation. Eleven orders of separation is the
null-space component the penalty path leaves in `A` and the saddle point removes.
If this ratio ever climbs toward the 1e-6 bound, **stop reading the agreement
numbers** — they would be two copies of one answer, and their agreement would
prove nothing.

**Step 2 — the probe table.** Eight points on the x axis from `2a = 0.006 m` out
to `0.4·R_domain = 0.012 m`, outside the conductor and inside the window the
outer wall perturbs least. On record every point agrees to 0.000% displayed, and
the vector L2 difference over all eight is **0.0004%** against the gate's 5%
ceiling. Note the two outermost points read `6.70e-06` / `6.48e-06` against
`1.311e-05` inside — that step is a property of the coarse fixture (h = 0.006 m
is the sampling window's own width), identical in both gauges, and therefore
invisible to this cross-check by construction. This example measures *agreement*,
not accuracy; `-e 1` and `MAG-13` are where the straight wire is compared to
`μ₀I/2πr`.

**Step 3 — the volume number, which is the one that covers ParaView.** Eight
points on one line agreeing says little about the field you are about to colour.
The run therefore re-measures agreement as an integral over the whole domain,
`sqrt(∫|B_lag − B_pen|² dx / ∫|B_pen|² dx)`, computed on the *exact CG1 functions
written to the XDMF file* — **0.0033%** on record. Both integrals are allreduced
before the division; a rank-local ratio would be silently wrong at `-n 2`. That
this is 8× the probe figure and still four orders inside the ceiling is the
expected ordering: the volume norm includes the conductor interior and the wall
region, where the probes never look.

**Step 4 — the multiplier spread, as a diagnostic only.** `nan` for penalty is
asserted (there is no multiplier to report, and a number there would mean the
diagnostic has stopped distinguishing the formulations). The Lagrange value
`2.083e+02` is finite and non-zero **by design**: the wire terminates on the
domain end caps, so `J·n ≠ 0` and the source is incompatible with the curl-curl
operator. The multiplier absorbs exactly that component. It is mesh-dependent, so
it is printed and never pinned — do not turn it into an assertion.

**Step 5 — open the fields in ParaView.**
`File → Open → paraview_output/gauge_cross_check_combined.xdmf` — one grid
carrying `CellTags` (1 = wire, 2 = air), `A_penalty`, `A_lagrange`, `B_penalty`,
`B_lagrange` and `B_difference`.

1. **Glyph** on `A_penalty`, then on `A_lagrange`, with the colour scale rescaled
   for each. What to look at: they look nothing alike, and the scale bars differ
   by ~11 orders. This is the picture of step 1.
2. **Glyph** or **Stream Tracer** on `B_penalty` and `B_lagrange`. What to look
   at: azimuthal loops around the wire, indistinguishable between the two. This
   is the picture of steps 2–3.
3. **Calculator** `mag(B_difference)` (the field is written directly, so no
   subtraction filter is needed). What to look at: the residue must be smooth and
   concentrated near the conductor surface and the outer wall — the two places
   the discretisation is worst. Structured residue *in the open air region*, away
   from both, is the diagnostic to worry about: it would mean one of the two
   solves is carrying a spurious field the other is not.
4. **Threshold** on `CellTags = 1` to isolate the wire if you want the interior;
   the cross-check itself is valid everywhere, unlike the analytic comparisons in
   `-e 1` and `-e 2`.

**Step 6 — what a deviation means.** Probe agreement degrading while the volume
number holds → a point-location problem, not physics (evaluation must go through
`post.evaluation.evaluate_vector_field_parallel`). Both agreement numbers
degrading together while the `max|A|` ratio stays tiny → a real discretisation
difference between the two formulations, which is a `MAG-15` regression and
should be reported, not tuned away. The `max|A|` ratio rising → the multiplier
equation has stopped constraining `A`; the Lagrange path is no longer usable as a
cross-check at all.

## Related

- The gate this example demonstrates: `tests/solver/test_gauge_lagrange.py`
  (`MAG-15`), and PROJECT_PLAN.md §7 for its record.
- Same fixture, compared against the closed form instead:
  `examples/magnetostatics/01_straight_wire.py`.
- ParaView workflow for this group: `examples/magnetostatics/PARAVIEW_GUIDE.md`.
- Combined-file layout: `examples/magnetostatics/COMBINED_XDMF_README.md`.
