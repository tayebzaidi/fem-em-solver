"""Domain sizing heuristic checks for coil+phantom geometry."""

import pytest

from fem_em_solver.io.mesh import MeshGenerator


def test_coil_phantom_domain_sizing_defaults_are_not_undersized():
    diagnostics = MeshGenerator.coil_phantom_domain_sizing_diagnostics(
        coil_major_radius=0.08,
        coil_minor_radius=0.01,
        coil_separation=0.08,
        phantom_radius=0.04,
        phantom_height=0.10,
        air_padding=0.04,
        phantom_offset_xy=(0.0, 0.0),
    )

    assert diagnostics["is_domain_undersized"] is False
    assert diagnostics["effective_air_padding_m"] == pytest.approx(0.04)
    assert diagnostics["provided_air_padding_m"] >= diagnostics["recommended_min_air_padding_m"]


def test_coil_phantom_domain_sizing_detects_small_padding_and_recommends_floor():
    diagnostics = MeshGenerator.coil_phantom_domain_sizing_diagnostics(
        coil_major_radius=0.08,
        coil_minor_radius=0.01,
        coil_separation=0.08,
        phantom_radius=0.04,
        phantom_height=0.10,
        air_padding=0.005,
        phantom_offset_xy=(0.0, 0.0),
    )

    assert diagnostics["is_domain_undersized"] is True
    assert diagnostics["effective_air_padding_m"] == pytest.approx(
        diagnostics["recommended_min_air_padding_m"]
    )
    assert diagnostics["effective_air_padding_m"] > diagnostics["provided_air_padding_m"]


def _coil_phantom_preset(offset_x: float, **overrides):
    kwargs = dict(
        coil_major_radius=0.08,
        coil_minor_radius=0.01,
        coil_separation=0.08,
        phantom_radius=0.04,
        phantom_height=0.10,
        air_padding=0.04,
    )
    kwargs.update(overrides)
    return MeshGenerator.coil_phantom_domain_sizing_diagnostics(
        phantom_offset_xy=(offset_x, 0.0), **kwargs
    )


def test_coil_phantom_domain_sizing_accounts_for_off_center_phantom_extent():
    """The off-centre phantom enters sizing through the containment identity.

    `GEO-4` step 1 (known-issues 5). This test previously asserted that an
    offset phantom strictly *grows* the box, and failed `assert 0.09 > 0.09`
    since it was written (`794d2f1`). The assertion is unattainable for any
    meshable configuration, not merely unexercised: `coil_phantom_domain`
    rejects a placement unless
    `|offset| + phantom_radius < coil_major - coil_minor` (mesh.py, the
    `radial_clearance <= 0` guard), so the phantom's outer radius is always
    strictly below the coil's `coil_major + coil_minor` and the max() in the
    sizing rule is always won by the coil. Measured here: at offset 0.03 the
    phantom reaches 0.07 m against the coil's 0.09 m.

    What the offset does change is the *clearance* to the wall, and that is
    what is gated below, together with the containment identity itself. The
    phantom-governed branch of the max is exercised separately, in
    `test_..._phantom_governed_branch_grows_the_box`.
    """
    centered = _coil_phantom_preset(0.0)
    shifted = _coil_phantom_preset(0.03)

    coil_outer = 0.08 + 0.01
    # z half-extent: max(separation/2 + minor, height/2) = max(0.05, 0.05).
    recommended_padding = 0.35 * max(coil_outer, 0.05)

    for name, diagnostics, expected_phantom_outer in (
        ("centered", centered, 0.04),
        ("shifted", shifted, 0.07),
    ):
        assert diagnostics["phantom_outer_radial_extent_m"] == pytest.approx(
            expected_phantom_outer
        ), name
        assert diagnostics["phantom_governs_radial_extent"] is False, name
        # Containment identity, clearance term explicit.
        assert diagnostics["recommended_domain_half_width_m"] == pytest.approx(
            max(coil_outer, expected_phantom_outer) + recommended_padding
        ), name
        # Clearance is never below the recommended padding while the coil governs.
        assert diagnostics["phantom_boundary_clearance_m"] == pytest.approx(
            max(coil_outer, expected_phantom_outer)
            + recommended_padding
            - expected_phantom_outer
        ), name
        assert diagnostics["phantom_boundary_clearance_m"] > recommended_padding, name

    # The coil governs both presets, so the box does not grow ...
    assert shifted["recommended_domain_half_width_m"] == pytest.approx(
        centered["recommended_domain_half_width_m"]
    )
    # ... and the whole offset is spent out of the phantom's wall clearance.
    assert centered["phantom_boundary_clearance_m"] - shifted[
        "phantom_boundary_clearance_m"
    ] == pytest.approx(0.03)


def test_coil_phantom_domain_sizing_phantom_governed_branch_grows_the_box():
    """The second term of the max does size the box once the phantom wins.

    Outside the meshable envelope by construction (see the guard cited above),
    so this exercises the arithmetic only: a 0.02 m phantom at 0.10 m offset
    reaches 0.12 m against the coil's 0.09 m.
    """
    centered = _coil_phantom_preset(0.0, phantom_radius=0.02)
    far = _coil_phantom_preset(0.10, phantom_radius=0.02)

    assert far["phantom_governs_radial_extent"] is True
    assert far["radial_extent_without_padding_m"] == pytest.approx(0.12)
    assert far["radial_extent_without_padding_m"] > centered["radial_extent_without_padding_m"]
    assert far["recommended_domain_half_width_m"] > centered["recommended_domain_half_width_m"]
    # Equality of clearance and padding is the signature of the governed branch.
    assert far["phantom_boundary_clearance_m"] == pytest.approx(
        far["recommended_min_air_padding_m"]
    )
    assert far["recommended_domain_half_width_m"] == pytest.approx(0.12 + 0.35 * 0.12)


def test_coil_phantom_domain_sizing_still_detects_zero_clearance():
    """Negative control: a zero-padding call must still be flagged undersized."""
    diagnostics = _coil_phantom_preset(0.03, air_padding=0.0)

    assert diagnostics["is_domain_undersized"] is True
    assert diagnostics["effective_air_padding_m"] == pytest.approx(0.35 * 0.09)
    assert diagnostics["provided_air_padding_m"] == 0.0


def test_coil_phantom_domain_sizing_rejects_negative_air_padding():
    with pytest.raises(ValueError, match="air_padding must be >= 0"):
        MeshGenerator.coil_phantom_domain_sizing_diagnostics(
            coil_major_radius=0.08,
            coil_minor_radius=0.01,
            coil_separation=0.08,
            phantom_radius=0.04,
            phantom_height=0.10,
            air_padding=-1.0e-3,
            phantom_offset_xy=(0.0, 0.0),
        )
