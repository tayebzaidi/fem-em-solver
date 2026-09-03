# Retention policy — logs, journals, and repo hygiene

Adopted 2026-09-03. This document says what the repo keeps, for how long,
and who removes the rest. It exists because harness logs were arriving at
about forty a day and the tracked log volume passed 110 MB in August 2026;
the journals that cite them had passed 70 000 lines between them.

The mechanical half of this policy is `scripts/maintenance/housekeeping.py`
(`--report` is read-only, `--apply` performs the sweep, `--check` exits
non-zero when a budget is exceeded). The preventive half is the filter
built into `scripts/testing/run_and_log.sh`. Nothing in this policy edits a
log's contents after it is written, rewrites git history, or removes a log
that a closure cites.

## 1. Artifact classes and retention

Ages are measured from the UTC timestamp in the log's filename
(`YYYYMMDDTHHMMSSZ_<chunk>.log`), not from mtime, so a checkout on another
machine reaches the same verdict.

| Class | What it is | Compress | Delete |
|---|---|---|---|
| **Gating log** | Cited by basename from `PROJECT_PLAN.md`, `docs/planning/plan-archive.md`, `docs/testing/known-issues.md`, any `examples/**/*.md`, `docs/validation/**/*.md`, `docs/ports/**/*.md`, or pinned in `docs/testing/retention-keep.txt` | at 7 days | **never** |
| **Non-gating log** | Every other file in `docs/testing/logs/` — failed attempts, reruns, probes, dry runs, smoke checks whose only citation is `attempts.md` or the `test-results.md` index | at 7 days | at 14 days |
| **Index** (`docs/testing/test-results.md`) | One row per harness run, append-only | never | never — it is the record that a deleted log once existed |
| **Journals** (`attempts.md`, `known-issues.md`, `PROJECT_PLAN.md`) | Narrative of record | rotated to the `*-archive.md` files by the weekly review, on the line thresholds in §3 | never |
| **Probe scripts** (`scripts/probes/`) | One-off measurement scripts | — | flagged by the sweep when their chunk ID no longer appears in `PROJECT_PLAN.md`; removal is a review decision, never automatic |

Why citation defines "gating": §4 of the plan makes a chunk ✅ only on an
executed, logged, quantitative assertion, and the auditor and
log-pathologist agents re-read those logs to overrule a status. Anything the
plan, the archive, known-issues, or an example guide points at is therefore
evidence and is kept. `attempts.md` cites every run it journals, including
the ones that went nowhere, so it does **not** confer gating status; the
journal entry itself is the surviving summary of a deleted log.

Compression keeps the basename and appends `.gz`, so every existing
citation still matches on a substring search. Readers use `zcat` or
`gzip -dc`; the Read tool does not open `.gz` files.

Deleted logs leave three traces: the `test-results.md` row, the
`attempts.md` entry, and git history. A citation that resolves to a missing
file should be read as "expired under this policy on the 14-day rule", and
if that log turns out to matter, restore it from history and add its
basename to `retention-keep.txt`.

## 2. Prevention — the harness filter

`run_and_log.sh` post-processes each log once the command exits. Runs of
consecutive gmsh mesh-optimisation progress lines (`ImproveMesh`,
`SwapImprove`, `SplitImprove`, `N swaps performed`, `Total badness`,
`a < quality < b`, and the like) collapse to one line reporting how many
were elided. Nothing else is touched: pytest output, tracebacks, the
`set -x` command echo, timing lines, and gmsh's node/element counts all
survive verbatim. The `## Exit` footer records the elided count so a reader
knows the log was filtered. Set `FEM_LOG_FILTER=0` to disable it for a run
whose raw mesher chatter is the object of study.

Rationale: the largest logs on main were ~1.9 MB each, and about nine
lines in ten were this chatter; the filter removes the growth at source
rather than paying for it in the sweep.

## 3. Budgets and tripwires

The sweep reports these; `--check` fails when any is exceeded, which is the
signal for the daily review to raise a "Housekeeping over budget" item in
the dashboard's Waiting-on-you section.

| Metric | Ceiling |
|---|---|
| Tracked `docs/testing/logs/` volume | 25 MB |
| Loose git objects (`git count-objects -v` size) | 50 MiB → `git gc` on `--apply` |
| `docs/testing/attempts.md` | 6 000 lines → rotate at the next weekly review |
| `docs/testing/known-issues.md` | 6 000 lines → rotate at the next weekly review |
| `PROJECT_PLAN.md` | 9 000 lines → compress closed §7 narratives per the weekly-review carve-out |

## 4. Cadence and ownership

- **Every harness run**: the filter (§2). No agent action.
- **Weekly sweep**: `scripts/automation/housekeeping.sh`, cron Sunday
  01:45 local (`scripts/automation/crontab`), runs `housekeeping.py --apply`
  and commits `chore(housekeeping): weekly sweep YYYY-MM-DD`. No Claude
  session is involved: the sweep is mechanical, skips on a dirty tree or off
  `main`, and shares the automation flock. What it can only flag (orphan
  probes, over-budget journals) lands in `docs/testing/housekeeping.md` for
  the next daily review; nobody widens the deletion set by hand.
- **Weekly review**: journal rotation on the §3 thresholds, as already
  specified in `docs/automation/weekly-review.md`.
- **Daily review**: reads `--check`, escalates an over-budget state.

## 5. What the sweep never does

- Delete a gating log, whatever its age.
- Modify a log's contents (compression is byte-preserving).
- Rewrite history, `git filter-*`, or force-push.
- Delete a probe script, an example, or a journal line.
- Run compute of any kind.
