"""Static "what is the setup" figure for an example guide (`EX-57`).

Every runnable example under ``examples/`` owes its same-stem guide one
committed PNG that shows the *problem setup* — the tagged regions of the mesh
(conductor, phantom, ports, air box) as a clipped 3-D view beside a mid-plane
slice — so a reader can see what is being simulated before reading a single
number. This module is the one place that draws it, so every figure in the
tree reads the same way (same colours per region class, same two panels).

Design constraints, each already paid for elsewhere in the repo:

* **Opt-in.** The figure is rendered only when ``FEM_EM_SETUP_FIGURES=1`` is
  in the environment (or ``enabled=True`` is passed). Renders are not
  bit-reproducible across VTK builds, so an always-on call would dirty the
  committed PNG on every corpus run. The scheduled corpus runs never set the
  variable; the `EX-57` figure slots do.
* **Rank-safe.** Every rank hands its *owned* cells to rank 0, which merges
  and renders; ghosts are excluded through ``index_map(tdim).size_local``.
  Rendering a rank-local partition would draw a mesh with a rank boundary
  through it — the same class of defect as an unreduced ``cell_tags.values``.
* **Headless.** PyVista is used off-screen; the ``bad X server connection``
  warning VTK prints in the container is benign (measured 2026-09-13, the
  screenshot is written).
* **Root-owned output.** The container runs as root on a bind mount, so the
  PNG is re-owned through :func:`~fem_em_solver.io.paraview_utils.adopt_host_ownership`.

Typical call, immediately after the example has built its mesh::

    from fem_em_solver.post.setup_figure import write_setup_figure
    write_setup_figure(
        mesh, cell_tags, FIGURE_DIR / f"{BASENAME}_setup.png",
        region_names={1: "conductor", 2: "air", 3: "phantom", 101: "port P1"},
        hide_tags=(2,), translucent_tags=(3,),
        title="mesh:3 — 4-leg birdcage, phantom, four port boxes",
    )

The guide then embeds it under a ``## Setup figure`` heading with a caption
naming the regions and the slice plane; ``scripts/testing/check_example_setup_figures.py``
is the census that finds the examples still owing one.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
from mpi4py import MPI

ENV_FLAG = "FEM_EM_SETUP_FIGURES"

# One colour per region *class*, keyed by the name the caller gives the tag,
# so a "conductor" is copper in every figure in the tree whatever its tag
# number is. Anything unnamed cycles through the fallback palette.
CLASS_COLOURS: dict[str, str] = {
    "conductor": "#b87333",  # copper
    "wire": "#b87333",
    "coil": "#b87333",
    "phantom": "#3b8ec2",  # saline blue
    "sphere": "#3b8ec2",
    "dielectric": "#3b8ec2",
    "air": "#d9d9d9",
    "vacuum": "#d9d9d9",
    "port": "#d62728",  # red — small features must pop
    "sheet": "#d62728",
    "implant": "#7f7f7f",
    "pml": "#bcbd22",
    "wall": "#7f7f7f",
}
FALLBACK_PALETTE: Sequence[str] = (
    "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b", "#e377c2", "#17becf",
)


def figures_enabled(enabled: bool | None = None) -> bool:
    """``enabled`` wins; otherwise the environment flag decides."""
    if enabled is not None:
        return bool(enabled)
    return os.environ.get(ENV_FLAG, "").strip() in {"1", "true", "yes", "on"}


def colour_for(name: str, ordinal: int) -> str:
    """Colour of a region from its name (class keyword match) or its ordinal."""
    lowered = name.lower()
    for keyword, colour in CLASS_COLOURS.items():
        if keyword in lowered:
            return colour
    return FALLBACK_PALETTE[ordinal % len(FALLBACK_PALETTE)]


def _owned_cell_tags(mesh, cell_tags) -> np.ndarray:
    """Per-owned-cell tag array (0 where the cell carries no tag)."""
    tdim = mesh.topology.dim
    n_owned = mesh.topology.index_map(tdim).size_local
    tags = np.zeros(n_owned, dtype=np.int64)
    if cell_tags is not None:
        idx = np.asarray(cell_tags.indices)
        keep = idx < n_owned
        tags[idx[keep]] = np.asarray(cell_tags.values)[keep]
    return tags


def gather_tagged_grid(mesh, cell_tags, comm: MPI.Comm | None = None):
    """Merge every rank's owned cells into one PyVista grid on rank 0.

    Returns the ``pyvista.UnstructuredGrid`` on rank 0 (with a ``"region"``
    cell array holding the tag) and ``None`` elsewhere.
    """
    from dolfinx.plot import vtk_mesh

    comm = comm if comm is not None else mesh.comm
    tdim = mesh.topology.dim
    n_owned = mesh.topology.index_map(tdim).size_local
    cells, cell_types, points = vtk_mesh(mesh, tdim, np.arange(n_owned, dtype=np.int32))
    piece = (
        np.asarray(cells),
        np.asarray(cell_types, dtype=np.uint8),
        np.asarray(points, dtype=np.float64),
        _owned_cell_tags(mesh, cell_tags),
    )
    pieces = comm.gather(piece, root=0)
    if comm.rank != 0:
        return None

    import pyvista as pv

    grids = []
    for cells_r, types_r, points_r, tags_r in pieces:
        if len(types_r) == 0:
            continue
        grid = pv.UnstructuredGrid(cells_r, types_r, points_r)
        grid.cell_data["region"] = tags_r
        grids.append(grid)
    if not grids:
        raise RuntimeError("gather_tagged_grid: no cells on any rank")
    merged = grids[0]
    for grid in grids[1:]:
        merged = merged.merge(grid, merge_points=False)
    return merged


def write_setup_figure(
    mesh,
    cell_tags,
    path: str | Path,
    *,
    region_names: Mapping[int, str],
    title: str = "",
    hide_tags: Iterable[int] = (),
    translucent_tags: Iterable[int] = (),
    slice_normal: Sequence[float] = (0.0, 0.0, 1.0),
    slice_origin: Sequence[float] | None = None,
    clip_normal: Sequence[float] | None = None,
    show_edges_on_slice: bool = True,
    window_size: Sequence[int] = (1600, 720),
    enabled: bool | None = None,
    comm: MPI.Comm | None = None,
) -> Path | None:
    """Render the two-panel setup figure to ``path`` (rank 0) and return it.

    Parameters
    ----------
    mesh, cell_tags
        The example's DolfinX mesh and its cell ``MeshTags``.
    path
        Output PNG, normally ``examples/<group>/figures/<basename>_setup.png``.
    region_names
        ``{tag: human name}`` for every tag worth drawing; the name picks the
        colour class (see :data:`CLASS_COLOURS`) and labels the legend.
    hide_tags
        Tags left out of the 3-D panel (the air box, typically). They still
        appear in the slice so the domain extent is visible.
    translucent_tags
        Tags drawn at 30 % opacity in the 3-D panel (the phantom, so the
        conductors inside it stay visible).
    slice_normal, slice_origin
        The cut plane of the right-hand panel; origin defaults to the mesh
        centre.
    clip_normal
        Optional half-space clip of the 3-D panel (e.g. ``(0, -1, 0)`` keeps
        y < 0) for fixtures whose interior a translucent region cannot show;
        off by default because it also removes every small region on the cut
        side (a port box), and the legend still lists them.
    enabled
        Overrides the ``FEM_EM_SETUP_FIGURES`` environment flag.

    Returns
    -------
    Path or None
        The written file on rank 0; ``None`` on other ranks or when disabled.
        Every rank returns together (the gather is collective), so the call is
        safe inside collective code.
    """
    if not figures_enabled(enabled):
        return None
    comm = comm if comm is not None else mesh.comm
    grid = gather_tagged_grid(mesh, cell_tags, comm)
    if comm.rank != 0:
        return None
    try:
        return _render(
            grid,
            mesh.topology.dim,
            Path(path),
            region_names=region_names,
            title=title,
            hide_tags=hide_tags,
            translucent_tags=translucent_tags,
            slice_normal=slice_normal,
            slice_origin=slice_origin,
            clip_normal=clip_normal,
            show_edges_on_slice=show_edges_on_slice,
            window_size=window_size,
        )
    except Exception as exc:  # a figure must never take the example down
        print(f"[setup-figure] FAILED for {path}: {exc!r}", flush=True)
        if os.environ.get(ENV_FLAG + "_STRICT", "") == "1":
            raise
        return None


def _render(
    grid,
    tdim: int,
    path: Path,
    *,
    region_names,
    title,
    hide_tags,
    translucent_tags,
    slice_normal,
    slice_origin,
    clip_normal,
    show_edges_on_slice,
    window_size,
) -> Path:
    """Rank-0 body of :func:`write_setup_figure`; raises on any render failure."""
    import pyvista as pv

    pv.OFF_SCREEN = True
    path.parent.mkdir(parents=True, exist_ok=True)

    hide = set(int(t) for t in hide_tags)
    translucent = set(int(t) for t in translucent_tags)
    present = sorted(int(t) for t in np.unique(grid.cell_data["region"]))
    names = {int(t): str(n) for t, n in region_names.items()}
    ordered = [t for t in present if t in names] + [t for t in present if t not in names]
    colours = {
        tag: colour_for(names.get(tag, f"tag {tag}"), i) for i, tag in enumerate(ordered)
    }

    bounds = np.asarray(grid.bounds).reshape(3, 2)
    centre = bounds.mean(axis=1)
    origin = np.asarray(slice_origin, dtype=float) if slice_origin is not None else centre

    plotter = pv.Plotter(off_screen=True, shape=(1, 2), window_size=list(window_size), border=False)
    plotter.set_background("white")

    # ---- left: 3-D view of the tagged regions (optionally clipped) ---------------------
    plotter.subplot(0, 0)
    for tag in ordered:
        if tag in hide:
            continue
        part = grid.extract_cells(np.flatnonzero(grid.cell_data["region"] == tag))
        if part.n_cells == 0:
            continue
        if clip_normal is not None and tdim == 3:
            part = part.clip(normal=clip_normal, origin=centre, invert=False)
        surface = part.extract_surface() if tdim == 3 else part
        if surface.n_points == 0 or surface.n_cells == 0:
            # A small region (a port box) can lie wholly in the clipped-away
            # half-space; PyVista refuses an empty mesh.
            continue
        label = names.get(tag, f"tag {tag}")
        plotter.add_mesh(
            surface,
            color=colours[tag],
            opacity=0.3 if tag in translucent else 1.0,
            show_edges=tdim == 2,
            edge_color="#555555",
            smooth_shading=False,
            label=label,
        )
    # One legend row per colour class ("port P1, P2, P3, P4", not four rows),
    # listing every named tag of the class whether or not the clip kept it.
    by_colour: dict[str, list[str]] = {}
    for tag in ordered:
        if tag in names:
            by_colour.setdefault(colours[tag], []).append(names[tag] + (" (hidden)" if tag in hide else ""))
    grouped = []
    for colour, labels in by_colour.items():
        if len(labels) <= 2:
            text = ", ".join(labels)
        else:
            text = f"{labels[0]} … {labels[-1]}"
        grouped.append((text, colour))
    if grouped:
        # PyVista 0.48.4's `map_loc_to_pos` (pyvista/plotting/renderer.py)
        # computes the legend's *x* anchor from ``size[1]`` (the height) for
        # any ``'right'`` location — `x = 1 - size[1] -
        # border` for 'right' — instead of ``size[0]`` (the width). With
        # ``loc="upper right"`` and a box wider than it is tall (true for
        # every setup figure: 2-3 short rows, several named tags each), the
        # box's right edge lands past the subplot's own viewport edge and
        # every row is clipped there — independent of label length or font
        # size, which is why widening ``size[0]`` alone (tried first, `EX-57`
        # this fixture, 2026-09-18) made it worse, not better. ``'left'``
        # locations take the bug-free branch (`x = border`, no width
        # dependency), so anchoring here instead keeps the whole box on
        # screen for any width. "upper left" collides with the title text
        # added below and "lower left" collides with the axes orientation
        # widget, so "center left" (still bug-free — the `'left' in loc`
        # branch matches) is the seam that hits neither.
        max_chars = max((len(text) for text, _ in grouped), default=0)
        legend_width = min(0.6, max(0.24, 0.05 + 0.011 * max_chars))
        plotter.add_legend(
            grouped, bcolor="white", face=None,
            size=(legend_width, 0.035 * len(grouped) + 0.02), loc="center left",
        )
    plotter.add_text(title or path.stem, position="upper_left", font_size=11, color="black")
    plotter.add_text(
        "3-D: tagged regions" + (", half-space clipped" if clip_normal is not None and tdim == 3 else ""),
        position="lower_right",
        font_size=9,
        color="#444444",
    )
    plotter.show_axes()
    if tdim == 3:
        plotter.view_isometric()
    else:
        plotter.view_xy()

    # ---- right: slice through the origin, every region incl. air ---------
    plotter.subplot(0, 1)
    if tdim == 3:
        cut = grid.slice(normal=slice_normal, origin=origin)
        panel_label = (
            f"slice: normal {tuple(float(c) for c in slice_normal)} through "
            f"({origin[0]:.3g}, {origin[1]:.3g}, {origin[2]:.3g}) m"
        )
    else:
        cut = grid
        panel_label = "mesh with cell tags"
    for tag in ordered:
        part = cut.extract_cells(np.flatnonzero(cut.cell_data["region"] == tag))
        if part.n_cells == 0 or part.n_points == 0:
            continue
        plotter.add_mesh(
            part,
            color=colours[tag],
            show_edges=show_edges_on_slice,
            edge_color="#666666",
            line_width=0.5,
            label=names.get(tag, f"tag {tag}"),
        )
    plotter.add_text(panel_label, position="lower_right", font_size=9, color="#444444")
    plotter.show_axes()
    if tdim == 3:
        normal = np.asarray(slice_normal, dtype=float)
        normal = normal / np.linalg.norm(normal)
        plotter.camera_position = [tuple(origin + normal * 10.0 * np.ptp(bounds, axis=1).max()), tuple(origin), (0.0, 1.0, 0.0) if abs(normal[1]) < 0.9 else (1.0, 0.0, 0.0)]
        plotter.reset_camera()
    else:
        plotter.view_xy()

    plotter.screenshot(str(path), transparent_background=False)
    plotter.close()

    try:
        from fem_em_solver.io.paraview_utils import adopt_host_ownership

        adopt_host_ownership(path.parent, comm=MPI.COMM_SELF)
    except Exception:  # ownership is a papercut fix, never a failure
        pass

    size_kib = path.stat().st_size / 1024.0
    print(
        f"[setup-figure] wrote {path} ({size_kib:.0f} KiB; regions "
        + ", ".join(f"{tag}={names.get(tag, '?')}" for tag in ordered)
        + ")",
        flush=True,
    )
    return path


__all__ = [
    "ENV_FLAG",
    "CLASS_COLOURS",
    "figures_enabled",
    "colour_for",
    "gather_tagged_grid",
    "write_setup_figure",
]
