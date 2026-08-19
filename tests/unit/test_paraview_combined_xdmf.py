"""Combined XDMF output must be a single grid, or ParaView probing breaks.

``XDMFFile.write_function`` emits one top-level ``<Grid>`` per function;
ParaView's Xdmf3 reader loads sibling grids as a vtkMultiBlockDataSet, and
point-probing filters (Plot Over Line, Probe) then return all-NaN for every
array outside the first block. ``consolidate_xdmf_grids`` rewrites the light
data so all attributes live on the mesh grid. This test asserts the merged
structure and round-trips the heavy data through the HDF5 file byte-for-byte.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import h5py
import pytest
from mpi4py import MPI

from dolfinx import default_scalar_type, fem, mesh as dmesh

from fem_em_solver.io.paraview_utils import write_combined_paraview_output


CONSTANT = np.array([1.5, -2.0, 3.0])

#: Names the writer is asked for; what it emits depends on the scalar type.
BASE_NAMES = ("CellTags", "F", "G")

#: DolfinX's XDMF writer stores one array per attribute in the real build and
#: splits each into ``real_<name>``/``imag_<name>`` when the scalar type is
#: complex. Derive the expected set from the *active* build (never a union of
#: both spellings: a real-mode run that emitted complex names must still fail).
SCALAR_IS_COMPLEX = np.issubdtype(np.dtype(default_scalar_type), np.complexfloating)

if SCALAR_IS_COMPLEX:
    EXPECTED_NAMES = {f"{part}_{n}" for n in BASE_NAMES for part in ("real", "imag")}
    FORBIDDEN_NAMES = set(BASE_NAMES)
else:
    EXPECTED_NAMES = set(BASE_NAMES)
    FORBIDDEN_NAMES = {f"{part}_{n}" for n in BASE_NAMES for part in ("real", "imag")}


def _split_name(name):
    """``real_F`` -> ``("F", "real")``; ``F`` -> ``("F", "real")`` in real mode."""
    for part in ("real", "imag"):
        if name.startswith(f"{part}_"):
            return name[len(part) + 1:], part
    return name, "real"


def _read_combined(path):
    """Parse the light data and pull in every heavy array it references.

    Returns a plain-Python dict so rank 0 can broadcast the whole verdict
    payload: every rank then runs the same assertions on the same bytes, which
    is what makes the test's per-rank summary lines identical (before this,
    non-zero ranks returned early and passed unconditionally while rank 0
    asserted — the rank-disagreement defect in the ``OPS-21`` known-issues
    entry; the fixture has broadcast rank 0's tmp path since the file was
    written, so a per-rank tmp dir was never the mechanism).
    """
    path = Path(path)
    tree = ET.parse(path)
    domain = tree.getroot().find("Domain")
    grids = domain.findall("Grid")

    facts = {"n_grids": len(grids), "attrs": {}}
    if len(grids) != 1:
        return facts

    grid = grids[0]
    facts["has_topology"] = grid.find("Topology") is not None
    facts["has_geometry"] = grid.find("Geometry") is not None

    for attr in grid.findall("Attribute"):
        data_item = attr.find("DataItem")
        if data_item is None:
            facts["attrs"][attr.get("Name")] = None
            continue
        h5_name, h5_path = data_item.text.strip().split(":")
        with h5py.File(path.parent / h5_name, "r") as h5:
            facts["attrs"][attr.get("Name")] = h5[h5_path][...]
    return facts


@pytest.fixture
def cube_with_fields(tmp_path_factory):
    comm = MPI.COMM_WORLD
    msh = dmesh.create_unit_cube(comm, 3, 3, 3)

    tdim = msh.topology.dim
    n_local = msh.topology.index_map(tdim).size_local
    indices = np.arange(n_local, dtype=np.int32)
    midpoints = dmesh.compute_midpoints(msh, tdim, indices)
    values = np.where(midpoints[:, 0] < 0.5, 1, 2).astype(np.int32)
    cell_tags = dmesh.meshtags(msh, tdim, indices, values)

    V = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    f = fem.Function(V, name="F")
    f.interpolate(lambda x: np.broadcast_to(CONSTANT[:, None], (3, x.shape[1])))
    g = fem.Function(V, name="G")
    g.interpolate(lambda x: -2.0 * x[:3])

    # All ranks need the same directory; broadcast rank 0's tmp path.
    out_dir = comm.bcast(
        str(tmp_path_factory.mktemp("pv")) if comm.rank == 0 else None
    )
    return comm, msh, cell_tags, f, g, out_dir


def test_combined_xdmf_is_single_grid_with_all_attributes(cube_with_fields):
    comm, msh, cell_tags, f, g, out_dir = cube_with_fields

    written = write_combined_paraview_output(
        out_dir, "cube", msh, cell_tags, {"F": (f, f), "G": (g, g)}, comm=comm
    )

    # Only rank 0 holds the written path (and does the consolidating rewrite);
    # broadcast the parsed result so every rank reaches the same verdict.
    facts = comm.bcast(_read_combined(written["combined"]) if comm.rank == 0 else None)

    # Exactly one grid: this is the property ParaView's probe filters need.
    assert facts["n_grids"] == 1, (
        f"expected a single consolidated grid, found {facts['n_grids']} — "
        "ParaView will load a multiblock and Plot Over Line breaks"
    )
    assert facts["has_topology"]
    assert facts["has_geometry"]

    names = set(facts["attrs"])
    assert names == EXPECTED_NAMES, (
        f"attribute names do not match the {'complex' if SCALAR_IS_COMPLEX else 'real'}"
        f"-build spelling: {sorted(names)}"
    )
    # Inverted assertion: the other build's spelling must be absent, so a
    # both-spellings union can never be mistaken for a fix.
    assert names.isdisjoint(FORBIDDEN_NAMES), (
        f"emitted the other build's attribute spelling: "
        f"{sorted(names & FORBIDDEN_NAMES)}"
    )

    n_cells_global = msh.topology.index_map(msh.topology.dim).size_global

    # Round-trip the heavy data referenced from the XML: the constant field
    # must come back exactly, the DG0 tags must partition every cell into the
    # two tag values, and every imaginary part must be identically zero (both
    # fields and the tags are real-valued whatever the scalar type is).
    for name, data in facts["attrs"].items():
        assert data is not None, f"{name} has no DataItem"
        base, part = _split_name(name)
        if part == "imag":
            assert np.array_equal(data, np.zeros_like(data)), (
                f"{name} is not identically zero"
            )
            continue
        if base == "F":
            assert data.shape[1] == 3
            assert np.array_equal(
                data, np.broadcast_to(CONSTANT, data.shape)
            ), "constant vector field did not round-trip exactly"
        elif base == "CellTags":
            assert data.size == n_cells_global
            counts = {v: int((data == v).sum()) for v in np.unique(data)}
            assert set(counts) == {1.0, 2.0}
            assert sum(counts.values()) == n_cells_global
