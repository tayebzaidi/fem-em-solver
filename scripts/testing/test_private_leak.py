#!/usr/bin/env python3
"""Positive and negative controls for `check_private_leak.py` (OPS-58).

Script-style, like `test_tier_guard.py`: host-side, no container, stdlib only.

    python3 scripts/testing/test_private_leak.py

Builds scratch git repositories under $TMPDIR with a **synthetic** reference
figure — never a value from docs/private/ or aed_results/ — and asserts the
checker's exit codes exactly:

    planted figure staged                 -> 1
    planted figure in the commit message  -> 1
    a truncated spelling in the message   -> 1
    the figure on a '#' comment line only -> 0 (git strips those)
    clean staged change                   -> 0, prints "clean:"
    no reference data                     -> 0, prints "SKIPPED"
    broken git                            -> 2, prints "could not inspect:"
    installed commit-msg hook, plant      -> the commit is refused

plus the pre-change control: the checker and hook installer pinned at
PRECHANGE_SHA (the commit before OPS-58) *pass* the message plant and the
broken-git case, which is the defect this chunk fixes. Exit 0 iff every
assertion holds.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "testing" / "check_private_leak.py"
INSTALLER = ROOT / "scripts" / "testing" / "install_git_hooks.sh"
PRECHANGE_SHA = "bef049382da0258fa111636d7e8d1f807dd2c490"

# Synthetic: invented for this test, no provenance. 10 significant digits,
# 9 distinct, so it is "informative" under the checker's rules.
FIGURE = "0.7351928464"
TRUNCATED = "0.73519284"          # 8 significant digits: the minimum length
SECRET_GLOB = "examples/ansys_benchmarks/*/aed_results/*"

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
}

failures: list[str] = []
table: list[tuple[str, int, int]] = []


def env(**extra) -> dict:
    e = dict(os.environ)
    for k in ("PRIVATE_LEAK_ROOT", "PRIVATE_LEAK_SECRET_GLOBS", "GIT_DIR",
              "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        e.pop(k, None)
    e.update(GIT_ENV)
    e.update(extra)
    return e


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], env=env(),
                          check=True, capture_output=True, text=True)


def make_repo(base: Path, name: str, with_reference: bool = True) -> Path:
    repo = base / name
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / ".gitignore").write_text("aed_results/\n")
    (repo / "README.md").write_text("scratch repo, round numbers only: 50 2026 1e-3\n")
    git(repo, "add", ".gitignore", "README.md")
    git(repo, "commit", "-q", "-m", "init")
    if with_reference:
        ref = repo / "examples" / "ansys_benchmarks" / "case" / "aed_results"
        ref.mkdir(parents=True)
        (ref / "export.csv").write_text(f"freq_hz,s11_re\n64000000,{FIGURE}\n")
    return repo


def run_checker(script: Path, repo: Path, *args: str, path_prefix: str = "",
                overrides: bool = True) -> subprocess.CompletedProcess:
    extra = {}
    if overrides:
        extra = {"PRIVATE_LEAK_ROOT": str(repo), "PRIVATE_LEAK_SECRET_GLOBS": SECRET_GLOB}
    if path_prefix:
        extra["PATH"] = path_prefix + os.pathsep + os.environ.get("PATH", "")
    return subprocess.run([sys.executable, str(script), *args], cwd=repo,
                          env=env(**extra), capture_output=True, text=True, timeout=20)


def expect(label: str, proc: subprocess.CompletedProcess, code: int,
           needle: str | None = None, forbid_figure: bool = True) -> None:
    out = proc.stdout + proc.stderr
    table.append((label, code, proc.returncode))
    ok = proc.returncode == code and (needle is None or needle in out)
    # The committed checker prints locations, never the figure (its output
    # lands in logs). The pre-change one printed it; not asserted there.
    if forbid_figure and (FIGURE[2:] in out or TRUNCATED[2:] in out):
        ok = False
        out += "\n[test] the checker printed the figure itself"
    print(f"{'PASS' if ok else 'FAIL'}  {label:58} expected {code}, got {proc.returncode}"
          + (f"  [{needle!r} {'present' if needle in out else 'ABSENT'}]" if needle else ""))
    if not ok:
        failures.append(label)
        print("      | " + out.strip().replace("\n", "\n      | "))


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="ops58_"))
    try:
        fake = base / "fakebin"
        fake.mkdir()
        (fake / "git").write_text("#!/bin/sh\necho 'fatal: simulated git failure' >&2\nexit 128\n")
        (fake / "git").chmod(0o755)

        prechange = base / "check_private_leak_prechange.py"
        prechange.write_text(subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{PRECHANGE_SHA}:scripts/testing/check_private_leak.py"],
            check=True, capture_output=True, text=True).stdout)

        print("== committed checker ==")
        repo = make_repo(base, "staged")
        (repo / "notes.md").write_text(f"s11 came out at {FIGURE} here\n")
        git(repo, "add", "notes.md")
        expect("planted figure staged", run_checker(CHECKER, repo), 1, "BLOCKED")

        repo = make_repo(base, "message")
        msg = repo / "MSG"
        msg.write_text(f"fix: tune\n\nS11 matched AED ({FIGURE}).\n")
        expect("planted figure in the message", run_checker(CHECKER, repo, "--message-file", str(msg)), 1, "BLOCKED")
        msg.write_text(f"fix: tune\n\nS11 matched AED ({TRUNCATED}).\n")
        expect("truncated spelling in the message", run_checker(CHECKER, repo, "--message-file", str(msg)), 1, "BLOCKED")
        msg.write_text(f"fix: tune\n# {FIGURE} on a comment line git strips\n")
        expect("figure only on a '#' comment line", run_checker(CHECKER, repo, "--message-file", str(msg)), 0, "clean:")
        expect("missing message file", run_checker(CHECKER, repo, "--message-file", str(repo / "nope")), 2, "could not inspect:")

        repo = make_repo(base, "clean")
        (repo / "notes.md").write_text("pi is 3.14159265 and that is ours\n")
        git(repo, "add", "notes.md")
        expect("clean staged change", run_checker(CHECKER, repo), 0, "clean:")

        repo = make_repo(base, "noref", with_reference=False)
        (repo / "notes.md").write_text(f"s11 came out at {FIGURE} here\n")
        git(repo, "add", "notes.md")
        expect("no reference data", run_checker(CHECKER, repo), 0,
               "SKIPPED: no reference data on this machine; nothing was checked")

        repo = make_repo(base, "brokengit")
        (repo / "notes.md").write_text(f"s11 came out at {FIGURE} here\n")
        git(repo, "add", "notes.md")
        expect("broken git (hook mode)", run_checker(CHECKER, repo, path_prefix=str(fake)), 2, "could not inspect:")
        expect("broken git (--audit)", run_checker(CHECKER, repo, "--audit", path_prefix=str(fake)), 2, "could not inspect:")

        repo = make_repo(base, "audit")
        git(repo, "commit", "-q", "--allow-empty", "-m", f"old commit quoting {FIGURE}")
        expect("--audit finds a figure in history", run_checker(CHECKER, repo, "--audit"), 1, "commit ")
        repo = make_repo(base, "auditclean")
        expect("--audit on a clean history", run_checker(CHECKER, repo, "--audit"), 0, "clean:")

        print("\n== installed hooks, end to end (a scratch clone laid out like this one) ==")
        for label, checker_src, installer_src, code in (
                ("committed hooks refuse the message plant", CHECKER.read_text(), INSTALLER.read_text(), 1),
                ("PRE-CHANGE hooks accept the message plant (control)", prechange.read_text(),
                 subprocess.run(["git", "-C", str(ROOT), "show",
                                 f"{PRECHANGE_SHA}:scripts/testing/install_git_hooks.sh"],
                                check=True, capture_output=True, text=True).stdout, 0)):
            repo = make_repo(base, "hooks_" + str(code))
            tdir = repo / "scripts" / "testing"
            tdir.mkdir(parents=True)
            (tdir / "check_private_leak.py").write_text(checker_src)
            (tdir / "install_git_hooks.sh").write_text(installer_src)
            (tdir / "install_git_hooks.sh").chmod(0o755)
            git(repo, "add", "scripts")
            git(repo, "commit", "-q", "--no-verify", "-m", "add the checker")
            subprocess.run([str(tdir / "install_git_hooks.sh")], env=env(), check=True,
                           capture_output=True, text=True)
            (repo / "notes.md").write_text("an honest change\n")
            git(repo, "add", "notes.md")
            proc = subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m",
                                   f"fix: S11 matched AED ({FIGURE})"],
                                  env=env(), capture_output=True, text=True, timeout=30)
            expect(label, proc, code)

        print("\n== pre-change control: the checker pinned at "
              f"{PRECHANGE_SHA[:7]} (the defects OPS-58 fixes) ==")
        repo = make_repo(base, "pre_broken")
        (repo / "scripts" / "testing").mkdir(parents=True)
        pre = repo / "scripts" / "testing" / "check_private_leak.py"
        shutil.copy(prechange, pre)   # its ROOT is parents[2] of its own path
        (repo / "notes.md").write_text(f"s11 came out at {FIGURE} here\n")
        git(repo, "add", "notes.md")
        expect("PRE-CHANGE planted figure staged (still caught)",
               run_checker(pre, repo, overrides=False), 1, "BLOCKED", forbid_figure=False)
        expect("PRE-CHANGE broken git reads as a pass (control)",
               run_checker(pre, repo, path_prefix=str(fake), overrides=False), 0)
        repo2 = make_repo(base, "pre_noref", with_reference=False)
        (repo2 / "scripts" / "testing").mkdir(parents=True)
        pre2 = repo2 / "scripts" / "testing" / "check_private_leak.py"
        shutil.copy(prechange, pre2)
        proc = run_checker(pre2, repo2, overrides=False)
        expect("PRE-CHANGE no reference data is silent (control)", proc, 0)
        if proc.stdout.strip():
            failures.append("pre-change no-reference output was not silent")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print("\nexit-code table (case, expected, measured):")
    for label, want, got in table:
        print(f"  {label:58} {want}  {got}")
    print(f"\n{len(table) - len(failures)}/{len(table)} cases as asserted")
    if failures:
        print("FAILED: " + "; ".join(failures))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
