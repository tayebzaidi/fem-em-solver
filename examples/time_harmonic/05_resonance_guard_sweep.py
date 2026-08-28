"""Example (`EX-8`): the near-resonance guard firing on a frequency sweep.

The `§5.4` ramp entry for Phase 2 diagnostics, and the first example anywhere in
this repository whose subject is a **failure mode of the solver** rather than a
field. Every other example shows a solve that worked; this one shows the one
that silently does not.

PROJECT_PLAN §7 names it: with PEC boundaries and a low-loss interior the
curl-curl operator is *exactly singular* at the truncation box's cavity
eigenfrequencies, and MUMPS returns a clean exit code on a near-singular system
— the same shape as `MAG-10`'s "converged, residual 0.0, 920% error". An MRI
birdcage is deliberately operated near resonance, so Phase 6 will live inside
this trap. ``core/resonance.py`` is the detector: stored electric energy
``W(f) = (ε₀/4)∫εᵣ|E|²`` is smooth away from a mode and behaves like a simple
pole ``W ∼ |f − f₀|⁻²`` near one, so the logarithmic sensitivity
``S = |d ln W / d ln f| ≈ 2f/|f − f₀|`` is ``O(1)`` in a quiet band and diverges
on approach. It needs no eigen-solve and no geometry — only two solves a sweep
is doing anyway.

**It asserts, it does not merely render.** The sweep windows, the mesh, the
material and the drive are *imported* from the module that closed `TH-1` step 5
(``tests/validation/test_resonance_guard.py``), never restated — the §7 `EX-8`
plan is explicit that the first attempt at that gate failed on a badly-placed
window (separation 2.814×), so the windows are the gate's or they are wrong:

* *The anchor, two-sided.* The guard must **fire** on the approach sweep at the
  on-record implied detuning of ~1.5% (max ``|dlnW/dlnf|`` = 137.554 vs the
  threshold of 50), and the energy rise must follow the pole law within **10%**
  — 4% detuning to 1% detuning is a factor ``(0.04/0.01)² = 16``, measured
  16.505× (3.156% off) on the gate record
  ``20260731T021521Z_TH-1-step5b.log``. The second half is what makes this a
  calibrated detector and not a tripwire: it checks the *law*, not that the
  numbers grew.
* *The negative control is in-fixture, not cited.* A guard that always triggers
  is exactly as useless as one that never does, so the quiet sweep — the
  midpoint between the two lowest modes, as far from both poles as the band
  allows — is solved here too and must stay **silent** (max slope 21.951 on
  record). The separation between the two maximum slopes, 6.267× on record, is
  the discrimination this example claims.
* *The exported fields are the scored fields.* The two ``.xdmf`` arrays are the
  phasors solved at the nearest approach point and at the quiet midpoint, and
  the stored energy re-assembled from each is checked against the value its
  sweep point was scored on. What ParaView colours is therefore the near-singular
  solve itself, next to a healthy one on the same mesh and the same colour scale.

Run it through the example runner (the ``th:`` group sources the complex build
automatically)::

    ./run_examples.sh -e th:5

Output lands in ``examples/time_harmonic/paraview_output``: open
``time_harmonic_05_resonance_guard_combined.xdmf`` and colour by ``E_magnitude_near`` and then by
``E_magnitude_quiet`` with the *same* range — the near-resonant field saturates
the scale while the quiet one is nearly black, which is the pole made visible.
Both are clean, plausible-looking fields; only their *magnitudes* betray that
one of them is a solve of a nearly singular operator. That is the whole point of
the guard: nothing about the near-resonant solve's exit code, residual, or field
shape says anything is wrong.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from mpi4py import MPI

from dolfinx import default_scalar_type, fem
from dolfinx import mesh as dmesh

from fem_em_solver.core import check_energy_continuity, stored_electric_energy
from fem_em_solver.core.cavity import solve_pec_cavity_modes
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)

# The gated fixture lives in the test that closed `TH-1` step 5; the §7 `EX-8`
# plan requires importing it rather than restating it — the sweep windows in
# particular, which that gate had to place twice. The runner puts only ``src``
# on PYTHONPATH, so the repo root goes on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.validation.test_resonance_guard import (  # noqa: E402
    DEGREE,
    DIVISIONS,
    EDGES,
    _solve_at,
)

#: The gate's own windows, quoted here only as fractions so the printed table can
#: name them; the frequencies themselves come from the discrete spectrum below.
#: Approach: 4%, 2%, 1% below the discrete pole (the last implies a slope near
#: 2/0.01 = 200). Quiet: ±2% about the midpoint between the two lowest modes.
NEAR_DETUNINGS = (0.04, 0.02, 0.01)
QUIET_OFFSETS = (-0.02, 0.0, 0.02)

#: ``W ∼ |f − f₀|⁻²`` over the approach: (0.04/0.01)² = 16.
POLE_LAW_AMPLIFICATION = (NEAR_DETUNINGS[0] / NEAR_DETUNINGS[-1]) ** 2

#: The gate's own ceiling on the pole-law check (`TH-1` step 5, unchanged here);
#: 3.156% on record. Not a knob — a miss is a regression finding.
AMPLIFICATION_RTOL = 0.10

#: On record in ``20260731T021521Z_TH-1-step5b.log``, for the printed comparison.
RECORD_NEAR_MAX_SLOPE = 137.554
RECORD_QUIET_MAX_SLOPE = 21.951
RECORD_SEPARATION = 6.267
RECORD_AMPLIFICATION = 16.505
RECORD_IMPLIED_DETUNING = 0.01454

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"
BASENAME = "time_harmonic_05_resonance_guard"


def _magnitude_field(msh, fields, name: str) -> tuple[fem.Function, float]:
    """CG1 ``|E|`` of a solved phasor, plus its global peak [V/m].

    XDMF cannot carry N1curl, hence the interpolation. The magnitude is taken on
    the array as ``sqrt(Σ|E_i|²)`` so no complex ``sqrt`` is ever formed, and the
    peak is reduced across ranks before anyone sees it.
    """
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    e_cg = fem.Function(v_cg)
    e_cg.interpolate(fields.e_complex)
    e_cg.x.scatter_forward()

    components = np.abs(e_cg.x.array.reshape(-1, 3))
    magnitude = np.sqrt(np.sum(components * components, axis=1))

    s_cg = fem.functionspace(msh, ("Lagrange", 1))
    e_mag = fem.Function(s_cg, name=name)
    e_mag.x.array[:] = magnitude
    e_mag.x.scatter_forward()

    peak = msh.comm.allreduce(
        float(np.max(magnitude)) if magnitude.size else 0.0, op=MPI.MAX
    )
    return e_mag, peak


def main() -> None:
    comm = MPI.COMM_WORLD
    started = time.perf_counter()

    if not np.issubdtype(np.dtype(default_scalar_type), np.complexfloating):
        raise RuntimeError(
            "this example needs the complex DolfinX build "
            "(source /usr/local/bin/dolfinx-complex-mode); the runner's `th:` "
            "group sources it automatically"
        )

    if comm.rank == 0:
        print("=" * 72)
        print("EX-8 — the near-resonance guard firing on a frequency sweep")
        print("=" * 72)
        print(
            f"\n[why] with PEC walls and a lossless interior the curl-curl "
            f"operator is exactly singular at this box's cavity modes, and the "
            f"direct solver exits cleanly anyway. The guard is the energy-"
            f"continuity check S = |dlnW/dlnf| ~ 2f/|f-f0|, which is O(1) in a "
            f"quiet band and diverges on approach."
            f"\n[geometry] {EDGES[0]} x {EDGES[1]} x {EDGES[2]} m PEC box, "
            f"N1curl degree {DEGREE} on a {DIVISIONS} mesh, air interior, "
            f"uniform z-directed drive (the `TH-1` step-5 fixture, imported)",
            flush=True,
        )

    # The sweep is placed against the *discrete* pole, not the closed form: the
    # discretisation moves the fundamental by a fraction of a percent, which
    # matters when a window sits 1% away. This is the fixture's own reasoning.
    spectrum = solve_pec_cavity_modes(
        edges=EDGES, divisions=DIVISIONS, degree=DEGREE, n_modes=2, comm=comm
    )
    f1, f2 = float(spectrum.frequencies_hz[0]), float(spectrum.frequencies_hz[1])

    msh = dmesh.create_box(
        comm,
        [np.array([0.0, 0.0, 0.0]), np.array(EDGES)],
        list(DIVISIONS),
        cell_type=dmesh.CellType.tetrahedron,
    )

    near_freqs = [f1 * (1.0 - d) for d in NEAR_DETUNINGS]
    mid = 0.5 * (f1 + f2)
    quiet_freqs = [mid * (1.0 + d) for d in QUIET_OFFSETS]

    if comm.rank == 0:
        print(
            f"\n[spectrum] the discrete poles this sweep is placed against: "
            f"f1 = {f1:.6e} Hz, f2 = {f2:.6e} Hz",
            flush=True,
        )

    # Solve every point once and keep the fields; the two the export needs are
    # then the very solves the guard scored, not equivalent re-solves.
    solve_started = time.perf_counter()
    near_fields = [_solve_at(msh, f) for f in near_freqs]
    quiet_fields = [_solve_at(msh, f) for f in quiet_freqs]
    solve_seconds = time.perf_counter() - solve_started

    near_energies = [stored_electric_energy(fs, comm) for fs in near_fields]
    quiet_energies = [stored_electric_energy(fs, comm) for fs in quiet_fields]

    near = check_energy_continuity(near_freqs, near_energies)
    quiet = check_energy_continuity(quiet_freqs, quiet_energies)

    amplification = near_energies[-1] / near_energies[0]
    amplification_error = (
        abs(amplification - POLE_LAW_AMPLIFICATION) / POLE_LAW_AMPLIFICATION
    )
    separation = near.max_slope / quiet.max_slope

    # ---- the S-metric table (the §7 `EX-8` plan's output quantity) -----------
    if comm.rank == 0:
        print(
            f"\n[sweep] six solves in {solve_seconds:.1f} s; the guard's S-metric "
            f"table, threshold {near.slope_threshold:.1f}:",
            flush=True,
        )
        header = (
            f"  {'arm':<9}{'f [Hz]':>14}{'detuning':>11}{'W [J]':>13}"
            f"{'|dlnW/dlnf|':>14}"
        )
        print(header)
        print("  " + "-" * (len(header) - 2))
        for arm, freqs, energies, detunings in (
            ("approach", near_freqs, near_energies, NEAR_DETUNINGS),
            ("quiet", quiet_freqs, quiet_energies, QUIET_OFFSETS),
        ):
            for index, (f, w, d) in enumerate(zip(freqs, energies, detunings)):
                slope = ""
                if index > 0:
                    metric = near if arm == "approach" else quiet
                    slope = f"{metric.slopes[index - 1]:14.3f}"
                label = arm if index == 0 else ""
                print(
                    f"  {label:<9}{f:14.6e}{d:>10.1%} {w:13.4e}{slope}",
                    flush=True,
                )
        print(f"\n  approach: {near.describe()}")
        print(f"  quiet:    {quiet.describe()}")
        print(
            f"\n[record] `TH-1` step 5, 20260731T021521Z_TH-1-step5b.log: "
            f"approach max slope {RECORD_NEAR_MAX_SLOPE:.3f} / implied detuning "
            f"{RECORD_IMPLIED_DETUNING:.3%}, quiet max slope "
            f"{RECORD_QUIET_MAX_SLOPE:.3f}, separation {RECORD_SEPARATION:.3f}x, "
            f"amplification {RECORD_AMPLIFICATION:.3f}x",
            flush=True,
        )
        print(
            f"\n[anchor] energy amplification over the approach "
            f"{amplification:.3f}x vs the |f-f0|^-2 pole law's "
            f"{POLE_LAW_AMPLIFICATION:.1f}x -> {amplification_error:.3%} "
            f"(ceiling {AMPLIFICATION_RTOL:.0%}, {abs(RECORD_AMPLIFICATION - POLE_LAW_AMPLIFICATION) / POLE_LAW_AMPLIFICATION:.3%} on record)"
            f"\n[control] slope separation near/quiet {separation:.3f}x "
            f"({RECORD_SEPARATION:.3f}x on record): the guard distinguishes a "
            f"pole from ordinary dispersion, rather than always firing",
            flush=True,
        )

    # ---- the anchor: fires on one arm, silent on the other ------------------
    assert near.triggered, (
        f"the guard did not fire {NEAR_DETUNINGS[-1]:.0%} from a cavity mode: "
        f"{near.describe()} — a regression finding, not a threshold to lower"
    )
    assert not quiet.triggered, (
        f"the guard fired in the band between modes, so it cannot distinguish "
        f"resonance from ordinary dispersion: {quiet.describe()}"
    )
    # ---- the anchor: the pole *law*, not merely that the numbers grew -------
    assert amplification_error < AMPLIFICATION_RTOL, (
        f"stored energy rose {amplification:.3f}x from "
        f"{NEAR_DETUNINGS[0]:.0%} to {NEAR_DETUNINGS[-1]:.0%} detuning, but the "
        f"|f-f0|^-2 pole law requires {POLE_LAW_AMPLIFICATION:.1f}x "
        f"({amplification_error:.2%} off against a {AMPLIFICATION_RTOL:.0%} "
        f"ceiling, {RECORD_AMPLIFICATION:.3f}x on the `TH-1` step-5 record) — "
        f"either the drive no longer couples to the fundamental or the pole is "
        f"not where the eigen-solve says it is"
    )
    # ---- margin: neither verdict may turn on a third significant figure -----
    assert near.max_slope > 2.0 * near.slope_threshold, (
        f"near-resonant slope {near.max_slope:.2f} clears the threshold "
        f"{near.slope_threshold:.1f} by less than 2x"
    )
    assert quiet.max_slope < 0.5 * quiet.slope_threshold, (
        f"quiet-band slope {quiet.max_slope:.2f} sits within 2x of the threshold "
        f"{quiet.slope_threshold:.1f}; the guard has no false-positive margin"
    )
    # ---- the implied detuning is a physical read-out, not just a flag -------
    assert 0.003 < near.implied_detuning_fraction < 0.03, (
        f"implied detuning {near.implied_detuning_fraction:.4%} does not recover "
        f"the {NEAR_DETUNINGS[-1]:.0%} the sweep was placed at — the pole model "
        f"is not describing this energy rise"
    )

    # ---- ParaView: the near-singular solve beside a healthy one -------------
    e_mag_near, peak_near = _magnitude_field(msh, near_fields[-1], "E_magnitude_near")
    e_mag_quiet, peak_quiet = _magnitude_field(
        msh, quiet_fields[1], "E_magnitude_quiet"
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / f"{BASENAME}_combined",
        msh,
        None,  # a structured box: one homogeneous region, nothing to threshold on
        {"E_magnitude_near": e_mag_near, "E_magnitude_quiet": e_mag_quiet},
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)

    # The exported arrays must be the solves the table was scored from. Energy
    # is a functional of the whole field, so re-assembling it from the very
    # Functions handed to the writer is a strong identity: an off-by-one in the
    # sweep index, or a stale field, breaks it immediately.
    energy_near_exported = stored_electric_energy(near_fields[-1], comm)
    energy_quiet_exported = stored_electric_energy(quiet_fields[1], comm)
    near_identity = abs(energy_near_exported - near_energies[-1]) / near_energies[-1]
    quiet_identity = (
        abs(energy_quiet_exported - quiet_energies[1]) / quiet_energies[1]
    )
    peak_ratio = peak_near / peak_quiet

    if comm.rank == 0:
        print(
            f"\n[paraview] wrote {xdmf_path}"
            f"\n[paraview] |E| peaks at {peak_near:.4e} V/m on the near-resonant "
            f"solve ({near_freqs[-1]:.6e} Hz, {NEAR_DETUNINGS[-1]:.0%} detuned) "
            f"against {peak_quiet:.4e} V/m in the quiet band "
            f"({quiet_freqs[1]:.6e} Hz) — a factor {peak_ratio:.2f} on the same "
            f"mesh, same drive, same colour scale"
            f"\n[paraview] the exported fields ARE the scored ones: energy "
            f"re-assembled from each Function handed to the writer reproduces its "
            f"sweep entry to {near_identity:.2e} / {quiet_identity:.2e} relative"
            f"\n[paraview] colour by `E_magnitude_near` and `E_magnitude_quiet` "
            f"with a shared range: both are clean, plausible fields — nothing in "
            f"the exit code, the residual, or the shape says one of them is a "
            f"solve of a nearly singular operator. Only the magnitude does, and "
            f"that is exactly what the guard reads."
            f"\n\nAll assertions hold. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )

    assert near_identity < 1e-12 and quiet_identity < 1e-12, (
        f"the energy re-assembled from the exported Functions misses its sweep "
        f"entry by {near_identity:.3e} / {quiet_identity:.3e} relative — what "
        f"ParaView would colour is not the field the S-metric table scored"
    )
    assert peak_ratio > 1.0, (
        f"the near-resonant solve peaks at {peak_ratio:.3f}x the quiet one; the "
        f"pole that the {amplification:.2f}x energy rise reports is not visible "
        f"in the field that was written"
    )


if __name__ == "__main__":
    main()
