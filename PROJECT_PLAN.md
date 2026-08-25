# PROJECT_PLAN.md — FEM Electromagnetics Solver for MRI Coil Simulation

**Single source of truth for scope, status, and sequencing.** Resolved defects and
the reasoning behind past decisions live in [`docs/project-history.md`](docs/project-history.md);
nothing there is a task.

---

## 1. Mission *(rescoped 2026-08-04)*

A FEniCSX/DolfinX finite element toolkit that reproduces, for the slice of
electromagnetics relevant to **MRI RF safety**, the workflow an engineer runs
in Ansys Electronics Desktop — HFSS plus the circuit solver first, with the
Pennes bioheat equation for thermal simulation as the long-term extension.
The canonical workflow the tool must support end to end:

1. **Construct** a birdcage coil + gelled saline phantom simulation from
   parametric geometry — often with an implant inside the phantom.
2. **Tune** the birdcage at 64 MHz (1.5 T) and 128 MHz (3 T): EM solve plus
   circuit co-simulation to pick capacitor values, verify the mode spectrum,
   and match the ports.
3. **Drive** the tuned coil and extract the safety quantities: B1+ maps,
   SAR (whole-phantom and local, including near-implant hot spots), and port
   S-parameters.
4. Long term: **couple to thermal** via the Pennes bioheat equation.

Commercial solvers are expensive and black-box; open-source alternatives lack
the MRI-specific workflow. The scope is deliberately **the MRI-safety slice of
HFSS, not HFSS**: general-purpose 3-D full-wave parity is out of reach for
this project and is not the goal. Parity claims are made per-workflow ("tunes
a shielded 8-rung birdcage at 128 MHz to within X of AED"), never
per-product.

**Cross-validation against Ansys is part of the method.** `examples/` carries
runnable examples with XDMF outputs for visual review in ParaView, and
periodically a benchmark case specified precisely enough for the human
operator to replicate in Ansys Electronics Desktop; the returned numbers
become gates (§5.4).

---

## 2. Current state — read before planning work

What is validated, to what tolerance, and what must not be trusted.
(The history of how each claim was earned lives in §7's result blocks,
`docs/planning/plan-archive.md`, and `docs/project-history.md`.)

### 2.1 Validated, with the number that licenses it

- **Magnetostatics** (`core/solvers.py`, N1curl + gauge penalty, default
  1.0): Helmholtz **0.04%** centre / 0.83% mean; circular loop 7.07%;
  straight wire **`E_Ω` = 10.6172%** at h = 0.0025, falling
  25.2868 → 10.6172 → **6.6458%** on the h = 0.004/0.0025/0.0018 ladder at
  fitted rate **1.69** (`MAG-18`, 2026-08-22 — the annulus-restricted
  domain L2 that replaced the 10-point radial sample; the retired sampled
  statistic read 12.75% at n_points = 10 and 15.80% at 8 on the *same*
  field, so it never licensed a number); PEC cavity modes **0.0436%**
  (re-gated on the 0.11 image 2026-08-25 by `OPS-24` — `core/cavity.py` had
  been missed by the `OPS-18` migration and the `TH-9` gates were
  non-executing 2026-08-23 → 08-25; the migrated calls reproduce the 0.7.2
  per-mode errors 0.0123 / 0.0153 / 0.0201 / 0.0436% to the printed digit,
  known-issues entry retired).
  The `E_Ω` digits quoted here are the **0.11 image** ones, re-gated on
  `main` 2026-08-23 (§9 item 1, ruling (3\*)): the ladder is monotone at
  fitted rate **1.6854**, the record rung reproduces
  1.0617170177e-01 / 1.0617170374e-01 across two in-slot `-n 2` runs and
  1.0617175341e-01 at `-n 4` (4.86e-07 relative, inside the re-registered
  1e-6), and the natural-BC wall stays strictly worse (32.3155% vs
  10.6172%, ratio 0.3285). The 0.7.2 digits it replaces were
  25.3787 → 10.7288 → 6.6708% at rate 1.6842; no band moved. The
  `OPS-18` ✅ scope caveat is discharged.
- **Time-harmonic complex solve** (`TH-1`, complex build mandatory — real
  mode raises): MMS rate 0.9929; lossy plane wave α **0.019%** / β 0.059%
  (`TH-6`); evanescent waveguide γ **0.006%** (`TH-7`); quasi-static
  sphere 2.443% (`TH-8`); resonance guard calibrated (`TH-1` step 5).
- **The Larmor regime, on an imposed field** (`TH-10`): interior field vs
  the Mie series **3.643% / 1.826%** at 64 / 128 MHz (the 128 MHz figure
  re-recorded **1.769%** on the 0.11 image *with its mesh*,
  55 251 → 55 241 cells — `OPS-18` step 3 attempt 1, green log
  `20260822T123746Z`; 64 MHz reproduces bit-identically), and the
  SAR-relevant ½∫σ|E|² to **3.629%** — quasi-statics is the *wrong answer* there
  (under-predicts absorbed power 2.4× at 1.5 T). Degree-2 N1curl is gated
  on the same fixture (`TH-12` step 1, 2026-08-18): **0.1405%** interior
  relL2 on the coarse 5 866-cell rung — 25.9× the degree-1 fine-rung
  accuracy at 3.01× fewer cells, for 4.3× wall and 2.7× memory.
- **Coil loading, eddy-current regime only** (`MAT-6`): ΔR vs Dodd–Deeds
  **1.58%** at 10 MHz, σ = 100 S/m, on the production drive; ΔX is
  reported, never gated (not box-converged).
- **SAR machinery on an imposed uniform field** (`MAT-4`): mean SAR vs the
  lossy-sphere closed form to 3.5%; the 1 g/10 g averaging operator exact.
- **S-parameters, two-torus validation fixture only** (`PORT-1` ✅
  2026-08-15): field-derived through `run_n_port_sparameter_sweep`,
  reciprocity `‖S−Sᵀ‖/‖S‖ = 2.5494e-05` vs the 1e-3 gate — carrying the
  **two named systematics** of 3b-xviii (PEC box, an effective-range
  extrapolation; gap-generator feed model, Jin 3e §10.4.2.1). The retired
  heuristic is reachable only behind a `DeprecationWarning`.
  *Caveat lifted 2026-08-24 (`PORT-9` leg (d3), §9 item 2):* the sweep's
  S no longer comes via the terminated `Z` — the gated routes assemble it
  from power waves (`S_ij = b_i/a_j`), and on the asymmetric two-torus at
  the matched drive `Z_p = z0` the per-pair asymmetry fell from
  2.831857978e-03 (old conversion, same run) to **2.972992845e-15**. The
  `Z` this bullet's records once went through is retained as a documented
  *terminated transimpedance* diagnostic and is never reciprocity-gated.
  The two moved records were re-recorded route-tagged under (1\*) with no
  band moved (σ_max 0.864809457, `‖S−Sᵀ‖/‖S‖` 4.758625e-05); the
  gap-voltage route's undriven ports are not terminated in `z0`, so its
  residual is the route's own and stays gated at 1e-3. The two named
  systematics and the two-torus-only scope are unchanged.
- **Four lumped-sheet ports on the gapped 4-leg birdcage, at 10 MHz
  only** (`PORT-9` ✅ 2026-08-25, step 3 legs (c)/(d0)/(d)/(d1′)). Four
  driven solves on `GEO-18`'s gapped, sheeted fixture (116 085 cells,
  `f = 0.5`, `w = A/h`, `Z_p = z0 = 50 Ω`) assemble a 4×4 that passes
  three pre-stated gates: **(i)** `‖S−Sᵀ‖/‖S‖` ~ 1e-14 vs 1e-3 on the
  power-wave assembly; **(ii)** `σ_max(S)` = 0.999992805 ≤ 1 + 1e-9 with
  column power sums ≤ 0.793823974; **(iii′)** every C4 circulant class of
  `Z` spreads ≤ **0.5%** (measured 0.0553 / 0.0353 / 0.0214%), the band
  tightened from 5% with this closure. The gate has its **geometric
  negative control**: rotating one leg 22.5° breaks all three classes by
  two orders (6.2219 / 7.1142 / 2.8474%) while reciprocity holds at
  2.259e-14, and the pre-fix terminated-`Z` route read 5.57e-03 on that
  same displaced fixture — a 2.466e+11× separation. **Scope, hard:**
  10 MHz is the port model's frequency, not a Larmor frequency; this
  licenses no resonance, tuning, B1+ or SAR claim, and no figure at
  64/128 MHz (that is `PORT-11`, unrun). See §2.2.
- `post/evaluation.py` point location (all point evaluation goes through
  it), gmsh generation + tag QA, the runner, and the logging harness.

### 2.2 Not validated — do not trust, do not extend

- **The birdcage has ports at 10 MHz only; nothing is validated at a
  Larmor frequency, and no coil is tuned or resonant.** *(Rewritten
  2026-08-25 — `PORT-9` ✅ with leg (d1′). The old head of this bullet,
  "No coil or birdcage has ports", is retired: the gapped 4-leg birdcage
  now carries four lumped-sheet ports and a gated 4×4 — see §2.1. What
  remains unvalidated and is what this bullet now covers: **any**
  S-parameter, impedance or coupling figure for a coil at 64/128 MHz
  (`PORT-11`, unrun), any resonance, mode-spectrum or tuning claim
  (Phase 6, no lumped capacitors exist), and B1+/SAR on a solved coil field.
  The 16-leg *mesh* is now gated (`GEO-19` ✅ 2026-08-25 — CAD identities
  and a cost rung, **no solve and no port model at 16 legs**), and the
  32-port ring layout is still unbuilt above four legs (`GEO-20` step 2). The
  10 MHz result is a **port-model validation on a gated fixture**, not an
  MRI-regime result; do not quote it as one.)* The history below is kept
  because every band and convention in the port model was set in it. The
  birdcage-port direction is scoped —
  `PORT-9` (lumped/circuit-element port BC, Jin ch. 11) — and as of
  2026-08-16 both named prerequisites have **executed and closed**:
  `PORT-10` (the two systematics compose additively, cross-term
  −0.0604 pp) and `GEO-15` (graded conductor sizing reaches 0.967 of CAD
  mass; `PORT-9` budgets from 98 k cells). `PORT-9` **step 1 closed
  2026-08-17**: the mesh prerequisite `GEO-16` landed (longitudinal sheet
  on an opt-in kwarg, area = CAD to roundoff), the parked formulation
  branch was merged with its six exact identities green, and the first
  lumped-port `Z` was solved on the two-torus fixture at 10 MHz —
  `Im Z₁₂ = 0.829782 × ωM₁₂` against the gated gap route's `0.894310`,
  a cross-route deviation of **7.7095%**. **Step 2 executed 2026-08-17:
  both pre-stated bands MISS** (cross-route 7.7095% vs 5%, lumped mutual
  12.6931% vs 10%; the gap route stays inside at 6.0391%), neither
  widened, and the miss is **diagnosed** — it is the transverse average
  over the full-width sheet (7.7783 pp of it; path/projection residual
  only 0.0763 pp), a property of the two feed definitions on this box,
  not of the solver or the mesh. **Step 2b executed 2026-08-17 (12:00
  slot): the band HOLDS at the narrowed width** — ladder 7.7095% →
  3.6730% → **1.8333%** at f = 0.5 against the unmoved 5% band, f = 1.0
  reproducing step 2's record to < 1e-4. Step 2's gate is closed **at
  the narrowed definition**: a lumped port sheet is specified by its
  interior width fraction f and its width is measured as `w = A/h` on
  the filtered facet set — the convention is part of the port model's
  spec. **Step 2c executed 2026-08-18 (22:30 slot): the reciprocity leg
  is closed** — the lumped-sheet route landed in
  `run_n_port_sparameter_sweep` and the two-torus sweep is reciprocal at
  `‖S−Sᵀ‖/‖S‖ = 2.574249e-11` against the unmoved 1e-3 band, cross-route
  1.6079% / 1.5950% inside the 5% band, with **0.23 pp of drive
  dependence** off step 2b's impressed-gap 1.8333% — a lumped reading
  should be quoted with its drive stated. Step 3's gate (i) prerequisite
  is discharged. **Step 3 executed its preflight 2026-08-19/20 and is
  🚫-blocked on the mesh**: the birdcage fixture has no port-sheet facet
  (global facet set exactly `{1}`) and its port boxes have **no
  terminals** — conductor-facing area exactly 0.000000e+00 m² on all
  four, because the coil is uncut and the boxes float in air outside it.
  The prerequisite was `GEO-18` (cut the legs, boxes straddling the cuts;
  commissioned 2026-08-20) and it **closed 2026-08-22**: the gapped
  birdcage now has planar disk terminals (0.988616 of `2·π·r_leg²`) and
  a port sheet per leg gap (area = `dx·g` to 1.000000000000, C4 spread
  8.470e-16) — a mesh with somewhere to put a port. **Step 3 closed
  2026-08-25** across legs (c)/(d0)/(d)/(d1′): see §2.1's birdcage-port
  bullet for what it licenses. B1+ remains §10 subgoal 4, and is now
  blocked on `PORT-11` (the same three gates at 64/128 MHz), not on
  `PORT-9`.
- **Coil loading at the Larmor frequencies is an extrapolation.** The
  apparent frequency trend is now attributed: `TH-11` step 4's fixed-f
  h-ladders read **flat in f** — the h → 0 brackets [−2.15, −0.91]% at
  10 MHz and [−3.37, −0.38]% at 30 MHz overlap at ~−1%, so the monotone
  three-point set 1.58 / 5.59 / 10.27% was the resolution term, not
  physics. That is printed evidence adjudicated by the 2026-08-17 review,
  not a gate, and 64 MHz itself still has **no h → 0 bracket** (finest
  rung +2.81% at 2.52 cells/δ). **The degree-1 h-ladder to that bracket
  is closed as a measured negative** (`TH-11` step 5, adjudicated
  2026-08-18 10:30 review): the memory wall is superlinear in cells —
  0.42 M cells comfortable, **0.99 M pegs `memory.peak` at
  `memory.max` = 64.00 GiB**, 2.81 M OOMs at every legal rank count
  (MUMPS factor fill-in) — and an affordable third rung would need a
  refinement ratio ≈ 1.2 whose difference signal sits at the 0.01 pp
  run-to-run floor, so the fit would be noise. **The degree-2 axis is
  now measured too** (`TH-12` step 2, 2026-08-18): on the 138 619-cell
  coil fixture at 10 MHz, degree 2 walks the coarse-rung ΔR deviation
  +1.5834% → **−0.8508%** — h → 0 quality on an unrefined mesh — but at
  **61.94 GiB summed peak RSS (96.8% of `memory.max`)**, i.e. against
  the same wall, and the 64 MHz case needs ~2.5× the cells at fixed
  cells/δ. **Adjudicated 2026-08-18 18:00 review: no affordable
  (order, h) route to a gated 64 MHz h → 0 bracket exists on this box**
  — there is no rung swap to scope, and the degree-2 reading stands as
  corroborating evidence from the order axis, not a gate. This bullet
  moves only when a review adjudicates a gated 64 MHz bracket (which
  now requires either more memory or an out-of-core/iterative solver
  path, neither scoped).
- **SAR on a solved coil field** — the IEEE C95.3 claim — is open;
  `MAT-4` stays 🟡 until it exists on the coil+phantom fixture.
- **`⚠️` chunks** (`TH-2`/`TH-3`, `PORT-4`/`PORT-5`/`PORT-8`, `WF-2`/
  `WF-3`, `MAT-1`) carry code whose tests assert too little to protect
  them; revalidate before building on them. `OPS-17` (§7, ✅ 2026-08-21)
  removed or replaced the finiteness-only tests themselves and reconciled
  the complex-suite baseline (216 of 232 validation tests observed in
  completed complex runs; the two absentees are formally deferred with
  reasons); the `⚠️` glyph stays until each chunk's own physics is
  revalidated.

### 2.3 Before you debug a failing test

**Check [`docs/testing/known-issues.md`](docs/testing/known-issues.md)
first.** It lists every currently-failing test with symptom, the commit it
was verified failing at, and the diagnosed cause. Several tests fail on
`main` for reasons unrelated to any change you are making.
---

## 3. Status legend

| Symbol | Meaning |
|---|---|
| ✅ VERIFIED | Test executed, assertion is quantitative, passing |
| 🟡 IN PROGRESS | Actively being implemented |
| 🧪 UNVERIFIED | Code landed; test has never actually executed anywhere |
| ⚠️ PLACEHOLDER-BACKED | Implemented and "green", but the green rests on tests that assert too little (§2.2) |
| ⬜ NOT STARTED | |
| 🚫 BLOCKED | Cannot proceed; blocker named in the chunk |

`⚠️` is not a bug report against the chunk's own code — it means the chunk
cannot be trusted until revalidated against the real solve (`OPS-17`, ✅
2026-08-21, replaced the tests; the glyph itself retires per chunk as each
one's physics is revalidated). Do not "fix" a `⚠️` chunk by
loosening its test.

**A measurement-only step is `🧪`, never `✅`** *(clarified 2026-08-02, 18:00
review, after an audit found two probe steps carrying `✅`)*. Several chunks are
split into a probe step whose stated product is "measurements, assert nothing"
and a gate step that turns those measurements into bounds. The probe step lands
real code and real logs, but §4.3 asks for an executed quantitative *assertion*,
and a script that only prints has none — so the probe step is `🧪` until its
gate lands, however good its numbers are. This is a clarification of §4, not an
exception to it: the fix is to write the gate, never to widen §4. Demoted on
this ground 2026-08-02: `PORT-1` step 1, `MAT-6` step 2a. (`PORT-1` step 1 was
restored to ✅ the same day when its gate, step 2, landed — which is exactly
the intended route back.)

---

## 4. Definition of done

A chunk is `✅ VERIFIED` when **all** of the following hold:

1. **Code and docs are committed.**
2. **The agent executed the verification command itself** and recorded the result
   via `scripts/testing/run_and_log.sh`. A chunk does not park on a human.
3. **The assertion is quantitative** — at least one check compares against:
   - a closed-form analytic solution, with a stated tolerance
   - a measured convergence rate under h- or p-refinement
   - a conservation, reciprocity, or symmetry identity
   - a documented reference value from literature or a prior validated run

   > **Finiteness-only gate:** a chunk may **not** be `✅` if every assertion it
   > adds is "is finite", "is non-zero", "has shape N", or "did not raise". Those
   > are welcome as *additional* assertions and insufficient as the *only* ones.
4. **Its runtime tier is declared and its measured elapsed time recorded.**
5. **Any dependency on a `⚠️` chunk is stated explicitly** in the chunk entry.

Never loosen a failing assertion to make a test pass. A failing analytic
comparison is evidence about the test as much as about the code.

### When human verification *is* required

Reserve it for judgments a test cannot make, and name the judgment: "does this B1+
map look physically plausible in ParaView?", "is this refinement acceptable near
the port faces?", "does this S11 curve resemble published birdcage behavior?"
Never for routine pass/fail.

---

## 5. Execution policy

### 5.1 Compute budget — shared machine

The development server is a **shared 36-core box; this project may use at most 12
cores.** Every verification command declares a tier and must not exceed it:

| Tier | Ceiling | Use for |
|---|---|---|
| `smoke` | 30 s | Imports, pure-Python logic, config validation |
| `standard` | 3 min | Coarse meshes, single small solves — the default |
| `heavy` | 20 min | Convergence studies, sweeps — must be labeled `heavy` |

- Wrap commands in `timeout -k 30 <s>` at the tier ceiling — the `-k` is
  mandatory: a plain TERM does not reliably stop an `mpiexec` job, and an
  overrun can wedge the container (MAT-6 step 10, 2026-08-12; known-issues has
  the recovery recipe). **If a run overruns, kill it and
  redesign the case smaller.** Never re-run with a longer timeout. 20 minutes is a
  hard ceiling for any single compute command regardless of tier.
- **`mpiexec -n 12` is the hard rank ceiling.** Use the smallest count that fits
  the tier — more ranks on a fixed mesh stop paying quickly, and a bigger mesh is
  usually a better use of the budget than more ranks on a small one. Keep `-n 2`
  for anything a rank-local bug could hide in (`MAG-11` was a missing allreduce
  visible only under MPI), and note that CI runs at `-n 2`, so a test that only
  passes at wider ranks is not CI-portable.
- **Memory ceiling: the container is capped at 128 GiB** (`docker-compose.yml`
  `deploy.resources.limits.memory`; raised from 64 GiB by operator directive
  2026-08-24, host has 754 GiB). Read it from
  `/sys/fs/cgroup/memory.max` rather than assuming — `memory.peak` does not
  exist at container level on this box, so track `memory.current` between
  commands. **Memory is a tier dimension like time:** a case that pegs the
  ceiling is redesigned smaller, never granted more. Raising the limit is an
  operator decision, not a chunk's (§9 standing constraint).
  **⚠️ Several recorded negatives were measured against the *old* 64 GiB wall
  and are not evidence about this box any more** — `TH-11` step 5 (2.81 M
  cells OOM, 0.99 M pegged), `TH-12`'s degree-2 wall (61.94 GiB on the coarse
  rung), `OPS-17`'s `coil_loading_degree2` deferral, and the §10 epitaph
  killing the coil-loading-trend target. None of them is automatically
  reopened: re-pricing one is a **review** decision, and any revival needs its
  finest rung priced first (the epitaph's own lesson). Do not cite "does not
  fit the box" from a pre-2026-08-24 measurement without re-measuring.
- Record real elapsed time in `docs/testing/test-results.md`.
- **A tier is a measurement, not an intention.** A chunk whose runtime has never
  been measured is `unmeasured`. Cost-probe first: build the mesh, print the cell
  count, solve a tiny case, extrapolate, then size the real case to fit.

Cost is dominated by mesh size: ~8×10³ cells solve in seconds, ~4×10⁵ cells take
minutes, and CI cannot host the `heavy` tier.

### 5.2 Agent autonomy and loop hygiene

- Agents implement **and verify**. Human-gated completion is prohibited (§4.2).
- **No-op guard:** if a work cycle produces only documentation edits and executes
  no verification command, stop and escalate rather than commit an audit note.
- **Do not append duplicate status blocks.** Status lives in §7 tables. (The
  legacy human-gated queue `docs/testing/pending-tests.md` and its
  `AWAITING-HUMAN-TEST` status were removed 2026-08-04 — verification is
  agent-executed per §4; the old queue survives in git history.)

### 5.3 Verification environment — Docker

All verification runs inside the `fem-em-solver` container. Preflight
`docker compose -f docker/docker-compose.yml ps` — STATUS must be "Up"; `exec`
fails with `service ... is not running` otherwise, and that is a *setup* error,
not a test failure. Do **not** use the `cd docker && ...` form: a `cd` inside a
compound command prompts for permission regardless of the allowlist, which fails
in scheduled sessions.

One-time setup: `docker compose -f docker/docker-compose.yml build` (~4 min), then
`... up -d`. The repo mounts at `/workspace`, so source edits need no rebuild.

| Property | Value |
|---|---|
| Image / base | `fem-em-solver:latest` on `dolfinx/dolfinx:v0.11.0` |
| dolfinx / Python | `0.11.0.post0` / 3.12.3 |
| numpy / gmsh | 2.4.6 / 4.15.2-git-657c8e9 |
| h5py / HDF5 | 3.16.0 / 2.1.1 (built from source against the image's HDF5) |
| petsc4py / mpi4py | 3.25.1 / 4.1.2 |
| Default PETSc scalar | `numpy.float64` — **real mode** |
| Complex build | `/usr/local/dolfinx-complex` |
| Memory cap | 64 GB (raised from 16 GB by `MAT-6` step 7, operator-approved 2026-08-10) |

Upgraded 0.7.2 → 0.11.0 by `OPS-18` (2026-08-23, step 3b), measured on the
built image in `20260823T200740Z_OPS-18-step3b-env-probe.log`. The compose
`PYTHONPATH` literal (`.../lib/python3.12/dist-packages`) is the **only**
version-encoded path in the project — the `dolfinx-{real,complex}-mode`
wrappers and `src/sitecustomize.py` derive the tag themselves. The gate
`tests/environment/test_dolfinx_version.py` asserts the adopted version, and
derives the expected Python tag from `sys.version_info`, so the next upgrade
fails loudly rather than silently importing the wrong tree.

**Complex scalars**, required by `TH-1`:
`source /usr/local/bin/dolfinx-complex-mode` (→ `numpy.complex128`);
`dolfinx-real-mode` switches back. The chunk commands set
`PYTHONPATH=/workspace/src`, which drops the container's dolfinx path;
`src/sitecustomize.py` re-appends the dist-packages directory matching the active
`PETSC_ARCH`, so imports resolve in **either** mode. Set
`FEM_EM_REQUIRE_COMPLEX=1` on any run that is supposed to be complex, so the
real-mode skips in `tests/environment/test_complex_mode.py` become failures, and
put `tests/environment` first in the pytest path list.

Run everything through the harness so results land in
`docs/testing/test-results.md` and `docs/testing/logs/`:

```bash
scripts/testing/run_and_log.sh <CHUNK-ID> "docker compose exec -T fem-em-solver bash -lc '...'"
```

Use `exec -T` — without it `exec` allocates a TTY and can hang under an agent. The
harness exports `COMPOSE_FILE` itself; a bare `docker compose` outside `docker/`
needs `-f docker/docker-compose.yml`.

### 5.4 Examples and Ansys cross-validation

- **`examples/` is a maintained product surface, not a scratch area.** Each
  phase keeps **at least five** clean, runnable examples demonstrating its
  capability from distinct angles (different geometries, materials, drives, or
  output quantities — five trivial variations of one case do not count),
  executed via `./run_examples.sh` and producing combined-XDMF output that
  opens in ParaView — this is how the human operator reviews progress
  independently of the test suite. When a chunk changes what an example
  demonstrates, the same commit updates the example. A broken example is a
  defect (known-issues discipline applies). **Examples accrue with gate
  closures, not at phase end**: each time a chunk closes a quantitative gate
  (§4 ✅), the next daily review enqueues a standalone example chunk
  demonstrating that newly gated capability (daily-review.md step 5). The
  audited bar for an in-progress phase is therefore a ramp —
  `examples ≥ min(5, gating chunks closed ✅)` — checked by the weekly review
  (weekly-review.md step 4); the flat five binds once the phase completes.
  *(Clarified 2026-08-09, weekly review: the ramp binds the physics phases
  1+. Phase 0's infrastructure capability — Docker, CI, the harness, the
  runner — is exercised by every example run and does not owe a separate
  example set; its meshing slice is covered by the `mesh:` group.)*
  Example chunks are their own §7 entries sized for one implementer run,
  never riders on physics chunks, and never target ungated capability.
  *(Operator directive 2026-08-10:)* **every runnable example also ships
  with a same-stem step-by-step guide page** — what it demonstrates, how
  to run it, and how to analyze the output step by step so the operator
  can understand what is going on without reading the source (required
  sections and the mechanical gate: §7 `EX-15`). A missing or stale guide
  is a defect like a broken example; the doc-reference checker enforces
  presence and structure, and the weekly review audits guides with the
  ramp. Example chunks scoped after 2026-08-10 include the guide page in
  their done-when; the pre-existing examples are backfilled by `EX-15`.
- **Ansys benchmark cases** live in `examples/ansys_benchmarks/<case>/`, each
  containing: `SPEC.md`, precise enough to replicate in Ansys Electronics
  Desktop with no judgement calls (geometry with dimensions, materials,
  boundary conditions, port definitions, frequencies, mesh guidance, and
  exactly which quantities to export); the runnable script; our results
  (metrics JSON + XDMF); and `COMPARISON.md` with our numbers filled in and
  blank columns for the AED numbers.
- **Cadence is the weekly planning review's call**
  (docs/automation/weekly-review.md) — roughly one case per phase milestone,
  and only on gated capability. A benchmark on ungated physics wastes a
  licence-hour measuring noise.
- **Returned AED numbers are adjudicated by the next weekly review**: recorded
  in the case's `COMPARISON.md`, promoted into §7 gates where they agree, and
  opened as known-issues/chunks where they disagree — a disagreement with the
  commercial solver is a finding to diagnose, never to explain away.

---

## 6. Phase map

| Phase | Goal | Gating chunks | State |
|---|---|---|---|
| 0 | Infrastructure, packaging, CI, meshing | `OPS-1`, `OPS-2` | Done |
| 1 | Magnetostatics + analytic validation | `MAG-1`…`MAG-6` | **Complete and trustworthy** |
| 2 | Time-harmonic Maxwell, complex materials, ABC/PML | `TH-1`…`TH-9` | In progress — every analytic gate closed (`TH-1`/`TH-6`/`TH-7`/`TH-8`/`TH-9` ✅); Larmor sphere `TH-10` ✅; coil trend `TH-11` ✅ closed on a measured negative (no 64 MHz h → 0 bracket fits the box, 2026-08-18); degree-2 `TH-12` steps 1–3 ✅, production order decided degree 1 for coil-fed solves (§10, 2026-08-23), `TH-13` discriminator open; `TH-2`/`TH-3` API hardening ⚠️ |
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-6` | `MAT-2` ✅; `MAT-6` ✅ (ΔR to 1.58% pinned / 1.5834% on the production projected drive, step 3; eddy-current regime); SAR gated on an **imposed** uniform field only (`MAT-4` steps 1+3: lossy-sphere closed form 3.5%, mass-averaging exact at 1 g/10 g) — coil-driven SAR and the C95.3 claim still open |
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-11` | `PORT-1` ✅ 2026-08-15 (field-derived S through the package, two-torus fixture only, two named systematics); `PORT-10` ✅ 08-16; **`PORT-9` ✅ 2026-08-25 at 10 MHz on the gapped 4-leg birdcage** — leg (d1′)'s geometric negative control passed on the power-wave route (displaced classes 6.2219 / 7.1142 / 2.8474% vs the tightened (iii′) 0.5%, reciprocity 2.259e-14 vs 1e-3, 2.466e+11× from the pre-fix 5.57e-03), no Larmor/resonance/tuning claim; history: steps 1–2c ✅ on the two-torus (lumped-sheet BC, 1.8333% cross-route, reciprocity 2.6e-11), step 3 on the gapped birdcage has two gated legs (c)/(d0) at 10 MHz (C4 spread 0.0152–0.0159% vs 5%, 50 Ω termination separates the classes 598× — re-recorded image-tagged on the 0.11 image 2026-08-24 by leg (d3c): 0.0359%, 253.2002×) and **leg (d) closed 2026-08-23 — the 4×4 passes all three gates** (reciprocity 2.495292352e-05 vs 1e-3, σ_max 0.862659137 ≤ 1, class spreads 0.0199 / 0.0180 / 0.0108% vs 5%, gate (iii) since tightened to 0.5%); leg (d1)'s geometric control ran 2026-08-23 and **found the route loses reciprocity (5.57e-03 vs 1e-3) once the fixture is asymmetric**; leg (d2) (asymmetric two-torus, 13:30 slot) traced it to the assembly — the readout *is* the source's adjoint (1.33e-10), the asymmetry is the terminated-`Z` per-column normalisation — and the 18:00 review ruled the power-wave S fix (leg (d3)) with the class re-record (d3b), (d1′) serial on (d3b); `PORT-11` (64/128 MHz) scoped 2026-08-23, serial on it; `PORT-4`…`PORT-8` open |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 for excitation; both meshes (coil+phantom, birdcage) generate and are identity-gated in CI (`GEO-9`, 2026-08-03); the birdcage fixture is loaded (phantom inside) and since `GEO-18` ✅ 2026-08-22 has terminals and port sheets — the first B1+ chunk is scoped by the daily review when `PORT-9` closes (§10 subgoal 4) |
| 6 | Birdcage tuning at 64/128 MHz: mode spectrum, lumped capacitors, circuit co-simulation (the HFSS + Circuit split); production target: **32-port high-pass birdcage at 1.5 T** (§10 operator directive 2026-08-17); **fixture scale re-directed 2026-08-25 — two fixtures, F-small (today's 0.07 m gate fixture, records frozen) and F-human (≈ 0.15 m radius / 0.30 m long high-pass, the deliverable fixture); the `N ≤ 25` ceiling was arithmetic on the wrong radius and dissolves at human scale. Full directive in §10 Phase 6 — the 2026-08-30 weekly review must dispose of it, cost probe first** | subgoals owned by the weekly review (§10); mesh prerequisites `GEO-19` (16 legs, cost rung) + `GEO-20` (ring-gap ports) scoped 2026-08-23 | Not started — mesh prerequisites may run any time (CAD-identity gates); physics subgoals wait on `PORT-9`/`PORT-11` |
| 7 | Implants: parametric implant geometry in the phantom, local SAR / near-implant hot spots | subgoals owned by the weekly review (§10) | Not started |
| 8 | Thermal: Pennes bioheat driven by SAR | subgoals owned by the weekly review (§10) | Not started |
| 9 | Advanced: MPI scaling, AMR, sweeps, optimization | — | Deferred |

Phases 6–8 are the 2026-08-04 scope adjustment (§1). Their phase goals and
subgoals live in §10's long-horizon roadmap and are **owned by the weekly
planning review**; the daily review breaks current-phase subgoals into
implementer-sized items and does not restructure phases.

### Critical path

```
TH-1 (real complex time-harmonic formulation)
   ├─> TH-6/7/8 (analytic validation gates)
   ├─> MAT-2 ──> MAT-6 (materials actually affect fields; Dodd–Deeds)
   └─> PORT-1 (real port excitation) ──> PORT-2…8 ──> WF-5…8
```

**`TH-1` landed 2026-07-31 and `PORT-1` closed 2026-08-15; the constraint
moves down the chain.** The `⚠️` backlog still may not be extended until
revalidated against the real solve, and nothing S-parameter-shaped beyond
the two-torus fixture grows except through the scoped birdcage-port lineage
(`PORT-9` at 10 MHz → `PORT-11` at 64/128 MHz, 2026-08-23).

---

## 7. Chunk backlog

IDs are prefixed by subsystem and **globally unique and stable**. Legacy
`A1`/`B2`/`C3` IDs in commit messages and old logs map here via §8.
These tables are the authoritative *status*. Closed chunks and steps keep
compressed result blocks here (gated numbers, dates, log IDs, live
carry-forwards); their full plans, execution journals and audit narratives are
archived verbatim in `docs/planning/plan-archive.md` — grep there before
re-deriving a closed step's diagnosis. (The older per-chunk log,
`docs/testing/pending-tests.md`, was removed 2026-08-04; see git history.)

### OPS — Infrastructure & testing operations

| ID | Title | Status | Tier |
|---|---|---|---|
| `OPS-1` | Executable verification environment (Docker) | ✅ | smoke |
| `OPS-2` | CI runs the real test suite, not just `tests/unit` | ✅ | standard |
| `OPS-3` | Deterministic test tolerance policy | ✅ | smoke |
| `OPS-4` | Lightweight smoke matrix | ✅ | smoke |
| `OPS-5` | Testing status dashboard | ✅ | smoke |
| `OPS-6` | Expanded run-and-log metadata | ✅ | smoke |
| `OPS-7` | Guided pending-test queue helper *(retired 2026-08-04 — queue tooling removed; verification is agent-executed per §4)* | 🧪 | smoke |
| `OPS-8` | v1 milestone acceptance checklist | 🧪 | smoke |
| `OPS-9` | Prune duplicate/stale entries from `pending-tests.md` | ✅ | smoke |
| `OPS-10` | Complex-mode CI job for the frequency-domain gates | ✅ | smoke |
| `OPS-11` | Put `tests/mesh` in CI — the directory no job runs | ✅ | smoke |
| `OPS-12` | Adjudicate the residual-trend classifier (known-issues 2) and return `test_convergence_diagnostics.py` to CI | ✅ 2026-08-08 | standard |
| `OPS-13` | Land the rank-safe `_validate_material_map_tags` fix on `main` with its own gate | ✅ 2026-08-08 | standard |
| `OPS-14` | Diagnose the rank-dependence of `test_single_port_excitation` (known-issues 6) | ✅ | standard |
| `OPS-15` | Retire the checker's standing freshness tax: default `--max-age-s` 1 h → 48 h | ✅ 2026-08-10 | smoke |
| `OPS-16` | Retry-on-529 in the three automation launchers (two review slots lost 2026-08-13; rubric in the §9 item) | ⬛ **WON'T FIX — operator decision 2026-08-22** | smoke |
| `OPS-17` | Delete or replace the finiteness-only test suites (operator directive 2026-08-16) | ✅ **closed 2026-08-21, 18:00 review** — leg (b2) closed at **216 of 216 runnable** validation tests observed in completed complex runs: the two deferrals formally adopted (`coil_loading_degree2` 14, skips = the adjudicated `TH-12` memory wall; `port_gap_voltage_padding` 2), denominator re-based 232 → 216 on the 00:00 slot's independent collect audit; steps 1–3 all ✅ ⇒ chunk ✅, `OPS-18` queued per the commitment. Full history: steps 1–2 ✅ (14 dispositions landed; 4 defects surfaced, 3 carried as strict xfail; step 3 🟡 attempts 1–2 2026-08-17 — sweep anchor restated 45 → **56, reconciled**; a completed leg found a silent `_DummyComm` regression from `PORT-1` step 4; **leg (a) closed attempt 2** — all 377 real-mode tests observed in completed legs, 171 + 206 exact, every failure named; leg (b) attempted 2026-08-18, **both complex commands exit 124** — complex mode is >2.6× real on the same tests, the leg needs three commands and likely two slots; **rescoped 2026-08-18 03:00 review as (b1) remainder + (b2) validation**, one slot each; **(b1) attempt 1 2026-08-18 🟡 — command 1 completed (3 failed / 122 passed / 1 xfailed, 392.76 s, the three failures exactly the named expected ones, one rank-dependent XDMF count delta), command 2 exit 124 at 44%: complex `tests/solver` is > 12× real, not 2.6×. The leg's real finding is that attempt 3's "cache artifact" call was wrong — on a cold cache `test_coil_phantom_magnetostatics` fails in 5.58 s with a genuine `ComplexComparisonError`**; **(b1) attempt 2 2026-08-18 ✅ CLOSED — complex `tests/solver` runs as one command, 46 passed / 2 xfailed in 111.22 s, exit 0, both ranks identical; counts reconcile to 171 non-validation complex, the same 171 leg (a) observed; defect 3's th-smoke Poynting xfail finally read in a completed leg; the ">12× real" rule is **withdrawn** as a cold-cache FFCx-JIT artifact — warm complex is ~2.7× real, and `test_gauge_penalty.py`, which killed the 480 s cold leg at 61%, is 8 passed in 20.33 s warm**. *Leg (b1) audited COMPLIANT 2026-08-18 10:30 review — the 49 = 48 + 1 and 171/209 reconciliations re-derived from the log footers, both ranks identical in the closing leg; the coil-phantom exclusion is within the written anchor (observed FAILED in its own completed log `20260818T124712Z`, two known-issues entries), with the caveat on record that the completed observation shows the warm-cache message while the genuine `ComplexComparisonError` appeared in an exit-124 run — the three-state map is disclosed in known-issues*; only leg (b2) remains; **(b2) attempt 1 2026-08-19 🟡 — three commands completed (impedance file `24 passed`/488 s; cost probe re-bases the stale 380 collect to **397**, validation **225**; shortest-first subset `23 passed`/121 s with the per-file sinks priced), then the written negative-result clause fired: `test_circular_loop.py` **cannot JIT-compile one form in the complex build**, reproducibly and independently of cache state — new known-issues entry, which also names the **0-byte FFCx stub** trap that mis-attributes such failures as cache artifacts (a stale stub from 2026-08-18 14:02 was still in the cache). Coverage 39/225; 186 remain, 3 blocked**; **(b2) attempt 2 2026-08-19 🟡 — the prescribed 4×-larger batch lost its window to a *second* instance of the same defect (`test_helmholtz_magnitude` FAILED at 62%, `test_helmholtz_v2` hung, exit 124; 9 passes uncounted for want of a footer), and the slot instead **diagnosed the cause**: the fixtures' own `current_density` callables use `ufl.max_value` / `<=` geometry predicates that UFL forbids on complex operands — `ComplexComparisonError` in 13.10 s for helmholtz, a swallowed FFCx root-node failure in 113.38 s for circular_loop, both on the load form at `solvers.py:385`. `src/` has **no** `max_value`; three sibling test files already document the fix (regularise inside the `sqrt`). **Fixture debt, not a solver defect**, and the same family as `OPS-20`. Coverage still 39/225; blocked 3 → 5**; **rescoped 2026-08-19 03:00 review** — the fixture fix is commissioned as `OPS-22` and queued first, (b2) resumes under **per-file completed-run accounting**, anchor re-based to 225 validation / 398 total, the +1 non-validation delta attributed benign (`POST-5` step 1's dropped `def` + 2 added tests); **re-adjudicated 2026-08-19 10:30 review — every (b2) blocker discharged**: the 5 blocked tests are observed in `OPS-22`'s completed log `20260819T094710Z` (coverage re-bases 39 → **44**/225 under per-file accounting), the (b1) coil-phantom exclusion is discharged by `OPS-20`'s completed log `20260819T110144Z` (same 30% gate, 17.1233%, complex), and the twice-measured suite-growth warning — complex `tests/solver` no longer fits a 480 s window warm — is folded into the §9 item; **(b2) attempt 3 2026-08-19 🟡 — first clean run under the rescope: two completed runs, `14 passed`/400.01 s and `13 passed`/52.69 s, both exit 0 and both ranks identical, **+19 validation tests ⇒ coverage 44 → 63**; anchor re-based 225 → **227** validation / **402** total and reconciled exactly to `POST-5` steps 2–3, closing attempt 1's unattributed +1; **blocked 5 → 0**, `OPS-22` having discharged the risk class; two exit-124 windows were sizing errors with no failure and no hang signature, and priced the SAR/padding group at > 400 s for five files. Tail 162 runnable in ~35 files, now the expensive half — next leg takes one `coil_loading_*`/`dodd_deeds_*` family per slot at 540 s**; **(b2) attempt 4 2026-08-20 🟡 — `dodd_deeds_*` drawn, two completed runs at each file's *recorded* rank width (`combined_knobs` `8 passed`/**404.61 s** at `-n 8` vs the MAT-6 record's 421.90 s; `resistance_slab_resolution` `9 passed`/**386.85 s** at `-n 2` vs its record's 386.82 s, drift **0.008%**), every rank footer identical, no moved digit. Anchor re-based 227 → **232** validation / **412** total; **coverage 63 → 72**, tail 158 runnable, blocked 0. The "one family per slot at `-n 2`/540 s" prescription is **withdrawn**: two `-n 2` windows died at exit 124 — one batch inside its *first* file, one single file with its *first test* still in setup — and `--durations=0` shows the entire cost is a single module-scoped fixture setup (404.13 s / 386.41 s, every other call ≤ 0.03 s), so per-file accounting cannot split it. New rule: grep the file's own MAT-6 log for its recorded width and elapsed time before sizing; budget one file per ~400 s window, ~2 more slots for this family**; **(b2) attempt 5 2026-08-20 🟡 — the recorded-width rule executed as written, working first try on every command with **no exit 124**: three files counted in three completed complex runs, all exit 0 (`reactance_box_truncation` `9 passed`/**397.17 s** at `-n 8` vs its record's 426.17 s; `projected_drive` `8 passed`/**67.78 s** at `-n 2` vs 63.92 s; `dodd_deeds_impedance` **full file** `14 passed`/**87.43 s** at `-n 2`, the cheap marker subset `7 passed, 7 deselected`/1.29 s run first for the record). **Coverage 63 → 72 → 91 of 232**, tail 139 runnable, blocked 0; `dodd_deeds_*` is 28 of 38, the remaining 10 being exactly `box_size` + `wire_resolution`. Both open map caveats discharged: `box_truncation`'s "1 failed" record is superseded by a later `9 passed` one (no known-issues entry owed), and the impedance file's 3 `integration` tests, budgeted a window each, cost 87 s for the *whole file* — **the family's cost is bimodal**, ~400 s for the three mesh-refinement files (one module-scoped fixture setup) and an order cheaper for the rest, not a flat ~400 s per file. One benign rank asymmetry recorded: at `-n 2` the rank footers agree on outcome and elapsed time to the hundredth of a second but differ in *warning* count (rank-local UFL `Expr.ufl_domain()` deprecations)**; **(b2) attempt 6 2026-08-20 🟡 — attempt 5's prescription executed and **the `dodd_deeds_*` family closes at 38 of 38**: three completed complex runs, all exit 0, all at `-n 2` (`reactance_box_size` **full file** `8 passed`/**559.58 s** against its two recorded `-k` halves 271.08 s + 260.07 s; `wire_resolution` projected/refinement `8 passed, 2 deselected`/**499.80 s** vs the record's 491.96 s; `wire_resolution` pinned `6 passed, 4 deselected`/**242.68 s** vs 237.77 s, the two selections disjoint over that file's 6 validation tests). Every printed physics figure bit-identical to its `MAT-6` record (366207 cells; `dR` 1.5763 / 1.5713 / 1.0562 / 1.0558%; `dX` 0.9849 / 0.8740 / 0.9194 / 0.9189), only wall-clock differs. **Coverage 91 → 101 of 232**, tail 129 runnable, blocked 0. Two rules sharpened: the prescription's `-n 8` guess for `box_size` was **wrong** — the file is recorded twice at `-n 2` in its own step-4 logs, and the recorded-width rule caught it, so the rule stands unamended over family-level heuristics; and the cost model is **three-shaped**, not bimodal — `box_size`'s halves simply add (559.58 ≈ 271 + 260 + 28), so expensive files are either one-setup/unsplittable or per-test-solve/splittable at their recorded `-k` boundaries. `coil_loading_*` (58, unpriced) is all that remains of the tail's big blocks**; **(b2) attempt 7 2026-08-21 🟡 — `coil_loading_*` **priced from its own logs at no compute cost** (all 58 reconciled: two cheap 6-test files at ~70 s, `mesh_cache` 5, `third_rung` 7 env-gated at `-n 8`, `richardson_ladder` 14 rung-gated, `larmor_resolution` 6 at 390.89 s, and `degree2` 14 whose own record is `5 passed, 13 skipped` — the skips *are* the `TH-12` memory wall, so the file is a **defer-with-reason**), then opened: one exit-124 window and one completed run, `16 passed`/**137.18 s**/exit 0 at `-n 2`, both rank footers identical ⇒ **coverage 101 → 113 of 232**, tail 117 runnable, blocked 0, `coil_loading_*` 12 of 58. Two rules for the review: the operator flag's `memory.peak` instrument **does not exist at container level** (pinned at `memory.max` = 64.00 GiB by the `TH-11` OOM, on a read-only mount, unresettable — use `memory.current` between commands: 21.6 MB idle → 446.8 → 455.1, no strays); and the recorded-width rule is **necessary but not sufficient** — a family's *first* complex command pays a one-time JIT cost ~2.4× its warm cost (the same two files that ate a 480 s window cold ran in 137.18 s warm, −4.4% vs their combined 143.5 s record), so size a family's first command at recorded elapsed × 3 or warm the cache on a small file and count nothing**; **(b2) attempt 8 2026-08-21 🟡 — attempt 7's two-slot prescription **landed in one slot**: three completed complex runs, all exit 0, every rank footer identical (`larmor_resolution` alone at `-n 2` **10 passed**/**427.15 s** vs its record's 390.89 s, +9.28%; `larmor_mesh_cache` at `-n 2` **9 passed**/**445.55 s**; `larmor_third_rung` at `-n 8` **11 passed**/**174.86 s** vs its record's 172.40 s, +1.43%). **Coverage 113 → 131 of 232**, tail 99 runnable, blocked 0, `coil_loading_*` **30 of 58**; run 3's `-s` physics is bit-identical to the `TH-11` rank-control record (417914 cells; `P_loss` loaded +5.8523036e-01 W, free exactly 0.0 W; `ΔR` +1.3838746e+00 Ω, `ΔX` −5.8741123e+00 Ω, deviation +2.8063%, ΔX ratio 0.9514), only wall-clock differs. Three findings: the recorded-width rule gains **read *all* of a file's logs, not the first match** — the prescription's two `-n 8` `MODE=loaded|free` commands (201 s) are dominated by one `MODE=full` command (172.40 s), and the split route's own `skip` messages are what make it look mandatory; the operator flag's memory wall is the **rung, not the file** — `TH11_STEP5_RUNG=third` at `-n 8` is **status 137 at 908 s**, that log *is* the `TH-11` OOM, and `third` is the fixture's **default**, so pin `fine` (`memory.current` 21.5 MB idle → 425.5 MB across all three runs, `pgrep -c python3` = 0 throughout); and the real→complex ratio is measured **directly at 3.15×** on `mesh_cache`, the family's only real-only record. `richardson_ladder` (14) is the last drawable block; `degree2` (14) still awaits its formal review-level defer**; **(b2) attempt 9 2026-08-21 🟡 — `richardson_ladder` took **one** command, not the prescribed two, and the freed window closed the SAR/padding group: two completed complex runs, both exit 0, both rank footers identical (`richardson_ladder` at `RUNG=baseline FREQ_MHZ=10,30`, `-n 2`, **18 passed**/**140.25 s** vs its record's 135.83 s, +3.25%; the five SAR/padding files at `-n 2`, **14 passed**/**247.68 s**). **Coverage 131 → 155 of 232**, tail 75 runnable, blocked 0, `coil_loading_*` **44 of 58** — the whole family bar `degree2`. Run 1's `-s` physics is bit-identical to the `TH-11` step-4 baseline record on 15 of 17 lines (138619 cells, `I'` 0.919666 A, `dR` deviations +1.5834% / +5.5912%, `dX` ratios 0.9200 / 0.9500, free `P_loss` exactly 0.0 W); the only two that differ are the complex-power identity **residuals** at ~1e-14 against their own 1e-09 bound — machine noise, not a record. Two rules: **a rung/mode env var that changes the mesh is not a test-set partition** (the collect log's 14 IDs are 7 × two frequencies, all of them in the baseline command; attempt 8's split inference cost a budgeted 560 s window), and **a dead window quotes a *cold* price** — attempt 3's "> 400 s" for the SAR/padding group measured 247.68 s warm with 54% unused, so re-measure before deferring a group as expensive. Both big families are now closed. **Then, in the same slot, the leg finished**: six more completed complex runs, all exit 0, all `-n 2`, every rank footer identical (`port_lumped_bc`+`two_torus` 15 passed/98.20 s; `port_systematics_composition` alone 7 passed/**360.23 s** vs its own `PORT-10` record 352.37 s — the batch-C killer needed a window of its own; `poynting_balance`+`sheet_sweep` 18 passed/242.80 s; `package_sparameters`+`narrowed_sheet`+`solenoidal_drive` 19 passed/350.80 s; `lossy_sphere_fullwave`+`port_reaction_impedance` 16 passed/210.18 s; `degree2_energy_mechanism`+`lossy_sphere_degree2` 10 passed/12.08 s). **Coverage 155 → 216 of 232 — the runnable tail is exhausted**, 232 − 14 (`coil_loading_degree2`) − 2 (`port_gap_voltage_padding`) = 216 being exactly the reachable denominator attempts 7–8 asked for, reconciled by footer arithmetic (4 env + N validation, 85 banked this slot). Eight commands, **no exit 124**, no assertion touched, nothing filed. Third rule: **a padded record is an upper bound on the unpadded file, not an estimate**. **The leg now awaits one review decision, not three** — formally defer the two files and adopt the 216 denominator, and leg (b2) closes on this slot's logs with nothing further to run**) | standard |
| `OPS-18` | DolfinX version upgrade, recurring (0.7.2 → newest qualifying; operator directive 2026-08-16) | 🟡 **steps 1–2 ✅ 2026-08-22** — `0.11.0.post0` builds and boots in both modes on `attempt/OPS-18` (`c767171`), negative control fires; step 2 closed the same day, **`418 collected / 0 errors` in both modes** against the red baseline's `124 / 75`, the whole migration being one module (`io/mesh.py`: `gmshio` → `dolfinx.io.gmsh`, `MeshData` unpacking, 11 call sites, one shim) and validation unmoved at 232. One new-gmsh volume drift (4.251e-04 relative) filed to known-issues for step 3 to dispose of; no assertion touched. **Step 3 attempt 1 2026-08-22 🟡** — three of five gate families reproduce (`TH-6` 3.609441e-02 / α 0.017% / β 0.060%; `TH-10` bit-identical at 64 MHz, 3.643% and power 3.629%, with 128 MHz re-recorded 1.826% → 1.769% *with* its mesh 55 251 → 55 241 cells; `MAT-4` SAR 3.422% / 3.536%), after fixing the pack's second wave, which fires only under a **solve**: `petsc_options_prefix` × 7, `functionspace` × 1, and the undocumented `interpolate(cells=)` → `cells0=` × 2. `MAT-6`, `PORT-1`, the real-mode leg and §5.3's table remain. **Step 3 attempt 2 2026-08-22 🟡** (`3cbd5b5`) — `MAT-4` gets the clean green log it owed (`9 passed`/35.83 s/exit 0), `MAT-6` re-gates green on its impedance file (`24 passed`/88.60 s with `port_lumped_bc`, +1.3% on the record) and on the §2.1 ΔR site (`projected_drive`, 8 passed); one more undocumented break fixed (`create_cell_partitioner` now requires `max_facet_to_cell_links`, 1 site, value 2). **`PORT-1` blocked, cause measured:** the image's **numpy 2.4.6** renders `f"{np.float64(x)!r}"` as `np.float64(…)`, so `two_torus_domain`'s gap-arc `MathEval` string carries a token **gmsh 4.15.2** cannot parse — SIGABRT at Meshing 1D. Two probes separate grammar from literals; fix is a `float()` coercion, one slot away. Real-mode leg and §5.3's table still owed. **Step 3 attempt 3 2026-08-22 🟡** (`445a3ea`) — **`PORT-1` meshes again**: the `float()` coercion turns the SIGABRT into `17 passed / 2 failed` in 260.93 s, and the prescribed `!r` sweep is measured (53 hits in `src/`, 4 parser-facing, **one** `MathEval` call site in the whole package — the predicted birdcage siblings do not exist). A **fifth** undocumented break fixed: `element.interpolation_points` is now a property, not a method (2 `src/` sites, 4 in `examples/`), taking the real-mode `MAG` leg from `5 failed / 13 passed` to `17 passed / 1 failed`. **Both legs then stopped on records that moved, not code that broke** — `PORT-1`'s `passivity_max_sigma` 0.861356895 vs 0.861449 (band 1e-6) and gap ratio 0.894141 vs 0.894310 (band 1e-4) *while* reciprocity holds at 3.112128e-05 inside its 1e-3 physics band and passivity holds; and `test_straight_wire_b_field` at 15.3848% vs a 15% band that the test records as 1.18× the measured error of a mesh gmsh has since grown 145 900 → 147 235 cells. Two known-issues entries, no band touched; disposal is a review decision. **Step 3 attempt 4 2026-08-22 🟡** (`231d6c7`) — both experiments those entries named were run, and they **split the two failures apart**: the two-torus mesh **moved** (184 919 → 184 176 cells, −4.017e-03, i.e. 24-40× the records' misses ⇒ mesh reading *consistent* for leg 1), while the straight-wire ladder **refutes** it for leg 2 — the other two rungs mesh to within 0.13% of their recorded counts on 0.11 yet move −1.6% and **−51.8%** in error (9.2568% → **4.4605%**), with a 0.7.2 control reproducing July's record to 0.035%. The fitted rate goes **1.10 → 1.99** and the gated rung h = 0.0025 is a **1.8× outlier on its own 0.11 ladder** that `-n 4` reproduces bit-identically (partitioning excluded). 0.11 is the *more* accurate solver here, so loosening the 15% band is likely the wrong disposal; still owed are the review's re-record ruling (leg 1) and one cheap `n_points` probe on leg 2's outlier. **Step 3 attempt 5 2026-08-22 🟡** (`731c40e`) — the `n_points` 8/10/20 sweep on both images, one solve per rung: the sampler is **excluded** as the outlier's cause (0.11 gated rung worse at every count), and the 0.7.2 control finds the larger fact — the 10-point radial L2 swings **34%** of its own value under the sampler on the recording image and **the 15% band already fails on 0.7.2 at `n_points = 8` (15.8028%)**; the gate was passing on a sampler choice. 16:30 slot marked 3a ⛔ pending two rulings. **Rulings, 18:00 review 2026-08-22:** (1) leg 1 **re-record licensed** — version-tagged, bit-identical twice, no band moved (§9 item 4); (2) leg 2 **gate replaced, not re-banded** — `MAG-18` commissioned (§9 item 1), 3a resumes behind it; full text in the prose entry below. **Step 3a CLOSED 2026-08-23, attempt 8** — the 10:30 review's class ruling (1\*) executed: `STEP1_LUMPED_RATIO_RECORD` 0.829782 → **0.828893** and `STEP1_CROSS_ROUTE_RECORD` 0.077095 → **0.077431** written version-tagged, no band moved, and the anchor is **`19 passed` / exit 0 twice in the slot** (238.64 s / 238.73 s, complex, `-n 2`, both rank footers identical) against attempt 7's `1 failed / 18 passed`, with both records identical to six digits across the two runs, reciprocity 2.679e-05 inside 1e-3 and σ_max 0.861356895 < 1; the loop unmasked no further record, and the only other consumer of the two constants (`test_port_lumped_narrowed_sheet.py`'s `f = 1.0` control) is `12 passed` / exit 0 on the same digits. Leg 2 closed in attempt 7 ⇒ **only 3b remains** (§5.3 table, drift disposal, merge). **Step 3b CLOSED 2026-08-23, 15:00 slot ⇒ chunk ✅ — `main` boots `0.11.0.post0`.** (i) §5.3's environment table rewritten from a probe of the built image (`20260823T200740Z_OPS-18-step3b-env-probe.log`: dolfinx `0.11.0.post0`, Python 3.12.3, numpy 2.4.6, gmsh 4.15.2-git-657c8e9, h5py 3.16.0 / HDF5 2.1.1, petsc4py 3.25.1, mpi4py 4.1.2), with the compose `PYTHONPATH` named as the project's only version-encoded literal. (ii) The step-2 volume drift **disposed by re-record under (1\*)**: `UNIFORM_VOLUMES_RECORD` carries the v0.11.0 values version-tagged (tag 1 → 1.192257046e-04, tag 2 → 1.185069486e-04, tag 3 unmoved, tag 4 → 1.143589055e-02), the 1e-9 band untouched, the partition identity still exactly **1.000000000000** and the `GEO-17` sign + recovery gates green on their own digits; `TH-10`'s 128 MHz 55 251 → 55 241 re-record is now explicit in that entry. (iii) Three known-issues entries closed (numpy-2 `!r` by `445a3ea`; the two-torus re-records and the non-determinism entry by `5df1e39`, the latter quoting (b′)); the straight-wire entry is **superseded not resolved** and its scope updated — `MAG-18` de-gated the band, but the `E_Ω` ladder has **not** been re-measured on 0.11 and is owed. (iv) **Anchor met:** `tests/environment` + `test_mesh_tag_integrity.py` real / `-n 2` is **`7 passed, 4 skipped` / exit 0** where step 2's shim-runtime log read `1 failed, 6 passed, 4 skipped` — reproduced three times in-slot (one plain, two `-s`, every printed digit identical, rank footers identical), and the same red baseline was first reproduced this slot on the rebuilt image (`20260823T200356Z_OPS-18-step3b-confirm.log`, Status 1) before the re-record. Full-suite collect **`437 collected / 0 errors` in both modes** (`…200620Z…-collect-real.log`, `…200631Z…-collect-complex.log`, `PYTEST_RC=0`), reconciled per module against step 2's 418 by counting, not assuming: **418 + 5 (leg (d)) + 4 (leg (c)) + 2 (leg (d0)) + 5 (leg (d2)) + 3 (`MAG-18`) = 437**. (v) `attempt/OPS-18` merged to `main` with every log. **Scope caveat on ✅:** every §2.1 family was re-gated green on 0.11 across attempts 1–8 and item 1 (`TH-6` `20260822T123401Z`; `TH-10` `20260822T…-th10`; `MAT-4` `20260822T140418Z_OPS-18-step3-mat4.log`; `MAT-6` `20260822T140709Z_…-mat6-dR-port1-sparams.log`; `PORT-1` `20260823T170403Z` / `20260823T170821Z_OPS-18-step3a-leg1-run*.log`) — **except the real-mode `MAG` family, whose last 0.11 observation is attempt 3's `17 passed / 1 failed` on the since-retired 15% band**; the `MAG-18` `E_Ω` gates that replaced it are unobserved on 0.11 and are owed to a review. **Scope caveat DISCHARGED 2026-08-23, 19:30 slot** (§9 item 1, ruling (3\*)): the real-mode `MAG` family is now re-gated green on 0.11 — `MAG-18`'s three anchors met twice in-slot on `main` (`7 passed` / exit 0, `20260824T003059Z` / `20260824T003650Z_MAG-18-regate-run*.log`, plus the `-n 4` leg `20260824T003606Z`), rate 1.6854 ≥ 0.7, cross-width 4.86e-07 ≤ 1e-6, natural-BC ratio 0.3285, no record and no band moved. Every §2.1 family has now been re-gated on the image `main` boots. | heavy |
| `OPS-19` | Doc-reference checker: staleness must not own the exit code (2 runs flagged the masked signal 2026-08-16) | ✅ (2026-08-16: exit 0/1/2 split + `--stale-severity {fail,report}` default `report`; on `main` the checker now reads `dead=0 guide=0 stale=24 exit=2` where it read exit 1, guide pass green 21/21; 8 tests, 1.91 s, smoke) | smoke |
| `OPS-20` | Disposition the coil-phantom `ComplexComparisonError`: localize with `--tb=long`, then fix the form or mark `@real_only` (known-issues 2026-08-18; commissioned 2026-08-18 10:30 review) | ✅ *(2026-08-19, 06:00 slot — fixed, no `@real_only`; the commissioned `ComplexComparisonError` was already dead, killed by `OPS-22` through the **imported** drive callable, and a free grep found it. Only the predicted second layer remained: the complex build now **passes the same 30% gate at the same 17.1233%**, both ranks identical, real-mode digits unmoved across control and re-run; collect count unchanged at 49. *Audited COMPLIANT 2026-08-19 10:30 review — all five footers, the 17.1233% in all three counted runs and the line-142 `Im`-assertion verified; the skipped cold-cache clear is journalled in three places and adjudicated sound; cosmetic journal error on record: the exit-124 batch log does carry a footer (124 / 481 s), the uncounted disposition stands*)* | standard |
| `OPS-21` | Make the combined-XDMF test scalar-type-aware and rank-deterministic (known-issues 2026-08-18, two defects in one test; commissioned 2026-08-18 10:30 review) | ✅ | standard |
| `OPS-22` | Make the three magnetostatic loop-drive fixtures complex-safe: replace the `ufl.max_value` / `<=` predicates in their `current_density` callables (known-issues 2026-08-19; commissioned 2026-08-19 03:00 review from the `OPS-17` leg-(b2) attempt-2 diagnosis; unblocks 5 tests in leg (b2)) | ✅ *(2026-08-19, 04:30 slot — all three files fixed, no `@real_only` needed; real-mode digits unmoved to the last printed figure across three runs, and the complex build now runs all three files to a footer: **5 passed, 412.12 s, exit 0**, both ranks identical. *Audited COMPLIANT 2026-08-19 10:30 review — footers, closed-form assertions and the new `Im`-bound idiom verified against all five logs; one caveat on record: `test_helmholtz_v2.py`'s complex coverage rests on a silenced `ComplexWarning` `float()` cast, not an assertion — fold an `Im`-bound in whenever that file is next touched*)* | standard |
| `OPS-23` | Sweep the `OPS-21` rank-0-return defect pattern (4 measured sites in 3 test files) + the `test_helmholtz_v2.py` Im-bound (commissioned 2026-08-20 03:00 review from the 00:00 slot's grep survey) | ✅ | smoke-to-standard | 3 real sites (all in `test_csv_export_stats_parity.py`) + the Im-bound fixed; 2 of the commissioned sites were print-only false positives and 1 exempted site was a real defect; 12 passed both ranks, 5.00 s. *Audited COMPLIANT 2026-08-21 18:00 review — red-baseline byte-identity re-verified against the log's rank blocks; benign omission: the first exit-0 helmholtz-real log is in test-results.md but uncited in the annotation* |
| `OPS-24` | Migrate `core/cavity.py`'s two `assemble_matrix(..., diagonal=)` sites to the 0.11 signature — `TH-9`'s cavity gate + resonance guard have been **non-executing on `main` since the 0.11 merge** (known-issues 2026-08-24; found by `EX-30` leg (th); commissioned 2026-08-24 18:00 review; closed 2026-08-25 — `diagonal=` → `diag=`, all four green, 0.0436% worst-mode reproduced to the printed digit) | ✅ | standard |
| `OPS-25` | Re-join `th:7` to its gate: hoist the series-interior interpolation into the gate module and import it, migrating the repo's only `interpolate(cells=)` site (known-issues 2026-08-24; ruled hoist-not-repair by the 2026-08-24 18:00 review) | ✅ (2026-08-25: hoisted to `series_interior_function` in `test_lossy_sphere_fullwave.py`; `th:7` green in 14 s with both element-order records reproducing — degree 1 8.1541% / 8.3869%, degree 2 0.1405% / 0.0058%, drifts ≤ 1.48e-03 in a 1% band — and the gate's `P_series(meshed)` **bit-identical to all ten printed digits** across the refactor; `13 passed in 25.28s`) | standard |
| `OPS-26` | **Systematic dolfinx-0.11 migration completeness sweep** — re-run `OPS-17`'s "observed in a completed run" census on the 0.11 image and statically sweep `src/` for un-migrated call sites. Two silently-broken gates have already been found *by examples rather than by the upgrade's own re-gate* (`TH-9` cavity, `OPS-24`; straight-wire h-refinement, red on `main`, found 2026-08-25 by `mag:6`); a third is likelier than not. **Commissioned 2026-08-25 by operator directive, interactive session** — queue at the next review. *Queued 2026-08-25 10:30 review: step 1 is §9 item 3; step 2 held until step 1's site list lands.* | ⬜ | heavy (split across ≥ 2 slots) |

**`OPS-24` — migrate `core/cavity.py` to 0.11; turn `TH-9`'s gates back on** ✅
*(commissioned 2026-08-24 18:00 review from `EX-30` leg (th)'s finding 1;
closed 2026-08-25, 21:00 CDT slot.)*
> **Closed 2026-08-25.** The break was a pure keyword rename, established by
> introspecting the installed 0.11 `dolfinx.fem.petsc.assemble_matrix` rather
> than assumed: `diagonal=` → **`diag=`**, docstring "Rows/columns that are
> constrained by a Dirichlet boundary condition are zeroed, with the diagonal
> to set to `diag`" — semantics unchanged, so the constrained-DOF eigenvalues
> still land at `bc_diagonal`/1.0 and `solve_pec_cavity_modes`'s
> `spurious_cutoff = 0.5 · bc_diagonal` reasoning holds verbatim. Two lines
> changed in `core/cavity.py` (`:129`, `:131`) plus a migration comment; no
> test, band, tolerance or recorded eigenfrequency touched, and no solver
> path altered. **Red baseline reproduced in-slot first** — `4 failed, 9
> passed in 1.83s`, all 9 `tests/environment` green, Status 1
> (`20260825T020052Z_OPS-24-red-baseline.log`, 4 s) — matching the
> commissioning probe's `4 failed, 9 passed in 2.11s` exactly. **After the
> fix, `13 passed` twice**: 32.11 s / Status 0 / 33 s harness
> (`20260825T020111Z_OPS-24-green.log`) and 29.71 s / Status 0 / 31 s
> harness with `-s` for the printed diagnostics
> (`20260825T020157Z_OPS-24-green-quoted.log`), both `-n 2`, complex,
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first. **Every recorded
> figure reproduces the pre-0.11 record to the printed digit** — the
> closed-form eigenfrequency comparison on 720 cells / 5330 dofs prints
> 239.9805 / 291.3904 / 312.3465 / 346.5469 MHz against analytic
> 239.9510 / 291.3459 / 312.2838 / 346.3958 MHz, i.e. **0.0123 / 0.0153 /
> 0.0201 / 0.0436%**, worst-mode **0.0436%** equal to the `TH-9` record and
> to the test module's own header table; `null_modes_in_band = 0`;
> refinement h 0.1667 → 0.1143 takes max err 0.0436% → **0.0102%** at fitted
> rate **3.85** (gate > 2.0); the gradient-mode zero cluster is 8/8 below
> 2.529e-07 with max |λ| = **5.560e-14** against k₁² = 25.2909 (gate 1e-8
> relative); the energy-continuity guard fires **137.554** near-resonant and
> reads **21.951** clear against the 50.0 threshold. That digit-for-digit
> agreement is itself the evidence the rename was semantics-preserving.
> Retires the cavity known-issues entry and the §2.1 non-executing caveat;
> `th:2` / `th:5` are unblocked for `EX-30` leg (th) (§9 item 4), which owns
> re-running them — this chunk did not.
`cavity.py:129`/`:131` still pass `diagonal=` to
`dolfinx.fem.petsc.assemble_matrix`, dropped in 0.11 — `OPS-18` step 2's
migration missed the module because nothing scheduled runs
`test_cavity_resonances.py` / `test_resonance_guard.py`, so the 0.11 merge
landed with a dead subsystem inside a green-looking tree. Gate probe on
`main`: `4 failed, 9 passed in 2.11s`, all 9 `tests/environment` green
(`20260824T213908Z_EX-30-th-cavity-gate-probe.log`). Full rubric (anchors,
red-baseline negative control, traps, stop rules) in the §9 item. Done-when:
all four tests green at `-n 2` complex with the closed-form eigenfrequency
comparison quoted (record 0.0436% worst-mode), no band or recorded
eigenfrequency touched; retires the cavity known-issues entry and removes
the §2.1 non-executing caveat.

**`OPS-26` — systematic dolfinx-0.11 migration completeness sweep** ⬜
*(commissioned 2026-08-25, operator directive, interactive session: "queue
the systematic sweep to make sure the transition to 0.11 actually worked
properly". Queue at the next review — it was not in §9 when the directive
landed. **Queued by the 10:30 review the same morning: step 1 is §9
item 3; step 2 stays unqueued until step 1's site list lands, because the
list shapes the census.**)*
> **Why this exists, stated as evidence rather than worry.** `OPS-18` was
> audited COMPLIANT and its §4 close stands — but "every cited log is green"
> and "every gate executes" are different claims, and the upgrade's re-gate
> checked the first. Two defects have since surfaced, **both found by the
> examples layer, neither by the upgrade**:
> * `core/cavity.py` — `assemble_matrix(diagonal=)` → `diag=`. `TH-9`'s
>   closed-form cavity gate and the resonance guard were **non-executing on
>   `main` from the 0.11 merge until `OPS-24` (2026-08-25)**, invisible
>   because nothing scheduled runs those two modules.
> * `tests/validation/test_convergence.py::TestConvergence::test_h_refinement_straight_wire`
>   — **red on `main` right now**: fitted rate 1.9038 outside the `MAG-13`
>   band, the h = 0.0018 rung's error having collapsed 9.26% → 4.4605% on
>   0.11. Found 2026-08-25 by `mag:6`. `MAG-18` re-gated the `E_Ω` ladder and
>   not this test, which is how it survived. **Diagnosing it is not this
>   chunk's job** (that is a `MAG-13`/`MAG-18` call) — enumerating its class
>   is.
>
> The common shape: a module that no scheduled command runs can be red or
> dead indefinitely. `OPS-17` built exactly the instrument for this and
> closed at **216 of 216 runnable validation tests observed in completed
> runs** — but that census was taken on **0.7.2**, and the image has since
> changed underneath it. This chunk re-takes it.
>
> * **Step 1 — static sweep (smoke, no solves).** Sweep `src/` and `tests/`
>   for call sites whose signature changed between 0.7.2 and 0.11.
>   **Introspect the installed module in the container** (`inspect.signature`)
>   rather than testing against a hardcoded list — the known five
>   (`io.gmshio` → `io.gmsh` / `model_to_mesh`'s `MeshData`,
>   `LinearProblem(petsc_options_prefix=)`, `fem.FunctionSpace` →
>   `functionspace`, `interpolate(cells=)` → `cells0=`,
>   `assemble_matrix(diagonal=)` → `diag=`,
>   `create_cell_partitioner(max_facet_to_cell_links=)`) are the ones already
>   *found*, so a list-based check can only rediscover them. **Anchor (§4):**
>   a machine-checkable count of call sites per API, reconciled against the
>   sites the five landed migrations touched, with **zero un-migrated sites
>   surviving** — or each survivor named with its module and line.
>   **Negative control:** the checker must flag a deliberately reverted call
>   site in a temp copy; a sweep that cannot fail is not a sweep.
> * **Step 2 — execution census on 0.11 (heavy, likely 2+ slots).** Re-run
>   `OPS-17` leg (b2)'s methodology on the current image: every collected test
>   **observed in a completed run with a footer**, real and complex, at each
>   file's recorded rank width. **Anchor (§4):** an observed/collected count
>   with the complement enumerated *by name*, each carrying one of exactly
>   three dispositions — **green**, **red with a filed known-issues entry**,
>   or **deferred with a stated reason**. The 216/232 denominator is the prior
>   and **must be re-derived, not inherited** (`GEO-18`/`GEO-19`/`GEO-20`,
>   `PORT-9` and `EX-31` have all added tests since).
>   **Cost discipline, from `OPS-17`'s own lessons:** grep each file's
>   existing logs for its *recorded* rank width and elapsed time before
>   sizing; a family's first complex command pays ~2.4–3× cold-JIT; read
>   *all* of a file's logs, not the first match. Budget one file per ~400 s
>   window where its record says so.
> * **Traps.** (i) `--collect-only` proves nothing about runtime — both
>   found defects collect clean. (ii) A red found here is **filed, never
>   fixed in-slot** and never re-recorded: a failing analytic comparison is
>   evidence about the test as much as the code. (iii) Do not loosen a band
>   to make the census green — the census's value is that it counts reds.
> * **Negative result (a real one, not a fallback).** If the census comes
>   back with the straight-wire test as the only red and no new dead module,
>   that is the chunk's deliverable and it closes ✅ — "we looked
>   systematically and there are two" is the result the directive asked for.
>
**`OPS-25` — re-join `th:7` to its gate (hoist the series-interior
interpolation)** ✅ *(2026-08-25, 22:30 implementer slot)* *(commissioned 2026-08-24 18:00 review from `EX-30`
leg (th)'s finding 3.)* `th:7` line 198 is the repo's **only**
`interpolate(cells=)` site — the example re-derived a step its banner claims
to import, and the private copy rotted while the gate
(`test_lossy_sphere_fullwave.py:457`) was migrated to `cells0=`. Ruling:
hoist and import, never repair in place — repairing preserves the
divergence the `ANS-1` rule exists to prevent. Full rubric in the §9 item.
Done-when: `th:7` green via `./run_examples.sh` with both element-order
records unchanged, the gate module green after the refactor, no `src/`
change; retires the `th:7` known-issues entry.
> **Closed 2026-08-25.** The hoist is `series_interior_function(series, msh,
> cell_tags)` at `test_lossy_sphere_fullwave.py:367` — CG2 vector space,
> `Function`, sphere-cell index array and the migrated `cells0=`
> interpolation, in one place. `_power_rung` and
> `07_element_order_lossy_sphere.py:_row_and_fields` both call it; the
> example's private copy is **deleted**, and `SPHERE_TAG` /
> `_series_interior_interpolant` dropped out of the example's import list
> with it, so the example can no longer re-derive this step at all. No
> `src/` change; no record, band or assertion moved.
> **The quantitative anchor is a bit-identical reproduction.** The moved
> code's only output is the gate's meshed-series ohmic power, and it
> reproduces `OPS-18` step 3's green log
> (`20260822T123746Z_OPS-18-step3-th10-rerun.log`) to every printed digit:
> `P_series(meshed)` = **1.048951142e-07 W** (coarse, 5 866 cells) and
> **1.066439173e-07 W** (fine, 17 667 cells), power errors 8.387% / 3.629%,
> quadrature-16 recheck 1.24e-16 — and the `TH-10` field figures beside them
> are unmoved (3.643% at 64 MHz, 1.769% / 59.16× at 128 MHz).
> `13 passed in 25.28s` (Status 0, 27 s harness, `-n 2`, complex,
> `tests/environment` first, both `test_lossy_sphere_fullwave.py` and
> `test_lossy_sphere_degree2.py`),
> `20260825T033221Z_OPS-25-gate-green.log`.
> **`th:7` end to end:** Status 0, **14 s**,
> `20260825T033152Z_OPS-25-th7-green.log`, asserting its own records inside
> the 1% band — degree 1 relL2 8.1541% (drift 4.00e-06) / power 8.3869%
> (1.18e-05), degree 2 relL2 0.1405% (5.50e-05) / power 0.0058% (1.48e-03),
> `|Im P|/Re P` = 0.000e+00 at both orders. Red reproduced in-slot first
> (`20260825T033114Z_OPS-25-red-baseline.log`, Status 1, `TypeError` at line
> 198), so the fix is bracketed by a measured red and a measured green.
> **Census delta (item 4 owns the arithmetic):** docrefs reads
> `dead=0 guide=0 stale=51 stale_severity=report exit=2`
> (`20260825T033312Z_OPS-25-docrefs.log`) — passes the `OPS-19` `exit != 1`
> gate. `th:7`'s two artifacts
> (`element_order_sphere_degree{1,2}_combined.xdmf`) left the stale set as
> this run refreshed them; **four `time_harmonic` entries remain** — `th:2`'s
> `pec_cavity_mode`, `th:5`'s `resonance_guard`, and `th:6`'s two
> `larmor_sphere_{64,128}MHz`. The total moved 55 → 51 against the `EX-31`
> log, not −2, because staleness is wall-clock: five other artifacts were
> refreshed by intervening slots and three `birdcage_leg_gaps_*` ones aged
> past the 48 h limit. Do not read a memorized total.

**`OPS-18` — DolfinX version upgrade, recurring** ⬜
*(commissioned 2026-08-16, operator session. The base image is pinned at
`dolfinx/dolfinx:v0.7.2` (late 2023) while upstream is at v0.11.0; the
operator wants regular upgrades with deliberate lag. This chunk is
**re-executable**: each pass marks the table row ✅ with the adopted
version and date, then the next qualifying release reopens it ⬜ with a
dated annotation. The ID stays stable.)*
> **Lag policy.** Adopt a release only when it is ≥ 8 weeks old **or** has
> received a patch release (x.y.z, z ≥ 1). When several qualify, jump
> directly to the newest — never step through intermediates (each step
> costs a full re-gate). **Trigger:** scheduled sessions have no network,
> so upstream release checks happen in interactive operator sessions; when
> one finds a qualifying release, it reopens this chunk and the daily
> review queues it.
> **Release check 2026-08-18 (interactive session, operator present):
> TRIGGER FIRES.** Upstream newest is **v0.11.0** with patch
> `v0.11.0.post0` — qualifying on both prongs of the lag policy (≥ 8
> weeks old *and* patched). Target: `0.7.2 → v0.11.0.post0`. The daily
> review should queue steps 1–3. Note for step 2, learned since
> commissioning: `discrete_gradient` currently lives at
> `dolfinx.cpp.fem.petsc.discrete_gradient` in 0.7.2 — expect it (and
> the AMS-relevant plumbing) to have moved namespaces across 0.7 → 0.11;
> any iterative-solver work (`TH-13`-class) should land *after* this
> upgrade or be written against the new API.
> **Migration pack cached 2026-08-18** (interactive session, tracked
> in-repo): **`docs/references/dolfinx-0.11-migration/`** — distilled
> old→new API map with a repo-specific hit list, per-version
> release-note summaries (0.10 is a documented gap — introspect the
> container), and verbatim 0.11 idioms from the upstream demos. Step 2
> starts there; two known hard breaks it documents: `gmshio` moved to
> `dolfinx.io.gmsh` with `model_to_mesh` returning a `MeshData` object
> (breaks `io/mesh.py` tuple unpacking), and `LinearProblem` takes
> `petsc_options_prefix`. The installed container API is ground truth
> over the pack. *(This resolves the 03:30Z run's "observed mid-slot"
> flag: the pack is tracked, not ignored.)*
> **Operator note 2026-08-18 (interactive session): the fired trigger
> above has not been acted on.** The 03:00, 10:30 and 18:00 daily
> reviews each restocked §9 without queueing steps 1–3 and without a
> deferral note, contrary to this entry's trigger clause. The next
> daily review must queue steps 1–3 or record a dated deferral
> rationale here; see the matching note in the §9 preamble.
> **Deferral recorded 2026-08-19, 03:00 review.** The trigger is
> acknowledged and the upgrade is **deliberately deferred until
> `OPS-17` step 3 closes** (leg (b2) is the only open part). Rationale:
> step 3's done-when is that every gated number reproduces and every
> failure is attributable, but the complex-suite baseline is mid-audit
> at 39/225 validation tests observed, with a just-diagnosed
> fixture-debt defect (`OPS-22`, commissioned this review) whose
> symptom — `ComplexComparisonError` / swallowed FFCx root-node
> failures during form compilation — is exactly what an 0.7→0.11 UFL/
> FFCx migration break would look like. Upgrading now would make
> post-upgrade complex failures unattributable between migration and
> pre-existing debt, and the entry's own trap rule ("a gated number
> that moves is a finding") is unenforceable without a reconciled
> baseline. The sequencing note above already licenses clearing the
> short in-flight tails first; those tails (`OPS-22`, leg (b2)'s
> resumption, `POST-5` step 3, `TH-12` step 3) are all queued in §9
> now and sum to ~4–6 slots. **Commitment:** the review that records
> `OPS-17` step 3 closed queues `OPS-18` steps 1–3 at the top of §9 in
> the same commit; a review that finds this condition met and does not
> queue it repeats the protocol defect this note exists to end.
> **Condition met — commitment executed 2026-08-21, 18:00 review.**
> `OPS-17` step 3 closed this review (leg (b2) at the adopted 216
> denominator); steps 1–3 are queued as §9 items 1–3 in the same commit,
> with a sanctioned persistent `attempt/OPS-18` worksite so `main` keeps
> booting 0.7.2 until step 3 is green (per this entry's negative-result
> clause; the §9 items carry the worksite and container-restore rules).
> **Step 1 CLOSED 2026-08-22, 04:30 implementer slot** (commit `c767171` on `attempt/OPS-18`; `main` keeps 0.7.2 per the worksite rule). Adopted **`0.11.0.post0`** (`dolfinx.__version__`) from image tag **`v0.11.0`** — `dolfinx/dolfinx:v0.11.0.post0` does not exist on Docker Hub; Python **3.10 → 3.12**, the compose `PYTHONPATH` literal being the only version-encoded path in the project (the mode wrappers and `src/sitecustomize.py` derive the tag; from-source h5py unchanged, HDF5 3.16.0). Standard tier, `-n 2`, both rank footers identical: real `3 passed, 1 skipped` / 2 s, `ScalarType=float64` (`20260822T093934Z_OPS-18-step1-real.log`); complex `4 passed` / 2 s, `complex128` (`20260822T093943Z_OPS-18-step1-complex.log`); **negative control** real + `FEM_EM_REQUIRE_COMPLEX=1` → `1 failed, 3 passed`, exit 1 (`20260822T093954Z_OPS-18-step1-negctl.log`). New gate `tests/environment/test_dolfinx_version.py` derives the expected tag from `sys.version_info`. Step 2's red baseline banked in the same slot: `124 collected / 75 errors` per rank, identical in both modes (`20260822T094005Z_OPS-18-step2-census-real.log`, `20260822T094029Z_OPS-18-step2-census-complex.log`) — 71 of 75 `ImportError: cannot import name 'gmshio' from 'dolfinx.io'`, 4 cascades. Note: `docker image tag` is not allowlisted; rollback via cached rebuild from `main`'s Dockerfile works (0.7.2 / python 3.10.12 / `memory.max` 64.00 GiB restored).
> **Step 2 CLOSED 2026-08-22, 06:00 implementer slot** (on `attempt/OPS-18`; `main` keeps 0.7.2). **Anchor met — the full suite collects with ZERO errors in both modes**, `418 collected` per rank, `PYTEST_RC=0`: real `20260822T110429Z_OPS-18-step2-census-real2.log` (2.10 / 2.09 s), complex `20260822T110440Z_OPS-18-step2-census-complex.log` (2.36 / 2.35 s, `FEM_EM_REQUIRE_COMPLEX=1`); 418 reconciled exactly against leg-(b2)'s 412 + 4 (`test_dolfinx_version.py`) + 2 (`GEO-18` step 2, `bd12613`), per-directory in `20260822T110534Z_OPS-18-step2-census-tree.log` (validation unmoved at 232). **The whole migration was one import:** `src/fem_em_solver/io/mesh.py`, `dolfinx.io.gmshio` → `dolfinx.io.gmsh`, with `model_to_mesh`'s six-field `MeshData` wrapped by one module-level `_model_to_mesh` shim restoring `(mesh, cell_tags, facet_tags)` for all 11 call sites; the pack's predicted `FunctionSpace`/`LinearProblem`/`discrete_gradient` breaks did not fire at collect or in the runtime probe. Shim runtime probe (`tests/environment` + `tests/mesh/test_mesh_tag_integrity.py`, real, `-n 2`): `1 failed, 6 passed, 4 skipped` / 15.85 s (`20260822T110624Z_OPS-18-step2-shim-runtime.log`) — meshes build, tags intact, both policy identity tests pass.
> **Carried into step 3:** (i) the one failure is the predicted new-gmsh drift — meshed volume tag 1 `coil_1` 1.191750413e-04 → 1.192257046e-04 m³, **4.251e-04 relative** against its `OPS-17` record — filed to known-issues; **no assertion, band or record was touched**; re-record vs finding is step 3's call under §5.3's trap clause, by comparison not argument. (ii) **Harness rule:** a command whose payload ends in a pipe reports the pipe's exit code (`20260822T110402Z_OPS-18-step2-census-real.log` ended in `| tail -40`) — drop the pipe or `set -o pipefail` + echo `PYTEST_RC=` per rank.
> Full narrative (steps 1–2): `docs/planning/plan-archive.md`, entry «§7 OPS-18 steps 1–2 closure narrative — archived 2026-08-23 (weekly review)».
> **Step 3 attempt 1 — 🟡 PROGRESS 2026-08-22, 07:30 implementer slot** (on
> `attempt/OPS-18`; `main` keeps 0.7.2). Three of five gate families re-gated
> green on `0.11.0.post0`; `MAT-6` and `PORT-1`, the real-mode leg and §5.3's
> table remain. `mpiexec -n 2`, complex build, `FEM_EM_REQUIRE_COMPLEX=1`,
> `tests/environment` first, both rank footers identical on every run.
> * **The pack's second wave fired here, not at collect — a solve is what
>   reaches it.** Step 2's reading held exactly: `LinearProblem`'s
>   `petsc_options_prefix` (**7 call sites**; each given its *own* prefix, since
>   0.11 inserts `petsc_options` into the global PETSc database under it and a
>   shared literal would let two solvers overwrite each other's
>   `pc_factor_mat_solver_type`), `FunctionSpace` → `functionspace` (1 site),
>   and one the pack does not document: `Function.interpolate(cells=)` →
>   **`cells0=`** (0.11 signature `(u0, cells0=None, cells1=None)`,
>   introspected in the container; 2 sites). All three surfaced in the **first
>   7 s of the first command** — `20260822T123401Z_OPS-18-step3-th6.log`,
>   `3 failed, 7 passed`, the red baseline for the fixes.
>   `discrete_gradient`'s namespace move still has not fired.
> * **`TH-6` reproduces** (`20260822T123518Z_…-th6-rerun.log`, `10 passed` /
>   21.27 s / exit 0): fine rung 24³ / 82 944 cells, rel L2 **3.609441e-02**
>   (record 3.61%), α **0.017%**, β **0.060%**, L2 rate in h **0.9998**;
>   `MAT-2` σ-ratio 10.3243 vs 10.3116 (0.124%).
> * **`TH-10` reproduces, with one re-record** (`20260822T123746Z_…-th10-
>   rerun.log`, `11 passed` / 21.36 s / exit 0). **64 MHz is bit-identical** to
>   the record — 5 866 / 17 667 cells, relL2 8.154% → **3.643%**, ohmic power
>   **3.629%**. **128 MHz's fine rung moved 1.826% → 1.769% *with its mesh*:
>   55 251 → 55 241 cells.** Disposed as a **re-record by measurement**, under
>   this entry's own trap clause: the moved cell count is step 2's filed
>   new-gmsh drift, the identities are intact, the shift is *toward* the series
>   with separation rising 57.31× → 59.16×, and the band is unmoved and
>   untouched. The 64 MHz rungs being bit-identical is what makes this a mesh
>   result rather than a physics one.
> * **`MAT-4` reproduces** — fine rung 74 020 cells, mean SAR **3.422%** at
>   64 MHz / **3.536%** at 128 MHz, `Im/Re E_z` 0.1752 vs 0.1755 and 1.9900 vs
>   2.0011. Recorded honestly as the weaker of the three: both tests PASSED but
>   inside `20260822T123618Z_…-th10-mat4.log`, whose `Status: 1` is the co-run
>   `TH-10` file's pre-fix `interpolate` break. **This family owes a clean
>   green log of its own.**
> * **Cost:** four commands, **108 s total** (7 + 23 + 55 + 23). The cold-JIT
>   × 3 windows (560/540/480 s) were never approached and nothing hit exit 124.
>   **Rule banked: a re-gate leg's first command into an unvisited family is a
>   break-finder, not a measurement** — run its cheapest member first to flush
>   API breaks, then size the real window, or discover
>   `petsc_options_prefix` 400 s into a `dodd_deeds` one.
> **Step 3 attempt 2 — 🟡 PROGRESS 2026-08-22, 09:00 implementer slot** (on
> `attempt/OPS-18`, `3cbd5b5`; `main` keeps 0.7.2). Six harness commands,
> **224 s of compute** plus ~4 min of container round-trip; nothing hit
> exit 124. Full journal: `docs/testing/attempts.md`, 2026-08-22T14:15Z.
> * **`MAT-4` discharges attempt 1's self-declared debt** —
>   `20260822T140418Z_…-mat4.log`, **`9 passed` / 35.83 s / exit 0**, a clean
>   green log of its own rather than a PASS cited inside a red co-run.
> * **`MAT-6` re-gates on two files** — `20260822T140518Z_…-mat6-port1-
>   flush.log`, **`24 passed` / 88.60 s / exit 0** (`dodd_deeds_impedance`
>   against its `OPS-17` record of 87.43 s, **+1.3%**, plus `port_lumped_bc`),
>   and `20260822T140709Z_…-mat6-dR-port1-sparams.log`'s **12 passed** =
>   4 environment + `dodd_deeds_projected_drive`'s 8, the file carrying the
>   §2.1 production projected drive at 1.5834%. That log's `Status: 134`
>   belongs to the `PORT-1` files below and is named, not hidden.
> * **A fourth undocumented break, fixed:** 0.11 makes
>   `max_facet_to_cell_links` a **required** argument of
>   `mesh.create_cell_partitioner` (0.7.2 took the ghost mode alone), and
>   `singledispatch` reports it as `TypeError: _() missing 1 required
>   positional argument`, naming neither the function nor the meaning. One
>   call site (`io/mesh.py`, `two_torus_domain`); the value is **2** —
>   dolfinx's own default in `create_mesh` and its documented value for a
>   non-branching manifold mesh, which every fixture here is. `None`
>   ("no upper bound") would have been the wrong safe-looking choice.
> * **`PORT-1` is blocked, and the cause is measured rather than argued.**
>   Both two-torus files abort the *process* in `mesh.generate` —
>   `20260822T140912Z_…-port1-rerun.log`, **`Status: 134`** (SIGABRT) at 12 s,
>   `Error [mathex::parseatom()]: invalid token on expression`. Two probes
>   split grammar from literals: gmsh in the image is **4.15.2-git-657c8e9**
>   and parses the *exact* gap-arc expression when its numbers are plain
>   Python floats (`20260822T141005Z_…-gmsh-mathex-probe.log`, 4 s), while the
>   image's **numpy 2.4.6** renders a numpy scalar's `repr` as
>   `np.float64(0.00591…)` (`20260822T141027Z_…-numpy-repr-probe.log`, 2 s).
>   `two_torus_domain` interpolates `arc_half_y` — a numpy scalar — into the
>   `MathEval` size field with `!r`, so the field string literally contains
>   `np.float64(`. **Image debt of ours that numpy 1.x masked**, not an
>   upstream regression and not a gated number moving; no band, assertion or
>   record touched. Fix is a `float()` coercion, deferred by the minute-45
>   rule.
> * **Rule banked: an f-string feeding a *parser* must coerce, not `repr`.**
>   `!r` renders Python syntax and is only accidentally valid in another
>   grammar; numpy 2 changed the accident. Grep `!r` inside any string handed
>   to gmsh, PETSc options or a shell before the next upgrade — a class, not
>   an instance.
> * **Sandbox trap, newly named:** `git checkout` **cannot** swap
>   `docker/Dockerfile` or `docker/docker-compose.yml` here — the permission
>   sandbox grants write access by bind-mounting them, and a bind-mounted file
>   cannot be unlinked (`Device or resource busy`). A branch switch *reports*
>   `M docker/Dockerfile` and silently leaves the old content. Move those two
>   files with the Edit tool and verify with `git status --porcelain`.
>   Container round-trip measured at **109 s build + 14 s recreate** each way,
>   base layers cached — ~4 min of fixed overhead per OPS-18 slot.
> * **Still owed for step 3 to close:** `PORT-1` (after the coercion), the
>   **real-mode leg**, §5.3's environment table, and disposal of step 2's
>   filed volume-drift known-issues entry.
> *Reviewed 2026-08-22, 10:30 — steps 1–2 audited from their footers
> (real `3 passed, 1 skipped` / control `1 failed, 3 passed` / `418
> collected` in both modes, all `-n 2`, both ranks identical) and hold as
> step-level closes; the chunk stays 🟡. Attempt 2's four-of-five reading
> accepted; the 128 MHz re-record is licensed by this entry's trap clause
> and is made explicit in 3b. The numpy-2 `!r` defect gets a known-issues
> entry this review (attempt 2 journaled it only in attempts.md). Step 3
> is rescoped into §9 items **3a** (PORT-1 coercion + sweep, real-mode
> leg) and **3b** (§5.3 table, drift disposal, confirming run, merge).*
> **Step 3 attempt 3 — 🟡 PROGRESS 2026-08-22, 12:00 implementer slot** (on
> `attempt/OPS-18`, `445a3ea`; `main` restored to a booted 0.7.2, verified
> `dolfinx.__version__ == 0.7.2`). Three harness commands, **777 s of
> compute**, no exit 124. Both of 3a's prescribed fixes landed and both were
> measured against a red baseline; **neither leg is green**, and both misses
> are records that moved, not code that broke. Full journal:
> `docs/testing/attempts.md`, 2026-08-22T17:30Z.
> * **`PORT-1` meshes again — the coercion is the fix, and it is separated
>   from luck by its own negative control.** `float()` on `arc_half_y`,
>   `major_radius` and `z_c` before the `MathEval` f-strings turns attempt
>   2's `Status: 134` (SIGABRT at 12 s) into
>   `20260822T170346Z_…-port1-coerced.log`, **`17 passed / 2 failed` in
>   260.93 s**, both rank footers identical. The prescribed sweep is
>   **measured, and it refutes its own prediction**: 53 `!r` interpolations
>   in `src/`, of which the 4 two-torus `MathEval` sites (the required
>   negative control) are the only parser-facing ones — the other 49 are
>   Python exception messages — and `MathEval` has exactly **one** call site
>   in all of `src/`. The birdcage fixtures do **not** carry the class.
> * **A fifth undocumented 0.11 break, found by the real-mode leg and
>   fixed:** `element.interpolation_points` is now a **property** returning
>   the `(n, gdim)` array, so calling it raises
>   `TypeError: 'numpy.ndarray' object is not callable`. Probed in the image;
>   2 sites in `src/` (`solvers.py` `compute_b_field` / `compute_h_field`),
>   4 in `examples/`. Red `20260822T170854Z_…-real-mag.log`
>   (`5 failed / 13 passed`) → green-but-one
>   `20260822T171401Z_…-real-mag2.log` (**`17 passed, 4 skipped / 1 failed`**
>   in 272.43 s). The four `examples/` sites take the identical one-token
>   change and are **not** covered by a log this slot.
> * **Two stops, both journaled, no band touched.** (i) `PORT-1`'s two
>   remaining failures are *reproduction* records, not physics gates:
>   `passivity_max_sigma` 0.861356895 vs 0.861449 (band 1e-6) and the
>   two-torus gap ratio 0.894141 vs 0.894310 (band 1e-4), with
>   `‖S−Sᵀ‖/‖S‖` printed at **3.112128e-05** against its 2.5494e-05 record.
>   **The physics holds in the same run** — reciprocity is 32× inside the
>   `PORT-1` 1e-3 band, passivity holds (σ_max 0.8614 < 1), and the
>   open-limit and cross-route identities PASS. So 3a's anchor is **met on
>   the band it names and missed on the digit string**, which is why this is
>   a stop and not a close. (ii) The real-mode leg's one failure is
>   `test_straight_wire_b_field` at **15.3848%** against a 15% band on a
>   mesh that grew **145 900 → 147 235 cells** — and that band is recorded
>   *in the test* as the measured error of the 145.9k mesh (12.75%), i.e.
>   1.18× a measurement on a still-converging O(h^1.2) ladder. Every other
>   `MAG` gate passes: convergence, the analytic-BC comparison that *is* the
>   `MAG-13` claim, both circular-loop gates, all 7 mutual-inductance tests.
> * **The common hypothesis, and its own counter-evidence.** New gmsh
>   (4.15.2-git-657c8e9) moves the meshes, and moved meshes move
>   solution-dependent records at 1e-4 — the same mechanism as step 2's
>   volume drift and `TH-10`'s 55 251 → 55 241. But a 1.9% cell-count change
>   producing a 21% error change is **steeper than the straight-wire
>   ladder's own rate**, so the mesh alone does not explain leg 2, and
>   nothing measured excludes an assembly/interpolation change. Two
>   known-issues entries filed with the cheap experiments that would decide
>   it (print the two-torus cell count on both images; re-run the recorded
>   `h` ladder's other two rungs on 0.11).
> * **Still owed for step 3 to close:** disposal of the two record moves
>   above (a review decision, not an implementer's), §5.3's environment
>   table, and step 2's volume-drift entry.
>
> **Step 3 attempt 4 — 🟡 PROGRESS 2026-08-22, 13:30 implementer slot**
> (branch `231d6c7`; no `src/` change — both cheap experiments attempt 3
> named were run, and nothing else):
>
> * **Experiment 1, leg 1: the two-torus mesh *moved*.**
>   `tests/mesh/probe_two_torus_cell_count.py` (fixture arguments imported
>   from `test_port_lumped_two_torus._build`, counts reduced across ranks,
>   `-n 2`, mesh only) prints **184 919 cells / 31 676 vertices** on 0.7.2 +
>   gmsh 4.11.1 and **184 176 / 31 550** on 0.11.0.post0 + gmsh 4.15.2 —
>   **−4.017e-03** relative, every tag group moving ≤ 1%. Against records
>   that missed by 9.2e-05 and 1.7e-04, that is a 24-40× attenuation:
>   **consistent** with the mesh reading the review already granted
>   `TH-10`, though the 0.7.2 leg had to run on `main`'s source (the
>   branch's `io/mesh.py` needs `dolfinx.io.gmsh`), so image and migration
>   are not separated. Logs `20260822T183313Z_…-twotorus-cells-072.log`
>   and `20260822T183626Z_…-twotorus-cells-011.log`, both Status 0.
> * **Experiment 2, leg 2: the mesh explanation is *refuted*, and 0.11 is
>   the better solver.** `tests/validation/probe_straight_wire_ladder.py`
>   (same solve, sampling and metric as the gated test, imported) re-ran the
>   ladder's other two rungs on **both** images, `-n 2`, real:
>   h = 0.004 gives 22.1925% → **21.8417%** on 38 750 → 38 740 cells, and
>   h = 0.0018 gives 9.2568% → **4.4605%** on 383 248 → 383 146 cells. The
>   0.7.2 column reproduces July's record to **+0.011% / −0.035%** — a
>   clean control, so the record is not stale. Both probed rungs mesh to
>   within **0.13%** of their recorded counts while their errors move −1.6%
>   and **−51.8%**: no mesh change can do that. The fitted rate over the
>   same endpoints goes **1.10 → 1.99**, and the *gated* rung h = 0.0025
>   is a **1.8× outlier on its own 0.11 ladder** (fit predicts 8.6%, it
>   measures 15.3848%) and the only rung whose count moved appreciably
>   (+0.92%). Logs `20260822T184158Z_…-wire-ladder-072.log` and
>   `20260822T183710Z_…-wire-ladder-011.log`, both Status 0.
> * **Experiment 3, run in the same slot: the outlier is *stable*.** The
>   gated rung on 0.11 at **`-n 4`** is bit-identical to `-n 2` — 147 235
>   cells, 15.3848% (`20260822T184951Z_…-wire-h0025-n4.log`) — so
>   partitioning and mesh instability are excluded; `-n 1` is a sizing
>   finding only (exit 124 at 400 s, not retried). The gated rung's own
>   0.7.2 control was also taken: **145 884 cells, 12.7485%**
>   (`20260822T185944Z_…-wire-h0025-072.log`), the July record to 0.012%,
>   so all three rungs of the 0.7.2 ladder reproduce to ≤ 0.04%.
> * **Consequence.** The two failures do **not** share a cause, so they need
>   separate dispositions. Leg 2's is probably *not* "loosen 15%": on 0.11
>   the h = 0.0018 rung already reaches 4.46%, inside the < 5% target
>   `MAG-13`'s own comment calls unreachable below ~1.1M cells. The open
>   question is what the h = 0.0025 rung is measuring — next cheap probe is
>   `n_points` 8/20 on 0.11 against the fit's 8.6% prediction (sampler
>   sensitivity vs a real non-monotonicity). No band, assertion or record
>   touched.
> * **Sandbox trap, confirmed a second time and now routine:** `git checkout`
>   silently leaves the old `docker/Dockerfile` / `docker-compose.yml`
>   content on a branch switch (`Device or resource busy`); the Edit-tool
>   swap + `git status --porcelain` check worked in both directions.
>   Round-trip measured at ~100 s build + 15 s recreate each way.
> * **Step 3 attempt 5, 2026-08-22 15:00 slot (`731c40e`) — the `n_points`
>   probe, and it answers more than it was asked.** One solve per rung,
>   the same field sampled at `n_points` 8 / 10 / 20, on **both** images
>   (`20260822T200503Z_…-wire-ladder-npoints-011.log`,
>   `20260822T201014Z_…-wire-ladder-npoints-072.log`, Status 0). At fixed
>   `n_points` the 0.11 gated rung is worse at every count (8: 15.80 →
>   16.60; 10: 12.75 → 15.38; 20: 11.50 → 13.70) and none approaches the
>   0.11 fit's 8.6% — the sampler is **excluded** as the outlier's cause;
>   what remains is a real non-monotonicity of this discretization near
>   h = 0.0025 on 0.11. But the 0.7.2 column is the finding: the 10-point
>   radial L2 spans **34%** of its own value on the gated rung
>   (11.4984–15.8028%) and 43% on the fine rung, and **the 15% band
>   already fails on 0.7.2 at `n_points = 8`** — the gate has been passing
>   on a sampler choice, not a margin, since July. Nothing touched.
> * **Rulings — 18:00 review, 2026-08-22.** The 16:30 slot marked 3a ⛔
>   because both dispositions touch a record or a band an implementer may
>   not touch. Both are now ruled:
>   1. **Leg 1 — the re-record is licensed, narrowly.** The three moved
>      numbers (`passivity_max_sigma` 0.861449 → 0.861356895 at band 1e-6;
>      gap ratio 0.894310 → 0.894141 at 1e-4; reciprocity 2.5494e-05 →
>      3.112128e-05 at 5e-7) are **reproduction records of a solved field
>      on a named mesh**, not physics bounds; every physics gate in the same
>      run holds (reciprocity 32× inside 1e-3, σ_max 0.8614 < 1, open-limit
>      and cross-route PASS); and the fixture's mesh moved 4.017e-03 with
>      the image's gmsh — the same three facts on which this review series
>      granted `TH-10`'s 55 251 → 55 241 re-record (attempt 1). **Conditions:**
>      (a) version-tagged — the 0.7.2 value *and* its 184 919 cells stay in
>      the test as a comment beside the new value with 184 176 cells and
>      `0.11.0.post0 / gmsh 4.15.2`; (b) the new digit string is written
>      only after two runs in the same slot reproduce it **bit-identically**
>      (attempt 4's stability criterion); (c) no band moves — 1e-6 / 1e-4 /
>      5e-7 stay; (d) branch-only until 3b merges. The attribution caveat
>      attempt 4 recorded (the 0.7.2 count was taken on `main`'s source)
>      is noted and does not change the ruling: the counts are what they
>      are on the image each test will run on. Queued as §9 item 4.
>   2. **Leg 2 — the gate is replaced, not re-banded, and not "fixed" on
>      0.11.** "Loosen 15%" is refused (the standing rule, and attempt 4
>      showed 0.11 is the *more* accurate solver here — a loosened band
>      would record the wrong fact). "Find the 0.11 non-monotonicity" is
>      refused *as an `OPS-18` clause*: attempt 5 showed the statistic it
>      would be chasing swings 34% under its own sampler on the image that
>      recorded it, so it cannot adjudicate a version bump either way. A
>      10-sample radial L2 is not a gateable statistic; the 15% band was
>      1.18× a number whose sampler spread is larger than that headroom.
>      **Disposal: `MAG-18`** (commissioned this review, §9 item 1) — a
>      sampler-independent annulus-restricted domain L2 of `|B_h| −
>      |B_ana|`, assembled not sampled, gated on a pre-registered
>      convergence rate plus rank-independence and the natural-BC control,
>      measured on 0.7.2 / `main` first so the record has a clean origin;
>      the 10-point number becomes reported-not-gated with the finding
>      cited. `OPS-18` 3a then re-measures leg 2 in the new norm on 0.11
>      (§9 item 4), where ruling (1)'s re-record terms apply to the
>      `E_Ω` record if it moves with the 147 235-cell mesh while the rate
>      and controls hold. The 15.3848% non-monotonicity known-issues entry
>      **stays open** — it is observed and unexplained, and `MAG-18` is
>      not claimed to resolve it.
>   3. **3b's drift disposal inherits ruling (1)**: the `OPS-17` volume
>      record (4.251e-04) and `TH-10`'s 128 MHz cell count are re-recorded
>      version-tagged, the same way.
> * **Step 3a attempt 6 — 🟡 2026-08-23, 00:00 implementer slot** (branch
>   `9b3c9e2`, `main` merged in at `95fbb1b` so `MAG-18`'s gate is present;
>   `main` restored to a booted 0.7.2, verified). Four commands, ~1 030 s,
>   no exit 124, nothing written. **Leg 2 is green on its anchors:** `E_Ω`
>   reads **25.2868 / 10.6172 / 6.6458%** on the recorded ladder (38 740 /
>   147 235 / 383 146 cells), monotone, rate **1.6854 ≥ 0.7** against
>   0.7.2's 1.6842 — a rate that moves 7e-04 across the bump that moved the
>   retired 10-point number 21% — and the natural-BC control is strictly
>   worse at 32.315493% vs 10.617170%, ratio 0.3285. The run's single
>   failure is the retired sampler control reproducing **the 0.11 column
>   attempt 5 already measured** (16.6033 / 15.3848 / 13.6986% vs the
>   0.7.2 record 15.8028 / 12.7485 / 11.4984), i.e. a record pinned to its
>   recording image saying so. **Leg 1 stops on ruling (1)'s own condition
>   (b):** two runs in the slot (`2 failed / 17 passed`, 255.24 s and
>   244.98 s) are *not* bit-identical — `passivity_max_sigma`
>   0.8613568946068969 / 0.86135689450373, gap ratio 0.8941410489050936 /
>   0.8941410492011536, `‖S−Sᵀ‖/‖S‖` **3.112128e-05 / 3.112131e-05** — and
>   while the first two agree at the precision they would be written to,
>   the third **differs in the 7th significant digit, which is the digit
>   string the ruling would have me write**. Physics green in both runs
>   (reciprocity 2.679e-05 inside 1e-3, σ_max 0.8614 < 1). The wobble is
>   run-to-run on an unchanged tree and image (reduction/factorisation
>   order), and the real-mode leg carries it too (`E_Ω` printed twice in
>   one run, 7e-10 apart). **The decision 3a now waits on is a precision
>   restatement, not a band move:** condition (b) as "agreement to ≤ 1e-9
>   relative across two runs, record written only to digits both runs
>   share" admits all three re-records and writes the symmetry ratio as
>   3.11213e-05 (6 digits); as "bit-identical" it is unsatisfiable on this
>   fixture. Still owed besides that: `circular_loop` +
>   `mutual_inductance_reference` on 0.11 (no `MAG-18` anchor), §5.3's
>   table, the drift disposal — all of 3b. Journal:
>   `docs/testing/attempts.md`, 2026-08-23T05:25Z.
> * **Ruling (1) condition (b) restated — 2026-08-23 03:00 review.** The
>   attempt-6 finding is accepted as measured: the fixtures are run-to-run
>   non-deterministic at ~1e-10 relative (known-issues entry of
>   2026-08-23), so "bit-identical" was a criterion no record on this
>   solver can meet, and it is withdrawn. Note that the implementer's own
>   proposal — "≤ 1e-9 relative" — would *also* reject the `‖S−Sᵀ‖/‖S‖`
>   record (its move is 1.0e-06 relative, because a symmetry residual is a
>   difference of near-equal quantities and cancellation amplifies the
>   same 3e-11 absolute wobble); a single relative tolerance is the wrong
>   shape. **(b′): across two runs of the same command in one slot, the
>   record's move must be ≤ 1% of that record's own unmoved band, and the
>   new value is written only to the digits both runs share — never fewer
>   digits than the band resolves.** Checked against attempt 6's table:
>   `passivity_max_sigma` 1.2e-10 vs band 1e-6 (1.2e-4 of band),
>   gap ratio 3.3e-10 vs 1e-4, `‖S−Sᵀ‖/‖S‖` 3e-11 abs vs 5e-7 abs
>   (6e-5 of band), `E_Ω` 7e-10 vs 1e-4 — all four admitted, and the
>   symmetry record is written as **3.11213e-05**. A record whose wobble
>   is within 100× of its band is *not* re-recordable under (b′): that
>   would be a band too tight for the solver, a finding to file, not a
>   digit to write. **Attempt 6's two runs already satisfy (b′) for all
>   three leg-1 records and for `E_Ω`** (7e-10 within one run is the
>   same floor), so the next slot writes them and confirms green; it does
>   not need to measure them again. Conditions (a), (c), (d) unchanged.
>   Queued as §9 item 2.
> * **Step 3a attempt 7 — 🟡 2026-08-23, 06:00 implementer slot** (branch
>   `66aaf69`, `main` merged in at `d7abf54`; `main` restored to a booted
>   0.7.2 and probed — `0.7.2 / python 3.10.12`, `pgrep -c python3` = 0).
>   Six harness commands, ~1 100 s, no exit 124, no wedge, no denial.
>   **All four licensed records are written and confirmed green, and
>   leg 2 closes.** Leg 1 (complex, `-n 2`), twice in the slot
>   (`20260823T110726Z_…-leg1-confirm.log` `1 failed / 18 passed` /
>   234.88 s; `20260823T112102Z_…-leg1-confirm-rerun.log` same counts /
>   226.36 s, both rank footers identical): `passivity_max_sigma`
>   **0.861356895** (band 1e-6), `‖S−Sᵀ‖/‖S‖` **3.11213e-05** (band 5e-7,
>   six digits per (b′)), two-torus gap ratio **0.894141** (band 1e-4) all
>   reproduce as written in both runs, with the physics green in both
>   (reciprocity 2.679e-05 inside 1e-3, σ_max 0.861357 < 1). Leg 2 (real,
>   `-n 2`, `20260823T111216Z_…-leg2-confirm.log`) is **`11 passed, 4
>   skipped`** / 293.59 s / exit 0 against attempt 6's `1 failed / 10
>   passed / 4 skipped` — `E_Ω` written **1.061717e-01** at 147 235 cells
>   (measured 1.0617170177e-01), rate **1.6854**, monotone, natural-BC
>   ratio 0.3285, and the retired sampler control now keyed by image
>   (raising on an unrecorded one rather than borrowing another's row),
>   reproducing the 0.11 triplet 16.603276 / 15.384842 / 13.698645% to
>   ≤ 3.3e-06. Leg 2's two remaining owed files ran on 0.11 and hold their
>   **existing** bands: `circular_loop` + `mutual_inductance_reference`
>   **`14 passed, 4 skipped`** / 184.85 s / exit 0
>   (`20260823T111729Z_…-leg2-loop-mutual.log`) — loop L2 5.8814% vs the
>   0.08 band, `ωM₁₂` identity 3.093e-07 vs 1e-6, tube quadrature
>   converged at (8,16). **What 3a now waits on is one decision, and it is
>   a new one:** writing the gap ratio unmasked the two later assertions in
>   `test_step_1_measurements_reproduce`, which checks three records in one
>   loop. `STEP1_LUMPED_RATIO_RECORD` reads 0.828893 vs 0.829782 (moved
>   8.89e-04) and `STEP1_CROSS_ROUTE_RECORD` 0.077431 vs 0.077095 (moved
>   3.36e-04), both against the same 1e-4 band, both reproduction records
>   of the *same* solved field on the *same* fixture whose mesh moved
>   184 919 → 184 176 cells — the class ruling (1) licensed — and both
>   satisfying (b′) on this slot's two runs (lumped ratio moves 6.6e-10,
>   6.6e-06 of its band; the cross-route print is identical to six
>   digits). Ruling (1) enumerates **three** numbers, so neither was
>   written: extending a review ruling is not an implementer's call.
>   Known-issues updated with the table; nothing else in either leg is
>   open. Journal: `docs/testing/attempts.md`, 2026-08-23T11:35Z.
> * **Ruling (1) extended to its class — (1\*), 2026-08-23 10:30 review.**
>   Attempt 7 was right not to write them and right that the ruling was
>   the wrong shape: it enumerated three numbers because three had been
>   seen, and a test that checks several records in one loop surfaces them
>   one at a time. Restated as a class rule so no further unmasking needs
>   a review: **a record is re-recordable under (1\*) iff (i) it is a
>   reproduction record of a solved field on a named mesh — a digit string,
>   not a physics band; (ii) every physics gate in the same run holds on
>   0.11; (iii) the fixture's mesh is one the image's gmsh moved
>   (184 919 → 184 176 or 145 900 → 147 235 cells — no other mesh has been
>   shown to move); (iv) it satisfies (b′).** Conditions (a) version-tagged
>   beside the 0.7.2 value with both cell counts, (c) no band moves, (d)
>   branch-only until 3b, unchanged. Checked against attempt 7's two:
>   `STEP1_LUMPED_RATIO_RECORD` 0.829782 → **0.828893** (1e-4 band; move
>   across runs 6.6e-10, 6.6e-06 of band) and `STEP1_CROSS_ROUTE_RECORD`
>   0.077095 → **0.077431** (1e-4 band; identical to six digits) — both
>   admitted, both written to six digits. Any further record the same loop
>   unmasks is written in-slot under (1\*) with its (b′) arithmetic printed
>   in the journal; a record that *fails* (iv) is filed, not written, as
>   before. Queued as §9 item 1 — a write-and-confirm of ~10 min.
> * **Step 3a CLOSED — attempt 8, 2026-08-23, 12:00 implementer slot**
>   (branch `attempt/OPS-18`, `main` merged in at `070b1b5`; `main`
>   restored to a booted 0.7.2 and probed). Four harness commands, ~770 s,
>   no exit 124, no wedge, no denial. Ruling (1\*) executed as written:
>   `STEP1_LUMPED_RATIO_RECORD` **0.828893** and `STEP1_CROSS_ROUTE_RECORD`
>   **0.077431** are written version-tagged beside their 0.7.2 values
>   (0.829782 / 0.077095 at 184 919 cells; new at 184 176,
>   `0.11.0.post0 / gmsh 4.15.2`), the 1e-4 `REPRODUCTION_BAND` and every
>   physics band untouched. **Anchor met, twice in the slot:**
>   `tests/environment` + `test_port_package_sparameters.py` +
>   `test_port_lumped_two_torus.py`, complex, `-n 2`, **`19 passed`** /
>   exit 0 in both runs (`20260823T170403Z_…-leg1-run1.log`, 238.64 s;
>   `20260823T170821Z_…-leg1-run2.log`, 238.73 s; both rank footers
>   identical), against attempt 7's `1 failed / 18 passed`. Both records
>   reproduce identically to six printed digits across the two runs —
>   (b′): the lumped route's `Im Z12` moves 1.029281339 → 1.029281338 Ω
>   (1e-9 absolute; 1e-5 of the 1e-4 band through ωM₁₂), the cross-route
>   print does not move — and the physics is green in both (reciprocity
>   2.679e-05 inside 1e-3, σ_max 0.861356895/0.861356894 < 1 and inside its
>   1e-6 record band, `‖S−Sᵀ‖/‖S‖` 3.112128e-05, open-limit and
>   cross-route decomposition PASS, the pre-stated 5% cross-route MISS
>   unchanged at 7.7431%). **The loop unmasked no further record**, so
>   (1\*) needed no further application. One command beyond the written
>   anchor closed the only other consumer of these constants:
>   `test_port_lumped_narrowed_sheet.py`, whose `f = 1.0` negative control
>   asserts the same two records, is **`12 passed`** / 142.72 s / exit 0
>   (`20260823T171239Z_…-narrowed-sheet.log`) and prints that rung as
>   7.7431% / gap 0.894141 / lumped 0.828893 — the identical digits, so the
>   write is consistent across the package and not just its own file.
>   Leg 2 was closed in attempt 7 ⇒ **3a is closed**; the chunk stays 🟡 on
>   3b (§5.3's table, the drift disposal, the merge). Journal:
>   `docs/testing/attempts.md`, 2026-08-23T17:20Z.
> * **Step 1 — build and boot (standard).** Bump the `FROM` line, rebuild,
>   and fix the environment plumbing that encodes version-specific paths:
>   the compose `PYTHONPATH` (`dolfinx-real/lib/python3.10/…` — both the
>   variant dir and the Python minor can change), the
>   `/usr/local/bin/dolfinx-complex-mode` wrapper, and the from-source
>   h5py build against the image's HDF5. **Done-when (§4):** container Up;
>   real and complex modes both import dolfinx and report the target
>   version under `mpiexec -n 2`; harness log committed.
> * **Step 2 — API migration (standard).** Port `src/` and `tests/` to the
>   new API (0.7→0.11 crosses the `FunctionSpace`→`functionspace` rename,
>   `dolfinx.fem.petsc` assembly/solver rework, and gmsh-interop signature
>   changes). **Done-when (§4):** full suite collects with zero errors in
>   both modes; harness log committed.
> * **Step 3 — re-gate (heavy).** Re-run the quantitative gate suite
>   through the harness at `-n 2`, real and complex legs. **Done-when
>   (§4):** every §2.1 gated number reproduces within its existing band
>   (TH-6 decay/phase, TH-10 lossy-sphere, MAT-4 SAR, MAT-6 ΔR, PORT-1
>   S-params with its two named systematics), pre-existing known-issues
>   failures excepted and cited; elapsed recorded; §5.3's environment
>   table updated. **Traps:** a gated number that moves is a *finding*
>   (upstream regression or a latent bug of ours the old version masked) —
>   open a known-issues entry and stop; never loosen a band to absorb it.
>   Budget discipline: the re-gate leg is heavy-tier — split across runs
>   rather than exceeding the 20-minute ceiling. **Negative result:**
>   park on an `attempt/*` branch with the failing step named; `main`
>   keeps 0.7.2 until all three steps are green.

**`OPS-19` — doc-reference checker: staleness must not own the exit code** ✅ *(commissioned 2026-08-16, 10:30 review; step 1 closed 2026-08-16, 16:30 implementer slot; archived 2026-08-23.)*
> **Result.** `scripts/testing/check_example_doc_references.py` now exits `EXIT_OK`/`EXIT_HARD`/`EXIT_STALE_ONLY` = 0/1/2, with `--stale-severity {fail,report}` defaulting to `report` (`fail` reproduces the pre-split reading bit for bit) and a machine-readable `RESULT: dead=… guide=… stale=… stale_severity=… exit=…` line; `--max-age-s` (`OPS-15`'s 48 h) unchanged, no example re-run or refreshed.
> **Gated:** `tests/unit/test_doc_reference_exit_codes.py`, 8 tests, 1.91 s, smoke, `-n 1` (`20260816T213312Z_OPS-19-step1-rerun.log`) — on the committed tree `dead=0 guide=0 stale=24 stale_severity=report exit=2`, guide pass green at **21/21 examples, 0 pending**; each fixture asserts the exit code against the literal and against arithmetic over the printed counts. **Negative controls:** a dead artifact reference and a missing `.py` both still exit 1 (`dead=1 stale=0`); boundary on the untouched default: 47 h → `stale=0 exit=0`, 49 h → `stale=1 exit=2`.
> **Bug fixed in passing:** `collect_references` called `doc.relative_to(REPO_ROOT)` unconditionally, so any `--docs-root` outside the repo raised `ValueError` (first run `20260816T213248Z_OPS-19-step1.log`, 7 failed / 1 passed, 2 s); now `display_path()`.
> **Carry-forwards:** the checker has exactly one call site class (ad hoc harness commands; `run_examples.sh` has none) — if a docrefs call is ever added to the runner, `0` and `2` are both pass. The stale `paraview_output/` artifacts remain a standing backlog, not this chunk's — and the figure is **55**, not 24: `EX-29` closed 2026-08-24 and the pre-fix count was a census of the 5 examples that write to the repo-root directory (`EX-30` refreshes the set).
> Full narrative: `docs/planning/plan-archive.md`, entry «§7 OPS-19 full narrative — archived 2026-08-23 (weekly review)».

**`OPS-16` — retry-on-529 in the automation launchers** ⬛ **WON'T FIX** *(commissioned 2026-08-13, 10:30 review; blocked 2026-08-14, 21:00 run; **declined by the human operator 2026-08-22, interactive session**; archived 2026-08-23. Do not re-commission, do not re-raise the permission ask, and do not queue it in §9.)*
> **Result.** Blocked by the permission layer, not the work: every file lives under `scripts/automation/`, and `Edit(scripts/automation/**)` is in the **`ask`** section of `.claude/settings.json`, which a headless `claude -p --permission-mode acceptEdits` run cannot answer — no scheduled session can execute this chunk in any scoping. **Operator decision 2026-08-22:** the rule **stays under `ask`** (a session that can edit its own launcher can change its own model, effort, timeout, `--permission-mode` and `--disallowedTools`), and the avoided cost — a few implementer slots lost to an out-of-credits, API-500 or 529 launch failure (worst observed: the 2026-08-19 18:00 review, `logs/automation/20260819T230001Z_daily-review.log`, one review plus effectively four implementer slots) — is **acceptable**. Settled, not open. The full design is recorded in the 2026-08-14T02:03Z `docs/testing/attempts.md` entry for reference only.
> **Standing instructions, in force until the operator says otherwise:** (1) do not queue `OPS-16` in §9, as a fallback or spare, or toward queue depth; (2) do not re-escalate the unblock on the dashboard's Waiting-on-you, in attempts.md, or in a review summary; (3) journal launch failures as ordinary weather — record the cost, never attribute it to a missing `OPS-16`.
> **Live carry-forwards:** `.gitignore:13` is a bare `lib/` (no leading slash), so any `*/lib/` in the repo is **ignored at any depth** — still true, still worth fixing if such a directory is ever added (use another name or a `!scripts/automation/lib/` negation). The *supervisor* framing (retry logic above the launcher, in an ungated directory called by cron with its own outer `timeout`) is recorded so it is not re-derived, **not** as a queued alternative.
> Full narrative: `docs/planning/plan-archive.md`, entry «§7 OPS-16 full narrative (won't fix) — archived 2026-08-23 (weekly review)».

**`OPS-17` — delete or replace the finiteness-only test suites** ✅ *(commissioned 2026-08-16, operator session; step 1 ✅ 2026-08-17, step 2 ✅ 2026-08-17, step 3 legs (a) 2026-08-17 / (b1) 2026-08-18 / (b2) closed by the 2026-08-21 18:00 review — **chunk ✅ 2026-08-21**; archived 2026-08-23.)*
> **Step 1 — sweep (`scripts/testing/finiteness_sweep.py`, AST):** `20260817T020244Z_OPS-17-step1-sweep.log`, smoke, 2 s, exit 0 — **306 test functions in 89 files: 225 `QUANT`, 22 `pytest.raises`-only, 59 candidates** (11 assert nothing); every candidate read; disposition **10 replace / 4 delete / 45 keep**. Finding: no `⚠️` chunk was propped up by a swept row.
> **Step 2 — dispositions (2026-08-17, 06:00 slot):** 4 deletes + 10 replacements landed, all `-n 2`: `20260817T111036Z_OPS-17-step2-collect.log` (359 collected, 6 s), `20260817T111054Z_OPS-17-step2-mesh-n2.log` (15 s), `20260817T111217Z_OPS-17-step2-solver-n2.log` (41 s), `20260817T112448Z_OPS-17-step2-th-smoke2-n2.log`, `20260817T113031Z_OPS-17-step2-portgap-n2.log` (1 passed, 448 s), `20260817T113806Z_OPS-17-step2-xfail-n2.log` (10 passed, 2 xfailed, 202 s). Anchors: `solver/test_cylinder.py` straight-wire `μ₀I/2πr` **13.2751%** L2 (band 25%); `solver/test_coil_phantom_magnetostatics.py` on-axis two-loop Biot–Savart **17.1233%** L2 (30%); `solver/test_two_torus.py` and `mesh/test_mesh_tag_integrity.py` volume-partition ratio **1.000000000000** (1e-9); `mesh/test_birdcage_port_tags.py` layout diagnostics exact (1e-12); `validation/test_straight_wire.py` fitted h-rate in `[0.7, 1.5]`; `validation/test_port_gap_voltage_impedance.py` 3b-x record pinned (1%). Four defects surfaced as `xfail(strict=True)`, **no band loosened**: region-resolution policy shrinks coil volumes **−21.68% / −22.62%** (→ `GEO-17`); Coulomb multiplier spread **7.836781e+00** on a divergence-free source (→ `MAG-17`); Poynting imbalance **116.7465%** vs 25% with wrong-sign flux, and `poynting_power_balance` raising on scalar `sigma=0.0` (→ `POST-5`). `⚠️`-retirement clause: confirmed, nothing to retire.
> **Step 3 leg (a) — real mode, closed 2026-08-17:** sweep control **56 candidates, reconciled** against the prescribed 45 (two `replace` rows kept finiteness bodies via a new sibling test; 10 newcomers keep-class; `20260817T200056Z_OPS-17-step3-sweep.log`); `tests/ --ignore=tests/validation` **3 failed, 134 passed, 32 skipped, 2 xfailed** / 218 s (`20260817T201248Z_OPS-17-step3-real-nonvalidation-n2.log`); real validation 33 + 1 + 5 = **39 passed, 167 skipped = 206** (`20260817T213419Z_OPS-17-step3b-real-validation-remainder.log`, `20260817T213843Z_OPS-17-step3b-real-mesh-cache.log`, `test_convergence.py` priced at 119.61 s); collect **377 = 171 + 206** exactly (`20260817T214141Z_OPS-17-step3b-collect-real-unpiped.log`). The 3 failures are named: two `_DummyComm` `allgather` regressions from `PORT-1` step 4 and known-issues entry 3's zero-diagonal.
> **Step 3 leg (b1) — complex non-validation, closed 2026-08-18:** `3 failed, 122 passed, 1 xfailed` / 392.76 s (`20260818T123045Z_OPS-17-step3d-complex-nonsolver.log`); `tests/solver` **46 passed, 2 xfailed** / 111.22 s warm (`20260818T141104Z_OPS-17-step3e-complex-solver-warm.log` — defect 3's Poynting xfail and `MAG-17`'s observed in a completed leg); `test_coil_phantom_magnetostatics` FAILED in its own completed log (`20260818T124712Z_OPS-17-step3d-coilphantom-complex.log`, `ComplexComparisonError` → `OPS-20`); collect 49 (`20260818T141312Z_OPS-17-step3e-collect-solver.log`); 126 + 45 = **171**, the same 171 as leg (a).
> **⚠️ Memory-premise caveat (2026-08-24).** The `coil_loading_degree2` deferral below rests on the `TH-12` degree-2 memory wall measured at the **old 64 GiB** ceiling; §5.1 now records **128 GiB**. If that file becomes runnable the **216 denominator moves** — which is a **review** decision and an explicit re-based close, never a silent edit. The deferral stands until then; `port_gap_voltage_padding` is unaffected (its reason is padded-record-only, not memory).
> **Step 3 leg (b2) — complex validation, closed 2026-08-21 18:00 review at 216 of 216:** nine attempts 2026-08-19 → 2026-08-21 across 25 exit-0 complex logs (`20260819T020055Z_OPS-17-step3f-complex-portgap-impedance.log`, 24 passed / 488.37 s, through `20260821T033534Z_OPS-17-step3j-sar-padding-group.log`, 14 passed / 247.68 s); every printed physics figure bit-identical to its `MAT-6`/`TH-11`/`PORT-10` record (e.g. `dR` 1.5763% / 1.0562% / +1.5834% / +5.5912%, `ΔR = +1.3838746e+00 Ω`, 417914 cells), only wall-clock moved (≤ +9.28%); denominator re-based 206 → 225 → 227 → **232**, audited `20260821T050352Z_OPS-17-step3l-collect-audit2.log` (236 = 4 + 232), observed file set 49 of 51 with the complement exactly the two deferred files. **Formally deferred:** `test_coil_loading_degree2.py` (14 — record `5 passed, 13 skipped`, the skips *are* the `TH-12` memory wall) and `test_port_gap_voltage_padding.py` (2, since attempt 3); attempting either is new-chunk work with a memory prescription.
> **Live carry-forwards:** the 3 `tests/ports/` failures remain named expected failures owned by `PORT-1` / known-issues entry 3; the 10 post-sweep candidate newcomers (`TH-11` step 4/5a ×8, `PORT-9` step 2b ×1, `OPS-17`'s deliberate `isnan` half ×1) await a review disposition; the `OPS-18` deferral commitment was executed 2026-08-21. **Standing rules learned here:** never pipe pytest inside a harness command (the footer reports the pipe's exit); complex ≈ 2.6–2.7× real on a warm FFCx cache, a family's first cold command ≈ ×3 (size as a throwaway warm-up); size each file from *all* its own recorded logs (width and elapsed), a padded record is an upper bound; rung/mode env vars select meshes, not test partitions — confirm splits against collect IDs; preflight `find /root/.cache/fenics -name '*.c' -size 0` and delete stubs only; coverage cannot be re-derived from node IDs at `-n 2` (footer arithmetic + file presence is the sound route); a non-collective complex raise hangs `mpiexec` ~300 s on exit; `memory.peak` is pinned at `memory.max` and read-only — use `memory.current`.
> Full narrative: `docs/planning/plan-archive.md`, entry «§7 OPS-17 full narrative — archived 2026-08-23 (weekly review)».

**`OPS-20` — disposition the coil-phantom `ComplexComparisonError`** ✅ *(closed 2026-08-19, 06:00 implementer slot; disposition (a) — fixed, not marked; no `@real_only`, complex collect stays at 49)*.
- The commissioned `ComplexComparisonError` was dead on arrival: the test imports `azimuthal_current_density` from `tests/validation/test_circular_loop.py`, already repaired by `OPS-22`; no cold-cache window spent. The real defect was the second layer (`ValueError: Unknown format code '%' for object of type 'complex'` at `test_coil_phantom_magnetostatics.py:145`, rank-split because only rank 0 prints); fixed with the `OPS-22` idiom — assert `max|Im B_z| ≤ 1e-12·max|B_z|`, compare on `np.real`. The ~300 s non-collective exit hang died with the raise.
- Gated numbers (`-n 2`, standard): real control before edit L2 **17.1233%** vs the 30% band (`OPS-17` step-2 record to the digit); complex after fix **1 passed / 5.11 s, L2 17.1233%**, both ranks identical; real re-run **17.1233%** unmoved. Stub sweep clean before and after.
- Logs: `20260819T110051Z` (real control, 7 s), `20260819T110111Z` (complex diagnosis, `--tb=long`, user frame at :145), `20260819T110144Z` (complex fixed), `20260819T110156Z` (real re-run); uncounted whole-`tests/solver` complex batch `20260819T110220Z` timed out at 89% (exit 124, 481 s) — no count claim.
- Carry-forwards: complex `tests/solver` no longer fits a 480 s window (111.22 s warm on 2026-08-18; `POST-5` step 2 is the candidate for the added cold forms); the two examples journaled by `OPS-22` (`02_circular_loop.py:173`, `04_helmholtz_analytic_comparison.py:79`) will carry this second layer too.

Full narrative: `docs/planning/plan-archive.md`, entry «§7 OPS-20 full narrative — archived 2026-08-23 (weekly review)».

**`OPS-21` — make the combined-XDMF test scalar-type-aware and
rank-deterministic** ✅ *(closed 2026-08-19, 16:30 implementer slot; test-side only, no writer change)*.
- The rank split was never a tmp-path race (the fixture has broadcast rank 0's path since `8c6ac03`): the mechanism was the test's own `if comm.rank != 0: return`, so non-zero ranks passed unconditionally and real-mode coverage was rank-0-only. Fix: rank 0 parses light data + every referenced heavy array (`_read_combined`), `comm.bcast`s, every rank runs every assertion. `SCALAR_IS_COMPLEX` selects `EXPECTED_NAMES`; the complementary spelling is `FORBIDDEN_NAMES`, asserted disjoint; imaginary parts asserted identically zero.
- Gated: exact set identity in both builds at `-n 2`. Real `{CellTags, F, G}` with the six split names absent — 1 passed / 3 s (`20260819T213140Z_OPS-21-step1-real.log`). Complex `{real_F, imag_F, real_G, imag_G, real_CellTags, imag_CellTags}` with the three bare names absent — 5 passed / 2 s (`20260819T213153Z_OPS-21-step1-complex.log`). Both ranks' summary lines identical in each run.
- Red baseline (predicate inverted): 1 failed on **both** ranks, byte-identical message, exit 1 / 2 s (`20260819T213221Z_OPS-21-step1-redbaseline.log`); reverted and re-confirmed green, 1 passed (`20260819T213234Z_OPS-21-step1-real-final.log`).
- Carry-forwards: `OPS-17` leg (b1) may count this file in complex; known-issues entry removed. Follow-up, not forced: the `G` field still has no value assertion in either build (presence + zero imaginary part only). The rank-0-return pattern was swept repo-wide by `OPS-23`.

Full narrative: `docs/planning/plan-archive.md`, entry «§7 OPS-21 full narrative — archived 2026-08-23 (weekly review)».

**`OPS-22` — make the three magnetostatic loop-drive fixtures
complex-safe** ✅ *(closed 2026-08-19, 04:30 implementer slot; fixed, not marked — all three files, no `@real_only` anywhere)*.
- Two defects: (i) the commissioned `ufl.max_value` / `<=` predicates in the fixtures' `current_density` callables — regularised inside the `sqrt` (`+ 1e-24`), wire predicates rewritten as `ufl.le(ufl.real(r²), a²)`; (ii) a second layer behind it — `evaluate_vector_field_parallel` returns the complex scalar type for a real magnetostatic solution (`ValueError: Unknown format code '%'`), fixed by asserting `max|Im B_z| ≤ 1e-12·max|B_z|` then comparing on `np.real` (a new complex-mode assertion, no-op in real mode).
- Gated (`-n 2`): real baseline before any edit 5 passed / 223.24 s — loop relL2 **7.0658%**, max **13.8212%**, |B_z|max 2.974560e-05 T; Helmholtz centre **0.728%**, mean **0.644%**, CV **0.1602%** (`20260819T093105Z`); after predicate fix (`20260819T093529Z`) and after real-part fix (`20260819T095414Z`, 5 passed / 199.91 s) every digit identical. Complex build, all three files (`20260819T094710Z`, `FEM_EM_REQUIRE_COMPLEX=1`): **5 passed / 412.12 s / exit 0**, both ranks identical, digits match the real record to the last figure. Interim `20260819T093933Z` (1 failed / 3 passed) is the between-fixes state. Stub sweep clean before and after.
- Costs for sizing: `test_circular_loop` is the sink in complex — **289.41 s** (on-axis) + **102.46 s** (symmetry); magnitude file 18.99 s; `_v2` 0.74 s.
- Carry-forwards: the same `max_value` idiom stands in `examples/magnetostatics/02_circular_loop.py:173` and `04_helmholtz_analytic_comparison.py:79`, unexercised in complex mode (expect layer (ii) there too); `OPS-17` leg (b2) may draw its 5 blocked tests; `test_helmholtz_v2.py`'s `float()` cast caveat was closed by `OPS-23`.

Full narrative: `docs/planning/plan-archive.md`, entry «§7 OPS-22 full narrative — archived 2026-08-23 (weekly review)».

**`OPS-13` — land the rank-safe `_validate_material_map_tags` fix** ✅
*(2026-08-08; full narrative in `docs/planning/plan-archive.md`)*. The one
hunk from the 3b-xiii branch: the tag set is reduced with
`mesh.comm.allgather` before it is tested. New gate
`tests/materials/test_material_map_rank_safety.py` — worst-case fixture
(exactly one tagged cell of 162), exact set identity + volume identity to
1e-12, every digit identical at `-n 2`/`-n 4`; red baseline reproduced the
3b-xiii hang (exit 124) with the hunk stashed. In CI at both widths.
Observed and left alone (worth a review's scoping):
`build_material_fields`'s `phantom_cells.size == 0` check reads the same
rank-local array — unmeasured, not known-broken.

**`OPS-14` — diagnose the rank-dependence of `test_single_port_excitation`
(known-issues 6)** ✅ *(closed as a diagnosis 2026-08-08; full narrative in
`docs/planning/plan-archive.md`)*. Two defects, both wholly inside the
`PORT-0` placeholder: the fixture tags over **rank-local** indices (the
global tag set is rank-count dependent — required tags genuinely absent at
`-n 4/8`), and `excitation.py` handed rank-local `cell_tags.values` to the
validator (non-collective raise — the 3b-xiii hang family). Separated by
counterfactuals; neither fix suffices alone. Pre-registered not-to-fix
branch taken: known-issues 6 re-pointed at `PORT-1` (whose step 4 later
fixed the validator defect); only a docstring hazard warning landed under
`src/`. Survey: no other non-collective tag read remains in `src/`.

**`OPS-11` — `tests/mesh` in CI** ✅ *(created 2026-08-02, closed 2026-08-03,
12:00 run; full narrative archived in `docs/planning/plan-archive.md`)*
> The directory no job ran — which is why known-issues 7 (mesh generators
> failing outright) sat undiscovered. The `validation` job's
> `Mesh generation suite` step now runs the **whole directory** with exactly
> one exclusion left: the known-issues-5 `--deselect` (off-centre sizing
> arithmetic) — **removed 2026-08-06 by `GEO-4` step 1; the step now excludes
> nothing and runs 27 passed 1 skipped in 85.3 s**. **20 passed 1 skipped
> 1 deselected in 42.15 s, exit 0**
> (`20260803T200504Z_GEO-9-step2b-gate.log`; the birdcage `--ignore` was
> removed by `GEO-9` step 2b as required). The "those and only those" control
> was executed, not quoted (`20260803T170132Z_OPS-11-fullsweep.log`); the
> §4.3 assertion is the volume-partition identities (`1e-9`) executing in CI
> across three files. The remaining exclusion is annotated at its
> known-issues entry and must be removed by the commit that fixes it.

**`OPS-10` — complex-mode CI job** ✅ *(2026-07-31; full narrative archived)*
> Before this, CI executed **no** time-harmonic solve at all (`@complex_only`
> skips). The `validation-complex` job sources
> `/usr/local/bin/dolfinx-complex-mode` and runs `tests/environment` first
> (so an environment regression is not blamed on the formulation), then the
> frequency-domain gates, under `FEM_EM_REQUIRE_COMPLEX=1` — which converts
> skips into failures so the job cannot pass by skipping. Verified with the
> CI-fidelity invocation (no `PYTHONPATH` override, `pip install -e`) plus a
> real-mode negative control that fails rather than skips.
>
> **This job has never executed on a GitHub runner.** Local `main` is well
> ahead of `origin/main` — nothing pushed since 2026-07-27 — so every "in CI"
> claim in this file is verified by local reproduction of the CI invocation
> only. The runner-environment caveat settles on the first push, which is a
> human action, not a scheduled-session one.
> CI notes for anyone editing `.github/workflows/ci.yml`: MPI here is
> **MPICH/Hydra**, so `--allow-run-as-root` is not a valid flag and will break the
> job. The `validation` job timeout is 45 min (`MAG-13` is heavy tier). Two tests
> are explicitly `--deselect`ed, both downstream of the time-harmonic proxy and to
> be revisited with `TH-1`: `test_phantom_material_assignment_and_time_harmonic_pipeline_wiring`
> and `test_phantom_field_metrics_and_exports_are_finite`.

**`OPS-12` — adjudicate the residual-trend classifier** ✅ *(2026-08-08;
retires known-issues 2; full narrative in
`docs/planning/plan-archive.md`)*. The code was wrong on all three counts,
not the test: undocumented asymmetric thresholds (labels now partition by
the sign of `f − 0.5`, table in the docstring); the second failure's
recorded symptom was wrong (an under-resourced `ksp_max_it` cap — the cap
moved, not the assertion); and the classifier was **unreachable in
production** (the time-harmonic path never called
`setConvergenceHistory()`, so the membership assertion had passed
vacuously) — now armed and tied to the unit identity. Gate: exact discrete
identity on an 11-row family spanning both threshold sides; in
`validation-complex`.

**Open follow-up in OPS — the `lint` CI job is red on `main`, and that is
adjudicated as expected-red for now** *(surfaced by `OPS-12`'s regression
log, decided 2026-08-08, 03:00 review)*. `flake8`/`black --check`/`isort
--check-only` fail on `src` and `tests` from **pre-existing** debt (W293
throughout `solvers.py`, E501 in `time_harmonic.py`, etc.) — no recent chunk
introduced any of it (verified for `OPS-12`: zero findings on its added
lines). A repo-wide reformat is deliberately **deferred until the `PORT-1`
lineage lands**: `attempt/PORT-1-step3bxiii-…` carries a 2000+-line test
file plus `src/` edits, and reformatting `main` underneath it would turn the
eventual landing into a conflict festival for zero behavioral gain. Whoever
lands that branch should scope the reformat as the next OPS chunk, in its
own commit, immediately after. Until then: red `lint` is known and expected;
do not "fix in passing", and do not read it as a chunk failure.

**`OPS-15` — retire the checker's standing freshness tax** ✅ *(2026-08-10;
full narrative in `docs/planning/plan-archive.md`)*. The doc-reference
checker's default `--max-age-s` went 3600 → **172800 (48 h)** — the 1 h
window was shorter than the 90-min slot grid and taxed every
example-touching slot an 80–200 s refresh. Two-sided anchor met: default
exits 0 on day-old artifacts with zero refresh solves; `--max-age-s 1`
still flags all 14 (the branch is retuned, not disabled — the 158-h
`EX-14` catch stays 3.3× over the new limit).

**`OPS-23` — sweep the `OPS-21` rank-0-return defect pattern + the
`test_helmholtz_v2.py` Im-bound** ✅ *(step 1 closed 2026-08-20, 09:00 implementer slot — and the chunk closes; test-side only, no `src/` change, no gate value moved)*.
- The commissioned census was wrong in both directions: `test_degree2_energy_mechanism.py:237` and `test_lossy_sphere_degree2.py:249` are guards inside a `_print_table` helper, not defects (left untouched, not run); the exempted `test_csv_export_stats_parity.py:252` is a real instance (rank-0-only negative control of `POST-1` step 6). Three real sites, all in `test_csv_export_stats_parity.py` (`:143`, `:192`, `:252`), fixed with the `OPS-21` template (rank 0 parses + `bcast`, every rank asserts, prints stay rank-0). `test_helmholtz_v2.py` gets `max|Im B_z| ≤ 1e-12·max|B_z|` before the `float()` casts, then explicit `np.real`.
- Gated (`-n 2`, smoke, both ranks identical every run): csv complex 11 passed / 5.51 s — 5 184 default rows / 4 896 guarded / **288** drops per tag, worst round-trip disagreement **3.808e-16** vs unmoved 1e-12 (`20260820T140248Z_OPS-23-step1-csv-green.log`); helmholtz real 2 passed / 3 skipped / 0.82 s (`20260820T140344Z_OPS-23-step1-helmholtz-real2.log`) and complex 5 passed / 1.09 s (`20260820T140330Z_OPS-23-step1-helmholtz-complex.log`), mean B_z **4.219228e-09 T**, CV **0.1873%** vs unmoved 1% gate, `max|Im B_z| = 0.000e+00` vs 4.231e-21 bound.
- Red baseline, all four fixed predicates inverted: 8 failed / 4 passed / exit 1 / 5.13 s, the eight `AssertionError` lines byte-identical between ranks (`20260820T140405Z_OPS-23-step1-redbaseline.log`); final 12 passed / exit 0 / 5.00 s (`20260820T140438Z_OPS-23-step1-final.log`).
- Standing nuance: round-off-scale nondeterminism in the iterative solves (round-trip 3.808e-16 vs 3.822e-16; helmholtz `std B_z` moves in the 6th significant digit, 7.902679 / 7.902639 / 7.902744e-12), four–six orders below the gates; gated digits bit-stable.

Full narrative: `docs/planning/plan-archive.md`, entry «§7 OPS-23 full narrative — archived 2026-08-23 (weekly review)».

### MAG — Magnetostatics (Phase 1)

| ID | Title | Status | Tier | Result |
|---|---|---|---|---|
| `MAG-1` | Vector-potential formulation, N1curl, gauge penalty | ✅ | standard | 0.04% centre vs closed form |
| `MAG-2` | Straight-wire analytic validation | ✅ | standard | |
| `MAG-3` | Circular-loop analytic validation | ✅ | standard | |
| `MAG-4` | Helmholtz analytic validation | ✅ | standard | 0.04% centre / 0.83% mean |
| `MAG-5` | h-refinement convergence study | ✅ | standard | |
| `MAG-6` | Coil+phantom B-field symmetry metric strategy | ✅ | landed on DG0 at h = 0.010: mirror-symmetry `max_rel_diff` **0.323844 / 0.302661 / 0.308407** at `-n 1/2/4` vs the untouched 0.350, three-way rank spread **7.00%** (gate ≤ 10%); `-n 1` byte-reproduces the on-record 0.323844 | steps 1–3 ✅ 2026-08-08 — CG1 interpolation owned it (rank-dependent 3.03×, non-convergent under `h`); boundary and gauge exonerated; ~0.53 was discretisation (p ≈ 1.07); step 3 re-pointed **both** sampled metrics at DG0 and refined one rung, no tolerance touched; known-issues 4 retired. Gates discretisation symmetry, **not** phantom physics (uniform μ) |
| `MAG-7` | Fix point evaluation in validation tests | ✅ | standard | |
| `MAG-8` | Restrict straight-wire current density to the wire | ✅ | standard | |
| `MAG-9` | Re-size validation meshes to fit the tier budget | ✅ | standard | |
| `MAG-10` | Gauge penalty was below the safe window | ✅ | standard | default now 1.0 |
| `MAG-11` | Parallel energy was rank-local (missing allreduce) | ✅ | smoke | |
| `MAG-12` | `evaluate_at_points` used the MAG-7 broken pattern | ✅ | smoke | |
| `MAG-13` | Analytic-Dirichlet outer boundary for wire/loop | ✅ | heavy | wire 12.75%, loop 7.07%, rate 1.10; 167 s + 196 s. **2026-08-25: its rate gate (`test_h_refinement_straight_wire`, band [0.7, 1.5]) is red on `main` on the 0.11 image — fitted 1.9038, the finest rung's error collapsed 9.26% → 4.4605% (known-issues 2026-08-25). Disposition is `MAG-19`; the ✅ here is the 0.7.2 close and stands.** |
| `MAG-14` | Helmholtz magnitude comparison in the test suite | ✅ | smoke | 0.728% vs closed form (1.731% before `GEO-8`); 11 s, in CI |
| `MAG-15` | Lagrange-multiplier Coulomb gauge (cross-check) | ✅ | smoke | 7 passed, 13 s |
| `MAG-16` | Complex-build-safe magnetostatic energy | ✅ 2026-08-05 | smoke | 10 passed complex `-n 2` in 4.9 s; cross-build pin 2.9e-07, `Im W` exactly 0; retires known-issues 8 |
| `MAG-17` | Coulomb-gauge multiplier does not vanish for a divergence-free source: h-ladder discriminator (`OPS-17` step-2 defect 2, known-issues 2026-08-17; commissioned 2026-08-17 10:30 review) | ✅ *(audited COMPLIANT 2026-08-21 18:00 review — rate 2.4476 vs the pre-registered ≥ 0.7 verified in `…final2.log`; one nuance on record: the cited "ladder" log is exit 1 — a sign-convention fix in the fit sits between it and the record run, same spreads, band unmoved)* | standard |
| `MAG-18` | Sampler-independent straight-wire gate: annulus-restricted domain L2 of `|B_h| − |B_ana|` with a pre-registered rate band (`OPS-18` step 3 attempt 5 finding, known-issues 2026-08-22: the 10-point radial L2 swings 34% under its own sampler and the 15% band already fails on 0.7.2 at `n_points = 8`; commissioned 2026-08-22 18:00 review) | 🟡 **2026-08-22** — the gate is built, live on `main` and green: `E_Ω` 25.3787 → 10.7288 → 6.6708% on the recorded ladder, **rate 1.6842 ≥ 0.7** and monotone (i ✅); natural-BC wall 32.3117% vs analytic 10.7288%, ratio 0.3320, strictly worse (iii ✅); the h = 0.0025 record 1.0728835983e-01 at 145 884 cells reproduced bit-identically across two `-n 2` runs; the retired 10-point row reproduced under assertion at all three sample counts (15.802788 / 12.748522 / 11.498352% vs 15.8028 / 12.7485 / 11.4984, ≤ 4.2e-06 relative). **Anchor (ii) not met as pre-registered:** `-n 2` vs `-n 4` agree to **7.28e-08**, not 1e-10 — the solve is a direct LU whose factorization order follows the partition, and the *retired* statistic moves the same way on the same two runs (1.9e-07), so ~1e-7 is the solve's cross-width floor and no norm on this field beats it. Known-issues entry filed; the 1e-10 clause is the review's to dispose of. `7 passed`/270.64 s/`-n 2`. **✅ 2026-08-23 03:00 review** — (ii) re-registered at ≤ 1e-6 relative (14× the measured floor, five orders under the sampler defect it excludes), met by the logged `-n 2`/`-n 4` pair; prose entry has the audit. **Re-gated on 0.11 2026-08-23 (§9 item 1, ruling (3\*)) — all three anchors green on the image `main` boots, `7 passed` / exit 0 twice in-slot** (`20260824T003059Z_MAG-18-regate-run1.log`, 296 s; `20260824T003650Z_MAG-18-regate-run2.log`, 296 s; `-n 4` record probe `20260824T003606Z_MAG-18-regate-n4.log`, 32 s): (i) `E_Ω` 25.2868 → 10.6172 → **6.6458%** monotone at fitted rate **1.6854** (0.7.2 read 1.6842 — the *gate* moved 7e-04 across a version change that moved the mesh 145 884 → 147 235 cells, which is the point of `MAG-18`); (ii) `-n 2` 1.0617170177e-01 vs `-n 4` 1.0617175341e-01 = **4.86e-07 relative**, inside the re-registered 1e-6 and consistent with the ~1e-7 LU floor, with the two `-n 2` runs agreeing to 1.86e-08; (iii) natural BC 32.315493% vs analytic 10.617170%, ratio **0.3285**, strictly worse. **No record moved and no band moved** — `E_OMEGA_H0025_RECORD` (1.061717e-01, already version-tagged v0.11.0 by 3a leg 2) reproduces to 2.9e-09 of its 1e-4 band, and the `0.11` `n_points` control row reproduces at all three counts (≤ 3.6e-06 relative). | heavy |
| `MAG-19` | Dispose of the red straight-wire rate gate on 0.11 (fitted 1.9038 vs [0.7, 1.5]; the finest rung's sampled error collapsed on the image): anomalous rung vs wrong instrument, discriminated by running both norms on the same four-rung ladder (commissioned 2026-08-25 10:30 review; known-issues 2026-08-25) | 🟡 *(**step 1 measured 2026-08-25, 13:30 slot** — the 4×2 table exists and both in-run anchors reproduce digit for digit: the sampled three-rung fit is **1.9038** (the red) and the `E_Ω` three-rung fit is **1.6854** with the h = 0.0025 `E_Ω` record at 2.094e-08 relative, i.e. the `ANS-1` import is right and the physics is what moved. **The pre-stated decision rule selects neither branch**, and says so cleanly: (a) fails because the sampled ladder has a *second* out-of-band pair that does not involve h = 0.0018 (0.004→0.003 at **0.5822**), and (b) fails because the sampled norm is not scattered everywhere — dropping h = 0.0018 alone returns the fit to **0.7309**, inside [0.7, 1.5]. New finding for the ruling: `E_Ω` is stable but **cannot carry the two-sided band** — its pairwise rates run 1.4261–1.9843 and its fit is 1.6661–1.8588 on every subset, so a duty *transfer* of [0.7, 1.5] as written would be instantly red; `E_Ω`'s live gate is one-sided ≥ 0.7 and it passes that on 6/6 pairs. Probe `tests/validation/probe_straight_wire_dual_norm.py` (asserts nothing), log `20260825T183555Z_MAG-19-step1-dualnorm-fits.log`, 160 s at `-n 2`; h = 0.0030 priced at 88 018 cells / 16.5 s. No band moved; ruling requested — options in the prose entry)* | standard |

**`MAG-17` — the Coulomb-gauge multiplier does not vanish for a
divergence-free source: h-ladder discriminator** ✅ *(step 1 closed 2026-08-20, 07:30 implementer slot — and the chunk closes; audited COMPLIANT 2026-08-21 18:00 review)*.
- Verdict **DISCRETE-SOURCE**: multiplier spread 7.836781e+00 → 3.052022e+00 → 1.438617e+00 at h = 0.005 / 0.0035 / 0.0025 (29 190 / 82 819 / 208 049 cells), fitted log-log rate **2.4476** (pairwise 2.645 / 2.234) vs the pre-registered ≥ 0.7 band; the ASSEMBLY-DEFECT band (|rate| < 0.3) missed superlinearly. Base rung reproduces the `OPS-17` record to every printed digit. Negative control: the incompatible straight wire stays at 2.083064e+02, > 10× the loop's base-h spread (recorded 26.6×).
- Diagnosis: the anchor was wrong, not the constraint block — `p` absorbs the interpolated `J`'s O(h) discrete divergence, so "spread → 0 to solver tolerance" cannot hold on any single mesh. The strict xfail is retired; the claim now lives in `tests/solver/test_gauge_multiplier_convergence.py` (monotone decrease + rate ≥ the **unmoved** 0.7, deliberately not tightened; plus `test_multiplier_still_separates_an_incompatible_source`); `test_gauge_lagrange.py` keeps the wire-side scale gate.
- Standard tier, 97 s at `-n 2`, real build. Logs: `20260820T123307Z_MAG-17-step1-ladder.log` (ladder; exit 1 — a sign-convention fix in the fit sits between it and the record run, same spreads, band unmoved), `20260820T123823Z_MAG-17-step1-final2.log` (final, 6 passed), sizing probe `20260820T123124Z_MAG-17-step1-probe.log`.
- Carry-forwards: known-issues defect 2 retired in the same commit; none owed — the residual is benign; `MAG-15`'s open follow-ups are unaffected.

Full narrative: `docs/planning/plan-archive.md`, entry «§7 MAG-17 full narrative — archived 2026-08-23 (weekly review)».

**`MAG-16` — complex-build-safe magnetostatic energy** ✅ *(2026-08-05;
retires known-issues 8; full narrative in `docs/planning/plan-archive.md`)*.
`compute_magnetic_energy()` reduces with `np.real` and **raises** above
`ENERGY_IMAG_RTOL = 1e-8` (`abs()` rejected deliberately — it would absorb
a negative real part too). Cross-build pin 2.9e-07 (penalty; its operator
carries the gauge null space, hence `PIN_RTOL = 1e-5`) / 1.3e-13
(Lagrange); `Im W` exactly 0 by `ufl.inner` conjugation. The file joined
the `validation-complex` CI job, which is what stops the cast returning.

**`MAG-6` — the step record, compressed** *(steps 1–5; full plans,
journals and the step-4 √3 diagnosis archived in
`docs/planning/plan-archive.md`)*:
> * **Step 1** (2026-08-08): the boundary-mirror hypothesis died — the
>   symmetry metric is **rank-dependent 3.03×** through the CG1
>   interpolation (`curl A` is cell-wise constant; nodal averaging is
>   partition-dependent), while DG0 sampling is rank-stable; padding and
>   gauge both exonerated on the DG0 path. The negative control is not
>   directional because μ is uniform — the phantom is physically invisible.
> * **Step 2**: the DG0 metric converges at p ≈ 1.07 and meets the
>   untouched 0.350 at h = 0.010; CG1 does not converge on the same ladder.
>   The finest rung voided itself by its own rank-spread control (point
>   sampling under a fixed grid becomes a partition question again — the
>   ceiling on refining this estimator).
> * **Step 3** (closes the chunk, known-issues 4 retired): the test
>   samples DG0 at h = 0.010, both metrics re-pointed, tolerances
>   untouched; mirror `max_rel_diff` 0.324/0.303/0.308 at `-n 1/2/4`,
>   spread 7.00% vs the ≤ 10% gate. The centerline metric carries **no**
>   rank-stability claim.
> * **Step 4**: the centerline's "88% scatter" was two things — a **√3
>   probe bug** (`Function.eval` squeezes a single point to shape `(3,)`;
>   always `.reshape(-1, 3)` — `evaluate_vector_field_parallel` is immune
>   by construction) and **gauge contamination** at the sub-floor
>   `gauge_penalty=1e-3`; at the validated 1.0 the spread is 0.341%.
> * **Step 5**: the gate fixture solves at the validated floor
>   (`1e-3 → 1.0`); both metrics landed on their step-4 predictions to
>   < 0.01%. Of the other sub-floor call sites, only `examples/mri/01`
>   carried on-record numbers — handled by `EX-13`/`EX-16`.
>
> The metric gates **discretisation symmetry, not phantom physics**
> (uniform μ); the caveat lives in the test's module docstring.

**`MAG-13` step-2 lineage — the < 5% wire, measured three ways**
*(profile, re-gate, 2b, 2c, rungs 2–3, diag; full narratives archived in
`docs/planning/plan-archive.md`. `MAG-13` stays ✅ at its recorded numbers
throughout — this lineage extends measurements, it never reopened the
chunk.)*
> * **Rung 2** (2026-08-11): h = 0.00125, 1 097 873 cells, relL2 **5.6494%**
>   — on-rate (1.174) but over the 5% target. **Rung 3** (2026-08-13):
>   h = 0.001127, 1 520 152 cells, **3.7372%** in 420.3 s at `-n 8` — the
>   target reached by brute force; three-rung fitted rate 1.407, not a
>   converged constant. The per-radius "near-wire concentration" pattern
>   did not survive rung 3 (far radii worsened while the total fell —
>   mesh-realization noise, not a spatial map).
> * **Profile step** (2026-08-11/12, re-gated with biting exit codes): the
>   dense 45-radius map — error ∝ 1/r (slope −1.069) *and* a per-cell
>   staircase, both signatures of **cell-wise-constant B** (lowest-order
>   N1curl); local error is O(h/r), which is why the global rate reads ~1.
> * **Step 2b** (2026-08-12): CG1-projected `curl A` reads **1.9557%**
>   where DG1 reads 4.7235% — on the *existing* mesh, for 2.71 s (1% of
>   the solve); the staircase breaks 8/8; the residual is band-flat ≈ 2%.
>   **Step 2c** (2026-08-13): the third rung confirms the recovery rate —
>   CG1 **p = 2.003** / DG1 p = 1.217 — with the honest caveat that
>   pairwise rates spread ±0.20 and the level came in 6.8% below the p = 2
>   extrapolation (floor-approach signature).
> * **Standing decision (weekly review's):** whether `compute_b_field`
>   moves to continuous CG1 recovery — cheap and second-order, but every
>   B-consuming test's recorded number would shift (a re-gating exercise).
>   Graded refinement stays the cheaper *mesh* route on cost alone. The
>   exit gate was bitten live 2026-08-15 (exit 1 at the 12.7485% smoke
>   rung, azimuthality PASS independently). Degree-2 `A` is on record
>   diverging on this fixture — not a free swap.
>   **Decided 2026-08-16 (weekly review): declined for now.** No §10
>   goal is currently limited by B-field accuracy — the wire gate stands
>   at 3.74% on the mesh route — so the re-gating tax (every recorded
>   B-consuming number shifts in one commit) buys nothing today.
>   Revisit when §10 subgoal-4 B1+ work opens: its gates are new, so
>   adopting CG1 recovery there carries no re-gating cost, and the
>   measured case (1.9557% vs 4.7235%, p = 2.003) is already on record.
>   Not an epitaph — the option stays live, the default stays DG1.
> * The two 2026-08-08 "mystery harness deaths" were the
>   **background-and-end-turn trap** (a headless session backgrounding a
>   harness run and ending its turn SIGKILLs the tree) — the reason every
>   scheduled-slot recipe runs harness commands foreground.

**`MAG-18` — sampler-independent straight-wire gate** ✅ *(closed 2026-08-23 03:00 review on the 2026-08-22 logs; commissioned
2026-08-22 18:00 review as the disposal of `OPS-18` step 3 leg 2; §9
item 1 carries the executable rubric.)* **Why it exists.**
`test_straight_wire_b_field` gates a relative L2 over **10 radial sample
points** at the wire midplane against `μ₀I/(2πr)`, band 15% = 1.18× the
12.75% measured in July on the h = 0.0025 mesh. `OPS-18` attempt 5
(`20260822T201014Z_OPS-18-step3-wire-ladder-npoints-072.log`) sampled
the *same solved field* at `n_points` 8 / 10 / 20 on the recording
image and read **15.8028% / 12.7485% / 11.4984%** — a 34% swing of the
statistic under a choice the physics does not see, and the 15% band
**already failing** at `n_points = 8` on 0.7.2. The gate has been passing
on a sampler choice since `MAG-13`. That is a defect of the *statistic*,
not of the solver: the same slot showed the field converging at rate 1.10
(0.7.2) and 1.99 (0.11) in the same sampled norm, so the discretization is
fine and the instrument is not.
> * **What it gates instead.** `E_Ω = ‖|B_h| − |B_ana|‖_{L²(Ω)} /
>   ‖|B_ana|‖_{L²(Ω)}` on the annulus `Ω = {2a ≤ r ≤ 0.8 R_domain, |z| ≤
>   0.25 L}` — the same region the samples span, as a reduced integral
>   with no sample count. `B_h` is the solver's DG0 `compute_b_field`;
>   `B_ana` is `AnalyticalSolutions.straight_wire_magnetic_field`
>   interpolated into the same DG0 space; Ω is a DG0 indicator built from
>   a numpy mask on owned-cell midpoints (not a `ufl.conditional` — the
>   `OPS-22` complex-comparison trap, and the file imports in both builds).
>   Both integrals are `assemble_scalar` + `allreduce(SUM)`.
> * **Done-when (§4), pre-registered before any number is seen:** (i) on
>   the recorded ladder h = 0.004 / 0.0025 / 0.0018 `E_Ω` is monotone
>   decreasing with a log-log rate **≥ 0.7** (the `MAG-17` convention —
>   a DG0 field of an N1curl-degree-1 potential should show ≥ 1, 0.7 is
>   the headroom); (ii) the h = 0.0025 value agrees at `-n 2` and `-n 4`
>   to **1e-10 relative** — the control that the new statistic lacks the
>   old one's defect; (iii) the natural-BC solve reads strictly worse on
>   `E_Ω` at h = 0.0025 — `MAG-13`'s claim restated in the new norm. The
>   h = 0.0025 `E_Ω` becomes a **version-tagged reproduction record**
>   (value, 145 884 cells, `0.7.2 / gmsh 4.11.1`, band 1e-4 relative) and
>   is *not* a physics bound; the rate is the physics bound. The 10-point
>   `rel_error < 0.15` assertion becomes reported-not-gated with the
>   attempt-5 row printed beside `E_Ω` as the negative control (reproduced
>   to 1e-4) — a replacement, not a loosening. §2.1's wire line is
>   amended to quote `E_Ω` and its rate.
> * **Cost:** heavy, `-n 2`, real, `timeout -k 30 600`; the ladder ran
>   98–126 s on 0.7.2 in attempt 4/5, one extra natural-BC solve ~27 s,
>   one `-n 4` command ~28 s — ≤ 250 s of compute. Never `-n 1` at
>   h = 0.0025 (exit 124 at 400 s, attempt 4).
> * **Scope:** `main` / 0.7.2 only; does not touch `OPS-18`, the 0.11
>   image, or the still-open 15.3848% non-monotonicity entry — `MAG-18`
>   may explain it later, it does not claim to now. **Negative result:**
>   rate < 0.7 or non-monotone means the wire gate was never converging
>   in a norm — known-issues entry, §2.1 wire line flagged, `OPS-18`
>   item 4 runs leg 1 only; never fit the band to the result.
> * **Executed 2026-08-22** (log `20260823T003518Z_MAG-18-full.log`,
>   `7 passed` / 270.64 s / `-n 2`, heavy; probes
>   `20260823T003327Z_MAG-18-record-probe.log` `-n 2` and
>   `20260823T003406Z_MAG-18-record-n4.log` `-n 4`, 31 s + 26 s). **(i)
>   holds**: `E_Ω` = 25.3787% / 10.7288% / 6.6708% at
>   h = 0.004 / 0.0025 / 0.0018 (38 750 / 145 884 / 383 248 cells),
>   monotone, fitted rate **1.6842** against the pre-registered 0.7 — the
>   field *was* converging; the instrument was the problem, exactly as the
>   commission read it. **(iii) holds**: at h = 0.0025 the natural-BC wall
>   reads **32.3117%** against the analytic wall's 10.7288%, ratio 0.3320
>   — `MAG-13`'s claim is stronger in the new norm than in the old one
>   (0.63 at h = 0.004 sampled). **(ii) does not hold as written**: `-n 2`
>   1.0728835983e-01 vs `-n 4` 1.0728836764e-01 is **7.28e-08** relative,
>   not 1e-10. The cause is measured, not guessed — `MagnetostaticSolver`
>   solves with `ksp_type=preonly, pc_type=lu`, a direct factorization
>   whose pivot order follows the partition, and the **retired** 10-point
>   statistic moves 1.9e-07 across the same two runs. ~1e-7 is the
>   *solve's* cross-width reproducibility floor, shared by every functional
>   of this field, so the 1e-10 pre-registration was unreachable by
>   construction and says nothing about the sampler defect (ii) was
>   commissioned to exclude. Nothing was loosened in-slot: the test asserts
>   the pre-registered **record** band 1e-4, the deviation is filed to
>   known-issues, and re-registering (ii) at the measured floor is the
>   review's call. The record 1.0728835983e-01 / 145 884 cells /
>   `0.7.2 gmsh 4.11.1` reproduced **bit-identically** across the two
>   `-n 2` runs before it was written into the test. The negative control
>   is asserted, not merely printed: 15.802788 / 12.748522 / 11.498352%
>   at `n_points` 8 / 10 / 20 reproduce the attempt-5 row to ≤ 4.2e-06
>   relative, so the log carries the 34% sampler swing beside the norm
>   that has none. `test_straight_wire_b_field`'s `rel_error < 0.15` is now
>   reported-not-gated with the finding cited at the assertion site.
>   **Chunk stays 🟡** on (ii) alone: `OPS-18` item 4's leg 2 may
>   re-measure `E_Ω` on 0.11 — the gate is on `main`.
> * **(ii) re-registered and the chunk closed ✅ — 2026-08-23 03:00
>   review.** (ii) was commissioned to exclude a *sampler* defect of
>   order 34%; a pre-registration of 1e-10 was below the direct-LU
>   partition-order floor, which the slot measured rather than assumed
>   (7.28e-08 on `E_Ω`, 1.9e-07 on the retired statistic across the same
>   two widths, and the run-to-run floor on one width is ~1e-9 — the
>   2026-08-23 known-issues entry). **(ii) now reads: `-n 2` vs `-n 4`
>   agree to ≤ 1e-6 relative** — 14× above the measured floor, five
>   orders below the defect it excludes; it is satisfied by the logged
>   pair (`20260823T003518Z_MAG-18-full.log:2956` = 1.0728835983e-01 at
>   `-n 2`, `20260823T003406Z_MAG-18-record-n4.log:379` = 1.0728836764e-01
>   at `-n 4`), and the `-n 4` run *asserted* the in-test record band
>   (`test_domain_l2_record`, Status 0, 26 s). §4 audit: harness logs,
>   agent-executed, rate 1.6842 ≥ 0.7 and natural-BC 0.3320 asserted in
>   the test, elapsed recorded. Audited against the §5.4 ramp: the
>   capability — the straight-wire field against `μ₀I/(2πr)` — is already
>   demonstrated by `examples/magnetostatics/01_straight_wire.py` and
>   `06_h_convergence_rate.py`; this chunk changed the *instrument*, not
>   the capability, so no example is owed. §2.1's wire line quotes `E_Ω`.

**`MAG-19` — dispose of the red straight-wire rate gate on 0.11: anomalous
rung, or wrong instrument** 🟡 *(commissioned 2026-08-25 10:30 review from
`EX-30` leg (root)'s finding: `test_convergence.py::TestConvergence::test_h_refinement_straight_wire`
is red on `main` — fitted rate **1.9038** outside the `MAG-13` band
[0.7, 1.5], because the h = 0.0018 rung's sampled error collapsed
9.26% → **4.4605%** on the 0.11 image while the two coarser rungs moved
< 3 pp. Known-issues 2026-08-25. `OPS-26` step 2 will *count* this red; this
chunk is the one that *disposes* of it.)*
> **The two readings, and the pre-stated decision rule.** The gate's own
> docstring already names the mechanism that fits reading (a): the sampled
> 10-point norm reads "whichever cell contains" each sample, so individual
> resolutions carry O(h) sampling noise, and a rate well above 1.5 means one
> resolution is anomalous — precisely why `MAG-13` once excluded h = 0.0035.
> Reading (b) says the instrument, not the rung: `MAG-18` built the
> sampler-independent `E_Ω` annulus norm *because* the 10-point norm swings
> 34% under its own sampler, and the `E_Ω` ladder is green on 0.11 at rate
> 1.6854. These are discriminable by measurement:
> * **Step 1 (standard, `-n 2`, real, one command ~250 s).** Re-run the
>   three-rung ladder **plus one added rung at h = 0.0030** (interpolating
>   38.7 k → 147.2 k cells, ~80 k, ~15 s solve), and on the *same four
>   solves* compute both norms per rung: the sampled 10-point relative L2
>   (the gate's own `solve_h_refinement`) and the `MAG-18` `E_Ω` annulus
>   norm (**import** `test_straight_wire_domain_gate`'s machinery per the
>   `ANS-1` rule; do not restate it). Print the 4×2 error table and all
>   pairwise rates for both norms. **In-run anchor:** the three original
>   rungs reproduce the 08-25 probe digits (21.8417 / 15.3848 / 4.4605%,
>   log `20260825T141636Z`) — the red must be reproduced before it is
>   disposed of. **Decision rule, pre-stated:** if the sampled norm's
>   pairwise rates are consistent (within [0.7, 1.5]) on every pair *not*
>   involving h = 0.0018 while the `E_Ω` pairwise rates are consistent
>   across **all** pairs including it, the h = 0.0018 rung's *sampled*
>   reading is anomalous on 0.11 → **reading (a)**: re-choose the sequence
>   (replace 0.0018 with the finest rung where both instruments' pairwise
>   rates agree — 0.0030 is the candidate this step prices), old sequence
>   kept in-comment with both logs cited, band [0.7, 1.5] **unmoved**. If
>   instead the sampled pairwise rates are scattered outside the band on
>   pairs that do not involve 0.0018, the instrument is unstable at every h
>   → **reading (b)**: the rate duty moves to the `E_Ω` ladder `MAG-18`
>   already gates (which is *executing and green*), and this test keeps its
>   monotone-decay assertion plus the error table as a report — an explicit
>   duty *transfer* to a live tighter gate, recorded as such, never a
>   deletion. If the measurement fits neither branch cleanly, report it,
>   update the known-issues entry, stop — chunk stays 🟡.
> * **Traps already paid for:** the sampled norm's noise is O(h) — do not
>   fit through a rung both instruments disagree on; `mag:6` imports
>   `RESOLUTIONS`/`RATE_MIN`/`RATE_MAX`/the fit from this module (`ANS-1`),
>   so whatever lands here re-gates the example with **zero** example-side
>   edits — run `-e 6` as the consumer check; h = 0.0018 is 383 k cells
>   (~92 s solve on record) — keep the command inside `timeout -k 30 400`.
> * **Scope/negative:** no band moves in any branch ([0.7, 1.5] is either
>   kept or transferred, never widened); the known-issues entry retires
>   only with the commit that lands the disposition green, including
>   `mag:6`. This chunk does not touch `mag:1`'s mesh floor (separate
>   entry, separate ruling).
>
> **Step 1 measured — 2026-08-25, 13:30 slot. Outcome: the pre-stated rule's
> third branch, neither reading, ruling requested.** One command, one solve per
> rung, both norms on the same solved field (`ANS-1`: the sampled norm is the
> gate's own `solve_h_refinement`, `E_Ω` is `test_straight_wire._domain_l2_error`);
> probe `tests/validation/probe_straight_wire_dual_norm.py`, log
> `20260825T183555Z_MAG-19-step1-dualnorm-fits.log`, **160 s** at `-n 2`,
> Status 0. Both in-run anchors reproduce **digit for digit**, so the
> instrument import is right and the measurement is the physics:
>
> | h (m) | cells | sampled 10-pt | `E_Ω` |
> | --- | --- | --- | --- |
> | 0.0040 | 38 740 | 21.841675% | 25.286827% |
> | 0.0030 | 88 018 | 18.473177% | 14.288381% |
> | 0.0025 | 147 235 | 15.384843% | 10.617170% |
> | 0.0018 | 383 146 | 4.460528% | 6.645807% |
>
> *Anchor:* the three original rungs reproduce `20260825T141636Z` to
> ≤ 1.321e-06 relative and the sampled three-rung fit is **1.9038**, the red
> itself. *Negative control:* the `E_Ω` three-rung fit through the imported
> machinery is **1.6854**, the `MAG-18` re-gate value, and the h = 0.0025
> `E_Ω` record reads 1.0617170222e-01 against the recorded 1.0617170000e-01,
> **2.094e-08** relative — the import is not what moved.
>
> **Pairwise rates.** Sampled: 0.5822 / 0.7456 / 1.9894 / 1.0034 / 2.7819 /
> 3.7690. `E_Ω`: 1.9843 / 1.8464 / 1.6735 / 1.6288 / 1.4985 / 1.4261.
> Least-squares fits — original 3 rungs: sampled **1.9038**, `E_Ω` 1.6854;
> all 4: sampled 1.9707, `E_Ω` 1.6661; **without h = 0.0018**: sampled
> **0.7309**, `E_Ω` 1.8588.
>
> **Why neither branch fires, on the rule as written.**
> * Reading **(a)** requires the sampled pairwise rates in band on *every*
>   pair not involving h = 0.0018. They are **2/3**: 0.004→0.003 reads
>   **0.5822**, a second outlier, and it is on the very rung 0.0030 that (a)
>   would promote. So the h = 0.0018 rung is not the *only* anomalous one.
> * Reading **(b)** requires the sampled rates scattered outside the band on
>   pairs avoiding 0.0018 — they are not: 2/3 pairs are in band and the
>   0.0018-free fit is **0.7309**, inside [0.7, 1.5]. The instrument is not
>   unstable at every h.
>
> **What the measurement does settle, and the new constraint it finds.** The
> red is overwhelmingly the h = 0.0018 rung's: all three pairs involving it
> are out of band (1.9894 / 2.7819 / 3.7690) and removing it alone takes the
> fit 1.9038 → 0.7309. But **the duty transfer of branch (b) is not available
> as written**: `E_Ω` is the stable instrument (every pairwise rate in
> [1.4261, 1.9843], every fit in [1.6661, 1.8588], 6/6 pairs above its own
> one-sided ≥ 0.7) yet it sits **above 1.5 everywhere**, so moving the
> two-sided [0.7, 1.5] onto it would be red on arrival. `E_Ω`'s live gate is
> one-sided ≥ 0.7 for exactly this reason. Symmetrically, (a)'s re-chosen
> sequence [0.004, 0.003, 0.0025] fits **0.7309** — 0.03 above the band edge,
> i.e. a gate with essentially no margin, on a statistic already shown to
> swing 34% under its own sampler.
>
> **Options for the ruling** (none taken here; no band moved, nothing
> re-recorded): (i) transfer the rate duty to `E_Ω` under `E_Ω`'s *own*
> one-sided ≥ 0.7 criterion rather than the two-sided band, this test keeping
> monotone decay plus the table as report — the transfer branch (b) intended,
> with the band question named honestly; (ii) accept (a)'s substance and
> re-choose the sequence anyway, acknowledging the 0.7309 margin; (iii) ask
> whether the two-sided band's *upper* edge is meaningful for either
> statistic on 0.11, given both now fit above 1.5 on the full ladder.
> Chunk stays 🟡 pending that ruling; `mag:6` was **not** run as a consumer
> check because no gate changed, and the known-issues entry stays open with
> the 4×2 table added.

**Open follow-ups in MAG:**

- `MAG-15` is a working option, not a finished subsystem: Dirichlet
  conditions on `A` are rejected (`bc_functions` raises — so
  `TimeHarmonicBoundaryCondition.PEC` would not work); the point-pin on `p`
  is not `H¹`-stable in 3D, so use `gauge_multiplier_spread()` rather than
  `max|p|`; it is not wired through `TimeHarmonicSolver` or the port entry
  points; and the degree-2 cost (~7.5× the penalty) is unprofiled against
  MUMPS.
- `J·n ≠ 0` at the straight-wire end caps still stands unmeasured; capping
  the wire short of the end faces was never needed.

### GEO — Geometry & meshing

Independent of the §2.1 physics defect; meshes are meshes.

| ID | Title | Status | Tier |
|---|---|---|---|
| `GEO-1` | Parametric birdcage geometry generator | 🧪 | standard |
| `GEO-2` | Port-face geometry robustness checks | 🧪 | standard |
| `GEO-3` | Phantom placement presets (centered/off-center) | 🧪 | standard |
| `GEO-4` | Air-box and boundary sizing heuristics | 🧪 | smoke |
| `GEO-5` | Region-specific mesh resolution policy | 🧪 | standard |
| `GEO-6` | Geometry sanity report utility | 🧪 | smoke |
| `GEO-7` | Mesh-tag QA diagnostic hardening | 🧪 | standard |
| `GEO-8` | **Make `two_torus_domain` a conforming mesh** | ✅ | standard |
| `GEO-9` | **`coil_phantom_domain` / birdcage meshes do not generate** | ✅ 2026-08-03 — step 1 (coil+phantom gated), step 2a (finalize + `bcast`: 180 s hang → 13 s), step 2b (`occ.fragment` rewrite; both identities 1.000000000000, whole `tests/mesh` green in CI). Retires known-issues 7 | standard |
| `GEO-10` | **`two_torus_domain` never emits its `outer_boundary` facet tag** (known-issues 10) | ✅ *(2026-08-06, 00:00 run; known-issues 10 retired)* | standard |
| `GEO-11` | **Boundary-classification margins under OCC bounding-box padding (CAD-only probe sweep)** | ✅ | smoke |
| `GEO-12` | **Widen the two `1e-9` wall tolerances and gate the `outer_boundary` group** (known-issues 12) | ✅ | standard |
| `GEO-13` | **Decouple `cylindrical_domain`'s wall tolerance from `resolution`** (known-issues 13) | ✅ | standard |
| `GEO-14` | **The shared ~3% geometry floor: faceting vs resolution** (entry lives after `TH-11`, beside the fixtures it measures) | ✅ *(closed 2026-08-15 review on the refuted hypothesis: RESOLUTION, 3.643% → 1.781% at 55 251 cells, rate 1.77 in h — no faceting floor)* | standard |
| `GEO-15` | **Birdcage conductor sizing: is graded sizing a `PORT-9` prerequisite?** (the 0.7091 question; named prerequisite of `PORT-9` step 3) | ✅ 2026-08-16 (graded sizing recovers **0.9670** of the conductor's CAD mass at h_c = 1.6 mm vs **0.7403** baseline, gate cleared, `GEO-9` identities unmoved at < 1e-9; 41 s at `-n 2`; closed by the 10:30 review — the chunk was its one question, now answered by measurement) | standard |
| `GEO-16` | **Emit the gap boxes' longitudinal port-sheet mid-plane in `two_torus_domain`** (the `PORT-9` step-1 mesh prerequisite; commissioned 2026-08-16 18:00 review) | ✅ | standard |
| `GEO-17` | `coil_phantom_domain` region-resolution policy shrinks the coil volumes it refines (−21.68%/−22.62%; `OPS-17` step-2 defect 1, known-issues 2026-08-17; commissioned 2026-08-17 10:30 review) — step 1 ✅ 2026-08-20: the sizes were never applied (`getBoundary` `combined=True` ⇒ 0 points); `Min`-over-`Constant`-fields, coil meshed/CAD 0.7547 → **0.8356** | ✅ *(audited COMPLIANT 2026-08-21 18:00 review — 1e-9 negative-control gate, sign-of-refinement identity and partition 1.000000000000 verified against `20260820T110549Z…final.log`)* | standard |
| `GEO-18` | Birdcage conductor gaps: cut the legs so the port boxes have terminals (`PORT-9` step-3 mesh prerequisite; commissioned 2026-08-20 03:00 review from step 3 legs (a)+(b) 🚫) | ✅ 2026-08-22 (*step 2 audited COMPLIANT 2026-08-22 03:00 review — every figure verbatim in `20260822T020113Z_GEO-18-step2.log:8569-8576`, no pre-existing test touched; one transparency note: the sheets-off control asserts the `110+i` **cell** tags absent, and the `210+i` facet absence the entry and commit claim is implied by that, not measured — `EX-28` is commissioned to assert it directly*; **step 1 ✅ 2026-08-20** — terminals exist: 2.236196e-04 m² per port, **0.988616** of the closed-form `2·π·r_leg²`, all four equal to the printed 7 digits, *audited COMPLIANT 2026-08-21 18:00 review — closed-form band, closure and mass identities verified against all three logs, the pre-derivation red disclosed*; **step 2 ✅ 2026-08-22** — the sheets exist and are exact: meshed sheet area `1.120000000e-04 m²` = the analytic `dx·g` at **1.000000000000** on all four ports, `w_eff = A/h` equal to the bbox extent to 1.000000000000, out-of-plane spread ≤ 2.512e-16 m, half-volumes 0.500000000000 each, C4 sheet spread **8.470e-16**, step 1's terminal band and closure re-asserted on the sheeted mesh) | standard |
| `GEO-19` | `birdcage_port_domain` at `leg_count = 16`, gapped + sheeted: identity family re-gated (C16), cost rung measured — 32-port directive item (a) (commissioned 2026-08-23 weekly review) | ✅ *(**step B ✅ 2026-08-25** — the local-frame port construction is on `main` under ruling (6\*): invariance control `3 passed` from `main` at 116 085 / 114 655 cells, C4 spread 6.050e-16, terminals 0.988616 × 4, no-gap control 98 666 digit for digit; the three `PORT-9` modules `19 passed` **twice in-slot** on the mesh-tagged re-records, σ_max 0.999992805, class separation 166.6766×, (d0) margin 2256.9707×, leg (c)'s `I₁` reproducing to 5.934e-12 against a 1e-9 band. The open-limit (1e6 Ω) column is retired as a record-bearing fixture — no band widened. **Step C attempt 1 2026-08-25**: the rung is measured — 116 085 → **307 296 cells (2.6472×)**, mesh 22.93 → **74.18 s (3.2357×)**, inside the 1 M / 600 s stop rule — and gates (i)/(iii)/(iv)/(v) are green at 16 legs (partition and closure 1.000000000000, C16 sheet spread **1.331e-15**, conductor 0.981503, separation margin 1.560723×) with the 4-leg control reproducing step B's record at delta **0** cells / 6.050e-16. Gate (ii)'s *equality* half is red at **8.434e-04** vs 1e-5 — a three-valued azimuth-class structure with ≤ 2e-7 inside each class, i.e. a C4 band applied to C16; parked on `attempt/GEO-19-stepC-20260825T125000Z`, no band widened, ruling requested. **Ruled 2026-08-25 10:30 review: construction symmetry — per-azimuth-class reading, intra-class 1e-6, inter-class ceiling 5e-3, every existing band unmoved; landing instructions in the prose entry, queued §9 item 1**. **Step C landed 2026-08-25 12:00 slot — chunk ✅**: the ruled module is `2 passed` / **117 s** from `main` (`20260825T170316Z_GEO-19-stepC-ruled.log`; record run `…T170523Z…-ruled-record.log`, 115 s). Gate (ii) per class from the mesh's own coordinate mirrors — three classes, intra **1.923e-07 / 5.849e-08 / 6.144e-08** against 1e-6, inter **8.431e-04** against 5e-3; the 4-leg control returns **one** class at **3.184e-08**, i.e. the reading reduces to the old flat gate. Four already-green gates reproduce (partition/closure/halves/`dx·g` 1.000000000000, C16 sheet spread 1.331e-15, conductor 0.981503, margin 1.560723×) and the control meshes **116 085** cells, delta **0**. **Cost rung: 116 085 → 307 296 cells (2.6472×), mesh 22.99 → 74.37 s (3.2346×)** — Phase 6's first measured rung, on F-small. No band outside the module moved; `GEO-20` step 2 unblocked)* | heavy (probe first) |
| `GEO-20` | High-pass birdcage ring-gap port layout (`ring_gap_length`, `2·leg_count` ports, the `GEO-18` pattern on the end rings) — 32-port directive item (b); step 1 at 4 legs, step 2 at 16 after `GEO-19` (commissioned 2026-08-23 weekly review) | 🟡 *(**step 1 ✅ 2026-08-24** — the 8 ring ports exist at 4 legs and every pre-stated gate is green twice in-slot: terminal **0.974455** of the closed-form `2·π·r_ring²` inside the [0.95, 1.0] inscribed band and equal across the 8 to **≈ 2e-8** (gate 1e-5; digit corrected by the 10:30 review audit — see the prose entry), closure and port-volume **1.000000000000**, sheet meshed/analytic **1.000000000000** with out-of-plane spread **5.042e-18 m**, C4 and top/bottom-mirror spreads below 1e-12, `GEO-9` partition green, conductor 0.969275 ≥ 0.95; negative controls green — kwarg off reproduces the uncut birdcage and the leg+ring mesh is a 12-port mesh with **both** identity families exact. Step 2 (16 legs, 32 ports) is serial on `GEO-19`)* | standard |

> `GEO-4`'s substance is discharged for the two-torus fixture (`air_padding` +
> graded sizing), but it stays 🧪 until its own test executes. **Every other
> fixture in `io/mesh.py` still uses a single global `setSize` and tight padding,
> including coil+phantom** — expect the same boundary-mirror error that cost 20%
> on Helmholtz, and expect graded sizing to be equally necessary.

**`GEO-4` step 1 — off-centre domain sizing (known-issues 5)** ✅
*(2026-08-06; full diagnosis in `docs/planning/plan-archive.md`)*. The
oldest standing failure on `main` was the test's own assertion: the
`radial_clearance` guard means the coil always governs the box, so "an
offset phantom grows the box" is false for every meshable configuration.
The test now gates the containment identity with the clearance term
explicit plus the exact identity `clearance(centered) − clearance(shifted)
= 0.03 m`; the `OPS-11` `--deselect` is gone and `tests/mesh` runs
unexcluded in CI. Handed to a review: the overlap guard is z-blind. `GEO-4`
itself stays 🧪 (graded-sizing generalization is separate work).

**`GEO-10` — `outer_boundary` facet tag never emitted (known-issues 10)** ✅
*(2026-08-06; full narrative in `docs/planning/plan-archive.md`)*. Cause:
gmsh inflates OCC bounding boxes by the geometric tolerance (measured
1.000e-07) and the flat-against-wall test used `tol = 1e-9` — every wall
failed and the physical group was silently skipped. Fix: `1e-9 → 1e-6`.
Gate: tag sets exactly `{1}` / `{1, 201, 202}`, tagged area = analytic box
surface at ratio 1.000000000000000 (an identity — planar walls); neither
Helmholtz consumer depends on tag `1` (digit-identical regression).

**`GEO-8` — make `two_torus_domain` a conforming mesh** ✅ *(2026-08-01;
full narrative archived in `docs/planning/plan-archive.md`)*
> The fixture never fragmented — three disconnected components, `PORT-1`'s
> `Z₁₂ ≡ 0`. Fixed with `occ.fragment` + centroid/mass re-derivation of the
> physical groups (**fragment renumbers — never trust its returned tag
> order**). Mesh volume / analytic box 1.002633 → 1.000000000; Helmholtz
> centre-field error 1.731% → 0.728%. Measurement worth keeping: at uniform
> `resolution=0.01` a meshed torus retains only 0.598 of its analytic
> volume — **the wire needs `wire_resolution ≲ 0.4·minor_radius`** before
> any volume-based conformity statement means anything.

**`GEO-9` — `coil_phantom_domain` / birdcage meshes do not generate** ✅
*(steps 1, 2a, 2b ✅ 2026-08-03; known-issues 7 retired; full diagnosis in
`docs/planning/plan-archive.md`)*
> Two independent defects, neither the guessed one: `coil_phantom_domain`
> was innocent; the **birdcage** raised without reaching `gmsh.finalize()`,
> poisoning later meshes and hanging rank 1 at a skipped collective. Fixes:
> rank-0 body isolated with the failure `bcast` to every rank (180 s hang →
> 13 s prompt failure — the isolation gate's no-hang `allreduce` assertion
> degenerates at `-n 1`, never move it to a single-rank job); one
> `occ.fragment` against all tools with every group re-derived from the
> out-map. Both volume identities 1.000000000000, all four port boxes
> exact, conductor 0.7091 banded — that number is exactly what `GEO-4`'s
> open half (the birdcage's single global `setSize`) measures. The mesh is
> 8.95 s, not the known-issues "~10 minutes" (that was the hang).

**`GEO-11` — boundary-classification margins under OCC padding** ✅
*(2026-08-06; full sweep narrative in `docs/planning/plan-archive.md`)*.
CAD-only two-sided margin gate over four fixtures
(`test_boundary_classification_margins.py`): found `GEO-10`'s exact defect
live in `loop_over_half_space_domain` (0/12 walls accepted) and
`sphere_in_box_domain` (0/7) — became known-issues 12 → `GEO-12`; and
`cylindrical_domain` under-separated at 4.50× — known-issues 13 →
`GEO-13`. Not covered, deliberately: `coil_phantom_domain` /
`birdcage_port_domain` (their CAD stages would have to be factored out of
the generators first — a review's call).

**`GEO-12` — widen the two `1e-9` wall tolerances** ✅ *(2026-08-06;
known-issues 12 retired; full narrative in
`docs/planning/plan-archive.md`)*. Both tolerances → `1e-6`; accepted
counts land exactly on each fixture's wall count; meshed facet-tag gate
(`test_wall_boundary_tag_areas.py`) asserts the analytic cube-surface area
at 1e-9. All six discarding callers re-run: no landed number moved a
digit.

**`GEO-13` — decouple `cylindrical_domain`'s wall tolerance from
`resolution`** ✅ *(2026-08-07; known-issues 13 retired; full narrative in
`docs/planning/plan-archive.md`)*. Tolerance is now
`0.01 × (outer_radius − inner_radius)` — chosen from a sweep window
`[1e-4, 0.05]` measured on all four repo call sites; classification
unchanged (3 of 6 surfaces), margins now 1.1e-04× / 1.0e+02×. All four
fixtures in the margins file assert live (the `GEO-11` sweep closes). New
precondition at the use site: a radial gap below ~1e-4 m stops clearing
the OCC padding by 10× (smallest gap in the repo: 0.07 m).

**`GEO-15` — birdcage conductor sizing: is graded sizing a `PORT-9`
prerequisite?** ✅ 2026-08-16 *(entry written 2026-08-16, 03:00 daily
review; step 1 executed by the 07:30 implementer run; **closed by the
10:30 review** — the chunk was scoped as a single measured question and
step 1 answered it (audited §4-COMPLIANT: pre-stated ≥ 0.95 gate, logs,
elapsed recorded). The implementer left the flip to the review; the
remaining 3.3% is curvature faceting, not a mesh-size failure, and pinning
it down buys `PORT-9` nothing. One latent hazard the audit found — a
rank-local `perf_counter` budget break in the ladder test that could
desync collectives if it ever fires — is recorded in known-issues, not
here. Mesh-only: no solves.)* The birdcage mesh (`GEO-9`) keeps only **0.7091** of the
conductor's analytic volume under the single global `setSize = 0.015` —
part is the analytic sum double-counting the 8 leg∩ring junctions (CAD
masses give 0.9578), the rest is 0.015 against a 0.004 ring minor radius.
`GEO-8`'s measured rule (`wire_resolution ≲ 0.4·minor_radius`, i.e.
≲ 0.0016 here) says the conductor is ~10× under-resolved, and a lumped
port on that surface inherits the coarse conductor boundary. This chunk
answers `PORT-9` step 3's open question by measurement.
> * **Step 1 ✅ 2026-08-16** — gate **0.967019 ≥ 0.95** of CAD mass at
>   h_c = 1.6e-3 (98 474 cells, 16.74 s; baseline global-`setSize`
>   0.740335 at 48 245 cells / 6.07 s; negative-control separation
>   0.2267); the junction double-count is **4.22%** (CAD 1.030097043e-04
>   vs analytic 1.075503356e-04 m³); `GEO-9` identities unmoved < 1e-9 on
>   every rung. Logs `20260816T123337Z_GEO-15-step1.log` (1 passed, 41 s,
>   `-n 2`) + `20260816T123433Z_GEO-15-step1-regression.log` (4 passed,
>   21 s). **Live carry-forwards:** new `birdcage_port_domain` kwargs
>   `conductor_resolution` / `conductor_refine_distance` /
>   `return_diagnostics`, all defaults unchanged; the working mechanism
>   is a Distance→Threshold field over the conductor surfaces — the
>   three `Mesh.MeshSizeFrom*` switches must be off or gmsh re-imposes
>   the coarse size; `PORT-9` may assume graded sizing and budgets from
>   98 k cells; the residual 3.3% is curvature faceting; `GEO-4` stays 🧪
>   (no solve ran). Full narrative + original plan:
>   `docs/planning/plan-archive.md`, archived 2026-08-16.

**`GEO-16` — emit the gap boxes' longitudinal port-sheet mid-plane in
`two_torus_domain`** ✅ *(closed 2026-08-17; commissioned 2026-08-16 18:00 review as the mesh prerequisite `PORT-9` step 1 named.)*
> **Result ✅ 2026-08-17** (`tests/mesh/test_two_torus_port_sheet.py`, `20260817T003627Z_GEO-16-regression.log`, 5 passed, 47.3 s at `-n 2`, standard). Opt-in `emit_port_sheet=False` (default) fragments each gap box on its mid-plane `z = ±separation/2` (dim-2 tool to the existing `occ.fragment`), halves carried as cell tags `101`/`111`, `102`/`112` by centroid z; sheet facet tags `211`/`212` rebuilt dolfinx-side via `_interface_facet_tags` (now accepts a sequence of cell-tag pairs; no dim-2 gmsh group, known-issues 9).
> **Anchor met:** MPI-reduced `dS` area per sheet **9.573030358733e-05 m²** vs CAD mid-plane **9.573030358733e-05 m²**, `meshed/CAD = 1.000000000000` (band 1e-9); 84 owned facets per sheet, asserted non-empty before the identity; out-of-plane spread 3.5e-18 m; sheets agree < 1e-12.
> **Measured extents (printed, never gated — what `PORT-9` step 1 must use instead of nominal dimensions):** `w = 1.200000000e-02 m`, `h = 7.977525299e-03 m`, `w/h = 1.504225878` squares, `area/(w·h) = 1.000000000` (CAD bbox `w/h = 1.504206917`, 5th-digit difference from gmsh's 1e-7 bbox inflation, `GEO-10`).
> **Negative controls held:** kwarg off — 79 534 cells, tag sets `{1,2,3,101,102}` / `{1,201,202}`, no `21x` group; 3b-iv gate reproduces `meshed/analytic = 0.974490841` bit-identical to the 2026-08-05 record. Fragmented-mesh port areas 1.563786482e-04 m² per port (same 0.9745 of analytic).
> **Carry-forward:** a caller selecting the gap volume by tag must take **both** halves of each box when the kwarg is on (`PORT-9` step 1).
> Full narrative: `docs/planning/plan-archive.md`, entry «§7 GEO-16 full narrative — archived 2026-08-23 (weekly review)».

**`GEO-17` — `coil_phantom_domain`'s region-resolution policy shrinks the
coil volumes it refines** ⬜ *(commissioned 2026-08-17 10:30 review from
`OPS-17` step-2 defect 1 — full measurement in known-issues "Four defects…"
§1; the failing gate is carried as
`tests/mesh/test_mesh_tag_integrity.py::test_region_resolution_policy_does_not_move_the_tagged_volumes`,
`xfail(strict=True)`.)* Asking for a *finer* coil size (0.012 vs uniform
0.015) loses **−21.68% / −22.62%** of the meshed coil volumes (CAD recovery
75.5% → 59.1%) — a sign an inscribing linear-tet mesh cannot produce by
refinement, so the size request is not reaching the coil surfaces.
Known-issues hypothesis: the region size fields **replace** rather than
take the min of the surface sizing on shared curved interfaces, so the
coarse air field (0.020) wins on the coil and phantom boundaries. This
fixture is `MAT-4`'s road to SAR-on-a-coil, so its fidelity is mission
path, not polish.
> **Step 1 — confirm the mechanism and fix the sizing path (standard, one
> run).** Read `coil_phantom_domain`'s size-field construction; if the
> hypothesis holds, the fix is composing the fields with `Min` (or setting
> `Mesh.MeshSizeExtendFromBoundary`-equivalent per-region floors) so a
> region's requested size *bounds* the interface sizing. **Anchor (§4):**
> the carried xfail flips to **XPASS → un-mark it**: policy-mesh coil
> volumes ≥ uniform-mesh volumes (the sign-of-refinement identity, the
> defect's own gate), and meshed/CAD coil recovery printed at both sizings
> (expect ≥ 75.5% under the policy; print, gate only the sign). Both
> meshes must still partition their own volume to 1e-9 (the conformity
> gate that already passes — it must not move). **Negative control:** the
> uniform mesh's four tagged volumes reproduce their recorded table
> (known-issues §1) to 1e-9 — the fix may not move the uniform path.
> **Tier/cost:** standard, `-n 2`; the two meshes cost 15 s in step 2's
> leg (`20260817T111054Z`), budget `timeout -k 30 400`. **Traps:** gmsh
> size fields are global state — clear between builds; `cell_tags.values`
> is rank-local, reduce before summing volumes; do not "fix" by coarsening
> the air. **Scope:** `coil_phantom_domain` only; no solver claim, no
> `MAT-4` status change. **Negative result:** if the mechanism is *not*
> the field composition, the diagnosis (which field owns each interface,
> printed per surface) is the deliverable — record it in this entry and
> known-issues, report, stop.
> **Step 1 executed 2026-08-20, 06:00 slot — ✅, and the hypothesis is
> refuted.** The size fields were not competing on the interface; there were
> no size fields. `coil_phantom_domain` collected each region's CAD points by
> walking volume → surfaces → curves → points with `gmsh.model.getBoundary`'s
> **default `combined=True`**, and the boundary of a volume's *combined*
> closed shell is empty — so all four regions collected **0 points**,
> `mesh.setSize` was never called once, and the only surviving sizing
> authority was the `CharacteristicLengthMin/Max` clamps (uniform
> `[0.015, 0.015]`, policy `[0.010, 0.020]`). The policy run therefore meshed
> the coil at the **air's** 0.020 ceiling, which is the whole −22%. Measured
> diagnosis: `20260820T110127Z_GEO-17-step1-diag.log`, `air: 0 pts -> NO SIZE
> SET` for every region at both sizings. **Fix:** the per-region sizes are now
> a `Min` over four per-volume `Constant` fields (`VolumesList` +
> `IncludeBoundary=1`, `VOut = 1e22`) set as the background mesh, so a
> region's request bounds the size on its own boundary and a shared curved
> interface takes the finer of its two neighbours. **Measured** (`-n 2`,
> 13 s, `20260820T110549Z_GEO-17-step1-final.log`), uniform h = 0.015 against
> coil 0.012 / phantom 0.010 / air 0.020: coil_1 **+10.7169%**
> (1.191750413e-04 → 1.319468693e-04 m³, meshed/CAD 0.754685 → **0.835563**),
> coil_2 **+10.7851%** (0.752565 → 0.833730), phantom **+0.9374%** (0.983531 →
> 0.992751), air **−0.2643%** — the air is the one region the policy coarsens
> and the one region that loses volume. Both meshes still partition their own
> volume at ratio **1.000000000000**. **Negative control passed:** the uniform
> column reproduces the `OPS-17` record to every printed digit (gated at
> 1e-9 in the test), so the fix does not touch a mesh that asks for one size
> everywhere; a probe that additionally forced
> `MeshSizeExtendFromBoundary/FromPoints/FromCurvature` to 0 **did** move it
> (coil_1 −3.12%) and was reverted — the two logs are
> `20260820T110302Z_GEO-17-step1-fieldfix.log` (forced off) and
> `20260820T110407Z_GEO-17-step1-probe-defaults.log` (defaults, kept), and the
> comparison is recorded in the source comment. **One band replaced with its
> measurement** (§4 precedent `MAG-10`/`MAG-15`): the carried strict xfail's
> 5% band asserted that region sizing "must not move the geometry", which is
> false for a curved region — an inscribing linear-tet mesh's CAD recovery
> *grows* with refinement, so a real 0.015 → 0.012 refinement of a torus of
> minor radius 0.01 must move the volume, and by more than 5% (+10.72%
> measured). The test (renamed
> `test_region_resolution_policy_refines_the_tagged_volumes_toward_cad`) now
> gates the identity this step pre-registered — policy volume > uniform volume
> for every refined tag — plus meshed/CAD ≤ 1.0 for both sizings (the
> inscription bound) and policy coil recovery ≥ the pre-stated 0.755. Nothing
> was loosened: the old band would now *reject* a correct mesh. **Scope
> kept:** `coil_phantom_domain` only, no solver claim, no `MAT-4` status
> change. The chunk closes — known-issues "Four defects" §1 is marked
> resolved.

**`GEO-18` — birdcage conductor gaps: cut the legs so the port boxes have
terminals** ✅ *(both steps closed — step 1 2026-08-20, step 2 2026-08-22; commissioned 2026-08-20 03:00 review from `PORT-9` step 3 legs (a)+(b) 🚫. Review decision: cut the legs, not the end rings — drive direction `ẑ` for every port, square section `dx = dy` makes the four-port layout C4-invariant by construction; port azimuths move from 45° + k·90° to the leg positions k·90° in the gapped variant, a deliberate low-pass-birdcage physics change.)*
> * **Step 1 ✅ 2026-08-20** (`leg_gap_length` opt-in, default `None` bit-for-bit; `_birdcage_leg_gap_layout` helper). `g = 8 mm`, box `(1.400000e-02, 1.400000e-02, 8.000000e-03)` m, `h_c = 1.6e-3`. Per port: terminal area **2.236196e-04 m²** = **0.988616** of `2·π·r_leg² = 2.261947e-04 m²` (band [0.95, 1.0]), equal on all four ports to 7 digits; closure `(A_cond + A_air + A_phan)/A_box = 1.000000000000`; phantom-facing 0; gap volume meshed/analytic **1.000000000000**; `GEO-9` partition identities < 1e-9; gapped meshed/CAD conductor **0.970152** (≥ 0.95); **114 846** cells, mesh 22.61 s, rung 24.32 s. Mass identity re-derived off a cancellation (§4 `MAG-10`/`MAG-15` precedent): `CAD_gapped/(CAD_uncut − 4·π·r_leg²·g)` = **1.000000000192** (1e-9), the difference form read 0.999999994733. Negative control: kwarg off reproduces **98 474** cells, `EX-21` 0.967019, conductor-facing `0.000000e+00 m²` on all four ports. Logs `20260820T093433Z_GEO-18-step1.log`, `20260820T093603Z_GEO-18-step1-final.log` (8 passed, 136.61 s), `20260820T093830Z_GEO-18-step1-record.log` (1 passed, 45.16 s), all `-n 2`. `tests/mesh/test_birdcage_port_terminals.py` kept as the standing guard on the default geometry.
> * **Step 2 ✅ 2026-08-22** (`emit_port_sheets` opt-in, `ValueError` without `leg_gap_length`; attempt 1 parked on `attempt/GEO-18-step2-20260822T004500Z`, exit 124 from an `allreduce` inside `if comm.rank == 0`, log `20260822T003614Z_GEO-18-step2.log`; fix hoisted the collective). Per port (`20260822T020113Z_GEO-18-step2.log`, 2 passed, 53 s, `-n 2`): sheet **54 facets, 1.120000000e-04 m²**, meshed/analytic `dx·g` = **1.000000000000** (1e-9); `h = 8.000000000e-03 m`, `w_eff = A/h = 1.400000000e-02 m`, `w_eff/w_bbox = 1.000000000000`; out-of-plane spread **2.512e-16 / 9.714e-17 m** (band 1e-12); half-volumes **0.500000000000 / 0.500000000000**; step-1 gates survive (terminal ratio 0.988616, closure 1.000000000000, partition < 1e-9); C4 sheet spread **8.470e-16**. Sheeted mesh **116 416** cells (mesh 22.73 s, rung 24.77 s); cell tags `100+i`/`110+i`, sheet facet tags `210+i`. Negative control: sheets off reproduces step 1 exactly (114 846 cells, 0.988616, tags `[1, 2, 3, 101, 102, 103, 104]`, every `110+i`/`210+i` absent). Regression: birdcage mesh suite 10 passed, 186 s (`20260822T020224Z_GEO-18-step2-regression.log`).
> **Carry-forward:** `PORT-9` step 3's mesh prerequisite is discharged — the birdcage has terminals and a port sheet per port; step 3 re-runs unchanged (gates (i)–(iii) never moved). A gapped birdcage without lumped elements still cannot resonate — no port model, solve, impedance or resonance claim here. Ramp example `EX-28` ✅ 2026-08-23.
> Full narrative: `docs/planning/plan-archive.md`, entry «§7 GEO-18 full narrative — archived 2026-08-23 (weekly review)».

**`GEO-19` — `birdcage_port_domain` at `leg_count = 16`, gapped and
sheeted: the identity family re-gated and the cost rung measured** ✅
*(closed 2026-08-25, 12:00 implementer slot — step C landed under the
10:30 review's construction-symmetry ruling; the closing measurement is at
the end of this entry. Commissioned 2026-08-23 weekly review — item (a) of the operator's
2026-08-17 32-port directive, §10 Phase 6. Mesh only, CAD-identity gates,
no solve — so it does not wait on any physics gate and may be queued
whenever the daily review has a free slot. Heavy tier, `-n 2`,
cost-probe-first: nothing above `leg_count = 4` has ever been meshed.)*
**Do:** generate the `GEO-18` step-2 fixture (`leg_gap_length = 8e-3`,
`emit_port_sheets = True`, `conductor_resolution = 1.6e-3`) at `leg_count
= 16`; print cells, mesh wall, and per-port sheet/terminal diagnostics.
**Gate (§4), pre-stated:** (i) `GEO-9` tagged-volume partition < 1e-9;
(ii) every one of the 16 terminals inside [0.95, 1.0] of `2·π·r_leg²` and
equal across ports to 1e-5 (`GEO-18` step 1's record band); (iii) every
sheet meshed/analytic `dx·g` = 1 to 1e-9, **C16** sheet-area spread
< 1e-12; (iv) conductor meshed/CAD ≥ 0.95 at the graded sizing; (v) the
layout diagnostics' minimum port-centre separation ≥ the generator's
`min_port_center_separation` (legs at 22.5° pitch on `ring_radius = 0.07`
are 27.4 mm apart — the 14 mm boxes must not touch; if they do, the
finding is that the production geometry needs a larger ring or narrower
boxes, recorded, not worked around). **Negative control:** `leg_count = 4`
in the same run reproduces the step-2 record (116 416 cells, 0.988616,
8.470e-16) bit-identically. **Stop rule:** if the probe exceeds 1 M cells
or 600 s of mesh time, record the count and the scaling from 4 → 16 and
stop — that number *is* the deliverable for Phase 6's pricing, and the
next item is a sizing chunk. **Done-when:** gates (i)–(v) executed at 16
legs with cell count, mesh time and `-n 2` elapsed recorded; §10 Phase 6
gets its first measured cost.

**Attempt 1, 2026-08-23 16:30 slot — 🟡 not the gates, but two blockers
measured and the first one cleared. The fixture cannot be built at 16
legs, for a reason no gate would have caught.**

*Blocker A (cleared this slot).* The port halves were encoded as cell tags
`100+i` and `110+i`, which **collide for `i >= 11`**, so
`_build_birdcage_port_model` refused `emit_port_sheets` above **nine** legs
outright (`mesh.py:3133`, "leg_count must be <= 9"). The chunk as
commissioned was unexecutable on its first line. Fixed by widening the
upper base to **`200+i`**; the lower tags are untouched, so no existing tag
*value* moved. **Verified inert**, which is the whole claim: the `GEO-18`
step-2 + step-1 modules are `3 passed` / exit 0 / 93 s
(`20260823T213647Z_GEO-19-tagfix-regression.log`) with **116 368 cells,
C4 sheet spread 6.050e-16, terminal ratios 0.988616 × 4 — identical
digit for digit** to the same modules run *before* the change in the same
slot (`20260823T213127Z_GEO-19-probe4.log`, `2 passed` / 59 s). The
encoding ceiling is now 99 legs.

*Blocker B (open — this is what `GEO-19` actually needs).* With A cleared,
the 16-leg build reaches the sheet construction and raises
`NotImplementedError: emit_port_sheets builds axis-aligned rectangles, so
every leg must sit on a coordinate axis; port P2 is at 22.500 degrees`
(`mesh.py:3189`, `20260823T213546Z_GEO-19-step1.log`). The mid-plane sheet
is built as an axis-aligned dim-2 tool, which is only *possible* for
`leg_count <= 4`. **Sixteen legs need the sheet built in each leg's own
local frame** — the rectangle rotated into `(r̂, ẑ)` at the leg's azimuth,
with the half-assignment centroid test taken along the leg's radial
normal instead of along x or y. That is a geometry change to
`_build_birdcage_port_model`, not a knob, and it is the whole of the next
attempt. Note the kinship with `PORT-9` leg (d1)'s standing warning that
"two-torus sheets are coordinate-axis": this is the same limitation, met
from the mesh side.

*Measured anyway — a finding for the 32-port directive itself, ahead of
gate (v).* The gapped layout's clearance floor is `1.25·box_width` =
**1.750000e-02 m** against a leg pitch of `2·ring_radius·sin(π/N)`. At
`N = 16` that is 2.731e-02 m and passes with 1.56× margin, as the weekly
review predicted. At **`N = 32` it is 1.366e-02 m and fails** — the
generator rejects the layout before meshing (measured at `N = 100`:
4.397506e-03 m vs the same floor, `20260823T213546Z_GEO-19-step1.log`).
The closed-form ceiling on `ring_radius = 0.07` with 14 mm boxes is
**`N ≤ 25`**. So the directive's production count does **not** fit the
production geometry: 32 legs need a larger ring (≥ 0.0876 m at this box),
narrower boxes, or a lowered floor — recorded as the geometry's finding,
not worked around, exactly as gate (v) instructed. **The `GEO-20` ring-gap
layout is unaffected** (its ports sit at the inter-leg mid-azimuths on the
rings, a different pitch), so item (b) is not blocked by this.

*Parked:* `attempt/GEO-19-20260823T214500Z` carries
`tests/mesh/test_birdcage_port_scaleup.py` — the gates (i)–(v) module
written and executing, ready to run the moment blocker B is cleared. Its
4-leg control records are already version-tagged to 0.11. `main` carries
only the cleared blocker A and its regression log.

**Rescoped 2026-08-23 18:00 review — blocker B is its own step, not a
rider on the gates.** The chunk now runs as two implementer items:
*Step B* (§9 item 3) — the geometry rewrite at the raise site: build the
`(w, g)` sheet rectangle at azimuth 0 and rotate it by the leg azimuth
about `ẑ` before the OCC fragment; replace the Cartesian half-assignment
(`mesh.py:3270-3278`) with the signed projection of the cell centroid
onto the leg's radial normal `(cos θ, sin θ)`. Its gate is *invariance*:
at the four axis azimuths the rotation is the identity, so the `GEO-18`
modules must reproduce the 0.11 record digit for digit (116 368 cells,
0.988616 × 4, C4 spread 6.050e-16 —
`20260823T213647Z_GEO-19-tagfix-regression.log`); prediction from
attempt 1: the identity family holds at 16 too, because the sheet is
still a planar rectangle meshed by a conforming fragment, so `dx·g`
stays exact. *Step C* (§9 item 5) — land the parked module and run gates
(i)–(v) at 16 legs with the entry's stop rule binding. The negative
control's record digits are the **0.11** values above, not the table's
original 0.7.2 digits (116 416 / 8.470e-16), which stand as
version-tagged history. The `N ≤ 25` layout ceiling is recorded above
and flagged to the weekly review for §10 Phase 6; it gates nothing here.

**Step B attempt 1, 2026-08-24 03:30Z slot — 🟡 the rewrite is written,
green twice in-slot, and parked on
`attempt/GEO-19-stepB-20260824T034500Z` (`12737a8`). It is not a defect
in the rewrite that stopped it; it is what the rewrite does to
`PORT-9`'s recorded digits.**

*What was built.* The `NotImplementedError` is gone. Both the gap box and
its mid-plane rectangle are constructed at azimuth 0 and taken to the
leg's azimuth by **one** transform about `ẑ`; the half-assignment is the
signed projection of the piece centroid on the plane's own normal
`φ̂ = (−sin θ, cos θ)`. Two things the rescope did not name turned out to
be forced. (1) **The box has to rotate with the sheet.** A rotated
rectangle of width `dx` spans an *axis-aligned* square section only at
multiples of 90°; anywhere else the sheet is shorter than the chord, the
fragment leaves the box one piece, and there are no port halves at all —
so the sheet alone would not have built at 16 legs either. In gap mode
the section is a square (`dx = dy = box_width`), so the rotation is
exact-onto at the four axis azimuths. (2) **`occ.rotate` is not exact
there.** It applies `cos(π/2) = 6.1e-17`, moving vertices a few ulps, so
the transforms go through `occ.affineTransform` with a matrix whose
entries are snapped to 0/±1 (`_z_rotation_affine`) — at 0/90/180/270 an
exact identity or coordinate swap.

*The invariance control, twice in-slot.* `3 passed` / Status 0, 90.08 s
and 88.97 s (`20260824T033811Z_GEO-19-stepB-snapped-run1.log`,
`20260824T033956Z_…-run2.log`), bit-identical to each other. Of the
three record digits: terminal ratios **0.988616 × 4 ✓**, C4 sheet spread
**6.050e-16 ✓** (exactly), cell count **116 085 vs 116 368 ✗** (−0.24%;
gapped 114 655 vs 114 855, −0.17%). Every analytic identity is exact
(sheet area / `dx·g` = 1.000000000000, halves 0.500000000000, closure
1.000000000000) and the **CAD is digit-identical** to the record —
masses, sheet areas, sheet CAD extents, fragment volume counts, grading
surface counts all reproduce. Out-of-plane sheet spread *improves*,
2.5e-16 → 1.8e-18 m.

*Why the count moved, measured rather than asserted.* Three geometries
differing by ≤ 5 ulps give three cell counts: the old construction
116 368, an unsnapped `occ.rotate` rewrite **116 437**
(`20260824T033344Z_GEO-19-stepB-run1.log`), the snapped one 116 085.
The old code's own `cx = ring_radius·cos(π/2)` is **4.286263797e-18**,
not 0 — so the pre-change boxes at 90/180/270° sat ~5 ulps off their
exact positions, and *no* correct local-frame construction can reproduce
that. gmsh's tie-breaking amplifies ulp-level input into ~1e-3 relative
cell count. Controls: both runs reproduce each other exactly, and the
untouched no-gap path reproduces **98 666** cells digit for digit across
all four logs. **So "cell count digit for digit" is not a property this
gate can have; the gate's intent — no geometry drift — is met, and the
review is asked to rule on the digit rather than the implementer
loosening it.**

*What actually blocks the landing.* On the moved fixture three `PORT-9`
birdcage assertions go red — `3 failed, 16 passed` / 124.68 s,
`20260824T034214Z_GEO-19-stepB-port9-regression.log`: leg (c)'s open
driven current deviates **1.376e-03** from record, leg (d0)'s `Z_11`
**1.840e-02** against a 1e-9 print band, and leg (c)'s class-degeneracy
gate **flips** — `|Z31|` sits 0.0321% from the adjacent pair's mean
against that pair's own 0.0407% spread, i.e. the opposite port is no
longer separated from the adjacent class. The first two are re-records
and belong to §9 item 4's licence, not to a mesh chunk. The third is not
a re-record: it is a gate changing sense, on a fixture whose C4/degeneracy
structure `PORT-9` legs (c)/(d0)/(d) are built on. Landing step B would
leave `main` red, so it is parked. **Next attempt:** a review ruling that
sequences step B against `PORT-9` — either step B lands together with the
birdcage re-record (making item 4 a two-cause measurement, which is why it
was not done here), or `PORT-9`'s birdcage records are pinned to a mesh
the geometry rewrite does not touch.

**Adjudicated 2026-08-24 03:00 review — ruling (4\*), full text in §9.**
The rewrite is correct and the cell-count digit-for-digit expectation is
ruled unsatisfiable (the old construction's own `ring_radius·cos(π/2)` =
4.286e-18 puts its boxes ~5 ulps off exact, which no correct local-frame
construction reproduces; the gate's intent — no geometry drift — is met by
the digit-identical CAD and exact analytic identities). The
pin-to-another-fixture option is rejected — the gapped birdcage *is* the
fixture. Sequencing: `PORT-9` leg (d3b) re-records the birdcage class on
the **unmoved** mesh first (§9 item 1, single cause: route), then step B
lands with a mesh-tagged (1\*) re-record of the same records (§9 item 2),
so each re-record has one cause. The flipped class-degeneracy gate's
disposition is pre-registered in item 2: measure the full `|Z_i1|` class
structure on the new mesh against item 1's baseline; keep the gate if the
separation is restored, else replace the ordering assertion with recorded
class means/spreads and file the thin-separation finding to known-issues,
flagged to the weekly review for §10 Phase 6.

**Step B attempt 2, 2026-08-24 18:30Z slot — 🟡 the merge is clean and the
invariance control is green *from `main`'s tree*, but the landing is parked a
second time on a third red the ruling did not predict: the open-limit column is
not mesh-converged.** Parked on
`attempt/GEO-19-stepB-20260824T183000Z` (`6c1f54e`).

*The merge.* `12737a8` cherry-picked onto post-`GEO-20` `main`; one conflict, at
the `sheet_of_ordinal` type annotation — `main`'s leg encoding was still the old
`(axis, coordinate)` pair while `GEO-20` had added a parallel
`ring_sheet_of_ordinal` keyed by `(normal, point)`. Resolved to step B's
`(normal, point)` for the legs, keeping `GEO-20`'s ring dict and its
`n_ports_total <= 99` check, so both port families now use the same
C_N-covariant encoding — which is what `GEO-20`'s own comment asked for.

*(a) The invariance control, from `main`.* `3 passed` / Status 0 / **96 s**
(`20260824T183257Z_GEO-19-stepB-invariance.log`). Cell counts **116 085**
sheeted / **114 655** gapped, exactly the attempt's prediction; C4 sheet spread
**6.050e-16**; terminal ratios **0.988616 × 4**; sheet meshed/analytic, halves
and closure all `1.000000000000`; out-of-plane spread ≤ 7.103e-18 m. The
negative control the item named — the untouched no-gap path — reproduces
**98 666** cells digit for digit. Nothing here is a finding; the rewrite
survives the merge intact.

*(b)+(c) The `PORT-9` regression, and the disposition.* `3 failed, 16 passed`
/ 117.80 s (`20260824T183519Z_GEO-19-stepB-port9-measure.log`). Two of the three
are the re-records item 2 licensed, and both are in hand, mesh-tagged against
item 1's (d3c) baselines: leg (c)'s driven current
`+9.990584892e-07+4.709566544e-09j A` (moves **1.381e-03**) and leg (d0)'s
terminated `Z₁₁` `+2.215494591e+01+7.460189773e+00j Ω` (moves **1.852e-02**;
full column in `6c1f54e`). The pre-registered (4\*)(iii) disposition resolves
**against keeping the gate**: leg (c)'s magnitude-only margin goes 5.0594× →
**0.7906×** and its complex form 6.9398× → 1.5951×, so the separation is not
restored — it was already below leg (d0)'s 10× floor before step B.

*The third red, which is why this is parked rather than landed.* On the same
open (1e6 Ω) fixture, `Z₁₁` moves **~40%** — `+7.111692404e+02 −
3.351665665e+03j` → `+9.201557829e+02 − 4.718342449e+03j`, `|Z₁₁|` 3.42e+03 →
4.81e+03 Ω — under a **0.24%** cell-count change, while the three mutuals move
0.3% and the *terminated* column moves 1.9e-02. At `Z_p = 1e6 Ω` the port is
nearly open, `I₁` is a ~1e-9 A near-cancellation residual, and `Z₁₁ = V₁/I₁`
inherits its conditioning. Item 2's negative-result clause is explicit that a
red a mesh-tagged re-record does not explain goes to known-issues + §7 and
stops, and re-recording a 40%-mobile quantity at a 1e-9 print band would pin
noise as a fact. Entered as a 🚫 OPEN known-issues entry with both columns and
all four margins.

*The contrast is the useful result.* Everything on the **terminated** fixture
improves under step B: leg (d0)'s discrimination margin 253.2002× →
**2256.9707×**, the 4×4's class separation 150.3584× → **166.6766×**, every
intra-class spread down (0.0617/0.0359/0.0237% → 0.0553/0.0353/0.0214%),
σ_max 0.999993391 → 0.999992805, reciprocity 2.049e-14 → 2.152e-14 relative,
all three gates green. So the anti-degeneracy role the flipped leg (c) gate was
carrying is already carried, with two decades more margin, by two gates that are
on `main`, green, and *better* on step B's mesh.

**What the next review is asked to rule.** Whether the open-limit column is
retired as a record-bearing fixture (this attempt's reading — it is a
diagnostic, and its anti-degeneracy duty is redundant), in which case step B
lands together with that retirement and leg (c)'s reproduction anchor is
re-sited on the terminated fixture and (d1′) re-scoped to match; or whether the
open column's conditioning is itself to be measured first (an h-refinement rung
on the open fixture), in which case step B stays parked for another cycle. The
implementer declines to choose: retiring a record-bearing gate is not an
in-slot judgement, and neither branch is the one item 2 pre-registered.
`GEO-19` stays 🟡; the blocker-B known-issues entry stays open (step B is still
not on `main`); step C (§9 item 5) remains serial behind this. *(Superseded by
the step-B ✅ entry below: step B landed 2026-08-25 under ruling (6\*).)*

**Ruling (6\*), 2026-08-24 18:00 review — option (A) granted: the open-limit
column is retired as a record-bearing fixture, and step B lands with the
retirement (§9 item 1).** The retirement is a replacement, not a loosening:
no band widens, leg (c)'s reproduction anchor re-sites on its driven `I₁`
(mesh-tagged) and the terminated fixture, the degeneracy ordering assertion
executes its pre-registered (4\*)(iii) disposition (recorded class
means/spreads; thin-separation finding stays flagged to the weekly review
for Phase 6), and the open solve may keep printing as a diagnostic with its
digits kept as history. Option (B) — an h-refinement conditioning rung on
the open fixture — was considered and **not** commissioned: ≥ 2 slots for a
number nothing gates on. `PORT-9` leg (d1′) is re-scoped to the terminated
anchors. Full text in §9.

**Step B ✅ — landed on `main` 2026-08-25 (§9 item 1, executing (6\*)).**
`6c1f54e` cherry-picked onto `main` clean (no conflict: nothing between
`cc4ab78` and `9ee3ee2` touched `mesh.py` or the birdcage port modules), and
the retirement executed in the same commit. Everything the item pre-stated
was measured, and every anchor hit its expected digit:

*(a) The invariance control, from `main`* —
`20260825T003437Z_GEO-19-stepB-invariance-main.log`, **`3 passed` / Status 0
/ 95 s**. Sheeted **116 085** cells, gapped **114 655**, C4 sheet spread
**6.050e-16**, terminal meshed/analytic **0.988616 × 4**, sheet `dx·g` and
closure `1.000000000000` on all four ports, out-of-plane ≤ 7.103e-18 m. The
negative control the item named — the untouched no-gap path — meshes
**98 666** cells digit for digit.

*(b) The three `PORT-9` modules, twice in-slot* —
`20260825T003622Z_...-run1.log` and `20260825T003832Z_...-run2.log`, **`19
passed` / Status 0 / 118 s and 117 s**. Fixture identity: 116 085 cells,
ratio to the re-recorded `STEP2_CELL_COUNT` **1.000000**. Gates, all
pre-stated and unmoved: σ_max(S) **0.999992805** ≤ 1 + 1e-9; pooled class
separation **166.6766×** ≥ 10× (worst intra-class spread 0.0553%); leg (d0)
discrimination margin **2256.9707×** ≥ 10×; leg (c)'s C4 adjacent-pair
spread inside its 5% band; reciprocity gated at 1e-3 and *reported* as an
order of magnitude — `‖S−Sᵀ‖/‖S‖` read 9.490519548e-15 and 1.464324816e-14
across the two runs, which is the (d3c) finding, not a motion. Re-recorded
constants reproduce inside their bands: leg (c)'s driven `I₁` to
**5.934e-12** (band 1e-9, both runs bit-identical) and leg (d0)'s terminated
column to 1.071e-10…2.568e-10.

*(c) The retirement, in code.* `STEP2_CELL_COUNT` 116 368 → **116 085**,
moved once at its source (leg (c)'s module; the other two import it).
`LEG_C_I1_A` re-recorded mesh-tagged to **+9.990584892e-07 +
4.709566544e-09j A**. `LEG_C_Z_COLUMN`'s reproduction assertion is retired —
the four entries are still solved and printed as a diagnostic, their digits
kept in-comment as mesh-tagged history at all three cell counts. Leg (c)'s
anti-degeneracy *ordering* assertion executes (4\*)(iii)'s pre-registered
disposition: retired, margin still printed, both readings (5.0594× at
116 368, 0.7906× at 116 085) recorded in the docstring alongside the two
gates that now hold the duty. **No band widened anywhere**, and the two
gates the duty moved to are green and *better* on step B's mesh.

`GEO-19` stays 🟡 — step C (16 legs, the cost rung; §9 item 5) is what the
chunk is actually for, and blocker B's known-issues entry stays open until
it runs. The open-limit conditioning entry also stays OPEN, now carrying
(6\*)'s retire-when. Both step-B attempt branches
(`…T034500Z`, `…T183000Z`) deleted after the greens from `main`.

**Step C attempt 1, 2026-08-25 07:30 slot — 🟡 the rung is measured and four
of the five gates are green at sixteen legs; the fifth is red on a band that
turns out to be a C4 band. Parked on
`attempt/GEO-19-stepC-20260825T125000Z` (`e7a3926`).**
`20260825T124357Z_GEO-19-stepC-run1.log`, `-n 2`, `1 failed, 1 passed` /
**114 s** (heavy commissioned, standard measured).

*The cost rung — Phase 6's deliverable, and it fits.* 4 → 16 legs takes
**116 085 → 307 296 cells (2.6472×)** and **22.93 → 74.18 s of mesh wall
time (3.2357×)**, both far inside the entry's stop rule (1 M cells / 600 s).
The scaling is sub-linear in neither direction by accident: the air box and
phantom are unchanged, so only the conductor and the 32 half-boxes grow.

*The negative control, digit for digit.* The in-module 4-leg build reproduces
step B's mesh-tagged record exactly — **116 085** cells (delta **0**,
relative 0.000e+00), C4 sheet spread **6.050e-16** against the recorded
6.050e-16, terminal ratios 0.988616 × 4, terminal spread 3.184e-08. So
everything gate 1 measures is the construction and not the count, which is
what the control was for.

*Gates (i), (iii), (iv), (v) at sixteen legs.* `GEO-9` partition
**1.000000000000** and air box **1.000000000000**; all 32 half-boxes
**0.500000000000**; all 16 sheets meshed/analytic `dx·g`
**1.000000000000** with C16 area spread **1.331e-15** (band 1e-12),
out-of-plane extent ≤ **1.736e-17 m** *in each port's own frame*, effective
width `A/h/w` **1.000000000000**, and closure **1.000000000000** on every
port; conductor meshed/CAD **0.981503** ≥ 0.95 — *better* than the 4-leg
control's 0.970069 at the same `h_c`; minimum port-centre separation
**2.731265e-02 m** against the floor 1.750000e-02 m, margin **1.560723×**,
matching the closed-form prediction recorded in attempt 1 to the digit.

*Gate (ii), and why it is a finding rather than a re-record.* The terminals
are all inside `GEO-18` step 1's inscribed band (min/max **0.988615667 /
0.989449760** of `2·π·r_leg²`), but their spread across the 16 is
**8.434e-04** against the pre-stated 1e-5. The ratios take exactly three
values sorted by azimuth — 0.988616 at the eight multiples of 45°,
0.989367 at 22.5/157.5/202.5/337.5°, 0.989450 at 67.5/112.5/247.5/292.5° —
with **≤ 2e-7 spread inside each class**, i.e. tighter than the band. The
1e-5 was measured where the ports are exact 90° coordinate permutations of
each other and so run identical arithmetic; at 22.5° they do not, and an
inscribed triangulation of a disk under-reads its area by ~1.1% to begin
with. The spread is **13× smaller than that under-read**. The entry's
negative-result clause is binding, so no band was widened and the module is
parked; the ruling asked for is which quantity the equality gate asserts —
C_N symmetry of the construction (per-azimuth-class, and *tighter* than
today at ~1e-6) or agreement of the discretization across azimuths (h-
dependent, wanting a refinement rung rather than a constant). Both fit the
measurement; choosing is not an in-slot judgement. Known-issues entry filed.

*Reconciliations the landing needed* (all in `e7a3926`, none of them a band
move): the parked module's sheet reading was the axis-aligned
`_sheet_axes`/`_sheet_extents` pair, replaced by `PORT-9` leg (d1)'s
projection helpers since only 4 of 16 ports sit on a coordinate axis; the
control constant re-recorded 116 368 → **116 085**, mesh-tagged to step B,
with 116 416 and 116 368 kept in-comment as history; the layout diagnostics
read through `diagnostics["port_layout"]`, where `GEO-20`'s parallel
`ring_port_layout` put them. **One trap paid, recorded for the next
module:** a `KeyError` inside a `if comm.rank == 0:` report block left rank 1
in the following collective, so 97 s of pytest became a **561 s Status 124**
(`20260825T123320Z_GEO-19-stepC.log`) — the whole heavy window for a wrong
dictionary key. The module now reports through a guard that broadcasts the
failure and asserts it after the gates.

Blocker B's known-issues entry is **retired** by this run — the
`NotImplementedError` is unreachable and the 16-leg fixture builds. `GEO-19`
stays 🟡 on gate (ii) alone; `GEO-20` step 2 stays serial behind it.

**RULING (2026-08-25 10:30 review) — gate (ii)'s equality half asserts C_N
symmetry of the *construction*, and the reading becomes per-azimuth-class.**
The measurement decides this: the ≤ 2e-7 spread *inside* each of the three
azimuth classes says the construction is exactly C16-covariant — sixteen
copies of the same disk, each meshed by whatever arithmetic its azimuth
lands on — while the 8.434e-04 *between* classes is 13× below the inscribed
triangulation's own ~1.1% closed-form under-read, i.e. the discretization's
azimuthal variation and nothing else. Gating that at 1e-5 gates the mesh,
not the generator; and the h-dependent alternative would spend a refinement
rung (74 s of mesh per rung at 16 legs) to re-learn what the three-class
table already shows. Landing instructions for the parked module, all
pre-stated here so the slot is mechanical:
* **Intra-class equality asserted at 1e-6** — tighter than today's 1e-5;
  measured basis ≤ 2e-7 at 16 legs (5× headroom) and 3.184e-08 at C4. At
  4 legs every port is one class, so the reading *reduces to the existing
  gate exactly* — that identity is the back-compat control and the C4
  numbers must not move.
* **Inter-class spread asserted under a coarse discretization ceiling of
  5e-3**, so a genuinely broken port cannot hide in "reported structure":
  measured basis 8.434e-04 (~6× headroom), and the ceiling sits at half the
  ~1.1e-2 under-read scale that owns the effect. The three class values are
  printed with their azimuths.
* The absolute `GEO-18` step 1 band [0.95, 1.0] is **unmoved**, as is every
  other gate. This ruling moves no existing constant: the 1e-5 stays the C4
  modules' band; the per-class 1e-6 and the 5e-3 ceiling are new constants
  whose measured basis is this run, cited in the module.
* The known-issues terminal-equality entry retires **with the commit that
  lands the ruled module green from `main`** (its own retire-when), not
  with this ruling.

**Step C landed, 2026-08-25 12:00 slot — ✅ `GEO-19` closes. The ruled module
is green from `main` at sixteen legs, and the ruling's own predicted basis
reproduces to the digit.** `20260825T170316Z_GEO-19-stepC-ruled.log`
(`2 passed` / **117 s**, Status 0, `-n 2`, real build, heavy commissioned and
standard measured for the second slot running) plus the record run
`20260825T170523Z_GEO-19-stepC-ruled-record.log` (`2 passed` / **115 s**,
Status 0, `-s`, which is where the per-port and per-class tables live —
pytest captures the report on a green test).

*Gate (ii) under the ruling.* The class key is taken from the **mesh's own
symmetry**, never from the measured areas: the air box and phantom are
symmetric under `x → −x` and `y → −y`, so every azimuth folds into [0, 90]°,
and the aligned folds {0, 45, 90} are one class because they read one value.
The fold alone reproduces the measured table — and the run agrees:

| class | ports | meshed/analytic | intra-class spread (band **1e-6**) |
|---|---|---|---|
| aligned (0/45/…/315°) | 8 | 0.988615772 | **1.923e-07** |
| 22.5/157.5/202.5/337.5° | 4 | 0.989367514 | **5.849e-08** |
| 67.5/112.5/247.5/292.5° | 4 | 0.989449735 | **6.144e-08** |

Inter-class spread **8.431e-04** against the **5e-3** ceiling (5.8× headroom;
attempt 1's flat reading was 8.434e-04, so the class means recover it). The
90° rotation is deliberately *not* assumed anywhere — assuming it would merge
22.5° with 67.5°, and those differ by 8.4e-05, two decades above the
intra-class band. **Back-compat identity:** at four legs every port is
aligned, the module reports **1 azimuth class**, intra-class **3.184e-08**,
inter-class **0.000e+00** — the per-class reading *is* the old flat gate,
which is exactly what the ruling required.

*The four already-green gates, and the negative control, unchanged.* At 16
legs: partition **1.000000000000**, air box **1.000000000000**, all 32 halves
**0.500000000000**, all 16 sheets `dx·g` **1.000000000000** with C16 spread
**1.331e-15** and out-of-plane ≤ 3.4e-18 m, closure **1.000000000000** per
port, conductor meshed/CAD **0.981503**, separation **2.731265e-02 m** vs the
floor 1.750000e-02 m, margin **1.560723×**. The four-leg control reproduces
step B's mesh-tagged record digit for digit: **116 085** cells (delta **0**,
relative 0.000e+00), C4 sheet spread **6.050e-16**, terminal ratios
0.988615825 … 0.988615857.

*The cost rung, restated as the deliverable.* 4 → 16 legs: **116 085 →
307 296 cells (2.6472×)**, mesh **22.99 → 74.37 s (3.2346×)** — reproducing
attempt 1's 2.6472× / 3.2357× and far inside the entry's 1 M-cell / 600 s
stop rule. This is Phase 6's first measured cost rung on the F-small
fixture; it says nothing about F-human, whose scale the 2026-08-30 weekly
review owns.

*What moved and what did not.* One file, `tests/mesh/test_birdcage_port_scaleup.py`:
`TERMINAL_EQUALITY_BAND = 1e-5` is replaced by `TERMINAL_INTRA_CLASS_BAND =
1e-6` and `TERMINAL_INTER_CLASS_CEILING = 5e-3`, both with their measured
basis in-comment. **No constant outside this module changed** — the C4
modules keep their 1e-5, `TERMINAL_AREA_BAND` keeps [0.95, 1.0], and no
assertion was removed. The rank-0 report deadlock guard from attempt 1 is
kept as landed. `GEO-19` → ✅; the terminal-equality known-issues entry
retires with this commit; **`GEO-20` step 2 (16 legs, 32 ring-gap ports) is
unblocked.** `attempt/GEO-19-stepC-20260825T125000Z` deleted after the green
from `main`.

**`GEO-20` — high-pass birdcage: ring-gap port layout (`ring_gap_length`),
the `GEO-18` pattern on the end rings** 🟡 *(commissioned 2026-08-23 weekly
review — item (b) of the 32-port directive. First at `leg_count = 4`
(8 ring-gap ports), standard tier; the 16-leg / 32-port instantiation is a
second step serial on `GEO-19`. Mesh only, no solve.)* **Do:** opt-in
`ring_gap_length = g` removes the arc `|φ − φ_mid| ≤ g/(2·ring_radius)` at
the mid-azimuth between each adjacent leg pair on **both** end rings
(`2·leg_count` gaps), re-places a port box centred on the gap spanning it
exactly (the `GEO-18` step-1 construction rotated into the ring's local
frame: drive direction azimuthal `φ̂`, terminals = the two planar cut faces
of the ring tube, closed-form area `π·ring_minor_radius²` each), and — with
`emit_port_sheets` — the sheet on the plane through the gap centre normal
to `φ̂`. Leg gaps stay independent (`leg_gap_length` may be `None`: a
high-pass birdcage has uncut legs). **Gate (§4), pre-stated:** per ring
gap, terminal area in [0.95, 1.0] of `2·π·r_ring²` and equal across the
`2·leg_count` ports to 1e-5; closure `(A_cond + A_air + A_phan)/A_box =
1` to 1e-9; sheet meshed/analytic = 1 to 1e-9 with `C_N` spread < 1e-12
(N = `leg_count`) and top/bottom ring mirror symmetry < 1e-12; `GEO-9`
partition < 1e-9; conductor meshed/CAD ≥ 0.95. **Negative controls:**
kwarg off reproduces `EX-21`'s uncut record (98 474 cells, 0.967019)
bit-identically; leg gaps on + ring gaps on coexist with both identity
families holding (the 4-leg fixture becomes a 12-port mesh). **Done-when:**
the gates executed at 4 legs with elapsed recorded, and a `mesh:` example
owed by the daily review's ramp rule; step 2 (16 legs, 32 ports) re-runs
the same gates after `GEO-19` and is priced there.
> * **Step 1 (4 legs, 8 ring ports) ✅ 2026-08-24** *(`tests/mesh/test_birdcage_ring_gaps.py`, `20260824T124525Z_GEO-20-step1-ringgaps.log` 2 passed / 70.4 s and `20260824T124646Z_GEO-20-step1-ringgaps-pass2.log` 5 passed / 158.0 s, standard, `-n 2`, real)*. `ring_gap_length = 8.0e-03 m` ⇒ half-angle **5.714285714e-02 rad**, port width `w = 2·r_ring + 2·clearance` = **1.0e-02 m**; the ring-gapped rung meshes **110 786** cells in 20.9 s, the leg+ring 12-port rung **128 402** in 24.9 s *(corrected 10:30 review audit — 25.2 s was the red `124317Z` run's mesh time; the cited green log reads 24.93 s)*.
>   **The construction, and why the closed forms exist.** The `GEO-18` docstring's "the end-ring alternative gives oblique torus sections at 45 degrees and no closed form at all" is true of an *axis-aligned* box cutting the ring, and that is not what is built. Each ring is `leg_count` partial-torus arcs whose ends are the **radial** half-planes `phi = phi_c ± alpha`, so every cut face is an exact disk of area `pi·r_ring²`. The port solid spanning the gap is the `GEO-18` box **rotated into the gap's own frame**: the wedge `|phi − phi_c| ≤ alpha` ∩ `|z − z_ring| ≤ w/2` ∩ `|u − R| ≤ w/2` with `u = rho·cos(phi − phi_c)`. All six faces are planar, so `V = 2·R·w²·tan(alpha)` = 8.008718871e-07 m³, `A = 2·w²/cos(alpha) + 8·R·w·tan(alpha)` = 5.206757303e-04 m², and the mid-plane section `w²` = 1.0e-04 m² are all exact under a linear mesh — a constant-`rho` face would have turned all three into faceting bands. Corners are evaluated directly in global coordinates rather than built at `phi = 0` and rotated (`GEO-19` ruling (4\*)'s ulp lesson).
>   **Gates, all green twice in-slot.** Terminal **9.796288e-05 m²** = **0.974455** of the closed-form `2·pi·r_ring²` = 1.005309649e-04 m² (band [0.95, 1.0]), the 8 readings taking two values 4.1e-12 apart — spread **≈ 2.1e-08** against the 1e-5 equality gate *(corrected 10:30 review audit: the assertion is green but never prints the spread; the close wrote 2.1e-09, and `std/mean` derived from the printed per-port areas is 2.06e-12 / 9.796e-05 ≈ 2.1e-08 — still three decades inside the gate)*; closure `(A_cond + A_air + A_phan)/A` and port volume/analytic both **1.000000000000**; sheet meshed/analytic **1.000000000000** on 14 facets per port with out-of-plane spread **5.042e-18 m** measured along the sheet's own azimuthal normal; C4 spread and top/bottom mirror on volume and sheet below 1e-12; `GEO-9` partition < 1e-9; conductor meshed/CAD **0.969275** ≥ 0.95; phantom-facing area exactly 0 on all 8.
>   **Negative controls.** (i) Kwarg off reproduces the uncut birdcage — 4 port tags only, **98 666** cells (the 0.11 image's count, ratio 1.001950 against the module's 98 474 record, inside its own 1% band, so nothing is re-recorded here) and meshed/CAD **0.966977** vs `EX-21`'s 0.967019. (ii) Leg gaps + ring gaps together give the **12-port** mesh with *both* identity families exact: leg terminals reproduce `GEO-18` step 1's **0.988616** digit for digit and ring terminals 0.974455, closure and volume 1.000000000000 on all 12. (iii) `GEO-18`'s own two modules re-run green from the same tree.
>   **One finding, measured and not gated.** The union form of the mass identity — gapped CAD conductor = uncut CAD conductor − `2·leg_count·pi·r_ring²·g` — reads **0.999998939803**, 1.06e-06 off, well past the 1e-9 the leg cut achieved. It is *not* the arcs: Pappus on the ring primitives before any boolean reads **1.000000000000** on both the 8 arcs (4.099883683960e-05 m³) and the 2 uncut tori (4.421582771688e-05 m³), so the swept angles are exactly `2·pi/N − g/R`. The residual is OCC's quadrature on a union of 28 vs 20 curved pieces, differenced; the module therefore gates the primitive identity at 1e-9 and records the union ratio. `GEO-18` step 1 hit the same amplification (28× on its own difference) and moved its assertion for the same reason — there the primitive was a cylinder and needed no separate check.

### TH — Time-harmonic Maxwell (Phase 2)

| ID | Title | Status | Tier |
|---|---|---|---|
| `TH-1` | **Real complex time-harmonic formulation** | ✅ | standard |
| `TH-2` | Time-harmonic API hardening | ⚠️ | standard |
| `TH-3` | Boundary-condition option set | ⚠️ | standard |
| `TH-4` | Convergence/conditioning diagnostics | 🧪 | standard |
| `TH-5` | Absorbing boundary condition (ABC) | ⬜ | standard |
| `TH-6` | **Validation: plane wave in lossy half-space** | ✅ | standard |
| `TH-7` | **Validation: waveguide cutoff / coaxial line** | ✅ | standard |
| `TH-8` | **Validation: sphere in uniform field (quasi-static)** | ✅ | standard |
| `TH-9` | **Validation: PEC rectangular-cavity resonances** | ✅ | standard |
| `TH-10` | **Validation: lossy dielectric sphere in a full-wave field at 64/128 MHz (the first Larmor-regime gate)** | ✅ — **128 MHz re-recorded on the 0.11 image, `OPS-18` step 3 attempt 1 / step 3b (2026-08-23):** interior relL2 **1.826% → 1.769%**, *with* its mesh moving **55 251 → 55 241 cells** under the image's gmsh 4.15.2. The 64 MHz gate is **bit-identical** across the image change (3.643%, power 3.629%), so this is the same new-gmsh mesh drift as the `OPS-17` volume record, disposed the same way — a re-record by measurement under class ruling (1\*), no band and no gated physics claim moved (the §2.1 / §2.2 `TH-10` numbers and `EX-19`'s reproduction stand). | standard |
| `TH-11` | **Coil-loading trend across the eddy→displacement transition (`MAT-6`'s ΔR machinery at rising f)** | ✅ *(closed 2026-08-18 on step 4's answer + step 5's measured negative — the `GEO-14` precedent; step 1 ✅ 2026-08-13 — 64 MHz feasible at the 10 MHz price, identities to 1e-14, quasi-static ΔR deviation 1.5834% → **10.2698%**, unattributed between physics and 1.26 cells/δ; step 2 ✅ 2026-08-15 — the resolution rung attributes most of it to mesh: **+2.8063%** at 2.52 cells/δ, a −7.4635 pp move, the pre-registered RESOLUTION-DOMINATED band, so no gated trend claim is scopeable yet; step 3 ✅ 2026-08-16 — the 30 MHz mid-point reads **+5.5912%**, giving 1.5834 / 5.5912 / 10.2698% across 10 / 30 / 64 MHz, but cells/δ falls 3.18 / 1.84 / 1.26 in lockstep, so the confound is monotone too and the trend stays a set of points; step 4 ✅ 2026-08-17 — the fixed-f h-ladder reads **flat in f**: refinement moves the deviation −1.87 pp at 10 MHz and −4.48 pp at 30 MHz (−7.46 pp at 64 MHz on record) and the h → 0 brackets overlap at ~−1%, so the "trend" was the resolution term; no gated trend claim is scopeable and §2 stands; step 5 scoped 2026-08-17 review, attempt 1 🚫 2026-08-17 — the third rung is **priced and does not fit a scheduled slot**: 2 807 309 cells (inside the 3.4 M ceiling) but 288.2 s of mesh plus a loaded solve still assembling at the 570 s kill, so §7's probe stop condition fired; module parked on `attempt/TH-11-step5-20260817T123353Z`; **rescoped by the 10:30 review as 5a/5b** — 5a caches the mesh to XDMF and buys the `-n 8` rank change with a measured control (fine-rung +2.8063% reproduced within 0.1 pp), 5b runs the pair off the cache; step 5a ✅ 2026-08-17 — the cache round-trips the 2 807 309-cell rung **exactly** (per-tag owned counts and tag names preserved, mesh 126.4 s replaced by a 14.8 s read) and the `-n 8` fine-rung pair reproduces the `-n 2` record to **+0.00002 pp**, so the rank change is bought; 5b is unblocked and needs one solve per command at ~480 s; step 5b attempt 1 🟡 2026-08-18 — the loaded/free split is **exact** (fine rung reproduced to the last digit, drive surrogate 0.000e+00) and the cache reads back at `-n 12`, but the third-rung solve was **OOM-killed with the container** at 518 s, so the rung is memory-bound at 64 GiB, not time-bound: the review's lever (b) more ranks is the wrong one and (c) shrinking the rung is now live; module parked on `attempt/TH-11-step5b-20260818T004000Z`; step 5b attempt 2 🟡 2026-08-18 — the peak is now **measured**: at `-n 8` the same solve drove `memory.peak` to **64.00 GiB, exactly `memory.max`**, and ran past `timeout -k 30 560` without returning, so `-n 12`'s OOM and `-n 8`'s overrun are one wall with two failure modes and **no rank count affords 2 807 309 cells on this box** — §7's stop condition fires and (c) shrinking to ~1.4 M cells is the review's call; parked on `attempt/TH-11-step5b-20260818T024200Z`; **rescoped 2026-08-18 03:00 review as step 5c** — the ~1.4 M rung (`near ≈ 0.0018`, non-2 `ratio`) end to end off the parked branch, 480 s ceilings, `memory.peak` printed every command; step 5c attempt 1 🚫 2026-08-18 — **the stop condition fired at 0.99 M cells**: the rung meshes to 994 258 cells and its loaded solve alone pegs `memory.peak` at `memory.max` = 64.00 GiB (identity family green at 1e-9 on the solve that completed), so the wall is superlinear in cells — 0.42 M comfortable / 0.99 M pegged / 2.81 M OOM, MUMPS fill-in; **step 5 closed as a measured negative, adjudicated 2026-08-18 10:30 review** — no affordable third rung exists (a rung between 0.42 M and 0.99 M is ratio ≈ 1.2, difference signal at the 0.01 pp run-to-run floor), no 5d scoped, no 64 MHz bracket; the surviving axis is `TH-12` step 2, which names this swap. **Chunk closed:** the trend question is answered — the apparent frequency trend was the resolution term (step 4), no gated trend claim is scopeable, and §2 carries the negative)* | standard (steps 4–5 heavy) |
| `TH-12` | **Second-order elements (degree-2 N1curl): accuracy-per-DOF and cost, measured** (operator directive 2026-08-18; decides the production element order for §10 Phase 5/6 — see entry) | 🟡 *(step 1 ✅ 2026-08-18 — degree 2 on the **coarse** 5 866-cell sphere reads **0.1405%** interior relL2, against the degree-1 fine-rung record 3.643% at 17 670 cells: **25.9× the accuracy at 3.01× fewer cells**, and the ohmic-power error falls 8.3869% → **0.0058%**; the cost is 5.22× the DOFs (7 591 → 39 634), 4.32× the solve wall (0.93 → 4.03 s) and 2.67× the summed peak RSS (388 → 1 036 MiB), i.e. **sublinear in DOFs on both**; negative control green — degree 1 on the same rung reproduces its recorded 8.387% power error to 0.0001 pp; step 2 (the coil) is unblocked. *Audited COMPLIANT 2026-08-18 10:30 review — every claimed number verified against `20260818T110442Z_TH-12-step1-sphere-degree2-rss.log`, gate asserted in code at the unloosened record, `TH-10` callers unmoved; the `memory.peak` → summed-RSS instrument substitution is disclosed and instrument-only*; step 2 ✅ 2026-08-18 — the coil at degree 2 reads ΔR deviation **−0.8508%** against step 4's h → 0 bracket [−2.1492%, −0.9050%]: **outside by 0.054 pp past the upper edge**, having moved **−2.434 pp** off degree 1's +1.5834% on the same coarse mesh, so raising the order walks the coarse rung essentially to the refined answer; the cost is 5.423× the DOFs for **~20× the solve wall** (12.4 + 12.2 s → 235.4 + 266.4 s) and **61.94 GiB** summed peak RSS — 29% above the calibrated 48.04 GiB projection and 96.8% of `memory.max`, so degree 2 is against the same memory wall that killed `TH-11` step 5b; controls green (degree-1 anchor to −0.00002 pp, cells exact, σ = 0 dissipation exactly +0.0), and **one real defect found and left failing**: the complex-power identity reads 3–5e-9 against its 1e-9 family bound at degree 2 because `W_e` explodes 2.03e-13 → 7.16e-06 J (ungauged gradient null space, `Im Z` +9.02 → −2 117 Ω) — common-mode, so the ΔR reading survives, but the identity no longer discriminates at this order; known-issues carries it, unassigned. *Audited COMPLIANT 2026-08-18 18:00 review — every claimed number verified against the log; exit 1 is exactly the two unloosened identity tests.* **Adjudicated, same review:** no affordable (order, h) route to the 64 MHz bracket exists on this box (recorded §2.2, no rung swap scoped), and the identity defect's disposition is commissioned as **step 3** (mechanism: generic-to-incompatible-drives vs coil-feed-specific, on the smoke + sphere fixtures at smoke cost). step 3 ✅ 2026-08-19 — the mechanism reads **COIL-SPECIFIC** at the pre-registered ≤ 10×-on-both band and not narrowly: the smoke fixture's incompatible `J·n ≠ 0` drive moves `W_e/W_m` **1.155×** across order and the sphere's imposed field **1.015×**, against the coil's **3.426e+07×**, so `J·n ≠ 0` is *not sufficient* and the incompatible-drive hypothesis is refuted; anchors green (smoke reproduces `POST-5`'s 1.199162e-06 W at rtol 1e-6 on 1 405 cells; the sphere pair reproduces step 1's 0.1405% / 0.0058% and the degree-1 control band), negative control asserted, energy forms imported not restated; **confound named** — the three fixtures' baseline `W_e/W_m` spans 2.16 / 1.07 / 6.7e-6, so the step excludes "`J·n ≠ 0` is sufficient" but does not separate the feed model from "only a `W_m ≫ W_e` fixture can display it" (`20260819T183425Z_TH-12-step3-warm.log`, 8 passed / 10 s at `-n 2`). **The chunk stays 🟡 pending only the weekly review's production-order decision clause**)* | standard (step 2 heavy) |
| `TH-13` | The degree-2 gradient-subspace injector: feed model or any `W_m ≫ W_e` fixture? — the discriminator `TH-12` step 3 named (commissioned 2026-08-23 weekly review; cheap fixtures only) | ⬜ | standard |

**`TH-10` — lossy dielectric sphere, full-wave, 64/128 MHz (Larmor gate)**
✅ *(steps 1–4 ✅ 2026-08-13, chunk closed by the 10:30 review; full step
narratives archived in `docs/planning/plan-archive.md`)*. The Mie-series
anchor lives in `utils/analytical.py` (`LossySphereSeries`, `e^{+jωt}` by
conjugating both `ε_c` and the field; six identity gates incl. a
conjugated-convention control at 2.1e+04× separation). Gated against the
series on an imposed total-field wall (the `TH-8` pattern): interior relL2
**3.643% at 64 MHz** (18.68× closer to the series than to quasi-statics)
and **1.826% at 128 MHz** (57.31×), both under 5% and decreasing; the
SAR-relevant ½∫σ|E|² to **3.629%** at 64 MHz with the quasi-static power
route missing by 58.14% (quasi-statics under-predicts absorbed power 2.4×
at 1.5 T). Monotonicity of the power error is asserted in-file since
2026-08-15 (8.387% → 3.629%, digits bit-identical to the record).
`GEO-14`'s discriminator later showed the ~3% residual is mesh resolution
still converging (1.781% at 55 251 cells, rate 1.77 in h), not a faceting
floor — frequency-independent *and* mesh-limited. Standing caveats: the
step-4 negative-control margin is 1.16× (a fixture property); the series
reference vs quasi-statics separation is 55–69% in relL2 vs 102–155% in
max-norm — quote the norm with the number. Gates the volume integral only
— no mass averaging, no C95.3 wording, no coil. The coil-loading trend was
commissioned as `TH-11`.

**`TH-11` — coil-loading trend across the eddy→displacement transition** ✅ *(closed 2026-08-18, 10:30 review, by adjudication — step 5 a measured negative; commissioned 2026-08-13 10:30 review to validate `MAT-6`'s ΔR machinery at rising f.)*
> **⚠️ Memory-premise caveat (2026-08-24).** The container ceiling was raised **64 GiB → 128 GiB** by operator directive (§5.1; `/sys/fs/cgroup/memory.max` verified at 128.0 GiB). Step 5's negative — 2.81 M cells OOM, 0.99 M pegged at 64.00 GiB — was measured against the *old* wall, and both rungs sat inside 2× it. That makes the affordability claim **unmeasured, not false** — it is not evidence about this box any more, and must not be cited without re-measuring. **Nothing here is reopened by this note**: re-pricing a third rung is a **review** decision, and step 4's finding is the load-bearing one — the apparent trend was the resolution term, flat in f, and more RAM does not turn a resolution artefact into a trend. A revival needs a new argument *and* its finest rung priced first (§10 epitaph).
> * **Step 1 ✅ 2026-08-13** (`tests/validation/test_coil_loading_larmor_probe.py`, `20260814T003445Z_TH-11-step1-larmor-n2.log`, 138 619 cells, solves 30.5 + 27.0 s at `-n 2`): 64 MHz ΔR deviation **+10.2698%** vs Dodd–Deeds (1.5834% at 10 MHz) at 1.26 cells/δ; complex-power identities ~1e-14, σ = 0 control exact.
> * **Step 2 ✅ 2026-08-15** (`test_coil_loading_larmor_resolution.py`, `20260816T003251Z_TH-11-step2-resolution-n2.log`, 390.9 s, 417 914 cells): `near` = 0.0025 reads **+2.8063%**, a −7.4635 pp move — RESOLUTION-DOMINATED.
> * **Step 3 ✅ 2026-08-16** (`test_coil_loading_transition_30mhz.py`, `20260816T183310Z_TH-11-step3-30mhz-n2.log`, 10 passed, 70.3 s): 30 MHz reads **+5.5912%**, ΔX ratio 0.9500; identity 2.7373e-14 / 1.6799e-14 (bound 1e-9); confound monotone (cells/δ 3.18 → 1.84 → 1.26).
> * **Step 4 ✅ 2026-08-17** (`test_coil_loading_richardson_ladder.py`; `20260817T033320Z_TH-11-step4-baseline.log` 138 s, `20260817T033547Z_TH-11-step4-fine-10mhz.log` 422 s, `20260817T034258Z_TH-11-step4-fine-30mhz.log` 383 s; heavy, `-n 2`): **fixed-f h-ladders are flat in f** — refining 0.005 → 0.0025 moves **+1.5834% → −0.2829%** (10 MHz) and **+5.5912% → +1.1119%** (30 MHz); h → 0 brackets **[−2.1492%, −0.9050%]** at 10 MHz, **[−3.3675%, −0.3812%]** at 30 MHz (p = 1 / p = 2), overlapping, both straddling ~−1%. Identity ≤ 8.1597e-14 on six solves; baseline anchors reproduced to −0.00002 / −0.00000 pp (floor 0.01 pp). The apparent trend was the resolution term.
> * **Step 5 (64 MHz third rung, `near` = 0.00125) — measured negative.** Probe `20260817T123353Z_TH-11-step5-probe.log` (exit 124): 2 807 309 cells, 5.03 cells/δ, mesh 288.2 s. **5a ✅ 2026-08-17:** XDMF cache exact (`20260817T183751Z_TH-11-step5a-cache-third.log`, 2 807 309 cells, 126.4 s mesh, 14.8 s read-back; smoke `20260817T183709Z_TH-11-step5a-cache-smoke2.log`, `20260817T183248Z_TH-11-step5a-cache-smoke.log` exit 124); rank control `20260817T184026Z_TH-11-step5a-rank-control.log` (`-n 8`, 174 s) reproduces **+2.8063%** to **+0.00002 pp** against the 0.1 pp band; fine-rung solve 72–73 s at `-n 8`. **5b 🟡×2:** `-n 12` OOM-killed with the container (`20260818T003806Z_TH-11-step5b-third-loaded.log`, exit 137 at 518 s); `-n 8` `memory.peak` **68 719 480 832 B = 64.00 GiB vs `memory.max` 68 719 476 736 B**, timed out (`20260818T020143Z_TH-11-step5b-third-loaded-n8.log`, exit 137, 908 s); loaded/free split exact (`20260818T003418Z_TH-11-step5b-rehearsal.log`, 288 s, `DRIVE_SCALAR_BAND` 1e-12 measured 0.000e+00). **5c 🟡:** `near` = 0.0018 → **994 258 cells** (`20260818T093219Z_TH-11-step5c-cache.log`); loaded solve completed at `-n 8` in 320.5 s, ΔR +1.3628036e+00 Ω, but `memory.peak` 64.00 GiB = 100.0% of cap (`20260818T093314Z_TH-11-step5c-loaded-n8.log`); free solve exit 124 at 479.2 s (`20260818T093919Z_TH-11-step5c-free-ladder-n8.log`).
> **Adjudication (2026-08-18 10:30 review), relied on by §2.2:** the memory wall is superlinear in cells (0.42 M comfortable / 0.99 M pegged at 64.00 GiB / 2.81 M OOM — MUMPS fill-in); every degree-1 third rung is unaffordable or statistically useless (ratio ≈ 1.2 vs 0.01 pp floor); no 5d. The chunk's question is answered by step 4 (resolution, not physics; brackets flat in f at 10/30 MHz); **64 MHz has no h → 0 bracket** and the gated-bracket deliverable transfers to `TH-12` step 2. §2.2's extrapolation bullet carries the negative and moves only on a gated 64 MHz bracket. Branches `attempt/TH-11-step5b-20260818T024200Z`, `attempt/TH-11-step5c-20260818T101500Z` deleted; the non-uniform three-rung fit `(d_c − d_m)/(d_m − d_f) = (h_c^p − h_m^p)/(h_m^p − h_f^p)` (p by bisection) is recorded as a formula only, never exercised on data — re-implement, do not inherit.
> **Standing cautions:** ~480 s is the safe container ceiling for a foreground slot (560 s exceeded the 660 s Bash wall under memory pressure); `memory.peak` is a lifetime high-water mark (see `TH-12` step 1).
> Full narrative: `docs/planning/plan-archive.md`, entry «§7 TH-11 full narrative — archived 2026-08-23 (weekly review)».

**`TH-12` — second-order elements (degree-2 N1curl): accuracy-per-DOF and
direct-solver cost, measured on gated fixtures** ⬜ *(commissioned
2026-08-18, operator directive — element order is to be evaluated as a
cross-phase lever, and the production element order for the §10 Phase-5/6
work is to be decided from this chunk's measurements, not assumed.)*
Motivation, all on record: every open accuracy question in the TH/MAT
lineage is a cells-per-skin-depth question (`TH-11` steps 2/4: the
apparent frequency trend was the resolution term), and `TH-11` step 5b
has now measured that the degree-1 route to the 64 MHz h → 0 bracket
**does not fit the box** — 2 807 309 cells OOM at every legal rank count
(64.00 GiB = `memory.max`; **⚠️ caveat 2026-08-24 — the ceiling is now 128
GiB by operator directive, see §5.1, so that OOM is a statement about the
old box and this chunk's step 2 must re-price rather than inherit it. The
degree-2 wall this chunk was scoped around, 61.94 GiB on the *coarse*
rung, was 96.8% of the old cap and is ~48% of the new one**). Degree 2 is the other axis: ~20 DOFs/tet vs
6, denser MUMPS blocks, but second-order field convergence ⇒ far fewer
cells at matched accuracy. The infrastructure exists —
`TimeHarmonicSolver(problem, degree=2)` builds `("N1curl", 2)` and the
DG output spaces follow `self.degree` — it has simply never been gated.
**Scope guard:** time-harmonic E-formulation only. The magnetostatic
A-formulation's degree-2 failure (penalty-gauge null-space contamination,
920% field error with a clean solver exit, `core/solvers.py`) is a
formulation property, stays barred, and is *not* evidence about this
chunk. Curved second-order **geometry** (gmsh mesh order 2 — the answer
to `GEO-15`'s 3.3% faceting residual) is a separate knob, out of scope
here; a `GEO` chunk may cite this entry.
> * **Step 1 (gate) — the sphere at degree 2** ✅ *(2026-08-18, `tests/validation/test_lossy_sphere_degree2.py`, `20260818T110442Z_TH-12-step1-sphere-degree2-rss.log`, 7 s at `-n 2`; identical accuracy digits in `20260818T110346Z`)*. Degree 2 on the coarse 5 866-cell rung reads **0.1405%** interior relL2 against the gate ≤ 3.643% (degree-1 fine-rung record at 17 670 cells) — 25.9× the accuracy at 3.01× fewer cells; ohmic-power error **8.3869% → 0.0058%**. Negative control: degree 1 reproduces its 8.387% power error to 0.0001 pp. Cost: 7 591 → **39 634 DOFs** (5.22×), solve 0.93 → **4.03 s** (4.32×), summed peak RSS 388 → **1 036 MiB** (2.67×). `|Im P|/Re P` = **0.000e+00** at both orders. Caution: cgroup `memory.peak` is a lifetime high-water mark — price memory by summed `ru_maxrss` or a freshly recreated container.
> * **Step 2 (reading) — the coil at degree 2** ✅ *(2026-08-18 attempt 2, `20260818T200059Z_TH-12-step2-full.log`, 546 s at `-n 8`; probe `20260818T183449Z_TH-12-step2-probe.log`, calibration `20260818T183730Z_TH-12-step2-calibrate.log` fitting RSS exponent p = 1.271 on degree-1 rungs; audited COMPLIANT 2026-08-18 18:00 review)*. Degree 2 on the 138 619-cell fixture at 10 MHz reads ΔR deviation **−0.8508%** (ΔR +3.1985142e-01 Ω, ΔX −5.6252149e-01 Ω, ΔX ratio 0.9134) vs the step-4 h → 0 bracket [−2.1492%, −0.9050%] — outside by 0.054 pp past the upper edge (5× the 0.01 pp floor, inside the bracket's 1.24 pp width); degree 1 on the same mesh +1.5834% (reproduced to −0.00002 pp), so order moved the deviation −2.434 pp. Cost: 162 710 → **882 296 DOFs** (5.423×), solve 12.4 + 12.2 s → **235.4 + 266.4 s** (~20×, superlinear), summed peak RSS 6.66 → **61.94 GiB** (96.8% of `memory.max`; 29% above the 48.04 GiB projection — treat p = 1.271 as a floor for degree-2 pricing). Controls: cells 138 619, σ = 0 dissipation +0.0 at both orders, drive mismatch 9.2e-35 / 1.0e-34.
>   **Defect, not loosened:** the complex-power identity fails at degree 2 (4.5931e-09 loaded / 3.0030e-09 free vs 1e-9; degree 1 8.07e-15 / 8.71e-15) — `W_e` 2.03e-13 → **7.16e-06 J**, `Im Z` +9.02 → **−2 117 Ω**: the ungauged gradient null space at second order swamps the magnetic term; common-mode, cancels in ΔZ, so the reading stands. Module fails by default; known-issues entry open with three dispositions. **Adjudicated (18:00 review):** no affordable (order, h) route to the 64 MHz bracket exists on this box (recorded in §2.2); no rung swap scoped; dispositions (a)/(c) contingent on step 3.
> * **Step 3 (mechanism) — is the degree-2 `W_e` explosion generic to incompatible drives, or coil-feed-specific?** ✅ *(2026-08-19, `tests/validation/test_degree2_energy_mechanism.py`, `20260819T183425Z_TH-12-step3-warm.log`, 8 passed / 10 s at `-n 2`; cold-compile `20260819T183329Z_TH-12-step3-compile.log` identical ratios)*. Reading **`COIL-SPECIFIC`** (pre-registered ≤ 10×-on-both band): cross-order `W_e/W_m` moves **1.155×** on the incompatible-drive smoke fixture (2.164348 → 2.499688), **1.015×** on the sphere (1.068190 → 1.052552), vs the coil's **3.426e+07×** (6.677632e-06 → 2.287540e+02) — `J·n ≠ 0` is not sufficient; hypothesis refuted. Anchors: smoke degree-1 reproduces `POST-5` **1.199162e-06 W** at rtol 1e-6 on 1 405 cells; sphere pair reproduces step 1 (0.1405% / 0.0058%) on 5 866 cells, 7 591 / 39 634 DOFs; `|Im P|/Re P` < 1e-9 both orders. **Confound carried:** baseline `W_e/W_m` differs 2.16 / 1.07 / 6.7e-6, so a fixed absolute contamination moves the coil ~1e6× more — the step does not separate "the feed model injects it" from "only a `W_m ≫ W_e` fixture displays it"; discriminating needs a magnetically-dominated compatible-drive fixture or the absolute gradient content of `E` (disposition (b) proper) — scoped as `TH-13` (2026-08-23 weekly review). Known-issues entry stays open, the two degree-2 coil identity tests stay failing, no coil number moved.
>   Full narrative (steps 1–3): `docs/planning/plan-archive.md`, entry «§7 TH-12 steps 1–3 closure narrative — archived 2026-08-23 (weekly review)».
> * **Decision clause:** results go to the weekly review, which sets
>   the production element order for the §10 Phase-5/6 breakdown (the
>   32-port directive's cost rung is then priced at the chosen order).
>   No recorded degree-1 number moves; every degree-2 number lands as a
>   new row beside its degree-1 sibling.

**`GEO-14` — the shared ~3% geometry floor: discriminate faceting from
resolution** ✅ *(commissioned 2026-08-13, closed 2026-08-15 on a refuted
hypothesis; full entry archived in `docs/planning/plan-archive.md`)*.
Step 1's one-command discriminator read the pre-registered **RESOLUTION**
band: the 64 MHz interior residual falls 3.643% → **1.781%** at the priced
55 251-cell mesh (rate 1.77 in h — no floor), with the 128 MHz record
reproduced to 1.8e-05 as the exact negative control
(`20260813T213156Z_GEO-14-step1-discriminator.log`). There is no shared
faceting floor to grade against; surface-graded sizing (the never-scoped
step 2) stays available to any future chunk that finds an actual floor.
The re-aim at `MAG-13`'s wire was declined — its own rung ladder already
attributes that residual to resolution.

**`TH-1` — Real complex time-harmonic formulation** ✅ *(all five steps,
2026-07-30/31; full step journal archived in `docs/planning/plan-archive.md`)*
> Replaced the `E = −ωA` proxy with an actual frequency-domain solve:
>
> ```
> ∇×(μᵣ⁻¹∇×E) − k₀²ε_c E = −jωμ₀J,    ε_c = εᵣ − j·σ/(ωε₀)
> ```
>
> **Formulation notes (live constraints, not history):**
> - **The sign convention is part of the spec.** The equation assumes `e^{+jωt}`,
>   matching `ε_c = εᵣ − j·σ/(ωε₀)`. Every analytic gate must be derived in the
>   same convention or validation fails spuriously with conjugated fields.
>   `ufl.inner` conjugates its second argument in complex mode — `ufl.dot` for
>   the load silently flips the convention.
> - **Do not port the gauge penalty.** At ω > 0 the operator acts as `−k₀²ε_c`
>   on the gradient subspace — nonzero everywhere, dissipative wherever σ > 0.
>   The `MAG-10` disease is statics-only; a penalty here would *add* error.
> - **The silent-failure mode is near-resonance ill-conditioning.** With PEC
>   boundaries and lossless air the matrix is exactly singular at cavity
>   eigenfrequencies — and an MRI coil is deliberately operated near resonance.
>   MUMPS returns clean exit codes on near-singular systems. The `core/resonance.py`
>   energy-continuity guard (step 5) is the calibrated detector: threshold 50
>   fires at ~4% fractional detuning, verified against the `TH-9` fixture
>   (pole-law 16.505× vs 16.0×, 3.16%).
> - `build_material_fields` returns σ and εᵣ only — per-tag `μᵣ` needs that
>   function extended (`POST-3` step 5's first code touch).
>
> Results: MMS gate `E_ex = (sin ky, sin kz, sin kx)` at relative L2
> 11.26% → 5.66% over a 2× refinement, **rate 0.9929** vs the O(h) expectation;
> assembled operator complex symmetric to 1e-10 and **not** Hermitian — the
> structural signature that the loss term survived assembly. `solve()` raises
> in real mode (`require_complex_mode`); `TimeHarmonicProblem.dirichlet_e_field`
> imposes an analytic total field on the exterior N1curl dofs, which is how
> every closed-form gate below drives its box. Logs
> `20260731T003553Z_TH-1-steps123-mms.log`, `20260731T021415Z_TH-1-step5.log`.

**`TH-9` — PEC cavity resonance gate** ✅ *(2026-07-30, `core/cavity.py` +
`tests/validation/test_cavity_resonances.py`, `20260730T154846Z_TH-9.log`)*
> First four modes of a 1.0 × 0.8 × 0.6 m cavity match the closed form to
> **0.0436%** (720 cells) / 0.0102% (2268); rate 3.85; the 8 gradient modes
> return as a machine-zero cluster (3.2e-15). **Traps that stand:** a
> 1.0 × 0.7 × 0.5 box is degenerate (two modes coincide); PEC rows need a large
> diagonal in `A` and **unit** diagonal in `B` or the GHEP orthogonalisation is
> invalid. This is the known-frequency fixture the `TH-1` resonance guard is
> verified against.

**`TH-6` — lossy plane wave vs closed form** ✅ *(2026-07-31,
`tests/validation/test_lossy_plane_wave.py`, `20260731T020427Z_TH-6-gate3.log`)*
> The exact source-free `E = ẑe^{−jkx}`, `k = k₀√ε_c` (`Im k < 0` branch),
> imposed as Dirichlet data (εᵣ = 78, σ = 0.7 S/m, 127.74 MHz); *interior*
> slopes measured: `α` to **0.019%**, `β` to **0.059%**, L2 rate 0.9998. Clears
> §10's < 5% MVP bar (the bar is on the field norm — 16³ landed at 5.41% and
> the fix was mesh, not tolerance). Fixed in passing: `post/evaluation.py`
> gathered into a `float64` buffer and had never been called under the complex
> build; it now follows the function's dtype.

**`TH-7` — Validation: waveguide cutoff** ✅ *(2026-07-31,
`tests/validation/test_waveguide_cutoff.py`, `20260731T123411Z_TH-7-gate-final.log`)*
> Evanescent TE₁₀ below cutoff — decay from the transverse geometry against the
> operator's *real* part, complementing `TH-6`'s `Im ε_c` decay. `γ` to
> **0.006%** at 2.4 GHz; L2 rate 1.0013; three-frequency sweep each within
> 0.066% with end-to-end ratio to 0.038% (a k₀-blind solver returns ratio 1);
> `|Im E_y|/|Re E_y|` exactly 0.0 (convention check); the `TH-1` energy guard
> asserted quiet in-band.

**`TH-8` — Validation: dielectric sphere in a uniform quasi-static field** ✅
*(2026-07-31, 15:00 run; `20260731T200457Z_TH-8-gate-final.log`)*
> `E_in = 3/(ε+2)·E₀` measured at **2.443%** at the finest of three meshes,
> fitted rate 1.9675 (superconvergence of the probe-averaged functional, not a
> better element); interior uniformity 0.080%. The load-bearing negative
> control: dropping the sphere from the `material_map` under the *same*
> Dirichlet data moves the interior to 2348% off — the gate cannot be passing
> by reading back its boundary data. New fixture
> `MeshGenerator.sphere_in_box_domain`; its sizing is a gmsh `Ball` field, not
> a `Distance` field (unsigned — would coarsen toward the centre, where the
> gate measures). The lossy-sphere extension it named became `MAT-4` step 1;
> the `k₀R → 0` low-frequency-breakdown regime is still unstressed.
> `TH-8` is a cheap closed-form gate in the same mould; it, `TH-7`, or `TH-6`
> would have caught the `E = −ωA` defect immediately.

> `TH-4` is 🧪 rather than ⚠️ because PETSc residual/conditioning diagnostics are
> meaningful regardless of which weak form is assembled.

> `TH-5` demoted off the MVP path: a birdcage operates inside an RF shield, so a
> **PEC outer boundary is physically correct** for the Phase-5 deliverables.
> ABC/PML is needed only for unshielded free-space validation geometries.

**`TH-13` — the degree-2 gradient-subspace injector: feed model, or any
`W_m ≫ W_e` fixture?** ⬜ *(commissioned 2026-08-23 weekly review from
`TH-12` step 3's named confound — the one thing standing between the
measured degree-2 numbers and a production-order decision for coil-fed
solves; §10 "element-order lever". Standard tier, `-n 2`, complex build,
cheap fixtures only — the coil at degree 2 is 61.94 GiB and is **not** run
here.)* `TH-12` step 3 read the explosion as `COIL-SPECIFIC` (smoke 1.155×,
sphere 1.015×, coil 3.426e+07× on `W_e/W_m` across order) but could not
separate "the coil's feed model injects gradient content" from "only a
fixture with baseline `W_e/W_m` ~ 1e-6 can display a fixed absolute
contamination", because neither cheap fixture is magnetically dominated.
> * **Step 1 (discriminator) — a magnetically dominated fixture with a
>   compatible drive.** The circular-loop azimuthal drive (div J = 0,
>   J·n = 0 — `POST-5` step 2's closed drive) in the time-harmonic smoke box
>   at 10 MHz, degree 1 and 2 on one mesh; print `W_m`, `W_e`, `W_e/W_m`,
>   `|Im P|/Re P` at both orders with the imported energy forms
>   (`test_coil_loading_degree2.py`, never restated). Pre-registered: the
>   fixture must first *be* magnetically dominated — assert degree-1
>   `W_e/W_m ≤ 1e-2`, else the fixture is wrong and the step stops; then
>   cross-order `W_e/W_m` ≥ 1e3× ⇒ **CLASS** (any `W_m ≫ W_e` fixture
>   displays it — the coil's feed is not special, and the defect is the
>   ungauged second-order gradient space itself), ≤ 10× ⇒ **FEED** (the
>   coil's feed model injects it; the production coil port model is the
>   suspect). In between is the finding, recorded, no band invented.
> * **Step 2 (direct measure) — gradient content of `E`.** On the same
>   fixture and the sphere, project `E_h` onto the discrete gradient space
>   `∇H¹` (degree-matched Lagrange) and report `‖∇φ‖/‖E‖` at both orders;
>   pre-registered anchor: the sphere's ratio at degree 2 stays within 2×
>   its degree-1 value (compatible drive, no explosion — `TH-12` step 1's
>   0.1405% says the field is right), asserted; the loop fixture's ratio is
>   the quantity step 1's verdict predicts (CLASS ⇒ it explodes with
>   `W_e/W_m`; FEED ⇒ it does not), asserted against step 1's own reading.
> **Anchors in-run:** smoke degree-1 dissipated power reproduces `POST-5`
> **1.199162e-06 W** at rtol 1e-6; the sphere pair reproduces `TH-12` step 1
> (0.1405% / 0.0058%). **Done-when:** both steps executed with the verdict
> and both ratios recorded; the known-issues degree-2 complex-power entry
> gets its disposition (CLASS ⇒ a gauged/tree-cotree or `H¹`-augmented
> degree-2 formulation is the next chunk; FEED ⇒ the port model's feed is
> the next chunk); §10's production-order decision is revisited by the
> weekly review with the verdict on record.

### MAT — Materials & phantoms (Phase 3)

| ID | Title | Status | Tier |
|---|---|---|---|
| `MAT-1` | Gelled saline presets (low/mid/high σ) | ⚠️ | smoke |
| `MAT-2` | Materials demonstrably affect solved fields | ✅ | standard |
| `MAT-3` | Debye/Cole-Cole dispersion models | ⬜ | smoke |
| `MAT-4` | SAR computation `σ|E|²/(2ρ)` | 🟡 | standard |
| `MAT-5` | Temperature-dependent conductivity | ⬜ | smoke |
| `MAT-6` | **Dodd–Deeds coil-over-lossy-half-space impedance** | ✅ | heavy |

> `MAT-1` is `⚠️` not because the preset table is wrong but because nothing
> consumes it.

**`MAT-4` — SAR computation** 🟡 *(steps 1–3 ✅; full plans, control-ceiling
arithmetic and audits archived in `docs/planning/plan-archive.md`)*.
**Step 1** (2026-08-03): mean SAR vs the lossy-sphere closed form
`σ|3E₀/(ε_c+2)|²/(2ρ)` — **3.42% / 3.54%** at h = R/10 under a 10% bound;
the first quantitative gate on the imaginary axis of ε_c; `post/sar.py`
computes SAR in UFL from `e_complex` and does not route through
`phantom_fields.py`. **Step 2** (2026-08-04): the averaging operator gated
at m = 0.05 g (uniform-field identity 0.999846, kernel mass 0.040%, lens
ceiling control). **Step 3** (2026-08-07): the sizing gap closed on
R = 0.03 m — identity **exact at 1 g and 10 g** on an imposed field; kernel
mass 0.0120% / 0.0044%; quadrature degree 16 required (the ball is a UFL
`conditional`; degree 12 is surface-under-resolved sampling noise).
Standing traps: `ufl.real` around any UFL comparison with a non-zero
centre (`ComplexComparisonError` — a comparison that works at the origin
is not evidence it works elsewhere); density via `build_density_field`.
**What remains — why 🟡:** an IEEE C95.3-conformant 1 g/10 g claim needs a
solved coil+phantom field, which stays unlicensed (§2); the honest venue
is the coil+phantom fixture now that `GEO-9` is closed.

**`MAT-2` — conductivity demonstrably drives the solved field** ✅ *(2026-07-31,
`tests/validation/test_lossy_plane_wave.py::test_conductivity_measurably_changes_the_field`,
log `20260731T020427Z_TH-6-gate3.log`, 21 s at `-n 2`, complex build)*
> Stronger than the "differ by a stated threshold" originally planned: σ = 0.1
> and σ = 1.4 S/m are solved on the same 24³ box at 127.74 MHz and each interior
> decay constant is compared with *its own* closed form — 2.1193 vs 2.1243 Np/m
> (0.233%) and 21.8781 vs 21.9045 Np/m (0.121%) — and the **ratio** 10.3232 is
> compared with the closed-form 10.3116 (0.113%). A σ-independent solver (the
> retired proxy) returns ratio 1. `MAT-6` still owns the coil-loading claim.

> `MAT-6` is the quantitative teeth for `MAT-2`. Dodd & Deeds (1968) gives the
> closed-form impedance change of a circular coil above a layered conductive
> half-space — the project's headline physics, *"the phantom loads the coil"*, in
> closed form. Upgrades `MAT-2` from "fields differ by a threshold" to "the coil
> impedance change matches a published solution", and bridges `TH-1` to `PORT-1`.

**`MAT-6` — the step record, compressed** *(steps 1–10a; full narratives,
plans and probes archived verbatim in `docs/planning/plan-archive.md`)*:

> * **Steps 1–2b** ✅ *(2026-07-31; chunk closed here)*. Closed form
>   anchored on the perfect-conductor limit (two derivations to 0.0002%);
>   the 1968 eddy-current kernel — saline at Larmor is outside its regime.
>   Gate at f = 10 MHz, σ = 100 S/m, W = 0.15, 138 619 cells:
>   **ΔR = +0.3276882 Ω vs Dodd–Deeds +0.3225961 Ω — 1.58%** (< 5%, bound
>   sized from the box sweep); ΔX ratio 0.8123, sign + order only (not
>   box-converged); null-tagging control 1.31e-08; σ-blind fails by 100%.
>   Traps that recur: `ufl.max_value` does not compile in the complex build
>   (regularise inside the sqrt); a killed run leaves a stale FFCx lock
>   (`rm -rf ~/.cache/fenics`).
> * **Step 3** ✅ *(2026-08-04)*: re-gated under the production projected
>   drive — **1.5834%**, the projection is a 5e-5 no-op on ΔR; ΔX ratio
>   0.8123 → 0.9200. Method note: separate module importing the fixture,
>   nothing restated.
> * **Steps 4–5** ✅ *(2026-08-05/07)*: the ΔX drive gap does not shrink
>   with box size (0.1077 → 0.1109 at W = 0.25) but collapses 215× under
>   wire refinement — it was finite-wire discretisation, the `W_e^spur`
>   attribution withdrawn. ΔR's wire term measured: 1.5834% → 1.0562% at
>   `resolution_wire` 0.001. The literal `h/r_wire ≥ 16` target is
>   unreachable in the container as configured (memory).
> * **Step 6** 🚫 *(2026-08-08)*: combined-knob fixture (697 401 cells)
>   OOM-killed at the then-16 G container cap — a total-footprint cgroup
>   ceiling, rank-blind; escalated.
> * **Step 7** ✅ *(closed 2026-08-11)*: the operator approved
>   `docker/docker-compose.yml` `limits.memory: 16G → 64G` (verified at the
>   kernel, 68719476736); after three slots lost to backgrounded harness
>   calls (headless sessions must run harness commands **foreground**), the
>   additivity reading landed: **ΔX ratio 0.9835 vs the 0.9843 additive
>   prediction, defect −0.080 pp — ADDITIVE**, no cross-term; `-n 8`
>   established on this fixture family (2.08× speedup over `-n 4`).
> * **Step 8** ✅ *(2026-08-11)*: the slab-resolution knob owns the ΔR
>   residual — `resolution_near` 0.005 → 0.0025 takes ΔR **1.5834% →
>   0.2829%** (417 914 cells); a sub-1% fixture needs slab mesh, not a
>   thinner wire. **Promotion to the production fixture is deferred** until
>   the operator's `ANS-1` Ansys comparison is adjudicated — it would move
>   §2's headline number and every downstream citation in one commit.
> * **Step 9** ✅ *(2026-08-12)*: box truncation owns the ΔX residual — the
>   three-rung trend 0.9200 / 0.9849 / 0.9960 extrapolates to r∞ = 1.0023
>   at recovered exponent **p = 3.045** (dipolar, not given to the fit).
>   Second finding: ΔR is *not* box-converged at W = 0.25 (moves 0.38 pp at
>   W = 0.35); its invariance control was refuted, band not widened. Any
>   composed-ΔR reading composes **signed ΔZ values**, never percent errors.
> * **Steps 10 / 10a** 🟡 / ✅ *(2026-08-12)*: the composed
>   (box+wire+slab) fixture meshes at 895 974 cells but one solve exceeded
>   ~1 700 s at `-n 8` — ≥ 5.7× the stop rule. Step 10a's attribution:
>   fill-in **exonerated** (factor-flops ratio 1.693× vs 1.28× cells);
>   surviving suspects are cgroup memory pressure (MUMPS in-core estimate
>   69 894 MB vs the 65 536 MiB cap) and MUMPS parallel load balancing.
>   **Step 10 is the weekly review's to commission**: a memory-headroom run
>   (`-n 12`, or out-of-core / raised `ICNTL(14)`) timed against the 257 s
>   prediction. **Commissioned 2026-08-16 (weekly review) as step 10b**,
>   heavy, one command, deliberately narrow: the composed 895 974-cell
>   fixture, one solve at `-n 12` with MUMPS `ICNTL(14)` raised (and
>   out-of-core as the in-run fallback if the in-core estimate still
>   exceeds the cgroup cap), wrapped `timeout -k 30 1200` — **done-when:**
>   solve wall time recorded and either ≤ 2× the 257 s prediction
>   (attribution CONFIRMED: memory pressure owned the ≥ 5.7× overrun) or
>   not (attribution REFUTED — record the time, suspect load balancing,
>   stop; that negative result closes 10b too). No tolerance moves; the
>   ΔZ physics is already gated on the per-knob fixtures. Priced from the
>   step-7 `-n 8` record; if the mesh alone exceeds 300 s, kill and
>   report — do not shrink the case, the composed size *is* the question.
>   Note the factor stays resident after `solve()` returns
>   (`time_harmonic.py:453`) — post-solve processing on MAT-6-class
>   fixtures holds ~37–52 GB against the cap. The overrun also proved plain
>   `timeout` does not stop mpiexec (hence the mandatory `-k 30`) and
>   wedged the container (recovery: `up -d --force-recreate`).

### POST — Post-processing & field extraction

| ID | Title | Status | Tier |
|---|---|---|---|
| `POST-1` | Interface-aware field extraction reliability | 🟡 *(adjudicated 2026-08-05, 18:00 review — mean semantics decided, extremum semantics is step 4)* | standard |
| `POST-2` | Energy/consistency diagnostics | ⚠️ | standard |
| `POST-3` | Replace vacuous consistency metrics | 🟡 | standard |
| `POST-4` | Centerline point evaluation is rank-count-dependent: attribute and fix the ownership tie-break in `evaluate_vector_field_parallel` | ✅ *(chunk closed 2026-08-12 — every step closed or dispositioned; note the title's premise was itself refuted, the tie-break was never the defect. Step 1 ✅ 2026-08-11 — ownership **refuted**, 0/120 multi-claims; locus is the Lagrange-P1 interpolation, 1.163e+04× separation. Step 2 🚫 skipped. Step 3 ✅ 2026-08-11 — the centerline samples the source fields: **23.5539% → 0.008613%**, a 2735× collapse; known-issues entry **retired**. Step 4 ✅ 2026-08-12 — the export-path P1 artifact is **bounded and attributed**: midpoint relative medians **51.17% / 52.47% / 20.18%** (`A`/`B`/`E`), vertex/midpoint separation **0.42–0.68×** so the step's vertex-localization hypothesis is **REFUTED**, and a DG1 target reproduces all three sources to round-off — 100% of it is the P1 continuity constraint. All four steps now closed or dispositioned)* | standard |
| `POST-5` | Real Poynting power balance: wrong-sign boundary flux on the time-harmonic smoke fixture + `poynting_power_balance` raises on scalar `sigma=0.0` (`OPS-17` step-2 defects 3 + 4, known-issues 2026-08-17; commissioned 2026-08-17 10:30 review) | ✅ *(step 1 ✅ 2026-08-18: defect 4 fixed, `ds` ruled out at ratio 1.000000000000, ladder verdict **SOURCE/ASSEMBLY**. Step 2 ✅ 2026-08-19: the closed azimuthal drive reads **ASSEMBLY** — imbalance 116.7465% → 105.9632% with the sign unmoved, against a band that required < 25% and positive — so defect 3 is the boundary leg, not the source. **Step 3 ✅ 2026-08-19 — and it overturns step 2's verdict**: scored against closed form *by itself* the boundary leg is **sound** (4.1141% at 24³ vs the pre-registered 10%, O(h) at rate 0.981, volume-leg control 0.0174%), and the smoke fixture's O(100%) imbalance is the **impressed-source term `½Re∫E·J̄dV` that the helper omits** — restoring it drops 116.7465% → **16.7465%** (axial) and 105.9632% → **5.9632%** (azimuthal), both inside the pre-registered 25%. The chunk's "the sign is one the identity forbids" premise is false for a driven domain. **Step 4 ✅ 2026-08-19 — the helper now knows the impressed-source term and the xfail is a passing gate**: `poynting_power_balance` takes `current_density` + `source_measure` and scores the three-term statement, the smoke gate reads **16.7465%** against its unmoved 25% band, the two-term record 116.7465% is still computed and asserted, and the J = 0 control on `TH-6` assembles **exactly 0.0 W** with all seven other quantities bit-identical to the source-free call. `20260819T201005Z_POST-5-step4-smoke-final.log` 12 passed / exit 0 / 8 s and `20260819T200651Z_POST-5-step4-negcontrol.log` 15 passed / exit 0 / 152 s, both `-n 2` complex. *Step 3 audited COMPLIANT 2026-08-19 10:30 review — every step-3 assertion verified PASSED in the log body before the exit-124 kill landed in a pre-existing gmsh-heavy test, the second window footers exit 0, and the test diff is purely additive (0 deletions); caveat on record: the bands' pre-registration rests on the journal, not the commit graph — the run-time HEAD predates the band constants, inherent to the write-run-commit workflow*)* | standard |

> *(Closed-step plans, execution journals and audits for `POST-1` and
> `POST-3` are archived verbatim in `docs/planning/plan-archive.md`.)*
>
> **`POST-1`** 🟡 — steps 1–6 all ✅; **what remains is the coil+phantom
> application, where the chunk earns its ✅.** Compressed record: three real
> defects found and fixed (the complex→float64 cast scoring phantom metrics
> on `Re(E)` — closed by `POST-3` step 4; the ghost-cell double-count in
> tagged-cell aggregation — step 1; the guardrail's rank-local fallback —
> step 2, decision now on the allreduced interior count). Steps 3/4/4b
> measured drop-set semantics on the `TH-8` sphere and a chordal-error-free
> planar fixture: the interface guardrail is **harmless for means**
> (0.01 pp) and **harmful for peaks** (dropping the interface layer costs
> 2.157× in peak error — the layer is 22% *more* accurate than the
> interior), and step-3's `Re E`-vs-`|E|` question was discharged as an
> exact equality on the lossless sphere. **Step 5 flipped the production
> default to `prefer_interior=False`** (all four sites in
> `post/phantom_fields.py`; parameter retained, `True` path pinned; no
> landed gate moved — `MAT-4`'s mean SAR is structurally insensitive).
> Step 6 gated CSV-export/stats parity bit-for-bit in both modes.
> Transferable lessons that outlive the steps: sample `e_complex`, never
> `Re` of a phasor, for magnitude anchors (the planar fixture scored
> 61.8232% on the substitution); thin tagged regions for guardrail tests
> must be hexahedra; the `_owned_cell_count` AttributeError escape hatch is
> pinned, not fixed.

> The old flagship metric `e_to_b_mean_ratio` is by construction
> `≈ ω·|A|/|∇×A|` — a mesh length scale, not physics; deprecated-as-a-gate
> in `post/consistency.py`. **`POST-3` replaced it with identities that can
> fail for real reasons — all five of its own steps are ✅** *(full plans +
> journals in `docs/planning/plan-archive.md`)*: step 1 Poynting real-power
> balance (4.13% at 24³, rate 0.987, σ-blind control 95.2%); step 2 σ(x) as
> a DG0 field (4.49% two-slab, rate 0.9915); step 3 total-current
> divergence residual (rate 0.942 in h, CG2/CG1 vacuity separation 1.5e13;
> environment note: `pc_type hypre` SIGABRTs this image — use `gamg`);
> step 4 phasor-magnitude semantics (both `Re`-cast sites removed,
> identities exact); step 5 piecewise μᵣ through both legs (4.3284% at 32³,
> rate 0.9922, both vacuity controls fire at 3.69× / 5.10×).
> **Reciprocity is discharged by `PORT-1` step 2** (decision 2026-08-02:
> the reaction-route `‖Z−Zᵀ‖/‖Z‖` *is* the field-level reciprocity, at
> machine precision). **What remains:** the 🟡 → ✅ flip is a review's
> adjudication, nothing else is open.

**`POST-5` — real Poynting power balance: wrong-sign flux + the scalar-σ
raise** ✅ *(closed 2026-08-19, step 4 at the 15:00 slot; steps 1–4 ✅ 2026-08-18/19, each audited COMPLIANT)*. **Premise refuted, helper fixed.** The "forbidden" flux sign was never a Maxwell violation: with an impressed `J` the identity is three-term, `−∮½Re(E×H̄)·n̂dS = ½∫σ|E|²dV + ½Re∫E·J̄dV`, and the omitted source term was the whole O(100%) imbalance. **Gated numbers:** step 1 h-ladder h ∈ {0.030, 0.020, 0.015} imbalance 116.7465% / 115.4059% / 114.4227%, fitted rate **0.0290** vs pre-registered ≥ 0.7, sign never corrects ⇒ SOURCE/ASSEMBLY; `∮x·n̂dS = 3|Ω|` ratio 1.000000000000 (1e-10 band) — `ds` is outward; σ-blind control exactly 0.000000e+00 W at all rungs (`== 0.0`). Step 2 closed azimuthal drive (div J = 0, J·n = 0): 105.9632%, still negative ⇒ source compatibility excluded. Step 3 on `TH-6` plane wave, legs vs closed forms (`2αβ = ωμ₀σ = 7.060162290693e+02` at rtol 1e-12, common value 1.241101e-04 W): flux leg 8.1205% (12³) → **4.1141%** (24³), rate 0.981, volume leg 0.0711% / 0.0174%, both inside the 10% `POST5_STEP3_LEG_BAND` — `H = ∇×E/(−jωμᵣμ₀)` and the facet assembly are correct; three-term residual axial **16.7465%**, azimuthal **5.9632%** vs 25% `SOURCE_TERM_RESIDUAL_MAX`. Step 4: `poynting_power_balance` gained `current_density` / `source_measure` and returns `source_power_w` plus always-present `two_term_power_scale_w` / `two_term_relative_imbalance`; `test_time_harmonic_smoke_solve_conserves_real_power` lost `xfail(strict=True)` and passes at 16.7465% vs 25% (two-term 116.7465% reproduced at rtol 1e-6); J = `fem.Constant` zero ⇒ source term exactly 0.0 W, 7 other keys bit-identical (imbalance 8.185716%); σ-blind separation re-derived — ceiling 5.97×, floor 3.0×, measured 83.2535% = 4.97×.
**Logs:** `20260818T215101Z_POST-5-step1-ladder2.log` (5 s), `20260818T215117Z_POST-5-step1-negcontrol.log` (8 passed, 129 s), `20260819T051150Z_POST-5-step2-closed-drive2.log` (4 s), `20260819T051210Z_POST-5-step2-smoke-full.log` (10 passed + 1 xfailed), `20260819T123438Z_POST-5-step3.log`, `20260819T124405Z_POST-5-step3-source.log` (5 passed), `20260819T201005Z_POST-5-step4-smoke-final.log` (12 passed, 8 s), `20260819T200934Z_POST-5-step4-smoke-diag.log`, `20260819T200651Z_POST-5-step4-negcontrol.log` (15 passed, 152 s).
**Carry-forwards:** (a) the smoke fixture's 16.7465% / 5.9632% residuals are curl-trace discretisation error at ~9 cells/λ, quoted as gated, not explained; the two-term 116.7465% / 105.9632% readings stay computable by design. (b) Any `SpatialCoordinate`-in-a-facet-integral form on a gmsh mesh must pin `metadata={"quadrature_degree": …}` — an unpinned one killed two windows (`20260818T213256Z`, `20260818T214040Z`); 0-byte FFCx cache stubs are a live lock (`find /root/.cache/fenics -size 0` in any stalled-JIT preflight; see known-issues). (c) `test_time_harmonic_smoke.py` and `test_poynting_balance.py` no longer fit one 540 s window together. (d) Natural-BC driven fixtures satisfy `½∫σ|E|² + ½Re∫E·J̄ = 0` by construction, so the three-term residual there is exactly the flux over scale. Known-issues defect-3 entry corrected on the sign claim. Ramp example `EX-26` ✅.
Full narrative: `docs/planning/plan-archive.md`, entry «§7 POST-5 full narrative — archived 2026-08-23 (weekly review)».

**`POST-4`** ✅ *(closed 2026-08-12; full step plans + journals in
`docs/planning/plan-archive.md`)*. The chunk title's premise was refuted by
its own step 1: the `evaluate_vector_field_parallel` ownership tie-break
was never the defect (0/120 multi-claims) and that function was never
changed. What the chunk bought: **(step 1)** the 23% centerline rank
spread attributed to the Lagrange-P1 interpolation of non-conforming
fields (interpolant path 97.9755% vs source path 0.008426%, 1.163e+04×
separation; a 56× artifact present even at `-n 1`); **(step 3)** the mri
centerline printout now samples the source fields — spread 23.5539% →
**0.008613%**, a 2735× collapse; known-issues entry retired; **(step 4)**
the export-path P1 artifact bounded and attributed — midpoint relative
medians 51.17% / 52.47% / 20.18% (`A`/`B`/`E`), a DG1 target reproduces
all three sources to round-off, so 100% of it is the P1 continuity
constraint; **(step 5)** the DG1/VTX faithful-export route priced — exact
round-trip fidelity, 10.5× disk, no wall-clock cost; complex-build
`VTXWriter` emits two real arrays per field; VTX rows are dof coordinates
incl. ghosts. **Standing (2026-08-12 review call):** DG1/VTX is the
faithful-export direction, but adoption is **blocked on the operator's
one-click ParaView check** of a DG1 `.bp` (dashboard Waiting-on-you);
"P1 + caveat" is the standing answer and no example switches its export
until that check returns.

### PORT — Ports & S-parameters (Phase 4)

**All `⚠️` chunks below sit on the §2.2 placeholder.**

| ID | Title | Status | Tier |
|---|---|---|---|
| `PORT-0` | Quarantine the placeholder coupling model | ✅ | smoke |
| `PORT-1` | **Real port excitation from the solved field** | ✅ *(closed 2026-08-15 review: done-when met through the package — `‖S−Sᵀ‖/‖S‖ = 2.5494e-05` vs the 1e-3 gate on a field-derived S, two-torus fixture; step 4, `20260813T183606Z`)* | standard |
| `PORT-2` | Port data model and tagging contract | 🧪 | smoke |
| `PORT-3` | Calibration checklist → executable checks | 🧪 | standard |
| `PORT-4` | Multi-port drive/termination consistency | ⚠️ | standard |
| `PORT-5` | S-matrix reciprocity/passivity metrics | 🧪 *(step 1 ✅ 2026-08-16: the metrics are off placeholder data — see below; the chunk's frequency-sweep scope is untouched)* | standard |
| `PORT-6` | Frequency sweep orchestration | 🧪 | smoke |
| `PORT-7` | Touchstone metadata + parser cross-check | 🧪 | smoke |
| `PORT-8` | Port-orientation sensitivity | ⚠️ | standard |
| `PORT-9` | Lumped-element port boundary condition (the birdcage port model) | ✅ **2026-08-25 at 10 MHz on the gapped 4-leg birdcage** (leg (d1′) solve half: displaced 4×4 on the power-wave route, `‖S−Sᵀ‖/‖S‖` 2.259e-14 vs 1e-3 — 2.466e+11× separation from the pre-fix 5.57e-03 on the same fixture — gate (iii′) breaks 0.5% on all three classes under a 22.5° single-leg rotation, self 6.2219% / adjacent 7.1142% / opposite 2.8474%, while the zero rung reproduces leg (d0)'s column to ≤ 2.568e-10 and σ_max 0.999992805; (iii′) 5% → 0.5% committed with all three consumers green, `13 passed` + `24 passed`. **No Larmor, resonance or tuning claim** — `PORT-11` carries 64/128 MHz) *(**step 1 done 2026-08-17** — parked formulation merged, sheet instantiated on `GEO-16`'s facet tag `212` of the solve fixture, both routes read off one 10 MHz solve: gap 0.894310 × ωM₁₂ raw (−0.0233 pp off its unfragmented record), lumped 0.829782, cross-route **7.7095%** against step 2's 5% band. **Step 2 executed 2026-08-17**: both pre-stated bands **MISS** (cross-route 7.7095% vs 5%; lumped mutual 12.6931% vs 10%; the gap route stays inside at 6.0391%) and the miss is **diagnosed** — it is the transverse average over the sheet, 7.7783 pp, with a path/projection residual of only **0.0763 pp** against the pre-stated ~1 pp threshold. Bands not widened. **Decision made 2026-08-17 10:30: narrow the sheet — step 2b scoped** (width ladder f ∈ {1.0, 0.735, 0.5}; the measured profile predicts ~1% at interior width). **Step 2b executed 2026-08-17, 12:00 slot — the band HOLDS**: ladder 7.7095% (f = 1.0, the negative control, reproducing step 2 to < 1e-4) → 3.6730% → **1.8333%** at f = 0.5 against the unmoved 5% band, open-limit identity < 1e-11 per width, 14 passed 150.5 s at `-n 2`. One finding en route: the sheet's width is the **area-based effective width `A/h`**, not the bounding-box extent (the midpoint filter leaves a ragged edge; bbox overstates by 14–15% and the first attempt read 14.04% MISS because of it) — the convention is now part of the port model's spec. Step 2's gate is closed at the narrowed definition; step 3 unblocked on this side, its ports use f = 0.5. **Step 2c executed 2026-08-18, 22:30 slot — the reciprocity leg is run and the route exists**: `run_n_port_sparameter_sweep` gained a third excitation route (`LumpedSheetPortSpec`, sheets on every port, impressed source on the driven one, `V = V_src − I·Z_p`), and the two-torus two-port sweep at f = 0.5 on both ports reads **‖S − Sᵀ‖/‖S‖ = 2.574249e-11** against the unmoved 1e-3 band (‖Z − Zᵀ‖/‖Z‖ = 1.767820e-09), 7 passed 122.2 s at `-n 2`. Cross-route *inside* the sweep 1.6079% / 1.5950%, inside step 2's 5% band, 0.23 pp off step 2b's 1.8333% — the reading is drive-dependent at that grain. Two legs not run as written (the 1e-4 reproduction is not the same quantity under a sheet drive; the fragmented-mesh gap sweep needs a multi-tag `GapVoltagePortSpec`), the negative control run instead as the record-owning gates, 16 passed. Step 3's gate (i) prerequisite is discharged. **Step 3 legs (a)+(b) executed 2026-08-19/20, both 🚫**: the birdcage mesh has **no port-sheet facet** (global facet set exactly `{1}`) and its port boxes have **no terminals** (conductor facet area exactly 0.000000e+00 m² on all four ports under a closure identity at 1.000000000000) — they are air blocks outside an uncut coil, so no solve can reach the gates. **Step 3 is blocked on `GEO-18`** (birdcage conductor gaps, commissioned 2026-08-20 03:00 review — cut the legs, square-section boxes, drive `ẑ`; supersedes leg (a)'s mid-plane prescription). **`GEO-18` closed 2026-08-22** — terminals (step 1) *and* port sheets (step 2, area exact to 1.000000000000, C4 spread 8.470e-16) now exist on the birdcage, so **step 3's mesh prerequisite is discharged**; step 3 re-runs unchanged, unqueued as of this slot. **Step 3 leg (c) executed 2026-08-22, 16:30 slot — the first field on the gapped birdcage**: one lumped-sheet solve, P1 driven, 116 416 cells at ratio 1.000000 of the `GEO-18` step-2 record, **price 7.55 s** at `-n 2` (mesh 21.35 s), and the pre-stated C4 gate holds — `|Z₂₁ − Z₄₁|/|Z₂₁|` = **0.0159%** against the unmoved 5% band, `6 passed 40 s`. The **finding** is the control: the anti-degeneracy check passes at 1.0060× margin (0.0160% vs 0.0159%), so at `Z_p = 1e6 Ω` column 1 of Z is near-degenerate and leg (d) must first find a port impedance that separates adjacent from opposite coupling). **Step 3 leg (d0) executed 2026-08-22, 22:30 slot — the termination is found**: at the ports' own `Z_p = z0 = 50 Ω` the discrimination margin `|Z₃₁ − ½(Z₂₁ + Z₄₁)|/|Z₂₁ − Z₄₁|` reads **598.4002×** against the pre-stated 10× floor **while** the adjacent spread holds at **0.0152%** inside the unmoved 5% band, `8 passed 48.90 s` at `-n 2` and every digit reproduced by a second in-slot run. Both negative controls pass: the 1e6 Ω control re-solves leg (c)'s column to ≤ 2.4e-10 relative, and `|I₁|` rises 13 875.96× (9.993e-07 → 1.3866e-02 A), so the termination closed a conduction path. `Z₁₁` turns from 3.43 kΩ capacitive to +21.73 + 7.46j Ω and the mutuals split into adjacent 17.008/17.011 Ω vs opposite 16.028 Ω — a 5.9% class separation on a 0.0152% intra-class spread. Leg (d) runs at 50 Ω, four solves, ~30 s, standard tier. **Legs (d) and (d1) scoped 2026-08-23 03:00 review** — (d) the 4×4 under the unmoved 08-16 gates (i)–(iii) with the (d0)-column and pooled-class controls in-run; (d1) the geometric control as a `leg_azimuth_offsets_rad` mesh knob rotating one leg with its port (the 08-16 "displace the box" wording corrected — a box off its leg is a degenerate port, not an asymmetric coil). Chunk ✅ on (d) + (d1), never (d) alone; §9 items 1 and 3. **Step 3 leg (d) executed 2026-08-23, 04:30 slot — the 4×4 exists and all three gates pass on the first run**: four driven lumped-sheet solves at `Z_p = z0 = 50 Ω` on one 116 416-cell mesh (31.56 s of solve, `9 passed 64.23 s` at `-n 2`, reproduced bit-identically by a second in-slot run), **(i) `‖S−Sᵀ‖/‖S‖` = 2.495292352e-05 vs 1e-3**, **(ii) `σ_max(S)` = 0.862659137 ≤ 1 + 1e-9 with column power sums ≤ 0.515251749**, **(iii) C4 class spreads self 0.0199% / adjacent 0.0180% / opposite 0.0108% vs the unmoved 5%**; both controls pass (the P1 column reproduces leg (d0)'s record to ≤ 1.9e-10; pooled off-diagonal 9.2570% = 466.06× the worst intra-class spread). Step 3 is ✅ **on the undisplaced mesh**; the chunk stays 🟡 until leg (d1)'s geometric control runs, and §2.2 is unmoved until then. **Leg (d1) attempts 1–2, 2026-08-23 (parked, `attempt/PORT-9-d1-20260823T124500Z`)**: mesh knob exact, but displaced the opposite class reads 1.6476% vs 5% and **`‖S−Sᵀ‖/‖S‖` = 5.57e-03 vs 1e-3** — the route loses reciprocity on an asymmetric layout. **Ruled 10:30 review:** the width hypothesis is refuted from the log's own Z (worst pair P2–P4, no port moved); the residual is a global readout-not-adjoint systematic that symmetric fixtures cancel, so **2c's 2.6e-11 measured the fixture, not the route**; gate (iii) tightened to **(iii′) ≤ 0.5%**; **leg (d2)** — asymmetric two-torus, `f` = 0.5 / 0.735, predictions A: O(1e-2) / B: ≤ 1e-9 — decides it, (d1′) serial on it. **Leg (d2) executed 2026-08-23 and disposes finding 2: A is refuted at its own mechanism** — `I₁(drive 2)` = `I₂(drive 1)` to 1.33e-10, so the readout *is* the source's adjoint — and **A′ stands**: `Z₁₂/Z₂₁` = `I₁(d1)/I₂(d2)` to 1.33e-10, i.e. the whole asymmetry is `_assemble_impedance_matrix` normalising each column by the *driven* port's own current, which makes its `Z` a terminated transimpedance, not the open-circuit matrix reciprocity symmetrises; the asymmetric sweep reads `‖S−Sᵀ‖/‖S‖` = 8.255602536e-09 inside the unmoved 1e-3 only because at `Z_p` = 1e6 Ω the kΩ diagonal hides a 0.25% **per-pair** asymmetry of the same order as (d1)'s 0.2–1.6%. The assembly fix is owed to a review — it moves the 2b/2c/(c)/(d0)/(d) records. **Ruled (2\*) 2026-08-23 18:00 review: power-wave S assembly on the gated routes (leg (d3), §9 item 2), birdcage class re-record (leg (d3b), §9 item 4), the open-circuit-`Z` alternative rejected on leg (c)'s near-degenerate 1e6 Ω column; (d1′) serial on (d3b)**. **Leg (d3) executed 2026-08-24, 21:00 slot — the fix lands and the mechanism is confirmed at its own mechanism**: the gated routes now assemble `S = b_i/a_j` from power waves (`z_matrix` retained as a documented *terminated transimpedance* diagnostic, never reciprocity-gated), and on the asymmetric two-torus at the matched drive `Z_p = z0 = 50 Ω` the fixed route reads **`‖S−Sᵀ‖/‖S‖` = 1.324004669e-16, per-pair 2.972992845e-15** against the old conversion's 1.143811489e-04 / 2.831857978e-03 computed from the retained `Z` **in the same run** — a **9.525277e+11×** separation on the pre-stated ≥ 100× negative control, both gates 1e-6, never widened (`20260824T020350Z_PORT-9-step3d3-asym.log`, `13 passed 186.30s`). Leg (d2)'s identities re-measured unmoved (transadmittance symmetry 2.98e-15; `Z₁₂/Z₂₁` = `I₁(d1)/I₂(d2)` to 3.18e-15, `|Z₁₂/Z₂₁|` = 0.9973497458 — the terminated `Z` keeps its 0.27% asymmetry, now demoted to diagnostic). Class re-record under (1\*), **no band moved**: `test_port_lumped_two_torus` / `test_port_lumped_narrowed_sheet` green untouched (cross-route ladder 7.7431% MISS / 1.0986% / 1.9222% INSIDE vs 5%), `test_port_package_sparameters` σ_max 0.861356895 → **0.864809457** and `‖S−Sᵀ‖/‖S‖` 3.11213e-05 → **4.758625e-05**, both reproduced by the confirm run `20260824T021425Z_PORT-9-step3d3-rerecord-confirm.log` (`14 passed`, Status 0) to 1.6e-10 = 3.2e-04 of the 5e-7 band. Scope: two-torus class only, one green pass per consumer module rather than the item's twice-in-slot (journaled in attempts.md); leg (d3b) unblocked. **Leg (d1′) closed the chunk 2026-08-25 — see the ✅ note at the head of this cell and the prose entry**)* | standard |
| `PORT-10` | The two `PORT-1` systematics: composition measured, not assumed | ✅ 2026-08-16 (cross-term **−0.0604 pp** inside the pre-stated ±0.5 pp) | heavy |
| `PORT-11` | Lumped-sheet ports on the gapped birdcage at 64 MHz (then 128): `PORT-9`'s three gates in the displacement-current regime — §10 subgoal 2b; serial on `PORT-9` ✅ (commissioned 2026-08-23 weekly review) | ⬜ | heavy (probe first) |

**`PORT-1` — Real port excitation from the solved field** ✅ *(closed by
the 2026-08-15, 18:00 review. Full plans, execution journals, adjudications
and audit notes for every step are archived verbatim in
`docs/planning/plan-archive.md` — grep there before re-deriving anything.)*

**Done-when, met:** reciprocity below a stated tolerance on a real,
failable identity, through the package entry point —
`run_n_port_sparameter_sweep` reads the solved field,
`‖S−Sᵀ‖/‖S‖ = 2.5494e-05` against the 1e-3 gate, `‖S‖₂ = 0.861449`,
`is_placeholder=False` (step 4, 2026-08-13,
`20260813T183606Z_PORT-1-step4-packagegate.log`, 7 passed 153.9 s; the
retiring heuristic differs by 3.078e-01 and stays reachable behind a
`DeprecationWarning`). The claim is the **two-torus fixture through this
entry point only** — not birdcage ports, not S11/Z_in, not B1+.

**The step ladder, compressed** *(two-loop fixture, f = 10 MHz,
`ωM₁₂ = +1.241755 Ω`)*: steps 1–2 gated the reaction-route Z
(reciprocity 2.65e-13, `Im Z₁₂` −9.35% of ωM₁₂, the repo's first
field-derived S); 2b–2f diagnosed and removed the electric-energy excess
on the diagonal (gradient content of the discretised load, ratio
0.999998; solenoidal projection is the production drive since 2f); 3a put
`sparameters_from_impedance()` in `src/`. The 3b gap-voltage lineage
(i–xviii) built the gapped fixture, excluded three estimator families by
measurement, found the factor 2 in `_gap_arc_quadrature`'s integration
limits (the buried arc: 0.8% of loop length carrying 45% of the EMF —
terminal to terminal the port voltage is 0.894543 × ωM₁₂, not 0.4937),
excluded wedge limits / the ωM₁₂ reference (+0.481%, wrong sign) / the
PEC box / loss as owners of the residual ~3% estimator-vs-control offset,
and landed with 3b-xvii (matched-topology Faraday-closure gate, 11×
margin) and 3b-xviii (the pair gate: `Im Z₁₂` vs the filamentary closed
form at the unmoved 10%, corrected **0.939581, −6.04%**).

**The two named systematics** (single source:
`src/fem_em_solver/ports/systematics.py`, the `EX-18` lift): PEC box
`D∞ = +0.0169` at `p = 1.657` — an **effective-range** extrapolation from
three padding rungs spanning a factor 1.5, never quoted without its
exponent (pinning `p = 3` gives −1.43 pp); gap physics ÷(1 − 0.030224),
Jin 3e §10.4.2.1's gap-generator feed-model artifact class, earned by the
3b-xvi h-refinement measurement (feed discretisation exonerated at
Δ = +0.0508 pp vs a 0.5 pp band).

**Standing cautions that outlive the chunk:** no `Z_in`/`S₁₁` off this
fixture's unprojected diagonal (`W_e/W_m = 6.524`, step 2b); `Z₁₁`'s
driven-port path integral does not converge (crosses the impressed
source's terminals) — mutual is always the undriven port;
`MUTUAL_TOLERANCE = 0.10` is measurement-justified (the filamentary
reference spans 66.5% of nominal over ±r_wire) — do not tighten; any `dS`
integral over a subdomain some rank does not touch needs an unconditional
`create_entity_permutations()` (the 3b-iv lazy-collective hang); the
"gap wins over conductor" piece policy; known-issues 11 (lateral strips
in the 2xx tags below overhang ≈ 6e-4); the two systematics' independent
composition — the weekly review's open question — was **answered
2026-08-16** (`PORT-10` ✅: cross-term −0.0604 pp vs ±0.5 pp, additive;
the sequential ladder stands); known-issues 3 stays open for its
defect (1).

> **Two port tests are red and deliberately left red.** Both fakes set
> `current = voltage/z0` at the driven port, making it perfectly matched, so
> `b = (V − Z₀I)/2√Z₀ = 0` and the S-matrix diagonal is legitimately zero against
> an assertion demanding non-zero. Fixing them means tuning assertions to match a
> heuristic that `PORT-1` deletes; resolve them there.

> `PORT-3` was 🚫; its recorded failure was a docker preflight error, not a code
> failure, and `OPS-1` resolved that. Real status is unknown — hence 🧪, not ✅.

> `PORT-0` quarantine: `PlaceholderPortModelWarning` on every call, `is_placeholder`
> threaded through the result types, and `export_touchstone()` refuses flagged data
> unless `allow_placeholder=True`. Fabricated `.s2p` files can no longer leave the
> project looking authoritative. `PORT-6`/`PORT-7` are 🧪 rather than ⚠️ — sweep-grid
> generation and Touchstone *formatting* are correct independent of what fills the
> matrix.

**`PORT-5` step 1 — sweep-level sanity metrics on the field route** ✅
*(2026-08-16, `20260816T093556Z_PORT-5-step1-rerun.log`, 10 passed
149.1 s at `-n 2`, standard, wrap `timeout -k 30 500`.)* The metrics had
only ever seen placeholder or hand-built matrices — §10 target 3's
"`PORT-5`'s sweep-level path is untouched". Three cases now ride the
`PORT-1` step-4 module's own fixture (`tests/validation/test_port_package_sparameters.py`;
same module-scoped sweep pair, **no extra solves** — the metrics are pure
numpy). Measured on the report `run_n_port_sparameter_sweep` *returns*:
`passivity_max_sigma` = **0.861449197** against step 4's gated
`‖S‖₂ = 0.861449`, miss **1.97e-07** inside the pre-stated 1e-6, and
equal to `numpy.linalg.norm(S, 2)` to < 1e-12 (same quantity, two
implementations); `reciprocity_max_abs_delta` = 2.194793e-05, which for a
2×2 converts exactly (`‖S−Sᵀ‖_F = √2·max|Sᵢⱼ−Sⱼᵢ|`) to
**‖S−Sᵀ‖/‖S‖ = 2.549409e-05** against the gated 2.5494e-05, band 5e-7;
`passivity_max_column_power_sum` = 0.741345553 ≤ 1 (the second metric
step 4 never read); **no warnings** on the field route.
> **Negative controls, both executed.** The deprecated heuristic's S
> through the same metrics: `passivity_max_sigma` = **0.999985964171**,
> separation from the field route's **0.138537** > the pre-stated 0.13,
> `reciprocity_max_abs_delta` identically 0. An S with one off-diagonal
> perturbed by 2× the warning threshold: delta 9.999344e-02, both
> reciprocity warnings fire, and the untouched matrix still reports none
> — "no warnings" is evidence only because a warning can fire.
> **One §9 constant was wrong and is corrected with its measurement.**
> The item quoted the heuristic's `passivity_max_sigma` as exactly
> `1.000000000000`; that number is the *reaction-route* fixture's
> (`PORT-1` step 2 iv) and the hand-built unitary S of
> `test_port_reaction_impedance.py`, not this mesh's. Measured here:
> 0.999985964171, unitary to 1.4036e-05 (first run,
> `20260816T093226Z_PORT-5-step1.log`, 1 failed / 9 passed — the two
> anchor cases passed at their pre-stated bands in that same run). The
> premise assertion now reads "unitary to 5e-5" with the measurement in a
> code comment; the *discriminating* assertion, the 0.13 separation, was
> never moved.
>
> **Scope.** Metrics wiring only: no tolerance in `sparameters.py` moved,
> `PORT-5`'s frequency-sweep ambitions stay unscoped, and the claim is the
> two-torus fixture through this entry point — every `PORT-1` standing
> caution above applies unchanged.

**`PORT-9` — lumped-element port boundary condition (the birdcage port
model)** 🟡 *(scoped 2026-08-16, weekly planning review — discharges the §9
hold on birdcage ports. Direction per the 2026-08-12 operator note: a
lumped/circuit-element port boundary condition, Jin 3e ch. 11's port
hierarchy — theory in-repo at `docs/references/jin-fem-3e/`; the
implementing step cites chapter/equation numbers after reading it. Not
further gap-voltage estimator variants.)* The gap-voltage `∫E·dl`
machinery stays what `PORT-1` validated; this chunk builds the port model
the birdcage will actually use, and validates it **on the fixture where
the answer is already gated**.
> * **Step 1 — formulation on the two-torus fixture** ✅ *(2026-08-17 re-run; first attempt 2026-08-16 parked then merged `121d65c`; prerequisite `GEO-16` ✅ 2026-08-17)*. Resistive-sheet lumped port, Jin 3e §1.5.4 (1.60)–(1.63) / §6.5 (6.93)–(6.98), `ports/lumped.py`, six exact identity gates (circuit identity `I = V_src/Z_p` to < 1e-12) + passive-sheet control. Wired onto facet tag `212` of the 184 919-cell solve fixture; measured extents `w = 1.040000000e-02 m`, `h = 1.395505060e-02 m`, `w/h = 0.745249896` squares. Gap route on the fragmented mesh 0.939609 corrected (−0.0233 pp vs record); lumped route (`Z_p = 1e6 Ω` probe) 0.873069 corrected; **cross-route 7.7095%**, printed not gated. Logs `20260817T050734Z_PORT-9-step1-rerun-final.log` (12 passed 78.6 s), `20260817T050456Z_PORT-9-step1-rerun.log`, `20260816T170543Z_PORT-9-step1.log`. Convention: `sheet_terminal_current` is generator-sign, comparator is `−I·Z_p`; gap box is **two** cell tags (`101`+`111`, `102`+`112`).
> * **Step 2 — cross-route identity (gate)** ✅ *(2026-08-17, 04:30 slot; `20260817T093554Z_PORT-9-step2.log`, 15 passed 95.2 s)*. **Both pre-stated bands MISS, neither widened:** cross-route 7.7095% vs 5%, lumped ratio 0.873069 ⇒ 12.6931% vs 10% mutual band (gap route INSIDE at 6.0391%). **Diagnosed entirely as the transverse average:** sheet-average vs centre-chord **7.7783 pp**, path/projection residual 0.0763 pp (vs ~1 pp gate, 13× margin); open-limit identity `V_lumped = −(1/w)∫_S E·ĥ dS` asserted < 1e-11; interior stations `|s| ≤ 0.735` within 1.1% of the chord. The `|x−a| < r_minor` fringe-area split (0.1506%) is under-resolved and nothing depends on it. Review 2026-08-17 10:30: narrow the sheet.
> * **Step 2b — narrowed sheet gates the band** ✅ *(2026-08-17, 12:00 slot; `20260817T170841Z_PORT-9-step2b-effective-width.log`, 14 passed 150.5 s; first attempt `20260817T170448Z_PORT-9-step2b.log` 1 failed / 13 passed)*. Ladder f = 1.000 / 0.735 / 0.500 → 7.7095% MISS / 3.6730% / **1.8333% INSIDE vs 5%** (2.7× margin); f = 1.0 reproduces 7.7095% and gap ratio 0.894310 to < 1e-4; gap route flat 0.894310 / 0.894324 / 0.894349; identity < 1e-11 per width; facet counts 1585 → 1511 → 1375, one mesh (midpoint filter `_narrowed_sheet_tags`, no re-mesh). **Width convention, now spec: `w = A/h` on the filtered facet set, never the bbox extent** (bbox overstated 15.3% / 14.2% and read 16.3925% / 14.0402% MISS). Step 3 ports use f = 0.5 and this rule.
> * **Step 2c — lumped-sheet sweep route + reciprocity** ✅ *(2026-08-18, 22:30 slot; `20260818T033643Z_PORT-9-step2c.log`, 7 passed 122.2 s, mesh 39.0 s, sweep 57.0 s; control `20260818T033925Z_PORT-9-step2c-control.log`, 16 passed 145.0 s)*. `LumpedSheetPortSpec` + `run_lumped_sheet_port_case` is `run_n_port_sparameter_sweep`'s third route (both specs at once is an error; `PortVoltageCurrentEstimate.path_voltage_v` added). **`‖S−Sᵀ‖/‖S‖ = 2.574249e-11` vs 1e-3**, `‖Z−Zᵀ‖/‖Z‖ = 1.767820e-09`, `Z₁₂ = +1.097173784e-02 + 1.111378170e+00j Ω`; both sheets f = 0.5, 1375 facets, `w = A/h = 5.171485579e-03 m`; **cross-route inside the sweep 1.6079% (P1) / 1.5950% (P2)** vs 2b's 1.8333% — **0.23 pp drive dependence** (impressed sheet vs impressed gap), expected by step 3, not a defect. Printed, ungated: `σ_max(S) = 0.9869`, max column power sum 0.9740. Control reproduced `EX-20` `‖S‖₂ = 0.861449`, `‖S−Sᵀ‖/‖S‖ = 2.5494e-05`. Open: `GapVoltagePortSpec` takes one cell tag per gap box and cannot run on the `GEO-16`-fragmented mesh.
>   Scope of all four steps: two-torus only, no birdcage claim; the chunk stays 🟡 until step 3. Ramp example `EX-24` ✅. Full narrative: `docs/planning/plan-archive.md`, entry «§7 PORT-9 steps 1, 2, 2b, 2c closure narrative — archived 2026-08-23 (weekly review)».
> * **Step 3 — birdcage instantiation.** The BC on the birdcage mesh's four
>   port boxes (`GEO-9`, generated and identity-gated). **Both prerequisites
>   reported 2026-08-16 and the block is lifted:** `GEO-15` ✅ — graded
>   conductor sizing is achievable and cheap, so this step *assumes* it
>   (`conductor_resolution = 1.6e-3`; budget from **98 474 cells**, mesh
>   16.74 s, not the 48 k baseline); `PORT-10` ✅ — the two systematics
>   compose additively (cross-term −0.0604 pp inside ±0.5 pp), so the
>   sequential ladder in `ports/systematics.py` may be applied on this
>   topology, with the `PORT-10` caveat quoted (one finite padding step,
>   feed-discretisation probe — not the extrapolations themselves).
>   **Gate, scoped by the 2026-08-16 10:30 review — pre-stated, never
>   widened.** On the solved 4×4 through `run_n_port_sparameter_sweep`:
>   (i) reciprocity `‖S−Sᵀ‖/‖S‖ ≤ 1e-3` (step 2's band, unchanged);
>   (ii) passivity `σ_max(S) ≤ 1 + 1e-9` and unit column power sums ≤ 1;
>   (iii) **C4 circulant symmetry of Z** — the CAD geometry is invariant
>   under 90° rotation (ports sit at leg-gap midpoints on a uniform
>   angular grid, `io/mesh.py` `theta = linspace(0, 2π, leg_count)`), so
>   Z must be circulant up to meshing asymmetry: max relative spread
>   within each rotation-equivalence class ({Z_ii}, {adjacent Z_i,i±1},
>   {opposite Z_i,i+2}) **≤ 5%**. (iii) is the step's closed-form-free
>   quantitative identity: it needs no birdcage analytic solution, only
>   the symmetry group. **Negative control:** one port box displaced
>   azimuthally by half a gap — the class spread must blow through 5%
>   while reciprocity (route-independent) stays ≤ 1e-3, separating
>   "symmetry gate measures geometry" from "solver is healthy".
>   **Cost:** never solved — cost-probe-first is binding (`PORT-10`
>   precedent): probe the graded mesh + one single-port solve before
>   committing to four; estimate from `ANS-3` (178 k cells, 2 package
>   solves, 46.3 s) puts 4 solves on ~100 k cells at ~60–120 s, heavy
>   tier, `-n 2`. **Serial:** depends on steps 1–2b landing on the
>   two-torus fixture (2b's band held 2026-08-17) **and on step 2c's
>   lumped-sheet sweep route** — gate (i) runs through
>   `run_n_port_sparameter_sweep`, which has no lumped-sheet route until
>   2c lands; this step's ports use the **same narrowed-width
>   convention** (f = 0.5, `w = A/h`) 2b gates. **Negative result:** a class spread
>   > 5% on the undisplaced mesh is a finding about mesh-induced
>   asymmetry at the graded sizing — record the measured spread per
>   class in this entry and stop; never widen (iii) to admit it.
>   >
>   > **Leg (a) executed 2026-08-19, 21:00 slot — step 3 is BLOCKED on a mesh
>   > prerequisite the entry did not name, and the blocker is measured, not
>   > read off the source**
>   > (`tests/mesh/test_birdcage_port_sheet_prerequisite.py`, 1 passed / exit 0
>   > / 22 s at `-n 2`, real build, standard;
>   > `20260820T020354Z_PORT-9-step3a-numbers.log`, and the same test without
>   > `-s` in `20260820T020316Z_PORT-9-step3a.log`).
>   > Gate (i) runs through `run_n_port_sparameter_sweep`'s lumped-sheet route,
>   > and `LumpedSheetPortSpec` addresses a port by **facet tag** — the gap
>   > box's longitudinal mid-plane, which on the two-torus fixture exists only
>   > because `GEO-16` split each gap box into halves (`101`/`111`,
>   > `102`/`112`) and rebuilt the interface as facet `211`/`212`.
>   > `birdcage_port_domain` has no equivalent: on the step-3 mesh the
>   > **global** facet-tag set (allgathered — rank-local `facet_tags.values`
>   > would not settle it) is exactly **`{1}`**, the outer PEC boundary, with
>   > none of `{211, 212, 213, 214}` present; and each port region's meshed
>   > volume is the **whole** analytic box to `1.000000000000` on all four
>   > ports, i.e. one undivided region with no interface for
>   > `_interface_facet_tags` to rebuild a sheet from. So there is no surface
>   > to put a port on, and no amount of solving reaches gate (i).
>   > **Anchors, both exact:** the same run reproduces the rung step 3 budgets
>   > from — **98 474 cells, ratio to the record 1.000000** — and `EX-21`'s
>   > meshed/CAD conductor **0.967019** against the imported `CAD_MASS_GATE`
>   > 0.95, with the `GEO-9` partition identities re-asserted < 1e-9. **Cost
>   > probe, the entry's binding one, now paid on the mesh side:** mesh
>   > 18.43 s (record 16.74 s), rung 20.13 s, 26 fragment volumes. The solve
>   > side is still unpriced and stays so — pricing a solve on a fixture with
>   > no ports would measure nothing step 3 needs.
>   > **Prescription for the review — a `GEO-16`-for-the-birdcage chunk,
>   > serial before step 3:** in `_build_birdcage_port_model`, split each port
>   > box at its longitudinal mid-plane before the `occ.fragment` call, carry
>   > the halves as `100+i` / `110+i`, and extend the `port_gap` interface
>   > rebuild to `{210+i: ((100+i, 110+i),)}`; the acceptance is `GEO-16`'s own
>   > — the port group unchanged *as a set* (each port's meshed volume must
>   > stay at the `1.000000000000` this leg just recorded), the sheet planar,
>   > and `w = A/h` the area-based effective width step 2b's convention
>   > requires. Note the mid-plane must be chosen so the sheet spans terminal
>   > to terminal along the **azimuthal** (leg-to-leg) direction — the port
>   > boxes are axis-aligned at midpoint angles 45°+k·90°, not radially
>   > oriented, so the drive direction is per-port, not a global constant.
>   > Nothing about gates (i)–(iii) moves; leg (a) neither widened nor
>   > weakened anything.
>   >
>   > **Leg (b) executed 2026-08-19, 22:30 slot — leg (a)'s prescription is
>   > REFUTED, and the prerequisite is bigger than a mid-plane split: the
>   > birdcage port boxes have no terminals at all**
>   > (`tests/mesh/test_birdcage_port_terminals.py`, 1 passed / exit 0 / 25 s
>   > at `-n 2`, real build, standard;
>   > `20260820T033402Z_PORT-9-step3b.log`). Leg (a) prescribed splitting each
>   > port box at its mid-plane so a sheet could span it — which assumes the
>   > box touches conductor on two sides, the way the two-torus gap box does
>   > (it replaces a removed arc of the wire, so facet group `201` = gap↔wire
>   > *is* the terminal pair). That assumption is false here. Partitioning each
>   > port region's boundary by the region behind it gives, on all four ports:
>   > **conductor 0 facets / 0.000000e+00 m², air 24 facets /
>   > 5.200000e-04 m² = 1.000000000 of the analytic box surface, phantom 0
>   > facets**, closure `(A_cond + A_air + A_phan)/A_box = 1.000000000000`
>   > against a 1e-9 band. The port boxes are isolated air blocks floating
>   > *outside* the coil — by construction, not by accident:
>   > `birdcage_port_layout_diagnostics` sets
>   > `port_radius = conductor_outer_radius + port_dy/2 + port_clearance` and
>   > **raises** unless `conductor_radial_clearance > 0`, and the legs are
>   > uncut cylinders spanning the full `coil_length`, so the fixture contains
>   > no conductor discontinuity anywhere. A sheet on a mid-plane of such a box
>   > would drive between air and air.
>   > **Controls.** The zero is an absence, not a miss: the closure identity
>   > says the three regions exhaust the box boundary exactly, and the same
>   > interface machinery on the same mesh measures the phantom↔air surface at
>   > **2.013394e-02 m²**, `0.971035` of its closed form
>   > `2πr² + 2πrh = 2.073451e-02 m²` — inside the pre-stated [0.95, 1.0]
>   > band an inscribed triangulation must occupy. Facet counts are reduced
>   > over **owned** facets only (`indices < size_local`), or every
>   > partition-boundary facet would be double-counted at `-n 2`. Leg (a)'s
>   > anchors re-reproduce on the same run: 98 474 cells (ratio 1.000000),
>   > meshed/CAD conductor 0.967019, `GEO-9` identities < 1e-9.
>   > **Corrected prescription for the review — supersedes leg (a)'s.** The
>   > prerequisite chunk is not "split the port box" but "give the birdcage a
>   > gap to put a port in": cut each leg (or each end-ring segment) at the
>   > port location so the conductor is genuinely discontinuous, and place the
>   > port box straddling the cut so its two cut-facing faces are metal — the
>   > two-torus topology, transplanted. Only then does a mid-plane split mean
>   > anything, and only then is `w = A/h` computable. This is a *physics*
>   > change to the fixture (an uncut birdcage has no capacitors and cannot
>   > resonate either), so it is the review's to commission, not an
>   > implementer's to improvise. Both open questions leg (a) raised stay
>   > open and are now downstream of it: the per-port azimuthal drive
>   > direction, and whether gate (iii)'s C4 circulant premise survives
>   > axis-aligned boxes with `dx ≠ dy` at 45°. Nothing about gates (i)–(iii)
>   > moves; leg (b) neither widened nor weakened anything.
>   >
>   > **Review decision (2026-08-20, 03:00): commissioned as `GEO-18`,
>   > cutting the LEGS — leg (b)'s prescription adopted with the geometry
>   > choice made.** Cut each leg at `|z| ≤ g/2` and re-place each port box
>   > centred on its leg spanning exactly the gap (`dz = g`, square
>   > transverse `dx = dy`), rather than cutting end-ring segments: vertical
>   > legs give exactly planar disk terminals with closed-form area
>   > `π·r_leg²`, where a 45° axis-aligned box against a torus gives oblique
>   > cuts with no clean analytic anchor. This resolves both of leg (a)'s
>   > open questions by construction — the drive direction is `ẑ` for every
>   > port (global, not per-port), and square-section boxes at k·90° make
>   > the layout exactly C4-invariant, so gate (iii)'s premise holds by
>   > design. The port azimuths move from the leg-gap midpoints to the leg
>   > positions — the physics of a low-pass birdcage (drive elements in the
>   > legs). Step 3 re-runs unchanged once `GEO-18` steps 1 (gaps +
>   > identities) and 2 (the port-sheet mid-plane, `GEO-16`'s pattern,
>   > scoped after step 1's measured extents) land; the f = 0.5 / `w = A/h`
>   > convention carries over. **Step 3 stays blocked until then — it is no
>   > longer the §9 drain fallback.**
>   >
>   > **Review decision (2026-08-22, 03:00): `GEO-18` closed, the block is
>   > lifted, and step 3 is split into two serial legs so the cost-probe-first
>   > rule is a queue item rather than a hope.** The mesh step 3 runs on is
>   > now fixed: `birdcage_port_domain(leg_gap_length=LEG_GAP_LENGTH,
>   > emit_port_sheets=True, conductor_resolution=1.6e-3)` as built by
>   > `tests/mesh/test_birdcage_port_sheets.py` — **116 416 cells**, sheets
>   > on facet tags `211`–`214`, halves `101`–`104` / `111`–`114`, terminals
>   > planar disks, drive `ẑ` for every port, mesh 22.73 s + rung 24.77 s at
>   > `-n 2`. The solve side is **unpriced** (the 98 k budget above was the
>   > uncut graded coil; `ANS-3`'s 178 k-cell / 2-solve / 46.3 s is the only
>   > comparable), so:
>   > * **Leg (c) — one-port solve, priced and symmetry-checked (heavy,
>   >   `-n 2`, complex build).** Instantiate `LumpedSheetPortSpec` on all
>   >   four sheets at f = 0.5 (`w = A/h`, step 2b's convention), drive port
>   >   1 only, at the two-torus records' **10 MHz** (the port-model
>   >   frequency, not a Larmor claim), one package solve through the
>   >   lumped-sheet route. **Anchor (§4):** one solve yields column 1 of Z,
>   >   and C4 predicts its two *adjacent* entries equal: **`|Z₂₁ − Z₄₁| /
>   >   |Z₂₁| ≤ 5%`** — gate (iii)'s adjacent class read off one column,
>   >   pre-stated at (iii)'s own band; and `|Z₃₁|` (opposite) asserted
>   >   *different* from the adjacent pair by more than that spread, so the
>   >   check cannot pass on a Z that is all one number. Self-term `Re Z₁₁ >
>   >   0` is reported, not gated. **Negative control:** a 50-facet sheet
>   >   with the port *open* (the step-2b open-limit identity, `Z_p → ∞`
>   >   recovering the no-sheet solve to < 1e-11) is the same second solve
>   >   the displaced-box control would cost; run it **only if the first
>   >   solve priced under 300 s wall**, else record the price and stop —
>   >   the price *is* this leg's deliverable. **Cost:** timeout
>   >   `-k 30 1200`; the cold-JIT rule (first complex command at recorded
>   >   × 3) applies to a form this fixture has never compiled. **Traps:**
>   >   complex build + `FEM_EM_REQUIRE_COMPLEX=1`; `ufl.max_value` /
>   >   ordering comparisons on complex operands (`OPS-22`); pin
>   >   `quadrature_degree` on any `SpatialCoordinate` facet integral
>   >   (`POST-5`); sweep 0-byte `.c` stubs before blaming the cache; port
>   >   addressing is by **facet tag**, and rank-local `facet_tags.values`
>   >   does not settle what tags exist. **Scope:** closes nothing in §2 —
>   >   a priced one-column reading holds step 3 at 🟡; reciprocity and
>   >   passivity need leg (d). **Negative result:** adjacent spread > 5% on
>   >   the undisplaced mesh is the mesh-asymmetry finding the step-3 entry
>   >   already names — record per-entry magnitudes here + known-issues,
>   >   stop, never widen; a solve that does not fit 1200 s at `-n 2` is a
>   >   sizing finding (record memory + wall, try `-n 4` once, then stop).
>   > * **Leg (d) — the 4×4 and gates (i)–(iii) as written (heavy, serial
>   >   after (c)'s price).** Four solves sized from (c)'s measurement (one
>   >   command per solve if (c) read > 250 s), `run_n_port_sparameter_sweep`
>   >   lumped-sheet route, then (i) reciprocity ≤ 1e-3, (ii) passivity, (iii)
>   >   all three circulant classes ≤ 5%, plus the displaced-box negative
>   >   control from the entry above. Not queued until (c) has a number.
>   >
>   > **Leg (c) executed 2026-08-22, 16:30 slot — the gate holds, the price is
>   > small, and the degeneracy control is the finding.**
>   > `tests/validation/test_port_birdcage_lumped_column.py`, **6 passed 40 s**
>   > at `-n 2`, complex build, `20260822T213612Z_PORT-9-step3c-rerun.log`.
>   > The first field on the gapped birdcage: 116 416 cells at ratio
>   > **1.000000** of `GEO-18` step 2's record, four `21x` sheets narrowed to
>   > step 2b's `f = 0.5` (27 facets each, `A/h` = 7.413268623e-03 m against
>   > the full 1.400000000e-02 m bbox, out-of-plane 8.882e-19 m, all four
>   > bit-identical), `LumpedSheetPortSpec` on every one at `Z_p = 1e6 Ω` (the
>   > two-torus probe value), drive `ẑ`, P1 driven only, 10 MHz.
>   > * **Price — the deliverable.** Mesh **21.35 s**, rung 28.75 s, **one
>   >   solve 7.55 s** wall at `-n 2` (12.29 s on the first, cold-JIT run).
>   >   Leg (d)'s four solves therefore project to **~30 s** of solve time on
>   >   one mesh, so leg (d) is a *standard*-tier item, not the heavy one it
>   >   was scoped as, and the open-limit negative control is far inside this
>   >   entry's own 300 s affordability rule.
>   > * **The gate, as pre-stated.** `|Z₂₁ − Z₄₁|/|Z₂₁|` = **0.0159%** against
>   >   the unmoved 5% band. Column 1 of Z:
>   >   `Z₁₁ = +7.157807613e+02 − 3.356708736e+03j`,
>   >   `Z₂₁ = +1.234475890e+01 − 1.879647891e+03j`,
>   >   `Z₃₁ = +1.190817590e+01 − 1.879802412e+03j`,
>   >   `Z₄₁ = +1.231173574e+01 − 1.879351468e+03j` Ω, off
>   >   `I₁ = +9.992734880e-07 + 3.351870842e-09j` A. `Re Z₁₁` = +715.78 Ω,
>   >   reported not gated. Every figure reproduced **bit-identically** across
>   >   the slot's two runs.
>   > * **The finding, and why this closes nothing.** The entry's own
>   >   anti-degeneracy control — `|Z₃₁|` must sit further from the adjacent
>   >   pair's mean than the pair sits from itself — passes at **0.0160% vs
>   >   0.0159%, a discrimination margin of 1.0060×**. It fires, but at the
>   >   noise floor: at `Z_p = 1e6 Ω` all four ports are effectively open, the
>   >   three mutuals agree to four digits, and column 1 of Z is
>   >   **near-degenerate at this grain**. So the 0.0159% adjacent spread is
>   >   evidence that the mesh is C4-symmetric and that the route wires the
>   >   four sheets consistently — it is *not* evidence that the solve resolves
>   >   port-to-port coupling, because a solve resolving none would read the
>   >   same. **Leg (d) must not be run at `Z_p = 1e6 Ω`**: the question it
>   >   inherits is which port impedance separates adjacent from opposite
>   >   coupling on this fixture (the ports' own `z0_ohm` = 50 Ω is the obvious
>   >   first probe, and it costs one 7.55 s solve to find out), and gate
>   >   (iii)'s three circulant classes are uninformative until one does.
>   > * One structural check of this module's own was **wrong as written and
>   >   was fixed with the measurement recorded**, not loosened: the sheet's
>   >   centre was read as the unweighted mean facet midpoint, which is not a
>   >   rectangle's centre on an unstructured triangulation (r = 6.997337e-02 m
>   >   against the exact 7.000000e-02 m, 3.8e-4 relative,
>   >   `20260822T213427Z_PORT-9-step3c.log`). Reading the bounding-box centre
>   >   instead — exact for the full rectangle `GEO-18` step 2 gates — puts all
>   >   four sheets at r = 7.000000e-02 m and at azimuths 0/90/180/270 deg
>   >   inside the 1e-9 band the module asserts. No physics band, record or
>   >   assertion moved.
>   > * **Scope.** Step 3 stays 🟡 and §2 is unmoved: one column of Z is not a
>   >   network, no reciprocity or passivity claim is made here, and 10 MHz is
>   >   the port model's frequency, not a Larmor claim.
>   >
>   > **Leg (c) audited COMPLIANT, 18:00 review 2026-08-22** — every figure
>   > above is verbatim in `20260822T213612Z_PORT-9-step3c-rerun.log`
>   > (`:4702`–`4705`: Z₂₁, spread 0.0159% INSIDE, Z₃₁ deviation 0.0160%,
>   > margin 1.0060×; footer `6 passed`, Status 0, Elapsed 40 s, `-n 2`);
>   > the one structural fix (bbox centre) is disclosed with its red log.
>   > A step close, not a chunk close. **Review reading of the finding:** on
>   > a gapped birdcage every undriven leg is *open* at its gap when
>   > `Z_p = 1e6 Ω`, so the driven current (≈ 1 µA at ~3.4 kΩ capacitive
>   > `Z₁₁`) has no closed conduction path and the three mutuals are the
>   > electrostatic division of the ring potentials — nearly equal by
>   > construction. `Z_p` is therefore **not a numerical knob here: it is
>   > the capacitor a birdcage carries at every gap**, and the port model's
>   > finite `Z_p` is what lets the structure conduct at all. That makes
>   > the termination probe a physics step, not a tuning of the control.
>   > * **Leg (d0) — the termination probe (standard, `-n 2`, complex,
>   >   0.7.2; scoped 18:00 review 2026-08-22; §9 item 3).** Same module
>   >   and fixture as leg (c), two solves: `Z_p = 1e6 Ω` on every port
>   >   (control) and `Z_p = 50 Ω` — the ports' own `z0_ohm` — on every
>   >   port, P1 driven, 10 MHz. **Anchor:** at 50 Ω the discrimination
>   >   margin `|Z₃₁ − ½(Z₂₁ + Z₄₁)| / |Z₂₁ − Z₄₁|` ≥ **10×** *while* the
>   >   adjacent spread `|Z₂₁ − Z₄₁|/|Z₂₁|` stays ≤ **5%** — leg (c)'s
>   >   floor is 1.0060× at 0.0159%, so 10× is a 0.16% separation on the
>   >   same floor, reachable rather than wished for, and a margin bought
>   >   by breaking C4 is a mesh finding, not a pass. **Negative controls:**
>   >   the 1e6 Ω solve reproduces leg (c)'s column bit-identically
>   >   (anchors the run to the record before the knob turns); `|I₁|` at
>   >   50 Ω > 10× the open 9.993e-07 A (the termination closed a path —
>   >   if not, the sheets are not in the circuit). **Cost:** mesh 21.35 s
>   >   + 2 × 7.55 s + cold JIT, `timeout -k 30 400`, ~60 s expected.
>   >   **Scope:** closes nothing in §2; step 3 stays 🟡 until leg (d)'s
>   >   4×4, which is scoped from (d0)'s margin. **Negative result:**
>   >   margin < 10× at 50 Ω means the four ports are too weakly coupled at
>   >   10 MHz for a circulant reading — both columns to §7 + known-issues,
>   >   stop; the review picks the next knob (frequency, or a reactive
>   >   `Z_p` at the birdcage's tuning capacitance), never a third
>   >   impedance guessed in-slot.
>   >
>   > **Leg (d0) executed 2026-08-22, 22:30 slot — the gate passes by 60×, and
>   > the termination is what puts the birdcage in a circuit.**
>   > `tests/validation/test_port_birdcage_termination_probe.py` (a new module —
>   > leg (c)'s is untouched, so its record-owning tests still run), **8 passed
>   > 48.90 s** at `-n 2`, complex build, standard tier,
>   > `20260823T033304Z_PORT-9-step3d0.log`, confirmed by a second in-slot run
>   > `20260823T033413Z_PORT-9-step3d0-rerun.log` (`8 passed 45.22 s`) that
>   > reproduces **every digit of both columns bit-identically**. One mesh
>   > (116 416 cells, ratio 1.000000 of the `GEO-18` step-2 record, 21.43 s;
>   > four `f = 0.5` sheets at 27 facets, `A/h` = 7.413268623e-03 m, azimuths
>   > 0/90/180/270 deg, out-of-plane 8.882e-19 m — leg (c)'s fixture exactly),
>   > two solves, P1 driven, 10 MHz.
>   > * **The gate, as pre-stated.** At `Z_p = 50 Ω` the discrimination margin
>   >   `|Z₃₁ − ½(Z₂₁ + Z₄₁)|/|Z₂₁ − Z₄₁|` = **598.4002×** against the
>   >   pre-stated 10× floor, *while* the adjacent spread `|Z₂₁ − Z₄₁|/|Z₂₁|`
>   >   = **0.0152%** stays inside the unmoved 5% band — the separation is not
>   >   bought by breaking C4. Column 1 at 50 Ω:
>   >   `Z₁₁ = +2.173224483e+01 + 7.459491479e+00j`,
>   >   `Z₂₁ = +1.700799365e+01 + 2.384284683e-01j`,
>   >   `Z₃₁ = +1.602758027e+01 − 9.538522445e-01j`,
>   >   `Z₄₁ = +1.701057452e+01 + 2.384109272e-01j` Ω, off
>   >   `I₁ = +1.379158864e-02 − 1.434197942e-03j` A. `Re Z₁₁` = +21.73 Ω,
>   >   reported not gated. Solve price **9.19 s** (cold) / **7.00 s** (rerun),
>   >   the same grain as leg (c)'s 7.55 s.
>   > * **Both negative controls pass.** (1) The 1e6 Ω solve reproduces leg
>   >   (c)'s recorded column to **≤ 2.4e-10 relative** (`I₁` to 7.8e-12)
>   >   against the 1e-9 print-precision band — the run is anchored to the
>   >   record before the knob turns, and every one of leg (c)'s printed digits
>   >   comes back. (2) `|I₁|` goes 9.992791096e-07 A → 1.386595979e-02 A, a
>   >   gain of **13 875.96×** against the 10× floor: the 50 Ω termination
>   >   closed a conduction path, so the sheets are demonstrably in the circuit.
>   > * **The physics, in one line.** Open at every gap, the driven leg carries
>   >   ≈ 1 µA against a 3.43 kΩ *capacitive* `|Z₁₁|` and the three mutuals are
>   >   the electrostatic division of the ring potentials (1.8797 / 1.8798 /
>   >   1.8794 kΩ, all four digits shared). Terminated, `Z₁₁` becomes
>   >   **resistive-inductive** (+21.73 + 7.46j Ω), the current rises four
>   >   orders of magnitude, and the mutuals separate into their two symmetry
>   >   classes — adjacent 17.008/17.011 Ω, opposite 16.028 Ω, a **5.9%**
>   >   adjacent-to-opposite difference sitting on top of a 0.0152% intra-class
>   >   spread. The review's reading is confirmed by measurement: `Z_p` is the
>   >   gap capacitor, not a numerical knob, and only a finite one lets the
>   >   structure conduct.
>   > * **Disclosure on the margin definitions.** Leg (d0)'s statistic is taken
>   >   on the **complex** entries as scoped; leg (c)'s anti-degeneracy check
>   >   was the magnitude-only analogue. On the *same* 1e6 Ω column they read
>   >   1.7361× and 1.0060× — the numbers are not interchangeable, so both are
>   >   printed in every row of this module's log. Neither band moved and no
>   >   assertion of leg (c)'s was edited.
>   > * **Scope.** Step 3 stays 🟡 and §2 is unmoved: two columns of Z are not
>   >   a network, no reciprocity, passivity or Larmor claim is made, and
>   >   10 MHz remains the port model's frequency. What (d0) delivers is the
>   >   termination leg (d) must run at — **`Z_p = 50 Ω`, `z0_ohm` itself** —
>   >   and the evidence that at that termination the circulant classes of gate
>   >   (iii) are resolvable at all: the adjacent/opposite separation is 390×
>   >   the intra-class spread. Leg (d)'s four solves project to **~28–37 s**,
>   >   a standard-tier item.
>   >
>   > **Leg (d) scoped 2026-08-23 03:00 review — the 4×4 at 50 Ω, the three
>   > gates as pre-stated on 2026-08-16.** Same fixture and code path as (d0)
>   > (116 416 cells, sheets `211`–`214` at f = 0.5, `w = A/h`, 10 MHz,
>   > `Z_p = 50 Ω` on every port), all four ports driven in turn through
>   > `run_n_port_sparameter_sweep`'s lumped-sheet route (step 2c's
>   > `LumpedSheetPortSpec`, the route (d0) used for one column). New module
>   > `tests/validation/test_port_birdcage_four_port.py`; (c)'s and (d0)'s
>   > modules stay untouched. **Anchors (§4), none widened:** (i)
>   > `‖S−Sᵀ‖/‖S‖ ≤ 1e-3`; (ii) `σ_max(S) ≤ 1 + 1e-9` and every column
>   > power sum ≤ 1; (iii) C4 — max relative spread within each of the
>   > three classes {Z_ii}, {Z_i,i±1}, {Z_i,i+2} ≤ 5%, and on Z
>   > (not S, so the sweep's termination convention does not enter).
>   > **Negative controls, both executed in-run:** (1) the driven-P1 column
>   > of the 4×4 reproduces (d0)'s recorded 50 Ω column to ≤ 1e-9 relative
>   > (`Z₁₁ = +2.173224483e+01 + 7.459491479e+00j`, `Z₂₁ =
>   > +1.700799365e+01 + 2.384284683e-01j`, `Z₃₁ = +1.602758027e+01 −
>   > 9.538522445e-01j`, `Z₄₁ = +1.701057452e+01 + 2.384109272e-01j` Ω) —
>   > the four-port sweep is anchored to the one-column record before any
>   > network claim is made; (2) the *pooled* off-diagonal class (adjacent
>   > and opposite treated as one class, the reading a blind gate would
>   > take) must spread ≥ 10× the worst intra-class spread — (d0)'s
>   > column says 5.9% vs 0.0152% ≈ 390×, so 10× is arithmetically reachable
>   > and shows gate (iii) resolves structure, not noise. The 2026-08-16
>   > text's *geometric* control (one port displaced by half a gap) needs a
>   > mesh knob `io/mesh.py` does not have (`theta` is a fixed `linspace`)
>   > and is **leg (d1)**, below — not folded in here. **Cost:** mesh
>   > 21.4 s + 4 × 7–9 s solves + S assembly + cold JIT ⇒ ~60–80 s;
>   > **standard**, `-n 2`, `timeout -k 30 400`, complex build,
>   > `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first. **Traps:**
>   > facet tags allgathered; the sweep route errors if both a gap spec and
>   > a sheet spec are given (2c); the S-matrix reference impedance is
>   > `z0_ohm = 50 Ω` — the same number as `Z_p`, by (d0)'s finding, not by
>   > coincidence, and the test prints both so a reader can tell them
>   > apart; 0-byte `.c` stubs; print `σ_max` and the column sums to 9
>   > digits as the 4×4's reproduction record. **Scope:** (i)–(iii) green
>   > makes step 3 ✅ *as measured on the undisplaced mesh* and `PORT-9`'s
>   > §7 status moves to ✅ **only once (d1) has also run** — the symmetry
>   > gate without its geometric control is a consistency check, not a
>   > validated gate; §2.2's "no coil has ports" sentence is rewritten at
>   > that point, not before; no Larmor claim, 10 MHz stays the model's
>   > frequency. **Negative result:** a class spread > 5% on this mesh is
>   > mesh-induced asymmetry at the graded sizing — record all three class
>   > spreads and both controls in this entry and known-issues, stop;
>   > σ_max > 1 is a passivity finding about the lumped-sheet route on a
>   > four-port network (2c's 0.9869 was two-port) — same disposal; never
>   > widen (i)–(iii).
>   >
>   > **Leg (d) executed 2026-08-23, 04:30 slot — the birdcage has a 4×4, and
>   > all three gates pass on the first run.**
>   > `tests/validation/test_port_birdcage_four_port.py` (a new module; (c)'s
>   > and (d0)'s untouched), **9 passed 64.23 s** at `-n 2`, complex build,
>   > standard tier, `20260823T093319Z_PORT-9-step3d.log` (Elapsed 66 s),
>   > confirmed by a second in-slot run
>   > `20260823T093439Z_PORT-9-step3d-rerun.log` (`9 passed 58.66 s`,
>   > Elapsed 60 s) that reproduces **every printed digit of Z, S, σ(S), the
>   > column power sums and all four spreads bit-identically**. One mesh
>   > (116 416 cells, ratio 1.000000 of the `GEO-18` step-2 record, 21.56 s;
>   > four `f = 0.5` sheets at 27 facets, area 5.930614898e-05 m², `h` = the
>   > 8 mm gap exactly, `A/h` = 7.413268623e-03 m, azimuths 0/90/180/270 deg,
>   > out-of-plane 8.882e-19 m — leg (d0)'s fixture exactly), four driven
>   > solves through `run_n_port_sparameter_sweep`'s lumped-sheet route in
>   > **31.56 s** total, `Z_p = z0_ohm = 50 Ω` on every port (both printed and
>   > named).
>   > * **(i) reciprocity — PASS.** `‖S−Sᵀ‖/‖S‖` = **2.495292352e-05** against
>   >   the unmoved 1e-3 band, 40× inside; `‖Z−Zᵀ‖/‖Z‖` = 3.237695452e-05,
>   >   reported. Four independent solves, each driving a different leg,
>   >   assembled column by column — this is the first reciprocity reading on
>   >   a **coil**, not the two-torus fixture.
>   > * **(ii) passivity — PASS.** `σ(S)` = **0.862659137 / 0.800484790 /
>   >   0.800313330 / 0.187484393**, so `σ_max` = 0.862659137 against
>   >   `1 + 1e-9`; column power sums **0.515083460 / 0.515157098 /
>   >   0.515116202 / 0.515251749**, max 0.515251749 ≤ 1. `PORT-5`'s own
>   >   metrics agree to all nine digits. Roughly half the incident power is
>   >   absorbed (lossy legs + saline phantom), half returned — physically
>   >   the expected reading for a loaded, untuned coil at 10 MHz, reported
>   >   not gated.
>   > * **(iii) C4 circulant symmetry of Z — PASS on all three classes.**
>   >   Spreads **self 0.0199%** (n = 4, mean |Z| 2.297517344e+01 Ω),
>   >   **adjacent 0.0180%** (n = 8, 1.701066377e+01 Ω), **opposite 0.0108%**
>   >   (n = 4, 1.605653897e+01 Ω), each against the unmoved 5% band —
>   >   251–463× inside. The class statistic is the four-port generalisation
>   >   of leg (c)/(d0)'s `|Z₂₁ − Z₄₁|/|Z₂₁|`: widest complex separation
>   >   within the class over the class's own mean magnitude, taken on **Z**
>   >   so the termination convention does not enter.
>   > * **Both negative controls pass.** (1) The P1-driven column of the 4×4
>   >   reproduces leg (d0)'s recorded column to **≤ 1.9e-10 relative**
>   >   (1.033e-10 / 1.938e-10 / 1.474e-10 / 1.448e-11 on `Z₁₁`…`Z₄₁`)
>   >   against the 1e-9 print-precision band — every printed digit comes
>   >   back, so the network claim stands on the one-column record. The
>   >   residual ~1e-10 is the project's known cross-run solver
>   >   non-determinism, not a fixture move. (2) The **pooled** off-diagonal
>   >   class spreads **9.2570%** against a worst intra-class spread of
>   >   0.0199% — a separation of **466.0644×** against the 10× floor, so
>   >   gate (iii) is resolving the adjacent/opposite structure (d0) found,
>   >   not passing on noise.
>   > * **Scope.** Step 3 is ✅ **as measured on the undisplaced mesh**, and
>   >   `PORT-9` stays 🟡 until leg (d1)'s geometric control runs: a symmetry
>   >   gate whose negative control has not been executed is a consistency
>   >   check. §2.2's "no coil has ports" sentence is unmoved for the same
>   >   reason. 10 MHz remains the port model's frequency — no resonance,
>   >   tuning or Larmor claim; `PORT-11` owns 64/128 MHz.
>   > * **Cost note for the review:** commissioned standard at ~60–80 s,
>   >   **measured 66 s / 60 s harness**. The four solves cost 31.56 s
>   >   together (≈ 7.9 s each, leg (d0)'s 7.00–9.19 s grain), the mesh
>   >   21.56 s — leg (d1)'s two-mesh, eight-solve estimate of 120–160 s
>   >   holds.
>   >
>   > **Leg (d1) scoped 2026-08-23 03:00 review — the geometric negative
>   > control of gate (iii).** Add an optional `leg_azimuth_offsets_rad`
>   > (length `leg_count`, default all-zero) to
>   > `MeshGenerator.birdcage_port_domain` / `_birdcage_leg_gap_layout`,
>   > added to `theta` per leg so that **leg 1, its gap, its terminals, its
>   > port box and its sheet all rotate together** by `+π/(2·leg_count)`
>   > (a quarter of the inter-leg spacing) while legs 2–4 and both rings
>   > stay put — the coil itself loses C4, which is what gate (iii) claims
>   > to detect. (Displacing the box *off* its leg, as the 2026-08-16
>   > text literally says, would put the sheet in air facing no terminal —
>   > a degenerate port, not an asymmetric coil; the intent was the
>   > latter.) Gate with the (d) module parametrised on the offsets.
>   > **Anchors:** all-zero offsets reproduce (d)'s 4×4 to ≤ 1e-9
>   > relative (the knob's identity control, the pattern `GEO-18` step 2
>   > used); with port 1 displaced, the {Z_i,i±1} and {Z_i,i+2} class
>   > spreads **exceed 5%** (leg 1 is now 67.5°/112.5° from its
>   > neighbours instead of 90°/90°, so its two adjacent mutuals split by
>   > far more than the 5.9% adjacent-to-opposite separation (d0) measured
>   > at 90° — if the spread stays under 5% the gate is blind and step 3
>   > cannot close on it) **while reciprocity stays ≤ 1e-3**
>   > (route-independent, separating "the gate measures geometry" from
>   > "the solver broke"). **Negative control of the control:** `GEO-9`'s
>   > partition identity and `GEO-18`'s sheet area `dx·g` hold on the
>   > displaced mesh to 1e-9 on all four ports — the mesh is still
>   > conforming and every sheet still spans its gap; the asymmetry is the
>   > only thing that moved. **Cost:** two meshes (~21 s each) + 8 solves
>   > ⇒ ~120–160 s; standard, `-n 2`, `timeout -k 30 500`. **Traps:** the
>   > ring–leg fusion (`GEO-9`) assumes nothing about leg spacing but the
>   > `birdcage_port_layout_diagnostics` clearance check does — read it
>   > before choosing the offset, and shrink the offset rather than the
>   > clearance if it fires; the four-way `TERMINAL_AREA_BAND` check must
>   > still pass on the rotated leg; gmsh state is global, clear between
>   > rungs. **Scope:**
>   > closes `PORT-9` step 3 ✅ and the chunk ✅ with (d) green; nothing at
>   > 64/128 MHz. **Negative result:** spread under 5% on the displaced mesh
>   > ⇒ gate (iii) is not a symmetry gate at this grain — record the
>   > displaced spreads here and in known-issues, `PORT-9` stays 🟡, the
>   > review re-specifies (iii) (tighter band, or a different invariant);
>   > never declare step 3 on (d) alone.
>   >
>   > **Leg (d1) attempt 1, 2026-08-23 07:30 slot — 🟡 the mesh half is
>   > built and green; the solve half did not run.** Parked on
>   > `attempt/PORT-9-d1-20260823T124500Z` at `e5e8a8c`; `main` clean.
>   > `leg_azimuth_offsets_rad` exists on `birdcage_port_domain` /
>   > `_birdcage_leg_gap_layout` as scoped, and
>   > `tests/mesh/test_birdcage_leg_offset.py` reads **`5 passed` / 71.16 s
>   > at `-n 2`** (`20260823T123737Z_PORT-9-step3d1-mesh-rerun.log`).
>   > **Identity control exact:** all-zero offsets give 116 416 cells, the
>   > same cell-tag set and all four sheet areas 1.120000000e-04 m²,
>   > matching the baseline rung digit for digit (the generator skips the
>   > rotation outright at zero, so this is an identity, not a small-angle
>   > limit). **Negative control of the control green on the displaced
>   > rung** (leg 1 at 22.5°, 116 944 cells): P1's sheet centre at
>   > 22.5000° with legs 2–4 unmoved to < 1e-6 °, every port's sheet
>   > meshed/analytic `dx·g` = **1.000000000000** against the 1e-9 band,
>   > `w` = 1.400000000e-02 m and `h` = 8.000000000e-03 m in that port's
>   > *own* radial/axial frame with out-of-plane spread 1.1e-16–2.5e-16 m,
>   > halves partitioning the box to 1.000000000000, terminals 0.989367
>   > (P1) / 0.988616 (P2–P4) inside `GEO-18` step 1's [0.95, 1.0]. **Not
>   > run: the leg's actual anchor** — the zero-offset 4×4 reproducing leg
>   > (d)'s to 1e-9 and the displaced class spreads against 5% — so step 3
>   > and `PORT-9` stay 🟡 and §2.2 is unmoved. Two findings for the next
>   > attempt: the port box and sheet must be built at the *undisplaced*
>   > azimuth and rotated (the generator's `addRectangle` route requires a
>   > coordinate-axis leg), and the lower/upper half-plane convention is
>   > **not** C4-covariant (legs on ±x take upper = +y, legs on ±y take
>   > upper = +x), so the naive φ̂-normal rewrite flips two of leg (d)'s
>   > columns — it is now a (normal, point) pair carrying the old
>   > convention exactly. The solve half also needs frame-aware sheet
>   > narrowing: `_sheet_axes` / `_narrowed_transverse` pick a *global*
>   > axis off the bbox and cannot handle a 22.5° sheet. Journal
>   > 2026-08-23T12:45Z.
>   >
>   > **Leg (d1) attempt 2, 2026-08-23 09:00 slot — 🟡 the solve half ran
>   > end to end and the leg's anchor MISSED on both halves; nothing
>   > widened.** Parked on `attempt/PORT-9-d1-20260823T124500Z` at
>   > `bbe657f`; `main` clean, tests not on it, nothing red in CI.
>   > `tests/validation/test_port_birdcage_leg_offset_sweep.py` builds two
>   > rungs of the same code path (zero offsets 116 416 cells, leg 1 at
>   > +22.5° 116 944 cells) and drives four lumped-sheet solves on each at
>   > `Z_p = z0 = 50 Ω`, 10 MHz — `2 failed, 7 passed` / **119 s** at
>   > `-n 2`, standard tier, `20260823T140422Z_PORT-9-step3d1.log`.
>   > **The identity control passes and makes the comparison controlled:**
>   > all sixteen entries of the zero rung's 4×4 reproduce leg (d)'s record
>   > to **≤ 2.969e-10** relative against the 1e-9 band, with
>   > `‖S−Sᵀ‖/‖S‖` = 2.495292352e-05 and `σ_max` = 0.862659137 identical to
>   > nine digits — the knob and the frame-aware narrowing this leg added
>   > (`_narrowed_radial`, the midpoint filter along the port's own radial
>   > direction, reducing term by term to leg (c)/(d)'s global-axis one on a
>   > coordinate-axis leg) do not move the solve.
>   > **Miss 1 — gate (iii) is blind on one class.** Displaced spreads
>   > **self 5.1819% / adjacent 7.1147% / opposite 1.6476%** against the
>   > unmoved 5% band (symmetric rung 0.0199 / 0.0180 / 0.0108%;
>   > amplification 260.89× / 395.76× / 152.49×). Adjacent detects the
>   > broken C4 by 1.42×; **opposite does not**, and the anchor required
>   > both. Geometric in direction: 22.5° moves P1–P3 from 180° to 157.5°
>   > while P2–P4 stays 180°, and (d0) measured only 5.9% across the whole
>   > 90°→180° span, so the opposite pair is perturbed on a flat part of
>   > the coupling curve.
>   > **Miss 2 — the route loses reciprocity when the layout does.**
>   > Displaced `‖S−Sᵀ‖/‖S‖` = **5.570640234e-03** vs the unmoved 1e-3
>   > (`‖Z−Zᵀ‖/‖Z‖` = 7.440778193e-03), **223×** the symmetric rung on the
>   > same code path; `σ_max` = 0.865743230, still passive. Reciprocity is a
>   > material property, so this is a route/discretisation systematic — and
>   > it is the half of the anchor that separates "the gate measures
>   > geometry" from "the solve broke", so the displaced spreads above
>   > cannot be read as pure geometry while it stands. One measured
>   > asymmetry tracks it, offered as hypothesis not diagnosis: the
>   > interior-width filter keeps **26** facets on the rotated sheet against
>   > **27** elsewhere, so P1's `w = A/h` is 7.272128105e-03 m against
>   > 7.413268623e-03 m — a 1.9% width difference entering
>   > `sheet_width_m` and hence the V/I estimate, which cancels exactly on
>   > the symmetric rung where all four sheets are identical.
>   > **The negative control of the control is green on both rungs** —
>   > every sheet a full rectangle at `dx·g` = 1.120000000e-04 m²,
>   > meshed/analytic **1.000000000000**, planar to ≤ 1.7e-17 m in its own
>   > port frame — so neither miss is a broken port. **`PORT-9` stays 🟡
>   > and §2.2 is unmoved**; per this leg's negative-result clause the
>   > review re-specifies gate (iii) and disposes of the reciprocity
>   > finding. Both are in known-issues (entry «Gate (iii) is blind to a
>   > broken C4 on the *opposite* class…»). Journal 2026-08-23T14:10Z.
>   >
>   > **Ruling, 2026-08-23 10:30 review — the width hypothesis is refuted
>   > by the run's own numbers; finding 2 is a route systematic the
>   > symmetric fixtures have been hiding; gate (iii) is re-specified at
>   > 0.5%; a diagnostic leg (d2) is scoped ahead of any (d1) re-run.**
>   > * **Finding 2's hypothesis does not survive arithmetic.** If P1's
>   >   1.9% narrower sheet (`w` 7.272 vs 7.413 mm) entered the V/I estimate
>   >   asymmetrically, every `Z₁ⱼ/Zⱼ₁` would carry the common factor
>   >   0.98096 (or its inverse) and the three pairs not involving P1 would
>   >   stay at 1. From the displaced Z printed at
>   >   `20260823T140422Z_PORT-9-step3d1.log:9327-9330`:
>   >
>   >   | pair | `|Z_ij/Z_ji|` | phase | `|Z_ij − Z_ji| / |mean|` |
>   >   |---|---|---|---|
>   >   | 1–2 | 0.99589 | −0.288° | 0.650% |
>   >   | 1–3 | 1.00109 | +0.105° | 0.213% |
>   >   | 1–4 | 1.00625 | +0.447° | 0.999% |
>   >   | 2–3 | 1.00523 | +0.392° | 0.861% |
>   >   | **2–4** | **1.01041** | +0.735° | **1.648%** |
>   >   | 3–4 | 1.00515 | +0.343° | 0.788% |
>   >
>   >   No common factor on row/column 1, and the **worst pair is P2–P4 —
>   >   neither port moved**. The 1.9% width asymmetry is real but is not
>   >   the mechanism (Frobenius 7.44e-03 recomputed from the table,
>   >   matching the log). What the table says instead: the asymmetry is
>   >   **global and of order the discretisation**, ~0.2–1.6% on every
>   >   pair, on a mesh that gmsh regenerated whole when one leg moved
>   >   (116 416 → 116 944 cells). A Galerkin curl-curl solve with a
>   >   symmetric bilinear form is *discretely* reciprocal — on any mesh —
>   >   **iff the voltage readout is the same functional as the impressed
>   >   source**. A readout that is not the source's adjoint (e.g. source
>   >   impressed on one facet set, `V` averaged over another, or a
>   >   path-type readout) gives `Z − Zᵀ` of order the local discretisation
>   >   error, which **cancels exactly when every port sees the same local
>   >   mesh** — which is every fixture this route has ever been measured
>   >   on: the two identical tori (2c: 2.6e-11), the C4 birdcage (d:
>   >   2.5e-05). **So the route's reciprocity has only ever been tested
>   >   where symmetry enforces it, and step 2c's 2.6e-11 is evidence of a
>   >   symmetric fixture, not of a reciprocal discretisation.** That is
>   >   the finding this review files; the hypothesis is named A below and
>   >   leg (d2) decides it.
>   > * **Gate (iii) re-specified — (iii′): each class spread ≤ 0.5%.** The
>   >   5% was pre-stated 2026-08-16 before any coil number existed. The
>   >   measured symmetric floor is 0.0108–0.0199% (leg (d); 0.0152–0.0159%
>   >   on (c)/(d0)), and the weakest measured geometric response is the
>   >   opposite class at 1.6476% under a 22.5° rotation — a quarter of the
>   >   leg pitch. A band that cannot see that on one of its classes is not
>   >   a symmetry gate. 0.5% sits **25× above the floor and 3.3× below the
>   >   weakest displaced class**; it is a tightening, which the standing
>   >   rule permits, and every symmetric reading already taken satisfies
>   >   it, so **leg (d) stays ✅ under (iii′) without a re-run** (the test
>   >   file's band moves with the (d1′) commit). Stated honestly: 0.5% is
>   >   set from these two measurements after seeing them, so the (d1′)
>   >   re-run is the first *test* of the band, not a confirmation — and
>   >   the displaced spreads it will read are only creditable as geometry
>   >   after (d2) has disposed of hypothesis A, because a 0.2–1.6%
>   >   per-pair route asymmetry is the same order as the 0.5% band. The
>   >   opposite class is physically the flattest under any single-leg
>   >   rotation (P2–P4 stays at 180°; (d0) measured 5.9% across the whole
>   >   90°→180° span); if its post-(d2) spread comes under 0.5%, that is
>   >   reported and the review rules whether the opposite class belongs in
>   >   the geometric control at all — never widen (iii′).
>   > * **Leg (d2) scoped — reciprocity of the lumped-sheet route on an
>   >   *asymmetric* two-port (standard, `-n 2`, complex, `main`).**
>   >   Fixture: step 2b/2c's two-torus, sheets on both ports, **`f = 0.5`
>   >   on port 1 and `f = 0.735` on port 2** — both widths are rungs of
>   >   2b's ladder, so no new geometry and each width's readout is already
>   >   on record (cross-route 1.8333% / 3.6730%). **Step 0, before any
>   >   solve, journaled:** read `run_n_port_sparameter_sweep`'s lumped-sheet
>   >   route and state in one paragraph whether the `V` readout functional
>   >   is the impressed source's adjoint — same facet set, same weighting —
>   >   and if not, what differs (full-sheet source vs narrowed readout is
>   >   the obvious candidate, since narrowing was introduced at step 2b as
>   >   a *readout* change). **Anchors, pre-registered:** (a) control —
>   >   `f = 0.5 / 0.5` reproduces 2c's `‖S−Sᵀ‖/‖S‖` = 2.574249e-11 to
>   >   ≤ 1e-9 absolute; (b) asymmetric — `‖S−Sᵀ‖/‖S‖` against the unmoved
>   >   1e-3, printing `|Z₁₂/Z₂₁|` and its phase to nine digits.
>   >   **Predictions, so either outcome is a finding:** under **A** (readout
>   >   not adjoint) the asymmetric two-port reads O(1e-2) — 2b measured
>   >   the readout moving 1.84 pp between exactly these two widths, and
>   >   that difference does not cancel when the ports differ; under **B**
>   >   (route discretely reciprocal) it reads ≤ 1e-9 like the control, and
>   >   the birdcage's 5.6e-03 is then *birdcage-specific* — the
>   >   non-C4-covariant half-plane `(normal, point)` convention attempt 1
>   >   found, or the terminal halves — and a leg (d3) on the birdcage
>   >   follows. **Cost:** 2c's two-port sweep was 122 s for 7 tests; two
>   >   sweeps ≈ 250 s; `timeout -k 30 500`. **Traps:** complex build +
>   >   `FEM_EM_REQUIRE_COMPLEX=1` + `tests/environment` first; the sweep
>   >   errors on gap-spec + sheet-spec together; if `LumpedSheetPortSpec`
>   >   cannot take a per-port width fraction, add the field — do **not**
>   >   merge `attempt/PORT-9-d1-*`'s `_narrowed_radial` for this (the
>   >   two-torus sheets are coordinate-axis, 2c's route suffices); 0-byte
>   >   `.c` stubs; `-s` to see the prints. **Scope:** closes nothing;
>   >   disposes finding 2 one way or the other. **Negative result:** both
>   >   outcomes are the measurement — §7 annotation and the known-issues
>   >   entry updated with which hypothesis stood. **Flagged now:** if A
>   >   stands, the fix is a readout change that **moves the 2b/2c/(c)/(d0)/
>   >   (d) records** (1.8333%, 0.894141, the 4×4 digits) — a class
>   >   re-record on the (1\*) pattern, to be ruled when the fix is scoped,
>   >   never done in-slot.
>   > * **Leg (d2) executed 2026-08-23, 13:30 slot — A is refuted, A′ stands:
>   >   the readout is the source's adjoint and the asymmetry is the
>   >   terminated-`Z` assembly.** Two sweeps on one 184 919-cell two-torus
>   >   mesh (`test_port_lumped_sheet_asymmetric.py`, `9 passed` / 198 s and
>   >   191 s at `-n 2`, complex, standard;
>   >   `20260823T183434Z_PORT-9-step3d2.log`,
>   >   `20260823T183823Z_PORT-9-step3d2-repeat.log`, both runs identical to
>   >   8–10 digits). **Step 0, journaled before the solves** (module
>   >   docstring): the source of port *j* is built from
>   >   `f_j[k] = ∫_{S_j} ĥ_j·v_k dS` and the current readout of port *i* is
>   >   `(1/(R_i h_i)) f_iᵀx` — **same facet set, same weighting, same
>   >   vector** — so on a complex-symmetric operator `I_i(drive j)` =
>   >   `I_j(drive i)` exactly, on any mesh; what is not adjoint-consistent is
>   >   one level up, `Z_ij = V_i/I_j` with every port *terminated*, which is
>   >   not the open-circuit matrix reciprocity makes symmetric. **Anchor (a)**
>   >   control `f` = 0.5/0.5: `‖S−Sᵀ‖/‖S‖` = **2.574356760e-11**, 1.078e-15
>   >   from step 2c's record, inside the 1e-9 band. **Anchor (b)** asymmetric
>   >   `f` = 0.5/0.735 (`w₂/w₁` = 1.472822047): **8.255602536e-09** — 320.7×
>   >   the control but five orders **inside** the unmoved 1e-3, so
>   >   **prediction B at the Frobenius grain and A's O(1e-2) does not
>   >   happen**; `|Z₁₂/Z₂₁|` = 0.997537168, phase −0.020146017°.
>   >   **Mechanism, both halves asserted at a pre-stated 1e-6 and both
>   >   green:** (i) `I₁(d2)` = `I₂(d1)` to **1.33e-10** (the readout *is* the
>   >   adjoint — A refuted at its own mechanism, not merely by its number);
>   >   (ii) `Z₁₂/Z₂₁` = `I₁(d1)/I₂(d2)` to **1.33e-10** — the whole `Z`
>   >   asymmetry is the per-column normalisation by the driven port's own
>   >   current. **The reading that matters is per-pair, not Frobenius:** 0.25%
>   >   here, the same order as (d1)'s 0.2–1.6% table; the Frobenius ratio
>   >   hides it because at `Z_p` = 1e6 Ω the kΩ diagonal drowns the 1.13 Ω
>   >   mutuals, while the birdcage's 50 Ω termination puts `Z₁₁` ≈ 21.7 Ω
>   >   beside 17 Ω mutuals and the same per-pair asymmetry surfaces as
>   >   5.57e-03. **So (d1)'s miss is neither a discretisation residual nor
>   >   birdcage-specific — it is the assembly, made visible by a matched
>   >   termination**, and step 2c's 2.6e-11 measured a fixture whose ports
>   >   have equal self-currents. Closes nothing; finding 2 of the (d1)
>   >   known-issues entry is disposed. **Owed to a review:** the fix is an
>   >   assembly change (open-circuit `Z`, or `S` straight from power waves as
>   >   `_assemble_sparameter_matrix` already does — on a matched termination
>   >   `a_i` = 0 at every undriven port, so `S_ij ∝ I_i/V_src` is symmetric by
>   >   the identity (i) just measured) and it moves the 2b/2c/(c)/(d0)/(d)
>   >   records — a class re-record, never done in-slot.
>   > * **Leg (d1′) — the re-run — is serial on (d2)** and is not queued
>   >   until the review has (d2)'s number: on the fixed route if A, on the
>   >   parked branch's sweep module if B (then with a (d3) first). Its
>   >   anchors when it runs: zero rung reproduces the then-current 4×4 to
>   >   1e-9; displaced, all three class spreads **> 0.5%** (iii′) *while*
>   >   `‖S−Sᵀ‖/‖S‖ ≤ 1e-3`; the symmetric rung's spreads ≤ 0.5%. The
>   >   branch stays parked; its mesh knob and `tests/mesh/
>   >   test_birdcage_leg_offset.py` (`5 passed`, identity exact) are the
>   >   useful content and land with (d1′), not before.
>   > * **Ruling (2\*), 2026-08-23 18:00 review — the fix is the power-wave
>   >   S assembly, scoped as legs (d3) and (d3b).** The gated field routes
>   >   (gap-voltage *and* lumped-sheet) assemble the terminated `Z` and
>   >   push it through `sparameters_from_impedance`
>   >   (`ports/sparameters.py:328-329`), which assumes the open-circuit
>   >   matrix — their S inherits the terminated-`Z` asymmetry *and* a
>   >   conversion bias, which is why `PORT-1`'s records are in the class.
>   >   Fix: assemble S from power waves directly (`_power_waves` /
>   >   `_assemble_sparameter_matrix`, today reachable only from the
>   >   deprecated heuristic path) — `S_ij = b_i/a_j` with `a_j` =
>   >   `V_src/(2√z0)` at a matched drive, symmetric by mechanism identity
>   >   (i). Open-circuit `Z` **rejected**: leg (c) measured the 1e6 Ω
>   >   column as near-degenerate, so that assembly gates on the regime the
>   >   (d0) study showed is fragile. The terminated `Z` stays as a
>   >   documented diagnostic, never reciprocity-gated. Class re-record
>   >   (2b/2c/(c)/(d0)/(d) + `PORT-1` consumers) on the (1\*) pattern —
>   >   route-tagged beside the old digits, bands unmoved, (b′) arithmetic
>   >   journaled — split as **(d3)** two-torus (§9 item 2, with the
>   >   50 Ω asymmetric two-torus as the mechanism's own negative control:
>   >   old conversion ≥ 1e-4, fixed route ≤ 1e-6) and **(d3b)** birdcage
>   >   (§9 item 4). **(d1′) is serial on (d3b)** and stays a review's to
>   >   queue from (d3b)'s digits.
>   > * **Leg (d3b) executed 2026-08-24, 04:30 slot — all three gates pass on
>   >   the birdcage's fixed route, and the re-record turns out to have a
>   >   second cause the ruling did not know about (🟡, one ruling owed).**
>   >   Three modules (legs (c), (d0), (d)) re-run whole on `main`, complex,
>   >   `-n 2`, twice in-slot: `2 failed, 17 passed` at 121.4 s and 112.7 s
>   >   (`20260824T093133Z_PORT-9-step3d3b-run1.log`,
>   >   `20260824T093526Z_PORT-9-step3d3b-run2.log`; harness 124 s / 114 s).
>   >   **Anchor (i) lands as pre-registered, orders below leg (d):**
>   >   `‖S−Sᵀ‖/‖S‖` = **8.244846162e-15** (run 1) / **1.161493453e-14**
>   >   (run 2) against the unmoved 1e-3 band and against the terminated
>   >   conversion's 2.495292352e-05 — a **~2.5e+9×** improvement, the
>   >   birdcage confirmation of ruling (2\*). The two runs differ in this
>   >   digit alone, at 1.4× of each other: `S` is symmetric to the float
>   >   floor, so the *ratio* is noise over noise and reproduces only in
>   >   order of magnitude — everything else below is bit-identical across
>   >   the two runs. **(ii)** `σ_max(S)` = **0.999993391** ≤ 1 + 1e-9
>   >   (leg (d)'s conversion read 0.862659137), column power sums
>   >   0.807772326 / 0.807647060 / 0.807688415 / **0.808049459** ≤ 1.
>   >   **(iii′)** the C4 class spreads of the diagnostic `Z` read **0.0617%
>   >   self / 0.0359% adjacent / 0.0237% opposite**, inside the tightened
>   >   0.5% (iii′) as well as the module's unmoved 5%; class means
>   >   |Z| = 2.297360911e+01 / 1.701075777e+01 / 1.605637772e+01 Ω, pooled
>   >   off-diagonal 9.2727% = **150.3584×** the worst intra-class spread
>   >   (floor 10×). Leg (d0)'s discrimination margin re-measured at
>   >   **253.2002×** (record 598.4002×), its adjacent spread 0.0359%
>   >   (record 0.0152%), the 1e6 Ω control at 6.9398× / 0.0039%.
>   >   `‖Z−Zᵀ‖/‖Z‖` = 9.852810597e-05 — the terminated `Z` keeps its
>   >   asymmetry, as (d3) demoted it to a diagnostic.
>   >   **The finding: the birdcage mesh moved with the image, so the
>   >   re-record is not single-cause.** All three modules print **116 368
>   >   cells against the record's 116 416** (ratio 0.999588), and the two
>   >   `Z` reproduction controls fail on that: leg (c)'s driven current at
>   >   6.829e-06 and leg (d0)'s `Z₁₁` at 1.449e-04 relative, against
>   >   1e-9 print-precision bands. The route cannot be the cause — legs (c)
>   >   and (d0) never call the sweep's S assembly, and (d3) touched only
>   >   `_assemble_sparameter_matrix` — and the tag encoding is excluded by
>   >   `0f8ea96`'s own 116 368 measured before *and* after its change. What
>   >   is left is the `OPS-18` step 3b image (the birdcage records are all
>   >   pre-0.11), the same 1e-4 motion the retired 0.11 known-issues entry
>   >   recorded for the two-torus family. Every geometric identity holds on
>   >   the moved mesh (sheet area 5.930614898e-05 m², `h` = 8.000000000e-03
>   >   m exactly, out-of-plane 8.882e-19 m, four identical sheets).
>   >   **Nothing was re-recorded and no band moved**: ruling (4\*)'s whole
>   >   sequencing rests on one cause per re-record, and this is a third,
>   >   earlier cause it did not know about, so the image-tagged birdcage
>   >   re-record is **owed to a review** (the digits above are what it would
>   >   write). Known-issues entry filed for the two red controls. `PORT-9`
>   >   stays 🟡; (d1′) still unqueued. **Ruling (5\*) (2026-08-24 10:30
>   >   review) grants the re-record** — image-tagged for the two
>   >   reproduction controls (single measured cause), (1\*) in-class for
>   >   the moved diagnostics, image+route-tagged for any new fixed-route
>   >   S record (the 0.10 image is gone, the split is unmeasurable) —
>   >   executed as leg (d3c), §9 item 1; full text in §9.
>   > * **Leg (d3c) executed 2026-08-24, 12:00 slot — ruling (5\*) carried
>   >   out: the birdcage records now live on the image `main` boots, and the
>   >   two red reproduction controls are green (🟡, (d1′) still owed).**
>   >   The edits, all digits taken from (d3b)'s two bit-identical runs:
>   >   leg (c)'s `I₁` = **+9.992781266e-07 + 3.346865998e-09j A** and its
>   >   1e6 Ω `Z` column (`Z₁₁` = +7.111692404e+02 − 3.351665665e+03j,
>   >   `Z₂₁` = +1.224919287e+01 − 1.878346946e+03j, `Z₃₁` =
>   >   +1.193721196e+01 − 1.878700877e+03j, `Z₄₁` = +1.231338434e+01 −
>   >   1.878312313e+03j Ω) **image-tagged**; leg (d0)'s 50 Ω column
>   >   (`Z₁₁` = **+2.172952668e+01 + 7.461413742e+00j**, `Z₂₁` =
>   >   +1.700667611e+01 + 2.379070919e-01j, `Z₃₁` = +1.602683719e+01 −
>   >   9.541994594e-01j, `Z₄₁` = +1.701267933e+01 + 2.390098116e-01j Ω)
>   >   **image-tagged**; the fixture's cell record 116 416 → **116 368**
>   >   (`GEO-18` step 2's count on the 0.11 image; its 2% band unmoved, and
>   >   all three modules now print ratio 1.000000); the moved in-class
>   >   diagnostics under (1\*) (margin 253.2002×, adjacent spread 0.0359%,
>   >   class means 2.297360911e+01 / 1.701075777e+01 / 1.605637772e+01 Ω);
>   >   and the fixed-route S digits recorded **image+route-tagged** in leg
>   >   (d)'s module docstring, the joint tag stated as unmeasurable-by-any-
>   >   future-run rather than split. Every pre-0.11 digit is kept beside its
>   >   replacement in the same comment. **Verification — the three modules
>   >   re-run whole, twice in-slot: `19 passed` both times**, 115.7 s and
>   >   113.2 s (harness 118 s / 115 s;
>   >   `20260824T170332Z_PORT-9-step3d3c-run1.log`,
>   >   `20260824T170544Z_PORT-9-step3d3c-run2.log`). **Negative control —
>   >   within-run reproduction of every edited record**: leg (c)'s `I₁` at
>   >   4.211e-11 / 4.212e-11 and its `Z` column at ≤ 2.360e-10, leg (d0)'s
>   >   column at ≤ 1.452e-10, all against the 1e-9 print-precision band, and
>   >   no digit differs from (d3b)'s — the mesh did not move again. **The
>   >   gates re-confirmed on the re-recorded constants:** (i) `‖S−Sᵀ‖/‖S‖`
>   >   = 1.152855902e-14 / 4.557532901e-15 vs 1e-3 (the order-of-magnitude
>   >   quantity (d3b) named, spanning 4.6e-15–1.2e-14 across the four runs
>   >   now on record); (ii) `σ_max(S)` = 0.999993391, max column power sum
>   >   0.808049459; (iii) class spreads 0.0617 / 0.0359 / 0.0237% vs the
>   >   module's unmoved 5%, pooled separation 150.3584× vs the 10× floor;
>   >   (d0)'s margin 253.2002× vs 10×. No band or gate was moved. The
>   >   known-issues "two birdcage reproduction controls" entry retires with
>   >   this commit. `PORT-9` stays 🟡 — (d1′) is the closing leg and only a
>   >   review queues it; §9 item 2 (`GEO-19` step B) is unblocked.
>   > * **Leg (d1′) mesh half executed 2026-08-25, 04:30 slot — the layout
>   >   knob is on `main` and exact; the solve half did not fit the slot.**
>   >   `leg_azimuth_offsets_rad` (one angle per leg, added to that leg's
>   >   azimuth) now reaches `birdcage_port_domain`, `_birdcage_leg_gap_layout`
>   >   (so the pairwise centre-separation floor sees the displaced spacing)
>   >   and `_build_birdcage_port_model`. It is a **much smaller change than
>   >   the parked attempt's**: `GEO-19` step B already built each box and
>   >   sheet in the leg's own local frame and rotated it onto its azimuth, so
>   >   the knob is one added vector of azimuths (`theta_leg`) and no geometry
>   >   kernel work — the attempt branch's rigid-rotation and
>   >   (normal, point) rewrites are superseded on `main`, not re-landed.
>   >   `tests/mesh/test_birdcage_leg_offset.py`, `6 passed 81.42 s` at `-n 2`
>   >   real (`20260825T093515Z_PORT-9-step3d1-mesh.log`, harness 84 s).
>   >   **Identity control (exact):** the all-zero build meshes **116 085**
>   >   cells — step B's mesh-tagged record digit for digit — with the same
>   >   global cell-tag set and the same four sheet areas as the no-kwarg
>   >   baseline; the offsets are *added*, and adding an exact zero is exact,
>   >   so this is an identity and not a small-angle limit. **Displaced rung**
>   >   (leg 1 at `π/(2·leg_count)` = 22.5°): 116 475 cells, P1's sheet centre
>   >   at 22.5000° while P2/P3/P4 stay at 90/180/270° to < 1e-6°, and every
>   >   `GEO-18` identity survives the rotation — sheet area
>   >   `1.120000000e-04 m²` = analytic `dx·g` at **1.000000000000** on all
>   >   four, out-of-plane spread ≤ **1.610e-17 m** in each port's *own*
>   >   azimuthal direction, terminals 0.989368 / 0.988616 ×3 inside `GEO-18`
>   >   step 1's [0.95, 1.0], box halves 0.500000000000 each summing to
>   >   1.000000000000. Three refusals gated: offsets without `leg_gap_length`,
>   >   offsets with `ring_gap_length` (the `GEO-20` arcs are centred on the
>   >   *uniform* mid-azimuths, which a displaced leg no longer bisects), and a
>   >   wrong-length offset vector. **Not done, and what (d1′) still owes:** the
>   >   displaced 4×4 through the (d3) power-wave assembly, its reciprocity and
>   >   class-spread anchors, and the (iii′) 5% → 0.5% tightening — the
>   >   tightening is deliberately *not* committed here because proving the
>   >   existing consumers green at 0.5% is its own compute run. No band moved,
>   >   no assertion loosened, no S-parameter or reciprocity claim in this
>   >   commit; `PORT-9` stays 🟡. The solve half needs a frame-aware sheet
>   >   narrowing (`_narrowed_transverse` picks a *global* axis off the bounding
>   >   box and cannot name the transverse direction of a sheet at 22.5°) —
>   >   the parked branch's `_narrowed_radial` / `_projected_extents` are the
>   >   ready adaptation, and `attempt/PORT-9-d1-20260823T124500Z` stays parked
>   >   for exactly that payload.
>   > * **Leg (d1′) solve half executed 2026-08-25, 06:00 slot — the
>   >   geometric negative control passes on the power-wave route, and
>   >   `PORT-9` closes ✅ at 10 MHz.**
>   >   `tests/validation/test_port_birdcage_leg_offset_sweep.py` (adapted
>   >   from the parked branch onto `main`'s landed mesh knob; the retired
>   >   open-limit anchors did **not** come back and the branch's
>   >   `LEG_D_Z_MATRIX` reproduction anchor is replaced by leg (d0)'s
>   >   terminated column, imported from `test_port_birdcage_four_port.py`
>   >   per (6\*)(v)). Two rungs, **eight driven lumped-sheet solves** at
>   >   `Z_p = z0 = 50 Ω`, 10 MHz, `f = 0.5`, `w = A/h`, with each sheet
>   >   narrowed along its **own radial direction** (`_narrowed_radial`) —
>   >   `_narrowed_transverse` picks a global axis and cannot narrow a
>   >   sheet at 22.5°. `13 passed 106.64 s` at `-n 2`, complex, standard
>   >   tier (`20260825T110438Z_PORT-9-step3d1.log`, harness 108 s; meshes
>   >   22.71 / 22.89 s, sweeps 25.75 / 27.84 s).
>   >   **Anchor (a), the identity control — the zero rung *is* leg (d)'s
>   >   solve:** 116 085 cells at ratio **1.000000**, leg (d0)'s terminated
>   >   column reproduced to ≤ **2.568e-10** relative on all four entries,
>   >   `σ_max(S)` = **0.999992805** to 4.065e-10, and the three class
>   >   spreads **0.0553 / 0.0353 / 0.0214%** — step B's records digit for
>   >   digit, all inside (iii′). **Anchor (b), reciprocity on an
>   >   asymmetric 3D fixture — the first test of the (d3) fix outside a
>   >   symmetric or 2D layout:** displaced `‖S−Sᵀ‖/‖S‖` = **2.259e-14**
>   >   (order of magnitude only, per (d3c); the confirm run read 6.846e-14
>   >   and the zero rung 1.044e-14 / 8.660e-15) against the unmoved 1e-3,
>   >   with `σ_max` = 0.999992337 ≤ 1 + 1e-9. The **pre-fix negative
>   >   control** is decisive: the terminated-`Z` route read **5.57e-03** on
>   >   this exact displaced fixture (`20260823T140422Z_PORT-9-step3d1.log`),
>   >   so the separation is **2.466e+11×** against the (d3) ruling's ≥ 100×
>   >   bar — leg (d1)'s miss was the assembly, and it is gone.
>   >   **Anchor (c), the leg's substance — gate (iii′) sees the broken
>   >   C4:** with leg 1 rotated 22.5° the gated classes break 0.5% by two
>   >   orders, self **6.2219%** (112.58× amplification over the symmetric
>   >   rung) and adjacent **7.1142%** (201.52×). The opposite class was
>   >   pre-ruled *reported, not gated* (physically the flattest under a
>   >   single-leg rotation); it read **2.8474%** (133.11×) and **also
>   >   exceeds** the band — so on this fixture all three classes respond
>   >   and the review's open question about whether the opposite class
>   >   belongs in the geometric control is answered affirmatively by
>   >   measurement. Every sheet the displaced rung solved on is still the
>   >   clean `GEO-18` construction (full-sheet `dx·g` ratio inside 1e-9,
>   >   out-of-plane spread < 1e-12 m in each port's own frame), so no
>   >   spread above is a broken port.
>   >   **(iii′) committed: `ADJACENT_SPREAD_BAND` 5% → 0.5%** at its single
>   >   source in leg (c)'s module, with **all three consumers re-run green
>   >   under the new value in the same slot** — leg (c) 0.0407%, leg (d0)
>   >   0.0040% and margin 2256.9707×, leg (d)'s three classes 0.0553 /
>   >   0.0353 / 0.0214% with separation 166.6766×, plus this module's
>   >   confirm run: `24 passed 222.15 s`
>   >   (`20260825T110643Z_PORT-9-step3d1-consumers.log`, harness 224 s).
>   >   It is a **tightening**; no band was widened and no assertion
>   >   loosened anywhere in this commit.
>   >   **Scope.** `PORT-9` ✅ **at 10 MHz on this gated fixture** — four
>   >   lumped-sheet ports on the gapped, sheeted 4-leg birdcage, gates
>   >   (i)/(ii)/(iii′) green with their geometric negative control. No
>   >   Larmor claim, no resonance or tuning claim, and no S-parameter
>   >   claim beyond this fixture and the two-torus one; `PORT-11` step 1
>   >   is unblocked. `attempt/PORT-9-d1-20260823T124500Z` deleted — both
>   >   halves of its payload are now on `main`, green from `main`.

**`PORT-10` — the two `PORT-1` systematics: composition measured, not
assumed** ✅ *(scoped 2026-08-16, weekly planning review — the first of the
two §9-hold questions; **closed 2026-08-16, 09:00 slot**.)* The PEC-box correction (`D∞ = +0.0169` at
`p = 1.657`, an effective-range extrapolation) and the gap-physics
correction (`÷(1 − 0.030224)`, Jin 3e §10.4.2.1) were each measured in
isolation; `ports/systematics.py` composes them multiplicatively, and that
composition is untested (§7 `PORT-1` standing cautions). Design: 2×2
factorial on the two-torus fixture — {baseline, +1 padding rung} ×
{baseline, gap h-refined rung (the 3b-xvi mesh)} — four solves, one
command. **Gate:** the cross-term (deviation of the jointly-measured
`Im Z₁₂/ωM₁₂` shift from the sum of the two individually-measured shifts)
within a pre-stated **±0.5 pp** band, the 3b-xvi grain. **Negative
result:** a cross-term outside the band is a finding — annotate
`systematics.py`'s quotation rule, open a known-issues entry, report,
stop; never widen. **Tier:** heavy — cost-probe first (`EX-20`'s pair is
178 s at `-n 2`; the padded and refined rungs cost more), single command
under the 1200 s ceiling or the case shrinks. `ANS-3`'s AED comparison is
the independent adjudication input for the same question (§5.4).
>
> **Result (2026-08-16, `tests/validation/test_port_systematics_composition.py`,
> 7 passed 352.4 s at `-n 2`, `20260816T140643Z_PORT-10.log`).** Cost probe
> first, as the entry required: the two unmeasured padded corners mesh at
> 194 985 and **263 751** cells, inside 3b-xvi's 350 000 stop rule, 95 s
> (`20260816T140457Z_PORT-10-costprobe.log`) — the gate was then sized from
> that measurement, not from an extrapolation. Each systematic is driven by
> its own knob (`air_padding` for the PEC box, gap-box `h_box` for the
> gap/feed term) and each corner is one mesh + one solve reading the
> terminal-to-terminal estimator on the undriven port, gap 101 driven,
> `I_cond` normalisation — 3b-xvi's own lean path. Corner ratios ×ωM₁₂:
> base **0.894543**, padded 0.924103, refined **0.895051**, joint 0.924007.
> Shifts off base: PEC box **+2.9559 pp** (0.08 → 0.10), gap/feed
> **+0.0508 pp** (reproducing 3b-xvi's +0.0508 pp), joint +2.9464 pp against
> a sum of parts +3.0067 pp ⇒ **cross-term X = −6.037e-04 = −0.0604 pp**,
> inside the pre-stated ±0.5 pp by **8.3×**. The two knobs' effects add at
> this grain, so measuring each with the other at baseline — how both
> systematics were in fact measured — is legitimate, and the sequential
> ladder in `ports/systematics.py` carries no interaction error resolvable
> here. **Anchors:** both baseline corners reproduce their records to
> **+2.979e-07** and **+1.536e-07** against a 0.1 pp band, so the lean path
> is the record's quantity. **Negative controls, both executed in-run on the
> same arithmetic:** a joint corner displaced +1.0 pp gives X = +0.9396 pp
> and the wedge-only estimator (0.493653, the integral that misses the
> buried gap arc) gives X = −43.0958 pp — both asserted to fail the band.
> **Scope of the claim:** `Δ_box` is one finite padding step, not the
> `W → ∞` extrapolation `D∞`, and `Δ_feed` probes the gap term through feed
> discretisation, not the gap physics itself; the factorial tests the
> *separability* of the two measurements, not the extrapolations layered on
> them. Nothing in `systematics.py` or `MUTUAL_TOLERANCE` moved. `PORT-9`
> step 3's prerequisite from this side is discharged (`GEO-15` is the other).

**`PORT-11` — lumped-sheet ports on the gapped birdcage at the Larmor
frequencies: the 64 MHz port gate** ⬜ *(commissioned 2026-08-23 weekly
review as §10 subgoal 2b — the birdcage half of `PORT-9` closes at 10 MHz,
the two-torus records' frequency, and the mission's ports are at 64/128 MHz.
**Serial on `PORT-9` ✅** — step 3 leg (d)'s gates (i)–(iii) on the 4×4 at
10 MHz must exist before a frequency is changed; do not start earlier.)*
**Scope:** the same code path — `run_n_port_sparameter_sweep`, lumped-sheet
route, `GEO-18` step-2 fixture (116 416 cells at `conductor_resolution =
1.6e-3` when this was written; **the mesh-tagged record is now `GEO-19`
step B's 116 085** — noted 2026-08-25 10:30 review; four `f = 0.5` sheets,
`Z_p = z0 = 50 Ω` per leg (d0)), phantom at
the `TH-10` saline values (σ, εᵣ at 64 MHz) — at **64 MHz** first, 128 MHz
as a second leg only if 64 MHz gates. Nothing new is formulated; what is
measured is whether the port model and mesh survive the displacement-current
regime on the loaded birdcage. Cost-probe-first is binding (`PORT-9` leg
(c) precedent: 7.55 s/solve at 10 MHz; MUMPS cost is mesh-bound, not
frequency-bound, so four solves should price near leg (d)'s ~30 s — *measure
it*, the phantom's cells/δ and cells/λ are what change).
> * **Step 1 (probe, 🧪) — one 64 MHz solve, priced.** Print: cells/δ
>   in the phantom (δ at the `TH-10` σ) and cells/λ in air, wall, summed
>   `ru_maxrss`, `|Im P|/Re P`, and column 1 of Z; reproduce `PORT-9` leg
>   (d0)'s 10 MHz column on the same mesh/code path to `1e-6` relative as the
>   in-run anchor (the frequency is the only knob turned). Standard, `-n 2`.
>   **Stop rule:** cells/δ in the phantom below ~2 at this mesh is a
>   resolution finding, not a band to widen — record it, and the next item
>   is a `GEO` sizing chunk for the phantom, not step 2.
> * **Step 2 (gate) — the 4×4 at 64 MHz.** `PORT-9` step 3's three gates,
>   unchanged and pre-stated: (i) reciprocity `‖S−Sᵀ‖/‖S‖ ≤ 1e-3`; (ii)
>   passivity `σ_max(S) ≤ 1 + 1e-9`, unit column power sums ≤ 1; (iii) C4
>   circulant class spread ≤ 5% on Z. Plus the frequency control: the 10 MHz
>   sweep re-run in the same command reproduces leg (d)'s recorded S to
>   `1e-6`. **Negative control:** `PORT-9`'s displaced-port-box mesh at
>   64 MHz — class spread must blow through 5% while (i) stays ≤ 1e-3.
>   Heavy tier (priced by step 1), `-n 2`. **Negative result:** a gate that
>   fails at 64 MHz and passes at 10 MHz on the same mesh is the finding this
>   chunk exists to surface — record the numbers per gate, open a
>   known-issues entry, stop; never widen.
> * **Step 3 — 128 MHz**, step 2 repeated, only after step 2 gates.
> **Done-when:** step 2's three gates executed at 64 MHz through the
> package entry point with elapsed recorded — then §2.2's "no coil or
> birdcage has ports" bullet moves, §10's Target box "loaded birdcage …
> runs end to end" ticks, and `ANS-4` (the birdcage 4-port at 64 MHz) may
> be commissioned on gated physics. Honest limit: the port model's feed
> systematics are the two-torus ones (`PORT-1` 3b-xviii, `PORT-10`); this
> chunk measures a self-consistency identity set, not an absolute-accuracy
> claim — that is the AED comparison's job.

### WF — End-to-end workflow & MRI outputs (Phase 5)

| ID | Title | Status | Tier |
|---|---|---|---|
| `WF-1` | MRI example CLI/config | 🧪 | smoke |
| `WF-2` | Reproducible output bundle manifest | ⚠️ | standard |
| `WF-3` | Quick-look phantom metrics report | ⚠️ | standard |
| `WF-4` | Scenario presets (debug/dev/benchmark-lite) | 🧪 | standard |
| `WF-5` | Loaded birdcage: frequency shift & Q degradation | ⬜ | heavy |
| `WF-6` | B1+ field mapping and homogeneity (CV) | ⬜ | heavy |
| `WF-7` | SAR10g hotspot identification | ⬜ | heavy |
| `WF-8` | Publication-quality visualization pipeline | ⬜ | standard |

> `WF-2`/`WF-3` produce structurally valid manifests and reports containing
> physically meaningless numbers. The plumbing is fine and becomes useful the
> moment `TH-1` lands.

### EX — Examples (§5.4 ramp)

Standalone example chunks enqueued by the daily review when a chunk closes a
quantitative gate (§5.4). Each is sized for one implementer run, executes via
`./run_examples.sh`, produces combined-XDMF that opens in ParaView, and
demonstrates a **gated** capability from an angle no existing example covers.

**Ramp accounting.** Phases 1–3 are at quota per §5.4's
`min(5, gating chunks closed ✅)` (backfill `EX-4`…`EX-12` discharged the
2026-08-09 audit's shortfalls); Phases 4/5 accrue as their gates close.
`mri:1` is the one ungated example, labelled as such in the file.

| ID | Title | Status | Tier |
|---|---|---|---|
| `EX-1` | Two-torus port fixture: conforming mesh, cell and facet tags in ParaView | ✅ | standard |
| `EX-2` | Cylindrical phantom domain: wall classification and tags in ParaView | ✅ | standard |
| `EX-3` | Mass-averaged SAR on the standard-masses sphere: point and 1 g/10 g fields in ParaView | ✅ | standard |
| `EX-4` | Lossy plane wave: decay and phase vs closed form (first time-harmonic example) | ✅ | standard |
| `EX-5` | PEC cavity resonances: eigenfrequencies vs closed form, mode field in ParaView | ✅ | standard |
| `EX-6` | Sphere in a uniform field: solved quasi-static response vs closed form | ✅ | standard |
| `EX-7` | Waveguide/coax: the `TH-7` gated quantity as a runnable example | ✅ | standard |
| `EX-8` | Resonance guard on a frequency sweep: the `TH-1` step-5 detector firing | ✅ | standard |
| `EX-9` | Measured h-convergence rate as an example output (Phase 1) | ✅ 2026-08-10 | heavy (reclassified from standard: 130 s of solve, §5.1 names convergence studies) |
| `EX-10` | Gauge cross-check: penalty vs Lagrange-multiplier Coulomb gauge (Phase 1) | ✅ | standard |
| `EX-11` | Dodd–Deeds coil loading: ΔR vs closed form, eddy currents in ParaView | ✅ | standard |
| `EX-12` | Examples hygiene: stale claims, dead references, the 2026-02 PNG | ✅ | smoke |
| `EX-13` | `examples/mri/01` at the validated gauge floor: rank-spread measured, on-record numbers refreshed | 🚫 | standard |
| `EX-14` | Straight-wire VTX export repair + the refcheck freshness branch exercised | ✅ (2026-08-10: round-trip max\|B\| identical to 12 digits, rel diff 0.000e+00 vs 1e-10; freshness branch fired, then green) | standard |
| `EX-15` | Every runnable example gets a step-by-step analysis guide (3 steps, operator directive) | ✅ (2026-08-11: all three steps landed; **16 of 16** runnable examples checked against 3 required headings, `PENDING_GUIDES` empty, negative controls fired in all three steps) | standard |
| `EX-16` | `examples/mri/01`: converge the frequency-domain solve, then re-measure the rank spread | 🚫 (2026-08-10: solve converges — `preonly`/LU, `reason=4` — and the spread does **not** move, 23.5539% vs the 23.5545% unconverged record; anchor FAIL, negative-result clause taken. Fix landed; the 23% is the centerline sampling path, 3215× the phantom path on the same fields) | standard |
| `EX-17` | Circular-loop VTX export repair: port the `EX-14` diff, same round-trip anchor | ✅ (2026-08-10: round-trip max\|B\| 7.756122914931e-05 T both ways, rel diff 0.000e+00 vs 1e-10; loop's analytic numbers unmoved, checker green) | standard |
| `EX-18` | Gap-voltage port pair → Z → S on the two-torus fixture (the 3b-xvii/xviii gated capability; first ports example) | ✅ (2026-08-13: raw 0.894543 × ωM₁₂ printed as the miss it is, corrected 0.939849 (−6.02%) inside the unmoved 10%; ‖S−Sᵀ‖/‖S‖ = 2.5494e-05, ‖S‖₂ = 0.861449 ≤ 1; blind-ladder negative control −98.26% asserted to fail; 134 s at `-n 2`) | standard |
| `EX-19` | Larmor lossy-sphere example (`TH-10`'s newly gated capability: first example solving at 64/128 MHz; rubric in the §9 item) | ✅ (2026-08-13: `th:6`, fixture imported from the `TH-10` test module; all four records reproduced through the example path — 3.643% / 1.826% interior relL2 at 18.68× / 57.31× separation, power 3.629% with the quasi-static route missing 58.140% — max drift **1.7e-04** vs a pre-stated 1% band; convergence and both negative controls executed in-run; 24 s at `-n 2`) | standard |
| `EX-20` | Package S-parameter sweep example (`PORT-1` step 4's newly gated capability: first example calling `run_n_port_sparameter_sweep` on the solved field — the entry-point angle `EX-18` does not cover; full rubric in the §9 item, commissioned 2026-08-15 review) | ✅ (2026-08-16: `ports:2`, one `run_n_port_sparameter_sweep(..., gap_voltage_ports=specs)` call → two solves → Z → S; **all four step-4 records reproduced inside the pre-stated 1% band, misses 3.33e-07 / 3.23e-07 / 3.67e-06 / 2.29e-07** — raw 0.894543 printed first and asserted to *fail* the 10% band, corrected 0.939849 (−6.02%) inside it, ‖S−Sᵀ‖/‖S‖ = 2.5494e-05, ‖S‖₂ = 0.861449 ≤ 1, `\|Z₁₂−Z₂₁\|/\|Z₂₁\|` = 5.8309e-04 printed; negative control executed in-run — the deprecated heuristic route on the same mesh/ports gives an identically-zero off-diagonal, max\|ΔS\| = 3.078e-01 with its `DeprecationWarning` shown; 178.2 s at `-n 2`, 178 055 cells; guide pass 19/19 green. **Named limitation on record:** the sweep returns no fields, so the combined XDMF costs one extra port-1 solve (23.0 s) — surfacing `TimeHarmonicFields` from `SParameterSweepResult` is unscoped. *Audit 2026-08-16, 03:00 review: COMPLIANT; tier reclassified standard → heavy per the `EX-9` precedent — 178.2 s sits at the 180 s standard boundary and the wrap was 500 s; the companion docrefs log exits 1 on 24 pre-existing stale artifacts from other examples, none EX-20's (journaled in attempts.md)*) | heavy |
| `EX-21` | Graded birdcage conductor mesh (`GEO-15`'s newly gated capability: first birdcage example of any kind — geometry angle no example covers; mesh-only, no solve; full rubric in the §9 item, commissioned 2026-08-16 10:30 review) | ✅ (2026-08-16: `mesh:3`, `examples/meshing/03_birdcage_graded_conductors.py` + same-stem guide; two rungs of the same fixture on the **CAD (occ) mass** denominator — graded `h_c` = 1.6 mm keeps **0.967019** ≥ the imported `CAD_MASS_GATE` = 0.95, baseline global `setSize` keeps **0.740335** and is asserted to *fail* the same gate (`EX-18` inverted-assertion pattern), **separation 0.226685**; `GEO-9` box-partition identities re-asserted on **both** rungs < 1e-9 and the conductor CAD mass identical across them < 1e-12; 48 245 → 98 474 cells, 26.0 s at `-n 2`, standard. Every constant imported from the `GEO-15`/`GEO-9` test modules, none restated (`ANS-1`). Logs `20260816T200348Z_EX-21-example-n2.log` and `20260816T200516Z_EX-21-example-n2-final.log` (ratios bit-identical across both); docrefs `20260816T200505Z_EX-21-docrefs-fix.log` — 24 dead references, all pre-existing staleness from other examples, **none EX-21's** (its one own violation was found and fixed by the first docrefs run). **Measured note for `PORT-9` step 3:** the graded birdcage is 98 474 cells, confirming that entry's 98 k budget) | standard |
| `EX-22` | Restore the absent example artifacts: refresh runs for `mag` 01/02/04/05/06 + `mri:1` (commissioned 2026-08-16 weekly review — see entry below) | ✅ (2026-08-19: the standing **`stale=24` backlog is 0** — `dead=0 guide=0 stale=0 stale_severity=report exit=0`, the first `exit=0` the checker has returned under the `OPS-19` contract, guide pass green at 24/24 runnable examples and 33 guides scanned. Three refresh runs, all `-n 2`, real build for `mag` / complex for `mri`, all **exit 0**: `-e 1,2,4` 230 s, `-e 5,6` 151 s, `-e mri:1` 6 s. Every recorded anchor reproduced by the examples' own asserts — `EX-14`/`EX-17` VTX round-trips **0.000e+00** against their 1e-10 tol on both `straight_wire_B.bp` (max\|B\| 4.463816061893e-05 T) and `circular_loop_B.bp` (7.756122914931e-05 T); `EX-10` gauge cross-check **0.0003% probe / 0.0033% volume** against the 5% `MAG-15` gate; `EX-9` fitted h-convergence rate **1.1009** inside the `MAG-13` (0.7, 1.5) band, byte-matching the record; `EX-19`-era helmholtz centre B_z 1.28% with the h-ladder 0.89% / 0.24% / 1.28% at 70 054 / 103 984 / 160 478 cells. `mri:1` is the labelled **ungated** example — its printed record reproduced digit-for-digit against the guide, not gated: 9 261 cells / 2 077 vertices, cell tags 385 / 350 / 493 / 8 033, phantom \|E\| 1.244231e+02 / 3.150176e+02 / 1.975909e+02, \|B\| 8.791014e-08 / 2.771692e-06 / 1.292004e-06, ratio 1.529336e+08, coverage 493/493/493 with 0 drops. Logs `20260820T003126Z_EX-22-mag-124.log`, `20260820T003532Z_EX-22-mag-56.log`, `20260820T003812Z_EX-22-mri1.log`, `20260820T003833Z_EX-22-docrefs.log`. The 2026-08-16 premise correction held throughout: nothing was absent, `dead=0` before and after — this was a pure freshness restore) | heavy |
| `EX-23` | Two-torus port-sheet mesh (`GEO-16`'s newly gated capability: first example with an interior sheet surface, facet tags rebuilt dolfinx-side — geometry angle no example covers; mesh-only, no solve; commissioned 2026-08-17 review) | ✅ (2026-08-17: `mesh:4`, `examples/meshing/04_two_torus_port_sheet.py` + same-stem guide; both sheets **84 facets**, meshed/CAD = **1.000000000000** inside the imported `AREA_IDENTITY_BAND` = 1e-9, 211/212 area symmetry bit-identical (< 1e-12), out-of-plane spread **3.469e-18** m; kwarg-off control reproduces **79 534** cells with cell tags `{1,2,3,101,102}`, facet tags `{1,201,202}` and sheet tags asserted *absent* (`EX-18` inverted-assertion pattern); extents printed not gated — w = 1.200000000e-02 m, h = 7.977525299e-03 m, **w/h = 1.504225878** against the generator's CAD-side 1.504206917; port areas 1.563786482e-04 m² on both 201/202, unmoved. 79 888 cells / 13.7 s sheet mesh, 79 534 / 12.2 s control, **26.0 s** in-script (30 s harness) at `-n 2`, standard. Every constant imported from `tests/mesh/test_two_torus_port_sheet.py` and the `PORT-1` facet module (`ANS-1`) except `SHEET_SYMMETRY_BAND = 1e-12`, which the test holds only as an inline literal and the example restates unloosened (10:30-review audit note). Logs `20260817T140233Z_EX-23-list.log`, `20260817T140242Z_EX-23-example-n2.log`, docrefs `20260817T140416Z_EX-23-docrefs.log` — `dead=0 guide=0 stale=24 exit=2`, staleness-only and **none EX-23's** (its own artifacts are fresh; the 24 are `EX-22`'s standing backlog), guide pass green: 22 runnable examples checked, 31 guide files scanned (the 03:00-era "31 guides green" conflated the two counts; corrected 10:30 review)) | standard |
| `EX-24` | Lumped-sheet port at interior width (`PORT-9` step 2b's newly gated capability: first example instantiating the lumped-element port BC — the drive/BC angle `EX-18`/`EX-20`, both gap-voltage, do not cover; commissioned 2026-08-17 18:00 review) | ✅ (2026-08-18: `ports:3`, `examples/ports/03_lumped_sheet_port_widths.py` + same-stem guide; **both legs on one mesh** — the width ladder reproduced **7.7095% → 3.6730% → 1.8333%** and the gate at `f = 0.5` held at **1.8333%** against the imported, unmoved `CROSS_ROUTE_BAND` = 5%; `f = 1.0` reproduced `STEP1_CROSS_ROUTE_RECORD` (0.077095) and `STEP1_GAP_RATIO_RECORD` (0.894310) inside `REPRODUCTION_BAND` = 1e-4 **and** was asserted to *miss* the 5% band (`EX-18` inverted pattern), while the gap route stayed flat at 0.894310/0.894324/0.894349 × ω·M₁₂ (drift 3.9e-5 < 1e-4 — a third control this example adds); open-limit identity `V = −(1/w_f)∫_S E·ĥ dS` at **1.8e-15 / 8.5e-16 / 2.1e-16** against 1e-11 per width; sweep leg through `LumpedSheetPortSpec` gave `is_placeholder=False` and **‖S−Sᵀ‖/‖S‖ = 2.574296e-11** against the 1e-3 band (step 2c's record 2.574249e-11, reproduced to 4.7e-16 absolute), cross-route inside the sweep **1.6079% / 1.5950%** (~0.23 pp below step 2b's 1.8333% — the drive differs, reported not gated); gap-box volume 1.000000000000, sheets 1585 → 1511 → 1375 facets, planar to < 1e-12, `w = A/h` asserted equal to the bbox extent on the `f = 1.0` rectangle and strictly below it on both narrowed sheets. 184 919 cells / 40.1 s mesh, solves 26.9/24.1/24.1 s, sweep 52.3 s, **237.5 s** in-script (239 s harness) at `-n 2`, standard. Every band and record imported from `test_port_lumped_two_torus.py`, `test_port_lumped_narrowed_sheet.py`, `test_port_lumped_sheet_sweep.py` and `test_port_package_sparameters.py` (`ANS-1`); none restated. Logs `20260819T003342Z_EX-24-importcheck.log`, `20260819T003401Z_EX-24-example-n2.log`, docrefs `20260819T003912Z_EX-24-docrefs.log` — `dead=0 guide=0 stale=24 exit=2`, staleness-only and **none EX-24's** (the 24 are `EX-22`'s standing backlog), guide pass green at 32 guides scanned) | standard |
| `EX-25` | Degree-2 Larmor sphere: accuracy-per-cost side by side (`TH-12` step 1's newly gated capability: first example at any element order other than 1 — the discretization angle no example covers; commissioned 2026-08-18 10:30 review) | ✅ (2026-08-19: `th:7`, `examples/time_harmonic/07_element_order_lossy_sphere.py` + same-stem guide; **both orders on one mesh** — 5 866 cells solved at N1curl degree 1 and 2 in one run, all four `TH-12` step-1 records reproduced inside the imported `EX-19` 1% band: relL2 **8.1541%** / **0.1405%** (drift 4.00e-06 / 5.50e-05) and ohmic-power error **8.3869%** / **0.0058%** (drift 1.18e-05 / 1.48e-03); inverted negative control asserted both ways — degree 1 *misses* the degree-1 fine-rung record 3.643% at 17 670 cells while degree 2 beats it on 3.01× fewer cells at 25.9× the accuracy; DOFs asserted exactly 7 591 / 39 634, cells 5 866 at both orders, `\|Im P\|/Re P` = **0.000e+00** at both against the imported 1e-9 family bound. Cost printed not gated: 5.22× DOFs for 2.02× solve wall (3.75 → 7.59 s) and 2.74× summed `ru_maxrss` (376.8 → 1032.8 MiB) — sublinear on both axes *on this fixture*, printed beside `TH-12` step 2's contrary ~20×/5.42× coil reading so no production-order claim is implied. Two combined XDMFs on the identical mesh + CG1 output space. **13.4 s** in-script (16 s harness) at `-n 2`, standard. Constants imported from `tests/validation/test_lossy_sphere_degree2.py` and the `TH-10` module (`ANS-1`); restated with provenance only where the gate holds no named constant — `RECORD_FIELD_ERROR` (both orders), the degree-2 power record, `RECORD_DOFS`, and `COARSE_CELLS = 5866` (the gate carries it as an inline literal), all unloosened and all asserted. Logs `20260819T140334Z_EX-25-example-n2.log` (exit 0), docrefs `20260819T140453Z_EX-25-docrefs.log` — `dead=0 guide=0 stale=24 exit=2`, staleness-only and **none EX-25's** (the 24 are `EX-22`'s standing backlog), guide pass green at 33 guides scanned. *Audited COMPLIANT 2026-08-19 10:30 review — records asserted not printed, the four restated constants match their provenance unloosened, and the stale-24 set verified byte-identical to `EX-24`'s docrefs log, so no new staleness*) | standard |
| `EX-26` | Poynting power-balance audit (`POST-5`'s newly gated capability: `poynting_power_balance` with the impressed-source term — the output-quantity angle no example covers, power accounting rather than fields; commissioned 2026-08-20 03:00 review) | ✅ (2026-08-20: `th:8`, `examples/time_harmonic/08_poynting_power_balance.py` + same-stem guide; **both fixtures on one run, closed as written** — driven cylinder three-term **16.7465%** inside the imported, unmoved `POYNTING_IMBALANCE_MAX` = 25% with the two-term reading of the *same field* printed at **116.7465%** and asserted to *miss* that band (`EX-18` inverted pattern), `TH-6` plane wave source-free **8.185716%** with each leg scored against its own closed form at **8.1205% / 0.0711%** inside the imported `POST5_STEP3_LEG_BAND` = 10%, and the `POST-5` step-4 control exact — source term `0.0` W at J = 0 with all **7** other dict keys bit-identical to the source-free call. Second control the tests carry and the example re-executes: σ-blind (lossless medium, same field) volume leg exactly 0.0 W, residual 83.2535% = **4.97×** the honest reading against the pre-registered 3.0× floor and the 5.97× arithmetic ceiling. All **8** records reproduced inside a pre-stated 1% band, worst drift **3.00e-04** (the `TH-6` Ohmic-leg error, the record quoted to the fewest digits); driven-fixture drifts 1.40e-06 / 2.01e-07 / 3.36e-07 / 1.11e-07 / 3.36e-07. Two combined XDMFs carrying `E` (CG1) plus `B` and the real Poynting vector `½Re(E×H̄)` as **DG0 cell fields** — `curl E` of a degree-1 N1curl field is cell-wise constant, so smoothing to vertices would invent resolution the solve does not have. 1 405 cells driven / 10 368 cells `TH-6`, **4.7 s** in-script (8 s harness) at `-n 2`. Every band, fixture, drive and analytic leg imported from `tests/solver/test_time_harmonic_smoke.py`, `tests/validation/test_poynting_balance.py` and the `TH-6` module (`ANS-1`); restated with provenance only where the gate holds the number as printed output rather than a named constant — `TH6_RECORD_IMBALANCE` = 0.08185716, `TH6_RECORD_FLUX_ERROR` = 0.081205, `TH6_RECORD_DISSIPATED_ERROR` = 0.000711, `TH6_CELLS` = 10368 — all unloosened and all asserted. Logs `20260820T170422Z_EX-26-example-n2.log` (exit 0) and `20260820T170540Z_EX-26-docrefs.log` — **`dead=0 guide=0 stale=0 stale_severity=report exit=0`**, the second `exit=0` under the `OPS-19` contract, 34 guides scanned and `EX-22`'s stale-0 restore still holding at this commit. **Tier note for the review:** commissioned standard, **measured smoke** (8 s harness). The commission's 8 s + 152 s estimate charged this example the whole `TH-6` file; the 152 s belongs to that file's *other* tests — the 24³ rung and the piecewise-σ / piecewise-μᵣ families — not to the 12³ rung the example audits. *Audited COMPLIANT 2026-08-21 18:00 review — records asserted through the example path, XDMF artifacts on disk, docrefs exit 0, tier relabel confirmed*) | standard (measured smoke) |
| `EX-27` | Region-resolution policy on the coil+phantom mesh (`GEO-17`'s newly gated capability: first example whose subject is a mesh-*sizing policy* — policy-on vs clamps-only on one fixture, the volume-recovery angle no example covers; `EX-21` grades one conductor by an explicit `h_c`, a different angle. Mesh-only, no solve; this is the mesh capability `MAT-4`'s SAR-on-a-coil route runs through. Commissioned 2026-08-21 18:00 review; full rubric in the §9 item) | ✅ (2026-08-22: `mesh:5`, `examples/meshing/05_region_resolution_policy.py` + same-stem guide; **closed as written on the first run**, every element of the rubric executed and no band moved. Policy coil meshed/CAD **0.835563 / 0.833730** against the imported, unmoved `POLICY_MIN_CAD_RECOVERY` = 0.755, both reproducing the `GEO-17` records to every printed digit inside the pre-stated 1% band; the clamps-only mesh asserted to **miss** that same floor at **0.754685 / 0.752565** (`EX-18` inverted pattern) — and because the floor was pre-registered as "the uniform mesh's own recovery", that control clears by only ~3.2e-4 **by construction**, so the example gates the *sizing* separation separately at a pre-stated `SIZING_SEPARATION` = 0.05, measured **+0.080879 / +0.081165**. Sign identity on all three refined tags (+10.7169% / +10.7851% / +0.9374%) with the one coarsened region, the air, the one that pays (**−0.2643%**); inscription bound meshed/CAD ≤ 1 on both meshes, all three curved tags (max 0.992751); tagged-volume partition **1.000000000000** on both meshes at the imported `VOLUME_PARTITION_BAND` = 1e-9; and the clamps-only path re-asserted against the imported `OPS-17` record on all **4** tags at 1e-9 — the negative control on `GEO-17`'s fix itself, which may not touch a mesh that asks for one size everywhere. Two combined XDMFs with `CellTags` (`EX-21`/`EX-23` mesh-only precedent); 19 792 cells clamps-only / 20 843 policy, 5.4 s in-script at `-n 2`. Geometry, policy sizes, floor, refined-tag list, CAD volumes and the `OPS-17` table are all **imported** from `tests/mesh/test_mesh_tag_integrity.py` (`ANS-1`) — `POLICY_RESOLUTIONS` was hoisted to module level in that file by this chunk so the sizing itself is imported rather than restated (3 passed, 13 s regression, `20260822T033508Z_EX-27-geo17-regression.log`); the two policy *recovery* records are restated with log provenance and a 1% band, the `EX-26` precedent, because the gate holds them as printed output. Logs `20260822T033345Z_EX-27-example-n2.log` (exit 0) and `20260822T033529Z_EX-27-docrefs.log` — **`dead=0 guide=0 stale=24 stale_severity=report exit=2`**, `exit != 1` under the `OPS-19` contract, 35 guides scanned; the 24 stale entries are `EX-22`'s 48 h window re-growing exactly as the commission predicted ("stale re-grows from ~2026-08-22 by design") and none of them is an `EX-27` artifact. **Tier note for the review:** commissioned standard, **measured smoke** (8 s harness) — the commission's 13 s estimate was the two meshes alone and was close; the exports cost less than assumed. *Audited COMPLIANT 2026-08-22 03:00 review: every gate is CAD-analytic, record, or monotonicity; nothing loosened; the regression's "13 s" is pytest-internal, the harness row says 15 s — both true*) | standard (measured smoke) |
| `EX-28` | Gapped birdcage with leg terminals and port sheets (`GEO-18`'s newly gated capability, both steps: first example with a **discontinuous conductor** — planar disk terminals on a cut leg and an interior sheet spanning metal to metal on a coil; `EX-21` is the uncut graded birdcage, `EX-23` the two-torus sheet — a geometry angle no example covers. Mesh-only, no solve; this is the mesh `PORT-9` step 3 solves on. Commissioned 2026-08-22 03:00 review, deferred from 08-21 until the fixture stopped moving; full rubric in the §9 item) | ✅ (2026-08-23: `mesh:6`, `examples/meshing/06_birdcage_leg_gaps_port_sheets.py` + same-stem guide; **closed as written on the first run**, every element of the rubric executed and no band moved. Sheeted rung **116 416 cells**, meshed/CAD conductor **0.970193** against the imported, unmoved `CAD_MASS_GATE` = 0.95; per port the sheet is **54 facets, `1.120000000e-04 m²`, meshed/analytic `1.000000000000`** against the analytic `dx·g`, `h = 8.000000000e-03 m` = the gap exactly, **`w_eff/w_bbox = 1.000000000000`** (the `PORT-9` step 2b convention, i.e. the facet set is the whole rectangle), out-of-plane spread `2.512e-16` m (P1/P3) / `9.714e-17` m (P2/P4), halves **`0.500000000000/0.500000000000`** of the analytic gap box, terminal `2.236196e-04 m²` = **0.988616** of the closed-form `2.261946711e-04 m²` inside the imported `TERMINAL_AREA_BAND` [0.95, 1.0] *and* inside step 1's pre-stated `1e-5` record band, closure **`1.000000000000`**; **C4 sheet spread `8.470e-16`** — every figure reproducing `GEO-18` step 2's log to the printed digit. `GEO-9` partition `< 1e-9` on both rungs. **Negative control (inverted, `EX-18`/`EX-23` pattern):** the uncut rung at **98 474 cells, ratio 1.000000** against `EX-21`'s record and meshed/CAD **0.967019** = the record, cell tags `[1, 2, 3, 101-104]` with no `11x` half tag, conductor-facing area **exactly `0.000000e+00 m²`** on all four ports (leg (b)'s finding re-measured) — **and the `210+i` facet groups asserted absent by measurement**, `_global_facet_count` = 0 on all four after an `_interface_facet_tags` rebuild on the uncut mesh, which closes the one clause `GEO-18` step 2's audit found implied rather than asserted. Three combined XDMFs (sheeted cells, sheeted sheet facets 211-214, uncut cells) for the side-by-side. Every constant **imported** from `tests/mesh/test_birdcage_leg_gaps.py` and `tests/mesh/test_birdcage_port_sheets.py` and the modules they import (`ANS-1`); nothing restated, no pre-existing test touched. Logs `20260823T020338Z_EX-28-example-n2.log` (exit 0, **43.1 s in-script / 46 s harness at `-n 2`**, sheeted 21.46 s mesh / 23.41 s rung, uncut 19.02 s) and `20260823T020531Z_EX-28-docrefs.log` — **`dead=0 guide=0 stale=24 stale_severity=report exit=2`**, `exit != 1` under the `OPS-19` contract, 36 guides scanned, none of the 24 stale entries an `EX-28` artifact. **Tier note for the review:** commissioned standard, **measured standard** (46 s harness against the commission's ~75 s estimate; the `EX-27` precedent that exports are cheaper than the meshes held again — the two builds are 42 s of the 43 s)) | standard |
| `EX-29` | Doc-reference checker freshness-gates every example's own `paraview_output/` (22 of 27 examples were never checked — known-issues 2026-08-23; commissioned 2026-08-23 weekly review) | ✅ | smoke |
| `EX-30` | Refresh the 13-example stale artifact set the checker could not see (10–17 d old on 2026-08-23; commissioned 2026-08-23 weekly review; **re-scoped 2026-08-24 10:30 review to four legs from the honest `stale=55` census** — see prose entry) | 🟡 (**leg (th) ✅ 2026-08-25**: all eight `th:` examples green, `time_harmonic` census 4 → 0 inside a derived 51 → 47, the licensed 128 MHz alignment executed — 0.01826 → 0.01769 / 57.31 → 59.16, version-tagged — and `th:6` reproducing to 2.02e-04 / 5.45e-05 in its unmoved 1% band; 105 s, measured standard. Legs (root), (mesh), (ports) all queued 2026-08-25 03:00 review — §9 items 3–5, with in-class (1\*) example-record licences granted for (mesh)/(ports). **Leg (root) attempted 2026-08-25 09:00 — not closed**: 6 of 8 green, census 47 → 26 fully attributed, two reds filed as known-issues, one of them a `MAG-13` convergence **gate red on `main`** since the 0.11 merge — see prose entry) | heavy |
| `EX-31` | Ring-gapped birdcage with dual port families (`GEO-20` step 1's newly gated capability: first example with ring-gap terminals as exact disks from radial cut planes, and the first 12-port dual-family mesh — a geometry angle `EX-28` (leg gaps only) does not cover; mesh-only, no solve; commissioned 2026-08-24 10:30 review) | ✅ (2026-08-24: `mesh:7`, `examples/meshing/07_birdcage_ring_gap_ports.py` + same-stem guide; **closed as written on the first run**, every element of the rubric executed and no band moved — see the prose entry for the digits. *Audited COMPLIANT 2026-08-24 18:00 review: all three footers verified (75 / 72 / 1 s, statuses 0/0/2 with exit 2 = the `OPS-19` stale-only contract), the printed assertions match this entry to the last decimal, the gate-module strengthening is real (records asserted at their source, lines 403/458/538, imported by the example not restated), and `git show 7529fa4 -- tests/` is 24 insertions / 0 deletions — purely additive, nothing loosened*) | standard (measured standard) |
| `EX-32` | Birdcage 4-port power-wave S-matrix at 10 MHz (`PORT-9`'s newly gated capability: first example solving ports on the **birdcage** — every existing S-parameter example is two-torus (`EX-20`/`EX-24`/ports:1–3), and `EX-28`/`EX-31` are mesh-only; commissioned 2026-08-25 10:30 review, §5.4 ramp) | ⬜ | standard |

**`EX-26` — Poynting power-balance audit** ✅ *(2026-08-20, 12:00 slot; commissioned 2026-08-20 03:00 review, §5.4 ramp on `POST-5` step 4; audited COMPLIANT 2026-08-21 18:00 review)*. `examples/time_harmonic/08_poynting_power_balance.py` + same-stem guide, `th:8`. **Closed as written, both fixtures on one run, no band moved.** Driven cylinder three-term **16.7465%** inside the imported `POYNTING_IMBALANCE_MAX` = 25%, two-term 116.7465% asserted to *miss* (inverted control); `TH-6` plane wave source-free **8.185716%**, legs 8.1205% / 0.0711% inside `POST5_STEP3_LEG_BAND` = 10%; J = 0 source term `== 0.0` W with 7 other keys bit-identical; σ-blind residual 83.2535% = **4.97×** (floor 3.0×, ceiling 5.97×); impressed-source term = 100.0% of the largest term. All 8 records inside a 1% band, worst drift 3.00e-04. Restated with provenance: `TH6_RECORD_IMBALANCE` = 0.08185716, `TH6_RECORD_FLUX_ERROR` = 0.081205, `TH6_RECORD_DISSIPATED_ERROR` = 0.000711, `TH6_CELLS` = 10368. Two combined XDMFs (`E` CG1; `B` and `½Re(E×H̄)` as DG0 — honest resolution of a degree-1 `curl E`, faceted in ParaView by choice). 1 405 / 10 368 cells, 4.7 s in-script, 8 s harness at `-n 2`.
**Logs:** `20260820T170422Z_EX-26-example-n2.log` (exit 0), `20260820T170540Z_EX-26-docrefs.log` (`dead=0 guide=0 stale=0 exit=0`).
**Carry-forwards:** commissioned standard, **measured smoke** — the 152 s estimate belonged to the `TH-6` file's other tests, not the 12³ rung; demonstration only, no SAR or coil-loading claim.
Full narrative: `docs/planning/plan-archive.md`, entry «§7 EX-26 full narrative — archived 2026-08-23 (weekly review)».

**`EX-25` — degree-2 Larmor sphere: accuracy-per-cost side by side** ✅ *(2026-08-19, 09:00 slot; commissioned 2026-08-18 10:30 review, §5.4 ramp on `TH-12` step 1)*. New `examples/time_harmonic/` example on the `TH-10` lossy saline sphere (`EX-19` fixture, imported): the same coarse 5 866-cell mesh solved at degree 1 and degree 2 in one run, side-by-side table + combined XDMF of both solutions (one mesh, one CG1 export space — the only variable is the element). **Closed as written, no band moved:** all four records inside the imported 1% `REPRODUCTION_BAND` (worst drift 1.48e-03, degree-2 power error) — degree 2 **0.1405%** relL2 / **0.0058%** power, degree 1 **8.1541%** / **8.3869%**; `|Im P|/Re P` exactly 0.0 at both orders; inverted control asserted both ways (degree 1 misses the 3.643% fine-rung record, degree 2 beats it); DOFs asserted exactly **7 591 / 39 634**. Cost ratios 5.22× DOFs → 2.02× wall, 2.74× RSS — sublinear, the opposite shape from `TH-12` step 2's coil (~20× wall for 5.42× DOFs); the 2.02× includes mesh + assembly (step 1's solve-only 4.32×), neither gated. Constants from `tests/validation/test_lossy_sphere_degree2.py` and the `TH-10` module (`ANS-1`); complex-mode XDMF `real_*`/`imag_*` split (`OPS-21`); summed `ru_maxrss`, not `memory.peak`.
**Carry-forwards:** sphere fixture only — no production-order claim (that is the weekly review's per the `TH-12` decision clause; decided 2026-08-23, §10); the example prints both cost shapes side by side precisely so this fixture's cheap second order is not generalised.
Full narrative: `docs/planning/plan-archive.md`, entry «§7 EX-25 full narrative — archived 2026-08-23 (weekly review)».

**`EX-24` — lumped-sheet port at interior width** ✅ *(2026-08-18, 19:30 slot; commissioned 2026-08-17 18:00 review + 2026-08-18 03:00 addendum, §5.4 ramp on `PORT-9` steps 2b/2c; audited COMPLIANT 2026-08-19 03:00 review)*. Example on the `GEO-16` port-sheet solve fixture: the f ∈ {1.0, 0.735, 0.5} width ladder as three lumped-BC solves plus, at f = 0.5, the two-port sweep through `LumpedSheetPortSpec`; combined XDMF with sheet tags; same-stem guide. Constants imported from `tests/validation/test_port_lumped_narrowed_sheet.py`, `tests/validation/test_port_lumped_sheet_sweep.py` and the two-torus module (`ANS-1`). **Closed as written, both legs on one run, no band moved:** ladder 7.7095% / 3.6730% / **1.8333%** (gate at f = 0.5 against 5%), f = 1.0 reproducing both step-1 records (7.7095%, gap ratio 0.894310) inside 1e-4 *and* asserted to miss the band, open-limit identity ≤ **1.8e-15** per width, sweep reciprocity **2.574296e-11** against 1e-3, gap route asserted flat across the ladder (0.894310 → 0.894349, drift 3.9e-5 against `REPRODUCTION_BAND`). Both legs share one mesh (non-mutating midpoint filter): 237.5 s in-script against the ~260 s estimate, standard tier at `-n 2`.
**Logs:** `20260819T003401Z_EX-24-example-n2.log` (every plan number matched digit-for-digit; footers 4 s / 239 s / 1 s); docrefs exit 2 staleness-only, all 24 stale artifacts pre-existing `EX-22` backlog.
**Carry-forwards:** the sweep's cross-route sits **~0.23 pp below** the ladder's at the same width (1.6079 / 1.5950% vs 1.8333%) — the impressed-sheet drive reads closer to the centreline than the impressed-gap drive, a systematic `PORT-9` step 3 should expect rather than debug; `w = A/h`, never the bbox extent; two-torus only, no birdcage claim.
Full narrative: `docs/planning/plan-archive.md`, entry «§7 EX-24 full narrative — archived 2026-08-23 (weekly review)».

**`EX-23` — two-torus port-sheet mesh example** ✅ *(2026-08-17, 09:00
slot; commissioned 2026-08-17 review, §5.4 ramp on `GEO-16`'s newly gated
capability)*. **Closed as written** — every element of the rubric below
executed, no band moved and none needed to move: both area identities
landed at `1.000000000000`, the kwarg-off control reproduced 79 534 cells
with the sheet tags absent, and the docrefs checker exits 2
(staleness-only, none of it this example's). Two things worth carrying
forward: the sheet mesh costs **+354 cells** over the control
(79 888 vs 79 534) — the fragment is nearly free, which is the number
`PORT-9` step 3 should budget from; and the measured `w/h = 1.504225878`
sits **1.3e-05 relative** above the generator's own CAD-side
`squares_w_over_h = 1.504206917`, the arc-chord difference between the
CAD surface and its triangulation, printed side by side in the example.
*(Original plan below.)*
`examples/meshing/01` shows the gapped two-torus and `03` the graded
birdcage; no example shows an **interior sheet surface** — the
known-issues-9 pattern (facet tag rebuilt from cell tags on the dolfinx
side, never a dim-2 gmsh group) that `GEO-16` gated and `PORT-9` now
builds on. **Do:** `examples/meshing/04_two_torus_port_sheet.py` + the
same-stem guide (`EX-15` rule: same commit), dispatched through
`./run_examples.sh`, producing combined-XDMF (cells + facets, tags
`211`/`212` visible) that opens in ParaView. Import every constant from
`tests/mesh/test_two_torus_port_sheet.py`, none restated (`ANS-1`
pattern): assert both sheets' meshed/CAD area to `AREA_IDENTITY_BAND`
(= 1e-9; `GEO-16`'s gate, `1.000000000000` on record), the 211/212
symmetry identity < 1e-12, and the kwarg-off negative control (recorded
cell count `79 534`, no `21x` tags — the `EX-18`/`EX-21`
inverted-assertion pattern); print the measured extents
(`w/h = 1.504225878` on this fixture's parameterisation). **Tier/cost:**
standard, mesh-only, no solve; `GEO-16`'s runs were 31/49 s at `-n 2` —
budget ~60 s, `timeout -k 30 480`. **Traps:** the sheet kwarg splits
each gap volume into **two** cell tags (`101`+`111`, `102`+`112`) —
select both; docrefs checker gates on **`exit != 1`** (`OPS-19`
contract), staleness is information; facet counts asserted `> 0` before
any area identity (vacuous-pass guard). **Scope:** mesh-only — no port,
no solve, no `Z` claim; the solve fixture's differently-parameterised
`w/h = 0.745249896` belongs to `PORT-9`, not here. **Negative result:**
the area identity failing on the example path is a regression against
`GEO-16`'s gate — known-issues entry, report, stop.

**`EX-22` — restore the absent example artifacts** ✅ *(closed 2026-08-19,
19:30 slot — see the §7 table row for the full closure numbers. Done-when
met in three runner commands rather than the entry's two: `mag` was split
`-e 1,2,4` / `-e 5,6` so neither container window could approach the
foreground ceiling, since the only prior all-mag timing on record (204 s)
predates examples 05 and 06 and would have left the group unpriced at
~390 s. Measured: 230 s + 151 s + 6 s. The checker reads `exit=0` for the
first time under the `OPS-19` contract; nothing was ever dead, so the
2026-08-16 premise correction is confirmed a second time and the chunk was
a freshness restore, never a recovery)* *(commissioned
2026-08-16, weekly review — examples-health audit)*. Six examples' gated
`paraview_output/` outputs are **absent on disk**, not merely stale:
every `straight_wire_*`, `helmholtz_*`, `gauge_cross_check_*`,
`h_convergence_rate_*` and `mri_coil_phantom_*` artifact plus
`circular_loop_B.bp` is gone (gitignored, so unrecoverable without
reruns) — the source of the doc-reference checker's 24 standing
stale-reference violations (`OPS-19` owned the *policy* split and landed
2026-08-16 — those 24 now score `exit=2`, staleness-only, and no longer
mask a real defect; this chunk restores the *artifacts*).
**Premise correction, measured 2026-08-16 16:30 slot
(`20260816T213312Z_OPS-19-step1-rerun.log` lines 44–68):** the 24 are
`dead=0 stale=24` — every one of them **exists** in `paraview_output/`,
aged 145.5–151.4 h, including `circular_loop_B.bp`. "Absent on disk" does
not hold at this commit; the chunk's refresh work is unchanged, but its
done-when should be read as 24 → 0 *stale*, and whether any artifact is
genuinely missing needs re-auditing before the runs are sized. **Do:**
runner refresh runs, `mag` 01/02/04/05/06 and `mri:1`, through the
harness. **Done-when:** each run exits 0 with its recorded anchors
reproduced by the examples' own asserts (`EX-14`/`EX-17` round-trip
identities included), the six examples' artifacts exist on disk, and the
doc-reference checker's stale/dead count drops 24 → 0 (guide pass stays
green — 21/21 since `EX-21`; the checker under the `OPS-19` contract then
reads `exit=0`). **Tier:** heavy — `EX-9`'s convergence example alone is ~130 s;
run as two runner commands (`mag` group, then `mri:1`), each wrapped
`timeout -k 30 500`. **Trap:** `mri:1` is the labelled *ungated* example
— reproduce its printed record, do not invent a gate for it. **Negative
result:** an example that no longer reproduces its record is a real
regression — known-issues entry, report, stop; never refresh past a
failure.

**`EX-4`…`EX-12` — the 2026-08-09 backfill, all ✅ by 2026-08-10** *(full
plans + closure narratives in `docs/planning/plan-archive.md`)*. Common
pattern, held across all nine: fixture and constants **imported** from the
gate test, never restated; the gate record reproduced digit for digit
through the example path; the exported array itself gated, not merely
written; runner-dispatched harness logs. Per-example anchors on record:
`EX-4` α/β to 0.0185% / 0.0593% (`th:1`); `EX-5` four cavity modes to
≤ 0.0436%, Rayleigh-quotient export identity 3.48e-15 (`th:2`); `EX-6`
interior E_z 2.443%, volume-integral corroboration 0.014% (`th:3`); `EX-7`
γ = 37.650399 Np/m at 0.006%, TE₁₀ profile RMS 0.200% (`th:4`); `EX-8`
resonance guard 137.554 vs threshold 50, pole law 3.156% (`th:5`); `EX-9`
h-convergence rate 1.1009 in the gate's (0.7, 1.5) band, heavy tier, plus
the CG1-export finding (smoothing costs 7.89 pp on a 1/r field); `EX-10`
gauge cross-check 0.0004% probe / 0.0033% volume with an 11-order |A|
separation (`-e 5`); `EX-11` Dodd–Deeds ΔR 1.5834% byte-matching `MAT-6`
step 3, σ = 0 control exactly zero (`mat:1`, feeds `ANS-1`); `EX-12`
examples hygiene + the doc-reference checker (its freshness/`.bp` findings
spawned `EX-14`/`EX-17`).

**`EX-15` ✅ 2026-08-11** *(operator directive 2026-08-10; full plan +
three step closures in `docs/planning/plan-archive.md`)*. Every runnable
example ships a same-stem analysis guide with three required headings
(policy stated in §5.4), enforced by a guide pass in
`scripts/testing/check_example_doc_references.py` that reads the example
set from `./run_examples.sh --list`. Closed at **16 of 16** guides,
`PENDING_GUIDES` empty (`20260811T110627Z_EX-15-step3-refcheck-final.log`);
negative controls (missing guide, missing heading) fired in all three
steps. Standing rule: a new example must ship its guide in the same
commit; on-record numbers in guides are copied from §7/gate records and
cited by log name, never re-measured.

**`EX-13` 🚫 2026-08-10, closed negative** *(full plan + result in
`docs/planning/plan-archive.md`)*. The `MAG-6` gate-fixture rank-spread
reading (0.024%) does not transfer to `examples/mri/01`: floor spread
23.5545% vs the < 5% anchor, sub-floor 23.3010% (no discrimination —
`TimeHarmonicSolver.solve` ignores `gauge_penalty`, so the E leg is inert
by construction). The 23% measured the unconverged GMRES iterate; salvage
scoped as `EX-16`.

**`EX-16` 🚫 2026-08-10, closed negative** *(full plan + result in
`docs/planning/plan-archive.md`)*. Converging `examples/mri/01`'s
time-harmonic solve (direct `preonly`/LU, `reason=4`) did **not** move the
23% `-n 2`/`-n 4` centerline spread (23.5539% vs the 23.5545% unconverged
record) — the convergence hypothesis is refuted. The decisive positive
control: the 493-point phantom-region sampler agrees to 0.007326% on the
same fields, **3215×** tighter, so the defect is the centerline
point-evaluation path (on-axis points on shared mesh edges, the `MAG-6`
step-4 mechanism). Known-issues entry stays open, re-pointed at
`evaluate_vector_field_parallel` (assigned `POST-4`). The code fix landed
on its merits; `WF-1` stays 🧪.

**`EX-17` ✅ 2026-08-10** *(full plan + closure in
`docs/planning/plan-archive.md`)*. The `EX-14` diff ported to
`02_circular_loop.py`: round-trip max |B| 7.756122914931e-05 T both ways,
rel diff 0.000e+00 vs 1e-10 on a mesh 30× larger
(`20260810T200154Z_EX-17-gate-mag2.log`, 124 s); the loop's analytic
numbers (6.3046% / 13.5037%) unmoved; known-issues entry retired.

**`EX-18` ✅ 2026-08-13** *(doc repairs 2026-08-16; full plan + closure in
`docs/planning/plan-archive.md`)*. `ports:1`, the first ports example:
gap-voltage pair → Z → S on the two-torus fixture, reproducing the
3b-xviii digits — raw 0.894543 × ωM₁₂ printed first and labelled the miss
it is, corrected 0.939849 (−6.02%) inside the unmoved 10%,
‖S−Sᵀ‖/‖S‖ = 2.5494e-05, ‖S‖₂ = 0.861449; blind-fixture control −98.26%
asserted to fail (`20260813T110940Z_EX-18-example-n2-v3.log`, 135 s). The
systematics ladder was lifted into `src/fem_em_solver/ports/systematics.py`
with a bit-identity test, so example and gate share one definition. Doc
repairs 2026-08-16: guide pass 3 → 0 violations, the 400× band-margin
comment corrected to 7.7× with the band value untouched
(`20260816T033121Z_EX-18-docrefs-fix.log`).

**`EX-14` ✅ 2026-08-10** *(full plan + closure in
`docs/planning/plan-archive.md`)*. Straight-wire VTX export repaired
(writers handed the Lagrange interpolants, split `try`); round-trip
identity exact — read-back max |B| 4.463805898300e-05 T, rel diff
0.000e+00 vs 1e-10 (`20260810T140337Z_EX-14-gate-mag1-v2.log`). The
freshness negctl caught a second real defect: a `.bp` is a directory whose
own mtime never updates — fixed with `artifact_mtime()`. Filed, not fixed:
the identical defect in `02_circular_loop.py` (became `EX-17`).


**`EX-1` ✅ 2026-08-07** *(landed 2026-08-06, demoted for missing runner
logs, restored by `20260807T003044Z_EX-1-runner-mesh1.log`; full history in
`docs/planning/plan-archive.md`)*. `mesh:1` builds the gapped two-torus
fixture (79 534 cells) and asserts the `GEO-8`/`GEO-10` closed-form
identities allreduced — area and volume ratios 1.000000000000, wire ratios
0.963633 / 0.963756 — through the runner. The lesson that outlived it:
§5.4 examples close only on a logged `./run_examples.sh --list` + `-e`
dispatch, not a byte-equivalent direct invocation.

**`EX-2` ✅ 2026-08-07** *(full plan + closure in
`docs/planning/plan-archive.md`)*. `mesh:2` builds `cylindrical_domain()`
at the `GEO-13` defaults and reproduces its classification record exactly
(3 of 6 surfaces accepted, wall 1.111111e-04 × tol, interior
9.999989e+01 × tol); partition identity 1.000000000000000; the plan's
per-tag inscription-band premise was refuted by measurement — at
`resolution = 2 × inner_radius` the inner cylinder is a gmsh heptagonal
prism, gated in closed form at 1.11e-16 (asserted 1e-12). Caller audit:
the 28% inner-volume deficit is latent in every repo caller, armed only if
a test ever gates an inner-region quantity. Log `20260807T140554Z_EX-2.log`.

**`EX-3` ✅ 2026-08-08** *(full plan + closure in
`docs/planning/plan-archive.md`)*. `mri:2` reproduces the `MAT-4` step-3
record digit for digit through the example path: `SAR_avg/SAR_point` =
1.00000000 at 1 g and 10 g, kernel mass 0.0120% / 0.0044%, pointwise vs
closed form 4.96e-16; the exported DG0 array re-averages to the closed form
to 1.32e-15; surface-ball negative control 2.1894 vs lens ceiling 2.1681.
Log `20260808T020414Z_EX-3-gate.log` (14 s, `-n 2`). Imposed field only —
no SAR-on-a-coil claim.

**`EX-29` — the doc-reference checker must freshness-gate every example's
own `paraview_output/`** ✅ *(commissioned 2026-08-23 weekly review, examples
health audit; known-issues entry of the same date. Smoke tier, `-n 1`, no
solve.)* **Defect:** `check_example_doc_references.py` defaults
`--output-dir` to the repo-root `paraview_output/` (`:241-242`) and exempts
any referenced artifact whose basename exists anywhere under `examples/`
(`in_tree_artifacts`, `:276-298`) on the false premise that it is
committed — `.gitignore` ignores `paraview_output/` at every depth, so
**22 of 27** runnable examples are never freshness-checked and every
`stale=24` reading since `OPS-19` has been a census of 5. **Do:** (1)
resolve each referenced artifact at its example-relative path (the
directory the example actually writes, `Path(__file__).parent /
"paraview_output"` for everything outside `mag`/`mri:1`) and apply
`--max-age-s` to all of them; (2) restrict the exemption to paths
`git ls-files` reports as tracked (none today — assert that in the test
so the exemption cannot silently widen again); (3) delete the orphaned
`examples/magnetostatics/paraview_output/` (2026-08-03/04 `circular_loop_*`
leftovers; `02_circular_loop.py` has written to the repo root since
`EX-17`). **Gate (§4):** `tests/unit/test_doc_reference_exit_codes.py`
gains fixtures asserting (a) an *untracked* in-tree artifact older than
`--max-age-s` counts as stale (`exit=2`, `stale=1`), (b) a tracked one
does not, (c) the 47 h / 49 h boundary holds on example-relative paths,
and (d) on the committed tree the `RESULT:` `stale=` figure equals the
count the test computes itself by walking every `examples/**/paraview_output/`
and the repo-root directory with the same age rule — the existing 8 tests
stay green unchanged. **Negative control:** the pre-fix checker on the same
tree must report `stale=24` (the 5-example census) against the post-fix
count — assert the two differ, so the change is demonstrated, not assumed.
**Done-when:** the extended unit file passes at `-n 1` via the harness with
elapsed recorded; the companion docrefs run prints the full-census `RESULT:`
line; `EX-30` is re-sized from that count. No example re-run here.

**Closed 2026-08-24, 06:00 slot.** All three "Do" items landed and the gate is
green twice in-slot: `tests/unit/test_doc_reference_exit_codes.py` **15 passed
in 3.71 s** (`20260824T110512Z_EX-29-unit.log`, harness Elapsed 5 s, `-n 1`)
and the whole `tests/unit` directory **22 passed in 7.33 s**
(`20260824T110540Z_EX-29-unit-run2.log`, Elapsed 9 s) — the 8 pre-existing
`OPS-19` tests unchanged and still green. **The negative control, measured on
the same tree in the same slot:** the pre-fix checker read
`dead=0 guide=0 stale=24 exit=2`
(`20260824T110150Z_EX-29-prefix-control.log`, run before any edit); the
post-fix checker reads `dead=0 guide=0 stale=55 exit=2`
(`20260824T110531Z_EX-29-census.log`, Elapsed 1 s) — the same 36 guides and
117 references, **24 → 55**. Gate (d)'s independent walk of every
`examples/**/paraview_output/` + the repo root reproduces the printed figure
exactly (`stale=55 checked=58 hidden_pre_fix=32`): **32 of the 58 resolved
artifact references live outside the repo-root directory**, i.e. the old
basename exemption hid more than half the census. `EX-30` is re-sized from
**55**, not 24, by a review.

**Two findings the entry's own text did not predict, both measured.** (1) The
tracked set is **not empty**: `git ls-files` reports three committed artifacts
under `examples/` — `ansys_benchmarks/loop_over_lossy_slab_10MHz/metrics.json`,
`ansys_benchmarks/two_torus_gap_ports_10MHz/metrics.json`, and
`magnetostatics/straight_wire_validation.png`. These are exactly the
"committed next to its own case" artifacts the exemption was written for, so
the exemption is kept and **pinned by path** in
`COMMITTED_EXAMPLE_ARTIFACTS` (the "assert it is empty" instruction would have
been a false assertion; pinning the paths serves the same anti-widening
purpose). (2) `git` inside the container fails —
`fatal: detected dubious ownership in repository at '/workspace'`, root over a
host-owned bind mount — and the failure is silent in the *wrong* direction: an
empty exemption made the two tracked `metrics.json` read as **dead references**
(`dead=1 exit=1`, seen on the first run of the day). The checker passes
`-c safe.directory=` for the repo root and the docs root; any future
in-container `git` call needs the same. Both are recorded in known-issues,
whose `EX-29` entry closes with this commit.

**`EX-30` — refresh the 13-example stale artifact set the checker could not
see** ⬜ *(commissioned 2026-08-23 weekly review; §5.4 "XDMF outputs still
reflect current capability" — staleness stated: as of 2026-08-23 the
artifacts of `mesh:1` (~17 d), `mesh:2` (~16 d), `mri:2` (~15 d), `mat:1`,
`th:1`–`th:4`, `ans:1` (~14 d), `th:5` (~13 d), `ports:1`, `th:6` (~10 d)
all predate `OPS-17`'s test replacement and have not been regenerated
since. Heavy tier, `-n 2`, two legs so each fits one slot.)* **`EX-29` landed
2026-08-24, so the checker is now the census instrument and the number to
size against is `stale=55`, not the 24 this entry was written beside
(`20260824T110531Z_EX-29-census.log`); a review re-scopes the two legs from
it before this chunk is queued.** **Leg (a), cheap set:** `mesh:1`, `mesh:2`, `mri:2`,
`mat:1`, `ans:1`, `ports:1` via `./run_examples.sh` (their recorded
in-script times sum to well under 480 s; `ports:1` is the sink at ~134 s).
**Leg (b), time-harmonic set:** `th:1`–`th:6` (`th:6` 24 s, the rest ≤ 60 s
each on record). **Gate (§4):** every example's *own* asserted records
reproduce (the `EX-22` precedent — these examples assert their gated
numbers, e.g. `th:6`'s 3.643% / 1.826% / 3.629% inside a 1% band, `mat:1`'s
Dodd–Deeds ΔR, `ports:1`'s ‖S−Sᵀ‖/‖S‖ = 2.5494e-05), every run exits 0,
and afterwards **no** `paraview_output/` artifact referenced by any guide
is older than 48 h (count by `find`, then by the checker once `EX-29` is
in). **Negative result:** an example whose records do not reproduce is a
finding — record the drift, open a known-issues entry naming the chunk that
owns the record, do **not** re-record; the ramp count in §10 drops by one
until it is adjudicated. **Done-when:** both legs' harness logs with
elapsed, the reproduced records quoted, and the post-run artifact census.

> **Re-scoped 2026-08-24, 10:30 review, from the honest census** (`stale=55`
> across 26 repo-root + 11 `time_harmonic` + 10 `meshing` + 4 `ports` +
> 2 `ans` + 1 `mri` + 1 `materials`;
> `20260824T110531Z_EX-29-census.log`). The two-leg split above was sized
> off the invisible-set estimate and is superseded by **four legs, each
> one slot**, gated differently because the record families differ:
> * **Leg (th)** — `th:1`–`th:8` (11 stale). Analytic-comparison bands at
>   ~1% against ~1e-4 image motion: records expected to reproduce;
>   doubles as the example layer's 0.11 re-gate for the family.
>   **Queueable now** (§9 item 4, 2026-08-24).
> * **Leg (root)** — the repo-root writers (26 stale) + `mri:2` +
>   `mat:1`. Magnetostatics closed forms re-gated on 0.11 (`MAG-18`);
>   queue after leg (th)'s precedent run confirms the pattern.
> * **Leg (mesh)** — `examples/meshing/` (10 stale). These assert
>   cell-count and CAD-mass records the 0.11 image moved (`EX-28`'s
>   116 416 is exactly the constant ruling (5\*) re-records) — **gated on
>   §9 item 1 (leg (d3c)) settling**, then queue with an in-class (1\*)
>   example-record licence for the moved cell counts.
> * **Leg (ports)** — `examples/ports/` (4 stale) + the two `ans`
>   benchmark artifacts. `ports:1`/`ports:3` assert field-route S records
>   the (d3) power-wave assembly moved — **gated on §9 items 1–2 plus an
>   explicit (1\*) example-record licence from a review** (the 03:00
>   review's deferral stands).
> The done-when above applies per leg (harness log with elapsed,
> reproduced records quoted, post-leg census delta); the chunk is ✅ when
> all four legs have run and the census reads 0 stale for their sets.

> **Leg (th) ATTEMPTED 2026-08-24, 16:30 slot — 🟡 not closed; 5 of 8
> examples refreshed, three reds with three distinct causes, nothing
> re-recorded.** Census **55 → 50** against the leg's predicted 44; the
> pre-run control read the standing `dead=0 guide=0 stale=55 exit=2`
> exactly (`20260824T213114Z_EX-30-th-census-pre.log`, 11 of them
> `time_harmonic`), and the post-run count
> (`…T213836Z_EX-30-th-census-post.log`) is **fully attributed**: the five
> that cleared are `th:1`/`th:3`/`th:4`/`th:8`'s artifacts, the six that
> remain are exactly the artifacts of the three red examples, and no other
> family's count moved. Green and reproducing: **`th:1`** 12.6 s (rate
> 0.9998 on the `TH-6` record, α 0.0173% and β 0.0600% against 1%),
> **`th:3`** 7.7 s, **`th:4`** 5.7 s, **`th:8`** 7.8 s — all "All
> assertions hold". **Three reds, each a known-issues entry, none of them a
> record this leg may touch:** (i) `th:2` + `th:5` crash in
> `src/.../core/cavity.py:129/131` — `assemble_matrix(..., diagonal=)` was
> **never migrated to 0.11**, and the gate probe
> (`…T213908Z_EX-30-th-cavity-gate-probe.log`, complex, `-n 2`) reads
> **`4 failed, 9 passed in 2.11s`** with all 9 `tests/environment` green, so
> `TH-9`'s cavity gate and the resonance guard have been **non-executing on
> `main` since the 0.11 merge**; (ii) `th:7` crashes on
> `Function.interpolate(cells=)`, the repo's **only** such site, i.e. an
> example/gate divergence rather than a migration class; (iii) `th:6`'s
> **128 MHz** interior relL2 measures 1.76864% against the `TH-10` record
> 1.826% — a **3.14%** drift on the record's **own 55 241-cell mesh**, while
> **64 MHz reproduces to 4.04e-05** on the same run. The leg's prediction
> ("records expected to reproduce; image motion ~1e-4") is confirmed at
> 64 MHz and wrong by two decades at 128 MHz, and because the mesh did not
> move this is **not** the 0.11-mesh-motion class every prior entry belongs
> to. `TH-10`'s own gate module has not been re-run on 0.11; that single
> standard-tier command is what decides whether (iii) is an example-path
> divergence or a real motion in a figure §2 quotes. **Leg (th) therefore
> needs a review to split off (i) and (ii) as `OPS-18` follow-ons and (iii)
> as a `TH-10` re-gate before it can be re-queued**; the remaining three
> legs are untouched by this. Full journal: `docs/testing/attempts.md`,
> 2026-08-24T21:55Z.

> **Disposed 2026-08-24, 18:00 review.** (i) and (ii) commissioned as
> `OPS-24` / `OPS-25` (§9 items 2–3). (iii) **diagnosed from documentation,
> no run needed**: `TH-10`'s 128 MHz fine rung was already re-recorded
> 1.826% → **1.769%** *with its mesh* (55 251 → 55 241 cells) by `OPS-18`
> step 3 attempt 1 — the green 0.11 log
> `20260822T123746Z_OPS-18-step3-th10-rerun.log` prints relL2 1.769%,
> separation 59.16× at 55 241 cells, exactly what `th:6` measured
> (1.76864% / 59.16×, 2e-4 apart) against its never-updated restated
> constants (0.01826 / 57.31). (iii) is therefore the same class as (ii) —
> example/gate divergence — and the leg is re-queued as §9 item 4 with the
> alignment licence (the two 128 MHz constants re-recorded version-tagged
> from that log, nothing else).

> **Leg (th) ✅ CLOSED 2026-08-25, 00:00 implementer slot — all eight
> examples green, `time_harmonic` census 4 → 0.** The alignment was executed
> exactly as licensed and nothing else was re-recorded:
> `RECORD_INTERIOR_L2[128 MHz]` 0.01826 → **0.01769** and
> `RECORD_SEPARATION[128 MHz]` 57.31 → **59.16** in
> `examples/time_harmonic/06_larmor_lossy_sphere.py`, version-tagged from
> `20260822T123746Z_OPS-18-step3-th10-rerun.log` with the 0.7.2 digits and
> their 55 251-cell mesh kept in-comment beside them; the 1% reproduction
> band and every 64 MHz constant untouched. `th:6` then reproduced **1.769%
> against 1.769% (drift 2.02e-04)** and **59.16× against 59.16× (drift
> 5.45e-05)** at 55 241 cells, with 64 MHz unmoved at 3.643% / 18.67×
> (4.04e-05 / 2.96e-04) — the 18:00 review's documentation-only diagnosis of
> (iii) confirmed by measurement, three decades inside the band.
> **Census, derived not memorized:** the pre-run control read `dead=0
> guide=0 stale=51 exit=2` (`20260825T050102Z_EX-30-th-precensus.log`) with
> exactly **four** `time_harmonic` entries (`th:6` × 2, `th:2`, `th:5` — the
> 16:30 reading of 50 plus item 3's `th:7` refresh landing at 51), so the
> predicted post-run count was 51 − 4 = **47**; the post-run census reads
> **`stale=47`** with **zero** `time_harmonic` entries
> (`20260825T050353Z_EX-30-th-postcensus.log`), and no other family moved.
> All four runs Status 0, `-n 2`, complex, driven in pairs so no red could
> truncate a batch: `th:1`+`th:2` 23 s
> (`20260825T050147Z_EX-30-th-run-1to2.log`), `th:3`+`th:4` 14 s
> (`…T050214Z_…-3to4.log`), `th:5`+`th:6` 55 s (`…T050232Z_…-5to6.log`),
> `th:7`+`th:8` 13 s (`…T050335Z_…-7to8.log`) — **105 s of compute total**,
> commissioned heavy, **measured standard**. `th:2` and `th:5` ran for the
> first time since the 0.11 merge (`OPS-24`) and `th:7` through its hoisted
> import (`OPS-25`), so the leg also served as the example layer's 0.11
> re-gate for the whole family. The `th:6` known-issues entry is retired;
> the companion guide's transcript, drift table and cost line are
> re-recorded version-tagged from the run. **`EX-30` stays 🟡** — legs
> (root), (mesh) and (ports) are untouched and still gated as scoped above.

> **All three remaining legs queued 2026-08-25, 03:00 review (§9 items
> 3–5), each independent.** Leg (root)'s gate — leg (th)'s precedent —
> is discharged by the close above. Legs (mesh) and (ports) carry the
> in-class (1\*) example-record licences their re-scope required (granted
> in §9): named cell-count/CAD-mass constants (mesh) and (d3)-moved
> field-route S constants (ports) re-record **version-tagged from each
> leg's own green run on current `main`**, old digits kept in-comment,
> importing from gate modules per the `ANS-1` rule where feasible; no
> identity band, reproduction band, or gate tolerance moves under either
> licence. Close rule: the last leg to land with all four legs' logs and
> a census reading 0 for the four sets declares the chunk ✅.

> **Leg (root) ATTEMPTED 2026-08-25, 09:00 implementer slot — 🟡 not
> closed; six of eight examples green, two reds, and one of them is a
> validation gate that is red on `main`.** Census **47 → 26**, fully
> attributed and derived, not memorized: the pre-run control read `dead=0
> guide=0 stale=47 exit=2` (`20260825T140117Z_EX-30-root-precensus.log`)
> with this leg's set being exactly **28** entries (26 repo-root + 1
> `mri` + 1 `materials`), so a clean leg predicted **19**; the post-run
> census reads **`stale=26`** (`20260825T141928Z_EX-30-root-postcensus.log`),
> i.e. **21 of the 28 cleared** and the remaining **7 are precisely the
> `straight_wire_*` artifacts of the one example that never meshed**.
> **No other family moved** — `meshing` 13 → 13, `ports` 4 → 4, `ans`
> 2 → 2, and `dead=0 guide=0` both readings. 19 + 7 = 26, exact.
> **Green and reproducing** (Status 0): `mag:2`, `mag:4`, `mag:5`
> (`20260825T140737Z_EX-30-root-run-mag2to5.log`, 231 s) — `mag:5` is the
> quantitative anchor of the set, "All assertions hold" on **all 7** of
> its assertions at **14 055 cells, digit for digit** with its guide's
> recorded mesh; and `mri:1`, `mri:2`, `mat:1`
> (`20260825T141416Z_EX-30-root-run-mri-mat.log`, 88 s) — `mri:2` "All
> identities hold" with SAR against the closed form at **3.31e-16** (point)
> and **2.81e-15** (DG0 field-averaged), 1 g and 10 g ratios
> **1.00000000** against the 0.5% budget and kernel masses 0.0120% /
> 0.0041% against 0.1%; `mat:1` "All assertions hold" with the Dodd–Deeds
> **ΔR relative error 1.5838%** against the 2% ceiling, reproducing the
> `MAT-6` step-3 record of **1.5834%** to 4e-04. **Two reds, both filed,
> nothing re-recorded:** (i) `mag:1` does not mesh at all on 0.11 — gmsh
> "Invalid boundary mesh (overlapping facets)" at
> `mesh.py:304 straight_wire_domain`, at the example's own
> `resolution = 0.01` / `domain_radius = 0.04` parameter set that **no
> gate exercises** (the same generator meshed three times in the very next
> run) — **localised in 29 s** by
> `tests/validation/probe_straight_wire_mesh_resolution.py` to
> `resolution` **alone**: `h = 0.01` fails for every geometry tried
> including the gate's own `L = 0.20 / R = 0.030`, while `h = 0.008 /
> 0.006 / 0.005 / 0.004` all mesh, so it is a coarse-resolution floor in
> the generator on 0.11 rather than an odd box; (ii) `mag:6` exits 1 on **fitted rate 1.9038 outside the `MAG-13`
> band [0.7, 1.5]** — and because that example *imports* the band, the
> resolutions and the fit from `tests/validation/test_convergence.py`
> (the `ANS-1` rule), the gate was probed directly and is **red on `main`
> with the identical number**
> (`20260825T141636Z_EX-30-root-mag6-gate-probe.log`, `1 failed in
> 143.11s`): the finest rung's error collapsed **9.26% → 4.4605%** while
> the middle rung is the already-documented 147 235 cells / 15.3848%.
> That is a `MAG-13`/`MAG-18` finding surfaced by the example layer, not
> an example-side drift, and it means **a magnetostatics convergence gate
> has been red on `main` unobserved since the 0.11 merge**. Both are
> known-issues entries. **Third, smaller finding for the review — the
> re-record licence class:** `mag:2`, `mag:4` and `mri:1` assert nothing
> (0 `assert` statements each) and their guides carry 0.7.2-tagged record
> tables that the 0.11 mesh motion has moved by sub-percent amounts —
> `mag:2` 411 393 → **409 596** cells with relL2 6.3046% → **6.2134%**,
> `mag:4` 70 054 / 103 984 / 160 478 → **69 918 / 103 950 / 160 677**
> cells, `mri:1` phantom `|E|` mean 1.975909e+02 → **1.979842e+02**. This
> is exactly the in-class (1\*) situation legs (mesh) and (ports) were
> granted a licence for; leg (root) has **none**, so the digits stand
> un-re-recorded and the leg asks for one. **Compute:** 907 s across five
> runs plus two 1 s censuses; commissioned standard, measured standard.
> Full journal: `docs/testing/attempts.md`, 2026-08-25T14:30Z.

**`EX-31` ✅ 2026-08-24** — ring-gapped birdcage with dual port families.
`mesh:7`, `examples/meshing/07_birdcage_ring_gap_ports.py` + same-stem guide,
**closed as written on the first run** (log
`20260824T200613Z_EX-31-example-n2.log`, exit 0, **70.6 s in-script / 75 s
harness at `-n 2`**, real build; ring-gapped rung 21.24 s mesh / 23.37 s rung,
leg+ring 25.35 s / 27.32 s, uncut control 17.14 s / 18.63 s — the three builds
are 69 s of the 70.6 s, the `EX-27`/`EX-28` precedent that exports are cheaper
than the meshes holding a third time). Tier: commissioned standard, **measured
standard**. Every gated figure reproduces `GEO-20` step 1's own log
(`20260824T124525Z`) **to the printed digit**, so the example path and the gate
path agree exactly.
**Ring-gapped rung (110 786 cells = the record; 4 leg + 8 ring ports):**
terminal `9.796288043e-05` / `9.796288455e-05 m²` = **0.974454791** /
**0.974454832** of the closed-form `1.005309649e-04 m²` — inside the imported
`[0.95, 1.0]` inscribed band *and* the new `0.974455 ± 1e-5` record band —
with terminal spread **2.099e-08** against the 1e-5 equality gate; closure and
volume/analytic **`1.000000000000`** on all eight against the analytic wedge
(`8.008718871e-07 m³`, surface `5.206757303e-04 m²`); sheet **14 facets,
`1.000000000e-04 m²`, meshed/analytic `1.000000000000`** against `w²`;
out-of-plane spread `5.042e-18`–`1.448e-17` m along each sheet's *own*
azimuthal normal (the `GEO-18` bounding-box planarity check is not reusable on
a radial sheet — the extents read `(7.071068e-03, 7.071068e-03, 1.000000e-02)`,
the `w = 1e-2` rectangle seen edge-on at 45°); C4+mirror spreads **1.666e-15**
(volume) / **2.443e-16** (sheet) against 1e-12; Pappus on the ring primitives
**`1.000000000000`** pre-boolean; `GEO-9` partition < 1e-9; meshed/CAD
conductor **0.969275** ≥ the imported 0.95; phantom-facing area exactly 0 on
all eight.
**12-port dual-family rung (128 402 cells = the record):** both identity
families exact on the same mesh — closure and volume/analytic
**`1.000000000000`** on all 12, leg terminals **0.988615809–0.988615855**
against `GEO-18` step 1's `0.988616 ± 1e-5` and ring terminals against
`0.974455 ± 1e-5`. The two opt-ins do not interact.
**Negative control (inverted, `EX-18`/`EX-28` pattern):** `ring_gap_length=None`
gives cell tags `[1, 2, 3, 101-104]` — the four leg boxes and **no ring port
tag at all** — 98 666 cells (ratio 1.001950 against the module's 98 474 record,
inside its own 1% band: the 0.11 image's count, nothing re-recorded) and
meshed/CAD **0.966977** vs `EX-21`'s 0.967019; and, measured rather than
implied, `_global_facet_count` **= 0** on every ring sheet group `215`–`222`
after running the *same* `_interface_facet_tags` rebuild on that mesh.
**Records hoisted to the gate, not restated in the example** (the `ANS-1`
rule): `RING_TERMINAL_RATIO` = 0.974455 (band 1e-5), `RING_GAP_CELL_RECORD` =
110 786 and `LEG_RING_CELL_RECORD` = 128 402 now live in
`tests/mesh/test_birdcage_ring_gaps.py` and are asserted **there** as well, so
a record that moves fails at its own source; the module re-ran green with them
(`20260824T200739Z_EX-31-gate-module.log`, 2 passed / 70.4 s, `-n 2`, real) —
this is a strengthening of `GEO-20` step 1's gate, no band moved and no
assertion loosened. Four combined XDMFs (ring cells, ring sheet facets
215-222, leg+ring cells, uncut cells). Docrefs
`20260824T200857Z_EX-31-docrefs.log` — **`dead=0 guide=0 stale=55
stale_severity=report exit=2`**, `exit != 1` under the `OPS-19` contract, **28**
runnable examples now scanned (27 before this one), the standing `stale=55`
census unchanged and none of it an `EX-31` artifact.

<details><summary>Original entry (commissioning + rubric)</summary>

**`EX-31` — ring-gapped birdcage with dual port families** ⬜ *(commissioned
2026-08-24 10:30 review; `GEO-20` step 1's ramp obligation — first example
with ring-gap terminals (exact disks from the radial cut planes
`phi = phi_c ± alpha`) and the first **12-port** leg+ring dual-family mesh;
`EX-28` covers leg gaps only.)* `mesh:7`,
`examples/meshing/07_birdcage_ring_gap_ports.py` + same-stem guide,
mesh-only, no solve, two rungs: the ring-gapped birdcage (8 ring ports,
110 786 cells / 20.9 s on record) and the leg+ring 12-port mesh (128 402 /
24.9 s). **Gates (§4, every constant imported from
`tests/mesh/test_birdcage_ring_gaps.py` and the modules it imports,
`ANS-1` pattern, nothing restated):** ring terminal ratio **0.974455** of
the closed-form `2·π·r_ring²` inside [0.95, 1.0], equal across the 8 to
1e-5; closure, port volume, and sheet identities at 1e-9; sheet
out-of-plane along the azimuthal normal < 1e-12; C4 + top/bottom mirror
< 1e-12; `GEO-9` partition < 1e-9; conductor meshed/CAD ≥ 0.95; on the
12-port rung both identity families exact with leg terminals reproducing
`GEO-18`'s **0.988616**; both cell counts inside the module's own 1% band
(0.11-image records taken 2026-08-24 — no re-record licence needed).
**Negative control (`EX-18` inverted pattern):** the kwarg-off uncut rung
with the ring-port tags asserted *absent*. Combined XDMF per rung opening
in ParaView, run via `./run_examples.sh`, docrefs `exit != 1`. **Cost:**
~120 s at `-n 2`, standard. **Negative result:** a record missing its band
through the example path is an example/test divergence finding —
known-issues + this entry, stop.

</details>

**`EX-32` — birdcage 4-port power-wave S-matrix at 10 MHz** ⬜
*(commissioned 2026-08-25 10:30 review, §5.4 ramp on `PORT-9` ✅ 2026-08-25.
Angle no existing example covers: every S-parameter example to date solves
the **two-torus** pair (`EX-20`, `EX-24`, ports:1–3), and the two birdcage
examples (`EX-28`, `EX-31`) are mesh-only — no example has ever solved a
port on the birdcage. Sized for one implementer run.)*
> **Content.** `examples/ports/04_birdcage_four_port_sparameters.py` +
> same-stem guide: mesh the `GEO-18` gapped 4-leg fixture (phantom loaded,
> four `f = 0.5` sheets, step B's mesh-tagged 116 085 cells — a *print*,
> never an assert; the mesh regenerates whole), run
> `run_n_port_sparameter_sweep` on the power-wave route at 10 MHz, print the
> 4×4, the three C4 circulant class spreads, σ_max(S), and the reciprocity
> residual **as an order of magnitude only** (the (d3c) rule — power-wave
> readings sit at ~1e-16…1e-11 and never reproduce digit-for-digit).
> Combined XDMF of the port-1-driven `|B|`/`|E|` in ParaView — the first
> field picture of a driven birdcage port in the examples tree.
> **Anchors (§4), imported per `ANS-1`, never restated:** σ_max and the
> class-spread band from `test_port_birdcage_lumped_column.py`
> (σ_max ≤ 1 + 1e-9; spreads inside (iii′) 0.5% — records 0.999992805,
> 0.0553 / 0.0353 / 0.0214%); leg (d0)'s terminated column via
> `LEG_D0_Z_COLUMN` from `test_port_birdcage_four_port.py` (1e-9-band
> class). **Negative control:** the deprecated heuristic route on the same
> mesh prints an identically-zero off-diagonal with its
> `DeprecationWarning` shown (the `EX-20` pattern). **Cost:** leg (d)'s
> mesh + four solves measured 22.9 + ~31 s; with export budget ~120 s at
> `-n 2`, standard, `timeout -k 30 400`. Complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`. **Traps:** `run_examples.sh` is `set -e`;
> docrefs gate on `exit != 1`; census attribution before/after per the
> `EX-30` discipline. **Scope:** 10 MHz only — the guide states the
> `PORT-9` caveat verbatim (no Larmor, no resonance, no tuning claim; feed
> systematics are the two-torus ones). **Negative result:** an imported
> record missing its band through the example path is an example/test
> divergence finding — known-issues + this entry, stop; nothing
> re-recorded.

### ANS — Ansys benchmark cases (§5.4)

Commissioned by the weekly planning review only, on gated physics only; the
human operator replicates each case in Ansys Electronics Desktop and the
next weekly review adjudicates the returned numbers.

| ID | Title | Status | Tier |
|---|---|---|---|
| `ANS-1` | Loop over a lossy slab at 10 MHz: runnable half of the first AED benchmark | ✅ | standard |
| `ANS-3` | Two coaxial gapped loops at 10 MHz: runnable half of the second AED benchmark (2-port Z/S; `ANS-2` reserved by §10 for the future B1+/SAR case) | ✅ | heavy |

**`ANS-1` ✅ 2026-08-09** *(scoped 2026-08-09, weekly review; full plan and
closure narrative in `docs/planning/plan-archive.md`)*. Runnable half of
the first AED benchmark, dispatched through the runner's `ans:` group
(`./run_examples.sh -e ans:1 -n 2 -t 180`, log
`20260809T183731Z_ANS-1.log`, 70 s): ΔR = +3.2770406e-01 Ω, **1.5834%**
from Dodd–Deeds against the 2% ceiling and 1.387e-08 relative from the
`MAT-6` pin against 1e-3; σ = 0 control exact (0.0 W, 0.0 A/m², asserted
with no tolerance); energy identity ratio 1.0000. `metrics.json`,
`COMPARISON.md` (AED columns blank per SPEC), and the |J| XDMF landed in
the case directory; every constant, mesh, and drive is imported from the
`MAT-6`/`EX-11` modules, so the benchmark cannot drift from the gate. The
AED half is the operator's (§5.4 Waiting-on-you).

**`ANS-3` ✅ 2026-08-16** — two coaxial gapped loops at 10 MHz: runnable
half. Dispatched through the runner's `ans:` group
(`./run_examples.sh -e ans:3 -n 2 -t 500`, log
`20260816T110354Z_ANS-3-runnable-half-n2.log`, **131 s** wall clock, 128.1 s
in-script at `-n 2` on 178 055 cells — mesh 35.9 s, package sweep 46.3 s,
export solve 21.4 s). Every anchor reproduced inside `EX-20`'s pre-stated
1% band, misses ≤ **3.67e-06**: raw mutual 0.894543 (3.33e-07), corrected
0.939849 (3.23e-07), ‖S−Sᵀ‖/‖S‖ = 2.5494e-05 (3.67e-06), ‖S‖₂ = 0.861449
(2.29e-07). Negative control executed and printed **first**: the raw rung
is −10.55% against the unmoved 10% band and is asserted to *fail* it, so
the two systematics are visibly load-bearing; the corrected rung is −6.02%,
inside. Im Z₂₁ = +1.110803269e+00 Ω against ωM₁₂ = 1.241755 Ω;
|Z₁₂−Z₂₁|/|Z₂₁| = 5.8309e-04 (reported, not gated). `metrics.json`
(full complex 2×2 Z and S, ladder, identities, mesh/timing),
`COMPARISON.md` (our columns filled, AED columns blank per SPEC) and the
combined XDMF landed in the case directory; every geometry, drive,
quadrature and correction constant is **imported** from
`examples/ports/02_package_sparameter_sweep.py` (`EX-20`) and
`fem_em_solver.ports.systematics`, so the benchmark cannot drift from the
gate — `ANS-1`'s rule. The 45.7 s heuristic control of `EX-20` is
deliberately absent: this entry names the raw rung as the negative control,
and dropping the heuristic is what brought the case in at 131 s.
The AED half is the operator's (§5.4 Waiting-on-you), and it is also
`PORT-10`'s independent adjudication input. Incidental fix landed with it:
`scripts/run_examples.sh` now issues `timeout -k 30` inside the container —
it was the last compute path still sending a bare TERM to an `mpiexec` job
(the MAT-6 step-10 wedge mode).

<details><summary>Original entry (commissioning + plan)</summary>

**`ANS-3` — two coaxial gapped loops at 10 MHz: runnable half**
*(commissioned 2026-08-16 by the interrupted weekly-scope session —
authoritative spec in
`examples/ansys_benchmarks/two_torus_gap_ports_10MHz/SPEC.md`; this entry
written by the 03:00 daily review to give the commission its runnable-half
chunk, mirroring `ANS-1`'s shape.)* Regenerate the gated two-torus 2-port
numbers through `run_n_port_sparameter_sweep` — the `EX-20` path, never
hand-transcribed — into the case directory: `metrics.json`,
`COMPARISON.md` with our columns filled and AED columns blank per SPEC,
combined XDMF. Dispatch through the runner's `ans:` group
(`./run_examples.sh -e ans:3 ...`).
> **Anchor:** the `PORT-1` step-4 records, reproduced inside `EX-20`'s
> pre-stated 1% band (`EX-20` measured misses ≤ 3.67e-06): corrected ratio
> 0.939849 × ωM₁₂ (ωM₁₂ = +1.241755 Ω filamentary), reciprocity
> ‖S−Sᵀ‖/‖S‖ = 2.5494e-05 against 1e-3, ‖S‖₂ = 0.861449 ≤ 1. **Negative
> control:** the raw rung 0.894543 printed first and asserted to *fail*
> the unmoved 10% band (the `EX-20` inverted assertion). **Tier/cost:**
> heavy by the `EX-20` measurement — 178.2 s at `-n 2` for the sweep plus
> 23.0 s for the export solve (the sweep discards `TimeHarmonicFields`,
> `EX-20`'s named limitation); one command, container `timeout -k 30 500`.
> **Traps:** complex mode + `FEM_EM_REQUIRE_COMPLEX=1`; geometry, drive,
> and correction constants come from the `EX-20`/`PORT-1` modules so the
> benchmark cannot drift from the gate (`ANS-1`'s rule); the docrefs
> checker exits 1 on unrelated stale artifacts (known, benign). **Scope:**
> runnable half only — no adjudication, no coil/birdcage claim; on landing,
> the operator's AED replication goes to the dashboard Waiting-on-you and
> the next weekly review adjudicates (it is also `PORT-10`'s independent
> adjudication input). **Negative result:** any drift from the gated
> records outside the 1% band is a finding about the example path —
> report, annotate this entry, stop.

</details>

---

## 8. Legacy ID mapping

Commit messages, `docs/testing/logs/*.log`, and the retired
`docs/testing/pending-tests.md` (removed 2026-08-04; in git history) use older
IDs. Two generations collided — `E1`–`E4` refer to *different chunks* in
the ROADMAP than in `pending-tests.md`. Resolve via this table.

| Legacy (ROADMAP gen-2) | New ID | | Legacy (gen-1, in `pending-tests.md`) | New ID |
|---|---|---|---|---|
| A1 | `MAG-6` | | C1 (coil+phantom B-solve) | `MAG-1` |
| A2 | `OPS-3` | | C2 (sanity validation metrics) | `MAG-6` |
| A3 | `OPS-4` | | D1 (freq-domain scaffold) | `TH-2` |
| A4 | `GEO-7` | | D2 (phantom material MVP) | `MAT-1` |
| A5 | `OPS-5` | | D3 (E/B extraction) | `POST-1` |
| B1–B6 | `GEO-1`…`GEO-6` | | E1 (port data model) | `PORT-2` |
| C1 | `TH-2` | | E2 (birdcage port tags) | `GEO-1` |
| C2 | `MAT-1` | | E3 (port excitation hook) | `PORT-4` |
| C3 | `TH-3` | | E4 (N-port S-assembly) | `PORT-5` |
| C4 | `POST-1` | | E5 (Touchstone export) | `PORT-7` |
| C5 | `POST-2` | | E6 (calibration checklist) | `PORT-3` |
| C6 | `TH-4` | | F1 (run-and-log metadata) | `OPS-6` |
| D1–D6 | `PORT-3`…`PORT-8` | | F2 (manual checklist doc) | `OPS-7` |
| E1–E4 | `WF-1`…`WF-4` | | | |
| F1–F3 | `OPS-6`…`OPS-8` | | | |

---

## 9. Immediate sequencing

Phase-1/2 analytic gates are closed (§6); the working front is ports
beyond the two-torus fixture and the Larmor-regime validation gate.

1. **The birdcage-port lineage**: step 2's gate **closed at the
   narrowed definition 2026-08-17** (step 2b: ladder
   7.7095 → 3.6730 → **1.8333%** against the unmoved 5% band; the width
   convention `w = A/h` is now part of the port model's spec), and
   **step 2c closed 2026-08-18** (the lumped-sheet sweep route,
   reciprocal at 2.574249e-11 vs the unmoved 1e-3) — step 3's gate (i)
   prerequisite is discharged. **Step 3 is blocked on the mesh
   (2026-08-19/20, legs (a)+(b) 🚫): the birdcage has no port-sheet
   facet and its port boxes have no terminals — the coil is uncut.**
   **`GEO-18` closed 2026-08-22** (step 1 the terminals, step 2 the port
   sheets — 1.120000000e-04 m² = analytic on all four, C4 spread
   8.470e-16), so the mesh prerequisite is discharged, and **step 3's
   4×4 passed all three gates 2026-08-23 on the undisplaced mesh** (leg
   (d): reciprocity 2.495292352e-05 vs 1e-3, σ_max 0.862659137 ≤ 1, C4
   class spreads 0.0199 / 0.0180 / 0.0108% vs 5%, ports at f = 0.5).
   Leg (d1)'s displaced control then **lost reciprocity 223×**, and leg
   (d2) (2026-08-23) traced it to the assembly: the terminated-`Z`
   per-column normalisation, not the readout and not the discretisation.
   Legs (d3), (d3b) and finally **(d1′) all landed; `PORT-9` is ✅
   2026-08-25 at 10 MHz and §2.2 moved with it** (the "no coil or
   birdcage has ports" head is retired; the Larmor claim is `PORT-11`
   step 1, now unblocked).
2. **The 64 MHz h → 0 bracket** §2's extrapolation sentence waits on:
   `TH-11` closed 2026-08-18 (the degree-1 ladder is a measured
   negative — superlinear memory wall), `TH-12` step 2 measured the
   coil at degree 2 against the same wall (61.94 GiB, 96.8% of
   `memory.max`), and the 2026-08-18 18:00 review adjudicated **no
   affordable (order, h) route on this box** (§2.2). Step 3's
   mechanism reading (COIL-SPECIFIC, 2026-08-19) is input to the
   weekly review's production-order decision clause; nothing on this
   front is implementer-ready.
3. Then `PORT-4`…`PORT-8`, then Phase 5 (`WF-5`…`WF-8`).

**Standing rules.** Do not add new features to `⚠️` subsystems. Do not
trust a chunk's status without a log — any §7 status that is not `✅`
reads "unknown", not "probably fine". Since `OPS-19` (2026-08-16), the
docrefs checker exits 0/1/2 (clean / hard violation / staleness-only) and
prints a machine-readable `RESULT:` line — chunks that run examples gate
on **`exit != 1`**, and read staleness (`exit 2`) as information, not
failure.

### On deck — maintained by the scheduled daily review

The next scheduled implementer run takes the **first** item below that is not
marked done or blocked (see `docs/automation/implementer-run.md`). At least five
open items — the four runs before the next review, plus a spare — ordered, each
sized for one run: ≤ 1 h wall clock, ≤ 20 min per compute command. Prefer items
that do not depend on each other; where the critical path is genuinely serial,
say so in the item. Items that fail twice get rescoped by the review before they
may reappear. If every item is done or blocked, the drain instruction at the
end of this section applies: **stop and journal**.

Last reviewed **2026-08-25, 10:30 review**. Interval (since 08-25 03:00):
four slots scheduled, four ran — **one chunk closed, two parked asking
for rulings, one incomplete-but-landed** — plus an interactive operator
session that landed two directives minutes before this review. 04:30 —
item 1's mesh half: the `leg_azimuth_offsets_rad` knob landed green
(`6 passed 81.42 s`; all-zero offsets reproduce step B's 116 085 cells
digit for digit, every `GEO-18` identity survives the 22.5° rotation),
with the finding that the parked branch's mesh commit was superseded by
step B. 06:00 — item 1's solve half: **`PORT-9` closes ✅** — the
displaced 4×4 breaks (iii′) on all three classes (6.2219 / 7.1142 /
2.8474% vs 0.5%) while reciprocity holds at 2.259e-14, separation
**2.466e+11×** from the pre-fix Z-route's 5.57e-03; the (iii′) 5% → 0.5%
tightening committed with all three consumers green (`24 passed
222.15 s`); §2.2's "no coil or birdcage has ports" head retired; the §10
Phase-4 box ticked at 10 MHz on its own pre-stated condition. 07:30 —
item 2: `GEO-19` step C **measured the 16-leg rung** (116 085 → 307 296
cells, 2.6472×; mesh 22.93 → 74.18 s), four of five gates green, parked
on gate (ii)'s equality half (8.434e-04 vs 1e-5, three azimuth classes
≤ 2e-7 tight inside each) — ruled below. 09:00 — item 3: `EX-30` leg
(root) ran six of eight examples green, census 47 → 26 exact and
derived, and surfaced **two reds, one of them a gate red on `main`**:
`test_h_refinement_straight_wire` fits rate 1.9038 outside [0.7, 1.5]
on 0.11 (unobserved since the merge), and `mag:1` no longer meshes at
its own `resolution = 0.01` — localised in a 29 s probe to a
coarse-resolution floor in `straight_wire_domain`, geometry-independent.
Two known-issues entries opened, one retired (blocker B, on its own
retire-when). 10:20/10:26 — **operator directives (interactive
session):** `OPS-26` (the systematic 0.11 migration completeness sweep)
commissioned with instruction "queue at the next review" — queued below;
and the **fixture-scale directive** (F-small/F-human two-fixture split,
§10 Phase 6) — addressed to the 2026-08-30 weekly review, deliberately
**not** acted on here beyond the §6 flag the session itself placed.

**Audit (§4): `PORT-9`'s closure COMPLIANT** — the only ✅ flip this
interval, audited against its own artifacts. All five claimed logs exist
with footers and elapsed times (84 / 108 / 224 / 6 / 3 s, Status 0
throughout); every quoted anchor digit greps out of the cited log
(σ_max 0.999992805 in both runs, 2.258906722e-14 behind the rounded
2.259e-14, the (d0) column at 2.568e-10, the three class spreads
reproducing to the printed digit across both runs); the diff audit found
**exactly one band change, the licensed tightening** (0.05 → 0.005 at
its single source), zero assertions removed, zero skips. Three minor
observations, none §4-violating: (i) the solve/consumers logs record the
parent commit's hash — in-slot run-then-commit, disclosed by the
post-commit collect check, consistent with the `OPS-24` precedent;
(ii) `ADJACENT_SPREAD_BAND` serves both gate directions and the
tightening makes the negative-control exceedance *easier* — immaterial
here since both gated displaced classes exceed even the old 5%;
(iii) one cosmetic stale "(iii)" docstring reference.

**Rulings this review.** (1) `GEO-19` gate (ii) asserts **construction
symmetry** — per-azimuth-class reading, intra-class 1e-6, inter-class
under a 5e-3 discretization ceiling, every existing band unmoved; full
landing instructions in the §7 entry, known-issues entry annotated.
(2) `mag:1` moves to `resolution = 0.008` (probe-cited, old value
in-comment); no generator guard in-slot — the threshold is unbisected
and a guess-constant guard is worse than the documented floor.
(3) The gate red is commissioned as **`MAG-19`** (§7) with a pre-stated
two-branch decision rule — anomalous rung vs wrong instrument —
discriminated by running both norms on the same four-rung ladder; no
band moves in either branch. (4) **Licence:** `EX-30` leg (root)
receives the same in-class (1\*) example-record licence legs
(mesh)/(ports) hold, covering exactly the three **un-asserted guide
tables** its attempt measured (`mag:2` 411 393 / 6.3046% →
409 596 / 6.2134%; `mag:4`'s three rung counts; `mri:1`'s phantom `|E|`
mean), version-tagged from the leg's own green run, old digits
in-comment; no band, tolerance, or asserted record moves under it.

Branch dispositions: **`attempt/GEO-19-20260823T214500Z` deleted this
review** — its mesh-side edits are strictly behind `main` (step B's
local-frame construction superseded them; verified by diff) and its
scaleup module was carried, reconciled, onto
`attempt/GEO-19-stepC-20260825T125000Z` (`e7a3926`), which **stays
parked as item 1's payload**. `attempt/PORT-9-d1-20260823T124500Z` was
deleted by the 06:00 slot after both halves landed green from `main`.
No `recovered/*`; tree clean at every handoff and at this review.
Deliberately not queued: **`PORT-11` step 1** — unblocked by `PORT-9` ✅
and already scoped cost-probe-first in §7 (fixture note updated to step
B's 116 085), but this interval's slots go to the two ruling-unblocked
landings, the operator-directed `OPS-26`, and the `EX-30` drain;
`PORT-11` is first in line at the next review. Also commissioned but
not queued: **`EX-32`** (§5.4 ramp on `PORT-9` ✅ — the first example
solving ports on the birdcage; §7 entry ready). `OPS-26` step 2 is not
queued until step 1's sweep lands (its site list shapes the census).

**Six items: 1–5 independent of each other; item 6 is serial on item 2
and says so.** Items 4–6 are the three remaining `EX-30` legs; each
closes on its own census arithmetic (the chunk goes ✅ only when the
last leg can point at all four legs' logs and a census reading 0 for
their sets). Still unqueued by design: `PORT-11` step 1, `GEO-20`
step 2 (serial on `GEO-19` ✅ — item 1 is what unblocks it), `OPS-26`
step 2, `EX-32`, and `PORT-4`…`PORT-8`.

**⚠️ Standing constraint on the compose allow — read before editing that
file.** `docker-compose.yml` line 9 is `- ..:/workspace`, so write access
to it is write access to *what the container mounts from the host*. The
operator granted this knowingly and narrowly (2026-08-22). **Edit only
`environment:` keys. Do not touch `volumes:`, do not add a mount, do not
widen a path, and do not change the memory limit (**128 G**, raised from
64 G by operator directive 2026-08-24) — in this or any future chunk.** A chunk that believes it needs a mount change is a **blocked
finding for the operator**. The `Edit(docker/.claude/**)` caution stands
for the same reason: a nested `.claude/` is a settings-override surface.
One surviving mechanic: `git checkout` cannot swap `docker/Dockerfile` /
`docker-compose.yml` in this sandbox — bind-mounted, "Device or resource
busy", a *silent* wrong-content switch — so any chunk that must move them
uses the Edit tool and verifies `git status --porcelain`.

1. ✅ **DONE 2026-08-25, 12:00 slot — `GEO-19` closes.** The ruled module
   is green from `main` (`2 passed` / 117 s,
   `20260825T170316Z_GEO-19-stepC-ruled.log`; record run
   `…T170523Z…-ruled-record.log`). Gate (ii) per azimuth class, keyed off
   the mesh's own coordinate mirrors: intra **1.923e-07 / 5.849e-08 /
   6.144e-08** vs 1e-6, inter **8.431e-04** vs 5e-3; the 4-leg control is
   **one** class at 3.184e-08 (the back-compat identity). Every anchor the
   item named reproduces — partition/closure/halves/`dx·g` 1.000000000000,
   C16 sheet spread 1.331e-15, conductor 0.981503, margin 1.560723×,
   control 116 085 cells delta 0 / C4 spread 6.050e-16 — and the cost rung
   is **116 085 → 307 296 cells (2.6472×), mesh 22.99 → 74.37 s
   (3.2346×)**. Known-issues terminal-equality entry retired,
   `GEO-20` step 2 unblocked, attempt branch deleted. *(Original item:)*
   **`GEO-19` step C — land the parked 16-leg module under this
   review's gate-(ii) ruling (standard, `-n 2`, real, `main`;
   independent).** Take `tests/mesh/test_birdcage_port_scaleup.py` from
   `attempt/GEO-19-stepC-20260825T125000Z` (`e7a3926`), apply the
   **construction-symmetry ruling** (full landing instructions in the
   `GEO-19` §7 entry): gate (ii)'s equality becomes per-azimuth-class —
   intra-class ≤ **1e-6** (measured basis ≤ 2e-7 at 16 legs,
   3.184e-08 at C4), inter-class spread ≤ **5e-3** (measured basis
   8.434e-04; the ~1.1e-2 inscribed-under-read owns the effect), the
   three class values printed with their azimuths; the absolute
   [0.95, 1.0] band, the C4 modules' 1e-5, and every other gate
   **unmoved**. Then run gates (i)–(v) at `leg_count = 16` from `main`
   and land. **Anchors:** the ruled gate (ii) plus the four already-green
   gates reproduce the 07:30 measurement — partition/closure/halves/
   `dx·g` at 1.000000000000, C16 sheet spread ~1.3e-15, conductor
   0.981503, separation margin 1.560723×, and the cost rung 307 296
   cells / ~74 s restated as the chunk's deliverable. **Negative
   control:** the in-module 4-leg build reproduces step B's mesh-tagged
   record digit for digit (116 085 cells, delta 0, C4 spread 6.050e-16,
   ratios 0.988616 × 4) — and at 4 legs the per-class reading *is* the
   old gate (one class), which is the back-compat identity. **Cost:**
   measured 114 s at `-n 2` for the full module (07:30 run); mesh 74 s;
   `timeout -k 30 600`, commissioned heavy for headroom, expect
   standard. **Traps (paid):** the rank-0 `KeyError` report deadlock —
   the parked module already carries the broadcast guard, keep it; gmsh
   fresh model per count; cell counts are prints, never asserts; delete
   the attempt branch only after green from `main` (the 08-23 ancestor
   branch is already deleted by this review). **Scope:** closes
   `GEO-19` ✅ (mesh identities at 16 legs + Phase 6's first measured
   cost rung), retires the terminal-equality known-issues entry, and
   unblocks `GEO-20` step 2; no solve, no port claim, no F-human claim
   (fixture scale is the weekly review's §10 question). **Negative
   result:** a red under the *ruled* reading — intra-class > 1e-6 or
   inter-class > 5e-3 — is a genuine generator finding the three-class
   table cannot explain: known-issues + §7, chunk stays 🟡, stop; never
   widen.
2. 🚫 **BLOCKED ON A RULING 2026-08-25, 13:30 slot — the measurement is done;
   the pre-stated rule selects neither branch.** The 4×2 table exists and both
   anchors reproduce digit for digit (sampled three-rung fit **1.9038**, the
   red; `E_Ω` fit **1.6854** and its h = 0.0025 record within **2.094e-08**
   through the imported machinery). (a) fails — a *second* out-of-band sampled
   pair avoids h = 0.0018 (0.004→0.003 at **0.5822**, on the very rung (a)
   would promote); (b) fails — dropping h = 0.0018 alone returns the sampled
   fit to **0.7309**, inside the band, so the instrument is not unstable
   everywhere. New constraint for the ruling: `E_Ω` is stable (pairwise
   1.4261–1.9843, fits 1.6661–1.8588, 6/6 above its own one-sided ≥ 0.7) but
   sits **above 1.5 everywhere**, so the two-sided band cannot simply be
   *transferred* onto it. Three options are laid out in the §7 entry; no band
   moved, nothing re-recorded, `mag:6` deliberately not run (no gate changed).
   Log `20260825T183555Z_MAG-19-step1-dualnorm-fits.log`, 160 s at `-n 2`;
   probe `tests/validation/probe_straight_wire_dual_norm.py` landed on `main`
   (asserts nothing). **The next slot takes item 3.** *(Original item:)*
   **`MAG-19` step 1 — discriminate the red straight-wire rate gate:
   anomalous rung vs wrong instrument (standard, `-n 2`, real, `main`;
   independent).** Execute the §7 `MAG-19` entry as written: one command
   re-runs the three-rung ladder **plus h = 0.0030**, computes the
   sampled 10-point norm *and* the imported `MAG-18` `E_Ω` norm on the
   same four solves, prints the 4×2 table and all pairwise rates, and
   applies the **pre-stated decision rule** (§7): consistent-except-
   0.0018 ⇒ reading (a), re-choose the sequence (0.0030 the candidate),
   old sequence in-comment, band unmoved; scattered-everywhere-while-
   `E_Ω`-consistent ⇒ reading (b), duty transfers to the live `MAG-18`
   gate and this test keeps monotone decay + the table as report;
   neither ⇒ report, update known-issues, stop at 🟡. **Anchor:** the
   red reproduced first — 21.8417 / 15.3848 / 4.4605% digit for digit
   against `20260825T141636Z` — then the disposition's own green,
   including `-e 6` as the consumer check (`mag:6` imports everything
   per `ANS-1`; zero example-side edits expected). **Negative control:**
   the `E_Ω` ladder's 0.11 record (rate 1.6854, `MAG-18` re-gate logs)
   must reproduce through the imported machinery — if *it* moves, the
   import is wrong, not the physics. **Cost:** the three-rung probe
   measured 143 s; +0.0030 (~80 k cells) ≈ +15 s; one command inside
   `timeout -k 30 400`, plus the `-e 6` run (~145 s). **Traps:** §7
   entry's list (O(h) sampling noise, the 383 k-cell finest rung, the
   `ANS-1` import direction). **Scope:** disposes of the gate red only;
   `mag:1`'s mesh floor is item 6's, and `[0.7, 1.5]` never widens.
   **Negative result:** the neither-branch outcome is itself the
   finding — known-issues updated with the 4×2 table, stop.
3. **`OPS-26` step 1 — the static 0.11 migration sweep (smoke, no
   solves, `main`; independent; operator-directed).** Execute the §7
   `OPS-26` step 1 as written: sweep `src/` and `tests/` for call sites
   whose signature changed between 0.7.2 and 0.11, **introspecting the
   installed module in the container** (`inspect.signature`) rather than
   checking a hardcoded list — the known five renames are the ones
   already found; the sweep's value is the sixth. **Anchor:** a
   machine-checkable count of call sites per changed API, reconciled
   against the sites the five landed migrations touched, with zero
   un-migrated sites surviving — or each survivor named with module and
   line. **Negative control (binding):** the checker must flag a
   deliberately reverted call site in a temp copy — a sweep that cannot
   fail is not a sweep. **Cost:** smoke; container import + AST/grep
   passes, no mesh, no solve; one command, `timeout -k 30 120`.
   **Traps:** `--collect-only` proves nothing (both found defects
   collect clean); a survivor is *filed*, never fixed in-slot (each
   becomes a known-issues entry naming module/line — the `OPS-24`/
   `OPS-25` pattern); no band may move to make anything green.
   **Scope:** step 1 only — step 2 (the execution census, heavy,
   2+ slots) is deliberately not queued until this lands, because the
   site list shapes it. **Negative result:** survivors found is the
   *successful* outcome (each filed); zero survivors with a working
   negative control closes step 1 and is equally informative.
4. **`EX-30` leg (mesh) — `examples/meshing/` (standard, `-n 2`, real,
   `main`; independent; licence granted 03:00 review).** The stale
   meshing artifacts — the 09:00 slot's census read **13**, not the 10
   this item first quoted (staleness is wall-clock); size against 13
   and derive in-run. The 0.11 image and step B moved cell-count and CAD-mass
   records (`EX-28`'s constants are exactly the class rulings (5\*)
   and (6\*) re-recorded on the gate side); the licence above covers
   re-recording those **named constants** version-tagged from this
   leg's own green runs on current `main` (cite the commit hash), old
   digits kept in-comment. **Anchors:** the *identity* assertions are
   the quantitative gates and none of them moves — closure and
   `dx·g` = 1.000000000000-class identities, `GEO-9` partition, C4/
   mirror spreads at their existing tolerances — plus the derived
   census (meshing 13 → 0, attributed pre/post, no other family
   moved). **Negative control:** any path step B's invariance log
   pinned reproduces digit for digit (gapped 114 655, sheeted 116 085,
   no-gap 98 666 where an example exercises it). **Cost:** meshing
   examples record ~20–25 s each; two paired commands,
   `timeout -k 30 660` each; real build. **Traps:** re-record from
   *this leg's own run*, never from a prior log — items 1–2 may land
   mesh-adjacent code earlier in this interval, and the version tag
   must name the commit actually run; gmsh fresh model per example;
   the licence covers counts and CAD masses only — an **identity** red
   is a generator finding, not a re-recordable drift. **Scope:** this
   leg only. **Negative result:** identity red ⇒ known-issues + §7,
   nothing re-recorded, stop; count drift outside any stated
   reproduction band on a *licensed* constant is re-recorded under the
   licence with the delta quoted in the commit.
5. **`EX-30` leg (ports) — `examples/ports/` + the two `ans` artifacts
   (standard, `-n 2`, complex, `main`; independent; licence granted
   03:00 review; spare for the four pre-review slots).** The 4 stale
   `ports` + 2 `ans` artifacts.
   `ports:1`/`ports:3` restate field-route S records the (d3)
   power-wave assembly moved (e.g. the old `‖S−Sᵀ‖/‖S‖ = 2.5494e-05`
   class); the licence covers re-recording those named constants from
   the gate modules' current records — **import per the `ANS-1` rule
   where feasible rather than restate**, so this class of divergence
   cannot recur. **Anchors:** every example's own gates green with the
   reciprocity figure recorded as an **order of magnitude** ((d3c) —
   power-wave readings sit at ~1e-16…1e-11 and do not reproduce
   digit-for-digit; never pin one at a print band), σ_max ≤ 1 + 1e-9
   class checks unmoved, the `ans` pair reproducing their benchmark
   records; derived census (`ports` 4 → 0, `ans` 2 → 0, attributed,
   no other family moved). **Negative control:** the census
   attribution; the retired heuristic route must stay retired (its
   `DeprecationWarning` is the tell). **Cost:** `ports:1` is the
   recorded sink at ~134 s; budget two commands, `timeout -k 30 660`
   each; complex build + `FEM_EM_REQUIRE_COMPLEX=1`. **Traps:**
   `run_examples.sh` `set -e` batching; the 1e-3 reciprocity band and
   every other band stay unmoved — the licence is for record
   constants only. **Close rule:** whichever of items 4–6 lands last
   and can point at all four legs' harness logs with a census reading
   0 for the four sets declares `EX-30` ✅ in its commit; otherwise
   the leg closes and the chunk stays 🟡. **Negative result:** an
   example red its own gate module does not explain is a fresh
   finding — known-issues + §7, nothing re-recorded, stop.
6. **`EX-30` leg (root) completion — the two ruled reds plus the
   licensed guide tables (standard, `-n 2`, mixed builds, `main`;
   SERIAL: depends on item 2 having landed a green disposition for
   `mag:6`'s gate — if it did not, skip this item and journal why).**
   The 09:00 attempt did the measuring (six of eight green, census
   47 → 26 exact); this slot executes the three rulings and closes the
   leg. (i) Move `mag:1` to `resolution = 0.008` per the 10:30 ruling
   (old 0.01 in-comment citing `20260825T142512Z_…-mag1-mesh-probe.log`);
   run it; its 7 `straight_wire_*` artifacts are the leg's entire stale
   remainder. (ii) Re-run `mag:6` — green by item 2's disposition with
   zero example-side edits expected; if it is *not* green, stop and
   journal (do not touch the example to make it so). (iii) Under the
   leg's (1\*) licence (granted above): re-record the three un-asserted
   guide tables — `mag:2` (409 596 cells / 6.2134%), `mag:4`'s three
   rung counts (69 918 / 103 950 / 160 677), `mri:1`'s phantom `|E|`
   mean (1.979842e+02) — version-tagged from this slot's own runs,
   citing the commit hash actually run; old 0.7.2 digits in-comment.
   **Anchors:** `mag:1`'s own in-file assertions green at 0.008 and the
   B-field closed form it prints; `mag:6` green through the item-2 gate;
   census derived — pre-count, attribute the 7, predict 26 − 7 = **19**,
   assert the derived number and that no other family moved (19 =
   meshing 13 + ports 4 + ans 2, which items 4–5 own). **Negative
   control:** the census attribution; and the re-records are guide-table
   only — any *asserted* record drifting is a finding, never a
   re-record. **Cost:** `mag:1` at 0.008 meshes in 2.6 s (probe); the
   09:00 slot's green batches measured 231 + 88 s; two paired commands,
   `timeout -k 30 660`. **Traps:** `run_examples.sh` `set -e` batching;
   real build for `mag:*`, complex where the header says so; the
   `mag:1` teardown-hang trap (`th:6` class) — a red here burns its
   window in `MPI_Abort` teardown, so run `mag:1` first and alone.
   **Scope:** this leg only; retires the `mag:1` known-issues entry
   (the floor finding re-heads and stays, per the ruling); the close
   rule in item 5 applies if this lands last. **Negative result:**
   report the measurement, known-issues + §7, chunk stays 🟡, stop.
*(The per-review journal — slot recap, completion audits, plan-work notes,
§10 assessment — lives in the review commits and
`docs/planning/plan-archive.md`, not here.)*

If the queue drains: **stop and journal.** There is no fallback chunk:
`PORT-9` step 3's legs are serial by design — (d) is not queued until
(d0) has a margin — and a review scopes each leg from the previous one's
number, not an implementer in-slot. History of the birdcage-port hold in
`docs/planning/plan-archive.md`.

Every frequency-domain command needs `source /usr/local/bin/dolfinx-complex-mode`
**and** `FEM_EM_REQUIRE_COMPLEX=1`, with `tests/environment` first in the pytest
path list, so an environment regression fails before the formulation tests get
blamed.

---

## 10. Success criteria and long-horizon roadmap

### MVP (end of Phase 2)
- [x] Time-harmonic solver reproduces the analytic lossy plane-wave solution to < 5% *(3.61% in L2; decay constant 0.019%, `TH-6`)*
- [x] Helmholtz coil magnetostatic result matches analytic to < 5% *(0.04%)*
- [x] Phantom σ and εᵣ measurably change the solved field *(σ: interior decay
  constants each match their own closed form and their ratio is 10.3232 vs the
  closed-form 10.3116, `MAT-2`; εᵣ: at εᵣ = 78 the measured β = 27.03 rad/m
  matches the εᵣ-dependent closed form 27.02 to 0.059% where vacuum would give
  2.68, `TH-6`. The loaded-**coil** claim landed 2026-07-31: the FEM ΔR of a
  loop over a conductive half-space matches Dodd–Deeds to 1.58%, `MAT-6` step
  2b — in the eddy-current regime, not yet at saline/Larmor; step 3 extended it
  to the production projected drive at 1.5834%, 2026-08-04.)*

### Target (end of Phase 4)
- [x] Loaded birdcage + phantom simulation runs end to end **at 10 MHz**
  *(ticked 2026-08-25 with `PORT-9` ✅ — the box's own condition below was
  "this box ticks at 10 MHz when leg (d1′) lands", and it landed: the
  displaced 4×4 breaks gate (iii′) on all three classes by two orders
  while reciprocity holds at 2.259e-14. **The Larmor-frequency claim is
  `PORT-11` and is unrun** — nothing here licenses a 64/128 MHz figure, a
  resonance or a tuning claim. Original text, kept:)* *(the mesh half is
  done: both fixtures generate and are identity-gated in CI as of 2026-08-03,
  `GEO-9` steps 1 + 2b, and graded conductor sizing is gated as of
  2026-08-16, `GEO-15`. The two-torus excitation lineage closed —
  `PORT-1` ✅ 2026-08-15. What remains is ports on the birdcage itself:
  `PORT-9` 🟡 — as of 2026-08-23 the gapped, loaded birdcage has a solved
  lumped-sheet port column at 10 MHz with two pre-stated gates passed
  (C4 spread 0.0152–0.0159% vs 5%; 50 Ω termination margin 598× vs 10×),
  and as of the same day the **4×4 with reciprocity/passivity/C4 is
  solved and green** (leg (d): 2.495292352e-05 vs 1e-3, σ_max
  0.862659137, class spreads 0.0199 / 0.0180 / 0.0108% vs 5%). What is
  left is leg (d1), the geometric negative control of the C4 gate; this
  box ticks at 10 MHz when it lands, and the Larmor-frequency claim is
  `PORT-11`. **Leg (d1′) landed 2026-08-25 and `PORT-9` is ✅** — on
  `GEO-19` step B's mesh and the (d3) power-wave assembly the records are
  σ_max 0.999992805 and spreads 0.0553 / 0.0353 / 0.0214% against the
  tightened (iii′) 0.5%.)*
- [ ] S-parameters derived from the solved field, not a coupling heuristic
  *(the **route** is done — `PORT-1` ✅ 2026-08-15:
  `run_n_port_sparameter_sweep` reads the solved field end to end,
  `‖S−Sᵀ‖/‖S‖ = 2.5494e-05` vs the 1e-3 gate, heuristic retired behind a
  `DeprecationWarning`; reproduced through `EX-20` and `ANS-3` to
  ≤ 3.67e-06. Corrected 2026-08-16, weekly review — the previous
  parenthetical's "still calls the heuristic" predated step 4. The box
  stays unticked because the only fixture with ports is the two-torus
  pair: it ticks when the same machinery gates on the birdcage,
  `PORT-9`.)*
- [ ] S-matrix satisfies reciprocity and passivity within stated tolerance
  *(demonstrated on that same fixture, and as of `PORT-1` step 3a, 2026-08-03,
  through **`PORT-5`'s own metrics** rather than the test's arithmetic:
  `passivity_max_sigma = 1.000000000000` and unit column power sums to `1e-9`,
  `reciprocity_max_abs_delta = 3.4981e-13`. Left open because the matrix is
  still a two-loop air fixture's; what step 3a removed was the "placeholder
  matrices only" objection. **The sweep-level clause is now discharged** —
  `PORT-5` step 1, 2026-08-16: the report `run_n_port_sparameter_sweep`
  returns on the field route reproduces the gated `‖S‖₂` to 1.97e-07 and
  `‖S−Sᵀ‖/‖S‖` to 9e-11, warning-free, with both negative controls
  executed. What keeps the box unticked is the *fixture*, not the route.)*
- [ ] B1+ field matches literature/measured data qualitatively *(routes through
  the coil+phantom fixture, which `GEO-9` step 1 gated on 2026-08-03; nothing
  has yet computed B1+ on it.)*

### Long-horizon roadmap — owned by the weekly planning review

The weekly review (docs/automation/weekly-review.md) maintains this section
with brutal realism: phase goals, subgoals within phases, and dated
assessments extrapolated from **measured pace**, never from hope. Rules of
engagement: a subgoal that has not moved in a month is rescoped or killed, not
carried; parity claims are per-workflow, never per-product (§1); a phase goal
without a named validation target (closed form, literature value, or AED
comparison) is not a goal; every phase milestone lands an `examples/` case
and, where gated physics supports it, an Ansys benchmark case (§5.4).

First weekly review 2026-08-09: re-derived from measured pace per the
seeding note; owned here thereafter. "Phase 5 (current)" is the organizing
goal, not a claim that §6's phases 2–4 are closed — their open gates
(`PORT-1`, the Larmor-regime validation, coil-driven SAR) *are* the content
of the loaded-birdcage goal, and §6 stays authoritative for gate status.

**Pace ledger** *(week 2026-08-02 → 08-09, the first measured week — full
ledger in `docs/planning/plan-archive.md`)*: 47 items reached §4-✅ from 72
journaled implementer slots at a 65% slot-completion rate; measured
throughput 12 ✅ port steps/week, 5 analytic gates/week when focused. The
measured risk to pace is reliability (host downtime, harness kills,
human-gated decisions), not physics.

**Pace ledger, week 2026-08-09 → 08-16** *(measured 2026-08-16, weekly
review; sources: 105 commits `7e93fe3..`, 78 attempts.md entries)*:
**51 items reached §4-✅** (24 chunk closures + 27 further gated steps) —
throughput per fired slot *rose*, but ~30 of the week's ~112 scheduled
slots produced nothing, none for physics reasons: 14 lost to a ~23.8 h
host outage, 12 to a drained §9 queue (downstream of the dead reviews),
4 review slots dead on the usage limit, 2 to API 529s. Where slots fired:
9 port-lineage steps (subgoals 1–2) and 7 Larmor-gate items (subgoal 3)
landed — consistent with the 08-09 throughput numbers. Last week's
verdict stands and sharpened: **the binding constraint is slot
reliability, not solve difficulty.** Mitigations landed this week: §9
restock floor ≥ 6 mutually independent items (08-15 review), weekly slot
moved past the 02:00 usage reset (`5478b20`), `OPS-18` upgrade cadence;
the outage class has no in-repo mitigation (dashboard Waiting-on-you).

**Pace ledger, week 2026-08-16 → 08-23** *(measured 2026-08-23, weekly
review; sources: 107 commits `ce4572b..5ca8c1f`, 78 attempts.md entries,
+224 rows in test-results.md)*: **39 items reached §4-✅** (20 chunk
closures + 19 further gated steps) — down from 51, **−23.5%**. Attribution:
subgoal 2 (ports) **10** — `PORT-9` steps 1/2/2b/2c, `GEO-16`, `GEO-18`
+ step 1, `EX-23`/`EX-24`/`EX-28`; subgoal 3 (Larmor) **8** — `TH-11` +
steps 3/4/5a, `TH-12` steps 1–3, `EX-25`; subgoals 1 and 4 **0**;
infrastructure/examples/other **21** (`OPS-17` + 3 steps, `OPS-19`–`23`,
`OPS-18` steps 1–2, `GEO-17`, `MAG-17`, `POST-5` + 3 steps,
`EX-21`/`22`/`26`/`27`). Physics share 18/39 = 46% (was 31%). Slot
ledger: 78 journaled slots, **67 fired with work** (40 complete, 25
incomplete, 13 blocked), **11 lost to non-physics causes** (14%): 10
drained to an empty §9 after **four consecutive daily reviews died on the
usage limit** (08-20 10:30 → 08-21 10:30; the review launchers run
`claude-fable-5`, the implementer launcher `claude-opus-5`, and only the
former was out of credits — `c57b12a`), 1 to the `Edit(docker/**)` ask
rule (`647b390`, cleared by `c724575`). No host outage this week. Seven of
~21 scheduled reviews did not fire. The verdict sharpens a third time:
**the governing half is the unreliable half** — every implementer slot ran;
the slots that produced nothing were starved by dead reviews, and §9's
restock floor (≥ 6 items) is the only in-repo mitigation. Docs-only
attempts that produced no ✅: 23 commits (`OPS-17` leg (b2) ×10, `OPS-18`
step 3 ×7, `TH-11` 5b ×2, other ×4) — the `OPS-18` upgrade alone consumed
7 slots this week on *records*, not physics, and is now stuck on a
reproduction criterion (bit-identical re-runs) that known-issues shows is
unachievable at ~1e-10 run-to-run noise; that ruling is the daily review's
to re-make, and this review notes only that the upgrade is the week's
largest non-physics sink.

**Phase 5 — loaded birdcage RF (current).** Subgoals, each with its
validation target:

1. *Port-estimator adjudication* — the licensed gapped-vs-closed
   discriminator at σ = 800 (weekly-review licence 2026-08-09 in the
   `PORT-1` entry: two-slot budget, pre-registered disposition, branch
   lands with the lineage's first ✅ gate). Target: matched-topology
   consistency identity on the two-torus fixture. **Update 2026-08-12
   (operator session, textbook-grounded — §7 `PORT-1` adjudication):** the
   second slot is re-pointed to gap-region h-refinement (step 3b-xvi;
   Jin's feed-modeling practice, and 45% of the loop EMF sits sub-cell),
   all outcomes proceed to the 3b-i/ii port-pair gate with a stated,
   labeled systematic, and further σ-placement or `∫E·dl`-variant
   diagnosis is barred. The 08-09 assessment's step count stands.
   **Closed 2026-08-16 (weekly review):** the lineage terminated —
   `PORT-1` ✅ 2026-08-15 on the matched-topology gate (reciprocity
   2.5494e-05 vs 1e-3 through the package entry point), and the one
   question this subgoal left open, whether the two named systematics
   compose, was answered by `PORT-10` ✅ 2026-08-16: cross-term
   **−0.0604 pp** against a pre-stated ±0.5 pp band — additive, the
   sequential ladder in `ports/systematics.py` stands as measured.
2. *Honest S-parameters from the package* — gap-voltage `V = −∫E·dl` ports,
   `excitation.py` replaced, N-port Z from single-port solves, then the
   same machinery on the birdcage mesh. Targets: cross-route identity
   (gap-voltage Z vs reaction Z on the same solved field), reciprocity
   below stated tolerance, and the `PORT-5` metrics on a package-produced
   S-matrix. **Assessment 2026-08-09:** remaining work ≈ 20 ± 5 steps at
   the landed grain (discriminator + re-point + the deferred 3b-i/ii pair
   gate + V/I estimator + single-port Z + `excitation.py` + birdcage tags +
   N-port assembly); measured port throughput 12 ✅ steps/week ⇒ 20/12 ≈
   **1.7 weeks — ports on the birdcage ≈ 2026-08-19…26**. *(Note
   2026-08-12, operator session: for the birdcage itself, the port
   definition should move toward a lumped/circuit-element port boundary
   condition rather than further gap-voltage estimator variants — Jin
   ch. 11's hierarchy; theory now in-repo at `docs/references/jin-fem-3e/`.
   The two-torus `∫E·dl` machinery stays what the 3b-i/ii gate validates,
   with its systematic stated.)* **Assessment 2026-08-16:** the
   two-torus half of the 08-09 estimate is **done** — 9 subgoal-1/2
   steps landed this week (3b-xvi/xvii/xviii, step 4/chunk ✅, `PORT-5`
   step 1, `PORT-10`, `GEO-15`), and both `PORT-9` prerequisites are
   measured (composition additive; graded conductor sizing 0.967 of CAD
   mass, budget from 98 k cells). What remains is the birdcage half:
   `PORT-9` (lumped-element port BC, Jin ch. 11 — scoped ⬜, not
   started), ≈ 8–12 steps at the landed grain; at the measured 9–12 port
   steps/week ⇒ **≈ 1 week of fired slots — ports on the birdcage
   ≈ 2026-08-23…27**, the tail of the 08-09 window. The 08-09 watch
   condition resolved honestly: 3b-xvi needed a third slot (two parked
   attempts), but the re-pointed round converted and the lineage closed
   two days later — no re-plan forced. **Assessment 2026-08-23 — the
   watch condition fired, so this is a re-plan, not an extension.** The
   08-16 condition was "`PORT-9`'s first gated step on the birdcage by the
   08-23 review". By the letter it is **not met**: no birdcage *step* is
   ✅, step 3 stays 🟡, and §2.2's "no coil or birdcage has ports" stands.
   By measurement it is close: two pre-stated birdcage gates passed this
   week — leg (c) C4 adjacent spread **0.0159%** vs 5% (08-22), leg (d0)
   discrimination margin **598.4×** vs 10× at `Z_p = 50 Ω` with the
   spread at 0.0152% (08-23) — and the 4×4 with gates (i)–(iii), leg (d),
   is priced at ~30 s standard. Where the estimate went wrong, named: the
   8–12 steps were spent as 4 two-torus steps + 2 gated birdcage legs +
   **2 steps of an unnamed mesh prerequisite** (`GEO-18`: the fixture had
   no terminals and no sheet — legs (a)/(b) 🚫 measured it) + 2 🚫 legs;
   the prerequisite cost three calendar days (08-19 → 08-22), one of them
   the dead-review day. **Re-plan:** (2a) *10 MHz birdcage network* = leg
   (d), one slot — `PORT-9` ✅ and the Target box "loaded birdcage … runs
   end to end" ticks at 10 MHz, but the mission's ports are at 64/128 MHz,
   which the 08-16 subgoal never named; (2b) *Larmor ports* is therefore
   new content, scoped as **`PORT-11`** (§7, serial on `PORT-9` ✅: one
   priced 64 MHz probe, then gates (i)–(iii) at 64 MHz with the 10 MHz
   sweep as the in-run control, then 128 MHz) — ≈ 3–4 steps at the landed
   grain. Arithmetic at the measured 10 port-lineage items/week: 1 + 3–4
   ≈ 0.5 week of fired slots ⇒ **`PORT-9` ✅ ≈ 2026-08-24, Larmor birdcage
   ports ≈ 2026-08-28…31** if reviews fire. Watch condition for 08-30: if
   `PORT-11` step 1's probe has not landed a price by then, the lineage is
   not "one more step" and the 08-30 review re-plans again rather than
   extends.
3. *Larmor-regime validation gate — this phase's real content.* Every
   loading/SAR gate today is eddy-current (10 MHz) or imposed-field; saline
   at 64/128 MHz is an extrapolation (§2.1). Named targets: the lossy
   dielectric sphere in a full-wave field at 64/128 MHz against its
   analytic series solution (the `TH-8` machinery carried into the
   displacement-current regime), and the coil-loading trend vs frequency
   crossing out of the eddy-current regime. **Assessment 2026-08-09:**
   ≈ 8–12 gate-grain items at the TH-campaign precedent (5 gates/week
   focused) ⇒ ≈ 1.5–2 weeks once queued; a §7 chunk ID should exist by
   the next weekly review. **Assessment 2026-08-16:** the chunk-ID
   clause is satisfied and the subgoal is most of the way done — 7
   Larmor-grain items landed this week: `TH-10` ✅ 08-13 (the sphere
   target itself: 3.643% / 1.826% at 64/128 MHz, power 3.629%, plus the
   08-15 monotonicity assert), `GEO-14` ✅ 08-15, `TH-11` 🟡 steps 1–2
   (the trend target: step 2 attributes most of the +10.27% 64 MHz
   deviation to mesh, landing at +2.81% resolution-dominated), and
   `TH-11` step 3 ✅ 08-16 (the 30 MHz mid-point, +5.5912%). Remaining:
   whatever gated trend claim the three-point reading licenses — and
   step 3 showed it licenses none directly, because cells/δ (3.18 /
   1.84 / 1.26) falls monotonically with the same f the deviation rises
   with. The unblocking rung is an h-refinement ladder at *fixed* f
   (Richardson), unscoped as of 08-16 — ≈ 2–4 items ⇒ **< 1 week of
   fired slots**. Honest limit unchanged: no gated trend claim is
   scopeable *yet*; §2.1's "coil-at-Larmor is an extrapolation"
   sentence stands until one gates. **Assessment 2026-08-23 — rescoped;
   the second target is killed (epitaph below).** Of the two named
   targets, the sphere **closed** (`TH-10` ✅ 08-13, 3.643% / 1.826% /
   3.629%) and the coil-loading trend is **finished as a measured
   negative**: `TH-11` ✅ 08-18 by adjudication — step 4's fixed-f ladders
   read flat in f (brackets overlapping at ~−1% at 10 and 30 MHz), so the
   apparent trend was resolution; step 5 priced the 64 MHz third rung at
   2.81 M cells, **OOM at every legal rank count**, 0.99 M cells pegged at
   `memory.max` = 64.00 GiB; `TH-12` step 2 found the degree-2 route hits
   the same wall at 61.94 GiB. Eight Larmor-grain items landed this week
   and none can turn into a gated 64 MHz coil bracket on this box — the
   subgoal's remaining content was a fit no affordable rung can feed.
   What the phase still owes on Larmor physics is now carried by
   `PORT-11` (the loaded birdcage at 64 MHz under identity gates, subgoal
   2b) and subgoal 4 (SAR/B1+ on a solved coil field, against the
   `TH-10`-gated sphere machinery), not by a coil-loading trend. §2.2's
   extrapolation bullet stands as written — it moves only on more memory
   or an out-of-core/iterative solver path, neither of which is on the
   mission's shortest path this quarter; if Phase 6's 32-port cost rung
   (`GEO-19`) also does not fit, the solver-path question returns as a
   Phase-6 subgoal with that measurement behind it.
4. *B1+ and SAR maps on the coil+phantom fixture at 64/128 MHz.* Targets:
   SAR through the `MAT-4`-gated averaging operator (its C95.3 claim closes
   here); B1+ gated qualitatively against published birdcage homogeneity
   behaviour and, once computed, an AED benchmark case (`ANS-2`, to be
   commissioned when subgoals 2–3 close). Blocked on 2 + 3 by §6's
   scaffolding rule. *(Note 2026-08-16, weekly review: this is now the
   only subgoal with no owning §7 chunk ID — correctly, while blocked —
   but subgoals 2–3 are ≈ 1 week out, so the daily review should scope
   the first B1+ chunk when `PORT-9` gates, and `ANS-2`'s commissioning
   trigger is unchanged. `MAT-4` last moved 2026-08-07; it is the
   watch-item for the one-month stall rule at the 08-30 review.)*
   **Assessment 2026-08-23:** unchanged and correctly so — 0 items this
   week, still the only subgoal without a §7 chunk, still blocked by the
   scaffolding rule behind subgoal 2. What changed is the input: the
   fixture it will run on is the *loaded* gapped birdcage (`GEO-18`,
   phantom inside), which after `PORT-9` leg (d) is a port-driven coil
   with a solved field at 10 MHz — the first B1+ chunk (`|B₁⁺| =
   |B_x + jB_y|/2` on the phantom from that field, gated on the C4
   symmetry of the map and on `∫σ|E|²` reproducing the sweep's power
   accounting) can be scoped by the daily review the day `PORT-9` closes,
   at 10 MHz, with the 64 MHz map following `PORT-11`. `MAT-4`'s
   coil-driven SAR route goes through the same field. The one-month rule
   on `MAT-4` stands for 08-30; the fix is the B1+/SAR chunk, not an
   extension. Arithmetic: ≈ 6–8 steps at the landed grain, unmeasured
   pace for this work type ⇒ no date until the first step lands.

**Phase-5 exit assessment, 2026-08-09 (the arithmetic on record):** ports
≈ 1.7 wk (subgoal 2) + Larmor gates ≈ 1.5–2 wk (subgoal 3, partly
parallel) + maps ≈ 1 wk (subgoal 4) ⇒ **exit ≈ 2026-09-06…13 at measured
pace, reliability permitting**. That is well inside a quarter, so no rescope
is forced. The number honest people watch: if the port lineage's
discriminator round does not convert to the 3b-i/ii pair gate within its
two-slot budget, subgoal 2's 20-step estimate is wrong and the next weekly
review re-plans rather than extends.

**Phase-5 exit assessment, 2026-08-16 (the arithmetic):** subgoal 1
closed; remaining = `PORT-9` ≈ 1 wk (subgoal 2) + Larmor remainder
< 1 wk (subgoal 3, parallel) + maps ≈ 1 wk (subgoal 4) ⇒ **exit
≈ 2026-09-06…13 unchanged at measured per-slot pace — but only if slot
reliability holds.** This week lost ~30 of ~112 scheduled slots to
non-physics causes; a repeat adds a week, and that is now the modeled
risk, not the physics. The number honest people watch this week: **if
`PORT-9`'s first gated step has not landed by the 2026-08-23 weekly
review, the 8–12-step estimate is wrong and that review re-plans rather
than extends.**

**Phase-5 exit assessment, 2026-08-23 (the arithmetic):** subgoals 1 and
3 closed (3 as a measured negative); remaining = `PORT-9` leg (d) (1 slot)
+ `PORT-11` (≈ 3–4 steps, ≈ 0.5 wk at 10 port items/wk) + maps (subgoal
4, ≈ 6–8 steps, no measured pace — taken at the port grain, ≈ 0.7–1 wk)
⇒ **exit ≈ 2026-09-08…15 at the measured pace — a slip of ~2 days
against the 08-16 window**, attributable to the unnamed `GEO-18`
prerequisite and the 08-20/21 dead-review day, not to physics. Still
inside a quarter; no rescope forced. The modeled risk is unchanged in
kind and worse in evidence: this week's losses were 100% governing-half
(credit-dead reviews), and a second such day adds a week. The number
honest people watch: **if `PORT-9` is not ✅ and `PORT-11` step 1 has not
priced 64 MHz by the 2026-08-30 review, the port lineage is not "one step
from done" and that review re-plans it; and if the first B1+ chunk is not
scoped by then, subgoal 4's "blocked, correctly" reading becomes a stall.**

**Production element order, decided 2026-08-23 (the `TH-12` decision
clause).** **Degree 1 is the production order for the Phase-5/6
coil-fed solves** (`PORT-9`, `PORT-11`, the birdcage B1+/SAR maps, the
32-port cost rung). Degree 2 is **adopted for imposed-field
phantom-dominated solves only** — the `TH-10`-class sphere lineage and
any SAR-operator validation on an imposed field — where it is measured to
win outright (0.1405% vs 3.643% at 3.01× fewer cells, 2.7× memory). The
bar it fails on the coil: the degree-2 coil solve carries a complex-power
identity miss of 3–5e-9 vs 1e-9 with 99.6% spurious electric energy
(`W_e/W_m` 6.7e-6 → 229) and sits at 96.8% of `memory.max` on the
138 k-cell fixture — an order that cannot pass the family's own identity
on the production drive is not production-grade, whatever its ΔR reads.
Reversible on evidence: `TH-13` (§7) is the discriminator `TH-12` step 3
named; a CLASS verdict makes a gauged degree-2 formulation the next
chunk, a FEED verdict points at the port model, and either re-opens this
decision at the following weekly review. The 32-port cost rung (`GEO-19`)
is priced at degree 1 accordingly.

**OPERATOR DIRECTIVE 2026-08-25 (interactive session) — two fixtures, and
the fixture-scale finding behind it. FOR THE 2026-08-30 WEEKLY REVIEW: this
is the disposition of the `N ≤ 25` question the 08-23 review deferred to you,
and it must be answered in that review's §10 pass. The weekly review owns the
final scoping; the operator has stated the intent and the reasoning below is
the interactive session's, offered as a recommendation, not as a decision.**

> **The finding.** `birdcage_port_domain`'s default `ring_radius = 0.07 m`
> is a **14 cm-diameter, 14 cm-long coil around a 6 cm phantom**. That is a
> bench-scale fixture, not a human coil — the operator's actual target is
> "rather large, it had to fit a human, like 30 cm diameter and length."
> **No entry in this plan has ever justified 0.07 m**; it is an unexamined
> inheritance from an early coarse fixture, and every downstream constraint
> derived from it inherits that. In particular the `N ≤ 25` ceiling is just
> arithmetic on the wrong radius: `2π(0.07)/17.5 mm = 25.1`. At
> `ring_radius = 0.15` the same 17.5 mm clearance floor admits **53 legs**
> (32 legs give 29.5 mm spacing), so the 32-port directive has no geometry
> problem at human scale and needs neither a bigger clearance rule nor
> narrower boxes.
>
> **Why this is a physics finding and not a bookkeeping one.** At 64 MHz the
> wavelength in tissue (εᵣ ≈ 80) is ≈ 0.52 m; at 128 MHz ≈ 0.26 m. A 30 cm
> coil is a substantial fraction of a wavelength — that is *why* this project
> needs a full-wave solve rather than a quasi-static one (§1). A 14 cm coil
> around a 6 cm phantom is electrically far smaller and will **systematically
> understate exactly the effects Phase 5/6 exist to capture**: B1+
> inhomogeneity, dielectric/wavelength behaviour, and the SAR distribution.
> Those come out *qualitatively* wrong, not merely imprecise. For the 10 MHz
> gating work done so far this was harmless — at 30 m wavelength nothing is
> scale-sensitive — which is why it has gone unnoticed for the whole port
> lineage.
>
> **The directive.** Maintain **two** fixtures, not one:
> * **(F-small) the gate fixture** — today's `ring_radius = 0.07 m`
>   parameters, unchanged. It keeps every existing record valid (116 085
>   cells, `PORT-9`'s S-matrix, the `GEO-18`/`19`/`20` identities,
>   `EX-28`/`EX-31`), stays cheap enough to run in an ordinary slot, and
>   remains the home of the CAD-identity and reciprocity/passivity gates.
>   **Its records must not move for this.**
> * **(F-human) the production fixture** — a **human-scale high-pass
>   birdcage**: `ring_radius ≈ 0.15 m`, `coil_length ≈ 0.30 m`, phantom
>   scaled to match (a 6 cm phantom in a 30 cm coil is not a load), the
>   **high-pass ring-gap topology** `GEO-20` already builds, at the
>   directive's 32 ports. This is the fixture the Phase 5/6 *deliverables*
>   run on — B1+ maps, coil-driven SAR, mode spectrum, tuning.
>
> Keeping them separate is the point: it buys the right physics for the
> deliverables **without** a mass re-record of the validation lineage, and
> F-small stays useful precisely *because* it is cheap.
>
> **What the weekly review must decide (not pre-empted here).**
> 1. **Cost, first and blocking.** Volume goes as r³: 0.07 → 0.15 m is ≈ 10×
>    at fixed resolution. `GEO-19` step C measured 16 legs at **307 296
>    cells / 74.18 s** on F-small; F-human at 32 ports plausibly lands at
>    **3–4 M cells**, and `TH-11` step 5 measured **2.81 M as an OOM** — at
>    the *old* 64 GiB ceiling. **The ceiling is now 128 GiB** (§5.1,
>    operator directive 2026-08-24), so this is the first real test of that
>    raise and is exactly the re-pricing the `TH-11`/`TH-12`/`OPS-17`
>    memory-premise caveats were left open for. **A cost probe comes before
>    any dated commitment** — §5.1's "a tier is a measurement, not an
>    intention", and the §10 epitaph's own lesson (a target needs its finest
>    rung priced before it is named).
> 2. Whether F-human is a **new parameter set** on `birdcage_port_domain` or
>    a **separate constructor**, and which gates transfer to it. The
>    CAD-identity families should transfer unchanged — they are scale-free.
> 3. Whether `GEO-19` step C's parked C16 terminal-equality band question
>    should be settled on F-small first (it is a C4 band applied to C16,
>    independent of scale) so that F-human does not inherit an open ruling.
> 4. Sequencing against Phase 5 subgoal 4: the first B1+ chunk was to be
>    scoped "the day `PORT-9` closes" (2026-08-25) on the *loaded F-small*
>    birdcage at 10 MHz. That should still happen — it is the cheap way to
>    gate the B1+ machinery — with the human-scale map following on F-human.
>    **Do not block subgoal 4 on F-human.**
>
> **What this directive does not do:** it does not re-record anything, does
> not change a default, does not commission a chunk, and does not move the
> 32-port target. `GEO-19`/`GEO-20` continue as scoped on F-small.

**Phase 6 — tuning.** Mode spectrum of the birdcage (the `TH-9` eigensolver
machinery on the birdcage mesh), lumped capacitors at the gap/port level,
and a circuit co-simulation loop: S-parameters from the EM solve, tuning
and matching in a circuit layer — the HFSS + Circuit split. Validation
targets, named now: birdcage mode frequencies against the lumped-element
ladder-network closed form; tuned S11/capacitor values against an AED
HFSS + Circuit benchmark case. Hard parts unchanged: near-resonance solves
are §2.1's ill-conditioning trap *by construction*, and the phase is
`PORT-1`-blocked until gap-voltage ports gate. **Assessment 2026-08-09:**
earliest meaningful start ≈ end of August (when subgoal-2 ports land); no
completion date — no circuit co-simulation work of any kind exists in the
repo, so there is no measured pace to extrapolate from, and inventing one
is what this section exists to prevent. First date next review after its
first steps land. **Assessment 2026-08-16:** unchanged — ports are ≈ 1
week out, so "earliest meaningful start ≈ end of August" still holds and
still awaits `PORT-9`; no circuit co-simulation work exists yet, so
still no completion date. **Assessment 2026-08-23:** the physics start
still waits on `PORT-9`/`PORT-11` (the scaffolding rule — a mode
spectrum on a port model that has not gated at 64 MHz would be the ⚠️
backlog again), so "earliest meaningful physics start ≈ 2026-09-01"
follows from subgoal 2b's arithmetic above. What *can* start now, and is
scoped this review, is the directive's mesh half, because its gates are
CAD identities with no physics dependency: **`GEO-19`** (item (a), 16
legs, the first measured cost rung above 4 legs) and **`GEO-20`** (item
(b), the high-pass ring-gap port layout, 4 legs first). Items (c) (C4 →
C_N gate generalization) and (d) (the AED HFSS + Circuit case at 16
legs) stay unscoped until `GEO-19` reports whether 16 legs fit the box
at all — a cost rung, not a hope, is what dates this phase. Still no
completion date, for the same reason as the last two weeks.

**Operator directive 2026-08-17 (binding on this phase's scoping):** the
production target for real MRI-safety work at 1.5 T is a **high-pass
birdcage** (capacitors in the end-ring segments, not the rungs) with
**32 ports** — i.e. 16 rungs × 2 end rings, one lumped port per ring
gap. Everything gated so far is the 4-leg fixture with one port box per
leg-pair; a high-pass topology needs ring-gap port surfaces the current
`birdcage_port_domain` layout does not emit, and nothing above
`leg_count = 4` has ever been meshed, identity-gated, or costed. When
this phase is broken down, the breakdown must therefore include, before
any tuning claim: (a) parametric leg count re-gated at 16 (the `GEO-9`
identity family + graded sizing at the larger conductor count, with a
measured cost rung — cell count scales with legs); (b) the high-pass
ring-gap port layout as a mesh chunk (the `GEO-16` pattern, on the end
rings); (c) `PORT-9` step 3's circulant-symmetry gate generalized C4 →
C_N (the 32-port S-matrix is block-circulant in the 16 ring-gap pairs);
(d) the AED HFSS + Circuit benchmark commissioned at the production
rung count, not at 4. The 4-leg fixture stays the cheap validation
vehicle — first gates land there — but Phase 6 does not close on it.
Circuit-layer detail is deliberately left to the reviews when the phase
opens (operator: the area is well-covered by literature; ladder-network
closed forms are the entry point).

**The element-order lever (operator directive 2026-08-18, cross-phase).**
Second-order (degree-2 N1curl) elements are to be *evaluated by
measurement* (`TH-12`) and, if they win on accuracy-per-DOF, adopted as
the production order for the Phase-5/6 solves — every open TH/MAT
accuracy question is a cells-per-δ question, `TH-11` step 5b has measured
that the degree-1 route to the 64 MHz bracket does not fit the box, and
the production 32-port case only compounds that. Honest scope of the
lever: it applies to the time-harmonic E-formulation lineage (Phases 2–6,
including SAR fields and port integrals); it does **not** apply to the
closed Phase-1 magnetostatics (degree-2 A is on record diverging under
the penalty gauge — a formulation property, and Phase 1 is not worth
re-gating). Curved second-order *geometry* is the separable second half
of the same idea (it is the answer class for `GEO-15`'s 3.3% faceting
residual) and awaits its own `GEO` chunk. No dated estimate until
`TH-12` step 1 lands a number. *(2026-08-23: steps 1–3 landed; the
decision is recorded above — degree 1 in production for coil-fed solves,
degree 2 for imposed-field phantom solves, `TH-13` the reopening
condition.)*

**Phase 7 — implants.** Parametric implant geometry first (wires, rods,
plates in the phantom; CAD import later), mesh grading around thin
conductors (the `MAG-13` 1/r lesson, made worse by skin depth), local SAR
and near-implant hot spots. Validation targets: published measured implant-
heating data, and AED comparisons — this is where they matter most. No
dated estimate: no measured pace for this work type exists.

**Phase 8 — thermal.** Pennes bioheat with SAR as the source term;
phantom-regime validation first (gel: no perfusion, so the equation reduces
to heat conduction + source, which analytic solutions cover). Mathematically
the easiest phase; the risk is validation data and the EM–thermal
interface, not the solver. No dated estimate, same rule.

**Epitaphs.**
- *2026-08-23 — Phase 5 subgoal 3, second target: "the coil-loading trend
  vs frequency crossing out of the eddy-current regime", killed.* Eight
  gated items and two weeks showed the three-point trend was the
  resolution term (`TH-11` step 4, flat in f), and that the 64 MHz h → 0
  bracket that would have licensed a trend claim does not fit a 64 GiB
  box at degree 1 (2.81 M cells OOM, 0.99 M pegged) or degree 2 (61.94
  GiB on the *coarse* rung). The lesson: a trend target needs its finest
  rung priced before it is named.
  **Caveat added 2026-08-24: the box is no longer 64 GiB.** The operator
  raised the container ceiling to **128 GiB**, so the affordability half
  of this epitaph is now unmeasured rather than false — 2.81 M cells at
  degree 1 and the degree-2 coarse rung both sat *inside* 2× their old
  wall. The *physics* half is untouched and is the load-bearing one:
  `TH-11` step 4 showed the three-point trend was the resolution term,
  flat in f, and more RAM does not make a resolution artefact a trend.
  Reviving this target therefore needs a new argument, not just a bigger
  rung — the weekly review owns that call. The Larmor coil question lives on as
  `PORT-11` (identity gates on the loaded birdcage) and subgoal 4, not as
  a ΔR(f) fit.

**Examples and benchmarks.** The §5.4 ramp accounting lives in the §7 `EX`
family (backfill `EX-4`…`EX-12` opened 2026-08-09). Ramp check 2026-08-16
(weekly review): 20 runnable examples, every phase at or above quota —
Phase 1 five, Phase 2 six, Phases 3 and 4 exactly at quota (2/2 each) with
**no headroom**: the next `MAT` or `PORT` gate closure immediately owes an
example, and `EX-21` (birdcage mesh) is the queued answer for `GEO`.
Both AED benchmarks' runnable halves are closed (`ANS-1` 08-09, `ANS-3`
08-16) and wait on the operator's Ansys halves — no `COMPARISON.md` has
AED numbers yet, so nothing to adjudicate this week; `ANS-2` (B1+/SAR)
stays reserved for subgoal 4. One health defect found: five examples'
gated `paraview_output/` artifacts are **absent on disk** (not merely
stale — gitignored and deleted), `EX-22` opened to restore them.
**Ramp check 2026-08-23 (weekly review): 27 runnable examples (+7), every
phase at or above its ramp, no shortfall.** Per phase, gating chunks
✅ / quota / examples: Phase 1 **6 / 5 / 5** (complete, flat five binds,
exactly met); Phase 2 **5 / 5 / 8** (+3 headroom — `EX-25` element order,
`EX-26` power balance landed); Phase 3 **2 / 2 / 2** (no headroom for the
second week — `MAT-4`'s coil-driven closure owes an example the same day);
Phase 4 **2 / 2 / 3** (+1 — `EX-24` lumped-sheet port); Phase 5 0 / 0 / 0
(`mri:1` is the labelled ungated example and does not count); mesh group
6 (`EX-21`/`23`/`27`/`28` this week — four of the seven new examples went
to the ramp-exempt group, so Phases 3 and 5 gained nothing). Guides
present for 27/27; no example is listed broken. **Two health findings,
both opened as §7 chunks:** (1) the doc-reference checker freshness-gates
only the 5 examples that write to the repo-root `paraview_output/`; the
other 22 get an existence-only pass through a false "committed in-tree"
exemption, so every `stale=24, none of them mine` line since `OPS-19`
was a census of 5 — `EX-29` fixes the checker (known-issues entry of this
date); (2) the artifacts it could not see are 10–17 days old for 13
examples, all predating `OPS-17`'s test replacement — `EX-30` refreshes
them in two legs. `EX-22`'s 08-16 premise correction is corroborated
(`dead=0` throughout; it was a freshness restore). **Benchmarks:** no
`COMPARISON.md` has AED numbers (both cases' AED columns verbatim blank),
so nothing to adjudicate; **no new case commissioned** — the gated-physics
milestone since `ANS-3` is degree-2 on the imposed-field sphere, which
`ANS-1`/`ANS-3` do not cover but which is not the mission's next
question, and two cases already wait on the operator's single AED queue.
The next commission is the birdcage 4-port Z at 10 MHz (`ANS-4`) the week
`PORT-9` leg (d) gates, and its 64 MHz sibling when `PORT-11` does;
`ANS-2` stays reserved for subgoal 4.

**Ratification, 2026-08-16.** The `PORT-9`/`PORT-10` scoping, `ANS-3`
commissioning, plan prune, and attempts archival annotated "*weekly
planning review 2026-08-16*" were executed by the operator's interactive
session (the scheduled 01:30 slot died on the usage limit; `d21d228`
landed the tail). This review audited and ratifies them as weekly-scope
work — the annotations stand.

---

## 11. Key technical reference

**Function spaces** — H(curl)/Nédélec for `E` and `A`; H(div) for `B`; L2 for
scalar potential in A-V formulations.

**Boundary conditions** — PEC `n×E = 0`; PMC `n·B = 0`; ABC for radiation; PML via
complex coordinate stretching; waveguide ports for S-parameter extraction.

**Materials** — `ε = ε₀(ε' − jε'')`, `μ = μ₀(μ' − jμ'')`; anisotropic tensors;
frequency-dependent dispersion. Gelled saline at 128 MHz (3T): `σ ≈ 0.6–0.9 S/m`,
`εᵣ ≈ 78–80`; phantom diameter 16–20 cm (head), 30–40 cm (body); ~1% agarose.

**Linear solvers** — MUMPS direct for small/medium; GMRES + ILU iterative; complex
systems required for time-harmonic (`TH-1`).

**Post-processing** — `SAR = σ|E|²/(2ρ)` [W/kg]; `J = σE`; Poynting `S = ½Re(E×H*)`.

### Resources
- [FEniCSX Tutorial](https://jorgensd.github.io/dolfinx-tutorial/) ·
  [API docs](https://docs.fenicsproject.org/dolfinx/v0.7.0/)
- Similar work: [Elmer FEM](https://www.elmerfem.org/) (EM module),
  [OpenEMS](https://openems.de/) (FDTD), [scikit-rf](https://scikit-rf.readthedocs.io/)
