#!/usr/bin/env bash
# Scheduled weekly planning review (Fable 5, high effort). Installed in crontab;
# see docs/automation/weekly-review.md for the protocol the session follows.
set -euo pipefail

REPO="/home/taz5297/Development/fem-em-solver"
LOCK="$HOME/.fem-em-automation.lock"
LOGDIR="$REPO/logs/automation"
CLAUDE_BIN="$HOME/.local/bin/claude"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

mkdir -p "$LOGDIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$LOGDIR/${TS}_weekly-review.log"

# One automation session at a time on this shared box, ever.
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u) another automation run holds the lock; skipping" >> "$LOG"
  exit 0
fi

cd "$REPO"
START="$(date '+%Y-%m-%d %H:%M %Z')"

# 60 min wall-clock cap in the Sunday 02:15 buffer slot (moved from 01:30
# on 2026-08-16: the plan's usage window resets at 02:00 local, and the old
# slot starved whenever late-Saturday work drained it); the 03:00 daily
# review shares the flock, so an overrun makes it skip rather than collide.
# High effort: this is the long-horizon judgement session (phase planning,
# pace extrapolation, benchmark adjudication) and runs once a week.
# Documentation-only, so subagents spend tokens, not cores.
timeout --kill-after=120 3600 "$CLAUDE_BIN" \
  --model claude-fable-5 \
  --effort high \
  --permission-mode acceptEdits \
  --disallowedTools WebFetch WebSearch \
  -p "Scheduled weekly planning review session, started ${START}. Read docs/automation/weekly-review.md and execute it exactly. Documentation work only: no solves, no meshing." \
  >> "$LOG" 2>&1
STATUS=$?

echo "$(date -u) exit=${STATUS}" >> "$LOG"
exit "$STATUS"
