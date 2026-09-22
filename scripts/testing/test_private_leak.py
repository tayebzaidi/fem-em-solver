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

plus the **shared-input allowlist** controls (OPS-58, operator ruling
2026-09-21). The allowlist must suppress exactly its one named site and
blind the checker to nothing else:

    allowlisted site alone                -> 0, "clean:" AND the suppression
                                             is reported, never silent
    a genuine (synthetic) AED *output*
      alongside it                        -> 1, still BLOCKED
    the same value in another file        -> 1
    the same value under another key      -> 1
    every entry reproduces from its
      published closed form               -> asserted in-process

plus the pre-change control: the checker and hook installer pinned at
PRECHANGE_SHA (the commit before OPS-58) *pass* the message plant and the
broken-git case, which is the defect this chunk fixes. Exit 0 iff every
assertion holds.
"""
from __future__ import annotations

import importlib.util
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
# Stands in for a genuine AED *output* in the allowlist controls: synthetic,
# invented here, reproducible from nothing.
OUTPUT_FIGURE = "0.4182736509"
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


def expect_text(label: str, proc: subprocess.CompletedProcess, needle: str) -> None:
    """A content assertion on output whose exit code another case pinned."""
    out = proc.stdout + proc.stderr
    ok = needle in out
    table.append((label, 1, int(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label:58} {needle!r} "
          f"{'present' if ok else 'ABSENT'}")
    if not ok:
        failures.append(label)
        print("      | " + out.strip().replace("\n", "\n      | "))


def load_checker():
    """Import the checker as a module, to read SHARED_INPUTS directly."""
    spec = importlib.util.spec_from_file_location("check_private_leak", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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

        print("\n== shared-input allowlist (OPS-58 operator ruling 2026-09-21) ==")
        checker = load_checker()
        entry = checker.SHARED_INPUTS[0]
        value = repr(entry["compute"]())
        # (1) Every entry must be a shared *input*: reproducible, bit for bit,
        # from geometry the repo already publishes, and already published
        # itself. An AED output can satisfy neither, which is what keeps the
        # tracked allowlist safe. The cited source must be a tracked file and
        # must carry the value to the precision it publishes it at.
        for e in checker.SHARED_INPUTS:
            label = f"allowlist entry reproduces from {e['closed_form']}"
            value = e["compute"]()
            src = ROOT / e["published_in"].split(":")[0]
            cited = src.is_file()
            published = cited and f"{value:.6e}" in src.read_text()
            good = bool(e["reason"].strip()) and cited and published
            table.append((label, 1, int(good)))
            print(f"{'PASS' if good else 'FAIL'}  {label:58} "
                  f"cited source {'tracked' if cited else 'MISSING'}, "
                  f"value {'published there' if published else 'NOT PUBLISHED'}")
            if not good:
                failures.append(label)

        def allowlist_repo(name: str) -> Path:
            """A scratch repo reproducing the allowlisted site exactly.

            The reference export holds the allowlisted value (as the raw AED
            export does — AED echoes its input back) and, separately, a
            synthetic figure standing in for a genuine AED output.
            """
            repo = make_repo(base, name)
            ref = repo / "examples/ansys_benchmarks/case/aed_results/export.csv"
            ref.write_text(f"volume,{value}\nsomething,{OUTPUT_FIGURE}\n")
            site = repo / entry["path"]
            site.parent.mkdir(parents=True, exist_ok=True)
            site.write_text('{\n  "%s": %s\n}\n' % (entry["key"], value))
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "--no-verify", "-m", "the shared input")
            return repo

        repo = allowlist_repo("allow_clean")
        proc = run_checker(CHECKER, repo, "--audit")
        expect("allowlisted shared input alone", proc, 0, "clean:")
        expect_text("the suppression is reported, never silent", proc,
                    "1 shared-input match suppressed")
        expect_text("the suppression names the site, not the figure", proc,
                    entry["key"])

        repo = allowlist_repo("allow_output")
        (repo / "notes.md").write_text(f"AED reported {OUTPUT_FIGURE} for this port\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "--no-verify", "-m", "a genuine output")
        proc = run_checker(CHECKER, repo, "--audit")
        expect("a genuine AED output beside it is still flagged", proc, 1, "BLOCKED")
        expect_text("...and the suppression is still reported", proc,
                    "1 shared-input match suppressed")

        repo = allowlist_repo("allow_otherfile")
        (repo / "notes.md").write_text(
            '  "%s": %s\n' % (entry["key"], value))
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "--no-verify", "-m", "same value, another file")
        expect("the same value in another file is NOT suppressed",
               run_checker(CHECKER, repo, "--audit"), 1, "BLOCKED")

        repo = allowlist_repo("allow_otherkey")
        site = repo / entry["path"]
        site.write_text('{\n  "%s": %s,\n  "peak_sar_1g_w_per_kg": %s\n}\n'
                        % (entry["key"], value, value))
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "--no-verify", "-m", "same value, another key")
        expect("the same value under another key is NOT suppressed",
               run_checker(CHECKER, repo, "--audit"), 1, "BLOCKED")

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
