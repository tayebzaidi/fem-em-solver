"""Environment gate: the pinned ``scikit-rf`` in the image (`OPS-60`).

`PORT-23` moves the circuit layer (termination / cascade / renormalisation of
the field-derived N-port) onto ``scikit-rf``, gated against the raw (C2)
reduction in ``ports/circuit.py``. The library's wave and port-order
conventions are exactly the class of fact a silent version bump can move
(`PORT-20` was a convention bug), so the version is pinned in
``docker/Dockerfile`` and asserted here — the `OPS-18` pattern of
``test_dolfinx_version.py``.

The pin was read from PyPI at execution (2026-09-21, ``pip index versions
scikit-rf`` inside the container, log
``20260921T093027Z_OPS-60-version-probe.log``): newest release 2.1.0.

Negative control: on an image built before `OPS-60` the import fails
(``ModuleNotFoundError``) and this test fails — it does not skip.

Run through the harness::

    docker compose exec -T fem-em-solver bash -lc \\
      'cd /workspace && PYTHONPATH=/workspace/src mpiexec -n 1 \\
       python3 -m pytest tests/environment/test_scikit_rf_version.py -v -s'
"""

from __future__ import annotations

import pytest

# Bump in the same commit that bumps docker/Dockerfile's ``scikit-rf==`` pin;
# the two are one fact in two files.
EXPECTED_SKRF_VERSION = "2.1.0"


@pytest.mark.integration
def test_pinned_scikit_rf_version_is_exact():
    """``import skrf`` succeeds and reports exactly the pinned release."""
    import skrf

    print(f"\n[OPS-60] skrf={skrf.__version__} file={skrf.__file__}")
    assert skrf.__version__ == EXPECTED_SKRF_VERSION, (
        f"container reports scikit-rf {skrf.__version__}, expected "
        f"{EXPECTED_SKRF_VERSION} (docker/Dockerfile pin)"
    )
