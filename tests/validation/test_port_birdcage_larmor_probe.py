"""`PORT-11` step 1 — one 64 MHz solve on the loaded gapped birdcage, priced.

`PORT-9` closed on 2026-08-25 **at 10 MHz**: the lumped-sheet port model, the
gapped `GEO-19` step-B birdcage, four ``f = 0.5`` sheets terminated at
``Z_p = z0 = 50 Ω``, three gates (reciprocity, passivity, C4 class spread) and a
geometric negative control.  The mission's ports are at 64/128 MHz, where the
displacement current in the saline load is no longer negligible against the
conduction current — at the `TH-10` saline values the loss tangent
``σ/(ωε)`` is ``1.8`` at 64 MHz against ``11.5`` at 10 MHz.  Nothing is
reformulated here.  What this module measures is **whether the fixture that
gated at 10 MHz can be afforded and resolved at 64 MHz at all**, before a
heavy 4×4 sweep is commissioned against it (§7 `PORT-11` step 1; §9 item 1,
2026-08-25 18:00 review).

**This is a priced probe, not a gate.**  No reciprocity, passivity, circulant,
resonance or tuning claim is made at 64 MHz, and `PORT-11` stays 🧪 whatever
this module prints.  Step 2 — the 4×4 at 64 MHz under `PORT-9` step 3's three
unchanged gates — is commissioned off this price by a review, never in-slot.

**What it prints** (§7 step 1's list):

* cells per skin depth ``δ`` in the phantom, and cells per wavelength ``λ`` in
  the phantom and in air — the two resolution readings that actually change
  when the frequency does (MUMPS cost is mesh-bound; the physics is not);
* summed ``ru_maxrss`` across ranks;
* ``|Im P| / Re P`` at the driven port;
* column 1 of ``Z`` at 64 MHz, beside the same column at 10 MHz.

**The anchor / negative control (they are the same measurement).**  The 10 MHz
solve runs in this module, on **this** mesh through **this** code path, and must
reproduce `PORT-9` leg (d0)'s recorded 50 Ω column
(``LEG_D0_Z_COLUMN``, imported — never restated) to ``1e-6`` relative.  The
frequency is the only knob this module turns, so if the 10 MHz column moves,
the harness changed and nothing the 64 MHz solve prints is comparable to
anything `PORT-9` recorded.  The band is looser than the four-port module's
own ``1e-9`` print-precision band deliberately: that module asserts the record
against itself, this one asserts that a *different module* on the same mesh
lands on it, and 1e-6 is the pre-stated figure in §9 item 1.

**The stop rule (pre-stated, §7 step 1, binding).**  ``cells/δ`` in the phantom
below ~2 at this mesh is a **resolution finding, never a band question**: it is
gated below at ``PHANTOM_CELLS_PER_DELTA_FLOOR`` and a miss means the follow-on
is a `GEO` phantom-sizing chunk, not step 2.  Nothing here may be widened to
make that assertion pass.

**Named limitation on ``|Im P|/Re P``.**  ``run_lumped_sheet_port_case`` returns
per-port ``V``/``I`` and no fields, so the volume integral ``½∫σE·Ē`` the
`TH-11`/`TH-12` family bound is defined on cannot be formed from its return
value.  What is printed here is the **driven port's terminal complex power**
``P = ½·V₁·conj(I₁)`` — a different quantity with a different meaning: its
imaginary part is the reactive power the coil stores, which at 64 MHz is
physics, not numerical noise, and is exactly what a tuning chunk will want.  It
is printed, never gated.  Surfacing fields from the lumped-sheet route is
unscoped.

Cost: standard tier, ``-n 2``, one mesh (~21 s) and two solves (leg (c) priced
7.55 s/solve on this mesh class at 10 MHz; MUMPS is mesh-bound, so 64 MHz
should price near it — *measured* below, which is the point).

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-11-step1 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 400 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_birdcage_larmor_probe.py -v -s'"
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

import dolfinx

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.io.mesh import _interface_facet_tags
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.lumped import LumpedSheetPortSpec, run_lumped_sheet_port_case
from fem_em_solver.utils.analytical import complex_permittivity
from fem_em_solver.utils.constants import EPSILON_0, MU_0

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheets import (
    PORT_LOWER,
    PORT_UPPER,
    SHEET_IFACE,
    _build,
    _sheet_axes,
)
from tests.mesh.test_birdcage_port_tags import LEG_COUNT
from tests.mesh.test_two_torus_port_facets import _facet_group_area
from tests.mesh.test_two_torus_port_sheet import _sheet_extents, _sheet_facet_count
from tests.validation.test_lossy_sphere_degree2 import _rss_peak_bytes
from tests.validation.test_lossy_sphere_fullwave import (
    FREQUENCY_64_HZ,
    SALINE_EPSILON_R,
    SALINE_SIGMA,
)
from tests.validation.test_port_birdcage_four_port import (
    LEG_D0_Z_COLUMN,
    TERMINATED_PORT_IMPEDANCE_OHM,
)
from tests.validation.test_port_birdcage_lumped_column import (
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
    STEP2_CELL_COUNT,
    STEP2_CELL_COUNT_BAND,
    _narrowed_transverse,
    _sheet_bbox_centre,
)
from tests.validation.test_port_gap_voltage_impedance import (
    FREQUENCY_HZ,
    SIGMA_WIRE_S_PER_M,
)
from tests.validation.test_port_lumped_narrowed_sheet import GATED_WIDTH_FRACTION

# The air region of the birdcage port domain (`GEO-18`'s partition: 1 conductor,
# 2 air, 3 phantom).  This fixture has **no separate vessel-wall region** — the
# phantom is a bare cylinder — so §7's "cells/λ in air and wall" is reported
# here as air and phantom, and the absence is stated rather than papered over.
AIR_CELL_TAG = 2

# **The anchor band**, pre-stated in §9 item 1 (2026-08-25 18:00 review): the
# 10 MHz leg of this module must land on leg (d0)'s recorded column to this
# relative deviation.  Not a physics tolerance and not widenable — if it misses,
# the harness moved and the 64 MHz numbers are not comparable to `PORT-9`.
FREQUENCY_CONTROL_BAND = 1.0e-6

# **The stop rule**, pre-stated in §7 `PORT-11` step 1: fewer than this many
# cells per skin depth in the phantom at 64 MHz is a resolution finding about
# the mesh, and the follow-on is a `GEO` phantom-sizing chunk, not step 2.
PHANTOM_CELLS_PER_DELTA_FLOOR = 2.0


def _propagation_constants(epsilon_r, sigma, frequency_hz):
    """``(α, β, δ, λ)`` of the lossy medium in the ``e^{+jωt}`` convention.

    ``k = ω·sqrt(μ₀ε₀ε_c)`` with ``ε_c = εᵣ − j·σ/(ωε₀)``
    (:func:`complex_permittivity`, imported — the sign convention is part of the
    `TH-1` spec and is not restated here).  The physical branch is the one that
    decays along the direction of travel, i.e. ``Im k < 0``; the attenuation
    constant is ``α = −Im k`` and the phase constant ``β = Re k``, so the skin
    depth is ``1/α`` and the wavelength ``2π/β``.  For ``σ = 0`` this reduces to
    ``α = 0`` and the free-space wavelength, which is why air goes through the
    same function rather than a second formula.
    """
    omega = 2.0 * np.pi * float(frequency_hz)
    eps_c = complex_permittivity(epsilon_r, sigma, frequency_hz)
    k = omega * np.sqrt(MU_0 * EPSILON_0 * eps_c)
    if k.imag > 0.0:
        k = -k
    alpha = -float(k.imag)
    beta = float(k.real)
    return {
        "alpha": alpha,
        "beta": beta,
        "delta": (1.0 / alpha) if alpha > 0.0 else float("inf"),
        "lambda": (2.0 * np.pi / beta) if beta > 0.0 else float("inf"),
        "loss_tangent": (
            sigma / (omega * EPSILON_0 * epsilon_r) if epsilon_r > 0.0 else float("inf")
        ),
    }


def _tag_cell_size(msh, cell_tags, tag, comm):
    """Mean and max cell diameter over the cells carrying ``tag``, globally.

    ``cell_tags.find`` is rank-local and includes ghosts, so the owned cells are
    filtered off the index map before ``dolfinx.cpp.mesh.h`` is called and the
    mean is formed from globally reduced (sum, count) — the rank-safety rule.
    """
    tdim = msh.topology.dim
    n_owned = msh.topology.index_map(tdim).size_local
    local = np.asarray(cell_tags.find(tag), dtype=np.int32)
    local = local[local < n_owned]
    if local.size:
        h_local = dolfinx.cpp.mesh.h(msh._cpp_object, tdim, local)
        h_sum = float(np.sum(h_local))
        h_max = float(np.max(h_local))
        h_min = float(np.min(h_local))
    else:
        h_sum, h_max, h_min = 0.0, -np.inf, np.inf
    count = int(comm.allreduce(int(local.size), op=MPI.SUM))
    h_sum = float(comm.allreduce(h_sum, op=MPI.SUM))
    h_max = float(comm.allreduce(h_max, op=MPI.MAX))
    h_min = float(comm.allreduce(h_min, op=MPI.MIN))
    assert count > 0, f"cell tag {tag} has no owned cells on any rank"
    return {"cells": count, "h_mean": h_sum / count, "h_max": h_max, "h_min": h_min}


@pytest.fixture(scope="module")
def larmor_probe():
    """One mesh; two 50 Ω lumped-sheet solves, 10 MHz (control) then 64 MHz."""
    comm = MPI.COMM_WORLD
    ports_idx = list(range(1, LEG_COUNT + 1))

    msh, cell_tags, _facet_tags, diag, t_mesh = _build(True)
    tdim = msh.topology.dim
    ncells = int(msh.topology.index_map(tdim).size_global)
    # Hoisted on every rank before any facet-restricted form (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    halves = {i: (PORT_LOWER + i, PORT_UPPER + i) for i in ports_idx}
    tags_f = _interface_facet_tags(
        msh, cell_tags, {SHEET_IFACE + i: halves[i] for i in ports_idx}
    )

    # Leg (c)/(d0)/(d)'s sheet construction, unchanged and copied from the
    # four-port module: measure each full sheet, name its transverse axis off the
    # measured extents, narrow to step 2b's f = 0.5, re-measure `w = A/h`.
    geometry = {}
    for i in ports_idx:
        tag = SHEET_IFACE + i
        extents = _sheet_extents(msh, tags_f, tag, comm)
        w_bbox, _h_bbox, _spread = _sheet_axes(extents, diag, i)
        centroid = _sheet_bbox_centre(msh, tags_f, tag, comm)
        geometry[i] = {
            "tag": tag,
            "axis": 0 if extents[0] >= extents[1] else 1,
            "centroid": centroid,
            "w_full": float(w_bbox),
            "azimuth_deg": float(
                np.degrees(np.arctan2(centroid[1], centroid[0])) % 360.0
            ),
        }

    for i in ports_idx:
        g = geometry[i]
        tags_f = _narrowed_transverse(
            msh,
            tags_f,
            g["tag"],
            GATED_WIDTH_FRACTION,
            float(g["centroid"][g["axis"]]),
            g["axis"],
            0.5 * g["w_full"],
        )

    sheets = []
    for i in ports_idx:
        g = geometry[i]
        n_facets = _sheet_facet_count(msh, tags_f, g["tag"], comm)
        assert n_facets > 0, f"sheet {g['tag']}: no owned facets anywhere"
        area = _facet_group_area(msh, tags_f, g["tag"], comm)
        extents = _sheet_extents(msh, tags_f, g["tag"], comm)
        w_bbox, h_bbox, spread = _sheet_axes(extents, diag, i)
        sheets.append(
            {
                **g,
                "facets": int(n_facets),
                "area": float(area),
                "h": float(h_bbox),
                "w": float(area / h_bbox),
                "w_bbox": float(w_bbox),
                "out_of_plane": float(spread),
            }
        )

    sizes = {
        "conductor": _tag_cell_size(msh, cell_tags, CONDUCTOR_CELL_TAG, comm),
        "air": _tag_cell_size(msh, cell_tags, AIR_CELL_TAG, comm),
        "phantom": _tag_cell_size(msh, cell_tags, PHANTOM_CELL_TAG, comm),
    }

    def _solve(frequency_hz):
        problem = TimeHarmonicProblem(
            mesh=msh,
            frequency_hz=frequency_hz,
            material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
            cell_tags=cell_tags,
            material_map={
                CONDUCTOR_CELL_TAG: HomogeneousMaterial(
                    sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0
                ),
                PHANTOM_CELL_TAG: HomogeneousMaterial(
                    sigma=SALINE_SIGMA, epsilon_r=SALINE_EPSILON_R, mu_r=1.0
                ),
            },
            boundary_condition="pec_zero_tangential_a",
        )
        port_defs = []
        specs = []
        for s in sheets:
            pid = f"P{s['tag'] - SHEET_IFACE}"
            port_defs.append(
                PortDefinition(
                    port_id=pid,
                    positive_tag=int(s["tag"]),
                    negative_tag=CONDUCTOR_CELL_TAG,
                    orientation="leg_gap_axial_plus_z",
                    z0_ohm=TERMINATED_PORT_IMPEDANCE_OHM,
                )
            )
            specs.append(
                LumpedSheetPortSpec(
                    port_id=pid,
                    facet_tag=int(s["tag"]),
                    port_impedance_ohm=TERMINATED_PORT_IMPEDANCE_OHM,
                    gap_height_m=s["h"],
                    sheet_width_m=s["w"],
                    drive_direction=(0.0, 0.0, 1.0),
                    drive_voltage_v=1.0 + 0.0j,
                    interior=True,
                )
            )
        comm.Barrier()
        t0 = time.perf_counter()
        result = run_lumped_sheet_port_case(
            problem, port_defs, specs, facet_tags=tags_f, driven_port_id="P1"
        )
        comm.Barrier()
        t_solve = time.perf_counter() - t0
        i_driven = result.responses["P1"].current_a
        v_driven = result.responses["P1"].voltage_v
        z_column = np.array(
            [result.responses[p.port_id].voltage_v / i_driven for p in port_defs],
            dtype=np.complex128,
        )
        # Terminal complex power at the driven port — see the module docstring:
        # this is NOT the `TH-11` family's volume integral, and it is printed,
        # never gated.
        power = 0.5 * complex(v_driven) * np.conjugate(complex(i_driven))
        media = {
            "phantom": _propagation_constants(
                SALINE_EPSILON_R, SALINE_SIGMA, frequency_hz
            ),
            "air": _propagation_constants(1.0, 0.0, frequency_hz),
        }
        return {
            "frequency_hz": float(frequency_hz),
            "result": result,
            "z_column": z_column,
            "i_driven": complex(i_driven),
            "v_driven": complex(v_driven),
            "power": complex(power),
            "media": media,
            "cells_per_delta_phantom": media["phantom"]["delta"]
            / sizes["phantom"]["h_mean"],
            "cells_per_lambda_phantom": media["phantom"]["lambda"]
            / sizes["phantom"]["h_mean"],
            "cells_per_lambda_air": media["air"]["lambda"] / sizes["air"]["h_mean"],
            "solve_time": float(t_solve),
        }

    # Control first, then the knob: the frequency is the only thing that moves.
    solves = {"control_10mhz": _solve(FREQUENCY_HZ), "larmor_64mhz": _solve(FREQUENCY_64_HZ)}
    rss_bytes = _rss_peak_bytes(comm)

    if comm.rank == 0:
        print(
            f"\n[PORT-11 step1] gapped+sheeted birdcage: {ncells} cells "
            f"(record {STEP2_CELL_COUNT}, ratio {ncells / STEP2_CELL_COUNT:.6f}), "
            f"mesh {diag['mesh_wall_time_s']:.2f} s, rung {t_mesh:.2f} s; "
            f"f_width = {GATED_WIDTH_FRACTION}, P1 driven, Z_p = z0 = "
            f"{TERMINATED_PORT_IMPEDANCE_OHM:.1f} Ohm on all {LEG_COUNT} ports",
            flush=True,
        )
        for name, sz in sizes.items():
            print(
                f"    region {name:9s}: {sz['cells']:7d} owned cells  h_mean "
                f"{sz['h_mean']:.6e} m  [min {sz['h_min']:.6e}, max "
                f"{sz['h_max']:.6e}]",
                flush=True,
            )
        print(
            "    (this fixture has no separate vessel-wall region — `GEO-18`'s "
            "partition is conductor / air / phantom only, so §7's "
            "'cells/lambda in air and wall' reads air and phantom here)",
            flush=True,
        )
        print(
            f"    summed ru_maxrss across ranks: {rss_bytes / 2**30:.4f} GiB",
            flush=True,
        )
        for name, sv in solves.items():
            ph, air = sv["media"]["phantom"], sv["media"]["air"]
            print(
                f"\n[PORT-11 step1] {name}: f = {sv['frequency_hz']:.6e} Hz, solve "
                f"{sv['solve_time']:.2f} s wall at -n 2\n"
                f"    phantom (saline eps_r = {SALINE_EPSILON_R}, sigma = "
                f"{SALINE_SIGMA} S/m): loss tangent {ph['loss_tangent']:.4f}, "
                f"delta = {ph['delta']:.6e} m, lambda = {ph['lambda']:.6e} m\n"
                f"      cells/delta = {sv['cells_per_delta_phantom']:.4f} "
                f"(floor {PHANTOM_CELLS_PER_DELTA_FLOOR:.1f}, GATED at 64 MHz), "
                f"cells/lambda = {sv['cells_per_lambda_phantom']:.4f}\n"
                f"    air: lambda = {air['lambda']:.6e} m, cells/lambda = "
                f"{sv['cells_per_lambda_air']:.4f}\n"
                f"    V_1 = {sv['v_driven']:+.9e} V, I_1 = {sv['i_driven']:+.9e} A\n"
                f"    P = 0.5*V_1*conj(I_1) = {sv['power']:+.9e} VA, "
                f"|Im P|/Re P = "
                f"{abs(sv['power'].imag) / abs(sv['power'].real):.6e} "
                f"(terminal complex power, printed not gated)",
                flush=True,
            )
            for k, z in enumerate(sv["z_column"], start=1):
                print(f"    Z_{k}1 = {z:+.9e} Ohm  |Z| = {abs(z):.9e}", flush=True)

    return {
        "solves": solves,
        "sheets": sheets,
        "sizes": sizes,
        "cells": ncells,
        "mesh_time": float(t_mesh),
        "rss_bytes": float(rss_bytes),
    }


@complex_only
def test_the_probe_solved_the_gated_fixture_at_both_frequencies(larmor_probe):
    """Structural: the leg (d0) fixture, two real field solves, four sheets.

    None of this is a result; all of it is what the price below needs in order
    to be a price of the thing `PORT-9` gated rather than of something else.
    """
    ratio = larmor_probe["cells"] / STEP2_CELL_COUNT
    assert abs(ratio - 1.0) < STEP2_CELL_COUNT_BAND, (
        f"the probe meshed {larmor_probe['cells']} cells against the record "
        f"{STEP2_CELL_COUNT}; this is not the fixture `PORT-9` measured, so "
        "nothing priced here is a price of that fixture"
    )
    for s in larmor_probe["sheets"]:
        assert s["out_of_plane"] < 1.0e-12, (
            f"sheet {s['tag']}: out-of-plane spread {s['out_of_plane']:.3e} m — "
            "the filtered facet set is not a plane"
        )
        assert s["w"] < s["w_full"], (
            f"sheet {s['tag']}: A/h = {s['w']:.9e} m is not below the full "
            f"sheet's extent {s['w_full']:.9e} m — the interior-width filter "
            "did not run"
        )
    assert larmor_probe["solves"]["control_10mhz"]["frequency_hz"] == pytest.approx(
        FREQUENCY_HZ
    )
    assert larmor_probe["solves"]["larmor_64mhz"]["frequency_hz"] == pytest.approx(
        FREQUENCY_64_HZ
    )
    for name, sv in larmor_probe["solves"].items():
        r = sv["result"]
        assert not r.is_placeholder, (
            f"the {name} solve returned is_placeholder=True — it fell back to "
            "the PORT-0 coupling heuristic, so no impedance here came off a field"
        )
        assert len(r.responses) == LEG_COUNT
        assert r.responses["P1"].is_driven
        assert np.all(np.isfinite(sv["z_column"].real))
        assert np.all(np.isfinite(sv["z_column"].imag))


@complex_only
def test_the_ten_megahertz_leg_reproduces_leg_d0(larmor_probe):
    """**The anchor.**  The 10 MHz column reproduces leg (d0)'s record to 1e-6.

    The frequency is the only knob this module turns.  The 10 MHz solve is the
    same mesh, the same sheets, the same route and the same 50 Ω termination as
    `PORT-9` leg (d0), so its column must land on ``LEG_D0_Z_COLUMN`` — imported
    from the four-port module, never restated.  If it does not, the harness
    changed rather than the physics, and every 64 MHz number this module prints
    is uninterpretable.  Band pre-stated at 1e-6 relative (§9 item 1); it is not
    a physics tolerance and it does not widen.
    """
    sv = larmor_probe["solves"]["control_10mhz"]
    deviations = np.abs(sv["z_column"] - LEG_D0_Z_COLUMN) / np.abs(LEG_D0_Z_COLUMN)

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step1] ANCHOR: 10 MHz vs `PORT-9` leg (d0)'s recorded "
            f"50 Ohm column, band {FREQUENCY_CONTROL_BAND:.0e} relative:",
            flush=True,
        )
        for k, (z, rec, dev) in enumerate(
            zip(sv["z_column"], LEG_D0_Z_COLUMN, deviations), start=1
        ):
            print(
                f"    Z_{k}1 {z:+.9e}  record {rec:+.9e}  rel. deviation "
                f"{dev:.3e}  "
                f"{'PASS' if dev < FREQUENCY_CONTROL_BAND else 'MISS'}",
                flush=True,
            )

    worst = float(np.max(deviations))
    assert worst < FREQUENCY_CONTROL_BAND, (
        f"the 10 MHz leg deviates {worst:.3e} from leg (d0)'s recorded column "
        f"against the pre-stated {FREQUENCY_CONTROL_BAND:.0e} band — the mesh "
        "or the code path moved, not the frequency, so nothing this module "
        "prints at 64 MHz is comparable to what `PORT-9` recorded"
    )


@complex_only
def test_the_phantom_resolves_the_skin_depth_at_64_mhz(larmor_probe):
    """**The stop rule.**  ``cells/δ`` in the phantom at 64 MHz ≥ 2.

    Pre-stated in §7 `PORT-11` step 1 and binding: at this mesh, a phantom that
    does not resolve its own skin depth is a **resolution finding about the
    mesh**, and the follow-on is a `GEO` phantom-sizing chunk, not step 2's
    4×4.  It is never a band to widen — the assertion below fails loudly on
    purpose, and the number it fails with is the deliverable.

    ``δ`` is taken from the full lossy-medium propagation constant, not the
    good-conductor approximation: the saline load's loss tangent at 64 MHz is
    ~1.8, so ``σ ≫ ωε`` does not hold and ``sqrt(2/ωμσ)`` would be the wrong
    number by tens of percent.
    """
    sv = larmor_probe["solves"]["larmor_64mhz"]
    control = larmor_probe["solves"]["control_10mhz"]
    cells_per_delta = sv["cells_per_delta_phantom"]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-11 step1] STOP RULE at {sv['frequency_hz'] / 1e6:.0f} MHz "
            f"(floor {PHANTOM_CELLS_PER_DELTA_FLOOR:.1f}, pre-stated, "
            f"not widenable):\n"
            f"    phantom h_mean {larmor_probe['sizes']['phantom']['h_mean']:.6e} "
            f"m, delta {sv['media']['phantom']['delta']:.6e} m  =>  cells/delta "
            f"{cells_per_delta:.4f}  "
            f"{'PASS' if cells_per_delta >= PHANTOM_CELLS_PER_DELTA_FLOOR else 'MISS'}"
            f"\n    (10 MHz control: delta "
            f"{control['media']['phantom']['delta']:.6e} m, cells/delta "
            f"{control['cells_per_delta_phantom']:.4f} — the load is thinner at "
            f"the higher frequency, which is why this is gated at 64 MHz)",
            flush=True,
        )

    assert cells_per_delta >= PHANTOM_CELLS_PER_DELTA_FLOOR, (
        f"at 64 MHz the phantom resolves its own skin depth "
        f"({sv['media']['phantom']['delta']:.6e} m) with only "
        f"{cells_per_delta:.4f} cells against the pre-stated floor of "
        f"{PHANTOM_CELLS_PER_DELTA_FLOOR:.1f} — this is a resolution finding "
        "about the mesh, not a band question (§7 `PORT-11` step 1 stop rule): "
        "the follow-on is a `GEO` phantom-sizing chunk, never step 2"
    )
