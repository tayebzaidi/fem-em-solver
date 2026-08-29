"""``B`` from a time-harmonic ``E``, and the rotating component ``B₁⁺``.

Faraday's law in the frequency domain, ``∇×E = −jωB``, is the only route from
the solved N1curl phasor to a magnetic field; ``B`` lands on DG0, the natural
home of a curl of an N1curl field (`WF-6` step 1, 2026-08-29 — lifted from the
private copies `examples/ports/04` and `examples/ports/05` each carried).

``B₁⁺`` is the circularly polarised component that rotates *with* the nuclear
precession — the one an MRI transmit coil is judged on.  In the peak-phasor
convention the solver works in, it is ``|B_x + jB_y|/2``.
"""

from __future__ import annotations

import numpy as np
import ufl
from dolfinx import fem

__all__ = ["magnetic_flux_density_from_e", "b1_plus"]


def _require_complex(function, what: str) -> None:
    if not np.iscomplexobj(np.asarray(function.x.array)):
        raise ValueError(
            f"{what} needs the complex DolfinX build: the field handed in has "
            f"dtype {np.asarray(function.x.array).dtype}, and ∇×E/(−jω) is not "
            "representable in real mode (source /usr/local/bin/dolfinx-complex-mode)"
        )


def magnetic_flux_density_from_e(e_complex, omega_rad_per_s, *, name: str = "B_phasor"):
    """``B = ∇×E / (−jω)`` as a DG0 vector ``Function`` on ``e_complex``'s mesh.

    ``e_complex`` is the solved phasor (N1curl, peak convention);
    ``omega_rad_per_s`` is ``2πf``.  The result is ghost-updated, so a caller
    may read ``x.array`` on any rank.
    """
    omega = float(omega_rad_per_s)
    if not np.isfinite(omega) or omega <= 0.0:
        raise ValueError(f"omega_rad_per_s must be finite and positive, got {omega_rad_per_s!r}")
    _require_complex(e_complex, "magnetic_flux_density_from_e")

    msh = e_complex.function_space.mesh
    w_dg = fem.functionspace(msh, ("DG", 0, (3,)))
    b_fn = fem.Function(w_dg, name=name)
    b_fn.interpolate(
        fem.Expression(
            ufl.curl(e_complex) / (-1j * omega), w_dg.element.interpolation_points
        )
    )
    b_fn.x.scatter_forward()
    return b_fn


def b1_plus(b_complex, *, name: str = "B1_plus"):
    """``|B₁⁺| = |B_x + jB_y| / 2`` as a DG0 scalar ``Function``.

    Takes the DG0 vector phasor :func:`magnetic_flux_density_from_e` returns.
    The value is a real magnitude; in the complex build it is stored in a
    complex array with zero imaginary part, so read ``.real`` after a point
    evaluation.
    """
    _require_complex(b_complex, "b1_plus")
    msh = b_complex.function_space.mesh
    if b_complex.function_space.element.value_shape != (3,):
        raise ValueError(
            "b1_plus wants the 3-vector B phasor, got value shape "
            f"{b_complex.function_space.element.value_shape}"
        )

    s_dg = fem.functionspace(msh, ("DG", 0))
    out = fem.Function(s_dg, name=name)
    components = np.asarray(b_complex.x.array).reshape(-1, 3)
    out.x.array[:] = np.abs(components[:, 0] + 1j * components[:, 1]) / 2.0
    out.x.scatter_forward()
    return out
