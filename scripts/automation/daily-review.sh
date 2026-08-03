#!/usr/bin/env bash
# Scheduled daily plan review (Fable 5, xhigh effort). Installed in crontab; see
# docs/automation/daily-review.md for the protocol the session follows.
set -euo pipefail

REPO="/home/taz5297/Development/fem-em-solver"
LOCK="$HOME/.fem-em-automation.lock"
LOGDIR="$REPO/logs/automation"
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

# 45 min wall-clock cap. Reviews ran 7-9 min against the old 30 min ceiling;
# the headroom is for subagent fan-out (step 3 audit), and the next implementer
# slot is 90 min out, so overrunning the cap cannot collide with it.
# Permissions come from .claude/settings.json (allowlist + denies); acceptEdits
# auto-approves file edits inside the repo only. Web tools stay off; subagents
# are ON for this session -- it is documentation-only, so they spend tokens,
# not cores, and the 12-core compute budget is untouched.
timeout --kill-after=120 2700 "$CLAUDE_BIN" \
  --model claude-fable-5 \
  --effort xhigh \
  --permission-mode acceptEdits \
  --disallowedTools WebFetch WebSearch \
  -p "Scheduled daily review session, started ${START}. Read docs/automation/daily-review.md and execute it exactly. Documentation work only: no solves, no meshing." \
  >> "$LOG" 2>&1
STATUS=$?

echo "$(date -u) exit=${STATUS}" >> "$LOG"
exit "$STATUS"
