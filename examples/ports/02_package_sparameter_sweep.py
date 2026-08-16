"""Package S-parameter sweep: ``run_n_port_sparameter_sweep`` on a solved field.

`EX-20`.  The first example that drives the **package entry point**
:func:`fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep` rather than
assembling ``Z`` by hand.  `EX-18` builds the impedance matrix itself and calls
:func:`~fem_em_solver.ports.sparameters.sparameters_from_impedance` on it; this
example hands the package a mesh, two :class:`PortDefinition` s and two
:class:`~fem_em_solver.ports.gap_voltage.GapVoltagePortSpec` s and lets the sweep
run both solves, assemble ``Z`` column by column, and convert.  That is the
capability `PORT-1` step 4 gated on 2026-08-13 (its gate lives in
``tests/validation/test_port_package_sparameters.py``), from the angle a user
actually reaches for.

**The negative control runs in this file, not beside it.**  The same sweep
without ``gap_voltage_ports=`` is the retiring `PORT-0` proximity heuristic
(known-issues 3): the example calls it on the same mesh and the same ports,
shows its :class:`DeprecationWarning`, and asserts its S-matrix differs from the
solved-field one.  A heuristic that happened to agree would be a finding about
the gate, not a passing example.

**Anchor.**  Every asserted number reproduces
``docs/testing/logs/20260813T183606Z_PORT-1-step4-packagegate.log`` within a
pre-stated **1%** relative band: raw mutual ``0.894543``, corrected
``0.939849``, ``||S - S^T||/||S|| = 2.5494e-05``, ``||S||_2 = 0.861449``.  The
raw mutual is printed **first and labelled a miss** — at -10.55% the unmoved 10%
band would not accept it; only the two named systematics bring it inside.

**What this example is not.**  Two-torus fixture only.  No birdcage ports, no
B1+, no Touchstone export, and no ``S11`` claim (`PORT-1` step 2b localised an
electric-energy excess on this fixture's diagonal).  ``PORT-1``'s reciprocity
gate is closed; the *other* package S-parameter path (``ports/excitation.py``)
remains the heuristic this file uses as its control.

**A named limitation of the entry point.**  ``run_n_port_sparameter_sweep``
returns port quantities, not fields: :class:`SParameterSweepResult` carries
``s_matrix``/``z_matrix`` and per-port responses, and the solver's
:class:`TimeHarmonicFields` are discarded inside it.  The ParaView export below
therefore costs **one extra solve** of port 1's drive, run directly through
:class:`~fem_em_solver.core.TimeHarmonicSolver` exactly as the sweep runs it.
The example says so rather than exporting nothing or pretending the sweep
produced the file.

Run (complex build required)::

    ./run_examples.sh -e ports:2
    ./run_examples.sh -e ports:2 -n 2 -t 540

Outputs ``paraview_output/package_sparameter_sweep_combined.xdmf`` (mesh +
CellTags + the port-1 drive's ``E`` fields; threshold on ``CellTags`` to see the
gap boxes 101/102 and the conductors 1/2).
"""

from __future__ import annotations

import time
import warnings
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
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.gap_voltage import GapVoltagePortSpec
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep
from fem_em_solver.ports.systematics import mutual_systematics_ladder
from fem_em_solver.utils.analytical import AnalyticalSolutions

# ---------------------------------------------------------------------------
# The fixture.  Restated from the gate module rather than imported: examples run
# with PYTHONPATH=/workspace/src and must not depend on `tests/`.  Identical to
# EX-18's and to tests/validation/test_port_package_sparameters.py's — the
# anchor below is only reproducible on this geometry at this padding.
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

# delta = sqrt(2/(omega*mu0*sigma)) = 5.63 mm = 1.13 r_wire: the current path is
# inside a skin depth, which is what makes it resolvable at h_wire.
SIGMA_WIRE_S_PER_M = 8.0e2
DRIVE_CURRENT_A = 1.0
REFERENCE_IMPEDANCE_OHM = 50.0

# Step 3b-x's converged order for the terminal-to-terminal path integral.  The
# gate module sweeps to measure the rate; the example takes the gated order, and
# the raw-ratio reproduction below is what carries the precondition here.
PATH_QUADRATURE_ORDER = 4097

# ---------------------------------------------------------------------------
# The anchor.  Recorded digits from
# docs/testing/logs/20260813T183606Z_PORT-1-step4-packagegate.log (PORT-1
# step 4, the package-path gate at -n 2).  The band is the one the EX-20 rubric
# pre-stated: 1% relative on each, deliberately looser than the digits it cites,
# never to be tightened onto the measurement nor widened to make a run pass.
RECORDED_RAW_RATIO = 0.894543
RECORDED_CORRECTED_RATIO = 0.939849
RECORDED_S_SYMMETRY_RESIDUAL = 2.5494e-05
RECORDED_S_SPECTRAL_NORM = 0.861449
REPRODUCTION_BAND_RELATIVE = 0.01

# PORT-1's own mutual band, unmoved since 3b-ii: the gate the corrected ratio
# must sit inside and the raw ratio does not.
MUTUAL_TOLERANCE = 0.10
# Passivity is an inequality, not a reproduction: ||S||_2 <= 1 for a passive
# 2-port, asserted beside the 1% reproduction of the recorded value.
S_SPECTRAL_NORM_CEILING = 1.0
# The negative control's floor: the heuristic S must differ from the solved
# field's by more than this.  3.078e-01 on record — two orders of magnitude of
# headroom, so this is a floor, not a fitted threshold.
HEURISTIC_SEPARATION_FLOOR = 2.0e-3

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "package_sparameter_sweep"


def _mutual_inductance(a: float, rho: float, z: float) -> float:
    """Filamentary ``M12`` between two coaxial loops, the closed-form target."""
    pts = np.array([[rho, 0.0, z]], dtype=float)
    A = AnalyticalSolutions.circular_loop_vector_potential(pts, 1.0, a, loop_center=0.0)
    return 2.0 * np.pi * rho * float(A[0, 1])


def _gap_half_extents():
    half_xz = MINOR_RADIUS + GAP_OVERHANG
    half_y = MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE) + GAP_BURIAL
    return half_xz, half_y


def _gap_box_edge_angle() -> float:
    _, half_y = _gap_half_extents()
    return float(np.arcsin(half_y / MAJOR_RADIUS))


def _azimuthal_unit(x):
    rho = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
    return ufl.as_vector([-x[1] / rho, x[0] / rho, 0.0])


def _arc_quadrature(port_index: int, order: int):
    """Gauss-Legendre nodes on the centreline arc, terminal to terminal.

    Weights carry the arc-length factor ``a`` so the spec's contract
    (``V = -sum(w_i (E.that)_i)``) holds.  Legendre nodes are strictly interior,
    so the terminals themselves — where a point locates into a cell on either
    side of the material interface — are never sampled.
    """
    phi_term = _gap_box_edge_angle()
    nodes, weights = np.polynomial.legendre.leggauss(order)
    phi = phi_term * nodes
    z_c = (-1.0) ** (port_index + 1) * SEPARATION / 2.0
    points = np.column_stack(
        [
            MAJOR_RADIUS * np.cos(phi),
            MAJOR_RADIUS * np.sin(phi),
            np.full_like(phi, z_c),
        ]
    )
    tangents = np.column_stack([-np.sin(phi), np.cos(phi), np.zeros_like(phi)])
    return points, tangents, MAJOR_RADIUS * phi_term * weights


def _tag_volume(msh, cell_tags, tag: int, comm) -> float:
    """Globally reduced meshed volume of one cell tag (rank-local otherwise)."""
    dx = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(int(tag),))
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * dx))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _gap_drive(j_magnitude: float):
    """Impressed current density across a gap box, along ``+yhat``.

    The same drive ``run_gap_voltage_port_case`` builds internally; reproduced
    here only for the ParaView export's extra solve.  It is not solenoidal — it
    terminates on the arc end faces where the conduction current takes over —
    hence ``project_source=False``.
    """

    def current_density(x):
        return ufl.as_vector([0.0, j_magnitude, 0.0])

    return current_density


def _paraview_fields(msh, fields):
    """CG1 ``E_real`` / ``E_imag`` / ``E_magnitude`` from the solved phasor.

    XDMF cannot carry N1curl, and the writers take Lagrange interpolants only
    (the `EX-14`/`EX-17` lesson).
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


def _relative_miss(measured: float, recorded: float) -> float:
    return abs(measured - recorded) / abs(recorded)


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
        print("EX-20 — run_n_port_sparameter_sweep on the solved field", flush=True)
        print("=" * 78, flush=True)

    # -- the fixture ------------------------------------------------------
    t_mesh = time.perf_counter()
    msh, cell_tags, _facet_tags = MeshGenerator.two_torus_domain(
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
    # Unconditionally on every rank, before any tagged form: the assembler
    # reaches `create_entity_permutations` lazily and only on ranks owning
    # integration entities (PORT-1 step 3b-iv, known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    if comm.rank == 0:
        print(
            f"[EX-20] mesh: {ncells} cells in {t_mesh:.1f} s "
            f"(padding {AIR_PADDING}, gap arc {GAP_ARC_RESOLUTION:.1e})",
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

    # -- what the package needs: definitions + gap-voltage specs -----------
    _, half_y = _gap_half_extents()
    ports = [
        PortDefinition(
            port_id=f"P{k + 1}",
            positive_tag=GAP_TAGS[k],
            negative_tag=WIRE_TAGS[k],
            orientation="gap_azimuthal_plus_y",
            z0_ohm=REFERENCE_IMPEDANCE_OHM,
        )
        for k in range(2)
    ]
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
            )
        )

    # -- one call: two solves, Z column by column, S at Z0 -----------------
    t_sweep = time.perf_counter()
    solved = run_n_port_sparameter_sweep(problem, ports, gap_voltage_ports=specs)
    t_sweep = time.perf_counter() - t_sweep

    assert not solved.is_placeholder, (
        "the solved-field route returned is_placeholder=True — the flag that "
        "gates Touchstone export must distinguish it from the heuristic"
    )
    assert solved.z_matrix is not None, "the solved-field route must return its Z"

    # -- the negative control, on the same mesh and the same ports ---------
    t_heuristic = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        heuristic = run_n_port_sparameter_sweep(problem, ports)
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    t_heuristic = time.perf_counter() - t_heuristic

    # -- the ladder, raw rung first ---------------------------------------
    omega_m12 = OMEGA * _mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    im_z12 = float(solved.z_matrix[1, 0].imag)
    ladder = mutual_systematics_ladder(im_z12, omega_m12)

    s = solved.s_matrix
    s_symmetry = float(np.linalg.norm(s - s.T) / np.linalg.norm(s))
    s_spectral = float(np.linalg.norm(s, 2))
    z_reciprocity = float(
        abs(solved.z_matrix[0, 1] - solved.z_matrix[1, 0]) / abs(solved.z_matrix[1, 0])
    )
    heuristic_delta = float(np.max(np.abs(heuristic.s_matrix - s)))

    misses = {
        "raw": _relative_miss(ladder["raw"], RECORDED_RAW_RATIO),
        "corrected": _relative_miss(ladder["corrected"], RECORDED_CORRECTED_RATIO),
        "symmetry": _relative_miss(s_symmetry, RECORDED_S_SYMMETRY_RESIDUAL),
        "spectral": _relative_miss(s_spectral, RECORDED_S_SPECTRAL_NORM),
    }

    if comm.rank == 0:
        print(
            f"[EX-20] package sweep: Im Z12 = {im_z12:+.9e} Ohm, "
            f"omega*M12 = {omega_m12:.6f} Ohm",
            flush=True,
        )
        print(f"[EX-20] Z (Ohm) through the package:\n{solved.z_matrix}", flush=True)
        print(
            "[EX-20] systematics ladder, raw rung FIRST (the miss it is):\n"
            f"    raw            {ladder['raw']:.6f}  "
            f"({100.0 * ladder['raw_deviation']:+.2f}%  <- a MISS against the "
            f"{100.0 * MUTUAL_TOLERANCE:.0f}% band)\n"
            f"    + PEC box      {ladder['box_corrected']:.6f}\n"
            f"    + gap physics  {ladder['corrected']:.6f}  "
            f"({100.0 * ladder['deviation']:+.2f}%, inside the band)",
            flush=True,
        )
        print(f"[EX-20] S at Z0 = {REFERENCE_IMPEDANCE_OHM:.0f} Ohm:\n{s}", flush=True)
        print(
            f"[EX-20] identities: |Z12 - Z21|/|Z21| = {z_reciprocity:.4e}, "
            f"||S - S^T||/||S|| = {s_symmetry:.4e}, ||S||_2 = {s_spectral:.6f}",
            flush=True,
        )
        print(
            "[EX-20] reproduction of the step-4 record "
            f"(band {100.0 * REPRODUCTION_BAND_RELATIVE:.0f}% relative): "
            f"raw {misses['raw']:.2e}, corrected {misses['corrected']:.2e}, "
            f"symmetry {misses['symmetry']:.2e}, ||S||_2 {misses['spectral']:.2e}",
            flush=True,
        )
        print(
            "[EX-20] negative control — the deprecated heuristic route "
            f"({len(deprecations)} DeprecationWarning(s)):\n{heuristic.s_matrix}\n"
            f"    max|S_heuristic - S_field| = {heuristic_delta:.6e} "
            f"(floor {HEURISTIC_SEPARATION_FLOOR:.1e})",
            flush=True,
        )
        for w in deprecations:
            print(f"    DeprecationWarning: {w.message}", flush=True)

    # -- gates -------------------------------------------------------------
    for name, recorded in (
        ("raw", RECORDED_RAW_RATIO),
        ("corrected", RECORDED_CORRECTED_RATIO),
        ("symmetry", RECORDED_S_SYMMETRY_RESIDUAL),
        ("spectral", RECORDED_S_SPECTRAL_NORM),
    ):
        assert misses[name] < REPRODUCTION_BAND_RELATIVE, (
            f"{name} does not reproduce the PORT-1 step-4 record {recorded:.6g} "
            f"within {100.0 * REPRODUCTION_BAND_RELATIVE:.0f}%: relative miss "
            f"{misses[name]:.3e} — the example path is not the gated path"
        )

    assert abs(ladder["raw_deviation"]) >= MUTUAL_TOLERANCE, (
        f"the raw mutual {ladder['raw']:.6f} passed the "
        f"{100.0 * MUTUAL_TOLERANCE:.0f}% band on its own — the systematics "
        "this example exists to show would be doing nothing"
    )
    assert abs(ladder["deviation"]) < MUTUAL_TOLERANCE, (
        f"corrected mutual {ladder['corrected']:.6f} is "
        f"{100.0 * ladder['deviation']:+.2f}% against the closed form, outside "
        f"the unmoved {100.0 * MUTUAL_TOLERANCE:.0f}% band"
    )
    assert s_spectral <= S_SPECTRAL_NORM_CEILING, (
        f"S is not passive: ||S||_2 = {s_spectral:.6f} > "
        f"{S_SPECTRAL_NORM_CEILING:.1f}"
    )
    assert heuristic.is_placeholder, "the heuristic route must keep marking itself"
    assert deprecations, (
        "the heuristic route must emit a DeprecationWarning now that the "
        "solved-field route exists"
    )
    assert heuristic_delta > HEURISTIC_SEPARATION_FLOOR, (
        f"the retiring heuristic reproduces the solved-field S to "
        f"{heuristic_delta:.3e} — that is a finding about the heuristic, not a "
        "passing example"
    )

    # -- ParaView: one extra solve, because the sweep returns no fields ----
    gap_volume = _tag_volume(msh, cell_tags, GAP_TAGS[0], comm)
    gap_area = gap_volume / (2.0 * half_y)
    t_export_solve = time.perf_counter()
    fields = TimeHarmonicSolver(problem, degree=1).solve(
        current_density=_gap_drive(DRIVE_CURRENT_A / gap_area),
        subdomain_ids=[int(GAP_TAGS[0])],
        project_source=False,
    )
    t_export_solve = time.perf_counter() - t_export_solve

    OUTPUT_DIR.mkdir(exist_ok=True)
    e_re, e_im, e_mag = _paraview_fields(msh, fields)
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
            print(f"[EX-20] wrote {written[0]} (+ .h5)", flush=True)
        print(
            f"[EX-20] all gates green: raw {ladder['raw']:.6f} (a miss), "
            f"corrected {ladder['corrected']:.6f} "
            f"({100.0 * ladder['deviation']:+.2f}%, inside "
            f"{100.0 * MUTUAL_TOLERANCE:.0f}%); ||S - S^T||/||S|| = "
            f"{s_symmetry:.4e}; ||S||_2 = {s_spectral:.6f} <= 1; heuristic "
            f"control separated by {heuristic_delta:.3e}",
            flush=True,
        )
        print(
            f"[EX-20] elapsed {elapsed:.1f} s (mesh {t_mesh:.1f} s, package "
            f"sweep {t_sweep:.1f} s, heuristic control {t_heuristic:.1f} s, "
            f"export solve {t_export_solve:.1f} s) on {comm.size} rank(s), "
            f"{ncells} cells",
            flush=True,
        )


if __name__ == "__main__":
    main()
