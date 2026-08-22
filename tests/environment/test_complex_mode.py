"""Environment gate: complex-scalar DolfinX (`TH-1` plan, step 0).

A frequency-domain Maxwell solve cannot be assembled in real mode, and the
failure is silent: with a real `PETSc.ScalarType` the imaginary part of
``ε_c = εᵣ − jσ/(ωε₀)`` is discarded and the solve returns quietly wrong
fields rather than raising. §5.3 therefore makes the environment its own
logged chunk — environment failures must not masquerade as formulation
failures.

The container carries both builds and switches with
``source /usr/local/bin/dolfinx-{real,complex}-mode``. The chunk commands set
``PYTHONPATH=/workspace/src``, which drops the container's dolfinx path;
``src/sitecustomize.py`` restores the one matching ``PETSC_ARCH``. This file
gates that whole path end to end.

Run in complex mode as::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       mpiexec -n 2 python3 -m pytest tests/environment -v'

``FEM_EM_REQUIRE_COMPLEX=1`` turns the real-mode skips into failures, so a
run that was *meant* to exercise complex mode cannot pass by skipping.
In real mode (the default, and what the `validation` CI job runs) the
consistency test below still asserts, and the complex-only tests skip. The
`validation-complex` job (`OPS-10`) runs this file the other way, under
``FEM_EM_REQUIRE_COMPLEX=1``.
"""

from __future__ import annotations

import os

import numpy as np
import pytest
import ufl
from mpi4py import MPI
from petsc4py import PETSc

import dolfinx
from dolfinx import fem, mesh as dmesh
from dolfinx.fem.petsc import assemble_matrix

IS_COMPLEX = np.issubdtype(np.dtype(PETSc.ScalarType), np.complexfloating)
REQUIRE_COMPLEX = os.environ.get("FEM_EM_REQUIRE_COMPLEX", "") == "1"

# Skip the complex-only tests in real mode, unless the run declared itself
# complex — then they run and fail loudly via _require_complex().
complex_only = pytest.mark.skipif(
    not IS_COMPLEX and not REQUIRE_COMPLEX,
    reason=f"real-mode build ({np.dtype(PETSc.ScalarType)})",
)


def _require_complex() -> None:
    """Fail (not skip) when the run was declared complex but the build is real."""
    if not IS_COMPLEX:
        raise AssertionError(
            "FEM_EM_REQUIRE_COMPLEX=1 but PETSc.ScalarType is "
            f"{np.dtype(PETSc.ScalarType)} and dolfinx resolved to "
            f"{dolfinx.__file__} — the complex build was not picked up."
        )


@pytest.mark.integration
def test_scalar_type_matches_active_dolfinx_build():
    """``PETSc.ScalarType``, ``PETSC_ARCH`` and the imported dolfinx agree.

    Asserts in both modes: the failure this guards is a *mismatch* — a complex
    ``PETSC_ARCH`` with a real dolfinx handed back by the sitecustomize shim,
    which is exactly what the earlier hardcoded-path version of that shim did.
    """
    arch = os.environ.get("PETSC_ARCH", "")
    expected_complex = "complex" in arch.lower()
    dolfinx_build = "complex" if "/dolfinx-complex/" in dolfinx.__file__ else "real"

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[TH-1 step 0] PETSC_ARCH={arch!r} ScalarType="
            f"{np.dtype(PETSc.ScalarType)} dolfinx={dolfinx.__file__} "
            f"version={dolfinx.__version__}"
        )

    assert IS_COMPLEX == expected_complex, (
        f"PETSC_ARCH={arch!r} implies complex={expected_complex} but "
        f"PETSc.ScalarType is {np.dtype(PETSc.ScalarType)}"
    )
    assert dolfinx_build == ("complex" if IS_COMPLEX else "real"), (
        f"scalar type is {np.dtype(PETSc.ScalarType)} but dolfinx was imported "
        f"from {dolfinx.__file__}"
    )
    if IS_COMPLEX:
        assert np.dtype(PETSc.ScalarType) == np.dtype(np.complex128)


@complex_only
@pytest.mark.integration
def test_complex_constant_assembles_to_closed_form():
    """``∫_Ω c dx`` over the unit cube equals ``c`` for complex ``c``."""
    _require_complex()
    comm = MPI.COMM_WORLD
    msh = dmesh.create_unit_cube(comm, 2, 2, 2)
    c = 2.0 - 3.0j
    const = fem.Constant(msh, PETSc.ScalarType(c))

    # assemble_scalar is rank-local; reduce before asserting.
    local = fem.assemble_scalar(fem.form(const * ufl.dx))
    total = comm.allreduce(local, op=MPI.SUM)

    assert abs(total - c) < 1e-13, f"∫c dx = {total}, expected {c}"


@complex_only
@pytest.mark.integration
def test_inner_conjugates_second_argument_but_dot_does_not():
    """Pin the `TH-1` sign-convention trap with two closed-form integrals.

    ``ufl.inner(f, g)`` is sesquilinear in complex mode — it conjugates ``g``
    — while ``ufl.dot`` is bilinear. With ``f = 1+2j`` and ``g = 3+4j``
    (both along x̂) over the unit cube::

        ∫ inner(f, g) dx = (1+2j)(3−4j) = 11 + 2j
        ∫ dot(f, g)   dx = (1+2j)(3+4j) = −5 + 10j

    Using ``dot`` for the `TH-1` load term instead of ``inner`` silently flips
    the e^{+jωt} convention; these numbers are how that gets caught.
    """
    _require_complex()
    comm = MPI.COMM_WORLD
    msh = dmesh.create_unit_cube(comm, 2, 2, 2)
    f = fem.Constant(msh, np.array([1.0 + 2.0j, 0.0, 0.0], dtype=PETSc.ScalarType))
    g = fem.Constant(msh, np.array([3.0 + 4.0j, 0.0, 0.0], dtype=PETSc.ScalarType))

    inner_total = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(f, g) * ufl.dx)), op=MPI.SUM
    )
    dot_total = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.dot(f, g) * ufl.dx)), op=MPI.SUM
    )

    if comm.rank == 0:
        print(f"[TH-1 step 0] inner={inner_total} dot={dot_total}")

    assert abs(inner_total - (11.0 + 2.0j)) < 1e-13, f"inner gave {inner_total}"
    assert abs(dot_total - (-5.0 + 10.0j)) < 1e-13, f"dot gave {dot_total}"


@complex_only
@pytest.mark.integration
def test_complex_weighted_n1curl_mass_matrix_scales_exactly():
    """``∫ ε_c u·v̄ dx`` assembles to ``ε_c`` times the real N1curl mass matrix.

    The N1curl basis is real, so the ε_c-weighted matrix must equal the plain
    mass matrix scaled by ε_c entry for entry. This is the smallest check that
    complex coefficients survive the whole assembly path (form compilation,
    kernel, PETSc matrix) with the right dtype, on the element family `TH-1`
    actually uses.
    """
    _require_complex()
    comm = MPI.COMM_WORLD
    msh = dmesh.create_unit_cube(comm, 2, 2, 2)
    V = fem.functionspace(msh, ("N1curl", 1))
    u, v = ufl.TrialFunction(V), ufl.TestFunction(V)

    eps_c = 1.0 - 3.0j
    eps = fem.Constant(msh, PETSc.ScalarType(eps_c))

    mass = assemble_matrix(fem.form(ufl.inner(u, v) * ufl.dx))
    mass.assemble()
    weighted = assemble_matrix(fem.form(eps * ufl.inner(u, v) * ufl.dx))
    weighted.assemble()

    mass_norm = mass.norm(PETSc.NormType.FROBENIUS)
    residual = weighted.copy()
    residual.axpy(
        PETSc.ScalarType(-eps_c), mass, structure=PETSc.Mat.Structure.SAME_NONZERO_PATTERN
    )
    residual_norm = residual.norm(PETSc.NormType.FROBENIUS)

    if comm.rank == 0:
        print(
            f"[TH-1 step 0] ||M||_F={mass_norm:.6e} "
            f"||M_c - eps_c*M||_F={residual_norm:.3e}"
        )

    assert mass_norm > 0.0
    assert residual_norm < 1e-12 * mass_norm, (
        f"weighted N1curl mass matrix is not eps_c*M: residual "
        f"{residual_norm:.3e} vs {mass_norm:.3e}"
    )
