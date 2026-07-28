#!/usr/bin/env bash
# Scheduled implementer run (Opus). Installed in crontab; see
# docs/automation/implementer-run.md for the protocol the session follows.
set -euo pipefail

REPO="/home/taz5297/Development/fem-em-solver"
LOCK="$HOME/.fem-em-automation.lock"
LOGDIR="$HOME/fem-em-automation/logs"
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
# auto-approves file edits inside the repo only. Web and subagent tools are off.
timeout --kill-after=120 3900 "$CLAUDE_BIN" \
  --model claude-opus-5 \
  --permission-mode acceptEdits \
  --disallowedTools WebFetch WebSearch Task Agent \
  -p "Scheduled implementer run, started ${START}. You have 60 minutes of wall clock (externally enforced at 65); start no new implementation work after minute 45. Read docs/automation/implementer-run.md and execute it exactly." \
  >> "$LOG" 2>&1
STATUS=$?

echo "$(date -u) exit=${STATUS}" >> "$LOG"
exit "$STATUS"
