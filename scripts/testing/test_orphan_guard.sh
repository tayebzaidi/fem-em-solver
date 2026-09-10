#!/usr/bin/env bash
# OPS-43 (b) gate: run_and_log.sh refuses to start while ranks survive in the
# target service (PROJECT_PLAN §9 item 3 / §7 OPS-43 (b)). Host-side; run it
# through the harness itself:
#
#   scripts/testing/run_and_log.sh OPS-43b "timeout -k 30 120 bash scripts/testing/test_orphan_guard.sh"
#
# Asserted:
#   anchor   probe live  -> modified harness exits exactly ORPHAN_REFUSAL (75),
#                           names the probe PID, adds no test-results row and
#                           no log file;
#            probe killed -> same call exits exactly 0 and adds exactly one row.
#   scope    probe live  -> a host-only CMD is not checked (exit 0, one row).
#   control  probe live  -> the pre-change harness (HEAD's run_and_log.sh, in a
#                           scratch root under the repo, deleted afterwards)
#                           proceeds, exit 0.
#
# Disclosure: the nested harness calls this script makes append their own rows
# and logs to docs/testing/ (chunk ids OPS-43b-refuse / -hostonly / -proceed);
# the row-count assertions are deltas around each call, so they are exact
# regardless. The control's scratch index and log live only in the scratch
# root; its Exit block is echoed here before the scratch root is removed.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"
export COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.yml"
SERVICE=fem-em-solver
PROBE=hydra_pmi_proxy-orphan-probe
REFUSAL=75
INDEX="$ROOT_DIR/docs/testing/test-results.md"
LOG_DIR="$ROOT_DIR/docs/testing/logs"
SCRATCH="$ROOT_DIR/.ops43b_scratch_root"
TRIVIAL="docker compose exec -T $SERVICE true"
FAILS=0

cleanup() {
  docker compose exec -T "$SERVICE" pkill -f "$PROBE" </dev/null >/dev/null 2>&1 || true
  rm -rf "$SCRATCH"
}
trap cleanup EXIT INT TERM

check() {  # check <description> <condition-status>
  if [[ "$2" -eq 0 ]]; then echo "PASS: $1"; else echo "FAIL: $1"; FAILS=$((FAILS + 1)); fi
}
rows() { wc -l <"$INDEX"; }
logs() { find "$LOG_DIR" -maxdepth 1 -type f | wc -l; }
probe_pid() { docker compose exec -T "$SERVICE" pgrep -f "$PROBE" </dev/null 2>/dev/null | tr -d '\r'; }

echo "== container process table before anything ($SERVICE) =="
docker compose exec -T "$SERVICE" ps -eo pid,etimes,args </dev/null
PRE="$(docker compose exec -T "$SERVICE" ps -eo pid,etimes,args </dev/null | awk 'NR>1 && $3!="ps"' | grep -E 'mpiexec|hydra_pmi_proxy|pytest' || true)"
if [[ -n "$PRE" ]]; then
  echo "ABORT: a matching process already runs before the probe; the anchor cannot be measured:"
  echo "$PRE"
  exit 1
fi

echo "== start probe =="
docker compose exec -d -T "$SERVICE" bash -c "exec -a $PROBE sleep 120" </dev/null
PID=""
for _ in $(seq 1 20); do PID="$(probe_pid)"; [[ -n "$PID" ]] && break; sleep 0.5; done
echo "probe pid: ${PID:-<none>}"
[[ -n "$PID" ]]; check "probe is live in $SERVICE" $?
docker compose exec -T "$SERVICE" ps -eo pid,etimes,args </dev/null

echo "== anchor, probe live: modified harness must refuse =="
R0="$(rows)"; L0="$(logs)"
OUT="$(scripts/testing/run_and_log.sh OPS-43b-refuse "$TRIVIAL" 2>&1)"; ST=$?
R1="$(rows)"; L1="$(logs)"
echo "$OUT"
echo "status=$ST rows_before=$R0 rows_after=$R1 logs_before=$L0 logs_after=$L1"
[[ "$ST" -eq "$REFUSAL" ]]; check "refusal status is exactly $REFUSAL (got $ST)" $?
[[ -n "$PID" && "$OUT" == *"pid=$PID "* ]]; check "refusal names probe pid $PID" $?
[[ "$R1" -eq "$R0" ]]; check "no test-results row written ($R0 -> $R1)" $?
[[ "$L1" -eq "$L0" ]]; check "no log file written ($L0 -> $L1)" $?

echo "== scope, probe live: host-only CMD is not checked =="
R0="$(rows)"
scripts/testing/run_and_log.sh OPS-43b-hostonly "true"; ST=$?
R1="$(rows)"
echo "status=$ST rows_before=$R0 rows_after=$R1"
[[ "$ST" -eq 0 ]]; check "host-only CMD proceeds with the probe live (got $ST)" $?
[[ "$R1" -eq $((R0 + 1)) ]]; check "host-only CMD appends exactly one row ($R0 -> $R1)" $?

echo "== negative control, probe live: pre-change harness proceeds =="
mkdir -p "$SCRATCH/scripts/testing"
git show HEAD:scripts/testing/run_and_log.sh >"$SCRATCH/scripts/testing/run_and_log.sh"
if grep -q ORPHAN_REFUSAL "$SCRATCH/scripts/testing/run_and_log.sh"; then
  echo "note: HEAD's harness already carries the check; the control is not a pre-change copy"
  check "control copy is pre-change" 1
fi
bash "$SCRATCH/scripts/testing/run_and_log.sh" OPS-43b-control "$TRIVIAL"; ST=$?
echo "control status=$ST"
echo "control log Exit block:"
grep -A2 '^## Exit' "$SCRATCH"/docs/testing/logs/*_OPS-43b-control.log
[[ "$ST" -eq 0 ]]; check "pre-change harness proceeds with the probe live (got $ST)" $?
[[ -n "$(probe_pid)" ]]; check "probe was still live after the control" $?

echo "== kill probe =="
docker compose exec -T "$SERVICE" pkill -f "$PROBE" </dev/null
for _ in $(seq 1 20); do [[ -z "$(probe_pid)" ]] && break; sleep 0.5; done
[[ -z "$(probe_pid)" ]]; check "probe gone" $?
docker compose exec -T "$SERVICE" ps -eo pid,etimes,args </dev/null

echo "== anchor, probe killed: same call must proceed =="
R0="$(rows)"
scripts/testing/run_and_log.sh OPS-43b-proceed "$TRIVIAL"; ST=$?
R1="$(rows)"
echo "status=$ST rows_before=$R0 rows_after=$R1"
[[ "$ST" -eq 0 ]]; check "same call exits exactly 0 (got $ST)" $?
[[ "$R1" -eq $((R0 + 1)) ]]; check "exactly one row appended ($R0 -> $R1)" $?

echo "== summary: $FAILS failure(s) =="
[[ "$FAILS" -eq 0 ]]
