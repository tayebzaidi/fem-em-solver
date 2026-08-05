"""`PORT-1` step 3b-iv — port facet tags on the arc-end discs, mesh only.

``two_torus_domain(port_gap=True)`` now emits one facet physical group per
port (``201`` / ``202``) holding the surfaces the gap box and the conductor
arc share. No field is solved here: this file gates the *area* of those facet
groups against the analytic cut, so step 3b-v's facet-integral port voltage
starts from a surface that is known to be the right one.

**What the analytic area is, and why it is not ``pi r^2``.** The gap box
overhangs the tube in ``x`` and ``z`` (``gap_half_xz = minor_radius +
gap_clearance``), so the arc can only leave the box through the two ``y``-faces
at ``y = +/- gap_half_y``. Those planes are *not* normal to the tube axis --
the arc crosses them at ``phi = arcsin(gap_half_y / major_radius) ~ 0.2 rad``
off the ``+x`` axis -- so each cut is an oblique section of the solid torus,
larger than the tube's circular cross-section. Its exact area follows from
the solid torus ``(sqrt(x^2+y^2) - R)^2 + (z-z0)^2 <= r^2`` restricted to
``y = y0``: substituting ``s = sqrt(x^2 + y0^2)``,

    A(y0) = int_{R-r}^{R+r} 2 sqrt(r^2 - (s-R)^2) * s / sqrt(s^2 - y0^2) ds

which reduces to ``pi r^2`` at ``y0 = 0`` and is ~2% larger at this fixture's
``y0``. That integral is the anchor; the naive ``pi r^2`` is printed beside it
so the discrepancy stays visible rather than being absorbed into a tolerance.
The 2.16% correction is confirmed independently: the quadrature above gives
1.604721580e-04 m^2 for the pair and OCC's own ``getMass(2, .)`` on the two
CAD surfaces gives 1.604721e-04 m^2 (printed by the mesh generator).

**Negative controls.** (a) The ungapped fixture emits no ``2xx`` facet group at
all — exact separation, not a band. (b) A group mistakenly placed on the gap
box's whole ``y``-face would measure ``2 * (2*gap_half_xz)^2``, ~1.80x the disc
pair; the measured area is asserted below that, so the two readings cannot be
confused.
"""

from __future__ import annotations

import numpy as np
import ufl
from mpi4py import MPI
from scipy.integrate import quad

from dolfinx import default_scalar_type, fem

from fem_em_solver.io.mesh import MeshGenerator

SEPARATION = 0.05
MAJOR_RADIUS = 0.02
MINOR_RADIUS = 0.005
RESOLUTION = 0.01
AIR_PADDING = 2.0 * MINOR_RADIUS
WIRE_RESOLUTION = 0.002

GAP_ANGLE = 0.30
GAP_CLEARANCE = 1.0e-3

PORT_FACET_TAGS = (201, 202)


def _gap_half_y():
    return MAJOR_RADIUS * np.sin(0.5 * GAP_ANGLE) + GAP_CLEARANCE


def _gap_half_xz():
    return MINOR_RADIUS + GAP_CLEARANCE


def _analytic_cut_area(y0):
    """Exact area of the plane ``y = y0`` through one solid-torus tube."""
    r, big_r = MINOR_RADIUS, MAJOR_RADIUS
    assert y0 < big_r - r, "the cut plane must not reach the hole of the torus"

    def integrand(s):
        return 2.0 * np.sqrt(max(r * r - (s - big_r) ** 2, 0.0)) * s / np.sqrt(
            s * s - y0 * y0
        )

    value, _ = quad(integrand, big_r - r, big_r + r, limit=200)
    return value


def _analytic_port_area():
    """Two cuts per port, at ``y = +gap_half_y`` and ``y = -gap_half_y``."""
    return 2.0 * _analytic_cut_area(_gap_half_y())


def _analytic_box_face_area():
    """The vacuity ceiling: both whole ``y``-faces of the gap box."""
    return 2.0 * (2.0 * _gap_half_xz()) ** 2


def _facet_group_area(msh, facet_tags, tag, comm):
    """``int_tag 1 dS``, reduced.

    These facets are *interior* (gap on one side, conductor on the other), so
    the measure is ``dS`` with an ``avg`` restriction, not ``ds`` — an ``ds``
    form would silently assemble zero. ``assemble_scalar`` is rank-local.

    ``create_entity_permutations`` is called here, explicitly and on every
    rank, and that is not optional (measured 2026-08-05, known-issues 9):
    an interior-facet assembly needs it, but the assembler only reaches it
    when the rank actually owns integration entities for the tag. Under this
    fixture's partition each rank owns the facets of exactly *one* port, so
    for a given tag one rank entered the collective and the other did not —
    the run hung at ``-n 2`` for 180 s while ``-n 1`` finished in 22.5 s.
    Hoisting the call out makes it collective-symmetric.
    """
    msh.topology.create_entity_permutations()

    dS_tag = ufl.Measure(
        "dS", domain=msh, subdomain_data=facet_tags, subdomain_id=(tag,)
    )
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(ufl.avg(one) * dS_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _global_facet_tag_set(msh, facet_tags, comm):
    local = set(np.unique(facet_tags.values).tolist()) if facet_tags is not None else set()
    return set().union(*comm.allgather(local))


def _gapped_mesh(comm):
    return MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=RESOLUTION,
        air_padding=AIR_PADDING,
        wire_resolution=WIRE_RESOLUTION,
        far_resolution=RESOLUTION,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_clearance=GAP_CLEARANCE,
        comm=comm,
    )


def _mark(comm, msg):
    """Per-rank progress marker (`PORT-1` 3b-iv route 3, known-issues 9).

    Kept in the file: the parallel hang under pytest is not diagnosed, and the
    markers are what localise it. They cost two lines of output per run.
    """
    print(f"[3b-iv r{comm.rank}] {msg}", flush=True)


def test_port_facet_groups_are_the_arc_end_discs():
    """Each port's facet group is the two oblique cuts through its arc."""
    comm = MPI.COMM_WORLD
    _mark(comm, "building gapped mesh ...")
    msh, _, facet_tags = _gapped_mesh(comm)
    _mark(comm, f"mesh built, facet tag entries={facet_tags.values.size}")
    assert facet_tags is not None, "model_to_mesh returned no facet tags"

    # Interior-facet integrals need the facet->cell map built first.
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    _mark(comm, "create_connectivity(fdim, tdim) returned")

    tags_present = _global_facet_tag_set(msh, facet_tags, comm)
    _mark(comm, f"tag set allgathered: {sorted(tags_present)}")
    assert set(PORT_FACET_TAGS) <= tags_present, (
        f"port facet tags missing from the mesh; found {sorted(tags_present)}"
    )

    areas = []
    for t in PORT_FACET_TAGS:
        _mark(comm, f"assembling dS area for tag {t} ...")
        areas.append(_facet_group_area(msh, facet_tags, t, comm))
        _mark(comm, f"tag {t} area reduced")
    a_exact = _analytic_port_area()
    a_naive = 2.0 * np.pi * MINOR_RADIUS**2
    a_face = _analytic_box_face_area()

    if comm.rank == 0:
        print(
            f"\n[3b-iv] facet tags present: {sorted(tags_present)}"
            f"\nA_201={areas[0]:.9e}  A_202={areas[1]:.9e}  m^2"
            f"\nanalytic oblique cut pair={a_exact:.9e}  "
            f"meshed/analytic={areas[0] / a_exact:.9f}, {areas[1] / a_exact:.9f}"
            f"\nnaive 2*pi*r^2={a_naive:.9e} "
            f"(exact/naive={a_exact / a_naive:.9f}); "
            f"gap-box y-face pair={a_face:.9e} "
            f"(={a_face / a_exact:.6f}x the cut pair)"
            f"\nport-to-port ratio={areas[0] / areas[1]:.12f}",
            flush=True,
        )

    # Band measured 2026-08-05 (probe log
    # 20260805T020659Z_PORT-1-step3biv-serial-isolation.log): 0.974490841 for
    # both ports at WIRE_RESOLUTION = 0.002. The 2.55% deficit is the same
    # chordal effect the volume shows (0.980079 on the ungapped torus, and
    # 0.98030 on the gapped arc): a linear-tet mesh inscribes the curved tube
    # surface, so a cut through it is inscribed in the analytic cut too. The
    # expectation written into the 3b-iv plan — "far tighter than the volume's
    # 0.980" — is refuted by this measurement; a section of an inscribed solid
    # inherits the solid's deficit rather than improving on it.
    for tag, a in zip(PORT_FACET_TAGS, areas):
        assert 0.970 < a / a_exact < 0.980, (
            f"facet group {tag} area {a:.9e} m^2 is {a / a_exact:.9f} of the "
            f"analytic oblique cut pair {a_exact:.9e} m^2, outside the "
            "measured band (0.970, 0.980)"
        )

    # Vacuity control: a group placed on the gap box's whole y-faces instead of
    # the conductor cut would read ~1.80x this. Total separation.
    for tag, a in zip(PORT_FACET_TAGS, areas):
        assert a < 0.75 * a_face, (
            f"facet group {tag} area {a:.9e} m^2 is not separated from the "
            f"whole-y-face reading {a_face:.9e} m^2 — the group is on the box "
            "face, not on the conductor cut"
        )

    # Same solid, mirrored in z: the two ports are built identically.
    assert abs(areas[0] / areas[1] - 1.0) < 1e-9, (
        f"port facet areas differ: {areas[0]:.12e} vs {areas[1]:.12e}"
    )


def test_ungapped_fixture_emits_no_port_facet_groups():
    """Negative control: without `port_gap` there is no `2xx` facet group."""
    comm = MPI.COMM_WORLD
    msh, _, facet_tags = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=RESOLUTION,
        air_padding=AIR_PADDING,
        wire_resolution=WIRE_RESOLUTION,
        far_resolution=RESOLUTION,
        comm=comm,
    )
    tags_present = _global_facet_tag_set(msh, facet_tags, comm)

    if comm.rank == 0:
        print(f"\n[3b-iv ungapped control] facet tags: {sorted(tags_present)}",
              flush=True)

    assert not (set(PORT_FACET_TAGS) & tags_present), (
        f"the ungapped path emitted port facet tags: {sorted(tags_present)}"
    )
    # Nothing is asserted about the outer-boundary group (tag 1) here: measured
    # 2026-08-05, it does not reach the dolfinx facet tags from *either* path
    # (the gapped mesh reports [201, 202] only). That is pre-existing and is
    # filed in known-issues.md, not fixed in passing.
