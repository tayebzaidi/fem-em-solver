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

`PORT-15` step 1 adds the rest of the circuit layer's algebra: the S ↔ Z
conversions at a real reference impedance (`s_to_z` / `z_to_s`), and the
high-pass birdcage ladder network — its mesh matrices
(`birdcage_highpass_mesh_matrices`) and the closed-form mode spectrum
(`birdcage_highpass_mode_frequencies`) that diagonalising them reproduces.
Still no FEM: nothing here knows where an inductance came from.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

__all__ = [
    "termination_reflection_coefficient",
    "reduce_terminated_ports",
    "s_to_z",
    "z_to_s",
    "birdcage_highpass_mesh_matrices",
    "birdcage_highpass_mode_frequencies",
]


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


# ---------------------------------------------------------------------------
# S ↔ Z at a real reference impedance
# ---------------------------------------------------------------------------


def _check_real_z0(z0_ohm: float) -> float:
    z0 = float(z0_ohm)
    if not np.isfinite(z0) or z0 <= 0.0:
        raise ValueError(f"z0 must be finite and positive, got {z0_ohm!r}")
    return z0


def s_to_z(s: np.ndarray, z0: float) -> np.ndarray:
    """``Z = z0 (I + S)(I − S)⁻¹`` — the impedance matrix of an N-port.

    Valid for a real reference impedance ``z0``; ``I − S`` must be nonsingular,
    which it is whenever ``‖S‖₂ < 1`` (a strictly lossy passive network).
    """
    z0 = _check_real_z0(z0)
    matrix = np.asarray(s, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"s must be a square rank-2 matrix, got shape {matrix.shape}")
    identity = np.eye(matrix.shape[0], dtype=np.complex128)
    lhs = identity - matrix
    if abs(np.linalg.det(lhs)) == 0.0:
        raise ValueError("(I − S) is singular: this S has no finite Z representation")
    # X (I − S) = z0 (I + S)  ⇔  (I − S)ᵀ Xᵀ = z0 (I + S)ᵀ.
    return np.linalg.solve(lhs.T, z0 * (identity + matrix).T).T


def z_to_s(z: np.ndarray, z0: float) -> np.ndarray:
    """``S = (Z − z0 I)(Z + z0 I)⁻¹`` — the inverse of `s_to_z`.

    ``Z + z0 I`` is nonsingular for any ``Z`` with a positive semi-definite
    Hermitian part (any passive network) and a real positive ``z0``.
    """
    z0 = _check_real_z0(z0)
    matrix = np.asarray(z, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"z must be a square rank-2 matrix, got shape {matrix.shape}")
    identity = np.eye(matrix.shape[0], dtype=np.complex128)
    rhs = matrix + z0 * identity
    if abs(np.linalg.det(rhs)) == 0.0:
        raise ValueError("(Z + z0 I) is singular: this Z has no S representation at that z0")
    # X (Z + z0 I) = (Z − z0 I)  ⇔  (Z + z0 I)ᵀ Xᵀ = (Z − z0 I)ᵀ.
    return np.linalg.solve(rhs.T, (matrix - z0 * identity).T).T


# ---------------------------------------------------------------------------
# The high-pass birdcage ladder network
# ---------------------------------------------------------------------------


def _leg_and_ring_arrays(
    n_legs: int,
    l_leg_h: float | Sequence[float] | np.ndarray,
    l_ring_h: float | Sequence[float] | np.ndarray,
    c_ring_f: float | Sequence[float] | np.ndarray,
) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
    n = int(n_legs)
    if n < 3:
        raise ValueError(
            f"n_legs must be at least 3 (at N = 2 a window's two neighbours coincide), got {n_legs!r}"
        )

    def _broadcast(value, name: str) -> np.ndarray:
        array = np.atleast_1d(np.asarray(value, dtype=float))
        if array.size == 1:
            array = np.full(n, float(array.reshape(())[()]))
        if array.shape != (n,):
            raise ValueError(f"{name} must be a scalar or a length-{n} sequence, got shape {array.shape}")
        if not np.all(np.isfinite(array)) or np.any(array <= 0.0):
            raise ValueError(f"{name} must be finite and strictly positive, got {value!r}")
        return array

    return (
        n,
        _broadcast(l_leg_h, "l_leg_h"),
        _broadcast(l_ring_h, "l_ring_h"),
        _broadcast(c_ring_f, "c_ring_f"),
    )


def birdcage_highpass_mesh_matrices(
    n_legs: int,
    l_leg_h: float | Sequence[float] | np.ndarray,
    l_ring_h: float | Sequence[float] | np.ndarray,
    c_ring_f: float | Sequence[float] | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Mesh inductance ``L`` and inverse-capacitance ``C_inv`` of the ladder, (C3).

    The high-pass birdcage is an ``N``-window ladder closed on itself.  Window
    ``m`` (``m = 0 … N−1``) is bounded by leg ``m`` on one side and leg
    ``m+1 (mod N)`` on the other, and by one end-ring segment top and bottom.
    Each **ring segment** carries an inductance ``l_ring_h`` and a series
    capacitance ``c_ring_f`` (that series capacitor in the *ring* is what makes
    the birdcage high-pass); each **leg** carries ``l_leg_h`` and no capacitor.
    Mutual inductance between elements is neglected — the standard lumped
    ladder idealisation.

    With mesh (loop) currents ``I_m``, leg ``m`` carries ``I_m − I_{m−1}`` and
    the two ring segments of window ``m`` carry ``I_m``.  KVL round window ``m``,
    at angular frequency ``ω``, is

        jω[ 2L_r I_m + L_l(I_m − I_{m−1}) + L_l(I_m − I_{m+1}) ]
            + (2/(jωC)) I_m = 0                                            (C3)

    (the factors 2 are the window's *two* ring segments, in series: inductances
    add, and two ``C``'s in series give ``C/2``, i.e. reactance ``2/(jωC)``).
    In matrix form ``(−ω² L + C_inv) I = 0`` with

        L[m,m]   = 2 L_r + L_l[m] + L_l[m+1]
        L[m,m±1] = − L_l[shared leg]          C_inv[m,m] = 2 / C[m]        (C4)

    so the resonances are the generalised eigenvalues ``ω² = eig(L⁻¹ C_inv)``.
    Uniform ``l_leg_h`` makes ``L`` circulant and (C4) diagonalises in closed
    form — see `birdcage_highpass_mode_frequencies`.  Per-element sequences are
    accepted precisely so that a *detuned* ladder (one leg off nominal) can be
    built and its spectrum compared against the circulant closed form.

    Parameters
    ----------
    n_legs
        Number of legs ``N`` = number of windows (``N ≥ 3``).
    l_leg_h, l_ring_h, c_ring_f
        Per-leg inductance (H), per-ring-**segment** inductance (H) and
        per-ring-**segment** capacitance (F); scalar or length-``N``.
        ``l_ring_h[m]`` / ``c_ring_f[m]`` are window ``m``'s segment values.

    Returns
    -------
    ``(L, C_inv)``, both real ``N×N`` and symmetric, in SI units (H and 1/F).
    """
    n, l_leg, l_ring, c_ring = _leg_and_ring_arrays(n_legs, l_leg_h, l_ring_h, c_ring_f)

    inductance = np.zeros((n, n), dtype=float)
    for m in range(n):
        left = m  # leg m, shared with window m−1
        right = (m + 1) % n  # leg m+1, shared with window m+1
        inductance[m, m] = 2.0 * l_ring[m] + l_leg[left] + l_leg[right]
        inductance[m, (m - 1) % n] -= l_leg[left]
        inductance[m, (m + 1) % n] -= l_leg[right]

    inverse_capacitance = np.diag(2.0 / c_ring)
    return inductance, inverse_capacitance


def birdcage_highpass_mode_frequencies(
    n_legs: int,
    l_leg_h: float,
    l_ring_h: float,
    c_ring_f: float,
) -> np.ndarray:
    """Closed-form resonant angular frequencies of the high-pass ladder, (C5).

    For uniform elements the mesh matrix (C4) is circulant, so its eigenvectors
    are the discrete Fourier modes ``I_m^{(k)} = e^{j2πkm/N}``.  Substituting
    into (C3),

        −ω²[ 2L_r + L_l(2 − e^{−j2πk/N} − e^{+j2πk/N}) ] + 2/C = 0
        ⇒ ω²[ 2L_r + 4 L_l sin²(πk/N) ] = 2/C

    since ``2 − 2cos(2πk/N) = 4 sin²(πk/N)``; dividing by 2,

        ω_k = 1 / √( C ( L_r + 2 L_l sin²(πk/N) ) ) ,   k = 0 … ⌊N/2⌋      (C5)

    ``k`` and ``N−k`` give the same frequency, so every ``0 < k < N/2`` is a
    degenerate pair (the two linear combinations are the sine/cosine standing
    waves; the ``k = 1`` pair is the homogeneous-``B₁`` mode a birdcage is
    driven in quadrature on).  ``k = 0`` is the real end-ring mode
    ``ω_0 = 1/√(L_r C)`` — all mesh currents equal, no leg current — and is kept
    here rather than discarded.  ``k = N/2`` (``N`` even) is the single
    highest, non-degenerate mode.  Note the **high-pass** ordering: ``ω_k``
    *decreases* with ``k``, so the end-ring mode is the highest frequency and
    the useful ``k = 1`` mode sits just below it.

    This reproduces the ladder-network spectrum of the birdcage literature
    (Hayes et al. 1985; Leifer 1997) — the derivation above is the module's
    own; no number from those papers enters this file.

    Parameters
    ----------
    n_legs
        Number of legs ``N ≥ 3``.
    l_leg_h, l_ring_h, c_ring_f
        Scalars: leg inductance (H), ring-**segment** inductance (H) and
        ring-**segment** capacitance (F).  Same convention as
        `birdcage_highpass_mesh_matrices`, whose ``L⁻¹ C_inv`` eigenvalues are
        the squares of what this returns.

    Returns
    -------
    ``ω_k`` in rad/s for ``k = 0 … ⌊N/2⌋``, one entry per *distinct* mode
    frequency (index = ``k``), i.e. length ``N//2 + 1``.
    """
    n, l_leg, l_ring, c_ring = _leg_and_ring_arrays(n_legs, l_leg_h, l_ring_h, c_ring_f)
    for array, name in ((l_leg, "l_leg_h"), (l_ring, "l_ring_h"), (c_ring, "c_ring_f")):
        if not np.allclose(array, array[0], rtol=0.0, atol=0.0):
            raise ValueError(
                f"{name} must be uniform for the closed form; a detuned ladder has no circulant "
                "spectrum — build it with birdcage_highpass_mesh_matrices and diagonalise"
            )
    k = np.arange(n // 2 + 1)
    effective_l = l_ring[0] + 2.0 * l_leg[0] * np.sin(np.pi * k / n) ** 2
    return 1.0 / np.sqrt(c_ring[0] * effective_l)
