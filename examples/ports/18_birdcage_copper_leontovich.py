"""Example (`EX-59`): the copper birdcage — the surface loss density on the coil.

`TH-14` step 2 (closed 2026-09-13) gated the gapped 4-leg birdcage's cavity
wall (facet tag `BIRDCAGE_CONDUCTOR_SURFACE_TAG`, 401) with Jin §5.8.3's
third-kind surface-impedance term at copper conductivity, replacing the
cavity-wall Dirichlet pin `ports:14` (`EX-54`) used for the PEC hole. This
example is the first to render that loss on the coil itself: the copper
10 MHz reading of `TH-14` step 2's own fixture, reproduced to the printed
digit, plus a DG0 field naming exactly what it is — the facet-integrated
loss *per adjacent cell*, in watts, not a density.

**It asserts, and it does not re-implement** (the `ANS-1` rule,
`EX-32`/`EX-33` precedent). Every record, band and helper is imported from
``tests/validation/test_th14_birdcage_copper.py`` (`TH-14` step 2's gate
module) — no gate-module edit was needed, so there is no rule-(a) additive
lift and no gate re-run owed; the module-private helpers below are imported
directly by name, unchanged.

**The case.** `TH-14` step 2's 10 MHz copper branch only: the hole mesh
(``_sheets_build(True, as_hole=True)``), the outer-box facet group
(``_outer_box_tags``), the four lumped-sheet ports (``_build_ports``), one
copper 4-port S-parameter sweep with the Leontovich term
(``extra_bilinear_terms=[term]``), then the P1 field solve
(``run_lumped_sheet_port_case(..., return_fields=True,
extra_bilinear_terms=[term_cu])``) and the power accounting exactly as the
gate module's own ``ladder`` fixture, lines 303-326. The PEC sweep and the
σ ladder are not reproduced here — they are not in the §7 row.

**Anchors (asserted, imported bands, copper 10 MHz only):**

* ``RECIPROCITY_BAND`` on ``||S-S^T||/||S||``;
* ``σ_max(S) <= 1 + PASSIVITY_SIGMA_TOLERANCE``;
* each C4 class spread (self/adjacent/opposite) ``<= ADJACENT_SPREAD_BAND``;
* ``P_surf > 0``;
* the power-identity residual ``<= DISCRETE_IDENTITY_RTOL``.

**Reproduce-to-the-digit.** Every printed record here is the gate module's
own 10 MHz copper reading, compared against
``docs/testing/logs/20260914T021500Z_TH-14.log:1032`` (``Z_s``),
``:1054`` (``P_src``, ``ΣP_sheet``, ``P_phantom``, ``P_surf``, residual) and
``:1055`` (``P_coil/P_in``, ``P_phantom/P_in``). A miss beyond print
rounding is an example/test **divergence**: a known-issues entry and a
stop, never a re-record from the example side. There is no stored module
constant for these readings, so nothing asserts against them directly —
the assertions above are the gate's own bands, imported and evaluated on
this run's numbers.

**The facet field: DG0 on the adjacent cells, named as such.** The
Leontovich integrand ``½Re(1/Z_s)|n×E|²`` is integrated over facet tag 401
with a DG0 test function inserted (``fem.assemble_vector`` of the same
``ds_c`` form ``_surface_loss_w`` uses, with ``v`` multiplied in) — the
result is the **facet-integrated copper loss per adjacent cell, in watts**
(not a density; the field and its printed line and the guide all say so).
Its sum over owned dofs equals ``_surface_loss_w``'s scalar ``P_surf`` to
``DISCRETE_IDENTITY_RTOL`` by construction (DG0 partition of unity) — an
asserted consistency check, not an independent physics claim.

**Printed reference, not recomputed, no assert.** The σ = 800 S/m solid
control's share of input power on a *different* fixture (`TH-15` step 3c,
``docs/testing/logs/20260914T005452Z_TH-15-step3c.log:2787``) is held as
three literal numbers read from that log line, with the ratio computed
in-script and printed beside the copper reading here — never a band, never
recomputed from the solid fixture.

**No absolute copper-coil accuracy claim** (`ANS-6`): the copper number is
a model reading on this fixture, not a validated accuracy figure.

Needs the complex DolfinX build; the runner sources it for the ``ports:``
group automatically::

    ./run_examples.sh -e ports:18
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem, la

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.io.mesh import BIRDCAGE_CONDUCTOR_SURFACE_TAG  # noqa: E402
from fem_em_solver.core.cavity import surface_resistance_ohm  # noqa: E402
from fem_em_solver.ports.lumped import run_lumped_sheet_port_case  # noqa: E402
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep  # noqa: E402
from fem_em_solver.post.setup_figure import write_setup_figure  # noqa: E402

from tests.mesh.test_birdcage_port_sheets import _build as _sheets_build  # noqa: E402
from tests.mesh.test_birdcage_port_tags import LEG_COUNT  # noqa: E402
from tests.validation.test_birdcage_power_identity import (  # noqa: E402
    DISCRETE_IDENTITY_RTOL,
    _sheet_field_dissipation_w,
    _source_power_w,
)
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    PASSIVITY_SIGMA_TOLERANCE,
    _circulant_classes,
    _class_spread,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    ADJACENT_SPREAD_BAND,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ  # noqa: E402
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND  # noqa: E402
from tests.validation.test_th14_birdcage_copper import (  # noqa: E402
    COPPER_SIGMA,
    DRIVEN,
    OUTER_BOX_TAG,
    _build_ports,
    _leontovich_term,
    _outer_box_tags,
    _problem,
    _surface_loss_w,
    _sweep_record,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
FIGURE_DIR = Path(__file__).resolve().parent / "figures"
BASENAME = "ports_18_birdcage_copper_leontovich"

# `TH-15` step 3c solid control (σ = 800 S/m, a *different* fixture, 10 MHz),
# read verbatim off `docs/testing/logs/20260914T005452Z_TH-15-step3c.log:2787`.
# PRINTED REFERENCE ONLY -- never recomputed, never a band.
SOLID_800_CONTROL_LOG_READINGS = {
    "p_src": 3.143759587e-03,
    "p_sheets": 2.695481546e-03,
    "p_non_phantom": 4.482216632e-04,
}


def _e_magnitude_dg0(e_complex, msh):
    """``|E|`` as a real DG0 field (the ``ports:14`` pattern)."""
    dg0 = fem.functionspace(msh, ("DG", 0))
    e_sq = fem.Function(dg0)
    e_sq.interpolate(
        fem.Expression(ufl.inner(e_complex, e_complex), dg0.element.interpolation_points)
    )
    e_mag = fem.Function(dg0, name="E_magnitude")
    e_mag.x.array[:] = np.sqrt(np.maximum(np.real(e_sq.x.array), 0.0))
    e_mag.x.scatter_forward()
    return e_mag


def _coil_surface_loss_per_cell_w(msh, facet_tags, z_s, e, comm):
    """Facet-integrated copper loss ``½Re(1/Z_s)|n×E|²`` per *adjacent cell*, W.

    Not a density: this is the same integrand `_surface_loss_w` reduces to a
    scalar, with a DG0 test function inserted so each cell touching facet
    tag 401 keeps its own share. DG0 test functions restricted to a single
    exterior facet take the one adjacent cell's value, so no interior
    restriction ("+"/"-") ambiguity arises.
    """
    v0 = fem.functionspace(msh, ("DG", 0))
    v = ufl.TestFunction(v0)
    ds_c = ufl.Measure(
        "ds", domain=msh, subdomain_data=facet_tags, subdomain_id=BIRDCAGE_CONDUCTOR_SURFACE_TAG
    )
    n = ufl.FacetNormal(msh)
    re_y = fem.Constant(msh, default_scalar_type(0.5 * np.real(1.0 / complex(z_s))))
    # conj(v): complex-mode arity needs the test function conjugated; v is real DG0.
    form = fem.form(re_y * ufl.inner(ufl.cross(n, e), ufl.cross(n, e)) * ufl.conj(v) * ds_c)
    b = fem.assemble_vector(form)
    b.scatter_reverse(la.InsertMode.add)
    b.scatter_forward()
    loss = fem.Function(v0, name="coil_surface_loss_per_cell_W")
    loss.x.array[:] = np.real(b.array)
    loss.x.scatter_forward()
    index_map = v0.dofmap.index_map
    total = float(comm.allreduce(np.sum(np.real(b.array[: index_map.size_local])), op=MPI.SUM))
    return loss, total


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
        print("EX-59 -- the copper birdcage: surface loss density on the coil, 10 MHz", flush=True)
        print("=" * 78, flush=True)

    comm.Barrier()
    t0 = time.perf_counter()
    msh, cell_tags, facet_tags, _diag, t_mesh = _sheets_build(True, as_hole=True)
    tdim = msh.topology.dim
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()
    ncells = int(msh.topology.index_map(tdim).size_global)
    outer_tags, census = _outer_box_tags(msh, facet_tags, comm)
    tags_f, port_defs, specs = _build_ports(msh, cell_tags, comm)
    comm.Barrier()
    t_build = time.perf_counter() - t0

    if comm.rank == 0:
        print(
            f"\n[fixture] hole mesh {ncells} cells, mesh+ports {t_build:.1f} s at "
            f"-n {comm.size}; outer-box census {census}",
            flush=True,
        )

    # ---- setup figure (EX-57), on the built mesh, before any solve --------
    region_names = {2: "air", PHANTOM_CELL_TAG: "phantom"}
    for spec in specs:
        region_names[int(spec.facet_tag)] = f"port {spec.port_id}"
    write_setup_figure(
        msh,
        cell_tags,
        FIGURE_DIR / f"{BASENAME}_setup.png",
        region_names=region_names,
        hide_tags=(2,),
        translucent_tags=(PHANTOM_CELL_TAG,),
        slice_normal=(0.0, 0.0, 1.0),
        title="ports:18 -- the copper birdcage hole, Leontovich wall (tag 401)",
        comm=comm,
    )

    omega = 2.0 * np.pi * FREQUENCY_HZ
    r_s = surface_resistance_ohm(omega, COPPER_SIGMA)
    z_s = (1.0 + 1.0j) * r_s
    imp_problem = _problem(msh, cell_tags, FREQUENCY_HZ, outer_tags, (OUTER_BOX_TAG,))

    # ---- (a) the copper 4-port sweep, reciprocity/passivity/class-spread ---
    t1 = time.perf_counter()
    term = _leontovich_term(msh, facet_tags, z_s, omega)
    sw = _sweep_record(run_n_port_sparameter_sweep(
        imp_problem, port_defs, lumped_sheet_ports=specs, lumped_sheet_facet_tags=tags_f,
        extra_bilinear_terms=[term]))
    comm.Barrier()
    t_sweep = time.perf_counter() - t1

    assert sw["reciprocity"] <= RECIPROCITY_BAND, (
        f"copper ||S-S^T||/||S|| = {sw['reciprocity']:.3e} > {RECIPROCITY_BAND:.0e}"
    )
    sigma_max = float(np.max(sw["sigma"]))
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"copper sigma_max(S) = {sigma_max:.12f} > 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e}"
    )
    for name, value in sw["spreads"].items():
        assert value <= ADJACENT_SPREAD_BAND, (
            f"copper class '{name}' spread {value * 100:.4f}% > {ADJACENT_SPREAD_BAND * 100:.1f}%"
        )

    if comm.rank == 0:
        sp = sw["spreads"]
        print(
            f"\n[sweep] Z_s = {z_s.real:.6e}(1+j) ohm, sweep {t_sweep:.1f} s",
            flush=True,
        )
        for row in range(LEG_COUNT):
            print(
                "    S_cu_%dk = " % (row + 1)
                + "  ".join(f"{v:+.9e}" for v in sw["s"][row]),
                flush=True,
            )
        print(
            f"\n[gates] reciprocity {sw['reciprocity']:.9e} (band {RECIPROCITY_BAND:.0e}); "
            f"sigma_max(S) = {sigma_max:.12f} (band 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e}); "
            f"spreads self {sp['self'] * 100:.4f}% adjacent {sp['adjacent'] * 100:.4f}% "
            f"opposite {sp['opposite'] * 100:.4f}% (band {ADJACENT_SPREAD_BAND * 100:.1f}%) "
            "-- ALL IMPORTED GATES HOLD",
            flush=True,
        )

    # ---- (b) the P1 field solve, copper, and power accounting -------------
    term_cu = _leontovich_term(msh, facet_tags, z_s, omega)
    t1 = time.perf_counter()
    p1, fields = run_lumped_sheet_port_case(
        imp_problem, port_defs, specs, facet_tags=tags_f, driven_port_id=DRIVEN,
        verbose=False, return_fields=True, extra_bilinear_terms=[term_cu])
    comm.Barrier()
    t_p1 = time.perf_counter() - t1
    e = fields.e_complex
    sigma_f = fields.sigma_field
    dx = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags)

    def _vol(measure):
        form = fem.form(0.5 * sigma_f * ufl.inner(e, e) * measure)
        return float(np.real(comm.allreduce(fem.assemble_scalar(form), op=MPI.SUM)))

    acct = {"mesh": msh, "facet_tags": tags_f}
    sheet_objs = {sp.port_id: sp.sheet(driven=(sp.port_id == DRIVEN)) for sp in specs}
    p_sheets = sum(_sheet_field_dissipation_w(acct, sh, e, omega) for sh in sheet_objs.values())
    p_src = float(_source_power_w(acct, sheet_objs[DRIVEN], e, omega))
    p_total = _vol(dx)
    p_phantom = _vol(dx(PHANTOM_CELL_TAG))
    p_non_phantom = p_total - p_phantom
    p_surf = _surface_loss_w(msh, facet_tags, z_s, e, comm)

    identity_residual = abs(
        p_src - p_sheets - p_phantom - p_non_phantom - p_surf
    ) / abs(p_src)
    p_in = p_src - p_sheets

    assert p_surf > 0.0, p_surf
    assert identity_residual <= DISCRETE_IDENTITY_RTOL, identity_residual

    if comm.rank == 0:
        print(
            f"\n[field] P1 copper field solve {t_p1:.1f} s at -n {comm.size}",
            flush=True,
        )
        print(
            f"    P_src {p_src:.9e} W, sum P_sheet {p_sheets:.9e} W, "
            f"P_phantom {p_phantom:.9e} W, P_(Omega\\phantom) {p_non_phantom:.9e} W, "
            f"P_surf {p_surf:.9e} W; residual/P_src {identity_residual:.3e} "
            f"(ASSERTED <= {DISCRETE_IDENTITY_RTOL:g})",
            flush=True,
        )
        print(
            f"    PRINTED: P_coil/P_in = {p_surf / p_in:.6e}, "
            f"P_phantom/P_in = {p_phantom / p_in:.6e} (copper, f = {FREQUENCY_HZ:.3e} Hz)",
            flush=True,
        )

    # ---- printed reference: TH-15 step3c solid sigma=800 control ----------
    ref = SOLID_800_CONTROL_LOG_READINGS
    ref_p_in = ref["p_src"] - ref["p_sheets"]
    ref_share = ref["p_non_phantom"] / ref_p_in
    if comm.rank == 0:
        print(
            f"\n[printed, no band] P_coil/P_in (copper) = {p_surf / p_in:.6e} beside "
            f"P_(Omega\\phantom)/P_in (sigma=800 solid, TH-15 step3c "
            f"log:2787, PRINTED reference, not recomputed) = {ref_share:.6e}",
            flush=True,
        )

    # ---- the facet field: DG0 on the adjacent cells, named as such --------
    loss, p_surf_from_field = _coil_surface_loss_per_cell_w(msh, facet_tags, z_s, e, comm)
    field_residual = abs(p_surf_from_field - p_surf) / abs(p_surf)
    assert field_residual <= DISCRETE_IDENTITY_RTOL, (p_surf_from_field, p_surf, field_residual)
    if comm.rank == 0:
        print(
            f"\n[consistency] sum(coil_surface_loss_per_cell_W over owned dofs) = "
            f"{p_surf_from_field:.9e} W vs P_surf = {p_surf:.9e} W: rel dev "
            f"{field_residual:.3e} (true by construction, DG0 partition of unity; "
            f"ASSERTED <= {DISCRETE_IDENTITY_RTOL:g})",
            flush=True,
        )

    # ---- combined XDMF: |E| and the per-cell loss on the cell grid --------
    OUTPUT_DIR.mkdir(exist_ok=True)
    e_mag = _e_magnitude_dg0(e, msh)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        cell_tags,
        {"E_magnitude": e_mag, "coil_surface_loss_per_cell_W": loss},
        comm=comm,
        facet_tags=facet_tags,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    elapsed = time.perf_counter() - started
    if comm.rank == 0:
        print(
            f"\n[output] {path} -- CellTags, E_magnitude (DG0), "
            "coil_surface_loss_per_cell_W (DG0, watts per cell adjacent to tag 401, "
            "NOT a density), facet_tags grid (tag 401 the cavity wall)",
            flush=True,
        )
        print(f"\n[timing] total {elapsed:.1f} s at -n {comm.size}", flush=True)
        print("\nAll imported gates hold.", flush=True)


if __name__ == "__main__":
    main()
