#!/usr/bin/env bash
# Harness routing gate: run_and_log.sh resolves service / profile / ledger once
# and its orphan check (OPS-43 (b)) lists processes in the service the command
# actually targets. Before 2026-09-19 the check had no xxl branch, so an XXL
# command was checked against the ordinary `fem-em-solver` container. Host-side,
# no real docker: a stub `docker` first on PATH records its argv and answers
# the `ps` listing with one fake surviving rank, so every call ends in the
# refusal path — which by contract writes no log, no row and no ledger row.
#
#   scripts/testing/run_and_log.sh OPS-ROUTING "timeout -k 30 60 bash scripts/testing/test_service_routing.sh"
#
# Asserted, for each of fem-em-solver / fem-em-solver-xl / fem-em-solver-xxl:
#   - dry run prints the expected service / profile / ledger;
#   - the orphan listing is `docker compose [--profile <tier>] exec -T <service> ps …`
#     against exactly that service, and the harness exits 75 naming it;
#   - test-results.md, both ledgers and the log directory are unchanged.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/service_routing.XXXXXX")"
FAILS=0
trap 'rm -rf "$SCRATCH"' EXIT

check() {  # check <description> <condition-status>
  if [[ "$2" -eq 0 ]]; then echo "PASS: $1"; else echo "FAIL: $1"; FAILS=$((FAILS + 1)); fi
}

mkdir -p "$SCRATCH/bin"
cat >"$SCRATCH/bin/docker" <<'EOF'
#!/usr/bin/env bash
echo "$*" >>"$STUB_ARGV"
if [[ "$*" == *" ps -eo pid,etimes,args" ]]; then
  echo "    PID ELAPSED COMMAND"
  echo "   4242    9999 mpiexec -n 8 python3 -m pytest tests/stub"
fi
exit 0
EOF
chmod +x "$SCRATCH/bin/docker"
export STUB_ARGV="$SCRATCH/argv"

state() {
  wc -l <docs/testing/test-results.md
  wc -l <docs/testing/xl-ledger.md
  wc -l <docs/testing/xxl-ledger.md
  find docs/testing/logs -maxdepth 1 -type f | wc -l
}

for case in "fem-em-solver|<none>||exec -T fem-em-solver ps" \
            "fem-em-solver-xl|xl|xl-ledger.md|--profile xl exec -T fem-em-solver-xl ps" \
            "fem-em-solver-xxl|xxl|xxl-ledger.md|--profile xxl exec -T fem-em-solver-xxl ps"; do
  IFS='|' read -r SVC PROFILE LEDGER LISTING <<<"$case"
  CMD="docker compose exec -T $SVC true"
  echo "== $SVC =="

  DRY="$(scripts/testing/run_and_log.sh --dry-run ROUTING-dry "$CMD" | grep 'Routing:')"
  echo "  $DRY"
  [[ "$DRY" == "[DRY RUN] Routing: service=$SVC profile=$PROFILE ledger=$LEDGER" ]]
  check "$SVC: dry run resolves service=$SVC profile=$PROFILE ledger=${LEDGER:-<none>}" $?

  : >"$STUB_ARGV"
  S0="$(state)"
  OUT="$(PATH="$SCRATCH/bin:$PATH" scripts/testing/run_and_log.sh ROUTING-refuse "$CMD" 2>&1)"; ST=$?
  S1="$(state)"
  PS_CALL="$(grep ' ps -eo pid,etimes,args$' "$STUB_ARGV")"
  echo "  status=$ST listing argv: $PS_CALL"
  [[ "$ST" -eq 75 ]]; check "$SVC: stubbed survivor -> refusal status 75 (got $ST)" $?
  [[ "$(wc -l <<<"$PS_CALL")" -eq 1 && "$PS_CALL" == "compose $LISTING -eo pid,etimes,args" ]]
  check "$SVC: orphan listing is exactly 'compose $LISTING …'" $?
  [[ "$OUT" == *"live ranks in service $SVC"$'\n'* ]]; check "$SVC: refusal names service $SVC" $?
  [[ "$S0" == "$S1" ]]; check "$SVC: no row, no ledger row, no log written" $?
done

echo "== summary: $FAILS failure(s) =="
[[ "$FAILS" -eq 0 ]]
