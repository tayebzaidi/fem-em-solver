"""`GEO-28` — C4 census of the unloaded F-small birdcage mesh.

MEASUREMENT ONLY. This script asserts nothing (beyond printing the 116 085
``size_global`` control and its ratio), is imported by nothing, and changes no
`src/` file, band or record. It answers one question: does quadrant 2 — the
leg-2 / `+ŷ`…`−x̂` neighbourhood — carry a cell-count, volume or `h` spread of
the order of 3% that the other three quadrants do not?

The mesh is `birdcage_port_domain` exactly as
``tests/mesh/test_birdcage_port_sheets._build(True)`` calls it (the `WF-6`
step-4 fixture, 116 085 cells).

Quadrant `Q_n` is the ±45° sector about leg `n`'s azimuth `φ_n`
(0 / 90 / 180 / 270°). Membership is the squared-projection test on cell
midpoints — no ``atan2``, no ``sqrt`` inside a comparison: with
``u_n = (cos φ_n, sin φ_n)`` and ``d = x·u_x + y·u_y``, a midpoint is in `Q_n`
iff ``d > 0`` and ``d² > 0.5·(x² + y²)``, since ``cos 45° = 1/√2``.

Rank-safety: every count and volume is rank-local and reduced with
``MPI.SUM``; ghost cells are counted once by restricting to
``index_map(3).size_local`` (`OPS-39`'s ``_census`` fix); ``dolfinx.cpp.mesh.h``
takes *local* cell indices; ``size_global`` is read after distribution.

Run (real build, no solve, no complex mode):

    mpiexec -n 2 python3 -u scripts/probes/geo28_birdcage_c4_census.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

import dolfinx.cpp as _dcpp

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.mesh.test_birdcage_port_sheets import _build  # noqa: E402
from tests.mesh.test_birdcage_leg_gaps import LEG_GAP_LENGTH  # noqa: E402
from tests.mesh.test_birdcage_port_tags import (  # noqa: E402
    COIL_LENGTH,
    LEG_COUNT,
    LEG_SPACING,
    LEG_WIDTH,
    RING_MINOR_RADIUS,
    RING_RADIUS,
)

# The control: `20260908T004020Z_WF-6.log:1881`. Printed and compared, never
# asserted — a miss is an `OPS-18`-class drift to record and stop on.
CONTROL_CELL_RECORD = 116085

CONDUCTOR_TAG, AIR_TAG, PHANTOM_TAG = 1, 2, 3

# (3)'s shell: the near field `WF-6` step 4b evaluates in.
SHELL_LO_FRAC, SHELL_HI_FRAC = 0.4, 0.6
SHELL_HALF_Z = 0.01

# (4)'s per-leg cylinder.
LEG_HALF_Z = 0.05


def _print(text, comm):
    if comm.rank == 0:
        print(text, flush=True)


def _owned_cell_geometry(mesh):
    """Midpoints and signed-volume magnitudes of the *owned* cells only."""
    tdim = mesh.topology.dim
    n_owned = int(mesh.topology.index_map(tdim).size_local)
    x = mesh.geometry.x
    dofmap = np.asarray(mesh.geometry.dofmap)
    if dofmap.ndim == 1:
        dofmap = dofmap.reshape(-1, 4)
    nodes = dofmap[:n_owned, :4]
    verts = x[nodes]  # (n_owned, 4, 3)
    mid = verts.mean(axis=1)
    e = verts[:, 1:, :] - verts[:, 0:1, :]
    vol = np.abs(np.linalg.det(e)) / 6.0
    return n_owned, mid, vol


def _quadrant_masks(mid, n_quadrants):
    """The squared-projection sector test — no `atan2`, no `sqrt`."""
    x, y = mid[:, 0], mid[:, 1]
    r2 = x * x + y * y
    masks = []
    for n in range(n_quadrants):
        phi = 2.0 * np.pi * n / n_quadrants
        ux, uy = float(np.cos(phi)), float(np.sin(phi))
        d = x * ux + y * uy
        masks.append((d > 0.0) & (d * d > 0.5 * r2))
    return masks


def _sum(comm, value):
    return comm.allreduce(value, op=MPI.SUM)


def _spread(values):
    v = np.asarray(values, dtype=float)
    mean = v.mean()
    if mean == 0.0:
        return float("nan")
    return float((v.max() - v.min()) / mean)


def _row(label, values, fmt="{:.6e}"):
    body = "  ".join(fmt.format(v) for v in values)
    return f"  {label:<34s} {body}   spread={_spread(values):.4e}"


def main():
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    _print(
        "\n[GEO-28] C4 census of the unloaded F-small birdcage mesh "
        "(measurement-only; asserts nothing)\n"
        f"[GEO-28] ranks={comm.size}  quadrants about leg azimuths "
        f"0/90/180/270 deg, +-45 deg, squared-projection test on cell midpoints",
        comm,
    )

    mesh, cells, _facets, diag, build_elapsed = _build(True)
    n_global = int(mesh.topology.index_map(mesh.topology.dim).size_global)
    _print(
        f"[GEO-28] CONTROL size_global={n_global} (record {CONTROL_CELL_RECORD}, "
        f"ratio {n_global / CONTROL_CELL_RECORD:.6f})  "
        f"mesh={float(diag['mesh_wall_time_s']):.2f} s  rung={build_elapsed:.2f} s",
        comm,
    )

    n_owned, mid, vol = _owned_cell_geometry(mesh)

    # Cell tags, restricted to owned cells (ghosts counted once).
    tag_of = np.zeros(n_owned, dtype=np.int32)
    idx = np.asarray(cells.indices)
    val = np.asarray(cells.values)
    keep = idx < n_owned
    tag_of[idx[keep]] = val[keep]

    masks = _quadrant_masks(mid, LEG_COUNT)
    unassigned = _sum(comm, int(np.count_nonzero(~np.any(masks, axis=0))))
    _print(
        f"[GEO-28] owned cells assigned to no quadrant (sector boundary / axis): "
        f"{unassigned}",
        comm,
    )

    labels = [f"Q{n + 1}" for n in range(LEG_COUNT)]

    # ---- (1) per-quadrant cell count and meshed volume of each core tag -----
    counts, volumes = {}, {}
    for tag in (CONDUCTOR_TAG, AIR_TAG, PHANTOM_TAG):
        is_tag = tag_of == tag
        counts[tag] = [
            _sum(comm, int(np.count_nonzero(is_tag & m))) for m in masks
        ]
        volumes[tag] = [
            _sum(comm, float(vol[is_tag & m].sum())) for m in masks
        ]

    # ---- (2) the CAD quarter of the coil, from the generator's parameters ---
    r_leg = 0.5 * LEG_WIDTH
    stub_length = 0.5 * (COIL_LENGTH - LEG_GAP_LENGTH)
    ring_cad_total = float(diag["ring_cad_mass_m3"])
    ring_analytic_total = 2.0 * (2.0 * np.pi**2 * RING_RADIUS * RING_MINOR_RADIUS**2)
    legs_per_quadrant_cad = 2.0 * np.pi * r_leg**2 * stub_length
    cad_quarter_sum = ring_cad_total / LEG_COUNT + legs_per_quadrant_cad
    conductor_cad_total = float(diag["cad_mass_by_group"]["conductor"])
    cad_quarter_exact = conductor_cad_total / LEG_COUNT
    dx, dy, dz = (float(s) for s in diag["port_box_size_m"])
    gap_box_volume = dx * dy * dz

    # ---- (3) cell-size statistic in the near-field shell -------------------
    r2 = mid[:, 0] ** 2 + mid[:, 1] ** 2
    shell = (
        (r2 >= (SHELL_LO_FRAC * RING_RADIUS) ** 2)
        & (r2 <= (SHELL_HI_FRAC * RING_RADIUS) ** 2)
        & (np.abs(mid[:, 2]) <= SHELL_HALF_Z)
    )
    local_ids = np.arange(n_owned, dtype=np.int32)
    h_all = np.asarray(
        _dcpp.mesh.h(mesh._cpp_object, mesh.topology.dim, local_ids)
    )
    shell_count, shell_mean, shell_max = [], [], []
    for m in masks:
        sel = shell & m
        c = _sum(comm, int(np.count_nonzero(sel)))
        s = _sum(comm, float(h_all[sel].sum()))
        hx = h_all[sel].max() if np.any(sel) else -np.inf
        shell_count.append(c)
        shell_mean.append(s / c if c else float("nan"))
        shell_max.append(float(comm.allreduce(float(hx), op=MPI.MAX)))

    # ---- (4) per leg, the conductor inside the leg's own cylinder ----------
    leg_cells, leg_volume = [], []
    for n in range(LEG_COUNT):
        phi = 2.0 * np.pi * n / LEG_COUNT
        cx, cy = RING_RADIUS * np.cos(phi), RING_RADIUS * np.sin(phi)
        d2 = (mid[:, 0] - cx) ** 2 + (mid[:, 1] - cy) ** 2
        sel = (
            (tag_of == CONDUCTOR_TAG)
            & (d2 <= r_leg**2)
            & (np.abs(mid[:, 2]) <= LEG_HALF_Z)
        )
        leg_cells.append(_sum(comm, int(np.count_nonzero(sel))))
        leg_volume.append(_sum(comm, float(vol[sel].sum())))
    stub_pair_cad = 2.0 * np.pi * r_leg**2 * (LEG_HALF_Z - 0.5 * LEG_GAP_LENGTH)

    elapsed = time.perf_counter() - started

    # ---- the table ---------------------------------------------------------
    if comm.rank == 0:
        print(
            f"\n[GEO-28] geometry from the generator's own parameters: "
            f"R={RING_RADIUS} m  r_leg={r_leg} m  r_ring={RING_MINOR_RADIUS} m  "
            f"leg_spacing={LEG_SPACING} m  coil_length={COIL_LENGTH} m  "
            f"g={LEG_GAP_LENGTH} m  stub={stub_length:.9e} m\n"
            f"[GEO-28] ring CAD mass (both rings)={ring_cad_total:.9e} m^3 "
            f"(analytic 2*2pi^2*R*r^2={ring_analytic_total:.9e}, ratio "
            f"{ring_cad_total / ring_analytic_total:.9f}); conductor CAD total="
            f"{conductor_cad_total:.9e} m^3; CAD quarter (C4-exact, /4)="
            f"{cad_quarter_exact:.9e} m^3; CAD quarter as ring/4 + 2 stubs "
            f"(no leg-ring overlap subtracted, an upper bound)="
            f"{cad_quarter_sum:.9e} m^3; gap box={gap_box_volume:.9e} m^3 "
            f"(dx,dy,dz={dx:.6e},{dy:.6e},{dz:.6e})\n"
            f"[GEO-28] shell {SHELL_LO_FRAC}R<=r<={SHELL_HI_FRAC}R "
            f"({SHELL_LO_FRAC * RING_RADIUS:.4f}-{SHELL_HI_FRAC * RING_RADIUS:.4f} m), "
            f"|z|<={SHELL_HALF_Z} m; leg cylinder r<={r_leg} m, |z|<={LEG_HALF_Z} m",
            flush=True,
        )
        print(
            "\n[GEO-28] per-quadrant table (columns "
            + " ".join(labels)
            + f"; quadrant Qn is the +-45 deg sector about leg n at "
            f"{', '.join(f'{90 * n} deg' for n in range(LEG_COUNT))})"
        )
        print("  (1) counts and meshed volumes by tag")
        print(_row("coil (tag 1) cells", counts[CONDUCTOR_TAG], "{:12d}"))
        print(_row("coil (tag 1) volume [m^3]", volumes[CONDUCTOR_TAG]))
        print(_row("phantom (tag 3) cells", counts[PHANTOM_TAG], "{:12d}"))
        print(_row("phantom (tag 3) volume [m^3]", volumes[PHANTOM_TAG]))
        print(_row("air (tag 2) cells", counts[AIR_TAG], "{:12d}"))
        print(_row("air (tag 2) volume [m^3]", volumes[AIR_TAG]))
        print("  (2) coil quadrant volume against the CAD quarter")
        print(
            _row(
                "meshed/CAD quarter (C4-exact)",
                [v / cad_quarter_exact for v in volumes[CONDUCTOR_TAG]],
                "{:12.9f}",
            )
        )
        print(
            _row(
                "meshed/(ring/4 + 2 stubs)",
                [v / cad_quarter_sum for v in volumes[CONDUCTOR_TAG]],
                "{:12.9f}",
            )
        )
        print("  (3) near-field shell cell size (dolfinx.cpp.mesh.h)")
        print(_row("shell cells", shell_count, "{:12d}"))
        print(_row("shell mean h [m]", shell_mean))
        print(_row("shell max h [m]", shell_max))
        print("  (4) per leg, conductor inside the leg's own cylinder")
        print(_row("leg cells", leg_cells, "{:12d}"))
        print(_row("leg volume [m^3]", leg_volume))
        print(
            _row(
                "leg volume / 2-stub CAD",
                [v / stub_pair_cad for v in leg_volume],
                "{:12.9f}",
            )
        )
        print(
            f"  (2-stub CAD inside |z|<={LEG_HALF_Z}: {stub_pair_cad:.9e} m^3)"
        )
        print("  (5) spreads (max-min)/mean, collected")
        for name, vals in (
            ("coil cells", counts[CONDUCTOR_TAG]),
            ("coil volume", volumes[CONDUCTOR_TAG]),
            ("phantom cells", counts[PHANTOM_TAG]),
            ("phantom volume", volumes[PHANTOM_TAG]),
            ("air cells", counts[AIR_TAG]),
            ("air volume", volumes[AIR_TAG]),
            ("shell cells", shell_count),
            ("shell mean h", shell_mean),
            ("shell max h", shell_max),
            ("leg cells", leg_cells),
            ("leg volume", leg_volume),
        ):
            print(f"    spread {name:<18s} = {_spread(vals):.6e}")
        print(
            f"\n[GEO-28] totals: owned+ghost-free cells summed="
            f"{sum(counts[CONDUCTOR_TAG]) + sum(counts[AIR_TAG]) + sum(counts[PHANTOM_TAG]) + unassigned}"
            f" vs size_global={n_global} (the difference is the port-box tags "
            f"100+i / 200+i, which are not in the three core tags)\n"
            f"[GEO-28] probe wall time={elapsed:.2f} s",
            flush=True,
        )


if __name__ == "__main__":
    main()
