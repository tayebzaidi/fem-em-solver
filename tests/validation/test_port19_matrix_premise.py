"""`PORT-19` step 1 — the matched-termination sweep's system matrix is
bit-identical across drives.

Step 2 (factor once per sweep, solve N right-hand sides) is void unless the
matrix a lumped-sheet sweep assembles does not depend on which port is
driven.  The code reading says it cannot: every port's sheet enters the
bilinear list (``ports/lumped.py:484-489``) through
:func:`lumped_port_bilinear_term`, whose only sheet coefficient is
``sheet.sheet_resistivity`` (``:276``), and ``spec.sheet(driven=...)`` changes
only ``source_voltage_v`` (``:392``).  The base ``bilinear_form`` takes no
sheet at all, so it cannot carry the drive.  This module **measures** that on
the gated 4-leg fixture instead of trusting it.

**Anchor (asserted, an exact identity, no tolerance).**  For each drive
k = P1..P4, ``sheets_k`` is built exactly as ``lumped.py:475-477`` builds it and
``A_k`` is the assembled sum over all four ports of
``lumped_port_bilinear_term``, each closure binding its sheet by default
argument as ``lumped.py:485`` does.  Every ``A_k`` has ``A_1``'s nonzero
pattern (rank-local CSR compared on each rank, the verdict reduced with a
logical AND) and ``(A_k - A_1).norm(NORM_INFINITY) == 0.0`` (a PETSc global
norm).  Per port, ``sheet(driven=True).sheet_resistivity`` equals
``sheet(driven=False).sheet_resistivity`` byte for byte.

**Controls (asserted).**  (i) The right-hand sides differ:
``||b_1 - b_2||_2 > 0`` from ``lumped_port_linear_term`` — a probe blind to the
drive would read 0.  (ii) Sensitivity: ``A`` built with a
``dataclasses.replace`` copy of P2's (frozen) spec at ``port_impedance_ohm``
51 Ohm instead of 50 differs from ``A_1`` (``||.||_inf > 0``), structurally,
since ``1/rho_s`` is the term's coefficient.  The magnitude is printed and no
factor is asserted (standing rule (e)).

Scope: no solve, no ``src/`` change, no speedup claim.

Run (complex build required)::

    scripts/testing/run_and_log.sh PORT-19-step1 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       FEM_EM_REQUIRE_COMPLEX=1 PYTHONPATH=/workspace/src timeout -k 30 180 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port19_matrix_premise.py -v -s --tb=short'"
"""

from __future__ import annotations

import dataclasses
import time

import numpy as np
import pytest
import ufl
from dolfinx import fem
from dolfinx.fem.petsc import assemble_matrix, assemble_vector
from mpi4py import MPI
from petsc4py import PETSc

from fem_em_solver.core import TimeHarmonicSolver
from fem_em_solver.ports.lumped import (
    lumped_port_bilinear_term,
    lumped_port_linear_term,
)

from tests.complex_mode import complex_only
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep

# Control (ii)'s perturbed termination: P2 at 51 Ohm instead of the sweep's 50.
PERTURBED_PORT_ID = "P2"
PERTURBED_PORT_IMPEDANCE_OHM = 51.0


def _sheets_for_drive(port_defs, specs, driven_port_id):
    """``sheets_k`` exactly as ``ports/lumped.py:460-477`` builds it."""
    spec_by_id = {spec.port_id: spec for spec in specs}
    for spec in specs:
        spec.validate()
    port_ids = [port.port_id for port in port_defs]
    return port_ids, {
        pid: spec_by_id[pid].sheet(driven=(pid == driven_port_id)) for pid in port_ids
    }


def _assemble_port_matrix(msh, facet_tags, v_space, port_ids, sheets, omega):
    """Sum over all ports of the sheet term, closures bound by default argument."""
    terms = [
        lambda trial, test, _s=sheets[pid]: lumped_port_bilinear_term(
            msh, facet_tags, _s, trial, test, omega_rad_per_s=omega
        )
        for pid in port_ids
    ]
    trial = ufl.TrialFunction(v_space)
    test = ufl.TestFunction(v_space)
    a = None
    for term in terms:
        a = term(trial, test) if a is None else a + term(trial, test)
    mat = assemble_matrix(fem.form(a))
    mat.assemble()
    return mat


def _assemble_driven_rhs(msh, facet_tags, v_space, sheets, driven_port_id, omega):
    """The driven sheet's load term, as ``lumped.py:490-493`` builds it."""
    terms = [
        lambda test, _s=sheets[driven_port_id]: lumped_port_linear_term(
            msh, facet_tags, _s, test, omega_rad_per_s=omega
        )
    ]
    test = ufl.TestFunction(v_space)
    vec = assemble_vector(fem.form(terms[0](test)))
    vec.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)
    return vec


def _same_pattern(mat_a, mat_b, comm):
    """Rank-local CSR structure compared per rank; verdict reduced with AND."""
    ia_a, ja_a, _ = mat_a.getValuesCSR()
    ia_b, ja_b, _ = mat_b.getValuesCSR()
    local = bool(np.array_equal(ia_a, ia_b) and np.array_equal(ja_a, ja_b))
    return bool(comm.allreduce(local, op=MPI.LAND))


def _difference(mat_k, mat_1, comm):
    """``||A_k - A_1||_inf`` (global) plus a rank-reduced differing-entry census."""
    diff = mat_k.copy()
    diff.axpy(-1.0, mat_1, structure=PETSc.Mat.Structure.DIFFERENT_NONZERO_PATTERN)
    norm_inf = float(diff.norm(PETSc.NormType.NORM_INFINITY))
    _, _, vals_k = mat_k.getValuesCSR()
    _, _, vals_1 = mat_1.getValuesCSR()
    if vals_k.shape == vals_1.shape:
        changed = int(np.count_nonzero(vals_k != vals_1))
        max_abs = float(np.max(np.abs(vals_k - vals_1))) if vals_k.size else 0.0
    else:
        changed, max_abs = -1, float("nan")
    diff.destroy()
    return (
        norm_inf,
        int(comm.allreduce(changed, op=MPI.SUM)) if changed >= 0 else -1,
        float(comm.allreduce(max_abs, op=MPI.MAX)),
    )


@pytest.fixture(scope="module")
def premise():
    comm = MPI.COMM_WORLD
    t0 = time.perf_counter()
    built = build_four_port_sweep(build_only=True)
    t_build = time.perf_counter() - t0

    msh = built["mesh"]
    facet_tags = built["facet_tags"]
    problem = built["problem"]
    port_defs = built["port_defs"]
    specs = built["specs"]
    omega = 2.0 * np.pi * float(problem.frequency_hz)
    # The sweep's own space: `run_lumped_sheet_port_case` defaults degree=1 and
    # builds `TimeHarmonicSolver(problem, degree=degree)`.
    v_space = TimeHarmonicSolver(problem, degree=1).function_space()

    t1 = time.perf_counter()
    port_ids = [port.port_id for port in port_defs]
    mats, rhs, sheets_by_drive = {}, {}, {}
    for pid in port_ids:
        ids_k, sheets_k = _sheets_for_drive(port_defs, specs, pid)
        assert ids_k == port_ids
        sheets_by_drive[pid] = sheets_k
        mats[pid] = _assemble_port_matrix(msh, facet_tags, v_space, ids_k, sheets_k, omega)
        rhs[pid] = _assemble_driven_rhs(msh, facet_tags, v_space, sheets_k, pid, omega)

    ref = port_ids[0]
    a1 = mats[ref]
    a1_norm = float(a1.norm(PETSc.NormType.NORM_INFINITY))
    comparisons = {}
    for pid in port_ids:
        comparisons[pid] = {
            "pattern": _same_pattern(mats[pid], a1, comm),
            "diff": _difference(mats[pid], a1, comm),
        }

    b_diff = rhs[port_ids[0]].copy()
    b_diff.axpy(-1.0, rhs[port_ids[1]])
    b_diff_norm = float(b_diff.norm(PETSc.NormType.NORM_2))
    b1_norm = float(rhs[port_ids[0]].norm(PETSc.NormType.NORM_2))
    b2_norm = float(rhs[port_ids[1]].norm(PETSc.NormType.NORM_2))
    b_diff.destroy()

    # Control (ii): a copy of P2's frozen spec at 51 Ohm; every other field kept.
    spec_by_id = {spec.port_id: spec for spec in specs}
    original = spec_by_id[PERTURBED_PORT_ID]
    perturbed = dataclasses.replace(
        original, port_impedance_ohm=PERTURBED_PORT_IMPEDANCE_OHM
    )
    specs_pert = [perturbed if s.port_id == PERTURBED_PORT_ID else s for s in specs]
    ids_p, sheets_p = _sheets_for_drive(port_defs, specs_pert, ref)
    a_pert = _assemble_port_matrix(msh, facet_tags, v_space, ids_p, sheets_p, omega)
    pert_pattern = _same_pattern(a_pert, a1, comm)
    pert_diff = _difference(a_pert, a1, comm)
    t_assemble = time.perf_counter() - t1

    resistivity = {}
    for spec in specs:
        rd = spec.sheet(driven=True).sheet_resistivity
        ru = spec.sheet(driven=False).sheet_resistivity
        resistivity[spec.port_id] = (rd, ru)

    if comm.rank == 0:
        print(
            f"\n[PORT-19 step1] gated 4-leg fixture: {built['cells']} cells, "
            f"{v_space.dofmap.index_map.size_global * v_space.dofmap.index_map_bs} "
            f"N1curl(1) dofs, f = {problem.frequency_hz:.3e} Hz; build "
            f"{t_build:.2f} s, assemblies {t_assemble:.2f} s at -n {comm.size}",
            flush=True,
        )
        print(
            f"    A_1 = sum of the four sheet terms, P1 driven: global size "
            f"{a1.getSize()}, ||A_1||_inf = {a1_norm:.9e}",
            flush=True,
        )
        for pid in port_ids:
            c = comparisons[pid]
            print(
                f"    drive {pid}: pattern == A_1: {c['pattern']};  "
                f"||A_k - A_1||_inf = {c['diff'][0]!r};  differing CSR values "
                f"{c['diff'][1]};  max |dA| {c['diff'][2]!r}",
                flush=True,
            )
        for pid, (rd, ru) in resistivity.items():
            print(
                f"    {pid}: rho_s(driven) = {rd!r}  rho_s(undriven) = {ru!r}  "
                f"V_src driven {spec_by_id[pid].sheet(driven=True).source_voltage_v!r}",
                flush=True,
            )
        print(
            f"    control (i): ||b_1||_2 = {b1_norm:.9e}  ||b_2||_2 = {b2_norm:.9e}  "
            f"||b_1 - b_2||_2 = {b_diff_norm:.9e}",
            flush=True,
        )
        print(
            f"    control (ii): P2 at {PERTURBED_PORT_IMPEDANCE_OHM} Ohm (was "
            f"{original.port_impedance_ohm!r}); pattern == A_1: {pert_pattern};  "
            f"||A_pert - A_1||_inf = {pert_diff[0]:.9e}  "
            f"(relative to ||A_1||_inf: {pert_diff[0] / a1_norm:.9e});  differing "
            f"CSR values {pert_diff[1]};  max |dA| {pert_diff[2]:.9e}",
            flush=True,
        )

    yield {
        "port_ids": port_ids,
        "comparisons": comparisons,
        "a1_norm": a1_norm,
        "b_diff_norm": b_diff_norm,
        "resistivity": resistivity,
        "original": original,
        "perturbed": perturbed,
        "pert_pattern": pert_pattern,
        "pert_diff": pert_diff,
    }

    for mat in mats.values():
        mat.destroy()
    for vec in rhs.values():
        vec.destroy()
    a_pert.destroy()


@complex_only
def test_every_drive_assembles_a_nonzero_port_matrix(premise):
    """The identity below is not vacuous: ``A_1`` is a nonzero operator."""
    assert premise["a1_norm"] > 0.0, "A_1 assembled to zero — the probe sees no sheet"


@complex_only
def test_every_drive_has_a_1s_nonzero_pattern(premise):
    bad = [pid for pid, c in premise["comparisons"].items() if not c["pattern"]]
    assert not bad, f"drives {bad} assemble a different nonzero pattern from A_1"


@complex_only
def test_the_port_matrix_is_bit_identical_across_drives(premise):
    bad = {
        pid: c["diff"]
        for pid, c in premise["comparisons"].items()
        if not (c["diff"][0] == 0.0)
    }
    assert not bad, (
        "premise false — the port matrix depends on the drive: "
        + "; ".join(
            f"{pid}: ||A_k - A_1||_inf = {d[0]!r}, {d[1]} CSR values differ, "
            f"max |dA| {d[2]!r}"
            for pid, d in bad.items()
        )
    )


@complex_only
def test_sheet_resistivity_does_not_depend_on_the_drive(premise):
    for pid, (rd, ru) in premise["resistivity"].items():
        assert np.asarray(rd).tobytes() == np.asarray(ru).tobytes(), (
            f"{pid}: rho_s(driven) = {rd!r} != rho_s(undriven) = {ru!r}"
        )


@complex_only
def test_control_i_the_right_hand_sides_differ(premise):
    assert premise["b_diff_norm"] > 0.0, (
        "||b_1 - b_2||_2 == 0 — the probe is blind to the drive"
    )


@complex_only
def test_control_ii_the_matrix_sees_a_termination_change(premise):
    original, perturbed = premise["original"], premise["perturbed"]
    assert perturbed.port_impedance_ohm == PERTURBED_PORT_IMPEDANCE_OHM
    assert original.port_impedance_ohm != PERTURBED_PORT_IMPEDANCE_OHM, (
        "dataclasses.replace mutated the fixture's spec"
    )
    assert premise["pert_pattern"], "the 51 Ohm copy changed the nonzero pattern"
    assert premise["pert_diff"][0] > 0.0, (
        "A with P2 at 51 Ohm equals A_1 — the probe is blind to rho_s"
    )
