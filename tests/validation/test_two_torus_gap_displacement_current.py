"""`TH-15` step 2d — the gap-displacement port current on the solid two-torus.

``run_gap_voltage_port_case`` has taken a port's ``I`` as the **conduction**
current in the conductor *volume* since `PORT-1`.  A conductor solved as a hole
(`TH-15` step 2a) has no conductor cells, so that definition raises before any
``Z`` entry exists (step 2, 2026-09-06 13:30).  Step 2b's Ampere-loop contour
current cleared the raise but read the *driven wire's* field on a loop 12.5 mm
out, so its absolute floor (~1e-2 A) sat an order of magnitude above the
undriven port's true current (~1.2e-3 A) and reciprocity missed at 1.4338e-03
against ``S_SYMMETRY_BAND`` — a floor that scales with the drive, not with the
port (parked, `ae79a4f`, `20260907T020614Z_TH-15.log:1050-1052, 1075`).

The 2026-09-07 03:00 review's ruling (1) names the third route, and it is the
one the fixture already defines.  The gap box is a *tagged cell volume*, the
impressed drive already lives on it, and by continuity of the total current
across the gap face

    ``I_k = [I_drive if k is driven] + (1/g_k) int_{gap k} (sigma + j w eps)
            E . hhat_k dV``

with ``g_k = gap_length_m`` and ``hhat_k`` the unit ``drive_direction``.  On the
*undriven* port that gap field is the port's own — its gap voltage (V2 =
1.07 V, `:1051`) across a gap far thinner than the wire — against an ambient
field of the driven wire's order ~1e2 V/m, so the readout is conditioned on the
right current by two decades.  It is added as
``GapVoltagePortSpec.current_route="gap_displacement"``; the default
``"conduction"`` leaves every pre-existing caller on today's code.

**Anchors (asserted).**

  (v)   *the open-circuit condition on the undriven port* —
        ``|I_disp,undriven| / I_drive <= OPEN_CIRCUIT_BAND`` = 1e-4 on P2 of
        the P1 drive and P1 of the P2 drive.  This is the hypothesis
        ``Z[i, k] = V_i / I_k`` rests on: ``_assemble_impedance_matrix``
        (`ports/sparameters.py:234-253`) reads the *driven* port's current
        only, so an ``S``/``Z`` reduction is meaningful exactly when the
        undriven terminals carry no current.  Predicted 1e-6 class — it is
        ``j w (eps_0 A_gap / g) V_undriven``; ``V_undriven`` printed beside;
  (ii)  *continuity on the driven port* — ``|(I_drive + I_gap)/I_cond - 1|``
        against the pre-registered ``CONTINUITY_BAND`` = 0.10, where
        ``I_disp`` carries ``I_drive`` (the loop route read 1.86% here,
        `20260907T020614Z_TH-15.log:1048`); the sign convention
        ``rhohat x (-zhat) = phihat`` is what this anchor checks;
  (iii) *reciprocity* — ``||S - S^T||/||S||`` at the imported
        ``S_SYMMETRY_BAND`` = 1e-3, which the conduction route holds at
        4.76e-05 on this mesh and the loop route missed at 1.4338e-03;
  (iv)  *the closed-form mutual* — the corrected ``Im Z12 / (omega M12)``
        inside the imported ``MUTUAL_TOLERANCE`` through the same systematics
        ladder ``test_port_package_sparameters`` applies, the conduction
        route's 0.939822 record printed beside it.

**Negative control (asserted — §9 standing rule (e); backed by a prior
measurement of the same comparison on the same fixture,
`20260907T093741Z_TH-15.log:1000, 1005`).**  The conduction *volume average*
on the same undriven ring must sit at least 100x above the gap-face current:
``|I_cond,undriven| / |I_disp,undriven| >= 100`` (measured 1.2065e-03 /
1.6903e-03 A against 1.5407e-06 A, i.e. 783x / 1097x, which is also the
ceiling).  It is the record that an open ring's *induced* current is not its
*terminal* current.  Separation printed beside the assertion.

**Two anchors were deleted, not loosened (2026-09-07 10:30 review, ruling
(1); step 2c, 04:30 slot).**  ``..._is_the_conduction_current_on_the_undriven_
port`` asserted ``|I_disp/I_cond - 1| <= 0.10`` on the undriven port and read
**9.998674e-01** (drive P1, port P2) and **9.993525e-01** (drive P2, port P1)
— `20260907T093741Z_TH-15.log:1000, 1005`.  Its asserted negative control
``..._beats_the_loop_route_on_the_undriven_port`` read a separation of
**0.99x** against the Ampere-loop route's 9.860947e-01 on the identical port
of the identical solve — `…093741Z:1022-1025`.  Both compared two *different*
quantities to a third that neither is: the conduction volume average
``sigma/L int_conductor E . phihat dV`` around a ring that is open at its gap
is the induced current closing through the ring's own stray capacitance, and
it vanishes at the gap faces while the gap face carries the gap capacitor's
current.  No ``h``, band or fit makes them agree, and no consumer reads the
undriven current: ``Z`` has never contained it on any route.  The readings
above are the record; the open-circuit anchor (v) is what the undriven port
is actually gated on.

**Scope.**  10 MHz, degree 1, the **solid** fixture only — two solves, no hole,
no lossless identity (that is step 2 proper), no ``Re Z = 0`` claim, no band
moved.  ``TH-15`` stays 🟡.
"""

from __future__ import annotations

import numpy as np
import pytest
from mpi4py import MPI

from dolfinx import default_scalar_type

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.gap_voltage import GapVoltagePortSpec
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep
from fem_em_solver.ports.systematics import mutual_systematics_ladder

# Every fixture parameter and every pre-existing band is imported, never
# restated (the two exceptions are the new CONTINUITY_BAND and the loop-route
# record below, both pre-registered here with their provenance).
from tests.validation.test_port_package_sparameters import (
    DRIVE_CURRENT_A,
    FREQUENCY_HZ,
    GAP_TAGS,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    MUTUAL_TOLERANCE,
    OMEGA,
    PATH_QUADRATURE_ORDER,
    RECORDED_CORRECTED_RATIO,
    REFERENCE_IMPEDANCE_OHM,
    SEPARATION,
    SIGMA_WIRE_S_PER_M,
    S_SYMMETRY_BAND,
    WIRE_TAGS,
    _arc_quadrature,
    _azimuthal_unit,
    _gap_half_extents,
    _mutual_inductance,
)
from tests.validation.test_port_lumped_two_torus import _build

# --- the one new band, pre-registered ---------------------------------------
# Two definitions of the same physical current on the same solved field: they
# differ by the gap's fringing (the gap is 5.2 mm along the wire against a
# 5 mm wire radius, so E in the gap volume is not one-dimensional) plus the
# discretisation of a degree-1 field on h_wire = 2.5 mm.  Percent-class is the
# prediction; 0.10 is the *class* of the imported MUTUAL_TOLERANCE, chosen
# before the measurement and not adjusted after it.
CONTINUITY_BAND = 0.10

# --- the open-circuit band, pre-registered (ruling (1), 2026-09-07 10:30) ----
# The undriven gap terminal current as a fraction of the impressed drive.  It
# is jw(eps_0 A_gap/g) V_undriven with A_gap/g the gap capacitor's geometry and
# V_undriven ~ 1 V, so 1e-6 class is the prediction; 1e-4 is two decades of
# headroom on that prediction and is the loosest reading at which "the undriven
# terminals carry no current" remains a true statement about Z = V/I_driven.
OPEN_CIRCUIT_BAND = 1e-4

# --- the negative control's floor -------------------------------------------
# The conduction volume average on the *same* undriven ring, over the gap-face
# current.  Backed by the same comparison on the same fixture:
# 20260907T093741Z_TH-15.log:1000, 1005 -> 783x and 1097x.
CONDUCTION_SEPARATION_FLOOR = 100.0


def _ports():
    return [
        PortDefinition(
            port_id=f"P{k + 1}",
            positive_tag=GAP_TAGS[k],
            negative_tag=WIRE_TAGS[k],
            orientation="gap_azimuthal_plus_y",
            z0_ohm=REFERENCE_IMPEDANCE_OHM,
        )
        for k in range(2)
    ]


def _displacement_specs():
    """The package gate's specs, with the current route switched."""
    _, half_y = _gap_half_extents()
    specs = []
    for k in range(2):
        points, tangents, weights = _arc_quadrature(k, PATH_QUADRATURE_ORDER)
        specs.append(
            GapVoltagePortSpec(
                port_id=f"P{k + 1}",
                gap_cell_tag=GAP_TAGS[k],
                gap_length_m=2.0 * half_y,
                conductor_cell_tag=WIRE_TAGS[k],
                conductor_sigma_s_per_m=SIGMA_WIRE_S_PER_M,
                conductor_direction=_azimuthal_unit,
                conductor_cross_section_m2=float(np.pi * MINOR_RADIUS**2),
                path_points=points,
                path_tangents=tangents,
                path_weights=weights,
                drive_direction=(0.0, 1.0, 0.0),
                drive_current_a=DRIVE_CURRENT_A,
                current_route="gap_displacement",
            )
        )
    return specs


def _prepare(msh):
    tdim = msh.topology.dim
    # Unconditionally on every rank before any tagged form (`PORT-1` 3b-iv).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()


def _skip_unless_complex():
    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        pytest.skip("needs the complex DolfinX build")


@pytest.fixture(scope="module")
def displacement_sweep():
    """The sigma = 800 solid, driven twice, ``I`` from the port's own gap."""
    _skip_unless_complex()
    comm = MPI.COMM_WORLD
    msh, cell_tags, _facet_tags, t_mesh = _build(comm)
    _prepare(msh)
    n_cells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    if comm.rank == 0:
        print(
            f"\n[TH-15 step 2d] solid mesh: {n_cells} cells, {t_mesh:.2f} s",
            flush=True,
        )
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            tag: HomogeneousMaterial(sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0)
            for tag in WIRE_TAGS
        },
        boundary_condition="pec_zero_tangential_a",
    )
    result = run_n_port_sparameter_sweep(
        problem, _ports(), gap_voltage_ports=_displacement_specs()
    )
    return {"result": result, "n_cells": n_cells, "comm": comm}


def _ratio(result, driven_id: str, port_id: str) -> tuple[complex, complex, complex]:
    """``(I_disp, I_cond, I_disp/I_cond)`` for one port of one drive."""
    response = result.excitation_results[driven_id].responses[port_id]
    diagnostics = response.current_diagnostics or {}
    assert "conduction" in diagnostics, (
        f"the gap_displacement route reported no conduction diagnostic on "
        f"'{port_id}' — the solid mesh has conductor cells, so the comparison "
        "must exist"
    )
    i_cond = diagnostics["conduction"]
    assert i_cond is not None, (
        f"'{port_id}': the conduction diagnostic is None on a mesh whose "
        "conductor tags are present"
    )
    i_disp = complex(response.current_a)
    return i_disp, complex(i_cond), i_disp / complex(i_cond)


def _report(label, result, driven_id, port_id, comm) -> float:
    i_disp, i_cond, ratio = _ratio(result, driven_id, port_id)
    miss = abs(ratio - 1.0)
    diagnostics = result.excitation_results[driven_id].responses[port_id].current_diagnostics
    if comm.rank == 0:
        print(
            f"[TH-15 step 2d] {label} (drive {driven_id}, port {port_id}):\n"
            f"    I_disp = drive {diagnostics['drive_part']!r} + gap field "
            f"{diagnostics['gap_field_part']!r}\n"
            f"           = {i_disp!r} A\n"
            f"    I_cond = {i_cond!r} A\n"
            f"    I_disp / I_cond = {ratio!r}, |I_disp/I_cond - 1| = "
            f"{miss:.6e} (band {CONTINUITY_BAND:.2f})",
            flush=True,
        )
    return miss


def test_the_undriven_port_is_open_at_its_terminals(displacement_sweep):
    """Anchor (v) + its separation control: the premise ``Z = V / I_driven``.

    The undriven gap current is asserted below 1e-4 of the drive, and the
    conduction volume average on the *same* ring is asserted at least 100x
    above it — the record that the induced ring current is not a terminal
    current (see the module docstring for the deleted anchor (i)).
    """
    result = displacement_sweep["result"]
    comm = displacement_sweep["comm"]
    drive = abs(complex(DRIVE_CURRENT_A))
    for driven_id, port_id in (("P1", "P2"), ("P2", "P1")):
        i_disp, i_cond, _ratio_unused = _ratio(result, driven_id, port_id)
        response = result.excitation_results[driven_id].responses[port_id]
        v_undriven = complex(response.voltage_v)
        open_ratio = abs(i_disp) / drive
        separation = abs(i_cond) / abs(i_disp)
        if comm.rank == 0:
            print(
                f"[TH-15 step 2d] open-circuit anchor (drive {driven_id}, "
                f"undriven port {port_id}):\n"
                f"    V_undriven = {v_undriven!r} V (|V| = {abs(v_undriven):.6e})\n"
                f"    I_disp     = {i_disp!r} A (|I| = {abs(i_disp):.6e})\n"
                f"    |I_disp| / I_drive = {open_ratio:.6e} "
                f"(band {OPEN_CIRCUIT_BAND:.1e}; predicted 1e-6 class)\n"
                f"    I_cond (volume average, same ring) = {i_cond!r} A\n"
                f"    separation |I_cond| / |I_disp| = {separation:.1f}x "
                f"(floor {CONDUCTION_SEPARATION_FLOOR:.0f}x)",
                flush=True,
            )
        assert open_ratio <= OPEN_CIRCUIT_BAND, (
            f"drive {driven_id}, undriven port {port_id}: |I_disp|/I_drive = "
            f"{open_ratio:.6e} above the pre-registered "
            f"{OPEN_CIRCUIT_BAND:.1e} — the undriven port is not open at its "
            "terminals, so Z = V / I_driven does not hold on this fixture"
        )
        assert separation >= CONDUCTION_SEPARATION_FLOOR, (
            f"drive {driven_id}, undriven port {port_id}: the conduction "
            f"volume average is only {separation:.1f}x the gap-face current, "
            f"below the asserted {CONDUCTION_SEPARATION_FLOOR:.0f}x — the two "
            "quantities are no longer separated on this fixture"
        )


def test_the_gap_current_is_the_conduction_current_on_the_driven_port(
    displacement_sweep,
):
    """Anchor (ii): with ``I_drive`` added; the sign convention's check."""
    result = displacement_sweep["result"]
    comm = displacement_sweep["comm"]
    for driven_id in ("P1", "P2"):
        miss = _report("driven", result, driven_id, driven_id, comm)
        assert miss < CONTINUITY_BAND, (
            f"driven port {driven_id}: |(I_drive + I_gap)/I_cond - 1| = "
            f"{miss:.6e} outside the pre-registered {CONTINUITY_BAND:.2f}"
        )


def test_the_gap_route_sweep_is_reciprocal_and_lands_on_the_mutual(
    displacement_sweep,
):
    """Anchors (iii) and (iv): the network identities, on the new current."""
    result = displacement_sweep["result"]
    comm = displacement_sweep["comm"]
    assert not result.is_placeholder, (
        "the gap_displacement route must not mark itself a placeholder"
    )

    s = result.s_matrix
    symmetry = float(np.linalg.norm(s - s.T) / np.linalg.norm(s))
    im_z12 = float(result.z_matrix[1, 0].imag)
    omega_m12 = OMEGA * _mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    ladder = mutual_systematics_ladder(im_z12, omega_m12)
    if comm.rank == 0:
        print(
            f"[TH-15 step 2d] solid sigma=800, gap_displacement route: "
            f"Im Z12 = {im_z12:+.9e} Ohm, omega*M12 = {omega_m12:.6f} Ohm; raw "
            f"{ladder['raw']:.6f} ({100.0 * ladder['raw_deviation']:+.2f}%) -> "
            f"corrected {ladder['corrected']:.6f} "
            f"({100.0 * ladder['deviation']:+.2f}%, band "
            f"{100.0 * MUTUAL_TOLERANCE:.0f}%); the conduction route's record on "
            f"this mesh is {RECORDED_CORRECTED_RATIO:.6f}\n"
            f"    ||S - S^T||/||S|| = {symmetry:.4e} (band {S_SYMMETRY_BAND:.1e}; "
            f"conduction route 4.76e-05, loop route 1.4338e-03)\n"
            f"    Z (Ohm):\n{result.z_matrix}\n    S:\n{s}",
            flush=True,
        )

    assert symmetry < S_SYMMETRY_BAND, (
        f"the gap_displacement S is not reciprocal: ||S - S^T||/||S|| = "
        f"{symmetry:.4e} >= {S_SYMMETRY_BAND:.1e}"
    )
    assert abs(ladder["deviation"]) < MUTUAL_TOLERANCE, (
        f"the gap_displacement route's corrected mutual {ladder['corrected']:.6f} "
        f"is {100.0 * ladder['deviation']:+.2f}% against the closed form, outside "
        f"the unmoved {100.0 * MUTUAL_TOLERANCE:.0f}% band"
    )
