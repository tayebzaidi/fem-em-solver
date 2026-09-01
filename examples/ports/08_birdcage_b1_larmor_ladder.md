# `ports:8` — the `|B₁⁺|` ladder at the Larmor frequencies, 64 and 128 MHz

Runs `examples/ports/08_birdcage_b1_larmor_ladder.py` (`EX-40`). Two rungs of
the loaded four-leg birdcage — **64 MHz** and **128 MHz**, the ¹H Larmor
frequencies of a 1.5 T and a 3 T system — on **one** mesh, each producing a
`|B₁⁺|` field for ParaView and each asserting the two identities `WF-6` step 2b
gated there.

## 1. What this demonstrates

Every `|B₁⁺|` picture this repo had before this example is a **10 MHz**
picture. `ports:6` (`EX-38`) put the first one in ParaView; `ports:7` (`EX-39`)
added the quadrature drive and `|B₁⁻|`. Both run at the eddy-current rung the
project meshes and gates on — not at a frequency any MRI system operates at.
`ports:5` (`EX-34`) does climb the Larmor ladder, but it stops at the 4×4
`S`-matrix: a terminal quantity with no field behind it.

`WF-6` step 2b (✅ 2026-08-31) closed that gap numerically — it ran the B₁⁺
identities at 64 and 128 MHz for the first time and they held — but it did so
inside `tests/validation/test_birdcage_b1_larmor.py`, and nobody opens a test
module in ParaView. **The frequency is the angle this example adds.** It is the
§5.4 ramp step 2b owes.

The construction is not re-implemented anywhere here. The fixture is
`PORT-9` leg (d)'s own `build_four_port_sweep` — `GEO-18`'s gapped, sheeted,
phantom-loaded birdcage on `GEO-19` step B's 116 085-cell mesh, with four
`f = 0.5` lumped-element sheets at `Z_p = 50 Ω` — called once at 64 MHz to
build the mesh and once at 128 MHz with `reuse=`, so **the frequency is
demonstrably the only thing that differs between the two rungs**. Three driven
solves are kept per rung for their fields: P1 and P2 carry the symmetry
identity, P3 is the control's drive. `B = ∇×E/(−jω)` comes from
`post.magnetic_flux_density_from_e` (DG0, Faraday), is L²-projected to CG1 by
`post.project_to_cg1` — the production estimator since `WF-6` step 1d — and
`|B₁⁺| = |B_x + jB_y|/2` is formed from the projected vector.

### What it asserts

Every band, record and helper is imported (`ANS-1`'s rule). Per rung:

| anchor | what it is | band / record |
|---|---|---|
| **gate (i)** | three-way real-power accounting at the P1 drive: supplied `½ Re(V_src I*)` against phantom + conductor + sheets | ≤ `POWER_BALANCE_BAND` = 1%, **and** reproduces step 2b's residual at `RECORD_RTOL` = 1e-4 |
| **gate (ii)** | CG1 C4 covariance of the `\|B₁⁺\|` map, P1 → P2 at +90° | ≤ `C4_COVARIANCE_BAND` = 5%, **and** reproduces step 2b's record at `CG1_RECORD_RTOL` = 1e-3 |
| resolution | phantom cells/λ, checked **before** any gate is read | ≥ `PHANTOM_CELLS_PER_LAMBDA_FLOOR` = 10 (`PORT-11` step 3), record at 1e-4 |
| sample set | all 51 tag-3 centroids evaluate in both drives, in the control and in their rotated images | `== n_points`, ≥ `MIN_SAMPLE_POINTS` |
| fixture | one mesh object shared by both rungs, at `GEO-19` step B's cell count | ratio 1.000000 to 1e-9, `sweeps[label]["mesh"] is base["mesh"]` |

**Negative control.** P3 sits 180° from P1, so reading *it* at the **+90°**
image is the right operation applied to the wrong drive. It is asserted
**outside** the 5% band and against its own step-2b record. A covariance gate
that passed on the wrong drive would not be resolving the drive's azimuth at
all — the identity would be free.

The gate-(i) conductor-blind control is asserted too: dropping the conductor's
`½∫σ|E|²` must push the residual outside the band, or the identity is
insensitive to a term it is supposed to weigh.

### What it read on the run that landed it

`docs/testing/logs/20260901T020415Z_EX-40.log`, Status 0, 113 s at `-n 2`,
116 085 cells (record 116 085, ratio 1.000000), `reused_mesh = True`, 51 of 51
points valid at both rungs:

```
rung       cells/lambda   gate(i) P1     (ii) P2@+90   control P3@+90   mean |B1+| (P1)
64 MHz       21.8936    9.5231e-03       2.2187%       24.7535%   1.695428e-08 T
128 MHz      12.5024    9.2445e-03       2.1315%       25.2589%   1.294928e-08 T
```

Every column reproduced step 2b's record to between 1.9e-07 and 1.1e-05
relative. The identity/control separation is **11.2×** at 64 MHz and **11.9×**
at 128 MHz.

**Printed, ungated, labelled:** the mean `|B₁⁺|` of the **P1 single drive**
over the sample set, at 1 V per port — `1.695428e-08 T` at 64 MHz and
`1.294928e-08 T` at 128. It falls with frequency at a fixed drive *voltage*
because the terminal current falls: this fixture's port impedance rises with
frequency, so the same 1 V pushes less current through the leg. That is a
terminal-impedance effect and **not** a statement about the coil's efficiency,
its homogeneity, or what it would do driven at a fixed current or a fixed
power. Step 2b's recorded means for the *quadrature* map at these rungs
(`6.500452e-08` / `4.936577e-08` T) are printed beside it for provenance only —
a different drive, not reproduced here.

## 2. How to run it

Needs the complex DolfinX build; the runner sources it for the `ports:` group
automatically.

```
./run_examples.sh -e ports:8 -t 400
```

Through the logging harness, as every verification run must be:

```
scripts/testing/run_and_log.sh EX-40 "./run_examples.sh -e ports:8 -t 400"
```

If the runner fails with `permission denied … /var/run/docker.sock`, run its
inner command verbatim instead (PROJECT_PLAN §9's runner trap):

```
scripts/testing/run_and_log.sh EX-40 "docker compose exec -T fem-em-solver \
  bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \
  PYTHONPATH=/workspace/src timeout -k 30 400 mpiexec -n 2 python3 \
  examples/ports/08_birdcage_b1_larmor_ladder.py'"
```

Cost on the run that landed it: mesh 24.8 s, six driven solves ≈ 34 s, the
sweeps' own four-solve rungs ≈ 46 s, projections and two XDMF writes for the
rest — **113 s total** at `-n 2`, standard tier.

## 3. How to analyze it, step by step

1. **Read the fixture line first.** `116085 cells … ratio 1.000000`,
   `reused_mesh = True`, and two distinct frequencies. If the ratio is not
   1.000000 the run stops before any field is read — every record below was
   measured on that mesh and means nothing on another.
2. **Read the cells/λ column before the gates.** 21.8936 at 64 MHz and 12.5024
   at 128, against a floor of 10. The 128 MHz rung is only 25% above the floor:
   this is the rung where a resolution finding would show up first, and the
   example asserts the floor *before* it reads a gate so that a miss reports
   itself as a resolution problem rather than as a passing identity nobody may
   quote.
3. **Then gate (i).** The residual is a conservation identity: real power in at
   the driven sheet equals what the phantom, the conductor and the four sheets
   dissipate. Note the split — at 64 MHz the phantom takes 0.03% of the
   supplied power and the sheets 89.8%; at 128 MHz the phantom is up to 0.14%
   and the conductor to 12.1%. **This is a 50 Ω-terminated coil, not a tuned
   one**; almost all the power goes into the terminations.
4. **Then gate (ii), with its control beside it.** 2.2187% / 2.1315% against
   5%, next to 24.7535% / 25.2589% for the mis-rotated drive. Read them as a
   pair: the identity number alone says nothing until you know what the same
   comparison returns when it is wrong.
5. **Open the two XDMF files** —
   `ports_08_birdcage_b1_larmor_ladder_64MHz_combined.xdmf` and
   `ports_08_birdcage_b1_larmor_ladder_128MHz_combined.xdmf`, both in
   `examples/ports/paraview_output/`. Each `_combined` file carries `B_real` /
   `B_imag` (the CG1-projected `B` phasor), `B1_plus_cg1` (CG1 — the gated
   estimator), `B1_plus_dg0` (the raw DG0 curl) and `CellTags`. Threshold
   `CellTags` on `3` to isolate the phantom and colour it by `B1_plus_cg1`.
6. **Put both rungs on a common colour range.** That is the picture: the same
   coil, the same phantom, the same 1 V drive, at the two frequencies this
   project exists for. Then re-read step 5 of the scope section before
   describing what you see.
7. **Compare `B1_plus_cg1` against `B1_plus_dg0`** on the same threshold. The
   DG0 field is the piecewise-constant cell scatter; the CG1 field is what
   `WF-6` step 1d re-registered the gate around. `EX-38` measures that
   difference quantitatively at 10 MHz (8.65% vs 2.19%); here it is left as a
   visual.

## 4. Scope — read before quoting a number

* **Identities on one unconverged fixture.** Two symmetry/conservation
  self-consistency checks per rung, degree 1, F-small. Nothing here is an
  absolute-accuracy claim about `|B₁⁺|` at 64 or 128 MHz, and no comparison
  against Ansys, literature or measurement has been made at either.
* **No quadrature.** The maps here are *single-drive* maps. The circularly
  polarised drive lives in `ports:7` (`EX-39`), at 10 MHz.
* **No homogeneity, CV or SAR.** The phantom power term in gate (i) is a power
  accounting term, not a SAR figure; `WF-6` step 3 measured coil-driven point
  SAR and it **missed** every identity by 25–41% (known-issues, 2026-08-31).
* **No tuning or resonance claim.** The coil is 50 Ω-terminated at all four
  ports and is not tuned to either Larmor frequency. `PROJECT_PLAN.md` §2 is
  the authority on what the port model licenses; read it before quoting any of
  this.
* **The mean `|B₁⁺|` is ungated.** See §1 — it falls with frequency for a
  terminal-current reason, and a coil-efficiency reading of it would be wrong.
