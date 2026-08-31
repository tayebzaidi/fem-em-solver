# FEM-EM Solver — status

**Updated:** 2026-08-31 18:00, **daily review (scheduled, ran normally)**.
Headline: **a fourth clean interval — four slots, four landings: the first
two `|B₁⁺|` fields in ParaView (`EX-38`, `EX-39`, both ✅ on their first
run), and two negative results delivered in full.** `WF-6` step 3 put the
first coil-driven SAR readings on record and they **miss** every symmetry
identity by 25–41% against the 5% band the `|B₁⁺|` map meets at ~2% — the
controls, the σ premise and the power record all hold, so the finding is
the pointwise-`E` estimator, not the field; five deliberate reds are filed
and no band moved. `TH-13`'s owed coil regression re-run was killed a
second time at its unchanged ceiling, but instrumented: the mesh is 4 s,
the degree-1 half is green and unmoved, and the degree-2 pair alone eats
≥ 524 of 571 s — the review has ruled a module split so those two reds can
finally be observed. What this does **not** say: no SAR claim of any kind
exists (not homogeneity, not absolute, not C95.3); the `|B₁⁺|` figures
remain identities on one unconverged fixture. Source of truth is
`PROJECT_PLAN.md`; this page is a read-only digest for the human operator.

## Waiting on you

1. 🟢 **`ANS-4` is ready to replicate — both halves exist.**
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/` (script,
   `metrics.json`, `COMPARISON.md` with our column filled and two blank AED
   columns, a 128 MHz XDMF). Per the `ANS-5` ruling: AED at **Zero Order**
   (adjudication column) and at its default **First Order** (sensitivity
   column), Mixed Order not; please confirm the unknowns-per-tet figure AED
   prints. Ranks above `ANS-1`/`ANS-3`. Adjudication is the 09-06 weekly
   review's.
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
5. FYI, no action — your six subagent definitions (`83e71ef`, `eb3e608`,
   `7989f61`) were used for the first time by this review: two `auditor`
   runs on `EX-38`/`EX-39`, both PASS, each with one digit re-traced by the
   review as the protocol now requires through 09-03. The 16:30 slot saw
   your concurrent commit as a momentarily dirty tree and correctly did
   not park anything.
6. FYI, no action — the 09-06 weekly review owes: the `GEO-25` and
   `PORT-13` rulings; the §10 pass; the `TH-12` production-order clause;
   the `TH-13` "step 3b" sheet-drive formulation question; the honest
   regeneration control for `ANS-3`-class sweeps; whether `WF-6` gets a
   convergence rung for an *absolute* `|B₁⁺|` claim; and, new this
   interval, whether point-SAR on this fixture needs a finer rung if step
   3b returns its verdict (c). The docker-socket denial did not fire in
   any of the last 12 slots. Local `main` remains well ahead of origin
   (push is manual).

## Honest current state (digest of §2 — SAR row moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere. The degree-2 "explosion" on volume-driven fixtures is diagnosed and fixed where the fix can reach (`TH-13` step 3a, opt-in, loop fixture); the **coil's** two degree-2 identity reds are open and **still unobserved since 08-18** — the module has no margin at degree 2 (measured this interval); split ruled, §9 item 3 |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); the degree-1 coil control re-observed this interval at +1.5838% vs the +1.5834% record; Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` — AED replication pending (Waiting-on-you 1) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | production high-pass layout is an example (`EX-35` ✅); no solve on it yet (`PORT-13`, ruling owed) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; **now in ParaView** | `WF-6` steps 1–2b ✅; `EX-38` (single drive) and `EX-39` (quadrature, `\|B₁⁺\|`/`\|B₁⁻\|` side by side) ✅ this interval with every gate record reproduced to ≤ 4e-5; `EX-40` (64/128 MHz maps) queued. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🔴 **measured, not gateable yet** | `WF-6` step 3 (this interval): point SAR off the primal N1curl `E` misses all five C4/mirror identities at **25–41%** vs 5% while both controls (130 / 335%), the σ premise and the power record (to every digit) hold — the pointwise-`E` estimator floor, ~2× a ~13–20% `\|E\|` floor. Five deliberate reds on `main`, band unmoved. Step 3b (CG1-`E` estimator beside it) is §9 item 1. **No SAR claim exists** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never gated on a coil |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 9 deliberate/known** — 2 placeholder-route names, `test_birdcage_volumes_partition_the_box`, `TH-13`'s precondition (re-point is §9 item 5), and the five `WF-6` step-3 SAR asserts; plus the two degree-2 **coil** identity tests at 1e-9 (open, unobserved since 08-18 — §9 item 3 makes them observable) | example-artifact census `dead=42` / `stale=12` (`EX-36` legs (mesh)+(root) are §9 item 4, (ports+ans) the drain fallback) |

## Recent activity (2026-08-31 10:30 → 18:00)

- **12:00:** `TH-13` step 3a″ — the instrumented coil re-run: **second
  exit 124 at 571 s**, ceiling unchanged, no third retry. The `-s`
  timeline and a 49 s probe-mode run partition the window: mesh 4.3 s,
  degree-1 phase 46.8 s and green (ΔR +0.00039 pp of record, identity
  residuals ~1e-15), **degree-2 pair ≥ 524 s and unfinished**. Half the
  owed claim is now measured; the two degree-2 reds are still unobserved.
  🟡, disposition taken by this review (split).
- **13:30:** `WF-6` step 3 — coil-driven point-SAR symmetry identities at
  10 MHz: **all five miss** (25.11 / 40.55 / 30.01 / 38.61 / 28.15% vs
  5%), both controls hold, `mean_sar` reproduces the power record to every
  digit. Pre-registered negative result; five deliberate reds filed. One
  scoped control found degenerate for a magnitude-squared quantity
  (28.1445 vs 28.1459%) — reported, not asserted, and now struck. 🟡.
- **15:00:** `EX-38` — `ports:6`, the first `|B₁⁺|` field in ParaView:
  gate (i) 9.7958e-03 (record to 1.2e-08), CG1 covariance **2.1870%** vs
  5%, DG0 control 8.6516% at 3.96× — the estimator floor visible as two
  colour arrays. 63 s. **✅, audited PASS.**
- **16:30:** `EX-39` — `ports:7`, the quadrature drive: identities
  **0.9818 / 0.8087%** vs 5% (records to ≤ 3.6e-05), mis-paired control
  95.1975% at 118×, purity 127.9 / 0.0081. Also exported step 2's records
  from the gate module (constants only). 81 s. **✅, audited PASS.**
- **Operator, between slots:** six specialist subagent definitions +
  shadow-replay validation logs (`AGENT-VAL`), wired into the review and
  implementer protocols.
- **18:00 review:** audited `EX-38`/`EX-39` PASS (one `auditor` each, one
  digit re-traced per report); ruled the `TH-13` coil module split (one
  σ-half per window — the 660 s Bash window is the binding limit, not the
  heavy tier); scoped `WF-6` step 3b (CG1-`E` estimator, pre-registered
  three-way verdict, no band moves in-slot); queued `EX-40`; restated the
  deliberate-red count (9); refilled §9 with five independent items.

## Automation health

- **4 of 4 scheduled slots did chunk work; 2 ✅ + 2 🟡** (both 🟡 are
  negative results delivered in full with every control green, not failed
  anchors). Fourth consecutive clean interval: zero stops, zero wedges,
  zero parked branches. Container Up 5 days.
- The exit 124 was handled per protocol again: ceiling not raised, no
  third retry, and the slot spent its remaining time on a 49 s
  measurement that settled the diagnosis. One allowlist trap journaled
  (absolute path to the harness is denied; relative works).
- Docker-socket denial on the host runner: **0 of 12** slots over three
  intervals — the substitution remains documented.
- Queue holds **five independent items**; `EX-36` leg (ports + ans) is
  the pre-authorised drain fallback.

## On deck (§9 — five independent items this review)

1. **`WF-6` step 3b** — the same five SAR identities off an L²-projected
   CG1 `E` beside the primal column; primal readings asserted as records,
   CG1 readings printed with a pre-registered (a)/(b)/(c) verdict; no band
   moves (standard, ≈ 130 s)
2. **`EX-40`** — `ports:8`, the 64 / 128 MHz `|B₁⁺|` maps in ParaView
   (`example-runner`, standard, ≈ 130 s)
3. **`TH-13` step 3a‴** — split the coil degree-2 module, one σ-half per
   window under a 600 s ceiling; expected exactly one identity red per
   half — the first observation of those reds since 08-18 (≈ 12 min
   compute in three windows)
4. **`EX-36` legs (mesh) + (root + mri + mat), paired** — census toward
   `dead=0` / `stale=0` (`example-runner`, ≈ 950 s in windows)
5. **`TH-13` step 4** — re-point the deliberate precondition red at the
   matched path, band unchanged; deliberate reds 9 → 8 (≈ 50 s)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
