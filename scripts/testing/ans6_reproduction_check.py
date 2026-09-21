"""`ANS-6` step 2 control: the unset `ans:6` run reproduces the tracked S.

Usage (repo root, after an unset `ans:6` run has rewritten metrics.json):

    git show <ref>:examples/ansys_benchmarks/ans6_copper_birdcage_four_port_10_64_128MHz/metrics.json > ref.json
    python3 scripts/testing/ans6_reproduction_check.py ref.json

Compares every S leaf (re and im of every entry, both columns, all three
frequencies) of the working-tree ``metrics.json`` against the reference file,
relative to the entry's modulus, and ASSERTS the worst against the imported
``LEG_D0_REPRODUCTION_BAND`` (1e-9; never ``EXACT_IDENTITY_RTOL``, §9 item 23).
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    LEG_D0_REPRODUCTION_BAND,
)

CASE = REPO / "examples/ansys_benchmarks/ans6_copper_birdcage_four_port_10_64_128MHz"


def main(ref_path: str) -> None:
    ref = json.loads(Path(ref_path).read_text())
    new = json.loads((CASE / "metrics.json").read_text())
    worst, where, n = 0.0, None, 0
    for label, rung in ref["rungs"].items():
        for col in ("cu", "pec"):
            a = rung[col]["s_matrix"]
            b = new["rungs"][label][col]["s_matrix"]
            for i, row in enumerate(a):
                for j, e in enumerate(row):
                    za = complex(e["re"], e["im"])
                    zb = complex(b[i][j]["re"], b[i][j]["im"])
                    rel = abs(zb - za) / abs(za)
                    n += 1
                    if rel > worst:
                        worst, where = rel, (label, col, i + 1, j + 1)
    print(f"[ANS-6 step 2] control: {n} S leaves at -n {new['mpi_ranks']} vs reference "
          f"(-n {ref['mpi_ranks']}); worst relative deviation {worst:.3e} at {where} "
          f"(ASSERTED <= LEG_D0_REPRODUCTION_BAND {LEG_D0_REPRODUCTION_BAND:.0e})", flush=True)
    assert worst <= LEG_D0_REPRODUCTION_BAND, (worst, where)
    print("[ANS-6 step 2] control PASS", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
