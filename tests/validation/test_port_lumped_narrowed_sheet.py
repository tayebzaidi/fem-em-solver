"""`PORT-9` step 2b — **the narrowed port sheet gates the cross-route band**.

Step 2 (2026-08-17) measured a cross-route deviation of **7.7095%** between the
lumped-port route and the gated gap-voltage route on the two-torus fixture,
outside the 5% band pre-stated at scoping, and *diagnosed* the miss: it is the
transverse average over the port sheet, 7.7783 pp of it, against a
path/projection residual of only 0.0763 pp.  The lumped port reads
``V = −(1/w)∫_S E·ĥ dS`` — the gap voltage averaged **across the width of the
gap box** — while the gap route integrates the centreline alone, and step 2's
transverse profile showed the dilution lives in the outer ~25% of the width: the
seven interior stations (``|s| ≤ 0.735`` of the half-width) all sit within
**1.1%** of the chord.

The 2026-08-17 10:30 review's decision was **narrow the sheet**, not widen the
band and not redefine the terminal voltage as the sheet average (which would
re-derive every `PORT-1` systematic for no physical gain, and a quoted 7.8% feed
systematic would not transfer — it is a property of *this box's* width-to-gap
ratio).  Physically the narrow sheet is also the honest model: a real feed strap
is narrower than the gap box it sits in.

**What this module does.**  One mesh of the step-1 solve fixture, then for each
interior width fraction ``f ∈ {1.0, 0.735, 0.5}`` a lumped-port sheet built on
the *filtered* facet set ``|x − a| ≤ f·half_xz`` and its own assembly + solve
(the BC surface enters the bilinear form, so a width is a solve).  Off each
solved field both routes are read exactly as step 1 reads them.

The filter is a **facet-midpoint** filter applied to `GEO-16`'s already
dolfinx-side-rebuilt ``21x`` tags — no gmsh change, no re-mesh, and the mesh is
bit-identical across the ladder, which is what makes ``f = 1.0`` a usable
negative control.

**Traps carried forward from step 1, verbatim.**  Complex build
(``FEM_EM_REQUIRE_COMPLEX=1``); the generator-convention sign, so the terminal
voltage comparable to the gap route is ``−I·Z_p``; two cell tags per gap box
after the fragment; and — the one this step adds — ``w`` is **re-measured from
the filtered facet set**, never taken as ``f × w_full``: the sheet crosses a
round arc, and the filtered set's nodes reach past its midpoints.  The measured
width is the **area-based effective width ``A/h``**, not the bounding-box
extent; that distinction is worth 14 pp on the narrow rungs and is the one
thing this run had to measure before its own gate meant anything (see the
comment at the measurement, and the first attempt's log).

**Bands, all pre-stated and none invented here.**  At ``f = 0.5`` the
cross-route ``|ΔZ₁₂|/|Z₁₂| ≤ 5%`` — step 2's own band, unmoved, now *expected*
to hold; at every width the open-limit reduction
``V_lumped = −(1/w_f)∫_S E·ĥ dS`` to < 1e-11; and ``f = 1.0`` reproduces step
2's **7.7095%** record to 1e-4 (a narrowing that moved the full-width answer
would have changed the fixture, not the sheet).

Cost: standard tier, ``-n 2``, one mesh (~40 s) and three solves (~25 s each).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-9-step2b "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 500 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_lumped_bc.py \\
       tests/validation/test_port_lumped_narrowed_sheet.py -v -s'"
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import ufl
from mpi4py import MPI

import dolfinx

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.ports.lumped import (
    LumpedPortSheet,
    lumped_port_bilinear_term,
    sheet_terminal_current,
)
from fem_em_solver.ports.systematics import mutual_systematics_ladder

from tests.complex_mode import complex_only
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_two_torus_port_sheet import (
    SHEET_FACET_TAGS,
    _sheet_extents,
    _sheet_facet_count,
)
from tests.validation.test_port_gap_voltage_impedance import (
    DRIVE_CURRENT_A,
    FREQUENCY_HZ,
    GAP_TAGS,
    MAJOR_RADIUS,
    OMEGA,
    PATH_QUADRATURE_GATE_ORDERS,
    PRODUCTION_LADDER_DRIVEN_COLUMN,
    SEPARATION,
    SIGMA_WIRE_S_PER_M,
    WIRE_TAGS,
    MINOR_RADIUS,
    _azimuthal_unit,
    _gap_drive,
    _gap_half_extents,
    _path_voltage,
    _reduce,
    _tag_measure,
    _tag_volume,
)
from tests.validation.test_port_reaction_impedance import mutual_inductance
from tests.validation.test_port_lumped_two_torus import (
    AREA_IDENTITY_BAND,
    CROSS_ROUTE_BAND,
    DECOMPOSITION_IDENTITY_BAND,
    GAP_CELL_TAGS_WITH_SHEET,
    PROBE_PORT_IMPEDANCE_OHM,
    QUADRATURE_DRIFT_TOLERANCE,
    REPRODUCTION_BAND,
    STEP1_GAP_RATIO_RECORD,
    STEP1_CROSS_ROUTE_RECORD,
    VOLUME_IDENTITY_BAND,
    _build,
)

# The ladder the review scoped. ``1.0`` is the negative control (the whole
# mid-plane, i.e. step 2's own sheet); ``0.735`` is the outermost station step
# 2's profile measured inside 1.1% of the chord; ``0.5`` is the width the band
# is gated at.
WIDTH_FRACTIONS = (1.0, 0.735, 0.5)
GATED_WIDTH_FRACTION = 0.5

# Step 2's transverse profile predicted the narrowed sheets: every station with
# ``|s| ≤ 0.735`` read within 1.1% of the chord, so a sheet restricted to that
# width should read the centreline voltage to ~1%. Printed beside the measured
# ladder — a *prediction*, never an assertion (the assertion is the 5% band).
PROFILE_PREDICTION = 0.011


def _narrowed_sheet_tags(msh, facet_tags, sheet_tag, fraction, x_centre, half_xz):
    """`GEO-16`'s sheet tag, restricted to ``|x − a| ≤ f·half_xz``.

    The ``21x`` groups are rebuilt dolfinx-side from cell tags, so narrowing the
    port sheet needs no gmsh change and no re-mesh: it is a filter on the facet
    **midpoints** of the existing tag, and every other tag in the mesh passes
    through untouched.  The mesh itself is therefore bit-identical across the
    width ladder — which is what makes ``f = 1.0`` a control on the fixture
    rather than on a second mesh.

    Midpoints, not nodes: a node-based test would drop or keep a facet according
    to which of its three corners cleared the threshold, and the two rules would
    disagree on exactly the boundary strip whose contribution the ladder is
    measuring.  ``w`` is re-measured from the *result* (nodes reach past the
    kept midpoints, and the sheet crosses a round arc), never computed as
    ``f × w_full``.
    """
    fdim = msh.topology.dim - 1
    idx = np.asarray(facet_tags.indices, dtype=np.int32)
    val = np.asarray(facet_tags.values, dtype=np.int32)
    on_sheet = val == int(sheet_tag)
    sheet_facets = idx[on_sheet]
    keep = np.ones(sheet_facets.size, dtype=bool)
    if sheet_facets.size:
        mid = dolfinx.mesh.compute_midpoints(msh, fdim, sheet_facets)
        keep = np.abs(mid[:, 0] - x_centre) <= fraction * half_xz
    new_idx = np.concatenate([idx[~on_sheet], sheet_facets[keep]]).astype(np.int32)
    new_val = np.concatenate(
        [
            val[~on_sheet],
            np.full(int(np.count_nonzero(keep)), int(sheet_tag), dtype=np.int32),
        ]
    ).astype(np.int32)
    order = np.argsort(new_idx, kind="stable")
    return dolfinx.mesh.meshtags(msh, fdim, new_idx[order], new_val[order])


@pytest.fixture(scope="module")
def width_ladder():
    """One mesh; one assembly + solve per interior width fraction."""
    comm = MPI.COMM_WORLD
    col = PRODUCTION_LADDER_DRIVEN_COLUMN          # 0 -> gap 101 driven
    driven_tags = GAP_CELL_TAGS_WITH_SHEET[GAP_TAGS[col]]
    sheet_tag = int(SHEET_FACET_TAGS[1 - col])     # 212 — the undriven port

    msh, cell_tags, facet_tags, t_mesh = _build(comm)
    assert facet_tags is not None, "model_to_mesh returned no facet tags"
    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
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

    rungs = []
    for fraction in WIDTH_FRACTIONS:
        tags_f = _narrowed_sheet_tags(
            msh, facet_tags, sheet_tag, fraction, MAJOR_RADIUS, half_xz
        )
        n_facets = _sheet_facet_count(msh, tags_f, sheet_tag, comm)
        assert n_facets > 0, (
            f"f = {fraction}: the narrowed sheet has no owned facets anywhere — "
            "the port form would be an integral over nothing"
        )
        area_f = _facet_group_area(msh, tags_f, sheet_tag, comm)
        extents_f = _sheet_extents(msh, tags_f, sheet_tag, comm)
        w_bbox_f = float(extents_f[0])
        h_f = float(extents_f[1])
        # The measured width is the **area-based effective width** A/h, not the
        # bounding-box extent — measured 2026-08-17, first attempt of this run
        # (`20260817T170448Z_PORT-9-step2b.log`), where taking the bbox extent
        # put the ladder at 16.39% / 14.04% instead of the profile's ~1%.
        #
        # Why: the midpoint filter leaves a *ragged* edge — a facet is kept
        # whole when its midpoint clears the threshold, so its nodes reach past
        # it — and the kept region is then not a rectangle. ``R = Z_p*w/h``
        # counts squares between the terminal edges, i.e. it wants the strip's
        # mean width; the bbox extent is its *maximum*. On this ladder the two
        # differ by 15.3% (f = 0.735) and 14.2% (f = 0.5), and the resulting
        # mis-scaling of ``I*Z_p = (1/w) int_S E.hhat dS`` reproduced the whole
        # deviation. A/h is the mean width by definition, it makes the lumped
        # reading the true *area* average of ``E.yhat`` (times h), and on a
        # rectangle it IS the bbox extent — asserted below on the f = 1.0 rung,
        # which is why the negative control is untouched by this choice.
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

        e = fields.e_complex
        i_conduction = (
            SIGMA_WIRE_S_PER_M
            * _reduce(
                ufl.inner(e, phi_hat) * _tag_measure(msh, cell_tags, WIRE_TAGS[col]),
                comm,
            )
            / arc_length
        )
        v_gap = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[-1], comm)
        v_gap_coarse = _path_voltage(e, 1 - col, PATH_QUADRATURE_GATE_ORDERS[0], comm)
        # Generator convention (step 1's trap): the terminal voltage comparable
        # to the gap route's V = -int E.that dl is -I*Z_p.
        i_sheet = sheet_terminal_current(msh, tags_f, sheet, e, comm)
        v_lumped = -i_sheet * PROBE_PORT_IMPEDANCE_OHM

        # The open-limit reduction, assembled independently of ports.lumped so
        # it stays a *checked* identity at every width, not a restatement.
        ds_sheet = ufl.Measure(
            "dS", domain=msh, subdomain_data=tags_f, subdomain_id=(sheet_tag,)
        )
        h_hat = ufl.as_vector([0.0, 1.0, 0.0])
        int_ey = _reduce(ufl.inner(e("+"), h_hat) * ds_sheet, comm)
        v_sheet_average = -int_ey / w_f

        z12_gap = v_gap / i_conduction
        z12_lumped = v_lumped / i_conduction
        rungs.append(
            {
                "f": float(fraction),
                "facets": int(n_facets),
                "area": float(area_f),
                "w": w_f,
                "w_bbox": w_bbox_f,
                "h": h_f,
                "out_of_plane": float(extents_f[2]),
                "sheet_resistivity": sheet.sheet_resistivity,
                "solve_time": t_solve,
                "i_conduction": i_conduction,
                "i_sheet": i_sheet,
                "v_gap": v_gap,
                "v_lumped": v_lumped,
                "v_sheet_average": v_sheet_average,
                "quadrature_drift": abs(v_gap - v_gap_coarse) / abs(v_gap),
                "ratio_gap": abs(z12_gap.imag) / omega_m,
                "ratio_lumped": abs(z12_lumped.imag) / omega_m,
                "corrected_gap": mutual_systematics_ladder(z12_gap.imag, omega_m)[
                    "corrected"
                ],
                "corrected_lumped": mutual_systematics_ladder(
                    z12_lumped.imag, omega_m
                )["corrected"],
                "cross_route": abs(z12_lumped - z12_gap) / abs(z12_gap),
            }
        )
        del fields, e, solver, problem, tags_f

    record = {
        "cells": int(ncells),
        "mesh_time": t_mesh,
        "sheet_tag": sheet_tag,
        "sheet_area_cad": sheet_area_cad,
        "gap_volume_ratio": gap_volume / gap_volume_analytic,
        "half_xz": half_xz,
        "omega_m": omega_m,
        "rungs": rungs,
    }
    if comm.rank == 0:
        print(
            f"\n[PORT-9 step2b] fragmented two-torus fixture: {ncells} cells, "
            f"mesh {t_mesh:.1f} s; driven gap cell tags {driven_tags}, narrowed "
            f"lumped sheets on facet tag {sheet_tag}; solves "
            + ", ".join(f"f={r['f']:.3f} {r['solve_time']:.1f} s" for r in rungs),
            flush=True,
        )
    del msh, cell_tags, facet_tags
    return record


@complex_only
def test_the_width_ladder_is_a_nested_family_on_one_fixture(width_ladder):
    """Structural identities, asserted before any route is compared.

    The ladder only means something if each rung is the *same* fixture with a
    *smaller* sheet: the gap box the drive normalises through is untouched
    (meshed/analytic volume, `PORT-1` 3b-i's 1.000000000000), the ``f = 1.0``
    rung is the whole CAD mid-plane (so the control really is step 2's sheet),
    each narrower rung has strictly fewer facets and strictly less area, and
    every rung is still planar (out-of-plane spread at round-off).  Each
    terminal path integral is checked converged in its quadrature.
    """
    r = width_ladder
    assert abs(r["gap_volume_ratio"] - 1.0) < VOLUME_IDENTITY_BAND, (
        f"meshed/analytic gap-box volume {r['gap_volume_ratio']:.12f} over both "
        "halves — narrowing the sheet moved the volume the drive normalises "
        "through, so the rungs are not one fixture"
    )
    full = r["rungs"][0]
    assert full["f"] == 1.0, "the first rung must be the full-width control"
    area_ratio = full["area"] / r["sheet_area_cad"]
    assert abs(area_ratio - 1.0) < AREA_IDENTITY_BAND, (
        f"f = 1.0: meshed/CAD sheet area {area_ratio:.12f} — the control sheet "
        "is not the gap box's mid-plane, so it is not step 2's sheet"
    )
    # The full-width sheet is a rectangle, so its area-based effective width
    # A/h — the width every rung's ``R = Z_p*w/h`` is measured with — must be
    # its bounding-box extent to round-off. This is what makes the control a
    # control: the width definition the narrow rungs need cannot have moved the
    # rung that reproduces step 2.
    assert abs(full["w"] / full["w_bbox"] - 1.0) < AREA_IDENTITY_BAND, (
        f"f = 1.0: effective width A/h = {full['w']:.9e} m against the "
        f"bounding-box extent {full['w_bbox']:.9e} m — the full-width sheet is "
        "not the rectangle both definitions assume it is"
    )
    for prev, rung in zip(r["rungs"], r["rungs"][1:]):
        assert rung["facets"] < prev["facets"], (
            f"f = {rung['f']}: {rung['facets']} facets against "
            f"{prev['facets']} at f = {prev['f']} — the filter did not narrow"
        )
        assert rung["area"] < prev["area"], (
            f"f = {rung['f']}: area {rung['area']:.9e} against "
            f"{prev['area']:.9e} at f = {prev['f']}"
        )
    for rung in r["rungs"]:
        assert rung["out_of_plane"] < 1.0e-12, (
            f"f = {rung['f']}: out-of-plane spread {rung['out_of_plane']:.3e} m "
            "— the filtered facet set is not a plane"
        )
        assert rung["quadrature_drift"] < QUADRATURE_DRIFT_TOLERANCE, (
            f"f = {rung['f']}: the terminal path integral moved "
            f"{rung['quadrature_drift']:.3e} between orders "
            f"{PATH_QUADRATURE_GATE_ORDERS}"
        )

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step2b] sheet {r['sheet_tag']} width ladder "
            f"(half-width {r['half_xz']:.6e} m, tube minor radius "
            f"{MINOR_RADIUS:.6e} m); meshed/analytic gap volume "
            f"{r['gap_volume_ratio']:.12f}",
            flush=True,
        )
        for rung in r["rungs"]:
            print(
                f"    f = {rung['f']:.3f}  facets {rung['facets']:5d}  "
                f"area {rung['area']:.9e} m^2 "
                f"({rung['area'] / r['sheet_area_cad']:.9f} of CAD)  "
                f"w = A/h = {rung['w']:.9e} m (bbox extent "
                f"{rung['w_bbox']:.9e}, f*w_full would be "
                f"{rung['f'] * r['rungs'][0]['w']:.9e})  h = {rung['h']:.9e} m  "
                f"w/h = {rung['w'] / rung['h']:.9f} squares  "
                f"R = {rung['sheet_resistivity']:.6e} Ohm/square",
                flush=True,
            )


@complex_only
def test_the_open_limit_reduction_holds_at_every_width(width_ladder):
    """``V_lumped = -(1/w_f) int_S E.hhat dS`` — step 2's identity, per rung.

    The narrowing changes the sheet the port model integrates over *and* the
    ``w`` its ``R = Z_p*w/h`` is scaled by; if the two ever came from different
    facet sets, the terminal voltage would silently be scaled by the wrong
    width and the whole ladder would be a measurement of that bug.  Checked
    against an independently assembled form, as in step 2.
    """
    for rung in width_ladder["rungs"]:
        rel = abs(rung["v_lumped"] - rung["v_sheet_average"]) / abs(rung["v_lumped"])
        assert rel < DECOMPOSITION_IDENTITY_BAND, (
            f"f = {rung['f']}: lumped terminal voltage {rung['v_lumped']:+.9e} V "
            f"against the independently assembled sheet average "
            f"{rung['v_sheet_average']:+.9e} V — relative {rel:.3e}, above "
            f"{DECOMPOSITION_IDENTITY_BAND:.0e}: the port model's sheet and the "
            "width it is scaled by are not the same facet set"
        )


@complex_only
def test_full_width_reproduces_the_step_2_record(width_ladder):
    """**The negative control.**  ``f = 1.0`` is step 2's own measurement.

    The whole mid-plane is the sheet step 2 read 7.7095% off.  If this rung
    moved, the narrowing machinery changed the *fixture* — the mesh, the drive,
    the solve — and the ladder below would be measuring that change rather than
    the width.  The gap route is checked at the same grain for the same reason.
    """
    full = width_ladder["rungs"][0]
    for name, measured, record in (
        ("cross-route", full["cross_route"], STEP1_CROSS_ROUTE_RECORD),
        ("gap ratio", full["ratio_gap"], STEP1_GAP_RATIO_RECORD),
    ):
        assert abs(measured - record) < REPRODUCTION_BAND, (
            f"f = 1.0 {name}: {measured:.6f} against the step-1/2 record "
            f"{record:.6f} — moved by {abs(measured - record):.2e}, above "
            f"{REPRODUCTION_BAND:.0e}; the width filter changed the fixture, "
            "not just the sheet"
        )


@complex_only
def test_the_narrowed_sheet_gates_the_cross_route_band(width_ladder):
    """**Step 2b's gate.**  At ``f = 0.5`` the cross-route band must hold.

    Step 2's band — ``|dZ12|/|Z12| <= 5%`` between the two feed models on
    identical geometry — pre-stated at scoping, never widened, and missed at
    7.7095% by the full-width sheet.  The diagnosis said the miss was the
    transverse average and nothing else; the review's decision was to narrow the
    port sheet to the interior width, where step 2's own profile put every
    station within 1.1% of the chord.  This asserts the consequence.

    A deviation that does *not* fall toward the profile's ~1% as ``f`` shrinks
    refutes the transverse-averaging diagnosis — that is the informative
    negative result, and the band still never widens.
    """
    r = width_ladder
    gated = [x for x in r["rungs"] if x["f"] == GATED_WIDTH_FRACTION]
    assert len(gated) == 1, "the gated width fraction is not on the ladder"
    gated = gated[0]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step2b] CROSS-ROUTE ladder (omega*M12 = "
            f"{r['omega_m']:.6f} Ohm; band {CROSS_ROUTE_BAND * 100:.0f}%, "
            f"pre-stated at scoping and not widened; step 2's transverse "
            f"profile predicts ~{PROFILE_PREDICTION * 100:.1f}% at interior "
            f"width):",
            flush=True,
        )
        for rung in r["rungs"]:
            verdict = "INSIDE" if rung["cross_route"] <= CROSS_ROUTE_BAND else "MISS"
            print(
                f"    f = {rung['f']:.3f}  |dZ12|/|Z12| = "
                f"{rung['cross_route'] * 100:8.4f}%  {verdict:6s}  "
                f"gap {rung['ratio_gap']:.6f} x omega*M12 "
                f"(corrected {rung['corrected_gap']:.6f}), lumped "
                f"{rung['ratio_lumped']:.6f} (corrected "
                f"{rung['corrected_lumped']:.6f})  "
                f"V_gap = {rung['v_gap']:+.9e}, V_lumped = "
                f"{rung['v_lumped']:+.9e} V",
                flush=True,
            )
        print(
            f"[PORT-9 step2b] GATE at f = {GATED_WIDTH_FRACTION}: "
            f"{gated['cross_route'] * 100:.4f}% against the "
            f"{CROSS_ROUTE_BAND * 100:.0f}% band",
            flush=True,
        )

    assert gated["cross_route"] <= CROSS_ROUTE_BAND, (
        f"f = {GATED_WIDTH_FRACTION}: cross-route deviation "
        f"{gated['cross_route'] * 100:.4f}% against the pre-stated "
        f"{CROSS_ROUTE_BAND * 100:.0f}% band — the narrowed sheet does NOT "
        "recover the centreline voltage, which refutes step 2's "
        "transverse-averaging diagnosis (§7 `PORT-9` step 2b, negative "
        "result: record the ladder, open a known-issues entry, report, stop). "
        "The band is never widened to admit it."
    )
