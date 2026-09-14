#!/usr/bin/env python3
"""Exercise the two big-compute tiers in `bash_guard.py`.

Run as a file, never as an inline command: the guard is a PreToolUse hook, so a
shell invocation whose *own text* contains a tier's service name is itself
matched and denied. Writing the cases here keeps them out of the command line.

    python3 scripts/testing/test_tier_guard.py
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts" / "automation" / "hooks" / "bash_guard.py"

spec = importlib.util.spec_from_file_location("guard", GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

TEMPLATE = (
    'scripts/testing/run_and_log.sh CHUNK "docker compose exec -T {svc} '
    "bash -lc 'timeout -k 60 {timeout} mpiexec -n {ranks} python3 -m pytest a'\""
)


def verdict(cmd: str) -> str:
    r = subprocess.run([sys.executable, str(GUARD)],
                       input=json.dumps({"tool_input": {"command": cmd}}),
                       capture_output=True, text=True)
    if not r.stdout.strip():
        return "ALLOW"
    reason = json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    return "DENY  " + reason[:88]


def main() -> int:
    xl, xxl = guard.TIERS["xl"], guard.TIERS["xxl"]
    for name, spec_ in (("xl", xl), ("xxl", xxl)):
        used = guard.runs_in_trailing_week(spec_["ledger"])
        print(f"{name:4} budget: {used} of {spec_['per_week']} used in the trailing 7 days "
              f"({spec_['ledger'].name})")
    print()

    cases = [
        ("xl  at its 4 h ceiling",      xl["service"], 14400, 16),
        ("xl  asked for 5 h",           xl["service"], 18000, 16),
        ("xl  asked for 8 h",           xl["service"], 28800, 16),
        ("xl  asked for 17 ranks",      xl["service"],  7200, 17),
        ("xxl at its 8 h ceiling",     xxl["service"], 28800, 16),
        ("xxl asked for 9 h",          xxl["service"], 32400, 16),
        ("xxl asked for 20 ranks",     xxl["service"], 28800, 20),
        ("ordinary service, 17 ranks", "fem-em-solver", 600, 17),
        ("ordinary service, 8 ranks",  "fem-em-solver", 600,  8),
    ]
    for label, svc, timeout, ranks in cases:
        cmd = TEMPLATE.format(svc=svc, timeout=timeout, ranks=ranks)
        print(f"{label:28} -> {verdict(cmd)}")

    print("\nbypassing the harness:")
    raw = ('docker compose exec -T ' + xxl["service"] +
           " bash -lc 'timeout -k 60 28800 mpiexec -n 16 python3 -m pytest a'")
    print(f"{'xxl without run_and_log.sh':28} -> {verdict(raw)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
