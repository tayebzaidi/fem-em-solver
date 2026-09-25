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
  *Corrected 2026-09-20 (`PORT-20`, from the `ANS-3` adjudication):* **S on
  the current route is `z_to_s(Z)` since `PORT-20`** — on the gap-voltage /
  impressed-current route the undriven ports are *open*, so `b_i/a_j` was
  never a column of S there; that branch now converts its open-circuit `Z`
  (agreeing with `ports/circuit.py`'s independent implementation at
  9.4e-17 relative, and with the closed form `(Z−z0)(Z+z0)⁻¹` exactly on
  synthetic 2-/3-ports). Only this bullet's two S records moved —
  σ_max 0.864809457 → **0.861356894**, `‖S−Sᵀ‖/‖S‖` 4.758625e-05 →
  **3.112129e-05** — with every band unmoved and every `Z`-derived record
  (the mutual ratio above included) digit-identical. The **lumped-sheet**
  routes of the two bullets below are untouched and re-ran byte-identical.
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
  128 MHz only; `ANS-4` step 3, `xl`, is the 64 MHz evidence — **its window
  ran 2026-09-16 02:00**: 16 passed, 1658 s, `memory.peak` 280.8 GiB, every
  imported gate green on the 592 744-cell degree-2 rung, and the degree
  1 → 2 move at 64 MHz on the driven column is 6.51 / 2.60 / 4.11 % by C4
  class (`20260916T070008Z_ANS-4-step3.log:2427, 4596`); the private miss
  against AED and the pre-registered decision rule are the 09-19 weekly's,
  so this sentence does not move until then). The 09-06
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
  Beside it, **the lumped RLC sheet and the circuit layer are gated on the
  same fixture** (`PORT-14` ✅ 2026-09-13: the termination-reduction
  identity holds under 1e-3 at 10 MHz on the registered floor and at 64 MHz
  on the κ-derived width `w/(1 + κ)`, κ = 1.06 % the sheet's named
  systematic — 5.359129e-05 / 1.998404e-06 for C / L,
  `20260914T003252Z_PORT-14-step3-64mhz.log:1937–1959`; `PORT-15` ✅
  2026-09-14: `C_tuned` = 15.570 pF from the stored 4×4 zeroes `Im Z_in`
  to 2.1e-15 and one in-model solve at that C reproduces the circuit's
  tuned `S₁₁` to 8.26e-5 and the reduced 2×2 to 6.12e-5,
  `20260914T020419Z_PORT-15.log:1967–1968, 3732–3742`) — **self-consistency
  between the field solve and the circuit reduction on one F-small fixture
  at 64 MHz; "tuned" is a series resonance (`R_in` 6.77 Ω, `|S₁₁|` 0.761),
  not a match, 128 MHz is a printed reading, and no mode frequency is
  claimed** (`TH-17`).
  **The F-small tuned resonance is located by a driven sweep consistent
  with the circuit layer across 44–84 MHz** (`PORT-22` step 1 ✅
  2026-09-20): on the 116 085-cell gate mesh at degree 1, `Im Z_in(f)`
  from the in-model tuned drive runs −34.62 → +25.60 Ω over the grid with
  **exactly one sign change, in the [60, 64] MHz bracket** (interpolated
  zero 63.9986 MHz, `R_in` 6.7725 Ω, loaded Q 6.93 — printed, not gated),
  and at **every** one of the 11 grid frequencies the circuit reduction of
  that frequency's *untuned* 4×4 reproduces the in-model tuned `S₁₁`
  within the imported `REDUCTION_BAND` = 1e-3 (worst 8.256069e-05 at
  64 MHz, 0.083× band; κ computed in-run, 1.0600e-02 → 1.0618e-02 across
  the band), while the same prediction at `0.5 × C_tuned` misses by
  1.116902 = **1117× the band** (`20260920T110503Z_PORT-22.log:2136–2153`,
  `20260920T110833Z_PORT-22.log:2082–2108`). **Circuit-vs-field identity
  on one fixture, degree 1, series resonance — no absolute `S₁₁` or
  `Z_in` figure (known-issues 2026-09-19) and no mode-spectrum claim
  (`TH-17`'s).**
  **The circuit layer also runs through a vetted engine, `scikit-rf`
  2.1.0** (`PORT-23` step 1, 2026-09-23; `OPS-60` ✅ pins it): an
  `skrf.circuit.Circuit` netlist built in our code terminates the stored
  4×4 and reproduces the raw (C2) reduction to ≤ 3.5e-16 at 64 and 10 MHz,
  its sweep zero is `C_tuned` exactly, and a mis-ordered port map misses by
  201.9× the floor (`20260923T093456Z_PORT-23.log`). The raw layer stays
  as the gate; this is an engine identity, not a new physics claim.
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
  `20260906T213913Z_TH-15.log:2628–2650`). **Since `TH-15` step 3
  (2026-09-13) the birdcage hole also *solves* with its four lumped-sheet
  ports:** the 4×4 passes `PORT-9`/`PORT-11`'s imported identity gates at
  10 / 64 / 128 MHz (reciprocity ≤ 1.6e-14, σ_max ≤ 0.999994, class spread
  ≤ 0.0734 % vs 0.5 %) with the solid control reproducing `LEG_D_S_MATRIX_10MHZ`
  in the same window (`20260913T202954Z_TH-15.log:951–954, 2768`) —
  identities on the hole route, **not** an accuracy claim: the hole-vs-solid
  `max\|ΔS\|` is a printed record, and the terminal-power sum's excess over
  the volume loss (7.6937e-05 W, 1 208× the phantom loss) **is the sheets'
  own Cauchy–Schwarz deficit `C − terminal`, equal to every printed digit on
  the hole and on the solid** (step 3c,
  `20260914T005452Z_TH-15-step3c.log:969–970, 2790–2791`; hole/solid
  `C/terminal − 1` 0.9997) — the registered power sentence is
  `Σ½Re(V I*) = P_vol + (C − terminal)` (re-registered 2026-09-14 03:00
  review under rule (h); the 2026-09-13 known-issues entry is retired). The
  two-torus hole still carries no gated port current (step 2).
  **Copper as a Leontovich surface (`TH-14`, ✅ 2026-09-14):** the third-kind term
  `jωμ₀/Z_s ∫_Γc (n × E)·(n × W) dS` is gated on the lossy-wall `TH-9`
  cavity's Q against Pozar's closed form (+0.010 % at σ = 1e4, `Q ∝ √σ` to
  0.05 %, the PEC pencil damping-free to 4.8e-19,
  `20260914T004807Z_TH-14.log`) and on the F-small birdcage as a copper
  hole — the three port identities at 10 / 64 / 128 MHz, the surface-loss
  identity to 3e-13, a σ-ladder 5.8e7 → 5.8e11 whose distance from the PEC
  4×4 falls 10× per 100× σ, coil-loss share 0.929 / 0.448 / 0.219 printed
  (`20260914T021500Z_TH-14.log:1037–1364`), and — the closed form at
  copper σ — on the **Dodd–Deeds copper slab as a Leontovich floor** under
  `MAT-6`'s loop at 10 MHz: ΔR(5.8e7) −0.299 % from `coil_impedance_change`
  (band 2 %), the surface-loss identity to 1.31e-8, ΔR(5.8e7)/ΔR(5.8e9) =
  9.9910 (linear in `R_s`, band 1 %), the thin-skin identity (ΔX − ΔX_PEC)/ΔR
  = 1.00097 vs the closed form's 1.00095 (band 2 %), PEC-floor control 0
  (`20260914T094224Z_TH-14-step2.log:283–293`, 340 s; the slab is removed
  by `create_submesh` so the floor is a true domain boundary). One loop,
  one liftoff, one frequency; no absolute S on a copper coil (`ANS-6`).
- **The F-human birdcage rung is a gated *mesh*** (`GEO-25` step 2,
  2026-09-05): the 16-leg, 32-ring-port coil at `ring_radius` 0.15 m
  meshes to **504 642 cells** at fixed absolute sizing with the volume
  partition exact, all 32 terminal ratios inside [0.95, 1.0] and
  meshed/CAD conductor mass 0.965414 ≥ 0.95, while the same coil with the
  sizing scaled to the radius reads 0.893028 and fails the gate
  (`20260905T183654Z_GEO-25.log:9728–9735, 20017–20027`). CAD identities
  only — and since **`WF-7` step 0 (2026-09-13) one degree-1 single-drive
  lumped-sheet solve has run on the longitudinal-sheet variant of this rung
  at 64 MHz** (507 266 cells, 607 039 unknowns, 37 s solve, 10.93 GiB summed
  `ru_maxrss` at `-n 8`, `20260913T190102Z_WF-7-step0.log:10419–10427`) —
  a price, not a gate: nothing about that field is asserted, and no Phase 6
  date rests on it.
- `post/evaluation.py` point location (all point evaluation goes through
  it), gmsh generation + tag QA, the runner, and the logging harness.

### 2.2 Not validated — do not trust, do not extend

- **Two external disagreements are open since the 2026-09-19 weekly — read
  them before quoting any S entry.** (1) On the two-torus **current-drive**
  route (`PORT-1`, `EX-20`, `ans:3`) the reported `S` is **not the 50 Ω
  S-matrix**: the undriven port is open, so `S_ij = b_i/a_j` is not a column
  of S. The same run's `Z` is the open-circuit matrix, is what `PORT-1`'s
  gate of record reads, and agrees with the external code (`ANS-3` AGREE on
  the primary row). Every lumped-sheet-route matrix is unaffected.
  **FIXED 2026-09-20 by `PORT-20` (✅, steps 1–3): that route reports
  `S = z_to_s(Z)`, the two S-derived records are re-recorded and the
  known-issues entry is retired.** One residue, known-issues 2026-09-20:
  `ans:3`'s *generated* `metrics.json` / `COMPARISON.md` still show the
  pre-correction S table, because re-running that case in a slot would
  rewrite its gitignored private comparison. (2) The **order-matched**
  `ANS-4` comparison (our degree 2
  against AED First Order) AGREES at 128 MHz and on the coupling classes at
  all three frequencies, and **DISAGREES on the self class `S₁₁` at 64 MHz
  (the pre-registered rule fired) and at 10 MHz**, where the earlier
  degree-1 AGREE is re-read as partly coincidental. Neither rung is yet
  shown `h`-converged (`xl` 3e / 3g). Until that is resolved **no absolute
  `S₁₁`, `Z_in`, match or tuned-`S₁₁` figure is licensed at 10 or 64 MHz at
  either order**; the circuit-layer identities (`PORT-14`/`PORT-15`) are
  unaffected because both of their sides are ours. Diagnosis: `PORT-21`,
  `ANS-6`'s PEC column. Numbers private; known-issues 2026-09-19; §10.

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
- **An absolute coil-driven SAR is now externally checked at 10 MHz on
  F-small (`ANS-2` AGREE, 2026-09-18): whole-phantom dissipated power to
  5 % of HFSS (AED lower), pointwise SAR at the four ball centres within
  ±10 % (scatter on our side); normalised to accepted power the codes agree
  to ≈ 1–2 %, so the residual is the lumped-port feed systematic, not the
  SAR operator. The *compliance* SAR number — the IEEE C95.3 *limit*
  claim — is still open** (it needs a body model, a real input power and a
  real coil), and remains open after
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
| `xl` | **4 h, 512 GiB, 16 ranks — six runs per trailing 7 days, i.e. every night Sun–Fri** (4 h since 2026-09-13, was 2 h: step 2d's 7225 s window is the measured reason; a full window now ends 06:00 and overlaps the 04:30 slot, accepted) (operator directive 2026-09-13 — the windows cost no tokens and the box is quietest at 02:00; three from 2026-09-10; was one, raised because the measured constraint turned out to be wall-clock rather than memory) | The convergence rung the heavy tier cannot hold (operator directive 2026-09-05). Runs against the separate `fem-em-solver-xl` compose service (profile `xl`), **commissioned by the weekly planning review** — pre-registered in `docs/testing/xl-pending.md` with a named chunk and step, the exact command, a *measured* price and the readout — **and queued by the daily review as clerk** into `docs/testing/<tier>-queue.env` whenever the queue is empty and the ledger budget allows (operator directive 2026-09-13, daily-review.md step 6b; before that only the weekly could queue, so at most one of the three windows a week ever ran), and recorded in `docs/testing/xl-ledger.md`; the bash guard denies a second XL exec inside 7 days, any XL exec outside `run_and_log.sh`, any `timeout` above 7200 s, and `-n` above 16. First slot reserved for the `ANS-4` 128 MHz refinement rung |
| `xxl` | **8 h, 754 GiB, 16 ranks — one run per trailing 7 days, Saturday 02:00** (operator directive 2026-09-10) | The window a 2 h `xl` slot cannot hold: the human-scale coil, or a many-drive sweep before the factorisation is reused. Runs against the separate `fem-em-solver-xxl` service (profile `xxl`), from `docs/testing/xxl-queue.d/` via `xl-run.sh xxl`, recorded in `docs/testing/xxl-ledger.md`. 754 GiB is this WSL VM's **whole** allocation — half the machine's 1.5 TB — so the kernel OOM killer reaches a runaway before the cgroup does; that is the operator's stated choice and is recorded in `docker-compose.yml` rather than silently softened. Saturday is its own cron day so the two tiers cannot both start at 02:00 |

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
  runs the first `*.env` file in `docs/testing/<tier>-queue.d/` (a FIFO
  since 2026-09-15 — the one-slot `<tier>-queue.env` it replaces lost every
  window after a review-less night, and is honoured only as a legacy
  fallback), checks the ledger budget before taking it, and deletes the
  file afterwards; an empty directory is the normal state and the entry
  then costs a second. **No Claude session is involved**, which is also what makes
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
- **The big-compute slots are a budget, not a loophole — and, since
  2026-09-15, one that is meant to be spent every night.** Six `xl` runs and
  one `xxl` run per trailing 7 days, commissioned by the weekly review on the
  measurements the heavy tier cannot hold, with the daily review holding a
  backlog floor of ≥ 4 `xl` and ≥ 1 `xxl` entries ahead in
  `docs/testing/xl-pending.md` and a licence to fill a shortfall with
  **priced-family variants** and **cost probes** only (daily-review.md step
  6b; operator directive 2026-09-15, after four of five nightly windows
  fired empty in the first wind-down week); the
  ledger row is written by the harness *when the run starts* — since
  2026-09-19 into the gitignored sidecar `logs/<tier>-ledger.pending`,
  folded into the tracked ledger when the window ends (a killed wrapper's
  row is folded in by the next window, elapsed blank), so that a window
  overlapping the 03:00 review or an implementer slot no longer leaves
  `main` dirty for its whole length — so a killed
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
  window on it is a cost probe whose readout says so. A **priced-family
  variant** (same script and mesh as a measured row; frequency, degree,
  drive or port set, rank count or one env knob varied) inherits the
  family's measured price with the scaling stated, and is the one class
  the daily review may commission without a new measurement (2026-09-15).
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

- **A second independent reference (operator directive 2026-09-20): Palace.**
  Beside the private AED columns, the open-source Palace solver (`OPS-61`) is
  a reference the project *may publish* — its numbers can live in tracked
  `COMPARISON.md` columns and in gate bands, which AED numbers never can.
  The rule that a benchmark is a judge and never the solver applies to it
  unchanged: nothing in `src/` is built on Palace. Commissioning a Palace
  case is the weekly's, like an AED case; the first is the `ANS-4` fixture,
  to adjudicate the ≈ 3 % self-class offset `ANS-6` isolated to the port
  model.

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
| 2 | Time-harmonic Maxwell, complex materials, ABC/PML | `TH-1`…`TH-9` | In progress — every analytic gate closed (`TH-1`/`TH-6`/`TH-7`/`TH-8`/`TH-9` ✅); Larmor sphere `TH-10` ✅; coil trend `TH-11` ✅ closed on a measured negative (no 64 MHz h → 0 bracket fits the box, 2026-08-18); degree-2 `TH-12` ✅ (closed 2026-09-02 on the re-affirmed production-order clause: degree 1 coil-fed, degree 2 imposed-field), `TH-13` ✅ 2026-08-31 (the injector is the degree-1-only source projection; coil degree-2 identity reds stay open in known-issues); **`TH-19` steps 1–2 ✅ 2026-09-10, outcome (a) — the matched projection clears the degree-2 coil identity by five orders on both σ-halves; production order unchanged until step 3 tests the birdcage's sheet drive (§10 2026-09-13)**; **`TH-19` step 3 ✅ 2026-09-13 (both degree-2 identities green on the sheet drive at 10 / 128 MHz); `TH-14` ✅ 2026-09-14 (copper via Leontovich: cavity Q +0.010 %, Dodd–Deeds floor −0.299 %, the copper birdcage's identities); 2026-09-19 weekly: degree 2 is the target order and the default is not flipped — decision pre-registered for 09-26 on `xl` 3e / 3g (§10)**; `TH-2`/`TH-3` API hardening ⚠️ |
| 3 | Material models, phantoms, SAR | `MAT-1`…`MAT-6` | `MAT-2` ✅; **`MAT-4` externally anchored 2026-09-18 — `ANS-2` AGREE at 10 MHz on F-small (5 % integral / ±10 % pointwise, residual = feed; no compliance claim)**; `MAT-6` ✅ (ΔR to **0.2747%** on the production projected drive and the 418 888-cell slab-refined fixture promoted by step 11, 2026-09-06 — 1.5834% was the pre-refinement record; eddy-current regime; **externally checked 2026-09-02 — `ANS-1` adjudicated AGREE against Maxwell 3D, numbers private; the weekly re-checks that verdict against the moved column**); SAR gated on an **imposed** uniform field only (`MAT-4` steps 1+3: lossy-sphere closed form 3.5%, mass-averaging exact at 1 g/10 g) — **`MAT-4` ✅ 2026-09-06 — step 4 puts the C95.3 mass-averaging operator on the *coil-driven* field: 10 g C4 identity 0.3303 / 0.0756 / 0.0574 / 0.3132% at the unmoved 5% band on F-small at 10 MHz, whole-phantom coverage identity 1.58e-14; the 1 g column is a printed record at 6.84% and the absolute / compliance claim is still open**; **step 5 + 5b close the 1 g column as a gate 2026-09-08 — the four 1 g C4 pairs 0.0957 / 0.1199 / 0.1305 / 0.1065% asserted at the same unmoved 5% band on `GEO-27`'s `h_p` = 0.0025 m rung (199 920 / 58 866 cells, a version-tagged record at the imported `CELL_COUNT_BAND`), both steps audited PASS** *(step 5 by the 2026-09-08 10:30 review; step 5b by the 2026-09-09 03:00 review — this cell was written by the 02:15 weekly 35 min before 5b's audit actually ran, and the audit then returned PASS, so the claim is true as of 03:00 and was premature when written)* — still a symmetry identity at one frequency on one fixture, still no absolute, C95.3-compliance, homogeneity or Larmor-SAR claim |
| 4 | Coil modeling, lumped elements, ports, S-params | `PORT-1`…`PORT-11` | `PORT-1` ✅ 2026-08-15 (field-derived S through the package, two-torus fixture only, two named systematics); `PORT-10` ✅ 08-16; **`PORT-9` ✅ 2026-08-25 at 10 MHz on the gapped 4-leg birdcage** — leg (d1′)'s geometric negative control passed on the power-wave route (displaced classes 6.2219 / 7.1142 / 2.8474% vs the tightened (iii′) 0.5%, reciprocity 2.259e-14 vs 1e-3, 2.466e+11× from the pre-fix 5.57e-03), no Larmor/resonance/tuning claim; history: steps 1–2c ✅ on the two-torus (lumped-sheet BC, 1.8333% cross-route, reciprocity 2.6e-11), step 3 on the gapped birdcage has two gated legs (c)/(d0) at 10 MHz (C4 spread 0.0152–0.0159% vs 5%, 50 Ω termination separates the classes 598× — re-recorded image-tagged on the 0.11 image 2026-08-24 by leg (d3c): 0.0359%, 253.2002×) and **leg (d) closed 2026-08-23 — the 4×4 passes all three gates** (reciprocity 2.495292352e-05 vs 1e-3, σ_max 0.862659137 ≤ 1, class spreads 0.0199 / 0.0180 / 0.0108% vs 5%, gate (iii) since tightened to 0.5%); leg (d1)'s geometric control ran 2026-08-23 and **found the route loses reciprocity (5.57e-03 vs 1e-3) once the fixture is asymmetric**; leg (d2) (asymmetric two-torus, 13:30 slot) traced it to the assembly — the readout *is* the source's adjoint (1.33e-10), the asymmetry is the terminated-`Z` per-column normalisation — and the 18:00 review ruled the power-wave S fix (leg (d3)) with the class re-record (d3b), (d1′) serial on (d3b); **`PORT-11` ✅ 2026-08-26 — the same three gates at 64 and 128 MHz on the same fixture** (64: 2.581325834e-14 / σ_max 0.999721388 / spreads 0.0573 / 0.0599 / 0.0370%; 128: 7.030990825e-15 / 0.998974779 / 0.1012 / 0.0916 / 0.0654%, cells/λ 12.5024 ≥ 10 enforced; audited COMPLIANT 18:00 review) — self-consistency identities only, no absolute-accuracy/resonance/tuning claim; **externally checked — `ANS-4` adjudicated AGREE at 10 MHz against HFSS (2026-09-06) and AGREE at 64/128 MHz (2026-09-13 weekly: on the order-matched degree-2 rung at 128 MHz, by mechanism at 64 MHz pending `ANS-4` step 3; numbers private; the degree-1 gate fixture's own 128 MHz entries sit 5–7 % from their order-matched value, invisible to the identity gates)**; `PORT-13` ✅ 2026-09-04 — the 32×32 on the 16-leg / 32-ring-port longitudinal rung passes the same three gates (reciprocity 5.4e-13, σ_max 0.9999995, 18 C16 × mirror classes ≤ 0.45%), self-consistency only; **2026-09-19 weekly — two external findings, numbers private: (1) `ANS-3` AGREE on the mutual-coupling row, but `PORT-1`'s current-drive route reports an `S` that is not the 50 Ω S-matrix (its `Z` is right; `PORT-20`, known-issues); (2) the order-matched `ANS-4` rungs: 128 MHz AGREE stands (3b), the 64 MHz rule fired on the self class (the "by mechanism" AGREE is withdrawn for `S₁₁`, kept for the couplings) and the 10 MHz degree-1 AGREE is re-read as partly coincidental (3c) — no absolute `S₁₁` / `Z_in` claim at 10 or 64 MHz at either order (`PORT-21`, known-issues)**; `PORT-4`…`PORT-8` open |
| 5 | Full MRI system: loaded birdcage, B1+, SAR maps | `WF-5`…`WF-8` | Blocked on Phases 2–4 for excitation; both meshes (coil+phantom, birdcage) generate and are identity-gated in CI (`GEO-9`, 2026-08-03); the birdcage fixture is loaded (phantom inside) and since `GEO-18` ✅ 2026-08-22 has terminals and port sheets — **`WF-6` steps 1–2b ✅ (2026-08-30/31): `\|B₁⁺\|` maps on the loaded F-small birdcage symmetry-gated at CG1 at 10, 64 and 128 MHz, in ParaView (`EX-38`/`39`/`40`), no homogeneity/absolute/tuning claim; coil-driven SAR is measured, not gated — steps 3–3e: the packaged phantom-restricted `E` estimator is honest (best-approximation and power anchors) and the five SAR identities still miss 5% at 6–9.5%, verdict (c), the ~1 cm phantom cells; **step 3f (2026-09-02) halves the phantom's `h` and all five land inside the band at 2.5–3.5%, clause (a) — verdict (c) confirmed, no gate registered in-slot, and the `\|B₁⁺\|` identities turn out not to be mesh-converged either (2.19% → 0.62%, three deliberate reds + known-issues)**; **step 3g (same day) reads the C4 identities as cell integrals of the primal `σ\|E\|²` on the coarse mesh and lands all twelve pairs at ≤ 1.52% — the construction, not `h`, was the binding mechanism**; **step 3h ✅ (2026-09-02) registers the repo's first coil-driven SAR gate — a C4 symmetry identity of quadrant powers on one fixture at 10 MHz at fixed `h` (twelve integral pairs ≤ 1.52% against the imported, unmoved 5% band), with the five pointwise asserts retired to records that still exceed the band; no mirror identity, no absolute SAR, no homogeneity, no C95.3, no Larmor, no convergence claim, and `WF-6` stays 🟡**; **2026-09-09 weekly: the SAR half of the F-small exit is DONE and the B₁⁺ half is now the single blocker.** The 09-06 review's "one item away — `MAT-4` step 2" landed 2026-09-06 as **step 4** (the step was renumbered, not skipped) and step 5b extended it to 1 g on 09-08, so the 09-06 watch condition ("if `MAT-4` step 2 is not ✅ by the 09-09 weekly, re-plan the SAR route") is **met, three days early**. What remains is subgoal 4's other half — the B₁⁺ closed-form gate, `WF-6` step 4 — which has taken **six attempts in five days (4, 4a, 4b, 4c, 4d, 4e) and landed two records and four parked negatives, zero gates**; the 09-08 10:30 ruling finished the comparand (odd-order cube sum `S_11`, bar ≈ 0.5–1.1%) and put the residual miss on the FEM, so the item is now **`WF-6` step 4f — the `h`-ladder**, priced by `GEO-29` (§10 Phase-5 assessment 2026-09-09); **2026-09-13 weekly: the 09-09 rule fired — no closed-form gate landed, and what the `h`-ladder measured is a monotone fall of the C4 four-copy spread (5.2506 → 2.0719 % on `main`, step 4g; the third rung stalls and its power residual is a banked negative), so subgoal 4's B₁⁺ target is re-scoped to that convergence statement (epitaph in §10) and Phase 5 exits on F-small when `WF-6` step 5 registers it — one tests-only item, ≈ 2026-09-14…15 if its first window is green**; **`WF-6` step 5 ✅ 2026-09-13 (12:00 slot) — see the §7 row**; **2026-09-19 weekly: Phase 5 has exited on F-small (`WF-6` ✅; `ANS-2` AGREE 2026-09-18, ratified) on the scope §10 states — no homogeneity, compliance, Larmor-SAR or human-scale claim; the human-scale maps are Phase 6's chain H** |
| 6 | Birdcage tuning at 64/128 MHz: mode spectrum, lumped capacitors, circuit co-simulation (the HFSS + Circuit split); production target: **32-port high-pass birdcage at 1.5 T** (§10 operator directive 2026-08-17); **fixture scale re-directed 2026-08-25 — two fixtures, F-small (today's 0.07 m gate fixture, records frozen) and F-human (≈ 0.15 m radius / 0.30 m long high-pass, the deliverable fixture); the `N ≤ 25` ceiling was arithmetic on the wrong radius and dissolves at human scale. Full directive in §10 Phase 6 — the 2026-08-30 weekly review must dispose of it, cost probe first** | **Gating chunks, listed explicitly 2026-09-09 weekly so §5.4's ramp is mechanically checkable on this phase (it was the one row with no `X-1…X-n` range): `GEO-19`, `GEO-20`, `GEO-25`, `GEO-26`, `PORT-13`, `PORT-14`, `PORT-15`, `TH-17`** — six closed ✅ at chunk-or-gated-step granularity, so the ramp is 5 and the corpus carries 8. Subgoals owned by the weekly review (§10); mesh prerequisites `GEO-19` (16 legs, cost rung) + `GEO-20` (ring-gap ports) scoped 2026-08-23, + `GEO-26` (longitudinal ring sheets — opened 2026-09-03 after `PORT-13` step 1 measured the `GEO-20` sheets transverse, `h = 0` for the lumped port model; the first ring-port solve waits on it) | **Started 2026-09-04 on the feature ladder** — mesh prerequisites all ✅ (`GEO-19`, `GEO-20`, `GEO-26`, `GEO-25`: the F-human rung is a gated 504 642-cell fixture, cost exponent 0.84 not r³), `PORT-13` ✅ (the 32×32), `PORT-15` step 1 ✅ (ladder-network closed form + S/Z reduction at machine precision), `POST-6` step 1b ✅; `PORT-14` 🟡 (lumped RLC sheet single-mode to 3.4e-3 — ruled a fixture record 2026-09-06, §7); conductor lineage `TH-15` steps 1/2a ✅; **2026-09-09 weekly: `TH-15` step 3a ✅ 2026-09-06 (`birdcage_port_domain(as_hole=True)` — the coil as a PEC hole) and step 2d ✅ 2026-09-07 (the gap-displacement port current on the open-circuit anchor), so `TH-17`'s mesh-side prerequisite is discharged and only `PORT-14` step 2 remains serial ahead of it; `PORT-16` ✅ 2026-09-07 (the exact discrete power identity on the 4-leg birdcage, single and superposed drives) closes the 1%-of-supplied accounting gap `POST-6` step 1b opened. `TH-15` step 2 itself is still open after seven sub-steps — 2f attributed the 2% `Z` asymmetry to the point-sampled `_path_voltage` and 2g measured the calibrated gap average as reading B; the `src/` replacement is specified but unwritten. `PORT-14` step 1e (the 09-06 ruling's `REDUCTION_FLOOR_F_SMALL` re-registration) has not been queued in three days and is the phase's oldest unstarted owed item** *(landed 2026-09-11)*; **2026-09-13 weekly: `PORT-19` ✅ (one factorisation per sweep, 11.2× on the 32×32), `TH-15` step 3b ✅ (`gap_cell_tags` landed, default unflipped; step 2's unitarity gate and step 3 still open), `PORT-14` step 2 frozen on a positive reading (a (1 + κ)-corrected width takes both 64 MHz residuals under 1e-3, unregistered — step 3 is the κ-derived registration); the tuned-birdcage chain is enumerated in §10 as ten numbered steps — internal milestone `TH-17` mode 1 at 64 MHz ≈ 2026-09-25…10-01 at the measured 2–3 days per numbered step, the AED-matched tuned `S₁₁` undated on the operator's AED queue**; **2026-09-19 weekly: seven of the ten chain steps landed 09-13/14 (`PORT-14` ✅, `PORT-15` ✅, `TH-15` step 3, `TH-19` step 3, `TH-14` ✅, `POST-6` ✅); `TH-17` step 1(i) found no eigenvalue at 64 MHz (1b queued; `PORT-22`, the driven-sweep resonance, opened as the independent route); `WF-7` 0b: human-scale order sensitivity 5.50 %, degree 2 priced at 106.1 GiB / 348 s per drive; `ANS-6` commissioned; three chains (T tuned, F feed model, H human scale) enumerated in §10 with 11 slot-executable steps — 2026-09-30 … 11-19 at the interval's two measured rates; the AED-matched tuned `S₁₁` stays undated, serial on chain F**; first physics target `TH-17` eigenmodes; no completion date (§10) |
| 7 | Implants: parametric implant geometry in the phantom, local SAR / near-implant hot spots | subgoals owned by the weekly review (§10) | Not started |
| 8 | Thermal: Pennes bioheat driven by SAR | subgoals owned by the weekly review (§10) | Not started |
| 9 | Advanced: MPI scaling, AMR, sweeps, optimization | — | Deferred — **`ARCH-1` (solver-agnostic MRI-safety layer) is embargoed until the 2026-10-17 weekly by operator instruction, §7**; **AMR is feature ladder C4** (operator directive 2026-09-04): not a boundary condition, but the largest remaining HFSS workflow gap (adaptive passes are what make an HFSS answer trustworthy without a mesh study); revisit after Phase 6 |

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
| `OPS-47` | **Move the open chunks' blockquote narratives out of `PROJECT_PLAN.md`** — *opened 2026-09-13 weekly review (§10 plan hygiene; row written by the operator's interactive session, which landed that review after the scheduled session died on the account limit).* **The defect, measured 2026-09-13:** `OPS-46` moved the 73 heavy table *rows* (806 962 B, under its 850 000 B bound), but the `>`-blockquote narratives it declared out of scope are the line count — `WF-6` 2 295, `TH-15` 1 243, `PORT-14` 736, `POST-6` 157 lines, **4 431 lines = 48 % of the file** — all under **open** chunks, which the archive contract forbids summarising or compressing. It does not forbid moving them byte for byte. **Change:** extend `scripts/maintenance/rotate_plan_archive.py chunks` to a chunk's blockquote narrative: the contiguous `>` block(s) under a §7 family table that name one chunk move verbatim to `docs/planning/chunks/<ID>.md` (appended after the row history the `OPS-46` move put there), replaced in place by one pointer line; same byte-identity refusal (the re-read file body must equal the extracted span), never overwrite, `--dry-run` and `--census` as for rows. **Anchors (asserted):** (i) every moved block is byte-identical to its new file span — an empty diff per chunk; (ii) `check_private_leak.py --audit` exit 0 after the move, with a planted synthetic value under `docs/planning/chunks/` caught first (positive control); (iii) `PROJECT_PLAN.md` line count re-measured before/after with `scripts/probes/measure_plan_sections.py` and recorded — the 4 000-line guide (weekly-review.md step 6) is the target, and the row says plainly whether it is met; (iv) every § reference in CLAUDE.md and `docs/automation/*.md` still resolves. Docs/tooling only — no `src/`, no test, no band. One commit for the tool, one per chunk for the moves. | ✅ Closed 2026-09-13 15:00 slot (step 2): the four narratives are moved byte for byte, one commit each (`POST-6` `dc39b23`, `PORT-14` `d0b8af6` — file created, `TH-15` `0968eda`, `WF-6` `20689ba`). **Span definition** (the step-1 tool's, ratified for the slot): from the chunk's opener line `**`ID` …` to the line before the next §7 table row, `##`/`###` heading or another chunk's opener, trailing blanks dropped — so `POST-6`'s 44 leading `POST-1`/`POST-3` lines stay in the plan. Anchors per chunk: (i) an independent re-extraction from `git show HEAD:PROJECT_PLAN.md` at the pre-commit revision is `cmp`-equal to the chunk-file span, and the written plan is `cmp`-equal to HEAD with that span replaced by the pointer; (ii) `check_private_leak.py --audit` rc 0; (iii) plan 9 951 → 9 840 → 9 078 → 7 838 → **5 546 lines**, 838 503 → **527 145 B**, each shrink = span − pointer, rider `--assert-below-*` PASS (`20260913T201352Z_OPS-47-step2-POST-6.log:35–68`, `…201427Z_…-PORT-14.log:34–69`, `…201455Z_…-TH-15.log:34–68`, `…201524Z_…-WF-6.log:34–73`); negative control, a spec naming `OPS-46` (row, no narrative), refused rc 1 with the plan unchanged (`…201336Z_…-neg.log:37–42`); (iv) all 88 `§N`/`§N.M` references in CLAUDE.md and `docs/automation/*.md` resolve, 0 unresolved (`…201542Z_…-final.log:46–49`). **The 4 000-line guide is NOT met:** 5 546 lines (`--assert-below-lines 4000` FAIL rc 3, `WF-6.log:50`; `final.log:50`), a miss recorded with the guide not widened. **Step 1** landed 2026-09-13 15:00 slot: `chunks --narratives` moves a narrative (opener `**`ID`` to the next boundary, measured not to be a pure `>` block) byte for byte, with the byte-identity refusal, a scripted size assert, and anchors (a)/(b)/(c) plus both negative controls green (`20260913T200730Z_OPS-47-step1-leak.log:53–58`, `20260913T200801Z_OPS-47-step1-moves.log:46–104`). The dry run gives `WF-6` 2 293, `TH-15` 1 241, `PORT-14` 763 and `POST-6` 112 lines (4 409; the probe's 157 for `POST-6` includes 44 lines of the `POST-1`/`POST-3` blockquote); at step 1 nothing had moved on the real plan. *Narratives: `docs/planning/chunks/{POST-6,PORT-14,TH-15,WF-6}.md`.* | smoke |
| `OPS-48` | **Restore the `EX-14` VTX read-back gate on the 0.11 image** — `mag:1` / `mag:2`'s `_check_vtx_roundtrip` calls the pre-2.10 `adios2.ADIOS()` API, catches the `AttributeError` and returns `False`, so the "written `.bp` reproduces the in-memory field" anchor has not executed since the image moved and the examples exit 0 regardless (known-issues 2026-09-14; found by the `EX-57` figure runs, `20260914T125223Z_EX-57-straight-wire.log:285`, `…125551Z_EX-57-circular-loop.log:305`; probe `…125326Z_EX-57-adios2-probe.log:34` reads `adios2 2.12.1 has ADIOS: False`). **Done-when (§4):** the reader ported to the 2.12 bindings (`adios2.bindings.ADIOS` or `FileReader`, the VTX local-block walk kept), both examples run through the harness at `-n 2` with `relative difference ≤ VTX_ROUNDTRIP_RTOL` (1e-10, unchanged) **asserted and executed** (the log shows the `✓ written .bp reproduces` line, not the `⚠ unavailable` line), a wrong-comparison control (read-back vs 0.5 × in-memory) printed at rel ≈ 1, the guides' read-back sections re-cited to the new logs, censuses `broken=0` / docrefs `exit != 1`, elapsed recorded, the known-issues entry retired in the same commit. Opened 2026-09-16 03:00 review (§9 item 2). **Closed 2026-09-16 (04:30 implementer slot).** The 2.12 bindings keep the identical low-level classes under `adios2.bindings` — measured `adios2.__version__ == '2.12.1'`, `hasattr(adios2.bindings, 'ADIOS') is True`, `Mode.ReadRandomAccess` / `Mode.Sync` present, `IO.SetEngine` / `IO.AvailableVariables` present (`20260916T094031Z_OPS-48.log`, `20260916T094102Z_OPS-48.log`) — so the port is a one-line import change plus the two `Mode` references; the BP4 local-block walk (`BlocksInfo` → `SetBlockSelection` → `Get`) is unchanged. The `⚠ unavailable` path now **raises** instead of returning `False`. **Executed, real build, `-n 2`:** `mag:1` `relative difference = 0.000e+00` (tol 1e-10) on in-memory = read-back = `4.972891321210e-05 T`, control (read-back vs 0.5 × in-memory) = `1.000e+00`, i.e. 1e10× the band — `20260916T094210Z_OPS-48-mag1.log:400–407`, Status 0, **7 s**; `mag:2` `relative difference = 0.000e+00` on `7.861367746496e-05 T`, control `1.000e+00` — `20260916T094228Z_OPS-48-mag2.log:337–343`, Status 0, **136 s**. Censuses `20260916T094524Z_OPS-48-census.log`: setup figures `broken=0` (`SUMMARY: examples=54 ok=9 missing=45 broken=0`), docrefs `dead=0 guide=0 stale=28 stale_severity=report exit=2` (≠ 1; the 28 stale entries are unrelated regenerable ParaView artifacts, pre-existing). Both guides re-cited to the new logs; the known-issues 2026-09-14 entry retired in the same commit (other `.bp` read-backs still not surveyed). No `src/` change. *Audited PASS 2026-09-18 03:00 review (`…094210Z_OPS-48-mag1.log:401–407`, `…094228Z_OPS-48-mag2.log:337–343`; the anchor and the control are executed `raise`s at `01_straight_wire.py:129–138`). The survey was then done by that review: one more dead-API reader and a writer-side short-circuit of this same gate — `OPS-50`.* | ✅ | standard (`mag:1` 7 s, `mag:2` 136 s at `-n 2`, measured) |
| `OPS-49` | **A time-series XDMF writer beside `write_xdmf_with_tags`** — `consolidate_xdmf_grids` collapses time collections and drops `<Time>` ("single-timestep files only", `io/paraview_utils.py:71`), so an example that wants rungs or drive states as ParaView time steps cannot use the helper: `EX-56` wrote two per-rung files, `EX-58` bypassed the helper with `XDMFFile` (known-issues 2026-09-16). **Done-when (§4):** additive `write_xdmf_time_series(filename, mesh, cell_tags, steps, comm)` with `steps = [(t, {name: Function}), …]`, one temporal collection whose `n` children each carry every field and CellTags; unit test at `-n 2`: (a) the XDMF parses to exactly one collection with `n` `<Time>` values equal to the `t`s written and every attribute on every child (in = out), (b) each step's arrays read back through `h5py` equal the gathered function arrays at rel ≤ 1e-12, (c) negative control — the same steps through the existing `write_xdmf_with_tags` at the pre-change commit (pinned `<sha>^`) collapse to ≤ 1 time value; `write_xdmf_with_tags` / `consolidate_xdmf_grids` byte-identical; elapsed recorded; the known-issues entry retired in the same commit. `EX-56` / `EX-58` are not rewritten by this chunk. Opened 2026-09-16 03:00 review (§9 item 3). **Closed 2026-09-16 (04:30 implementer slot).** `write_xdmf_time_series(filename, mesh, cell_tags, steps, comm, facet_tags=None)` plus a private `_consolidate_xdmf_time_series` that keeps the time axis: dolfinx's per-field temporal collections are merged onto the first collection's per-`t` children, the mesh grid's Topology/Geometry are inlined into each child (the xi:include targets go away with the mesh grid) and the single collection is the Domain's only grid. `facet_tags` is **rejected** with a `ValueError` (separate topology grid, out of scope); mismatched `{name: Function}` keys are rejected too (`write_function` names the grid after the function, so they would silently collide). Diff vs `fff1673`: **186 insertions, 0 deletions** — `write_xdmf_with_tags` and `consolidate_xdmf_grids` are byte-identical. **Executed, real build, `-n 2`, `20260916T095021Z_OPS-49.log`:** (a) count identity — `collections=1 children=3 times=[0.0, 0.5, 1.25] attrs/child=['CellTags', 'phi', 'sigma']`, every child also carrying its own Topology and Geometry; (b) `h5py` round trip — worst relative error **0.000e+00** over 6 arrays (3 steps × {CG1 `phi`, DG0 `sigma`}, globally gathered owned dofs, sorted), bound 1e-12; (c) asserted negative control at the pinned pre-change commit `fff1673` — the same three states through `write_xdmf_with_tags` give `<Time>` elements per file `[0, 0, 0]`, the collapse the known-issues entry describes. 3 passed in 0.83 s, elapsed **2 s**; `tests/io` regression 13 passed, elapsed 3 s (`20260916T095045Z_OPS-49.log`). Known-issues 2026-09-16 retired in the same commit. `EX-56` / `EX-58` not rewritten; ParaView's Xdmf3 reader itself cannot be exercised headless, so the XML identity is the gate. *Audited PASS 2026-09-18 03:00 review (`…095021Z_OPS-49.log:50–51,54,59,64–66`; asserts at `tests/io/test_xdmf_time_series.py:170–180,217–218`); caveat banked: control (c) runs today's `write_xdmf_with_tags`, argued byte-identical to `fff1673` by the 0-deletion diff, not a checkout of that commit. `EX-56` cannot adopt the writer (its two rungs are two meshes; the writer takes one) — the journal's follow-up applies to `EX-58` only and moves no status, so it is not queued.* | ✅ | smoke (2 s at `-n 2`, measured) |
| `OPS-50` | **Close the writer-side hole in the `EX-14` VTX read-back gate, and port the last dead-API `adios2` reader** — the survey `OPS-48` left open, done by the 2026-09-18 03:00 review (read-only sweep; exactly three files in the repo touch `adios2`). **(a)** `mag:1` / `mag:2` wrap each `io.VTXWriter` in `try/except Exception` that only prints `⚠ VTX output of B failed`, and the gate is then called as `if not (vtx_B_written and _check_vtx_roundtrip(…))` (`01_straight_wire.py:412–432`, `02_circular_loop.py:357–377`) — a writer failure short-circuits the read-back away and the example prints "XDMF files were still created" and **exits 0**: the same silently-disabled-gate mode `OPS-48` fixed on the reader side, reached through the writer. **(b)** `scripts/probes/post4_step5_probe.py:215–232` (`read_vtx_block`) still calls the pre-2.10 top-level `adios2.ADIOS()` / `adios2.Mode.*`; on the 0.11 image (`adios2` 2.12.1) it dies with an `AttributeError` — loud, not silent, but it is the probe the dashboard names as the regenerator for the operator's "does ParaView open a DG1 `.bp`" check, and it has not run since 2026-08-12 (`20260812T200532Z_POST-4-step5-n2.log`, v0.7.2 image). Known-issues 2026-09-18. **Done-when (§4):** (a) a `B` writer failure **raises** in both examples (the `A` writer may stay tolerant — no gate reads it); asserted control: a harness window that runs `mag:1` with `dolfinx.io.VTXWriter` monkeypatched to raise exits **non-zero**, and the same wrapper on the example file taken from the pinned pre-change commit exits **0** (the defect); the unpatched `mag:1` and `mag:2` reproduce `OPS-48`'s printed digits (`relative difference = 0.000e+00`, control `1.000e+00`) at `-n 2`; `PARAVIEW_GUIDE.md:166–170` reworded (both failure paths now exit non-zero). (b) the probe ported to `adios2.bindings` (the `OPS-48` edit, verbatim) and run at `-n 2` on the complex build printing `PROBE_RESULT PASS` with its own round-trip anchor and `PIN_REPRO_RTOL` unchanged — or, if the fixture pin has moved on the 0.11 image, the printed drift reported and (b) held 🟡 (a version-tagged record is `record-reconciler`'s, not this chunk's — ***amended 2026-09-20 03:00 review, §9 rule (j):** that agent's ≈ 0.5 % drift gate forbids it this re-record, step 2's two-instrument table licenses it, and the implementer performs it once as step 3 (§9 item 15): `STEP4_CELLS` and the three medians version-tagged to the 0.11 image, B to five significant digits, `PIN_REPRO_RTOL` untouched, the pinned pre-change probe still failing as the control; `PROBE_RESULT PASS` then closes (b)*). Censuses `broken=0` / docrefs `exit != 1`, elapsed recorded, the known-issues entry retired in the same commit. Opened 2026-09-18 03:00 review (§9 item 1). **(a) closed 2026-09-18 implementer slot; (b) 🟡 on the item's pre-registered negative-result branch — the probe imports and runs, and fails its own step-4 fixture pin.** **(a):** a `B` writer failure now `raise`s a `RuntimeError` in both examples after printing the `⚠` line (the `A` writer stays tolerant by comment — nothing reads `A` back), and `_check_vtx_roundtrip` is called unconditionally; the `vtx_B_written` flag and the "XDMF files were still created" fallback line are gone. **Asserted control, binary separation by exit status, same wrapper (`logs/ops50_control_wrapper.py`: `dolfinx.io.VTXWriter` replaced by a raising callable on every rank, then `runpy.run_path(..., run_name="__main__")`), `-n 2`, real build:** post-change `mag:1` exits **1** with `⚠ VTX output of B failed` on both ranks and the raise at both (`20260918T093606Z_OPS-50-control-raises.log:283,287,389,408`, Status 1, **6 s**); the same wrapper on the file pinned at `a33be1d` exits **0** printing `Note: XDMF files were still created and can be used instead` (`…093622Z_OPS-50-control-prechange.log:266–267,303`, Status 0, **7 s**) — the recorded defect. **Unpatched anchors reproduced, `-n 2`, real build:** `mag:1` `relative difference = 0.000e+00` (tol 1e-10, unchanged), control `1.000e+00` (`…093320Z_OPS-50-mag1.log:404–405`, Status 0, **8 s**; `max|B| = 4.972902974704e-05 T` against `OPS-48`'s `4.972891321210e-05` — a 2.3e-6 relative mesher-side drift in the *physics* value, not in the round-trip identity, which is exact on both); `mag:2` `0.000e+00` / `1.000e+00` on `7.861367746496e-05 T`, `OPS-48`'s digits to the last place (`…093336Z_OPS-50-mag2.log:340–341`, Status 0, **141 s**). `PARAVIEW_GUIDE.md` "VTX files not created" rewritten: neither `B` failure path is tolerated, the `A` warning is, and XDMF is not a substitute. **(b) 🟡:** the port landed (`from adios2 import bindings as adios2b` plus the two `Mode` references, `OPS-48`'s edit verbatim; the `BlocksInfo` → `SetBlockSelection` → `Get` walk untouched) and the probe runs end to end at `-n 2` on the complex build with its **own** round-trip anchor exact — `RT_DOF A/B/E max_abs_diff=0.000000e+00`, every `DISAGREE RT_*` line `rel_max=0.000000e+00` (`…093644Z_OPS-50-probe.log:381–389`) — but `PROBE_RESULT FAIL`, Status 1, **5 s**: `FAIL FIXTURE: 9291 cells != step-4 record 9261` and `FAIL REPRO A/B/E` at drifts of **11.4273% / 10.1019% / 7.8110%** against `PIN_REPRO_RTOL` 0.02 (unchanged), plus `FAIL PIN E` (the vertex/midpoint localisation ordering flipped) (`:393,400,407,418–423`). Per the item's scope that is a version-tagged record for `record-reconciler`, not this chunk's to move; `PIN_REPRO_RTOL` was not widened. Censuses `20260918T093746Z_OPS-50-census2.log`: setup figures `SUMMARY: examples=54 ok=14 missing=40 broken=0`, docrefs `RESULT: dead=0 guide=0 stale=27 stale_severity=report exit=2` (≠ 1; the 27 stale entries are the pre-existing regenerable ParaView artifacts). The first census pass (`…093713Z_OPS-50-census.log:92–95`) read `dead=2` — bare `` `A.bp` `` / `` `B.bp` `` tokens the guide reword had introduced, which the docref checker resolves as artifact references; the guide was reworded to name the directories instead, not the checker relaxed. No `src/`, no `tests/`. The known-issues 2026-09-18 entry is **narrowed to the probe**, not deleted: (a) is recorded there as retired, (b) stands open with the measured drift. **Ruling, 2026-09-19 03:00 review:** the residue is *not* `record-reconciler`'s — its own drift-sanity gate (≈ 0.5 %) forbids re-recording medians that moved 7.8–11.4 %, and the E-field vertex/midpoint ordering flipped (`PIN_SEP E` 1.2281× against step 4's 0.6835×); only the cell count (0.32 %) is in class. **Step 2 (executed 2026-09-19 implementer slot, measurement-only; §9 item 4):** `post4_step4_probe.py` unmodified imports and runs on 0.11 (no dead-API death), its conforming-source control exact — `CTRL_P1` MID and VTX all-zero against `CONTROL_MAX = 1e-10`, DG1 discriminator ≤ 4.15e-17 against `DISCRIM_MAX = 1e-14` (`20260919T110204Z_OPS-50-step2-probe4.log:389–396,407`) — so the table is readable. Both probes print `cells=9291` (`…probe4.log:377`, `20260919T110225Z_OPS-50-step2-probe5.log:372`) on a bit-identical mesh fingerprint. MID rel med, step-4 probe vs step-5 probe: A `4.532338e-01`/`4.532338e-01` (**0.00e+00**), B `4.717160e-01`/`4.717141e-01` (**4.03e-06**), E `2.175825e-01`/`2.175825e-01` (**0.00e+00**); VTX/MID separation `0.8198×/0.8520×/1.2281×` identical in both, against v0.7.2's `0.4185×/0.4818×/0.6835×`. So the 7.8–11.4 % drift and the flipped E ordering **are properties of the 0.11 mesh** — the instrument that made the records reads them too — and the first known-issues entry's *Cause* moves from asserted to measured. The 1e-6 anchor **fails on B** (4.03e-06), the pre-registered negative branch: filed as a second known-issues entry, but *not* with that branch's stated cause — a step-4-probe repeat 34 s later reprints B at `4.717154e-01` (`…probe4-repeat.log:399`) and the step-5 probe's two runs differ by 3.39e-06, so 4.03e-06 is inside each instrument's own spread on B while A and E are bit-identical across all four windows. B's ~4e-6 reproducibility floor is **not diagnosed** (candidate: the rank-partitioned `DG1` projection of `curl A`, unmeasured — the `-n 1` vs `-n 2` spread ladder is the next window). `OPS-50` stays 🟡; the review's question is now whether a 4e-6-reproducible B median clears the bar for a version-tagged re-record or B must be recorded to 5 digits. Nothing re-recorded; `PIN_REPRO_RTOL` untouched; no `src/`, `tests/` or `scripts/probes/` file edited. Three windows, 5 / 5 / 4 s at `-n 2`, standard, all Status 1 by design. `PIN_REPRO_RTOL` is never widened; `POST-4` ✅ stands on its own v0.7.2 logs. The "mesher-side" attribution of `mag:1`'s 2.3e-6 `max|B|` move above is a guess — the value carries no band and no status, and is recorded, not chased. **Step 3 (executed 2026-09-20 07:30 implementer slot, §9 item 15) — the licensed re-record is measured and correct, and it does NOT close (b): a *fifth* pin the licence did not name still fails, so this is the item's pre-registered negative-result branch and the change is parked, not merged.** Negative control first, the probe file at the pinned pre-change sha `30cfd74` extracted into the gitignored `/workspace/logs/` and run unmodified: `PROBE_RESULT FAIL`, Status 1, **5 s**, `cells=9291` against `step-4 record 9261`, `REPRO` drifts **11.4273% / 10.1016% / 7.8110%** (A/B/E) plus `FAIL PIN E` (`20260920T125551Z_OPS-50-step3-prechange.log:372,418–423`) — the recorded defect, reproduced in-slot. Then the re-record per the licence: `STEP4_CELLS` 9261 → **9291**, `STEP4_MID_REL_MED` A **4.532338e-01** / B **4.7172e-01** (five significant digits) / E **2.175825e-01**, GEO-16 comment style (image tag, date, both instrument logs, the v0.7.2 values and their log kept in-comment), and the separations comment given the 0.11 reading 0.8198× / 0.8520× / 1.2281× beside v0.7.2's with the E-ordering-flip sentence. `PIN_REPRO_RTOL`, `PIN_MID_MEDIAN_MIN`, `ROUNDTRIP_MAX`, `DG1_VS_SOURCE_MAX` untouched; nothing loosened. **Post-change window, `-n 2`, complex build, 4 s** (`20260920T125627Z_OPS-50-step3-probe.log`): all four licensed pins go green — `MESH_FINGERPRINT cells=9291 (step-4 record 9291)` (`:372`), `REPRO` drifts **8.293724e-08 / 9.705529e-06 / 1.167741e-07** against `PIN_REPRO_RTOL` 0.02 (`:393,400,407`), i.e. the licence's predicted ≤ 1e-5 in all three fields; round-trip anchors exact, `RT_DOF A/B/E max_abs_diff=0.000000e+00` against `ROUNDTRIP_MAX` 1e-14 (`:383,386,389`). **But `PROBE_RESULT FAIL`, Status 1, on one remaining line:** `FAIL PIN E: P1 vertex scaled median 2.126638e-01 now exceeds midpoint 1.731650e-01 — step 4's measured localization has flipped` (`:418`), i.e. the `vtx_s > mid_s` guard at `post4_step5_probe.py:540` — a **fifth** version-dependent pin. §9 item 15 licensed exactly four ("the step-5 probe's four fixture pins") and named four constants as untouchable; it did not license this guard, and re-scoping it is loosening an assertion, which an implementer may not do. The flip is *measured*, not new: `PIN_SEP E` reads **1.2281×** in all four 0.11-image windows across both instruments against v0.7.2's 0.6835×, and the review's own comment text (which this change carries) states it. So a one-line review ruling — version-tag the ordering guard to the 0.11 image, or restrict it to A and B with the E flip recorded — is all that stands between the parked change and `PROBE_RESULT PASS`. The change is committed on `attempt/OPS-50-20260920T125900Z` (`e2dd9ef`), `main` left with no `scripts/probes/` edit; the 2026-09-18 probe known-issues entry is **not** retired, and the B-nondeterminism entry stays open as ruled. Two windows, 5 / 4 s at `-n 2`, standard, both Status 1 (the first by design). **Ruled 2026-09-21 03:00 review (Done-when (b) amended again, rule (j)):** the `vtx_s > mid_s` ordering guard is a fixture-drift tripwire frozen from v0.7.2's separations; it is re-expressed as a **two-sided** version-tagged record `STEP4_SEP` = 0.8198 / 0.8520 / 1.2281 (A / B / E, 0.11 image, identical in all four 0.11 windows on both instruments) at the **unchanged** `PIN_REPRO_RTOL` 0.02 — stricter than the guard it replaces (which admitted any separation ≤ 1), v0.7.2's 0.4185 / 0.4818 / 0.6835 kept in-comment. Step 4's `REFUTED` verdict ("not O(50×)") holds on every field on both images. Executed by §9 item 26 (step 3b) from `attempt/OPS-50-20260920T125900Z`. **Step 3b (executed 2026-09-21 11:00 UTC implementer slot, §9 item 26) — (b) closed, `OPS-50` ✅.** `e2dd9ef`'s probe taken by path; the `vtx_s > mid_s` ordering guard replaced by `STEP4_SEP` = A 0.8198 / B 0.8520 / E 1.2281 (0.11 image, dated, logs cited, v0.7.2 0.4185 / 0.4818 / 0.6835 in-comment), each separation required to reproduce within the unchanged `PIN_REPRO_RTOL` 0.02, two-sided; `PIN_MID_MEDIAN_MIN`, `ROUNDTRIP_MAX`, `DG1_VS_SOURCE_MAX`, `PIN_REPRO_RTOL` and `post4_step4_probe.py` untouched. **Negative control (asserted, binary):** the `e2dd9ef` blob run from `/workspace/logs/` ends `FAIL PIN E: P1 vertex scaled median 2.126638e-01 now exceeds midpoint 1.731650e-01` / `PROBE_RESULT FAIL`, Status 1, **4 s** (`20260921T111404Z_OPS-50-step3b-prechange.log:418–419,422`). **Post-change, the committed probe, `-n 2`, complex build:** `PROBE_RESULT PASS`, Status 0, **4 s** (`20260921T111436Z_OPS-50-step3b-probe.log:421,424`): `cells=9291` (`:372`); `RT_DOF A/B/E max_abs_diff=0.000000e+00` against 1e-14 (`:383,386,389`); `REPRO` drifts 8.293724e-08 / 1.122198e-05 / 1.167740e-07 against 0.02 (`:393,400,407` — B's 1.12e-05 is the open B-nondeterminism spread, 1 800× inside the pin); `PIN_SEP_REPRO` drifts A 5.118413e-06 / B 3.490732e-06 / E 7.381801e-07 against 0.02 (`:412,414,416`). Known-issues 2026-09-18 probe entry retired; the B-nondeterminism entry stays open. | ✅ | standard (`mag:1` 8 s, `mag:2` 141 s, controls 6 / 7 s, probe 5 s, censuses 1 s — all at `-n 2`, measured 2026-09-18; step 3b probe 4 s + control 4 s at `-n 2`, 2026-09-21) |
| `OPS-51` | **Log labels that state the run's real rank width and frequency** — six prints in `tests/validation` hardcode `at -n 2` (five f-strings: `test_port_birdcage_leg_offset_sweep.py:407`, `…four_port.py:478`, `…larmor_probe.py:384`, `…lumped_column.py:519`, `…termination_probe.py:365`) or `at 128 MHz ===` (`test_ans4_resolution_ladder.py:697`), so the 2026-09-17 / 09-18 XL logs say "-n 2" on `-n 16` windows and "128 MHz" over 10 MHz data (known-issues 2026-09-18; found by the `log-pathologist` reading of `20260918T070008Z_ANS-4-step3c.log:2416,4585,4638`). Prints only; no gate reads them. **Done-when (§4):** the six literals replaced by the communicator's size and the rung's actual frequency; a `tests/unit` guard (real build, `-n 2`) asserting the count of the two literal patterns in `tests/validation/*.py` is **0**, with the asserted control that the same count on the files at the pinned pre-change commit is **6** (count identity, in = out); the ladder's step-3a flag-off control re-run at `-n 8` (its record width — `20260914T093325Z_ANS-4-step3a-w1.log`'s command verbatim) green with the 2a″ record assert **executed** at `STEP3A_RECORD_RTOL` (1e-6, unchanged) and the rung header reading `-n 8`; `pytest --collect-only` over the other four edited modules green (an f-string edit that does not import is the failure this catches); no band, record or assertion touched; elapsed recorded; the known-issues entry retired in the same commit. Opened 2026-09-18 03:00 review (§9 item 2). **Closed 2026-09-18 implementer slot.** All six literals are gone: the five `wall at -n 2` f-strings now format the solve's own communicator (`comm.size` where `comm` is already in scope — `leg_offset_sweep.py:407`, `four_port.py:478`, `larmor_probe.py:384`, `termination_probe.py:365`; `lumped_column.py` prints at test scope, so the fixture now carries `"comm_size": int(msh.comm.size)` and the PRICE line formats it), and the ladder's readout heading formats `LADDER_FREQUENCY_HZ / 1e6:g` instead of the literal `128`. **Anchor (a), real build, `-n 2`, `-s`** (`20260918T094347Z_OPS-51.log:51,57–63`, Status 0, **2 s**): the new `tests/unit/test_log_label_literals.py` scans 93 modules under `tests/validation` (never `tests/` — its own source holds both patterns as regex strings) and reads `count = 0 (required 0)`; **asserted negative control** — the same two regexes over the same 93 modules read out of the pinned pre-change commit `e091c0cbbea9146b64472e72d3215732a7431497` with `git show` (`git -c safe.directory=…`, callable in the container) read `count = 6 (expected 6)`, naming exactly the six sites known-issues listed. Count identity 6 → 0. **Anchor (b), complex build, `-n 8`** — the step-3a flag-off control, the command of `20260914T093325Z_ANS-4-step3a-w1.log:12` verbatim (`…DEGREE2=0 …C4_CONGRUENT=1 …RUNGS="1.0"`, durable capture with the trailing `; exit $rc`) — `20260918T094446Z_OPS-51-ladder-n8.log`, `15 passed, 1 skipped in 66.6 s`, `[capture] rc=0`, Status 0, **68 s**: `test_the_frequency_knob_reaches_the_solve` **executed, not skipped**, with the 2a″ record assert firing at `STEP3A_RECORD_RTOL` 1e-6 (unchanged) — `S11` rel **7.068e-11**, `S21` **8.176e-11**, `S31` **1.983e-13** (`:2154–2157`, the 09-14 window's 8.2e-11 reproduced); the rung header now reads `four driven solves in 4.68 s wall at -n 8` (`:2087`) and the step-3a line `-n 8 (record width -n 8)` (`:2153`). The readout heading reads `at 128 MHz ===` here because the flag-off control *is* 128 MHz (`FEM_EM_ANS4_FREQUENCY_HZ=unset`, `f = 1.280000e+08 Hz`) — the value is now formatted, not asserted by the string. **`pytest --collect-only`** over the four modules (b) does not exercise: `14 tests collected`, Status 0, **3 s** (`20260918T094408Z_OPS-51-collect.log:85`). **One deviation from "strings only", disclosed and covered by a fourth window:** `lumped_column.py`'s print is at test scope, so its fixture gained an additive `"comm_size"` key (3 lines, commented). Standing rule (c): the module was re-run green in the same slot — `20260918T094803Z_OPS-51-lumped.log`, complex build, `-n 2`, `2 passed in 34.60 s`, Status 0, **36 s**, with the PRICE line reading `one solve 6.52 s wall at -n 2` (`:1824`) — i.e. the same site that printed `-n 8` under the ladder's width now prints `-n 2` under this one, which is the property the chunk asserts. No band, record, assertion or control was touched (`STEP3A_RECORD_RTOL` is not in the diff); no `src/`. The 2026-09-18 label known-issues entry is retired in this commit. | ✅ | standard (guard 2 s at `-n 2`, collect-only 3 s, ladder 68 s at `-n 8`, lumped_column 36 s at `-n 2`, measured 2026-09-18) |
| `OPS-52` | **The F-human cost probe's labels say what ran** — opened by the 2026-09-19 03:00 review from a `log-pathologist` reading of the `WF-7` step 0b XXL window (`20260919T070008Z_WF-7-step0b.log`): with `FEM_EM_WF7_DEGREE=2` the probe prints `phase 4 flag-off control … vs the step-0 record` over what is the order-sensitivity readout (`:21173`), the degree-1 time bracket has never been met (37.02 s, 24.61 s against 3–8 min), the degree-2 brackets are a prediction the window undercut threefold, and `solve … (solve)` lost step 0's "(assemble+factorise+solve)". Prints only — no gate reads them; two queued windows (09-21 `xl`, 09-26 `xxl`) run this probe. **Done-when (§4):** the phase-4 label is a pure function that says `flag-off control` only at degree 1 and otherwise prints the relative move beside the degree-1 record, asserted by a `tests/unit` test (including 5.50 % on the 09-19 values) with a source-text count control 1 → 0 against the pinned pre-change sha; the two non-gating bracket dicts re-dated from the measured points with their logs; the `-n 8` flag-off control window green with the probe's own executed `S_driven` assert against an untouched `S_DRIVEN_STEP0_RECORD`; the 2026-09-19 known-issues entry retired in the same commit. Execution text: §9 item 3. **Closed 2026-09-19 (04:30 slot):** `_phase4_label(degree, comm_size, n_driven, port_id, s_driven_str, …)` is a pure function — `flag-off control` (+ `ASSERTED`) only at degree 1, otherwise `order readout: S_driven at degree {d} beside the degree-1 step-0 record` with `|S_d − S_1|/|S_1|` printed; `_solve_qualifier` restores step 0's `(assemble + factorise + solve)` on both `solve` prints (and `held` says `assemble + solve on the held factor`); the `FEM_EM_WF7_PORTS` print now says `(unset, default)`. Both non-gating brackets re-dated to measured × [0.5, 2] with log/width/date in comment: degree 1 (0.31–1.23 min, 5.47–21.86 GiB, `-n 8`, `20260913T190102Z_WF-7-step0.log`), degree 2 (2.90–11.59 min, 53.96–215.83 GiB, `-n 16`, `20260919T070008Z_WF-7-step0b.log`). `S_DRIVEN_STEP0_RECORD`, the cell band, the `-n 8` assert condition and every solver call untouched. **Asserted:** five unit assertions green at `-n 2`, 1.1 s (`20260919T095615Z_OPS-52.log:64`) — the recomputed 09-19 relative move **5.5008 % → printed `5.50 %`** (`:51`) and the source-text negative control, ungated `phase 4 flag-off control` **1 at `19bed9a9` → 0 in the tree** (`:60`); plus the `-n 8` flag-off control window as committed, `S_driven(P17)` 0.407423+0.344417j **ASSERTED** equal to the record with both `ANCHOR PASS` lines, cells 507 266 (+5.200e-03 INSIDE), rc 0, **154 s** (`20260919T095635Z_OPS-52.log:10424–10433`); re-dated brackets read INSIDE on their measured point (0.47 min, 10.581 GiB). 2026-09-19 probe-label known-issues entry retired in the closing commit. | ✅ | heavy by record (one 154 s control window at `-n 8`, measured 2026-09-19) |
| `OPS-53` | **`write_setup_figure` refuses a title it cannot draw** — opened by the 2026-09-19 03:00 review from the 2026-09-18 07:30 slot's finding: the helper draws its title with a bare `add_text` (no wrap, no length guard), and `mesh:4`'s 150-character title ran off the canvas ("not drawr") — a false-artefact mode the setup-figure census cannot see. **Done-when (§4):** a `MAX_TITLE_CHARS` constant set by measurement (bracket [126 whole, 150 clipped] ⇒ 130) and a `ValueError` raised before plotting on every rank; a `tests/unit` test asserting 131 raises / 130 does not, an `ast` scan asserting every constant `title=` at the 18 `write_setup_figure(` call sites under `examples/` is inside the limit, and the absent-guard control against the pinned pre-change sha; setup-figure census unchanged (`ok=18 missing=36 broken=0`) and one flagged `mesh:5` re-run digit-identical; the 2026-09-19 known-issues entry retired in the same commit. Legend elision and one-colour-per-class are corpus design, the operator's, and out of scope. Execution text: §9 item 5. **Closed 2026-09-19 (11:07 slot, `-n 1` and `-n 2`, real build, smoke/standard).** `MAX_TITLE_CHARS = 130` and `check_title_length` land in `src/fem_em_solver/post/setup_figure.py` as `write_setup_figure`'s **first statement** — before the `FEM_EM_SETUP_FIGURES` gate, before the collective gather and above every plotting import, so the raise is on every rank and an over-long title cannot hide behind an unflagged run. Message (quoted whole in `20260919T111004Z_OPS-53.log:48`): `write_setup_figure: title is 131 characters, over the MAX_TITLE_CHARS limit of 130. …` — both integers present, asserted. `tests/unit/test_setup_figure_title.py`: **7 passed** at `-n 1` in 1 s (`20260919T110950Z_OPS-53.log:51`) and on **both ranks** at `-n 2` in 2 s (`…111004Z_OPS-53.log:68,71`). Call-site scan (`ast`, not regex): **18** `write_setup_figure(` calls under `examples/` — the expected count — plus the docstring exemplar; 13 constant titles all ≤ 130, and **5 non-constant titles listed, not failed** (`mag:6` `%`-formatted, `mesh:1/2/3` and `ports:15` f-strings — `…111004Z_OPS-53.log:60`), which only the runtime guard can check. Negative control, binary: the 150-character case raises (the 07:30 slot's own title is **not** recorded — `20260918T123728Z_EX-57.log`'s `[setup-figure]` line prints path and regions only — so a **synthetic** 150-char string stands in, and the test says so), and the helper at the pinned pre-change sha `8ef79a1465c08` (a module constant, `git show` into a scratch module under `/logs/`) has **no** `check_title_length` and no `MAX_TITLE_CHARS`. Pre-existing gate (standing rule (c)): census unchanged at `examples=54 ok=18 missing=36 broken=0` (`…111013Z_OPS-53.log:89`) and the flagged `mesh:5` re-run green in 12 s with every `GEO-17` digit identical to `20260918T140647Z_EX-57.log:952–963` and a byte-identical PNG (`…111033Z_OPS-53.log:952–963,976`). Known-issues half (b) retired in the closing commit; half (a), the 14 clipped legends, stays open for §9 items 6–7. | ✅ | standard (unit 1–2 s; census 1 s; one 12 s `mesh:5` window at `-n 2`, measured 2026-09-19) |
| `OPS-54` | **XL / XXL windows run against an immutable checkout** — opened 2026-09-19 (interactive session, from an external code review). The three services bind-mount the live working tree (`docker/docker-compose.yml`), and a window holds its own lock, so a slot that commits to `src/` at 05:00 changes `/workspace/src` underneath ranks launched at 02:00. The commit-side half is fixed (2026-09-19: `xl-run.sh` stages and commits only the window's own paths and refuses a HEAD that has left `main`; the harness keeps the ledger row and the in-flight log under gitignored `/logs/` until the window ends — `test_xl_window_isolation.sh` 23/23, `20260920T004915Z_OPS-XL-ISOLATION.log`). The source-side half is open and is **not yet observed to have bitten**: every window from 09-16 on committed before 03:00, and a window is one Python invocation whose imports resolve at start, so the exposure is late imports and data files. **Sketch:** `xl-run.sh` adds a `git worktree` at the 02:00 HEAD under a gitignored path, the xl / xxl services mount *that* at `/workspace`, results are copied out and the worktree removed; touches compose, `bash_guard.py`'s path assumptions, the durable-capture raw-file paths and `--capture-orphan`. **Done-when (§4):** a scratch-repo test in which a concurrent commit to a tracked source file mid-window leaves the window's view of that file byte-identical to its 02:00 content, plus one real XL window through the new path with its record committed as today. For the weekly to schedule or decline; do not queue until a measured window has actually overlapped a slot, or the weekly decides the risk warrants it. | ⬜ | smoke (scratch-repo test) + one ordinary XL window |
| `OPS-55` | **`evaluate_vector_field_parallel` refuses equal-count point lists whose coordinates differ across ranks** — opened 2026-09-19 (interactive session, from an external code review; the same class as `OPS-40`, in the form its count guard cannot see). `post/evaluation.py` allgathers only `n_points`; each rank then locates and evaluates **its own** copy of the points and rank 0 scatters the hits by positional index, so with equal counts and different coordinates `values[i]` is the field at some other rank's row `i`, reported against rank 0's — all-valid mask, plausible numbers, no error; where two ranks both claim row `i` the last gathered wins. **Latent, not live:** a survey of the ~58 calling files found every current caller passing identical points (the one site building points from rank-local mesh data, `tests/validation/test_birdcage_b1_plus_closed_form.py:729–741`, gathers and broadcasts first); the realistic trigger is a fixed-N rank-local list (unseeded `np.random.rand(N, 3)`, `mesh.geometry.x[:N]`). **Plan.** (1) Validate, do **not** broadcast — broadcasting rank 0's points would hide a caller that still indexes the result against its own local `points`. Fold a digest into the existing collective: `comm.allgather((n_points, hashlib.blake2b(points.tobytes()).digest()))` — no extra round on the valid path. (2) Counts equal but digests differing is known on every rank, so the error path may use further collectives safely: bcast rank 0's points, each rank computes its first differing row and max abs deviation, allgather, and raise `ValueError` on **every** rank with the per-rank figures — the magnitude separates rank-local points (gross) from rank-dependent floating-point ordering (~1e-16); the message says to broadcast the points from rank 0. The count-mismatch message and the shape check are unchanged. (3) Bitwise identity is the documented contract; a caller differing only in the last bit would begin to raise — none found, and that raise is correct. **Done-when (§4):** in `tests/post/test_evaluation_collective_guard.py`, at `-n 1` and `-n 2`: equal counts with coordinates shifted by `0.01 * rank` inside the unit cube raise on every rank (allgathered flags `== [True] * size`), the message naming each rank's first differing row and deviation, and at `-n 1` the same construction does **not** raise (negative control); a pre-change control — the function at the pinned pre-change sha, `git show` into a scratch module under `/logs/` as `OPS-53` did — returns an all-valid mask on that input **and** values deviating from the closed form `(x, 2y, 3z)` at rank 0's points by the amount the shift predicts (quantitative: the defect was silent, and by how much); the existing identical-list test still green at `< 1e-12`. Standing rule (c): a representative `-n 2` subset of existing callers (`tests/post`, `tests/ports`, one SAR test) unchanged, since a false raise on a valid caller is the one way this change can do harm. Out of scope: the shape check raises rank-locally (a bad shape on one rank would hang the rest) — reachable only from already-broken caller code. For a review to queue into §9; not queued by this session. **Closed 2026-09-21 (11:00 UTC slot, §9 item 27):** digest `hashlib.blake2b(points.tobytes(), digest_size=16)` folded into the existing `allgather`; mismatch path bcasts rank 0's points, allgathers (first differing row, max abs deviation) and raises on every rank. Measured at `-n 2` (`20260921T111743Z_OPS-55.log`, 6 passed, 2 s): flags `[True, True]`, message `rank 0: first differing row -1, max abs deviation 0.000e+00; rank 1: first differing row 0, max abs deviation 1.000e-02`; `-n 1` negative control flags `[False]` (`20260921T111745Z_OPS-55-n1.log`, 6 passed, 2 s). Pre-change control, blob `git show 14a0d71:src/fem_em_solver/post/evaluation.py` (= this commit's `^`) into `/workspace/logs/`: all-valid mask, per-row deviation from `(x, 2y, 3z)` at rank 0's points `[1.1e-16, 3.000000e-02 ×7]` — exactly the predicted 0.03·rank for rows rank 1 located, silently (`20260921T111730Z_OPS-55-prechange.log:50`, asserted in-test to 1e-12). Rule (c) caller subset at `-n 2`: complex `tests/post tests/ports tests/validation/test_lossy_sphere_sar.py` 54 passed / 2 failed / 1 skipped, 159 s — the two failures are exactly known-issues entry 3 (placeholder fakes, no call into this function), the skip is the env-gated pre-change test (`20260921T111802Z_OPS-55-callers-complex.log:1203`); real `tests/post` 14 passed / 25 skipped, 3 s (`20260921T112042Z_OPS-55-callers-real.log`). No caller was passing rank-local points. (`20260921T111714Z_OPS-55-prechange.log` is a docker-socket denial from a `date &&`-prefixed call, no run.) | ✅ | smoke (unit, `-n 1` / `-n 2`) + standard (caller subset at `-n 2`) |
| `OPS-56` | **Sweep-planner endpoint inclusion must not depend on the carrier frequency** — opened 2026-09-19 (interactive session, from an external code review; reproduced in plain numpy with the function's own logic). `ports/sweep.py::_uniform_frequency_grid` decides whether to append the requested endpoint with a default `np.isclose`, whose `rtol = 1e-5` scales with the absolute frequency: at 128 MHz anything within ~1.3 kHz of `stop_hz` (640 Hz at 64 MHz) counts as already present. Reproduced: `(127.7000e6, 127.7009e6, 500)` ends at 127.7005 MHz; `(127.7000e6, 127.7012e6, 1e3)` drops the endpoint; `(64.0000e6, 64.0005e6, 1e3)` returns a **single point**. kHz steps around a resonance are what `refined_step_hz` exists for and what birdcage tuning will ask of it; `tests/ports/test_frequency_sweep_planner.py` uses MHz spacing only, so nothing sees it. Two neighbours in the same function: non-finite inputs fail by accident (`nan` → `ValueError: cannot convert float NaN to integer`, `inf` → `OverflowError`), and `plan_frequency_sweep` de-duplicates the merged coarse+refined grid with `np.unique`, which merges only bitwise-equal floats — two points 1e-8 Hz apart both survive, and each is a full field solve. **Plan.** Validate start / stop / step finite (intended `ValueError`s). Decide inclusion from the grid's own construction: `n = floor(span/step + 1e-9)`; the endpoint is on-grid iff `abs(span − n·step) <= 1e-9·step`, in which case the last point is set to `stop_hz` **exactly**, otherwise `stop_hz` is appended. De-duplicate the merged grid with the same step-relative tolerance (the finest step in play) instead of `np.unique`. Tolerances are relative to the **step**, never to the carrier. **Done-when (§4):** unit tests asserting exact grids for the three reproduced cases (endpoint present, length as computed by hand), a nondivisible span, the float-noise case `(0.1, 0.3, 0.1)` → 3 points, an on-grid endpoint bitwise equal to `stop_hz`, a coarse/refined near-duplicate merging to one point, and the intended `ValueError` for each non-finite input; a pre-change control showing the three reproduced cases fail on the pinned pre-change sha; the two existing planner tests green unchanged. Pure numpy — no solve. For a review to queue into §9. **Closed 2026-09-21 (§9 item 28, implementer):** finite checks + step-relative inclusion (`n = floor(span/step + 1e-9)`, on-grid iff `|span − n·step| ≤ 1e-9·step` ⇒ last point := `stop_hz` exactly, else appended) + `_merge_frequency_grids` de-duplicating at `1e-9 ×` the finest step in play. Pre-change control on the `c1d167d` blob (in `/logs/`): 3/3 reproduced cases fail — ends 127.7005 MHz, ends 127.7010 MHz, single point `(64.0e6,)`. Committed module `-n 1`: 19 passed, 2 s — three cases hit their hand grids with `stop_hz` bitwise last; `(0, 10, 3)` → `(0, 3, 6, 9, 10)`; `(0.1, 0.3, 0.1)` → 3 points ending bitwise 0.3; 63–65 MHz @ 0.1 MHz → 21 points ending bitwise 65e6; coarse/refined pair 6e-8 Hz apart merges (7 points, not 8); nan/±inf on each of start/stop/step raise the intended `ValueError`; the three pre-existing planner tests green **unchanged** (no caller of `plan_frequency_sweep` outside that test file, so no sweep record depended on the old rounding). Logs `20260921T112323Z_OPS-56.log` (control), `20260921T112330Z_OPS-56.log` (green). **Audit 2026-09-23 03:00 review: `auditor` DEMOTE(2) — overruled, ✅ stands.** The auditor could not grep four of the grids above out of the green log (the nondivisible span, the 0.3 float-noise case, the 21-point MHz grid, the 7-point merge) because the window printed nothing for them. They are the operands of **exact-equality asserts** — `tests/ports/test_frequency_sweep_planner.py:101` (`== (0.0, 3.0, 6.0, 9.0, 10.0)`), `:107–109`, `:114–115`, `:132–135` — whose `PASSED` lines are `20260921T112330Z_OPS-56.log:48–51`. A passing exact equality is log evidence of its value. §4's elements (harness log, agent-executed, quantitative assertion, elapsed) are all met; the digits are cited to source + PASSED line, not to a print. | ✅ | smoke |
| `OPS-57` | **S ↔ Z conversions: let the solve report singularity; one impedance-to-S implementation** — opened 2026-09-19 (interactive session, from an external code review). `ports/circuit.py` tests singularity with `abs(np.linalg.det(m)) == 0.0` at **three** sites (`terminate`'s `I − S_bb Γ` at `:138`, `s_to_z` at `:167`, `z_to_s` at `:185`). A determinant is scale- and dimension-dependent — `1e-21 · I₁₆` has `det == 0.0` exactly and condition number 1 — so the test can reject a perfectly conditioned matrix. **Honest size:** unreachable on this project's matrices (`I − S` has O(1) entries, `Z + z0 I` a diagonal ≥ z0), so this is a correctness-of-intent fix, not a live defect. The real weakness is the opposite one: `== 0.0` catches only *exactly* singular matrices, which `np.linalg.solve` already refuses (`LinAlgError: Singular matrix`), so the line is a second factorisation that adds a message and no protection. Separately, `ports/sparameters.py::sparameters_from_impedance` is the same formula as `z_to_s` with an explicit `np.linalg.inv`, a non-finite check `z_to_s` lacks, and a looser `z0` check. **Plan.** (1) Drop the three determinant tests; wrap each solve in `try / except np.linalg.LinAlgError` and raise `ValueError` with the **existing** message text. (2) Add the non-finite input check to `s_to_z` / `z_to_s`. (3) `sparameters_from_impedance` keeps its signature and docstring and delegates to `z_to_s` (check the import direction first — no cycle). **No conditioning threshold:** a near-open-circuit S legitimately has a huge Z, and a cut-off would be an invented tolerance. **Done-when (§4):** unit tests — round trip `z_to_s(s_to_z(S))` to ≤ 1e-12 on a 16-port matrix scaled so its determinant underflows (the pre-change control: the pinned pre-change sha raises on it); an exactly singular `I − S` still raises `ValueError` with the same message at all three sites; `sparameters_from_impedance` and `z_to_s` agree to ≤ 1e-14 on a random passive Z. Standing rule (c): `inv` → `solve` moves S in the last bits, so `tests/ports` and the PORT validation gates that consume `sparameters_from_impedance` are re-run at `-n 2` and must be green **with no tolerance touched** — a gate that fails on a last-bit change is a finding about that gate, reported, not loosened. For a review to queue into §9. | ✅ **2026-09-21 (11:00 UTC slot, §9 item 29)** — the three `det == 0.0` tests replaced by `try/except np.linalg.LinAlgError` → `ValueError` with the unchanged messages; `s_to_z`/`z_to_s` refuse non-finite input; `sparameters_from_impedance` keeps its signature/validation and delegates to `z_to_s` (circuit.py imports only numpy — no cycle). `tests/unit/test_ops57_sz_conversions.py` (smoke, `-n 2`, 22 passed with the `PORT-20`/`PORT-15` unit modules, 3 s, `20260921T112537Z_OPS-57.log`): 16-port round trip at z0 = 1e-21 Ω, **max\|Δ\| = 1.877e-16** ≤ 1e-12 with cond(Z + z0 I) = 3.944 and \|det\| = 0 — the pre-change control (the removed guard fires on that matrix) asserted; exactly singular matrices raise the same message at all three sites; `sparameters_from_impedance` vs `z_to_s` **0.000e+00** ≤ 1e-14. Rule (c), complex, `-n 2`, no tolerance touched: `test_port_package_sparameters.py` 18 passed / 194 s (`20260921T112548Z_OPS-57.log`; the one red is `tests/environment/test_scikit_rf_version.py`, the known-issues `OPS-60` deliberate entry) — `‖S − z_to_s(Z)‖/‖S‖ = 0`, σ_max 0.8613568944353246 vs record (miss 4.353e-10, band 1e-6), symmetry 3.112130867e-05 (miss 1.867e-11, band 5e-7); `PORT-9` gate `test_port_birdcage_four_port.py` 5 passed / 37 s (`20260921T112912Z_OPS-57.log`) — ‖S − Sᵀ‖/‖S‖ 1.078765433e-14 (was 1.044255156e-14: the predicted last-bit move), ‖Z − Zᵀ‖/‖Z‖ 8.814400604e-05 and σ_max 0.999992805 and class spreads 0.0553/0.0353/0.0214 % digit-identical. `PORT-20` step 2's 1e-12 residual is now a same-implementation check; its docstring names the unit closed form as the anchor. | smoke (unit) + standard (PORT gate re-run at `-n 2`) |
| `OPS-58` | **Private-leak check: commit messages, fail-closed on inspection errors, "skipped" is not "clean", and a positive control** — opened 2026-09-19 (interactive session, from an external code review, which framed these correctly as limits of the mechanism, **not evidence of a leak**). (a) CLAUDE.md forbids AED figures in commit messages, but `check_private_leak.py` runs as `pre-commit`, which never sees the message. (b) `staged_additions()` and `tracked_lines()` swallow every exception and yield nothing, so a failing `git diff` reads as a clean pass; `collect()` does the same for an unreadable secret file. (`published_digits()` failing is the safe direction — nothing subtracted — and stays.) (c) With no raw exports present the script returns 0 **silently**, so the CI `private-leak` job, which can never hold the exports, reads as a pass while checking nothing. (d) The checker has no test, and its own docstring records that it once passed its planted figure. **Plan.** `--message-file <path>` mode (comment lines stripped), installed by `install_git_hooks.sh` as a `commit-msg` hook beside `pre-commit`; `--audit` additionally scans `git log --format=%B`. Inspection errors propagate → exit 2 with `could not inspect: …`. No reference data → print `SKIPPED: no reference data on this machine; nothing was checked` (exit 0), distinct from `clean: …`. `ROOT` / secret globs overridable so a script-style test beside `test_tier_guard.py` can build a scratch git repo with **synthetic** secrets. **Done-when (§4):** that test asserts exit codes exactly — planted figure staged → 1; planted figure in the message → 1; a truncated spelling of it → 1; clean → 0 with `clean:`; no reference data → 0 with `SKIPPED`; broken git → 2 — plus the pre-change control (the pinned pre-change script passes the message plant and the broken-git case); the CI `private-leak` job runs the same test, which becomes the one part of that job that tests something on a runner; `--audit` on this clone still reports clean (the count of figures printed, never a figure). **Operator step after it lands:** re-run `scripts/testing/install_git_hooks.sh` once — `.git/hooks` is untracked and not agent-writable (dashboard Waiting-on-you). **What stays unfixed, deliberately:** matching needs ≥ 8 significant digits; a figure rounded to 3–4 digits in prose, or transformed into a ratio or percentage, is invisible to any digit matcher that is not also drowning in false positives. The hook is a copy-paste net; the written rule remains the control. **Closed 2026-09-22** — all eight exit-code cases plus the pre-change controls assert exactly, 24/24 (`20260922T040113Z_OPS-58.log`, 3 s, smoke host-side). `--audit` on this clone reported one match (2026-09-21); the operator ruled it a **false positive** — a shared geometric *input* the repo already publishes in plain text in its own `SPEC.md`, echoed back by the export, not an AED result — so no history rewrite. A **narrow shared-input allowlist** now suppresses exactly that site: an entry keys on (tracked path, JSON key present on the line, exact value) and carries its `reason` plus the tracked public source that publishes it; the value is **computed from its published closed form**, never written out, so an AED output cannot be entered at all. Suppression is never silent — the count and the site are printed on every run. Negative controls gate it: a synthetic AED *output* beside the allowlisted site is still flagged, and the same value in a different file, or under a different key in the same file, is still flagged. `--audit` now `clean:` with `1 shared-input match suppressed` (`20260922T040116Z_OPS-58-audit.log`, 8 s). **Operator step still open:** re-run `scripts/testing/install_git_hooks.sh` once. **Audit 2026-09-23 03:00 review: PASS** (24/24 at `20260922T040113Z_OPS-58.log:92`, `clean:` + suppression count at `…040116Z_OPS-58-audit.log:34`, both reds on ancestors). Tier note: both closing windows were wrapped in the standard `timeout -k 30 180` while this row says smoke; measured 3 s / 8 s fit either — the tier word stays smoke. | ✅ | smoke (host-side, no container) |
| `OPS-59` | **Two count pins that the `EX-57` figure task breaks once per figure: make them identities** — opened by the 2026-09-20 03:00 review (weekly flag 5 of 2026-09-19, plus this review's `OPS-53` audit). (a) `tests/unit/test_doc_reference_exit_codes.py::test_the_in_tree_exemption_cannot_silently_widen` is red on `main` (known-issues 2026-09-19): `COMMITTED_EXAMPLE_ARTIFACTS` was never widened for the setup PNGs committed since 2026-09-13. (b) `tests/unit/test_setup_figure_title.py:43` pins `EXPECTED_EXAMPLE_CALL_SITES = 18`; `main` carries 20 call sites since `6f75424` / `32f28d8` (known-issues 2026-09-20, red by inspection, not yet executed). | ✅ **2026-09-21 06:00 slot (§9 item 25): (a) closed on the review's ruling.** `examples/ansys_benchmarks/ans6_copper_birdcage_four_port_10_64_128MHz/metrics.json` declared in `LISTED_EXAMPLE_ARTIFACTS` (dated provenance comment, nothing else changed); both modules green at `-n 2`, real build, smoke — **27 passed, 8.2 s, 10 s wall** (`20260921T111239Z_OPS-59.log:580`); identity **`pinned=28 (listed=6 by_rule=22) checker=28 git_ls_files=28`**, extras none (`:354,383`; by_rule 21 → 22 because one figure landed since); negative controls green in the same window (synthetic non-setup PNG and orphan `*_setup.png` refused, `:418–420`); (b)'s identity `call_sites=22 committed_setup_pngs=22 census_ok=22` (`:570`). 2026-09-19 known-issues entry retired. (A first window, `20260921T111210Z_OPS-59.log`, ran the doc-reference module alone — 20 passed — and is kept; the 27 is the two-module window of record.) Prior state: 🟡 **(b) closed, (a) stopped on its own pre-registered negative result — 2026-09-20 07:30 slot, third item.** Both halves were built and executed at `-n 2`, real build, smoke; the counts are one higher than this row's text because the same slot's item-14 commit `75082a0` (`ANS-6` runnable half) added one example script, one `write_setup_figure` call site and one `*_setup.png` (census `examples=54 ok=20` → `55 / 21`, `20260920T125043Z_ANS-6-postcensus-figures.log`). **Pre-change red recorded first** (`20260920T130047Z_OPS-59-prechange.log`, 2 failed / 24 passed, 7.3 s, Status 1, 9 s wall): the call-site pin reads `assert 21 == 18` (`:763–764`) — the expected shape, one above the item's "20 != 18" — and the artifact pin shows **22 extras** (`:736–758`). **(b) ✅:** the literal is gone; the test now computes and asserts *call sites == committed `*_setup.png` == census `ok`*, measured **`call_sites=21 committed_setup_pngs=21 census_ok=21`** (`20260920T130232Z_OPS-59-postchange.log:576`), green, and the title-length scan is untouched. **(a) 🟡:** the pin is now `LISTED_EXAMPLE_ARTIFACTS` (5, declared by hand) **plus** `_setup_figures_admitted_by_rule()` (21, derived from the census module's own script↔figure pairing) — `pinned=26 (listed=5 by_rule=21) checker=27 git_ls_files=27` (`…postchange.log:358`) — so extras fell **22 → 1**, and the survivor is **`examples/ansys_benchmarks/ans6_…/metrics.json`** (`…postchange.log:386`), a **non-setup** artifact committed undeclared by `75082a0` two hours earlier. That is this item's pre-registered negative result ("extras include a non-setup file ⇒ name it, leave it red, stop — that one is a real unpinned artifact"), so the implementer did **not** add it to the list and `test_the_in_tree_exemption_cannot_silently_widen` stays red (1 failed / 26 passed, 8.2 s). Both asserted negative controls are green in the same window: the new `test_the_setup_figure_rule_admits_nothing_but_setup_figures` shows `by_rule=21` admits neither `examples/ports/figures/not_a_setup.png` nor the orphan `examples/ports/figures/zz_nonexistent_setup.png`, and listing either turns the identity red (`…postchange.log:420`); the `OPS-44` drop-any-member control still passes over all 26. **Unblocks with** one line — `ans6_…/metrics.json` declared in `LISTED_EXAMPLE_ARTIFACTS` under the `ANS-1` rule (the precedent is `OPS-44`'s late declaration of the `ANS-2`/`ANS-4` `metrics.json`) — plus one ≈ 8 s window; a review's call, not an implementer's. **Done-when (§4):** (a) the artifact pin admits exactly the files matching `examples/*/figures/*_setup.png` that have a same-stem example script, by rule rather than by list, and nothing else — asserted negative control: a non-setup PNG and an orphan `*_setup.png` injected into the listed set both still fail the pin; count identity extras-before = committed setup PNGs, extras-after = 0. (b) the literal 18 replaced by the three-count identity *call sites == committed `*_setup.png` == census `ok`*, the unmodified module's red recorded first. Both modules green at `-n 2` through the harness, elapsed recorded, both known-issues entries retired in the same commit, the `EX-57` per-item list amended. No `src/`. §9 item 16. **Ruled 2026-09-21 03:00 review:** (a)'s one surviving extra, `examples/ansys_benchmarks/ans6_copper_birdcage_four_port_10_64_128MHz/metrics.json` (`75082a0`), **is declared** in `LISTED_EXAMPLE_ARTIFACTS` under the `ANS-1` rule (an `ans:` case commits its own `metrics.json`; `OPS-44` is the late-declaration precedent) — §9 item 25, one ≈ 8 s window, closes the chunk. Standing from that review: an `ans:` runnable-half item declares its `metrics.json` in the commit that adds it. | smoke |
| `OPS-60` | **`scikit-rf` in the image, pinned** — the circuit engine `PORT-23` gates against the raw layer (operator directive 2026-09-20: use a vetted circuit solver, netlist prepared in our code) | ✅ **2026-09-23 (04:30 slot, §9 item 33): green on the ordinary `fem-em-solver` service** — `[OPS-60] skrf=2.1.0 file=/dolfinx-env/lib/python3.12/site-packages/skrf/__init__.py` PASSED on both ranks (`20260923T093017Z_OPS-60.log:76–77`, `:153–154`), whole `tests/environment` 12 passed per rank (`:146`, `:223`), dolfinx `0.11.0.post0` complex128 (`:68`), Status 0, 39 s, `-n 2`; no recreate was needed. Negative control on record: `ModuleNotFoundError` on the pre-rebuild image (`20260921T093041Z_OPS-60.log:48`). Known-issues 2026-09-21 DELIBERATE and 2026-09-23 NOT-A-RED entries retired; `PORT-23` unblocked. **Audit 2026-09-25 (03:00 review): auditor DEMOTE(8) on the tier word, overruled — ✅ stands.** Every §4 element is present and traced 8/8 (`20260923T093017Z_OPS-60.log:3,12,76,146,153,223,226–227`; red baseline on `9eb1e39`, the pin commit's parent, `20260921T093041Z_OPS-60.log:3,48,55`; the assert `tests/environment/test_scikit_rf_version.py:40` untouched since `f3fcdeb`). Exact version equality is §4-quantitative on the `OPS-18` / `OPS-25` precedent (a documented reference value with a discriminating control). The defect is the label: a "smoke" row whose closing window ran the whole `tests/environment` suite under `timeout -k 30 60` for 39 s — the window the 09-23 review's §9 item 33 wrote verbatim. Tier column re-labelled **standard**, the precedent of the 09-23 `OPS-57` / `OPS-58` tier notes. History: **2026-09-21 (04:30 slot): Dockerfile pin `scikit-rf==2.1.0` (newest on PyPI, read in-container by `pip index versions`, `20260921T093027Z_OPS-60-version-probe.log:34`) and the test landed; the negative control fails as predicted on the current image — `ModuleNotFoundError: No module named 'skrf'` (`20260921T093041Z_OPS-60.log:48`, 1 s, `-n 1`). ✅ owed to the operator's rebuild: the same test green on the rebuilt image (known-issues 2026-09-21). **2026-09-23: the operator rebuilt the image at ~21:10 local 2026-09-22 and reports `import skrf` → 2.1.0 host-side, but two attempts to run the gate (interactive session 02:13 UTC, `20260923T021343Z_OPS-60.log`; subagent immediately after) both died on `permission denied ... unix:///var/run/docker.sock` before entering the container — neither is a test result (known-issues 2026-09-23). The chunk stays 🟡 pending one harness-logged run from a session with docker-socket access; nothing in the repo needs to change for it.** **2026-09-23 03:00 review: the rebuilt image carries the pin** — the 02:00 `xl` window (same `fem-em-solver:latest` image, service recreated before the window) ran this test green on every rank, `[OPS-60] skrf=2.1.0` (`20260923T070007Z_ANS-4-step3f.log:271–283`), dolfinx `0.11.0.post0` unchanged (`:287`), congruent-cut cell records reproduced exactly (no mesher drift from the rebuild). ✅ is left to §9 item 33, which runs the test on the ordinary `fem-em-solver` service every slot uses — a container not recreated after the build still runs the old image. Step 1: add `scikit-rf==<latest release at execution, pinned>` to `docker/Dockerfile`'s pip block beside `pyvista`, and a `tests/environment/test_scikit_rf_version.py` that imports `skrf`, prints `skrf.__version__` and asserts it equals the pin (the `OPS-25` pattern). **The image rebuild is the operator's** (`docker compose build`, outside the sandbox); the slot edits the Dockerfile and the test, runs the test to show it *fails* on the current image (import error = the negative control), journals, and marks `PORT-23` PENDING PREREQUISITE → READY only after the operator's rebuilt image passes it. No other dependency moves; version-tagged constants are unaffected (nothing in `src/` imports `skrf`). | standard (re-labelled 2026-09-25 review; was smoke — the closing window measured 39 s) |
| `OPS-61` | **Palace as a second independent reference** — AWS's open-source curl-curl FEM (Nédélec, lumped ports, S-parameters, AMR, hypre AMS) run on the `ANS-4` fixture beside HFSS (operator directive 2026-09-20: keep our solver as the thing being validated, with two judges that share no code with it or with each other; **for the 2026-09-26 weekly to commission**, §5.4) | ⬜ **Why:** `ANS-6` isolated a ≈ 3 % self-class offset on the four-port birdcage to the lumped-port model / our degree-1 mesh (it is identical on a PEC coil and a copper coil). HFSS is one reference; a second general-purpose code with an *independently written* lumped-port model says whether the offset is ours or a port-model convention HFSS shares with nobody. Unlike AED numbers, **Palace results are publishable** — open source, no licence clause — so this reference can sit in tracked `COMPARISON.md` columns and in gates, which the AED columns never can. **Step 0 — the service (ops, cost probe first):** a `fem-em-palace` compose service from Palace's official container image if one is published, else a build stage (Spack or CMake against MFEM/hypre) pinned to a release; smoke: Palace's own bundled example runs to completion in the container; `-n` ≤ 12 ranks; the price of the smoke printed. **Step 1 — the `ANS-4` fixture:** export the gated four-leg birdcage mesh (`birdcage_port_domain`, the ×1 rung) to a format Palace reads (Gmsh `.msh` via the generator's own gmsh session; element tags carried), write the Palace JSON config — PEC box faces, phantom σ = 0.5 / εᵣ = 78, coil σ = 800 solved inside (the `ANS-4` fixture) *and* a PEC-coil variant (the `ANS-6` PEC column), four lumped ports on the gap sheets at 50 Ω, driven at 10 / 64 / 128 MHz — and run it under `run_and_log.sh` at the tier the probe sets. **Readout:** the 4×4 S per frequency; the three C4 classes against ours (tracked, public) and against the private AED column (`docs/private/`); Palace's own reciprocity / passivity / C4-spread identities beside our gate bands. **Decision rule, pre-registered:** (a) Palace agrees with HFSS on the self class and both differ from us by ≈ 3 % ⇒ the offset is ours (`PORT-21`'s target, now with two references); (b) Palace agrees with *us* and differs from HFSS ⇒ the offset is HFSS's port convention, and the `ANS-4` self-class verdict is re-read; (c) Palace agrees with neither ⇒ the lumped-port model is convention-sensitive at this fixture and the case moves to a wave-port or a de-embedded comparison. **Step 2 (at closure):** Palace on the `ANS-6` copper column (its surface-impedance boundary) and, later, the F-human rung at degree 2 as a price and S cross-check. **Not a migration:** nothing in `src/` changes; Palace is a reference, like AED, never the solver. | heavy (step 0 cost probe first; step 1 predicted minutes on the 116 k-cell rung) |
| `OPS-62` | **The `ANS-4` ladder's refinement guard counts unknowns, not cells** — opened and executed 2026-09-22 (interactive session, operator-instructed, **out of band**: it was not queued through §9, and §9 was deliberately left untouched). **Defect:** `tests/validation/test_ans4_resolution_ladder.py::test_every_finer_rung_actually_refines` asserted `finer["cells"] > coarser["cells"]` between consecutive rungs. That is the wrong invariant for step 2d's `h:degree` ladder, which refines in **h and p**: a p-rung holds the mesh fixed on purpose. **Evidence:** the 2026-09-22 XL window (`20260922T070007Z_ANS-4-step3e.log`, Status 1) ran the pre-registered `FEM_EM_ANS4_STEP2_RUNGSPEC="0.015:1 0.015:2 0.0075:2 0.005:2"` at 64 MHz; rungs 1 and 2 are the same mesh at degree 1 then degree 2, so the guard read `resolution 0.015 gave 116085 cells, not more than 0.015's 116085` (`:8802–8805, 8812`) while the discretisation actually went ~139 302 → ~742 944 unknowns (`:2452, 4542`). All four rungs completed and produced Z/S; the `PORT-11` gates, the record-rung check and the readout all passed — one spurious red on an otherwise usable window. **Internal inconsistency, not a judgement call:** the same file's stop rule is already stated in unknowns (`STOP_ABOVE_DOFS`, "cells mean different things at different orders"), through `_estimated_dofs(cells, degree)`; only the guard was never updated when the ladder gained p-rungs. **Fix:** `_refinement_measure(rung)` = `_estimated_dofs(rung["cells"], rung["degree"])` (the rung dicts have carried `degree` since `_four_port_rung` gained it) and a pure `_check_refines(rungs)` returning the offending consecutive pairs; the guard asserts that list is empty. **Strictly stronger, not loosened** — no tolerance, no `>=`, no equal-cells exemption: an inert `h` keyword still gives identical meshes at fixed degree ⇒ identical unknowns ⇒ still caught, **and** an inert or backwards `degree` knob, which a cell count cannot see, is caught too. Cells stay in the printed `[ANS-4 step2] refinement:` line (now cells *and* unknowns, rank 0 only); the failure message names the rung pair, both degrees and both unknown counts. **Controls (§4, smoke, `-n 2`, complex, `20260922T165511Z_OPS-62.log`, Status 0, 7 s):** `test_refinement_check_controls`, 1 passed in 1.3 s on **both** ranks, on synthetic rung dicts, no solve — four identical rungs ⇒ 3 failures caught; a p-rung (116 085 cells, degree 1 → 2) ⇒ clean, with the measure asserted at exactly 139 302 → 742 944; an h-rung ⇒ clean; **the real 3e ladder shape with that window's measured cell counts (116 085 / 116 085 / 281 728 / 592 744) ⇒ clean**, i.e. the fix would have let that window through; a degree drop at fixed h ⇒ caught; equal unknowns across a pair (1 600×1.2 == 300×6.4) ⇒ caught; and the strength case — cells 100 000 → 200 000 with degree 2 → 1, which the **old** cell guard passed and the new one catches. The module still collects: 6 tests in 2.5 s. Nothing else touched — no ladder data, no `_estimated_dofs`, no `STOP_ABOVE_DOFS`, no `PORT-11` band, no other test. **Whether `ANS-4` step 3e is re-run is the next 03:00 review's call** — this chunk did not touch `xl-queue.d/`, `xl-pending.md` or `xl-ledger.md`, and implementers never commission a window. **Audit 2026-09-23 03:00 review: PASS.** Correction from the same review's `log-pathologist` reading: the 3e window had **two** reds, not one — the second is the deliberate pre-rebuild `OPS-60` `skrf` red (`20260922T070007Z_ANS-4-step3e.log:8892–8895`, `:8969–8970`), not physics either; ruled **not re-run**, and 3f (09-23) ran 18 / 18 green under this guard (`20260923T070007Z_ANS-4-step3f.log:4923–4924`). | ✅ | smoke (pure-function controls, `-n 2`, 7 s) |
| `OPS-63` | **The `ans:2` example says ASSERTED only where it asserts, and carries no AED figure in tracked text** — opened by the 2026-09-25 03:00 review from the `log-pathologist` reading of the `ANS-2` step 4 `xl` window (known-issues 2026-09-25) | ✅ **DONE 2026-09-25 (06:00 slot, §9 item 41).** Example script + one guide sentence only; no shared builder, no `src/`. The example captures `build_four_port_sweep`'s return dict by wrapping the same function in the mass-averaged builder's module namespace (same call, same arguments; the builder discards the sweep, so this is the only route that edits no builder) and asserts, bands imported: `PORT-9` (i) ‖S − Sᵀ‖/‖S‖ **7.489e-15** ≤ `RECIPROCITY_BAND` 1e-3; (ii) σ_max **0.999993824**, max column power sum **0.793794824** ≤ 1 + `PASSIVITY_SIGMA_TOLERANCE`; (iii′) Z class spreads self **0.0551** / adjacent **0.0364** / opposite **0.0211 %** ≤ `ADJACENT_SPREAD_BAND` 0.5 %; `MAT-4` containment r0 + a_10g **28.3650 mm** < `PHANTOM_RADIUS` 30 mm and max |z_c| + a_10g 13.3650 mm < ½`PHANTOM_HEIGHT` 40 mm; the 10 g mis-paired control's sign **85.2523 / 85.2921 / 85.2750 / 85.2857 %** > `C4_COVARIANCE_BAND` 5 %. A `[ANS-2] LABEL KEY` line names which ASSERTED labels are the builders' pytest modules' and which the example asserts. The AED figure is replaced by a pointer to the private adjudication file, no number; the comparison template is an `rf"""` string (output byte-identical: the one former `\\|` is now written `\|`), and the example's own `SyntaxWarning` is gone from the log. **(i)** knob route `FEM_EM_ANS2_PHANTOM_RESOLUTION=0.0025`, `-n 4`, complex: `20260925T110348Z_OPS-63.log`, **195 s**, example exit 0, ALL ANCHORS GREEN, 199 920 / 58 866 cells (the window's Status 1 is only the chained comparison looking for `metrics_h0.0025.json` in `paraview_output/`; it is written beside `metrics.json`). Leaf identity against the tracked `metrics.json` at the imported `EXACT_IDENTITY_RTOL`: 145 leaves, 123 numeric primary, **worst 9.646e-11** at `.pointwise.0.sar_w_per_kg[1]` ≤ 1e-10, residuals ≤ 1e-10, derived C4 misses 4.95e-8 relative (reported, gated at the imported band) — PASS, `20260925T110725Z_OPS-63-leaf-identity.log` (Status 0; `…110714Z…` is the same PASS followed by an in-container `git status` that died on `dubious ownership`, exit 128). No number moved. Heavy tier (≈ 3.3 min). **(ii)** phrase census 2 before (review) → **0 matches** after (`git grep -c` exit 1). **(iii)** `OPS-58` `--audit` on the pre-change tree: **`clean:`**, 2061 figures compared, 1 shared-input match suppressed (`20260925T110045Z_OPS-63-audit-before.log:34`, 10 s); after: `clean:` (`20260925T110729Z_OPS-63-audit-after.log`). **Finding: the checker did not flag the AED figure** — expected from its own stated limit (≥ 8 significant digits; a figure rounded in prose is invisible to a digit matcher, §7 `OPS-58` "what stays unfixed"); checker not changed here. Observed, out of scope: the shared builder `tests/validation/test_port_birdcage_four_port.py:1` emits its own `SyntaxWarning: invalid escape sequence '\*'` (`20260925T110348Z_OPS-63.log:34`). **Defects (measured on `20260925T070008Z_ANS-2-step4.log`):** (1) three quantities print "ASSERTED" that the example never asserts — ball containment (`:2061`), the 10 g mis-paired control's sign (`:2073–2076`) and the `PORT-9` reciprocity / passivity / class-spread bands (`:2057`). The labels come from shared builders (`tests/validation/test_birdcage_sar_mass_averaged.py`, `tests/validation/test_port_birdcage_four_port.py`) whose asserts live in pytest functions the example does not call; the arithmetic holds in each case. The 1 g pairs print "(PRINTED NOT GATED)" at `:2073–2076` and "ASSERTED" at `:2100–2103` for the same numbers. (2) The script's `_spread` docstring (`02_birdcage_coil_driven_sar_10MHz.py:394`) and its step-4 print (`:620`) quote AED's own figure for the driven-point C4 spread. That is an AED value, not a relative agreement level, so the hard rule (CLAUDE.md; operator ruling 2026-09-24) keeps it out of tracked files. It entered with `a2e4a04` (2026-09-19) and is now in one tracked log (`:2113`). (3) An invalid-escape `SyntaxWarning` at script `:572`. **Change:** the example asserts each quantity it labels ASSERTED, importing every band from the gate modules (nothing restated, no shared builder edited, so rule (a) does not arise); it prints one line naming which labels are the builders' and which lines it asserts itself; the AED figure is replaced by a pointer to the private adjudication file with no number; `:572` becomes a raw string. **Done-when:** (i) the knob route at the tracked rung (`FEM_EM_ANS2_PHANTOM_RESOLUTION=0.0025`, `-n 4`, the route step 4a proved digit-identical to the unset run) runs green with the new asserts, and its `metrics_h0.0025.json` reproduces the tracked `metrics.json` on every primary leaf within the imported `EXACT_IDENTITY_RTOL` (step 4a measured worst 8.19e-11) — no number moved; (ii) the phrase census `git grep -c -e "on its own mesh" -e "against HFSS" -- examples/ansys_benchmarks/ans2_birdcage_coil_driven_sar_10MHz/02_birdcage_coil_driven_sar_10MHz.py` reads 2 before the change (measured by the 2026-09-25 review) and nothing after (asserted, binary — the phrases, not the number; `ports:2` carries the first phrase in an unrelated sense, hence the one-file scope); (iii) the `OPS-58` checker's `--audit` runs before and after, and its reading of the pre-change tree is recorded either way. If it did not flag the figure, that miss goes into this row as a finding and the checker is not changed here. **Not in scope:** the tracked logs that already carry the figure (the 09-25 `xl` log and the 4a / probe logs), which are the operator's call on history; the shared builders' print labels. | heavy (the example at the 0.0025 rung ≈ 200 s at `-n 4`) + smoke |
| `ARCH-1` | **The MRI-safety layer becomes solver-agnostic** — SAR averaging, B₁⁺ maps, loss partition, the thermal solve, the benchmark cases and their gates take fields and S-parameters from *any* field solver (ours, Palace's output, an HFSS field export) through one interface; the FEniCSx engine stays the in-house backend and the multiphysics home (operator directive 2026-09-20). **EMBARGOED: not before the weekly of 2026-10-17** — four weeks out by the operator's instruction, so that `PORT-21`, `OPS-61` (Palace) and the first human-scale physics land first and the interface is designed against two real backends, not one | ⬜ **Not queueable by a daily review** (outside §9 rule (4): it is architecture, not an enumerated chain step) **and not to be scheduled by the weeklies of 09-26, 10-03 or 10-10** — those may only annotate this row with what they learn. **Why:** the project's replaceable part is the curl-curl solve; its hard-to-replace parts are the verification culture, the MRI-safety layer and the multiphysics reach. Today the safety layer is written against DolfinX function spaces, so it can only judge our own fields; decoupled, it is an evidence toolkit that works with the field solver a user already has — the wider audience arrives through "works with Palace / HFSS output", not through replacing the engine — and it is also what lets the engine be dropped later without losing anything else, should the target narrow. **Shape (for the 10-17 weekly to write at execution grain):** (1) a `FieldSolution` interface — an unstructured mesh with cell tags plus `E` (complex, cell- or edge-based) and the material map, read from XDMF/VTU or from a `dolfinx` function directly; and a `PortSolution` — a Touchstone file plus port metadata; (2) `post/sar.py`, `post/b1.py`, the loss partition and `thermal/` consume only those; (3) two backends gated *identically*: the DolfinX one reproduces every existing `MAT-4` / `WF-6` / `TH-14` record to the digit (the refactor moves no number), the Palace one reproduces `OPS-61`'s S and the phantom power on the `ANS-4` fixture; (4) the benchmark cases' runnable halves dispatch on the backend. **Gate of record:** digit-identical reproduction of every imported band and record on the DolfinX backend before any second backend is wired — a refactor that moves a record is a defect. **Not in scope:** a GUI, a new solver, changing any physics. **Prerequisites the embargo waits on:** `OPS-61` step 1 (a second backend's fields to design against), `PORT-21` (so the port interface is not frozen around a known offset), one F-human physics step (so the interface sees a human-scale field once). | unmeasured — the 10-17 weekly costs it |
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
| `GEO-33` | **F-human-32: the 32-leg birdcage rung** — `birdcage_port_domain` at `n_legs = 32` (64 ring-gap ports on the high-pass topology), human-scale radius and length in the F-human class | ⬜ Future work, operator directive 2026-09-15: the 3T research coil the project is ultimately compared against has 32 legs, so the production fixture eventually needs a 32-leg rung beside the 16-leg F-human. **Parameters are generic by rule:** leg count, and a coil length and ring radius in the ordinary published clinical-birdcage range, nothing else — no rung/strip widths, capacitor values, shield or end-ring geometry taken from any specific product (the operator holds NDA-covered sizing and it never enters this repo, tracked or not; treat it like the AED numbers). Sequence: after the F-human degree-order question (`WF-7` step 0b, 2026-09-19 XXL) is read — step 1 is a `GEO-25`-style cost probe (mesh only, CAD identities, the C32 terminal-ratio gate, cell count and price), then a single degree-1 drive priced for the XL tier. Not dated; the weekly places it in §10 once the F-human order price is known. **Conductor model note (operator, 2026-09-20):** the research coil is built from copper *strips*, and the operator's own AED workflow models them as 2-D sheets with a Finite Conductivity boundary — so this rung should carry the coil as **zero-thickness sheets**, not round tubes: the same Leontovich `Z_s = (1 + j)/(σδ)` as `TH-14`, but applied on **both sides of an interior facet** (the tape is many skin depths thick at 64/128 MHz, so the two sides decouple and each sees plain `Z_s`; HFSS's thickness/layered option is not needed). That two-sided interior-facet form is a small extension of `TH-14`'s exterior-hole surface term and is this chunk's first step once scoped. `ANS-6` deliberately stays on round tubes to match the gated fixture; the strip geometry is a different fixture (edge current crowding changes `L` and the loss), not a different treatment. | unmeasured (cost probe first) |
| `GEO-34` | **STEP import through Gmsh/OpenCASCADE with named-group tagging and a case config file** — the CAD-input path: complex designs come in as STEP, materials / boundaries / ports are declared on named CAD groups in one config beside the file, and the generator's own tag scheme comes out the other end (operator directive 2026-09-20: no native modeller, ever — CAD in, preflight view, solve) | 🟡 **Step 1a landed 2026-09-23** (`20260923T110405Z_GEO-34.log`): `io/step_import.import_step` + JSON group map re-import the Gmsh-OCC-written F-small STEP with the generator's tag census, all four sheet areas at `SHEET_AREA_M2` to ≤ 2.2e-16, conductor meshed/CAD 0.970165 ≥ 0.95, and both unmapped/empty-group controls raising; 116 662 cells vs the primitive 116 085 (printed, not gated). Steps 1b (`PORT-9` gates on the import) and 1c (independent kernel) open. **Step 1b attempted 2026-09-25 — negative result, parked** (`attempt/GEO-34-step1b-20260925T094541Z`, `20260925T094541Z_GEO-34-step1b.log`, 114 s standard `-n 2`): on the imported mesh the cyclic pre-gate (iv), reciprocity (i) 1.897e-14 and passivity (ii) σ_max 0.999992218 pass and the P2/P3-swapped control fails (iv) as asserted, but C4 gate (iii′) misses — self 3.3151 %, adjacent 1.1102 %, opposite 2.2713 % against 0.5 %, separation 3.0514× against 10×. The miss is two-fold (x-axis legs ≠ y-axis legs; narrowed sheets 26/26/29/26 facets), so the STEP round trip changes port-level physics beyond the bands. Leading hypothesis: the import loses the port-box triangulation congruence of `GEO-19` step B (known-issues 2026-09-25). **Why:** every fixture so far is built from Gmsh primitives inside `io/mesh.py`; the research coil, implants and anything an HFSS user would bring exist as CAD. The space of open solvers without a CAD path is full; the differentiator is a path that keeps the gates. **Step 1 — import + tag map (standard):** `io/step_import.py` (additive): `import_step(path, config)` runs `gmsh.model.occ.importShapes`, synchronises, and maps the config's named groups — CAD entity names where the STEP carries them, else geometric selectors (bounding box / centroid / axis, the same predicates the generator already uses) — to the project's physical-group tags (volumes: conductor / phantom / air / implant; surfaces: PEC, impedance, port sheets with drive direction and reference impedance); sizing fields per group; returns the same `(mesh, cell_tags, facet_tags, diagnostics)` tuple the primitive generators return. Config is one YAML/JSON file next to the STEP — the same shape as a Palace config and what an HFSS user thinks in. **Gate (asserted):** the F-small four-leg birdcage rebuilt from a STEP that a new CadQuery/build123d emitter writes from the *same* parameters (`geo/step_emit.py`, additive) reproduces, through `import_step`, the `GEO-18` CAD identities (meshed/CAD conductor mass ≥ 0.95, terminal-area ratios in the imported band) and `PORT-9`'s four-port gates at 10 MHz (reciprocity / passivity / C4 spread, imported bands) — **the same identities, not the same cell count**: a STEP round-trip changes the CAD kernel's tessellation, so cell-count records are *printed beside the primitive rung's and not asserted* (the (1*) licence question is named in the row: mesher-dependent records become routine under STEP, and a re-record needs the reconciler, never this step). **Negative control (asserted):** the config with the port-sheet group deliberately unmapped fails the import with a message naming the missing group — a silent untagged port is the failure a config invites. **Step 2 — preflight export (standard):** `--preflight` on the runner: mesh, tag, and write the combined XDMF plus the setup figure with materials, boundaries and ports as coloured regions and *no solve*; gate: the preflight's tag census equals the solve path's on the same STEP. This is the "see what I am doing before I solve" the operator asked for; an interactive viewer (pyvista/trame) is a later `EX` item, not a product surface. **Step 3 — an external STEP (heavy by prediction, cost probe first):** a STEP not written by our emitter — a 16-leg high-pass birdcage drawn in FreeCAD or CadQuery by the operator with named groups — imported, meshed, port-gated at 10 MHz; the first design that did not come from `io/mesh.py`. **Not in scope:** editing, a GUI, IGES/STL (STL has no CAD entities to name; a later step if needed). **Sequencing:** independent of the physics chains; step 1 is a slot item once the review costs it (the emitter and importer are pure Gmsh/OCC — measured in seconds on F-small); `GEO-33`'s strip coil is the first consumer. **Costed and split by the 2026-09-23 03:00 review (§9 item 37):** step **1a** = the STEP round trip, the config's group map and the *mesh-level* gates only (tag census, `GEO-18`'s analytic sheet area, the CAD-mass gate; the unmapped-group control) — no solve; step **1b** = `PORT-9`'s four-port gates at 10 MHz on the imported mesh; step **1c** = the independent-kernel emitter. **Emitter substitution in 1a:** CadQuery / build123d are not in the image (`docker/Dockerfile`), and adding them is an operator rebuild; 1a emits the STEP with Gmsh's own OCC writer (`gmsh.write("….step")` on the generator's model before meshing), which exercises the STEP reader, entity renumbering and the group map but not an independent CAD kernel — that independence is 1c's, when the image carries one (the weekly / operator decides). | standard (steps 1–2); heavy by prediction (step 3, probe first) |
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
| `TH-15` | Internal perfect-electric-conductor bodies | 🟡 Open: ✅ step 1 (the PEC sphere as a hole against its closed form), 2a and 2d (the two-torus hole route; the gap-displacement port current on the open-circuit anchor, 2026-09-07), 3a (`birdcage_port_domain(as_hole=True)`, the 80 181-cell hole beside the 116 085-cell solid, 2026-09-06) and 3b (`gap_cell_tags`, default unflipped, 2026-09-09). Open: step 2's unitarity gate — eight sub-steps, 2f attributed the 2 % `Z` asymmetry to the point-sampled `_path_voltage`, 2h 🧪 2026-09-09, the `src/` replacement specified but unwritten — and the two-torus unitarity ruling above (weekly). **Step 3 ✅ 2026-09-13 15:00 slot** — the birdcage 4×4 as a PEC hole (80 181 cells, 19 826 tag-401 facets, 0 not exterior) passes `PORT-9`/`PORT-11`'s imported gates at 10 / 64 / 128 MHz: `‖S−Sᵀ‖/‖S‖` 1.59e-14 / 1.47e-15 / 9.16e-16, `σ_max` 0.999994234 / 0.999813792 / 0.999502556, worst class spread 0.0190 % / 0.0497 % / 0.0734 % (band 0.5 %); solid control reproduces `LEG_D_S_MATRIX_10MHZ` to 1.158e-10 (band 1e-6) in the same window (`20260913T202954Z_TH-15.log:951–954, 2768, 2833`; `…202718Z:951–954`; `…202828Z:956–959`). **The power anchor is a record, not a gate (ruled 2026-09-13 18:00 review, `log-pathologist` UNCOUNTABLE):** the item's registered comparand — the four-port terminal sum `Re Σ½V I*` against `½∫_phantom σ|E|²` — went red at **7.700077682e-05 W vs 6.376395218e-08 W** (`…202311Z:958`, 1 208×), and the in-slot substitute `P_src − ΣP_sheet,field = P_phantom` (3.634e-10 / 2.2e-12 / 1.1e-12) is `PORT-16`'s exact discrete identity on a mesh with **no conductor volume** (`…202954Z:80–81`: 10 fragment volumes, conductor solids removed) — it cannot test "all loss is in the phantom", which is the mesh's construction. **Step 3c ✅ 2026-09-13 19:30 slot — the excess is attributed.** The hole's 7.693701287e-05 W terminal excess equals the printed Cauchy–Schwarz deficit `C_total − Σ½|I|²Re Z_p` to every digit. The hole's driven-port `C/terminal − 1` is 1.058874954e-02 against the solid's 1.059204217e-02 (hole/solid 0.9997), so this is the sheets' terminal-form deficit, not a hole readout systematic. Anchors in `20260914T005452Z_TH-15-step3c.log` (21 passed, 102 s, `-n 2`): (a) the discrete identity with the non-phantom term closes at 3.327e-15 (hole) and 7.898e-15 (solid), the hole's `P_(Ω∖phantom)` reads 0 — both true by construction (`:966–967, 2787–2788`); (b) the solid's P1 `C/terminal − 1` reproduces 2d's 1.059204217e-02 at rel 1.490e-10 (`:2794`); (c) the three port gates re-ran green as committed: 1.707e-14, σ_max 0.999994234, worst spread 0.0190 %, `LEG_D_S_MATRIX_10MHZ` to 1.158e-10 (`:951–953, 2799`). This discharges the provenance caveat at 10 MHz. The known-issues entry is retired. **Power sentence re-registered by the 2026-09-14 03:00 review (rule (h)): `Σ½Re(V I*) = P_vol + (C − terminal)` — the hole's 7.693701287e-05 W excess equals `C_total − Σ½\|I\|²Re Z_p` to every digit (`:969–970`), as does the solid's 6.716202469e-05 W (`:2790–2791`); hole/solid `C/terminal − 1` = 0.9997, so it is the sheets' Cauchy–Schwarz deficit (`PORT-16`'s 10 MHz record), not a hole-route readout systematic.** Row stays 🟡 on step 2 (family frozen at 2e–2h since 2d; the weekly re-scopes). *State line refreshed 2026-09-13 10:30 review from the history — the `OPS-46` line was written from a ruling that predated 3a / 2d / 3b. History: `docs/planning/chunks/TH-15.md`.* | standard (step 3 heavy) |
| `TH-14` | **Surface-impedance (Leontovich) boundary on conductor surfaces** — `n × E = Z_s n × (n × H)`, `Z_s = (1 + j)/(σδ)`, so copper (σ = 5.8e7 S/m) is affordable at any frequency; Jin §1.5.3 (1.54)–(1.56) and §5.8.3 (third-kind boundary term) (operator directive 2026-09-04; the second conductor-model route; **serial on `TH-15`** for the conductor-as-hole mesh and facet tags). **Step 1 gated 2026-09-13 19:30 slot** (lossy-wall `TH-9` cavity against Pozar's Q_c: σ = 1e4 miss +0.010 % ≤ 5 %, Q(1e6)/Q(1e4) = 9.995, PEC control \|Im λ\|/Re λ = 4.8e-19, `20260914T004807Z_TH-14.log`); the 2026-09-06 "no separating anchor" annotation is retired — the Q_c anchor separates. **Step 2 (§9 item 6, the entry's "step 3") gated 2026-09-13 21:00 CDT slot** — copper F-small birdcage as a Leontovich hole, `tests/validation/test_th14_birdcage_copper.py`, `-n 2`: (a) copper reciprocity ≤ 1.9e-14, σ_max 0.999994 / 0.999814 / 0.999501, worst class spread 0.0734 % at 10 / 64 / 128 MHz; (b) surface-loss identity residual 1.6e-13 / 3.0e-13 / 7.0e-14 (band 1e-6); (c) 10 MHz bracket per class copper ≤ 2.36e-4 vs solid-800 record ≥ 2.48e-2, σ-ladder max\|ΔS\| falls ≈ 10× per 100× σ at all three f; predicted PEC-limit control 2.4e-6 / 4.2e-6 / 3.2e-6 ≤ 1e-4 met (printed); `P_coil/P_in` 0.929 / 0.448 / 0.219 (printed); 32 passed, 211 s (`20260914T021500Z_TH-14.log`). Outer box pinned by an in-module facet group (exterior ∖ 401), no mesh change. **Demoted ✅ → 🟡 by the 2026-09-14 03:00 review (auditor DEMOTE):** the row's own Done-when requires the Dodd–Deeds copper-slab step (the entry's "step 2") and the §2.1 conductor-model line; the slot closed on the §9 item's letter and flagged the conflict itself. The §2.1 line is written; the slab step is §9 item 2 (the Leontovich floor under `MAT-6`'s loop). **Slab step gated 2026-09-14 04:30 slot, 🟡 → ✅** (`tests/validation/test_th14_dodd_deeds_copper_floor.py`, `-n 2`, 17 passed, 340 s, `20260914T094224Z_TH-14-step2.log`). The floor is a real domain boundary: `create_submesh` on `MAT-6`'s own mesh minus the slab cells, with no mesher change. (a) ΔR(5.8e7) is −0.299 % from `coil_impedance_change` (2 %, `:283`). (b) The surface-loss identity holds to 1.31e-8 (1e-6, `:285`). (c) ΔR(5.8e7)/ΔR(5.8e9) = 9.9910 (1 %, `:292`). (d) (ΔX − ΔX_PEC)/ΔR = 1.00097 against the closed form's 1.00095 (2 %, `:284`). Census: floor 6852 + others 1258 = exterior 8110, overlap 0. The PEC-floor control's \|ΔR\|/\|ΔX\| = 0 (`:293`); it holds by construction, since the σ = 0 operator is real. Printed: ΔX(copper)/(ω·ΔL_image) = 0.910 (the box systematic), δ/h = 8.4e-3, and the 5.8e9 identity 8.98e-7, printed only. | ✅ | standard (step 3 heavy; slab step heavy, 340 s) |
| `TH-16` | **Symmetry planes: per-face PEC / PMC on cut faces with port rescaling** — HFSS *Perfect E* / *Perfect H* symmetry; quarter the birdcage, the memory lever for the F-human *refinement* rungs — **feature ladder B2** (operator directive 2026-09-04). *(Re-dated 2026-09-06 weekly: the "62 GiB F-human wall" was `TH-12` step 2's degree-2 figure on the 138 k-cell F-small and the r³ extrapolation; `GEO-25` measured F-human at fixed sizing as **504 642 cells** (exponent 0.84, 112 s to mesh), and the two priced degree-1 solves — `TH-11` step 5's 0.99 M cells at 64 GiB and `PORT-13` step 1's 270 k cells at 5.7 GiB summed RSS — bracket a first F-human 64 MHz degree-1 solve at ≈ 11–33 GiB, inside the 128 GiB box either way. Symmetry planes buy the degree-2 and h-refined F-human rungs, not the first solve; that solve is priced, not gated, by `WF-7` step 0.)* | ⬜ | standard |
| `TH-17` | **Birdcage eigenmodes** — the `TH-9` eigensolver on the loaded birdcage with a PEC coil (`TH-15`) and `PORT-14`'s capacitor sheets; mode frequencies vs the ladder-network closed form, Phase 6's named first target — **feature ladder B3** (operator directive 2026-09-04; serial on `TH-15`, `PORT-14`) | 🟡 **Step 1c EXECUTED 2026-09-21 (11:00 UTC slot, §9 item 24) — GREEN: the pencil-with-sheet-mass machinery is validated against a closed form (one LC loop).** `test_th17_birdcage_eigenmodes.py::test_step1c_lc_loop_closed_form` (env-gated `TH17_STEP1C=1`; no `src/`), `20260921T110359Z_TH-17.log`, Status 0, **394 s** (heavy; `-n 4`, complex, `timeout -k 30 1100`, durable capture, `-s`). Fixture `two_torus_domain(port_gap, emit_port_sheet, as_hole)`, every constant imported: 161 461 cells, 195 296 N1curl deg-1 dofs; the loop's sheet is facet tag **211** (the item said 201 — on the hole route 201/202 do not exist; 211 is torus 1's port sheet), `h` 1.395505060e-02 m, `w = A/h` 1.040000000e-02 m, `h/w` 1.341831788 (`:539`). **`L_fem = Im Z_in/ω` (printed, `:541–543`):** 1.062839664e-07 H at 10 MHz, **1.073064785e-07 H at 64 MHz** (used); Grover 1.085172998e-07 H beside, ratios 0.979420 / 0.988842 — never gated; `Z₂₁/Z₁₁` = 0.1604 / 0.1613 (the open loop's residual coupling, printed). `C = 1/((2π·64e6)²·L_fem)` = 5.763076340e-11 F in-run. **(a) asserted:** nearest eigenvalue `Re f` = 6.268576548e+07 Hz vs `f_LC` = 6.4e+07 Hz, **2.053 %** ≤ 5 % (`:571`; Im f +2.6e-09 Hz). **(b) asserted:** at `2·C`, `Re f` = 4.444741942e+07 Hz, ratio 0.7090512 vs 1/√2 = 0.7071068, **0.275 %** ≤ 2 % (`:572`). **Negative control asserted:** capacitor form removed ⇒ **0** eigenvalues in `f_LC·[0.8, 1.2]` (`:573`); the shift-invert at `f_LC` with `nev = 6` converged only the gradient cluster (`Re f` 8.1–9.1 kHz), so the predicted ≳ 0.5 GHz first cavity mode was **not reached at this target — prediction untested, printed as "none"** (rule (e)). Solve walls 96 / 124 / 99 s. **Consequence (item 24's "under green"):** the 1b (ii) ≈ 129.6 MHz floor stands as the F-small fixture's spectrum under the four-port loading, handed to the 09-26 weekly with the review's reading that row gate (a) may be mis-posed (below); no slot re-scopes gate (a). Prior status: 🟡 **Step 1 part (i) executed 2026-09-19 04:30 slot (second item, take-next) — the cost probe is CHEAP and the pencil assembles, but NO EIGENVALUE LANDS NEAR THE 64 MHz TARGET, so parts (ii)/(iii) did not run and the (C5) third-residual band is NOT pre-registered.** Landed additive and green on `main`: `core/cavity.py` gains `complex_relative_permittivity`, `general_mesh_pencil`, `solve_general_mesh_modes` (`_cavity_forms` and every box path byte-identical — nothing above the `TH-17` banner comment was touched), and `tests/validation/test_th17_birdcage_eigenmodes.py::test_cost_probe` (env-gated `TH17_PROBE=1`, so the default collection is unchanged). **Probe, `-n 4`, `20260919T094827Z_TH-17.log:899–915`, 51 s wall:** 80 181 cells, 111 121 N1curl deg-1 dofs, mesh 20.62 s + eigensolve 26.70 s = 47.80 s total, `ru_maxrss` 0.612 / 0.521 / 0.529 / 0.516 GiB (summed 2.179). Against the §9-item STOP rule (> 15 min or > 40 GiB at `-n 4`) that is **0.797 min and 2.179 GiB — PROCEED, by ~19× in time and ~18× in memory**; this step does *not* re-price to XL. `C_tuned` imported live from `PORT-15` step 3 (`tuning_sweep` + `select_c_tuned` on `S_64MHZ_EPS0_RECORD`) at 1.556993028375804e-11 F, never restated. **The blocker (the whole finding):** with `nev = 6` and shift-invert at `k₀² = (2π·64 MHz/c)² ≈ 1.799`, the nine converged eigenvalues are the **N1curl gradient (null-space) cluster** — λ ∈ [1.448e-09, 2.294e-09], i.e. `Re f` ≈ 1.8–2.3 kHz, `|λ − target| ≈ 1.8` for every one of them. Nothing in the pencil sits at 64 MHz. The capacitor term's sign and scale are as derived (`B_sheet = −(c²/ω_ref²)·L1(ω_ref)` = `+(C·h/w)/ε₀ ∫(n×u)·(n×v)`, positive-definite added mass, which is the direction that pulls the air box's ~GHz cavity modes down), so the leading hypothesis is that **the added surface mass is orders of magnitude too small to move any mode from ~GHz to 64 MHz, and/or the gradient cluster must be deflated before shift-invert can reach the physical branch** — the `TH-9` path discards it by a `null_cutoff_fraction`, which this general-mesh path does not yet do. Next attempt: (1) deflate/filter the null space (or solve the `k₀² > 0` branch with `EPS.setDeflationSpace` / a larger `ncv`), (2) print the un-loaded (C = 0) spectrum on the same mesh to locate the physical branch, (3) only then re-price nev/target. Prior state: ⬜ **Step 1 written 2026-09-18** (interactive operator session under the enumerated-chain licence, §9 rule (4); it is §10 chain step 5 — *the internal "tuned birdcage" milestone*; queued as §9 item 5). **Fixture:** `TH-15` step 3's hole mesh (`birdcage_port_domain(…, as_hole=True)`, the coil PEC by the exterior default, `test_th15_birdcage_pec_hole.py`) with the phantom (σ 0.5 S/m, εᵣ 78) and `PORT-14`'s four gap sheets as **capacitor sheets at `PORT-15` step 3's `C_tuned`** (imported from `test_port_circuit_layer_field.step3_tuning` — `tuned["c_f"]` — never restated); no source, no termination. **Formulation:** the lumped-sheet bilinear term (L1, `ports/lumped.py`) with `Z_p = 1/(jωC)` is `−ω²μ₀(h/w)C ∫(n×u)·(n×v)` — a surface *mass* term (`h/w` by (L2): `R = Z_p·w/h`, so `1/R = (h/w)·jωC`; the row said `w/h` until 2026-09-19 — a typo the 04:30 slot caught; the landed code derives and implements `h/w`) — and the phantom's conduction is linearised as a complex permittivity at `ω_lin` exactly as `TH-14` step 1 linearised the Leontovich wall (`core/cavity.py: solve_impedance_wall_cavity_mode`, one fixed-point re-solve at `Re ω`), so the whole problem is one non-Hermitian generalised pencil `A x = λ (B + B_sheet(C)) x`, shift-invert at `k₀² = (2π·64 MHz/c)²` (`_solve_pencil_nonhermitian`), `nev ≥ 6`. Additive `src/`: a general-mesh pencil builder beside `_cavity_forms` (the box path byte-identical; `TH-9` and `TH-14` step 1 gate modules re-run green). **Readout:** the complex eigenfrequencies nearest 64 MHz — the `k = 1` degenerate pair (mode 1), the `k = 0` end-ring mode above it and the `k = 2` mode below (high-pass ordering, `ports/circuit.py: birdcage_highpass_mode_frequencies` (C5)), each with `Q = Re ω/(2|Im ω|)`. **Gates (asserted):** (a) mode-1 `Re f` at 64 MHz within `PORT-14`'s named κ systematic (≈ 1 %; the constant imported from the `PORT-14` step 3 module, named in the §9 item) — `C_tuned` put the driven port's reduced network at series resonance there, so this is the circuit-layer ↔ eigen-layer consistency identity; (b) the pair degenerate to the imported `PORT-11` C4 spread band (0.5 %); (c) **closed-form structure:** `f_0 > f_1 > f_2` fit (C5) `ω_k⁻² = C(L_r + 2L_l sin²(πk/4))` with **positive** `L_r`, `L_l` (two unknowns, three equations; the third residual asserted ≤ a band the cost probe sets and the §9 item pre-registers before the gated run) — this replaces the chain's "step-2 inductances", which `PORT-15` step 2 read off *negative* (gap capacitance dominating); (d) **negative control:** at `2·C_tuned` mode 1 moves by the (C5) factor `1/√2` on `Re f` to the same band; (e) **PEC-phantom control** (σ → 0, Hermitian pencil): `Im ω` at machine zero, the `Re f` shift printed. **Done-when:** (a)–(e) through the harness at `-n 4`, the fixed-point shift recorded (< 0.1 % or the band re-read), elapsed recorded ⇒ **`TH-17` → ✅ and Phase 6's first physics target ticked.** **Not claimed:** no absolute mode frequency against AED (`ANS-6`'s), no B₁ homogeneity, no human scale. **Cost probe first (§5.1):** mesh + one shift-invert solve at `-n 4`, printed dofs / time / `ru_maxrss` — unmeasured on this mesh (`TH-9` / `TH-14` were boxes). **Step 1 part (i) ran 2026-09-19 (04:30 slot, `f085e51`): the probe is cheap (47.8 s, 2.18 GiB at `-n 4`; `general_mesh_pencil` / `solve_general_mesh_modes` landed additively in `core/cavity.py`, `TH-9`/`TH-14` gates re-run green `941fa15`) but shift-invert at the 64 MHz target returned only the N1curl gradient cluster (nine pairs at `Re f` ≈ 2 kHz), i.e. no eigenvalue anywhere in (0, ≈ 90 MHz) — parts (ii)–(iii) BLOCKED.** **Step 1b (written 2026-09-19, operator session; §9 item 10) — locate the missing mode or the defect, with a closed form:** (i) assemble the sheet mass alone and print `‖B_sheet‖` against `‖B‖` restricted to the sheet dofs — a zero says the (L1) forms never reached the pencil (facet tags / restriction), the first thing to rule out; (ii) a target scan — shift-invert at 1, 4, 16, 32, 64, 128, 256, 512 MHz with `nev = 6`, printing every converged eigenvalue with `Re f` > 1 MHz — to find where the capacitor-loaded modes actually sit; (iii) **the closed-form LC control:** a PEC circular loop (torus, major radius `a`, wire radius `r`) with **one** capacitor sheet in a gap resonates at `f = 1/(2π√(LC))` with `L = μ₀a(ln(8a/r) − 2)` (the loop closed form already in the repo, `tests/validation/test_port_self_impedance_energy.py`, imported), `C` chosen to put `f` near 64 MHz; the pencil's nearest eigenvalue asserted within 5 % on a mesh where the loop's own `L` (from `PORT-1`'s energy route) is within 2 % of the closed form. (iii) is the gate that decides between *the pencil is wrong* (known-issues entry, the §7 formulation re-derived) and *the birdcage's eigen-resonance at `C_tuned` is simply not at 64 MHz* (a finding about the circuit-layer identity, and (ii) says where it is). Heavy by measurement of (i) (seconds); `-n 4`. **Step 1b parts (i) and (ii) EXECUTED 2026-09-20 04:30 slot — the sheet mass is present and locally dominant, and the loaded spectrum's floor is ≈ 129.6 MHz, not 64 MHz.** `20260920T093810Z_TH-17.log`, Status 0, **232 s**, 3 passed, `-n 4`, 111 121 dofs; both new tests env-gated behind `TH17_STEP1B=1` (default collection unchanged), plus an additive `target_hz` keyword on the module's own `solve_modes` wrapper — **no `src/` change**. **(i) printed, never gated (`:1742–1747`):** the four gap sheets each carry 26 owned facets, area 5.835299e-05 m², `h` 8.000000e-03 m, `w` 7.294124e-03 m, `h/w` 1.096773e+00 (tags 211–214, identical — the C4 fixture). `‖B_volume‖_F` = 1.634083724e+01 vs `‖B_sheet‖_F` = 1.364209336e+01 (ratio 8.348e-01), and **on a sheet-dof indicator the sheet form dominates the volume form by 1.569208687e+03** (1.760307187e+02 vs 1.121780169e-01). So the (L1) forms *do* reach the pencil and the added surface mass is *not* negligible where it acts: the "too small to move a mode" half of step 1's hypothesis is **refuted**, and the facet-tag/restriction failure mode (i) existed to rule out is ruled out. **(ii) printed, never gated (`:1753–1800`):** the eight-target scan converges 6–14 pairs per target but finds **nothing with `Re f` > 1 MHz at the 1, 4, 16, 32 or 64 MHz targets** — the gradient cluster only, reproducing step 1 at its own target. Thirteen eigenvalues above 1 MHz appear from 128 MHz up: the **lowest physical modes are a near-degenerate pair at 1.295936260e+08 and 1.296011466e+08 Hz** (split 5.80e-05 relative, i.e. 0.0058 % — the C4 pair, well inside `PORT-11`'s 0.5 % spread band), then 1.589189395e+08 Hz, then a heavily damped 2.966755624e+08 Hz (λ = 2.559e+01 + 4.497e+01j), with the 256 and 512 MHz targets re-finding the same three and adding 5.283e+08 / 5.551e+08 / 5.553e+08 Hz. **The finding:** the loaded pencil's spectrum has a hard floor at ≈ 129.6 MHz and nothing in (2 kHz, 129.6 MHz); the 64 MHz target is in a genuine spectral gap, so shift-invert returning only the null space there is the correct answer to the question asked, not a solver defect. **Not yet decided** — which is what (iii) exists for: whether the ≈ 129.6 MHz floor is the physical `C_tuned` resonance (making step 1's gate (a) the false premise) or the pencil mis-scales the sheet term, cannot be settled by (i)/(ii), because neither carries a closed form. **Part (iii), the LC loop control — the step's only asserted anchor — is NOT executed, and its pre-condition is contradicted by the repo's own record (§9 standing rule (e), reported not decided):** item 10 asserts the loop's `PORT-1` energy route must give `L` within **2 %** of the closed form as the mesh pre-condition, but that fixture's *recorded* reading is `4ωW_m/I² = 7.437 Ω` against Grover's 6.818 Ω — **9.1 %**, measured 2026-08-03 and carried there as **printed, not gated**, attributed to the 0.08 m PEC-box padding (`test_port_self_impedance_energy.py`, module docstring and `test_magnetic_energy_reactance_against_grover`). The 2 % pre-condition is therefore unreachable on `PORT-1`'s fixture as it stands, and (iii) needs a padding/resolution rung for `L` — unpriced — before its 5 % eigenvalue anchor is honest. Both anchors left untouched. Also for whoever writes (iii): the helper is named **`grover_loop_inductance`**, not `loop_inductance` as item 10 has it. **Step 1c (written 2026-09-21 03:00 review, §9 item 24, rule (f) applied by the review):** (iii) is re-registered on a fixture that exists — `two_torus_domain(port_gap, emit_port_sheet, as_hole)`, torus 1's sheet carrying `C`, torus 2's gap open — with `L` taken from **that fixture's own driven lumped-sheet route** (`Im Z_in/ω`), so both sides of the unchanged 5 % are the fixture's numbers; Grover is printed beside, never gated (no single-loop generator exists; `PORT-1`'s 9.1 % is an impressed-current fixture at a fixed 0.08 m padding). Adds the `2·C → 1/√2` closed form at 2 % and the sheet-removed negative control. **Reading handed to the 09-26 weekly, not ruled here:** this module's pencil loads **all four** ports with `C_tuned` (`_capacitor_mass_forms`, `live=None`), while `PORT-22`'s driven sweep feeds P1 and tunes `Im Z_in(P1) = 0`; an eigenfrequency of the four-capacitor structure satisfies `Im Z_in(P1) = 1/(ωC_tuned)` instead, so the 1.2959e+08 Hz floor and `PORT-22`'s 63.9986 MHz zero answer different equations and are not in conflict — **gate (a) ("mode 1 at 64 MHz") may be mis-posed for this termination**; no slot re-scopes it. | heavy *(step 1 probe measured 47.8 s / 2.18 GiB at `-n 4`)* |
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


**`TH-15` narrative** — moved byte for byte to `docs/planning/chunks/TH-15.md` (`OPS-47`).

**`TH-14` — surface-impedance (Leontovich) boundary on conductor surfaces** ✅
*(closed 2026-09-14 04:30 slot; result block written by the 2026-09-19 weekly,
full narrative in `docs/planning/plan-archive.md`, entry «§7 TH-14 full
narrative — archived 2026-09-19 (weekly review)».)* Three gates, digits in the
§7 table row: **step 1** lossy-wall `TH-9` cavity Q against Pozar's Q_c
(σ = 1e4 miss +0.010 % in a 5 % band, `20260914T004807Z_TH-14.log`);
**slab step** copper Dodd–Deeds floor under `MAT-6`'s loop (ΔR −0.299 % in a
2 % band, surface-loss identity 1.31e-8, `20260914T094224Z_TH-14-step2.log`);
**birdcage step** copper F-small hole passes the `PORT-9`/`PORT-11` gates at
10 / 64 / 128 MHz with the surface-loss identity ≤ 3.0e-13 and the σ-ladder
converging onto the PEC matrix (`20260914T021500Z_TH-14.log`). The Fresnel
plane-wave step is retired as written (no separating anchor at copper).
**Carry-forwards:** the solid-side bracket is asserted at 10 MHz only (no
stored σ = 800 4×4 at 64/128 MHz); no absolute S claim on the copper coil —
that is `ANS-6`.


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
| `MAT-4` | SAR computation `σ|E|²/(2ρ)` | ✅ *(step 4 closed 2026-09-06: the C95.3 mass-averaging operator on the **coil-driven** F-small field — 10 g C4 identity 0.3303 / 0.0756 / 0.0574 / 0.3132% at the imported unmoved 5% band, whole-phantom identity 1.58e-14, `23 passed` / 130 s at `-n 4`, `20260907T003548Z_MAT-4-step4.log`. **Scope: 10 g at fixed `h` on one fixture at 10 MHz; the 1 g column is a printed record at 6.8383% worst, verdict (b); no absolute SAR, no C95.3 compliance claim, no Larmor, no convergence claim**. Step 5, 2026-09-08: on the 0.0025 phantom rung the 10 g pairs re-assert at 0.0309–0.0644% and the 1 g pairs read **0.0957–0.1305%**, printed. **Step 5b ✅ 2026-09-08: 1 g and 10 g are both C4-gated on the 0.0025 rung** at the same imported unmoved 5% band, and the rung's mesh (199 920 / 58 866) is a version-tagged record at the 1% `CELL_COUNT_BAND`; `26 passed` / Status 0 / 313 s at `-n 4`, `20260908T200629Z_MAT-4-step5b.log`)* **Externally anchored 2026-09-18 (`ANS-2` AGREE): the coil-driven phantom power and pointwise SAR this identity is built on agree with HFSS at 10 MHz on F-small (5 % integral, ±10 % pointwise, residual = feed); annotation only, no band moved, no AED value tracked.** | standard *(step 4 heavy by ceiling, measured 130 s; step 5 251 s at `-n 4`)* |
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


**`POST-6` narrative** — moved byte for byte to `docs/planning/chunks/POST-6.md` (`OPS-47`).

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
| `PORT-14` | **Lumped RLC sheets** — HFSS *Lumped RLC* boundary: the `PORT-9` sheet law generalised from 50 Ω to `Z_p(ω) = R + jωL + 1/(jωC)`, so capacitors live in the model — **feature ladder A2** (operator directive 2026-09-04; serial on nothing) | ✅ **Closed 2026-09-13 19:30 slot (step 3): the κ-derived width route (told width `w/(1 + κ)`, κ = in-run `C/terminal − 1` through `ports/shares.py`) is registered at 64 MHz — (0) lift 0.000e+00, (i) κ(64) 1.060762155e-02 vs 2d's 1.060762e-02 at 1.457e-07, (ii) corrected residuals 5.359129e-05 / 1.998404e-06 ≤ 1e-3, (iii) and the by-record control green, 116 085 cells, `-n 2` (`20260914T003252Z_PORT-14-step3-64mhz.log:1937–1959`, 114 s; `…003503Z_…-10mhz.log:1888–1902`, 196 s; `PORT-9` gate module re-run green `…004031Z_…-port9-gate.log:1971`, 66 s). κ is carried as the sheet's named systematic and `TH-17` may not gate a mode frequency tighter than it; the 128 MHz pair (4.013e-05 / 5.599e-06, `…003827Z_…-128mhz.log:1955–1956`) stays a printed out-of-sample reading. *History: `docs/planning/chunks/PORT-14.md`.*** Prior state: 🟡 *(step 1 executed 2026-09-05, 21:00 slot — complex `Z_p` + `ports/circuit.py` land and solve; the reduction identity misses the pre-stated 1e-3 band at 1.596e-03 / 3.371e-03 / 7.250e-04 for C / L / R, band not widened, known-issues 🟡; 64 MHz is step 2. **Step 1b executed 2026-09-05, 09:00 slot: the residual is non-monotone in sheet resolution — 1.5956e-03/3.3705e-03 at ×1 (116 085 cells), 4.1880e-03/8.8755e-03 at ×0.75 (161 695), 1.4904e-03/3.1449e-03 at ×0.6 (209 604), reciprocity ≤ 2.4e-14 and σ_max ≤ 0.99999292 on both refined rungs — so the resolution hypothesis is refuted and `sheet_width_m` (the ×0.75 rung is the one whose four sheet widths break C4) is the step-1c suspect; band untouched. **Step 1c executed 2026-09-05, 21:30 slot on the fixed 116 085-cell gate mesh — reading (1): the width the law is told is the lever. Residual ×5.803881 / ×5.830276 at ε = +5%, ×3.748033 / ×3.724086 at −5%, ×5.634488 / ×5.679903 at alternating ±5.3% (C / L); all three perturbed 4×4s reciprocal to ≤ 1.891254889e-14 with σ_max ≤ 0.999997273, cells 116 085 bitwise, the Γ = 0 control asserted on all six terminations. Both directions *raise* the residual, so the zero-crossing lies inside ±5%: a three-point fit puts it at ε\* ≈ −0.0107 (C) / −0.0110 (L), common to the two elements, with fitted minimum ≈ 0. Step 1b's uniformity framing is superseded — configuration C is not distinguishable from A. Band untouched, the red gate test not re-run**)* **Step 3 ruled 2026-09-13 18:00 review — anchor (i) re-registered, parked branch unblocked.** The 12:00 slot's parked route (`attempt/PORT-14-step3-20260913T172330Z`, `86c93f6`) had (0), (ii) **5.359129e-05 / 1.998404e-06 ≤ 1e-3** at 64 MHz, (iii) and the by-record control green and (i) red only because its comparand was step 2b's *pooled fit* 1.064081e-02, which this row's own 2d reading puts at 0.99688–0.99714× the `C/terminal − 1` it is meant to reproduce (`docs/planning/chunks/PORT-14.md:602–605`). (i) is therefore **re-registered as: the in-run derived κ(64) reproduces 2d's P1 `C/terminal − 1` record 1.060762e-02 at rtol 1e-3** (`20260912T123236Z_PORT-14-step2d-64mhz.log:1942–1949`; the parked run read it to 1.457e-07) — the same quantity on the same fixture, not a widened band; and the sign sentence is corrected to `1/(1 + κ)` (2e's fitted ×0.989446732), which is what the parked code implements. Re-queued as §9 item 1: land the branch's `src/` + tests by path, edit the one constant, re-run all three windows plus the `PORT-9` gate module (rule (c): `build_four_port_sweep` gained a default-`None` keyword). | standard (steps 1–2b); heavy by ceiling for steps 1c–3 (`timeout -k 30 590`, windows ≤ 196 s — cell reconciled 2026-09-14 03:00 review on the auditor's caveat) |
| `PORT-15` | The circuit layer | ✅ 2026-09-14 02:07Z on gate (i) + the tuned `S₁₁` (one F-small 4-leg fixture, 64 MHz; gate (ii), the 32-port mode spectrum, is `TH-17`'s and not claimed). Step 1's ladder-network closed form and termination reduction hold as pure-numpy identities. Gate (i): discharged by `PORT-14` step 3, stored record here (`tests/validation/test_port_circuit_layer_field.py`, step 2 ✅ 2026-09-14 01:07Z — stored 64 MHz residuals C 5.36e-5 / L 2.0e-6 under 1e-3, records reproduced ≤ 1.8e-13, `20260914T010448Z_PORT-15.log`). Step 3 ✅: `C_tuned` = 15.570 pF (P2..P4, P1 driven) zeroes `Im Z_in` to 2.1e-15 relative; in-model vs circuit tuned `S₁₁` 8.26e-5, 2×2 6.12e-5 under 1e-3 (`20260914T020419Z_PORT-15.log`, 7 passed, 176 s). "Tuned" = series resonance, `R_in` 6.77 Ω, `|S₁₁|` 0.761 — not matched. *History: `docs/planning/chunks/PORT-15.md`.* | smoke (step 1, measured 4 s); standard for the field-side steps (step 3 window 176 s) |
| `PORT-16` | The ~1 %-of-supplied accounting gap on the 4-leg fixture | ✅ Closed 2026-09-07: the exact discrete power identity closes on every single drive and on the superposed quadrature drive, and the accounting gap is attributed to the terminal form's Cauchy–Schwarz deficit. Step 3's gap h-rate is optional, unclaimed and the weekly's to commission. *History: `docs/planning/chunks/PORT-16.md`.* | standard (three windows ≤ 180 s at `-n 2`; the ×0.6 rung measured 136 s) |
| `PORT-17` | Wave ports / coax feeds — HFSS *Wave Port*; low priority: MRI coils are fed at lumped points through matching networks — **feature ladder C2** (operator directive 2026-09-04; commission only if a benchmark demands it) *(**renumbered from `PORT-16` by the 2026-09-09 03:00 daily review**, on the 02:15 weekly's finding 1: §7 carried two `PORT-16` rows, which breaks the stable-ID contract. The closed, audited, log-bearing chunk above keeps the ID; this unopened ladder entry moves. `PORT-17` was unused repo-wide. The §9 item-5 ladder table moved with it; no other file referenced this row)* | ⬜ | standard |
| `PORT-18` | Does the lumped-sheet port read its current off one side of a discontinuous component | 🧪 Measured 2026-09-10: the premise was false — the sheet normal is azimuthal — and the '+'-side mechanism is excluded for both the read-back and the source term. The printed lead is taken up by `GEO-32`; `ANS-4` step 2a and `WF-6` step 4f stay blocked. *History: `docs/planning/chunks/PORT-18.md`.* | standard (heavy by ceiling), `-n 2` + `-n 1`, no solve — **measured 154 s + 68 s** |
| `PORT-19` | Reuse the factorisation across the drives of one sweep | ✅ Closed: one factorisation per sweep instead of one per port, with `S`, `Z` and the kept fields matching per-drive solves inside their asserted bounds at both rank widths. Step 6 recorded the two remaining example callers green on the reuse-on default. *History: `docs/planning/chunks/PORT-19.md`.* | smoke (step 1), standard (step 2), heavy (step 3) |
| `PORT-20` | **The gap-voltage (current-drive) route must report the S-matrix** — on that route the undriven ports are open, so `S_ij = b_i/a_j` is not a column of S; the route's `Z` is the open-circuit matrix and `z_to_s(Z)` is S (opened 2026-09-19 by the weekly from the `ANS-3` adjudication; known-issues 2026-09-19; serial on nothing; `OPS-57`'s single impedance-to-S implementation is the conversion to call if it has landed, otherwise the existing `sparameters_from_impedance`) | ✅ **2026-09-20 — steps 1–3 all executed** (steps 1–2 in the 04:30 slot, item 11; **step 3 in the 09:00 slot, item 17**). **Step 3 (records, `-n 2`, complex, standard):** the four S-derived records are re-recorded under `S = z_to_s(Z)` with the power-wave digits kept beside them and *asserted* to fail each record's own band, and step 2's strict `xfail` is removed. `ports:2` green — `20260920T140828Z_PORT-20.log`, Status 0, **181 s**: measured `‖S − Sᵀ‖/‖S‖ = 3.112130445718013e-05` and `‖S‖₂ = 0.8613568944845725`, reproducing the new records at **1.59e-11 absolute / 1.43e-12 relative** against the unmoved 1e-6 bands; the `PORT-1` step-4 gate module green — `20260920T141141Z_PORT-20.log`, **18 passed / 190 s** (was 17 passed / 1 xfailed), `passivity_max_sigma 0.8613568944814173` vs the new record 0.861356894 (miss 4.814e-10, band 1e-6) and symmetry ratio `3.1121289645891435e-05` vs 3.112129e-05 (miss 3.541e-13, band 5e-7). **Negative control, asserted per record:** the superseded power-wave digits miss the corrected run by **1.647e-05 absolute** in the symmetry residual and **3.992e-03 relative** in `‖S‖₂` (gate module: 1.646e-05 / 3.453e-03) — the predicted ≈ 0.016-in-`\|S₂₁\|` size, each > its band. **Anchors held:** every `Z`-derived record is digit-identical, reproducing at 2.10e-10 / 2.06e-10 relative (raw / corrected mutual ratio) — nothing about `Z` moved, so the negative-result branch did not fire; reciprocity and passivity at **unmoved** bands. **The `ans:3` leg was not run — pre-registered stop:** `03_two_torus_gap_ports_10MHz.py:725-727` rewrites the gitignored `COMPARISON_private.md` unconditionally whenever `aed_results/` is present (it is), which the step forbids, so that case's *generated* `metrics.json` / `COMPARISON.md` still carry the pre-correction S table — filed as a 🟡 known-issues entry (2026-09-20) with its unblock condition; its *records* are imported from `examples/ports/02_…py` and are already corrected. **For the next interactive session:** CLAUDE.md's "`PORT-20`" open-finding clause (§ the two external findings paragraph) is now stale — the current-route finding is fixed; CLAUDE.md is the operator's file and no slot edits it. *History (steps 1–2, item 11):* The change landed as pre-registered: `run_n_port_sparameter_sweep` routes the gap-voltage branch through the new `_assemble_current_drive_route_matrices` → `sparameters_from_impedance(Z)`; the lumped-sheet branch is untouched. **Step 1** (`20260920T095207Z_PORT-20.log`, smoke, `-n 2`, 2 s, 3 passed, `tests/unit/test_port20_current_route_s.py`): on the T-network 2-port and the seeded random reciprocal 3-port the route's assembly reproduces `Z` and the analytic `(Z − z0)(Z + z0)⁻¹` at **max\|Δ\| = 0.000e+00** against the 1e-12 band; the **asserted negative control** — the pre-`PORT-20` power-wave assembly on the same open-port states — misses the analytic `S₂₁` by **\|ΔS₂₁\| = 6.614030e-02** (floor 1e-2, ceiling 2; the review's hand arithmetic of ≈ 0.066 recomputed independently, power-wave `0.44+0.08j` vs analytic `0.49397886+0.04177931j`). **Step 2** (`20260920T095318Z_PORT-20.log`, standard, `-n 2`, complex build, 201 s, 17 passed / 1 xfailed): on the two-torus fixture `‖S − z_to_s(Z)‖/‖S‖ = **9.417603e-17**` ≤ 1e-12 against `ports/circuit.py`'s independent implementation; reciprocity `‖S − Sᵀ‖/‖S‖ = 3.1121e-05` inside the **unmoved** 1e-3, passivity `‖S‖₂ = 0.861357` ≤ 1, `passivity_max_column_power_sum = 0.741120` ≤ 1; `PORT-1` step 4's mutual-ratio record reproduced untouched (raw miss 2.960e-11 / corrected 2.905e-11 vs 1e-6, read off `Z`) and the heuristic control still separates (max\|S_heur − S_field\| = 3.031724e-01, σ separation 0.138629 > 0.13). **Printed, predicted, not asserted** (rule (e)): tabulated-vs-implied \|S₂₁\| = **0.021598 vs 0.037654** (\|Δ\| 0.016698) against the known-issues reading ≈ 0.0216 vs ≈ 0.0377 — both predictions met. The lumped route's **byte-identity control** re-ran green and **digit-identical**: `20260920T095659Z_PORT-20.log`, 16 passed in 66.28 s, `‖S − Sᵀ‖/‖S‖ = 1.044255156e-14`, `‖Z − Zᵀ‖/‖Z‖ = 8.814400604e-05`, σ_max 0.999992805, class spreads 0.0553 / 0.0353 / 0.0214 % — every digit as in `20260914T004031Z_PORT-14-step3-port9-gate.log`. No band moved and no record was edited: the two S-derived records in `test_port_package_sparameters.py` (`RECORDED_PASSIVITY_MAX_SIGMA` 0.864809457 — now reading 0.861356894 — and `RECORDED_S_SYMMETRY_RATIO`) are records of the superseded quantity, so their test carries a **strict** `xfail` citing known-issues 2026-09-19 until step 3 re-records them. Remaining: **Step 1 (smoke, pure numpy — the closed form).** A synthetic passive reciprocal 2-port and 3-port with a known `Z` (a T-network and a random `R + jX` with `R` positive-definite): build the per-drive port states the route would see (`I_j` impressed, others open, `V = Z I`), run them through the route's assembly, and assert the reported `S` equals the analytic `(Z − z0)(Z + z0)⁻¹` at 1e-12. **Negative control (asserted):** the present per-port power-wave assembly on the same states misses that `S` by more than 1e-2 on the off-diagonal — so the test is red before the fix and says why. **Step 2 (standard, `-n 2`, the two-torus fixture).** `run_n_port_sparameter_sweep(gap_voltage_ports=…)` returns `S = z_to_s(Z)`; assert `‖S − z_to_s(Z)‖/‖S‖ ≤ 1e-12`, reciprocity and passivity at their **unmoved** bands, and `PORT-1` step 4's mutual-ratio record reproduced untouched (it is read from `Z`). The lumped-sheet route is asserted byte-identical by re-running `PORT-9` leg (d)'s 10 MHz 4×4 record. **Step 3 (records).** `EX-20`, `ans:3` and `PORT-1` step 4's S-derived records (`‖S‖₂`, the S table, any Touchstone fixture) are re-recorded under the corrected definition, each old value kept beside the new one in the module as the negative control (old misses new by > the record band). **Done-when (§4):** steps 1–3 executed by the implementer, the closed-form identity and both negative controls asserted, elapsed recorded, the known-issues entry retired, §2.1's `PORT-1` line gains "S on the current route is `z_to_s(Z)` since `PORT-20`". No band moves; a reciprocity or passivity red on the corrected `S` is a finding — stop, known-issues. | smoke (step 1), standard (steps 2–3) |
| `PORT-21` | **What the lumped-sheet port adds to `S₁₁`: the self-class feed systematic, measured on our side** — `ANS-4`'s order-matched comparison disagrees on the self class at 10 and 64 MHz and agrees on the couplings (known-issues 2026-09-19; verdict qualitative, numbers private); this chunk measures how much our own `S₁₁` moves under each port-model convention an independent code could legitimately differ in, so the private residual can be read against a public sensitivity table (opened 2026-09-19 by the weekly; **step 1 serial on nothing; step 2 serial on `xl` entries 7 and 11 having run**) | 🟡 **Step 1 CLOSED on `main` 2026-09-21 (09:30 slot, §9 item 22, step 1b) — every asserted anchor green in two windows, no band moved, no `src/`.** Module landed by path from `attempt/PORT-21-20260920T114000Z` with variant (c) **replaced** by (c′) = `c4_congruent_sheets=True` + `conductor_resolution = 0.5 × CONDUCTOR_RESOLUTION` (259 543 cells), read against its own **control′** = `c4_congruent_sheets=True` (116 118 cells, = the record); the uncongruent (c) numbers stay as a printed record with the three parked logs cited, its assert removed because the variant is replaced. **Asserted green:** control reproduces leg (d0)'s record at 10 MHz (band 1e-9) on 116 085 cells; (a) `PORT-14` step 3 residual **5.359129e-05** (0.054× `REDUCTION_BAND`, `20260921T094335Z_PORT-21.log:11519`); reciprocity / passivity / **0.5 %** C4 spread on every run incl. control′ and (c′) — (c′) spreads self/adj/opp **0.0403 / 0.0220 / 0.0228 %** (10 MHz, `…094335Z:11495`), **0.0204 / 0.0491 / 0.0263 %** (64, `:11516`), **0.0337 / 0.0837 / 0.0515 %** (128, `20260921T094925Z_PORT-21.log:5786`) — the pre-registered negative branch did **not** fire; knob floor cleared by ≥ 6.3e3× (c′ ≥ 1.538e4×). **Printed beside, not asserted:** control′ spreads 0.0475 / 0.0529 / 0.0366 % at 64 MHz and 0.0739 / 0.0822 / 0.0506 % at 128 MHz reproduce the records to every printed digit (`…094335Z:11510–11511`, `…094925Z:5780–5781`); **new at 10 MHz:** 0.0316 / 0.0244 / 0.0115 % (`…094335Z:11489`). **Table (printed, never asserted; `…094925Z:5795–5810`):** self-class `\|ΔS\|/\|S\|` (a) 3.411387e-02 / 1.552110e-02 / 6.327010e-03 (FALLS with f); (c′) **1.885271e-02 / 1.538416e-02 / 1.679098e-02** (non-monotonic; adjacent 6.025982e-03 / 6.669000e-03 / 1.332517e-02, opposite 4.185679e-03 / 9.536233e-03 / 1.761714e-02) at 10 / 64 / 128 MHz. (b) skipped and named. Windows: `20260921T094335Z_PORT-21.log` (10+64 MHz, Status 0, **341 s**, 5 passed) and `20260921T094925Z_PORT-21.log` (128 MHz, Status 0, **158 s**, 3 passed 2 skipped) — `-n 2`, complex, `timeout -k 30 590`, durable capture, `-s`; heavy by count, measured standard/heavy. No absolute `S₁₁`/`Z_in` at 10 or 64 MHz is claimed. Step 2 (the 09-26 weekly, private) reads this table. **Earlier record:** Step 1 attempted and measured 2026-09-20 (06:00 slot, second item) — the table is complete and printed, but the step's "every variant passes the imported gates" anchor is RED on variant (c), so step 1 does NOT close; the module is parked unmerged on `attempt/PORT-21-20260920T114000Z` and §9 item 13 is BLOCKED on a review ruling.** Green: the control reproduces leg (d0)'s gate record at **1.071e-10 … 2.568e-10** against the imported 1e-9 at all three frequencies on 116 085 cells (**no record drift on `main`**); variant (a) reproduces `PORT-14` step 3's registered residual at **5.359129e-05 = 0.054× `REDUCTION_BAND`**, in-run κ = 1.059204e-02 / 1.060762e-02 / 1.064828e-02 (the 64 MHz value reproducing `PORT-14` step 2d's 1.060762e-02); every variant cleared the 1e-6 knob-reaches-the-solve floor by ≥ 6.3e3× (smallest move 6.327e-03, largest 3.411e-02); reciprocity ≤ 1.79e-14 and passivity σ_max ≤ 0.999993 / max column power ≤ 0.8704 pass on **every** run including (c). Red: **variant (c)** (conductor-side grading halved, 8.0000e-04 m vs `CONDUCTOR_RESOLUTION` 1.6000e-03 m, re-meshing to **259 509 cells**) misses the imported **0.5 %** C4 class-spread band at all three frequencies — 10 MHz self **2.3607 %** / adj 1.2387 % / opp 1.0399 %; 64 MHz self **1.0508 %** / adj 0.9719 % / opp 0.9038 %; 128 MHz self **0.5553 %** / adj 0.6751 % / opp 0.6914 % — where the control and (a) sit at ≤ 0.1013 % on the same runs. **No band was moved, no `src/` touched, nothing diagnosed further.** Variant **(b)** is **skipped and named, not built**, as the row directs: `build_four_port_sweep` narrows every sheet with a module-level `GATED_WIDTH_FRACTION` and exposes no width-fraction parameter, so building the knob would be the generator change the step forbids. **The sensitivity table (printed, never asserted; `|ΔS|/|S|` per C4 class, variant against the control on the same fixture):** (a) self **3.411387e-02 / 1.552110e-02 / 6.327010e-03**, adjacent 1.002216e-02 / 8.605348e-03 / 6.344015e-03, opposite 9.459542e-03 / 7.093172e-03 / 3.992451e-03 at 10 / 64 / 128 MHz — the self-class move **FALLS** monotonically with frequency; (c) self **5.982326e-03 / 1.607415e-02 / 1.668383e-02**, adjacent 2.205190e-03 / 6.406405e-03 / 1.296737e-02, opposite 7.502789e-04 / 1.110089e-02 / 1.846200e-02 — it **RISES**. That opposite frequency trend between the two conventions is the table's readable content and is what step 2 (the weekly's, private) reads the residual against; **no absolute `S₁₁` figure is licensed here** (known-issues 2026-09-19) and nothing under `docs/private/` or `aed_results/` was opened in the slot. **Open question for the review (the unblock condition):** whether (c)'s anchor is re-scoped onto `c4_congruent_sheets=True` (`GEO-32`'s mechanism — the executor's *untested* reading is that the re-cut sheets on a 259 509-cell mesh are no longer C4-congruent, so the 0.5 % band belongs to the 116 085-cell gate cut and not to that one) or re-registered as "green on (a), red on (c) with the mesh-congruence cause named", closing on the table. The parked module runs as-is either way; no re-solve is needed to land it. **Logs:** `20260920T111725Z_PORT-21.log` (10+64 MHz, Status 1, 264 s), `20260920T112242Z_PORT-21.log` (128 MHz, Status 1, 127 s), `20260920T112548Z_PORT-21.log` (10+64 MHz re-run against the module **as parked** — rule (i) — Status 1, 263 s, and the window that supplied the 64 MHz (c) row the first short-circuited past); all `-n 2`, complex, `timeout -k 30 590`, durable capture, `-s`. *(Original step text below.)* ⬜ **Step 1 (heavy by count, `-n 2`, 116 085-cell F-small gate mesh, degree 1, factor reuse; ≈ 45 s per 4-drive solve from `PORT-15` step 3's measured 19.6 s + 25.3 s build).** At 10 / 64 / 128 MHz print the driven-column class entries under three variants, one knob each, against the gate record (reproduced first at rtol 1e-9 — the control): (a) sheet width told as `w/(1 + κ)` with the in-run κ (`PORT-14` step 3's opt-in); (b) full-width sheet `f = 1.0` against the gated interior half `f = 0.5`; (c) the port-box interior's conductor-side grading halved (the stub-face fringe). A variant whose knob the generator does not already expose is skipped and named, not built — this step adds no `src/` surface. **Asserted (identity):** every variant still passes the imported reciprocity / passivity / C4 gates, and variant (a) reproduces `PORT-14` step 3's registered residual. **Printed, never asserted:** `\|ΔS\|/\|S\|` per class per variant per frequency — the sensitivity table — and whether each variant's self-class move **falls with frequency** (the signature the private residual has). 🧪 by the §3 rule unless the identities are what a review counts; closes nothing absolute. **Step 2 (weekly, private).** The weekly reads the table against the private residual and the 3e / 3g `h`-convergence statements and rules: a variant whose self-class move matches the residual in size and frequency trend is named the feed systematic and written into §2.2 with its public size; none matching ⇒ the disagreement stays open against `ANS-6`'s PEC column. **Done-when (§4):** step 1's identities asserted and the table logged with elapsed; step 2's ruling written in §10. Never tunes a port parameter toward the external code — variants are conventions, fixed before the private file is opened. **Step 1 attempted 2026-09-20 (06:00 slot, parked `attempt/PORT-21-20260920T114000Z`; logs `20260920T111725Z` / `…112242Z` / `…112548Z_PORT-21.log`):** control reproduces the gate record at 1.071e-10…2.568e-10 (band 1e-9); (a) reproduces `PORT-14` step 3's residual at 5.359129e-05; self-class `|ΔS|/|S|` for (a) 3.411387e-02 / 1.552110e-02 / 6.327010e-03 at 10 / 64 / 128 MHz (falls with f); (b) skipped and named (no width-fraction parameter). **Record (2026-09-21 review ruling):** variant (c) as first built — halved conductor grading *without* the congruent cut, 259 509 cells — reads C4 class spreads 2.3607 / 1.2387 / 1.0399 % (10 MHz), 1.0508 / 0.9719 / 0.9038 % (64), 0.5553 / 0.6751 / 0.6914 % (128) against the imported 0.5 % band: a spread up to 4× the move it was to measure (5.982326e-03 / 1.607415e-02 / 1.668383e-02), so that row is mesh asymmetry (`GEO-30`…`-32`'s mechanism), **not** a feed sensitivity. The band is unmoved; **step 1b (§9 item 22)** rebuilds (c) on `c4_congruent_sheets=True` against its own congruent control′, with a pre-registered negative branch. | heavy |
| `PORT-22` | **Find the tuned birdcage's resonance by a driven sweep — the fallback to `TH-17`'s eigen route and the way an HFSS user tunes** — in-model capacitor sheets at `PORT-15` step 3's `C_tuned` on P2..P4, P1 driven, `Z_in(f)` on a discrete grid; the circuit layer predicts the same curve from the *untuned* 4×4 at each grid frequency, so the comparison is an identity, not a fit (opened 2026-09-19 by the weekly; §10 tuned-birdcage chain step 5′; serial on `PORT-15` ✅; independent of `TH-17` step 1b) | ✅ **Step 1 closed 2026-09-20 (06:00 implementer slot) — (i), (ii), (iii) and the negative control all asserted green on the grid as written, in two windows, no band moved and no `src/` touched.** New `tests/validation/test_port22_driven_sweep_resonance.py` (5 tests, `@complex_only`, gated on `FEM_EM_PORT22_FREQUENCIES_MHZ` so the default collection is 5 skips in 2.9 s — `main`'s CI time is unchanged); every constant and fixture imported (`S_64MHZ_EPS0_RECORD`, `tuning_sweep`, `select_c_tuned`, `tuned_input`, `_terminated_kept_network`, `_capacitor_impedance`, `_residual`, `TUNING_TERMINATED_INDICES` from `test_port_circuit_layer_field.py`; `REDUCTION_BAND`, `RECORD_RANK_WIDTH`, `STEP1_CELL_RECORD`, `STEP3_REGISTERED_FREQUENCY_HZ` from `test_port_lumped_rlc_termination.py`; `build_four_port_sweep`, `_solve_driven`, `REFERENCE_IMPEDANCE_OHM`, `ports.shares.terminal_form_deficit`), nothing restated — `C_tuned` is **recomputed** in-run by `PORT-15` step 3's own `tuning_sweep`/`select_c_tuned` at **1.556993028375804e-11 F** against step 3's printed 1.557e-11. Six solves per frequency on one mesh build per window (κ by `PORT-14` step 3's route — one uncorrected P1 solve + pooled `terminal_form_deficit`; the untuned matched 4×4 at that κ; the in-model tuned single drive with `Z_C(f, C_tuned)` on P2..P4), 116 085 cells asserted against `STEP1_CELL_RECORD` in both windows. **Windows, `-n 2`, complex, `timeout -k 30 590`, durable capture, `-s`:** `20260920T110503Z_PORT-22.log` (44–64 MHz) Status 0, **191 s**, 4 passed 1 skipped, `[capture] rc=0`; `20260920T110833Z_PORT-22.log` (68–84 MHz + anchor (iii)) Status 0, **167 s**, 3 passed 2 skipped, `[capture] rc=0` — **heavy by ceiling, measured standard**; per-frequency readings persisted to the gitignored `logs/port22/`, so (iii) asserts in the window that completes the 11-point grid and skips, naming what is missing, in the earlier one. **(i) 64 MHz (`:2136–2139`):** tuned `S₁₁` residual **8.256069e-05** against the imported `REDUCTION_BAND` 1e-3 (0.083× band), reproducing step 3's 8.26e-05; printed beside it, in-run κ(64) = **1.060762155e-02** against `PORT-14` step 2d's 1.060762e-02, `|S₁₁|` 0.761413303 vs step 3's 0.761, `R_in` 6.772592686 Ω vs 6.77 Ω. **(ii) all 11 grid points (`:2144–2149`, `…110833Z:2083–2087`):** worst residual **8.256069e-05** (at 64 MHz), rising monotonically 5.779018e-05 (44 MHz) → 8.256069e-05 (64 MHz) then falling to 7.255190e-05 (84 MHz) — every point ≤ 0.083× band; κ in-run per frequency drifts 1.059954e-02 → 1.061802e-02, **0.17 % across the band**. **(iii) (`…110833Z:2094–2106`):** `Im Z_in` −3.462456996e+01 Ω at 44 MHz rising monotonically to +2.559855276e+01 Ω at 84 MHz — **exactly one sign change, in [60, 64] MHz**, the bracket holding 64 MHz. **Negative control (asserted; `:2153`):** the circuit prediction at `0.5 × C_tuned` gives `|S₁₁|` **0.846071753** (step 3's 0.846) and misses the in-model curve by **1.116902 = 1116.9× the band** against the 10× asked — four orders of separation from the tuned prediction's 8.26e-05. **Printed, never gated:** interpolated zero of `Im Z_in` **f₀ = 63.998619 MHz**, `R_in(f₀)` = **6.772516 Ω**, `d(Im Z)/df` = 1.467392 Ω/MHz, loaded **Q = 6.9332**; no `TH-17` eigenvalue exists to print beside it (step 1b (iii) is blocked, §9 item 10). **Not claimed:** one fixture, degree 1, series resonance — no absolute `S₁₁` / `Z_in` at 10 or 64 MHz (known-issues 2026-09-19, `PORT-21`), no mode-spectrum claim (`TH-17`'s), no match, no human scale. *(Original step text below.)* ⬜ **Step 1 (heavy, `-n 2`, 116 085-cell mesh, degree 1).** Grid: 11 frequencies 44 → 84 MHz in 4 MHz steps (64 MHz included so step 3's record is a grid point). Per frequency two solves sets on one mesh build: the untuned matched 4×4 (factor reuse, 4 drives) and the in-model tuned single drive — ≈ 45 s + 20 s from `PORT-15` step 3's measured times ⇒ ≈ 12 min, split into two windows of ≤ 6 frequencies if the first overruns 590 s. **Asserted:** (i) at 64 MHz both reproduce `PORT-15` step 3's records (`C_tuned`, tuned `S₁₁` residual ≤ the imported `REDUCTION_BAND` 1e-3); (ii) at every grid frequency the circuit-reduced `S₁₁` from that frequency's untuned 4×4 equals the in-model tuned `S₁₁` within the same band, κ-corrected widths with κ computed in-run per frequency (`PORT-14` step 3); (iii) `Im Z_in(f)` changes sign exactly once on the grid, in the bracket containing 64 MHz. **Negative control (asserted):** the circuit prediction with `0.5 × C_tuned` misses the in-model curve by > 10× the band at 64 MHz (`PORT-15` step 3's 0.846 vs 0.761 record says it must). **Printed:** the interpolated zero of `Im Z_in`, `R_in` there, the loaded Q from the `Im Z` slope, beside `TH-17`'s eigenvalue if one exists by then. **Done-when (§4):** (i)–(iii) and the control asserted by the implementer, elapsed recorded; §2.1 gains "the F-small tuned resonance is located by a driven sweep consistent with the circuit layer across 44–84 MHz" — still one fixture, degree 1, series resonance, no absolute `S₁₁` (known-issues 2026-09-19), no mode-spectrum claim (`TH-17`'s). | heavy |
| `PORT-23` | **The circuit layer through `scikit-rf`, gated against the raw (C2) reduction** — the HFSS + Circuit split with a vetted engine: the field solve produces the 50 Ω N-port under MPI, the netlist is prepared in our code, `scikit-rf` terminates / cascades it on one process (operator directive 2026-09-20; serial on `OPS-60`) | 🟡 **Step 1 ✅ 2026-09-23 (04:30 slot, §9 item 34; the chunk stays open for step 2).** Additive `ports/circuit_skrf.py` (`network_from_records`, `terminate` via an `skrf.circuit.Circuit` netlist — `SeriesImpedance`→`Ground` per terminated port, `Circuit.Port` per kept port in ascending order, explicit `port_map`; no reflection coefficient computed in our code) and `tests/validation/test_port_circuit_skrf.py` (every record / band imported from the `PORT-14` / `PORT-15` modules; new: `IDENTITY_BAND` 1e-12, and `PORT-15`'s in-model tuned `S₁₁` stored as a cited record from `20260914T020419Z_PORT-15.log:3732`). `20260923T093456Z_PORT-23.log`, Status 0, **8 s**, `-n 2`, 6 passed per rank (`:93`, `:96`). **(a)** 64 MHz at `C_tuned` = 1.556993028375804e-11 F: max\|Δ\| skrf vs (C2) 3.511e-16 (1×1) / 1.415e-16 (2×2) ≤ 1e-12 (`:56–62`); **(b)** 10 MHz, P1 terminated, C / L / R ≤ 1.388e-16 (`:66–69`); **(c)** the skrf sweep's single zero equals `C_tuned` (\|ratio−1\| 0, \|Im Z\|/\|Z\| 1.585e-15 ≤ 1e-6); tuned `S₁₁` vs `PORT-15`'s in-model record 8.256e-05 ≤ `REDUCTION_BAND` 1e-3 (`:74–78`); **(d)** 50→75→50 Ω round trip 2.122e-15, power vs traveling 1.433e-15, skrf 75 Ω vs raw `z_to_s(s_to_z)` 9.421e-16 (`:82–85`; the third check added by the executor at the same band to cover the `superposition.py` convention clause). **Negative control (asserted), 2×2-kept per the 09-23 ruling:** a P2↔P3 swapped port map misses (C2) by 2.019e-01 = 201.9× the 1e-3 floor; class gap \|S₁₂−S₁₃\| 1.596e-01 above the 1e-2 stop (`:88–90`). API note for step 2: in 2.1.0 `Circuit` lives at `skrf.circuit.Circuit` (`skrf.Circuit` raises; `20260923T093252Z_PORT-23-api-probe.log`). Scope: identities on stored matrices; the printed `Z_in` is not an absolute claim (`PORT-21`). History: **Why a library, and why the raw layer stays:** the raw (C2) reduction in `ports/circuit.py` is forty lines pinned to a closed form and is what the `PORT-14`/`PORT-15` gates run through; it stays as the *control*. `scikit-rf` is the product: Touchstone in, connection-list netlist, termination / cascade / de-embed / renormalise native, the same object an HFSS Circuit user builds — so `ANS-7` compares like with like and matching networks, baluns and cable models come free. Conventions (power vs pseudo waves, port order, `z0` renormalisation — the `PORT-20` class of bug) are checked once, here, against the raw layer. **Step 1 — the identity.** Additive `ports/circuit_skrf.py`: `network_from_records(s, z0, f)` builds an `skrf.Network` from a stored 4×4 (the `PORT-15` module records at 64 and 10 MHz, imported); `terminate(network, {port: Z})` builds an `skrf.Circuit` of that network plus lumped impedances on the terminated ports and returns the kept-port S. **Gates (asserted):** (a) `terminate` vs `reduce_terminated_ports` at `C_tuned` on the stored 64 MHz 4×4 (the `PORT-15` step 3 sweep, imported), 1×1 and 2×2 kept, `max|Δ| ≤ 1e-12` — an identity, the band is machine precision; (b) the same at 10 MHz with the `PORT-15` step 2 terminations (the reduction floor); (c) the tuning zero found by sweeping `C` through `terminate` reproduces `C_tuned` to `TUNING_IM_Z_RTOL` (imported) — the tuned `S₁₁` then reproduces `PORT-15`'s in-model record at the imported `REDUCTION_BAND`; (d) **convention control:** renormalising the network to a different real `z0` (75 Ω) and back returns the input to 1e-12, and `s_def='power'` vs `'traveling'` agree for real `z0` to 1e-12 — asserts the library's wave convention is the one `superposition.py` documents. **Negative control (asserted):** a deliberately mis-ordered port map (ports 2 and 3 swapped in the netlist) breaks gate (a) by ≥ 1e-3 — port order is the silent failure a netlist invites, and the control shows the gate sees it. **Printed, never gated:** the kept-port `Z_in` from both engines, the `skrf` version. **Done-when:** (a)–(d) and the control green through the harness at `-n 2` (numpy + stored records; no field solve), elapsed recorded ⇒ `PORT-23` ✅ and the plan's circuit-layer sentence in §2.1 names `scikit-rf` as the engine with the raw reduction as its control. **Step 2 (opened at closure, not now):** the `ANS-7` interface — export the tuned birdcage as Touchstone + a text netlist that Ansys Circuit and `skrf` both consume; the `TH-17`/`PORT-22` tuned fixture as the case. **Not in scope:** nonlinear or time-domain elements (that would be `ngspice`, and nothing in the plan needs it). | standard (`-n 2`, stored matrices; seconds) |

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


**`PORT-14` narrative** — moved byte for byte to `docs/planning/chunks/PORT-14.md` (`OPS-47`).

**`PORT-15` — the circuit layer (HFSS + Circuit)** ✅ *(closed 2026-09-14
02:07Z on gate (i) + the tuned `S₁₁`; result block written by the 2026-09-19
weekly, full narrative in `docs/planning/plan-archive.md`, entry «§7 PORT-15
full narrative — archived 2026-09-19 (weekly review)»; row history stays in
`docs/planning/chunks/PORT-15.md`.)* Digits in the §7 table row
(`20260914T010448Z_PORT-15.log`, `20260914T020419Z_PORT-15.log`). **Live
carry-forwards:** gate (ii), the 32-port mode spectrum, is `TH-17`'s and is
not claimed; "tuned" means series resonance on one F-small 4-leg fixture at
64 MHz, not matched.

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
| `WF-7` | SAR10g hotspot identification | ✅ (**step 3 DONE 2026-09-25 (09:30 slot, §9 item 39, chain H5): the 10 g SAR hotspot located at human scale, C16- and mirror-gated.** New `tests/validation/test_wf7_f_human_sar10g_hotspot.py` (`FEM_EM_WF7_STEP3=1`) + additive `phantom_resolution=None` keyword on `_build_f_human` (`None` ⇒ no new generator key); no `src/`. `20260925T093315Z_WF-7-step3.log`, Status 0, 352 s, heavy, `-n 8`, 4 passed (`:11666`). Refined phantom 0.0075 m: **537 546 cells, 22 594 phantom cells** (printed beside 504 642, not asserted — no record), build 133.33 s (`:10468`); measured phantom (allreduced tag-3 vertex bbox) centre (0, 7.2e-9, 0) m, R = 64.2857 mm, H/2 = 85.7143 mm; 10 g ball a = 13.3650 mm = 3.56 phantom h across (`:11559`). Nine-ball lattice at az_ref 11.25°, ccw drive: **c\* = r 45 mm, z = z_c**, SAR₁₀g 2.0858e-04 W/kg (ball masses 9.984–10.024 g; the ±50 mm rows peak at 1.44e-04, `:11589–11598`, `:11614`). (i) coverage identity, ball radius 108.1429 mm (< 140 mm conductor clearance, asserted): power rel **9.592e-14**, mass rel **1.297e-13** ≤ `EXACT_IDENTITY_RTOL` 1e-10 (`:11617`); (ii) **C16 worst 0.4904 %** (R_7; range 0.0098–0.4904 %) ≤ `C4_COVARIANCE_BAND` 5 % (`:11599–11615`); (iii) **mirror 0.0502 %** ≤ 5 % (`:11616`) — *disclosed: c\* lies on the az_ref ray, which is the mirror plane, so `_mirror_xy(c*)` = c\* (identical ball mass 10.001116 g, `:11584`); the identity read here is cw SAR at c\* vs ccw SAR at c\*, the pre-registered one, not an off-plane reflection*; (iv) all 30 balls contained 1 mm clear (asserted). Negative control (*predicted* ≫ 5 %, printed, never asserted): single-drive P17 SAR₁₀g at c\* and C4 images R_4/R_8/R_12 68.11 / 96.40 / 70.03 %, spread 96.40 % = 196.6× the ccw worst — as predicted (`:11619`). Printed only: whole-phantom mean SAR (ccw) 1.7356e-04 W/kg (`:11618`); step 2's `|B₁⁺|` on the refined mesh C16 worst 0.0513 %, mirror 0.0456 %, **215 / 215** valid sample points (the 38-point question), identity 3.475e-16 (`:11620`); PRICE build 133.33 s, sweep+case 93.86 s, SAR phase 120.40 s (30 balls, 2.5–4.7 s each — the 25 s STOP rule did not fire), 348.02 s wall, 19.052 GiB summed `ru_maxrss` (`:11621`). Rule (a): the step-2 module re-run with the keyword unset, 5 passed, 507 266 cells, C16 worst 0.1495 % reproduced, 210 s (`20260925T093918Z_WF-7-step3-ruleA-step2.log:10480`, `:11566`, `:11609`). *One phantom, one fixture, 64 MHz, degree 1 — a SAR location and two symmetry identities; no C95.3, compliance or absolute SAR claim; carries the 5.50 % order caveat (step 0b).*) (**step 2, 2026-09-23 (04:30 slot, §9 item 36, chain H4): `|B₁⁺|` C16 gated at human scale.** New `tests/validation/test_wf7_f_human_b1_quadrature.py` (`FEM_EM_WF7_STEP2=1`) + additive `built=None, cell_record=None` keywords and four additive return keys (`result`, `points`, `mask`, `az_ref`, needed by (vi) and the P17 control) on `_build_ring_quadrature_case()`; no `src/`. `20260923T095104Z_WF-7-step2.log`, Status 0, 227 s, `-n 8`, 5 passed. On the F-human fixture at 64 MHz, degree 1, 32-port ccw quadrature with `POST-6` step 3's weights: (i) 507 266 cells (step 1's count reproduced), +0.52 % to the 504 642 record inside `CELL_COUNT_BAND` (`:10480`); (ii) 16 ports per ring on the 22.5° grid (`_ring_quadrature_slots` asserts; reference azimuth 11.250000°, `:11550`); (iii) worst C16 image of `|B₁⁺|_ccw` **0.1495 %** (R_8; range 0.0978–0.1495 %) ≤ `C4_COVARIANCE_BAND` 5 % (`:11551–11566`); (iv) mirror `|B₁⁻|_cw(Mx)` vs `|B₁⁺|_ccw(x)` **0.1634 %** ≤ 5 % (`:11567`); (v) `PORT-16` exact discrete identity on the superposed field 2.316e-16 ≤ 1e-6 (`:11568`); (vi) unit weight e_P17 deviation 0.000e+00 ≤ 1e-12 (`:11571`). Predicted controls, printed only: cw mis-paired 99.2969 % vs predicted 99.3438 % (`:11569`); single-drive P17 worst C16 spread 33.3425 %, 223× the ccw worst (`:11572`). Printed: **38 / 38 sample points — below the 50-point `MIN_SAMPLE_POINTS` floor `POST-6` step 3 asserts on its own fixture, not gated here (review to rule)**; `S[P17,P17]` 0.407423+0.344417j = step 1's digits (`:11573`); PRICE build 134.02 s, sweep 66.20 s, 223.82 s wall, 17.713 GiB summed `ru_maxrss` (`:11574`). Rule (a): `POST-6` step 3 re-run 17 / 17 green, 0.8102 % / 0.6769 % reproduced, 172 s (`20260923T095500Z_POST-6-step3-rerun-WF-7-step2.log:13670–13674`). *C16 invariance of `|B₁⁺|` at human scale only — no homogeneity, absolute `B₁⁺`, SAR or Larmor-accuracy claim.* *Self-consistency only; degree 1 at human scale carries the weekly's 5.50 % order caveat (`WF-7` step 0b, 2026-09-19).* H5 (step 3) becomes queueable. **Ruling on the 38 sample points (2026-09-25 03:00 review): step 2 stands as recorded.** `MIN_SAMPLE_POINTS` = 50 (`tests/validation/test_birdcage_b1_plus_map.py:135`) belongs to `POST-6`'s fixture. Its sample cylinder is absolute (radius 20 mm, half-height 20 mm, `:125–126`) and does not scale with the phantom, so on F-human's 15 mm phantom cells it holds 38 centroids. Step 2's Done-when (this row) names the band, the two identities and the unit weight, not the floor, and the count is disclosed. Not demoted. Step 3 runs on a refined phantom and reprints the same C16 reading on its denser point set as a record.) (**Step 3 (chain H5; §9 item 39, written 2026-09-25 review under rule (4)) — Done-when (added by that review, rule (j)):** on the F-human fixture at 64 MHz, degree 1, 32-port ccw quadrature (step 2's superposition), with the phantom refined to `phantom_resolution` = 0.0075 m (the 10 g ball, a = 13.365 mm at ρ = 1000, ≈ 3.6 phantom cells across — the regime `MAT-4` step 4 gated 10 g at on F-small; at the default 15 mm it is ≈ 1.8, the regime whose 1 g column missed 5 %), all asserted green in one logged window with elapsed: (i) `MAT-4`'s **coverage identity** — one ball enclosing the whole phantom (centre and radius from the allreduced tag-3 bounding box; radius just over the circumradius and clear of the conductor), ρ = 1000 on tag 3 and 0 elsewhere, reproduces `mean_sar(…, subdomain_ids=PHANTOM_CELL_TAG)`'s dissipated power and ρ × the meshed phantom volume within the imported `EXACT_IDENTITY_RTOL` (1e-10); (ii) the **10 g hotspot** — the argmax of `mass_averaged_sar` over a fixed candidate lattice — and its fifteen **C16 images** within the imported `C4_COVARIANCE_BAND` (5 %); (iii) the **mirror identity** — the cw drive's 10 g SAR at the mirrored hotspot vs the ccw drive's at the hotspot — within the same band; (iv) every ball's containment in the phantom. The location table is printed ⇒ **`WF-7` 🟡 → ✅** at the stated grain: *one phantom, one fixture, degree 1, the 5.50 % order caveat; a SAR location and a symmetry identity, not a C95.3 or compliance figure.*) (step 1, 2026-09-21: the F-human degree-1 32×32's identities gated — self-consistency only, see the step-1 record at the end of this cell) Step 0 (cost probe, 2026-09-13): one degree-1 single-drive lumped-sheet solve on the F-human rung (longitudinal ring sheets, 507 266 cells, +0.52 % vs `GEO-25`'s transverse record) at 64 MHz, `-n 8` — 607 039 unknowns, solve 37 s, mesh build 123 s, summed `ru_maxrss` 10.93 GiB (`20260913T190102Z_WF-7-step0.log:10419–10427`, 178 s); below the predicted 11–33 GiB / 3–8 min bracket. A measurement for the XXL commissioning, no physics claim. **Step 0b queued 2026-09-13 (operator, interactive) for the Saturday 2026-09-19 02:00 `xxl` window (`docs/testing/xl-pending.md` entry 1; `docs/testing/xxl-queue.env`):** the same probe with the new `FEM_EM_WF7_DEGREE=2` knob (unset is byte-identical), degree-1 control first in the same window at `-n 16`, against `fem-em-solver-xxl`. Readout, record only: `S_driven` at degree 1 and 2 on the same F-human mesh and `|S₂ − S₁|/|S₁|` — the human-scale order sensitivity — plus the degree-2 price (predicted ≈ 3.2 M unknowns, ≈ 235 GiB, ≈ 17 min from 2d's point; brackets 150–350 GiB / 10–60 min printed). Decision rule for the 09-19 weekly pre-registered in the pending file: same class as F-small's 64 MHz order move ⇒ degree 2 is the production order at human scale and this is its price; an order of magnitude smaller ⇒ degree 1 suffices for human-scale S; does not finish ⇒ the price is the finding and `TH-16` moves up. Nothing asserted beyond the imported cell band. **Step 0c (opened 2026-09-16 review, §9 item 1 + `xl-pending.md` entry 6):** the probe gains `FEM_EM_WF7_PORTS` (unset = byte-identical; `k` or `all` = the first `k` / every ring port driven in turn, each column's fields dropped), proved at heavy tier by the flag-off control (`S_driven` = step 0's `0.407423+0.344417j`) and a two-drive reciprocity assert; then the XL cost probe — the full 32-port degree-1 set on the F-human mesh at `-n 16`, readout the price plus the 32×32's reciprocity / passivity / C16 spreads printed beside `PORT-13`'s bands, nothing asserted. **The knob landed 2026-09-16 (heavy, `-n 8`, two windows): (a) flag-off control — the knob unset, the probe reproduces step 0's printed `S_driven` digits `0.407423+0.344417j` exactly, cells 507 266 (+0.52 %, inside the imported band), solve 31.71 s, summed `ru_maxrss` 10.93 GiB, 158 s window (`20260916T093301Z_WF-7-step0c.log:10425–10430`); (b) `FEM_EM_WF7_PORTS=2` — two drives P17, P18, the 2×2's reciprocity ratio **9.767e-16** against the imported `RECIPROCITY_BAND` 1e-3 and drive 2's `S_driven` 0.407959+0.343115j differing from drive 1's by 1.407e-03 > 1e-6, 155 s window (`20260916T093548Z_WF-7-step0c.log:10431–10438`). Priced for the XL window: the first drive factorises (27.71 s), the second back-substitutes the held MUMPS factor (`solve_kind` `held`, **0.59 s**, `PORT-19` step 3), so 32 drives extrapolate to ≈ 2 min mesh + 28 s + 31 × 0.6 s ≈ 3.5 min at `-n 8`; summed `ru_maxrss` moved 10.892 → 11.082 GiB over the second drive (+0.19 GiB per retained column). Negative control (*predicted*, printed, never asserted): the 2×2's `σ_max` 0.709401 ≤ `COLUMN_PASSIVITY_CEILING` 1 — as predicted; class spreads printed (|S_jj| spread 8.0579e-04, full-column Σ|S_ij|² 0.895804 / 0.895395). No F-human `S` claim, no band moved.** *The 32-port XL cost probe was queued by the 2026-09-18 03:00 review for Monday 2026-09-21 02:00 (`docs/testing/xl-queue.d/20260921-WF-7-step0c.env`, `xl-pending.md` entry 6).* **Step 0b ran 2026-09-19 02:00 (`xxl`, cron, no session) — a record, 🧪, banked by the 03:00 review from a `log-pathologist` reading** (`20260919T070008Z_WF-7-step0b.log`; both legs rc 0, Status 0, 673 s, `memory.peak` 106.1 GiB): degree 1 at `-n 16` reproduces step 0's `S_driven` digits (printed, not asserted at this width; 607 039 unknowns, 24.61 s); **degree 2 is 3 256 418 unknowns, 347.56 s, 107.9 GiB summed** — a third of the predicted price on both axes, so a degree-2 F-human drive is `xl`-sized; `S_driven(P17)` `0.436656+0.346994j`, i.e. `|S₂ − S₁|/|S₁|` = **5.50 %** (the review's arithmetic from two printed values; nothing about the degree-2 `S` is asserted). Unattributed and for the weekly: the printed power-accounting residual is 1.104e-02 at degree 2 against 4.187e-03 at degree 1. The decision rule's branch (c) is excluded; (a)-vs-(b) is the 2026-09-19 weekly's. **Step 0d** (daily licence, priced-family variant: degree 2 at the full 32-port set) is queued for the 2026-09-26 `xxl` window (`xl-pending.md` entry 9). Probe label defects from this log: `OPS-52`. **Step 0c RUN 2026-09-21 (`xl`, chain H1; `20260921T070008Z_WF-7-step0c.log`, Status 0, 228 s, `log-pathologist` CONFIRMED countable):** the degree-1 32-drive set is one factorisation (24.73 s) + 31 held back-substitutions (0.40–0.57 s), 607 039 unknowns, cumulative 224.19 s, summed `ru_maxrss` 13.842 GiB, `memory.peak` 11.96 GiB at `-n 16`; full 32×32 reciprocity **1.084e-14 ≤ the imported 1e-3, asserted**; σ_max 0.999915, `|S_jj|` spread 1.7891e-03, column sums 0.895287–0.896108, terminal residual 4.061e-03–4.624e-03 — printed only. ⇒ the F-human degree-1 32×32 is a **heavy-tier** job. **Step 1 (chain H3; §9 item 21, written 2026-09-21 review under rule (4)) — Done-when (added by that review, rule (j)):** on the F-human fixture at 64 MHz, degree 1, all 32 drives: the cell band, reciprocity ≤ `RECIPROCITY_BAND`, σ_max ≤ `MATRIX_PASSIVITY_CEILING`, exactly 18 C16 × mirror classes with worst spread ≤ `OPPOSITE_SPREAD_BAND`, `PORT-16`'s exact discrete power identity ≤ `DISCRETE_IDENTITY_RTOL` on the driven columns, and the mesh-level mis-paired-orientation control, all imported and asserted green in one logged window with elapsed ⇒ `WF-7` 🧪 → 🟡. *Self-consistency only; degree 1 at human scale carries the weekly's 5.50 % order caveat (`WF-7` step 0b, 2026-09-19).* **Step 1 DONE 2026-09-21 (09:30 slot, heavy, `-n 8`, one window 372 s, Status 0; new `tests/validation/test_wf7_f_human_ring_matrix.py`, no `src/`; `20260921T093429Z_WF-7-step1.log`):** (i) 507 266 cells, +5.200e-03 vs 504 642 inside `CELL_COUNT_BAND` 0.01 (`:10480`); 1 factorisation (33.65 s) + 31 held (0.51–0.70 s), summed `ru_maxrss` 11.012 GiB (`:10484–10516`); (ii) reciprocity **9.200731e-15** ≤ 1e-3 (`:10518`); (iii) σ_max **0.999914648** ≤ `MATRIX_PASSIVITY_CEILING` 1.0, margin +8.535e-05 (`:10519`); (iv) **18** C16 × mirror classes from measured azimuths / sheet-centre z, worst azimuth residual 5.684e-14°, worst spread **3.6997 %** (other ring, 2 steps) ≤ 5 % — first measurement on this fixture (`:10520–10539`); (v) exact discrete power identity max **2.835e-15** ≤ 1e-6 on **drives 1, 9, 17, 25 only** — the first identity evaluation cost 17.31 s > the item's 15 s stop rule, so the item's own fallback ran (`:10481–10483`, `:10540`); P_src,exact > 0 on each. Controls: *asserted* default-orientation build (504 642 cells, 132.90 s, no solve) max sheet extent along φ̂ 2.816e-17 m < 1e-12 while the longitudinal chord / min extent is 1.716154e-02 m (`:20224`); *asserted* P17 column × 1.01 lifts the ratio to 2.064468e-03 = 2.244e+11× the measured (bar 1e6×, `:10542`); *predicted, printed* 2.064468e-03 vs the 2e-3 `MATRIX_CONTROL_MARGIN` bar — at/above, inside the review's 1.5–2.1e-3 prediction (`:10543`). Printed only: terminal residual 4.061e-03–4.624e-03 beside pooled C/terminal−1 4.591e-03–4.689e-03; column sums 0.895287–0.896108; S_driven(P17) 0.407423+0.344417j = the step-0 record digits at `-n 8` (`:10541`). ⇒ `WF-7` 🧪 → 🟡. **Self-consistency identities on one fixture at degree 1 — no field, B₁⁺, SAR or absolute S; degree 1 at human scale carries the weekly's 5.50 % order caveat (`WF-7` step 0b, 2026-09-19).** **Step 2 (chain H4; §9 item 36, written 2026-09-23 review under rule (4)) — Done-when (added by that review, rule (j)):** on the same F-human fixture at 64 MHz, degree 1, the 32-port ccw quadrature drive superposed through `superpose_drives` with `POST-6` step 3's weights: the worst of the fifteen C16 images of the CG1 `|B₁⁺|_ccw` map, the mirror identity `|B₁⁻|_cw(Mx)` vs `|B₁⁺|_ccw(x)` — both ≤ the imported `C4_COVARIANCE_BAND` — `PORT-16`'s exact discrete identity on the superposed field ≤ `DISCRETE_IDENTITY_RTOL`, and the unit-weight identity (`UNIT_WEIGHT_CONTROL_RTOL`), asserted green in one logged window with elapsed, plus the rule-(a) re-run of `POST-6` step 3 green ⇒ the row records step 2; `WF-7` stays 🟡 (step 3, the 10 g hotspot, is the chunk's title). *C16 invariance of `|B₁⁺|` at human scale only — no homogeneity, absolute `B₁⁺`, SAR or Larmor-accuracy claim; carries the 5.50 % order caveat.* | heavy; step 0b **`xxl`** (measured 673 s / 106.1 GiB, 2026-09-19); step 0c **`xl`** (cost probe); step 0d **`xxl`** |
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

**`WF-6` narrative** — moved byte for byte to `docs/planning/chunks/WF-6.md` (`OPS-47`).

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
| `EX-54` | **The birdcage as a PEC hole in ParaView — the 4×4 and the field on the conductor-free mesh** (`examples/ports/14_birdcage_pec_hole_ports.py` + same-stem guide; `example-runner`) | ✅ **DONE 2026-09-14 02:31Z.** `_hole_rung(FREQUENCY_HZ)` at 10 MHz, imported unmodified except five additive return keys (`mesh`, `cell_tags`, `wall_facet_tags`, `sheet_facet_tags`, `fields` — nothing renamed/removed; gate module re-run green in-slot, 6 passed / 4 skipped (solid control not requested), 32.70 s, `20260914T023104Z_EX-54-th15-rerun.log:961`). All three imported gates plus the power identity asserted and green in the example: reciprocity 1.508e-14 (band 1e-3), σ_max 0.999994234 (band 1 + 1e-9), class spreads self 0.0190 %/adjacent 0.0094 %/opposite 0.0059 % (band 0.5 %), power rel dev 1.327e-10 (band 1e-3) — `20260914T023145Z_EX-54.log:897`. Printed only (no pre-registered band): the hole's 4×4 beside `PORT-11`'s solid σ = 800 S/m 10 MHz record (`LEG_D_S_MATRIX_10MHZ`), `max\|ΔS\|` per C4 class self 9.769e-02 / adjacent 2.484e-02 / opposite 4.828e-02 (`:908`); the cavity wall's (tag 401) `\|n × E\|` reads 2.989e-16 over 4.052772e-02 m² — machine-zero, confirming the PEC enforcement (`:910`). 80 181 cells, 31.8 s total at `-n 2` (`:895,914`). Combined XDMF `examples/ports/paraview_output/ports_14_birdcage_pec_hole_ports_combined.xdmf` (`CellTags`, `E_magnitude` DG0, `facet_tags` grid with tag 401). Census: pre `dead=0 guide=0 stale=0 exit=0` (`20260914T022309Z_EX-54.log:39`), post `dead=0 guide=0 stale=0 exit=0` (`20260914T023230Z_EX-54-census-post.log:39`). No copper, Larmor-accuracy or `TH-14` claim. | standard (host-runner, measured 34 s example / 32.70 s gate rerun) |
| `EX-55` | **The 32-port ccw quadrature drive on the 16-leg birdcage in ParaView** (`examples/ports/15_birdcage_sixteen_leg_quadrature_b1.py` + guide; `example-runner`) | ✅ *(leading glyph corrected 2026-09-20 03:00 review — the row closed 2026-09-14 and was audited PASS that day; it had kept its opening ⬜)* *Opened 2026-09-13 18:00 review (step 5) for the gate `POST-6` step 3 closed 2026-09-13: `ports:13` (`EX-49`) superposes an* asymmetric *drive on the 4-leg fixture; no example drives the 16-leg / 32-ring-port fixture in quadrature.* Angle: drive — `quadrature_phase_weights` at the 32 ring ports through `superpose_drives` at 10 MHz, `PORT-13`'s fixture imported from `tests/validation/test_port_birdcage_ring_matrix.py`, the CG1 `\|B₁⁺\|` map on the z = 0 sample cylinder written to combined XDMF, with the C16 rotation spread and the mirror identity asserted at the imported 5 % band (`test_birdcage_b1_plus_map.py:120`) and `PORT-16`'s exact power identity at the imported 1e-6. Trap: the gate's sample set holds exactly `MIN_SAMPLE_POINTS` = 50 (`20260913T185043Z_POST-6-step3.log:11780`) — the example prints the count and imports the constant. Done-when (§4): the three imported identities asserted, artifact named, census `exit != 1`, elapsed recorded. Predicted: the gate was 191 s at `-n 8` (build 82 s, 32 drives under reuse 30 s, identity 44 s); at the runner's `-n 2` *predicted* ≤ 8 min — pass the runner `-t 900` and record the measured window. No homogeneity, absolute or Larmor claim. **Closed ✅ 2026-09-14, 04:30 slot (take-next).** The flagged harness run `20260914T095534Z_EX-55.log` (`-n 2`, Status 0, 168 s) asserts (i) C16 spread 0.8102 % and (ii) mirror 0.6769 % (5 %), and (iii) the exact identity at 8.40e-16 (1e-6) (`:11641–11643`). The sample count is 50 against `MIN_SAMPLE_POINTS` = 50 (`:11647`). The unflagged control `…095938Z_EX-55-control.log` (149 s) reproduces them. Census `…095914Z_EX-55-census.log`: docrefs `exit=0` (`:39`), setup figures `examples=50 ok=2 missing=48 broken=0` (`:92`); the figure PNG is 343 KiB. Rule (a): the `ring_quadrature_case` body was lifted into `_build_ring_quadrature_case()` with 8 additive return keys. The gate was re-run green, `20260914T100313Z_EX-55-rule-a-gate.log` (`-n 8`, 15 passed, 148 s, (i)/(ii) digits unchanged). *Disclosed:* container timeout 560, not 900 (the foreground window). No census was logged before the change; the delta is reconstructed from the 09-14 census. | heavy (host-runner; measured 168 s at `-n 2`) |
| `EX-56` | **`\|B₁⁺\|` spread against resolution — the two-rung ladder in ParaView** (`examples/ports/16_birdcage_b1_resolution_ladder.py` + guide; `example-runner`) | ✅ **2026-09-14 06:00 slot:** fall asserted 5.2506 % → 2.0719 % at `-n 2` (records printed, rel 5.7e-06 / 6.9e-06, width disclosed), flagged 142 s / unflagged 136 s (`20260914T110437Z_EX-56.log:3618,3636`, `…110730Z_EX-56-control.log:3618,3629`), census 51/3/48/0 as predicted; **deviation:** two per-rung combined XDMFs, not one time-stepped file (the rungs' meshes differ). ~~⬜~~ *Opened 2026-09-13 18:00 review (step 5) for the gate `WF-6` step 5 closed 2026-09-13: `ports:8` (`EX-40`) ladders* frequency*; no example ladders resolution.* Angle: output quantity — the worst-radius C4 four-copy spread of CG1 `\|B₁⁺\|` on the unloaded F-small birdcage at 10 MHz at global sizing ×1 and ×0.012, imported from `tests/validation/test_birdcage_b1_plus_closed_form.py` (`LADDER`, `STEP5_RECORDED_SPREADS` 5.2506 % / 2.0719 % at `STEP5_SPREAD_RTOL` 1e-3 — imported records, asserted only as the module asserts them; the monotone-fall identity asserted), both rungs' `\|B₁⁺\|` written to one combined XDMF with the rung as a time step so ParaView steps through resolution, and the interior CV printed beside step 4a's filament closed-form CV (printed only). Trap: the ×0.0095 rung stays off (its power residual is a banked known-issues negative); `-n 4` is the record width and the runner's `-n 2` carries the 1e-4-class MUMPS drift (known-issues 09-09) — the example asserts the records at the module's rtol 1e-3 *only if* it runs at `-n 4`; at `-n 2` it prints them and asserts the fall. Done-when (§4): the fall asserted, records reproduced or their width disclosed, artifact named, census `exit != 1`, elapsed recorded. Predicted 204 s at `-n 4` (`20260909T200431Z_WF-6.log`); `-n 2` *predicted* ≈ 6–7 min, runner `-t 900`. A convergence statement only — no closed-form, homogeneity or Larmor claim. | heavy (host-runner) |
| `EX-57` | **One setup figure per example guide — standing, recurring** (operator directive 2026-09-13; `write_setup_figure` + `check_example_setup_figures.py` + exemplar `mesh:3`; one guide per item, the daily review queues the census's `--next` every active day and the drained-queue fallback draws the next one; closes when the census exits 0 on `main`) | 🟡 step 0 ✅ 2026-09-13; census 2026-09-19 (07:30 slot, drained-queue fallback, `mesh:7`): 54 examples, **20 ok, 34 missing**, 0 broken (`20260919T125104Z_EX-57.log:89`), docrefs `dead=0 guide=0 stale=16 … exit=2` (`20260919T125104Z_EX-57.log:112`) — and that slot fixed a **shared-helper defect the census cannot see**: every legend `write_setup_figure` has ever drawn was clipped mid-word, because PyVista 0.48.4's `map_loc_to_pos` anchors `"upper right"`-family locations with `x = 1 − size[1] − border`, i.e. off the box's *height* rather than its width (`pyvista/plotting/renderer.py`), and a setup-figure legend is always wider than tall — so widening the box made it worse. The legend is now anchored `"center left"` (clear of the title and the orientation widget, and on the bug-free branch) and sized to the longest grouped label. Additive, no signature change; committed PNGs are unaffected until re-rendered, so **the earlier figures carry clipped legends and will need re-rendering** — a review's to queue, not this item's. (`mesh:1`, `mesh:2`, `mesh:3`, `mesh:4`, `mesh:5`, `mesh:6`, `mesh:7`, `mesh:8`, `ports:15–18`, `th:10`, `mag:1`, `mag:2`, `mag:4`, `mag:5`, `mag:6`, `mri:1`, `mri:2`, `mri:3`, `mat:1`, `mat:2`, `th:1`, `th:2`, `th:4` done — `mesh:8` added by the 2026-09-20 09:00 slot (§9 item 18): drawn on the **16-leg rung** (`_measure(SCALED_LEG_COUNT)`), the `GEO-19`-gated capability the example prices — the four-leg control rung built later in the script is the in-script negative control and is not pictured. No `clip_normal`: every port box sits on the outer periphery at sixteen legs exactly as at four, so the unclipped isometric view keeps all sixteen on screen. Census `examples=55 ok=21→22 missing=34→33 broken=0` (`20260920T142115Z_EX-57-precensus.log`, `20260920T142424Z_EX-57-postcensus-figures.log`), docrefs `dead=0 guide=0 exit=2` both sides (`20260920T142132Z_EX-57-precensus-docrefs.log`, `20260920T142432Z_EX-57-postcensus-docrefs.log`); every `EX-33` digit reproduced to the digit in both the flagged (`20260920T142137Z_EX-57.log`, 120 s) and unflagged (`20260920T142443Z_EX-57-control.log`, 116 s) runs, and the unflagged run carries no `[setup-figure]` line — the render stayed opt-in. PNG read and checked against every caption/comment sentence before committing; no labelling defect found. `mesh:7` added by the 2026-09-19 07:30 slot as the drained-queue fallback (its second item): drawn on the **leg+ring rung**, the only one of the example's three that carries both port families as sheeted ports (rung 1's four leg boxes are uncut floating blocks — the asymmetry the script itself asserts), so the "gated rung" trap resolves to rung 2; both families are visible in the 3-D panel and the caption says plainly that the `z = 0` slice shows the four **leg** ports only, the eight ring ports sitting at `z = ±0.5·LEG_SPACING = ±0.055` m (`LEG_SPACING = 0.11`, `tests/mesh/test_birdcage_port_tags.py:25` — checked). No labelling error found here: every `10x`/`20x`/`21x` literal in script and guide is consistent with the imported `PORT_LOWER`/`PORT_UPPER` and `RING_PORTS`. `mesh:6` added by the same slot (§9 item 8): the render itself was clean on the first pass (legend whole, ports surviving the `z = 0` clip, title inside the limit), but checking every source-comment sentence against the geometry surfaced a **pre-existing labelling error** — the docstring (3 sites), the `[control]` and `[paraview]` prints and the guide (5 sites) named the gap boxes' upper halves `11x` / `111-114` where the imported `PORT_UPPER = 200` makes them `201-204`; strings only, no tag or assertion moved, both windows re-run and the re-rendered PNG byte-identical to the pre-edit one. `mesh:5` added by the 2026-09-18 09:00 slot: the first figure since the legend fix, and the legend reads whole in the rendered PNG (viewed) — the first pass's render was correct, but its source comment and guide caption both said the phantom is drawn translucent "so the two tori inside it stay visible", which is false of this fixture: `coil_major_radius` is 0.08 m against the phantom's 0.04 m radius, so the coils *encircle* the phantom and nothing is hidden behind it. Both were rewritten to what the image shows and the two windows re-run (rule (i)); the caption's "blue square" also became the rectangle it is (0.10 m along z × 0.08 m across x). `mesh:4` added by the 2026-09-18 07:30 slot: the `example-runner`'s first pass titled the PNG "each gap box split by its mid-plane port sheet" and commented the source "the split itself visible as the seam between the two cell groups", both **false of the render** — the two halves of each gap box share the `port` colour class by the one-colour-per-class convention, so each box reads as one solid block; the runner's own guide caption said so correctly, and the slot retitled to the tag-level statement the image does support (`gap boxes split into 101/111 and 102/112 …`) and rewrote the comment. Two more defects the slot fixed: the figure call sat **above** `mesh_seconds = perf_counter() - started`, folding the ~3 s render into the printed mesh time (flagged 17.7 s vs unflagged 14.9 s — moved below it; final pair reads 14.8 vs 15.1 s, the flagged one now the *faster*), and the corrected 150-char title **ran off the canvas and lost the final letter of "drawn"** — `write_setup_figure` draws the title as a plain `add_text` with no wrap and no length guard, so a ~145-char ceiling is now commented at the call site. A guard belongs in the helper; that is a review's to queue, not this item's. `mesh:2` added by the 2026-09-18 06:00 slot: the first pass hid the outer domain and left a bare phantom sliver showing neither the curved wall nor the 10:1 scale ratio, so the slot re-rendered with the outer domain translucent and the phantom solid inside it, and rewrote the caption (the runner's version also carried a bare `_facets.xdmf`, which the docrefs census read as a dead reference — rule (b), full filenames) — *the list read `ports:14–18` until the 2026-09-18 review; the census has `ports:14` missing, 15 = 2 + 4 + 1 + 5 + 3*). **Disposed by the 2026-09-19 03:00 review:** the 14 figures rendered before `c9cc369` (`mesh:3`, `th:10`, `mag:1/2/4/5/6`, `mri:1/2/3`, `ports:15–18`) are re-rendered by §9 items 6–7 (known-issues 2026-09-19); the missing title-length guard is `OPS-53`; the two remaining slot findings — legends elide past two same-class labels (`first … last`), and one colour per region class cannot show a split between two same-class regions (`mesh:4`) — are **design conventions of the corpus, the operator's to change** (dashboard), and captions carry what the image cannot; the per-item template in §9 now says "hide the region that is not the subject", names both census scripts, keeps the figure call outside any printed timer, and reads "check every caption and source-comment sentence against the geometry" `mesh:9` added by the 2026-09-21 12:30 UTC slot (§9 item 32): drawn on the **16-leg, both-end-rings-cut rung** (`_measure_ring(SCALED_LEG_COUNT)`), `GEO-20` step 2's newly gated capability this example prices — the 4-leg control built later in the script is the in-script negative control and is not pictured. First pass named the sixteen uncut leg boxes `leg L{i} (uncut)`, which matched no `CLASS_COLOURS` keyword and rendered as a six-colour fallback cycle rather than one conductor class; renamed to `leg L{i} conductor (uncut)` and re-rendered before committing. First pass also sliced exactly on the top ring's own axial symmetry plane (`z = 0.5*COIL_LENGTH`) and came back with the ring band unresolved, only the sixteen leg cross-sections; moving the slice 1 mm off that plane did not recover it — `RING_MINOR_RADIUS` is 4 mm and the caption says plainly that the 3-D panel, not the slice, is the one to read for the ring-gap layout. Census `examples=56 ok=23→24 missing=33→32 broken=0` (`20260921T130543Z_EX-57.log`, `20260921T130813Z_EX-57.log`), docrefs `dead=0 guide=0 stale=14 exit=2` both sides (same two logs); every `EX-35` digit reproduced to the digit in both the flagged (`20260921T130303Z_EX-57.log`, 119 s) and unflagged (`20260921T130608Z_EX-57.log`, 113 s) runs, the unflagged run carrying no `[setup-figure]` line. `OPS-59` (b) call-site / PNG / census identity re-run green after `git add`ing the new PNG (`20260921T130859Z_EX-57.log`, 20 passed). `mesh:10` added by the 2026-09-21 14:00 UTC slot (drained-queue fallback): drawn on the **longitudinal subject rung** (`_measure_ring(CONTROL_LEG_COUNT, orientation="longitudinal")`, `GEO-26` step 1); the transverse control is not pictured. Slice on the vertical plane through the coil axis and the 45°/225° gap pair (`phi_hat(45°)` as normal), which cuts all four on-plane ring ports (two per ring) across their chord — the `mesh:9` lesson applied. The executor's caption named tags `101`–`104` "the four copper rods" and said "one [port] per ring" in the slice — both **false of the fixture and the render** (`101`–`104` are the floating leg boxes, `tests/mesh/test_birdcage_ring_gaps.py:235`; the rods are tag `1`); the slot rewrote the guide caption (module untouched, so the flagged window stands under rule (i)). Census `examples=56 ok=24→25 missing=32→31 broken=0` (`20260921T140028Z_EX-57-next.log`, `20260921T142228Z_EX-57-postcensus.log`), docrefs `dead=0 guide=0 stale=13 exit=2`; every `EX-44` record identical flagged (`20260921T140630Z_EX-57.log`, 59 s) vs unflagged (`20260921T141931Z_EX-57.log`, 56 s), no `[setup-figure]` line in the latter; `OPS-59` (b) 20 passed (`20260921T142230Z_EX-57-ops59b.log`). PNG 365 KiB. `mesh:11` added by the 2026-09-23 06:00 CDT slot: 16-leg longitudinal ring-gap rung, census `ok` 25→26 `missing` 31→30 `broken` 0, docrefs `dead=0 guide=0 exit=2`; `GEO-26` step-3 records (270728 cells, 10/32 low-state terminals) reproduced digit for digit flagged (`20260923T110927Z_EX-57.log`) vs unflagged (`20260923T111200Z_EX-57.log`). `mesh:12` added by the 2026-09-23 11:15 UTC slot (drained-queue fallback): F-human 16-leg, both-end-rings-cut rung at 0.15 m (branch B, the fixed-absolute-sizing fixture; branch A, the negative control, is not pictured — not written to disk anywhere in the script), 1 mm off the inter-ring mid-plane on the same offset `mesh:9`/`mesh:11` measured necessary. Census `ok` 26→27 `missing` 30→29 `broken` 0 (`20260923T112127Z_EX-57.log`), docrefs before/after `dead=0 guide=0 stale=12 exit=2` unchanged (read on the pre-edit tree via `git stash`, `20260923T112146Z_EX-57.log` → `20260923T112155Z_EX-57.log`); `GEO-25` step-2 records (branch B 504642 cells / 0.965414 meshed-CAD, branch A 204977 cells / 0.893028) reproduced digit for digit flagged (`20260923T111718Z_EX-57.log`, 217.6 s) vs unflagged (`20260923T112205Z_EX-57.log`, 214.3 s), PNG byte-identical. `mat:1` added by the 2026-09-23 07:30 CDT slot (drained-queue fallback): the `MAT-6` W = 0.15 loop-over-half-space fixture (its only mesh; the σ = 0 control is the same mesh), air hidden, slab translucent, slice at `x = 0` through the loop's symmetry plane. Census `ok` 27→28 `missing` 29→28 `broken` 0 (`20260923T123233Z_EX-57.log` → `20260923T125238Z_EX-57.log`), docrefs `dead=0 guide=0` exit 2, `stale` 12→11 (the flagged run refreshed `mat:1`'s own ParaView output; `20260923T125244Z_EX-57.log`); records (418888 cells, ΔR 0.2747 % vs filament, 0.3895 % vs finite wire) identical flagged (`20260923T124124Z_EX-57.log`, 281 s, `-n 8`) vs unflagged (`20260923T125310Z_EX-57.log`, 256 s), PNG 445 KiB byte-identical; `OPS-59` (b) 20 passed (`20260923T125744Z_EX-57.log`). `mat:2` added by the 2026-09-23 09:00 CDT slot (drained-queue fallback, the census's `--next`): the `MAT-4` step 1 imposed-field lossy-sphere fixture (`_solve_lossy_sphere` → `MeshGenerator.sphere_in_box_domain`, `SPHERE_TAG=1`; the same mesh `mri:2` already pictures), air hidden, sphere translucent (nothing else inside it to reveal), slice at `z = 0` through the equatorial plane the interior `E_z` closed-form comparison is made on; the negative controls (two-sigma ratio, `sigma=0` vacuum) run on the same mesh, not a second one, so nothing else is pictured. Call placed after `solve_seconds` is captured (all three solves already timed) so the render never folds into the printed `[solve]` line. Census `ok` 28→29 `missing` 28→27 `broken` 0 (pre `20260923T140312Z_EX-57.log`, post `20260923T140441Z_EX-57.log`), docrefs `dead=0 guide=0 exit=2` both sides, `stale` 11→10 (the flagged run refreshed `mat:2`'s own ParaView output; `20260923T140318Z_EX-57.log` → `20260923T140448Z_EX-57.log`); `MAT-4` step 1 records (74020 cells, mean-SAR error 3.422%/3.536% vs the 10% bound, separation 4.850x) identical flagged (`20260923T140323Z_EX-57.log`, 56 s) vs unflagged (`20260923T140454Z_EX-57.log`, 52 s), no `[setup-figure]` line in the unflagged run; PNG 468 KiB (478788 bytes); `OPS-59` (b) 20 passed (`20260923T140551Z_EX-57.log`). `th:1` added by the 2026-09-25 06:00 CDT slot (§9 item 42): the `TH-6`/`EX-4` lossy-plane-wave fixture — a plain box domain with **no cell-tag regions** (one homogeneous lossy medium, the analytic wave imposed as Dirichlet data on every face), so the caption says plainly there is nothing to colour by region rather than inventing any; the helper offers no field-colouring mode, so the mesh is shown instead, named as the **24³ fine rung** (`_solve_plane_wave(N_FINE, ..., return_fields=True)`, the same mesh the α/β fit and the ParaView export use). Sliced normal to y (the x–z plane), showing both the propagation axis (+x, the decay direction) and the polarisation axis (z). Call placed after `fine_seconds` is captured so the render never folds into either printed `[solve]` line. Census `ok` 29→30 `missing` 27→26 `broken` 0 (`20260925T111108Z_EX-57.log` → `20260925T111304Z_EX-57.log`), docrefs `dead=0 guide=0 exit=2` both sides, `stale=10` unchanged (`20260925T111114Z_EX-57.log` → `20260925T111309Z_EX-57.log`); `TH-6`/`EX-4` records (rel L2 coarse 7.217852e-02 / fine 3.609441e-02, rate 0.9998, α 13.069299 Np/m vs closed-form 13.067043 (0.0173%), β 27.031347 rad/m vs 27.015150 (0.0600%), `|E|` span 3.701× vs closed-form 3.694×) identical flagged (`20260925T111144Z_EX-57.log`, 17 s) vs unflagged (`20260925T111230Z_EX-57.log`, 15 s), no `[setup-figure]` line in the unflagged run; PNG 60 KiB (61338 bytes); `OPS-59` (b) 20 passed (`20260925T111251Z_EX-57.log`). `th:2` added by the 2026-09-25 06:00 CDT slot (§9 drained-queue fallback, census's own `--next`): the `TH-9` PEC cavity-resonances fixture (`solve_pec_cavity_modes`, `create_box`) — a plain box domain with **no cell-tag regions** (a lossless, source-free 1.0×0.8×0.6 m box, `n × E = 0` on every face; one homogeneous region, nothing to colour by, and no field either since the helper draws the mesh, not a solved array), so the caption says plainly there is nothing to invent. Drawn on the gate's own (6, 5, 4) mesh, the only mesh the example builds. Sliced normal to y (the x–z plane through the box centre), the plane that shows the fundamental (TE₁₀₁) mode's half-wave structure along x and z and none along y (the guide's own step 5). Call placed after `solve_seconds` is captured so the render never folds into the printed `[solve]` line. Census `ok` 30→31 `missing` 26→25 `broken` 0 (`20260925T111503Z_EX-57-next.log` → `20260925T111635Z_EX-57.log`), docrefs `dead=0 guide=0 exit=2` both sides, `stale=10` unchanged (`20260925T111725Z_EX-57.log`); `TH-9`/`EX-5` records (720 cells, 5330 dofs, modes 239.9805/291.3904/312.3465/346.5469 MHz vs closed form 239.9510/291.3459/312.2838/346.3958 MHz, errors 0.0123%/0.0153%/0.0201%/0.0436%, `null_mode_count=0`, Rayleigh rel 5.34e-15 flagged / 3.48e-15 unflagged — both ≪ the 1e-6 gate, exported `|E|` span 2.156391e-17…1.0) identical flagged (`20260925T111617Z_EX-57.log`, 3 s) vs unflagged (`20260925T111732Z_EX-57.log`, 2 s), no `[setup-figure]` line in the unflagged run; PNG 87 KiB (88594 bytes); `OPS-59` (b) 20 passed (`20260925T111705Z_EX-57.log`, after `git add`ing the PNG). `th:3` added by the 2026-09-25 07:30 CDT slot (§9 drained-queue fallback, census's own `--next`): the `TH-8` dielectric-sphere-in-a-uniform-field fixture (`_solve` → `MeshGenerator.sphere_in_box_domain`, `SPHERE_TAG=1`; the same mesh `mri:2` and `mat:2` already picture), air hidden, sphere translucent (nothing else inside it to reveal — no second conductor, no coil), slice at `z = 0` through the mesh centre, near the plane the interior probe cloud and both exterior pole/equator probes sit close to. Call placed after `solve_seconds` is captured so the render never folds into the printed `[solve]` timing. Census `ok` 31→32 `missing` 25→24 `broken` 0 (`20260925T123026Z_EX-57-next.log` → `20260925T123230Z_EX-57.log`), docrefs `dead=0 guide=0 exit=2` both sides, `stale=10` unchanged (`20260925T123244Z_EX-57.log`); `TH-8`/`EX-6` records (39684 cells, interior `E_z` error 2.442% vs 2.443% on the `TH-8` record, spread 0.080%, transverse/`E_z` 0.084%, `|Im|/|Re|` 0.000e+00, volume-vs-probe 0.014%, tagged-volume error 0.568%, jump 59.20×/11.46× vs closed-form 56.27×/11.83×) identical flagged (`20260925T123139Z_EX-57.log`, 11 s) vs unflagged (`20260925T123155Z_EX-57.log`, 7 s), no `[setup-figure]` line in the unflagged run; PNG 425 KiB (435056 bytes); `OPS-59` (b) 20 passed (`20260925T123254Z_EX-57.log`, after `git add`ing the PNG). `th:4` added by the 2026-09-25 09:00 CDT slot (§9 drained-queue fallback, census's own `--next`): the `TH-7` evanescent-TE₁₀-below-cutoff fixture (`_solve` → plain `dmesh.create_box`, imported from `tests/validation/test_waveguide_cutoff.py`) — a plain box domain with **no cell-tag regions** (one lossless homogeneous medium, `εᵣ = μᵣ = 1`, `σ = 0`; the exact evanescent field is Dirichlet data on the whole boundary, so there is nothing to hide or draw translucent), so the caption says plainly there is nothing to colour by region. Sliced normal to y at `y = B_M/2` (the mesh centre), the plane carrying both axes the physics is read off: z (the propagation/decay axis the fitted γ is measured along) and x (the transverse `sin(πx/a)` TE₁₀ half-arch). Call placed after `solve_seconds` is captured so the render never folds into the printed `[solve]` timing. Census `ok` 32→33 `missing` 24→23 `broken` 0 (`20260925T140144Z_EX-57-pre.log` → `20260925T140447Z_EX-57-post.log`), docrefs `dead=0 guide=0 exit=2` both sides, `stale=10` unchanged (`20260925T140201Z_EX-57-pre-docrefs.log` → `20260925T140453Z_EX-57-post-docrefs.log`); `TH-7`/`EX-7` records (41472 cells, γ = 37.650399 Np/m vs closed form 37.652670 (0.006%, ceiling 5%), whole-domain rel L2 4.406648e-02, residual `|Im E_y|/|Re E_y|` 0.000e+00, CG1 cross-check 37.640293 Np/m (0.027% from the N1curl fit), transverse profile RMS 0.124% vs sin(πx/a), sweep control ratio 2.6373 vs 2.6383 cited not re-run) identical flagged (`20260925T140403Z_EX-57.log`, 10 s) vs unflagged (`20260925T140500Z_EX-57-unflagged.log`, 6 s), no `[setup-figure]` line in the unflagged run; PNG 58 KiB (59894 bytes); `OPS-59` (b) 20 passed (`20260925T140512Z_EX-57-ops59b.log`, after `git add`ing the PNG). | the example's own's own |
| `EX-58` | **The tuned birdcage — sweep, `C_tuned`, the in-model field** (`examples/ports/17_birdcage_tuned_circuit.py` + guide; `example-runner`) | ✅ **2026-09-14 06:00 slot (take-next):** `|Im Z_in|/|Z_in|` 2.113e-15 ≤ `TUNING_IM_Z_RTOL`, tuned `S₁₁` residual 8.255812e-05 ≤ `REDUCTION_BAND` (`20260914T112025Z_EX-58.log:43,1799`, flagged 58 s; control `…112312Z_EX-58-control.log:43,1799`, 57 s, same digits); rule (a) lift in `test_port_circuit_layer_field.py` (additive), gate re-run 7 passed 169 s (`…111515Z_EX-58-rule-a-gate.log:3753`); census 52/4/48/0; XDMF has two time steps, written with `XDMFFile` directly. ~~⬜~~ *Opened 2026-09-14 03:00 review (step 5) for the gates `PORT-15` steps 2–3 (closed 2026-09-14) and `PORT-14` step 3 (closed 2026-09-13): `ports:3` (`EX-24`) shows lumped* sheets *and nothing in the corpus terminates a port in a capacitor or tunes.* Angle: drive — `S_64MHZ_EPS0_RECORD`, `tuning_sweep`, `select_c_tuned`, `tuned_input` imported from `tests/validation/test_port_circuit_layer_field.py` (never copied); the `Im Z_in(C)` sweep printed, its zero asserted at the imported `TUNING_IM_Z_RTOL`; one in-model 64 MHz solve with `PORT-14`'s κ-corrected capacitor sheets at `C_tuned` (the module's terminated-network helper made importable additively under §9 rule (a), gate module re-run green in the same slot), the tuned `S₁₁` residual asserted at the imported `REDUCTION_BAND`; `\|E\|` on the phantom at `C_tuned` beside the 50 Ω baseline as two time steps of one combined XDMF. Done-when (§4): the two imported assertions green, artifact named, census `exit != 1`, setup figure per `EX-57`, elapsed recorded. Predicted ≈ 90 s at `-n 2` (`20260914T020419Z_PORT-15.log:3728`); runner `-t 600`. A series resonance on one fixture — no match, no mode frequency, no Larmor-accuracy claim. | standard (host-runner) |
| `EX-59` | **The copper birdcage — the surface loss density on the coil** (`examples/ports/18_birdcage_copper_leontovich.py` + guide; `example-runner`) | ✅ **Done 2026-09-14 07:30 slot** — imported port gates and the surface-loss identity asserted green, and the gate's 10 MHz copper digits reproduced (`20260914T124230Z_EX-59.log:904–918` against `20260914T021500Z_TH-14.log:1032–1055`; flagged 35 s, control 32 s). The facet field is **DG0 per adjacent cell, in W, not a density**; its owned sum equals `P_surf` to 1.5e-15, asserted and true by construction. The helpers are imported as they are, with no gate edit. Census 52/4/48/0 → 53/5/48/0, docrefs `exit=0`. ⬜ *Opened 2026-09-14 03:00 review (step 5) for the gated `TH-14` birdcage step (2026-09-14; the row is 🟡 on its slab step, the birdcage identities themselves are gated): `ports:14` (`EX-54`) is the PEC hole; no example carries a surface impedance.* Angle: output quantity — the 10 MHz copper configuration of `tests/validation/test_th14_birdcage_copper.py` (helpers module-private, §9 rule (a)); the three imported port gates and the surface-loss identity at `DISCRETE_IDENTITY_RTOL` asserted; the DG0 facet field `½Re(1/Z_s)\|n × E\|²` on tag 401 written through the facet grid (the `ports:14` pattern) beside `\|E\|` on the phantom; `P_coil/P_in` printed beside the σ = 800 solid's share. Done-when (§4): the imported assertions green, artifact named, census `exit != 1`, setup figure per `EX-57`, elapsed recorded. Predicted ≈ 60 s at `-n 2` (the gate fixture: 104.7 s for 3 f × 3 σ under reuse, `20260914T021500Z_TH-14.log:1348`); runner `-t 600`. No absolute copper-coil claim (`ANS-6`). | standard (host-runner) |
| `EX-60` | **The lossy-wall cavity — Q against σ beside Pozar** (`examples/time_harmonic/10_lossy_wall_cavity_q.py` + guide; `example-runner`) | ✅ **Done 2026-09-14 07:30 slot (take-next)** — both imported assertions green: `Q/Q_c − 1` +0.010 % ≤ 5 % and `Q(1e6)/Q(1e4)` 9.995026 ≤ 5 % from 10. The PEC control `|Im λ|/Re λ` 4.798e-19 and the exported mode's Rayleigh quotient (rel 7.3e-14) are also asserted, and the rung lines match `20260914T004807Z_TH-14.log:96–99` (`20260914T124948Z_EX-60.log:39–59`; flagged 11 s, control 7 s). `src/`: additive `return_mode` / `return_vectors` in `core/cavity.py`, with the gate re-run green (18 passed, 40 s). Census 53/5/48/0 → 54/6/48/0, docrefs `exit=0`. ⬜ *Opened 2026-09-14 03:00 review (step 5) for the gate `TH-14` step 1 (closed 2026-09-13): `th:2` (`EX-5`) is the PEC box; no example solves a lossy-wall eigenmode.* Angle: boundary model — `solve_impedance_wall_cavity_mode` (`core/cavity.py`) on the `TH-9` box at σ ∈ {1e4, 1e6, 5.8e7}, Pozar's `Q_c` imported from `tests/validation/test_cavity_leontovich_q.py` (never restated), the 1e4 rung asserted at the imported 5 % band and the `√σ` scaling identity asserted, copper printed as the PEC-limit reading; the TE₁₀₁ `\|E\|` to XDMF. Done-when (§4): the two imported assertions green, artifact named, census `exit != 1`, setup figure per `EX-57`, elapsed recorded. Predicted ≈ 1 min at `-n 2` (9.2 s of eigen-solves in a 45 s window, `20260914T004807Z_TH-14.log`); runner `-t 300`. One box, one mode; no coil. | standard (host-runner) |
| `EX-61` | **The tuned birdcage's resonance curve — `R_in(f)`, `X_in(f)`, `f₀` and loaded Q from a driven sweep** (`examples/ports/19_birdcage_tuned_resonance_curve.py` + same-stem guide; `example-runner`; §5.4 ramp for `PORT-22` ✅ 2026-09-20, audited PASS 2026-09-21) | ✅ **Done 2026-09-21 (12:30 UTC slot)** — all three imported anchors green at `-n 2` (record width): 64 MHz tuned `S11` residual `8.256069e-05 <= REDUCTION_BAND` 1e-3 (reproducing `PORT-15` step 3 / the `PORT-22` gate); the same residual at all six frequencies, worst `8.256069e-05` (0.0826× band); exactly one `Im Z_in` sign change, bracket `[60, 64]` MHz; negative control (`0.5 × C_tuned`) misses by `1.116902e+00` = 1116.9× the band, floor 10×. Printed (never gated): `f0 = 63.998619` MHz, `R_in(f0) = 6.772516` Ω, `Q = 6.9332` — reproducing `PORT-22`'s own 11-point-grid readings to the digit (`20260921T124138Z_EX-61.log`, Status 0, **203 s**). Rule (a) additive lift in `tests/validation/test_port22_driven_sweep_resonance.py`: the `c_tuned` / `window` pytest fixtures' bodies lifted verbatim to module-level `build_c_tuned()` / `run_window(frequencies_mhz, c_f)`, fixtures now thin delegates — no existing test's behaviour changed. Written: `ports_19_birdcage_tuned_resonance_curve_rin_xin.csv`/`.png` (`R_in`/`X_in` vs f, `f0` marked), combined XDMF of the 64 MHz tuned `|E|` field, setup figure (`figures/ports_19_birdcage_tuned_resonance_curve_setup.png`, 262 KiB; 3-D panel dominated by the unhidden opaque air block, the informative panel is the `z=0` slice — checked against the image, matches `ports:17`'s figure exactly, same pre-existing partly-unresolved legend). Censuses: docrefs `dead=0 guide=0 stale=16 exit=2` both sides (`20260921T124752Z_EX-61.log`, `20260921T124841Z_EX-61.log`; a guide reference used a shortened `…_rin_xin.png` form on the first post-census, fixed to the full filename before the second); setup-figure `examples=55→56 ok=22→23 missing=33 broken=0` (`20260921T124756Z_EX-61.log`, `20260921T124848Z_EX-61.log`), predicted delta matched. No absolute `S₁₁`/`Z_in` claim made (known-issues 2026-09-19). **Deviation:** first two harness attempts hit the `date -u && run_and_log.sh` docker-socket denial (known-issues 2026-09-20 entry — a non-exempted prefix loses the sandbox exemption); the bare re-invocation went through at once, not an outage. §9 item 31 DONE. ~~⬜ **Opened 2026-09-21 03:00 review.** `ports:17` (`EX-58`) shows the tuned state at one frequency; no example shows a frequency response. Six frequencies 52–72 MHz in 4 MHz steps on the 116 085-cell gate mesh, degree 1: per frequency the untuned matched 4×4 and the in-model tuned P1 drive, **every fixture, `C_tuned`, band and helper imported from `tests/validation/test_port22_driven_sweep_resonance.py`** (restate nothing). **Asserted (imported):** circuit-reduced vs in-model tuned `S₁₁` residual ≤ `REDUCTION_BAND` at each frequency; exactly one `Im Z_in` sign change, in the bracket holding 64 MHz; `PORT-22`'s `0.5 × C_tuned` control misses by > `CONTROL_MISS_FACTOR` × the band at 64 MHz. **Written:** `R_in` / `X_in` vs f as CSV + PNG; interpolated `f₀`, `R_in(f₀)`, loaded Q (printed, never gated — `PORT-22` read 63.998619 MHz / 6.772516 Ω / 6.9332 on its 11-point grid); combined XDMF of the tuned field at 64 MHz that opens in ParaView; setup figure per `EX-57`. **Not claimed:** any absolute `S₁₁` / `Z_in` (known-issues 2026-09-19, `PORT-21`), a mode spectrum (`TH-17`), a match. Done-when (§4): the three imported assertions green through `./run_examples.sh -e ports:19`, artifacts named in the guide by full filename, both censuses before / after, docrefs `exit != 1`, elapsed recorded. Predicted ≈ 200 s + export at `-n 2` (`PORT-22`: 358 s for 11 frequencies). §9 item 31.~~ **Rule (a) evidence, added by the 2026-09-23 03:00 review (audit PASS; the auditor flagged that this row did not cite it):** the additive lift of the `c_tuned` / `window` fixture bodies in `tests/validation/test_port22_driven_sweep_resonance.py` (`fd5980c`) was re-run green as committed in the same slot — `PORT-22` module, window 44–64 MHz, `-n 2`, **5 passed in 157.65 s**, Status 0 (`20260921T125120Z_EX-61-port22-regate.log`, commit `6998492`), four minutes after the ✅ commit `0d66fdb`. The code landed on `main` via an intermediate `attempt(EX-61)` commit rather than an `attempt/*` branch — harmless here, noted. | heavy |

**`EX-57` — one setup figure per example guide (standing, recurring)** 🟡 *(opened 2026-09-13 by operator directive: "at least one good visualization of the problem for each example in the examples folder, inserted into the .md files describing each example so people can see what the basic setup is"; step 0 executed interactively the same evening)*. Every script `./run_examples.sh --list` enumerates owes its same-stem guide a **`## Setup figure`** section that embeds one committed PNG from the group's `figures/` directory (`figures/<basename>_setup.png`, ≤ 600 KiB) and a caption naming the regions, the tags, the slice plane and what the reader should notice. **The infrastructure (step 0):** `src/fem_em_solver/post/setup_figure.py::write_setup_figure` — rank-safe (owned cells gathered to rank 0), headless PyVista, opt-in through `FEM_EM_SETUP_FIGURES=1` so the committed PNG never moves on a corpus run, two panels (tagged regions clipped in 3-D beside a mid-plane slice with mesh edges), one colour per region *class* so copper is copper in every figure; `scripts/testing/check_example_setup_figures.py` — the census (`ok` / `missing` / `broken`; exit 0 / 2 / 1 on the docrefs contract; `--next` prints the next example owing one in the runner's `--list` order); the docrefs checker searches `figures/` beside `paraview_output/`; exemplar `mesh:3` (`examples/meshing/03_birdcage_graded_conductors.py` + guide).
**Recurrence (the operator's "recurring background task"):** the daily review's step 6 appends **one `EX-57` figure item** to §9 On deck on every active day, naming the script `check_example_setup_figures.py --next` prints, until the census reads `missing=0`; the drained-queue fallback in §9 is the same item, so a slot that empties the queue draws the next figure instead of stopping. **Batched since 2026-09-25 (operator directive):** an item — queued or fallback — names up to three scripts, `--next 3` cut at the first that leaves the leading script's group directory, and **one** `example-runner` run draws them in order, one commit per figure, so a slot that runs out of clock keeps what it committed; the setup-figure and docrefs pre-censuses run once before the first figure and the post-censuses once after the last, predicting `missing` down by the number committed. Everything below that says "each item" applies to each figure. Reason (interactive transcript analysis, 2026-09-20 → 09-25): `example-runner` took ≈ 31 % of scheduled-session context, ≈ 65 turns per single figure, much of it the same start-up reads (this row, `setup_figure.py`, the harness log tails) repeated for every figure. Each figure is one example: add the `write_setup_figure` call right after the example builds its mesh (region names from the fixture's own tag map, air hidden, phantom translucent, the slice through the plane that shows the physics — the port plane, the coil mid-plane, the wave's propagation axis), run the example **once with the flag** through the harness at its recorded width, `git add` the PNG, write the `## Setup figure` section with its caption, then run both censuses (docrefs `exit != 1`, setup-figure `broken=0`) and re-run the example **without** the flag to show the default path is unchanged (same printed records). **Done-when per item (§4):** the census delta predicted before and read after (`missing` down by exactly one, `broken=0`), the example's imported assertions still green in the flagged run, elapsed recorded, PNG ≤ 600 KiB. **The committed PNG needs no pin edit** (`OPS-59`, 2026-09-20): `tests/unit/test_doc_reference_exit_codes.py` admits `examples/**/figures/*_setup.png` by *rule* — the census's own script↔figure pairing — so a figure lands without touching the artifact record. **A non-setup artifact is the opposite:** any other committed file under `examples/` (an `ans:` `metrics.json`, a validation PNG) still has to be named by hand in `LISTED_EXAMPLE_ARTIFACTS`, in the commit that commits it, or that test goes red on `main`. **Done-when for the chunk:** `check_example_setup_figures.py` exits 0 on `main`. **Traps:** the flagged run must be **the harness** (a bare shell render is unlogged — `EX-43` precedent); a region wholly inside the clipped half-space is skipped, not drawn — choose `clip_normal` so the ports survive; examples that build several meshes draw the *gated* rung; magnetostatics examples with a wire source and no conductor tag name the wire region so the copper colour applies; Ansys-benchmark cases (`ans:`) draw the geometry only — never a number from `aed_results/`. **Cost per item:** the example's recorded window plus the render (measured step 0: **+2 s** on `mesh:3`) plus censuses, ≈ 20 slot-min; **~50 examples ⇒ ~50 items**, one per active day, ≈ 10 weeks at the wind-down cadence, faster whenever a slot drains the queue. Tier: the example's own.
**Step 0 ✅ 2026-09-13 (interactive, on a worktree of `1abd55f`):** `mesh:3` at `-n 2` with the flag — Status 0, **31 s** (record 27.7 s ⇒ render ≈ +2–3 s), PNG **401 KiB**, gate records **0.966977 / 0.846150** reproduced digit for digit in both the flagged and the unflagged run; unflagged control Status 0, 29 s, no figure line. Census after: **`examples=48 ok=1 missing=47 broken=0`** (exit 2). Two earlier flagged attempts were red and fixed in place: an empty clipped port box (PyVista refuses an empty mesh — now skipped, and the half-space clip is opt-in) and a stray indent. Docrefs census on the worktree read `dead=88 guide=0`, all 88 the fresh checkout's absent `paraview_output/` artifacts and none the new PNG — not a corpus reading; `main`'s own census stands.
**Logs:** `20260914T024424Z_EX-57-step0.log` (flagged, Status 0, 31 s), `20260914T024455Z_EX-57-step0-control.log` (unflagged, Status 0, 29 s), `20260914T024524Z_EX-57-step0-census.log` (both censuses); reds `20260914T022747Z_EX-57-step0.log` (Status 142, the empty clipped box), `20260914T024312Z_EX-57-step0.log` (Status 1, the indent).

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
| `ANS-2` | Coil-driven SAR in the loaded four-leg birdcage at 10 MHz: pointwise SAR, whole-phantom power, mass-averaged SAR | ✅ **Adjudicated AGREE 2026-09-18 (interactive operator session in the weekly's form; the 2026-09-19 weekly may amend; numeric ruling in the gitignored `docs/private/ans2-adjudication-2026-09-18.md`).** **Step 4 ran 2026-09-25 (`xl`, `20260925T070008Z_ANS-2-step4.log`, Status 0, 1315 s, 39.91 GiB, orphans 0 / 0; `log-pathologist` reading, ledger row) and the 2026-09-25 03:00 review rules it branch (a) by the pre-registered rule:** at `phantom_resolution` 0.00125 m (719 769 cells, 452 228 phantom) the driven-point C4 spread falls **15.730 % → 4.528 %** (< 5 %) and the four phantom powers move −0.27 / −0.14 / −0.30 / −0.06 % (< 2 %; (b) fails on size, so no private reading was needed), every example assert green (10 g pairs ≤ 0.1751 %, coverage identity ≤ 6.82e-14). ⇒ the residual against HFSS is the feed; **the verdict's ±10 % pointwise band tightens to the measured 4.53 % spread and row 2's 5 % band stands.** Caveats the weekly may weigh: the margin is 0.47 pp on one rung; individual driven-point values moved −6.7 … +9.9 % between the rungs, so the pointwise samples are not themselves converged; the two rungs ran at different widths (`-n 4` / `-n 8`). The weekly carries the band into the private adjudication file. `metrics_h0.00125.json` is kept local under the gitignored `paraview_output/`, not committed: the `OPS-59` artifact pin admits one `metrics.json` per `ans:` case. The halved rung's cell counts are a candidate record, not asserted. Step 1 (runnable half) green with its control as a floor; step 3 (the operator's HFSS 2026 R1 replication, Zero and First Order) landed 2026-09-18 and the Linux half re-ran after the incident-power correction (`20260919T001707Z_ANS-2-normalisation-fix.log`, 201 s, anchors green). **Ruling on the shape-free rows 1–3:** the coil-driven whole-phantom dissipated power agrees with HFSS at the **5 % level** (AED lower) and pointwise SAR at the four ball centres within **±10 %** with the scatter on our side; normalised to each code's own accepted power the phantom dissipation agrees to ≈ 1–2 %, so the residual is the lumped-port feed systematic already named (`PORT-1`, `ANS-4` at 10 MHz), not the SAR computation; the two HFSS orders agree with each other. Rows 4–5 are records; row 6 (HFSS peak averaged SAR) is a cube-averaging boundary artefact and is not read. **Licensed:** the first absolute, externally checked coil-driven SAR statement in the repo, and `MAT-4`'s C4 identity gains an external anchor. **Not licensed:** any compliance (C95.3), homogeneity, B₁⁺, Larmor or quadrature claim. **Step 2** (rows 4–6, sphere-vs-cube) is now an optional record step. **Step 4 (i) executed 2026-09-19, 04:30 slot — the cost probe fired its own pre-registered STOP rule; step 4 re-prices to XL and is BLOCKED on a commissioning review.** The phantom h-halving diagnostic (does our 15.7 % driven-point C4 sampling scatter collapse toward HFSS's own (private) figure, and does the integral move (mesh) or not (feed); pre-registered decision rule in the gitignored adjudication file) was priced at ≈ 610 k cells and "minutes at `-n 8`". **Measured** (`20260919T093241Z_ANS-2.log:2033–2038`, Status 0, 566 s wall at `-n 8`): the 0.00125 m rung meshes to **719 769 cells / 452 228 phantom cells / 845 188 unknowns**, the mesh alone takes **359.8 s**, one drive **188.4 s**, and `ru_maxrss` sums to **40.89 GiB** across the eight ranks (max 5.76 GiB/rank). Four drives therefore extrapolate to **1 114 s = 18.6 min** *before* the 21 mass-averaged ball integrals and the point evaluations — over the item's 15 min ceiling, over the 40 GiB ceiling, and over §5.1's hard 20-min-per-command cap. Both stop criteria fire independently, so the pre-registered branch is unambiguous: **nothing else in the item ran**, no anchor was measured, and the ±10 % pointwise band on the verdict above is **unmoved**. The mesher, not the solver, is the surprise — 360 s of the 566 s is meshing, which the ≈ 610 k-cell prediction (scaled from `WF-7` step 0's *solve*) did not carry. Measurement-only probe committed as `tests/validation/probe_ans2_phantom_h_halving.py` (no assertion, no band). **Unblock:** a review pre-registers the four-drive halved-rung run in `docs/testing/xl-pending.md` under licence class "cost probe"/"priced family" — implementers never commission one. **Step 4a ✅ 2026-09-19 (the XL prerequisite):** the example reads `FEM_EM_ANS2_PHANTOM_RESOLUTION` — unset is byte-identical to the 0.0025 rung; when set it tags `metrics_h<res>.json` / `..._h<res with p for the point>.xdmf`, skips the two 0.0025-rung mesh-record assertions with a printed `[ANS-2 step 4] MESH-RECORD ASSERTIONS SKIPPED` line (every other imported band still asserted), never rewrites `COMPARISON.md` / `COMPARISON_private.md`, and prints the `[ANS-2 step 4]` readout beside the tracked rung's own `metrics.json`. Anchors: unset vs the tracked `metrics.json` and knob-`0.0025` vs unset both digit-identical on every primary leaf at `EXACT_IDENTITY_RTOL` (worst 8.187289e-11 / 8.167942e-11 of 145 leaves), negative control at 0.004 m prints the skip line and exits 0; the C4 sampling spread reads **15.730%** on the 0.0025 rung (reproducing the adjudication's 15.7%) and **7.392%** at 0.004 m — printed, never gated. `20260919T141006Z_ANS-2-step4a-unset-control.log`, `20260919T142050Z_ANS-2-step4a-knob-identity.log` (Status 0, 330 s). **`xl-pending.md` entry 10 is now READY** and its "meshes once vs per drive" branch is settled (once). Details and the two side measurements (derived C4-miss leaves reproduce only to 2.16e-8; `write_xdmf_with_tags` ate the resolution tag's decimals) in §9 item 9. *History: `docs/planning/chunks/ANS-2.md`.* | heavy *(step 1 198 s at `-n 4`; step 4 heavy by prediction, cost probe first)* |
| `ANS-3` | Two coaxial gapped loops at 10 MHz: runnable half of the second AED benchmark (2-port Z/S; `ANS-2` reserved by §10 for the future B1+/SAR case) | ✅ *(example path restored 2026-08-31 by `EX-37` and re-run green, 128 s; the 08-16 / 08-26 records stand)* **AED numbers landed 2026-09-19 (operator, HFSS 2026 R1, Zero and First Order); Linux half re-run `20260920T002403Z_ANS-3-aed-private.log` (149 s, anchors green, records at 1e-10), `COMPARISON_private.md` filled. Adjudication owed to the 2026-09-19 21:00 weekly; preliminary reading (interactive session, `docs/private/ans3-operator-notes-2026-09-19.md`): the primary row — the mutual coupling Im Z₁₂ — AGREES with both AED orders at the sub-percent level, and both codes sit at the same distance below the filamentary closed form, i.e. HFSS agrees with our *raw* mutual ratio, not the systematics-corrected one; the self-impedance rows are informative as the SPEC pre-declared (our conductor loss reads low at fixed wire sizing); and the S rows expose a definitional systematic in *our* table — the 50 Ω S implied by our own Z agrees with AED, the current-drive route's per-port S assembly does not (the `sparameters.py` docstring already says that assembly is exact only at a matched drive). The weekly rules; a `PORT` item on the current-drive route's S is the likely outcome.** **Adjudicated 2026-09-19 (weekly, §10; numbers private): AGREE on the primary row (the mutual coupling); the S rows DISAGREE and the defect is ours** — the current-drive route's tabulated `S` is not the 50 Ω S-matrix, while the same run's `Z` is right and its `z_to_s(Z)` agrees (known-issues 2026-09-19; `PORT-20`, §9 items 11 and 17, re-records this case's S table). The preliminary "raw, not corrected" reading above was **not adopted as written**: the two systematics move the modelled problem toward the filamentary closed form and apply to both codes equally, so code-to-code is raw-to-raw and the 10 % mutual band is not re-pointed. Self rows informative, as pre-declared. *(Row wording by the 2026-09-20 03:00 review at the weekly's request; the preliminary paragraph above states a relative agreement level against the external code — whether that phrasing may stay in a tracked file is the operator's open dashboard question, and this review repeats no level.)* | heavy |
| `ANS-4` | Gapped four-leg birdcage, phantom-loaded, four lumped ports: 4×4 S-matrix at 10 / 64 / 128 MHz | ✅ The step-2 family is frozen under the four-attempt rule: no degree-1 ladder on this fixture is in a proven asymptotic range, so a degree-1 extrapolant is not an h → 0 reference. **Larmor verdict banked 2026-09-13 (weekly): AGREE at 128 MHz on step 2d's order-matched rung, AGREE by mechanism at 64 MHz; step 3 (the 64 MHz degree-2 rung, `xl`, priced by 2d) is pre-registered in §10 for the 09-16 review's window; numbers private.** **Step 3 is pre-registered as `docs/testing/xl-pending.md` entry 2 (2026-09-13, operator session) behind step 3a — a tests-only §9 item that gives `test_ans4_resolution_ladder.py` a `FEM_EM_ANS4_FREQUENCY_HZ` knob (default 128e6, unset bit-identical; control: the `0.015:1` rung reproduces 2a″'s digits at `-n 2`); the Wednesday 09-16 daily review queues the window for Thursday 09-17 02:00 once 3a lands.** **Step 3a landed 2026-09-14 (04:30 slot):** the knob threads every rung. The flag-off control reproduces 2a″'s ×1 digits to 8.2e-11 at `-n 8` (rtol 1e-6), and at `64e6` every class moves ≥ 0.15 from the 128 MHz record (floor 1e-2) while the printed control matches `PORT-11`'s 64 MHz 4×4 to 6.1e-11 (`20260914T093325Z_ANS-4-step3a-w1.log`, 62 s; `…093444Z_…-w2.log`, 63 s). **Step 3's XL window ran 2026-09-16 02:00** (`20260916T070008Z_ANS-4-step3.log`, the FIFO's first file): `RUNGSPEC="0.015:1 0.005:2"` at 64 MHz, `-n 16`, **16 passed, Status 0, 1658 s**; the degree-2 rung 592 744 cells / 3.79 M unknowns, four drives 1476.9 s, summed `ru_maxrss` 282.3 GiB, `memory.peak` 280.8 GiB (service recreated before the window); every imported `PORT-11` gate green (reciprocity 1.6e-14, σ_max 0.999758, spreads 0.1985 / 0.1715 / 0.1946 %). Public readout: the degree 1 → 2 move on the driven column at 64 MHz is **6.51 / 2.60 / 4.11 %** (self / adjacent / opposite; 128 MHz read 6.09 / 5.38 / 6.70 %). **Recorded, not adjudicated** — the private AED miss and the decision rule are the 09-19 weekly's. **Steps 3b–3d queued by the 09-16 review as priced-family variants** (`xl-pending.md` entries 3–5: 128 MHz degree 2 on the C4-congruent cut, 10 MHz degree 2, 64 MHz degree 2 on the congruent cut; 09-17 / 09-18 / 09-20 02:00). **Adjudicated 2026-09-19 (weekly, §10; numbers private): the order-matched comparison AGREES on the coupling classes at all three frequencies and on every class at 128 MHz (3b: the congruent cut is not a degree-2 systematic there), and DISAGREES on the self class `S₁₁` at 64 MHz (step 3 — the pre-registered private rule fired; "AGREE by mechanism" is withdrawn for `S₁₁`) and at 10 MHz (3c — the public rule fired: the degree 1 → 2 move 4.41 / 1.35 / 1.08 % is in the Larmor moves' class, so the 09-06 degree-1 "10 MHz AGREE" was partly coincidental).** No absolute `S₁₁` / `Z_in` / match figure is licensed at 10 or 64 MHz at either order (§2.2, known-issues 2026-09-19). The row stays ✅ — the chunk's gates are self-consistency identities and all are green on every rung; the disagreement is tracked by `PORT-21` and read next against 3e / 3g (`xl` 09-22 / 09-24) and `ANS-6`'s PEC column. **3d ran 2026-09-20** (ledger): on the cut at 64 MHz the class spreads fall to 0.0132 / 0.0126 / 0.0081 % and the two-rung move (6.50 / 2.61 / 4.12 %) sits within 0.012 percentage points of step 3's — by entry 5's public rule the cut is not a degree-2 systematic at 64 MHz either; the 09-26 weekly rules. **3e ran 2026-09-22 and 3f 2026-09-23** (ledger rows filled by the 09-23 03:00 review from `log-pathologist` readings): 3e — the 64 MHz degree-2 *h*-ladder, cut off, every imported gate green on all four rungs, Status 1 only on two non-physics reds (the `OPS-62` guard, fixed; the pre-rebuild `OPS-60` `skrf` red); successive degree-2 changes (review arithmetic, not printed) S₁₁ 2.815 → 1.497 %, S₂₁ 1.570 → 0.816 %, S₃₁ 1.362 → 0.831 %, ratios 1.88 / 1.92 / 1.64, with the finest cut-off rung's ≈ 10× C4 spread leaving S₃₁'s ratio ambiguous (≈ 1.3–2.2). 3f — 10 MHz degree 2 on the cut, 18 passed: class spreads **0.0303 / 0.0158 / 0.0100 %** against 3c's cut-off 0.4451 / 0.2199 / 0.2186 %, two-rung move 4.4499 / 1.2966 / 1.2187 % — entry 8's **collapse branch** by the public numbers (3c's near-band self spread was the cut-off sheet asymmetry). Follow-ups queued under the daily licence: 3h (10 MHz *h*-ladder on the cut, 09-27) and 3i (64 MHz *h*-ladder on the cut, 09-28), `xl-pending.md` entries 12–13. The weekly rules on all of it. *History: `docs/planning/chunks/ANS-4.md`.* | heavy (≈ 160 s at `-n 2`, one command; measured 125 / 128 s); step 2 **`xl`** |
| `ANS-5` | **Pin the element-order correspondence in every ANS `SPEC.md`/`COMPARISON.md`** — our production `degree 1` is what HFSS calls **Zero Order**, not its default **First Order**; the specs do not say so, and a default-settings replication is a different discretization (operator observation, interactive session 2026-08-28) | ✅ **RULED 2026-08-30 02:15 weekly review** — (a) AED runs at **Zero Order** (matched, the adjudication column) **and** at its default **First Order** (an order-sensitivity column); **Mixed Order forbidden**; our side stays at one order (none of options 1–3 as framed — option 1 for the adjudication column plus a second AED column, our side unchanged, step 3 **not** taken). (b) `ANS-1` **is in scope** for the spec line (state the Maxwell 3D formulation and order AED used). Already-returned numbers at an unrecorded order stand as an "order-unknown" column. Steps 1–2 are documentary and queueable; `ANS-4`'s spec already carries the wording. **Steps 1–2 executed 2026-08-31 00:00 slot — 🟡:** README correspondence table + a *Basis / element order* paragraph in all three SPECs (four `*.md` files, +71/−3, no band or figure moved); the `ANS-1`/`ANS-3` `COMPARISON.md` rows need a **generator `.py`** edit the item's scope forbids — carried as a finding, **priced as step 1b by the 03:00 review (§9 item 2)**. **Step 1b executed 2026-08-31 06:00 slot — chunk ✅** (steps 1, 1b, 2; step 3 ruled not taken): both generators' `_write_comparison` now emit `AED (Zero Order)` / `AED (First Order)` and a `Basis order` row, both cases re-run green on their own asserts (ΔR **1.5838%** vs 2%; `PORT-1` step-4 reproduction **2.98e-05 / 2.92e-05 / 1.71e-06 / 3.33e-10** inside 1%, reciprocity 4.7586e-05 < 1e-3, ‖S‖₂ 0.864809 ≤ 1), census at the standing `dead=53 guide=0 stale=10`. The pre-registered ≤ 1e-8 `metrics.json` negative control **is not a valid discriminator for `ANS-3`** — measured below | smoke (no compute; step 1b ≈ 200 s, measured 61 + 133 s + 125 s control + 1 s census) |
| `ANS-6` | **Copper birdcage, phantom-loaded, four lumped ports: the `ANS-4` fixture with a σ = 5.8e7 S/m coil — the first AED case on a realistic conductor** (operator directive 2026-09-04, interactive session; **serial on `TH-15` ✅ and `TH-14` ✅**; AED side: HFSS *Finite Conductivity* boundary on the coil with Solve Inside off, plus a PEC-coil column) | 🟡 **Step 2b resolution knob ✅ 2026-09-23 (04:30 slot, §9 item 35).** `FEM_EM_ANS6_RESOLUTION` (m) on the degree-knob route only (alone ⇒ `RuntimeError`, `20260923T094749Z_ANS-6-step2b-resolution-alone-raises.log:39`); additive `resolution=None` on `_build_ladder()` / `_hole_rung()`; `ans6_reproduction_check.py --knob`; no `src/`. **(a) control** degree 1, h = 0.015, 64 MHz, `-n 4`: 80 181 cells, 111 121 unknowns, tracked `metrics.json` S leaves reproduced to 2.647e-15 (≤ 1e-9; the move floor replaced there by this stronger assert, per the item), step-2 gates green (`20260923T094235Z_ANS-6-step2b-a-h0p015-d1-64MHz.log:940–944`, 36 s). **(b) knob reaches the mesh** h = 0.0075: 226 642 cells, 294 763 unknowns, class moves 1.15e-2 – 2.86e-2 (> 1e-6, asserted), gates green; price point PEC / Cu / P1 sweeps 38.2 / 32.8 / 28.9 s, 147.4 s, summed `ru_maxrss` 6.39 GiB (`20260923T093956Z_…-b-h0p0075-d1-64MHz.log:950–953`, 149 s). Rule (a): `TH-14` 11 passed / 83 s (`20260923T094319Z_…ruleA-TH-14.log:1378`), `TH-15`@64 6 passed / 4 skipped / 32 s (`20260923T094451Z_…ruleA-TH-15-64MHz.log:995`). Censuses: setup figures 56 / 25 / 31 / 0 before (`20260923T080435Z_EX-57-next.log:35`) and after (`20260923T094549Z_…census-after.log:112`); docrefs after dead 0 / guide 0 (`:53`), its 14 stale entries all age-driven, none `ans6`. `xl-pending.md` entry 14 → READY. History: **Runnable half ✅ 2026-09-20 (07:30 slot, §9 item 14).** `examples/ansys_benchmarks/ans6_copper_birdcage_four_port_10_64_128MHz/06_copper_birdcage_four_port_10_64_128MHz.py` + same-stem guide, dispatched through `./run_examples.sh -e ans:6`. Both columns (Cu, PEC) at all three frequencies come from one call to `TH-14`'s own `_build_ladder()` — its `ladder` fixture body lifted, unchanged, to a module-level function (rule (a); `TH-14`'s 11-test gate suite re-run green in the same slot, `20260920T123746Z_ANS-6-TH14-gate-relift.log`, 101.62 s). Every imported gate (reciprocity, passivity, C4 spreads, both columns, all three frequencies) and the copper surface-loss identity (≤ `DISCRETE_IDENTITY_RTOL`) pass. **PEC column cross-check:** `TH-15` step 3's own `_hole_rung`, independently meshed and solved at 10 MHz, matches `TH-14`'s embedded PEC reference to a worst relative deviation of 3.331e-13 (band 1e-8) — two separate builds of "the coil as a hole" agreeing to 13 digits. `P_coil/P_in` (0.9288392 / 0.4483664 / 0.2186740 at 10/64/128 MHz) is not re-derived — read directly off the live `_build_ladder()` call, reproducing the SPEC's reference table and `TH-14`'s own log to every printed digit. Negative control (predicted, rule (e)): the σ = 5.8e11 S/m rung's `max|S−S_PEC|` (2.4–4.2e-06) sits ~25–40× under `PREDICTED_PEC_LIMIT_MAX_ABS_DS` (1e-4) at all three frequencies. `metrics.json` and `COMPARISON.md` written (AED columns blank by construction, no `aed_results/`/`docs/private/` opened); setup figure and combined XDMF (128 MHz, copper, P1-driven) land alongside. Docrefs census 68→70 guides (the new guide + the new `COMPARISON.md`), dead=0, exit=2 (pre-existing staleness, unrelated); setup-figure census 54→55 examples, 20→21 `ok`, broken=0. Run: `20260920T124620Z_ANS-6.log`, Status 0, 167 s at `-n 2`, degree 1. **Not claimed:** no adjudication, no resonance/tuning/absolute-accuracy claim, no absolute `S₁₁`/`Z_in` at 10 or 64 MHz (`PORT-21`). Operator AED replication and adjudication remain open (§5.4 Waiting-on-you).  **AED numbers landed 2026-09-20** (operator, HFSS 2026 R1, Cu and PEC × Zero and First Order; Linux half re-run `20260920T175038Z_ANS-6-aed-compare.log`, 140 s at `-n 4`, all gates green). **Adjudication owed to the next review** (weekly 2026-09-26, or a daily if asked); preliminary reading (interactive session, `docs/private/ans6-operator-notes-2026-09-20.md`): the **loss partition agrees** at every frequency and both AED orders — the first external check of the Leontovich surface-loss model; the **column difference S(Cu) − S(PEC) agrees** with HFSS First Order; and the absolute S classes carry the *same* self-class offset on the copper and the PEC columns alike, which **attributes `ANS-4`'s self-class disagreement to the lumped-port model / our degree-1 mesh and clears the resolved-conductor interior** (the SPEC's discriminator, answered). AED's own energy balance closes on every design. Follow-ups for the review: a private-mode comparison writer for this example (none exists; the reading above is by hand), and the self-class offset's home (`PORT-21`, or a degree-2 `xl` rung of this case). **2026-09-21 03:00 review:** adjudication is the 09-26 weekly's (§5.4 — no daily was asked); **step 2 (chain T9b, slot half) queued as §9 item 23** — `FEM_EM_ANS6_DEGREE` knob with the unset run digit-identical at `-n 4` (imported `LEG_D0_REPRODUCTION_BAND`), and the first degree-2 price on the 80 181-cell hole mesh at h = 0.015, 64 MHz, two columns, `-n 8` (predicted ≈ 515 k unknowns, ≈ 45 s, ≈ 12 GiB from `TH-19` step 3); the h = 0.005 `xl` cost probe is written by the review after that price exists. **Step 2 (T9b) knob ✅ + degree-2 price at h = 0.015 (2026-09-21 09:30 slot):** `FEM_EM_ANS6_DEGREE` (+ required `FEM_EM_ANS6_FREQ_MHZ`) on the script; additive `degree` on `_build_ladder()` / `_hole_rung()` and a `sigmas` subset on `_build_ladder()` (default the full ladder), no `src/`. Control: the unset run at `-n 4` reproduces every tracked S leaf to 1.395e-14 against the imported `LEG_D0_REPRODUCTION_BAND` 1e-9 (`scripts/testing/ans6_reproduction_check.py`, `20260921T095749Z_ANS-6-step2-control-check.log:34`); the regenerated `metrics.json` / `COMPARISON.md` were restored, not committed. Rule (a): `TH-14` module green, 11 passed (`20260921T095800Z_ANS-6-step2-gates.log:1476`; the `TH-15` half of that run errored at setup — `TH15_STEP3_FREQ_MHZ` unset, an invocation slip); `TH-15` re-run at 64 MHz green, 6 passed / 4 skipped (`20260921T095937Z_ANS-6-step2-gate-th15.log:995`). **Degree-2 price (64 MHz, `-n 8`, 80 181 cells, Cu + PEC + P1 = three factorisations):** PEC sweep 61.9 s, Cu sweep 53.9 s, P1 44.9 s, 183.9 s total, summed ru_maxrss 13.78 GiB — STOP rule not approached; reciprocity ≤ 4.866e-14, σ_max 0.999740, spreads ≤ 0.0202 %, copper identity 7.812e-13 (all asserted); negative control (asserted > 1e-6, ≤ 2): class moves vs degree 1 self 7.40e-02 / adjacent 4.06e-02 / opposite 4.13e-02 on both columns — self just above the printed-only 3–7e-2 prediction, adjacent/opposite inside it (`20260921T100022Z_ANS-6-step2-degree2-64MHz.log:924–942`). The global unknown count was **not printed** (the ≈ 515 k prediction stays unmeasured); the h = 0.005 `xl` entry can price from time and memory. | heavy |


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
   | **B1** | `TH-5` | Radiation boundary | — | existing ⬜ chunk, now dated by this ladder. **Skip recorded 2026-09-23 03:00 review:** not queued — Tier B follows item 4's conductor lineage, which has not closed (`TH-15` 🟡, `ANS-6` 🟡 awaiting the 09-26 adjudication); B3 (`TH-17`) went ahead only as the weekly's chain step T5. Whether B1 opens before the lineage closes is the weekly's call |
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
rubric element 7) — an item that cannot is not queued; (4) **enumerated-chain
licence (operator directive 2026-09-18):** when the queue is below the floor,
the daily review may write and queue, at full rubric grain, any *numbered*
step that the weekly has enumerated in a §10 chain (today: the "step count to
a tuned birdcage" list) whose serial prerequisites have landed — the weekly
supplied the question and the validation target, the review supplies the
execution detail; it may not add, reorder or re-target chain steps, and a
step whose target it cannot make assertable is queued as "write the anchor"
and returned to the weekly. Families frozen at
enactment: `WF-6` step 4 (4h–4k since 4g), `ANS-4` step 2 (2a‴, 2e, 2f, 2g
since 2a″), `PORT-14` step 2 (2, 2b–2e; no gate landed) — each carries its
ruling in §7.


Last reviewed **2026-09-25, 03:00 review** (Friday; `claude-opus-5-5`, the
daily override through 09-29). Full journal:
`docs/planning/reviews/2026-09-25-daily.md`. Rulings that bind the next slots:

- **The ordinary `fem-em-solver` service was down from ≈ 2026-09-23 15:00 UTC to this review** (`Exited (137)`, cause not established; `20260925T080223Z_EX-57-next.log`: "service is not running"). This review started it (`20260925T080307Z_SERVICE-START.log`). A slot that finds it down runs `scripts/testing/run_and_log.sh SERVICE-START "docker compose up -d fem-em-solver"` once, **bare**, journals it and proceeds. Never `build`.
- Audit: `OPS-60` auditor DEMOTE(8) (the tier word) **overruled**; ✅ stands; tier re-labelled standard (§7 row). Nothing demoted.
- `WF-7` step 2's 38 sample points: **step 2 stands** (the 50 floor is `POST-6`'s fixture constant; §7 row). Item 39 reprints that reading on its refined phantom.
- `ANS-2` step 4 (`xl` 09-25) **ruled branch (a)**: spread 15.73 → 4.53 %, phantom powers ≤ 0.30 %; the pointwise band tightens to 4.53 % (§7 row, ledger).
- `ANS-4` 3g (`xl` 09-24): falling (ratios 1.93 / 1.94 / 1.67), but S₁₁'s last change 3.61 % (and S₃₁'s 1.10 %) exceeds 1.08 %, so neither branch holds as written. **The weekly rules; no slot touches `ANS-4`.**
- `OPS-63` opened (known-issues 2026-09-25): the `ans:2` example's unasserted "ASSERTED" labels and an AED figure in its tracked text. **Never write that figure** in a plan, journal or commit message.
- The 09-26 weekly's, not a slot's: `TH-17` gate (a), `ANS-6` adjudication, `PORT-21` step 2, T6 (`TH-19` step 4), H6 (`GEO-33` vs the strip-conductor note), `OPS-61`, `OPS-54`, B1 (`TH-5`). No slot opens `docs/private/` or `aed_results/`. No absolute `S₁₁` / `Z_in` at 10 or 64 MHz.
- Docker socket: call the harness **bare** — `scripts/testing/run_and_log.sh …` with nothing chained after it (`;`, `&&`, a pipe or a redirect is denied within 1 s; three this morning). Retry once, never park.
- Executors run foreground and never nest (item 42; the fallback paragraph below).
- XL: 6 of 6 charged in the trailing 7 days; ahead **4 `xl`** (09-27 3h, 09-28 3i, 09-29 `ANS-6` 2c = entry 14, 09-30 3j = entry 15, new) and **1 `xxl`** (09-26 `WF-7` 0d). Floors met. After 09-26 no `xxl` is pre-registered; that is the weekly's.
- Parked: five `attempt/*` kept (the 09-09 ruling; `attempt/OPS-50-…` pins `e2dd9ef`). No `recovered/*`. `.worktrees/census-before` is root-owned residue (operator).

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
three occurrences in 21 slots, intermittent; 0 of the last 35):** if
`./run_examples.sh` fails with
`permission denied … /var/run/docker.sock`, run the runner's inner command
verbatim through `run_and_log.sh` (`docker compose exec -T fem-em-solver
bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode &&
PYTHONPATH=/workspace/src timeout -k 30 <T> mpiexec -n 2 python3
examples/<path>.py'`) and journal the denial; do not spend the slot on it.
The host runner stays the documented entry point and the substitution
stays the fallback. **Allowlist trap (12:00 slot):** the harness entry is
the repo-relative `scripts/testing/run_and_log.sh *` — an absolute path is
denied; write it relative. **Dry-run shape (16:30 slot):** `--dry-run`
emits one `docker compose exec` line per example; chain them with `&&`
into legs.

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
noticed; a log without the readings is a window not spent. **(h) (added
2026-09-13 18:00)** an executor that re-registers a red anchor's
*comparand* in-slot (`TH-15` step 3, 15:00) does so as rule (f) allows only
when the new comparand measures the *same physics* as the old one and
says so; a substitute that is true by construction on the fixture (an
identity with one side removed by the mesh) is a **record**, and the item
stays at its pre-registered result — red — for the review to rule on.
**(i) (added 2026-09-13 18:00)** the window a step is closed on runs the
module **as committed**: if the module is edited after its last green
window (even a comment), the window is re-run before the commit, or the
row says it was not. **(j) (added 2026-09-14 03:00)** a review that writes
"**Status it can move:** `X` → ✅" first reads `X`'s §7 Done-when and either
matches it or amends the row in the same review commit; an executor that
meets a mismatch closes on the *row* (holds 🟡) and flags it, as the 21:00
slot did with `TH-14` — the §9 letter never outranks the row.


**Every window below that uses §5.1 durable capture copies the idiom
verbatim, trailing `; exit $rc` included.** Since `OPS-45` the footer honours
a `[capture] rc=` line only when it is the *last* output line. **Every pytest
window runs with `-s`** (rule (g)). **Every window runs inside the container
through `run_and_log.sh`** — host `python3` is denied.

*(Items 19–38 are collapsed to one line each below (daily-review.md step
6c); their execution text is in git (`9eb1e39` for 19–32, `099e2d5` for
33–38), their rulings in `docs/planning/reviews/2026-09-21-daily.md` /
`2026-09-23-daily.md`, their readouts in the §7 rows and
`docs/testing/attempts.md`.)*

19. DONE 2026-09-21 (04:30) — `OPS-60` ⬜ → 🟡: pin + version test; control `ModuleNotFoundError`; `f3fcdeb`; `20260921T093041Z_OPS-60.log`.
20. MOVED 2026-09-23 → item 34.
21. DONE 2026-09-21 (09:30) — `WF-7` step 1 🧪 → 🟡 (H3): F-human 32×32 identities; `182c90b`; `20260921T093429Z_WF-7-step1.log`.
22. DONE 2026-09-21 (09:30) — `PORT-21` step 1 closed on `main` (🟡, F3); `185ef70`; `20260921T094335Z_PORT-21.log`.
23. DONE 2026-09-21 (09:30) — `ANS-6` step 2 degree knob (T9b half); `612b8a4`; `20260921T100022Z_ANS-6-step2-degree2-64MHz.log`.
24. DONE 2026-09-21 — `TH-17` step 1c green (T5); `7e4bbab`; `20260921T110359Z_TH-17.log`.
25.–30. DONE 2026-09-21/22 — `OPS-59`, `OPS-50`, `OPS-55`, `OPS-56`, `OPS-57`, `OPS-58` ✅; audits PASS (one DEMOTE overruled) 09-23.
31. DONE 2026-09-21 — `EX-61` ✅; `0d66fdb`; `20260921T124138Z_EX-61.log`. 32. DONE — `EX-57` `mesh:9` / `mesh:10`.
33. DONE 2026-09-23 (04:30) — `OPS-60` 🟡 → ✅: `skrf=2.1.0` on the ordinary service, 12 passed, 39 s; `64f393c`; `20260923T093017Z_OPS-60.log`. Audit DEMOTE(8) (tier word) overruled 09-25, tier re-labelled standard.
34. DONE 2026-09-23 (04:30) — `PORT-23` step 1 ✅ (row 🟡): skrf `Circuit` = raw (C2) to ≤ 3.5e-16, swapped-port control 201.9× floor; `b84a5b8`; `20260923T093456Z_PORT-23.log`.
35. DONE 2026-09-23 (04:30) — `ANS-6` step 2b resolution knob: h = 0.015 reproduces tracked S to 2.647e-15; h = 0.0075 moves classes 1.15–2.86e-2; `b6e4004`; `xl` entry 14 READY → queued 09-29.
36. DONE 2026-09-23 (04:30) — `WF-7` step 2 (H4): `|B₁⁺|_ccw` C16 worst 0.1495 %, mirror 0.1634 %, identity 2.316e-16; 38 sample points ruled 09-25 (§7 row); `fb6a44d`; `20260923T095104Z_WF-7-step2.log`.
37. DONE 2026-09-23 (06:00) — `GEO-34` step 1a (row 🟡): STEP round trip, census = generator's, sheets to ≤ 2.2e-16, meshed/CAD 0.970165, both controls raise; `8fc56fc`; `20260923T110405Z_GEO-34.log`.
38. DONE 2026-09-23 (06:00 + three fallbacks) — `EX-57` `mesh:11`, `mesh:12`, `mat:1`, `mat:2`: census `missing` 31 → 27; `83f64c2`, `e0aa152`, `a60d87a`, `cabb2f3`.

**Predicted slot-minutes (rubric element 3 + 15 min fixed), running total
over the *open, unblocked* items:** item 39 → 60 · item 40 → 105 · item 41 →
145 · item 42 → **165**. **Floor 240: short by 75 min; items 4 of 5: short
by one** (2026-09-25 03:00 review). Every chain step a slot could execute
is queued or waits on the weekly (T6, F4, H6) or the operator (T10, F5).
The only other ready physics is the `xl` backlog, which cron runs.
The drained-queue `EX-57` fallback covers the gap; the weekly sees the
shortfall. **All four items are independent**, ordered physics first:
item 39 is the weekly's chain step H5 (rule (4)); 40 is `GEO-34` step 1b as
its row splits it; 41 is the defect this review opened; 42 is the standing
`EX-57` item.

39. DONE 2026-09-25 (04:30) — `WF-7` step 3 (H5) 🟡 → ✅: 10 g hotspot c* r 45 mm z_c, C16 worst 0.4904 %, mirror 0.0502 %, coverage 9.6e-14 / 1.3e-13; `20260925T093315Z_WF-7-step3.log`; rule (a) `20260925T093918Z_WF-7-step3-ruleA-step2.log`.

40. BLOCKED 2026-09-25 (04:30, take-next) — `GEO-34` step 1b negative result: on the import (iv) 0/90/180/270° exact, (i) 1.897e-14, (ii) σ_max 0.999992218 all pass, P2/P3-swapped control fails (iv) as asserted; **(iii′) misses** — self 3.3151 % / adjacent 1.1102 % / opposite 2.2713 % vs 0.5 %, separation 3.0514× vs 10× (primitive rule (a) re-run 0.0553/0.0353/0.0214 %, 166.6766×, green); parked `attempt/GEO-34-step1b-20260925T094541Z` (`92d03fa`); `20260925T094541Z_GEO-34-step1b.log`, `20260925T094757Z_GEO-34-step1b-ruleA.log`; known-issues 2026-09-25, attempts.md. **Unblock condition:** a review-designed probe of the import's per-port sheet congruence (x-axis vs y-axis legs differ: Z₁₁≈Z₃₃ ≠ Z₂₂≈Z₄₄; narrowed sheets 26/26/29/26 facets) and a fix to the import config/cut; bands never move. Item text kept below for the re-run.
   **`GEO-34` step 1b — `PORT-9`'s four-port gates at 10 MHz on the
   STEP-imported F-small mesh** (implementer; additive keyword
   `built=None` on `build_four_port_sweep`
   (`tests/validation/test_port_birdcage_four_port.py:219`). A tuple
   `(msh, cell_tags, facet_tags, diag, t_mesh)` replaces the `_build(True, …)`
   call at `:313–319` and nothing else; the hoist, the sheet rebuild, the
   `f = 0.5` narrowing, the specs and the sweep run as now. `None` ⇒
   byte-identical. The existing `reuse=` keyword is **not** the route: it
   skips the narrowing block (`:303–311`). New test
   `tests/mesh/test_step_import_four_port.py` (`FEM_EM_GEO34_STEP1B=1`),
   reusing step 1a's export/import (`tests/mesh/test_step_import.py`, its
   config `tests/mesh/data/geo34_fsmall_birdcage_step.json`); **rule (a):
   `test_port_birdcage_four_port.py` re-run green in-slot and disclosed**;
   **no `src/`**; standard; `-n 2`; complex build; independent;
   **45 slot-min**: one ≈ 2–3 min window + one ≈ 70 s re-run + 15 + writing).
   **Anchors (asserted, every band imported, none restated):** on the
   imported mesh at 10 MHz, degree 1: (i) reciprocity `‖S − Sᵀ‖/‖S‖` ≤
   `RECIPROCITY_BAND` 1e-3 (`test_port_lumped_sheet_sweep.py:86`);
   (ii) σ_max(S) and every column power sum ≤ 1 + `PASSIVITY_SIGMA_TOLERANCE`
   (`test_port_birdcage_four_port.py:129`); (iii′) the Z self / adjacent /
   opposite class spreads ≤ `ADJACENT_SPREAD_BAND` 0.5 %
   (`test_port_birdcage_lumped_column.py:121`), and control (2)'s pooled /
   worst separation ≥ `POOLED_SEPARATION_FLOOR` 10 (`:173`); (iv) a
   **cyclic-order pre-gate**: each sheet's measured azimuth (`:340–348`)
   equals 90°·(i − 1) mod 360 within `AZIMUTH_MATCH_DEG` 1e-6°
   (`tests/validation/test_port_birdcage_ring_column.py:158`, imported). A
   miss on the imported mesh prints the four azimuths; it is this item's
   negative result for the review, not a tolerance to move. `_circulant_classes` (`:193–216`) is
   pure index arithmetic, so a non-cyclic config would silently mix the
   adjacent and opposite classes.
   **Negative control (asserted, binary):** a copy of the config with the
   P2 and P3 port groups swapped makes the pre-gate (iv) fail with both
   azimuths named. Alongside it, **predicted and printed** (rule (e)): the
   same solve's Z with indices 2 ↔ 3 permuted, class spreads recomputed.
   The primitive record's adjacent 17.0085 Ω against opposite 16.0605 Ω
   (`20260914T004031Z_PORT-14-step3-port9-gate.log:1875–1906`) predicts
   ≈ 5.9 % against the 0.5 % band.
   **Do not assert** control (1), the leg-(d0) column at 1e-9 (`:598`). It
   is a digit record of the primitive mesh and fails by construction on a
   re-tessellated one: print its deviation, labelled "printed, mesh differs".
   **Printed, never gated:** cells (116 662 in 1a) beside 116 085; reciprocity,
   σ values, column sums and class spreads beside the primitive's
   1.044e-14 / 0.999992805 / 0.7938 / 0.0553 · 0.0353 · 0.0214 %; sheet
   azimuths; the `BOPAlgo` fragment warnings' count (1a's log `:1846`,
   harmless there); import, mesh and sweep seconds.
   **Tier / cost:** 1a's export + import + mesh 37.6 s plus the generator
   rung 27.3 s (`20260923T110405Z_GEO-34.log`); the four-drive sweep 7.2 s
   at `-n 2` on the primitive mesh, module 63.6 s
   (`20260914T004031Z_PORT-14-step3-port9-gate.log:1859,1971`) ⇒ one
   ≈ 2–3 min window, `timeout -k 30 300`, `-s`; rule (a) ≈ 70 s,
   `timeout -k 30 180`.
   **Traps:** the structural test's `out_of_plane < 1e-12` / `w < w_full`
   asserts (`:578–587`) have only met the primitive mesh — if one fails on
   the import, that is this item's negative result, not a tolerance to move;
   `birdcage_port_domain`'s overlapping-facets entries (known-issues
   2026-08-25 / 08-27) — keep the config's 1.6 mm conductor size; gmsh on
   rank 0 only; lower/upper halves of a port box are not distinguished by
   CAD volume (1a's comparison), harmless here because the sheet is the
   shared interface.
   **Scope:** the four-port gates on the imported mesh. Not the independent
   CAD kernel (1c), not the preflight (step 2), no cell record.
   **Status it can move:** the `GEO-34` row records step 1b (step 1's gate
   complete except 1c's kernel independence); the row stays 🟡.
   **Negative result:** any gate over its band on the imported mesh ⇒ the
   STEP round trip changes port-level physics beyond the bands. Report the
   classes beside the primitive's, open a known-issues entry, park on
   `attempt/*`, mark BLOCKED (rule (d)); this is the finding for the weekly.

41. DONE 2026-09-25 (06:00) — `OPS-63` ⬜ → ✅: the `ans:2` example now asserts the builders' ASSERTED-labelled checks (PORT-9 reciprocity 7.489e-15, σ_max 0.999993824, column sum 0.793794824, Z spreads 0.0551/0.0364/0.0211 %; containment 28.3650 mm < 30 mm; 10 g control 85.25–85.29 % > 5 %), AED figure replaced by a pointer, `:572` raw; knob route green 195 s `-n 4`, leaf identity worst 9.646e-11 ≤ 1e-10; census 2 → 0; `--audit` clean before and after; `20260925T110348Z_OPS-63.log`, `20260925T110725Z_OPS-63-leaf-identity.log`, `20260925T110045Z_OPS-63-audit-before.log`, `20260925T110729Z_OPS-63-audit-after.log`.

42. DONE 2026-09-25 (06:00 slot, take-next) — `EX-57` th:1 setup figure ⬜ → ✅ row: census `missing` 27 → 26 (`ok` 29 → 30), `broken=0`, docrefs `dead=0 guide=0 exit=2` unchanged (`20260925T111108Z_EX-57.log` → `20260925T111309Z_EX-57.log`, four logs); `TH-6`/`EX-4` records identical flagged (`20260925T111144Z_EX-57.log`, 17 s) vs unflagged (`20260925T111230Z_EX-57.log`, 15 s); `OPS-59` (b) 20 passed (`20260925T111251Z_EX-57.log`); PNG 60 KiB. Full record: §7 `EX-57` row.

43. DONE 2026-09-25 (06:00 slot, drained-queue fallback) — `EX-57` th:2 setup figure ⬜ → ✅ row: census `missing` 26 → 25 (`ok` 30 → 31), `broken=0` (`20260925T111503Z_EX-57-next.log` → `20260925T111635Z_EX-57.log`), docrefs `dead=0 guide=0 exit=2` both sides, `stale=10` unchanged (`20260925T111725Z_EX-57.log`); `TH-9`/`EX-5` records (four mode frequencies, `null_mode_count=0`, exported `|E|` span 2.156391e-17…1.0) identical flagged (`20260925T111617Z_EX-57.log`, 3 s) vs unflagged (`20260925T111732Z_EX-57.log`, 2 s); `OPS-59` (b) 20 passed after `git add`ing the PNG (`20260925T111705Z_EX-57.log`); PNG 87 KiB. Full record: §7 `EX-57` row.

44. DONE 2026-09-25 (07:30 slot, drained-queue fallback) — `EX-57` th:3 setup figure ⬜ → ✅ row: census `missing` 25 → 24 (`ok` 31 → 32), `broken=0` (`20260925T123026Z_EX-57-next.log` → `20260925T123230Z_EX-57.log`), docrefs `dead=0 guide=0 exit=2` both sides, `stale=10` unchanged (`20260925T123244Z_EX-57.log`); `TH-8`/`EX-6` records (interior `E_z` 2.442% vs 2.443% record, spread 0.080%, transverse 0.084%, `|Im|/|Re|` 0.0e+00, volume-vs-probe 0.014%, jump 59.20×/11.46×) identical flagged (`20260925T123139Z_EX-57.log`, 11 s) vs unflagged (`20260925T123155Z_EX-57.log`, 7 s), no `[setup-figure]` line in the unflagged run; `OPS-59` (b) 20 passed after `git add`ing the PNG (`20260925T123254Z_EX-57.log`); PNG 425 KiB. Full record: §7 `EX-57` row.

45. DONE 2026-09-25 (09:00 slot, drained-queue fallback) — `EX-57` th:4 setup figure ⬜ → ✅ row: census `missing` 24 → 23 (`ok` 32 → 33), `broken=0` (`20260925T140144Z_EX-57-pre.log` → `20260925T140447Z_EX-57-post.log`), docrefs `dead=0 guide=0 exit=2` both sides, `stale=10` unchanged (`20260925T140201Z_EX-57-pre-docrefs.log` → `20260925T140453Z_EX-57-post-docrefs.log`); `TH-7`/`EX-7` records (γ = 37.650399 Np/m vs closed form 37.652670, 0.006% vs 5% ceiling, rel L2 4.406648e-02, `|Im E_y|/|Re E_y|` 0.000e+00, CG1 cross-check 0.027%, transverse profile RMS 0.124%, sweep control ratio 2.6373 vs 2.6383 cited not re-run) identical flagged (`20260925T140403Z_EX-57.log`, 10 s) vs unflagged (`20260925T140500Z_EX-57-unflagged.log`, 6 s), no `[setup-figure]` line in the unflagged run; `OPS-59` (b) 20 passed after `git add`ing the PNG (`20260925T140512Z_EX-57-ops59b.log`); PNG 58 KiB. Full record: §7 `EX-57` row.

*(The per-review journal — slot recap, completion audits, plan-work notes,
§10 assessment — lives in the review commits and
`docs/planning/plan-archive.md`, not here.)*

If the queue drains: **take the next `EX-57` setup figure, then stop and
journal** (operator directive 2026-09-13 — the one standing fallback). Run
`python3 scripts/testing/check_example_setup_figures.py --next`; the path it
prints is the item, executed per the `EX-57` §7 entry (flagged harness run at
the example's recorded width, `git add` the PNG, `## Setup figure` section
with caption, both censuses, unflagged re-run, one commit). **The executor
runs foreground and does not nest** (added 2026-09-25 review, after the
09-23 `mat:1` breach: a spawned `example-runner` spawned a background
executor that resumed *after* the slot had committed). Prompt it "you are
the executor — do not spawn agents, never background a harness window", and
check `ListAgents` before committing. If the census
prints nothing (`missing=0`), **stop and journal** — there is no other
fallback: `PORT-9` step 3's legs are serial by design — (d) is not queued
until (d0) has a margin — and a review scopes each leg from the previous
one's number, not an implementer in-slot. `EX-36`, the former pre-authorised
exception, closed 2026-09-01 (`ae67b4c`). History of the birdcage-port hold
in `docs/planning/plan-archive.md`.

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

*(Superseded weekly blocks, 2026-08-09 … 09-06 — five pace ledgers, two agent-value measurements, the 09-02 rulings, the 09-02 and 09-06 Phase-5 exit assessments, examples health 09-06 — moved verbatim to `docs/planning/plan-archive.md` 2026-09-19. The current block of each kind is the 2026-09-13 one below; the trend is in `docs/status/weekly-progress.md` from 2026-09-19.)*

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

*(Phase-5 exit assessment 2026-09-09, including the dated scoping rule the 2026-09-13 exit decision applied: `docs/planning/plan-archive.md`, moved verbatim 2026-09-19.)*

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

*(Phase-5 exit assessments 2026-08-09 / 08-16 / 08-23: `docs/planning/plan-archive.md`, moved verbatim 2026-09-19.)*

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
- *2026-09-19 — "AGREE by mechanism" as a verdict class, killed.* The 09-13
  64 MHz `ANS-4` verdict was banked on a mechanism instead of a rung; the
  rung ran (`xl` 09-16) and its pre-registered rule fired on the self class.
  A verdict is read off a rung or it is INCONCLUSIVE.
- *2026-09-19 — the 09-13 "2–3 days per numbered step" forecast, killed.*
  Seven of ten chain steps landed in under a day; a closing step written
  after its diagnosis is priced by its own window, not its family's history.
- *2026-09-13 — the closed-form B₁⁺ band gate on F-small, killed.* A 2 % CG1
  floor cannot host a 5 % band with a 1.1 % comparand bar and a 3–8 % miss;
  subgoal 4 exits on the two-rung convergence statement (`WF-6` step 5 ✅).
  Revive only on a degree-2 or curved-geometry rung. Full text: archive.
- *2026-09-13 — `TH-14`'s Fresnel plane-wave step, retired as written.* At
  copper the Fresnel Γ differs from PEC by ≈ 4e-6, which no FEM band
  separates; the lossy-wall cavity Q replaced it and gated at +0.010 %.
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

*(Plan-hygiene note 2026-09-02: `docs/planning/plan-archive.md`.)*

**Ratification, 2026-08-16.** The `PORT-9`/`PORT-10` scoping, `ANS-3`
commissioning, plan prune, and attempts archival annotated "*weekly
planning review 2026-08-16*" were executed by the operator's interactive
session (the scheduled 01:30 slot died on the usage limit; `d21d228`
landed the tail). This review audited and ratifies them as weekly-scope
work — the annotations stand.

*(Superseded weekly blocks, 2026-09-09 and 2026-09-13 — assessment, pace ledger, third agent-value measurement, the Phase-5 exit decision, the three frozen families, the `ANS-4` Larmor verdict of 09-13, the `TH-19` / `POST-6` / `TH-11` 5d rulings, the tuned-birdcage chain as first written, XL/XXL, examples health, benchmarks, hygiene, flagged-for-the-daily — moved verbatim to `docs/planning/plan-archive.md` 2026-09-19. The current block of each kind is the 2026-09-19 one below.)*

**Pace ledger, interval 2026-09-13 09:50 → 09-19 21:00 CDT (6.47 days,
measured from `63eb49c`; sources: 111 commits, the attempts journal,
`20260920T020140Z_WEEKLY-COUNTS.log`; first interval on the wind-down
schedule, which began 09-13 19:00).** **22 items reached §4-✅:** five physics
chunks — `WF-6`, `POST-6`, `PORT-14`, `PORT-15`, `TH-14`; six `OPS` chunks
(`-47`, `-48`, `-49`, `-51`, `-52`, `-53`); six examples (`EX-54`, `-55`,
`-56`, `-58`, `-59`, `-60`); five gated steps outside them (`TH-19` step 3,
`TH-15` steps 3 and 3c, `ANS-4` 3a, `ANS-2` 4a). **22 / 6.47 = 3.40/day**
(09-13: 3.01), and for the first time since 08-23 the chunk column is physics:
**5 physics chunks / 6.47 d = 0.77/day** against 0/6 last interval. *The
number flatters and the split says why:* **all five physics chunks closed in
the first 17 hours** (09-13 12:07 → 09-14 04:50 CDT, still on the old
eight-slot day) — the three frozen families' single numbered steps, exactly
as the 09-13 review scoped them, each green on its first window because
the diagnosis had already been paid for. **In the 5.7 days after that, under
the wind-down, 16 implementer sessions closed zero physics chunks and one
gated physics step** (`ANS-2` 4a; `TH-17` step 1(i) and `ANS-2` step 4's probe
are honest negatives) — **0.18 physics steps/day.** Not a throughput limit: every
session fired (22/22, 6/6 dailies, zero died). It was **starvation** — from
09-14 07:30 the §9 queue held no physics because every open anchor was
weekly-owned and the weekly now comes once in 6.5 days; ≈ 8 of 22 sessions
were wholly or mostly `EX-57` setup figures (14 journal entries). The
operator's 09-18 directive (daily executes enumerated chain steps) is the
fix, and it only works if this section enumerates — which is what the three
chains below are for. Attribution by phase: Phase 0 six chunks; Phase 2 one
step (`TH-19` 3); Phase 5 one chunk (`WF-6`) plus the `ANS-2` verdict;
Phase 6 four chunks (`POST-6`, `PORT-14`, `PORT-15`, `TH-14`) and two steps.
Known-issues 3 opened by slots + 2 by this review / 3 retired by slots.
Progress against cost, and the continue / change decision:
`docs/status/weekly-progress.md` § 2026-09-19.

**The 09-13 forecast, audited.** It said "≈ 2–3 days per numbered step,
serial ⇒ steps 1–5 ≈ 10–15 days". Steps 1–4 and 6–8 — seven of ten — landed
in **under one day**. The estimate was wrong by an order of magnitude because
it took the families' *diagnosis-phase* rate for their *closing-step* rate.
Lesson recorded: a numbered step written after the diagnosis is priced by
its own window, not by its family's history. The forecast's other half
stands unrefuted and unsupported: step 5 (`TH-17`) has had one attempt, a
negative, so it has no rate at all.

**Phase 5 — exited on F-small, 2026-09-13.** `WF-6` step 5 ✅ (`8ad4548`)
registered the two-rung B₁⁺ convergence statement the 09-13 decision named;
`ANS-2` was adjudicated **AGREE** on rows 1–3 on 09-18 (operator's
interactive session in this review's form; read and **ratified** here — the
normalisation correction `e4697e9` is a convention fix on our side with the
AED file untouched, and the verdict's "residual = feed" reading is
independently consistent with the `ANS-4` self-class finding below). Honest
scope of the exit is unchanged from 09-13: symmetry-gated B₁⁺ at three
frequencies, a two-rung convergence statement, C4-gated 1 g / 10 g SAR at
10 MHz, one externally checked absolute SAR statement (`ANS-2` AGREE; the
agreement level is not repeated here — whether a relative level is
publishable is dashboard item 1, the operator's) — no homogeneity, compliance, Larmor-SAR or human-scale claim.
`ANS-2` step 4 (phantom h-halving) is `xl` entry 10, READY.

**Rulings, 2026-09-19 (protocol step 5 and the `xl` / `xxl` readouts owed to
this review; every AED figure is in the gitignored
`docs/private/ans3-ans4-adjudication-2026-09-19.md`).**

* **`ANS-3` — AGREE on the primary row; S rows DISAGREE, and the defect is
  ours.** The mutual coupling `Im Z₂₁` agrees with both AED orders (level
  private). The pre-read's "HFSS agrees with our raw ratio, not the
  corrected one" is **not adopted as written**: the two named systematics
  correct *the modelled problem toward the filamentary closed form*, and the
  AED model has the same PEC box and the same gaps, so they apply to both
  codes equally — code-to-code is raw-to-raw, and what AED adds is that the
  residual distance to the filament is shared by an independent solver, i.e.
  fixture physics, not our error. The 10 % mutual band is not re-pointed.
  Self rows: informative as pre-declared — our conductor loss reads low at
  fixed wire sizing. **S rows: our tabulated `S` on the current-drive route
  is not the 50 Ω S-matrix** (undriven port open ⇒ `a_i ≠ 0`); the same
  run's `Z` is right and its `z_to_s(Z)` agrees. Known-issues 2026-09-19;
  **`PORT-20`** opened with a closed-form done-when. Every lumped-sheet-route
  matrix in the repo is unaffected.
* **`ANS-4` step 3b (128 MHz, congruent cut) — rule did not fire.** Classes
  within step 2d's own spreads of step 2d's (≤ 0.083 % against ≤ 0.142 %);
  the cut is not a degree-2 systematic, **the 128 MHz AGREE stands as
  written**, and the 09-13 loose end is closed: the finest rung's rising C4
  spread was the sheet triangulation (`GEO-31`) — on the cut it is
  0.0056 / 0.0088 / 0.0070 %.
* **`ANS-4` step 3 (64 MHz) — the pre-registered private rule FIRED on the
  self class; couplings inside it.** "AGREE by mechanism at 64 MHz" is
  therefore **not** upgraded to evidence: it becomes AGREE on the coupling
  classes, **open DISAGREE on the self class**. The threshold is not moved.
* **`ANS-4` step 3c (10 MHz) — the public rule fired:** the degree 1 → 2 move
  4.41 / 1.35 / 1.08 % is in the same class as the Larmor moves, so **the
  09-06 "10 MHz AGREE", read at degree 1, was partly coincidental**; privately
  the order-matched self class disagrees there too. The shape — concentrated
  in `S₁₁`, *falling* with frequency — is not what fixed-`h` truncation does
  and is what a port-local reactance convention does; but each of 10 and
  64 MHz has one degree-2 rung, so neither is yet an `h`-converged value.
  Known-issues 2026-09-19; **`PORT-21`** opened; `xl` entry 11 (3g)
  pre-registered beside the daily's entry 7 (3e). **Consequence, public:** no
  absolute `S₁₁` / `Z_in` / match claim is licensed at 10 or 64 MHz at either
  order; §2.2 and §6 carry it.
* **`WF-7` step 0b (`xxl`) — branch (a).** F-human's degree 1 → 2 move on the
  driven entry is **5.50 %**, the same class as F-small's 6.51 / 2.60 / 4.11 %
  at 64 MHz ⇒ a human-scale S quoted at degree 1 carries that error and
  **degree 2 is the human-scale order**; its measured price is 3.26 M
  unknowns, **106.1 GiB peak, 348 s** for one drive at `-n 16`. `TH-16` does
  not move up (branch (c) excluded). *The reading the daily flagged:* the
  printed power-accounting residual is 1.104e-02 at degree 2 against
  4.187e-03 at degree 1. **Not ruled a degree-2 defect, and not dismissed:**
  the probe prints the *terminal* residual, which `PORT-16` showed is a
  κ-class quantity (≈ 1 % on F-small) and not an energy leak — the
  statement that would convict degree 2 is a failure of `PORT-16`'s **exact
  discrete** identity, which `TH-19` step 3 measured green at degree 2 on
  F-small (4.6e-15 / 8.9e-15). So chain H's first gated step (H3) asserts the
  exact identity at the imported 1e-6 and prints the terminal residual beside
  the in-run κ; until then the 1.1e-2 is an unattributed record.
* **`ANS-2` — ratified as closed; step 2 (rows 4–6, sphere-vs-cube averaging)
  stays the optional record the closing commit made it.** It is on no chain:
  the AED peak-averaged row is a boundary artefact of cube averaging and
  comparing against it licenses nothing. The SPEC's unticked box is accurate.
* **`GEO-33` (32-leg F-human rung, operator directive 09-15) — placed as
  H6**, after the 16-leg F-human 32×32 is priced and gated (H1, H3): its
  step 1 is a `GEO-25`-style cost rung and the 64-port price is only
  meaningful beside the 32-port one. Generic parameters only, per its row.
* **Production element order (`TH-19`, owed since 09-13) — target degree 2,
  default not flipped this week.** For: both fixtures identity-clean at
  degree 2 (`TH-19` steps 1–3), 128 MHz order-matched AGREE, branch (a)
  above, and the operator's stated preference. Against, new this week: at
  10 MHz the single degree-2 rung sits *farther* from the external code than
  degree 1 did, on the self class. **Pre-registered for the 09-26 weekly:**
  if 3e and 3g both show the degree-2 sequence `h`-converged (successive
  changes falling with ratio ≳ 1.5, the last below the smallest class move),
  the self-class disagreement is a model-level difference independent of
  order and **the default flips to degree 2 for lumped-sheet S work**, by a
  `TH-19` step 4 that re-records every degree-1 S record beside its degree-2
  value; if either ladder is not converged, the default stays and the ladder
  is the finding.

**Live chains — every open step numbered, with its validation target and
serial prerequisites (§9 rule (4): the daily review executes these at full
rubric grain; it does not need this review to come back first).**

*Chain T — the tuned F-small birdcage* (the 09-13 chain, steps 1–4, 6–8
landed 09-13/14 — archive). Open:

* **T5. `TH-17` step 1b → (ii) → (iii)** — as queued (§9) — closed-form LC
  control on a single PEC loop, target scan, sheet-mass norm, then mode 1
  within the κ systematic. Target: closed form + circuit consistency.
  Serial on nothing open.
* **T5′. `PORT-22` step 1** — the driven-sweep resonance, 44–84 MHz, gated on
  the circuit-vs-field identity at every grid frequency (§7 row). **Independent
  of T5**, and the fallback definition of "tuned" if T5 stalls.
* **T6. `TH-19` step 4** — the degree-2 default flip with re-records. Serial
  on the 09-26 weekly's ruling above; *not queueable before it*.
* **T9. `ANS-6` runnable half** — `ans:6` from the SPEC commissioned today
  (`examples/ansys_benchmarks/ans6_copper_birdcage_four_port_10_64_128MHz/SPEC.md`):
  Cu and PEC columns at 10 / 64 / 128 MHz, degree 1, every constant imported
  from `test_th14_birdcage_copper.py` and the `TH-15` step 3 module; gated on
  the imported identities and on reproducing `TH-14`'s printed `P_coil/P_in`
  0.929 / 0.448 / 0.219 at rtol 1e-6; writes `COMPARISON.md` with AED columns
  blank. Serial on nothing (`TH-14` ✅, `TH-15` step 3 ✅). Heavy (`TH-14`'s
  window: 211 s).
* **T9b. `ANS-6` order-matched rung** — a degree knob on T9's script, control
  = unset is digit-identical; then an `xl` cost probe on the hole mesh at
  h = 0.005 degree 2 (no priced point exists on the *hole* mesh — fewer cells
  than `ANS-4`'s, no conductor interior). Serial on T9.
* **T10. `ANS-7`** — HFSS + Circuit tuned case; SPEC written by the weekly
  that adjudicates `ANS-6`. Serial on T5 or T5′, T9 and the operator.

*Chain F — the feed model (new; it gates every absolute `S₁₁`).*

* **F1. `PORT-20` steps 1–3** — current-route S = `z_to_s(Z)`, closed-form
  identity at 1e-12, negative control the present assembly. Serial on nothing.
* **F2. `xl` entries 7 (3e, 09-22) and 11 (3g)** — are the 64 and 10 MHz
  degree-2 rungs `h`-converged? Cron, zero tokens.
* **F3. `PORT-21` step 1** — the public sensitivity table of `S₁₁` to three
  port conventions at three frequencies; identities asserted, table printed.
  Serial on nothing.
* **F4. `PORT-21` step 2** — this review reads F3 against the private
  residual, 09-26 or the weekly after F2 and F3 exist.
* **F5. `ANS-6` PEC column adjudication** — removes the conductor interior
  from both codes. Serial on T9 and the operator.

*Chain H — human scale (F-human, 32 ports).* *(Step numbers under `WF-7`
are this chain's; the daily reconciles them with the row's own history when
it writes the items.)*

* **H1. `WF-7` step 0c (`xl`, queued 09-21)** — degree-1 price of the full
  32-drive set under factor reuse. Decides whether the F-human 32×32 is an
  ordinary heavy job.
* **H2. `WF-7` step 0d (`xxl`, queued 09-26)** — the same at degree 2.
* **H3. `WF-7` step 1 — the F-human 32×32 at 64 MHz, degree 1, gated on
  `PORT-13`'s three identities** (reciprocity ≤ 1e-3, σ_max ≤ 1 + 1e-9, the
  18 C16 × mirror classes at the imported band), negative control the
  mis-paired sheet orientation, **plus `PORT-16`'s exact discrete power
  identity at the imported 1e-6 on the driven columns, the terminal residual
  printed beside the in-run κ** (the 0b reading above). Target: identities.
  Serial on H1's price (tier declared from it). *Self-consistency only;
  carries the 5.50 % order caveat in its own row.*
* **H4. `WF-7` step 2 — ccw quadrature `|B₁⁺|` at human scale**, `POST-6`
  step 3's C16-invariance gate imported unchanged, from H3's kept fields.
  Serial on H3.
* **H5. `WF-7` step 3 — 10 g SAR hotspot location**, gated on the C16 / mirror
  identity of the hotspot set and on `MAT-4`'s coverage identity; the
  location table printed. Serial on H4. *The first human-scale safety
  quantity; still one phantom, no compliance claim.*
* **H6. `GEO-33` step 1 — the 32-leg F-human cost rung** (cells, meshability,
  the imported mesh identities; 🧪). Serial on H1 and H3. Not before them.

**Phase 6 date, with the arithmetic.** Open numbered steps across T, F, H:
**17** (T: 6, of which 5 slot-executable; F: 5, of which 2; H: 6, of which 4 — the
rest are cron windows, weekly rulings or the operator). Slot-executable: **11**. Measured rates this interval: numbered chain steps
7 / 6.47 d = 1.08/day overall, **0.18/day under the wind-down while
starved**. 11 / 1.08 ≈ 10 days; 11 / 0.18 ≈ 61 days ⇒ **between 2026-09-30 and
2026-11-19 for the slot-executable steps**, the width being exactly the
starvation this review is trying to end; the next ledger narrows it or the
range was dishonest. The operator's AED queue, last week's stated longest
pole, **returned two cases in two days** (`ANS-2` 09-18, `ANS-3` 09-19) and
now holds one (`ANS-6`): that reason for "no date" is retired. Phase 6's
terminal claim (tuned `S₁₁` matched to AED, T10) still has no date — it is
serial on chain F, which is a disagreement under diagnosis, and nobody can
date a diagnosis. **Watch condition for 09-26:** if neither T5 has located
mode 1 nor T5′ has landed, "tuned" is re-scoped to the driven-sweep
definition and `TH-17` drops to a mode-spectrum record.

**Agent value, fourth measurement.** (a) Auditor: one DEMOTE that mattered —
`TH-14`'s 21:00 ✅ was demoted by the 09-14 03:00 review on the row's own
Done-when (the slab step unexecuted) and re-closed the same morning with
the step run: the mechanism worked as designed. Keep. (b) Pathologist: **2
invocations** (ledger rows `ANS-4-step3b`, `WF-7-step0b`), both CONFIRMED
countable, 0 OVERRULED — first non-zero interval; keep at opus. (c) Review
completion: 6 of 6 dailies `ok`, this weekly alive in its new Saturday
window. (d) Navigator: not measured this week. (e) Example-runner: six
`EX` closures; a 09-16 journal entry records an *executor delegation
anomaly* (`dd2b35b`) — read by the daily, not re-audited here. (f)
Mesh-probe: 0 invocations. Footers: six at 2026-08-31 (19 days),
`implementer.md` 2026-09-13 — none over 30 days. All tiers unchanged.

**XL and XXL slots, 2026-09-19 (protocol step 3b).** Ledgers read; the four
RUN entries (1–4) are ruled above and marked in `xl-pending.md`. The daily's
backlog (entries 5–9, queued through 09-23 and the 09-26 `xxl`) is **kept
whole** — 3d (64 MHz on the cut) and 3f (10 MHz on the cut) matter more now
than when they were written: 3c's 10 MHz self-class spread sits at 89 % of
its band and the cut is what removes that from the 10 MHz reading. Entry 10
(`ANS-2` step 4) stays READY for the first free night. **Commissioned today:
entry 11, `ANS-4` step 3g** — the 10 MHz degree-2 `h`-ladder, 3e's command
with the frequency varied, priced by the same family (2d, step 3, 3c).
`xxl`: entry 9 holds the 09-26 window; nothing further is priced at that
tier, so nothing further is commissioned. Budget: six `xl` per trailing
7 days, four queued + two READY = full.

**Examples health, 2026-09-19 (step 4; delegated sweep, citations
re-read).** **54 runnable examples** (+6: `EX-54`, `-55`, `-56`, `-58`,
`-59`, `-60`), every one with a guide and all required sections, `dead=0
guide=0` (`20260919T125104Z_EX-57.log:111–112`); `stale=16` artifacts
across 13 examples older than the 14-day window (oldest `ports:8`, 442.8 h)
— information by `OPS-19`, no chunk opened. Ramp (gating ✅ / ramp /
examples): Phase 1 6 / 5 / 5; Phase 2 ≥ 5 / 5 / 10; Phase 3 3 / 3 / 4;
Phase 4 4 / 4 / 5; **Phase 5 6 / 5 / 7** (`WF-6` ✅ → `EX-56`); **Phase 6
10 / 5 / 14** (`POST-6` → `EX-55`, `PORT-14` + `PORT-15` → `EX-58`, `TH-14`
→ `EX-59` + `EX-60`, `TH-15` step 3 → `EX-54`). **No shortfall** — the
daily's step-5 mechanism fired on every gate closure this interval. `EX-57`:
20 of 54 setup figures. It is useful and it is not the mission; see the
progress file's decision.

**Benchmarks, 2026-09-19 (step 5, both directions).** *Adjudicated:* `ANS-3`
(above), `ANS-2` ratified, `ANS-4`'s three order-matched readouts ruled.
`ANS-1` stands. *Commissioned:* **`ANS-6`** — `TH-14` ✅ is the gated-physics
milestone since the last case, the operator's 09-04 directive names it, and
its PEC column is the cleanest discriminator available for chain F. SPEC is
self-sufficient for the AED half; it goes to the top of the dashboard's
Waiting-on-you list. `ANS-7` is not opened: it is serial on a tuned
resonance that does not exist yet.

**Plan hygiene, 2026-09-19.** Rotation first, committed alone (`846589a`):
`attempts.md` 14 194 → 2 037 lines under the new 7-day window (162 entries,
zero-loss); `TH-14` and `PORT-15` closed narratives to the archive behind
result blocks; known-issues rotation a no-op. This block's predecessors
(09-09 and 09-13) moved verbatim in the same session (`history`, zero-loss
on 36 262 lines): `PROJECT_PLAN.md` 5 517 → ≈ 5 000 lines with this block in. The 4 000-line
guide is still unmet and the residue is §9 (≈ 930 lines, daily-owned) and
§7's open rows; this review does not chase it further.

**Flagged for the 2026-09-20 03:00 daily review — not weekly-owned.**

1. **Queue from the chains, physics first:** F1 (`PORT-20`, smoke +
   standard), T5′ (`PORT-22` step 1, heavy), F3 (`PORT-21` step 1, heavy),
   T9 (`ANS-6` runnable half, heavy) are all serial on nothing and mutually
   independent; with T5 (`TH-17` 1b, already queued) that is five
   independent physics items — more than a wind-down day consumes.
2. **Queue `xl` entry 11 (3g)** and entry 10 into the first free nights.
3. `START_HERE.md` lists `EX-55` as ⬜ while its row reads "Closed ✅
   2026-09-14" — the row's leading glyph is stale; one-character fix, then
   regenerate the index.
4. `ANS-3`'s and `ANS-4`'s §7 rows and §2.1 / §2.2 should carry this
   review's verdicts in the daily's own wording (the §6 cells and
   known-issues already do); `ANS-3`'s SPEC checkbox "Adjudication" is
   ticked by this review.
5. The red `test_the_in_tree_exemption_cannot_silently_widen` on `main`
   (known-issues 2026-09-19) has no chunk; it is a smoke-tier item.
6. Dashboard: `ANS-6` added to Waiting-on-you by this review; the state
   digest's S-parameter row needs the self-class caveat.

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
