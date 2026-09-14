# XL / XXL pending windows — pre-registered by the weekly, queued by the daily

**Why this file exists (operator directive 2026-09-13).** XL and XXL windows
are cron scripts with no Claude session — the only compute in the project
that costs no tokens — but only the weekly review may commission one, the
queue files hold one item each, and under the wind-down schedule the weekly
runs once a week. Left as it was, at most one of the three budgeted XL
windows and, some weeks, no XXL window would run. This file splits the role:
the **weekly decides** (it pre-registers entries here — tier, chunk and step,
the exact command, the measured price, the readout and the decision rule)
and the **daily review is the clerk** (daily-review.md step 6b: it copies the
top READY entry of a tier into `docs/testing/<tier>-queue.env`
verbatim when that queue is empty and the tier's budget allows). An
interactive operator session may do either.

**Budget, as the clerk reads it.** `xl`: fewer than six rows with a
non-zero `Elapsed` in the trailing 7 days of `docs/testing/xl-ledger.md`
(nightly Sun–Fri, operator directive 2026-09-13)
(killed and 0-second rows are uncharged, §5.1). `xxl`: no such row in the
trailing 7 days of `docs/testing/xxl-ledger.md`. The next run date is the
next 02:00 for the tier (xl Sun–Fri, xxl Saturday) after the budget opens.

**Status words.** `READY` — prerequisite landed, command final. `PENDING
PREREQUISITE` — names the item that must land first (an ordinary §9 item).
`QUEUED <date> for <run date>` — copied into the queue file. `RUN <log>` —
the launcher cleared the queue; the review that finds the ledger row marks
it and the weekly interprets it. Entries are never edited after `QUEUED`
except to add the run status; a changed command is a new entry.

## Entries

### 1. `xxl` — `WF-7` step 0b: the F-human rung at degree 2, one drive, 64 MHz

**Status:** QUEUED 2026-09-13 (operator, interactive) for Saturday
2026-09-19 02:00.

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

**Status:** PENDING PREREQUISITE — `ANS-4` step 3a.

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
XL_COMMAND="docker compose --profile xl exec -T fem-em-solver-xl bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && mkdir -p /workspace/logs && PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 FEM_EM_SOLVER_PROGRESS=2 FEM_EM_ANS4_FREQUENCY_HZ=64e6 FEM_EM_ANS4_STEP2_RUNGSPEC=\"0.015:1 0.005:2\" timeout -k 60 7200 mpiexec -n 16 python3 -m pytest tests/environment tests/validation/test_ans4_resolution_ladder.py -v -s --tb=short > /workspace/logs/ans4-step3-raw.log 2>&1; rc=\$?; echo \"[XL] memory.peak bytes:\" >> /workspace/logs/ans4-step3-raw.log; cat /sys/fs/cgroup/memory.peak >> /workspace/logs/ans4-step3-raw.log; echo \"[capture] rc=\$rc\" >> /workspace/logs/ans4-step3-raw.log; cat /workspace/logs/ans4-step3-raw.log; exit \$rc'"
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
