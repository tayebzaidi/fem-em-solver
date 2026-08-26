"""`PORT-9` step 3 leg (d) — the 4x4 on the gapped birdcage at 50 Ohm.

Leg (c) put the first field on `GEO-18`'s gapped, sheeted birdcage and read one
column of ``Z`` at the two-torus probe impedance; leg (d0) found the termination
that puts the structure in a circuit at all (``Z_p = z0 = 50 Ohm``, discrimination
margin 2256.9707x against a 10x floor, adjacent spread 0.0040% inside the unmoved
0.5% band, leg (d1')'s (iii') tightening — `GEO-19` step B's mesh; 253.2002x / 0.0359% on the pre-step-B one).  Neither is a network: two columns of ``Z`` carry no reciprocity, no
passivity and no circulant reading.

This module drives **all four ports in turn** through
:func:`~fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep`'s
lumped-sheet route (step 2c's :class:`LumpedSheetPortSpec`, the route leg (d0)
used for its single column), on leg (d0)'s fixture exactly — 116 085 cells, four
``f = 0.5`` sheets on facet tags 211-214, ``w = A/h``, 10 MHz, ``Z_p = 50 Ohm``
on every port — and reads the assembled 4x4.

**The three gates**, pre-stated 2026-08-16 and never widened (§7 `PORT-9` step 3,
leg (d) as scoped by the 2026-08-23 03:00 review):

* **(i) reciprocity** — ``‖S − Sᵀ‖/‖S‖ ≤ 1e-3`` (step 2c's ``RECIPROCITY_BAND``,
  imported, not restated);
* **(ii) passivity** — ``σ_max(S) ≤ 1 + 1e-9`` and every column power sum ``≤ 1``;
* **(iii) C4 symmetry** — the maximum relative spread within each of the three
  circulant classes ``{Z_ii}``, ``{Z_i,i±1}`` and ``{Z_i,i+2}`` is ``≤ 0.5%``
  (``ADJACENT_SPREAD_BAND``, imported from leg (c)), taken **on Z**, so the
  sweep's termination convention does not enter the symmetry reading.

**Negative controls, both in-run.**  (1) The driven-P1 column of the 4x4
reproduces leg (d0)'s recorded 50 Ohm column to its printed precision — the
network claim is anchored to the one-column record before it is made.  (2) The
*pooled* off-diagonal spread (adjacent and opposite read as one class, which is
what a blind gate would take) must be at least 10x the worst intra-class spread:
otherwise gate (iii) is passing on noise rather than resolving structure.  Leg
(d0)'s column puts that ratio near 164x, so 10x is arithmetically reachable.

**The fixed-route records, mesh-tagged (2026-08-24, ruling (4\*), `GEO-19`
step B).**  On the power-wave S assembly (leg (d3), `8fd5af7`) and the
local-frame port construction's **116 085**-cell mesh:
``‖S − Sᵀ‖/‖S‖`` ~ 1e-14 (band 1e-3; noise over noise, so this one is
reproducible **in order of magnitude only** — 2.152e-14 relative here against
2.049e-14 pre-step-B), ``σ_max(S)`` = 0.999992805 (band 1 + 1e-9), maximum
column power sum 0.793823974, and the three class means/spreads 2.338160261e+01
Ohm / 0.0553%, 1.700854304e+01 Ohm / 0.0353%, 1.606048044e+01 Ohm / 0.0214%
against the imported band, which is now the 10:30 review's (iii′) reading of
**0.5%** — leg (d1′) executed that tightening on 2026-08-25 and re-ran this
module green under it, unchanged in every digit; the pooled-vs-worst separation
of negative control (2) reads 166.6766x.

The **pre-step-B** baselines these replace are the image+route-tagged ones of
ruling (5\*), taken on the 116 368-cell mesh and measured twice in-slot,
bit-identical in every ``Z`` digit (`20260824T093133Z` / `20260824T093526Z`,
leg (d3b); re-derived at `20260824T170332Z` / `170544Z`, leg (d3c)):
``σ_max(S)`` = 0.999993391, maximum column power sum 0.808049459, class
means/spreads 2.297360911e+01 Ohm / 0.0617%, 1.701075777e+01 Ohm / 0.0359%,
1.605637772e+01 Ohm / 0.0237%, separation 150.3584x.  Every gate is green on
both meshes and no band moved; the class structure **improves** under step B
(separation 150.4x → 166.7x, every intra-class spread down).  The 0.11 image
is common to both, so this re-record's single cause is the mesh.

**Scope.**  10 MHz, the port model's frequency — no Larmor, resonance or tuning
claim.  Gates (i)-(iii) green make step 3 ✅ *as measured on the undisplaced
mesh*; `PORT-9` itself moves to ✅ only once leg (d1)'s geometric control has run,
because a symmetry gate without its negative control is a consistency check, not
a validated gate.  Legs (c)'s and (d0)'s modules are untouched — this one adds.

Cost: standard tier, ``-n 2``, one mesh (~21 s) and four solves (~7-9 s each at
leg (d0)'s price) plus S assembly and cold JIT.

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-9-step3d "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 400 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_birdcage_four_port.py -v -s'"
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicProblem
from fem_em_solver.io.mesh import _interface_facet_tags
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.ports.lumped import LumpedSheetPortSpec
from fem_em_solver.ports.sparameters import run_n_port_sparameter_sweep

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
from tests.validation.test_lossy_sphere_fullwave import SALINE_EPSILON_R, SALINE_SIGMA
from tests.validation.test_port_birdcage_lumped_column import (
    ADJACENT_SPREAD_BAND,
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
from tests.validation.test_port_lumped_sheet_sweep import RECIPROCITY_BAND
from tests.validation.test_port_package_sparameters import REFERENCE_IMPEDANCE_OHM

# Leg (d0)'s termination: the ports' own reference impedance, found by
# measurement, not guessed in-slot (§7 `PORT-9` step 3 leg (d0)).  `Z_p` and the
# S-matrix's `z0_ohm` are the same number here for that reason and not by
# coincidence; both are printed, named, so a reader can tell them apart.
TERMINATED_PORT_IMPEDANCE_OHM = REFERENCE_IMPEDANCE_OHM

# **Gate (ii)**, pre-stated 2026-08-16 and unmoved: the S-matrix of a passive
# network has no singular value above 1.  The slack is numerical only.
PASSIVITY_SIGMA_TOLERANCE = 1.0e-9

# **Negative control (1)** — leg (d0)'s recorded 50 Ohm column, from
# `20260824T093133Z_PORT-9-step3d3b-run1.log`, reproduced bit-identically by that
# slot's second run `20260824T093526Z_PORT-9-step3d3b-run2.log`.  The band is the
# log's print precision (9 decimal places), not a physics tolerance: no physics
# band is defined here and none moves.
#
# **Mesh-tagged re-record, 2026-08-24 (ruling (4\*), `GEO-19` step B).**  The
# port sheets and gap boxes are now built in each leg's own local frame and
# rotated in by one snapped transform, which is exact-onto at the four axis
# azimuths but not *bit*-identical to the old axis-aligned construction — the
# old code's own `ring_radius·cos(π/2)` = 4.286263797e-18 put its boxes ~5 ulps
# off exact, and gmsh's tie-breaking turns that into 116 368 → 116 085 cells.
# So this fixture moved and its `Z` column moved with it, by 1.9e-02 (`Z_11`)
# down to 5.9e-04 (`Z_41`) relative.  Cause is the mesh **alone**: the 0.11
# image is common to these digits and the ones they replace, and the route is
# untouched by `12737a8` (a `src/fem_em_solver/io/mesh.py`-only commit).
#
# The two prior baselines, both retained as version-tagged history:
#   116 368 cells, 0.11 image (ruling (5\*), `20260824T170332Z`, leg (d3c)) —
#     +2.172952668e+01 + 7.461413742e+00j, +1.700667611e+01 + 2.379070919e-01j,
#     +1.602683719e+01 − 9.541994594e-01j, +1.701267933e+01 + 2.390098116e-01j;
#   116 416 cells, pre-0.11 image (`20260823T033304Z_PORT-9-step3d0.log`) —
#     +2.173224483e+01 + 7.459491479e+00j, +1.700799365e+01 + 2.384284683e-01j,
#     +1.602758027e+01 − 9.538522445e-01j, +1.701057452e+01 + 2.384109272e-01j.
# Measured at `20260824T183519Z_GEO-19-stepB-port9-measure.log` (lines 9220-9223).
LEG_D0_Z_COLUMN = np.array(
    [
        +2.215494591e01 + 7.460189773e00j,
        +1.700770839e01 + 2.351108372e-01j,
        +1.603004601e01 - 9.503096442e-01j,
        +1.700838310e01 + 2.350192948e-01j,
    ],
    dtype=np.complex128,
)
LEG_D0_REPRODUCTION_BAND = 1.0e-9

# **Negative control (2)**: the pooled off-diagonal class (adjacent and opposite
# read as one) must spread at least this many times the worst intra-class spread,
# or gate (iii) is passing on noise rather than resolving the layout's structure.
# Leg (d0)'s column reads 5.9% pooled against 0.0353% intra-class (~167x on the
# `GEO-19` step-B mesh, ~150x on the pre-step-B one), so the floor is reachable
# rather than wished for.
POOLED_SEPARATION_FLOOR = 10.0


def _class_spread(values):
    """Maximum pairwise disagreement in a class, relative to its mean magnitude.

    The class generalisation of leg (c)/(d0)'s ``|Z₂₁ − Z₄₁|/|Z₂₁|``: the widest
    complex separation any two members of the class show, divided by the class's
    own mean magnitude.  On a perfectly C4-symmetric layout every circulant class
    is constant and this is zero.
    """
    entries = np.asarray(values, dtype=np.complex128)
    scale = float(np.mean(np.abs(entries)))
    gap = 0.0
    for a in range(entries.size):
        for b in range(a + 1, entries.size):
            gap = max(gap, float(abs(entries[a] - entries[b])))
    return gap / scale if scale > 0.0 else np.inf


def _circulant_classes(z_matrix):
    """The three C4 classes of a 4-port circulant ``Z``: self, adjacent, opposite.

    Indices are taken modulo ``LEG_COUNT`` on the physical layout: port ``i+1``
    and ``i-1`` are the driven leg's azimuthal neighbours (90 deg away), ``i+2``
    is the leg across the coil (180 deg).  Every off-diagonal entry of the 4x4
    lands in exactly one class, and their union is the whole off-diagonal.
    """
    n = z_matrix.shape[0]
    self_terms, adjacent, opposite = [], [], []
    for row in range(n):
        for col in range(n):
            step = (row - col) % n
            if step == 0:
                self_terms.append(z_matrix[row, col])
            elif step == n // 2:
                opposite.append(z_matrix[row, col])
            else:
                adjacent.append(z_matrix[row, col])
    return {
        "self": np.array(self_terms, dtype=np.complex128),
        "adjacent": np.array(adjacent, dtype=np.complex128),
        "opposite": np.array(opposite, dtype=np.complex128),
    }


def build_four_port_sweep():
    """One mesh; four driven lumped-sheet solves at 50 Ohm; the assembled 4x4.

    The module fixture's body, lifted to module level so a consumer can run the
    gated sweep *through this module* rather than re-implementing it — the
    `ANS-1` import rule taken past constants to the construction itself
    (`EX-33` precedent, 2026-08-26; `EX-32` is the consumer). Additive: the
    fixture below is unchanged in behaviour and no gate reads the extra keys.
    """
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

    # Leg (c)/(d0)'s sheet construction, unchanged: measure each full sheet, name
    # its transverse axis off the measured extents, narrow to step 2b's f = 0.5
    # with the midpoint filter, then re-measure `w = A/h` on the filtered set.
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

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
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
                z0_ohm=REFERENCE_IMPEDANCE_OHM,
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
    result = run_n_port_sparameter_sweep(
        problem,
        port_defs,
        lumped_sheet_ports=specs,
        lumped_sheet_facet_tags=tags_f,
    )
    comm.Barrier()
    t_sweep = time.perf_counter() - t0

    z_matrix = np.asarray(result.z_matrix, dtype=np.complex128)
    s_matrix = np.asarray(result.s_matrix, dtype=np.complex128)
    classes = _circulant_classes(z_matrix)
    spreads = {name: _class_spread(v) for name, v in classes.items()}
    pooled = _class_spread(
        np.concatenate([classes["adjacent"], classes["opposite"]])
    )
    sigma = np.linalg.svd(s_matrix, compute_uv=False)
    column_power = np.sum(np.abs(s_matrix) ** 2, axis=0)
    reciprocity = float(
        np.linalg.norm(s_matrix - s_matrix.T) / np.linalg.norm(s_matrix)
    )
    z_reciprocity = float(
        np.linalg.norm(z_matrix - z_matrix.T) / np.linalg.norm(z_matrix)
    )

    if comm.rank == 0:
        print(
            f"\n[PORT-9 step3d] gapped+sheeted birdcage: {ncells} cells "
            f"(record {STEP2_CELL_COUNT}, ratio {ncells / STEP2_CELL_COUNT:.6f}), "
            f"mesh {diag['mesh_wall_time_s']:.2f} s, rung {t_mesh:.2f} s; "
            f"f = {FREQUENCY_HZ:.3e} Hz, f_width = {GATED_WIDTH_FRACTION}; "
            f"four driven solves through the lumped-sheet sweep in "
            f"{t_sweep:.2f} s wall at -n 2\n"
            f"    Z_p (lumped sheet, leg (d0)'s termination) = "
            f"{TERMINATED_PORT_IMPEDANCE_OHM:.6e} Ohm;  z0_ohm (S-matrix "
            f"reference) = {REFERENCE_IMPEDANCE_OHM:.6e} Ohm  — the same number "
            "by leg (d0)'s finding, not by coincidence",
            flush=True,
        )
        for s in sheets:
            print(
                f"    sheet {s['tag']} (P{s['tag'] - SHEET_IFACE}): azimuth "
                f"{s['azimuth_deg']:7.3f} deg; {s['facets']:5d} facets  "
                f"area {s['area']:.9e} m^2  h = {s['h']:.9e} m  "
                f"w = A/h = {s['w']:.9e} m  out-of-plane "
                f"{s['out_of_plane']:.3e} m",
                flush=True,
            )
        print("[PORT-9 step3d] Z (Ohm), column k = port k driven:", flush=True)
        for row in range(LEG_COUNT):
            entries = "  ".join(f"{z:+.9e}" for z in z_matrix[row])
            print(f"    Z_{row + 1}k = {entries}", flush=True)
        print("[PORT-9 step3d] S (z0 = 50 Ohm):", flush=True)
        for row in range(LEG_COUNT):
            entries = "  ".join(f"{s:+.9e}" for s in s_matrix[row])
            print(f"    S_{row + 1}k = {entries}", flush=True)
        print(
            f"    ||S - S^T||/||S|| = {reciprocity:.9e}   "
            f"||Z - Z^T||/||Z|| = {z_reciprocity:.9e}\n"
            f"    sigma(S) = "
            + ", ".join(f"{v:.9f}" for v in sigma)
            + f"\n    column power sums = "
            + ", ".join(f"{v:.9f}" for v in column_power)
            + f"\n    class spreads: self {spreads['self'] * 100:.4f}%  "
            f"adjacent {spreads['adjacent'] * 100:.4f}%  "
            f"opposite {spreads['opposite'] * 100:.4f}%  "
            f"(band {ADJACENT_SPREAD_BAND * 100:.1f}%); pooled off-diagonal "
            f"{pooled * 100:.4f}%",
            flush=True,
        )

    return {
        "result": result,
        "z": z_matrix,
        "s": s_matrix,
        "classes": classes,
        "spreads": spreads,
        "pooled": pooled,
        "sigma": sigma,
        "column_power": column_power,
        "reciprocity": reciprocity,
        "z_reciprocity": z_reciprocity,
        "sheets": sheets,
        "cells": ncells,
        "sweep_time": float(t_sweep),
        # Export handles for a consumer that needs the fixture itself (no gate
        # here reads them; `EX-32` writes ParaView off this mesh and re-solves
        # the P1-driven case for the field the sweep does not retain).
        "mesh": msh,
        "cell_tags": cell_tags,
        "facet_tags": tags_f,
        "problem": problem,
        "port_defs": port_defs,
        "specs": specs,
        "mesh_time": float(t_mesh),
        "halves": halves,
    }


@pytest.fixture(scope="module")
def four_port_sweep():
    """The gated 4x4, built once per module."""
    return build_four_port_sweep()


@complex_only
def test_the_sweep_drove_four_solved_field_ports_on_the_gated_fixture(
    four_port_sweep,
):
    """Structural: leg (d0)'s fixture, four driven solves, four planar sheets.

    None of this is a gate; all of it is what the gates need in order to mean
    anything.  In particular ``is_placeholder=False`` is what separates a solved
    field from the retired `PORT-0` coupling heuristic.
    """
    r = four_port_sweep["result"]
    assert not r.is_placeholder, (
        "the four-port sweep returned is_placeholder=True — it fell back to the "
        "PORT-0 coupling heuristic, so no impedance here came off a field"
    )
    assert r.z_matrix is not None, "the lumped-sheet route must return its Z"
    assert four_port_sweep["z"].shape == (LEG_COUNT, LEG_COUNT)
    assert four_port_sweep["s"].shape == (LEG_COUNT, LEG_COUNT)
    assert np.all(np.isfinite(four_port_sweep["z"].real))
    assert np.all(np.isfinite(four_port_sweep["z"].imag))

    ratio = four_port_sweep["cells"] / STEP2_CELL_COUNT
    assert abs(ratio - 1.0) < STEP2_CELL_COUNT_BAND, (
        f"the sweep meshed {four_port_sweep['cells']} cells against `GEO-18` "
        f"step 2's record {STEP2_CELL_COUNT}; this is not the fixture legs (c) "
        "and (d0) measured, so their records are not comparable"
    )
    for s in four_port_sweep["sheets"]:
        assert s["out_of_plane"] < 1.0e-12, (
            f"sheet {s['tag']}: out-of-plane spread {s['out_of_plane']:.3e} m — "
            "the filtered facet set is not a plane"
        )
        assert s["w"] < s["w_full"], (
            f"sheet {s['tag']}: A/h = {s['w']:.9e} m is not below the full "
            f"sheet's extent {s['w_full']:.9e} m — the interior-width filter did "
            "not run"
        )
    # One solve per port, each driving its own port and no other.
    assert set(r.excitation_results) == {f"P{i}" for i in range(1, LEG_COUNT + 1)}
    for driven, response in r.excitation_results.items():
        assert response.responses[driven].is_driven
        for pid, est in response.responses.items():
            if pid != driven:
                assert not est.is_driven


@complex_only
def test_the_driven_column_reproduces_leg_d0(four_port_sweep):
    """**Negative control (1).**  Column 1 of the 4x4 is leg (d0)'s column.

    The four-port sweep runs the same route leg (d0) ran for one column, on the
    same mesh at the same termination, so its P1-driven column must land on
    (d0)'s recorded digits.  If it does not, either the fixture moved or the
    sweep's column-by-column assembly is not the single-solve reading — and no
    network claim built on top of it would be comparable to the record.  The band
    is the log's print precision, not a physics tolerance.
    """
    column = four_port_sweep["z"][:, 0]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d] control (1): the P1-driven column vs leg (d0)'s "
            f"record (`20260823T033304Z_PORT-9-step3d0.log`), band "
            f"{LEG_D0_REPRODUCTION_BAND:.0e} relative:",
            flush=True,
        )
        for k, (z, z_rec) in enumerate(zip(column, LEG_D0_Z_COLUMN), start=1):
            print(
                f"    Z_{k}1 {z:+.9e} vs record {z_rec:+.9e}  rel. deviation "
                f"{abs(z - z_rec) / abs(z_rec):.3e}",
                flush=True,
            )

    for k, (z, z_rec) in enumerate(zip(column, LEG_D0_Z_COLUMN), start=1):
        err = abs(z - z_rec) / abs(z_rec)
        assert err < LEG_D0_REPRODUCTION_BAND, (
            f"Z_{k}1 = {z:+.9e} Ohm deviates {err:.3e} from leg (d0)'s recorded "
            f"{z_rec:+.9e} Ohm against the {LEG_D0_REPRODUCTION_BAND:.0e} print-"
            "precision band — this 4x4 is not built on leg (d0)'s solve"
        )


@complex_only
def test_the_four_port_network_is_reciprocal(four_port_sweep):
    """**Gate (i).**  ``‖S − Sᵀ‖/‖S‖ ≤ 1e-3`` on the birdcage's 4x4.

    Four independent solves, each driving a different leg, assembled column by
    column.  The network is passive and made of reciprocal materials, so the
    result must be symmetric; asymmetry above the band is a finding about the
    lumped-sheet route on a four-port network, never a licence to widen.  The
    band is step 2c's, imported.
    """
    ratio = four_port_sweep["reciprocity"]

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d] GATE (i) reciprocity (band {RECIPROCITY_BAND:.0e}, "
            f"step 2c's, unmoved):\n"
            f"    ||S - S^T||/||S|| = {ratio:.9e}  "
            f"{'PASS' if ratio <= RECIPROCITY_BAND else 'MISS'}\n"
            f"    ||Z - Z^T||/||Z|| = {four_port_sweep['z_reciprocity']:.9e} "
            "(reported)",
            flush=True,
        )

    assert ratio <= RECIPROCITY_BAND, (
        f"the birdcage 4x4 reads ||S - S^T||/||S|| = {ratio:.9e} against the "
        f"pre-stated {RECIPROCITY_BAND:.0e} band (||Z - Z^T||/||Z|| = "
        f"{four_port_sweep['z_reciprocity']:.9e}) — a finding about the "
        "lumped-sheet route's reciprocity on four ports (§7 `PORT-9` step 3 leg "
        "(d), negative result: record and stop; never widen (i)-(iii))"
    )


@complex_only
def test_the_four_port_network_is_passive(four_port_sweep):
    """**Gate (ii).**  ``σ_max(S) ≤ 1 + 1e-9`` and every column power sum ``≤ 1``.

    A network of lossy conductors, saline and air cannot deliver more power to
    its ports than is fed in, so ``S`` is a contraction.  Both readings are
    printed to nine digits as the 4x4's reproduction record.  Step 2c's
    two-port sweep read ``σ_max = 0.9869``, ungated; this is the first time the
    condition is a gate, and on four ports.
    """
    sigma = four_port_sweep["sigma"]
    column_power = four_port_sweep["column_power"]
    sigma_max = float(np.max(sigma))
    power_max = float(np.max(column_power))
    report = four_port_sweep["result"].sanity_report

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d] GATE (ii) passivity (tolerance "
            f"{PASSIVITY_SIGMA_TOLERANCE:.0e}, pre-stated 2026-08-16, unmoved):\n"
            f"    sigma_max(S) = {sigma_max:.9f}  "
            f"{'PASS' if sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE else 'MISS'}"
            f"   (PORT-5 metric: {report.passivity_max_sigma:.9f})\n"
            f"    max column power sum = {power_max:.9f}  "
            f"{'PASS' if power_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE else 'MISS'}"
            f"   (PORT-5 metric: {report.passivity_max_column_power_sum:.9f})",
            flush=True,
        )

    assert sigma_max <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
        f"sigma_max(S) = {sigma_max:.9f} exceeds 1 by more than "
        f"{PASSIVITY_SIGMA_TOLERANCE:.0e} — the assembled 4x4 is active, which is "
        "a passivity finding about the lumped-sheet route on four ports (§7 "
        "`PORT-9` step 3 leg (d), negative result: record and stop)"
    )
    for k, value in enumerate(column_power, start=1):
        assert value <= 1.0 + PASSIVITY_SIGMA_TOLERANCE, (
            f"column {k} of S carries power sum {value:.9f} > 1 + "
            f"{PASSIVITY_SIGMA_TOLERANCE:.0e} — driving port {k} returns more "
            "power than it is fed"
        )


@complex_only
def test_the_impedance_matrix_is_c4_circulant(four_port_sweep):
    """**Gate (iii′).**  Each circulant class of ``Z`` spreads ``≤ 0.5%``.

    The four legs sit at 0/90/180/270 deg on a layout that is C4-invariant by
    construction (`GEO-18`: square-section port boxes on the legs, drive ``ẑ``),
    so ``Z`` must be circulant: one self term, one adjacent term, one opposite
    term.  This is the four-port statement of leg (c)'s single-pair check, taken
    on ``Z`` rather than ``S`` so the termination convention does not enter, with
    the band imported from leg (c) and unmoved.

    Its own negative control travels with it: the *pooled* off-diagonal class
    must spread at least 10x the worst intra-class spread, or the gate is passing
    on noise rather than resolving the two symmetry classes leg (d0) separated.
    """
    spreads = four_port_sweep["spreads"]
    pooled = four_port_sweep["pooled"]
    worst = max(spreads.values())
    separation = pooled / worst if worst > 0.0 else np.inf

    if MPI.COMM_WORLD.rank == 0:
        print(
            f"\n[PORT-9 step3d] GATE (iii) C4 circulant symmetry of Z "
            f"(band {ADJACENT_SPREAD_BAND * 100:.1f}%, leg (c)'s, unmoved):",
            flush=True,
        )
        for name in ("self", "adjacent", "opposite"):
            members = four_port_sweep["classes"][name]
            print(
                f"    {name:9s} n = {members.size}  mean |Z| = "
                f"{np.mean(np.abs(members)):.9e} Ohm  spread "
                f"{spreads[name] * 100:.4f}%  "
                f"{'INSIDE' if spreads[name] <= ADJACENT_SPREAD_BAND else 'MISS'}",
                flush=True,
            )
        print(
            f"    control (2): pooled off-diagonal spread {pooled * 100:.4f}% "
            f"vs worst intra-class {worst * 100:.4f}%  =>  separation "
            f"{separation:.4f}x (floor {POOLED_SEPARATION_FLOOR:.0f}x)  "
            f"{'PASS' if separation >= POOLED_SEPARATION_FLOOR else 'MISS'}",
            flush=True,
        )

    for name, value in spreads.items():
        assert value <= ADJACENT_SPREAD_BAND, (
            f"the {name} class of Z spreads {value * 100:.4f}% against the "
            f"pre-stated {ADJACENT_SPREAD_BAND * 100:.1f}% band — on an "
            "undisplaced, C4-invariant layout that is mesh-induced asymmetry at "
            "the graded sizing (§7 `PORT-9` step 3 leg (d), negative result: "
            "record all three class spreads and both controls, stop; never widen)"
        )
    assert separation >= POOLED_SEPARATION_FLOOR, (
        f"the pooled off-diagonal class spreads {pooled * 100:.4f}%, only "
        f"{separation:.4f}x the worst intra-class spread {worst * 100:.4f}%, "
        f"against the pre-stated {POOLED_SEPARATION_FLOOR:.0f}x floor — gate "
        "(iii) is not resolving the adjacent/opposite structure leg (d0) "
        "measured, so its passing says nothing about C4 symmetry"
    )
