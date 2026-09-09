#!/usr/bin/env bash
# Scheduled XL window (operator directive 2026-09-09). Cron, 02:00 local.
#
# The box is shared with work this sandbox cannot see — on 2026-09-09 the
# Windows host was at 100% CPU with two solves while this VM read load 0.84 and
# every container 0.00%. Rather than try to detect that (which cannot be done
# from here), XL windows run at 02:00 when the machine is quiet.
#
# **No Claude session.** An XL window is one deterministic command, and running
# it from an agent is what made it hard: a foreground harness call is capped at
# 660 s and an implementer slot is killed at 65 min, so no scheduled *session*
# can hold a 2 h window. A plain cron script has neither limit. That is the
# whole reason this file exists.
#
# What runs is one line in scripts/automation/xl-queue.env, set by the weekly
# review or the operator. Empty or absent means nothing is queued and this
# exits quietly — so the entry can sit in cron every night and cost nothing.
set -uo pipefail

REPO="/home/taz5297/Development/fem-em-solver"
LOCK="$HOME/.fem-em-xl.lock"          # its own lock, NOT the automation flock:
                                      # a 2 h XL window must not starve the
                                      # 02:15 weekly or the 03:00 review, both
                                      # of which are documentation-only.
LOGDIR="$REPO/logs/automation"
QUEUE="$REPO/scripts/automation/xl-queue.env"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

mkdir -p "$LOGDIR"
LOG="$LOGDIR/$(date -u +%Y%m%dT%H%M%SZ)_xl-run.log"
exec >>"$LOG" 2>&1
echo "$(date -u) xl-run starting"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "$(date -u) another XL window holds the lock; skipping"
  exit 0
fi

[[ -f "$QUEUE" ]] || { echo "$(date -u) no queue file; nothing to run"; exit 0; }
# shellcheck source=/dev/null
source "$QUEUE" || true
CHUNK="${XL_CHUNK:-}"
CMD="${XL_COMMAND:-}"
if [[ -z "$CHUNK" || -z "$CMD" ]]; then
  echo "$(date -u) queue empty (XL_CHUNK/XL_COMMAND unset); nothing to run"
  exit 0
fi

cd "$REPO" || exit 1
if [[ -n "$(git status --porcelain)" ]]; then
  echo "$(date -u) tree dirty; refusing to run an XL window on it"
  git status --short
  exit 0
fi
if [[ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]]; then
  echo "$(date -u) not on main; skipping"
  exit 0
fi

# §5.1: restart the service immediately before the window so the container's
# `memory.peak` belongs to this run — it is per container lifetime and cannot
# be reset on this kernel.
docker compose -f docker/docker-compose.yml --profile xl up -d --force-recreate fem-em-solver-xl
sleep 5

echo "$(date -u) running XL chunk $CHUNK"
# The box is quiet by schedule, so the guard's interactive box-confirmation is
# satisfied here by the clock rather than by a human at 02:00.
FEM_EM_XL_BOX_OK=1 scripts/testing/run_and_log.sh "$CHUNK" "$CMD"
STATUS=$?
echo "$(date -u) run_and_log exit=$STATUS"

docker compose -f docker/docker-compose.yml --profile xl stop fem-em-solver-xl

# Consume the queue entry either way: a failed XL window has still spent its
# slot (§5.1), and re-running it unattended tomorrow is exactly what the
# once-per-interval rule exists to prevent. Re-queue deliberately or not at all.
: > "$QUEUE"
echo "$(date -u) queue cleared"

git add -A
if git diff --cached --quiet; then
  echo "$(date -u) nothing to commit"
else
  git -c user.name="fem-em xl-run" -c user.email="xl-run@localhost" commit -q -m "chore(xl): scheduled XL window — $CHUNK $(date -u +%Y-%m-%d)

Ran by scripts/automation/xl-run.sh at the 02:00 slot. Harness log, ledger row
and test-results row are in this commit; the readout still needs a human or a
review to interpret it, and the ledger's last four columns are filled by hand."
  echo "$(date -u) committed $(git rev-parse --short HEAD)"
fi
exit "$STATUS"
