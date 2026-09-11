#!/usr/bin/env bash
# OPS-45 gate: the harness footer honours a final `[capture] rc=` line
# (PROJECT_PLAN §7 OPS-45 / §9 / §5.1). Host-only commands, no container; run
# it through the harness itself:
#
#   scripts/testing/run_and_log.sh OPS-45 "timeout -k 30 120 bash scripts/testing/test_capture_status.sh"
#
# Asserted (anchor, against the working-tree harness):
#   (i)   `echo x; echo "[capture] rc=1"` (command exits 0) => `- Status: 1`,
#         harness exit 1, new row Exit 1, capture note present.
#   (ii)  the full documented idiom WITH `exit $rc`, rc = 3 => Status 3, exit 3,
#         row Exit 3, no capture note.
#   (iii) rc line not last (`echo "[capture] rc=1"; echo tail`, exit 0)
#         => Status 0, exit 0, row Exit 0, no note.
#   (iv)  `echo "[capture] rc=0"; exit 5` => Status 5, exit 5, row Exit 5, no note.
# Asserted (negative control): case (i) through the pinned pre-change harness
#   `git show 06044b4:scripts/testing/run_and_log.sh` (copied under the
#   gitignored logs/, two levels deep so its ROOT_DIR resolves to the repo)
#   reads `- Status: 0` and exits 0 -- the defect reproduces.
#
# Disclosure: every nested harness call appends its own log to docs/testing/logs
# and one row to test-results.md (chunk ids OPS-45-i, -ii, -iii, -iv,
# OPS-45-control); row assertions are +1 deltas around each call. Scratch files
# live under the gitignored logs/ and are removed on every exit path.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"
INDEX="$ROOT_DIR/docs/testing/test-results.md"
PRE_SHA=06044b4
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SCRATCH_TOP="$ROOT_DIR/logs/.ops45_scratch"
RAW_REL="logs/ops45-idiom-$STAMP-raw.log"
FAILS=0

cleanup() { rm -rf "$SCRATCH_TOP"; rm -f "$ROOT_DIR/$RAW_REL"; }
trap cleanup EXIT INT TERM

check() {  # check <description> <condition-status>
  if [[ "$2" -eq 0 ]]; then echo "PASS: $1"; else echo "FAIL: $1"; FAILS=$((FAILS + 1)); fi
}
rows() { wc -l <"$INDEX"; }

# run_case <label> <harness path> <chunk id> <command> <want status> <want note 0|1>
run_case() {
  local label="$1" harness="$2" chunk="$3" cmd="$4" want="$5" want_note="$6"
  echo "== $label =="
  echo "command: $cmd"
  local r0 r1 out st log row_exit row_log notes
  r0="$(rows)"
  out="$("$harness" "$chunk" "$cmd" 2>&1)"; st=$?
  r1="$(rows)"
  echo "$out"
  log="$(printf '%s\n' "$out" | sed -n 's/^Log written: //p')"
  echo "harness exit=$st rows $r0 -> $r1 log=${log:-<none>}"
  [[ -n "$log" && -f "$log" ]]; check "$label: log exists" $?
  echo "Exit block:"; grep -A4 '^## Exit$' "$log" 2>/dev/null
  row_exit="$(tail -n 1 "$INDEX" | awk -F'|' '{gsub(/ /, "", $7); print $7}')"
  row_log="$(tail -n 1 "$INDEX" | awk -F'|' '{gsub(/[ `]/, "", $8); print $8}')"
  notes="$(grep -c '^- Capture note:' "$log" 2>/dev/null)"
  echo "last row: $(tail -n 1 "$INDEX")"
  grep -qx -- "- Status: $want" "$log" 2>/dev/null; check "$label: footer reads '- Status: $want'" $?
  [[ "$st" -eq "$want" ]]; check "$label: harness exits $want (got $st)" $?
  [[ "$r1" -eq $((r0 + 1)) ]]; check "$label: test-results rows rise by exactly 1 ($r0 -> $r1)" $?
  [[ "$row_exit" == "$want" ]]; check "$label: new row Exit is $want (got '$row_exit')" $?
  [[ "$row_log" == "$(basename "$log")" ]]; check "$label: new row names this log" $?
  [[ "${notes:-0}" -eq "$want_note" ]]; check "$label: capture note count is $want_note (got ${notes:-0})" $?
}

HARNESS=scripts/testing/run_and_log.sh

run_case "(i) rc line last, command exits 0" "$HARNESS" OPS-45-i \
  'echo x; echo "[capture] rc=1"' 1 1

run_case "(ii) documented idiom with exit \$rc, rc 3" "$HARNESS" OPS-45-ii \
  "( echo y; exit 3 ) > $RAW_REL 2>&1; rc=\$?; echo \"[capture] rc=\$rc\" >> $RAW_REL; cat $RAW_REL; exit \$rc" 3 0

run_case "(iii) rc line not last" "$HARNESS" OPS-45-iii \
  'echo "[capture] rc=1"; echo tail' 0 0

run_case "(iv) rc=0 line, command exits 5" "$HARNESS" OPS-45-iv \
  'echo "[capture] rc=0"; exit 5' 5 0

echo "== negative control: pinned pre-change harness $PRE_SHA =="
mkdir -p "$SCRATCH_TOP"
PRE_HARNESS="$SCRATCH_TOP/run_and_log.sh"
git show "$PRE_SHA:scripts/testing/run_and_log.sh" >"$PRE_HARNESS"; GS=$?
chmod +x "$PRE_HARNESS"
[[ "$GS" -eq 0 && -s "$PRE_HARNESS" ]]; check "control: pinned harness extracted from $PRE_SHA" $?
grep -c 'CAPTURE_RC' "$PRE_HARNESS" | sed 's/^/control: CAPTURE_RC mentions in pinned harness = /'
run_case "control (i) through $PRE_SHA harness" "$PRE_HARNESS" OPS-45-control \
  'echo x; echo "[capture] rc=1"' 0 0

echo "== summary: $FAILS failure(s) =="
[[ "$FAILS" -eq 0 ]]
