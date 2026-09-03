#!/usr/bin/env bash
# Scheduled weekly housekeeping sweep. Installed in crontab (Sunday 01:45
# local, in the buffer before the 02:15 weekly review); implements
# docs/testing/retention-policy.md §4. No Claude session: the sweep is fully
# mechanical (scripts/maintenance/housekeeping.py --apply) and anything it can
# only flag — orphan probes, over-budget journals — lands in
# docs/testing/housekeeping.md for the next daily review to read.
set -euo pipefail

REPO="/home/taz5297/Development/fem-em-solver"
LOCK="${FEM_EM_AUTOMATION_LOCK:-$HOME/.fem-em-automation.lock}"
LOGDIR="$REPO/logs/automation"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

mkdir -p "$LOGDIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$LOGDIR/${TS}_housekeeping.log"

# One automation session at a time on this shared box, ever.
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u) another automation run holds the lock; skipping" >> "$LOG"
  exit 0
fi

cd "$REPO"

# Same preflight as the implementer run: never sweep on a dirty tree or off
# main — a parked attempt or a half-written review must not be swept into a
# housekeeping commit.
if [[ -n "$(git status --porcelain)" ]]; then
  echo "$(date -u) tree is dirty; skipping sweep" >> "$LOG"
  git status --short >> "$LOG"
  exit 0
fi
if [[ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]]; then
  echo "$(date -u) not on main; skipping sweep" >> "$LOG"
  exit 0
fi

DATE="$(date -u +%Y-%m-%d)"
{
  echo "# housekeeping sweep ${DATE}"
  timeout --kill-after=60 900 python3 scripts/maintenance/housekeeping.py --apply
} >> "$LOG" 2>&1
STATUS=$?

if git diff --cached --quiet; then
  echo "$(date -u) nothing to commit (exit=${STATUS})" >> "$LOG"
  exit "$STATUS"
fi

git -c user.name="fem-em housekeeping" -c user.email="housekeeping@localhost" \
  commit -q -m "chore(housekeeping): weekly sweep ${DATE}

Automated run of scripts/maintenance/housekeeping.py --apply under
docs/testing/retention-policy.md. Deleted logs stay indexed in
docs/testing/test-results.md and are recoverable from git history." \
  >> "$LOG" 2>&1

echo "$(date -u) exit=${STATUS} commit=$(git rev-parse --short HEAD)" >> "$LOG"
exit "$STATUS"
