"""Runtime path compatibility for container test commands.

The chunk test commands in ``PROJECT_PLAN.md`` set ``PYTHONPATH=/workspace/src``,
which *replaces* the DolfinX path configured by the container environment. This
module re-appends the correct one.

Which one is correct depends on the active DolfinX build. The dolfinx images ship
both a real and a complex PETSc build and switch between them with
``source /usr/local/bin/dolfinx-{real,complex}-mode``, which exports::

    PETSC_ARCH=linux-gnu-real64-32       (real)
    PETSC_ARCH=linux-gnu-complex128-32   (complex)
    PYTHONPATH=/usr/local/dolfinx-<mode>/lib/python<X.Y>/dist-packages:$PYTHONPATH
    LD_LIBRARY_PATH=/usr/local/dolfinx-<mode>/lib:$LD_LIBRARY_PATH

Only ``PYTHONPATH`` is lost to the inline assignment; ``LD_LIBRARY_PATH`` and
``PETSC_ARCH`` survive. So ``PETSC_ARCH`` is a reliable signal for which
dist-packages directory to restore.

An earlier version hardcoded the *real* path and Python 3.10. Under complex mode
that silently handed back a real-scalar DolfinX -- a frequency-domain solve would
have assembled with real scalars and produced quietly wrong results rather than
failing. Relevant to TH-1.
"""

from __future__ import annotations

import os
import sys

_PY_TAG = f"python{sys.version_info[0]}.{sys.version_info[1]}"


def _dolfinx_mode() -> str:
    """Return 'complex' or 'real' based on the active PETSc arch."""
    return "complex" if "complex" in os.environ.get("PETSC_ARCH", "").lower() else "real"


def _candidate_paths() -> list[str]:
    """DolfinX dist-packages for the active mode, then the shared lib dir."""
    mode = _dolfinx_mode()
    paths = [
        f"/usr/local/dolfinx-{mode}/lib/{_PY_TAG}/dist-packages",
        # Fall back to the other build only if the preferred one is absent, so a
        # missing complex install surfaces as a scalar-type mismatch rather than
        # an ImportError with no explanation.
        f"/usr/local/dolfinx-{'real' if mode == 'complex' else 'complex'}"
        f"/lib/{_PY_TAG}/dist-packages",
        "/usr/local/lib",
    ]
    return paths


for _path in _candidate_paths():
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.append(_path)
