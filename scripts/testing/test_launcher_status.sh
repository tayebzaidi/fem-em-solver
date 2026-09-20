#!/usr/bin/env bash
# Launcher footer gate: daily-review.sh / weekly-review.sh / implementer-run.sh
# write `outcome=<path> exit=<n>` on every exit path. Before 2026-09-19 a
# nonzero CLI exit ended the script under `set -e` ahead of `STATUS=$?`, so a
# timed-out or dead session left no exit line at all. Host-side, no solver, no
# docker, no real CLI: the launchers run against a stub in a scratch root.
#
#   scripts/testing/run_and_log.sh OPS-LAUNCHER "timeout -k 30 60 bash scripts/testing/test_launcher_status.sh"
#
# Asserted, per launcher:
#   stub exits 0   -> launcher exits 0,   footer `outcome=ok exit=0`
#   stub exits 1   -> launcher exits 1,   footer `outcome=session-failed exit=1`
#   stub exits 124 -> launcher exits 124, footer `outcome=timeout exit=124`
#   stub exits 137 -> launcher exits 137, footer `outcome=timeout exit=137`
#   lock held      -> launcher exits 0,   footer `outcome=skipped-lock exit=0`,
#                     stub never invoked
#   CLI missing    -> launcher exits 127, footer `outcome=session-failed exit=127`
# The 124/137 legs test the classification only; the real `timeout` cap is not
# waited out.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/launcher_status.XXXXXX")"
FAILS=0
trap 'rm -rf "$SCRATCH"' EXIT

check() {  # check <description> <condition-status>
  if [[ "$2" -eq 0 ]]; then echo "PASS: $1"; else echo "FAIL: $1"; FAILS=$((FAILS + 1)); fi
}

STUB="$SCRATCH/claude-stub"
cat >"$STUB" <<'EOF'
#!/usr/bin/env bash
echo "stub session body"
touch "$STUB_MARK"
exit "${STUB_RC:-0}"
EOF
chmod +x "$STUB"

run_launcher() {  # run_launcher <launcher> <case-name> <stub-rc> [claude-bin]
  local repo="$SCRATCH/$1.$2"
  mkdir -p "$repo"
  export STUB_MARK="$repo/stub-ran"
  FEM_EM_REPO="$repo" FEM_EM_AUTOMATION_LOCK="$SCRATCH/lock" \
    FEM_EM_CLAUDE_BIN="${4:-$STUB}" STUB_RC="$3" \
    bash "$ROOT_DIR/scripts/automation/$1.sh"
  ST=$?
  FOOTER="$(tail -n 1 "$repo"/logs/automation/*.log)"
  echo "  [$1/$2] status=$ST footer: $FOOTER"
}

for L in daily-review weekly-review implementer-run; do
  echo "== $L =="
  for case in "0 ok" "1 session-failed" "124 timeout" "137 timeout"; do
    set -- $case
    run_launcher "$L" "rc$1" "$1"
    [[ "$ST" -eq "$1" ]]; check "$L: stub rc=$1 -> launcher exits $1 (got $ST)" $?
    [[ "$FOOTER" == *"outcome=$2 exit=$1" ]]; check "$L: stub rc=$1 -> footer outcome=$2 exit=$1" $?
  done

  (
    exec 8>"$SCRATCH/lock"; flock 8
    run_launcher "$L" locked 0
    [[ "$ST" -eq 0 && "$FOOTER" == *"outcome=skipped-lock exit=0" && ! -e "$STUB_MARK" ]]
  ); check "$L: held lock -> exit 0, outcome=skipped-lock, stub not invoked" $?

  run_launcher "$L" nocli 0 "$SCRATCH/no-such-cli"
  [[ "$ST" -eq 127 ]]; check "$L: missing CLI -> launcher exits 127 (got $ST)" $?
  [[ "$FOOTER" == *"outcome=session-failed exit=127" ]]; check "$L: missing CLI -> footer outcome=session-failed exit=127" $?
done

echo "== summary: $FAILS failure(s) =="
[[ "$FAILS" -eq 0 ]]
