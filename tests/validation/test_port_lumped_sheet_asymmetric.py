"""`PORT-9` step 3 leg (d2) — **is the lumped-sheet route reciprocal when the
ports are not equivalent?**

Leg (d1) (2026-08-23) rotated one birdcage leg with its port and the 4x4 lost
reciprocity by 223x (``‖S − Sᵀ‖/‖S‖`` = 5.57e-03 against the unmoved 1e-3).
The 10:30 review refuted the implementer's sheet-width hypothesis from the
log's own ``Z`` (the worst pair was P2-P4, neither port moved) and read the
residual instead as a **global route systematic that every symmetric fixture
cancels** — which would make step 2c's 2.574249e-11 a measurement of the
fixture's symmetry, not of the route's reciprocity.

This module decides that on the cheapest possible asymmetric fixture: step
2b/2c's **two-torus**, one mesh, sheets on both ports, but at **two different
widths** — ``f = 0.5`` on port 1 and ``f = 0.735`` on port 2, both rungs of
step 2b's own ladder, so no new geometry and each width's readout is already on
record (cross-route 1.9222% / 1.0986%).  Two sweeps run on that one mesh:

* the **control** at ``f = 0.5 / 0.5`` — step 2c's configuration exactly,
  which must reproduce its 2.574249e-11 (anchor (a));
* the **asymmetric** sweep at ``f = 0.5 / 0.735`` — the same route, the same
  mesh, the same solver, differing only in which facets each sheet owns
  (anchor (b), against step 2's unmoved 1e-3 band).

**Step 0, the readout-adjointness reading, journaled before the solves ran**
(§7 leg (d2) requires it in one paragraph; it is stated here because the code
is what it is about).  The impressed source of the driven port ``j`` is
``lumped_port_linear_term``: ``b_j = −jωμ₀ · V_src/(R_j h_j) · f_j`` with
``f_j[k] = ∫_{S_j} ĥ_j·v_k dS``.  The current readout of port ``i`` is
``sheet_terminal_current``: ``I_i = (1/(R_i h_i)) ∫_{S_i} E·ĥ_i dS`` plus, on
the driven port only, the source's own ``V_src A_i/(R_i h_i²)``.  The field
part is ``(1/(R_i h_i)) f_iᵀ x`` — **the same facet set ``S_i``, the same
weighting ``ĥ_i/(R_i h_i)``, the same vector ``f_i`` the source is built from**.
So the readout *is* the source's adjoint, and since the assembled operator is
complex-**symmetric** (real basis functions, ``ufl.inner`` conjugating only the
test slot, PEC rows symmetric, and the sheet term (L1) symmetric in trial/test),

    I_i(drive j) = −jωμ₀ V_src /(R_i h_i R_j h_j) · f_iᵀ A⁻¹ f_j  =  I_j(drive i)

**exactly**, on any mesh, for ``i ≠ j``.  What is *not* adjoint-consistent is
the **assembly**, one level up: ``_assemble_impedance_matrix`` forms
``Z_ij = V_i/I_j`` with every port terminated in ``Z_p``, which is a
*terminated transimpedance*, not the open-circuit impedance matrix reciprocity
makes symmetric.  With ``V_i = −Z_p I_i`` at the undriven ports,

    Z_ij / Z_ji = [I_i(j)/I_j(j)] / [I_j(i)/I_i(i)] = I_i(drive i) / I_j(drive j)

once the transadmittance symmetry above is used — the ratio of the two
**driven-port self-currents**, which is 1 for equivalent ports and nothing in
particular otherwise.  That is a third hypothesis, **A′**, sharper than the
review's A: the field readout is adjoint (so the route is discretely
reciprocal in ``I``), and the whole asymmetry lives in the per-column
normalisation by the driven port's own current.  Both identities above are
asserted below at a pre-stated 1e-6, so A′ is falsifiable in the same run that
measures anchors (a) and (b) — if either fails, A′ is wrong and A or B stands.

Cost: standard tier, ``-n 2``, one mesh (~40 s) and four solves (~25 s each).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-9-step3d2 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 500 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_lumped_sheet_asymmetric.py -v -s'"
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.lumped import LumpedSheetPortSpec
from fem_em_solver.ports.sparameters import (
    run_n_port_sparameter_sweep,
    sparameters_from_impedance,
)

from tests.complex_mode import complex_only
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_two_torus_port_sheet import (
    SHEET_FACET_TAGS,
    _sheet_extents,
    _sheet_facet_count,
)
from tests.validation.test_port_gap_voltage_impedance import (
    FREQUENCY_HZ,
    MAJOR_RADIUS,
    SIGMA_WIRE_S_PER_M,
    WIRE_TAGS,
    _gap_half_extents,
)
from tests.validation.test_port_package_sparameters import (
    PATH_QUADRATURE_ORDER,
    REFERENCE_IMPEDANCE_OHM,
    _arc_quadrature,
)
from tests.validation.test_port_lumped_narrowed_sheet import _narrowed_sheet_tags
from tests.validation.test_port_lumped_two_torus import (
    PROBE_PORT_IMPEDANCE_OHM,  # noqa: F401 — the 1e6 Ohm probe leg (d2) ran at
    _build,
)
from tests.validation.test_port_lumped_sheet_sweep import (
    DRIVE_VOLTAGE_V,
    RECIPROCITY_BAND,
)

# The two rungs of step 2b's ladder this leg puts on the two ports. Both are
# gated widths with a recorded readout (1.9222% / 1.0986% cross-route), so the
# asymmetry is entirely in *which facets each sheet owns* — same mesh, same
# geometry, same solver.
CONTROL_FRACTIONS = (0.5, 0.5)
ASYMMETRIC_FRACTIONS = (0.5, 0.735)

# Step 2c's gated reading of ``‖S − Sᵀ‖/‖S‖`` on the symmetric rung
# (2026-08-18, 22:30 slot). Anchor (a) reproduces it to ≤ 1e-9 absolute — the
# control is the same configuration, so anything larger means this module's
# fixture is not step 2c's.
# Leg (d3) retires the *assertion* on it (different assembly, different
# termination — see PORT_IMPEDANCE_OHM below); the digit stays as the printed
# history the control is read against.
STEP2C_RECIPROCITY_RECORD = 2.574249e-11
CONTROL_REPRODUCTION_BAND = 1.0e-9  # leg (d2)'s band, no longer asserted

# **Leg (d3), 2026-08-24.**  The route now assembles S from power waves
# (`S_ij = b_i/a_j`) instead of converting the terminated `Z`, and that identity
# is exact only at a **matched** drive: with `Z_p = z0` the undriven ports give
# `b_i = −√z0·I_i` and the driven port `a_j = V_src/(2√z0)`, so `S_ij ∝ I_i(d j)`
# and leg (d2)'s measured transadmittance symmetry (1.33e-10, unchanged below)
# carries straight into S.  Leg (d2) ran this module at the 1e6 Ohm probe, where
# `a_j` still carries the driven port's own current; the sweeps below therefore
# run at `Z_p = z0 = 50 Ohm`, which is also the termination leg (d0) found for
# the birdcage.
PORT_IMPEDANCE_OHM = REFERENCE_IMPEDANCE_OHM

# The fixed route's gate: exact in infinite precision, so the band is the linear
# solver's floor with margin — five orders below leg (d1)'s 5.57e-03 and four
# below the 1e-3 the terminated conversion was ever gated at.  Never widened.
FIXED_ROUTE_BAND = 1.0e-6

# The mechanism's own negative control, computed in the same run from the
# retained (terminated) `Z`: the old conversion must still read at least this,
# i.e. at least 100x the fixed route's band.  A miss here would mean the fix had
# nothing to fix on this fixture and anchor (a) proves nothing.
OLD_CONVERSION_FLOOR = 1.0e-4

# Pre-stated band for the two mechanism identities of hypothesis A′ (see the
# module docstring). Both are exact in infinite precision; the floor is the
# linear solver's, which step 2c measured at ~2.6e-11 on this very fixture, so
# 1e-6 is ~5 orders above the noise and ~4 below the O(1e-2) route asymmetry
# hypothesis A predicts. Never widened: a miss refutes A′.
MECHANISM_BAND = 1.0e-6


def _rel(a: complex, b: complex) -> float:
    """``|a − b| / |½(a + b)|`` — the symmetric relative deviation."""
    mean = 0.5 * (complex(a) + complex(b))
    return float(abs(complex(a) - complex(b)) / abs(mean))


def _run_sweep(msh, cell_tags, facet_tags, fractions, comm, label):
    """One two-port lumped-sheet sweep at the given per-port width fractions.

    The narrowing filter rewrites one ``21x`` tag and passes every other tag
    through, so composing it once per sheet narrows both on the *same* mesh —
    step 2c's construction, extended to a per-sheet fraction. The mesh is
    untouched, which is what makes the control a control.
    """
    half_xz, _half_y = _gap_half_extents()

    tags_f = facet_tags
    for sheet_tag, fraction in zip(SHEET_FACET_TAGS, fractions):
        tags_f = _narrowed_sheet_tags(
            msh, tags_f, int(sheet_tag), float(fraction), MAJOR_RADIUS, half_xz
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

    ports = []
    specs = []
    sheets = []
    for k, (sheet_tag, fraction) in enumerate(zip(SHEET_FACET_TAGS, fractions)):
        sheet_tag = int(sheet_tag)
        n_facets = _sheet_facet_count(msh, tags_f, sheet_tag, comm)
        assert n_facets > 0, f"{label}: sheet {sheet_tag} has no owned facets anywhere"
        area = _facet_group_area(msh, tags_f, sheet_tag, comm)
        extents = _sheet_extents(msh, tags_f, sheet_tag, comm)
        h = float(extents[1])
        # Step 2b's ``w = A/h`` convention on the filtered facet set, re-measured
        # per sheet — never ``f * w_full``.
        w = area / h
        sheets.append(
            {
                "tag": sheet_tag,
                "f": float(fraction),
                "facets": int(n_facets),
                "area": float(area),
                "w": w,
                "w_bbox": float(extents[0]),
                "h": h,
                "out_of_plane": float(extents[2]),
            }
        )
        points, tangents, weights = _arc_quadrature(k, PATH_QUADRATURE_ORDER)
        ports.append(
            PortDefinition(
                port_id=f"P{k + 1}",
                positive_tag=sheet_tag,
                negative_tag=WIRE_TAGS[k],
                orientation="gap_azimuthal_plus_y",
                z0_ohm=REFERENCE_IMPEDANCE_OHM,
            )
        )
        specs.append(
            LumpedSheetPortSpec(
                port_id=f"P{k + 1}",
                facet_tag=sheet_tag,
                port_impedance_ohm=PORT_IMPEDANCE_OHM,
                gap_height_m=h,
                sheet_width_m=w,
                drive_direction=(0.0, 1.0, 0.0),
                drive_voltage_v=DRIVE_VOLTAGE_V,
                interior=True,
                path_points=points,
                path_tangents=tangents,
                path_weights=weights,
            )
        )

    comm.Barrier()
    t0 = time.perf_counter()
    result = run_n_port_sparameter_sweep(
        problem,
        ports,
        lumped_sheet_ports=specs,
        lumped_sheet_facet_tags=tags_f,
    )
    comm.Barrier()
    t_sweep = time.perf_counter() - t0

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3d2] {label}: fractions {fractions}, sweep "
            f"{t_sweep:.1f} s",
            flush=True,
        )
        for s in sheets:
            print(
                f"    sheet {s['tag']}  f = {s['f']:.3f}  facets {s['facets']:5d}  "
                f"area {s['area']:.9e} m^2  w = A/h = {s['w']:.9e} m "
                f"(bbox {s['w_bbox']:.9e})  h = {s['h']:.9e} m",
                flush=True,
            )

    return {"result": result, "sheets": sheets, "sweep_time": t_sweep, "label": label}


@pytest.fixture(scope="module")
def asymmetric_sweeps():
    """One mesh; the control sweep and the asymmetric sweep on it."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, facet_tags, t_mesh = _build(comm)
    assert facet_tags is not None, "model_to_mesh returned no facet tags"
    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    # Hoisted on every rank before any facet-restricted form (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3d2] fragmented two-torus fixture: {ncells} cells, "
            f"mesh {t_mesh:.1f} s; two sweeps on this one mesh",
            flush=True,
        )

    control = _run_sweep(
        msh, cell_tags, facet_tags, CONTROL_FRACTIONS, comm, "CONTROL f = 0.5 / 0.5"
    )
    asymmetric = _run_sweep(
        msh,
        cell_tags,
        facet_tags,
        ASYMMETRIC_FRACTIONS,
        comm,
        "ASYMMETRIC f = 0.5 / 0.735",
    )

    return {
        "control": control,
        "asymmetric": asymmetric,
        "cells": int(ncells),
        "mesh_time": t_mesh,
        "comm": comm,
    }


def _reciprocity(result) -> tuple[float, float]:
    """``(‖S − Sᵀ‖/‖S‖, ‖Z − Zᵀ‖/‖Z‖)`` for one sweep result."""
    s = result.s_matrix
    z = result.z_matrix
    return (
        float(np.linalg.norm(s - s.T) / np.linalg.norm(s)),
        float(np.linalg.norm(z - z.T) / np.linalg.norm(z)),
    )


@complex_only
def test_the_two_sweeps_differ_only_in_sheet_width(asymmetric_sweeps):
    """Structural: one mesh, two solved-field sweeps, one narrower port.

    The whole leg rests on the two sweeps being the *same* fixture — if the
    asymmetric run also moved the mesh, its reciprocity number would carry a
    second explanation, which is exactly the ambiguity leg (d1) hit when gmsh
    regenerated the birdcage whole (116 416 → 116 944 cells).
    """
    for key in ("control", "asymmetric"):
        r = asymmetric_sweeps[key]["result"]
        assert not r.is_placeholder, f"{key}: the sweep fell back to the heuristic"
        assert r.z_matrix is not None, f"{key}: the route must return its Z"
        assert r.z_matrix.shape == (2, 2)
        for s in asymmetric_sweeps[key]["sheets"]:
            assert s["out_of_plane"] < 1.0e-12, (
                f"{key}: sheet {s['tag']} out-of-plane spread "
                f"{s['out_of_plane']:.3e} m — the filtered set is not a plane"
            )

    c_sheets = asymmetric_sweeps["control"]["sheets"]
    a_sheets = asymmetric_sweeps["asymmetric"]["sheets"]

    # Port 1 is untouched between the two sweeps; port 2 is the only difference.
    assert c_sheets[0]["area"] == a_sheets[0]["area"], (
        "port 1's sheet moved between the control and the asymmetric sweep — "
        "the two runs are not the same fixture"
    )
    assert a_sheets[1]["area"] > c_sheets[1]["area"], (
        f"port 2's sheet did not widen: {a_sheets[1]['area']:.9e} m^2 at "
        f"f = {a_sheets[1]['f']} against {c_sheets[1]['area']:.9e} at "
        f"f = {c_sheets[1]['f']} — the asymmetry was never introduced"
    )

    if MPI.COMM_WORLD.rank == 0:
        w_ratio = a_sheets[1]["w"] / a_sheets[0]["w"]
        print(
            f"\n[PORT-9 step3d2] the asymmetry: w2/w1 = {w_ratio:.9f} "
            f"(w1 = {a_sheets[0]['w']:.9e} m, w2 = {a_sheets[1]['w']:.9e} m) "
            f"on one {asymmetric_sweeps['cells']}-cell mesh",
            flush=True,
        )


def _pair_ratio(s: np.ndarray) -> float:
    """``max_{i<j} |S_ij/S_ji − 1|`` — the per-pair asymmetry.

    The Frobenius ratio ``‖S − Sᵀ‖/‖S‖`` is grain-limited by the largest entry;
    leg (d2) found a 0.25% per-pair asymmetry hiding inside a 8.3e-09 Frobenius
    reading at ``Z_p`` = 1e6 Ohm.  This is the pair-resolved statistic that saw
    it, asserted here beside the norm so neither can hide the other.
    """
    worst = 0.0
    n = s.shape[0]
    for i in range(n):
        for j in range(i + 1, n):
            if abs(s[j, i]) == 0.0:
                continue
            worst = max(worst, float(abs(s[i, j] / s[j, i] - 1.0)))
    return worst


def _old_conversion(result) -> tuple[float, float]:
    """``(‖S − Sᵀ‖/‖S‖, per-pair)`` of the *retired* terminated-Z conversion.

    Computed in the same run from the ``z_matrix`` the route still returns as a
    diagnostic, so the negative control shares every solve with the gated
    reading — no second fixture, no second mesh, no second solver call.
    """
    s_old = sparameters_from_impedance(result.z_matrix, z0_ohm=REFERENCE_IMPEDANCE_OHM)
    return (
        float(np.linalg.norm(s_old - s_old.T) / np.linalg.norm(s_old)),
        _pair_ratio(s_old),
    )


@complex_only
def test_the_symmetric_control_is_reciprocal_on_the_fixed_route(asymmetric_sweeps):
    """**Anchor (a), control half.**  ``f = 0.5 / 0.5`` at the matched drive.

    Leg (d2)'s version of this test reproduced step 2c's 2.574249e-11, which was
    the *terminated conversion's* residual on a symmetric fixture at the 1e6 Ohm
    probe.  Leg (d3) changes both the assembly (power waves) and the termination
    (``Z_p = z0 = 50 Ohm``), so that digit is history, not a target — it is
    printed beside the new reading and never asserted.  What is asserted is the
    fixed route's own gate, on the fixture whose symmetry cannot fail it: an
    equivalent-port sweep that misses ``1e-6`` would mean the assembly itself is
    broken and nothing below is a reading of the asymmetry.
    """
    r = asymmetric_sweeps["control"]["result"]
    ratio, z_ratio = _reciprocity(r)
    pair = _pair_ratio(r.s_matrix)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d3] ANCHOR (a) CONTROL f = 0.5 / 0.5, "
            f"Z_p = z0 = {PORT_IMPEDANCE_OHM:.0f} Ohm, power-wave S "
            f"(band {FIXED_ROUTE_BAND:.0e}):\n"
            f"    ||S - S^T||/||S|| = {ratio:.9e}   per-pair = {pair:.9e}\n"
            f"    ||Z - Z^T||/||Z|| = {z_ratio:.9e}  (terminated Z, diagnostic)\n"
            f"    leg (d2) history at Z_p = 1e6 Ohm through the terminated "
            f"conversion: {STEP2C_RECIPROCITY_RECORD:.6e} (step 2c's record, "
            f"not a target here)",
            flush=True,
        )

    assert ratio <= FIXED_ROUTE_BAND, (
        f"the symmetric control reads ||S - S^T||/||S|| = {ratio:.9e} against "
        f"the pre-stated {FIXED_ROUTE_BAND:.0e} — the power-wave assembly is "
        "not reciprocal even on equivalent ports, so nothing below reads the "
        "asymmetry"
    )
    assert pair <= FIXED_ROUTE_BAND, (
        f"the symmetric control's per-pair asymmetry is {pair:.9e} against "
        f"{FIXED_ROUTE_BAND:.0e}"
    )


@complex_only
def test_the_asymmetric_two_port_is_reciprocal(asymmetric_sweeps):
    """**Anchor (a), the leg's gate.**  0.5 / 0.735 at the matched drive.

    Leg (d2) left this fixture reading a 0.25% *per-pair* asymmetry through the
    terminated conversion, traced to ``_assemble_impedance_matrix`` normalising
    each column by the driven port's own current.  Ruling (2\\*) fixed it at the
    assembly: S now comes from power waves, and at ``Z_p = z0`` the driven
    current drops out, leaving ``S_ij ∝ I_i(drive j)`` — symmetric by the
    transadmittance identity the next test re-measures.

    Both statistics are gated at ``1e-6`` **while the old conversion, computed
    in the same run from the retained terminated ``Z``, must still read at least
    ``1e-4``** — the mechanism's own negative control, at least 100x separation.
    A fixed route missing the gate refutes ruling (2\\*)'s mechanism; the bands
    are never widened to admit either outcome.
    """
    r = asymmetric_sweeps["asymmetric"]["result"]
    ratio, z_ratio = _reciprocity(r)
    pair = _pair_ratio(r.s_matrix)
    old_ratio, old_pair = _old_conversion(r)
    z = r.z_matrix
    z_pair = z[0, 1] / z[1, 0]
    control_ratio, _ = _reciprocity(asymmetric_sweeps["control"]["result"])

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d3] ANCHOR (a) ASYMMETRIC f = 0.5 / 0.735, "
            f"Z_p = z0 = {PORT_IMPEDANCE_OHM:.0f} Ohm "
            f"(gate {FIXED_ROUTE_BAND:.0e}, control floor "
            f"{OLD_CONVERSION_FLOOR:.0e}, step 2's {RECIPROCITY_BAND:.0e} "
            f"unmoved above both):\n"
            f"    FIXED (power waves)      ||S - S^T||/||S|| = {ratio:.9e}   "
            f"per-pair = {pair:.9e}\n"
            f"    OLD (terminated Z -> S)  ||S - S^T||/||S|| = {old_ratio:.9e}   "
            f"per-pair = {old_pair:.9e}\n"
            f"    separation: {old_pair / max(pair, 1e-300):.6e} x on the "
            f"per-pair statistic\n"
            f"    control (symmetric fixture) fixed route: {control_ratio:.9e}\n"
            f"    ||Z - Z^T||/||Z|| = {z_ratio:.9e}  (terminated Z, diagnostic)\n"
            f"    |Z12/Z21| = {abs(z_pair):.9f}, "
            f"phase = {np.degrees(np.angle(z_pair)):+.9f} deg\n"
            f"    Z12 = {z[0, 1]:+.9e} Ohm, Z21 = {z[1, 0]:+.9e} Ohm\n"
            f"    Z11 = {z[0, 0]:+.9e} Ohm, Z22 = {z[1, 1]:+.9e} Ohm",
            flush=True,
        )

    assert old_pair >= OLD_CONVERSION_FLOOR, (
        f"the retired terminated-Z conversion reads a per-pair asymmetry of "
        f"only {old_pair:.9e} on this fixture, below the pre-stated "
        f"{OLD_CONVERSION_FLOOR:.0e} negative-control floor — there is nothing "
        "here for the power-wave assembly to have fixed, so the gate below is "
        "not evidence for ruling (2*)"
    )
    assert ratio <= FIXED_ROUTE_BAND, (
        f"the asymmetric two-port reads ||S - S^T||/||S|| = {ratio:.9e} on the "
        f"power-wave route against the pre-stated {FIXED_ROUTE_BAND:.0e} "
        f"(old conversion {old_ratio:.9e} in the same run) — ruling (2*)'s "
        "mechanism is refuted: the asymmetry is not (only) the terminated-Z "
        "normalisation (§7 `PORT-9` leg (d3), negative result: §7 annotation + "
        "known-issues quoting this number, nothing re-recorded, stop)"
    )
    assert pair <= FIXED_ROUTE_BAND, (
        f"the asymmetric two-port's per-pair asymmetry is {pair:.9e} on the "
        f"power-wave route against {FIXED_ROUTE_BAND:.0e} (old conversion "
        f"{old_pair:.9e}) — the Frobenius norm passed and the pair-resolved "
        "statistic did not, exactly the grain leg (d2) warned about"
    )


@complex_only
def test_the_field_readout_is_the_sources_adjoint(asymmetric_sweeps):
    """**Mechanism, first half of A′.**  ``I_i(drive j) = I_j(drive i)``.

    The direct, assembly-free test of the review's hypothesis A.  The source of
    port ``j`` is built from ``f_j[k] = ∫_{S_j} ĥ_j·v_k dS`` and the current
    readout of port ``i`` is ``(1/(R_i h_i)) f_iᵀ x`` — the same facet set and
    the same weighting — so with a complex-symmetric operator the off-diagonal
    transadmittance is exactly symmetric on *any* mesh, equivalent ports or
    not.  If this holds while anchor (b) misses, the asymmetry is not in the
    readout at all but one level up, in the ``Z`` assembly (the next test).
    """
    comm = MPI.COMM_WORLD
    rows = []
    for key in ("control", "asymmetric"):
        r = asymmetric_sweeps[key]["result"]
        i_12 = r.excitation_results["P2"].responses["P1"].current_a  # drive P2, read P1
        i_21 = r.excitation_results["P1"].responses["P2"].current_a  # drive P1, read P2
        rows.append((key, i_12, i_21, _rel(i_12, i_21)))

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3d2] MECHANISM A' (i): transadmittance symmetry "
            f"I_1(drive 2) vs I_2(drive 1), band {MECHANISM_BAND:.0e} relative:",
            flush=True,
        )
        for key, i_12, i_21, dev in rows:
            print(
                f"    {key:11s}  I_1(d2) = {i_12:+.9e} A   "
                f"I_2(d1) = {i_21:+.9e} A   rel dev = {dev:.9e}",
                flush=True,
            )

    for key, i_12, i_21, dev in rows:
        assert dev <= MECHANISM_BAND, (
            f"{key}: the off-diagonal transadmittance is not symmetric — "
            f"I_1(drive 2) = {i_12:+.9e} A against I_2(drive 1) = {i_21:+.9e} A, "
            f"relative deviation {dev:.9e} above the pre-stated "
            f"{MECHANISM_BAND:.0e}. The current readout is then NOT the "
            "impressed source's adjoint and hypothesis A' is refuted"
        )


@complex_only
def test_the_z_asymmetry_is_the_per_column_normalisation(asymmetric_sweeps):
    """**Mechanism, second half of A′.**  ``Z12/Z21 = I_1(drive 1)/I_2(drive 2)``.

    ``_assemble_impedance_matrix`` divides column ``j`` by the *driven* port's
    own total current, so what it calls ``Z`` is a terminated transimpedance,
    not the open-circuit impedance matrix reciprocity makes symmetric.  With
    ``V_i = −Z_p I_i`` at the undriven ports and the transadmittance symmetry
    of the previous test, ``Z_ij/Z_ji`` collapses exactly to the ratio of the
    two driven-port self-currents — 1 for equivalent ports, and nothing in
    particular otherwise.  Asserted on both sweeps at the same pre-stated
    1e-6: it is an identity, so the control must satisfy it too.
    """
    comm = MPI.COMM_WORLD
    rows = []
    for key in ("control", "asymmetric"):
        r = asymmetric_sweeps[key]["result"]
        z = r.z_matrix
        measured = complex(z[0, 1] / z[1, 0])
        i_11 = r.excitation_results["P1"].responses["P1"].current_a
        i_22 = r.excitation_results["P2"].responses["P2"].current_a
        predicted = complex(i_11 / i_22)
        rows.append((key, measured, predicted, _rel(measured, predicted)))

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3d2] MECHANISM A' (ii): Z12/Z21 against the "
            f"driven-port self-current ratio I_1(d1)/I_2(d2), band "
            f"{MECHANISM_BAND:.0e} relative:",
            flush=True,
        )
        for key, measured, predicted, dev in rows:
            print(
                f"    {key:11s}  Z12/Z21 = {measured:+.9e}   "
                f"I_1(d1)/I_2(d2) = {predicted:+.9e}   rel dev = {dev:.9e}",
                flush=True,
            )

    for key, measured, predicted, dev in rows:
        assert dev <= MECHANISM_BAND, (
            f"{key}: Z12/Z21 = {measured:+.9e} does not equal the driven-port "
            f"self-current ratio {predicted:+.9e} (relative deviation "
            f"{dev:.9e} above the pre-stated {MECHANISM_BAND:.0e}) — the "
            "terminated-Z assembly is not the mechanism, and hypothesis A' is "
            "refuted in its second half"
        )
