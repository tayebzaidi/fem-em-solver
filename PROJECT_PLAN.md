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
  licenses no resonance, tuning, B1+ or SAR claim. See §2.2.
- **The same three gates pass at both Larmor frequencies on the same
  fixture** (`PORT-11` ✅ 2026-08-26, steps 2 and 3; audited COMPLIANT
  18:00 review). Frequency is demonstrably the only knob turned — the
  in-run 10 MHz rung reproduces leg (d)'s 4×4 to 1.158e-10 vs 1e-6 in
  both modules. **64 MHz:** reciprocity 2.581325834e-14 vs 1e-3, σ_max
  0.999721388 ≤ 1 + 1e-9, C4 class spreads 0.0573 / 0.0599 / 0.0370% vs
  0.5%. **128 MHz:** 7.030990825e-15, σ_max 0.998974779, spreads
  0.1012 / 0.0916 / 0.0654% — on a phantom that has crossed to
  displacement-dominated (loss tangent 0.9002, cells/λ 12.5024 against a
  pre-stated floor of 10, enforced before any gate is read). The 22.5°
  displaced control breaks (iii′) at 12.9 / 27.8% (64) and 16.7 / 34.7%
  (128) while (i) holds at ~1e-15. **Scope, hard:** this is a
  self-consistency identity set (reciprocity, passivity, C4 symmetry)
  on one gated fixture — it is *not* an absolute-accuracy, resonance,
  tuning, B1+ or SAR claim, and the feed systematics remain the
  two-torus ones (`PORT-1` 3b-xviii, `PORT-10`). The absolute comparison
  is the AED benchmark's job (`ANS-4` — runnable half ✅ 2026-08-30, the
  operator's AED replication at Zero and First Order pending).
- `post/evaluation.py` point location (all point evaluation goes through
  it), gmsh generation + tag QA, the runner, and the logging harness.

### 2.2 Not validated — do not trust, do not extend

- **The birdcage's port S-matrix at 10 / 64 / 128 MHz is a gated
  self-consistency identity set, not an absolute-accuracy result; no
  coil is tuned or resonant, and no Larmor-frequency figure has been
  compared against anything outside this code.** *(Rewritten 2026-08-26
  18:00 review — `PORT-11` ✅ at both Larmor frequencies; the 08-25 head
  "ports at 10 MHz only" is retired, see §2.1. What remains unvalidated
  and is what this bullet now covers: the **absolute accuracy** of any
  S/Z/coupling figure at 64/128 MHz (the gates are reciprocity, passivity
  and C4 symmetry — a wrong-by-a-constant-factor port model passes all
  three; the independent check is the AED benchmark `ANS-4` — its runnable
  half landed 2026-08-30, the operator's AED replication is pending), any
  resonance, mode-spectrum or
  tuning claim (Phase 6, no lumped capacitors exist), and B1+/SAR on a
  solved coil field. Two readings on record, gated by nothing: the C4
  spreads grow ~1.7× per Larmor step (0.055 → 0.057 → 0.101%) and
  `|Im P|/Re P` at the driven port rises 0.34 → 1.76 → 2.66 — stored
  energy, physics not noise, but the trend is what a resolution study at
  128 MHz would have to explain before any tighter band is written.
  Older text, kept for the record: the old head of this bullet on 08-25 was
  "The birdcage has ports at 10 MHz only; nothing is validated at a
  Larmor frequency", itself replacing "No coil or birdcage has ports".
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
  mass; `PORT-9` budgets from 98 k cells — measured on 0.7.2; the gate
  behind that figure was non-executing on `main` from the 0.11 merge until
  `GEO-21` ✅ 2026-08-26, which greened it on a **coarse-graded** control —
  0.966977 at 98 666 cells now reproduces the 0.967 / 98 k figure, but the
  live gate measures fine-vs-coarse grading, and the graded-vs-ungraded
  answer to this prerequisite question remains the 0.7.2 close). `PORT-9` **step 1 closed
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
  bullet for what it licenses. B1+ remains §10 subgoal 4; its port
  prerequisite `PORT-11` (the same three gates at 64/128 MHz) **closed
  2026-08-26**, so B1+ on the solved birdcage field is no longer blocked
  on ports — it is unscoped (a `WF`/`POST` chunk the weekly review owns).
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
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-11` | `PORT-1` ✅ 2026-08-15 (field-derived S through the package, two-torus fixture only, two named systematics); `PORT-10` ✅ 08-16; **`PORT-9` ✅ 2026-08-25 at 10 MHz on the gapped 4-leg birdcage** — leg (d1′)'s geometric negative control passed on the power-wave route (displaced classes 6.2219 / 7.1142 / 2.8474% vs the tightened (iii′) 0.5%, reciprocity 2.259e-14 vs 1e-3, 2.466e+11× from the pre-fix 5.57e-03), no Larmor/resonance/tuning claim; history: steps 1–2c ✅ on the two-torus (lumped-sheet BC, 1.8333% cross-route, reciprocity 2.6e-11), step 3 on the gapped birdcage has two gated legs (c)/(d0) at 10 MHz (C4 spread 0.0152–0.0159% vs 5%, 50 Ω termination separates the classes 598× — re-recorded image-tagged on the 0.11 image 2026-08-24 by leg (d3c): 0.0359%, 253.2002×) and **leg (d) closed 2026-08-23 — the 4×4 passes all three gates** (reciprocity 2.495292352e-05 vs 1e-3, σ_max 0.862659137 ≤ 1, class spreads 0.0199 / 0.0180 / 0.0108% vs 5%, gate (iii) since tightened to 0.5%); leg (d1)'s geometric control ran 2026-08-23 and **found the route loses reciprocity (5.57e-03 vs 1e-3) once the fixture is asymmetric**; leg (d2) (asymmetric two-torus, 13:30 slot) traced it to the assembly — the readout *is* the source's adjoint (1.33e-10), the asymmetry is the terminated-`Z` per-column normalisation — and the 18:00 review ruled the power-wave S fix (leg (d3)) with the class re-record (d3b), (d1′) serial on (d3b); **`PORT-11` ✅ 2026-08-26 — the same three gates at 64 and 128 MHz on the same fixture** (64: 2.581325834e-14 / σ_max 0.999721388 / spreads 0.0573 / 0.0599 / 0.0370%; 128: 7.030990825e-15 / 0.998974779 / 0.1012 / 0.0916 / 0.0654%, cells/λ 12.5024 ≥ 10 enforced; audited COMPLIANT 18:00 review) — self-consistency identities only, no absolute-accuracy/resonance/tuning claim; `PORT-4`…`PORT-8` open |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 for excitation; both meshes (coil+phantom, birdcage) generate and are identity-gated in CI (`GEO-9`, 2026-08-03); the birdcage fixture is loaded (phantom inside) and since `GEO-18` ✅ 2026-08-22 has terminals and port sheets — the first B1+ chunk is **`WF-6` step 1, scoped 2026-08-29 10:30 review** (§10 subgoal 4; 10 MHz on the loaded F-small birdcage) |
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
| `OPS-26` | **Systematic dolfinx-0.11 migration completeness sweep** — re-run `OPS-17`'s "observed in a completed run" census on the 0.11 image and statically sweep `src/` for un-migrated call sites. Two silently-broken gates have already been found *by examples rather than by the upgrade's own re-gate* (`TH-9` cavity, `OPS-24`; straight-wire h-refinement, red on `main`, found 2026-08-25 by `mag:6`); a third is likelier than not. **Commissioned 2026-08-25 by operator directive, interactive session** — queue at the next review. *Queued 2026-08-25 10:30 review: step 1 is §9 item 3; step 2 held until step 1's site list lands.* ***Step 1 ✅ 2026-08-25, 15:00 slot** — `src`/`tests` clean at 434 call sites / 29 APIs, negative control binding and passing, two survivors filed in `scripts/probes/`; step 2 (execution census) is now unblocked.* ***Step 2 leg (a) DONE 2026-08-27 (four consecutive slots, 19:30 → 00:00)** — the seven cheap roots at **184 / 189 observed (182 green, 2 red), 5 deferred**, every deferral with a substantive reason and `182 + 2 + 5 = 189`; two reds and one rank-dependent deadlock filed in known-issues (all three carry the 0.11 "overlapping facets" string on *different* generators — owner **`GEO-23`**, commissioned by the 03:00 review), one dead module filed. The fix that unstuck `tests/solver` (0 → 47/51 in ~220 s) was one command per module; leg (b) adopts it from the start. Step 2 stays 🟡 on leg (b) (§9 item 1).* ***Step 2 leg (b) PARTIAL 2026-08-27 (04:30 slot)** — denominator re-derived at **289 / 63 modules** (`validation` 272/59, `ports` 17/4); **22 observed (19 green, 3 red), 267 deferred**, `tests/ports` **complete at 17/17**, `tests/validation` at 5/272. New defect class found (**finding 12**): `tests/ports/test_port_orientation_sensitivity.py` is red because `OPS-14`'s rank-safety `comm.allgather` outgrew its `_DummyComm` double — not a 0.11 break, and invisible to step 1's static sweep by construction. The owed `materials` complex conversion **failed onto a fifth `GEO-23` "overlapping facets" site**, the second rank-dependent one; leg (a)'s 184/189 is unchanged with that name's deferral reason upgraded. Two known-issues entries filed. Leg (c) owns the ~267-name `tests/validation` remainder.* ***Step 2 leg (b) PARTIAL, second slot 2026-08-27 (06:00)** — **139 / 289 observed (136 green, 3 red), 150 deferred**; `tests/validation` **5 → 122 of 272**, this slot's **117 names all green**, twenty-seven module-per-command runs, no batching, **no red, no no-footer deferral, no exit 124**, 2 028 s. **Finding 15:** `grep -L complex tests/validation/test_*.py` returns **6 of 59** — 53 modules are complex-gated, so the real build scores them as runtime skips, which is the structural reason attempt 1 banked 5 names; running the complex build for the 53 and the real build for the 6 banked **117** in one slot at the cost of one zero-compute grep, and all 6 real-build modules are now green, so the remainder is entirely complex work. **Finding 16:** cost is concentrated, not spread — gap-voltage 483 s + circular-loop 350 s are 41% of the slot for 20% of its names — and thirteen 0.11 prices are banked for leg (c). **Finding 17:** `test_circular_loop.py`, which stopped `OPS-17` (b2) attempts 1–2 with the JIT failure that commissioned `OPS-22`, is `3 passed in 348.74s` complex — the fixture fix holds on 0.11. Leg (c) owns the remaining **150** names over **28** modules (`coil_loading_*` 58, `dodd_deeds_*` 38, birdcage 32, straight-wire 7, a 13-name cheap remainder, the one complex-only skip).* ***Step 2 leg (c) PARTIAL 2026-08-27 (07:30 slot)** — **188 / 289 observed (184 green, 4 red), 101 deferred**; `tests/validation` **122 → 171 of 272**, fourteen module-per-command runs, 1 874 s. The **birdcage `PORT-9`/`PORT-11` block is complete at 32/32 green** for 593 s (18.5 s/name, the census's best rate — priced blocks before unpriced cheap tails is what bought the slot 49 names). **Finding 18 — leg (b)'s build classifier is unsound and its failure mode is invisible to the fail-closed control:** `grep -L complex` misfiled the real-build magnetostatics module `test_straight_wire.py` as complex-gated on a *comment* at line 94, and running it in the complex build produced a **footered Status-1 red** (`TypeError: '>' not supported between instances of 'complex' and 'float'`, 3 failed / 4 passed, 192 s) indistinguishable from a genuine red; in the real build the same module is **7 passed, Status 0, 314 s**. Sound classifier, now used: grep the actual gate (`complex_mode|requires_complex|is_complex|skipif`). **Finding 19 (red, filed):** leg (b)'s owed complex conversion of `test_geometry_floor_discriminator.py` lands on a genuine red — it asserts the **pre-`OPS-18`** 128 MHz record 1.8260% and measures `OPS-18`'s 1.7686% (3.14% > 1%); a stale constant, not a `TH-10` finding. **Finding 20:** `test_helmholtz_v2.py`, the `OPS-17` (b2) attempt-2 *hang*, is `1 passed in 1.24s` in the **real** build — the hang was a finding-18-class build-gate artifact. **Finding 21:** `test_port_gap_voltage_padding.py`, the `OPS-17` (b2) formal deferral, re-priced not inherited — **Status 124 at 400 s with zero `PASSED`/`FAILED` lines printed**, i.e. it completed none of its 2 tests in the window; deferral upgraded from inherited to measured. Leg (d) owns the remaining **101** names over **16** modules: `coil_loading_*` 58, `dodd_deeds_*` 38, `test_port_systematics_composition.py` 3, and finding 21's 2.* ***Step 2 leg (d) PARTIAL 2026-08-27 (09:00 slot)** — **207 / 289 observed (202 green, 5 red), 82 deferred**; `tests/validation` **171 → 190 of 272**, four module-per-command runs, 704 s, three footered (Status 0/0/1) and one Status 124. **Finding 23 (red, filed):** `test_coil_loading_larmor_mesh_cache.py::test_the_cached_rung_is_the_priced_mesh` asserts the **exact** 0.7.2-era cell count 2 807 309 and 0.11's gmsh meshes **2 808 204** — **+0.032%**, a mesher-version drift against an equality record, with the module's other 4 names green in the same run. That is the **third** site of the class leg (c)'s finding 19 named (`test_geometry_floor_discriminator.py`) and `GEO-16` first showed: **records made on 0.7.2 and not swept when `OPS-18` re-recorded**. The class, not the constant, is the deliverable — a review should commission one sweep over all exact-equality records rather than three one-constant fixes. **Finding 24:** the real-build route for `larmor_mesh_cache` is real and cheap — `OPS-17` (b2) priced it at 445.55 s **complex**, this slot ran it **real at 219 s (2.03×)**, and its 4 environment skips are all complex-only tests outside the census roots, so a gate-classifier "not complex-gated" verdict (finding 18's rule) is worth **half the window** on this module. **Finding 25:** `test_coil_loading_larmor_third_rung.py` did **not** reproduce its `OPS-17` (b2) record — recorded `11 passed / 174.86 s / exit 0` at `-n 8` with `TH11_STEP5_RUNG=fine`, this slot **Status 124 at 300 s** with only the module's first (non-solving) test out, `deferred — no footer`. The likely cause is **ordering**: in attempt 8 `mesh_cache` ran immediately *before* it and populated the rung's on-disk cache, so 174.86 s is a **warm-cache** price, not the module's. Leg (e) should run `mesh_cache` first and `third_rung` second in the same slot, at `-k 30 500`. **Rate note (finding 22 confirmed):** the two priced `dodd_deeds` modules returned **14 names for 184 s = 13 s/name**, the census's best rate to date, against 219 s for 5 names on the unpriced-in-this-build `mesh_cache`. Leg (e) owns the remaining **82** names over **13** modules: `coil_loading_*` 53 (of which `degree2`'s 14 are the `TH-12` structural defer and `third_rung`'s 7 need the cache ordering), `dodd_deeds_*` 24 over 5 modules (all ~400 s single-fixture files, widths in the leg-(c) price table), `test_port_systematics_composition.py` 3, `test_port_gap_voltage_padding.py` 2.* *Queued as leg (e) by the 2026-08-27 10:30 review (§9 item 1); the three stale-record reds are `OPS-27`, finding 12's test double is `OPS-28`.* ***Step 2 leg (e) PARTIAL 2026-08-27 (12:00 slot)** — **214 / 289 observed (208 green, 6 red), 75 deferred**; `tests/validation` **190 → 197 of 272**, five compute windows, 1 853 s, three footered (Status 1/1/1) and two Status 124. **Finding 25 CONFIRMED and the ordering remedy works:** `mesh_cache` real first (262 s, its 4 green + the filed finding-23 red reproduced verbatim), then `third_rung` complex `-n 8` `fine` against the warm cache — which **footered at 304 s**, where the same command cold had been Status 124 at 301 s. The recorded 174.86 s was indeed a warm-cache price; the module's own cold price is ≥ 500 s. **Finding 27 — the trap list's "sweep 0-byte FFCx stubs first" is not optional, and skipping it cost this slot a 329 s window.** The first warm `third_rung` attempt returned a **footered Status 1 with all 7 census names in ERROR**, every one `RuntimeError: Failed JIT compilation of form: JIT compilation timed out, probably due to a failed previous compile … libffcx_forms_1ea5a4c22c3fbbdfad7ef834d249519203ba0bb6.c`. The cache held **exactly one** 0-byte `.c`, timestamped 14:07 — i.e. created by *leg (d)'s own* 300 s kill of this very module five hours earlier. One `rm` and the identical command produced `1 failed, 17 passed`. **This is the failure mode the fail-closed control cannot see** (compare finding 18): a poisoned stub yields a *footered* run whose names are ERROR, not absent, so a census that trusted the footer would have recorded 7 spurious reds. **Rule, now mandatory: sweep `find /root/.cache/fenics -name '*.c' -size 0` before the first window of every slot, and again after any exit-124 window, because a killed window poisons the cache for the next one.** **Finding 28 (red, filed, the fourth stale-record site):** `third_rung::test_the_rung_is_inside_the_priced_ceiling` asserts the exact 0.7.2 fine-rung count **417 914** and 0.11 meshes **418 888** — **+0.233%**, seven times the `mesh_cache` site's relative drift, same sign, with the module's other 6 names (both complex-power identities, the free-solve dissipation identity, and `test_the_fine_rung_reproduces_step2s_recorded_deviation`) green in the same run. So the rung's *physics* reproduces its `TH-11` record while only its cell count does not. **Note for `OPS-27`: its planned `grep -rn '0\.7\.2' tests/` would not necessarily reach this constant** — it was found by reading a red's assertion message, so the sweep clause should be widened to exact-equality mesh counts regardless of version tag. **Finding 29 — two `dodd_deeds` prices from leg (c) did not hold on this image, both near-misses:** `reactance_combined_knobs` `-n 8` (recorded 421.90 s) was **Status 124 at 521 s** having printed one `PASSED`, and `resistance_slab_resolution` `-n 2` (recorded 386.82 s) was **Status 124 at 437 s** having reached **100% of its progress bar on both ranks** before dying in teardown/summary. Both are `deferred — no footer` by the fail-closed control despite the second one visibly finishing its tests — the control is working as designed, and the remedy is width, not interpretation: budget these two at **≥ 600 s** (slab is worth ~450 s + margin, knobs unknown above 520 s). No stub and no stray `python3` was left by either kill. Leg (f) owns the remaining **75** names over **12** modules: `dodd_deeds_*` 24 over 5 (two of them now re-priced upward), `coil_loading_*` 46 (of which `degree2`'s 14 remain the `TH-12` structural defer), `test_port_systematics_composition.py` 3, `test_port_gap_voltage_padding.py` 2.* ***Step 2 leg (f) PARTIAL 2026-08-27 (13:30 slot)** — **255 / 289 observed (242 green, 13 red), 34 deferred**; `tests/validation` **197 → 238 of 272**, six compute windows, 2 314 s, five footered (Status 1 ×5) and one Status 124; **41 names banked**, the census's best rate on the expensive tail. **Finding 30 — the stale-record class collapses to shared meshes, and it re-shapes `OPS-27`:** this slot's six reds are all of that class, and pooling them with legs (c)–(e) gives **nine red names over eight modules carrying only FOUR distinct 0.7.2-era cell counts** — 138 619 → 138 490 (**−0.093%**) in `richardson_ladder` ×2 params, `larmor_probe` and `transition_30mhz`; 417 914 → 418 888 (**+0.233%**) in `slab_resolution`, `larmor_resolution` and `third_rung`; 697 401 → 697 926 (**+0.075%**) in `combined_knobs`; 2 807 309 → 2 808 204 (**+0.032%**) in `mesh_cache`. Two consequences: the **unit of repair is the mesh, not the file** (a per-file fix leaves siblings red; one re-record retires up to four names, so `OPS-27` is **four measurements and ~nine edits**, not nine measurements), and the **drift is per-mesh, not a global offset** (it does not even share a sign, so no unmeasured record can be predicted from a measured one). Leg (e)'s note that `grep -rn '0\.7\.2' tests/` is insufficient is confirmed twice over — none of the five new sites was reachable by version tag; all were found by reading a red's assertion message. **The census is the sweep: `OPS-27` should take its site list from finding 30's table, not re-derive it by grep.** **Finding 31 — item 1's own draw order is lossy and cost-relevant:** `richardson_ladder` was budgeted as two commands / 800 s, but `OPS-17` step 3j had already refuted the split in the journal (`TH11_STEP4_RUNG` selects the *mesh*, `FREQ_MHZ=10,30` selects both parametrisations) — **one command, all 14 names, 143 s**; and the "unpriced" `larmor_probe`/`transition_30mhz` pair was priced in the journal at 137.18 s and reproduced at **137.35 s (+0.12%) for 12 names**. Two zero-compute greps turned a budgeted 800 s + "unpriced" into 282 s for 26 of the slot's 41 names. **Rule: grep `attempts.md` for the module name before sizing any window.** **Finding 32:** finding 29's ≥ 1.5× sizing rule is validated — `slab_resolution` footered at 429.91 s (+11.1% over record) and `combined_knobs` at 568.26 s (**+34.7%**, the census's largest under-price, which is why its 520 s and 615 s windows fell on opposite sides) — but `reactance_box_truncation` is not a pricing near-miss: at `-n 8` / 600 s it died **inside its first validation test** with no other name started, so it is `deferred — measured, first test alone > 590 s at -n 8` and must not get a third `-n 8` window without a by-name split or a width change (its first test is itself another cell-count equality, so finding 30 predicts a tenth red behind it). Finding 27's cache sweep was run before window 1 and again after the exit 124 — **clean both times**, zero stray `python3`. Leg (g) owns the remaining **34** names over **6** modules, of which only **20 over 5** are reachable (`degree2`'s 14 stay the `TH-12` structural defer): the three untried `dodd_deeds_*` 15, `test_port_systematics_composition.py` 3, `test_port_gap_voltage_padding.py` 2 — one slot should finish the tail **and** write the chunk-level reconciliation.* ***Step 2 leg (g) PARTIAL 2026-08-27 (15:00 slot)** — **264 / 289 observed (250 green, 14 red), 25 deferred**; `tests/validation` **238 → 247 of 272**, four compute windows, 1 606 s, three footered (Status 0/0/1) and one Status 124; **9 names banked**, and the reachable tail is down to **9 names over 3 modules**. The two `PORT` unknowns are now resolved in opposite directions: `test_port_systematics_composition.py` is **14 passed / 363.35 s** (`-n 2`, +0.87% on its `20260821T034507Z` record of 360.23 s) — its 3 census names green, and the `PORT-10` batch-C killer is simply an expensive file, not a broken one. **Finding 33 — `test_port_gap_voltage_padding.py` is a measured structural deferral, not a pricing miss, and it is now cited to two windows at the same width:** at `-n 2` / **590 s** it printed `collected 2 items` and then the name of its first test and nothing else — Status 124, zero `PASSED`/`FAILED` lines, exactly as at 400 s (finding 21). Its `gap_ports_padded` fixture is `scope="module"`, so a by-name split cannot help — it would pay the same setup twice — and the deferral reason is upgraded to **`deferred — measured, module fixture alone > 590 s at -n 2`, two windows (400 s, 590 s)**. That makes it the same shape as `box_truncation` (finding 32) and a *substantive* reason for step 2's close criterion, not a `not reached in slot`. **Finding 34 — finding 31's journal-grep rule paid a third time, and `reactance_wire_resolution` was never unpriced:** item 1 budgets it as "record 491.96 s with 2 deselected, full file unpriced, ≥ 740 s" and therefore unrunnable in one foreground window, but the journal carries **two disjoint `-k` halves** from 2026-08-20 (`pinned` 242.68 s, `projected or refinement` 499.80 s) that together cover all 6 validation names. Run at those boundaries — with the environment root dropped and the second half selected by **node id** rather than `-k "a or b"` (the quoting trap) — the halves came in at **214.36 s (−11.7%)** and **434.40 s (−13.1%)**, *both under their records*, and the file is complete at 6/6 in 649 s against a budgeted ≥ 740 s for one window that could not have run. Note the sign: this is the first module family to come in **under** its 0.7.2-era price, which is why finding 29's ≥ 1.5× rule must stay a *sizing* rule and never becomes a prediction. **Finding 35 (red, filed) — a tenth stale-record name, a fifth mesh, and it has no sibling:** `wire_resolution::test_the_refinement_landed_on_the_wire_and_not_on_the_far_field` asserts the exact 0.7.2 count **366 207** and 0.11 meshes **365 970** (**−0.0647%**, the second negative drift), with the module's other 5 names green across the two halves. A zero-compute `grep -rn '366207' tests/` finds **only this site** — so finding 30's "one re-record retires up to four names" is an upper bound and the value→module map is ragged (**4, 3, 1, 1, 1**); `OPS-27` should size itself as **five measurements, ~ten edits**. Finding 27's cache sweep ran before window 1 and again after the exit 124 — clean both times, zero stray `python3`. Leg (h) owns the remaining **25** names over **4** modules, of which only **9 over 2** are reachable: `reactance_box_size` **4** (journal-priced at **559.58 s full file at `-n 2`**, or two recorded `-k` halves of 271.08 s + 260.07 s — take the halves, the full file was 98.2% of its window) and `box_truncation` **5** (finding 32: `-n 2` or a by-name split, never a third `-n 8` window); `degree2`'s 14 and `gap_voltage_padding`'s 2 are both defers-with-reason and are **not** to be re-opened. **Leg (h) should finish the tail and owes the chunk-level reconciliation.*** ***Step 2 ✅ 2026-08-27 (16:30 slot, leg (h)) ⇒ chunk ✅.** Final: **268 / 289 observed (254 green, 14 red), 21 deferred**; `tests/validation` **247 → 251 of 272**, `tests/ports` 17/17. Three windows, 1 166 s, two footered (Status 0/0) and one Status 124. `reactance_box_size` is **4/4 green** on its two recorded `-k` halves (282.59 s + 289.44 s = 572 s, +4.2% / +11.3% on the 2026-08-20 record — **finding 37**: taking the halves was right, the full file's 559.58 s + 11% would have blown a 590 s window). **Finding 36:** `reactance_box_truncation` is a **permanent measured deferral** — Status 124 at both `-n 8`/600 s (leg (f)) and `-n 2`/590 s (this slot), each dying inside its first validation test; its `projected_xlarge_box` fixture is `scope="module"` and all five tests consume it, so width is not the constraint and a by-name split cannot help. It needs a *smaller fixture*, not a different selection — a `MAT-6` pricing question, not a census one. Finding 30's predicted eleventh red sits behind that fixture and is **pending**, not falsified. **Chunk-level reconciliation (written in `attempts.md`, 2026-08-27T22:20Z):** repo-wide over both censuses, **478 collected → 452 observed (436 green, 16 red), 26 deferred** (452 + 26 = 478), i.e. **94.6% of the repo's collected tests observed in a footered run on 0.11**, with **zero `not reached in slot` and zero `deferred — no footer`** surviving. The **seed list of four is green by name** — `test_convergence.py` **1 passed / 141.51 s** (its `test_h_refinement_straight_wire`, cited in this chunk's own rationale as *red on `main` right now*, **PASSED**; `MAG-20` owns the band, but the gate executes), `test_port_lumped_two_torus.py` 5 passed / 90.97 s, `test_cavity_resonances.py` 3 passed / 5.59 s, `test_birdcage_conductor_sizing.py` PASSED in leg (a)'s 38-item run. The **16 reds are exactly three families with named owners**: ten stale 0.7.2-era exact records over 8 modules but only **5 distinct meshes** (`OPS-27`), three "overlapping facets" reds (five `GEO-23` *sites* counting the dead `test_cylindrical_domain.py` module and the rank-divergent `materials` conversion — 10 + 3 + 3 = 16), and three test-double-drift names (`OPS-28`, finding 12 — invisible to step 1's static sweep by construction). The **26 deferrals** are `degree2` 14 (`TH-12` memory wall), `box_truncation` 5 (finding 36), `gap_voltage_padding` 2 (finding 33), leg (a)'s 5 (all `GEO-23`/filed) — every one a measured cost or a filed defect. **No band was loosened and no red fixed in-slot across seven census slots.** **Answer to the operator's directive:** the 0.11 transition worked; the three exception families are stale *records* (the physics reproduces), one gmsh boundary-mesh family, and one mock a prior chunk's rank-safety fix outgrew — **`OPS-18`'s §4 close stands**, every §2 physics claim's gate was observed executing and passing on 0.11.* *Audited COMPLIANT 2026-08-27 18:00 review — all 18 leg (e)–(h) footers re-read (statuses and per-leg elapsed sums 1 853 / 2 314 / 1 606 / 1 166 s reproduce from the logs), 18 matching `test-results.md` rows, reconciliation arithmetic verified (268 + 21 = 289, 452 + 26 = 478, 16 = 10 + 3 + 3, 26 = 14 + 5 + 2 + 5); one wording defect corrected in this row (the reds-vs-sites conflation above). The §7 prose entry below narrates step 1 and leg (a) only — the leg (b)–(h) evidence lives in this row and `attempts.md`.* | ✅ | heavy (split across ≥ 2 slots) |
| `OPS-27` | **Re-record the 0.7.2-era exact records the `OPS-18` re-record did not reach, version-tagged on the `GEO-16` precedent, and sweep for siblings** — two reds on `main` filed by the `OPS-26` census: `test_geometry_floor_discriminator.py` `RECORD_128_RELL2` = 0.01826 vs `OPS-18`'s 1.7686% (leg (c) finding 19) and `test_coil_loading_larmor_mesh_cache.py` `NCELLS_THIRD` = 2 807 309 vs 0.11's 2 808 204 (leg (d) finding 23, +0.032% mesher drift); `GEO-16`'s 79 534 → 79 070 was the first of the class. No band introduced; a `grep -rn '0\.7\.2' tests/` sweep (11 files) tabulated for a third site. Commissioned 2026-08-27 10:30 review. *Re-scoped 2026-08-27 18:00 review from the finished census: the class is **ten names / eight modules / five meshes** plus the relative-L2 pair, every 0.11 value already measured in a census log — split into **step 1** (cheap half: geomfloor, the 138 619 family, `mesh_cache`; ≈ 570 s) and **step 2** (expensive half: the 417 914 family, `combined_knobs`, `wire_resolution`; ≈ 1 440 s), independent; `box_truncation`'s suspected sixth mesh pending on a cheaper fixture. Rubrics: §9 items 1 and 2.* ***Step 1 ✅ 2026-08-27 (19:30 slot)** — the cheap half landed exactly as ruled: `RECORD_128_RELL2` 0.01826 → **0.017686** / `RECORD_128_SEPARATION` 57.31 → **59.16**, `NCELLS_BASELINE` 138_619 → **138_490**, `NCELLS_THIRD` 2_807_309 → **2_808_204**, every one an exact equality version-tagged with its 0.7.2 digit and its census log in-comment (`GEO-16` precedent), **no band anywhere and `git diff -- src/` empty**. All four anchors green from `main` in four foreground windows, 604 s total: geomfloor `12 passed / 46.45 s` (Status 0, 49 s, `-n 2` complex), richardson `FREQ_MHZ=10,30` **`25 passed` / 147.00 s** where the census read `2 failed, 23 passed` (Status 0, 149 s), probe + 30 MHz **`23 passed` / 149.09 s** where the census read `2 failed, 21 passed` (Status 0, 150 s), `mesh_cache` **real** `12 passed, 4 skipped / 254.75 s` where the census read `1 failed, 11 passed, 4 skipped` (Status 0, 256 s). Collected counts identical to the census runs (25 / 23 / 16), so exactly the six stale-record names flipped and no other name's status moved. **Finding 38 — the 138 619 family is ONE constant, not four:** `richardson_ladder`, `transition_30mhz` (and `degree2`) all *import* `test_coil_loading_larmor_probe.NCELLS_BASELINE`, so finding 30's "the unit of repair is the mesh, not the file" holds in its strongest form — one edit retired four reds, and a per-file sweep would have found nothing to edit in two of the three modules. **Finding 39 — the `0.7.2` completeness grep is confirmed empty:** `grep -rn '0\.7\.2' tests/` returns 26 hits over 11 files and **none** is one of this chunk's sites; every hit is either an already-swept record carrying both digits or prose. The demotion to a completeness check was right. **Finding 40 (scope note for step 2 / the review):** the value greps surface **prose** copies of these meshes in modules outside either step's scope — `138 619` in `test_coil_loading_degree2.py` (×5), `test_degree2_energy_mechanism.py`, `test_dodd_deeds_impedance.py` (×2), `test_dodd_deeds_projected_drive.py`, `test_dodd_deeds_reactance_box_size.py`, `test_dodd_deeds_reactance_box_truncation.py` (×3), `test_dodd_deeds_reactance_combined_knobs.py` (×3), `test_dodd_deeds_reactance_wire_resolution.py` (×3), `test_dodd_deeds_resistance_slab_resolution.py` — and `417 914` in `richardson_ladder` (×3). None is asserted (the `_dodd_deeds_` ones are growth-ratio *denominators* printed for scale, not records), so none was edited under this step's "five names, five files" scope; they are stale documentation and want a single prose sweep after step 2 lands, not an in-scope edit here.* ***Step 2 ✅ 2026-08-27 (21:00 slot) ⇒ chunk ✅** — the expensive half landed as ruled: `NCELLS_FINE` 417_914 → **418_888** (`slab_resolution`, `larmor_resolution`), `NCELLS_COMBINED` 697_401 → **697_926** (`combined_knobs`), and the `:268` literal 366_207 → **365_970** (`wire_resolution`); exact equalities, version-tagged, no band, `git diff -- src/` empty. Three anchors green from `main`, **1 523 s**, all Status 0: slab `-n 2` **16 passed / 479.37 s** (census `1 failed, 15 passed`), knobs `-n 8` **15 passed / 577.00 s** (census `1 failed, 14 passed`), wire-projected `-n 2` by node id **4 passed / 459.44 s** (census `1 failed, 3 passed`); collected counts identical (16 / 15 / 4). **Finding 41:** `third_rung:443` holds no constant — it imports `NCELLS_FINE` from `larmor_resolution`, so the rubric's five edits are **four**, and step 1's finding 38 (import aliases, not per-file records) repeats on a second family. **Finding 42:** `combined_knobs` reproduced inside its finding-32-widened 660 s window at 577.00 s (+1.5% on its census reading); all three anchors came in **above** their census elapsed (+11.5% / +1.5% / +5.8%), so the ≥ 1.5× rule stays a sizing rule. **Finding 43:** the negative control is name-and-status level only — an all-green run captures the prints the census log showed via failure capture. `larmor_resolution` and `third_rung` are edited but not re-run (same mesh value the slab run measured; `third_rung` is warm-cache-only 304 s at `-n 8`, finding 25) — their known-issues line is re-headed 🟡 "re-recorded, re-run owed to the next census". Retired: the leg (f) entry in full, the leg (g) `wire_resolution` entry. `box_truncation`'s suspected sixth mesh stays pending, fixture not opened.* ***Step 3 ✅ 2026-08-28 (16:30 slot) — the owed tail is closed.** Both re-runs green from `main` in two foreground windows, **719 s**, both Status 0 with identical rank streams: `test_coil_loading_larmor_resolution.py` `-n 2` complex **`17 passed` / 424.32 s** (`20260828T213049Z_OPS-27-step3-larmor-resolution.log`, 426 s) where the census read `1 failed, 16 passed`; `test_coil_loading_larmor_third_rung.py` `-n 8` complex `TH11_STEP5_RUNG=fine` **`18 passed` / 291.03 s** (`20260828T213807Z_OPS-27-step3-thirdrung.log`, 293 s) where the destubbed census read `1 failed, 17 passed`. **Collected counts identical to the census runs (17 / 18)**, so exactly the two stale-record names flipped and no other name's status moved — the `NCELLS_FINE == 418_888` equality and its imported alias (finding 41) are both executed green now, and both known-issues entries are RETIRED. **Finding 44 — the cold price feared for `third_rung` does not exist on the record.** Finding 25 inferred a "≥ 500 s cold" from a 300 s kill and a 304 s warm footer, and the rubric sized a 900 s window for it; the module returned at **291 s, below the warm figure**, with `larmor_resolution` having run first as ruled. So this slot again measured a *warm-fixture* price and the cold price is still unmeasured — the ≥ 500 s number should not be carried forward as if it were a measurement. **Finding 45 — the finding-40 prose sweep is not a mechanical substitution; three quarters of the copies must keep the 0.7.2 digit.** Of the 33 spaced-form `138 619` / `417 914` copies `tests/` carried at `ac7f03f`, **19 were re-recorded** (each written as the 0.11 value with the 0.7.2 digit kept in the same comment, so the *old* digit's count does not fall) across seven modules — `richardson_ladder` ×3, `larmor_resolution` ×5, `third_rung` ×2, `degree2` ×5, `dodd_deeds_impedance` ×2, `projected_drive`, `slab_resolution`; `grep -rno '138 490\|418 888' tests/` goes **14 → 33**, i.e. exactly 19 new sites — and the rest were deliberately left, in three kinds: (a) **dated result blocks** that narrate a 0.7.2 run (`slab_resolution` and `wire_resolution`'s log-cited ladder tables, `degree2`'s two `20260818T…` probe/calibration comments, `degree2_energy_mechanism`'s "`TH-12` step 2 measured"), (b) **executable growth denominators and the print strings and docstring ratios coupled to them** (`wire_resolution:263/266`, `combined_knobs:246/247` and its "5.03×", `box_truncation:334` and its "4.29×", `slab_resolution`'s `NCELLS_LANDED`, `box_size:75`'s "2.17× (138 619 → 300 591)") — moving the digit without moving the denominator makes the file inconsistent, and moving the denominator is a constant edit this step's negative control forbids, and (c) counts on meshes **the census never measured on 0.11** (`box_truncation`'s fixture, finding 36; `box_size`'s 300 591). So the residue is a *coupled-constant* job for whichever chunk re-prices those fixtures, not leftover prose. `git diff -- src/` empty; the seven edited modules `py_compile` clean (`20260828T214616Z_OPS-27-step3-prose-sweep-compile.log`, Status 0).* | ✅ | heavy (both steps — step 1 measured 256 s on its `mesh_cache` window, over the 180 s standard ceiling; label corrected 2026-08-28 03:00 audit) |
| `OPS-28` | **Give `tests/ports/test_port_orientation_sensitivity.py`'s `_DummyComm` the `allgather` that `OPS-14`'s rank-safety reduction calls, then read the module's real assertions back against known-issues entry 3** — census leg (b) finding 12: a correct reduction outgrew a test double, a class step 1's static sweep cannot see. The reduction stays; the deprecated placeholder route stays runnable (`PORT-1` step 4's negative control). Commissioned 2026-08-27 10:30 review; full rubric in §9 item 3. ***✅ 2026-08-28, 22:30 implementer slot** — one added `staticmethod allgather(value) -> [value]` on `_DummyComm`, nine lines including its comment, `src/` untouched (`git diff -- src/` empty). Bracketed by measurement on the identical command (`tests/ports`, `-n 2`, real, smoke, `-k 30 120`): red baseline `3 failed, 14 passed in 1.50s` / Status 1 / 3 s, gate `2 failed, 15 passed in 0.79s` / Status 1 / 2 s. The sign-flip anchor is **green** — `V(P2) = +5.000000e-02 V` aligned vs `−5.000000e-02 V` flipped, magnitudes equal to `rel=1e-12`, coupling factor `+1.0e-01 → −1.0e-01`. The S-matrix name reaches its assertion for the first time since `OPS-14` and is **red there**, so entry 3 is re-dated, not retired — with a correction it measured: on that 2-port fake the diagonal is **not** zero (`S11 = S22 = 9.047e-01 − 1.289e-02j`); the **off-diagonal** is, because the undriven port is the matched one (`V = 5.000000e-02 = Z₀I` at `Z₀ = 50 Ω` ⇒ `b = 0` exactly). Entry 3's mechanism is confirmed, its old title was imprecise for this name, and its disposition is unchanged (`PORT-0`/`PORT-1`). The leg (b) `allgather` known-issues entry retires whole. Negative control: the other three `tests/ports` modules unchanged — `sparameter_assembly` still 3 passed / 1 failed (entry 3's other name), planner 3 and `port_definition` 8 green in both runs. Logs `20260828T033037Z_OPS-28-red-baseline.log`, `20260828T033055Z_OPS-28-gate.log`.* | ✅ | smoke |
| `OPS-29` | **Rank-safe the `phantom_material` empty-tag check in `build_material_fields`** — the `OPS-13` defect survived 20 lines below its own fix; measured breaking `examples/mri/01_coil_phantom_fields.py` at `-n 12` (interactive session, 2026-08-28) | ✅ 2026-08-28 | smoke |


**`OPS-29` — rank-safe the `phantom_material` empty-tag check** ✅
*(self-commissioned by an interactive session, 2026-08-28, from a live
`examples/mri/01_coil_phantom_fields.py` failure reported by the human
operator; planned and executed in the same session at the operator's
direction.)*

> **The defect.** `core/time_harmonic.py:256` tests
> `phantom_cells.size == 0` on the **rank-local** `cell_tags.values` and
> raises `ValueError: phantom_material requested but no cells found for
> phantom_tag=3`. This is the *same* defect `OPS-13` fixed in
> `_validate_material_map_tags` — twenty lines above in the same file,
> whose docstring already spells the mechanism out (`PORT-1` step 3b-xiii,
> 601 s of wall clock burned when ranks disagreed about entering the
> solve). The `phantom_material` branch, added later, never got the
> reduction.
>
> **Measured, not inferred** (interactive session, 2026-08-28, at `15e596f`,
> the example's own mesh: `coil_phantom_domain`, `resolution=0.02`, the
> `debug`/`coarse` preset, 9 291 cells, **493 phantom cells globally**):
>
> | ranks | tag-3 cells per rank | outcome |
> |---|---|---|
> | 8 | 35, 76, 11, 61, 116, 58, 49, 87 | every rank owns phantom cells; builds clean |
> | 12 | 22, **0**, 73, 35, 71, **0**, 58, **0**, 102, 27, **0**, 105 | 4 ranks raise, 8 return normally |
>
> The tag exists globally at both widths; only the partition differs. The
> 8 surviving ranks at `-n 12` were headed into `scatter_forward` when
> MPICH tore the job down — the abort is the lucky outcome, the hang is
> the unlucky one. **The trigger is rank count against a 493-cell
> subdomain, not the mesh, the preset or the resolution**, which is why
> this reads as intermittent.
>
> **Step 1 — the fix.** Reduce before testing, matching the idiom the
> sibling already uses: sum the rank-local count over `mesh.comm` and
> raise only if the **global** count is zero. Ghost cells may be counted
> twice; irrelevant to a `> 0` test. The per-cell assignment loop below is
> already correct — a rank owning no phantom cells iterates an empty array
> — so it is not touched.
>
> **Step 2 — the gate.** Extend `tests/materials/test_material_map_rank_safety.py`
> (the `OPS-13` gate) rather than opening a new file: its fixture already
> tags **exactly one cell of the whole mesh**, so at every rank count
> above 1 there is a rank whose local phantom array is empty — the worst
> case, reproduced deterministically and at smoke cost. Three names, each
> asserted on **every** rank:
>
> 1. *positive* — a one-cell phantom tag builds on all ranks, gated by the
>    exact volume identity `∫σ dx = σ_phantom × 1/162` (Kuhn subdivision
>    of a 3³ unit cube, the closed form `OPS-13` already uses), plus the
>    ε_r counterpart. This is the §4 quantitative assertion, and it is
>    partition-independent by construction.
> 2. *negative control* — a genuinely absent phantom tag must still raise,
>    and raise on **all** ranks. A rejection that happens on only some
>    ranks is exactly as broken as an acceptance that does.
> 3. *the two pre-existing guards are untouched by the reduction* — the
>    `cell_tags is None` raise, and the "assigned in both `material_map`
>    and `phantom_material`" raise.
>
> **Step 3 — the anchor.** Re-run the example the operator hit, at
> `-n 12`, complex build, to completion. A green unit gate on a synthetic
> unit cube is not evidence about the real fixture; the 12-rank run is.
>
> **Tier: smoke** for steps 1–2 (unit cube, `-n 12`), **standard** for
> step 3. **Definition of done (§4):** the volume identity above, the
> before/after `-n 12` transition on the real example, and elapsed times
> recorded.
>
> **Non-goals.** No band, tolerance or recorded figure moves. The
> partitioner is not touched — a rank owning no phantom cells is legal and
> stays legal. `post/phantom_fields.py:81,107` were checked for the same
> pattern and are **already safe** (they return empty rather than raising,
> and hoist `create_connectivity` above the early return); no sweep chunk
> is owed.

> **Closed 2026-08-28, interactive session, at `15e596f`+.** One line of
> production code changed (`core/time_harmonic.py:266`, plus the `MPI`
> import and a nine-line comment); no band, tolerance or recorded figure
> moved.
>
> **Red baseline reproduced in-session first, through the harness, and it
> is the deadlock rather than the abort** —
> `20260828T165319Z_OPS-29-red-baseline.log`, `-n 12`: **11 of 12 ranks
> print `FAILED` at 66%** on the new positive test and the twelfth (the
> one owning the phantom cell) never returns, so the session hangs in the
> *next* test and `timeout -k 30 180` kills it. **Status 124, elapsed
> 181 s.** That is the `OPS-13` mechanism reproduced verbatim, one file
> later: ranks disagree about whether to enter the solve, and the
> agreeing ones burn the window. (`PORT-1` step 3b-xiii cost 601 s to the
> same shape.)
>
> **Green, same command, after the one-line reduction** —
> `20260828T165646Z_OPS-29-green-n12.log`: **6 passed in 0.91–0.94 s on
> all 12 ranks, Status 0, elapsed 3 s**, and
> `20260828T165703Z_OPS-29-green-n2.log` at the CI width: **6 passed in
> 0.78 s, Status 0, elapsed 2 s**. The worst case is reached and asserted,
> not hoped for — the run prints `empty_phantom_ranks=11`, i.e. eleven of
> twelve ranks own no phantom cell.
>
> **The quantitative anchor** (`[OPS-29]` line, `-n 12`):
> `int(sigma) = 4.44444444444444531e-03` against the closed form
> `σ_phantom × 1/162 = 4.44444444444444444e-03` — **1.9e-16 relative**,
> summation order only. Partition-independent by construction, and the
> `OPS-13` anchor in the same run is unmoved
> (`V_tagged = 6.17283950617284090e-03` vs closed form
> `6.17283950617283916e-03`).
>
> **The real fixture, which is what the operator actually hit** —
> `20260828T165709Z_OPS-29-example-n12.log`:
> `examples/mri/01_coil_phantom_fields.py` at **`-n 12`, complex build,
> runs to `Example completed`, Status 0, elapsed 5 s**, against the
> operator's pre-fix `ValueError` on the same command. Free bonus anchor:
> the phantom aggregates reproduce the figures recorded in
> `examples/mri/01_coil_phantom_fields.md` — |E| min/max/mean
> `1.276853e+02 / 3.043725e+02 / 1.979842e+02` **to the printed digit**,
> |B| to 6.6e-6 relative — so the fix restored the run without moving what
> the run reports. The example's standing `|E|/|B| strongly imbalanced`
> warning is pre-existing and documented in that same file (an ungated
> proxy drive, §2.2); it is not evidence about this chunk.
>
> **Recorded cost of the red baseline:** the killed 181 s run leaked its
> `/dev/shm/mpich_shm_*` segment (29 MB of 64 MB), per the known-issues
> entry filed the same day; cleared before the green run.
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

**`OPS-26` — systematic dolfinx-0.11 migration completeness sweep** ✅
*(step 1 ✅ 2026-08-25 static sweep; step 2 ✅ 2026-08-27, seven census legs
(a)–(h) across the 19:30 → 16:30 slots. **452 of 478 collected tests observed
in a footered run on 0.11 — 436 green, 16 red in three owned families, 26
deferred with substantive measured reasons, no `not reached in slot`.** The
chunk-level reconciliation is in `docs/testing/attempts.md`, entry
2026-08-27T22:20Z; the row above carries its summary.)*
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
> * **Step 1 — static sweep ✅ 2026-08-25, 15:00 implementer slot.**
>   `scripts/testing/check_dolfinx_api_migration.py` resolves every DolfinX
>   call site against the **installed** module's `inspect.signature`, in two
>   passes: a dotted pass (`fem.functionspace(...)`) and a **method pass**
>   (`obj.interpolate(...)`), the latter added because the dotted pass
>   structurally cannot see `OPS-25`'s actual defect — an instance method on a
>   `Function`. Gate module `tests/environment/test_dolfinx_api_migration.py`,
>   **3 passed / 18.60 s** at `-n 2`
>   (`20260825T201054Z_OPS-26.log`, smoke). **Result: `src/` + `tests/` are
>   clean** — **434** resolved call sites over **29** distinct APIs across
>   **159** files, `violations=0`, `uncheckable=0`, `shadowed=0`
>   (`20260825T200851Z_OPS-26.log`). **Two survivors outside the gated roots**,
>   filed not fixed: `scripts/probes/mag13_step2b_recovery.py:180` and
>   `scripts/probes/post3_step3_debug.py:55` construct `LinearProblem` without
>   0.11's required `petsc_options_prefix` (`20260825T200918Z_OPS-26.log`;
>   known-issues 2026-08-25). `examples/` is clean. The **negative control is
>   binding and passes**: six landed migrations reverted in a temp copy, each
>   matched to a finding **in the file it was reverted in**, covering all three
>   violation classes (`applied=6 baseline=0 reverted=7 status=pass`).
>   Two false-positive classes were paid and are now structural, not listed:
>   `create_cell_partitioner` is a `functools.singledispatch` whose base
>   signature is *not* the one the repo's green call matches (a call must
>   violate **every** registered overload), and the method pass's exclusions
>   are **derived** — `dir(numpy.ndarray)`, `dir(object)`, and every method
>   name any class in the swept tree defines — never hand-listed. Note for
>   step 2: `FunctionSpace` still **exists** in 0.11 as a three-argument class,
>   so the rename is an **arity** break, not a lookup one — by-eye and
>   grep-for-the-name review cannot see it.
> * **Step 1 as originally scoped — static sweep (smoke, no solves).** Sweep `src/` and `tests/`
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
> * *Queued 2026-08-26 18:00 review as §9 items 1 and 2 — the first
>   interval since commissioning that starts with an empty queue and four
>   consecutive slots. Split by directory into two one-slot legs with a
>   fail-closed disposition, so neither leg can over-claim: **leg (a)**
>   `tests/environment`, `tests/unit`, `tests/io`, `tests/mesh`,
>   `tests/materials`, `tests/post`, `tests/solver` (118 modules
>   repo-wide; these directories are the cheap majority); **leg (b)**
>   `tests/validation` and `tests/ports` (the heavy modules — the
>   straight-wire module alone is 363 s, the birdcage-port modules
>   72–198 s each, so leg (b) may itself not finish in one slot). Every
>   module not observed in a footered run by the end of a leg's slot is
>   enumerated **by name** as `deferred: not reached in slot` — that is a
>   legal disposition and the chunk stays 🟡 until the deferred list is
>   empty or every remaining name carries a *substantive* reason.
>   Whichever leg lands last writes the reconciliation.*
> * **Step 2 leg (a) — PARTIAL, 2026-08-26 19:30 implementer slot. 30 of 189
>   observed (29 green, 1 red), 159 deferred. Leg (a) is NOT complete and
>   stays queued.** Two findings, both filed in known-issues 2026-08-27.
>
>   **Denominator re-derived, not inherited** (`20260827T003050Z_OPS-26.log`,
>   real build, `--collect-only`, Status 0, 5 s): the seven leg-(a)
>   directories collect **189** tests over **54** modules —
>   `environment` 11 / `unit` 22 / `io` 8 / `mesh` 57 / `materials` 7 /
>   `post` 33 / `solver` 51. (The inherited 216/232 was a repo-wide 0.7.2
>   figure and does not apply to this root set.)
>
>   | root | collected | observed | green | red | deferred |
>   |---|---|---|---|---|---|
>   | `tests/environment` | 11 | 11 | 11 | 0 | 0 |
>   | `tests/post` | 33 | 19 | 18 | 1 | 14 |
>   | `tests/unit` | 22 | 0 | 0 | 0 | 22 |
>   | `tests/io` | 8 | 0 | 0 | 0 | 8 |
>   | `tests/mesh` | 57 | 0 | 0 | 0 | 57 |
>   | `tests/materials` | 7 | 0 | 0 | 0 | 7 |
>   | `tests/solver` | 51 | 0 | 0 | 0 | 51 |
>   | **total** | **189** | **30** | **29** | **1** | **159** |
>
>   The three totals sum to the collected count (29 + 1 + 159 = 189), as the
>   fail-closed control requires.
>
>   **Observed green by name** (complex build, `FEM_EM_REQUIRE_COMPLEX=1`,
>   `-n 2`, `20260827T003201Z_OPS-26-step2a-complex.log`):
>   `environment/test_complex_mode.py` (4), `test_dolfinx_api_migration.py`
>   (3), `test_dolfinx_version.py` (4); `post/test_csv_export_stats_parity.py`
>   (7), `test_drop_set_semantics_planar.py` (3),
>   `test_drop_set_semantics_sphere.py` (2),
>   `test_interface_guardrail_fallback.py` (5),
>   `test_phantom_field_metrics.py::test_evaluate_on_cells_fallback_skips_invalid_cell_point_pairs`
>   (1, from the isolated re-run).
>
>   **Finding 1 — a new red, and it is the class this chunk exists to catch.**
>   `post/test_phantom_field_metrics.py::test_phantom_field_metrics_and_exports_are_finite`
>   aborts in gmsh with **`Invalid boundary mesh (overlapping facets) on
>   surface 1`** — *the identical symptom string* as `GEO-21`'s birdcage
>   entry, but on the **coil+phantom** generator. `1 failed, 1 passed in
>   1.24s` (`20260827T004755Z_OPS-26-step2a-red-tb.log`). If the shared string
>   is a shared cause, the 0.11 gmsh regression is **not birdcage-specific**;
>   that is a hypothesis for a `mesh`-owning chunk, not a claim this census
>   lands. **Filed, not fixed, not re-recorded**, per the item's own rule.
>
>   **Finding 2 — the red also eats the command.** After failing at 1.24 s the
>   ranks diverge and teardown never returns: the isolated run hit `timeout -k
>   30 200` (Status 124, 201 s) *after* printing its full summary, and in the
>   batch it hung the next module (`post/test_phantom_phasor_semantics.py`,
>   never reported) until the 900 s window expired (Status 124, 901 s). **That
>   lost window is why leg (a) stopped at two of seven roots** — the census
>   command was correct, the module under it is a rank-divergence trap of the
>   `mag:1` class the item's own traps list warned about, met in `tests/post`
>   rather than in leg (b). The slot's own procedural error is separate and
>   smaller: the first census command was sized `timeout -k 30 900`, above the
>   protocol's ~590 s foreground ceiling, so it also had to be recovered from
>   the background. Next leg: size every command `timeout -k 30 540` and run
>   `tests/post` **after** the other roots, or `--deselect` this test by name.
>
>   **Finding 3 — a dead module.** `tests/mesh/test_cylindrical_domain.py`
>   collects **zero** tests: it is a module-level script (no `test_*`
>   function) that nonetheless executes a mesh build at import. It is absent
>   from the collection tree while present in the directory listing — the
>   `OPS-26` class exactly. Filed; disposition belongs to a `mesh` chunk.
>
>   **Deferred by name, all `deferred — not reached in slot` unless stated.**
>   `post`: `test_phantom_phasor_semantics.py` (3) — *`deferred — command
>   killed at 900 s while this module was executing; no per-test result`*;
>   `test_quicklook_report.py` (3); `test_tagged_cell_partition_invariance.py`
>   (8). Whole roots unreached: `unit` (3 modules / 22),
>   `io` (2 / 8), `mesh` (23 collecting modules / 57 — including the seed
>   module `test_birdcage_conductor_sizing.py`), `materials` (2 / 7),
>   `solver` (13 / 51). **Leg (a)'s built-in positive is still owed**: the seed
>   module `test_birdcage_conductor_sizing.py` (`GEO-21`) sits in the unreached
>   `mesh` root. The item's other seed clause, "any `core/cavity.py` consumer
>   under these roots" (`OPS-24`), resolves to **none** — the two cavity
>   consumers (`validation/test_cavity_resonances.py`,
>   `validation/test_resonance_guard.py`) are under `tests/validation`, i.e.
>   **leg (b)**; only `environment/test_dolfinx_api_migration.py` mentions
>   `cavity` under leg (a) and it is not a consumer. Recorded so the
>   reconciliation does not later look for a seed that was never in this leg.
> * **Step 2 leg (a), second slot — PARTIAL, 2026-08-26 21:00 implementer
>   slot. Cumulative 93 of 189 observed (91 green, 2 red), 96 deferred**
>   (was 30/189). **Leg (a)'s built-in positive is discharged**: the seed
>   module `test_birdcage_conductor_sizing.py` (`GEO-21`) is observed
>   **green** in a **Status-0** run. Leg (a) is still NOT complete and stays
>   queued. One new red, filed (known-issues 2026-08-27).
>
>   | root | collected | observed | green | red | deferred |
>   |---|---|---|---|---|---|
>   | `tests/environment` | 11 | 11 | 11 | 0 | 0 |
>   | `tests/unit` | 22 | 22 | 22 | 0 | 0 |
>   | `tests/io` | 8 | 8 | 8 | 0 | 0 |
>   | `tests/materials` | 7 | 6 | 6 | 0 | 1 |
>   | `tests/post` | 33 | 19 | 18 | 1 | 14 |
>   | `tests/mesh` | 57 | 27 | 26 | 1 | 30 |
>   | `tests/solver` | 51 | 0 | 0 | 0 | 51 |
>   | **total** | **189** | **93** | **91** | **2** | **96** |
>
>   91 + 2 + 96 = 189, as the fail-closed control requires. Denominator not
>   re-derived this slot and not inherited from outside the leg: the only
>   commit since the 19:30 derivation (`2dfc932`) is documentation-only
>   (`git diff --stat 18bb604 2dfc932` touches `docs/` alone), so **189 over
>   54 modules still holds**.
>
>   **Newly observed green by name** (real build, `-n 2`,
>   `20260827T022014Z_OPS-26-step2a-real3-cheap.log`, **Status 0, 47 s**,
>   `37 passed, 1 skipped in 46.12s` — the count is exactly seed 1 + `unit`
>   22 + `io` 8 + `materials` 7 = 38): `mesh/test_birdcage_conductor_sizing.py`
>   (1, **the seed**); `unit/test_analytical_lightweight.py` (6),
>   `test_doc_reference_exit_codes.py` (15), `test_paraview_combined_xdmf.py`
>   (1); `io/test_mesh_qa_diagnostics.py` (3), `test_touchstone_export.py`
>   (5); `materials/test_material_map_rank_safety.py` (3),
>   `test_phantom_material_model.py` (3 of 4).
>
>   And from the `tests/mesh` pass (real, `-n 2`,
>   `20260827T022114Z_OPS-26-step2a-real4-mesh.log`, Status 124 at 480 s,
>   27 of 57 reported before the kill): `test_birdcage_finalize_isolation.py`
>   (1), `test_birdcage_leg_gaps.py` (1), `test_birdcage_leg_offset.py` (6),
>   `test_birdcage_port_scaleup.py` (2),
>   `test_birdcage_port_sheet_prerequisite.py` (1),
>   `test_birdcage_port_sheets.py` (2), `test_birdcage_port_tags.py` (2 of 3),
>   `test_birdcage_port_terminals.py` (1), `test_birdcage_ring_gaps.py` (2),
>   `test_boundary_classification_margins.py` (5),
>   `test_coil_phantom_conforming.py` (2).
>
>   **Finding 4 — a new red, and the "overlapping facets" string now spans
>   three generators.**
>   `mesh/test_birdcage_port_tags.py::test_birdcage_volumes_partition_the_box`
>   aborts with **`Invalid boundary mesh (overlapping facets) on surface 59
>   surface 79`** from `birdcage_port_domain` itself
>   (`src/fem_em_solver/io/mesh.py:3245`), after a *successful* OCC fragment
>   (`volumes=26`, all four ports at 8.000000e-07 m³). Isolated:
>   `1 failed in 2.54s`, **Status 1, 4 s**
>   (`20260827T022935Z_OPS-26-step2a-mesh-red-tb.log`). With `GEO-21`'s open
>   birdcage and the 19:30 slot's coil+phantom, that is **three call paths,
>   one symptom** — a shared 0.11 gmsh cause is now the more economical
>   hypothesis than three independent sizings, but this census measures
>   nothing about the cause and does not claim one. **Not a kill artifact:**
>   the run that found it followed a Status-0 run, and the isolated re-run
>   raises a gmsh exception, not a `dolfinx/jit.py` `RuntimeError`. Filed,
>   not fixed.
>
>   **Finding 5 — `tests/solver` is fail-closed at 0/51, deliberately.** Two
>   commands attempted it and **both were killed at 540 s**
>   (`20260827T020111Z_OPS-26-step2a-real1.log`, Status 124;
>   `20260827T021051Z_OPS-26-step2a-real2-solver.log`, Status 124, run after
>   `rm -rf /root/.cache/fenics`). The first followed the 19:30 slot's two
>   killed runs, so known-issues' **"do not trust *any* failure in a run that
>   follows a killed one until the cache is cleared"** applies to it; the
>   second was itself a cold-cache run, which that same entry's sizing
>   corollary says must never share a window with measurement. The two runs
>   also **disagree with each other** — e.g.
>   `test_time_harmonic_solver_boundary_pec_is_applied_to_solve_path` is
>   SKIPPED in the first and PASSED in the second, and
>   `test_energy_matches_explicitly_reduced_assembly` is ERROR then PASSED —
>   which is the instability that entry describes, not a physics reading. Both
>   runs' ~25 ERROR/FAILED lines are therefore **discarded, not filed and not
>   counted**, and all 51 tests are `deferred — real-mode runs killed at 540 s
>   in a cold/poisoned FFCx-cache chain; results not trustworthy per
>   known-issues`. **New measurement worth keeping:** `tests/solver` does
>   **not** fit one 540 s foreground window in the **real** build on a cold
>   cache — the sizing corollary previously recorded this only for complex
>   (480 s exhausted at 61%). Next leg must clear the cache in a throwaway
>   warm-up command and measure in a *second* command.
>
>   **Finding 6 — the 19:30 slot's standing prediction is half-answered.** Of
>   the four coil+phantom consumers named as candidates to red like finding 1,
>   two are now observed **green**: `mesh/test_coil_phantom_conforming.py`
>   (2/2) and `materials/test_phantom_material_model.py` (3 green, 1 skipped).
>   `mesh/test_coil_phantom_mesh.py` and `mesh/test_mesh_tag_integrity.py`
>   remain unreached. So the coil+phantom generator is fine at *those two*
>   modules' resolutions, which is evidence for a sizing-dependent rather than
>   a blanket failure — but finding 4 arrived from a third generator in the
>   same slot, so this does not narrow to "fixture-specific".
>
>   **Deferred by name (96), one disposition each.**
>   `materials/test_phantom_material_model.py::test_phantom_material_assignment_and_time_harmonic_pipeline_wiring`
>   (1) — *`deferred — skipped at runtime in the real build`*, by name, never
>   folded into observed. `post` (14), unchanged from the 19:30 table:
>   `test_phantom_phasor_semantics.py` (3) — *`deferred — command killed at
>   900 s while this module was executing`*; `test_quicklook_report.py` (3);
>   `test_tagged_cell_partition_invariance.py` (8). `solver` (51) — the whole
>   root, reason under finding 5. `mesh` (30), all *`deferred — not reached in
>   slot`*: `test_coil_phantom_mesh.py` (3),
>   `test_domain_sizing_heuristics.py` (6), `test_geometry_sanity_report.py`
>   (2), `test_mesh_tag_integrity.py` (3), `test_region_resolution_policy.py`
>   (3), `test_two_torus_conforming.py` (2), `test_two_torus_gapped.py` (2),
>   `test_two_torus_outer_boundary.py` (2), `test_two_torus_port_facets.py`
>   (2), `test_two_torus_port_sheet.py` (3),
>   `test_wall_boundary_tag_areas.py` (2). (`test_cylindrical_domain.py`
>   collects zero tests and is outside the 189 — finding 3, already filed.)
>
>   **What leg (c) needs**, in order: (i) `tests/solver` 51, as a cache
>   warm-up command plus a measurement command, real build; (ii) the 30
>   `tests/mesh` names above, ~300 s at the observed rate; (iii) the 14 `post`
>   names in the complex build with
>   `--deselect tests/post/test_phantom_field_metrics.py::test_phantom_field_metrics_and_exports_are_finite`.
>   That is one slot if (i) behaves and two if it does not.
> * **Step 2 leg (a), third slot (leg (c)) — PARTIAL, 2026-08-26 22:30
>   implementer slot. Cumulative 137 of 189 observed (135 green, 2 red), 52
>   deferred** (was 93/189). **`tests/post` and `tests/mesh` are now complete
>   roots** — every collected test in them observed, zero deferred. Leg (a)
>   is still NOT complete: `tests/solver` remains fail-closed at 0/51 and is
>   the entire remaining gap. No new red filed; no code changed.
>
>   | root | collected | observed | green | red | deferred |
>   |---|---|---|---|---|---|
>   | `tests/environment` | 11 | 11 | 11 | 0 | 0 |
>   | `tests/unit` | 22 | 22 | 22 | 0 | 0 |
>   | `tests/io` | 8 | 8 | 8 | 0 | 0 |
>   | `tests/materials` | 7 | 6 | 6 | 0 | 1 |
>   | `tests/post` | 33 | 33 | 32 | 1 | 0 |
>   | `tests/mesh` | 57 | 57 | 56 | 1 | 0 |
>   | `tests/solver` | 51 | 0 | 0 | 0 | 51 |
>   | **total** | **189** | **137** | **135** | **2** | **52** |
>
>   135 + 2 + 52 = 189, as the fail-closed control requires. Denominator not
>   re-derived and not inherited from outside the leg: the only commits since
>   the 19:30 derivation are documentation-only, so **189 over 54 modules
>   still holds**.
>
>   **Newly observed green by name.** Real build, `-n 2`,
>   `20260827T034820Z_OPS-26-step2a-mesh-rest.log`, **Status 0, 135 s**
>   (`29 passed, 1 skipped in 133.51s`) — the whole 30-name `tests/mesh`
>   remainder: `test_coil_phantom_mesh.py` (3),
>   `test_domain_sizing_heuristics.py` (6), `test_geometry_sanity_report.py`
>   (2), `test_mesh_tag_integrity.py` (3), `test_region_resolution_policy.py`
>   (3), `test_two_torus_conforming.py` (1 of 2),
>   `test_two_torus_gapped.py` (2), `test_two_torus_outer_boundary.py` (2),
>   `test_two_torus_port_facets.py` (2), `test_two_torus_port_sheet.py` (3),
>   `test_wall_boundary_tag_areas.py` (2). Complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `-n 2`, `tests/environment` first,
>   `20260827T035101Z_OPS-26-step2a-post-complex.log`, **Status 0, 60 s**
>   (`27 passed in 58.74s`) — the 14-name `tests/post` remainder:
>   `test_phantom_phasor_semantics.py` (3), `test_quicklook_report.py` (3),
>   `test_tagged_cell_partition_invariance.py` (8), plus
>   `mesh/test_two_torus_conforming.py::test_driven_torus_field_reaches_the_air_region`
>   (the one real-build skip above — **green in complex**, so it converts to
>   observed rather than staying deferred) and `tests/environment`'s 11
>   re-observed. The hanging `post/test_phantom_field_metrics.py` needed no
>   `--deselect`: the 14 owed names are three whole modules, so it was simply
>   not listed.
>
>   **Finding 7 — the warm-up/measure design for `tests/solver` is a measured
>   negative, and the "warm cache" hypothesis is refuted.** The item's leg-(c)
>   recipe was executed exactly: a throwaway warm-up
>   (`20260827T033100Z_OPS-26-step2a-warmup.log`, real, `-n 2`, `timeout -k 30
>   500`, **Status 124 at 501 s**, stub sweep first, results discarded) then a
>   separate measurement command
>   (`20260827T033932Z_OPS-26-step2a-solver.log`, **Status 124 at 500 s**).
>   **Both died at the same 70% mark, in the same module**
>   (`test_single_port_excitation.py`) — i.e. paying a full 500 s of warm-up
>   bought the measurement run *nothing*. The known-issues sizing corollary's
>   "warm cache ⇒ `tests/solver` in 111 s complex / 41 s real" **does not
>   hold on the current tree**; whatever now costs the time is not JIT
>   compilation. All 51 stay `deferred — two real-mode runs killed at 500 s;
>   no completed footered run`.
>
>   **Finding 8 — removing the stalling module does not rescue the root, and
>   the stall is a teardown/rank divergence, not an unfinished sweep.** Third
>   command, `--ignore=tests/solver/test_single_port_excitation.py`
>   (`20260827T035220Z_OPS-26-step2a-solver-minus.log`, real, `-n 2`,
>   `timeout -k 30 480`, **Status 124 at 481 s**, 47 collected): one rank
>   reached **100%** and printed
>   `11 failed, 17 passed, 7 skipped, 12 errors in 0.85s`, while the other sat
>   at **97%** (`test_two_cylinder.py` / `test_two_torus.py`) until the kill,
>   ending in `MPI_Abort(59)` on a PETSc SIGTERM trailer. So `tests/solver`
>   holds a `mag:1`-class divergence *independent of* the single-port module.
>   **These 23 non-green names are NOT filed and NOT counted**: the summary's
>   own `0.85s` is irreconcilable with the 481 s wall clock, which is the
>   two-summary-lines artifact family, and the run has no footer of its own —
>   the fail-closed control says such a run counts every module as deferred,
>   never green and never red.
>
>   **Candidate signature worth keeping for the next leg** (a hypothesis, not
>   a census result): **21 of the 23** non-green names carry the *identical*
>   `IndexError: index 0 is out of bounds for axis 0 with size 0`, spanning
>   `test_energy_and_point_evaluation.py`, `test_gauge_lagrange.py`,
>   `test_gauge_multiplier_convergence.py`, `test_gauge_penalty.py`,
>   `test_time_harmonic_smoke.py`, `test_two_cylinder.py`, `test_two_torus.py`,
>   `test_cylinder.py` and `test_coil_phantom_magnetostatics.py` — one shared
>   cause cascading, not nine independent reds. The 22nd is
>   `test_boundary_condition_selection.py::test_time_harmonic_solver_boundary_natural_selects_empty_dirichlet_set`
>   with **`Invalid boundary mesh (overlapping facets) on surface 1 surface
>   1`** — which would make a **fourth** call path for that string if it
>   survives a trustworthy run. It has not been shown to, here.
>
>   **Deferred by name (52), one disposition each.** `tests/solver` (51) —
>   the whole root, `deferred — three real-mode commands (warm-up, measure,
>   measure-minus-stall) all killed at 480–500 s; no completed footered run,
>   results discarded per the fail-closed control`.
>   `materials/test_phantom_material_model.py::test_phantom_material_assignment_and_time_harmonic_pipeline_wiring`
>   (1) — `deferred — skipped at runtime in the real build` (unchanged; it
>   was not re-attempted in complex this slot).
>
>   **Slot cost:** five commands, 1 677 s of recorded elapsed (501 + 500 +
>   135 + 60 + 481); **1 001 s of it bought nothing** — the two solver
>   commands the item's own recipe prescribed.
>
>   **What leg (d) needs.** The cheap roots are done; only `tests/solver`
>   remains, and three consecutive whole-root commands have now failed the
>   same way, so **stop running the root as one command**. Run it
>   **module-by-module**, one command per module at `timeout -k 30 240`, in
>   ascending module size, so every module gets its own footer and one
>   diverging module costs one module rather than the root: that converts a
>   guaranteed 0/51 into at worst a partial with named survivors. Take
>   `test_boundary_condition_selection.py` first (it is the one carrying the
>   distinct symptom) and `test_single_port_excitation.py` /
>   `test_two_cylinder.py` / `test_two_torus.py` last. Budget ~8 modules per
>   slot; 13 modules is likely two slots. Only after a module has a
>   Status-0-or-Status-1 footer of its own may its reds be filed.
> * **Step 2 leg (a), fourth slot (leg (d)) — leg (a) SUBSTANTIVELY COMPLETE,
>   2026-08-27 00:00 implementer slot. Cumulative 184 of 189 observed (182
>   green, 2 red), 5 deferred** (was 137/189). **`tests/solver` went 0/51 →
>   47/51 green** — the root that three whole-root commands had failed to
>   observe at all. Six of the seven leg-(a) roots are now complete; the
>   remaining 5 deferred names carry substantive, non-`not reached in slot`
>   reasons. No code changed. One known-issues entry added (a *mechanism*
>   finding, explicitly not a counted red).
>
>   | root | collected | observed | green | red | deferred |
>   |---|---|---|---|---|---|
>   | `tests/environment` | 11 | 11 | 11 | 0 | 0 |
>   | `tests/unit` | 22 | 22 | 22 | 0 | 0 |
>   | `tests/io` | 8 | 8 | 8 | 0 | 0 |
>   | `tests/materials` | 7 | 6 | 6 | 0 | 1 |
>   | `tests/post` | 33 | 33 | 32 | 1 | 0 |
>   | `tests/mesh` | 57 | 57 | 56 | 1 | 0 |
>   | `tests/solver` | 51 | 47 | 47 | 0 | 4 |
>   | **total** | **189** | **184** | **182** | **2** | **5** |
>
>   182 + 2 + 5 = 189, as the fail-closed control requires. **Denominator
>   re-derived for this root, not inherited** (`20260827T050052Z_OPS-26-step2a-legd-collect.log`,
>   real, `--collect-only -q`, **Status 0, 4 s**): `tests/solver` collects
>   **51 tests over 13 modules** — `test_boundary_condition_selection.py` 4,
>   `test_coil_phantom_magnetostatics.py` 1, `test_convergence_diagnostics.py`
>   14, `test_cylinder.py` 1, `test_energy_and_point_evaluation.py` 6,
>   `test_gauge_lagrange.py` 4, `test_gauge_multiplier_convergence.py` 2,
>   `test_gauge_penalty.py` 4, `test_single_port_excitation.py` 4,
>   `test_time_harmonic_smoke.py` 8, `test_tolerance_policy.py` 1,
>   `test_two_cylinder.py` 1, `test_two_torus.py` 1. That matches the 51 the
>   19:30 slot derived for this root, so the 189/54 total is unchanged.
>
>   **Finding 9 — the module-per-command design is the fix, and it is not
>   marginal.** Three consecutive slots had run `tests/solver` as one command
>   and observed **zero** of 51. Run as **one command per module** at
>   `timeout -k 30 120…240`, `-n 2`, real build, **twelve of the thirteen
>   modules returned a Status-0 footer** and the whole root cost **~220 s of
>   compute**, against the 1 001 s that bought nothing in leg (c). The
>   divergence was never a property of the root; it was one module, and
>   batching let it eat every other module's result.
>
>   **Newly observed green by name (real build, `-n 2`, one command each).**
>   `test_tolerance_policy.py` (1) — Status 0, 1 s
>   (`20260827T050605Z_..._m02-tolpolicy.log`);
>   `test_convergence_diagnostics.py` (13 of 14) — Status 0, 2 s
>   (`…050612Z_..._m03-convdiag.log`, `13 passed, 1 skipped`);
>   `test_gauge_penalty.py` (4) — Status 0, 14 s (`…050623Z_..._m04-gaugepen.log`);
>   `test_gauge_multiplier_convergence.py` (2) — Status 0, **129 s**
>   (`…050643Z_..._m05-gaugemult.log`, the root's dominant single cost);
>   `test_gauge_lagrange.py` (4) — Status 0, 6 s (`…050902Z_..._m06-gaugelag.log`);
>   `test_cylinder.py` (1) — Status 0, 36 s (`…050913Z_..._m07-cylinder.log`);
>   `test_coil_phantom_magnetostatics.py` (1) — Status 0, 7 s
>   (`…050955Z_..._m08-coilphantom.log`);
>   `test_energy_and_point_evaluation.py` (6) — Status 0, 6 s
>   (`…051007Z_..._m09-energy.log`);
>   `test_time_harmonic_smoke.py` (3 of 8) — Status 0, 3 s
>   (`…051024Z_..._m10-thsmoke.log`, `3 passed, 5 skipped`);
>   `test_two_cylinder.py` (1) — Status 0, 3 s (`…051038Z_..._m11-twocyl.log`);
>   `test_two_torus.py` (1) — Status 0, 2 s (`…051046Z_..._m12-twotorus.log`);
>   `test_single_port_excitation.py` (4) — Status 0, 1 s
>   (`…051054Z_..._m13-singleport.log`).
>   Then the six real-build complex-only skips, **all green in complex** and
>   therefore converted to observed rather than deferred: complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `-n 2`, `tests/environment` first,
>   `20260827T051113Z_OPS-26-step2a-legd-complex-skips.log`, **Status 0, 34 s**
>   (`33 passed` = `environment` 11 + `convergence_diagnostics` **14** +
>   `time_harmonic_smoke` **8**, i.e. zero skipped in complex) —
>   `test_convergence_diagnostics.py::test_time_harmonic_solver_emits_optional_solve_health_diagnostics`
>   (1) and the five `test_time_harmonic_smoke.py` names.
>
>   **Finding 10 — leg (c)'s 23 discarded names were correctly discarded, and
>   the discard is now *positively* confirmed rather than merely prudent.** Of
>   the nine modules that carried the shared
>   `IndexError: index 0 is out of bounds for axis 0 with size 0` in the
>   footerless leg-(c) run, **eight are green here in footered runs**
>   (`test_energy_and_point_evaluation.py`, `test_gauge_lagrange.py`,
>   `test_gauge_multiplier_convergence.py`, `test_gauge_penalty.py`,
>   `test_time_harmonic_smoke.py`, `test_two_cylinder.py`, `test_two_torus.py`,
>   `test_cylinder.py`, `test_coil_phantom_magnetostatics.py`). The
>   fail-closed control paid for itself: filing those 21 names would have put
>   21 false reds in known-issues.
>
>   **Finding 11 — the one surviving module, and the "overlapping facets"
>   string is rank-dependent.** `test_boundary_condition_selection.py` (4)
>   deadlocked in **both** builds — real `timeout -k 30 240` **Status 124 at
>   241 s** (`20260827T050123Z_..._m01-bcsel.log`), complex `timeout -k 30
>   180` **Status 124 at 180 s** (`20260827T051201Z_..._m01-bcsel-complex.log`).
>   The complex log shows the *same test* PASSED on one rank at `[ 46%]` and
>   FAILED on the other at `[ 93%]` with
>   `Invalid boundary mesh (overlapping facets) on surface 1 surface 1`, then
>   `MPI_Abort(59)` on the kill — so one rank raising inside gmsh while the
>   other proceeds **is** the hang mechanism, and on this call path the
>   overlapping-facets trigger is partition-dependent, not a property of the
>   geometry alone. That cuts against the resolution-floor reading the three
>   prior entries for that string share. The module's second failure is
>   `IndexError: index 0 is out of bounds for axis 0 with size 0` — leg (c)'s
>   candidate signature, on a swept cache in an isolated module. **Filed as a
>   mechanism finding, explicitly NOT as a counted red** (known-issues
>   2026-08-27, fourth slot): neither run has a footer, and the control admits
>   reds only from footered runs. The one command that would settle it — this
>   module at `-n 1` — was deliberately **not** spent: `-n 1` is not the
>   census's recorded width, so an observation at it would not count. It is
>   named in the known-issues entry as the next owner's first move.
>
>   **Cache state exonerated for this whole slot.** First command swept
>   `find /root/.cache/fenics -name '*.c' -size 0 -print -delete` and it
>   printed nothing (`…050052Z_..._legd-collect.log:34`), and no command in the
>   slot ran on the heels of a kill except the two `bcsel` retries themselves.
>
>   **Deferred by name (5), one disposition each — no `not reached in slot`
>   remains in leg (a).** `tests/solver/test_boundary_condition_selection.py`
>   (4: `test_normalize_boundary_condition_accepts_enum_and_string_values`,
>   `test_normalize_boundary_condition_rejects_unknown_value`,
>   `test_time_harmonic_solver_boundary_natural_selects_empty_dirichlet_set`,
>   `test_time_harmonic_solver_boundary_pec_is_applied_to_solve_path`) —
>   `deferred — module-scoped commands deadlocked at -n 2 in both builds
>   (Status 124 × 2); no Status-0/1 footer, so no name may be scored green or
>   red; mechanism filed in known-issues`.
>   `materials/test_phantom_material_model.py::test_phantom_material_assignment_and_time_harmonic_pipeline_wiring`
>   (1) — `deferred — skipped at runtime in the real build`; **unchanged and
>   now the cheapest open name in leg (a)** — it was never re-attempted in
>   complex, and this slot's complex command shows that route converts such
>   skips (it converted six). One ~30 s complex command should close it.
>
>   **Slot cost:** fifteen commands, **~660 s** of recorded elapsed, of which
>   421 s went to the two `bcsel` deadlocks — i.e. 239 s bought 47 of the 51
>   names.
>
>   **What remains for leg (a):** the 1 `materials` name in complex, and a
>   decision on `test_boundary_condition_selection.py` that is a `solver`/`mesh`
>   chunk's to make, not the census's. Leg (a) is otherwise complete. The
>   chunk stays 🟡 until **leg (b)** (`tests/validation` + `tests/ports`, §9
>   item 2) lands and its owner writes the chunk-level reconciliation.
>   **Leg (b) should adopt the module-per-command shape from the start** —
>   finding 9 is the strongest methodological result this chunk has produced,
>   and leg (b)'s roots hold the modules most likely to diverge.
> * **Step 2 leg (b) — PARTIAL, 2026-08-27 04:30 implementer slot. 22 of 289
>   observed (19 green, 3 red), 267 deferred. `tests/ports` is COMPLETE at
>   17/17; `tests/validation` is 5 of 272. Leg (b) stays queued.** Three
>   findings, two known-issues entries filed 2026-08-27.
>
>   **Denominator re-derived, not inherited** (`20260827T093400Z_OPS-26-step2b-collect.log`,
>   real build, `--collect-only -q`, **Status 0, 3 s**): the two leg-(b)
>   roots collect **289** tests over **63** modules — `tests/validation`
>   **272 / 59**, `tests/ports` **17 / 4**. The `OPS-17`-era 232 the item
>   expected to have moved has indeed moved, and in the opposite direction
>   from a naive reading: 232 was a *repo-wide* 0.7.2 figure, whereas 272 is
>   `tests/validation` alone. **Arithmetic caution for the next leg:** with
>   `--collect-only` and no `-q` taking effect (this repo's `pyproject.toml`
>   `addopts` forces `-v`), pytest prints a **tree**, and the tree carries
>   three `<Class …>` nodes (`TestCircularLoop`, `TestConvergence`,
>   `TestStraightWire`) that a line-delta count reads as tests. Counting
>   `<Function` only — or reconciling against the printed
>   `289 tests collected` — is the check; a raw delta count gives 275/59 for
>   `tests/validation`, three too many.
>
>   | root | collected | observed | green | red | deferred |
>   |---|---|---|---|---|---|
>   | `tests/ports` | 17 | 17 | 14 | 3 | 0 |
>   | `tests/validation` | 272 | 5 | 5 | 0 | 267 |
>   | **total** | **289** | **22** | **19** | **3** | **267** |
>
>   19 + 3 + 267 = 289, as the fail-closed control requires.
>
>   **Observed green by name, one command per module, real build, `-n 2`.**
>   `ports/test_frequency_sweep_planner.py` (3) — Status 0, 1 s
>   (`…093737Z_..._p01-freqsweep.log`);
>   `ports/test_port_definition.py` (8) — Status 0, 2 s
>   (`…093742Z_..._p02-portdef.log`);
>   `ports/test_sparameter_assembly.py` (3 of 4) — Status 1, 2 s
>   (`…093752Z_..._p04-sparam.log`);
>   `validation/test_convergence.py` (1) — Status 0, **143 s**
>   (`…093506Z_..._v01-convergence.log`, `1 passed in 141.51s`);
>   `validation/test_tolerance_policy.py` (1) — Status 0, 1 s
>   (`…093823Z_..._v02-tolpolicy.log`);
>   `validation/test_field_consistency_metrics.py` (2) — Status 0, 2 s
>   (`…093827Z_..._v03-fieldconsist.log`);
>   `validation/test_helmholtz_magnitude.py` (1) — Status 0, 13 s
>   (`…093832Z_..._v04-geomfloor.log`).
>
>   **Seed-list result, and one seed name is stale.** `test_convergence.py`
>   is **green**, confirming `MAG-19` step 2's disposition executes on `main`
>   at the retired band — the seed the item cared most about. The item's
>   second named seed, **`test_two_torus_port_sheet.py`, does not exist in
>   either leg-(b) root**; the `GEO-16` fixture the ruling meant is
>   `tests/validation/test_port_lumped_two_torus.py` (5 tests), still
>   unobserved. The next leg should use that name.
>
>   **Finding 12 — a new defect class, and step 1 structurally could not see
>   it.** `ports/test_port_orientation_sensitivity.py` (2 of 2) is red with
>   `AttributeError: '_DummyComm' object has no attribute 'allgather'`
>   (Status 1, 2 s, `…093747Z_..._p03-orient.log`). Cause diagnosed in one
>   line: `OPS-14` added a rank-safety reduction at
>   `src/fem_em_solver/ports/excitation.py:265` —
>   `problem.mesh.comm.allgather(...)` — and the module's stub comm
>   (`test_port_orientation_sensitivity.py:16-21`) defines `rank` and
>   `allreduce` and nothing else. **This is not a 0.11 migration break and
>   not a gmsh regression**: it is test-double drift behind a *correct*
>   rank-safety fix, and `check_dolfinx_api_migration.py` cannot see it by
>   construction, since `comm.allgather` is a valid mpi4py API and
>   `_DummyComm` is not a DolfinX type. The reduction must not be reverted;
>   the double is what is stale. Recorded verbatim because the irony is the
>   finding: `excitation.py`'s own comment says the reduction was "fixed here
>   so the deprecated route stays *runnable*", and it is what stopped the
>   route running — undetected because nothing scheduled runs `tests/ports`.
>   **Step 1 swept and step 2 caught it; that is the argument for step 2's
>   existence, made by measurement.**
>
>   **Finding 13 — two of the three reds were already filed, one was not, and
>   one filed symptom has silently changed.** Known-issues entry 3 ("Port
>   tests assert a non-zero S-matrix diagonal on a matched port") lists both
>   `test_sparameter_assembly.py::test_n_port_sweep_assembles_finite_matrix_with_expected_shape`
>   (still red for exactly the filed reason — `array([0.+0.j, 0.+0.j,
>   0.+0.j])`, a legitimately matched port) and
>   `test_port_orientation_sensitivity.py::test_port_orientation_flip_changes_off_diagonal_sparameter_sign`
>   — but the latter **no longer fails for that reason**: it dies in the tag
>   reduction and never reaches its S-matrix assertion, so entry 3's
>   diagnosis is now *unreachable* on it rather than refuted.
>   `…::test_port_orientation_flip_changes_induced_voltage_sign` was in no
>   entry at all and is a genuinely new red. All three counted; new entry
>   filed 2026-08-27, entry 3 left standing and cross-referenced. **Note for
>   the reconciliation:** a census that scored "already in known-issues" as
>   not-a-red would have missed both the new name and the changed symptom.
>
>   **Finding 14 — the owed `materials` conversion failed, and it is a fifth
>   `GEO-23` site.** The item's "first thing, ~30 s" command
>   (`20260827T093043Z_OPS-26-step2b-materials-complex.log`, complex,
>   `FEM_EM_REQUIRE_COMPLEX=1`, `-n 2`, `timeout -k 30 180`) ran
>   `tests/materials/test_phantom_material_model.py` and did **not** convert
>   the runtime skip to green: the test resolves **differently on the two
>   ranks** — `PASSED [ 66%]` on one, `FAILED [100%]` on the other with
>   `Invalid boundary mesh (overlapping facets) on surface 1 surface 1` —
>   then teardown ate the window (**Status 124, 181 s**, after the summary
>   `1 failed, 14 passed in 20.79s` had printed). Per leg (a) finding 11's
>   ruling this is **not** a counted red (no Status-0/1 footer); the leg (a)
>   name stays deferred with its **reason upgraded** from `skipped at runtime
>   in the real build` to `rank-divergent gmsh abort, no footer`. **Leg (a)'s
>   totals are unchanged at 184 / 189 (182 + 2 + 5).** For `GEO-23` this is a
>   *fifth* call site carrying that string and the **second** demonstrably
>   partition-dependent one — two independent rank-dependent sites is
>   materially stronger evidence against the shared resolution-floor reading
>   than leg (a)'s single site was, and this module belongs in `GEO-23` step
>   1's rank-width table.
>
>   **Method deviation, declared.** The last command of the slot batched
>   **two** modules (`test_geometry_floor_discriminator.py` +
>   `test_helmholtz_magnitude.py`) rather than one, against the item's
>   module-per-command rule, to fit the timebox. It returned Status 0 so no
>   observation was lost, but the shortcut is recorded rather than hidden:
>   had either diverged, both would have been `deferred — no footer`. Do not
>   repeat it in leg (c).
>
>   **Deferred by name with a substantive reason (1).**
>   `validation/test_geometry_floor_discriminator.py::test_larmor_sphere_residual_at_the_priced_fine_mesh`
>   (1) — `deferred — complex-only, SKIPPED in the real build (log line 48,
>   "source /usr/local/bin/dolfinx-complex-mode")`. Leg (d)'s pattern
>   converts these; one complex command owes it, and finding 14 is the
>   warning that such a conversion can land on a red rather than a green.
>   The remaining **266** are `deferred — not reached in slot`, which the
>   item declares a legal, non-failing disposition.
>
>   **Slot cost:** eight commands, **~350 s** of recorded elapsed, of which
>   **181 s** went to the one rank-divergent teardown and **143 s** to
>   `test_convergence.py` — i.e. 26 s bought the other 21 names. The cheap
>   tail of these roots is very cheap; the cost is concentrated in a handful
>   of modules the item already priced.
>
>   **What remains for leg (c)** (~267 names over ~55 modules, all in
>   `tests/validation`): the priced heavies (`test_straight_wire.py` 7 at
>   ~363 s, the `PORT-11` pair, the three birdcage `PORT-9` modules, the
>   `coil_loading_*` family at 14 + 14 + 7 + 6 + 6 + 6 + 5), the corrected
>   `GEO-16` seed name `test_port_lumped_two_torus.py`, the one complex-only
>   skip above, and the large cheap tail. Ascending recorded cost still
>   applies, and `test_port_gap_voltage_impedance.py` (**20** tests, the
>   root's largest module) is the best names-per-second target after the
>   singletons.
> * **Step 2 leg (b) — PARTIAL (second slot), 2026-08-27 06:00 implementer
>   slot. 139 of 289 observed (136 green, 3 red), 150 deferred.
>   `tests/validation` 5 → 122 of 272, all 117 of this slot's names green,
>   zero reds, zero exit-124 windows.** Twenty-seven commands, one module
>   each, `-n 2` throughout, **2 028 s** of recorded elapsed. No code changed
>   anywhere; `main` clean at handoff.
>
>   | root | collected | observed | green | red | deferred |
>   |---|---|---|---|---|---|
>   | `tests/ports` | 17 | 17 | 14 | 3 | 0 |
>   | `tests/validation` | 272 | 122 | 122 | 0 | 150 |
>   | **total** | **289** | **139** | **136** | **3** | **150** |
>
>   136 + 3 + 150 = 289, as the fail-closed control requires.
>
>   **Finding 15 — the build, not the module order, is this root's dominant
>   census variable, and the previous slot's shape was costing it every
>   name.** `grep -L complex tests/validation/test_*.py` returns **6 of 59**
>   modules: `test_cavity_resonances.py`,
>   `test_coil_phantom_bfield_metrics.py`,
>   `test_mutual_inductance_reference.py`,
>   `test_field_consistency_metrics.py`, `test_convergence.py`,
>   `test_tolerance_policy.py`. **53 of 59 `tests/validation` modules are
>   complex-gated**, so a real-build command over them scores runtime skips
>   — `deferred — <skip reason>`, never green — which is exactly what
>   attempt 1's real-build shape would have produced for the whole root, and
>   is the structural reason it banked only 5 names. This slot ran the
>   complex build (`source /usr/local/bin/dolfinx-complex-mode`,
>   `FEM_EM_REQUIRE_COMPLEX=1`) for the 53 and the real build for the other
>   6, and converted **117 names in one slot against attempt 1's 5**. Cost of
>   the check: one `grep -L`, zero compute. **Rule for leg (c): read the
>   module's build gate before sizing its command; in `tests/validation` the
>   complex build is the default and the real build the exception.**
>   Corollary, now measured: **all 6 real-build modules are observed and
>   green**, so the entire 150-name remainder is complex-build work.
>
>   **Observed green by name, one command per module (no batching — the
>   previous slot's declared deviation was not repeated), `-n 2`, Status 0
>   and identical rank footers on all twenty-seven.** Complex build:
>   `test_port_lumped_bc.py` (6) **6 s** (`…110129Z_…v05-lumpedbc.log`,
>   `6 passed in 4.05s` — the slot's deliberate JIT warm-up, and it cost 4 s,
>   not the priced 2.4–3×);
>   `test_current_divergence.py` (3) **7 s** (`…v06-currentdiv`);
>   `test_mass_averaged_sar.py` (2) **22 s** (`…v07-massavgsar`);
>   `test_mass_averaged_sar_standard_masses.py` (3) **16 s** (`…v08-massavgstd`);
>   `test_resonance_guard.py` (2) **33 s** (`…v09-resguard`);
>   `test_port_gap_voltage_impedance.py` (**20**) **483 s**
>   (`…110320Z_…v10-gapvolt.log`, `20 passed in 481.47s`);
>   `test_poynting_balance.py` (11) **133 s** (`…v11-poynting`);
>   `test_port_reaction_impedance.py` (9) **174 s** (`…v12-reactionz`);
>   `test_port_package_sparameters.py` (6) **163 s** (`…v15-pkgsparam`);
>   `test_port_solenoidal_drive.py` (5) **42 s** (`…v16-solenoidal`);
>   `test_port_self_impedance_energy.py` (3) **40 s** (`…v17-selfimped`);
>   `test_port_lumped_two_torus.py` (5) **92 s** (`…v18-twotorus`);
>   `test_port_lumped_sheet_sweep.py` (3) **111 s** (`…v19-sheetsweep`);
>   `test_port_gradient_load.py` (3) **39 s** (`…v20-gradload`);
>   `test_port_lumped_narrowed_sheet.py` (4) **150 s** (`…v21-narrowed`);
>   `test_degree2_energy_mechanism.py` (4) **21 s** (`…v22-deg2mech`);
>   `test_lossy_sphere_degree2.py` (2) **9 s** (`…v23-lsdeg2`);
>   `test_lossy_sphere_fullwave.py` (3) **23 s** (`…v24-lsfullwave`);
>   `test_lossy_sphere_sar.py` (1) **34 s** (`…v25-lssar`);
>   `test_dielectric_sphere.py` (2) **15 s** (`…v26-dielsphere`);
>   `test_lossy_plane_wave.py` (2) **21 s** (`…v27-planewave`);
>   `test_time_harmonic_mms.py` (2) **7 s** (`…v28-thmms`);
>   `test_waveguide_cutoff.py` (2) **14 s** (`…v29-waveguide`);
>   `test_circular_loop.py` (3) **350 s** (`…113324Z_…v30-circloop.log`).
>   Real build: `test_mutual_inductance_reference.py` (7) **3 s**
>   (`…v13-mutualind`, `7 passed in 0.94s`);
>   `test_cavity_resonances.py` (3) **7 s** (`…v14-cavity`);
>   `test_coil_phantom_bfield_metrics.py` (1) **13 s** (`…v31-coilphantom`).
>
>   **Seed-list note.** The corrected `GEO-16` seed name from attempt 1,
>   `test_port_lumped_two_torus.py`, is **green** (5 passed, 92 s) — three
>   of the item's four named seeds are now observed green, and the fourth
>   (the `PORT-11` pair) is in leg (c)'s birdcage block.
>
>   **Finding 16 — the cost is concentrated in a few modules, not spread,
>   and the item's own "largest module first" heuristic paid.** Two modules
>   are **833 s of the slot's 2 028 s (41%) for 23 of the 117 names (20%)** —
>   gap-voltage 483 s and circular-loop 350 s; the other 25 commands bought
>   94 names for 1 195 s, and the twelve cheapest bought 33 names for 214 s.
>   The 20-test module was nevertheless the right early draw: at 24 s/name it
>   is still cheaper per name than `test_convergence.py` (143 s for 1) and
>   far cheaper than the unpriced `test_straight_wire.py` (~363 s for 7).
>   **Pricing banked for leg (c)**, previously unrecorded on 0.11:
>   gap-voltage 483, circular-loop 350, reaction-Z 174, package-S 163,
>   narrowed-sheet 150, Poynting 133, sheet-sweep 111, two-torus 92,
>   solenoidal 42, self-impedance 40, gradient-load 39, lossy-sphere-SAR 34,
>   resonance-guard 33 s — size from these, not from the `OPS-17`-era 0.7.2
>   records.
>
>   **Finding 17 — `test_circular_loop.py`, the `OPS-19`/`OPS-22` JIT
>   casualty, is green on 0.11.** `OPS-17` (b2) attempts 1–2 were each
>   stopped by this file ("cannot JIT-compile one form in the complex
>   build", traced to fixture-side `ufl.max_value`/comparison predicates on
>   complex operands, commissioned as `OPS-22`). It is now `3 passed in
>   348.74s`, Status 0, complex, `-n 2` — **`OPS-22`'s fixture fix holds on
>   the 0.11 image**; the file is expensive, not broken. Recorded because two
>   prior legs lost windows to this name.
>
>   **Negative-result column: empty, and that is itself the observation.**
>   Zero reds, zero no-footer deferrals, zero exit-124 windows across
>   twenty-seven commands including two windows over 340 s — against leg
>   (a)'s three gmsh aborts and a deadlocking module, and attempt 1's three
>   `tests/ports` reds. `test_coil_phantom_bfield_metrics.py`, drawn
>   deliberately because leg (a)'s coil+phantom gmsh abort made it the
>   slot's best red candidate, is `1 passed in 11.34s`. The 0.11 migration
>   damage found so far is **not** distributed across `tests/validation`'s
>   solved-field suites; it sits in the mesh-generating and test-double
>   paths (`GEO-23`, finding 12).
>
>   **Deferred (150).** One with a substantive reason, carried unchanged
>   from attempt 1:
>   `validation/test_geometry_floor_discriminator.py::test_larmor_sphere_residual_at_the_priced_fine_mesh`
>   — `deferred — complex-only, SKIPPED in the real build`; finding 15 says
>   the conversion command is a complex one and should be cheap. The other
>   **149** are `deferred — not reached in slot`.
>
>   **What remains for leg (c)** (150 names over 28 modules, all
>   `tests/validation`, all complex-build): the `coil_loading_*` family
>   (58, priced in `OPS-17` (b2), needing its recorded rank widths and
>   `TH11_STEP5_RUNG=fine`; `coil_loading_degree2`'s 14 are the `TH-12`
>   memory-wall defer-with-reason), the `dodd_deeds_*` family (38), the
>   `PORT-9`/`PORT-11` birdcage block (32 at 72–201 s each),
>   `test_straight_wire.py` (7 at ~363 s, also `MAG-20`'s anchor module), a
>   13-name cheap remainder (`sheet_asymmetric` 5, `box_padding_sweep` 3,
>   `systematics_composition` 3 at its recorded 360 s,
>   `gap_voltage_padding` 2 — an `OPS-17` (b2) formal deferral to re-price
>   rather than inherit — and `helmholtz_v2` 1, which **hung** in `OPS-17`
>   (b2) attempt 2 and needs its own bounded window), plus the one
>   complex-only skip. Ascending recorded cost still applies; the build-gate
>   check of finding 15 now applies first.
> * **Step 2 leg (c) — PARTIAL, 2026-08-27 07:30 implementer slot. 188 of 289
>   observed (184 green, 4 red), 101 deferred. `tests/validation` 122 → 171
>   of 272; the birdcage `PORT-9`/`PORT-11` block complete at 32/32 green.**
>   Fourteen commands, one module each, `-n 2` throughout, every one with
>   `timeout -k 30`, **1 874 s** of recorded elapsed. No code changed
>   anywhere; `main` clean at handoff.
>
>   | root | collected | observed | green | red | deferred |
>   |---|---|---|---|---|---|
>   | `tests/ports` | 17 | 17 | 14 | 3 | 0 |
>   | `tests/validation` | 272 | 171 | 170 | 1 | 101 |
>   | **total** | **289** | **188** | **184** | **4** | **101** |
>
>   184 + 4 + 101 = 289, as the fail-closed control requires.
>
>   **Observed this slot by name (49 names: 48 green, 1 red).** Complex build
>   unless marked **real**:
>   `test_port_lumped_sheet_asymmetric.py` (5) — Status 0, 206 s
>   (`…123130Z_…v32-sheetasym.log`; this command also carried
>   `tests/environment` as §9's mandated env guard, `16 passed` = 11 env + 5,
>   and paid the slot's cold-JIT premium);
>   `test_port_birdcage_lumped_column.py` (2) — Status 0, 40 s
>   (`…123529Z_…v33-bc-lumpedcol.log`);
>   `test_port_birdcage_larmor_probe.py` (3) — Status 0, 43 s
>   (`…123616Z_…v34-bc-larmorprobe.log`);
>   `test_port_birdcage_termination_probe.py` (4) — Status 0, 41 s
>   (`…123704Z_…v35-bc-termprobe.log`);
>   `test_port_birdcage_four_port.py` (5) — Status 0, 57 s
>   (`…123748Z_…v36-bc-fourport.log`);
>   `test_port_birdcage_leg_offset_sweep.py` (5) — Status 0, 106 s
>   (`…123849Z_…v37-bc-legoffset.log`);
>   `test_port_birdcage_larmor_gate.py` (6) — Status 0, 152 s
>   (`…124039Z_…v38-bc-larmorgate.log`);
>   `test_port_birdcage_larmor_gate_128.py` (7) — Status 0, 154 s
>   (`…124317Z_…v39-bc-larmorgate128.log`);
>   `test_straight_wire.py` (7) — Status 0, **314 s**, **real**
>   (`…124937Z_…v41-straightwire-real.log`, `7 passed in 312.60s`);
>   `test_helmholtz_v2.py` (1) — Status 0, 3 s, **real**
>   (`…125543Z_…v43-helmholtzv2.log`);
>   `test_port_box_padding_sweep.py` (3) — Status 0, 142 s
>   (`…125551Z_…v44-boxpadding.log`);
>   `test_geometry_floor_discriminator.py` (1) — Status 1, 23 s, **RED**
>   (`…125507Z_…v42-geomfloor.log`), known-issues 2026-08-27.
>
>   **Finding 18 — leg (b)'s build classifier is unsound, and its failure
>   mode is the one thing the fail-closed control cannot see.** Finding 15
>   classified `tests/validation` modules with `grep -L complex`.
>   `test_straight_wire.py` — a *magnetostatics* module — contains the word
>   "complex" only in a **comment** (line 94, about avoiding complex
>   comparisons), so the classifier scored it complex-gated. Run in the
>   complex build it produced `3 failed, 4 passed in 190.42s`, **Status 1**,
>   192 s (`…124600Z_…v40-straightwire.log`), every failure
>   `TypeError: '>' not supported between instances of 'complex' and 'float'`
>   at `test_straight_wire.py:231` (`assert den > 0.0` on a complex
>   `assemble_scalar`). **That is a fully footered, rank-identical Status-1
>   red produced entirely by the census's own build choice** — the fail-closed
>   control bounds *missing* observations, not *fabricated* ones, so a
>   misclassified build would have been silently recorded as a module defect.
>   Re-run in the real build: **7 passed, Status 0, 314 s.** Cost of the
>   error: one 192 s window. **Rule for leg (d), replacing finding 15's:**
>   classify by the *gate*, not the word —
>   `grep -l "complex_mode\|requires_complex\|is_complex\|skipif"` — which on
>   this slot's five candidate modules correctly separated the three
>   complex-gated ones from `test_helmholtz_v2.py` and (had it been asked)
>   `test_straight_wire.py`. Finding 15's 117-name result stands; its
>   *method* does not. Also worth the reconciliation's attention: the 0.11
>   price of `test_straight_wire.py` is **314 s**, so the inherited ~363 s is
>   a ceiling — and the module is **green on `main` at `58c77d9`**, which is
>   the anchor `MAG-20` (§9 item 2) needs.
>
>   **Finding 19 — the owed complex conversion lands on a red, and the red is
>   a stale record (filed).**
>   `test_geometry_floor_discriminator.py::test_larmor_sphere_residual_at_the_priced_fine_mesh`,
>   carried by leg (b) as `deferred — complex-only`, is now **observed and
>   red**: it asserts the 128 MHz relL2 against the recorded **1.8260%** and
>   measures **1.7686%** (3.14% > its 1% band). 1.769% is **`OPS-18`'s**
>   re-recorded 0.11 value, already in §2 and CLAUDE.md; 1.826% is the 0.7.2
>   figure from `TH-10` closure. So the file holds the pre-`OPS-18` constant
>   and its own message ("a regression in the fixture or this file, not a
>   geometry finding") names the right disposition. **This is not evidence
>   against `TH-10`** — the solve reproduces `OPS-18`. Filed, not fixed
>   (a census lands no fix); the one-constant re-record with the `OPS-18`
>   mesh cited in-comment is a chunk for a review to commission.
>
>   **Finding 20 — the `OPS-17` (b2) hang was a finding-18 artifact.**
>   `test_helmholtz_v2.py`, which hung in `OPS-17` (b2) attempt 2 and was
>   queued here for "its own bounded window and a possible no-footer", is
>   `1 passed in 1.24s`, Status 0, in the **real** build. Two of this
>   census's inherited horror stories (this and finding 17's
>   `test_circular_loop.py`) have now resolved to "runs fine, in the right
>   build" — which is itself an argument for the census.
>
>   **Finding 21 — a deferral re-priced rather than inherited, and it stayed
>   deferred on measurement.** `test_port_gap_voltage_padding.py` (2), an
>   `OPS-17` (b2) formal deferral the item told leg (c) to re-price: **Status
>   124 at 400 s** (`…125818Z_…v45-gapvoltpad.log`) with **zero `PASSED` or
>   `FAILED` lines anywhere in the log** — it completed none of its two tests
>   inside the window, so this is not a teardown-ate-the-footer case like
>   finding 11's but a genuine cost wall. Disposition
>   `deferred — no footer, exit 124 at 400 s, zero test outcomes printed`;
>   the reason is now measured on 0.11 rather than inherited from 0.7.2. Leg
>   (d) should give it ≥ 600 s or split it by name.
>
>   **Finding 22 — value-ordering beats cost-ordering when the tail is
>   unpriced.** The item's "ascending recorded cost" was followed for the
>   cheap remainder's first module and cost **206 s for 5 names**; the slot
>   then reordered to take the *priced* birdcage block, which returned **32
>   names for 593 s (18.5 s/name)** — the best rate anywhere in this census,
>   against the slot average of 38 s/name and leg (b)'s 17 s/name. The rule
>   the two slots jointly support: **prefer a priced block to an unpriced
>   cheap tail**, because an unpriced 3-name module can cost more than a
>   priced 7-name one, and the 400 s finding-21 window is what an unpriced
>   2-name module actually cost.
>
>   **Deferred (101), all in `tests/validation`.** Two with a substantive
>   measured reason — `test_port_gap_voltage_padding.py`'s two names per
>   finding 21. The other **99** are `deferred — not reached in slot`, the
>   item's declared legal disposition.
>
>   **What remains for leg (d)** (101 names over 16 modules, all
>   `tests/validation`): `coil_loading_*` (58 — priced in `OPS-17` (b2) at
>   their **recorded rank widths**, `larmor_third_rung` needing
>   `TH11_STEP5_RUNG=fine` pinned, and `coil_loading_degree2`'s 14 taken as
>   the `TH-12` memory-wall defer-with-reason, not re-opened),
>   `dodd_deeds_*` (38), `test_port_systematics_composition.py` (3, its own
>   window at its recorded 360 s — the `PORT-10` batch-C killer), and
>   finding 21's 2. Apply finding 18's gate-based classifier before sizing
>   any command. Whichever leg lands last owes the **chunk-level
>   reconciliation**: the seed list of four by name, three totals repo-wide,
>   and the dead module plus the `GEO-23` entries cross-referenced.
> * **Step 2 — execution census on 0.11 (heavy, likely 2+ slots).** Re-run
>   `OPS-17` leg (b2)'s methodology on the current image: every collected test
>   **observed in a completed run with a footer**, real and complex, at each
>   file's recorded rank width. **Anchor (§4):** an observed/collected count
>   with the complement enumerated *by name*, each carrying one of exactly
>   three dispositions — **green**, **red with a filed known-issues entry**,
>   or **deferred with a stated reason**. The 216/232 denominator is the prior
>   and **must be re-derived, not inherited** (`GEO-18`/`GEO-19`/`GEO-20`,
>   `PORT-9` and `EX-31` have all added tests since). *Seed list (2026-08-25
>   18:00 review): the class this census exists to catch now has **three**
>   confirmed members, every one found by an example rather than a scheduled
>   run — `core/cavity.py`'s `TH-9` gates (`OPS-24`), `test_convergence.py`'s
>   rate gate (`MAG-19`), and `test_birdcage_conductor_sizing.py`'s CAD-mass
>   gate (`GEO-21`) — plus `test_two_torus_port_sheet.py`'s stale-record red
>   (`GEO-16` ruling). Step 2's observed-run sweep starts from step 1's
>   159-file site list and must include these four modules by name in its
>   reconciliation.*
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
**`OPS-27` — re-record the stale 0.7.2-era exact records, version-tagged;
sweep for siblings** ✅ *(step 1 2026-08-27 19:30 slot, step 2 2026-08-27
21:00 slot)* *(commissioned 2026-08-27 10:30 review from `OPS-26`
step 2 findings 19 and 23.)* The class: a record made on the 0.7.2 image and
not swept when `OPS-18` re-recorded the 0.11 figures. Three sites so far —
`GEO-16`'s two-torus cell count (re-recorded 2026-08-25, the precedent), and
the two now red on `main`. Done-when: `RECORD_128_RELL2` / `RECORD_128_SEPARATION`
carry `OPS-18`'s 0.017686 / 59.16 with the 0.7.2 digits and
`20260822T123746Z_OPS-18-step3-th10-rerun.log` in-comment; `NCELLS_THIRD`
carries 2 808 204 with 2 807 309 and
`20260827T141059Z_OPS-26-step2d-meshcache-real.log` in-comment; both modules
green from `main` with their unmoved bands (the 1% drift band, the
`NCELLS_THIRD_CEILING`) and the 64 MHz leg untouched; a table of every
`0.7.2`-tagged record in `tests/` with its 0.11 status from a census log;
the two known-issues entries retired. Not a band, not a `TH-10` re-open, not
a fix of any third site the table surfaces — that is filed. Full rubric
(anchor, control, cost, traps, negative result) is §9 item 2.

> **Re-scoped 2026-08-27, 18:00 review, from the finished census.** The
> class is **ten red names over eight modules carrying five distinct meshes**
> plus the one relative-L2 record, not two sites — and every 0.11 value is
> *already measured* in a footered census log at a recorded commit, so this
> chunk buys **no new measurements**: it edits by value and re-runs one
> module per mesh as the anchor. Site list (finding 35's table in
> `attempts.md`, leg (g); known-issues entries of 08-27):
>
> | record (0.7.2 → 0.11) | drift | sites (names) | census log |
> |---|---|---|---|
> | `RECORD_128_RELL2` 0.01826 → 0.017686, `RECORD_128_SEPARATION` 57.31 → 59.16 | — | `test_geometry_floor_discriminator.py` (1) | `20260827T125507Z…` / `20260822T123746Z_OPS-18-step3-th10-rerun.log` |
> | 138 619 → 138 490 | −0.093% | `richardson_ladder` ×2 params, `larmor_probe`, `transition_30mhz` (4) | `…183121Z_OPS-26-step2f-richardson.log`, `…185143Z_…probe-30mhz.log` |
> | 2 807 309 → 2 808 204 | +0.032% | `larmor_mesh_cache` `NCELLS_THIRD` (1) | `…141059Z_…meshcache-real.log` |
> | 417 914 → 418 888 | +0.233% | `slab_resolution`, `larmor_resolution`, `third_rung` (3) | `…183401Z`, `…185422Z`, `…171110Z…destubbed.log` |
> | 697 401 → 697 926 | +0.075% | `reactance_combined_knobs` (1) | `…184138Z_…combined-knobs.log` |
> | 366 207 → 365 970 | −0.0647% | `reactance_wire_resolution` (1) | `…202222Z_…wireres-projected.log` |
>
> **Split into two independent steps by re-run cost** (each step is one
> implementer run; different files, either order):
> * **Step 1 — the cheap half (standard):** the relative-L2 pair, the
>   138 619 family (4 names, 2 modules) and `mesh_cache` — six names, four
>   files. Anchor re-runs: geomfloor complex `-n 2` (23 s), richardson
>   complex `-n 2` (143 s, one command — `FREQ_MHZ=10,30` selects both
>   params, `OPS-17` step 3j), the probe/30 MHz pair complex `-n 2`
>   (139 s), mesh_cache real `-n 2` (262 s): ≈ 570 s over four commands.
> * **Step 2 — the expensive half (heavy):** the 417 914 family (3 names,
>   3 modules), `combined_knobs` and `wire_resolution` — five names, five
>   files. Anchor re-runs: `slab_resolution` complex `-n 2` (430 s, sized
>   ≥ 600), `combined_knobs` complex `-n 8` (570 s, sized 660 — finding 32's
>   +35% under-price), `wire_resolution` **projected half by node id**
>   (436 s, sized 600); `larmor_resolution` and `third_rung` are edited but
>   **not** re-run (their 0.11 count is the same mesh value the slab run
>   asserts; `third_rung` is a warm-cache-only 304 s at `-n 8`) — say so in
>   the commit. ≈ 1 440 s over three commands.
> * **Pending, not in either step:** `box_truncation::test_the_xlarge_box_mesh_is_the_probes`
>   is a suspected sixth mesh no window has reached (finding 36) — it stays
>   filed here until its `projected_xlarge_box` fixture is cheaper, a
>   `MAT-6` pricing question.
> * The `grep -rn '0\.7\.2' tests/` sweep stays as a **completeness check
>   only** — it reached none of the ten sites; the table above is the site
>   list. Every re-record stays an exact equality, version-tagged, 0.7.2 digit
>   and census log in-comment (`GEO-16` precedent); **no band anywhere**.
> * Done-when (amended): all eleven names green from `main` on their re-run
>   modules, every affected module's *other* names byte-identical to its
>   census log, `git show -- tests/` touching only the constants and their
>   comment/docstring copies, and the five known-issues entries of this class
>   (leg (c) geomfloor, leg (d) `mesh_cache`, leg (e) `third_rung`, leg (f)
>   five, leg (g) `wire_resolution`) retired by the step that lands each.

> **Step 2 ✅ 2026-08-27 (21:00 implementer slot) ⇒ chunk ✅.** The
> expensive half landed as ruled: `NCELLS_FINE` 417_914 → **418_888** in
> `test_dodd_deeds_resistance_slab_resolution.py` and
> `test_coil_loading_larmor_resolution.py`, `NCELLS_COMBINED` 697_401 →
> **697_926** in `test_dodd_deeds_reactance_combined_knobs.py`, and the
> literal at `test_dodd_deeds_reactance_wire_resolution.py:268` 366_207 →
> **365_970** — every one an exact equality version-tagged with its 0.7.2
> digit and its census log in-comment (`GEO-16` precedent), **no band
> anywhere and `git diff -- src/` empty**. Three anchors green from `main`
> in three foreground windows, **1 523 s**, all Status 0 with identical
> rank streams: `slab_resolution` `-n 2` complex **16 passed / 479.37 s**
> where the census read `1 failed, 15 passed`
> (`20260828T020157Z_OPS-27-step2-slab.log`, 482 s);
> `combined_knobs` `-n 8` complex **15 passed / 577.00 s** where it read
> `1 failed, 14 passed` (`20260828T021014Z_OPS-27-step2-knobs.log`, 579 s);
> `wire_resolution`'s projected half at the census's four node ids `-n 2`
> complex **4 passed / 459.44 s** where it read `1 failed, 3 passed`
> (`20260828T022006Z_OPS-27-step2-wire-projected.log`, 462 s). Collected
> counts identical to the census runs (16 / 15 / 4), so exactly the four
> stale-record names flipped and no other name's status moved.
> **Finding 41 — the rubric's "five names, five files" is four edits in
> four files, and step 1's finding 38 repeats:**
> `test_coil_loading_larmor_third_rung.py:443` holds **no constant** — it
> asserts the `expected` from its rung table, which *imports* `NCELLS_FINE`
> from `larmor_resolution`, so `git diff` on that module is empty and the
> single `larmor_resolution` edit re-records it. Two of the census's ten
> sites (four of its names) turned out to be import aliases; a per-file
> sweep would have edited nothing in either. **Finding 42 — `combined_knobs`
> reproduced its re-priced window with room to spare:** 577.00 s inside the
> 660 s ruled by finding 32's ≥ 1.5× rule, against the 568.26 s census
> reading (+1.5%) and the 521 s exit-124 that motivated the widening — the
> under-price was real and the remedy held. `slab_resolution` came in at
> 479.37 s (+11.5% on 429.91 s) and the wire half at 459.44 s (+5.8% on
> 434.40 s), i.e. **all three above their census readings**, so the sizing
> rule stays a sizing rule. **Finding 43 (scope note):** the negative
> control is executed at name-and-status level only, as in step 1 — pytest
> captures stdout on passing tests, so an all-green anchor prints no
> `ΔR`/`ΔX`/cell-count line to compare byte-for-byte against the census
> log's failure-capture output. `larmor_resolution` and `third_rung` are
> **edited but not re-run** (their 418 888 is the same mesh value the slab
> run measured); their known-issues lines are marked "re-recorded, re-run
> owed to the next census". Retired by this step: the leg (f) entry in full
> and the leg (g) `wire_resolution` entry; the leg (e) `third_rung` entry is
> re-headed 🟡 rather than retired for that reason. `box_truncation`'s
> suspected sixth mesh stays **pending** (finding 36) — its fixture was not
> opened. Stale *prose* copies of these meshes in nine out-of-scope modules
> (step 1 finding 40) are still unswept and still want one prose-only pass.

> **Audit + step 3 commissioned, 2026-08-28 03:00 review.** §4 audit
> COMPLIANT on all seven footers (604 s + 1 523 s reproduce; every command
> `-n ≤ 8`, longest 579 s under `-k 30 660`; `src/` untouched in both
> commits). Two audit notes: the step-1 tier label said `standard` while
> its `mesh_cache` window measured 256 s — the row now reads `heavy`; and
> the OPS-27 logs are name-and-status evidence only (finding 43) — the
> measured 0.11 digits live in the census logs the constants cite
> in-comment, which is where an auditor must look. **Step 3 (the owed
> tail)** is queued as §9 item 5: run the two edited-not-re-run modules
> and do the finding-40 prose sweep in one slot; `box_truncation`'s sixth
> mesh stays pending until its fixture is re-priced (not this step).

**`OPS-28` — restore the `_DummyComm` double behind `OPS-14`'s reduction**
✅ *(closed 2026-08-28, 22:30 implementer slot)* *(commissioned 2026-08-27 10:30 review from `OPS-26` step 2 finding
12.)* `excitation.py:262-268` reduces `cell_tags.values` with
`comm.allgather` so the deprecated placeholder route "stays runnable"; the
only module that runs that route stubs its comm with `rank` + `allreduce`
and has been red since — undetected because nothing scheduled runs
`tests/ports`. Done-when: the double gains `allgather(value) -> [value]`,
the induced-voltage sign-flip test is green from `main`, the S-matrix
sign-flip test's outcome is *recorded* and known-issues entry 3 is either
retired for that name or re-dated with the reason it still fails, no
`src/` change. Full rubric is §9 item 3.
> **Closed 2026-08-28.** All four done-when clauses met, and the outcome
> of the S-matrix name is the branch the rubric anticipated: it is red at
> its own assertion, so entry 3 is **re-dated with the reason**, not
> retired. The finding worth keeping is that entry 3's one-line statement
> was wrong for this name — the placeholder's matched port on the 2-port
> orientation fixture is the *undriven* one, so the identically-zero wave
> lands on the **off-diagonal** (`S21 = S12 = 0`) while the diagonal is a
> healthy `9.047e-01 − 1.289e-02j`. Same `b = (V − Z₀I)/(2√Z₀) = 0`
> mechanism entry 3 diagnosed for the 3-port fake's diagonal, different
> matrix entry; the entry's title now says "power wave", not "diagonal".
> **Finding 44 (method, for the review):** this is the second time in two
> days that a test double, not the physics, produced a red — and the
> module is still in no scheduled command, so nothing prevents the next
> drift. The durable fix is coverage, not another one-line double repair;
> a review may want to price `tests/ports` (17 names, **2 s** at `-n 2`)
> into a scheduled command. Quantitative anchor, tier and elapsed times
> are in the §7 table row above.

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
| `MAG-13` | Analytic-Dirichlet outer boundary for wire/loop | ✅ | heavy | wire 12.75%, loop 7.07%, rate 1.10; 167 s + 196 s. **2026-08-25: its rate gate (`test_h_refinement_straight_wire`, band [0.7, 1.5]) is red on `main` on the 0.11 image — fitted 1.9038, the finest rung's error collapsed 9.26% → 4.4605% (known-issues 2026-08-25). Disposition is `MAG-19`; the ✅ here is the 0.7.2 close and stands.** **Disposed 2026-08-25 by `MAG-19` step 2 (ruling (i)): the sampled two-sided band is retired with its basis, the rate duty now belongs to `MAG-18`'s one-sided `E_Ω` ≥ 0.7 gate, and `test_h_refinement_straight_wire` gates monotone decay and is green.** |
| `MAG-14` | Helmholtz magnitude comparison in the test suite | ✅ | smoke | 0.728% vs closed form (1.731% before `GEO-8`); 11 s, in CI |
| `MAG-15` | Lagrange-multiplier Coulomb gauge (cross-check) | ✅ | smoke | 7 passed, 13 s |
| `MAG-16` | Complex-build-safe magnetostatic energy | ✅ 2026-08-05 | smoke | 10 passed complex `-n 2` in 4.9 s; cross-build pin 2.9e-07, `Im W` exactly 0; retires known-issues 8 |
| `MAG-17` | Coulomb-gauge multiplier does not vanish for a divergence-free source: h-ladder discriminator (`OPS-17` step-2 defect 2, known-issues 2026-08-17; commissioned 2026-08-17 10:30 review) | ✅ *(audited COMPLIANT 2026-08-21 18:00 review — rate 2.4476 vs the pre-registered ≥ 0.7 verified in `…final2.log`; one nuance on record: the cited "ladder" log is exit 1 — a sign-convention fix in the fit sits between it and the record run, same spreads, band unmoved)* | standard |
| `MAG-18` | Sampler-independent straight-wire gate: annulus-restricted domain L2 of `|B_h| − |B_ana|` with a pre-registered rate band (`OPS-18` step 3 attempt 5 finding, known-issues 2026-08-22: the 10-point radial L2 swings 34% under its own sampler and the 15% band already fails on 0.7.2 at `n_points = 8`; commissioned 2026-08-22 18:00 review) | 🟡 **2026-08-22** — the gate is built, live on `main` and green: `E_Ω` 25.3787 → 10.7288 → 6.6708% on the recorded ladder, **rate 1.6842 ≥ 0.7** and monotone (i ✅); natural-BC wall 32.3117% vs analytic 10.7288%, ratio 0.3320, strictly worse (iii ✅); the h = 0.0025 record 1.0728835983e-01 at 145 884 cells reproduced bit-identically across two `-n 2` runs; the retired 10-point row reproduced under assertion at all three sample counts (15.802788 / 12.748522 / 11.498352% vs 15.8028 / 12.7485 / 11.4984, ≤ 4.2e-06 relative). **Anchor (ii) not met as pre-registered:** `-n 2` vs `-n 4` agree to **7.28e-08**, not 1e-10 — the solve is a direct LU whose factorization order follows the partition, and the *retired* statistic moves the same way on the same two runs (1.9e-07), so ~1e-7 is the solve's cross-width floor and no norm on this field beats it. Known-issues entry filed; the 1e-10 clause is the review's to dispose of. `7 passed`/270.64 s/`-n 2`. **✅ 2026-08-23 03:00 review** — (ii) re-registered at ≤ 1e-6 relative (14× the measured floor, five orders under the sampler defect it excludes), met by the logged `-n 2`/`-n 4` pair; prose entry has the audit. **Re-gated on 0.11 2026-08-23 (§9 item 1, ruling (3\*)) — all three anchors green on the image `main` boots, `7 passed` / exit 0 twice in-slot** (`20260824T003059Z_MAG-18-regate-run1.log`, 296 s; `20260824T003650Z_MAG-18-regate-run2.log`, 296 s; `-n 4` record probe `20260824T003606Z_MAG-18-regate-n4.log`, 32 s): (i) `E_Ω` 25.2868 → 10.6172 → **6.6458%** monotone at fitted rate **1.6854** (0.7.2 read 1.6842 — the *gate* moved 7e-04 across a version change that moved the mesh 145 884 → 147 235 cells, which is the point of `MAG-18`); (ii) `-n 2` 1.0617170177e-01 vs `-n 4` 1.0617175341e-01 = **4.86e-07 relative**, inside the re-registered 1e-6 and consistent with the ~1e-7 LU floor, with the two `-n 2` runs agreeing to 1.86e-08; (iii) natural BC 32.315493% vs analytic 10.617170%, ratio **0.3285**, strictly worse. **No record moved and no band moved** — `E_OMEGA_H0025_RECORD` (1.061717e-01, already version-tagged v0.11.0 by 3a leg 2) reproduces to 2.9e-09 of its 1e-4 band, and the `0.11` `n_points` control row reproduces at all three counts (≤ 3.6e-06 relative). | heavy |
| `MAG-19` | Dispose of the red straight-wire rate gate on 0.11 (fitted 1.9038 vs [0.7, 1.5]; the finest rung's sampled error collapsed on the image): anomalous rung vs wrong instrument, discriminated by running both norms on the same four-rung ladder (commissioned 2026-08-25 10:30 review; known-issues 2026-08-25) | ✅ **2026-08-25** *(**step 1 measured 2026-08-25, 13:30 slot** — the 4×2 table exists and both in-run anchors reproduce digit for digit: the sampled three-rung fit is **1.9038** (the red) and the `E_Ω` three-rung fit is **1.6854** with the h = 0.0025 `E_Ω` record at 2.094e-08 relative, i.e. the `ANS-1` import is right and the physics is what moved. **The pre-stated decision rule selects neither branch**, and says so cleanly: (a) fails because the sampled ladder has a *second* out-of-band pair that does not involve h = 0.0018 (0.004→0.003 at **0.5822**), and (b) fails because the sampled norm is not scattered everywhere — dropping h = 0.0018 alone returns the fit to **0.7309**, inside [0.7, 1.5]. New finding for the ruling: `E_Ω` is stable but **cannot carry the two-sided band** — its pairwise rates run 1.4261–1.9843 and its fit is 1.6661–1.8588 on every subset, so a duty *transfer* of [0.7, 1.5] as written would be instantly red; `E_Ω`'s live gate is one-sided ≥ 0.7 and it passes that on 6/6 pairs. Probe `tests/validation/probe_straight_wire_dual_norm.py` (asserts nothing), log `20260825T183555Z_MAG-19-step1-dualnorm-fits.log`, 160 s at `-n 2`; h = 0.0030 priced at 88 018 cells / 16.5 s. No band moved; ruling requested — options in the prose entry. **Ruled 2026-08-25 18:00 review: option (i)** — rate duty transfers to the `E_Ω` ladder under its own one-sided ≥ 0.7 (already `MAG-18`-gated, green on 0.11); this test keeps monotone decay + the table as report; the sampled two-sided band retires with its basis stated, no upper edge re-imposed anywhere. Step 2 is the landing, §9 item 2. **Step 2 LANDED 2026-08-25, 21:00 slot ⇒ chunk ✅** — the red reproduced first (Status 1, rate **1.90**, 21.8417 / 15.3848 / **4.4605%** at 38 740 / 147 235 / 383 146 cells, 145.27 s), then the disposition green on **bit-identical** errors (`1 passed` / Status 0 / 142.36 s), `MAG-18`'s module green **untouched** as the negative control (`7 passed` / Status 0 / 362.68 s, `E_Ω` fit **1.6854 ≥ 0.7**, record 1.0617170177e-01, natural-BC ratio 0.3285) and `-e 6` green (Status 0 / 148 s, "All assertions hold"). No band moved; one residual sampled upper edge in `test_straight_wire_convergence` (green at 0.7900) filed for the review, not fixed. Logs `20260826T020124Z` / `…020508Z` / `…020739Z` / `…021403Z_MAG-19-step2-*`. *Audited COMPLIANT 2026-08-26 03:00 review (delegated verification; findings checked by this review): all four footers verified (Status 1/0/0/0, 147/144/364/148 s), the red ran on the pre-fix parent `daaf2e1` so it is a genuine red-baseline, every claimed digit greps out of the logs (1.9038 in all three relevant logs, the three errors bit-identical between red and green, `E_Ω` 1.6854 and record 1.0617170177e-01 at mag18 log lines 2682/2684), the retired band's basis is a ~35-line in-comment statement with `RATE_MIN`/`RATE_MAX` values unchanged as report-only, `test_straight_wire.py` has zero edits in the commit (the negative control held), and `mag:6`'s alignment matches. One commit-message imprecision noted: "residual sampled upper edge … green at 0.7900" — 0.7900 is near the* lower *edge; the residual is the retained two-sided band itself, stated accurately in known-issues.* **Residual ruled 2026-08-26 03:00 review: commissioned as `MAG-20`** — the two-rung 8-point sampled fit in `test_straight_wire_convergence` (line 424) keeps ruling (i)'s question open; measure-first disposition, see the `MAG-20` entry)* | standard |
| `MAG-20` | Dispose of the residual two-sided sampled rate band in `test_straight_wire_convergence` — a two-rung 8-point sampled fit still gated on [0.7, 1.5], green at 0.7900, on an instrument `MAG-19` measured swinging 34% under its own sampler (commissioned 2026-08-26 03:00 review from `MAG-19` step 2's filed residual; measure-first, own decision rule — ruling (i) is **not** inherited) | ✅ **2026-08-28** *(step 1 measured and disposed in the 00:00 slot: the pre-stated sweep returns **no crossing** — fitted two-rung rate **0.7900 / 0.7246 / 0.9934** at n_points 8 / 10 / 20, all inside [0.7, 1.5] — so the band is **kept and validated**, not retired. Nothing moved: `RATE_MIN`/`RATE_MAX` unchanged, no assertion added or removed, the disposition is a ~25-line in-comment measurement record. Probe `tests/validation/probe_straight_wire_convergence_npoints.py` (asserts nothing, 49 s at `-n 2`), anchor `test_straight_wire.py` **7 passed / 371 s / Status 0** from `main` with `E_Ω` fit 1.6854 and the h = 0.0025 record 1.0617170193e-01 (1.5e-9 of its 1e-4 band) untouched. **Two residual findings handed to the review, not acted on**: the sampler swing on this test's 0.4 R window is only 6–7% of the error (vs the 34% `MAG-19` measured on the 0.8 R window), but it still moves the *rate* by **37% of its own value**, and the n = 10 row clears `RATE_MIN` by **0.0246**)* | standard |

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
>
> **RULED 2026-08-25, 18:00 review — option (i). Step 2 is the landing
> (§9 item 2, 18:00 queue).** The rate duty transfers to the `E_Ω` ladder
> under `E_Ω`'s **own one-sided ≥ 0.7** criterion — which `MAG-18` already
> gates, live and green on 0.11 (fit 1.6854, 6/6 pairwise above 0.7) — and
> `test_h_refinement_straight_wire` keeps its monotone-decay assertion plus
> the error table as a report. The two-sided [0.7, 1.5] on the sampled
> statistic is retired **with its basis stated in-comment**, not widened:
> the statistic swings 34% under its own sampler on both images and the band
> already failed on 0.7.2 at `n_points = 8` (`OPS-18` step 3 attempt 5) —
> the gate was passing on a sampler choice, which is the defect `MAG-18`
> built `E_Ω` to remove. Option (ii) rejected (a 0.03 margin on a statistic
> with a 34% sampler swing is not a gate); option (iii) answered narrowly —
> no upper edge is re-imposed anywhere, because none has a validated basis
> on 0.11 and under-convergence is the failure mode a rate gate exists to
> catch; a superconvergence guard, if ever wanted, is a weekly-review
> commissioning with its own measured basis. **Landing instructions
> (step 2):** rewrite the test per the transfer (duty statement pointing at
> `MAG-18`'s gate as the owner, old assertion in-comment with both logs
> cited); keep the module exporting what `mag:6` imports and reconcile the
> example's use of `RATE_MIN`/`RATE_MAX` to the transferred duty in the same
> commit (old text in-comment — a licensed alignment under this ruling, not
> a loosening); anchors are the disposition's own green, `MAG-18`'s gate
> green in the same run set, and `-e 6` as the consumer check; the
> known-issues entry retires with this commit. No new solve beyond the gate
> and example runs is needed — every number the ruling used is in step 1's
> log.
>
> **Step 2 LANDED — 2026-08-25, 21:00 slot ⇒ chunk ✅.** The ruling executed
> as written, in one commit, on four `-n 2` real-build runs, and the red was
> reproduced before it was disposed of:
>
> | run | log (`…Z_MAG-19-step2-…`) | result | elapsed |
> | --- | --- | --- | --- |
> | red, pre-edit | `20260826T020124Z_…-red` | Status **1**, rate **1.90** | 145.27 s |
> | disposition | `20260826T020508Z_…-green` | **`1 passed`** / Status 0 | 142.36 s |
> | `MAG-18` control | `20260826T020739Z_…-mag18` | **`7 passed`** / Status 0 | 362.68 s |
> | `-e 6` consumer | `20260826T021403Z_…-e6` | Status 0, "All assertions hold" | 148 s |
>
> *Anchor.* The red run reproduces `MAG-19` step 1 digit for digit — 21.8417 /
> 15.3848 / **4.4605%** at 38 740 / 147 235 / 383 146 cells — and the green run
> reproduces those three **bit-identically**, so the only thing that changed
> between Status 1 and Status 0 is the assertion, not the physics. The fitted
> rate still prints (1.9038) beside the retired band and the new
> `RATE_DUTY_OWNER` string; what the test now gates is monotone decay.
> *Negative control, and it held:* `MAG-18`'s module is **untouched** (zero
> edits to `test_straight_wire.py`) and green — `E_Ω` 25.2868 → 10.6172 →
> 6.6458% at fitted **1.6854 ≥ 0.7**, record 1.0617170177e-01, natural-BC ratio
> 0.3285, i.e. the 2026-08-23 re-gate reproducing. The duty moved onto a gate
> that is executing and green. *Consumer:* `mag:6` needed only the licensed
> alignment (its rate assertion retired in-comment with both logs cited, the
> monotone assertion it already carried promoted from negative control to
> anchor) and passes; `RESOLUTIONS`/`RATE_MIN`/`RATE_MAX`/the fit are still
> exported and still imported, nothing restated (`ANS-1`).
> **No band moved.** *One residual, filed not fixed:*
> `test_straight_wire.py::test_straight_wire_convergence` still gates a
> two-rung 8-point sampled fit on the same `[0.7, 1.5]` (green at **0.7900** in
> the control run). It sits inside the module this landing had to leave
> untouched and outside `MAG-19`'s scope, so it was left alone, named
> in-comment at the constants and in the retired known-issues entry — whether
> the ruling's "no upper edge on a sampled statistic" reaches it is a review
> question.

**`MAG-20` — dispose of the residual two-sided sampled rate band in `test_straight_wire_convergence`** ✅
**2026-08-28** *(step 1 measured and disposed in the 00:00 slot; audited COMPLIANT 03:00 review; commissioned
2026-08-26 03:00 review from `MAG-19` step 2's residual. Full narrative archived in `docs/planning/plan-archive.md`, entry «§7 MAG-20 full narrative — archived 2026-08-30 (weekly review)».)*
> * **Measured (`20260828T050130Z_MAG-20-step1-npoints-probe.log`, 49 s, 0.11 / gmsh 4.15.2):** the two-rung
>   ([0.004, 0.0025], 38 740 / 147 235 cells) sampled fit at `n_points` 8 / 10 / 20 reads **0.7900 / 0.7246 / 0.9934**
>   (errors 21.5512 / 21.1826 / 22.6647% and 14.8669 / 15.0685 / 14.2097%, swing +7.00% / +6.04%). **No count crosses
>   either edge of [0.7, 1.5]** ⇒ under the pre-stated rule the band is kept and **validated**; `RATE_MIN`/`RATE_MAX`
>   unchanged, disposition is an in-comment measurement record; n = 8 reproduces `MAG-19`'s 0.7900 to four decimals.
> * **Anchor (§4):** `test_straight_wire.py` **7 passed / 369.95 s / Status 0** from `main`
>   (`20260828T050256Z_MAG-20-step1-anchor-module.log`), `E_Ω` fit **1.6854**, h = 0.0025 record 1.0617170193e-01 vs
>   tagged 1.0617170177e-01 (1.5e-09 relative, 1.5e-05 of its 1e-4 band); diff two pure-addition hunks, no `src/`.
> * **Findings 45–46, recorded not acted (03:00 ruling):** sampler swing on this window is 6–7% (vs `MAG-19`'s 34%)
>   yet moves the rate by 37% of its value; n = 10 clears `RATE_MIN` by only 0.0246. No third rung commissioned; if
>   the gate ever reads red at n = 8 the disposition is ruling (i)'s retire-with-basis; never tighten the record band below ~1e-8.

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
| `GEO-15` | **Birdcage conductor sizing: is graded sizing a `PORT-9` prerequisite?** (the 0.7091 question; named prerequisite of `PORT-9` step 3) | ✅ 2026-08-16 (graded sizing recovers **0.9670** of the conductor's CAD mass at h_c = 1.6 mm vs **0.7403** baseline, gate cleared, `GEO-9` identities unmoved at < 1e-9; 41 s at `-n 2`; closed by the 10:30 review — the chunk was its one question, now answered by measurement. **2026-08-25: its gate `test_graded_conductor_sizing_recovers_the_cad_mass` is red on `main` on the 0.11 image — the ungraded baseline rung no longer meshes (conductor-sizing axis, not resolution; known-issues 2026-08-25). Disposition is `GEO-21`; the ✅ here is the 0.7.2 close and stands**. **2026-08-26: `GEO-21` ✅ — the gate is green again on a *coarse-graded* control (`BASELINE_CONTROL_RESOLUTION` = 4.8e-3, 0.846150 vs graded 0.966977), so what the live module measures is now **fine vs coarse grading**. The graded-vs-ungraded answer to the `PORT-9`-prerequisite question is the 0.7.2 close and must be cited as such — do not restate it off the module's present numbers**) | standard |
| `GEO-16` | **Emit the gap boxes' longitudinal port-sheet mid-plane in `two_torus_domain`** (the `PORT-9` step-1 mesh prerequisite; commissioned 2026-08-16 18:00 review) | ✅ **2026-08-25: `test_kwarg_off_reproduces_the_recorded_mesh` is red on `main` — the kwarg-off record 79 534 (0.7.2) vs 79 070 measured on 0.11, sheet exonerated by two independent no-sheet builds. Ruled 2026-08-25 18:00 review: re-record licensed, gate constant + both guide copies in one commit (§9 item 3, known-issues entry has the full scope); the ✅ stands. **LANDED 2026-08-25, 22:30 slot** — `NCELLS_UNGATED_RECORD` = **79 070** version-tagged to the 0.11 image with the 0.7.2 digit and both provenance logs in-comment; gate pair `5 passed / 55.84 s / Status 0` printing `cells=79070` and the meshed-band cross-check **0.974490841** inside 0.970–0.980 (`20260826T033222Z_GEO-16-rerecord-gate-pair.log`), `mesh:4` green with the sheeted build properly distinct at **79 940** (`…033350Z`, 31 s) and `mesh:1` at **79 070 / 14.1 s** (`…033431Z`, 16 s); the `mesh:1` docstring + guide and four `mesh:4` guide copies moved in the same commit. No band moved; known-issues entry retired** | standard |
| `GEO-17` | `coil_phantom_domain` region-resolution policy shrinks the coil volumes it refines (−21.68%/−22.62%; `OPS-17` step-2 defect 1, known-issues 2026-08-17; commissioned 2026-08-17 10:30 review) — step 1 ✅ 2026-08-20: the sizes were never applied (`getBoundary` `combined=True` ⇒ 0 points); `Min`-over-`Constant`-fields, coil meshed/CAD 0.7547 → **0.8356** | ✅ *(audited COMPLIANT 2026-08-21 18:00 review — 1e-9 negative-control gate, sign-of-refinement identity and partition 1.000000000000 verified against `20260820T110549Z…final.log`. **2026-08-25: `mesh:5`'s example-side inverted control lost its separation on 0.11 — clamps-only clears the 0.755 floor by 6e-6; the gate module itself is green (one-sided on the policy mesh). Ruled 2026-08-25 18:00 review: re-choose the control measure-first with ≥ 0.05 separation, demote to report only if none exists — §9 item 3, known-issues entry has the branches; the ✅ stands. **LANDED 2026-08-25, 22:30 slot — the re-choose branch, not the demotion.** A four-sizing probe (`20260826T033622Z_GEO-17-mesh5-sizing-probe.log`, `-n 1`, 8 s) measured coil meshed/CAD at h = 0.015 / 0.018 / 0.020 / 0.025 (0.755006 / **0.649812** / 0.595547 / 0.471986 on coil_1) and the example adopted `CONTROL_RESOLUTION` = **0.018**, the first coarser sizing missing the 0.755 floor by ≥ `CONTROL_SEPARATION` = 0.05 — measured margins **+0.105188 / +0.106569**, whole probe table in-comment, hunting stopped at the first that separated. The control is a **third build**, not a re-pointed one: `UNIFORM_VOLUMES_RECORD` is a gate constant at h = 0.015, so the clamps-only mesh stays as its 1e-9 reproduction and as the sign-identity baseline, and `SIZING_SEPARATION` is now asserted against **both** baselines (+0.078411 / +0.085109 and +0.183605 / +0.187132). `POLICY_MIN_CAD_RECOVERY`, the one-sided gate-module assertion and every record are untouched — `test_mesh_tag_integrity.py` was not edited. `mesh:5` green twice (`…033758Z`, `…033959Z`, Status 0, 8 / 9 s); known-issues entry retired**)* | standard |
| `GEO-18` | Birdcage conductor gaps: cut the legs so the port boxes have terminals (`PORT-9` step-3 mesh prerequisite; commissioned 2026-08-20 03:00 review from step 3 legs (a)+(b) 🚫) | ✅ 2026-08-22 (*step 2 audited COMPLIANT 2026-08-22 03:00 review — every figure verbatim in `20260822T020113Z_GEO-18-step2.log:8569-8576`, no pre-existing test touched; one transparency note: the sheets-off control asserts the `110+i` **cell** tags absent, and the `210+i` facet absence the entry and commit claim is implied by that, not measured — `EX-28` is commissioned to assert it directly*; **step 1 ✅ 2026-08-20** — terminals exist: 2.236196e-04 m² per port, **0.988616** of the closed-form `2·π·r_leg²`, all four equal to the printed 7 digits, *audited COMPLIANT 2026-08-21 18:00 review — closed-form band, closure and mass identities verified against all three logs, the pre-derivation red disclosed*; **step 2 ✅ 2026-08-22** — the sheets exist and are exact: meshed sheet area `1.120000000e-04 m²` = the analytic `dx·g` at **1.000000000000** on all four ports, `w_eff = A/h` equal to the bbox extent to 1.000000000000, out-of-plane spread ≤ 2.512e-16 m, half-volumes 0.500000000000 each, C4 sheet spread **8.470e-16**, step 1's terminal band and closure re-asserted on the sheeted mesh) | standard |
| `GEO-19` | `birdcage_port_domain` at `leg_count = 16`, gapped + sheeted: identity family re-gated (C16), cost rung measured — 32-port directive item (a) (commissioned 2026-08-23 weekly review) | ✅ *(**step B ✅ 2026-08-25** — the local-frame port construction is on `main` under ruling (6\*): invariance control `3 passed` from `main` at 116 085 / 114 655 cells, C4 spread 6.050e-16, terminals 0.988616 × 4, no-gap control 98 666 digit for digit; the three `PORT-9` modules `19 passed` **twice in-slot** on the mesh-tagged re-records, σ_max 0.999992805, class separation 166.6766×, (d0) margin 2256.9707×, leg (c)'s `I₁` reproducing to 5.934e-12 against a 1e-9 band. The open-limit (1e6 Ω) column is retired as a record-bearing fixture — no band widened. **Step C attempt 1 2026-08-25**: the rung is measured — 116 085 → **307 296 cells (2.6472×)**, mesh 22.93 → **74.18 s (3.2357×)**, inside the 1 M / 600 s stop rule — and gates (i)/(iii)/(iv)/(v) are green at 16 legs (partition and closure 1.000000000000, C16 sheet spread **1.331e-15**, conductor 0.981503, separation margin 1.560723×) with the 4-leg control reproducing step B's record at delta **0** cells / 6.050e-16. Gate (ii)'s *equality* half is red at **8.434e-04** vs 1e-5 — a three-valued azimuth-class structure with ≤ 2e-7 inside each class, i.e. a C4 band applied to C16; parked on `attempt/GEO-19-stepC-20260825T125000Z`, no band widened, ruling requested. **Ruled 2026-08-25 10:30 review: construction symmetry — per-azimuth-class reading, intra-class 1e-6, inter-class ceiling 5e-3, every existing band unmoved; landing instructions in the prose entry, queued §9 item 1**. **Step C landed 2026-08-25 12:00 slot — chunk ✅**: the ruled module is `2 passed` / **117 s** from `main` (`20260825T170316Z_GEO-19-stepC-ruled.log`; record run `…T170523Z…-ruled-record.log`, 115 s). Gate (ii) per class from the mesh's own coordinate mirrors — three classes, intra **1.923e-07 / 5.849e-08 / 6.144e-08** against 1e-6, inter **8.431e-04** against 5e-3; the 4-leg control returns **one** class at **3.184e-08**, i.e. the reading reduces to the old flat gate. Four already-green gates reproduce (partition/closure/halves/`dx·g` 1.000000000000, C16 sheet spread 1.331e-15, conductor 0.981503, margin 1.560723×) and the control meshes **116 085** cells, delta **0**. **Cost rung: 116 085 → 307 296 cells (2.6472×), mesh 22.99 → 74.37 s (3.2346×)** — Phase 6's first measured rung, on F-small. No band outside the module moved; `GEO-20` step 2 unblocked)* | heavy (probe first) |
| `GEO-20` | High-pass birdcage ring-gap port layout (`ring_gap_length`, `2·leg_count` ports, the `GEO-18` pattern on the end rings) — 32-port directive item (b); step 1 at 4 legs, step 2 at 16 after `GEO-19` (commissioned 2026-08-23 weekly review) | ✅ *(audited **COMPLIANT** 2026-08-29 10:30 review — both step-2 logs Status 0 at 188 / 184 s, `1 passed` on every rank stream, 40 port lines per log at 1.000000000000 and 0 off-digit, every assert a reduced closed-form/symmetry identity at 1e-9 / 1e-12 / 1e-6 / 5e-3, module byte-identical to the parked attempt, nothing loosened. Two prose corrections, gate unaffected: the C32 sheet spread is 4.985e-16 at `-n 2` and 4.488e-16 at `-n 12` — it moves at the 1e-16 floor like the C16 value, so "only one digit moves" undercounts; and the 16-leg terminal "spread 2.572e-07 against the 1e-5 band" is std/mean, printed not asserted — the 1e-5 `RING_TERMINAL_RATIO_BAND` gates the 4-leg control only, the 16-leg terminals are gated by [0.95, 1.0] plus the per-class 1e-6 / 5e-3.)* *(**step 1 ✅ 2026-08-24** — the 8 ring ports exist at 4 legs and every pre-stated gate is green twice in-slot: terminal **0.974455** of the closed-form `2·π·r_ring²` inside the [0.95, 1.0] inscribed band and equal across the 8 to **≈ 2e-8** (gate 1e-5; digit corrected by the 10:30 review audit — see the prose entry), closure and port-volume **1.000000000000**, sheet meshed/analytic **1.000000000000** with out-of-plane spread **5.042e-18 m**, C4 and top/bottom-mirror spreads below 1e-12, `GEO-9` partition green, conductor 0.969275 ≥ 0.95; negative controls green — kwarg off reproduces the uncut birdcage and the leg+ring mesh is a 12-port mesh with **both** identity families exact. Step 2 (16 legs, 32 ports) is serial on `GEO-19`. **Step 2 attempt 1 2026-08-28 — negative result, parked on `attempt/GEO-20-step2-20260828T094500Z`, no band landed.** The 16-leg ring-gapped fixture **builds** (265 621 cells, 48 ports = 16 leg + 32 ring) and is **green at `-n 1`** (`20260828T093352Z_GEO-20-step2-probe1.log`, `1 passed` / 275 s) but **red at `-n 2` on the identical geometry** (`20260828T093839Z_GEO-20-step2-record.log`, Status 1 / 198 s): three of the 32 ring sheets do not reconstruct — P30 and P37 at **0 facets**, P45 at **5 facets / 0.315302109223** of `w²` — against 1.000000000000 on the other 29, and P30's boundary closure reads **0.981164653445** against 1e-9. Everything not routed through a sheet is exact at both widths: 32/32 port volumes 1.000000000000 of `2·R·w²·tan α`, `GEO-9` partition and air-box closure 1.000000000000, ring arcs against Pappus 1.000000000000, conductor 0.976465 of CAD, no phantom contact. **The terminals are the finding that did land as information:** all 32 read 0.974454791–0.974455668, spread **2.572e-07**, i.e. the ring family shows **no** azimuth-class split at 16 legs where the leg family split three ways at 8.434e-04 (`GEO-19` step C) — the ruled per-class bands were applied from the start and would have passed, as would the flat 1e-5. Both negative controls reproduce digit for digit in the same run: kwarg off at 16 legs **307 296** cells / C16 sheet spread **1.331e-15** (ratio 1.000000), and the 4-leg ring rung **110 786** cells (ratio 1.000000) with **one** azimuth class at intra 4.198e-08. **Cost rung measured and citable** (a cell count and a wall time, not a reconstruction reading): 4 → 16 legs ring-gapped **110 786 → 265 621 cells (2.3976×)**, mesh **23.30 → 72.23 s (3.1003×)** — cheaper than the leg-gapped 16-leg build's 307 296 / 72.23 s. Known-issues entry opened; the rank-width dependence is **not diagnosed**, the hypothesis is `_interface_facet_tags` matching on owned cells only, and the `-n 4`/`-n 8` discriminator costs no `src/` change. A fix in `_interface_facet_tags` touches every module that reconstructs a sheet and could move existing records — **a review's ruling, not an in-slot fix**. **Cause diagnosed 2026-08-28, interactive session — and it is not in `_interface_facet_tags`:** `birdcage_port_domain` is built with **no partitioner**, i.e. `GhostMode.none`, so an interior port facet on a partition boundary has no second cell to read a tag from. The class is width-driven, not leg-count-driven — the **4-leg** 12-port rung is exact at `-n 1/2/4/8` and loses one air facet at `-n 12` (P8 closure **0.990103697427**), and the same mesh reads `1.000000000000` on all 12 with `shared_facet` plumbed. The fix and the re-record sweep are **`GEO-24`**; see the re-headed known-issues entry. **Step 2a ✅ 2026-08-28 (15:00 slot)** — the ownership table is measured on the 32-port fixture at `-n 4` and `-n 8` (Status 1 / 189 s each, no `src/` change): the broken-sheet set **moves with the width** — {P25, P29, P37, P41, P45} at 4 and {P17, P21, P26, P30, P37, P44, P48} at 8 against {P30, P37, P45} at 2, neither new set nested in the old — and is **identical to the set of ports whose two half-boxes are not owned by one rank**, symmetric difference empty both ways at both widths, 32 × 2 with no exception; the 4-leg control is 0 broken / 0 straddling at both. All 40 port volumes, both closures and Pappus stay **1.000000000000** and both cell-count controls reproduce at ratio 1.000000, so the defect is confined to facet reconstruction. Confirmed ⇒ stop per the ruling; chunk stays 🟡, the fix is `GEO-24`'s. **Step 2 attempt 2 queued by the 2026-08-29 03:00 review as §9 item 4** — a re-run of the parked module (`31c08ed`, the one file on the attempt branch) at `-n 2` and `-n 12` once the `GEO-24` plumb is on `main` (§9 item 1); the plumb repaired both 4-leg `-n 12` reds at unchanged cell counts, so the prediction is zero broken sheets at any width. **Unblocked 2026-08-29, 06:00 slot:** `GEO-24` closed (step 2b green on the validation family at both widths), so the re-run may proceed and step 1's "closure and volume/analytic **1.000000000000** on all 12" **loses its width-conditional caveat** — it is measured true at 12 ranks on the plumbed tree, port P8 reading 176 air facets / closure 1.000000000000 where it read 175 / 0.990103697427. **Step 2 attempt 2 ✅ 2026-08-29, 09:00 slot — the re-run is green at BOTH widths and the chunk closes.** The parked module (`31c08ed`, `tests/mesh/test_birdcage_ring_gaps_scaleup.py`, +569 lines, restored by `git checkout` — the generator signature had not moved) is `1 passed` at `-n 2` (`20260829T140037Z_GEO-20-step2-rerun-n2.log`, Status 0 / **188 s**) and at `-n 12` (`…140402Z_…-rerun-n12.log`, Status 0 / **184 s**), standard tier, real, `-s`, `-k 30 570`. **Every pre-stated anchor from the `-n 1` probe is met at both parallel widths:** **265 621** cells, all **32/32** ring sheets meshed/analytic **1.000000000000** of `w²` (grep count: 32 port lines, **0** off the digit), all 32 boundary closures 1.000000000000, all 32 `volume/analytic` 1.000000000000 of `2·R·w²·tan α`, terminals **0.974454791–0.974455668** with spread **2.572e-07** against the 1e-5 band, C32 sheet spread 4.488e-16, the four ruled azimuth classes at intra **4.198e-08 / 4.498e-07 / 4.681e-07 / 8.997e-07** (band 1e-6) and inter **3.315e-07** (ceiling 5e-3), `GEO-9` partition and air-box closure 1.000000000000, Pappus 1.000000000000, conductor **0.976465** of CAD. **The plumb's prediction — zero broken sheets at any width — is confirmed:** attempt 1's three reds are repaired, P30 and P37 back to **176 air facets** from 0, P45 to **180 facets / closure 1.000000000000** from 5 / 0.315302109223. **Both in-run negative controls reproduce digit for digit at both widths:** kwarg off at 16 legs **307 296** cells (ratio 1.000000) and the 4-leg ring rung **110 786** cells (ratio 1.000000) with one azimuth class at intra 4.198e-08; the only digit that moves anywhere is the C16 sheet spread at the 1e-15 roundoff floor (1.331e-15 at `-n 2`, 1.210e-15 at `-n 12` — `GEO-24` step 1a saw the same pair, reported not a failure). **Cost rung reproduced:** 4 → 16 legs ring-gapped 110 786 → 265 621 cells (**2.3976×**), mesh 21.63 → 68.19 s (3.1529×) at `-n 2` and 21.74 → 67.72 s at `-n 12`. The module lands on `main`, `attempt/GEO-20-step2-20260828T094500Z` is deleted, and the 32-port fixture's sheets are now licensed to read. Nothing loosened, no band moved)* | standard |
| `GEO-21` | Dispose of the red `GEO-15` graded-conductor gate on 0.11: the ungraded baseline (`conductor_resolution=None`) no longer meshes at any global resolution tried, so the whole gate is non-executing on `main` (found by `EX-30` leg (mesh); commissioned 2026-08-25 18:00 review; known-issues 2026-08-25) | ✅ **2026-08-26** *(status marker flipped by the 18:00 review audit — the prose entry and the `GEO-15` row already read ✅; history: step 1 measured 2026-08-26, blocked on a ruling — the candidate control `h_c = 3.2e-3` recovers **0.916742** of the CAD mass, which is **neither** pre-stated branch: not ≤ 0.90 "clearly below", not clearing 0.95, and **inside the module's own `CAD_MASS_GATE - 0.05` = 0.90 separation guard**, so branch (2) as named cannot produce a green gate without loosening that guard. Graded side green — 0.966977 at 98 666 cells. Coarse-ward ladder measured and handed over, nothing adopted; see the entry. **Ruled 2026-08-26 03:00 review: option (b), control = 4.8e-3** — separation 0.846150 vs 0.966977 with the 0.90 guard unmoved, demoted claim (fine-vs-coarse grading) stated; 6.4e-3 rejected for cliff adjacency. **Step 2 ✅ 2026-08-26 (04:30 slot) — landed as written and the chunk closes**: control `None` → 4.8e-3 version-tagged with the six-rung probe table in-comment, demoted claim (fine vs coarse grading) in the module docstring and the `mesh:3` guide, gate `1 passed in 41.11s` at 0.846150 / 0.916742 / 0.966977 with the 0.95 gate and the 0.90 separation guard unmoved, `mesh:3` green at separation 0.120826, docrefs `dead=0 guide=0 stale=13 exit=2` giving `meshing` 2 → 0; known-issues gate red retired, generator-continuum finding re-headed and open)* | standard |
| `GEO-22` | `straight_wire_domain` coarse-resolution floor on 0.11: bisect the `[0.008, 0.010)` threshold and land a measured guard so a too-coarse request raises legibly instead of aborting inside gmsh (owner for the `EX-30` leg (root) finding; commissioned 2026-08-26 18:00 review; known-issues 2026-08-25, re-headed 08-26 and again 08-28) | ✅ *(**demoted ✅ → 🧪 2026-08-29 10:30 review, §4 clause 3** — the closing evidence is a probe that asserts nothing plus a re-run of `test_geometry_failure_is_collective.py`, whose `total_caught == comm.size` is the did-raise property the 08-28 18:00 audit already classified as non-quantitative for `GEO-23`; the fix is step 2c, one asserted leg-D anchor — queued §9)* — **step 1 ✅ 2026-08-28 as a measured negative: there is no floor.** The 2.5e-4 sweep of `[0.008, 0.010]` reads **non-monotone on both geometries** — `h = 0.00875` fails while coarser rungs mesh — and reproduces **bit-identically** across two runs, so no `RESOLUTION_FLOOR` can be written and none was; `src/` untouched. **Step 2 ✅ 2026-08-29 (07:30 slot) ⇒ chunk ✅** — the size-field probe leg the 08-28 10:30 ruling commissioned reads **18/18 OK and 0/18 fallbacks** against leg C's 7 FAILs and 18/18 fallbacks, on a leg-C control that reproduces step 1 bit-identically in its own process; `src/` still untouched and the size-field *licence* is the weekly review's. **Step 2c ✅ 2026-08-29 (16:30 slot) ⇒ chunk back to ✅** — the probe's finding is now asserted: `tests/mesh/test_straight_wire_size_field_probe.py` reads **19 823 cells / 0 fallbacks** patched and **21 830 / 1** unpatched on the example geometry at `h = 0.008`, 0.00% against the pre-stated ±1% band, identical at `-n 1` (8 s) and `-n 2` (7 s); the perturbed-reference negative control reds on both rank streams and the restored constant re-runs green. `src/` untouched, no record moved, known-issues entry stays OPEN | smoke (probe `-n 1`) + standard (gate) |
| `GEO-23` | The 0.11 "Invalid boundary mesh (overlapping facets)" family: one owner for the three `OPS-26` census reds (coil+phantom generator, `birdcage_port_domain` partition test, and the **rank-dependent** `test_boundary_condition_selection.py` deadlock) plus the dead `test_cylindrical_domain.py` module — classify each as geometry-deterministic or partition-dependent, ladder the resolution, land no fix (commissioned 2026-08-27 03:00 review; four known-issues entries of 2026-08-27). ***Step 1 ✅ 2026-08-28 (09:00 slot)** — all four sites are **geometry-deterministic**, red at `-n 1` (2–4 s, Status 1); the two "rank-dependent" claims are **log-interleave artifacts, withdrawn by measurement**; the `-n 2` deadlock is a **raise-path** property (row 2's wrapped re-raise footers at Status 1 in 5 s where the three unwrapped sites cost 120 s each); both laddered generators are **monotone**, each failing exactly one 0.8-step above a meshing sizing (`cylindrical_domain` 0.040 → meshes 0.032/1 213 cells; `coil_phantom_domain` 0.030 → meshes 0.024/5 464 cells); the four sites are **three generators** (the two phantom modules share one byte-identical call); the recorded `IndexError … size 0` signature is **in-process gmsh contamination, not a second defect**; control green at unmoved bands; the dead module is now one asserting 1e-9 partition test. Step 2 (a review's call) has two measured, separable levers — sizing and raise-path.* ***Step 2a ✅ 2026-08-28 (12:00 slot)** — the raise-path lever landed: one shared `_raise_geometry_failure_on_every_rank` helper wraps the rank-0 gmsh build in `straight_wire_domain`, `cylindrical_domain` and `coil_phantom_domain` (`git diff -w` = +76 lines, 0 deletions — the rest is indentation). All three deadlocking rows of the step-1 table now footer at **Status 1 in 2–3 s** where step 1 recorded **Status 124 at 120–121 s**, summaries unchanged, each non-building rank's traceback ending in the wrapped `RuntimeError` naming generator and `resolution`; `GEO-22`'s gate (`tests/mesh/test_geometry_failure_is_collective.py`, the `allreduce`d caught flag at `h = 0.00875`) is `1 passed in 0.91s` at `-n 2`. Controls green and unmoved: the three modules at `-n 1` exactly as step 1, `mag:1` at **21 830 cells / 6.666667e-05 T**, `test_cylindrical_domain.py` 1 passed, `test_coil_phantom_mesh.py` 3 passed, the `GEO-21` control 36.76 s. Twelve windows, 72 s. The three census reds stay red (geometry reds, step 2b's) but cost seconds to observe. **Step 2b (sizing) is the only step left.*** ***Step 2b ✅ 2026-08-28 (13:30 slot) ⇒ chunk ✅** — the sizing lever landed and **all three census reds are green**: three call sites moved to step 1's coarsest measured meshing rung (`test_boundary_condition_selection.py:26` 0.04 → **0.032**, `test_phantom_material_model.py:110` and `test_phantom_field_metrics.py:35` 0.03 → **0.024**), each with the step-1 ladder in-comment and a reduced global cell-count print. Every module green at **both** widths: bcsel `3 passed, 1 skipped` at `-n 1` (0.94 s) and `-n 2` (0.80 s) real, phantom-material `4 passed` at `-n 1` (2.66 s) and `-n 2` (1.63 s) complex, phantom-metrics `2 passed` at `-n 1` (1.71 s) and `-n 2` (1.67 s) complex — against the census reds' `1 failed, 2 passed, 1 skipped` / `1 failed, 3 passed` / `1 failed, 1 passed`. The printed counts are **1213** and **5464 / 5464**, reproducing the step-1 ladder's 1 213 / 5 464 **exactly** (0.00% against the pre-stated ±1%), so the sizing is stable run-to-run and across rank width. **No physics assertion moved** — the negative result this step existed to expose did not occur, and since no module pins a cell count the only assertions at risk were physics ones. Controls: `test_cylindrical_domain.py` at its unmoved 0.02 `1 passed in 1.29s` at `-n 2`, and the complex `tests/environment` gate `11 passed` before the complex windows. `src/` untouched; `git diff --stat` is three test files plus docs. Eight footered windows, 40 s recorded elapsed, FFCx stub sweep clean before window 1 and no exit 124 in the slot. The three geometry known-issues entries are **RETIRED** (both halves closed — 2a's deadlock, 2b's geometry). **Residual, and a review's call, not this chunk's:** the fourth site the chunk was commissioned over — `test_birdcage_volumes_partition_the_box` on `birdcage_port_domain` — is **still red** and was never laddered here, because its resolution floor is already `GEO-21`'s open entry and its fixture is `GEO-20`'s; no `GEO-23` step remains for it.* ***Demoted ✅ → 🧪 by the 2026-08-28 18:00 review audit (§4 clause 3).** The step-2b anchor — 1213 / 5464 cells reproducing step 1's ladder at ±1% — is a `print` at each of the three call sites, compared by the reader against a comment; no test asserts it. The only assertion 2a/2b *added* (`test_geometry_failure_is_collective.py:60`, `total_caught == comm.size`) is a did-raise property, and the three re-greened modules' own gates are finiteness/positivity except a pre-existing σ/ε DG0 identity (`test_phantom_material_model.py:139,185`) that 2b did not add. Logs, agent execution and elapsed all check out (20 footered windows, 112 s); nothing was loosened; `src/` untouched. **Step 2c (queued, §9 item 1):** turn each of the three prints into an asserted `abs(n_global / N_REF − 1) ≤ 0.01` against the step-1 ladder value (a documented reference from a prior run, §4 3(iv)), `allreduce`d before the assert; on green the chunk returns to ✅.* ***Step 2c ✅ 2026-08-29 (19:30 slot, 2026-08-28 local) ⇒ chunk back to ✅** — the anchor is now asserted, not printed. Each of the three moved call sites carries a module constant `N_CELLS_REF` (1213 / 5464 / 5464, the step-1 `-n 1` ladder values, version-tagged in-comment with the 0.7.2-era sizing that no longer meshes) and one gate `abs(n_global / N_CELLS_REF - 1) <= 0.01`, where `n_global` is `mesh.topology.index_map(dim).size_global` — already global on every rank, so the step-2b `comm.allreduce(size_local)` was **removed rather than kept under the assert** (summing a global would have read `size * n` and the gate would have failed at `-n 2` for the wrong reason). Six windows green at both widths: bcsel `3 passed, 1 skipped` at `-n 1` (3 s) and `-n 2` (3 s) real, phantom-material `4 passed` at `-n 1` (3 s) and `-n 2` (4 s) complex, phantom-metrics `2 passed` at `-n 1` (3 s) and `-n 2` (3 s) complex, every one printing its reference count **exactly** (1213 / 5464 / 5464, 0.00% against the ±1% band) on both rank streams. **Negative control executed and footered:** `N_CELLS_REF` 1213 → 1300 (7.2% off) gives `1 failed, 2 passed, 1 skipped` / Status 1 / 2 s at `-n 2`, the new `AssertionError` naming generator, measured count and reference on **both** ranks while the modules' pre-existing assertions stay green — so the gate is load-bearing and rank-symmetric; the constant was restored and re-run green (`3 passed, 1 skipped`, Status 0, 2 s). Complex `tests/environment` gate `11 passed` (21 s) before the complex windows; FFCx 0-byte stub sweep clean before window 1, zero stray `python3`, no exit 124 in the slot. `src/` untouched; the diff is the three test modules. Nine footered windows, **44 s** recorded elapsed. The `GEO-21` residual (`test_birdcage_volumes_partition_the_box`) is unchanged and still not this chunk's.* | ✅ | smoke (`-n 1` probes) + standard (`-n 2` ladders) |
| `GEO-24` | **Give `birdcage_port_domain` the `shared_facet` ghost layer, and re-read every module that reconstructs a sheet on it at `-n 2` and `-n 12`** — the diagnosed cause of the `GEO-20` step 2 rank-width defect (known-issues re-headed 2026-08-28; commissioned by the human operator, interactive session, 2026-08-28) | ✅ *(**step 1a ✅ 2026-08-28, 21:00 slot** — the `main`-side "before" table for the seven `tests/mesh/` consumers is measured at both widths in 14 windows / **668 s**, no `src/` change: **every cell count identical across widths** (116 085 / 98 666 / 128 111 / 114 655 / 116 085+116 475 / 98 666 / 307 296), **`-n 2` green in all seven**, and **two `-n 12` reds, both facet reconstruction** — `test_birdcage_ring_gaps` on `port P8 closure 0.990103697427`, the width probe's digit exactly, and `test_birdcage_port_terminals` on its phantom↔air positive control, **245 facets / 0.935322 against 255 / 0.979885**, outside the `[0.95, 1.0]` band. That second red is the step's new information: the `GhostMode.none` gap is **not** port-sheet-specific — any interior material interface on this fixture inherits it, so **step 2a's gate must also require 255 facets / 0.979885 at `-n 12`**. Pre-stated negative control holds: every terminal ratio and port-volume identity (no facet reconstruction in either) is identical at both widths in every module, including the 16-leg scale-up's three azimuth classes and its C16 sheet spread (1.331e-15 vs 1.210e-15, the only digit that moves anywhere, at the 1e-15 floor). Consumer list re-derived by construction — **no difference** from the review's seven. **Cost finding: nothing unmeasured** — `test_birdcage_port_scaleup` at `-n 12` took **108 s** inside `-k 30 570` (`GEO-19` step C's exit 124 was a bundled window, not this module's price), and `-n 12` costs the same wall clock as `-n 2` throughout (±2 s), the mesh being built on rank 0 either way. Step 1b (validation family) and step 2a (the plumb + this family re-read) are unblocked; full table in the known-issues entry)* ***step 1b ✅ 2026-08-29, 22:30 slot** — the `main`-side "before" table for the five `tests/validation/` consumers is measured at both widths in 13 windows / **660 s**, complex, no `src/` change, and the family is **clean**: every cell count identical across widths (116 085 in four modules, 116 085 + 116 475 in `_leg_offset_sweep`), **green at `-n 2` and at `-n 12` in all five**, and every gated digit identical — `Z_{11,21,31,41}` reproducing their `PORT-9` records at 1.07e-10–2.57e-10, `sigma_max(S)` **0.999992805** and max column power sum **0.793823974** unchanged, C4 class spreads **0.0553 / 0.0353 / 0.0214 %** unchanged, `||S−S^T||/||S||` 8.141422487e-15 → 1.116856988e-13 (band 1e-3), the termination margin **2256.9707×** / spread **0.0040%** unchanged, and `_leg_offset_sweep`'s displaced rung still breaking (iii′) at 6.2219 / 7.1142 / 2.8474 %. So the `GhostMode.none` gap costs this family **nothing** at `-n 12` — it is confined to the modules that read a facet group directly (step 1a's two reds). Consumer list re-derived by construction, no difference from the review's five; the two `_larmor_gate*` modules are correctly outside the intersection. **The pre-stated negative control is the step's finding and it did *not* hold:** `test_port_lumped_two_torus.py` — already `shared_facet`-plumbed — is green at `-n 2` (gap ratio **0.894141**, the record exactly) and **red at `-n 12`** (**0.894274**, moved 1.33e-04 against a 1e-04 band) at an unchanged **184 176** cells, with the other four tests passing; the moving quantity is a *solved* line integral (`Im Z12` 1.110303775 → 1.110469250, 1.5e-4), not a facet reconstruction. **Step 2b's gate must therefore separate reconstruction readings (must be exactly 1.000000000000) from solve-derived digits, which this fixture shows can drift at 1e-4 with rank width even when the ghost layer is present**; whether the two-torus band should be width-qualified is a review's call. Nothing loosened, no record re-written; step 2b unblocked)* ***step 2a 🟡 2026-08-29, 00:00 slot — the plumb works and is NOT landed; blocked on a review's re-record ruling.** The one-keyword `partitioner=create_cell_partitioner(GhostMode.shared_facet, 2)` at `io/mesh.py:3356` (the `two_torus_domain` kwarg and comment, nothing else in `src/`) was applied, the seven `tests/mesh/` consumers re-read at `-n 2` and `-n 12` in 14 windows, and the patch then **reverted on `main` and parked on `attempt/GEO-24-step2a-20260829T052300Z` (`e1dede8`)**. ≈ 870 s of compute over 16 windows + 1 control window. **Two of the three gate clauses pass outright:** every cell count is identical to step 1a at both widths and every kwarg-off control reproduces (`cells 116085 vs 116085, delta 0, relative 0.000e+00`); and **both previously-red `-n 12` readings are repaired** — `ring_gaps` port P8 back to **176 air facets / closure 1.000000000000** from 175 / **0.990103697427**, and `port_terminals`' phantom↔air control back to **256 facets** from 245 — all seven modules `passed` at both widths. **The third clause is what stops the step:** `port_terminals`' `-n 2` phantom↔air digit **moves, 255 facets / 0.979885 → 256 / 0.984183**, and item 4's pre-stated negative result is that a moving `-n 2` digit is a review's, so the slot reverted rather than landed. Every other `-n 2` digit in all seven modules is identical (C4 spread 6.050e-16, leg terminals 0.988615825–0.988615858, ring terminals 0.974454791/0.974454832, Pappus 1.000000000000, the 16-leg classes 0.989367514/0.989449735/0.988615772 and C16 1.331e-15). **The moved digit is diagnosed, not left open:** two serial windows read **256 / 0.984183 at `-n 1` on the plumbed tree *and* at `-n 1` on `main`** — a single rank needs no ghost layer, so 256 is the truth and step 1a's 255 was itself one facet short of it at every parallel width. The record was **defective, not partition-dependent**; after the plumb the reading is 256 / 0.984183 at `-n 1`, `-n 2` and `-n 12` alike. Pre-stated untouched-fixture controls green with the plumb applied (`test_two_torus_port_sheet` + `test_cylindrical_domain`, `4 passed`, `GEO-16` control 79 070 cells). **Owed by a review:** rule on re-recording 255 → 256 / 0.984183 with its `-n 1` provenance (that is step 3's business, which item 4's scope excludes), after which the parked branch lands unchanged. Nothing loosened, no record re-written, no band moved)* ***RULED 2026-08-29 03:00 review: defect repair, not re-baseline.** The `-n 1` reading on `main` with no plumb (`…050535Z_…-terminals-n1-main.log`, 256 / 0.984183) is the serial truth and needs no ghost layer, so step 1a's 255 / 0.979885 was one facet short at every parallel width from the same `GhostMode.none` gap — the record was defective, and no test carried it (`test_birdcage_port_terminals` gates a `[0.95, 1.0]` band). Landing the parked commit with the re-read is **step 2a′** (§9 item 1); step 2b (validation family, §9 item 2) closes the chunk and retires the known-issues entry; the two-torus `-n 12` finding from step 1b is split out as its own chunk, `PORT-12`, and is not this chunk's. A second lesson recorded for step 2b: step 1a treated `-n 2` as the reference width, and this fixture can be one facet short at `-n 2` too — reconstruction digits are checked against the digit, solved digits against their band.* ***step 2a ✅ 2026-08-29, 04:30 slot (step 2a′ — the landing)** — `e1dede8` cherry-picked onto `31a4e0b` as `470f410`; `git diff HEAD~1 -- src/` is that one `io/mesh.py:3356` kwarg + comment hunk alone and the tree is clean after. Re-read on the **landed** tree in six windows / **246 s**: `test_birdcage_port_terminals` at `-n 1` / `-n 2` / `-n 12` (23 / 21 / 22 s) and `test_birdcage_ring_gaps` at `-n 2` / `-n 12` (75 s each), all Status 0, logs `20260829T0930…–0934…_GEO-24-step2aP-*`. **Every pre-stated anchor met:** phantom↔air **256 facets / 0.984183 at all three widths** on **98 666** cells (the serial truth now reproduced in parallel — the repair), `ring_gaps` port P8 at `-n 12` **176 air facets / closure 1.000000000000** (was 175 / 0.990103697427) on **128 111** cells with all 12 `volume/analytic` and all 8 sheets 1.000000000000, the ring-gapped rung **110 786** cells, Pappus 1.000000000000 gapped and uncut, and every other digit identical to the step-2a table (leg terminals 0.988615826–0.988615858, ring terminals 0.974454791 / 0.974454832, port boxes air 24 facets / closure 1.000000000000, kwarg-off control 98 666 / 0.966977). **Negative control green and unmoved:** `test_two_torus_port_sheet` + `test_cylindrical_domain` `4 passed` / 30 s with the `GEO-16` control at **79 070** cells — no cell count moved anywhere, so the landed commit is the measured one. **Step 1a's `-n 2` `255 / 0.979885` is annotated *defective* (one facet short; `-n 1` truth 256 / 0.984183) in the known-issues table**, per the 03:00 ruling; no band, tolerance or record in `tests/` moved. `attempt/GEO-24-step2a-20260829T052300Z` deleted. The chunk stays 🟡 on **step 2b** (the five `tests/validation/` consumers), which closes it and retires the known-issues entry.* ***step 2b ✅ 2026-08-29, 06:00 slot — the validation family re-reads clean on the plumbed tree at both widths; CHUNK CLOSED and the known-issues entry RETIRED.** Eleven windows / **485 s** at `470f410`, complex, `FEM_EM_REQUIRE_COMPLEX=1`, `-s`, `-k 30 480`, one module per width per window, **no `src/` change in the slot**; env gate `11 passed` / 21 s, then all ten module windows **Status 0** (`20260829T1100…–1108…Z_GEO-24-step2b-*`): `_lumped_column` 33 / 30 s, `_four_port` 49 / 39 s, `_larmor_probe` 38 / 33 s, `_termination_probe` 38 / 33 s, `_leg_offset_sweep` 97 / 74 s at `-n 2` / `-n 12`. **Both pre-stated gate classes met.** *(i) Reconstruction readings identical to the digit:* all four `_lumped_column` sheets **26 facets / 5.835298880e-05 m² / `w = A/h` 7.294123600e-03 m / out-of-plane 0.000e+00 m** at both widths, every cell count identical across widths and equal to step 1b's records at ratio **1.000000** (**116 085** in four modules, 116 085 + **116 475** in `_leg_offset_sweep`). *(ii) Solved digits inside each module's own in-file band at both widths:* `Z_{11,21,31,41}` at rel. deviation **1.071e-10–2.568e-10** of their `PORT-9` records, `sigma_max(S)` **0.999992805**, max column power sum **0.793823974**, C4 class spreads **0.0553 / 0.0353 / 0.0214 %** (band 0.5%) with separation 166.6766×, `||S−S^T||/||S||` 1.044e-14 / 1.897e-14 (band 1e-3), termination margin **2256.9707×** / spread **0.0040%**, displaced rung **6.2219 / 7.1142 / 2.8474 %** (amplifications 112.58× / 201.52× / 133.11×). The **only** `-n 12` movement anywhere is `_lumped_column`'s `Z_11` at **4.1e-9** relative and the two Frobenius residuals at the 1e-14 floor — reported, orders inside every band and far below `PORT-12`'s 1e-4. **Negative control** (this family has no kwarg-off control; the control is step 1b's own table): every `-n 2` digit reproduces step 1b's `main`-side reading, so the plumb changed nothing this family could see — expected, step 1b having shown the family took no damage from `GhostMode.none`. The two-torus control was deliberately **not** re-run (its `-n 12` red is `PORT-12`'s, unmoved by this patch). **Disposition:** `GEO-20` step 1's "1.000000000000 on all 12" **loses its width-conditional caveat** (measured true at 12 ranks on the landed tree), `GEO-20` step 2 becomes an unblocked re-run of the parked 32-port module, and step 1a's `-n 2` 255 / 0.979885 stands annotated *defective*. Nothing loosened, no band moved, no record in `tests/` touched.* | standard |
| `GEO-25` | **F-human cost probe** — `birdcage_port_domain` at `ring_radius` 0.07 → 0.15 m (30 cm coil, the operator's 2026-08-25 directive), a parameter set on the existing constructor, not a new one; cell count and mesh time per rung, conductor sizing **not** coarser than the 4.8 mm floor without re-measuring it (known-issues `GEO-21` ruling) | ⬜ *(commissioned 2026-08-30 02:15 weekly review; **the ruling text was lost with that session** — what survived is the dashboard summary and the `GEO-21` known-issues ruling's two sentences. Not queueable until the 2026-09-06 weekly review re-writes the anchor (a cell-count / mesh-time stop rule against the `GEO-19` 2.6472× / 3.2357× rung), the rung ladder and the scope; §10 subgoal 4 is explicitly **not** blocked on it)* | heavy (probe first) |


**`GEO-24` — plumb the birdcage ghost layer, then re-read the fixture's records at two widths** ✅ *(steps 1a
2026-08-28 21:00, 1b 22:30, 2a′ 2026-08-29 04:30, 2b 2026-08-29 06:00 ⇒ chunk closed; commissioned by the human
operator 2026-08-28; the table row carries every step's digits; the commissioning plan archived in
`docs/planning/plan-archive.md`, entry «§7 GEO-24 full narrative (commissioning plan; closure recorded in the table row) — archived 2026-08-30 (weekly review)».)*
> * **Cause and fix:** `birdcage_port_domain` called `_model_to_mesh` with no partitioner (`GhostMode.none`), so a
>   facet reconstruction across a partition boundary could miss its second cell. One kwarg at `io/mesh.py:3356`,
>   `create_cell_partitioner(GhostMode.shared_facet, 2)` (`470f410`); nothing else in `src/`.
> * **Before (1a, 14 windows / 668 s; 1b, 13 windows / 660 s):** every cell count identical across widths (116 085 /
>   98 666 / 128 111 / 114 655 / 116 475 / 307 296); two `-n 12` reds, both facet reconstruction — `ring_gaps` P8
>   closure **0.990103697427** (175 vs 176 facets) and `port_terminals` phantom↔air **245 / 0.935322** vs 255 / 0.979885;
>   the five `tests/validation/` consumers clean at both widths (σ_max 0.999992805, spreads 0.0553 / 0.0353 / 0.0214%).
> * **After (2a′ 6 windows / 246 s, `20260829T0930…–0934…_GEO-24-step2aP-*`; 2b 11 windows / 485 s,
>   `20260829T1100…–1108…Z_GEO-24-step2b-*`):** P8 **176 / 1.000000000000** at `-n 12`; phantom↔air **256 / 0.984183 at
>   `-n 1` / `-n 2` / `-n 12`** — ruled 08-29 03:00 a defect repair (the `-n 1` truth), not a re-baseline; every `-n 2`
>   validation digit reproduces 1b, the only `-n 12` movement `Z_11` at 4.1e-9. Known-issues entry RETIRED; `GEO-20` step 1's "1.000000000000 on all 12" loses its width caveat; `GEO-20` step 2 becomes an unblocked re-run. * **Carry-forward:** the two-torus `-n 12` gap-ratio drift (0.894141 → 0.894274 at 184 176 cells) is **`PORT-12`**.

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

**`GEO-17` — `coil_phantom_domain`'s region-resolution policy shrinks the coil volumes it refines** ✅ *(step 1
2026-08-20 06:00 slot; audited COMPLIANT 2026-08-21 18:00 review; commissioned 2026-08-17 10:30 review from
`OPS-17` step-2 defect 1 (−21.68% / −22.62% coil volume under a finer request). Full narrative archived in
`docs/planning/plan-archive.md`, entry «§7 GEO-17 full narrative — archived 2026-08-30 (weekly review)».)*
> * **Hypothesis refuted, mechanism measured:** there were no size fields at all — `gmsh.model.getBoundary` with the
>   default `combined=True` returned **0 points** for every region (`20260820T110127Z_GEO-17-step1-diag.log`), so the
>   policy meshed the coil at the air's 0.020 clamp. **Fix:** per-region sizes as a `Min` over per-volume `Constant`
>   fields (`VolumesList`, `IncludeBoundary=1`) set as the background mesh.
> * **Measured (`20260820T110549Z_GEO-17-step1-final.log`, `-n 2`, 13 s):** coil_1 **+10.7169%** (1.191750413e-04 →
>   1.319468693e-04 m³, meshed/CAD 0.754685 → **0.835563**), coil_2 **+10.7851%** (0.752565 → 0.833730), phantom +0.9374%,
>   air −0.2643%; both meshes partition their volume at **1.000000000000**; uniform column reproduces the `OPS-17`
>   record at 1e-9 (negative control). Probe forcing `MeshSizeExtendFrom*` off moved coil_1 −3.12% and was reverted
>   (`…110302Z_…-fieldfix.log` vs `…110407Z_…-probe-defaults.log`).
> * **Band replaced with its measurement:** the strict xfail's 5% "must not move" premise is false for a curved region;
>   now `test_region_resolution_policy_refines_the_tagged_volumes_toward_cad` (policy > uniform, meshed/CAD ≤ 1.0, coil recovery ≥ 0.755). Known-issues "Four defects" §1 resolved; `mesh:5` control re-chosen 2026-08-25 (row).

**`GEO-18` — birdcage conductor gaps: cut the legs so the port boxes have
terminals** ✅ *(both steps closed — step 1 2026-08-20, step 2 2026-08-22; commissioned 2026-08-20 03:00 review from `PORT-9` step 3 legs (a)+(b) 🚫. Review decision: cut the legs, not the end rings — drive direction `ẑ` for every port, square section `dx = dy` makes the four-port layout C4-invariant by construction; port azimuths move from 45° + k·90° to the leg positions k·90° in the gapped variant, a deliberate low-pass-birdcage physics change.)*
> * **Step 1 ✅ 2026-08-20** (`leg_gap_length` opt-in, default `None` bit-for-bit; `_birdcage_leg_gap_layout` helper). `g = 8 mm`, box `(1.400000e-02, 1.400000e-02, 8.000000e-03)` m, `h_c = 1.6e-3`. Per port: terminal area **2.236196e-04 m²** = **0.988616** of `2·π·r_leg² = 2.261947e-04 m²` (band [0.95, 1.0]), equal on all four ports to 7 digits; closure `(A_cond + A_air + A_phan)/A_box = 1.000000000000`; phantom-facing 0; gap volume meshed/analytic **1.000000000000**; `GEO-9` partition identities < 1e-9; gapped meshed/CAD conductor **0.970152** (≥ 0.95); **114 846** cells, mesh 22.61 s, rung 24.32 s. Mass identity re-derived off a cancellation (§4 `MAG-10`/`MAG-15` precedent): `CAD_gapped/(CAD_uncut − 4·π·r_leg²·g)` = **1.000000000192** (1e-9), the difference form read 0.999999994733. Negative control: kwarg off reproduces **98 474** cells, `EX-21` 0.967019, conductor-facing `0.000000e+00 m²` on all four ports. Logs `20260820T093433Z_GEO-18-step1.log`, `20260820T093603Z_GEO-18-step1-final.log` (8 passed, 136.61 s), `20260820T093830Z_GEO-18-step1-record.log` (1 passed, 45.16 s), all `-n 2`. `tests/mesh/test_birdcage_port_terminals.py` kept as the standing guard on the default geometry.
> * **Step 2 ✅ 2026-08-22** (`emit_port_sheets` opt-in, `ValueError` without `leg_gap_length`; attempt 1 parked on `attempt/GEO-18-step2-20260822T004500Z`, exit 124 from an `allreduce` inside `if comm.rank == 0`, log `20260822T003614Z_GEO-18-step2.log`; fix hoisted the collective). Per port (`20260822T020113Z_GEO-18-step2.log`, 2 passed, 53 s, `-n 2`): sheet **54 facets, 1.120000000e-04 m²**, meshed/analytic `dx·g` = **1.000000000000** (1e-9); `h = 8.000000000e-03 m`, `w_eff = A/h = 1.400000000e-02 m`, `w_eff/w_bbox = 1.000000000000`; out-of-plane spread **2.512e-16 / 9.714e-17 m** (band 1e-12); half-volumes **0.500000000000 / 0.500000000000**; step-1 gates survive (terminal ratio 0.988616, closure 1.000000000000, partition < 1e-9); C4 sheet spread **8.470e-16**. Sheeted mesh **116 416** cells (mesh 22.73 s, rung 24.77 s); cell tags `100+i`/`110+i`, sheet facet tags `210+i`. Negative control: sheets off reproduces step 1 exactly (114 846 cells, 0.988616, tags `[1, 2, 3, 101, 102, 103, 104]`, every `110+i`/`210+i` absent). Regression: birdcage mesh suite 10 passed, 186 s (`20260822T020224Z_GEO-18-step2-regression.log`).
> **Carry-forward:** `PORT-9` step 3's mesh prerequisite is discharged — the birdcage has terminals and a port sheet per port; step 3 re-runs unchanged (gates (i)–(iii) never moved). A gapped birdcage without lumped elements still cannot resonate — no port model, solve, impedance or resonance claim here. Ramp example `EX-28` ✅ 2026-08-23.
> Full narrative: `docs/planning/plan-archive.md`, entry «§7 GEO-18 full narrative — archived 2026-08-23 (weekly review)».

**`GEO-19` — `birdcage_port_domain` at `leg_count = 16`, gapped and sheeted: the identity family re-gated and
the cost rung measured** ✅ *(closed 2026-08-25 12:00 slot; step B 2026-08-25 under ruling (6\*), step C under the
10:30 construction-symmetry ruling; commissioned 2026-08-23 weekly review, 32-port directive item (a). Attempts,
rulings (4\*)/(6\*) and the class-gate derivation archived in `docs/planning/plan-archive.md`, entry «§7 GEO-19 full narrative — archived 2026-08-30 (weekly review)».)*
> * **Blockers cleared:** tag collision above 9 legs (upper halves → `200+i`); axis-aligned sheets → each box and
>   sheet built at azimuth 0 and taken to the leg by a snapped `affineTransform`. Step B invariance from `main`:
>   **116 085** sheeted / **114 655** gapped cells, C4 spread **6.050e-16**, terminals 0.988616 × 4, no-gap 98 666
>   (`20260825T003437Z_GEO-19-stepB-invariance-main.log`); the three `PORT-9` modules `19 passed` twice on the
>   mesh-tagged re-records (σ_max 0.999992805, separation 166.6766×, (d0) margin 2256.9707×). Open-limit (1e6 Ω)
>   column retired as a record-bearing fixture — no band widened.
> * **Step C at 16 legs (`20260825T170316Z_GEO-19-stepC-ruled.log` 2 passed / 117 s; `…T170523Z…-ruled-record.log`):**
>   partition / closure / halves / `dx·g` **1.000000000000**, C16 sheet spread **1.331e-15** vs 1e-12, conductor
>   meshed/CAD **0.981503** ≥ 0.95, separation 2.731265e-02 m vs floor 1.750000e-02 m (**1.560723×**); gate (ii) per
>   azimuth class — intra **1.923e-07 / 5.849e-08 / 6.144e-08** vs 1e-6, inter **8.431e-04** vs 5e-3; 4-leg control
>   one class at 3.184e-08, 116 085 cells delta 0. **Cost rung: 116 085 → 307 296 cells (2.6472×), mesh 22.99 → 74.37 s (3.2346×).** * **Carry-forward:** F-small only — **says nothing about F-human**; closed-form layout ceiling **N ≤ 25** on `ring_radius = 0.07` with 14 mm boxes (32 legs need ≥ 0.0876 m) flagged to §10 Phase 6; open-limit conditioning known-issues entry OPEN with (6\*)'s retire-when; thin adjacent/opposite separation flagged for Phase 6.

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
> * **Step 2 attempt 1 (2026-08-28, 04:30 slot) — negative result, parked on `attempt/GEO-20-step2-20260828T094500Z`.** Summary in the table row; full measurement in `attempts.md` 2026-08-28T09:50Z and the known-issues entry of the same date. The branch is **kept**: its module (`tests/mesh/test_birdcage_ring_gaps_scaleup.py`, every band imported, both controls) is the fixture step 2a needs and is not reproduced anywhere on `main`.
> * **Ruled 2026-08-28 10:30 review — step 2a, the discriminator, is queued (§9 item 3); the `src/` fix is not.** The attempt's hypothesis (`_interface_facet_tags` matches a sheet facet by the tags of its two adjacent *owned* cells, so a port whose two half-boxes straddle a rank boundary loses its sheet) predicts one specific, cheap observable: **the set of broken ports moves with the rank count.** Measure that before any `src/` line moves. **Do (no `src/` change):** copy the parked module's test onto the working tree from the branch (`git show attempt/GEO-20-step2-20260828T094500Z:tests/mesh/test_birdcage_ring_gaps_scaleup.py > …` — do not merge the branch), add a per-port print of the rank owning the `PORT_LOWER+i` / `PORT_UPPER+i` cells (rank-local counts `allgather`ed — `cell_tags.values` is rank-local), and run the one test at `-n 4` and `-n 8` with `-s`, each its own footered command. **Anchor (§4), pre-stated:** the broken-port set at each width, printed as a table against the `-n 2` record {P30, P37, P45}; the prediction is a *different* set at each width **and** every broken port having its lower and upper half-box cells owned by different ranks with every intact port on one rank — that ownership-vs-reconstruction agreement across 32 × 3 ports is the quantitative assertion, and a single intact straddling port or a single broken same-rank port **refutes** the hypothesis. **Negative controls:** the 29 intact `1.000000000000` sheet readings at `-n 2` are the baseline the new widths are read against; all 32 port volumes at 1.000000000000 of `2·R·w²·tan α` must reproduce at both new widths (the volume identity does not route through the sheet and must not move). **Cost:** the `-n 2` record was 198 s; mesh time is rank-independent (gmsh on rank 0, ~72 s), so expect ~150–200 s per width, ≈ 400 s over two commands at `-k 30 400` each; standard tier, real build. **Traps:** `-s` is mandatory (the module's evidence lives in `print` — the `-n 1` probe carries no numbers for exactly that reason); a broken sheet gives `_sheet_azimuth_deg` a NaN centre — the `_report_safely` guard already converts that into a footered red, keep it; a fresh gmsh model per build. **Scope:** measurement only — no edit to `_interface_facet_tags`, no band, no record, the module lands on `main` only if the review later rules it in (leave it on the branch; commit the ownership print there or as a probe under `scripts/probes/`). **Negative result:** the same three ports broken at every width means the defect is *not* partition-driven and the hypothesis is wrong — record the table in the known-issues entry, chunk stays 🟡, stop; the hypothesis *confirmed* is also stop — the fix touches every sheet-reconstructing module (`GEO-16`, `GEO-18`, `GEO-19`, `PORT-9`'s three, `EX-31`/`EX-33`) and is commissioned as step 2b by a review with an explicit re-record licence, never in-slot.
> * **Step 2a ✅ executed 2026-08-28 (15:00 slot) — the ownership table is measured on the 32-port fixture, the broken set moves with the rank width, and it agrees with rank ownership port for port with no exception at either width.** Logs `20260828T200204Z_GEO-20-step2a-n4.log` and `20260828T200524Z_GEO-20-step2a-n8.log`, Status 1 / **189 s each**, standard tier, real, `-s`, the parked module plus an `allgather`ed per-port count of owned `PORT_LOWER+i` / `PORT_UPPER+i` cells; no `src/` change and nothing landed on `main` but logs and prose. Broken sheets: **{P25, P29, P37, P41, P45}** at `-n 4` and **{P17, P21, P26, P30, P37, P44, P48}** at `-n 8`, against the `-n 2` record {P30, P37, P45} — three different sets, and neither new set is a superset of the old (P45 breaks at 2 and 4, not 8; P30 at 2 and 8, not 4). The pre-stated quantitative assertion holds exactly: at both widths **broken ≡ straddling**, symmetric difference **empty in both directions**, 32 ports × 2 widths, so the refuting observation (an intact straddling port, or a broken same-rank port) did not occur. The 4-leg control is **0 broken / 0 straddling** at both widths. Every negative control reproduces digit for digit: 40/40 port volumes **1.000000000000** of `2·R·w²·tan α`, `GEO-9` partition and air-box closure **1.000000000000**, Pappus **1.000000000000**, kwarg-off 16-leg **307 296** cells / C16 spread **1.331e-15** (ratio 1.000000), 4-leg ring **110 786** cells (ratio 1.000000). Failure shape unchanged: the sheet is lost whole (0 facets) or as a fragment (5 facets / **0.315302109223** at `-n 4`, 6 facets / **0.449137697797** at `-n 8`) while the terminal stays at its intact value and the volume stays exact; closure drops (0.991120008826 / 0.991064589826) only on the one port per run that also loses an **air** facet — the 4-leg-at-`-n 12` signature. **This confirms the phenomenology the ruling asked for, and it is the ghost-layer cause, not the `_interface_facet_tags` one:** a straddling port is exactly a port whose interior sheet facets have a neighbour cell that `GhostMode.none` never materialises. Per the ruling, **confirmed ⇒ stop** — chunk stays 🟡, no band, no record, no `src/` line. The fix and the re-record sweep are **`GEO-24`**'s (already commissioned by the human operator); with this table `GEO-24` step 1 owes only the before/after readings of the modules on `main`, and `GEO-20` step 2 becomes a re-run once `GEO-24` step 2 is green. The instrumented module lands as `scripts/probes/geo20_step2a_ownership_scaleup.py` — the §7 entry's stated alternative to the branch, taken because a concurrent session held `examples/ports/05_*` modified mid-slot and that path differs between `main` and the branch, so a `git checkout` of the branch would have refused; the branch is unchanged and nothing under `tests/` moved. See the attempts.md entry of 2026-08-28T20:40Z for that anomaly.
> * **Step 2 attempt 2 ✅ executed 2026-08-29 (09:00 slot) — the re-run on the plumbed tree is green at `-n 2` and `-n 12`; `GEO-20` is ✅ and the 32-port ring-gap layout is built and gated.** Two windows, **372 s** total, standard tier, real, `-s`, `-k 30 570`, no `src/` change in the slot: `20260829T140037Z_GEO-20-step2-rerun-n2.log` (Status 0 / 188 s) and `20260829T140402Z_GEO-20-step2-rerun-n12.log` (Status 0 / 184 s), each `1 passed`. The module came back exactly as parked — `git checkout 31c08ed -- tests/mesh/test_birdcage_ring_gaps_scaleup.py`, the single file on the attempt branch, +569 lines; the birdcage generator's signature had not moved and no import failed. **The quantitative assertion (§4) is the 32-fold reconstruction identity family**, all read at both widths: 32/32 sheets meshed/analytic **1.000000000000** of `w²`, 32/32 boundary closures **1.000000000000** against 1e-9, 32/32 `volume/analytic` **1.000000000000** of the analytic wedge `2·R·w²·tan α`, plus `GEO-9` partition, air-box closure and the Pappus ring-arc check all at 1.000000000000 and the ruled per-azimuth-class terminal bands (intra 4.198e-08 / 4.498e-07 / 4.681e-07 / 8.997e-07 against 1e-6; inter 3.315e-07 against 5e-3). **Attempt 1's failure is repaired exactly where the `GhostMode.none` diagnosis said it would be:** P30 and P37 go 0 → **176 air facets**, P45 goes 5 facets / 0.315302109223 → **180 / 1.000000000000**, on the identical **265 621**-cell geometry — so `GEO-24`'s one-keyword plumb, not any change in this module, is what made the fixture readable in parallel. Both in-run controls reproduce (307 296 and 110 786 cells, ratio 1.000000 each); the single moving digit anywhere is the C16 sheet spread at the 1e-15 floor (1.331e-15 → 1.210e-15), the same pair `GEO-24` step 1a reported. The cost rung re-measures at 2.3976× cells and ~3.15× mesh time, unchanged from attempt 1. Branch `attempt/GEO-20-step2-20260828T094500Z` **deleted** with this commit, per its disposition ("delete it with the commit that lands or retires the module"). The known-issues entry was already retired by `GEO-24` step 2b; it gains only a confirmation line, no re-opening.

**`GEO-21` — dispose of the red `GEO-15` graded-conductor gate on 0.11: the ungraded baseline no longer
meshes** ✅ *2026-08-26 (step 1 00:00 slot, ruled 03:00 review option (b), step 2 04:30 slot; commissioned
2026-08-25 18:00 review from `EX-30` leg (mesh). Full narrative archived in `docs/planning/plan-archive.md`, entry «§7 GEO-21 full narrative — archived 2026-08-30 (weekly review)».)*
`GEO-15`'s ✅ is the 0.7.2 close and stands; the `h_c = None` control aborted in gmsh ("overlapping facets") on 0.11.
> * **Step 1 (measure-first):** red reproduced `20260826T050100Z_GEO-21-step1-red-repro.log`; CAD-mass probe
>   `…050134Z_…-cad-mass-probe.log` — 3.2e-3 → **0.916742** (47 975 cells), 1.6e-3 → **0.966977** (98 666), CAD mass
>   1.030097043e-04 m³; control ladder `…050319Z_…-control-ladder.log` (`-n 1`) — 4.8e-3 → **0.846150** (33 185),
>   6.4e-3 → 0.767219 (27 912), 9.6e-3 → FAIL. Neither pre-stated branch fired (0.916742 fails the module's own
>   `CAD_MASS_GATE − 0.05` = 0.90 separation guard); ruling requested.
> * **Ruling (b):** control = `h_c = 4.8e-3` (buffer rung away from the meshability cliff); the claim is **demoted to
>   fine vs coarse grading** — "grading required" closed on 0.7.2 and stays there — stated in module, test, `mesh:3`
>   docstring and guide. **Step 2:** gate `20260826T093202Z_GEO-21-step2-gate.log` `1 passed in 41.11s`, 0.846150 /
>   0.916742 / 0.966977 asserted at the unmoved ≥ 0.95 gate and 0.90 guard (cleared by 0.0538); `mesh:3`
>   `…093403Z_…-mesh3.log` separation 0.120826; docrefs `…093552Z` `stale=13`, **`meshing` 2 → 0**; two latent bugs fixed.
> * **Carry-forward (OPEN):** known-issues entry re-headed on the generator-continuum finding — coarse conductor sizings, `None` included, cannot mesh on 0.11 — uncommissioned; `GEO-23`'s fourth site (`birdcage_port_domain`) lands here.

**`GEO-22` — `straight_wire_domain`: bisect the coarse-resolution floor and guard it** ✅ *(step 1 2026-08-28
07:30 slot; step 2 2026-08-29 07:30; demoted ✅ → 🧪 by the 08-29 10:30 review under §4 clause 3 and restored by
step 2c, 2026-08-29 16:30. Commissioned 2026-08-26 18:00 review as owner of `EX-30` leg (root)'s finding. Full
narrative archived in `docs/planning/plan-archive.md`, entry «§7 GEO-22 full narrative — archived 2026-08-30 (weekly review)».)*
> * **Step 1 — measured negative:** the 2.5e-4 sweep of [0.008, 0.010] is **non-monotone on both geometries**
>   (example FAIL at 0.00875 / 0.00925 / 0.00975 / 0.01000, gate FAIL at 0.00875 / 0.00900 / 0.01000) and bit-identical
>   twice (`20260828T123115Z_GEO-22-step1-bisect.log`, `…123205Z_…-repeat.log`); 21 830 cells at 0.008. **No
>   `RESOLUTION_FLOOR` exists and none was written; `src/` untouched.** Ruling 08-28 10:30: raise-path wrap via
>   `GEO-23` step 2a (gate `test_geometry_failure_is_collective.py`, `20260828T170254Z`), allowlist rejected.
> * **Step 2 — size-field probe (leg D, no `src/`):** gmsh `Distance`/`Threshold` field on the wire surface reads
>   **18/18 OK, 0/18 fallbacks** vs leg C's 7 FAIL / 18 fallbacks (`20260829T123331Z_GEO-22-step2-sizefield.log`, 33 s);
>   leg C control bit-identical in its own process (`…123413Z_…-legC-control.log`); gate re-run 1 passed (`…123459Z`).
> * **Step 2c — the assert:** `tests/mesh/test_straight_wire_size_field_probe.py` patched **19 823 cells / 0
>   fallbacks**, unpatched **21 830 / 1**, **0.00% vs ±1%** at `-n 1` (`20260829T213132Z_…-step2c-n1.log`, 8 s) and `-n 2`
>   (`…213148Z_…-n2.log`, 7 s); perturbed reference reds on both ranks (`…213211Z`), restore green (`…213227Z`). * **Carry-forward (OPEN):** landing the size field would move `mag:1`'s 21 830 and the three ladder records — **that licence is the weekly review's**, and the known-issues entry stays OPEN on exactly that decision.

**`GEO-23` — the 0.11 "overlapping facets" family: classify, ladder, own** ✅ *(step 1 2026-08-28 09:00 slot;
ruled 10:30 review; step 2a 12:00, step 2b 13:30 ⇒ chunk closed 2026-08-28; commissioned 2026-08-27 03:00 review
from `OPS-26` step 2's four sites. Full narrative and both step-2 rubrics archived in `docs/planning/plan-archive.md`, entry «§7 GEO-23 full narrative — archived 2026-08-30 (weekly review)».)*
> * **Step 1 (8 windows, 318 s, `20260828T140041Z…141217Z`):** **all four sites fail at `-n 1`** — nothing is
>   partition-dependent; the two "rank-divergent" observations were log-interleave artifacts (withdrawn by measurement).
>   The deadlock is a **raise-path** property (rows 1/3/4 Status 124 at 120–121 s; `birdcage_port_domain`, already
>   wrapped, footers Status 1 in 5 s). Ladders monotone: `cylindrical_domain` 0.032 → 1 213 cells, `coil_phantom_domain`
>   0.024 → 5 464. In-process ladders read gmsh contamination (`IndexError`), not geometry. Dead `test_cylindrical_domain.py`
>   → one asserting test at 1e-9; `tests/mesh` collects 58.
> * **Step 2a (raise path, 12 windows / 72 s):** `_raise_geometry_failure_on_every_rank` (`io/mesh.py:30–61`) wraps
>   `straight_wire` / `cylindrical` / `coil_phantom` (+76 lines, zero deletions); the three deadlocking rows footer
>   **Status 1 in 2–3 s** at `-n 2` (`20260828T170311Z/170331Z/170347Z`, ≈ 50× cheaper); `mag:1` 21 830 cells and
>   `B(3 mm) = 6.666667e-05 T` unmoved (`…170414Z`); `GEO-21` control 1 passed / 36.76 s.
> * **Step 2b (sizing, 8 windows / 40 s):** `0.04 → 0.032` and `0.03 → 0.024` at the three call sites; all green at `-n 1`
>   and `-n 2` (`20260828T183106Z…183242Z`) with counts **1213 / 5464 exact (0.00% vs ±1%)**; no physics assertion moved; the three known-issues entries RETIRED. * **Carry-forward:** the fourth site, `test_birdcage_volumes_partition_the_box` on `birdcage_port_domain`, is **still red** — it is `GEO-21`'s open generator-continuum entry; re-home or reopen as step 3 is a review's call.

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
| `TH-13` | The degree-2 gradient-subspace injector: feed model or any `W_m ≫ W_e` fixture? — the discriminator `TH-12` step 3 named (commissioned 2026-08-23 weekly review; cheap fixtures only) | ✅ *(closed 2026-08-31 on step 2 — (A) holds at round-off, the injector is the degree-1-only `H¹₀`-only source projection; audited COMPLIANT 03:00 review. Follow-on **step 3a** — the matched projection, opt-in, loop fixture only — scoped 03:00 review, §9 item 1, **executed 2026-08-31 04:30 slot and 🟡**: both anchors met with 6–14 orders of margin (residue 1.298386e-02 / 1.045186e-01 → **8.109635e-17 / 1.790460e-16** vs ≤ 1e-8; gradient share of `W_e` 99.98% / 99.9997% → **4.6e-23 / 3.1e-21** vs ≤ 1e-6; `W_e` to 0.018% / 2.6e-4 % of record vs ≤ 2% / ≤ 1%), default path bit-identical on control (b) at **0.000e+00**, but one of the two owed regression re-runs — `test_coil_loading_degree2.py` — **could not be executed** (exit 124 meshing; new known-issues entry), so the coil identity tests' 1e-9 reds are unverified on this commit; the lumped-sheet coil drive is `project_source=False` and out of 3a's reach, see entry)* | standard |

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
`W_m ≫ W_e` fixture?** ✅ *(**closed 2026-08-31 on step 2's done-when: (A)
holds at both degrees and both frequencies at 1e-11-class round-off, (B)'s
shares recorded, and the known-issues degree-2 entry has its disposition —
the injector is the degree-1-only, `H¹₀`-only source projection, and the
original CLASS/FEED dichotomy is retired as §7's done-when says it is if (A)
holds.** The *fix* — the degree-/boundary-matched projection — is step 3, a
`src/` change a review prices and re-measures on the coil; it is not this
chunk. The step-1′ precondition assert stays a deliberate red on `main` per
the step-1′ bullet, and the two degree-2 coil identity tests stay failing at
the unloosened 1e-9 bound. Steps 1 and 1′ executed 2026-08-30, both negative
— step 1 missed its precondition at 10 MHz and read IN-BETWEEN; step 1′
measured the ω² rescope premise **refuted** (`W_e/W_m` is frequency-
independent on this fixture) and the degree-2 **saturation** confirmed, so the
cross-order ratio is the wrong observable; **step 2 rescoped 2026-08-30 18:00
review** onto a mechanism the review found by reading
`core/source_projection.py` — the drive projection is CG1 ∩ H¹₀ only, at any
solve degree and under the default PMC boundary — and pre-registered as the
gradient-projection identity, §9 item 2; readings below the two bullets;
step 2 not run; commissioned 2026-08-23 weekly review from
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
> * **Step-1 reading — NEGATIVE ON BOTH CLAUSES** *(2026-08-30,
>   `tests/validation/test_degree2_gradient_discriminator.py`,
>   `20260830T020301Z_TH-13-step1.log`, standard tier, 1 failed / 12 passed /
>   1 skipped, exit 1, **36 s** at `-n 2`, complex build)*. The fixture was
>   built as scoped — `POST-5` step 2's closed azimuthal loop on the smoke
>   box's own 1 405-cell mesh at 10 MHz, energies through step 3's imported
>   helpers, solver default gauge. **(i) The precondition failed:** degree-1
>   `W_e/W_m` = **1.952350e-02** against the pre-registered ≤ 1e-2, so the
>   fixture is *not* magnetically dominated and is not the missing cell of the
>   step-3 table; per the §7 clause the step stops there and the assert is
>   left failing on `main` rather than loosened. In hindsight the miss was
>   predictable to a factor of 1.5: `W_e/W_m ~ ω²` at fixed impressed current,
>   and the box's own 2.164348 at 127.74 MHz scales to 1.33e-2 at 10 MHz.
>   **(ii) The verdict is IN-BETWEEN:** cross-order move **5.156e+01×**,
>   between 10× and 1e3×; recorded, test skipped, no band invented in-slot.
>   **What did hold:** both step-3 controls reproduced to the digit on this
>   code path — smoke **1.155×** (2.164348 → 2.499688), sphere **1.015×**
>   (1.068190 → 1.052552) at the imported 1% band — and `|Im P|/Re P` =
>   0.000e+00 at both orders on the loop, so nothing drifted since
>   2026-08-19 and the in-between number is the fixture's, not a regression.
>   **The suggestive part:** degree 2 lifts the loop's `W_e` 63.7×
>   (5.621559e-19 → 3.579741e-17 J) while `W_m` moves 1.23×, landing
>   `W_e/W_m` at **1.006682** — the same O(1) equipartition smoke (2.50) and
>   sphere (1.05) already sit at, and nowhere near the coil's degree-2
>   **229**. **Arithmetic the pre-registration missed:** starting from
>   1.95e-2, a 1e3× move would have to reach `W_e/W_m` ≈ 20, so CLASS was
>   *unreachable* on this fixture before the run began — the bands and the
>   fixture were not compatible, which is the real defect in the step as
>   written. **Rescope for the review, not executed in-slot** (§7 pins
>   10 MHz): the same fixture at ≤ 7 MHz meets the precondition and at 1 MHz
>   reads ~2e-4, which leaves ~5e3× of headroom under equipartition so both
>   bands become representable. Nothing is fixed, no coil number moved, the
>   known-issues degree-2 entry stays open with this reading appended.
> * **Step 1′ — the ω² rescope: the same fixture at 1 MHz (ruled 2026-08-30
>   02:15 weekly review; written by the 10:30 daily review from the
>   step-1 reading, the weekly session having died before writing it).**
>   Standard, complex, `-n 2`, `main`, **no `src/` change**. Add a second
>   parametrised row to `test_degree2_gradient_discriminator.py` at
>   `LOOP_FREQUENCY_HZ = 1.0e6` on the same 1 405-cell mesh and the same
>   imported drive / energy forms; keep the 10 MHz row as a **recorded**
>   reading (its precondition assert becomes a printed record with the
>   1.952350e-02 figure in-comment, so `main`'s deliberate red retires
>   with this step — the 10 MHz fixture is *known* not to be magnetically
>   dominated, asserting it again gates nothing). **Pre-registered
>   arithmetic:** `W_e/W_m ~ ω²` at fixed impressed current, so from
>   1.952350e-02 at 10 MHz the 1 MHz row reads ≈ **1.95e-4** — inside the
>   unchanged `MAGNETIC_DOMINANCE_MAX = 1e-2` by 50×, and a 1e3× CLASS move
>   lands at ≈ 0.2, *below* the O(1) equipartition every fixture sits at, so
>   both bands are representable for the first time. **Anchors, asserted:**
>   degree-1 `W_e/W_m` at 1 MHz ≤ 1e-2 **and** within 2× of the ω²
>   prediction 1.95e-4 (the fixture behaves as scaled — if it does not, the
>   fixture changed, not the physics); the step-3 controls reproduce smoke
>   **1.155×** / sphere **1.015×** at the imported 1% band; the `POST-5`
>   **1.199162e-06 W** smoke anchor at rtol 1e-6. **Verdict bands, unchanged:**
>   cross-order `W_e/W_m` ≥ **1e3×** ⇒ CLASS, ≤ **10×** ⇒ FEED, in between
>   recorded with no band invented. **Negative control:** the 10 MHz row's
>   **5.156e+01×** must reproduce at rtol 1e-3 (same code path, same
>   fixture — a moved 10 MHz move means the run is not comparable). **Cost:**
>   step 1 was 36 s; one more degree-1 + degree-2 pair on 1 405 cells ≈
>   **≤ 60 s**, `-k 30 300`. **Traps:** as step 1 (complex build, no ordering
>   comparison in the drive callable, 0-byte FFCx stubs); the loop's degree-2
>   `W_e` lifted 63.7× at 10 MHz and landed exactly at equipartition — if the
>   1 MHz row *also* lands at `W_e/W_m ≈ 1` at degree 2 the contamination
>   **saturates** and "cross-order move" is the wrong discriminant, which is
>   itself the finding (record it, it sends the chunk straight to step 2).
>   **Scope:** step 1′ only; step 2 scoped from the verdict; no coil number
>   moves; §10's production-order decision is the weekly review's to revisit
>   with the verdict on record. **Negative result:** an in-between ratio or
>   a saturated degree-2 `W_e/W_m ≈ 1` is recorded on this entry and the
>   known-issues degree-2 entry, stop.
> * **Step-1′ reading — THE ω² PREMISE IS REFUTED; `W_e/W_m` IS
>   FREQUENCY-INDEPENDENT ON THIS FIXTURE** *(2026-08-30 15:00 slot,
>   `20260830T200543Z_TH-13-step1prime-final.log`, same module, standard tier,
>   1 failed / 13 passed / 1 skipped, exit 1, **32 s** at `-n 2`, complex
>   build; first window `20260830T200305Z_TH-13-step1prime.log`, 36 s, same
>   numbers)*. The 1 MHz row was built exactly as scoped — same 1 405-cell
>   mesh, same closed azimuthal drive, same imported energy forms, only
>   `LOOP_FREQUENCY_HZ` moved. **Predicted 1.952350e-04, measured
>   1.926692e-02**: **98.7×** the pre-registered prediction and **0.9869×**
>   the 10 MHz reading across a full decade of ω. The energies themselves
>   barely move — `W_e` 5.621559e-19 → 5.544787e-19 J, `W_m`
>   2.879380e-17 → 2.877879e-17 J, dissipated power
>   1.139571e-09 → 1.124008e-09 W — so both `E` and `H` are essentially
>   frequency-independent here and the quasi-static `E ~ ωA`-at-fixed-
>   impressed-current argument (used by step 1's hindsight paragraph *and* by
>   this rescope) **does not describe this solve**; it should not be reused
>   anywhere in this family without being measured first. **The precondition
>   therefore fails again** (1.926692e-02 vs the unmoved ≤ 1e-2): frequency is
>   not the knob that makes this fixture magnetically dominated, the fixture is
>   still not the missing cell of step 3's table, and per this entry's own
>   clause the step stops there with the assert left red rather than loosened —
>   **`main`'s deliberate red moves from the 10 MHz row to the 1 MHz row; it
>   does not multiply, and the ≤ 1e-2 / 10× / 1e3× bands are untouched.** The
>   ω²-prediction clause, pre-registered here as an assertion, is **demoted to
>   a printed record** with the measurement in-comment at
>   `OMEGA_SQUARED_PREDICTED_RATIO` (MAG-10/MAG-15 precedent): a second red on
>   a premise measurement has already killed gates nothing the precondition
>   does not. **The saturation trap this bullet named fired:** degree-2
>   `W_e/W_m` at 1 MHz is **1.010649** against 10 MHz's 1.006682, cross-order
>   move **5.246e+01×** against 5.156e+01× — the contamination saturates at
>   O(1) equipartition *independently of the degree-1 baseline*, so
>   **"cross-order move in `W_e/W_m`" is the wrong discriminant** and no
>   frequency will make it the right one. That is the finding, and it retires
>   the frequency route rather than motivating a third rescope. **Negative
>   controls, all green:** the 10 MHz row reproduced step 1 at rtol 1e-3 on
>   both its degree-1 ratio and its move; step 3's smoke **1.155×** / sphere
>   **1.015×** at the imported 1% band; the `POST-5` anchor **1.199162e-06 W**
>   at rtol 1e-6 (newly asserted here); `|Im P|/Re P` = 0.000e+00 on all four
>   loop solves. Nothing fixed, no coil number moved, known-issues entry
>   updated and still open. **For the review:** the observable, not the
>   fixture, is what is wrong — go to **step 2** (`‖∇φ‖/‖E‖`, the absolute
>   gradient content), whose pre-registered anchors do not depend on a
>   magnetically-dominated fixture at all.
> * **Step 2 — RESCOPED 2026-08-30 18:00 review: the gradient-projection
>   identity on the loop fixture, both orders.** *(Supersedes the
>   "`‖∇φ‖/‖E‖` at both orders" framing, retired before it ran: that ratio
>   is bounded by 1, and a uniform or quasi-static conduction field is
>   itself a gradient — the sphere control would read ≈ 1 at both orders
>   and say nothing — so it cannot separate physical from spurious gradient
>   content.)* **What the review found by reading, not measuring:**
>   `core/source_projection.py::remove_gradient_content` (the
>   `project_source=True` default every solve in this family uses) removes
>   the drive's gradient content against **`("Lagrange", 1)` ∩ H¹₀ only,
>   at every solve degree and under every boundary mode**
>   (`source_projection.py:108`, `:134–136`). A degree-2 N1curl test space
>   contains `∇(Lagrange₂) ⊋ ∇(CG1)`, and this fixture's default `NATURAL`
>   (PMC) boundary admits `∇q` for **all** `q ∈ CG`, not only `H¹₀` — so the
>   projected `J′` keeps a gradient residue in exactly the directions the
>   solve tests, and the discrete system answers it *exactly*: testing the
>   assembled weak form with `v = ∇ψ` (curl ∇ψ = 0) leaves
>   `−(k² E_h, ∇ψ) = (load_factor · J′, ∇ψ)` for every admissible `ψ`, i.e.
>   **the `∇Lagrange_p`-projection of `E_h` equals the `∇Lagrange_p`-
>   projection of `J′` times a constant fixed by the form's own
>   coefficients** (homogeneous `k² = ω²μ₀ε₀ε_r − iωμ₀σ` on this box;
>   `load_factor = −iωμ₀`, `time_harmonic.py:448`). With `σ ≫ ωε` (0.7 vs
>   0.0434 S/m at 10 MHz) that constant's magnitude is `1/|σ + iωε|` —
>   **frequency-flat**, which is the step-1′ reading: the "quasi-static
>   `E ~ ωA`" argument failed because the dominant `E` is Ohm's-law response
>   to the residue, not induction. A derivation, pre-registered here so the
>   run can refute it.
>   **Build:** in `test_degree2_gradient_discriminator.py`, for each of the
>   four existing loop solves (degrees 1/2 × 10/1 MHz — no new physics
>   solves), two Laplace projections in **degree-matched** Lagrange,
>   `(∇χ, ∇q) = (E_h, ∇q)` and `(∇φ, ∇q) = (J′_used, ∇q)`, with the
>   Dirichlet set the N1curl boundary mode actually implies (`NATURAL` ⇒
>   none; PEC ⇒ `H¹₀` — read it off `build_boundary_conditions`, do not
>   assume), `J′_used = solver._projection.current` (the whole-domain UFL
>   expression the load integrates, `time_harmonic.py:461`), and the
>   constant `c` read from `load_factor` and the form's mass coefficient
>   rather than from theory.
>   **Anchors:** **(A, exact identity)** `‖∇χ − c·∇φ‖ / ‖∇χ‖ ≤ 1e-6` at
>   **both** degrees and both frequencies (direct MUMPS solves; expect
>   ~1e-10) — the pre-registered discriminant: if it holds, every joule of
>   degree-2 electric energy the known-issues entry calls "spurious" is the
>   drive's *unremoved* gradient residue divided by `(σ + iωε)`, and no
>   free "ungauged null-space mode" story survives (`k² ≠ 0` pins it).
>   **(B, the mechanism's size, printed not gated):** `‖P_∇₂J′‖/‖P_∇₁J′‖`,
>   and `ε₀ε_r‖∇χ‖²/2` as a share of the measured `W_e` at each degree —
>   under (A) predicted to carry the 63.7× degree-2 lift (share ∈ [0, 1];
>   no band invented). **(C, in-run controls):** `POST-5` **1.199162e-06 W**
>   at rtol 1e-6, the four loop rows reproducing steps 1/1′ at rtol 1e-3,
>   `|Im P|/Re P` = 0. **Negative controls:** (A) re-read with `c`
>   deliberately off by 10% fails at ≥ 1e-1 (the `PORT-12` step-2
>   load-bearing-probe precedent, reverted before commit); one extra
>   **unprojected** degree-1 solve (`project_source=False`, ~8 s) reads
>   `‖P_∇₁J‖/‖J‖` visibly above the projected `‖P_∇₁J′‖/‖J′‖` — the
>   projection must be seen doing something (`PORT-1` step 2d/2e precedent,
>   8.175e-06 → 0). **Cost:** the module is 32 s; four Laplace pairs on
>   1 405 cells and one extra solve add ≤ 30 s — **≤ 90 s**, standard,
>   `-n 2`, `-k 30 300`, complex + `FEM_EM_REQUIRE_COMPLEX=1`,
>   `tests/environment` first. **Traps:** `ufl.inner` conjugates the test
>   function — same convention on both sides of (A);
>   `create_connectivity(tdim−1, tdim)` before `exterior_facet_indices`;
>   `assemble_scalar` is rank-local — reduce every norm; pin
>   `quadrature_degree` on the `SpatialCoordinate`-bearing forms (`POST-5`
>   step 1); the Lagrange space's Dirichlet set must be the one the solver
>   applied; leave the precondition assert red as it is (not this step's to
>   retire). **Scope:** loop fixture only, **no `src/` change** — the
>   degree-/boundary-matched projection is **step 3**, scoped by a review
>   from (A)/(B)'s numbers and then priced on the coil; nothing here
>   touches the coil's 229× or the 1e-9 identity tests directly.
>   **Negative result:** (A) failing at either degree is a formulation
>   finding — the discrete gradient equation is not what the form says —
>   record on the degree-2 known-issues entry, stop; (B) reading
>   `‖P_∇₁J′‖/‖J′‖ ≫ 1e-6` under a PEC mode is a projection-space finding,
>   record, stop. Never loosen the precondition or invent a verdict band.
> * **Step-2 reading — (A) HOLDS AT BOTH DEGREES AND BOTH FREQUENCIES; THE
>   INJECTOR IS THE DEGREE-1-ONLY, `H¹₀`-ONLY SOURCE PROJECTION** *(2026-08-31
>   21:00 slot, `20260831T021154Z_TH-13-step2.log`, same module, standard tier,
>   1 failed / 15 passed / 1 skipped, exit 1, **32 s** at `-n 2`, complex
>   build)*. Built as scoped: no new physics solve — the four existing loop
>   solutions each got two degree-matched Laplace projections, `J′_used` taken
>   from `solver._projection.current` (the expression the load integrates), the
>   Dirichlet set read off `build_boundary_conditions` (`NATURAL` ⇒ none, so a
>   single dof is pinned to fix the additive constant, which leaves `∇χ`
>   untouched and is shared by both potentials of a pair).
>   **(A):** `‖∇χ − c∇φ‖/‖∇χ‖` = **2.970e-12 / 2.640e-11** at 1 MHz degrees
>   1/2 and **3.697e-13 / 2.586e-12** at 10 MHz, against the pre-registered
>   ≤ 1e-6 — round-off, as the derivation predicted. `c` was read off the
>   form's coefficients and reproduces `−1/(σ + jωε₀εᵣ)` to
>   `|c|·|σ + jωε| = 1.000000000`; it moves only 1.425834 → 1.428544 across a
>   decade of ω, so **step 1′'s frequency-flatness is now explained, not just
>   observed**. **Load-bearing probe** (`PORT-12` step-2 precedent, kept as an
>   assertion rather than run-and-reverted): `c` mistuned by 1.1× moves the
>   residual to **1.000e-01** on all four rows, so (A) is not vacuous.
>   **(B), recorded, no band invented:** the gradient part of `E` carries
>   **99.98%** of the measured `W_e` at degree 1 and **99.9997%** at degree 2
>   (1 MHz; 98.24% / 99.97% at 10 MHz), and `‖P_∇₂J′‖/‖P_∇₁J′‖` = **8.049884**
>   at *both* frequencies — whose square **64.8** is step 1's 63.7× degree-2
>   `W_e` lift. The degree-2 "explosion" is therefore, to four digits, the
>   drive's **unremoved** gradient residue answered through Ohm's law at
>   `1/|σ + jωε|`; no free ungauged null-space mode survives (`k² ≠ 0` pins
>   it), and the ungauged-second-order-gradient-space story is superseded.
>   **Projection control** (`PORT-1` step 2d/2e precedent): one extra
>   `project_source=False` degree-1 solve reads `‖P_∇₁J‖/‖J‖` =
>   **7.589863e-02** against the projected **1.298386e-02** — the projection
>   removes 5.8× of the CG1 content and leaves precisely the non-`H¹₀` part a
>   PMC box still tests. **(C) in-run controls all green** (they are the
>   module's existing asserts): the `POST-5` **1.199162e-06 W** anchor at rtol
>   1e-6, steps 1/1′ reproduced at rtol 1e-3 (10 MHz 1.952350e-02 / 5.156e+01×;
>   the 1 MHz row and step 3's smoke 1.155× / sphere 1.015× unmoved),
>   `|Im P|/Re P` = 0.000e+00 on all five loop solves.
>   **Trap paid, recorded for the family:** holding the solves' meshes and
>   PETSc objects alive in a module-scoped fixture ran every assertion green and
>   then **deadlocked in teardown** — PETSc destruction is collective and Python
>   collected the handles in rank-dependent order (first window
>   `20260831T020528Z_TH-13-step2.log`, killed at the 300 s ceiling, identical
>   numbers). The fix is structural: each row's projections are computed inside
>   the solve helper and only floats escape, so both ranks free at the same
>   point in the program. **No `src/` change**, no coil solve, no coil number
>   moved; the step-1′ precondition red stays on the 1 MHz row (a deliberate red
>   held per this entry, not step 2's to retire), and the two degree-2 identity
>   tests stay failing at the unloosened 1e-9 bound.
> **Done-when (rescoped 2026-08-30 18:00):** step 2's (A) executed at both
> degrees with (B)'s shares recorded; the known-issues degree-2
> complex-power entry gets its disposition — **(A) HOLDS** ⇒ the injector is
> the **degree-1-only, `H¹₀`-only source projection**, common to every
> drive (the CG1-projected coil drive's residue lives in `∇Lagrange₂`; the
> unprojected port sheets' residue is their full discrete divergence,
> closed by the phantom's σ — which is physics), and the next chunk is the
> degree-/boundary-matched projection (step 3, then re-measured on the coil
> where `TH-12` step 2 read 229×); **(A) FAILS** ⇒ a formulation defect,
> priced as a gauged/`H¹`-augmented second-order chunk; §10's
> production-order decision is revisited by the weekly review with the
> verdict on record. The original CLASS/FEED dichotomy is retired — if (A)
> holds, both fixtures inject through the same mechanism at a size set by
> their drive's residue, and the question was never which fixture.
> * **Step 3a — the degree-/boundary-matched projection, opt-in, measured on
>   the loop fixture (scoped 2026-08-31 03:00 review; priced from
>   `core/source_projection.py:108,134–136` and `core/time_harmonic.py:449–461`;
>   the chunk is ✅ on step 2 and this step is a follow-on `src/` change, so it
>   carries its own done-when and does not reopen the chunk).** Standard tier,
>   complex build, `-n 2`, `main`, ≤ 90 s (module 32 s + four extra loop
>   solves at ~1 s each on 1 405 cells), `timeout -k 30 300`,
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first.
>   **Build:** `remove_gradient_content` gains two keyword arguments with
>   defaults that reproduce today's behaviour **bit for bit** — `degree: int
>   = 1` (the Lagrange degree of `ψ`, `:108`) and `pin_exterior: bool = True`
>   (the `H¹₀` Dirichlet set, `:134–136`; `False` leaves `ψ` unpinned and fixes
>   the additive constant by pinning one dof, exactly as step 2's projection
>   helper did — lift that code, do not re-derive it). `TimeHarmonicSolver.solve`
>   accepts `project_source="matched"` beside `True`/`False`: `degree =
>   self.degree`, `pin_exterior = (build_boundary_conditions()[1] is
>   PEC_ZERO_TANGENTIAL_A)`. Nothing else in `src/` changes; `True` stays the
>   default and every caller that passes `True`/`False` assembles the same load
>   it does today.
>   **Anchors (pre-registered from step 2's (A) and (B), asserted in code):**
>   (i) projection exactness — under `"matched"` the degree-p Laplace projection
>   of `J′_used` against the *matched* test space reads `‖P_∇ₚJ′‖/‖J′‖ ≤ 1e-8`
>   at degrees 1 and 2, 1 and 10 MHz (today's degree-1 figure is 1.298386e-02,
>   the non-`H¹₀` part; degree 2's is 8.049884× that); (ii) the mechanism's
>   prediction — with the residue gone, (A) says `P_∇ₚE_h = c·P_∇ₚJ′ ≈ 0`, so
>   the gradient share of `W_e` falls from **99.98% / 99.9997%** to **≤ 1e-6** at
>   both degrees, and the absolute `W_e` falls to **≤ 2%** of its on-record
>   value at degree 1 (5.621559e-19 J; the recorded non-gradient share is 0.02%,
>   margin 100×) and **≤ 1%** at degree 2 (3.579741e-17 J; recorded share
>   3e-6, margin ~3 000×) — the bands are derived from (B) with stated margins,
>   not tuned to a run. **Recorded, not gated:** the new degree-2 / degree-1
>   `W_e` ratio (was 63.7×; what remains is the solenoidal electric energy of
>   an unconverged 1 405-cell loop, and nobody has a prediction for its
>   cross-order move — do not invent one), `W_e/W_m` at both degrees (the
>   step-1 precondition is **not** re-asserted under `"matched"` — it stays a
>   deliberate red on the default path per the step-1′ bullet), and `|Im
>   P|/Re P`.
>   **Negative controls:** (a) the default path is untouched — the module's
>   existing asserts (`POST-5` **1.199162e-06 W** at rtol 1e-6, the steps 1/1′
>   rows at rtol 1e-3, (A)'s four residuals, the **8.049884** ratio at rtol
>   1e-6) all reproduce on `project_source=True`; (b) `"matched"` at degree 1
>   with `pin_exterior=True` forced is bit-identical to `True` (same `ψ`, same
>   load — assert the `W_e` at rtol 1e-12), so the new arguments are the
>   *only* thing that moves the number; (c) the load-bearing check for (i): the
>   `True` path's `‖P_∇₂J′‖/‖J′‖` printed beside `"matched"`'s, ≥ 1e3× apart.
>   **Owed re-runs for the `src/` change** (defaults preserved, so these are
>   regression checks, not new measurements): the modules that import the
>   projection or assert its records —
>   `tests/validation/test_dodd_deeds_projected_drive.py` and
>   `tests/validation/test_coil_loading_degree2.py` (the two degree-2 coil
>   identity tests stay **failing** at 1e-9 exactly as before — a changed
>   reading there means the default path moved, which is a defect); the
>   `ports:4` example does **not** need a re-run (its drive is
>   `project_source=False`, `ports/lumped.py:429`).
>   **Traps:** the step-2 teardown deadlock — compute every projection inside
>   the solve helper and let only floats escape; `ufl.inner` conjugates the
>   test function; `create_connectivity(tdim-1, tdim)` before
>   `exterior_facet_indices`; the one-dof pin under `pin_exterior=False` must be
>   the same dof on both potentials of a pair and rank-safe (pin the globally
>   lowest-numbered dof, on the rank that owns it); pin `quadrature_degree`;
>   no ordering comparison on complex operands.
>   **Scope boundary — read before claiming anything about the coil.** The
>   lumped-sheet birdcage drive is a *surface* term with `current_density=None`
>   and `project_source=False` (`ports/lumped.py:429`), so the matched
>   projection **cannot reach the coil's 229× at all**; the coil's residue is the
>   sheets' full discrete divergence closed by the phantom's σ (the done-when
>   paragraph above), and whether *that* should be removed, and how, is a
>   formulation question for the weekly review (a possible step 3b), not this
>   step. The known-issues degree-2 complex-power entry therefore **stays
>   open** after 3a, and the two coil identity tests stay failing. 3a gates
>   only: "the projection, matched, removes the residue it was built to
>   remove, and the mechanism's prediction for the loop fixture's `W_e` holds".
>   **Negative result:** (i) failing is a bug in the new code (the projection
>   is a Laplace solve — its own residual is the check), fix in-slot; (ii)
>   failing with (i) green is a **finding** — the gradient part of `E_h` is
>   not set by the drive's residue alone, (A)'s reading was incomplete —
>   record both numbers in the known-issues entry, keep the assert, stop; never
>   widen a band.
> * **Step-3a reading — BOTH ANCHORS MET WITH 6–14 ORDERS OF MARGIN; ONE OF THE
>   TWO OWED REGRESSION RE-RUNS COULD NOT BE EXECUTED** 🟡 *(2026-08-31, 04:30
>   implementer slot, `20260831T094852Z_TH-13-step3a-final.log`, same module,
>   standard tier, 1 failed / 18 passed / 1 skipped, exit 1, **37 s** at `-n 2`,
>   complex build)*. Built exactly as scoped: `remove_gradient_content` gains
>   `degree: int = 1` and `pin_exterior: bool = True` (the `False` branch pins
>   the globally lowest-numbered dof, lifted from step 2's helper), and
>   `TimeHarmonicSolver.solve` accepts `project_source="matched"` beside
>   `True`/`False`, setting `degree = self.degree` and `pin_exterior` from
>   `selected_bc is PEC_ZERO_TANGENTIAL_A`. Nothing else in `src/` moved.
>   **(i)** `‖P_∇ₚJ′‖/‖J′‖` under `"matched"` reads **8.109635e-17** (degree 1)
>   and **1.790460e-16** (degree 2), identical at both frequencies, against the
>   pre-registered ≤ 1e-8 — it is the matched Laplace solve's own residual, as
>   the scoping said it would be. Control (c) is **1.601e+14×** / **5.838e+14×**
>   of separation from the default path's 1.298386e-02 / 1.045186e-01, against
>   the ≥ 1e3× bar. **(ii)** the gradient share of `W_e` falls from 99.98% /
>   99.9997% to **4.618447e-23** / **3.109722e-21** at 1 MHz (4.390171e-25 /
>   2.738225e-23 at 10 MHz) against ≤ 1e-6, and `W_e` collapses to
>   **9.856327e-23 J** (degree 1, 0.018% of the 5.544787e-19 J record) and
>   **9.349492e-23 J** (degree 2, 2.6e-4 % of 3.592428e-17 J) against ≤ 2% /
>   ≤ 1%. Each row is banded against the record from **its own** frequency:
>   §7 pre-registered 5.621559e-19 / 3.579741e-17, which are step 1′'s 10 MHz
>   readings, and the 1 MHz pair sits 1.4% / 0.4% away (`W_e` is frequency-flat
>   here — step 1′'s own finding), so all four rows are gated with the two
>   pre-registered fractions unchanged. **Recorded, not gated, as scoped:** the
>   matched degree-2/degree-1 `W_e` ratio is **9.485777e-01×** where the default
>   path's was 63.7× — the 63.7 was the residue, and what remains is
>   cross-order-flat; `W_e/W_m` is 3.424858e-06 / 2.630270e-06 at 1 MHz (the
>   step-1 precondition is **not** re-asserted under `"matched"`); `|Im P|/Re P`
>   = 0.000e+00 on every matched row.
>   **Negative controls, all green.** (a) every step-1/1′/2 assertion reproduces
>   to the digit on the default path — (A)'s four residuals 2.970e-12 /
>   2.640e-11 / 3.697e-13 / 2.586e-12, the mistuned probe 1.000e-01,
>   `‖P_∇₂J′‖/‖P_∇₁J′‖` = 8.049884, the unprojected control 7.589863e-02 vs
>   1.298386e-02, `POST-5` 1.199162e-06 W, the steps 1/1′ rows. (b) on the PEC
>   box at degree 1, where `"matched"` *is* `True`, the two solves read `W_e` =
>   5.995936714066138e-23 J and 5.995936714066138e-23 J — **0.000e+00
>   relative**, so the new keywords are default-preserving as an identity, not
>   as an agreement. The one red is the step-1′ precondition at
>   **1.926692e-02** on the 1 MHz row, unmoved and deliberate.
>   **Why 🟡 and not ✅ — the owed re-run that did not run.**
>   `test_dodd_deeds_projected_drive.py` re-ran green (**15 passed / exit 0 /
>   79 s**, `20260831T093558Z_TH-13-step3a-dodd-regression.log`, matching its
>   2026-08-27 record). `test_coil_loading_degree2.py` **did not**: at `-n 8`
>   under `timeout -k 30 570` it spent the entire ceiling inside
>   `test_the_mesh_is_the_mat6_step3_baseline` and was killed at exit 124
>   (`20260831T093807Z_TH-13-step3a-coil-degree2-regression.log`, 571 s), where
>   the *whole* module including the 61.94 GiB degree-2 factorization took 543 s
>   on 2026-08-18. The mesh alone now exceeds 560 s — a regression in its own
>   right, filed to known-issues with `OPS-18`'s gmsh 4.15.2 as the untested
>   suspect and the `probe` mode noted as no cheaper (it builds the same mesh
>   first). Per §5.1 the ceiling was **not** raised and the case has no smaller
>   variant an implementer may choose in-slot, so the claim "the two degree-2
>   coil identity tests still fail at 1e-9 exactly as before" is **unverified on
>   this commit**; the container was healthy afterwards (no stray `python3`,
>   `memory.max` 137438953472). What 3a *does* rest on for the default path is
>   control (b)'s bit-identity, the dodd-deeds module, and a diff whose default
>   branch is the old code verbatim.
>   **Scope held:** the coil is untouched — `ports/lumped.py:429` still drives
>   with `project_source=False`, no caller was switched to `"matched"`, the
>   known-issues degree-2 entry stays open with 3a's disposition on it, and
>   whether a *sheet* drive's residue should be removed at all remains step 3b,
>   a formulation ruling for the weekly review.

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
| `PORT-11` | Lumped-sheet ports on the gapped birdcage at 64 MHz (then 128): `PORT-9`'s three gates in the displacement-current regime — §10 subgoal 2b; serial on `PORT-9` ✅ (commissioned 2026-08-23 weekly review) | ✅ **2026-08-26 on step 2's three gates at 64 MHz** (`test_port_birdcage_larmor_gate.py`, `17 passed in 177.48s` at `-n 2` on the complex build, `20260826T110434Z_PORT-11-step2.log`: reciprocity **2.581325834e-14** vs 1e-3, `σ_max(S)` **0.999721388** ≤ 1 + 1e-9 with max column power sum 0.804704664, C4 class spreads **0.0573 / 0.0599 / 0.0370%** vs (iii′)'s 0.5% at a pooled-vs-worst separation of 671.0527× — every band imported from the `PORT-9` modules, none moved. Twelve driven solves on three rungs, one knob each: the in-run 10 MHz rung reproduces leg (d)'s recorded 4×4 to **1.158e-10** vs the pre-stated 1e-6 and leg (d0)'s column to 2.568e-10, and the 22.5° displaced rung at 64 MHz breaks (iii′) on self **12.8947%** / adjacent **27.7509%** while (i) holds at 1.252073140e-15. Consumer `test_port_birdcage_leg_offset_sweep.py` re-run green on every closing digit after its rung builder took a `frequency_hz` parameter, `5 passed in 103.82s`. **No resonance, tuning or absolute-accuracy claim. **Step 3 closed the chunk's last step 2026-08-26 at 128 MHz** — the same three gates on the same frozen mesh with one constant changed: reciprocity **7.030990825e-15**, `σ_max(S)` **0.998974779** (max column power sum 0.861668762), class spreads **0.1012 / 0.0916 / 0.0654%** vs 0.5% at a 576.9483× separation, with the pre-gate resolution rule cleared **by measurement** (phantom loss tangent 0.9002 — displacement-dominated — cells/λ **12.5024** vs the pre-stated floor of 10, cells/δ 5.1845 vs 2.0), the 10 MHz control reproducing leg (d)'s 4×4 to 1.158e-10 and the 22.5° displaced rung breaking (iii′) on self 16.7006% / adjacent 34.6556% while (i) holds at 1.837477555e-15; `18 passed in 197.85s` (`20260826T213414Z_PORT-11-step3.log`, Status 0, 201 s), consumer `16 passed in 130.04s`. `PORT-11` now carries **both** Larmor frequencies**) *(**step 1 done 2026-08-25** — the 64 MHz solve exists and is **affordable**: one lumped-sheet solve on the `GEO-19` step-B mesh at ratio 1.000000 of the 116 085 record, priced **9.49 / 6.36 s** across two in-slot runs against the 10 MHz leg's 6.50–6.56 s on the same mesh — MUMPS mesh-bound as predicted, so step 2's 4×4 prices at ~26 s mesh + 4 solves ≈ **55–65 s, standard tier, not heavy**. Summed `ru_maxrss` **1.82 GiB**. **The stop rule clears**: phantom cells/δ **5.9213** against the pre-stated floor of 2.0 (δ = 1.159804e-01 m from the full lossy-medium propagation constant, loss tangent 1.8004 — not the good-conductor approximation), cells/λ 21.89 in the phantom and 496.16 in air. **Anchor passed**: the 10 MHz leg reproduces leg (d0)'s recorded column to a worst **2.568e-10** against the pre-stated 1e-6 band, so the frequency is the only knob turned. No gate claim at 64 MHz — step 2 **commissioned 2026-08-26 03:00 review, §9 item 2**, standard tier at step 1's price, gates as the `PORT-9` modules assert them today — see the prose entry; **executed 2026-08-26, all three green**)* | heavy (probe first; **step 2 measured and ran standard**) |
| `PORT-12` | The two-torus gap-route record drifts with rank width on an already-plumbed fixture: `tests/validation/test_port_lumped_two_torus.py` reads gap ratio **0.894141** (= `STEP1_GAP_RATIO_RECORD`) at `-n 2` and **0.894274** at `-n 12` — 1.33e-04 against the 1e-4 `REPRODUCTION_BAND` — at **184 176** cells both, `Im Z12` 1.110303775 → 1.110469250, four other tests green; a *solved* line integral, not a facet reconstruction. Step 1: the `-n 4` / `-n 8` rungs to classify the drift (monotone solve-side vs. a jump on the gap route only), no band moved; step 2 is the weekly review's width-qualification call on that table (found by `GEO-24` step 1b as its failed negative control; commissioned 2026-08-29 03:00 review; known-issues 2026-08-29) | ✅ *(**step 1 ✅ 2026-08-29, 12:00 slot** — the four-width table is measured in three windows / **189 s** at `c4630ed`, complex, `FEM_EM_REQUIRE_COMPLEX=1`, `-s`, `-k 30 300`, one width per window, **no code change in the slot**: env gate `11 passed` / 21 s, then `-n 4` (87 s) and `-n 8` (81 s), each `1 failed, 4 passed` / Status 1 on the same reproduction assert. Logs `20260829T1700…–1702…Z_PORT-12-step1-*`. **The pre-stated question was shape, and the answer is: an evaluation-path effect on the gap route alone, non-monotone in width — not a solve-side drift.** Gap ratio **0.894141** (`-n 2`, = record) → **0.894274** (`-n 4`, +1.33e-04) → **0.894347** (`-n 8`, +2.06e-04) → **0.894274** (`-n 12`, +1.33e-04): `-n 8`, not `-n 12`, is the worst width, so there is no "more partitions ⇒ more drift" law and the monotone-solve-side candidate is **excluded**. The exclusion is positive, not inferential: the **lumped route reads the same solved field through the sheet's own law and is flat to 2e-09** at all four widths (`Im Z12(lumped)` 1.029281338 / …337 / …336 / …338; `I_sheet` −4.122422e−08−1.000166e−06j at every width), and the step-2 *surface* read `mean E.yhat over the sheet` is **bit-identical to every printed digit at all four widths** (shadow −2.958541e+00−7.177866e+01j, fringe +8.607682e-03−1.009219e-02j, ratio 0.000185) — the solved field is width-independent to ~1e-9, five orders below the gap route's motion. Cross-route tracks the gap route (7.743060e-02 / 7.754834e-02 / 7.761484e-02 / 7.753298e-02) as it must, being derived from it; the path/projection residual is likewise non-monotone (0.0689 / 0.0632 / 0.0662 / 0.0836 pp). Sub-shape for the root-cause hunt: **`Re V_gap` *is* monotone** (1.365256733e-02 → 1.368962224e-02 → 1.370291038e-02 → 1.373904726e-02, 6.5e-03 relative across the four widths) while `Im V_gap` is not. **Pre-stated negative control held:** every reconstruction digit identical at all four widths — 184 176 cells, sheet 212 **1583 owned facets**, meshed/CAD area **1.000000000000**, `w` 1.040000000e-02 m, `h` 1.395505060e-02 m, `w/h` 0.745249896, out-of-plane spread 0.0e+00 m, gap volume **1.000000000000** — so this is **not** the `GEO-24` class of defect on a plumbed fixture, and the module's own volume/area identity asserts (1e-9) passed at both new widths. Full table in the known-issues entry. **Nothing loosened, no band moved, no record re-written, no width qualified** — that is step 2's, and step 2 is the 2026-08-30 weekly review's: with the drift non-monotone and confined to one route, the "solver-side fix" option in the original framing is off, leaving (i) width-qualify `REPRODUCTION_BAND` as a `-n 2` statement, (ii) a pre-registered parallel band ≥ 2.1e-04, or (iii) a commissioned root-cause step on the line integral's partition crossing)* ***step 2 ✅ 2026-08-30, 13:30 slot — CHUNK CLOSED, known-issues entry RETIRED.** The 02:15 weekly review's ruling (option (i) with a bounded envelope) is implemented in `tests/validation/test_port_lumped_two_torus.py`, **tests only, no `src/` change**: three windows / **310 s** at `cc18435`, complex, `FEM_EM_REQUIRE_COMPLEX=1`, `-s`, `-k 30 300`, `tests/environment` first in every window. `REPRODUCTION_BAND` stays 1e-4 and its comment now states it is a **`-n 2` record** (with step 1's four-width table inline); a new pre-registered **`PARALLEL_DRIFT_ENVELOPE = 3.0e-4`** is the band `test_step_1_measurements_reproduce` uses when `comm.size > 2`, printing each measured drift; and a new sixth test, `test_the_lumped_route_is_width_flat`, asserts `Im Z12(lumped)` = **1.029281338** Ω at rtol **1e-8**. **The pre-stated negative control was run first and held:** `-n 8` on unpatched `main` footered **Status 1**, `1 failed, 15 passed` / 105 s (`20260830T183101Z_PORT-12-step2-control-n8-main.log`) on `gap ratio: 0.894347 … moved by 2.06e-04, above 1e-04`. **Every anchor met on the patched tree:** at `-n 8` — the worst width — **17 passed** / Status 0 / 103 s (`…183340Z_…-patched-n8.log`) with the gap ratio **0.894347**, drift **+2.06e-04** against the 3e-04 envelope printed, lumped ratio drift **−2.99e-07**, cross-route **+1.84e-04**, and `Im Z12(lumped)` **1.029281338** at relative **2.344e-10**; at `-n 2` **17 passed** / Status 0 / 102 s (`…183533Z_…-patched-n2.log`) with the gap ratio **0.894141** — step 1's record exactly, inside the unmoved 1e-4 — and `Im Z12(lumped)` at **4.649e-10**. Step 1's whole table reproduced digit-for-digit at both widths (`Im Z12(gap)` 1.110303775 / 1.110559796, `I_sheet` −4.122422e−08−1.000166e−06j). **The 1e-8 assert was probed load-bearing**, as the entry required: pointed at the gap route's `Im Z12` 1.110303775 it fails at relative **7.297e-02** (`…183730Z_…-probe-n2.log`, Status 1, `1 failed, 5 deselected` / 82 s; the one-line edit was reverted and is not committed). `STEP1_GAP_RATIO_RECORD` untouched, no band widened, no record re-written, no root-cause claim made — option (iii) stays declined and re-opens only if a production quantity ever reads a gap-route integral at parallel width.* | standard (complex, 84 s per width) |
| `PORT-13` | **Phase-6 ring-rung solve probe** — the first solve on the 32-ring-port high-pass layout (`mesh:9`, 265 621 cells, `GEO-20`/`EX-35`) | ⬜ *(commissioned 2026-08-30 02:15 weekly review; **the ruling text was lost with that session** — only the dashboard's one-line summary survived. Not queueable until the next weekly review (2026-09-06) re-writes the anchor, the cost estimate and the scope; the daily review does not scope Phase-6 work)* | heavy (probe first) |

**`PORT-12` step 2 — width-qualify the record and bound the parallel drift
(ruled 2026-08-30 02:15 weekly review, option (i) with a bounded envelope;
ruling text in the known-issues entry — that session died before writing
this paragraph, the 10:30 daily review wrote it from the ruling).** Smoke
tier, complex, `main`, **no `src/` change**: `tests/validation/
test_port_lumped_two_torus.py` only. **Build:** `REPRODUCTION_BAND = 1e-4`
stays and its comment states it is a **`-n 2` record** (every
`PORT-1`/`OPS-18` two-torus digit is quoted at that width); a new
pre-registered `PARALLEL_DRIFT_ENVELOPE = 3e-4` (provenance: step 1's
four-width table, max +2.06e-04 at `-n 8`, 1.46× headroom) is the band
`test_step_1_measurements_reproduce` uses when `comm.size > 2`, so the drift
is bounded on every width rather than hidden by a skip; and the lumped
route's width-flatness becomes the module's new negative control — assert
`Im Z12(lumped)` reproduces **1.029281338** at rtol **1e-8** (measured
flat to 2e-9 across all four widths), which is the reason the production
port model is unaffected. **Anchors, asserted:** at `-n 2` the gap ratio
**0.894141** inside 1e-4 (unchanged); at `-n 8` — the worst width — the gap
ratio inside 3e-4 of the record with the measured **+2.06e-04** printed;
`Im Z12(lumped)` at 1e-8 on both widths; the module's other four tests
unchanged. **Negative control:** run the `-n 8` window on `main` **first**
and footer its Status 1 (the existing red, `1 failed, 4 passed`), then the
patched tree green — the envelope must be visibly load-bearing; and the
1e-8 lumped assert must *fail* if pointed at the gap-route `Im Z12`
1.110303775 (a one-line probe, not committed). **Cost:** 84 s per width
(`20260829T1700…Z_PORT-12-step1-*`), three windows ≈ **260 s**, `-k 30
300` each, `tests/environment` first. **Traps:** complex build +
`FEM_EM_REQUIRE_COMPLEX=1`; `-n 8` is the hard case, not `-n 12`; `-s`;
do not touch `STEP1_GAP_RATIO_RECORD`. **Scope:** closes the chunk ✅ and
retires the known-issues entry; **not** a root-cause fix (option (iii)
declined — no birdcage or Larmor quantity reads a gap-route integral) and
**not** a widened record (option (ii) declined). **Negative result:** the
`-n 8` drift reading outside 3e-4, or the lumped route moving at 1e-8, is
a new fact about the fixture — record it on the known-issues entry, do not
widen the envelope, stop.

**`PORT-1` — Real port excitation from the solved field** ✅ *(closed by the 2026-08-15 18:00 review. Full
plans, journals and adjudications for steps 1–4 and 3b(i–xviii) were archived on 2026-08-15; the 2026-08-15
compressed record itself is now in `docs/planning/plan-archive.md`, entry «§7 PORT-1 compressed record (2026-08-15 form) — archived 2026-08-30 (weekly review)» — grep there before re-deriving.)*
> * **Done-when, met:** `run_n_port_sparameter_sweep` reads the solved field — `‖S−Sᵀ‖/‖S‖ = 2.5494e-05` vs the 1e-3
>   gate, `‖S‖₂ = 0.861449`, `is_placeholder=False` (step 4, `20260813T183606Z_PORT-1-step4-packagegate.log`, 7 passed,
>   153.9 s); retiring heuristic differs by 3.078e-01. **Two-torus fixture through this entry point only** — not
>   birdcage ports, not S11/Z_in, not B1+. (Later re-records: 0.11 image 3.11213e-05 / 0.861356895 under `OPS-18` (1\*);
>   power-wave route 4.758625e-05 / 0.864809457 under `PORT-9` leg (d3).)
> * **Ladder, compressed:** f = 10 MHz, `ωM₁₂ = +1.241755 Ω`; reaction-route reciprocity 2.65e-13; electric-energy
>   excess removed by the solenoidal projection (ratio 0.999998, production drive since 2f); 3b found the factor 2 in
>   `_gap_arc_quadrature` (port voltage 0.894543 × ωM₁₂) and landed 3b-xvii (Faraday closure, 11× margin) and 3b-xviii
>   (`Im Z₁₂` vs the filamentary form at the unmoved 10%: corrected **0.939581, −6.04%**).
> * **Systematics (`ports/systematics.py`):** PEC box `D∞ = +0.0169` at `p = 1.657` (effective-range, never quoted
>   without its exponent); gap physics ÷(1 − 0.030224) (Jin 3e §10.4.2.1); composition additive (`PORT-10`, −0.0604 pp).
> * **Standing cautions:** no `Z_in`/`S₁₁` off the unprojected diagonal (`W_e/W_m = 6.524`); mutual is always the undriven port; `MUTUAL_TOLERANCE = 0.10` is measurement-justified — do not tighten; unconditional `create_entity_permutations()` before subdomain `dS` integrals (3b-iv hang); known-issues 3 (defect 1) and 11 stay open.

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

**`PORT-9` — lumped-element port boundary condition (the birdcage port model)** ✅ *(closed 2026-08-25 06:00
slot, leg (d1′), **at 10 MHz on the gapped 4-leg birdcage**; scoped 2026-08-16 weekly review, Jin 3e ch. 11 port
hierarchy. Steps 1–2c (two-torus) archived 2026-08-23; step 3 legs (a)–(d1′) with rulings (2\*)/(4\*)/(5\*)/(6\*)
archived in `docs/planning/plan-archive.md`, entry «§7 PORT-9 full narrative (step 3 legs (a)–(d1′)) — archived 2026-08-30 (weekly review)».)*
> * **Two-torus (steps 1–2c):** resistive-sheet lumped port (`ports/lumped.py`), circuit identity to < 1e-12; narrowed
>   sheet f = 0.5 with `w = A/h` gates cross-route **1.8333%** vs 5%; sweep route `‖S−Sᵀ‖/‖S‖` 2.574249e-11.
> * **Step 3 on the birdcage** (mesh from `GEO-18`, then `GEO-19` step B's 116 085 cells; `Z_p = z0 = 50 Ω`, f = 0.5):
>   leg (c) one solve **7.55 s**, adjacent spread 0.0159%; (d0) termination margin **598.4002×** at 50 Ω (open 1e6 Ω
>   column near-degenerate — `Z_p` is the gap capacitor); (d) 4×4 reciprocity 2.495292352e-05, σ_max 0.862659137;
>   (d1) displaced rung lost reciprocity (5.57e-03) → (d2) readout *is* the source's adjoint (1.33e-10), the asymmetry
>   is the terminated-`Z` assembly → ruling (2\*): **power-wave S**; (d3) asymmetric two-torus 1.324004669e-16 vs old
>   1.143811489e-04 (9.525277e+11× separation); (d3b/d3c) birdcage fixed route 4.6e-15–1.2e-14, σ_max **0.999993391**,
>   spreads 0.0617 / 0.0359 / 0.0237%, cell record 116 416 → 116 368 (image) → 116 085 (step B), all re-records version-tagged under (1\*)/(5\*).
> * **Closing leg (d1′), `20260825T110438Z_PORT-9-step3d1.log` (13 passed 106.64 s) + `…110643Z_…-consumers.log`
>   (24 passed 222.15 s):** zero rung reproduces (d0)'s column ≤ 2.568e-10, σ_max **0.999992805**, spreads **0.0553 / 0.0353 / 0.0214%**, separation 166.6766×, margin 2256.9707×; leg 1 rotated 22.5° breaks (iii′) on all three classes — **6.2219 / 7.1142 / 2.8474%** vs 0.5% — while `‖S−Sᵀ‖/‖S‖` = 2.259e-14 (2.466e+11× from the pre-fix 5.57e-03). (iii′) 5% → 0.5% committed as a tightening, all consumers green. * **Carry-forward:** **no Larmor, resonance or tuning claim** (`PORT-11` owns 64/128 MHz); terminated `Z` is a diagnostic, never reciprocity-gated; power-wave residuals are order-of-magnitude only ((d3c) rule); open-limit conditioning known-issues entry OPEN; `GapVoltagePortSpec` cannot run on the `GEO-16`-fragmented mesh.

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

**`PORT-11` — lumped-sheet ports on the gapped birdcage at the Larmor frequencies** ✅ **2026-08-26** *(step 1
probe 08-25 19:30, step 2 64 MHz 08-26 06:00, step 3 128 MHz 08-26 16:30; both audited COMPLIANT by the 18:00
review; commissioned 2026-08-23 weekly review as §10 subgoal 2b, serial on `PORT-9`. Full narrative archived in
`docs/planning/plan-archive.md`, entry «§7 PORT-11 full narrative — archived 2026-08-30 (weekly review)».)* Same code path and fixture as `PORT-9` leg (d) — only the frequency moved.
> * **Step 1 (`20260826T003427Z/003559Z_PORT-11-step1*.log`, 14 passed twice):** phantom cells/δ **5.9213** (stop rule
>   ≥ 2), cells/λ 21.8936, loss tangent 1.8004; MUMPS frequency-flat (9.49 / 6.36 s vs 6.56 / 6.50 s at 10 MHz).
> * **Step 2, 64 MHz (`20260826T110434Z_PORT-11-step2.log`, 17 passed 177.48 s, 179 s):** (i) `‖S−Sᵀ‖/‖S‖`
>   **2.581325834e-14** vs 1e-3; (ii) σ_max **0.999721388** ≤ 1 + 1e-9, max column power 0.804704664; (iii′) class spreads
>   **0.0573 / 0.0599 / 0.0370%** vs 0.5%, anti-noise control 671.0527× vs 10×; 10 MHz control reproduces
>   `LEG_D_S_MATRIX_10MHZ` to **1.158e-10** vs 1e-6 and `LEG_D0_Z_COLUMN` to 2.568e-10; displaced control breaks (iii′) at
>   12.8947 / 27.7509 / 7.7239% with (i) at 1.25e-15; consumer `…110750Z` 5 passed 103.82 s.
> * **Step 3, 128 MHz (`20260826T213414Z_PORT-11-step3.log`, 18 passed 197.85 s, 201 s):** pre-gate rule by measurement —
>   loss tangent **0.9002** (displacement-dominated), **cells/λ 12.5024 ≥ 10**, cells/δ 5.1845; (i) **7.030990825e-15**;
>   (ii) σ_max **0.998974779**, column power 0.861668762; (iii′) **0.1012 / 0.0916 / 0.0654%**, control 576.9483×;
>   displaced 16.7006 / 34.6556 / 13.2091%; consumer `…213748Z` 16 passed 130.04 s. * **Carry-forward:** **self-consistency identities on one fixture — no resonance, tuning or absolute-accuracy claim**; feed systematics are the two-torus ones (`PORT-1` 3b-xviii, `PORT-10`); `|Im P|/Re P` (terminal power 1.755210 / 2.659902 at 64 / 128 MHz) printed never gated; no vessel-wall region; `ANS-4` handed to the 08-30 weekly review.

### WF — End-to-end workflow & MRI outputs (Phase 5)

| ID | Title | Status | Tier |
|---|---|---|---|
| `WF-1` | MRI example CLI/config | 🧪 | smoke |
| `WF-2` | Reproducible output bundle manifest | ⚠️ | standard |
| `WF-3` | Quick-look phantom metrics report | ⚠️ | standard |
| `WF-4` | Scenario presets (debug/dev/benchmark-lite) | 🧪 | standard |
| `WF-5` | Loaded birdcage: frequency shift & Q degradation | ⬜ | heavy |
| `WF-6` | B1+ field mapping and homogeneity (CV) — **step 1 scoped 2026-08-29 10:30 review (§10 subgoal 4's first B1+ chunk): `\|B₁⁺\| = \|B_x + jB_y\|/2` on the loaded F-small birdcage at 10 MHz from the `PORT-9` single-drive field, gated on a three-way power accounting and C4 covariance of the map; see entry. Step 1 executed 2026-08-29 13:30 slot — the `post/` helpers landed and gate (i) closed at 9.80e-3 of supplied power (band 1e-2), gate (ii) **red at 8.65% against its 5% band** (known-issues), so the chunk is 🧪 and no B1+ claim exists. Step 1b executed 2026-08-29 19:30 — the CG1-projected estimator reads 2.19 / 2.11 / 1.89% at +90 / −90 / 180° against DG0's 8.65 / 9.58 / 8.60%, with the mis-rotated control surviving at 23.3%: the pre-registered verdict is **(a), the DG0 estimator floor**. No band moved; gate (ii) stays red and re-registering it is a review's call. Step 1c executed 2026-08-29 22:30 — the DG0 reading on a 96-point rotation-invariant ring set is 9.93 / 9.95 / 8.47% against the centroid set's 8.65 / 9.58 / 8.60%, every angle inside ±2 pp: **the sample set is not the mechanism**, corroborating 1b's estimator-floor verdict from the other side. Still no band moved. Step 1d executed 2026-08-30 12:00 — the ruling landed in the code: `post.project_to_cg1` is the packaged production estimator and gate (ii) is the CG1 covariance identity at all three angles, **2.1870 / 2.1146 / 1.8911%** against the unmoved 5% band, controls holding (mis-rotated 23.2642%, DG0 column unmoved at 8.6516 / 9.5808 / 8.5970%). `19 passed` / Status 0 / 97 s; **step 1 is ✅ and the chunk is 🟡** — a symmetry identity only, no CV / homogeneity / absolute claim; steps 2–3 are a review's to scope. **Step 2 scoped 2026-08-30 18:00 review** — the quadrature drive by exact superposition of the four solved fields at 10 MHz, two symmetry identities (C4-invariance; the co/counter-rotating mirror identity `\|B₁⁺\|_ccw(x) = \|B₁⁻\|_cw(Mx)`) at the measured CG1 floor, and the first *ungated* CV / polarisation-purity figures; §9 item 3. Step 2 executed 2026-08-31 22:30 slot — **both identities green at the CG1 floor: (a) C4-invariance of the quadrature `\|B₁⁺\|` map **0.9818%** and (b) the mirror identity `\|B₁⁻\|_cw(Mx)` vs `\|B₁⁺\|_ccw(x)` **0.8087%**, against the unmoved imported 5% band, with the mis-paired control at **95.1975%**; `17 passed` / Status 0 / 96 s. Ungated and labelled: centre purity `\|B₁⁺\|/\|B₁⁻\|` **127.91** (ccw) / **0.0081** (cw) / **1.0006** (P1 linear), mean `\|B₁⁺\|` 7.976427e-08 T at 1 V per port, CV **2.7563%** (51 centroids) / **2.4577%** (96 ring points). `post.b1_minus` landed. **Steps 1–2 ✅, chunk stays 🟡** — symmetry identities on one fixture at 10 MHz, no homogeneity, absolute, tuning or Larmor claim** | 🟡 | heavy (step 1 standard, complex) |
| `WF-7` | SAR10g hotspot identification | ⬜ | heavy |
| `WF-8` | Publication-quality visualization pipeline | ⬜ | standard |

> `WF-2`/`WF-3` produce structurally valid manifests and reports containing
> physically meaningless numbers. The plumbing is fine and becomes useful the
> moment `TH-1` lands.

**`WF-6` — B1+ field mapping and homogeneity** 🟡 *(steps 1 and 2 ✅ — step 1
2026-08-30 with step 1d, **step 2 ✅ 2026-08-31 22:30 slot** (0.9818% / 0.8087%
against 5%, control 95.1975%, log `20260831T033704Z_WF-6-step2.log`);
**2b (64/128 MHz) scoped 2026-08-31 03:00 review** — bullet after step 2's
record, §9 item 4; 3 (SAR) unscoped. Step 1 scoped 2026-08-29
10:30 review. §10 subgoal 4 said the first B1+ chunk "can be scoped by the
daily review the day `PORT-9` closes" — that was 08-25, `PORT-11` followed
08-26, and the 08-25 operator directive says "do not block subgoal 4 on
F-human". Nothing in the repo computes B from a time-harmonic E outside two
copy-pasted example helpers, and nothing anywhere computes B₁⁺; the step is
therefore one small `post/` addition plus a gate module. Degree 1, per the
§10 production-order decision.)*
> * **Step 1 — the map at 10 MHz on the loaded F-small birdcage, from the
>   `PORT-9` single-drive field.** Standard tier, complex build, `-n 2`,
>   `main`. **Build:** (a) `src/fem_em_solver/post/faraday.py` —
>   `magnetic_flux_density_from_e(e_complex, omega)` = the
>   `curl(E)/(−jω)` DG0-vector interpolation that
>   `examples/ports/04_birdcage_four_port_sparameters.py:140-182`
>   (`_paraview_fields`) and `examples/ports/05_…:192-236` each carry a
>   private copy of, and `b1_plus(b_complex)` = `|B_x + jB_y|/2` (peak
>   phasor convention, the one `e_complex` is in); export both from
>   `post/__init__.py`, and make the two examples import the helper (their
>   guides do not change and the census must read `dead=0`). (b)
>   `tests/validation/test_birdcage_b1_plus_map.py`: reuse
>   `build_four_port_sweep` from `test_port_birdcage_four_port.py` for the
>   mesh/problem/specs (116 085 cells, one C4-symmetric phantom of tag 3,
>   `r = 0.03`, `z ∈ [−0.04, 0.04]`, on the coil axis) and the
>   `_solve_driven_p1` re-solve pattern from `examples/ports/04` — the sweep
>   returns no fields — for drives **P1 and P2** (two solves, undriven
>   ports at 50 Ω as in leg (d)). **Anchor (i), a conservation identity,
>   asserted:** three-way power accounting for each drive —
>   `½ Re(V_src · Ī)` at the driven sheet **=** `mean_sar(e, sigma=fields.sigma_field, rho=any, cell_tags, subdomain_ids=3)['dissipated_power_w']`
>   (phantom, ½∫σ|E|²) **+** the same integral over conductor tag 1 **+**
>   `Σ_i ½ |I_i|² Re Z_p,i` over all four sheets (driven included), pre-registered
>   band **1%** of the supplied power. The `TH-11` family reads
>   its complex-power identity at 1e-9, but the sheet-resistance term has
>   never been closed on this fixture, so 1% is the honest first band; the
>   measured residual is the record either way. **Anchor (ii), a symmetry
>   identity, asserted:** C4 covariance of the map — on a fixed set of
>   sample points in the phantom (cell centroids of tag 3 in `z ∈ [−0.02,
>   0.02]`, `r ≤ 0.02`, via `evaluate_vector_field_parallel`, never
>   `f.eval`), `|B₁⁺|` from the P2 drive at the point rotated by +90° about
>   z equals `|B₁⁺|` from the P1 drive at the point: assert the relative
>   ℓ² mismatch over the set **≤ 5%**, pre-registered as a *discretisation*
>   band — B is DG0 on a gmsh mesh that is not itself C4-symmetric, so the
>   ceiling is cell-to-cell scatter, not the 0.5% `ADJACENT_SPREAD_BAND`
>   the S-matrix classes meet. Print the mismatch, the centre-point
>   `|B₁⁺|`, and the phantom/conductor/sheet power shares. **Negative
>   control:** drop the conductor term from (i) — the identity must then
>   miss by the conductor share (σ = 800 S/m against the phantom's 0.5),
>   asserted `>` the 1% band; and rotate by +90° against the **P3** drive
>   (180° apart) for the covariance — must **exceed** the 5% band, since
>   the map from the opposite port is the 180° image, not the 90° one.
>   **Cost:** mesh ~22 s + three solves ~8 s each + integrals; the
>   `PORT-9` step 3d module is 66 s for four solves, so **≈ 75 s**,
>   `timeout -k 30 300`; the two examples re-run for the import change
>   through `./run_examples.sh` (`ports:4` 88 s, `ports:5` 139 s, host
>   side, docrefs `exit != 1`). **Traps:** complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; DG0 interpolation
>   of a UFL `curl` needs `fem.Expression` with the DG0 space's
>   interpolation points, complex dtype; `mean_sar` needs a `rho` — pass
>   `1000.0`, it does not enter `dissipated_power_w`; `sheet_terminal_current`
>   returns every port's `I_i`, read them from the case result, do not
>   re-derive; the `column power sum 0.793823974` is `Σ|S_ij|²`,
>   dimensionless — not a watt and not this gate; `run_examples.sh` runs on
>   the **host** (the `EX-32` trap); rank-safety on every integral
>   (`assemble_scalar` is rank-local). **Scope:** 10 MHz, F-small, single
>   drives, degree 1 — **no** quadrature drive, **no** homogeneity/CV number,
>   **no** 64/128 MHz, **no** literature or AED comparison, no SAR claim
>   (the phantom integral is a power term here, not a SAR map); on green
>   the chunk is **🟡** with step 1 ✅ — steps 2 (the quadrature-driven map
>   and its CV at 64/128 MHz on the `PORT-11` ladder) and 3 (`MAT-4`'s
>   coil-driven SAR through the same field, its one-month-stall fix) are
>   scoped by a review from step 1's shares. **Negative result:** (i)
>   missing by more than 1% is the finding — record the three shares and
>   the residual in a new known-issues entry, keep the assert, chunk stays
>   ⬜/🧪, stop (a sheet-power bookkeeping error and a real solver defect
>   look identical here and only a review separates them); (ii) above 5% is
>   reported the same way — never widen either band in-slot.
> * **Step 1 executed, 2026-08-29 13:30 implementer slot — built as written,
>   gate (i) green, gate (ii) red; the step's own negative-result clause
>   applied, so the chunk is 🧪 and `main` carries one deliberate red.**
>   `src/fem_em_solver/post/faraday.py` landed with
>   `magnetic_flux_density_from_e` and `b1_plus`, exported from `post/`, and
>   both `examples/ports/04`,`05` now import the helper instead of carrying a
>   private copy (each re-run green through the harness: `ports:4` 78 s Status 0
>   `…183919Z_WF-6-step1-examples.log`, `ports:5` 128 s Status 0
>   `…184042Z_WF-6-step1-examples-05.log`; the doc-reference census finds
>   **no dead reference to either example's artifacts**,
>   `…184303Z_WF-6-step1-docrefs.log`, its `dead=53 stale=2` being entirely
>   examples this slot did not run).
>   `tests/validation/test_birdcage_b1_plus_map.py` solves **four** single
>   drives on `build_four_port_sweep`'s 116 085-cell fixture (5.6–6.0 s each)
>   and reads:
>   **Gate (i) ✅** — the three-way accounting closes to **9.795751e-03** of the
>   supplied 6.856240413e-03 W at the P1 drive and **9.796209e-03** at P2,
>   inside the pre-registered 1e-2, with shares **0.0008% phantom /
>   6.5374% conductor / 92.4822% sheets** and the conductor-blind negative
>   control missing by 7.517001e-02 (7.7× the band). The sheet term dominating
>   at 92% is the honest reading of a 50 Ω termination on every port and is why
>   1% rather than 1e-9 was the right first band.
>   **Gate (ii) ❌ 8.6516% against 5%** on 51 tag-3 centroids
>   (`r ≤ 0.02`, `|z| ≤ 0.02`); `|B₁⁺|` mean 2.077398e-08 T at `V_src = 1 V`.
>   The 180° negative control **holds at 27.3161%** (3.2× the failing reading),
>   so the estimator resolves the drive azimuth; the ungated diagnostics say
>   the miss is *systematic* — pointwise deviation median 6.7395%, p90
>   15.0357%, max 17.5662%, and the **second 90° instance (P4 at −90°) reads
>   9.5808%**, alike to P2's. Both 90° instances agreeing rules out anything
>   peculiar to P2 and points at DG0 cell-scatter on a mesh that is not itself
>   C4-symmetric. Logs `…183450Z_WF-6-step1.log` (89 s, with
>   `tests/environment`) and `…183728Z_WF-6-step1-diagnostic.log` (87 s).
>   **No band was widened and no assert removed**, per the clause above.
>   **Step 1b is a review's call**, with two candidates already separated in the
>   known-issues entry: (a) the 5% band underestimated the DG0 scatter floor —
>   the remedy is a better estimator (CG1-projected `B`, volume-weighted
>   comparison, or a rotation-invariant sample set), not a looser band; (b) a
>   real C4 asymmetry in the field, which the fixture's ≤ 0.5% `Z` class spreads
>   bound an order of magnitude below this at the terminals. Steps 2 and 3 keep
>   their prerequisite: step 1's shares are now on record, but the map itself is
>   not gated until (ii) closes.
> * **Steps 1b and 1c — scoped 2026-08-29 18:00 review: separate candidate (a),
>   the DG0 estimator floor, from candidate (b), a real C4 asymmetry, by
>   measurement; neither moves the 5% band.** One fact the 10:30 scoping
>   missed and step 1 exposed: the sample set is **51 centroids** in a
>   0.02 m-radius × 0.04 m cylinder, i.e. ≈ 1 cm phantom cells on the 116 085-cell
>   fixture — a DG0 curl is piecewise constant over cells that size, so
>   cell-to-cell scatter of order 10% is not surprising, and the 5% band was a
>   guess against a floor nobody had measured. Both steps reuse
>   `tests/validation/test_birdcage_b1_plus_map.py`'s fixture (`b1_plus_map`,
>   four solves P1–P4, 5.6–6.0 s each, mesh ~22 s) and change nothing about
>   the module's asserts; each adds a new module or a new test function with
>   its own pre-registered assert. Two independent slots, ≈ 100–120 s each.
>   * **Step 1b — the estimator leg: CG1-projected `B` on the same 51 points.**
>     Standard, complex, `-n 2`, `main`. L²-project the DG0 `B_phasor`
>     (complex vector) onto `("Lagrange", 1, (3,))` with a mass-matrix
>     `LinearProblem` (not `interpolate` — DG0 → CG1 interpolation is
>     ill-defined at vertices), apply `b1_plus` to the projection, and read
>     it at the same 51 points and their ±90° / 180° images through
>     `evaluate_vector_field_parallel`. Print the DG0 and CG1 relative ℓ²
>     mismatches side by side for **P2 at +90°, P4 at −90°, P3 at 180°**
>     (the 180° identity is *also* a covariance identity — P3 is the 180°
>     image of P1 — and step 1 never read it; it is the sharpest discriminator
>     here: a DG0 scatter floor is the same at 90° and 180°, a C2-preserving
>     C4-breaking field asymmetry is not) and the pointwise median / p90 for
>     each. **Anchors, asserted:** (1) the DG0 P2-at-+90° reading reproduces
>     step 1's **8.6516%** at rtol 1e-4 (same mesh, same points — a record
>     reproduction, and the proof the projection leg reads the same field);
>     (2) gate (i)'s P1 residual reproduces **9.795751e-03** at rtol 1e-4;
>     (3) the mis-rotated control P3-at-+90° stays **> 5%** under *both*
>     estimators (the estimator must still resolve azimuth — a CG1
>     projection that smooths the 27.3% control below 5% has smoothed the
>     map away, and that is a negative result, not a pass). **Verdict bands,
>     pre-registered, recorded not asserted:** CG1 mismatch ≤ 5% at all three
>     covariance angles ⇒ candidate (a) — the review re-registers gate (ii)
>     on the CG1 estimator with the measured floor as its band's provenance;
>     CG1 90° readings stay ≥ 7% while CG1 180° reads ≤ 5% ⇒ candidate (b),
>     a C4-breaking asymmetry in the field — the review commissions a
>     field-side hunt (per-port sheet current phases, the phantom's
>     off-axis fit); all three stay ≥ 7% under CG1 ⇒ neither — the map's
>     azimuthal structure at these points is not resolved at ~1 cm cells and
>     step 1c's sample set decides. **Negative control:** anchor (3) above,
>     plus `evaluate_vector_field_parallel`'s `valid` mask must be all-true on
>     the images (a point outside the mesh silently drops out of the ℓ²).
>     **Cost:** mesh 22 s + four solves 24 s + one complex CG1 mass solve on
>     116 085 cells (≈ 5 s) + evaluations ≈ **100 s**, `-k 30 400`, one
>     window plus `tests/environment`. **Traps:** complex build +
>     `FEM_EM_REQUIRE_COMPLEX=1`; the mass-matrix `LinearProblem` needs
>     `petsc_options={"ksp_type": "cg", "pc_type": "jacobi"}` or it defaults
>     to LU on a 3-vector CG1 space (fine at this size, slow); rank-safety on
>     the ℓ² (gather values, the helper returns global arrays — check before
>     reducing twice); `-s`; do not touch the existing asserts or the 5%
>     constant. **Scope:** measurement only — no band moves, gate (ii) stays
>     red, the chunk stays 🧪, no CV, no 64/128 MHz. **Negative result:** any
>     reading is the finding — the three-angle × two-estimator table goes into
>     the known-issues `WF-6` entry and the slot stops; a CG1 that fails
>     anchor (3) is recorded as "the projection over-smooths at this
>     resolution" and the review looks at step 1c.
>   * **Step 1b executed, 2026-08-29 19:30 implementer slot — ✅ as scoped, and
>     the verdict is (a), the estimator floor. No band moved; gate (ii) is
>     still red and the chunk is still 🧪.** Built as written on
>     `test_birdcage_b1_plus_map.py`'s own `b1_plus_map` fixture (nothing in
>     `src/` changed, so no example re-run was owed): a `cg1_estimator_table`
>     module fixture L²-projects each drive's DG0 `B_phasor` onto
>     `("Lagrange", 1, (3,))` through a Hermitian mass-matrix `LinearProblem`
>     (CG/Jacobi, `ksp_rtol` 1e-12, `petsc_options_prefix` per 0.11) and forms
>     `|B_x + jB_y|/2` from the **evaluated** projected vector at the same 51
>     points — the magnitude is taken after the point evaluation, `|·|` being
>     non-linear. Log `20260830T003238Z_WF-6-step1b.log`, `1 failed, 15 passed`
>     / Status 1 / **98 s** with `tests/environment`; the single failure is
>     gate (ii) itself, untouched.
>     **Anchors, all three green:** DG0 P2-at-+90° reproduces **8.6516%** and
>     gate (i)'s P1 residual reproduces **9.795751e-03**, both at rtol 1e-4;
>     the mis-rotated control P3-at-+90° stays outside 5% under *both*
>     estimators (DG0 **27.3161%**, CG1 **23.2642%**); `valid` all-true, 51 of
>     51, on every rotated image.
>     **The table (recorded, in the known-issues entry too):** `+90°` DG0
>     8.6516% │ CG1 **2.1870%**; `−90°` DG0 9.5808% │ CG1 **2.1146%**;
>     `180°` DG0 8.5970% │ CG1 **1.8911%**. CG1 is inside 5% at all three
>     covariance angles ⇒ the pre-registered **candidate (a)** branch. The
>     sharpest single reading is the 180° column, which step 1 never had: DG0
>     misses by 8.5970% there, the *same* as at +90°, which is what a
>     scatter floor looks like and is not what a C2-preserving, C4-breaking
>     field asymmetry would produce — candidate (b) is unsupported by any
>     reading on this fixture. The projection moves the mean `|B₁⁺|` by 0.38%
>     (2.077398e-08 → 2.069556e-08 T), so it smooths the scatter and not the
>     map.
>     **What is owed next, and to whom:** re-registering gate (ii) on the CG1
>     estimator with this table as the band's provenance is a **review's
>     call**, explicitly not the slot's. Step 1c stays worth running as
>     scoped — it is independent, and a ring-set DG0 reading near 8–9% would
>     confirm the floor is the DG0 scatter itself rather than the centroid
>     sampling, which is the one thing this leg cannot distinguish.
>   * **Step 1c — the sample-set leg: a rotation-invariant point set at DG0.**
>     Standard, complex, `-n 2`, `main`; **independent of 1b** (it does not
>     need 1b's result and must not wait for it). Replace the centroid sample
>     with a set closed under the C4 rotation: rings at `r ∈ {0.005, 0.010,
>     0.015, 0.020}` m, `z ∈ {−0.015, 0, +0.015}` m, **8 azimuths** (45°
>     steps) — 96 points, every point's ±90° and 180° image a member of the
>     set, all inside the tag-3 phantom (radius 0.03, `|z| ≤ 0.04`). Read the
>     DG0 `|B₁⁺|` map from P1 on the set once, and the P2 / P4 / P3 maps on
>     the rotated set, and print the relative ℓ² mismatch at +90°, −90° and
>     180°, plus the mismatch **per ring** (each `(r, z)` separately) so the
>     radial structure of the scatter is on record. **Anchors, asserted:** (1)
>     `valid` all-true on all 96 points and every image (the set is inside
>     the phantom by construction — a false here is a geometry mistake);
>     (2) the P1 map on the set is itself **C4-invariant as a set of values
>     only if the mesh were symmetric — it is not, so assert nothing on that;
>     instead** assert the record reproduction of gate (i)'s **9.795751e-03**
>     at rtol 1e-4 and of the centroid-set DG0 **8.6516%** at rtol 1e-4 (the
>     module's existing reading, re-printed from the same fixture); (3) the
>     mis-rotated control P3-at-+90° **> 5%** on the ring set. **Verdict
>     bands, recorded not asserted:** the ring-set +90° / −90° / 180°
>     mismatches against the centroid set's 8.65 / 9.58 / (1b's 180°)
>     figures — agreement within ±2 pp says the sample set is not the
>     mechanism and the floor is the DG0 scatter itself; a per-ring
>     pattern (inner rings ≤ 5%, outer ≥ 10%, or the reverse) is a
>     structure the review reads against the coil geometry. **Cost:** same
>     fixture, no projection ≈ **90 s**, `-k 30 400`. **Traps:** the ring
>     points must not sit exactly on a cell facet — jitter the azimuth start
>     by 3.7° (a point on a facet returns whichever cell the locator finds
>     first, rank-dependently); the rotation must be the *fixture's* P1→P2
>     angle read from the sheet frames as `b1_plus_map` already does, not a
>     literal 90°; complex build, `-s`, `evaluate_vector_field_parallel`
>     only. **Scope / negative result:** as 1b — table into the known-issues
>     entry, chunk stays 🧪, no band moves.
>   * **Step 1c executed, 2026-08-29 22:30 implementer slot — ✅ as scoped, and
>     the verdict is "the sample set is not the mechanism". No band moved;
>     gate (ii) is still red and the chunk is still 🧪.** Built as written on
>     `test_birdcage_b1_plus_map.py`'s own `b1_plus_map` fixture (nothing in
>     `src/` changed, no example re-run owed, no new solve — only the points
>     changed): a `ring_set_table` module fixture reads the DG0 `|B₁⁺|` of the
>     four existing drives on 96 points closed under the C4 rotation — `r ∈
>     {0.005, 0.010, 0.015, 0.020}` m × `z ∈ {−0.015, 0, +0.015}` m × 8
>     azimuths in 45° steps, start jittered 3.7° so no point sits on a
>     coordinate plane (and so plausibly on a cell facet, where the locator's
>     answer is rank-dependent). The rotation is again the fixture's own
>     P1→P2 sheet separation, 90.000000°. Log
>     `20260830T033147Z_WF-6-step1c.log`, `1 failed, 18 passed` / Status 1 /
>     **97 s** with `tests/environment`; the single failure is gate (ii)
>     itself, untouched.
>     **Anchors, all three green:** `valid` **96 of 96** on all four drives
>     and every rotated image (the set is interior by construction);
>     centroid-set DG0 P2-at-+90° reproduces **8.6516%** and gate (i)'s P1
>     residual **9.795751e-03**, both at rtol 1e-4; the mis-rotated control
>     P3-at-+90° reads **25.8213%** on the ring set, asserted outside 5%.
>     **The table (recorded, in the known-issues entry too), ring set vs the
>     centroid set:** `+90°` **9.9271%** vs 8.6516% (**+1.28 pp**); `−90°`
>     **9.9519%** vs 9.5808% (**+0.37 pp**); `180°` **8.4706%** vs 1b's
>     8.5970% (**−0.13 pp**). Every angle inside ±2 pp ⇒ the pre-registered
>     **"sample set is not the mechanism"** branch: the centroid set's lack of
>     closure under the rotation was not manufacturing the miss, and the ~9%
>     floor is the DG0 scatter itself. Together with 1b this is a two-sided
>     result — change the estimator and the miss falls 4–5×, change the sample
>     set and it does not move.
>     **Per-ring structure, for the review:** no monotone radial trend
>     (6.33…11.65% across the `r = 0.010` rings, 4.61…12.63% across
>     `r = 0.020`); lowest ring `r = 0.020, z = +0.015` at 4.61 / 6.21 /
>     3.96%, highest `r = 0.005, z = −0.015` at 11.25 / 12.27 / 6.52%. A
>     ring-to-ring spread of the same order as the overall figure is what a
>     per-cell scatter looks like. `|B₁⁺|` over the ring set, P1 driven: mean
>     2.023327e-08 T, max 3.263326e-08, min 1.419703e-08.
>     **What is owed next:** unchanged from 1b — re-registering gate (ii) on
>     the CG1 estimator with 1b's table as provenance is a **review's call**,
>     now with 1c's corroboration that the sampling is not the confound.
>   * **Step 1d — re-register gate (ii) on the CG1-projected estimator
>     (ruled 2026-08-30 02:15 weekly review; ruling text in the known-issues
>     `WF-6` entry — that session died before writing this bullet, the 10:30
>     daily review wrote it from the ruling).** Standard, complex, `-n 2`,
>     `main`. **Build:** (a) `post/faraday.py` gains
>     `project_to_cg1(b_dg0)` — the Hermitian mass-matrix `LinearProblem`
>     (CG/Jacobi, `ksp_rtol` 1e-12, `petsc_options_prefix`) step 1b's
>     `cg1_estimator_table` fixture already carries, moved into the package
>     and exported from `post/__init__.py`; the test fixture calls it. The DG0
>     `magnetic_flux_density_from_e` is kept as the raw curl. (b) In
>     `test_birdcage_b1_plus_map.py`,
>     `test_b1_plus_map_is_c4_covariant_under_the_drive_rotation` becomes the
>     CG1 covariance identity at **all three angles** (+90°, −90°, 180°) on
>     the 51 centroids against the **unchanged** `C4_COVARIANCE_BAND = 5e-2`;
>     the DG0 readings are printed and cited in-comment with their records
>     (8.6516 / 9.5808 / 8.5970%), not gated — gating a DG0 curl on a
>     non-symmetric mesh gates the mesh, not the map (`GEO-19` step-C
>     precedent). **Anchors, asserted:** CG1 mismatches reproduce step 1b's
>     **2.1870 / 2.1146 / 1.8911%** at rtol 1e-3 (a record reproduction with
>     2.3× headroom under 5%; p90 ≤ 3.47%); gate (i)'s **9.795751e-03**
>     unchanged at rtol 1e-4; the mis-rotated control P3-at-+90° stays
>     **> 5%** under CG1 (record **23.2642%**); `valid` 51/51 on every
>     image. **Negative control:** the mis-rotated control, plus the DG0
>     print must still read 8.6516% — a DG0 column that moved means the
>     projection changed the field, not the estimator. **Cost:** the module
>     is 98 s with the CG1 fixture (`20260830T003238Z`); `-k 30 400`; the
>     `src/` change owes `ports:4` (78 s) and `ports:5` (128 s) re-runs via
>     `./run_examples.sh` on the host (docker-socket denial ⇒ the §9 runner
>     substitution), docrefs `exit != 1`. **Traps:** the projection is
>     applied to the complex 3-vector and `|B_x + jB_y|/2` is formed from
>     the **evaluated** projection (`|·|` is non-linear); helper returns
>     global arrays — do not reduce twice; `-s`; complex build +
>     `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first. **Scope:** on
>     green the chunk is **🟡 with step 1 ✅** (a symmetry identity — no CV,
>     homogeneity or absolute-accuracy claim follows); steps 2–3 stay serial
>     on it and are scoped by a review; the known-issues entry and `main`'s
>     deliberate red retire with the landing. **Negative result:** CG1 not
>     reproducing 1b's table at rtol 1e-3 is a finding about the projection
>     path — record the new column in the known-issues entry, keep the old
>     DG0 gate red, stop; never widen the 5%.
>   * **Step 1d executed, 2026-08-30 12:00 implementer slot — ✅ as scoped.
>     Gate (ii) closes on the CG1 estimator, `main`'s deliberate red retires,
>     and `WF-6` is 🟡 with step 1 ✅.** Built as written. (a)
>     `post/faraday.py` gained `project_to_cg1(b_dg0)` — step 1b's Hermitian
>     mass-matrix `LinearProblem` (CG/Jacobi, `ksp_rtol` 1e-12, local PETSc
>     import per the `current_divergence` precedent), exported from
>     `post/__init__.py`, with the DG0 `magnetic_flux_density_from_e` kept
>     untouched as the raw curl; the test module's fixture-local
>     `_project_to_cg1` is gone and the fixture calls the package function.
>     (b) `test_b1_plus_map_is_c4_covariant_under_the_drive_rotation` is now
>     the CG1 covariance identity at **all three** angles against the
>     **unchanged** `C4_COVARIANCE_BAND = 5e-2`, each angle *also* asserted
>     against step 1b's record at rtol 1e-3 (a drifting reading would slip
>     through 2.3× of headroom otherwise); the DG0 column is printed and cited
>     in-comment, never gated.
>     **Anchors, all green:** CG1 **2.1870 / 2.1146 / 1.8911%** at +90° /
>     −90° / 180°, reproducing 1b exactly; gate (i)'s **9.795751e-03** at
>     rtol 1e-4; mis-rotated control P3-at-+90° **23.2642%** under CG1,
>     outside the band; `valid` 51/51 on every image. **Negative control:**
>     the DG0 print still reads **8.6516 / 9.5808 / 8.5970%** (asserted at
>     rtol 1e-4) — the projection changed the estimator, not the field.
>     Log `20260830T170242Z_WF-6-step1d.log`, **19 passed / Status 0 / 97 s**
>     with `tests/environment`, complex, `-n 2`.
>     **The `src/` change's owed re-runs, both green:** `ports:4` 76 s
>     Status 0 (`20260830T170431Z_WF-6-step1d-examples.log`), `ports:5` 127 s
>     Status 0 (`20260830T170559Z_WF-6-step1d-examples-05.log`) — the runner's
>     docker-socket denial recurred and the §9 substitution was used for both.
>     Doc-reference census `exit=1`, `dead=53 guide=0 stale=2`
>     (`20260830T170816Z_WF-6-step1d-docrefs.log`): no `ports_04_*` or
>     `ports_05_*` artifact among the dead, so these two examples' references
>     are live and the 53 are `EX-36`'s, unchanged.
>     **What this does and does not claim:** gate (ii) is a **symmetry
>     identity** on one fixture at 10 MHz. No B₁⁺ homogeneity, CV or
>     absolute-accuracy claim follows, and §2 is not moved by it. Steps 2–3
>     stay serial on step 1 and are a review's to scope.
>   * **Step 2 — scoped 2026-08-30 18:00 review: the quadrature drive by
>     exact superposition, at 10 MHz on the same fixture; two symmetry
>     identities and the first (ungated) homogeneity figures.** The four
>     single-drive solves already in `b1_plus_map` share one mesh, one
>     `V_src`, and the same linear sheet law on every port in every solve
>     (`V = V_src − I·Z_p`, `Z_p = 50 Ω`), so the field of all four ports
>     driven at once with phases `φ_k` is **exactly** `Σ_k e^{iφ_k} E_k` —
>     no new solve, no new plumbing. **Build:** `post/faraday.py` gains
>     `b1_minus` (`|B_x − jB_y|/2`, the counter-rotating component) beside
>     `b1_plus`, exported; a new module
>     `tests/validation/test_birdcage_b1_quadrature.py` forms the two
>     rotation senses `B_ccw = Σ e^{+ikπ/2} B_k`, `B_cw = Σ e^{−ikπ/2} B_k`
>     in port order, projects each through `post.project_to_cg1`, and reads
>     `|B₁⁺|` / `|B₁⁻|` on the 51 centroids through
>     `evaluate_vector_field_parallel`. **Anchors, asserted:** (a)
>     **C4-invariance** — advancing the phase pattern by one port is a 90°
>     rotation of the drive and multiplies the superposed field by a global
>     phase, so `|B₁⁺|_ccw(R₉₀ x) = |B₁⁺|_ccw(x)`: relative L² ≤ **5e-2**
>     (`C4_COVARIANCE_BAND`, whose CG1 provenance is step 1d's 2.19 / 2.11 /
>     1.89% — a superposition of four fields each inside the floor is inside
>     it); (b) **the mirror identity** — a 4-leg birdcage has a mirror plane
>     through each port and `B` is a pseudovector, so reversing the rotation
>     sense equals reflecting: `|B₁⁺|_ccw(x) = |B₁⁻|_cw(M x)`, `M` the
>     reflection in the plane through port 1's azimuth, at the 51 centroids'
>     mirror images, relative L² ≤ **5e-2** (the same floor — a
>     non-symmetric mesh enters at the same order as in (a)); (c) step 1's
>     records reproduce — gate (i) **9.795751e-03** at rtol 1e-4, the three
>     CG1 covariance readings at rtol 1e-3. **Reported, not gated (no
>     closed form; §2 does not move):** the centre-point polarisation purity
>     `|B₁⁺|/|B₁⁻|` for each sense (an ideal quadrature birdcage gives ∞ for
>     one and 0 for the other — the number MRI cares about), mean `|B₁⁺|`
>     at 1 V per port, and the **CV** of `|B₁⁺|_ccw` over the 51 centroids
>     and over step 1c's 96-point ring set — the first homogeneity figures,
>     labelled as such. **Negative controls:** the mis-paired comparison
>     `|B₁⁺|_ccw(x)` vs `|B₁⁺|_cw(M x)` must **miss** the 5% band (an ideal
>     birdcage makes one of them ≈ 0 at the centre; assert > 5% only, as
>     step 1d's 23.26% control does); the P1 single drive's centre purity is
>     printed as the "what a non-rotating field reads" line (linear
>     polarisation ⇒ `|B₁⁺| ≈ |B₁⁻|`). **Cost:** the map fixture is 97 s
>     (mesh ~22 s, four solves 5.6–6.0 s); two extra CG1 projections and the
>     point reads add ≤ 15 s — **≤ 120 s**, standard, `-n 2`, `-k 30 400`,
>     complex + `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first. The
>     `src/` change owes `ports:4` (76 s) and `ports:5` (127 s) re-runs and
>     the docrefs census (`exit 1` from `EX-36`'s 53 is not this step's).
>     **Traps:** the reflection plane goes through a **port** — read its
>     azimuth off the fixture, the legs need not sit on the coordinate axes;
>     magnitudes are taken *after* the point evaluation; the mirrored
>     centroids are fresh points — assert `valid` 51/51 on them too; the
>     phase sign convention only has to be consistent between the two
>     senses; helper returns global arrays; runner on the host,
>     docker-socket substitution. **Scope:** 10 MHz, F-small, degree 1,
>     superposition only — no simultaneous-source solve, **no 64/128 MHz**
>     (step 2b on the `PORT-11` ladder, serial on this landing), no
>     homogeneity *claim* (CV is a printed number), no SAR (step 3), no
>     literature or AED comparison; on green the chunk stays **🟡** with
>     steps 1–2 ✅. **Negative result:** (a) or (b) missing 5% is a finding
>     about the superposition path or the mirror assumption — record both
>     readings in a known-issues entry, keep the assert, stop; never widen
>     the band.
>
>     **Executed 2026-08-31, 22:30 slot — ✅, both identities green at the
>     CG1 floor.** `post.b1_minus` landed beside `b1_plus` (shared private
>     `_rotating_component`, exported from `post`), and
>     `tests/validation/test_birdcage_b1_quadrature.py` built the two senses
>     by superposing the four DG0 curls and projecting each through
>     `project_to_cg1`. **17 passed / Status 0 / 96 s**, log
>     `20260831T033704Z_WF-6-step2.log`.
>     * **(a) C4-invariance 0.9818%** and **(b) mirror identity 0.8087%**,
>       both against the **unmoved, imported** `C4_COVARIANCE_BAND = 5e-2` —
>       i.e. inside step 1d's single-drive floor (2.19 / 2.11 / 1.89%) rather
>       than merely inside the band, which is the right expectation for a sum
>       of four fields each inside that floor. 51/51 points valid on all three
>       image sets (`x`, `Rx`, `Mx`).
>     * **Negative controls, both fired.** The mis-paired
>       `|B₁⁺|_cw(Mx)` vs `|B₁⁺|_ccw(x)` reads **95.1975%** (asserted `> 5%`
>       only); the P1 single drive's centre purity is **1.0006**, a linear
>       polarisation splitting evenly between the senses exactly as it must.
>     * **Reported, ungated, and labelled in the log as such:** centre
>       `|B₁⁺|/|B₁⁻|` = **127.9083** (ccw) and **0.0081** (cw) — the
>       polarisation-purity number MRI cares about, on one unconverged
>       fixture; mean `|B₁⁺|_ccw` **7.976427e-08 T** at 1 V per port; **CV
>       2.7563%** over the 51 centroids and **2.4577%** over step 1c's 96-point
>       ring set. No homogeneity *claim* is made or entered in §2.
>     * **The premise is asserted, not assumed:** a separate test reads the
>       four specs' `port_impedance_ohm` and `drive_voltage_v` and the four
>       solves' `source_voltage_v` and requires one value each — superposition
>       is exact only because the operator is shared.
>     * **A sign-convention error was made, measured and fixed before the
>       commit, and the band never moved.** The first run
>       (`20260831T033416Z_WF-6-step2.log`, Status 1) paired `e^{+jkπ/2}` with
>       an azimuth-*increasing* `k`, which makes the gated sense the
>       counter-rotating one: its centre purity read **0.0081** against the
>       other sense's **127.91**, and both identities came back at **18.8192%
>       / 20.2202%** — ~10× the CG1 floor, the signature of a ~2%
>       discretisation error on a quantity suppressed ~120× by cancellation.
>       In the `e^{jωt}` convention the sense `B₁⁺` reads is driven by a
>       pattern that *lags* with azimuth, so the exponent sign was corrected by
>       that derivation (the measurement is the confirmation, not the reason).
>       Both readings are recorded in the module and in `attempts.md`.
>     * **Owed re-runs, all green:** `ports:4` 76 s Status 0
>       (`20260831T033900Z_…-examples-04.log`), `ports:5` 127 s Status 0
>       (`…034019Z_…-examples-05.log`), doc-reference census `dead=53 guide=0
>       stale=10` unmoved (`…034237Z_…-docrefs.log`; the `exit=1` is `EX-36`'s
>       53, not this step's).
>     * **Scope held.** 10 MHz, F-small, degree 1, superposition only. No
>       simultaneous-source solve, no 64/128 MHz, no SAR, no absolute or
>       tuning claim; §2 is not moved. Steps 1–2 ✅ and the chunk stays 🟡.
>
> * **Step 2b — the same identities at the Larmor frequencies, 64 and
>   128 MHz, on the `PORT-11` mesh (scoped 2026-08-31 03:00 review).**
>   Standard tier, complex build, `-n 2`, `main`; no `src/` change. Every
>   B₁⁺ number on record is 10 MHz: the fixtures hard-code it —
>   `build_four_port_sweep()` takes no frequency
>   (`tests/validation/test_port_birdcage_four_port.py:219–300`, `FREQUENCY_HZ`
>   imported at `:114`) — while the identical construction already runs at
>   64/128 MHz through `_four_port_rung(name, offsets, frequency_hz=…,
>   reuse=…)` (`tests/validation/test_port_birdcage_leg_offset_sweep.py:199–455`),
>   the `PORT-11` / `EX-34` / `ANS-4` route, at **5.6–5.7 s per solve,
>   frequency-flat** (`ANS-4`'s `metrics.json`: 22.7 / 22.9 / 22.5 s per
>   four-solve rung). **Build:** `build_four_port_sweep(frequency_hz=
>   FREQUENCY_HZ)` — one keyword argument with the existing default, so the
>   10 MHz fixture is bit-identical — and a new
>   `tests/validation/test_birdcage_b1_larmor.py` that builds the sweep once
>   per frequency (module-scoped, mesh built once and reused across the two
>   frequencies as `ANS-4` does; **only floats and numpy arrays escape the
>   solve helper** — the `TH-13` step-2 teardown deadlock), then runs the
>   step-1d and step-2 readings unchanged in *form*: gate (i) at P1, the
>   single-drive CG1 covariance at +90 / −90 / 180°, the quadrature (a)
>   C4-invariance and (b) mirror identity, the mis-paired control, purity and
>   CV printed. **Anchors (imported, unmoved):** gate (i) ≤ 1e-2 of supplied
>   power at each frequency; (ii) and (a)/(b) ≤ `C4_COVARIANCE_BAND` = 5% at
>   each frequency; `valid` 51/51 on all image sets; cell count = 116 085
>   (`STEP2_CELL_COUNT`) with ratio 1.000000; the 10 MHz rows of the same
>   module reproduce 2.1870 / 2.1146 / 1.8911% and 0.9818 / 0.8087% at rtol
>   1e-3 (the control that the frequency argument is the only thing that
>   moved). **What is unknown, and why this item is informative either
>   way:** the 5% band's provenance is a **10 MHz** floor measurement (CG1
>   2.19 / 2.11 / 1.89%, 2.3× headroom); nobody has measured whether the CG1
>   floor holds at 64 MHz (cells/λ phantom 21.89) or at 128 MHz (12.50, the
>   `PORT-11` step-3 floor of 10). A miss at 128 MHz with 64 MHz green is a
>   resolution finding about the B₁⁺ estimator, not a formulation defect.
>   **Negative controls:** the mis-paired `|B₁⁺|_cw(Mx)` vs `|B₁⁺|_ccw(x)`
>   > 5% at each frequency (10 MHz reads 95.20%); the P1 linear purity ≈ 1
>   printed. **Reported, ungated, labelled:** centre `|B₁⁺|/|B₁⁻|` per sense,
>   mean `|B₁⁺|` at 1 V per port, CV over the 51 centroids and the 96-point
>   ring, at each frequency, beside the 10 MHz record (127.91 / 0.0081 /
>   7.976427e-08 T / 2.7563%) — the first Larmor-frequency B₁⁺ numbers in
>   the repo, and **still identities on one unconverged fixture**, not a
>   homogeneity claim. **Cost:** mesh ~22 s + 8 solves ≈ 46 s + 8 curls and
>   CG1 projections (step 2's module ran 96 s for four) ≈ **200–260 s**;
>   `timeout -k 30 600`; if the 10 MHz rows are included for the reproduction
>   control, 12 solves ≈ 300 s — still one command. **Traps:** the CG1
>   projection is a mass-matrix `LinearProblem` (CG/Jacobi, rtol 1e-12), keep
>   it; `|B₁⁺|` is real stored complex — magnitudes after the point
>   evaluation; `PHANTOM_CELLS_PER_LAMBDA_FLOOR = 10` is `PORT-11`'s gate,
>   import it and print cells/λ at each rung rather than re-deriving; the
>   superposition premise (shared `Z_p`, `V_src`) is asserted per frequency.
>   **Scope:** degree 1, F-small, the two Larmor frequencies, symmetry
>   identities only; no SAR (step 3), no absolute, tuning or homogeneity
>   claim; §2.2's "every 64/128 MHz claim is an identity on one fixture"
>   stands. Steps 1–2b ✅ leaves the chunk 🟡. **Negative result:** any
>   identity missing the band at either frequency — known-issues entry with
>   every reading and the cells/λ beside it, keep the assert, stop; **never
>   widen the band, never re-register it in-slot** (that is what step 1d's
>   ruling was for, and it was a review's).

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
| `EX-30` | Refresh the 13-example stale artifact set the checker could not see (10–17 d old on 2026-08-23; commissioned 2026-08-23 weekly review; **re-scoped 2026-08-24 10:30 review to four legs from the honest `stale=55` census** — see prose entry) | ✅ *(2026-08-26, all four legs)* (**leg (th) ✅ 2026-08-25**: all eight `th:` examples green, `time_harmonic` census 4 → 0 inside a derived 51 → 47, the licensed 128 MHz alignment executed — 0.01826 → 0.01769 / 57.31 → 59.16, version-tagged — and `th:6` reproducing to 2.02e-04 / 5.45e-05 in its unmoved 1% band; 105 s, measured standard. Legs (root), (mesh), (ports) all queued 2026-08-25 03:00 review — §9 items 3–5, with in-class (1\*) example-record licences granted for (mesh)/(ports). **Leg (root) attempted 2026-08-25 09:00 — not closed**: 6 of 8 green, census 47 → 26 fully attributed, two reds filed as known-issues, one of them a `MAG-13` convergence **gate red on `main`** since the 0.11 merge — see prose entry. **Leg (mesh) attempted 2026-08-25 16:30 — not closed**: 4 of 7 green, census 13 → 6 fully attributed inside a derived 26 → 19, licence granted but **not used** — nothing re-recorded — and three reds, **two of them further gate reds on `main`** (`GEO-15` graded-conductor, `GEO-16` kwarg-off cell record), the third an inverted control that lost its separation by 6e-6). **Leg (ports) ✅ 2026-08-26 (07:30 slot)**: all five examples green, `ports` census 4 → 0 and `ans` 2 → 0 inside a derived 13 → 7, and the (1\*) licence used exactly once — `ports:2`'s restated `‖S−Sᵀ‖/‖S‖` was red at a 8.666e-01 relative miss because the `PORT-9` leg (d3) power-wave assembly moved the record 2.5494e-05 → **4.758625e-05** (the gate module's current digit, matched bit-for-bit), with `‖S‖₂` 0.861449 → **0.864809457** the same class hiding *inside* the band; re-recorded version-tagged, no band moved, `ans:3` fixed by import with zero script edits. **Leg (root) ✅ 2026-08-26 (12:00 slot) and with it the chunk**: both ruled reds disposed — `mag:1` moved `resolution` 0.01 → **0.008** per the 08-25 10:30 ruling and is green at **21 830 cells**, the 08-25 probe's count reproduced exactly with its analytic `B(3 mm) = 6.666667e-05 T` and decay ratio 12.67 unmoved; `mag:6` green through the landed `MAG-19` with **zero** example-side edits on bit-identical errors 21.8417 / 15.3848 / 4.4605%. The (1\*) licence hit all three predicted digits exactly (`mag:2` 409 596 / 6.2134%, `mag:4` 69 918 / 103 950 / 160 677, `mri:1` 1.979842e+02), version-tagged to this slot's logs and commit `c466143`; three shape-changing readings flagged in prose rather than silently re-recorded (`mag:4`'s max on-axis error is no longer monotone). Census `stale=7` → **`stale=0`, `dead=0 guide=0 exit=0`** — the prediction met exactly and the first clean corpus-wide census since `EX-29`. 447 s, measured standard; no band moved; the `straight_wire_domain` coarse-resolution floor re-heads and stays open, unassigned) | heavy (measured standard per leg) |
| `EX-31` | Ring-gapped birdcage with dual port families (`GEO-20` step 1's newly gated capability: first example with ring-gap terminals as exact disks from radial cut planes, and the first 12-port dual-family mesh — a geometry angle `EX-28` (leg gaps only) does not cover; mesh-only, no solve; commissioned 2026-08-24 10:30 review) | ✅ (2026-08-24: `mesh:7`, `examples/meshing/07_birdcage_ring_gap_ports.py` + same-stem guide; **closed as written on the first run**, every element of the rubric executed and no band moved — see the prose entry for the digits. *Audited COMPLIANT 2026-08-24 18:00 review: all three footers verified (75 / 72 / 1 s, statuses 0/0/2 with exit 2 = the `OPS-19` stale-only contract), the printed assertions match this entry to the last decimal, the gate-module strengthening is real (records asserted at their source, lines 403/458/538, imported by the example not restated), and `git show 7529fa4 -- tests/` is 24 insertions / 0 deletions — purely additive, nothing loosened*) | standard (measured standard) |
| `EX-32` | Birdcage 4-port power-wave S-matrix at 10 MHz (`PORT-9`'s newly gated capability: first example solving ports on the **birdcage** — every existing S-parameter example is two-torus (`EX-20`/`EX-24`/ports:1–3), and `EX-28`/`EX-31` are mesh-only; commissioned 2026-08-25 10:30 review, §5.4 ramp) | ✅ *(2026-08-26, green on the first run; every gate-module record reproduced exactly and the only reading that moved is the one (d3c) declares non-reproducible)* | standard (measured standard, 88 s) |
| `EX-33` | 16-leg gapped + sheeted birdcage mesh (`GEO-19`'s newly gated capability: first example above four legs — `EX-28`/`EX-31`/`mesh:3` are all 4-leg, so the geometry angle is new; mesh-only, no solve, no port claim; commissioned 2026-08-25 18:00 review, §5.4 ramp) | ✅ *(audited COMPLIANT 2026-08-26 18:00 review: three footers Status 0 at 131 / 126 / 1 s, all 16 claimed digits grep out of the run log, bands *and* `_assert_identity_family` imported from the gate module, the gate-module diff a single +6-line additive hunk)* | standard |
| `EX-34` | Birdcage 4-port S-matrix across the frequency ladder 10 / 64 / 128 MHz on **one** mesh (`PORT-11`'s newly gated capability: first example solving ports at a Larmor frequency — `EX-32` is 10 MHz only, `EX-19`/`EX-25` are Larmor on the sphere with no ports; the drive/output angle is the frequency ladder itself: loss tangent, cells/δ, cells/λ, `\|Im P\|/Re P` and the three gate readings side by side; commissioned 2026-08-26 18:00 review, §5.4 ramp) | ✅ 2026-08-28 (`ports:5`, `20260828T110615Z_EX-34-run2.log`, **139 s** Status 0 at `-n 2` complex; one 116 085-cell mesh, 12 driven solves, all three gates green on all three rungs; 128 MHz cells/λ 12.5024 ≥ 10) | standard |
| `EX-36` | Re-run the examples whose artifacts the 2026-08-28 rename (`67e4c1c`) orphaned — census `dead=53 exit=1` on 2026-08-29 — until it reads `dead=0`; four legs by runner group, each one slot (commissioned 2026-08-30 02:15 weekly review; entry written by the 10:30 daily review) | ⬜ | standard per leg (105 / ≈ 500 / 447 / 935 s measured by `EX-30`) |
| `EX-35` | 16-leg **ring-gapped** birdcage mesh — the 32-ring-port high-pass layout (`GEO-20` step 2's newly gated capability, 2026-08-29: `EX-31`/`mesh:7` cuts the rings at 4 legs, `EX-33`/`mesh:8` cuts the **legs** at 16 — no example has the production high-pass topology at the production leg count; mesh-only, no solve, no port claim; commissioned 2026-08-29 10:30 review, §5.4 ramp) | ✅ | standard |
| `EX-37` | **`ANS-1`/`ANS-3` are unrunnable since the 2026-08-28 rename**: `67e4c1c` rewrote the two cases' `__import__("01_dodd_deeds_coil_loading")` / `("02_package_sparameter_sweep")` strings along with their artifact basenames, and no module of the prefixed name exists — the `ANS-4` slot's observation, verified by the 18:00 review from `git log -S`; restore the two strings, re-run `ans:1` and `ans:3`, census (commissioned 2026-08-30 18:00 review; known-issues entry) | ✅ *(2026-08-31, 19:30 slot — negative control Status 1/3 s, both cases green, 63 s / 128 s)* | standard (≈ 5 + 70 + 131 s + census) |
| `EX-38` | `\|B₁⁺\|` map of the loaded 4-leg birdcage at 10 MHz into ParaView (`WF-6` step 1's newly gated capability, 2026-08-30: the CG1-projected `\|B₁⁺\|` field under gates (i)/(ii) — no example writes a B₁⁺ field, `ports:4`/`ports:5` stop at S-matrices; the output-quantity angle; commissioned 2026-08-30 18:00 review, §5.4 ramp) | ⬜ | standard (≈ 70 s) |
| `EX-39` | Quadrature-driven birdcage: co- and counter-rotating `\|B₁⁺\|` / `\|B₁⁻\|` maps at 10 MHz into ParaView (`WF-6` step 2's newly gated capability, 2026-08-31: exact superposition of the four single-drive fields with `e^{∓jkπ/2}` phases, C4-invariance and the mirror identity at the CG1 floor — the **drive** angle: no example superposes ports or shows the two rotating senses side by side; `EX-38` is the single-drive map; commissioned 2026-08-31 03:00 review, §5.4 ramp) | ⬜ | standard (≈ 100 s) |

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

**`EX-29` — the doc-reference checker must freshness-gate every example's own `paraview_output/`** ✅ *(closed
2026-08-24 06:00 slot; commissioned 2026-08-23 weekly review; smoke, `-n 1`, no solve. Full narrative archived in
`docs/planning/plan-archive.md`, entry «§7 EX-29 full narrative — archived 2026-08-30 (weekly review)».)* Defect: `check_example_doc_references.py` resolved only the repo-root directory
and exempted any basename found under `examples/`, so **22 of 27** runnable examples were never freshness-checked.
> * **Done:** artifacts resolved at their example-relative path with `--max-age-s` applied to all; exemption
>   restricted to `git ls-files`-tracked paths, **pinned by path** in `COMMITTED_EXAMPLE_ARTIFACTS` (three tracked
>   artifacts exist — the "assert empty" instruction would have been false); orphaned
>   `examples/magnetostatics/paraview_output/` deleted.
> * **Gated:** `tests/unit/test_doc_reference_exit_codes.py` **15 passed in 3.71 s** (`20260824T110512Z_EX-29-unit.log`,
>   `-n 1`), whole `tests/unit` 22 passed (`…110540Z_…-run2.log`); negative control on the same tree — pre-fix
>   `stale=24` (`20260824T110150Z_EX-29-prefix-control.log`) vs post-fix **`stale=55`** (`…110531Z_EX-29-census.log`),
>   gate (d)'s independent walk reproducing `stale=55 checked=58 hidden_pre_fix=32` exactly.
> * **Findings:** in-container `git` needs `-c safe.directory=` (dubious-ownership on the bind mount, silently
>   turning tracked artifacts into `dead=1`); known-issues entry closed. `EX-30` re-sized from 55, not 24.

**`EX-30` — refresh the stale example-artifact set the checker could not see** ✅ *(2026-08-26, all four legs;
commissioned 2026-08-23 weekly review, re-scoped 2026-08-24 10:30 review to legs (th) / (root) / (mesh) / (ports)
from the honest `stale=55` census. Every leg's journal, red and census derivation archived in `docs/planning/plan-archive.md`, entry «§7 EX-30 full narrative — archived 2026-08-30 (weekly review)».)*
> * **Leg (th) ✅ 08-25:** all eight `th:` examples green, 105 s; licensed 128 MHz alignment 0.01826 → **0.01769** /
>   57.31 → **59.16** from `20260822T123746Z_OPS-18-step3-th10-rerun.log`, `th:6` reproducing 1.769% (2.02e-04) and
>   59.16× (5.45e-05), 64 MHz 3.643% unmoved; `time_harmonic` census 4 → 0. Reds spawned `OPS-24`, `OPS-25`.
> * **Leg (mesh) 08-25 (4/7 green, licence unused):** `mesh:1` 79 070, `mesh:2` 5 717 cells; reds spawned `GEO-21`
>   (graded-conductor gate), the `GEO-16` 79 534 → 79 070 record class (→ `OPS-27` precedent), `mesh:5`'s control (→ `GEO-17` row).
> * **Leg (ports) ✅ 08-26 (935 s):** `ports:2` restated `‖S−Sᵀ‖/‖S‖` 2.5494e-05 → **4.758625e-05** and `‖S‖₂` 0.861449 →
>   **0.864809457** (the gate's power-wave digits, `PORT-9` leg (d3)), `ports:1` → 3.11213e-05 / 0.861356895; `ans:1`
>   ΔR 1.5838% vs the 1.5834% record; `ports` 4 → 0, `ans` 2 → 0 (`20260826T12…Z_EX-30-ports-*.log`).
> * **Leg (root) ✅ 08-26 (447 s):** `mag:1` `resolution` 0.01 → **0.008**, 21 830 cells, `B(3 mm) = 6.666667e-05 T`
>   (`20260826T170155Z_EX-30-root2-run-mag1.log`); `mag:6` green through `MAG-19` on 21.8417 / 15.3848 / 4.4605%; (1\*)
>   guide re-records `mag:2` 409 596 / 6.2134%, `mag:4` 69 918 / 103 950 / 160 677, `mri:1` 1.979842e+02 (commit `c466143`);
>   earlier `mag:5` 14 055 cells all 7 assertions, `mri:2` SAR 3.31e-16 / 2.81e-15, `mat:1` ΔR 1.5838%. * **Census:** **`dead=0 guide=0 stale=0 exit=0`** (`20260826T171345Z_EX-30-root2-postcensus.log`), the first clean corpus-wide reading since `EX-29`. **Carry-forward:** the `straight_wire_domain` floor entry → `GEO-22` (OPEN).

**`EX-31` — ring-gapped birdcage with dual port families** ✅ *(2026-08-24; `mesh:7`,
`examples/meshing/07_birdcage_ring_gap_ports.py` + same-stem guide, closed as written on the first run; commissioned
2026-08-24 10:30 review as `GEO-20` step 1's ramp obligation. Result and commissioning text archived in
`docs/planning/plan-archive.md`, entry «§7 EX-31 full narrative (result block + commissioning block) — archived 2026-08-30 (weekly review)».)*
> * **Run:** `20260824T200613Z_EX-31-example-n2.log`, exit 0, **70.6 s in-script / 75 s harness at `-n 2`**, real build;
>   every gated figure reproduces `GEO-20` step 1's log (`20260824T124525Z`) to the printed digit.
> * **Ring-gapped rung (110 786 cells = record; 4 leg + 8 ring ports):** terminals **0.974454791 / 0.974454832** of
>   `1.005309649e-04 m²` inside [0.95, 1.0] and the `0.974455 ± 1e-5` record band, spread 2.099e-08 vs 1e-5; closure and
>   volume/analytic **1.000000000000** on all eight; sheets 14 facets, `1.000000000e-04 m²`, meshed/analytic
>   1.000000000000; C4+mirror spreads 1.666e-15 / 2.443e-16 vs 1e-12; Pappus 1.000000000000; conductor 0.969275 ≥ 0.95.
> * **12-port rung (128 402 cells = record):** both identity families exact; leg terminals 0.988615809–0.988615855.
>   **Negative control (inverted):** `ring_gap_length=None` gives tags `[1, 2, 3, 101-104]`, 98 666 cells (ratio
>   1.001950 of the 98 474 record, inside 1%), `_global_facet_count = 0` on every ring sheet group 215–222.
> * **Hoisted to the gate (`ANS-1`):** `RING_TERMINAL_RATIO`, `RING_GAP_CELL_RECORD`, `LEG_RING_CELL_RECORD` now asserted
>   in `tests/mesh/test_birdcage_ring_gaps.py` (`20260824T200739Z_EX-31-gate-module.log`, 2 passed / 70.4 s). Docrefs
>   `…200857Z` `stale=55 exit=2`, 28 runnable examples scanned.

**`EX-32` — birdcage 4-port power-wave S-matrix at 10 MHz** ✅ 2026-08-26 *(15:00 slot, green on the first run;
commissioned 2026-08-25 10:30 review as `PORT-9`'s §5.4 ramp. Full narrative archived in `docs/planning/plan-archive.md`, entry «§7 EX-32 full narrative — archived 2026-08-30 (weekly review)».)*
`examples/ports/04_birdcage_four_port_sparameters.py` + guide, `ports:4` — the first example solving a port on the coil;
it calls leg (d)'s own `build_four_port_sweep()` (lifted to module level, additive), never re-implementing the sweep.
> * **Run:** `20260826T200545Z_EX-32-run1.log`, **88 s** / 85.0 s in-script, Status 0, `-n 2` complex. **Every gate record
>   reproduced:** 116 085 cells at ratio **1.000000**, σ_max **0.999992805**, max column power **0.793823974**, class
>   means 2.338160261e+01 / 1.700854304e+01 / 1.606048044e+01 Ω with spreads **0.0553 / 0.0353 / 0.0214%** vs the
>   imported 0.5%, separation **166.6766×** vs 10×; P1 column vs `LEG_D0_Z_COLUMN` **1.071e-10 … 2.568e-10** vs 1e-9.
> * **Negative control asserted:** the retired `PORT-0` heuristic on the same mesh keeps `is_placeholder=True`, prints an
>   identically zero off-diagonal and separates from the field-derived S by **6.446452e-01** vs the `EX-20` 2e-3 floor.
> * **(d3c) reading:** `‖S − Sᵀ‖/‖S‖` 4.183068067e-13 here vs the module's ~2.152e-14 — both ~11 decades under 1e-3; first
>   evidence the "order of magnitude only" rule is ~1.3 decades wide. Nothing re-recorded.
> * Gate module green after the refactor (`20260826T200746Z_EX-32-gate.log`, 16 passed in 71.98s); census
>   **`dead=0 guide=0 stale=0 exit=0`**, 30/30 guided (`…200908Z_EX-32-census.log`). Scope: 10 MHz only, `PORT-9` caveat verbatim.

**`EX-34` — birdcage 4-port S-matrix across the Larmor frequency ladder, one mesh** ✅ 2026-08-28 *(06:00 slot,
green on the second run — the first hit the runner trap: `run_examples.sh` drives `docker` and must run on the
host; commissioned 2026-08-26 18:00 review as `PORT-11`'s ramp. Full narrative archived in `docs/planning/plan-archive.md`, entry «§7 EX-34 full narrative — archived 2026-08-30 (weekly review)».)*
`examples/ports/05_birdcage_larmor_frequency_ladder.py` + guide, `ports:5`: **one** 116 085-cell mesh (ratio 1.000000,
24.0 s) reused by all three rungs (asserted `reused_mesh`), twelve driven solves, `_four_port_rung` imported.
> * **Run:** `20260828T110615Z_EX-34-run2.log`, **139 s** / 136.8 s in-script, Status 0, `-n 2` complex. Gates imported
>   and asserted on every rung (1e-3 / 1 + 1e-9 / 0.5% / 10×): **10 MHz** 1.657e-14, σ_max 0.999992805, 0.793823974,
>   0.0553 / 0.0353 / 0.0214%, 166.6766×; **64 MHz** 1.179e-15, 0.999721388, 0.804704664, 0.0573 / 0.0599 / 0.0370%,
>   671.0527×; **128 MHz** 5.457e-15, 0.998974779, 0.861668762, 0.1012 / 0.0916 / 0.0654%, 576.9483×. Pre-gate stop
>   rule first: cells/λ **12.5024** ≥ 10 (cells/δ 5.1845), loss tangent 11.5225 → 1.8004 → 0.9002 up the ladder.
> * **Anchors:** 10 MHz reproduces leg (d)'s 4×4 to **1.158e-10** vs 1e-6 and (d0)'s column to 2.568e-10; Larmor rungs
>   reproduce `PORT-11` step 2/3 inside 1% (σ_max 2.814e-10 / 4.374e-11; worst spread misses 1.075e-03 / 6.755e-04 =
>   print precision). **Negative control at 128 MHz:** `PORT-0` heuristic zero off-diagonal, separation **1.585461e+00** vs 2e-3.
> * Gate module green after the additive `reuse=` parameter (`20260828T111019Z_EX-34-gate.log`, 5 passed in 103.07s);
>   census `dead=0 guide=0`, 31/31 guided (`…111008Z_EX-34-census2.log`). **Scope verbatim in the guide: self-consistency
>   identities on one fixture — no resonance, tuning, B1+/SAR or absolute-accuracy claim.**

**`EX-33` — 16-leg gapped + sheeted birdcage mesh** ✅ 2026-08-26 *(13:30 slot, green on the first run;
commissioned 2026-08-25 18:00 review as `GEO-19`'s §5.4 ramp; mesh-only, no solve, no F-human claim. Full narrative
archived in `docs/planning/plan-archive.md`, entry «§7 EX-33 full narrative — archived 2026-08-30 (weekly review)».)* `examples/meshing/08_birdcage_sixteen_legs.py` + guide, `mesh:8`.
> * **Run:** `20260826T183240Z_EX-33-run1.log`, **131 s** / 127.7 s in-script, Status 0, `-n 2` real. The `GEO-19` identity
>   family asserted by the gate module's own `_assert_identity_family` on this run's mesh: partition / air box
>   1.000000000000, 32 halves 0.500000000000, 16 sheets `dx·g` 1.000000000000, C16 sheet spread **1.331e-15** vs 1e-12,
>   closure 1.000000000000, conductor meshed/CAD **0.981503**, separation margin **1.560723×**; azimuth classes
>   `aligned` (8) 0.988615772, 22.5° (4) 0.989367514, 67.5° (4) 0.989449735 — intra **1.923e-07 / 5.849e-08 / 6.144e-08**
>   vs 1e-6, inter **8.431e-04** vs 5e-3.
> * **Negative control asserted:** the in-run 4-leg build reports **one** azimuth class (spread 3.184e-08, inter-class
>   0.000e+00) at **116 085** cells, relative 0.000e+00 against the step-B record.
> * **Cost rung (printed):** 4 → 16 legs, cells 116 085 → 307 296 (**2.6472×**, record reproduced exactly), mesh 26.51 →
>   84.25 s (**3.1777×**) — mesh seconds grow faster than cells.
> * Gate module green after the additive `_measure` return (`20260826T183618Z_EX-33-gate.log`, 2 passed in 124.56s);
>   census **`dead=0 guide=0 stale=0 exit=0`**, 29/29 guided (`…183831Z_EX-33-census.log`). No band or record moved.

**`EX-35` — 16-leg ring-gapped birdcage mesh: the 32-ring-port high-pass layout** ✅ *(2026-08-29 15:00 slot,
green first attempt; commissioned 2026-08-29 10:30 review as `GEO-20`'s §5.4 ramp; mesh-only, legs uncut — 32 sheets,
not 48; no solve, no F-human claim. Full narrative archived in `docs/planning/plan-archive.md`, entry «§7 EX-35 full narrative — archived 2026-08-30 (weekly review)».)*
`examples/meshing/09_birdcage_sixteen_ring_gaps.py` + guide, `mesh:9`, no runner edit needed.
> * **Run:** `20260829T200308Z_EX-35-run1.log`, **104 s** at `-n 2` / 101.1 s in-script, Status 0. Every commissioning
>   record reproduced to the digit: **265 621 cells** (relative 0.000e+00), terminals **0.974454791–0.974455668**, C32
>   sheet spread **4.985e-16** vs 1e-12, conductor meshed/CAD **0.976465** ≥ 0.95, Pappus on the 32 arcs
>   3.134786420778e-05 / 3.134786420778e-05 = 1.000000000000, partition / closure / wedge volume / `w²` sheets
>   1.000000000000 on all 32. Anchor: `_assert_ring_identity_family` imported from the gate module, both rungs.
> * **Azimuth classes 4 at 16 legs / 1 at 4:** intra 4.198e-08 / 4.498e-07 / 4.681e-07 / 8.997e-07 vs 1e-6, inter-class
>   **3.315e-07** vs 5e-3 — four orders inside, against the leg family's 8.431e-04 (`EX-33`): ring-gap cut faces are
>   exact planar disks whose triangulation barely notices azimuth.
> * **Negative control:** in-run 4-leg ring rung **110 786** cells (relative 0.000e+00 vs `RING_GAP_CELL_RECORD`), one
>   class, all eight terminals asserted against 0.974455. **Cost rung (printed):** 110 786 → 265 621 cells (2.3976×),
>   mesh 22.29 → 66.95 s (3.0042×); leg-arc clearance 3.744468e-03 m at 16 legs (Phase 6 count study).
> * Gate module green after the additive `_measure_ring` return (`20260829T200504Z_EX-35-gate-rerun.log`, 1 passed in 183.33 s).

**`EX-36` — re-run the examples whose artifacts the 2026-08-28 rename
orphaned, until the census reads `dead=0`** ⬜ *(commissioned 2026-08-30
02:15 weekly review; this entry written by the 10:30 daily review from the
surviving summary and the census on record.)* Commit `67e4c1c` (2026-08-28)
prefixed every example's output artifacts with group and number across 66
files, and the guides now reference names that exist only once each example
has re-run: the 2026-08-29 census (`20260829T184303Z_WF-6-step1-docrefs.log`)
reads **`dead=53 guide=0 stale=2 exit=1`** where `EX-30` had left it at
`dead=0 stale=0`. No physics moved; the **exit 1** blocks every chunk that
gates on the census, which is why this is queued ahead of its size.
> **Legs, by runner group, each one slot, independent, in cost order —
> the `EX-30` measurements are the estimates:** (th) the eight
> `time_harmonic` examples, **105 s** total (`EX-30` leg (th)); (mesh) the
> nine `meshing` examples (`mesh:3` 41 s, `mesh:8` 131 s, `mesh:9` 104 s,
> `mesh:7` 75 s — ≈ 500 s); (root + mri + mat) `mag:*`, `mri:*`, `mat:1`,
> **447 s** (`EX-30` leg (root)); (ports + ans) `ports:1–5` and `ans:1,3`,
> **935 s** (`EX-30` leg (ports)) — split into two windows if a single
> command would exceed 20 min. **Anchor, per example:** each example's own
> in-script asserts against its gate module's records (every runnable example
> imports its constants — `ANS-1`'s rule), so a green run *is* the
> quantitative check; and per leg, the census `dead` count for that group
> falls to **0** and the group's `stale` to 0 (`check_example_doc_references.py`,
> `exit != 1` reads as the gate, `exit 2` as information). **Negative
> control:** the pre-leg census printed first, showing the group's non-zero
> `dead` count. **Traps:** `run_examples.sh` on the host; docker-socket
> denial ⇒ the §9 substitution; magnetostatics 01/02/04/05/06 and `mri:1`
> write to the repo-root `paraview_output/` via a cwd-relative path (the
> rename commit's note), so run them from the repo root; any example that
> reds is **not** fixed in-slot — it gets a known-issues entry and the leg
> stops at its census figure. **Scope:** artifacts only; no record, band or
> guide number moves; a leg whose examples all reproduce is ✅ for that leg,
> the chunk ✅ when the whole census reads `dead=0`. **Negative result:** a
> red example is a finding about that example on the 0.11 image — journal,
> known-issues, stop.

**`EX-37` — restore the `ANS-1`/`ANS-3` example imports the rename broke**
✅ *(commissioned 2026-08-30 18:00 review; executed 2026-08-31, 19:30
slot.)* `67e4c1c` prefixed every
example's artifacts by a global text substitution, and in the two ANS
scripts the substitution also hit the `__import__` string that loads the
gated example module:
`examples/ansys_benchmarks/loop_over_lossy_slab_10MHz/01_loop_over_lossy_slab_10MHz.py:96`
now asks for `01_materials_01_dodd_deeds_coil_loading` and
`…/two_torus_gap_ports_10MHz/03_two_torus_gap_ports_10MHz.py:88` for
`02_ports_02_package_sparameter_sweep`, while the files on disk are
`examples/materials/01_dodd_deeds_coil_loading.py` and
`examples/ports/02_package_sparameter_sweep.py` (`git log -S` shows both
strings born in that commit; `EX-30` leg (ports) had both cases green two
days earlier). Both raise `ModuleNotFoundError` at import; their ✅
runnable halves are unrunnable and `EX-36` leg (ports + ans) would red on
them. `ANS-4` sidestepped it by importing by path.
> **Build:** restore the two strings to the on-disk stems (two one-line
> edits, nothing else); `grep -rn '__import__(' examples tests` must show no
> other renamed stem. **Anchor:** `./run_examples.sh -e ans:1 -n 2 -t 300`
> and `-e ans:3 -n 2 -t 500` green — each script's own asserts against its
> gate module's records (`ANS-1`'s Dodd–Deeds slab numbers, `ANS-3`'s
> two-port Z/S at their 08-26 `EX-30` digits) are the quantitative check;
> the post-run census reads the two cases' artifacts fresh (`dead=53` is
> `EX-36`'s and stays — this chunk owns none of it). **Negative control,
> first:** `ans:1` on unpatched `main` through the harness — Status ≠ 0
> with `ModuleNotFoundError: No module named
> '01_materials_01_dodd_deeds_coil_loading'` in the log, within seconds.
> **Cost:** ≈ 5 s + 70 s (`ANS-1`, 08-09) + 131 s (`ANS-3`, 08-16) +
> census ≈ **4 min**, standard, `-n 2`; runner on the host, docker-socket
> denial ⇒ the §9 substitution. **Traps:** the `ans:` group nests one
> directory deep; `-t` is the runner's own timeout; a script that reds for
> any *other* reason is not fixed in-slot — known-issues, stop. **Scope:**
> the two import strings only; no record, band, number or guide moves;
> `EX-36` leg (ports + ans) is serial on this landing. **Negative result:**
> either case still red after the fix — a second, different 08-28
> breakage; extend the known-issues entry with the traceback, stop.

> **DONE 2026-08-31 (19:30 slot), exactly as scoped — two strings, nothing
> else.** **Negative control first**, on unpatched `main`
> (`20260831T003025Z_EX-37.log`): `./run_examples.sh -e ans:1 -n 2 -t 300`,
> **Status 1 / 3 s**, `ModuleNotFoundError: No module named
> '01_materials_01_dodd_deeds_coil_loading'` — the first observation of this
> defect in a harness log, the known-issues entry having been written from
> reading alone. Both strings restored to their on-disk stems;
> `grep -rn '__import__(' examples tests` shows those two call sites and no
> other renamed stem. **Anchors, both green on the patched tree at `-n 2`:**
> `ans:1` **Status 0 / 63 s** (`20260831T003037Z_EX-37.log`) with the script's
> own Dodd–Deeds assert reading **ΔR 1.5838%** against its 2% ceiling and the
> `MAT-6` step-3 record of 1.5834%; `ans:3` **Status 0 / 128 s**
> (`20260831T003145Z_EX-37.log`) reproducing the `PORT-1` step-4 record inside
> its 1% band (raw 2.98e-05, corrected 2.92e-05) with reciprocity
> `max|Sij−Sji|` 4.097e-05 (rel 1.897e-03) and passivity `σ_max` 0.864809.
> The two `metrics.json`/`COMPARISON.md` pairs are regenerated by the runs:
> every physical figure reproduces its committed value to ≤ ~1e-8 relative
> (`ANS-1` `R_ohm` 0.3277053865833211 vs …251; `ANS-3` `S₁₁` −8.2459527e-01
> +2.4709965e-01j vs …964j) — **no record, band or ceiling was moved**; what
> moved is timestamps, wall-clock timings and solver noise in the last digits.
> **Census** (`20260831T003409Z_EX-37-docrefs.log`): `dead=53 guide=0
> stale=10 stale_severity=report exit=1` — `dead=53` and `guide=0` unchanged
> and entirely `EX-36`'s; the 10 stale are **age-only** (52.4 h / 52.2 h /
> 52.1 h against a 48 h limit, eight `magnetostatics_01_straight_wire_*` plus
> `ports_01_*`/`ports_02_*_combined.xdmf`) and **none is an `ans_*`
> artifact** — this chunk's two cases wrote fresh ones and are absent from the
> list. The `stale=2` → `10` step is the 48 h clock advancing over examples
> nobody re-ran, not a regression; a review may decide whether that set is
> worth a refresh run. Known-issues entry removed in this commit.
> **`EX-36` leg (ports + ans) is unblocked.** No claim about either
> benchmark's accuracy follows: the ✅ runnable halves keep their 08-09 /
> 08-16 records, and the AED columns are still blank.

**`EX-38` — the first `|B₁⁺|` field in ParaView: loaded 4-leg birdcage at
10 MHz** ⬜ *(commissioned 2026-08-30 18:00 review, §5.4 ramp, from `WF-6`
step 1 ✅.)* No example writes a B₁⁺ field — `ports:4`/`ports:5` stop at
S-matrices, and `WF-6`'s map lives only in a test module.
> **Build:** `examples/ports/06_birdcage_b1_plus_map.py` + same-stem guide
> (`ports:6`): `build_four_port_sweep`'s fixture, **two** lumped-sheet
> solves (P1 and P2, 5.6–6.0 s each on the 116 085-cell mesh),
> `post.magnetic_flux_density_from_e` → `post.project_to_cg1` →
> `post.b1_plus`, and one combined XDMF carrying the CG1 `B` phasor
> (real/imag), `|B₁⁺|` and the phantom cell tags — the phantom `|B₁⁺|` map
> is the deliverable. Every constant, band and record imported from
> `tests/validation/test_birdcage_b1_plus_map.py` (`ANS-1`'s rule), nothing
> restated. **Anchors (in-script asserts):** gate (i)'s three-way power
> accounting at P1 reproduces **9.795751e-03** at rtol 1e-4 (band 1e-2
> imported); the CG1 C4 covariance P1 → P2 at +90° reproduces **2.1870%**
> at rtol 1e-3 against the imported 5% band; `valid` 51/51; cell ratio
> 1.000000 with `reused_mesh`. **Negative control:** the DG0 `|B₁⁺|` read
> on the same 51 points prints its **8.6516%** (rtol 1e-4) beside the CG1
> figure — the example shows the estimator floor the gate was re-registered
> around, and a DG0 column that moved would mean the field changed.
> **Cost:** mesh ~22 s + two solves ~12 s + two projections + XDMF export
> ≈ **70 s**, standard, `-n 2`, `-t 300`, complex; docrefs census
> `exit != 1` for *this* example's artifacts (`EX-36`'s 53 are not this
> chunk's). **Traps:** runner on the host, docker-socket substitution;
> `ports:6` must not collide with an existing stem; DG0 `fem.Expression`
> interpolation of a UFL `curl` needs the DG0 interpolation points;
> `|B₁⁺|` is real stored complex — write `.real`. **Scope:** what gates
> (i)/(ii) license — a map and its symmetry identity at 10 MHz on F-small;
> **no** homogeneity/CV, no 64/128 MHz, no quadrature drive (`WF-6`
> step 2), no absolute claim. **Negative result:** a record not
> reproducing is a finding about the example path — known-issues, stop; no
> band moves.

**`EX-39` — the quadrature drive in ParaView: `|B₁⁺|` and `|B₁⁻|` of the
loaded 4-leg birdcage at 10 MHz** ⬜ *(commissioned 2026-08-31 03:00 review,
§5.4 ramp, from `WF-6` step 2 ✅.)* `WF-6` step 2 gated the quadrature drive
by exact superposition (C4-invariance 0.9818%, mirror identity 0.8087% vs 5%)
and read a centre polarisation purity of 127.9 — the number MRI cares about —
in a test module nobody opens in ParaView. `EX-38` writes the *single-drive*
map; no example superposes the four ports or shows the co- and
counter-rotating senses together.
> **Build:** `examples/ports/07_birdcage_b1_quadrature_map.py` + same-stem
> guide (`ports:7` — the runner selects by filename prefix,
> `scripts/run_examples.sh:180–184`, so this does not wait on `EX-38`'s
> `ports:6`). `build_four_port_sweep`'s fixture, **four** lumped-sheet solves
> (P1…P4, 5.6–6.0 s each on the 116 085-cell mesh),
> `post.magnetic_flux_density_from_e` on each, superpose the four DG0 curls
> with `e^{∓jkπ/2}` on the fixture's azimuth index for the two senses
> (**lift the phase convention from
> `tests/validation/test_birdcage_b1_quadrature.py` verbatim** — the sign
> slip that cost step 2 a window is documented in that module's docstring),
> `post.project_to_cg1` → `post.b1_plus` / `post.b1_minus`, and one combined
> XDMF carrying, for the ccw drive, the CG1 `B` phasor, `|B₁⁺|` and `|B₁⁻|`
> (the near-null counter-rotating map is the picture), plus the phantom
> tags. Every constant, band and record imported from
> `test_birdcage_b1_quadrature.py` / `test_birdcage_b1_plus_map.py`
> (`ANS-1`'s rule). **Anchors (in-script asserts):** (a) C4-invariance of the
> quadrature `|B₁⁺|` map reproduces **0.9818%** at rtol 1e-3 against the
> imported 5% band; (b) the mirror identity reproduces **0.8087%** at rtol
> 1e-3; gate (i) at P1 **9.795751e-03** at rtol 1e-4; the four solves share one
> `Z_p` and one `V_src` (the superposition premise, asserted); `valid`
> 51/51; cell ratio 1.000000, `reused_mesh`. **Negative control:** the
> mis-paired `|B₁⁺|_cw(Mx)` vs `|B₁⁺|_ccw(x)` misses the band (reads
> **95.1975%**, asserted > 5%). **Printed, ungated, labelled as such:**
> centre `|B₁⁺|/|B₁⁻|` (record 127.9083 / 0.0081), mean `|B₁⁺|` (record
> 7.976427e-08 T at 1 V per port), CV over the 51 centroids (2.7563%) — the
> guide says in one sentence why none of these is a homogeneity claim.
> **Cost:** mesh ~22 s + four solves ~24 s + four curls, two projections and
> the XDMF ≈ **100 s**, standard, `-n 2`, `-t 400`, complex; docrefs census
> `exit != 1` for *this* example's artifacts. **Traps:** host runner,
> docker-socket substitution; `ports:7` must not collide with an existing
> stem; DG0 `fem.Expression` of a UFL `curl` needs the DG0 interpolation
> points; magnitudes after the point evaluation; `|B₁⁺|` real stored
> complex — write `.real`; `./run_examples.sh -e ports:6..7` is **not** a
> valid token (WF-6 step 2 paid a window for it). **Scope:** what step 2
> licenses — two maps and two symmetry identities at 10 MHz on F-small;
> **no** homogeneity/CV claim, no 64/128 MHz (`WF-6` step 2b), no SAR, no
> absolute claim. **Negative result:** a record not reproducing is a
> finding about the example path — known-issues, stop; no band moves.

### ANS — Ansys benchmark cases (§5.4)

Commissioned by the weekly planning review only, on gated physics only; the
human operator replicates each case in Ansys Electronics Desktop and the
next weekly review adjudicates the returned numbers.

| ID | Title | Status | Tier |
|---|---|---|---|
| `ANS-1` | Loop over a lossy slab at 10 MHz: runnable half of the first AED benchmark | ✅ *(example path restored 2026-08-31 by `EX-37` and re-run green, 63 s; the 08-09 record stands)* | standard |
| `ANS-3` | Two coaxial gapped loops at 10 MHz: runnable half of the second AED benchmark (2-port Z/S; `ANS-2` reserved by §10 for the future B1+/SAR case) | ✅ *(example path restored 2026-08-31 by `EX-37` and re-run green, 128 s; the 08-16 / 08-26 records stand)* | heavy |
| `ANS-4` | **Gapped four-leg birdcage, phantom-loaded, four lumped ports: 4×4 S-matrix at 10 / 64 / 128 MHz — runnable half** (commissioned 2026-08-30 02:15 weekly review; authoritative spec `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/SPEC.md`; the first independent absolute check of the coil-fed port model at a Larmor frequency) | ✅ **runnable half 2026-08-30** (`20260830T213415Z_ANS-4-run1.log`, Status 0, 125 s at `-n 2`) — all three gates on all three rungs of one 116 085-cell mesh (ratio 1.000000, `reused_mesh`); 10 MHz reproduces leg (d)'s 4×4 to **1.158e-10** (band 1e-6) and leg (d0)'s column to **2.568e-10** (band 1e-9); 64 / 128 MHz reproduce `PORT-11` steps 2/3 to worst **1.075e-03** / **6.755e-04** (band 1e-2); control separation **1.585460** vs 2e-3. **Operator's AED replication at both orders is now Waiting-on-you; adjudication is a weekly review's** | heavy (≈ 160 s at `-n 2`, one command; measured 125 s) |
| `ANS-5` | **Pin the element-order correspondence in every ANS `SPEC.md`/`COMPARISON.md`** — our production `degree 1` is what HFSS calls **Zero Order**, not its default **First Order**; the specs do not say so, and a default-settings replication is a different discretization (operator observation, interactive session 2026-08-28) | ⬜ **RULED 2026-08-30 02:15 weekly review** — (a) AED runs at **Zero Order** (matched, the adjudication column) **and** at its default **First Order** (an order-sensitivity column); **Mixed Order forbidden**; our side stays at one order (none of options 1–3 as framed — option 1 for the adjudication column plus a second AED column, our side unchanged, step 3 **not** taken). (b) `ANS-1` **is in scope** for the spec line (state the Maxwell 3D formulation and order AED used). Already-returned numbers at an unrecorded order stand as an "order-unknown" column. Steps 1–2 are documentary and queueable; `ANS-4`'s spec already carries the wording. **Steps 1–2 executed 2026-08-31 00:00 slot — 🟡:** README correspondence table + a *Basis / element order* paragraph in all three SPECs (four `*.md` files, +71/−3, no band or figure moved); the `ANS-1`/`ANS-3` `COMPARISON.md` rows need a **generator `.py`** edit the item's scope forbids — carried as a finding, **priced as step 1b by the 03:00 review (§9 item 2)**. **Step 1b executed 2026-08-31 06:00 slot — chunk ✅** (steps 1, 1b, 2; step 3 ruled not taken): both generators' `_write_comparison` now emit `AED (Zero Order)` / `AED (First Order)` and a `Basis order` row, both cases re-run green on their own asserts (ΔR **1.5838%** vs 2%; `PORT-1` step-4 reproduction **2.98e-05 / 2.92e-05 / 1.71e-06 / 3.33e-10** inside 1%, reciprocity 4.7586e-05 < 1e-3, ‖S‖₂ 0.864809 ≤ 1), census at the standing `dead=53 guide=0 stale=10`. The pre-registered ≤ 1e-8 `metrics.json` negative control **is not a valid discriminator for `ANS-3`** — measured below | smoke (no compute; step 1b ≈ 200 s, measured 61 + 133 s + 125 s control + 1 s census) |


**`ANS-5` — pin the element-order correspondence in the benchmark specs** 🟡
*(**RULED 2026-08-30 02:15 weekly review — see the table row above for (a)
and (b); step 3 is not taken.** **Steps 1–2
executed 2026-08-31 00:00 slot** — the SPEC and README half landed on all
three cases; the `ANS-1`/`ANS-3` `COMPARISON.md` half is a generator (`.py`)
change this chunk's scope forbids, carried as a finding at the foot of this
entry — **priced by the 2026-08-31 03:00 review as step 1b, §9 item 2; the
chunk is ✅ when it lands.** Original entry follows unchanged.)* *(raised by the human operator, interactive session 2026-08-28, on noticing
that Ansys defaults to First Order basis functions with Zero / Second / Mixed
offered. **The weekly review owns §5.4 and must rule on (a) and (b) below
before any step executes**; this entry is the drafting session's
recommendation, not a decision.)*

> **The finding, measured.** Ansys and FEniCS name curl-conforming bases by
> different conventions — HFSS by the polynomial order of the tangential
> field, FEniCS by the Nédélec index — and they are off by one. Unknowns per
> tetrahedron, our side measured directly on the 0.11 image (2026-08-28):
>
> | HFSS name | unknowns/tet | ours | measured DOF/tet |
> |---|---|---|---|
> | Zero Order | 6 (edges only) | `degree=1` — **our production order** | **6** |
> | **First Order** *(HFSS default)* | 20 (edges + faces) | `degree=2` | **20** |
> | Second Order | 45 | `degree=3` | **45** |
> | Mixed Order | per element | **no equivalent** — `TimeHarmonicSolver.degree` is one global int | — |
>
> The 6/20/45 column is measured; the HFSS column is the standard basis
> definition and **the review should have the operator confirm it against the
> matrix statistics AED prints** before it is written into a spec as fact.
>
> **Why it matters here.** A replication run at AED's defaults compares a
> 20-unknown element against our 6-unknown one. That is a discretization
> difference, not a modelling difference, and it lands in the same column as
> the physics: any ΔZ / S-parameter gap would be misattributed. The size of
> the effect is not hypothetical — on `TH-10`'s sphere at *identical* 5 866
> cells, degree 1 → degree 2 moves interior relL2 **8.1541% → 0.1405%** and
> ohmic power error **8.3869% → 0.0058%** (`TH-12` step 1 / `EX-25`). Ohmic
> power is the integral SAR routes through.
>
> **Where the specs are silent.** `examples/ansys_benchmarks/README.md`
> promises a `SPEC.md` "precise enough to build in AED with **no further
> questions**". It is not, on this axis: `ANS-3`'s *Frequency and solver*
> section says "HFSS driven solve with the two lumped ports … Direct solver
> preferred" and stops; `ANS-1`'s *Solve and mesh guidance* pins adaptive
> refinement to ≤ 0.5% energy error and elements per skin depth but no order.
> Our own side is already stated — `ANS-1`'s `COMPARISON.md` *Solve metadata*
> row reads "138490 tetrahedra, lowest-order Nédélec edge elements (`N1curl`,
> degree 1)" with the AED cell blank — so the asymmetry is that **we declare
> our order and never ask AED for its own.** By the weekly review's own
> commissioning standard — a `SPEC.md` with "no judgement calls left to the
> operator" (docs/automation/weekly-review.md step 5) — the basis order is a
> judgement call the specs currently leave to the operator, and the operator
> made it by accepting a default.
>
> **(a) THE RULING: which side moves.** The three options are not symmetric
> and the drafting session does **not** recommend one:
>
> 1. **Set AED to Zero Order.** Apples-to-apples, zero cost, keeps our
>    production order. But it benchmarks a configuration no HFSS user runs,
>    and it makes the operator's default experience diverge from the
>    benchmark's.
> 2. **Raise our side to `degree=2` for benchmark cases.** Matches the AED
>    default — but for **coil-fed** solves this is exactly the configuration
>    §10 rejected on 2026-08-23: complex-power identity miss **3–5e-9** vs a
>    1e-9 bound, **99.6%** spurious electric energy, **96.8%** of `memory.max`
>    on the 138 k-cell fixture. Putting a benchmark on an order the plan does
>    not license for that drive would make the benchmark unciteable for the
>    thing it exists to check.
> 3. **Report both orders on our side.** AED's default column then faces our
>    degree 2, and our production degree 1 is carried alongside. Costs one
>    extra solve per case and doubles the `COMPARISON.md` table width; on the
>    coil cases it also means publishing a degree-2 column the plan says is
>    not production-grade, which needs wording, not just a number.
>
> **(b) THE SECOND RULING: what "matched order" means for `ANS-1`.** It is a
> **Maxwell 3D eddy-current** case, not an HFSS driven solve; the basis
> dropdown the operator saw is not the same control. The review must say
> whether `ANS-1` is in scope at all, or whether this chunk is HFSS-solver
> cases only (`ANS-3`, and `ANS-4` when commissioned).
>
> **Step 1 — the template (no compute).** Add a mandatory *Basis / element
> order* line to the SPEC solver section and a matching row to
> `COMPARISON.md`'s *Solve metadata*, with the correspondence table above
> stated once in `examples/ansys_benchmarks/README.md`. **Whatever (a) rules,
> the spec must forbid Mixed Order** — we have no per-element order and could
> not reproduce it, so a Mixed-Order AED run is not comparable to any run of
> ours.
>
> **Step 2 — retro-fill.** Apply the ruling to `ANS-1` and `ANS-3`, and fold
> it into `ANS-4`'s spec when the review commissions it. If either case has
> **already** been replicated in AED by then, its returned numbers were taken
> at an unrecorded order and the review must decide whether they stand,
> re-run, or are annotated as order-unknown.
>
> **Step 3 — only if (a) rules option 3.** Add the second solve to each
> runnable half and record both orders with elapsed times. This is the only
> step with compute; `ANS-3` is heavy tier (131 s at `-n 2` on 178 055 cells),
> so a second order roughly doubles it and `degree=2` memory on that fixture
> is unpriced — **price it before adopting option 3.**
>
> **Definition of done (§4).** Documentary for steps 1–2: no band, no
> tolerance, no recorded figure moves, and no physics claim is added. If step
> 3 runs, its gate is the recorded pair of solves with elapsed times, and the
> `COMPARISON.md` wording must carry §10's licence limits verbatim rather than
> presenting a degree-2 coil column as production.
>
> **Non-goals.** This chunk does **not** re-open the production element order
> — that is §10's decision of 2026-08-23 and `TH-13`'s discriminator, and a
> benchmark convenience is not the evidence class that moves it. It commissions
> no new benchmark case. It does not touch `TH-13`.
>
> **Executed 2026-08-31 00:00 slot — steps 1–2 landed, documentary, no
> compute (§9 item 4).** The ruling is now written into the specs. `git diff
> --stat`: `examples/ansys_benchmarks/README.md` (+40),
> `birdcage_four_port_10_64_128MHz/SPEC.md` (+3/−1),
> `loop_over_lossy_slab_10MHz/SPEC.md` (+18/−1),
> `two_torus_gap_ports_10MHz/SPEC.md` (+13/−1) — four files, `*.md` under
> `examples/ansys_benchmarks/` only, **no band, tolerance, recorded figure or
> physics claim moved**; the only numerals added are the 6 / 20 / 45
> correspondence already stated in this entry. Written: the correspondence
> table + the ruling (two AED columns, Mixed Order forbidden, unknowns/tet
> confirmation asked, order-unknown disposition) once in the README as a
> *Basis / element order — mandatory in every `SPEC.md`* section; a *Basis /
> element order* paragraph in `ANS-3`'s *Frequency and solver* and `ANS-1`'s
> *Solve and mesh guidance*, both pointing at the README table; `ANS-4`'s
> existing paragraph given the same README pointer so the three read as one
> form. `ANS-1`'s carries ruling (b) explicitly — Maxwell 3D, so it asks for
> the **formulation** and the order AED used, and for an **order-unknown**
> label if the solver offers no choice. Both SPEC *Quantities to export*
> tables gained basis order / unknowns-per-tet in their Solve-metadata row.
> **Documentary chunks execute no verification command; this one is the §5.2
> no-op guard's licensed exception, ruled queueable by the 02:15 weekly
> review — the done-when is the diff, and it is stated above.**
>
> **Finding carried to the review — step 1's `COMPARISON.md` half cannot be
> done for `ANS-1`/`ANS-3` inside this chunk's scope.** Both files are
> **generated whole** by their runnable halves
> (`01_loop_over_lossy_slab_10MHz.py:145` and
> `03_two_torus_gap_ports_10MHz.py:155` write the entire document, Solve
> metadata table included), so a hand edit to either `.md` is silently
> reverted by the next `ans:1` / `ans:3` run — and `EX-36` leg (ports + ans)
> is queued to make exactly those runs. Adding the *Basis order* row and the
> second AED column there is a **`.py` change**, which §9 item 4 forbids in
> as many words ("do not touch the two `.py` files item 1 edits") and which
> its `*.md`-only done-when excludes. Nothing was edited in those two files.
> `ANS-4` needs no such change — its generator already emits `AED (Zero
> Order)` / `AED (First Order)` columns and a `Basis order` row
> (`04_birdcage_four_port_10_64_128MHz.py:192`). **Residual work, for a
> review to scope:** a ≈ 10-line, two-file generator edit plus one `ans:1` +
> `ans:3` re-run to regenerate both documents (≈ 70 + 131 s, one runner
> window each). Until it lands the two older `COMPARISON.md` files carry a
> single unlabelled `AED` column while their SPECs ask for two — the specs
> are the authority the operator builds from, so the asymmetry misleads
> nobody, but it is not the "one form" step 2 asks for.
>
> **Not done, deliberately:** step 3 (ruled not taken); the README's *Cases*
> list, which still names only `ANS-1` and has been missing `ANS-3` and
> `ANS-4` since each was commissioned — pre-existing drift, outside this
> chunk's scope, flagged here for a review.
>
> **Step 1b — the generator half, scoped 2026-08-31 03:00 review (the
> finding above, priced; documentary in intent, but it re-runs two gated
> examples so it carries a harness log).** Standard tier, complex build,
> `-n 2`, host runner (docker-socket denial ⇒ the §9 substitution). **Build:**
> in `01_loop_over_lossy_slab_10MHz.py::_write_comparison` (`:145`) and
> `03_two_torus_gap_ports_10MHz.py::_write_comparison` (`:155`), replace the
> single `AED` column by `AED (Zero Order)` / `AED (First Order)` and add a
> `Basis order` row to the Solve-metadata table, lifting the wording from
> `04_birdcage_four_port_10_64_128MHz.py:192` so the three read as one form;
> the two `SPEC.md` files already ask for exactly these columns (steps 1–2).
> Also add `ANS-3` and `ANS-4` to the README *Cases* list (the second
> finding; `*.md`, three lines). **No other line of either `.py` changes** —
> no constant, band, ceiling or record, and nothing in the physics path
> between the solve and `metrics.json`. Then `./run_examples.sh -e ans:1 -n 2
> -t 300` and `-e ans:3 -n 2 -t 500` regenerate both documents, and the census
> runs. **Anchors:** the two scripts' own asserts, unmoved — `ANS-1`'s
> Dodd–Deeds ΔR against its 2% ceiling (reads 1.5838%, record 1.5834%) and
> `ANS-3`'s `PORT-1` step-4 reproduction inside 1% with reciprocity and
> passivity (4.097e-05, σ_max 0.864809 on 2026-08-31) — so a green run is
> the quantitative check; plus the regenerated `metrics.json` physical figures
> reproduce the committed ones to ≤ 1e-8 relative (`EX-37` measured
> ~1e-13 / ~3e-9), checked by the implementer from `git diff`, not by eye.
> **Negative control:** `git diff -- '*metrics.json'` shows *only*
> `generated_utc`, `*_seconds` and last-digit noise — a moved physical figure
> means the generator edit touched the physics path, and the slot stops.
> **Cost:** ≈ 63 + 128 s + census (2026-08-31 measurements), two runner
> windows. **Traps:** the `ans:` group nests one directory deep; the
> generators write the *whole* document, so verify the new columns/row appear
> in both regenerated files by reading them, not by assuming; `EX-36` leg
> (ports + ans) will re-run both cases again later and must reproduce the
> same documents — fine and expected. **Scope:** two `_write_comparison`
> bodies and three README lines; step 3 stays not taken; nothing under `src/`
> or `tests/`; `ANS-4`'s files are not touched. **Done-when:** both regenerated
> `COMPARISON.md` files carry the two AED columns and the `Basis order` row,
> both runs green, `metrics.json` physics unmoved — **`ANS-5` ✅** (steps 1,
> 1b, 2; step 3 ruled not taken). **Negative result:** either case red for
> any reason other than the edit — revert the edit, known-issues, stop.
>
> **Step 1b reading — executed 2026-08-31, 06:00 slot; `ANS-5` ✅.** Both
> `_write_comparison` bodies now emit `AED (Zero Order)` / `AED (First
> Order)` in every AED-bearing table and a `Basis order` row in Solve
> metadata, with the `04_…py` order paragraph lifted verbatim; the README
> *Cases* list gained `ANS-3` and `ANS-4`. The `.py` diff is confined to the
> two functions — no constant, band, ceiling or record moved — and both
> regenerated documents were read back to confirm the columns
> (`COMPARISON.md` `:24`/`:66`/`:69` and `:23`/`:48`/`:57`/`:87`/`:90`).
> **`ans:1`** `20260831T110240Z_ANS-5-step1b-ans1.log`, Status 0, 61 s: ΔR
> **1.5838%** against the 2% ceiling, 4.048e-06 relative from the pin,
> σ = 0 control exactly 0.0 W / 0.0 A/m², energy ratio 1.0000.
> **`ans:3`** `20260831T110908Z_ANS-5-step1b-ans3-final.log`, Status 0,
> 133 s: raw 0.894516 a **miss** at −10.55% (the inverted control),
> corrected 0.939822 at −6.02% inside the 10% band, ‖S − Sᵀ‖/‖S‖
> **4.7586e-05** < 1e-3, ‖S‖₂ **0.864809** ≤ 1, `PORT-1` step-4
> reproduction **2.98e-05 / 2.92e-05 / 1.71e-06 / 3.33e-10** inside the 1%
> band. Census `20260831T111136Z_ANS-5-step1b-census.log` at the standing
> `dead=53 guide=0 stale=10 exit=1`, no `ans_*` among the ten stale.
>
> **Finding — the ≤ 1e-8 `metrics.json` negative control is not a valid
> discriminator for `ANS-3`, and never was.** The first `ans:3` run
> (`20260831T110348Z…`, Status 0, 123 s) moved `Z₁₁` Im by **4.9e-8**
> relative against the committed file, over the pre-registered 1e-8. Rather
> than stop on a control whose premise (*a moved figure means the edit
> touched the physics path*) is untestable by inspection, the slot ran the
> decisive experiment: `git checkout HEAD --` the generator and re-ran the
> identical command (`20260831T110634Z_ANS-5-step1b-ans3-unedited-control.log`,
> Status 0, 125 s). **The unedited generator misses the band too** — `Z₂₂`
> Im 7.164396053162261 → 7.164396135620619 (**1.15e-8** relative), `S₂₂` Im
> 1.1e-8, `‖S − Sᵀ‖/‖S‖` 4.7586448e-05 → 4.7586412e-05 (7.6e-7 relative,
> cancellation-amplified). So the run-to-run scatter of this 177 998-cell
> two-rank iterative sweep reaches ~1e-8–5e-8 on the Z/S entries
> intrinsically; `EX-37`'s single ~3e-9 observation (2026-08-31 19:30),
> from which the 1e-8 figure was priced, was one draw from that
> distribution, not its width. `ANS-1` is unaffected — its physics
> reproduces at ~1e-15 relative (`delta_R_ohm` 0.3277053865833211 →
> …215) and passes ≤ 1e-8 comfortably. **For a review:** the honest
> negative control for `ANS-3` is the scripts' own `PORT-1` step-4
> reproduction band (1%, and every entry sits ≤ 3e-05 inside it), not a
> byte-level `metrics.json` diff; a future item should either quote
> ~1e-7 for `ANS-3` or drop the figure and cite the in-script band.
> Consequently the chunk is closed on the pre-registered *gated* anchors,
> which all held, with the band finding recorded rather than the band
> quietly widened.

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

**`ANS-4` — loaded birdcage 4-port S-matrix at 10 / 64 / 128 MHz: runnable
half** ✅ **2026-08-30** *(commissioned 2026-08-30 by the weekly planning review — its
`SPEC.md` landed via `recovered/2026-08-30T1100Z`; this entry written by the
10:30 daily review to give the commission its runnable-half chunk, mirroring
`ANS-3`'s shape. Physics gated by `PORT-9` ✅ and `PORT-11` ✅; the case is the
mission's first absolute check at a Larmor frequency.)* Regenerate the gated
4×4 numbers through the **`ports:5` path** — `build_four_port_sweep` /
`_four_port_rung` imported from `examples/ports/05_birdcage_larmor_frequency_ladder.py`
and the `PORT-9`/`PORT-11` gate modules, never re-implemented or
hand-transcribed — into the case directory as
`04_birdcage_four_port_10_64_128MHz.py` + same-stem guide: `metrics.json`
(full complex 4×4 `Z` and `S` per frequency, the three gate figures, mesh /
timing / basis-order metadata), `COMPARISON.md` with our columns filled and
the AED columns (Zero Order **and** First Order, per `ANS-5`) blank per SPEC,
and one combined XDMF (the P1-driven field at 128 MHz through the shared
`post.faraday` helper). Dispatch through the runner's `ans:` group
(`./run_examples.sh -e ans:4 -n 2 -t 500`).
> **Anchor:** every gate asserted on every rung with the imported bands —
> `‖S−Sᵀ‖/‖S‖ ≤ 1e-3`, `σ_max ≤ 1 + 1e-9`, C4 class spreads ≤ 0.5% — and
> the records reproduced: 10 MHz `LEG_D_S_MATRIX_10MHZ` to **1e-6** and
> (d0)'s column to 1e-9; 64 / 128 MHz inside `LARMOR_RECORD_BAND = 1e-2` of
> `PORT-11` steps 2/3 (σ_max 0.999721388 / 0.998974779, spreads
> 0.0573 / 0.0599 / 0.0370% and 0.1012 / 0.0916 / 0.0654%); mesh **116 085**
> cells at ratio 1.000000, `reused_mesh` asserted. **Negative control:** the
> retired `PORT-0` heuristic on the same mesh at 128 MHz, zero off-diagonal,
> separation **1.585461** against the 2e-3 floor — printed first, as
> `EX-34` does. **Tier/cost:** `ports:5` is **139 s** at `-n 2` for the
> twelve driven solves on one mesh (`20260828T110615Z_EX-34-run2.log`) plus
> one export solve ≈ 8 s ⇒ ≈ **160 s**, one command, container
> `timeout -k 30 500`, heavy tier by the runner's `-t 500`. **Traps:**
> complex mode + `FEM_EM_REQUIRE_COMPLEX=1`; `run_examples.sh` runs on the
> **host** (`EX-32`/`EX-34` trap) and its docker-socket denial has one
> occurrence — substitute the inner command through `run_and_log.sh` per
> §9; the `ans:` group nests one directory deep, so the new script's
> basename must carry the `04_` prefix and the guide must exist for the
> census (`guide=0`); artifacts are group-and-number prefixed since
> `67e4c1c`; the docrefs checker reads `exit != 1` as the gate. **Scope:**
> runnable half only — no adjudication, no tuning / resonance / absolute
> claim from our side; on landing the operator's two AED runs are already
> the dashboard's Waiting-on-you item 1 and the next weekly review
> adjudicates. **Negative result:** any drift from the gated records outside
> the imported bands is a finding about the example path — report, annotate
> this entry, stop.
>
> **Executed 2026-08-30 16:30 slot — ✅, everything green on the first run.**
> `./run_examples.sh -e ans:4 -n 2 -t 500` through the harness
> (`20260830T213415Z_ANS-4-run1.log`, **Status 0, 125 s**, heavy tier): the
> host runner did **not** hit the docker-socket denial, so no substitution was
> needed. Written: `04_birdcage_four_port_10_64_128MHz.py` + same-stem guide,
> `metrics.json`, `COMPARISON.md` (our column filled; **two** blank AED
> columns, Zero Order and First Order, per `ANS-5`), and
> `paraview_output/ans4_birdcage_four_port_128mhz_combined.xdmf` (P1-driven at
> 128 MHz, 5.8 s export solve). **Measured:** mesh 116 085 cells, ratio
> **1.000000**, `reused_mesh` asserted on both Larmor rungs; sweeps
> 22.7 / 22.9 / 22.5 s (mesh built once in 21.9 s); gates (i)
> **1.469e-14 / 1.126e-15 / 8.763e-16**,
> (ii) σ_max **0.999992805 / 0.999721388 / 0.998974779** with column-power
> maxima 0.793823974 / 0.804704664 / 0.861668762, (iii′) spreads
> 0.0553 / 0.0353 / 0.0214%, 0.0573 / 0.0599 / 0.0370%,
> 0.1012 / 0.0916 / 0.0654% with pooled separations 166.7× / 671.1× / 576.9×
> against the 10× floor; stop rule 128 MHz cells/λ **12.5024** ≥ 10. **Records
> reproduced:** 10 MHz leg (d)'s 4×4 worst entry **1.158e-10** (band 1e-6) and
> leg (d0)'s column **2.568e-10** (band 1e-9); 64 MHz worst **1.075e-03** and
> 128 MHz worst **6.755e-04** against `PORT-11` steps 2/3 (band 1e-2, the
> misses are on spreads recorded to three digits — σ_max and column power
> agree to 1e-10). **Negative control, printed first:** the retired `PORT-0`
> heuristic at 128 MHz, `is_placeholder=True`, one `DeprecationWarning`,
> max|off-diagonal| **0.000000e+00**, separation **1.585460** against the 2e-3
> floor. Docrefs census `20260830T213718Z_ANS-4-docrefs2.log`: **guide=0**,
> `dead=53` unchanged and entirely `EX-36`'s (the new case contributes none;
> the first census run flagged the guide's three missing `EX-15` headings and
> the guide was rewritten to carry them). No `src/` change, so nothing owed
> host-side. **Carry-forward:** the runnable half only — the gates are
> self-consistency identities on one fixture, and the AED replication at
> **both** orders is now the dashboard's Waiting-on-you; adjudication is a
> weekly review's, on the numbers the operator returns.

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

Last reviewed **2026-08-31, 03:00 review**. Interval (since the 18:00
review): **four slots, four landed, zero stopped, zero parked** — the
second clean interval in a row, on a queue whose items were independent by
design; items 1–4 of the 18:00 queue were consumed in order. 19:30 `EX-37`
(3 + 63 + 128 s): negative control on unpatched `main` red with the
`ModuleNotFoundError` in the log — the first harness observation of the
defect — then both cases green on their own asserts (ΔR 1.5838% vs 2%; the
`PORT-1` step-4 record inside 1%), `metrics.json` physics reproduced to
≤ 3e-9 relative, known-issues entry retired, **chunk ✅**. 21:00 `TH-13`
step 2 (32 s after a 300 s teardown-deadlock window): identity (A) holds
at **2.970e-12 / 2.640e-11 / 3.697e-13 / 2.586e-12** vs 1e-6 with the
mistuned-`c` probe at 1.000e-01; (B) the gradient part carries **99.98% /
99.9997%** of `W_e` and `‖P_∇₂J′‖/‖P_∇₁J′‖ = 8.049884` (squared 64.8 = the
63.7× lift) — the degree-2 "explosion" is the drive's *unremoved* gradient
residue answered through Ohm's law; **chunk ✅**, known-issues entry
carries the disposition and stays open pending the fix. 22:30 `WF-6`
step 2 (96 s after a 99 s sign-slip window): quadrature drive by exact
superposition — C4-invariance **0.9818%**, mirror identity **0.8087%** vs
the unmoved 5%, mis-paired control 95.1975%, centre purity 127.91 / 0.0081,
CV 2.7563% ungated; `post.b1_minus` landed, `ports:4`/`ports:5` re-run
green; **steps 1–2 ✅, chunk 🟡**. 00:00 `ANS-5` steps 1–2 (documentary,
no compute): the element-order ruling written into the README and all three
SPECs (+71/−3, `*.md` only), with the finding that the `ANS-1`/`ANS-3`
`COMPARISON.md` half is a *generator* change the item forbade — **🟡**.
Tree clean, no `attempt/*`, no `recovered/*`, container Up 5 days.

**Audit (§4).** `TH-13` and `EX-37` changed to ✅ this interval; both
audited **COMPLIANT** by one auditor each. `TH-13`:
`20260831T021154Z_TH-13-step2.log` footered (Status 1, 32 s), the one red
is exactly `test_the_loop_fixture_is_magnetically_dominated` on the 1 MHz
row (the deliberate step-1′ precondition, `:610–642`), the identity bound
is `GRADIENT_IDENTITY_MAX = 1e-6` asserted at `:419` and the probe
`MISTUNED_C_MIN = 9e-2` at `:427` — code, not prints; (B)'s shares are
printed and un-banded as the done-when said; `git show 2e35afa --stat`
touches no `src/` file and the test diff loosens nothing (both bounds are
new constants, not moved ones); the first window's Status 124 log was kept
and journaled, not deleted. `EX-37`: four footered logs matching every
claimed status and elapsed, the negative-control traceback verbatim at
lines 44/47, both scripts' anchors live `assert`s (`DELTA_R_RTOL = 0.02`;
`REPRODUCTION_BAND_RELATIVE`, `S_SYMMETRY_RTOL`, `S_SPECTRAL_NORM_CEILING`),
the `.py` diff exactly one line each, `metrics.json` physics moved at
~1e-13 / ~3e-9 relative, none of the ten stale census entries an `ans_*`.
`WF-6` step 2 (a step, not a chunk) was read the same way: 17 passed,
Status 0, 96 s, the imported 5% band byte-identical across the sign-slip
window and the final run. `ANS-5` steps 1–2 ran no verification command
by the weekly review's explicit ruling; the diff is the done-when and it
matches (`8dace12`, four `*.md`). No demotion.

**Two things this review established by reading, both now in §7.**
(1) **The `TH-13` fix cannot reach the coil.** The lumped-sheet birdcage
drive is a surface term — `ports/lumped.py:429` calls
`solve(current_density=None, …, project_source=False)` — so a degree-/
boundary-matched `remove_gradient_content` never touches it; the coil's
229× is the sheets' own discrete divergence closed by the phantom's σ
(step 2's done-when paragraph already said so). Step 3 is therefore split:
**3a** (item 1) is the matched projection, opt-in with bit-identical
defaults, gated on the loop fixture by the mechanism's own prediction
(gradient share of `W_e` from 99.98% / 99.9997% to ≤ 1e-6; `W_e` to ≤ 2% /
≤ 1% of record); whether a *sheet* drive's residue should be removed at all
is a formulation ruling for the 09-06 weekly review (a possible 3b), and
the known-issues degree-2 entry stays open through 3a. (2) **`WF-6` step 2b
is cheap and unblocked.** Every B₁⁺ number on record is 10 MHz because
`build_four_port_sweep()` hard-codes it, while `_four_port_rung(…,
frequency_hz=…, reuse=…)` already runs the identical construction at
64/128 MHz at 5.6–5.7 s per solve, frequency-flat (`ANS-4`'s
`metrics.json`). One keyword argument with the existing default puts the
step-1d and step-2 identities at both Larmor frequencies for ≈ 250 s — and
nobody has measured whether the CG1 floor the 5% band rests on survives
cells/λ = 12.5 at 128 MHz, so a miss there is a finding, not a failure
(item 4).

**Example chunk (§5.4).** `WF-6` step 2 newly gated the quadrature drive
(two symmetry identities at the CG1 floor) and no example superposes ports
or shows the two rotating senses — `EX-39` (`ports:7`) is added, item 6.
It is independent of `EX-38` (`ports:6`, item 5): the runner selects by
filename prefix (`scripts/run_examples.sh:180–184`). `TH-13` closed a
diagnosis, not a capability — no example. `EX-37` is itself an example.

**Residual `main` reds at `-n 2`:** unchanged — the two entry-3 names,
`test_birdcage_volumes_partition_the_box` (`GEO-21`'s floor entry), and
`TH-13`'s precondition at **1.926692e-02 on the 1 MHz row** (a deliberate
red held per §7; item 1 does not retire it — under `"matched"` the ratio is
recorded, not re-asserted, and the default-path red stays until a review
rules on it with 3a's numbers in hand). The two degree-2 **coil** identity
tests stay failing at 1e-9 (`known-issues`, open). §2 did not move: the
`TH-13` result is a diagnosis of a known red, and `WF-6` step 2's figures
are identities on one fixture at 10 MHz.

**Six items this queue, all independent — five ready plus a spare; none
depends on another landing.** Disjoint files throughout: item 1 touches
`core/source_projection.py`, `core/time_harmonic.py` and one test module;
item 2 two `ansys_benchmarks` generators + README; item 3 runs
`time_harmonic` examples; item 4 one test helper's signature + one new test
module; items 5–6 one new `ports/` example each. Deliberately not queued:
`PORT-4`…`PORT-8`, any 128 MHz resolution study, `GEO-25` and `PORT-13`
(anchors owed by the 2026-09-06 weekly review), **`TH-13` step 3b** (the
sheet-drive residue — a formulation ruling, weekly review), `WF-6` step 3
(SAR), the `TH-12` production-order clause (weekly), `EX-36` legs (mesh) /
(root) / (ports + ans) beyond the drain fallback below, a `MAG-20` third
rung, and **`TH-13` steps 1/1′/2 as written** (do not re-run them).

**⚠️ Standing constraint on the compose allow — read before editing that
file.** `docker-compose.yml` line 9 is `- ..:/workspace`, so write access
to it is write access to *what the container mounts from the host*. The
operator granted this knowingly and narrowly (2026-08-22). **Edit only
`environment:` keys. Do not touch `volumes:`, do not add a mount, do not
widen a path, and do not change the memory limit (**128 G**, raised from
64 G by operator directive 2026-08-24) — in this or any future chunk.** A
chunk that believes it needs a mount change is a **blocked finding for the
operator**. The `Edit(docker/.claude/**)` caution stands for the same
reason: a nested `.claude/` is a settings-override surface. One surviving
mechanic: `git checkout` cannot swap `docker/Dockerfile` /
`docker-compose.yml` in this sandbox — bind-mounted, "Device or resource
busy", a *silent* wrong-content switch — so any chunk that must move them
uses the Edit tool and verifies `git status --porcelain`.

**Runner trap (2026-08-29 13:30 and 2026-08-30 12:00 — two occurrences,
intermittent; the 16:30 slot ran the host runner cleanly):** if
`./run_examples.sh` fails with `permission denied … /var/run/docker.sock`,
run the runner's inner command verbatim through `run_and_log.sh`
(`docker compose exec -T fem-em-solver bash -lc 'cd /workspace && source
/usr/local/bin/dolfinx-complex-mode && PYTHONPATH=/workspace/src timeout
-k 30 <T> mpiexec -n 2 python3 examples/<path>.py'`) and journal the
denial; do not spend the slot on it. The host runner stays the documented
entry point (it is what the guides tell a reader to run) and the
substitution stays the fallback — the 12:00 entry's proposal to invert
that is declined until the denial is understood; it is on the dashboard as
an operator FYI.

1. **🟡 PARTLY DONE 2026-08-31, 04:30 slot — both anchors met, one owed
   regression re-run blocked.** `TH-13` step 3a landed on `main`: the
   matched projection is in `src/` and gated on the loop fixture (residue
   → 8.109635e-17 / 1.790460e-16 vs ≤ 1e-8, separation 1.6e+14× /
   5.8e+14× vs ≥ 1e3×; gradient share → 4.6e-23 / 3.1e-21 vs ≤ 1e-6;
   `W_e` → 9.856327e-23 / 9.349492e-23 J, 0.018% / 2.6e-4 % of record vs
   ≤ 2% / ≤ 1%), default path bit-identical at 0.000e+00 on control (b),
   `18 passed` / 37 s with only the deliberate step-1′ red
   (`20260831T094852Z_TH-13-step3a-final.log`). **Left for a review:**
   `test_coil_loading_degree2.py` hit exit 124 *inside its mesh build* at
   571 s where the whole module took 543 s on 2026-08-18 — a new
   known-issues entry, not re-run with a raised ceiling — so the two
   degree-2 coil identity reds are unverified on this commit. Original
   item below.
   **`TH-13` step 3a — the degree-/boundary-matched source projection,
   opt-in, gated on the loop fixture (standard, complex, `-n 2`, `main`;
   independent; scoped this review — execute the §7 step-3a bullet as
   written).** `remove_gradient_content(…, degree=1, pin_exterior=True)`
   — new keywords whose defaults reproduce today's `ψ` bit for bit —
   and `TimeHarmonicSolver.solve(project_source="matched")` (degree =
   the solve's, pin only under PEC; lift step 2's one-dof pin for the
   `NATURAL` constant). **Anchors, pre-registered from step 2's (A)/(B):**
   (i) under `"matched"`, `‖P_∇ₚJ′‖/‖J′‖ ≤ 1e-8` at degrees 1/2, 1 and
   10 MHz (today 1.298386e-02 and 8.05× that); (ii) the gradient share of
   `W_e` falls from **99.98% / 99.9997%** to **≤ 1e-6**, and `W_e` to
   **≤ 2%** of 5.621559e-19 J (degree 1) and **≤ 1%** of 3.579741e-17 J
   (degree 2) — margins 100× / ~3 000× over (B)'s recorded non-gradient
   shares. **Recorded, not gated:** the new degree-2/degree-1 `W_e` ratio
   (was 63.7×; no prediction exists — do not invent one), `W_e/W_m` under
   `"matched"` (the precondition is **not** re-asserted there), `|Im P|/Re
   P`. **Negative controls:** the default path reproduces every existing
   module assert (`POST-5` 1.199162e-06 W rtol 1e-6, steps 1/1′ rows rtol
   1e-3, (A)'s four residuals, 8.049884 at rtol 1e-6); `"matched"` at
   degree 1 with `pin_exterior=True` forced equals `True` at rtol 1e-12 on
   `W_e`; the `True` path's `‖P_∇₂J′‖/‖J′‖` printed beside `"matched"`'s,
   ≥ 1e3× apart. **Owed re-runs:** `test_dodd_deeds_projected_drive.py`
   and `test_coil_loading_degree2.py` — the latter's two identity tests
   stay **failing** at 1e-9 exactly as before (a moved reading there means
   the default moved: defect). **Cost:** ≤ **90 s** (module 32 s + four
   ~1 s solves), `-k 30 300`, `FEM_EM_REQUIRE_COMPLEX=1`,
   `tests/environment` first. **Traps:** only floats escape the solve
   helper (step 2's teardown deadlock); `inner` conjugates the test
   function; `create_connectivity` before `exterior_facet_indices`; the
   one-dof pin rank-safe and identical for both potentials of a pair; pin
   `quadrature_degree`; no `<=` on complex operands. **Scope:** the coil is
   **out of reach** — `ports/lumped.py:429` drives with
   `project_source=False`, so 3a says nothing about the 229×; the
   known-issues degree-2 entry stays open, the coil identity tests stay
   red, the step-1′ precondition red stays on the default path. **Negative
   result:** (i) red is a bug in the new code, fix in-slot; (ii) red with
   (i) green is a finding — (A)'s reading was incomplete — record both
   numbers in the known-issues entry, keep the assert, stop; never widen.
2. **✅ DONE 2026-08-31, 06:00 slot — `ANS-5` closes.** Both generators carry
   the two AED columns and the `Basis order` row; `ans:1` green at ΔR
   **1.5838%** (61 s) and `ans:3` green at reproduction **2.98e-05 /
   2.92e-05 / 1.71e-06 / 3.33e-10** inside 1% (133 s); census at the
   standing `dead=53 guide=0 stale=10`. **One finding for the review:** the
   item's ≤ 1e-8 `metrics.json` negative control is not achievable for
   `ANS-3` — the *unedited* generator misses it too (1.15e-8 on `Z₂₂` Im,
   measured this slot with `git checkout HEAD --`), so the figure measures
   iterative-solve scatter, not a physics-path touch. Chunk closed on the
   gated anchors; the band was recorded, not widened (§7 step-1b reading).
   Original item below.
   **`ANS-5` step 1b — the generator half of the element-order ruling
   (standard, complex, `-n 2`, host runner; independent; scoped this
   review — §7 step-1b bullet).** In `01_loop_over_lossy_slab_10MHz.py::
   _write_comparison` (`:145`) and `03_two_torus_gap_ports_10MHz.py::
   _write_comparison` (`:155`): `AED` → `AED (Zero Order)` / `AED (First
   Order)` columns and a `Basis order` Solve-metadata row, wording lifted
   from `04_…py:192`; plus `ANS-3`/`ANS-4` added to the README *Cases*
   list. **Nothing else in either `.py`.** Re-run `ans:1` (`-t 300`) and
   `ans:3` (`-t 500`), census. **Anchors:** the scripts' own asserts —
   ΔR vs the 2% ceiling (1.5838%, record 1.5834%); the `PORT-1` step-4
   reproduction inside 1% with reciprocity/passivity — and `metrics.json`
   physics reproducing the committed figures to ≤ 1e-8 relative, read off
   `git diff`. **Negative control:** `git diff -- '*metrics.json'` shows
   only `generated_utc`, `*_seconds` and last-digit noise; a moved
   physical figure stops the slot. **Cost:** ≈ 63 + 128 s + census
   (08-31 measurements), two runner windows; substitution if the socket
   denial fires. **Traps:** `ans:` nests one directory deep; the
   generators write the whole document — read both regenerated files to
   confirm the new columns/row exist. **Scope:** two `_write_comparison`
   bodies + three README lines; step 3 not taken; `ANS-4` untouched;
   nothing under `src/`/`tests/`. **Done-when:** both `COMPARISON.md`
   files carry the two AED columns and the row, both runs green, physics
   unmoved — **`ANS-5` ✅**. **Negative result:** either case red for a
   reason other than the edit — revert, known-issues, stop.
3. **`EX-36` leg (th) — re-run the eight `time_harmonic` examples until
   the census reads `dead=0` for that group (standard, complex, `-n 2`,
   host-side runner; independent; §7 entry).** Pre-leg census first
   (prints the group's non-zero `dead` count), then the eight `th:<n>`
   selections — **one token per example** (`th:1..8` is *not* a valid
   runner token: `WF-6` step 2 paid a 0-second window for `ports:4..5`) —
   105 s total by `EX-30` leg (th), then the census again. **Anchors:**
   each example's own in-script asserts against its gate records (`th:6`
   reproduces 1.769% / 59.16×, `th:8` its 16.7465% / 8.185716%); post-leg
   census `dead` for `time_harmonic` = **0**. **Negative control:** the
   pre-leg census. **Traps:** runner on the host, substitution above; a
   red example is not fixed in-slot. **Scope:** artifacts only, no record
   moves; leg ✅, chunk stays ⬜ until all four legs land. **Negative
   result:** a red example is a known-issues entry and the leg stops at
   its census figure.
4. **`WF-6` step 2b — the B₁⁺ identities at 64 and 128 MHz (standard,
   complex, `-n 2`, `main`; independent; scoped this review — §7 step-2b
   bullet).** `build_four_port_sweep(frequency_hz=FREQUENCY_HZ)` (one
   keyword, existing default) and a new
   `tests/validation/test_birdcage_b1_larmor.py`: mesh once (116 085
   cells, `STEP2_CELL_COUNT`), four solves per frequency, the step-1d and
   step-2 readings unchanged in form. **Anchors (imported, unmoved):**
   gate (i) ≤ 1e-2 at each frequency; single-drive CG1 covariance at
   +90/−90/180° and the quadrature (a) C4-invariance / (b) mirror identity
   ≤ `C4_COVARIANCE_BAND` = 5% at each frequency; `valid` 51/51; the
   10 MHz rows reproduce 2.1870 / 2.1146 / 1.8911% and 0.9818 / 0.8087% at
   rtol 1e-3. **Negative control:** the mis-paired sense > 5% at each
   frequency (10 MHz: 95.20%). **Recorded, ungated, labelled:** centre
   purity, mean `|B₁⁺|`, CV, cells/λ (import `PHANTOM_CELLS_PER_LAMBDA_FLOOR`)
   at each frequency — the first Larmor B₁⁺ numbers, still identities on
   one unconverged fixture. **Cost:** ≈ **250 s** (8–12 solves at
   5.6–5.7 s, frequency-flat per `ANS-4`; curls + CG1 projections ~50 s),
   `-k 30 600`. **Traps:** only floats/arrays escape the solve helper;
   magnitudes after point evaluation; assert the shared `Z_p`/`V_src` per
   frequency; the 5% band's floor is a **10 MHz measurement** — a 128 MHz
   miss at cells/λ 12.5 is a resolution finding. **Scope:** degree 1,
   F-small, symmetry identities only; no SAR, absolute, tuning or
   homogeneity claim; chunk stays 🟡. **Negative result:** any identity
   missing at either frequency — known-issues entry with every reading and
   cells/λ, keep the assert, stop; **never widen or re-register in-slot**.
5. **`EX-38` — `ports:6`, the first `|B₁⁺|` field in ParaView (standard,
   complex, `-n 2`, host runner; independent; §7 entry, §5.4 ramp;
   carried from the 18:00 queue unchanged).**
   `examples/ports/06_birdcage_b1_plus_map.py` + guide:
   `build_four_port_sweep`'s fixture, two solves (P1, P2),
   `magnetic_flux_density_from_e` → `project_to_cg1` → `b1_plus`, one
   combined XDMF with the CG1 `B` phasor, `|B₁⁺|` and the phantom tags.
   **Anchors (in-script asserts, all imported from
   `test_birdcage_b1_plus_map.py`):** gate (i) **9.795751e-03** at rtol
   1e-4; CG1 C4 covariance at +90° **2.1870%** at rtol 1e-3 vs the imported
   5%; `valid` 51/51; cell ratio 1.000000, `reused_mesh`. **Negative
   control:** the DG0 read prints **8.6516%** (rtol 1e-4) beside the CG1
   figure. **Cost:** ≈ **70 s**, `-t 300`; docrefs `exit != 1` for this
   example's artifacts. **Traps:** host runner, substitution; DG0
   `fem.Expression` needs the DG0 interpolation points; `.real` on the
   magnitude. **Scope:** map + symmetry identity at 10 MHz only — no CV,
   no Larmor, no quadrature, no absolute claim. **Negative result:** a
   record not reproducing — known-issues, stop.
6. *(spare)* **`EX-39` — `ports:7`, the quadrature drive in ParaView:
   `|B₁⁺|` and `|B₁⁻|` side by side (standard, complex, `-n 2`, host
   runner; independent of item 5 — the runner selects by filename prefix;
   §7 entry written this review, §5.4 ramp).**
   `examples/ports/07_birdcage_b1_quadrature_map.py` + guide: four solves,
   superposition with the phase convention **lifted verbatim from
   `test_birdcage_b1_quadrature.py`**, both senses through
   `project_to_cg1` → `b1_plus`/`b1_minus`, one combined XDMF with the CG1
   `B` phasor, `|B₁⁺|`, `|B₁⁻|` and the phantom tags. **Anchors (imported
   asserts):** (a) **0.9818%** and (b) **0.8087%** at rtol 1e-3 vs the
   imported 5%; gate (i) **9.795751e-03** at rtol 1e-4; shared
   `Z_p`/`V_src` asserted; `valid` 51/51; cell ratio 1.000000. **Negative
   control:** the mis-paired sense **95.1975%**, asserted > 5%. **Printed,
   ungated:** centre purity 127.9083 / 0.0081, mean `|B₁⁺|` 7.976427e-08 T,
   CV 2.7563%. **Cost:** ≈ **100 s**, `-t 400`; docrefs `exit != 1` for
   this example's artifacts. **Traps:** host runner, substitution; no
   `..` range tokens; DG0 interpolation points; `.real`. **Scope:** two
   maps + two identities at 10 MHz — no CV/homogeneity claim, no Larmor,
   no SAR, no absolute claim. **Negative result:** a record not
   reproducing — known-issues, stop.

*(The per-review journal — slot recap, completion audits, plan-work notes,
§10 assessment — lives in the review commits and
`docs/planning/plan-archive.md`, not here.)*

If the queue drains: **stop and journal.** There is no fallback chunk:
`PORT-9` step 3's legs are serial by design — (d) is not queued until
(d0) has a margin — and a review scopes each leg from the previous one's
number, not an implementer in-slot. The remaining `EX-36` legs are the
one exception a review has pre-authorised: if items 1–6 are all done or
blocked, a slot may take `EX-36` leg (mesh), then (root), then
(ports + ans) — unblocked since `EX-37` ✅ 2026-08-31; split into two
windows, and skip any case whose artifact the pre-leg census already reads
fresh — each as scoped in §7; they are independent of everything above. History of the birdcage-port hold in
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
- [x] Loaded birdcage + phantom simulation runs end to end **at 10 MHz —
  and, since 2026-08-26, at 64 and 128 MHz under the same three gates**
  *(ticked 2026-08-25 with `PORT-9` ✅ — the box's own condition below was
  "this box ticks at 10 MHz when leg (d1′) lands", and it landed: the
  displaced 4×4 breaks gate (iii′) on all three classes by two orders
  while reciprocity holds at 2.259e-14. **The Larmor-frequency half
  landed 2026-08-26 — `PORT-11` ✅ at 64 and 128 MHz** under the same
  three gates, frequency the only knob (10 MHz control to 1.158e-10):
  the loaded birdcage runs end to end **at the Larmor frequencies** as a
  self-consistency identity set. Still nothing here licenses an
  absolute-accuracy, resonance or tuning claim — 18:00 review. Original
  text, kept:)* *(the mesh half is
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
