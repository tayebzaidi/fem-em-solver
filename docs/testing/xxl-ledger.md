# XXL-tier ledger — the Saturday window, one run per week, 754 GiB / 8 h

Operator directive 2026-09-10 (PROJECT_PLAN §5.1). The `fem-em-solver-xxl`
compose service (profile `xxl`, 754 G limit) exists for the cases a 2 h `xl`
window cannot hold. Commissioned like `xl` — by the weekly planning review or
the operator, with a pre-registered readout — and gated by the same guard,
which counts the rows below against a budget of **one per trailing 7 days**.

`run_and_log.sh` appends the row when a window **starts**, so a killed or
failed run has still spent the week. Fill the last four columns by hand from
the footer and commit the row with the log.

Why 754 GiB: this WSL VM's whole allocation, half of the machine's 1.5 TB. A
container limit equal to the VM's total memory means the kernel OOM killer
reaches a runaway before the cgroup does — recorded in `docker-compose.yml`
rather than silently softened.

| Date (UTC) | Chunk | Log | Ranks | Cells | Peak memory (GiB) | Elapsed (s) | Readout |
|---|---|---|---|---:|---:|---:|---|
