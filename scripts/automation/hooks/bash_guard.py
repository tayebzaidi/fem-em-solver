#!/usr/bin/env python3
"""PreToolUse guard for Bash commands (wired in .claude/settings.json).

Enforces two CLAUDE.md hard rules mechanically, for every session including
the headless cron runs:

  1. Rank ceiling: any `mpiexec/mpirun -n/-np N` with N > 12 is denied.
  2. Harness routing: pytest invocations must go through
     scripts/testing/run_and_log.sh (collection-only queries are exempt).

Fail-open on malformed input: a broken guard must not brick every Bash call.
"""
import json
import re
import sys


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        cmd = payload.get("tool_input", {}).get("command", "") or ""
    except Exception:
        sys.exit(0)  # fail open

    # Rule 1: 12-rank ceiling, absolute — applies even inside harness commands.
    for m in re.finditer(r"mpi(?:exec|run)\s+(?:-n|-np)\s+(\d+)", cmd):
        if int(m.group(1)) > 12:
            deny(
                f"mpiexec -n {m.group(1)} exceeds the 12-rank ceiling for this "
                "project (CLAUDE.md hard rules; shared 36-core box). Use the "
                "smallest rank count that fits the tier."
            )

    # Rule 2: pytest runs go through the logging harness. Matching is scoped
    # to actual invocations (container exec, mpiexec, or a host-side pytest at
    # a command boundary) so grep/git/commit-message mentions never trip it.
    if "run_and_log.sh" not in cmd:
        collect_only = "--collect-only" in cmd or "--co" in cmd or "--version" in cmd
        in_container = "docker compose" in cmd and "exec" in cmd and re.search(r"\bpytest\b", cmd)
        host_side = re.search(r"(?:^|[;&|]\s*)(?:timeout\s+\S+\s+)?(?:mpi(?:exec|run)[^;&|]*\s)?(?:python3?\s+-m\s+)?pytest\b", cmd)
        if (in_container or host_side) and not collect_only:
            deny(
                "pytest must run through the logging harness: "
                "scripts/testing/run_and_log.sh <CHUNK-ID> \"docker compose exec -T "
                "fem-em-solver bash -lc '...'\" (CLAUDE.md hard rules). "
                "Collection-only checks (--collect-only) are exempt."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
