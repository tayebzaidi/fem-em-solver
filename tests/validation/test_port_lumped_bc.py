"""`PORT-9` step 1 — the lumped-port sheet forms, pinned against exact identities.

This module gates :mod:`fem_em_solver.ports.lumped` at the level the code
actually claims something: the three forms (L1)–(L3) of that module's docstring
are *exactly* computable on a flat unit sheet with a constant field, so each is
asserted against its closed form to machine precision rather than for
finiteness.  Nothing here is a port-impedance claim — see the module docstring
and PROJECT_PLAN §7 `PORT-9`: step 1 is measurement/formulation only, and the
cross-route bands live in step 2.

Geometry: the unit cube's ``x = 0`` face, tagged 7.  Choosing ``w = h = 1 m``
makes the sheet exactly **one square**, so Jin's ohms-per-square ``R`` equals
the terminal impedance ``Z_p`` (L2) and every identity below reads off the
port's own circuit value with no geometric factor hiding in it.

Cost: smoke tier — one 4³ unit-cube mesh, no solve.
"""

from __future__ import annotations

import numpy as np
import pytest
import ufl
from mpi4py import MPI

import dolfinx
from dolfinx import default_scalar_type, fem

from fem_em_solver.ports.lumped import (
    LumpedPortSheet,
    lumped_port_bilinear_term,
    lumped_port_linear_term,
    sheet_resistivity_ohm_per_square,
    sheet_terminal_current,
)
from fem_em_solver.utils.constants import MU_0

from tests.complex_mode import complex_only

FREQUENCY_HZ = 1.0e7          # 10 MHz — the two-torus fixture's frequency
OMEGA = 2.0 * np.pi * FREQUENCY_HZ
PORT_IMPEDANCE_OHM = 50.0
SHEET_TAG = 7
GAP_HEIGHT_M = 1.0            # one square: R == Z_p
SHEET_WIDTH_M = 1.0
SOURCE_VOLTAGE_V = 1.0 + 0.0j

# Exact-arithmetic identities: every quantity below is a product of exactly
# representable factors, so the only error is assembly quadrature on a flat
# facet of a constant integrand.  1e-12 relative is generous for that.
EXACT_TOLERANCE = 1.0e-12


@pytest.fixture(scope="module")
def sheet_mesh():
    """Unit cube with the ``x = 0`` face tagged as an exterior port sheet."""
    comm = MPI.COMM_WORLD
    msh = dolfinx.mesh.create_unit_cube(comm, 4, 4, 4, dolfinx.mesh.CellType.tetrahedron)
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    facets = dolfinx.mesh.locate_entities_boundary(
        msh, tdim - 1, lambda x: np.isclose(x[0], 0.0)
    )
    facets = np.sort(facets)
    facet_tags = dolfinx.mesh.meshtags(
        msh, tdim - 1, facets, np.full(facets.size, SHEET_TAG, dtype=np.int32)
    )
    return msh, facet_tags


def _sheet(**overrides) -> LumpedPortSheet:
    kwargs = dict(
        port_id="p1",
        facet_tag=SHEET_TAG,
        port_impedance_ohm=PORT_IMPEDANCE_OHM,
        gap_height_m=GAP_HEIGHT_M,
        sheet_width_m=SHEET_WIDTH_M,
        # The sheet lies in the x = 0 plane, so the terminal-to-terminal
        # direction must lie in that plane: z.
        drive_direction=(0.0, 0.0, 1.0),
        source_voltage_v=SOURCE_VOLTAGE_V,
        interior=False,
    )
    kwargs.update(overrides)
    return LumpedPortSheet(**kwargs)


def _constant_z_field(msh):
    """``E = ẑ`` in N1curl — a constant field the space represents exactly."""
    v_space = fem.functionspace(msh, ("N1curl", 1))
    f = fem.Function(v_space)
    f.interpolate(
        lambda x: np.vstack(
            (np.zeros(x.shape[1]), np.zeros(x.shape[1]), np.ones(x.shape[1]))
        ).astype(default_scalar_type)
    )
    f.x.scatter_forward()
    return f


def _assemble(form, comm) -> complex:
    """``assemble_scalar`` is rank-local — reduce before anyone reads it."""
    return complex(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM))


def test_sheet_resistivity_is_ohms_per_square():
    """(L2): ``R = Z_p w / h``, and one square makes ``R = Z_p``."""
    assert sheet_resistivity_ohm_per_square(
        50.0, gap_height_m=1.0, sheet_width_m=1.0
    ) == pytest.approx(50.0, rel=EXACT_TOLERANCE)
    # Two squares in series across the sheet halve the ohms-per-square.
    assert sheet_resistivity_ohm_per_square(
        50.0, gap_height_m=2.0e-3, sheet_width_m=1.0e-3
    ) == pytest.approx(25.0, rel=EXACT_TOLERANCE)
    with pytest.raises(ValueError):
        sheet_resistivity_ohm_per_square(50.0, gap_height_m=0.0, sheet_width_m=1.0)


@complex_only
def test_sheet_area_is_the_unit_square(sheet_mesh):
    """Precondition: the tagged facet set is exactly the ``x = 0`` unit face.

    Every identity below is proportional to the sheet area, so a mis-tagged
    facet set would show up as a scale error in all of them at once and could be
    mistaken for a formulation error.  Pin the area first.
    """
    msh, facet_tags = sheet_mesh
    ds_sheet = ufl.Measure("ds", domain=msh, subdomain_data=facet_tags, subdomain_id=(SHEET_TAG,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    area = _assemble(one * ds_sheet, msh.comm)
    assert float(np.real(area)) == pytest.approx(1.0, rel=EXACT_TOLERANCE)


@complex_only
def test_bilinear_sheet_term_matches_closed_form(sheet_mesh):
    """(L1) on ``E = v = ẑ``: ``jωμ₀ A / R``, exactly.

    ``n̂ = −x̂`` on this face and ``|n̂ × ẑ| = 1``, so the tangential trace is a
    unit vector over the whole sheet and the integral collapses to the area.
    """
    msh, facet_tags = sheet_mesh
    e = _constant_z_field(msh)
    sheet = _sheet()
    form = lumped_port_bilinear_term(
        msh, facet_tags, sheet, e, e, omega_rad_per_s=OMEGA
    )
    measured = _assemble(form, msh.comm)
    expected = 1j * OMEGA * MU_0 * 1.0 / PORT_IMPEDANCE_OHM
    assert abs(measured - expected) / abs(expected) < EXACT_TOLERANCE
    # The sheet must be *dissipative*: with a real R > 0 the term is purely
    # +j·(positive), which is the sign that adds resistance rather than gain.
    assert measured.imag > 0.0


@complex_only
def test_linear_sheet_term_matches_closed_form(sheet_mesh):
    """(L3) tested against ``v = ẑ``: ``−jωμ₀ V_src A / (R h)``."""
    msh, facet_tags = sheet_mesh
    v = _constant_z_field(msh)
    sheet = _sheet()
    form = lumped_port_linear_term(msh, facet_tags, sheet, v, omega_rad_per_s=OMEGA)
    measured = _assemble(form, msh.comm)
    expected = (
        -1j * OMEGA * MU_0 * SOURCE_VOLTAGE_V / (PORT_IMPEDANCE_OHM * GAP_HEIGHT_M) * 1.0
    )
    assert abs(measured - expected) / abs(expected) < EXACT_TOLERANCE


@complex_only
def test_open_circuit_terminal_current_is_v_over_z(sheet_mesh):
    """The circuit identity the whole model exists to reproduce: ``I = V_src/Z_p``.

    With the field switched off (``E = 0``) the sheet is the bare source in
    series with its own impedance, so its terminal current must be exactly
    ``V_src / Z_p`` — 20 mA at 1 V into 50 Ω.  This is what says the
    ohms-per-square conversion (L2) and the sheet-to-terminal reduction in
    :func:`sheet_terminal_current` are inverses of each other rather than two
    independently plausible scalings.
    """
    msh, facet_tags = sheet_mesh
    v_space = fem.functionspace(msh, ("N1curl", 1))
    zero = fem.Function(v_space)
    zero.x.array[:] = 0.0
    zero.x.scatter_forward()

    sheet = _sheet()
    current = sheet_terminal_current(msh, facet_tags, sheet, zero, msh.comm)
    expected = SOURCE_VOLTAGE_V / PORT_IMPEDANCE_OHM
    assert abs(current - expected) / abs(expected) < EXACT_TOLERANCE

    # Negative control: a passive sheet (no source) on a zero field carries no
    # current.  Without it, a bug that ignored E and returned V_src/Z_p from the
    # constant alone would pass the assertion above.
    passive = _sheet(source_voltage_v=0.0)
    assert abs(sheet_terminal_current(msh, facet_tags, passive, zero, msh.comm)) < 1e-30


@complex_only
def test_passive_sheet_current_follows_the_field(sheet_mesh):
    """A passive sheet in ``E = ẑ`` carries ``I = A/(R h) = 1/Z_p`` per volt/metre.

    The other half of the constitutive law: with no source, the current is the
    field's doing.  ``E·ĥ = 1`` over the unit sheet, so ``I = 1/(R h) · A / h``
    reduces to ``1/Z_p`` at one square — 20 mA.
    """
    msh, facet_tags = sheet_mesh
    e = _constant_z_field(msh)
    passive = _sheet(source_voltage_v=0.0)
    current = sheet_terminal_current(msh, facet_tags, passive, e, msh.comm)
    expected = 1.0 / PORT_IMPEDANCE_OHM
    assert abs(current - expected) / abs(expected) < EXACT_TOLERANCE
