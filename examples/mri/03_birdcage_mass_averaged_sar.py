"""Example (`EX-53`): mass-averaged 10 g SAR on the coil-driven field.

The `§5.4` ramp's **output-quantity** angle on `MAT-4` step 4 (2026-09-06):
`mri:2` shows the C95.3 averaging operator on an *imposed* uniform field, and
`ports:9` shows the coil-driven quadrant *powers*. Nothing under
``examples/`` shows a mass-averaged SAR on a **solved coil field**, nor the
ball placement that turns the C4 identity into a statement about the drive
rather than about the mesh. This example is that picture: four single-drive
F-small birdcage solves on the finer-phantom rung, four 10 g averaging balls
sitting under the four legs, and the C4 covariance identity read off the
coil-driven field itself.

**Import, never restate.** Every constant — ``CENTRE_RADIUS_M``,
``WHOLE_PHANTOM_BALL_RADIUS_M``, ``EXACT_IDENTITY_RTOL``, the ball masses, the
quadrature degree, the C4 band through its import chain — comes from
``tests/validation/test_birdcage_sar_mass_averaged.py``. The construction
itself is **called, not re-implemented**: this example imports
``_build_mass_averaged``, the module-level function the gate's own pytest
fixture now wraps (a one-line rule-(a) lift, additive only — the fixture's
existing behaviour and every existing assertion are unchanged; the four new
return keys, ``mesh``/``cell_tags``/``rho_field``/``solves``, are what an
external caller needs and were not exposed before). Calling it here runs
*exactly* the gate's four curl-curl solves and 21 ``mass_averaged_sar`` calls
a second time in this process — not a comparison against a frozen number, a
re-execution of the same code path.

**Anchors (asserted, imported, never restated).** The four cyclic 10 g C4
pairs at the imported ``C4_COVARIANCE_BAND`` (5%; records 0.3303 / 0.0756 /
0.0574 / 0.3132% below); the whole-phantom ball reproducing the tagged
``½∫σ|E|²`` at ``EXACT_IDENTITY_RTOL`` (round-off — the same discrete
integral written two ways) and step 3f's own record at ``CG1_RECORD_RTOL``;
the four balls' containment inside the phantom exactly as the gate asserts
it; the mesh cell counts against ``FINE_CELL_COUNT`` / ``FINE_PHANTOM_CELL_COUNT``.

**Negative control (asserted for its sign, predicted for its size — rule
(e)).** The mis-paired *far-side* ball (``c_{k+2}`` under drive ``k``) must
read **outside** the band on all four drives — asserted, backed by the gate's
own measurement on this fixture
(``20260907T003548Z_MAT-4-step4.log:1943-1946``, and reproduced fresh in the
harness log this run wrote). Its ~86% size is **printed**, not asserted
(ceiling 100% — the ratio of two positive SARs cannot exceed it).

**Printed, not gated:** the four 1 g pairs and their pre-registered verdict
clause (the gate's own ``_one_gram_verdict``); the kernel-mass identity
against the closed form ``ρ·4πa³/3`` (predicted, 0.1% budget — the sphere
gate's finer ``h/a`` measurement does not transfer here); each drive's peak
10 g SAR over the four centres, labelled explicitly **not a C95.3 compliance
figure**.

**Scope.** 10 MHz, degree 1, one mesh, four single drives. No absolute SAR,
no C95.3 compliance or limit claim, no homogeneity, no Larmor, no
convergence claim. `MAT-4` stays 🟡; nothing here changes that.

**The pointwise SAR field this writes to ParaView uses the phantom's
physical, uniform ``PHANTOM_RHO_KG_PER_M3``** (not the gate's special
zero-mapped ``rho_field``, which exists only so a ball's *mass* integral
excludes non-phantom cells and would divide by zero everywhere outside the
phantom if used pointwise). This mirrors exactly how the gate's own
``tagged`` anchor computes ``mean_sar`` — ``rho=PHANTOM_RHO_KG_PER_M3``, a
scalar, not a field — so the two are the same choice, not a new one.

Run it through the example runner (the ``mri:`` group sources the complex
build automatically)::

    ./run_examples.sh -e mri:3

Output lands in ``examples/mri/paraview_output/``: open
``mri_03_birdcage_mass_averaged_sar_combined.xdmf``, threshold on
``AveragingBall`` (1-4 = the four 10 g balls) over the ``SAR`` colour map.

Measured 2026-09-07 (see the harness log this run's slot recorded): the P1
drive's whole-phantom identity, the four C4 pairs, and the four negative
controls all reproduced the gate's own log digit-for-digit.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path
# here so the ``tests.*`` gate modules can be imported (the `ANS-1` pattern
# every EX-* example follows: import the gate's constants, never restate
# them).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.setup_figure import write_setup_figure  # noqa: E402

from tests.validation.test_birdcage_b1_plus_map import (  # noqa: E402
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    PHANTOM_RHO_KG_PER_M3,
)
from tests.validation.test_birdcage_sar_fine_phantom import (  # noqa: E402
    FINE_CELL_COUNT,
    FINE_PHANTOM_CELL_COUNT,
    STEP3F_FINE_PRIMAL_PHANTOM_POWER_W,
)
from tests.validation.test_birdcage_sar_mass_averaged import (  # noqa: E402
    CENTRE_RADIUS_M,
    CONTROL_CEILING,
    CONTROL_PREDICTED,
    EXACT_IDENTITY_RTOL,
    WHOLE_PHANTOM_BALL_RADIUS_M,
    _build_mass_averaged,
)
from tests.mesh.test_birdcage_port_tags import PHANTOM_RADIUS  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
FIGURE_DIR = Path(__file__).resolve().parent / "figures"
BASENAME = "mri_03_birdcage_mass_averaged_sar"


def _pointwise_sar_field(mesh, e_complex, sigma_field):
    """``σ(x)|E(x)|²/(2ρ)`` as a DG0 field, ``ρ`` the phantom's physical density.

    A **scalar** ``PHANTOM_RHO_KG_PER_M3``, exactly the choice the gate's own
    ``tagged`` anchor makes for ``mean_sar`` — not the gate's zero-elsewhere
    ``rho_field``, which would divide by zero in every non-phantom cell if
    used here (it exists only to keep a ball's *mass* integral confined to
    phantom cells, never to weight a pointwise field).
    """
    expr = 0.5 * sigma_field * ufl.inner(e_complex, e_complex) / PHANTOM_RHO_KG_PER_M3
    dg0 = fem.functionspace(mesh, ("DG", 0))
    sar = fem.Function(dg0, name="SAR")
    sar.interpolate(fem.Expression(expr, dg0.element.interpolation_points))
    sar.x.array[:] = np.real(sar.x.array)
    sar.x.scatter_forward()
    return sar


def _averaging_ball_field(mesh, centres, radius):
    """DG0 integer field: 0 outside every ball, ``k + 1`` inside ball ``k``.

    Built with the same UFL ``conditional`` on squared distance
    ``mass_averaged_sar`` uses internally (`post/sar.py`), so the surface this
    field renders is the surface the operator actually integrated against —
    not a fresh geometric re-derivation that could silently disagree. The
    four 10 g balls sit close enough (``r0`` = 15 mm, ``a_10g`` ~ 13.4 mm)
    that adjacent balls overlap slightly; a later ``k`` wins the overlap in
    this rendering (cosmetic — no anchor depends on non-overlap).
    """
    x = ufl.SpatialCoordinate(mesh)
    value = ufl.as_ufl(0.0)
    for k in range(4):
        offset = x - ufl.as_vector([float(c) for c in centres[k]])
        inside = ufl.lt(ufl.real(ufl.dot(offset, offset)), float(radius) ** 2)
        value = ufl.conditional(inside, float(k + 1), value)

    dg0 = fem.functionspace(mesh, ("DG", 0))
    ball = fem.Function(dg0, name="AveragingBall")
    ball.interpolate(fem.Expression(value, dg0.element.interpolation_points))
    ball.x.array[:] = np.real(ball.x.array)
    ball.x.scatter_forward()
    return ball


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "this example needs the complex DolfinX build "
            "(source /usr/local/bin/dolfinx-complex-mode); the runner's `mri:` "
            "group sources it automatically"
        )

    if comm.rank == 0:
        print("=" * 72)
        print("EX-53 — mass-averaged 10 g SAR on the coil-driven field")
        print("=" * 72)
        print(
            "\n[scope] 10 MHz, degree 1, one mesh (finer-phantom rung), four "
            "single-leg drives. No absolute SAR, no C95.3 compliance claim, "
            "no Larmor, no convergence claim. MAT-4 stays yellow.",
            flush=True,
        )

    # ---- run the gate's own construction, verbatim -------------------------
    # `_build_mass_averaged` is the exact function the gate's pytest fixture
    # now wraps (rule-(a) lift, additive only). Calling it here re-executes
    # the four curl-curl solves and the 21 `mass_averaged_sar` calls in this
    # process; nothing below is a comparison against a frozen literal.
    solve_started = time.perf_counter()
    result = _build_mass_averaged()
    solve_seconds = time.perf_counter() - solve_started

    if comm.rank == 0:
        print(
            f"\n[gate reproduced] {result['cells']} cells "
            f"({result['phantom_cells']} tag-3), 4 solves + 21 operator calls "
            f"in {solve_seconds:.1f} s",
            flush=True,
        )

    # EX-57 setup figure: tag 1 is the birdcage conductor (legs + end rings,
    # copper by class-colour), tag 2 the surrounding air (hidden), tag 3 the
    # saline phantom (translucent), 100+i / 200+i the lower / upper halves of
    # port i's split lumped-sheet box in leg i's gap (the generator's
    # encoding, `tests/mesh/test_birdcage_port_sheets.py` PORT_LOWER /
    # PORT_UPPER). Sliced through z = 0 -- the plane the four leg gaps (and
    # so the port sheets) and `CENTRE_RADIUS_M`'s four 10 g ball centres all
    # sit in (the gate builds them at `(r0 cos, r0 sin, 0.0)`). No-op unless
    # FEM_EM_SETUP_FIGURES=1.
    port_names = {100 + i: f"port P{i} box (lower)" for i in range(1, 5)}
    port_names.update({200 + i: f"port P{i} box (upper)" for i in range(1, 5)})
    write_setup_figure(
        result["mesh"],
        result["cell_tags"],
        FIGURE_DIR / f"{BASENAME}_setup.png",
        region_names={1: "conductor", 2: "air", 3: "phantom (saline)", **port_names},
        hide_tags=(2,),
        translucent_tags=(3,),
        slice_normal=(0.0, 0.0, 1.0),
        slice_origin=(0.0, 0.0, 0.0),
        title="mri:3 -- mass-averaged 10 g SAR on the coil-driven field (MAT-4 step 4)",
        comm=comm,
    )

    # ---- anchor (iii): the mesh is step 3f0's mesh, exactly -----------------
    assert (result["cells"], result["phantom_cells"]) == (
        FINE_CELL_COUNT,
        FINE_PHANTOM_CELL_COUNT,
    ), (
        f"mesh mismatch: {result['cells']} / {result['phantom_cells']} cells "
        f"against the gate's {FINE_CELL_COUNT} / {FINE_PHANTOM_CELL_COUNT} — "
        "this is not step 3f0's fixture"
    )

    # ---- containment: every 10 g ball inside the phantom's CAD surface -----
    reach = CENTRE_RADIUS_M + result["radii"]["10 g"]
    assert reach < PHANTOM_RADIUS, (
        f"the 10 g ball reaches r = {reach:.6f} m, outside the phantom's "
        f"{PHANTOM_RADIUS:.6f} m CAD radius"
    )
    if comm.rank == 0:
        print(
            f"[containment] r0 + a_10g = {reach * 1e3:.4f} mm < phantom radius "
            f"{PHANTOM_RADIUS * 1e3:.1f} mm — ASSERTED",
            flush=True,
        )

    # ---- anchor (i): whole-phantom ball vs the tagged integral -------------
    whole = result["whole"]
    tagged = result["tagged"]
    power_miss = abs(whole["dissipated_power_w"] / tagged["dissipated_power_w"] - 1.0)
    record_miss = abs(
        whole["dissipated_power_w"] / STEP3F_FINE_PRIMAL_PHANTOM_POWER_W - 1.0
    )
    if comm.rank == 0:
        print(
            f"\n[anchor i] whole-phantom ball (r = {WHOLE_PHANTOM_BALL_RADIUS_M} m) "
            f"P1 drive: {whole['dissipated_power_w']:.9e} W vs tagged integral "
            f"{tagged['dissipated_power_w']:.9e} W [{power_miss:.3e} relative, "
            f"budget {EXACT_IDENTITY_RTOL:.0e}]"
            f"\n[anchor i] against step 3f's own record "
            f"{STEP3F_FINE_PRIMAL_PHANTOM_POWER_W:.9e} W [{record_miss:.3e} "
            f"relative, budget {CG1_RECORD_RTOL:.0e}]",
            flush=True,
        )
    assert power_miss <= EXACT_IDENTITY_RTOL, (
        f"whole-phantom ball {whole['dissipated_power_w']:.12e} W misses the "
        f"tagged integral {tagged['dissipated_power_w']:.12e} W by "
        f"{power_miss:.6e} > {EXACT_IDENTITY_RTOL:.0e}"
    )
    assert record_miss <= CG1_RECORD_RTOL, (
        f"whole-phantom power {whole['dissipated_power_w']:.9e} W misses step "
        f"3f's record {STEP3F_FINE_PRIMAL_PHANTOM_POWER_W:.9e} W by "
        f"{record_miss:.6e} > {CG1_RECORD_RTOL:.0e}"
    )

    # ---- anchor (ii): the four cyclic 10 g C4 pairs, the gate ---------------
    if comm.rank == 0:
        print(
            f"\n[anchor ii] the four cyclic 10 g C4 pairs, ASSERTED <= the "
            f"imported unmoved {C4_COVARIANCE_BAND * 100:.1f}% band; the "
            "mis-paired far-side control, sign ASSERTED > band, size PREDICTED "
            f"~{CONTROL_PREDICTED * 100:.0f}% (ceiling {CONTROL_CEILING * 100:.0f}%):",
            flush=True,
        )
    for k in range(4):
        ten = result["ten_pairs"][k]
        one = result["one_pairs"][k]
        control = result["control_pairs"][k]
        if comm.rank == 0:
            print(
                f"        k={k}->{(k + 1) % 4}  10 g {ten * 100:9.4f}%   "
                f"1 g {one * 100:9.4f}% (printed, not gated)   "
                f"control {control * 100:9.4f}%",
                flush=True,
            )
        assert ten <= C4_COVARIANCE_BAND, (
            f"10 g C4 pair k={k}->{(k + 1) % 4} reads {ten * 100:.4f}%, outside "
            f"the imported {C4_COVARIANCE_BAND * 100:.1f}% band"
        )
        assert control > C4_COVARIANCE_BAND, (
            f"far-side control at k={k} reads {control * 100:.4f}%, inside the "
            f"{C4_COVARIANCE_BAND * 100:.1f}% band — the C4 identity is not "
            "measuring covariance"
        )
        assert control <= CONTROL_CEILING, (
            f"far-side control at k={k} reads {control * 100:.4f}%, above the "
            f"{CONTROL_CEILING * 100:.0f}% ceiling a ratio of two positive SARs "
            "cannot exceed"
        )

    # ---- printed only: kernel mass, peaks, 1 g verdict -----------------------
    if comm.rank == 0:
        for label in ("1 g", "10 g"):
            row = "  ".join(
                f"{abs(result['kernel_mass'][label][k][0] / result['kernel_mass'][label][k][1] - 1.0) * 100:7.4f}%"
                for k in range(4)
            )
            print(
                f"[kernel mass, predicted not asserted, rule (e)] {label:<5} "
                f"errors {row}",
                flush=True,
            )
        for k in range(4):
            print(
                f"[peak, NOT a C95.3 compliance figure] drive k={k}: "
                f"{result['peaks'][k]:.9e} W/kg",
                flush=True,
            )
        print(
            f"[1 g verdict, printed not gated] {result['verdict']} — "
            f"{result['verdict_text']}",
            flush=True,
        )

    # ---- ParaView -------------------------------------------------------------
    mesh = result["mesh"]
    cell_tags = result["cell_tags"]
    p1_fields = result["solves"]["P1"]["fields"]
    sar_field = _pointwise_sar_field(mesh, p1_fields.e_complex, p1_fields.sigma_field)
    ball_field = _averaging_ball_field(
        mesh, result["centres"], result["radii"]["10 g"]
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        mesh,
        cell_tags,
        {"SAR": sar_field, "AveragingBall": ball_field},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {xdmf_path}"
            "\n[paraview] threshold `AveragingBall` (1-4 = the four 10 g balls) "
            "over the `SAR` (W/kg) colour map to see the balls sitting in the "
            "coil-driven field."
            f"\n\nAll anchors hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
