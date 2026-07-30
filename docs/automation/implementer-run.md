# Implementer run protocol (Opus, scheduled)

Run by `scripts/automation/implementer-run.sh` via cron, six times daily
(every 3 h at :42, 07:42–22:42 local). One run = one attempt at the **top
"On deck" item** in PROJECT_PLAN.md §9.

## Timebox

60 minutes wall clock, externally enforced (the wrapper kills the session at
65). Note the start time immediately; **start no new implementation work
after minute 45** — the final 15 minutes are for documentation and leaving a
clean tree. The per-command compute budget is unchanged and non-negotiable:
§5.1 tiers, 10-minute hard ceiling, `timeout` at the tier ceiling, shared
machine.

## Steps

1. Preflight: `git status` must be clean. If it is not, do **no** chunk work:
   append an `anomaly` entry to `docs/testing/attempts.md` describing what
   you found, commit only that, and stop. Confirm the container is Up per
   CLAUDE.md.
2. Take the FIRST item under "On deck" in §9 that is not marked done or
   blocked. Do not choose a different item for any reason. If the list is
   empty, append an attempts.md entry saying so and stop.
3. Execute the chunk following `.claude/agents/implementer.md` (read it
   first) and the chunk's §7 entry, which carries the implementation plan.
4. Outcome:
   - **Complete** (§4-done: verification executed, quantitative assertion,
     harness log + elapsed time recorded): commit code + tests + logs +
     §7 status flip together on `main`, marking the On-deck item done in the
     same commit.
   - **Incomplete** (out of time, or blocked): park ALL code changes on a
     branch `attempt/<CHUNK-ID>-<UTC-timestamp>` (commit there, return to a
     clean `main`). On `main`, commit only the attempts.md entry plus any §7
     annotation (🟡/🚫 with the blocker named). **Never leave `main` red or
     dirty** — a half-applied change on main costs the next run its
     preflight.
5. Always append an entry to `docs/testing/attempts.md` (append-only): UTC
   timestamp, chunk ID, outcome (`complete|incomplete|blocked|anomaly`),
   what was tried, measured numbers, harness log filenames, branch name if
   parked, and a one-line hypothesis for the next attempt. The daily review
   is the reader — write for it.

## Non-negotiables

Everything in `.claude/agents/implementer.md` applies unchanged: all
verification through `run_and_log.sh`, tier ceilings with kill-and-shrink on
overrun, never loosen assertions, rank-safety reductions, no work on ⚠️
subsystems, known-issues.md discipline for unrelated failures.

## Working inside the permission allowlist

Scheduled sessions run against `.claude/settings.json` with no human to
answer prompts — a denied tool call is simply denied. Consequences:

- All compute goes through `scripts/testing/run_and_log.sh ...` or
  `docker compose exec ...` at the **top level** of the Bash command. Host
  `python3`/`pytest` are not allowed and the host lacks dolfinx anyway.
- Read files with the Read/Grep/Glob tools, not `cat`/`sed`/`head` — the
  generic readers are not allowlisted, deliberately.
- Multi-line commit messages: write the message to a file with the Write
  tool and use `git commit -F <file>` (then delete the file via the same
  commit's `git add` scope or leave it untracked in the scratch area).
  Command substitution like `git commit -m "$(cat ...)"` is treated as
  injection by the permission layer and will be denied.
- If a genuinely needed command is denied, do not fight it: document the
  denial in your attempts.md entry so the daily review can propose an
  allowlist change to the human.
