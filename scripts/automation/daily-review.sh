#!/usr/bin/env bash
# Scheduled daily plan review (high effort since 2026-09-15, operator directive; was medium). Installed in crontab; see
# docs/automation/daily-review.md for the protocol the session follows.
set -euo pipefail

# REPO / LOCK / CLAUDE_BIN are overridable so scripts/testing/test_launcher_status.sh
# can drive this launcher against a stub CLI in a scratch root; cron sets none.
REPO="${FEM_EM_REPO:-/home/taz5297/Development/fem-em-solver}"
LOCK="${FEM_EM_AUTOMATION_LOCK:-$HOME/.fem-em-automation.lock}"
LOGDIR="$REPO/logs/automation"
CLAUDE_BIN="${FEM_EM_CLAUDE_BIN:-$HOME/.local/bin/claude}"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

mkdir -p "$LOGDIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$LOGDIR/${TS}_daily-review.log"

# Footer on EVERY exit path. Under `set -e` a nonzero `timeout` used to end the
# script before `STATUS=$?`, so exactly the runs that needed diagnosis (timeout,
# session-limit death, CLI error) left no exit line. `exit=<n>` stays the token
# checkin.sh greps; outcome= says which path wrote it.
OUTCOME="launcher-error"
trap 'rc=$?; echo "$(date -u) outcome=${OUTCOME} exit=${rc}" >> "$LOG"' EXIT

# One automation session at a time on this shared box, ever.
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u) another automation run holds the lock; skipping" >> "$LOG"
  OUTCOME="skipped-lock"
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
  # An override scoped to the other review (REVIEW_MODEL_OVERRIDE_SCOPE) is
  # ignored here; an empty scope means both reviews.
  if [[ -n "${REVIEW_MODEL_OVERRIDE_SCOPE:-}" && "$REVIEW_MODEL_OVERRIDE_SCOPE" != "daily" ]]; then
    echo "$(date -u) review-model override scoped to ${REVIEW_MODEL_OVERRIDE_SCOPE}, not daily; ignored" >> "$LOG"
  elif [[ -n "${REVIEW_MODEL_OVERRIDE:-}" && -n "${REVIEW_MODEL_OVERRIDE_UNTIL:-}" ]]; then
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
STATUS=0
timeout --kill-after=120 2700 "$CLAUDE_BIN" \
  --model "$REVIEW_MODEL" \
  --effort high \
  --permission-mode acceptEdits \
  --disallowedTools WebFetch WebSearch \
  -p "Scheduled daily review session, started ${START}. Read docs/automation/daily-review.md and execute it exactly. Documentation work only: no solves, no meshing." \
  >> "$LOG" 2>&1 || STATUS=$?

# 124 = timeout sent TERM at the cap, 137 = the --kill-after KILL landed.
case "$STATUS" in
  0)       OUTCOME="ok" ;;
  124|137) OUTCOME="timeout" ;;
  *)       OUTCOME="session-failed" ;;
esac
exit "$STATUS"
