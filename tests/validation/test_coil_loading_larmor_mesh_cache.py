"""`TH-11` step 5a, command 1: cache the 64 MHz third rung to XDMF.

Step 5 attempt 1 priced the third rung (``resolution_near`` = 0.00125) at
**2 807 309 cells** on 0.7.2 (**2 808 204** on the 0.11 image, `OPS-27` step 1)
and **288.2 s of meshing** — inside §7's 3.4 M ceiling but
so expensive that a mesh-plus-pair command cannot return inside a scheduled
session's ~590 s foreground window.  The 10:30 review's decision (a) is this
module: generate that mesh **once**, write it to XDMF, and read it back in the
same command so the round trip is *verified* rather than assumed.  Step 5b then
solves off the cache and pays 0 s of meshing.

**What is gated** — that the cache is the same mesh, not merely a mesh:

* the owned cell count on the written mesh is the probe's exact record
  ``NCELLS_THIRD == 2_808_204`` (the ``third`` rung only; the ``smoke`` rung has
  no record and gates the round trip alone);
* the read-back mesh has the **same** owned cell count;
* the cell-tag and facet-tag **value sets** survive the round trip, and so do
  the per-tag owned cell counts, tag by tag — the count is what the solver's
  ``dx(WIRE_TAG)`` and slab measures integrate over, so a silently renumbered or
  dropped region would change every downstream reading;
* the tag **names** survive — ``read_meshtags`` selects by name, so a renamed
  grid makes the cache unreadable by 5b even when the numbers are right (§7's
  named trap).

Rank-safety: ``cell_tags.values`` is rank-local *and* covers ghosts under a
ghosted decomposition, so every count here is restricted to owned entities
(``index_map.size_local``) and reduced before assertion.  The read is done with
``GhostMode.none`` to match ``gmshio``'s ghost-free default in `io/mesh.py`,
so the two decompositions are like-for-like.

Selection by environment, so the round-trip mechanics can be exercised cheaply
before the 288 s rung is bought:

* ``TH11_CACHE_RUNG`` — ``third`` (default, ``near`` = 0.00125, the priced rung)
  or ``smoke`` (a deliberately coarse variant of the same fixture, no count
  record, ~seconds);
* ``TH11_CACHE_DIR`` — where the ``.xdmf``/``.h5`` pair lands; defaults to
  ``output/th11_step5_cache`` (gitignored — meshes are not repo content).

Run (complex build not required — this command never solves)::

    docker compose exec -T fem-em-solver bash -lc \\
      'cd /workspace && TH11_CACHE_RUNG=smoke PYTHONPATH=/workspace/src \\
       mpiexec -n 2 python3 -m pytest \\
       tests/validation/test_coil_loading_larmor_mesh_cache.py -v -s'
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pytest
from mpi4py import MPI

from dolfinx import io, mesh as dmesh

from fem_em_solver.io.mesh import MeshGenerator
from tests.validation.test_coil_loading_larmor_third_rung import (
    NCELLS_THIRD_CEILING,
    RESOLUTION_NEAR_THIRD,
)
from tests.validation.test_dodd_deeds_impedance import (
    FEM_BOX_HALF_WIDTH,
    FEM_LIFTOFF,
    FEM_LOOP_RADIUS,
    FEM_WIRE_RADIUS,
)

# The probe's exact record: the mesh generator never sees the frequency, so this
# count is a property of the rung and must reproduce to the cell.  Re-recorded
# on the **0.11 image** (dolfinx 0.11 / gmsh 4.15.2) by `OPS-27` step 1:
# 2 808 204 cells at `-n 2` in
# ``20260827T141059Z_OPS-26-step2d-meshcache-real.log`` (the same count read
# twice there — at mesh time and at read-back — with the cell tags
# {1: 13342, 2: 1067531, 3: 1727331} unchanged).  It read 2 807 309 until
# 2026-08-27 — measured on the **0.7.2** image / gmsh 4.11.1 in
# ``20260817T123353Z_TH-11-step5-probe.log`` — and that digit is stale, not a
# regression: the drift is +0.032%, the smallest of this class, and the
# module's other four names (the ceiling, the round-trip, the tag sets) stayed
# green through the move.  `NCELLS_THIRD_CEILING` is unchanged.  Version-tag
# this constant again if the image moves.
NCELLS_THIRD = 2_808_204

# Grid names the cache is written under.  5b reads by name; changing either of
# these invalidates every existing cache file, which is why they are constants
# here rather than literals at the call sites.
MESH_NAME = "mesh"
CELL_TAGS_NAME = "cell_tags"
FACET_TAGS_NAME = "facet_tags"

# Geometry xpath for `write_meshtags`: the default `/Xdmf/Domain/Grid/Geometry`
# is ambiguous once a second grid (the first tag set) is in the file, so both
# tag writes point explicitly at the mesh grid.
_GEOMETRY_XPATH = f"/Xdmf/Domain/Grid[@Name='{MESH_NAME}']/Geometry"

# The rungs this module can cache: near-field size, wire size, far size, and the
# expected owned cell count (``None`` for the smoke rung, which has no record).
RUNGS = {
    "third": (RESOLUTION_NEAR_THIRD, 0.002, 0.025, NCELLS_THIRD),
    # Only the *volume* sizes coarsen on the smoke rung: `resolution_wire` stays
    # at the fixture's 0.002 because the wire radius is 0.0025 m, and a surface
    # size above it makes gmsh grind (a 0.01 wire size did not finish meshing in
    # 240 s — `20260817T183248Z_TH-11-step5a-cache-smoke.log`).
    "smoke": (0.01, 0.002, 0.05, None),
}


def _rung() -> str:
    rung = os.environ.get("TH11_CACHE_RUNG", "third").strip().lower()
    if rung not in RUNGS:
        raise ValueError(f"TH11_CACHE_RUNG must be one of {sorted(RUNGS)}; got {rung!r}")
    return rung


def cache_paths(rung: str) -> Path:
    """Where this rung's cache lives — importable, so 5b reads the same path."""
    root = Path(os.environ.get("TH11_CACHE_DIR", "output/th11_step5_cache"))
    return root / f"loop_half_space_{rung}.xdmf"


def _owned_tag_counts(msh, tags, comm) -> dict[int, int]:
    """Global per-tag counts over **owned** entities only.

    ``tags.values`` is rank-local and, on a ghosted mesh, also carries ghost
    entities — summing it across ranks double-counts them.  Restricting to
    ``indices < size_local`` of the entity dimension's index map makes the sum a
    partition-invariant property of the mesh, which is exactly what a
    write/read comparison needs.
    """
    dim = tags.dim
    size_local = msh.topology.index_map(dim).size_local
    owned = np.asarray(tags.indices) < size_local
    values = np.asarray(tags.values, dtype=np.int64)[owned]
    local: dict[int, int] = {}
    for value, count in zip(*np.unique(values, return_counts=True)):
        local[int(value)] = int(count)
    merged: dict[int, int] = {}
    for part in comm.allgather(local):
        for value, count in part.items():
            merged[value] = merged.get(value, 0) + count
    return merged


def _owned_cells(msh, comm) -> int:
    return int(
        comm.allreduce(msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM)
    )


@pytest.fixture(scope="module")
def cached_rung():
    """Mesh the rung, write it to XDMF, read it back — one command, both halves."""
    rung = _rung()
    resolution_near, resolution_wire, resolution_far, ncells_expected = RUNGS[rung]
    comm = MPI.COMM_WORLD
    path = cache_paths(rung)
    if comm.rank == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
    comm.Barrier()

    t_mesh = time.perf_counter()
    msh, cell_tags, facet_tags = MeshGenerator.loop_over_half_space_domain(
        loop_radius=FEM_LOOP_RADIUS,
        wire_radius=FEM_WIRE_RADIUS,
        liftoff=FEM_LIFTOFF,
        box_half_width=FEM_BOX_HALF_WIDTH,
        resolution_wire=resolution_wire,
        resolution_near=resolution_near,
        resolution_far=resolution_far,
        near_half_width=0.06,
        near_depth=0.05,
        near_height=0.03,
        comm=comm,
    )
    comm.Barrier()
    t_mesh = time.perf_counter() - t_mesh

    written = dict(
        ncells=_owned_cells(msh, comm),
        cell_counts=_owned_tag_counts(msh, cell_tags, comm),
        facet_counts=_owned_tag_counts(msh, facet_tags, comm),
    )
    if comm.rank == 0:
        print(
            f"\n[TH-11 step 5a | rung {rung} (near {resolution_near})] "
            f"{written['ncells']} cells, mesh {t_mesh:.1f} s at -n {comm.size} "
            f"(ceiling {NCELLS_THIRD_CEILING}); cell tags {written['cell_counts']}, "
            f"facet tags {written['facet_counts']}",
            flush=True,
        )

    msh.name = MESH_NAME
    cell_tags.name = CELL_TAGS_NAME
    facet_tags.name = FACET_TAGS_NAME
    msh.topology.create_connectivity(msh.topology.dim - 1, msh.topology.dim)

    t_write = time.perf_counter()
    with io.XDMFFile(comm, str(path), "w") as xdmf:
        xdmf.write_mesh(msh)
        xdmf.write_meshtags(cell_tags, msh.geometry, geometry_xpath=_GEOMETRY_XPATH)
        xdmf.write_meshtags(facet_tags, msh.geometry, geometry_xpath=_GEOMETRY_XPATH)
    comm.Barrier()
    t_write = time.perf_counter() - t_write

    t_read = time.perf_counter()
    with io.XDMFFile(comm, str(path), "r") as xdmf:
        # Ghost-free, matching `gmshio`'s default in io/mesh.py: 5b must solve
        # on the same decomposition family the -n 2 records were measured on.
        msh_r = xdmf.read_mesh(ghost_mode=dmesh.GhostMode.none, name=MESH_NAME)
        msh_r.topology.create_connectivity(msh_r.topology.dim - 1, msh_r.topology.dim)
        cell_tags_r = xdmf.read_meshtags(msh_r, name=CELL_TAGS_NAME)
        facet_tags_r = xdmf.read_meshtags(msh_r, name=FACET_TAGS_NAME)
    comm.Barrier()
    t_read = time.perf_counter() - t_read

    read = dict(
        ncells=_owned_cells(msh_r, comm),
        cell_counts=_owned_tag_counts(msh_r, cell_tags_r, comm),
        facet_counts=_owned_tag_counts(msh_r, facet_tags_r, comm),
        cell_tags_name=cell_tags_r.name,
        facet_tags_name=facet_tags_r.name,
    )
    if comm.rank == 0:
        size_mb = sum(
            p.stat().st_size
            for p in (path, path.with_suffix(".h5"))
            if p.exists()
        ) / 1024.0**2
        print(
            f"[TH-11 step 5a] cache {path} ({size_mb:.1f} MiB): write "
            f"{t_write:.1f} s, read-back {t_read:.1f} s at -n {comm.size}; "
            f"mesh {t_mesh:.1f} s is what 5b no longer pays"
            f"\n[TH-11 step 5a] read-back: {read['ncells']} cells, cell tags "
            f"{read['cell_counts']}, facet tags {read['facet_counts']}, names "
            f"{read['cell_tags_name']!r}/{read['facet_tags_name']!r}",
            flush=True,
        )

    return dict(
        rung=rung,
        resolution_near=resolution_near,
        ncells_expected=ncells_expected,
        path=path,
        written=written,
        read=read,
        t_mesh=t_mesh,
        t_write=t_write,
        t_read=t_read,
    )


@pytest.mark.integration
def test_the_cached_rung_is_the_priced_mesh(cached_rung):
    """The written mesh is the probe's exact 2 808 204-cell third rung.

    Frequency never reaches the mesh generator, so the rung's count is fixed by
    its sizing parameters alone: a different number means 5b would extrapolate
    the 64 MHz ladder off a different discretisation than the one §7 priced.
    """
    expected = cached_rung["ncells_expected"]
    ncells = cached_rung["written"]["ncells"]
    print(f"\n  written: {ncells} cells at near = {cached_rung['resolution_near']}")
    if expected is None:
        pytest.skip("the smoke rung has no count record; it gates the round trip only")
    assert ncells == expected, (
        f"the third rung meshed to {ncells} cells, not the probe's recorded "
        f"{expected}: the fixture changed rather than being re-meshed"
    )


@pytest.mark.integration
def test_the_round_trip_preserves_the_cell_count(cached_rung):
    """Owned cell count is identical across write → read."""
    written, read = cached_rung["written"]["ncells"], cached_rung["read"]["ncells"]
    print(f"\n  cells: written {written}, read back {read}")
    assert read == written, (
        f"the XDMF round trip changed the cell count: {written} written, "
        f"{read} read back"
    )


@pytest.mark.integration
@pytest.mark.parametrize("which", ["cell_counts", "facet_counts"])
def test_the_round_trip_preserves_the_tag_populations(cached_rung, which):
    """Tag value sets *and* per-tag owned counts survive the round trip.

    The value set alone is too weak: the solver integrates over
    ``dx(WIRE_TAG)`` and the slab tag, so a region that survives by name but
    loses cells changes every ΔZ downstream.  Counts are owned-only and reduced,
    so they are partition-invariant and comparable across the two (different)
    decompositions.
    """
    written = cached_rung["written"][which]
    read = cached_rung["read"][which]
    print(f"\n  {which}: written {written}, read back {read}")
    assert set(read) == set(written), (
        f"the XDMF round trip changed the {which} value set: {sorted(written)} "
        f"written, {sorted(read)} read back"
    )
    assert read == written, (
        f"the XDMF round trip changed per-tag {which}: {written} written, "
        f"{read} read back"
    )


@pytest.mark.integration
def test_the_round_trip_preserves_the_tag_names(cached_rung):
    """``read_meshtags`` selects by name — 5b cannot find a renamed grid."""
    read = cached_rung["read"]
    print(
        f"\n  names: {read['cell_tags_name']!r} (want {CELL_TAGS_NAME!r}), "
        f"{read['facet_tags_name']!r} (want {FACET_TAGS_NAME!r})"
    )
    assert read["cell_tags_name"] == CELL_TAGS_NAME
    assert read["facet_tags_name"] == FACET_TAGS_NAME
