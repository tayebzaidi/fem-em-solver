"""ParaView output utilities for FEM-EM solver."""

import os
import xml.etree.ElementTree as ET
from pathlib import Path

from mpi4py import MPI


def adopt_host_ownership(output_dir, comm=MPI.COMM_WORLD) -> int:
    """Give files under ``output_dir`` the same owner as the directory holding it.

    The dev container runs as root while the repository is bind-mounted from the
    host, so anything written lands root-owned and the host user cannot delete or
    overwrite it without sudo. Re-owning to match the enclosing directory (which
    the bind mount keeps as the host user) removes that papercut.

    No-op when not running as root, when the ids already match, or when the
    filesystem refuses the change -- output should never be lost to a
    housekeeping step, so failures here are swallowed deliberately.

    Returns the number of paths successfully re-owned (0 on non-zero ranks).
    """
    if comm.rank != 0:
        return 0

    output_dir = Path(output_dir)
    if not output_dir.exists() or not hasattr(os, "geteuid") or os.geteuid() != 0:
        return 0

    try:
        reference = output_dir.parent.stat()
    except OSError:
        return 0

    uid, gid = reference.st_uid, reference.st_gid
    if uid == 0 and gid == 0:
        return 0

    changed = 0
    targets = [output_dir, *output_dir.rglob("*")]
    for path in targets:
        try:
            info = path.stat()
            if (info.st_uid, info.st_gid) != (uid, gid):
                os.chown(path, uid, gid)
                changed += 1
        except OSError:
            continue

    return changed


def consolidate_xdmf_grids(xdmf_path, comm=MPI.COMM_WORLD):
    """Merge every field grid in a dolfinx XDMF file into the mesh grid.

    ``XDMFFile.write_function`` emits one top-level ``<Grid>`` (a temporal
    collection referencing the mesh topology/geometry via xi:include) per
    function. ParaView's Xdmf3 reader turns sibling grids into a
    vtkMultiBlockDataSet: rendering filters cope, but point-probing filters
    (Plot Over Line, Probe) only sample one block, so arrays from the other
    grids come back all-NaN. Rewriting the light-data XML so all
    ``<Attribute>`` elements live on the single mesh grid makes the file load
    as one vtkUnstructuredGrid; the ``.h5`` heavy data is untouched.

    Only valid when every attribute was written on the same mesh — true for
    all output in this module, where cell tags go through
    :func:`cell_tags_to_function` (a DG0 field on the field grid) rather than
    ``write_meshtags`` (which writes its own, differently ordered, topology).

    Single-timestep files only: time collections are collapsed and ``<Time>``
    elements dropped. Rank 0 does the rewrite; collective barrier at the end.
    """
    if comm.rank == 0:
        xdmf_path = Path(xdmf_path)
        tree = ET.parse(xdmf_path)
        domain = tree.getroot().find("Domain")

        # The mesh grid is the uniform one that actually owns Topology/Geometry.
        grids = domain.findall("Grid")
        mesh_grid = next(
            g for g in grids
            if g.get("GridType", "Uniform") == "Uniform"
            and g.find("Topology") is not None
        )

        for grid in grids:
            if grid is mesh_grid:
                continue
            # Function grids are temporal collections; descend to every
            # uniform grid inside and lift out its attributes.
            for uniform in grid.iter("Grid"):
                for attr in uniform.findall("Attribute"):
                    mesh_grid.append(attr)
            domain.remove(grid)

        ET.indent(tree)
        tree.write(xdmf_path, xml_declaration=True, encoding="utf-8")
    comm.barrier()


def cell_tags_to_function(mesh, cell_tags, name="CellTags"):
    """Represent MeshTags as a DG0 function for ParaView output.

    ``XDMFFile.write_meshtags`` stores tags in a separate XDMF grid, which
    ParaView exposes as its own block — thresholding on the tags together with
    the fields is then awkward. A DG0 function written with ``write_function``
    lands as an ordinary cell-data array on the same grid as the fields, so
    the Threshold filter sees it directly alongside A, B, etc.

    Untagged cells get value 0 (no mesh generator tag uses 0).
    """
    from dolfinx import fem

    V0 = fem.functionspace(mesh, ("DG", 0))
    tags = fem.Function(V0, name=name)
    tags.x.array[:] = 0.0
    # One DG0 dof per cell; go through the dofmap rather than assuming
    # dof index == cell index.
    cell_dofs = V0.dofmap.list.reshape(-1)
    tags.x.array[cell_dofs[cell_tags.indices]] = cell_tags.values
    tags.x.scatter_forward()
    return tags


def write_xdmf_with_tags(filename, mesh, cell_tags, functions, comm=MPI.COMM_WORLD):
    """
    Write a single XDMF output containing mesh, optional cell tags, and fields.

    Cell tags are written as a DG0 cell array named "CellTags" on the same
    grid as the fields (see :func:`cell_tags_to_function`), so ParaView can
    threshold on them like any other array.

    Parameters
    ----------
    filename : str or Path
        Output base path (".xdmf" extension is applied automatically).
    mesh : dolfinx.mesh.Mesh
        Mesh to export.
    cell_tags : dolfinx.mesh.MeshTags | None
        Optional cell tags to write for ParaView thresholding.
    functions : dict[str, dolfinx.fem.Function]
        Mapping of field name -> function to write on the same grid.
    comm : MPI.Comm
        MPI communicator.
    """
    from dolfinx import io

    filename = Path(filename)
    xdmf_file = filename.with_suffix(".xdmf")
    h5_file = filename.with_suffix(".h5")

    with io.XDMFFile(comm, xdmf_file, "w") as xdmf:
        xdmf.write_mesh(mesh)
        if cell_tags is not None:
            xdmf.write_function(cell_tags_to_function(mesh, cell_tags))

        for _, func in functions.items():
            xdmf.write_function(func)

    # One grid per file, or ParaView loads a multiblock and Plot Over Line
    # returns NaN for every array outside the first block.
    consolidate_xdmf_grids(xdmf_file, comm=comm)

    if comm.rank == 0:
        return xdmf_file, h5_file
    return None, None


def write_combined_paraview_output(
    output_dir,
    basename,
    mesh,
    cell_tags,
    fields,
    comm=MPI.COMM_WORLD,
):
    """
    Write standardized ParaView outputs.

    Produces per-field files and one combined file containing all selected fields
    plus cell tags.

    Parameters
    ----------
    output_dir : Path | str
        Output directory.
    basename : str
        Base filename (e.g. "straight_wire").
    mesh : dolfinx.mesh.Mesh
        Mesh to export.
    cell_tags : dolfinx.mesh.MeshTags | None
        Optional cell tags.
    fields : dict[str, tuple[Function, Function]]
        Mapping name -> (original_function, lagrange_function).
        The lagrange function is used for XDMF output compatibility.
    comm : MPI.Comm
        MPI communicator.

    Returns
    -------
    dict[str, Path]
        Paths of written files.
    """
    from dolfinx import io

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    written_files = {}

    # Cell tags as a DG0 array, so every file carries them on the field grid.
    tag_func = cell_tags_to_function(mesh, cell_tags) if cell_tags is not None else None

    # Individual files (one field per file)
    for name, (_, lagrange_func) in fields.items():
        xdmf_path = output_dir / f"{basename}_{name}.xdmf"
        with io.XDMFFile(comm, xdmf_path, "w") as xdmf:
            xdmf.write_mesh(mesh)
            if tag_func is not None:
                xdmf.write_function(tag_func)
            xdmf.write_function(lagrange_func)
        consolidate_xdmf_grids(xdmf_path, comm=comm)
        written_files[name] = xdmf_path

    # Combined file (all fields + tags)
    lagrange_funcs = {name: lag_func for name, (_, lag_func) in fields.items()}
    combined_base = output_dir / f"{basename}_combined"
    xdmf_file, _ = write_xdmf_with_tags(
        combined_base,
        mesh,
        cell_tags,
        lagrange_funcs,
        comm=comm,
    )
    if xdmf_file:
        written_files["combined"] = xdmf_file

    # Container runs as root; hand the results back to the host user.
    adopt_host_ownership(output_dir, comm=comm)

    return written_files
