# FEM-EM Solver — status

**Updated:** 2026-08-31 10:30, **daily review (scheduled, ran normally)**.
Headline: **a third clean interval — four slots, four landings, `ANS-5`
closed, and the first Larmor-frequency B₁⁺ numbers are on record.** `WF-6`
step 2b ran the five B₁⁺ symmetry identities at 64 and 128 MHz on one mesh
and every one held inside the unmoved 5% band down to 12.5 phantom
cells/λ — the CG1 estimator floor measured at 10 MHz survives the full
frequency ladder. The `TH-13` matched source projection landed and does
exactly what the mechanism predicted (residue to ~1e-16, the spurious
degree-2 electric energy collapses to 0.02% of record) — opt-in, loop
fixture only, the coil untouched. What this does **not** say: the Larmor
B₁⁺ figures (mean 6.5e-8 / 4.9e-8 T at 1 V/port, CV ≈ 2.8–3.0%) are
identities on one unconverged fixture — no homogeneity, tuning, absolute
or SAR claim; and one owed regression re-run (`test_coil_loading_degree2`)
was killed at its unchanged ceiling, so the two degree-2 coil identity
reds are unverified on the newest commit (re-run queued first). Source of
truth is `PROJECT_PLAN.md`; this page is a read-only digest for the human
operator.

## Waiting on you

1. 🟢 **`ANS-4` is ready to replicate — both halves exist.**
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/` (script,
   `metrics.json`, `COMPARISON.md` with our column filled and two blank AED
   columns, a 128 MHz XDMF). Per the `ANS-5` ruling — now in every
   `SPEC.md`, the README **and the generated `COMPARISON.md` tables**
   (`ANS-5` closed 06:00 slot): AED at **Zero Order** (adjudication
   column) and at its default **First Order** (sensitivity column), Mixed
   Order not; please confirm the unknowns-per-tet figure AED prints.
   Ranks above `ANS-1`/`ANS-3`. Adjudication is the 09-06 weekly review's.
2. 🟢 **`ANS-3` and `ANS-1` AED runs** — still yours, behind `ANS-4`. Both
   scripts runnable and green (re-verified 06:00 slot); their
   `COMPARISON.md` tables now carry the two AED columns and a `Basis
   order` row. If you have **already** run either at an unrecorded order,
   say which — the numbers stand as an "order-unknown" column.
3. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
4. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
5. FYI, no action — the 09-06 weekly review owes: the `GEO-25` and
   `PORT-13` rulings; the §10 pass; the `TH-12` production-order clause;
   the `TH-13` "step 3b" sheet-drive formulation question; and two new
   flags from this interval — the honest regeneration control for
   `ANS-3`-class sweeps (run-to-run solver scatter measured at ~1e-8–5e-8,
   so byte-level `metrics.json` controls are invalid there) and whether
   `WF-6` should get a convergence rung for an *absolute* `|B₁⁺|` claim.
   The docker-socket denial did not fire in any of the last 8 slots.
   Local `main` remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — B₁⁺ row moved this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11 (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere. The degree-2 "explosion" on volume-driven fixtures is diagnosed **and now fixed where the fix can reach**: the opt-in `project_source="matched"` projection lands the residue at ~1e-16 on the loop fixture (`TH-13` step 3a, 🟡 pending one blocked regression re-run); the **coil's** degree-2 identity failure stays open and is out of that fix's reach |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only.** Absolute accuracy at Larmor is `ANS-4` — AED replication pending (Waiting-on-you 1) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | production high-pass layout is an example (`EX-35` ✅); no solve on it yet (`PORT-13`, ruling owed) |
| B₁⁺ / coil-driven SAR | 🧪 computed; symmetry-gated at CG1 **at 10, 64 and 128 MHz**, not homogeneity-gated | `WF-6` steps 1–2b ✅ (08-30/31): single-drive + quadrature identities all inside the unmoved 5% band at all three frequencies on one 116 085-cell mesh (gate (ii) 1.89–2.22%, quadrature 0.70–0.98%, controls 23–25% / 95%); phantom cells/λ 69.1 / 21.9 / **12.5** vs floor 10 — no resolution miss. **Ungated, labelled:** mean `\|B₁⁺\|` 7.98 / 6.50 / 4.94e-8 T at 1 V/port, centre purity 128 / 142 / 172, CV 2.76 / 2.77 / 3.02%. SAR on the coil is step 3, scoped this review (§9 item 2); still **no homogeneity, absolute, tuning or SAR claim** |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil — first coil-driven SAR identities are §9 item 2 |
| Test-suite trust | ✅ census complete; **residual reds on `main` at `-n 2`: 4 deliberate/known** — 2 placeholder-route names, `test_birdcage_volumes_partition_the_box`, `TH-13`'s precondition (re-point ruled, §9 item 6); plus the two degree-2 **coil** identity tests at 1e-9 (open, diagnosed, **unverified on the newest commit** — re-run is §9 item 1) | example-artifact census `dead=42` (was 53; `EX-36` leg (th) ✅, legs (mesh)+(root) paired as §9 item 5, (ports+ans) the drain fallback); 10 artifacts age-stale, none physics |

## Recent activity (2026-08-31 03:00 → 10:30)

- **04:30:** `TH-13` step 3a — the matched projection landed: residue
  1.3e-2 / 1.0e-1 → **8.1e-17 / 1.8e-16** (vs ≤ 1e-8), spurious `W_e`
  collapses to 0.018% / 2.6e-4 % of record, default path bit-identical
  (0.000e+00). **🟡, not ✅:** the owed `test_coil_loading_degree2.py`
  re-run was killed at its unchanged 570 s ceiling (exit 124). The slot's
  "mesh regression" diagnosis was **corrected by this review**: the same
  mesh built in 4.5 s the same morning — the module simply has a 5%
  margin; instrumented re-run queued first.
- **06:00:** `ANS-5` step 1b — both `COMPARISON.md` generators emit the
  two AED columns + `Basis order` row; `ans:1`/`ans:3` green on their own
  asserts. **Chunk ✅** (audited COMPLIANT). Bonus finding, measured with
  an unedited-generator control: the ≤ 1e-8 `metrics.json` control was
  solver scatter, not a physics-path signal — recorded, band not widened.
- **07:30:** `EX-36` leg (th) — all eight `time_harmonic` examples green
  on their gate records in 83 s; census **53 → 42 dead**, the group at
  0 dead / 0 stale. **Leg ✅, chunk 🟡.**
- **09:00:** `WF-6` step 2b — the five B₁⁺ identities at **64 and
  128 MHz**, green on the first run (202 s): every reading inside the
  unmoved bands, 10 MHz rung reproducing all records at rtol 1e-3, first
  Larmor B₁⁺ figures on record (ungated). The pre-registered 128 MHz
  resolution question: **no miss** at 12.5 cells/λ.
- **10:30 review:** audited `ANS-5` and `WF-6` step 2b COMPLIANT;
  corrected the coil-mesh known-issues diagnosis by reading (mesh
  excluded, 4.5 s evidence); ruled the `TH-13` precondition re-point;
  scoped `WF-6` step 3 (coil-driven SAR identities); commissioned `EX-40`
  (Larmor `|B₁⁺|` ladder example); paired the two cheap `EX-36` legs;
  refilled §9 with six independent items.

## Automation health

- **4 of 4 scheduled slots did chunk work; 3 ✅ + 1 🟡** (the 🟡 is a
  blocked re-run, not a failed anchor — both its anchors hit with 6–14
  orders of margin). Third consecutive clean interval: zero stops, zero
  wedges, zero parked branches. Container Up 4 days.
- The one exit 124 was handled per protocol: ceiling not raised, entry
  filed, container verified healthy — and this review's reading corrected
  the entry's diagnosis before it could misdirect a slot.
- Docker-socket denial on the host runner: **0 of 8** slots over two
  intervals — intermittent; the substitution remains documented.
- Queue holds **six independent items** (five ready + spare); `EX-36`
  leg (ports + ans) is the pre-authorised drain fallback.

## On deck (§9 — six independent items this review)

1. **`TH-13` step 3a″** — the owed coil regression re-run, instrumented
   with `-s`, ceiling unchanged; green re-verifies the two degree-2 coil
   identity reds and closes the known-issues ceiling entry (≈ 550 s)
2. **`WF-6` step 3** — coil-driven SAR symmetry identities at 10 MHz via
   `post.point_sar` on the solved birdcage field; first SAR-on-a-coil
   readings, symmetry-gated only (standard, ≈ 120 s)
3. **`EX-38`** — `ports:6`, the first `|B₁⁺|` field in ParaView at 10 MHz
   (standard, ≈ 70 s)
4. **`EX-39`** — `ports:7`, the quadrature `|B₁⁺|`/`|B₁⁻|` maps side by
   side (standard, ≈ 100 s)
5. **`EX-36` legs (mesh) + (root + mri + mat), paired** — census toward
   `dead=0`; also clears the 10 age-stale artifacts (≈ 950 s in windows)
6. *(spare)* **`TH-13` step 4** — re-point the deliberate precondition red
   at the matched path, band unchanged; `main`'s deliberate reds 4 → 3
   (≈ 50 s)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
