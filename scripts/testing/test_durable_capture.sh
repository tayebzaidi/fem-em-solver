#!/usr/bin/env bash
# OPS-43 (a) gate: durable capture survives a killed wrapper, and
# run_and_log.sh --capture-orphan turns the surviving raw file into a footered
# log (PROJECT_PLAN §9 item 3 / §7 OPS-43 (a) / §5.1). Host-side; run it
# through the harness itself:
#
#   scripts/testing/run_and_log.sh OPS-43a "timeout -k 30 120 bash scripts/testing/test_durable_capture.sh"
#
# Asserted:
#   anchor   a container command in the documented rc-in-raw-file shape prints
#            `line 1`..`line 12` one second apart and exits 3. The harness is
#            started on it in the background INSIDE this script, in its own
#            session/process group; that group is SIGKILLed mid-window; the
#            container command is polled (<= 30 s) until it finishes by itself.
#            Then: exactly 12 `line` lines and exactly one `[capture] rc=3` in
#            the raw file; the recovered log has `## Exit` and `- Status: 3`;
#            the capture call exits 3; test-results rows rise by exactly 1.
#   control  the killed wrapper's own log (if created) has NO `## Exit`.
#   control  a copy of the raw file without its rc line makes --capture-orphan
#            exit NO_RC_CAPTURE (76) and write `Status: unknown (no rc line)`.
#
# Negative-result branch (item text): if the container command dies with the
# killed wrapper, the raw file state and the container ps are printed and the
# script exits 2 without running the capture assertions.
#
# Disclosure: the nested harness calls append their own logs to docs/testing/
# (chunk ids OPS-43a-killed [no footer, no row -- the defect], OPS-43a-capture,
# OPS-43a-norc [one row each]); row assertions are deltas around each call.
# Raw files live under the gitignored logs/ and are removed on every exit path.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"
export COMPOSE_FILE="$ROOT_DIR/docker/docker-compose.yml"
SERVICE=fem-em-solver
MARKER=ops43a-durable-capture-marker   # must not match mpiexec|hydra_pmi_proxy|pytest
NO_RC=76
INDEX="$ROOT_DIR/docs/testing/test-results.md"
LOG_DIR="$ROOT_DIR/docs/testing/logs"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="ops43a-capture-$STAMP"
RAW_REL="logs/$NAME-raw.log"
RAW="$ROOT_DIR/$RAW_REL"
RAW_CT="/workspace/$RAW_REL"
NORC_REL="logs/$NAME-norc-raw.log"
NORC="$ROOT_DIR/$NORC_REL"
SCRATCH_TOP="$ROOT_DIR/logs/.ops43a_scratch"
SCRATCH="$SCRATCH_TOP/$STAMP"
FAILS=0
HPGID=""

cleanup() {
  if [[ -n "$HPGID" ]]; then kill -KILL -- "-$HPGID" 2>/dev/null || true; fi
  docker compose exec -T "$SERVICE" pkill -f "$MARKER" </dev/null >/dev/null 2>&1 || true
  rm -f "$RAW" "$NORC"
  rm -rf "$SCRATCH_TOP"
}
trap cleanup EXIT INT TERM

check() {  # check <description> <condition-status>
  if [[ "$2" -eq 0 ]]; then echo "PASS: $1"; else echo "FAIL: $1"; FAILS=$((FAILS + 1)); fi
}
rows() { wc -l <"$INDEX"; }
count() { local n; n="$(grep -cE "$1" "$2" 2>/dev/null)"; echo "${n:-0}"; }
marker_pids() { docker compose exec -T "$SERVICE" pgrep -f "$MARKER" </dev/null 2>/dev/null | tr -d '\r' | tr '\n' ' '; }
cps() { docker compose exec -T "$SERVICE" ps -eo pid,etimes,args </dev/null; }

echo "== container process table before anything ($SERVICE) =="
cps
PRE="$(cps | awk 'NR>1 && $3!="ps"' | grep -E "mpiexec|hydra_pmi_proxy|pytest|$MARKER" || true)"
if [[ -n "$PRE" ]]; then
  echo "ABORT: a matching process already runs; the anchor cannot be measured:"
  echo "$PRE"
  exit 1
fi

mkdir -p "$SCRATCH" "$ROOT_DIR/logs"
rm -f "$RAW"
INNER="cd /workspace && : $MARKER; ( for i in \$(seq 1 12); do echo \"line \$i\"; sleep 1; done; exit 3 ) > $RAW_CT 2>&1; rc=\$?; echo \"[capture] rc=\$rc\" >> $RAW_CT; cat $RAW_CT; exit \$rc"
CMD="docker compose exec -T $SERVICE bash -lc '$INNER'"
echo "== documented shape under test =="
echo "$CMD"

echo "== start harness in the background, own session =="
KILLED_BEFORE="$(find "$LOG_DIR" -maxdepth 1 -name '*_OPS-43a-killed.log' | wc -l)"
ROWS_KILLED0="$(rows)"
T0="$(date +%s.%N)"
setsid scripts/testing/run_and_log.sh OPS-43a-killed "$CMD" >"$SCRATCH/wrapper.out" 2>&1 </dev/null &
HPID=$!
sleep 0.3
PG="$(ps -o pgid= -p "$HPID" 2>/dev/null | tr -d ' ')"
MYPG="$(ps -o pgid= -p $$ | tr -d ' ')"
echo "harness pid=$HPID pgid=${PG:-<none>} gate pgid=$MYPG"
if [[ -z "$PG" || "$PG" == "$MYPG" ]]; then
  echo "ABORT: the harness is not in a process group of its own; refusing to kill"
  exit 1
fi
HPGID="$PG"

# wait for the window to be under way (>= 2 lines written), bounded, then ~4 s
for _ in $(seq 1 60); do
  [[ "$(count '^line [0-9]+$' "$RAW")" -ge 2 ]] && break
  sleep 0.25
done
while awk -v t0="$T0" -v now="$(date +%s.%N)" 'BEGIN{exit !(now - t0 < 4.0)}'; do sleep 0.1; done

echo "== SIGKILL the harness process group =="
echo "host processes in group $HPGID before the kill:"
ps -o pid,pgid,args -g "$HPGID" 2>/dev/null || true
LINES_AT_KILL="$(count '^line [0-9]+$' "$RAW")"
kill -KILL -- "-$HPGID"
KILL_ST=$?
T_KILL="$(date +%s.%N)"
KILLED_PG="$HPGID"
HPGID=""
wait "$HPID" 2>/dev/null
echo "kill status=$KILL_ST at t=$(awk -v a="$T0" -v b="$T_KILL" 'BEGIN{printf "%.2f", b-a}') s; raw line count at kill=$LINES_AT_KILL"
[[ "$KILL_ST" -eq 0 ]]; check "harness process group killed (kill status $KILL_ST)" $?
[[ "$LINES_AT_KILL" -ge 1 && "$LINES_AT_KILL" -le 11 ]]; check "kill landed mid-window (1 <= $LINES_AT_KILL <= 11 lines written)" $?
sleep 0.5
# Host-side survivors = the killed group's members, or any `compose exec`
# client carrying the marker. NOT a bare `pgrep -f $MARKER`: on this WSL2 host
# the container's own processes are visible in the host PID namespace, so that
# pattern matched the container bash (host 826758/826769 = container 282/293)
# and failed while the compose clients were already gone
# (docs/testing/logs/20260910T213546Z_OPS-43a.log:52-55).
HOST_LEFT="$(ps -o pid=,args= -g "$KILLED_PG" 2>/dev/null; pgrep -af "compose exec.*$MARKER" || true)"
echo "host wrapper/compose-client processes left: ${HOST_LEFT:-<none>}"
[[ -z "$HOST_LEFT" ]]; check "no host-side wrapper or compose client survives the group kill" $?
ALIVE="$(marker_pids)"
echo "container marker pids right after the kill: ${ALIVE:-<none>}"
cps

if [[ -z "${ALIVE// /}" && "$(count '^line [0-9]+$' "$RAW")" -lt 12 ]]; then
  echo "NEGATIVE RESULT: the container command died with the killed wrapper."
  echo "raw file state:"; ls -la "$RAW" 2>&1; cat "$RAW" 2>&1
  echo "container ps:"; cps
  exit 2
fi
[[ -n "${ALIVE// /}" ]]; check "container command outlives the killed wrapper" $?

echo "== poll the container until the command finishes by itself (<= 30 s) =="
DONE=1
for _ in $(seq 1 60); do
  if [[ -z "$(marker_pids | tr -d ' ')" ]]; then DONE=0; break; fi
  sleep 0.5
done
T_DONE="$(date +%s.%N)"
echo "container command gone at t=$(awk -v a="$T0" -v b="$T_DONE" 'BEGIN{printf "%.2f", b-a}') s"
check "container command finished by itself within 30 s of the kill" $DONE
cps

echo "== negative control: the killed wrapper's own log =="
KILLED_AFTER="$(find "$LOG_DIR" -maxdepth 1 -name '*_OPS-43a-killed.log' | wc -l)"
echo "killed-wrapper logs before=$KILLED_BEFORE after=$KILLED_AFTER; rows before=$ROWS_KILLED0 now=$(rows)"
if [[ "$KILLED_AFTER" -gt "$KILLED_BEFORE" ]]; then
  KLOG="$(find "$LOG_DIR" -maxdepth 1 -name '*_OPS-43a-killed.log' -newermt "@${T0%.*}" | sort | tail -n 1)"
  echo "killed wrapper log: $KLOG (tail follows)"
  tail -n 5 "$KLOG"
  NEXIT="$(count '^## Exit$' "$KLOG")"
  [[ "$NEXIT" -eq 0 ]]; check "killed wrapper's log has no '## Exit' ($NEXIT found)" $?
else
  echo "no killed-wrapper log was created"
fi
echo "wrapper stdout/stderr:"; cat "$SCRATCH/wrapper.out"

echo "== raw file after the command finished =="
cat -A "$RAW" | sed 's/^/  | /'
NLINE="$(count '^line [0-9]+$' "$RAW")"
NRC3="$(grep -cxF '[capture] rc=3' "$RAW")"
NRCANY="$(count '\[capture\] rc=' "$RAW")"
echo "line lines=$NLINE rc=3 lines=$NRC3 any rc lines=$NRCANY"
[[ "$NLINE" -eq 12 ]]; check "raw file carries exactly 12 'line' lines (got $NLINE)" $?
[[ "$NRC3" -eq 1 && "$NRCANY" -eq 1 ]]; check "raw file carries exactly one rc line, '[capture] rc=3'" $?
SEQ_OK=0; for i in $(seq 1 12); do grep -qx "line $i" "$RAW" || SEQ_OK=1; done
check "raw 'line' lines are line 1 .. line 12" $SEQ_OK

echo "== anchor: --capture-orphan on the surviving raw file =="
R0="$(rows)"
OUT="$(scripts/testing/run_and_log.sh --capture-orphan OPS-43a-capture "$RAW_REL" 2>&1)"; ST=$?
R1="$(rows)"
echo "$OUT"
REC="$(printf '%s\n' "$OUT" | sed -n 's/^Log written: //p')"
echo "capture status=$ST rows_before=$R0 rows_after=$R1 recovered log=${REC:-<none>}"
[[ -n "$REC" && -f "$REC" ]]; check "recovered log exists" $?
echo "recovered log header (mode/raw) and Exit block:"
grep -E '^- (Chunk|Command|Mode|Raw file)' "$REC" 2>/dev/null
grep -A4 '^## Exit$' "$REC" 2>/dev/null
[[ "$(count '^## Exit$' "$REC")" -eq 1 ]]; check "recovered log has exactly one '## Exit'" $?
grep -qx -- '- Status: 3' "$REC" 2>/dev/null; check "recovered log has '- Status: 3'" $?
[[ "$(count '^line [0-9]+$' "$REC")" -eq 12 ]]; check "recovered log's Output carries the 12 lines" $?
[[ "$ST" -eq 3 ]]; check "capture call exits exactly 3 (got $ST)" $?
[[ "$R1" -eq $((R0 + 1)) ]]; check "test-results rows rise by exactly 1 ($R0 -> $R1)" $?

echo "== negative control: raw copy with the rc line removed =="
grep -vF '[capture] rc=' "$RAW" >"$NORC"
echo "norc copy: line lines=$(count '^line [0-9]+$' "$NORC") rc lines=$(count '\[capture\] rc=' "$NORC")"
R0="$(rows)"
OUT="$(scripts/testing/run_and_log.sh --capture-orphan OPS-43a-norc "$NORC_REL" 2>&1)"; ST=$?
R1="$(rows)"
echo "$OUT"
NREC="$(printf '%s\n' "$OUT" | sed -n 's/^Log written: //p')"
echo "no-rc capture status=$ST rows_before=$R0 rows_after=$R1 log=${NREC:-<none>}"
grep -A4 '^## Exit$' "$NREC" 2>/dev/null
[[ "$ST" -eq "$NO_RC" ]]; check "no-rc capture exits exactly NO_RC_CAPTURE=$NO_RC (got $ST)" $?
grep -qx -- '- Status: unknown (no rc line)' "$NREC" 2>/dev/null; check "no-rc log has '- Status: unknown (no rc line)'" $?
[[ "$(count '^- Status: [0-9]+$' "$NREC")" -eq 0 ]]; check "no-rc log claims no numeric status" $?
[[ "$R1" -eq $((R0 + 1)) ]]; check "no-rc capture appends exactly one row ($R0 -> $R1)" $?
tail -n 1 "$INDEX"

echo "== container process table at the end =="
cps

echo "== summary: $FAILS failure(s) =="
[[ "$FAILS" -eq 0 ]]
