#!/usr/bin/env bash
# XL-window isolation gate (2026-09-19). An XL / XXL window holds its own lock,
# so reviews and implementer slots run while it does. Two defects followed:
# `xl-run.sh` ended with `git add -A` (it would commit another session's work
# in flight), and the harness dirtied main for the whole window (tracked
# ledger row at start, untracked log under docs/). This runs xl-run.sh END TO
# END in a scratch repo — real run_and_log.sh, real bash_guard.py budget
# arithmetic, a stub `docker`, no container, no compute — while the queued
# command itself plays the concurrent session.
#
#   scripts/testing/run_and_log.sh OPS-XL-ISOLATION "timeout -k 30 120 bash scripts/testing/test_xl_window_isolation.sh"
#
# Asserted:
#   window 1  mid-window `git status --porcelain` is EMPTY;
#             the xl-run commit holds exactly 4 paths (log, ledger,
#             test-results, queue entry removal);
#             the concurrent session's untracked / modified / staged files are
#             all still there, uncommitted, in the state it left them, and the
#             launcher log names them;
#             the ledger row carries an elapsed >= 1, the sidecar is gone, and
#             bash_guard.runs_in_trailing_week == 1.
#   window 2  a sidecar row left by a killed wrapper is folded in with a blank
#             elapsed: ledger rows 1 -> 3, charged rows == 2 (not 3).
#   branch    with HEAD moved off main mid-window nothing is committed there.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/xl_isolation.XXXXXX")"
REPO="$SCRATCH/repo"
FAILS=0
trap 'rm -rf "$SCRATCH"' EXIT

check() {  # check <description> <condition-status>
  if [[ "$2" -eq 0 ]]; then echo "PASS: $1"; else echo "FAIL: $1"; FAILS=$((FAILS + 1)); fi
}
G() { git -C "$REPO" "$@"; }

# --- scratch repo -----------------------------------------------------------
mkdir -p "$REPO/scripts/testing" "$REPO/scripts/automation/hooks" \
         "$REPO/docs/testing/logs" "$REPO/docs/testing/xl-queue.d" "$SCRATCH/home/.local/bin"
cp "$ROOT_DIR/scripts/testing/run_and_log.sh" "$REPO/scripts/testing/"
cp "$ROOT_DIR/scripts/automation/xl-run.sh" "$REPO/scripts/automation/"
cp "$ROOT_DIR/scripts/automation/hooks/bash_guard.py" "$REPO/scripts/automation/hooks/"
cp "$ROOT_DIR/.gitignore" "$REPO/.gitignore"
printf '# XL ledger (scratch)\n\n| Date | Chunk | Log | Ranks | Cells | Peak | Elapsed (s) | Readout |\n|---|---|---|---|---|---|---|---|\n' >"$REPO/docs/testing/xl-ledger.md"
echo "tracked source" >"$REPO/src.txt"
touch "$REPO/docs/testing/logs/.keep"

# The queued command IS the concurrent session: it records what `git status`
# shows mid-window, then leaves one untracked, one modified and one staged file.
cat >"$SCRATCH/probe.sh" <<EOF
#!/usr/bin/env bash
cd "$REPO"
git status --porcelain >"$SCRATCH/mid_status.\$1"
if [[ "\$1" == 1 ]]; then
  echo "in flight" >foreign_untracked.txt
  echo "edited by another session" >>src.txt
  echo "staged by another session" >foreign_staged.txt && git add foreign_staged.txt
fi
[[ "\$1" == 3 ]] && git checkout -q -b attempt/other-session
sleep 2
EOF
queue() {  # queue <n>  — the tier is routed by the service name in the command
  printf 'XL_CHUNK="ISO-%s"\nXL_COMMAND="bash %s %s # fem-em-solver-xl"\n' "$1" "$SCRATCH/probe.sh" "$1" \
    >"$REPO/docs/testing/xl-queue.d/0$1-ISO.env"
}
queue 1
printf '#!/usr/bin/env bash\nexit 0\n' >"$SCRATCH/home/.local/bin/docker"
chmod +x "$SCRATCH/home/.local/bin/docker"
G init -q -b main
G add -A
G -c user.name=t -c user.email=t@localhost commit -q -m "scratch base"

window() { HOME="$SCRATCH/home" FEM_EM_REPO="$REPO" FEM_EM_XL_LOCK="$SCRATCH/xl.lock" \
             bash "$REPO/scripts/automation/xl-run.sh" xl; }
charged() { (cd "$REPO/scripts/automation/hooks" && python3 -c "import bash_guard as g; print(g.runs_in_trailing_week(g.TIERS['xl']['ledger']))"); }
ledger_rows() { grep -cE '^\| *20[0-9]{2}-' "$REPO/docs/testing/xl-ledger.md"; }

# --- window 1 ---------------------------------------------------------------
echo "== window 1: concurrent session in flight =="
window; ST=$?
echo "xl-run exit=$ST"; echo "-- launcher log:"; sed 's/^/   /' "$REPO"/logs/automation/*_xl-run.log
[[ "$ST" -eq 0 ]]; check "xl-run exits 0 (got $ST)" $?
[[ -f "$SCRATCH/mid_status.1" && ! -s "$SCRATCH/mid_status.1" ]]
check "mid-window git status --porcelain is empty ($(wc -l <"$SCRATCH/mid_status.1" 2>/dev/null) lines)" $?

echo "-- xl-run commit:"; G show --stat --format='%an | %s' HEAD | sed 's/^/   /'
[[ "$(G log -1 --format=%an)" == "fem-em xl-run" ]]; check "HEAD is the xl-run commit" $?
PATHS="$(G show --name-only --format= HEAD | sort)"
N="$(wc -l <<<"$PATHS")"
[[ "$N" -eq 4 ]]; check "commit holds exactly 4 paths (got $N)" $?
WANT="$(printf '%s\n' docs/testing/test-results.md docs/testing/xl-ledger.md docs/testing/xl-queue.d/01-ISO.env \
        "$(cd "$REPO" && ls docs/testing/logs/*_ISO-1.log)" | sort)"
[[ "$PATHS" == "$WANT" ]]; check "those paths are log + ledger + test-results + queue entry" $?

echo "-- git status after window 1:"; G status --porcelain | sed 's/^/   /'
[[ "$(G status --porcelain -- foreign_untracked.txt)" == "?? foreign_untracked.txt" ]]; check "other session's untracked file still untracked" $?
[[ "$(G status --porcelain -- src.txt)" == " M src.txt" ]]; check "other session's edit still modified, unstaged" $?
[[ "$(G status --porcelain -- foreign_staged.txt)" == "A  foreign_staged.txt" ]]; check "other session's staged file still staged, not committed" $?
[[ "$(G status --porcelain | wc -l)" -eq 3 ]]; check "nothing else is dirty" $?
grep -q 'foreign_untracked.txt' "$REPO"/logs/automation/*_xl-run.log && grep -q 'src.txt' "$REPO"/logs/automation/*_xl-run.log
check "launcher log names the paths it left alone" $?

ROW="$(grep -E '^\| *20[0-9]{2}-' "$REPO/docs/testing/xl-ledger.md" | tail -1)"
ELAPSED="$(awk -F'|' '{gsub(/ /,"",$8); print $8}' <<<"$ROW")"
echo "   ledger row: $ROW"
[[ "$ELAPSED" =~ ^[0-9]+$ && "$ELAPSED" -ge 1 ]]; check "ledger row elapsed is a number >= 1 (got '$ELAPSED')" $?
[[ ! -e "$REPO/logs/xl-ledger.pending" ]]; check "sidecar removed after the fold" $?
[[ -z "$(ls "$REPO/logs/inflight" 2>/dev/null)" ]]; check "in-flight log moved out of logs/inflight" $?
C="$(charged)"; [[ "$C" -eq 1 ]]; check "bash_guard charges exactly 1 row (got $C)" $?

# --- window 2: stale sidecar row from a killed wrapper -----------------------
echo "== window 2: killed wrapper left a sidecar row =="
G checkout -q -- src.txt; G rm -q -f --cached foreign_staged.txt; rm -f "$REPO/foreign_untracked.txt" "$REPO/foreign_staged.txt"
printf '| %s | ISO-killed | `20260101T000000Z_ISO-killed.log` | | | | | |\n' "$(date -u +%Y-%m-%d)" >"$REPO/logs/xl-ledger.pending"
queue 2; G add -A; G -c user.name=t -c user.email=t@localhost commit -q -m "queue 2"
window; ST=$?
[[ "$ST" -eq 0 ]]; check "xl-run exits 0 (got $ST)" $?
[[ ! -s "$SCRATCH/mid_status.2" ]]; check "mid-window git status --porcelain is empty" $?
R="$(ledger_rows)"; [[ "$R" -eq 3 ]]; check "ledger rows 1 -> 3 (got $R)" $?
grep -q 'ISO-killed | `20260101T000000Z_ISO-killed.log` | | | | | |' "$REPO/docs/testing/xl-ledger.md"
check "killed wrapper's row folded in with a blank elapsed" $?
C="$(charged)"; [[ "$C" -eq 2 ]]; check "bash_guard charges 2 rows, not 3 (got $C)" $?
[[ -z "$(G status --porcelain)" ]]; check "tree clean after window 2" $?

# --- branch: HEAD moved off main mid-window ----------------------------------
echo "== branch: another session checked out attempt/* mid-window =="
queue 3; G add -A; G -c user.name=t -c user.email=t@localhost commit -q -m "queue 3"
BEFORE="$(G rev-parse main)"
window
[[ "$(G rev-parse --abbrev-ref HEAD)" == "attempt/other-session" && "$(G rev-parse HEAD)" == "$BEFORE" ]]
check "nothing committed onto attempt/other-session" $?
[[ "$(G rev-parse main)" == "$BEFORE" ]]; check "main unmoved" $?
grep -q 'FAILED: HEAD is on attempt/other-session' "$(ls -t "$REPO"/logs/automation/*_xl-run.log | head -1)"
check "launcher log says FAILED and why" $?

echo "== summary: $FAILS failure(s) =="
[[ "$FAILS" -eq 0 ]]
