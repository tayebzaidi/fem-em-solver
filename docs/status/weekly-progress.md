# Weekly progress against cost

Append-only. One `## YYYY-MM-DD` section per weekly planning review, written
by docs/automation/weekly-review.md step 2b: the mechanical counts from
`scripts/automation/weekly_counts.py` pasted verbatim, then the review's own
rows — newly supported workflows, uncertainties resolved (negative results
included), defects retired, repeated failure, lost slots, cost — ending in a
three-line **decision**: one activity to continue, one to change or stop, and
the evidence for each.

Rules of the file:

- **No single score.** Commit count, queue depth and machine time spent are
  context, never success. An XL / XXL window is reported by what it decided.
- **`unavailable` stays `unavailable`.** Token usage is not recorded (the
  launchers run `claude -p` in text mode); it is never estimated here.
- **Evidence or nothing.** Every row cites a chunk ID, a `log:line` or a
  commit. Ansys figures never appear — qualitative verdict only.
- The interval is "since the last weekly-review commit", measured, not seven
  days.
