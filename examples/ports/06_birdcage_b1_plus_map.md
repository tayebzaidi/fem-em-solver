# `ports:6` — the first `|B₁⁺|` map: loaded 4-leg birdcage at 10 MHz

`EX-38`, the §5.4 ramp `WF-6` step 1 ✅ (2026-08-30) owes. The first example in
this tree that writes the quantity an MRI transmit coil is actually judged on —
the circularly polarised transmit field **inside the phantom** — into a file you
can open.

## 1. What this demonstrates

Every port example before this one stops at a **terminal** quantity. `ports:1`
(`EX-18`), `ports:2` (`EX-20`) and `ports:3` (`EX-24`) read impedances off the
two-torus pair; `ports:4` (`EX-32`) and `ports:5` (`EX-34`) read the birdcage's
4×4 `Z`/`S` at 10 MHz and across the Larmor ladder. `ports:4` does write a field
picture, but it is `|E|` and `|B|` — never the transmit component.

`|B₁⁺| = |B_x + jB_y|/2` is the part of the RF magnetic field that co-rotates
with the nuclear precession and therefore does the transmit work. `WF-6` step 1
gated it on this fixture, and step 1d made the CG1 projection the production
estimator — but the map lives in a test module, and nobody opens a test module in
ParaView. That is what this example is for.

The fixture is `GEO-18`'s gapped, sheeted, phantom-loaded four-leg birdcage on
`GEO-19` step B's mesh (116 085 cells), four `f = 0.5` lumped-element port sheets
at `Z_p = 50 Ω`, 10 MHz, degree 1. It is built by `PORT-9` leg (d)'s own
`build_four_port_sweep`, so the fixture here *is* the gate module's. Two extra
driven solves (P1, P2) are kept for their fields, because the sweep returns
readings and not phasors; `B = ∇×E/(−jω)` then comes from
`post.magnetic_flux_density_from_e` (DG0, Faraday), is L²-projected to CG1 by
`post.project_to_cg1`, and `|B₁⁺|` is formed from the projected vector.

### What it asserts

Nothing is restated: every band, record and helper is imported from
`tests/validation/test_birdcage_b1_plus_map.py` and its upstream modules (the
`EX-33` reading of the `ANS-1` rule — import the construction, not only the
constants).

* **gate (i)**, the conservation identity — three-way real-power accounting at
  the P1 drive (`½Re(V_src Ī)` supplied = phantom `½∫σ|E|²` + conductor +
  `Σ ½|I_i|²Re Z_p`) inside `POWER_BALANCE_BAND` (1%), reproducing step 1's
  recorded `STEP1_GATE_I_P1_RESIDUAL` = 9.795751e-03 at `RECORD_RTOL` (1e-4).
  Its in-run negative control drops the conductor term and must then miss;
* **gate (ii)**, the symmetry identity — the CG1 C4 covariance of the map,
  P1 → P2 at +90°, inside the imported `C4_COVARIANCE_BAND` (5%) and reproducing
  step 1b's recorded 2.1870% at `CG1_RECORD_RTOL` (1e-3);
* **the sample set** — all of the tag-3 centroids in the sample cylinder
  (`r ≤ 0.02 m`, `|z| ≤ 0.02 m`) evaluate in both drives *and* in the rotated
  image, at or above `MIN_SAMPLE_POINTS`;
* **the fixture** — cell ratio 1.000000 against `STEP2_CELL_COUNT`, and both
  field solves asserted to run on the sweep's own mesh object (`reused_mesh`), so
  "the gated fixture" is a checked property and not a claim in a docstring;
* **the drive rotation** — 90.000000° read off the fixture's own sheet azimuths,
  never a literal.

**Negative control.** The same covariance is read on the raw **DG0** curl beside
the CG1 figure, asserted against step 1's recorded 8.6516% at 1e-4 *and* asserted
to stay **outside** the 5% band. That is the estimator floor gate (ii) was
re-registered around: a moved DG0 column would mean the field changed rather than
the estimator, and a DG0 column that suddenly agreed with CG1 would mean the
projection is no longer doing anything.

### What it read on the run that landed it

`20260831T200401Z_EX-38.log`, Status 0, **63 s** wall clock / 60.5 s in-script at
`-n 2` on the complex build. One mesh (116 085 cells, ratio 1.000000, 22.0 s),
the gated sweep's four solves 22.9 s, two field solves 5.5 + 5.5 s.

| reading | this run | record | relative |
| --- | --- | --- | --- |
| gate (i) residual, P1 | 9.795751117e-03 | 9.795751e-03 | 1.195e-08 |
| gate (ii) CG1 covariance | 2.1870% | 2.1870% | 1.643e-05 |
| DG0 control covariance | 8.6516% | 8.6516% | 3.227e-06 |
| valid sample points | 51 / 51 | — | — |

The DG0 read is **3.96×** the CG1 one on the same points and the same field —
piecewise-constant cell scatter on a gmsh mesh that is not itself C4-symmetric,
which is exactly what step 1d's projection removes.

Recorded and **ungated** (no absolute claim is licensed): over the 51 points at
`V_src = 1 V`, CG1 `|B₁⁺|` mean 2.069556e-08 T (max 2.886353e-08, min
1.475431e-08); DG0 mean 2.077398e-08 T.

## 2. How to run it

```
./run_examples.sh -e ports:6 -n 2 -t 300
```

The runner sources the complex DolfinX build for the `ports:` group
automatically; the script raises immediately on a real build. If the runner
fails with `permission denied … /var/run/docker.sock`, run its inner command
verbatim through `run_and_log.sh` (PROJECT_PLAN §9's runner-trap note) — that is
a host-side docker-socket intermittency, not this example.

## 3. How to analyze it, step by step

`paraview_output/ports_06_birdcage_b1_plus_map_combined.xdmf` carries, on one
grid:

| array | space | what it is |
| --- | --- | --- |
| `B_real`, `B_imag` | CG1 vector | the L²-projected `B` phasor |
| `B1_plus_cg1` | CG1 scalar | `|B_x + jB_y|/2`, the gated estimator |
| `B1_plus_dg0` | DG0 scalar | the same from the raw curl — the control |
| `CellTags` | DG0 | 1 conductor, 3 phantom |

**Threshold `CellTags` on 3** and colour the result by `B1_plus_cg1`: that is the
transmit field inside the phantom, and it is the deliverable. Switching the
colour array to `B1_plus_dg0` shows the cell-to-cell scatter the projection
removes — the two pictures are the estimator finding, visible rather than
tabulated.

## 4. Scope — read before quoting a number

Everything here is at **10 MHz**, on **single** drives, at degree 1, on the
F-small fixture, and both gates are **self-consistency identities**: a
conservation law and a symmetry. Nothing in this example is an absolute-accuracy
claim about `|B₁⁺|`, and no convergence rung for `|B₁⁺|` itself exists yet.

Explicitly **not** here: homogeneity or CV of the map; 64/128 MHz (`WF-6` step
2b gated the identities there, and `EX-40` is the example); the quadrature drive
and `|B₁⁻|` (`ports:7`, `EX-39`); SAR of any kind — the phantom `½∫σ|E|²` above
is a power term in the conservation identity, not a SAR map, and SAR10g/C95.3
belong to `MAT-4` step 2 and `WF-7`.
