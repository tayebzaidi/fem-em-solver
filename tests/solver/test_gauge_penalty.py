"""Gauge-penalty regularisation guards (MAG-10).

The curl-curl operator has a gradient null space. ``MagnetostaticSolver`` removes
it with a penalty term ``gauge * inner(A, v)``, which leaves a null-space
component in A of magnitude ~1/gauge. ``B = curl(A)`` cancels a gradient exactly
in exact arithmetic, but once that component is orders larger than the physical
field, floating-point cancellation destroys B.

That failure is invisible through every other channel: the default solver is a
direct LU, so PETSc reports converged with residual 0.0 regardless. Measured on
the straight-wire fixture at N1curl degree 2, h=0.003, gauge 1e-3: 920% field
error, KSP reason 4, residual 0.0.

These tests pin the two guards that make the failure detectable.
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from fem_em_solver.core.solvers import (
    DEFAULT_GAUGE_PENALTY,
    GaugeContaminationWarning,
    MagnetostaticProblem,
    MagnetostaticSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.constants import MU_0

WIRE_RADIUS = 0.003
DOMAIN_RADIUS = 0.03
WIRE_LENGTH = 0.20
RESOLUTION = 0.006  # coarse: these tests probe conditioning, not accuracy


def _solve(gauge_penalty, degree=1):
    comm = MPI.COMM_WORLD
    mesh, cell_tags, _ = MeshGenerator.straight_wire_domain(
        wire_length=WIRE_LENGTH,
        wire_radius=WIRE_RADIUS,
        domain_radius=DOMAIN_RADIUS,
        resolution=RESOLUTION,
        comm=comm,
    )
    solver = MagnetostaticSolver(
        MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0), degree=degree
    )
    j = 1.0 / (np.pi * WIRE_RADIUS**2)
    A = solver.solve(
        current_density=lambda x: ufl.as_vector([0.0, 0.0, j]),
        subdomain_id=1,
        gauge_penalty=gauge_penalty,
    )
    local_max = float(np.max(np.abs(A.x.array))) if A.x.array.size else 0.0
    return comm.allreduce(local_max, op=MPI.MAX)


def test_default_gauge_penalty_is_inside_the_safe_window():
    """The default must not sit below the numerically safe range.

    Measured safe across 1e0..1e6 on two independent geometries (straight wire
    and Helmholtz two-torus); B is insensitive across that range. The historical
    1e-3 was below it and silently corrupted degree-2 solves.
    """
    assert DEFAULT_GAUGE_PENALTY >= 1.0
    assert DEFAULT_GAUGE_PENALTY <= 1.0e6


def test_small_gauge_penalty_warns_about_null_space_contamination():
    """A too-small penalty must be reported, since the linear solve will not be.

    This is the guard that would have caught a 920% error while PETSc reported
    converged with residual 0.0.
    """
    with pytest.warns(GaugeContaminationWarning, match="below the validated floor"):
        _solve(1e-3)  # the historical default


def test_default_gauge_penalty_does_not_warn():
    """A well-posed solve must stay quiet, or the warning is worthless."""
    import warnings as _w

    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        _solve(DEFAULT_GAUGE_PENALTY)

    contamination = [w for w in caught if issubclass(w.category, GaugeContaminationWarning)]
    assert not contamination, (
        "default gauge penalty should not trip the contamination guard: "
        f"{[str(w.message) for w in contamination]}"
    )


def test_null_space_magnitude_scales_inversely_with_gauge_penalty():
    """|A| ~ 1/gauge is the mechanism behind the failure; pin it.

    If this stops holding, the reasoning behind DEFAULT_GAUGE_PENALTY no longer
    applies and the value must be re-derived rather than trusted.
    """
    a_small = _solve(1.0)
    a_large = _solve(100.0)

    # Two decades more penalty => roughly two decades less null-space amplitude.
    ratio = a_small / max(a_large, 1e-300)
    assert 10.0 < ratio < 1000.0, (
        f"expected |A| to scale as ~1/gauge (ratio ~100), got {ratio:.3g}"
    )
