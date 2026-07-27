"""ParaView output utilities for FEM-EM solver."""

import os
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


def write_xdmf_with_tags(filename, mesh, cell_tags, functions, comm=MPI.COMM_WORLD):
    """
    Write a single XDMF output containing mesh, optional cell tags, and fields.

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
            tdim = mesh.topology.dim
            mesh.topology.create_connectivity(tdim, tdim)
            xdmf.write_meshtags(cell_tags, mesh.geometry)

        for _, func in functions.items():
            xdmf.write_function(func)

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

    # Individual files (one field per file)
    for name, (_, lagrange_func) in fields.items():
        xdmf_path = output_dir / f"{basename}_{name}.xdmf"
        with io.XDMFFile(comm, xdmf_path, "w") as xdmf:
            xdmf.write_mesh(mesh)
            if cell_tags is not None:
                tdim = mesh.topology.dim
                mesh.topology.create_connectivity(tdim, tdim)
                xdmf.write_meshtags(cell_tags, mesh.geometry)
            xdmf.write_function(lagrange_func)
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
