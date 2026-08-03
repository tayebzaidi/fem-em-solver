"""`GEO-9` step-1 gate for ``MeshGenerator.coil_phantom_domain``.

Known-issues 7 recorded both coil+phantom mesh tests failing at
``dolfinx/io/gmshio.py:118: AssertionError``, and the `GEO-9` §7 entry
hypothesised the group re-derivation at ``io/mesh.py:1622-1634`` — an extra
fragment piece left with no physical group. **Measurement says otherwise**
(2026-08-03, logs ``20260803T033050Z_GEO-9-before`` and
``20260803T033119Z_GEO-9-order-probe``): the fixture generates perfectly in a
fresh process and the two tests pass in 4.8 s. They fail only when
``tests/mesh/test_birdcage_port_tags.py`` runs *first* in the same process —
that generator raises inside its rank-0 block without ``gmsh.finalize()``,
leaving gmsh initialised and busy ("Gmsh has aleady been initialized" /
"I'm busy! Ask me that later..."), so every later ``occ`` call is refused and
``model_to_mesh`` reads the stale birdcage model. Fragment and the group
re-derivation are innocent; the contamination is `GEO-9` step 2's to fix.

What this file adds is the assertion whose absence let that failure be a
downstream ``AssertionError`` in dolfinx rather than a statement about the
mesh: the `GEO-8` volume-partition identity, applied to the four coil+phantom
regions.
"""

from __future__ import annotations

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.io.mesh import MeshGenerator
from tests.mesh.helpers import global_cell_tag_set

COIL_MAJOR_RADIUS = 0.08
COIL_MINOR_RADIUS = 0.01
COIL_SEPARATION = 0.08
PHANTOM_RADIUS = 0.04
PHANTOM_HEIGHT = 0.10
AIR_PADDING = 0.04
RESOLUTION = 0.015

COIL_TAGS = (1, 2)
PHANTOM_TAG = 3
AIR_TAG = 4


def _generate(**kwargs):
    return MeshGenerator.coil_phantom_domain(
        coil_major_radius=COIL_MAJOR_RADIUS,
        coil_minor_radius=COIL_MINOR_RADIUS,
        coil_separation=COIL_SEPARATION,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        air_padding=AIR_PADDING,
        resolution=RESOLUTION,
        comm=MPI.COMM_WORLD,
        **kwargs,
    )


def _analytic_box_volume(phantom_offset_xy=(0.0, 0.0)):
    """``8·(radial_extent+pad)²·(z_extent+pad)`` with the generator's own sizing.

    The generator inflates ``air_padding`` to its recommended minimum, so the
    box the mesh actually fills is set by ``effective_air_padding_m``, not by
    the requested ``AIR_PADDING``.
    """
    sizing = MeshGenerator.coil_phantom_domain_sizing_diagnostics(
        coil_major_radius=COIL_MAJOR_RADIUS,
        coil_minor_radius=COIL_MINOR_RADIUS,
        coil_separation=COIL_SEPARATION,
        phantom_radius=PHANTOM_RADIUS,
        phantom_height=PHANTOM_HEIGHT,
        air_padding=AIR_PADDING,
        phantom_offset_xy=phantom_offset_xy,
    )
    pad = sizing["effective_air_padding_m"]
    half_x = sizing["radial_extent_without_padding_m"] + pad
    half_z = sizing["z_extent_without_padding_m"] + pad
    return 8.0 * half_x * half_x * half_z


def _tag_volume(msh, cell_tags, tag, comm):
    """``∫_tag 1 dV``, reduced — ``assemble_scalar`` is rank-local."""
    dx_tag = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * dx_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _total_volume(msh, comm):
    one = fem.Constant(msh, default_scalar_type(1.0))
    local = fem.assemble_scalar(fem.form(one * ufl.dx))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def test_coil_phantom_volumes_partition_the_box():
    """The four tagged regions tile the analytic air box exactly."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = _generate(phantom_placement_preset="centered")

    assert global_cell_tag_set(msh, cell_tags) == {1, 2, 3, 4}

    v_box = _analytic_box_volume()
    v_total = _total_volume(msh, comm)
    v_coils = [_tag_volume(msh, cell_tags, t, comm) for t in COIL_TAGS]
    v_phantom = _tag_volume(msh, cell_tags, PHANTOM_TAG, comm)
    v_air = _tag_volume(msh, cell_tags, AIR_TAG, comm)

    v_torus = 2.0 * np.pi**2 * COIL_MAJOR_RADIUS * COIL_MINOR_RADIUS**2
    v_cylinder = np.pi * PHANTOM_RADIUS**2 * PHANTOM_HEIGHT

    if comm.rank == 0:
        print(
            f"\nV_box={v_box:.6e}  V_mesh={v_total:.6e}  ratio={v_total / v_box:.12f}"
            f"\nV_coil1={v_coils[0]:.6e}  V_coil2={v_coils[1]:.6e}  "
            f"V_torus_analytic={v_torus:.6e}  "
            f"meshed/analytic={v_coils[0] / v_torus:.4f}, {v_coils[1] / v_torus:.4f}"
            f"\nV_phantom={v_phantom:.6e}  V_cylinder_analytic={v_cylinder:.6e}  "
            f"meshed/analytic={v_phantom / v_cylinder:.4f}"
            f"\nV_air={v_air:.6e}  sum(tagged)/V_mesh="
            f"{(v_air + v_phantom + sum(v_coils)) / v_total:.12f}",
            flush=True,
        )

    # The box boundary is planar, so a linear-tet mesh of it is exact to
    # roundoff: the chordal deficit of the torus and cylinder surfaces is
    # interior and cancels between each region and the air around it.
    assert abs(v_total / v_box - 1.0) < 1e-9, (
        f"total mesh volume {v_total:.6e} m^3 vs analytic box {v_box:.6e} m^3 "
        f"(ratio {v_total / v_box:.9f}); a ratio above 1 means a region is "
        "meshed twice, i.e. the fragment did not conform"
    )

    # Tags partition the mesh: air is the box *minus* coils and phantom.
    assert abs((v_air + v_phantom + sum(v_coils)) / v_total - 1.0) < 1e-9

    # Each curved region inscribes its analytic volume. `GEO-8` measured 0.9801
    # of the analytic torus at wire_resolution ≲ 0.4·minor_radius; this fixture
    # has a single global 0.015 that is larger than the 0.01 minor radius, so
    # the tori keep only 0.7547 / 0.7526 (measured 2026-08-03,
    # 20260803T033625Z_GEO-9-step1-probe.log) — a statement about resolution,
    # not about the fragment. The cylinder resolves one curved surface at
    # 0.04 m radius and keeps 0.9835.
    for tag, v in zip(COIL_TAGS, v_coils):
        assert 0.70 * v_torus < v < v_torus, (
            f"coil tag {tag} meshed volume {v:.6e} m^3 outside the inscribed "
            f"band (0.70, 1.00) x analytic {v_torus:.6e} m^3"
        )
    assert 0.90 * v_cylinder < v_phantom < v_cylinder, (
        f"phantom meshed volume {v_phantom:.6e} m^3 outside the inscribed band "
        f"(0.90, 1.00) x analytic {v_cylinder:.6e} m^3"
    )

    # Air is the complement, not the whole box.
    assert v_air < v_box - 0.9 * v_cylinder, (
        f"air volume {v_air:.6e} m^3 is not the box minus the phantom and "
        f"coils (box {v_box:.6e}, cylinder {v_cylinder:.6e})"
    )


def test_coil_phantom_off_center_preset_partitions_and_conserves_phantom_volume():
    """Moving the phantom in x changes neither the partition nor its volume."""
    comm = MPI.COMM_WORLD
    msh, cell_tags, _ = _generate(phantom_placement_preset="off_center")

    assert global_cell_tag_set(msh, cell_tags) == {1, 2, 3, 4}

    v_box = _analytic_box_volume(phantom_offset_xy=(0.35 * PHANTOM_RADIUS, 0.0))
    v_total = _total_volume(msh, comm)
    v_tagged = sum(
        _tag_volume(msh, cell_tags, t, comm) for t in (*COIL_TAGS, PHANTOM_TAG, AIR_TAG)
    )
    v_phantom = _tag_volume(msh, cell_tags, PHANTOM_TAG, comm)
    v_cylinder = np.pi * PHANTOM_RADIUS**2 * PHANTOM_HEIGHT

    if comm.rank == 0:
        print(
            f"\n[off_center] V_box={v_box:.6e}  V_mesh={v_total:.6e}  "
            f"ratio={v_total / v_box:.12f}  sum(tagged)/V_mesh="
            f"{v_tagged / v_total:.12f}"
            f"\n[off_center] V_phantom={v_phantom:.6e}  "
            f"meshed/analytic={v_phantom / v_cylinder:.4f}",
            flush=True,
        )

    assert abs(v_total / v_box - 1.0) < 1e-9
    assert abs(v_tagged / v_total - 1.0) < 1e-9
    # The phantom is rigidly translated, so its volume is preset-independent:
    # a leaked overlap with a coil would show up here as a deficit.
    assert 0.90 * v_cylinder < v_phantom < v_cylinder, (
        f"off-centre phantom meshed volume {v_phantom:.6e} m^3 outside the "
        f"inscribed band (0.90, 1.00) x analytic {v_cylinder:.6e} m^3"
    )
