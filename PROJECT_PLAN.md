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
  **0.280%** against the filament closed form at 10 MHz, σ = 100 S/m, on
  the production projected drive and the slab-refined **418 888-cell**
  fixture promoted by step 11 (2026-09-06; 1.58% was the pre-refinement
  138 619-cell record); ΔX is reported, never gated (not box-converged).
  The closed form is a filament; the fixture is a 5 mm wire, and that
  modelling term is quantified (`MAT-8` ✅ 2026-09-02): **+0.115%** on ΔR,
  **+0.145%** on ΔX at the fixture. It raises the closed form, and the
  refined FEM sits *below* the filament value, so the discrepancy against
  the corrected form is **≈ −0.40%**, and 0.115% is the floor under any
  sub-0.5% ΔR claim on this fixture.
- **SAR machinery on an imposed uniform field** (`MAT-4`): mean SAR vs the
  lossy-sphere closed form to 3.5%; the 1 g/10 g averaging operator exact.
- **Mass-averaged 10 g SAR on the coil-driven field** (`MAT-4` step 4 ✅
  2026-09-06): the same C95.3 operator applied to the four single-drive
  F-small birdcage solves on the finer-phantom rung passes a **C4
  covariance identity** at 0.3303 / 0.0756 / 0.0574 / 0.3132% against the
  unmoved 5% band, with the whole-phantom coverage identity exact to
  1.58e-14 and the far-side ball control at ~86%. **A symmetry identity on
  one fixture at fixed `h` at 10 MHz — not an absolute SAR number, not a
  C95.3 compliance or limit claim, not Larmor, not converged in `h`; the
  1 g column misses the same band at 6.84% on that rung and is a printed
  record — but on the 2.5 mm phantom rung (`MAT-4` step 5b, 2026-09-08,
  199 920 cells) **both columns are gated at that same unmoved 5% band**:
  the 1 g pairs read 0.0957 / 0.1199 / 0.1305 / 0.1065%, asserted, with
  the mis-paired 1 g control at 87.01–87.06% and the rung's mesh pinned as
  a version-tagged record at the 1% band. Still one fixture, one
  frequency, two rungs — not a convergence rate.**
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
  is the AED benchmark's job (`ANS-4` — runnable half ✅ 2026-08-30; the
  operator's AED replication at Zero and First Order **landed 2026-09-04**,
  numbers private — **adjudicated 2026-09-06 (weekly review, run
  interactively): AGREE at 10 MHz** (couplings and the terminated-drive
  input impedance agree to the few-percent level a converged AED pair
  brackets, so the port model is not wrong by a constant factor), and
  **INCONCLUSIVE at 64 / 128 MHz** on 09-06 — **re-adjudicated 2026-09-13
  (weekly review): AGREE at 128 MHz** on `ANS-4` step 2d's order-matched
  rung (our degree 2 is HFSS First Order by `ANS-5`; the degree-2 sequence
  converges, successive change 1.19 → 0.62 % on `S₁₁`, and the residual
  against AED's converged column is in the class of AED's own two orders'
  mutual agreement) and **AGREE by mechanism at 64 MHz** (the rung ran at
  128 MHz only; `ANS-4` step 3, `xl`, is the 64 MHz evidence). The 09-06
  "not element order" inference was wrong — AED was order-insensitive
  because it had converged, ours moved 6.09 / 5.38 / 6.70 % because it had
  not. **What this means for every degree-1 S figure at 128 MHz: the gate
  fixture's own entries sit 5–7 % from their order-matched value and every
  identity gate passes on them unchanged** — identities do not see this
  class of error. No absolute figure is quoted, nothing at Larmor beyond
  the verdict word is promoted, numbers private, §10 2026-09-13).
- **A package-level multi-port drive exists, gated on the 4-leg
  identities** (`POST-6` step 1, 2026-09-04; feature ladder A1):
  `ports.superpose_drives` combines N stored single-drive solves under a
  complex weight vector on the drives' own N1curl space, and through it the
  quadrature weights reproduce `WF-6` step 2's C4 / mirror records
  (0.9818% / 0.8087%, package path vs fixture path to 1.2e-15), linearity
  holds at 1e-12 and `w = e_k` returns drive k bit for bit
  (`20260905T004202Z_POST-6.log:1911–1914`). **The drive-level power
  statement is now gated in its exact form** (`PORT-16` step 2,
  2026-09-07): on the superposed quadrature field,
  `P_src,exact(w) = P_vol(w) + P_sheet,exact(w)` closes at **5.877e-15 /
  1.435e-14** against 1e-6 and the attribution
  `P_acc(w) − P_vol(w) = C(w) − sheets_terminal(w)` at **9.881e-14 /
  1.581e-13** against 1e-1
  (`20260907T110826Z_PORT-16.log:1942–1946`), with the `w = e_k`
  generalisation reproducing step 1's single-drive shares bit for bit
  (`:1948–1951`). **What it is not:** the *terminal* form
  `½aᴴ(I − SᴴS)a = ½∫σ|E_w|²` still reads **11.648%** — that figure is a
  **record, not a conservation band** (03:00 review ruling, 2026-09-07):
  the exact identity closes at 1e-14 on every drive and the ~6.7e-05 W the
  terminal form misses is its own Cauchy–Schwarz deficit (reproduced to
  1e-13), a fixed 1.06% sheet-field non-uniformity at this `h` over a
  drive-dependent denominator, not a leak. `POWER_BALANCE_BAND` keeps its
  1e-2 value and its single-drive asserts; the deliberate red retired with
  step 2's commit.
  Beside it, **RLC
  sheets and the circuit layer exist but are not gated** (`PORT-14` step 1
  🟡 — the field-side termination-reduction identity misses 1e-3 at
  1.6e-3 / 3.4e-3 / 7.2e-4; steps 1b–1c (2026-09-05) showed the miss is
  *not* a mesh-resolution effect and *is* linear in the width the sheet
  law is told, with a zero-crossing ≈ 1.1% below the area-based `A/h`
  (`20260905T213322Z_PORT-14-step1c.log:1985–1986, 2054–2055, 2123–2124`)
  — a measured lever, not yet a correction, and no constant has been
  tuned; `PORT-15` step 1 ✅ is pure algebra at
  machine precision and claims nothing about any meshed coil).
- **A PEC interior body is gated on the sphere's exterior dipole
  coefficient at 10 MHz** (`TH-15` step 1, 2026-09-05): the conductor
  solved as a *hole* with `n × E = 0` on its cavity facets fits
  β = 1.019746 against the perfect-conductor β = 1, **1.97% vs the 4.886%
  band**, with the field's relative-L2 exterior miss converging at
  **+1.19 in h** over the `TH-8` rungs (`20260905T170225Z_TH-15.log:290–296`).
  The natural-cavity control misses by 29.0× the band. **Not** loss, Q,
  copper (`TH-14`), the two-torus (step 2) or a coil (step 3); the
  pointwise field miss on the gate rung is 46.07%, a first-order N1curl
  floor recorded and asserted nowhere. The two-torus and the 4-leg
  birdcage both **mesh** as holes through `MeshGenerator` (steps 2a / 3a,
  2026-09-06: 161 461 and 80 181 cells, every sheet and cavity-area
  identity asserted, `20260906T050829Z_TH-15.log:1463–1477`,
  `20260906T213913Z_TH-15.log:2628–2650`) — meshes, not solves: no port
  has yet carried a current on either hole (the gap-voltage current is a
  conduction integral over conductor cells a hole does not have; step 2b).
- **The F-human birdcage rung is a gated *mesh*** (`GEO-25` step 2,
  2026-09-05): the 16-leg, 32-ring-port coil at `ring_radius` 0.15 m
  meshes to **504 642 cells** at fixed absolute sizing with the volume
  partition exact, all 32 terminal ratios inside [0.95, 1.0] and
  meshed/CAD conductor mass 0.965414 ≥ 0.95, while the same coil with the
  sizing scaled to the radius reads 0.893028 and fails the gate
  (`20260905T183654Z_GEO-25.log:9728–9735, 20017–20027`). CAD identities
  only — **no solve has touched this rung**, its 64 MHz cost is unpriced,
  and no Phase 6 date rests on it.
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
  half landed 2026-08-30, the operator's AED replication landed 2026-09-04,
  **adjudicated 2026-09-06: AGREE at 10 MHz, INCONCLUSIVE at 64/128 MHz;
  re-adjudicated 2026-09-13 (weekly): AGREE at 128 MHz on the
  order-matched degree-2 rung, AGREE by mechanism at 64 MHz pending
  `ANS-4` step 3** — so the *order-matched* answer is externally checked,
  while the **degree-1 production fixture's own 128 MHz entries are
  measured 5–7 % from it** (our own order move, 2b/2d) and every identity
  gate passes on them: this bullet stands for degree-1 figures exactly as
  written, and the production-order question is `TH-19` step 3), any
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
  The 16-leg *mesh* is gated (`GEO-19` ✅ 2026-08-25), the 32-ring-port
  layout is built on both sheet orientations (`GEO-20` step 2 / `EX-35`
  transverse; `GEO-26` ✅ 2026-09-04 longitudinal, 270 728 cells, all 32
  sheets exact to 1e-12), and **`PORT-13` step 1 (2026-09-04) put the first
  field on it: one column at 10 MHz, degree 1, P17 driven with 31 ports
  terminated at 50 Ω — power accounting residual 9.68e-3 inside the imported
  1e-2, the two opposite ports agreeing to 0.35%, one solve 28 s at `-n 8`
  (`20260904T050538Z_PORT-13.log:10750–10763`), and **step 2 (2026-09-04,
  04:30 slot) made it a 4×4 sub-block** — four drives over the one mesh (P17,
  its top-ring mirror P33, the two opposites P25 / P41): reciprocity of the
  sub-block 4.118219e-13 vs the unmoved 1e-3 (machine-level because the
  operator is complex-symmetric; the 1%-column control at 7.045× the band is
  what gives it teeth), column passivity 0.9158–0.9160 under 1, the
  top/bottom mirror identity worst pair 0.0308% vs 5% on two independently
  solved columns, the power residual 9.68e-3 on all four columns to six
  digits (`20260904T093638Z_PORT-13.log:10786–10854`), and **step 3
  (2026-09-04, 17:00 slot) assembled the full 32×32**: the 32×32 exists and
  is reciprocal (‖S − Sᵀ‖_F/‖S‖_F = 5.446798e-13 vs the unmoved 1e-3, with
  the 1%-column control at 2.496× the band), passive (σ_max = 0.999999452 ≤
  1) and C16 × mirror symmetric (all 18 measured classes inside 5%, worst
  0.4426%) to those digits, over 32 drives whose power residuals all sit at
  9.33–9.68e-3 inside the imported 1e-2
  (`20260904T171419Z_PORT-13.log:77–119`). That is a **network-level
  self-consistency reading on one fixture at 10 MHz, degree 1** — no σ_max
  record, no absolute-accuracy claim, no resonance, tuning or mode-spectrum
  claim exists at 16 legs.** The 10 MHz result is a **port-model validation
  on a gated fixture**, not an MRI-regime result; do not quote it as one.)* The history below is kept
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
  on ports — it is `WF-6` (steps 1–2b ✅ by 2026-08-31: `|B₁⁺|` maps and
  five symmetry identities at 10/64/128 MHz on the loaded F-small fixture,
  CG1 covariance ≈ 1.9–2.2% vs 5%; **identities on one unconverged mesh —
  no homogeneity, absolute, tuning or SAR claim**). Its B₁⁺ target is **a
  convergence statement, registered by step 5 (✅ 2026-09-13)**: on the
  unloaded F-small birdcage at 10 MHz the worst-radius C4 four-copy spread
  of the CG1 `|B₁⁺|` falls **5.2506 % → 2.0719 %** (ratio 0.3946) as the
  global resolution goes 0.015 → 0.012 m, the C4 covariance falls
  3.6159 % → 1.6815 % alongside it, and the power residual stays inside the
  unmoved 1 % band on both rungs — spreads reproduced at rtol 1e-3 and both
  falls asserted (`20260913T170259Z_WF-6-step5.log:1987, 3831, 3836`). The
  closed-form comparand (odd-order cube sum `S₁₁`) misses the ×1 rung by
  ≈ 3.2 % at the centre and ≈ 5.3 / 7.9 % at 0.4R / 0.5R — a record; the
  third rung (×0.0095) stalls near 2 % and its ≈ 2 % common-mode power
  residual is a banked, unexplained negative (known-issues). **No
  closed-form, homogeneity, absolute, C95.3 or Larmor B₁⁺ claim exists**
  (§10 epitaph, 2026-09-13). Its step 3
  (2026-08-31) read the coil-driven **point-SAR** map off the primal
  N1curl `E` and measured it **25–41%** off the same five identities
  against the same 5% band — the pointwise-`E` estimator's own floor,
  filed as five deliberate reds on `main` (known-issues). Step 3b
  (2026-08-31) put the CG1-`E` estimator beside it and read **worse**
  (152 / 110 / 170 / 53 / 41%) with the primal column reproducing to every
  digit — and its own diagnostics (`‖E_cg1 − E‖/‖E‖` **1876%** over the
  phantom, CG1 phantom power **+35 199%**) say `project_to_cg1` does not
  fit an N1curl `E` at all, so that is now the open finding. **No SAR
  claim exists**; the `|B₁⁺|` gates project `B` and are untouched.
- **Coil loading at the Larmor frequencies is measured flat in f on one
  XL window — a record, not a gate** *(head re-worded 2026-09-13 weekly
  review; it read "is an extrapolation" until `TH-11` step 5d's 64 MHz
  bracket landed, see the end of this bullet)*. The
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
  **Pointer, 2026-09-09 18:00 daily review — the premise above is now
  measured false, and this review does not move the bullet.** "More
  memory" arrived: `TH-11` step 5d ran the 2 808 204-cell 64 MHz third
  rung to completion on the 512 GiB XL service — `Status 0`, 4838 s at
  `-n 8`, 17 passed / 1 skipped, 263.4 GiB `memory.peak` — a container-lifetime
  maximum spanning the killed first attempt, **not this run's attributable
  peak** (ledger note; `OPS-43` (c) measured `memory.peak` unable to separate
  two runs, `20260910T050613Z_OPS-43c.log:90–95`) (`docs/testing/xl-ledger.md`,
  `20260909T153910Z_TH-11-step5d.log`) — giving the ladder
  **+10.2698% → +2.8063% → +0.3824%** at h 0.005 / 0.0025 / 0.00125 and a
  two-rung bracket **[−2.0415%, −0.4256%]** that overlaps step 4's 10 MHz
  [−2.15, −0.91] and 30 MHz [−3.37, −0.38]. So the sentence "no affordable
  (order, h) route exists **on this box**" was a statement about a 64 GiB
  ceiling. Whether that bracket is *gated* — and therefore whether this
  bullet moves — is **the 2026-09-13 weekly's ruling**, assigned there by
  the operator in `f5071f6` and not taken here: the daily review does not
  own §2's capability claims, and three caveats stand in the way (Dodd–Deeds
  is quasi-static and is the *comparison* rather than the reference at
  64 MHz; the two-rung `p_eff` = 2.876 disagrees with the three-rung
  `p` = 1.623, so the bracket is the honest object and the point estimate is
  not; and `d₀` = −0.7834% sits just outside the 10 MHz bracket's upper end).
  Recorded here so no reader takes the paragraph above as still current.
  **Ruled 2026-09-13 (weekly review): the bracket is a record, not a
  gate**, for exactly those three caveats plus a fourth — a 4838 s XL
  window is not a CI assertion. What it licenses: ΔR against the
  quasi-static Dodd–Deeds kernel is **measured flat in f across
  10–64 MHz to the bracket width (≈ 1.6 pp)**, confirming the 08-23
  epitaph's physics half on the box that could afford the rung; the
  bullet's head moves from "extrapolation" to "measured, not gated" and
  nothing asserts it (§10 2026-09-13).
- **An absolute / compliance SAR number on a solved coil field** — the
  IEEE C95.3 *limit* claim — is still open, and remains open after
  `MAT-4` step 4 (2026-09-06) moved that row to ✅: what step 4 gates is
  the **10 g mass-averaged C4 covariance identity** on the coil-driven
  field (0.3303 / 0.0756 / 0.0574 / 0.3132% at the unmoved 5% band,
  `tests/validation/test_birdcage_sar_mass_averaged.py`), a
  self-consistency statement on one fixture at fixed `h` at 10 MHz. No
  drive normalisation, no `h` convergence, no Larmor rung and no
  compliance comparison exists; the 1 g column misses the same band at
  6.84% on that rung and is a printed record there, while on the 2.5 mm
  phantom rung (`MAT-4` step 5b, 2026-09-08,
  `tests/validation/test_birdcage_sar_1g_rung.py`) the 1 g column **is
  gated** at the same unmoved 5% band, reading 0.0957–0.1305% — a second
  self-consistency identity on the same fixture at the same frequency, and
  still not an absolute or compliance number. The first
  coil-driven SAR *symmetry* readings exist (`WF-6` step 3, 2026-08-31)
  and miss their band by 5–8× read **pointwise** off the primal `E`. Since
  `WF-6` step 3h (2026-09-02) the repo gates exactly one coil-driven SAR
  quantity: **a C4 symmetry identity of quadrant powers on one fixture at
  10 MHz at fixed `h`** (the twelve integral pairs ≤ 1.52% against the
  imported 5% band, `tests/validation/test_birdcage_sar_integral.py`).
  Since step 3i (2026-09-03) the mirror identity through each drive's own
  azimuth is gated on the same four solves — the four single-drive flank
  pairs ≤ 1.76% against the same band, the flank-vs-opposite control at
  38% — a single-drive statement, so independent evidence rather than a
  re-reading of the rotation identity. Those are self-consistency
  identities and nothing else — no absolute SAR, no homogeneity, no
  C95.3, no Larmor, no convergence claim.
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
| `xl` | **2 h, 512 GiB, 16 ranks — three runs per trailing 7 days** (operator directive 2026-09-10; was one, raised because the measured constraint turned out to be wall-clock rather than memory) | The convergence rung the heavy tier cannot hold (operator directive 2026-09-05). Runs against the separate `fem-em-solver-xl` compose service (profile `xl`), **commissioned only by the weekly planning review** with a named chunk and a pre-registered readout, and recorded in `docs/testing/xl-ledger.md`; the bash guard denies a second XL exec inside 7 days, any XL exec outside `run_and_log.sh`, any `timeout` above 7200 s, and `-n` above 16. First slot reserved for the `ANS-4` 128 MHz refinement rung |
| `xxl` | **8 h, 754 GiB, 16 ranks — one run per trailing 7 days, Saturday 02:00** (operator directive 2026-09-10) | The window a 2 h `xl` slot cannot hold: the human-scale coil, or a many-drive sweep before the factorisation is reused. Runs against the separate `fem-em-solver-xxl` service (profile `xxl`), from `scripts/automation/xxl-queue.env` via `xl-run.sh xxl`, recorded in `docs/testing/xxl-ledger.md`. 754 GiB is this WSL VM's **whole** allocation — half the machine's 1.5 TB — so the kernel OOM killer reaches a runaway before the cgroup does; that is the operator's stated choice and is recorded in `docker-compose.yml` rather than silently softened. Saturday is its own cron day so the two tiers cannot both start at 02:00 |

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
- **XL windows run at 02:00 from cron, not from a session (operator directive
  2026-09-09) — and that is the whole answer to box contention.** The box is
  shared with work this sandbox cannot see, so scheduling a quiet hour beats
  detection that cannot work. `scripts/automation/xl-run.sh` at 02:00 daily
  runs whatever single window is queued in `scripts/automation/xl-queue.env`
  and clears the queue afterwards; empty is the normal state and the entry then
  costs a second. **No Claude session is involved**, which is also what makes
  it possible: a foreground harness call is capped at 660 s and an implementer
  slot is killed at 65 min, so no scheduled *session* can hold a 2 h window,
  while a cron script has neither limit. It takes its own lock rather than the
  automation flock, so a long window cannot starve the 02:15 weekly or the
  03:00 review, and it restarts the service first so `memory.peak` belongs to
  the run. A failed window still consumes its queue entry, for the same reason
  a started run has spent the week: re-queue deliberately or not at all.
- **This box cannot be measured from inside the sandbox (measured 2026-09-09) —
  which is *why* the schedule above exists rather than a detector.** This is WSL2: `/proc/loadavg`,
  `nproc` and `free` describe **this Linux VM only**. Work on the Windows host,
  in another WSL distro, or in another VM is invisible, and it cannot be probed
  — there is no `powershell.exe` on PATH and `/mnt` is unreadable. The
  measurement that settles it: the operator's Task Manager showed **100 % CPU
  with two solves running** while this VM reported **load 0.84** and both
  project containers **0.00 %**. A load-average check would have called the box
  free and started a 16-rank, 2-hour window straight into it. Consequences:
  (a) `scripts/testing/box_check.sh` reports containers, VM load and VM memory
  and prints its own blind spot, and its green verdict means only "nothing *I*
  can see is using the box"; (b) a mandatory per-run confirmation token was
  tried and **removed the same day** — it blocked ordinary work, since any file
  or command merely *containing* the XL command matches the guard's trip-wire,
  so it prevented editing the guard and even writing the queue file; the 02:00
  schedule replaces it and `FEM_EM_XL_BOX_OK` survives only as something the
  launcher sets; (c) the
  docker socket is reachable from a direct agent command but **not from inside
  a script** here, so `box_check.sh`'s container section goes blank exactly when
  run the convenient way and says "unavailable" rather than reporting zero.
- **An XL window waits for the box (operator directive 2026-09-09).** It holds
  up to 16 of 36 cores for up to two hours, so starting one onto a machine
  somebody else is already using is the rudest thing this project can do.
  `bash_guard.py` now refuses an XL command when the 1-minute load average
  leaves fewer free cores than the window's rank count plus 4, and the denial
  says what the load is and what it must fall below. Two properties worth
  knowing: it **fails open** — a guard that cannot read `/proc/loadavg` must
  not become the reason nothing can run — and load average is a decaying mean
  that cannot tell our own load from anyone else's, so for a minute or two
  after one of our runs ends it will postpone the next one. That is the safe
  direction; `FEM_EM_XL_IGNORE_LOAD=1` is the operator's escape hatch when the
  load is known to be ours and decaying, and never a way past somebody else's
  work. Verified across the threshold: at 36 cores and 16 ranks it allows at
  load 12, postpones at 16.1, and the same load allows an 8-rank window.
- **The big-compute slots are a budget, not a loophole.** Three `xl` runs and
  one `xxl` run per trailing 7 days, spent by the weekly review on the
  measurements the heavy tier cannot hold; the
  ledger row is appended by the harness *when the run starts*, so a killed
  run has still spent its slot **if it consumed box time**. The budget counts
  elapsed seconds, not attempts: a row whose elapsed column is 0 or empty
  never started and is not charged (2026-09-10 — two of five rows that day
  were 0-second environment failures, and pricing those like a two-hour solve
  would be absurd). That cannot be gamed the way a retry could, because the
  harness measures the elapsed time itself. Bring the service up for the slot
  (`docker compose -f docker/docker-compose.yml --profile xl up -d
  fem-em-solver-xl`) and stop it afterwards. Every other rule above (kill and
  shrink, `timeout -k 30`, rank-local bugs at `-n 2` first) applies to it
  unchanged.
- **A long window must survive its client (measured 2026-09-09).** `TH-11`
  step 5d's first attempt was killed at ~40 min *on the wrapper side*: the
  harness process died, so the log got no `## Exit` footer and nothing in it
  was countable — while the container-side `timeout`, `mpiexec` and all eight
  ranks kept running at ~85% CPU on 260 GiB with **nobody consuming their
  output**. Two rules follow, and they apply to any window over ~10 minutes,
  not only XL ones:
  * **Redirect container-side to a file first, then echo it back** —
    `... pytest ... > /workspace/logs/<name>-raw.log 2>&1; rc=$?; echo
    "[capture] rc=$rc" >> /workspace/logs/<name>-raw.log; cat
    /workspace/logs/<name>-raw.log; exit $rc`. `/logs/` is gitignored, so it
    never dirties a preflight. The `[capture] rc=` line puts the exit status
    *in the file*, not only on the dead client's stdout. If the client dies,
    the file still holds everything; once the container command has finished,
    `scripts/testing/run_and_log.sh --capture-orphan <ID>
    logs/<name>-raw.log` turns it into a normal log with a real `## Exit`
    (`Status:` from the last rc line, one test-results row, exit = that
    status; **76** `NO_RC_CAPTURE` and `Status: unknown (no rc line)` when the
    file has none). **Mechanised 2026-09-10 (`OPS-43` (a))**; the escaped
    host-side form is in `run_and_log.sh`'s header, and the gate is
    `scripts/testing/test_durable_capture.sh`. The killed wrapper's own log
    has no `## Exit`: cite the recovered one. **In normal mode the footer
    honours a final rc line (`OPS-45`, 2026-09-11):** if the command exits 0
    but its last non-blank output line is `[capture] rc=<n>` with n ≠ 0, the
    Status, row Exit and harness exit are n and `## Exit` carries a
    `Capture note:` — so an idiom that drops `; exit $rc` can no longer
    record green; a non-zero command exit is never overwritten (gate
    `scripts/testing/test_capture_status.sh`). Still write the trailing
    `exit $rc`. A bare pipe or `tee` does **not** do this: when the client
    goes, `tee` takes SIGPIPE and the run dies with it.
  * **After any killed window, check for orphaned ranks before doing anything
    else** — `docker exec <service> ps -eo pid,etime,pcpu,comm`. A dead
    wrapper does not stop the compute. Kill the `timeout` supervisor, verify
    the rank count is zero, and only then re-run. An unnoticed orphan holds
    cores and memory on a shared box indefinitely. **Mechanised 2026-09-10
    (`OPS-43` (b)):** `run_and_log.sh` now lists the target service's
    processes before any `docker compose … exec` command and exits **75**
    (`ORPHAN_REFUSAL`), printing PID / elapsed / args and writing no log or
    row, while any `mpiexec|hydra_pmi_proxy|pytest` survives. A 75 means
    "clean up first", never "retry".
- **`memory.peak` is per *container lifetime*, not per run, and cannot be
  reset on this kernel** (WSL2 6.6; `/sys/fs/cgroup/memory.peak` is
  read-only, measured 2026-09-09). A reading taken after a second run is the
  **maximum over every run since the container started**, so either restart
  the service immediately before the window — which zeroes it — or have the
  module print its own `ru_maxrss`. Label any figure that cannot be
  attributed to one run as what it is; `ANS-4` step 2b's ledger row carries
  exactly that caveat.
- **No chunk is marked `xl` without a *measured* memory price.** An
  extrapolated one is how the 2026-09-09 slot went to a case that measured
  249 s and ~16.6 GiB — an eighth of the ordinary service's own limit — while
  the genuinely memory-bound case waited (§7 `ANS-4` step 2b). A censored
  reading is not a measurement either: `TH-11` step 5's "0.99 M cells pegged
  at `memory.max` = 64.00 GiB" was clipped at the limit, so it bounded demand
  from below and licensed no extrapolation at all. The honest price for a
  case that has only ever been killed is **unmeasured**, and the first XL
  window on it is a cost probe whose readout says so.
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

Logs are retained under `docs/testing/retention-policy.md` (adopted
2026-09-03): the harness collapses gmsh optimisation chatter at write time,
every log is gzipped at 7 days, and logs not cited from this plan, its archive,
known-issues, or an example guide are deleted at 14 days by
`scripts/maintenance/housekeeping.py --apply`. Cite the log basename in the §7
closure annotation — that citation is what keeps it. Read `.log.gz` with `zcat`.

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
  *(Tightened 2026-09-09, weekly review: the count is **gating chunks or
  gated steps closed ✅**, whichever granularity the phase's §7 entries use.
  Reason — the 2026-09-09 ramp check measured Phase 5's requirement as
  `min(5, 0) = 0`, because its only live gating chunk `WF-6` is 🟡 while
  carrying five ✅ gated steps (1, 2, 2b, 3h, 3i); a bar of zero cannot bind
  anything, which is the opposite of what this rule is for. Under the
  tightened count Phase 5 owes 5 and has 6 — still no shortfall, and now a
  number that binds. This raises the bar and never lowers it: a phase whose
  chunks are all ✅ counts exactly as before.)*
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


**Tier label for host-runner example legs (ruled 2026-09-02 weekly review).** An `EX-*` leg executed through `./run_examples.sh` is tiered by the per-window ceiling its §7 entry states, not by §5.1's 180 s pytest figure — write it as "standard (host-runner, ≤ 500 s window)"; a window past its stated ceiling is an overrun, a window past 180 s is not. Measured: `EX-30` 105 / 447 / 935 s, `EX-36` 141 / 228 / 182 s under the same label.

## 6. Phase map

| Phase | Goal | Gating chunks | State |
|---|---|---|---|
| 0 | Infrastructure, packaging, CI, meshing | `OPS-1`, `OPS-2` | Done |
| 1 | Magnetostatics + analytic validation | `MAG-1`…`MAG-6` | **Complete and trustworthy** |
| 2 | Time-harmonic Maxwell, complex materials, ABC/PML | `TH-1`…`TH-9` | In progress — every analytic gate closed (`TH-1`/`TH-6`/`TH-7`/`TH-8`/`TH-9` ✅); Larmor sphere `TH-10` ✅; coil trend `TH-11` ✅ closed on a measured negative (no 64 MHz h → 0 bracket fits the box, 2026-08-18); degree-2 `TH-12` ✅ (closed 2026-09-02 on the re-affirmed production-order clause: degree 1 coil-fed, degree 2 imposed-field), `TH-13` ✅ 2026-08-31 (the injector is the degree-1-only source projection; coil degree-2 identity reds stay open in known-issues); **`TH-19` steps 1–2 ✅ 2026-09-10, outcome (a) — the matched projection clears the degree-2 coil identity by five orders on both σ-halves; production order unchanged until step 3 tests the birdcage's sheet drive (§10 2026-09-13)**; `TH-2`/`TH-3` API hardening ⚠️ |
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-6` | `MAT-2` ✅; `MAT-6` ✅ (ΔR to **0.2747%** on the production projected drive and the 418 888-cell slab-refined fixture promoted by step 11, 2026-09-06 — 1.5834% was the pre-refinement record; eddy-current regime; **externally checked 2026-09-02 — `ANS-1` adjudicated AGREE against Maxwell 3D, numbers private; the weekly re-checks that verdict against the moved column**); SAR gated on an **imposed** uniform field only (`MAT-4` steps 1+3: lossy-sphere closed form 3.5%, mass-averaging exact at 1 g/10 g) — **`MAT-4` ✅ 2026-09-06 — step 4 puts the C95.3 mass-averaging operator on the *coil-driven* field: 10 g C4 identity 0.3303 / 0.0756 / 0.0574 / 0.3132% at the unmoved 5% band on F-small at 10 MHz, whole-phantom coverage identity 1.58e-14; the 1 g column is a printed record at 6.84% and the absolute / compliance claim is still open**; **step 5 + 5b close the 1 g column as a gate 2026-09-08 — the four 1 g C4 pairs 0.0957 / 0.1199 / 0.1305 / 0.1065% asserted at the same unmoved 5% band on `GEO-27`'s `h_p` = 0.0025 m rung (199 920 / 58 866 cells, a version-tagged record at the imported `CELL_COUNT_BAND`), both steps audited PASS** *(step 5 by the 2026-09-08 10:30 review; step 5b by the 2026-09-09 03:00 review — this cell was written by the 02:15 weekly 35 min before 5b's audit actually ran, and the audit then returned PASS, so the claim is true as of 03:00 and was premature when written)* — still a symmetry identity at one frequency on one fixture, still no absolute, C95.3-compliance, homogeneity or Larmor-SAR claim |
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-11` | `PORT-1` ✅ 2026-08-15 (field-derived S through the package, two-torus fixture only, two named systematics); `PORT-10` ✅ 08-16; **`PORT-9` ✅ 2026-08-25 at 10 MHz on the gapped 4-leg birdcage** — leg (d1′)'s geometric negative control passed on the power-wave route (displaced classes 6.2219 / 7.1142 / 2.8474% vs the tightened (iii′) 0.5%, reciprocity 2.259e-14 vs 1e-3, 2.466e+11× from the pre-fix 5.57e-03), no Larmor/resonance/tuning claim; history: steps 1–2c ✅ on the two-torus (lumped-sheet BC, 1.8333% cross-route, reciprocity 2.6e-11), step 3 on the gapped birdcage has two gated legs (c)/(d0) at 10 MHz (C4 spread 0.0152–0.0159% vs 5%, 50 Ω termination separates the classes 598× — re-recorded image-tagged on the 0.11 image 2026-08-24 by leg (d3c): 0.0359%, 253.2002×) and **leg (d) closed 2026-08-23 — the 4×4 passes all three gates** (reciprocity 2.495292352e-05 vs 1e-3, σ_max 0.862659137 ≤ 1, class spreads 0.0199 / 0.0180 / 0.0108% vs 5%, gate (iii) since tightened to 0.5%); leg (d1)'s geometric control ran 2026-08-23 and **found the route loses reciprocity (5.57e-03 vs 1e-3) once the fixture is asymmetric**; leg (d2) (asymmetric two-torus, 13:30 slot) traced it to the assembly — the readout *is* the source's adjoint (1.33e-10), the asymmetry is the terminated-`Z` per-column normalisation — and the 18:00 review ruled the power-wave S fix (leg (d3)) with the class re-record (d3b), (d1′) serial on (d3b); **`PORT-11` ✅ 2026-08-26 — the same three gates at 64 and 128 MHz on the same fixture** (64: 2.581325834e-14 / σ_max 0.999721388 / spreads 0.0573 / 0.0599 / 0.0370%; 128: 7.030990825e-15 / 0.998974779 / 0.1012 / 0.0916 / 0.0654%, cells/λ 12.5024 ≥ 10 enforced; audited COMPLIANT 18:00 review) — self-consistency identities only, no absolute-accuracy/resonance/tuning claim; **externally checked — `ANS-4` adjudicated AGREE at 10 MHz against HFSS (2026-09-06) and AGREE at 64/128 MHz (2026-09-13 weekly: on the order-matched degree-2 rung at 128 MHz, by mechanism at 64 MHz pending `ANS-4` step 3; numbers private; the degree-1 gate fixture's own 128 MHz entries sit 5–7 % from their order-matched value, invisible to the identity gates)**; `PORT-13` ✅ 2026-09-04 — the 32×32 on the 16-leg / 32-ring-port longitudinal rung passes the same three gates (reciprocity 5.4e-13, σ_max 0.9999995, 18 C16 × mirror classes ≤ 0.45%), self-consistency only; `PORT-4`…`PORT-8` open |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 for excitation; both meshes (coil+phantom, birdcage) generate and are identity-gated in CI (`GEO-9`, 2026-08-03); the birdcage fixture is loaded (phantom inside) and since `GEO-18` ✅ 2026-08-22 has terminals and port sheets — **`WF-6` steps 1–2b ✅ (2026-08-30/31): `\|B₁⁺\|` maps on the loaded F-small birdcage symmetry-gated at CG1 at 10, 64 and 128 MHz, in ParaView (`EX-38`/`39`/`40`), no homogeneity/absolute/tuning claim; coil-driven SAR is measured, not gated — steps 3–3e: the packaged phantom-restricted `E` estimator is honest (best-approximation and power anchors) and the five SAR identities still miss 5% at 6–9.5%, verdict (c), the ~1 cm phantom cells; **step 3f (2026-09-02) halves the phantom's `h` and all five land inside the band at 2.5–3.5%, clause (a) — verdict (c) confirmed, no gate registered in-slot, and the `\|B₁⁺\|` identities turn out not to be mesh-converged either (2.19% → 0.62%, three deliberate reds + known-issues)**; **step 3g (same day) reads the C4 identities as cell integrals of the primal `σ\|E\|²` on the coarse mesh and lands all twelve pairs at ≤ 1.52% — the construction, not `h`, was the binding mechanism**; **step 3h ✅ (2026-09-02) registers the repo's first coil-driven SAR gate — a C4 symmetry identity of quadrant powers on one fixture at 10 MHz at fixed `h` (twelve integral pairs ≤ 1.52% against the imported, unmoved 5% band), with the five pointwise asserts retired to records that still exceed the band; no mirror identity, no absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim, and `WF-6` stays 🟡**; **2026-09-09 weekly: the SAR half of the F-small exit is DONE and the B₁⁺ half is now the single blocker.** The 09-06 review's "one item away — `MAT-4` step 2" landed 2026-09-06 as **step 4** (the step was renumbered, not skipped) and step 5b extended it to 1 g on 09-08, so the 09-06 watch condition ("if `MAT-4` step 2 is not ✅ by the 09-09 weekly, re-plan the SAR route") is **met, three days early**. What remains is subgoal 4's other half — the B₁⁺ closed-form gate, `WF-6` step 4 — which has taken **six attempts in five days (4, 4a, 4b, 4c, 4d, 4e) and landed two records and four parked negatives, zero gates**; the 09-08 10:30 ruling finished the comparand (odd-order cube sum `S_11`, bar ≈ 0.5–1.1%) and put the residual miss on the FEM, so the item is now **`WF-6` step 4f — the `h`-ladder**, priced by `GEO-29` (§10 Phase-5 assessment 2026-09-09); **2026-09-13 weekly: the 09-09 rule fired — no closed-form gate landed, and what the `h`-ladder measured is a monotone fall of the C4 four-copy spread (5.2506 → 2.0719 % on `main`, step 4g; the third rung stalls and its power residual is a banked negative), so subgoal 4's B₁⁺ target is re-scoped to that convergence statement (epitaph in §10) and Phase 5 exits on F-small when `WF-6` step 5 registers it — one tests-only item, ≈ 2026-09-14…15 if its first window is green**; **`WF-6` step 5 ✅ 2026-09-13 (12:00 slot) — see the §7 row** |
| 6 | Birdcage tuning at 64/128 MHz: mode spectrum, lumped capacitors, circuit co-simulation (the HFSS + Circuit split); production target: **32-port high-pass birdcage at 1.5 T** (§10 operator directive 2026-08-17); **fixture scale re-directed 2026-08-25 — two fixtures, F-small (today's 0.07 m gate fixture, records frozen) and F-human (≈ 0.15 m radius / 0.30 m long high-pass, the deliverable fixture); the `N ≤ 25` ceiling was arithmetic on the wrong radius and dissolves at human scale. Full directive in §10 Phase 6 — the 2026-08-30 weekly review must dispose of it, cost probe first** | **Gating chunks, listed explicitly 2026-09-09 weekly so §5.4's ramp is mechanically checkable on this phase (it was the one row with no `X-1…X-n` range): `GEO-19`, `GEO-20`, `GEO-25`, `GEO-26`, `PORT-13`, `PORT-14`, `PORT-15`, `TH-17`** — six closed ✅ at chunk-or-gated-step granularity, so the ramp is 5 and the corpus carries 8. Subgoals owned by the weekly review (§10); mesh prerequisites `GEO-19` (16 legs, cost rung) + `GEO-20` (ring-gap ports) scoped 2026-08-23, + `GEO-26` (longitudinal ring sheets — opened 2026-09-03 after `PORT-13` step 1 measured the `GEO-20` sheets transverse, `h = 0` for the lumped port model; the first ring-port solve waits on it) | **Started 2026-09-04 on the feature ladder** — mesh prerequisites all ✅ (`GEO-19`, `GEO-20`, `GEO-26`, `GEO-25`: the F-human rung is a gated 504 642-cell fixture, cost exponent 0.84 not r³), `PORT-13` ✅ (the 32×32), `PORT-15` step 1 ✅ (ladder-network closed form + S/Z reduction at machine precision), `POST-6` step 1b ✅; `PORT-14` 🟡 (lumped RLC sheet single-mode to 3.4e-3 — ruled a fixture record 2026-09-06, §7); conductor lineage `TH-15` steps 1/2a ✅; **2026-09-09 weekly: `TH-15` step 3a ✅ 2026-09-06 (`birdcage_port_domain(as_hole=True)` — the coil as a PEC hole) and step 2d ✅ 2026-09-07 (the gap-displacement port current on the open-circuit anchor), so `TH-17`'s mesh-side prerequisite is discharged and only `PORT-14` step 2 remains serial ahead of it; `PORT-16` ✅ 2026-09-07 (the exact discrete power identity on the 4-leg birdcage, single and superposed drives) closes the 1%-of-supplied accounting gap `POST-6` step 1b opened. `TH-15` step 2 itself is still open after seven sub-steps — 2f attributed the 2% `Z` asymmetry to the point-sampled `_path_voltage` and 2g measured the calibrated gap average as reading B; the `src/` replacement is specified but unwritten. `PORT-14` step 1e (the 09-06 ruling's `REDUCTION_FLOOR_F_SMALL` re-registration) has not been queued in three days and is the phase's oldest unstarted owed item** *(landed 2026-09-11)*; **2026-09-13 weekly: `PORT-19` ✅ (one factorisation per sweep, 11.2× on the 32×32), `TH-15` step 3b ✅ (`gap_cell_tags` landed, default unflipped; step 2's unitarity gate and step 3 still open), `PORT-14` step 2 frozen on a positive reading (a (1 + κ)-corrected width takes both 64 MHz residuals under 1e-3, unregistered — step 3 is the κ-derived registration); the tuned-birdcage chain is enumerated in §10 as ten numbered steps — internal milestone `TH-17` mode 1 at 64 MHz ≈ 2026-09-25…10-01 at the measured 2–3 days per numbered step, the AED-matched tuned `S₁₁` undated on the operator's AED queue**; first physics target `TH-17` eigenmodes; no completion date (§10) |
| 7 | Implants: parametric implant geometry in the phantom, local SAR / near-implant hot spots | subgoals owned by the weekly review (§10) | Not started |
| 8 | Thermal: Pennes bioheat driven by SAR | subgoals owned by the weekly review (§10) | Not started |
| 9 | Advanced: MPI scaling, AMR, sweeps, optimization | — | Deferred — **AMR is feature ladder C4** (operator directive 2026-09-04): not a boundary condition, but the largest remaining HFSS workflow gap (adaptive passes are what make an HFSS answer trustworthy without a mesh study); revisit after Phase 6 |

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
| `OPS-35` | **Repository entry-point and supported-environment consolidation** — interactive maintenance pass requested by the operator after the 2026-09-03 repository-health review. Replaced the stale README (including its contradictory phase table and nonexistent `CircularLoop` API example) with a concise alpha-status entry point linked to the live dashboard; added `CONTRIBUTING.md` with the repository's Docker, evidence, MPI, and private-data rules; pointed MkDocs at the live dashboard while retaining the 2026-07-31 page as an explicitly historical snapshot; aligned all CI solver jobs and package metadata with the already-supported DolfinX 0.11 image; updated `setup-python` v4 → v5 and Codecov v3 → v4; and installed the declared documentation toolchain in the development image. No solver source, physics assertion, tolerance, record, or capability claim changed. Verification: `20260903T183816Z_OPS-CLEANUP-SMOKE.log`, **16 passed**, Status 0, 1 s; `run_examples.sh --list` confirmed every README selector; TOML and both YAML files parse; shell syntax and `git diff --check` pass. The preceding combined attempt, `20260903T183801Z_OPS-CLEANUP.log`, records the smoke suite green followed by Status 127 because the running pre-change container lacks `mkdocs`; the Dockerfile fix addresses that missing dependency, but the strict documentation build remains for CI or the next image rebuild. | ✅ *(documentation/operations change; smoke assertions unchanged and green)* | smoke |
| `OPS-36` | Log retention policy, harness chatter filter, weekly housekeeping sweep | ✅ Closed as documentation and operations: the log retention policy, harness chatter filter and weekly housekeeping sweep landed, with gating logs exempt from the volume budget by operator decision. *History: `docs/planning/chunks/OPS-36.md`.* | smoke |
| `OPS-37` | Re-base the `PORT-1` step-4 gate module's two mutual-ratio records onto the 0.11 image and tighten its reproduction control to 1e-6 | ✅ Closed: the `PORT-1` step-4 gate module's two mutual-ratio records are re-based onto the 0.11 image under a 1e-6 reproduction band, with every physics band unmoved. *History: `docs/planning/chunks/OPS-37.md`.* | standard (179 s + 173 s measured) |
| `OPS-38` | `write_xdmf_with_tags` learns facet tags, and the three improvising examples move onto it | ✅ Closed: `write_xdmf_with_tags` writes facet tags under a closed-form round-trip gate, and the three improvising examples now call the helper. *History: `docs/planning/chunks/OPS-38.md`.* | smoke + standard (host-runner; measured 6 / 65 / 103 / 113 / 2 s) |
| `OPS-39` | The `TH-15` step-0 probe's `_census` made rank-safe, gated on the count identity at `-n 2` | ✅ Closed: the `TH-15` step-0 probe's census is rank-safe and gated on the count identity at `-n 2`, and its known-issues entry is retired. *History: `docs/planning/chunks/OPS-39.md`.* | smoke + standard |
| `OPS-40` | `evaluate_vector_field_parallel` refuses a point list that differs across ranks | ✅ Closed: `evaluate_vector_field_parallel` refuses a point list that differs across ranks, gated by executed asserts in a new test module. *History: `docs/planning/chunks/OPS-40.md`.* | smoke + standard (measured 4 / 2 / 57 / 47 s) |
| `OPS-41` | Declare `test_port_package_sparameters.py`'s three digit-reproduction records `-n 2` records, and attribute the 1e-4 width sensitivity to `V` or `I` | ✅ Closed and audited PASS 2026-09-08 10:30: the three digit-reproduction records are declared `-n 2` records, and the width sensitivity is pinned as a strict xfail under its override variable. *History: `docs/planning/chunks/OPS-41.md`.* | standard × 3 (181 + 136 + 142 s) |
| `OPS-42` | The corpus census's staleness window reports the run cadence, not staleness | ✅ Closed 2026-09-09: the corpus census's staleness window no longer reports the run cadence, and the exit-code contract is kept. One unrelated red on `main` was filed to known-issues, not edited. *History: `docs/planning/chunks/OPS-42.md`.* | smoke |
| `OPS-43` | Long-window robustness: durable capture, orphan-rank cleanup, and per-run memory instrumentation | ✅ Closed at the 2026-09-11 03:00 daily review: durable capture, orphan-rank refusal, per-run memory instrumentation and the solver-progress inertness gate all landed. The tier was corrected to standard, not the evidence. *History: `docs/planning/chunks/OPS-43.md`.* | standard *(re-declared 2026-09-11 03:00 review from *smoke*: measured 6–61 s under 120–180 s wrappers)* |
| `OPS-44` | Re-pin `COMMITTED_EXAMPLE_ARTIFACTS` to the five artifacts git actually tracks | ✅ Closed 2026-09-09: `COMMITTED_EXAMPLE_ARTIFACTS` is re-pinned to the five artifacts git tracks, and the exemption still means tracked by git rather than anything under `examples/`. *History: `docs/planning/chunks/OPS-44.md`.* | smoke |
| `OPS-45` | The harness footer must not call a red durable-capture window green | ✅ Closed and audited PASS at the 2026-09-11 18:00 review: the harness footer no longer calls a red durable-capture window green. *History: `docs/planning/chunks/OPS-45.md`.* | smoke |
| `OPS-46` | Move the heavy §7 chunk histories out of `PROJECT_PLAN.md` | ✅ Closed 2026-09-12 21:00 slot: all 73 listed rows are moved byte for byte with anchors (i), (ii) and (iv) green (plan 806 962 B, under 850 000 B); (iii) landed by the operator (`2a0ca4d`) and exercised by the 2026-09-13 10:30 review. **Audited PASS 2026-09-13 10:30** (log lines re-cited in the history file; two caveats: (iv) was a printed `wc -c`, not a scripted assert — an `OPS-47` step 1 rider — and "74 rows" was the census discrepancy, 73 were listed and moved). The narrative blocks are `OPS-47`. *History: `docs/planning/chunks/OPS-46.md`.* | smoke |
| `OPS-47` | **Move the open chunks' blockquote narratives out of `PROJECT_PLAN.md`** — *opened 2026-09-13 weekly review (§10 plan hygiene; row written by the operator's interactive session, which landed that review after the scheduled session died on the account limit).* **The defect, measured 2026-09-13:** `OPS-46` moved the 73 heavy table *rows* (806 962 B, under its 850 000 B bound), but the `>`-blockquote narratives it declared out of scope are the line count — `WF-6` 2 295, `TH-15` 1 243, `PORT-14` 736, `POST-6` 157 lines, **4 431 lines = 48 % of the file** — all under **open** chunks, which the archive contract forbids summarising or compressing. It does not forbid moving them byte for byte. **Change:** extend `scripts/maintenance/rotate_plan_archive.py chunks` to a chunk's blockquote narrative: the contiguous `>` block(s) under a §7 family table that name one chunk move verbatim to `docs/planning/chunks/<ID>.md` (appended after the row history the `OPS-46` move put there), replaced in place by one pointer line; same byte-identity refusal (the re-read file body must equal the extracted span), never overwrite, `--dry-run` and `--census` as for rows. **Anchors (asserted):** (i) every moved block is byte-identical to its new file span — an empty diff per chunk; (ii) `check_private_leak.py --audit` exit 0 after the move, with a planted synthetic value under `docs/planning/chunks/` caught first (positive control); (iii) `PROJECT_PLAN.md` line count re-measured before/after with `scripts/probes/measure_plan_sections.py` and recorded — the 4 000-line guide (weekly-review.md step 6) is the target, and the row says plainly whether it is met; (iv) every § reference in CLAUDE.md and `docs/automation/*.md` still resolves. Docs/tooling only — no `src/`, no test, no band. One commit for the tool, one per chunk for the moves. | ⬜ | smoke |
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
| `OPS-17` | Delete or replace the finiteness-only test suites (operator directive 2026-08-16) | ✅ Closed at the 2026-08-21 18:00 review: every runnable validation test was observed in a completed complex run, with two files formally deferred and the denominator re-based. `OPS-18` was queued per the commitment. *History: `docs/planning/chunks/OPS-17.md`.* | standard |
| `OPS-18` | DolfinX version upgrade, recurring (0.7.2 → newest qualifying; operator directive 2026-08-16) | ✅ Closed 2026-08-23: `main` boots the 0.11 image with every §2.1 family re-gated green on it, and the real-mode `MAG` scope caveat was discharged the same day. *History: `docs/planning/chunks/OPS-18.md`.* | heavy |
| `OPS-19` | Doc-reference checker: staleness must not own the exit code (2 runs flagged the masked signal 2026-08-16) | ✅ (2026-08-16: exit 0/1/2 split + `--stale-severity {fail,report}` default `report`; on `main` the checker now reads `dead=0 guide=0 stale=24 exit=2` where it read exit 1, guide pass green 21/21; 8 tests, 1.91 s, smoke) | smoke |
| `OPS-20` | Disposition the coil-phantom `ComplexComparisonError`: localize with `--tb=long`, then fix the form or mark `@real_only` (known-issues 2026-08-18; commissioned 2026-08-18 10:30 review) | ✅ *(2026-08-19, 06:00 slot — fixed, no `@real_only`; the commissioned `ComplexComparisonError` was already dead, killed by `OPS-22` through the **imported** drive callable, and a free grep found it. Only the predicted second layer remained: the complex build now **passes the same 30% gate at the same 17.1233%**, both ranks identical, real-mode digits unmoved across control and re-run; collect count unchanged at 49. *Audited COMPLIANT 2026-08-19 10:30 review — all five footers, the 17.1233% in all three counted runs and the line-142 `Im`-assertion verified; the skipped cold-cache clear is journalled in three places and adjudicated sound; cosmetic journal error on record: the exit-124 batch log does carry a footer (124 / 481 s), the uncounted disposition stands*)* | standard |
| `OPS-21` | Make the combined-XDMF test scalar-type-aware and rank-deterministic (known-issues 2026-08-18, two defects in one test; commissioned 2026-08-18 10:30 review) | ✅ | standard |
| `OPS-22` | Make the three magnetostatic loop-drive fixtures complex-safe: replace the `ufl.max_value` / `<=` predicates in their `current_density` callables (known-issues 2026-08-19; commissioned 2026-08-19 03:00 review from the `OPS-17` leg-(b2) attempt-2 diagnosis; unblocks 5 tests in leg (b2)) | ✅ *(2026-08-19, 04:30 slot — all three files fixed, no `@real_only` needed; real-mode digits unmoved to the last printed figure across three runs, and the complex build now runs all three files to a footer: **5 passed, 412.12 s, exit 0**, both ranks identical. *Audited COMPLIANT 2026-08-19 10:30 review — footers, closed-form assertions and the new `Im`-bound idiom verified against all five logs; one caveat on record: `test_helmholtz_v2.py`'s complex coverage rests on a silenced `ComplexWarning` `float()` cast, not an assertion — fold an `Im`-bound in whenever that file is next touched*)* | standard |
| `OPS-23` | Sweep the `OPS-21` rank-0-return defect pattern (4 measured sites in 3 test files) + the `test_helmholtz_v2.py` Im-bound (commissioned 2026-08-20 03:00 review from the 00:00 slot's grep survey) | ✅ | smoke-to-standard | 3 real sites (all in `test_csv_export_stats_parity.py`) + the Im-bound fixed; 2 of the commissioned sites were print-only false positives and 1 exempted site was a real defect; 12 passed both ranks, 5.00 s. *Audited COMPLIANT 2026-08-21 18:00 review — red-baseline byte-identity re-verified against the log's rank blocks; benign omission: the first exit-0 helmholtz-real log is in test-results.md but uncited in the annotation* |
| `OPS-24` | Migrate `core/cavity.py`'s two `assemble_matrix(..., diagonal=)` sites to the 0.11 signature — `TH-9`'s cavity gate + resonance guard have been **non-executing on `main` since the 0.11 merge** (known-issues 2026-08-24; found by `EX-30` leg (th); commissioned 2026-08-24 18:00 review; closed 2026-08-25 — `diagonal=` → `diag=`, all four green, 0.0436% worst-mode reproduced to the printed digit) | ✅ | standard |
| `OPS-25` | Re-join `th:7` to its gate: hoist the series-interior interpolation into the gate module and import it, migrating the repo's only `interpolate(cells=)` site (known-issues 2026-08-24; ruled hoist-not-repair by the 2026-08-24 18:00 review) | ✅ (2026-08-25: hoisted to `series_interior_function` in `test_lossy_sphere_fullwave.py`; `th:7` green in 14 s with both element-order records reproducing — degree 1 8.1541% / 8.3869%, degree 2 0.1405% / 0.0058%, drifts ≤ 1.48e-03 in a 1% band — and the gate's `P_series(meshed)` **bit-identical to all ten printed digits** across the refactor; `13 passed in 25.28s`) | standard |
| `OPS-26` | Systematic dolfinx-0.11 migration completeness sweep | ✅ Closed: `OPS-17`'s completed-run census was re-run on the 0.11 image and `src/` was swept for un-migrated call sites. The numbered findings and the rules they set are in the history file. *History: `docs/planning/chunks/OPS-26.md`.* | heavy (split across ≥ 2 slots) |
| `OPS-27` | Re-record the 0.7.2-era exact records the `OPS-18` re-record did not reach, version-tagged on the `GEO-16` precedent, and sweep for siblings | ✅ Closed: the 0.7.2-era exact records the `OPS-18` re-record did not reach are re-recorded version-tagged, and the prose residue is left as a coupled-constant job for whichever chunk re-prices those fixtures. *History: `docs/planning/chunks/OPS-27.md`.* | heavy (both steps — step 1 measured 256 s on its `mesh_cache` window, over the 180 s standard ceiling; label corrected 2026-08-28 03:00 audit) |
| `OPS-28` | **Give `tests/ports/test_port_orientation_sensitivity.py`'s `_DummyComm` the `allgather` that `OPS-14`'s rank-safety reduction calls, then read the module's real assertions back against known-issues entry 3** — census leg (b) finding 12: a correct reduction outgrew a test double, a class step 1's static sweep cannot see. The reduction stays; the deprecated placeholder route stays runnable (`PORT-1` step 4's negative control). Commissioned 2026-08-27 10:30 review; full rubric in §9 item 3. ***✅ 2026-08-28, 22:30 implementer slot** — one added `staticmethod allgather(value) -> [value]` on `_DummyComm`, nine lines including its comment, `src/` untouched (`git diff -- src/` empty). Bracketed by measurement on the identical command (`tests/ports`, `-n 2`, real, smoke, `-k 30 120`): red baseline `3 failed, 14 passed in 1.50s` / Status 1 / 3 s, gate `2 failed, 15 passed in 0.79s` / Status 1 / 2 s. The sign-flip anchor is **green** — `V(P2) = +5.000000e-02 V` aligned vs `−5.000000e-02 V` flipped, magnitudes equal to `rel=1e-12`, coupling factor `+1.0e-01 → −1.0e-01`. The S-matrix name reaches its assertion for the first time since `OPS-14` and is **red there**, so entry 3 is re-dated, not retired — with a correction it measured: on that 2-port fake the diagonal is **not** zero (`S11 = S22 = 9.047e-01 − 1.289e-02j`); the **off-diagonal** is, because the undriven port is the matched one (`V = 5.000000e-02 = Z₀I` at `Z₀ = 50 Ω` ⇒ `b = 0` exactly). Entry 3's mechanism is confirmed, its old title was imprecise for this name, and its disposition is unchanged (`PORT-0`/`PORT-1`). The leg (b) `allgather` known-issues entry retires whole. Negative control: the other three `tests/ports` modules unchanged — `sparameter_assembly` still 3 passed / 1 failed (entry 3's other name), planner 3 and `port_definition` 8 green in both runs. Logs `20260828T033037Z_OPS-28-red-baseline.log`, `20260828T033055Z_OPS-28-gate.log`.* | ✅ | smoke |
| `OPS-29` | **Rank-safe the `phantom_material` empty-tag check in `build_material_fields`** — the `OPS-13` defect survived 20 lines below its own fix; measured breaking `examples/mri/01_coil_phantom_fields.py` at `-n 12` (interactive session, 2026-08-28) | ✅ 2026-08-28 | smoke |
| `OPS-30` | Migrate the two filed `scripts/probes/` survivors to dolfinx 0.11 | ✅ Closed: both filed `scripts/probes/` survivors are migrated to dolfinx 0.11, and the audit re-tiered the row to standard with no demotion. *History: `docs/planning/chunks/OPS-30.md`.* | standard (re-tiered from smoke 2026-09-02, 37 s measured) |
| `OPS-32` | Private-mode comparison writers for `ANS-3` and `ANS-4` | ✅ Closed: the private-mode comparison writers for `ANS-3` and `ANS-4` landed with no AED value in any tracked table, as ratified at audit. The control half's follow-up is `OPS-33`. *History: `docs/planning/chunks/OPS-32.md`.* | standard (measured 171 s + 172 s + 1 s) |
| `OPS-33` | Re-base `ans:3`'s four `RECORDED_*` constants to the 0.11 image under the (1*) licence, then register the 1e-6 run-to-run control `OPS-32` could not | ✅ Closed: `ans:3`'s four records are re-based to the 0.11 image and the 1e-6 run-to-run control is registered with a negative control that bites. The audit re-tiered the row to heavy with no demotion. *History: `docs/planning/chunks/OPS-33.md`.* | heavy (re-tiered from standard 2026-09-03, 206 s measured; 165 s + 206 s + 1 s) |
| `OPS-34` | Measure the `ports:1` terminated-`Z` records against the 0.11 image; re-base the example's four `RECORDED_*` only if stale | ✅ Closed: the `ports:1` terminated-`Z` records were measured against the 0.11 image under the 1e-6 band. The stale digits in `test_port_package_sparameters.py` and the `gap_voltage.py` docstring are left to a review. *History: `docs/planning/chunks/OPS-34.md`.* | standard (143 / 142 / 143 s) |
| `OPS-31` | Re-record the `ports:3` cross-route narrative to the 0.11 image | ✅ Closed: the `ports:3` cross-route narrative is re-recorded to the 0.11 image, and the audit re-tiered the row to heavy with no demotion. *History: `docs/planning/chunks/OPS-31.md`.* | heavy (re-tiered from standard 2026-09-02, 235 s measured) |

**`OPS-29` — rank-safe the `phantom_material` empty-tag check in
`build_material_fields`** ✅ *(2026-08-28; full 122-line entry archived in
`docs/planning/plan-archive.md`, 2026-09-06 weekly review).* Result: the
`OPS-13` defect survived 20 lines below its own fix; measured breaking
`examples/mri/01_coil_phantom_fields.py` at `-n 12` (red baseline), green
at `-n 12` and `-n 2` after the reduction, example green at `-n 12`. Live
carry-forward: none. Logs: `20260828T165319Z_OPS-29-red-baseline.log`,
`20260828T165646Z_OPS-29-green-n12.log`,
`20260828T165709Z_OPS-29-example-n12.log`.

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
*(step 1 ✅ 2026-08-25 static sweep — 434 call sites over 29 APIs clean,
`20260825T201054Z_OPS-26.log`; step 2 ✅ 2026-08-27 over seven census legs
(a)–(h), the 19:30 → 16:30 slots; audited COMPLIANT 2026-08-27 18:00 review.)*
**Gated result: 452 of 478 collected tests observed in a footered run on the
0.11 image — 436 green, 16 red in three owned families, 26 deferred with
measured reasons, zero `not reached in slot` and zero `deferred — no
footer`.** The 16 reds are ten stale 0.7.2-era exact records over 8 modules /
5 meshes (`OPS-27`, closed), three gmsh "overlapping facets" reds (`GEO-23`),
three test-double-drift names (`OPS-28`, closed). Chunk-level reconciliation:
`docs/testing/attempts.md` 2026-08-27T22:20Z. **Live carry-forwards:**
`GEO-23`; finding 36's permanently deferred `reactance_box_truncation` and
the sixth mesh suspected behind its fixture (a `MAT-6` fixture-pricing
question, still open). The table row above carries the per-leg evidence.
**Full narrative archived 2026-09-09 → `docs/planning/plan-archive.md`.**

**`OPS-27` — re-record the stale 0.7.2-era exact records, version-tagged;
sweep for siblings** ✅ *(step 1 2026-08-27 19:30 slot, step 2 2026-08-27
21:00 slot, step 3 2026-08-28 16:30 slot; commissioned 2026-08-27 10:30
review from `OPS-26` step 2 findings 19 and 23.)* **Re-recorded — each an
exact equality version-tagged with its 0.7.2 digit and its census log
in-comment, no band introduced or moved, `git diff -- src/` empty:**
`RECORD_128_RELL2` 0.01826 → 0.017686 and `RECORD_128_SEPARATION` 57.31 →
59.16; `NCELLS_BASELINE` 138 619 → 138 490; `NCELLS_THIRD` 2 807 309 →
2 808 204; `NCELLS_FINE` 417 914 → 418 888; `NCELLS_COMBINED` 697 401 →
697 926; `wire_resolution:268` 366 207 → 365 970. Logs: step 1 four windows /
604 s, step 2 three windows / 1 523 s, step 3
`20260828T213049Z_OPS-27-step3-larmor-resolution.log` +
`20260828T213807Z_OPS-27-step3-thirdrung.log` (719 s). **Live carry-forward:**
finding 45's coupled-constant residue belongs to whichever chunk re-prices
those fixtures. **Full narrative archived 2026-09-09 → `docs/planning/plan-archive.md`.**

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
interpolation)** ✅ *(2026-08-25; full 50-line entry archived in
`docs/planning/plan-archive.md`, 2026-09-06 weekly review).* Result:
hoisted to `series_interior_function` in `test_lossy_sphere_fullwave.py`;
`th:7` green in 14 s with both element-order records reproducing (degree 1
8.1541% / 8.3869%, degree 2 0.1405% / 0.0058%), the gate's
`P_series(meshed)` bit-identical across the refactor, `13 passed`. Live
carry-forward: none. Logs: `20260825T033114Z_OPS-25-red-baseline.log`,
`20260825T033152Z_OPS-25-th7-green.log`,
`20260825T033221Z_OPS-25-gate-green.log`.

**`OPS-18` — DolfinX version upgrade, recurring** ✅ *(closed 2026-08-23;
glyph reconciled 2026-09-01; full 519-line entry archived in
`docs/planning/plan-archive.md`, 2026-09-06 weekly review).* Result:
`0.11.0.post0` builds and boots in both modes; `418 collected / 0 errors`
against the red baseline's `124 / 75`; the migration was one module
(`io/mesh.py`: `gmshio` → `dolfinx.io.gmsh`, 11 call sites, one shim). Step 3
re-recorded the mesher-dependent records on the 0.11 image under the (1*)
licence (`TH-10` 128 MHz 1.769%, one new-gmsh volume drift 4.251e-04 filed
and disposed); step 3b closed the chunk. Live carry-forward: none — the
recurring-upgrade trigger is the row's own "newest qualifying image" clause.
Logs: `20260822T093934Z_OPS-18-step1-real.log`,
`20260822T093943Z_OPS-18-step1-complex.log`,
`20260822T094005Z_OPS-18-step2-census-real.log` (11 in the archived entry).

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
| `MAG-18` | Sampler-independent straight-wire gate: annulus-restricted domain L2 of `\|B_h\| − \|B_ana\|` with a pre-registered rate band (`OPS-18` step 3 attempt 5 finding, … | ✅ Closed: the annulus-restricted domain L2 gate is sampler-independent, with the `-n 2` / `-n 4` readings inside the re-registered band and the natural-BC control strictly worse. No record moved and no band moved. *History: `docs/planning/chunks/MAG-18.md`.* | heavy |
| `MAG-19` | Dispose of the red straight-wire rate gate on 0.11 (fitted 1.9038 vs [0.7, 1.5]; the finest rung's sampled error collapsed on the image): anomalous rung vs … | ✅ Closed: the red straight-wire rate gate on 0.11 is disposed of, with the retired band's basis stated in-comment and `RATE_MIN` / `RATE_MAX` kept report-only. The residual is commissioned as `MAG-20`. *History: `docs/planning/chunks/MAG-19.md`.* | standard |
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

**`MAG-18` — sampler-independent straight-wire gate** ✅ *(closed 2026-08-23
03:00 review on the 2026-08-22 logs; commissioned 2026-08-22 18:00 review as
the disposal of `OPS-18` step 3 leg 2; re-gated on the 0.11 image
2026-08-23.)* Replaces the 10-point radial sampler — whose statistic swung
34% under its own `n_points` and whose 15% band already failed at 8 points on
0.7.2 — with an annulus-restricted domain L2, `E_Ω`. **Gated on 0.11, all
three anchors green, `7 passed` / exit 0 twice in-slot:** (i) `E_Ω` 25.2868 →
10.6172 → 6.6458% monotone at fitted rate 1.6854 ≥ 0.7; (ii) `-n 2` vs `-n 4`
agree to 4.86e-07 against the re-registered ≤ 1e-6 (the ~1e-7 direct-LU
cross-width floor is why the original 1e-10 clause was not met); (iii)
natural-BC wall ratio 0.3285, strictly worse. `E_OMEGA_H0025_RECORD`
1.061717e-01 (v0.11.0) reproduces to 2.9e-09 of its 1e-4 band. Logs
`20260824T003059Z_MAG-18-regate-run1.log`, `…003650Z_…run2.log`,
`…003606Z_MAG-18-regate-n4.log`. **Full narrative archived 2026-09-09 → `docs/planning/plan-archive.md`.**

**`MAG-19` — dispose of the red straight-wire rate gate on 0.11** ✅
*(commissioned 2026-08-25 10:30 review, closed 2026-08-25; full 180-line
entry archived in `docs/planning/plan-archive.md`, 2026-09-06 weekly
review).* Result: both norms on the same four-rung ladder — the sampled
three-rung fit reproduces the red **1.9038** and the `E_Ω` fit reads
**1.6854** with the h = 0.0025 record at 2.094e-08 relative, so the `ANS-1`
import is right and the physics moved with the image; the pre-stated
decision rule selected neither branch (a second out-of-band sampled pair
at 0.5822; dropping h = 0.0018 alone returns 0.7309), and the ruling
re-registered the gate on the measured ladder without loosening. The MAG-19
audit narrative is the auditor agent's worked exemplar (`.claude/agents/
auditor.md`). Live carry-forward: none. Log:
`20260825T183555Z_MAG-19-step1-dualnorm-fits.log`.

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
| `GEO-19` | `birdcage_port_domain` at `leg_count = 16`, gapped + sheeted: identity family re-gated (C16), cost rung measured | ✅ Closed: the 16-leg gapped and sheeted birdcage's identity family is re-gated under C16, with the 4-leg control reducing to the old flat gate. Its cost rung is Phase 6's first measured rung, and `GEO-20` step 2 is unblocked. *History: `docs/planning/chunks/GEO-19.md`.* | heavy (probe first) |
| `GEO-20` | High-pass birdcage ring-gap port layout (`ring_gap_length`, `2·leg_count` ports, the `GEO-18` pattern on the end rings) | ✅ Closed: the 32-port ring-gap module landed on `main` with the 4-leg and 16-leg ring rungs reproduced, and the 32-port fixture's sheets are licensed to read. Nothing loosened and no band moved. *History: `docs/planning/chunks/GEO-20.md`.* | standard |
| `GEO-21` | Dispose of the red `GEO-15` graded-conductor gate on 0.11: the ungraded baseline (`conductor_resolution=None`) no longer meshes at any global resolution tried, so the whole gate is non-executing on `main` (found by `EX-30` leg (mesh); commissioned 2026-08-25 18:00 review; known-issues 2026-08-25) | ✅ **2026-08-26** *(status marker flipped by the 18:00 review audit — the prose entry and the `GEO-15` row already read ✅; history: step 1 measured 2026-08-26, blocked on a ruling — the candidate control `h_c = 3.2e-3` recovers **0.916742** of the CAD mass, which is **neither** pre-stated branch: not ≤ 0.90 "clearly below", not clearing 0.95, and **inside the module's own `CAD_MASS_GATE - 0.05` = 0.90 separation guard**, so branch (2) as named cannot produce a green gate without loosening that guard. Graded side green — 0.966977 at 98 666 cells. Coarse-ward ladder measured and handed over, nothing adopted; see the entry. **Ruled 2026-08-26 03:00 review: option (b), control = 4.8e-3** — separation 0.846150 vs 0.966977 with the 0.90 guard unmoved, demoted claim (fine-vs-coarse grading) stated; 6.4e-3 rejected for cliff adjacency. **Step 2 ✅ 2026-08-26 (04:30 slot) — landed as written and the chunk closes**: control `None` → 4.8e-3 version-tagged with the six-rung probe table in-comment, demoted claim (fine vs coarse grading) in the module docstring and the `mesh:3` guide, gate `1 passed in 41.11s` at 0.846150 / 0.916742 / 0.966977 with the 0.95 gate and the 0.90 separation guard unmoved, `mesh:3` green at separation 0.120826, docrefs `dead=0 guide=0 stale=13 exit=2` giving `meshing` 2 → 0; known-issues gate red retired, generator-continuum finding re-headed and open)* | standard |
| `GEO-22` | `straight_wire_domain` coarse-resolution floor on 0.11: bisect the `[0.008, 0.010)` threshold and land a measured guard so a too-coarse request raises legibly instead of aborting inside gmsh (owner for the `EX-30` leg (root) finding; commissioned 2026-08-26 18:00 review; known-issues 2026-08-25, re-headed 08-26 and again 08-28) | ✅ *(**demoted ✅ → 🧪 2026-08-29 10:30 review, §4 clause 3** — the closing evidence is a probe that asserts nothing plus a re-run of `test_geometry_failure_is_collective.py`, whose `total_caught == comm.size` is the did-raise property the 08-28 18:00 audit already classified as non-quantitative for `GEO-23`; the fix is step 2c, one asserted leg-D anchor — queued §9)* — **step 1 ✅ 2026-08-28 as a measured negative: there is no floor.** The 2.5e-4 sweep of `[0.008, 0.010]` reads **non-monotone on both geometries** — `h = 0.00875` fails while coarser rungs mesh — and reproduces **bit-identically** across two runs, so no `RESOLUTION_FLOOR` can be written and none was; `src/` untouched. **Step 2 ✅ 2026-08-29 (07:30 slot) ⇒ chunk ✅** — the size-field probe leg the 08-28 10:30 ruling commissioned reads **18/18 OK and 0/18 fallbacks** against leg C's 7 FAILs and 18/18 fallbacks, on a leg-C control that reproduces step 1 bit-identically in its own process; `src/` still untouched and the size-field *licence* is the weekly review's. **Step 2c ✅ 2026-08-29 (16:30 slot) ⇒ chunk back to ✅** — the probe's finding is now asserted: `tests/mesh/test_straight_wire_size_field_probe.py` reads **19 823 cells / 0 fallbacks** patched and **21 830 / 1** unpatched on the example geometry at `h = 0.008`, 0.00% against the pre-stated ±1% band, identical at `-n 1` (8 s) and `-n 2` (7 s); the perturbed-reference negative control reds on both rank streams and the restored constant re-runs green. `src/` untouched, no record moved, known-issues entry stays OPEN | smoke (probe `-n 1`) + standard (gate) |
| `GEO-23` | The 0.11 "Invalid boundary mesh (overlapping facets)" family: one owner for the three `OPS-26` census reds (coil+phantom generator, `birdcage_port_domain` … | ✅ Closed: the overlapping-facets family has one owner and its gate is load-bearing and rank-symmetric, with `src/` untouched. The `GEO-21` residual is unchanged and not this chunk's. *History: `docs/planning/chunks/GEO-23.md`.* | smoke (`-n 1` probes) + standard (`-n 2` ladders) |
| `GEO-24` | Give `birdcage_port_domain` the `shared_facet` ghost layer, and re-read every module that reconstructs a sheet on it at `-n 2` and `-n 12` | ✅ Closed: the `shared_facet` ghost layer is plumbed and changed nothing this family could see, so `GEO-20` step 1's all-ranks reading loses its width-conditional caveat. Nothing loosened, no band moved, and no record in `tests/` touched. *History: `docs/planning/chunks/GEO-24.md`.* | standard |
| `GEO-25` | F-human cost probe | ✅ Closed as the F-human cost probe: branch B's CAD identities and cell record are registered, not a solve, a port gate or a physics fixture. F-human physics stays Phase 6's and the weekly's. *History: `docs/planning/chunks/GEO-25.md`.* | heavy (probe first) |
| `GEO-27` | Phantom-resolution cost probe for the 1 g SAR rung | 🧪 Measured: the phantom-resolution cost table for the 1 g SAR rung is delivered, with only the 0.0075 rung repeated across processes. The row stays 🧪 until a gate consumes the table. *History: `docs/planning/chunks/GEO-27.md`.* | standard by expectation (heavy by ceiling) — measured 132 s |
| `GEO-28` | C4 census of the unloaded F-small birdcage mesh | 🧪 Measured: the C4 census of the unloaded F-small birdcage mesh is delivered, and the near-field shell carries on the order of one cell at the global resolution, supporting `GEO-29`'s premise. It is measurement-only and never ✅. *History: `docs/planning/chunks/GEO-28.md`.* | standard (heavy by ceiling), `-n 2` — measured 29 / 30 s |
| `GEO-29` | Global-resolution cost ladder of the unloaded F-small birdcage port fixture | 🧪 Measured: the global-resolution cost ladder of the unloaded F-small fixture is delivered as a cost table. None of its finer rungs may be pinned as a version-tagged record without its own repeat. *History: `docs/planning/chunks/GEO-29.md`.* | heavy by ceiling, `-n 1` — measured **145 s** (probe 141.30 s) |
| `GEO-30` | Does the four-port birdcage fixture stay C4-symmetric under refinement? One geometric census across *both* refinement axes | 🧪 Measured 2026-09-09: the four-port fixture's geometric census across refinement is delivered and the mesh is excluded as the mechanism. The ruling on `ANS-4` step 2a and `WF-6` step 4f was left to the review. *History: `docs/planning/chunks/GEO-30.md`.* | standard by expectation, heavy by ceiling, `-n 2`, no solve — priced from `GEO-29`'s 21.6 / 26.4 / 32.9 / 45.6 s per mesh and `GEO-28`'s one-window census; **actual 133 s** for all four rungs in one window |
| `GEO-31` | The port gap-sheets' *triangulation* under the C4 rotation | 🧪 Measured 2026-09-09: the port gap-sheets' triangulation differs under the C4 rotation, and refinement amplified an existing asymmetry rather than creating one. The follow-on is `PORT-18`. *History: `docs/planning/chunks/GEO-31.md`.* | standard by expectation, heavy by ceiling, `-n 2`, no solve — priced from `GEO-30`'s 133 s and **measured 144 s** (meshing 25.29 / 33.93 / 31.25 / 36.97 s) |
| `GEO-32` | Force a C4-congruent port-sheet cut by construction | 🧪 Measured and accepted by the 2026-09-10 18:00 review: a C4-congruent cut carries the whole read-back spread, and `ANS-4` step 2a′ showed it carried the `Z` break too. It is measurement-only. *History: `docs/planning/chunks/GEO-32.md`.* | standard (heavy by ceiling), `-n 2`, no solve — **measured 127 s + 81 s + 54 s regression** |
| `GEO-26` | Longitudinal ring-gap port sheets for `birdcage_port_domain` | ✅ Closed: the longitudinal ring-gap port sheets exist in `birdcage_port_domain`, and the 16-leg terminal-area states are measured and stated in the comment. The 4-leg band did not move. *History: `docs/planning/chunks/GEO-26.md`.* | standard (step 1 ≈ 50 s per width, measured; step 2 declared heavy, 158–160 s per width measured; step 3 heavy by measurement, 221–226 s per window) |


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
| `TH-5` | Absorbing boundary condition (ABC) — **feature ladder B1** (operator directive 2026-09-04, §9 item 5; HFSS *Radiation* boundary; entry below) | ⬜ | standard |
| `TH-6` | **Validation: plane wave in lossy half-space** | ✅ | standard |
| `TH-7` | **Validation: waveguide cutoff / coaxial line** | ✅ | standard |
| `TH-8` | **Validation: sphere in uniform field (quasi-static)** | ✅ | standard |
| `TH-9` | **Validation: PEC rectangular-cavity resonances** | ✅ | standard |
| `TH-10` | **Validation: lossy dielectric sphere in a full-wave field at 64/128 MHz (the first Larmor-regime gate)** | ✅ — **128 MHz re-recorded on the 0.11 image, `OPS-18` step 3 attempt 1 / step 3b (2026-08-23):** interior relL2 **1.826% → 1.769%**, *with* its mesh moving **55 251 → 55 241 cells** under the image's gmsh 4.15.2. The 64 MHz gate is **bit-identical** across the image change (3.643%, power 3.629%), so this is the same new-gmsh mesh drift as the `OPS-17` volume record, disposed the same way — a re-record by measurement under class ruling (1\*), no band and no gated physics claim moved (the §2.1 / §2.2 `TH-10` numbers and `EX-19`'s reproduction stand). | standard |
| `TH-11` | Coil-loading trend across the eddy→displacement transition (`MAT-6`'s ΔR machinery at rising f) | ✅ Closed on step 4's answer plus step 5's measured negative, on the `GEO-14` precedent: the degree-1 coil-loading ladder hits a superlinear memory wall. Any reopening needs an `xl` slot and a review re-pricing it. *History: `docs/planning/chunks/TH-11.md`.* | standard (steps 4–5 heavy; step 5d **`xl`**) |
| `TH-12` | Second-order elements (degree-2 N1curl): accuracy-per-DOF and cost, measured (operator directive 2026-08-18; decides the production element order for §10 Phase … | ✅ Closed at the 2026-09-02 weekly review, with the decision clause on production element order re-affirmed. Degree 2 buys accuracy per cell at a measured cost, and the coil rung meets the same memory wall. *History: `docs/planning/chunks/TH-12.md`.* | standard (step 2 heavy) |
| `TH-13` | The degree-2 gradient-subspace injector: feed model or any `W_m ≫ W_e` fixture? — the discriminator `TH-12` step 3 named (commissioned 2026-08-23 weekly review; cheap fixtures only) | ✅ *(closed 2026-08-31 on step 2 — (A) holds at round-off, the injector is the degree-1-only `H¹₀`-only source projection; audited COMPLIANT 03:00 review. Follow-on **step 3a** — the matched projection, opt-in, loop fixture only — scoped 03:00 review, §9 item 1, **executed 2026-08-31 04:30 slot and 🟡**: both anchors met with 6–14 orders of margin (residue 1.298386e-02 / 1.045186e-01 → **8.109635e-17 / 1.790460e-16** vs ≤ 1e-8; gradient share of `W_e` 99.98% / 99.9997% → **4.6e-23 / 3.1e-21** vs ≤ 1e-6; `W_e` to 0.018% / 2.6e-4 % of record vs ≤ 2% / ≤ 1%), default path bit-identical on control (b) at **0.000e+00**, but one of the two owed regression re-runs — `test_coil_loading_degree2.py` — **could not be executed** (exit 124 at 571 s, twice — step 3a″ on 2026-08-31 measured the cost as the degree-2 pair alone, ≥ 524 s, mesh 4.3 s; known-issues entry), so the coil identity tests' 1e-9 reds are unverified on this commit — the degree-1 half of the owed claim was re-observed by 3a″ (+0.00039 pp of record), and **step 3a‴ (module split, one σ-half per window) closed that gap on 2026-09-01**: the two reds are now **observed** at 3.8990e-09 / 3.7235e-09 against the unloosened 1e-9, one per half, each window footered inside its 600 s ceiling — see the step-3a‴ bullet; the lumped-sheet coil drive is `project_source=False` and out of 3a's reach, see entry)* | standard |
| `TH-15` | Internal perfect-electric-conductor bodies | 🟡 Open: ✅ step 1 (the PEC sphere as a hole against its closed form), 2a and 2d (the two-torus hole route; the gap-displacement port current on the open-circuit anchor, 2026-09-07), 3a (`birdcage_port_domain(as_hole=True)`, the 80 181-cell hole beside the 116 085-cell solid, 2026-09-06) and 3b (`gap_cell_tags`, default unflipped, 2026-09-09). Open: step 2's unitarity gate — eight sub-steps, 2f attributed the 2 % `Z` asymmetry to the point-sampled `_path_voltage`, 2h 🧪 2026-09-09, the `src/` replacement specified but unwritten — and step 3, the birdcage 4×4 as a PEC hole (§10 chain step 4; queued 2026-09-13 10:30 review). *State line refreshed 2026-09-13 10:30 review from the history — the `OPS-46` line was written from a ruling that predated 3a / 2d / 3b. History: `docs/planning/chunks/TH-15.md`.* | standard (step 3 heavy) |
| `TH-14` | **Surface-impedance (Leontovich) boundary on conductor surfaces** — `n × E = Z_s n × (n × H)`, `Z_s = (1 + j)/(σδ)`, so copper (σ = 5.8e7 S/m) is affordable at any frequency; Jin §1.5.3 (1.54)–(1.56) and §5.8.3 (third-kind boundary term) (operator directive 2026-09-04; the second conductor-model route; **serial on `TH-15`** for the conductor-as-hole mesh and facet tags) | ⬜ | standard (step 3 heavy) |
| `TH-16` | **Symmetry planes: per-face PEC / PMC on cut faces with port rescaling** — HFSS *Perfect E* / *Perfect H* symmetry; quarter the birdcage, the memory lever for the F-human *refinement* rungs — **feature ladder B2** (operator directive 2026-09-04). *(Re-dated 2026-09-06 weekly: the "62 GiB F-human wall" was `TH-12` step 2's degree-2 figure on the 138 k-cell F-small and the r³ extrapolation; `GEO-25` measured F-human at fixed sizing as **504 642 cells** (exponent 0.84, 112 s to mesh), and the two priced degree-1 solves — `TH-11` step 5's 0.99 M cells at 64 GiB and `PORT-13` step 1's 270 k cells at 5.7 GiB summed RSS — bracket a first F-human 64 MHz degree-1 solve at ≈ 11–33 GiB, inside the 128 GiB box either way. Symmetry planes buy the degree-2 and h-refined F-human rungs, not the first solve; that solve is priced, not gated, by `WF-7` step 0.)* | ⬜ | standard |
| `TH-17` | **Birdcage eigenmodes** — the `TH-9` eigensolver on the loaded birdcage with a PEC coil (`TH-15`) and `PORT-14`'s capacitor sheets; mode frequencies vs the ladder-network closed form, Phase 6's named first target — **feature ladder B3** (operator directive 2026-09-04; serial on `TH-15`, `PORT-14`) | ⬜ | heavy |
| `TH-18` | **Layered impedance boundary** — thin copper foil on a substrate (HFSS *Layered Impedance*), the construction of real coils; a refinement of `TH-14` — **feature ladder B4** (operator directive 2026-09-04; serial on `TH-14`) | ⬜ | standard |
| `TH-19` | Carry the matched source projection to the coil, and retest the production element order | ⬜ Open: the matched source projection is shown to do the work on the coil fixture, and the disposition is referred to the weekly with no default change. The birdcage's lumped-sheet drive still bypasses the projection. **Ruled 2026-09-13 (weekly): outcome (a) accepted, no default change; step 3 re-scoped as the two degree-2 power identities on the sheet-driven 4-leg birdcage at 10 / 128 MHz (§10) — the production-order decision follows it at the 09-16 weekly.** **Step 3 executed 2026-09-13 13:30: both degree-2 identities green on the sheet-driven birdcage at 10 / 128 MHz — (a) 4.6e-15 / 8.9e-15 vs 1e-6, (b) 6.8e-11 / 1.8e-12 vs 1e-9, `W_e/W_m` unmoved by the order (`20260913T183446Z_TH-19-step3-10MHz.log`, `…183723Z_…-128MHz.log`, 134 / 118 s at `-n 8`); no default change, the decision is the 09-16 weekly's.** *History: `docs/planning/chunks/TH-19.md`.* | standard (steps 1–2), heavy (step 3) |

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
`W_m ≫ W_e` fixture?** ✅ *(commissioned 2026-08-23, closed 2026-08-31 on
step 2; step 3a 🟡 2026-08-31; full 577-line entry archived in
`docs/planning/plan-archive.md`, 2026-09-06 weekly review).* Result: (A)
holds at round-off — the injector is the degree-1-only `H¹₀` source
projection, so the degree-2 `W_e` explosion is a property of the drive
projection, not of the feed; audited COMPLIANT 03:00 review. Step 3a's
matched projection meets both anchors with 6–14 orders of margin (residue
8.1e-17 / 1.8e-16 vs ≤ 1e-8; gradient share of `W_e` 4.6e-23 / 3.1e-21 vs
≤ 1e-6), default path bit-identical on control (b). Live carry-forward: the
coil degree-2 identity reds stay open in known-issues as the reopening
condition of the `TH-12` production-order clause (§10). Logs:
`20260830T020301Z_TH-13-step1.log`, `20260830T200543Z_TH-13-step1prime-final.log`,
`20260831T021154Z_TH-13-step2.log` (16 in the archived entry).


**`TH-15` — internal PEC bodies: the conductor as a hole with
`n × E = 0` on its surface** ⬜ *(commissioned 2026-09-04 by operator
directive, interactive session; the first of two conductor-model routes;
serial on nothing; `TH-14` and `ANS-6` are serial on it.)* **Why.** Every
conductor in every gated fixture is a solved-inside volume whose σ is capped
by the mesh: `δ = √(2/(ωμ₀σ)) ≥ r_wire` (asserted in
`test_port_gap_voltage_impedance.py::test_sigma_respects_the_skin_depth_constraint`),
which is where the 800 S/m coil comes from. Copper at 10 MHz has δ ≈ 21 µm;
no volume mesh resolves it. §1's steps 2–3 (tuning, matching, B₁⁺ and SAR
per unit accepted power) are loss-partition quantities and the 800 S/m coil
carries a coil-loss share no real birdcage has, so no per-workflow parity
claim on a tuned coil can be made on it. The solver has two outer-boundary
modes (`TimeHarmonicBoundaryCondition`: natural, PEC) and no interior
conductor model of any kind. This chunk adds the lossless one; `TH-14`
adds the lossy one on the same mesh and facet tags. **Path.** Through the
`TH-1` solver and the `PORT-9` `extra_bilinear_terms` hook — *not* through
`TH-3`'s ⚠️ option set, which the §9 standing rule forbids extending; the
review confirms that reading before step 1 runs.
> * **Step 0 (mesh, measurement first).** Does `MeshGenerator` emit a
>   conductor as a *hole* — its volume absent from the cell set, its surface
>   present as a tagged facet set — for the two-torus and
>   `birdcage_port_domain` generators, with the port sheets still touching
>   the (now surface-only) terminals? Probe with the `mesh-probe` agent on
>   the two-torus fixture first. Pre-registered stop: if OCC fragmentation
>   of a hollow torus against a sheet lands in the `GEO-23` "overlapping
>   facets" family, this becomes a `GEO` chunk and `TH-15` waits on it.
>   Record cell counts against the solved-inside records (a hole is fewer
>   cells; say how many).
>   **🧪 MEASURED 2026-09-05 (00:00 implementer slot, `mesh-probe`, two-torus
>   only; 🧪 by the §3 rule — the probe
>   `tests/mesh/probe_two_torus_conductor_hole.py` asserts nothing, and step 1
>   is what gates this).** Seven harness windows, `-n 1`, real build, standard
>   tier, 3–48 s each. **The answer is yes, and the pre-registered stop did not
>   fire** — no `Invalid boundary mesh (overlapping facets)`, no mesher
>   fallback, no gmsh warning on the cut route; B meshes as "3D Meshing 5
>   volumes with 1 connected component". Both variants repeat bit-identically
>   (2 repeats each; every count and printed digit exact).
>   *Control (A, solid):* **184 176 cells / 31 550 vertices**, reproducing the
>   0.11 record exactly (`20260905T050518Z_TH-15.log:950–951`, repeat
>   `…051110Z:950–951`).
>   *B (hole):* **161 461 cells / 29 345 vertices** — a **13.7% cheaper mesh**,
>   −22 715 cells (`…051023Z:510–511`, repeat `…051156Z:510–511`). Conductor
>   tags **absent** from the cell census (`{3: 110 778, 101, 102, 111, 112}`,
>   no tag 1 or 2, `…051023Z:512`) against A's `{1: 9471, 2: 9348, 3: 110 696,
>   …}` (`…051110Z:952`) — the air tag moves only **+82 cells (+0.074%)**, the
>   re-triangulation at the removed interface; the rest of the delta is A's
>   18 819 conductor cells plus 3 978 fewer gap-piece cells (in B each gap box
>   is two halves, not six pieces).
>   *The sheet still touches the terminals:* B's port sheets carry 1579 facets
>   each at area **1.451325262e-04** against `nominal_area` identically, rel
>   dev **1.868e-16 and 0.000e+00** — tighter than A's 2.241e-15 / 2.988e-15
>   and far inside the 1e-9 reading (`…051023Z:514–515`). Both halves of each
>   gap box are present in the CAD census.
>   *The conductor surface arrives as a facet set:* B tag 301, **7642 facets,
>   area 1.515910101e-02** (`…051023Z:516`) against A's conductor/air interface
>   **7658 facets, 1.515909540e-02** — −16 facets (−0.21%), areas agreeing to
>   **3.7e-7** relative.
>   **One mechanism finding step 1 must not rediscover.** `occ.cut` with
>   `removeTool=False` preserves the tool volume but **not its surfaces'
>   identity with the cavity** — measured, each torus keeps 6 of its 7 faces
>   and the air gets its own 22 cavity faces. Building the conductor-surface
>   physical group from the *retained tool* therefore tags faces that are not
>   faces of any tet, and `_model_to_mesh` **aborts**: `nodes not attached to
>   any tet=716`, then `Invalid rank has value 1 but must be nonnegative and
>   less than 1` / `Abort(202007046)` (`…050616Z:506–509`, isolated by the
>   group-suppressed diagnostic `…050827Z`). The group must be derived from the
>   **meshed** volumes' boundary (a face bounding exactly one of air/gap and not
>   flat against an outer wall); that route gives `duplicates=0`, `nodes not
>   attached to any tet=0`, and survives dropping the conductor volumes 22/22.
>   Group 301 is exterior to the meshed domain, so it comes straight out of
>   `model_to_mesh` — no known-issues-9 interior-facet hazard.
>   **`MeshGenerator` was not edited**; B is a probe-local copy of the OCC
>   sequence. Step 0b (the birdcage hole) and step 1 are unblocked; step 1
>   inherits the surface-group rule above.
> * **Step 1 (formulation, cheap fixture).** Homogeneous Dirichlet on the
>   conductor-surface facet dofs (`locate_dofs_topological` on the tagged
>   facets — an `H(curl)` tangential-trace condition, Jin §1.5.2), volume
>   excluded. Gate (closed form): a **PEC sphere in a uniform time-harmonic
>   field** at 10 MHz — the `TH-8` fixture with the sphere's material
>   replaced by the hole — against the static-limit dipole field outside the
>   sphere (`E_r`, `E_θ` on the `TH-8` sample set); band **≤ the `TH-8`
>   record's own miss × 2**, pre-stated in the module from the imported
>   `TH-8` constant, never restated. ~~Negative control: the same sphere at
>   σ = 800 solved inside must *not* pass the PEC closed form (the field
>   penetrates ~δ); print its miss.~~
>   **Control corrected by the 2026-09-05 03:00 review, before the step
>   runs.** The σ = 800 volume sphere is *not* a negative control on this
>   fixture: the `TH-8` excitation is a quasi-static **electric** field
>   (k₀R = 5e-3), where what matters is `σ/(ωε₀)` = 1.4e6 at 10 MHz, so
>   the lossy volume sphere's exterior dipole coefficient is the PEC value
>   to ~1e-6 — it would *pass*. (δ ≈ 5.6 mm is the eddy-current
>   penetration and is irrelevant to an E-field exclusion problem.) The
>   same arithmetic says the `TH-8` dielectric at ε = 78 has
>   β = (ε−1)/(ε+2) = 0.9625, within 3.75% of the PEC's β = 1 — so a 4.9%
>   band on the *field* cannot tell a PEC hole from a dielectric sphere.
>   **Hence the gate is on the dipole coefficient itself, and the control
>   is the natural cavity:** with no condition on the cavity facets the
>   curl-curl weak form's gradient block enforces `n·(εE) = 0` there, a
>   void with β = −½ — an exterior `E_r` at r = 1.2R, θ = 0 of
>   1 − 2·0.5·(1/1.2)³ = 0.421 E₀ against the PEC's 2.157 E₀, an 80% miss,
>   ceiling |Δβ| = 1.5. Assert the control misses by ≥ 5× the band; the
>   ceiling is 30× and none larger is claimed. Full item in §9 (item 3 of
>   the 2026-09-05 03:00 review).
>   **🟡 MEASURED 2026-09-05 (07:30 implementer slot), NOT CLOSED — the gate
>   passes, one *other* pre-stated anchor does not, and its band is not mine
>   to move. Code parked on `attempt/TH-15-20260905T124500Z`; `main` carries
>   only this note and the logs.** All of (a), (b), (c) written; standard
>   tier, `-n 2`, complex build, four harness windows, 28 / 5 / 6 / 12 s.
>   *The gate (anchor i):* on the middle rung (**13 239 cells** — the hole is
>   25% cheaper than `TH-8`'s 17 667 at the same resolution) the fitted
>   exterior dipole coefficient is **β = 1.019746, |β − 1| = 1.9746%**
>   against the 4.886% band (`20260905T123453Z_TH-15.log:132–133`).
>   *The control (natural cavity):* **β = −0.419038** against the void's
>   closed-form −½, **|β − 1| = 141.9%, 29.0× the band** (`…:141`), inside
>   the 1.5 ceiling and over the 5× separation. *Anchor (iii):*
>   `|Im E|/|Re E| = 0.000e+00`. *Anchor (iv):* **1702** cavity dofs on tag 2
>   (reduced), max |E| on them **0.000e+00** (`…:136`) — the chord
>   quadrature points of a cavity edge lie strictly inside the absent sphere,
>   where the data callable is zero, so the trace is pinned exactly.
>   *Anchor (v):* the tagged and default routes locate the identical dof
>   array per rank, **4836 = 4836** dofs reduced, and `(1,)` releases the
>   cavity to **3134** (`…:147`). `test_dielectric_sphere.py` is **2 passed**
>   with the additive keyword off (`20260905T123859Z_TH-15.log:345`), its
>   finest rung 2.442% — the imported `TH8_RECORD_INTERIOR_MISS = 0.02443`
>   to the digit.
>   **What failed: anchor (ii), the *pointwise* field miss at the same band.**
>   Max `|E − E_closed|/E₀` over the two shells is **46.07%** (rms 18.6%,
>   relative-L2 15.6%) against 4.886% (`…123453Z:134`,
>   `…123612Z:101–102`) — while the β fitted from the *same* 48 points is
>   right to 2%, because the pointwise error is orthogonal to the dipole
>   column and averages out of the least squares. It is a discretisation
>   floor, not a defect: the `TH-8` ladder measured through
>   `scripts/probes/th15_pec_hole_resolution.py`
>   (`20260905T123827Z_TH-15.log:191–199`) gives
>   (h = 0.0125 / 0.00833 / 0.00625; 4530 / 13 239 / 29 563 cells)
>   β-miss **9.305 / 1.975 / 2.864%**, max miss **59.16 / 46.07 / 20.54%**,
>   rms **25.07 / 18.64 / 10.73%**, relative-L2 **21.03 / 15.64 / 9.00%**,
>   fitted rates in h **+1.84 / +1.47 / +1.19 / +1.19** — everything
>   converges, and the *finest* `TH-8` rung is still 20.5% pointwise. Lowest
>   order N1curl 1 cell from a Dirichlet-pinned curved wall (the 1.2R shell
>   sits 1.2 h off it) has a pointwise floor ~10× its dipole moment's miss;
>   this is the `WF-6` step 3h class (pointwise estimator floor ≫ the
>   integral identity's), and anchor (ii) restated the field band the 03:00
>   review had already argued cannot discriminate here.
>   **The ruling the next review owes this step:** demote (ii) to a printed
>   record (the `WF-6` step 3h precedent) and close step 1 on (i), (iii),
>   (iv), (v) + the control, band untouched — or re-scope it to the
>   converging quantity. The slot did **not** widen or delete it; nothing
>   here is a licence to move 4.886%.
>   **RULING — 2026-09-05 10:30 review: anchor (ii) is re-scoped to the
>   converging quantity; nothing at 4.886% moves.** The 03:00 review's own
>   argument (a ~5% *field* band cannot discriminate PEC from dielectric on
>   this fixture) should have retired the pointwise field anchor when it
>   moved the gate to β, and did not; the slot's ladder now shows the
>   pointwise miss is a first-order N1curl floor still at 20.5% on the
>   finest `TH-8` rung — a band it could only pass on a mesh no `TH-8`
>   rung is. Re-asserting it at 4.886% would be asserting a mesh the test
>   does not build. So: **(ii) becomes the convergence rate** — the fitted
>   rate in `h` of the relative-L2 exterior miss over the three `TH-8`
>   rungs (h = 0.0125 / 0.00833 / 0.00625; measured 21.03 / 15.64 / 9.00%,
>   rate **+1.19**, `20260905T123827Z_TH-15.log:191–199`) asserted
>   **≥ 0.8** (the `POST-5` step-1 precedent of a rate floor under the
>   theoretical value: lowest-order Nédélec is O(h) in L2, so 1.0 is the
>   expectation and 0.8 leaves the two-interval fit its slack; measured
>   margin 1.5×). The gate rung's max pointwise and rms misses (46.07% /
>   18.64%) are **printed as records**, never asserted — the `WF-6` step 3h
>   disposition. β at 4.886%, the control at 5×, (iii), (iv), (v) are
>   unchanged. The ladder is three solves ≈ 6 s and lives in the parked
>   probe; the test module imports the probe's `run` (or the probe moves
>   its ladder into the module and imports back — printed digits must not
>   move). **Not a loosening:** no bound that was ever green is widened;
>   a pre-registered anchor that measured a discretisation floor is
>   replaced by the quantity the same measurement showed converging, and
>   the replacement is one of §4's three named anchor classes. Landing is
>   §9 item 1 of this review: cherry-pick `5e804a5`, make the two-line
>   change, re-run the module and `TH-8` green, delete the branch.
>   **✅ LANDED 2026-09-05 (12:00 implementer slot), step 1 of 3 done.**
>   `5e804a5` cherry-picked clean onto `07a439c`; the ladder
>   (`LADDER`, `run`) moved from the probe into
>   `tests/validation/test_pec_sphere_hole.py` and the probe now imports it
>   back (one direction only — the module never imports the probe).
>   Anchor (ii) is now `POINTWISE_CONVERGENCE_RATE_FLOOR = 0.8` against the
>   fitted rate in `h` of the relative-L2 exterior miss; the pointwise max
>   and rms are printed as records. **Measured, standard tier, `-n 2`,
>   complex build, three windows 34 / 13 / 5 s:** (i) β = **1.019746**,
>   |β − 1| = **1.9746%** vs 4.886% — the parked digits reproduced exactly
>   on 13 239 cells; (ii) ladder rel-L2 **21.031 / 15.641 / 9.000%** at
>   h = 0.0125 / 0.00833 / 0.00625 (4530 / 13 239 / 29 563 cells), fitted
>   rate **+1.1917** ≥ 0.8 (margin 1.49×); records max **46.0725%**, rms
>   **18.6437%**; (iii) `|Im E|/|Re E|` = **0.000e+00**; (iv) **1702**
>   reduced cavity dofs, max |E| on them **0.000e+00**; (v) route equality
>   `None` = `(1, 2)` = **4836**, `(1,)` = 3134. Control: β = **−0.419038**,
>   |β − 1| = **141.9038% = 29.0×** the band, under the 1.5 ceiling, cavity
>   dofs released at 1.410e-02. **14 passed** (11 `tests/environment` + 3)
>   in 34 s, `20260905T170225Z_TH-15.log:290–309`;
>   `test_dielectric_sphere.py` **2 passed** in 13 s with the additive
>   keyword off, finest rung 2.442% (`20260905T170309Z_TH-15.log:225,345`);
>   the probe reprints the parked table to the digit
>   (`20260905T170327Z_TH-15.log:191–199` vs `…123827Z:191–199`), 5 s, with
>   `PYTHONPATH=/workspace/src:/workspace`. No band moved; §2.1 gained the
>   one licensed line. `attempt/TH-15-20260905T124500Z` deleted.
> * **Step 2a (the mesh route step 2 needs; scoped 2026-09-05 18:00 review
>   — step 0's cut moved into `MeshGenerator`, its counts and areas as
>   executed asserts).** Step 0 proved the two-torus hole meshes, but on a
>   *probe-local* copy of the OCC sequence
>   (`tests/mesh/probe_two_torus_conductor_hole.py::_hole_build`); step 2's
>   `Re P_in = 0` identity needs a route the `PORT-1` package can call:
>   `MeshGenerator.two_torus_domain(..., as_hole=True)`, mirroring
>   `sphere_in_box_domain(as_hole=True)` (`io/mesh.py:2029–2145`) — the two
>   conductors cut from the air (`removeTool=False`), their volumes dropped
>   from the model, the conductor-surface physical group (the probe's tag
>   `301`, exported as a module constant) built from `getBoundary` of the
>   **meshed** volumes and never from the retained tool's faces (step 0's
>   abort: `nodes not attached to any tet=716`). Default `False`; every
>   existing caller meshes exactly as before. **Anchors (asserted, new
>   module `tests/mesh/test_two_torus_conductor_hole.py`, every band
>   imported):** (i) cells reproduce step 0's **161 461** at the imported
>   `CELL_COUNT_BAND` — a version-tagged record under the (1\*) licence,
>   which the probe repeated bit-identically twice; (ii) conductor cell
>   tags 1 and 2 **absent** from the reduced cell census, air tag 3 and the
>   gap tags present; (iii) both port sheets at `nominal_area` to the
>   imported 1e-9 (`GEO-18` `EXACT`; step 0 read 1.9e-16 / 0.0); (iv) the
>   tag-301 facet area equals the `as_hole=False` route's conductor/air
>   interface area to **≤ 1e-5** relative (step 0: 3.7e-7, so the band is
>   ~30× the reading and is the same reduced-area identity `GEO-9` uses).
>   **Negative control (asserted — backed by step 0's measurement of the
>   same comparison, `20260905T050518Z_TH-15.log:950–952` /
>   `…051023Z:510–516`):** `as_hole=False` reproduces the 0.11 record
>   **184 176** cells with tags 1 / 2 present (9471 / 9348); assert hole
>   cells < solid cells and the two tag sets differ exactly as step 0
>   printed. **Tier / ranks / cost:** step 0's windows were 3–48 s at
>   `-n 1`; two builds ≈ 90 s ⇒ standard, `timeout -k 30 300`, `-n 2` with
>   every census reduced (`-n 1` if the `GEO-23` gmsh-serial rule bites —
>   say so in the journal). **Traps already paid for:** retained-tool faces
>   ≠ cavity faces; this fixture's `GhostMode.shared_facet` for the interior
>   sheet facets; `cell_tags.values` rank-local; one OS process per gmsh
>   variant if contamination appears (`GEO-23` step 1's rule — a second
>   harness window, not a fixture hack). **Scope:** a mesh route and its
>   identities — no solve, no `Re P_in` (that is step 2, the weekly's to
>   scope), no birdcage hole (step 3's mesh), no PEC-gate re-run; the row
>   stays 🟡. **Negative result:** a cell count off the record at the band
>   is a known-issues entry with both counts (the probe's repeat was inside
>   one image); a tag-301 area off the interface area by > 1e-5 is the
>   finding that the `MeshGenerator` port differs from the probe's cut —
>   known-issues, park on `attempt/*`, stop.
> * **Step 2a ✅ done 2026-09-06 (05:00 implementer slot) — every anchor and
>   the control green on the executed route, and the census had to be made
>   rank-safe before any of them could be compared.** `as_hole` landed as one
>   additive keyword on `MeshGenerator.two_torus_domain`
>   (`io/mesh.py`; `TWO_TORUS_CONDUCTOR_SURFACE_TAG = 301` exported),
>   requiring `port_gap and emit_port_sheet`; the cut sequence, the
>   `removeTool=False` rule and the cavity group from `getBoundary` of the
>   **meshed** volumes are step 0's verbatim. New module
>   `tests/mesh/test_two_torus_conductor_hole.py`, **12 passed, 4 skipped in
>   123.72 s** (standard, `-n 2`, real build, `tests/environment` first),
>   `20260906T050829Z_TH-15.log:1543`, elapsed 126 s. Readings, all at
>   `…050829Z:1463–1477`: hole **161 461** cells / 29 345 vertices, ratio
>   **1.000000** at the imported `CELL_COUNT_BAND` (0.01); cell census
>   `{3: 110778, 101: 12585, 102: 12632, 111: 12740, 112: 12726}` — tags 1
>   and 2 **absent**; facet census `{1: 1344, 211: 1579, 212: 1579,
>   301: 7642}`; both sheets `1.451325262e-04` at `rel_dev` **8.882e-16 /
>   6.661e-16** against the imported `SHEET_AREA_BAND` 1e-9; tag-301 area
>   **1.515910101e-02** against the solid route's conductor/air interface
>   **1.515909540e-02** (7.579509813e-03 + 7.579585585e-03, 3830 + 3828
>   facets), **3.704e-07** relative against the 1e-5 band — step 0's figure
>   to the digit. Control: `as_hole=False` reproduces **184 176** cells with
>   tags 1 / 2 present at **9471 / 9348** and the sheets at 1583 facets;
>   hole < solid. Every one of those per-tag numbers equals step 0's `-n 1`
>   reading exactly.
>   **The one finding.** The first run failed the control's per-tag counts
>   (`20260906T050521Z_TH-15.log:1485`: solid tag 2 read **9448** vs 9348,
>   1.0697% > the 1% band; tag 1 9556 vs 9471; air 113 483 vs 110 696) —
>   *not* a mesh difference (total cells, sheet areas and the cavity area
>   were already exact) but the probe's `_census` summing `tags.values`
>   across ranks, which under this fixture's `GhostMode.shared_facet`
>   counts every shared entity twice: the tag sum overshot the owned cell
>   count by **2972**. The census is now masked on `size_local`
>   (`_owned_census`) and an executed assert requires the per-tag census to
>   sum to the global owned cell count on both routes, so a width-dependent
>   census fails rather than drifts. No band was moved. Step 0's probe read
>   at `-n 1`, where the two agree; anything importing that probe's
>   `_census` at width > 1 has the same defect.
> * **Step 2 (identities on the PEC two-torus).** The `PORT-1` package on
>   the hollow two-torus: reciprocity ≤ 1e-3 (imported), passivity, and the
>   new identity a lossless coil buys — **`Re P_in = 0` to 1e-9-class
>   round-off** (no phantom, no loss anywhere), the first exact power
>   identity the port lineage has had. Standard tier.
>   **Scoped 2026-09-06 10:30 review (§9 item 2; the 18:00 review had
>   assigned it to the 2026-09-06 weekly, which lost its plan work to the
>   account session limit).** The identity is stated on the network the
>   package returns: **`max_ij |Re Z_ij|/|Z_ij| ≤ 1e-9`** on the
>   `as_hole=True` mesh with `pec_facet_tags=(1, 301)` and σ = 0 everywhere
>   — with real ε, no σ and homogeneous PEC data the discrete system is
>   real-symmetric with a purely imaginary drive, so `E·J` is imaginary to
>   round-off regardless of solver convergence and the expected reading is
>   1e-14-class; plus `‖SᴴS − I‖_F ≤ 1e-9`, σ_max ≤ 1 + the imported
>   `PASSIVITY_SIGMA_TOLERANCE`, reciprocity at the imported
>   `S_SYMMETRY_BAND`, `Im Z₁₂` vs ωM₁₂ at the imported `MUTUAL_TOLERANCE`
>   with the ratio printed beside the solid's 0.9398, and cells at the
>   step-2a record. Control: the σ = 800 solid through the identical
>   sweep, `Re Z₁₁ > 0` asserted, its `|Re Z₁₁|/|Z₁₁|` *predicted* order
>   0.5 and printed. Gap-voltage route only — the lumped-sheet route adds a
>   resistive sheet and is not lossless by construction. Heavy by ceiling,
>   `-n 4`, `timeout -k 30 400`.
>   **🚫 Attempted 2026-09-06 (13:30 implementer slot) and blocked on the
>   port-current definition, not on the physics.** The module
>   `tests/validation/test_two_torus_pec_hole_ports.py` (anchors (i)–(v)
>   and the σ = 800 control, every band imported, `LOSSLESS_BAND = 1e-9`
>   pre-stated) is parked on `attempt/TH-15-step2-20260906T183305Z`
>   (`4dedf89`). The hole mesh reproduces step 2a's **161 461** cells in
>   26.32 s and the PEC solve *returns*, but
>   `run_gap_voltage_port_case` then raises `non-positive conductor
>   length` (`ports/gap_voltage.py:255`;
>   `20260906T183305Z_TH-15.log:606, 734–739`, `-n 4`, complex, 11 passed /
>   4 errors in 100.15 s, elapsed 102 s). The gap-voltage port's `I` is the
>   **conduction** current in the conductor *volume*
>   (`I = σ ∫_{tag 1} E·φ̂ dx / L`, `gap_voltage.py:249–265`) and the hole
>   has no conductor cells, so `L = 0`; fixing `conductor_length_m` only
>   moves the failure to `I ≡ 0` in `_assemble_impedance_matrix`. A PEC
>   conductor carries a **surface** current, and no surface-current port
>   extraction exists in the package. Step 2 therefore needs a prior step —
>   `I = ∮ H·dl = (1/jωμ₀) ∮ (∇×E)·dl` around the cavity wall (or `n × H`
>   integrated over tag 301), anchored against the solid route's `Im Z₁₂`
>   before the lossless identities are attempted. Nothing about anchors
>   (i)–(v) was measured; no band moved.
> * **Step 2b (the Ampère-loop port current — scoped 2026-09-06 18:00
>   review, §9 item 2, ruling (1): a missing capability, not a defect,
>   so a step rather than a known-issues entry).** `GapVoltagePortSpec`
>   gains optional `loop_points` / `loop_tangents` / `loop_weights`; when
>   present the port current is `I = (1/μ₀) ∮ B·dl` with the DG0
>   `magnetic_flux_density_from_e` read on the loop through
>   `evaluate_vector_field_parallel`, right-handed about
>   `conductor_direction`; otherwise the conduction integral exactly as
>   today. Loop: radius 2.5 × `MINOR_RADIUS` in the plane normal to the
>   centreline at `φ_gap + GAP_ANGLE`, 256-point trapezoid. Anchored on
>   the **solid** first — reciprocity at `S_SYMMETRY_BAND` and
>   `Im Z₁₂/(ωM₁₂)` at `MUTUAL_TOLERANCE` through the loop route on the
>   same mesh the conduction route holds them, `Re(I_loop/I_cond) > 0`
>   with the ratio printed (predicted percent-class: a DG0 curl sampled
>   at `H_WIRE` 2.5 mm), the empty loop at `≤ 1e-3` (Ampère, predicted
>   1e-6-class) — then once on the hole with `pec_facet_tags=(1, 301)`:
>   cells at the step-2a record, reciprocity, `Im Z₁₂/(ωM₁₂)` inside
>   `MUTUAL_TOLERANCE` with the ratio beside the solid's 0.9398. Heavy by
>   ceiling, `-n 4`; the package gate re-run green (rule (c)). No
>   lossless identity — that stays step 2, whose parked module needs only
>   the loop added to its specs; the branch is kept until step 2 lands.
>   A DG0 loop sample off the conduction current by > 20% at both loop
>   radii is the finding that the next candidate is the surface form
>   `n × H` over tag 301 — known-issues, park, stop.
>   **🚫 Attempted 2026-09-06 (21:00 implementer slot): the capability
>   works and clears step 2's blocker; two of the four asserted anchors
>   miss, both on the same mechanism.** Parked on
>   `attempt/TH-15-step2b-20260907T021500Z` (`ae79a4f`) — code
>   (`GapVoltagePortSpec.loop_points/loop_tangents/loop_weights`, the
>   additive `diagnostic_loops` + `PortVoltageCurrentEstimate.
>   current_diagnostics` that make the empty-loop control and the
>   loop-independence reading cost no extra solve, and the loop branch in
>   `run_gap_voltage_port_case`), the new module
>   `tests/validation/test_two_torus_ampere_loop_current.py`, and the log.
>   One window, `-n 4`, complex, **3 failed / 12 passed in 220.50 s**,
>   elapsed 222 s (`20260907T020614Z_TH-15.log:1678, 1939`); a 4 s
>   collect-only smoke first (`…020602Z`). **What the window bought.**
>   The `as_hole=True` PEC mesh now returns a **full 2×2** — 161 461 cells
>   at the imported band (`:1567`, `:1857`), the sweep completes and the
>   13:30 slot's `non-positive conductor length` is gone, i.e. the missing
>   capability is built. The closed-form mutual holds on **both** routes
>   inside the imported `MUTUAL_TOLERANCE`: solid raw 0.900681 → corrected
>   **0.946178** (−5.38%, `:1074`), hole raw 0.885484 → corrected
>   **0.930508** (−6.95%, `:1858`), beside the conduction route's 0.939822
>   — anchor (iv)'s mutual leg and anchor (i)'s mutual leg both pass, and
>   the "(iv) outside 0.10" stop did **not** fire. Anchor (ii) passes:
>   `I_loop/I_cond = 0.981664 + 0.004919j` on the driven port, i.e.
>   `|I_loop/I_cond − 1| = **1.86%**` (`:1048`), the *predicted*
>   percent-class, and the 3.5 × `MINOR_RADIUS` loop reproduces the 2.5 ×
>   one to **0.53%** (`:1049`) — the > 20% negative-result stop did not
>   fire at either radius. **What missed, asserted, not loosened.**
>   Anchor (iii), the empty loop: **8.874e-03** against the pre-stated
>   1e-3 ceiling (`:1088`), predicted 1e-6-class; in absolute terms
>   `I_empty = 8.467e-03 A`, which is not a displacement current but the
>   **DG0 contour quadrature's own floor** out in the `H_FAR` = 30 mm
>   region. Anchors (i)/(iv), reciprocity: **1.4338e-03** solid (`:1075`)
>   and **4.4523e-03** hole (`:1092`) against the imported
>   `S_SYMMETRY_BAND` = 1e-3, which the *conduction* route holds at
>   4.76e-05 on the same mesh. **One mechanism explains both**: the
>   undriven port's true current is ~1.2e-03 A (`:1052`) while the loop
>   reading's absolute floor is ~1e-02 A, so the off-diagonal currents are
>   noise (`I_loop/I_cond = 0.032 + 0.190j` on the undriven P2, `:1052`)
>   while the driven current — the only one `Z₁₂ = V₁/I₂` consumes — is
>   good to 1.9%. That is why the mutual passes and reciprocity does not.
>   No band moved, nothing loosened, `main` untouched; the package gate
>   re-run (rule (c)) was **not** executed — nothing landed to regress.
>   **Unblock condition (a review's to rule on, not an implementer's):**
>   either a current definition whose floor scales with the port's own
>   current rather than with the drive — the surface form `n × H` over
>   tag 301, or the loop integrated as a *facet* form instead of a
>   256-point DG0 point sample — or a ruling that the loop route's
>   reciprocity is asserted at its own measured band with the conduction
>   route's 4.76e-05 kept as the separation control. `TH-15` stays 🟡.
>   **Ruling, 2026-09-07 03:00 review — neither (a) as offered nor (b); a
>   third route, and it is the one the fixture already defines.** (b) is
>   refused: asserting the loop route's reciprocity "at its own measured
>   band" is a band fitted to a floor the slot itself diagnosed as a
>   sampling artifact (MAG table, defect 5). Of the two (a) candidates,
>   the `n × H` facet form and the loop-as-facet-form both read the
>   *discrete curl* of the degree-1 field at the undriven wire, where the
>   field is the driven wire's and the port's own contribution is 1e-3 of
>   it — their O(h) quadrature error would still scale with the drive.
>   The quantity whose error scales with the port's own current is the
>   **displacement current through the port's own gap**: the gap box is a
>   tagged cell volume on both the solid and the hole mesh (the impressed
>   drive already lives there, `gap_voltage.py:224–240`), and by
>   continuity the wire current at the gap face is `I_k = I_drive
>   δ_k,driven + (1/g_k) ∫_{gap k} (σ + jωε) E·ĥ_k dV`. On the undriven
>   port that gap field is the port's own — its gap voltage (V₂ = 1.07 V,
>   `…020614Z:1051`) over a gap far thinner than the wire, against an
>   ambient field of the driven wire's order ~1e2 V/m — so the readout is
>   conditioned on the right current by two decades, and on a PEC hole
>   the gap's end caps are the cavity wall itself, where `E·ĥ` is the
>   normal field. **Step 2c** (§9 item 1) lands it as
>   `current_route="gap_displacement"` on the spec; the loop route on
>   `ae79a4f` is **not** landed (its floor is the drive's), and the
>   branch is deleted by the slot that lands 2c, its numbers being fully
>   in the 🚫 paragraph above. Step 2 proper (the parked module on
>   `4dedf89`, its current extraction swapped) follows as §9 item 6,
>   serial on 2c.
> * **Step 2c (the gap-displacement port current — scoped 2026-09-07
>   03:00 review; §9 item 1, full item there).** One additive keyword-only
>   field `current_route: str = "conduction"` on `GapVoltagePortSpec`
>   accepting `"gap_displacement"`; the conduction branch of
>   `run_gap_voltage_port_case` unchanged (its raise included), the
>   displacement branch reading `I_k` as above with `(σ + jωε)` from the
>   problem's material on the gap tag (assert `σ_gap == 0` on the
>   two-torus, print `ε_gap/ε₀`, never hard-code ε₀), the driven port
>   adding `drive_current_a`; the conduction current carried as a
>   diagnostic wherever the conductor tag has volume. New module
>   `tests/validation/test_two_torus_gap_displacement_current.py` on the
>   **solid** two-torus only. **Anchors (asserted):** (i) continuity on
>   the undriven port `|I_disp/I_cond − 1|` ≤ 0.10 (new pre-registered
>   bound, predicted percent-class); (ii) the same on the driven port with
>   `I_drive` added (loop route read 1.86%); (iii) reciprocity at the
>   imported `S_SYMMETRY_BAND` 1e-3 (conduction route 4.76e-05, loop route
>   1.4338e-03 on this mesh); (iv) the corrected mutual inside the imported
>   `MUTUAL_TOLERANCE`. **Negative control (asserted, backed by
>   `…020614Z:1052`):** the loop route's undriven ratio `0.032 + 0.190j`
>   is the record the new route must beat, separation printed. **Cost:**
>   two solid solves ≈ 220 s at `-n 4` (`:1045–1075`), `timeout -k 30 500`,
>   plus rule (c)'s `test_port_package_sparameters.py` re-run. **Scope:**
>   solid fixture only, no hole solve, no `Re Z = 0` claim, no band moved.
>   **Negative result:** (i) outside 0.10 ⇒ the gap's discrete field is
>   not the port current at this `h` — known-issues, park, stop; the
>   `n × H` facet form is then the last candidate, a review's to scope.
>   **🚫 Attempted 2026-09-07 (04:30 implementer slot): anchor (i) misses
>   by construction and the asserted negative control fails; the
>   negative-result exit was taken, nothing loosened, nothing fitted.**
>   Parked on `attempt/TH-15-step2c-20260907T094500Z` (`f942dc2`) — the
>   additive `current_route` keyword and its displacement branch in
>   `ports/gap_voltage.py`, the cherry-picked `current_diagnostics` field
>   in `ports/excitation.py` (the only thing taken from `ae79a4f`), the
>   new module `tests/validation/test_two_torus_gap_displacement_current.
>   py`, and the three logs. Windows: a 4 s collect-only smoke
>   (`20260907T093428Z_TH-15.log`, 15 collected), then `-n 4` complex
>   `-v --tb=short` with `tests/environment` — **2 failed / 13 passed in
>   129.69 s**, elapsed 131 s (`20260907T093440Z_TH-15.log:1140`) — then
>   an `-s` window to capture the passing anchors' digits, **2 failed / 2
>   passed in 102.27 s**, elapsed 103 s (`20260907T093741Z_TH-15.log:1069`).
>   Gap material read off the problem as required, never re-declared:
>   `σ_gap = 0.000000e+00 S/m`, `ε_gap/ε₀ = 1.000000` (`…093741Z:982–986`).
>   **What passed.** (ii) continuity on the *driven* port:
>   `|(I_drive + I_disp)/I_cond − 1|` = **2.243038e-02** (drive P1) and
>   **2.236565e-02** (drive P2) against 0.10 (`:1013`, `:1018`) — the
>   predicted percent class, the sign convention confirmed. (iii)
>   reciprocity `‖S − Sᵀ‖/‖S‖` = **5.2613e-04** inside the imported
>   `S_SYMMETRY_BAND` 1e-3 (`:1030`), where the loop route missed at
>   1.4338e-03 and the conduction route holds 4.76e-05. (iv) the mutual:
>   raw 0.865226 (−13.48%) → corrected **0.909618** (−9.04%) inside the
>   imported `MUTUAL_TOLERANCE` (`:1029`), beside the conduction record
>   0.939822. **What missed, asserted, not loosened.** (i) continuity on
>   the **undriven** port: `|I_disp/I_cond − 1|` = **9.998674e-01** (drive
>   P1, port P2, `:1000`) and **9.993525e-01** (drive P2, port P1,
>   `:1005`) against the pre-registered 0.10 — the ratio is
>   `1.3337e-04 + 1.2703e-03j`, i.e. the two currents differ by their own
>   size. The asserted negative control fails with them: the loop route's
>   record `0.032 + 0.190j` reads **9.860947e-01** on the identical port
>   of the identical solve, separation **0.99×** against the predicted
>   ~50× (`:1022–1025`) — the gap route is *not* better conditioned on
>   the undriven port's current than the route it was scoped to replace.
>   **Mechanism, and it is not `h`.** The undriven gap current
>   **1.5407e-06 A** is correct as a gap-capacitor current,
>   `jω(ε₀A_gap/g)V₂` with V₂ = 1.067 V (`:983`), 1e-6 class. What it
>   fails to equal is the *conduction* route's `σ/L ∫_conductor E·φ̂ dV`,
>   a **volume average around a ring that is open at the gap**: on an
>   open-circuited port the wire current vanishes at the gap faces and
>   peaks opposite them, so the volume average and the gap-face current
>   are different quantities and continuity between them does not hold at
>   any `h`. On the driven port the impressed 1 A dominates both, which
>   is why (ii) reads 2.2%. The step-2c item's stop text ("not the port
>   current at this `h`") is therefore too kind — no refinement closes
>   (i), and the review should read this as a statement about the two
>   *definitions*, not about resolution. **Caveat on (iii)/(iv):** they
>   pass on off-diagonal currents 1e-3 of the conduction route's, which
>   is a scale-invariance of the two-port reduction, not evidence for the
>   route. Rule (c)'s package-gate re-run was **not** executed — nothing
>   landed on `main` to regress. `main` untouched, no band moved,
>   `TH-15` stays 🟡. **Unblock condition (a review's, not an
>   implementer's):** the surviving honest use of this route is what
>   (ii)/(iv) actually support — the **driven** port's current on a mesh
>   with no conductor cells; whether a full 2×2 can be assembled from
>   driven-port currents alone (one solve per port, each read at its own
>   driven gap) is the ruling step 2 now waits on, with the `n × H` facet
>   form the remaining alternative. Both the step-2b and step-2c branches
>   are now kept until that ruling.
>   **Ruling, 2026-09-07 10:30 review — candidate (a): the 2×2 is
>   assembled from driven-port currents alone, and that is not a new
>   choice but the package's existing definition.**
>   `_assemble_impedance_matrix` (`ports/sparameters.py:234–253`) builds
>   `Z[i, k] = V_i / I_k` with `I_k` the *driven* port's current in solve
>   `k` and `V_i` the path voltage read on every port of that solve; the
>   undriven current has never entered `Z` on any route. Anchor (i)
>   therefore gated a quantity no consumer reads, and the 03:00 ruling's
>   premise — that the gap-face current and the conduction volume average
>   are "the same current" on an open ring — is refuted by the measurement
>   and by the definitions: the volume average (1.2e-3 A) is the induced
>   current closing through the undriven ring's own stray capacitance, the
>   gap face carries the gap capacitor's 1.5e-6 A, and an open-circuit `Z`
>   needs the *terminal* current to vanish — which is exactly what the gap
>   route reads. Two consequences. **(1) The right undriven-port anchor is
>   the open-circuit condition itself**, pre-registered here:
>   `|I_disp,undriven| / I_drive ≤ 1e-4` (measured **1.5407e-06** on both
>   solves, `…093741Z:983, 1000, 1005`; predicted 1e-6 class, printed) —
>   the hypothesis `Z = V / I_driven` rests on, asserted for the first
>   time. Its separation control is the conduction volume average on the
>   same undriven ring, **asserted ≥ 100×** the gap-face current (backed by
>   the same comparison on the same fixture, `:1000`, `:1005`: 1.2065e-03
>   / 1.6903e-03 A against 1.5407e-06, i.e. 783× / 1097×, the ceiling),
>   read as the record that an open ring's induced current is not a
>   terminal current. **(2) Anchor (i) and the loop-record control are
>   deleted, not loosened**: each compared two different quantities to a
>   third that neither is, so no `h`, band or fit could make them agree;
>   the test docstring keeps both readings (9.998674e-01 / 9.993525e-01,
>   separation 0.99×) with their log lines as the reason. Nothing that was
>   ever green is touched; (ii)–(iv) stay asserted exactly as
>   pre-registered on the branch, where they are already green. The
>   `n × H` facet form is not needed and is not scoped. Step 2d (§9 item
>   1) lands `f942dc2` under this ruling; step 2 proper (§9 item 4)
>   follows on it, serial.
> * **Step 2d (the gap-displacement route landed on the driven-port
>   definition — scoped 2026-09-07 10:30 review; §9 item 1, full item
>   there).** Take `f942dc2`'s `src/` and `tests/` content and its three
>   logs (path checkout, not a whole-commit cherry-pick — the branch's
>   plan/journal hunks conflict with `main`). In
>   `tests/validation/test_two_torus_gap_displacement_current.py` replace
>   the undriven-continuity test and the loop-record control by the
>   open-circuit anchor and its separation control above; keep (ii) driven
>   continuity ≤ 0.10, (iii) reciprocity at the imported
>   `S_SYMMETRY_BAND`, (iv) the corrected mutual inside the imported
>   `MUTUAL_TOLERANCE`, the conduction records printed beside. Solid
>   fixture only, `-n 4`, ≈ 131 s measured (`…093440Z:1140`) plus rule
>   (c)'s `test_port_package_sparameters.py` re-run. Landing deletes both
>   `attempt/TH-15-step2b-…` (its numbers are in the 🚫 paragraph above)
>   and `attempt/TH-15-step2c-…` (its code is landed) and retires the
>   step-2c known-issues entry. `TH-15` stays 🟡; no §2 change; no band
>   moved.
>   **✅ LANDED 2026-09-07 (12:00 implementer slot).** Path checkout of
>   `f942dc2`'s two `src/fem_em_solver/ports/` files, the test module and
>   its three logs (`main` had not touched `ports/` since `2f65cbe` —
>   verified empty before the checkout); the branch's three
>   `test-results.md` rows copied by hand into chronological place.
>   Module change exactly as ruled: `test_the_gap_current_is_the_
>   conduction_current_on_the_undriven_port` and `test_the_gap_route_
>   beats_the_loop_route_on_the_undriven_port` **deleted** with their
>   readings (9.998674e-01 / 9.993525e-01, separation 0.99×,
>   `20260907T093741Z_TH-15.log:1000, 1005, 1022–1025`) kept in the module
>   docstring as the record and the reason; `LOOP_ROUTE_UNDRIVEN_RATIO`
>   removed with the test that consumed it. **Windows:** a 4 s
>   collect-only smoke (`20260907T170250Z_TH-15.log`, 3 collected), then
>   one `-n 4` complex window with `tests/environment` first, `-s -v
>   --tb=short`, `timeout -k 30 500` — **14 passed in 134.38 s**, elapsed
>   **136 s**, `Status: 0` (`20260907T170302Z_TH-15.log:1150, 1348–1349`);
>   standard by measurement, heavy by ceiling. **Anchors, all asserted,
>   all green.** (v) the new `OPEN_CIRCUIT_BAND` = 1e-4 on
>   `|I_disp,undriven| / I_drive`: **1.541112e-06** on drive P1 / port P2
>   *and* on drive P2 / port P1 — the predicted 1e-6 class, printed with
>   `V_undriven` = 1.067373e+00 V and 1.091649e+00 V
>   (`…170302Z:1050–1053`, `:1057–1060`); the asserted separation control
>   `|I_cond,undriven| / |I_disp,undriven| ≥ 100` reads **782.9×** and
>   **1096.8×** (`:1055`, `:1062`), reproducing the step-2c 783× / 1097×
>   to the digit. (ii) driven continuity **2.243038e-02** / **2.236565e-02**
>   against 0.10 (`:1071`, `:1076`) — the `ρ̂ × (−ẑ) = φ̂` sign confirmed.
>   (iii) reciprocity **5.2613e-04** inside the imported `S_SYMMETRY_BAND`
>   1e-3, conduction route 4.76e-05 printed beside (`:1079`). (iv) the
>   corrected mutual **0.909618** (raw 0.865226, −13.48% → −9.04%) inside
>   the imported `MUTUAL_TOLERANCE` 10%, the conduction record 0.939822
>   printed beside (`:1078`). Every (ii)–(iv) digit is `f942dc2`'s,
>   unmoved by the five-commit rebase. **Rule (c)'s re-run — and a
>   correction to the item's sizing.** At the item's `-n 4` the package
>   gate fails **three digit-reproduction records** (`3 failed / 3 passed`
>   in 145.46 s, `20260907T170528Z_TH-15.log:743–749`); its records were
>   set at `-n 2` (`20260904T110501Z_OPS-37.log:12`, 17 passed / 171.42 s),
>   the misses are 1e-4-class repartitioning of the 184 176-cell mesh, and
>   **no band or physics gate is among them**. Re-run at `-n 2` on the same
>   tree: **17 passed in 187.37 s**, elapsed 188 s, `Status: 0`
>   (`20260907T170838Z_TH-15.log:146, 214–215`) — rule (c) discharged, the
>   conduction route provably untouched (the diff leaves its arithmetic
>   byte-identical). The `-n 4` width sensitivity is filed as its own
>   known-issues entry, not fixed in passing. Step-2c known-issues entry
>   retired in this commit; `attempt/TH-15-step2b-20260907T021500Z` and
>   `attempt/TH-15-step2c-20260907T094500Z` deleted. `TH-15` stays 🟡 (step
>   2 proper and step 3 open); no §2 change; no band moved.
> * **Step 2 proper (the parked PEC-hole 2×2 re-run on the displacement
>   route — §9 item 4 of the 2026-09-07 10:30 review).**
>   **🚫 Attempted 2026-09-07 (16:30 implementer slot): the hole port
>   *solves*, the lossless identity is exact, and two asserted anchors miss
>   on a mechanism the item did not pre-register — stopped under standing
>   rule (e), nothing loosened.** Parked on
>   `attempt/TH-15-step2proper-20260907T213739Z` (`144feff`) — `4dedf89`'s
>   `tests/validation/test_two_torus_pec_hole_ports.py` path-checked-out
>   with `current_route="gap_displacement"` in `_specs()` for both the hole
>   and the solid control, plus the item's printed open-circuit reading —
>   and its two logs. **No `src/` change was needed or made:** the step-2d
>   displacement branch already guards its conduction diagnostic on
>   `_tag_volume(...) > 0` (`ports/gap_voltage.py:365–368`), so the 13:30
>   slot's `non-positive conductor length` never fires on a hole. Windows:
>   a 4 s collect-only smoke (`20260907T213256Z_TH-15.log`, 5 tests), then
>   one `-n 4` complex window with `tests/environment` first, `-s -v
>   --tb=short`, `timeout -k 30 500` — **2 failed / 14 passed in 215.30 s**,
>   elapsed **217 s**, `Status: 1` (`20260907T213308Z_TH-15.log:1904,
>   1907–1908`); heavy by ceiling, standard by measurement.
>   **What passed, asserted.** (v) cells **161 461 / 161 461 = 1.000000** at
>   the imported `CELL_COUNT_BAND`, 24.22 s to mesh (`:590`, `:616`) — step
>   2a's record to the integer. (i) **the lossless identity, exactly**:
>   `max_ij |Re Z_ij|/|Z_ij|` = **0.000000e+00** against the pre-stated
>   `LOSSLESS_BAND` 1e-9 (`:624–627`); `Z` is purely imaginary to the bit,
>   `[[6.51916156j, 1.05007456j], [1.02878956j, 6.42566429j]]` Ω. (ii)
>   reciprocity `‖S − Sᵀ‖/‖S‖` = **4.286714e-04** inside the imported
>   `S_SYMMETRY_BAND` 1e-3 (`:632`). The control: the σ = 800 S/m solid
>   through the identical sweep reads `Re Z₁₁` = **+3.771673e+00 Ω > 0**
>   (asserted), `|Re Z₁₁|/|Z₁₁|` = **0.469192** against the *predicted*
>   order 0.5, printed only (`:1572`). **What missed, asserted, not
>   loosened.** (iii) unitarity `‖SᴴS − I‖_F` = **7.538037e-03** against
>   `LOSSLESS_BAND` 1e-9 and `σ_max` = **1.002865051123** against
>   `1 + PASSIVITY_SIGMA_TOLERANCE` (`:633–634`); (iv) the mutual
>   `Im Z₂₁` = **+1.028789564e+00 Ω** against `ωM₁₂` = 1.241755 Ω, ratio
>   **0.828497 (−17.15%)** outside the imported `MUTUAL_TOLERANCE` 10%
>   (`:636`), beside the solid gap route's 0.909618 and the conduction
>   route's 0.939822. **One mechanism, and it is not dissipation.** `Re Z`
>   is identically zero, so nothing dissipates; what fails is that `Z` is
>   not **symmetric** — `Z₁₂ = 1.05007456j` against `Z₂₁ = 1.02878956j`,
>   **2.07%** apart. For purely imaginary `Z`, `S = (jX − Z₀)(jX + Z₀)⁻¹`
>   is unitary exactly iff `X = Xᵀ`, and 2% of asymmetry lands 7.5e-3 of
>   non-unitarity — the reading. (ii) passes on the *same* matrix only
>   because the S off-diagonals (~0.02) are diluted by the diagonal (~0.97)
>   in `‖S‖`, so S-reciprocity is ~50× weaker than Z-reciprocity on this
>   network; the asymmetry is visible upstream of the reduction as
>   `V_undriven` = 1.0224 V (drive P1) vs 1.0437 V (drive P2) on a nominally
>   mirror-symmetric fixture (`:593`, `:595`). **The item's pre-registered
>   negative result was `Re Z` outside the band with the mutual inside; the
>   measured combination is the opposite one and carries no label, so this
>   slot stopped and reported (standing rule (e)) rather than deciding.**
>   **New measurement (printed, not gated — the item's ask):** the
>   open-circuit reading on the hole, `|I_disp,undriven| / I_drive` =
>   **1.463859e-06** on *both* drives (`:606–615`), beside step 2d's solid
>   record 1.541112e-06 — the first reading of that quantity on a hole
>   mesh, where the gap's end caps are the cavity wall; there is no
>   conduction volume average to separate against (`I_cond` diagnostic
>   `None`, as the route's guard intends). Rule (c) is vacuous — no `src/`
>   diff. `main` untouched, no band moved, `TH-15` stays 🟡.
>   **Unblock condition (a review's, not an implementer's):** whether the
>   2.07% `Z` asymmetry is (a) the mesh's — the two tori are not mirror
>   images after distribution, testable by re-running at `-n 2` and by the
>   solid's own `Z₁₂/Z₂₁` on the same route (step 2d printed `S`
>   reciprocity 5.2613e-04 but never `Z` symmetry), or (b) the
>   displacement route's, the two gap tags reading different effective
>   `A_gap/g`; and separately whether the −17.15% mutual is the PEC cavity
>   wall genuinely excluding flux the filament `ωM₁₂` closed form counts
>   (in which case the comparand, not the band, is what must change) or the
>   same asymmetry seen once. **Neither `LOSSLESS_BAND` nor
>   `MUTUAL_TOLERANCE` is widened, and (i)/(ii) are already green.**
>   **Ruled 2026-09-07 18:00 review — both misses have a candidate
>   mechanism the fixture's own numbers can test in one window, and
>   neither touches a band.** *(a) The 2.07% `Z` asymmetry is a per-port
>   current-reading calibration, not a physics asymmetry.* A lossless
>   reciprocal network has `Z = Zᵀ` exactly, so the measured
>   `Z₁₂/Z₂₁ = (V₁⁽²⁾/I₂)/(V₂⁽¹⁾/I₁)` reads `c₁/c₂` — the ratio of the
>   fractions of each port's true terminal current that its reading
>   captures. The displacement route integrates `jω ε E·n̂` over one facet
>   set per port, so a 2% difference between the two gap tags' effective
>   `A_gap/g` (CAD or mesh) maps one-to-one onto `Z₁₂/Z₂₁`; the conduction
>   route averages the whole ring volume and would not see it. Step 2d
>   never printed the solid's `Z₁₂/Z₂₁`, and its S-reciprocity 5.2613e-04
>   on a `‖S‖ ≈ √2` matrix with `|S₁₂| ≈ 0.02` is *consistent* with a
>   2–3% Z-asymmetry on the solid too — the dilution the slot named. So
>   the discriminating measurement is the solid on both routes plus the
>   two gap tags' areas and lengths read from the mesh, not a `-n 2`
>   re-run (a MUMPS solve moves at ~1e-12 with width, not 2%). *(b) The
>   −17.15% mutual is the comparand, rule (f) class, to the order of the
>   miss.* On the solid the current is uniform across the 5 mm wire
>   (δ ≈ 5.6 mm) and the centre-line filament is the right comparand to
>   ~1%; on a PEC hole the receiving tube carries no flux through its
>   body, so its linked flux is the flux through the disc bounded by its
>   *inner* edge — `a − r_w = 35 mm`, not 40 — and the source's surface
>   current sits off the centre-line as well. The receiver term alone at
>   dipole order, `M ∝ ρ²a/(a² + ρ² + d²)^{3/2}` at `ρ = 35` against
>   `40 mm` with `d = 40 mm`, is **−13%**; the measured hole/solid ratio on
>   the same route is 0.828497/0.909618 = **0.911** (−9%), and the
>   symmetrised hole mutual `(1.05007456 + 1.02878956)/2 / 1.241755` =
>   0.8371 (−16.3%) says the asymmetry is *not* the mutual's miss. The
>   filament `ωM₁₂(a, a, d)` is a comparand the hole's CAD cannot meet;
>   the band is not what moves. The comparand is re-registered by the
>   fixture's own geometry — `_mutual_inductance(a, a − r_w, d)` (receiver
>   exclusion only) and `_mutual_inductance(a − r_w, a − r_w, d)` (both at
>   the inner edge), the helper the module already imports — printed by
>   step 2e, ratified as the bracket by the next review that reads it;
>   the `PEC_BOX_SYSTEMATIC` ladder (+1.69e-2, fitted on the solid) is
>   printed beside but not applied to the hole. *(c)* The S-vs-Z
>   reciprocity dilution is real but confined to fixtures whose
>   S-reciprocity sits far above machine precision — the birdcage 4-port's
>   is ~1e-14 (`PORT-9`), where the dilution is moot; no `PORT-*` chunk
>   opens for it, and step 2e's `Z₁₂/Z₂₁` prints are its measurement.
> * **Step 2e — attribute the hole's 2.07% `Z` asymmetry and re-register
>   the mutual comparand (scoped 2026-09-07 18:00 review, §9 item 2).**
>   On `attempt/TH-15-step2proper-20260907T213739Z` (`144feff`), in
>   `tests/validation/test_two_torus_pec_hole_ports.py` only — no `src/`
>   change, rule (c) vacuous. **Add, asserted — an exact algebraic
>   identity, pre-registered at 1e-9:** on the hole, `S_sym` built from the
>   symmetrised reactance `X_s = (X + Xᵀ)/2` satisfies
>   `‖S_symᴴ S_sym − I‖_F ≤ 1e-9` and `σ_max(S_sym) ≤ 1 + 1e-9` — the
>   proof that the 7.538037e-03 non-unitarity and the σ_max excess are
>   *entirely* the asymmetry (one cause, two readings). The existing (iii)
>   assert on the raw `S` stays in place and red. **Add, printed — rule
>   (e), no prior measurement of these comparisons on this fixture:**
>   (1) `Z₁₂/Z₂₁` and `|Z₁₂ − Z₂₁|/|Z₁₂|` on the hole (2.07% is the record,
>   `…213308Z:624–626`), on the solid on the displacement route, and on
>   the solid on the **conduction** route (a third `_specs()` entry,
>   `current_route="conduction"`, `as_hole=False`) — predicted:
>   displacement-route solid 2–3%, conduction-route solid ≲ 0.5%, which is
>   (a); (2) per port, the gap facet-tag area
>   (`assemble_scalar(form(1 * ds(tag)))`, `MPI.SUM`), the gap volume via
>   `_tag_volume`, `A_gap/g` from them, and the two ports' ratio —
>   predicted 2% if (a) is CAD or mesh; (3) the mutual bracket:
>   `Im Z₂₁/ω` and `Im Z₁₂/ω` against `_mutual_inductance(a, a, d)` (the
>   current comparand, `ωM = 1.241755 Ω`), `_mutual_inductance(a, a − r_w,
>   d)` and `_mutual_inductance(a − r_w, a − r_w, d)` with `a =
>   MAJOR_RADIUS`, `r_w = MINOR_RADIUS`, `d = SEPARATION`, plus the
>   hole/solid ratio on the displacement route (0.911 is the record) —
>   predicted: the measured hole mutual lies between the two inner-edge
>   comparands. **Tier / ranks / cost:** hole 2×2 + solid displacement
>   ≈ 217 s at `-n 4` (`…213308Z:1907`); the added solid conduction sweep
>   ≈ 131 s (step 2c's two solid solves, `…093440Z:1140`) ⇒ one window
>   `-n 4`, `timeout -k 30 600`, heavy by ceiling, ≈ 350 s class;
>   collect-only smoke first. **Traps:** those of step 2 proper; the third
>   spec shares the solid mesh with the second — build it once; `ds` needs
>   the facet tags the hole module already loads; `-k a or b`; complex
>   build + `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; no
>   `run_in_background`. **Scope:** a measurement step on a parked branch
>   — it does *not* close step 2; the two red asserts stay red, both bands
>   unmoved; `TH-15` stays 🟡; the readings go into this bullet on `main`
>   with their log lines, the code and logs stay on the branch (the 16:30
>   slot's pattern); both `TH-15` `attempt/*` branches are kept. **Negative
>   result:** the symmetrised-`S` identity missing at 1e-9 means the
>   non-unitarity is *not* only the asymmetry — a second mechanism,
>   known-issues with the reading, stop; the solid's displacement-route
>   `Z₁₂/Z₂₁` reading ≲ 0.5% while the hole's is 2% means the asymmetry is
>   the *hole's* (its gap end caps are the cavity wall) — report and stop.
>   Either way the 18:00 rulings are re-read, not defended.
> * **Step 2e EXECUTED 2026-09-07 (21:00 implementer slot) — the assert
>   is green, prediction (3) lands to 0.01%, and predictions (1) and (2)
>   both fail in the same direction: mechanism (a) is refuted.** Neither
>   pre-registered exit fired (the 1e-9 identity held; the solid's
>   displacement `Z₁₂/Z₂₁` is *not* ≲ 0.5%, it is larger than the hole's,
>   which is the opposite of that exit's premise). One window, `-n 4`,
>   complex build, `timeout -k 30 560`, heavy by ceiling, **elapsed 306 s**
>   (≈ 350 s predicted), **2 failed / 18 passed**
>   (`20260908T020506Z_TH-15.log`, on the branch; footer `Status: 1`,
>   `Elapsed (s): 306`). The two failures are step 2's pre-existing red
>   asserts, byte-identical to the record — raw-`S` unitarity 7.538037e-03
>   and the mutual 0.828497 / −17.15% (`:1652`, `:1656`). No band moved,
>   no `src/` change; code, log and `test-results.md` row committed on
>   `attempt/TH-15-step2proper-20260907T213739Z` (`4275308`), `main`
>   carrying only this record. Both `TH-15` branches kept.
>   **Asserted (green):** `test_symmetrised_hole_network_is_exactly_unitary`
>   — `‖S_symᴴ S_sym − I‖_F = 9.362447e-18` against the 1e-9 band, and
>   `σ_max(S_sym) = 1.000000000000` against the raw 1.002865051123
>   (`:1582–1583`). **Caveat the executor printed and the next review must
>   read (`:1584`):** `result.s_matrix` is assembled from *wave
>   amplitudes*, not from `z_matrix` (`sparameters.py:194–222`), so what
>   the symmetrisation repairs is `z_to_s(Z_raw)`, whose non-unitarity is
>   **1.183730e-03** with `σ_max` 1.000418599355. The identity therefore
>   proves the asymmetry is the whole of the *Z-route* rung; it does **not**
>   prove the recorded 7.538037e-03 on the wave-assembled `S` is only the
>   asymmetry — that number is 6.4× larger, and the 18:00 ruling did not
>   draw the distinction. The assert as pre-registered passes and was not
>   changed.
>   **(1) `Z₁₂/Z₂₁`, printed (`:1608–1610`)** — hole displacement
>   `|Z₁₂/Z₂₁| = 1.020689360`, asymmetry **2.026999e-02** (reproducing the
>   2.07% record); solid displacement 1.022546702 / **2.236184e-02**;
>   solid **conduction** 1.022477321 / **2.229415e-02**. The 2–3%
>   prediction for the solid displacement route holds; the ≲ 0.5%
>   prediction for the conduction route **fails** — it reads the same
>   2.2%.
>   **(2) Gap geometry, printed (`:1617–1623`)**, `g = 1.395505060e-02` m:
>   both ports on both meshes identical — `A_sheet = 1.451325262180e-04`
>   m², `V_gap = 7.546891363338e-07` m³, `A_gap = V_gap/g =
>   5.408000000000e-05` m², P1/P2 ratios **1.000000000 to twelve digits**.
>   The ~2% prediction **fails**. (Implementation note: tags 211/212 are
>   *interior* sheets, so `ds` reads zero on them; the lineage's `dS`-based
>   `_facet_area`, already `MPI.SUM`-reduced, was used and said so in a
>   code comment.)
>   **Together (1)+(2) refute the 18:00 ruling's mechanism (a).** The
>   asymmetry is not the per-port displacement-gap calibration and not
>   CAD/mesh gap geometry; it is not the hole's either, since the solid
>   shows it slightly *larger*. It is common to hole and solid and to both
>   current routes — i.e. it lives in the voltage/field solution, not in
>   the current reading. **For the review:** the remaining candidate the
>   fixture can test is the *voltage* reading — the point-sampled
>   `_path_voltage` the `OPS-41` width entry already suspects — and a
>   `c₁/c₂` that survives route-swapping is not a calibration at all.
>   **(3) Mutual bracket, printed (`:1630–1637`)**, ω = 6.283185e+07 rad/s
>   — hole `Im Z₂₁/ω = 1.637369444655e-08` H, `Im Z₁₂/ω =
>   1.671245571251e-08` H, mean **1.654307507953e-08** H; solid
>   1.709957284323e-08 / 1.748428708228e-08 H. Against
>   `M(a, a, d) = 1.976313852319e-08` H (the current comparand,
>   ωM = 1.241755 Ω): hole `Z₂₁` 0.828497 (−17.15%), hole mean 0.837067,
>   solid `Z₂₁` 0.865226. Against `M(a, a − r_w, d) =
>   1.654508076658e-08` H (receiver inner edge): hole `Z₂₁` 0.989641
>   (−1.04%), **hole mean 0.999879 (−0.01%)**, solid 1.033514. Against
>   `M(a − r_w, a − r_w, d) = 1.412092268826e-08` H: hole `Z₂₁` 1.159534,
>   hole mean 1.171529, solid 1.210939. `PEC_BOX_SYSTEMATIC = +1.69e-02`
>   printed beside, **not** applied. Prediction (3) **holds sharply**: the
>   hole mutual lies between the two inner-edge comparands, and the
>   symmetrised hole mean matches the receiver-exclusion filament
>   `M(a, a − r_w, d)` to **0.01%** — the rule-(f) re-registration the
>   18:00 ruling proposed, now with a number, for a review to ratify.
>   One discrepancy to note: the hole/solid ratio on the displacement
>   route reads `Z₂₁` **0.957550** / `Z₁₂` 0.955856, not the 0.911 record
>   — this window's own solid reads 0.865226 of `M(a, a, d)` where the
>   ruling assumed 0.909618, so the two are not the same comparison and
>   the review should say which solid reading stands. Not measured (a
>   second window): the solid conduction route's `Im Z/ω`.
> * **Ruled 2026-09-08 03:00 review — three rulings on step 2e.** (1)
>   **The receiver-inner-edge comparand is ratified under rule (f).** A
>   PEC tube carries no flux through its own cross-section, so the EMF
>   around *every* loop on its surface is the same and equals the flux
>   through its inner-edge disc: `M(a, a − r_w, d)` with the source kept
>   as the filament at `a` is the first-order closed form for a
>   filament-source / hole-receiver pair, and the symmetrised hole mean
>   lands on it to −0.01% (`20260908T020506Z_TH-15.log:1630–1637`). What
>   it leaves out, and the docstring must say: the *source* is a hole too
>   and its current is not a filament at `a` — the ~1% between `Z₂₁`
>   alone (0.989641) and the mean is the asymmetry, not the comparand.
>   Step 2f asserts the mutual against it at the imported `MUTUAL_TOLERANCE`
>   10% (unmoved), the old `M(a, a, d)` comparison kept as a printed
>   record beside. (2) **The wave-vs-`Z` distinction is real and step 2
>   cannot close on the symmetrised identity alone.** `result.s_matrix`
>   is assembled from wave amplitudes (`sparameters.py:194–222`) and its
>   7.538037e-03 non-unitarity is 6.4× the `z_to_s(Z_raw)` route's
>   1.183730e-03 (`:1584`); the extra 6.4e-3 is a second reading the
>   fixture makes and nobody has attributed — step 2f prints
>   `‖S_wave − z_to_s(Z_raw)‖_F` and the per-entry difference, predicted
>   the whole of the gap. The unitarity gate stays red and unmoved.
>   (3) **No solid mutual reading "stands"**: the 0.909618 is step 2d's
>   *unboxed* two-torus record and 2e's 0.865226 is the hole module's own
>   boxed solid, so the 0.911 hole/solid ratio compared two fixtures;
>   step 2f prints the boxed solid on both routes beside the unboxed
>   record with the log lines, and the hole/solid ratio is the same-mesh
>   0.9576 (`:1608–1610`) until a review says otherwise. **The surviving
>   asymmetry candidate is the voltage reading**, and it is common to
>   both fixtures and both current routes: step 2f measures it.
> * **Step 2f — the gap voltage two ways, and the mutual gated on the
>   ratified comparand (scoped 2026-09-08 03:00 review, §9 item 2).** On
>   `attempt/TH-15-step2proper-20260907T213739Z` (`4275308`), the same
>   arrangement as 2e: the record lands on `main` in this bullet, code and
>   log stay on the branch; test module only,
>   `tests/validation/test_two_torus_pec_hole_ports.py`; no `src/`, rule
>   (c) vacuous. **The change:** (a) the mutual assert re-pointed at
>   `_mutual_inductance(a, a − r_w, d)` per ruling (1), docstring carrying
>   the derivation and the omission, the `M(a, a, d)` ratio printed as the
>   superseded record; (b) per port, per drive, on the hole and on the
>   boxed solid (displacement route): the point-sampled `_path_voltage`
>   the port reads, and the gap-averaged voltage `V̄ = (g / V_gap)
>   ∫_gap E · d̂ dV` (the gap tag's volume, `d̂` the gap's axis as
>   `_specs()` gives it, `assemble_scalar` reduced `MPI.SUM`,
>   `quadrature_degree` pinned) — printed as `V_path`, `V̄`, and
>   `|V_path − V̄| / |V̄|`; then `Z` rebuilt with `V̄` in place of `V_path`
>   and its `Z₁₂/Z₂₁` printed beside the record's; (c) ruling (2)'s prints,
>   `‖S_wave − z_to_s(Z_raw)‖_F` and the 2×2 difference. **Anchors
>   (asserted):** (i) the mutual on the hole, `Im Z₂₁/ω` against
>   `M(a, a − r_w, d)`, inside the imported `MUTUAL_TOLERANCE` — backed by
>   2e's 0.989641 (`…020506Z:1630–1637`); (ii) 2e's symmetrised-`S`
>   identity and the lossless identity, unchanged; the raw-`S` unitarity
>   assert stays red and unmoved. **Printed, predicted (rule (e)):** (1)
>   `|V_path − V̄|/|V̄|` — predicted ~1–2% on every port, with the two
>   ports' readings differing in the direction that makes `Z₁₂/Z₂₁` 2%;
>   (2) `Z₁₂/Z₂₁` on the `V̄` route — predicted ≲ 0.5% if the path sample
>   is the mechanism, the record's 2.07% if it is not; (3) the wave-vs-`Z`
>   gap — predicted 6.4e-3, the whole of the difference. **Tier / ranks /
>   cost:** 2e's window measured **306 s** at `-n 4` for hole + solid
>   (displacement) + solid (conduction); the conduction solid is not
>   needed here — drop it (≈ 130 s saved) and the two `V̄` assembles are
>   seconds ⇒ one window `-n 4`, `timeout -k 30 560`, ≈ 200 s class;
>   collect-only smoke first. **Traps already paid for:** those of 2e —
>   tags 211/212 are interior sheets (`ds` reads zero; the `dS`-based
>   `_facet_area` lineage), `-k a or b`, complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first, no
>   `run_in_background`; the gap volume integral must be restricted to the
>   gap tag (`dx(tag)`), and `d̂` is a constant vector, not
>   `SpatialCoordinate`-derived (the ordering trap does not arise). **Scope:**
>   closes nothing — step 2 stays open on the unitarity gate, `TH-15` stays
>   🟡, both `TH-15` branches kept; the mutual gate's comparand changes
>   under rule (f), no band moves. **Negative result:** the `V̄`-route
>   `Z₁₂/Z₂₁` still 2% with `V_path` and `V̄` agreeing to < 0.5% means the
>   asymmetry is in the field, not the reading — known-issues with the
>   table, mark 🚫 (rule (d)), stop; the mutual missing the ratified
>   comparand by more than 10% cannot happen on the same mesh (2e's number
>   is the backing) — if it does, the module or mesh changed: report, do
>   not re-point, stop.
> * **Step 2f executed 2026-09-08 06:00 slot (implementer) — the point-
>   sampled path voltage IS the 2% `Z` asymmetry.** One window, `-n 4`,
>   complex build, `timeout -k 30 560`: **350 s**, `Status: 1`,
>   **1 failed / 21 passed** in 348.49 s
>   (`20260908T111059Z_TH-15.log:1806`, footer `:1957–1958`); the single
>   failure is step 2's pre-registered raw-`S` unitarity gate,
>   `7.538037e-03 > 1e-09` (`:1665, 1730`), red and unmoved as scoped. A
>   first window without `-s` (`20260908T110445Z_TH-15.log`, 355 s, same
>   1 failed / 21 passed) swallowed the prints and was re-run; both logs
>   are on the branch. Code and both logs on
>   `attempt/TH-15-step2proper-20260907T213739Z` at **`10b3af1`** (test
>   module only, no `src/` — rule (c) vacuous); `main` carries this record.
>   **(a) The mutual anchor is green on the ratified comparand.**
>   `Im Z₂₁ = +1.028789564e+00` Ω against `M(a, a − r_w, d) =
>   1.654508076658e-08` H (`ωM = 1.039558` Ω): **ratio 0.989641 (−1.04%)**,
>   inside the imported, unmoved `MUTUAL_TOLERANCE` 10% (`:1613`) —
>   reproduces 2e's number exactly. The superseded `M(a, a, d)` ratio
>   **0.828497 (−17.15%)** is printed beside it (`:1614, 1618`). The
>   docstring carries the PEC-tube derivation and the disclosed
>   source-side omission. (ii) lossless identity `max|Re Z|/|Z| = 0`, and
>   the symmetrised-`S` identity `4.444549e-16` vs 1e-9 with
>   `σ_max = 1.000000000000` (`:1584–1585`) — both as 2e.
>   **(b) Prediction (2) holds sharply and prediction (1) fails**
>   (`:1629–1646`). Rebuilding `Z` on the gap-averaged voltage collapses
>   the asymmetry on *both* fixtures: `|Z₁₂ − Z₂₁|/|Z₁₂|` goes
>   **2.026999e-02 → 1.510620e-04** on the hole (`|Z₁₂/Z₂₁|` 1.020689360 →
>   **0.999848961**, `:1634–1635`) and **2.236184e-02 → 1.925413e-04** on
>   the boxed solid (1.022546701 → **0.999807496**, `:1642–1643`) — a
>   **134× / 116×** reduction from changing the *reading* alone. The probe
>   re-solve is the sweep's solve to round-off
>   (`‖Z_path − Z_sweep‖/‖Z_sweep‖` = 5.067176e-08 hole / 8.072266e-08
>   solid, `:1637, 1645`) and the sweep's own `Z` reproduces the `V_path`
>   asymmetry to nine digits (`:1636, 1644`), so the two routes differ only
>   in how the gap voltage is read. The mechanism is visible in the
>   readings themselves: the two **undriven** `V̄` values agree across
>   drives to **ten digits** (`6.789932166e-01` vs `6.789932160e-01` on the
>   hole, `:1631–1632`; `7.146416533e-01` vs `7.146416531e-01` on the
>   solid) where the `V_path` samples differ by 2% (1.022408810 vs
>   1.043719436) — the arc sample, not the field, carries the asymmetry.
>   Prediction (1) is **refuted**: `|V_path − V̄|/|V̄|` is **49–54%** on
>   undriven ports and **100.2%** on driven ones, not the predicted 1–2%,
>   because the driven-port `V̄` is dominated by the impressed source
>   inside the gap volume and the gap box is longer than `g` — `V̄` is
>   **uncalibrated in magnitude** and only its *reciprocity* is meaningful
>   here. Disclosed implementation note: the §7 formula
>   `V̄ = (g/V_gap)∫E·d̂ dV` is `−V` in `_path_voltage`'s convention
>   (`V = −∫E·dl`, `d̂ = +ŷ` the arc tangent at `φ = 0`), so the sign is
>   matched and the literal expression retained as `v_bar_raw`; nothing
>   scaled or fitted. Quadrature pinned at degree 4, `assemble_scalar`
>   explicitly `MPI.SUM`-reduced, measure restricted to `dx(gap tag)`.
>   **(c) Prediction (3) misses by 4.6×** (`:1651–1657`):
>   `‖S_wave − z_to_s(Z_raw)‖_F` = **2.915842e-02**, not the predicted
>   6.4e-3 (2.061373e-02 relative to `‖S_wave‖_F`), and it is **essentially
>   all off-diagonal** — `|diff|` = 8.425202e-04 / **2.081315e-02** /
>   **2.038642e-02** / 8.427208e-04 on [1,1] / [1,2] / [2,1] / [2,2]. The
>   6.4e-3 prediction was the *difference of two non-unitarity residuals*,
>   which is not this norm; the wave-vs-`Z` gap is a larger, distinctly
>   off-diagonal object than the ruling assumed. **Scope respected:** step
>   2 stays open on the unitarity gate, `TH-15` stays 🟡, no band moved,
>   both `TH-15` branches kept, the solid conduction spec dropped from the
>   window as planned (2e's 2.229415e-02 quoted in the docstring).
>   **For the review:** the `_path_voltage` fix chunk the 03:00 review
>   named is now licensed by a measurement, and the open question it must
>   answer is calibration — restrict the average to the `g`-long gap slab
>   rather than the whole burial/overhang box and exclude the impressed
>   source on the driven port, then check whether that one change also
>   moves the 2.9e-2 off-diagonal wave-vs-`Z` gap and the 7.5e-3 raw-`S`
>   non-unitarity, or whether those are a second, independent reading.
> * **Ruled 2026-09-08 10:30 review — licensed twice, not yet
>   specifiable; step 2g measures the calibration (§9 item 4).** Two
>   independent measurements name the point-sampled `_path_voltage` as
>   the carrier: 2f's 134× / 116× collapse of the `Z` asymmetry under a
>   gap-averaged read, and `OPS-41`'s 3.249e-04 width move on `V` against
>   ≤ 3.6e-09 on `I` (`20260908T123716Z_OPS-41.log:709–715` vs
>   `…124026Z:719–725`, same mechanism on the package fixture). A `src/`
>   replacement is therefore licensed — **but the gap average 2f measured
>   is uncalibrated by 49–100%**, and a `src/` change that cannot
>   reproduce the mutual inside the unmoved 10% is not a fix. The
>   geometry says why: the gap box is `2(r_w + GAP_OVERHANG)` = 10.4 mm
>   square around a 10 mm wire (1.38× the wire's cross-section) and
>   `2(a·sin(θ/2) + GAP_BURIAL)` = 13.95 mm long against an 11.95 mm
>   chord (`_gap_half_extents`, `test_port_package_sparameters.py:
>   296–299`), and `V̄` was normalised by the *box* length over the
>   *tag's* meshed volume. Step 2g measures the calibration on the
>   branch, test module only, before any `src/` chunk is written; the
>   `src/` chunk is scoped from its table. 2f's prediction (3) is
>   restated for the record: the 03:00 6.4e-3 was the difference of two
>   non-unitarity residuals; the wave-vs-`Z` gap is 2.915842e-02,
>   off-diagonal, and unattributed. `OPS-41`'s ungated `V_P2^(P2)`
>   diagonal (2.287e-02 across widths) is the driven-port reading 2g
>   prints on this fixture — no separate item.
> * **Step 2g — the calibrated gap average: footprint- and
>   chord-restricted volume reads beside 2f's, `Z` and the mutual
>   rebuilt on each, reading A's reciprocity asserted (scoped 2026-09-08
>   10:30 review, §9 item 4).** On
>   `attempt/TH-15-step2proper-20260907T213739Z` (`10b3af1`), 2e/2f's
>   arrangement: the record lands on `main` in this bullet, code and log
>   stay on the branch; test module only,
>   `tests/validation/test_two_torus_pec_hole_ports.py`; no `src/`, rule
>   (c) vacuous. **The change:** beside 2f's `V̄` (reading **A**, the
>   whole tag), two restricted averages built from a **DG0 indicator on
>   cell midpoints** (`dolfinx.mesh.compute_midpoints` on the gap tag's
>   owned cells — rank-local, no UFL conditional, no `sqrt`; the
>   `test_birdcage_b1_plus_map.py:242–254` pattern): (**B**) the tag ∩ the
>   wire footprint `(x − a)² + z² ≤ r_w²` about the gap's arc axis;
>   (**C**) B ∩ the chord slab `|y| ≤ a·sin(θ/2)`; each normalised as
>   `V̄_X = ∫_X E·d̂ dV / A_X` with `A_X = V_X / ℓ_X` for the indicated
>   (reduced) volume `V_X` and the slab's own length (`ℓ_B` the tag's
>   `y`-extent, `ℓ_C` the chord); the indicated volumes printed against
>   the CAD `π r_w² · 2a sin(θ/2)` = 938.6 mm³ so the DG0 granularity is
>   visible (predicted within 5% at `GAP_ARC_RESOLUTION` 0.3 mm). Per
>   port, per drive, on the hole and the boxed solid (displacement
>   route): `V_path`, `V̄_A`, `V̄_B`, `V̄_C`, `|V_path − V̄_X|/|V̄_X|`;
>   `Z` rebuilt on B and on C with `|Z₁₂ − Z₂₁|/|Z₁₂|` and `Im Z₂₁/ω`
>   against the ratified `M(a, a − r_w, d)`. **Anchors (asserted):** (i)
>   and (ii) as 2f (the mutual on the path route inside the unmoved 10%,
>   the lossless and symmetrised-`S` identities; the raw-`S` unitarity
>   red unmoved); (iii) **new, backed by 2f:** reading A's rebuilt `Z`
>   reciprocal to `|Z₁₂ − Z₂₁|/|Z₁₂| ≤ 1e-3` on the hole and the solid
>   (1.510620e-04 / 1.925413e-04, `20260908T111059Z_TH-15.log:1634–1635,
>   1642–1643`). **Printed, predicted (rule (e)):** (1)
>   `|V_path − V̄_C|/|V̄_C|` on the two undriven readings — predicted
>   ≤ 5% (A reads 49–54%, `:1630–1641`); (2) reading C's reciprocity —
>   predicted ≤ 1e-3 (the restriction is the same on both ports); (3) the
>   mutual on C's `Z₂₁` — predicted inside 10%, the first calibrated
>   volume-read mutual; (4) the driven-port `|V_path − V̄_C|/|V̄_C|` — no
>   prediction (A reads 100.2%; the impressed source lives in the same
>   cells); (5) `‖S_wave − z_to_s(Z_C)‖_F` beside 2f's 2.915842e-02.
>   **Tier / ranks / cost:** 2f's window measured **350 s** at `-n 4`
>   (`:1957–1958`); six extra DG0 assembles are seconds ⇒ one window
>   `-n 4`, `timeout -k 30 560`, **`-s`** (2f lost a window to a
>   swallowed print); collect-only smoke first. **Traps already paid
>   for:** 2f's — tags 211/212 are interior sheets (`ds` reads zero; the
>   `dS`-based `_facet_area` lineage), `dx(tag)`, `d̂` a constant vector,
>   the sign convention (`V̄_raw = −V` in `_path_voltage`'s convention —
>   keep 2f's `v_bar`/`v_bar_raw` pair); **midpoints and
>   `cell_tags.find` are rank-local — build the indicator on owned cells
>   and reduce the indicated volume `MPI.SUM`**; the indicator multiplies
>   inside the form (`chi · inner(E, d̂) · dx(tag)`) at the pinned
>   `GAP_AVERAGE_QUADRATURE_DEGREE`; `-k a or b`; complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; no
>   `run_in_background`. **Scope:** closes nothing — step 2 stays open on
>   the unitarity gate, `TH-15` stays 🟡, both `TH-15` branches kept, no
>   `src/`, no band moved; the deliverable is the specification of the
>   `src/` `_path_voltage` replacement, which a review writes from the
>   table. **Negative result:** reading C still ≥ 20% off `V_path` on the
>   undriven ports with its indicated volume within 5% of CAD means the
>   arc sample is not representative of the cross-section field at all
>   and the fix is definitional (a terminal-face potential difference),
>   not geometric — the table here and in known-issues, mark 🚫 (rule
>   (d)), stop; C's reciprocity worse than 1e-2 means the restriction
>   re-introduces the sampling sensitivity — same disposition.
> * **Step 2g EXECUTED 2026-09-08 (16:30 implementer slot) — the
>   calibrated reading is the footprint restriction B, not the chord
>   restriction C; C's negative-result clause fires and the item is
>   marked 🚫, but the deliverable (the `src/` specification) is served.**
>   On the branch, now `6f68956`; nothing on `main` but this record, the
>   known-issues row and the §9 marking. One window,
>   `20260908T213405Z_TH-15.log`, `-n 4`, complex build +
>   `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first, `-s -v
>   --tb=short`, `timeout -k 30 560`: **1 failed / 23 passed in 383.64 s**,
>   `Status: 1`, elapsed **386 s** (heavy by ceiling; collect-only smoke
>   first, 13 tests). The single red is step 2's pre-registered raw-`S`
>   unitarity gate, `‖SᴴS − I‖_F = 7.538037e-03 > 1e-09`, **byte-identical
>   to 2f and unmoved**. Test module only; no `src/`; no band moved.
>   **Anchors:** (i) and (ii) green as 2f; **(iii), the new assert:**
>   reading A's rebuilt `Z` reciprocity **1.510600e-04** (hole) /
>   **1.925424e-04** (solid) against `READING_A_RECIPROCITY_BAND` = 1e-3
>   (`:1666–1667`), reproducing 2f's digits. **The table** (all printed,
>   rule (e)) — undriven `|V_path − V̄_X|/|V̄_X|` (`:1674–1675,
>   1686–1687`): `A` 50.577 / 53.716 / 49.341 / 52.725 %, **`B` 2.736 /
>   7.414 / 2.535 / 6.267 %**, `C` 114.867 / 307.792 / 108.537 /
>   265.311 %; driven-port miss (no prediction) A 100.23 %, B ≈ 102.2 %,
>   C ≈ 100.5 % (`:1673, 1676, 1685, 1688`). Rebuilt `Z` (`:1677–1679,
>   1689–1691`), reciprocity then `Im Z₂₁/ω` against the ratified
>   `M(a, a − r_w, d)` = 1.654508076658e-08 H: **A** 1.5106e-04 /
>   1.9254e-04, 1.087396e-08 H (−34.28 %) / 1.144938e-08 H (−30.80 %);
>   **B** 2.434274e-02 / 1.412485e-02, 1.593762e-08 H (**−3.67 %**) /
>   1.667684e-08 H (**+0.80 %**) — inside the unmoved 10 %; **C**
>   8.594116e-01 / 7.135082e-01, 7.620397e-09 H (−53.94 %) /
>   8.197867e-09 H (−50.45 %). Indicated volumes (`:1671–1672,
>   1683–1684`): `V_A` = 754.689 mm³ on all four, `V_B` 553.436–556.300,
>   `V_C` 475.336–477.301 mm³ ⇒ `V_C`/CAD 938.947 mm³ = 0.5069 (−49.3 %).
>   `‖S_wave − z_to_s(Z_X)‖_F` (`:1680–1682, 1692–1694`): hole 2.811093 /
>   2.826628 / 2.817232, solid 2.613614 / 2.627881 / 2.620246 — all O(1),
>   not comparable to 2f's 2.915842e-02 (which is `z_to_s` of the
>   *sweep's* `Z_raw`, not of a `V̄` route), so **prediction (5) is
>   uninformative as posed**. **Predictions (1), (2) and (3) all fail for
>   C and all but hold for B**, which the item did not separately predict:
>   the footprint restriction alone lands the mutual inside the unmoved
>   10 % on both fixtures where the whole tag misses by −34 % / −31 %.
>   **Two readings for a review, neither ruled here.** (α) The item's CAD
>   comparand looks **2× too large for this tag**: `V_A` = 754.689 mm³ is
>   exactly half the naive box (108.16 mm² × 13.955 mm = 1509.4 mm³) and
>   the fixture's own `A_gap = V_gap/g` = 5.408000e-05 m² is exactly half
>   `(2(r_w + GAP_OVERHANG))²` (`:1603–1604`) — the gap cell tag appears
>   to be a half-domain; against the halved comparand 469.5 mm³, `V_C` is
>   **+1.39 %**, inside the predicted 5 %, and `V_B/(π r_w² ℓ_B)` = 0.505
>   for the same reason. This is arithmetic on printed numbers, not a
>   measurement. (β) The chord slab drops ≈ 14 % of the volume
>   (`V_C/V_B` ≈ 0.859) but ≈ 52 % of the reading, so the field is
>   concentrated in the `GAP_BURIAL` overhang beyond the chord and C
>   amputates it asymmetrically — a mechanism, untested in this slot.
>   **Disposition:** C's reciprocity 8.6e-01 / 7.1e-01 exceeds the item's
>   own 1e-2 threshold ⇒ §9 item 4 marked 🚫 per rule (d), table into
>   known-issues, stop. Step 2 stays open on the unitarity gate, `TH-15`
>   stays 🟡, both branches kept, nothing loosened. **For the review:** the
>   `src/` `_path_voltage` replacement should be specified from **reading
>   B** (wire-footprint-restricted, whole-`y` slab), with (α) settled
>   first — if the tag is a half-domain, every `V̄` normalisation on this
>   fixture carries a factor 2 that reading B's mutual agreement does not
>   currently reflect.
> * **Step 2h EXECUTED 2026-09-09 (06:00 implementer slot, `mesh-probe`,
>   🧪 measurement-only) — reading (α) is CONFIRMED: the gap cell tag is
>   exactly half the gap box, to twelve digits, and by design. The factor
>   2 is settled.** `main` at `c212bc1`; nothing but this record, the
>   known-issues row, the probe script and the §9 marking. Geometry only,
>   **no solve**, real build. Two windows, `-n 2`, `timeout -k 30 300`,
>   `-s`, **character-identical in every measured digit** (only gmsh build
>   times differ): `20260909T110257Z_TH-15-step2h.log` (Status 1, elapsed
>   **58 s**) and `20260909T110426Z_TH-15-step2h.log` (Status 1, **56 s**);
>   standard by measurement, heavy by ceiling. `Status: 1` is the anchor's
>   own negative-result exit, not a crash. **The three numbers the `src/`
>   specification is written from**, identical on both fixtures (hole and
>   boxed solid) and both ports (`:513–519, 1438–1444`): `V_tag` =
>   7.546891363338e-07 m³ = **754.689136 mm³**; **`V_tag`/box = 0.500000**
>   against the CAD box 1509.378273 mm³; `V_tag`/(π r_w² · chord) =
>   **0.803761** against 938.947478 mm³; and `A_gap = V_tag/g` =
>   5.408000000000e-05 m² = 54.080000 mm² = **0.500000** of the box
>   cross-section 108.160000 mm² (`g = 2·half_y` = 1.395505060e-02 m,
>   chord = 11.955051 mm). Extents from owned cell midpoints (hole, P1):
>   `x` span 1.017787e-02 and `y` span 1.388758e-02 cover the full box
>   (10.4 / 13.955 mm), while **`z` spans 5.067458e-03 — half of 10.4 mm**,
>   over `z ∈ [−2.5099e-02, −2.0032e-02]`, i.e. the half *below* the
>   torus-1 centre plane at `z = −0.02`. Owned cells: hole 12 585 / 12 632,
>   solid 13 661 / 13 648 (the solid reproduces `OPS-39`'s `-n 1` census).
>   **Negative control green** — the C2 identity `|V_P1 − V_P2|/|V_P1|` =
>   **2.525310e-15** (hole) / **8.698290e-15** (solid) against 1e-3
>   (`:521, 1446`), so the volume reading is not a probe bug.
>   **Anchor's negative-result clause fired, and the mechanism is
>   documented in `src/` itself.** `V_tag` matches **neither** named CAD
>   candidate inside 5% (`:1450–1453`), which the item says to record and
>   stop on — but the missing third candidate is not a guess: when
>   `emit_port_sheet=True` the generator **splits each gap box at its
>   mid-plane into two cell groups**, `101`/`111` for gap 1 (below/above)
>   and `102`/`112` for gap 2, and its docstring already says "a caller
>   that selects the gap volume by tag must take **both halves**"
>   (`src/fem_em_solver/io/mesh.py:1176–1181, 1425–1426, 1455,
>   1542, 1582–1583`). The generator's own fragment census, printed above
>   the mesh, reads `gap_1 = gap_2 = gap_1_upper = gap_2_upper =
>   7.546891e-07` against `gap_box_analytic = 1.509378e-06` (`:40`) —
>   four equal halves, two per port. So the whole gap box is `101 ∪ 111`
>   (`102 ∪ 112`), and `GAP_TAGS = (101, 102)` selects half of it.
>   **Consequence for the `src/` specification (the next review's, not
>   ruled here):** `_tag_volume(GAP_TAGS[k])` reads half the gap box, so
>   every `V̄` normalised by the box length over `V_tag` on this fixture
>   carries a factor 2; 2g's `V_C`/CAD = 0.5069 is `V_C` against the
>   *full*-box-scale comparand, and against the half comparand 469.5 mm³
>   it is **+1.39%**. **Scope: closes nothing** — `TH-15` stays 🟡 on step
>   2's unitarity gate, both branches kept, no `src/` change, no test
>   edited, no band moved, no record written. Deliverable landed:
>   `scripts/probes/th15_gap_tag_geometry.py` (imported by nothing).
> * **Step 3a (the birdcage hole as a `MeshGenerator` route — scoped
>   2026-09-06 10:30 review, §9 item 4; step 2a's pattern on
>   `birdcage_port_domain`).** One additive `as_hole=False` keyword: the
>   coil conductor volumes cut from the air with `removeTool=False` and
>   dropped, the phantom and gap boxes kept as volumes, the sheets kept,
>   the coil-surface group (an exported `BIRDCAGE_CONDUCTOR_SURFACE_TAG`)
>   from `getBoundary` of the **meshed** volumes. On the `PORT-9` four-port
>   fixture (116 085-cell solid), asserted with every band imported: the
>   four sheets at the `GEO-18` analytic 1.120000000e-04 m² at `EXACT`
>   1e-9 (the sheets still touch the surface-only terminals); the
>   phantom + air + gap partition of the box minus the coil's CAD volume
>   at 1e-9; the coil-surface area equal to the solid route's
>   conductor/air + conductor/phantom interface area to ≤ 1e-5 (the
>   `GEO-9` identity; step 2a read 3.7e-7); conductor tags absent, census
>   summing to `size_global`. Cell count printed as the first record.
>   Control: `as_hole=False` reproduces 116 085 with the conductor tags
>   present, hole < solid. Pre-registered stop: gmsh "overlapping facets"
>   on the cut is a `GEO` finding — known-issues, park, stop. Standard,
>   `-n 2`, real build, ≈ 60 s. No solve; step 3 proper stays the weekly's.
>   **✅ LANDED 2026-09-06 (16:30 implementer slot), 6 passed / 54 s,
>   standard, `-n 2`, real build (`20260906T213913Z_TH-15.log:2655`).**
>   `birdcage_port_domain(as_hole=True)` (additive, keyword-only, default
>   `False`) and the exported `BIRDCAGE_CONDUCTOR_SURFACE_TAG = 401`; new
>   gate `tests/mesh/test_birdcage_conductor_hole.py`. Readings, all at
>   `-n 2`: the hole meshes **80 181 cells / 19 369 vertices in 23.02 s**
>   against the solid control's **116 085** (ratio to the `PORT-9` record
>   **1.000000**, band 0.01) — hole/solid **0.690709**, the first
>   measurement of this route and the (1\*) record it opens
>   (`:2628–2632`); all four port sheets mesh **1.120000000e-04 m²** on
>   *both* routes at **≤ 3.331e-16** relative against the imported
>   `SHEET_AREA_BAND` 1e-9 — no terminal was detached (`:2637–2644`); the
>   cavity wall (tag 401, 40 CAD surfaces, **19 894 facets**,
>   4.052771523e-02 m²) reproduces the solid route's whole conductor
>   interface 4.052769926e-02 m² (19 877 facets) to **3.942e-07**, band
>   1e-5 — step 2a's two-torus reading was 3.70e-07 (`:2650`); the hole
>   census is `{2, 3, 101–104, 201–204}` with tag 1 **absent** and present
>   in the control, both censuses summing to their owned cell count.
>   The pre-registered `GEO-23` stop did not fire. **One band was
>   *re-registered by measurement*, not loosened** (MAG-10/MAG-15
>   precedent, recorded in the test's docstring): the partition anchor's
>   1e-9 was stated against the *analytic* box, and the first window
>   measured the **solid** route — which this chunk does not touch and
>   which has no cut in it — missing the analytic box by **3.379e-08**
>   relative, the hole missing `box − coil` by **3.408e-08**, i.e. the same
>   ~3.9e-10 m³ that is OCC's own mass quadrature on the tori and cylinders
>   (3.9e-06 of the coil's 9.939e-05 m³;
>   `20260906T213704Z_TH-15.log:2647`, Status 1). The chunk's own identity
>   is now stated where both sides are the same OCC numbers — hole groups +
>   conductor = solid groups, ratio **1.000000000000** at 1e-9 — and the
>   analytic comparison is asserted on **both** routes at a measured
>   `CAD_ANALYTIC_BAND` = 1e-7 (`20260906T213913Z_TH-15.log:2647`). Scope
>   held: no solve, no S-matrix, no PEC gate, no 16-leg variant; the row
>   stays 🟡.
> * **Step 3 (the birdcage, heavy).** `birdcage_port_domain` with the coil
>   as a hole, phantom present, `PORT-9`/`PORT-11`'s three gates at 10 / 64
>   / 128 MHz with every band imported, plus **`Re P_in = ½∫_phantom σ|E|²`
>   to ≤ 1e-3** (all loss is in the phantom by construction). Record the
>   4×4 beside the σ = 800 record and print `max|ΔS|` per class — a
>   *reading*, gated by nothing; it is the number `TH-14` step 3 brackets.
> * **Done-when (§4).** Steps 1–3 executed, the PEC-sphere closed form and
>   the two power identities asserted, cell counts and elapsed times
>   recorded, §2.1 gains a "conductor model" line stating exactly what is
>   gated (PEC interior bodies on three fixtures) and what is not (no loss,
>   no Q, no copper). No band moved.

**`TH-14` — surface-impedance (Leontovich) boundary on conductor
surfaces** ⬜ *(commissioned 2026-09-04 by operator directive, interactive
session; the second conductor-model route; **serial on `TH-15`** — same
hole mesh, same facet tags, one surface term added; `ANS-6` is serial on
it.)* **Formulation.** On the conductor-surface facets Γ_c the field
satisfies `n × E = Z_s n × (n × H)` with `Z_s = (1 + j)/(σδ)` (Jin §1.5.3,
(1.54)–(1.56); valid when δ ≪ the surface's radius of curvature, which copper
satisfies on every fixture here by 10³–10⁴). In the `E`-field curl-curl weak
form that is the third-kind boundary term of Jin §5.8.3,
`jωμ₀ ∫_Γc (1/Z_s)(n × E)·(n × W) dS`, i.e. exactly the shape of the
lumped-sheet term the `PORT-9` `extra_bilinear_terms` hook already carries
— the hook is the implementation route, with a `surface_impedance` material
attribute per facet tag. HFSS's counterpart is the *Finite Conductivity*
boundary with Solve Inside off, which is what `ANS-6` replicates.
> * **Step 1 (closed form, plane wave).** The `TH-6` lossy-half-space fixture
>   with the half-space replaced by an impedance surface at σ ∈ {1e4, 5.8e7}
>   S/m: reflection coefficient against the exact Fresnel `Γ = (η_c − η₀)/(η_c
>   + η₀)`; the Leontovich error is O(δ/λ), so pre-state **≤ 1e-3** on `|Γ|`
>   and `arg Γ` at 5.8e7 and record the 1e4 rung as the approximation's own
>   scale. Negative control: `Z_s = 0` (PEC) must give `|Γ| = 1` and miss the
>   phase by the recorded amount. Smoke/standard tier.
>   **Annotation, 2026-09-06 10:30 review — step 1 as written cannot state
>   a separating anchor, and is not queued until the weekly rewrites it.**
>   At 10 MHz and σ = 5.8e7 S/m, `η_c/η₀ = (1 + j)·√(ωε₀/(2σ))` ≈
>   2.2e-6, so the Fresnel Γ differs from the PEC's −1 by ≈ 4e-6 in
>   modulus and phase — the "≤ 1e-3" band cannot tell the copper rung from
>   the `Z_s = 0` control, and the control as written ("miss the phase by
>   the recorded amount") is a 4e-6 miss no FEM band resolves. The
>   1e4 S/m rung is the same to 1e-4. Two facts the rewrite can use: (a)
>   for a plane wave at normal incidence on a *flat* surface the impedance
>   condition `n × E = η_c n × (n × H)` is exact at any σ (the half-space
>   wave impedance is η_c exactly), so the gate rung can sit where the
>   effect is first-order visible — at σ = 1 S/m, `σ/(ωε₀)` ≈ 1.8e3 keeps
>   the good-conductor form valid, `|η_c/η₀|` ≈ 0.024 and `|Γ|` ≈ 0.967,
>   arg Γ ≈ π − 0.034: a 3.3% effect against a 1e-3 band, 33× separation
>   from the `Z_s = 0` control, with the copper rung printed as the
>   PEC-limit reading; (b) the `TH-6` fixture pins the exact total field on
>   every wall by Dirichlet data, which makes any Γ comparison circular —
>   the rewrite needs a non-circular drive (an impressed current sheet or
>   a Dirichlet wall that carries the incident field only) and that design
>   is the weekly's, not an implementer's. The sphere-with-`Z_s` idea the
>   18:00 review recorded has the same defect at copper (the E-driven β
>   moves at O(δ/a) ≈ 1e-4).
> * **Step 2 (closed form, coil loading — the copper Dodd–Deeds).** `MAT-6`'s
>   loop-over-slab fixture with the slab as an impedance surface at **σ =
>   5.8e7** and the loop itself still solved inside at its gated σ: ΔR and ΔX
>   against Dodd–Deeds (the closed form is valid at any σ), pre-stated band
>   **2%** (the `MAT-6` record is 1.58% at 100 S/m on a resolved volume; the
>   surface route has no resolution term, so if it misses by more the miss is
>   the formulation). Standard tier; the `ANS-1` slab geometry, so it is also
>   an AED-checkable point.
> * **Step 3 (the copper birdcage, heavy).** `TH-15` step 3's hole mesh with
>   `Z_s` for copper on the coil surface, phantom present: `PORT-9`/`PORT-11`
>   gates at 10 / 64 / 128 MHz (bands imported), the power identity
>   **`Re P_in = ½∫_phantom σ|E|² + ½∫_Γc Re(Z_s)|H_t|² ≤ 1e-3`**, and the
>   **bracket**: the copper 4×4 must lie between the σ = 800 record and the
>   `TH-15` PEC 4×4 class by class, and the σ ladder {5.8e7, 5.8e9, 5.8e11}
>   must converge onto the PEC matrix monotonically — the consistency
>   identity between the two routes, and the reason `TH-15` goes first.
>   Print the coil-loss share `P_coil/P_in` at each frequency beside the
>   σ = 800 fixture's; that pair of numbers is the whole point of the
>   directive.
> * **Done-when (§4).** Steps 1–3 executed, Fresnel and Dodd–Deeds asserted,
>   the power identity and the two-route bracket asserted, elapsed times
>   recorded, §2.1's conductor-model line updated to "copper via Leontovich,
>   gated on a plane wave, a Dodd–Deeds slab and the F-small birdcage's
>   identities". Still no absolute S claim on the copper coil — that is
>   `ANS-6`.


**`TH-5` — absorbing boundary condition (HFSS *Radiation*)** ⬜ *(**feature
ladder B1**, operator directive 2026-09-04, §9 item 5; the first Tier-B item,
queued after the conductor lineage.)* **Why.** A shielded birdcage's shield
is its physical boundary and the PEC box is right; everything else —
unshielded coils, leads near the phantom surface, any SAR comparison against
an open-boundary HFSS model — is not, and `PORT-1` already had to carry a
named PEC-box systematic (`D∞ = +0.0169` at p = 1.657, effective-range
extrapolation). Jin ch. 9.
> * **Step 1.** First-order ABC `n × (∇ × E) + jk₀ n × (n × E) = 0` on the
>   outer box as a third `TimeHarmonicBoundaryCondition` mode — a surface
>   term of the `PORT-9` hook's shape, Jin §9.2. Gate (closed form): an
>   electric dipole in free space, `|E|` on a sphere of sampling points vs
>   the exact field, box at 0.5 λ and 1 λ; pre-state the band from Jin's
>   first-order-ABC reflection-coefficient curve at the box's incidence
>   angles, not from a wish.
> * **Step 2 (the systematic collapses, or does not).** The two-torus
>   mutual with the ABC box at `PORT-1`'s three paddings: the box term
>   `D∞` must fall below its own PEC-box magnitude by ≥ 5× — a
>   pre-registered identity between two boundary models on one fixture.
> * **Step 3 (optional, review's call).** PML only if step 1's band is
>   insufficient for the 64/128 MHz birdcage box (λ ≈ 2.3–4.7 m, so the
>   box is electrically small and a first-order ABC may already be enough).
> * **Done-when (§4).** Steps 1–2 executed and asserted; §2.1 gains the
>   boundary-model line.

**`TH-16` — symmetry planes** ⬜ *(**feature ladder B2**, operator directive
2026-09-04.)* Per-face boundary assignment on the outer box (PEC on some
faces, PMC on others — today the mode is global), a mesh generator that cuts
the birdcage fixture on `x = 0` / `y = 0`, and the port bookkeeping HFSS does
automatically (a port bisected by a symmetry plane carries half the
impedance and half the power). Gate: the **quarter birdcage reproduces the
full 4×4's three C4 classes to ≤ 1e-3** — an identity, no closed form
needed — at a measured cell count and memory ≤ ¼ + overhead. The lever
against the F-human 62 GiB wall (`GEO-25`); date it after `GEO-25` reports.

**`TH-17` — birdcage eigenmodes** ⬜ *(**feature ladder B3**, operator
directive 2026-09-04; serial on `TH-15` and `PORT-14`.)* The `TH-9`
eigensolver on `birdcage_port_domain` with the coil as a PEC hole and
`PORT-14`'s capacitor sheets in the ring gaps, phantom lossless first. Gate:
the N mode frequencies of the ladder network against the lumped-element
closed form (Phase 6's named first target; the ladder's `L`/`M` from the
`PORT-13` Z-matrix, its `C` from the sheets) to a pre-stated band the review
sizes from the closed form's own approximation. Lossy phantom (complex
eigenvalues, Q) is step 2 and is what `WF-5` measures.

**`TH-18` — layered impedance boundary** ⬜ *(**feature ladder B4**, operator
directive 2026-09-04; serial on `TH-14`.)* `Z_s` of a foil-on-substrate
stack from the transmission-line recursion; gate: normal-incidence
reflection from a thin copper foil on a dielectric slab vs the closed-form
stack. Last in Tier B; do not queue before B1–B3 have landed.

### MAT — Materials & phantoms (Phase 3)

| ID | Title | Status | Tier |
|---|---|---|---|
| `MAT-1` | Gelled saline presets (low/mid/high σ) | ⚠️ | smoke |
| `MAT-2` | Materials demonstrably affect solved fields | ✅ | standard |
| `MAT-3` | Debye/Cole-Cole dispersion models — **feature ladder C3** (operator directive 2026-09-04; matters once tissue-property maps replace the gel, Phase 7) | ⬜ | smoke |
| `MAT-4` | SAR computation `σ|E|²/(2ρ)` | ✅ *(step 4 closed 2026-09-06: the C95.3 mass-averaging operator on the **coil-driven** F-small field — 10 g C4 identity 0.3303 / 0.0756 / 0.0574 / 0.3132% at the imported unmoved 5% band, whole-phantom identity 1.58e-14, `23 passed` / 130 s at `-n 4`, `20260907T003548Z_MAT-4-step4.log`. **Scope: 10 g at fixed `h` on one fixture at 10 MHz; the 1 g column is a printed record at 6.8383% worst, verdict (b); no absolute SAR, no C95.3 compliance claim, no Larmor, no convergence claim**. Step 5, 2026-09-08: on the 0.0025 phantom rung the 10 g pairs re-assert at 0.0309–0.0644% and the 1 g pairs read **0.0957–0.1305%**, printed. **Step 5b ✅ 2026-09-08: 1 g and 10 g are both C4-gated on the 0.0025 rung** at the same imported unmoved 5% band, and the rung's mesh (199 920 / 58 866) is a version-tagged record at the 1% `CELL_COUNT_BAND`; `26 passed` / Status 0 / 313 s at `-n 4`, `20260908T200629Z_MAT-4-step5b.log`)* | standard *(step 4 heavy by ceiling, measured 130 s; step 5 251 s at `-n 4`)* |
| `MAT-5` | Temperature-dependent conductivity | ⬜ | smoke |
| `MAT-6` | Dodd–Deeds coil-over-lossy-half-space impedance | ✅ Closed: the Dodd–Deeds coil-over-half-space impedance is gated in the eddy-current regime, with step 11 scoped by the 2026-09-02 weekly review to promote the slab-refined fixture to production. The coil-at-Larmor case remains an extrapolation. *History: `docs/planning/chunks/MAT-6.md`.* | heavy |
| `MAT-8` | Finite-wire correction to the Dodd–Deeds closed form | ✅ Closed: the finite-wire correction to the Dodd–Deeds closed form is implemented and gated by its filament and perfect-conductor limits, smoke tier with no solve. *History: `docs/planning/chunks/MAT-8.md`.* | smoke |

> `MAT-1` is `⚠️` not because the preset table is wrong but because nothing
> consumes it.

**`MAT-4` — SAR computation** ✅ *(closed 2026-09-06 on step 4, extended by steps 5 / 5b on 2026-09-08; the step-4 / 5 / 5b plans, execution journals and audits are archived verbatim in `docs/planning/plan-archive.md`, entry «§7 MAT-4 full narrative — archived 2026-09-13 (weekly review)»; steps 1–3's plans and control-ceiling arithmetic were archived there earlier.)*
> * **Steps 1–3** ✅ (2026-08-03 / 04 / 07): mean SAR vs the lossy-sphere closed form `σ|3E₀/(ε_c+2)|²/(2ρ)` **3.42% / 3.54%** at h = R/10 under a 10% bound; the averaging operator exact at 1 g and 10 g on an imposed field (R = 0.03 m, kernel mass 0.0120% / 0.0044%), quadrature degree 16 required. Standing traps: `ufl.real` around any UFL comparison off the origin; density via `build_density_field`.
> * **Step 4** ✅ (2026-09-06, `20260907T003548Z_MAT-4-step4.log`, 23 passed, **132 s** at `-n 4`; audited PASS 2026-09-07 03:00): the C95.3 mass-averaging operator on the **coil-driven** F-small field at 10 MHz on the 120 499 / 2 746-cell fine-phantom rung — the four cyclic **10 g** C4 pairs **0.3303 / 0.0756 / 0.0574 / 0.3132%** against the imported, unmoved 5% band; whole-phantom ball identity **1.576517e-14** vs 1e-10 (mass 4.096723e-14, fine-rung power record 5.587038273e-08 W to 5.398570e-11); mis-paired 180° control 86.0132 / 85.9249 / 85.9671 / 85.9582%; 1 g pairs printed 6.8383 / 2.9297 / 0.4116 / 4.7159% (verdict (b), the ~10-cell ball). One `src/` change: `build_density_field` accepts `0.0` (regression `20260907T003812Z_MAT-4-step4-src-regression.log`, 6 passed).
> * **Step 5** ✅ (2026-09-08, `20260908T140457Z_MAT-4-step5.log` + rerun `20260908T141147Z_MAT-4-step5-rerun.log`, 18 passed, 251 / 245 s at `-n 4`; audited PASS 2026-09-08 10:30): the `GEO-27` rung (`phantom_resolution` 0.0025, **199 920 / 58 866** cells on both windows) — 10 g pairs 0.0309 / 0.0060 / 0.0394 / 0.0644%, ball identity 8.126833e-14; 1 g pairs **0.0957 / 0.1199 / 0.1305 / 0.1065%** printed under clause (A); 10 g peaks 6.178300937 / 6.176390316 / 6.176760066 / 6.174323671e-07 W/kg (−2.67 … −2.43% rung to rung), 1 g averages 5.515422939 / 5.510146420 / 5.516752827 / 5.509553429e-07 W/kg, phantom power +1.5005% — none a compliance figure.
> * **Step 5b** ✅ (2026-09-08, `20260908T200629Z_MAT-4-step5b.log`, 26 passed, **313 s** at `-n 4`; audited PASS 2026-09-09 03:00): the 1 g column **asserted** at the same unmoved 5% band (0.0957 / 0.1199 / 0.1305 / 0.1065%, factor 38 of headroom), ball identity 5.262457e-14, mis-paired 1 g control 87.0143 / 87.0546 / 87.0506 / 87.0592% printed (predicted ~85%); `ONE_GRAM_RUNG_CELL_RECORD = 199_920` and `ONE_GRAM_RUNG_PHANTOM_CELL_RECORD = 58_866` version-tagged (1\*) at the imported `CELL_COUNT_BAND` 1%, never at equality.
> * **Scope of the ✅, verbatim:** 1 g and 10 g mass-averaged SAR on the coil-driven field — C4 covariance identities at fixed `h` on F-small at 10 MHz; **no absolute SAR, no C95.3 compliance or limit claim, no homogeneity, no Larmor, no convergence rate** (two rungs of one quantity), no quadrature drive. **Live carry-forwards:** the absolute / compliance claim waits on `ANS-2`'s AED half; the owed example landed as `EX-53` (`mri:3`); `QUADRATURE_DEGREE` 16 is imported from the step-3 module.

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

**`MAT-6` — the step record, compressed** *(steps 1–10b; the 2026-08-16-form ten-bullet step record is archived verbatim in `docs/planning/plan-archive.md`, entry «§7 MAT-6 full narrative — archived 2026-09-13 (weekly review)», beside the full narratives and probes; the step-11 promotion is in `docs/planning/chunks/MAT-6.md`.)*
> * **Steps 1–3** ✅ (2026-07-31 / 08-04): Dodd–Deeds anchored on the perfect-conductor limit (two derivations to 0.0002%); gate at f = 10 MHz, σ = 100 S/m, W = 0.15, 138 619 cells — **ΔR +0.3276882 Ω vs +0.3225961 Ω, 1.58%** (< 5%), re-gated on the production projected drive at **1.5834%** (the projection a 5e-5 no-op on ΔR); ΔX ratio 0.8123 → 0.9200, sign + order only; null-tagging control 1.31e-08, σ-blind fails by 100%. Traps: `ufl.max_value` does not compile in the complex build; a killed run leaves a stale FFCx lock (`rm -rf ~/.cache/fenics`).
> * **Steps 4–5, 8–9** ✅ (08-05 → 08-12): the ΔX drive gap is finite-wire discretisation (collapses 215× under wire refinement; ΔR's wire term 1.5834% → 1.0562% at `resolution_wire` 0.001); the slab knob owns ΔR — `resolution_near` 0.005 → 0.0025 takes ΔR **1.5834% → 0.2829%** on 417 914 cells (promotion deferred until `ANS-1` was adjudicated; landed as step 11, 2026-09-06, 0.2747% on the 418 888-cell fixture); box truncation owns ΔX (0.9200 / 0.9849 / 0.9960 → r∞ = 1.0023 at recovered p = 3.045); ΔR is *not* box-converged at W = 0.25 (0.38 pp at W = 0.35, control refuted, band not widened); composed readings compose **signed ΔZ**, never percent errors.
> * **Steps 6, 7** 🚫 / ✅ (08-08, 08-11): the 697 401-cell combined fixture OOM'd at the then-16 G cap; the operator raised it to 64 G and the additivity reading landed — ΔX ratio **0.9835 vs 0.9843 predicted, −0.080 pp, ADDITIVE**; `-n 8` established on this family (2.08× over `-n 4`); headless sessions run harness commands foreground.
> * **Steps 10 / 10a / 10b** (08-12, 08-16): the 895 974-cell composed fixture overran ≥ 5.7× (one solve > ~1 700 s at `-n 8`); fill-in exonerated (1.693× flops vs 1.28× cells), memory pressure (MUMPS in-core 69 894 MB vs the 65 536 MiB cap) and load balancing the surviving suspects; 10b commissioned 2026-08-16 (weekly review) as one `-n 12` solve with `ICNTL(14)` raised under `timeout -k 30 1200`, done-when ≤ 2× the 257 s prediction. The overrun proved plain `timeout` does not stop `mpiexec` (hence `-k 30`) and wedged the container (recovery `up -d --force-recreate`); the factor stays resident after `solve()` (`time_harmonic.py:453`).

### POST — Post-processing & field extraction

| ID | Title | Status | Tier |
|---|---|---|---|
| `POST-1` | Interface-aware field extraction reliability | 🟡 *(adjudicated 2026-08-05, 18:00 review — mean semantics decided, extremum semantics is step 4)* | standard |
| `POST-2` | Energy/consistency diagnostics | ⚠️ | standard |
| `POST-3` | Replace vacuous consistency metrics | 🟡 | standard |
| `POST-4` | Centerline point evaluation is rank-count-dependent: attribute and fix the ownership tie-break in `evaluate_vector_field_parallel` | ✅ *(chunk closed 2026-08-12 — every step closed or dispositioned; note the title's premise was itself refuted, the tie-break was never the defect. Step 1 ✅ 2026-08-11 — ownership **refuted**, 0/120 multi-claims; locus is the Lagrange-P1 interpolation, 1.163e+04× separation. Step 2 🚫 skipped. Step 3 ✅ 2026-08-11 — the centerline samples the source fields: **23.5539% → 0.008613%**, a 2735× collapse; known-issues entry **retired**. Step 4 ✅ 2026-08-12 — the export-path P1 artifact is **bounded and attributed**: midpoint relative medians **51.17% / 52.47% / 20.18%** (`A`/`B`/`E`), vertex/midpoint separation **0.42–0.68×** so the step's vertex-localization hypothesis is **REFUTED**, and a DG1 target reproduces all three sources to round-off — 100% of it is the P1 continuity constraint. All four steps now closed or dispositioned)* | standard |
| `POST-5` | Real Poynting power balance: wrong-sign boundary flux on the time-harmonic smoke fixture + `poynting_power_balance` raises on scalar `sigma=0.0` (`OPS-17` … | ✅ Closed: `poynting_power_balance` no longer raises on scalar zero conductivity, and step 3 found the boundary leg sound against closed form, overturning step 2's verdict. *History: `docs/planning/chunks/POST-5.md`.* | standard |
| `POST-6` | Arbitrary multi-port drive superposition | ✅ 2026-09-13: the 32-port ccw quadrature drive on `PORT-13`'s 16-leg ring fixture, superposed through `superpose_drives` at 10 MHz, is C16-invariant — worst `|B₁⁺|` rotation spread 0.8102 %, mirror 0.6769 % (both ≤ the imported 5 %), exact power identity 3.961e-15 (`20260913T185043Z_POST-6-step3.log:11798–11800`), with step 1's four anchors and the 4-leg cw control by record green (`…185405Z_…:1913`). Re-scoped 2026-09-13 (weekly, `auditor` DEMOTE(scope) concurring) to close on step 3; the `WF-6`/`WF-7` re-pointing clause dropped; no homogeneity, absolute or Larmor claim. *History: `docs/planning/chunks/POST-6.md`.* | standard; step 3 heavy (191 s at `-n 8`) |

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


**`POST-6` — arbitrary multi-port drive superposition (HFSS *Edit
Sources*)** ⬜ *(**feature ladder A1** — the first item of the ladder,
operator directive 2026-09-04, §9 item 5; serial on nothing.)* **Why.**
Quadrature drive is the MRI excitation and every B₁⁺/SAR quantity in §1 step
3 is defined under it. `WF-6` step 2 built it once, for four ports at fixed
`e^{∓jkπ/2}`, inside a test module; `EX-39` shows it. Nothing package-level
takes *N* stored single-drive solves and a complex weight vector, which is
what a tuned 32-port drive (`PORT-15`) and any asymmetric drive need.
> * **Step 1.** `ports.superpose_drives(sweep_result, weights)` → the
>   combined `E` (and `B` via `post.magnetic_flux_density_from_e`), the
>   combined port voltages/currents, and the combined accepted power. Gates,
>   all identities: (i) the four-port quadrature weights reproduce `WF-6`
>   step 2's C4-invariance and mirror digits **verbatim** (imported, never
>   restated); (ii) linearity — the superposed port voltages equal the
>   weighted sums of the single-drive ones to 1e-12; (iii) power —
>   `P_acc = wᴴ(I − SᴴS)w` from the S-matrix equals the volume loss integral
>   of the superposed field to ≤ 1e-3 (the first drive-level power identity).
>   Standard tier on the 116 085-cell 4-leg mesh.
>   **Review 2026-09-05 (03:00), two rulings on the slot's disclosures.**
>   (a) **Ratified:** anchor (i)'s pre-registered rtol 1e-6 against
>   `STEP2_IDENTITY_RECORDS` was arithmetically unreachable — the records
>   are four-significant-digit literals (`0.9818e-2`), so even a
>   bit-identical re-run agrees with them only to ±5.1e-5 — and the
>   substituted pair (literals at the imported `CG1_RECORD_RTOL` = 1e-3,
>   package-vs-fixture path equality at 1e-12, measured 1.2e-15) is
>   strictly tighter on the quantity that carries the information. Not a
>   loosening; the 1e-6 was the queueing review's error. (b) **The
>   denominator hypothesis is arithmetic on the log, adopted as the
>   working diagnosis, not as a finding:** `WF-6` step 1's single-drive
>   accounting misses by 9.795751e-03 × 6.856240413e-03 W =
>   **6.716e-05 W absolute** (`20260831T033704Z_WF-6-step2.log:4684–4688`);
>   `supplied − sheets` is 5.154401e-04 W, so that same absolute gap is
>   **13.0%** of the single-drive accepted power, and the superposed drive
>   reads 3.511e-04 W absolute on 3.014e-03 W = 11.6% — the same fraction
>   within the cross-term share. Whether the S-derived `P_acc` *equals*
>   `supplied − sheets` per drive is the one thing not measured; that is
>   an identity of the power-wave definition at `z0 = Re Z_p` and is
>   step 1b's assertion.
> * **Step 1b (the denominator, measured in-run; queued 2026-09-05 03:00
>   review as §9 item 2).** In the existing module, for each single drive
>   k: `P_acc,k = ½|a_k|² (1 − Σ_i |S_ik|²)` from the assembled 4×4 beside
>   the fixture's `supplied − sheets` accounting, asserted equal at rtol
>   **1e-6** (the power-wave identity; both are already computed in the
>   module, `test_port_drive_superposition.py:248` and the `_power_waves`
>   route); then the single-drive form of identity (iii) `P_acc,k` vs
>   `½∫σ|E_k|²`, **printed** with its residual, and the ratio
>   (superposed residual) / (mean single-drive residual) printed. Gate:
>   the rtol 1e-6 identity only. **Disposition rule, pre-stated:** if it
>   holds and the four single-drive residuals read ≈ 13%, the drive-level
>   red is the fixture's ~1% accounting offset against a 13× smaller
>   denominator — the *next* review re-points `POWER_BALANCE_BAND`'s
>   drive-level use to `supplied` (or opens a chunk for the 1% offset
>   itself), and the test stays red until it does; if the identity fails,
>   the S-matrix's power-wave normalisation disagrees with the sheet
>   accounting — known-issues entry with both numbers, stop.
>   **Executed 2026-09-05, 06:00 implementer slot — the identity holds at
>   machine precision.** `tests/validation/test_port_drive_superposition.py`
>   only, three new tests on the existing `superposition_case` fixture, no
>   new solve; `20260905T110305Z_POST-6.log`, `1 failed, 21 passed … 102.66s`
>   (`:2034`), Elapsed **104 s** (`:2112`), heavy by ceiling
>   (`timeout -k 30 600`), `-n 2`, complex. The one failure is the
>   *deliberate* step-1 red `test_the_drive_level_power_identity_closes`,
>   untouched. **(1b-i) green:** `P_acc,k = ½|a_k|²(1 − Σ_i|S_ik|²)` equals
>   `supplied_k − Σ_i sheets_ik` to **1.683e-15 / 0.000e+00 / 1.679e-15 /
>   0.000e+00** for P1–P4 against the pre-registered 1e-6 (`:1924–1939`) —
>   the power-wave normalisation and the sheet accounting are one number, so
>   "the two accountings disagree" is excluded and the 11.6% is **not** a
>   normalisation story. **(1b-ii) green:** the superposed ccw `P_acc`
>   reproduces 3.014424803e-03 W at rtol 1e-9 — same solves, same path.
>   **Printed, not asserted:** the four `|P_acc,k − P_vol,k|/P_acc,k` read
>   **1.303004e-01 / 1.302723e-01 / 1.300031e-01 / 1.302052e-01**, mean
>   **1.301952e-01**, and the superposed 1.164806e-01 is **0.8947×** that
>   mean (`:1940`) — the four-port drive misses *slightly less* than its own
>   single drives, so the superposition adds nothing. **Negative control,
>   ceiling first:** deleting `S_kk` from drive k's column misses by
>   7.659732e-01 / 7.656687e-01 / 7.634896e-01 / 7.652279e-01, each equal to
>   the closed form `|S_kk|²/(1 − Σ_i|S_ik|²)` computed from the assembled
>   4×4 *before* the assertion, against a claimed floor of 1e-3 (1000× the
>   band); nothing above the computed value claimed. **The disposition rule
>   fires as written:** the identity held and the four residuals read ≈ 13%,
>   so the drive-level red is the fixture's ~1%-of-`supplied` accounting
>   offset read against a 13× smaller denominator. `POWER_BALANCE_BAND` was
>   **not** touched in-slot and the test stays red; the next review is the
>   actor. **What step 1b does not settle:** the ~6.7e-05 W absolute gap
>   common to every drive is still unexplained — it is 0.98% of supplied and
>   13.0% of accepted, and candidate (b) "a real un-accounted loss channel"
>   survives at that same absolute size. Known-issues entry carries both.
>   **Review 2026-09-05 10:30 — the disposition is held for the 2026-09-06
>   weekly, with a recommendation.** The 03:00 review listed this decision
>   for the weekly explicitly ("a decision the dailies cannot make") before
>   step 1b ran, and step 1b's result sharpens rather than removes the
>   reason: re-pointing the drive-level band at `supplied` makes the test a
>   restatement of `WF-6` step 1's single-drive gate (0.98% of supplied,
>   already green) and gates nothing about the *superposition*, whose own
>   contribution step 1b measured at 0.8947× the single-drive mean. The
>   recommendation this review records: **(a)** re-scope the drive-level
>   test to the relative identity the data actually supports — the
>   superposed residual against the mean single-drive residual, both
>   computed in-run, ratio asserted ≤ 1 + `CG1_RECORD_RTOL`-class slack
>   (measured 0.8947; a superposition that *adds* power error is what it
>   would catch); **(b)** the 6.7e-05 W absolute gap becomes its own chunk
>   with a mechanism list (sheet-loss vs volume-integral double count in
>   the gap cells; Poynting flux through the outer wall under the natural
>   BC; the `_loss_power_w` quadrature on DG0 σ) — `POST-5`'s
>   three-term identity is the instrument, and a fixed-`h` gap that is
>   0.98% of supplied on every drive is a systematic, not noise. The test
>   stays red and `POWER_BALANCE_BAND` stays 1e-2 until the weekly rules;
>   the known-issues entry leaves with that commit.
> * **Step 2.** The same on `PORT-13`'s 32-ring-port fixture with the
>   16-fold quadrature weights; the C16 invariance of `|B₁⁺|` is the gate.
> * **Done-when (§4).** Both steps asserted; `WF-6` step 3 and `WF-7` are
>   re-pointed to consume this entry point rather than their own sums.

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
| `PORT-9` | Lumped-element port boundary condition (the birdcage port model) | ✅ Closed 2026-08-25 by leg (d1′), as the note at the head of the history records; the two-torus class re-record that preceded it moved no band. *History: `docs/planning/chunks/PORT-9.md`.* | standard |
| `PORT-10` | The two `PORT-1` systematics: composition measured, not assumed | ✅ 2026-08-16 (cross-term **−0.0604 pp** inside the pre-stated ±0.5 pp) | heavy |
| `PORT-11` | Lumped-sheet ports on the gapped birdcage at 64 MHz (then 128): `PORT-9`'s three gates in the displacement-current regime | ✅ Closed: step 2's 4×4 at 64 MHz ran at standard tier after step 1's probe cleared the phantom resolution stop rule, and all three gates were green. *History: `docs/planning/chunks/PORT-11.md`.* | heavy (probe first; **step 2 measured and ran standard**) |
| `PORT-12` | The two-torus gap-route record drifts with rank width on an already-plumbed fixture: `tests/validation/test_port_lumped_two_torus.py` reads gap ratio 0.894141 … | ✅ Closed: step 1's gap-ratio record reproduces at both rank widths inside the unmoved band, and the 1e-8 assert was probed load-bearing. No band widened, no record rewritten, and no root-cause claim is made. *History: `docs/planning/chunks/PORT-12.md`.* | standard (complex, 84 s per width) |
| `PORT-13` | Phase-6 ring-rung solve probe | ✅ Closed: steps 1, 2 and 3 are all closed and the full 32×32 on the 32-ring-port high-pass layout is reciprocal / passive / C16 per step 3. A step 4 is a review's to scope. *History: `docs/planning/chunks/PORT-13.md`.* | heavy (probe first) |
| `PORT-14` | **Lumped RLC sheets** — HFSS *Lumped RLC* boundary: the `PORT-9` sheet law generalised from 50 Ω to `Z_p(ω) = R + jωL + 1/(jωC)`, so capacitors live in the model — **feature ladder A2** (operator directive 2026-09-04; serial on nothing) | 🟡 *(step 1 executed 2026-09-05, 21:00 slot — complex `Z_p` + `ports/circuit.py` land and solve; the reduction identity misses the pre-stated 1e-3 band at 1.596e-03 / 3.371e-03 / 7.250e-04 for C / L / R, band not widened, known-issues 🟡; 64 MHz is step 2. **Step 1b executed 2026-09-05, 09:00 slot: the residual is non-monotone in sheet resolution — 1.5956e-03/3.3705e-03 at ×1 (116 085 cells), 4.1880e-03/8.8755e-03 at ×0.75 (161 695), 1.4904e-03/3.1449e-03 at ×0.6 (209 604), reciprocity ≤ 2.4e-14 and σ_max ≤ 0.99999292 on both refined rungs — so the resolution hypothesis is refuted and `sheet_width_m` (the ×0.75 rung is the one whose four sheet widths break C4) is the step-1c suspect; band untouched. **Step 1c executed 2026-09-05, 21:30 slot on the fixed 116 085-cell gate mesh — reading (1): the width the law is told is the lever. Residual ×5.803881 / ×5.830276 at ε = +5%, ×3.748033 / ×3.724086 at −5%, ×5.634488 / ×5.679903 at alternating ±5.3% (C / L); all three perturbed 4×4s reciprocal to ≤ 1.891254889e-14 with σ_max ≤ 0.999997273, cells 116 085 bitwise, the Γ = 0 control asserted on all six terminations. Both directions *raise* the residual, so the zero-crossing lies inside ±5%: a three-point fit puts it at ε\* ≈ −0.0107 (C) / −0.0110 (L), common to the two elements, with fitted minimum ≈ 0. Step 1b's uniformity framing is superseded — configuration C is not distinguishable from A. Band untouched, the red gate test not re-run**)* | standard |
| `PORT-15` | The circuit layer | 🟡 Open: step 1's ladder-network closed form and termination reduction hold as pure-numpy identities, with nothing claimed about the FEM coil. Step 2 reads the inductances from `PORT-13`'s 32×32 and compares the resonances, plus gate (i) against `PORT-14`'s measured 3×3. *History: `docs/planning/chunks/PORT-15.md`.* | smoke (step 1, measured 4 s); standard for the field-side steps |
| `PORT-16` | The ~1 %-of-supplied accounting gap on the 4-leg fixture | ✅ Closed 2026-09-07: the exact discrete power identity closes on every single drive and on the superposed quadrature drive, and the accounting gap is attributed to the terminal form's Cauchy–Schwarz deficit. Step 3's gap h-rate is optional, unclaimed and the weekly's to commission. *History: `docs/planning/chunks/PORT-16.md`.* | standard (three windows ≤ 180 s at `-n 2`; the ×0.6 rung measured 136 s) |
| `PORT-17` | Wave ports / coax feeds — HFSS *Wave Port*; low priority: MRI coils are fed at lumped points through matching networks — **feature ladder C2** (operator directive 2026-09-04; commission only if a benchmark demands it) *(**renumbered from `PORT-16` by the 2026-09-09 03:00 daily review**, on the 02:15 weekly's finding 1: §7 carried two `PORT-16` rows, which breaks the stable-ID contract. The closed, audited, log-bearing chunk above keeps the ID; this unopened ladder entry moves. `PORT-17` was unused repo-wide. The §9 item-5 ladder table moved with it; no other file referenced this row)* | ⬜ | standard |
| `PORT-18` | Does the lumped-sheet port read its current off one side of a discontinuous component | 🧪 Measured 2026-09-10: the premise was false — the sheet normal is azimuthal — and the '+'-side mechanism is excluded for both the read-back and the source term. The printed lead is taken up by `GEO-32`; `ANS-4` step 2a and `WF-6` step 4f stay blocked. *History: `docs/planning/chunks/PORT-18.md`.* | standard (heavy by ceiling), `-n 2` + `-n 1`, no solve — **measured 154 s + 68 s** |
| `PORT-19` | Reuse the factorisation across the drives of one sweep | ✅ Closed: one factorisation per sweep instead of one per port, with `S`, `Z` and the kept fields matching per-drive solves inside their asserted bounds at both rank widths. Step 6 recorded the two remaining example callers green on the reuse-on default. *History: `docs/planning/chunks/PORT-19.md`.* | smoke (step 1), standard (step 2), heavy (step 3) |

**`PORT-16` (the accounting-gap row) — rulings, 2026-09-07 03:00 review: step 1 audited PASS; `POWER_BALANCE_BAND` ruled a record; step 2 rescoped; step 3 named.**
*Audit.* `auditor` PASS on all eight checks at `a2f8db0`: headers `fcfd101` = the closer's parent; 20 of 20 digits traced (`20260907T051231Z_PORT-16.log:1882–1893, 1895–1910, 1912–1915, 1917–1920, 1922–1924, 1997, 2065–2066`; window 1's sign signature `rel dev 2.000e+00` at `…050816Z:1882, 1885, 1888, 1891, 1917`); (i) and (iv) are executed asserts (`test_birdcage_power_identity.py::test_the_discrete_power_identity_closes_on_every_drive`, `::test_the_cauchy_schwarz_deficit_of_the_terminal_form_reproduces_the_gap`); `POWER_BALANCE_BAND` is imported nowhere in the module; `test_port_drive_superposition.py` is absent from the diff; no `src/`; 131 s inside standard. Re-traced by this review: `:1882` `rel dev 6.760e-15`; `:1917` `C - sheets_terminal 6.716202469e-05 W … rel dev 3.212e-13`. Both derivation repairs are ratified — the driven sheet's field-only form is not a theorem (its terminal current is driven by `E_t + E_src ĥ`), and a sign fixed in the test's own helper with the red window committed beside the green one is the MAG-10 / MAG-15 precedent. The control's 0.484102 outside the predicted [0.5, 2] window was printed, not asserted, exactly as rule (e) requires; the prediction was wrong by 3% and is not relied on anywhere.
*Ruling (1) — `POWER_BALANCE_BAND` is a record, not a conservation band.* The quantity it bounds, `|P_acc − P_vol|/P_acc` with `P_acc` built from terminal currents, is not an identity for the discrete solution: it misses by the terminal form's Cauchy–Schwarz deficit, now measured at 1.0106× the terminal sheet dissipation on every drive and reproduced to 1e-13. The three green single-drive asserts (`test_birdcage_b1_plus_map.py:432`, `test_port_birdcage_ring_matrix.py:273, 466`, `test_port_drive_superposition.py:682, 713`) **stay exactly as they are** — nothing green is touched — but are henceforth read as records of a ~1% fixed offset at fixed `h`; a future red on any of them is attributed through step 1's split before anyone re-bands it. The **drive-level** assertion (`test_port_drive_superposition.py::test_the_drive_level_power_identity_closes`, the deliberate red at 11.648%) was asserting a fixed absolute deficit against a 5× smaller denominator; it is re-pointed at the identity that *is* exact — step 2. This is not a loosened bound: the replacement asserts two identities at 1e-6 and 1e-1 (measured 1e-14 / 1e-13 class on the singles) on the same solve where the old line asserted a non-identity at 1e-2, and the old residual stays printed with the band beside it. The `POST-6` known-issues entry stays open until step 2's commit retires it. The 18:00 review had listed this ruling for the 09-09 weekly; step 1's attribution is decisive enough to act on now, and the weekly may overrule it with step 3 in hand.
*Ruling (2) — step 2 rescoped* (§9 item 2, full item there): the exact identity (i) at the imported `DISCRETE_IDENTITY_RTOL` and the attribution (ii) at the imported `ATTRIBUTION_RTOL` on the **superposed** ccw / cw drives in the module that holds the red, with `w = e_k` reproducing step 1's single-drive integrals to 1e-12 as the control of the generalisation; the row closes ✅ when it lands, and its example is `ports:9`'s power table — no new one. *Step 3 (named, not queued):* the `h`-exponent of `C/sheets_terminal − 1` on `PORT-14` step 1b's ×0.75 / ×0.6 conductor rungs — the only physics question left in this row, worth a slot only if the weekly wants the offset's `h`-dependence on record before ruling on the band's future.
*Audit of the closure (step 2), 2026-09-07 10:30 review — PASS on all eight checks at `7a82688`.* Header `2f65cbe` = the closer's parent (`20260907T110826Z_PORT-16.log:1–16`); 10 of 10 digits traced (`:1942–1943`, `:1945–1946`, `:1948–1951`, `:2038`, `:2106–2107`); the disposed red's baseline `20260905T004202Z_POST-6.log` sits on `2d8ce09`, a strict ancestor; the anchors are executed asserts (`test_port_drive_superposition.py:959`, `:974`) against bounds imported from step 1's module; `POWER_BALANCE_BAND` (`test_birdcage_b1_plus_map.py:101`, 1e-2) is absent from the commit's diff and its single-drive assert at `test_port_drive_superposition.py:895–896` is unedited; no `src/`, `test_birdcage_power_identity.py` untouched; 104 s inside standard. Re-traced by this review: `:1942` `rel dev 5.877e-15`, `:1945` `P_acc − P_vol 3.511221378e-04 W … C − sheets_terminal 3.511221378e-04 W`. The auditor's one caveat — the `timeout -k 30 400` wrapper exceeds the 180 s standard figure — is the step-1 precedent (tier by measured elapsed) and changes nothing. Step 3 stays the weekly's; not queued.

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


**`PORT-14` — lumped RLC sheets (HFSS *Lumped RLC*)** 🟡 *(step 1 executed
2026-09-05, 21:00 implementer slot — **the code lands, the gate does not
close.** `series_rlc_impedance` and a complex `Z_p` on the sheet, plus
`src/fem_em_solver/ports/circuit.py::reduce_terminated_ports`, are in and
solve; the 50 Ω baseline reproduces `PORT-9` on the run's own mesh
(`‖S−Sᵀ‖/‖S‖ = 1.464324816e-14`, `σ_max = 0.999992805`); the reduction
identity reads **1.595580e-03 (C = 100 pF), 3.370512e-03 (L = 1 µH),
7.249519e-04 (R = 200 Ω)** against the pre-stated **1e-3**, i.e. the lumped
sheet is single-mode to 3.4e-03, not 1e-3. Band **not** widened, per §9
item 2's negative-result protocol; known-issues 🟡, test deliberately red on
`main`. The ceiling-first Γ = 0 control passes with room (Δ = 0.322 / 0.325 /
0.211, misses 0.322 / 0.327 / 0.212 = 200–330× the band), so the gate is
resolving the termination. The residual **tracks |Γ|**, not the element type —
the hypothesis a step 1b would test is sheet/interior-width resolution, not
the complex arithmetic. `20260905T020428Z_PORT-14.log`, heavy tier by ceiling,
`-n 2`, 105 s, 13 solves on one 116 085-cell mesh.)* *(**feature ladder
A2**, operator directive 2026-09-04; serial on nothing; `TH-17` is serial on
it.)* The `PORT-9` sheet term carries `Z_p = 50 Ω`; let it carry
`Z_p(ω) = R + jωL + 1/(jωC)` per sheet, so a capacitor in a ring gap is a
boundary condition rather than a circuit afterthought. Gate (an algebraic
identity, no closed form needed): **the field-solved S-matrix with port *k*
terminated in `Z_p` equals the circuit reduction of the 50 Ω S-matrix by
that termination** (`S' = S_aa + S_ab Γ (I − S_bb Γ)⁻¹ S_ba`, Γ the
termination's reflection coefficient) to ≤ 1e-3 on the 4-leg fixture at 10
and 64 MHz, for a capacitor, an inductor and a resistor each. That is also
`PORT-15`'s gate seen from the field side, which is why the two are one
lineage. Standard tier.
> * **Step 1b (the |Γ| ordering, measured on resolution; scoped
>   2026-09-05 03:00 review, §9 item 4).** The slot's hypothesis — the
>   residual tracks |Γ| (1.6e-3 and 3.4e-3 at |Γ| = 1, 7.2e-4 at
>   |Γ| = 0.6), i.e. total reflection re-excites the sheet's non-single-mode
>   content — predicts that the residual falls with sheet resolution and
>   is indifferent to the element type. Measure it on the **L = 1 µH**
>   case (the worst) and the **C = 100 pF** case, on two refined rungs of
>   the same fixture: `conductor_resolution` × 0.75 and × 0.5 through an
>   additive `conductor_resolution=None` keyword on
>   `tests/mesh/test_birdcage_port_sheets.py::_build` (the `WF-6` step 3f₀
>   `phantom_resolution` precedent — `None` leaves every gate's mesh
>   bit-identical, and `test_port_birdcage_four_port.py` is re-run green
>   in the same slot as its gate). Per rung: the 50 Ω 4×4 (4 solves) with
>   the imported reciprocity / passivity asserts, then the two terminated
>   3×3s (6 solves), residuals **printed** beside the 116 085-cell record
>   with the cell count. **Pre-registered readings:** monotone decrease on
>   both cases is the hypothesis confirmed and step 2 (64 MHz) is queued
>   on the finer rung; flat or rising residuals refute it and the next
>   suspect is the sheet law's `sheet_width_m` (the area-based effective
>   width, `lumped.py:353`) — a `PORT-14` step 1c, not a band change.
>   `REDUCTION_BAND` stays 1e-3 either way; the row stays 🟡; nothing is
>   asserted on the residuals in this step. Heavy by ceiling.
> * **Step 1b executed 2026-09-05, 09:00 implementer slot — the hypothesis is
>   REFUTED, and the refutation names the next suspect.** Two refined rungs,
>   one window each, band untouched, row still 🟡. The residual is **not**
>   monotone in sheet resolution:
>
>   | `conductor_resolution` | cells | `sheet_width_m` per port | C = 100 pF | L = 1 µH |
>   |---|---|---|---|---|
>   | ×1 (step 1's record) | 116 085 | 7.294123600e-03 ×4 | 1.595580e-03 | 3.370512e-03 |
>   | ×0.75 | 161 695 | **6.884098695e-03 / 7.649794837e-03 alternating** | 4.187955e-03 (×2.6247) | 8.875487e-03 (×2.6333) |
>   | ×0.6 | 209 604 | 7.674817764e-03 ×4 | 1.490415e-03 (×0.9341) | 3.144877e-03 (×0.9331) |
>
>   (`20260905T140449Z_PORT-14-step1b-r075.log:1886–1888, 1892–1893, 1897–1898`,
>   Status 0, 149 s, `-n 2`; `20260905T140738Z_PORT-14-step1b-r060.log:1877–1879,
>   1885–1886, 1892–1893`, Status 0, 136 s, `-n 4` — licensed because the first
>   window came in under 300 s. Both heavy by ceiling; a `--collect-only`
>   import smoke first, `20260905T140432Z_PORT-14-step1b-smoke.log:76–77`,
>   Status 0, 5 s.) **Asserted and green on both rungs** (imported bands, none
>   moved): reciprocity `‖S−Sᵀ‖/‖S‖` = **2.392912949e-14** (×0.75) and
>   **1.574340894e-14** (×0.6) against 1e-3; `σ_max` = **0.999992054** and
>   **0.999992924** against 1 + 1e-9; cell count strictly above the record on
>   both; and the ceiling-first Γ = 0 control asserted on both terminations of
>   both rungs (Δ = 0.3202 / 0.3232 and 0.3217 / 0.3252, missing by 0.3204 /
>   0.3267 and 0.3218 / 0.3264 — 200–330× the band, as step 1). So each rung is
>   a valid 4×4 and its residual means something.
>   **Reading.** The residual rises 2.6× on the ×0.75 rung and falls 0.93× on
>   the finer ×0.6 rung — not monotone, so the slot's |Γ|-plus-resolution
>   hypothesis is refuted; and step 2 (64 MHz) is **not** queued on "the finer
>   rung" as the pre-registration would have had it. What the residual *does*
>   track is the pre-registered next suspect, `sheet_width_m` (`lumped.py:353`,
>   the area-based effective width off the **measured** extents): the ×0.75
>   rung is the only one whose four narrowed sheets do not share one width —
>   they alternate 6.884e-03 / 7.650e-03, a C4 break of ±5.3% — and it is the
>   only rung whose residual rises. The two elements move by the *same* factor
>   on each rung to 4 significant figures (2.6247 / 2.6333; 0.9341 / 0.9331),
>   i.e. the residual is a common geometric factor times a per-element
>   constant, not an element-type effect — which is the same conclusion step 1
>   drew from the |Γ| ordering, now with the geometry named.
>   **`PORT-14` step 1c is therefore the live branch:** the sheet law's
>   effective width, not mesh density. Note the C4 break is invisible to
>   `PORT-9`'s reciprocity/passivity/C4 gates — all three pass on the ×0.75
>   rung — so it is a defect only the reduction identity can see. Code from
>   this step is additive and gate-neutral: `conductor_resolution=None` on
>   `tests/mesh/test_birdcage_port_sheets.py::_build` and on
>   `build_four_port_sweep` (`None` ⇒ the module `CONDUCTOR_RESOLUTION`, every
>   gate's mesh bit-identical), and three rung tests in
>   `tests/validation/test_port_lumped_rlc_termination.py` that **skip** unless
>   `FEM_EM_PORT14_CONDUCTOR_RESOLUTION_FACTOR` is set, so the gate rung (and
>   its deliberately red gate test) is untouched and was not re-run here.
> * **Step 1c (the width law, measured on a fixed mesh; scoped 2026-09-05
>   10:30 review, §9 item 4).** Step 1b's table has one clean discriminator
>   in it: the ×0.75 rung is the only rung whose four `sheet_width_m` values
>   are not equal (6.884e-03 / 7.650e-03 alternating, ±5.3% about their
>   mean) and the only rung whose residual *rose*. Hold the **×1 mesh**
>   (116 085 cells, the gate rung — no new mesh) fixed and perturb the width
>   the sheet law is *told*, per port, through the `LumpedSheetPortSpec`
>   rebuild the module already does in `_terminated_three_port`
>   (`test_port_lumped_rlc_termination.py:101–125`): three configurations,
>   each a full 50 Ω 4×4 (4 solves) plus the L and C terminated 3×3s (6
>   solves) with the 4×4 reduced by the *nominal* Γ exactly as step 1 —
>   **(A) common +5%**, **(B) common −5%**, **(C) alternating ±5.3%**
>   (P1, P3 at +5.3%, P2, P4 at −5.3% — step 1b's ×0.75 rung reproduced on
>   the gate mesh). Baseline is step 1's record (1.595580e-03 / 3.370512e-03),
>   imported not re-run. **The pre-stated readings.** The sheet resistivity
>   is `Z_p · w/h` (`lumped.py:111`), so a *common* factor `(1+ε)` on `w`
>   scales every sheet's effective `Z` by `(1+ε)` while the reduction's Γ is
>   built from the nominal `Z_p/z0` ratio, which the common factor leaves
>   invariant; the field-solved S is referenced to the nominal `z0 = 50`
>   through `_power_waves`, which it does not. Hence: (1) if the residual
>   under (A)/(B) moves **linearly in ε and in opposite directions** with
>   a common zero-crossing `ε*` for C and L (both elements moved by the
>   same factor per rung in step 1b to 4 s.f., so the crossing must be
>   common), the width law is the lever and `(1+ε*)` is the correction
>   the area-based `A/h` is missing — a step 1d re-derives the effective
>   width (edge-based, or from the sheet's own 50 Ω self-consistency) and
>   then, and only then, re-runs the gate; (2) if (A)/(B) leave the
>   residual **flat** (< 10% change) while (C) moves it by the step 1b
>   factor (×2.6-class), the *uniformity* of the widths is what the
>   identity sees and the law's absolute value is exonerated — the suspect
>   becomes the sheet's non-single-mode content itself, which is a
>   resolution-of-the-*sheet* question the ×0.75 rung's C4 break masked,
>   and step 2 (64 MHz) waits on a sheet-refinement rung, not a conductor
>   one; (3) if none of (A)/(B)/(C) moves the residual by more than 10%,
>   `sheet_width_m` is exonerated entirely, the ×0.75 rise is a mesh
>   artefact, and the next suspect is the reduction's assumption that the
>   terminated sheet is the *same* port (same `I`, same `V` definition) the
>   50 Ω sweep measured — a `sheet_terminal_current` question. **Anchors
>   (asserted, all imported, none moved):** per configuration, reciprocity
>   ≤ `RECIPROCITY_BAND` and `σ_max ≤ 1 + PASSIVITY_SIGMA_TOLERANCE` on the
>   4×4 — a perturbed width must still give a valid passive reciprocal
>   network or its residual means nothing; cell count = the 116 085 record
>   (same mesh, bitwise). **Negative control, ceiling first:** the Γ = 0
>   control on each configuration as step 1 did (Δ from the 4×4 first,
>   assert ≥ 5× the band only where Δ ≥ 5e-3; step 1 measured 0.32 / 0.33).
>   **Printed, not asserted:** the six residuals, each beside the record
>   and as a factor of it; the per-port `sheet_width_m` actually passed.
>   **Tier / ranks / cost:** 30 solves on the gate mesh; step 1's 13 solves
>   ran 105 s at `-n 2` ⇒ ≈ 240 s, one window, `timeout -k 30 600`, `-n 2`
>   (this is a fixed-mesh measurement, so `-n 4` is licensed if the first
>   configuration passes 100 s — split into two windows rather than
>   overrun). **Traps:** step 1's list; the width goes into the spec and
>   *only* the spec — the mesh, the facet tags and the measured extents are
>   untouched, so print the widths passed per port and per configuration;
>   the gate rung's red test is not re-run here; `abs`/`.real` before any
>   comparison; `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first,
>   pytest `-s`; the new tests **skip** unless `FEM_EM_PORT14_WIDTH_SWEEP`
>   is set, so `main`'s red set does not change. **Scope:** a measurement
>   on the gate mesh at 10 MHz; `REDUCTION_BAND` stays 1e-3, the row stays
>   🟡, no record moves, no §2 change, no `src/` change. **Negative result:**
>   reading (3) is itself the finding — §7 annotation naming the
>   `sheet_terminal_current` suspect, stop; a configuration whose 4×4 fails
>   reciprocity/passivity is a fixture finding (known-issues with its
>   widths, stop).
> * **Step 1c executed 2026-09-05, 21:30 implementer slot — the data select
>   pre-registered reading (1): `sheet_width_m` IS the lever, and the
>   zero-crossing is common to both elements.** One window, one mesh, band
>   untouched, row still 🟡, no record moved, no `src/` change.
>   `20260905T213322Z_PORT-14-step1c.log`, heavy tier by ceiling
>   (`timeout -k 30 570`), `-n 2`, complex build, **`9 passed, 6 deselected
>   in 230.46s`, Status 0, 258 s** (`:2132`, `:2138–2139`) — 34 solves on the
>   one 116 085-cell gate mesh (baseline 4×4 + 3 × (4 + 3 + 3)); a
>   `--collect-only` import smoke first, `20260905T213309Z_PORT-14-step1c-smoke.log:55`
>   (`9/15 tests collected (6 deselected)`), Status 0, 4 s.
>
>   The baseline rung reproduces step 1b's ×1 row exactly: **116 085 cells**,
>   `sheet_width_m` = **7.294123600e-03 m ×4** (`:1924`). Per configuration,
>   the residuals **printed, not asserted**, beside step 1's record:
>
>   | config | ε per port (P1…P4) | widths told (m) | C = 100 pF | L = 1 µH |
>   |---|---|---|---|---|
>   | — (step 1's record) | 0 | 7.294123600e-03 ×4 | 1.595580e-03 | 3.370512e-03 |
>   | **A** common +5% | +.05 ×4 | 7.658829780e-03 ×4 | **9.260556e-03 (×5.803881)** | **1.965102e-02 (×5.830276)** |
>   | **B** common −5% | −.05 ×4 | 6.929417420e-03 ×4 | **5.980286e-03 (×3.748033)** | **1.255208e-02 (×3.724086)** |
>   | **C** alt. ±5.3% | +.053/−.053/+.053/−.053 | 7.680712151e-03 / 6.907535049e-03 alternating | **8.990276e-03 (×5.634488)** | **1.914418e-02 (×5.679903)** |
>
>   (`:1976–1981, 1985–1986` (A); `:2045–2050, 2054–2055` (B);
>   `:2114–2119, 2123–2124` (C).)
>   **Asserted and green on all three** (imported bands, none moved, all nine
>   tests pass): cell count **116 085 bitwise** on every configuration — the
>   perturbation enters the `LumpedSheetPortSpec` and nothing else, through
>   `build_four_port_sweep`'s existing `reuse` route with `sheets[k]["w"]`
>   scaled; reciprocity `‖S−Sᵀ‖/‖S‖` = **1.891254889e-14 / 4.829117353e-15 /
>   7.780907717e-15** against 1e-3; `σ_max` = **0.999988336 / 0.999997273 /
>   0.999996814** against 1 + 1e-9 — so each perturbed 4×4 is a valid passive
>   reciprocal network and its residual means something. The ceiling-first
>   Γ = 0 control is asserted on all six terminations (Δ = 0.3254 / 0.3281,
>   0.3177 / 0.3221, 0.3060 / 0.3081, all above the 5e-3 floor; misses 0.3259 /
>   0.3361, 0.3175 / 0.3173, 0.3064 / 0.3157 — 200–330× the band, as step 1)
>   (`:1990–1991`, `:2059–2060`, `:2128–2129`).
>
>   **Reading — outcome (1), with one qualification.** (A) and (B) both move
>   the residual by far more than the 10% the pre-registration set as "flat":
>   ×5.80 and ×3.75. So outcomes (2) and (3) are excluded and `sheet_width_m`
>   is **not** exonerated: the width the law is told is the lever, on a mesh
>   that did not move by a single cell. The qualification is that the two
>   directions do **not** move the residual in opposite directions — both
>   *raise* it — so the zero-crossing lies **inside** ±5%, not outside it, and
>   the nominal `A/h` is already near the optimum rather than off by a
>   discoverable factor. Post-hoc arithmetic on the three printed residuals
>   (*a three-point fit done by hand on the log's numbers, not a measurement,
>   and nothing in code depends on it*): modelling the residual as
>   `|r₀ + kε|` and solving for the vertex of `r²(ε)` gives
>   **ε\* = −0.01074 (C = 100 pF)** and **ε\* = −0.01097 (L = 1 µH)** with a
>   fitted minimum of **zero to within the fit's own error** (both `r²(ε*)`
>   come out marginally negative, −1.4e-07 and −1.2e-06 in `r²`). That is
>   exactly the pre-registered signature of reading (1): a **common**
>   zero-crossing for the two elements — the two agree to 2% of each other —
>   at an effective width ≈ **1.1% below** the area-based `A/h`, and the
>   sensitivity `|k|` is 0.153 (C) / 0.323 (L) per unit ε, i.e. a 1% width
>   error alone produces a residual of order the whole 1.6e-03 / 3.4e-03 miss.
>   As in step 1b, the two elements move by the **same factor** on each
>   configuration to 3 s.f. (5.804 / 5.830; 3.748 / 3.724; 5.634 / 5.680) — a
>   common geometric factor times a per-element constant, not an element-type
>   effect.
>
>   **Step 1b's "uniformity" framing is superseded by this.** Configuration
>   (C) — the ×0.75 rung's C4 break reproduced on the gate mesh, mean width
>   nominal — is **not** distinguishable from the common +5% configuration (A)
>   at the 3% level (5.634 / 5.680 vs 5.804 / 5.830), so the *uniformity* of
>   the four widths is not what the identity sees; the ×0.75 rung's ×2.6 rise
>   is the width **magnitude** effect, as its ∓5.6% / +4.9% departures from
>   nominal predict. Consistent with the terminated port P1's own width
>   dominating the sensitivity (it is the port whose sheet law and whose Γ
>   both enter the reduction), though these three configurations do not
>   separate the four ports and no per-port claim is made here.
>
>   **Not claimed.** `REDUCTION_BAND` stays **1e-3** and is not widened; the
>   gate test stays deliberately red on `main` and **was not re-run in this
>   slot** (`-k width_sweep`, 6 deselected); the row stays 🟡; no §2 change; no
>   `src/` change; 10 MHz only. The ε\* arithmetic above is a reading of three
>   points, not a re-derived width law — what would license a step 1d is a
>   review's call, not this slot's.
>   Code is additive and gate-neutral: `tests/validation/test_port_lumped_rlc_termination.py`
>   gains `WIDTH_CONFIGURATIONS`, a `width_sweep_baseline` fixture, a
>   parametrised `width_sweep_case` fixture and three tests, all of which
>   **skip** unless `FEM_EM_PORT14_WIDTH_SWEEP` is set.
> * **Step 1d (the origin of ε\*, measured; scoped 2026-09-05 18:00 review
>   under step 1c's own pre-registration — "linear with a common
>   zero-crossing ⇒ the `A/h` law needs a correction" — and it tunes
>   nothing).** Step 1c's fit says the sheet law closes the reduction
>   identity if told a width **1.07–1.10% below** the area-based `A/h`,
>   one number common to C and L. Step 1d does two things on the fixed
>   116 085-cell gate mesh. **(a) Name a geometric origin.**
>   `build_four_port_sweep` already measures per sheet `area`, `h` (the
>   bounding-box extent along the drive, `h_bbox`), `w_bbox`,
>   `w = area/h`, `facets`, `out_of_plane`
>   (`tests/validation/test_port_birdcage_four_port.py:319–337`). Print,
>   per port: `w/w_bbox − 1` (the ragged-edge fraction step 2b measured at
>   14–15% on the *full* width), `area/(w_bbox·h) − 1`, the reduced *mean*
>   height `area/w_bbox` against `h_bbox`, and the gap length the
>   generator was told beside `h_bbox`. The law uses
>   `R = Z_p·w/h = Z_p·A/h_bbox²`, so a facet set whose mean terminal
>   separation is 0.5% under its bounding box already produces a 1%
>   impedance offset — to first order `Z_eff = Z_p·h_actual/h_bbox`, from
>   `I = (1/R)∫(E·ĥ)dS/h` with `E ≈ V/h_actual`. Each candidate ratio is a
>   **prediction of ε\***; the pre-registered comparison is
>   `|ε_geom − ε\*| ≤ 0.3·|ε\*|` (≈ 0.3 pp) for *one* candidate — none there
>   means the origin is not geometric. **(b) Test the fit on a fourth
>   point.** Carry step 1c's six residuals as constants
>   (`STEP1C_RESIDUALS`, the log's printed digits: C 1.595580e-03 /
>   9.260556e-03 / 5.980286e-03 and L 3.370512e-03 / 1.965102e-02 /
>   1.255208e-02 at ε = 0 / +0.05 / −0.05), recompute ε\* per element in
>   code from the `|r₀ + kε|` model (never typed in), then run the two
>   lossless terminated 3×3s once more through the existing `reuse` route
>   with every told width scaled by `(1 + ε\*)` (configuration **D**, 10
>   solves) and print the residuals beside step 1's record *and* beside
>   `REDUCTION_BAND`. The fit predicts ≈ 0; whether both land ≤ 1e-3 is
>   **printed, not asserted**, because the width was fitted to the
>   residual — asserting it would be circular. **Anchors (asserted,
>   imported, unmoved):** D's 4×4 reciprocity ≤ `RECIPROCITY_BAND`,
>   `σ_max ≤ 1 + PASSIVITY_SIGMA_TOLERANCE`, cells 116 085 bitwise.
>   **Negative control (asserted — backed by step 1 / 1c's measurement of
>   the same comparison on this mesh, Δ = 0.31–0.33):** Γ = 0 on D, Δ
>   from the 4×4 first, the miss asserted ≥ 5× the band only where
>   Δ ≥ 5e-3. **Pre-registered readings (constants in code, printed, none
>   asserted):** (1) D ≤ 1e-3 on both *and* one `ε_geom` within 0.3 pp of
>   ε\* ⇒ **step 1e**, review-scoped: the fixture — geometry belongs to
>   the fixture, `lumped.py:351–357` — supplies the law that geometric
>   quantity instead of `h_bbox`, the red gate is re-run, and a residual
>   ≤ 1e-3 on *unfitted* input is what closes step 1; (2) D ≤ 1e-3 but no
>   geometric candidate predicts ε\* ⇒ the offset is a field effect of the
>   sheet (edge fringing — the single-mode residual proper); the
>   known-issues entry records it and **no** constant enters the law —
>   re-registering the band on measured evidence is the weekly's call;
>   (3) D not ≤ 1e-3 ⇒ the linear model fails beyond three points — print
>   `r(ε\*)` and stop. **Tier / ranks / cost:** step 1c's 34 solves took
>   258 s at `-n 2` (`20260905T213322Z_PORT-14-step1c.log:2138`); (b) is
>   14 solves (baseline 4 + 10) ≈ 110 s and (a) is geometry on the built
>   mesh ⇒ heavy by ceiling, one window, `timeout -k 30 400`, `-n 2`,
>   complex build, `tests/environment` first, pytest `-s`, behind
>   `FEM_EM_PORT14_WIDTH_SWEEP` like 1c with `-k step1d` so 1c's nine tests
>   are deselected. **Traps already paid for:** 1c's list —
>   `sheets[k]["w"]` is the only thing `reuse` reads, perturb it and
>   nothing else; `abs`/`.real` before `<=`; the red gate test is not
>   re-run; a mean-height candidate needs the facet *vertices* gathered
>   across ranks, not one rank's bounding box. **Scope:** a measurement at
>   10 MHz; `REDUCTION_BAND` stays 1e-3, the row stays 🟡, no `src/`
>   change, no §2 change. **Negative result:** every reading is
>   pre-registered — record it in this entry and in the known-issues
>   disposition and stop; a D whose 4×4 fails reciprocity/passivity is a
>   fixture finding (known-issues with its widths, stop).
> * **Step 1d executed 2026-09-05, 19:30 implementer slot — the data select
>   pre-registered reading (2): the three-point fit holds on a fourth point,
>   and the origin of ε\* is *not* one of the measured geometric ratios.**
>   One window, one mesh, band untouched, row still 🟡, no record moved, no
>   `src/` change. `20260906T003627Z_PORT-14-step1d.log`, heavy tier by
>   ceiling (`timeout -k 30 400`), `-n 2`, complex build,
>   `FEM_EM_PORT14_WIDTH_SWEEP=1`, `-k step1d`: `tests/environment`
>   **`11 passed … 24.23s`** (`:116`) then **`4 passed, 15 deselected in
>   110.42s`, Status 0, 137 s** (`:2114`, `:2120–2121`) — 14 solves on the
>   one 116 085-cell gate mesh (baseline 4×4 + D's 4×4 + 2 × 3 terminated);
>   a `--collect-only` smoke first, `20260906T003614Z_PORT-14-step1d-smoke.log`
>   (`4/19 tests collected (15 deselected)`), Status 0, 4 s.
>
>   **(b) The fit on a fourth point.** ε\* is recomputed **in code** from
>   `STEP1C_RESIDUALS` (step 1c's six printed digits) by solving the exact
>   parabola through the three `(ε, r²)` points — never typed in:
>   **ε\* = −0.010735 (C = 100 pF)**, **−0.010970 (L = 1 µH)**, fitted minima
>   −1.375055e-07 / −1.178493e-06 in `r²`, mean **ε\* = −0.010852**
>   (`:2005–2007`). Configuration **D** — all four told widths
>   7.294123600e-03 → **7.214965819e-03 m**, ratio **0.989147732**
>   (`:2094–2098`) — through the same `reuse` route on the same mesh gives,
>   **printed not asserted** (the width was fitted *to* these residuals, so
>   asserting them would be circular):
>
>   | element | residual at ε\* | vs step 1's record | vs `REDUCTION_BAND` = 1e-3 |
>   |---|---|---|---|
>   | C = 100 pF | **5.756561e-05** | 1.595580e-03 → **×0.036078** | **0.057566×** the band |
>   | L = 1 µH | **1.196780e-04** | 3.370512e-03 → **×0.035507** | **0.119678×** the band |
>
>   (`:2103–2105`.) The linear model predicted ≈ 0 at a point 5% outside the
>   fitted interval's centre and the measurement lands 17× / 28× below the
>   record — **reading (3) is excluded**: `|r₀ + kε|` holds beyond step 1c's
>   three points. It does not go to zero (5.8e-05 / 1.2e-04 remain), which is
>   the residual the width constant cannot explain.
>
>   **(a) No geometric origin.** Every sheet is identical to nine digits
>   (26 facets, area 5.835298880e-05 m², `h_bbox` 8.000000000e-03 m,
>   `w = A/h` 7.294123600e-03 m, `w_bbox` 9.167340025e-03 m, mean height
>   `A/w_bbox` 6.365313018e-03 m, out-of-plane 0.0) (`:2001–2004`, all from
>   `build_four_port_sweep`'s own comm-reduced `area`/`_sheet_extents`, so
>   nothing rank-local is read). Against the pre-registered window
>   **±0.003256** (0.3 × |ε\*|), the candidates read (`:2008–2040`, the same
>   on all four ports): `area/(w_bbox·h_bbox) − 1` = `w/w_bbox − 1` =
>   `h_mean/h_bbox − 1` = **−0.204336** (miss 0.193484; step 2b's ragged edge,
>   here 20.4% on the narrowed sheet), its inverse **+0.256812** (miss
>   0.267664), `h_bbox/port_box_z_told − 1` = **−0.200000** / **+0.250000**,
>   and the told gap length **matched exactly** — `h_bbox` = the generator's
>   `leg_gap_length` = 8.000000000e-03 m to nine digits, ε_geom = **+0.000000**,
>   miss **0.010852**. Nearest candidate 0.010852 = 3.3× the window. So the
>   1.09% is **not** a mis-measured terminal separation and not the ragged
>   edge: **reading (2)** — a field effect of the sheet (edge fringing, the
>   single-mode residual proper). Per the pre-registration **no constant
>   enters the law**, there is no step 1e, and re-registering the band on this
>   evidence is the weekly's call.
>
>   **Asserted and green** (imported bands, none moved): cells **116 085
>   bitwise**, reciprocity **9.998294990e-15** vs 1e-3, `σ_max` =
>   **0.999993774** vs 1 + 1e-9 (`:2099`) — D is a valid passive reciprocal
>   four-port, so its residual means something. The ceiling-first Γ = 0
>   control is asserted on both terminations: Δ = **0.321025 / 0.324791**
>   (above the 5e-3 floor), miss **0.321023 / 0.324743** = 321× / 325× the
>   band (`:2110–2111`) — the same 0.31–0.33 step 1 and 1c measured.
>
>   **Not claimed.** `REDUCTION_BAND` stays **1e-3**; the gate test stays
>   deliberately red on `main` and **was not re-run** (15 deselected); the row
>   stays 🟡; no §2 change; no `src/` change; 10 MHz only. D's residual is a
>   **fitted** number and closes nothing — what would close step 1 is a
>   residual ≤ 1e-3 on *unfitted* input. Code is additive and gate-neutral:
>   `tests/validation/test_port_lumped_rlc_termination.py` gains
>   `STEP1C_RESIDUALS`, `_epsilon_star`, `_geometric_candidates`, three
>   fixtures and four `step1d` tests, all skipping unless
>   `FEM_EM_PORT14_WIDTH_SWEEP` is set.
> * **Step 1e executed 2026-09-11, 07:30 implementer slot — F-small's
>   single-mode floor registered as a (1\*) record; the deliberate red
>   retires.** The 2026-09-06 weekly ruling (§10 Phase 6), tests only, no
>   `src/`. `REDUCTION_BAND` = 1e-3 keeps its value and comment and is **not**
>   re-registered. `tests/validation/test_port_lumped_rlc_termination.py`
>   gains `REDUCTION_FLOOR_F_SMALL` (C 1.595580e-03 / L 3.370512e-03 / R
>   7.249519e-04, cited to `20260905T020428Z_PORT-14.log:1858, 1865, 1872`),
>   `REDUCTION_FLOOR_RTOL` = 1e-3 and `RECORD_RANK_WIDTH` = 2. On the `OPS-41`
>   precedent the record assertion skips off `-n 2`, after the readings are
>   printed. The gate now asserts `|r/record − 1| ≤ 1e-3` per element and
>   prints each residual against the band as "systematic, not gated".
>   `STEP1_RESIDUAL_RECORD` takes its C/L entries from the new dict; R stays
>   out so `STEP1B_TERMINATIONS` is unchanged. `c4_congruent_sheets` off; the
>   `GEO-19` record mesh.
>   `20260911T123334Z_PORT-14-step1e.log`, standard tier (`timeout -k 30 300`),
>   `-n 2`, complex build, `-s`, no step 1b/1c/1d env var set:
>   **`15 passed, 16 skipped … 110.80s`** (`:2050`), **Status 0, 113 s**
>   (`:2118–2119`). Collect-only smoke first,
>   `20260911T123311Z_PORT-14-step1e-smoke.log` (31 collected `:81`, Status 0,
>   4 s).
>
>   | element | residual | record | ratio | `|ratio − 1|` | vs band (printed) |
>   |---|---|---|---|---|---|
>   | C = 100 pF | 1.595580e-03 | 1.595580e-03 | 0.999999762 | **2.380e-07** | 1.595580× |
>   | L = 1 µH | 3.370512e-03 | 3.370512e-03 | 1.000000106 | **1.065e-07** | 3.370512× |
>   | R = 200 Ω | 7.249519e-04 | 7.249519e-04 | 0.999999966 | **3.391e-08** | 0.724952× |
>
>   (`:1888, :1895, :1902`.) Every record reproduces ≥ 4 000× inside the rtol.
>   **Negative control (asserted, backed by the step 1 log):** held against
>   another element's record, each residual fails reproduction.
>   `|r_C/rec_L − 1|` = **0.526606** (pre-registered 0.527), and
>   `|r_R/rec_C − 1|` = **0.545650** (pre-registered 0.546) (`:1913, :1917`).
>   Every off-diagonal pair is asserted > 100× the rtol, so a swapped or
>   mis-keyed record cannot pass.
>   **Unmoved anchors, green:**
>   - 50 Ω baseline: reciprocity 1.044255156e-14 vs 1e-3, σ_max 0.999992805
>     vs 1 + 1e-9 (`:1884`; step 1 read 1.464e-14, the 1-ULP class).
>   - Γ = 0 control: Δ = 0.3218888 / 0.3254627 / 0.2112830, miss
>     0.3219520 / 0.3267853 / 0.2120063 (`:1922–1924`), step 1's digits
>     exactly.
>
>   **Not claimed:** no absolute-accuracy or single-mode-accuracy claim. The
>   residual *is* the sheet's named systematic (edge fringing, step 1d
>   reading (2)) on F-small at 10 MHz. `TH-17` may not gate a mode frequency
>   tighter than it without saying so. The row stays 🟡: step 2 (64 MHz) is
>   open and now unblocked. Known-issues 2026-09-05 `PORT-14` step 1 entry
>   retired in the same commit.
>
> **Step 2 executed 2026-09-11 (13:30 slot) — negative result: at 64 MHz the
> capacitor's residual is above the item's 1e-2 stop line.** Env
> `FEM_EM_PORT14_STEP2_64MHZ=1` drives the same fixture, sweep and
> terminations at 64 MHz on the 116 085-cell record mesh (`c4_congruent_sheets`
> off). The 10 MHz record tests print their readings and then skip. The default
> path is unchanged. Anchor `20260911T183201Z_PORT-14-step2.log`, `-n 2`, standard:
> 13 passed, 18 skipped in 113.60 s (`:2053`), Status 0, Elapsed 115 s (`:2122`).
>
> | Element | Z_p at 64 MHz | Γ | residual | × 10 MHz record | × band |
> |---|---|---|---|---|---|
> | C = 100 pF | −j24.86796 Ω | −0.603378−0.797455j | **1.354202e-02** | 8.487 | 13.54 |
> | L = 1 µH | +j402.1239 Ω | +0.969550+0.244893j | 5.021261e-04 | 0.149 | 0.50 |
> | R = 200 Ω | 200 Ω | +0.600000 | 7.445387e-04 | 1.027 | 0.74 |
>
> (`:1882–1884, :1891, :1898, :1905`.)
> - **Anchors (asserted, imported, unmoved), green.** 50 Ω reciprocity
>   9.950176195e-16 against 1e-3, σ_max 0.999721388 against 1 + 1e-9 (`:1885`).
>   Γ = 0 control asserted on all three: Δ = 0.4806 / 0.2390 / 0.1829, miss
>   0.4940 / 0.2393 / 0.1836 (`:1924–1926`). The identity is resolved and no
>   coupling skip fired.
> - **Proof the sweep was rebuilt.** S₁₁ is +4.488964206e-02+5.803022759e-01j
>   against 10 MHz −3.712480826e-01+1.417750480e-01j, and S₂₁ moved by 1.915e-01
>   (`:1886–1887`). The `reuse=` route is mesh-only and the problem is rebuilt at
>   `frequency_hz`.
> - **Routes.** The 50 Ω 4×4 rides `PORT-19`'s reuse-on default; the terminated
>   3×3s go through `run_lumped_sheet_port_case` directly.
> - **Default-path control.** `20260911T183421Z_PORT-14-step2-default.log`
>   (flag unset): 15 passed, 16 skipped, Status 0, 111 s. The 10 MHz records
>   reproduce to |ratio − 1| = 2.380e-07 / 1.065e-07 / 3.391e-08
>   (`:1888, :1895, :1903`).
>
> **Reading.** L and R stay under the 1e-3 band; C does not, and it is above
> 1e-2. Both C and L have |Γ| = 1, yet C rose ×8.5 while L fell ×0.15, so
> 10 MHz's ordering does not carry over. Per the item's negative-result clause
> the three residuals are recorded here and the step stopped.
>
> **Not changed.** No 64 MHz record is registered, no band moves, and `PORT-15`
> gate (i) is not opened. `PORT-15` gate (i) and `TH-17` must not assume a 64 MHz
> floor ≤ 1e-2 for a capacitive termination. The row stays 🟡.
>
> **Hypothesis for the next step (unqueued).** The residual may follow the
> terminated sheet's current. −j24.9 Ω may partly cancel the leg reactance and
> re-excite the sheet's fringing content. The next step would print |I_P1| per
> element and cond(I − S_bb Γ) at 10 and 64 MHz from the solves the module
> already returns.
>
> **Ruled and scoped 2026-09-11 18:00 review — steps 2b and 2c (§9 items 2
> and 5), both measure-only.** The review's arithmetic on step 2's printed
> 64 MHz S₁₁ (`:1886`) gives `|D| = |1 − S₁₁Γ|` = 0.6837 / 1.2393 / 1.0335 for
> C / L / R. So the reduction's first-order sensitivity to the terminated
> column, `|Γ|²/|D|²` = 2.1395 / 0.6511 / 0.3371, spreads C:L by only 3.3×
> against the measured 27× residual spread. *Predicted:* amplification through
> S₁₁ does not carry the C residual, and the slot's cond(I − S_bb Γ) reading
> alone would not discriminate. **Step 2b** therefore fits the termination the
> field solve actually realised. For one terminated port the reduction is
> `S′ − S_aa = t·M` with the rank-1 `M = S_a1 S_1a` and `t = Γ/(1 − S₁₁Γ)`.
> The least-squares `t` is a closed-form projection, `Γ_eff = t/(1 + S₁₁t)`,
> and `Z_eff = z0(1 + Γ_eff)/(1 − Γ_eff)`. Printed at 10 and 64 MHz per
> element: `ΔZ = Z_eff − Z_p`, `Z_eff/Z_p − 1`, and the non-rank-1 remainder.
> A **common ΔZ** across C/L/R that scales with ω would read as unmodelled
> series reactance. A **common Z_eff/Z_p − 1** would read as step 1c's
> proportional width law. **Step 2c** runs step 1c's width configurations at
> 64 MHz. Neither step registers a record or moves a band, and `PORT-15` gate
> (i) stays closed until a 64 MHz record exists.
>
> **Step 2b executed 2026-09-11 (21:00 slot). One realised termination carries
> the whole residual at both frequencies.** Tests only, no `src/` change:
> `_realised_termination` and `test_step2b_the_realised_termination_is_printed`
> were added, and the fixture now keeps `results`. Four windows, all `-n 2`,
> standard, `timeout -k 30 300`, each Status 0:
> - `20260912T020247Z_PORT-14-step2b.log` (64 MHz, 14 passed / 18 skipped,
>   122 s);
> - `20260912T020500Z_PORT-14-step2b-default.log` (10 MHz, 16 / 16, 118 s);
> - the same two re-run with one added post-hoc κ print:
>   `20260912T020824Z_PORT-14-step2b-w2.log` (116 s) and
>   `20260912T021021Z_PORT-14-step2b-default-w2.log` (118 s).
>
> The nominal residuals, `Z_eff` and `t` reproduced to every printed digit in the
> re-runs, and the remainders to ≤ 3e-6 relative. Readings (w2 logs, 64 MHz
> `:1927–1954`, 10 MHz `:1927–1955`):
>
> | Element | f | \|Z_eff/Z_p − 1\| | Re ΔZ (Ω) | Im ΔZ/ω (H) | remainder / nominal | κ_k = ΔZ/(Z_p − z0) | \|I_P1\|/\|I_drive\| (P2/P3/P4) |
> |---|---|---|---|---|---|---|---|
> | C | 10 MHz | 1.109475e-02 | −0.5294121 | −2.681e-08 | 2.2e-7 | 1.058471e-02 | 0.180 / 0.166 / 0.180 |
> | L | 10 MHz | 1.353422e-02 | −0.5292585 | +1.059e-08 | 2.3e-7 | 1.059024e-02 | 0.355 / 0.338 / 0.355 |
> | R | 10 MHz | 7.941857e-03 | +1.588371 | −1.543e-11 | 2.5e-7 | 1.058914e-02 | 0.120 / 0.112 / 0.120 |
> | C | 64 MHz | 2.374962e-02 | −0.5295059 | −6.506e-10 | 1.7e-6 | 1.057617e-02 | 0.811 / 0.727 / 0.811 |
> | L | 64 MHz | 1.073146e-02 | −0.5278062 | +1.065e-08 | 2.1e-6 | 1.064945e-02 | 0.084 / 0.064 / 0.084 |
> | R | 64 MHz | 7.940094e-03 | +1.588007 | −1.527e-11 | 2.1e-6 | 1.058671e-02 | 0.159 / 0.120 / 0.159 |
>
> The κ_k imaginary parts are ≤ 4.1e-05. Pooled post-hoc κ is
> 1.058709e-02 − 3.6e-06j at 10 MHz (per-element misfit ≤ 3.4e-4, `:1948–1951`)
> and 1.064081e-02 − 1.5e-05j at 64 MHz (misfit ≤ 6.2e-3, `:1947–1950`).
> - **Anchors (asserted), green in all four windows.**
>   - (a) Recovery from the exact (C2) reduction: ≤ 1.227e-15 against 1e-9.
>   - (b) The ×1.01 reduction: ≤ 7.856e-16 against 1e-6.
>   - (c) Reproduction of step 2's 64 MHz residuals: 2.827e-07 / 7.581e-08 /
>     4.728e-08 against rtol 1e-5. *Disclosed extension:* the same assertion
>     also runs at 10 MHz against `REDUCTION_FLOOR_F_SMALL` (2.380e-07 /
>     1.065e-07 / 3.391e-08). That is additive and backed by
>     `20260911T183421Z_PORT-14-step2-default.log:1888, :1895, :1903`.
> - **Negative control (asserted).** Held against the other frequency's reading,
>   every residual misses by ≥ 2 631× the rtol (R, 10 MHz) against the 100× bar.
> - **Pre-registered predictions (printed only).**
>   - Remainder ≪ nominal: **held**, ≤ 2.5e-6 of nominal everywhere, so no
>     error lives in the kept block.
>   - Common `Im ΔZ/ω` within 2×: **failed** at both frequencies (signs differ).
>     The unmodelled-series-inductance reading is refuted.
>   - Common `Z_eff/Z_p − 1` within 2×: **held at 10 MHz** (1.70×), **failed
>     at 64 MHz** (2.99×; C:L 2.21×).
> - **Observation, not asserted.** The six nominal residuals order exactly as
>   `|I_P1|/|I_drive|` does. C at 64 MHz carries 0.81 of the drive current and
>   the largest residual.
>
> **Reading: slot derivation, a hypothesis for the review.** The post-hoc fit
> `ΔZ = κ(Z_p − z0)` with a single real κ holds on all six readings. Suppose
> every sheet realises `(1+κ)·Z_told` while the port voltage is still reported
> as `V_src − I·Z_told`. Then the 50 Ω 4×4 is the network plus a series `κ·z0`
> at each port, and a terminated sheet presents `Z_p + κ(Z_p − z0)` to it. That
> is the printed form. So step 1c's proportional law, applied to *all four*
> sheets, would explain C's 64 MHz jump as the same κ reached through a larger
> sheet current, not a new mechanism. It would also explain why the literal
> `Z_eff/Z_p − 1` test is not common, since that quantity is `κ(1 − z0/Z_p)`.
> Three independent numbers agree to about three figures:
> - κ at 10 MHz, 1.0587e-2;
> - step 1c's −ε\* ≈ 1.07 / 1.10e-2;
> - `PORT-16`'s C/terminal − 1 = 1.0592e-2 on the same `build_four_port_sweep()`
>   fixture (`20260907T051231Z_PORT-16.log:1895–1910`).
>
> That points at the Cauchy–Schwarz sheet-field non-uniformity as κ's origin.
> This is unproven here.
>
> **§9 item 5 (step 2c).** Its literal skip condition fires: at 64 MHz C and
> L's `Z_eff/Z_p − 1` differ by 2.21× > 2×. But the reading above says that
> observable is the wrong test of the proportional law, so whether 2c is
> BLOCKED or re-pointed at κ is the review's ruling. **Not changed:** no
> record, no band, no `Z_p` correction; `PORT-15` gate (i) stays closed and the
> row stays 🟡.
>
> **Ruled 2026-09-12 03:00 review.** Step 2b accepted (re-read
> `…step2b-w2.log:1947–1951`, `…step2b-default-w2.log:1948–1951`). Step 2c is
> **re-pointed at κ, not BLOCKED**: `Z_eff/Z_p − 1` is `κ(1 − z0/Z_p)` under
> the proportional law, so the 18:00 skip condition tested the wrong
> observable. 2c now predicts ε\* = −κ_k at 64 MHz (§9 item 4). Step 2d (§9
> item 3) tests κ's origin: the `PORT-16` module driven at 64 MHz through the
> existing `frequency_hz` keyword prints C/terminal − 1 beside κ(64 MHz) =
> 1.0641e-2. If they agree as they do at 10 MHz (1.0592e-2 against 1.0587e-2),
> a single multiplicative correction on the told sheet impedance is the
> candidate route to a 64 MHz record for `PORT-15` gate (i) — the weekly's to
> scope, never an in-slot change.
>
> **Step 2d executed 2026-09-12 (07:30 slot). At 64 MHz, C/terminal − 1 reads
> κ(64) to −0.3 %.** Tests only, in the `PORT-16` module
> (`test_birdcage_power_identity.py`), additive: env `FEM_EM_PORT16_64MHZ`, and
> new `test_step2d_c_over_terminal_is_printed`. When the flag is on, (iv) prints
> and skips. Two windows, `-n 2`, standard, `timeout -k 30 300`, `rc=0`:
> - `20260912T123236Z_PORT-14-step2d-64mhz.log`: 16 passed / 1 skipped, 93 s;
> - `20260912T123429Z_PORT-14-step2d-10mhz.log`: 17 passed, 92 s.
>
> - **Anchors (asserted).**
>   - (i) closes at 64 MHz: 3.3e-15 to 7.0e-15 on P1–P4 and 4.3e-15 on the ×2
>     control, against 1e-6 (`…64mhz.log:1882–1891, :1922`). (ii) and (iii)
>     are green at 64 MHz.
>   - Flag off, C/terminal − 1 reproduces the 10 MHz readings to ≤ 1.45e-10
>     against rtol 1e-5 (`…10mhz.log:1938–1944`). The references are computed
>     from the ten-digit C and gap values at `20260907T051231Z_PORT-16.log:1917–1920`.
> - **Negative control (asserted).** S₁₁ at 64 MHz sits 6.045e-01 from
>   `STEP1E_S11_S21_10MHZ` (`…64mhz.log:1940`), so the sweep was rebuilt.
> - **Readings (printed, `…64mhz.log:1942–1949`).** C/terminal − 1 =
>   1.060762e-02 / 1.060916e-02 / 1.061032e-02 / 1.060766e-02 on P1–P4.
>   - Against pooled κ(64) = 1.064081e-02, that is 0.99688–0.99714×. The
>     predicted 5 % window holds; the 20 % negative-result bar is far away.
>   - The readings sit between κ_C (+0.30 %) and κ_L (−0.39 %).
>   - The per-sheet spread is 1.06040e-02 to 1.06123e-02.
> - **Frequency shift (printed).** From 10 to 64 MHz, C/terminal − 1 moves by
>   +0.15 % (1.059204e-02 → 1.060762e-02 on P1), while κ moves by +0.51 %
>   (1.058709e-02 → 1.064081e-02). The predicted sign held; the size is
>   ≈ 0.3× κ's. So κ − (C/terminal − 1) grows from ≈ 5e-6 at 10 MHz to
>   ≈ 3.3e-5 at 64 MHz.
> - **Other printed readings.** The ×2 control's sheet factor at 64 MHz is
>   0.349799, outside the predicted [0.5, 2]. That window is printed only.
>
> **Reading.** κ is the terminal form's Cauchy–Schwarz deficit to ≤ 0.5 % at
> both frequencies. A frequency-growing ≈ 0.3 % remainder is not in that
> deficit. **Not changed:** no record, no band, no `Z_p` correction. The row
> stays 🟡, `PORT-16` stays ✅, and `PORT-15` gate (i) stays closed. The
> multiplicative-correction route is the weekly's to scope; item 4 (step 2c's
> width lever at 64 MHz) is the independent read.
>
> **Step 2c (re-pointed) executed 2026-09-12 (09:00 slot). At 64 MHz the told
> width's zero-crossing reads −κ_k to +3.1 % (C) and −4.2 % (L).** Tests only,
> additive, in `test_port_lumped_rlc_termination.py`. `width_sweep_baseline` and
> `width_sweep_case` take `_rlc_frequency_hz()` for both
> `build_four_port_sweep` and `series_rlc_impedance` (flag unset ⇒
> `FREQUENCY_HZ`, bit-identical arithmetic); the step-1c print lines name the
> frequency; new `test_the_width_sweep_epsilon_star_fit_is_printed` fits
> through (0, step 2's ε = 0 residual), (+5 %, A), (−5 %, B) once all three
> configurations are in. One window:
> `20260912T140430Z_PORT-14-step2c.log`, `FEM_EM_PORT14_WIDTH_SWEEP=1
> FEM_EM_PORT14_STEP2_64MHZ=1`, `-n 2`, `-s`, `-k "width_sweep or
> environment"`, `timeout -k 30 590`, durable capture: **23 passed,
> 12 deselected in 183.45 s** (`:2163`), `[capture] rc=0` (`:2229`), Status 0,
> **185 s** (`:2232–2233`). Heavy by ceiling.
>
> - **Anchors (asserted, unmoved), green.** f = 6.400000e+07 Hz on every line
>   (`:1880, :1932, :2003, :2074`); 116 085 cells bitwise on A / B / C;
>   reciprocity 1.351536152e-15 / 2.238321049e-15 / 1.934662477e-15 against
>   1e-3; σ_max 0.999535567 / 0.999907252 / 0.999839277 against 1 + 1e-9
>   (`:1937, :2008, :2079`).
> - **Negative control (asserted).** Γ = 0 on all six terminations: Δ =
>   0.4671 / 0.2400, 0.4928 / 0.2377, 0.4516 / 0.2319; misses 0.5454 / 0.2416,
>   0.4431 / 0.2366, 0.5331 / 0.2335 — ≥ 234× the band against the 5× bar
>   (`:1946–1947, :2017–2018, :2088–2089`).
>
> | config | C = 100 pF residual (× ε = 0) | L = 1 µH residual (× ε = 0) |
> |---|---|---|
> | ε = 0 (step 2, `…step2.log:1891, :1898`) | 1.354202e-02 | 5.021261e-04 |
> | A common +5 % | 7.879573e-02 (×5.818610) | 2.862518e-03 (×5.700796) |
> | B common −5 % | 5.047888e-02 (×3.727574) | 1.895173e-03 (×3.774297) |
> | C alt. ±5.3 % | 8.205738e-02 (×6.059464) | 2.859601e-03 (×5.694986) |
>
> (`:1941–1942, :2012–2013, :2083–2084`.)
> - **Fit (printed, `:2093–2098`).** ε\*(C) = **−0.010908** (10 MHz −0.010735),
>   ε\*/(−κ_C) = **1.031340**; ε\*(L) = **−0.010199** (10 MHz −0.010970),
>   ε\*/(−κ_L) = **0.957693**.
> - **Predictions (printed only).** Within 10 % of −κ_k: **held** on both
>   (3.1 %, 4.2 %). C/L within 2 %: **failed**, ε\*(C)/ε\*(L) = 1.069490.
>   Both ±5 % directions raise L's residual: **held** (×5.70, ×3.77).
> - **Negative-result bars: none fires.** Off −κ_k by > 30 %: clear. C vs L by
>   > 2×: clear. All residuals within ±10 % of ε = 0: clear (factors 3.7–6.1).
> - **Observation, not asserted.** C's parabola dips below zero,
>   r²(ε\*) = −1.626e-05 against r₀² = 1.834e-04 (≈ 9 %; at 10 MHz it was
>   −1.4e-07). So C's three 64 MHz points are not exactly `|r₀ + kε|`. L's
>   minimum is +1.74e-08 against 2.52e-07. The ε = 0 point comes from step 2's
>   window, which reproduced to ≤ 3e-7 across runs (step 2b anchor (c)).
>
> **Reading.** The width lever reaches the proportional law at 64 MHz. Each
> element's zero-crossing sits within 5 % of its own −κ_k, as at 10 MHz. The
> C/L split grew from 2 % at 10 MHz to 7 % at 64 MHz, and that is the only
> pre-registered prediction that missed. It is the same order as C's
> departure from the linear model above. **Not changed:** no record, no band,
> no `Z_p` correction. The row stays 🟡 and `PORT-15` gate (i) stays closed.
> Whether a `(1+κ)` correction becomes a registered route is the weekly's.
>
> **Step 2e executed 2026-09-12 (13:30 slot). Configuration D at 64 MHz takes
> both lossless residuals under `REDUCTION_BAND`.** Tests only, additive, same
> module. Under `FEM_EM_PORT14_STEP2_64MHZ`, `step1d_baseline` and
> `step1d_configuration_d` take `_rlc_frequency_hz()`, and `step1d_fit` fits
> `STEP2C_RESIDUALS` (step 2's ε = 0 plus 2c's A/B). Two new tests skip with the
> flag off: `test_step1d_step2e_the_64mhz_fit_reproduces_step2c` and
> `test_step1d_step2e_the_baseline_was_built_at_64mhz`. The terminated-solve
> test stores its in-window ε = 0 residuals before its 64 MHz skip. One window:
> `20260912T183330Z_PORT-14-step2e.log`, `WIDTH_SWEEP=1 STEP2_64MHZ=1`,
> `-n 2`, `-s`, `-k "step1d or terminated_solve_matches or environment"`,
> `timeout -k 30 590`, durable capture: **17 passed, 1 skipped, 19 deselected
> in 189.13 s** (`:3897`), `[capture] rc=0` (`:3963`), Status 0, **191 s**
> (`:3966–3967`). Heavy by ceiling.
>
> - **Anchors and controls (asserted), green.**
>   - The fit reproduces 2c's printed ε\* to 3.38e-05 (C) and 9.36e-06 (L)
>     against rtol 1e-4 (`:3756–3757`). The mean is −0.010553268 against the
>     09:00 journal's hand-rounded −0.010554 (6.94e-05, `:3758`).
>   - The baseline was rebuilt at 64 MHz: S₁₁ sits 6.045467e-01 from the
>     10 MHz record (`:3762`), equal to step 2d's to every printed digit.
>   - D (widths × 0.989446732): 116 085 cells bitwise, reciprocity
>     1.897246132e-15, σ_max 0.999760614 (`:3816–3821`).
>   - Γ = 0 on D: Δ 0.4833 / 0.2388, misses 0.4832 / 0.2388, ≥ 239× the band
>     (`:3831–3832`).
> - **Negative control by reproduction (predicted rtol 1e-6): held.** In-window
>   ε = 0 is 1.354202e-02 / 5.021261e-04, |ratio − 1| = 2.827e-07 / 7.581e-08
>   against step 2 (`:1886, :1893, :3825–3826`). 2c's mixed-window fit is not
>   undermined by drift.
>
> | element | D residual | D/(ε = 0), 64 MHz | step 1d D/(ε = 0), 10 MHz | fit's prediction at the mean ε\* | vs band 1e-3 |
> |---|---|---|---|---|---|
> | C = 100 pF | 1.190127e-04 | 0.008788 | 0.036078 | ≈ 0 (r² = −1.605e-05) | 0.119×, UNDER |
> | L = 1 µH | 9.581734e-07 | 0.001908 | 0.035507 | 1.331180e-04 | 0.00096×, UNDER |
>
> (`:3825–3827`; printed, never asserted — the width was fitted to these.)
>
> **Reading.** The negative-result table selects "both under ⇒ record".
> The (1 + mean ε\*(64)) width undoes κ at 64 MHz on the gate mesh by a larger
> factor than at 10 MHz. L's residual lands 139× below its own fit's floor and
> C's ≈ 4× below what a zero at 2c's ε\*(C) would give (slot arithmetic,
> k = √a). So both true zero-crossings sit nearer the common mean than the
> three-point fits placed them. 2c's 7 % C/L split is within those fits'
> resolution (~3e-4 in ε\*), not evidence of element-dependent physics.
> **Not changed:** no record, no band, no `src/`, no `Z_p` correction. The
> row stays 🟡 and `PORT-15` gate (i) stays closed. Whether a κ-derived (not
> fitted) width becomes a registered route is the weekly's; 128 MHz would be
> its out-of-sample point.
>
> **Ruled 2026-09-12 18:00 review — step 2e accepted; the step-2 family is
> frozen under the four-attempt rule and its question is closed as
> measured.** Re-read `20260912T183330Z_PORT-14-step2e.log:3825–3827` (D
> residuals 1.190127e-04 / 9.581734e-07) and `:1886, :1893` (the in-window
> ε = 0 reproduction). Step 2 has now run five attempts (2, 2b, 2c, 2d, 2e)
> and none registered a record or moved a band, so under §9's family cap (the
> operator directive of 2026-09-12, enacted by this review) no 2f is queued.
> The banked reading: at 64 MHz on the gate mesh, κ is the terminal form's
> Cauchy–Schwarz deficit to 0.3 % (2d) and a (1 + κ)-corrected width takes
> both lossless residuals under 1e-3 (2e). What would move the row from 🟡
> is a **registered** 64 MHz route — a κ-*derived* width, not a fitted one,
> with 128 MHz as its out-of-sample point — and that is the 2026-09-13
> weekly's to specify as a numbered step 3, not a sixth letter under step 2.
>
> **Step 3 scoped 2026-09-13 (weekly review) — the κ-derived width route,
> registered at 64 MHz, out-of-sample at 128 MHz.** One additive opt-in on
> the sheet law scaling the told width by `(1 + κ)` with κ computed in-run
> from the ε = 0 solve's `C/terminal − 1` (`PORT-16`'s `_exact_shares`),
> never fitted; asserted: κ(64) reproduces 2d's 1.0641e-2 at rtol 1e-3, both
> 64 MHz lossless residuals ≤ `REDUCTION_BAND` 1e-3 on the gate mesh, the
> uncorrected 10 MHz floor record unmoved; negative control by record the
> uncorrected 64 MHz miss (1.354202e-02); the corrected 10 MHz pair and the
> 128 MHz pair with in-run κ(128) printed and *predicted* under, never
> asserted. Moves the row 🟡 → ✅ with κ carried as the sheet's named
> systematic. Full item in §10 (the three frozen families).
>
> **Step 3 executed 2026-09-13 12:00 slot — 🚫 incomplete on a
> mis-registered anchor; code parked on
> `attempt/PORT-14-step3-20260913T172330Z` (`86c93f6`).** (0) lifted
> `C/terminal − 1` = test helper bitwise; (ii) corrected 64 MHz lossless
> residuals **5.359129e-05 / 1.998404e-06** ≤ 1e-3; (iii) the 10 MHz floor
> reproduces unmoved; negative control green; printed κ(128)
> 1.064828193e-02 with corrected 4.013e-05 / 5.599e-06 under 1e-3. **(i)
> red:** derived κ(64) 1.060762155e-02 vs "2d's 1.0641e-2" misses by
> 3.119e-03 — but 1.0641e-2 is 2b's *pooled fit*; 2d's `C/terminal − 1` is
> 1.060762e-02 on P1 (reproduced to 1.457e-07), and the step-2d text above
> already records the 0.99688–0.99714× gap. The comparand, not the route,
> is wrong. **Sign:** 2e's fitted ×0.989446732 is `1/(1 + κ)`, not
> `(1 + κ)`; the parked code implements `1/(1 + κ)`. Not loosened; a review
> re-registers (i). Logs `20260913T171434Z_PORT-14-step3-64mhz.log`
> (Status 1, 114 s), `…171649Z_…-10mhz.log` (197 s),
> `…172026Z_…-128mhz.log` (114 s), all `-n 2`.

**`PORT-15` — the circuit layer (HFSS + Circuit)** 🟡 *(**step 1 ✅
2026-09-05, 22:30 slot** — the algebra and its three identities; digits in
the §7 table row. **feature ladder A3**, operator directive 2026-09-04;
serial on `PORT-13` ✅ for the 32×32.)*
Pure linear algebra on a stored N-port S- or Z-matrix: terminate ports in a
lumped network (capacitor values per ring gap, a drive port with its
matching), read tuned S₁₁/S₂₁ and the mode spectrum as the network's
resonances, sweep capacitor values at zero field-solve cost. Gates: (i) the
same reduction identity as `PORT-14` from the circuit side, against
`PORT-14`'s in-model solve; (ii) mode frequencies of the 32-port high-pass
network against the ladder-network closed form (Phase 6's named target).
With `POST-6` this turns one EM solve into tuned-coil B₁⁺ maps — the Ansys
workflow. Standard tier; the field solves are already on disk.

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
assumed** ✅ *(2026-08-16; full 49-line entry archived in
`docs/planning/plan-archive.md`, 2026-09-06 weekly review).* Result:
cross-term **−0.0604 pp** against the pre-stated ±0.5 pp band — additive,
the sequential ladder in `ports/systematics.py` stands as measured; it
closed §10 Phase 5 subgoal 1's last open question. Live carry-forward:
none. Logs: `20260816T140457Z_PORT-10-costprobe.log`,
`20260816T140643Z_PORT-10.log`.

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
| `WF-6` | B1+ field mapping and homogeneity (CV) | ✅ 2026-09-13 (step 5) on the re-scoped subgoal-4 target: on the unloaded F-small birdcage at 10 MHz, CG1, the worst-radius C4 four-copy spread of `\|B₁⁺\|` falls 5.2506 → 2.0719 % and the C4 covariance 3.6159 → 1.6815 % as resolution goes 0.015 → 0.012 m — both falls asserted, both spreads reproduced at rtol 1e-3 (`20260913T170259Z_WF-6-step5.log`, 24 passed, Status 0, 156 s at `-n 4`). A convergence statement only — no closed-form, homogeneity, absolute, C95.3 or Larmor claim; the flag-on ×0.0095 power residual stays banked OPEN in known-issues. *History: `docs/planning/chunks/WF-6.md`.* | heavy (step 1 standard, complex; steps 3h 194 s / 3f′ 117 s / 3i 96 s standard; step 4a 4 s smoke, `-n 1`, real; **step 4g 204 s at `-n 4`**; **step 5 156 s at `-n 4`**; **step 4h 199 s at `-n 4`** + 52 s flag-off control; **step 4i 198 s + 104 s at `-n 4`**; **step 4j 199 s + 101 s at `-n 4`**; step 4k 29 + 32 + 39 + 38 s smoke, `-n 1`, no solve) |
| `WF-7` | SAR10g hotspot identification | ⬜ | heavy |
| `WF-8` | Publication-quality visualization pipeline | ⬜ | standard |
| `WF-9` | **Implant transfer-function excitation (ISO 10974 Tier 3)** — a local impressed source stepped along a lead path + the tangential-`E` path-integral post-processor; heating from `∫ TF(z)·E_tan(z) dz` gated against the direct lead-in-phantom solve — **feature ladder C1** (operator directive 2026-09-04; Phase 7; `WF-7` is to be scoped with this in mind) | ⬜ | heavy |

> `WF-2`/`WF-3` produce structurally valid manifests and reports containing
> physically meaningless numbers. The plumbing is fine and becomes useful the
> moment `TH-1` lands.


**`WF-9` — implant transfer-function excitation (ISO 10974 Tier 3)** ⬜
*(**feature ladder C1**, operator directive 2026-09-04; Phase 7, unscoped
until the phase opens.)* Implant heating is assessed from the tangential
`E` along the lead trajectory in the phantom *without* the implant, folded
with a transfer function measured by stepping a local source along the lead.
Needs: a point-like impressed current source (the `project_source` machinery
at a chosen location/direction), a path-integral post-processor for
`E_tan(z)`, and the fold. Gate: the Tier-3 identity — heating from
`∫ TF(z)·E_tan(z) dz` against the direct lead-in-phantom solve on one
fixture — plus published measured lead-heating data where a geometry
matches. `WF-7`'s hotspot chunk is to be scoped as this pipeline's consumer,
not as a local-SAR peak alone.

**`WF-6` — B1+ field mapping and homogeneity** 🟡 *(steps 1, 2 and 2b ✅ — step 1
2026-08-30 with step 1d, **step 2 ✅ 2026-08-31 22:30 slot** (0.9818% / 0.8087%
against 5%, control 95.1975%, log `20260831T033704Z_WF-6-step2.log`),
**step 2b ✅ 2026-08-31 09:00 slot** — the same five identities at 64 and
128 MHz on one mesh, all inside the unmoved bands at 21.89 / 12.50 phantom
cells/λ, log `20260831T140418Z_WF-6-step2b.log`; **step 3 executed 2026-08-31
13:30 slot and delivered its pre-registered negative result** — the coil-driven
point-SAR map misses all five identities at 25–41% against the same unmoved 5%
band, controls and the power-record reproduction holding, five deliberate reds
on `main` and a known-issues entry, log `20260831T183526Z_WF-6-step3.log`; **no
SAR claim exists** and step 3b (a CG1-`E` estimator leg) is a review's to scope.

**Step 3e executed 2026-09-02 00:30 slot — the promotion landed and every
step-3d anchor reproduced through the packaged path, to every printed digit.**
`_project_to_cg1_restricted` moved verbatim out of
`tests/validation/test_birdcage_sar_map.py` into
`src/fem_em_solver/post/faraday.py` as **`post.project_to_cg1_restricted`**,
signature `(field, cell_tags, *, name, tag, ksp_rtol=1e-12,
return_diagnostics=False)` — `return_diagnostics` default flipped **off** to
match `project_to_cg1`, PETSc prefix renamed off the step-scoped name to
`fem_em_restricted_cg1_mass_`, exported from `post/__init__.py` and both
`__all__`s; the test module is its first caller with
`return_diagnostics=True`. Log `20260902T003813Z_WF-6-step3e-table.log`,
`5 failed, 69 passed` / Status 1 / **122 s** at `-n 2` complex with
`tests/environment` (11 passed) in the same window; the module-only run is
`20260902T003518Z_WF-6-step3e.log`, `5 failed, 58 passed` / Status 1 / 98 s,
and `tests/environment` alone `20260902T003443Z_WF-6-step3e-env.log`,
`11 passed` / Status 0 / 29 s. The 5 failures are step 3's five primal SAR
asserts, unmoved to the digit (25.1096 / 40.5462 / 30.0142 / 38.6120 /
28.1459%). **17 new test items, all green, every one a step-3d record
re-measured through `post/`:** (i) `‖P_Ω E − E‖_Ω/‖E‖_Ω` = **18.7238%** at
`CG1_RECORD_RTOL`, with the **negative control** — the *global*
`post.project_to_cg1` on the same field over the same phantom, measured in the
same run at **1876.1871%** — giving a separation of **100.20×** against the
pre-registered **50×** floor (a promotion that kept integrating over `dx`
would read 1.0×); (ii) `a + b × x` **4.385695e-13** (anchor 1e-10) and
`x² ê_x` **3.741459e-01** (floor 1e-4), both bounds unmoved and the records
now printed beside them; (iii) pinned max |value| **0.000e+00** over owned
**and** ghost blocks at `-n 2`, census asserted at **170** free of **21 397**
owned blocks / **64 191** dofs (globally reduced, rank-count independent);
(iv) all six restricted solves `converged_reason` **2** in **25 / 25 / 25 /
25 / 21 / 25** its, now asserted as `== 2`, `21 ≤ its ≤ 25`, 64 191 dofs
(strengthened from the pre-existing `> 0`, which stays); (v) restricted
phantom power **5.440097168e-08 W** (−3.5058% from the primal record) and the
five identity readings **8.2868 / 9.4743 / 7.3477 / 6.8146 / 6.1185%** with
both controls **123.6255%** / **333.0778%**, all at `CG1_RECORD_RTOL`.
**Collateral:** the `project_to_cg1` docstring now carries 3c's finding as a
`.. warning::` — a *global* L² fit is not a field estimator inside a low-field
subdomain, with the 32.7802 / 1876.1871 / 838.8978% domain table and a pointer
at the restricted sibling — so it no longer lives only in known-issues.
**Scope, unchanged:** this packages an estimator, it does **not** register a
gate. The five primal asserts stay exactly as written and red, the module
still exits 1, no band, tolerance or record moved, no SAR claim comes into
existence, verdict (c) is unaffected, and `WF-6` stays **🟡**. `B` callers are
untouched by construction: no signature, default, band or record of
`project_to_cg1` moved.

**Step 3e′ executed 2026-09-02 06:00 slot — the estimator-degree rung, every
anchor green and the pre-registered clause (γ) printing with its own stated
cause excluded by the same run.** `post.project_to_cg1_restricted` gained a
keyword-only `degree: int = 1` (default unchanged; nothing CG1 moved) and was
driven at `degree=2` for six restricted mass solves on the same mesh, same four
fields, same 51 points, **no curl-curl solve**. Anchors: the degree-monotonicity
theorem holds — `‖P²_Ω E − E‖_Ω/‖E‖_Ω` **14.4724%** ≤ CG1's **18.7238%**; the
pre-registered flip landed at **10.6 decades** (`x² ê_x` 6.659346e-02 at degree
1 → **1.505524e-12** at degree 2 on one exact source), `a + b × x`
1.363313e-12; pinned max **0.000e+00** with 1 004 free of 160 537 owned CG2
blocks on 481 611 dofs; six solves reason **2** in 39–48 its; both controls
survive at 123.2927 / 327.6543%. **And the five identities got worse** —
**19.3491 / 17.2097 / 16.0699 / 14.4087 / 11.3230%** against CG1's 8.2868 /
9.4743 / 7.3477 / 6.8146 / 6.1185% (+5.2 to +11.1 pp) — while the phantom power
*improved* to 5.519662942e-08 W (−2.09% from the primal record vs CG1's
−3.51%). Since a mis-assembled restriction is excluded by the anchors, what is
measured is that **a globally better L² fit of `E` is pointwise worse for these
C4 identities at these 51 points**: the projector and the estimator's degree are
both now excluded as the mechanism, and the identity-from-a-fitted-field
construction itself is what a review must adjudicate (candidates in the
known-issues step-3d row). `20260902T110503Z_WF-6-step3e-prime.log`,
**`5 failed, 82 passed` / Status 1 / 125 s** at `-n 2` complex with
`tests/environment`, standard tier, well inside the 600 s ceiling so the
cost-wall fallback was never needed; printed table
`20260902T111000Z_WF-6-step3e-prime-verdict.log` (121 s). **No band moved, no
SAR gate registered, no SAR claim exists, the five primal asserts stay red and
`WF-6` stays 🟡.**

Step 1 scoped 2026-08-29
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
>
>   **Executed 2026-08-31 (09:00 slot) — green on the first run, chunk
>   stays 🟡.** Built as written: `build_four_port_sweep(frequency_hz=…,
>   reuse=…)` — two additive keywords on the `_four_port_rung` precedent,
>   both defaulting to today's behaviour, no `src/` change — and
>   `tests/validation/test_birdcage_b1_larmor.py`, which imports every
>   helper, band and record from steps 1/1c/1d/2 and restates none.
>   **One mesh, 116 085 cells (ratio 1.000000), three rungs, 12 solves at
>   5.44–5.99 s each; `16 passed` / Status 0 / 202 s at `-n 2`**
>   (`20260831T140418Z_WF-6-step2b.log`), against the 200–260 s estimate.
>     * **Every identity inside the unmoved, imported 5% band at all three
>       frequencies.** Gate (ii) at +90 / −90 / 180°: **2.1870 / 2.1146 /
>       1.8911%** (10 MHz), **2.2187 / 2.1667 / 1.9574%** (64 MHz),
>       **2.1315 / 2.1735 / 1.9511%** (128 MHz). Quadrature (a) C4 /
>       (b) mirror: **0.9818 / 0.8087%**, **0.9570 / 0.7570%**,
>       **0.9106 / 0.6968%**. Gate (i) P1 residual **9.7958e-03 /
>       9.5231e-03 / 9.2445e-03** against 1e-2, its conductor-blind
>       control 10.19 / 10.19 / 13.05% (P2 rows within 4e-5 of the P1
>       rows at every rung).
>     * **Controls all held**, and are the reason the readings mean
>       something: mis-rotated `P3@+90deg` **23.2642 / 24.7535 / 25.2589%**
>       and mis-paired `|B₁⁺|_cw(Mx)` **95.1975 / 95.1118 / 95.1161%**,
>       both asserted strictly outside the band; `valid` 51/51 on every
>       drive and image set and 96/96 on the ring set; the shared
>       `Z_p` = 50 Ω / `V_src` = 1 V premise asserted per rung.
>     * **The reproduction control is exact.** The 10 MHz rung of the new
>       module reproduced all five step-1d/step-2 records at rtol 1e-3 —
>       so the two Larmor columns differ from it by the frequency keyword
>       and nothing else.
>     * **The pre-registered 128 MHz resolution question is answered, and
>       the answer is "no miss".** Phantom cells/λ **69.1393 / 21.8936 /
>       12.5024** against `PORT-11`'s imported floor of 10; the five
>       identities are flat in frequency to ≈ 0.1 pp across a 12.8×
>       frequency span and a 5.5× resolution span. The CG1 floor the 5%
>       band rests on — a 10 MHz measurement — therefore survives at
>       12.5 cells/λ **on this fixture, for these symmetry quantities**.
>       That is a statement about the estimator, not about accuracy: a
>       symmetry identity is blind to any error the C4 rotation shares.
>     * **First Larmor-frequency B₁⁺ figures in the repo — reported,
>       ungated, labelled.** Centre purity `|B₁⁺|/|B₁⁻|` ccw **127.91 /
>       141.81 / 171.94**, cw 0.0081 / 0.0087 / 0.0092, P1 linear
>       1.0006 / 1.0024 / 1.0031 (the "what a non-rotating field reads"
>       line, ≈ 1 at every frequency). Mean `|B₁⁺|` at 1 V per port
>       **7.976427e-08 / 6.500452e-08 / 4.936577e-08 T**, falling with
>       frequency as the loaded coil's terminal current does. CV
>       **2.7563 / 2.7738 / 3.0177%** over the 51 centroids and 2.4577 /
>       2.3847 / 2.5400% over the 96 ring points. **None of these is a
>       homogeneity claim**: no converged mesh, no real drive, no tuning —
>       §2.2's "every 64/128 MHz claim is an identity on one fixture"
>       stands unchanged.
>     * **Scope held.** Degree 1, F-small, symmetry identities only; no
>       SAR, no absolute, tuning or homogeneity claim; §2 did not move.
>       Steps 1, 2 and 2b ✅ and the chunk stays **🟡** — step 3 (SAR) is
>       a review's to scope.
>
> **Step 3 scoped 2026-08-31 10:30 review — coil-driven SAR symmetry
> identities at 10 MHz (§9 item 2).** The subgoal-4 SAR route goes through
> the same solved field as B₁⁺, and `_power_shares` already calls
> `post.mean_sar` for gate (i)'s phantom term — this step changes what is
> *read*, not what is computed. New
> `tests/validation/test_birdcage_sar_map.py`, importing every helper, band
> and record from `test_birdcage_b1_plus_map.py` /
> `test_birdcage_b1_quadrature.py` (`ANS-1`'s rule): the point-SAR map
> `σ|E|²/(2ρ)` via `post.point_sar` on the 51 phantom centroids (E is the
> primal N1curl field — no curl, no DG0/CG1 projection chain, so the CG1
> floor story does not transfer and nobody has measured this estimator's
> floor). **Anchors (bands imported, unmoved):** (i) C4 covariance of the
> single-drive SAR map P1 → P2/P3/P4 at +90/−90/180° ≤ the imported 5%
> band; (ii) the quadrature SAR map (superpose the four `E` fields with
> the step-2 phase convention, *then* square) is C4-invariant ≤ 5% and
> satisfies the mirror identity `SAR_ccw(x) = SAR_cw(Mx)` ≤ 5%; (iii)
> `mean_sar`'s `dissipated_power_w` on P1 reproduces gate (i)'s phantom
> share record at rtol 1e-3 (conservation cross-check against the step-1
> record, not a new band). **Pre-registered ceiling note (rubric #2):** SAR
> is quadratic in `E`, so a symmetric-error argument allows ~2× the B₁⁺
> map's ~2.2% covariance floor — 5% is therefore a real bar, not a
> giveaway, and the mis-rotated control (B₁⁺ analogue read 23–25%) is the
> separation. **Negative controls:** the mis-rotated single-drive
> comparison > 5%; the mis-paired quadrature sense > 5%; the σ-blind
> `mean_sar` control (score against σ = 0 in the conductor tag) from the
> `MAT-4` machinery where cheap. **Recorded, ungated, labelled:** peak and
> mean point-SAR at 1 V per port, peak-to-mean ratio, for both the P1 and
> the quadrature drive. **Cost:** mesh ~22 s + four solves ~24 s + point
> evaluations ≈ **120 s**, standard, complex, `-n 2`, `-k 30 400`.
> **Traps:** `point_sar` takes the *split* `e_real`/`e_imag` fields and a
> scalar σ — assert the phantom-σ-uniform premise before using it;
> magnitudes after point evaluation; only floats/arrays escape the solve
> helper; no `<=` on complex operands. **Scope:** 10 MHz, F-small,
> degree 1, symmetry identities plus one reproduction — **no** SAR10g /
> C95.3 (that is `MAT-4` step 2 + `WF-7`), no mass-averaged claim, no
> Larmor SAR (a later step mirrors 2b's rung pattern), no absolute claim;
> chunk stays 🟡. **Negative result:** an identity missing is an estimator
> finding exactly like step 1's DG0 floor — known-issues entry with every
> reading, keep the assert, stop; whether point-SAR needs its own
> re-registered band is the next review's ruling, never in-slot.
>
> **Step 3 executed 2026-08-31 13:30 slot — the pre-registered negative
> result: every SAR identity misses, the controls and the reproduction
> hold, and the finding is the estimator.** New
> `tests/validation/test_birdcage_sar_map.py`, everything imported
> (fixture, sample set, band, records, phase convention);
> `20260831T183526Z_WF-6-step3.log`, **`5 failed, 16 passed` / Status 1 /
> 96 s** at `-n 2` complex with `tests/environment`, against the ≈ 120 s
> estimate.
>
>   * **The five identities, band 5% imported and unmoved:** single-drive
>     C4 `SAR_P2(Rx)` **25.1096%**, `SAR_P4(−Rx)` **40.5462%**,
>     `SAR_P3(180°)` **30.0142%**; quadrature C4 **38.6120%**; mirror
>     `SAR_cw(Mx)` vs `SAR_ccw(x)` **28.1459%**. The `|B₁⁺|` analogues on
>     the *same* points, same drives, same band read 2.19 / 2.11 / 1.89%
>     and 0.98 / 0.81%.
>   * **Everything that could have made it a defect instead passes.**
>     Controls: mis-rotated `SAR_P3(Rx)` **129.8187%**, quadrature vs
>     single drive **334.5786%**, both asserted `> 5%`. Anchor (iii):
>     `mean_sar`'s phantom `dissipated_power_w` on P1 =
>     **5.637745667e-08 W**, reproducing gate (i)'s record to every
>     printed digit. Premise: phantom σ flat at **0.5 S/m** over 537
>     tag-3 cells, asserted before a scalar σ is handed to `point_sar`;
>     all 51 points of every image set evaluated (`point_sar` raises
>     rather than zero-filling).
>   * **The diagnosis is in the run, not in a hypothesis.** The three
>     single-drive readings use only step 1's solved fields and step 1d's
>     own image sets — no superposition, no mirror, no code this step
>     introduced — and they already miss by 25–40%. What changed is the
>     estimator: `|B₁⁺|` is read off an L²-projected CG1 `B`, SAR
>     pointwise off the **primal N1curl `E`** with no projection. A
>     Whitney `E` is normally discontinuous, so its centroid value carries
>     an O(h) per-cell error the C4 rotation does not share, and squaring
>     doubles it — 25–40% ≈ 2× a ~13–20% pointwise `|E|` floor. Step 1's
>     8.65% DG0 curl, one estimator further out.
>   * **One scoped control was degenerate and is reported instead of
>     asserted.** The mirror-omitted comparison `SAR_ccw(Mx)` vs
>     `SAR_ccw(x)` reads **28.1445%** against identity (iii)'s 28.1459% —
>     the mirror moves it by 1.4e-3 pp. SAR is a magnitude-squared with no
>     ± senses to mis-pair, so step 2's `|B₁⁺|_cw(Mx)` analogy does not
>     carry; the module prints this ungated (docstring says why) and
>     asserts the two controls that do separate. Disposition is the
>     review's.
>   * **Reported, ungated, labelled:** point SAR at 1 V per port — P1
>     peak **7.630679e-07** W/kg, mean **1.453536e-07** W/kg, peak/mean
>     **5.2497**; quadrature peak **2.065442e-06** W/kg, mean
>     **7.706353e-07** W/kg, peak/mean **2.6802**. Not safety figures.
>   * **Collateral, verified:** the phase convention now lives in one
>     place — `quadrature_phase_weights` in
>     `test_birdcage_b1_quadrature.py`, called by that module's fixture
>     and by this one, so the two legs cannot drift on the thing step 2
>     paid a run to get right. Step 2 re-ran green and unmoved:
>     `20260831T183734Z_WF-6-step3-step2-regression.log`, **`6 passed` /
>     Status 0 / 80 s**, identities 0.9818 / 0.8087%, control 95.1975%.
>   * **Five deliberate reds on `main`** with a known-issues entry
>     carrying every reading (🔴 OPEN 2026-08-31). **No band moved**,
>     `WF-6` stays **🟡**, and **no SAR claim exists** — the step measured
>     that the coil-driven point-SAR map is not yet gateable at the B₁⁺
>     band, which is a finding, not a gate. **Resolves with** a step-3b
>     estimator leg on step 1b's pattern: the same identities off an
>     L²-projected CG1 `E` beside the primal column, no new solve, ≈ 96 s
>     — a review's to scope.
>
> **Step 3b scoped 2026-08-31 18:00 review — the estimator comparison,
> on step 1b's pattern (§9 item 1 carries the executable plan).** A
> second module fixture `sar_map_cg1`: `post.project_to_cg1` on each
> solve's `e_complex` (its check is value shape `(3,)`, which N1curl
> satisfies — the same mass projection 1d used on `B`), split on the
> projection's own space, `point_sar` on exactly step 3's image sets, the
> quadrature senses by superposing the CG1 dof arrays with the imported
> phase weights (linear, so equal to projecting the superposition).
> **Asserted:** the primal column reproduces step 3's five readings
> (25.1096 / 40.5462 / 30.0142 / 38.6120 / 28.1459%) and both controls
> (129.8187 / 334.5786%) at `CG1_RECORD_RTOL`, exported as
> `STEP3_PRIMAL_*` records; the CG1 column's two controls stay `> 5%`
> (the projection must not smooth them away); the `mean_sar` record; the
> five primal asserts untouched and red. **Printed, not gated:** the five
> CG1 identity readings with a pre-registered verdict — **(a)** all ≤ 5%
> with controls surviving → pointwise-`E` estimator floor, the next review
> re-registers the SAR gate on CG1 as 1d did; **(b)** 180° in, ±90° out →
> something rotation-specific in the field, a review reads it; **(c)** all
> out → the ~1 cm phantom cells do not resolve a quadratic-in-`E` map at
> this band, a finer-rung question for the weekly review. The
> mis-paired-sense comparison is **struck** from SAR scopings (degenerate
> at 1.4e-3 pp, measured). Collateral, constants only: the module's step-2
> literals switch to `EX-39`'s exported `STEP2_*`. ≈ 130 s, `-n 2`,
> standard. **No band moves in-slot; `WF-6` stays 🟡 under every
> verdict.**
>
> **Step 3b executed 2026-08-31 19:30 slot — verdict (c) prints, and the
> run's own diagnostics say (c)'s pre-registered *reason* is the wrong
> one: the finding is `project_to_cg1` on an N1curl `E`, not the
> phantom's resolution.** `20260901T003300Z_WF-6-step3b.log` (105 s) and
> `20260901T003548Z_WF-6-step3b-diagnostic.log` (100 s, the added
> projection diagnostic), both **`5 failed, 25 passed` / Status 1** at
> `-n 2` complex with `tests/environment`, against the ≈ 130 s estimate.
>
>   * **The anchor held to every digit.** The primal column reproduced
>     step 3's five identities — 25.1096 / 40.5462 / 30.0142 / 38.6120 /
>     28.1459% — and both controls — 129.8187 / 334.5786% — at
>     `CG1_RECORD_RTOL`, now exported as `STEP3_PRIMAL_IDENTITY_RECORDS` /
>     `STEP3_PRIMAL_CONTROL_RECORDS` with the log line as provenance. The
>     five primal asserts are untouched and are the run's five failures.
>   * **The CG1 column is worse than the primal one everywhere**
>     (printed, never gated): **152.0459 / 109.7797 / 169.5050 / 53.1869 /
>     40.8440%**. Both CG1 controls survive the projection and are
>     asserted — 163.6144 / 75.9135% against the 5% band — so the
>     pre-registered verdict evaluates, in code, to **(c)**.
>   * **(c)'s pre-registered reading does not survive the same run.** The
>     CG1 phantom power `½∫σ|E_cg1|²` reads **1.990062891e-05 W** against
>     the primal record 5.637745667e-08 W (**+35 198.9%**; step 1d's `B`
>     projection moved its mean by 0.38%), and the diagnostic re-run's
>     `‖E_cg1 − E‖/‖E‖` over the phantom reads **1876.1871%**. A
>     projection cannot be 19× its own argument in the region being read
>     *and* be a coarse-but-honest estimator of it, so the measurement is
>     about the projector applied to `E`, not about ~1 cm phantom cells
>     failing to resolve a quadratic map. The estimator step 1d registered
>     for the DG0 `B` phasor is **not, as landed, a usable `E`
>     estimator on this fixture**; the `|B₁⁺|` gates are untouched, since
>     they project `B` and its 0.38% figure is unchanged.
>   * **Nothing moved that a negative result may not move.** No band, no
>     tolerance, no assert; the mis-paired-sense comparison stayed struck;
>     the module carries no step-2 numeric literals, so the scoped
>     `STEP2_*` collateral was a no-op (recorded so the next review does
>     not re-scope it). Five deliberate reds on `main`, unchanged in count
>     and in value. **No SAR claim exists** and `WF-6` stays **🟡**.
>   * **Owed next, for a review to scope (in known-issues' new "Resolves
>     with"):** separate the three candidates for the projector finding —
>     a global L² fit dominated by the sheet/conductor-edge `E`
>     singularities; a non-converged CG/Jacobi mass solve at `ksp_rtol`
>     1e-12 on a vector CG1 space over 116 085 cells, which the helper
>     never checks; or an element-side mismatch that the value-shape
>     `(3,)` guard does not catch. One slot: print the KSP converged
>     reason and iteration count, and read `‖E_cg1 − E‖/‖E‖` over the
>     whole mesh beside the phantom-restricted figure.
> **Step 3c scoped 2026-09-01 03:00 review — the projector diagnosis, §9
> item 6.** Separate the three candidates in one slot, on the step-3b
> module (`tests/validation/test_birdcage_sar_map.py`, the `sar_map_cg1`
> fixture), no new solve. **(i)** The mass solve's convergence:
> `post.project_to_cg1` builds a `LinearProblem` and discards its solver —
> expose it behind an opt-in kwarg (default off, the `B` callers untouched)
> and assert `getConvergedReason()` **> 0** with `getIterationNumber()`
> printed; the expected value is `KSP_CONVERGED_RTOL` (2) at `ksp_rtol`
> 1e-12 / `ksp_atol` 1e-30, and `DIVERGED_ITS` (−3) at PETSc's 10 000-step
> default is what candidate 2 looks like. **(ii)** The exact-reproduction
> control: interpolate `f = a + b × x` — in `N1curl₁ ∩ CG1³` — into the
> solve's own N1curl space on the fixture mesh (as a complex `Function`;
> the helper refuses real inputs), project it, and assert
> `‖P f − f‖_{L²(Ω)}/‖f‖ ≤ 1e-10`: a pass refutes candidate 3 (an
> element-side mismatch), a fail confirms it. The control's control is
> `f = x² ê_x` (∉ CG1³), whose residual must read **> 1e-3**. **(iii)**
> Printed, not gated: `‖E_cg1 − E‖/‖E‖` over the **whole mesh** beside the
> phantom figure (1876.1871%, re-asserted at rtol 1e-3 as a record) and
> over a **phantom core** — phantom cells none of whose vertices lie on the
> phantom boundary (cell→vertex connectivity, rank-local; reduce every norm
> with `assemble_scalar` + `allreduce`). A whole-mesh figure ≪ the phantom's
> says the global fit is dominated elsewhere (candidate 1, the sheet /
> conductor-edge `E`); a core figure ≪ the phantom's says the mechanism is
> the CG1 smear of the normal-`E` jump at the σ interface — which no
> vertex-continuous space represents — and the honest `E` estimator is
> phantom-restricted or cellwise, a review's step 3d to scope. **Anchors:**
> (i), (ii); every step-3b record (primal and CG1 columns, both control
> sets, phantom power, the 1876% figure) reproducing at `CG1_RECORD_RTOL`;
> the five deliberate reds kept exactly. **Negative control:** the `x²`
> field's residual, and the mis-rotated CG1 control still asserted > 5%.
> **Cost:** step 3b ran 100–105 s; two extra 116 085-cell vector mass solves
> ≈ 10 s → **≈ 130 s**, `timeout -k 30 400`, `tests/environment` first.
> **Traps:** no `<=` on complex operands; `project_to_cg1`'s default `name`
> — pass one per field; the module's five primal asserts stay red and the
> run's exit stays 1 — the anchors are read from the log, as 3b's were.
> **Scope:** a diagnosis of the projector — no band, no SAR gate, no
> re-registration, nothing in `src/` beyond the opt-in diagnostics return;
> `WF-6` stays 🟡 whatever prints. **Negative result:** (ii) failing or (i)
> ≤ 0 *is* the finding — known-issues "Resolves with" row, keep every
> assert, do not raise the iteration cap in-slot, stop.
>
> **Step 3c executed 2026-09-01 07:30 slot — the projector is a projector;
> candidates 2 and 3 are refuted and candidate 1 is what the domain table
> says.** `20260901T123421Z_WF-6-step3c.log`, standard tier, complex, `-n 2`
> with `tests/environment`, **`5 failed, 38 passed` / Status 1 / 103 s**
> against the ≈ 130 s estimate. The five failures are step 3's five primal
> asserts, unmoved to the digit (25.1096 / 40.5462 / 30.0142 / 38.6120 /
> 28.1459%); every step-3b record — primal and CG1 identity columns, both
> control sets, the CG1 phantom power 1.990062891e-05 W, the 1876.1871%
> phantom residual — reproduced at `CG1_RECORD_RTOL` and is now asserted.
>
>   * **(i) The mass solve converges.** `converged_reason` **2**
>     (`KSP_CONVERGED_RTOL`) in **26** iterations on **64 191** CG1 dofs at
>     `ksp_rtol` 1e-12 — **candidate 2 (a non-converged Jacobi/CG mass solve
>     the helper never checks) is refuted.** The solver is now readable
>     through an opt-in `return_diagnostics` kwarg on `post.project_to_cg1`
>     (default off; every `B` caller untouched).
>   * **(ii) The projector reproduces what `CG1³` contains, exactly.**
>     `f = a + b × x`, interpolated into the solve's own N1curl space as a
>     complex `Function` and projected, leaves `‖P f − f‖/‖f‖` =
>     **1.326607e-13** against the 1e-10 anchor (reason 2, 23 its); the
>     control's control `x² ê_x` leaves **9.882703e-02**, above the 1e-3
>     floor (reason 2, 26 its). **Candidate 3 (an element-side mismatch the
>     value-shape `(3,)` guard misses) is refuted:** `project_to_cg1` *is*
>     the L² projection it documents, on N1curl input.
>   * **(iii) The domain table says candidate 1.** `‖E_cg1 − E‖/‖E‖` reads
>     **32.7802%** over the **whole mesh**, **1876.1871%** over the
>     **phantom** and **838.8978%** over the **phantom core** (33 of 537
>     owned tag-3 cells, no vertex on the phantom boundary). The whole-mesh
>     figure is **57× below** the phantom's: the global L² fit is a fit of
>     the regions that dominate `‖E‖` — the sheets and conductor edges — and
>     the phantom, whose `|E|` is orders of magnitude smaller, is a
>     rounding-error corner of it. That is **candidate 1, measured.** The
>     σ-interface smear is present but secondary: excluding every cell that
>     touches the phantom boundary halves the residual (1876 → 839%) and
>     leaves it O(10), so the interface jump is not the mechanism either.
>   * **What this closes and what it does not.** `post.project_to_cg1`
>     needs no fix — the `|B₁⁺|` gates that use it are untouched and remain
>     correct (they read `B` where `B` is not 10³ times larger elsewhere).
>     What is wrong is the *use*: a **global** L² projection is not an `E`
>     estimator inside a low-field subdomain of a fixture with a huge-field
>     region. The honest estimator is phantom-restricted (project on the
>     phantom submesh) or cellwise; scoping that is **step 3d**, a review's
>     call, not this slot's. **No band moved, no assert loosened, nothing
>     re-registered, no SAR claim exists** and `WF-6` stays **🟡**.
>
> **Step 3d — scoped 2026-09-01 10:30 review from 3c's three readings (§9
> item 9): the phantom-restricted CG1 `E` estimator, and the five identities
> read off it.** 3c's domain table said the *use* is wrong, not the
> projector: a global L² fit on this fixture is a fit of the sheet /
> conductor-edge `E`, and the low-`|E|` phantom gets its tail (whole mesh
> 32.78% vs phantom 1876.19%, 57× apart). The two routes 3c named are not
> equal. **Cellwise is struck by derivation, not run:** a degree-1
> first-kind N1curl function is `a + b × x` on every cell, which `DG1³`
> contains, so a per-cell L² projection onto `DG1³` reproduces the primal
> `E` exactly and its point readings *are* the primal column (25.11 /
> 40.55 / 30.01 / 38.61 / 28.15%); a per-cell projection onto `DG0³` is the
> cell average, which discards the in-cell variation and keeps every
> inter-cell jump — neither is an estimator, and the slot does not spend a
> window confirming what the polynomial degrees already say. **The
> phantom-restricted route, on the parent mesh** — no submesh, no
> cross-mesh interpolation of an N1curl field (an unpaid trap): in the
> step-3b module, a sibling of `post.project_to_cg1` (test-local first;
> `post/` only if a review later promotes it) whose mass matrix and load
> are `ufl.inner(u, v) * dx(3)` / `ufl.inner(E, v) * dx(3)` with
> `dx = Measure("dx", subdomain_data=cell_tags)` on the **same**
> `("Lagrange", 1, (3,))` space, and every CG1 dof with no phantom-cell
> support pinned to zero through a `dirichletbc` (dofs =
> complement of `fem.locate_dofs_topological(space, tdim,
> phantom_cells)`, taken over owned **and ghost** dofs so the pin is
> consistent across ranks; `phantom_cells` from `cell_tags.find(3)`
> including ghosts — the restricted mass matrix is SPD on the phantom
> vertex set, so CG + Jacobi at `ksp_rtol` 1e-12 stands; read the
> `converged_reason` through the same opt-in diagnostics pattern 3c
> landed). Four restricted projections (P1–P4), the two quadrature senses
> by superposing dof arrays (linear, as 3b), `point_sar` on exactly the 51
> points, the two controls (mis-rotated `SAR_P3(Rx)`; quadrature vs single
> drive) exactly as 3b built them. **Anchors (asserted):** (i) the
> best-approximation inequality — `P_Ω` minimises `‖· − E‖_Ω` over all of
> `CG1³|_Ω`, and the global projection restricted to the phantom is one
> member of that set, so `‖P_Ω E − E‖_Ω / ‖E‖_Ω ≤ 1876.1871%` (3b/3c's
> record, `STEP3B_PHANTOM_PROJECTION_RESIDUAL`) is a theorem about the
> code, and a violation is a bug in the restriction, not a finding about
> SAR; the separation factor is printed; (ii) the exact-reproduction
> control under the restriction — `f = a + b × x` (`PROJECTOR_FIELD_A/B`)
> interpolated complex into the solve's N1curl space and restricted-
> projected leaves `‖P_Ω f − f‖_Ω / ‖f‖_Ω ≤ 1e-10` (`PROJECTOR_EXACT_
> RESIDUAL`), and outside the phantom the pinned dofs read exactly 0;
> (iii) `converged_reason > 0` on all six restricted solves; (iv) every
> 3b/3c record reproduced at `CG1_RECORD_RTOL` — primal identities and
> controls, the global-CG1 identities and controls, the CG1 phantom power
> 1.990062891e-05 W, the 1876.1871% residual, the whole-mesh 32.7802%
> and core 838.8978% — and the five primal asserts kept **exactly as
> written and red**. **Negative controls:** the restricted CG1 column's
> two controls asserted `> C4_COVARIANCE_BAND` (the primal ceilings are
> 129.8 / 334.6%, 3b's global-CG1 read 163.6 / 75.9% — a restricted
> control landing under 5% is itself the finding); the control's control
> `x² ê_x` under the restriction, printed and asserted `> 1e-4` — the
> global reading was 9.882703e-02, the restricted one is a quadratic's
> CG1 fit error over the phantom, of order `(h/D)²`, and no phantom this
> mesh resolves at ~1 cm cells has `D/h` above 100, so 1e-4 is the
> arithmetic floor, not a tuned one. **Printed, journaled, NOT gated:** the
> five restricted-CG1 identity readings and the restricted phantom power
> `½∫_Ω σ|E_Ω|²` beside the primal 5.637745667e-08 W and the global-CG1
> 1.990062891e-05 W (+35 199%), with 3b's **pre-registered three-way
> verdict** printed beside them, unchanged: **(a)** all five ≤ 5% with both
> restricted controls > 5% → a pointwise-`E` estimator floor exists on
> this fixture, and the next review re-registers the SAR gate on the
> restricted estimator exactly as 1d did for `|B₁⁺|`; **(b)** the 180°
> column ≤ 5% but a ±90° column misses → something the rotation does not
> share in the field itself (sheet / mesh asymmetry) — a review reads it;
> **(c)** all five miss → with the projector exonerated (3c) and the
> global-fit tail removed (this step's (i)), the residual miss is the
> fixture's resolution of a quadratic-in-`E` map at ~1 cm phantom cells,
> and a finer rung is the weekly review's question, costed against
> `TH-11`'s memory wall. **Cost:** 3c ran 103 s; six restricted mass
> solves on a matrix that is identity outside the phantom add ≈ 20 s →
> **≈ 130 s**, standard tier, complex, `-n 2`, `tests/environment` first,
> `timeout -k 30 400`. **Traps:** the helper refuses real inputs —
> interpolate the controls as complex; `locate_dofs_topological` on a
> blocked space returns block indices — build the zero BC from a zero
> `fem.Function(space)` and those indices, never a scalar `Constant`; the
> complement must be taken over `size_local + num_ghosts` blocks or the
> ghost rows go unpinned and the two-rank solve differs from the one-rank
> one (this is what `-n 2` is for); `cell_tags.find` and every norm are
> rank-local — `assemble_scalar` + `allreduce` on every figure; `point_sar`
> takes `np.real` of each split field — split the complex CG1 arrays as
> 3b did, never hand the complex function twice; do **not** add the
> mis-paired-sense comparison (degenerate for a magnitude-squared, step 3);
> the module's exit stays 1 (five deliberate reds) — read the anchors from
> the log as 3b/3c did; no `<=` on complex operands. **Scope:** an
> estimator comparison on one fixture at 10 MHz — **no band moves
> in-slot, no SAR gate is registered, nothing re-registered, no
> homogeneity / absolute / C95.3 claim, `WF-6` stays 🟡 whatever prints**;
> nothing under `src/` unless the review promotes the helper afterwards.
> **Negative result:** whichever verdict prints is the deliverable —
> journal it in this bullet and the known-issues "Resolves with (step 3c's
> finding)" row, keep every assert, stop; anchor (i) *failing* is a defect
> in the restriction (pinning or measure), to be journaled as such and
> not read as physics; a 3b/3c record not reproducing is a fixture
> finding, not a rescope.
>
> **Step 3d executed 2026-09-01 13:30 slot, every anchor green on the first
> run — the restricted estimator is an honest `E` estimator and it takes the
> five identities from 25–40% to 6.1–9.5%, but all five still miss 5%, so the
> pre-registered verdict prints (c).**
> `20260901T183416Z_WF-6-step3d.log`, standard tier, complex, `-n 2` with
> `tests/environment`, **`5 failed, 52 passed` / Status 1 / 123 s** against the
> ≈ 130 s estimate. The five failures are step 3's five primal asserts,
> unmoved to the digit (25.1096 / 40.5462 / 30.0142 / 38.6120 / 28.1459%); every
> 3b/3c record reproduced at `CG1_RECORD_RTOL`, and step 3c's other two domain
> figures (whole mesh 32.7802%, phantom core 838.8978%) are now asserted too.
>
>   * **(i) The best-approximation inequality holds, with room to spare.**
>     `‖P_Ω E − E‖_Ω/‖E‖_Ω` = **18.7238%** against the global fit's
>     **1876.1871%** on the same phantom — a **100.20×** separation, not a
>     marginal pass. 3c's diagnosis is thereby confirmed constructively: the
>     1876% was the global fit's tail, and restricting the fit to the region it
>     is read over removes it.
>   * **(ii)/(iii) The restriction is a projection.** `f = a + b × x`
>     restricted-projected leaves **4.385695e-13** over `dx(3)` (anchor 1e-10);
>     the control's control `x² ê_x` leaves **3.741459e-01**, two orders above
>     the arithmetic `(h/D)² ≳ 1e-4` floor (the *global* figure was 9.88e-02 —
>     the restriction makes the quadratic *harder* to fit, as a smaller domain
>     with the same `h` should). Pinned dofs read **exactly 0.000e+00** on owned
>     and ghost blocks at `-n 2`; **170** of 21 397 owned CG1 blocks are free.
>     All six restricted mass solves return `converged_reason` **2**
>     (`KSP_CONVERGED_RTOL`) in 21–25 iterations on 64 191 dofs.
>   * **The restricted phantom power corroborates it independently.**
>     `½∫_Ω σ|E_Ω|²` = **5.440097168e-08 W**, i.e. **−3.51%** against the primal
>     record 5.637745667e-08 W — against the *global* CG1 projection's
>     +35 198.9% (1.990062891e-05 W, −99.73% from here). A projection does not
>     conserve power, so −3.5% is the size an honest `E` fit over this phantom
>     has; +35 199% was not.
>   * **The five identities, printed and NOT gated:** **8.2868 / 9.4743 /
>     7.3477 / 6.8146 / 6.1185%** (primal 25.11 / 40.55 / 30.01 / 38.61 /
>     28.15%; global CG1 152.05 / 109.78 / 169.51 / 53.19 / 40.84%). Both
>     restricted controls survive and are asserted: **123.6255%** (mis-rotated)
>     and **333.0778%** (quadrature vs single drive) — the fit did not smooth the
>     azimuthal structure away, it removed the estimator noise. So the estimator
>     column improved by 3–6× at every identity and by 20× against the global
>     one, and **still misses the 5% band at every one of the five**: the
>     pre-registered verdict evaluates to **(c)**, all five outside.
>   * **What (c) means now, with 3c and this step's (i) both in hand.** The
>     projector is exonerated (3c) and the global-fit tail is removed (this step,
>     100× separation, power to −3.5%), so the residual 6.1–9.5% is what is left
>     when the estimator is right: **the fixture's ~1 cm phantom cells reading a
>     quadratic-in-`E` map**. That is (c)'s pre-registered reading, and this time
>     the diagnostics do not contradict it — unlike step 3b, where they relocated
>     the finding. A finer phantom rung is **the weekly review's question, costed
>     against `TH-11`'s memory wall**; it is not this bullet's to scope. The
>     restricted helper stays test-local (`_project_to_cg1_restricted` in
>     `tests/validation/test_birdcage_sar_map.py`); promoting it into `post/` is a
>     review's call. **No band moved, no assert loosened, no SAR gate registered,
>     nothing re-registered, nothing under `src/`, no SAR claim exists** and
>     `WF-6` stays **🟡**.
>
> **Steps 3e and 3e′ scoped 2026-09-01 18:00 review** — the two questions
> step 3d left that are a *daily* review's, both named by the step-3d
> known-issues "Resolves with" row and neither of them the finer-mesh rung
> (that stays the weekly's, costed against `TH-11`).
>
>   * **Step 3e — promote `_project_to_cg1_restricted` into `post/`**
>     (§9 item 1). Its best-approximation anchor (18.7238% vs the global
>     fit's 1876.1871%, 100.20×), its exact-reproduction control
>     (4.385695e-13) and its ghost-safe pinning (170 free of 21 397 owned
>     blocks, pinned max \|value\| exactly 0.000e+00 at `-n 2`) are all
>     measured and asserted, which is the bar step 1d cleared before
>     `project_to_cg1` was packaged for `B`. It is the only `E` estimator
>     this repo has that reproduces the phantom power to 3.5%. Collateral:
>     a docstring warning on `post.project_to_cg1` that a *global* L² fit
>     is not an `E` estimator inside a low-field subdomain — 3c's finding,
>     which currently lives only in known-issues. **No gate is registered
>     and no band moves**; `WF-6` stays 🟡.
>   * **Step 3e′ — the estimator-degree rung** (§9 item 4). Verdict (c)
>     attributes the residual 6.1–9.5% to the fixture's ~1 cm phantom cells
>     reading a quadratic-in-`E` map, but nothing has separated *estimator
>     degree* from *mesh h* on this fixture. A CG2³ restricted projection
>     of the same four solved fields on the same mesh separates them for
>     the cost of six mass solves and no curl-curl solve, and it is a
>     different axis from the weekly's finer-mesh question, not a
>     pre-emption of it. The anchor is a theorem — the restricted
>     best-approximation residual cannot *increase* with degree — and the
>     control's control flips sign of difficulty: `x² ê_x` lies in CG2³
>     exactly, so where CG1 left 3.741459e-01 the CG2 fit must reproduce it
>     to ~1e-10, a 9-decade pre-registered separation. **A null result (the
>     five identities do not move) is the informative outcome**: it
>     corroborates (c) and hands the weekly a question about h alone.
>
> **Step 3e′ executed 2026-09-02 06:00 slot — every anchor green on the first
> run, and the pre-registered clause that printed is (γ), whose own stated
> cause the same run excludes.** `post.project_to_cg1_restricted` gained a
> keyword-only `degree: int = 1` (default unchanged, so no CG1 caller, record or
> band moved; the space and the bc's zero `Function` are both built from it, and
> `degree < 1` raises), and the test module drives it at `degree=2` for six
> restricted mass solves on the same 116 085-cell mesh, the same four solved
> fields, the same 51 points, the same pinning — **no curl-curl solve**.
>
>   * **Anchors, all asserted, all green.** (i) *Degree monotonicity*, a theorem
>     about the code: `‖P²_Ω E − E‖_Ω/‖E‖_Ω` = **14.4724%** against the imported
>     CG1 bound **18.7238%** — the CG2³ fit is strictly *better* in the norm it
>     minimises, as `CG1³ ⊂ CG2³` requires. (ii) The pre-registered **flip**
>     landed: `x² ê_x` restricted-projects at degree 2 to **1.505524e-12**
>     (bound 1e-10) where the **same exact source** at degree 1 reads
>     **6.659346e-02** — a measured separation of **10.6 decades**, one source,
>     one operator, one difference. (iii) `a + b × x` **1.363313e-12**.
>     (iv) Pinned max |value| exactly **0.000e+00** over owned *and* ghost
>     blocks at `-n 2`; census **1 004 free of 160 537** owned CG2 blocks on
>     **481 611** dofs (reported, not asserted — no CG2 record exists) against
>     CG1's 170 / 21 397 / 64 191. (v) All six CG2 solves `converged_reason`
>     **2**, in **48 / 48 / 48 / 48 / 39 / 47** its (reported, not gated).
>     (vi) Every step-3d/3e CG1 record reproduced unmoved in the same window.
>     Negative control: both step-3b controls **survive** the higher-degree fit
>     at **123.2927%** and **327.6543%** (CG1: 123.6255 / 333.0778%).
>   * **The printed verdict, which is the deliverable: (γ).** The five
>     identities off the CG2-restricted `E` read **19.3491 / 17.2097 / 16.0699 /
>     14.4087 / 11.3230%** against CG1's **8.2868 / 9.4743 / 7.3477 / 6.8146 /
>     6.1185%** and primal's 25.11 / 40.55 / 30.01 / 38.61 / 28.15% — every one
>     **worse** than CG1 by **+11.06 / +7.74 / +8.72 / +7.59 / +5.20 pp**, so
>     the pre-registered arithmetic selects (γ). CG2-restricted phantom power
>     **5.519662942e-08 W**, **−2.0945%** from the primal record 5.637745667e-08 W
>     — *closer* than CG1's −3.51%.
>   * **But (γ)'s pre-registered cause — "the CG2 restriction is mis-assembled,
>     and anchors (i)/(ii) should have caught it" — is excluded by this run's
>     own anchors**, which are green with orders of room, and the log says so on
>     its own line rather than leaving a reviewer to act on the clause's prose.
>     What is actually measured is that **a globally better L² fit of `E` over
>     the phantom is pointwise *worse* for these C4 identities at these 51
>     points**: the CG1 fit's extra smoothing was flattering the identities, not
>     resolving them. Both of the mechanisms this fixture has named — the
>     projector (3b/3c) and now the estimator's **degree** — are excluded, and
>     verdict (c)'s attribution to mesh `h` is neither confirmed nor refuted:
>     step 3f will now be read knowing a better estimator can *raise* these
>     numbers. **This is a finding about the identity-from-a-fitted-field
>     construction and it is a review's to adjudicate, not a slot's** — the
>     candidates are written into the known-issues step-3d row (read the
>     identities as phantom *integrals* rather than at 51 sampled points; or
>     re-run step 1c's sample-set control on this column; or run 3f anyway).
>   * **Scope, unchanged and observed:** no band moved, no tolerance moved, **no
>     SAR gate registered**, no homogeneity / absolute / C95.3 claim, the five
>     primal asserts stay exactly as written and red, the module still exits 1,
>     and **`WF-6` stays 🟡**. 13 new test items, all green.
>     `20260902T110503Z_WF-6-step3e-prime.log`, **`5 failed, 82 passed` /
>     Status 1 / 125 s** at `-n 2` complex with `tests/environment` (11 passed)
>     in the same window — **standard tier, against the item's 250–400 s
>     estimate and its 600 s ceiling, so the pre-registered cost-wall fallback
>     (drop to the four single drives) was never needed**; the printed table is
>     `20260902T111000Z_WF-6-step3e-prime-verdict.log` (same content, `-s`,
>     121 s) and the pre-caveat table run is
>     `20260902T110734Z_WF-6-step3e-prime-table.log` (module only, 99 s).
>     Cost note for the weekly: CG2³ was **7.50×** the CG1 dofs and cost about
>     **2×** the CG1 iterations, and the whole window still fits in 125 s
>     because the restricted mass matrix is identity outside 537 cells.
>
> **Step 3f scoped 2026-09-02 weekly review — the finer-phantom rung, costed
> against `TH-11` and found cheap.** The `TH-11` memory wall was 2.81 M cells
> on a *coil* refinement; the phantom here is a few hundred ~1 cm cells inside
> a 116 085-cell mesh, so halving the phantom sizing alone (`phantom_resolution`
> 0.01 → 0.005, ≈ 8× phantom cells) adds **≈ 5–10 k cells**, not millions, and
> the four-drive sweep stays standard tier (`PORT-11` step 1 priced 116 k
> cells at ≈ 25 s/solve at `-n 2`; budget ≈ 150 s for four solves + six
> restricted mass solves, `timeout -k 30 600`). Execute after step 3e′ (they
> answer different axes; if 3e′ printed (α), stop and re-plan instead).
> **Anchors:** (i) the coil-side records must not move — gate (i) power
> accounting and the `|B₁⁺|` C4 identities reproduce at `CG1_RECORD_RTOL`
> on the new mesh (they are mesh-converged at the ~2% floor; a move > 0.5 pp
> is a fixture finding); (ii) the restricted estimator's best-approximation
> inequality and exact-reproduction control hold on the new mesh (≤ the
> 18.7238% / 1e-10 records); (iii) the five SAR identities off the
> restricted `E` are **printed, not gated**, with the verdict pre-registered
> here: **(a)** all five ≤ 5% ⇒ (c) confirmed, and the daily review may then
> register the coil-driven SAR gate on the restricted estimator at the finer
> rung — the first coil-driven SAR gate in the repo; **(b)** they fall but
> stay > 5% ⇒ report the ratio (one halving should roughly quarter a
> second-order residual, 6–9.5% → 1.5–2.5%; a ratio near 1 says h is not the
> mechanism either) and stop; **(c)** unchanged ⇒ neither degree nor h — a
> review re-reads the identities themselves. **Negative control:** both
> step-3b controls asserted to survive on the new mesh. Scope: one rung on
> F-small at 10 MHz; no band moves in-slot; `WF-6` stays 🟡 whatever prints.
> Negative result: the printed verdict is the deliverable — journal, stop.
>
> **Annotation, 2026-09-02 03:00 daily review — the knob named above does not
> exist yet, so step 3f is not queueable as written.** `birdcage_port_domain`
> (`src/fem_em_solver/io/mesh.py:3069`) takes one global `resolution`
> (0.015, a gmsh `setSize` everywhere) and an optional `conductor_resolution`
> Threshold field; `phantom_resolution` is a parameter of the *coil+phantom*
> family's `coil_phantom_region_resolution_policy` (`mesh.py:2378`), not of
> the birdcage constructor, and `build_four_port_sweep` reaches the mesh only
> through `tests/mesh/test_birdcage_port_sheets._build`, which passes the
> module constants `RESOLUTION` / `CONDUCTOR_RESOLUTION` and nothing else. The
> phantom's ~1 cm cells are simply the global 0.015 (537 cells in a
> π·0.03²·0.08 m³ cylinder ⇒ h ≈ 1.5 cm). Halving the *global* resolution
> would refine air and coil too and is not the cheap rung the weekly costed.
> **Step 3f₀ (scoped by this review, §9 item 4)** adds the knob:
> `phantom_resolution: Optional[float] = None` on `birdcage_port_domain`, a
> gmsh Constant/Box field over the phantom cylinder taken into the existing
> `Min` of size fields, and a `phantom_resolution=` passthrough on `_build`
> and `build_four_port_sweep` — mesh-only, real mode, with the no-op control
> as the anchor (parameter absent ⇒ the 116 085-cell mesh reproduces at
> 0.000e+00). Step 3f then runs at `phantom_resolution=0.0075` (one halving,
> ≈ 8× ⇒ ≈ 4 300 phantom cells, +≈ 4 k cells overall, inside the weekly's
> 5–10 k budget) and is serial on 3f₀ **and** 3e′ (§9 item 7). The
> weekly's "0.01 → 0.005" is re-read as "0.015 → 0.0075"; the cost estimate
> and the pre-registered (a)/(b)/(c) verdict are unchanged.
>
> **Step 3f₀ ✅ 2026-09-02, 09:00 slot — the knob exists, its `None` path is a
> measured no-op, and step 3f's mesh is priced.** `phantom_resolution:
> Optional[float] = None` on `birdcage_port_domain` (`io/mesh.py`) and on
> `_build_birdcage_port_model`: a gmsh `Box` field over the phantom's own
> bounding box (`VIn = phantom_resolution`, `VOut = resolution`, margin
> 1e-3 of the extent, `Thickness = 0`) combined with the existing conductor
> `Distance→Threshold` through a new `Min` field. The conductor branch is
> otherwise untouched (the `GEO-21` 4.8 mm floor ruling), and with one field
> in the list the tail reduces to the single `setAsBackgroundMesh(threshold)`
> this code has always made, so `None` creates **no field at all**. Additive
> `phantom_resolution=` passthroughs on `tests/mesh/test_birdcage_port_sheets.
> _build` and `…test_port_birdcage_four_port.build_four_port_sweep`
> (`frequency_hz` / `reuse` precedent; ignored under `reuse`, which builds no
> mesh). New module `tests/mesh/test_birdcage_phantom_resolution.py`, `1
> passed in 83.94s`, `-n 2` real, standard tier, harness elapsed **86 s**,
> Status 0 (`20260902T140410Z_WF-6-step3f0.log`) — three builds, ≈ 24–25 s of
> gmsh each. **Every pre-registered anchor met.** *(i) The no-op control, the
> anchor:* parameter absent ⇒ **116 085** cells and **537** tag-3 cells, both
> at **0.000e+00** relative to the record, asserted at exact equality — no
> existing record, gate or example moved. *(i′) Negative control:*
> `phantom_resolution = 0.015`, equal to the global sizing, gives **116 085 /
> 537** as well, so gmsh is not honouring the field's mere presence. *(ii) The
> knob turned:* at `phantom_resolution = 0.0075` the tag-3 count goes **537 →
> 2 746 = 5.1136×** (band [5, 12] around the (h/hₚ)³ = 8× prediction — the
> shortfall is the Box's sharp transition and Netgen's optimise pass, not a
> mis-sized field) with the cells *outside* tag 3 moving **1.9083%** (ceiling
> 10%): total **116 085 → 120 499**, i.e. **+4 414 cells**, inside the
> weekly's 5–10 k budget and confirming step 3f stays standard tier. *(iii)
> Scale-free CAD identities on the refined mesh:* `GEO-18` sheet area
> **1.120000000e-04 m² on all four ports** (1e-9 band) and the `GEO-19`
> partition + air-box closure **1.000000000000**, on the negative control too;
> the cell-tag set is unchanged. Tag-3 counts are `size_local`-restricted and
> `MPI.SUM`-reduced (the reason for `-n 2`). No default moved, no band
> touched, nothing solved; `WF-6` stays 🟡. **Step 3f is unblocked on the mesh
> side** and remains serial on step 3e′.
>
> **Rulings of the 2026-09-02 10:30 review on steps 3e′ and 3f₀, and step 3g
> scoped.** *(1) Step 3e′'s clause (γ) is read as the run read it, not as it
> was written:* the CG2 restriction is not mis-assembled (every anchor green
> with orders of room), and what the rung measured is that a better L² fit
> of `E` over the phantom is *pointwise worse* at the 51 sample points.
> With the projector (3b/3c) and the degree (3e′) both excluded, the
> remaining candidates are mesh `h` and the construction itself — reading a
> quadratic-in-`E` identity from a fitted field at points inherits the fit's
> pointwise error, which no norm bound controls. **Ruling: run step 3f
> anyway (it is now unblocked on both halves and is queued first), and read
> its verdict knowing a better-resolved `E` can raise these numbers; and
> scope the integral-form construction as step 3g, independent of 3f and
> on the coarse mesh.** *(2) Step 3f₀'s 5.11× growth against the naive 8×*
> is accepted as measured: the band held, the CAD identities held, and the
> outside-tag-3 change was 1.9%; a thicker transition would buy cells, not
> information. Step 3f's expectation is re-recorded from 3f₀'s measurement
> — **2 746** phantom cells, 120 499 total — and no field parameter moves.
> *(3) Step 3f's anchor (ii) is sharpened, not loosened:* the weekly's
> "residual ≤ 18.7238%" compared two different meshes' primal fields and is
> not a theorem; the theorem is the same-mesh best-approximation inequality
> (restricted residual ≤ the global fit's residual on the *new* mesh), which
> is what is asserted, with the 18.7238% comparison printed.
>
> **Step 3g scoped 2026-09-02 10:30 review — the integral-form SAR
> identities, off the primal field, no estimator.** Let the coil axis be
> `z` and `θ_j = jπ/2`. Define the smooth azimuthal partition of unity
> `w_j(x) = ((c_j + √(c_j² + ε²))/2)²` with
> `c_j = (x cos θ_j + y sin θ_j)/√(x² + y² + ε²)`, `ε = 1e-9 m` — at each
> point only two adjacent `w_j` are non-zero and they sum to
> `cos² + sin² = 1`, so `Σ_j w_j = 1` identically and `w_{j+1}(x) =
> w_j(R⁻¹x)` exactly under the 90° rotation `R` (the regularised-`sqrt`
> form exists because `ufl.max_value` is the `OPS-22` complex-build trap).
> Read `P_j^{(k)} = ½ ∫_{dx(3)} σ w_j |E^{(k)}|² dx` for the four single
> drives `k` and the four quadrants `j` — sixteen cell integrals of the
> **primal** N1curl `E`, `assemble_scalar` reduced with `MPI.SUM`,
> `quadrature_degree` pinned — plus the same four integrals for the
> step-2 quadrature drive. **Anchors, asserted:** (i) the partition
> identity `Σ_j P_j^{(k)} = P_phantom^{(k)}` at rtol 1e-10 for every drive,
> with the gate-(i) drive's total reproducing the record **5.637745667e-08
> W** at `CG1_RECORD_RTOL` — an exact identity of the construction, so a
> miss is a defect in the integrals; (ii) the negative control — pairing
> quadrant `j` under drive `k` with quadrant `j+2` (180°) under drive `k+1`
> — reads *strictly larger* than the C4 pairing `j+1` for every `k`
> (an ordering, no factor: nobody has measured this ceiling), ratio
> printed. **Printed, not gated, verdict pre-registered:** the twelve C4
> pairs `|P_{j+1}^{(k+1)} − P_j^{(k)}| / P_j^{(k)}` (rotation sense taken
> from the pairing that made `test_birdcage_sar_map`'s `|B₁⁺|` gate green,
> never re-derived in-slot) and the quadrature drive's four-quadrant
> spread: **(a)** all ≤ 5% ⇒ the integral construction is the gateable one
> and a review registers the first coil-driven SAR gate on it; **(b)**
> between 5% and the pointwise primal 25–41% ⇒ report; **(c)** at or above
> the pointwise readings ⇒ the sample set was not the mechanism and the
> phantom's `h` is the last candidate standing (3f decides). Standard,
> `-n 2` complex, four solves and no mass solves ⇒ ≈ 100–125 s (3e′'s 125
> s carried six mass solves), `timeout -k 30 600`; new module
> `tests/validation/test_birdcage_sar_integral.py` importing the sweep
> builder, so its window can exit 0 beside the five primal reds. Scope:
> C4 only, no mirror identity, no band, no gate, no SAR claim, `WF-6`
> stays 🟡. Negative result: journal the verdict here and in the
> known-issues step-3d row, keep every assert, stop.
>
> **Rulings on the two rungs the 10:30 review carried to this weekly:** the
> *absolute-convergence rung* (an h-ladder for the `|B₁⁺|` map itself) is
> **deferred behind step 3f** — it turns the same knob, and 3f's anchor (i)
> is its first data point for free; scope it only if (i) moves. A `MAG-20`
> third rung is **killed** (epitaph in §10): Phase 1 is closed and a sharper
> magnetostatic rate is not on the mission's path this quarter.
>
> **Step 3f executed 2026-09-02 15:00 slot — the finer-phantom rung prints
> (a), and the coil-side anchor it was given goes red in the favourable
> direction.** New module `tests/validation/test_birdcage_sar_fine_phantom.py`
> runs the whole four-drive sweep through
> `build_four_port_sweep(phantom_resolution=0.0075)` — no `reuse=`, which
> hands back the coarse mesh — and re-reads every column of step 3e on it.
> `20260902T170559Z_WF-6-step3f.log`, **`3 failed, 27 passed` / Status 1 /
> 175 s** at `-n 2` complex with `tests/environment`, standard tier against
> the item's 150–200 s estimate; a collect-only smoke ran first
> (`20260902T170546Z_WF-6-step3f-collect.log`, 19 items, 5 s).
>
>   * **(iii) The knob reached the constructor**, asserted at exact equality:
>     **120 499** cells, **2 746** tag-3 cells, reproducing step 3f₀'s
>     measurement (coarse 116 085 / 537, **5.1136×** the phantom cells).
>   * **The deliverable — the five identities off
>     `post.project_to_cg1_restricted` (degree 1), printed not gated:
>     3.3600 / 3.4442 / 3.4525 / 3.0332 / 2.5465%** against the coarse mesh's
>     8.2868 / 9.4743 / 7.3477 / 6.8146 / 6.1185% — **−4.93 / −6.03 / −3.90 /
>     −3.78 / −3.57 pp, ratios 0.4055 / 0.3635 / 0.4699 / 0.4451 / 0.4162**
>     (mean **0.42** against the 0.25 a purely second-order residual would
>     give for one halving of `h`). All five are **inside** the imported,
>     unmoved 5% band, so the pre-registered clause evaluates to **(a)**:
>     **verdict (c)'s attribution to the phantom's ~1 cm cells is confirmed**,
>     the mechanism the projector (3c) and the estimator's degree (3e′) were
>     both excluded from. Both negative controls survive and are asserted —
>     mis-rotated **121.0800%**, quadrature-vs-single-drive **384.1297%**
>     (coarse 123.6255 / 333.0778%).
>   * **(ii) The estimator is still an estimator on the new mesh**, every
>     anchor green: the **same-mesh** best-approximation inequality
>     **12.5225% ≤ 1626.2098%** over the same phantom cells (129.86×, both
>     measured in this run — the 10:30 review's sharpening; the coarse
>     18.7238% is printed beside it, not asserted), `a + b × x`
>     **9.947634e-13** with `x² ê_x` at **2.142147e-01**, pinned max |value|
>     **0.000e+00** over owned *and* ghost blocks (**722** free of 22 147
>     owned CG1 blocks, **66 441** dofs, vs the coarse 170 / 21 397 / 64 191),
>     all six restricted solves reason **2** in 20–25 its. Restricted phantom
>     power **5.499426495e-08 W**, **−1.5681%** from this mesh's primal
>     5.587038273e-08 W (coarse: −3.5058%).
>   * **(i) Gate (i) is unmoved and gate (ii)'s anchor is not.** The power
>     accounting closes at **9.795780e-03** / **9.796465e-03** inside the
>     unmoved 1e-2 band (the P1 figure agreeing with the coarse record
>     9.795751e-03 to 3e-6 relative), conductor-drop control 7.52e-02. But the
>     three CG1 `|B₁⁺|` C4 identities read **0.6177 / 0.5966 / 0.5647%**
>     against their records 2.1870 / 2.1146 / 1.8911% — **−1.5693 / −1.5180 /
>     −1.3264 pp**, outside the pre-registered **0.5 pp** ceiling, so the three
>     parametrised asserts are **red on `main`** with a known-issues entry, per
>     the item's own "a larger move is a fixture finding" clause. The move is
>     an **improvement** (4× further inside the 5% band, control still at
>     25.4563%), so gate (ii) is not invalidated — what is invalidated is the
>     claim that 2.19% was a *converged* floor with 2.3× of headroom. **This is
>     the deferred absolute-convergence rung's first data point, arriving for
>     free exactly as the weekly said it would**, and its disposition (re-read
>     the anchor one-sided / run step 1c's ring-set control on this mesh /
>     a third rung at 0.00375) is a **review's**, not a slot's.
>   * **Caveat the module prints and no one should read past:** the sample set
>     is the mesh's own tag-3 centroids, so it grew **51 → 373** points with
>     the refinement; `h` and the sample set moved together. Step 1c
>     separated them for the coarse DG0 `|B₁⁺|` column (±2 pp, centroid vs
>     rotation-invariant ring set) and found the set was not the mechanism,
>     which is why this is read as an `h` rung — but a review minded to
>     register the SAR gate on clause (a) should want that control re-run on
>     this column first.
>   * **Scope, observed:** no band moved, no tolerance moved, **no SAR gate
>     registered**, no homogeneity / absolute / C95.3 claim, the five primal
>     asserts in `test_birdcage_sar_map.py` untouched and still red, nothing
>     under `src/`, and **`WF-6` stays 🟡**. Registering the first coil-driven
>     SAR gate in the repo — on the restricted estimator at this rung, with
>     this table as its provenance — is now a live and evidenced option for a
>     review, and it is the only thing clause (a) authorises anyone to
>     consider.
>
> **Step 3g executed 2026-09-02 16:30 slot — every anchor green on the first
> run, and the pre-registered clause that prints is (a): the *construction*
> was the mechanism.** New module `tests/validation/test_birdcage_sar_integral.py`,
> `build_four_port_sweep()` at the **default** resolution (116 085 cells —
> deliberately step 3's own mesh, so "integral vs pointwise" is the only thing
> that differs from step 3's window and the rung is independent of 3f), four
> curl-curl solves and **no** mass solves.
> `20260902T213441Z_WF-6-step3g.log`, **`20 passed` / Status 0 / 106 s** at
> `-n 2` complex with `tests/environment` first, standard tier against the
> item's 100–125 s estimate; a collect-only smoke ran first
> (`20260902T213431Z_WF-6-step3g-collect.log`, 9 items, 4 s).
>
>   * **The deliverable — the twelve C4 pairs `|P_{j+1}^{(k+1)} − P_j^{(k)}| /
>     P_j^{(k)}`, printed not gated: 0.7149 / 1.1908 / 1.4417 / 0.9703 |
>     1.5200 / 0.2132 / 0.3377 / 0.9086 | 1.0569 / 0.8355 / 0.2780 / 0.2302%**
>     (means 1.0794 / 0.7449 / 0.6002%, worst **1.5200%**) — **all twelve
>     inside the unmoved imported 5% band**, against the pointwise primal
>     column's 25.11–40.55% and the pointwise *restricted-estimator* column's
>     6.1–9.5% on this same coarse mesh. The pre-registered clause is
>     therefore **(a)**. The quadrature drive's four-quadrant spread is
>     **0.4641%**.
>   * **(i) The partition identity is exact.** `Σ_j P_j^{(k)}` reproduces
>     `P_phantom^{(k)}` to every printed digit for all five drives (asserted at
>     rtol 1e-10): 5.637745667e-08 / 5.630901879e-08 / 5.646798644e-08 /
>     5.621308271e-08 W for k = 0…3 and 3.796523707e-07 W for the quadrature
>     drive. The gate-(i) drive's total is **5.637745667e-08 W** — step 1's
>     record reproduced **digit-for-digit**, not merely inside
>     `CG1_RECORD_RTOL`, which ties these twenty integrals to step 1's gated
>     three-way power accounting on the same solve, measure and σ.
>   * **(ii) The mis-paired (180°) control is asserted and enormous**:
>     **96.1655 / 97.4944 / 95.5869%** against the C4 means, ratios
>     **89.09× / 130.89× / 159.27×**. The ordering the item asked for holds by
>     two orders of magnitude, so the twelve readings above are not passing on
>     an azimuthally structureless map.
>   * **What this measures, stated narrowly.** Steps 3c / 3e′ / 3f excluded the
>     projector, the estimator's degree and (3f) implicated `h`. This rung
>     shows the *fourth* candidate — reading a quadratic identity from a field
>     at sampled points, which inherits the pointwise error squared — is worth
>     4–6× on this fixture at **fixed** `h`: the same four solves that read
>     25–41% pointwise and 6.1–9.5% through the best available estimator read
>     **≤ 1.52%** as integrals, with no estimator in the path at all. 3f's `h`
>     finding is not contradicted (it is a different knob on a different mesh);
>     what is new is that the coarse mesh was never the binding constraint for
>     an *integral* statement.
>   * **Scope, observed:** C4 only — no mirror identity, no band moved, no
>     tolerance moved, **no gate registered**, no §2 claim, no homogeneity /
>     absolute / C95.3 claim, the five primal asserts in
>     `test_birdcage_sar_map.py` untouched and still red, nothing under `src/`,
>     and **`WF-6` stays 🟡**. Registering the first coil-driven SAR gate on
>     the *integral* construction is a **review's** ruling and clause (a) is
>     its evidence; it is the only thing this run authorises anyone to
>     consider.
>
> **Ruling, 2026-09-02 18:00 review — the integral construction is the one
> the repo gates; the pointwise five become records; the `|B₁⁺|` reds get
> their control.** Two constructions printed (a) today and the review had to
> pick one. **Step 3g's integral construction wins**, for three reasons that
> do not depend on its number being smaller: (1) it is a statement about the
> **primal** field — no estimator, no projector, no sample set in the path,
> so none of the three mechanisms steps 3b–3e′ spent five slots excluding can
> re-enter; (2) its partition identity is an **exact** anchor of the
> construction (`Σ_j P_j = P_phantom` to every digit), so a broken integral
> cannot hide behind a physics band; (3) it is cheaper by a whole mesh (106 s
> on the coarse fixture, four solves, no mass solves). Step 3f's
> pointwise-restricted 2.5–3.5% is **corroboration** — it says the same
> physics converges toward the same identity under `h` — but it carries the
> caveat its own module prints (51 → 373 centroids moved with `h`) and a
> 1.6× larger worst case on a mesh that costs 175 s. **What this ruling does
> to the five pointwise primal asserts** in `test_birdcage_sar_map.py`
> (`test_single_drive_sar_map_is_c4_covariant` ×3,
> `test_quadrature_sar_map_is_c4_invariant`,
> `test_reversing_the_rotation_sense_equals_reflecting_the_sar_map`): they
> assert a 5% band on a quantity the repo has now measured, through six rungs
> (3b/3c/3d/3e/3e′/3g), to be the *wrong statement* of the identity — a
> quadratic in `E` read at points inherits the pointwise error squared. They
> are **re-stated as record reproductions** of the `STEP3_PRIMAL_*` values
> (rtol 1e-3, the same licence step 3b used when it exported them), labelled
> in the docstring as the pointwise floor, with the 5% band **removed from
> those five and not moved anywhere**. This is not the loosening §7 forbids:
> the bound is not widened on the same quantity, the quantity is retired as a
> gate with its measurement kept, and the gate moves to the construction the
> identity is actually a theorem about. The two pointwise negative controls
> stay asserted `> band` exactly as they are (they still separate). **Step
> 3h** (§9 item 1) does exactly this and registers the twelve integral C4
> pairs at the unmoved imported 5% band, worst measured 1.5200% (3.3×
> headroom — *not* claimed converged: 3f just showed a "converged ~2% floor"
> claim on this fixture does not survive one `h` rung, so 3h states the
> headroom as measured-at-fixed-`h`, and step 3f′ prints the integral pairs
> on the 0.0075 rung beside it). **On the three `|B₁⁺|` reds** (3f's
> known-issues entry, options 1–3): option (2) is taken — the ring-set control
> is the one thing that answers both 3f caveats at once (does the sample set
> or `h` move the `|B₁⁺|` identities; does it move the SAR column) and it is
> a `_ring_points` call the repo already has. **Step 3f′** (§9 item 2) runs
> it on the 0.0075 mesh, re-reads anchor (i) **one-sided** (an identity may
> not get *worse* than its coarse record by more than 0.5 pp; getting better
> is the convergence measurement it is) and re-records the fine-rung `|B₁⁺|`
> figures as a second-rung record beside the coarse ones, never replacing
> them. Option (3), a 0.00375 rung, is **not** queued: 3f₀ priced one halving
> at +4 414 cells and 5.1× the phantom, so the next halving is ≈ 8× the tag-3
> cells again and needs a cost probe before anyone lists it — the weekly's
> call. Neither step moves a band. **Registering the gate is 3h's and only
> 3h's; if 3h's first window shows any integral pair above 5% on the same
> mesh that read 1.52% today, that is a stop, not a re-band.**

> **Ruling, 2026-09-03 03:00 review — one gate, a second identity on it,
> and the empty one named.** Both items landed green (3h `109 passed` /
> 194 s, 3f′ `54 passed` / 117 s) and 3f′'s slot asked whether the
> restricted-CG1 estimator's 3.36–2.55% at the 0.0075 rung, now with a
> ring-set control behind it, earns a *second* SAR gate. **No.** The gate
> is the statement the identity is a theorem about — quadrant powers of the
> primal field — and a second gate on an estimator-mediated pointwise
> quantity would re-admit exactly the three mechanisms (projector, degree,
> sample set) that six rungs spent excluding; the estimator figures stay
> asserted records in `test_birdcage_sar_fine_phantom.py`, which is where a
> future change to `project_to_cg1_restricted` will show. What the integral
> construction *can* still carry is the **mirror identity** step 3 retired
> from the pointwise map: on drive `k` the mirror through the coil axis and
> the port's azimuth fixes quadrants `k` and `k+2` and swaps the flanks, so
> `P_{k−1}^{(k)} = P_{k+1}^{(k)}` — and 3h's own table
> (`20260903T003309Z_WF-6-step3h.log:4682–4685`) already gives the four
> readings, **1.7527 / 1.5261 / 0.3438 / 0.9563%**, against a
> flank-vs-opposite control of **37.8–39.0%** (≥ 21× separation). **Step
> 3i** (§9 item 2) asserts those four at the unmoved 5% band on the same
> four solves. The ccw/cw quadrature mirror identity as quadrant integrals
> is **not** queued and should not be: on a C4-symmetric partition the
> quadrature quadrant powers agree to 0.4641% under *any* pairing, so the
> ceiling rubric says no control can separate a right pairing from a wrong
> one at a 5% band — an identity that cannot fail is not a gate. No
> convergence language enters §2 from 3f′; it is one `h` data point on a
> gate that is stated at fixed `h`.

> **Steps 4a / 4 — the B1+ closed-form gate (the weekly's 2026-09-06 §10
> target, split by the 18:00 daily review, ruling (4)).** The weekly
> wrote the target as *N infinitely long line currents*; on F-small
> (`coil_length` 0.14 m, `ring_radius` 0.07 m) the finite-length factor
> at the centre plane is `L/√(L² + 4R²)` = **0.7071**, so the 2D form
> misses the centre field by 29% and cannot anchor a ~2% band. The
> closed form is therefore the Biot–Savart superposition of **finite
> legs plus ring arcs**, still "evaluated numerically rather than
> transcribed". **Step 4a (§9 item 5, smoke, pure numpy, no FEM):**
> `utils.analytical.birdcage_filament_field(points, *, ring_radius,
> coil_length, leg_currents, ring_currents=None)` — finite segments in
> closed form, arcs by Gauss–Legendre, ring-arc currents from Kirchhoff
> with zero mean (raise unless `Σ I_n = 0`); gated on exact identities:
> the infinite-line limit against the imported
> `straight_wire_magnetic_field` (1e-5 at `L = 10³R`), the ring limit
> against the imported `circular_loop_magnetic_field_on_axis` (1e-10),
> `∇·B = 0` at 1e-8 for the closed mode-1 circuit with the ring-less
> pattern as the ≥ 100× control, C4 covariance at 1e-12, the 0.7071
> factor at 1e-6, and the mode-2 (`cos 2φ_n`) centre field exactly zero —
> step 4's negative control, closed-form side. **Step 4 (queued by the
> review after 4a lands):** one unloaded F-small sweep (phantom σ = 0,
> εᵣ = 1) on `birdcage_port_domain`, the quadrature `|B₁⁺|` radial
> profile at r ≤ 0.5 R against 4a's function with the leg current read
> from the FEM's driven-sheet current, asserted within the CG1 band `WF-6`
> measured (≈ 2%), the loaded map's profile printed beside it never
> asserted, the mode-2 drive as the ≥ 10× control (rule (e): asserted
> for its sign — the closed form is exactly zero — predicted for its
> size). Standard tier, `-n 2`, the 116 085-cell fixture. No homogeneity
> or literature claim enters §2 from either step.
>
> **Step 4 — scoped 2026-09-07 10:30 review (§9 item 3), with step 4a's
> correction (1) built in: on F-small the end rings contribute exactly
> `R²/ρ² = 0.5` of the legs' own centre field (`−μ₀IRh/(πρ³)`,
> `20260907T123926Z_WF-6.log:51`), so the anchor is the full
> `birdcage_filament_field` (legs + rings) and a legs-only comparison
> reads ~33% low by construction.** New module
> `tests/validation/test_birdcage_b1_plus_closed_form.py`. **Fixture:**
> `build_four_port_sweep` gains one additive keyword
> `phantom_material=None` (default: today's saline; rule (c), gate module
> re-run green in the same slot); the unloaded sweep passes
> `HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0)` on the same
> 116 085-cell mesh at 10 MHz. Four single-drive solves through the map
> module's `_solve_driven` (fields + `sheet_terminal_current` per sheet),
> the quadrature weights through `ports.superpose_drives` (`POST-6`), the
> superposed leg currents by the same linearity, `I_w,j = Σ_k w_k I_j^(k)`,
> projected onto zero mean before they enter the closed form
> (`|mean I| / max|I|` printed — predicted the C4-spread class ~1e-2,
> never asserted; 4a raises on a non-zero sum). **Anchor (asserted):** the
> CG1 `|B₁⁺|` of `WF-6` step 1b's estimator at eleven points in `z = 0` —
> `r = 0, 0.1R … 0.5R` along `x̂`, and `0.1R … 0.5R` along `ŷ` — against
> `|B₁⁺|` of `birdcage_filament_field(points, ring_radius=0.07,
> coil_length=0.14, leg_currents=I_w)` (both `(B_x + jB_y)/2`), every
> point inside a new pre-registered `CLOSED_FORM_BAND = 5.0e-2` —
> predicted 2–3% (the CG1 map's own C4 record 0.9818%, the filament vs
> the 2.5 mm wire ≈ (a/d)² ≲ 0.5% at `r ≤ 0.5R`, and the terminal-vs-
> volume current split the two-torus measured at 2.2%), the worst point
> printed. **Negative controls (rule (e) labels):** (α) the legs-only
> closed form (`ring_currents` forced to zero) misses the FEM centre
> field by more than `CLOSED_FORM_BAND` — **asserted** for its sign,
> backed by 4a's exact identity at `…123926Z:51`; size **predicted**
> ~33%, printed; (β) the mode-2 drive `w = (1, −1, 1, −1)` — the closed
> form's centre `B₁⁺` is exactly zero (4a's (vi)), so the FEM's mode-2
> centre `|B₁⁺|` is **asserted** ≤ `CLOSED_FORM_BAND` × the mode-1 centre
> value; size **predicted** ~1e-2, ratio printed. The loaded (saline)
> profile at the same points is printed beside the unloaded one, never
> asserted. **Tier / ranks / cost:** four unloaded + four loaded solves on
> 116 085 cells — `MAT-4` step 4 measured 132 s for four solves at `-n 4`
> on the 120 499-cell rung (`20260907T003548Z_MAT-4-step4.log:2260`) ⇒
> one window `-n 4`, `timeout -k 30 600`, heavy by ceiling, ≈ 270 s
> class; the gate re-run `test_port_birdcage_four_port.py` at `-n 4`,
> `timeout -k 30 400` (the same four solves, ≈ 115 s class per
> `20260907T140233Z_MAT-4-step4-rerun.log`). **Traps already paid for:**
> the leg azimuths and the leg-current sign are conventions — assert first
> that the generator's leg azimuths (`tests/mesh/test_birdcage_port_tags.py`,
> the constants 4a imported) equal 4a's `2πn/N` up to one common offset,
> and rotate the evaluation points, never the currents, if they differ;
> the sheet's terminal current is signed along the sheet's drive direction
> — map it to "+ẑ along the leg" explicitly; the port gap is bridged by
> the sheet's own surface current, so the closed form's leg is the full
> `coil_length`, not the leg minus the gap (an 8 mm gap at the centre
> plane is ~8% of the centre field — dropping it is the first wrong
> answer); `evaluate_vector_field_parallel` is a collective over an
> identical point list on every rank; `assemble_scalar` is rank-local;
> `-k a or b`; complex build + `FEM_EM_REQUIRE_COMPLEX=1`,
> `tests/environment` first; no `run_in_background`. **Scope:** the
> closed-form gate at the centre plane of the *unloaded* coil at 10 MHz,
> fixed `h`, CG1 — no homogeneity, CV, literature, absolute or Larmor
> claim; `WF-6` stays 🟡 (its homogeneity target is still open); §2's B₁⁺
> row gains one clause, "closed-form-gated at the centre plane of the
> unloaded coil", only when this lands. **Negative result:** the centre
> point missing by > 50% is a convention error — re-check azimuths and
> sign before anything is committed (4a's (v) clause); the centre inside
> the band with `r = 0.5R` outside is a statement about the CG1 map at
> the wire's near field — known-issues with the eleven-point table, park,
> stop; the centre missing with conventions verified is the finding that
> the FEM's leg current is not the filament's (non-uniform along the
> conductor) — known-issues, park, stop. `CLOSED_FORM_BAND` is never
> widened.
>
> **Step 4 executed 2026-09-07 15:00 slot — the third pre-registered exit
> fired, and the run's own control names the mechanism more precisely than
> the exit did.** `11 failed, 16 passed` / Status 1 / **93 s** at `-n 4`
> complex (`20260907T200630Z_WF-6.log`, wrapped `timeout -k 30 570`,
> collect-only smoke first at `…200619Z`, 16 items, 5 s). The eleven
> centre-plane points miss the unmoved `CLOSED_FORM_BAND = 5.0e-2` at
> **26.6201% (centre) / 26.2742 / 26.4648 / 24.5583 / 21.6815 / 19.4760
> (+x̂, r = 0.1R…0.5R) / 26.9033 / 27.3560 / 24.9922 / 21.2489 / 16.7641
> (+ŷ)** — FEM centre **8.097478100e-08 T** against the closed form's
> **1.103500413e-07 T** (`:1924–1934, :2499–2520`). **The band was not
> widened and nothing landed on `main`.** *Exit 1 (a convention error) is
> excluded by the run itself:* the fixture's leg azimuths are
> **360.0000 / 90.0000 / 180.0000 / 270.0000 deg**, the closed form's
> `2πn/N` lattice up to one common offset whose spread over the four legs
> is **0.000e+00 deg** (`:1919–1920`); every sheet's `drive_direction` is
> asserted `(0, 0, 1)`, the closed form's `+ẑ` leg convention; and control
> (β), the mode-2 drive, is **green** at **7.743627e-03** of the mode-1
> centre against 5.00e-02 (`:1938`) — the FEM reproduces step 4a's exact
> centre zero, so it is tracking the closed form's *structure*. *What the
> miss is:* control (α) reads the legs-only closed form at
> **7.356669419e-08 T**, so the filament's Kirchhoff rings add exactly
> **50%** at the centre (step 4a's `R²/ρ² = 0.5`) while the FEM's coil adds
> only **10.07%** — **FEM/legs-only 1.1007 against the filament's 1.500**,
> the FEM sitting far closer to an *open* coil than to a closed one. The
> four superposed leg currents are equal to four digits
> (1.820730e-02 / 1.820756e-02 / 1.820518e-02 / 1.820726e-02 A, `:1921`),
> so the terminal leg current is not the discrepancy; the **ring** current
> the FEM's coil carries is ~5× below `cumsum(I) − mean(cumsum(I))` on
> those same currents, and that is the next measurement. Rule (c) held: the
> additive `phantom_material` keyword is a no-op on the gate module,
> `5 passed / 44.01 s` at `-n 4`, Status 0, 46 s
> (`20260907T200858Z_WF-6.log:84, 96–97`). **No absolute `|B₁⁺|` claim
> exists, §2's B₁⁺ row does not gain the authorized clause, and `WF-6`
> stays 🟡** — the chunk's existing gates are symmetry identities, every
> one of them invariant to a uniform 27% scale, which is why this
> comparison was scoped in the first place. Parked on
> `attempt/WF-6-step4-20260907T205600Z` (`499c527`), known-issues entry
> filed, §9 item 3 marked 🚫 in the same commit (rule (d)). **Sizing
> correction:** the item's "four unloaded + four loaded solves" missed that
> `build_four_port_sweep` runs its own four-drive S-parameter sweep before
> the module's four field solves, so each rung costs **eight**; the loaded
> print sits behind `WF6_STEP4_LOADED` (default off) and was not solved.
>
> **Ruled 2026-09-07 18:00 review — the comparand was wrong twice, both
> errors the 10:30 review's, and together they account for the miss to
> first order; the ring current is not implicated by anything measured.**
> *(1) The rings are not where the closed form was told.* `birdcage_port_domain`
> places the end rings at `z = ±leg_spacing/2 = ±55 mm` (`io/mesh.py:3772,
> 3821`) and the legs run the full `coil_length`, `±70 mm`, with 15 mm
> dead-end stubs beyond each ring (`:3858`); the item passed
> `coil_length=0.14`, so the filament had its rings at ±70 mm and its
> current-carrying legs 27% longer than the fixture's. With the rings at
> ±55 mm the legs' centre field is 0.874 of 4a's value and the rings are
> `R²/ρ² = 0.618` of *that* (not 0.5): the free-space form's 1.50 L
> becomes **1.414 L**. *(2) The coil is not in free space.* The generator
> closes the air in a **PEC** box (`:4092–4101`) of half-extents
> `ring_radius + max(leg_radius_eff, ring_minor_radius) + port_dy +
> air_padding` radially and `max(coil_length/2, …) + air_padding`
> axially — with `AIR_PADDING = 0.03`, about ±0.11 m in x, y and
> ±0.10 m in z, so the rings sit **4.5 cm** from the end walls and the
> legs **4 cm** from the side walls. At 10 MHz the box is ≪ λ and a PEC
> wall imposes `B_n = 0`: every current has an image of equal magnitude
> with tangential components reversed and normal components kept. First-
> order images at the centre, from the same segment and arc formulas 4a
> asserted: each ring's near end-wall image cancels 0.45 of it
> (`h′ = 145 mm`, `ρ′³ = 4.2e-3` against `h = 55`, `ρ³ = 7.1e-4`), so the
> rings' 0.54 L become ≈ **0.30 L**; each leg loses 0.26 to its nearest
> side wall and 0.07 to the two perpendicular walls, gains 0.07 from the
> far wall and 0.10 from the end-wall leg images, so the legs' 0.874 L
> become ≈ **0.74 L**; total ≈ **1.04 L** against the measured
> **1.1007 L** (`…200630Z:1937`), the residual being the corner (second-
> order) images, which add. The free-space form at ±70 mm is ~27% above
> what a filament coil in *this* box at *these* ring planes produces, and
> the measured 26.62% deficit is the geometry and the box, not the coil.
> Control (α)'s reading "the FEM's rings add 10%" compared a boxed FEM
> with an unboxed, mis-positioned legs-only form and is not a statement
> about the ring current. **What this does not settle:** the displacement
> current a ~1 V coil pushes into a PEC wall 4 cm away (C ~ 20 pF,
> ωC ~ 1e-3 S, ≲ 6% of the 18 mA leg current) is inside the 5% band's
> margin and unmeasured, so the ring-current measurement the slot asked
> for stays worth one window — as a Kirchhoff check, not as the
> diagnosis. **Disposition (rule (f)):** the comparand is re-registered —
> the same filament form with `coil_length = LEG_SPACING` (the ring
> plane, which is also the current-carrying leg length) summed over the
> PEC box's image lattice, an exact construction for a rectangular box —
> and `CLOSED_FORM_BAND = 5.0e-2` is unmoved, asserted against the boxed
> form (step 4b, §9 item 1); the currents are measured directly (step 4c,
> §9 item 4). Nothing in the run's eleven readings, conventions or
> controls is disputed; 4a's identities stand as free-space identities at
> the `h = R` it was given.
>
> **Step 4b — the boxed closed form at the fixture's ring planes (scoped
> 2026-09-07 18:00 review, §9 item 1).** From
> `attempt/WF-6-step4-20260907T205600Z` (`499c527`) by path checkout onto
> `main` (the module, the four-port keyword, the three logs and their
> `test-results.md` rows). **Add** to `utils/analytical.py` one additive
> function `birdcage_filament_field_in_pec_box(points, *, ring_radius,
> coil_length, leg_currents, box_half_extents, image_order)` returning
> `Σ_{(i,j,k) ∈ [−N, N]³} birdcage_filament_field(points − c_ijk, …,
> leg_currents=P_ij I)` with `c_ijk = (2iX_b, 2jY_b, 2kZ_b)` and `P_ij` the
> leg-current map for the parity of `i` and `j`: an x-mirror sends leg `n`
> (azimuth `2πn/N`) to `N/2 − n mod N`, a y-mirror to `−n mod N`, and each
> mirror negates the currents (`(−1)^{i+j}` overall); a z-mirror changes
> no argument — the end-wall image is the translated coil with kept leg
> currents, and the function's own top/bottom ring convention supplies
> the reversed ring. `(0,0,0)` is the free-space term. **Read the box from
> the mesh, never assume it:** `allreduce` of min/max of `mesh.geometry.x`
> per axis (predicted ±0.11 / ±0.11 / ±0.10); read the ring plane as
> `LEG_SPACING / 2` from `tests/mesh/test_birdcage_port_tags.py` and pass
> `coil_length=LEG_SPACING`. **Anchors (asserted):** (i) the eleven
> centre-plane points against the boxed form at `N = 3`, every point
> inside the unmoved `CLOSED_FORM_BAND = 5.0e-2` — predicted ≲ 3%
> (first-order 1.04 L against 1.10 L measured, the corner images adding);
> worst point printed; (ii) pure-numpy identities on the new function,
> smoke tier `-n 1`: the `N = 0` term equals `birdcage_filament_field` bit
> for bit, and at each of the six wall-centre points the lattice sum's
> normal component satisfies `|B_n|/|B| ≤ 1e-2` at `N = 3` and decreases
> from `N = 2` — the check that the parity map is right (a wrong sign
> gives O(1); the truncation tail bounds it at ~(X_b/2NX_b)³); (iii) 4a's
> module re-run unchanged (4 s). **Controls (rule (e)):** (α′) the
> *original* free-space form at `coil_length = 0.14` misses the FEM centre
> by more than `CLOSED_FORM_BAND` — **asserted**, backed by this run's
> 26.62% (`…200630Z:1924`); the free-space form at `LEG_SPACING` and the
> boxed legs-only form printed beside (predicted 1.414 L and ≈ 0.74 L);
> (β) mode-2 as before, asserted; the lattice drift
> `|B(N) − B(N−1)|/|B(N)|` at `N = 1, 2, 3, 4` printed — the sum is
> conditionally convergent, so the drift is the honest error bar
> (predicted ≤ 1e-2 at `N = 3`; if it exceeds the band's margin at
> `N = 4`, report it as the finding). **Tier / ranks / cost:** the
> unloaded rung measured 93 s at `-n 4` (`…200630Z`, eight solves); the
> lattice sum is 343 filament evaluations at 11 points, seconds ⇒ one
> window `-n 4`, `timeout -k 30 400`; the numpy identities `-n 1` smoke;
> rule (c) for the additive `phantom_material` keyword —
> `test_port_birdcage_four_port.py` at `-n 4`, `timeout -k 30 400`,
> ≈ 46 s (`…200858Z:97`). **Traps:** those of step 4; the image map is a
> permutation *and* a sign — assert `sum(P_ij I) = 0` before each call
> (4a raises otherwise); an x-mirror composed with a y-mirror is the
> rotation by π, so `P_11 I` must equal the currents rotated two legs — a
> free check; the wall `B_n` identity is the one that catches a wrong
> parity; the stubs beyond the rings carry no current and are not in the
> form. **Scope:** closes step 4 with the clause "closed-form-gated at the
> centre plane of the unloaded coil *in its PEC box*" for §2's B₁⁺ row;
> `WF-6` stays 🟡; the landing keeps `attempt/WF-6-step4-…` until step 4c
> lands or parks (4c reads the same branch). **Negative result:** the
> centre inside the band and `r = 0.5R` outside is the CG1 near-field
> statement — known-issues with the table, park, stop; every point still
> ~20% low with the wall identity green is the finding that the box and
> ring planes are *not* the mechanism — known-issues, park, 4c becomes
> the diagnosis, stop. `CLOSED_FORM_BAND` never widens.
>
> **Step 4b executed 2026-09-07 19:30 slot — the 18:00 ruling is confirmed by
> measurement (26.62% → 2.33% at the centre, every predicted comparand landing
> on the nose), and the pre-registered `r = 0.5R` exit fires on one point of
> eleven; the binding uncertainty is now the comparand's own truncation.**
> `20260908T004020Z_WF-6.log`, **1 failed / 15 passed in 68.81 s** at `-n 4`
> complex, elapsed **71 s**, `Status: 1` (`:1881–1909` the table, `:1998` the
> footer); the same module with `tests/environment` at
> `20260908T003808Z_WF-6.log`, **1 failed / 26 passed in 100.06 s**, elapsed
> **102 s** (`:176–177`, `:473`). **Anchor (i):** centre **2.3345%**, `+x̂`
> 2.5175 / 1.3374 / 2.3495 / 3.8483 / 3.5983%, `+ŷ` 1.6429 / 0.1095 / 1.7611 /
> 4.4223 / **7.0875%**; median 2.3495%, worst point [10] = `r = 0.5R` along
> `+ŷ` (`:1889–1900`). Ten of eleven inside the unmoved 5%; **the band was not
> widened and nothing landed on `main`**. **The re-registration is vindicated
> quantitatively:** in units of `L` = the free-space legs-only centre field at
> `COIL_LENGTH` (7.356669419e-08 T), free space at `COIL_LENGTH` reads
> **1.5000 L** (review 1.500), free space at `LEG_SPACING` **1.4140 L** (review
> 1.414), boxed legs-only **0.7321 L** (review ≈ 0.74), boxed legs + rings
> **1.0756 L** against the FEM's **1.1007 L** (review ≈ 1.04 + corners) —
> `:1902–1907`. Control (α′) **asserted green**: the step-4 free-space comparand
> still misses by **26.6201%** (`:1901`), `…200630Z:1924` to the digit, so the
> gate discriminates between the two comparands. Control (β) green at
> **7.743627e-03** (`:1909`). **Three unpredicted readings.** (a) The PEC box
> measured off the mesh is **±0.120 / ±0.120 / ±0.100 m**, not the predicted
> ±0.11 / ±0.11 / ±0.10 (`:1882–1883`); the review's radial arithmetic was 1 cm
> short. (b) **The lattice truncation drift is 4.642e-02 at `N = 3` and
> 3.297e-02 at `N = 4`** against the predicted ≤ 1e-2 (`:1908`) — the
> comparand's own error bar is the size of the band, which the item's clause
> pre-registers as the finding, and a 7.09% point against a ±3–5% comparand is
> not evidence about the FEM. (c) The FEM's own `+x̂` / `+ŷ` pair at `r = 0.5R`
> differ by **3.4%**, a C4 asymmetry of the same order as the miss.
> **Anchor (ii)** (`20260908T003713Z_WF-6.log`, `-n 1`, 1 failed / 9 passed in
> 5.44 s, elapsed 7 s): (ii-a) `N = 0` equals `birdcage_filament_field` bit for
> bit (`np.array_equal`) — green; (ii-b) `P_11 I` = the currents rotated two
> legs, each mirror an involution with zero sum — green; (ii-c) the wall-normal
> identity converges by 9.3× (max **9.990e-02** at `N = 2` → **1.077e-02** at
> `N = 3`, `:60–61`) but lands **above** its pre-registered 1e-2 — the same
> truncation as (b). One disclosed definition correction: the item's literal
> `|B_n|/|B_total|` is degenerate (at the `+ŷ` wall of a mode-1 drive the field
> is purely normal by symmetry and the ratio reads 1.000e+00 at every `N`,
> `20260908T003604Z_WF-6.log:60–61`), so the denominator is the source coil's
> own `N = 0` field and the drive is `(1, 2, −3, 0)`. **Anchor (iii) and the
> rule-(c) window were not run** — the slot ended at the exit. Parked on
> `attempt/WF-6-step4b-20260908T004458Z`; §9 item 1 marked 🚫 in the same
> commit (rule (d)). §2's B₁⁺ row gains nothing; `WF-6` stays 🟡. **What a
> review must rule on next:** the comparand's truncation, not the coil — either
> accelerate the lattice (or raise `N`) until the drift is asserted below the
> band, or re-register the gate as "band + measured drift"; the FEM's own 3.4%
> C4 asymmetry at `r = 0.5R` is a second, independent candidate for the last
> point and `WF-6` step 2's C4 record (0.9818%) is the comparison to make.
>
> **Step 4c — the coil's conduction currents measured, a Kirchhoff check
> (scoped 2026-09-07 18:00 review, §9 item 4).** Independent of 4b (it
> does not consume the boxed form). On `main` if 4b landed, else on the
> branch — `git diff 499c527 main -- tests/validation/test_port_birdcage_four_port.py`
> empty means the keyword landed. New module
> `tests/validation/test_birdcage_conductor_currents.py`: the four
> unloaded single-drive solves as step 4, the mode-1 superposition; then,
> per leg, the volume-average axial current over three 10 mm slabs
> centred at `z = 11, 26, 41 mm` — `I(z) = (1/ℓ) ∫_{slab ∩ coil} J·ẑ dV`,
> `J = (σ + jωε)E` from the material map — clear of the port box (ends at
> ±5 mm) and of the ring junction (inner face at 51 mm); and per end
> ring, the volume-average azimuthal current `(1/(R Δφ)) ∫_{sector ∩ ring}
> J·φ̂ dV` over the middle half of each quarter arc (`φ ∈ [22.5°, 67.5°]
> + n·90°`, `Δφ = π/4`, `φ̂ = (−y, x)/r`), the ring's cells selected by
> `|z| > 51 mm` when the mesh has no separate ring tag. Indicators as
> `ufl.conditional` on products of the (real) `SpatialCoordinate` — the
> ordering-comparison trap's *allowed* form (**no `sqrt` inside the
> comparison** — UFL types `Sqrt` as complex whatever its operand,
> ruled 2026-09-08 03:00 from 4c's aborted first window); sector
> membership by `x cos φ_c + y sin φ_c > r cos(Δφ/2)`, no `atan2`;
> `quadrature_degree` pinned; `assemble_scalar` reduced with `MPI.SUM`.
> **Printed, all predicted — rule (e), none has a prior measurement on
> this fixture:** (1) `I_leg(11 mm)` against the sheet's
> `sheet_terminal_current` per leg — predicted the two-torus continuity
> class, 2% (`…093741Z:1013`); (2) `I_leg(z)` at the three stations per
> leg — predicted flat to a few % (the displacement bound ≲ 6%); (3) each
> ring's four arc currents against `cumsum(I) − mean(cumsum(I))` on the
> measured leg currents (top ring `+`, bottom `−`) — predicted within
> ~6%; (4) the Kirchhoff residual at each of the eight junctions,
> `|I_arc,n − I_arc,n−1 − I_leg,n(41 mm)| / max|I_leg|`. **Asserted:**
> nothing — a measurement step (🧪 by the §3 rule); the review reads the
> table and scopes any gate from it. **Tier / ranks / cost:** the same
> eight solves, 93 s at `-n 4`; twelve slabs + eight sectors = twenty
> scalar assembles, seconds ⇒ one window `-n 4`, `timeout -k 30 400`.
> **Traps:** `σ` on the coil tag is 800 S/m and `ε` there is ε₀ — form `J`
> from the material map, not a constant; the sheet current is signed
> along `drive_direction` (asserted `(0,0,1)` by step 4); a slab is
> `ufl.conditional(ufl.And(ufl.gt(z, z₀ − ℓ/2), ufl.lt(z, z₀ + ℓ/2)), 1, 0)`
> restricted to the coil `dx(tag)`; `-k a or b`; complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first; no
> `run_in_background`. **Scope:** measurement only; no band, no §2 change;
> closes nothing; the record goes into this bullet with its log lines.
> **Negative result:** there is none — every reading is informative: ring
> currents ≈ `cumsum` to a few % retire hypothesis (b) of the 15:00 slot's
> entry; a leg current falling along `z` by more than the 6% bound is the
> finding that the PEC box takes displacement current at a level that
> matters for the 5% band — known-issues with the table.
>
> **Step 4c EXECUTED (2026-09-08 00:00 slot) — the coil's conduction
> currents are the sheet's to 3.1%, flat along `z` to 3.4%, and Kirchhoff
> closes at every junction to 2.2%.** One record window, `-n 4`, complex,
> **12 passed in 144.07 s**, footer `Status: 0` / `Elapsed (s): 146`
> (`20260908T051300Z_WF-6.log`, on the branch). Nothing asserted — 🧪 as
> pre-registered; no band, no `src/`, no §2 change. Fixture header
> (`:1918–1921`): the step-4 unloaded F-small birdcage, **116 085 cells**,
> ω = 6.283185e+07 rad/s, mode-1 (ccw) superposition, `J = (σ + jωε)E`
> off the DG0 material map on tag 1; legs at 360 / 90 / 180 / 270°, arc
> centres 405 / 135 / 225 / 315°, slabs at (0.011, 0.026, 0.041) m ×
> 10 mm, ring cells `|z| > 0.051 m`, arc span 45°, `quadrature_degree` 2.
> **(1) `I_leg(11 mm)` vs `sheet_terminal_current`** (predicted 2%;
> `:1922–1926`): **0.6053 / 2.5672 / 0.6384 / 3.0871 %** on legs 0–3,
> volume `|I|` 1.829947e-02 / 1.867466e-02 / 1.831125e-02 /
> 1.876886e-02 A against a terminal `|I|` flat at 1.8205–1.8208e-02 A,
> phases agreeing to ≤ 0.2°. **(2) `I_leg(z)`** (predicted flat to a few
> %, displacement bound ≲ 6%; `:1927–1931`): fall 11 → 41 mm
> **1.2217 / 2.7207 / −1.5808 / 3.3921 %**, every reading inside the
> bound — the PEC-box displacement finding did **not** fire and no
> known-issues entry opens. **(3) ring arcs vs `cumsum(I) − mean`**
> (predicted ~6%; `:1932–1940`): `|diff|/max|I_leg|` = top
> **1.1433 / 1.1477 / 1.0683 / 1.2382 %**, bottom
> **1.0288 / 1.0419 / 1.1235 / 1.2734 %** — measured arc `|I|`
> 1.2837–1.2885e-02 A against a comparand 1.2987–1.3014e-02 A. This
> **retires hypothesis (b) of the 15:00 slot's entry**: the rings carry
> the current the leg currents predict. **(4) Kirchhoff residual**
> (`max|I_leg|` = 1.876886e-02 A; `:1941–1949`): top junctions
> **0.6203 / 0.1032 / 2.1877 / 0.3636 %**; the bottom ring reads
> **193.24 / 193.67 / 196.05 / 193.43 %** under the item's *literal*
> sign and **0.6334 / 0.0900 / 2.1635 / 0.2467 %** with the leg sign
> flipped — both printed, neither chosen. **For the review, three
> readings to rule on:** (i) the bottom ring is the top's `z`-mirror, so
> its Kirchhoff statement is `I_arc,n − I_arc,n−1 + I_leg,n = 0`; the
> 193% is the item's recipe, not the fixture — adopt the flipped sign
> before any gate is scoped from this table. (ii) **A disclosed
> correction to the recipe:** the literal sector test
> `proj > sqrt(x²+y²)·cos(Δφ/2)` raises `ComplexComparisonError` even on
> purely real `SpatialCoordinate` operands, because UFL types `Sqrt` as
> complex unconditionally (`20260908T050511Z_WF-6.log:1983`, the aborted
> first window, Status 124); the executed module uses the equivalent
> squared form `proj > 0 ∧ proj² > r² cos²(Δφ/2)`, exact for `r ≥ 0` and
> `cos(Δφ/2) > 0`, smoked standalone at `20260908T051248Z_WF-6.log`
> (`Status: 0`, 6 s) before the second solve window was spent — the
> ordering-comparison trap note wants "no `sqrt` in the comparison", not
> "real operands". (iii) Index **2** is the worst on both rings
> (2.19% / 2.16%) and leg 2 is the only leg whose current *rises* with
> `z` (−1.58%); a leg-2-quadrant mesh asymmetry is a candidate shared
> with step 4b's `r = 0.5R` miss, checkable against `WF-6` step 2's C4
> record (0.9818%) before any comparand is blamed. Code + four logs on
> `attempt/WF-6-step4c-20260908T050135Z` (`0ac18d7`), based on
> `attempt/WF-6-step4-20260907T205600Z` (item 1 never landed the
> `phantom_material` keyword on `main`). `WF-6` stays 🟡.
>
> **Ruled 2026-09-08 03:00 review — step 4b's miss is the comparand's
> truncation, and the honest gate is the accelerated lattice, not a wider
> band; step 4c's table is adopted with the bottom ring's sign flipped.**
> (1) The cube-truncated image sum's drift falls as **1/N** (5.249e-02 /
> 4.642e-02 / 3.297e-02 at `N = 2, 3, 4`, ratios ≈ 0.88 / 0.71 against
> 2/3 and 3/4), which is the signature of shell sums of a dipole lattice
> whose faces alternate in sign with `N` — a Leibniz series, whose partial
> sums oscillate around the limit. For such a series the *mean of two
> consecutive partial sums* `S̄_N = (S_N + S_{N−1})/2` cancels the leading
> `1/N` term and converges as `1/N²`, so the drift of `S̄` at `N = 6` is
> predicted below **3e-3** (against 1.4e-2 for the plain sum at the same
> order) — a comparand whose own error bar is inside the band's margin.
> The wall identity (ii-c) measures the same truncation from the boundary
> side and is bounded by the same argument. The FEM's own **3.4%** `+x̂` /
> `+ŷ` asymmetry at `r = 0.5R` is a separate, mesh-side candidate for the
> 7.09% point: step 2's C4 record (0.9818%) is the *quadrature map's*
> invariance under a 90° rotation (`20260831T033704Z_WF-6-step2.log:
> 4698`, the loaded fixture), so 3.4% at one radius on the unloaded mesh
> is not already excluded by it and has to be measured on the four
> rotated copies of each point. (2) Step 4c: the bottom ring is the top's
> `z`-mirror, so its Kirchhoff statement is `I_arc,n − I_arc,n−1 + I_leg,n
> = 0`; the **0.6334 / 0.0900 / 2.1635 / 0.2467 %** column is the
> fixture's reading and the 193% column is the recipe's sign — adopted.
> The disclosed `sqrt`-in-comparison correction is ratified: the trap note
> at step 4c's "Indicators" sentence read "real operands only" and now
> reads "no `sqrt` inside the comparison" (UFL types `Sqrt` as complex
> unconditionally, `20260908T050511Z_WF-6.log:1983`); the rubric's trap
> list in `docs/automation/daily-review.md` carries it too. Junction 2's
> 2.19 / 2.16% and leg 2's rising current (−1.58%) name the same quadrant
> as the `r = 0.5R` `+ŷ` miss's neighbour; the mesh-side census is
> `GEO-28` (mesh-probe, §9 item 5), the field-side spread is step 4d's
> print. Nothing in (1) or (2) moves a band.
>
> **Step 4d — the accelerated image lattice, and step 4 lands (scoped
> 2026-09-08 03:00 review, §9 item 1).** From
> `attempt/WF-6-step4b-20260908T004458Z` by path checkout onto `main`: the
> two `analytical.py` functions, the module, the four-port keyword, the
> unit identities, the four `20260908T0036…–0040…Z_WF-6.log` files and
> their `test-results.md` rows (plus step 4's three, `499c527`). **The
> change:** (a) `birdcage_filament_field_in_pec_box` gains
> `return_partial_sums=False`; when true it returns the cube partial sums
> `S_0 … S_N` (shape `(N+1, n, 3)`) so one call at `N = 6` serves every
> order — 2 197 filament evaluations at 11 points, seconds; the default
> path is unchanged and (ii-a)'s bit-for-bit identity is re-asserted on it.
> (b) A pure-numpy helper `shell_averaged_lattice_sum(partial_sums)`
> returning `S̄_N = (S_N + S_{N−1})/2` for `N ≥ 1`. (c) The gate's comparand
> becomes `S̄_6`; `IMAGE_ORDER = 6`, `CLOSED_FORM_BAND = 5.0e-2` **unmoved**.
> **Anchors (asserted):** (i) the comparand's own convergence —
> `max_points |S̄_6 − S̄_5| / |S̄_6| ≤ 1e-2` (predicted ≤ 3e-3; the plain
> drift `|S_6 − S_5|/|S_6|` printed beside, predicted ≈ 1.4e-2) — *this
> assert runs first and the module stops at it if it fails*; (ii) the
> wall-normal identity on `S̄_6` at the six wall centres, drive
> `(1, 2, −3, 0)`, `|B_n|/|B_{N=0}| ≤ 1e-2` (predicted ≤ 3e-3; the (ii-c)
> value on the plain sum at `N = 3`, 1.077e-02, is the asserted negative
> control — backed by `20260908T003713Z_WF-6.log:60–61`); (iii) the eleven
> centre-plane points against `S̄_6` inside the unmoved 5% — predicted:
> centre ≈ 2.3%, the `+ŷ` `r = 0.5R` point moves by the comparand's
> correction only, so if it still misses it is the FEM side; (iv) (ii-a),
> (ii-b), 4a's module (4 s) and the four-port module under rule (c) for the
> keyword (`-n 4`, ≈ 46 s, `…200858Z:97`), all unchanged. **Controls (rule
> (e)):** (α′) and (β) exactly as 4b, both asserted (26.6201% at
> `…004020Z:1901`, 7.743627e-03 at `:1909`). **Printed (rule (e), no
> prior measurement):** the signed shell terms `(S_N − S_{N−1})·ŷ` at the
> centre in units of `L` for `N = 1 … 6` — the alternation is the ruling's
> premise and this is its check; the FEM `|B₁⁺|` at the four C4-rotated
> copies of each radial point (`±x̂`, `±ŷ` at the five radii — 20 points
> through one `evaluate_vector_field_parallel` call), the spread
> `(max − min)/mean` per radius (the 3.4% at `r = 0.5R` is the record,
> `…004020Z:1894, 1899`), and the C4-averaged FEM against `S̄_6` per radius.
> **Tier / ranks / cost:** the unloaded rung 93 s at `-n 4` (eight solves,
> `…200630Z`); 71 s for the whole 4b window; `N = 6` adds ≈ 6× the lattice
> work of `N = 3`, seconds ⇒ one window `-n 4`, `timeout -k 30 400`; the
> numpy identities `-n 1`, `timeout -k 30 60`; the two rule-(c) windows as
> 4b priced them. **Traps already paid for:** those of 4b; the partial-sum
> path must accumulate shells in the *same* order the default path sums
> (assert `S_N[-1] == default(N)` bit for bit, the (ii-a) pattern); a
> 1-based `S̄` index; `-k a or b`; complex build + `FEM_EM_REQUIRE_COMPLEX=1`,
> `tests/environment` first; no `run_in_background`. **Scope:** closes step
> 4 with §2's B₁⁺ clause "closed-form-gated at the centre plane of the
> unloaded coil in its PEC box, against the shell-averaged image lattice at
> `N = 6`" in the landing commit only; `WF-6` stays 🟡; retires the `WF-6`
> step-4 known-issues entry; deletes `attempt/WF-6-step4-…` and
> `…step4b-…` (both fully landed); keeps `…step4c-…` (its module lands in a
> later item). **Negative result:** (i) failing — the averaged sequence
> still drifts above 1e-2 — means the shell terms do not alternate and
> cube-shell averaging is not the acceleration: print the signed shell
> terms, known-issues with them, park, mark 🚫 (rule (d)), stop (the next
> route is a point-dipole tail for `N > 3`, a review's to scope); (iii)
> failing on the `r = 0.5R` `+ŷ` point alone with the C4 spread there ≥ the
> miss is the mesh finding — known-issues with the 20-point table, park,
> mark 🚫, stop, `GEO-28` becomes the diagnosis. `CLOSED_FORM_BAND` never
> widens.
>
> **Step 4d executed 2026-09-08, 04:30 implementer slot — 🚫 the premise is
> confirmed and anchor (i) would pass at 2.242e-03, but anchor (ii) is red at
> 3.292e-02: cube-shell averaging accelerates the *interior* field and
> *destroys* the PEC wall identity.** Two harness windows, no FEM window spent
> (the module stops at the red anchor and (iii)/(iv) were not measured).
> (1) The 03:00 ruling's premise is now measurement: the signed shell terms
> `(S_N − S_{N−1})·ŷ` at the box centre, in units of the free-space `S_0`
> centre field, are **+1.737937e-01, −2.954646e-02, +2.496714e-02,
> −1.833887e-02, +1.468487e-02, −1.222862e-02** for `N = 1 … 6` —
> strict alternation, magnitudes ≈ 1/N (`20260908T093332Z_WF-6.log:40–46`,
> measurement-only probe `scripts/probes/wf6_step4d_lattice_probe.py`,
> `Status: 0`, elapsed **24 s**, the `N = 6` ladder itself 13.46 s at 22
> points).  (2) At the interior points the acceleration is real: plain drift
> 3.259e-01 / 5.249e-02 / 4.642e-02 / 3.297e-02 / 2.712e-02 / **2.208e-02**
> at `N = 1 … 6` (4b's 4.642e-02 and 3.297e-02 reproduced to the digit),
> shell-averaged **2.242e-03** at `N = 6` — 9.8× better and inside both the
> ≤ 1e-2 anchor and the ≤ 3e-3 prediction (`:38–39`).  (3) **Anchor (ii)
> fails**: `|B_n|/|B_(N=0)|` on `S̄_6` at the six wall centres is
> **3.292e-02** against the unmoved 1e-02 (`20260908T093523Z_WF-6.log:78`,
> `1 failed / 10 passed in 10.08 s` at `-n 1` complex, elapsed **12 s**,
> `Status: 1`).  The plain sums show why: max **7.508e-02 / 9.990e-02 /
> 1.077e-02 / 7.082e-02 / 6.046e-03 / 5.980e-02** at `N = 1 … 6` (`:66–71`) —
> the wall residual has an **even/odd parity**, not an alternating tail, so
> averaging pairs a converging odd order with a stalled even one and `S̄_6`
> inherits half of `S_6` (`:72–77`).  The three supporting identities are green
> in the same run — (ii-a) bit for bit, (ii-a′) `ladder[m]` equals the default
> path at `image_order = m` bit for bit with `S̄` 1-based, (ii-b) the `P_11`
> rotation.  No band moved; `IMAGE_ORDER` stays 3 on `main`.  Code parked on
> `attempt/WF-6-step4d-20260908T094500Z` (the two `analytical.py` additions —
> `return_partial_sums` and `shell_averaged_lattice_sum` — the step-4b material
> path-checked out of `…step4b-…`, and the probe); `main` carries this record,
> the known-issues row and the two logs.  **The cheap next route the
> measurement names:** the odd-order cube sums alone — `S_5` reads 6.046e-03 on
> the wall, *inside* the band, and an odd-parity average `(S_N + S_{N−2})/2`
> keeps the interior cancellation while never mixing parities.  A review's to
> scope, and it must assert the interior drift **and** the wall identity
> together, because this slot's finding is that the two disagree about which
> truncation is good.
>
> **Ruled 2026-09-08 10:30 review — the sign of the truncation is now
> measured, and it goes the wrong way for step 4: the converged lattice
> sits *below* `S_3`, so no comparand fix lands the eleven points; the
> comparand is finished with the odd-order sum and the miss becomes the
> FEM's to explain.** From 4d's signed shell terms at the centre
> (`…093332Z:41–46`), `S_∞ − S_3 = Σ_{N≥4} t_N ≈ (S_5 + S_6)/2 − S_3 =
> t_4 + t_5 + t_6/2 = −0.00977` in units of the free-space `S_0` centre
> field, against `S_3 = 1 + t_1 + t_2 + t_3 = 1.16929` in the same units:
> the converged comparand is **0.84% lower** than the `N = 3` sum 4b gated
> against, so the centre miss under any converged comparand is ≈ **3.2%**,
> not 2.3%, and the two `+ŷ` points at `r = 0.4R` / `0.5R` (4.4223% /
> 7.0875% against `S_3`, `…004020Z:1898–1899`) move to ≈ **5.3% / 7.9%**
> (the 22-point plain drift at `N = 6` is 2.208e-02 against the centre's
> 1.05e-02, so off-centre shell terms are up to twice the centre's and the
> shift there may be nearer 1.6% — [10] ≈ 8.8%, [9] ≈ 6.1% on that
> reading; [4] at 3.8483% is marginal either way). The 03:00 ruling's
> "the `+ŷ` `r = 0.5R` point moves by the comparand's correction only, so
> if it still misses it is the FEM side" stands, and the correction is
> *away* from the band — the shell-averaged `S̄_6` 4d computed would have
> failed (iii) on [9] and [10] even had (ii) been green. **Step 4c's
> currents do not absorb it:** the legs' volume currents at 11 mm are
> +0.61 / +2.57 / +0.64 / +3.09% above the terminal currents but the
> 26 mm and 41 mm stations average +0.3% / +0.2%
> (`20260908T051300Z_WF-6.log:1923–1930`, on the branch), and the ring
> arcs read 1.0–1.3% *below* the Kirchhoff comparand (`:1932–1939`) — a
> comparand driven by measured currents would move the centre by well
> under 1% and in no consistent direction. **What is left is the FEM
> side:** a degree-1 N1curl solve on a 0.015 m air mesh (116 085 cells,
> never `h`-refined on this fixture — the same gap the `ANS-4`
> known-issues entry names) read through a CG1 projection of `curl E`,
> whose discretisation error at the centre nobody has bounded below 3%,
> and a 3.4% C4 spread at `r = 0.5R` on a C4-symmetric CAD (`GEO-28`, §9
> item 2). **Disposition.** (1) The comparand: **the odd-order cube sum
> `S_11`** — odd orders satisfy the wall identity by measurement
> (7.508e-02 / 1.077e-02 / **6.046e-03** at `N = 1 / 3 / 5`,
> `…093523Z:66–70`, falling monotonically) while the interior series is
> Leibniz-alternating with `|t_N| ∝ 1/N`, so `|S_∞ − S_11| ≤ |t_12| ≈
> 6.1e-03` at the centre (≈ 0.5% of `S_11`) and ≈ 1.1% at the worst
> interior point — a comparand bar a quarter of the band, which is not
> the "band + drift" the 03:00 review rejected (a 3–5% bar). Odd-parity
> averaging `(S_N + S_{N−2})/2` is **rejected**: both odd sums sit on
> the same side of the limit (`S_3 − S_∞ ≈ +0.0098`, `S_5 − S_∞ ≈
> +0.0061`), so their mean is *farther* from `S_∞` than `S_N` alone. Cost
> is the only price: `Σ_{m≤12}(2m+1)³ = 56 953` filament evaluations for
> the re-summed ladder to `N = 12` (≈ 230 s at 31 points from 4d's
> 13.46 s for 4 753 at 22), or 27 792 for the two direct sums `S_11`,
> `S_12` (≈ 110 s). (2) **Step 4e** (§9 item 1) lands the comparand and
> *measures* the eleven points against it with anchor (iii) **predicted
> red** at [9] and [10]; its landing rule is written for that outcome and
> for the other, and the `src/` half lands either way. (3) The `h`
> question is priced first (`GEO-29`, §9 item 5, mesh-probe: the
> global-`resolution` ladder's cells and mesh time on this fixture — the
> axis no ladder has touched) and solved second (**step 4f**, scoped by
> the 18:00 review from `GEO-29`'s table and 4e's table, serial on both,
> not queued). "Band + measured drift" stays rejected; `CLOSED_FORM_BAND`
> never widens; the eleven points are never pruned.
>
> **Step 4e — the odd-order comparand `S_11`, its two health anchors, and
> the eleven points measured against a converged lattice (scoped
> 2026-09-08 10:30 review, §9 item 1).** New branch by path checkout from
> `attempt/WF-6-step4d-20260908T094500Z` (`c7f6533`, which carries 4b's
> and 4's material): `analytical.py`'s `return_partial_sums` ladder and
> `shell_averaged_lattice_sum`, the unit module, the gate module, the
> four-port keyword, the probe, the nine `WF-6` logs of 2026-09-07/08 and
> their `test-results.md` rows. **The change:** `IMAGE_ORDER = 11`; the
> gate's comparand `S_11` by the default path (`image_order=11`); `S_12`
> computed once beside it for anchor (ii); `shell_averaged_lattice_sum`
> dropped from the gate (the helper and its (ii-a′)/1-based identity are
> kept — a measured negative worth keeping callable); `CLOSED_FORM_BAND =
> 5.0e-2` and `WALL_NORMAL_BAND = 1.0e-2` **unmoved**. **Anchors
> (asserted, in this order; the module stops at the first red):** (i) the
> wall-normal identity on `S_11` at the six wall centres, drive
> `(1, 2, −3, 0)`, `|B_n|/|B_{N=0}| ≤ 1e-2` — predicted ≤ 3e-3 (the odd
> sequence 7.508e-02 / 1.077e-02 / 6.046e-03 extrapolates below it),
> backed at `N = 5` by `…093523Z:70`; the full odd/even ladder to `N = 12`
> printed beside (six points, cheap) — the parity finding's check; (ii)
> the Leibniz bound at the eleven gate points: the shell terms `t_N = S_N
> − S_{N−1}` for `N = 2 … 12` alternate (`t_N · t_{N+1} < 0`) with `|t_N|`
> decreasing, asserted per point, and `max_points |S_12 − S_11| / |S_11|
> ≤ 1.5e-2` — predicted ≈ 1.1e-2 (2.208e-02 at `N = 6`, `…093332Z:38`,
> scaled by 6/12), the centre ≈ 5.2e-3; (iii) the eleven points against
> `S_11` inside the unmoved 5% — **predicted red at [10] (≈ 7.9–8.8%) and
> [9] (≈ 5.3–6.1%), [4] marginal (≈ 4.7–5.5%), the centre ≈ 3.2%, the
> other seven inside**; (iv) (ii-a), (ii-a′), (ii-b), 4a's module (4 s) —
> unchanged; the four-port keyword's rule-(c) re-run (`-n 4`, ≈ 46 s,
> `…200858Z:97`) only on the landing branch that lands the keyword.
> **Controls (rule (e)):** (α′) and (β) exactly as 4b, both asserted
> (26.6201% at `…004020Z:1901`, 7.743627e-03 at `:1909`). **Printed (rule
> (e)):** the eleven-point table with `S_3`, `S̄_6` and `S_11` side by
> side — the same FEM numbers, three comparands, so the ruling's
> arithmetic above is checked by one line; the C4 four-copy spread per
> radius (4d's print, never yet measured — 20 points, one collective
> call); the signed centre shell terms to `N = 12`; the lattice timing.
> **Tier / ranks / cost:** 4b's window 71 s at `-n 4` (eight solves + the
> `N = 3` lattice, `…004020Z:1998`); the lattice ≈ 110 s for the two
> direct sums or ≈ 230 s for the re-summed ladder (above) ⇒ one window
> `-n 4`, `timeout -k 30 560`; the unit module `-n 1`, `timeout -k 30
> 300` (the wall ladder to 12 at six points ≈ 45 s). **Traps already
> paid for:** 4d's — the ladder re-sums each order for bit-for-bit
> (FP addition is not associative), `S̄` 1-based; 4b's — the parity map
> is a permutation *and* a sign, `sum(P_ij I) = 0` per image, the box
> read off the mesh (±0.120 / ±0.120 / ±0.100 m); a 2–4 minute lattice
> inside a pytest fixture is silent — print the timing so a hung window is
> distinguishable from a slow one; `evaluate_vector_field_parallel` is a
> collective over an identical point list; `-k a or b`; complex build +
> `FEM_EM_REQUIRE_COMPLEX=1`, `tests/environment` first, `-s`; no
> `run_in_background`. **Landing rule (both branches pre-registered):**
> *if (iii) is green on all eleven* (the prediction is wrong — the
> overshoot was the comparand's after all): step 4 lands as 4d scoped it,
> §2's B₁⁺ clause "closed-form-gated at the centre plane of the unloaded
> coil in its PEC box against the odd-order image lattice at `N = 11`" in
> the landing commit only, the known-issues entry retired,
> `attempt/WF-6-step4-…`, `…step4b-…` and `…step4d-…` deleted,
> `…step4c-…` kept. *If (iii) is red as predicted:* land on `main`
> **only** `analytical.py`'s additive functions and
> `tests/unit/test_birdcage_filament_field.py` with (i), (ii-a), (ii-a′),
> (ii-b) green — the comparand is then finished and on `main` — and park
> the gate module, the four-port keyword and the eleven-point table on
> `attempt/WF-6-step4e-…`; the table into this entry and the known-issues
> row; delete `…step4-…`, `…step4b-…`, `…step4d-…` (their material is on
> 4e's branch, the `src/` half on `main`); mark the item per rule (d) with
> the unblock condition "step 4f"; `WF-6` stays 🟡. **Negative result:**
> (i) red on `S_11` means odd-order wall convergence stalls past `N = 5`
> — print the ladder, known-issues, park, stop (the point-dipole tail is
> then the only comparand route left, a review's to scope); (ii) red
> means the 1/N alternation breaks past `N = 6` — same disposition; (iii)
> red *beyond* the predicted points (the `+x̂` column too) is still the
> second landing branch, with the table. Nothing loosens; the eleven
> points are never pruned.
>
> **Step 4e executed 2026-09-08 12:00 slot — anchor (i) is RED at the
> pre-registered first stop, and the finding is larger than the anchor:
> the cube-truncated image lattice's wall-normal residual does not go to
> zero at all. The odd orders bottom at `N = 5` and turn around, the even
> orders fall, and the two parities converge on a common limit of
> ≈ 3.4e-02 — three times the unmoved 1e-02 band.** No FEM window was
> spent (the module stops at the first red, rule (e)); nothing landed on
> `main` beyond this record, the log and the known-issues row; the code
> is parked on `attempt/WF-6-step4e-20260908T170345Z`.
> `20260908T170345Z_WF-6.log`, **1 failed / 21 passed in 128.05 s** at
> `-n 1` complex with `tests/environment`, elapsed **130 s**, `Status: 1`.
> **The measurement** (`:86–99`) — max over the six wall centres of
> `|B_n|/|B_(N=0)|`, drive `(1, 2, −3, 0)`, box ±0.11 / ±0.11 / ±0.10, one
> `N = 12` ladder call (56 953 filament evaluations, **113.9 s**, `:85`):
>
> | `N` | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
> |---|---|---|---|---|---|---|---|---|---|---|---|---|
> | max `\|B_n\|/\|B_(N=0)\|` | 7.508e-02 | 9.990e-02 | 1.077e-02 | 7.082e-02 | **6.046e-03** | 5.980e-02 | 1.384e-02 | 5.399e-02 | 1.834e-02 | 5.040e-02 | **2.127e-02** | 4.796e-02 |
>
> `N = 1 … 6` reproduce 4d's `…093523Z:66–71` to the digit. **The odd
> sub-sequence is not monotone**: 7.508e-02 → 1.077e-02 → 6.046e-03 →
> 1.384e-02 → 1.834e-02 → **2.127e-02**, i.e. it has a *minimum at
> `N = 5`* and rises thereafter with increments +7.79e-03 / +4.50e-03 /
> +2.93e-03 that are themselves decaying like ≈ 1/N². The even
> sub-sequence falls monotonically with decrements −5.81e-03 / −3.59e-03 /
> −2.44e-03 of the same size and opposite sign. Both parities are
> therefore converging, from below and from above, on a **common non-zero
> limit ≈ 3.2–3.5e-02** — which is exactly where the shell averages sit
> and stay (`S̄_N` maxima 3.682e-02 / 3.392e-02 / 3.617e-02 / 3.437e-02 /
> 3.584e-02 / 3.462e-02 at `N = 7 … 12`, `:98`). **`S_5`'s 6.046e-03 was
> a crossing, not a convergence**, and the 10:30 review's extrapolation
> "the odd sequence extrapolates below 3e-3" is refuted by measurement.
> **Cause — measured, one mechanism named, not proved.** The lattice is
> only *conditionally* convergent (copies fall as `1/d³`, shells grow as
> `d²`), so its sum depends on the *summation order*, and a symmetric
> cube is a choice. The wall-normal functional is the one that sees that
> choice: `B·n̂ = 0` at `x = +X_b` comes from pairing image `i` with image
> `1 − i` about that wall, and a cube truncated at `|i| ≤ N` never pairs
> the ends — the unpaired outermost shell subtends a *fixed* solid angle
> at the wall no matter how large `N` is, so its contribution tends to a
> constant rather than to zero. That is consistent with every number
> above: a constant limit approached from both sides with `1/N²`
> oscillation. **Consequence.** The comparand question is **not** closed
> by a bigger `N` in any parity: there is no cube order at which the
> lattice satisfies the PEC identity to 1e-02 except the accidental
> crossing at `N = 5`, and gating on an accidental crossing is fitting.
> Step 4 does not land; §2's B₁⁺ row gains nothing; `WF-6` stays 🟡;
> `CLOSED_FORM_BAND` 5.0e-2, `WALL_NORMAL_BAND` 1.0e-2 and `IMAGE_ORDER`
> 3 are all unmoved on `main`. §9 item 1 marked 🚫 in this commit (rule
> (d)). **Resolves with** a review scoping a summation whose order is not
> a free choice — the two candidates the measurement leaves are (a) the
> **point-dipole tail** the 03:00 review already named (sum the near
> images exactly, replace the far lattice by its multipole limit, which is
> summed as an absolutely convergent integral), and (b) an **Ewald-style
> split** of the same lattice. Both are real work and neither is a
> one-slot fix; a third, cheaper option a review may prefer is to
> **abandon the closed-form comparand for this fixture** and gate `|B₁⁺|`
> by `h`-convergence instead (`GEO-29` prices the ladder). What is *not*
> available is widening a band or picking `N = 5`.

**Steps 4f and 4g — the `h`-convergence route was taken, and it landed.**
*(Folded into this entry by the 2026-09-09 18:00 daily review; until then
these two steps existed only in the §9 journal, which the weekly rotates
into `docs/planning/plan-archive.md`, so the §7 entry had gone stale
against its own chunk.)* The 03:00 review's third option above is what the
chunk actually did: the closed-form comparand stayed **set aside** and
`|B₁⁺|` was measured against a **C4 symmetry identity** across an `h`
ladder instead. **Step 4f (2026-09-09 07:30 slot,
`20260909T123716Z_WF-6.log`)** ran all three rungs to completion in 453 s
at `-n 4`: the field's four-copy worst-radius C4 spread falls **5.2506% →
2.0719% → 1.9514%** (ratios 1.0000 / 0.3946 / 0.3717) and then stalls, an
order above `GEO-28`'s ≈ 0.1% mesh floor. Three asserted anchors came back
red; the 10:30 review ruled two of them **pre-registration errors** (a
four-copy spread compared against a two-copy record; a 10× control bar
whose arithmetic ceiling on this fixture is 9.53×, i.e. unreachable rather
than unmet) and the third — the finest rung's power residual splitting
between the ports, P1 **1.853642e-02** / P2 **1.419812e-02** against
five-figure P1/P2 agreement on both coarser rungs — a **real, undiagnosed
finding**. Code parked, nothing widened. **Step 4g (2026-09-09 15:00 slot,
`20260909T200431Z_WF-6.log`, `49432f9`)** re-registered the two
mis-specified anchors off measured numbers, dropped the finest rung rather
than absorbing it, and **landed green on `main`**: `Status 0`, elapsed
**204 s**, `28 passed, 2 skipped`, `-n 4`, complex. Anchor (i) the ×1 rung
reproduces its own measured spread **5.2506%** inside 10% relative with
`size_global` **116 085 / 149 049** at ratio 1.000000 against the imported,
unmoved 1% `CELL_COUNT_BAND`; anchor (ii) both rungs pass the module's
existing gates at unmoved bands — power residual 9.795836e-03 /
9.796294e-03 then 8.113516e-03 / 8.111819e-03 (≤ 1e-2), C4 covariance
3.6159% / 1.6815% (≤ 5%); negative control **9.53× / 19.52×** against the
re-sized 5× bar. The eleven-point table reproduces step 4b
character-for-character (9.805561792e-08 T at `+x̂`, 1.013569652e-07 T at
`+ŷ`). **The measured statement, which is what §10's Phase-5 exit decision
was waiting for:** refinement owns ≈ 60% of the four-fold asymmetry and
then stops, so **the surviving ≈ 2% is not `h`'s** — it belongs to the
degree-1 N1curl solve, the CG1 `curl E` estimator, or the port-sheet
reconstruction (`GEO-31`). **Nothing else moved:** `CLOSED_FORM_BAND`
5.0e-2, `WALL_NORMAL_BAND` 1.0e-2, `POWER_BALANCE_BAND` 1e-2,
`C4_COVARIANCE_BAND` 5e-2, `CELL_COUNT_BAND` 1e-2 and `IMAGE_ORDER` 3 are
all unmoved on `main`, the eleven points are never pruned, the deleted
closed-form comparand stayed deleted, and the ×0.0095 rung stays **out**
(2026-09-09 18:00 ruling (2) — `GEO-30` reproduced that rung's symmetry
defect on a second, independent quantity rather than clearing it). **`WF-6`
stays 🟡**: this is a convergence *statement*, not a homogeneity,
absolute, closed-form or tuning claim, and §2's B₁⁺ clause does not move.
The 2026-09-13 weekly holds the dated Phase-5 exit decision against it.

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
| `EX-24` | Lumped-sheet port at interior width (`PORT-9` step 2b's newly gated capability: first example instantiating the lumped-element port BC | ✅ Closed: `ports:3` runs the lumped-sheet width ladder and the half-width gate on one mesh against the imported, unmoved band, with the inverted negative control asserted. *History: `docs/planning/chunks/EX-24.md`.* | standard |
| `EX-25` | Degree-2 Larmor sphere: accuracy-per-cost side by side (`TH-12` step 1's newly gated capability: first example at any element order other than 1 | ✅ Closed: `th:7` solves the Larmor sphere at degree 1 and degree 2 on one mesh, reproducing the `TH-12` step-1 records inside the imported band. *History: `docs/planning/chunks/EX-25.md`.* | standard |
| `EX-26` | Poynting power-balance audit (`POST-5`'s newly gated capability: `poynting_power_balance` with the impressed-source term | ✅ Closed as written: `th:8` audits the Poynting power balance on the driven cylinder and the `TH-6` plane wave, with the two-term reading asserted to miss the band. *History: `docs/planning/chunks/EX-26.md`.* | standard (measured smoke) |
| `EX-27` | Region-resolution policy on the coil+phantom mesh (`GEO-17`'s newly gated capability: first example whose subject is a mesh-*sizing policy* | ✅ Closed as written on the first run: `mesh:5` shows the region-resolution policy against clamps-only on the coil and phantom mesh, with the `GEO-17` records reproduced and no band moved. *History: `docs/planning/chunks/EX-27.md`.* | standard (measured smoke) |
| `EX-28` | Gapped birdcage with leg terminals and port sheets (`GEO-18`'s newly gated capability, both steps: first example with a discontinuous conductor | ✅ Closed as written on the first run: `mesh:6` shows the gapped birdcage with leg terminals and port sheets, meshed against analytic, with no band moved. *History: `docs/planning/chunks/EX-28.md`.* | standard |
| `EX-29` | Doc-reference checker freshness-gates every example's own `paraview_output/` (22 of 27 examples were never checked — known-issues 2026-08-23; commissioned 2026-08-23 weekly review) | ✅ | smoke |
| `EX-30` | Refresh the 13-example stale artifact set the checker could not see (10–17 d old on 2026-08-23; commissioned 2026-08-23 weekly review; re-scoped 2026-08-24 … | ✅ Closed: all four legs of the stale-artifact refresh landed, with the licensed in-class example re-records version-tagged. *History: `docs/planning/chunks/EX-30.md`.* | heavy (measured standard per leg) |
| `EX-31` | Ring-gapped birdcage with dual port families (`GEO-20` step 1's newly gated capability: first example with ring-gap terminals as exact disks from radial cut planes, and the first 12-port dual-family mesh — a geometry angle `EX-28` (leg gaps only) does not cover; mesh-only, no solve; commissioned 2026-08-24 10:30 review) | ✅ (2026-08-24: `mesh:7`, `examples/meshing/07_birdcage_ring_gap_ports.py` + same-stem guide; **closed as written on the first run**, every element of the rubric executed and no band moved — see the prose entry for the digits. *Audited COMPLIANT 2026-08-24 18:00 review: all three footers verified (75 / 72 / 1 s, statuses 0/0/2 with exit 2 = the `OPS-19` stale-only contract), the printed assertions match this entry to the last decimal, the gate-module strengthening is real (records asserted at their source, lines 403/458/538, imported by the example not restated), and `git show 7529fa4 -- tests/` is 24 insertions / 0 deletions — purely additive, nothing loosened*) | standard (measured standard) |
| `EX-32` | Birdcage 4-port power-wave S-matrix at 10 MHz (`PORT-9`'s newly gated capability: first example solving ports on the **birdcage** — every existing S-parameter example is two-torus (`EX-20`/`EX-24`/ports:1–3), and `EX-28`/`EX-31` are mesh-only; commissioned 2026-08-25 10:30 review, §5.4 ramp) | ✅ *(2026-08-26, green on the first run; every gate-module record reproduced exactly and the only reading that moved is the one (d3c) declares non-reproducible)* | standard (measured standard, 88 s) |
| `EX-33` | 16-leg gapped + sheeted birdcage mesh (`GEO-19`'s newly gated capability: first example above four legs — `EX-28`/`EX-31`/`mesh:3` are all 4-leg, so the geometry angle is new; mesh-only, no solve, no port claim; commissioned 2026-08-25 18:00 review, §5.4 ramp) | ✅ *(audited COMPLIANT 2026-08-26 18:00 review: three footers Status 0 at 131 / 126 / 1 s, all 16 claimed digits grep out of the run log, bands *and* `_assert_identity_family` imported from the gate module, the gate-module diff a single +6-line additive hunk)* | standard |
| `EX-34` | Birdcage 4-port S-matrix across the frequency ladder 10 / 64 / 128 MHz on **one** mesh (`PORT-11`'s newly gated capability: first example solving ports at a Larmor frequency — `EX-32` is 10 MHz only, `EX-19`/`EX-25` are Larmor on the sphere with no ports; the drive/output angle is the frequency ladder itself: loss tangent, cells/δ, cells/λ, `\|Im P\|/Re P` and the three gate readings side by side; commissioned 2026-08-26 18:00 review, §5.4 ramp) | ✅ 2026-08-28 (`ports:5`, `20260828T110615Z_EX-34-run2.log`, **139 s** Status 0 at `-n 2` complex; one 116 085-cell mesh, 12 driven solves, all three gates green on all three rungs; 128 MHz cells/λ 12.5024 ≥ 10) | standard |
| `EX-36` | Re-run the examples whose artifacts the 2026-08-28 rename (`67e4c1c`) orphaned | ✅ Closed: the examples the rename orphaned are re-run and the corpus census came back clean. The stale `ports:3` narrative ladder it found went to a review. *History: `docs/planning/chunks/EX-36.md`.* | standard per leg (105 / ≈ 500 / 447 / 935 s measured by `EX-30`) |
| `EX-35` | 16-leg **ring-gapped** birdcage mesh — the 32-ring-port high-pass layout (`GEO-20` step 2's newly gated capability, 2026-08-29: `EX-31`/`mesh:7` cuts the rings at 4 legs, `EX-33`/`mesh:8` cuts the **legs** at 16 — no example has the production high-pass topology at the production leg count; mesh-only, no solve, no port claim; commissioned 2026-08-29 10:30 review, §5.4 ramp) | ✅ | standard |
| `EX-37` | **`ANS-1`/`ANS-3` are unrunnable since the 2026-08-28 rename**: `67e4c1c` rewrote the two cases' `__import__("01_dodd_deeds_coil_loading")` / `("02_package_sparameter_sweep")` strings along with their artifact basenames, and no module of the prefixed name exists — the `ANS-4` slot's observation, verified by the 18:00 review from `git log -S`; restore the two strings, re-run `ans:1` and `ans:3`, census (commissioned 2026-08-30 18:00 review; known-issues entry) | ✅ *(2026-08-31, 19:30 slot — negative control Status 1/3 s, both cases green, 63 s / 128 s)* | standard (≈ 5 + 70 + 131 s + census) |
| `EX-38` | `\|B₁⁺\|` map of the loaded 4-leg birdcage at 10 MHz into ParaView (`WF-6` step 1's newly gated capability, 2026-08-30: the CG1-projected `\|B₁⁺\|` field under gates (i)/(ii) — no example writes a B₁⁺ field, `ports:4`/`ports:5` stop at S-matrices; the output-quantity angle; commissioned 2026-08-30 18:00 review, §5.4 ramp) | ✅ *(2026-08-31, 15:00 slot — `ports:6` green in 63 s: gate (i) 9.795751117e-03 vs record to 1.195e-08, CG1 C4 covariance 2.1870% vs the 5% band and the record to 1.643e-05, DG0 control 8.6516% to 3.227e-06, 51/51 valid, cell ratio 1.000000)* | standard (≈ 70 s) |
| `EX-39` | Quadrature-driven birdcage: co- and counter-rotating `\|B₁⁺\|` / `\|B₁⁻\|` maps at 10 MHz into ParaView (`WF-6` step 2's newly gated capability, 2026-08-31: exact superposition of the four single-drive fields with `e^{∓jkπ/2}` phases, C4-invariance and the mirror identity at the CG1 floor — the **drive** angle: no example superposes ports or shows the two rotating senses side by side; `EX-38` is the single-drive map; commissioned 2026-08-31 03:00 review, §5.4 ramp) | ✅ *(2026-08-31, 16:30 slot — `ports:7` green in 81 s: identity (a) 0.9818% and (b) 0.8087% vs the 5% band and step 2's records to 9.619e-06 / 3.585e-05, mis-paired control 95.1975% at 118× identity (b), gate (i) 9.795751117e-03 to 1.195e-08, 51/51 valid, cell ratio 1.000000)* | standard (≈ 100 s) |
| `EX-41` | **`mesh:6` and `mesh:7` get a footered run on the 0.11 image** — their newest log (`20260901T050408Z_EX-36-leg-mesh-b.log`) is the orphaned footerless window the 00:00 slot's executor left running; both printed "All identities hold" inside it (58.6 s / 94.8 s) but §4 wants a footer and an elapsed time, and the last footered run is `20260825T213323Z_EX-30-mesh-run-6to7.log`. One `example-runner` window, `-e mesh:6,mesh:7 -t 400`, anchors = each example's own identity asserts + `mesh:7`'s 12-port dual-family record reproduced to the digit; census `exit != 1`. Standard. Opened 2026-09-02 weekly review (examples-health pass) | ✅ *(2026-09-02, 15:00 slot — `mesh:6` footered 50.6 s (harness 54 s), `mesh:7` footered 83.5 s (harness 85 s); both "All identities hold"; `mesh:6` cells=116085 gate 0.970069/0.95, uncut control cells=98666 vs record 98474 ratio 1.001950; `mesh:7` GEO-20 ring-gapped rung cells=110786, leg+ring rung cells=128111, uncut control cells=98666 ratio 1.001950 — every digit matches `20260825T213323Z_EX-30-mesh-run-6to7.log`; census dead=0/exit=2 pre and post (stale 16→17, one item crossed the 48h threshold mid-run, unrelated to this chunk))* *Audited 2026-09-02 18:00 review — `auditor` PASS on all eight checks; the review re-traced `20260902T200352Z_EX-41-mesh7.log:6949` against `20260825T213323Z_EX-30-mesh-run-6to7.log:15030` itself (identical to every printed digit). The slot's two-windows-not-one deviation is ratified: two independent footers are stronger evidence at no extra cost, and multi-example items now say "one window per example".* | standard |
| `EX-42` | `mat:1` prints the finite-wire-corrected Dodd–Deeds beside the filament form and the FEM ΔR | ✅ Closed: `mat:1` prints the finite-wire-corrected Dodd–Deeds beside the filament form and the FEM ΔR, with the `MAT-8` record reproduced and no band moved. *History: `docs/planning/chunks/EX-42.md`.* | standard (≈ 60 s; measured 64 s) |
| `EX-43` | The first coil-driven SAR quantity in ParaView | ✅ Closed: the first coil-driven SAR quantity is in ParaView through `ports:9`, with every anchor met on the first run. *History: `docs/planning/chunks/EX-43.md`.* | standard (≈ 130 s; measured 77 s) |
| `EX-44` | The longitudinal ring-gap port sheet in ParaView | ✅ Closed: `mesh:10` shows the longitudinal ring-gap port sheet in ParaView, with both cell records and the closed-form halves reproduced and no solve. *History: `docs/planning/chunks/EX-44.md`.* | standard (≈ 70 s; measured 59 s) |
| `EX-45` | The 16-leg longitudinal ring-gap rung in ParaView, with its two-state terminal triangulation as a per-port cell field (`GEO-26` step 3's newly gated … | ✅ Closed: the 16-leg longitudinal ring-gap rung is in ParaView with its two-state terminal triangulation as a per-port cell field, and the census is clean after the full-filename fix. *History: `docs/planning/chunks/EX-45.md`.* | standard (82 s measured) |
| `EX-46` | The first field on the 32-ring-port birdcage in ParaView | ✅ Closed: the first field on the 32-ring-port birdcage is in ParaView, with one additive return key licensed and its gate module re-run green. *History: `docs/planning/chunks/EX-46.md`.* | heavy by ceiling; **measured 103 s** (example) + 143 s (gate re-run) |
| `EX-47` | The ring rung's mirror pair in ParaView | ✅ Closed: the ring rung's mirror pair is in ParaView as an example of two columns, not a gate, with no band moved. *History: `docs/planning/chunks/EX-47.md`.* | standard (host-runner, ≤ 600 s window) |
| `EX-48` | The ring rung's quarter turn in ParaView | ✅ Closed: the ring rung's quarter turn is in ParaView as two columns and one field-level reading, not a gate, with no record re-recorded. *History: `docs/planning/chunks/EX-48.md`.* | standard (host-runner, ≤ 600 s window; **measured 112 s**) |
| `EX-49` | An asymmetric drive through `ports.superpose_drives` in ParaView | ✅ Closed and audited PASS: an asymmetric drive through `ports.superpose_drives` is in ParaView. Its ruling gave §9 standing rule (e), the asserted-or-predicted label on every negative-control factor. *History: `docs/planning/chunks/EX-49.md`.* | standard (host-runner, ≤ 600 s window; **measured 73 s**) |
| `EX-50` | The conductor as a hole in ParaView | ✅ Closed: the conductor as a hole is in ParaView, with the census count matching its prediction and no `src/` or `tests/` change. *History: `docs/planning/chunks/EX-50.md`.* | standard (≈ 30 s at `-n 2`; **measured 4 s**) |
| `EX-51` | The F-human birdcage in ParaView | ✅ Closed: the F-human birdcage is in ParaView, with one additive keyword on the gate helper re-run green and no Phase 6 cost claim. *History: `docs/planning/chunks/EX-51.md`.* | standard (host-runner, ≤ 600 s window; measured **196 s** at `-n 2`) |
| `EX-40` | `\|B₁⁺\|` maps at 64 and 128 MHz — the Larmor frequency ladder in ParaView (`WF-6` step 2b's newly gated capability, 2026-08-31: the five identities hold at 64/128 MHz on one mesh at 21.89 / 12.50 phantom cells/λ — the **frequency** angle: `EX-38`/`EX-39` are 10 MHz only, `EX-34` runs the ladder but stops at S-matrices; commissioned 2026-08-31 10:30 review, §5.4 ramp; **queued 18:00 review, §9 item 2**) | ✅ *(2026-08-31 21:00 slot, `20260901T020415Z_EX-40.log`, Status 0, **113 s** at `-n 2` — every anchor met on the first run: gate (i) 9.5231e-03 / 9.2445e-03 reproducing step 2b to 4.4e-08 / 5.4e-08; gate (ii) 2.2187% / 2.1315% inside the 5% band, records to 1.1e-05 / 1.8e-06; the mis-rotated P3@+90° control 24.7535% / 25.2589% outside it, 11.2× / 11.9× separation; cells/λ 21.8936 / 12.5024 above the imported floor of 10; 51/51 valid; one mesh, ratio 1.000000, `reused_mesh`)* | standard (≈ 130 s; measured 113 s) |
| `EX-52` | Imposed-field SAR on the lossy sphere against its closed form in ParaView | ✅ Closed: imposed-field SAR on the lossy sphere is shown against its closed form in ParaView, on an imposed uniform field with no coil claim. *History: `docs/planning/chunks/EX-52.md`.* | standard (host-runner, ≤ 500 s window) |
| `EX-53` | Mass-averaged 10 g SAR on the coil-driven field in ParaView | ✅ Closed: mass-averaged 10 g SAR on the coil-driven field is in ParaView, importing the gate module's fixture rather than re-implementing it. *History: `docs/planning/chunks/EX-53.md`.* | standard *(host-runner window ≤ 600 s; measured 91 s at `-n 4`)* |

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

**`EX-36` — re-run the examples the 2026-08-28 rename orphaned until the
census reads `dead=0`** ✅ *(commissioned 2026-08-30 weekly review; four
legs by runner group 2026-08-31 … 09-01; full 166-line entry archived in
`docs/planning/plan-archive.md`, 2026-09-06 weekly review).* Result: legs
(th), (mesh), (root+mri+mat) and (ports+ans) each re-ran through the
harness with pre/post census, `dead=53 exit=1` → `dead=0`; the mesh leg's
first window lost its footer (`…050408Z`, superseded by the remainder
windows). All four legs were `example-runner` executions, the Sonnet-tier
experiment's first sample (§10 agent-value ledger). Live carry-forward:
none — the artifact-naming rule it enforced is `example-runner.md`
non-negotiable 6. Logs: `20260831T123115Z_EX-36-leg-th-a.log`,
`20260901T050142Z_EX-36-legs-precensus.log`,
`20260901T093312Z_EX-36-leg-mesh-remainder-precensus.log` (9 in the
archived entry).

**`EX-37` — restore the `ANS-1`/`ANS-3` example imports the rename broke**
✅ *(2026-08-31 19:30 slot; full 69-line entry archived in
`docs/planning/plan-archive.md`, 2026-09-06 weekly review).* Result: the
`__import__` strings re-pointed to the prefixed module names; negative
control Status 1 / 3 s, both cases green (63 s / 128 s); records reproduce
the 08-16 figures with AED columns still blank. Live carry-forward: the
run-to-run Z/S scatter it measured (≤ 5e-8) is the basis of the 1e-6
reproduction controls (ruled 2026-09-02 weekly). Logs:
`20260831T003025Z_EX-37.log`, `20260831T003409Z_EX-37-docrefs.log`.

**`EX-38` — the first `|B₁⁺|` field in ParaView: loaded 4-leg birdcage at
10 MHz** ✅ *(2026-08-31, 15:00 slot; commissioned 2026-08-30 18:00 review,
§5.4 ramp, from `WF-6` step 1 ✅.)*
`examples/ports/06_birdcage_b1_plus_map.py` + same-stem guide (`ports:6`):
two lumped-sheet solves on the 116 085-cell mesh and one combined XDMF
carrying the CG1 `B` phasor (real/imag), `|B₁⁺|` and the phantom cell tags.
Every constant, band and record imported from
`tests/validation/test_birdcage_b1_plus_map.py` (`ANS-1`'s rule), none
restated. Landed `20260831T200401Z_EX-38.log`, Status 0; docrefs
`20260831T200629Z_EX-38-docrefs2.log`, `guide=0`. No homogeneity, absolute
or tuning claim — the map is `WF-6` step 1's gated capability and nothing
more. **Full narrative archived 2026-09-09 → `docs/planning/plan-archive.md`.**

**`EX-39` — the quadrature drive in ParaView: `|B₁⁺|` and `|B₁⁻|` of the
loaded 4-leg birdcage at 10 MHz** ✅ *(commissioned 2026-08-31 03:00 review,
§5.4 ramp, from `WF-6` step 2 ✅; landed 2026-08-31, 16:30 slot.)*
`examples/ports/07_birdcage_b1_quadrature_map.py` + same-stem guide
(`ports:7`): four lumped-sheet solves on the 116 085-cell mesh, the four DG0
curls superposed with `e^{∓jkπ/2}` on the fixture's azimuth index for the co-
and counter-rotating senses. Imports `WF-6` step 2's gated identities
(C4-invariance 0.9818%, mirror 0.8087% against the 5% band, centre
polarisation purity 127.9) and restates none of them. Logs
`20260831T213402Z_EX-39.log` (Status 0),
`20260831T213623Z_EX-39-docrefs.log` (`guide=0`). No homogeneity, absolute or
tuning claim. **Full narrative archived 2026-09-09 → `docs/planning/plan-archive.md`.**

**`EX-40` — the Larmor `|B₁⁺|` ladder in ParaView: 64 and 128 MHz maps of the
loaded 4-leg birdcage** ✅ *(commissioned 2026-08-31 10:30 review, §5.4 ramp,
from `WF-6` step 2b ✅; queued 2026-08-31 18:00 review as §9 item 2, executor
`example-runner`; closed 2026-08-31 21:00 slot, first run green.)*
`20260901T020415Z_EX-40.log` (Status 0, **113 s** at `-n 2`; mesh 24.8 s, six
kept solves ≈ 34 s) plus `20260901T020734Z_EX-40-docrefs2.log`. Both Larmor
rungs on one 116 085-cell mesh (ratio 1.000000, `reused_mesh = True` and
`sweeps[label]["mesh"] is base["mesh"]` asserted), 51 of 51 sample points
valid at each. Gates (i)/(ii) and the P3 control are imported from `WF-6`
step 2b, none restated. No homogeneity, absolute, tuning or convergence claim
at either Larmor frequency. **Full narrative archived 2026-09-09 → `docs/planning/plan-archive.md`.**

### ANS — Ansys benchmark cases (§5.4)

Commissioned by the weekly planning review only, on gated physics only; the
human operator replicates each case in Ansys Electronics Desktop and the
next weekly review adjudicates the returned numbers.

| ID | Title | Status | Tier |
|---|---|---|---|
| `ANS-1` | Loop over a lossy slab at 10 MHz: runnable half of the first AED benchmark | ✅ Closed: no disagreement with the independent solver to diagnose, ΔX stays reported and never gated, and the numeric ruling lives only in the gitignored docs/private adjudication. Any `ans:` case that commits its own `metrics.json` pins that path in the same commit. *History: `docs/planning/chunks/ANS-1.md`.* | standard |
| `ANS-2` | Coil-driven SAR in the loaded four-leg birdcage at 10 MHz: pointwise SAR, whole-phantom power, mass-averaged SAR | 🟡 Open: step 1's runnable half is green with its control asserted as a floor, and nothing absolute is licensed. Step 2 (SPEC rows 4–6) and step 3 (the operator's AED replication) remain open. *History: `docs/planning/chunks/ANS-2.md`.* | heavy |
| `ANS-3` | Two coaxial gapped loops at 10 MHz: runnable half of the second AED benchmark (2-port Z/S; `ANS-2` reserved by §10 for the future B1+/SAR case) | ✅ *(example path restored 2026-08-31 by `EX-37` and re-run green, 128 s; the 08-16 / 08-26 records stand)* | heavy |
| `ANS-4` | Gapped four-leg birdcage, phantom-loaded, four lumped ports: 4×4 S-matrix at 10 / 64 / 128 MHz | ✅ The step-2 family is frozen under the four-attempt rule: no degree-1 ladder on this fixture is in a proven asymptotic range, so a degree-1 extrapolant is not an h → 0 reference. **Larmor verdict banked 2026-09-13 (weekly): AGREE at 128 MHz on step 2d's order-matched rung, AGREE by mechanism at 64 MHz; step 3 (the 64 MHz degree-2 rung, `xl`, priced by 2d) is pre-registered in §10 for the 09-16 review's window; numbers private.** *History: `docs/planning/chunks/ANS-4.md`.* | heavy (≈ 160 s at `-n 2`, one command; measured 125 / 128 s); step 2 **`xl`** |
| `ANS-5` | **Pin the element-order correspondence in every ANS `SPEC.md`/`COMPARISON.md`** — our production `degree 1` is what HFSS calls **Zero Order**, not its default **First Order**; the specs do not say so, and a default-settings replication is a different discretization (operator observation, interactive session 2026-08-28) | ✅ **RULED 2026-08-30 02:15 weekly review** — (a) AED runs at **Zero Order** (matched, the adjudication column) **and** at its default **First Order** (an order-sensitivity column); **Mixed Order forbidden**; our side stays at one order (none of options 1–3 as framed — option 1 for the adjudication column plus a second AED column, our side unchanged, step 3 **not** taken). (b) `ANS-1` **is in scope** for the spec line (state the Maxwell 3D formulation and order AED used). Already-returned numbers at an unrecorded order stand as an "order-unknown" column. Steps 1–2 are documentary and queueable; `ANS-4`'s spec already carries the wording. **Steps 1–2 executed 2026-08-31 00:00 slot — 🟡:** README correspondence table + a *Basis / element order* paragraph in all three SPECs (four `*.md` files, +71/−3, no band or figure moved); the `ANS-1`/`ANS-3` `COMPARISON.md` rows need a **generator `.py`** edit the item's scope forbids — carried as a finding, **priced as step 1b by the 03:00 review (§9 item 2)**. **Step 1b executed 2026-08-31 06:00 slot — chunk ✅** (steps 1, 1b, 2; step 3 ruled not taken): both generators' `_write_comparison` now emit `AED (Zero Order)` / `AED (First Order)` and a `Basis order` row, both cases re-run green on their own asserts (ΔR **1.5838%** vs 2%; `PORT-1` step-4 reproduction **2.98e-05 / 2.92e-05 / 1.71e-06 / 3.33e-10** inside 1%, reciprocity 4.7586e-05 < 1e-3, ‖S‖₂ 0.864809 ≤ 1), census at the standing `dead=53 guide=0 stale=10`. The pre-registered ≤ 1e-8 `metrics.json` negative control **is not a valid discriminator for `ANS-3`** — measured below | smoke (no compute; step 1b ≈ 200 s, measured 61 + 133 s + 125 s control + 1 s census) |
| `ANS-6` | **Copper birdcage, phantom-loaded, four lumped ports: the `ANS-4` fixture with a σ = 5.8e7 S/m coil — the first AED case on a realistic conductor** (operator directive 2026-09-04, interactive session; **serial on `TH-15` ✅ and `TH-14` ✅**; AED side: HFSS *Finite Conductivity* boundary on the coil with Solve Inside off, plus a PEC-coil column) | ⬜ | heavy |


**`ANS-5` — pin the element-order correspondence in the benchmark specs** ✅
*(ruled 2026-08-30 weekly review, steps 1–2 executed 2026-08-31; full
245-line entry archived in `docs/planning/plan-archive.md`, 2026-09-06
weekly review).* Result: our production `degree 1` (N1curl, 6 unknowns/tet)
is HFSS **Zero Order**, the adjudication column; AED's default **First
Order** (20/tet) is the order-sensitivity column; Mixed Order forbidden;
`ANS-1` in scope for the formulation/order line. README correspondence
table and a *Basis / element order* paragraph in all three SPECs; the
`ANS-1`/`ANS-3` `COMPARISON.md` rows regenerated from their generators
(step 1b). The 6 / 20 correspondence was **confirmed by HFSS's own matrix
sizes on 2026-09-04** (`ANS-4` row). Live carry-forward: none. Logs:
`20260831T110240Z_ANS-5-step1b-ans1.log`,
`20260831T110908Z_ANS-5-step1b-ans3-final.log`,
`20260831T111136Z_ANS-5-step1b-census.log`.

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

**`ANS-3` ✅ 2026-08-16** — two coaxial gapped loops at 10 MHz: runnable half *(the execution record and the original commissioning plan are archived verbatim in `docs/planning/plan-archive.md`, entry «§7 ANS-3 full narrative — archived 2026-09-13 (weekly review)».)*
> * **Done-when, met** (`20260816T110354Z_ANS-3-runnable-half-n2.log`, **131 s** wall at `-n 2`, 178 055 cells — mesh 35.9 s, sweep 46.3 s, export solve 21.4 s; `./run_examples.sh -e ans:3 -n 2 -t 500`): every `EX-20` anchor reproduced inside the pre-stated 1% band, misses ≤ **3.67e-06** — raw mutual 0.894543, corrected 0.939849, ‖S−Sᵀ‖/‖S‖ = 2.5494e-05, ‖S‖₂ = 0.861449; Im Z₂₁ = +1.110803269e+00 Ω vs ωM₁₂ = 1.241755 Ω, |Z₁₂−Z₂₁|/|Z₂₁| = 5.8309e-04 (reported, not gated). **Negative control printed first:** the raw rung −10.55% asserted to *fail* the unmoved 10% band; the corrected rung −6.02% inside.
> * **Artifacts:** `metrics.json` (complex 2×2 Z and S, ladder, identities, mesh/timing), `COMPARISON.md` (our columns filled, AED columns blank; Zero / First Order columns added by `ANS-5` step 1b), combined XDMF; every constant imported from `examples/ports/02_package_sparameter_sweep.py` (`EX-20`) and `ports/systematics.py` — `ANS-1`'s rule. Incidental fix landed with it: `scripts/run_examples.sh` issues `timeout -k 30` inside the container.
> * **Carry-forward:** the AED half is the operator's (dashboard Waiting-on-you, behind `ANS-2`) and is also `PORT-10`'s independent adjudication input; re-run green 2026-08-31 by `EX-37` (128 s), the 08-16 / 08-26 records standing.

**`ANS-4` — loaded birdcage 4-port S-matrix at 10 / 64 / 128 MHz: runnable half** ✅ **2026-08-30** *(the commissioning text and the 16:30 execution journal are archived verbatim in `docs/planning/plan-archive.md`, entry «§7 ANS-4 full narrative — archived 2026-09-13 (weekly review)»; the step-2 ladder history and the adjudications are in `docs/planning/chunks/ANS-4.md`.)*
> * **Done-when, met** (`20260830T213415Z_ANS-4-run1.log`, Status 0, **125 s** at `-n 2`, `./run_examples.sh -e ans:4 -n 2 -t 500`, heavy): every gate on every rung of one 116 085-cell mesh (ratio 1.000000, `reused_mesh` asserted) — reciprocity 1.469e-14 / 1.126e-15 / 8.763e-16, σ_max 0.999992805 / 0.999721388 / 0.998974779, C4 spreads 0.0553 / 0.0353 / 0.0214%, 0.0573 / 0.0599 / 0.0370%, 0.1012 / 0.0916 / 0.0654% (pooled separations 166.7× / 671.1× / 576.9× vs the 10× floor); 128 MHz cells/λ **12.5024** ≥ 10.
> * **Records reproduced:** 10 MHz leg (d)'s 4×4 to **1.158e-10** (band 1e-6) and leg (d0)'s column to 2.568e-10 (1e-9); 64 / 128 MHz worst 1.075e-03 / 6.755e-04 against `PORT-11` steps 2/3 (band 1e-2). **Negative control, printed first:** the retired `PORT-0` heuristic at 128 MHz, max|off-diagonal| 0.000000e+00, separation **1.585460** vs the 2e-3 floor.
> * **Artifacts:** `04_birdcage_four_port_10_64_128MHz.py` + same-stem guide, `metrics.json`, `COMPARISON.md` (two blank AED columns, Zero and First Order, per `ANS-5`), `paraview_output/ans4_birdcage_four_port_128mhz_combined.xdmf` (P1-driven at 128 MHz); census `20260830T213718Z_ANS-4-docrefs2.log` `guide=0`. Everything is imported from the `ports:5` / `PORT-9` / `PORT-11` modules, so the benchmark cannot drift from the gate.
> * **Carry-forward:** self-consistency identities on one fixture; the AED adjudication lives on the row, in `docs/planning/chunks/ANS-4.md` and in gitignored `docs/private/` — AGREE at 10 MHz (2026-09-06); the Larmor verdict is the 2026-09-13 weekly's (§2.2, §6, §10).

---


**`ANS-6` — copper birdcage, the `ANS-4` fixture on a realistic conductor**
⬜ *(commissioned 2026-09-04 by operator directive, interactive session — an
exception to "commissioned by the weekly planning review only", recorded
here as such; the weekly review owns its spec text and adjudication as for
every other case. Serial on `TH-15` ✅ and `TH-14` ✅.)* **Why.** `ANS-4`
is the absolute check of the port model at the Larmor frequencies, but on
an 800 S/m coil that no real birdcage resembles; its coil-loss share is
wrong by construction and every tuning-workflow parity claim (§1 step 2)
needs the conductor model checked against AED *before* Phase 6 leans on it.
One case, same geometry, one thing moved: the coil conductivity.
> * **Step 1 (spec).** `examples/ansys_benchmarks/birdcage_copper_four_port/SPEC.md`
>   by copying `ANS-4`'s spec with these changes and no others: coil
>   σ = **5.8e7 S/m** (copper, μᵣ = 1), *Solve Inside off*, HFSS **Finite
>   Conductivity** boundary on every coil face; a **second AED column with
>   the coil as PEC** (HFSS *Perfect E* on the same faces) matching `TH-15`;
>   the `ANS-5` order rule unchanged (Zero + First Order, Mixed forbidden);
>   quantities as `ANS-4` plus the **coil-loss share `P_coil/P_accepted`**
>   per frequency (HFSS: surface loss on the finite-conductivity boundary
>   from the field calculator) — the row that discriminates the conductor
>   model. Our side: `TH-14` (copper) and `TH-15` (PEC) columns.
> * **Step 2 (runnable half).** As `ANS-4`'s script, importing every band
>   from the `TH-14`/`TH-15` gate modules; `metrics.json`, `COMPARISON.md`
>   (AED columns blank by construction) and the private-mode writer
>   (`OPS-32`'s pattern, `aed_results/ans6_aed_results.json`). Heavy tier.
> * **Step 3 (operator replication).** The `ANS-4` PyAEDT script (untracked,
>   `aed/`) adapted: material copper, `solve_inside = False`,
>   `assign_finite_conductivity` on the coil faces, a second design with
>   `assign_perfecte_to_sheets` on them. Goes to the dashboard's
>   Waiting-on-you when step 2 closes. Numbers private, verdict public, as
>   always.
> * **Done-when (§4).** Step 2's harness log with the imported gates
>   asserted; adjudication by the first weekly review after the AED numbers
>   land — AGREE on the S classes **and** on the coil-loss share is what
>   licenses §2.1 to say "conductor model checked externally".

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
   narrowed definition 2026-08-17** (step 2b: the cross-route ladder
   INSIDE the unmoved 5% band at the narrowed width; the width
   convention `w = A/h` is now part of the port model's spec. *The
   three-rung figures this sentence used to quote were the v0.7.2
   reading; the 0.11 image reads 7.7431 → 1.0986 → 1.9222% and
   `OPS-31` reconciles the narrative — §9 item 3, 2026-09-01 18:00
   review*), and
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
4. **Operator directive 2026-09-04 (interactive session) — the conductor
   model.** Both realistic-conductor routes are commissioned and are to be
   completed, in this order: **`TH-15`** (internal PEC bodies, conductor as
   a hole) → **`TH-14`** (Leontovich surface impedance, copper) →
   **`ANS-6`** (the `ANS-4` birdcage with a copper coil, replicated in AED
   with a Finite-Conductivity column and a PEC column). Queued in the
   order item 5's ladder gives (Tier A first, then this lineage); the
   weekly review owns the §10 Phase 6 subgoal it becomes and `ANS-6`'s
   spec text. The
   routes go through the `TH-1` solver and the `PORT-9` surface-term hook,
   not `TH-3`'s ⚠️ option set (standing rule below) — the review confirms
   that reading before step 1 runs.
5. **Operator directive 2026-09-04 (interactive session) — the Ansys
   feature ladder.** The boundary conditions and excitations HFSS users
   rely on for the §1 workflow that this repo lacked, ranked once by the
   operator so that no review has to re-derive the priority. **Reviews
   queue the ladder in this order; an item is skipped only when blocked
   (serial dependency not ✅, or a measured cost the box cannot pay), and
   every skip is recorded in this table with its reason, in the row's
   Note column.** Tier A is cheap linear algebra on solves that already
   pass their gates and comes *before* the conductor lineage of item 4;
   Tier B is real FEM work and comes after it; Tier C is phase-gated and
   is not queued until its phase opens.

   | Rank | Chunk | HFSS feature | Serial on | Note |
   |---|---|---|---|---|
   | **A1** | `POST-6` | Edit Sources (multi-port amplitude/phase) | — | first item; package-level version of `WF-6` step 2 |
   | **A2** | `PORT-14` | Lumped RLC boundary | — | capacitors in the model |
   | **A3** | `PORT-15` | HFSS + Circuit link | `PORT-13` ✅ | tuning at zero field-solve cost. Queued in ladder order 2026-09-04 18:00 review as §9 item 3 — **step 1 is the part that is serial on nothing**: the ladder-network closed form and the termination-reduction algebra, gated by pure-numpy identities (no FEM); gate (i) against `PORT-14`'s in-model solve waits on A2 |
   | — | `TH-15` → `TH-14` → `ANS-6` | Perfect E on bodies → Finite Conductivity → the copper AED case | — | item 4's lineage, between the tiers. `TH-15` step 0 (`mesh-probe`, 🧪 by the §3 rule until step 1 gates it) queued 2026-09-04 18:00 review as §9 item 4 |
   | **B1** | `TH-5` | Radiation boundary | — | existing ⬜ chunk, now dated by this ladder |
   | **B2** | `TH-16` | Perfect E / H symmetry planes | `GEO-25` report | the F-human memory lever. The `GEO-25` report landed 2026-09-04 16:30 (cost exponent ≈ 0.84 at fixed sizing, not r³; 504 642 cells at 0.15 m) — the weekly re-dates the 62 GiB figure from it |
   | **B3** | `TH-17` | Eigenmode solution | `TH-15`, `PORT-14` | Phase 6's first target |
   | **B4** | `TH-18` | Layered Impedance | `TH-14` | last in Tier B |
   | **C1** | `WF-9` | (implant TF excitation, ISO 10974) | Phase 7 open | scope `WF-7` as its consumer |
   | **C2** | `PORT-17` | Wave Port | a benchmark that needs it | low *(renumbered from `PORT-16` 2026-09-09 03:00 review — ID collision with the closed accounting-gap chunk)* |
   | **C3** | `MAT-3` | frequency-dependent materials | Phase 7 open | existing ⬜ chunk |
   | **C4** | Phase 9 AMR | adaptive passes | Phase 6 closed | not a BC; the largest workflow gap |

   What is deliberately *not* on the ladder, because it already exists:
   PEC outer box, lumped ports (`PORT-9`), incident plane wave (`TH-6`),
   projected current drives, the 4-port fixed quadrature (`WF-6` step 2).
6. **Operator directive 2026-09-05 (interactive session) — the XL tier.**
   §5.1 gains a fourth tier: one run per 7 days at up to 512 GiB, 16 ranks
   and 2 h, against the separate `fem-em-solver-xl` compose service,
   commissioned only by the weekly planning review (protocol step 3b),
   enforced by the bash guard and `docs/testing/xl-ledger.md`. **The first
   slot is reserved for the `ANS-4` diagnosis rung** — the operator's AED
   replication (landed 2026-09-04) agrees with our 10 MHz classes and
   disagrees at the Larmor rungs with a frequency trend, and the private
   pre-read names our fixed 116 085-cell mesh's resolution at 128 MHz as the
   first suspect; the 2026-09-06 weekly review adjudicates, opens the
   diagnosis chunk, and spends the slot on its finest rung. Recorded
   negatives measured against the old 64 GiB wall (`TH-11` step 5, `TH-12`)
   are still not automatically reopened; the review re-prices one only
   with an XL slot in hand.

**Standing rules.** Do not add new features to `⚠️` subsystems. Do not
trust a chunk's status without a log — any §7 status that is not `✅`
reads "unknown", not "probably fine". Since `OPS-19` (2026-08-16), the
docrefs checker exits 0/1/2 (clean / hard violation / staleness-only) and
prints a machine-readable `RESULT:` line — chunks that run examples gate
on **`exit != 1`**, and read staleness (`exit 2`) as information, not
failure.

### On deck — maintained by the scheduled daily review

The next scheduled implementer run takes the **first** item below that is not
marked done or blocked (see `docs/automation/implementer-run.md`). **Restock
floor (operator directive 2026-09-13): ≥ 240 predicted slot-minutes of open,
unblocked work and ≥ 5 items** — each item's costed wall clock plus 15 min
fixed, running total written beside the list, shortfall stated in minutes when
the floor is not met (daily-review.md step 6). Items are ordered, each sized
for one run: ≤ 1 h wall clock, ≤ 20 min per compute command. Prefer items
that do not depend on each other; where the critical path is genuinely serial,
say so in the item. If every item is done or blocked, the drain instruction at the
end of this section applies: **stop and journal**.

**Three rules enacted 2026-09-12 18:00 review (operator directives of
2026-09-12, `247290d`):** (1) **a slot that commits its item with a clean
tree before minute 30 takes the next open item** (implementer-run.md step 2 —
never on a dirty tree, never an item whose stated dependency has not landed,
one outcome commit and one journal entry per item); (2) **a step family is
capped at four attempts** since its last sub-step that landed a gate — a
numbered step plus all its lettered sub-steps is one family, relettering
does not reset the count, a landed gate does — and at four the family is
frozen: a review re-scopes the question as a new numbered step or banks the
measured negative, and never queues a fifth letter (this replaces the former
"items that fail twice get rescoped" sentence, which never fired); (3)
**every item below names the status its result can move** (daily-review.md
rubric element 7) — an item that cannot is not queued. Families frozen at
enactment: `WF-6` step 4 (4h–4k since 4g), `ANS-4` step 2 (2a‴, 2e, 2f, 2g
since 2a″), `PORT-14` step 2 (2, 2b–2e; no gate landed) — each carries its
ruling in §7.


Last reviewed **2026-09-13, 10:30 review**. *(The 2026-09-12 18:00 interval
narrative is archived verbatim in `docs/planning/plan-archive.md`.)*

**Interval (09-12 18:00 → 09-13 10:30, one review interval doubled): the
03:00 review did not run.** The account session limit ("resets 7:10am")
killed the 02:15 weekly mid-edit and swallowed the 03:00 review and the
04:30 / 06:00 slots before they started (launcher logs 117 / 117 / 65 / 65
bytes). Of the six slots that fired, two did chunk work and consumed the
whole 18:00 queue under the take-next rule, two stopped on the drained
queue, two stopped on the stranded weekly diff.

| Slot | Chunk | Outcome |
|---|---|---|
| 19:30 | `OPS-46` step 1, `PORT-19` step 6, `OPS-46` step 2 (WF, ANS, PORT), `OPS-46` step 3 (MAG, GEO) — four items in one slot | `a962e78` tooling landed, anchors green, nothing moved; `b260450` `ports:3` 195 s / `ports:13` 43 s green, census exit 0, `PORT-19` stays ✅; `2592c5b` / `efb05ed` / `8404422` and `c96873e` / `ac1b22c` — every anchor green, one commit per family |
| 21:00 | `OPS-46` step 3 (OPS), step 4 (TH, MAT, POST, EX), re-measurement | `b27e690`; `7abb7f0` / `294603d` / `dfa6377` / `6c0c529`; closure `1f4e706`: plan 927 147 → **806 962 B**, 73 tracked chunk files, leak audit rc 0 — `OPS-46` 🟡 → ✅ with (iii) operator-pending |
| 22:30, 00:00 | — | queue drained; stopped and journaled |
| 02:15 weekly | ran on schedule | archive rotation committed (`bf1ea49`), then died on the limit with +566/−18 plan lines uncommitted |
| 03:00 review, 04:30, 06:00 | — | did not start (session limit) |
| 07:30 | — | first encounter of the stranded diff, stopped per step 1 (`9ed6195`) |
| 09:00 | — | second encounter: parked on `recovered/20260913T140010Z`, queue drained, stopped (`ef8dc53`) |

**Operator activity:** one interactive session (09:48–10:10) landed the
recovered weekly diff on `main` (`c1d7200`, `63eb49c`), enacted the
slot-minutes restock floor (`ca524af`), and made the agent-definition edits
`OPS-46` anchor (iii) waited on plus the five carried one-liners and the
`implementer.md` footer (`2a0ca4d`, `86bb3e7`) — dashboard items 1 and 7
close. No `recovered/*` branch remains. This review ran on
`claude-fable-5-1`, no override
(`logs/automation/20260913T153001Z_daily-review.log`).

**Tree and branches.** Clean at review start; `fem-em-solver` Up 2 days;
the four `attempt/*` branches (`TH-15-step2proper`, `WF-6-step4b/4c/4e`)
kept unchanged on the 2026-09-09 18:00 ruling; no new attempt, nothing to
rescope (step 4). The session-limit loss is the second Sunday running for
the 02:15 weekly (09-06, 09-13) and this time took the 03:00 review and
two slots with it — an operator matter, on the dashboard.

**Audit (§4).** `OPS-46` ✅ (`1f4e706`) — `auditor` **PASS**, re-cited by
this review: plan **806 962 B** and **73** chunk files
(`20260913T020712Z_OPS-46-step4-measure-after.log:34–35`); leak audit
`leak_audit_rc=0`, Status 0, 17 s
(`20260913T020720Z_OPS-46-step4-leak-audit.log:34–42`); per-family
`[anchor] … PASS` gates 15 / 11 / 11 / 45 with 0 FAIL in the TH / MAT /
POST / EX step-4 logs; `git show --stat 1f4e706` docs-only; smoke tier
honest (worst window 17 s). **Anchor (iii) exercised here:**
`plan-navigator` answered a chunk-only question from
`docs/planning/chunks/OPS-46.md:15` with the citation (the leak-audit log,
17 s, 73 files), which this review checked against the file directly — the
corpus edit (`2a0ca4d`) works. Two caveats recorded in the row: anchor
(iv)'s `< 850 000 B` was a printed `wc -c` compared by hand, not a scripted
assert (a rider on item 6 below); and the row's "74 rows" is the step-1
census discrepancy — 73 IDs were listed and moved, `GEO-17` / `ANS-5` are
over 2 KB but in no list. `PORT-19` step 6 was a regression record under an
existing ✅, not a status change — no audit. **Example step (§5.4):** `OPS-46`
gates tooling, not a physics capability; no example chunk opens.

**§10 assessment (step 5).** No gap: the weekly enumerated the
tuned-birdcage chain (§10, ten numbered steps) and named five independent
steps for this queue plus `OPS-47`; nothing is invented here. Row
housekeeping done in this commit: `TH-15`'s state line refreshed from its
history (weekly flag 4 — it read "step 1 of 3 landed" against 3a ✅ 09-06,
2d ✅ 09-07, 3b ✅ 09-09, 2h 🧪 09-09).

**Restock (step 6).** Nine items, each with its predicted slot-minutes,
running total **192 of the 240-minute floor — shortfall 48 min**, stated
rather than filled. What exists and is not queued, and why: `ANS-4` step 3
(`xl`; cannot run before Thursday 09-17 02:00 — the 09-16 weekly's to copy
into `xl-queue.env`); `WF-6` 4l, `ANS-4` 2h, `PORT-14` 2f (families frozen);
`PORT-15` steps 2–3 (serial on item 2 landing); `TH-14` step 1 (serial on
item 8's facet tags); `TH-17` step 1 (serial on items 2 and 8); the `-n 2`
MUMPS drift's third draw (no status it can move). A note on the metric, not
a change to it: items 2–4 and 8 write `src/` or test code and will use most
of a slot whatever their window minutes say; the directive counts windows,
and this review does not pad them.

**Residual `main` reds at `-n 2`: 3 deliberate/known**, plus the padding
module's red at `-n 4` (known-issues, 2026-09-09). The `WF-6` ×0.0095 red is
opt-in only and is not counted.

**⚠️ Standing constraint on the compose allow — read before editing that
file.** `docker-compose.yml` line 9 is `- ..:/workspace`, so write access
to it is write access to *what the container mounts from the host*. The
operator granted this knowingly and narrowly (2026-08-22). **Edit only
`environment:` keys. Do not touch `volumes:`, do not add a mount, do not
widen a path, and do not change the memory limit (**128 G**, raised from
64 G by operator directive 2026-08-24) — in this or any future chunk.**
*(The `fem-em-solver-xl` service added 2026-09-05 is the one operator-
authorized exception — a second service with its own 512 G limit under the
`xl` profile; the constraint applies to it verbatim, and chunks do not
edit it either.)* A
chunk that believes it needs a mount change is a **blocked finding for the
operator**. The `Edit(docker/.claude/**)` caution stands for the same
reason: a nested `.claude/` is a settings-override surface. One surviving
mechanic: `git checkout` cannot swap `docker/Dockerfile` /
`docker-compose.yml` in this sandbox — bind-mounted, "Device or resource
busy", a *silent* wrong-content switch — so any chunk that must move them
uses the Edit tool and verifies `git status --porcelain`.

**Runner trap (2026-08-29 13:30, 2026-08-30 12:00 and 2026-09-01 04:30 —
three occurrences in 21 slots, intermittent; 0 of the last 31):** if
`./run_examples.sh` fails with
`permission denied … /var/run/docker.sock`, run the runner's inner command
verbatim through `run_and_log.sh` (`docker compose exec -T fem-em-solver
bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode &&
PYTHONPATH=/workspace/src timeout -k 30 <T> mpiexec -n 2 python3
examples/<path>.py'`) and journal the denial; do not spend the slot on it.
The host runner stays the documented entry point and the substitution
stays the fallback. **Allowlist trap (12:00 slot):** the harness entry is
the repo-relative `scripts/testing/run_and_log.sh *` — an absolute path is
denied; write it relative.

**Standing rules for every item below (from the 10:30 review, kept):**
(a) an `EX-*` item may add an *additive* return key or keyword to a gate
fixture's helper it imports, provided the gate module is re-run green
through the harness in the same slot and the diff is disclosed; (b) guide
artifact references carry the full filename; (c) a `src/` change beyond an
item's letter follows ruling (a) above — disclosed, its pre-existing gate
re-run green in the same slot; **(d) (added 2026-09-05 10:30) a slot that
parks its item on `attempt/*`, or otherwise leaves it neither done nor
runnable, marks the §9 item BLOCKED with the unblock condition in the
*same* commit as the record** — the next slot reads §9 first, and an
unmarked item costs it the ten minutes the 09:00 slot spent on
`e49cb67`; **(e) (added 2026-09-05 18:00) every negative-control factor
in an item is labelled *asserted* or *predicted*: asserted only when a
prior measurement of the *same* comparison on the *same* fixture backs
it (cite the log line), predicted otherwise — and a predicted factor is
printed beside the measured one, never asserted. An executor that meets
a failing pre-registered assertion whose label is missing stops and
reports the negative result; it does not decide in-slot** (`EX-49`,
2026-09-05 15:00, ruled by the 18:00 review; `MAT-6` step 11, 2026-09-06
07:30, ruled by the 10:30 review); **(f) (added 2026-09-06 18:00) a band
an item states against an *analytic* comparand that the executed
fixture's own CAD or mesher cannot meet is re-registered by measurement
on the same quantity where both sides are the fixture's numbers, said
so in the docstring and the journal, and the review ratifies or reverts
it** (`TH-15` step 3a, 16:30 slot — ratified above, ruling (2)); it is
never widened silently and never on a quantity that was already green.
**(g) (added 2026-09-08 10:30)** every pytest window below runs with `-s`
— two windows (≈ 9 min) were lost this interval to swallowed prints
(`TH-15` step 2f, `OPS-41`), each re-run only because the executor
noticed; a log without the readings is a window not spent.

*(The 18:00 queue's five items are done: `OPS-46` steps 1–4 (`a962e78`,
`2592c5b`/`efb05ed`/`8404422`, `c96873e`/`ac1b22c`/`b27e690`,
`7abb7f0`/`294603d`/`dfa6377`/`6c0c529`, closure `1f4e706`) and `PORT-19`
step 6 (`b260450`). Their item texts are in `git show 122f7f7` and
`docs/testing/attempts.md`.)*

**Every window below that uses §5.1 durable capture copies the idiom
verbatim, trailing `; exit $rc` included.** Since `OPS-45` the footer honours
a `[capture] rc=` line only when it is the *last* output line. **Every
`OPS-47` window runs its script inside the container** (`docker compose exec
-T fem-em-solver bash -lc 'cd /workspace && python3 scripts/…'` through
`run_and_log.sh`) — host `python3` is denied. **Every pytest window runs
with `-s`** (rule (g)).

**Predicted slot-minutes (rubric element 3 + 15 min fixed), running total:**
item 1 → 19 · item 2 → 44 · item 3 → 65 · item 4 → 88 · item 5 → 111 ·
item 6 → 127 · item 7 → 143 · item 8 → 166 · item 9 → **192**. Floor 240:
**shortfall 48 min**, stated, not filled (see the narrative above for what
exists and why it is not queued). Items 1–6 and 8 are mutually independent;
item 7 depends on item 6; item 9 is taken only when 1–8 are all done or
blocked.

1. ✅ **DONE 2026-09-13 12:00 slot** (`20260913T170259Z_WF-6-step5.log`:
   24 passed / 9 skipped, Status 0, 156 s at `-n 4`; `WF-6` → ✅).
   **`WF-6` step 5 — register the two-rung convergence statement and close
   the F-small B₁⁺ deliverable (the Phase-5 exit item)** (implementer; tests
   only, `tests/validation/test_birdcage_b1_plus_closed_form.py`; complex;
   heavy by measurement; `-n 4`; `main`; independent; **19 slot-min**:
   204 + 34 s windows + 15).
   **Why:** the 2026-09-13 weekly's Phase-5 exit decision (§10): the 09-09
   rule fired, subgoal 4's B₁⁺ target is the convergence statement, and this
   step registers it. Not a 4l — nothing here diagnoses ×0.0095.
   **The change:** on the default `LADDER` (×1, ×0.012; `ACTIVE_LADDER` and
   the ×0.0095 opt-in untouched, off), new step-5 tests:
   **Anchors (asserted):** (i) the ×1 worst-radius four-copy spread of
   `|B₁⁺|` reproduces **5.2506 %** and the ×0.012 spread **2.0719 %** at
   rtol 1e-3 — records backed by 4g on the same fixture, statistic and
   width (`20260909T200431Z_WF-6.log:1982–1994`, 204 s at `-n 4`,
   test-results row 2026-09-09 20:07:55); (ii) the fall is monotone —
   `spread(×0.012) < spread(×1)` and `covariance(×0.012) < covariance(×1)`
   (3.6159 % → 1.6815 %), the identity form; (iii) the existing anchors
   unchanged — cell counts at `CELL_COUNT_BAND`, covariance ≤ the imported
   5 %, power residual ≤ the imported 1e-2, cw separation ≥ 5×.
   **Printed, never asserted (rule (e)):** the interior CV of `|B₁⁺|` on
   both rungs beside step 4a's filament closed-form CV; the ×1 eleven-point
   miss against `S₁₁` (the §10 record: ≈ 3.2 % centre, ≈ 5.3 / 7.9 % at
   0.4R / 0.5R).
   **Negative control (asserted, by record, already in the module):** the
   cw-weight spread `RECORDED_CW_SPREAD` 0.951975 against the ccw records —
   the ≥ 5× separation is the control; no new factor is introduced.
   **Tier / ranks / cost:** heavy by measurement (204 s at `-n 4`, 4g),
   `timeout -k 30 1200`, complex build, `tests/environment` first, `-s`.
   **Traps:** `-n 4` is the record width — the `-n 2` MUMPS drift
   (known-issues 09-09) shows as a 1e-4-class miss at other widths, and 4g
   ran at `-n 4`; `RECORDED_X1_WORST_SPREAD` already exists at a 10 %
   tolerance for the 4h flag-off control — the rtol 1e-3 pair is
   *additional*, delete or loosen nothing; do not enable the ×0.0095 rung;
   no pipe.
   **Same commit:** §2.2's B₁⁺ bullet (the sentences from "Its closed-form
   gate (step 4, 2026-09-07/08) is still parked" to "says how",
   `PROJECT_PLAN.md:358–369`) re-worded to the convergence statement in
   §10's Phase-5-exit words; the §7 `WF-6` row 🟡 → ✅ with a state line
   written from that statement; known-issues' ×0.0095 entry untouched
   (banked, OPEN). The §6 row-5 sentence is the weekly's — leave a one-line
   pointer, do not restructure.
   **Scope:** a convergence statement on F-small at 10 MHz, CG1; no
   homogeneity, absolute, C95.3, closed-form-B₁⁺, Larmor or human-scale
   claim.
   **Status it can move:** `WF-6` 🟡 → **✅** on the re-scoped target, and
   §2.2's clause with it.
   **Negative result:** (i) or (ii) red ⇒ an `OPS-18`-class record drift —
   known-issues entry with the readings, row stays 🟡, stop; never widen the
   rtol.

2. 🚫 **BLOCKED 2026-09-13 12:00 slot — anchor (i)'s comparand is
   mis-registered; code parked on `attempt/PORT-14-step3-20260913T172330Z`
   (`86c93f6`).** (0), (ii), (iii) and the negative control green; (i) red
   at 3.119e-03 vs rtol 1e-3 because 1.064081e-02 is step 2b's *pooled fit*,
   which this plan's own 2d reading puts at 0.99688–0.99714× `C/terminal − 1`
   (`:4208–4209`) — the derived κ(64) 1.060762155e-02 matches 2d's P1 record
   to 1.457e-07. Also: "scale by `(1 + κ)`" is sign-inverted — 2e's fitted
   ×0.989446732 is `1/(1 + κ)`, which is what the parked code implements.
   **Unblocks when** a review re-registers (i) against 2d's `C/terminal − 1`
   record (and corrects the sign text); then the parked branch re-runs as-is.
   Logs `20260913T171434Z_PORT-14-step3-64mhz.log` (Status 1),
   `…171649Z_…-10mhz.log`, `…172026Z_…-128mhz.log` (Status 0).
   **`PORT-14` step 3 — the κ-derived width route, registered at 64 MHz,
   out-of-sample at 128 MHz (the tuned-birdcage chain's first step)**
   (implementer; one additive `src/` opt-in + tests in
   `tests/validation/test_port_lumped_rlc_termination.py`; complex; heavy by
   ceiling; `-n 2`; `main`; independent; **25 slot-min**: ≈ 3 × 191 s + 15).
   **Why:** §10's chain step 1 and the 09-16 weekly's watch condition; the
   step-2 family is frozen on a positive-but-unregistered reading (2e). The
   scoped text is the `PORT-14` blockquote's "Step 3 scoped 2026-09-13".
   **Trap first, it decides the design:** `_exact_shares` lives in
   `tests/validation/test_birdcage_power_identity.py:313`, not in `src/` —
   `src/` cannot import `tests/`. Lift the `C/terminal − 1` computation into
   `src/` (beside `superpose_drives` in `ports/superposition.py`, or a new
   `ports/shares.py`) and assert **(0)** the lifted function reproduces the
   test helper on the 4-leg fixture's P1 drive at rtol 1e-12 before
   anything else.
   **The change:** an opt-in keyword on the lumped-sheet law (default off)
   scaling the told width by `(1 + κ)`, **κ computed in-run** from the ε = 0
   solve's `C/terminal − 1` — never fitted, never a literal.
   **Anchors (asserted):** (i) the derived κ(64) reproduces 2d's pooled
   **1.064081e-02** at rtol 1e-3 (`e92e34e`, same fixture); (ii) with the
   derived width both 64 MHz lossless residuals on the 116 085-cell gate
   mesh ≤ `REDUCTION_BAND` 1e-3 (2e's fitted-width reading 1.190127e-04 /
   9.581734e-07, `20260912T183330Z_PORT-14-step2e.log:3825–3827`, fitted
   width within 3e-4 of the derived one); (iii) `REDUCTION_FLOOR_F_SMALL`
   at 10 MHz reproduces on the *uncorrected* route, unmoved.
   **Negative control (asserted, by record):** the uncorrected 64 MHz miss
   1.354202e-02 / 5.021261e-04 (step 2; 2e reproduced it to 2.8e-07 /
   7.6e-08, `…step2e.log:1886, :1893`).
   **Printed, *predicted* under 1e-3, never asserted:** the corrected 10 MHz
   pair; the 128 MHz pair with its own in-run κ(128) — the out-of-sample
   reading a review decides on.
   **Tier / ranks / cost:** heavy by ceiling: 2e's 64 MHz pair (ε = 0 +
   corrected) was 191 s at `-n 2`; three pairs ≈ 10 min in one or three
   windows, `timeout -k 30 1200` each, `-s`.
   **Traps:** default-off so every existing gate is unchanged (rule (c);
   if the lift touches `test_birdcage_power_identity.py`'s import path,
   re-run that module green in the same slot, 104 s); `-n 2` is this
   module's record width — `OPS-41`: the point-sampled `V` carries a 1e-4
   width sensitivity, never compare a record across widths; no pipe.
   **Scope:** registers the route at 64 MHz; 128 MHz is a printed reading;
   no tuning, resonance or `TH-17` claim.
   **Status it can move:** `PORT-14` 🟡 → **✅** on (0)–(iii) green, with κ
   carried as the sheet's **named systematic** (09-06 ruling) and `TH-17`
   barred from gating a mode frequency tighter than it; `PORT-15` gate (i)
   unblocks (chain step 2, the next review writes it into §7).
   **Negative result:** (ii) red with the derived width ⇒ the fitted and
   derived κ differ by more than the residual slope allows — known-issues
   entry, row stays 🟡, stop, no fit.

3. ✅ **DONE 2026-09-13 13:30 slot** (`20260913T183446Z_TH-19-step3-10MHz.log`
   / `20260913T183723Z_TH-19-step3-128MHz.log`: 15 passed each, Status 0,
   134 / 118 s at `-n 8`; degree-2 (a) 4.6e-15 / 8.9e-15, (b) 6.8e-11 /
   1.8e-12 — both green; production order to the 09-16 weekly).
   **`TH-19` step 3 — the two degree-2 power identities on the sheet-driven
   4-leg birdcage at 10 and 128 MHz** (implementer; tests only, new tests on
   the pattern of `tests/validation/test_coil_loading_degree2_pair.py`;
   complex; heavy; `-n 8`; `main`; independent; **21 slot-min**: ≈ 6 min +
   15).
   **Why:** the weekly's `TH-19` outcome-(a) ruling (§10): the production
   order is live again because the `ANS-4` verdict measured the degree-1
   128 MHz entries 5–7 % from their order-matched value, and the objection
   has never been tested on the sheet drive, which bypasses the projection
   (`ports/lumped.py:480–483`) — that bypass is the object under test.
   **The change:** `run_lumped_sheet_port_case(…, degree=2)` (the driver
   takes `degree`, `ports/lumped.py:422`), single drive P1, 116 085-cell
   mesh, 10 and 128 MHz.
   **Anchors (asserted):** (a) `PORT-16`'s exact discrete power identity
   `P_src,exact = P_vol + P_sheet,exact` at the imported
   `DISCRETE_IDENTITY_RTOL` 1e-6 (`test_birdcage_power_identity.py:227`);
   (b) the reactive identity `Im P_src = 2ω(W_m − W_e)` at the `TH-12`
   family band, imported from that module, never restated. `W_e / W_m`
   printed beside degree 1's.
   **Negative control (asserted):** degree 1 reproduces `PORT-16` step 1's
   four readings — the same module's own records
   (`20260907T110826Z_PORT-16.log`, 23 passed, 104 s).
   **Tier / ranks / cost:** heavy; priced by `ANS-4` 2b — degree 2 on this
   mesh solved four drives in 178 s at `-n 16` (≈ 16.6 GiB) ⇒ two single
   drives at `-n 8` ≈ 3–4 min, plus the degree-1 control ≈ 6 min;
   `timeout -k 30 1200`; print `ru_maxrss` per rank (`OPS-43`); durable
   capture with `; exit $rc`.
   **Traps:** do not route the sheet drive through the injector — the
   untouched bypass is the point; a `SpatialCoordinate`-bearing facet
   integral on the gmsh mesh needs a pinned `quadrature_degree` (`POST-5`
   step 1, nine-minute compile); a single drive needs no sweep and no
   reuse; `-s`.
   **Scope:** two identities at degree 2 on one fixture; no accuracy claim;
   no default change in-slot.
   **Status it can move:** none directly — both green sends the
   production-order decision to the 09-16 weekly with both fixtures
   identity-clean; a red identity opens the gauged degree-2 formulation
   chunk `TH-12` step 3 named and adds the reading to the `TH-13`-era
   degree-2 known-issues entry. The `TH-19` row records the outcome either
   way.
   **Negative result:** report the residuals, known-issues addendum, stop.

4. ✅ **DONE 2026-09-13 13:30 slot** (`20260913T185043Z_POST-6-step3.log`:
   15 passed, Status 0, 191 s at `-n 8` — (i) C16 0.8102 %, (ii) mirror
   0.6769 %, (iii) 3.961e-15; module regression `…185405Z_…` 24 passed / 4
   skipped at `-n 2`; `POST-6` → ✅).
   **`POST-6` step 3 — the 32-port ccw quadrature drive on `PORT-13`'s
   fixture through `superpose_drives`, gated on C16 invariance of `|B₁⁺|`**
   (implementer; tests in `tests/validation/test_port_drive_superposition.py`;
   complex; heavy; `-n 8`; `main`; independent; **23 slot-min**: ≈ 8 min +
   15).
   **Why:** the row's re-scoped done-when (weekly 09-13, `auditor`
   DEMOTE(scope) concurring): step 1's anchors are met, the 09-06 "step 2"
   is void, and the original 32-port quadrature gate has never run.
   **The change:** the 32-ring-port high-pass fixture imported from
   `tests/validation/test_port_birdcage_ring_matrix.py` (never copied), the
   16-fold ccw quadrature weights through `superpose_drives` at 10 MHz under
   `PORT-19`'s reuse default.
   **Anchors (asserted):** (i) C16 invariance of the CG1 `|B₁⁺|` map at the
   imported `WF-6` 5 % band (the b1_plus module's constant); (ii) the mirror
   identity; (iii) `PORT-16`'s exact power identity on the superposed field
   at `DISCRETE_IDENTITY_RTOL` 1e-6.
   **Negative control:** the cw / mis-paired weights. **Asserted** only on
   the comparison a record backs — the 4-leg `RECORDED_CW_SPREAD` 0.951975
   with its ≥ 5× separation; on the 32-port fixture the cw factor is
   ***predicted*** and printed beside the measured one, never asserted
   (rule (e)).
   **Tier / ranks / cost:** heavy; `PORT-13` measured 9–10 s/solve at
   `-n 8` (windows 271–274 s, test-results 2026-09-04 17:09–17:14) ⇒ 32
   drives ≈ 6 min with reuse, plus the CG1 projection ≈ 8 min;
   `timeout -k 30 1200`; durable capture, `; exit $rc`.
   **Traps:** point samples through `evaluate_vector_field_parallel`, never
   `f.eval`; `cell_tags.values` is rank-local; the ring-sheet
   triangulation is two-state under the rotation (`GEO-26` step 3, `EX-45`)
   — compare at rotated points, never by facet index; `-s`.
   **Scope:** 10 MHz only; no homogeneity, absolute or Larmor claim; the
   `WF-6`/`WF-7` re-pointing clause is dropped (weekly).
   **Status it can move:** `POST-6` 🟡 → **✅** on (i)–(iii) green.
   **Negative result:** (i) red is a finding on the 32-port fixture's C16 —
   known-issues entry, row stays 🟡, stop.

5. **`WF-7` step 0 — the F-human cost probe: one single-drive degree-1
   lumped-sheet solve on the `GEO-25` rung at 64 MHz, memory and time
   printed** (implementer; a filed probe script
   `scripts/probes/wf7_step0_f_human_cost.py` on the `OPS-30` survivors'
   pattern; complex; heavy; `-n 8`; `main`; independent; 🧪 by the §3 rule;
   **23 slot-min**: predicted 3–8 min + 15).
   **Why:** §10 2026-09-13: the XXL window of 09-19 cannot be commissioned
   without a measured memory price at human scale, and §5.1 forbids marking
   one without it. This number is what the 09-16 weekly reads.
   **The change:** the F-human fixture from
   `tests/validation/test_birdcage_f_human_rung.py` (record 504 642 cells,
   32-ring-port longitudinal layout), 64 MHz, degree 1, one driven sheet +
   31 terminated through `run_lumped_sheet_port_case`; print cells,
   unknowns, factorisation time, `ru_maxrss` on every rank and summed
   (`OPS-43`'s instrumentation).
   **Anchor (asserted):** the cell record only, at `GEO-25`'s imported band.
   Everything else is printed.
   **Negative control:** the *prediction* is the control — 11–33 GiB and
   3–8 min from the two priced degree-1 points (`TH-11` 0.99 M cells /
   64 GiB; `PORT-13` 270 k / 5.7 GiB); a reading outside that bracket is the
   finding, printed.
   **Tier / ranks / cost:** heavy, `-n 8`, `timeout -k 30 1200`, durable
   capture with `; exit $rc`; include the `GEO-25` mesh build in the window
   (its own gate ran ≈ 3.5 min); container memory limit 128 G, so the upper
   prediction fits.
   **Traps:** orphan check `pgrep -c python3` inside the container before
   and after (never `pgrep -f "python3 -m pytest"`); no `f.eval`; one
   command, one window — if it is killed, check for orphaned ranks before
   anything else (§5.1).
   **Scope:** one reading; no physics, no gate, no F-human claim.
   **Status it can move:** the §7 `WF-7` row ⬜ → **🧪** with the reading as a
   step-0 line; the 09-16 weekly's XXL commissioning reads it.
   **Negative result:** OOM or a wedge ⇒ the failure *is* the reading —
   record it (known-issues), recover the container per known-issues, stop.

6. **`OPS-47` step 1 — the tooling: `chunks` learns blockquote narratives,
   with the byte-identity refusal, a scripted size assert, and a dry run
   over the four blocks** (implementer; docs/tooling only, no `src/`, no
   test module, no band; either build; smoke; `-n 1`; `main`; independent;
   **16 slot-min**).
   **Why:** the §7 `OPS-47` row (weekly 09-13): the four `>`-blockquote
   narratives under open chunks are 4 431 lines = 48 % of the plan, and the
   archive contract forbids compressing them but not moving them byte for
   byte.
   **The change:** extend `scripts/maintenance/rotate_plan_archive.py chunks`
   per the row — the contiguous `>` block(s) under a §7 family table naming
   one chunk move verbatim to `docs/planning/chunks/<ID>.md`, appended after
   the row history, replaced by one pointer line; refuse unless the re-read
   file span equals the extracted span; never overwrite; `--dry-run`,
   `--census`. **Rider (auditor caveat on `OPS-46`, 2026-09-13):** anchor
   (iv)'s `< 850 000 B` was a printed `wc -c` compared by hand — add a
   scripted size assert to the move script so step 2's re-measurement is an
   assert, not a reading.
   **Anchors (asserted, each in a footered harness log):** (a) leak-check
   positive control — a planted synthetic value in a scratch file under
   `docs/planning/chunks/` is caught (non-zero, file named), removed, exit 0
   on the tree; (b) self-test on a *copy* of the plan under gitignored
   `logs/`: move `POST-6`'s block (157 lines, the smallest) — file span
   `cmp`-equal to the extracted span, the copy shrinks by exactly (span
   bytes − pointer bytes), `git diff --stat PROJECT_PLAN.md` empty; (c)
   `--dry-run` over the four blocks lists them with line counts matching
   `measure_plan_sections.py --blocks` (`WF-6` 2 295, `TH-15` 1 243,
   `PORT-14` 736, `POST-6` 157 at the weekly's measurement — re-measure, the
   weekly's own edits shifted lines).
   **Negative control (asserted):** one byte altered in the extracted file
   ⇒ refusal, non-zero, the copy unchanged (`cmp` against its pre-run copy).
   **Tier / ranks / cost:** seconds per run; smoke; `-n 1`, no `mpiexec`;
   budget the slot for the code.
   **Traps:** Grep for a block, never Read the plan whole; the blocks carry
   nested `>` lines and `\|`; a block may be several contiguous `>`
   paragraphs separated by bare `>` lines — the span is from the first `>`
   line naming the chunk to the last `>` line before a non-`>` line; commit
   with a literal multi-line message via `-F`; no pipe in the harness
   command.
   **Scope:** nothing moved on the real plan; no row edited by hand.
   **Status it can move:** `OPS-47` ⬜ → 🟡 (tooling landed, (a)–(c) green).
   **Negative result:** the positive control is not caught ⇒ stop,
   known-issues, mark item 7 BLOCKED in the same commit; the self-test fails
   ⇒ fix in-slot or park on `attempt/*` and mark item 7 BLOCKED.

7. **`OPS-47` step 2 — move the four blocks, one commit per chunk, and
   re-measure the plan** (implementer; docs only; smoke; `-n 1`; `main`;
   **depends on item 6 landing — if `OPS-47` step 1's commit is not on
   `main`, skip to item 8**; **16 slot-min**).
   **The change:** `POST-6`, `PORT-14`, `TH-15`, `WF-6` in that order
   (smallest first), each from a spec whose pointer line names the chunk
   file; one commit per chunk.
   **Anchors (asserted, per chunk, in the journal with the harness log):**
   (i) the moved span re-extracted from git at the pre-commit revision is
   `cmp`-equal to the chunk-file span; (ii) `check_private_leak.py --audit`
   exit 0 after each chunk; (iii) plan line count before and after each move
   via `measure_plan_sections.py`, recorded — and the row says plainly
   whether the 4 000-line guide is met (*predicted* not met: ≈ 9 200 − 4 431
   ≈ 4 800 lines; a miss is recorded, never a widened guide); (iv) every §
   reference in `CLAUDE.md` and `docs/automation/*.md` still resolves
   (grep each `§N` / `§N.M` against the plan's headings).
   **Negative control (asserted, once, before the first real move):** the
   tool refuses a spec naming a chunk with no block.
   **Tier / ranks / cost:** seconds per run; smoke.
   **Traps:** items 1–4 above and several known-issues entries cite these
   blocks by plan line number — after the move a line cite is stale; the
   journal lists each cite it saw and points it at the chunk file, the
   review fixes the rest; the `TH-15` block spans the `TH` table's
   blockquote *and* a `>` "Done-when" paragraph — the span is the whole
   contiguous block; `WF-6`'s block is 2 295 lines of `\|`.
   **Scope:** these four blocks only; no glyph, no band.
   **Status it can move:** `OPS-47` 🟡 → **✅** when (i)–(iv) hold on all four
   and the guide question is answered in the row.
   **Negative result:** any (i) mismatch ⇒ do not commit that chunk (or
   revert), journal the chunk and byte offset, stop.

8. **`TH-15` step 3 — the birdcage as a PEC hole: `PORT-9`/`PORT-11`'s three
   gates at 10 / 64 / 128 MHz on `birdcage_port_domain(as_hole=True)`, plus
   the lossless power identity** (implementer; `src/` plumbing if needed +
   tests; complex; heavy; `-n 2`; `main`; independent of items 1–7;
   **23 slot-min**: predicted 5–8 min + 15).
   **Why:** §10's chain step 4, "serial on nothing" — the mesh route (3a,
   80 181-cell hole vs the 116 085-cell solid,
   `tests/mesh/test_birdcage_conductor_hole.py`) and `gap_cell_tags` (3b)
   are ✅; the solve on it has never run. Unblocks `TH-14` step 1 (chain
   step 7) on its facet tags.
   **The change:** the hole fixture with the phantom present, PEC on the
   cavity wall `BIRDCAGE_CONDUCTOR_SURFACE_TAG` 401 through
   `TimeHarmonicProblem.pec_facet_tags` (step 1's hook,
   `tests/validation/test_pec_sphere_hole.py:20, :207`) — **check first**
   whether `run_lumped_sheet_port_case` passes `pec_facet_tags` through to
   the problem; if not, one additive keyword (rule (c): disclosed, the
   `PORT-9` gate module re-run green in the same slot). Three sweeps under
   `PORT-19` reuse.
   **Anchors (asserted, every band imported from the `PORT-9` / `PORT-11`
   modules):** reciprocity ≤ 1e-3, σ_max ≤ 1, C4 class spreads at the
   tightened (iii′) 0.5 %, at all three frequencies; plus
   `Re P_in = ½∫_phantom σ|E|²` to ≤ 1e-3 (all loss is in the phantom by
   construction).
   **Negative control (asserted, by record):** the solid route reproduces
   `PORT-11`'s own 4×4 reproduction records at `-n 2` in the same window —
   same module, same fixture, same width.
   **Printed, gated by nothing:** the 4×4 beside the σ = 800 record and
   `max|ΔS|` per class — the number `TH-14` step 3 brackets; and the
   natural-cavity control (tag 401 *not* in `pec_facet_tags`), *predicted*
   to break the power identity as step 1's did.
   **Tier / ranks / cost:** heavy; `PORT-11`'s sweeps on the solid at `-n 2`
   were 67 / 179 / 201 s (10 / 64 / 128 MHz); the hole has 0.69× the cells,
   so three sweeps under reuse are *predicted* 5–8 min; `timeout -k 30 1200`;
   `-s`; durable capture.
   **Traps:** `as_hole` requires `port_gap and emit_port_sheet`
   (`io/mesh.py:1226`) and the 3b default is unflipped — pass what 3a's
   gate passes; the terminals are surface-only on the hole route (3a: the
   sheets still touch them) — the sheet-current facet integral must not
   assume a conductor cell on either side (`PORT-18` measured the normal
   azimuthal); the N1curl DOFs on tag 401 are Dirichlet (step 1's
   `_cavity_dofs` pattern); `-n 2` is the record width (`OPS-41`).
   **Scope:** the birdcage as a PEC hole with its identities; no copper, no
   Larmor-accuracy or `TH-14` claim; **step 2's `Re Z = 0` two-torus
   identity is not this item** — the weekly rules whether the parked
   `attempt/TH-15-step2proper` lands with it or is a record.
   **Status it can move:** `TH-15` step 3 ✅ as a gated step in the row; the
   row 🟡 → ✅ only if the weekly's step-2 ruling has landed, otherwise the
   row stays 🟡 with step 3 recorded ✅.
   **Negative result:** a red gate on the hole with the solid control green
   ⇒ a finding on the PEC-hole route (known-issues), stop; a red control ⇒
   an environment/record drift, `tests/environment` first, stop.

9. **Refresh the twelve examples that cross the 14-day census window on
   2026-09-14 (`th:1`–`8`, `ports:4`–`7`), `EX-30` pattern** (`example-runner`;
   runs only, through `./run_examples.sh`, no example edit; complex; `-n 2`;
   `main`; **taken only when items 1–8 are all done or blocked** — the
   weekly authorised it as a drained-slot leg, not as work; **26 slot-min**:
   ≈ 11 min of windows + 15).
   **Windows:** the `EX-36` leg commands verbatim
   (`20260831T123115Z_EX-36-leg-th-a.log:12`,
   `20260901T170411Z_EX-36-leg-portsans-b.log:12`), census before and after
   as `EX-53` ran it, gated on `exit != 1` (`exit 2` = staleness is
   information; the after-census is *predicted* `stale=0`).
   **Anchors (asserted by the examples themselves, imported, unmoved):**
   each example's own assertions; the census `RESULT:` line.
   **Negative control:** none — a refresh; a red imported assertion is a
   finding, not a fix in slot.
   **Tier / ranks / cost:** measured 08-31 / 09-01: `th` legs 27 + 56 s;
   the `ports`/`ans` legs 141 + 228 + 182 s (superset) ⇒ ≈ 11 min; the
   runner's `-t` is the container-side timeout; foreground, the spawn
   prompt states the rule.
   **Traps:** runner trap (`permission denied … /var/run/docker.sock`) —
   emit with `--dry-run`, run the emitted command through `run_and_log.sh`,
   journal the denial; the allowlist entry is the repo-relative
   `scripts/testing/run_and_log.sh`; `paraview_output/` is gitignored.
   **Scope:** runs only.
   **Status it can move:** the corpus census from `exit 2` back to `exit 0`
   — the state every `EX-*` item's gate reads; no §7 row.
   **Negative result:** a red imported assertion ⇒ known-issues entry naming
   the example and the assertion, stop.

*(The per-review journal — slot recap, completion audits, plan-work notes,
§10 assessment — lives in the review commits and
`docs/planning/plan-archive.md`, not here.)*

If the queue drains: **stop and journal.** There is no fallback chunk:
`PORT-9` step 3's legs are serial by design — (d) is not queued until
(d0) has a margin — and a review scopes each leg from the previous one's
number, not an implementer in-slot. `EX-36`, the former pre-authorised
exception, closed 2026-09-01 (`ae67b4c`) and **nothing replaces it as a
fallback**. History of the birdcage-port hold in
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

**Pace ledger, interval 2026-08-30 10:31 → 09-02 02:42 (2.68 days;
measured 2026-09-02 by the Wednesday weekly review, run interactively
after the scheduled 02:15 slot died on an expired CLI login; sources: 62
commits `dc1af52..1939a63`, 34 attempts.md entries, +90 rows in
test-results.md). The 08-30 weekly's own §10 pass was lost with its
session (only its §7/known-issues/dashboard output was recovered,
`dc1af52`), so this ledger also stands in for it.** **26 items reached
§4-✅** (10 chunk closures — `PORT-12`, `ANS-4`, `EX-37`, `TH-13`, `ANS-5`,
`EX-38`, `EX-39`, `EX-40`, `EX-36`, `OPS-30` — + 16 further gated steps),
i.e. **9.7 items/day ≈ 68/week-equivalent** against the last measured
week's 39; the interval is short and the mix is light (examples and
re-runs), so read the rate as an upper bound, not a trend. Attribution:
**subgoal 4 (B1+/SAR) 11** — `WF-6` steps 1d/2/2b/3/3b/3c/3d/3e (four of
them measured negatives on the SAR side) + `EX-38`/`39`/`40`; element-order
lineage (`TH-13` steps 1′/2/3a/3a‴/4) **5**; ports/benchmarks (`PORT-12`,
`ANS-4`, `ANS-5`) **3** + the `ANS-1` AED half (operator); examples/infra
(`EX-36` ×4 legs, `EX-37`, `OPS-30`) **7**. Physics share 16/26 = 62%.
Slot ledger: 32 implementer slots scheduled, **30 fired**, 2 drained by
design (09-01 15:00/16:30, a queue the daily review honestly left two
short), **2 died on the expired login** (09-01 22:30, 09-02 00:00); of 8
scheduled daily reviews 6 fired normally, 1 died on the CLI-version pin
(09-01 18:00, re-run interactively) and today's 03:00 is pending; the
weekly died on the login. **Governing-half losses again, and again
launcher-side, not limits**: zero reviews died on usage limits this
interval (the 2-of-3 baseline the agent-value clause was written against
is gone), three sessions died on credentials/version — the class no
in-repo mitigation reaches, and the dashboard is the only alarm.

**Agent value, first measurement (weekly-review.md's 09-01 clause).**
(a) Auditor: 6 audits of newly-✅ chunks since 08-31 (`EX-38`, `EX-39`,
`EX-40`, `EX-36`, plus two legs), **0 demotions, 0 disagreements with the
reviewer's own digit trace** — a catch rate of 0 on a sample where the
reviewer also found nothing; not yet informative, keep. (b) Pathologist:
1 ruling (09-01 03:00 review), six claims, **5 CONFIRMED / 1 OVERRULED /
0 UNCOUNTABLE** — the overrule corrected a wrong kill-time reading before
it entered a status; earning its keep. (c) Review completion: 0 of 8
reviews died on limits (baseline 2 of 3) — the mitigation was the 02:00
reset alignment, not the agents, but the agents did not make it worse.
(d) Navigator: 3 sweeps this review (queue refill 09-01 18:00; anchors and
archive candidates 09-02), **0 citation errors** on the ~40 citations the
reviewer re-opened; one NOT FOUND was correct (the "ANS-3/ANS-4 scatter
question" was a review-preamble coinage for `EX-37`'s measured 1e-8–5e-8
run-to-run Z/S scatter, ruled below). (e) Example-runner: 4 delegated
legs, 4 footered, 4 audited PASS, against an implementer baseline of one
orphaned footerless window (09-01 00:00, pre-rule). **Verdict: all six
stay at their tiers**; `implementer.md` lacks a "Last verified against"
footer (flagged); the other footers are dated 08-31.

**Rulings owed to this review (the 10:30 and 18:00 daily reviews' carry
list), each now in §7:** `GEO-25` and `PORT-13` re-scoped with anchors,
stop rules and prices (the lost 08-30 text re-written); `TH-13` step 3b
**not scoped** — the `TH-12` production-order clause is re-affirmed with
`TH-13` in hand and `TH-12` closes ✅, the coil degree-2 reds staying open
in known-issues as the reopening condition; `WF-6`'s finer-*mesh* rung
scoped as **step 3f** (costed cheap: the phantom is hundreds of cells, not
`TH-11`'s millions), its absolute-convergence rung deferred behind 3f, a
`MAG-20` third rung killed (epitaph); `ANS-2` **not commissioned** —
subgoals 2–3 are closed but the B1+ maps are symmetry-gated only, and two
cases already sit in the operator's single AED queue, so the trigger is
"when `ANS-4`'s AED half lands"; the `EX-37` scatter question ruled: the
`ANS-3`/`ANS-4` reproduction *controls* re-register at 1e-6 against the
measured ≤ 5e-8 run-to-run scatter (a record-class change under the (1*)
licence, 20× margin; no physics band moves); the `example-runner` tier
vocabulary ruled (§5.4): host-runner example legs are tiered by their
stated per-window ceiling, and "standard (host-runner, ≤ 500 s window)"
is the label. **F-human disposition (owed since 08-30):** (1) the cost
probe is `GEO-25` as re-scoped, blocking any Phase-6 date; (2) F-human is
a parameter set on `birdcage_port_domain`, not a constructor; (3) the C16
terminal-equality question was settled by `GEO-19` step C (the ratio gate
[0.95, 1.0] is the C_N gate; the 1e-5 equality band was C4-only) and
F-human inherits the ratio gate; (4) sequencing held — subgoal 4 ran on
F-small as directed and was not blocked. **Private-data rule (operator
directive 2026-09-02):** AED numbers never enter a tracked file; the
weekly's numeric adjudications live in gitignored `docs/private/`.

**Phase-5 exit assessment, 2026-09-02 (the arithmetic):** subgoals 1–3
closed; subgoal 4 has its B1+ half **done to the honest bar** (symmetry
identities at all three frequencies, pictures in ParaView, no homogeneity
claim — and the Target box's "matches literature qualitatively" has no
named literature value yet, which is the missing anchor) and its SAR
half **measured, not gated** — four negative steps in three days located
the estimator floor, exonerated the projector, built an honest restricted
estimator, and left a 6–9.5% residual attributed to phantom resolution.
Remaining at the landed grain: step 3e′ (queued) + step 3f (scoped) +
one gate registration ≈ **3–4 items** for SAR, and **one item** to name
the B1+ literature anchor (a review's, not an implementer's). At the
measured 9.7 items/day that is < 1 day of fired slots; at the last
measured *week's* 39/week it is < 1 week. **Exit ≈ 2026-09-05…09 on
F-small** — the front of the 08-23 window (09-08…15), the first time the
estimate has moved earlier, and it moved earlier because the SAR route
turned out to be cheap once the estimator was understood. Two honest
caveats: a step-3f verdict (b)/(c) sends the SAR gate back to a review
with no date; and "Phase 5 exit" here means the *F-small* deliverable —
the human-scale maps are Phase 6's, dated only after `GEO-25` prices
them. The number honest people watch: **if step 3f has not printed by the
2026-09-06 weekly, or printed (b)/(c), the SAR gate is not "one rung
away" and that review re-plans it rather than extends.**

**Pace ledger, interval 2026-09-02 02:51 → 09-06 10:48 (4.33 days; measured
2026-09-06 by the Sunday weekly review, run interactively by the operator's
session after the scheduled 02:15 slot committed its `attempts.md` rotation
(`70a2a79`) and then died on the account session limit; sources: 108 commits
`944be5a..b8c0eae`, +142 rows in test-results.md, the census and examples
sweeps delegated to two general-purpose agents and re-cited by the
reviewer).** **34 items reached §4-✅** (23 chunk closures — `MAT-8`,
`GEO-26`, `PORT-13`, `GEO-25`, `EX-41`…`EX-51` (eleven), `OPS-31`…`OPS-38`
(eight) — + 11 further gated steps: `WF-6` 3f₀/3f′/3h/3i, `GEO-26` step 1,
`PORT-13` steps 1–2, `PORT-15` step 1, `POST-6` step 1b, `TH-15` steps 1 and
2a), i.e. **7.9 items/day ≈ 55/week-equivalent** against the 09-02
interval's 9.7/day upper bound and the last full week's 39. Attribution:
**Phase 5 subgoal 4 (B1+/SAR) 5** — `MAT-8`, `WF-6` ×4 — the SAR gate
registered (3h) and the mirror identity (3i); **Phase 6 mesh + ports 8** —
`GEO-26` (2), `PORT-13` (3), `GEO-25`, `PORT-15`, `POST-6` 1b; **Phase 2
conductor model 2** — `TH-15` steps 1 and 2a; examples 11, ops 8. Physics
share 15/34 = **44 %** (the 09-02 interval read 62 %; this one carried the
retention/entry-point maintenance and the example ramp for five closures).
Negative and partial results, all landed honestly with bands unmoved:
`PORT-14` steps 1/1b/1c/1d (the sheet is single-mode to 3.4e-3, the width
law is the lever, no measured geometry predicts the offset), `POST-6` step 1
(drive-level power identity red — denominator, settled by 1b), `GEO-26`
step 2's pre-registered STOP (retired by step 3), `TH-15` step 1's first
parking (re-scoped anchor, landed), `GEO-25` demoted ✅ → 🧪 by the §3
measurement-only rule and re-closed by step 2. Slot ledger: ≈ 52
implementer slots scheduled, **3 produced nothing for non-physics reasons**
(09-03 09:00 API 529; 09-06 04:30 and 06:00 on the account session limit)
and 2 were protocol anomalies (09-03 16:30 preflight-dirty from a hand-run
housekeeping sweep left staged — one slot; 09-06 09:00 queue drained); of
13 scheduled daily reviews **12 fired**, the 09-06 03:00 died on the
session limit, and **the weekly died on the same limit after its
checkpoint commit** — so, unlike the 09-02 interval, **governing-half
losses are back on limits (2 of 14 governing sessions)**, in the 02:15–06:00
band right after the 02:00 reset, which the operator alone can move
(dashboard, top item). Operator directives landed interactively this
interval: AED privacy as a hard rule (09-02), the conductor model
(`TH-15`/`TH-14`/`ANS-6`, 09-04), the Ansys feature ladder Tiers A/B/C
(09-04), the `ANS-4` AED replication (09-04), the XL tier (09-05), and the
retention policy / housekeeping sweep (09-03).

**Agent value, second measurement (weekly-review.md's 09-01 clause).**
(a) Auditor: 13 audits of newly-✅ chunks, **13 PASS, 0 auditor demotions**;
the interval's two demotions (`EX-43`, census digits in no harness log,
09-03 10:30; `GEO-25`, the §3 measurement-only rule, 09-04 18:00) were made
by the reviewer — the first is inside check 2's remit ("every numeric claim
greps out of a cited log") and the review logs do not say whether the
auditor flagged it or the reviewer found it first, so the catch rate is
**unattributable from the record**; the reviews must start quoting the
auditor's own line when they demote. Keep at its tier. (b) Pathologist: **0
invocations** recorded in fourteen review logs — nothing disputed reached
it; no measurement. (c) Review completion: 12 of 13 dailies fired and the
weekly was cut off — **2 governing sessions died on limits** against the
09-02 interval's 0. The protocol's prescribed first mitigation ("drop the
pathologist to sonnet before other mitigations") does not fit the failure:
the pathologist ran 0 times, and the sessions that died did so *at start*
in the post-reset band, i.e. the limit was consumed by the preceding
implementer slots, not by review-side agents. The mitigation that fits is
the schedule (operator's call, dashboard item 1); the pathologist stays at
opus until a review dies *mid-session* with an agent bill behind it. (d)
Navigator: not invoked by this review (two general-purpose sweep agents
were, with every number re-cited to a hash or file:line by the reviewer —
0 citation errors on the ~40 re-opened). (e) Example-runner: **12 of the 13
example closures this interval** were runner-executed, all 12 audited PASS
(the 13th, `EX-40`, ran implementer-direct); one runner closure was
demoted (`EX-43`, unlogged census — re-closed next slot) and one converted
a failing pre-registered control factor into a print (`EX-49`, upheld by
the review and turned into standing rule (e)). Both were protocol gaps the
implementer would have hit equally; the runner's §4 landing rate is 12/12.
**Verdict: all six stay at their tiers.** `implementer.md` still lacks a
"Last verified against" footer (flagged twice now); every other footer is
dated 08-31, inside the 30-day window.

**Examples health, 2026-09-06 (step 4; delegated sweep, re-cited).** 45
runnable examples, **every one with a footered Status-0 harness run ≤ 6
days old** (oldest: `th:1`–`8` and `ports:4`–`7`, 2026-08-31); one
truncated mesh-leg log (`…050408Z`) is superseded by its remainder
windows. Ramp per phase (`examples ≥ min(5, gating ✅)`): Phase 0 meshing
slice 5/5; Phase 1 5/5; Phase 2 9 vs 5; **Phase 3 2 (+ `ans:1`) vs 3 —
short by one, the only shortfall**, because `MAT-8` and `MAT-4` step 1
never got a distinct-angle example (the daily-review step-5 mechanism
missed on the imposed-field SAR gate) — **`EX-52` opened** (§7); Phase 4
6 (+ `ans:3`/`ans:4`) vs 5; Phase 5 5 vs 0 (`WF-6` 🟡, step-level gates
only); Phase 6 10 vs 5. Agent footers all 08-31 (≤ 30 days);
`implementer.md` has none. Plan hygiene: §7 rotation this review moved
nine closed narratives (1 872 lines) to the archive, `PROJECT_PLAN.md`
9 867 → 7 995 before this pass; the remaining large blocks are all
**open** chunks (`WF-6` 1 527 lines, `OPS-26` 976, `PORT-14` 383, `TH-15`
336) and rotate when they close.

**Phase-5 exit assessment, 2026-09-06 (the arithmetic; the 09-02 watch
condition):** the condition was "step 3f prints by this review, and not
(b)/(c)". **Met on 09-02 itself** — 3f printed clause (a) (all five SAR
identities inside the band at 2.5–3.5 % on the halved-`h` phantom), 3g found
the construction not `h` was binding, and **3h registered the repo's first
coil-driven SAR gate** the same day (twelve quadrant-power C4 pairs ≤ 1.52 %
against the imported, unmoved 5 % band at 10 MHz on F-small; 3i added the
mirror identity at ≤ 1.75 %). Subgoal 4's B1+ half is done to the honest
bar (unchanged); its SAR half is **gated, not merely measured**. What
remains for the F-small exit at the landed grain: **one item** — `MAT-4`
step 2, the C95.3 mass-averaged SAR through the gated averaging operator on
the restricted estimator's field (its one-month stall rule trips 09-07;
the fix is the daily review queueing step 2 at 18:00 today, not an
extension — this review does not extend it) — plus the B1+ anchor below,
which is this review's and is written. At 7.9 items/day that is **< 1 day
of fired slots ⇒ Phase 5 exits on F-small ≈ 2026-09-07…08**, the front of
the 09-02 window (09-05…09), and it slipped two days only because the
06:00/04:30 slots and the 03:00 review were lost to the limit. Honest
scope of "exit": the F-small deliverable set — symmetry-gated B1+ maps at
three frequencies, one coil-driven SAR identity gate at 10 MHz at fixed
`h`, mass-averaged SAR pending — with no absolute, homogeneity, C95.3,
Larmor-SAR or convergence claim; the human-scale maps are Phase 6's. The
number honest people watch: **if `MAT-4` step 2 is not ✅ by the 09-09
weekly, subgoal 4 is not "one item away" and that review re-plans the SAR
route rather than extends.**

**Subgoal 4's B1+ validation target, written 2026-09-06 (the item the
09-02 review assigned this one).** The Target box's "matches literature
qualitatively" named no value, and no in-repo source carries a CV or
profile for a loaded 4-leg low-pass birdcage at this fill factor, so a
literature number is not a target this review can honestly write. The
computable target is: **the 2D birdcage closed form** — N infinitely long
line currents on a circle of radius R carrying the mode-1 pattern `I_n =
I cos φ_n` (Hayes et al. 1985, the birdcage paper; Jin, *Electromagnetic
Analysis and Design in MRI*, the birdcage chapter), whose interior
transverse field is uniform apart from harmonics whose leading order is
set by N, evaluated *numerically* by Biot–Savart superposition rather than
by a transcribed formula — against the **unloaded** F-small `|B₁⁺|` map at
10 MHz along a radial line at r ≤ 0.5 R, band from the CG1 floor `WF-6`
measured (≈ 2 %). That is a closed form the mission can gate on; the
loaded-coil homogeneity stays qualitative (a picture) until `ANS-2` gives
it an external number. Expressed as a §7 chunk for the daily review to
queue: **`WF-6` step 4** — *the unloaded-coil B1+ closed-form gate*, one
solve on `birdcage_port_domain` with the phantom's σ = 0 and εᵣ = 1,
radial profile printed and asserted against the line-current
superposition within the CG1 band, the loaded map's profile printed
beside it never asserted, negative control per rule (e) asserted: the
mode-2 current pattern (`cos 2φ_n`) must miss the mode-1 closed form by
≥ 10× the band. Standard tier (`-n 2`, the 116 085-cell fixture).

**Phase-5 exit assessment, 2026-09-09 (the arithmetic; the 09-06 watch
condition MET, and the blocker has changed halves).** *Interval:* last
weekly-review commit `70a2a79` 2026-09-06 02:28 → this session 2026-09-09
02:15 = **2.99 days** (the Sunday→Wednesday 3-day leg of the 3/4 split; all
rates below divide by 2.99, never by 7).

*The count.* **14 §4-compliant closures** — `MAT-6` step 11; `OPS-39`;
`TH-15` step 3a; `MAT-4` step 4 (⇒ `MAT-4` ✅); `EX-52`; `PORT-16` steps 1
and 2 (⇒ `PORT-16` ✅); `WF-6` step 4a; `EX-53`; `TH-15` step 2d; `OPS-40`;
`OPS-41`; `MAT-4` steps 5 and 5b. Three further landings are
**measurement-only 🧪** and close nothing by §4 (`GEO-27`, `GEO-28`,
`GEO-29`); four are parked negatives or branch records (`WF-6` steps 4, 4b,
4d, 4e; `TH-15` steps 2, 2b, 2c, 2 proper, 2e, 2f, 2g). By phase:
**Phase 5 six** (`MAT-4` ×3, `WF-6` step 4a, `EX-52`, `EX-53`), **Phase 6
four** (`TH-15` ×2, `PORT-16` ×2), **Phase 3 one**, **Phase 0 three**.

*The rate, and why the headline number flatters.* 14 / 2.99 = **4.68
closures/day**, against the 09-06 review's 7.9 — a **41 % fall**. The
denominator that matters is coarser: only **7 chunks reached ✅**
(2.34/day), and only **two of them are physics** (`MAT-4`, `PORT-16`) —
the other five are three `OPS` infrastructure chunks and two examples.
Half the interval's closures are sub-steps of two items that did **not**
close. Two measured causes, both nameable: (i) the 09-08 18:00 daily review
died on usage credits (146-byte launcher log,
`logs/automation/20260908T230001Z_daily-review.log`), §9 was never
re-topped, and the 21:00 / 22:30 / 00:00 slots all stopped-and-journaled —
**the last 24 h produced 3 closures, the interval's worst day**; (ii) the
two active physics fronts are both in multi-attempt spirals against
sub-percent modelling artifacts — `WF-6` step 4 is **six attempts in five
days, zero gates**, `TH-15` step 2 is **seven sub-steps in three days,
still open**.

*Phase-5 exit.* The 09-06 watch condition was "if `MAT-4` step 2 is not ✅
by the 09-09 weekly, re-plan the SAR route". It is **met, three days
early** — the content landed 2026-09-06 as step 4 (renumbered, not skipped)
and step 5b extended it to a 1 g gate on 09-08. **Subgoal 4's SAR half is
done; its B₁⁺ half is now the single blocker**, and the aggregate 4.68/day
**may not be applied to it**: the remaining work is one item whose own
measured closure rate is **0 gates in 6 attempts over 5 days**. What is
measured about it: the 09-08 10:30 ruling finished the comparand (odd-order
cube sum `S_11`, bar ≈ 0.5 % at the centre / ≈ 1.1 % worst interior — a
quarter of the band) and put the residual miss on the FEM at ≈ 3.2 % centre
and ≈ 5.3 / 7.9 % at `r = 0.4R / 0.5R` against a ≈ 2 % CG1 band; `GEO-29`
then priced the only remaining lever — the global-`h` ladder costs **2.43×
cells for a nominal 8× refinement** (116 085 → 281 728, mesh 21.6 → 45.6 s)
and the interior mean circumradius falls 2.19e-02 → 1.07e-02 m, dropping
below `GEO-28`'s 1.4e-02 m shell thickness only at the finest rung. So
`WF-6` **step 4f** is a two-rung solve on a fully priced mesh ladder:
ordinary heavy tier, 1–2 implementer slots, no XL, no new physics.

*Scoping decision, dated and falsifiable (the realism rule, applied to
ourselves).* **If `WF-6` step 4f has not either landed the B₁⁺ gate or
printed a monotone fall of the eleven-point miss across ≥ 2 refinement
rungs by the 2026-09-13 weekly review, subgoal 4's B₁⁺ target is re-scoped
from a band gate to a measured convergence statement** — "the eleven-point
miss falls from X % to Y % as the interior cell size halves, with the
comparand bar at ≤ 1.1 %" — and Phase 5 exits on that. This is a cut, not
an extension: a gate the project cannot reach in ten days on a fixture it
has fully priced and whose comparand is now bounded at a quarter of the
band is a gate written at the wrong altitude, and the honest deliverable is
the convergence measurement. No date for the F-small exit is written here
beyond that condition, because the only item left has no measured closure
rate to extrapolate from.

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
   **Assessment 2026-09-02 (covering the lost 08-30 pass):** **11 items
   in 2.7 days** — the subgoal went from "no chunk" to the most active
   front. B1+: `WF-6` steps 1/1b/1c/1d/2/2b ✅ — `|B₁⁺|` C4-covariant at
   the CG1 floor (~2%) at 10/64/128 MHz, quadrature drive by exact
   superposition, the co/counter-rotating mirror identity, first ungated
   CV (2.8–3.0%) and purity figures, three examples. SAR: steps 3/3b/3c/
   3d/3e — the point-`E` estimator misses the same identities by 25–40%,
   the global CG1 projection is a fit of the sheet edges (1876% phantom
   residual), the phantom-restricted projection is honest (18.7%, power
   to −3.5%) and packaged as `post.project_to_cg1_restricted`, and the
   identities still miss at 6–9.5%. **The subgoal's two named targets
   re-read:** the `MAT-4` C95.3 SAR claim now has a concrete route (step
   3f → gate registration → `MAT-4` step 2 on the restricted estimator);
   the B1+ "published birdcage homogeneity behaviour" target still names
   **no literature value** — writing that anchor (a specific paper's CV or
   profile for a loaded 4-leg low-pass birdcage at this fill factor) is
   the subgoal's one non-implementer item and is assigned to the
   2026-09-06 weekly. `MAT-4`'s one-month stall rule: it last moved
   08-07 and would trip on 09-07; the fix is step 3f landing the gate its
   step 2 needs, not an extension — if 3f prints (a), the daily review
   queues `MAT-4` step 2 the same day.

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

**Assessment 2026-09-06 — the phase has started, on the feature ladder,
and the cost premise it was dated against is dead.** *Epitaph for the r³
cost model (directive item 1 above):* `GEO-25` measured the F-human rung at
fixed absolute sizing as **504 642 cells at 0.15 m** with a fitted cell
exponent of **0.84 in radius, not 3** — the pinned 1.6 mm conductor
refinement dominates the count and grows with conductor length, not domain
volume; scaling the sizing with the radius is refuted separately (conductor
mass recovery 0.893 < the 0.95 gate, asserted two-sided by step 2). The
"3–4 M cells" and the "62 GiB wall" in `TH-16`'s row were arithmetic on
that model and are re-dated (§7 `TH-16`): a first F-human 64 MHz degree-1
solve is bracketed at ≈ 11–33 GiB by the two priced degree-1 points
(`TH-11` 0.99 M cells / 64 GiB; `PORT-13` 270 k / 5.7 GiB), inside the
128 GiB box either way, and is *priced* by `WF-7` step 0 before anything
is dated on it — a tier is a measurement. What landed this interval on
Phase 6 proper: the mesh prerequisites are **all ✅** (`GEO-19`/`20`/`26`/
`25`), **`PORT-13` ✅** — the 32×32 on the 32-ring-port longitudinal rung
under the three gates, 9–10 s/solve at `-n 8` — **`PORT-15` step 1 ✅**
(the ladder-network closed form and the S/Z termination reduction at
machine precision, the circuit layer's algebra; convention pinned:
per-ring-segment `L`/`C`), `POST-6` step 1b ✅ (the power-wave identity
closes at 1.7e-15; the drive-level band retired and re-registered, `PORT-16`
opened for the 1 %-of-supplied gap), and `PORT-14` steps 1–1d 🟡 — complex
sheet impedances exist and solve, the termination-reduction identity misses
1e-3 at 1.6e-3 / 3.4e-3 for the lossless elements, resolution is not the
axis, the sheet-width law is the lever, and no measured geometry predicts
the −1.09 % width offset (reading (2), a field effect of the sheet: edge
fringing). **Ruling on `PORT-14` (owed to this review):** `REDUCTION_BAND`
= 1e-3 is *not* re-registered at 5e-3 — that would be fitting the band to
the artifact; instead the fixture's measured single-mode floor is
registered as a (1\*) **record** on F-small (`REDUCTION_FLOOR_F_SMALL`,
3.4e-3 at the nominal `A/h` width, reproduced to the digit across four
runs), the gate asserts the residual at that record (reproduction rtol
1e-3) and prints against 1e-3, the deliberate red retires, and the offset is
carried as a **named systematic** of the lumped sheet exactly as `PORT-1`
carries its two — step 2 (64 MHz, the nominal width, on the record mesh)
proceeds on that footing and `TH-17` may not gate a mode frequency tighter
than the systematic without saying so. The daily review scopes step 1e as
that re-registration (tests only). Conductor lineage: `TH-15` steps 0/1/2a
landed in three days (the PEC hole gates on the dipole coefficient β to
1.97 % vs 4.89 %, the two-torus hole is a `MeshGenerator` route 13.7 %
cheaper with every identity to 1e-7); step 2 (the lossless `Re Z = 0`
identity on the hollow two-torus) and 3a (the birdcage as a hole) are
queued; `TH-14` step 1 cannot use β as its anchor (annotated 09-06 10:30)
and waits on this review's next pass for a loss-partition anchor. **Pace on
the phase, measured:** 8 Phase-6 items in 4.33 days ≈ 1.8/day. **First
physics target `TH-17` (eigenmodes, B3)** is serial on `TH-15` step 3a +
`PORT-14` step 2 ≈ 4–5 items ⇒ **scopeable by the 09-09 weekly, first
mode-frequency number ≈ 2026-09-12…14** if slots fire; still **no
completion date** — a tuned S11 against an HFSS + Circuit case needs
`ANS-6`'s copper coil first, and `TH-14` has no anchor yet. **XL slot
(step 3b): spent** — the first slot goes to `ANS-4` step 2, the 128 MHz
h-ladder + degree-2 discriminator, as §5.1 reserved it; the pre-registered
readout, cost and decision rule are in the §7 `ANS-4` row and §9 item 5.

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

**Operator directive 2026-09-04 (binding on this phase's scoping) — the
conductor model.** Every gated coil is solved inside at σ = 800 S/m, the
ceiling the skin-depth-≥-wire-radius mesh rule allows (§7 `TH-15` entry);
copper is δ ≈ 21 µm at 10 MHz and cannot be a volume. Tuning, matching and
per-unit-accepted-power B₁⁺/SAR are loss-partition quantities, so no
parity claim in this phase stands on the 800 S/m coil. Added as a
prerequisite subgoal, before any tuning claim: (e) **realistic conductors
by both routes** — `TH-15` (interior PEC, the lossless limit) then `TH-14`
(Leontovich surface impedance, copper), each gated on a closed form and on
the F-small birdcage's identities, and checked externally by **`ANS-6`**
(the `ANS-4` fixture with a copper coil, AED Finite-Conductivity and PEC
columns). Item (d)'s HFSS + Circuit benchmark at 16 legs is then
commissioned on the copper coil, not on 800 S/m. No date: the first step is
a mesh-probe whose outcome (hole meshing inside or outside the `GEO-23`
family) sets the pace; the review dates it after `TH-15` step 0 reports.
**Same directive, the feature ladder (§9 item 5):** Tier A — `POST-6`
(multi-port superposition), `PORT-14` (RLC sheets), `PORT-15` (the circuit
layer) — is queued *ahead* of the conductor lineage because it is linear
algebra on gated solves and, with `PORT-13`'s 32×32, it is the tuning
workflow itself; `TH-17` (eigenmodes, B3) is Phase 6's first physics target
and is serial on `TH-15` + `PORT-14`. The Phase 6 breakdown's items
(a)–(d) stand; (e) conductors and the ladder are added, not substituted.
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
- *2026-09-02 — a `MAG-20` third h-rung, killed.* `MAG-20` closed with a
  fitted rate inside its band on two-and-a-half rungs; a third rung would
  sharpen a Phase-1 number that gates nothing on the mission's path this
  quarter. Revive only if a Phase-5/6 magnetostatic control needs it.
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
**Ramp check 2026-09-02 (weekly review; the 08-30 check was lost with
its session): 34 runnable examples (+7 since 08-23), every phase at or
above its ramp, no shortfall; census `dead=0 guide=0 stale=0 exit=0` at
09-01 17:12Z — the first clean corpus-wide census since the 08-28
rename.** Per phase, gating ✅ / quota / examples: Phase 1 **6 / 5 / 5**;
Phase 2 **6 / 5 / 8** (`TH-13`, `TH-12` closed; +3 headroom); Phase 3
**2 / 2 / 2** (no headroom for the third check running — `MAT-6` step 11
and any `MAT-4` gate owe an example the day they land); Phase 4 **5 / 5 /
5** (`PORT-9`/`10`/`11`/`12` + `PORT-1`; `ports:1`–`5`, exactly met, no
headroom); Phase 5 **0 / 0 / 3** (`ports:6`–`8` are the ungated-but-
identity-checked B1+ pictures, counted as headroom against the first
`WF-6` ✅); mesh group 9. Every example has a footered green run inside
the interval except `mesh:6`/`mesh:7` (newest run is the orphaned
footerless 09-01 window; last footer 08-25) — **`EX-41`** opened.
**Benchmarks:** `ANS-1` gained AED numbers and is **adjudicated AGREE**
(§7; numbers private); `ANS-3`/`ANS-4` still wait on the operator's AED
queue, low-order pair only; `OPS-32` ports the private-mode writer to
both before either gains numbers; **no new case commissioned** (`ANS-2`'s
trigger stated above).

**Plan-hygiene note, 2026-09-02.** `PROJECT_PLAN.md` is ~8 000 lines;
the closed narratives still in §7 that exceed the ~50-line guide are
`OPS-26` (~976 lines), `OPS-18` (~520), `ANS-5` (~246), `MAG-18` (~102),
`ANS-4` (~79), `EX-37` (~70) — measured by the navigator this review. The
attempts.md rotation landed (`f9462f0`); the §7 rotation is **deferred to
the 2026-09-06 weekly** rather than done in the minutes before the 03:00
daily review, because a result block written without reading the block
it replaces is the kind of summary the archive contract forbids.

**Ratification, 2026-08-16.** The `PORT-9`/`PORT-10` scoping, `ANS-3`
commissioning, plan prune, and attempts archival annotated "*weekly
planning review 2026-08-16*" were executed by the operator's interactive
session (the scheduled 01:30 slot died on the usage limit; `d21d228`
landed the tail). This review audited and ratifies them as weekly-scope
work — the annotations stand.

**Assessment 2026-09-09 — Phase 6 has a measured pace for the first time,
and no denominator to spend it against.** Four §4 closures landed on Phase 6
this interval (`TH-15` step 3a, `TH-15` step 2d, `PORT-16` steps 1 and 2)
over 2.99 days = **1.34/day** — the first non-zero measured Phase-6 rate in
this section's history, which since 2026-08-09 has written "no completion
date" because *no pace existed*. That reason is now spent, and it is
replaced by a different and more honest one: **nobody has enumerated how
many gated steps stand between here and "a tuned birdcage at 64 MHz", so
there is nothing for 1.34/day to divide into.** A rate without a denominator
dates nothing, and inventing the denominator is exactly the unmeasured
estimate this section deletes on sight. **The subgoal this review adds is
the enumeration itself** — see below.

*The interval's real finding, and it is not a good one.* Both active physics
fronts are in multi-attempt spirals against sub-percent modelling artifacts:
`WF-6` step 4 is **six attempts over five days with zero gates**, and
`TH-15` step 2 is **seven sub-steps over three days and still open** (2f
attributed the 2 % `Z` asymmetry to the point-sampled `_path_voltage`, 2g
measured the calibrated gap average as reading B; the `src/` replacement is
specified but unwritten). Each sub-step is individually §4-compliant and
each counts in the pace number, which is why the headline 4.68/day flatters:
half the interval's closures belong to two items that did not close. This is
not a discipline failure — every one of those sub-steps measured something
real and several were negative results correctly banked — but it is a
scoping signal. A front that needs seven sub-steps to characterise one
artifact is a front whose *chunk* was scoped at the wrong grain, and the
remedy is to name the closing step before the next sub-step runs, not to
keep subdividing. Applied concretely: `TH-15` step 2's next landing must be
the `src/` `_path_voltage` replacement written from reading B, not an
eighth measurement.

**Phase 6 subgoal added 2026-09-09 — *the step count to a tuned birdcage***.
Target: a written, ordered enumeration of every gated step between the
current state and "the F-small birdcage is tuned to 64 MHz and the tuned
`S₁₁` matches an AED HFSS + Circuit case", each step with its validation
target named (closed form, identity, or AED comparison) and its serial
dependencies. This is a *planning* deliverable, not a solve, and it is
weekly-owned — the next weekly review writes it, from the feature ladder
(§9 item 5), the `PORT-14` → `PORT-15` → `TH-17` chain, and the conductor
lineage `TH-15` → `TH-14` → `ANS-6`. Until it exists, **Phase 6 still has no
completion date, and the reason is now recorded as a missing enumeration
rather than a missing pace.** *Oldest unstarted owed item on this phase:*
`PORT-14` step 1e — the 2026-09-06 ruling's `REDUCTION_FLOOR_F_SMALL`
re-registration, tests only, which has not been queued in three days and
blocks `PORT-14` step 2, which blocks `TH-17`.

---

**XL slot, 2026-09-09 (protocol step 3b) — SPENT, and the item is split.**
`docs/testing/xl-ledger.md` carries **zero rows**: the tier was created by
operator directive 2026-09-05 and no slot has ever been spent, so this
review may commission one. The reserved first slot is `ANS-4` step 2 (§9
item 6). **Ruling: `ANS-4` step 2 is split, and only half of it is XL work.**

*The arithmetic, from priced smaller rungs, all our own numbers.* Step 2 as
written is four degree-1 `conductor_resolution` rungs plus one degree-2
solve, in one 2 h window. Priced separately:

* **The degree-1 ladder is not XL work at all.** The ×1 rung is 116 085
  cells and solves eight single drives in 71 s
  (`20260908T004020Z_WF-6.log:1998`), so four drives ≈ 36 s; `PORT-14`
  step 1b measured ×0.75 and ×0.6 at 161 695 and 209 604 cells and ×0.45
  projects to ≈ 330 k. Scaling the ×1 solve superlinearly to the ×0.45 rung
  gives ≈ 230 s for four drives plus ≈ 60 s of meshing, and memory at
  `TH-12`'s degree-1 point (6.66 GiB on 138 619 cells) with its own
  `p = 1.271` floor exponent gives ≈ 21 GiB at 330 k — **well inside the
  ordinary service's wall**. All four rungs fit **two ordinary heavy
  windows** at `-n 4`, `timeout -k 30 560`. They are headless,
  implementer-runnable work and should not wait on an operator session.
* **The degree-2 solve is genuinely XL, on memory before time.** `TH-12`
  step 2 measured degree 2 on 138 619 cells at 882 296 DOFs, 235.4 + 266.4 s
  for *two* solves, and **61.94 GiB summed peak RSS = 96.8 % of the ordinary
  service's `memory.max`**, with the review's own instruction to treat
  `p = 1.271` as a **floor**. `ANS-4`'s ×1 mesh is 0.837× those cells ⇒
  ≈ 739 k DOFs and ≳ 49 GiB by that floor — and step 2 needs **four** drives,
  not two, so ≈ 1 000 s of solve plus mesh and assembly, **≈ 1 100–1 300 s**.
  That is over the 660 s host foreground window *and* at ~77 % of the
  ordinary memory wall computed from an exponent known to under-predict by
  29 %. Exactly the case the tier exists for.

*The split.* **`ANS-4` step 2a** — the four degree-1 rungs at 128 MHz on the
ordinary service, two heavy windows, headless, the daily review's to queue.
**`ANS-4` step 2b** — the single degree-2 solve on the ×1 mesh, `xl`,
`-n 16` against `fem-em-solver-xl`, `timeout -k 60 7200`, **this week's XL
slot**. The pre-registered readout and the decision rule are unchanged from
the 2026-09-06 adjudication and are **not** restated or loosened here: the
three C4 class entries `S₁₁`/`S₂₁`/`S₃₁` at 128 MHz on every rung with their
relative move from the ×1 record; the C4 spread and `σ_max` on every rung
asserted at the imported, unmoved `PORT-11` bands; a Richardson h → 0
estimate from the three finest degree-1 rungs printed; the private half (the
estimate against the AED column, and the ruling) in `docs/private/` only.

*Trap that 2b must pre-register, or it will read as a failure.* `TH-12`
step 2 found the complex-power identity **fails at degree 2** (4.59e-09 vs
the 1e-9 band; `W_e` 2.03e-13 → 7.16e-06 J), and step 3 read the mechanism
**`COIL-SPECIFIC`** (cross-order `W_e/W_m` moves 3.4e+07× on the coil against
1.015–1.155× on the sphere and the smoke fixture). The birdcage **is** a
coil, so 2b will reproduce that red. It is expected, it is common-mode, it
cancels in the S entries exactly as it cancelled in `TH-12`'s ΔZ, and **the
band is not to be loosened** — 2b declares it a pre-registered red with the
`TH-12` known-issues entry cited, and takes the S entries as the readout.

*Cost, ledger and hold.* `run_and_log.sh` appends the ledger row at window
start; the implementer brings `fem-em-solver-xl` up and stops it after. The
service has in fact been **Up since 2026-09-07 and unused by any slot** —
28 h of idle container at review time. **The `xl` item's headless hold
stands**: 2b's ≈ 1 100–1 300 s window cannot fit a 660 s foreground slot, so
2b is an **operator-interactive run** and goes to the top of the dashboard's
Waiting-on-you list. 2a has no such constraint and carries the diagnosis
regardless.

*Honest caveat on the split.* Splitting means the h-ladder's Richardson
estimate — the thing that actually decides the 2026-09-06 decision rule —
lands **before** the degree-2 control. If 2a alone closes ≥ 50 % of the
private gap, the Larmor verdict is decidable without 2b, and 2b becomes a
bound on our own order sensitivity rather than a discriminator. That is
still worth the slot (no one has measured our order sensitivity on a
coil-fed birdcage at a Larmor frequency, and `TH-12` measured order moving a
different quantity by 2.43 pp on a comparable fixture), but the **2026-09-13
weekly may re-commission the slot** if 2a's result changes the question.
Never split the slot further, never carry it over.

---

**Benchmarks, 2026-09-09 (protocol step 5, both directions).**

*Adjudicate — nothing new to rule on.* No case gained AED numbers this
interval: the newest file under any `aed_results/` is dated 2026-09-04
(`ANS-4`), and `ANS-3`'s case directory still has **no** `aed_results/` and
no `COMPARISON_private.md` at all, so it remains waiting on the operator's
AED queue. `ANS-4`'s ruling (AGREE at 10 MHz, INCONCLUSIVE at 64/128 MHz)
stands unchanged and its diagnosis chunk is commissioned above.

*The `ANS-1` re-check owed to this review — **done, and the verdict holds
tighter**.* §6's `MAT-6` row instructed this review to re-check the `ANS-1`
AGREE verdict against the column `MAT-6` step 11 moved. Step 11 landed
2026-09-06 (`0efe994`) and our ΔR deviation moved from 1.5834 % to
**0.2747 %** on the promoted 418 888-cell slab-refined fixture. The
2026-09-06 adjudication had already written the arithmetic this landing
would produce; **the landed digit matches it**, so no re-adjudication is
triggered and **AGREE stands, tighter than before**. One reading changed and
is worth recording publicly because it is about *our* result, not AED's: the
refinement moved our ΔR toward the closed form by 1.31 pp, so the two codes
no longer *bracket* Dodd–Deeds — they now sit on the same side and closer
together than before. Numbers private
(`docs/private/ans1-adjudication-2026-09-01.md` and the 09-06 file's
"`ANS-1` re-check" section); nothing numeric moves into a tracked file.

*Commission — **`ANS-2` opened**, and its trigger was pre-written.* §10 has
reserved `ANS-2` for "the B1+/SAR case" since 2026-08-16, with the trigger
"subgoal 4". That trigger fired: `MAT-4` step 4 (2026-09-06) put the C95.3
mass-averaging operator on the **coil-driven** field with the 10 g C4
quadrant identity inside the unmoved 5 % band, and step 5b (2026-09-08)
gated the 1 g column on `GEO-27`'s rung — a phase milestone on **gated**
physics since `ANS-4`, which is §5.4's bar for a new case. **SPEC.md
written this review:**
`examples/ansys_benchmarks/birdcage_coil_driven_sar_10MHz/SPEC.md`.

Three scoping judgements are recorded in that spec and are this review's,
not the operator's:

1. *The case is cheap because it reuses `ANS-4`.* Geometry, materials,
   ports and boundary condition are byte-for-byte `ANS-4`'s — same HFSS
   project, one frequency, plus a phantom mass density and a
   field-calculator export. One AED session replicates it, which is §5.4's
   size bar.
2. *The primary adjudication rows are the **shape-free** ones* — pointwise
   SAR at four named points and the whole-phantom dissipated power —
   **not** the mass-averaged rows. Our operator averages over a **sphere**
   of equal mass; IEC 62704-1 (and therefore HFSS) averages over a **cube**.
   Those are different operators and will differ by a few percent in a
   curved field. The spec says so in advance, requires AED to report which
   averaging shape it used, and forbids reading a rows-4–6 miss as a finding
   until rows 1–3 have agreed. Pre-registering that is the difference
   between a systematic and a false disagreement.
3. *Normalisation is carried explicitly rather than matched.* Our drive is
   `V_src` = 1 V behind 50 Ω ⇒ 5.0e-03 W incident; HFSS's default is 1 W.
   SAR is linear in incident power, so the spec asks the operator to run at
   whatever HFSS uses and **report the number**, and we rescale. A silent
   normalisation mismatch is the one error mode that would pass every
   self-check on both sides.

*Why this case matters more than its cost suggests.* Every coil-driven SAR
number this repository has is a **symmetry identity** — four quadrant values
agreeing to ≤ 0.14 %. A SAR computation wrong by a constant factor passes
that identity exactly. The only absolute SAR check on record is against the
lossy-sphere closed form on an **imposed uniform field**, never on a coil,
which is why §2 still says the absolute/compliance claim is open. `ANS-2` is
the first thing that can close it. The runnable half is a §7 chunk for the
daily review to scope and queue; the case goes to Waiting-on-you when that
box is checked, **not before** — sending the operator a spec whose runnable
half does not exist would waste an AED session.

---

**Ramp check 2026-09-09 (weekly review): 47 runnable examples, every phase
at or above its ramp, no shortfall — and the rule that measures it has been
tightened because it was measuring zero.** Per phase, gating ✅ (at the
tightened chunk-or-gated-step granularity, §5.4) / ramp / examples:
Phase 1 **6 / 5 / 5** (complete, flat five binds, **exactly met with zero
margin** — retiring or breaking any one magnetostatics example drops a
*completed* phase below its bar, which is the only fragile row in the
table); Phase 2 **5 / 5 / 9** (+4); Phase 3 **3 / 3 / 4** (+1);
Phase 4 **4 / 4 / 5** (+1); Phase 5 **5 / 5 / 6** (+1 — `WF-6` steps 1, 2,
2b, 3h, 3i are the five gated steps; under the *old* chunk-only formula this
row read `min(5, 0) = 0`, a bar that cannot bind, which is why §5.4 was
tightened this review); Phase 6 **6 / 5 / 8** (+3, against the gating-chunk
list added to §6's Phase-6 row this review — it was the one row with no
`X-1…X-n` range, so the ramp was not mechanically checkable on it at all).
Mesh group 5, ramp-exempt (§5.4, 2026-08-09). Guides present for **47/47**,
all required sections, `dead=0 guide=0`.

*Two health findings, neither a shortfall.* (1) **The corpus census has not
been re-run since 2026-09-07** and still reads
`dead=0 guide=0 stale=81 exit=2` at `f700f5e`
(`20260907T140926Z_EX-53-census-post.log:120`) — the 81 stale artifacts
belong to **40 of the 47 examples**, i.e. `stale` is now the *normal* state
of the corpus rather than an exception, with the oldest at ~178 h
(`ports:4`/`ports:5`). By `OPS-19` staleness is `exit 2` = information, not
failure, so nothing is red; but a signal that fires on 85 % of the corpus is
not carrying information any more, and the question for the daily review is
whether the checker's 48 h threshold is the right one for a repo whose
examples run weekly — **not** whether to refresh 40 artifacts by hand.
(2) `examples/ansys_benchmarks/two_torus_gap_ports_10MHz/03_two_torus_gap_ports_10MHz.py:398`
emits `SyntaxWarning: invalid escape sequence '\*'` at *collection*, which
has been polluting ~25 unrelated harness logs since 09-05 and makes a
path-grep over-report `ans:3` runs by five days. Cosmetic, one-character
fix, worth a rider on the next `ans:`-touching chunk.

*Agent files (weekly-review.md's ~30-day footer check).* Six of the seven
`.claude/agents/*.md` carry a "Last verified against" footer dated
**2026-08-31** — 9 days, all fresh. The seventh, **`implementer.md`, carries
no footer at all**, and it is the most-invoked agent of the seven: there is
no record of when its instructions were last checked against a real chunk
execution. Flagged, not fixed here.

---

**Plan-hygiene note, 2026-09-09.** The rotation ran first this session and
committed on its own (`12cb7b6`), per the commit-first checkpoint. `attempts.md`
18 218 → **15 056** lines (31 entries older than 14 days moved verbatim;
zero-loss check passed on 32 796 non-blank lines) — still far over `OPS-36`'s
6 000-line budget, and the residue is **inside** the 14-day window, so the
rotation cannot reach it: the budget and the retention rule disagree, and
that is a rule question for the operator, not something a rotation can fix.
`PROJECT_PLAN.md` 10 311 → **8 976** lines (`OPS-26` 976, `OPS-27` 126,
`MAG-18` 101, `EX-38` 58, `EX-39` 77, `EX-40` 77 archived verbatim, each
replaced by a ≤ 15-line result block; zero-loss check passed on 36 438
non-blank lines; every § reference in CLAUDE.md and docs/automation/*.md
re-verified). **Still over the 4 000-line guide and structurally unable to
reach it:** the two largest §7 narratives are `WF-6` (2 249 lines) and
`TH-15` (1 193) and both belong to **open** chunks, which the archive
contract does not permit compressing. Together with `MAT-4` (304, closed
2026-09-06 but with live carry-forwards and three sub-steps landed in the
last four days) they are 3 746 lines — 42 % of the file. The honest reading
is that the 4 000-line guide cannot be met while two 🟡 chunks each carry a
thousand lines of live narrative, and the next weekly should either compress
`MAT-4` (now cold enough) or say plainly that the guide is unreachable until
`WF-6` and `TH-15` close.

---

**Flagged for the 2026-09-09 03:00 daily review — not weekly-owned, stated
here so it is not lost.**

1. **`PORT-16` is a stable-ID collision and `PORT-17` is free.** §7 carries
   **two** `PORT-16` rows: the accounting-gap chunk, **✅ 2026-09-07 with
   two audited steps and logs**, and the feature-ladder C2 "Wave ports /
   coax feeds" entry, unopened and phase-gated. Stable IDs are a §7 contract
   and this breaks it. The closed chunk with logs owns the ID; the ladder
   entry should be renumbered (`PORT-17` is unused repo-wide). The §9
   ladder table (item 5) needs the same edit — both are the daily review's.
2. **The working tree was dirty at review start and was left exactly as
   found.** `tests/mesh/test_birdcage_leg_offset.py` and
   `tests/validation/test_port_birdcage_leg_offset_sweep.py` are modified
   and `tests/validation/test_ans4_resolution_ladder.py` is untracked, all
   written 2026-09-09 01:58–01:59 by an interactive session — additive
   `conductor_resolution` / `degree` keywords on the existing rung helpers
   plus a 390-line `ANS-4` step-2 ladder module carrying its own
   pre-registered readout and a `FEM_EM_ANS4_STEP2_RUNGS` trimming knob that
   makes the 2a/2b split above **mechanical**. This review is
   documentation-only and did not commit, run or verify any of it. It is the
   03:00 review's to dispose of, and it is urgent: a dirty tree stops the
   next implementer slot and is parked on `recovered/*` by the one after,
   so leaving it costs two more slots on top of the three already lost.
3. **§9 has been drained since the 09-08 10:30 review** (three consecutive
   stop-and-journal slots) because the 18:00 daily review died on usage
   credits. The 02:15 weekly cannot re-top §9 by protocol. **The 03:00
   review is the only session that can restore throughput**, and the
   ready-to-queue items this review produced are: `ANS-4` **step 2a** (two
   ordinary heavy windows, priced above, independent of everything else),
   `WF-6` **step 4f** (the `h`-ladder, mesh-priced by `GEO-29`, and the item
   the Phase-5 exit condition is written against), `PORT-14` **step 1e**
   (tests only, the phase's oldest owed item), the `ANS-2` runnable half,
   and finding 1's renumbering.

---

**Pace ledger, interval 2026-09-09 02:35 → 09-13 02:15 (3.99 days; measured
2026-09-13 by the scheduled Sunday weekly review; sources: 128 commits
`713516e..0589bbe`, 54 attempts.md entries (lines 15057–17975 before this
session's rotation), +149 rows in test-results.md, the census and examples
sweeps delegated to two general-purpose agents and every number re-cited by
the reviewer).** **12 items reached §4-✅** — six chunk closures, `OPS-42`,
`OPS-43` (auditor DEMOTE on tier honesty, corrected smoke → standard),
`OPS-44`, `OPS-45`, `OPS-46` (closure claim made 21:09 on 09-12, **audit
pending** at the 03:00 review — anchor (iii) is operator-pending by design),
`PORT-19` — and six gated steps outside them: `ANS-2` step 1, `TH-11` step 5d
(operator-run, `xl`), `WF-6` step 4g, `PORT-14` step 1e, `TH-19` steps 1–2,
`TH-15` step 3b. **12 / 3.99 = 3.01 closures/day**, against the 09-09
interval's 4.68 (−36 %) and the 09-06 interval's 7.9 (−62 %). The coarser
denominator is worse: **six chunks reached ✅ (1.50/day) and none of them is
physics** — five are `OPS` infrastructure and the sixth, `PORT-19`, is a solver
speed-up (factor reuse, an 11.2× wall-clock win, gated on bit-identity). The
operator's own interactive measurement on 09-12 (`247290d`: 79 chunk-step
commits in seven days, two closures in four, steps-per-closure ≈ 15:1) is
what this interval reads like from the inside. Attribution by phase:
**Phase 0 five chunks**; **Phase 2 two steps** (`TH-11` 5d, `TH-19` 1–2);
**Phase 5 two steps** (`ANS-2` 1, `WF-6` 4g); **Phase 6 one chunk + two
steps** (`PORT-19`; `PORT-14` 1e, `TH-15` 3b); Phases 1, 3, 4 zero. Physics
share by item 7/12 = 58 %; by chunk **0/6**. Measured-only 🧪 and negative
landings, all banked honestly with bands unmoved: `WF-6` 4f/4h/4i/4j/4k,
`PORT-14` 2/2b/2c/2d/2e, `ANS-4` 2a/2b/2d/2a′/2a″/2a‴/2e/2f/2g, `TH-15` 2h,
`GEO-30`/`31`/`32`, `PORT-18`, `OPS-43` (d)'s blocked window — **26 sub-steps
on five fronts, three of which the 09-12 18:00 review froze under the
operator's four-attempt cap**. Eleven stable IDs opened (`GEO-30`–`32`,
`OPS-42`–`46`, `PORT-18`, `PORT-19`, `TH-19`) against six closed; known-issues
6 opened / 4 retired (9 open headers, was 7). **Slot ledger — the first
interval since 09-02 with zero governing-half losses:** 48 implementer slots
scheduled, **48 fired**, 43 did chunk work, **4 stopped on a drained §9**
(09-10 09:00, 09-11 00:00, 09-12 22:30, 09-13 00:00), 1 anomaly (09-10 12:00,
the operator's in-flight XL window left the tree dirty); **12 of 12 daily
reviews fired**, this weekly fired on schedule, no session died on limits or
credentials. The drain has a new cause worth naming: the 09-12 18:00 review
queued five items of which four were one serial chain, the enacted take-next
rule let the 19:30 slot run four items and the 21:00 slot three, and the
queue that was sized for four slots lasted two — **under take-next, five
items is one slot's worth when they are cheap**, and the daily review's
restock floor needs to count expected slot-minutes, not items (flagged
below). The verdict on pace, brutally: **throughput is now bounded by
diagnosis, not by slots.** Every slot fired and every review ran, and the
interval still closed zero physics chunks because the three active physics
fronts each spent 4–9 sub-steps characterising a sub-percent artifact
(`WF-6` ×0.0095's 2 % power residual, `PORT-14`'s 1 % width offset, `ANS-4`'s
degree-1 non-asymptoticity) — all three real, all three now banked, none of
them a gate. The four-attempt cap enacted 09-12 is the right mechanism and
this review applies it: each frozen family below gets exactly one numbered
step with a status it can move, or a closure.

**Agent value, third measurement (weekly-review.md's 09-01 clause).** (a)
Auditor: 5 chunk audits (`OPS-42`/`43`/`44`/`45`, `PORT-19`), 5 PASS on
evidence, **one DEMOTE on tier honesty** (`OPS-43` declared smoke, measured
53–61 s under `-k 30 180` → re-declared standard, `710c743`) — the first
auditor-originated demotion on record; the catch is small but it is the
class §4 item 4 exists for. Keep. (b) Pathologist: **0 invocations** in 12
review logs, second interval running; nothing disputed reached it. Keep at
opus (no review died mid-session with an agent bill behind it). (c) Review
completion: **13 of 13** governing sessions fired (12 dailies + this weekly)
against 2-of-3-died at the clause's baseline — the 02:00-reset alignment and
the operator's credit top-up, not the agents, but the agents did not make it
worse. (d) Navigator: used once by the 09-12 18:00 review (the `POST-6`
staleness flag, which this review confirms below was a correct flag); its
corpus still excludes `docs/planning/chunks/` until the operator's
`.claude/agents` edit lands (dashboard item 1), so this review Read the chunk
files directly and re-cited every number itself — 0 citation errors on ~60
re-opened. (e) Example-runner: 0 example closures this interval (no gate
closed, so daily-review step 5 opened nothing; `PORT-19` step 6 ran two
examples implementer-direct as a regression record). (f) Mesh-probe: 2
invocations (`TH-15` 2h, `WF-6` 4k), both no-solve, both deterministic across
a repeat build, both honest negatives. **Verdict: all six stay at their
tiers.** Footers: six dated 2026-08-31 (13 days, inside the 30-day window);
`implementer.md` still carries none — flagged for the fourth consecutive
review, and it is an operator edit (`Edit(.claude/**)` is on the ask list),
dashboard item 7.

**Phase-5 exit decision, 2026-09-13 (the 09-09 scoping rule, applied).** The
09-09 rule was: *if `WF-6` step 4f has not either landed the B₁⁺ gate or
printed a monotone fall of the eleven-point miss across ≥ 2 refinement rungs
by this review, subgoal 4's B₁⁺ target is re-scoped from a band gate to a
measured convergence statement, and Phase 5 exits on that.* **Neither arm is
met as written, and the rule fires.** No closed-form B₁⁺ gate exists (4g's
own commit: "closes nothing … no closed-form B₁⁺ gate"). What was measured is
a monotone fall of the **C4 four-copy spread** — 5.2506 % → 2.0719 % over
`resolution` 0.015 → 0.012 m on `main` with asserted anchors (4g,
`20260909T200431Z_WF-6.log:1982–1994`), 1.9514 % at 0.0095 on the parked
branch (4f) and then a stall — not of the eleven-point closed-form miss,
because the 09-09 03:00 review had already refuted that comparand's route
(no cube order satisfies the identity; `CLOSED_FORM_BAND` 5e-2 unmoved and
unused). The 4f/4g/4h–4k sequence then spent four more slots on a rung that
was already off the ladder, and the 09-12 18:00 review froze the family. So
the cut pre-registered on 09-09 is taken now, not extended: **subgoal 4's
B₁⁺ target becomes the convergence statement** — "on the unloaded F-small
birdcage at 10 MHz the worst-radius C4 four-copy spread of `|B₁⁺|` falls
5.2506 % → 2.0719 % (ratio 0.3946) as the global resolution goes 0.015 →
0.012 m, the C4 covariance 3.6159 % → 1.6815 % alongside it, the power
residual inside the unmoved 1 % band on both rungs; the closed-form
comparand (odd-order cube sum `S₁₁`, bar ≤ 1.1 %) misses the ×1 rung by
≈ 3.2 % at the centre and ≈ 5.3 / 7.9 % at 0.4R / 0.5R, a record; the third
rung's 2 % common-mode power residual is a banked, unexplained negative" —
and **`WF-6` step 5, scoped below, registers it**. *Epitaph, 2026-09-13 —
the closed-form B₁⁺ band gate on F-small, killed.* Six attempts (4, 4b–4e)
found the comparand needed an image sum whose order the identity does not
fix, and the `h`-ladder found the FEM side stalls at ≈ 2 % on a rung whose
power accounting then breaks — a 2 % CG1 floor cannot host a 5 % band with
a 1.1 % comparand bar and a 3–8 % miss, and ten days on a fully priced
fixture is the honest evidence that the gate was written at the wrong
altitude. Revive only on a degree-2 or curved-geometry rung that moves the
CG1 floor. **Date:** Phase 5 exits on F-small **when `WF-6` step 5 lands** —
one tests-only item priced by 4g at 204 s at `-n 4`, queueable by the 03:00
review, so **≈ 2026-09-14…15 if its first window is green**; the aggregate
3.01/day is not applied because this item's own family rate is one green
landing (4g) in eleven attempts. Honest scope of "exit": symmetry-gated
B₁⁺ maps at three frequencies, a two-rung convergence statement, 1 g / 10 g
mass-averaged SAR C4-gated at 10 MHz at fixed `h`, pictures in ParaView —
no absolute, homogeneity, C95.3, Larmor-SAR or closed-form B₁⁺ claim; the
human-scale maps are Phase 6's.

**The three frozen families, each given its numbered step (owed by the
09-12 18:00 review; the daily review queues them, in this order).**

* **`WF-6` step 5 — register the convergence statement and close the
  F-small deliverable.** Tests only, `tests/validation/test_birdcage_b1_plus_closed_form.py`,
  default `LADDER` (×1, ×0.012), `-n 4`, heavy by measurement (204 s).
  Asserted: (i) the ×1 four-copy spread reproduces 5.2506 % and the ×0.012
  spread 2.0719 % at rtol 1e-3 (records backed by 4f and 4g on the same
  fixture, same statistic); (ii) the fall is monotone —
  `spread(×0.012) < spread(×1)` and `covariance(×0.012) < covariance(×1)`,
  the identity form; (iii) the existing anchors (cell counts at
  `CELL_COUNT_BAND`, covariance ≤ the imported 5 %, power residual ≤ the
  imported 1e-2, cw separation ≥ 5×) unchanged. Printed, never asserted
  (rule (e)): the interior CV of `|B₁⁺|` on both rungs beside the filament
  closed form's own CV from step 4a, and the ×1 eleven-point miss against
  `S₁₁` (the record above). ×0.0095 stays out. **Status it can move:**
  `WF-6` 🟡 → **✅** on the re-scoped target (§2's B₁⁺ clause moves to the
  convergence wording in the same commit); a red on (i) or (ii) is an
  `OPS-18`-class drift, known-issues, stop. Not a 4l: nothing here diagnoses
  ×0.0095.
* **`PORT-14` step 3 — the κ-derived width route, registered at 64 MHz,
  out-of-sample at 128 MHz.** One additive `src/` change — an opt-in on the
  lumped-sheet law that scales the told width by `(1 + κ)` with **κ computed
  in-run** from the ε = 0 solve's `C/terminal − 1` (`PORT-16`'s
  `_exact_shares`, the Cauchy–Schwarz deficit 2d showed *is* κ to 0.3 %),
  never a fitted number — plus tests in the step-2 module. Asserted: (i)
  the derived κ(64) reproduces 2d's 1.0641e-2 at rtol 1e-3 (record, same
  fixture); (ii) with the derived width both lossless residuals at 64 MHz on
  the 116 085-cell gate mesh ≤ `REDUCTION_BAND` 1e-3 (backed by 2e's
  1.190127e-04 / 9.581734e-07 with a fitted width within 3e-4 of the derived
  one, same comparison, same fixture); (iii) the registered 10 MHz floor
  `REDUCTION_FLOOR_F_SMALL` still reproduces on the *uncorrected* route
  (unmoved). Negative control (asserted by record): the uncorrected width at
  64 MHz misses 1e-3 (step 2's 1.354202e-02). Printed, *predicted* under
  1e-3, never asserted: the corrected 10 MHz residuals and the **128 MHz**
  pair with its own in-run κ(128) — the out-of-sample reading a review
  decides on. Heavy by ceiling (2e: 191 s at `-n 2`; 128 MHz adds one
  solve). **Status it can move:** `PORT-14` 🟡 → **✅** on (i)–(iii) green,
  with the κ correction carried as the sheet's **named systematic** (the
  09-06 ruling) and `TH-17` barred from gating a mode frequency tighter than
  it; `PORT-15` gate (i) unblocks. A red on (ii) with the derived width is a
  finding that the fitted and derived κ differ by more than the residual
  slope allows — known-issues, stop, no fit.
* **`ANS-4` step 3 — the 64 MHz order-matched rung, `xl`.** Degree 2 at
  h = 0.005 (592 744 cells, 3.79 M unknowns) at **64 MHz**, `-n 16` against
  `fem-em-solver-xl`, `timeout -k 60 7200`, durable capture, service
  restarted first. **Priced by measurement**, not extrapolation: step 2d ran
  this exact mesh and order at 128 MHz in 7225 s for four drives at a
  **290.2 GiB** peak — before `PORT-19`'s factor reuse; with one
  factorisation and three back-substitutions the window is *predicted*
  2 000–3 000 s and the memory the same. Public readout: the three C4
  classes at 64 MHz at degree 2 against the degree-1 record, every imported
  `PORT-11` gate on the rung. Private readout (`docs/private/`): the miss
  against the AED First Order column. Decision rule, pre-registered: a miss
  in the same class as the 128 MHz order-matched residual ⇒ the 64 MHz
  AGREE below stands on evidence and its "by mechanism" qualifier is
  dropped; a materially larger miss ⇒ a frequency-dependent feed-model
  systematic re-opens as a known-issues entry and a `PORT` systematics
  chunk. **Cannot run before Thursday 2026-09-17 02:00** — see the XL
  ledger ruling below — so it is the 09-16 review's to queue into
  `xl-queue.env`, and this review pre-registers it so that review only has
  to copy it.

**`ANS-4` Larmor verdict, banked 2026-09-13 (protocol step 5, adjudicate;
numeric ruling in gitignored `docs/private/ans4-adjudication-2026-09-13.md`,
nothing numeric about AED enters this file).** **AGREE at 128 MHz** on the
order-matched comparison: step 2d's finest degree-2 rung — by `ANS-5`, our
degree 2 *is* HFSS First Order, and AED's First Order run converged at a
comparable unknown count — sits at a residual in the same class as AED's own
two orders' mutual agreement, and the degree-2 sequence converges
(successive change 1.19 → 0.62 % on `S₁₁`, ratio 1.90; 1.21 → 0.62 on
`S₂₁`; 0.75 → 0.50 on `S₃₁`), so the residual is a disagreement between two
converged codes, not our truncation, and it is small. The 09-06 decision
rule ("closes ≥ 50 % of the private gap ⇒ discretisation") is met on every
class. **AGREE at 64 MHz by mechanism, one caveat carried:** step 2d ran at
128 MHz only; at 64 MHz the degree-1 miss was smaller with the same
signature, and the mechanism 2d established — our degree-1 gate fixture is
unconverged while AED's run is converged — is what produces a miss that
grows with frequency at fixed `h`. `ANS-4` step 3 above is the rung that
turns "by mechanism" into evidence. **The 09-06 reasoning error, recorded so
it is not re-derived:** that ruling excluded element order because AED's
own Zero→First Order shift was small; the inference is invalid when only
one side is converged — AED was order-insensitive *because* it had
converged, ours moved 6.09 / 5.38 / 6.70 % under the same change because it
had not, and the asymmetry was the signal. **What the frozen degree-1
families add:** no degree-1 ladder on this fixture is in a proven
asymptotic range on either knob (2a‴, 2f, 2g), so a degree-1 extrapolant is
not an h → 0 reference; the rung that decided was the order-matched one.
**What this does and does not license:** the 64 / 128 MHz 4×4 gains
"externally checked, AGREE" in §2.2 / §6 with the qualifier; the 2026-09-06
known-issues entry retires; **no absolute-accuracy figure is quoted**, no
resonance, tuning, SAR, B₁⁺ or human-scale claim. **The public consequence
that matters most:** at degree 1 the gate fixture's own 128 MHz S entries sit
5–7 % from their order-matched value (our own order move) while every
self-consistency gate in the repo passes on them unchanged — identities do
not see this class of error, and §2.2 now says so. The production element
order is therefore live again: `TH-19` below.

**`TH-19` outcome (a) — ruled; step 3 re-scoped.** Steps 1–2 showed the
matched source projection takes the degree-2 coil identity from 2.39e-09
(red, reproduced first) to 2.04e-14 / 5.94e-15 on both σ-halves against the
unmoved 1e-9, with `W_e` falling 3.8e7× — outcome (a), the injector was the
whole of the `TH-12` objection on a projected volume drive. **The
production-order default is not changed by this review**, because the
birdcage's lumped-sheet drive bypasses the projection (`ports/lumped.py:480–483`)
and the objection has never been tested on it. **Step 3, re-scoped:** the
degree-2 identity on the sheet-driven 4-leg F-small birdcage — `PORT-16`'s
exact discrete power identity `P_src,exact = P_vol + P_sheet,exact` at the
imported `DISCRETE_IDENTITY_RTOL` 1e-6 and the reactive identity
`Im P_src = 2ω(W_m − W_e)` at the `TH-12` family band, at 10 and 128 MHz,
degree 2 on the 116 085-cell mesh, `W_e/W_m` printed beside degree 1's;
negative control (asserted): degree 1 reproduces `PORT-16` step 1's four
readings. Priced by 2b: degree 2 on this mesh solves four drives in 178 s at
`-n 16` (≈ 16.6 GiB observed) ⇒ two single drives at `-n 8` ≈ 3–4 min,
ordinary service, heavy. **Status it can move:** none directly; (a) on the
birdcage sends the production-order decision to the 2026-09-16 weekly with
both fixtures identity-clean, (b)/(c) opens the gauged degree-2 formulation
chunk `TH-12` step 3 named. The `TH-13`-era degree-2 known-issues entry
stays open until that decision.

**`POST-6` — audited against `PORT-16`'s logs; re-scoped, not closed.** The
09-12 18:00 review's staleness flag was correct. What is met: step 1's four
anchors — (i) the package quadrature reproduces `WF-6` step 2's C4 / mirror
records (0.9818 % / 0.8087 %, path equality 1.2e-15), (ii) linearity at
1e-12, (iv) the single-drive residuals, and (iii) **as re-pointed by
`PORT-16` step 2** at the exact discrete identity on the superposed field
(5.877e-15 / 1.435e-14 vs 1e-6, `20260907T110826Z_PORT-16.log:1942–1946`,
23 passed, 104 s) with the terminal residual printed beside the untouched
band. The 09-06 weekly's "step 2" (the common-mode re-registration) is
**void — superseded by `PORT-16` step 2 before it ran** (epitaph: the exact
identity is the stronger statement and the same test module carries it).
What is *not* met is the chunk's own written done-when: its original step 2
— the 16-fold quadrature drive through `superpose_drives` on `PORT-13`'s
32-ring-port fixture with the **C16 invariance of `|B₁⁺|`** as the gate —
has never run, and the "re-point `WF-6` step 3 and `WF-7`" clause has not
happened. Ruling: the done-when is re-scoped to **step 3 (renumbered from
the original step 2)** — the 32-port ccw quadrature drive on `PORT-13`'s
fixture at 10 MHz through `superpose_drives` under factor reuse, gated on
C16 invariance of the CG1 `|B₁⁺|` map at the imported `WF-6` 5 % band, the
mirror identity, and `PORT-16`'s exact power identity on the superposed
field; negative control the cw / mis-paired weights (asserted by the same
comparison's 4-leg record) — heavy (`PORT-13` measured 9–10 s/solve at
`-n 8`, 32 drives ≈ 6 min with reuse, plus the projection); and the
re-pointing clause is **dropped** — `WF-6` step 3h's gate stands on its own
sums and a gated test is not refactored for tidiness; `ports:13` (`EX-49`)
and `PORT-16` step 2 already consume the entry point. `POST-6` closes ✅
when step 3 lands. The auditor's reading of the same logs is recorded in
this review's commit.

**`TH-11` step 5d's §2 sentence — ruled: the bracket is a record, and the
"extrapolation" wording moves.** The 64 MHz three-rung ladder on the XL
service (2 808 204 cells, 4838 s at `-n 8`, 17 passed / 1 skipped,
`20260909T153910Z_TH-11-step5d.log`) reads +10.2698 % → +2.8063 % →
+0.3824 % and brackets h → 0 at **[−2.0415 %, −0.4256 %]**, overlapping the
10 MHz [−2.15, −0.91] and 30 MHz [−3.37, −0.38] brackets. So the coil-loading
ΔR against Dodd–Deeds is **measured flat in f across 10–64 MHz to the
bracket width (≈ 1.6 pp)** — the 08-23 epitaph's physics half is confirmed
on the box that could afford it. It is **not gated** and this review does
not gate it: the comparand is the quasi-static kernel (a comparison, not a
reference, at 64 MHz), the two-rung `p_eff` 2.876 disagrees with the
three-rung 1.623 so only the bracket is honest, and a 4838 s XL window is
not a CI assertion. §2.2's bullet head changes from "is an extrapolation" to
"is measured, not gated, at 64 MHz on one XL window", and CLAUDE.md's
sentence with it; §2.1 gains nothing.

**Phase 6 subgoal — *the step count to a tuned birdcage*, written (owed
since 09-09).** Target restated: the F-small 4-leg birdcage tuned to 64 MHz
in the circuit layer, the tuned `S₁₁` reproduced in-model, and the tuned
`S₁₁` matched to an AED HFSS + Circuit case. Every step below is a
*numbered* step with its validation target; the serial chain is marked.

1. **`PORT-14` step 3** (above) — registered 64 MHz lumped-RLC route,
   κ-derived. Target: reduction identity ≤ 1e-3 on C and L. Serial on
   nothing. *Moves `PORT-14` → ✅.*
2. **`PORT-15` step 2** — gate (i) from the circuit side: terminate the
   stored 64 MHz 4×4 `S` (10 MHz control) in the capacitor / inductor
   values of step 1's fixture through `reduce_terminated_ports` and assert
   equality with `PORT-14` step 3's in-model sheet solve at the registered
   residual (band imported from step 3, never re-derived); plus the
   inductance read-off — `Im Z` of the 10 MHz 4×4 gives the per-window
   `L_r`, `L_l` of `PORT-15` step 1's ladder model, printed. Target: identity
   with the FEM at the registered band. Serial on 1. *Moves nothing; opens
   3.*
3. **`PORT-15` step 3** — the tuning sweep: capacitor value swept on the
   stored 64 MHz 4×4 to put the mode-1 resonance of the reduced network at
   64 MHz; then **one** in-model solve with `PORT-14`'s capacitor sheets at
   the tuned `C` at 64 MHz, asserting the circuit-predicted tuned `S₁₁` and
   the reduced 2×2 against the in-model values at the step-3 registered
   band. Target: the HFSS + Circuit self-consistency identity (circuit
   prediction = field solve at the tuned value), plus the ladder-network
   closed form's resonance with the step-2 inductances printed beside it.
   Serial on 2. *Moves `PORT-15` → ✅ (its gates (i) and the tuned `S₁₁`);
   the mode-frequency gate (ii) is `TH-17`'s.*
4. **`TH-15` step 3** — the birdcage as a PEC hole: `PORT-9`/`PORT-11`'s
   three gates at 10 / 64 / 128 MHz on `birdcage_port_domain(as_hole=True)`
   plus `Re P_in = ½∫_phantom σ|E|²` ≤ 1e-3. Target: the identities and the
   lossless power identity. Serial on nothing (mesh route ✅ step 3a,
   `gap_cell_tags` ✅ 3b). *Moves `TH-15` → ✅ with step 2's `Re Z = 0`
   two-torus identity, which the parked `attempt/TH-15-step2proper` carries
   and which lands with this step or is ruled a record.*
5. **`TH-17` step 1** — eigenmodes of the loaded F-small birdcage with the
   PEC coil (4) and the tuned capacitor sheets (3): the `TH-9` eigensolver,
   mode-1 frequency asserted at 64 MHz within `PORT-14`'s named systematic
   (the κ correction, ≈ 1 %) and the mode spectrum against the
   ladder-network closed form with the step-2 inductances. Target: closed
   form + circuit-layer consistency. Serial on 3 and 4. *Moves `TH-17` → ✅
   and ticks Phase 6's first physics target.* **This is the internal
   "tuned birdcage" milestone.**
6. **`TH-19` step 3** (above) — the degree-2 identity on the sheet drive;
   then the production-order decision at a weekly. Target: two power
   identities. Serial on nothing; **gates whether steps 3 and 5 are quoted
   at degree 1 or degree 2** — the `ANS-4` verdict says degree-1 absolute
   entries are 5–7 % off at 128 MHz, so a tuned `S₁₁` quoted at degree 1
   carries that.
7. **`TH-14` step 1** — the Leontovich surface-impedance boundary, gated on
   **the closed-form Q of a lossy-wall cavity**: the `TH-9` PEC box with its
   walls given `Z_s = (1 + j)/(σδ)`, the TE₁₀₁ complex eigenfrequency's
   `Q = Re ω / (2 Im ω)` against Pozar's perturbation closed form
   `Q_c = (kad)³ b η / (2π² R_s) · 1/(2a³b + 2bd³ + a³d + ad³)` at an `R_s`
   where the perturbation is valid (Q ≳ 100), within 5 %; negative control
   PEC walls give no damping. This is the loss-partition anchor `TH-14` has
   lacked since 09-06 (β cannot be its anchor) — a copper-scale surface
   loss with an exact reference. Serial on 4's mesh (the hole's facet tags).
8. **`TH-14` step 2** — the copper F-small birdcage 4×4 at 10 / 64 / 128 MHz
   beside the PEC (4) and σ = 800 columns; target: the identities, and the
   loss partition `P_coil / P_phantom` printed. Serial on 7. *Moves `TH-14`
   → ✅.*
9. **`ANS-6`** — the copper AED case (Finite Conductivity + PEC columns),
   SPEC written by a weekly when 8 lands; adjudicated by the next weekly
   after the operator returns numbers. Serial on 8 **and on the operator's
   AED queue**.
10. **`ANS-7` (to be opened)** — the HFSS + Circuit tuned case: the `ANS-6`
    fixture with the four capacitors at our tuned `C`, AED's tuned `S₁₁(f)`
    and resonance beside ours. Target: **the subgoal's terminal AED
    comparison.** Serial on 5, 6, 9 and the AED queue.

*The arithmetic, honest.* Steps 1–5 are the internal chain — five numbered
steps, four of them serial. Phase 6's measured closure rate this interval
is **3 gated items / 3.99 days = 0.75/day** (09-09: 1.34/day), but those
were sub-steps; the rate that applies to *numbered* steps is the frozen
families' own: `PORT-14` step 2 took five sub-steps over two days to reach
a positive-but-unregistered reading, `TH-15` step 2 eight sub-steps over
four days and is still open, `ANS-4` step 2 nine sub-steps over four days.
**≈ 2–3 days per numbered step, serial** ⇒ steps 1–5 ≈ 10–15 days of fired
slots ⇒ **the internal tuned-birdcage milestone (`TH-17` mode 1 at 64 MHz)
≈ 2026-09-25 … 10-01**, inside a quarter, no cut forced. Steps 6–8 run in
parallel on the same slots and add no calendar time if the queue carries
two fronts. **Steps 9–10 have no date this review can write:** the
operator's AED queue has returned nothing since 2026-09-04 and has two
cases in it (`ANS-2` ready since 09-09, `ANS-3` since 08-16), so the
terminal AED comparison is bounded by the human half, not by slots — the
same governing-half conclusion every pace ledger since 08-09 has reached,
now on the operator's side of the table. **Phase 6 still has no completion
date, and the reason is now recorded as the AED queue, not a missing
enumeration.** Watch condition for the 09-16 weekly: if `PORT-14` step 3
has not landed a registered 64 MHz route by then, the chain's first step
took longer than its family's own history and the 2–3-day figure is wrong
— re-plan, do not extend.

**XL and XXL slots, 2026-09-13 (protocol step 3b).** **XL: not spent —
the budget is exhausted.** `docs/testing/xl-ledger.md` carries three rows
with non-zero elapsed inside the trailing 7 days (09-09 `ANS-4` step 2b
249 s; 09-09 `TH-11` step 5d 4838 s; 09-10 `ANS-4` step 2d 7225 s — the
killed and the 0-second rows are uncharged by §5.1), which is the whole
three-per-week budget; the oldest ages out at 2026-09-16 ≈ 14:37Z, so the
first window that can run is **Thursday 2026-09-17 02:00**, and the guard
would deny anything queued before it. `xl-queue.env` stays empty. The
candidate is pre-registered above (`ANS-4` step 3) so the Wednesday review
commissions it by copying. Two findings for §5.1, both already enacted by
the operator on 09-09/10 and confirmed here: the first slot went to a
249 s / ~16.6 GiB run (2b) because its price was extrapolated, and §5.1's
"no `xl` without a measured memory price" rule now exists; and 2d ran 25 s
past the 2 h ceiling with the deadline lifted by hand — with `PORT-19`'s
reuse landed since, the same case is predicted to fit, and step 3 is
written with that margin. **XXL (Saturday 2026-09-19 02:00): not spent** —
no candidate has a measured memory price at the human scale, and §5.1
forbids marking one without it. The prerequisite is a cost probe, scoped
here as **`WF-7` step 0**: the F-human rung (`GEO-25`, 504 642 cells, the
32-ring-port longitudinal layout) at 64 MHz, degree 1, one single-drive
lumped-sheet solve through `run_lumped_sheet_port_case`, printing cells,
unknowns, factorisation time and `ru_maxrss` on every rank, `-n 8`, heavy,
durable capture — *predicted* 11–33 GiB and 3–8 min from the two priced
degree-1 points (`TH-11` 0.99 M cells / 64 GiB, `PORT-13` 270 k / 5.7 GiB),
🧪 by the §3 rule, closes nothing, gated by nothing but the cell record.
Its reading prices the F-human 32×32 under reuse (ordinary service if the
single solve is under ~30 GiB) and the F-human **degree-2** rung — ≈ 3.2 M
unknowns, bracketed at ≈ 250–300 GiB by 2d's 3.79 M-unknown measurement —
which is the genuine xxl candidate (the human-scale order sensitivity: at
F-small, degree 1 is 5–7 % off at 128 MHz, and nobody has measured it at
0.15 m). The 09-16 review commissions the 09-19 window from `WF-7` step 0's
number or writes "not spent" again.

**Examples health, 2026-09-13 (step 4; delegated sweep, re-cited).**
**48 runnable examples** (the runner enumerates 48, not 47 — `ans:2` landed
09-09 after the last count), **every one with a footered Status-0 harness
run, every one with its same-stem guide**, and the corpus census at
`20260913T004551Z_PORT-19-step6-census.log:39` reads
`dead=0 guide=0 stale=0 exit=0` under the 14-day window `OPS-42` set
(`check_example_doc_references.py:100`). Ramp per phase (gating ✅ at the
chunk-or-gated-step granularity / ramp / examples): Phase 1 **6 / 5 / 5**
(complete, flat five, still zero margin); Phase 2 **≥ 5 / 5 / 9**
(`th:1`–`9`); Phase 3 **3 / 3 / 4** (`mat:1`, `mat:2`, `mri:2`, `ans:1`);
Phase 4 **4 / 4 / 5** (`ports:1`–`5`); Phase 5 **5 / 5 / 6** (`ports:6`–`9`,
`mri:3`, `ans:2`); Phase 6 **6 / 5 / 9** (`mesh:8`–`12`, `ports:10`–`13`);
mesh group ramp-exempt. **No shortfall; no chunk opened.** Two health
readings, neither a defect: (1) **39 of the 48 have no run in the last
seven days** — the oldest cohort (`th:1`–`8`, `ports:4`–`7`, twelve
examples) last ran 2026-08-31 and **crosses the 14-day census window on
2026-09-14**, when `stale` starts firing as `exit 2`; by `OPS-19` that is
information, not failure, and the daily review's step-5 machinery may
refresh them as an `EX-30`-pattern leg when a slot is otherwise drained —
this review does not open a chunk for artifacts that are green and merely
old. (2) `examples/mri/01_coil_phantom_fields.md:246` names its combined
XDMF under `examples/mri/paraview_output/` while the file lives in the
repo-root `paraview_output/`; the checker resolves it through its second
candidate directory so the census is clean — a one-line guide correction,
rider on the next `mri:`-touching chunk. Agent footers: six at 2026-08-31,
`implementer.md` none (above). The three untracked AED replication scripts
under `*/aed/` are correctly outside the runner's discovery.

**Benchmarks, 2026-09-13 (protocol step 5, both directions).** *Adjudicate:*
`ANS-4`'s Larmor verdict is banked above — the only adjudication this
interval, and it came from **our** rung (step 2d), not from new AED numbers:
no case gained AED data (newest file under any `aed_results/` is still
2026-09-04; `ANS-2` and `ANS-3` have no `aed_results/` at all). `ANS-1`
AGREE stands (re-checked 09-09, nothing moved since). *Commission:* **no new
case.** The gated-physics milestones since `ANS-2` was commissioned (09-09)
are `PORT-19` (a solver speed-up, gated on bit-identity — not physics) and
the two `MAT-4` steps `ANS-2` already covers; `ANS-6` waits on `TH-14`
(step 8 above) by the operator's own directive, and a copper spec written
before the conductor model gates would be a benchmark on ungated physics.
`ANS-2` stays at the top of the dashboard's Waiting-on-you list — **ready
since 09-09, four days without an AED session; `ANS-3` behind it since
08-16**. The AED queue is now the longest pole on every absolute claim in
§2 (the coil-driven SAR absolute, the copper coil, the tuned `S₁₁`), and
this review says so on the dashboard rather than opening a third case into
the same queue.

**Plan hygiene, 2026-09-13.** The rotation ran first and committed on its
own (`bf1ea49`): `attempts.md` 17 981 → **12 243** lines (51 entries older
than 14 days, 5 738 lines, moved verbatim; zero-loss check on 35 207
non-blank lines) — still over `OPS-36`'s 6 000-line budget with the residue
inside the retention window, the rule question for the operator unchanged;
`PROJECT_PLAN.md` 9 699 → **9 207** lines (`MAT-4` 303, `ANS-4` 76,
`ANS-3` 62, `MAT-6` 70 archived verbatim, each replaced by a ≤ 6-line
result block; zero-loss on 38 195 non-blank lines; every § reference in
CLAUDE.md and docs/automation/*.md re-verified). **The 4 000-line guide is
unreachable and this review says so plainly:** `OPS-46` moved the 73 heavy
table *rows* (806 962 B, under its 850 000 B bound) but the `>`-blockquote
narratives it declared out of scope are the line count — `WF-6` 2 295,
`TH-15` 1 243, `PORT-14` 736, `POST-6` 157 lines, **4 431 lines = 48 % of
the file**, all under **open** chunks the archive contract forbids
compressing. What the contract does *not* forbid is moving them byte for
byte to `docs/planning/chunks/<ID>.md` the way `OPS-46` moved the rows —
that is neither a summary nor a compression. **`OPS-47` opened** (§7 OPS
table): extend the `chunks` subcommand to a chunk's blockquote narrative,
same byte-identity refusal, same leak check, the plan line count as the
anchor. Until it lands the guide stays unmet by construction.

**Flagged for the 2026-09-13 03:00 daily review — not weekly-owned, stated
here so it is not lost.**

1. **`OPS-46`'s closure claim is unaudited.** It flipped ✅ at 21:09 on
   09-12 with "the review audits"; no review has run since. Anchor (iii)
   is operator-pending by design and does not block the audit.
2. **Five numbered steps are ready to queue**, each with the status it can
   move: `WF-6` step 5 (tests only, 204 s at `-n 4` — the Phase-5 exit item),
   `PORT-14` step 3 (the chain's first step, ≈ 4 min at `-n 2`), `TH-19`
   step 3 (heavy, `-n 8`), `POST-6` step 3 (heavy, `-n 8`), `WF-7` step 0
   (cost probe, heavy, `-n 8`, 🧪). `ANS-4` step 3 is the 09-16 review's
   (`xl`, budget). All five are mutually independent — the first genuinely
   independent five-item queue in a week.
3. **The restock floor should count slot-minutes under take-next.** Four
   slots drained this interval with every review alive, three of them after
   a five-item queue of cheap serial `OPS-46` moves was consumed by two
   slots. daily-review.md step 6's "queue more than five when items are
   short" needs a number: ≥ 4 slots × 60 min of *predicted* work, not five
   items.
4. **`TH-15`'s row state line is stale** ("step 1 of 3 landed") against its
   history (3a ✅ 09-06, 2d ✅ 09-07, 3b ✅ 09-09, 2h 🧪 09-09; step 2's
   unitarity gate and step 3 open). The `OPS-46` state line was written from
   the row's last *ruling*, which predates those; a one-sentence refresh.
5. **The 2026-09-14 census will start reporting `stale` on twelve examples**
   (above) — `exit 2`, information; do not spend a slot on it unless the
   queue is otherwise drained.
6. **The `-n 2` MUMPS drift's third draw is not queued** (dashboard item 6's
   last clause): no gate depends on it since `OPS-43` (d) and `PORT-19`
   step 5 re-anchored at `-n 1`, and a third sample of a 2-in-34 event
   diagnoses nothing; it stays an observation until a gate needs a `-n 2`
   bit-identity again.

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
