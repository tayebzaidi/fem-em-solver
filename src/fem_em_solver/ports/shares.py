"""`PORT-14` step 3 — the lumped sheet's terminal-form deficit, in the package.

`PORT-16` step 1 measured, in a test module
(``tests/validation/test_birdcage_power_identity.py::_exact_shares``), that the
sheets' terminal-current dissipation ``½|I|² Re Z_p`` is the uniform-field
**Cauchy–Schwarz lower bound** on what the solved field deposits in the sheet,

    ½|I|² Re Z_p  ≤  C = ½ Re(Y_s) ∫_S |E_t + E_src ĥ|² dA ,   Y_s = 1/R,

and `PORT-14` step 2d showed the pooled deficit ``C/terminal − 1`` *is* the
proportional-law coefficient ``κ`` of the sheet's realised termination to 0.3 %
at 64 MHz.  `src/` cannot import `tests/`, so the ``C/terminal − 1``
computation is lifted here verbatim in arithmetic (same forms, same reductions,
same summation order) so the sheet law's default-off width opt-in
(:func:`~fem_em_solver.ports.lumped.sheet_resistivity_ohm_per_square`) can take
``κ`` computed in-run rather than a literal.  The test module keeps its own
helper; `PORT-14` step 3's anchor (0) asserts the two agree at rtol 1e-12.

Every number returned is MPI-reduced (``assemble_scalar`` is rank-local).
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from .lumped import LumpedPortSheet, _sheet_measure, sheet_terminal_current

__all__ = ["sheet_ceiling_dissipation_w", "terminal_form_deficit"]


def sheet_ceiling_dissipation_w(mesh, facet_tags, sheet: LumpedPortSheet, e_complex) -> float:
    """``½ Re(Y_s) ∫_S |E_t + E_src ĥ|² dA`` — the Cauchy–Schwarz ceiling.

    ``E_t = E − (E·n̂)n̂`` with ``n̂`` from the ``'+'`` side; ``ufl.dot`` for the
    real normal (``ufl.inner`` would conjugate it).  Interior sheets only, as
    in the test helper this lifts.
    """
    ds_sheet = _sheet_measure(mesh, facet_tags, sheet)
    n = ufl.FacetNormal(mesh)("+")
    e_r = e_complex("+")
    e_t = e_r - ufl.dot(e_r, n) * n
    e_src = complex(sheet.source_voltage_v) / float(sheet.gap_height_m)
    src_vec = ufl.as_vector([default_scalar_type(e_src * c) for c in sheet.unit_drive()])
    total = e_t + src_vec
    integral = complex(
        mesh.comm.allreduce(
            fem.assemble_scalar(fem.form(ufl.inner(total, total) * ds_sheet)), op=MPI.SUM
        )
    )
    y_s = 1.0 / sheet.sheet_resistivity
    return 0.5 * float(np.real(y_s)) * float(np.real(integral))


def terminal_form_deficit(
    mesh, facet_tags, sheets: Sequence[LumpedPortSheet], e_complex, comm=None
) -> dict:
    """``C/terminal − 1`` for one solved drive, pooled and per sheet.

    ``sheets`` are the sheets exactly as they entered the solve (the driven one
    carrying its ``source_voltage_v``); ``e_complex`` is that solve's phasor.
    The terminal form is ``½|I|² Re Z_p`` with ``I`` from the package's own
    :func:`~fem_em_solver.ports.lumped.sheet_terminal_current` and ``Z_p``
    each sheet's own ``port_impedance_ohm``.

    Returns ``{"pooled", "per_sheet", "ceiling", "terminal", "ceiling_total",
    "terminal_total"}``, all rank-identical.
    """
    comm = mesh.comm if comm is None else comm
    ceiling = {}
    terminal = {}
    for sheet in sheets:
        ceiling[sheet.port_id] = sheet_ceiling_dissipation_w(mesh, facet_tags, sheet, e_complex)
        current = sheet_terminal_current(mesh, facet_tags, sheet, e_complex, comm)
        terminal[sheet.port_id] = (
            0.5 * abs(complex(current)) ** 2 * float(np.real(sheet.port_impedance_ohm))
        )
    ceiling_total = float(sum(ceiling.values()))
    terminal_total = float(sum(terminal.values()))
    return {
        "pooled": ceiling_total / terminal_total - 1.0,
        "per_sheet": {pid: ceiling[pid] / terminal[pid] - 1.0 for pid in ceiling},
        "ceiling": ceiling,
        "terminal": terminal,
        "ceiling_total": ceiling_total,
        "terminal_total": terminal_total,
    }
