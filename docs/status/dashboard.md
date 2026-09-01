# FEM-EM Solver — status

**Updated:** 2026-09-01 10:30, **daily review (scheduled, ran normally)**.
Headline: **four of four slots landed, nothing parked, no anomaly — the
first clean interval since the specialist executors went live.** `EX-36`
is one leg from closing (meshing, magnetostatics, MRI and materials
example groups all read `dead=0 stale=0`; only `ports:1`–`3` remain);
`TH-13`'s discriminator module is **exit 0 for the first time** (the
deliberate precondition red re-pointed at the matched path, 3.42e-06 vs
1e-2, band unchanged, deliberate reds 9 → 8); and `WF-6` step 3c
**exonerated the projector** — `project_to_cg1` reproduces `a + b × x` to
1.3e-13 and its mass solve converges — while the domain table named the
real defect: a *global* L² fit of `E` on a fixture whose sheet edges carry
fields 10³× the phantom's fits the sheets (32.8% whole-mesh error) and
hands the phantom the tail (1876%). Your 07:23 launcher line (`e53211a`)
landed the backstop the 03:00 review asked for. The foreground-executor
rule held in both delegated slots. No SAR claim exists; no quantitative
§2 claim moved. Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

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
5. FYI, no action — **the launcher backstop is retired from this list**:
   your `e53211a` (07:23) put `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` in
   `implementer-run.sh` with the anomaly cited. Both delegated slots since
   (04:30, 09:00) also obeyed the protocol rule, so the backstop has not
   yet been needed.
6. FYI, no action — **the queue will drain today.** Only two items are
   ready (`EX-36`'s last leg; `WF-6` step 3d), so the 15:00 and 16:30
   slots will stop and journal. That is by design: every anchor that
   would make a third item ready is owed by the 09-06 weekly review
   (`GEO-25`, `PORT-13`, `PORT-4`…`8`, `TH-13` step 3b's sheet-drive
   formulation ruling, the `TH-12` production-order clause, `ANS-2`, the
   `ANS-3`/`ANS-4` scatter question, `WF-6`'s absolute convergence rung).
   Local `main` remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — no quantitative row moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11 (`MAG-20` ✅). Re-observed today by the `EX-36` leg: Helmholtz centre `B_z` 0.92 / 0.34 / 1.34% rows, gauge cross-check under the `MAG-15` ceilings, `mag 6` fitted rate 1.9038 |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere. The degree-2 "explosion" on volume-driven fixtures is diagnosed and fixed where the fix can reach (`TH-13` step 3a, opt-in, loop fixture; the discriminator module is now **exit 0**, its precondition measuring the matched path at 3.42e-06 vs 1e-2); the **coil's** two degree-2 identity reds stay open, observed 2026-09-01 at 3.8990e-09 / 3.7235e-09 vs 1e-9 — a formulation question for the weekly review |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); `mat:1` re-observed today at +1.5838% vs the +1.5834% record; Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` — AED replication pending (Waiting-on-you 1) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | `mesh:8` / `mesh:9` re-run today reproduce `EX-33`'s cost rung and `GEO-20` step 2's 265 621 cells at 0.000e+00 relative; production high-pass layout is an example (`EX-35` ✅); no solve on it yet (`PORT-13`, ruling owed) |
| B₁⁺ | 🧪 computed; symmetry-gated at CG1 at 10, 64 and 128 MHz, not homogeneity-gated; in ParaView at all three frequencies | `WF-6` steps 1–2b ✅; `EX-38` / `EX-39` / `EX-40` ✅. The CG1 `B` projection these gates use is **untouched** by the SAR finding (step 3c: the projector is exact where both spaces agree; `B` has no 10³ field contrast). Still **no homogeneity, absolute or tuning claim** |
| Coil-driven SAR | 🔴 **measured, not gateable yet — the projector is exonerated, the *use* is the defect** | step 3: primal point SAR misses all five identities at **25–41%** vs 5%. Step 3b: the global-CG1 `E` reads **152 / 110 / 170 / 53 / 41%**. Step 3c (this interval): mass solve converges (reason 2, 26 its), `a + b × x` reproduced to **1.3e-13**, `x² ê_x` control 9.9e-02 — so `project_to_cg1` is what it says; `‖E_cg1 − E‖/‖E‖` = **32.8% whole mesh / 1876% phantom / 839% phantom core** says a global fit is a fit of the sheet edges. Step 3d (§9 item 9, scoped today): the phantom-restricted estimator, anchored on a best-approximation inequality, five identities read under 3b's pre-registered verdict. Five deliberate reds on `main`, band unmoved. **No SAR claim exists** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never gated on a coil |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 8 deliberate/known** — 2 placeholder-route names, `test_birdcage_volumes_partition_the_box`, and the five `WF-6` step-3 SAR asserts; plus the two degree-2 **coil** identity tests at 1e-9 (open, observed, `-n 8` only) | example-artifact census **`dead=2 stale=2`** at 14:10Z (from `dead=53` on 08-29) — every remaining line is `ports_01`–`03`, `EX-36` item 8's; a green item 8 should read `dead=0 stale=0 exit=0` |

## Recent activity (2026-09-01 03:00 → 10:30)

- **04:30:** `EX-36` leg (mesh) remainder via `example-runner` — `mesh:8`
  108 s and `mesh:9` 103 s, both Status 0, records at 0.000e+00 relative;
  `meshing_*` census `dead=0 stale=0`, post-census `dead=23 stale=2` as
  predicted. Docker-socket denial hit (3rd time in 17 slots), substitution
  used. ✅ leg; chunk 🟡.
- **06:00:** `TH-13` step 4 — `test_degree2_gradient_discriminator.py`
  **19 passed / 1 skipped / exit 0 / 38 s**, first green; matched-path
  `W_e/W_m` **3.424858e-06** vs the unchanged 1e-2, default-path
  1.926692e-02 now the asserted `>` control; every other record to the
  digit; `git diff -- src/` empty. Deliberate reds 9 → 8.
- **07:23, operator:** `e53211a` — the launcher backstop.
- **07:30:** `WF-6` step 3c — `5 failed, 38 passed` / 103 s; candidates 2
  and 3 refuted (reason 2 / 26 its; 1.326607e-13 vs 1e-10; control
  9.882703e-02), candidate 1 measured (32.78 / 1876.19 / 838.90%); every
  3b record now asserted; opt-in `return_diagnostics` on
  `project_to_cg1`, default path untouched. 🟡.
- **09:00:** `EX-36` leg (root + mri + mat) via `example-runner` — four
  windows 142 / 84 / 137 / 73 s, all Status 0; `mat:1` ΔR 1.5838%;
  post-census **`dead=2 stale=2`**, exactly as predicted; the
  rename-orphaned `.gitignore` pattern fixed. ✅ leg; chunk 🟡.
- **10:30 review:** digits re-traced in all four logs (no ✅ to audit);
  `WF-6` step 3d scoped (item 9); truncated duplicate journal entry
  removed; two stale §7 glyphs (`OPS-18`, `MAG-18`) reconciled to their
  own 08-23 closure text; runner-trap count corrected; queue honestly
  holds two items.

## Automation health

- **4 of 4 scheduled slots did chunk work and completed** (two `example-
  runner` legs, two `implementer` runs). Zero parked branches, zero
  anomalies, tree clean at every preflight. Container Up 5 days.
- **Foreground-executor rule: 2 for 2** since it was written (03:00);
  the launcher backstop is in place and untested by need.
- Docker-socket denial on the host runner: **3 of 17** slots; 1 of the
  last 5. Substitution stays the fallback.
- Queue holds **two independent items**; slots 3 and 4 of this interval
  will drain and journal — expected, see Waiting-on-you 6.

## On deck (§9 — items 8 and 9, independent)

8. **`EX-36` leg (ports)** — `ports:1`, `ports:2`, `ports:3` in three
   windows; closes the chunk if green (`example-runner`, foreground;
   ≈ 11 min)
9. **`WF-6` step 3d** — the phantom-restricted CG1 `E` estimator on the
   parent mesh; best-approximation inequality asserted against the 1876%
   record, exact-reproduction control under the restriction, five SAR
   identities printed under 3b's pre-registered verdict; no band moves
   (`implementer`, foreground; ≈ 130 s)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
