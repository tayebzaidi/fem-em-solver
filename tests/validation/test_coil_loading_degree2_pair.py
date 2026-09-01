"""`TH-13` step 3a‴: the degree-2 coil identities, **one σ-half per process**.

Why this module exists.  :mod:`tests.validation.test_coil_loading_degree2`
solves the loaded/free pair at both orders in a single interpreter, and since
2026-08-18 nobody has been able to read its two degree-2 identity results:
``TH12_STEP2_MODE=full`` hit ``exit 124`` at the 570 s ceiling twice (`TH-13`
step 3a′ and 3a″).  3a″ partitioned the cost on the failing run itself — mesh
4.3 s, the full degree-1 row 46.8 s and green, and **the degree-2 pair alone
≥ 524 s** — so the module has no margin at degree 2 and the constraint that
actually binds a scheduled slot is the 660 s foreground window a harness run
must return its footer inside, not the 1200 s heavy tier.

The 18:00 review of 2026-08-31 ruled option (a): **shrink the case, do not
raise the ceiling.**  This module runs the same fixture with exactly one of the
two degree-2 solves, selected by ``TH12_DEGREE2_HALF``:

* ``loaded`` — σ = ``FEM_SIGMA_SLAB``, the conducting half-space;
* ``free``   — σ = 0, the control.

There is **no default**: an unset selector raises, because a module that
silently picked a half would report "the identity holds" while having observed
only one of the two solves the record covers.

Everything else is imported from step 2's module, never restated — the mesh
call (:func:`_build_baseline_mesh`), the pair solve
(:func:`_solve_pair`, used for the degree-1 row) and the §7 cost probe
(:func:`_cost_probe`).  The degree-1 row is kept in full: it is the probe's
input, it is the negative control that pins the fixture, and it costs 46.8 s.

**What each window observes** (three observations of the same records — the
trimmed original in probe mode, then this module twice):

* the mesh is the 138 490-cell `MAT-6` step-3 baseline (0.7.2: 138 619);
* the degree-1 ΔR control reproduces **+1.5834%** inside the 0.01 pp
  run-to-run floor, and both degree-1 identity residuals sit under 1e-9;
* the §7 cost probe prices degree 2 and returns its under-cap verdict.

**Pre-registered expectation** (`TH-13` step 3a‴, and the 08-18 record):
exactly **one red per half** — the degree-2 complex-power identity at the
**unloosened** 1e-9 — with a footer inside the ceiling.  A *green* degree-2
identity would contradict 2026-08-18 and is a finding to journal, not to
celebrate.  No record, band, tolerance or fixture parameter moves here.

**Cross-half tests.**  Two of the degree-2 checks compare the two solves —
the drive control ``||J′_loaded − J′_free||²`` and the ΔZ signs (which need
``z_loaded − z_free``).  One process holds one half, so they ``pytest.skip``
with that reason unless both halves are present, which in half mode they never
are.  The degree-2 ΔR reading against step 4's bracket is likewise unobservable
here and stays as 2026-08-18 recorded it.

Run (complex build only), one command per half::

    docker compose exec -T fem-em-solver bash -lc \\
      'source /usr/local/bin/dolfinx-complex-mode && cd /workspace && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 \\
       TH12_DEGREE2_HALF=loaded timeout -k 30 600 mpiexec -n 8 python3 -m \\
       pytest tests/validation/test_coil_loading_degree2_pair.py -v -s'
"""

from __future__ import annotations

import os

import numpy as np
import pytest
import ufl
from mpi4py import MPI

from dolfinx import fem

from fem_em_solver.core.resonance import stored_electric_energy
from tests.complex_mode import complex_only
from tests.validation.test_coil_loading_degree2 import (
    FREQUENCY_HZ,
    MEMORY_GUARD_FRACTION,
    _build_baseline_mesh,
    _cost_probe,
    _solve_pair,
)
from tests.validation.test_coil_loading_larmor_probe import (
    DR_REL_10MHZ,
    IDENTITY_TOLERANCE,
    NCELLS_BASELINE,
    _ohmic_power,
    _solve_projected_at,
    _stored_magnetic_energy,
)
from tests.validation.test_coil_loading_richardson_ladder import (
    DR_WOBBLE_FLOOR_PP,
)
from tests.validation.test_dodd_deeds_impedance import (
    FEM_LOOP_RADIUS,
    FEM_SIGMA_SLAB,
    WIRE_TAG,
    _azimuthal_current_density,
)
from tests.validation.test_dodd_deeds_projected_drive import _reduced_real
from tests.validation.test_lossy_sphere_degree2 import _rss_peak_bytes

#: The two σ values, by name.  ``loaded`` is the conducting half-space the
#: `MAT-6` record is measured against; ``free`` is the σ = 0 control.
HALF_SIGMA = {"loaded": FEM_SIGMA_SLAB, "free": 0.0}


def _half() -> str:
    """The selected σ-half.  **No default** — an unset selector is an error.

    Deliberate: a default would let a run report "the degree-2 identity holds"
    on the strength of one solve while reading as though it had seen both.  The
    message names the two legal values so an unset run is legible in the log
    rather than merely red.
    """
    raw = os.environ.get("TH12_DEGREE2_HALF")
    if raw is None or not raw.strip():
        raise RuntimeError(
            "TH12_DEGREE2_HALF is unset and this module has no default: set it "
            "to 'loaded' or 'free'.  One process solves one degree-2 half "
            "(`TH-13` step 3a‴) because the pair costs >= 524 s at -n 8 and "
            "does not return inside a scheduled window."
        )
    half = raw.strip().lower()
    if half not in HALF_SIGMA:
        raise ValueError(
            f"TH12_DEGREE2_HALF must be 'loaded' or 'free'; got {raw!r}"
        )
    return half


def _solve_half(msh, cell_tags, degree: int, comm, half: str) -> dict:
    """One σ-half at ``degree`` on an existing mesh — half of :func:`_solve_pair`.

    Body is :func:`_solve_pair`'s, with the second solve and every cross-half
    quantity (ΔZ, the drive mismatch) removed rather than reformulated: the
    current normalisation, the reaction integral over the whole domain, the two
    energy routes and the dissipation helper are the same imported helpers, so
    the identity residual computed here is the identity residual the pair
    computes, on the same solve.
    """
    sigma = HALF_SIGMA[half]
    fields, j_prime, t_solve = _solve_projected_at(
        msh, cell_tags, sigma, FREQUENCY_HZ, comm, degree=degree
    )

    x = ufl.SpatialCoordinate(msh)
    phi_hat = _azimuthal_current_density(1.0)(x)
    dx_wire = ufl.Measure(
        "dx", domain=msh, subdomain_data=cell_tags, subdomain_id=(WIRE_TAG,)
    )
    current = _reduced_real(ufl.inner(j_prime, phi_hat) * dx_wire, comm) / (
        2.0 * np.pi * FEM_LOOP_RADIUS
    )

    # The reaction integral over the WHOLE domain, reduced before the division —
    # `MAT-6` steps 3-8 and `TH-11` steps 1-5 form it exactly this way.  J' is
    # real, so inner()'s conjugation of its second argument is a no-op.
    reaction = comm.allreduce(
        fem.assemble_scalar(fem.form(ufl.inner(fields.e_complex, j_prime) * ufl.dx)),
        op=MPI.SUM,
    )
    z_reaction = complex(-reaction / current**2)

    omega = 2.0 * np.pi * FREQUENCY_HZ
    w_e = stored_electric_energy(fields, comm=comm)
    w_m = _stored_magnetic_energy(fields.e_complex, omega, comm)
    im_energy = 4.0 * omega * (w_m - w_e) / current**2

    return dict(
        degree=degree,
        half=half,
        sigma=sigma,
        current=current,
        z_reaction=z_reaction,
        w_e=w_e,
        w_m=w_m,
        im_energy=im_energy,
        im_reaction=z_reaction.imag,
        residual=abs(z_reaction.imag - im_energy) / abs(z_reaction.imag),
        p_loss=_ohmic_power(msh, cell_tags, fields.e_complex, sigma, comm),
        t_solve=t_solve,
        rss_peak=_rss_peak_bytes(comm),
    )


@pytest.fixture(scope="module")
def half_rows():
    """Mesh, the full degree-1 row, the cost probe, then **one** degree-2 solve.

    The order is step 2's and is load-bearing for the same reasons: the
    degree-1 row pins the fixture against its record *before* any degree-2
    number is read, and it is the measured input the §7 memory projection
    scales.  Only the last phase is halved.
    """
    half = _half()
    comm = MPI.COMM_WORLD
    msh, cell_tags, ncells, t_mesh = _build_baseline_mesh(comm)

    # Pre-solve baseline: interpreter + dolfinx + this mesh, subtracted from the
    # degree-1 peak so the projection scales only what the solve costs.
    rss_baseline = _rss_peak_bytes(comm)

    row1 = _solve_pair(msh, cell_tags, 1, comm)
    projection = _cost_probe(
        msh, comm, row1["n_dofs"], row1["rss_peak"], rss_baseline
    )

    if comm.rank == 0:
        print(
            f"\n[TH-13 3a''' | half {half!r} | f = {FREQUENCY_HZ / 1e6:g} MHz] "
            f"{ncells} cells, mesh {t_mesh:.1f} s at -n {comm.size}"
            f"\n[TH-13 3a'''] COST PROBE (before any degree-2 assembly): "
            f"{row1['n_dofs']} DOFs at degree 1 -> {projection['n_dofs_2']} at "
            f"degree 2 ({projection['dof_ratio']:.2f}x); projection "
            f"{projection['guard'] / 2**30:.2f} GiB (linear end "
            f"{projection['linear'] / 2**30:.2f} GiB) against "
            f"{MEMORY_GUARD_FRACTION:.0%} of memory.max = "
            f"{projection['threshold'] / 2**30:.2f} GiB"
            f"\n[TH-13 3a''']   VERDICT: "
            + (
                "OVER CAP — the degree-2 half is not attempted; this number is "
                "the result (§7 negative-result clause)"
                if projection["over_cap"]
                else "under cap — the degree-2 half is attempted"
            ),
            flush=True,
        )

    rows2 = {}
    if not projection["over_cap"]:
        rows2[half] = _solve_half(msh, cell_tags, 2, comm, half)

    if comm.rank == 0:
        _print_reading(half, row1, rows2, projection, ncells)

    return dict(
        half=half,
        row1=row1,
        rows2=rows2,
        projection=projection,
        ncells=ncells,
        t_mesh=t_mesh,
    )


def _print_reading(half, row1, rows2, projection, ncells) -> None:
    """The window's deliverable: the re-observed degree-1 row, then the half."""
    print(
        f"\n[TH-13 3a'''] READING at {FREQUENCY_HZ / 1e6:g} MHz on {ncells} "
        f"cells, half {half!r} (one σ-half per process — no ΔZ, no bracket "
        f"comparison; those are cross-half and stay as 2026-08-18 recorded them)"
    )
    print(
        f"  degree 1 (full pair, the control): {row1['n_dofs']:8d} DOFs, "
        f"dR deviation {row1['dr_dev']:+.4%} vs record {DR_REL_10MHZ:+.4%}, "
        f"solves {row1['t_loaded']:.1f} s + {row1['t_free']:.1f} s"
    )
    print(
        f"    identity residuals: loaded "
        f"{row1['identities']['loaded']['residual']:.4e}, free "
        f"{row1['identities']['free']['residual']:.4e} (bound "
        f"{IDENTITY_TOLERANCE:.0e})"
    )
    if half in rows2:
        row = rows2[half]
        print(
            f"  degree 2, {half}: {projection['n_dofs_2']:8d} DOFs, solve "
            f"{row['t_solve']:.1f} s, summed peak RSS "
            f"{row['rss_peak'] / 2**30:.2f} GiB (process high-water mark, so it "
            f"includes the degree-1 row — an upper bound on its own footprint)"
        )
        print(
            f"    Im Z reaction {row['im_reaction']:.6e} Ω vs energy "
            f"{row['im_energy']:.6e} Ω → residual {row['residual']:.4e} "
            f"(bound {IDENTITY_TOLERANCE:.0e}; W_m {row['w_m']:.4e} J, W_e "
            f"{row['w_e']:.4e} J); P_loss {row['p_loss']:+.7e} W"
        )
    else:
        print(
            "  degree 2 was not solved (cost probe over cap) — the projection "
            "above is this window's result"
        )


def _row2_or_skip(half_rows) -> dict:
    rows2 = half_rows["rows2"]
    half = half_rows["half"]
    if half not in rows2:
        projection = half_rows["projection"]
        pytest.skip(
            f"the degree-2 {half} solve was not attempted: cost-probe "
            f"projection {projection['guard'] / 2**30:.2f} GiB against "
            f"threshold {projection['threshold'] / 2**30:.2f} GiB "
            f"(over cap: {projection['over_cap']})"
        )
    return rows2[half]


def _both_halves_or_skip(half_rows) -> dict:
    """Cross-half tests need both degree-2 solves; one process holds one."""
    rows2 = half_rows["rows2"]
    if set(rows2) != set(HALF_SIGMA):
        pytest.skip(
            "cross-half comparison needs both degree-2 solves in one process; "
            f"this process holds {sorted(rows2) or 'none'} "
            "(`TH-13` step 3a‴ runs one σ-half per window because the pair "
            "costs >= 524 s at -n 8).  The reading stays as 2026-08-18 "
            "recorded it."
        )
    return rows2


# ---------------------------------------------------------------------------
# re-observed in every window: the fixture really is the fixture
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_the_mesh_is_the_mat6_step3_baseline(half_rows):
    """138 490 cells (0.7.2: 138 619) — the rung the record sits on.

    The element order never reaches the mesh generator, so a different count
    would mean this half is not the problem the 08-18 record covers.
    """
    ncells = half_rows["ncells"]
    print(f"\n  cells: {ncells} (record: {NCELLS_BASELINE})")
    assert ncells == NCELLS_BASELINE, (
        "the element order does not reach the mesh generator, so the count must "
        f"be the step-3 baseline's {NCELLS_BASELINE}; got {ncells}"
    )


@complex_only
@pytest.mark.integration
def test_the_degree1_control_reproduces_its_recorded_deviation(half_rows):
    """+1.5834% to the `MAT-6` step-8 run-to-run floor of 0.01 pp.

    Same-process pinning: the control shares this mesh object, rank count and
    interpreter with the degree-2 half, so a drift here invalidates the
    degree-2 reading before it is made.  The bound is a measured floor, not a
    fitted tolerance.
    """
    row = half_rows["row1"]
    moved_pp = 100.0 * (row["dr_dev"] - DR_REL_10MHZ)
    print(
        f"\n  degree 1: {row['dr_dev']:+.4%} vs record {DR_REL_10MHZ:+.4%} → "
        f"{moved_pp:+.5f} pp (floor {DR_WOBBLE_FLOOR_PP} pp)"
    )
    assert abs(moved_pp) <= DR_WOBBLE_FLOOR_PP, (
        f"the degree-1 anchor moved {moved_pp:+.5f} pp off its record "
        f"{DR_REL_10MHZ:+.4%}, beyond the {DR_WOBBLE_FLOOR_PP} pp run-to-run "
        "floor: the fixture changed under the record, so nothing measured at "
        "degree 2 here is comparable to it"
    )


@complex_only
@pytest.mark.integration
@pytest.mark.parametrize("which", ["loaded", "free"])
def test_the_degree1_identities_hold_in_this_window(half_rows, which):
    """Both degree-1 identity residuals under 1e-9, in **this** process.

    The degree-1 pair is solved in every window whichever half is selected, so
    this is the third observation of the same record (3a″ read 8.4704e-15 /
    3.7068e-15) and it is what licenses reading the degree-2 residual below as
    a statement about the element order rather than about the assembly.
    """
    entry = half_rows["row1"]["identities"][which]
    print(
        f"\n  degree 1, {which}: Im Z reaction {entry['im_reaction']:.6e} Ω vs "
        f"energy {entry['im_energy']:.6e} Ω → residual {entry['residual']:.4e} "
        f"(bound {IDENTITY_TOLERANCE:.0e})"
    )
    assert entry["residual"] < IDENTITY_TOLERANCE, (
        f"complex-power identity broken on the degree-1 {which} solve: "
        f"reaction {entry['im_reaction']:.6e} Ohm vs energy "
        f"{entry['im_energy']:.6e} Ohm, relative {entry['residual']:.4e}"
    )


@complex_only
@pytest.mark.integration
def test_the_cost_probe_priced_degree2_before_solving_it(half_rows):
    """The §7 probe produced a real number and the stop rule was evaluated.

    Degree-2 N1curl carries 2 DOFs per edge and 2 per face against degree 1's
    1 per edge, so on a tetrahedral mesh the ratio is bounded well away from 1:
    a probe reporting anything at or below unity has not priced the space it
    claims to.
    """
    projection = half_rows["projection"]
    print(
        f"\n  degree-2 DOFs {projection['n_dofs_2']} "
        f"({projection['dof_ratio']:.3f}x degree 1); projection "
        f"{projection['guard'] / 2**30:.2f} GiB vs threshold "
        f"{projection['threshold'] / 2**30:.2f} GiB "
        f"(over cap: {projection['over_cap']})"
    )
    assert projection["dof_ratio"] > 1.0, (
        f"degree 2 priced at {projection['dof_ratio']:.3f}x the degree-1 DOF "
        "count: a second-order N1curl space on the same mesh cannot have fewer "
        "unknowns, so the probe measured the wrong space"
    )
    assert np.isfinite(projection["guard"]), (
        "the memory projection is not finite, so the §7 stop rule was never "
        f"actually evaluated: {projection}"
    )


# ---------------------------------------------------------------------------
# the degree-2 half itself — the observation this split exists to make
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_complex_power_identity_holds_at_degree2(half_rows):
    """``Im Z = 4ω(W_m − W_e)/I′²`` to 1e-9 on the selected degree-2 solve.

    Exact for the discrete solution, so this gates bookkeeping rather than
    accuracy; the `TH-11` degree-1 rungs meet it at ~1e-14.  The bound is the
    step-2f family's and is **not** widened for the ~5.4x larger degree-2
    system — that is the whole point.  Pre-registered as **red** (2026-08-18);
    it is red here so that it is *observed* rather than assumed.
    """
    row = _row2_or_skip(half_rows)
    print(
        f"\n  degree 2, {row['half']}: Im Z reaction {row['im_reaction']:.6e} Ω "
        f"vs energy {row['im_energy']:.6e} Ω → residual {row['residual']:.4e} "
        f"(bound {IDENTITY_TOLERANCE:.0e}; W_m {row['w_m']:.4e} J, W_e "
        f"{row['w_e']:.4e} J)"
    )
    assert row["residual"] < IDENTITY_TOLERANCE, (
        f"complex-power identity broken on the {row['half']} solve at degree 2: "
        f"reaction {row['im_reaction']:.6e} Ohm vs energy "
        f"{row['im_energy']:.6e} Ohm, relative {row['residual']:.4e}"
    )


@complex_only
@pytest.mark.integration
def test_this_half_dissipates_what_its_sigma_says(half_rows):
    """σ = 0 ⇒ ``½∫σ|E|²`` is ``+0.0`` **exactly**; σ > 0 ⇒ positive.

    `EX-11`'s control at second order, read on whichever half this process
    holds.  A σ-blind pipeline returns the loaded value for both, so the
    separation is infinite by construction and the σ = 0 assertion is exact
    equality, not a band.  Across the two windows the pair of readings is the
    same statement the paired test made.
    """
    row = _row2_or_skip(half_rows)
    print(
        f"\n  degree 2, {row['half']} (σ = {row['sigma']:g} S/m): P_loss "
        f"{row['p_loss']:+.7e} W"
    )
    if row["half"] == "free":
        assert row["p_loss"] == 0.0, (
            "a σ = 0 slab must dissipate exactly nothing at degree 2, got "
            f"{row['p_loss']!r}"
        )
    else:
        assert row["p_loss"] > 0.0, (
            f"the loaded slab must dissipate at degree 2, got {row['p_loss']!r}"
        )


# ---------------------------------------------------------------------------
# cross-half: unobservable in half mode, skipped with the reason
# ---------------------------------------------------------------------------


@complex_only
@pytest.mark.integration
def test_both_solves_are_driven_by_the_same_projected_current(half_rows):
    """The drive control at 1e-24 — needs both halves' ``J′`` in one process."""
    rows2 = _both_halves_or_skip(half_rows)
    raise AssertionError(  # pragma: no cover - unreachable in half mode
        "both degree-2 halves are present, which half mode cannot produce; "
        f"re-scope this test before trusting it: {sorted(rows2)}"
    )


@complex_only
@pytest.mark.integration
def test_the_loaded_coil_dissipates_and_expels_flux(half_rows):
    """ΔR > 0, ΔX < 0 — needs ``z_loaded − z_free``, i.e. both halves."""
    rows2 = _both_halves_or_skip(half_rows)
    raise AssertionError(  # pragma: no cover - unreachable in half mode
        "both degree-2 halves are present, which half mode cannot produce; "
        f"re-scope this test before trusting it: {sorted(rows2)}"
    )
