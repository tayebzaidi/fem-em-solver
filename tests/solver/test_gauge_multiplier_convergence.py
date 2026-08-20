"""Coulomb-gauge multiplier convergence on a divergence-free source (MAG-17).

`OPS-17` step 2 (2026-08-17) anchored ``GaugeMethod.LAGRANGE``'s multiplier
against "zero to solver tolerance for a divergence-free source" and found
spread 7.836781e+00 on a closed current loop at h = 0.005 (known-issues, "Four
defects ...", defect 2). Two candidates were named and left undecided: (a)
benign discretisation — the source enters through an interpolated ``J`` whose
discrete divergence is O(h), so the spread falls with refinement; (b) a real
assembly defect in the constraint block, in which case the spread is
h-independent.

`MAG-17` step 1 (this file) separates them with an h-ladder, on pre-registered
bands: fitted log-log rate >= 0.7 => DISCRETE-SOURCE, |rate| < 0.3 =>
ASSEMBLY-DEFECT, in between => no claim. Measured at `-n 2`
(``20260820T123307Z_MAG-17-step1-ladder.log``):

    h = 0.0050   29 190 cells   spread 7.836781e+00
    h = 0.0035   82 819 cells   spread 3.052022e+00
    h = 0.0025  208 049 cells   spread 1.438617e+00

fitted rate **2.4476** (pairwise 2.645 and 2.234) — far above the 0.7 band,
so the verdict is
DISCRETE-SOURCE: the multiplier is absorbing the interpolated source's
discrete divergence, not a defect in the constraint. The anchor
``OPS-17`` wrote was the wrong one; the right one is convergence, and it is
gated here. The multiplier is still *responding* to compatibility, which the
negative control below pins: the deliberately incompatible straight wire
(``J.n != 0`` on the end caps) stays an order of magnitude above the loop at
the same base h.

Tier: standard. Three magnetostatic LAGRANGE solves plus the wire control,
measured 95 s at `-n 2`.
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from fem_em_solver.core.solvers import (
    GaugeMethod,
    MagnetostaticProblem,
    MagnetostaticSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.constants import MU_0
from tests.solver.test_gauge_lagrange import (
    DOMAIN_RADIUS,
    LOOP_DOMAIN_RADIUS,
    LOOP_RADIUS,
    LOOP_RESOLUTION,
    LOOP_WIRE_RADIUS,
    RESOLUTION,
    WIRE_LENGTH,
    WIRE_RADIUS,
)
from tests.validation.test_circular_loop import azimuthal_current_density

# The ladder. The coarsest rung is the `OPS-17` record's own mesh, so the
# measurement it reported is reproduced rather than replaced; the refinement
# factor per rung is ~1.43 in h (~2.8x in cells).
LADDER = (LOOP_RESOLUTION, 0.0035, 0.0025)

# Pre-registered discriminator bands (MAG-17 step 1, PROJECT_PLAN section 7).
RATE_DISCRETE_SOURCE = 0.7  # >= this: the spread is a discretisation residual
RATE_ASSEMBLY_DEFECT = 0.3  # |rate| < this: h-independent, a real defect

# Negative control: the incompatible straight wire read 2.083064e+02 against
# the loop's 7.836781e+00 at base h, 26.6x. The gate is an order of magnitude,
# well clear of the recorded separation.
WIRE_TO_LOOP_MIN_RATIO = 10.0


def _lagrange_loop_spread(resolution: float, comm: MPI.Intracomm) -> tuple[float, int]:
    """Spread of the Coulomb-gauge multiplier on the closed loop at one h."""
    mesh, cell_tags, _ = MeshGenerator.circular_loop_domain(
        loop_radius=LOOP_RADIUS,
        wire_radius=LOOP_WIRE_RADIUS,
        domain_radius=LOOP_DOMAIN_RADIUS,
        resolution=resolution,
        comm=comm,
    )
    n_cells = comm.allreduce(
        mesh.topology.index_map(mesh.topology.dim).size_local, op=MPI.SUM
    )
    solver = MagnetostaticSolver(
        MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0), degree=1
    )
    solver.solve(
        current_density=azimuthal_current_density(1.0 / (np.pi * LOOP_WIRE_RADIUS**2)),
        subdomain_id=1,
        gauge=GaugeMethod.LAGRANGE,
    )
    # gauge_multiplier_spread() reduces across ranks internally.
    return solver.gauge_multiplier_spread(), n_cells


@pytest.fixture(scope="module")
def multiplier_ladder():
    """Multiplier spread at each ladder rung, plus the wire control at base h."""
    comm = MPI.COMM_WORLD
    spreads = []
    cells = []
    for h in LADDER:
        spread, n_cells = _lagrange_loop_spread(h, comm)
        spreads.append(spread)
        cells.append(n_cells)

    mesh, cell_tags, _ = MeshGenerator.straight_wire_domain(
        wire_length=WIRE_LENGTH,
        wire_radius=WIRE_RADIUS,
        domain_radius=DOMAIN_RADIUS,
        resolution=RESOLUTION,
        comm=comm,
    )
    wire_solver = MagnetostaticSolver(
        MagnetostaticProblem(mesh=mesh, cell_tags=cell_tags, mu=MU_0), degree=1
    )
    wire_solver.solve(
        current_density=lambda x: ufl.as_vector(
            [0.0, 0.0, 1.0 / (np.pi * WIRE_RADIUS**2)]
        ),
        subdomain_id=1,
        gauge=GaugeMethod.LAGRANGE,
    )

    # spread ~ C h^p, so the least-squares slope of log(spread) against log(h)
    # IS the convergence rate: positive p means the spread falls with h.
    rate = float(np.polyfit(np.log(np.array(LADDER)), np.log(np.array(spreads)), 1)[0])
    if comm.rank == 0:
        print("\n[MAG-17] Coulomb-gauge multiplier h-ladder (divergence-free loop):")
        for h, n_cells, spread in zip(LADDER, cells, spreads):
            print(f"  h={h:.4f}  cells={n_cells:7d}  spread={spread:.6e}", flush=True)
        print(f"  fitted log-log rate: {rate:.4f}", flush=True)
    return {
        "spreads": spreads,
        "cells": cells,
        "rate": rate,
        "wire_spread": wire_solver.gauge_multiplier_spread(),
    }


def test_multiplier_spread_converges_for_a_divergence_free_source(multiplier_ladder):
    """The spread is a discretisation residual, not a constraint-assembly defect.

    This is the quantitative anchor `OPS-17` step 2 should have written. A
    multiplier that is identically zero in the continuum need not be zero
    discretely: the interpolated ``J`` has a discrete divergence of O(h), and
    ``p`` absorbs exactly that. What must hold is that it *converges away*.

    Measured 2026-08-20 (`MAG-17` step 1, log in the module docstring): rate
    **2.4476** on the three-rung ladder, against the pre-registered 0.7 that
    separates DISCRETE-SOURCE from ASSEMBLY-DEFECT (|rate| < 0.3). The band is
    kept at the pre-registered 0.7 rather than tightened to the measurement,
    so the gate stays the discriminator it was designed as.
    """
    spreads = multiplier_ladder["spreads"]
    rate = multiplier_ladder["rate"]

    assert np.all(np.isfinite(spreads)), f"non-finite spread on the ladder: {spreads}"
    assert all(b < a for a, b in zip(spreads, spreads[1:])), (
        f"multiplier spread is not monotone under refinement: {spreads}"
    )
    assert rate >= RATE_DISCRETE_SOURCE, (
        f"fitted log-log rate {rate:.4f} is below the {RATE_DISCRETE_SOURCE} "
        "DISCRETE-SOURCE band: the multiplier is not converging away with "
        "refinement, which is the ASSEMBLY-DEFECT signature "
        f"(|rate| < {RATE_ASSEMBLY_DEFECT}) the ladder was built to catch"
    )


def test_multiplier_still_separates_an_incompatible_source(multiplier_ladder):
    """Negative control: the multiplier has not stopped responding to J.n != 0.

    A ladder that drove both fixtures to zero would mean the fixture changed,
    not that the gauge is healthy. The straight wire terminates on the domain
    end caps, so its source is genuinely incompatible and the multiplier must
    stay well above the loop's at the same base resolution. Recorded
    2026-08-17: 2.083064e+02 (wire) vs 7.836781e+00 (loop), 26.6x.
    """
    wire_spread = multiplier_ladder["wire_spread"]
    base_loop_spread = multiplier_ladder["spreads"][0]

    ratio = wire_spread / base_loop_spread
    assert ratio > WIRE_TO_LOOP_MIN_RATIO, (
        f"incompatible wire spread {wire_spread:.6e} is only {ratio:.1f}x the "
        f"divergence-free loop's {base_loop_spread:.6e} at base h — the "
        "multiplier has stopped discriminating compatible from incompatible "
        "sources"
    )
