#!/usr/bin/env bash
set -euo pipefail

# Project-root test entrypoint.
#
# The historical pending-tests queue (docs/testing/pending-tests.md +
# scripts/testing/run_pending_tests.sh) was removed 2026-08-04: verification is
# executed by agents through scripts/testing/run_and_log.sh, not queued for a
# human. This script keeps the lightweight smoke matrix that CI depends on.
#
# Usage:
#   ./run_tests.sh --smoke     # lightweight smoke matrix (used by CI)
#   ./run_tests.sh --list      # show the smoke matrix targets

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

SMOKE_TEST_TARGETS=(
  "tests/unit/test_analytical_lightweight.py"
  "tests/solver/test_tolerance_policy.py"
  "tests/validation/test_tolerance_policy.py"
  "tests/ports/test_port_definition.py"
)

usage() {
  sed -n '4,14p' "$0"
}

case "${1:-}" in
  --smoke)
    cd "$ROOT_DIR"
    echo "Running lightweight smoke matrix (no heavy FEM/mesh/solver cases):"
    for target in "${SMOKE_TEST_TARGETS[@]}"; do
      echo "  - $target"
    done
    python3 -m pytest "${SMOKE_TEST_TARGETS[@]}" -v
    ;;
  --list)
    echo "Smoke matrix targets:"
    for target in "${SMOKE_TEST_TARGETS[@]}"; do
      echo "  - $target"
    done
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "Unknown or missing argument: '${1:-}'" >&2
    echo "Full verification goes through scripts/testing/run_and_log.sh (see PROJECT_PLAN.md §5)." >&2
    usage >&2
    exit 2
    ;;
esac
