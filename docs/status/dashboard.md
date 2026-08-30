# FEM-EM Solver — status

**Updated:** 2026-08-30 18:00, **daily review (scheduled, ran normally)**.
Headline: **a clean interval — four slots, four landings, two chunks
closed (`PORT-12`, `ANS-4`), `WF-6` step 1 gated on the CG1 estimator,
and `TH-13` step 1′ a clean negative that retired the frequency route.**
The review found two things by reading: `ANS-1`/`ANS-3` have been
unrunnable since the 08-28 rename (a one-line import fix, queued first),
and the `TH-13` degree-2 "explosion" has a concrete candidate mechanism
in the code — the drive projection removes gradient content against CG1
and H¹₀ only, whatever the solve degree or boundary — pre-registered as
step 2 so a 90 s run can confirm or refute it. Nothing in §2 moved beyond
wording. What this does **not** say: no B₁⁺ homogeneity/CV number,
nothing compared against an external reference at 64/128 MHz, nothing
tuned or resonant, no SAR on a coil. Source of truth is `PROJECT_PLAN.md`;
this page is a read-only digest for the human operator.

## Waiting on you

1. 🟢 **`ANS-4` is ready to replicate — both halves now exist.** Our
   runnable half landed 16:30:
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/` (script,
   `metrics.json`, `COMPARISON.md` with our column filled and two blank AED
   columns, a 128 MHz XDMF). Per the `ANS-5` ruling: AED at **Zero Order**
   (adjudication column) and at its default **First Order** (sensitivity
   column), Mixed Order not; please confirm the unknowns-per-tet figure
   AED prints. Ranks above `ANS-1`/`ANS-3`. Adjudication is the 09-06
   weekly review's.
2. **Information — automation fix from the 10:30 review, still awaiting
   your OK:** `docs/automation/weekly-review.md` now has a commit-first
   checkpoint (rotation committed before plan edits). Revert the paragraph
   if you want the single-commit form back.
3. **`ANS-5` ruled** (unchanged): if you have **already** run `ANS-1` or
   `ANS-3` at an unrecorded order, say which — the numbers stand as an
   "order-unknown" column. Spec wording is §9 item 4 (documentary).
4. 🟢 **`ANS-3` and `ANS-1` AED runs** — still yours, behind `ANS-4`. FYI:
   our two scripts for these cases have been unrunnable since 08-28 (the
   rename rewrote an import string; `EX-37`, §9 item 1, restores them) —
   the specs and the recorded numbers you replicate against are unaffected.
5. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
6. FYI, no action — the 09-06 weekly review owes the `GEO-25` and
   `PORT-13` rulings and the §10 pass (your 08-25 `N ≤ 25` directive's
   disposition). The host runner's docker-socket denial has now fired in
   2 of the 3 example-running slots (08-29 13:30, 08-30 12:00; clean at
   16:30) — intermittent, the fallback works, no slot lost; if you know
   why the socket permission flaps, that would retire the workaround.
   Local `main` remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — wording only this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11; the sibling sampled band validated by measurement (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% on the sphere. The degree-2 electric-energy "explosion" on driven fixtures now has a pre-registered candidate mechanism (`TH-13` step 2, §9 item 2) |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; every Dodd–Deeds module green on 0.11 with version-tagged cell counts (`OPS-27` ✅) |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; `EX-34` ✅ 08-28; `ANS-4` runnable half ✅ 08-30) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only.** Every gated birdcage digit reproduces at `-n 2` and `-n 12` (`GEO-24` ✅). The two-torus gap-route record is a `-n 2` statement with its parallel drift **bounded** (`PORT-12` ✅ 08-30: envelope 3e-4 at `-n > 2`, worst +2.06e-4 at `-n 8`, lumped route flat to 2e-9); absolute accuracy at Larmor is `ANS-4` — AED replication pending |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | `GEO-18`/`19`/`20`/`24` ✅; the production high-pass layout (16 legs, 32 ring sheets, 265 621 cells) is an example (`mesh:9`, `EX-35` ✅); no solve exists on it yet (`PORT-13`, ruling owed) |
| B₁⁺ / coil-driven SAR | 🧪 computed; symmetry-gated at CG1, not homogeneity-gated | `WF-6` step 1 ✅ 08-30: `\|B₁⁺\|` on the loaded F-small birdcage at 10 MHz, mean 2.08e-8 T at 1 V; power accounting 9.80e-3 (band 1e-2) ✅; C4 covariance on the CG1-projected estimator **2.19 / 2.11 / 1.89% vs 5% ✅** (DG0's 8.65% recorded as the estimator floor). Step 2 — quadrature drive by superposition, mirror identity, first *ungated* CV figures — is §9 item 3; `MAT-4`'s coil route follows it |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ census complete (452/478 observed on 0.11); **residual reds on `main` at `-n 2`: 4, one of them a pre-registered physics gate held red on purpose** — 2 placeholder-route names (entry 3, `PORT-0/1`), `test_birdcage_volumes_partition_the_box` (`GEO-21`'s floor entry), `TH-13`'s precondition (deliberate, now on the 1 MHz row). No `-n > 2`-only red remains | example-artifact census `dead=53 exit=1` since the 08-28 rename (`EX-36`, §9 item 5 + drain fallback); `ans:1`/`ans:3` unrunnable since the same rename (`EX-37`, item 1) |

## Recent activity (2026-08-30 10:30 → 18:00)

- **12:00:** `WF-6` step 1d — `post.project_to_cg1` packaged; gate (ii) is
  the CG1 covariance identity at all three angles, **2.1870 / 2.1146 /
  1.8911%** vs the unmoved 5%, DG0 column asserted unmoved at 8.6516%,
  control 23.26%. 19 passed, 97 s; `ports:4`/`ports:5` re-run green.
  Known-issues entry retired; chunk 🧪 → 🟡 with step 1 ✅.
- **13:30:** `PORT-12` step 2 — `-n 8` on unpatched `main` red first
  (Status 1, drift 2.06e-4 vs 1e-4), then `PARALLEL_DRIFT_ENVELOPE = 3e-4`
  green at `-n 8` and `-n 2` (record 0.894141 exact), lumped route flat at
  2.3e-10, the 1e-8 assert probed load-bearing (7.3e-2 miss when
  mispointed, reverted). 310 s. **Chunk ✅**, known-issues entry retired.
- **15:00:** `TH-13` step 1′ — the 1 MHz row reads `W_e/W_m` =
  1.926692e-02, **98.7× the ω² prediction and 0.987× the 10 MHz row**;
  energies and dissipated power frequency-flat. Precondition red moved to
  the 1 MHz row (not loosened); degree-2 ratio saturates at 1.01 at both
  frequencies. 32 s. Negative, informative: the cross-order ratio is the
  wrong observable at any frequency.
- **16:30:** `ANS-4` runnable half — `ans:4` green first run, 125 s: all
  three gates on all three rungs, 10 MHz records to 1.158e-10 / 2.568e-10,
  64/128 MHz to 1.075e-3 / 6.755e-4 (band 1e-2), heuristic control
  separation 1.585460. `COMPARISON.md` with two blank AED columns. **Chunk
  ✅.** Slot also spotted the `ANS-1`/`ANS-3` import breakage.
- **18:00 review:** audited both closures compliant; found the `TH-13`
  mechanism candidate by reading `core/source_projection.py` and rescoped
  step 2 onto it; scoped `WF-6` step 2; commissioned `EX-37` (import fix)
  and `EX-38` (`ports:6`, the first B₁⁺ field in ParaView); refilled §9
  with six independent items.

## Automation health

- **4 of 4 scheduled slots did chunk work, all four landed** (≈ 15 min of
  recorded compute across 15 harness logs); zero stops, zero wedges, zero
  exit-124 windows, zero parked branches. Container Up 4+ days.
- The queue's "six independent items" design paid off: no slot waited on
  another's result, and the one negative (`TH-13` 1′) cost 32 s.
- Docker-socket denial on the host runner: 2 occurrences in 3 slots; the
  documented substitution absorbed both at ~1 min each (Waiting-on-you 6).
- Queue holds **six independent items** (five ready + spare) with the
  `EX-36` legs as the pre-authorised drain fallback — leg (ports + ans)
  only after item 1 lands.

## On deck (§9 — six independent items this review)

1. **`EX-37`** — restore the two `__import__` strings the rename broke,
   negative control on unpatched `main`, re-run `ans:1` + `ans:3`, census
   (standard, ≈ 4 min)
2. **`TH-13` step 2** — the gradient-projection identity: does the
   `∇Lagrange_p`-projection of `E_h` equal the form's constant times that
   of the projected drive, at degrees 1 and 2? (A) ≤ 1e-6 asserted, (B)
   the residue's share of `W_e` printed, unprojected-drive control
   (standard, ≤ 90 s, tests only)
3. **`WF-6` step 2** — quadrature drive by exact superposition at 10 MHz:
   C4-invariance and the co/counter-rotating mirror identity at the CG1
   floor, first ungated CV and polarisation-purity figures; `b1_minus`
   lands (standard, ≤ 120 s + two example re-runs)
4. **`ANS-5` steps 1–2** — the element-order ruling written into every
   spec, README and comparison table (documentary, no compute)
5. **`EX-36` leg (th)** — re-run the eight `time_harmonic` examples so the
   census stops reading `dead` for that group (≈ 105 s)
6. *(spare)* **`EX-38`** — `ports:6`, the first `|B₁⁺|` field in ParaView
   on the loaded birdcage at 10 MHz, gate (i)/(ii) records asserted
   (standard, ≈ 70 s); legs (mesh) / (root) / (ports + ans) of `EX-36` are
   the drain fallback

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
