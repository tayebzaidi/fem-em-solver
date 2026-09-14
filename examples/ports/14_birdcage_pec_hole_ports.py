"""Example (`EX-54`): the birdcage as a PEC hole in ParaView.

`TH-15` step 3 (closed 2026-09-13) gated the gapped 4-leg birdcage meshed as a
**PEC hole** — the coil is cut out of the box entirely (no conductor cells),
its cavity wall is facet group ``BIRDCAGE_CONDUCTOR_SURFACE_TAG`` (401), and
that wall is PEC by construction because ``pec_facet_tags=None`` pins every
exterior facet (`TimeHarmonicProblem`'s default) and tag 401's facets are
themselves exterior on this mesh. Four lumped-sheet ports drive it exactly as
`PORT-9`/`PORT-11` drive the solid coil. `EX-50` showed the hole *mesh* only
(no solve, no ports); this is the first example that solves it.

**It asserts, and it does not re-implement** (the `ANS-1` rule). Every
record, band and helper below is imported from
``tests/validation/test_th15_birdcage_pec_hole.py`` (`TH-15` step 3's gate
module) — reciprocity (``RECIPROCITY_BAND``), passivity
(``PASSIVITY_SIGMA_TOLERANCE``), the C4 class spread (``ADJACENT_SPREAD_BAND``)
and the power identity (``POWER_IDENTITY_BAND``) are imported, never
restated, and asserted here exactly as the gate module asserts them, on the
identical construction (``_hole_rung``, the module's own fixture body, not a
copy of it).

**Rule (a) additive return keys, disclosed.** ``_hole_rung`` did not return
the mesh, tags or solved field — nothing an example needs to render
anything, since the gate module only ever reduces them to scalars. Five keys
were added to its return dict: ``mesh``, ``cell_tags``, ``wall_facet_tags``
(the mesh's own facet tags, carrying tag 401 — what the problem was built
with), ``sheet_facet_tags`` (the ports' narrowed sheet tags, a *different*
meshtags object) and ``fields``. Nothing existing was renamed, removed or
recomputed. The gate module was re-run green from `main` in this slot after
the change — see the guide's harness log for the rerun window.

**No copper, no Larmor-accuracy, no `TH-14` claim.** This is the *hole*
route only (an empty cavity, saline phantom, PEC wall) at 10 MHz; `TH-14`'s
copper surface-impedance hole (landed 2026-09-13, after this item was
opened) is a different fixture and is not imported here.

**Printed, not asserted (no pre-registered band):**

* the hole's 4x4 ``S`` beside `PORT-11`'s own solid sigma = 800 S/m 10 MHz
  record (``LEG_D_S_MATRIX_10MHZ``, imported), and ``max|Delta S|`` per C4
  class (self / adjacent / opposite) between them — an observational
  hole-vs-solid comparison, not a bracket or an accuracy claim;
* the cavity wall's ``|n x E|`` reading (an ``L2``-type average over facet
  group 401), predicted approx 0 up to the N1curl interpolation floor, since
  the wall is PEC by construction.

**Output.** ``paraview_output/ports_14_birdcage_pec_hole_ports_combined.xdmf``
— the mesh, ``CellTags`` (threshold on the phantom tag, `PHANTOM_CELL_TAG`),
a DG0 ``E_magnitude`` field (``|E|`` from the P1-drive phasor, real by
construction), and the ``facet_tags`` grid carrying facet group 401 (the
cavity wall) in the same file.

**Scope.** One fixture (the gapped 4-leg hole), one frequency (10 MHz), the
three imported gates plus the power identity. No absolute-accuracy,
resonance or tuning claim; no copper.

**Negative result protocol.** A red imported gate here while the gate module
holds it is an example/test divergence: a known-issues entry naming this
example, and a stop — never a re-record from the example side.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:14
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path
# so the gate module's constants, bands and fixture are imported rather than
# restated.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)

from tests.mesh.test_birdcage_port_tags import LEG_COUNT  # noqa: E402
from tests.validation.test_port_birdcage_four_port import (  # noqa: E402
    _circulant_classes,
)
from tests.validation.test_port_birdcage_larmor_gate import (  # noqa: E402
    LEG_D_S_MATRIX_10MHZ,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_gap_voltage_impedance import FREQUENCY_HZ  # noqa: E402
from tests.validation.test_th15_birdcage_pec_hole import (  # noqa: E402
    ADJACENT_SPREAD_BAND,
    PASSIVITY_SIGMA_TOLERANCE,
    POWER_IDENTITY_BAND,
    RECIPROCITY_BAND,
    _hole_rung,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "ports_14_birdcage_pec_hole_ports"


def _e_magnitude_dg0(e_complex, msh):
    """``|E|`` as a real DG0 field — what ParaView colours by.

    ``|E|^2`` is interpolated (a polynomial expression) and the square root
    is taken on the array afterwards, so no complex ``sqrt`` is ever formed
    (the same pattern as `materials/01_dodd_deeds_coil_loading.py`'s
    ``|J|`` field).
    """
    dg0 = fem.functionspace(msh, ("DG", 0))
    e_sq = fem.Function(dg0)
    e_sq.interpolate(
        fem.Expression(ufl.inner(e_complex, e_complex), dg0.element.interpolation_points)
    )
    e_mag = fem.Function(dg0, name="E_magnitude")
    e_mag.x.array[:] = np.sqrt(np.maximum(np.real(e_sq.x.array), 0.0))
    e_mag.x.scatter_forward()
    return e_mag


def _cavity_wall_n_cross_e(msh, facet_tags, e_complex, tag, comm):
    """``sqrt(int_wall |n x E|^2 dS / area)`` on exterior facet group ``tag``.

    Exterior facets carry a single-valued ``FacetNormal`` (no restriction
    needed, unlike the interior sheet forms this reuses the style of).
    Predicted approx 0 up to the N1curl interpolation floor: tag 401's
    facets are exterior and ``pec_facet_tags=None`` pins every exterior
    facet, so tangential ``E`` is Dirichlet-zero there by construction.
    """
    ds_wall = ufl.Measure("ds", domain=msh, subdomain_data=facet_tags, subdomain_id=(tag,))
    n = ufl.FacetNormal(msh)
    cross_val = ufl.cross(n, e_complex)
    num = complex(
        comm.allreduce(
            fem.assemble_scalar(fem.form(ufl.inner(cross_val, cross_val) * ds_wall)),
            op=MPI.SUM,
        )
    )
    area = float(
        np.real(comm.allreduce(fem.assemble_scalar(fem.form(1.0 * ds_wall)), op=MPI.SUM))
    )
    return float(np.sqrt(max(np.real(num), 0.0))), area


def _max_abs_delta_by_class(s_hole, s_solid):
    """``max|Delta S|`` per C4 class (self/adjacent/opposite) on ``S_hole - S_solid``."""
    delta = s_hole - s_solid
    classes = _circulant_classes(delta)
    return {name: float(np.max(np.abs(vals))) for name, vals in classes.items()}


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
        print("EX-54 -- the birdcage as a PEC hole in ParaView, 10 MHz", flush=True)
        print("=" * 78, flush=True)

    comm.Barrier()
    t0 = time.perf_counter()
    rung = _hole_rung(FREQUENCY_HZ)
    comm.Barrier()
    t_rung = time.perf_counter() - t0

    if comm.rank == 0:
        print(
            f"\n[fixture] {rung['cells']} cells, f = {FREQUENCY_HZ:.3e} Hz, "
            f"{t_rung:.1f} s at -n {comm.size}; tag 401: {rung['n_cavity']} owned "
            f"facets, {rung['n_cavity_interior']} not exterior",
            flush=True,
        )

    # ---- the three imported gates, asserted exactly as the gate module does ---
    assert rung["reciprocity"] <= RECIPROCITY_BAND, (
        f"hole ||S-S^T||/||S|| = {rung['reciprocity']:.3e} > {RECIPROCITY_BAND:.0e}"
    )
    sigma_max = float(np.max(rung["sigma"]))
    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"hole sigma_max(S) = {sigma_max:.12f} > 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e}"
    )
    for name, value in rung["spreads"].items():
        assert value <= ADJACENT_SPREAD_BAND, (
            f"hole class '{name}' spread {value * 100:.4f}% > "
            f"{ADJACENT_SPREAD_BAND * 100:.1f}%"
        )
    power_dev = abs(rung["p_in"] - rung["p_phantom"]) / abs(rung["p_phantom"])
    assert power_dev <= POWER_IDENTITY_BAND, (
        f"Re P_in {rung['p_in']:.9e} W vs phantom loss {rung['p_phantom']:.9e} W: "
        f"rel dev {power_dev:.3e} > {POWER_IDENTITY_BAND:.0e}"
    )

    if comm.rank == 0:
        sp = rung["spreads"]
        print(
            f"\n[gates] reciprocity {rung['reciprocity']:.3e} (band {RECIPROCITY_BAND:.0e}); "
            f"sigma_max {sigma_max:.9f} (band 1 + {PASSIVITY_SIGMA_TOLERANCE:.0e}); "
            f"class spreads self {sp['self'] * 100:.4f}% adjacent "
            f"{sp['adjacent'] * 100:.4f}% opposite {sp['opposite'] * 100:.4f}% "
            f"(band {ADJACENT_SPREAD_BAND * 100:.1f}%); power rel dev "
            f"{power_dev:.3e} (band {POWER_IDENTITY_BAND:.0e}) -- ALL GATES HOLD",
            flush=True,
        )
        for row in range(LEG_COUNT):
            print(
                "    S_hole_%dk = " % (row + 1)
                + "  ".join(f"{v:+.9e}" for v in rung["s"][row]),
                flush=True,
            )

    # ---- printed only: the hole's 4x4 beside the solid sigma=800 record -------
    delta_by_class = _max_abs_delta_by_class(rung["s"], LEG_D_S_MATRIX_10MHZ)
    if comm.rank == 0:
        print(
            "\n[printed, no band] solid sigma=800 S/m 10 MHz record "
            "(LEG_D_S_MATRIX_10MHZ, PORT-11, imported):",
            flush=True,
        )
        for row in range(LEG_COUNT):
            print(
                "    S_solid_%dk = " % (row + 1)
                + "  ".join(f"{v:+.9e}" for v in LEG_D_S_MATRIX_10MHZ[row]),
                flush=True,
            )
        print(
            "    max|Delta S| by C4 class: self "
            f"{delta_by_class['self']:.3e}  adjacent {delta_by_class['adjacent']:.3e}  "
            f"opposite {delta_by_class['opposite']:.3e} (PRINTED; no pre-registered "
            "band -- an observational hole-vs-solid comparison, not a bracket)",
            flush=True,
        )

    # ---- printed only: the cavity wall's |n x E| ------------------------------
    e_complex = rung["fields"].e_complex
    msh = rung["mesh"]
    wall_facet_tags = rung["wall_facet_tags"]
    n_cross_e_avg, wall_area = _cavity_wall_n_cross_e(
        msh, wall_facet_tags, e_complex, 401, comm
    )
    if comm.rank == 0:
        print(
            f"\n[printed, no band] cavity wall (tag 401) |n x E|: "
            f"sqrt(int|n x E|^2 dS / area) = {n_cross_e_avg:.3e} over area "
            f"{wall_area:.6e} m^2 (predicted approx 0 up to the N1curl "
            "interpolation floor -- the wall is PEC by construction, "
            "pec_facet_tags=None)",
            flush=True,
        )

    # ---- combined XDMF: |E| on the cell grid, facet_tags (tag 401) alongside --
    OUTPUT_DIR.mkdir(exist_ok=True)
    e_mag = _e_magnitude_dg0(e_complex, msh)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        rung["cell_tags"],
        {"E_magnitude": e_mag},
        comm=comm,
        facet_tags=wall_facet_tags,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    elapsed = time.perf_counter() - started
    if comm.rank == 0:
        print(
            f"\n[output] {path} -- CellTags (threshold PHANTOM_CELL_TAG="
            f"{PHANTOM_CELL_TAG} for |E| on the phantom), E_magnitude (DG0), "
            "facet_tags grid (threshold 401 for the cavity wall)",
            flush=True,
        )
        print(f"\n[timing] total {elapsed:.1f} s at -n {comm.size}", flush=True)
        print("\nAll imported gates hold.", flush=True)


if __name__ == "__main__":
    main()
