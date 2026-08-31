# `ports:7` — the quadrature drive: `|B₁⁺|` **and** `|B₁⁻|` at 10 MHz

`EX-39`, the §5.4 ramp `WF-6` step 2 ✅ (2026-08-31) owes. `ports:6` (`EX-38`)
pictures the transmit field of a **single** driven port; this one drives all four
at once, the way a real birdcage is driven, and puts the two rotation senses side
by side.

## 1. What this demonstrates

An MRI birdcage is driven in **quadrature**: every port at once, each 90° behind
its neighbour, so that the transverse field rotates. One sense —
`|B₁⁺| = |B_x + jB_y|/2`, the one that co-rotates with the nuclear precession —
does the transmit work; the counter-rotating `|B₁⁻| = |B_x − jB_y|/2` is wasted
power that a working quadrature drive cancels. `WF-6` step 2 gated that drive and
measured a centre polarisation purity of **127.9** in a test module. This example
is the picture.

**Superposition here is exact, not an approximation.** The four single-drive
solves share one mesh, one operator and one source amplitude — *every* port's
sheet is in the bilinear form of *every* solve, at the same `Z_p = 50 Ω`; only
the right-hand side moves. A linear system with a fixed operator and four
right-hand sides superposes exactly, so the four-port drive with phases `φ_k`
**is** `Σ_k e^{jφ_k} E_k`. The two senses are formed on the fixture's own
azimuth-increasing port index `k`:

```
B_ccw = Σ_k e^{−jkπ/2} B_k        B_cw = Σ_k e^{+jkπ/2} B_k
```

each superposed on the raw DG0 curl, then L²-projected to CG1 by
`post.project_to_cg1` — the production estimator since `WF-6` step 1d — before
any point is read. Both magnitudes are formed *after* the evaluation, because
`|·|` is not linear.

The phase convention is **imported, never re-derived**: the weights come from
`test_birdcage_b1_quadrature.quadrature_phase_weights`, the single source of
truth for the one thing that cost step 2 a window. Its docstring records the sign
slip and what the wrong pairing measured — a near-null "ccw" sense and both
identities 10× off the floor.

The fixture is `GEO-18`'s gapped, sheeted, phantom-loaded four-leg birdcage on
`GEO-19` step B's mesh (116 085 cells), four `f = 0.5` lumped-element sheets at
`Z_p = 50 Ω`, 10 MHz, degree 1, built by `PORT-9` leg (d)'s own
`build_four_port_sweep`.

### What it asserts

Nothing is restated: every band, record and helper is imported from
`tests/validation/test_birdcage_b1_quadrature.py` and its upstream gate modules
(the `EX-33` reading of the `ANS-1` rule — import the construction, not only the
constants). Step 2's own records are now exported by that module as
`STEP2_IDENTITY_RECORDS`, `STEP2_CONTROL_MISMATCH`, `STEP2_CENTRE_PURITY`,
`STEP2_MEAN_B1_PLUS_CCW_T` and `STEP2_CV_CENTROIDS`, so this example reproduces
them rather than copying literals out of a log.

* **identity (a), C4-invariance** — advancing the phase pattern one port is the
  same drive rotated 90°, which multiplies the superposed field by a global
  phase, and a global phase does not move a magnitude. `|B₁⁺|_ccw(Rx)` matches
  `|B₁⁺|_ccw(x)` inside the imported `C4_COVARIANCE_BAND` (5%), reproducing step
  2's **0.9818%** at `CG1_RECORD_RTOL` (1e-3);
* **identity (b), the mirror** — `B` is a pseudovector, so reflecting in the
  plane through port 1's azimuth exchanges the two senses:
  `|B₁⁻|_cw(Mx) = |B₁⁺|_ccw(x)`, same band, reproducing **0.8087%**;
* **the superposition premise** — one `Z_p`, one `V_src`, and four solved drives
  equal to the fixture's. If a future fixture change made the ports
  non-identical, *this* is what goes red rather than a symmetry reading;
* **gate (i)** — step 1's three-way power accounting at the P1 drive still closes
  inside `POWER_BALANCE_BAND` (1%) and reproduces `STEP1_GATE_I_P1_RESIDUAL` =
  9.795751e-03 at `RECORD_RTOL` (1e-4), with its own in-run control (dropping the
  conductor term must then miss). That is the proof this is step 1's field;
* **the sample set and the fixture** — every tag-3 centroid in the sample
  cylinder evaluates in **both** senses on **all three** point sets (`x`, `Rx`,
  `Mx`), at or above `MIN_SAMPLE_POINTS`; cell ratio 1.000000 against
  `STEP2_CELL_COUNT`; all four solves asserted to run on the sweep's own mesh
  object; the 90° rotation, the four quadrature slots and the mirror plane all
  read off the fixture's sheet azimuths, never literals.

**Negative control.** The mis-paired `|B₁⁺|_cw(Mx)` against `|B₁⁺|_ccw(x)` is
`|B₁⁻|_ccw` in disguise — the sense the coil drives *against* — and is asserted
to **miss** the band. Without it, identity (b) could be passing on a degeneracy
in which the two senses are indistinguishable.

### What it read on the run that landed it

`20260831T213402Z_EX-39.log`, Status 0, **81 s** wall clock / 77.7 s in-script at
`-n 2` on the complex build. One mesh (116 085 cells, ratio 1.000000, 26.3 s),
the gated sweep's four solves 24.3 s, four field solves 6.2 / 6.4 / 5.8 / 6.0 s.
Port slots read off the fixture: P1 → `k=0`, P2 → `k=1`, P3 → `k=2`, P4 → `k=3`.

| reading | this run | step 2 record | relative |
| --- | --- | --- | --- |
| (a) C4 invariance of `|B₁⁺|_ccw` | 0.9818% | 0.9818% | 9.619e-06 |
| (b) mirror `|B₁⁻|_cw(Mx)` vs `|B₁⁺|_ccw(x)` | 0.8087% | 0.8087% | 3.585e-05 |
| mis-paired control | 95.1975% | 95.1975% | — (asserted `> 5%` only) |
| gate (i) residual, P1 | 9.795751117e-03 | 9.795751e-03 | 1.195e-08 |
| valid sample points | 51 / 51 | — | — |

The control is **118×** identity (b) on the same points: the two senses are
resolved, not smoothed together.

Recorded and **ungated**, and none of it a homogeneity or absolute claim: centre
purity `|B₁⁺|/|B₁⁻|` = **127.9083** ccw and **0.0081** cw (a linear polarisation
would read ≈ 1 — the P1 single drive reads 1.0006 in step 2's log); mean
`|B₁⁺|_ccw` = 7.976427e-08 T over the 51 centroids at 1 V per port; CV over that
set 2.7563%.

## 2. How to run it

```
./run_examples.sh -e ports:7 -n 2 -t 400
```

The runner sources the complex DolfinX build for the `ports:` group
automatically; the script raises immediately on a real build. `ports:6..7` is
**not** a valid selection token (`WF-6` step 2 paid a window for it) — pass one
token per example. If the runner fails with
`permission denied … /var/run/docker.sock`, run its inner command verbatim
through `run_and_log.sh` (PROJECT_PLAN §9's runner-trap note); that is a
host-side docker-socket intermittency, not this example.

## 3. How to analyze it, step by step

`paraview_output/ports_07_birdcage_b1_quadrature_map_combined.xdmf` carries, on
one grid:

| array | space | what it is |
| --- | --- | --- |
| `B_real_ccw`, `B_imag_ccw` | CG1 vector | the L²-projected quadrature `B` phasor |
| `B1_plus_ccw` | CG1 scalar | `|B_x + jB_y|/2` — the transmit field |
| `B1_minus_ccw` | CG1 scalar | `|B_x − jB_y|/2` — the wasted sense |
| `CellTags` | DG0 | 1 conductor, 3 phantom |

**Threshold `CellTags` on 3**, colour the phantom by `B1_plus_ccw`, then switch
the colour array to `B1_minus_ccw` **keeping the same colour range** (untick
"rescale on change"). The second picture going nearly black is the quadrature
drive doing its job — the same 128:1 the centre purity line reports, seen rather
than tabulated. Rescaling `B1_minus_ccw` to its own range instead shows where the
residual counter-rotating field lives, which is a structure of the four-leg
geometry, not a defect.

## 4. Scope — read before quoting a number

Everything here is at **10 MHz**, degree 1, on the F-small fixture, by
superposition, and both identities are **self-consistency** checks — a symmetry
and its mirror. Nothing here is an absolute-accuracy claim about either sense,
and no convergence rung for `|B₁⁺|` itself exists yet.

The centre purity, the mean `|B₁⁺|` and the CV are **printed and never
asserted**, deliberately: a CV is a homogeneity figure, and a homogeneity figure
needs a converged mesh and a real drive to mean anything. This fixture has
neither.

Explicitly **not** here: 64/128 MHz (`WF-6` step 2b gated the identities there,
and `EX-40` is that example); a simultaneous-source solve (the superposition
premise is asserted, not the four-source system); SAR of any kind — the phantom
`½∫σ|E|²` above is a power term in the conservation identity, and `WF-6` step 3's
coil-driven SAR symmetry readings are **red** at 25–40% on the pointwise-`E`
estimator; no literature or AED comparison.
