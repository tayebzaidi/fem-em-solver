"""OPS-40: ``evaluate_vector_field_parallel`` refuses a rank-dependent point list.

The routine is collective — rank 0 sizes its output buffer by the caller's
``points`` and scatters each rank's hits into it by index — so a caller that
hands each rank its own *local* points corrupts the gather at ``-n 2`` and
passes silently at ``-n 1`` (EX-52, ``20260907T033551Z_EX-52.log:400``).

The guard must raise on **every** rank: a rank-0-only raise ahead of the
gather is a hang, not a failure.
"""

import numpy as np
import pytest
from mpi4py import MPI

from dolfinx import fem, mesh as dmesh

from fem_em_solver.post.evaluation import evaluate_vector_field_parallel


def _linear_vector_function(comm):
    """A P1 vector field with the exact closed form ``(x, 2y, 3z)``."""
    msh = dmesh.create_unit_cube(comm, 6, 6, 6)
    V = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    f = fem.Function(V)
    f.interpolate(lambda x: np.vstack((x[0], 2.0 * x[1], 3.0 * x[2])))
    return f


def _rank_dependent_points(rank):
    """``n = 3 + rank`` points, all inside the unit cube."""
    n = 3 + rank
    t = np.linspace(0.2, 0.8, n)
    return np.column_stack((t, t, t))


def test_rank_dependent_point_list_raises_on_every_rank():
    comm = MPI.COMM_WORLD
    f = _linear_vector_function(comm)
    points = _rank_dependent_points(comm.rank)

    raised = False
    message = ""
    try:
        evaluate_vector_field_parallel(f, points)
    except ValueError as exc:
        raised = True
        message = str(exc)

    flags = comm.allgather(raised)
    messages = comm.allgather(message)

    if comm.size == 1:
        # Negative control: a single rank cannot disagree with itself, so the
        # same construction must NOT raise.
        assert flags == [False], f"guard fired at -n 1: {messages}"
        return

    # Every rank raises, or the next collective hangs.
    assert flags == [True] * comm.size, f"guard raised on only some ranks: {flags}"

    # The message names each rank's count and states the rule.
    for msg in messages:
        for rank in range(comm.size):
            assert f"rank {rank}: {3 + rank}" in msg, msg
        assert "collective" in msg
        assert "allgather your points first" in msg


def test_identical_point_list_path_unchanged():
    """The valid path is untouched: values match the closed form exactly."""
    comm = MPI.COMM_WORLD
    f = _linear_vector_function(comm)

    t = np.linspace(0.2, 0.8, 5)
    points = np.column_stack((t, t, t))

    values, valid = evaluate_vector_field_parallel(f, points)

    assert bool(np.all(valid)), f"points not located: {valid}"
    expected = np.column_stack((t, 2.0 * t, 3.0 * t))
    err = float(np.max(np.abs(np.asarray(values).real - expected)))
    assert err < 1e-12, f"max deviation from (x, 2y, 3z) = {err:.3e}"

    # Identical across ranks (the collective contract).
    gathered = comm.allgather(np.asarray(values).tolist())
    for g in gathered[1:]:
        assert g == gathered[0]


def _shifted_points(rank):
    """OPS-55: equal count on every rank, coordinates shifted by 0.01 * rank."""
    t = np.linspace(0.15, 0.85, 8)
    return np.column_stack((t, t, t)) + 0.01 * rank


def test_equal_count_different_coordinates_raises_on_every_rank():
    """OPS-55: the count guard cannot see this; the digest guard must."""
    comm = MPI.COMM_WORLD
    f = _linear_vector_function(comm)
    points = _shifted_points(comm.rank)

    raised = False
    message = ""
    try:
        evaluate_vector_field_parallel(f, points)
    except ValueError as exc:
        raised = True
        message = str(exc)

    flags = comm.allgather(raised)
    messages = comm.allgather(message)
    if comm.rank == 0:
        print(f"OPS55 flags={flags} message[0]={messages[0]!r}")

    if comm.size == 1:
        # Negative control: rank 0's shift is zero, a single rank cannot
        # disagree with itself — must NOT raise.
        assert flags == [False], f"guard fired at -n 1: {messages}"
        return

    assert flags == [True] * comm.size, f"guard raised on only some ranks: {flags}"
    for msg in messages:
        assert "rank 0: first differing row -1, max abs deviation 0.000e+00" in msg, msg
        for rank in range(1, comm.size):
            # Every row differs (first row 0) by exactly 0.01 * rank.
            assert (
                f"rank {rank}: first differing row 0, max abs deviation "
                f"{0.01 * rank:.3e}" in msg
            ), msg
        assert "collective" in msg
        assert "broadcast the points from rank 0" in msg


def test_prechange_control_was_silent():
    """OPS-55 pre-change control: the function at the pinned pre-change sha
    (``git show 14a0d71:src/fem_em_solver/post/evaluation.py`` into
    ``/workspace/logs/``, path in ``OPS55_PRECHANGE_MODULE``) returns an
    all-valid mask on the shifted input and values off the closed form
    ``(x, 2y, 3z)`` at rank 0's points by exactly the shift: a row located by
    rank r reads ``F(p + 0.01 r) = F(p) + 0.01 r (1, 2, 3)``, so the per-row
    max-abs deviation is ``0.03 * r`` for the (last-gathered) claiming rank.
    """
    import importlib.util
    import os

    path = os.environ.get("OPS55_PRECHANGE_MODULE")
    if not path:
        pytest.skip("OPS55_PRECHANGE_MODULE not set (pre-change control window only)")
    spec = importlib.util.spec_from_file_location("ops55_prechange", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    comm = MPI.COMM_WORLD
    f = _linear_vector_function(comm)
    points = _shifted_points(comm.rank)
    values, valid = mod.evaluate_vector_field_parallel(f, points)

    ref = _shifted_points(0)
    expected = np.column_stack((ref[:, 0], 2.0 * ref[:, 1], 3.0 * ref[:, 2]))
    dev = np.max(np.abs(np.asarray(values).real - expected), axis=1)
    if comm.rank == 0:
        print(f"OPS55 prechange n={comm.size} valid_all={bool(np.all(valid))} "
              f"row_dev={np.array2string(dev, precision=6)}")

    assert bool(np.all(valid)), "pre-change mask not all-valid"
    allowed = [0.03 * r for r in range(comm.size)]
    for d in dev:
        assert min(abs(d - a) for a in allowed) < 1e-12, (d, allowed)
    if comm.size == 1:
        assert float(np.max(dev)) < 1e-12
    else:
        # The defect was silent AND wrong: some row reports another rank's
        # field, off by the predicted 0.03 * (size - 1) or a smaller multiple.
        assert float(np.max(dev)) > 0.03 - 1e-12, dev


@pytest.mark.parametrize("bad", [np.zeros((4, 2)), np.zeros(4)])
def test_shape_validation_precedes_nothing_it_should(bad):
    """The pre-existing shape check still fires (guard did not displace it)."""
    comm = MPI.COMM_WORLD
    f = _linear_vector_function(comm)
    with pytest.raises(ValueError, match=r"points must have shape"):
        evaluate_vector_field_parallel(f, bad)
