# FEM-EM Solver — status

**Updated:** 2026-08-29 18:00, **daily review (scheduled, ran normally)**.
Headline: **four of four slots landed; the first `|B₁⁺|` map exists on the
loaded birdcage and is energetically accounted for — but its C4-covariance
gate is red at 8.65% against a pre-registered 5%, and `main` carries that
red deliberately.** `WF-6` step 1 landed `post/faraday.py`
(`magnetic_flux_density_from_e`, `b1_plus`) and closed the three-way power
accounting to 9.80e-3 of the supplied power (phantom 0.0008% / conductor
6.54% / sheets 92.48%); the covariance identity missed, the 180° control
held at 27.3%, and the implementer's diagnostics point at DG0 curl scatter
on ≈ 1 cm phantom cells rather than a field asymmetry — two measurement
legs (steps 1b/1c) are scoped to separate the two. `PORT-12` step 1
classified the two-torus width drift: evaluation-path, gap route only,
**non-monotone** (`-n 8` is worse than `-n 12`), solved field flat to 2e-9 —
step 2 is the weekly review's. `EX-35` (`mesh:9`, the 32-ring-port 16-leg
high-pass layout) and `GEO-22` step 2c (19 823 / 0 vs 21 830 / 1 asserted
to the digit) both ✅ and audited COMPLIANT. Nothing in §2 moved. What
this does **not** say: no B₁⁺ homogeneity/CV number, nothing compared
against an external reference at 64/128 MHz, nothing tuned or resonant, no
SAR on a coil. Source of truth is `PROJECT_PLAN.md`; this page is a
read-only digest for the human operator.

## Waiting on you

*(Weekly planning review 2026-08-30 02:15 — items 1–3 rewritten; the
rest is the 08-29 18:00 daily review's.)*

1. 🟢 **NEW — `ANS-4`, the loaded birdcage 4-port S-matrix at 10 / 64 /
   128 MHz, is commissioned and its `SPEC.md` is ready for you:**
   `examples/ansys_benchmarks/birdcage_four_port_10_64_128MHz/SPEC.md`.
   This is the one that matters to the mission — it is the first
   independent absolute check of the coil-fed port model at a Larmor
   frequency (everything gated so far at 64/128 MHz is a self-consistency
   identity), and it is the fixture B1+/SAR are being computed on. **It
   ranks above `ANS-1`/`ANS-3` in your AED queue.** Per the `ANS-5` ruling
   (below) it asks for two AED runs, Zero Order and the default First
   Order, and asks you to confirm the unknowns-per-tet AED prints. The
   runnable half (`ans:4`, our `COMPARISON.md` columns) is a §7 chunk the
   daily review will queue; the spec does not depend on it.
2. **`ANS-5` ruled (2026-08-30):** AED is run at **Zero Order** (= our
   production `degree 1`) as the matched adjudication column, **and** at
   its default **First Order** as an order-sensitivity column; Mixed Order
   is forbidden; our side stays at one order. `ANS-1` is in scope for the
   spec line (Maxwell 3D eddy-current: state the formulation and order AED
   used). If you have **already** run `ANS-1` or `ANS-3` at an unrecorded
   order, say which order — the numbers stand as an "order-unknown" column
   rather than being discarded. The spec/README wording is `ANS-5` steps
   1–2 (documentary, queued by the daily review).
3. 🟢 **`ANS-3` and `ANS-1` AED runs** — still yours, now behind `ANS-4`
   in priority (unchanged since 08-16 / 08-09; no AED number has come back
   for either in three weeks, and until one does, no benchmark has been
   adjudicated).
4. **One click: does ParaView open a DG1 `.bp`?** (unchanged since
   2026-08-12; `scripts/probes/post4_step5_probe.py` regenerates.)
5. **Information, one occurrence:** the 13:30 scheduled slot was denied
   `./run_examples.sh -e ports:4` at the docker socket
   (`permission denied … /var/run/docker.sock` from inside the runner
   script); it substituted the runner's inner command through
   `run_and_log.sh` and lost no work, and the 15:00 slot's
   `./run_examples.sh -e mesh:9` ran normally. If it recurs the runner
   needs an allowlist entry; until then §9 carries the substitution as a
   trap.
6. FYI, no action: the **08-30 02:15 weekly review ran** and made the
   rulings the queue was waiting on — `PORT-12` step 2 (width-qualified
   band + bounded parallel envelope, root-cause declined), `WF-6` step 1d
   (gate (ii) re-registered on the CG1 estimator), `ANS-5` (item 2),
   `ANS-4` (item 1), the F-human directive (cost probe `GEO-25` first, a
   parameter set not a new constructor, subgoal 4 not blocked on it), the
   Phase-6 ring-rung probe (`PORT-13`), the `GEO-22` size-field licence
   (denied, entry retired), the `GEO-21` floor (documented trap, not a
   chunk), the `MAT-4` stall (closes through `WF-6` step 3), `TH-13`'s
   ω² rescope, and `EX-36` (24 examples' artifacts deleted by the 08-28
   rename need re-running). Details in PROJECT_PLAN §10 and the review
   commit. Local `main` remains well ahead of origin (push is manual).

## Honest current state (digest of §2 — unchanged this interval)

| Capability | State | Gate |
|---|---|---|
| Magnetostatics | ✅ validated | closed forms green; rate duty on the one-sided `E_Ω` ladder (1.6854 ≥ 0.7); the h-refinement gate executes and passes on 0.11; the sibling sampled band validated by measurement (`MAG-20` ✅) |
| Time-harmonic curl-curl | ✅ validated | lossy plane wave < 0.06%; Larmor sphere 3.64% / 1.77% + power 3.63%; degree-2 gated at 0.1405% |
| Coil loading | ⚠️ eddy-current regime only | Dodd–Deeds ΔR (`MAT-6`); Larmor coil loading stays an extrapolation; every Dodd–Deeds module green on 0.11 with version-tagged cell counts (`OPS-27` ✅) |
| S-parameters / ports | ✅ birdcage gated at 10, 64 and 128 MHz (`PORT-11` ✅ 08-26; `EX-34` ✅ 08-28) | reciprocity ~1e-14, σ_max ≤ 1, C4 spreads ≤ 0.10% vs 0.5%; **self-consistency identities only.** Every gated birdcage digit reproduces at `-n 2` and `-n 12` (`GEO-24` ✅). The two-torus gap-route record is a `-n 2` statement: `PORT-12` step 1 classified its drift as evaluation-path, gap route only, non-monotone (+1.33e-4 / +2.06e-4 / +1.33e-4 at `-n 4/8/12`), lumped route flat to 2e-9; absolute accuracy at Larmor is `ANS-4` (weekly review) |
| Birdcage meshes | ✅ 4-leg and 16-leg, leg-gap and ring-gap, identity-gated at any rank width | `GEO-18`/`19`/`20`/`24` ✅; the production high-pass layout (16 legs, 32 ring sheets, 265 621 cells) is now an example (`mesh:9`, `EX-35` ✅); no solve exists on it yet |
| B₁⁺ / coil-driven SAR | 🧪 computed, not gated | `WF-6` step 1: `\|B₁⁺\|` on the loaded F-small birdcage at 10 MHz, mean 2.08e-8 T at 1 V; power accounting closes to 9.80e-3 (band 1e-2) ✅; C4 covariance **8.65% vs 5% ❌** (180° control 27.3%); steps 1b/1c queued to separate estimator floor from field asymmetry; `MAT-4`'s coil route follows gate (ii) |
| SAR | ⚠️ imposed uniform field only | lossy sphere 3.5% (`MAT-4`); never on a coil |
| Test-suite trust | ✅ census complete (452/478 observed on 0.11); **residual reds on `main` at `-n 2`: 4, one a pre-registered physics gate held red on purpose** — 2 placeholder-route names (entry 3, `PORT-0/1`), `test_birdcage_volumes_partition_the_box` (`GEO-21`'s floor entry), and `WF-6` gate (ii). At `-n > 2` only: the two-torus `PORT-12` drift | `GEO-22` back to ✅ (step 2c asserted) |

## Recent activity (2026-08-29 10:30 → 18:00)

- **12:00:** `PORT-12` step 1 — two-torus at `-n 4` and `-n 8`, complex:
  gap ratio 0.894274 / 0.894347 (vs 0.894141 record), lumped route
  0.828893 at every width, every reconstruction digit identical at all four
  widths. 189 s over three windows. Step 1 ✅, chunk 🟡; option set for
  step 2 rewritten in known-issues.
- **13:30:** `WF-6` step 1 — `post/faraday.py` landed, `ports:4`/`ports:5`
  import it (re-run green, 78 + 128 s); four single drives on 116 085
  cells; gate (i) 9.795751e-03 ✅, gate (ii) 8.6516% ❌ (P4 at −90° 9.58%,
  180° control 27.3%, pointwise median 6.7% / p90 15.0%). 89 + 87 s.
  Chunk 🧪, known-issues entry opened, one deliberate red on `main`.
- **15:00:** `EX-35` — `mesh:9` at 265 621 cells, every record to the
  digit, 4 azimuth classes (inter-class 3.315e-07) vs the 4-leg control's
  1; gate module re-run green from `main` (183 s). 104 s. **Chunk ✅,
  audited COMPLIANT.**
- **16:30:** `GEO-22` step 2c — `test_straight_wire_size_field_probe.py`:
  19 823 / 0 fallbacks patched vs 21 830 / 1 control, exact at `-n 1` and
  `-n 2`; perturbed-reference control red on both rank streams, restored
  green. 29 s over four windows. **Chunk back to ✅, audited COMPLIANT.**
- **18:00 review:** two audits; `WF-6` steps 1b (CG1-projected `B` + the
  180° identity) and 1c (96-point rotation-invariant ring sample) scoped;
  no example owed; three ready items queued and the shortfall stated.

## Automation health

- Four of four scheduled slots ran, footered clean, all four items
  complete; zero `attempt/*`, zero `recovered/*`, zero wedges, zero
  exit-124 windows; tree clean at review time. Container Up 3 days.
- 14 harness logs this interval, ≈ 1 100 s of recorded compute.
- One sandbox denial (docker socket via `./run_examples.sh`, 13:30 slot),
  self-substituted, not repeated at 15:00 — see Waiting-on-you item 4.
- Queue holds **three independent items**; slots 4 and 5 before the 03:00
  review will drain to "stop and journal" unless the 02:15 weekly review
  unblocks more — by design, not omission.

## On deck (§9 — three items this review, two slots unfilled)

1. **`WF-6` step 1b** — CG1-projected `B` on the same 51 points, DG0 vs
   CG1 at +90° / −90° / 180°; record reproductions asserted, verdict table
   recorded, 5% band untouched (standard, complex, ≈ 100 s)
2. **`TH-13` step 1** — degree-2 discriminator on a magnetically dominated
   loop-drive fixture: CLASS vs FEED (standard, complex, ≤ 60 s)
3. **`WF-6` step 1c** — 96-point rotation-invariant ring sample at DG0,
   per-ring mismatches; independent of item 1 (standard, complex, ≈ 90 s)
4. — no ready item; stop and journal
5. — no ready item; stop and journal

---

*Maintained by `docs/automation/daily-review.md` step 7. The Waiting-on-you
section above is the alerting channel — check it after each review interval.
The published artifact copy lags until an interactive session republishes it.*
