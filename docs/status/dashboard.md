# FEM-EM Solver — status

**Updated:** 2026-08-31 03:00, **daily review (scheduled, ran normally)**.
Headline: **a second clean interval — four slots, four landings, two chunks
closed (`TH-13`, `EX-37`), `WF-6` step 2 green, `ANS-5` half landed.** The
`TH-13` mechanism the 18:00 review read off the code is now measured: the
degree-2 electric-energy "explosion" is the drive's *unremoved* gradient
residue answered through Ohm's law (identity to 1e-11, the residue's
size accounts for the 63.7× lift to four digits). The quadrature birdcage
drive passes both symmetry identities below 1% with a centre polarisation
purity of 128 — ungated, one fixture, 10 MHz. This review also established
that the `TH-13` projection fix **cannot reach the coil** (the lumped-sheet
drive bypasses the projection), so the coil's degree-2 identity failure is
a formulation ruling for the weekly review, not a queue item. Nothing in
§2 moved. What this does **not** say: no B₁⁺ homogeneity/CV claim, nothing
compared against an external reference at 64/128 MHz, nothing tuned or
resonant, no SAR on a coil. Source of truth is `PROJECT_PLAN.md`; this
page is a read-only digest for the human operator.

## Waiting on you

1. 🟢 **`ANS-4` is ready to replicate — both halves exist.**
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/` (script,
   `metrics.json`, `COMPARISON.md` with our column filled and two blank AED
   columns, a 128 MHz XDMF). Per the `ANS-5` ruling, now written into every
   `SPEC.md` and the benchmarks README (00:00 slot): AED at **Zero Order**
   (adjudication column) and at its default **First Order** (sensitivity
   column), Mixed Order not; please confirm the unknowns-per-tet figure AED
   prints. Ranks above `ANS-1`/`ANS-3`. Adjudication is the 09-06 weekly
   review's.
2. 🟢 **`ANS-3` and `ANS-1` AED runs** — still yours, behind `ANS-4`. Our
   two scripts are runnable again (`EX-37`, 19:30 slot — both green on
   their own asserts). Their `COMPARISON.md` tables still show a single
   `AED` column while the SPECs ask for two; §9 item 2 fixes the generator.
   If you have **already** run either at an unrecorded order, say which —
   the numbers stand as an "order-unknown" column.
3. **Information — automation fix from the 08-30 10:30 review, still
   awaiting your OK:** `docs/automation/weekly-review.md` has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
4. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
5. FYI, no action — the 09-06 weekly review owes: the `GEO-25` and
   `PORT-13` rulings; the §10 pass (your 08-25 `N ≤ 25` directive); the
   `TH-12` production-order clause, now with `TH-13`'s verdict in hand;
   and a **new** formulation question this review surfaced — whether a
   lumped-*sheet* port drive's discrete divergence (the coil's degree-2
   229×) should be projected out at all (`TH-13` "step 3b"). The host
   runner's docker-socket denial did **not** fire in any of the four slots
   this interval (previously 2 of 3). Local `main` remains well ahead of
   origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11; the sibling sampled band validated by measurement (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere. The degree-2 electric-energy "explosion" on volume-driven fixtures is now **diagnosed** (`TH-13` ✅ 08-31: unremoved gradient residue of the CG1/H¹₀-only source projection, identity at 1e-11); the opt-in matched projection is §9 item 1; the **coil's** degree-2 identity failure stays open and is out of that fix's reach |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; every Dodd–Deeds module green on 0.11 with version-tagged cell counts (`OPS-27` ✅) |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; `EX-34` ✅ 08-28; `ANS-4` runnable half ✅ 08-30) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only.** Every gated birdcage digit reproduces at `-n 2` and `-n 12` (`GEO-24` ✅); two-torus parallel drift bounded (`PORT-12` ✅). Absolute accuracy at Larmor is `ANS-4` — AED replication pending |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | `GEO-18`/`19`/`20`/`24` ✅; the production high-pass layout (16 legs, 32 ring sheets, 265 621 cells) is an example (`mesh:9`, `EX-35` ✅); no solve exists on it yet (`PORT-13`, ruling owed) |
| B₁⁺ / coil-driven SAR | 🧪 computed; symmetry-gated at CG1, not homogeneity-gated | `WF-6` steps 1–2 ✅ (08-30/31): single-drive `\|B₁⁺\|` on the loaded F-small birdcage at 10 MHz, power accounting 9.80e-3 (band 1e-2), C4 covariance **2.19 / 2.11 / 1.89% vs 5%**; quadrature drive by exact superposition — C4-invariance **0.98%**, co/counter-rotating mirror identity **0.81%** vs 5%, mis-paired control 95%. **Ungated, labelled:** centre purity 127.9, mean `\|B₁⁺\|` 7.98e-8 T at 1 V/port, CV 2.76%. 64/128 MHz is §9 item 4 (first Larmor B₁⁺ numbers); SAR on a coil (step 3) unscoped |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ census complete (452/478 observed on 0.11); **residual reds on `main` at `-n 2`: 4, one a pre-registered physics gate held red on purpose** — 2 placeholder-route names (entry 3, `PORT-0/1`), `test_birdcage_volumes_partition_the_box` (`GEO-21`'s floor entry), `TH-13`'s precondition (deliberate, 1 MHz row); plus the two degree-2 **coil** identity tests at 1e-9 (known-issues, open, diagnosed) | example-artifact census `dead=53 exit=1` since the 08-28 rename (`EX-36`, §9 item 3 + drain fallback); `ans:1`/`ans:3` runnable again (`EX-37` ✅); 10 artifacts age-stale (> 48 h), none physics |

## Recent activity (2026-08-30 18:00 → 2026-08-31 03:00)

- **19:30:** `EX-37` — negative control on unpatched `main` red with the
  `ModuleNotFoundError` in the log (3 s), two import strings restored,
  `ans:1` 63 s (ΔR 1.5838% vs 2%) and `ans:3` 128 s (`PORT-1` record
  inside 1%) green; `metrics.json` physics reproduced to ≤ 3e-9. **Chunk
  ✅**, known-issues entry retired, `EX-36` leg (ports + ans) unblocked.
- **21:00:** `TH-13` step 2 — identity `‖∇χ − c∇φ‖/‖∇χ‖` reads
  **3e-12 … 3e-11** vs 1e-6 at both degrees and frequencies, probe
  load-bearing (1.0e-1 when `c` is mistuned 10%); the gradient part of `E`
  carries 99.98% / 99.9997% of `W_e`; the residue's cross-order growth
  8.05× squares to the recorded 63.7× lift. 32 s after a 300 s
  teardown-deadlock window (journaled: collective PETSc destruction under
  rank-dependent GC). **Chunk ✅**; known-issues entry carries the
  disposition and stays open pending the fix.
- **22:30:** `WF-6` step 2 — quadrature drive by exact superposition of the
  four single-drive fields: C4-invariance **0.9818%**, mirror identity
  **0.8087%** vs the unmoved 5%, mis-paired control 95.20%, P1 linear
  purity 1.0006. Centre purity 127.91 / 0.0081, CV 2.7563% ungated.
  `post.b1_minus` landed; `ports:4`/`ports:5` re-run green. 96 s after a
  99 s phase-sign-slip window (corrected by derivation, band untouched).
  **Steps 1–2 ✅, chunk 🟡.**
- **00:00:** `ANS-5` steps 1–2 — the element-order ruling written once in
  the benchmarks README and into all three SPECs (+71/−3, `*.md` only, no
  compute). Finding: the `ANS-1`/`ANS-3` `COMPARISON.md` half is generated
  by the scripts, so it is a `.py` edit the item forbade. **🟡.**
- **03:00 review:** audited both closures compliant; priced `TH-13` step 3a
  and found the coil out of its reach; scoped `WF-6` step 2b (64/128 MHz)
  and `ANS-5` step 1b; commissioned `EX-39` (`ports:7`, the quadrature
  maps); refilled §9 with six independent items.

## Automation health

- **4 of 4 scheduled slots did chunk work, all four landed** (≈ 13 min of
  recorded compute across 12 harness logs, two of them the paid windows —
  a 300 s teardown deadlock and a 99 s sign slip, both diagnosed and fixed
  in-slot without touching a band); zero stops, zero wedges, zero parked
  branches. Container Up 5 days.
- Second consecutive interval in which every item was consumed in order
  with no inter-item dependency — the "independent items" queue design is
  holding.
- Docker-socket denial on the host runner: **0 of 4** slots this interval
  (2 of 3 the interval before) — intermittent; the substitution remains
  documented.
- Queue holds **six independent items** (five ready + spare), with the
  `EX-36` legs (mesh) / (root) / (ports + ans) as the pre-authorised drain
  fallback — all three now unblocked.

## On deck (§9 — six independent items this review)

1. **`TH-13` step 3a** — the degree-/boundary-matched source projection,
   opt-in with bit-identical defaults, gated on the loop fixture by the
   mechanism's own prediction (gradient share of `W_e` → ≤ 1e-6; `W_e` to
   ≤ 2% / ≤ 1% of record); the coil is explicitly out of scope (standard,
   ≤ 90 s)
2. **`ANS-5` step 1b** — the two `COMPARISON.md` generators emit the two
   AED columns and the basis-order row; README cases list fixed; `ans:1` +
   `ans:3` re-run (standard, ≈ 200 s) — closes `ANS-5`
3. **`EX-36` leg (th)** — re-run the eight `time_harmonic` examples so the
   census stops reading `dead` for that group (≈ 105 s)
4. **`WF-6` step 2b** — the single-drive and quadrature B₁⁺ identities at
   64 and 128 MHz on the `PORT-11` mesh, against the imported 5% band whose
   floor was measured at 10 MHz only; first Larmor B₁⁺ numbers, ungated
   (standard, ≈ 250 s)
5. **`EX-38`** — `ports:6`, the first `|B₁⁺|` field in ParaView on the
   loaded birdcage at 10 MHz (standard, ≈ 70 s)
6. *(spare)* **`EX-39`** — `ports:7`, the quadrature drive in ParaView:
   `|B₁⁺|` and `|B₁⁻|` side by side, both identities asserted (standard,
   ≈ 100 s)

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
