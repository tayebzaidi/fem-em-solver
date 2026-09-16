"""``write_xdmf_time_series`` keeps the time axis ``write_xdmf_with_tags`` drops.

``OPS-49``. Anchors, all on one ``create_box`` mesh with a DG0 and a CG1 field
over three steps:

(a) count identity (in = out): the XDMF parses to exactly **one** temporal
    collection with **3** ``<Time>`` values equal to the ``t``s written, and
    every child grid carries every attribute (both fields + CellTags);
(b) round trip: each step's arrays read back through ``h5py`` equal the
    functions' gathered arrays at rel <= 1e-12 (the identity ``EX-14``
    asserts on ``.bp``);
(c) negative control (asserted): the same three states through the *existing*
    ``write_xdmf_with_tags`` -- byte-identical in this change to commit
    ``fff1673`` (the pre-change ``HEAD``) -- parse to <= 1 time value, i.e.
    the collapse known-issues 2026-09-16 describes.

The writer is collective, so every rank asserts on broadcast (reduced)
values; nothing here is asserted on a rank-local reading.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
from dolfinx import default_scalar_type, fem, mesh
from mpi4py import MPI

from fem_em_solver.io.paraview_utils import (
    write_xdmf_time_series,
    write_xdmf_with_tags,
)

# The commit this test's negative control is pinned to: the state of
# write_xdmf_with_tags / consolidate_xdmf_grids before OPS-49, which this
# change leaves byte-identical.
PRE_CHANGE_COMMIT = "fff1673"

TIMES = [0.0, 0.5, 1.25]
FIELDS = ("phi", "sigma")
TAG_NAME = "CellTags"
REL_TOL = 1e-12



def _box_with_tags(comm, n=4):
    msh = mesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array([1.0, 1.0, 1.0])],
        [n, n, n],
        mesh.CellType.tetrahedron,
    )
    tdim = msh.topology.dim
    left = mesh.locate_entities(msh, tdim, lambda x: x[0] <= 0.5)
    right = mesh.locate_entities(msh, tdim, lambda x: x[0] > 0.5)
    indices = np.concatenate([left, right]).astype(np.int32)
    values = np.concatenate(
        [np.full(left.size, 1), np.full(right.size, 2)]
    ).astype(np.int32)
    order = np.argsort(indices)
    tags = mesh.meshtags(msh, tdim, indices[order], values[order])
    tags.name = "cell_tags"
    return msh, tags


def _owned(func):
    """Rank-local *owned* dof values (ghosts would double-count on gather)."""
    imap = func.function_space.dofmap.index_map
    bs = func.function_space.dofmap.index_map_bs
    return np.array(func.x.array[: imap.size_local * bs], dtype=np.float64)


def _gather_sorted(comm, func):
    """Globally sorted owned values, on rank 0 (None elsewhere)."""
    chunks = comm.gather(_owned(func), root=0)
    if comm.rank != 0:
        return None
    return np.sort(np.concatenate(chunks))


def _set_step(phi, sigma, t):
    """Values that differ between steps and depend only on position."""
    phi.interpolate(lambda x: (1.0 + t) * (x[0] + 2.0 * x[1] + 3.0 * x[2] + 0.5))
    sigma.interpolate(lambda x: (1.0 + t) * (7.0 + x[0] - x[2]))


def _read_attribute(h5py, xdmf_path, item_text):
    """Follow a DataItem's ``file.h5:/path`` reference and return the array."""
    h5_name, _, dataset = item_text.strip().rpartition(":")
    with h5py.File(xdmf_path.parent / h5_name, "r") as handle:
        return np.array(handle[dataset]).reshape(-1).astype(np.float64)


def test_time_series_keeps_one_collection_with_every_attribute(tmp_path):
    h5py = pytest.importorskip("h5py")
    comm = MPI.COMM_WORLD
    msh, tags = _box_with_tags(comm)

    V1 = fem.functionspace(msh, ("Lagrange", 1))
    V0 = fem.functionspace(msh, ("DG", 0))

    base = comm.bcast(str(tmp_path / "time_series"), root=0)

    # One Function pair per step (the writer takes the whole list, so a
    # single live pair would hand every step the last step's values), and
    # the gathered reference taken from the same objects.
    steps = []
    expected = {}
    for t in TIMES:
        p = fem.Function(V1, name="phi", dtype=default_scalar_type)
        s = fem.Function(V0, name="sigma", dtype=default_scalar_type)
        _set_step(p, s, t)
        steps.append((t, {"phi": p, "sigma": s}))
        got = {"phi": _gather_sorted(comm, p), "sigma": _gather_sorted(comm, s)}
        if comm.rank == 0:
            expected[f"{t:.12g}"] = got

    xdmf_path, _ = write_xdmf_time_series(base, msh, tags, steps, comm=comm)

    results = None
    if comm.rank == 0:
        xdmf_path = Path(xdmf_path)
        tree = ET.parse(xdmf_path)
        domain = tree.getroot().find("Domain")
        top = domain.findall("Grid")
        collections = [g for g in top if g.get("CollectionType") == "Temporal"]
        children = collections[0].findall("Grid") if len(collections) == 1 else []

        times = [float(c.find("Time").get("Value")) for c in children]
        attr_names = [
            sorted(a.get("Name") for a in c.findall("Attribute")) for c in children
        ]
        has_topology = [
            c.find("Topology") is not None and c.find("Geometry") is not None
            for c in children
        ]

        # (b) round trip through h5py, per step, per field.
        worst = 0.0
        compared = 0
        for child in children:
            key = f"{float(child.find('Time').get('Value')):.12g}"
            for attr in child.findall("Attribute"):
                name = attr.get("Name")
                if name not in FIELDS:
                    continue
                read = np.sort(
                    _read_attribute(h5py, xdmf_path, attr.find("DataItem").text)
                )
                ref = expected[key][name]
                assert read.size == ref.size, (name, key, read.size, ref.size)
                scale = max(np.max(np.abs(ref)), 1.0)
                worst = max(worst, float(np.max(np.abs(read - ref)) / scale))
                compared += 1

        results = {
            "n_top": len(top),
            "n_collections": len(collections),
            "n_children": len(children),
            "times": times,
            "attr_names": attr_names,
            "has_topology": has_topology,
            "worst_rel": worst,
            "compared": compared,
        }

    results = comm.bcast(results, root=0)

    # (a) count identity: one collection, three children, three times in = out
    assert results["n_top"] == 1, results
    assert results["n_collections"] == 1, results
    assert results["n_children"] == len(TIMES), results
    assert results["times"] == pytest.approx(TIMES, abs=0.0, rel=1e-12), results
    every = sorted([*FIELDS, TAG_NAME])
    assert results["attr_names"] == [every] * len(TIMES), results["attr_names"]
    assert all(results["has_topology"]), results["has_topology"]

    # (b) the h5py round trip
    assert results["compared"] == len(TIMES) * len(FIELDS), results["compared"]
    assert results["worst_rel"] <= REL_TOL, results["worst_rel"]

    if comm.rank == 0:
        print(
            f"OPS-49 (a) collections={results['n_collections']} "
            f"children={results['n_children']} times={results['times']} "
            f"attrs/child={results['attr_names'][0]}\n"
            f"OPS-49 (b) worst relative round-trip error = "
            f"{results['worst_rel']:.3e} over {results['compared']} arrays "
            f"(bound {REL_TOL:g})"
        )


def test_existing_single_state_writer_collapses_the_time_axis(tmp_path):
    """Negative control at ``PRE_CHANGE_COMMIT`` (byte-identical here)."""
    comm = MPI.COMM_WORLD
    msh, tags = _box_with_tags(comm)
    V1 = fem.functionspace(msh, ("Lagrange", 1))
    V0 = fem.functionspace(msh, ("DG", 0))
    phi = fem.Function(V1, name="phi", dtype=default_scalar_type)
    sigma = fem.Function(V0, name="sigma", dtype=default_scalar_type)

    counts = []
    for i, t in enumerate(TIMES):
        _set_step(phi, sigma, t)
        base = comm.bcast(str(tmp_path / f"single_state_{i}"), root=0)
        path, _ = write_xdmf_with_tags(
            base, msh, tags, {"phi": phi, "sigma": sigma}, comm=comm
        )
        n_times = None
        if comm.rank == 0:
            tree = ET.parse(path)
            n_times = len(list(tree.getroot().iter("Time")))
        counts.append(comm.bcast(n_times, root=0))

    # One file per state, and not even one <Time> survives in any of them:
    # the time axis cannot be expressed through this writer.
    assert all(c <= 1 for c in counts), counts
    assert sum(counts) < len(TIMES), counts
    if comm.rank == 0:
        print(f"OPS-49 (c) <Time> elements per single-state file = {counts}")


def test_facet_tags_are_rejected(tmp_path):
    """The named trap: half-supporting a second topology grid is worse."""
    comm = MPI.COMM_WORLD
    msh, tags = _box_with_tags(comm)
    V0 = fem.functionspace(msh, ("DG", 0))
    sigma = fem.Function(V0, name="sigma", dtype=default_scalar_type)
    base = comm.bcast(str(tmp_path / "rejected"), root=0)
    with pytest.raises(ValueError, match="facet_tags"):
        write_xdmf_time_series(
            base, msh, tags, [(0.0, {"sigma": sigma})], comm=comm, facet_tags=tags
        )
