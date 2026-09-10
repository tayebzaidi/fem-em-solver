"""`TH-15` step 3 — the gap volume can be selected from **both** box halves.

Step 2h settled the mechanism: ``MeshGenerator.two_torus_domain`` fragments each
gap box at its mid-plane when ``emit_port_sheet=True``, so the cell tags
``101`` / ``102`` that every caller passes as ``GapVoltagePortSpec.gap_cell_tag``
select **half** the box — measured ``V_tag``/box = 0.500000 with the ``z`` extent
exactly half and ``x``, ``y`` full
(``20260909T110257Z_TH-15-step2h.log:513-519``, SOLID rows ``:1438-1445``) — and
the generator's own docstring says a caller taking the gap volume "must take both
halves" (``src/fem_em_solver/io/mesh.py:1179-1182, 1425-1426``).
``run_gap_voltage_port_case`` divides the prescribed drive current by
``A_gap = V_gap / gap_length_m``, so that factor 2 sits in the drive density of
every solve on this fixture.

The ``src/`` change this module exercises is **deliberately additive**:
``GapVoltagePortSpec`` gains an optional ``gap_cell_tags`` tuple that defaults to
``(gap_cell_tag,)``, and the ``_tag_volume`` call site sums over it.  **The
default is not flipped here.**  Every pre-existing caller keeps today's
behaviour byte-for-byte, which is what the rule-(c) re-run of
``test_port_gap_voltage_impedance.py`` and ``test_port_gap_voltage_padding.py``
is evidence of.  Flipping the default is a review's ruling, made from the
numbers printed below.

**Anchor (asserted) — a geometric closed form.**  The summed volume of
``(101, 111)`` equals the CAD gap box ``(2(r_w + GAP_OVERHANG))^2 x 2 half_y`` =
1509.378273 mm^3 to <= 1e-3 relative, i.e. the ratio moves from the measured
0.500000 to 1.000000; and the same for ``(102, 112)``.  If it does **not** reach
the box inside 1e-3, ``111`` / ``112`` are not the other halves and step 2h's
mechanism is wrong: that is the item's negative result, to be recorded, not
chased.

**Negative control (asserted) — backed by step 2h's measurement of the same
quantity on the same mesh (``:1438-1445``).**  The single-tag selection still
reads 0.500000 of the box on this mesh, so the two selections differ by exactly
2.000000 inside 1e-6.  A change that silently altered the single-tag path breaks
this, which is why it is asserted rather than printed.  The fixture's own C2 is
carried through as well: the two ports' selections agree to <= 1e-3 (step 2h
measured 2.53e-15 / 8.70e-15).

**Printed, asserted nowhere.**  ``V`` (the port voltage the path route returns,
which is what a ``V̄`` normalisation would carry the factor into), the mutual
against the ratified closed form through the unmoved systematics ladder, and the
reciprocity residual ``||S - S^T||/||S||`` — each computed **both ways**,
single-half and both-halves, side by side.  Six numbers.  This module gates none
of them and moves no band, no record and no default.

**One thing the both-halves configuration is not.**  Only the drive
cross-section reads the summed volume; the impressed density's support stays on
``gap_cell_tag`` alone, exactly as the item specifies.  So the both-halves rung
drives ``J = I / A_box`` over half a box and therefore impresses ``I/2``: that
is the factor under discussion made visible, not a second bug.  Any reading of
the six numbers has to carry it.

**Scope.**  10 MHz, degree 1, the solid gapped fixture, conduction route (the
gated one).  Closes nothing; ``TH-15`` stays 🟡.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

from dolfinx import default_scalar_type

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.gap_voltage import GapVoltagePortSpec, _tag_volume
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep
from fem_em_solver.ports.systematics import mutual_systematics_ladder

# Every fixture parameter and every band below is imported, never restated
# (`ANS-1`), except the two pre-registered here with their provenance.
from tests.validation.test_port_package_sparameters import (
    DRIVE_CURRENT_A,
    FREQUENCY_HZ,
    GAP_OVERHANG,
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

# --- the upper halves, from the generator's own tag map ----------------------
# io/mesh.py:1425-1426 — gap 1 is (101, 111), gap 2 is (102, 112), below/above
# the mid-plane z = -/+ separation/2.
UPPER_GAP_TAGS = (111, 112)

# --- the anchor's comparand and its band, pre-registered ---------------------
# The CAD gap box, recomputed from the imported geometry below and cross-checked
# against the number the plan item names.  1e-3 is the band step 2h's C2 control
# used for the same class of geometric identity; the meshed volume of a box the
# mesher conforms to exactly is a twelve-digit quantity (step 2h read 0.500000
# of it to six printed digits on both fixtures), so 1e-3 is loose by decades and
# was chosen before this measurement.
CAD_GAP_BOX_MM3 = 1509.378273
VOLUME_BAND = 1.0e-3

# --- the negative control's band, pre-registered -----------------------------
# The two selections differ by *exactly* 2 if and only if the single tag is a
# half and the pair is the whole; 1e-6 is the item's figure and is the width at
# which "exactly 2.000000" is a statement rather than a rounding.
DOUBLING_BAND = 1.0e-6


def _skip_unless_complex():
    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        pytest.skip("needs the complex DolfinX build")


def _cad_gap_box_m3() -> float:
    half_xz, half_y = _gap_half_extents()
    return (2.0 * half_xz) ** 2 * (2.0 * half_y)


def _specs(both_halves: bool):
    """The gated package specs, optionally taking both gap-box halves."""
    _, half_y = _gap_half_extents()
    specs = []
    for k in range(2):
        points, tangents, weights = _arc_quadrature(k, PATH_QUADRATURE_ORDER)
        specs.append(
            GapVoltagePortSpec(
                port_id=f"P{k + 1}",
                gap_cell_tag=GAP_TAGS[k],
                gap_cell_tags=(
                    (GAP_TAGS[k], UPPER_GAP_TAGS[k]) if both_halves else None
                ),
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
            )
        )
    return specs


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


@pytest.fixture(scope="module")
def gapped_solid():
    """One mesh, built once; the geometry tests and both sweeps share it."""
    _skip_unless_complex()
    comm = MPI.COMM_WORLD
    msh, cell_tags, _facet_tags, t_mesh = _build(comm)
    tdim = msh.topology.dim
    # Unconditionally on every rank before any tagged form (`PORT-1` 3b-iv).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    # `size_local` excludes ghosts, so the reduction counts each cell once
    # (`OPS-39`).
    n_cells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    if comm.rank == 0:
        print(
            f"\n[TH-15 step 3] gapped solid mesh: {n_cells} cells, "
            f"{t_mesh:.2f} s build, {comm.size} rank(s)",
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
    return {
        "msh": msh,
        "cell_tags": cell_tags,
        "problem": problem,
        "comm": comm,
        "n_cells": n_cells,
    }


def test_the_two_gap_halves_sum_to_the_cad_box(gapped_solid):
    """Anchor + negative control: 0.500000 -> 1.000000, a factor of exactly 2.

    Geometry only, no solve: ``_tag_volume`` is the very function
    ``run_gap_voltage_port_case`` divides the drive current by, called on the
    single tag and on the pair.
    """
    msh = gapped_solid["msh"]
    cell_tags = gapped_solid["cell_tags"]
    comm = gapped_solid["comm"]

    cad_box = _cad_gap_box_m3()
    if comm.rank == 0:
        print(
            f"[TH-15 step 3] CAD gap box = {1.0e9 * cad_box:.6f} mm^3 "
            f"(the item's comparand {CAD_GAP_BOX_MM3:.6f} mm^3)",
            flush=True,
        )
    assert abs(1.0e9 * cad_box / CAD_GAP_BOX_MM3 - 1.0) <= VOLUME_BAND, (
        f"the fixture's CAD gap box {1.0e9 * cad_box:.6f} mm^3 is not the "
        f"comparand {CAD_GAP_BOX_MM3:.6f} mm^3 the item names — the geometry "
        "moved, and every number below is about a different box"
    )

    singles: list[float] = []
    pairs: list[float] = []
    for k in range(2):
        lower = GAP_TAGS[k]
        pair = (lower, UPPER_GAP_TAGS[k])
        v_single = _tag_volume(msh, cell_tags, lower, comm)
        v_pair = _tag_volume(msh, cell_tags, pair, comm)
        singles.append(v_single)
        pairs.append(v_pair)
        r_single = v_single / cad_box
        r_pair = v_pair / cad_box
        doubling = v_pair / v_single
        if comm.rank == 0:
            print(
                f"[TH-15 step 3] P{k + 1}: tag {lower} alone "
                f"V = {1.0e9 * v_single:.6f} mm^3, V/box = {r_single:.6f}\n"
                f"               tags {pair} summed "
                f"V = {1.0e9 * v_pair:.6f} mm^3, V/box = {r_pair:.6f}\n"
                f"               summed / single = {doubling:.9f} "
                f"(band |.-2| <= {DOUBLING_BAND:.0e})",
                flush=True,
            )
        # ANCHOR — the pair is the whole box.
        assert abs(r_pair - 1.0) <= VOLUME_BAND, (
            f"P{k + 1}: tags {pair} sum to {1.0e9 * v_pair:.6f} mm^3, "
            f"V/box = {r_pair:.6f}, outside {VOLUME_BAND:.0e} of the CAD box — "
            f"{UPPER_GAP_TAGS[k]} is not the other half of {lower} and step 2h's "
            "mechanism is wrong"
        )
        # NEGATIVE CONTROL — the single tag is untouched, and is a half.
        assert abs(r_single - 0.5) <= VOLUME_BAND, (
            f"P{k + 1}: tag {lower} alone reads V/box = {r_single:.6f}, not the "
            f"0.500000 step 2h measured on this mesh — the additive change "
            "altered the single-tag path"
        )
        assert abs(doubling - 2.0) <= DOUBLING_BAND, (
            f"P{k + 1}: the two selections differ by {doubling:.9f}, not exactly "
            f"2 inside {DOUBLING_BAND:.0e}"
        )

    for label, volumes in (("single", singles), ("summed", pairs)):
        c2 = abs(volumes[0] - volumes[1]) / abs(volumes[0])
        if comm.rank == 0:
            print(
                f"[TH-15 step 3] C2 control ({label}): "
                f"|V_P1 - V_P2|/|V_P1| = {c2:.6e} against {VOLUME_BAND:.0e}",
                flush=True,
            )
        assert c2 <= VOLUME_BAND, (
            f"the two ports' {label} gap selections differ by {c2:.6e} > "
            f"{VOLUME_BAND:.0e} — the fixture's own C2 is broken"
        )


def test_print_the_six_numbers_both_ways(gapped_solid):
    """Printed, asserted nowhere: ``V``, the mutual and reciprocity, both ways.

    Two sweeps on the same problem and the same mesh, differing only in
    ``gap_cell_tags``.  Nothing here is gated; the assertions live in the
    geometry test above.
    """
    problem = gapped_solid["problem"]
    comm = gapped_solid["comm"]
    omega_m12 = OMEGA * _mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)

    readings = {}
    for label, both in (("single-half (today's default)", False), ("both-halves", True)):
        t0 = time.perf_counter()
        result = run_n_port_sparameter_sweep(
            problem, _ports(), gap_voltage_ports=_specs(both)
        )
        elapsed = time.perf_counter() - t0
        s = result.s_matrix
        symmetry = float(np.linalg.norm(s - s.T) / np.linalg.norm(s))
        im_z12 = float(result.z_matrix[1, 0].imag)
        ladder = mutual_systematics_ladder(im_z12, omega_m12)
        v_driven = [
            complex(result.excitation_results[pid].responses[pid].voltage_v)
            for pid in ("P1", "P2")
        ]
        v_bar = float(np.mean([abs(v) for v in v_driven]))
        readings[label] = (v_bar, ladder, symmetry)
        if comm.rank == 0:
            print(
                f"\n[TH-15 step 3] {label}: sweep in {elapsed:.1f} s\n"
                f"    V (driven port, path route): P1 {v_driven[0]!r} V, "
                f"P2 {v_driven[1]!r} V; mean |V| = {v_bar:.9e} V\n"
                f"    Im Z12 = {im_z12:+.9e} Ohm, omega*M12 = {omega_m12:.6f} Ohm; "
                f"raw {ladder['raw']:.6f} "
                f"({100.0 * ladder['raw_deviation']:+.2f}%) -> corrected "
                f"{ladder['corrected']:.6f} ({100.0 * ladder['deviation']:+.2f}%; "
                f"the gated record is {RECORDED_CORRECTED_RATIO:.6f}, band "
                f"{100.0 * MUTUAL_TOLERANCE:.0f}%, NOT gated here)\n"
                f"    ||S - S^T||/||S|| = {symmetry:.6e} "
                f"(band {S_SYMMETRY_BAND:.1e}, NOT gated here)",
                flush=True,
            )

    if comm.rank == 0:
        a, b = readings["single-half (today's default)"], readings["both-halves"]
        print(
            "\n[TH-15 step 3] the six numbers, side by side "
            "(single-half | both-halves):\n"
            f"    mean |V|      {a[0]:.9e} | {b[0]:.9e}  "
            f"(ratio {b[0] / a[0]:.6f})\n"
            f"    corrected M   {a[1]['corrected']:.6f} | "
            f"{b[1]['corrected']:.6f}  (ratio {b[1]['corrected'] / a[1]['corrected']:.6f})\n"
            f"    ||S-S^T||/||S||  {a[2]:.6e} | {b[2]:.6e}\n"
            "    NB: the both-halves rung impresses I/2, because only the drive "
            "cross-section takes the summed volume — the source support is still "
            "the single tag (see the module docstring).",
            flush=True,
        )
