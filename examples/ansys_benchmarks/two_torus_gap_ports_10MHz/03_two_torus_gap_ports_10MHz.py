"""ANS-3 — two coaxial gapped loops at 10 MHz: the runnable half.

`ANS-3` (PROJECT_PLAN §7), the second commissioned Ansys Electronics Desktop
benchmark (§5.4).  `SPEC.md` beside this file is the authority for the
boundary-value problem the human operator replicates in AED; this script
produces *our* half of it and writes:

* ``metrics.json`` — the full complex ``Z`` and ``S`` at the two gap ports,
  the systematics ladder, the reciprocity/passivity identities, mesh and
  timing metadata
* ``COMPARISON.md`` — the SPEC's export table with our columns filled and the
  AED columns blank, ready for the operator
* ``paraview_output/ans3_two_torus_gap_ports_combined.xdmf`` — mesh, CellTags
  and the port-1 drive's ``E`` phasor

**Nothing here is transcribed.**  The fixture, the drive, the port specs and
the two systematic corrections are imported from the `EX-20` example module
(``examples/ports/02_package_sparameter_sweep.py``) and from
``fem_em_solver.ports``, exactly as `ANS-1` imports the `MAT-6`/`EX-11` path.
The benchmark therefore cannot drift away from the gate it is built on: if the
gated path moves, this case moves with it and its reproduction assertions fire.

**Anchor** (§7 `ANS-3`).  Every asserted number reproduces the `PORT-1` step-4
record inside `EX-20`'s pre-stated **1%** band: raw mutual ``0.894543``,
corrected ``0.939849``, ``||S - S^T||/||S|| = 2.5494e-05``,
``||S||_2 = 0.861449``.

**Negative control.**  The raw rung is printed **first** and asserted to
*fail* the unmoved 10% mutual band (the `EX-20` inverted assertion): at
-10.55% it does not pass on its own, so the two named systematics are visibly
doing work rather than decorating a number that was already inside.

**Out of scope** (SPEC "Out of scope", §7 `ANS-3`).  Runnable half only: no
adjudication, no frequency sweep, no coil or birdcage claim, no B1+/SAR.  Our
``Z11`` carries the unprojected electric-energy caveat (`PORT-1` standing
cautions) and is exported as a secondary row, not a claim.

Run it through the example runner (the ``ans:`` group sources the complex
build automatically)::

    ./run_examples.sh -e ans:3 -n 2 -t 500
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type

# The runner puts only ``src`` on PYTHONPATH; the repo root goes on sys.path so
# the `EX-20` example module (the gated path this case regenerates) is importable.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fem_em_solver.core import (  # noqa: E402
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.mesh import MeshGenerator  # noqa: E402
from fem_em_solver.io.paraview_utils import (  # noqa: E402
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.ports.definitions import PortDefinition  # noqa: E402
from fem_em_solver.ports.gap_voltage import GapVoltagePortSpec  # noqa: E402
from fem_em_solver.ports.sparameters import (  # noqa: E402
    run_n_port_sparameter_sweep,
)
from fem_em_solver.ports.systematics import (  # noqa: E402
    GAP_PHYSICS_SYSTEMATIC,
    PEC_BOX_SYSTEMATIC,
    mutual_systematics_ladder,
)

# `EX-20` is the gated example path (`PORT-1` step 4 through the package entry
# point). Every constant and helper below comes from it — the ANS-1 rule.
_EX20 = _REPO_ROOT / "examples" / "ports" / "02_package_sparameter_sweep.py"
sys.path.insert(0, str(_EX20.parent))
_ex20 = __import__("02_package_sparameter_sweep")  # noqa: E402  (leading digit)

FREQUENCY_HZ = _ex20.FREQUENCY_HZ
OMEGA = _ex20.OMEGA
MAJOR_RADIUS = _ex20.MAJOR_RADIUS
MINOR_RADIUS = _ex20.MINOR_RADIUS
SEPARATION = _ex20.SEPARATION
AIR_PADDING = _ex20.AIR_PADDING
H_FAR = _ex20.H_FAR
H_WIRE = _ex20.H_WIRE
GAP_ANGLE = _ex20.GAP_ANGLE
GAP_BURIAL = _ex20.GAP_BURIAL
GAP_OVERHANG = _ex20.GAP_OVERHANG
GAP_ARC_RESOLUTION = _ex20.GAP_ARC_RESOLUTION
WIRE_TAGS = _ex20.WIRE_TAGS
GAP_TAGS = _ex20.GAP_TAGS
SIGMA_WIRE_S_PER_M = _ex20.SIGMA_WIRE_S_PER_M
DRIVE_CURRENT_A = _ex20.DRIVE_CURRENT_A
REFERENCE_IMPEDANCE_OHM = _ex20.REFERENCE_IMPEDANCE_OHM
PATH_QUADRATURE_ORDER = _ex20.PATH_QUADRATURE_ORDER

RECORDED_RAW_RATIO = _ex20.RECORDED_RAW_RATIO
RECORDED_CORRECTED_RATIO = _ex20.RECORDED_CORRECTED_RATIO
RECORDED_S_SYMMETRY_RESIDUAL = _ex20.RECORDED_S_SYMMETRY_RESIDUAL
RECORDED_S_SPECTRAL_NORM = _ex20.RECORDED_S_SPECTRAL_NORM
REPRODUCTION_BAND_RELATIVE = _ex20.REPRODUCTION_BAND_RELATIVE
MUTUAL_TOLERANCE = _ex20.MUTUAL_TOLERANCE
S_SPECTRAL_NORM_CEILING = _ex20.S_SPECTRAL_NORM_CEILING

_mutual_inductance = _ex20._mutual_inductance
_gap_half_extents = _ex20._gap_half_extents
_azimuthal_unit = _ex20._azimuthal_unit
_arc_quadrature = _ex20._arc_quadrature
_tag_volume = _ex20._tag_volume
_gap_drive = _ex20._gap_drive
_paraview_fields = _ex20._paraview_fields
_relative_miss = _ex20._relative_miss

#: `PORT-1`'s own reciprocity gate on the field-derived S, unmoved: the
#: Frobenius asymmetry of a reciprocal 2-port is zero, and 2.5494e-05 is what
#: the fixture achieves. This is the SPEC's primary identity row.
S_SYMMETRY_RTOL = 1.0e-3

CASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = CASE_DIR / "paraview_output"
BASENAME = "ans3_two_torus_gap_ports_combined"


def _complex_entry(z: complex) -> dict:
    return {"re": float(np.real(z)), "im": float(np.imag(z))}


def _matrix_payload(m) -> list:
    return [[_complex_entry(m[i, j]) for j in range(m.shape[1])] for i in range(m.shape[0])]


def _write_metrics(payload) -> Path:
    path = CASE_DIR / "metrics.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def _fmt(z: complex) -> str:
    return f"{np.real(z):+.7e} {np.imag(z):+.7e}j"


def _write_comparison(m, z, s) -> Path:
    """``COMPARISON.md``: our columns filled, the two AED columns blank per SPEC.

    Every number comes from ``m``/``z``/``s``, which came from this run; the
    closed-form ``ωM₁₂`` is evaluated from ``AnalyticalSolutions`` seconds ago,
    not transcribed from a log.
    """
    lad = m["systematics_ladder"]
    path = CASE_DIR / "COMPARISON.md"
    path.write_text(
        f"""# ANS-3 — comparison table (our half filled, both AED halves blank)

Generated by `03_two_torus_gap_ports_10MHz.py` on {m["generated_utc"]}; every
number in the "Ours (FEM)" column is produced by that run through
`run_n_port_sparameter_sweep` — the `EX-20` path — and the filamentary closed
form is evaluated at run time from `utils/analytical.py`. Nothing is
transcribed. Re-run `./run_examples.sh -e ans:3 -n 2 -t 500` to regenerate.

`SPEC.md` is the authority for the problem to be replicated. Fill the AED
columns from the HFSS driven solve of that spec, reporting **all** digits AED
prints.

**Two AED columns, per the `ANS-5` ruling (2026-08-30).** Our side is
`Nedelec first kind, degree 1 (N1curl)`, 6 unknowns per tetrahedron =
**HFSS Zero Order (20 unknowns/tet = First Order, the AED default, is the
order-sensitivity column)**. Column **AED (Zero Order)** is the matched
discretization and is the *adjudication* column; column **AED (First Order)** is
the AED default and is an order-sensitivity reading only. Mixed Order is
forbidden — we have no per-element order and could not reproduce it.

## Z-matrix at the two lumped ports [Ω]

| Entry | Ours (FEM) | AED (Zero Order) | AED (First Order) | AED vs ours |
|---|---|---|---|---|
| Z₁₁ | {_fmt(z[0, 0])} | | | |
| Z₁₂ | {_fmt(z[0, 1])} | | | |
| Z₂₁ | {_fmt(z[1, 0])} | | | |
| Z₂₂ | {_fmt(z[1, 1])} | | | |

**Im Z₂₁ is the primary adjudication row.** Ours is
{np.imag(z[1, 0]):+.7e} Ω against the filamentary closed form
ωM₁₂ = {m["omega_m12_ohm"]:.6f} Ω — a ratio of {lad["raw"]:.6f} raw and
{lad["corrected"]:.6f} after the two named systematics
(§2.1: PEC-box {PEC_BOX_SYSTEMATIC:+.6f} on the ratio, gap-physics
{GAP_PHYSICS_SYSTEMATIC:+.6f} relative). The closed form spans 66.5% of
nominal over ±r_wire, so it is an anchor, not a gate; the gate is the
{100.0 * MUTUAL_TOLERANCE:.0f}% mutual band, which the corrected ratio passes
({100.0 * lad["deviation"]:+.2f}%) and the raw ratio does **not**
({100.0 * lad["raw_deviation"]:+.2f}%).

**Z₁₁/Z₂₂ are secondary rows, never gated.** Our diagonal carries the
unprojected electric-energy caveat (`PORT-1` standing cautions, PROJECT_PLAN
§7): an AED disagreement here is expected to be informative about *our* feed
model rather than alarming.

## S-matrix renormalized to Z₀ = {REFERENCE_IMPEDANCE_OHM:.0f} Ω

| Entry | Ours (FEM) | AED (Zero Order) | AED (First Order) | AED vs ours |
|---|---|---|---|---|
| S₁₁ | {_fmt(s[0, 0])} | | | |
| S₁₂ | {_fmt(s[0, 1])} | | | |
| S₂₁ | {_fmt(s[1, 0])} | | | |
| S₂₂ | {_fmt(s[1, 1])} | | | |

## Identities

| Quantity | Exact | Ours (FEM) | Gate | AED (Zero Order) | AED (First Order) |
|---|---|---|---|---|---|
| ‖S − Sᵀ‖/‖S‖ (reciprocity) | 0 | {m["s_symmetry_residual"]:.4e} | < {S_SYMMETRY_RTOL:.0e} | | |
| \\|Z₁₂ − Z₂₁\\|/\\|Z₂₁\\| | 0 | {m["z_reciprocity_residual"]:.4e} | reported | | |
| ‖S‖₂ (passivity) | ≤ 1 | {m["s_spectral_norm"]:.6f} | ≤ {S_SPECTRAL_NORM_CEILING:.1f} | | |

## Negative control (in-fixture, ours)

The **raw** mutual ratio {lad["raw"]:.6f} is printed first by the script and
asserted to *fail* the unmoved {100.0 * MUTUAL_TOLERANCE:.0f}% band
({100.0 * lad["raw_deviation"]:+.2f}%). An assertion that the uncorrected
number is a miss is what keeps the two systematic corrections honest: if the
fixture ever landed inside the band on its own, this case would fail loudly
rather than quietly reporting a corrected number nobody needed.

## Reproduction of the gated record

Each entry below is this run against the `PORT-1` step-4 record
(`docs/testing/logs/20260813T183606Z_PORT-1-step4-packagegate.log`), inside
`EX-20`'s pre-stated {100.0 * REPRODUCTION_BAND_RELATIVE:.0f}% band:

| Quantity | Record | This run | Relative miss |
|---|---|---|---|
| raw mutual ratio | {RECORDED_RAW_RATIO:.6f} | {lad["raw"]:.6f} | {m["reproduction_miss"]["raw"]:.2e} |
| corrected mutual ratio | {RECORDED_CORRECTED_RATIO:.6f} | {lad["corrected"]:.6f} | {m["reproduction_miss"]["corrected"]:.2e} |
| ‖S − Sᵀ‖/‖S‖ | {RECORDED_S_SYMMETRY_RESIDUAL:.4e} | {m["s_symmetry_residual"]:.4e} | {m["reproduction_miss"]["symmetry"]:.2e} |
| ‖S‖₂ | {RECORDED_S_SPECTRAL_NORM:.6f} | {m["s_spectral_norm"]:.6f} | {m["reproduction_miss"]["spectral"]:.2e} |

## Solve metadata

| Item | Ours (FEM) | AED (Zero Order) | AED (First Order) |
|---|---|---|---|
| Elements | {m["n_cells"]} tetrahedra, lowest-order Nédélec edge elements (`N1curl`, degree 1) | | |
| Basis order | Nedelec first kind, degree 1 (N1curl), 6 unknowns/tet | | |
| Adaptive passes | n/a — fixed graded mesh | | |
| Final ΔS | n/a — single non-adaptive solve per port | | |
| Solve time | {m["sweep_seconds"]:.1f} s for the 2-column sweep at `mpiexec -n {m["mpi_ranks"]}` (+ {m["export_solve_seconds"]:.1f} s for the export solve) | | |
| Drive current per port | {DRIVE_CURRENT_A:.1f} A impressed across the gap box along +ŷ | | |
| Skin depth δ in the wire | {m["skin_depth_m"] * 1e3:.2f} mm = {m["skin_depth_over_r_wire"]:.2f} r_wire | | |

Mesh sizing (from the gated fixture): wire {H_WIRE} m, far field {H_FAR} m,
gap-arc {GAP_ARC_RESOLUTION:.1e} m; air padding {AIR_PADDING} m, which is what
fixes the SPEC's box to x, y ∈ [−0.125, +0.125], z ∈ [−0.105, +0.105].

## Field export

`paraview_output/{BASENAME}.xdmf` (regenerated by each run; not tracked, like
every other `paraview_output/` in the repo). Threshold on `CellTags`
(1/2 = the two conductors, 101/102 = the gap boxes) and colour by
`E_magnitude` [V/m].

**A named limitation** (`EX-20`'s): `run_n_port_sparameter_sweep` returns port
quantities, not fields — `TimeHarmonicFields` are discarded inside it — so the
export above costs **one extra solve** of port 1's drive, run through
`TimeHarmonicSolver` exactly as the sweep runs it. The script says so rather
than pretending the sweep produced the file.

For the AED half, export |E| on the same gap-plane cut so the spatial
distributions can be compared, not just the terminal numbers.

## Provenance

* Gated path: `examples/ports/02_package_sparameter_sweep.py` (`EX-20`) —
  every geometry, drive, quadrature and systematics constant above is imported
  from it, never restated.
* Package entry point: `fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep`.
* Systematic corrections: `fem_em_solver.ports.systematics`
  (`PEC_BOX_SYSTEMATIC` = {PEC_BOX_SYSTEMATIC:+.6f},
  `GAP_PHYSICS_SYSTEMATIC` = {GAP_PHYSICS_SYSTEMATIC:+.6f}).
* Closed form: `AnalyticalSolutions.circular_loop_vector_potential`, filamentary
  M₁₂ for coaxial loops at a = {MAJOR_RADIUS} m, d = {SEPARATION} m.
* Gate of record: `PORT-1` step 4 (PROJECT_PLAN §7), reproduced by `EX-20`.
"""
    )
    return path


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "This example needs the complex DolfinX build: "
            "source /usr/local/bin/dolfinx-complex-mode (the runner does this "
            "automatically for the `ans:` group)."
        )

    if comm.rank == 0:
        print("=" * 78, flush=True)
        print("ANS-3 — two coaxial gapped loops at 10 MHz (runnable half)", flush=True)
        print("=" * 78, flush=True)

    # -- the gated fixture, restated from EX-20's constants ----------------
    t_mesh = time.perf_counter()
    msh, cell_tags, _facet_tags = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=H_FAR,
        air_padding=AIR_PADDING,
        wire_resolution=H_WIRE,
        far_resolution=H_FAR,
        port_gap=True,
        gap_angle=GAP_ANGLE,
        gap_burial=GAP_BURIAL,
        gap_overhang=GAP_OVERHANG,
        gap_arc_resolution=GAP_ARC_RESOLUTION,
        comm=comm,
    )
    t_mesh = time.perf_counter() - t_mesh

    tdim = msh.topology.dim
    n_cells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)
    # Unconditionally on every rank before any tagged form (PORT-1 step 3b-iv,
    # known-issues 9).
    msh.topology.create_connectivity(tdim - 1, tdim)
    msh.topology.create_entity_permutations()

    if comm.rank == 0:
        print(
            f"[ANS-3] mesh: {n_cells} cells in {t_mesh:.1f} s "
            f"(padding {AIR_PADDING} -> SPEC box x,y in [-0.125, 0.125], "
            f"z in [-0.105, 0.105])",
            flush=True,
        )

    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map={
            tag: HomogeneousMaterial(sigma=SIGMA_WIRE_S_PER_M, epsilon_r=1.0, mu_r=1.0)
            for tag in WIRE_TAGS
        },
        boundary_condition="pec_zero_tangential_a",
    )

    _, half_y = _gap_half_extents()
    ports = [
        PortDefinition(
            port_id=f"P{k + 1}",
            positive_tag=GAP_TAGS[k],
            negative_tag=WIRE_TAGS[k],
            orientation="gap_azimuthal_plus_y",
            z0_ohm=REFERENCE_IMPEDANCE_OHM,
        )
        for k in range(2)
    ]
    specs = []
    for k in range(2):
        points, tangents, weights = _arc_quadrature(k, PATH_QUADRATURE_ORDER)
        specs.append(
            GapVoltagePortSpec(
                port_id=f"P{k + 1}",
                gap_cell_tag=GAP_TAGS[k],
                gap_length_m=2.0 * half_y,
                conductor_cell_tag=WIRE_TAGS[k],
                conductor_sigma_s_per_m=SIGMA_WIRE_S_PER_M,
                conductor_direction=_azimuthal_unit,
                conductor_cross_section_m2=float(np.pi * MINOR_RADIUS**2),
                path_points=points,
                path_tangents=tangents,
                path_weights=weights,
                drive_direction=(0.0, 1.0, 0.0),
                drive_current_a=DRIVE_CURRENT_A,
            )
        )

    # -- one call: two solves, Z column by column, S at Z0 -----------------
    t_sweep = time.perf_counter()
    solved = run_n_port_sparameter_sweep(problem, ports, gap_voltage_ports=specs)
    t_sweep = time.perf_counter() - t_sweep

    assert not solved.is_placeholder, (
        "the solved-field route returned is_placeholder=True — this benchmark "
        "must export field-derived S-parameters, not the heuristic"
    )
    assert solved.z_matrix is not None, "the solved-field route must return its Z"

    z = np.asarray(solved.z_matrix)
    s = np.asarray(solved.s_matrix)

    omega_m12 = OMEGA * _mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    im_z12 = float(z[1, 0].imag)
    ladder = mutual_systematics_ladder(im_z12, omega_m12)

    s_symmetry = float(np.linalg.norm(s - s.T) / np.linalg.norm(s))
    s_spectral = float(np.linalg.norm(s, 2))
    z_reciprocity = float(abs(z[0, 1] - z[1, 0]) / abs(z[1, 0]))

    misses = {
        "raw": _relative_miss(ladder["raw"], RECORDED_RAW_RATIO),
        "corrected": _relative_miss(ladder["corrected"], RECORDED_CORRECTED_RATIO),
        "symmetry": _relative_miss(s_symmetry, RECORDED_S_SYMMETRY_RESIDUAL),
        "spectral": _relative_miss(s_spectral, RECORDED_S_SPECTRAL_NORM),
    }

    skin_depth = float(
        np.sqrt(2.0 / (OMEGA * 4.0e-7 * np.pi * SIGMA_WIRE_S_PER_M))
    )

    if comm.rank == 0:
        print(
            "[ANS-3] NEGATIVE CONTROL FIRST — the raw (uncorrected) mutual "
            f"ratio {ladder['raw']:.6f} is a MISS at "
            f"{100.0 * ladder['raw_deviation']:+.2f}% against the unmoved "
            f"{100.0 * MUTUAL_TOLERANCE:.0f}% band",
            flush=True,
        )
        print(
            f"[ANS-3] Im Z21 = {im_z12:+.9e} Ohm, omega*M12 = {omega_m12:.6f} Ohm "
            "(filamentary closed form, spans 66.5% of nominal over +-r_wire)",
            flush=True,
        )
        print(
            "[ANS-3] systematics ladder:\n"
            f"    raw            {ladder['raw']:.6f}  "
            f"({100.0 * ladder['raw_deviation']:+.2f}%, a MISS)\n"
            f"    + PEC box      {ladder['box_corrected']:.6f}\n"
            f"    + gap physics  {ladder['corrected']:.6f}  "
            f"({100.0 * ladder['deviation']:+.2f}%, inside the band)",
            flush=True,
        )
        print(f"[ANS-3] Z (Ohm):\n{z}", flush=True)
        print(f"[ANS-3] S at Z0 = {REFERENCE_IMPEDANCE_OHM:.0f} Ohm:\n{s}", flush=True)
        print(
            f"[ANS-3] identities: |Z12 - Z21|/|Z21| = {z_reciprocity:.4e}, "
            f"||S - S^T||/||S|| = {s_symmetry:.4e} (gate {S_SYMMETRY_RTOL:.0e}), "
            f"||S||_2 = {s_spectral:.6f} <= {S_SPECTRAL_NORM_CEILING:.1f}",
            flush=True,
        )
        print(
            "[ANS-3] reproduction of the PORT-1 step-4 record "
            f"(band {100.0 * REPRODUCTION_BAND_RELATIVE:.0f}% relative): "
            f"raw {misses['raw']:.2e}, corrected {misses['corrected']:.2e}, "
            f"symmetry {misses['symmetry']:.2e}, ||S||_2 {misses['spectral']:.2e}",
            flush=True,
        )

    # -- gates -------------------------------------------------------------
    for name, recorded in (
        ("raw", RECORDED_RAW_RATIO),
        ("corrected", RECORDED_CORRECTED_RATIO),
        ("symmetry", RECORDED_S_SYMMETRY_RESIDUAL),
        ("spectral", RECORDED_S_SPECTRAL_NORM),
    ):
        assert misses[name] < REPRODUCTION_BAND_RELATIVE, (
            f"{name} does not reproduce the PORT-1 step-4 record {recorded:.6g} "
            f"within {100.0 * REPRODUCTION_BAND_RELATIVE:.0f}%: relative miss "
            f"{misses[name]:.3e} — this benchmark is not exporting the gated path"
        )

    assert abs(ladder["raw_deviation"]) >= MUTUAL_TOLERANCE, (
        f"the raw mutual {ladder['raw']:.6f} passed the "
        f"{100.0 * MUTUAL_TOLERANCE:.0f}% band on its own — the systematics "
        "this benchmark exists to adjudicate would be doing nothing"
    )
    assert abs(ladder["deviation"]) < MUTUAL_TOLERANCE, (
        f"corrected mutual {ladder['corrected']:.6f} is "
        f"{100.0 * ladder['deviation']:+.2f}% against the closed form, outside "
        f"the unmoved {100.0 * MUTUAL_TOLERANCE:.0f}% band"
    )
    assert s_symmetry < S_SYMMETRY_RTOL, (
        f"reciprocity residual ||S - S^T||/||S|| = {s_symmetry:.4e} exceeds the "
        f"unmoved PORT-1 gate {S_SYMMETRY_RTOL:.0e}"
    )
    assert s_spectral <= S_SPECTRAL_NORM_CEILING, (
        f"S is not passive: ||S||_2 = {s_spectral:.6f} > "
        f"{S_SPECTRAL_NORM_CEILING:.1f}"
    )

    # -- ParaView: one extra solve, because the sweep returns no fields ----
    gap_volume = _tag_volume(msh, cell_tags, GAP_TAGS[0], comm)
    gap_area = gap_volume / (2.0 * half_y)
    t_export_solve = time.perf_counter()
    fields = TimeHarmonicSolver(problem, degree=1).solve(
        current_density=_gap_drive(DRIVE_CURRENT_A / gap_area),
        subdomain_ids=[int(GAP_TAGS[0])],
        project_source=False,
    )
    t_export_solve = time.perf_counter() - t_export_solve

    OUTPUT_DIR.mkdir(exist_ok=True)
    e_re, e_im, e_mag = _paraview_fields(msh, fields)
    written = write_xdmf_with_tags(
        OUTPUT_DIR / BASENAME,
        msh,
        cell_tags,
        {"E_real": e_re, "E_imag": e_im, "E_magnitude": e_mag},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    elapsed = time.perf_counter() - started

    if comm.rank == 0:
        metrics = {
            "case": "two_torus_gap_ports_10MHz",
            "chunk": "ANS-3",
            "spec": "SPEC.md (authority for geometry/materials/BCs/ports)",
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "regime": "eddy-current at 10 MHz; NOT a Larmor frequency (§2.1)",
            "gated_path": "run_n_port_sparameter_sweep via examples/ports/02_package_sparameter_sweep.py (EX-20)",
            "frequency_hz": FREQUENCY_HZ,
            "major_radius_m": MAJOR_RADIUS,
            "minor_radius_m": MINOR_RADIUS,
            "separation_m": SEPARATION,
            "air_padding_m": AIR_PADDING,
            "sigma_wire_S_per_m": SIGMA_WIRE_S_PER_M,
            "drive_current_A": DRIVE_CURRENT_A,
            "reference_impedance_ohm": REFERENCE_IMPEDANCE_OHM,
            "skin_depth_m": skin_depth,
            "skin_depth_over_r_wire": skin_depth / MINOR_RADIUS,
            "mesh": {
                "resolution_wire": H_WIRE,
                "resolution_far": H_FAR,
                "gap_arc_resolution": GAP_ARC_RESOLUTION,
                "gap_angle_rad": GAP_ANGLE,
                "gap_burial_m": GAP_BURIAL,
                "gap_overhang_m": GAP_OVERHANG,
                "path_quadrature_order": PATH_QUADRATURE_ORDER,
            },
            "n_cells": int(n_cells),
            "mpi_ranks": int(comm.size),
            "mesh_seconds": t_mesh,
            "sweep_seconds": t_sweep,
            "export_solve_seconds": t_export_solve,
            "total_seconds": elapsed,
            "z_matrix_ohm": _matrix_payload(z),
            "s_matrix": _matrix_payload(s),
            "omega_m12_ohm": omega_m12,
            "im_z21_ohm": im_z12,
            "systematics_ladder": {k: float(v) for k, v in ladder.items()},
            "systematics": {
                "pec_box": float(PEC_BOX_SYSTEMATIC),
                "gap_physics": float(GAP_PHYSICS_SYSTEMATIC),
            },
            "mutual_tolerance": MUTUAL_TOLERANCE,
            "s_symmetry_residual": s_symmetry,
            "s_symmetry_rtol": S_SYMMETRY_RTOL,
            "s_spectral_norm": s_spectral,
            "s_spectral_norm_ceiling": S_SPECTRAL_NORM_CEILING,
            "z_reciprocity_residual": z_reciprocity,
            "reproduction_record": {
                "source": "docs/testing/logs/20260813T183606Z_PORT-1-step4-packagegate.log",
                "raw": RECORDED_RAW_RATIO,
                "corrected": RECORDED_CORRECTED_RATIO,
                "symmetry": RECORDED_S_SYMMETRY_RESIDUAL,
                "spectral": RECORDED_S_SPECTRAL_NORM,
                "band_relative": REPRODUCTION_BAND_RELATIVE,
            },
            "reproduction_miss": {k: float(v) for k, v in misses.items()},
            "xdmf": f"paraview_output/{BASENAME}.xdmf",
            "aed": None,
        }
        metrics_path = _write_metrics(metrics)
        comparison_path = _write_comparison(metrics, z, s)
        if written is not None:
            print(f"[ANS-3] wrote {written[0]} (+ .h5)", flush=True)
        print(f"[ANS-3] wrote {metrics_path.name} and {comparison_path.name}", flush=True)
        print(
            f"[ANS-3] all gates green: raw {ladder['raw']:.6f} (a miss), "
            f"corrected {ladder['corrected']:.6f} "
            f"({100.0 * ladder['deviation']:+.2f}%, inside "
            f"{100.0 * MUTUAL_TOLERANCE:.0f}%); ||S - S^T||/||S|| = "
            f"{s_symmetry:.4e} < {S_SYMMETRY_RTOL:.0e}; ||S||_2 = "
            f"{s_spectral:.6f} <= 1",
            flush=True,
        )
        print(
            f"[ANS-3] elapsed {elapsed:.1f} s (mesh {t_mesh:.1f} s, package "
            f"sweep {t_sweep:.1f} s, export solve {t_export_solve:.1f} s) on "
            f"{comm.size} rank(s), {n_cells} cells",
            flush=True,
        )
        print(
            "[ANS-3] runnable half complete — the AED replication of SPEC.md is "
            "the operator's (PROJECT_PLAN §5.4 Waiting-on-you)",
            flush=True,
        )


if __name__ == "__main__":
    main()
