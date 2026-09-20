#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/testing/run_and_log.sh <chunk_id> <command...>
#   scripts/testing/run_and_log.sh --dry-run <chunk_id> <command...>
#   FEM_SOLVER_DRY_RUN=1 scripts/testing/run_and_log.sh <chunk_id> <command...>
#   scripts/testing/run_and_log.sh --capture-orphan <chunk_id> <logs/<name>-raw.log>
# Example:
#   scripts/testing/run_and_log.sh A1 "docker compose exec fem-em-solver bash -lc 'cd /workspace && PYTHONPATH=/workspace/src mpiexec -n 2 python3 examples/magnetostatics/01_straight_wire.py'"
#
# Exit status: the wrapped command's own status, except
#   2   usage error
#   75  ORPHAN_REFUSAL (OPS-43 (b)): CMD is a `docker compose … exec` and the
#       target service (fem-em-solver-xxl / -xl if named, else fem-em-solver) already
#       runs a process matching mpiexec|hydra_pmi_proxy|pytest. The PIDs,
#       elapsed seconds and args are printed on stderr; no log file, no
#       test-results row and no XL ledger row is written. Kill the survivors
#       (PROJECT_PLAN §5.1 "check for orphaned ranks") and re-run. A host-only
#       CMD, and a dry run, skip the check. If the process listing itself
#       cannot be taken (service down), the check warns and proceeds: the
#       wrapped command then fails visibly in its own log.
#   rc  (OPS-45) the command exited 0 but the final non-blank line of its
#       output is `[capture] rc=<rc>` with rc != 0: Status, the row's Exit and
#       the harness exit are rc (exit 1 if rc > 255), and `## Exit` carries a
#       `Capture note:`. Guards a durable-capture command missing `exit $rc`.
#   76  NO_RC_CAPTURE (OPS-43 (a)): --capture-orphan found no `[capture] rc=`
#       line in the raw file. The log is still written, with
#       `Status: unknown (no rc line)`, and one row is appended with Exit
#       `unknown`. A capture that cannot see the status never claims success.
#
# Durable capture (OPS-43 (a), PROJECT_PLAN §5.1). A window that may outlive
# its wrapper (anything over ~10 minutes) writes its container-side output AND
# its exit status to a raw file under the gitignored /logs/, then echoes it:
#
#   scripts/testing/run_and_log.sh <ID> "docker compose exec -T fem-em-solver \
#     bash -lc 'cd /workspace && PYTHONPATH=/workspace/src timeout -k 30 <T> \
#     mpiexec -n 2 python3 -m pytest <paths> -v -s --tb=short \
#     > /workspace/logs/<name>-raw.log 2>&1; rc=\$?; \
#     echo \"[capture] rc=\$rc\" >> /workspace/logs/<name>-raw.log; \
#     cat /workspace/logs/<name>-raw.log; exit \$rc'"
#
# (Escape `$` and the inner double quotes as shown when the outer quotes are
# double quotes on the calling shell; the container-side part stays in single
# quotes.) The rc line lands in the raw file before the echo, so a wrapper
# killed mid-window (the container command keeps running: `docker compose
# exec -T` does not propagate the client's death) still leaves the status on
# disk. Once the container command has finished (check `ps` in the service),
# turn the raw file into a footered harness log:
#
#   scripts/testing/run_and_log.sh --capture-orphan <ID> logs/<name>-raw.log
#
# It writes the normal header (naming the mode and the raw path), the raw
# contents as `## Output` through the retention filter below, and `## Exit`
# with `Status:` from the LAST `[capture] rc=` line; it appends one
# test-results row and exits with that status (76 above when there is none).
# The raw path may be host-relative (to the cwd, else the repo root), absolute,
# or the container's /workspace/... form. The killed wrapper's own log has no
# `## Exit`; leave it, the recovered log is the one to cite.

DRY_RUN="${FEM_SOLVER_DRY_RUN:-0}"
CAPTURE_MODE=0
NO_RC_CAPTURE=76
RAW_FILE=""

if [[ "${1:-}" == "--capture-orphan" ]]; then
  if [[ $# -ne 3 ]]; then
    echo "Usage: $0 --capture-orphan <chunk_id> <logs/<name>-raw.log>"
    exit 2
  fi
  CAPTURE_MODE=1
  RAW_ARG="$3"
  set -- "$2" "--capture-orphan $3"
fi

if [[ "$CAPTURE_MODE" == 0 && "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 [--dry-run] <chunk_id> <command...>"
  echo "       FEM_SOLVER_DRY_RUN=1 $0 <chunk_id> <command...>"
  exit 2
fi

CHUNK_ID="$1"
shift
CMD="$*"

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/docs/testing/logs"
INDEX_FILE="$ROOT_DIR/docs/testing/test-results.md"
mkdir -p "$LOG_DIR"

# Service routing, resolved ONCE and reused by the orphan check and the ledger
# block below. They used to match CMD separately, and the orphan check had no
# xxl branch: "fem-em-solver-xl" is not a substring of "fem-em-solver-xxl", so
# an XXL command had its orphan check run against the ordinary service
# (2026-09-19). xxl is tested first so a rename cannot silently file an xxl
# run under xl. TARGET_TIER is empty for the ordinary service.
TARGET_SERVICE="fem-em-solver"
TARGET_TIER=""
if [[ "$CMD" == *fem-em-solver-xxl* ]]; then
  TARGET_SERVICE="fem-em-solver-xxl"; TARGET_TIER="xxl"
elif [[ "$CMD" == *fem-em-solver-xl* ]]; then
  TARGET_SERVICE="fem-em-solver-xl"; TARGET_TIER="xl"
fi
PROFILE_ARGS=()
XL_LEDGER=""
XL_TIER=""
if [[ -n "$TARGET_TIER" ]]; then
  PROFILE_ARGS=(--profile "$TARGET_TIER")
  XL_LEDGER="$ROOT_DIR/docs/testing/$TARGET_TIER-ledger.md"
  XL_TIER="${TARGET_TIER^^}"
fi

if [[ "$CAPTURE_MODE" == 1 ]]; then
  case "$RAW_ARG" in
    /workspace/*) RAW_FILE="$ROOT_DIR/${RAW_ARG#/workspace/}" ;;
    /*) RAW_FILE="$RAW_ARG" ;;
    *) if [[ -f "$RAW_ARG" ]]; then RAW_FILE="$(pwd)/$RAW_ARG"; else RAW_FILE="$ROOT_DIR/$RAW_ARG"; fi ;;
  esac
  if [[ ! -f "$RAW_FILE" ]]; then
    echo "[harness] --capture-orphan: raw file not found: $RAW_ARG (resolved to $RAW_FILE)" >&2
    exit 2
  fi
fi

# Ensure docker compose can always find project config for this repo layout.
DEFAULT_COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.yml"
if [[ -z "${COMPOSE_FILE:-}" && -f "$DEFAULT_COMPOSE_FILE" ]]; then
  export COMPOSE_FILE="$DEFAULT_COMPOSE_FILE"
fi

ensure_index_file() {
  if [[ ! -f "$INDEX_FILE" ]]; then
    cat > "$INDEX_FILE" <<'EOF'
# FEM-EM Manual Test Results

This file is append-only and records test runs executed by the human operator.
Each run has a full log in `docs/testing/logs/`.

| UTC Timestamp | Chunk | Commit | Elapsed (s) | Env | Exit | Log |
|---|---|---|---:|---|---:|---|
EOF
    return
  fi

  python3 - "$INDEX_FILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
legacy_header = "| UTC Timestamp | Chunk | Exit | Log |"
legacy_sep = "|---|---|---:|---|"
new_header = "| UTC Timestamp | Chunk | Commit | Elapsed (s) | Env | Exit | Log |"
new_sep = "|---|---|---|---:|---|---:|---|"

if new_header in text:
    sys.exit(0)

if legacy_header not in text:
    sys.exit(0)

lines = text.splitlines()
out = []
i = 0
while i < len(lines):
    line = lines[i]
    if line == legacy_header:
        out.append(new_header)
        if i + 1 < len(lines) and lines[i + 1] == legacy_sep:
            out.append(new_sep)
            i += 2
        else:
            out.append(new_sep)
            i += 1
        while i < len(lines):
            row = lines[i]
            if not row.startswith("|"):
                out.append(row)
                i += 1
                continue
            parts = [p.strip() for p in row.strip().split("|")[1:-1]]
            if len(parts) == 4:
                utc_ts, chunk, exit_code, log_ref = parts
                out.append(f"| {utc_ts} | {chunk} | `unknown` | unknown | `legacy` | {exit_code} | {log_ref} |")
            else:
                out.append(row)
            i += 1
        break
    out.append(line)
    i += 1

path.write_text("\n".join(out) + "\n")
PY
}

TS="$(date -u +%Y%m%dT%H%M%SZ)"
SAFE_CHUNK="${CHUNK_ID//[^a-zA-Z0-9._-]/_}"
LOG_FILE="$LOG_DIR/${TS}_${SAFE_CHUNK}.log"

GIT_COMMIT_FULL="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
DOCKER_COMPOSE_VERSION="$(docker compose version 2>/dev/null | head -n 1 || echo unavailable)"
OS_META="$(uname -srm 2>/dev/null || echo unknown)"
PYTHON_META="$(python3 --version 2>/dev/null || echo unavailable)"
HOST_META="$(hostname 2>/dev/null || echo unknown)"
COMPOSE_META="${COMPOSE_FILE:-<unset>}"
ENV_META="host=${HOST_META};os=${OS_META};python=${PYTHON_META};compose=$(basename "$COMPOSE_META")"
ENV_META="${ENV_META//|//}"

# Dry-run mode: just print what would be executed, don't run anything
if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY RUN] Would execute test for chunk: $CHUNK_ID"
  echo "[DRY RUN] Command: $CMD"
  echo "[DRY RUN] Commit: $GIT_COMMIT_FULL"
  echo "[DRY RUN] Env: $ENV_META"
  echo "[DRY RUN] Log would be written to: $LOG_FILE"
  echo "[DRY RUN] Routing: service=$TARGET_SERVICE profile=${TARGET_TIER:-<none>} ledger=${XL_LEDGER:+$(basename "$XL_LEDGER")}"
  echo ""
  echo "To actually run this test, execute:"
  echo "  $0 $CHUNK_ID \"$CMD\""
  exit 0
fi

# Orphan-rank refusal (OPS-43 (b), PROJECT_PLAN §5.1): a killed wrapper leaves
# its container-side ranks running (2026-09-09: eight ranks on 260 GiB with no
# consumer). Refuse to double-book the service on top of them. Runs before the
# log header and before the XL ledger row, so a refusal writes nothing.
ORPHAN_REFUSAL=75
ORPHAN_PATTERN='mpiexec|hydra_pmi_proxy|pytest'
COMPOSE_EXEC_RE='docker[[:space:]]+compose[^;&|]*[[:space:]]exec([[:space:]]|$)'
if [[ "$CAPTURE_MODE" == 0 && "$CMD" =~ $COMPOSE_EXEC_RE ]]; then
  set +e
  PS_TABLE="$(cd "$ROOT_DIR" && docker compose ${PROFILE_ARGS[@]+"${PROFILE_ARGS[@]}"} exec -T "$TARGET_SERVICE" ps -eo pid,etimes,args </dev/null 2>&1)"
  PS_STATUS=$?
  set -e
  if [[ "$PS_STATUS" -ne 0 ]]; then
    echo "[harness] orphan check skipped: could not list processes in $TARGET_SERVICE (status $PS_STATUS): $PS_TABLE" >&2
  else
    OFFENDERS=""
    while IFS= read -r line; do
      read -r pid etimes args <<<"$line"
      [[ "$pid" =~ ^[0-9]+$ ]] || continue          # header
      [[ "$args" == "ps -eo pid,etimes,args" ]] && continue  # the listing itself
      if [[ "$args" =~ $ORPHAN_PATTERN ]]; then
        OFFENDERS+="  pid=$pid elapsed_s=$etimes args=$args"$'\n'
      fi
    done <<<"$PS_TABLE"
    if [[ -n "$OFFENDERS" ]]; then
      {
        echo "[harness] REFUSED (exit $ORPHAN_REFUSAL): live ranks in service $TARGET_SERVICE"
        printf '%s' "$OFFENDERS"
        echo "[harness] kill them (PROJECT_PLAN §5.1) and re-run; nothing was logged."
      } >&2
      exit "$ORPHAN_REFUSAL"
    fi
  fi
fi

START_EPOCH="$(date -u +%s)"

{
  echo "# Test Run"
  echo "- Chunk: $CHUNK_ID"
  echo "- Commit: $GIT_COMMIT_FULL"
  echo "- Time (UTC): $(date -u '+%Y-%m-%d %H:%M:%S')"
  echo "- Host: $HOST_META"
  echo "- OS: $OS_META"
  echo "- Python: $PYTHON_META"
  echo "- Docker Compose: $DOCKER_COMPOSE_VERSION"
  echo "- Root Dir: $ROOT_DIR"
  echo "- Working Dir: $(pwd)"
  echo "- COMPOSE_FILE: $COMPOSE_META"
  echo "- Command: $CMD"
  if [[ "$CAPTURE_MODE" == 1 ]]; then
    echo "- Mode: capture-orphan (OPS-43 (a)): output recovered from a raw file, nothing executed"
    echo "- Raw file: $RAW_FILE"
    echo "- Raw file mtime (UTC): $(date -u -r "$RAW_FILE" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo unknown)"
  fi
  echo ""
  echo "## Preflight"
  echo '\$ pwd'
  pwd
  echo ""
  echo '\$ ls -la docker'
  ls -la "$ROOT_DIR/docker" 2>&1 || true
  echo ""
  echo '\$ docker compose version'
  docker compose version 2>&1 || true
  echo ""
  echo '\$ docker compose config --services'
  docker compose config --services 2>&1 || true
  echo ""
  echo "## Output"
} > "$LOG_FILE"

# XL tier (PROJECT_PLAN §5.1, operator directive 2026-09-05): a command against
# the fem-em-solver-xl service consumes the weekly slot the moment it starts, so
# the ledger row is appended BEFORE the run (a killed run still spent the box);
# the bash guard reads this table. Ranks/cells/memory/readout are filled by hand.
# Two big-compute tiers, each with its own ledger (operator directive
# 2026-09-10); which one is the routing resolved at the top of this script.
IS_XL=0
if [[ "$CAPTURE_MODE" == 0 && -n "$TARGET_TIER" && -f "$XL_LEDGER" ]]; then
  IS_XL=1
  printf '| %s | %s | `%s` | | | | | |\n' \
    "$(date -u '+%Y-%m-%d')" "$CHUNK_ID" "$(basename "$LOG_FILE")" >> "$XL_LEDGER"
  echo "[harness] ${XL_TIER} slot consumed: row appended to $(basename "$XL_LEDGER")" >> "$LOG_FILE"
fi

set +e
if [[ "$CAPTURE_MODE" == 1 ]]; then
  echo "[harness] capture-orphan: contents of $RAW_FILE follow" >> "$LOG_FILE"
  cat "$RAW_FILE" >> "$LOG_FILE"
  [[ -n "$(tail -c 1 "$RAW_FILE")" ]] && echo "" >> "$LOG_FILE"
  # last rc line wins; tolerate a partial preceding line (no trailing newline)
  RC_LINE="$(grep -oE '\[capture\] rc=[0-9]+[[:space:]]*$' "$RAW_FILE" | tail -n 1)"
  if [[ -n "$RC_LINE" ]]; then
    STATUS="${RC_LINE#*rc=}"
    STATUS="${STATUS//[[:space:]]/}"
    STATUS_TEXT="$STATUS"
    ROW_EXIT="$STATUS"
    EXIT_CODE="$STATUS"
  else
    STATUS_TEXT="unknown (no rc line)"
    ROW_EXIT="unknown"
    EXIT_CODE="$NO_RC_CAPTURE"
  fi
else
  (
    cd "$ROOT_DIR"
    set -x
    bash -lc "$CMD"
  ) >> "$LOG_FILE" 2>&1
  STATUS=$?
  STATUS_TEXT="$STATUS"
  ROW_EXIT="$STATUS"
  EXIT_CODE="$STATUS"
  # OPS-45: a durable-capture command that drops its trailing `exit $rc` exits
  # with `cat`'s 0 over a failed window (WF-6 step 4h, 2026-09-11). If the
  # command exited 0 and its FINAL non-blank output line is a non-zero
  # `[capture] rc=` line, that line is the status. A non-zero command exit is
  # never overwritten, and an rc line followed by further output is ignored.
  if [[ "$STATUS" -eq 0 ]]; then
    LAST_LINE="$(grep -v '^[[:space:]]*$' "$LOG_FILE" | tail -n 1)"
    if [[ "$LAST_LINE" =~ ^\[capture\]\ rc=([0-9]+)[[:space:]]*$ ]] && (( 10#${BASH_REMATCH[1]} != 0 )); then
      CAPTURE_RC=$((10#${BASH_REMATCH[1]}))
      STATUS_TEXT="$CAPTURE_RC"
      ROW_EXIT="$CAPTURE_RC"
      EXIT_CODE=$(( CAPTURE_RC > 255 ? 1 : CAPTURE_RC ))
      CAPTURE_RC_NOTE="command exited 0 but its output's final [capture] rc= line reads $CAPTURE_RC; Status is the rc line"
    fi
  fi
fi
set -e

END_EPOCH="$(date -u +%s)"
ELAPSED_SECONDS=$((END_EPOCH - START_EPOCH))

# Retention-policy filter (docs/testing/retention-policy.md §2): collapse runs
# of gmsh mesh-optimisation progress lines to a single count line. Nothing else
# is touched. FEM_LOG_FILTER=0 disables it for a run whose raw mesher chatter is
# the object of study. Failure of the filter never fails the run.
ELIDED_LINES=0
if [[ "${FEM_LOG_FILTER:-1}" != "0" ]]; then
  ELIDED_LINES="$(python3 - "$LOG_FILE" <<'PY' || echo 0
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
chatter = re.compile(
    r"^Info\s+:\s+("
    r"ImproveMesh|SwapImprove\d*|SplitImprove|CombineImprove|"
    r"\d+ swaps performed|\d+ splits performed|\d+ edges? (?:swapped|split)|"
    r"Total badness = |[\d.eE+-]+ < quality < [\d.eE+-]+|"
    r"Optimizing (?:mesh|volume|surface)|Optimization starts|"
    r"Untangling|Smoothing|Volume optimization"
    r")"
)
out = []
run = 0
elided = 0

def flush():
    global run
    if run:
        out.append(f"[harness] {run} gmsh optimisation lines elided "
                   "(docs/testing/retention-policy.md §2; FEM_LOG_FILTER=0 keeps them)\n")
    run = 0

with path.open("r", encoding="utf-8", errors="surrogateescape") as fh:
    for line in fh:
        if chatter.match(line):
            run += 1
            elided += 1
            continue
        flush()
        out.append(line)
flush()
if elided:
    path.write_text("".join(out), encoding="utf-8", errors="surrogateescape")
print(elided)
PY
)"
fi

{
  echo ""
  echo "## Exit"
  echo "- Status: $STATUS_TEXT"
  echo "- Elapsed (s): $ELAPSED_SECONDS"
  echo "- Filtered lines (gmsh optimisation chatter): ${ELIDED_LINES:-0}"
  if [[ "$CAPTURE_MODE" == 1 ]]; then
    echo "- Capture note: Elapsed is this capture call's own time, not the window's; Status is the raw file's last [capture] rc= line"
  elif [[ -n "${CAPTURE_RC_NOTE:-}" ]]; then
    echo "- Capture note: $CAPTURE_RC_NOTE"
  fi
} >> "$LOG_FILE"

if [[ "$IS_XL" == 1 ]]; then
  # fill the elapsed column of the row appended above (last row naming this log)
  python3 - "$XL_LEDGER" "$(basename "$LOG_FILE")" "$ELAPSED_SECONDS" <<'PY' || true
import sys
from pathlib import Path
path, log, elapsed = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
lines = path.read_text().splitlines(keepends=True)
for i in range(len(lines) - 1, -1, -1):
    if log in lines[i]:
        cells = lines[i].rstrip("\n").split("|")
        if len(cells) >= 9:
            cells[7] = f" {elapsed} "
            lines[i] = "|".join(cells) + "\n"
        break
path.write_text("".join(lines))
PY
fi

ensure_index_file
printf '| %s | %s | `%s` | %s | `%s` | %s | `%s` |\n' \
  "$(date -u '+%Y-%m-%d %H:%M:%S')" \
  "$CHUNK_ID" \
  "$GIT_COMMIT_FULL" \
  "$ELAPSED_SECONDS" \
  "$ENV_META" \
  "$ROW_EXIT" \
  "$(basename "$LOG_FILE")" >> "$INDEX_FILE"

echo "Log written: $LOG_FILE"
echo "Index updated: $INDEX_FILE"
exit "$EXIT_CODE"
