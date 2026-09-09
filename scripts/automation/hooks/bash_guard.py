#!/usr/bin/env python3
"""PreToolUse guard for Bash commands (wired in .claude/settings.json).

Enforces the CLAUDE.md compute hard rules mechanically, for every session
including the headless cron runs:

  1. Rank ceiling: any `mpiexec/mpirun -n/-np N` with N > 12 is denied —
     except the XL tier (operator directive 2026-09-05): N <= 16 is allowed
     when the command is a `docker compose … exec` against the
     `fem-em-solver-xl` service (a mention of the name alone is not a run), goes through
     `scripts/testing/run_and_log.sh`, carries a `timeout -k 30 <s>` of at
     most 7200 s, and `docs/testing/xl-ledger.md` shows no XL run in the last
     7 days. The same four conditions gate *any* command against the XL
     service, whatever its rank count.
  2. Harness routing: pytest invocations must go through
     scripts/testing/run_and_log.sh (collection-only queries are exempt).

Fail-open on malformed input: a broken guard must not brick every Bash call.
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

RANK_CEILING = 12
XL_SERVICE = "fem-em-solver-xl"
XL_RANK_CEILING = 16
XL_TIMEOUT_CEILING_S = 7200
XL_INTERVAL_DAYS = 7
XL_LEDGER = Path(__file__).resolve().parents[3] / "docs" / "testing" / "xl-ledger.md"
XL_OVERRIDE = Path(__file__).resolve().parents[1] / "xl-override.env"

# Shared-box courtesy for the XL tier (operator directive 2026-09-09). An XL
# window holds up to 16 of this 36-core box's cores for up to two hours, so
# starting one onto a box somebody else is already using is the single rudest
# thing this project can do. Refuse when the cores are not there and say when
# to come back; the run is postponed, never silently degraded.
XL_LOAD_HEADROOM_CORES = 4.0
XL_LOAD_OVERRIDE_ENV = "FEM_EM_XL_IGNORE_LOAD"
XL_BOX_OK_ENV = "FEM_EM_XL_BOX_OK"


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def last_xl_run() -> "dt.date | None":
    """Date of the most recent ledger row (`| YYYY-MM-DD | ...`), or None."""
    try:
        text = XL_LEDGER.read_text(encoding="utf-8")
    except OSError:
        return None
    dates = [dt.date.fromisoformat(m) for m in re.findall(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|", text, flags=re.M)]
    return max(dates) if dates else None


def xl_interval_override() -> "str | None":
    """The reason string of an in-date operator override, else None.

    The 7-day interval is a budget the weekly review spends, and normally
    nothing may buy a second run inside it.  This is the one documented door:
    an **operator-authorised, dated, self-expiring** file that says who
    authorised the exception and until when.  It expires by date here, so an
    override cannot outlive its reason, and it never touches the ledger — the
    record of what ran stays complete and a spent slot stays spent.

    Malformed or absent file ⇒ no override, and the ordinary interval rule
    applies.  Fail-closed on purpose: the safe direction for a rule that
    protects a shared box is to deny.
    """
    try:
        text = XL_OVERRIDE.read_text(encoding="utf-8")
    except OSError:
        return None
    fields = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            fields[k.strip()] = v.strip().strip('"').strip("'")
    until = fields.get("XL_OVERRIDE_UNTIL", "")
    reason = fields.get("XL_OVERRIDE_REASON", "") or "no reason recorded"
    try:
        expiry = dt.date.fromisoformat(until)
    except ValueError:
        return None
    if dt.date.today() > expiry:
        return None
    return f"{reason} (operator override, expires {expiry.isoformat()})"


def xl_load_check(cmd: str) -> "str | None":
    """Reason to postpone an XL window on box load, or None to allow.

    Uses the 1-minute load average against the core count, reserving the ranks
    this command asks for plus a headroom margin. Fails **open** on anything
    unreadable — a guard that cannot measure the box must not become the reason
    no work can run.

    Honest limitation, worth knowing before trusting a refusal: load average is
    a decaying mean and does not distinguish our own load from anyone else's,
    so for a minute or two after one of our own runs ends it will read high and
    postpone the next one. That is the safe direction, and
    ``FEM_EM_XL_IGNORE_LOAD=1`` is the operator's escape hatch when the load is
    known to be our own and decaying.
    """
    raw = os.environ.get(XL_LOAD_OVERRIDE_ENV, "").strip().lower()
    if raw and raw not in ("0", "false", "no", "off"):
        return None
    try:
        with open("/proc/loadavg", encoding="utf-8") as fh:
            load1 = float(fh.read().split()[0])
        ncpu = float(os.cpu_count() or 0)
        if ncpu <= 0:
            return None
    except Exception:
        return None
    m = re.search(r"mpi(?:exec|run)\s+(?:-n|-np)\s+(\d+)", cmd)
    ranks = float(m.group(1)) if m else float(XL_RANK_CEILING)
    free = ncpu - load1
    needed = ranks + XL_LOAD_HEADROOM_CORES
    if free < needed:
        return (
            f"the box is busy: 1-min load {load1:.1f} of {ncpu:.0f} cores leaves "
            f"{free:.1f} free, and this window wants {ranks:.0f} ranks plus "
            f"{XL_LOAD_HEADROOM_CORES:.0f} cores of headroom ({needed:.0f}). An XL "
            "window holds its cores for up to two hours on a shared machine, so it "
            "waits rather than oversubscribing. Re-check `cat /proc/loadavg` and "
            f"start when the load is under {ncpu - needed:.1f}. If the load is our "
            f"own and still decaying, {XL_LOAD_OVERRIDE_ENV}=1 overrides — operator "
            "judgement only, and never to push past somebody else's work."
        )
    return None


def check_xl(cmd: str) -> None:
    """The four XL-tier conditions; deny on the first that fails."""
    if "run_and_log.sh" not in cmd:
        deny(f"Commands against {XL_SERVICE} must go through scripts/testing/run_and_log.sh "
             "(XL tier, PROJECT_PLAN §5.1).")
    timeouts = [int(v) for v in re.findall(r"timeout\s+-k\s+\d+\s+(\d+)", cmd)]
    if not timeouts:
        deny(f"Commands against {XL_SERVICE} must carry `timeout -k 30 <s>` with s <= "
             f"{XL_TIMEOUT_CEILING_S} (XL tier ceiling 2 h).")
    if max(timeouts) > XL_TIMEOUT_CEILING_S:
        deny(f"timeout {max(timeouts)} s exceeds the XL tier ceiling of {XL_TIMEOUT_CEILING_S} s.")
    busy = xl_load_check(cmd)
    if busy is not None:
        deny(f"XL window postponed — {busy}")

    # The load check above measures **this WSL VM only**. Measured 2026-09-09:
    # the operator's Task Manager showed 100% CPU with two solves running while
    # this VM reported load 0.84 and both project containers at 0.00%. There is
    # no way to probe the Windows host from inside the sandbox (no
    # powershell.exe on PATH, /mnt unreadable), so a green load reading is not
    # evidence the box is free and must not be treated as if it were.
    #
    # An XL window holds up to 16 cores for up to two hours, so the one thing
    # that can see the whole machine — the operator — has to say so. This is
    # deliberately a per-run acknowledgement and not a stored setting: the
    # question is "is the box free *now*", and a file cannot answer it.
    if not os.environ.get(XL_BOX_OK_ENV, "").strip():
        deny(
            "XL window needs the box confirmed free. This guard can only see "
            "this WSL VM, and on 2026-09-09 the Windows host was at 100% CPU "
            "with two solves while this VM read load 0.84 and every container "
            "0.00% — so a green load reading here is not evidence of anything. "
            "The host cannot be probed from the sandbox (no powershell.exe, "
            "/mnt unreadable). Run `scripts/testing/box_check.sh` for what is "
            "visible, then look at Task Manager for what is not, and re-run "
            f"with {XL_BOX_OK_ENV}=1 prefixed if the machine is actually free. "
            "An XL window holds up to 16 cores for up to 2 h on a shared box."
        )

    last = last_xl_run()
    if last is not None:
        age = (dt.date.today() - last).days
        if age < XL_INTERVAL_DAYS and xl_interval_override() is None:
            deny(f"The XL slot was used {age} day(s) ago ({last.isoformat()}, {XL_LEDGER.name}); "
                 f"one XL run per {XL_INTERVAL_DAYS} days (operator directive 2026-09-05). "
                 "Shrink the case to the heavy tier or wait for the slot. "
                 f"An operator may authorise an exception in {XL_OVERRIDE.name} "
                 "(dated, self-expiring); a scheduled session may not write one.")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        cmd = payload.get("tool_input", {}).get("command", "") or ""
    except Exception:
        sys.exit(0)  # fail open

    # "Targets the XL service" means an actual exec against it (a compute
    # command), not any mention of its name — heredocs, greps and commit
    # messages that name the service are not XL runs. `--profile xl up/stop`
    # is service lifecycle, not compute, and is not gated either.
    targets_xl = re.search(r"docker\s+compose[^;&|]*\bexec\b[^;&|]*" + re.escape(XL_SERVICE), cmd) is not None

    # Rule 1: rank ceiling, absolute — applies even inside harness commands.
    for m in re.finditer(r"mpi(?:exec|run)\s+(?:-n|-np)\s+(\d+)", cmd):
        n = int(m.group(1))
        if n > RANK_CEILING and not targets_xl:
            deny(
                f"mpiexec -n {n} exceeds the {RANK_CEILING}-rank ceiling for this "
                "project (CLAUDE.md hard rules; shared 36-core box). Use the "
                f"smallest rank count that fits the tier. (Up to {XL_RANK_CEILING} ranks "
                f"exist only in the weekly XL slot against {XL_SERVICE} — PROJECT_PLAN §5.1.)"
            )
        if n > XL_RANK_CEILING:
            deny(f"mpiexec -n {n} exceeds the XL tier's {XL_RANK_CEILING}-rank ceiling.")

    if targets_xl:
        check_xl(cmd)

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
