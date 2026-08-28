"""Example (`EX-34`): the birdcage 4-port S-matrix across 10 / 64 / 128 MHz.

`ports:4` (`EX-32`) solves the coil's four ports at **10 MHz**, the port model's
own frequency. `PORT-11` then carried the same three gates to both Larmor
frequencies (✅ 2026-08-26, steps 2 and 3), and this example is that chunk's
§5.4 ramp: the first example in the tree that solves a port **at a Larmor
frequency**, and the first to put all three frequencies side by side.

**The angle is the ladder, and the ladder needs one mesh.** The `PORT-11` gate
modules build a fresh mesh per rung — correct for a gate, where the mesh is part
of what is being asserted, but it means the 10 / 64 / 128 MHz readings there are
never *the same* mesh in one process. Here the `GEO-19` step-B fixture is built
**once** (116 085 cells, ~26 s) and all twelve driven solves run on it, so the
frequency is demonstrably the only thing that moves between the rungs and the
resolution table below is a property of one meshed object rather than three.

**What runs.** `GEO-18`'s gapped, sheeted, phantom-loaded four-leg birdcage;
four ``f = 0.5`` lumped-element port sheets, one per leg, at ``Z_p = 50 Ω``;
three rungs × four driven solves through the gate module's **own**
``_four_port_rung`` (`tests/validation/test_port_birdcage_leg_offset_sweep.py`),
assembled into a 4×4 by the power-wave route each time. Printed per rung: the
phantom's loss tangent, δ and λ, cells/δ and cells/λ (through the 128 MHz gate
module's own ``_resolution``), the three gate readings, ``σ_max``, the max
column power sum, ``|Im P|/Re P`` at the driven port, and reciprocity as an
order of magnitude.

**It asserts, and it does not re-implement.** Every band and every record is
imported from the `PORT-9`/`PORT-11` modules:

* **gate (i)** reciprocity ``‖S − Sᵀ‖/‖S‖ ≤ RECIPROCITY_BAND`` (1e-3) — every
  rung;
* **gate (ii)** passivity ``σ_max(S) ≤ 1 + PASSIVITY_SIGMA_TOLERANCE`` with
  every column power sum ``≤ 1`` — every rung;
* **gate (iii′)** C4 symmetry, each circulant class of ``Z`` spreading
  ``≤ ADJACENT_SPREAD_BAND`` (0.5%) with the pooled-vs-worst control at
  ``POOLED_SEPARATION_FLOOR`` (10×) — every rung;
* **the pre-gate stop rule** ``PHANTOM_CELLS_PER_LAMBDA_FLOOR`` (10) at
  128 MHz, imported and enforced *before* the 128 MHz gates are read;
* **the 10 MHz anchor** — leg (d)'s recorded 4×4 ``LEG_D_S_MATRIX_10MHZ`` to
  ``FREQUENCY_CONTROL_BAND`` (1e-6) and leg (d0)'s ``LEG_D0_Z_COLUMN`` to
  ``LEG_D0_REPRODUCTION_BAND``;
* **the Larmor anchors** — the 64 and 128 MHz rungs reproduce `PORT-11` step
  2/3's recorded ``σ_max``, column-power maximum and class spreads inside a
  pre-stated 1% band (the `EX-19` precedent). Reciprocity residuals are
  **excluded** from that comparison by the (d3c) rule: power-wave readings sit
  at ~1e-16…1e-11 and reproduce in order of magnitude only.

**Negative control** (the `EX-20`/`EX-32` pattern) at **128 MHz**, the rung no
control has ever been run on: the deprecated `PORT-0` coupling heuristic on the
same problem and the same mesh, its ``DeprecationWarning`` shown,
``is_placeholder`` asserted **True**, its identically-zero off-diagonal printed,
and its separation from the field-derived ``S`` asserted above the `EX-20`
2e-3 floor.

**Scope — read this before quoting any number below.** These are the
`PORT-11` claims verbatim: **self-consistency identities on one fixture, not an
absolute-accuracy, resonance or tuning claim.** A reciprocal, passive, C4
4×4 at 128 MHz says the assembly and the port model are consistent at that
frequency; it says nothing about whether this coil is tuned, what its resonances
are, or how close the entries are to a measurement or to Ansys. There is no
B1+ or SAR figure here. ``|Im P|/Re P`` is printed and never gated.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:5 -n 2 -t 400

Outputs, in ``paraview_output/``:
``ports_05_birdcage_larmor_frequency_ladder_128mhz_combined.xdmf`` (the 128 MHz
port-1-driven ``E``/``B`` phasor magnitudes — the rung no example has exported),
``..._10mhz_combined.xdmf`` for the side-by-side, and
``ports_05_birdcage_larmor_frequency_ladder_facets.xdmf``; threshold ``mesh_tags`` on
211–214 in the last to see the four port sheets the BC lives on.
"""

from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem, io

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gates' constants, helpers and construction can be imported rather than
# restated.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.core import TimeHarmonicSolver  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.ports.definitions import PortDefinition  # noqa: E402
from fem_em_solver.ports.lumped import (  # noqa: E402
    lumped_port_bilinear_term,
    lumped_port_linear_term,
)
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep  # noqa: E402

from tests.mesh.test_birdcage_port_sheets import PORT_LOWER, PORT_UPPER  # noqa: E402
from tests.mesh.test_birdcage_port_tags import LEG_COUNT  # noqa: E402
from tests.validation.test_lossy_sphere_fullwave import (  # noqa: E402
    FREQUENCY_64_HZ,
    FREQUENCY_128_HZ,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    LEG_D0_REPRODUCTION_BAND,
    LEG_D0_Z_COLUMN,
    PASSIVITY_SIGMA_TOLERANCE,
    POOLED_SEPARATION_FLOOR,
    TERMINATED_PORT_IMPEDANCE_OHM,
)
from tests.validation.test_port_birdcage_larmor_gate import (  # noqa: E402
    FREQUENCY_CONTROL_BAND,
    LEG_D_S_MATRIX_10MHZ,
    _terminal_power,
)
from tests.validation.test_port_birdcage_larmor_gate_128 import (  # noqa: E402
    PHANTOM_CELLS_PER_LAMBDA_FLOOR,
    STEP2_64MHZ,
    _require_resolution,
    _resolution,
)
from tests.validation.test_port_birdcage_leg_offset_sweep import (  # noqa: E402
    _four_port_rung,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    ADJACENT_SPREAD_BAND,
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
    STEP2_CELL_COUNT,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ  # noqa: E402
from tests.validation.test_port_lumped_sheet_sweep import (  # noqa: E402
    RECIPROCITY_BAND,
)
from tests.validation.test_port_package_sparameters import (  # noqa: E402
    REFERENCE_IMPEDANCE_OHM,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "ports_05_birdcage_larmor_frequency_ladder"

# The negative control's floor, the `EX-20` constant and rationale (`EX-32`
# carries the same one at 10 MHz): the heuristic S must differ from the
# field-derived one by more than this. It is a floor with orders of magnitude of
# headroom, never a fitted threshold — the two matrices are not the same kind of
# object, and a heuristic that happened to agree would be a finding about the
# heuristic, not a passing example.
HEURISTIC_SEPARATION_FLOOR = 2.0e-3

# **`PORT-11` step 3's 128 MHz record**, version-tagged:
# `20260826T213414Z_PORT-11-step3.log` on the 116 085-cell `GEO-19` step-B mesh
# through leg (d3)'s power-wave `S` assembly, 0.11 image. Restated here rather
# than imported because the 128 MHz gate module keeps these in its log and its
# §7 prose, not in a constant — the same reason that module restates step 2's
# 64 MHz digits as `STEP2_64MHZ`, which this example imports. The reciprocity
# residual travels for printing only and is excluded from the reproduction band
# by the (d3c) rule.
STEP3_128MHZ = {
    "reciprocity": 7.030990825e-15,
    "sigma_max": 0.998974779,
    "column_power_max": 0.861668762,
    "spreads": {"self": 0.001012, "adjacent": 0.000916, "opposite": 0.000654},
    "cells_per_delta_phantom": 5.1845,
    "cells_per_lambda_phantom": 12.5024,
}

# The reproduction band on the two Larmor records above. Pre-stated at **1%**
# (the `EX-19` precedent for reproducing a recorded figure through a *different*
# entry path): this example drives the identical construction, but on a mesh
# built once and reused across three rungs rather than rebuilt per rung, so the
# comparison is a reproduction check on the ladder's plumbing and not a physics
# tolerance. It does not widen. A miss is an example/test divergence finding
# (§7 `EX-34` negative result), never a licence.
LARMOR_RECORD_BAND = 1.0e-2

# Which rung reproduces which record. The 10 MHz rung has its own, tighter
# anchors (`LEG_D_S_MATRIX_10MHZ` at 1e-6 and `LEG_D0_Z_COLUMN`) and is handled
# separately below.
LARMOR_RECORDS = {"64 MHz": STEP2_64MHZ, "128 MHz": STEP3_128MHZ}


def _paraview_fields(msh, e_complex, omega):
    """CG1 ``E``/``B`` magnitudes from the solved phasor, plus the split ``E``.

    XDMF cannot carry N1curl and the writers take Lagrange interpolants only
    (`EX-14`/`EX-17`), so the phasor is interpolated before it is split. ``B``
    comes from Faraday's law, ``B = ∇×E/(−jω)``, on DG0 — the natural home of a
    curl of an N1curl field. Lifted unchanged from `EX-32`, which is the point:
    the picture is the same, only the frequency moved.
    """
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    e_cg = fem.Function(v_cg, name="E_phasor")
    e_cg.interpolate(e_complex)
    e_cg.x.scatter_forward()

    e_re = fem.Function(v_cg, name="E_real")
    e_re.x.array[:] = np.real(e_cg.x.array)
    e_im = fem.Function(v_cg, name="E_imag")
    e_im.x.array[:] = np.imag(e_cg.x.array)

    s_cg = fem.functionspace(msh, ("Lagrange", 1))
    e_mag = fem.Function(s_cg, name="E_magnitude")
    components = np.abs(e_cg.x.array.reshape(-1, 3))
    e_mag.x.array[:] = np.sqrt(np.sum(components * components, axis=1))

    w_dg = fem.functionspace(msh, ("DG", 0, (3,)))
    b_fn = fem.Function(w_dg, name="B_phasor")
    b_fn.interpolate(
        fem.Expression(
            ufl.curl(e_complex) / (-1j * omega), w_dg.element.interpolation_points
        )
    )
    s_dg = fem.functionspace(msh, ("DG", 0))
    b_mag = fem.Function(s_dg, name="B_magnitude")
    b_components = np.abs(b_fn.x.array.reshape(-1, 3))
    b_mag.x.array[:] = np.sqrt(np.sum(b_components * b_components, axis=1))

    for f in (e_re, e_im, e_mag, b_mag):
        f.x.scatter_forward()
    return {
        "E_real": e_re,
        "E_imag": e_im,
        "E_magnitude": e_mag,
        "B_magnitude": b_mag,
    }


def _solve_driven_p1(rung, comm):
    """One extra solve per exported rung, because the sweep returns no fields.

    Exactly the case ``run_lumped_sheet_port_case`` runs for ``driven='P1'``:
    every port's sheet in the bilinear form, P1's sheet also carrying the
    impressed source.
    """
    problem = rung["problem"]
    msh = rung["mesh"]
    tags_f = rung["facet_tags"]
    specs = rung["specs"]
    omega = 2.0 * np.pi * float(problem.frequency_hz)
    driven_id = rung["port_defs"][0].port_id

    sheets = [spec.sheet(driven=(spec.port_id == driven_id)) for spec in specs]
    driven_sheet = next(s for s in sheets if s.port_id == driven_id)

    solver = TimeHarmonicSolver(problem, degree=1)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=None,
        project_source=False,
        extra_bilinear_terms=[
            lambda trial, test, _s=sheet: lumped_port_bilinear_term(
                msh, tags_f, _s, trial, test, omega_rad_per_s=omega
            )
            for sheet in sheets
        ],
        extra_linear_terms=[
            lambda test, _s=driven_sheet: lumped_port_linear_term(
                msh, tags_f, _s, test, omega_rad_per_s=omega
            )
        ],
    )
    comm.Barrier()
    return fields.e_complex, omega, driven_id, time.perf_counter() - t0


def _write_paraview(rung, suffix, comm, with_facets=False):
    """Cells + tags + the driven field in one file; facet tags once, in a second."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    written = {}

    e_driven, omega, driven_id, t_solve = _solve_driven_p1(rung, comm)
    combined, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_{suffix}_combined",
        rung["mesh"],
        rung["cell_tags"],
        _paraview_fields(rung["mesh"], e_driven, omega),
        comm=comm,
    )
    if combined is not None:
        written[f"cells + E/B fields ({suffix})"] = combined

    if with_facets:
        msh = rung["mesh"]
        facets_path = OUTPUT_DIR / f"{BASENAME}_facets.xdmf"
        msh.topology.create_connectivity(msh.topology.dim - 1, msh.topology.dim)
        with io.XDMFFile(comm, facets_path, "w") as xdmf:
            xdmf.write_mesh(msh)
            xdmf.write_meshtags(rung["facet_tags"], msh.geometry)
        if comm.rank == 0:
            written["facet tags"] = facets_path

    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return written, driven_id, t_solve


def _heuristic_control(rung, comm):
    """The retired `PORT-0` route on the same problem and the same mesh, at 128 MHz.

    It is handed the **gap-box halves** rather than the port sheets because it
    validates its terminal tags against *cell* tags: the coupling heuristic
    predates the port sheet entirely and cannot address one. That is the
    control's content as much as the numbers are — the retired route reads
    regions and a ring-distance rule, the gated route reads a solved field, and
    at 128 MHz the retired route does not even know the frequency changed.
    """
    ports = [
        PortDefinition(
            port_id=f"H{i}",
            positive_tag=PORT_UPPER + i,
            negative_tag=PORT_LOWER + i,
            orientation="leg_gap_axial_plus_z",
            z0_ohm=REFERENCE_IMPEDANCE_OHM,
        )
        for i in range(1, LEG_COUNT + 1)
    ]
    comm.Barrier()
    t0 = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = run_n_port_sparameter_sweep(rung["problem"], ports)
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    comm.Barrier()
    return result, deprecations, time.perf_counter() - t0


def _assert_three_gates(label, rung, comm):
    """The `PORT-9` gate triple, imported and asserted, on one rung."""
    reciprocity = float(rung["reciprocity"])
    sigma_max = float(np.max(rung["sigma"]))
    power_max = float(np.max(rung["column_power"]))
    spreads = rung["spreads"]
    worst = max(spreads.values())
    separation = rung["pooled"] / worst if worst > 0.0 else np.inf
    decade = float(np.log10(reciprocity)) if reciprocity > 0.0 else -np.inf

    if comm.rank == 0:
        print(
            f"\n[gates @ {label}]\n"
            f"    (i)   ||S - S^T||/||S|| = {reciprocity:.9e} ~ 1e{decade:.0f}  "
            f"band {RECIPROCITY_BAND:.0e}  "
            f"{'PASS' if reciprocity <= RECIPROCITY_BAND else 'MISS'}  "
            f"(order of magnitude only, the (d3c) rule; "
            f"||Z - Z^T||/||Z|| = {rung['z_reciprocity']:.3e})\n"
            f"    (ii)  sigma_max(S) = {sigma_max:.9f}  max column power sum = "
            f"{power_max:.9f}  tolerance {PASSIVITY_SIGMA_TOLERANCE:.0e}  "
            f"{'PASS' if sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE else 'MISS'}\n"
            f"    (iii')C4 class spreads: self {spreads['self'] * 100:.4f}%  "
            f"adjacent {spreads['adjacent'] * 100:.4f}%  opposite "
            f"{spreads['opposite'] * 100:.4f}%  band "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}%  "
            f"{'PASS' if worst <= ADJACENT_SPREAD_BAND else 'MISS'}\n"
            f"          control: pooled off-diagonal {rung['pooled'] * 100:.4f}% "
            f"is {separation:.4f}x the worst intra-class spread (floor "
            f"{POOLED_SEPARATION_FLOOR:.0f}x)  "
            f"{'PASS' if separation >= POOLED_SEPARATION_FLOOR else 'MISS'}",
            flush=True,
        )

    assert not rung["result"].is_placeholder, (
        f"{label}: the sweep returned is_placeholder=True — it fell back to the "
        "PORT-0 coupling heuristic, so no impedance on this rung came off a "
        "solved field"
    )
    assert reciprocity <= RECIPROCITY_BAND, (
        f"{label}: ||S - S^T||/||S|| = {reciprocity:.6e} against the imported "
        f"{RECIPROCITY_BAND:.0e} band — an example/test divergence finding about "
        "the lumped-sheet route at this frequency, never a licence to widen "
        "(§7 `EX-34` negative result)"
    )
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"{label}: sigma_max(S) = {sigma_max:.9f} exceeds 1 by more than the "
        f"imported {PASSIVITY_SIGMA_TOLERANCE:.0e} — the assembled 4x4 is active"
    )
    for k, value in enumerate(rung["column_power"], start=1):
        assert value <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
            f"{label}: column {k} of S carries power sum {value:.9f} > 1 + "
            f"{PASSIVITY_SIGMA_TOLERANCE:.0e} — driving port {k} returns more "
            "power than it is fed"
        )
    for name, value in spreads.items():
        assert value <= ADJACENT_SPREAD_BAND, (
            f"{label}: the {name} class of Z spreads {value * 100:.4f}% against "
            f"the imported {ADJACENT_SPREAD_BAND * 100:.1f}% band — on an "
            "undisplaced, C4-invariant layout"
        )
    assert separation >= POOLED_SEPARATION_FLOOR, (
        f"{label}: the pooled off-diagonal class spreads "
        f"{rung['pooled'] * 100:.4f}%, only {separation:.4f}x the worst "
        f"intra-class spread, against the imported "
        f"{POOLED_SEPARATION_FLOOR:.0f}x floor — the class reading is not "
        "resolving the layout's structure"
    )
    return {"reciprocity": reciprocity, "sigma_max": sigma_max, "power_max": power_max}


def _assert_larmor_record(label, rung, record, comm):
    """The 64 / 128 MHz rung against `PORT-11`'s recorded digits, at 1% relative.

    Reciprocity is printed and **excluded** — the (d3c) rule. Everything else in
    the record is a well-conditioned reading that reproduces.
    """
    readings = {
        "sigma_max": (float(np.max(rung["sigma"])), record["sigma_max"]),
        "column_power_max": (
            float(np.max(rung["column_power"])),
            record["column_power_max"],
        ),
        **{
            f"spread_{name}": (rung["spreads"][name], record["spreads"][name])
            for name in ("self", "adjacent", "opposite")
        },
    }
    if comm.rank == 0:
        print(
            f"\n[anchor @ {label}] vs `PORT-11`'s record, band "
            f"{LARMOR_RECORD_BAND:.0e} relative (reciprocity excluded by the "
            f"(d3c) rule: {rung['reciprocity']:.3e} here vs "
            f"{record['reciprocity']:.3e} recorded — same decade, never a digit):",
            flush=True,
        )
        for name, (value, ref) in readings.items():
            print(
                f"    {name:18s} {value:.9f}  vs record {ref:.9f}  relative "
                f"{abs(value - ref) / abs(ref):.3e}",
                flush=True,
            )
    for name, (value, ref) in readings.items():
        miss = abs(value - ref) / abs(ref)
        assert miss < LARMOR_RECORD_BAND, (
            f"{label}: {name} = {value:.9f} deviates {miss:.3e} from `PORT-11`'s "
            f"recorded {ref:.9f}, outside the pre-stated "
            f"{LARMOR_RECORD_BAND:.0e} band — the example path is not driving the "
            "fixture the gate module measured (§7 `EX-34` negative result: "
            "known-issues entry, report, stop; nothing re-recorded)"
        )


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    ladder = (("10 MHz", FREQUENCY_HZ), ("64 MHz", FREQUENCY_64_HZ),
              ("128 MHz", FREQUENCY_128_HZ))

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "EX-34 - the birdcage 4-port S-matrix across 10 / 64 / 128 MHz, "
            "one mesh",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"\n[fixture] `GEO-18` gapped + sheeted 4-leg birdcage, phantom "
            f"loaded (conductor tag {CONDUCTOR_CELL_TAG}, phantom tag "
            f"{PHANTOM_CELL_TAG}, air elsewhere; no vessel wall in this "
            f"fixture), `GEO-19` step B mesh built ONCE\n"
            f"[ports]   {LEG_COUNT} lumped-element sheets, one per leg, "
            f"Z_p = {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ohm, "
            f"z0 = {REFERENCE_IMPEDANCE_OHM:.1f} Ohm\n"
            f"[ladder]  "
            + ", ".join(f"{label} ({f:.6e} Hz)" for label, f in ladder)
            + f" - 12 driven solves\n"
            f"[gates]   (i) ||S - S^T||/||S|| <= {RECIPROCITY_BAND:.0e};  "
            f"(ii) sigma_max(S) <= 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e} with "
            f"column power sums <= 1;\n"
            f"          (iii') each C4 class of Z spreads <= "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}%, pooled/worst separation >= "
            f"{POOLED_SEPARATION_FLOOR:.0f}x  - all three on EVERY rung\n"
            f"[stop]    pre-gate resolution at 128 MHz: phantom cells/lambda >= "
            f"{PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f}, imported and enforced before "
            f"the 128 MHz gates are read\n"
            f"[anchors] 10 MHz reproduces leg (d)'s 4x4 to "
            f"{FREQUENCY_CONTROL_BAND:.0e} and leg (d0)'s column to "
            f"{LEG_D0_REPRODUCTION_BAND:.0e}; 64/128 MHz reproduce `PORT-11`'s\n"
            f"          recorded sigma_max / column power / spreads to "
            f"{LARMOR_RECORD_BAND:.0e} (reciprocity excluded, the (d3c) rule)\n"
            f"[scope]   `PORT-11`'s claim verbatim: self-consistency identities "
            f"on one fixture. NOT an absolute-accuracy, resonance or\n"
            f"          tuning claim, and no B1+/SAR figure. |Im P|/Re P is "
            f"printed, never gated.",
            flush=True,
        )

    # ---- the ladder: one mesh, three rungs, twelve driven solves -----------
    zeros = np.zeros(LEG_COUNT)
    rungs = {}
    for label, frequency in ladder:
        rungs[label] = _four_port_rung(
            f"EX-34 {label}",
            zeros,
            frequency,
            reuse=rungs.get("10 MHz"),
        )

    for label, _ in ladder[1:]:
        assert rungs[label]["reused_mesh"], (
            f"the {label} rung rebuilt its mesh — the one-mesh ladder is this "
            "example's entire angle"
        )
        assert rungs[label]["mesh"] is rungs["10 MHz"]["mesh"], (
            f"the {label} rung is not on the same mesh object as the 10 MHz rung"
        )
        assert rungs[label]["cells"] == rungs["10 MHz"]["cells"]

    # ---- the resolution table, on the one solved mesh ----------------------
    resolution = _resolution(rungs["10 MHz"])
    if comm.rank == 0:
        print(
            f"\n[mesh] {rungs['10 MHz']['cells']} cells (`GEO-19` step B record "
            f"{STEP2_CELL_COUNT}, ratio "
            f"{rungs['10 MHz']['cells'] / STEP2_CELL_COUNT:.6f}), built in "
            f"{rungs['10 MHz']['mesh_time']:.1f} s and reused by all three rungs; "
            f"sweeps "
            + " + ".join(f"{rungs[l]['sweep_time']:.1f} s" for l, _ in ladder)
            + f" at -n {comm.size}",
            flush=True,
        )
        for name, sz in resolution["sizes"].items():
            print(
                f"    region {name:9s}: {sz['cells']:7d} owned cells  h_mean "
                f"{sz['h_mean']:.6e} m",
                flush=True,
            )
        print(
            "\n[ladder] the frequency table on this one mesh "
            "(loss tangent / delta / lambda / cells per each, phantom):",
            flush=True,
        )
        for label, _ in ladder:
            row = resolution["table"][label]
            ph = row["phantom"]
            power = _terminal_power(rungs[label])
            print(
                f"    {label:8s} tan_d {ph['loss_tangent']:.4f}  delta "
                f"{ph['delta']:.6e} m  lambda {ph['lambda']:.6e} m  =>  "
                f"cells/delta {row['cells_per_delta_phantom']:7.4f}  "
                f"cells/lambda {row['cells_per_lambda_phantom']:8.4f}  "
                f"(air cells/lambda {row['cells_per_lambda_air']:9.4f})\n"
                f"             P1 terminal P = {power:+.9e} VA  |Im P|/Re P = "
                f"{abs(power.imag) / abs(power.real):.6f}  (printed, never gated "
                "- stored energy, not a resonance reading)",
                flush=True,
            )
        print(
            "    the phantom crosses from conduction- to displacement-dominated "
            "up this ladder (tan_d 1.80 at 64 MHz, 0.90 at 128); delta stops "
            "falling\n    with frequency there, so it is cells/lambda and not "
            "cells/delta that tightens - which is why the stop rule below is on "
            "lambda.",
            flush=True,
        )

    # ---- the pre-gate stop rule, before any 128 MHz gate is read -----------
    row_128 = resolution["table"]["128 MHz"]
    if comm.rank == 0:
        print(
            f"\n[stop rule] 128 MHz phantom cells/lambda = "
            f"{row_128['cells_per_lambda_phantom']:.4f} against the imported "
            f"floor {PHANTOM_CELLS_PER_LAMBDA_FLOOR:.1f} "
            f"(record {STEP3_128MHZ['cells_per_lambda_phantom']:.4f})  "
            f"{'CLEAR' if row_128['cells_per_lambda_phantom'] >= PHANTOM_CELLS_PER_LAMBDA_FLOOR else 'FAIL'}",
            flush=True,
        )
    # The gate module's own enforcement, imported: it calls `pytest.fail` with
    # the resolution as the message, which is the behaviour this example wants
    # too - a resolution miss must never be reported as a gate pass.
    _require_resolution(resolution)
    assert row_128["cells_per_lambda_phantom"] >= PHANTOM_CELLS_PER_LAMBDA_FLOOR

    # ---- the three gates on every rung -------------------------------------
    for label, _ in ladder:
        rung = rungs[label]
        if comm.rank == 0:
            print(f"\n[sweep @ {label}] S (power waves, z0 = "
                  f"{REFERENCE_IMPEDANCE_OHM:.1f} Ohm):", flush=True)
            for r in range(LEG_COUNT):
                print("    S_%dk = " % (r + 1)
                      + "  ".join(f"{v:+.9e}" for v in rung["s"][r]), flush=True)
        _assert_three_gates(label, rung, comm)

    # ---- the 10 MHz anchor: leg (d)'s 4x4 and leg (d0)'s column ------------
    control = rungs["10 MHz"]
    s_dev = np.abs(control["s"] - LEG_D_S_MATRIX_10MHZ) / np.abs(LEG_D_S_MATRIX_10MHZ)
    z_dev = np.abs(control["z"][:, 0] - LEG_D0_Z_COLUMN) / np.abs(LEG_D0_Z_COLUMN)
    if comm.rank == 0:
        print(
            f"\n[anchor @ 10 MHz] leg (d)'s recorded 4x4: worst entry deviation "
            f"{np.max(s_dev):.3e} against the imported "
            f"{FREQUENCY_CONTROL_BAND:.0e}\n"
            f"                  leg (d0)'s terminated column: worst "
            f"{np.max(z_dev):.3e} against the imported "
            f"{LEG_D0_REPRODUCTION_BAND:.0e}",
            flush=True,
        )
    assert np.max(s_dev) < FREQUENCY_CONTROL_BAND, (
        f"the 10 MHz rung deviates {np.max(s_dev):.3e} from leg (d)'s recorded "
        f"4x4, outside the imported {FREQUENCY_CONTROL_BAND:.0e} band — the "
        "harness moved, not the frequency, and nothing the Larmor rungs read is "
        "comparable (§7 `EX-34` negative result)"
    )
    assert np.max(z_dev) < LEG_D0_REPRODUCTION_BAND, (
        f"the 10 MHz rung's driven column deviates {np.max(z_dev):.3e} from leg "
        f"(d0)'s record, outside the imported {LEG_D0_REPRODUCTION_BAND:.0e} band"
    )

    # ---- the Larmor anchors: `PORT-11`'s recorded digits at 1% -------------
    for label, record in LARMOR_RECORDS.items():
        _assert_larmor_record(label, rungs[label], record, comm)

    # ---- the negative control: the retired heuristic, at 128 MHz -----------
    heuristic, deprecations, t_heuristic = _heuristic_control(rungs["128 MHz"], comm)
    heuristic_delta = float(np.max(np.abs(heuristic.s_matrix - rungs["128 MHz"]["s"])))
    off_diagonal = np.abs(
        heuristic.s_matrix[~np.eye(LEG_COUNT, dtype=bool)]
    )
    if comm.rank == 0:
        print(
            f"\n[control] the deprecated PORT-0 coupling heuristic on the same "
            f"problem and the same mesh at 128 MHz ({t_heuristic:.1f} s, "
            f"{len(deprecations)} DeprecationWarning(s)):",
            flush=True,
        )
        for row in heuristic.s_matrix:
            print("    " + "  ".join(f"{v:+.6e}" for v in row), flush=True)
        for w in deprecations:
            print(f"    DeprecationWarning: {w.message}", flush=True)
        print(
            f"    max|off-diagonal| = {np.max(off_diagonal):.6e} (identically "
            f"zero: the heuristic predicts no coupling at all here)\n"
            f"    max|S_heuristic - S_field| = {heuristic_delta:.6e} "
            f"(floor {HEURISTIC_SEPARATION_FLOOR:.0e})  "
            f"is_placeholder = {heuristic.is_placeholder}",
            flush=True,
        )
    assert heuristic.is_placeholder, "the heuristic route must keep marking itself"
    assert deprecations, (
        "the heuristic route must emit a DeprecationWarning now that the "
        "solved-field route exists"
    )
    assert heuristic_delta > HEURISTIC_SEPARATION_FLOOR, (
        f"at 128 MHz the retired heuristic reproduces the field-derived S to "
        f"{heuristic_delta:.3e} — that is a finding about the heuristic, not a "
        "passing example"
    )

    # ---- ParaView: 128 MHz (new), plus 10 MHz for the side-by-side ---------
    written_128, driven_id, t_128 = _write_paraview(
        rungs["128 MHz"], "128mhz", comm, with_facets=True
    )
    written_10, _, t_10 = _write_paraview(rungs["10 MHz"], "10mhz", comm)
    if comm.rank == 0:
        print(
            f"\n[paraview] the {driven_id}-driven case re-solved for its field at "
            f"128 MHz ({t_128:.1f} s) and 10 MHz ({t_10:.1f} s); the sweep "
            f"returns readings, not fields:",
            flush=True,
        )
        for what, path in {**written_128, **written_10}.items():
            print(f"  {what:<32s} {path}")
        print(
            "\n[paraview] each _combined file carries `E_real` / `E_imag` / "
            "`E_magnitude` (CG1) and `B_magnitude`"
            "\n           (DG0, B = curl E / (-j omega) from Faraday's law) "
            "beside `CellTags`; the two files are"
            "\n           on the same mesh, so they open side by side. Threshold "
            "`mesh_tags` on 211-214 in"
            "\n           the _facets file to see the four port sheets the lumped "
            "BC lives on."
            f"\n\nAll three gates hold on all three rungs, on one mesh. "
            f"Total elapsed {time.perf_counter() - started:.1f} s."
            "\nSelf-consistency identities only - no resonance, tuning or "
            "absolute-accuracy claim (`PORT-11`).",
            flush=True,
        )


if __name__ == "__main__":
    main()
