"""`OPS-57` — S ↔ Z conversions let the factorisation report singularity, and
there is one impedance-to-S implementation.

Pure numpy, smoke tier.  Three anchors (the §7 row's done-when):

(i)   round trip ``z_to_s(s_to_z(S, z0), z0) == S`` to ≤ 1e-12 on a seeded
      16-port passive S at ``z0 = 1e-21 Ω`` — scaled so ``det(Z + z0 I)``
      underflows to exactly 0.0 while the matrix is well conditioned.
      **Pre-change control, asserted:** the removed test
      ``abs(np.linalg.det(Z + z0 I)) == 0.0`` is evaluated on the same matrix
      and is True — i.e. the pre-`OPS-57` ``z_to_s`` (sha 1da2fe5) raised
      ``ValueError`` on a matrix whose condition number is printed here.
(ii)  an *exactly* singular matrix still raises ``ValueError`` with the
      unchanged message at all three sites (``reduce_terminated_ports``,
      ``s_to_z``, ``z_to_s``); non-finite input is refused by both conversions.
(iii) ``sparameters_from_impedance`` and ``z_to_s`` agree to ≤ 1e-14 on a
      seeded random passive Z (they are now one implementation; the
      independent closed-form anchor for the S route is
      ``tests/unit/test_port20_current_route_s.py``).
"""

from __future__ import annotations

import numpy as np
import pytest

from fem_em_solver.ports.circuit import reduce_terminated_ports, s_to_z, z_to_s
from fem_em_solver.ports.sparameters import sparameters_from_impedance

ROUND_TRIP_TOL = 1e-12
AGREEMENT_TOL = 1e-14


def _passive_s(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
    s = a + a.T  # reciprocal
    return 0.9 * s / np.linalg.norm(s, 2)  # ‖S‖₂ = 0.9 < 1: strictly passive


def _passive_z(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    a = rng.standard_normal((n, n))
    r = a @ a.T + n * np.eye(n)
    b = rng.standard_normal((n, n))
    x = b + b.T
    return 10.0 * (r + 1j * x)


def test_round_trip_survives_an_underflowing_determinant(capsys):
    z0 = 1e-21
    s = _passive_s(16, seed=57)
    z = s_to_z(s, z0)
    rhs = z + z0 * np.eye(16)
    det = np.linalg.det(rhs)
    cond = np.linalg.cond(rhs)
    # Pre-change control: the removed determinant guard fires on this matrix.
    assert abs(det) == 0.0
    assert cond < 1e3
    back = z_to_s(z, z0)
    err = np.max(np.abs(back - s))
    with capsys.disabled():
        print(
            f"\n[OPS-57] 16-port, z0={z0:g}: |det(Z+z0 I)|={abs(det):g} "
            f"cond={cond:.6e} max|z_to_s(s_to_z(S))-S|={err:.3e} (tol {ROUND_TRIP_TOL:g})"
        )
    assert err <= ROUND_TRIP_TOL


def test_exactly_singular_matrices_raise_the_same_message():
    with pytest.raises(ValueError, match=r"\(I − S\) is singular: this S has no finite Z"):
        s_to_z(np.eye(3), 50.0)
    with pytest.raises(ValueError, match=r"\(Z \+ z0 I\) is singular: this Z has no S"):
        z_to_s(-50.0 * np.eye(3), 50.0)
    with pytest.raises(ValueError, match=r"is singular: this Z has no S"):
        sparameters_from_impedance(-50.0 * np.eye(3), z0_ohm=50.0)
    # S_bb = −1 with a short (Γ = −1): I − S_bb Γ = 0 exactly.
    s = np.array([[0.1, 0.2], [0.2, -1.0]], dtype=np.complex128)
    with pytest.raises(ValueError, match=r"\(I − S_bb Γ\) is singular: this termination"):
        reduce_terminated_ports(s, 50.0, {1: 0.0})


@pytest.mark.parametrize("func", [s_to_z, z_to_s])
@pytest.mark.parametrize("bad", [np.nan, np.inf, complex(0.0, np.inf)])
def test_conversions_refuse_non_finite_input(func, bad):
    m = 0.1 * np.eye(2, dtype=np.complex128)
    m[0, 1] = bad
    with pytest.raises(ValueError, match="non-finite"):
        func(m, 50.0)


def test_sparameters_from_impedance_is_z_to_s(capsys):
    z = _passive_z(6, seed=2057)
    a = sparameters_from_impedance(z, z0_ohm=50.0)
    b = z_to_s(z, 50.0)
    diff = np.max(np.abs(a - b))
    with capsys.disabled():
        print(f"\n[OPS-57] max|sparameters_from_impedance - z_to_s| = {diff:.3e}")
    assert diff <= AGREEMENT_TOL
