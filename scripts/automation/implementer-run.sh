#!/usr/bin/env bash
# Scheduled implementer run (Opus). Installed in crontab; see
# docs/automation/implementer-run.md for the protocol the session follows.
set -euo pipefail

REPO="/home/taz5297/Development/fem-em-solver"
LOCK="$HOME/.fem-em-automation.lock"
LOGDIR="$REPO/logs/automation"
CLAUDE_BIN="$HOME/.local/bin/claude"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

mkdir -p "$LOGDIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$LOGDIR/${TS}_implementer.log"

# One automation session at a time on this shared box, ever.
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u) another automation run holds the lock; skipping" >> "$LOG"
  exit 0
fi

cd "$REPO"
START="$(date '+%Y-%m-%d %H:%M %Z')"

# 60 min budget for the session, killed at 65 as the hard backstop.
# Permissions come from .claude/settings.json (allowlist + denies); acceptEdits
# auto-approves file edits inside the repo only. Web tools are off.
#
# Subagents: ON, but scoped by name to this repo's own definitions in
# .claude/agents/ (2026-08-31). Every built-in agent type is denied
# individually, so the only spawnable agents are the seven we wrote --
# implementer plus auditor / log-pathologist / plan-navigator / mesh-probe /
# example-runner / record-reconciler. Rationale: the 08-31 21:00 slot found
# `example-runner` unreachable because this line blocked the tool outright,
# while daily-review.sh did not, so reviews could queue work to an executor
# no implementer could invoke. Compute safety is unaffected: the
# hooks/bash_guard.py PreToolUse rank-ceiling and harness-routing rules were
# verified 2026-08-31 to fire inside subagent sessions (denial reproduced on
# `mpiexec -n 16`), and subagents inherit acceptEdits plus settings.json.
# NOTE: if a future Claude Code release adds a built-in agent type, add it to
# this deny list -- the scoping enumerates what is forbidden, not what is
# allowed.
timeout --kill-after=120 3900 "$CLAUDE_BIN" \
  --model claude-opus-5 \
  --effort medium \
  --permission-mode acceptEdits \
  --disallowedTools WebFetch WebSearch \
    "Agent(general-purpose)" "Agent(Explore)" "Agent(Plan)" \
    "Agent(claude)" "Agent(claude-code-guide)" "Agent(statusline-setup)" \
  -p "Scheduled implementer run, started ${START}. You have 60 minutes of wall clock (externally enforced at 65); start no new implementation work after minute 45. Read docs/automation/implementer-run.md and execute it exactly." \
  >> "$LOG" 2>&1
STATUS=$?

echo "$(date -u) exit=${STATUS}" >> "$LOG"
exit "$STATUS"
