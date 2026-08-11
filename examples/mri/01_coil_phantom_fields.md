# `-e mri:1` — coil + gelled saline phantom: the **ungated end-to-end demo**

Guide for `examples/mri/01_coil_phantom_fields.py`.
Written to be followed without the source open.

## 1. What this demonstrates

**Plumbing, and nothing else. This is the one ungated example in the tree.**
Every other example under `examples/` asserts an anchor from a gate that has
closed; this one asserts nothing. It shows that mesh generation, material
assignment, both solvers, the phantom-metrics post path and the ParaView export
all connect and run to completion on an MRI-shaped geometry — two coils, a
gelled saline phantom, air — at 127.74 MHz.

**No number it prints is evidence about the physics.** None is compared against
a closed form or any other reference. Read PROJECT_PLAN.md §2 before quoting one.
The chunk is `WF-1`, status 🧪 (end-to-end demo), and it stays 🧪.

Two specific reasons the numbers are not physics, both visible in the output:

- **The drive is a proxy.** A uniform `z`-directed current density is imposed
  over both torus regions; it is not a birdcage, not a gap-voltage port, and not
  resonant. Ports and B1+ are deliberately unscoped (`PORT-1`, §2).
- **The `|E|/|B|` balance check fails by eight orders of magnitude** — the run
  prints `|E|/|B| mean ratio: 1.529336e+08` and raises its own consistency
  warning. On a physical RF field those two are related by roughly the wave
  impedance; here they are not, because the E leg and the B leg are driven by
  the same proxy through two unrelated formulations. The warning is the honest
  output, not a bug to suppress.

What *is* real: `TH-6` (the lossy plane wave, ✅ 2026-07-31) gates the
time-harmonic formulation itself, and `th:1` demonstrates it. That gate says
nothing about *this* geometry — the mesh here is 9261 cells at the `debug`
preset, unconverged by any measure.

Since `EX-16` (2026-08-10) the frequency-domain leg solves through the solver's
**default direct path** and reports `converged=True (reason=4)` in one
iteration, at the validated magnetostatic gauge floor `gauge_penalty=1.0`. It
previously overrode that with GMRES+Jacobi and stopped at `ksp_max_it` with
`converged=False (reason=-3)`, `residual_norm=1.684628e+00`. A converged solve
at the validated gauge floor is strictly better than a truncated iterate at a
sub-floor penalty — but see the caveat below, because it did **not** fix what it
was hypothesised to fix.

### The open caveat: centerline samples are rank-dependent

**Do not quote a centerline number from a single rank count.** At `-n 2` vs
`-n 4` the five printed centerline `(|E|, |B|)` pairs spread by **23.5539%** —
against **23.5545%** for the unconverged solve it replaced, a ratio of
**1.0000**. Converging the KSP moved only the `|E|` leg (15.6832% → 13.4499%);
the maximum is carried by the **magnetostatic `|B|` leg**, which no
frequency-domain change can touch.

The decisive measurement is the positive control taken on the *same two runs and
the same fields*: the **493-point phantom-region** sampling path — the `|E|`/`|B|`
min/max/mean block, not the centerline block — agrees across rank counts to
**0.007326%**, **3215× tighter**. Same solve, same field, two samplers. The
defect is therefore in the **centerline point-evaluation path**
(`evaluate_vector_field_parallel`), not in the solve, the KSP or the gauge; the
likely mechanism is on-axis points at `x = y = 0` sitting on shared mesh edges,
exactly what `MAG-6` step 4 characterised.

That is an **open known-issues entry**, assigned to `POST-4` (step 1 diagnoses
ownership, step 2 — conditional — replaces last-writer-wins with a
min-global-cell tie-break). Until it closes: the phantom-region aggregates are
rank-stable and the centerline block is not.

On record at `-n 2`, `debug` preset (`20260810T170234Z_EX-16-direct-n2.log`,
exit 0, 6 s harness-wall; the `-n 4` companion is
`…170309Z_EX-16-direct-n4.log`, 4 s):

| Quantity | Value | Rank-stable? |
| --- | --- | --- |
| Mesh | 9261 cells, 2077 vertices | — |
| Cell tags | coil_1 **385**, coil_2 **350**, phantom **493**, air **8033** | — |
| Frequency-domain KSP | `preonly` / `lu`, `converged=True (reason=4)`, 1 iteration, `residual_norm=0.000000e+00` | — |
| Phantom `\|E\|` min/max/mean | 1.244231e+02 / 3.150176e+02 / **1.975909e+02** | **yes** — 0.007326% |
| Phantom `\|B\|` min/max/mean | 8.791014e-08 / 2.771692e-06 / **1.292004e-06** | **yes** — 0.007326% |
| `\|E\|/\|B\|` mean ratio | **1.529336e+08** (max 1.136553e+08) | — (non-physical by construction) |
| Sampling coverage | 493/493/493, 0 dropped | — |
| Centerline, `z = 0` | `\|E\| = 2.364105e+02`, `\|B\| = 4.933436e-07` | **NO** — 23.5539% across `-n 2`/`-n 4` |
| Centerline samples valid (E/B) | 5/5, 5/5 | — |
| quick-look status | **WARN** (the imbalance warning above) | — |

The `WARN` status is the expected output, not a failure.

## 2. How to run it

```
./run_examples.sh -e mri:1 -n 2 -t 180
```

**Complex build required** — the `mri:` group sources it automatically. In the
real build `TimeHarmonicSolver.solve` raises rather than silently dropping the
loss term. Tier: **standard**; **6 s** harness-wall on record at `-n 2` (4 s at
`-n 4`), at the default `debug` preset.

Three presets are available via `--preset`, trading cost for detail:

| Preset | Mesh resolution | Centerline samples | Frequency probes |
| --- | --- | --- | --- |
| `debug` (default) | 0.020 m (`coarse`) | 5 | 1 |
| `dev` | 0.015 m (`medium`) | 9 | 3 |
| `benchmark-lite` | 0.010 m (`fine`) | 17 | 3 |

The on-record numbers in this guide are all `debug`. `benchmark-lite` is
substantially more expensive and has no record here; size it with a cost probe
before running it in a slot.

## 3. How to analyze it, step by step

**Step 1 — check the mesh is the mesh you think it is.** Before any field
number, read the tag summary:

```
  tag 1 (coil_1): 385 cells
  tag 2 (coil_2): 350 cells
  tag 3 (phantom): 493 cells
  tag 4 (air): 8033 cells
```

These are **global** counts (allreduced), so they must be identical at every
rank count — that is the cheapest possible check that the partition is not
changing the problem. The geometry sanity report above them prints
`expected_volume_ratio` vs `observed_cell_ratio` per region; the coils read
0.013 expected vs 0.042/0.038 observed because the mesher over-resolves the
small torus volumes relative to their share of the box. That is a meshing
artifact and is why `warnings: none` is the right verdict there.

**Step 2 — confirm the frequency-domain solve converged.**

```
    ksp=preonly, pc=lu, converged=True (reason=4), iterations=1
    residual_norm=0.000000e+00, residual_trend=unavailable, history_samples=0
```

`preonly` + LU is a direct solve, so one iteration and a zero residual are the
correct readings, not suspicious ones — `residual_trend=unavailable` and
`history_samples=0` follow from there being no iteration history to record.
Anything reporting `converged=False (reason=-3)` means an iterative override has
crept back in; `EX-16` removed exactly that, and `EX-13` measured the truncated
iterate it produced.

**Note what this does and does not buy.** `converged=True` is a *precondition*,
not a result — a convergence flag alone closes nothing under §4. It certainly
does not make the printed numbers physics.

**Step 3 — read the phantom-region aggregates, which are the trustworthy block.**

```
  |E| min/max/mean: 1.244231e+02 / 3.150176e+02 / 1.975909e+02
  |B| min/max/mean: 8.791014e-08 / 2.771692e-06 / 1.292004e-06
  sampling coverage (valid/sampling/requested): 493/493/493
  dropped samples (boundary-adjacent, invalid E, invalid B): 0, 0, 0
```

These are aggregates over all 493 phantom cells and they reproduce across rank
counts to **0.007326%**. If you must quote a number from this example, quote one
of these — and quote it as plumbing output, not as a field. The coverage line is
part of the reading: `493/493/493` with zero drops means no sample was discarded
as boundary-adjacent or invalid, so the aggregate is over the whole phantom.

**Step 4 — read the consistency block, and expect it to warn.**

```
    |E|/|B| mean ratio: 1.529336e+08 (max ratio: 1.136553e+08)
    span ratios (E/B): 0.605028 / 0.968283
    mean-balance relative diff: 1.000000
    warnings:
      - |E| and |B| mean magnitudes are strongly imbalanced; ...
```

`mean-balance relative diff: 1.000000` is saturation — the two are so far apart
that the normalised difference has pinned at 1. This is the expected output of
an ungated proxy drive, and it is the single clearest reason nothing here is a
physics claim. The *span* ratios (0.61 and 0.97) are more informative than the
magnitudes: they say both fields vary over the phantom by a comparable relative
amount, i.e. the spatial structure is plausible even though the scales are not
related.

**Step 5 — read the centerline block last, and read it with the caveat.**

```
Centerline sample magnitudes (z, |E|, |B|):
  z=-0.0450 m -> |E|=1.564570e+02, |B|=3.689962e-07
  z=-0.0225 m -> |E|=2.240058e+02, |B|=3.530755e-07
  z=+0.0000 m -> |E|=2.364105e+02, |B|=4.933436e-07
  z=+0.0225 m -> |E|=2.247580e+02, |B|=4.055231e-07
  z=+0.0450 m -> |E|=1.629703e+02, |B|=4.348834e-07
```

The shape is sensible — both fields peak at the mid-plane between the coils —
but **these five pairs are partition-dependent to 23.5539%**. Running at `-n 4`
gives visibly different digits from the same solve. Treat this block as
illustrative only; the open `POST-4` entry owns it. The `centerline samples
valid (E/B): 5/5 / 5/5` line says all five points were located in some cell — it
does **not** say the same cell was chosen at every rank count, which is the
actual defect.

**Step 6 — open it in ParaView.**
`File → Open → examples/mri/paraview_output/mri_coil_phantom_fields_combined.xdmf`.

1. **Threshold** on `CellTags` (1/2 = the two coils, 3 = phantom, 4 = air) and
   keep 1–3 to see the geometry without the air box. That view alone is most of
   what this example is for: it shows the coil+phantom domain the project's
   mission geometry is built on.
2. **Colour by `B`** (magnitude) with only the phantom kept: field is highest
   near the mid-plane between the coils, which is the Helmholtz-like arrangement
   doing what it should qualitatively.
3. **Colour by `E`** on the same clip. Compare *shapes*, not scales — the scales
   are eight orders of magnitude apart for the reason in step 4.
4. `mri_coil_phantom_fields_A.xdmf`, `mri_coil_phantom_fields_B.xdmf` and
   `mri_coil_phantom_fields_E.xdmf` hold the same fields separately if you
   prefer one file per quantity.

**Step 7 — the machine-readable artifacts.** Alongside the XDMF the run writes
`mri_coil_phantom_phantom_metrics.json` (the step-3/step-4 blocks as JSON),
`mri_coil_phantom_phantom_E_samples.csv` and
`mri_coil_phantom_phantom_B_samples.csv` (the 493 per-cell samples),
`mri_coil_phantom_quicklook.json` / `mri_coil_phantom_quicklook.md` (the WARN
block), and `mri_coil_phantom_manifest.json` — which records the git commit,
every parameter, and whether each artifact exists. The manifest is the file to
read when you need to know *which* run produced a picture.

**Step 8 — what a deviation means.** `converged=False (reason=-3)` → an
iterative solver override has returned; that is the `EX-16` regression. Cell-tag
counts differing from 385/350/493/8033 at the `debug` preset → the mesh changed;
nothing below is comparable to this record. Phantom aggregates moving by more
than ~0.01% across rank counts → a *new* defect, because that path is the
rank-stable one; report it, it is not the known centerline issue. Centerline
numbers differing across rank counts → the **known** open issue, expected, do
not file it again. `dropped samples` non-zero → the phantom sampling lost cells
to the boundary filter and the aggregates no longer cover the whole phantom.
`|E|/|B|` ratio near the wave impedance → something has changed that would make
this a physics example, which it is not licensed to be; check what moved before
celebrating.

## Related

- The known-issues entry that owns the centerline caveat:
  `docs/testing/known-issues.md`, assigned to `POST-4` (PROJECT_PLAN.md §7).
- The measurement that attributed it: `EX-16` (PROJECT_PLAN.md §7), logs
  `20260810T170457Z_EX-16-spread-v2.log` and the `-n 2`/`-n 4` pair.
- The gate that makes the time-harmonic *formulation* real — which this geometry
  does not inherit: `examples/time_harmonic/01_lossy_plane_wave.py` (`th:1`,
  `TH-6`).
- A SAR quantity that **is** gated, on an imposed field:
  `examples/mri/02_mass_averaged_sar.py` (`mri:2`, `MAT-4` step 3).
- What is and is not real project-wide: PROJECT_PLAN.md §2.
