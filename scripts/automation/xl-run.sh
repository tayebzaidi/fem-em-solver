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
# can hold a 2 h (since 2026-09-13, 4 h) window. A plain cron script has neither limit. That is the
# whole reason this file exists.
#
# What runs is the lexically first `*.env` file in docs/testing/<tier>-queue.d/
# (operator directive 2026-09-15: a multi-entry FIFO, so the daily review can
# queue every READY entry of docs/testing/xl-pending.md at once and the
# Tuesday / Thursday windows — nights with no review to refill a one-slot
# file — are no longer lost). The legacy one-slot docs/testing/<tier>-queue.env
# is still honoured, first, when non-empty. Empty queue means nothing runs and
# this exits quietly — so the entry can sit in cron every night and cost
# nothing. The launcher checks the tier's ledger budget BEFORE taking an
# entry, so a spent budget leaves the queue intact for the night it reopens.
set -uo pipefail

# Which tier this invocation runs. `xl` = 2 h / 512 GiB / 3 per week (Sun-Fri
# 02:00); `xxl` = 8 h / 754 GiB / 1 per week (Saturday 02:00). Operator
# directive 2026-09-10. Each tier has its own queue file, its own ledger and
# its own compose service; the guard enforces the ceilings and the budget.
TIER="${1:-xl}"
case "$TIER" in
  xl)  SERVICE="fem-em-solver-xl"  ;;
  xxl) SERVICE="fem-em-solver-xxl" ;;
  *)   echo "usage: xl-run.sh [xl|xxl]" >&2; exit 2 ;;
esac

REPO="/home/taz5297/Development/fem-em-solver"
# Overridable because $HOME is read-only inside the agent sandbox; cron has a
# writable one. `housekeeping.sh` carries the same escape hatch.
LOCK="${FEM_EM_XL_LOCK:-$HOME/.fem-em-$TIER.lock}"   # its own lock, NOT the automation flock:
                                      # a 2 h XL window must not starve the
                                      # 02:15 weekly or the 03:00 review, both
                                      # of which are documentation-only.
LOGDIR="$REPO/logs/automation"
QUEUE="$REPO/docs/testing/$TIER-queue.env"   # legacy one-slot file; moved from scripts/automation/ 2026-09-13: Edit(scripts/automation/**) is on the ask list, so a headless daily review (the XL clerk, daily-review.md step 6b) could not write it there
QUEUE_DIR="$REPO/docs/testing/$TIER-queue.d"  # FIFO: NN-<chunk>.env files, same XL_CHUNK / XL_COMMAND format (2026-09-15)
GUARD_DIR="$REPO/scripts/automation/hooks"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

mkdir -p "$LOGDIR"
LOG="$LOGDIR/$(date -u +%Y%m%dT%H%M%SZ)_${TIER}-run.log"
exec >>"$LOG" 2>&1
echo "$(date -u) xl-run starting: tier=$TIER service=$SERVICE"

# Distinguish "cannot create the lock" from "another window holds it". They had
# the same message and the same exit 0, so an unwritable lock path looked
# exactly like a healthy skip — which is how a failed launch would hide.
if ! exec 9>"$LOCK" 2>/dev/null; then
  echo "$(date -u) FAILED: cannot open lock file $LOCK (set FEM_EM_XL_LOCK to a writable path)"
  exit 1
fi
if ! flock -n 9; then
  echo "$(date -u) another $TIER window holds the lock; skipping"
  exit 0
fi

# Pick the entry: the legacy one-slot file if it is non-empty, else the first
# file in the FIFO directory. ENTRY is what gets consumed afterwards.
ENTRY=""
XL_CHUNK=""; XL_COMMAND=""
if [[ -f "$QUEUE" ]]; then
  # shellcheck source=/dev/null
  source "$QUEUE" || true
  [[ -n "${XL_CHUNK:-}" && -n "${XL_COMMAND:-}" ]] && ENTRY="$QUEUE"
fi
if [[ -z "$ENTRY" && -d "$QUEUE_DIR" ]]; then
  for f in "$QUEUE_DIR"/*.env; do
    [[ -f "$f" ]] || continue
    XL_CHUNK=""; XL_COMMAND=""
    # shellcheck source=/dev/null
    source "$f" || true
    if [[ -n "${XL_CHUNK:-}" && -n "${XL_COMMAND:-}" ]]; then ENTRY="$f"; break; fi
    echo "$(date -u) skipping malformed queue entry $(basename "$f") (XL_CHUNK/XL_COMMAND unset)"
  done
fi
CHUNK="${XL_CHUNK:-}"
CMD="${XL_COMMAND:-}"
if [[ -z "$ENTRY" ]]; then
  echo "$(date -u) queue empty; nothing to run"
  exit 0
fi
QUEUED_AHEAD=$(( $(ls "$QUEUE_DIR"/*.env 2>/dev/null | wc -l) ))
echo "$(date -u) queue entry $(basename "$ENTRY") -> chunk $CHUNK ($QUEUED_AHEAD file(s) in $(basename "$QUEUE_DIR"))"

# Budget preflight (same arithmetic as bash_guard.py: charged rows in the
# trailing 7 days of the tier's ledger). A spent budget must NOT consume the
# entry — the guard inside run_and_log.sh would refuse the command anyway,
# and clearing the queue on a refusal is how a window gets silently lost.
USED="$(cd "$GUARD_DIR" && python3 -c "import bash_guard as g; t=g.TIERS['$TIER']; print(g.runs_in_trailing_week(t['ledger']), t['per_week'])" 2>/dev/null)"
if [[ -n "$USED" ]]; then
  set -- $USED
  if [[ "$1" -ge "$2" ]]; then
    echo "$(date -u) $TIER budget spent ($1 of $2 charged rows in the trailing 7 days); entry left in the queue for the night it reopens"
    exit 0
  fi
  echo "$(date -u) $TIER budget: $1 of $2 used in the trailing 7 days"
else
  echo "$(date -u) WARNING: could not read the $TIER budget from bash_guard.py; relying on the harness guard"
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

# Environment preflight, BEFORE anything that consumes the slot. The harness
# appends the ledger row the moment the window starts, so a failure after that
# point spends the week for nothing. Measured 2026-09-10: run by hand from an
# agent session, docker was permission-denied from inside this script (it works
# from a direct agent command, not from a script), the window died in 0 s, and
# it had already taken a ledger row and cleared the queue. Cron is outside that
# sandbox and unaffected — but the check is cheap and the failure was silent.
if ! docker compose -f docker/docker-compose.yml ps >/dev/null 2>&1; then
  echo "$(date -u) FAILED: docker unreachable from this context; queue and ledger untouched"
  exit 1
fi

# §5.1: restart the service immediately before the window so the container's
# `memory.peak` belongs to this run — it is per container lifetime and cannot
# be reset on this kernel.
docker compose -f docker/docker-compose.yml --profile "$TIER" up -d --force-recreate "$SERVICE"
sleep 5

echo "$(date -u) running $TIER chunk $CHUNK"
# The box is quiet by schedule, so the guard's interactive box-confirmation is
# satisfied here by the clock rather than by a human at 02:00.
FEM_EM_XL_BOX_OK=1 scripts/testing/run_and_log.sh "$CHUNK" "$CMD"
STATUS=$?
echo "$(date -u) run_and_log exit=$STATUS"

docker compose -f docker/docker-compose.yml --profile "$TIER" stop "$SERVICE"

# Consume the queue entry either way: a failed XL window has still spent its
# slot (§5.1), and re-running it unattended tomorrow is exactly what the
# once-per-interval rule exists to prevent. Re-queue deliberately or not at all.
if [[ "$ENTRY" == "$QUEUE" ]]; then
  : > "$QUEUE"
  echo "$(date -u) legacy queue file cleared"
else
  git rm -q --cached "$ENTRY" 2>/dev/null || true
  rm -f "$ENTRY"
  echo "$(date -u) queue entry $(basename "$ENTRY") consumed; $(ls "$QUEUE_DIR"/*.env 2>/dev/null | wc -l) left"
fi

git add -A
if git diff --cached --quiet; then
  echo "$(date -u) nothing to commit"
else
  git -c user.name="fem-em xl-run" -c user.email="xl-run@localhost" commit -q -m "chore($TIER): scheduled $TIER window — $CHUNK $(date -u +%Y-%m-%d)

Ran by scripts/automation/xl-run.sh $TIER at the 02:00 slot. Harness log, ledger row
and test-results row are in this commit; the readout still needs a human or a
review to interpret it, and the ledger's last four columns are filled by hand."
  echo "$(date -u) committed $(git rev-parse --short HEAD)"
fi
exit "$STATUS"
