# `-e th:2` — PEC cavity resonances: solved eigenfrequencies vs the closed form

Guide for `examples/time_harmonic/02_pec_cavity_resonances.py`. Written to be
followed without the source open.

## 1. What this demonstrates

**The first example in this repository that solves an eigenproblem** rather than
a driven problem. Every earlier example — including `th:1`, the first
time-harmonic one — imposes a source or boundary data and solves for the
response. This one asks the geometry what frequencies it supports and gets them
back. That is the primitive Phase 6 tunes the birdcage with.

A lossless, source-free box bounded by a perfect electric conductor supports the
modes of

```
∫ (∇×E)·(∇×v) dx = k² ∫ E·v dx,    n × E = 0 on ∂Ω
```

and on edges `a × b × d` the resonances have the closed form
`f_mnp = (c/2)·√((m/a)² + (n/b)² + (p/d)²)` with at most one index zero.

Why this is the sharpest test of the assembly in the repository: there are **no
materials, no sources, no drive**. The only inputs are the geometry and the two
bilinear forms, so a sign or scaling error anywhere in the curl-curl or the mass
assembly moves every frequency at once — and unlike a driven solve, there is no
boundary data the solver could read the answer back out of.

The fixture and the solve are *imported* from the module that closed `TH-9`
(`tests/validation/test_cavity_resonances.py` and `core/cavity.py`), so the
example and the gate cannot drift apart.

On record at `-n 2` (`20260809T200354Z_EX-5-gate.log`, 2 s, 2026-08-09;
reproducing the `TH-9` gate log `20260730T154846Z_TH-9.log` digit for digit):

| Mode | Solved | Rel. error | Ceiling |
| --- | --- | --- | --- |
| 1 (TE₁₀₁, fundamental) | **239.9805 MHz** | **0.0123%** | 0.5% |
| 2 | **291.3904 MHz** | **0.0153%** | 0.5% |
| 3 | **312.3465 MHz** | **0.0201%** | 0.5% |
| 4 | **346.5469 MHz** | **0.0436%** | 0.5% |

| Quantity | Value | Bound |
| --- | --- | --- |
| `null_mode_count` | **0** | `== 0` (no gradient mode leaked in) |
| Rayleigh quotient of the *exported* mode | 239.9805 MHz | **3.48e-15** rel. to the reported eigenvalue |
| Exported `|E|` span after peak normalisation | 2.31e-17 … 1.0 | — |
| Mesh / solve | 720 cells, 5330 dofs | 0.6 s of solve |

All four modes are printed and asserted, so the example cannot pass on one lucky
eigenvalue. The gate is `TH-9` (✅ 2026-07-30) and its own ceiling is 1%; the
0.5% here is the §7 `EX-5` plan's, well inside what the fixture delivers. This
example closes nothing — Phase-2 §5.4 backfill.

## 2. How to run it

```
./run_examples.sh -e th:2 -n 2 -t 180
```

The `th:` group sources the complex build automatically. The eigenproblem itself
is **real symmetric** and would run in either build; the group setting is what
governs, and you do not need to think about it. Tier: **standard** — 2 s on
record, of which 0.6 s is the eigensolve; the 720-cell mesh is deliberately
tiny, because closed-form accuracy here is set by the (6, 5, 4) element count
the gate chose, not by throwing cells at it.

## 3. How to analyze it, step by step

**Step 1 — the four frequencies against their closed forms.** This is the
anchor:

```
  mode 1: 239.9805 MHz   closed form 239.9510   0.0123%
  mode 2: 291.3904 MHz   ...                    0.0153%
  mode 3: 312.3465 MHz   ...                    0.0201%
  mode 4: 346.5469 MHz   ...                    0.0436%
```

Read all four before reacting to any one. The error rising monotonically with
mode number is the expected signature: higher modes have more structure per
cell, so the same mesh resolves them less well. An error pattern that does *not*
rise with mode number is more suspicious than a slightly larger error that does.
Each figure reproduces the `TH-9` record to every digit that record carries.

**Step 2 — `null_mode_count`, which must be exactly 0.** N1curl discretisations
carry a large cluster of **gradient modes** at zero eigenvalue — `∇φ` fields
that are curl-free and therefore physically meaningless here. If the
shift-and-invert target drifts toward zero, those modes come back instead of the
physical ones and the solver reports frequencies that are numerical artifacts.
`null_mode_count == 0` asserts that the target sat inside the physical band. A
nonzero count invalidates the whole table above it, however plausible the
numbers look.

**Step 3 — the negative control, cited rather than recomputed.** The null space
is not noise, it is a real cluster, and the gate measured it: **8 of 8**
eigenvalues nearest zero fall below the `1e-8·k₁²` cutoff, with
`max|λ|/k₁² ≈ 3.2e-15`. That is **13 orders of magnitude** of separation from
the O(0.04%)-accurate physical modes. The example prints that separation and
asserts that the cited cluster and this run's measured 4.36e-04 physical error
still straddle the gate's 1e-8 cutoff — i.e. the two populations have not
started to merge. It does not re-run the degree-1 solve behind the control.

**Step 4 — the exported mode is the asserted mode.** The Rayleigh quotient
`λ = ∫|∇×E|²/∫|E|²` of the very function written to XDMF is re-assembled and
converted back to a frequency: **239.9805 MHz**, **3.48e-15** relative to the
eigenvalue the solver reported. So ParaView is colouring the fundamental, not a
look-alike field that happened to be at the same index. The exported magnitude
spans **2.31e-17 … 1.0** after peak normalisation, which means the PEC wall
condition (`n × E = 0`) is visible in the array itself and not merely in the
formulation.

**Step 5 — open it in ParaView.**
`File → Open → examples/time_harmonic/paraview_output/pec_cavity_mode_combined.xdmf`,
then colour by `E_mode1_magnitude`.

1. **What to look at first:** brightest on the mid-plane, falling to zero on
   every wall. That zero *is* the boundary condition, and step 4's 2.31e-17
   floor is the same fact as a number.
2. **Glyph** on `E_mode1`: a single half-wave along `x` and along `z`, and
   **none** along `y`. That index pattern is what makes it TE₁₀₁ rather than
   some other mode at a nearby frequency — the frequency alone does not identify
   the mode, the field pattern does.
3. **Slice** through the mid-plane and check the arrows are unidirectional
   there. A mode with a sign reversal across the mid-plane is a higher index and
   you are looking at the wrong array.

**Step 6 — what a deviation means.** All four frequencies shifted by the same
factor → a scaling error in the assembly or in `c`, since nothing else can move
them together. One frequency shifted while the others hold → mode ordering,
likely a near-degeneracy the sort swapped; check the field pattern of step 5
before believing the number. `null_mode_count > 0` → the shift target, and stop
reading the table. Errors that no longer match the `TH-9` record while still
sitting under 0.5% → the fixture has drifted (mesh, box dimensions), and being
in-band does not excuse it. Any of these is a regression finding against `TH-9`:
report and stop, do not widen the ceiling.

## Related

- The gate this example runs: `tests/validation/test_cavity_resonances.py`
  (`TH-9`), and PROJECT_PLAN.md §7 for its record.
- What goes wrong when a **driven** solve sits near one of these
  eigenfrequencies — the failure mode this spectrum causes:
  `examples/time_harmonic/05_resonance_guard_sweep.py` (`th:5`).
- The first driven time-harmonic example:
  `examples/time_harmonic/01_lossy_plane_wave.py` (`th:1`).
