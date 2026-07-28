#!/usr/bin/env bash
# Scheduled daily plan review (Fable). Installed in crontab; see
# docs/automation/daily-review.md for the protocol the session follows.
set -euo pipefail

REPO="/home/taz5297/Development/fem-em-solver"
LOCK="$HOME/.fem-em-automation.lock"
LOGDIR="$HOME/fem-em-automation/logs"
CLAUDE_BIN="$HOME/.local/bin/claude"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

mkdir -p "$LOGDIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$LOGDIR/${TS}_daily-review.log"

# One automation session at a time on this shared box, ever.
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u) another automation run holds the lock; skipping" >> "$LOG"
  exit 0
fi

cd "$REPO"
START="$(date '+%Y-%m-%d %H:%M %Z')"

# 30 min wall-clock cap; review is documentation work and should be well under.
# Permissions come from .claude/settings.json (allowlist + denies); acceptEdits
# auto-approves file edits inside the repo only. Web and subagent tools are off.
timeout --kill-after=60 1800 "$CLAUDE_BIN" \
  --model claude-fable-5 \
  --permission-mode acceptEdits \
  --disallowedTools WebFetch WebSearch Task Agent \
  -p "Scheduled daily review session, started ${START}. Read docs/automation/daily-review.md and execute it exactly. Documentation work only: no solves, no meshing." \
  >> "$LOG" 2>&1
STATUS=$?

echo "$(date -u) exit=${STATUS}" >> "$LOG"
exit "$STATUS"
