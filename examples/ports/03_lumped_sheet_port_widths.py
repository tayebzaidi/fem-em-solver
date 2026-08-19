"""Example (`EX-24`): the **lumped-element port sheet** — width ladder and sweep.

`ports:1` (`EX-18`) and `ports:2` (`EX-20`) both drive the two-torus fixture
through the **gap-voltage** route: a terminal-to-terminal path integral read off
a field driven by an impressed gap current. Neither instantiates the
lumped-element port boundary condition (`PORT-9` steps 1–2c, Jin ch. 11) — a
sheet impedance ``R = Z_p · w / h`` entering the *bilinear form*, so the port is
part of the operator rather than a post-processing path. That is the angle this
example adds: the drive/BC angle first, then the output-quantity angle (an
S-matrix assembled from lumped-sheet excitations).

**Two legs, one mesh.**

1. *The width ladder* (`PORT-9` step 2b). The gap box's mid-plane sheet
   ``21x`` is narrowed by a facet-**midpoint** filter to interior width
   fractions ``f ∈ {1.0, 0.735, 0.5}`` of the half-width, and each width is its
   own assembly + solve (the BC surface is in the form). Off each solved field
   the lumped terminal voltage ``−I·Z_p`` and the gap route's path integral are
   both read, and their deviation is the cross-route quantity step 2 measured at
   **7.7095%** on the full sheet — outside the 5% band pre-stated at scoping.
   Narrowing the sheet to the interior width recovers the centreline voltage:
   the measured ladder is ``7.7095% → 3.6730% → 1.8333%``, and the band never
   moved.
2. *The sweep* (`PORT-9` step 2c). At the gated width ``f = 0.5``, **both**
   sheets are narrowed and the two-port S-matrix is assembled through
   :func:`~fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep` on the
   ``LumpedSheetPortSpec`` route — one solve per driven port, every port's sheet
   in the form, the driven port's sheet carrying the impressed source.
   Reciprocity ``‖S − Sᵀ‖/‖S‖`` is printed beside the unmoved 1e-3 band
   (step 2c's record: 2.574249e-11).

**It asserts, it does not merely render.** Every band and record below is
**imported** from the gate modules (`ANS-1` rule) — nothing is restated here, so
this example cannot drift from the gates it demonstrates:

* the gate — at ``f = 0.5`` the cross-route deviation ``|ΔZ₁₂|/|Z₁₂| ≤``
  ``CROSS_ROUTE_BAND`` (5%), on the ladder *and* through the sweep;
* the negative control — ``f = 1.0`` reproduces step 2's record to
  ``REPRODUCTION_BAND`` (1e-4) and is asserted to **miss** the 5% band (the
  `EX-18` inverted-assertion pattern), while the gap route stays flat at
  ``STEP1_GAP_RATIO_RECORD`` (0.894310 × ω·M₁₂) across the whole ladder — a
  narrowing that moved either would have changed the fixture, not the sheet;
* the open-limit identity ``V_lumped = −(1/w_f)∫_S E·ĥ dS`` to
  ``DECOMPOSITION_IDENTITY_BAND`` (1e-11) at **every** width, assembled
  independently of ``ports.lumped``;
* reciprocity through the sweep to ``RECIPROCITY_BAND`` (1e-3).

**The trap this fixture is made of.** ``w`` is the **area-based effective
width ``A/h``** of the *filtered* facet set, never the bounding-box extent and
never ``f × w_full``: the midpoint filter leaves a ragged edge, and taking the
bbox extent overstates the narrow rungs by 14–15% (which cost step 2b its first
attempt). On the full-width rung the sheet is a rectangle and the two
definitions coincide — asserted below, which is what leaves the negative
control untouched by the choice.

**Scope: two-torus only.** No birdcage, no `PORT-9` step 3 claim. Every number
is quoted from the test modules and reproduced here; the reciprocity *record* is
step 2c's.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:3

Outputs ``paraview_output/lumped_sheet_port_widths_combined.xdmf`` (mesh +
CellTags + the ``f = 0.5`` solved ``E_real`` / ``E_imag`` / ``E_magnitude``) and
``lumped_sheet_port_widths_facets.xdmf`` alongside it — threshold ``mesh_tags``
on 211/212 there to see the port sheets the BC lives on.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem, io

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gates' constants and helpers can be imported rather than restated.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.core import (  # noqa: E402
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.ports.definitions import PortDefinition  # noqa: E402
from fem_em_solver.ports.lumped import (  # noqa: E402
    LumpedPortSheet,
    LumpedSheetPortSpec,
    lumped_port_bilinear_term,
    sheet_terminal_current,
)
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep  # noqa: E402

from tests.mesh.test_two_torus_port_facets import _facet_group_area  # noqa: E402
from tests.mesh.test_two_torus_port_sheet import (  # noqa: E402
    SHEET_FACET_TAGS,
    _sheet_extents,
    _sheet_facet_count,
)
from tests.validation.test_port_gap_voltage_impedance import (  # noqa: E402
    DRIVE_CURRENT_A,
    FREQUENCY_HZ,
    GAP_TAGS,
    MAJOR_RADIUS,
    MINOR_RADIUS,
    OMEGA,
    PATH_QUADRATURE_GATE_ORDERS,
    PRODUCTION_LADDER_DRIVEN_COLUMN,
    SEPARATION,
    SIGMA_WIRE_S_PER_M,
    WIRE_TAGS,
    _azimuthal_unit,
    _gap_drive,
    _gap_half_extents,
    _path_voltage,
    _reduce,
    _tag_measure,
    _tag_volume,
)
from tests.validation.test_port_lumped_narrowed_sheet import (  # noqa: E402
    GATED_WIDTH_FRACTION,
    PROFILE_PREDICTION,
    WIDTH_FRACTIONS,
    _narrowed_sheet_tags,
)
from tests.validation.test_port_lumped_sheet_sweep import (  # noqa: E402
    DRIVE_VOLTAGE_V,
    RECIPROCITY_BAND,
    STEP2B_CROSS_ROUTE_AT_HALF_WIDTH,
)
from tests.validation.test_port_lumped_two_torus import (  # noqa: E402
    AREA_IDENTITY_BAND,
    CROSS_ROUTE_BAND,
    DECOMPOSITION_IDENTITY_BAND,
    GAP_CELL_TAGS_WITH_SHEET,
    PROBE_PORT_IMPEDANCE_OHM,
    QUADRATURE_DRIFT_TOLERANCE,
    REPRODUCTION_BAND,
    STEP1_CROSS_ROUTE_RECORD,
    STEP1_GAP_RATIO_RECORD,
    VOLUME_IDENTITY_BAND,
    _build,
)
from tests.validation.test_port_package_sparameters import (  # noqa: E402
    PATH_QUADRATURE_ORDER,
    REFERENCE_IMPEDANCE_OHM,
    _arc_quadrature,
)
from tests.validation.test_port_reaction_impedance import (  # noqa: E402
    mutual_inductance,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "lumped_sheet_port_widths"

CELL_TAG_NAMES = {
    1: "wire 1 (z<0)",
    2: "wire 2 (z>0)",
    3: "air",
    101: "gap 1 lower",
    111: "gap 1 upper",
    102: "gap 2 lower",
    112: "gap 2 upper",
}


def _paraview_fields(msh, e_complex):
    """CG1 ``E_real`` / ``E_imag`` / ``E_magnitude`` from the solved phasor.

    XDMF cannot carry N1curl, and the writers take Lagrange interpolants only
    (`EX-14`/`EX-17`), so the phasor is interpolated before it is split.
    """
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    e_cg = fem.Function(v_cg, name="E_phasor")
    e_cg.interpolate(e_complex)
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


def _write_paraview(msh, cell_tags, facet_tags, fields, comm):
    """Cells + tags + the solved field in one file, facet tags in a second."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    written = {}

    e_re, e_im, e_mag = fields
    combined, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        cell_tags,
        {"E_real": e_re, "E_imag": e_im, "E_magnitude": e_mag},
        comm=comm,
    )
    if combined is not None:
        written["cells + E field"] = combined

    facets_path = OUTPUT_DIR / f"{BASENAME}_facets.xdmf"
    msh.topology.create_connectivity(msh.topology.dim - 1, msh.topology.dim)
    with io.XDMFFile(comm, facets_path, "w") as xdmf:
        xdmf.write_mesh(msh)
        xdmf.write_meshtags(facet_tags, msh.geometry)
    if comm.rank == 0:
        written["facet tags"] = facets_path

    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return written


def _solve_one_width(
    msh,
    cell_tags,
    facet_tags,
    fraction,
    *,
    sheet_tag,
    driven_tags,
    col,
    half_xz,
    j,
    omega_m,
    arc_length,
    phi_hat,
    comm,
):
    """One rung of the width ladder: narrow, assemble, solve, read both routes.

    The narrowing is a filter on the **midpoints** of `GEO-16`'s already
    dolfinx-side-rebuilt ``21x`` tag, so the mesh is bit-identical across the
    ladder and ``f = 1.0`` is a control on the fixture rather than on a second
    mesh. ``w`` is re-measured from the filtered set as ``A/h`` — see the
    module docstring's trap note.
    """
    tags_f = _narrowed_sheet_tags(
        msh, facet_tags, sheet_tag, fraction, MAJOR_RADIUS, half_xz
    )
    n_facets = _sheet_facet_count(msh, tags_f, sheet_tag, comm)
    assert n_facets > 0, (
        f"f = {fraction}: the narrowed sheet has no owned facets anywhere — the "
        "port form would be an integral over nothing, and every identity below "
        "would pass vacuously"
    )
    area_f = _facet_group_area(msh, tags_f, sheet_tag, comm)
    extents_f = _sheet_extents(msh, tags_f, sheet_tag, comm)
    w_bbox_f = float(extents_f[0])
    h_f = float(extents_f[1])
    w_f = area_f / h_f

    sheet = LumpedPortSheet(
        port_id=f"p{1 - col}",
        facet_tag=sheet_tag,
        port_impedance_ohm=PROBE_PORT_IMPEDANCE_OHM,
        gap_height_m=h_f,
        sheet_width_m=w_f,
        drive_direction=(0.0, 1.0, 0.0),
        source_voltage_v=0.0,
        interior=True,
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
    solver = TimeHarmonicSolver(problem, degree=1)
    comm.Barrier()
    t0 = time.perf_counter()
    solved = solver.solve(
        current_density=_gap_drive(j),
        subdomain_ids=list(driven_tags),
        project_source=False,
        extra_bilinear_terms=[
            lambda trial, test, _t=tags_f, _s=sheet: lumped_port_bilinear_term(
                msh, _t, _s, trial, test, omega_rad_per_s=OMEGA
            )
        ],
    )
    comm.Barrier()
    t_solve = time.perf_counter() - t0

    e = solved.e_complex
    i_conduction = (
        SIGMA_WIRE_S_PER_M
        * _reduce(ufl.inner(e, phi_hat) * _tag_measure(msh, cell_tags, WIRE_TAGS[col]), comm)
        / arc_length
    )
    v_gap = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[-1], comm)
    v_gap_coarse = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[0], comm)
    # Generator convention (step 1's trap): the terminal voltage comparable to
    # the gap route's V = -int E.that dl is -I*Z_p.
    i_sheet = sheet_terminal_current(msh, tags_f, sheet, e, comm)
    v_lumped = -i_sheet * PROBE_PORT_IMPEDANCE_OHM

    # The open-limit reduction, assembled independently of ports.lumped so it
    # stays a *checked* identity at every width rather than a restatement.
    ds_sheet = ufl.Measure(
        "dS", domain=msh, subdomain_data=tags_f, subdomain_id=(sheet_tag,)
    )
    h_hat = ufl.as_vector([0.0, 1.0, 0.0])
    v_sheet_average = -_reduce(ufl.inner(e("+"), h_hat) * ds_sheet, comm) / w_f

    z12_gap = v_gap / i_conduction
    z12_lumped = v_lumped / i_conduction
    rung = {
        "f": float(fraction),
        "facets": int(n_facets),
        "area": float(area_f),
        "w": w_f,
        "w_bbox": w_bbox_f,
        "h": h_f,
        "out_of_plane": float(extents_f[2]),
        "sheet_resistivity": sheet.sheet_resistivity,
        "solve_time": t_solve,
        "v_gap": v_gap,
        "v_lumped": v_lumped,
        "v_sheet_average": v_sheet_average,
        "quadrature_drift": abs(v_gap - v_gap_coarse) / abs(v_gap),
        "ratio_gap": abs(z12_gap.imag) / omega_m,
        "ratio_lumped": abs(z12_lumped.imag) / omega_m,
        "cross_route": abs(z12_lumped - z12_gap) / abs(z12_gap),
    }
    # The ``f = 0.5`` field is the one ParaView gets; the others are released so
    # three solves do not hold three fields on a 12-core share.
    keep = fraction == GATED_WIDTH_FRACTION
    e_out = solved.e_complex if keep else None
    if not keep:
        del solved
    del solver, problem, tags_f
    return rung, e_out


def _run_sweep(msh, cell_tags, facet_tags, half_xz, comm):
    """Leg 2: the two-port S-matrix through the ``LumpedSheetPortSpec`` route.

    Both ``21x`` groups narrowed to the gated width by the same midpoint filter
    — it rewrites one tag and passes every other through, so composing it twice
    narrows both sheets on the ladder's own mesh.
    """
    tags_f = facet_tags
    for sheet_tag in SHEET_FACET_TAGS:
        tags_f = _narrowed_sheet_tags(
            msh, tags_f, int(sheet_tag), GATED_WIDTH_FRACTION, MAJOR_RADIUS, half_xz
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

    ports, specs, sheets = [], [], []
    for k, sheet_tag in enumerate(SHEET_FACET_TAGS):
        sheet_tag = int(sheet_tag)
        n_facets = _sheet_facet_count(msh, tags_f, sheet_tag, comm)
        assert n_facets > 0, f"sheet {sheet_tag}: no owned facets anywhere"
        area = _facet_group_area(msh, tags_f, sheet_tag, comm)
        extents = _sheet_extents(msh, tags_f, sheet_tag, comm)
        h = float(extents[1])
        w = area / h
        sheets.append(
            {
                "tag": sheet_tag,
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
                port_impedance_ohm=PROBE_PORT_IMPEDANCE_OHM,
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
    return result, sheets, time.perf_counter() - t0


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    col = PRODUCTION_LADDER_DRIVEN_COLUMN          # 0 -> gap 101 driven
    driven_tags = GAP_CELL_TAGS_WITH_SHEET[GAP_TAGS[col]]
    sheet_tag = int(SHEET_FACET_TAGS[1 - col])     # 212 — the undriven port

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "EX-24 — lumped-element port sheet at interior width "
            "(two-torus fixture)",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"\n[fixture] f = {FREQUENCY_HZ:.3e} Hz  R = {MAJOR_RADIUS} m  "
            f"r = {MINOR_RADIUS} m  separation = {SEPARATION} m"
            f"\n[port]    sheet facet tag {sheet_tag} (undriven), probe "
            f"impedance Z_p = {PROBE_PORT_IMPEDANCE_OHM:.1e} Ohm, drive "
            f"{DRIVE_CURRENT_A} A impressed in gap cells {driven_tags}"
            f"\n[gates]   cross-route <= {CROSS_ROUTE_BAND * 100:.0f}% at "
            f"f = {GATED_WIDTH_FRACTION}; f = 1.0 reproduces "
            f"{STEP1_CROSS_ROUTE_RECORD * 100:.4f}% to "
            f"{REPRODUCTION_BAND:.0e} and is asserted to MISS the band; "
            f"open-limit identity < {DECOMPOSITION_IDENTITY_BAND:.0e} per width;"
            f"\n          sweep reciprocity <= {RECIPROCITY_BAND:.0e}",
            flush=True,
        )

    # ---- the fixture, meshed once and shared by both legs -----------------
    msh, cell_tags, facet_tags, t_mesh = _build(comm)
    assert facet_tags is not None, "model_to_mesh returned no facet tags"
    tdim = msh.topology.dim
    n_cells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    # Hoisted on every rank before any facet-restricted form (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    half_xz, half_y = _gap_half_extents()
    gap_length = 2.0 * half_y
    gap_volume = sum(_tag_volume(msh, cell_tags, t, comm) for t in driven_tags)
    gap_area = gap_volume / gap_length
    gap_volume_analytic = (2.0 * half_xz) ** 2 * gap_length
    wire_volume = _tag_volume(msh, cell_tags, WIRE_TAGS[col], comm)
    arc_length = wire_volume / (np.pi * MINOR_RADIUS**2)
    sheet_area_cad = 4.0 * half_xz * half_y

    x_ufl = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_unit(x_ufl)
    j = DRIVE_CURRENT_A / gap_area
    omega_m = OMEGA * mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)

    gap_volume_ratio = gap_volume / gap_volume_analytic
    assert abs(gap_volume_ratio - 1.0) < VOLUME_IDENTITY_BAND, (
        f"meshed/analytic gap-box volume {gap_volume_ratio:.12f} over both "
        "halves — the drive normalises through this volume, so the rungs below "
        "would not be one fixture"
    )

    if comm.rank == 0:
        print(
            f"\n[mesh] {n_cells} cells in {t_mesh:.1f} s; meshed/analytic gap "
            f"volume {gap_volume_ratio:.12f} (band "
            f"{VOLUME_IDENTITY_BAND:.0e})\n"
            f"[mesh] omega*M12 = {omega_m:.6f} Ohm (Maxwell mutual inductance, "
            f"closed form)",
            flush=True,
        )

    # ---- leg 1: the width ladder ------------------------------------------
    rungs = []
    gated_field = None
    for fraction in WIDTH_FRACTIONS:
        rung, e_out = _solve_one_width(
            msh,
            cell_tags,
            facet_tags,
            fraction,
            sheet_tag=sheet_tag,
            driven_tags=driven_tags,
            col=col,
            half_xz=half_xz,
            j=j,
            omega_m=omega_m,
            arc_length=arc_length,
            phi_hat=phi_hat,
            comm=comm,
        )
        rungs.append(rung)
        if e_out is not None:
            gated_field = e_out

    full = rungs[0]
    assert full["f"] == 1.0, "the first rung must be the full-width control"

    if comm.rank == 0:
        print(
            f"\n[step 2b] sheet {sheet_tag} width ladder (half-width "
            f"{half_xz:.6e} m, CAD mid-plane area {sheet_area_cad:.9e} m^2); "
            "solves "
            + ", ".join(f"f={r['f']:.3f} {r['solve_time']:.1f} s" for r in rungs),
            flush=True,
        )
        for r in rungs:
            print(
                f"    f = {r['f']:.3f}  facets {r['facets']:5d}  "
                f"area {r['area']:.9e} m^2 "
                f"({r['area'] / sheet_area_cad:.9f} of CAD)  "
                f"w = A/h = {r['w']:.9e} m (bbox extent {r['w_bbox']:.9e}, "
                f"f*w_full would be {r['f'] * full['w']:.9e})  "
                f"h = {r['h']:.9e} m  w/h = {r['w'] / r['h']:.9f} squares  "
                f"R = {r['sheet_resistivity']:.6e} Ohm/square",
                flush=True,
            )

    # Structural: the same fixture with a strictly smaller, still-planar sheet.
    area_ratio = full["area"] / sheet_area_cad
    assert abs(area_ratio - 1.0) < AREA_IDENTITY_BAND, (
        f"f = 1.0: meshed/CAD sheet area {area_ratio:.12f} — the control sheet "
        "is not the gap box's mid-plane, so it is not step 2's sheet"
    )
    # The full-width sheet is a rectangle, so the A/h width the narrow rungs are
    # scaled by must be its bbox extent to round-off: the width *definition*
    # cannot have moved the rung that reproduces the record.
    assert abs(full["w"] / full["w_bbox"] - 1.0) < AREA_IDENTITY_BAND, (
        f"f = 1.0: effective width A/h = {full['w']:.9e} m against the "
        f"bounding-box extent {full['w_bbox']:.9e} m — the full-width sheet is "
        "not the rectangle both definitions assume it is"
    )
    for prev, r in zip(rungs, rungs[1:]):
        assert r["facets"] < prev["facets"] and r["area"] < prev["area"], (
            f"f = {r['f']}: {r['facets']} facets / area {r['area']:.9e} against "
            f"{prev['facets']} / {prev['area']:.9e} at f = {prev['f']} — the "
            "filter did not narrow"
        )
    for r in rungs:
        assert r["out_of_plane"] < 1.0e-12, (
            f"f = {r['f']}: out-of-plane spread {r['out_of_plane']:.3e} m — the "
            "filtered facet set is not a plane"
        )
        assert r["quadrature_drift"] < QUADRATURE_DRIFT_TOLERANCE, (
            f"f = {r['f']}: the terminal path integral moved "
            f"{r['quadrature_drift']:.3e} between orders "
            f"{PATH_QUADRATURE_GATE_ORDERS}"
        )

    # The open-limit identity, per width.
    if comm.rank == 0:
        print(
            f"\n[step 2b] open-limit reduction V_lumped = -(1/w_f) int_S E.hhat "
            f"dS (band {DECOMPOSITION_IDENTITY_BAND:.0e}, exact arithmetic on "
            "one solved field):",
            flush=True,
        )
    for r in rungs:
        rel = abs(r["v_lumped"] - r["v_sheet_average"]) / abs(r["v_lumped"])
        if comm.rank == 0:
            print(
                f"    f = {r['f']:.3f}  V_lumped = {r['v_lumped']:+.9e} V  "
                f"sheet average {r['v_sheet_average']:+.9e} V  "
                f"relative {rel:.3e}",
                flush=True,
            )
        assert rel < DECOMPOSITION_IDENTITY_BAND, (
            f"f = {r['f']}: lumped terminal voltage {r['v_lumped']:+.9e} V "
            f"against the independently assembled sheet average "
            f"{r['v_sheet_average']:+.9e} V — relative {rel:.3e}, above "
            f"{DECOMPOSITION_IDENTITY_BAND:.0e}: the port model's sheet and the "
            "width it is scaled by are not the same facet set"
        )

    # The ladder, its gate, and the inverted control.
    if comm.rank == 0:
        print(
            f"\n[step 2b] CROSS-ROUTE ladder (band {CROSS_ROUTE_BAND * 100:.0f}%, "
            f"pre-stated at scoping and never widened; step 2's transverse "
            f"profile predicts ~{PROFILE_PREDICTION * 100:.1f}% at interior "
            f"width):",
            flush=True,
        )
        for r in rungs:
            verdict = "INSIDE" if r["cross_route"] <= CROSS_ROUTE_BAND else "MISS"
            print(
                f"    f = {r['f']:.3f}  |dZ12|/|Z12| = "
                f"{r['cross_route'] * 100:8.4f}%  {verdict:6s}  "
                f"gap {r['ratio_gap']:.6f} x omega*M12, lumped "
                f"{r['ratio_lumped']:.6f}  V_gap = {r['v_gap']:+.9e}, "
                f"V_lumped = {r['v_lumped']:+.9e} V",
                flush=True,
            )

    # Negative control (i): the full-width rung IS step 2's measurement, at the
    # 1e-4 grain step 1 printed to — on both routes.
    for name, measured, record in (
        ("cross-route", full["cross_route"], STEP1_CROSS_ROUTE_RECORD),
        ("gap ratio", full["ratio_gap"], STEP1_GAP_RATIO_RECORD),
    ):
        assert abs(measured - record) < REPRODUCTION_BAND, (
            f"f = 1.0 {name}: {measured:.6f} against the step-1/2 record "
            f"{record:.6f} — moved by {abs(measured - record):.2e}, above "
            f"{REPRODUCTION_BAND:.0e}; the example path changed the fixture, "
            "not just the sheet (§7 `EX-24` negative result: known-issues "
            "entry, report, stop)"
        )
    # Negative control (ii): the gap route is blind to the port BC's sheet, so
    # it must stay flat across the whole ladder. A gap ratio that moved with f
    # would mean the narrowing perturbed the field the ladder is differencing.
    for r in rungs:
        drift = abs(r["ratio_gap"] - STEP1_GAP_RATIO_RECORD)
        assert drift < REPRODUCTION_BAND, (
            f"f = {r['f']}: gap-route ratio {r['ratio_gap']:.6f} x omega*M12 "
            f"drifted {drift:.2e} from the flat record "
            f"{STEP1_GAP_RATIO_RECORD:.6f} — narrowing the port sheet moved the "
            "route that does not see it"
        )
    # Negative control (iii), the `EX-18` inverted assertion: the full sheet
    # must MISS the band. If it passed, the ladder below would be demonstrating
    # nothing — the width would not be what the gate turns on.
    assert full["cross_route"] > CROSS_ROUTE_BAND, (
        f"f = 1.0: the full-width sheet reads {full['cross_route'] * 100:.4f}%, "
        f"inside the {CROSS_ROUTE_BAND * 100:.0f}% band it is on record for "
        "missing — the control is not a control, and the narrowing demonstrates "
        "nothing"
    )

    gated = [r for r in rungs if r["f"] == GATED_WIDTH_FRACTION]
    assert len(gated) == 1, "the gated width fraction is not on the ladder"
    gated = gated[0]
    if comm.rank == 0:
        print(
            f"[step 2b] GATE at f = {GATED_WIDTH_FRACTION}: "
            f"{gated['cross_route'] * 100:.4f}% against the "
            f"{CROSS_ROUTE_BAND * 100:.0f}% band  "
            f"(control f = 1.0 at {full['cross_route'] * 100:.4f}%, asserted to "
            "MISS)",
            flush=True,
        )
    assert gated["cross_route"] <= CROSS_ROUTE_BAND, (
        f"f = {GATED_WIDTH_FRACTION}: cross-route deviation "
        f"{gated['cross_route'] * 100:.4f}% against the pre-stated "
        f"{CROSS_ROUTE_BAND * 100:.0f}% band — the example path is off the "
        "`PORT-9` step 2b record. The band is never widened to admit it "
        "(§7 `EX-24` negative result: known-issues entry, report, stop)."
    )

    # ---- leg 2: the S-matrix through the lumped-sheet sweep ---------------
    result, sheets, t_sweep = _run_sweep(msh, cell_tags, facet_tags, half_xz, comm)
    s = result.s_matrix
    z = result.z_matrix
    reciprocity = float(np.linalg.norm(s - s.T) / np.linalg.norm(s))

    assert not result.is_placeholder, (
        "the lumped-sheet route returned is_placeholder=True — the sweep fell "
        "back to the PORT-0 coupling heuristic, and the S-matrix below is not "
        "field-derived"
    )
    assert z is not None and z.shape == (2, 2), "the route must return its 2x2 Z"
    for sh in sheets:
        assert sh["out_of_plane"] < 1.0e-12, (
            f"sheet {sh['tag']}: out-of-plane spread {sh['out_of_plane']:.3e} m"
        )
        assert sh["w"] < sh["w_bbox"], (
            f"sheet {sh['tag']}: A/h = {sh['w']:.9e} m is not below the bbox "
            f"extent {sh['w_bbox']:.9e} m — the narrowed sheet is not ragged, "
            "so the filter did not run"
        )

    if comm.rank == 0:
        print(
            f"\n[step 2c] two-port sweep through LumpedSheetPortSpec at "
            f"f = {GATED_WIDTH_FRACTION} on both sheets {list(SHEET_FACET_TAGS)}: "
            f"{t_sweep:.1f} s, impressed sheet drive "
            f"{DRIVE_VOLTAGE_V:+.1f} V, Z0 = {REFERENCE_IMPEDANCE_OHM} Ohm",
            flush=True,
        )
        for sh in sheets:
            print(
                f"    sheet {sh['tag']}  facets {sh['facets']:5d}  "
                f"area {sh['area']:.9e} m^2  w = A/h = {sh['w']:.9e} m "
                f"(bbox {sh['w_bbox']:.9e})  h = {sh['h']:.9e} m",
                flush=True,
            )
        print("\n[step 2c] S =", flush=True)
        for row in s:
            print(
                "    " + "  ".join(f"{v.real:+.9e}{v.imag:+.9e}j" for v in row),
                flush=True,
            )
        print(
            f"[step 2c] Z11 = {z[0, 0]:+.9e}, Z12 = {z[0, 1]:+.9e}, "
            f"Z21 = {z[1, 0]:+.9e}, Z22 = {z[1, 1]:+.9e} Ohm\n"
            f"[step 2c] RECIPROCITY ||S - S^T||/||S|| = {reciprocity:.6e} "
            f"against the {RECIPROCITY_BAND:.0e} band "
            f"(||Z - Z^T||/||Z|| = "
            f"{np.linalg.norm(z - z.T) / np.linalg.norm(z):.6e}; step 2c's "
            "record 2.574249e-11)",
            flush=True,
        )

    assert reciprocity <= RECIPROCITY_BAND, (
        f"lumped-sheet sweep reciprocity ||S - S^T||/||S|| = {reciprocity:.6e} "
        f"above the pre-stated {RECIPROCITY_BAND:.0e} band — the example path "
        "is off the `PORT-9` step 2c record; known-issues entry, report, stop"
    )

    # The cross-route reading carried through the sweep, against the same band.
    rows = []
    for driven_id, response in sorted(result.excitation_results.items()):
        for port_id, est in sorted(response.responses.items()):
            if est.is_driven:
                continue
            assert est.path_voltage_v is not None, (
                f"driven {driven_id}, port {port_id}: the route dropped the "
                "path voltage the cross-route comparison is read from"
            )
            deviation = abs(est.voltage_v - est.path_voltage_v) / abs(
                est.path_voltage_v
            )
            rows.append((driven_id, port_id, est, float(deviation)))
    assert rows, "the sweep produced no undriven-port reading to compare"

    if comm.rank == 0:
        print(
            f"\n[step 2c] CROSS-ROUTE inside the sweep (band "
            f"{CROSS_ROUTE_BAND * 100:.0f}%, unmoved; step 2b read "
            f"{STEP2B_CROSS_ROUTE_AT_HALF_WIDTH * 100:.4f}% at the same width "
            "under the impressed-gap drive, so the two are compared, not "
            "gated at 1e-4):",
            flush=True,
        )
        for driven_id, port_id, est, deviation in rows:
            print(
                f"    driven {driven_id}, undriven {port_id}: |dV|/|V| = "
                f"{deviation * 100:8.4f}%  (step 2b "
                f"{STEP2B_CROSS_ROUTE_AT_HALF_WIDTH * 100:.4f}%, delta "
                f"{abs(deviation - STEP2B_CROSS_ROUTE_AT_HALF_WIDTH) * 100:.4f} pp)"
                f"  V_sheet = {est.voltage_v:+.9e}, V_path = "
                f"{est.path_voltage_v:+.9e} V",
                flush=True,
            )
    for driven_id, port_id, _est, deviation in rows:
        assert deviation <= CROSS_ROUTE_BAND, (
            f"driven {driven_id}, undriven {port_id}: the sheet's terminal "
            f"voltage and the path integral differ by {deviation * 100:.4f}%, "
            f"above the unmoved {CROSS_ROUTE_BAND * 100:.0f}% band"
        )

    # ---- ParaView ---------------------------------------------------------
    assert gated_field is not None, "the gated rung's field was not retained"
    written = _write_paraview(
        msh, cell_tags, facet_tags, _paraview_fields(msh, gated_field), comm
    )
    if comm.rank == 0:
        print("\n[paraview] wrote:")
        for what, path in written.items():
            print(f"  {what:<16s} {path}")
        print(
            "\n[paraview] the _combined file carries the f = 0.5 solved phasor "
            "(E_real / E_imag / E_magnitude)"
            "\n           beside `CellTags` (1/2 wire, 3 air, 101/111 and "
            "102/112 the gap-box halves);"
            "\n           open the _facets file and threshold `mesh_tags` on "
            "211/212 to see the port"
            "\n           sheets the lumped BC lives on."
            f"\n\nAll gates hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
