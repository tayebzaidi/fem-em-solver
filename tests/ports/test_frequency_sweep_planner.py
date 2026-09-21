"""Tests for frequency sweep planning utility (chunk D4)."""

from __future__ import annotations

import pytest

from fem_em_solver.ports import FrequencySweepPlan, plan_frequency_sweep


def test_plan_frequency_sweep_coarse_only_is_deterministic_and_inclusive():
    plan = plan_frequency_sweep(
        start_hz=120.0e6,
        stop_hz=130.0e6,
        coarse_step_hz=5.0e6,
        z0_ohm=50.0,
        port_order=("P1", "P2", "P3", "P4"),
    )

    assert isinstance(plan, FrequencySweepPlan)
    assert plan.step_policy == "coarse-only"
    assert plan.z0_ohm == pytest.approx(50.0)
    assert plan.port_order == ("P1", "P2", "P3", "P4")
    assert plan.frequencies_hz == pytest.approx((120.0e6, 125.0e6, 130.0e6))


def test_plan_frequency_sweep_coarse_plus_refined_merges_and_sorts_frequencies():
    plan = plan_frequency_sweep(
        start_hz=120.0e6,
        stop_hz=130.0e6,
        coarse_step_hz=5.0e6,
        refine_centers_hz=(127.0e6,),
        refine_half_span_hz=2.0e6,
        refined_step_hz=1.0e6,
        z0_ohm=75.0,
        port_order=("P1", "P2"),
    )

    assert plan.step_policy == "coarse+refined"
    assert plan.z0_ohm == pytest.approx(75.0)
    assert plan.port_order == ("P1", "P2")
    assert plan.frequencies_hz == pytest.approx(
        (
            120.0e6,
            125.0e6,
            126.0e6,
            127.0e6,
            128.0e6,
            129.0e6,
            130.0e6,
        )
    )


def test_plan_frequency_sweep_rejects_invalid_refined_config():
    with pytest.raises(ValueError, match="refined_step_hz must be positive"):
        plan_frequency_sweep(
            start_hz=120.0e6,
            stop_hz=130.0e6,
            coarse_step_hz=5.0e6,
            refine_centers_hz=(127.0e6,),
            refine_half_span_hz=1.0e6,
            refined_step_hz=0.0,
        )

    with pytest.raises(ValueError, match="refine_half_span_hz must be positive"):
        plan_frequency_sweep(
            start_hz=120.0e6,
            stop_hz=130.0e6,
            coarse_step_hz=5.0e6,
            refine_centers_hz=(127.0e6,),
            refine_half_span_hz=-1.0,
            refined_step_hz=1.0e6,
        )


# --- OPS-56: endpoint inclusion is decided relative to the step, not the carrier.
# Expected grids computed by hand: n = floor(span/step); the endpoint is appended
# iff span - n*step is not ~0 relative to the step. The pre-change module
# (default np.isclose, rtol 1e-5 of the carrier) returned 127.7000/127.7005 MHz,
# 127.7000/127.7010 MHz and a single 64 MHz point for the three cases below.
REPRODUCED_CASES = (
    ((127.7000e6, 127.7009e6, 500.0), (127.7000e6, 127.7005e6, 127.7009e6)),
    ((127.7000e6, 127.7012e6, 1.0e3), (127.7000e6, 127.7010e6, 127.7012e6)),
    ((64.0000e6, 64.0005e6, 1.0e3), (64.0000e6, 64.0005e6)),
)


@pytest.mark.parametrize("args, expected", REPRODUCED_CASES)
def test_uniform_grid_keeps_endpoint_at_khz_steps_on_mhz_carriers(args, expected):
    start, stop, step = args
    plan = plan_frequency_sweep(start_hz=start, stop_hz=stop, coarse_step_hz=step)
    grid = plan.frequencies_hz
    assert len(grid) == len(expected)
    # Absolute tolerance far below the step (1e-6 Hz), never carrier-relative.
    assert grid == pytest.approx(expected, rel=0.0, abs=1e-6)
    assert grid[-1] == stop  # endpoint present, bitwise


def test_uniform_grid_nondivisible_span_appends_stop():
    plan = plan_frequency_sweep(start_hz=0.0, stop_hz=10.0, coarse_step_hz=3.0)
    assert plan.frequencies_hz == (0.0, 3.0, 6.0, 9.0, 10.0)


def test_uniform_grid_float_noise_on_grid_endpoint_is_bitwise_stop():
    # 0.3 - 0.1 = 0.19999999999999998 and /0.1 = 1.9999999999999998: still 3 points.
    plan = plan_frequency_sweep(start_hz=0.1, stop_hz=0.3, coarse_step_hz=0.1)
    assert len(plan.frequencies_hz) == 3
    assert plan.frequencies_hz[-1] == 0.3  # bitwise, not approx
    assert plan.frequencies_hz == pytest.approx((0.1, 0.2, 0.3), rel=0.0, abs=1e-15)


def test_uniform_grid_on_grid_endpoint_bitwise_at_mhz():
    plan = plan_frequency_sweep(start_hz=63.0e6, stop_hz=65.0e6, coarse_step_hz=0.1e6)
    assert len(plan.frequencies_hz) == 21
    assert plan.frequencies_hz[-1] == 65.0e6


def test_coarse_refined_near_duplicate_merges_to_one_point():
    delta = 6.0e-8  # a few ulp at 125 MHz; << 1e-9 * refined step (1e-3 Hz)
    center = 127.0e6 + delta
    assert center - 2.0e6 != 125.0e6  # precondition: not bitwise equal
    plan = plan_frequency_sweep(
        start_hz=120.0e6,
        stop_hz=130.0e6,
        coarse_step_hz=5.0e6,
        refine_centers_hz=(center,),
        refine_half_span_hz=2.0e6,
        refined_step_hz=1.0e6,
    )
    grid = plan.frequencies_hz
    # np.unique would keep both 125e6 and 125e6+delta (8 points).
    assert len(grid) == 7
    assert grid[1] == 125.0e6  # first of the merged pair is kept
    assert grid == pytest.approx(
        (120.0e6, 125.0e6, 126.0e6, 127.0e6, 128.0e6, 129.0e6, 130.0e6), rel=0.0, abs=1e-6
    )


@pytest.mark.parametrize("field", ["start_hz", "stop_hz", "coarse_step_hz"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_uniform_grid_rejects_non_finite_inputs(field, bad):
    kwargs = {"start_hz": 120.0e6, "stop_hz": 130.0e6, "coarse_step_hz": 5.0e6}
    kwargs[field] = bad
    with pytest.raises(ValueError, match="must be finite"):
        plan_frequency_sweep(**kwargs)
