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
