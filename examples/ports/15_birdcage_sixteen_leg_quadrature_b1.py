"""Example (`EX-55`): the 32-port ccw quadrature drive on the 16-leg birdcage.

`PORT-13`'s ring rung (`GEO-26` step 2's 16-leg, 32-ring-port geometry) is
driven through the *package* superposition entry point
(:func:`~fem_em_solver.ports.superposition.superpose_drives`) with
:func:`~fem_em_solver.ports.superposition.quadrature_phase_weights` applied
per ring at the 32 ring ports — the same route `POST-6` step 3 built to
extend the 4-leg quadrature drive (`ports:7`, `ports:13`) to the 16-leg
fixture. No existing example drives the 16-leg / 32-ring-port fixture in
quadrature.

**It asserts, and it does not re-implement** (the `ANS-1` rule, taken to the
fixture itself, `EX-33`'s precedent). Every record, band and helper below is
imported from ``tests/validation/test_port_drive_superposition.py``
(`POST-6` step 3's gate module) and its own upstream imports — nothing here
is restated. The gate module exposed its 32-drive build only as a
module-scoped pytest fixture (``ring_quadrature_case``), unusable outside
pytest collection; the licensed additive pattern (`EX-32`/`EX-33`) applies:
its body is lifted verbatim into a module-level function,
``_build_ring_quadrature_case``, which the fixture now calls — no behaviour
changed, and the gate module's own four ``test_step3_*`` tests read the
identical dict this example reads. Three more keys (``mesh``, ``cell_tags``,
``facet_tags``, ``drives``, ``cg1``, ``frequency_hz``, ``z0_ohm``,
``sheets``) were added to the returned dict, additive only, for the artifact
and the setup figure — nothing existing was touched.

**Anchors (asserted in-script, imported, never restated):**

* the sample set: ``n_valid`` >= ``MIN_SAMPLE_POINTS`` (printed count against
  the imported constant — the item's own trap, since the gate's sample set
  holds exactly 50);
* **(i)** the C16 rotation spread — worst of the fifteen ``R_m`` images,
  m = 1..15, of the ccw CG1 ``|B1+|`` map, asserted <= the imported
  ``C4_COVARIANCE_BAND`` (5%, `test_birdcage_b1_plus_map.py`);
* **(ii)** the mirror identity ``|B1-|_cw(Mx)`` vs ``|B1+|_ccw(x)``, same
  band;
* **(iii)** `PORT-16`'s exact discrete power identity ``P_src,exact =
  P_vol + P_sheet,exact`` on the superposed ccw field, asserted at the
  imported ``DISCRETE_IDENTITY_RTOL`` (1e-6).

**Negative control.** The §7 `EX-55` entry names no separate asserted
negative control for this item (unlike `EX-49`'s linear-drive C4 miss): the
gate module's own mis-paired cw comparison is *predicted, printed, never
asserted* there (§9 rule (e) — no record backs it on this fixture), so this
example reproduces that same printed-only reading rather than inventing an
assertion the gate module itself declines to make. What *is* an asserted
negative-adjacent reading here is band (i) and (ii) themselves: either one
failing is the control, since a mis-wired weight vector or sense would miss
them.

**Scope.** One fixture, 10 MHz, degree 1, the ccw ring drive only (cw is
built for the mirror identity but not asserted on its own). No homogeneity,
absolute-accuracy, resonance or tuning claim.

**Negative result protocol.** A miss on any of the three imported identities
through this example path while the gate module still holds them is an
example/test divergence (known-issues entry, stop) — never a re-record from
the example side.

Needs the complex DolfinX build. Run it through the example runner, which
sources complex mode for the ``ports:`` group automatically::

    ./run_examples.sh -e ports:15

Outputs
``paraview_output/ports_15_birdcage_sixteen_leg_quadrature_b1_combined.xdmf``
— the mesh, ``CellTags``, the 32 ring-sheet facet tags, and the real DG0
``|B1+|`` map of the ccw drive (``B1_plus_ccw``). Threshold ``CellTags`` on
the phantom tag and colour by ``B1_plus_ccw`` to see the C16-symmetric
map directly.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

_REPO_ROOT = Path(__file__).resolve().parents[2]
# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the gate module's constants, helpers and construction can be imported
# rather than restated.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post import b1_plus  # noqa: E402
from fem_em_solver.post.setup_figure import write_setup_figure  # noqa: E402

from tests.validation.test_birdcage_b1_plus_map import (  # noqa: E402
    C4_COVARIANCE_BAND,
    MIN_SAMPLE_POINTS,
)
from tests.validation.test_port_birdcage_lumped_column import (  # noqa: E402
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)
from tests.validation.test_port_drive_superposition import (  # noqa: E402
    STEP3_ENV,
    _build_ring_quadrature_case,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
FIGURE_DIR = Path(__file__).resolve().parent / "figures"
BASENAME = "ports_15_birdcage_sixteen_leg_quadrature_b1"


def _real_dg0_copy(field, name):
    """A fresh DG0 ``Function`` holding ``field``'s real part, for XDMF.

    XDMF carries no complex array (`EX-14`/`EX-17`); ``b1_plus`` already
    returns a real magnitude stored with zero imaginary part, so this only
    ever drops an exact zero (`EX-49`'s precedent, unchanged).
    """
    out = fem.Function(field.function_space, name=name)
    out.x.array[:] = np.real(np.asarray(field.x.array))
    out.x.scatter_forward()
    return out


def _write_combined(msh, cell_tags, facet_tags, fields, comm):
    OUTPUT_DIR.mkdir(exist_ok=True)
    path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        cell_tags,
        fields,
        comm=comm,
        facet_tags=facet_tags,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return path


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ports:` group)."
        )

    # This example *is* `POST-6` step 3's case; force the gate module's
    # environment gate on regardless of the ambient environment so the
    # fixture builds rather than the fixture's own pytest.skip firing (that
    # skip only matters under pytest collection).
    os.environ[STEP3_ENV] = "1"

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print(
            "EX-55 -- the 32-port ccw quadrature drive on the 16-leg "
            "birdcage, 10 MHz",
            flush=True,
        )
        print("=" * 78, flush=True)

    case = _build_ring_quadrature_case()

    if comm.rank == 0:
        print(
            f"\n[sample set] n_valid = {case['n_valid']} against the imported "
            f"MIN_SAMPLE_POINTS = {MIN_SAMPLE_POINTS}",
            flush=True,
        )
    assert case["n_valid"] >= MIN_SAMPLE_POINTS, (
        f"only {case['n_valid']} sample points are valid on every "
        f"rotated/mirrored image, against MIN_SAMPLE_POINTS = "
        f"{MIN_SAMPLE_POINTS}"
    )

    worst_m = case["worst_m"]
    worst = case["c16"][worst_m]
    if comm.rank == 0:
        print(
            f"\n[i] C16 rotation spread: worst {worst * 100:.4f}% at R_{worst_m} "
            f"(asserted <= C4_COVARIANCE_BAND {C4_COVARIANCE_BAND * 100:.1f}%)",
            flush=True,
        )
    assert worst <= C4_COVARIANCE_BAND, (
        f"|B1+|_ccw is not C16-invariant: R_{worst_m} reads {worst * 100:.4f}% "
        f"against the imported {C4_COVARIANCE_BAND * 100:.1f}% band"
    )

    if comm.rank == 0:
        print(
            f"\n[ii] mirror identity |B1-|_cw(Mx) vs |B1+|_ccw(x): "
            f"{case['mirror'] * 100:.4f}% (asserted <= "
            f"{C4_COVARIANCE_BAND * 100:.1f}%)",
            flush=True,
        )
    assert case["mirror"] <= C4_COVARIANCE_BAND, (
        f"the mirror identity reads {case['mirror'] * 100:.4f}% against the "
        f"imported {C4_COVARIANCE_BAND * 100:.1f}% band"
    )

    if comm.rank == 0:
        print(
            f"\n[iii] PORT-16's exact discrete power identity: relative "
            f"deviation {case['identity_dev']:.6e} (asserted <= "
            f"DISCRETE_IDENTITY_RTOL {case['identity_rtol']:g})",
            flush=True,
        )
    assert case["identity_dev"] <= case["identity_rtol"], (
        f"P_src,exact - P_vol - P_sheet,exact misses by "
        f"{case['identity_dev']:.6e} of P_src against "
        f"{case['identity_rtol']:g}"
    )

    if comm.rank == 0:
        print(
            "\n[negative control, PRINTED only -- the gate module's own "
            "reading, no record backs an assertion on this fixture]\n"
            f"    cw mis-paired |B1+|_cw(Mx) vs |B1+|_ccw(x) measured "
            f"{case['control'] * 100:.4f}% vs predicted "
            f"{case['predicted_control'] * 100:.4f}%; factor over the worst "
            f"C16 spread measured {case['control'] / worst:.2f}x",
            flush=True,
        )

    # ---- the setup figure (EX-57; opt-in, FEM_EM_SETUP_FIGURES=1) ----------
    region_names = {CONDUCTOR_CELL_TAG: "conductor", PHANTOM_CELL_TAG: "phantom"}
    for s in case["sheets"]:
        region_names[int(s["tag"])] = f"ring port {s['ordinal']}"
    write_setup_figure(
        case["mesh"],
        case["cell_tags"],
        FIGURE_DIR / f"{BASENAME}_setup.png",
        region_names=region_names,
        translucent_tags=(PHANTOM_CELL_TAG,),
        slice_normal=(0.0, 0.0, 1.0),
        title=(
            "ports:15 -- 16-leg birdcage, 32 ring ports, ccw quadrature drive "
            f"at {case['frequency_hz']:.3e} Hz"
        ),
        comm=comm,
    )

    # ---- the ccw |B1+| map, and the combined write --------------------------
    b1_plus_ccw = b1_plus(case["drives"]["ccw"].b_complex, name="B1_plus_ccw")
    fields = {"B1_plus_ccw": _real_dg0_copy(b1_plus_ccw, "B1_plus_ccw")}
    path = _write_combined(
        case["mesh"], case["cell_tags"], case["facet_tags"], fields, comm
    )

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {path}: mesh, CellTags, the 32 ring-sheet "
            "facet tags, `B1_plus_ccw` (DG0, phantom cells meaningful).",
            flush=True,
        )
        print(
            f"\nAll gates hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
