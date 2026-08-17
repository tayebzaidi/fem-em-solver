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
  straight wire 12.75% at the landed gate (3.74% at the finest measured
  rung), rate ≥ 1.1; PEC cavity modes **0.0436%**.
- **Time-harmonic complex solve** (`TH-1`, complex build mandatory — real
  mode raises): MMS rate 0.9929; lossy plane wave α **0.019%** / β 0.059%
  (`TH-6`); evanescent waveguide γ **0.006%** (`TH-7`); quasi-static
  sphere 2.443% (`TH-8`); resonance guard calibrated (`TH-1` step 5).
- **The Larmor regime, on an imposed field** (`TH-10`): interior field vs
  the Mie series **3.643% / 1.826%** at 64 / 128 MHz, and the SAR-relevant
  ½∫σ|E|² to **3.629%** — quasi-statics is the *wrong answer* there
  (under-predicts absorbed power 2.4× at 1.5 T).
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
- `post/evaluation.py` point location (all point evaluation goes through
  it), gmsh generation + tag QA, the runner, and the logging harness.

### 2.2 Not validated — do not trust, do not extend

- **No coil or birdcage has ports.** Any S-parameter figure quoted for a
  coil is unsupported. The birdcage-port direction is scoped —
  `PORT-9` (lumped/circuit-element port BC, Jin ch. 11) — and as of
  2026-08-16 both named prerequisites have **executed and closed**:
  `PORT-10` (the two systematics compose additively, cross-term
  −0.0604 pp) and `GEO-15` (graded conductor sizing reaches 0.967 of CAD
  mass; `PORT-9` budgets from 98 k cells). `PORT-9`'s step-1 **formulation**
  is written and identity-gated on a parked branch
  (`attempt/PORT-9-20260816T170800Z`, Jin 3e §1.5.4/§6.5 resistive sheet),
  and awaiting instantiation: its mesh prerequisite `GEO-16` closed
  2026-08-17 (the fixture now emits the longitudinal sheet on an opt-in
  kwarg, area = CAD to roundoff, `w/h = 1.504225878` squares measured), so
  the branch may now be merged and wired — but no lumped-port `Z` has ever
  been solved. This bullet stands until step 2's cross-route band
  gates. B1+ remains §10 subgoal 4, blocked behind it.
- **Coil loading at the Larmor frequencies is an extrapolation** until
  `TH-11` lands a gated trend (its resolution rung attributed most of the
  observed 64 MHz deviation to mesh, not physics; the three-point set
  1.58 / 5.59 / 10.27% at 10 / 30 / 64 MHz is monotone, but so is the
  resolution confound — cells/δ 3.18 / 1.84 / 1.26).
- **SAR on a solved coil field** — the IEEE C95.3 claim — is open;
  `MAT-4` stays 🟡 until it exists on the coil+phantom fixture.
- **`⚠️` chunks** (`TH-2`/`TH-3`, `PORT-4`/`PORT-5`/`PORT-8`, `WF-2`/
  `WF-3`, `MAT-1`) carry code whose tests assert too little to protect
  them; revalidate before building on them. `OPS-17` (§7) removes or
  replaces the finiteness-only tests themselves.

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
cannot be trusted until revalidated against the real solve (`OPS-17`
retires the glyph as its tests are replaced). Do not "fix" a `⚠️` chunk by
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
| Image / base | `fem-em-solver:latest` (6.26 GB) on `dolfinx/dolfinx:v0.7.2` |
| dolfinx / Python | 0.7.2 / 3.10.12 |
| Default PETSc scalar | `numpy.float64` — **real mode** |
| Complex build | `/usr/local/dolfinx-complex` |
| Memory cap | 64 GB (raised from 16 GB by `MAT-6` step 7, operator-approved 2026-08-10) |

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
| 2 | Time-harmonic Maxwell, complex materials, ABC/PML | `TH-1`…`TH-9` | In progress — every analytic gate closed (`TH-1`/`TH-6`/`TH-7`/`TH-8`/`TH-9` ✅); `TH-2`/`TH-3` API hardening ⚠️ |
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-6` | `MAT-2` ✅; `MAT-6` ✅ (ΔR to 1.58% pinned / 1.5834% on the production projected drive, step 3; eddy-current regime); SAR gated on an **imposed** uniform field only (`MAT-4` steps 1+3: lossy-sphere closed form 3.5%, mass-averaging exact at 1 g/10 g) — coil-driven SAR and the C95.3 claim still open |
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-10` | `PORT-1` ✅ 2026-08-15 (field-derived S through the package, two-torus fixture only, two named systematics); birdcage-port direction scoped 2026-08-16: `PORT-9` lumped-element port BC, prerequisites `PORT-10` + `GEO-15`; `PORT-4`…`PORT-8` open |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 for excitation; both meshes (coil+phantom, birdcage) generate and are identity-gated in CI (`GEO-9`, 2026-08-03) |
| 6 | Birdcage tuning at 64/128 MHz: mode spectrum, lumped capacitors, circuit co-simulation (the HFSS + Circuit split) | subgoals owned by the weekly review (§10) | Not started |
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
the two-torus fixture grows until a review scopes birdcage ports.

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
| `OPS-16` | Retry-on-529 in the three automation launchers (two review slots lost 2026-08-13; rubric in the §9 item) | 🚫 | smoke |
| `OPS-17` | Delete or replace the finiteness-only test suites (operator directive 2026-08-16) | ⬜ | standard |
| `OPS-18` | DolfinX version upgrade, recurring (0.7.2 → newest qualifying; operator directive 2026-08-16) | ⬜ | heavy |
| `OPS-19` | Doc-reference checker: staleness must not own the exit code (2 runs flagged the masked signal 2026-08-16) | ✅ (2026-08-16: exit 0/1/2 split + `--stale-severity {fail,report}` default `report`; on `main` the checker now reads `dead=0 guide=0 stale=24 exit=2` where it read exit 1, guide pass green 21/21; 8 tests, 1.91 s, smoke) | smoke |

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

**`OPS-19` — doc-reference checker: staleness must not own the exit code**
✅ *(commissioned 2026-08-16, 10:30 review; step 1 closed 2026-08-16, 16:30
implementer slot.)*
> **Closure (step 1).** `scripts/testing/check_example_doc_references.py` now
> scores staleness in its own bucket: module-level `EXIT_OK`/`EXIT_HARD`/
> `EXIT_STALE_ONLY` = 0/1/2, plus `--stale-severity {fail,report}` defaulting
> to `report`. Hard violations (dead reference, missing guide, missing
> heading) dominate; staleness alone exits 2; `--stale-severity fail`
> reproduces the pre-split reading bit for bit. A final
> `RESULT: dead=… guide=… stale=… stale_severity=… exit=…` line makes the
> split machine-readable without parsing the body. `--max-age-s` (`OPS-15`'s
> 48 h) did not move, and no example was re-run or refreshed.
>
> **Anchor (countable), `tests/unit/test_doc_reference_exit_codes.py`, 8
> tests, 1.91 s, smoke, `-n 1`,
> `20260816T213312Z_OPS-19-step1-rerun.log`:** on the tree as committed the
> checker reports `dead=0 guide=0 stale=24 stale_severity=report exit=2` —
> the 24 pre-existing stale `paraview_output/` artifacts, and nothing else,
> with the guide pass green at **21/21 examples, 0 pending** (the §9 item's
> "20/20" predates `EX-21`, which added the 21st). Each fixture test asserts
> the exit code twice: against the literal expected code and against the
> contract restated as arithmetic over the printed counts.
> **Negative control (the defect class must survive the split):** a temp-dir
> guide naming an artifact no run ever wrote still exits 1
> (`dead=1 stale=0`), as does one naming a non-existent `.py` — the artifact
> case travels the same code path staleness was carved out of, so a split
> that mis-scored "missing" as "stale" would fail here. Boundary control on
> the untouched default: the same fixture aged 47 h scores `stale=0 exit=0`
> and aged 49 h scores `stale=1 exit=2`.
>
> **Call sites — one, not two.** The §9 item and this entry both said
> `run_examples.sh`'s docrefs invocation must be updated to agree on the new
> codes. It has none: `grep -rn check_example_doc_references scripts/` hits
> only the checker's own usage docstring. The checker is invoked ad hoc in
> harness commands (`EX-18`, `EX-20`, `ANS-3`, `EX-21` logs), so there is no
> second caller to desynchronise, and the trap the item warned about — a
> green example run starting to fail on code 2 — cannot occur. If a docrefs
> call is ever added to the runner, `0` and `2` are both pass.
>
> **One bug found and fixed in passing** (pre-existing, latent until the
> fixtures existed): `collect_references` called `doc.relative_to(REPO_ROOT)`
> unconditionally, so any `--docs-root` outside the repo raised `ValueError`
> instead of reporting. Now `display_path()`, repo-relative when it can be.
> The first harness run (`20260816T213248Z_OPS-19-step1.log`, 7 failed / 1
> passed, 2 s) is that bug: every temp-dir fixture died before printing.
>
> **Original commissioning note (2026-08-16, 10:30 review).** Two independent
> implementer runs flagged the same defect this interval: 24 pre-existing
> stale `paraview_output/` artifacts (magnetostatics/MRI examples last
> regenerated 112–141 h ago) drive `check_example_doc_references.py` to exit 1
> on every invocation, so a chunk touching examples cannot tell its own
> breakage from the backlog's without reading the log body — `EX-20` and
> `ANS-3` both had to journal a red companion log as "known, benign". The fix
> is signal separation, not artifact refresh: a refresh run buys 48 h of green
> and then the treadmill resumes.
> * **Step 1 (gate) — split the exit code (smoke, no solves).** Give
>   staleness its own exit code (e.g. 0 = clean, 1 = dead reference or
>   missing guide/section, 2 = staleness-only) or a `--stale-severity
>   {fail,report}` flag defaulting to `report`, in
>   `scripts/testing/check_example_doc_references.py`; update
>   `run_examples.sh`'s docrefs invocation and the known-issues
>   "by design" entry (§ line ~502) with the new contract. **Anchor
>   (countable, asserted in a pytest wrapper or the checker's own
>   self-test):** on the current tree the checker reports exactly the
>   staleness violations and exits with the staleness-only code, with the
>   guide pass still green (20/20); **negative control:** a temp-dir copy
>   with one deliberately dead artifact reference in a guide must still
>   exit 1 — the defect class the checker exists for must survive the
>   split. **Tier/cost:** smoke, `-n 1`, seconds (the checker is pure
>   filesystem; `EX-18`'s docrefs runs are ~1 s). **Traps:** the checker
>   is called from `run_examples.sh` *and* standalone in harness
>   commands — both call sites must agree on the new codes or a green
>   example run will start failing on code 2; pytest captures prints
>   without `-s`. **Scope:** exit-code semantics only — no example is
>   re-run, no artifact refreshed, `--max-age-s` (OPS-15's 48 h) does not
>   move. **Negative result:** if the checker's structure resists the
>   split inside a slot, report the obstacle in this entry and stop.

**`OPS-16` — retry-on-529 in the automation launchers** 🚫
*(commissioned 2026-08-13, 10:30 review; blocked 2026-08-14, 21:00 run.)*
> **Blocked by the permission layer, not by the work.** Every file this chunk
> must touch lives under `scripts/automation/`, and `.claude/settings.json`
> lists `Edit(scripts/automation/**)` in the **`ask`** section — which in a
> headless `claude -p` run with `--permission-mode acceptEdits` is a denial,
> because there is nobody to answer the prompt. Both a `Write` of the new
> `lib/claude_retry.sh` and the single one-line `CLAUDE_BIN="${CLAUDE_BIN:-…}"`
> edit to `implementer-run.sh` were denied, so no scheduled session can execute
> this chunk in any scoping.
>
> The §9 item's trap paragraph is wrong about the rule's scope — it says only
> `scripts/automation/hooks/` is write-protected, but the glob covers the
> launchers too. **Unblocking is a human decision**, and a defensible one to
> refuse: a session that can edit its own launcher can change its own model,
> effort, timeout and disallowed tools. Either (a) the operator moves *only*
> the three launcher files to `allow`, keeping the `**` rule on `ask` so
> `hooks/` and new files stay gated, or (b) the operator applies the change by
> hand in an interactive session. The full design — shared helper, the retry
> ERE validated against both real failure logs, the deadline-based budget
> conservation `elapsed₁ + backoff + budget₂ = total` that leaves healthy runs
> bit-unchanged, the per-launcher floor, and the six-case stub-`CLAUDE_BIN`
> rehearsal with its ±2 s budget identity — is recorded in the
> 2026-08-14T02:03Z `docs/testing/attempts.md` entry, ready to apply.
>
> **Second trap, found in passing and independent of the first:**
> `.gitignore:13` is a bare `lib/` (Python-packaging leftover, no leading
> slash), so `scripts/automation/lib/` is **ignored at any depth** — the
> shared helper would have been committed-by-omission and every scheduled
> session would then die at `source` after the next pull. Name the directory
> something else or add a `!scripts/automation/lib/` negation. This applies to
> any future `*/lib/` in the repo, not just `OPS-16`.

**`OPS-17` — delete or replace the finiteness-only test suites** ⬜
*(commissioned 2026-08-16, operator session. The directive: tests whose
only assertions are finiteness-class are worse than no tests — they
green-lit both §2-era defects for months (§4's finiteness-only rule exists
because of them). Get rid of them; where a cheap quantitative anchor
exists, replace instead. Two steps, one implementer run each.)*
> * **Step 1 — inventory and disposition (smoke, no solves).** Sweep
>   `tests/` for test functions whose assertions are all finiteness-class
>   (`np.isfinite`, `> 0`, shape, `does not raise`) — grep, then confirm
>   by reading. Commit a table in this entry's annotation: file :: test ::
>   what it exercises :: disposition (**delete** / **replace**, naming the
>   anchor / **keep**, only where the test guards structure a quantitative
>   gate relies on — e.g. a negative control's fixture). **Done-when
>   (§4):** the table is committed with every row dispositioned and counts
>   stated; the sweep command and its output are in the harness log.
> * **Step 2 — execute the dispositions.** Delete the delete rows
>   outright; land the named replacements; run the full remaining suite
>   through the harness at `-n 2`, real and complex legs. **Done-when
>   (§4):** both harness logs green (pre-existing known-issues failures
>   excepted, cited); zero references to deleted tests remain in `docs/`
>   or §7; the `⚠️` glyph is retired from §3 and the family tables — a
>   chunk whose only green was finiteness falls back to 🧪 or ⬜, which is
>   the honest reading. **Traps:** never delete a test that carries the
>   negative control or fixture of a gated test (grep for imports first);
>   a deletion that leaves a CI job empty is a finding, not a success;
>   known-issues' pre-existing failures are not this chunk's to fix.
>   **Negative result:** report, leave the table committed, stop.

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
| `MAG-13` | Analytic-Dirichlet outer boundary for wire/loop | ✅ | heavy | wire 12.75%, loop 7.07%, rate 1.10; 167 s + 196 s |
| `MAG-14` | Helmholtz magnitude comparison in the test suite | ✅ | smoke | 0.728% vs closed form (1.731% before `GEO-8`); 11 s, in CI |
| `MAG-15` | Lagrange-multiplier Coulomb gauge (cross-check) | ✅ | smoke | 7 passed, 13 s |
| `MAG-16` | Complex-build-safe magnetostatic energy | ✅ 2026-08-05 | smoke | 10 passed complex `-n 2` in 4.9 s; cross-build pin 2.9e-07, `Im W` exactly 0; retires known-issues 8 |

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
`two_torus_domain`** ✅ *(closed 2026-08-17, `tests/mesh/test_two_torus_port_sheet.py`,
`20260817T003627Z_GEO-16-regression.log`, 47.3 s at `-n 2`, 5 passed —
commissioned 2026-08-16, 18:00 review — the mesh
prerequisite the `PORT-9` step-1 attempt named (attempts.md
2026-08-16T17:08Z, option (a) chosen: split the mesh chunk, keep the parked
formulation branch intact). A lumped-port sheet spans terminal to terminal
with the port current flowing **in** its plane; the fixture's only tagged
surfaces (facet tags 201/202) are gap↔conductor cross-sections **normal**
to the current — the wrong constitutive law. This chunk puts the right
surface in the mesh; `PORT-9` step 1 then re-runs unchanged off the parked
branch.)* **Do:** behind a new opt-in kwarg (e.g.
`emit_port_sheet=False` default — the gated `PORT-1`/`PORT-10` records
were measured on the unfragmented mesh and must stay reproducible), have
`two_torus_domain` fragment each gap box with its longitudinal mid-plane
so the tet mesh conforms to it, and rebuild the sheet's **facet tag from
cell tags on the dolfinx side** — do *not* create a dim-2 gmsh physical
group on an interior surface (known-issues 9: that hangs `model_to_mesh`
at `-n 2`; `io/mesh.py::_interface_facet_tags` is the in-repo pattern).
Print (never gate) the sheet's measured extents — area, length along the
current direction *h*, transverse width *w* — because the gap box crosses
a round arc, so the "number of squares" `R = Z_p·w/h` needs is a measured
quantity on this fixture, not the box's nominal dimensions (step-2 premise
from the 17:08Z entry). **Anchor:** MPI-reduced summed area of the
reconstructed facet set equals the gmsh/occ mass-property area of the
mid-plane surface to < 1e-9 relative (the `GEO-15` CAD-denominator
pattern), on both gap boxes; existing two-torus mesh identities re-asserted
unmoved. **Negative control:** (i) kwarg off — cell count and tag sets
bit-match the current record (import the recorded constants from the
`PORT-1`/3b-xvi tests, `ANS-1` rule: never restate); (ii) kwarg on — the
facet set is asserted non-empty *before* the area identity, so a
reconstruction that silently matches zero facets fails at 100% separation
rather than passing vacuously. **Tier/cost:** standard, `-n 2`, mesh-only
— two-torus meshes in ~36 s (`ANS-3` measured); ~120 s with both rungs and
checks, container `timeout -k 30 500`. **Traps:** `occ.fragment` renumbers
volumes — re-derive the cell-tag mapping after the fragment, never assume
it (the `GEO-9` step-2b lesson); facet sets and `cell_tags.values` are
rank-local — reduce before asserting; `-n 2` minimum (finalize/bcast
degenerates at `-n 1`). **Scope:** mesh-only, no solve, no port claim —
whether the gated gap-route numbers move on the fragmented mesh is
`PORT-9` step 1's measurement, not this chunk's. **Negative result:** a
mid-plane the fragment will not conform to, or an area identity that
misses, is a finding about the gap-box CAD — record the measured area and
the residual in this entry, known-issues if it blocks, stop.
>
> **Result ✅ 2026-08-17.** `emit_port_sheet=False` (default) landed on
> `two_torus_domain`; on it each gap box is fragmented by its own mid-plane
> `z = ±separation/2` (an `occ.addRectangle` at exactly the box cross-section,
> passed as a dim-2 *tool* to the existing `occ.fragment`), giving cell tags
> `101`/`111` and `102`/`112` for the lower/upper halves — told apart by
> centroid z, never by fragment's renumbered tags (`GEO-9` step-2b lesson).
> The sheet's facet tags `211`/`212` are rebuilt from the distributed cell
> tags via `_interface_facet_tags` (no dim-2 gmsh group, known-issues 9),
> which now accepts a *sequence* of cell-tag pairs per facet tag because the
> mid-plane also cuts the arc-end discs: `201` is `(101,1) ∪ (111,1)`.
> **Anchor met:** the MPI-reduced `dS` area of each sheet is
> **9.573030358733e-05 m²** against the CAD mid-plane
> **9.573030358733e-05 m²** — `meshed/CAD = 1.000000000000`, residual below
> the 1e-9 band and at roundoff (a plane meshed by linear tets is exact, so
> unlike the discs' 2.55% chordal deficit there is nothing to inscribe);
> 84 owned facets per sheet, asserted non-empty *before* the identity;
> out-of-plane spread 3.5e-18 m; the two sheets agree to < 1e-12.
> **Measured extents** (printed, never gated, and what `PORT-9` step 1 must
> take instead of nominal dimensions): `w = 1.200000000e-02 m` transverse,
> `h = 7.977525299e-03 m` along the current, `w/h = 1.504225878` squares,
> `area/(w·h) = 1.000000000` (the sheet fills its bounding rectangle — the arc
> is buried inside the box, so the mid-plane itself is a clean rectangle; the
> CAD bbox reads `w/h = 1.504206917`, differing in the 5th digit only through
> gmsh's 1e-7 bbox inflation, `GEO-10`). **Negative controls both held:**
> kwarg off meshes 79 534 cells with tag sets `{1,2,3,101,102}` / `{1,201,202}`
> and no `21x` group, and the 3b-iv gate re-run on the same commit reproduces
> `meshed/analytic = 0.974490841` for both ports — bit-identical to the value
> recorded 2026-08-05, so the shared code path did not move. Port areas on the
> *fragmented* mesh read 1.563786482e-04 m² per port, the same 0.9745 of the
> analytic cut pair. Cost: 47.3 s at `-n 2`, well inside the ~120 s estimate.
> Caveat for `PORT-9` step 1: a caller selecting the gap volume by tag must
> take **both** halves of each box when the kwarg is on.

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
| `TH-10` | **Validation: lossy dielectric sphere in a full-wave field at 64/128 MHz (the first Larmor-regime gate)** | ✅ | standard |
| `TH-11` | **Coil-loading trend across the eddy→displacement transition (`MAT-6`'s ΔR machinery at rising f)** | 🟡 *(step 1 ✅ 2026-08-13 — 64 MHz feasible at the 10 MHz price, identities to 1e-14, quasi-static ΔR deviation 1.5834% → **10.2698%**, unattributed between physics and 1.26 cells/δ; step 2 ✅ 2026-08-15 — the resolution rung attributes most of it to mesh: **+2.8063%** at 2.52 cells/δ, a −7.4635 pp move, the pre-registered RESOLUTION-DOMINATED band, so no gated trend claim is scopeable yet; step 3 ✅ 2026-08-16 — the 30 MHz mid-point reads **+5.5912%**, giving 1.5834 / 5.5912 / 10.2698% across 10 / 30 / 64 MHz, but cells/δ falls 3.18 / 1.84 / 1.26 in lockstep, so the confound is monotone too and the trend stays a set of points; step 4 scoped by the 18:00 review — fixed-f Richardson ladder at 10/30 MHz)* | standard (step 4 heavy) |

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

**`TH-11` — coil-loading trend across the eddy→displacement transition** 🟡
*(commissioned 2026-08-13, 10:30 review — validates `MAT-6`'s ΔR machinery
at rising f; owns the remaining half of §2's extrapolation sentence. Full
step-1/2 journals archived in `docs/planning/plan-archive.md`.)*
> * **Step 1 ✅ 2026-08-13** *(`tests/validation/test_coil_loading_larmor_probe.py`,
>   `20260814T003445Z_TH-11-step1-larmor-n2.log`)*: 64 MHz is feasible at
>   the 10 MHz price (solves 30.5 + 27.0 s at `-n 2`, 138 619 cells);
>   complex-power identities to ~1e-14, σ = 0 control exact. The reading
>   (printed, never gated): ΔR deviates **+10.2698%** from quasi-static
>   Dodd–Deeds vs 1.5834% at 10 MHz — but at 1.26 cells/δ it is
>   unattributable between physics and the under-resolved boundary layer.
>   *(The step-1 plan text misnamed its fixture — W = 0.25/near 0.0025 —
>   while pricing the W = 0.15 baseline; the run correctly took the priced
>   rung, per the 2026-08-15 review annotation.)*
> * **Step 2 ✅ 2026-08-15** *(`test_coil_loading_larmor_resolution.py`,
>   `20260816T003251Z_TH-11-step2-resolution-n2.log`, 390.9 s, `-n 2`,
>   417 914 cells)*: the `resolution_near` = 0.0025 rung reads
>   **+2.8063%**, a −7.4635 pp move — the pre-registered
>   **RESOLUTION-DOMINATED** band. Most of step 1's +10.27% was the
>   under-resolved ohmic layer, not physics; per the pre-registration **no
>   gated trend claim is scopeable on this evidence**. Unsettled: the
>   residual 2.81% at 2.52 cells/δ is ~9.9× the 10 MHz residual at coarser
>   relative resolution — suggestive of a real physics term, but not a
>   convergence measurement. The honest next rung is a third 64 MHz mesh
>   (`resolution_near` = 0.00125, ~3× cells ⇒ ~9 min/solve at `-n 2` —
>   cost-probe it) for a Richardson extrapolation in h before any physics
>   claim. §2's extrapolation sentence stands as written.
> * **Step 3 ✅ 2026-08-16** *(`test_coil_loading_transition_30mhz.py`,
>   `20260816T183310Z_TH-11-step3-30mhz-n2.log`, 10 passed, 70.3 s, standard,
>   `-n 2`, 138 619 cells, mesh 10.6 s + solves 30.5/26.7 s)*: the third point
>   reads ΔR deviation **+5.5912%** (ΔZ = +8.4022314e-01 − j2.4152825e+00 Ω vs
>   Dodd–Deeds +7.9573218e-01 − j2.5425171e+00 Ω), ΔX ratio **0.9500**. The
>   three points on this one rung are **1.5834% (10 MHz) → 5.5912% (30 MHz) →
>   10.2698% (64 MHz)**, monotone and close to linear in f; ΔX ratio moves
>   0.9200 → 0.9500 → 0.9690 in the same direction. All bookkeeping gates held
>   unmoved: complex-power identity **2.7373e-14** loaded / **1.6799e-14** free
>   against the 1e-9 family bound, σ = 0 dissipation exactly `+0.0` vs
>   +3.5532418e-01 W loaded, drive control, cell count exact. The reaction and
>   dissipation routes to ΔR agree to all 8 printed digits
>   (+8.4022314e-01 Ω both). **Still a trend point, not a trend claim** — the
>   confound is monotone too: cells/δ falls 3.18 → **1.84** → 1.26 across the
>   same three points, so the resolution term step 2 measured (worth −7.46 pp
>   at 64 MHz) grows alongside the physics term and this rung cannot separate
>   them. The honest next rung is unchanged from step 2's: a Richardson
>   extrapolation in h at fixed f, not a fourth frequency. §2's extrapolation
>   sentence stands as written.
> **Step 3 plan as scoped (2026-08-15, 18:00 review;
> the declared §9 spare, independent of step 2).** Step 1's module at
> f = 30 MHz on the step-1 baseline (W = 0.15 / near 0.005, 138 619 cells) —
> a third point across the eddy→displacement transition beside 10 MHz
> (1.5834%) and 64 MHz (+10.2698%). **Anchor:** the same identity gates as
> step 1 (complex-power < 1e-9, σ = 0 exact zero, drive control, cell count
> 138 619). **Reading (printed, never gated):** ΔR/ΔX beside Dodd–Deeds;
> the resolution caveat stated in the print — δ = 9.19 mm at 30 MHz ⇒
> 1.84 cells/δ on this rung, so this point carries the same unattributed
> resolution term as step 1 and is a trend *point*, not a trend *claim*.
> **Tier/cost:** standard, `-n 2`, ~60–75 s (step 1's price); container
> `timeout -k 30 590`. **Traps/scope/negative result:** step 2's, verbatim.
> * **Step 4 (scoped 2026-08-16, 18:00 review — the affordable half of the
>   Richardson programme steps 2 and 3 both recommended; heavy, one run).**
>   The h-ladder at **fixed f, at the two affordable frequencies**: solve
>   the loaded/free pair on the step-1 baseline (near 0.005, 138 619 cells)
>   *and* the step-2 refined rung (near 0.0025, 417 914 cells) at **10 MHz
>   and 30 MHz** — the baselines are already on record (1.5834% / 5.5912%),
>   so the new solves are the two refined-rung pairs. Extrapolate the ΔR
>   deviation to h → 0 at each f (Richardson, rate estimated from the pair
>   and printed beside step 2's 64 MHz move); the discriminating reading,
>   **printed, never gated**: extrapolated deviation ~flat in f ⇒ no
>   resolvable physics term below 30 MHz, rising in f ⇒ the term `TH-11`
>   is after survives mesh refinement. **Anchor (§4):** the step-1 identity
>   family on every rung — complex-power < 1e-9, σ = 0 exactly zero, drive
>   control, cell counts == 138 619 / 417 914. **Negative control:** the
>   two baseline-rung readings must reproduce their records (1.5834%,
>   +5.5912%) to the printed digits — a ladder that cannot reproduce its
>   own anchors has changed the fixture, not refined it. **Tier/cost:**
>   heavy, `-n 2`; step 2's refined 64 MHz pair cost 390.9 s total, and
>   frequency does not change the linear-system size, so budget ~400 s per
>   refined frequency — run as **two harness commands (one per f)**, each
>   `timeout -k 30 1100`, cost-probe the first before the second. **Traps:**
>   step 2's verbatim (FFCx lock after a kill; `-s`; complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first); print cells/δ
>   per rung (δ scales 1/√f·√(1+…) across the transition — compute it, do
>   not copy step 3's). **Scope:** the 64 MHz `near = 0.00125` third rung
>   (~9 min/solve, possibly over one slot) is **not** this step — if the
>   two-frequency extrapolation reads "rising", scoping that rung is the
>   review's next decision, not this run's. No gated trend claim either
>   way; §2's extrapolation sentence moves only when a review adjudicates
>   the extrapolated numbers. **Negative result:** flat-in-f is a *finding*
>   (the transition signal was resolution all along) — record both
>   extrapolations in this entry, report, stop.

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
| `PORT-9` | Lumped-element port boundary condition (the birdcage port model) | 🟡 *(step-1 formulation gated on `attempt/PORT-9-20260816T170800Z`; instantiation unblocked 2026-08-17 — `GEO-16` ✅ emits the sheet, `w/h = 1.504225878`, facet tags `211`/`212`)* | standard |
| `PORT-10` | The two `PORT-1` systematics: composition measured, not assumed | ✅ 2026-08-16 (cross-term **−0.0604 pp** inside the pre-stated ±0.5 pp) | heavy |

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
> * **Step 1 (🟡 attempted 2026-08-16, 12:00 slot — formulation landed,
>   instantiation blocked on the mesh) — formulation on the two-torus
>   fixture.** Implement the lumped-port BC on the existing gap faces (tags
>   101/102) and solve the gapped two-torus fixture at 10 MHz; print the
>   lumped-port `Z` beside the gated gap-voltage route on the same solved
>   field. No assertion beyond the existing identity gates; measurements feed
>   step 2.
>   > **Attempt 2026-08-16** (parked, `attempt/PORT-9-20260816T170800Z`;
>   > `20260816T170543Z_PORT-9-step1.log`, 10 passed, 4.29 s, smoke, `-n 2`).
>   > The **formulation** is written and gated: the resistive-sheet lumped
>   > port of Jin 3e §1.5.4 (1.60)–(1.63) in the variational form of §6.5
>   > (6.93)–(6.98), i.e. `a = +jωμ₀(1/R)∫_S(n̂×E)·conj(n̂×v)dS`,
>   > `L = −jωμ₀∫_S K_imp·conj(v)dS` with `K_imp = V_src/(Rh)ĥ` and
>   > `R = Z_p w/h` Ω/square (`ports/lumped.py`), pinned by six exact
>   > identities on a one-square sheet — including the circuit identity
>   > `I = V_src/Z_p` = 20 mA at 1 V/50 Ω to < 1e-12 relative, with a
>   > passive-sheet negative control. The **two-torus instantiation was not
>   > reached, and is blocked on geometry**: a lumped-port sheet spans
>   > terminal to terminal with the current flowing *in* its plane, whereas
>   > this fixture's only tagged surfaces (facet tags 201/202) are
>   > gap↔conductor cross-sections **normal** to the current — the wrong
>   > constitutive law, not a coarser one — and the gap is otherwise a cell
>   > volume (101/102, which the §9 item mis-names "gap faces"). The step
>   > therefore needs a **mesh-side prerequisite**: `two_torus_domain` must
>   > emit the gap box's longitudinal mid-plane as a surface, with the facet
>   > tag rebuilt from cell tags on the dolfinx side (known-issues 9). A
>   > second premise for step 2: the gap box crosses a *round* arc, so the
>   > sheet's `w` and `h` are not the box's nominal dimensions and the
>   > "number of squares" needs its own measured definition on this fixture
>   > before any `Z` read off it means anything. Full journal:
>   > `docs/testing/attempts.md`, 2026-08-16T17:08Z.
>   > **Review decision (2026-08-16, 18:00): option (a).** The mesh
>   > prerequisite is split out as `GEO-16` (§7 GEO table; emit the
>   > longitudinal mid-plane behind an opt-in kwarg, facet tag rebuilt
>   > dolfinx-side, sheet extents measured and printed). The parked
>   > branch is **kept, not merged and not deleted** — its six identity
>   > gates are the formulation's gate and its code is not capturable in
>   > plan text; the step-1 re-run **starts by merging
>   > `attempt/PORT-9-20260816T170800Z`**, wires the sheet onto
>   > `GEO-16`'s surface, and is a fixture wiring job, not a formulation
>   > job. Option (b) (a straight-wire gap fixture) was rejected: the
>   > step-2 cross-route comparison must happen on the two-torus fixture
>   > where the gap-voltage route is gated, so (b) defers the same mesh
>   > work without discharging anything.
>   > **Prerequisite discharged 2026-08-17: `GEO-16` ✅.** The step-1 re-run
>   > now has its surface — `two_torus_domain(..., emit_port_sheet=True)`,
>   > facet tags `211` (gap 1) / `212` (gap 2), area = CAD mid-plane to
>   > `1.000000000000`. Take `R = Z_p·w/h` from the **measured** extents
>   > `w = 1.200000000e-02 m`, `h = 7.977525299e-03 m`,
>   > **`w/h = 1.504225878` squares** — printed by the fixture, not nominal.
>   > Wiring trap the kwarg introduces: the gap volume is now **two** cell
>   > tags per box (`101`+`111`, `102`+`112`), so any selection by gap tag
>   > must take both halves; `201`/`202` are unchanged as sets.
> * **Step 2 (gate) — cross-route identity.** Pre-stated bands, set at
>   scoping and never widened: lumped-port `Im Z₁₂` within the unmoved
>   **10%** mutual band of ωM₁₂ (the `PORT-1` gate, absolute anchor), and
>   cross-route agreement `|Z₁₂(lumped) − Z₁₂(gap-voltage, corrected)| /
>   |Z₁₂(gap-voltage, corrected)| ≤ 5%` (two feed models on identical
>   geometry); reciprocity `‖S−Sᵀ‖/‖S‖ ≤ 1e-3` through
>   `run_n_port_sparameter_sweep`. A miss is a finding about one of the
>   feed models — diagnose, never widen.
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
>   tier, `-n 2`. **Serial:** depends on steps 1–2 landing on the
>   two-torus fixture; do not start it from a queue that hasn't seen
>   step 2's cross-route band hold. **Negative result:** a class spread
>   > 5% on the undisplaced mesh is a finding about mesh-induced
>   asymmetry at the graded sizing — record the measured spread per
>   class in this entry and stop; never widen (iii) to admit it.

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
| `EX-22` | Restore the absent example artifacts: refresh runs for `mag` 01/02/04/05/06 + `mri:1` (commissioned 2026-08-16 weekly review — see entry below) | ⬜ | heavy |

**`EX-22` — restore the absent example artifacts** ⬜ *(commissioned
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

1. **The birdcage-port lineage — prerequisites discharged 2026-08-16**
   (`PORT-10` ✅ composition additive, `GEO-15` ✅ graded sizing cheap,
   `ANS-3` ✅ runnable half; the AED half is the operator's): the front
   is now `PORT-9` itself (lumped-element port BC, Jin ch. 11): step 1's
   formulation is gated on `attempt/PORT-9-20260816T170800Z` but blocked
   on the `GEO-16` mesh prerequisite (18:00 review decision, option (a));
   then steps 1–2 on the two-torus fixture, then step 3 on the birdcage,
   whose gate is scoped in the §7 entry (reciprocity, passivity, C4
   circulant symmetry of Z).
2. **`TH-11`** — coil loading at Larmor frequencies: step 2 attributed
   most of the 64 MHz deviation to mesh resolution (+10.27% → +2.81%);
   step 3 ✅ added the 30 MHz mid-point (+5.5912%), but cells/δ falls
   3.18 / 1.84 / 1.26 across the three frequencies, so the confound is
   monotone with the signal. Step 4 (scoped, 18:00 review) is the
   Richardson extrapolation in h at fixed f — 10 and 30 MHz, the
   affordable frequencies.
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

Last reviewed 2026-08-16, **18:00 review**. Interval (since 10:30): four
slots ran in order. The 12:00 slot took `PORT-9` step 1 and **parked it**
(`attempt/PORT-9-20260816T170800Z`) — the resistive-sheet formulation is
written and gated by six exact identities, but the fixture has no
longitudinal port-sheet surface to put it on; the review adjudicated the
attempt's option (a): mesh prerequisite split out as **`GEO-16`** (new §7
chunk), parked branch kept for the re-run to merge. The 13:30 / 15:00 /
16:30 slots closed `TH-11` step 3, `EX-21`, and `OPS-19` step 1; all
three audited **COMPLIANT** (one subagent auditor each; logs footered,
anchors quantitative, plan numbers match the logs digit for digit).
`TH-11` **step 4 scoped** by this review (fixed-f Richardson ladder at
10/30 MHz — both step 2 and step 3 recommended it). `OPS-19`'s run also
corrected `EX-22`'s premise in place (the 24 references are *stale*, not
absent — `dead=0 stale=24`) and found only one docrefs call site. The
weekly review and the 02:15 slot move also landed this interval (their
own commits). Done-item texts and prior recaps:
`docs/planning/plan-archive.md`.

**Five items.** Items 1–3 are mutually independent; item 4 depends on
item 1; item 5 is the declared spare and depends on items 1 and 4.
Items 1–3 execute their §7 entries verbatim (`GEO-16`, `OPS-17` step 1,
`TH-11` step 4); items 4–5 execute the §7 `PORT-9` entries as annotated
by this review.

1. ✅ **done 2026-08-17** (`20260817T003627Z_GEO-16-regression.log`, 47.3 s,
   5 passed; sheet area = CAD to `1.000000000000`, measured
   `w/h = 1.504225878`; kwarg-off control bit-matches, incl. 3b-iv's
   `0.974490841`). **`GEO-16` — emit the longitudinal port-sheet mid-plane in
   `two_torus_domain` (standard, mesh-only, no solve).** Execute the §7
   `GEO-16` entry verbatim: opt-in kwarg, `occ.fragment` of the gap
   boxes' mid-plane, facet tag rebuilt from cell tags dolfinx-side
   (known-issues 9 — never a dim-2 gmsh group on an interior surface),
   sheet extents (area, *h*, *w*) measured and printed. Anchor:
   facet-set area vs occ mass-property area < 1e-9 rel, both boxes;
   kwarg-off bit-match of the recorded mesh is the negative control.
   ~120 s, `-n 2`, `timeout -k 30 500`. Independent of everything below.
2. **`OPS-17` step 1 — finiteness-only test inventory (smoke, no
   solves).** Execute the §7 `OPS-17` step-1 entry verbatim: sweep,
   table, dispositions — annotation and harness log only, nothing
   deleted yet. Independent of every other item.
3. **`TH-11` step 4 — fixed-f Richardson ladder at 10 and 30 MHz
   (heavy, two harness commands, one per frequency).** Execute the §7
   `TH-11` step-4 entry verbatim: refined-rung (417 914-cell) pairs at
   10 and 30 MHz, identity family on every rung, baseline records
   (1.5834% / +5.5912%) reproduced as the negative control, deviation
   extrapolated to h → 0 per frequency — printed, never gated. ~400 s
   per frequency at `-n 2`, `timeout -k 30 1100`, cost-probe the first
   command before the second. Independent of items 1–2.
4. *(serial)* **`PORT-9` step 1 re-run — lumped-port `Z` beside the gap
   route (standard, one solve).** **Depends on item 1 landing; if
   `GEO-16` did not land, stop and journal rather than improvising a
   surface.** Start by **merging `attempt/PORT-9-20260816T170800Z`**
   (formulation + six gated identities; re-run its
   `test_port_lumped_bc.py` to confirm green on the merge), then wire
   the sheet onto `GEO-16`'s facet set with `R = Z_p·w/h` taken from
   the **measured** extents `GEO-16` printed — never the gap box's
   nominal dimensions (the 17:08Z premise). Solve the fixture at
   10 MHz, print lumped-port `Z` beside the gap-voltage route **on the
   same solved field on the fragmented mesh**. **Anchor:**
   measurement-only — the existing identity gates stay green; printed
   comparators: gap-route corrected ratio 0.939849 × ωM₁₂,
   ωM₁₂ = 1.241755 Ω. The gap route is re-measured on the fragmented
   mesh — if it moved off its unfragmented record, print both and flag
   it; that delta is step 2's first exhibit, not a gate. **Negative
   control:** the parked branch's passive-sheet zero-field control,
   re-run on the merge. **Cost:** mesh ~40 s + one solve ~25 s +
   FFCx compile; ~180 s, `-n 2`, `timeout -k 30 500`. **Traps:**
   complex build + `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment`
   first; stale FFCx lock after a kill (clear `~/.cache/fenics`); `-s`
   to put the printed Z on record; the `'+'` restriction on the
   interior sheet is single-valued per Jin (1.60) — do not "fix" it.
   **Scope:** two-torus only; no birdcage, no S-claim; chunk stays 🟡.
   **Negative result:** a lumped Z wildly off the gap route is the
   finding step 2 exists to adjudicate — report both numbers in the §7
   entry, stop.
5. *(spare, serial)* **`PORT-9` step 2 — cross-route identity gate
   (standard).** **Depends on items 1 and 4 landing; if either did not,
   stop and journal rather than improvising past it.** Execute the §7
   `PORT-9` step-2 entry verbatim: lumped-port Im Z₁₂ inside the unmoved
   10% band of ωM₁₂; cross-route |ΔZ₁₂|/|Z₁₂| ≤ 5%; reciprocity ≤ 1e-3
   through `run_n_port_sparameter_sweep`. Bands pre-stated at scoping,
   never widened — a miss is a finding about one of the two feed
   models; diagnose in the §7 entry, stop. Cost: two routes on the
   step-1 artifacts, ~180 s, `-n 2`, `timeout -k 30 500`.

*(The per-review journal — slot recap, completion audits, plan-work notes,
§10 assessment — lives in the review commits and
`docs/planning/plan-archive.md`, not here.)*

If the queue drains: **stop and journal.** The former birdcage-port hold
is fully discharged: its two open questions closed as chunks 2026-08-16
(`PORT-10`, `GEO-15`), and `PORT-9` — the port model itself — is fully
scoped, step 3's gate included (10:30 review). Do not improvise beyond
the written `PORT-9` entry; its steps are serial by design. History of
the hold in `docs/planning/plan-archive.md`.

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
- [ ] Loaded birdcage + phantom simulation runs end to end *(the mesh half is
  done: both fixtures generate and are identity-gated in CI as of 2026-08-03,
  `GEO-9` steps 1 + 2b, and graded conductor sizing is gated as of
  2026-08-16, `GEO-15`. The two-torus excitation lineage closed —
  `PORT-1` ✅ 2026-08-15. What remains is ports on the birdcage itself:
  `PORT-9`, scoped ⬜.)*
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
   two days later — no re-plan forced.
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
   sentence stands until one gates.
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
still no completion date.

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

**Epitaphs.** None yet.

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
