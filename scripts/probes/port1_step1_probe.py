"""`PORT-1` step 1 — two-loop reaction Z-matrix probe.

Not a test: this is the measurement that *sizes* the step-2 gate, exactly as
`scripts/probes/mat6_step2a_probe.py` sized the `MAT-6` gate.  Nothing here is
asserted; the product is numbers for the `PORT-1` §7 entry.

Two coaxial tori in air, separated by ``d`` on the z-axis.  Torus ``k`` is
driven in turn with the regularised azimuthal impressed current, and the
reaction integral

    Z_ik = −(1/(I_k·I_i)) ∫_{torus i} E_k · J_i dV                        (1)

gives one column of a 2×2 impedance matrix per solve.  ``J_i`` is torus i's
*shape* current (the same azimuthal pattern, restricted by the measure to
torus i's tag) and every ``I`` is the **meshed** loop current
``∫J_φ dV / (2πa)`` — the nominal-current shortfall was a 17% error that looked
like physics in `MAT-6` step 2a.

The quantities this probe exists to report:

  * the 2×2 Z and its reciprocity residual ``‖Z − Zᵀ‖/‖Z‖`` — the identity
    step 2 turns into the first failable S-parameter assertion in the repo;
  * ``Im Z₁₂`` against the closed form ``ωM₁₂``, ``M₁₂ = 2πa·A_φ(a,d)/I`` from
    ``AnalyticalSolutions.circular_loop_vector_potential`` (Jackson 5.37);
  * how much of any disagreement is *modelling*, not solving: the closed form
    is filamentary, so it is re-evaluated over ρ, z = a ± r_wire, d ± r_wire;
  * box sensitivity at two air paddings — the outer boundary is PEC here, and
    it images the loop currents back into the domain;
  * wall clock per solve at ``-n 2``, which sets step 2's tier.

Air everywhere (σ = 0, εᵣ = 1), so the domain is lossless: ``Re Z₁₂`` is
numerical noise and its size relative to ``Im Z₁₂`` is itself a measurement.

Run (complex build required)::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src mpiexec -n 2 python3 \\
       scripts/probes/port1_step1_probe.py --paddings 0.08 0.12'
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
    check_energy_continuity,
    stored_electric_energy,
)
from fem_em_solver.io.mesh import MeshGenerator
from fem_em_solver.utils.analytical import AnalyticalSolutions
from fem_em_solver.utils.constants import EPSILON_0, MU_0

# --- the configuration under test -------------------------------------------
# f is a free knob: nothing about a reaction Z-matrix ties it to the Larmor
# frequency, and the quasistatic reference ωM only holds while k₀·(box
# diagonal) ≪ 1.  10 MHz keeps that product near 0.01 for the boxes below.
FREQUENCY_HZ = 10.0e6
MAJOR_RADIUS = 0.04   # a
MINOR_RADIUS = 0.005  # r_wire
SEPARATION = 0.04     # d, centre to centre along z
CURRENT_A = 1.0

TORUS_TAGS = (1, 2)
DOMAIN_TAG = 3


def _azimuthal_current_density(j_magnitude: float):
    """Uniform azimuthal current about the z-axis.

    Regularised inside the sqrt rather than with ``ufl.max_value``: in complex
    mode UFL refuses conditionals on complex-valued operands, so the
    magnetostatic loop fixture's ``max_value`` form does not compile here.
    """

    def current_density(x):
        rho_safe = ufl.sqrt(x[0] ** 2 + x[1] ** 2 + 1e-24)
        return ufl.as_vector([
            -x[1] / rho_safe * j_magnitude,
            x[0] / rho_safe * j_magnitude,
            0.0,
        ])

    return current_density


def _tag_volume(msh, cell_tags, tag: int, comm) -> float:
    dx_tag = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))
    one = fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
    return float(
        np.real(comm.allreduce(fem.assemble_scalar(fem.form(one * dx_tag)), op=MPI.SUM))
    )


def _tag_field_energy(msh, cell_tags, e_field, tag: int, comm) -> float:
    """``∫_tag |E|² dV``, reduced — a diagnostic, not a physical energy."""
    dx_tag = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))
    local = fem.assemble_scalar(fem.form(ufl.inner(e_field, e_field) * dx_tag))
    return float(np.real(comm.allreduce(local, op=MPI.SUM)))


def _solve_driving(msh, cell_tags, driven_tag: int, comm, frequency_hz=None):
    """One time-harmonic solve with torus ``driven_tag`` carrying the source."""
    problem = TimeHarmonicProblem(
        mesh=msh,
        frequency_hz=FREQUENCY_HZ if frequency_hz is None else frequency_hz,
        material=HomogeneousMaterial(sigma=0.0, epsilon_r=1.0, mu_r=1.0),
        cell_tags=cell_tags,
        material_map=None,
        boundary_condition="pec_zero_tangential_a",
    )
    solver = TimeHarmonicSolver(problem, degree=1)
    j_magnitude = CURRENT_A / (np.pi * MINOR_RADIUS**2)
    comm.Barrier()
    t0 = time.perf_counter()
    fields = solver.solve(
        current_density=_azimuthal_current_density(j_magnitude),
        subdomain_ids=[driven_tag],
    )
    comm.Barrier()
    return fields, time.perf_counter() - t0


def _reaction(msh, cell_tags, e_field, tag: int, i_driven: float, i_test: float, comm):
    """Equation (1) for one (driven, test) pair, reduced across ranks."""
    j_magnitude = CURRENT_A / (np.pi * MINOR_RADIUS**2)
    x = ufl.SpatialCoordinate(msh)
    j_vec = _azimuthal_current_density(j_magnitude)(x)
    dx_tag = ufl.Measure("dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(tag,))
    # J is real, so inner()'s conjugation of its second argument is a no-op:
    # this is the reaction integral ∫E·J, not ∫E·J̄.
    local = fem.assemble_scalar(fem.form(ufl.inner(e_field, j_vec) * dx_tag))
    # assemble_scalar is rank-local.
    total = comm.allreduce(local, op=MPI.SUM)
    return complex(-total / (i_driven * i_test))


def mutual_inductance(a: float, rho: float, z: float) -> float:
    """``M = 2πρ·A_φ(ρ, z)/I`` for a unit-current filamentary loop of radius a."""
    pts = np.array([[rho, 0.0, z]], dtype=float)
    A = AnalyticalSolutions.circular_loop_vector_potential(pts, 1.0, a, loop_center=0.0)
    # At (x=ρ, y=0) the azimuthal direction is +y.
    a_phi = float(A[0, 1])
    return 2.0 * np.pi * rho * a_phi


def run_box(padding: float, args, comm) -> dict:
    log = comm.rank == 0
    t_mesh = time.perf_counter()
    msh, cell_tags, _ = MeshGenerator.two_torus_domain(
        separation=SEPARATION,
        major_radius=MAJOR_RADIUS,
        minor_radius=MINOR_RADIUS,
        resolution=args.h_far,
        air_padding=padding,
        wire_resolution=args.h_wire,
        far_resolution=args.h_far,
        comm=comm,
    )
    t_mesh = time.perf_counter() - t_mesh

    tdim = msh.topology.dim
    ncells = comm.allreduce(msh.topology.index_map(tdim).size_local, op=MPI.SUM)

    j_magnitude = CURRENT_A / (np.pi * MINOR_RADIUS**2)
    v_exact = 2.0 * np.pi**2 * MAJOR_RADIUS * MINOR_RADIUS**2
    volumes = [_tag_volume(msh, cell_tags, t, comm) for t in TORUS_TAGS]
    # ∫J_φ dV = I·2πa for an ideal torus, so the meshed volume fixes the current
    # the solver actually sees.
    currents = [j_magnitude * v / (2.0 * np.pi * MAJOR_RADIUS) for v in volumes]

    # Conformity check.  ``two_torus_domain`` builds the box with ``addBox`` and
    # never fragments it against the tori, so the torus interiors may be meshed
    # twice — once as tagged tori, once as part of the box — leaving three
    # mutually disconnected components.  If the total volume exceeds the box
    # volume by the two torus volumes, that is what happened.
    v_total = float(
        np.real(
            comm.allreduce(
                fem.assemble_scalar(
                    fem.form(
                        fem.Constant(msh, np.array(1.0, dtype=np.complex128).item())
                        * ufl.dx
                    )
                ),
                op=MPI.SUM,
            )
        )
    )
    v_domain_tag = _tag_volume(msh, cell_tags, DOMAIN_TAG, comm)
    half_x = MAJOR_RADIUS + MINOR_RADIUS + padding
    half_z = SEPARATION / 2 + MINOR_RADIUS + padding
    v_box = 8.0 * half_x * half_x * half_z

    if log:
        print(f"\n=== air padding = {padding:.4f} m ===", flush=True)
        print(f"  mesh: {ncells} cells, generated in {t_mesh:.1f} s", flush=True)
        print(
            f"  volumes: total {v_total:.6e}, tag-{DOMAIN_TAG} {v_domain_tag:.6e},"
            f" analytic box {v_box:.6e} m^3"
            f"  (total/box = {v_total / v_box:.6f})",
            flush=True,
        )
        for tag, v, i in zip(TORUS_TAGS, volumes, currents):
            print(
                f"  torus {tag}: meshed/exact volume {v:.6e} / {v_exact:.6e} m^3"
                f" ({v / v_exact - 1.0:+.2%}), meshed current {i:.6f} A",
                flush=True,
            )

    if args.mesh_only:
        return dict(
            padding=padding, ncells=int(ncells), z=np.zeros((2, 2), dtype=complex),
            times=[0.0], energies=[], currents=currents, volumes=volumes,
            t_mesh=t_mesh, mesh=msh, cell_tags=cell_tags,
        )

    z_matrix = np.zeros((2, 2), dtype=complex)
    times = []
    energies = []
    for col, driven_tag in enumerate(TORUS_TAGS):
        fields, dt = _solve_driving(msh, cell_tags, driven_tag, comm)
        times.append(dt)
        energies.append(stored_electric_energy(fields, comm))
        for row, test_tag in enumerate(TORUS_TAGS):
            z_matrix[row, col] = _reaction(
                msh,
                cell_tags,
                fields.e_complex,
                test_tag,
                currents[col],
                currents[row],
                comm,
            )
        per_tag = [
            _tag_field_energy(msh, cell_tags, fields.e_complex, t, comm)
            for t in (*TORUS_TAGS, DOMAIN_TAG)
        ]
        if log:
            print(
                f"  drive torus {driven_tag}: int|E|^2 over tags "
                f"{(*TORUS_TAGS, DOMAIN_TAG)} = "
                + ", ".join(f"{v:.4e}" for v in per_tag),
                flush=True,
            )
            print(
                f"  drive torus {driven_tag}: {dt:.1f} s, "
                f"Z[.,{col + 1}] = "
                f"{z_matrix[0, col]:+.6e}, {z_matrix[1, col]:+.6e} Ohm",
                flush=True,
            )

    return dict(
        padding=padding,
        ncells=int(ncells),
        z=z_matrix,
        times=times,
        energies=energies,
        currents=currents,
        volumes=volumes,
        t_mesh=t_mesh,
        mesh=msh,
        cell_tags=cell_tags,
    )


def energy_sweep(box: dict, args, comm) -> None:
    """`check_energy_continuity` over a short sweep on the box already meshed.

    Box resonances sit far above 10 MHz for a 20 cm cavity, so this is expected
    to be quiet — which is the point: a triggered guard here would mean the
    quasistatic reference is being compared against a resonant field.
    """
    log = comm.rank == 0
    freqs = [FREQUENCY_HZ * s for s in args.sweep_scales]
    energies = []
    for f in freqs:
        fields, dt = _solve_driving(
            box["mesh"], box["cell_tags"], TORUS_TAGS[0], comm, frequency_hz=f
        )
        w = stored_electric_energy(fields, comm)
        energies.append(w)
        if log:
            print(f"  f = {f:.4g} Hz: W = {w:.6e} J  ({dt:.1f} s)", flush=True)
    report = check_energy_continuity(freqs, energies)
    if log:
        print(
            f"  |d ln W / d ln f| max = {report.max_slope:.4f}"
            f" (threshold {report.slope_threshold}), triggered = {report.triggered}",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paddings", type=float, nargs="+", default=[0.08])
    parser.add_argument("--h-wire", type=float, default=0.0025)
    parser.add_argument("--h-far", type=float, default=0.02)
    parser.add_argument("--energy-sweep", action="store_true")
    parser.add_argument("--mesh-only", action="store_true")
    parser.add_argument("--sweep-scales", type=float, nargs="+", default=[0.7, 1.0, 1.4])
    args = parser.parse_args()

    comm = MPI.COMM_WORLD
    log = comm.rank == 0

    omega = 2.0 * np.pi * FREQUENCY_HZ
    k0 = omega * np.sqrt(MU_0 * EPSILON_0)

    if log:
        print("=== PORT-1 step 1: two-loop reaction Z-matrix probe ===", flush=True)
        print(
            f"  f = {FREQUENCY_HZ:.4g} Hz, a = {MAJOR_RADIUS} m, "
            f"r_wire = {MINOR_RADIUS} m, d = {SEPARATION} m, air only",
            flush=True,
        )
        for p in args.paddings:
            half_x = MAJOR_RADIUS + MINOR_RADIUS + p
            half_z = SEPARATION / 2 + MINOR_RADIUS + p
            diag = 2.0 * np.sqrt(2.0 * half_x**2 + half_z**2)
            print(
                f"  padding {p:.3f} m: box diagonal {diag:.4f} m, "
                f"k0*diag = {k0 * diag:.5f}  (want << 1)",
                flush=True,
            )

    # Closed form, filamentary loops: M₁₂ = 2πa·A_φ(a, d)/I (Jackson 5.37).
    m_nominal = mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, SEPARATION)
    corners = [
        mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS + dr, SEPARATION + dz)
        for dr in (-MINOR_RADIUS, 0.0, MINOR_RADIUS)
        for dz in (-MINOR_RADIUS, 0.0, MINOR_RADIUS)
    ]
    m_lo, m_hi = min(corners), max(corners)
    if log:
        print(
            f"\n  closed form: M12 = {m_nominal:.6e} H, omega*M12 = "
            f"{omega * m_nominal:+.6e} Ohm",
            flush=True,
        )
        print(
            f"  finite-section spread (rho, z within +/- r_wire): M12 in "
            f"[{m_lo:.6e}, {m_hi:.6e}] H  "
            f"({(m_hi - m_lo) / m_nominal:.1%} of nominal)",
            flush=True,
        )
        # Doubling d is the physics control step 2 may use as a third solve.
        m_2d = mutual_inductance(MAJOR_RADIUS, MAJOR_RADIUS, 2.0 * SEPARATION)
        print(f"  M(2d)/M(d) = {m_2d / m_nominal:.6f}", flush=True)

    results = [run_box(p, args, comm) for p in args.paddings]

    if args.energy_sweep:
        if log:
            print("\n=== energy continuity (smallest box) ===", flush=True)
        energy_sweep(results[0], args, comm)

    if log:
        print("\n=== summary ===", flush=True)
        for r in results:
            z = r["z"]
            asym = np.linalg.norm(z - z.T) / np.linalg.norm(z)
            z12 = 0.5 * (z[0, 1] + z[1, 0])
            print(
                f"\n  padding {r['padding']:.3f} m, {r['ncells']} cells", flush=True
            )
            print(
                f"    Z = [[{z[0,0]:+.6e}, {z[0,1]:+.6e}],\n"
                f"         [{z[1,0]:+.6e}, {z[1,1]:+.6e}]] Ohm",
                flush=True,
            )
            print(f"    reciprocity ||Z-Z^T||/||Z|| = {asym:.4e}", flush=True)
            print(
                f"    Im Z12 (symmetrised) = {z12.imag:+.6e} Ohm vs omega*M12 = "
                f"{omega * m_nominal:+.6e} Ohm  "
                f"({z12.imag / (omega * m_nominal) - 1.0:+.2%})",
                flush=True,
            )
            print(
                f"    |Re Z12|/|Im Z12| = {abs(z12.real) / abs(z12.imag):.4e}"
                f"  (lossless domain: a real part is numerical)",
                flush=True,
            )
            print(
                f"    Im Z11, Im Z22 = {z[0,0].imag:+.6e}, {z[1,1].imag:+.6e} Ohm",
                flush=True,
            )
            print(
                f"    slowest solve {max(r['times']):.1f} s, mesh {r['t_mesh']:.1f} s",
                flush=True,
            )
        if len(results) >= 2:
            a, b = results[0], results[1]
            za = 0.5 * (a["z"][0, 1] + a["z"][1, 0])
            zb = 0.5 * (b["z"][0, 1] + b["z"][1, 0])
            print(
                f"\n  box sensitivity {a['padding']:.3f} -> {b['padding']:.3f} m: "
                f"Im Z12 moves {abs(zb.imag / za.imag - 1.0):.3%}",
                flush=True,
            )
        print("  NOTE: nothing is asserted here — this is the PORT-1 step-1 probe.",
              flush=True)


if __name__ == "__main__":
    main()
