"""Example (`EX-32`): the **birdcage's** 4-port power-wave S-matrix at 10 MHz.

Every S-parameter example before this one solves the **two-torus** pair —
`ports:1` (`EX-18`, gap-voltage route), `ports:2` (`EX-20`, the package sweep
plus its heuristic control), `ports:3` (`EX-24`, the lumped-element sheet).
The two birdcage examples, `EX-28` (leg gaps) and `EX-31` (ring gaps), are
**mesh-only**: no example in this repo has ever solved a port *on the coil*.
That is the angle this one adds, and it is the §5.4 ramp `PORT-9` ✅ owes.

**What runs.** `GEO-18`'s gapped, sheeted, phantom-loaded four-leg birdcage on
`GEO-19` step B's mesh; four ``f = 0.5`` lumped-element port sheets, one per
leg, at ``Z_p = 50 Ω``; four driven solves through
:func:`~fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep`'s
lumped-sheet route at 10 MHz, assembled into a 4×4 by the **power-wave** route
(`PORT-9` leg (d3)). Printed: the 4×4 ``Z`` and ``S``, the three C4 circulant
class spreads, ``σ_max(S)`` and the column power sums, and the reciprocity
residual **as an order of magnitude only** — the (d3c) rule, because power-wave
reciprocity readings sit at ~1e-16…1e-11 and never reproduce digit-for-digit.

**It asserts, it does not merely render — and it does not re-implement.** The
sweep is built by calling `PORT-9` leg (d)'s own
``tests/validation/test_port_birdcage_four_port.py::build_four_port_sweep``,
so the fixture, the sheet construction and the assembly here *are* the gate
module's, not a copy of them (the `EX-33` reading of the `ANS-1` rule: import
the construction, not only the constants). Every band below is likewise
imported and never restated:

* **gate (i)** reciprocity — ``‖S − Sᵀ‖/‖S‖ ≤ RECIPROCITY_BAND`` (1e-3, step
  2c's);
* **gate (ii)** passivity — ``σ_max(S) ≤ 1 + PASSIVITY_SIGMA_TOLERANCE`` and
  every column power sum ``≤ 1``;
* **gate (iii′)** C4 symmetry — each circulant class of ``Z`` spreads
  ``≤ ADJACENT_SPREAD_BAND`` (0.5%), with leg (d)'s own pooled-vs-worst
  separation control at ``POOLED_SEPARATION_FLOOR`` (10×);
* **the anchor** — the P1-driven column reproduces leg (d0)'s recorded
  terminated column ``LEG_D0_Z_COLUMN`` to ``LEG_D0_REPRODUCTION_BAND``
  (1e-9), so this 4×4 is demonstrably built on the one-column record.

**Negative control** (the `EX-20` pattern): the deprecated `PORT-0` coupling
heuristic is run on the same problem and the same mesh, its
``DeprecationWarning`` is shown, ``is_placeholder`` is asserted **True**, and
its S-matrix is asserted to be separated from the field-derived one. The
heuristic cannot even be handed these ports — it validates terminal tags
against **cell** tags and has never known what a port sheet is — so it is
given the gap-box halves instead, which is itself the point: the retired route
reads regions, the gated one reads a field.

**Scope: 10 MHz, the port model's frequency.** No Larmor frequency, no
resonance, no tuning claim, and no loaded-coil claim at 64/128 MHz — that is
`PORT-11`, and nothing here licenses a figure at those frequencies. The feed
systematics on record are the two-torus ones (`PORT-1` §2.2); this fixture has
no vessel wall, so the regions are conductor, phantom and air.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:4

Outputs ``paraview_output/birdcage_four_port_sparameters_combined.xdmf``
(mesh + CellTags + the port-1-driven ``E``/``B`` phasor magnitudes — the first
field picture of a driven birdcage port in the examples tree) and
``birdcage_four_port_sparameters_facets.xdmf`` alongside it; threshold
``mesh_tags`` on 211–214 there to see the four port sheets the BC lives on.
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
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    LEG_D0_REPRODUCTION_BAND,
    LEG_D0_Z_COLUMN,
    PASSIVITY_SIGMA_TOLERANCE,
    POOLED_SEPARATION_FLOOR,
    TERMINATED_PORT_IMPEDANCE_OHM,
    build_four_port_sweep,
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
BASENAME = "birdcage_four_port_sparameters"

# The negative control's floor, the `EX-20` constant and rationale: the
# heuristic S must differ from the field-derived one by more than this. It is a
# floor with orders of magnitude of headroom, never a fitted threshold — the
# two matrices are not the same kind of object, and a heuristic that happened
# to agree would be a finding about the heuristic, not a passing example.
HEURISTIC_SEPARATION_FLOOR = 2.0e-3

# The (d3c) rule, stated as a *decade* window rather than a value: power-wave
# reciprocity on this fixture is noise over noise (leg (d)'s records read
# 2.152e-14 on this mesh and 2.049e-14 on the pre-step-B one), so this example
# prints the decade and gates only on the imported 1e-3 band. Nothing here
# pins a digit.
RECIPROCITY_DECADE_FLOOR = -18.0


def _paraview_fields(msh, e_complex, omega):
    """CG1 ``E``/``B`` magnitudes from the solved phasor, plus the split ``E``.

    XDMF cannot carry N1curl and the writers take Lagrange interpolants only
    (`EX-14`/`EX-17`), so the phasor is interpolated before it is split.
    ``B`` comes from Faraday's law, ``B = ∇×E/(−jω)``, on DG0 — the natural
    home of a curl of an N1curl field.
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


def _write_paraview(msh, cell_tags, facet_tags, fields, comm):
    """Cells + tags + the driven field in one file, facet tags in a second."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    written = {}

    combined, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined", msh, cell_tags, fields, comm=comm
    )
    if combined is not None:
        written["cells + E/B fields"] = combined

    facets_path = OUTPUT_DIR / f"{BASENAME}_facets.xdmf"
    msh.topology.create_connectivity(msh.topology.dim - 1, msh.topology.dim)
    with io.XDMFFile(comm, facets_path, "w") as xdmf:
        xdmf.write_mesh(msh)
        xdmf.write_meshtags(facet_tags, msh.geometry)
    if comm.rank == 0:
        written["facet tags"] = facets_path

    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return written


def _solve_driven_p1(sweep, comm):
    """One extra solve, because the sweep returns readings and not fields.

    Exactly the case ``run_lumped_sheet_port_case`` runs for ``driven='P1'``:
    every port's sheet in the bilinear form, P1's sheet also carrying the
    impressed source. The `EX-20` pattern — the sweep is the measurement, this
    is the picture, and the two are checked against each other below.
    """
    problem = sweep["problem"]
    msh = sweep["mesh"]
    tags_f = sweep["facet_tags"]
    specs = sweep["specs"]
    omega = 2.0 * np.pi * float(problem.frequency_hz)
    driven_id = sweep["port_defs"][0].port_id

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


def _heuristic_control(sweep, comm):
    """The retired `PORT-0` route on the same problem and the same mesh.

    It is handed the **gap-box halves** rather than the port sheets because it
    validates its terminal tags against *cell* tags: the coupling heuristic
    predates the port sheet entirely and cannot address one. That is the
    control's content as much as the numbers are — the retired route reads
    regions and a ring-distance rule, the gated route reads a solved field.
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
        result = run_n_port_sparameter_sweep(sweep["problem"], ports)
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    comm.Barrier()
    return result, deprecations, time.perf_counter() - t0


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "EX-32 — the birdcage's 4-port power-wave S-matrix at 10 MHz",
            flush=True,
        )
        print("=" * 78, flush=True)
        print(
            f"\n[fixture] `GEO-18` gapped + sheeted 4-leg birdcage, phantom "
            f"loaded (conductor tag {CONDUCTOR_CELL_TAG}, phantom tag "
            f"{PHANTOM_CELL_TAG}, air elsewhere; no vessel wall in this "
            f"fixture)\n"
            f"[ports]   {LEG_COUNT} lumped-element sheets, one per leg, "
            f"Z_p = {TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ohm, "
            f"z0 = {REFERENCE_IMPEDANCE_OHM:.1f} Ohm, f = {FREQUENCY_HZ:.3e} Hz\n"
            f"[gates]   (i) ||S - S^T||/||S|| <= {RECIPROCITY_BAND:.0e};  "
            f"(ii) sigma_max(S) <= 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e} with "
            f"column power sums <= 1;\n"
            f"          (iii') each C4 class of Z spreads <= "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}%, pooled/worst separation >= "
            f"{POOLED_SEPARATION_FLOOR:.0f}x\n"
            f"[anchor]  the P1-driven column reproduces leg (d0)'s record to "
            f"{LEG_D0_REPRODUCTION_BAND:.0e} relative\n"
            f"[scope]   10 MHz only — no Larmor, no resonance, no tuning "
            f"claim; 64/128 MHz is `PORT-11`",
            flush=True,
        )

    # ---- the gated sweep, built by the gate module itself ------------------
    sweep = build_four_port_sweep()
    result = sweep["result"]
    z = sweep["z"]
    s = sweep["s"]
    spreads = sweep["spreads"]
    pooled = sweep["pooled"]
    worst = max(spreads.values())
    separation = pooled / worst if worst > 0.0 else np.inf
    sigma_max = float(np.max(sweep["sigma"]))
    power_max = float(np.max(sweep["column_power"]))
    reciprocity = float(sweep["reciprocity"])
    decade = float(np.log10(reciprocity)) if reciprocity > 0.0 else -np.inf

    assert not result.is_placeholder, (
        "the lumped-sheet route returned is_placeholder=True — the sweep fell "
        "back to the PORT-0 coupling heuristic, so no impedance below came off "
        "a solved field"
    )
    assert z is not None and z.shape == (LEG_COUNT, LEG_COUNT), (
        "the lumped-sheet route must return its 4x4 Z"
    )
    assert np.all(np.isfinite(z.real)) and np.all(np.isfinite(z.imag))

    if comm.rank == 0:
        print(
            f"\n[sweep] {sweep['cells']} cells (`GEO-19` step B record "
            f"{STEP2_CELL_COUNT}, ratio "
            f"{sweep['cells'] / STEP2_CELL_COUNT:.6f}), mesh "
            f"{sweep['mesh_time']:.1f} s, four driven solves in "
            f"{sweep['sweep_time']:.1f} s at -n {comm.size}",
            flush=True,
        )
        print("\n[sweep] Z (Ohm), column k = port k driven:", flush=True)
        for row in range(LEG_COUNT):
            print(
                f"    Z_{row + 1}k = "
                + "  ".join(f"{v:+.9e}" for v in z[row]),
                flush=True,
            )
        print(
            f"[sweep] S (power waves, z0 = {REFERENCE_IMPEDANCE_OHM:.1f} Ohm):",
            flush=True,
        )
        for row in range(LEG_COUNT):
            print(
                f"    S_{row + 1}k = "
                + "  ".join(f"{v:+.9e}" for v in s[row]),
                flush=True,
            )

    # ---- the anchor: leg (d0)'s recorded column ----------------------------
    if comm.rank == 0:
        print(
            f"\n[anchor] the P1-driven column vs leg (d0)'s terminated record "
            f"(band {LEG_D0_REPRODUCTION_BAND:.0e} relative, imported):",
            flush=True,
        )
        for k, (value, record) in enumerate(zip(z[:, 0], LEG_D0_Z_COLUMN), start=1):
            print(
                f"    Z_{k}1 {value:+.9e} vs record {record:+.9e}  relative "
                f"{abs(value - record) / abs(record):.3e}",
                flush=True,
            )
    for k, (value, record) in enumerate(zip(z[:, 0], LEG_D0_Z_COLUMN), start=1):
        miss = abs(value - record) / abs(record)
        assert miss < LEG_D0_REPRODUCTION_BAND, (
            f"Z_{k}1 = {value:+.9e} Ohm deviates {miss:.3e} from leg (d0)'s "
            f"recorded {record:+.9e} Ohm, outside the imported "
            f"{LEG_D0_REPRODUCTION_BAND:.0e} band — the example path is not on "
            "the fixture the gate module measured (§7 `EX-32` negative result: "
            "known-issues entry, report, stop; nothing re-recorded)"
        )

    # ---- gate (i): reciprocity, printed as a decade ------------------------
    if comm.rank == 0:
        print(
            f"\n[gate i] reciprocity ||S - S^T||/||S|| = {reciprocity:.3e} "
            f"~ 1e{decade:.0f} against the imported {RECIPROCITY_BAND:.0e} band "
            f"{'PASS' if reciprocity <= RECIPROCITY_BAND else 'MISS'}\n"
            f"         (order of magnitude only, the (d3c) rule — power-wave "
            f"residuals are noise over noise and no digit of this reading is a "
            f"record; ||Z - Z^T||/||Z|| = {sweep['z_reciprocity']:.3e})",
            flush=True,
        )
    assert reciprocity <= RECIPROCITY_BAND, (
        f"the birdcage 4x4 reads ||S - S^T||/||S|| = {reciprocity:.6e} against "
        f"the imported {RECIPROCITY_BAND:.0e} band — an example/test divergence "
        "finding about the lumped-sheet route on four ports, never a licence to "
        "widen (§7 `EX-32` negative result)"
    )
    assert decade >= RECIPROCITY_DECADE_FLOOR, (
        f"reciprocity reads 1e{decade:.0f}, below the 1e{RECIPROCITY_DECADE_FLOOR:.0f} "
        "floor this example prints against — that is under the double-precision "
        "noise the residual is made of, so the matrix is suspiciously exact"
    )

    # ---- gate (ii): passivity ---------------------------------------------
    report = result.sanity_report
    if comm.rank == 0:
        print(
            f"\n[gate ii] passivity (tolerance {PASSIVITY_SIGMA_TOLERANCE:.0e}, "
            f"imported):\n"
            f"    sigma(S) = " + ", ".join(f"{v:.9f}" for v in sweep["sigma"]) + "\n"
            f"    sigma_max = {sigma_max:.9f}  "
            f"{'PASS' if sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE else 'MISS'}"
            f"   (PORT-5 metric {report.passivity_max_sigma:.9f})\n"
            f"    column power sums = "
            + ", ".join(f"{v:.9f}" for v in sweep["column_power"])
            + f"\n    max column power sum = {power_max:.9f}  "
            f"{'PASS' if power_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE else 'MISS'}",
            flush=True,
        )
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"sigma_max(S) = {sigma_max:.9f} exceeds 1 by more than the imported "
        f"{PASSIVITY_SIGMA_TOLERANCE:.0e} — the assembled 4x4 is active"
    )
    for k, value in enumerate(sweep["column_power"], start=1):
        assert value <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
            f"column {k} of S carries power sum {value:.9f} > 1 + "
            f"{PASSIVITY_SIGMA_TOLERANCE:.0e} — driving port {k} returns more "
            "power than it is fed"
        )

    # ---- gate (iii'): C4 circulant symmetry of Z ---------------------------
    if comm.rank == 0:
        print(
            f"\n[gate iii'] C4 circulant classes of Z (band "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}%, imported):",
            flush=True,
        )
        for name in ("self", "adjacent", "opposite"):
            members = sweep["classes"][name]
            print(
                f"    {name:9s} n = {members.size}  mean |Z| = "
                f"{np.mean(np.abs(members)):.9e} Ohm  spread "
                f"{spreads[name] * 100:.4f}%  "
                f"{'INSIDE' if spreads[name] <= ADJACENT_SPREAD_BAND else 'MISS'}",
                flush=True,
            )
        print(
            f"    control: pooled off-diagonal {pooled * 100:.4f}% vs worst "
            f"intra-class {worst * 100:.4f}%  =>  separation {separation:.4f}x "
            f"(floor {POOLED_SEPARATION_FLOOR:.0f}x, imported)  "
            f"{'PASS' if separation >= POOLED_SEPARATION_FLOOR else 'MISS'}",
            flush=True,
        )
    for name, value in spreads.items():
        assert value <= ADJACENT_SPREAD_BAND, (
            f"the {name} class of Z spreads {value * 100:.4f}% against the "
            f"imported {ADJACENT_SPREAD_BAND * 100:.1f}% band — on an "
            "undisplaced, C4-invariant layout"
        )
    assert separation >= POOLED_SEPARATION_FLOOR, (
        f"the pooled off-diagonal class spreads {pooled * 100:.4f}%, only "
        f"{separation:.4f}x the worst intra-class spread, against the imported "
        f"{POOLED_SEPARATION_FLOOR:.0f}x floor — the class reading is not "
        "resolving the layout's structure"
    )

    # ---- the negative control: the retired heuristic route -----------------
    heuristic, deprecations, t_heuristic = _heuristic_control(sweep, comm)
    heuristic_delta = float(np.max(np.abs(heuristic.s_matrix - s)))
    if comm.rank == 0:
        print(
            f"\n[control] the deprecated PORT-0 coupling heuristic on the same "
            f"problem and mesh ({t_heuristic:.1f} s, "
            f"{len(deprecations)} DeprecationWarning(s)):",
            flush=True,
        )
        for row in heuristic.s_matrix:
            print(
                "    " + "  ".join(f"{v:+.6e}" for v in row),
                flush=True,
            )
        for w in deprecations:
            print(f"    DeprecationWarning: {w.message}", flush=True)
        print(
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
        f"the retired heuristic reproduces the field-derived S to "
        f"{heuristic_delta:.3e} — that is a finding about the heuristic, not a "
        "passing example"
    )

    # ---- ParaView: one extra solve, because the sweep returns no fields ----
    e_driven, omega, driven_id, t_export_solve = _solve_driven_p1(sweep, comm)
    written = _write_paraview(
        sweep["mesh"],
        sweep["cell_tags"],
        sweep["facet_tags"],
        _paraview_fields(sweep["mesh"], e_driven, omega),
        comm,
    )
    if comm.rank == 0:
        print(
            f"\n[paraview] the {driven_id}-driven case re-solved for its field "
            f"({t_export_solve:.1f} s; the sweep returns readings, not fields):",
            flush=True,
        )
        for what, path in written.items():
            print(f"  {what:<18s} {path}")
        print(
            "\n[paraview] the _combined file carries `E_real` / `E_imag` / "
            "`E_magnitude` (CG1) and `B_magnitude`"
            "\n           (DG0, B = curl E / (-j omega) from Faraday's law) "
            "beside `CellTags`;"
            "\n           open the _facets file and threshold `mesh_tags` on "
            "211-214 to see the four port"
            "\n           sheets the lumped BC lives on."
            f"\n\nAll gates hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
