"""`PORT-15` step 1 — the circuit layer's algebra, with no FEM in it.

Three anchors, all pure numpy (smoke tier, `-n 1`, no field solve, no mesh):

(i)   the high-pass birdcage closed form ``ω_k = 1/√(C(L_r + 2 L_l sin²(πk/N)))``
      equals the eigenvalues of ``L⁻¹ C_inv`` built from the mesh matrices, for
      N ∈ {4, 16}, degeneracies included, at rtol 1e-12;
(ii)  terminating a port through `reduce_terminated_ports` (the S route,
      `PORT-14`'s function) equals the Z route
      ``z_to_s(Z_aa − Z_ab (Z_bb + Z)⁻¹ Z_ba)`` at 1e-12, for six terminations
      spanning matched / capacitive / inductive / resistive / short / open;
(iii) ``Γ = 0`` returns ``S_aa`` exactly (bitwise).

Negative control: detuning **one leg** by ×1.01 in the mesh matrices splits every
degenerate pair and moves the spectrum off the closed form — so (i) is not
satisfied by any circulant-looking matrix.

No claim here is about the FEM coil: these are identities of the lumped network
and of the S↔Z conversion, nothing more (`PORT-15` §7, step 1's scope).
"""

from __future__ import annotations

import numpy as np
import pytest

from fem_em_solver.ports.circuit import (
    birdcage_highpass_mesh_matrices,
    birdcage_highpass_mode_frequencies,
    reduce_terminated_ports,
    s_to_z,
    z_to_s,
)

# One nominal ladder, used by every ladder test.  Values are round numbers of the
# right order for a birdcage (≈100 nH legs, ≈20 nH ring segments, 100 pF ring
# capacitors); nothing here is a claim about a physical coil.
L_LEG_H = 100e-9
L_RING_H = 20e-9
C_RING_F = 100e-12

Z0_OHM = 50.0


def _eigenvalues_of_ladder(inductance: np.ndarray, inverse_capacitance: np.ndarray) -> np.ndarray:
    """``ω²`` of the ladder: eigenvalues of ``L⁻¹ C_inv``, sorted ascending, real.

    `np.linalg.eigvals` returns unsorted complex values even for a matrix whose
    spectrum is real; the imaginary parts are asserted small *relative to the
    eigenvalue scale* (ω² is O(1e16) in SI, so an absolute 1e-12 would be a
    vacuous test) before `.real` is taken.
    """
    values = np.linalg.eigvals(np.linalg.solve(inductance, inverse_capacitance))
    scale = np.max(np.abs(values))
    assert np.max(np.abs(values.imag)) <= 1e-12 * scale, (
        f"L⁻¹C_inv has complex eigenvalues: max|Im| = {np.max(np.abs(values.imag)):.6e} "
        f"vs scale {scale:.6e}"
    )
    return np.sort(values.real)


def _closed_form_omega_squared_multiset(n_legs: int, **elements) -> np.ndarray:
    """The closed-form ``ω_k²`` with their multiplicities, sorted ascending.

    ``k`` and ``N−k`` are the same frequency, so every ``0 < k < N/2`` appears
    twice; ``k = 0`` (end-ring mode) and, for even N, ``k = N/2`` appear once.
    """
    omega = birdcage_highpass_mode_frequencies(n_legs, **elements)
    multiplicity = np.full(omega.size, 2)
    multiplicity[0] = 1
    if n_legs % 2 == 0:
        multiplicity[-1] = 1
    assert multiplicity.sum() == n_legs
    return np.sort(np.repeat(omega**2, multiplicity))


@pytest.mark.parametrize("n_legs", [4, 16])
def test_ladder_closed_form_matches_the_mesh_matrix_eigenvalues(n_legs, capsys):
    """Anchor (i): closed form == eig(L⁻¹ C_inv), degeneracies included, rtol 1e-12."""
    elements = dict(l_leg_h=L_LEG_H, l_ring_h=L_RING_H, c_ring_f=C_RING_F)
    inductance, inverse_capacitance = birdcage_highpass_mesh_matrices(n_legs, **elements)

    assert np.allclose(inductance, inductance.T, rtol=0.0, atol=0.0)
    measured = _eigenvalues_of_ladder(inductance, inverse_capacitance)
    predicted = _closed_form_omega_squared_multiset(n_legs, **elements)
    assert measured.size == predicted.size == n_legs

    relative = np.abs(measured - predicted) / np.abs(predicted)
    with capsys.disabled():
        omega = birdcage_highpass_mode_frequencies(n_legs, **elements)
        print(f"\n[PORT-15 (i)] N = {n_legs}: closed-form mode frequencies (MHz), k = 0…N/2:")
        print("  " + "  ".join(f"k={k}:{w / (2 * np.pi) / 1e6:.6f}" for k, w in enumerate(omega)))
        print(f"[PORT-15 (i)] N = {n_legs}: max |eig − closed form| / closed form = {relative.max():.3e}")

    assert np.allclose(measured, predicted, rtol=1e-12, atol=0.0), (
        f"N = {n_legs}: worst relative deviation {relative.max():.6e}\n"
        f"  eig       = {measured}\n  closed form = {predicted}"
    )
    # The k = 0 end-ring mode is kept, and is 1/√(L_r C) exactly.
    assert birdcage_highpass_mode_frequencies(n_legs, **elements)[0] == pytest.approx(
        1.0 / np.sqrt(L_RING_H * C_RING_F), rel=1e-14
    )


def test_one_detuned_leg_moves_the_spectrum_off_the_closed_form(capsys):
    """Negative control: ×1.01 on one leg splits the degenerate pairs, ≥ 1e-3 relative.

    First-order perturbation theory gives a ceiling: the split of mode ``k`` is
    ``(2ε/N)·4L_l sin²(πk/N) / (2L_r + 4L_l sin²(πk/N)) ≤ 2ε/N``, i.e. 0.5 % here
    (ε = 0.01, N = 4) for the mode with the largest leg share.  The assertion is
    only that the control clears 1e-3 — three orders above anchor (i)'s rtol.
    """
    n_legs = 4
    elements = dict(l_leg_h=L_LEG_H, l_ring_h=L_RING_H, c_ring_f=C_RING_F)
    legs = np.full(n_legs, L_LEG_H)
    legs[0] *= 1.01

    inductance, inverse_capacitance = birdcage_highpass_mesh_matrices(
        n_legs, l_leg_h=legs, l_ring_h=L_RING_H, c_ring_f=C_RING_F
    )
    measured = _eigenvalues_of_ladder(inductance, inverse_capacitance)
    predicted = _closed_form_omega_squared_multiset(n_legs, **elements)

    relative = np.abs(measured - predicted) / np.abs(predicted)
    # The k = 1 pair is degenerate in the tuned ladder: entries 1 and 2 of the
    # ascending ω² multiset.  Its split is the control's sharpest reading.
    pair_split = abs(measured[2] - measured[1]) / abs(predicted[1])

    with capsys.disabled():
        print(f"\n[PORT-15 control] N = 4, one leg ×1.01 (ε = 0.01, ceiling 2ε/N = 5.000e-03):")
        print(f"  per-mode |Δω²|/ω² = {np.array2string(relative, precision=4)}")
        print(f"  worst mode: {relative.max():.4e} in ω², {np.sqrt(1 + relative.max()) - 1:.4e} in ω")
        print(f"  k = 1 degenerate pair split: {pair_split:.4e} in ω²")

    assert relative.max() >= 1e-3, (
        f"the detuned ladder still matches the closed form to {relative.max():.3e} — "
        "anchor (i) would be trivially satisfied"
    )
    assert relative.max() <= 2.0 * 0.01 / n_legs * 1.05, (
        f"split {relative.max():.3e} exceeds the first-order ceiling 2ε/N = "
        f"{2.0 * 0.01 / n_legs:.3e}: the perturbation model, not just the matrix, is wrong"
    )
    assert pair_split >= 1e-3, f"the degenerate k = 1 pair did not split: {pair_split:.3e}"


def _random_passive_reciprocal_s(n: int, seed: int) -> np.ndarray:
    """A symmetric (reciprocal) strictly passive S: ``S = U diag(σ) Uᵀ``, σ < 1.

    Takagi form: for unitary ``U``, ``U D Uᵀ`` is symmetric and has singular
    values ``D``, so ``σ < 1`` makes it strictly passive (‖S‖₂ < 1) — which is
    also what makes ``I − S`` invertible for `s_to_z`.
    """
    rng = np.random.default_rng(seed)
    a = rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))
    q, r = np.linalg.qr(a)
    q = q * (np.diag(r) / np.abs(np.diag(r)))  # fix the QR phase convention
    sigma = np.linspace(0.9, 0.1, n)
    return q @ np.diag(sigma) @ q.T


@pytest.mark.parametrize(
    "z_termination",
    [50.0, -159.15j, +62.83j, 200.0, 0.0, 1e9],
    ids=["matched-50", "C-100pF-at-10MHz", "L-1uH-at-10MHz", "R-200", "short", "open-1e9"],
)
def test_s_route_termination_equals_the_z_route(z_termination, capsys):
    """Anchor (ii): `reduce_terminated_ports` == the Z-matrix reduction, 1e-12."""
    s = _random_passive_reciprocal_s(4, seed=20260905)
    assert np.allclose(s, s.T, rtol=0.0, atol=1e-15), "the fixture S must be reciprocal"
    assert np.linalg.norm(s, 2) < 1.0, "the fixture S must be strictly passive"

    z = s_to_z(s, Z0_OHM)
    assert np.allclose(z_to_s(z, Z0_OHM), s, rtol=0.0, atol=1e-13), "s_to_z / z_to_s round trip"

    s_route = reduce_terminated_ports(s, Z0_OHM, {3: z_termination})

    keep = np.arange(3)
    z_aa = z[np.ix_(keep, keep)]
    z_ab = z[np.ix_(keep, [3])]
    z_ba = z[np.ix_([3], keep)]
    z_bb = z[np.ix_([3], [3])]
    z_reduced = z_aa - z_ab @ np.linalg.solve(z_bb + complex(z_termination) * np.eye(1), z_ba)
    z_route = z_to_s(z_reduced, Z0_OHM)

    difference = np.max(np.abs(s_route - z_route))
    with capsys.disabled():
        print(
            f"\n[PORT-15 (ii)] Z = {z_termination!r} Ω: max |S'_S-route − S'_Z-route| = "
            f"{difference:.3e}  (‖S'‖_F = {np.linalg.norm(s_route):.6f})"
        )

    assert np.allclose(s_route, z_route, rtol=1e-12, atol=1e-12), (
        f"Z = {z_termination!r}: routes differ by {difference:.6e}\n"
        f"  S route = {s_route}\n  Z route = {z_route}"
    )


def test_matched_termination_returns_s_aa_exactly(capsys):
    """Anchor (iii): ``Γ = 0`` (Z = z0) returns ``S_aa`` bitwise, one and two ports."""
    s = _random_passive_reciprocal_s(4, seed=20260905)

    one = reduce_terminated_ports(s, Z0_OHM, {3: Z0_OHM})
    two = reduce_terminated_ports(s, Z0_OHM, {2: Z0_OHM, 3: Z0_OHM})

    with capsys.disabled():
        print(
            f"\n[PORT-15 (iii)] Γ = 0: max|S' − S_aa| = "
            f"{np.max(np.abs(one - s[:3, :3])):.3e} (1 port), "
            f"{np.max(np.abs(two - s[:2, :2])):.3e} (2 ports)"
        )

    assert np.array_equal(one, s[:3, :3])
    assert np.array_equal(two, s[:2, :2])
