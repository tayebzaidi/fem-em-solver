"""`OPS-52`: the `WF-7` F-human cost probe's phase-4 label says what ran.

The probe's phase-4 line was written when the probe had one order and was
emitted unconditionally; step 0b's ``FEM_EM_WF7_DEGREE=2`` knob made it false
without touching it, so the degree-2 leg of
``20260919T070008Z_WF-7-step0b.log:21173`` printed ``phase 4 flag-off
control: ... vs the step-0 record`` over what is the order-sensitivity
readout the window was commissioned for (known-issues, 2026-09-19).

These are string assertions on a pure function plus a source-text negative
control.  Nothing here solves; the probe's own executed anchors (the cell band
and the ``-n 8`` flag-off `S_driven` assert) are unchanged and are exercised by
the probe window, not by this file.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE_REL = "scripts/probes/wf7_step0_f_human_cost.py"


def _load_probe():
    """Import the probe by path (`scripts/` is not a package).

    The probe runs its solve only under ``if __name__ == "__main__"``, so
    importing it is safe — it costs the dolfinx import and reads its env knobs
    at module scope, nothing more.  Verified, not assumed: if that guard ever
    goes, this import would run an F-human mesh build and this test would time
    out rather than pass.
    """
    spec = importlib.util.spec_from_file_location(
        "wf7_step0_f_human_cost_under_test", REPO_ROOT / PROBE_REL
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_probe = _load_probe()
_phase4_label = _probe._phase4_label
S_DRIVEN_STEP0_RECORD = _probe.S_DRIVEN_STEP0_RECORD

# The pinned pre-change commit for the negative control.  A literal sha, never
# ``HEAD:`` — `HEAD` moves with the branch and the identity would evaporate
# (the `test_orphan_guard.sh` trap).
PRE_CHANGE_SHA = "19bed9a9ba60c1ed6373dfc3ac5bf1e460cabc82"

# The two printed values of the 2026-09-19 `xxl` window
# (`20260919T070008Z_WF-7-step0b.log`): degree 2 at `:21173`, degree 1 the
# step-0 record.  The relative move is recomputed here from these strings.
S_DRIVEN_DEGREE2_0919 = "0.436656+0.346994j"

# Scratch for `git show` output: under the gitignored `/logs/`, never `$TMPDIR`.
SCRATCH_DIR = REPO_ROOT / "logs" / "ops52-negative-control"

FLAG_OFF_PHRASE = "phase 4 flag-off control"
_DEGREE1_GUARD = re.compile(r"^(if|elif)\b.*\b(degree|DEGREE) == 1\b")


def _flag_off_outside_degree1(source: str) -> int:
    """Count ``phase 4 flag-off control`` outside any ``degree == 1`` branch.

    Block membership is by indentation: an ``if``/``elif`` statement whose test
    mentions ``degree == 1`` opens a guarded block that ends at the first
    non-blank line indented no further than the guard.  Conditional
    *expressions* mentioning ``DEGREE == 1`` inside a call do not open a
    block — which is exactly the pre-change shape, where the phrase was
    printed unconditionally and only the ``ASSERTED`` word was gated.
    """
    guard_indent: int | None = None
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        if guard_indent is not None and indent <= guard_indent:
            guard_indent = None
        if _DEGREE1_GUARD.match(stripped):
            guard_indent = indent
            continue
        if FLAG_OFF_PHRASE in line and guard_indent is None:
            count += 1
    return count


def test_phase4_label_degree2_is_an_order_readout_not_a_control():
    """At degree 2 the line is the readout, and it never claims a control."""
    label = _phase4_label(2, 16, 1, "P17", S_DRIVEN_DEGREE2_0919)
    assert "order readout" in label, label
    assert "flag-off control" not in label, label
    assert "degree 2" in label, label


def test_phase4_label_degree1_is_the_flag_off_control_and_says_asserted():
    """At degree 1, -n 8, one drive: the control, and it is asserted there."""
    label = _phase4_label(1, 8, 1, "P17", S_DRIVEN_STEP0_RECORD)
    assert "flag-off control" in label, label
    assert "ASSERTED" in label, label
    assert "order readout" not in label, label


def test_phase4_label_degree1_off_record_width_says_printed_only():
    label = _phase4_label(1, 16, 1, "P17", S_DRIVEN_STEP0_RECORD)
    assert "flag-off control" in label, label
    assert "printed only" in label, label
    assert "ASSERTED" not in label, label


def test_phase4_label_prints_the_0919_relative_move_to_two_decimals():
    """5.50 % on the two printed values of the 2026-09-19 window.

    Recomputed here, not copied: |S_2 - S_1| / |S_1| with
    S_2 = 0.436656+0.346994j (`:21173`) and S_1 = the step-0 record.
    """
    s2 = complex(S_DRIVEN_DEGREE2_0919)
    s1 = complex(S_DRIVEN_STEP0_RECORD)
    move_pct = abs(s2 - s1) / abs(s1) * 100.0
    assert move_pct == pytest.approx(5.50, abs=0.005), move_pct
    label = _phase4_label(2, 16, 1, "P17", S_DRIVEN_DEGREE2_0919)
    print(f"[OPS-52] recomputed relative move {move_pct:.4f} % ; label: {label}")
    assert "5.50 %" in label, label


def test_flag_off_phrase_left_the_ungated_path_negative_control():
    """Source-text identity: 1 occurrence at the pinned sha, 0 in the tree.

    The pre-change file has no ``_phase4_label`` to import, so the control is
    on the text: the phrase was emitted outside any ``degree == 1`` branch
    exactly once, and is emitted outside one zero times now.
    """
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    scratch = SCRATCH_DIR / f"{PRE_CHANGE_SHA[:8]}_wf7_step0_f_human_cost.py"
    blob = subprocess.run(
        # `-c safe.directory` because the container runs as a different uid
        # than the bind-mounted checkout's owner: without it git refuses with
        # "detected dubious ownership" (measured 2026-09-19, `OPS-52`).
        ["git", "-c", f"safe.directory={REPO_ROOT}", "show",
         f"{PRE_CHANGE_SHA}:{PROBE_REL}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    scratch.write_text(blob)

    before = _flag_off_outside_degree1(scratch.read_text())
    after = _flag_off_outside_degree1((REPO_ROOT / PROBE_REL).read_text())
    print(f"[OPS-52] negative control: ungated '{FLAG_OFF_PHRASE}' "
          f"{before} at {PRE_CHANGE_SHA[:8]} -> {after} in the working tree")
    assert (before, after) == (1, 0), (before, after)
