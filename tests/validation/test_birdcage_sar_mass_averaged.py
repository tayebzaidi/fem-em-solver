"""`MAT-4` step 4 — mass-averaged SAR on the **coil-driven** field.

Every mass-averaged SAR figure this repo has is on an *imposed* field: step 2
gated the operator at m = 0.05 g on a uniform ``E``, step 3 closed the sizing
gap at the C95.3 1 g / 10 g masses on the R = 0.03 m lossy sphere (identity
exact, kernel mass 0.0120% / 0.0044%, ``quadrature_degree`` 16 required).  This
module applies the *same* operator, ``post.sar.mass_averaged_sar``, to the
**solved** four-drive F-small birdcage field on the finer-phantom rung — the
fixture `WF-6` step 3f built and step 3h gated — and asserts a C4 symmetry
identity of the 10 g averages at the band step 3h's gate already uses.

**Why the primal field and no estimator.**  The 2026-09-02 / 09-03 rulings put
the coil-driven SAR gate on *integrals of the primal* ``E`` (step 3g/3h: twelve
C4 quadrant-power pairs at ≤ 1.52%), not on the restricted CG1 estimator whose
pointwise identities miss the band.  ``mass_averaged_sar`` is exactly such an
integral — over a ball rather than a quadrant — so the estimator is **not** in
this step's path and there is no projection anywhere below.

**The construction.**  One mesh (``PHANTOM_RESOLUTION_FINE``, 120 499 cells,
2 746 of them tag 3), four single-drive solves, ρ as the DG0 field
``build_density_field`` gives with ρ = 1000 kg/m³ in the phantom and **0 in
every other tag** (the reason for the one-line permissiveness change in
``post/sar.py``: a mapped zero density is a region excluded from the averaging
*mass*, which is what makes anchor (i) below a statement about the phantom and
not about the ball).  Ball radii come from ``averaging_ball_radius`` at the
imported ``ONE_GRAM_KG`` / ``TEN_GRAM_KG`` — 6.204 mm / 13.365 mm at ρ = 1000 —
and ball centres are ``c_k = (r₀cos φ_k, r₀ sin φ_k, 0)`` at the four port
azimuths with **r₀ = 0.015 m**, so that ``r₀ + a₁₀g`` = 0.0284 m is inside the
phantom's own 0.03 m CAD radius (asserted): no ball straddles the phantom
surface, where the integrand is discontinuous.

**Anchors, asserted.**

* **(i) the exact whole-phantom identity.**  A ball centred at the origin of
  radius 0.0501 m — larger than the phantom's circumradius
  ``√(0.03² + 0.04²)`` = 0.05 m exactly, smaller than the coil's 0.066 m inner
  surface — returns, under the P1 drive, a ``dissipated_power_w`` equal to
  ``mean_sar(..., subdomain_ids=PHANTOM_CELL_TAG)``'s at rtol **1e-10**.  The
  two are the same discrete integrand (σ is zero in the air, so the ball's
  σ|E|² is supported exactly on the phantom cells) over the same cells, and
  both quadratures are exact for a degree-2 integrand, so this is an *exact*
  identity and its band is round-off.  It gates the operator's cell coverage
  on this fixture: a ball that misses cells, double-counts ghosts, or fails to
  reduce would land nowhere near 1e-10.  Asserted with it: that power against
  the fine module's own record ``STEP3F_FINE_PRIMAL_PHANTOM_POWER_W`` at that
  module's record rtol, and ``mass_kg`` = ρ × the phantom's *meshed* volume at
  1e-10.
* **(ii) the C4 identity at 10 g.**  Rotating the drive by one leg rotates the
  solved field by 90° about the coil axis, so the 10 g average at the
  correspondingly rotated centre is invariant:
  ``|SAR₁₀g(c_{k+1}; k+1) − SAR₁₀g(c_k; k)| / SAR₁₀g(c_k; k)`` ≤ the imported,
  unmoved ``C4_COVARIANCE_BAND`` (5%), four cyclic pairs.  This is the gate.
* **(iii) the mesh is step 3f₀'s mesh** — ``FINE_CELL_COUNT`` global cells and
  ``FINE_PHANTOM_CELL_COUNT`` tag-3 cells at exact equality, imported.  A
  dropped ``phantom_resolution`` would silently rebuild the coarse mesh and
  every reading here would be a different fixture's.

**Printed with a pre-registered verdict clause, never asserted.**

* the four 1 g pairs.  A 6.2 mm ball on a phantom meshed at h = 7.5 mm is a
  ~10-cell integral; the `WF-6` step-3h lesson says that is pointwise-class,
  predicted 2–10%, and it is **printed** so that a review — never this module
  and never the slot that runs it — decides whether 1 g is gateable here;
* each ball's ``mass_kg`` beside the closed-form ``ρ·4πa³/3``, with the
  imported ``KERNEL_MASS_BUDGET`` (0.1%) as a **predicted** comparison under
  §9 rule (e): the sphere gate measured 0.0120% / 0.0044% at ``h/a`` far finer
  than this coil mesh's, so that identity is not assumed to transfer;
* the peak of ``SAR₁₀g`` over the four centres for each drive — **not a C95.3
  compliance figure**, an absolute number on one unnormalised drive.

**Negative control (asserted for its sign, predicted for its size — rule (e)).**
The mis-paired centre — the *far-side* ball, ``SAR₁₀g(c_{k+2}; k)`` against
``SAR₁₀g(c_k; k)`` — must read **outside** the band on every one of the four
drives.  A single-leg drive is strongly asymmetric about the axis, so the ball
under the driven leg and the ball opposite it cannot agree; if they did, the
C4 identity above would be measuring "the field is nearly uniform" and not
covariance.  The *sign* is asserted; the *size* is predicted ~90% from step
3g's quadrant analogue (96.2 / 97.5 / 95.6%,
``20260902T213441Z_WF-6-step3g.log``) with a ceiling of 100% — the ratio of two
positive SARs cannot miss by more — and is printed beside the measurement,
never asserted.

**Scope.**  10 MHz, degree 1, one mesh, four single drives.  **No absolute SAR
claim, no C95.3 compliance or limit claim, no homogeneity, no Larmor, no
convergence claim, and no quadrature drive** (its four-quadrant spread is 0.46%
under any pairing — an identity that cannot fail is not a gate, 09-03 ruling).
What closes here is exactly: *mass-averaged 10 g SAR on the coil-driven field,
C4 identity at fixed h on F-small at 10 MHz, with the 1 g column a printed
record.*

Run (complex build required)::

    scripts/testing/run_and_log.sh MAT-4-step4 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 560 \\
       mpiexec -n 4 python3 -m pytest tests/environment \\
       tests/validation/test_birdcage_sar_mass_averaged.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import pytest

from fem_em_solver.post.sar import (
    averaging_ball_radius,
    build_density_field,
    mass_averaged_sar,
    mean_sar,
)

from tests.complex_mode import complex_only
from tests.mesh.helpers import global_cell_tag_set
from tests.mesh.test_birdcage_phantom_resolution import (
    PHANTOM_RESOLUTION_FINE,
    _global_tag_cell_count,
)
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.mesh.test_birdcage_port_tags import PHANTOM_HEIGHT, PHANTOM_RADIUS
from tests.validation.test_birdcage_b1_plus_map import (
    C4_COVARIANCE_BAND,
    CG1_RECORD_RTOL,
    PHANTOM_RHO_KG_PER_M3,
    _solve_driven,
)
from tests.validation.test_birdcage_b1_quadrature import (
    QUADRATURE_STEP_DEG,
    _port_index,
)
from tests.validation.test_birdcage_sar_fine_phantom import (
    FINE_CELL_COUNT,
    FINE_PHANTOM_CELL_COUNT,
    STEP3F_FINE_PRIMAL_PHANTOM_POWER_W,
)
from tests.validation.test_mass_averaged_sar_standard_masses import (
    KERNEL_MASS_BUDGET,
    ONE_GRAM_KG,
    QUADRATURE_DEGREE,
    TEN_GRAM_KG,
)
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep
from tests.validation.test_port_birdcage_lumped_column import PHANTOM_CELL_TAG

# The averaging-ball centre radius.  0.015 m puts the four centres under the
# four legs at half the phantom's radius; ``CENTRE_RADIUS_M + a_10g`` = 0.0284 m
# against the fixture's imported ``PHANTOM_RADIUS`` = 0.03 m is asserted below,
# which is what keeps every ball inside the phantom's CAD surface (the ball is a
# UFL conditional and the integrand jumps at that surface).
CENTRE_RADIUS_M = 0.015

# The whole-phantom ball of anchor (i).  The phantom is a cylinder of radius
# 0.03 m and height 0.08 m, so its circumradius is exactly
# sqrt(0.03**2 + 0.04**2) = 0.05 m; the coil's nearest conducting surface is the
# leg at ring radius 0.07 minus half the 0.012 leg width = 0.064 m, and the ring
# torus at 0.07 - 0.004 = 0.066 m.  0.0501 m therefore encloses the whole
# phantom and touches no conductor -- and since sigma is zero in the air, the
# ball's sigma|E|^2 is supported exactly on the phantom cells.
WHOLE_PHANTOM_BALL_RADIUS_M = 0.0501

# Anchor (i) is an exact discrete identity (the same integrand over the same
# cells, both quadratures exact for a degree-2 integrand), so its band is
# floating-point round-off over an MPI reduction, not a physics tolerance.
EXACT_IDENTITY_RTOL = 1.0e-10

# The negative control's *predicted* size, printed never asserted (rule (e)):
# step 3g's quadrant analogue on this same fixture read 96.2 / 97.5 / 95.6%
# (`20260902T213441Z_WF-6-step3g.log`).  The ratio of two positive SARs cannot
# exceed 100%, so nothing larger is claimable.
CONTROL_PREDICTED = 0.90
CONTROL_CEILING = 1.00

# The 1 g column's predicted class, printed never asserted (rule (e)): a 6.2 mm
# ball on a 7.5 mm phantom h is a ~10-cell integral, which step 3h's lesson puts
# in the pointwise class.
ONE_GRAM_PREDICTED_LOW = 0.02
ONE_GRAM_PREDICTED_HIGH = 0.10


def _one_gram_verdict(pairs, band):
    """The pre-registered clause for the **printed** 1 g column.

    Evaluated from the readings in a fixed precedence so the clause a review
    acts on cannot disagree with the table printed above it.  Nothing here is
    asserted: 1 g is a record in this step by design.
    """
    worst = max(pairs.values())
    if worst <= band:
        return "(a)", (
            f"the worst 1 g C4 pair reads {worst * 100:.4f}%, inside the "
            f"{band * 100:.1f}% band the 10 g column is gated at — gating 1 g "
            "on this fixture is the NEXT REVIEW's ruling, never in-slot"
        )
    if worst <= ONE_GRAM_PREDICTED_HIGH:
        return "(b)", (
            f"the worst 1 g C4 pair reads {worst * 100:.4f}%, outside the "
            f"{band * 100:.1f}% band but inside the predicted pointwise class "
            f"({ONE_GRAM_PREDICTED_LOW * 100:.0f}-"
            f"{ONE_GRAM_PREDICTED_HIGH * 100:.0f}%) — as predicted, a ~10-cell "
            "integral on this h; report, and the route to a 1 g gate is h"
        )
    return "(c)", (
        f"the worst 1 g C4 pair reads {worst * 100:.4f}%, above even the "
        f"predicted {ONE_GRAM_PREDICTED_HIGH * 100:.0f}% ceiling of the "
        "pointwise class — a reading neither the band nor the prediction "
        "covers; report as-is for the review, never forced into a clause"
    )


@pytest.fixture(scope="module")
def mass_averaged():
    """One finer-phantom mesh, four drives, and the C95.3 operator on each.

    Four curl-curl solves and no mass solve, no projection and no estimator:
    every number below is an integral of the primal ``E``.  ``mass_averaged_sar``
    is called 21 times — the 4x4 of 10 g averages (four centres x four drives),
    the four 1 g averages at each drive's own centre, and the one whole-phantom
    ball of anchor (i).
    """
    sweep = build_four_port_sweep(phantom_resolution=PHANTOM_RESOLUTION_FINE)
    msh = sweep["mesh"]
    comm = msh.comm
    cell_tags = sweep["cell_tags"]
    cells = int(sweep["cells"])
    phantom_cells = _global_tag_cell_count(msh, cell_tags, PHANTOM_CELL_TAG, comm)

    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    order = sorted(azimuths)
    indices = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in order
    }
    by_k = {indices[pid]: pid for pid in order}

    solves = {pid: _solve_driven(sweep, pid) for pid in order}

    # rho: 1000 kg/m3 in the phantom, 0 in every other tag.  The tag list is
    # MPI-reduced (``global_cell_tag_set``) because ``cell_tags.values`` is
    # rank-local and a tag can legitimately live on no rank of a partition.
    all_tags = global_cell_tag_set(msh, cell_tags)
    rho_field = build_density_field(
        msh,
        PHANTOM_RHO_KG_PER_M3,
        cell_tags=cell_tags,
        density_map={int(t): 0.0 for t in sorted(all_tags) if int(t) != PHANTOM_CELL_TAG},
    )

    radii = {
        "1 g": averaging_ball_radius(mass_kg=ONE_GRAM_KG, rho=PHANTOM_RHO_KG_PER_M3),
        "10 g": averaging_ball_radius(mass_kg=TEN_GRAM_KG, rho=PHANTOM_RHO_KG_PER_M3),
    }
    centres = {
        k: (
            CENTRE_RADIUS_M * float(np.cos(np.radians(azimuths[by_k[k]]))),
            CENTRE_RADIUS_M * float(np.sin(np.radians(azimuths[by_k[k]]))),
            0.0,
        )
        for k in range(4)
    }

    def _ball(pid, k, label):
        return mass_averaged_sar(
            solves[pid]["fields"].e_complex,
            sigma=solves[pid]["fields"].sigma_field,
            rho=rho_field,
            center=centres[k],
            radius=radii[label],
            comm=comm,
            quadrature_degree=QUADRATURE_DEGREE,
        )

    ten_gram = {(k, j): _ball(by_k[k], j, "10 g") for k in range(4) for j in range(4)}
    one_gram = {(k, k): _ball(by_k[k], k, "1 g") for k in range(4)}

    ten_pairs = {
        k: abs(
            ten_gram[((k + 1) % 4, (k + 1) % 4)]["averaged_sar_w_per_kg"]
            - ten_gram[(k, k)]["averaged_sar_w_per_kg"]
        )
        / ten_gram[(k, k)]["averaged_sar_w_per_kg"]
        for k in range(4)
    }
    one_pairs = {
        k: abs(
            one_gram[((k + 1) % 4, (k + 1) % 4)]["averaged_sar_w_per_kg"]
            - one_gram[(k, k)]["averaged_sar_w_per_kg"]
        )
        / one_gram[(k, k)]["averaged_sar_w_per_kg"]
        for k in range(4)
    }
    control_pairs = {
        k: abs(
            ten_gram[(k, (k + 2) % 4)]["averaged_sar_w_per_kg"]
            - ten_gram[(k, k)]["averaged_sar_w_per_kg"]
        )
        / ten_gram[(k, k)]["averaged_sar_w_per_kg"]
        for k in range(4)
    }

    # --- anchor (i): the whole-phantom ball against the tagged integral.
    whole = mass_averaged_sar(
        solves["P1"]["fields"].e_complex,
        sigma=solves["P1"]["fields"].sigma_field,
        rho=rho_field,
        center=(0.0, 0.0, 0.0),
        radius=WHOLE_PHANTOM_BALL_RADIUS_M,
        comm=comm,
        quadrature_degree=QUADRATURE_DEGREE,
    )
    tagged = mean_sar(
        solves["P1"]["fields"].e_complex,
        sigma=solves["P1"]["fields"].sigma_field,
        rho=PHANTOM_RHO_KG_PER_M3,
        cell_tags=cell_tags,
        comm=comm,
        subdomain_ids=PHANTOM_CELL_TAG,
    )

    kernel_mass = {
        label: {
            k: (
                (one_gram if label == "1 g" else ten_gram)[(k, k)]["mass_kg"],
                PHANTOM_RHO_KG_PER_M3 * 4.0 / 3.0 * np.pi * radii[label] ** 3,
            )
            for k in range(4)
        }
        for label in ("1 g", "10 g")
    }
    peaks = {
        k: max(ten_gram[(k, j)]["averaged_sar_w_per_kg"] for j in range(4))
        for k in range(4)
    }
    verdict, verdict_text = _one_gram_verdict(one_pairs, C4_COVARIANCE_BAND)

    if comm.rank == 0:
        print(
            f"\n[MAT-4 step 4] the C95.3 mass-averaging operator on the "
            f"COIL-DRIVEN field: {cells} cells ({phantom_cells} tag-3) at "
            f"phantom_resolution = {PHANTOM_RESOLUTION_FINE} m, f = "
            f"{sweep['problem'].frequency_hz:.3e} Hz, degree 1, "
            f"quadrature_degree {QUADRATURE_DEGREE} (imported from MAT-4 step 3)\n"
            f"    ASSERTED (iii) mesh == {FINE_CELL_COUNT} / "
            f"{FINE_PHANTOM_CELL_COUNT} exactly\n"
            f"    ball radii a_1g = {radii['1 g'] * 1e3:.4f} mm, a_10g = "
            f"{radii['10 g'] * 1e3:.4f} mm at rho = {PHANTOM_RHO_KG_PER_M3:.1f} "
            f"kg/m3; centres at r0 = {CENTRE_RADIUS_M * 1e3:.1f} mm on the four "
            f"port azimuths — containment r0 + a_10g = "
            f"{(CENTRE_RADIUS_M + radii['10 g']) * 1e3:.4f} mm < phantom radius "
            f"{PHANTOM_RADIUS * 1e3:.1f} mm, ASSERTED\n"
            f"    solve times "
            + ", ".join(f"{p} {solves[p]['solve_time']:.2f} s" for p in order),
            flush=True,
        )
        print(
            f"    (i) WHOLE-PHANTOM BALL (r = {WHOLE_PHANTOM_BALL_RADIUS_M} m > the "
            f"phantom circumradius 0.05 m), P1 drive:\n"
            f"        ball    1/2 int sigma|E|^2 = {whole['dissipated_power_w']:.12e} W, "
            f"mass {whole['mass_kg']:.12e} kg, volume {whole['volume_m3']:.9e} m3\n"
            f"        tagged  1/2 int sigma|E|^2 = {tagged['dissipated_power_w']:.12e} W, "
            f"volume {tagged['volume_m3']:.9e} m3\n"
            f"        relative difference "
            f"{abs(whole['dissipated_power_w'] / tagged['dissipated_power_w'] - 1.0):.6e} "
            f"(ASSERTED <= {EXACT_IDENTITY_RTOL:.0e}); mass vs rho*V_phantom "
            f"{abs(whole['mass_kg'] / (PHANTOM_RHO_KG_PER_M3 * tagged['volume_m3']) - 1.0):.6e} "
            f"(ASSERTED <= {EXACT_IDENTITY_RTOL:.0e}); against step 3f's record "
            f"{STEP3F_FINE_PRIMAL_PHANTOM_POWER_W:.9e} W "
            f"{abs(whole['dissipated_power_w'] / STEP3F_FINE_PRIMAL_PHANTOM_POWER_W - 1.0):.6e} "
            f"(ASSERTED <= {CG1_RECORD_RTOL:.0e})",
            flush=True,
        )
        print(
            f"    SAR_10g(c_j; drive k) [W/kg] — rows are drives, columns are "
            f"centres; the diagonal is the C4 orbit, the (k, k+2) entry is the "
            f"negative control:",
            flush=True,
        )
        for k in range(4):
            row = "  ".join(
                f"{ten_gram[(k, j)]['averaged_sar_w_per_kg']:.9e}" for j in range(4)
            )
            print(
                f"        k={k} ({by_k[k]})  {row}   peak over centres "
                f"{peaks[k]:.9e} W/kg  — NOT a C95.3 compliance figure",
                flush=True,
            )
        print(
            f"    (ii) the four cyclic 10 g C4 pairs |SAR(c_k+1; k+1) - "
            f"SAR(c_k; k)| / SAR(c_k; k), ASSERTED <= the imported unmoved "
            f"{C4_COVARIANCE_BAND * 100:.1f}% band:",
            flush=True,
        )
        for k in range(4):
            print(
                f"        k={k}->{(k + 1) % 4}  10 g {ten_pairs[k] * 100:9.4f}%   "
                f"1 g {one_pairs[k] * 100:9.4f}% (PRINTED NOT GATED)   "
                f"mis-paired control (c_{(k + 2) % 4}; {k}) "
                f"{control_pairs[k] * 100:9.4f}% (sign ASSERTED > band; size "
                f"PREDICTED ~{CONTROL_PREDICTED * 100:.0f}%, ceiling "
                f"{CONTROL_CEILING * 100:.0f}%)",
                flush=True,
            )
        print(
            f"    kernel mass int_B rho dV vs the closed form rho*4/3*pi*a^3 — "
            f"PREDICTED comparison at the imported "
            f"{KERNEL_MASS_BUDGET:.1%} budget (rule (e): the sphere gate measured "
            f"0.0120% / 0.0044% at a far finer h/a; NOT asserted here):",
            flush=True,
        )
        for label in ("1 g", "10 g"):
            row = "  ".join(
                f"{abs(kernel_mass[label][k][0] / kernel_mass[label][k][1] - 1.0) * 100:7.4f}%"
                for k in range(4)
            )
            print(
                f"        {label:<5} closed form "
                f"{kernel_mass[label][0][1] * 1e3:.6f} g   errors  {row}",
                flush=True,
            )
        print(
            f"    PRE-REGISTERED 1 g VERDICT: {verdict} — {verdict_text}\n"
            "    SCOPE: 10 MHz, degree 1, one mesh, four single drives.  NO "
            "absolute SAR, NO C95.3 compliance or limit claim, no homogeneity, "
            "no Larmor, no convergence claim, no quadrature drive.",
            flush=True,
        )

    return {
        "cells": cells,
        "phantom_cells": phantom_cells,
        "radii": radii,
        "centres": centres,
        "ten_gram": ten_gram,
        "one_gram": one_gram,
        "ten_pairs": ten_pairs,
        "one_pairs": one_pairs,
        "control_pairs": control_pairs,
        "whole": whole,
        "tagged": tagged,
        "kernel_mass": kernel_mass,
        "peaks": peaks,
        "verdict": verdict,
        "verdict_text": verdict_text,
    }


@complex_only
def test_the_operator_ran_on_step_3f0s_finer_phantom_mesh(mass_averaged):
    """Anchor (iii): 120 499 cells, 2 746 of them tag 3, at exact equality.

    Imported from `WF-6` step 3f, never restated.  ``build_four_port_sweep``
    would silently rebuild the 116 085-cell coarse default if the
    ``phantom_resolution`` passthrough were dropped anywhere, and then every
    reading in this module would belong to a different fixture.  gmsh is
    deterministic for a fixed input, so the bound is equality; the tag-3 count
    is ``size_local``-restricted and ``MPI.SUM``-reduced.
    """
    assert (mass_averaged["cells"], mass_averaged["phantom_cells"]) == (
        FINE_CELL_COUNT,
        FINE_PHANTOM_CELL_COUNT,
    ), (
        f"the sweep meshed to {mass_averaged['cells']} cells with "
        f"{mass_averaged['phantom_cells']} in tag 3, not step 3f0's "
        f"{FINE_CELL_COUNT} / {FINE_PHANTOM_CELL_COUNT}"
    )


@complex_only
def test_every_averaging_ball_lies_inside_the_phantom(mass_averaged):
    """The containment the whole construction rests on: ``r₀ + a₁₀g`` < 0.03 m.

    The averaging ball is a UFL ``conditional`` on the spatial coordinate and
    the integrand jumps at the phantom's surface (σ inside, 0 outside).  A ball
    that straddled that surface would average a discontinuous integrand and its
    C4 identity would measure the mesh's rendering of a CAD surface rather than
    the field's symmetry.  ``PHANTOM_RADIUS`` is imported from the fixture's own
    generator call, not restated.
    """
    reach = CENTRE_RADIUS_M + mass_averaged["radii"]["10 g"]
    assert reach < PHANTOM_RADIUS, (
        f"the 10 g ball reaches r = {reach:.6f} m from the axis, outside the "
        f"phantom's {PHANTOM_RADIUS:.6f} m CAD radius"
    )
    for k, centre in mass_averaged["centres"].items():
        assert abs(centre[2]) + mass_averaged["radii"]["10 g"] < 0.5 * PHANTOM_HEIGHT, (
            f"centre {k} at z = {centre[2]:.6f} m puts the 10 g ball through the "
            "phantom's flat face"
        )


@complex_only
def test_the_whole_phantom_ball_reproduces_the_tagged_integral(mass_averaged):
    """Anchor (i): the operator's cell coverage, exact to round-off.

    ``mass_averaged_sar`` integrates ``½σ|E|²`` over the whole mesh weighted by
    the ball indicator; ``mean_sar`` integrates the same expression over the
    tag-3 cells.  σ is zero everywhere but the phantom and the conductor, and a
    ball of radius 0.0501 m encloses the phantom (circumradius 0.05 m exactly)
    and reaches no conductor (nearest surface 0.064 m), so the two forms are
    the *same* discrete integral written two ways — both quadratures being
    exact for the degree-2 integrand ``σ|E|²`` of a degree-1 N1curl field.  The
    band is therefore round-off over an MPI reduction, not physics: a miss at
    1e-10 is a defect in the operator's cell coverage (missed cells,
    double-counted ghosts, an unreduced local sum), which is exactly what this
    anchor exists to catch, and is a known-issues entry rather than a band to
    widen.
    """
    whole = mass_averaged["whole"]
    tagged = mass_averaged["tagged"]
    power_miss = abs(whole["dissipated_power_w"] / tagged["dissipated_power_w"] - 1.0)
    assert power_miss <= EXACT_IDENTITY_RTOL, (
        f"the enclosing ball absorbs {whole['dissipated_power_w']:.12e} W against "
        f"the tagged integral's {tagged['dissipated_power_w']:.12e} W — relative "
        f"{power_miss:.6e} > {EXACT_IDENTITY_RTOL:.0e}"
    )
    mass_miss = abs(
        whole["mass_kg"] / (PHANTOM_RHO_KG_PER_M3 * tagged["volume_m3"]) - 1.0
    )
    assert mass_miss <= EXACT_IDENTITY_RTOL, (
        f"the ball's mass {whole['mass_kg']:.12e} kg is not rho times the "
        f"phantom's meshed volume {PHANTOM_RHO_KG_PER_M3 * tagged['volume_m3']:.12e} "
        f"kg — relative {mass_miss:.6e} > {EXACT_IDENTITY_RTOL:.0e}; with rho = 0 "
        "outside tag 3 these can differ only if the ball misses phantom cells"
    )


@complex_only
def test_the_whole_phantom_power_reproduces_step_3fs_record(mass_averaged):
    """Anchor (i), second half: the same fixture's own primal record.

    ``STEP3F_FINE_PRIMAL_PHANTOM_POWER_W`` is `WF-6` step 3f's reading of
    ``½∫_tag3 σ|E_P1|²`` on this very mesh, imported at that module's record
    rtol.  It ties this module's four solves to the gated ones: a different
    drive normalisation, a different frequency or a different sheet impedance
    would reproduce every symmetry identity here and miss this number.
    """
    reading = mass_averaged["whole"]["dissipated_power_w"]
    miss = abs(reading / STEP3F_FINE_PRIMAL_PHANTOM_POWER_W - 1.0)
    assert miss <= CG1_RECORD_RTOL, (
        f"the P1 phantom power reads {reading:.9e} W against step 3f's record "
        f"{STEP3F_FINE_PRIMAL_PHANTOM_POWER_W:.9e} W (relative {miss:.6e} > "
        f"{CG1_RECORD_RTOL:.0e}) — this is not step 3f's solve"
    )


@complex_only
@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_the_ten_gram_average_is_c4_covariant(mass_averaged, k):
    """**The gate.** The 10 g mass-averaged SAR follows the drive around the coil.

    Driving leg ``k+1`` instead of leg ``k`` rotates the solved field by 90°
    about the coil axis (the fixture is C4-symmetric by construction and its
    ports sit on the 90° grid, which ``_port_index`` checks), so the mass
    average over the ball at the correspondingly rotated centre must be the
    same number.  It is a covariance identity of the *operator applied to a
    solved field*, not of the operator alone, and it is scored against
    ``C4_COVARIANCE_BAND`` — **imported from step 1d and unmoved**, the same 5%
    the step-3h integral gate uses.  A pair above it is the finding that the
    ball average at this ``h`` is not yet a gate: a known-issues entry with all
    readings, never a widened band.
    """
    reading = mass_averaged["ten_pairs"][k]
    assert reading <= C4_COVARIANCE_BAND, (
        f"the 10 g C4 pair k={k}->{(k + 1) % 4} reads {reading * 100:.4f}%, "
        f"outside the imported {C4_COVARIANCE_BAND * 100:.1f}% band "
        f"(SAR {mass_averaged['ten_gram'][(k, k)]['averaged_sar_w_per_kg']:.9e} vs "
        f"{mass_averaged['ten_gram'][((k + 1) % 4, (k + 1) % 4)]['averaged_sar_w_per_kg']:.9e} "
        "W/kg)"
    )


@complex_only
@pytest.mark.parametrize("k", [0, 1, 2, 3])
def test_the_far_side_ball_does_not_agree(mass_averaged, k):
    """The negative control: the mis-paired centre must miss the band.

    Under a single-leg drive the field is strongly asymmetric about the axis, so
    the 10 g average under the driven leg and the one diametrically opposite it
    cannot agree.  If they did, the C4 identity above would be reporting "the
    field is nearly uniform over the phantom" and would pass on a solver that
    had lost the drive entirely.  Only the **sign** is asserted (rule (e)); the
    size is predicted ~90% from step 3g's quadrant analogue on this fixture
    (96.2 / 97.5 / 95.6%, ``20260902T213441Z_WF-6-step3g.log``) with a 100%
    ceiling, and is printed beside the measurement.
    """
    reading = mass_averaged["control_pairs"][k]
    assert reading > C4_COVARIANCE_BAND, (
        f"the far-side ball (c_{(k + 2) % 4} under drive {k}) agrees with the "
        f"driven-side ball to {reading * 100:.4f}%, inside the "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band — the C4 identity above is not "
        "measuring covariance"
    )
