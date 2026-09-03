# `ports:9` — the first coil-driven SAR quantity: quadrant powers of the loaded birdcage

`EX-43`, opened by the 2026-09-03 03:00 review's §9 item 3, the §5.4 ramp
`WF-6` step 3g/3h/3i owes. Every other SAR example in this tree (`mri:2`)
reads a mass-averaged SAR figure on an **imposed** uniform field; every other
`|B₁⁺|` example (`ports:6`/`7`/`8`) writes a field on a **solved** coil. This
is the first example that does both at once: a coil-driven SAR quantity, on
the solved birdcage.

## 1. What this demonstrates

`WF-6` step 3g turned the C4 rotation identity of quadrant SAR power into a
**cell integral** of the primal N1curl `E` — no projection, no estimator, no
sample set — after three earlier rungs (3c, 3e′, 3f) separated the projector,
the estimator degree and the mesh `h` from the 25–41% miss a *pointwise*
reading of the same identity showed. Step 3h gated the twelve C4 pairs at
≤5%; step 3i added a second, independent symmetry — the mirror through the
coil axis and each drive's own azimuth — on the same four solves. That is the
first coil-driven SAR gate in the repo, and like every gate before it, it
lives in `tests/validation/test_birdcage_sar_integral.py` and nobody opens a
test module in ParaView.

This example runs `PORT-9` leg (d)'s own `build_four_port_sweep` — the
gapped, sheeted, phantom-loaded four-leg birdcage on the default
116 085-cell mesh, 10 MHz — the same four single-port driven solves plus the
CCW quadrature superposition, and prints the same table step 3g/h/i's gate
module does. Every helper (`_quadrant_weight`, `_quadrant_powers`, the C4
rotation sense, the mirror construction) is **imported**, never restated,
from `test_birdcage_sar_integral.py` as it stands at `642bfc5`.

### What it asserts

Nothing is restated: every band, record and helper is imported from the gate
module and its upstream modules (the `EX-33` reading of the `ANS-1` rule).

* **gate (i)**, the C4 rotation — twelve pairs
  `|P_{j+1}^{(k+1)} − P_j^{(k)}| / P_j^{(k)}` ≤ the imported
  `C4_COVARIANCE_BAND` (5%), each reproducing `STEP3G_INTEGRAL_PAIR_RECORDS`
  at rtol `CG1_RECORD_RTOL` (1e-3). Its in-run negative control — the
  mis-paired 180°-quadrant reading — must read strictly larger at every `k`;
* **the mirror identity** (step 3i) — `P_{k-1}^{(k)} = P_{k+1}^{(k)}`, one
  reading per drive, ≤ the same band, reproducing `STEP3I_MIRROR_RECORDS` at
  the same rtol;
* **the partition identity** — `Σ_j P_j^{(k)} = P_phantom^{(k)}` at rtol
  `PARTITION_RTOL` (1e-10), for all five drives (four single ports plus the
  quadrature superposition) — an identity of the construction (`Σ_j w_j ≡ 1`
  pointwise), asserted tightly because a miss names a wrong measure, a
  dropped reduction or a partition that does not partition;
* **the P1 total** — the P1 drive's phantom power reproduces step 1's
  recorded `STEP1_GATE_I_P1_PHANTOM_POWER_W` = 5.637745667e-08 W at rtol
  1e-3;
* **the fixture** — cell ratio 1.000000 against the recorded 116 085.

**Negative control.** The mis-paired 180°-quadrant control (quadrant `j`
under drive `k` vs quadrant `j+2` under drive `k+1`) reads strictly larger
than the C4 pairing at every `k` (3g/3h measured 89–159×), asserted in-run.

### What it read on the run that landed it

`20260903T123502Z_EX-43.log`, Status 0, **77 s** wall clock / 73.1 s
in-script at `-n 2` on the complex build (mesh 24.1 s, sweep 23.2 s, four
extra solves ~5.5 s each).

| reading | this run | record | relative |
| --- | --- | --- | --- |
| partition residual, worst of 5 drives | 1.573e-14 | ≤ 1e-10 | — |
| P1 phantom total | 5.637745667e-08 W | 5.637745667e-08 W | 4.114e-11 |
| C4 pairs, worst (k=1,j=0) | 1.5200% | 1.5200% | ~0 |
| mirror pairs, worst (k=0) | 1.7527% | 1.7527% | ~0 |
| mis-paired control / C4 pairing | 89.088–159.272× | 89–159× | — |
| flank-vs-opposite mirror control | 21.8–110.1× | — | — |
| cell ratio | 1.000000 | 1.000000 | — |

All twelve C4 pairs and all four mirror pairs reproduced their gate-module
records to the printed digit.

## 2. How to run it

```
./run_examples.sh -e ports:9 -n 2 -t 400
```

The runner sources the complex DolfinX build for the `ports:` group
automatically; the script raises immediately on a real build. If the runner
fails with `permission denied … /var/run/docker.sock`, run its inner command
verbatim through `run_and_log.sh` (PROJECT_PLAN §9's runner-trap note) — that
is a host-side docker-socket intermittency, not this example.

## 3. How to analyze it, step by step

`paraview_output/ports_09_birdcage_sar_quadrant_powers_combined.xdmf` carries,
on one grid:

| array | space | what it is |
| --- | --- | --- |
| `SAR_P1_W_per_kg` | DG0 scalar | `σ\|E\|²/(2ρ)`, P1 driven, phantom cells only |
| `SAR_quadrature_W_per_kg` | DG0 scalar | the same, CCW quadrature-superposed drive |
| `w_0` … `w_3` | DG0 scalar | the four azimuthal quadrant weights (`Σ_j w_j ≡ 1`) |
| `CellTags` | DG0 | 1 conductor, 3 phantom |

**Threshold `CellTags` on 3** and colour by `SAR_P1_W_per_kg` for the
coil-driven SAR map inside the phantom. Colour by `SAR_quadrature_W_per_kg`
for the quadrature-drive map. Threshold `w_0` (or `w_1`/`w_2`/`w_3`) above
0.5 to isolate one azimuthal quadrant — that is what the gated C4 pairs and
the mirror identity above are integrals *over*.

**The SAR maps are a viewing quantity, not the gate.** `σ|E|²/(2ρ)` is
interpolated per cell exactly the way `MAT-4`'s `mean_sar`/`point_sar` read
the same integrand, but pointwise rather than integrated — this is the
construction step 3's own pointwise rungs retired *as a gate* (the 25–41%
miss that motivated 3g's cell-integral construction in the first place).
Nothing about the map carries an assertion in this script; only the twelve
C4 pairs, the four mirror pairs, the partition identity and the P1 total are
gated, and only as self-consistency identities on one fixture at 10 MHz at
fixed `h`.

## 4. Scope — read before quoting a number

Two **symmetry identities** (C4 rotation, mirror reflection) of quadrant SAR
power on one fixture, 10 MHz, fixed `h` — nothing more. No band moves, no new
gate, no §2 change: `WF-6` stays 🟡. No absolute SAR figure, no homogeneity,
no C95.3, no Larmor, no convergence claim. The SAR maps this example writes
carry no assertion and no absolute-accuracy claim; they are a picture of the
integrand the identities are read from, not a validated SAR field.
