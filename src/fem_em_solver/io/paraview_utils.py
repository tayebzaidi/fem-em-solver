"""ParaView output utilities for FEM-EM solver."""

import copy
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
            if grid.find("Topology") is not None:
                # Owns its own topology (a write_meshtags facet grid): its
                # attributes are indexed by facets, not cells, so they cannot
                # be lifted onto the mesh grid. Leave it as its own block.
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


def write_xdmf_with_tags(
    filename, mesh, cell_tags, functions, comm=MPI.COMM_WORLD, facet_tags=None
):
    """
    Write a single XDMF output containing mesh, optional cell tags, and fields.

    Cell tags are written as a DG0 cell array named "CellTags" on the same
    grid as the fields (see :func:`cell_tags_to_function`), so ParaView can
    threshold on them like any other array.

    Optional ``facet_tags`` are written with ``XDMFFile.write_meshtags`` into
    the *same* file, as their own (facet-topology) grid — the sheets cannot
    live on the cell grid, so they stay a separate block, but the caller gets
    one file instead of two. :func:`consolidate_xdmf_grids` is still called
    once, last, and only merges the *field* grids onto the mesh grid; the
    facet grid owns its own Topology and is left alone.

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
    facet_tags : dolfinx.mesh.MeshTags | None
        Optional facet tags, written into the same file as a facet grid
        (array name is the tag object's ``name``, e.g. ``mesh_tags``).
    """
    from dolfinx import io

    filename = Path(filename)
    xdmf_file = filename.with_suffix(".xdmf")
    h5_file = filename.with_suffix(".h5")

    if facet_tags is not None:
        # write_meshtags needs facet -> cell connectivity to place the tagged
        # entities in the mesh's topology (known-issues 9).
        tdim = mesh.topology.dim
        mesh.topology.create_connectivity(tdim - 1, tdim)

    with io.XDMFFile(comm, xdmf_file, "w") as xdmf:
        xdmf.write_mesh(mesh)
        if cell_tags is not None:
            xdmf.write_function(cell_tags_to_function(mesh, cell_tags))

        for _, func in functions.items():
            xdmf.write_function(func)

        if facet_tags is not None:
            xdmf.write_meshtags(facet_tags, mesh.geometry)

    # One grid per file, or ParaView loads a multiblock and Plot Over Line
    # returns NaN for every array outside the first block.
    consolidate_xdmf_grids(xdmf_file, comm=comm)

    if comm.rank == 0:
        return xdmf_file, h5_file
    return None, None


def _consolidate_xdmf_time_series(xdmf_path, times, comm=MPI.COMM_WORLD):
    """Merge dolfinx's per-field temporal collections into **one** collection.

    ``XDMFFile.write_function(f, t)`` emits one top-level ``<Grid
    CollectionType="Temporal">`` *per function*, each holding one uniform
    child per ``t``. ParaView loads the siblings as a multiblock (the same
    Plot-Over-Line NaN trap :func:`consolidate_xdmf_grids` fixes) while
    :func:`consolidate_xdmf_grids` itself would flatten the time axis away
    ("single-timestep files only", above).

    This rewrite keeps the time axis: the children of the *first* collection
    become the hosts, every other collection's attributes are moved onto the
    host with the matching ``<Time Value>``, the mesh grid's Topology and
    Geometry are copied into each host (so the xi:include targets can go
    away with the mesh grid) and the single surviving collection is the only
    top-level grid left in the Domain.

    ``times`` is the write order; the output children follow it. Rank 0 does
    the rewrite, collective barrier at the end.
    """
    if comm.rank == 0:
        xdmf_path = Path(xdmf_path)
        tree = ET.parse(xdmf_path)
        domain = tree.getroot().find("Domain")

        grids = domain.findall("Grid")
        mesh_grid = next(
            g for g in grids
            if g.get("GridType", "Uniform") == "Uniform"
            and g.find("Topology") is not None
        )
        collections = [
            g for g in grids
            if g is not mesh_grid and g.get("CollectionType") == "Temporal"
        ]
        if not collections:
            raise ValueError(f"{xdmf_path}: no temporal collection to consolidate")

        def _time_key(uniform):
            time = uniform.find("Time")
            if time is None:
                raise ValueError(f"{xdmf_path}: a child grid carries no <Time>")
            return f"{float(time.get('Value')):.12g}"

        keys = [f"{float(t):.12g}" for t in times]

        hosts = {}
        for uniform in collections[0].findall("Grid"):
            hosts[_time_key(uniform)] = uniform
        missing = [k for k in keys if k not in hosts]
        if missing:
            raise ValueError(f"{xdmf_path}: no grid written at t in {missing}")

        for collection in collections[1:]:
            for uniform in collection.findall("Grid"):
                host = hosts[_time_key(uniform)]
                for attr in uniform.findall("Attribute"):
                    host.append(attr)

        # The hosts reference the mesh grid through xi:include xpointers;
        # inline Topology/Geometry so the mesh grid can be dropped and the
        # collection is the Domain's only child (one vtkUnstructuredGrid
        # per time step rather than a multiblock).
        topology = mesh_grid.find("Topology")
        geometry = mesh_grid.find("Geometry")
        include = "{http://www.w3.org/2001/XInclude}include"
        for key in keys:
            host = hosts[key]
            for inc in host.findall(include):
                host.remove(inc)
            host.insert(0, copy.deepcopy(geometry))
            host.insert(0, copy.deepcopy(topology))

        series = ET.Element(
            "Grid",
            {
                "Name": "TimeSeries",
                "GridType": "Collection",
                "CollectionType": "Temporal",
            },
        )
        for key in keys:
            series.append(hosts[key])

        for grid in grids:
            domain.remove(grid)
        domain.append(series)

        ET.indent(tree)
        tree.write(xdmf_path, xml_declaration=True, encoding="utf-8")
    comm.barrier()


def write_xdmf_time_series(
    filename, mesh, cell_tags, steps, comm=MPI.COMM_WORLD, facet_tags=None
):
    """Write one XDMF file whose steps are ParaView time steps (``OPS-49``).

    :func:`write_xdmf_with_tags` is single-state: its
    :func:`consolidate_xdmf_grids` pass drops ``<Time>``, so an example with
    two rungs or two drive states had to write two files or bypass the
    helper (known-issues 2026-09-16). This writer is the additive
    alternative and leaves both of those functions untouched.

    Parameters
    ----------
    filename : str or Path
        Output base path (".xdmf" is applied automatically). Avoid dotted
        stems: ``Path.with_suffix`` truncates them.
    mesh : dolfinx.mesh.Mesh
        The one mesh every step is written on.
    cell_tags : dolfinx.mesh.MeshTags | None
        Written as the DG0 array "CellTags" at *every* step, so ParaView's
        Threshold filter works at each time.
    steps : sequence[tuple[float, dict[str, dolfinx.fem.Function]]]
        ``[(t, {name: Function}), ...]``. Every step must carry the same
        field names and the times must be distinct. ``write_function`` names
        the grid after the function's own ``name``, so each key must equal
        its function's ``name`` -- otherwise two fields silently collide.
    comm : MPI.Comm
        MPI communicator (the write is collective).
    facet_tags : None
        Rejected: facet tags are a separate topology grid and cannot be
        carried on the cell grid's time steps. Out of scope for this writer.

    Returns
    -------
    tuple[Path, Path] | tuple[None, None]
        ``(xdmf_path, h5_path)`` on rank 0, ``(None, None)`` elsewhere.
    """
    from dolfinx import io

    if facet_tags is not None:
        raise ValueError(
            "write_xdmf_time_series does not support facet_tags: facet tags "
            "own their own topology grid, which has no per-step counterpart. "
            "Write them to a separate file with write_xdmf_with_tags."
        )

    steps = list(steps)
    if not steps:
        raise ValueError("write_xdmf_time_series needs at least one step")

    times = [float(t) for t, _ in steps]
    if len(set(f"{t:.12g}" for t in times)) != len(times):
        raise ValueError(f"write_xdmf_time_series needs distinct times, got {times}")

    field_names = list(steps[0][1])
    for t, fields in steps:
        if list(fields) != field_names:
            raise ValueError(
                "every step must carry the same field names in the same order: "
                f"t={t} has {list(fields)}, expected {field_names}"
            )
        for name, func in fields.items():
            if func.name != name:
                raise ValueError(
                    f"field key {name!r} does not match its function's name "
                    f"{func.name!r}; XDMFFile.write_function names the grid "
                    "after the function, so mismatched keys collide"
                )

    filename = Path(filename)
    xdmf_file = filename.with_suffix(".xdmf")
    h5_file = filename.with_suffix(".h5")

    tag_func = cell_tags_to_function(mesh, cell_tags) if cell_tags is not None else None
    if tag_func is not None and tag_func.name in field_names:
        raise ValueError(f"field name {tag_func.name!r} is reserved for cell tags")

    with io.XDMFFile(comm, xdmf_file, "w") as xdmf:
        xdmf.write_mesh(mesh)
        for (t, fields), t_float in zip(steps, times):
            if tag_func is not None:
                xdmf.write_function(tag_func, t_float)
            for func in fields.values():
                xdmf.write_function(func, t_float)

    _consolidate_xdmf_time_series(xdmf_file, times, comm=comm)

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
