"""Combined XDMF output must be a single grid, or ParaView probing breaks.

``XDMFFile.write_function`` emits one top-level ``<Grid>`` per function;
ParaView's Xdmf3 reader loads sibling grids as a vtkMultiBlockDataSet, and
point-probing filters (Plot Over Line, Probe) then return all-NaN for every
array outside the first block. ``consolidate_xdmf_grids`` rewrites the light
data so all attributes live on the mesh grid. This test asserts the merged
structure and round-trips the heavy data through the HDF5 file byte-for-byte.
"""

import xml.etree.ElementTree as ET

import numpy as np
import h5py
import pytest
from mpi4py import MPI

from dolfinx import fem, mesh as dmesh

from fem_em_solver.io.paraview_utils import write_combined_paraview_output


CONSTANT = np.array([1.5, -2.0, 3.0])


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

    if comm.rank != 0:
        return

    tree = ET.parse(written["combined"])
    domain = tree.getroot().find("Domain")
    grids = domain.findall("Grid")

    # Exactly one grid: this is the property ParaView's probe filters need.
    assert len(grids) == 1, (
        f"expected a single consolidated grid, found {len(grids)} — "
        "ParaView will load a multiblock and Plot Over Line breaks"
    )
    grid = grids[0]
    assert grid.find("Topology") is not None
    assert grid.find("Geometry") is not None

    attrs = {a.get("Name"): a for a in grid.findall("Attribute")}
    assert set(attrs) == {"CellTags", "F", "G"}

    n_cells_global = msh.topology.index_map(msh.topology.dim).size_global

    # Round-trip the heavy data referenced from the XML: the constant field
    # must come back exactly, and the DG0 tags must partition every cell
    # into the two tag values.
    for name, attr in attrs.items():
        data_item = attr.find("DataItem")
        assert data_item is not None
        h5_name, h5_path = data_item.text.strip().split(":")
        with h5py.File(written["combined"].parent / h5_name, "r") as h5:
            data = h5[h5_path][...]
        if name == "F":
            assert data.shape[1] == 3
            assert np.array_equal(
                data, np.broadcast_to(CONSTANT, data.shape)
            ), "constant vector field did not round-trip exactly"
        elif name == "CellTags":
            assert data.size == n_cells_global
            counts = {v: int((data == v).sum()) for v in np.unique(data)}
            assert set(counts) == {1.0, 2.0}
            assert sum(counts.values()) == n_cells_global
