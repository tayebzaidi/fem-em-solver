"""Shared complex-build gate for tests that run a time-harmonic solve.

Since `TH-1` steps 1–3 the frequency-domain path is an actual complex
curl-curl solve, so it cannot run in the real DolfinX build at all —
``TimeHarmonicSolver.solve`` raises rather than quietly dropping the
imaginary part of ε_c. The `validation` CI job runs real mode, so tests that
solve carry ``@complex_only``; they are exercised by the `validation-complex`
job (`OPS-10`) and by the complex-mode command in
``tests/validation/test_time_harmonic_mms.py``'s module docstring.

``FEM_EM_REQUIRE_COMPLEX=1`` turns the skip into a run (and therefore a loud
failure) so a run that declared itself complex cannot pass by skipping.
"""

from __future__ import annotations

import os

import numpy as np
import pytest
from petsc4py import PETSc

IS_COMPLEX = np.issubdtype(np.dtype(PETSc.ScalarType), np.complexfloating)
REQUIRE_COMPLEX = os.environ.get("FEM_EM_REQUIRE_COMPLEX", "") == "1"

complex_only = pytest.mark.skipif(
    not IS_COMPLEX and not REQUIRE_COMPLEX,
    reason=(
        "time-harmonic solves need the complex DolfinX build "
        f"(this one is {np.dtype(PETSc.ScalarType)}); "
        "source /usr/local/bin/dolfinx-complex-mode"
    ),
)
