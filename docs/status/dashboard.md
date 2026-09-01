# FEM-EM Solver — status

**Updated:** 2026-09-01 18:00, **daily review (run interactively at the
operator's request, following the scheduled protocol).**
Headline: **`EX-36` closed and the example corpus is clean for the first
time since the 08-28 rename — `dead=0 guide=0 stale=0 exit=0` — and
`WF-6` step 3d built an `E` estimator that is finally honest.** The
phantom-restricted CG1 projection cuts the phantom residual from 1876% to
**18.72%** (a 100× separation, asserted as a best-approximation
inequality) and brings the phantom power to within **−3.51%** of the
primal record where the global fit was off by +35 199%. The five SAR
symmetry identities improve 3–6× to **6.1–9.5%** — and still miss the 5%
band at all five, so the pre-registered verdict is **(c)**, this time
uncontradicted by its own diagnostics: what is left is the fixture's ~1 cm
phantom cells, not the estimator. **No SAR claim exists and no band
moved.** Two slots (15:00, 16:30) correctly drained and journalled rather
than inventing work; this review refilled the queue with four newly
scoped items. Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

## Waiting on you

1. 🟢 **`ANS-4` is ready to replicate — both halves exist.**
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/` (script,
   `metrics.json`, `COMPARISON.md` with our column filled and two blank AED
   columns, a 128 MHz XDMF). Per the `ANS-5` ruling: AED at **Zero Order**
   (adjudication column) and at its default **First Order** (sensitivity
   column), Mixed Order not; please confirm the unknowns-per-tet figure AED
   prints. Ranks above `ANS-1`/`ANS-3`. **Adjudication is now the
   2026-09-02 weekly review's** — the Wednesday slot, not 09-06.
2. 🟢 **`ANS-3` and `ANS-1` AED runs** — still yours, behind `ANS-4`. Both
   scripts runnable and green; their `COMPARISON.md` tables carry the two
   AED columns and a `Basis order` row. If you have **already** run either
   at an unrecorded order, say which — the numbers stand as an
   "order-unknown" column.
3. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
4. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
5. FYI, no action — **both of yesterday's automation blockers are cleared,
   and this review verified each.** `194a20c` warned that the review roles
   were pinned to `claude-fable-5-1` while the local CLI (2.1.250) could
   not send it, exposing the 02:15 Wednesday weekly and the 03:00 daily;
   `claude --version` now reads **2.1.258**, above the required 2.1.251.
   `6501ad9` recorded that `scripts/automation/crontab` was not installed;
   `crontab -l` shows the live spool already carries `15 2 * * 0,3`, so
   **the first mid-week weekly runs tomorrow at 02:15**. The only lag left
   is the tracked crontab file's header comment, which still says "Sunday
   02:15" — harmless, and folded into `OPS-31` as collateral.
6. FYI, no action — **the queue drained today and has been refilled.**
   Items 8 and 9 landed at 12:00 and 13:30 as predicted, so 15:00 and
   16:30 stopped and journalled by design. A `plan-navigator` sweep of the
   whole of §7 confirmed **no other entry carries a written, unexecuted,
   anchor-bearing step**, so this review *scoped* four new items rather
   than finding them, and says plainly that it found four and not five —
   they cover the four slots before the 02:15 weekly, which is the refill.
   Local `main` remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — no quantitative row moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere. The **coil's** two degree-2 identity reds stay open, observed 2026-09-01 at 3.8990e-09 / 3.7235e-09 vs 1e-9 — a formulation question for the weekly review |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`), `mat:1` at +1.5838% vs the +1.5834% record; Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` — AED replication pending (Waiting-on-you 1) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | production high-pass layout is an example (`EX-35` ✅); no solve on it yet (`PORT-13`, ruling owed by the 09-02 weekly) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; in ParaView at all three frequencies | `WF-6` steps 1–2b ✅; `EX-38` / `EX-39` / `EX-40` ✅. These gates project **`B`** on the whole mesh (0.38%) and are **untouched** by every SAR finding below. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🔴 **measured, not gateable — and now, for the first time, the estimator is exonerated too** | step 3: primal point SAR misses all five identities at **25–41%** vs 5%. Step 3b: the global-CG1 `E` reads **41–170%** (worse). Step 3c: the projector *is* a projector (reason 2 / 26 its; `a + b × x` to 1.3e-13) — the **use** was wrong, a global L² fit fits the sheet edges (32.8% whole mesh / **1876%** phantom). **Step 3d (this interval): the phantom-restricted estimator is honest** — residual **18.72%** (100.20× separation, asserted), phantom power **−3.51%** from the primal record, `x² ê_x` control 3.74e-01, pinned dofs exactly 0, six solves reason 2 — **and the five identities still miss at 6.1–9.5%**, so verdict **(c)**: the fixture's ~1 cm phantom cells. Five deliberate reds on `main`, band unmoved. **No SAR claim exists** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never gated on a coil |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 8 deliberate/known** — 2 placeholder-route names, `test_birdcage_volumes_partition_the_box`, and the five `WF-6` step-3 SAR asserts; plus the two degree-2 **coil** identity tests at 1e-9 (open, observed, `-n 8` only) | example-artifact census **`dead=0 guide=0 stale=0 exit=0`** at 17:12Z — the **first clean corpus-wide census since the 08-28 rename**, down from `dead=53` on 08-29 |

## Recent activity (2026-09-01 10:30 → 18:00)

- **12:00:** `EX-36` leg (ports + ans) via `example-runner` — three
  windows 141 / 228 / 182 s, all Status 0; `EX-18`'s `‖S − Sᵀ‖/‖S‖`
  **3.1121e-05** and `‖S‖₂` 0.861357 to the digit, `ports:3` reproducing
  `STEP1_CROSS_ROUTE_RECORD` 0.077431 at 1e-4; post-census **`dead=0
  guide=0 stale=0 exit=0`**. **`EX-36` ✅ — chunk closed.**
- **13:30:** `WF-6` step 3d — `5 failed, 52 passed` / Status 1 / **123 s**,
  every anchor green on the first run. Restricted residual **18.7238%** vs
  the global fit's 1876.1871%; `a + b × x` to 4.385695e-13; 170 free of
  21 397 owned CG1 blocks, pinned max exactly 0.000e+00 at `-n 2`;
  phantom power 5.440097168e-08 W (−3.51%). Five identities **8.2868 /
  9.4743 / 7.3477 / 6.8146 / 6.1185%**, both controls surviving
  (123.6255 / 333.0778%) — verdict **(c)**. Nothing under `src/`. 🟡.
- **15:00 and 16:30:** drained queue — **stopped and journalled**, no
  compute issued, no item invented. Both cross-checked the completed
  items against `git log` rather than trusting §9's glyphs, and both
  flagged that lag to this review.
- **17:23 / 18:22, operator:** `6501ad9` (Wednesday weekly), `54c8bd4` +
  `194a20c` (Fable 5.1 pin restored), and the CLI update to 2.1.258.
- **18:00 review:** `EX-36` audited — `auditor` **PASS** on all eight
  checks, and the review re-traced the census, S-matrix and footer digits
  itself. Nothing demoted. The item 4–7 glyph lag retired at the source
  (queue rewritten). Four new items scoped: `WF-6` **step 3e** (promote
  the restricted projector into `post/`) and **step 3e′** (the
  estimator-degree rung), **`OPS-30`** (two filed `scripts/probes/` 0.11
  survivors) and **`OPS-31`** (the stale `ports:3` narrative ladder). All
  "09-06 weekly" deferrals re-pointed to **09-02**.

## Automation health

- **4 of 4 scheduled slots completed**; 2 did chunk work, 2 correctly
  drained. Zero parked branches, zero anomalies, tree clean at every
  preflight. Container Up 6 days.
- **Foreground-executor rule: 3 for 3** since it was written (03:00).
  No docker-socket denial this interval (**3 of 20** slots overall).
- **Both launch-time blockers cleared and verified** — CLI 2.1.258 ≥
  2.1.251 for the `claude-fable-5-1` pin; live crontab carries
  `15 2 * * 0,3`. **First mid-week weekly planning review: 2026-09-02
  02:15.**
- One convention question handed to that weekly: the host-runner
  `example-runner` legs are labelled tier **standard** but their longest
  window measured **228 s**, above §5.1's literal 180 s ceiling. A
  repo-wide labelling convention (`EX-30` ran 105 / 447 / 935 s under the
  same label), not a new overrun — every window stayed inside its stated
  400–500 s Bash ceiling. Nothing re-tiered here.

## On deck (§9 — four items, independent, for the four slots before the 02:15 weekly)

1. **`WF-6` step 3e** — promote `_project_to_cg1_restricted` into `post/`
   as `project_to_cg1_restricted`; anchors are step 3d's records
   reproduced through the packaged path, negative control the global
   projector's 1876.1871% (≥ 50× separation). Plus the docstring warning
   on `project_to_cg1`. No gate registered *(implementer; ≈ 130 s)*
2. **`OPS-30`** — the two filed `scripts/probes/` 0.11 survivors take a
   `petsc_options_prefix`; the survivor-set pin moves in the same commit
   (it goes red in either direction). Anchor: the migration sweep reads
   **0** where it reads 2 today *(implementer; smoke, < 60 s)*
3. **`OPS-31`** — re-record the `ports:3` cross-route narrative from the
   v0.7.2 triple `7.7095 → 3.6730 → 1.8333%` to the 0.11 image's
   **7.7431 → 1.0986 → 1.9222%**. Dated §7 history keeps its figures;
   only forward-looking sites move *(`record-reconciler`; ≈ 230 s)*
4. **`WF-6` step 3e′** — the estimator-degree rung: the same five
   identities off a **CG2**-restricted `E`, separating estimator degree
   from mesh h for six mass solves and no curl-curl solve. Anchors are
   theorems (residual cannot increase with degree; `x² ê_x` is exact in
   CG2, a nine-decade flip). The **null** result is the informative one
   *(implementer; ≈ 250–400 s, ceiling 600 s)*

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy was republished by this interactive session.*
