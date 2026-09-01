# FEM-EM Solver — status

**Updated:** 2026-09-01 03:00, **daily review (scheduled, ran normally)**.
Headline: **three of four slots landed — `EX-40` ✅ (the 64/128 MHz
`|B₁⁺|` maps in ParaView, first run green), the `TH-13` coil degree-2
identity reds finally *observed* (3.90e-09 / 3.72e-09 against the
unloosened 1e-9, one per σ-half, after a module split), and `WF-6` step
3b's negative result relocating the SAR finding to the projector
(`project_to_cg1` misfits an N1curl `E` by 1876% over the phantom).** The
fourth slot — the **first to delegate to a specialist executor** after
your 23:32 commit — died at minute 19 with no journal and a dirty tree:
`example-runner` returned with a harness window still running and the
slot ended its turn waiting; the headless CLI's 600 s background ceiling
terminated it. Seven of nine meshing examples came back green anyway; the
review landed the logs, journaled the anomaly, wrote the executor rule
into the implementer protocol, and needs one launcher line from you
(below). No SAR claim exists; no quantitative §2 claim moved. Source of
truth is `PROJECT_PLAN.md`; this page is a read-only digest for the
human operator.

## Waiting on you

1. 🔴 **One launcher line, please — the review could not write it.**
   `scripts/automation/implementer-run.sh` (under `scripts/automation/`,
   outside a review session's write scope): add
   `export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` immediately before the
   `timeout --kill-after=120 3900 "$CLAUDE_BIN" \` line, with a comment
   pointing at the 2026-09-01 00:00 anomaly entry. Effect: a slot that
   ends its turn with a background task (a spawned executor, a
   backgrounded harness) is bounded by the existing 65-minute kill
   instead of being terminated after 600 s mid-run. The protocol rule
   (implementer-run.md step 3, fourth rule: executors foreground, never
   end the turn with one in flight) is already in force; this is the
   backstop for a slot that ignores it. Until you add it, the next
   delegated slot that backgrounds dies the same way.
2. 🟢 **`ANS-4` is ready to replicate — both halves exist.**
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/` (script,
   `metrics.json`, `COMPARISON.md` with our column filled and two blank AED
   columns, a 128 MHz XDMF). Per the `ANS-5` ruling: AED at **Zero Order**
   (adjudication column) and at its default **First Order** (sensitivity
   column), Mixed Order not; please confirm the unknowns-per-tet figure AED
   prints. Ranks above `ANS-1`/`ANS-3`. Adjudication is the 09-06 weekly
   review's.
3. 🟢 **`ANS-3` and `ANS-1` AED runs** — still yours, behind `ANS-4`. Both
   scripts runnable and green; their `COMPARISON.md` tables carry the two
   AED columns and a `Basis order` row. If you have **already** run either
   at an unrecorded order, say which — the numbers stand as an
   "order-unknown" column.
4. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
5. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
6. FYI, no action — your df38553 worked as intended on the tool side: the
   00:00 slot did reach `example-runner`, and the guard hook was not the
   problem. What failed is the foreground rule in its delegated form
   (item 1). The `log-pathologist` overruled the review's own first
   reading of that log (a "240 s Bash default" kill — the log says 267 s
   and does not name the mechanism), which is what the agent is for.
7. FYI, no action — the 09-06 weekly review owes: the `GEO-25` and
   `PORT-13` rulings; the §10 pass; the `TH-12` production-order clause;
   the `TH-13` "step 3b" sheet-drive formulation question (the coil reds
   are now observed, unchanged in value); the honest regeneration control
   for `ANS-3`-class sweeps; whether `WF-6` gets a convergence rung for an
   *absolute* `|B₁⁺|` claim; and, after step 3c reports, what the honest
   coil-driven `E`/SAR estimator is (phantom-restricted or cellwise). Local
   `main` remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — no quantitative row moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere. The degree-2 "explosion" on volume-driven fixtures is diagnosed and fixed where the fix can reach (`TH-13` step 3a, opt-in, loop fixture); the **coil's** two degree-2 identity reds are open and **observed 2026-09-01** at 3.8990e-09 / 3.7235e-09 vs 1e-9 (one σ-half per window, 374 / 405 s at `-n 8`) — a formulation question for the weekly review |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); the degree-1 coil control re-observed three times this interval at +1.5838% vs the +1.5834% record; Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` — AED replication pending (Waiting-on-you 2) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | production high-pass layout is an example (`EX-35` ✅); no solve on it yet (`PORT-13`, ruling owed) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; **in ParaView at all three frequencies** | `WF-6` steps 1–2b ✅; `EX-38` (single drive), `EX-39` (quadrature) and now `EX-40` (64 / 128 MHz ladder, 113 s, audited PASS) ✅ with every gate record reproduced to ≤ 1e-5. Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🔴 **measured, not gateable yet — and the CG1 route is worse** | step 3: point SAR off the primal N1curl `E` misses all five identities at **25–41%** vs 5%. Step 3b (this interval): the CG1-projected `E` reads **152 / 110 / 170 / 53 / 41%**, primal column reproduced to every digit, and the diagnostics — CG1 phantom power **+35 199%**, `‖E_cg1 − E‖/‖E‖` **1876%** over the phantom — say `post.project_to_cg1` is not a usable `E` estimator as landed. Five deliberate reds on `main`, band unmoved; step 3c (projector diagnosis: KSP convergence, exact-reproduction control, whole-mesh / core errors) is §9 item 6. **No SAR claim exists** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never gated on a coil |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 9 deliberate/known** — 2 placeholder-route names, `test_birdcage_volumes_partition_the_box`, `TH-13`'s precondition (re-point is §9 item 5), and the five `WF-6` step-3 SAR asserts; plus the two degree-2 **coil** identity tests at 1e-9 (open, observed, `-n 8` only) | example-artifact census `dead=42` / `stale=4` pre-leg on 09-01; `mesh:1`–`mesh:7` regenerated since (unmeasured post-leg); `EX-36` items 4 / 7 / 8 finish it |

## Recent activity (2026-08-31 18:00 → 2026-09-01 03:00)

- **19:30:** `WF-6` step 3b — verdict (c) printed, then relocated by the
  run's own diagnostics: the CG1-`E` column is **worse** than the primal
  at every identity, both CG1 controls survive, and the projection
  misfits `E` by 1876% over the phantom (CG1 phantom power 19× the
  record). The finding is the projector, not the phantom's resolution.
  `5 failed, 25 passed` / 105 + 100 s; no band moved. 🟡.
- **21:00:** `EX-40` — `ports:8`, the 64 / 128 MHz `|B₁⁺|` maps: gate (i)
  9.5231e-03 / 9.2445e-03, CG1 covariance **2.2187% / 2.1315%** vs 5%,
  mis-rotated control 24.75 / 25.26% at 11.2× / 11.9×, cells/λ 21.89 /
  12.50 above the floor of 10, one mesh. 113 s. **✅, audited PASS**
  (`…020415Z_EX-40.log:4708, :4726, :4756` re-traced by the review).
  This slot also found `example-runner` unreachable and fell back to the
  implementer prompt — the finding behind your df38553.
- **22:30:** `TH-13` step 3a‴ — the module split: probe-mode original
  8 passed / 49 s; `loaded` and `free` halves 1 failed each at **374 /
  405 s** under the unraised 600 s ceiling, residuals **3.8990e-09 /
  3.7235e-09** vs 1e-9 — the first observation of those reds since
  08-18, every anchor (138 490 cells, ΔR +0.00039 pp, cost probe) seen
  three times. 570 s-ceiling known-issues entry retired. 🟡 step, chunk ✅.
- **23:32, operator:** df38553 — implementer slots can spawn the seven
  repo agents; built-in agent types denied by name; guard hook verified
  inside subagents.
- **00:00:** `EX-36` legs (mesh) + (root) via `example-runner` — **died
  unjournaled at minute 19** (see headline). On record after the review's
  recovery (`b94034f`): pre-census `dead=42 stale=4`; `mesh:1`–`5` Status
  0 / 113 s; `mesh:6`/`7` green in a footerless window; `mesh:8`
  unwitnessed, `mesh:9` not run.
- **03:00 review:** audited `EX-40` PASS; `log-pathologist` ruling on the
  killed log (5 confirmed, 1 of the review's own readings overruled);
  outage cleared (logs landed, anomaly journaled by the review); executor
  rule written into implementer-run.md and the review rubric; `WF-6` step
  3c scoped; `EX-36` re-cut into three independent items; queue refilled
  to five.

## Automation health

- **3 of 4 scheduled slots did chunk work (1 ✅ + 2 🟡 delivered in
  full); 1 slot died** — the first delegated slot, on the
  foreground/background rule in its new subagent form (no journal, dirty
  tree for 2 h 40 min, no later slot tripped on it because none ran).
  Zero parked branches. Container Up 5 days.
- The exit-124 discipline held again at 22:30: the case was shrunk, the
  ceiling was not raised, and the reds became observable.
- Docker-socket denial on the host runner: **0 of 16** slots over four
  intervals.
- Queue holds **five independent items**; no drain fallback remains
  (the old one is item 8).

## On deck (§9 — items 4–8, all independent)

4. **`EX-36` leg (mesh) remainder** — `mesh:8` and `mesh:9`, one window
   each, census before/after (`example-runner` **spawned foreground**,
   660 000 ms Bash timeout per window; ≈ 4 min)
5. **`TH-13` step 4** — re-point the deliberate precondition red at the
   matched path, band unchanged; deliberate reds 9 → 8 (≈ 50 s)
6. **`WF-6` step 3c** — is `project_to_cg1` a projector on N1curl input?
   KSP converged reason asserted > 0, exact reproduction of `a + b × x`
   ≤ 1e-10 with `x² ê_x` as the control's control, whole-mesh / phantom /
   phantom-core errors printed; no band moves (≈ 130 s)
7. **`EX-36` leg (root + mri + mat)** — `1,2,4,5,6`, `mri:1`, `mri:2`,
   `mat:1` from the repo root in four windows (`example-runner`,
   foreground; ≈ 12 min)
8. **`EX-36` leg (ports)** — `ports:1`, `ports:2`, `ports:3` in three
   windows; `ans:*` and `ports:4–8` are fresh (`example-runner`,
   foreground; ≈ 11 min)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
