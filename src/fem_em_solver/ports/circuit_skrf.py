"""The circuit layer through `scikit-rf` — `PORT-23` step 1.

The field solve produces the 50 Ω N-port under MPI; this module hands that
matrix to a vetted circuit engine (`scikit-rf`, pinned in the image by
`OPS-60`) and lets it terminate the ports through a connection-list netlist —
the same object an HFSS Circuit user builds.  The raw (C2) reduction in
`ports/circuit.py` (``reduce_terminated_ports``) stays as the *control*: the
two must agree to machine precision, which is `PORT-23` step 1's gate.

**The netlist.**  For an N-port ``network`` and a map ``{port: Z}`` of
terminations, every *kept* port ``k`` is wired to a `Circuit.Port` at the
network's reference impedance, and every *terminated* port to a two-port
`Circuit.SeriesImpedance` of value ``Z`` whose far side is a `Circuit.Ground`
(a short) — i.e. ``Z`` from the port terminal to ground, the lumped element
the (C1) reflection coefficient describes.  No reflection coefficient is
computed here: `scikit-rf` does the element → S conversion and the
interconnection itself, so the comparison with (C2) checks both.

**Port order** is the silent failure a netlist invites (the `PORT-20` class of
bug).  ``port_map`` (logical port → network port) is explicit and defaults to
the identity; the kept ports are wired to `Circuit.Port` objects in ascending
logical order, and the returned matrix is in that order — the same convention
as ``reduce_terminated_ports``.

**Wave convention.**  For a real reference impedance, `scikit-rf`'s ``'power'``
(Kurokawa), ``'pseudo'`` and ``'traveling'`` definitions coincide with the
``a = (V + z₀I)/(2√z₀)`` power waves ``ports/superposition.py`` documents; the
gate module checks that rather than assuming it.

Serial on purpose: this runs on one process on a gathered matrix; nothing here
touches DolfinX or MPI.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

__all__ = [
    "network_from_records",
    "terminate",
    "input_impedance",
]


def _skrf():
    try:
        import skrf  # noqa: F401
        from skrf.circuit import Circuit
    except ImportError as exc:  # pragma: no cover - the image pins it (OPS-60)
        raise ImportError(
            "scikit-rf is required for ports.circuit_skrf (pinned in docker/Dockerfile, OPS-60)"
        ) from exc
    return skrf, Circuit


def network_from_records(s: np.ndarray, z0: float, frequency_hz: float | Sequence[float],
                         name: str = "fem_nport"):
    """An `skrf.Network` from a stored ``N×N`` (or ``F×N×N``) S-matrix.

    ``z0`` is the real reference impedance the matrix is expressed at (the field
    layer's 50 Ω); ``frequency_hz`` a scalar for one matrix or a length-``F``
    sequence for a stack.  The Network is built with ``s_def='power'`` — for a
    real ``z0`` the definitions coincide, which `PORT-23` gate (d) asserts.
    """
    skrf, _ = _skrf()
    z0 = float(z0)
    if not np.isfinite(z0) or z0 <= 0.0:
        raise ValueError(f"z0 must be finite, real and positive, got {z0!r}")
    matrix = np.asarray(s, dtype=np.complex128)
    if matrix.ndim == 2:
        matrix = matrix[np.newaxis, :, :]
    if matrix.ndim != 3 or matrix.shape[1] != matrix.shape[2]:
        raise ValueError(f"s must be N×N or F×N×N, got shape {np.asarray(s).shape}")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("s contains non-finite values")
    f = np.atleast_1d(np.asarray(frequency_hz, dtype=float))
    if f.shape != (matrix.shape[0],):
        raise ValueError(f"{f.size} frequencies for {matrix.shape[0]} matrices")
    frequency = skrf.Frequency.from_f(f, unit="Hz")
    return skrf.Network(frequency=frequency, s=matrix, z0=z0, name=name, s_def="power")


def terminate(
    network,
    terminations: Mapping[int, complex] | Sequence[tuple[int, complex]],
    *,
    port_map: Sequence[int] | None = None,
) -> np.ndarray:
    """Kept-port S after terminating ports in lumped impedances, via `skrf.Circuit`.

    Parameters
    ----------
    network
        An N-port `skrf.Network` (e.g. from `network_from_records`); its
        (uniform, real) ``z0`` is the kept ports' reference impedance.
    terminations
        ``{logical_port: Z_ohm}``; a scalar ``Z`` or one value per frequency.
        Every other logical port is kept, in ascending order.
    port_map
        Logical port ``i`` is wired to network port ``port_map[i]``; default the
        identity.  Exists so the netlist's port order is explicit (and so a
        negative control can deliberately mis-order it).

    Returns
    -------
    ``F×K×K`` complex array (``K`` kept ports) at the network's ``z0``; a single
    frequency still returns the leading axis of length 1.
    """
    _, Circuit = _skrf()
    n = int(network.nports)
    pairs = (
        list(terminations.items())
        if hasattr(terminations, "items")
        else [tuple(item) for item in terminations]
    )
    term = {int(k): z for k, z in pairs}
    if len(term) != len(pairs):
        raise ValueError(f"duplicate port index in terminations: {[k for k, _ in pairs]}")
    for k in term:
        if not 0 <= k < n:
            raise ValueError(f"termination port index {k} out of range for a {n}-port network")
    if len(term) == n:
        raise ValueError("terminating every port leaves no network to return")
    mapping = list(range(n)) if port_map is None else [int(p) for p in port_map]
    if sorted(mapping) != list(range(n)):
        raise ValueError(f"port_map must be a permutation of 0..{n - 1}, got {port_map!r}")

    z0_all = np.asarray(network.z0)
    z0 = complex(z0_all.flat[0])
    if not np.allclose(z0_all, z0, rtol=0.0, atol=0.0) or z0.imag != 0.0 or z0.real <= 0.0:
        raise ValueError("terminate needs one uniform real positive z0 on every port")
    z0 = float(z0.real)
    freq = network.frequency

    connections = []
    for logical in range(n):
        target = (network, mapping[logical])
        if logical in term:
            z = np.broadcast_to(np.asarray(term[logical], dtype=np.complex128), (len(freq),))
            if not np.all(np.isfinite(z)):
                raise ValueError(f"termination on port {logical} must be finite, got {term[logical]!r}")
            element = Circuit.SeriesImpedance(freq, z, name=f"Z_{logical}", z0=z0)
            ground = Circuit.Ground(freq, name=f"GND_{logical}", z0=z0)
            connections.append([target, (element, 0)])
            connections.append([(element, 1), (ground, 0)])
        else:
            port = Circuit.Port(freq, name=f"P_{logical}", z0=z0)
            connections.append([(port, 0), target])
    circuit = Circuit(connections)
    return np.asarray(circuit.network.s, dtype=np.complex128)


def input_impedance(s11: complex, z0: float) -> complex:
    """``Z_in = z0 (1 + S11)/(1 − S11)`` for a 1×1 kept network (printing aid)."""
    s11 = complex(s11)
    if s11 == 1.0:
        return complex(np.inf, np.inf)
    return float(z0) * (1.0 + s11) / (1.0 - s11)
