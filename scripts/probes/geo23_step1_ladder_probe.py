"""`GEO-23` step 1 (c) resolution ladder over the "overlapping facets" geometries.

Step 1 (a)/(b) measured all four census sites red at BOTH rank widths, so every
one of them qualifies for the ladder clause.  The four sites collapse to three
generators, and only two are this probe's business:

* ``cylindrical_domain`` at the ``test_boundary_condition_selection.py`` sizing
  (inner 0.01 / outer 0.08 / length 0.12, h = 0.04);
* ``coil_phantom_domain`` at the sizing BOTH phantom sites call with
  byte-identical kwargs (h = 0.03);

``birdcage_port_domain`` is excluded on purpose — `GEO-21` step 2 already
laddered it (known-issues 2026-08-25/26: everything coarser than ~4.8 mm
aborts), and this chunk must not re-record that.

Five geometric rungs per generator, ratio 0.8, starting AT the failing value and
walking towards fine.  Every rung is caught and printed as ``FAIL`` with the
gmsh string, so a geometry that fails at every rung is a printed ladder rather
than a traceback.  Prints only, asserts nothing, adopts nothing.

Run at ``-n 1`` — a rank-0 gmsh throw deadlocks the collective at wider ranks,
which is exactly what step 1 (a)/(b) measured.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from mpi4py import MPI

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402

RATIO = 0.8
N_RUNGS = 5

# Kwargs copied verbatim from the failing call sites.
CYLINDRICAL = dict(inner_radius=0.01, outer_radius=0.08, length=0.12)
CYLINDRICAL_H0 = 0.04  # tests/solver/test_boundary_condition_selection.py:26

COIL_PHANTOM = dict(
    coil_major_radius=0.07,
    coil_minor_radius=0.010,
    coil_separation=0.08,
    phantom_radius=0.03,
    phantom_height=0.08,
    air_padding=0.04,
)
COIL_PHANTOM_H0 = 0.03  # tests/post/test_phantom_field_metrics.py:35 and
#                         tests/materials/test_phantom_material_model.py:110


def _rungs(h0: float) -> list[float]:
    return [h0 * RATIO**k for k in range(N_RUNGS)]


def _ladder_rung(label: str, builder, kwargs: dict, h: float, comm) -> None:
    started = time.perf_counter()
    try:
        mesh, _, _ = builder(comm=comm, resolution=h, **kwargs)
        elapsed = time.perf_counter() - started
        n_cells = mesh.topology.index_map(3).size_global
        verdict = f"MESHES cells={n_cells:>8d}"
    except Exception as exc:  # noqa: BLE001 - the measurement IS the exception
        elapsed = time.perf_counter() - started
        verdict = f"FAIL   {type(exc).__name__}: {exc}"
    if comm.rank == 0:
        print(f"[probe] {label} h={h:<10.6f} {verdict}  ({elapsed:.1f} s)", flush=True)


def _ladder(label: str, builder, kwargs: dict, h0: float, comm) -> None:
    if comm.rank == 0:
        print(f"\n[probe] === {label} === five rungs from h0={h0} at ratio {RATIO}", flush=True)
    for h in _rungs(h0):
        _ladder_rung(label, builder, kwargs, h, comm)


def main() -> None:
    comm = MPI.COMM_WORLD
    which = sys.argv[1] if len(sys.argv) > 1 else "both"

    # One rung per PROCESS is mandatory, not stylistic: the first run of this
    # probe (20260828T140947Z) walked all five cylindrical rungs in one process
    # and every rung after the first returned
    # ``IndexError: index 0 is out of bounds for axis 0 with size 0`` in 0.0 s.
    # A rung that meshes in a fresh process reads as that IndexError once a
    # prior rung has thrown inside gmsh, so an in-process ladder measures gmsh
    # state, not the geometry.  Caller passes an explicit h to get one rung.
    if len(sys.argv) > 2:
        h = float(sys.argv[2])
        spec = {
            "cylindrical": ("cylindrical_domain", MeshGenerator.cylindrical_domain, CYLINDRICAL),
            "coil_phantom": ("coil_phantom_domain", MeshGenerator.coil_phantom_domain, COIL_PHANTOM),
        }[which]
        _ladder_rung(spec[0], spec[1], spec[2], h, comm)
        return

    if which in ("both", "cylindrical"):
        _ladder(
            "cylindrical_domain", MeshGenerator.cylindrical_domain,
            CYLINDRICAL, CYLINDRICAL_H0, comm,
        )
    if which in ("both", "coil_phantom"):
        _ladder(
            "coil_phantom_domain", MeshGenerator.coil_phantom_domain,
            COIL_PHANTOM, COIL_PHANTOM_H0, comm,
        )


if __name__ == "__main__":
    main()
