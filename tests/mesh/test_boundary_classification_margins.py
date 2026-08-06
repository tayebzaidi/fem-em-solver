"""`GEO-11` gate: two-sided margins of the `outer_boundary` wall tests.

`GEO-10` found that gmsh inflates an OCC entity's bounding box by its geometric
tolerance — measured `1.000e-07` on `two_torus_domain` — so a wall test tighter
than that padding silently classifies **zero** surfaces and the boundary
physical group is never declared at all.  No error, no warning; the group is
just missing (`20260806T050143Z_GEO-10-probe.log`, `tol = 1e-9` classifying
zero of six walls).  The fix there raised that fixture's ``tol`` to ``1e-6``.

The other `outer_boundary` derivations in ``io/mesh.py`` were *believed* safe,
but that belief rested on one fixture's measurement.  This file converts the
hazard into numbers.  For each fixture below it replicates the **CAD stage
only** — build the OCC model, fragment, synchronize, never mesh — applies that
fixture's own classification predicate to every dim-2 entity, and asserts a
two-sided separation:

* every surface the predicate *accepts* sits at ``residual/tol <= 0.1`` —
  the tolerance clears the bounding-box padding by 10x, so the group cannot
  silently empty the way `GEO-10`'s did;
* every surface the predicate *rejects* sits at ``residual/tol >= 10`` —
  the tolerance stays an order below the nearest interior face, so no interior
  face can be swept into the boundary group.

Equivalently: no surface's residual lands in the ambiguous band
``[0.1*tol, 10*tol]``.  Per-surface numbers are printed, so a failure reports
the offending margin rather than just a boolean.

CAD only, serial, no meshing: smoke tier, ``-n 1``.

What it measured (2026-08-06, `20260806T140325Z_GEO-11-probe.log`).  Two of the
four fixtures do not meet the margin, and one of them fails the `GEO-10` way:

* ``loop_over_half_space_domain`` (`MAT-6`) and ``sphere_in_box_domain``
  (`TH-8`/`MAT-4`) classify **zero** walls — 0 of 12 and 0 of 7 — because their
  ``tol = 1e-9`` sits 100x *below* the same ``1.000e-07`` OCC padding `GEO-10`
  measured.  Their ``outer_boundary`` group is never declared.  This is
  **latent, not a live wrong result**: every caller of both generators discards
  ``facet_tags`` (``msh, cell_tags, _ = ...``) and imposes its wall condition
  geometrically, so no landed gate reads the missing group.  known-issues 12.
* ``cylindrical_domain``'s interior margin is 4.50x its tolerance, below the
  10x floor — the inner cylinder's end caps sit at ``r = 0.01`` against an
  outer wall at ``r = 0.1`` with ``tol = resolution = 0.02``.  known-issues 13.
* ``two_torus_domain`` meets both sides, at exactly the 10x `GEO-10` designed.

Per the `GEO-11` plan, this chunk does **not** move any tolerance — that is a
per-fixture decision for a review with these numbers in hand.  The two failing
fixtures are pinned at their measured ratios instead, so the defect cannot
drift silently while the review holds it.

Scope.  The four fixtures gated here are the ones whose CAD stage is short
enough to replicate faithfully.  ``coil_phantom_domain`` and
``birdcage_port_domain`` are **not** covered — their CAD stages are ~190 lines
each and a copy would drift from the original silently, which is worse than no
gate.  Covering them needs the CAD stage factored out of the generator; that is
a separate chunk's decision, not something to improvise here.  See PROJECT_PLAN
§7 `GEO-11` and docs/testing/known-issues.md.
"""

from __future__ import annotations

from typing import Callable

import gmsh
import numpy as np
import pytest

#: A surface the predicate accepts must clear the bounding-box padding by this
#: factor: ``residual <= WALL_MARGIN * tol``.
WALL_MARGIN = 0.1
#: A surface the predicate rejects must sit at least this far outside the
#: tolerance: ``residual >= INTERIOR_MARGIN * tol``.
INTERIOR_MARGIN = 10.0

Bbox = tuple[float, float, float, float, float, float]
Residual = Callable[[Bbox], float]


def _box_and_residual(half_x: float, half_y: float, half_z: float) -> Residual:
    """Residual for the ``and``-paired box wall test.

    Matches ``two_torus_domain`` / ``loop_over_half_space_domain`` /
    ``sphere_in_box_domain``: a surface is on wall ``x-`` when *both* extremes
    of its bounding box coincide with that wall.  The clause residual is
    therefore the larger of the two extremes' distances, and the surface's
    residual is the smallest such clause over the six walls.
    """

    def residual(bbox: Bbox) -> float:
        x0, y0, z0, x1, y1, z1 = bbox
        clauses = (
            max(abs(x0 + half_x), abs(x1 + half_x)),
            max(abs(x0 - half_x), abs(x1 - half_x)),
            max(abs(y0 + half_y), abs(y1 + half_y)),
            max(abs(y0 - half_y), abs(y1 - half_y)),
            max(abs(z0 + half_z), abs(z1 + half_z)),
            max(abs(z0 - half_z), abs(z1 - half_z)),
        )
        return float(min(clauses))

    return residual


def _radial_residual(radius: float) -> Residual:
    """Residual for the ``abs(r_max - R) < resolution`` cylindrical wall test.

    Matches ``cylindrical_domain``: ``r_max`` is built from the bounding box's
    positive extremes only, exactly as the generator does.
    """

    def residual(bbox: Bbox) -> float:
        _, _, _, x_max, y_max, _ = bbox
        r_max = float(np.sqrt(max(x_max**2, y_max**2)))
        return abs(r_max - radius)

    return residual


def _build_two_torus() -> tuple[Residual, float]:
    """`GEO-10`'s fixture, at ``io/mesh.py`` ``two_torus_domain`` defaults."""
    separation = 0.05
    major_radius = 0.02
    minor_radius = 0.005

    gmsh.model.add("geo11_two_torus")
    z_offset = separation / 2
    wire_1 = gmsh.model.occ.addTorus(0, 0, -z_offset, major_radius, minor_radius)
    wire_2 = gmsh.model.occ.addTorus(0, 0, z_offset, major_radius, minor_radius)

    padding = 2.0 * minor_radius
    radial_extent = major_radius + minor_radius
    box_half_x = radial_extent + padding
    box_half_y = radial_extent + padding
    box_half_z = z_offset + minor_radius + padding

    domain = gmsh.model.occ.addBox(
        -box_half_x, -box_half_y, -box_half_z,
        2.0 * box_half_x, 2.0 * box_half_y, 2.0 * box_half_z,
    )
    gmsh.model.occ.fragment([(3, domain)], [(3, wire_1), (3, wire_2)])
    gmsh.model.occ.synchronize()

    # tol as landed by `GEO-10`; see io/mesh.py ~line 1174.
    return _box_and_residual(box_half_x, box_half_y, box_half_z), 1e-6


def _build_loop_over_half_space() -> tuple[Residual, float]:
    """`MAT-6`'s fixture, at ``loop_over_half_space_domain`` defaults."""
    loop_radius = 0.04
    wire_radius = 0.005
    liftoff = 0.015
    W = 0.10

    gmsh.model.add("geo11_loop_over_half_space")
    wire = gmsh.model.occ.addTorus(0, 0, liftoff, loop_radius, wire_radius)
    air = gmsh.model.occ.addBox(-W, -W, 0.0, 2 * W, 2 * W, W)
    slab = gmsh.model.occ.addBox(-W, -W, -W, 2 * W, 2 * W, W)
    gmsh.model.occ.fragment([(3, air), (3, slab)], [(3, wire)])
    gmsh.model.occ.synchronize()

    # tol as in io/mesh.py ~line 1384 — the value `GEO-10` showed can fail.
    return _box_and_residual(W, W, W), 1e-9


def _build_sphere_in_box() -> tuple[Residual, float]:
    """`TH-8`/`MAT-4`'s fixture, at ``sphere_in_box_domain`` defaults."""
    R = 0.05
    W = 0.10

    gmsh.model.add("geo11_sphere_in_box")
    sphere = gmsh.model.occ.addSphere(0.0, 0.0, 0.0, R)
    box = gmsh.model.occ.addBox(-W, -W, -W, 2 * W, 2 * W, 2 * W)
    gmsh.model.occ.fragment([(3, box)], [(3, sphere)])
    gmsh.model.occ.synchronize()

    # tol as in io/mesh.py ~line 1532 — the value `GEO-10` showed can fail.
    return _box_and_residual(W, W, W), 1e-9


def _build_cylindrical() -> tuple[Residual, float]:
    """``cylindrical_domain`` defaults; the wall test is ``< resolution``."""
    inner_radius = 0.01
    outer_radius = 0.1
    length = 0.2
    resolution = 0.02

    gmsh.model.add("geo11_cylindrical")
    inner = gmsh.model.occ.addCylinder(0, 0, -length / 2, 0, 0, length, inner_radius)
    outer = gmsh.model.occ.addCylinder(0, 0, -length / 2, 0, 0, length, outer_radius)
    gmsh.model.occ.fragment([(3, outer)], [(3, inner)])
    gmsh.model.occ.synchronize()

    # tol is the mesh resolution itself; see io/mesh.py ~line 682.
    return _radial_residual(outer_radius), resolution


#: Measured 2026-08-06 (`20260806T140325Z_GEO-11-probe.log`).  Two fixtures do
#: **not** meet the two-sided margin, so this chunk pins what they actually do
#: rather than moving their tolerances: per the `GEO-11` plan, widening a
#: fixture's tolerance is a per-fixture decision for a review with the numbers
#: in hand.  A pinned entry is a regression pin on a known defect, keyed to a
#: known-issues entry; a ``None`` pin means the fixture meets the margin.
#:
#: ``n_surfaces``      total dim-2 entities in the CAD model
#: ``n_accepted``      how many the fixture's own predicate classifies as wall
#: ``wall_ratio``      max(accepted residual)/tol, or ``None`` if none accepted
#: ``interior_ratio``  min(rejected residual)/tol, or ``None`` if none rejected
#: ``pin``             known-issues reference when the margin is not met
EXPECTATIONS = {
    "two_torus_domain": dict(
        n_surfaces=8, n_accepted=6,
        wall_ratio=1.000000e-01, interior_ratio=2.000010e04, pin=None,
    ),
    "loop_over_half_space_domain": dict(
        n_surfaces=12, n_accepted=0,
        wall_ratio=None, interior_ratio=1.000000e02,
        pin="known-issues 12 — outer_boundary group never declared (tol 1e-9 "
            "below the 1.000e-07 OCC padding). Latent: every caller discards "
            "facet_tags and drives the wall geometrically.",
    ),
    "sphere_in_box_domain": dict(
        n_surfaces=7, n_accepted=0,
        wall_ratio=None, interior_ratio=1.000000e02,
        pin="known-issues 12 — outer_boundary group never declared (tol 1e-9 "
            "below the 1.000e-07 OCC padding). Latent: every caller discards "
            "facet_tags and drives the wall geometrically.",
    ),
    "cylindrical_domain": dict(
        n_surfaces=6, n_accepted=3,
        wall_ratio=5.000000e-06, interior_ratio=4.499995e00,
        pin="known-issues 13 — interior margin 4.50x tol, below the 10x floor "
            "(inner cylinder end caps at r=0.01 vs outer wall r=0.1, "
            "tol = resolution = 0.02).",
    ),
}

FIXTURES: tuple[tuple[str, Callable[[], tuple[Residual, float]]], ...] = (
    ("two_torus_domain", _build_two_torus),
    ("loop_over_half_space_domain", _build_loop_over_half_space),
    ("sphere_in_box_domain", _build_sphere_in_box),
    ("cylindrical_domain", _build_cylindrical),
)


def _measure(name: str, build: Callable[[], tuple[Residual, float]]):
    """Build the CAD model, classify every dim-2 entity, print and return.

    gmsh state poisons every later build in the same process (`GEO-9` step 2a),
    so initialize/finalize is bracketed here rather than shared.
    """
    gmsh.initialize()
    try:
        residual_of, tol = build()
        rows = []
        for dim, surf in gmsh.model.getEntities(dim=2):
            bbox = gmsh.model.getBoundingBox(dim, surf)
            residual = residual_of(bbox)
            rows.append((surf, residual, residual < tol))
    finally:
        gmsh.finalize()

    print(f"\n[geo11] {name}: tol={tol:.3e}, {len(rows)} dim-2 entities")
    for surf, residual, accepted in rows:
        print(
            f"[geo11]   surf {surf:3d} residual={residual:.6e} "
            f"ratio={residual / tol:.6e} accepted={accepted}"
        )
    return rows, tol


@pytest.mark.parametrize("name,build", FIXTURES, ids=[f[0] for f in FIXTURES])
def test_wall_classification_margin(name, build):
    """Measure the two-sided margin and hold it to the recorded state.

    A fixture with ``pin=None`` must *meet* the margin.  A pinned fixture must
    reproduce its measured ratios exactly — the defect is a review's to fix,
    but it may not drift silently in the meantime.
    """
    expected = EXPECTATIONS[name]
    rows, tol = _measure(name, build)

    accepted = [r for _, r, ok in rows if ok]
    rejected = [r for _, r, ok in rows if not ok]
    wall_ratio = max(accepted) / tol if accepted else None
    interior_ratio = min(rejected) / tol if rejected else None

    print(
        f"[geo11] {name}: {len(accepted)}/{len(rows)} accepted, "
        f"wall_ratio={wall_ratio} (ceiling {WALL_MARGIN}), "
        f"interior_ratio={interior_ratio} (floor {INTERIOR_MARGIN}), "
        f"pin={'yes' if expected['pin'] else 'no'}"
    )

    # The CAD model itself must not drift under us; every ratio below is read
    # off these entities.
    assert len(rows) == expected["n_surfaces"], (
        f"{name}: CAD model has {len(rows)} dim-2 entities, recorded "
        f"{expected['n_surfaces']} — the geometry changed, re-measure before "
        "trusting any margin below."
    )
    assert len(accepted) == expected["n_accepted"], (
        f"{name}: the wall test accepted {len(accepted)} of {len(rows)} "
        f"surfaces, recorded {expected['n_accepted']} at tol={tol:.3e}."
    )

    def _pinned(actual, recorded, label):
        assert (actual is None) == (recorded is None), (
            f"{name}: {label} ratio is {actual}, recorded {recorded}"
        )
        if recorded is not None:
            # 1e-6 relative: the ratios are exact CAD arithmetic, so this only
            # absorbs the printed precision of the recorded value.
            assert actual == pytest.approx(recorded, rel=1e-6), (
                f"{name}: {label} residual/tol = {actual:.6e}, recorded "
                f"{recorded:.6e} on 2026-08-06."
            )

    _pinned(wall_ratio, expected["wall_ratio"], "worst accepted")
    _pinned(interior_ratio, expected["interior_ratio"], "nearest rejected")

    if expected["pin"] is not None:
        # Known defect, pinned above. Do not also assert the margin it fails.
        pytest.skip(f"{name}: margin not met — {expected['pin']}")

    # No known defect: the two-sided margin must actually hold.
    assert accepted, (
        f"{name}: the wall test accepted zero of {len(rows)} surfaces at "
        f"tol={tol:.3e}; the outer_boundary group would never be declared "
        f"(this is exactly known-issues 10)."
    )
    # `GEO-10` sized two_torus_domain's tol at exactly 10x the measured 1e-7
    # padding, so wall_ratio lands on 0.1 to within double-precision noise
    # (measured 1.000000000000029e-01). The 1e-6 relative slack is that noise,
    # not a loosened bound.
    assert wall_ratio <= WALL_MARGIN * (1.0 + 1e-6), (
        f"{name}: an accepted surface sits at residual/tol = "
        f"{wall_ratio:.6e}, above the {WALL_MARGIN} ceiling — the tolerance "
        f"does not clear the bounding-box padding by 10x and a small geometry "
        f"change could empty the group."
    )
    if interior_ratio is not None:
        assert interior_ratio >= INTERIOR_MARGIN * (1.0 - 1e-6), (
            f"{name}: a rejected surface sits at residual/tol = "
            f"{interior_ratio:.6e}, below the {INTERIOR_MARGIN} floor — an "
            f"interior face is within an order of magnitude of being swept "
            f"into the outer_boundary group."
        )


def test_geo10_known_case_reproduces_the_measured_padding():
    """The `GEO-10` measurement itself, re-derived: padding is ~1e-7, not 0.

    `20260806T050143Z_GEO-10-probe.log` measured a wall residual of `1.000e-07`
    on this fixture — the gmsh OCC geometric tolerance — against an interior
    face at `2.000e-02`.  That single pair is the whole reason the wall tests
    need a two-sided margin, so it is pinned here rather than left in a log.
    """
    rows, tol = _measure("two_torus_domain (GEO-10 known case)", _build_two_torus)

    walls = sorted(r for _, r, ok in rows if ok)
    interior = sorted(r for _, r, ok in rows if not ok)

    assert len(walls) == 6, f"expected the 6 box walls, classified {len(walls)}"

    # The padding is nonzero and of order 1e-7: strictly above what a 1e-9
    # tolerance can see, strictly below the landed 1e-6.
    assert 1e-9 < walls[-1] < 1e-6, (
        f"GEO-10 known case: worst wall residual {walls[-1]:.6e} outside the "
        "measured (1e-9, 1e-6) bracket"
    )
    assert walls[-1] == pytest.approx(1.0e-7, rel=0.5), (
        f"GEO-10 known case: worst wall residual {walls[-1]:.6e} is not the "
        "measured 1.000e-07 OCC padding"
    )
    # The probe log printed 2.000e-02 at three decimals; the full value is
    # 2.000010e-02 — the interior face carries the same 1e-7 padding.
    assert interior[0] == pytest.approx(2.000010e-2, rel=1e-6), (
        f"GEO-10 known case: nearest interior residual {interior[0]:.6e} is "
        "not the measured 2.000010e-02"
    )
