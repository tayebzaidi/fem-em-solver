# XL / XXL pending windows — pre-registered by the weekly, queued by the daily

**Why this file exists (operator directive 2026-09-13).** XL and XXL windows
are cron scripts with no Claude session — the only compute in the project
that costs no tokens — but only the weekly review may commission one, the
queue files hold one item each, and under the wind-down schedule the weekly
runs once a week. Left as it was, at most one of the three budgeted XL
windows and, some weeks, no XXL window would run. This file splits the role:
the **weekly decides** (it pre-registers entries here — tier, chunk and step,
the exact command, the measured price, the readout and the decision rule)
and the **daily review is the clerk** (daily-review.md step 6b: it copies
*every* READY entry of a tier into its own file in
`docs/testing/<tier>-queue.d/` verbatim, up to the tier's budget — a FIFO
the launcher drains one window per night, 2026-09-15). An interactive
operator session may do either.

**Backlog floor and daily licence (operator directive 2026-09-15).** The
daily review keeps **≥ 4 `xl` and ≥ 1 `xxl` entries ahead** (READY or
QUEUED for a future night), reports the count on the dashboard, and when
short may write entries itself in two classes only — **priced-family
variants** of an already-measured case (same script and mesh; frequency,
degree, drive/port set, rank count or one env knob varied) and **cost
probes** (first window on an unpriced case, readout = the price). Each such
entry names its licence class. Everything else is the weekly's.

**Budget, as the clerk reads it.** `xl`: fewer than six rows with a
non-zero `Elapsed` in the trailing 7 days of `docs/testing/xl-ledger.md`
(nightly Sun–Fri, operator directive 2026-09-13)
(killed and 0-second rows are uncharged, §5.1). `xxl`: no such row in the
trailing 7 days of `docs/testing/xxl-ledger.md`. The next run date is the
next 02:00 for the tier (xl Sun–Fri, xxl Saturday) after the budget opens.

**Status words.** `READY` — prerequisite landed, command final. `PENDING
PREREQUISITE` — names the item that must land first (an ordinary §9 item).
`QUEUED <date> for <run date>` — copied into `<tier>-queue.d/`. `RUN <log>` —
the launcher consumed the queue file; the review that finds the ledger row marks
it and the weekly interprets it. Entries are never edited after `QUEUED`
except to add the run status; a changed command is a new entry.

## Entries

### 1. `xxl` — `WF-7` step 0b: the F-human rung at degree 2, one drive, 64 MHz

**Status:** RUN `20260919T070008Z_WF-7-step0b.log` — both legs rc 0,
Status 0, 673 s, `memory.peak` 106.1 GiB; degree 2 is 3 256 418 unknowns,
347.56 s, 107.9 GiB summed; `|S₂ − S₁| / |S₁|` = 5.50 % from the two printed
`S_driven` values (ledger row 2026-09-19; marked by the 2026-09-19 03:00
review; the weekly of 2026-09-19 reads it against the decision rule below —
branch (c) is excluded, and the F-small 64 MHz moves it is compared with are
6.51 / 2.60 / 4.11 %, entry 4's "Why"). *(Was QUEUED 2026-09-13 (operator,
interactive) for Saturday 2026-09-19 02:00 — moved to
`docs/testing/xxl-queue.d/20260919-WF-7-step0b.env` 2026-09-15 when the queue
became a directory; consumed by the launcher.)*

**Prerequisite:** `scripts/probes/wf7_step0_f_human_cost.py` gained the
`FEM_EM_WF7_DEGREE` knob (this commit; unset or `1` is byte-identical to
step 0). Landed.

**What runs:** the step-0 probe twice in one window against
`fem-em-solver-xxl` at `-n 16`: degree 1 first (the control — step 0's
solve at `-n 8` read 607 039 unknowns, 37 s, 10.93 GiB summed; the same
mesh at `-n 16` re-reads `S_driven`), then degree 2. Durable capture, both
`rc`s recorded, `memory.peak` printed, `[capture] rc=` last.

**Price, predicted (not measured at this order and scale — that is the
point):** degree 2 on the 507 266-cell rung is ≈ 3.2 M unknowns. From
`ANS-4` step 2d's measured point (3.79 M unknowns, 290.2 GiB peak,
≈ 1 400 s per drive before factor reuse, `-n 16`) scaled at memory ∝ N^1.35
and time ∝ N^1.8: **≈ 235 GiB, ≈ 17 min**; the probe prints its own
brackets 150–350 GiB and 10–60 min and says INSIDE / OUTSIDE. Timeouts
1 500 s + 27 000 s inside the 28 800 s window; 754 GiB limit.

**Readout (record, 🧪 — nothing asserted beyond the imported cell band):**
`S_driven` at degree 1 and degree 2 on the same F-human mesh, and
`|S₂ − S₁| / |S₁|` — **the human-scale order sensitivity, which nobody has
measured**; plus the degree-2 price (unknowns, solve time, `ru_maxrss` per
rank, summed, `memory.peak`), banked in `xxl-ledger.md`.

**Decision rule, pre-registered for the 2026-09-19 weekly:** compare the
F-human degree-1 → 2 move with F-small's own move at 64 MHz (`ANS-4` step
2b, our figures). (a) F-human's move is in the same class or larger ⇒ a
human-scale S quoted at degree 1 carries that error, degree 2 is the
production order at human scale, and this window is its price. (b) Much
smaller (an order of magnitude) ⇒ degree 1 suffices at human scale for S,
and the human-scale sweep stays an ordinary heavy-tier job. (c) The
degree-2 run does not finish or exceeds the box ⇒ the price is the finding;
`TH-16` (symmetry planes) moves up. Either way no band moves and no
absolute claim is made.

### 2. `xl` — `ANS-4` step 3: the 64 MHz order-matched rung (weekly 2026-09-13, §10)

**Status:** RUN `20260916T070008Z_ANS-4-step3.log` — 16 passed, Status 0,
1658 s, `memory.peak` 280.8 GiB (ledger row 2026-09-16; marked by the
2026-09-16 03:00 review; the weekly of 2026-09-19 interprets it against the
decision rule below). *(Was QUEUED 2026-09-15 (operator, interactive) for
Wednesday 2026-09-16 02:00 — `docs/testing/xl-queue.d/20260916-ANS-4-step3.env`,
consumed by the launcher. Before that PENDING PREREQUISITE — `ANS-4` step 3a. 3a landed on `main`
2026-09-14, 04:30 slot. The knob reaches the solve, and the flag-off control
reproduced 2a″ at its `-n 8` record width, not `-n 2` (`OPS-41`). Marking
this entry READY is the next daily review's job.)*

**Prerequisite (an ordinary §9 item, standard tier, tests only):**
`tests/validation/test_ans4_resolution_ladder.py` is hard-wired to
`FREQUENCY_128_HZ` (two sites). Step 3a adds an env knob
`FEM_EM_ANS4_FREQUENCY_HZ` (default 128e6; unset is bit-identical) and
proves it with the flag-off control — the `0.015:1` rung reproduces step
2a″'s recorded digits — through the harness at `-n 2`. No band, no record.

**Budget:** open — three charged rows in the trailing 7 days (09-09 ×2,
09-10) against six. The gate is 3a: the first daily review after 3a lands
on `main` queues this for the next 02:00 (3a queued Monday 09-14 and
landed that morning ⇒ the Wednesday 09-16 03:00 review queues it for
**Thursday 2026-09-17 02:00**; Tuesday has no review).

**Command (final once 3a lands; the knob name above is the contract):**

```
XL_CHUNK="ANS-4-step3"
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_ANS4_FREQUENCY_HZ=64e6 FEM_EM_ANS4_STEP2_RUNGSPEC=\"0.015:1 0.005:2\" timeout -k 60 14400 mpiexec -n 16 python3 -m pytest tests/environment tests/validation/test_ans4_resolution_ladder.py -v -s --tb=short > /workspace/logs/ans4-step3-raw.log 2>&1; rc=\$?; echo \"[XL] memory.peak bytes:\" >> /workspace/logs/ans4-step3-raw.log; cat /sys/fs/cgroup/memory.peak >> /workspace/logs/ans4-step3-raw.log; echo \"[capture] rc=\$rc\" >> /workspace/logs/ans4-step3-raw.log; cat /workspace/logs/ans4-step3-raw.log; exit \$rc'"
```

**Price, measured:** step 2d ran this mesh and order at 128 MHz — 592 744
cells, 3.79 M unknowns, 290.2 GiB peak, 5 653 s for four drives before
factor reuse. With one factorisation and three back-substitutions
(`PORT-19`) the window is *predicted* 2 000–3 000 s; memory the same.

**Readout and decision rule:** as pre-registered by the 2026-09-13 weekly
(§10): public — the three C4 classes at 64 MHz at degree 2 against the
degree-1 record, every imported `PORT-11` gate on the rung; private
(`docs/private/`) — the miss against the AED First Order column. A miss in
the same class as the 128 MHz order-matched residual ⇒ the 64 MHz AGREE
stands on evidence and its "by mechanism" qualifier is dropped; a
materially larger miss ⇒ a frequency-dependent feed-model systematic
re-opens as a known-issues entry and a `PORT` systematics chunk.

### 3. `xl` — `ANS-4` step 3b: the 128 MHz degree-2 rung on the C4-congruent cut (daily licence: priced-family variant, 2026-09-16 review)

**Status:** RUN `20260917T070008Z_ANS-4-step3b.log` — 15 passed / 1
skipped (the `-n 16` record-width skip this entry predicted), Status 0,
1539 s, `memory.peak` 273.1 GiB, 592 550 cells at h = 0.005 under the cut
(ledger row 2026-09-17; marked by the 2026-09-18 03:00 review; the weekly
of 2026-09-19 interprets it against the decision rule below). *(Was QUEUED
2026-09-16 for Thursday 2026-09-17 02:00 —
`docs/testing/xl-queue.d/20260917-ANS-4-step3b.env`, consumed by the
launcher.)*

**Licence class:** priced-family variant of the `ANS-4-step3` (2026-09-16)
and `ANS-4-step2d` (2026-09-10) ledger rows — the same module, the same
`RUNGSPEC="0.015:1 0.005:2"`, the same generator; **one named env knob
varied**: `FEM_EM_ANS4_STEP2_C4_CONGRUENT=1` (`GEO-32`'s congruent
port-sheet cut, off in both priced rows). The frequency is the module
default (128 MHz, knob unset). The cut changes the mesh by construction
(116 118 vs 116 085 cells at the ×1 rung, +0.03 %; the h = 0.005 count
under the cut is unmeasured and is part of the readout).

**Why (the §10 question it answers):** the 128 MHz AGREE was banked on
step 2d's degree-2 rung with the cut *off*, while the degree-1 record it is
compared against (2a″) has the cut *on*, and `GEO-32` showed the cut
carries the whole degree-1 read-back spread. This window gives the
order-matched 4×4 on the same cut as the degree-1 record — apples to
apples — and shows whether the degree-2 class spreads (0.1985 / 0.1715 /
0.1946 % at 64 MHz, 3× the degree-1 rung's) are the cut too.

**Command:**

```
XL_CHUNK="ANS-4-step3b"
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_ANS4_STEP2_C4_CONGRUENT=1 FEM_EM_ANS4_STEP2_RUNGSPEC=\"0.015:1 0.005:2\" timeout -k 60 14400 mpiexec -n 16 python3 -m pytest tests/environment tests/validation/test_ans4_resolution_ladder.py -v -s --tb=short > /workspace/logs/ans4-step3b-raw.log 2>&1; rc=\$?; echo \"[XL] memory.peak bytes:\" >> /workspace/logs/ans4-step3b-raw.log; cat /sys/fs/cgroup/memory.peak >> /workspace/logs/ans4-step3b-raw.log; echo \"[capture] rc=\$rc\" >> /workspace/logs/ans4-step3b-raw.log; cat /workspace/logs/ans4-step3b-raw.log; exit \$rc'"
```

**Price, inherited from the family (scaling stated):** `ANS-4-step3` ran
this `RUNGSPEC` at `-n 16` in **1658 s** with `memory.peak` **280.8 GiB**
(592 744 cells, 3.79 M unknowns, four drives 1476.9 s); step 2d's same
rung read 290.2 GiB. A direct solver's cost is set by the mesh and order,
not the frequency, and the cut moves the cell count by ~0.03 %, so the
prediction is **1 500–2 500 s, 270–300 GiB**; if the congruent cut at
h = 0.005 meshes materially differently, the cell count printed at
`[ANS-4 step2d] rung h=0.005 degree 2 (c4_congruent_sheets=on)` is the
first reading. Timeout 14 400 s inside the 4 h window; 512 GiB limit.

**Readout (record, nothing asserted beyond the module's imported gates):**
public — the degree-2 4×4 at 128 MHz on the congruent cut, its class
spreads beside step 2d's (cut off), and the degree 1 → 2 move on the same
cut (the ×1 rung in this window against the 2a″ record, which the module
prints); private (`docs/private/`) — the miss against the AED First Order
column beside step 2d's. **Decision rule for the 09-19 weekly:** classes
within their own step-2d spread of step 2d's ⇒ the cut is not a degree-2
systematic and the 128 MHz AGREE stands as written; a class move larger
than the spread ⇒ the cut is a named systematic of the order-matched rung
and `GEO-32`'s 🧪 row gains the degree-2 reading. No band moves. The
module's 128 MHz record assert (`test_the_frequency_knob_reaches_the_solve`)
is skipped at `-n 16` by design (`OPS-41`) — the ×1 digits are printed.

### 4. `xl` — `ANS-4` step 3c: the 10 MHz degree-2 rung (daily licence: priced-family variant, 2026-09-16 review)

**Status:** RUN `20260918T070008Z_ANS-4-step3c.log` — 16 passed, Status 0,
1603 s, `memory.peak` 284.8 GiB (ledger row 2026-09-18; marked by the
2026-09-18 03:00 review; the weekly interprets it against the decision
rule below — and reads the self-class spread, 0.4451 % against the 0.5 %
band, with entry 8). *(Was QUEUED 2026-09-16 for Friday 2026-09-18 02:00 —
`docs/testing/xl-queue.d/20260918-ANS-4-step3c.env`, consumed by the
launcher.)*

**Licence class:** priced-family variant of `ANS-4-step3` — same module,
same `RUNGSPEC`, same mesh (cut off, the `GEO-19` record mesh), **frequency
varied only**: `FEM_EM_ANS4_FREQUENCY_HZ=10e6`.

**Why:** the `ANS-4` diagnosis began as a *frequency trend* — AED agreed
with our degree-1 classes at 10 MHz and disagreed at the Larmor rungs. The
degree 1 → 2 move is now measured at 128 MHz (6.09 / 5.38 / 6.70 %) and
64 MHz (6.51 / 2.60 / 4.11 %). The 10 MHz point says whether the order
sensitivity itself is frequency-dependent the way the miss was: a small
move at 10 MHz means the 10 MHz AGREE was non-accidental at degree 1 and
the Larmor misses were order; a move of the same size means order matters
everywhere and the 10 MHz agreement was at a degree-1 point that happened
to sit inside AED's band.

**Command:**

```
XL_CHUNK="ANS-4-step3c"
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_ANS4_FREQUENCY_HZ=10e6 FEM_EM_ANS4_STEP2_RUNGSPEC=\"0.015:1 0.005:2\" timeout -k 60 14400 mpiexec -n 16 python3 -m pytest tests/environment tests/validation/test_ans4_resolution_ladder.py -v -s --tb=short > /workspace/logs/ans4-step3c-raw.log 2>&1; rc=\$?; echo \"[XL] memory.peak bytes:\" >> /workspace/logs/ans4-step3c-raw.log; cat /sys/fs/cgroup/memory.peak >> /workspace/logs/ans4-step3c-raw.log; echo \"[capture] rc=\$rc\" >> /workspace/logs/ans4-step3c-raw.log; cat /workspace/logs/ans4-step3c-raw.log; exit \$rc'"
```

**Price, inherited:** `ANS-4-step3` — **1658 s, 280.8 GiB** at `-n 16` on
this exact mesh; frequency does not change the factorisation's size, so
the prediction is **1 500–2 000 s, 270–290 GiB**.

**Readout (record):** public — the degree-2 4×4 at 10 MHz, the imported
`PORT-9` gates on the rung, and the degree 1 → 2 move on the driven column
(the ×1 rung's 10 MHz 4×4 is `PORT-9` leg (d)'s, reproduced by `ANS-4`
run1 to 1.2e-10); private — the miss against the AED 10 MHz columns beside
the degree-1 one. **Decision rule for the weekly:** a 10 MHz move an order
of magnitude below the Larmor moves ⇒ the frequency trend is an
order-sensitivity trend, and the 10 MHz AGREE stands at either order; a
move in the same class ⇒ the degree-1 10 MHz AGREE is re-read as
coincidental and `ANS-4`'s row says so. The module's off-128 MHz knob
assert (every class moves > 1e-2 from the 128 MHz record) is the only
frequency-dependent gate and holds trivially at 10 MHz.

### 5. `xl` — `ANS-4` step 3d: the 64 MHz degree-2 rung on the C4-congruent cut (daily licence: priced-family variant, 2026-09-16 review)

**Status:** RUN `20260920T070008Z_ANS-4-step3d.log` — 16 passed, 0 skipped,
Status 0, 1619 s, `memory.peak` 281.1 GiB; class spreads on the cut
0.0132 / 0.0126 / 0.0081 %, two-rung move 6.50 / 2.61 / 4.12 % beside step
3's 6.51 / 2.60 / 4.11 % (ledger row, 2026-09-20 review). By the public rule
below the cut is not a degree-2 systematic at 64 MHz; the 09-26 weekly
rules and reads the private column. *(Was QUEUED 2026-09-16 for Sunday
2026-09-20 02:00 — `docs/testing/xl-queue.d/20260920-ANS-4-step3d.env`,
consumed by the launcher.)*

**Licence class:** priced-family variant of `ANS-4-step3` — same module,
same `RUNGSPEC`, same frequency (64 MHz); **one named env knob varied**:
`FEM_EM_ANS4_STEP2_C4_CONGRUENT=1`. The 64 MHz counterpart of entry 3, so
the weekly reads the cut's effect at both Larmor frequencies.

**Command:**

```
XL_CHUNK="ANS-4-step3d"
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_ANS4_FREQUENCY_HZ=64e6 FEM_EM_ANS4_STEP2_C4_CONGRUENT=1 FEM_EM_ANS4_STEP2_RUNGSPEC=\"0.015:1 0.005:2\" timeout -k 60 14400 mpiexec -n 16 python3 -m pytest tests/environment tests/validation/test_ans4_resolution_ladder.py -v -s --tb=short > /workspace/logs/ans4-step3d-raw.log 2>&1; rc=\$?; echo \"[XL] memory.peak bytes:\" >> /workspace/logs/ans4-step3d-raw.log; cat /sys/fs/cgroup/memory.peak >> /workspace/logs/ans4-step3d-raw.log; echo \"[capture] rc=\$rc\" >> /workspace/logs/ans4-step3d-raw.log; cat /workspace/logs/ans4-step3d-raw.log; exit \$rc'"
```

**Price, inherited:** as entry 3 — **1 500–2 500 s, 270–300 GiB** at
`-n 16` (the congruent-cut mesh at h = 0.005 will have been measured by
entry 3 the night before; if entry 3 found it materially larger, the
launcher's budget check is unaffected but the weekly should re-read this
prediction).

**Readout and decision rule:** as entry 3, at 64 MHz, beside
`ANS-4-step3`'s 4×4 (cut off): classes within step 3's own spread ⇒ the
cut is not a degree-2 systematic at 64 MHz either; a larger move ⇒ named
systematic, `GEO-32` row annotated. Private: the miss against AED's 64 MHz
First Order column beside step 3's. No band moves.

### 6. `xl` — `WF-7` step 0c: the F-human degree-1 solve at the full 32-port set (daily licence: cost probe, 2026-09-16 review)

**Status:** RUN `20260921T070008Z_WF-7-step0c.log` — `[capture] rc=0`,
Status 0, 228 s, `memory.peak` 11.96 GiB; one factorisation (24.73 s) + 31
held back-substitutions (0.40–0.57 s), cumulative 3.74 min — **below** the
5–45 min bracket, memory INSIDE; full 32×32 reciprocity 1.084e-14 asserted
green. Ledger row filled by the 2026-09-21 03:00 review. **Two corrections to
this entry's own text (log-pathologist, 2026-09-21):** the Readout's "nothing
asserted beyond the imported cell band" is wrong — the probe also asserts the
32×32 reciprocity and the drive-2 ≠ drive-1 floor (`:394–428`); and the
refinement paragraph called its own ≈ 3.5 min extrapolation "well inside"
a bracket whose floor is 5 min. Neither moves the decision rule: the set fits
one window with two orders of magnitude to spare, so chain step H3 is written
at the **heavy** tier (§9, 2026-09-21). *(Was QUEUED 2026-09-18 for Monday
2026-09-21 02:00 —
`docs/testing/xl-queue.d/20260921-WF-7-step0c.env`, the first `xl` night
after entry 5's 09-20; Saturday 09-19 is the `xxl` night; READY before that —
2026-09-16 09:38Z, §9 item 1 landed on `main` as `a267c5a`.)* The
probe's `FEM_EM_WF7_PORTS` knob is in (`scripts/probes/wf7_step0_f_human_cost.py`),
proved at heavy tier by the flag-off control (knob unset reproduces step 0's
printed `S_driven` `0.407423+0.344417j`, `20260916T093301Z_WF-7-step0c.log:10428`)
and the two-drive reciprocity assert (2×2 ratio 9.767e-16 ≤ the imported 1e-3,
drive 2 differs by 1.407e-03, `20260916T093548Z_WF-7-step0c.log:10433,10438`).
The command below is unchanged and runs as written. The next review queues it
for the following `xl` night.

**Price refinement from the two-drive window (2026-09-16, `-n 8`):** drive 1
factorises in 27.71 s, drive 2 back-substitutes the held factor in **0.59 s**
(`solve_kind` `held`), and summed `ru_maxrss` moved 10.892 → 11.082 GiB over
the second column. Extrapolated to 32 drives at `-n 8`: ≈ 2 min mesh + 28 s +
31 × 0.6 s ≈ 3.5 min and ≈ 17 GiB — well inside the 5–45 min / 10–40 GiB
brackets below, which stand unchanged (the XL window runs at `-n 16`, where
neither has been measured).

**Licence class:** cost probe — the first XL window on an unpriced case
(§5.1: "the first XL window on it is a cost probe whose readout says so").
`WF-7` step 0 priced *one* degree-1 drive on this mesh at `-n 8` on the
ordinary service (37 s solve, 123 s mesh, 10.93 GiB summed,
`20260913T190102Z_WF-7-step0.log:10419–10427`); the full 32-column set at
`-n 16` on the XL service has never run. The weekly posed the question
(daily-review.md step 6b.4: "the F-human degree-1 solve at the full port
set").

**What runs:** the step-0 probe once with every ring port driven in turn
(`FEM_EM_WF7_PORTS=all`, degree 1, 64 MHz, `-n 16`), each column's fields
dropped after its `S` column is read; the 32×32 assembled and its
reciprocity ratio, `σ_max` and class spreads printed beside `PORT-13`'s
imported bands.

**Command (final once the knob lands; the knob name is the contract):**

```
XL_CHUNK="WF-7-step0c"
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && R=/workspace/logs/wf7-step0c-raw.log && { echo [orphans-before]; pgrep -c python3; true; } > \$R 2>&1; PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_WF7_PORTS=all timeout -k 60 7200 mpiexec -n 16 python3 scripts/probes/wf7_step0_f_human_cost.py >> \$R 2>&1; rc=\$?; { echo [orphans-after]; pgrep -c python3; true; } >> \$R 2>&1; echo \"[XL] memory.peak bytes:\" >> \$R; cat /sys/fs/cgroup/memory.peak >> \$R; echo \"[capture] rc=\$rc\" >> \$R; cat \$R; exit \$rc'"
```

**Price, predicted (unmeasured — that is the point):** from step 0's
37 s per drive at `-n 8` without factor reuse, 32 drives ≈ 20 min plus
the 2 min mesh; at `-n 16` and with `reuse_factorization` after the first
drive the solve part could fall to a few minutes. **Brackets: 5–45 min,
10–40 GiB summed `ru_maxrss`**; the probe prints INSIDE / OUTSIDE per
drive and cumulatively, so a killed window still prices how far it got.
Timeout 7 200 s inside the 4 h window.

**Readout (the price, and records only):** unknowns, per-drive solve time
with and without reuse, cumulative wall clock, `ru_maxrss` per rank /
summed, `memory.peak`; the 32×32's `_reciprocity_ratio`, `σ_max` and class
spreads **printed** beside `RECIPROCITY_BAND` / `COLUMN_PASSIVITY_CEILING`
/ `OPPOSITE_SPREAD_BAND` — nothing asserted beyond the imported cell band.
**Decision rule for the weekly:** the price dates the human-scale S sweep
in §10 (a full set inside one `xl` window ⇒ the F-human degree-1 32×32 is
an ordinary XL job; outside ⇒ `TH-16` symmetry planes move up); a
reciprocity or passivity miss on the human-scale mesh is a finding for a
`PORT` chunk, not a band change.

### 7. `xl` — `ANS-4` step 3e: the 64 MHz degree-2 *h*-ladder (daily licence: priced-family variant, 2026-09-18 review)

**Status:** QUEUED 2026-09-18 for Tuesday 2026-09-22 02:00 —
`docs/testing/xl-queue.d/20260922-ANS-4-step3e.env`.

**Licence class:** priced-family variant of the `ANS-4-step2d` ledger row
(2026-09-10) — the same module, the same generator, **the same
`RUNGSPEC="0.015:1 0.015:2 0.0075:2 0.005:2"` as step 2d, frequency varied
only**: `FEM_EM_ANS4_FREQUENCY_HZ=64e6` (the knob `ANS-4-step3` /
`step3c` already ran green at `-n 16`). Every rung has a measured point at
this tier (step 2d: 116 085 / 116 085 / 281 728 / 592 744 cells, 0.14 /
0.74 / 1.80 / 3.79 M unknowns), so this is a variant, not a cost probe.

**Why (the §10 question it answers):** step 2d showed the 128 MHz degree-2
sequence *converging in h* (successive change 1.19 % → 0.62 %, ratio 1.90),
which is what lets the 128 MHz order-matched rung be read as a value rather
than a point. At 64 MHz only the two end rungs exist (`ANS-4-step3`:
`0.015:1` and `0.005:2`), so the 64 MHz order-matched figure the 09-19
weekly adjudicates has no *h*-convergence statement under it. This window
supplies the two missing degree-2 rungs at 64 MHz and the same successive-
change readout.

**Command:**

```
XL_CHUNK="ANS-4-step3e"
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_ANS4_FREQUENCY_HZ=64e6 FEM_EM_ANS4_STEP2_RUNGSPEC=\"0.015:1 0.015:2 0.0075:2 0.005:2\" timeout -k 60 14400 mpiexec -n 16 python3 -m pytest tests/environment tests/validation/test_ans4_resolution_ladder.py -v -s --tb=short > /workspace/logs/ans4-step3e-raw.log 2>&1; rc=\$?; echo \"[XL] memory.peak bytes:\" >> /workspace/logs/ans4-step3e-raw.log; cat /sys/fs/cgroup/memory.peak >> /workspace/logs/ans4-step3e-raw.log; echo \"[capture] rc=\$rc\" >> /workspace/logs/ans4-step3e-raw.log; cat /workspace/logs/ans4-step3e-raw.log; exit \$rc'"
```

**Price, inherited from the family (scaling stated):** step 2d ran this
exact `RUNGSPEC` at `-n 16` in **7225 s, 290.2 GiB peak** *before* factor
reuse (four-drive times 12.0 / 169.0 / 1119.2 / 5653.5 s). With `PORT-19`
reuse in the module since 09-11 the finest rung's four drives measured
**1476.9 s** (`ANS-4-step3`), a factor 3.8; applying the same factor to the
two middle rungs gives ≈ 12 + 45 + 295 + 1480 s of solves plus four mesh
builds — **predicted 2 000–3 500 s**, memory set by the finest rung,
**270–295 GiB**. Timeout 14 400 s inside the 4 h window; 512 GiB limit.
Frequency does not change the factorisation's size.

**Readout (record, nothing asserted beyond the module's imported gates and
its own ladder controls):** public — the three C4 classes of `S` at 64 MHz
on the three degree-2 rungs, the successive changes and their ratio beside
step 2d's 128 MHz 1.19 % → 0.62 % (1.90), every imported `PORT-11` gate per
rung; private (`docs/private/`) — nothing new is needed: the AED column is
the one step 3 is read against. **Decision rule for the weekly:** successive
degree-2 changes falling with ratio ≳ 1.5 and the last one below the
64 MHz two-rung move's smallest class (step 3, 2.60 %) ⇒ step 3's `0.005:2`
figure is an *h*-converged value at the stated successive change and the
adjudication may quote it as such; a non-monotone or non-falling sequence
⇒ the 64 MHz order-matched figure is a point, not a value, and the row
says so. No band moves. The module's 128 MHz record assert is skipped at
`-n 16` by design (`OPS-41`). **Trap already paid for:** step 2d's single
failure was the ladder's refinement control comparing two rungs that share
one mesh (`0.015:1` vs `0.015:2`), fixed 2026-09-10; this spec has run
green in that module only at 128 MHz, so a red on a ladder-control test at
64 MHz is a module finding for a §9 item, not a physics reading.

### 8. `xl` — `ANS-4` step 3f: the 10 MHz degree-2 rung on the C4-congruent cut (daily licence: priced-family variant, 2026-09-18 review)

**Status:** QUEUED 2026-09-18 for Wednesday 2026-09-23 02:00 —
`docs/testing/xl-queue.d/20260923-ANS-4-step3f.env`.

**Licence class:** priced-family variant of `ANS-4-step3c` (2026-09-18,
1603 s / 284.8 GiB) and `ANS-4-step3b` (2026-09-17, 1539 s / 273.1 GiB) —
same module, same `RUNGSPEC`, same frequency as 3c (10 MHz); **one named
env knob varied**: `FEM_EM_ANS4_STEP2_C4_CONGRUENT=1`, the knob 3b already
ran green at this rung (592 550 cells, 3 827 268 dofs).

**Why (the status it can move):** step 3c's degree-2 rung passed every
imported `PORT-11` gate, but its **self-class C4 spread read 0.4451 %
against the 0.5 % band** (`20260918T070008Z_ANS-4-step3c.log:4624`) — 89 %
of the band, where the identical mesh at 64 MHz read 0.1985 % and the
congruent-cut rung at 128 MHz read 0.0056 %. One frequency pair cannot say
whether that is the cut-off mesh's asymmetry growing as f falls or a
low-frequency property of the degree-2 solve. This window changes the one
variable 3b changed.

**Command:**

```
XL_CHUNK="ANS-4-step3f"
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_ANS4_FREQUENCY_HZ=10e6 FEM_EM_ANS4_STEP2_C4_CONGRUENT=1 FEM_EM_ANS4_STEP2_RUNGSPEC=\"0.015:1 0.005:2\" timeout -k 60 14400 mpiexec -n 16 python3 -m pytest tests/environment tests/validation/test_ans4_resolution_ladder.py -v -s --tb=short > /workspace/logs/ans4-step3f-raw.log 2>&1; rc=\$?; echo \"[XL] memory.peak bytes:\" >> /workspace/logs/ans4-step3f-raw.log; cat /sys/fs/cgroup/memory.peak >> /workspace/logs/ans4-step3f-raw.log; echo \"[capture] rc=\$rc\" >> /workspace/logs/ans4-step3f-raw.log; cat /workspace/logs/ans4-step3f-raw.log; exit \$rc'"
```

**Price, inherited:** three measured windows on this `RUNGSPEC` at `-n 16`
— 1658 / 1539 / 1603 s, 280.8 / 273.1 / 284.8 GiB (all with a warm FFCx
cache; the named cache volume survives the pre-window recreate). Prediction
**1 500–1 800 s, 270–290 GiB**. Timeout 14 400 s; 512 GiB limit.

**Readout (record; the imported gates are the module's own and stay
unmoved):** the degree-2 rung's three class spreads at 10 MHz with the cut
on, beside 3c's 0.4451 / 0.2199 / 0.2186 % (cut off); the two-rung move on
the driven column beside 3c's 4.41 / 1.35 / 1.08 %. **Decision rule for the
weekly:** self spread collapsing by an order (as 128 MHz did, to the 1e-2 %
class) ⇒ the 0.4451 % is the cut-off port-sheet asymmetry, `GEO-32`'s row
gains the degree-2 10 MHz reading and the congruent cut is the rung to
quote at low frequency; self spread staying in the 0.4 % class ⇒ a
frequency trend in the degree-2 C4 identity that would breach the band
below 10 MHz — a known-issues entry and a `PORT` systematics item, **never
a band change**. A red `PORT-11` gate in this window (spread > 0.5 %) is
the same finding, stronger, and is reported as measured.

### 9. `xxl` — `WF-7` step 0d: the F-human degree-2 solve at the full 32-port set (daily licence: priced-family variant, 2026-09-19 review)

**Status:** QUEUED 2026-09-19 for Saturday 2026-09-26 02:00 —
`docs/testing/xxl-queue.d/20260926-WF-7-step0d.env`.

**Licence class:** priced-family variant of the `WF-7-step0b` `xxl` ledger
row (2026-09-19) — the same probe, the same mesh (507 266 cells), the same
order (degree 2, measured at this tier: 3 256 418 unknowns, 347.56 s,
107.9 GiB summed, `memory.peak` 106.1 GiB), the same 64 MHz; **port set
varied only**: `FEM_EM_WF7_PORTS=all`, the knob `a267c5a` landed and entry 6
runs at degree 1 on 09-21. The two knobs are independent in the probe
(`wf7_step0_f_human_cost.py:117`, `:123`) but **have never run together** —
a red at the knob interaction is a probe finding for a §9 item, not a
physics reading. The weekly may replace or reorder this entry by renaming
or deleting the queue file; nothing depends on it.

**Why (the §10 question it answers):** step 0b priced *one* degree-2 column
at human scale and read a 5.50 % order move on it. If the weekly's branch
(a) holds (degree 2 is the production order at human scale), the quantity
§10 needs is the price of the **whole** degree-2 32×32 — one factorisation
plus 31 back-substitutions — and whether the human-scale degree-2 matrix
keeps `PORT-13`'s identities. It also answers, for free, whether step 0b's
degree-2 power-accounting residual (1.104e-02, 2.6× the degree-1 one) is a
property of port P17 or of every column.

**Command:**

```
XL_CHUNK="WF-7-step0d"
XL_COMMAND="docker compose --profile xxl exec -T fem-em-solver-xxl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && R=/workspace/logs/wf7-step0d-raw.log && { echo [orphans-before]; pgrep -c python3; true; } > \$R 2>&1; PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_WF7_DEGREE=2 FEM_EM_WF7_PORTS=all timeout -k 60 14400 mpiexec -n 16 python3 scripts/probes/wf7_step0_f_human_cost.py >> \$R 2>&1; rc=\$?; { echo [orphans-after]; pgrep -c python3; true; } >> \$R 2>&1; echo \"[XL] memory.peak bytes:\" >> \$R; cat /sys/fs/cgroup/memory.peak >> \$R; echo \"[capture] rc=\$rc\" >> \$R; cat \$R; exit \$rc'"
```

**Price, inherited from the family (scaling stated):** step 0b's degree-2
leg — 133 s mesh, 347.56 s first drive (factorisation 242.5 s), MUMPS
forward/backward solve driver **1.846 s** on the held factor
(`20260919T070008Z_WF-7-step0b.log:21167`). Thirty-one further columns at a
few seconds each (the degree-1 two-drive window read 0.59 s per held
column against a 0.20 s solve driver, a factor ≈ 3 of overhead) ⇒
**predicted 10–20 min, 105–130 GiB** (the factor is held once; column fields
are dropped after each `S` column is read). Timeout 14 400 s inside the 8 h
window; 754 GiB limit. The probe's own degree-2 brackets (150–350 GiB,
10–60 min *per drive*) are step 0b's stale prediction and, unless `OPS-52`
has re-dated them by then, will print OUTSIDE — a label, not a finding
(known-issues 2026-09-19).

**Readout (record — nothing asserted beyond the imported cell band):**
unknowns, first-drive and per-held-column solve times, cumulative wall
clock, `ru_maxrss` per rank / summed, `memory.peak`; the degree-2 32×32's
`_reciprocity_ratio`, `σ_max` and class spreads **printed** beside
`RECIPROCITY_BAND` / `COLUMN_PASSIVITY_CEILING` / `OPPOSITE_SPREAD_BAND`,
next to entry 6's degree-1 values; the per-column power-accounting
residual. **Decision rule for the weekly:** a full degree-2 set inside one
window at this price ⇒ the human-scale degree-2 S sweep is an ordinary
`xl`-sized job (106 GiB fits the 512 GiB service) and §10 dates it as such;
a reciprocity or passivity miss at degree 2 that entry 6 does not show at
degree 1 ⇒ a finding for a `PORT` chunk; residuals near 1e-2 on every
column ⇒ the accounting's degree-2 quadrature or the sheet term is the
suspect, a `POST` item — **never a band change**.

### 10. `xl` — `ANS-2` step 4: the phantom h-halving, four drives (operator session 2026-09-19; daily-licence class: cost probe, price measured by the step's own probe)

**Status:** QUEUED 2026-09-20 for Friday 2026-09-25 02:00 —
`docs/testing/xl-queue.d/20260925-ANS-2-step4.env`. *(Was READY.)* `ANS-2` step 4a landed 2026-09-19 (§9 item 9): the example
reads `FEM_EM_ANS2_PHANTOM_RESOLUTION`, tags `metrics_h<res>.json` and the
XDMF, skips the two 0.0025-rung mesh-record assertions **with a printed
`[ANS-2 step 4] MESH-RECORD ASSERTIONS SKIPPED` line** while every other
imported band stays asserted, leaves `COMPARISON.md` /
`COMPARISON_private.md` alone, and prints the `[ANS-2 step 4]` readout
(driven-point SAR, C4 spread, phantom powers, each beside the tracked 0.0025
rung's own `metrics.json`). Anchors measured green — unset vs the tracked
`metrics.json` and knob-`0.0025` vs unset both digit-identical at
`EXACT_IDENTITY_RTOL` on every primary leaf (worst 8.19e-11 / 8.17e-11),
negative control at 0.004 m prints the skip line and exits 0
(`20260919T141006Z_ANS-2-step4a-unset-control.log`,
`20260919T142050Z_ANS-2-step4a-knob-identity.log`). *The next review only
queues this entry — the first free `xl` night (Thu 2026-09-24 02:00 as of
writing).*

**Why `xl`:** the step's pre-registered cost probe fired its own STOP rule
(`32f4eae`, `20260919T093241Z_ANS-2.log`): at `phantom_resolution` =
0.00125 m the fixture meshes to **719 769 cells (452 228 phantom) / 845 188
unknowns**, mesh **359.8 s**, one drive **188.4 s**, `ru_maxrss` **40.89 GiB
summed** at `-n 8` — past the item's 15 min / 40 GiB stop and past §5.1's
20-min cap for four drives. §5.1's rule is met: the price is *measured*, on
this mesh, at this width.

**What runs:** the `ANS-2` example at the halved rung, all four single-port
drives, `-n 8` (the measured width; 16 ranks is unmeasured on this mesh and
not needed), durable capture per §5.1. **Outputs to commit:**
`metrics_h0.00125.json` and
`paraview_output/ans2_birdcage_coil_driven_sar_10mhz_combined_h0p00125.xdmf`
(the XDMF tag writes the decimal point as `p` — `write_xdmf_with_tags` strips
everything after the last dot as a suffix, which silently collapsed every
rung onto one filename until step 4a measured it); `metrics.json` and
`COMPARISON.md` are untouched by an overridden run.

**Command (final once 4a lands; the knob name is the contract):**

```
XL_CHUNK="ANS-2-step4"
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && R=/workspace/logs/ans2-step4-raw.log && { echo [orphans-before]; pgrep -c python3; true; } > \$R 2>&1; PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_ANS2_PHANTOM_RESOLUTION=0.00125 timeout -k 60 7200 mpiexec -n 8 python3 examples/ansys_benchmarks/ans2_birdcage_coil_driven_sar_10MHz/02_birdcage_coil_driven_sar_10MHz.py >> \$R 2>&1; rc=\$?; { echo [orphans-after]; pgrep -c python3; true; } >> \$R 2>&1; echo \"[XL] memory.peak bytes:\" >> \$R; cat /sys/fs/cgroup/memory.peak >> \$R; echo \"[capture] rc=\$rc\" >> \$R; cat \$R; exit \$rc'"
```

**Price, measured (the probe):** mesh 360 s once + 4 × 188 s ≈ **1 115 s** —
step 4a settles the open branch: **the example meshes once** for all four
drives (0.0025 rung, `-n 4`: 184.8 s wall of which 74.4 s is the four solves,
so a single mesh build precedes them; `20260919T142050Z_ANS-2-step4a-knob-identity.log`),
so the ≈ 2 200 s re-meshing arm is dead; ≈ 41 GiB summed at `-n 8` (the probe's figure; four drives hold one
field at a time). Timeout 7 200 s inside the 4 h window; 512 GiB limit.

**Readout (record — the imported bands asserted, the mesh-record bands
skipped with a printed line per 4a):** the four driven-point SAR values and
their C4 spread beside the 0.0025 rung's (15.7 %); the four phantom powers
beside the 0.0025 rung's and their relative change; the mass-averaged C4
pairs at the imported 5 % band; the halved rung's cell counts as a
candidate record. **Decision rule (pre-registered in
`docs/private/ans2-adjudication-2026-09-18.md` and §7 `ANS-2` step 4):**
(a) spread < 5 % and phantom power moves < 2 % ⇒ the residual against
HFSS is the feed; the verdict's pointwise band tightens to the measured
spread. (b) phantom power moves ≥ 2 % toward AED ⇒ mesh convergence is part
of the residual; a third rung is priced by a review. (c) spread does not
fall ⇒ not `h` — a point-evaluation defect, known-issues + `POST` chunk.
No band moves in the window; the review that finds the ledger row rules.

### 11. `xl` — `ANS-4` step 3g: the 10 MHz degree-2 *h*-ladder (weekly 2026-09-19, §10 chain F step F2)

**Status:** QUEUED 2026-09-20 for Thursday 2026-09-24 02:00 —
`docs/testing/xl-queue.d/20260924-ANS-4-step3g.env` (ahead of entry 10 so
that a budget-denied night still leaves 3g run before the 09-26 weekly,
which reads it with 3e). *(Was READY.)* No prerequisite; the knob, the module and the `RUNGSPEC`
have all run green at `-n 16` (`ANS-4-step3c` 2026-09-18 at 10 MHz, step 2d
2026-09-10 with this `RUNGSPEC`). The next daily review queues it for the
first free `xl` night.

**Why (the §10 question it answers):** the 2026-09-19 weekly ruled that 3c's
public rule fired — the 10 MHz degree 1 → 2 move (4.41 / 1.35 / 1.08 %) is in
the same class as the Larmor moves — and that the order-matched comparison
disagrees on the self class at 10 MHz (known-issues 2026-09-19; numbers
private). Both readings rest on **one** degree-2 rung at 10 MHz. Entry 7
(3e) supplies the missing degree-2 rungs at 64 MHz; this is the same ladder
at 10 MHz, where the disagreement is largest.

**Command:** entry 7's, with `FEM_EM_ANS4_FREQUENCY_HZ=10e6` and the raw-log
name changed — nothing else:

```
XL_CHUNK="ANS-4-step3g"
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_ANS4_FREQUENCY_HZ=10e6 FEM_EM_ANS4_STEP2_RUNGSPEC=\"0.015:1 0.015:2 0.0075:2 0.005:2\" timeout -k 60 14400 mpiexec -n 16 python3 -m pytest tests/environment tests/validation/test_ans4_resolution_ladder.py -v -s --tb=short > /workspace/logs/ans4-step3g-raw.log 2>&1; rc=\$?; echo \"[XL] memory.peak bytes:\" >> /workspace/logs/ans4-step3g-raw.log; cat /sys/fs/cgroup/memory.peak >> /workspace/logs/ans4-step3g-raw.log; echo \"[capture] rc=\$rc\" >> /workspace/logs/ans4-step3g-raw.log; cat /workspace/logs/ans4-step3g-raw.log; exit \$rc'"
```

**Price, measured in the family:** the finest rung at 10 MHz is 3c's own
window — four drives 1419.4 s, `memory.peak` 284.8 GiB, 1603 s total; the two
middle rungs scale from step 2d by the reuse factor entry 7 states
(≈ 45 s + ≈ 295 s) plus four mesh builds ⇒ **predicted 2 000–3 500 s,
270–295 GiB**. Frequency does not change the factorisation's size. Timeout
14 400 s inside the 4 h window; 512 GiB limit.

**Readout (record; nothing asserted beyond the module's imported gates and
ladder controls):** public — the three C4 classes at 10 MHz on the three
degree-2 rungs, the successive changes and their ratio beside step 2d's
128 MHz 1.19 % → 0.62 % (1.90) and 3e's 64 MHz pair; every imported gate per
rung (watch the self-class spread: 0.4451 % of a 0.5 % band on 3c's rung —
a red there is a `GEO-31`-class mesh reading, and entry 8 (3f, the congruent
cut at 10 MHz) is its control, not a reason to touch the band). Private —
nothing new: the AED column is the one 3c was read against.

**Decision rule (pre-registered, PROJECT_PLAN §10 2026-09-19):** successive
degree-2 changes falling with ratio ≳ 1.5 **and** the last change below the
smallest class move (1.08 %) ⇒ 3c's `0.005:2` figure is an *h*-converged
value, the 10 MHz self-class disagreement is a model-level difference, and
with the same outcome on 3e the production default flips to degree 2 by
`TH-19` step 4 and `PORT-21` step 2 reads its table against a converged
residual. Non-monotone or non-falling ⇒ the 10 MHz order-matched figure is a
point, not a value; the default stays at degree 1; the ladder is the finding.
No band moves.

### Weekly rulings on RUN entries, 2026-09-19 (full text PROJECT_PLAN §10; AED figures private)

- **Entry 1 (`WF-7` 0b, `xxl`)** — branch **(a)**: 5.50 % is in F-small's
  64 MHz class; degree 2 is the human-scale order at 106.1 GiB / 348 s per
  drive. The degree-2 terminal power residual (1.104e-02) is an unattributed
  record; chain H step H3 asserts the exact discrete identity.
- **Entry 2 (`ANS-4` step 3, 64 MHz)** — the pre-registered private rule
  **fired on the self class**; couplings inside it. The 64 MHz "AGREE by
  mechanism" is withdrawn for `S₁₁`, kept for the coupling classes.
  Known-issues 2026-09-19, `PORT-21`.
- **Entry 3 (`ANS-4` step 3b, 128 MHz, congruent cut)** — rule **did not
  fire**: classes within step 2d's spreads of step 2d's (≤ 0.083 % against
  ≤ 0.142 %). The cut is not a degree-2 systematic; the 128 MHz AGREE stands.
- **Entry 4 (`ANS-4` step 3c, 10 MHz)** — rule **fired**: the 10 MHz move is
  in the Larmor moves' class, so the degree-1 10 MHz AGREE is re-read as
  partly coincidental. The self-class spread at 89 % of its band is read
  with entry 8 when it runs.
- Entries 5–9 (daily licence) **kept**; entry 10 stays READY; entry 11 added.
