#!/usr/bin/env bash
# Scheduled daily plan review (high effort since 2026-09-15, operator directive; was medium). Installed in crontab; see
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

# Which model the review runs on. The default is in
# scripts/automation/review-model.env, which may also carry a **dated**
# override (a borrowed model while one credit pool is empty). The override
# expires by date inside this launcher, so a swap cannot outlive its reason
# and no revert has to be remembered. A missing or malformed file is not an
# outage: the fallback below is used and the log says which model ran.
REVIEW_MODEL="claude-fable-5-1"
MODEL_ENV="$REPO/scripts/automation/review-model.env"
if [[ -f "$MODEL_ENV" ]]; then
  # shellcheck source=/dev/null
  source "$MODEL_ENV" || true
  REVIEW_MODEL="${REVIEW_MODEL_DEFAULT:-$REVIEW_MODEL}"
  if [[ -n "${REVIEW_MODEL_OVERRIDE:-}" && -n "${REVIEW_MODEL_OVERRIDE_UNTIL:-}" ]]; then
    if [[ "$(date +%Y-%m-%d)" > "$REVIEW_MODEL_OVERRIDE_UNTIL" ]]; then
      echo "$(date -u) review-model override expired ${REVIEW_MODEL_OVERRIDE_UNTIL}; using ${REVIEW_MODEL}" >> "$LOG"
    else
      REVIEW_MODEL="$REVIEW_MODEL_OVERRIDE"
      echo "$(date -u) review-model override active until ${REVIEW_MODEL_OVERRIDE_UNTIL}: ${REVIEW_MODEL} (${REVIEW_MODEL_OVERRIDE_REASON:-no reason recorded})" >> "$LOG"
    fi
  fi
fi
echo "$(date -u) model=${REVIEW_MODEL}" >> "$LOG"

# 45 min wall-clock cap. Reviews ran 7-9 min against the old 30 min ceiling;
# the headroom is for subagent fan-out (step 3 audit), and the next implementer
# slot is 90 min out, so overrunning the cap cannot collide with it.
# Permissions come from .claude/settings.json (allowlist + denies); acceptEdits
# auto-approves file edits inside the repo only. Web tools stay off; subagents
# are ON for this session -- it is documentation-only, so they spend tokens,
# not cores, and the 12-core compute budget is untouched.
timeout --kill-after=120 2700 "$CLAUDE_BIN" \
  --model "$REVIEW_MODEL" \
  --effort high \
  --permission-mode acceptEdits \
  --disallowedTools WebFetch WebSearch \
  -p "Scheduled daily review session, started ${START}. Read docs/automation/daily-review.md and execute it exactly. Documentation work only: no solves, no meshing." \
  >> "$LOG" 2>&1
STATUS=$?

echo "$(date -u) exit=${STATUS}" >> "$LOG"
exit "$STATUS"
