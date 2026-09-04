"""Closed-form round trip for ``write_xdmf_with_tags(facet_tags=...)`` (OPS-38).

The keyword is additive: without it the file carries no facet grid at all
(the negative control below asserts ``read_meshtags`` raises), with it the
tags survive a write/read cycle well enough that a ``ds`` integral over the
read-back tags reproduces the exact area of the tagged face.
"""

import numpy as np
import pytest
import ufl
from dolfinx import default_scalar_type, fem, io, mesh
from mpi4py import MPI

from fem_em_solver.io.paraview_utils import write_xdmf_with_tags

TAG = 7
# x = 0 face of the unit cube: exactly 1 x 1.
EXACT_AREA = 1.0


def _tagged_cube(comm, n=8):
    """Unit cube with the ``x = 0`` face's facets tagged ``TAG``."""
    msh = mesh.create_unit_cube(comm, n, n, n)
    tdim = msh.topology.dim
    # Facet -> cell connectivity before any facet write or ds integral
    # (known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    facets = mesh.locate_entities_boundary(
        msh, tdim - 1, lambda x: np.isclose(x[0], 0.0)
    )
    facets = np.sort(facets)
    values = np.full(facets.shape, TAG, dtype=np.int32)
    tags = mesh.meshtags(msh, tdim - 1, facets, values)
    tags.name = "mesh_tags"
    return msh, tags


def _owned_tag_count(msh, tags):
    """Rank-local count of *owned* tagged facets (ghosts would double-count)."""
    local = msh.topology.index_map(msh.topology.dim - 1).size_local
    return int(np.count_nonzero(tags.indices < local))


def test_facet_tags_round_trip_reproduces_the_face_area(tmp_path):
    comm = MPI.COMM_WORLD
    msh, tags = _tagged_cube(comm)

    write_count = comm.allreduce(_owned_tag_count(msh, tags), op=MPI.SUM)
    assert write_count > 0

    base = comm.bcast(str(tmp_path / "facet_round_trip"), root=0)
    write_xdmf_with_tags(base, msh, None, {}, comm=comm, facet_tags=tags)

    with io.XDMFFile(comm, base + ".xdmf", "r") as xdmf:
        read_msh = xdmf.read_mesh(name="mesh")
        read_msh.topology.create_connectivity(
            read_msh.topology.dim - 1, read_msh.topology.dim
        )
        read_tags = xdmf.read_meshtags(read_msh, name="mesh_tags")

    # (i) the tag set read back, reduced across ranks
    local_set = set(int(v) for v in np.unique(read_tags.values))
    global_set = set().union(*comm.allgather(local_set))
    assert global_set == {TAG}

    # (ii) the tagged facet count, MPI-summed, equals the write-side count
    read_count = comm.allreduce(_owned_tag_count(read_msh, read_tags), op=MPI.SUM)
    assert read_count == write_count, (read_count, write_count)

    # (iii) the closed form: the x = 0 face of the unit cube has area 1
    ds = ufl.Measure("ds", domain=read_msh, subdomain_data=read_tags)
    area = comm.allreduce(
        fem.assemble_scalar(
            fem.form(fem.Constant(read_msh, default_scalar_type(1.0)) * ds(TAG))
        ),
        op=MPI.SUM,
    )
    assert abs(area - EXACT_AREA) < 1e-12, area


def test_without_the_keyword_there_is_no_facet_grid(tmp_path):
    """Negative control: the default write leaves nothing to read back."""
    comm = MPI.COMM_WORLD
    msh, _ = _tagged_cube(comm)

    base = comm.bcast(str(tmp_path / "no_facet_grid"), root=0)
    write_xdmf_with_tags(base, msh, None, {}, comm=comm)

    with io.XDMFFile(comm, base + ".xdmf", "r") as xdmf:
        read_msh = xdmf.read_mesh(name="mesh")
        read_msh.topology.create_connectivity(
            read_msh.topology.dim - 1, read_msh.topology.dim
        )
        with pytest.raises(Exception):
            xdmf.read_meshtags(read_msh, name="mesh_tags")
