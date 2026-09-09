# XL-tier ledger — one run per week, 512 GiB / 16 ranks / 2 h

Operator directive 2026-09-05 (interactive session; PROJECT_PLAN §5.1). The
`fem-em-solver-xl` compose service (profile `xl`, 512 G limit) exists for
**one** run per 7 days, commissioned **only by the weekly planning review**,
which names the chunk and its pre-registered readout. The bash guard
(`scripts/automation/hooks/bash_guard.py`) reads the most recent date in this
table and denies any XL command inside 7 days of it; `run_and_log.sh` appends
the row automatically when a harness command targets the XL service. Fill in
the last four columns by hand from the log after the run, and commit the row
with the log.

| Date (UTC) | Chunk | Log | Ranks | Cells | Peak memory (GiB) | Elapsed (s) | Readout |
|---|---|---|---:|---:|---:|---:|---|
| 2026-09-09 | ANS-4-step2b | `20260909T143756Z_ANS-4-step2b.log` | 16 | 116 085 | ~16.6 observed (see note) | 249 | degree 2 moves the three C4 classes of S at 128 MHz by **6.0900 / 5.3841 / 6.6959 %** off the degree-1 record; all imported gates green on both rungs, degree-2 class spreads *tighter* (0.0191–0.0334 % vs 0.0654–0.1012 %). **The slot was not needed:** 249 s against the predicted 1 100–1 300 s and ~16.6 GiB against ≳ 49 — this case fits the heavy tier and the ordinary 128 G service. |

**Note on the memory column (2026-09-09).** The step-2b module carries no
in-run `ru_maxrss` print, so 16.6 GiB is a `docker stats` reading taken by the
operator's interactive session while the degree-2 solve was running, **not a
measured peak** — the true peak is at or above it and was not instrumented. Any
future XL commissioning that leans on this figure should print `ru_maxrss`
instead. It is nonetheless a decade under the ordinary service's own 128 G
limit, which is the load-bearing part: this run did not need the tier.
| 2026-09-09 | TH-11-step5d | `20260909T145530Z_TH-11-step5d.log` | | | | | |
| 2026-09-09 | TH-11-step5d | `20260909T153910Z_TH-11-step5d.log` | | | | 4838 | |
