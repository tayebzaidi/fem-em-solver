"""The circuit layer: terminating ports of a stored N-port S-matrix.

`PORT-14` step 1 creates this module with the one function its gate needs; the
`PORT-15` lineage extends it (ladder-network closed forms, S/Z conversions).

**What the reduction is.**  Let an N-port network with reference impedance
``z0`` have scattering matrix ``S``, and split its ports into those kept (``a``)
and those terminated in lumped impedances ``Z_k`` (``b``).  Each termination
reflects the wave leaving its port,

    b_k^inc = Γ_k b_k^out ,     Γ_k = (Z_k − z0) / (Z_k + z0)              (C1)

with ``z0`` real — the ordinary voltage-wave reflection coefficient.  Writing the
network's own relation blockwise, ``b_a = S_aa a_a + S_ab a_b`` and
``b_b = S_ba a_a + S_bb a_b`` with ``a_b = Γ b_b``, eliminating ``a_b`` gives

    S' = S_aa + S_ab Γ (I − S_bb Γ)⁻¹ S_ba                                 (C2)

the ``(N−m)×(N−m)`` scattering matrix seen at the kept ports.  ``Γ = 0`` (matched
terminations, ``Z_k = z0``) returns ``S_aa`` exactly; an open (``Z → ∞``) is
``Γ = 1`` and a short is ``Γ = −1``.

**Why it is a gate and not a convenience.**  (C2) is exact for a network whose
ports are single-mode: the terminated port's field is fully described by one
travelling-wave amplitude, so terminating it in the *model* and reducing the
50 Ω matrix *afterwards* must agree.  Solving the field problem with a capacitor
sheet at port k and comparing against (C2) applied to the 50 Ω 4×4 therefore
measures exactly how single-mode the lumped sheet is — which is `PORT-14`'s
gate and, from the other side, `PORT-15`'s.

Pure numpy on purpose: it takes an S-matrix from any source and knows nothing
about the FEM package around it.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

__all__ = ["termination_reflection_coefficient", "reduce_terminated_ports"]


def termination_reflection_coefficient(z_ohm: complex, z0_ohm: float) -> complex:
    """``Γ = (Z − z0)/(Z + z0)`` for a real reference ``z0``, (C1).

    ``numpy.inf`` (or a `float('inf')`) is accepted and means an open circuit,
    ``Γ = 1``; ``Z = 0`` is a short, ``Γ = −1``.  ``Z = −z0`` is rejected: that is
    a negative-resistance singularity, not a passive termination.
    """
    z0 = float(z0_ohm)
    if not np.isfinite(z0) or z0 <= 0.0:
        raise ValueError(f"z0_ohm must be finite and positive, got {z0_ohm!r}")
    z = complex(z_ohm)
    if np.isinf(z.real) or np.isinf(z.imag):
        return 1.0 + 0.0j
    if not (np.isfinite(z.real) and np.isfinite(z.imag)):
        raise ValueError(f"termination impedance must be finite or infinite, got {z_ohm!r}")
    denominator = z + z0
    if denominator == 0.0:
        raise ValueError(
            f"termination impedance {z_ohm!r} equals −z0 = {-z0!r}: Γ is singular there"
        )
    return (z - z0) / denominator


def reduce_terminated_ports(
    s: np.ndarray,
    z0: float,
    terminations: Mapping[int, complex] | Sequence[tuple[int, complex]],
) -> np.ndarray:
    """The kept-port S-matrix after terminating some ports, (C2).

    Parameters
    ----------
    s
        ``N×N`` scattering matrix at the real reference impedance ``z0``.
    z0
        The reference impedance ``S`` is expressed at (ohms, real and positive).
    terminations
        ``{port_index: Z_ohm}`` (or an iterable of pairs) for the ports removed
        by termination; every other port is kept, in ascending index order.  An
        empty mapping returns ``S`` unchanged.

    Returns
    -------
    ``(N−m)×(N−m)`` S-matrix at the same ``z0``, rows/columns in the kept ports'
    ascending index order.
    """
    matrix = np.asarray(s, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"s must be a square rank-2 matrix, got shape {matrix.shape}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("s contains non-finite values")
    n = matrix.shape[0]

    pairs = (
        list(terminations.items())
        if hasattr(terminations, "items")
        else [tuple(item) for item in terminations]
    )
    indices = [int(k) for k, _ in pairs]
    if len(set(indices)) != len(indices):
        raise ValueError(f"duplicate port index in terminations: {indices}")
    for k in indices:
        if not 0 <= k < n:
            raise ValueError(f"termination port index {k} out of range for a {n}-port S")
    if not pairs:
        return matrix.copy()
    if len(pairs) == n:
        raise ValueError("terminating every port leaves no network to return")

    b = np.array(sorted(indices), dtype=int)
    a = np.array([k for k in range(n) if k not in set(indices)], dtype=int)
    gamma_by_index = {int(k): termination_reflection_coefficient(z, z0) for k, z in pairs}
    gamma = np.diag(np.array([gamma_by_index[int(k)] for k in b], dtype=np.complex128))

    s_aa = matrix[np.ix_(a, a)]
    s_ab = matrix[np.ix_(a, b)]
    s_ba = matrix[np.ix_(b, a)]
    s_bb = matrix[np.ix_(b, b)]

    inner = np.eye(b.size, dtype=np.complex128) - s_bb @ gamma
    if abs(np.linalg.det(inner)) == 0.0:
        raise ValueError("(I − S_bb Γ) is singular: this termination has no bounded solution")
    return s_aa + s_ab @ gamma @ np.linalg.solve(inner, s_ba)
