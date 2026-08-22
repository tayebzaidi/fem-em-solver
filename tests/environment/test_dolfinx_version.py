"""Environment gate: the adopted DolfinX version and its path plumbing (`OPS-18` step 1).

`OPS-18` is the recurring version-upgrade chunk. Its step-1 done-when is that the
container boots the *adopted* release and that both scalar builds resolve, under
``mpiexec -n 2``, through the same `PYTHONPATH` the compose file hands the chunk
commands.

Why this needs its own file rather than a line in ``test_complex_mode.py``: the
things an upgrade breaks are version-*encoded paths*, not physics. Between 0.7.2
and 0.11.0 the image's interpreter moved 3.10 → 3.12, so the compose
``PYTHONPATH`` literal
(``/usr/local/dolfinx-<mode>/lib/python<X.Y>/dist-packages``) silently stopped
pointing at anything. That failure mode is quiet in the worst way — the path just
drops off ``sys.path`` and ``import dolfinx`` either fails with no explanation or,
if some other copy is importable, hands back the *wrong build*. The assertions
below pin the version, the build, and the interpreter tag against each other so a
future bump cannot boot a mismatched trio unnoticed.

Run both legs through the harness::

    # real
    docker compose exec -T fem-em-solver bash -lc \\
      'cd /workspace && PYTHONPATH=/workspace/src mpiexec -n 2 \\
       python3 -m pytest tests/environment -v'
    # complex
    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 mpiexec -n 2 \\
       python3 -m pytest tests/environment -v'
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest
from mpi4py import MPI
from petsc4py import PETSc

import dolfinx

# The version this pass of `OPS-18` adopted. Bump it in the same commit that
# bumps docker/Dockerfile's FROM line; the two are one fact in two files.
#
# Upstream's newest at the 2026-08-18 release check was ``v0.11.0.post0``, which
# is what the lag policy qualified on. The *image* tag and the *version string*
# differ here and both were measured, 2026-08-22:
#   - ``dolfinx/dolfinx:v0.11.0.post0`` does not exist on Docker Hub
#     ("failed to resolve source metadata ... not found"); the published tag is
#     ``dolfinx/dolfinx:v0.11.0``.
#   - that image nevertheless reports ``dolfinx.__version__ == "0.11.0.post0"``
#     (log 20260822T093912Z_OPS-18-step1-real, which failed against a first
#     guess of "0.11.0" — this constant follows the measurement).
# So the adopted release *is* the qualifying ``.post0``; only the tag is shorter.
EXPECTED_DOLFINX_VERSION = "0.11.0.post0"

IS_COMPLEX = np.issubdtype(np.dtype(PETSc.ScalarType), np.complexfloating)
REQUIRE_COMPLEX = os.environ.get("FEM_EM_REQUIRE_COMPLEX", "") == "1"

complex_only = pytest.mark.skipif(
    not IS_COMPLEX and not REQUIRE_COMPLEX,
    reason=f"real-mode build ({np.dtype(PETSc.ScalarType)})",
)


def _require_complex() -> None:
    """Fail (not skip) when the run declared itself complex but the build is real."""
    if not IS_COMPLEX:
        raise AssertionError(
            "FEM_EM_REQUIRE_COMPLEX=1 but PETSc.ScalarType is "
            f"{np.dtype(PETSc.ScalarType)} and dolfinx resolved to "
            f"{dolfinx.__file__} — the complex build was not picked up."
        )


@pytest.mark.integration
def test_adopted_dolfinx_version_is_exact():
    """The running dolfinx reports exactly the adopted release.

    Asserts in both modes. A container still on the previous image, or one where
    a stale wheel shadows the image's install, fails here rather than three
    chunks downstream.
    """
    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[OPS-18 step 1] dolfinx={dolfinx.__version__} "
            f"file={dolfinx.__file__} python={sys.version.split()[0]} "
            f"ScalarType={np.dtype(PETSc.ScalarType)}"
        )
    assert dolfinx.__version__ == EXPECTED_DOLFINX_VERSION, (
        f"container reports dolfinx {dolfinx.__version__}, expected "
        f"{EXPECTED_DOLFINX_VERSION}"
    )


@pytest.mark.integration
def test_resolved_dolfinx_path_matches_mode_and_interpreter():
    """The imported dolfinx lives under the *active* build and the *running* Python.

    This is the direct gate on the compose ``PYTHONPATH`` literal: the path
    carries both a build name (``dolfinx-real`` / ``dolfinx-complex``) and an
    interpreter tag (``python3.12``), and an upgrade can move either. Deriving
    the expected tag from ``sys.version_info`` rather than restating it means the
    test cannot agree with a stale literal.
    """
    expected_mode = "complex" if IS_COMPLEX else "real"
    py_tag = f"python{sys.version_info[0]}.{sys.version_info[1]}"
    resolved = dolfinx.__file__

    if MPI.COMM_WORLD.rank == 0:
        print(f"[OPS-18 step 1] expect /dolfinx-{expected_mode}/ and /{py_tag}/ in {resolved}")

    assert f"/dolfinx-{expected_mode}/" in resolved, (
        f"PETSc.ScalarType is {np.dtype(PETSc.ScalarType)} (mode {expected_mode}) "
        f"but dolfinx was imported from {resolved}"
    )
    assert f"/{py_tag}/" in resolved, (
        f"running {py_tag} but dolfinx was imported from {resolved} — the "
        "PYTHONPATH interpreter tag is stale (compose file / mode wrapper)"
    )


@pytest.mark.integration
def test_h5py_built_against_the_image_hdf5():
    """The from-source h5py in docker/Dockerfile matches the image's HDF5.

    The whole reason that build is ``--no-binary=h5py`` is that a wheel's bundled
    HDF5 diverges from the one dolfinx's I/O links, and the mismatch surfaces as
    a corrupt/unreadable XDMF far from its cause. h5py itself raises on a
    major/minor mismatch at import; the equality below also catches a patch-level
    divergence, which it tolerates.
    """
    import h5py

    built, linked = h5py.version.hdf5_built_version_tuple, h5py.version.hdf5_version_tuple
    if MPI.COMM_WORLD.rank == 0:
        print(f"[OPS-18 step 1] h5py={h5py.version.version} built={built} linked={linked}")
    assert built == linked, (
        f"h5py was built against HDF5 {built} but links {linked} — the "
        "--no-binary=h5py build in docker/Dockerfile did not take"
    )


@complex_only
@pytest.mark.integration
def test_complex_build_is_complex128():
    """In a run declaring itself complex, the scalar type is exactly complex128.

    The negative control for step 1: run this file in **real** mode with
    ``FEM_EM_REQUIRE_COMPLEX=1`` and it must fail here, not skip. That is what
    keeps the complex leg from passing vacuously on a container where the
    complex build never resolved.
    """
    _require_complex()
    assert np.dtype(PETSc.ScalarType) == np.dtype(np.complex128)
    assert "complex" in os.environ.get("PETSC_ARCH", "").lower()
