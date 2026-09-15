# XL / XXL queue directories

`xl-queue.d/` and `xxl-queue.d/` are the FIFO queues `scripts/automation/xl-run.sh`
reads at 02:00 (operator directive 2026-09-15). Each `*.env` file holds one
window in the `XL_CHUNK` / `XL_COMMAND` format of the legacy `<tier>-queue.env`
(still honoured first when non-empty). Files run in lexical order, so name them
`<intended run date>-<chunk>.env`; the launcher checks the ledger budget before
taking a file, runs the first valid one, and deletes it afterwards whether the
window succeeded or failed. Entries are copied **verbatim** from
`xl-pending.md` by the daily review (daily-review.md step 6b), the weekly, or
the operator — never authored here.
