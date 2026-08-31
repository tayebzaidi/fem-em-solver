# Implementer run protocol (Opus, scheduled)

Run by `scripts/automation/implementer-run.sh` via cron, twelve times daily on
a 90-minute grid shared with the daily review (04:30, 06:00, 07:30, 09:00,
12:00, 13:30, 15:00, 16:30, 19:30, 21:00, 22:30, 00:00 local — four runs after
each of the three reviews at 03:00 / 10:30 / 18:00). One run = one attempt at
the **top "On deck" item** in PROJECT_PLAN.md §9. Sessions never overlap: the
grid spacing exceeds the 65-minute hard kill, and all runs share one `flock`.

## Timebox

60 minutes wall clock, externally enforced (the wrapper kills the session at
65). Note the start time immediately; **start no new implementation work
after minute 45** — the final 15 minutes are for documentation and leaving a
clean tree. The per-command compute budget is unchanged and non-negotiable:
§5.1 tiers, 20-minute hard ceiling per compute command, `mpiexec -n 12` max,
`timeout` at the tier ceiling, shared machine.

## Steps

1. Preflight: `git status` must be clean. If it is not, do **no** chunk work:
   append an `anomaly` entry to `docs/testing/attempts.md` describing what
   you found, commit only that, and stop. Confirm the container is Up per
   CLAUDE.md.

   **Exception — already-journaled documentation drift.** If a *prior* run's
   attempts.md anomaly entry already describes this exact dirty tree, you may
   land it and proceed with chunk work, provided ALL of the following hold
   (verify each; do not assume):
   - the current diff is **byte-identical** to the one the prior entry
     journaled (same files, same `git diff` content);
   - it touches **documentation only** — nothing under `src/`, `tests/`,
     `scripts/`, and no §7 status or done-when change in PROJECT_PLAN.md;
   - the edits are internally consistent and complete (they read as a
     finished change, not half of one).

   Commit the diff **by itself** first (`docs: land dirty tree journaled
   <UTC timestamp of the anomaly entry>`), note in your own attempts.md
   entry that you landed it and why the conditions held, then continue at
   step 2. If any condition fails — new or different dirtiness, anything
   non-documentation, no prior journal entry — the original rule applies
   unchanged: anomaly entry, commit only that, stop. Never discard or stash
   a human's edits; landing an already-journaled doc diff is the only
   permitted action.

   **Second encounter — park it and proceed.** If a prior run's attempts.md
   anomaly entry already journaled a dirty tree and the tree is *still* dirty
   now, the tree is stuck and stopping again just burns the rest of the day's
   slots. Whatever the diff contains:
   - commit it **as-is** to a new branch `recovered/<UTC-timestamp>` (create
     the branch, commit there, return to a clean `main`);
   - journal in your attempts.md entry what you parked, the branch name, and
     the timestamp of the prior entry that made this the second encounter;
   - then continue at step 2 and do chunk work normally.

   Parking preserves the content — nothing is discarded or stashed, and the
   branch is recoverable with one `git checkout`. The first encounter still
   stops, so a human editing interactively is never interrupted mid-change;
   only a tree that survived a full slot unattended gets moved. Never delete a
   `recovered/*` branch; the daily review disposes of it.
2. Take the FIRST item under "On deck" in §9 that is not marked done or
   blocked. Do not choose a different item for any reason. If every item is
   done or blocked, fall back to the chunk named in §9's "obvious next entry"
   sentence, scoped to one run; note in attempts.md that you used the
   fallback. If that sentence names nothing, append an attempts.md entry
   saying so and stop.
3. Execute the chunk following `.claude/agents/implementer.md` (read it
   first) and the chunk's §7 entry, which carries the implementation plan.
   Specialist executors exist for three chunk classes — an EX-* example
   chunk goes to `example-runner`, a measurement-only mesh/resolution probe
   to `mesh-probe`, a version-bump record sweep to `record-reconciler`
   (.claude/agents/); everything else stays with the implementer agent.
   `plan-navigator` and `log-pathologist` are available read-only for
   lookups and disputed prior logs. Never spawn `auditor` on your own
   closure — auditing is the review's job.
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
- **Never run the harness with `run_in_background`, and never end your turn
  while a harness command is running.** You are a headless `claude -p`
  session: ending the turn exits the CLI (exit 0), which SIGKILLs the
  backgrounded harness — footerless log, untracked artifacts, no journal
  entry, and the tree left dirty for the next slot. Three consecutive slots
  paid this on 2026-08-10/11 (19:30, 22:30, 00:00 — the whole night) on the
  same item. Run harness commands in the **foreground** with the Bash tool's
  `timeout` parameter at its 660000 ms maximum, and size the
  **container-side** `timeout` so the command returns a footer inside that
  window (≤ ~590 s of container time for a command with ~1 min of setup).
  Always write the container-side timeout as **`timeout -k 30 <s>`** — a
  plain TERM does not reliably stop an `mpiexec` job (MAT-6 step 10,
  2026-08-12: `timeout 590` fired and the ranks ran on for ~1 700 s,
  wedging the container). If a container wedges anyway (`exec` hangs,
  `restart`/`kill` report "did not receive an exit event"), the recovery
  is `docker compose -f docker/docker-compose.yml up -d --force-recreate`,
  then verify `memory.max` and zero stray `python3` before continuing. A
  compute step that cannot finish inside one foreground window at ≤ 12 ranks
  is too big for a scheduled slot: shrink the case or journal it for the
  review — do not background it.
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
