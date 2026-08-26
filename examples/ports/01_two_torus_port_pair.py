"""Gap-voltage port pair on the two-torus fixture: solved field → Z → S.

`EX-18`.  The first example in this repository that produces **port** quantities
from a solved field.  Everything before it exports fields (magnetostatic ``A``
and ``B``, plane-wave and cavity ``E``, SAR); this one drives two lumped ports,
reads a 2x2 impedance matrix off the solution and converts it to scattering
parameters at ``Z0 = 50 Ohm``.

What is demonstrated is exactly the capability `PORT-1` steps 3b-xvii/3b-xviii
gated on 2026-08-13, and nothing beyond it:

  * the **gapped two-torus fixture** — two partial tori (cell tags 1/2), each
    bridged by a rectangular dielectric gap box (tags 101/102), all fragmented
    conformally into one air box (tag 3) inside a PEC truncation box;
  * one solve per port, driven by an impressed ``+yhat`` current density across
    that port's gap box, with the conductors at ``sigma = 800 S/m``;
  * ``I_k`` from the meshed conduction current, ``V_i`` from the
    **terminal-to-terminal** tangential path integral ``-\\int E.that dl`` along
    the centreline arc, and ``Z_ik = V_i / I_k``;
  * the two **named, measured systematics** applied through
    :func:`fem_em_solver.ports.systematics.mutual_systematics_ladder` — the PEC
    box (``D_inf = +1.69 pp`` of ratio at ``p = 1.657``, an effective-range
    extrapolation) and the gap-generator feed model's gap physics
    (``div (1 - 0.030224)``, Jin 3e §10.4.2.1);
  * ``S = (Z - Z0 I)(Z + Z0 I)^-1`` through
    :func:`fem_em_solver.ports.sparameters.sparameters_from_impedance`.

**The raw number is on the record as a miss.**  The ladder is printed rung by
rung, raw first: the uncorrected mutual is ``0.894283 x omega*M12``, i.e.
**-10.57%** against the filamentary closed form, which the unmoved 10% band
would *not* accept.  Only after both systematics does it read ``0.939581``
(-6.04%).  An example that printed the corrected number alone would be
advertising a gate that does not exist.

**What this example is not.**  It is not a birdcage port, not an ``S11`` claim
(``PORT-1`` step 2b localised an electric-energy excess on this fixture's
diagonal — no ``Z_in`` and no ``S11`` may be read off it), and not a general
port capability: `PORT-1` stays 🟡 and the package's *other* S-parameter path
(``ports/excitation.py``) is still the ⚠️ heuristic of known-issues 3.  The two
systematics are specific to this geometry at this padding and must be
re-measured anywhere else.

**Anchor.**  Every asserted number is an allreduced reproduction of the digits
recorded in ``docs/testing/20260813T020352Z_PORT-1-step3bxviii-pairgate-n2.log``
(bands looser than the recorded digits, never tighter).  The negative control is
cited rather than recomputed: step 1's *unfragmented* ancestor of this fixture
returned ``Im Z12`` identically zero
(``20260731T213222Z_PORT-1-step1-costprobe.log``), and running the same ladder
on that number lands at **-98.26%**, which the example asserts *fails* the band
— a band that accepted the blind fixture would be gating nothing.

Run (complex build required)::

    ./run_examples.sh -e ports:1
    ./run_examples.sh -e ports:1 -n 2 -t 570

Outputs ``paraview_output/two_torus_port_pair_combined.xdmf`` (mesh + CellTags +
the port-1 drive's ``E`` fields; threshold on ``CellTags`` to see the gap boxes).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.ports.sparameters import sparameters_from_impedance
from fem_em_solver.ports.systematics import (
    GAP_PHYSICS_SYSTEMATIC,
    PEC_BOX_SYSTEMATIC,
    PEC_BOX_SYSTEMATIC_EXPONENT,
    mutual_systematics_ladder,
)
from fem_em_solver.post.evaluation import evaluate_vector_field_parallel
from fem_em_solver.utils.analytical import AnalyticalSolutions

# ---------------------------------------------------------------------------
# The fixture.  Restated from the gate modules rather than imported: examples
# run with PYTHONPATH=/workspace/src and must not depend on `tests/`.  Every
# value below is the landed fixture's, and the example *measures* the
# consequences (terminal angles, meshed volumes) rather than trusting them —
# a drift in any of them fails the pre-solve geometry check, not the anchor.
#   tests/validation/test_port_reaction_impedance.py (geometry, frequency)
#   tests/validation/test_port_gap_voltage_impedance.py (gap, sigma, quadrature)
FREQUENCY_HZ = 10.0e6
OMEGA = 2.0 * np.pi * FREQUENCY_HZ
MAJOR_RADIUS = 0.04  # a
MINOR_RADIUS = 0.005  # r_wire
SEPARATION = 0.04  # d, centre to centre along z
AIR_PADDING = 0.08
H_FAR = 0.03
H_WIRE = 0.0025

GAP_ANGLE = 0.30
GAP_BURIAL = 1.0e-3
GAP_OVERHANG = 2.0e-4
GAP_ARC_RESOLUTION = 3.0e-4

WIRE_TAGS = (1, 2)
GAP_TAGS = (101, 102)
AIR_TAG = 3
PORT_FACET_TAGS = (201, 202)

# delta = sqrt(2/(omega*mu0*sigma)) = 5.63 mm = 1.13 r_wire: the current path is
# inside a skin depth, which is what makes it resolvable at h_wire.
SIGMA_WIRE_S_PER_M = 8.0e2
DRIVE_CURRENT_A = 1.0

REFERENCE_IMPEDANCE_OHM = 50.0

# Step 3b-x's converged quadrature order for the terminal-to-terminal path
# integral.  The gate module sweeps (33 ... 4097) to measure the rate; the
# example takes the gated order only, and certifies it against the order below
# it rather than trusting the sweep on record.
PATH_QUADRATURE_GATE_ORDERS = (2049, 4097)
PATH_QUADRATURE_TOLERANCE = 1.0e-3

# The geometry identity that must hold before any solve is bought: the 201/202
# facets are the conductor/dielectric cut and lie in the gap box's own y faces,
# so arcsin(<y>_facet / a) is arcsin(half_y / a) exactly.
TERMINAL_ANGLE_TOLERANCE = 1.0e-6

# ---------------------------------------------------------------------------
# The anchor.  Recorded digits from
# docs/testing/20260813T020352Z_PORT-1-step3bxviii-pairgate-n2.log; the bands
# are deliberately looser than the digits they cite (a reproduction band, not a
# re-derivation of the gate) and are never to be tightened onto the measurement.
RECORDED_RAW_RATIO = 0.894283
RECORDED_CORRECTED_RATIO = 0.939581
# EX-30 leg (ports) re-record, 2026-08-26, under the same in-class (1*) licence
# as ports:2 (PROJECT_PLAN §9 item 3).  These two are **printed beside the
# measurement, never asserted** here — this example's gates are the two mutual
# ratios above — but their v0.7.2 digits (2.5494e-05 / 0.861449) had gone stale
# against what this route now produces, so the print read as a drift that is not
# one.  This example assembles S with `sparameters_from_impedance`, i.e. the
# *terminated-Z conversion* route, not ports:2's power-wave assembly, so the
# route-current digits are the v0.11.0 terminated-Z ones the gate module
# tests/validation/test_port_package_sparameters.py carries in-comment beside
# RECORDED_S_SYMMETRY_RATIO / RECORDED_PASSIVITY_MAX_SIGMA: 3.11213e-05 and
# 0.861356895 on its 184 176-cell mesh.  Measured here this slot on 177 998
# cells: 3.1121e-05 and 0.861357
# (20260826T123139Z_EX-30-ports-run-1to2.log).  Old digits kept above; nothing
# asserted changed and no band moved.
RECORDED_S_SYMMETRY_RESIDUAL = 3.11213e-05
RECORDED_S_SPECTRAL_NORM = 0.861356895

# |raw - recorded| band: 7.7x the difference between the 3b-xviii digit and the
# 3b-xi padding-sweep record at the same padding (0.894543 - 0.894283 = 2.60e-4),
# so a partition or lineage difference of that size passes and a real drift does
# not.  (The factor read "400x" until 2026-08-15: an ~50x overstatement of the
# margin, found by the 2026-08-13 daily review's step-3 audit.  The band value
# itself is unchanged — only the comment was wrong.)
RAW_REPRODUCTION_BAND = 2.0e-3
# PORT-1's own mutual band, unmoved since 3b-ii.  This is the gate the corrected
# ratio must sit inside, and the blind fixture must sit outside.
MUTUAL_TOLERANCE = 0.10
# 40x the recorded 2.5494e-05: Z is assembled from two independent solves with
# different integrands, so symmetry is a measured network identity here, not an
# algebraic one.
S_SYMMETRY_BAND = 1.0e-3
# Passivity is an inequality, not a reproduction: ||S||_2 <= 1 for a passive
# 2-port, and the record 0.861449 is printed beside it.
S_SPECTRAL_NORM_CEILING = 1.0

# Step 1's unfragmented-mesh record: the two loops meshed as disconnected
# islands, Im Z12 was *identically* zero
# (20260731T213222Z_PORT-1-step1-costprobe.log).  Cited, not recomputed.
BLIND_FIXTURE_IM_Z12_OHM = 0.0

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "two_torus_port_pair"


def _mutual_inductance(a: float, rho: float, z: float) -> float:
    """``M = 2*pi*rho*A_phi(rho, z)/I`` for a unit-current filamentary loop."""
    pts = np.array([[rho, 0.0, z]], dtype=float)
    A = AnalyticalSolutions.circular_loop_vector_potential(pts, 1.0, a, loop_center=0.0)
    # At (x = rho, y = 0) the azimuthal direction is +y.
    return 2.0 * np.pi * rho * float(A[0, 1])


def _reduce(form, comm) -> complex:
    """``assemble_scalar`` is rank-local — reduce before anyone reads it."""
    return complex(comm.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM))


def _tag_measure(msh, cell_tags, tag):
    return ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))


def _tag_volume(msh, cell_tags, tag, comm) -> float:
    one = fem.Constant(msh, default_scalar_type(1.0))
    return float(np.real(_reduce(one * _tag_measure(msh, cell_tags, tag), comm)))


def _gap_half_extents():
    """The gap box, recomputed from the same expressions as ``io/mesh``."""
    half_xz = MINOR_RADIUS + GAP_OVERHANG
    half_y = MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE) + GAP_BURIAL
    return half_xz, half_y


def _gap_box_edge_angle() -> float:
    """``|phi|`` at which the centreline leaves the gap box.

    The box spans ``|y| <= half_y`` and the centreline has ``y = a sin phi``, so
    the dielectric reaches ``arcsin(half_y / a)`` — strictly outside the nominal
    wedge ``gap_angle/2``, because ``GAP_BURIAL > 0``.  Step 3b-x's whole
    finding is that the 0.8% of loop length between the wedge and this angle
    carries 45% of the EMF, so the estimator's limits are *this* angle's.
    """
    _, half_y = _gap_half_extents()
    return float(np.arcsin(half_y / MAJOR_RADIUS))


def _azimuthal_unit(x):
    rho = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
    return ufl.as_vector([-x[1] / rho, x[0] / rho, 0.0])


def _arc_quadrature(port_index: int, phi_start: float, phi_end: float, order: int):
    """Gauss-Legendre nodes on ``(phi_start, phi_end)`` of the centreline circle.

    Legendre nodes are strictly inside ``(-1, 1)``, so the terminals themselves
    — where a point locates into a cell on either side of the material
    interface — are never sampled.  ``that(0) = +yhat``, so ``V`` carries the
    same sign convention the gate module's four estimators share.
    """
    nodes, weights = np.polynomial.legendre.leggauss(order)
    midpoint = 0.5 * (phi_start + phi_end)
    half_span = 0.5 * (phi_end - phi_start)
    phi = midpoint + half_span * nodes
    z_c = (-1.0) ** (port_index + 1) * SEPARATION / 2.0
    points = np.column_stack(
        [
            MAJOR_RADIUS * np.cos(phi),
            MAJOR_RADIUS * np.sin(phi),
            np.full_like(phi, z_c),
        ]
    )
    tangents = np.column_stack([-np.sin(phi), np.cos(phi), np.zeros_like(phi)])
    return points, tangents, half_span * weights


def _path_voltage(e_field, port_index: int, order: int, comm) -> complex:
    """``V = -\\int E.that dl`` terminal to terminal, ``order``-point Gauss.

    Sampling goes through
    :func:`~fem_em_solver.post.evaluation.evaluate_vector_field_parallel`, never
    ``f.eval`` — the points are collective and each rank owns only some of the
    cells they land in.
    """
    phi_term = _gap_box_edge_angle()
    points, tangents, weights = _arc_quadrature(port_index, -phi_term, phi_term, order)
    values, valid = evaluate_vector_field_parallel(e_field, points, comm)
    if not bool(np.all(valid)):
        raise RuntimeError(
            f"port {port_index + 1}: {int((~valid).sum())} of {order} arc "
            "quadrature points located in no cell — the centreline path left "
            "the mesh"
        )
    e_tangential = np.einsum("ij,ij->i", values, tangents)
    return complex(-MAJOR_RADIUS * np.sum(weights * e_tangential))


def _measure_terminal_angles(msh, facet_tags, comm):
    """``arcsin(y_extreme / a)`` on each signed half of each port facet pair.

    The 201/202 facets are the gap/conductor interface, and the far reach of
    that interface along the loop is the gap box's ``y = +-half_y`` face where it
    cuts the tube — so the estimator's integration limit is
    ``arcsin(y_extreme / a)`` with ``y_extreme`` the extreme ``y`` the tagged
    facets attain.

    **The extreme and not the mean.**  At ``GAP_OVERHANG = 2e-4 < 6e-4`` the
    tube protrudes through the gap box's ``-x`` face, so the tag picks up
    *lateral strips* of tube surface at ``|y| < half_y`` alongside the two
    planar discs (known-issues 11), and an area-weighted ``<y>`` over disc +
    strips reads 0.173852 rad against the exact 0.175335.  Every strip point
    lies inside the box, so none can exceed the face, and a plane meshed by
    linear elements is exact — which is why 1e-6 is a fair bound on the
    extreme and would be a wrong one on the mean.
    """
    import dolfinx

    tdim = msh.topology.dim
    angles = []
    for tag in PORT_FACET_TAGS:
        facets = facet_tags.find(tag)
        nodes = dolfinx.cpp.mesh.entities_to_geometry(
            msh._cpp_object, tdim - 1, np.asarray(facets, dtype=np.int32), False
        )
        y_nodes = msh.geometry.x[nodes][:, :, 1]
        facet_side = np.sign(y_nodes.mean(axis=1))

        pair = []
        for sign in (1.0, -1.0):
            selected = y_nodes[facet_side == sign]
            # A rank may own no facet of this half; -inf loses the MAX.
            local = float(np.max(sign * selected)) if selected.size else -np.inf
            y_extreme = sign * float(comm.allreduce(local, op=MPI.MAX))
            pair.append(float(np.arcsin(y_extreme / MAJOR_RADIUS)))
        angles.append(pair)
    return angles


def _gap_drive(j_magnitude: float):
    """Impressed current density across a gap box, along ``+yhat``.

    At the gap (``x ~ +a``, ``y ~ 0``) the azimuthal direction *is* ``+yhat``,
    so this drives the loop the way a lumped source across the gap would.  It is
    **not** solenoidal — it terminates on the arc end faces, where the
    conduction current ``sigma E`` takes over and closes the loop — hence
    ``project_source=False``: the divergence here is the physics, not the
    discrete-gradient artefact `PORT-1` step 2f removes.
    """

    def current_density(x):
        return ufl.as_vector([0.0, j_magnitude, 0.0])

    return current_density


def _paraview_fields(msh, fields):
    """CG1 ``E_real`` / ``E_imag`` / ``E_magnitude`` from the solved phasor.

    XDMF cannot carry N1curl, and the VTX/XDMF writers take Lagrange
    interpolants only (`EX-14`/`EX-17`).
    """
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    e_cg = fem.Function(v_cg, name="E_phasor")
    e_cg.interpolate(fields.e_complex)
    e_cg.x.scatter_forward()

    e_re = fem.Function(v_cg, name="E_real")
    e_re.x.array[:] = np.real(e_cg.x.array)
    e_im = fem.Function(v_cg, name="E_imag")
    e_im.x.array[:] = np.imag(e_cg.x.array)

    s_cg = fem.functionspace(msh, ("Lagrange", 1))
    e_mag = fem.Function(s_cg, name="E_magnitude")
    components = np.abs(e_cg.x.array.reshape(-1, 3))
    e_mag.x.array[:] = np.sqrt(np.sum(components * components, axis=1))

    for f in (e_re, e_im, e_mag):
        f.x.scatter_forward()
    return e_re, e_im, e_mag


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print("EX-18 — gap-voltage port pair -> Z -> S (two-torus fixture)", flush=True)
        print("=" * 78, flush=True)

    # -- the fixture ------------------------------------------------------
    t_mesh = time.perf_counter()
    msh, cell_tags, facet_tags = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=AIR_PADDING,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_burial=GAP_BURIAL,
        gap_overhang=GAP_OVERHANG,
        gap_arc_resolution=GAP_ARC_RESOLUTION,
        comm=comm,
    )
    t_mesh = time.perf_counter() - t_mesh

    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    # Every rank, unconditionally, before any facet form: the assembler reaches
    # `create_entity_permutations` lazily and only on ranks owning integration
    # entities, and this partition gives each rank exactly one port — a per-port
    # `dS` form entered the collective on one rank only and hung at -n 2
    # (PORT-1 step 3b-iv, known-issues 9, retired).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    if comm.rank == 0:
        print(
            f"[EX-18] mesh: {ncells} cells in {t_mesh:.1f} s "
            f"(padding {AIR_PADDING}, gap arc {GAP_ARC_RESOLUTION:.1e})",
            flush=True,
        )

    _, half_y = _gap_half_extents()
    gap_length = 2.0 * half_y
    # Cross-sections and arc lengths from the *meshed* volumes: a mesh that lost
    # part of the gap box shows up in V rather than being papered over by
    # analytic geometry.  The gap box buries into the arc ends, so a(2*pi - g)
    # overstates the conductor by the 3.6% step 3b-i measured.
    gap_areas = [_tag_volume(msh, cell_tags, t, comm) / gap_length for t in GAP_TAGS]
    wire_volumes = [_tag_volume(msh, cell_tags, t, comm) for t in WIRE_TAGS]
    arc_lengths = [v / (np.pi * MINOR_RADIUS**2) for v in wire_volumes]

    # -- pre-solve geometry check ----------------------------------------
    terminal_angles = _measure_terminal_angles(msh, facet_tags, comm)
    phi_term_expected = _gap_box_edge_angle()
    if comm.rank == 0:
        print(
            f"[EX-18] terminal angles from facet tags {PORT_FACET_TAGS}: "
            + "; ".join(
                f"port {k + 1} y>0 {pair[0]:+.9f}, y<0 {pair[1]:+.9f} rad"
                for k, pair in enumerate(terminal_angles)
            )
            + f" (expected +-{phi_term_expected:.9f} = arcsin(half_y/a), nominal "
            f"wedge +-{0.5 * GAP_ANGLE:.9f}, tolerance "
            f"{TERMINAL_ANGLE_TOLERANCE:.1e})",
            flush=True,
        )
    for k, pair in enumerate(terminal_angles):
        for s, (measured, expected) in enumerate(
            zip(pair, (phi_term_expected, -phi_term_expected))
        ):
            if abs(measured - expected) >= TERMINAL_ANGLE_TOLERANCE:
                raise RuntimeError(
                    f"port {k + 1}, {'y>0' if s == 0 else 'y<0'} terminal: the "
                    f"facet tags put the conductor/dielectric cut at "
                    f"{measured:+.9f} rad, the estimator's limit is "
                    f"{expected:+.9f} rad — the integration limits have drifted "
                    "from the meshed geometry"
                )

    # -- one solve per port ----------------------------------------------
    x_ufl = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_unit(x_ufl)

    z_matrix = np.zeros((2, 2), dtype=complex)
    solve_times = []
    paraview_fields = None
    for col, driven_gap in enumerate(GAP_TAGS):
        problem = TimeHarmonicProblem(
            mesh=msh,
            frequency_hz=FREQUENCY_HZ,
            material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
            cell_tags=cell_tags,
            material_map={
                tag: HomogeneousMaterial(
                    sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0
                )
                for tag in WIRE_TAGS
            },
            boundary_condition="pec_zero_tangential_a",
        )
        solver = TimeHarmonicSolver(problem, degree=1)
        comm.Barrier()
        t0 = time.perf_counter()
        fields = solver.solve(
            current_density=_gap_drive(DRIVE_CURRENT_A / gap_areas[col]),
            subdomain_ids=[driven_gap],
            project_source=False,
        )
        comm.Barrier()
        solve_times.append(time.perf_counter() - t0)

        e = fields.e_complex
        # I_k = (1/L_k) \int_{wire k} sigma E.phihat dV, on the meshed arc length.
        loop_currents = [
            SIGMA_WIRE_S_PER_M
            * _reduce(ufl.inner(e, phi_hat) * _tag_measure(msh, cell_tags, tag), comm)
            / arc_lengths[k]
            for k, tag in enumerate(WIRE_TAGS)
        ]
        i_driven = loop_currents[col]

        # V at both gate orders off this one solve: the coarse one certifies the
        # fine one before the fine one is compared to anything.  Quadrature
        # convergence is free; the solve is not.
        voltages_by_order = {
            order: [_path_voltage(e, p, order, comm) for p in range(2)]
            for order in PATH_QUADRATURE_GATE_ORDERS
        }
        coarse, fine = PATH_QUADRATURE_GATE_ORDERS
        for p in range(2):
            v_c, v_f = voltages_by_order[coarse][p], voltages_by_order[fine][p]
            rel = abs(v_f - v_c) / abs(v_f)
            # Step 3b-x's standing disposition: the precondition gates the
            # *undriven* port and prints the driven one.  With terminal-to-
            # terminal limits the driven port's path runs through the impressed
            # source's own terminals and its integral does not converge in the
            # quadrature at all (2.3e-2 at 4097, on record) — that is a property
            # of Z11, which nothing here reads.  The mutual is built from the
            # undriven port, where the same sweep reaches 3.9e-4.
            gated = p != col
            role = "gated" if gated else "printed, the driven diagonal"
            if comm.rank == 0:
                print(
                    f"[EX-18] port {col + 1} driven: V_path port {p + 1} "
                    f"({role}) = {v_f:+.9e} V (order {fine}; |dV|/|V| vs order "
                    f"{coarse} = {rel:.4e}, precondition "
                    f"{PATH_QUADRATURE_TOLERANCE:.1e})",
                    flush=True,
                )
            if not gated:
                continue
            assert rel < PATH_QUADRATURE_TOLERANCE, (
                f"port {p + 1}: the path integral is not converged in the "
                f"quadrature ({rel:.4e} >= {PATH_QUADRATURE_TOLERANCE:.1e}) — "
                "the voltage says nothing about the field yet"
            )

        path_voltages = voltages_by_order[fine]
        for row in range(2):
            z_matrix[row, col] = path_voltages[row] / i_driven

        if comm.rank == 0:
            print(
                f"[EX-18] port {col + 1} driven (gap tag {driven_gap}): "
                f"I_driven = {i_driven:+.6e} A, I_undriven = "
                f"{loop_currents[1 - col]:+.6e} A (ratio "
                f"{abs(loop_currents[1 - col]) / abs(i_driven):.4e} — the "
                f"undriven gap is a ~7e-14 F series C, open to four orders); "
                f"solve {solve_times[-1]:.1f} s",
                flush=True,
            )

        if col == 0:
            paraview_fields = _paraview_fields(msh, fields)

    # -- Z, the ladder, S -------------------------------------------------
    omega_m12 = OMEGA * _mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    driven_column = 0
    im_z12 = float(z_matrix[1 - driven_column, driven_column].imag)
    ladder = mutual_systematics_ladder(im_z12, omega_m12)
    blind = mutual_systematics_ladder(BLIND_FIXTURE_IM_Z12_OHM, omega_m12)

    s_matrix = sparameters_from_impedance(z_matrix, z0_ohm=REFERENCE_IMPEDANCE_OHM)
    s_symmetry = float(
        np.linalg.norm(s_matrix - s_matrix.T) / np.linalg.norm(s_matrix)
    )
    s_spectral = float(np.linalg.norm(s_matrix, 2))
    reciprocity = float(
        abs(z_matrix[0, 1] - z_matrix[1, 0]) / abs(z_matrix[0, 1])
    )

    if comm.rank == 0:
        print("-" * 78, flush=True)
        print(
            f"[EX-18] closed form: M12 = {omega_m12 / OMEGA:.6e} H, "
            f"omega*M12 = {omega_m12:.6f} Ohm (Jackson 5.37, filamentary)",
            flush=True,
        )
        print(
            f"[EX-18] Z (Ohm):\n"
            f"    Z11 = {z_matrix[0, 0]:+.6e}   Z12 = {z_matrix[0, 1]:+.6e}\n"
            f"    Z21 = {z_matrix[1, 0]:+.6e}   Z22 = {z_matrix[1, 1]:+.6e}",
            flush=True,
        )
        print(
            f"[EX-18] reciprocity |Z12 - Z21|/|Z12| = {reciprocity:.4e} "
            "(two solves, two integrands, one operator — a measured network "
            "identity, printed not gated here)",
            flush=True,
        )
        print(
            f"[EX-18] systematics ladder vs omega*M12 (Im Z12 = "
            f"{im_z12:+.9e} Ohm):\n"
            f"    raw            {ladder['raw']:.6f} "
            f"({100.0 * ladder['raw_deviation']:+.2f}%)  <- a MISS against the "
            f"{100.0 * MUTUAL_TOLERANCE:.0f}% band\n"
            f"    + PEC box      {ladder['box_corrected']:.6f} "
            f"({100.0 * ladder['box_deviation']:+.2f}%)  D_inf = "
            f"{PEC_BOX_SYSTEMATIC:+.4f} at p = {PEC_BOX_SYSTEMATIC_EXPONENT} "
            "(effective range — never quote without the exponent)\n"
            f"    + gap physics  {ladder['corrected']:.6f} "
            f"({100.0 * ladder['deviation']:+.2f}%)  div (1 "
            f"{GAP_PHYSICS_SYSTEMATIC:+.6f}), Jin 3e §10.4.2.1",
            flush=True,
        )
        print(
            f"[EX-18] negative control (step 1's unfragmented fixture, "
            f"Im Z12 = {BLIND_FIXTURE_IM_Z12_OHM:.1f} Ohm, cited from "
            "20260731T213222Z_PORT-1-step1-costprobe.log): the same ladder "
            f"gives {blind['corrected']:.6f} "
            f"({100.0 * blind['deviation']:+.2f}%) — asserted to FAIL the band",
            flush=True,
        )
        print(
            f"[EX-18] S at Z0 = {REFERENCE_IMPEDANCE_OHM:.0f} Ohm:\n"
            f"    S11 = {s_matrix[0, 0]:+.6e}   S12 = {s_matrix[0, 1]:+.6e}\n"
            f"    S21 = {s_matrix[1, 0]:+.6e}   S22 = {s_matrix[1, 1]:+.6e}\n"
            f"    ||S - S^T||/||S|| = {s_symmetry:.4e} (record "
            f"{RECORDED_S_SYMMETRY_RESIDUAL:.4e}), ||S||_2 = {s_spectral:.6f} "
            f"(record {RECORDED_S_SPECTRAL_NORM:.6f})",
            flush=True,
        )
        print(
            "[EX-18] S11/S22 are NOT a claim: PORT-1 step 2b localised an "
            "electric-energy excess on this fixture's diagonal, so no Z_in and "
            "no S11 may be read off it.  The gated quantity is the mutual.",
            flush=True,
        )
        print("-" * 78, flush=True)

    # -- the gates --------------------------------------------------------
    # Every number below is allreduced (the volumes and currents through
    # `_reduce`, the path voltages through `evaluate_vector_field_parallel`), so
    # each rank asserts the same thing.
    assert abs(ladder["raw"] - RECORDED_RAW_RATIO) < RAW_REPRODUCTION_BAND, (
        f"raw mutual {ladder['raw']:.6f} does not reproduce the 3b-xviii record "
        f"{RECORDED_RAW_RATIO:.6f} within {RAW_REPRODUCTION_BAND:.1e} — lineage "
        "or environment drift, not a tolerance to widen"
    )
    assert (
        abs(ladder["corrected"] - RECORDED_CORRECTED_RATIO) < RAW_REPRODUCTION_BAND
    ), (
        f"corrected mutual {ladder['corrected']:.6f} does not reproduce the "
        f"record {RECORDED_CORRECTED_RATIO:.6f} within "
        f"{RAW_REPRODUCTION_BAND:.1e}"
    )
    assert abs(ladder["deviation"]) < MUTUAL_TOLERANCE, (
        f"corrected mutual {ladder['corrected']:.6f} is "
        f"{100.0 * ladder['deviation']:+.2f}% against the closed form, outside "
        f"the unmoved {100.0 * MUTUAL_TOLERANCE:.0f}% band"
    )
    assert abs(blind["deviation"]) >= MUTUAL_TOLERANCE, (
        "the blind (unfragmented) fixture's Im Z12 = 0 passed the mutual band — "
        "the band is gating nothing"
    )
    assert s_symmetry < S_SYMMETRY_BAND, (
        f"S is not symmetric: ||S - S^T||/||S|| = {s_symmetry:.4e} >= "
        f"{S_SYMMETRY_BAND:.1e}"
    )
    assert s_spectral <= S_SPECTRAL_NORM_CEILING, (
        f"S is not passive: ||S||_2 = {s_spectral:.6f} > "
        f"{S_SPECTRAL_NORM_CEILING:.1f}"
    )

    # -- ParaView ---------------------------------------------------------
    OUTPUT_DIR.mkdir(exist_ok=True)
    e_re, e_im, e_mag = paraview_fields
    written = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        cell_tags,
        {"E_real": e_re, "E_imag": e_im, "E_magnitude": e_mag},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    elapsed = time.perf_counter() - started
    if comm.rank == 0:
        if written is not None:
            print(f"[EX-18] wrote {written[0]} (+ .h5)", flush=True)
        print(
            f"[EX-18] all gates green: raw {ladder['raw']:.6f} (a miss), "
            f"corrected {ladder['corrected']:.6f} "
            f"({100.0 * ladder['deviation']:+.2f}%, inside "
            f"{100.0 * MUTUAL_TOLERANCE:.0f}%); ||S - S^T||/||S|| = "
            f"{s_symmetry:.4e}; ||S||_2 = {s_spectral:.6f} <= 1",
            flush=True,
        )
        print(
            f"[EX-18] elapsed {elapsed:.1f} s "
            f"(mesh {t_mesh:.1f} s, solves "
            + " + ".join(f"{t:.1f}" for t in solve_times)
            + f" s) on {comm.size} rank(s), {ncells} cells",
            flush=True,
        )


if __name__ == "__main__":
    main()
