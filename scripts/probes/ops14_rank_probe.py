"""OPS-14 probe: locate the rank-dependence of `test_single_port_excitation`.

Diagnosis only (PROJECT_PLAN.md §7 `OPS-14`). Rebuilds the fixture of
`tests/solver/test_single_port_excitation.py` and prints, for whatever rank
count it is launched with:

1. the per-rank *local* tag set read by `problem.cell_tags.values` — the
   argument `ports/excitation.py:249` hands to `validate_required_port_tags_exist`;
2. the allgathered *global* tag set, which is the rank-count invariant;
3. the production call's outcome (raises / returns) and which ranks raise;
4. a counterfactual re-run in which only the validator's argument is replaced
   by the allgathered set — everything else untouched — so the downstream
   V/I/coupling numbers can be compared digit-for-digit across rank counts.

(3) vs (4) is the measurement: if (4) is byte-identical across -n 1/2/8 then
the single rank-local read at line 249 is the whole defect.

Run (standard tier):

    PYTHONPATH=/workspace/src mpiexec -n <N> python3 scripts/probes/ops14_rank_probe.py
"""

from __future__ import annotations

import warnings

import numpy as np
from mpi4py import MPI
from dolfinx import fem
from dolfinx.mesh import create_unit_cube, meshtags

from fem_em_solver.core import HomogeneousMaterial, TimeHarmonicFields, TimeHarmonicProblem
from fem_em_solver.ports import PortDefinition, run_single_port_excitation_case
from fem_em_solver.ports import excitation as excitation_module
from fem_em_solver.ports.definitions import validate_required_port_tags_exist

PORT_TAGS = (11, 12, 21, 22)


class DummyTimeHarmonicSolver:
    """Byte-identical stand-in for the solver the test patches in."""

    def __init__(self, problem, degree=1):
        self.problem = problem
        self.degree = degree

    def solve(self, **_kwargs):
        dg_vec = fem.functionspace(self.problem.mesh, ("DG", 1, (3,)))
        dg0 = fem.functionspace(self.problem.mesh, ("DG", 0))

        e_real = fem.Function(dg_vec, name="E_real_dummy")
        e_imag = fem.Function(dg_vec, name="E_imag_dummy")
        sigma = fem.Function(dg0, name="sigma_dummy")
        epsilon_r = fem.Function(dg0, name="epsilon_dummy")

        e_real.x.array[:] = 0.0
        e_imag.x.array[:] = 1.0
        sigma.x.array[:] = 0.5
        epsilon_r.x.array[:] = 10.0

        return TimeHarmonicFields(
            e_real=e_real,
            e_imag=e_imag,
            frequency_hz=self.problem.frequency_hz,
            sigma_field=sigma,
            epsilon_r_field=epsilon_r,
        )


def build_test_problem(*, global_indices: bool = False):
    """Rebuild the test fixture.

    ``global_indices=False`` reproduces the test verbatim (tags from rank-local
    cell indices). ``global_indices=True`` is counterfactual B: the same
    round-robin taken over the *global* cell numbering, which makes both the
    tag set and the per-tag cell counts rank-count invariant.
    """
    comm = MPI.COMM_WORLD
    mesh = create_unit_cube(comm, 2, 1, 1)

    tdim = mesh.topology.dim
    index_map = mesh.topology.index_map(tdim)
    n_local_cells = index_map.size_local
    cell_indices = np.arange(n_local_cells, dtype=np.int32)
    ordinal = cell_indices + (index_map.local_range[0] if global_indices else 0)

    tags = np.array(PORT_TAGS, dtype=np.int32)
    cell_values = tags[ordinal % len(tags)]
    cell_tags = meshtags(mesh, tdim, cell_indices, cell_values)

    return TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=127.74e6,
        material=HomogeneousMaterial(sigma=0.2, epsilon_r=5.0, mu_r=1.0),
        cell_tags=cell_tags,
        facet_tags=None,
    )


def make_ports():
    return [
        PortDefinition(port_id="P1", positive_tag=11, negative_tag=12, orientation="cw"),
        PortDefinition(port_id="P2", positive_tag=21, negative_tag=22, orientation="cw"),
    ]


def call_case(problem, ports):
    return run_single_port_excitation_case(
        problem,
        ports,
        driven_port_id="P1",
        driven_port_index=0,
        drive_voltage_v=1.0 + 0.0j,
        terminated_port_impedance_ohm=50.0,
    )


def main() -> None:
    warnings.simplefilter("ignore")
    comm = MPI.COMM_WORLD
    rank, size = comm.rank, comm.size

    excitation_module.TimeHarmonicSolver = DummyTimeHarmonicSolver

    problem = build_test_problem()
    ports = make_ports()

    tdim = problem.mesh.topology.dim
    n_local = int(problem.mesh.topology.index_map(tdim).size_local)
    n_global = comm.allreduce(n_local)

    local_tags = sorted({int(v) for v in np.asarray(problem.cell_tags.values)})
    gathered = comm.allgather(local_tags)
    local_counts = comm.allgather(n_local)
    global_tags = sorted({int(t) for chunk in gathered for t in chunk})

    # Per-tag global cell counts — the placeholder's `support`, allreduced the
    # same way `run_placeholder_port_coupling_case` does it.
    tag_values = np.asarray(problem.cell_tags.values)
    tag_counts = {
        tag: int(comm.allreduce(int(np.count_nonzero(tag_values == tag)))) for tag in PORT_TAGS
    }

    # --- (3) production path, unmodified -------------------------------------
    prod_error = None
    try:
        call_case(problem, ports)
    except ValueError as exc:
        prod_error = str(exc)
    prod_errors = comm.allgather(prod_error)

    if rank == 0:
        print("=" * 78)
        print(f"OPS-14 rank probe: comm size = {size}")
        print(f"global cells = {n_global}   global tag set = {global_tags}")
        print(f"global per-tag cell counts = {tag_counts}")
        print("-" * 78)
        print("rank | local cells | local tag set (argument at excitation.py:249)")
        for r, chunk in enumerate(gathered):
            print(f"{r:4d} | {local_counts[r]:11d} | {sorted({int(x) for x in chunk})}")
        n_divergent = sum(1 for t in gathered if sorted({int(x) for x in t}) != global_tags)
        n_raised = sum(1 for e in prod_errors if e is not None)
        print("-" * 78)
        print(f"ranks whose local tag set != global tag set : {n_divergent} / {size}")
        print(f"production call raised ValueError on ranks   : {n_raised} / {size}")
        for r, e in enumerate(prod_errors):
            if e is not None:
                print(f"    rank {r}: {e}")

    # --- (4) counterfactual A: only the validator's argument becomes collective
    def _collective_validate(ports_, available_tags):
        merged = {
            int(t)
            for chunk in comm.allgather(sorted({int(t) for t in available_tags}))
            for t in chunk
        }
        return validate_required_port_tags_exist(ports_, available_tags=merged)

    excitation_module.validate_required_port_tags_exist = _collective_validate
    report(comm, "counterfactual A (collective validator argument, test fixture)", problem, ports)

    # --- (5) counterfactual B: fixture tags taken over global cell numbering ---
    excitation_module.validate_required_port_tags_exist = validate_required_port_tags_exist
    problem_b = build_test_problem(global_indices=True)
    tags_b = np.asarray(problem_b.cell_tags.values)
    counts_b = {
        tag: int(comm.allreduce(int(np.count_nonzero(tags_b == tag)))) for tag in PORT_TAGS
    }
    if rank == 0:
        print(f"  global per-tag cell counts = {counts_b}")
    report(comm, "counterfactual B (global-index fixture, production code)", problem_b, ports)

    if rank == 0:
        print("=" * 78)


def report(comm, title, problem, ports) -> None:
    """Run the production call and print its estimates, or the raising ranks."""
    if comm.rank == 0:
        print("-" * 78)
        print(title + ":")
    error = None
    result = None
    try:
        result = call_case(problem, ports)
    except ValueError as exc:
        error = str(exc)
    errors = comm.allgather(error)
    if comm.rank != 0:
        return
    n_raised = sum(1 for e in errors if e is not None)
    if n_raised:
        print(f"  raised on {n_raised} / {comm.size} ranks; rank 0: {errors[0]}")
        return
    driven = result.responses["P1"]
    passive = result.responses["P2"]
    ctx_p2 = result.solve_context["P2"]
    print(f"  P1.V = {driven.voltage_v.real:.12e}{driven.voltage_v.imag:+.12e}j")
    print(f"  P1.I = {driven.current_a.real:.12e}{driven.current_a.imag:+.12e}j")
    print(f"  P2.V = {passive.voltage_v.real:.12e}{passive.voltage_v.imag:+.12e}j")
    print(f"  P2.I = {passive.current_a.real:.12e}{passive.current_a.imag:+.12e}j")
    print(f"  P2.coupling = {ctx_p2.coupling_factor:.12e}")
    print(f"  P2.wrapped_ring_distance = {ctx_p2.wrapped_ring_distance}")


if __name__ == "__main__":
    main()
