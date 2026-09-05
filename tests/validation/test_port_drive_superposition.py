"""`POST-6` step 1 — ``ports.superpose_drives`` on the 4-leg birdcage, 10 MHz.

`WF-6` step 2 formed a quadrature drive **inside a test module**, by weighting
four DG0 ``B`` fields with ``e^{∓jkπ/2}``.  This module drives the same four
ports through the *package* entry point
:func:`~fem_em_solver.ports.superposition.superpose_drives` — a weighted sum of
the solved ``E`` phasors on their own N1curl space, from one
``run_n_port_sparameter_sweep(..., keep_fields=True)`` — and asserts that the
package reproduces what the test module measured, plus the first **drive-level**
power identity this repo has had.

**The fixture is imported, never rebuilt**: ``build_four_port_sweep`` (`PORT-9`
leg (d)), the sample-point construction, the rotation/mirror helpers, the phase
convention (:func:`quadrature_phase_weights`) and every band come from the
modules that gated them.

**The four anchors.**

* **(i) the identity digits.**  The ccw quadrature weights driven through the
  package reproduce `WF-6` step 2's two identities — C4 0.9818%, mirror
  0.8087% (``STEP2_IDENTITY_RECORDS``,
  ``20260831T033704Z_WF-6-step2.log:4698–4699``) — and the cw-sense negative
  control reproduces its 95.1975% miss (``STEP2_CONTROL_MISMATCH``, ``:4700``).
  Both asserted at ``CG1_RECORD_RTOL`` (1e-3, imported), and both **also** read
  against the fixture's own DG0 superposition *in the same run* at 1e-12.

  *On the rtol.*  The `POST-6` step-1 item pre-registered "rtol 1e-6" for this
  reproduction.  That is arithmetically unreachable and not because of any
  physics: the records are stored to four significant digits (``0.9818e-2``),
  so **any** measurement — including a bit-identical re-run of the run that
  produced them — can only agree with the literal to ±5.1e-5 relative.  The
  cross-run comparison is therefore made at the repo's own rtol for figures
  read through a Krylov solve (``CG1_RECORD_RTOL``), and the divergence the
  1e-6 was reaching for — *does the package path compute what the test module's
  path computes?* — is asserted **in-run at 1e-12**, six orders tighter than
  1e-6, in :func:`test_the_package_path_and_the_fixture_dg0_path_agree`.
  Nothing was widened: the 1e-6 was never executable against a 4-digit record.

* **(ii) linearity.**  ``superpose_drives`` is a linear map of the weight
  vector: ``w = e_k`` returns drive k's dof array *exactly*
  (``np.array_equal``), ``S(w₁) + S(w₂) = S(w₁ + w₂)`` to 1e-12, the combined
  port voltages and currents are the weighted sums of the single-drive ones to
  1e-12, and the mapping and sequence spellings of the weights agree exactly.

* **(iii) the drive-level power identity.**  ``P_acc = ½ aᴴ(I − SᴴS)a``, from
  the sweep's own power-wave ``S`` at ``z0 = 50 Ω``, against ``½∫σ|E_w|²`` over
  phantom **+** conductor of the superposed field.  Asserted at the imported
  ``POWER_BALANCE_BAND`` (1e-2): the item's 1e-3 sits *below* this fixture's own
  single-drive accounting floor of 9.795751e-03 (``…step2.log:4684``), so 1e-3
  is printed against and never asserted (scoped before measurement — see the
  `POST-6` §7 row note).  The **blind sum** ``Σ_k |w_k|²P_k`` — the same
  accounting with the cross terms dropped — is printed beside it, and asserted
  to miss only when the in-run cross-term share exceeds 10× the band.

* **(iv) the fixture.**  All four single-drive residuals reproduce step 1's
  ``STEP1_GATE_I_P1_RESIDUAL`` = 9.795751e-03 at 1e-3, which is what says these
  are the solves the records were made on.

**Step 1b — the denominator, measured in-run.**  Anchor (iii) misses by 11.6%,
and the review's working diagnosis was that the S-derived ``P_acc`` and the
fixture's ``supplied − Σ sheets`` accounting are simply not the same number, so
the 11.6% would be the fixture's own ~1% single-drive offset read against a 13×
smaller denominator.  That is an identity of the power-wave definition at
``z0 = Re Z_p`` and it had never been measured.  Here it is, per single drive k:

* **(1b-i) asserted** — ``P_acc,k = ½|a_k|²(1 − Σ_i |S_ik|²)`` equals
  ``P_net,k = supplied_k − Σ_i sheets_ik`` (all four sheets, the driven one
  included) to ``STEP1B_POWER_WAVE_RTOL`` = 1e-6.
* **(1b-ii) asserted** — the superposed ccw ``P_acc`` reproduces step 1's
  ``STEP1_SUPERPOSED_ACCEPTED_W`` (3.014424803e-03 W,
  ``20260905T004202Z_POST-6.log:1915``) at rtol 1e-9.  Same solves, same path:
  a regression pin, not a new measurement.
* **printed, never asserted** — the four single-drive residuals
  ``|P_acc,k − P_vol,k| / P_acc,k`` and the ratio of the superposed 11.6% to
  their mean.
* **negative control** — ``P_acc,k`` recomputed with the reflection diagonal
  zeroed must break (1b-i).  Its miss is exactly ``|S_kk|²/(1 − Σ_i |S_ik|²)``,
  computed from the assembled 4×4 **before** the assertion and printed; the
  floor asserted is ``STEP1B_CONTROL_MIN_MISS`` = 1e-3, 1000× the band, and
  nothing above the computed value is claimed.

``POWER_BALANCE_BAND`` is **not** re-pointed here — the §7 disposition rule
names the next review as the actor, on these printed numbers.

**Scope.**  One entry point and its identities, on the 4-leg fixture at 10 MHz.
No tuning, no 32-port drive (step 2), no re-pointing of `WF-6`/`WF-7`, no band
moved, and no claim beyond "a package-level multi-port drive exists and closes
these identities".

Run (complex build required)::

    scripts/testing/run_and_log.sh POST-6 "docker compose exec -T fem-em-solver \\
      bash -lc 'cd /workspace && source /usr/local/bin/dolfinx-complex-mode && \\
       PYTHONPATH=/workspace/src FEM_EM_REQUIRE_COMPLEX=1 timeout -k 30 590 \\
       mpiexec -n 2 python3 -m pytest tests/environment \\
       tests/validation/test_port_drive_superposition.py -v -s'"
"""

from __future__ import annotations

import numpy as np
import pytest

from fem_em_solver.ports import run_n_port_sparameter_sweep, superpose_drives
from fem_em_solver.post import magnetic_flux_density_from_e, mean_sar, project_to_cg1

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.validation.test_birdcage_b1_plus_map import (  # noqa: F401 — imported bands/helpers
    CG1_RECORD_RTOL,
    C4_COVARIANCE_BAND,
    PHANTOM_RHO_KG_PER_M3,
    POWER_BALANCE_BAND,
    STEP1_GATE_I_P1_RESIDUAL,
    _power_shares,
    _relative_l2,
    _rotate_z,
    _sample_points,
)
from tests.validation.test_birdcage_b1_quadrature import (
    QUADRATURE_STEP_DEG,
    STEP2_CONTROL_MISMATCH,
    STEP2_IDENTITY_RECORDS,
    _mirror_xy,
    _port_index,
    _read_senses,
    _superpose_dg0,
    quadrature_phase_weights,
)
from tests.validation.test_port_birdcage_four_port import build_four_port_sweep
from tests.validation.test_port_birdcage_lumped_column import (
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)

# The item's pre-stated power figure.  **Printed, never asserted**: it is below
# this fixture's own single-drive accounting floor (9.795751e-03), so asserting
# it would be asserting that the superposed accounting beats the single-drive
# one.  ``POWER_BALANCE_BAND`` (imported, 1e-2) is the assertion.
PRINTED_POWER_TARGET = 1.0e-3

# Two paths through the *same* stored solves must agree to round-off: the
# package's (superpose E on N1curl, then curl) and the fixture's (curl each
# drive, then superpose the DG0 B).  Both are linear in the same fields, so a
# disagreement above this is a defect in one of them and not a tolerance
# question.
PATH_AGREEMENT_MAX = 1.0e-12

# Cross-term rule for (iii), pre-registered by the §9 item: the blind sum is
# printed unconditionally, and asserted to miss the identity only when the
# cross terms it drops are worth more than this multiple of the band.
CROSS_TERM_TRIGGER = 10.0 * POWER_BALANCE_BAND
BLIND_SUM_MIN_MISS = 5.0 * POWER_BALANCE_BAND

# --- `POST-6` step 1b ------------------------------------------------------
#
# The power-wave definition's own identity at ``z0 = Re Z_p``: the accepted
# power a drive's S-column reports and the terminal accounting's
# ``supplied − Σ sheets`` are the *same* quantity written two ways, so their
# agreement is limited only by the arithmetic that assembled S from the same
# stored terminal readings — not by any discretisation.  1e-6 is therefore a
# statement about the assembly, and a miss is a finding, not a tolerance.
STEP1B_POWER_WAVE_RTOL = 1.0e-6

# Step 1's superposed ccw reading (`20260905T004202Z_POST-6.log:1915`).  Pinned
# at 1e-9 because this module re-runs the *same* solves through the *same* path:
# nothing here is allowed to move it.
STEP1_SUPERPOSED_ACCEPTED_W = 3.014424803e-03
STEP1B_ACCEPTED_RTOL = 1.0e-9

# Negative-control floor: 1000× ``STEP1B_POWER_WAVE_RTOL``.  The control's true
# miss is ``|S_kk|²/(1 − Σ_i |S_ik|²)``, computed from the assembled 4×4 and
# printed before the assertion; this floor is what is *claimed*.
STEP1B_CONTROL_MIN_MISS = 1.0e-3


def _loss_power_w(sweep, e_complex, sigma_field):
    """``½∫σ|E|²`` over the phantom and the conductor, MPI-reduced."""
    kwargs = dict(
        sigma=sigma_field,
        rho=PHANTOM_RHO_KG_PER_M3,
        cell_tags=sweep["cell_tags"],
        comm=sweep["mesh"].comm,
    )
    phantom = float(
        mean_sar(e_complex, subdomain_ids=PHANTOM_CELL_TAG, **kwargs)["dissipated_power_w"]
    )
    conductor = float(
        mean_sar(e_complex, subdomain_ids=CONDUCTOR_CELL_TAG, **kwargs)[
            "dissipated_power_w"
        ]
    )
    return phantom, conductor


@pytest.fixture(scope="module")
def superposition_case():
    """One mesh, one field-keeping sweep, and both quadrature senses.

    The four solves happen **once**, inside
    ``run_n_port_sparameter_sweep(keep_fields=True)``; everything below is
    arithmetic on their stored phasors.
    """
    sweep = build_four_port_sweep()
    comm = sweep["mesh"].comm

    result = run_n_port_sparameter_sweep(
        sweep["problem"],
        sweep["port_defs"],
        lumped_sheet_ports=sweep["specs"],
        lumped_sheet_facet_tags=sweep["facet_tags"],
        keep_fields=True,
    )
    port_ids = list(result.port_ids)

    azimuths = {
        f"P{s['tag'] - SHEET_IFACE}": float(s["azimuth_deg"]) for s in sweep["sheets"]
    }
    delta_deg = (azimuths["P2"] - azimuths["P1"]) % 360.0
    slots = {
        pid: _port_index(azimuths[pid], azimuths["P1"], QUADRATURE_STEP_DEG)
        for pid in port_ids
    }
    ks = np.array([slots[pid] for pid in port_ids], dtype=float)
    weights = {
        sense: quadrature_phase_weights(ks, sense) for sense in ("ccw", "cw")
    }

    drives = {sense: superpose_drives(result, weights[sense]) for sense in weights}

    # The fixture's own path on the *same* stored fields: curl each drive, then
    # superpose the DG0 B.  This is the in-run comparison anchor (i) rests on.
    omega = 2.0 * np.pi * float(sweep["problem"].frequency_hz)
    b_per_drive = {
        pid: magnetic_flux_density_from_e(result.fields[pid].e_complex, omega)
        for pid in port_ids
    }
    fixture_dg0 = {
        sense: _superpose_dg0(
            [b_per_drive[pid] for pid in port_ids], weights[sense], f"B_fixture_{sense}"
        )
        for sense in weights
    }

    points = _sample_points(sweep)
    images = {
        "x": points,
        "Rx": _rotate_z(points, np.radians(delta_deg)),
        "Mx": _mirror_xy(points, azimuths["P1"]),
    }

    def identities(b_by_sense, tag):
        cg1 = {
            sense: project_to_cg1(b_by_sense[sense], name=f"B_{tag}_{sense}_cg1")
            for sense in b_by_sense
        }
        reads = {}
        for sense in cg1:
            for label, pts in images.items():
                plus, minus, valid = _read_senses(cg1[sense], pts)
                reads[(sense, label)] = {"plus": plus, "minus": minus, "valid": valid}
        mask = np.logical_and.reduce([r["valid"] for r in reads.values()])
        return mask, {
            "(a) C4 |B1+|_ccw(Rx) vs |B1+|_ccw(x)": _relative_l2(
                reads[("ccw", "Rx")]["plus"], reads[("ccw", "x")]["plus"], mask
            ),
            "(b) mirror |B1-|_cw(Mx) vs |B1+|_ccw(x)": _relative_l2(
                reads[("cw", "Mx")]["minus"], reads[("ccw", "x")]["plus"], mask
            ),
            "control |B1+|_cw(Mx) vs |B1+|_ccw(x)": _relative_l2(
                reads[("cw", "Mx")]["plus"], reads[("ccw", "x")]["plus"], mask
            ),
        }

    mask_pkg, package_identities = identities(
        {sense: drives[sense].b_complex for sense in drives}, "pkg"
    )
    mask_fix, fixture_identities = identities(fixture_dg0, "fix")

    # (iv) the four single-drive power accountings, through the fixture's own
    # ``_power_shares`` on the stored fields.
    v_src = {spec.port_id: complex(spec.drive_voltage_v) for spec in sweep["specs"]}
    shares, residuals, single_losses = {}, {}, {}
    for pid in port_ids:
        responses = result.excitation_results[pid].responses
        solved = {
            "driven": pid,
            "fields": result.fields[pid],
            "source_voltage_v": v_src[pid],
            "currents": {p: complex(responses[p].current_a) for p in port_ids},
        }
        sh = _power_shares(sweep, solved)
        total = sh["phantom"] + sh["conductor"] + sh["sheet_total"]
        shares[pid] = sh
        residuals[pid] = abs(sh["supplied"] - total) / abs(sh["supplied"])
        single_losses[pid] = sh["phantom"] + sh["conductor"]

    # --- step 1b: the single-drive power-wave identity, per drive -----------
    #
    # ``P_acc,k`` is taken through the *package* on ``w = e_k`` — the same
    # ``_power_waves`` route the superposed drive uses, so ``a_k`` carries the
    # fixture's own ``z0`` normalisation and is not renormalised here — and
    # re-derived in closed form from the assembled 4×4 beside it.  The closed
    # form is what the negative control perturbs.
    s_matrix = np.asarray(result.s_matrix, dtype=np.complex128)
    single_power = {}
    for index, pid in enumerate(port_ids):
        unit = np.zeros(len(port_ids), dtype=np.complex128)
        unit[index] = 1.0
        drive_k = superpose_drives(result, unit)

        a_k = complex(drive_k.incident_waves[index])
        column = s_matrix[:, index]
        reflected_fraction = float(np.sum(np.abs(column) ** 2))
        closed_form = 0.5 * abs(a_k) ** 2 * (1.0 - reflected_fraction)
        # Diagonal zeroed: the same column with ``S_kk`` deleted.  Written out
        # rather than differenced so the control is an independent evaluation.
        control_column = column.copy()
        control_column[index] = 0.0
        control_acc = 0.5 * abs(a_k) ** 2 * (
            1.0 - float(np.sum(np.abs(control_column) ** 2))
        )

        sh = shares[pid]
        net = float(sh["supplied"]) - float(sh["sheet_total"])
        accepted_k = float(drive_k.accepted_power_w)
        single_power[pid] = {
            "a": a_k,
            "acc": accepted_k,
            "acc_closed_form": closed_form,
            "net": net,
            "vol": float(single_losses[pid]),
            "supplied": float(sh["supplied"]),
            "sheet_total": float(sh["sheet_total"]),
            "identity_dev": abs(accepted_k - net) / abs(net),
            "vol_residual": abs(accepted_k - single_losses[pid]) / abs(accepted_k),
            "control_acc": control_acc,
            "control_miss": abs(control_acc - net) / abs(net),
            # The closed-form ceiling on the control's miss, from S alone.
            "control_ceiling": float(abs(s_matrix[index, index]) ** 2)
            / (1.0 - reflected_fraction),
            "s_kk": complex(s_matrix[index, index]),
            "reflected_fraction": reflected_fraction,
        }

    mean_single_vol_residual = float(
        np.mean([single_power[pid]["vol_residual"] for pid in port_ids])
    )

    # (iii) the drive-level identity, on the ccw (physical) drive.
    sigma_field = result.fields[port_ids[0]].sigma_field
    power = {}
    for sense in ("ccw", "cw"):
        phantom, conductor = _loss_power_w(sweep, drives[sense].e_complex, sigma_field)
        w = drives[sense].weights
        blind = float(sum(abs(w[i]) ** 2 * single_losses[pid] for i, pid in enumerate(port_ids)))
        volume = phantom + conductor
        accepted = drives[sense].accepted_power_w
        power[sense] = {
            "phantom": phantom,
            "conductor": conductor,
            "volume": volume,
            "accepted": accepted,
            "available": drives[sense].available_power_w,
            "blind": blind,
            "residual": abs(accepted - volume) / abs(accepted),
            "cross_share": abs(accepted - blind) / abs(accepted),
            "blind_miss": abs(accepted - blind) / abs(accepted),
        }

    if comm.rank == 0:
        print(
            f"\n[POST-6 step1] package multi-port drive on the 4-leg fixture: "
            f"{sweep['cells']} cells, f = {sweep['problem'].frequency_hz:.3e} Hz, "
            f"degree 1, z0 = {drives['ccw'].z0_ohm:.3e} Ohm; port slots "
            + ", ".join(f"{pid} k={slots[pid]}" for pid in port_ids)
            + f"; mirror plane at {azimuths['P1']:.3f} deg\n"
            f"    (i) identities through ports.superpose_drives on "
            f"{int(mask_pkg.sum())} of {points.shape[0]} phantom centroids "
            f"(band {C4_COVARIANCE_BAND * 100:.1f}%, records at rtol "
            f"{CG1_RECORD_RTOL:.0e}):",
            flush=True,
        )
        for label, value in package_identities.items():
            record = STEP2_IDENTITY_RECORDS.get(label, STEP2_CONTROL_MISMATCH)
            print(
                f"        {label:<44} package {value * 100:9.4f}%   record "
                f"{record * 100:9.4f}%   rel dev {abs(value - record) / record:.3e}   "
                f"fixture-DG0 path {fixture_identities[label] * 100:9.4f}%  "
                f"(path delta {abs(value - fixture_identities[label]) / fixture_identities[label]:.3e})",
                flush=True,
            )
        print(
            "    (iv) single-drive power residuals vs step 1's "
            f"{STEP1_GATE_I_P1_RESIDUAL:.6e} (rtol {CG1_RECORD_RTOL:.0e}, band "
            f"{POWER_BALANCE_BAND:.0e}): "
            + ", ".join(f"{pid} {residuals[pid]:.6e}" for pid in port_ids),
            flush=True,
        )
        for sense in ("ccw", "cw"):
            p = power[sense]
            print(
                f"    (iii) drive-level power, {sense} quadrature: P_acc = "
                f"1/2 a^H(I - S^H S)a = {p['accepted']:.9e} W  (available "
                f"{p['available']:.9e} W)\n"
                f"        volume 1/2 int sigma|E_w|^2  = {p['volume']:.9e} W "
                f"(phantom {p['phantom']:.9e}, conductor {p['conductor']:.9e})\n"
                f"        residual |P_acc - P_vol|/P_acc = {p['residual']:.6e}  "
                f"ASSERTED <= {POWER_BALANCE_BAND:.0e}; against the item's "
                f"{PRINTED_POWER_TARGET:.0e} it is "
                f"{p['residual'] / PRINTED_POWER_TARGET:.2f}x (printed, not asserted)\n"
                f"        blind sum sum_k |w_k|^2 P_k = {p['blind']:.9e} W, "
                f"cross-term share {p['cross_share'] * 100:.4f}% "
                f"(trigger {CROSS_TERM_TRIGGER * 100:.1f}%)",
                flush=True,
            )
        print(
            "    (1b) the power-wave identity per single drive: P_acc,k = "
            "1/2|a_k|^2(1 - sum_i|S_ik|^2) vs P_net,k = supplied_k - sum_i "
            f"sheets_ik  (ASSERTED rel <= {STEP1B_POWER_WAVE_RTOL:.0e})",
            flush=True,
        )
        for pid in port_ids:
            q = single_power[pid]
            print(
                f"        {pid}  P_acc {q['acc']:.9e} W   P_net {q['net']:.9e} W"
                f"   rel dev {q['identity_dev']:.3e}\n"
                f"            supplied {q['supplied']:.9e} W, sheets "
                f"{q['sheet_total']:.9e} W, |a_k| {abs(q['a']):.9e}, "
                f"sum_i|S_ik|^2 {q['reflected_fraction']:.9f}, |S_kk| "
                f"{abs(q['s_kk']):.9f}\n"
                f"            P_vol,k = 1/2 int sigma|E_k|^2 = {q['vol']:.9e} W"
                f"   residual |P_acc-P_vol|/P_acc = {q['vol_residual']:.6e} "
                "(PRINTED, not asserted)\n"
                f"            negative control (S diagonal zeroed): P_acc,k -> "
                f"{q['control_acc']:.9e} W, miss {q['control_miss']:.6e}; "
                f"closed-form ceiling |S_kk|^2/(1-sum_i|S_ik|^2) = "
                f"{q['control_ceiling']:.6e}; floor asserted "
                f"{STEP1B_CONTROL_MIN_MISS:.0e}",
                flush=True,
            )
        print(
            f"        mean single-drive |P_acc-P_vol|/P_acc = "
            f"{mean_single_vol_residual:.6e}; superposed (ccw) "
            f"{power['ccw']['residual']:.6e}; ratio superposed/mean = "
            f"{power['ccw']['residual'] / mean_single_vol_residual:.4f} "
            "(PRINTED, not asserted — the denominator question the 03:00 "
            "review posed)",
            flush=True,
        )

    return {
        "sweep": sweep,
        "result": result,
        "port_ids": port_ids,
        "slots": slots,
        "weights": weights,
        "drives": drives,
        "package_identities": package_identities,
        "fixture_identities": fixture_identities,
        "n_valid": int(mask_pkg.sum()),
        "n_points": int(points.shape[0]),
        "all_valid": bool(np.all(mask_pkg) and np.all(mask_fix)),
        "residuals": residuals,
        "shares": shares,
        "power": power,
        "single_power": single_power,
        "mean_single_vol_residual": mean_single_vol_residual,
    }


@complex_only
def test_the_sweep_kept_one_field_per_drive_on_one_space(superposition_case):
    """Structural: what the anchors need in order to mean anything.

    Four solved phasors, one function space, ``is_placeholder=False``, and a
    sample set that evaluates everywhere — a missed point would silently drop
    out of every ℓ² below.
    """
    result = superposition_case["result"]
    assert not result.is_placeholder
    assert result.fields is not None, "keep_fields=True returned no fields"
    assert set(result.fields) == set(superposition_case["port_ids"])

    # Each solve builds its own ``functionspace`` *object*; what has to be
    # shared is the mesh and the element, which is what makes the four solves
    # four right-hand sides of one operator.
    spaces = [
        result.fields[pid].e_complex.function_space
        for pid in superposition_case["port_ids"]
    ]
    same = {
        (id(s.mesh), str(s.ufl_element()), s.dofmap.index_map.size_local) for s in spaces
    }
    assert len(same) == 1, (
        "the four drives do not share one function space, so they are not four "
        "right-hand sides of one operator and their superposition is not a drive"
    )
    assert superposition_case["all_valid"], (
        f"only {superposition_case['n_valid']} of {superposition_case['n_points']} "
        "sample points evaluated in every sense on every image set"
    )
    assert sorted(superposition_case["slots"].values()) == [0, 1, 2, 3], (
        f"the four sheets do not occupy the four quadrature slots: "
        f"{superposition_case['slots']}"
    )


@complex_only
def test_a_unit_weight_vector_returns_that_drives_own_field(superposition_case):
    """**(ii)** ``w = e_k`` is the identity on drive k — array for array.

    No interpolation, no projection, no rescaling: the entry point's arithmetic
    on a unit vector must be exactly the stored solve, or every weighted sum
    above it carries a silent transformation.
    """
    result = superposition_case["result"]
    for index, pid in enumerate(superposition_case["port_ids"]):
        weights = np.zeros(len(superposition_case["port_ids"]), dtype=np.complex128)
        weights[index] = 1.0
        single = superpose_drives(result, weights)
        assert np.array_equal(
            np.asarray(single.e_complex.x.array),
            np.asarray(result.fields[pid].e_complex.x.array),
        ), (
            f"superpose_drives with w = e_{index} does not return drive '{pid}' "
            "bit for bit"
        )
        for other in superposition_case["port_ids"]:
            expected = complex(result.excitation_results[pid].responses[other].current_a)
            assert single.currents[other] == pytest.approx(expected, rel=1.0e-12), (
                f"the unit-weight drive's current at '{other}' is "
                f"{single.currents[other]:.9e}, not drive '{pid}''s {expected:.9e}"
            )


@complex_only
def test_the_drive_is_linear_in_its_weight_vector(superposition_case):
    """**(ii)** ``S(w₁) + S(w₂) = S(w₁ + w₂)`` on the field and the terminals.

    The non-tautological half of linearity: the two ways of reaching the same
    drive must land on the same field to round-off.  ``w₁`` and ``w₂`` are the
    two quadrature senses, whose sum is a *linear* (non-rotating) drive.
    """
    result = superposition_case["result"]
    w_ccw = superposition_case["weights"]["ccw"]
    w_cw = superposition_case["weights"]["cw"]

    combined = superpose_drives(result, w_ccw + w_cw)
    summed = np.asarray(
        superposition_case["drives"]["ccw"].e_complex.x.array
    ) + np.asarray(superposition_case["drives"]["cw"].e_complex.x.array)
    reference = np.linalg.norm(summed)
    deviation = float(
        np.linalg.norm(np.asarray(combined.e_complex.x.array) - summed) / reference
    )
    assert deviation <= PATH_AGREEMENT_MAX, (
        f"superpose_drives(w1 + w2) differs from its own w1 and w2 drives summed "
        f"by {deviation:.3e} relative — the entry point is not linear in the "
        "weight vector"
    )

    for pid in superposition_case["port_ids"]:
        expected_v = (
            superposition_case["drives"]["ccw"].voltages[pid]
            + superposition_case["drives"]["cw"].voltages[pid]
        )
        expected_i = (
            superposition_case["drives"]["ccw"].currents[pid]
            + superposition_case["drives"]["cw"].currents[pid]
        )
        assert combined.voltages[pid] == pytest.approx(expected_v, rel=1.0e-12)
        assert combined.currents[pid] == pytest.approx(expected_i, rel=1.0e-12)


@complex_only
def test_the_combined_terminals_are_the_weighted_sums_of_the_single_drives(
    superposition_case,
):
    """**(ii)** the combined ``V`` and ``I`` against the sums, read independently.

    ``V_i = V_src,i − I_i Z_p,i`` looks affine but is not: ``V_src,i`` in solve
    ``k`` is ``δ_ik V_src``, itself linear in the drive vector.  Recomputed here
    straight off ``excitation_results`` — the check that bites is the *pairing*
    of weight ``k`` with column ``k``, which a transposed loop would break.
    """
    result = superposition_case["result"]
    port_ids = superposition_case["port_ids"]
    for sense, drive in superposition_case["drives"].items():
        w = superposition_case["weights"][sense]
        for pid in port_ids:
            v = sum(
                w[k] * complex(result.excitation_results[driven].responses[pid].voltage_v)
                for k, driven in enumerate(port_ids)
            )
            i = sum(
                w[k] * complex(result.excitation_results[driven].responses[pid].current_a)
                for k, driven in enumerate(port_ids)
            )
            assert drive.voltages[pid] == pytest.approx(v, rel=1.0e-12), (
                f"[{sense}] combined V at '{pid}' is {drive.voltages[pid]:.9e}, not "
                f"the weighted sum {v:.9e}"
            )
            assert drive.currents[pid] == pytest.approx(i, rel=1.0e-12), (
                f"[{sense}] combined I at '{pid}' is {drive.currents[pid]:.9e}, not "
                f"the weighted sum {i:.9e}"
            )

        mapping = {pid: w[k] for k, pid in enumerate(port_ids)}
        by_name = superpose_drives(result, mapping)
        assert np.array_equal(
            np.asarray(by_name.e_complex.x.array),
            np.asarray(drive.e_complex.x.array),
        ), f"[{sense}] the mapping and sequence spellings of the weights disagree"


@complex_only
def test_the_package_path_and_the_fixture_dg0_path_agree(superposition_case):
    """**(i)**, the strong form: two superposition paths, one set of solves.

    The package superposes ``E`` on N1curl and takes the curl; `WF-6` step 2's
    fixture takes the curl of each drive and superposes the DG0 ``B``.  Both are
    linear in the same stored fields, so the identity readings must agree to
    round-off.  This is the assertion the item's "rtol 1e-6" was reaching for,
    made six orders tighter — and unlike a comparison against a 4-digit log
    literal, it is a comparison that can be made at that precision at all.
    """
    for label, package in superposition_case["package_identities"].items():
        fixture = superposition_case["fixture_identities"][label]
        deviation = abs(package - fixture) / fixture
        assert deviation <= PATH_AGREEMENT_MAX, (
            f"{label}: the package path reads {package * 100:.6f}% and the "
            f"fixture's DG0 path {fixture * 100:.6f}% on the *same* four solves, "
            f"{deviation:.3e} apart — one of the two superpositions is wrong; "
            "this is a package/test divergence, not a tolerance question"
        )


@complex_only
def test_the_quadrature_identities_reproduce_step_2s_records(superposition_case):
    """**(i)** the digits: C4 0.9818%, mirror 0.8087%, control 95.1975%.

    The records are imported from `WF-6` step 2 and never restated here.  The
    band ``C4_COVARIANCE_BAND`` is asserted alongside them so this module fails
    the same way step 2 would if the superposition itself went wrong, and the
    cw-sense control must still miss it — a package path that could not tell the
    two rotation senses apart would pass (a) and (b) on a degeneracy.
    """
    identities = superposition_case["package_identities"]
    for label, record in STEP2_IDENTITY_RECORDS.items():
        reading = identities[label]
        assert reading <= C4_COVARIANCE_BAND, (
            f"{label} reads {reading * 100:.4f}% through ports.superpose_drives, "
            f"outside the {C4_COVARIANCE_BAND * 100:.1f}% imported band"
        )
        assert reading == pytest.approx(record, rel=CG1_RECORD_RTOL), (
            f"{label} reads {reading * 100:.6f}% through the package, not `WF-6` "
            f"step 2's recorded {record * 100:.4f}% — the package drive is not "
            "the drive step 2 measured"
        )

    control = identities["control |B1+|_cw(Mx) vs |B1+|_ccw(x)"]
    assert control > C4_COVARIANCE_BAND, (
        f"the cw-sense control reads {control * 100:.4f}%, inside the band — the "
        "package path is not resolving the two rotation senses"
    )
    assert control == pytest.approx(STEP2_CONTROL_MISMATCH, rel=CG1_RECORD_RTOL), (
        f"the control reads {control * 100:.6f}%, not step 2's "
        f"{STEP2_CONTROL_MISMATCH * 100:.4f}%"
    )


@complex_only
def test_the_single_drive_power_residuals_reproduce_step_1(superposition_case):
    """**(iv)** all four drives close their accounting on step 1's digits.

    Step 1 published P1 (9.795751e-03) and printed P2; the other two are read
    here for the first time and asserted against the same record — on a C4
    fixture the four are the same measurement four times over.
    """
    for pid, residual in superposition_case["residuals"].items():
        assert residual <= POWER_BALANCE_BAND, (
            f"[{pid}] the single-drive power accounting misses by {residual:.6e}, "
            f"outside the imported {POWER_BALANCE_BAND:.0e} band"
        )
        assert residual == pytest.approx(
            STEP1_GATE_I_P1_RESIDUAL, rel=CG1_RECORD_RTOL
        ), (
            f"[{pid}] the residual reads {residual:.9e}, not step 1's "
            f"{STEP1_GATE_I_P1_RESIDUAL:.6e} — these are not the solves the "
            "records were made on"
        )


@complex_only
def test_the_drive_level_power_identity_closes(superposition_case):
    """**(iii)** ``½aᴴ(I − SᴴS)a`` equals the superposed field's volume loss.

    The first *drive-level* power statement in this repo: the accepted power of
    a four-port drive, computed from the terminal network alone, against the
    ``½∫σ|E_w|²`` of the field that drive actually produces.  Band: the imported
    ``POWER_BALANCE_BAND`` — the single-drive accounting on this fixture reads
    9.795751e-03 against it, so a superposed identity cannot be held to the
    item's 1e-3 without holding the fixture to something it never met.  The 1e-3
    is printed in the fixture's summary and asserted nowhere.
    """
    for sense in ("ccw", "cw"):
        p = superposition_case["power"][sense]
        assert p["accepted"] > 0.0, (
            f"[{sense}] the drive accepts {p['accepted']:.9e} W — a passive "
            "structure cannot deliver power back through every port at once"
        )
        assert p["residual"] <= POWER_BALANCE_BAND, (
            f"[{sense}] the drive-level power identity misses by {p['residual']:.6e}: "
            f"P_acc = {p['accepted']:.9e} W from the S-matrix against "
            f"{p['volume']:.9e} W of volume loss (phantom {p['phantom']:.9e}, "
            f"conductor {p['conductor']:.9e}); band {POWER_BALANCE_BAND:.0e}. This "
            "is an accounting defect in the superposition, not a band to widen"
        )

        # Negative control, pre-registered: the blind sum drops every cross term
        # between drives.  It is only *asserted* to miss when those cross terms
        # are worth something — on a drive where they are not, a miss would be
        # asserting the fixture's coupling rather than the identity.
        if p["cross_share"] > CROSS_TERM_TRIGGER:
            assert p["blind_miss"] >= BLIND_SUM_MIN_MISS, (
                f"[{sense}] the cross-term-blind sum {p['blind']:.9e} W misses "
                f"P_acc by only {p['blind_miss']:.6e} although the cross terms "
                f"are worth {p['cross_share'] * 100:.4f}% — the identity is then "
                "insensitive to the interference it exists to account for"
            )


@complex_only
def test_the_single_drive_power_wave_identity_closes(superposition_case):
    """**(1b-i)** ``½|a_k|²(1 − Σ_i|S_ik|²) = supplied_k − Σ_i sheets_ik``.

    Both sides are built from the *same* stored terminal readings: ``a_k`` and
    the S-column come from ``_power_waves`` on drive k's own ``V``/``I``, and
    the accounting side is ``½Re(V_src I*)`` less ``½|I_i|²Re Z_p`` on all four
    sheets.  At ``z0 = Re Z_p`` these are algebraically one quantity, so the
    only thing 1e-6 can catch is the assembly disagreeing with its own
    definition — which is exactly the question `POST-6` step 1's 11.6% raised.

    The closed form is checked against the package's ``accepted_power_w`` first,
    so a failure below cannot be blamed on the test's own arithmetic.
    """
    for pid, q in superposition_case["single_power"].items():
        assert q["acc"] == pytest.approx(q["acc_closed_form"], rel=1.0e-12), (
            f"[{pid}] the package's accepted power {q['acc']:.9e} W and the "
            f"closed form ½|a_k|²(1 − Σ|S_ik|²) = {q['acc_closed_form']:.9e} W "
            "disagree — the test's own arithmetic is not the package's"
        )
        assert q["net"] > 0.0, (
            f"[{pid}] supplied − sheets is {q['net']:.9e} W — the drive is not "
            "delivering power into the structure at all"
        )
        assert q["identity_dev"] <= STEP1B_POWER_WAVE_RTOL, (
            f"[{pid}] the power-wave identity misses by {q['identity_dev']:.6e}: "
            f"P_acc = {q['acc']:.9e} W from the S-column against "
            f"P_net = supplied {q['supplied']:.9e} − sheets "
            f"{q['sheet_total']:.9e} = {q['net']:.9e} W, band "
            f"{STEP1B_POWER_WAVE_RTOL:.0e}. The S-matrix's power-wave "
            "normalisation and the sheet accounting disagree; this is a "
            "finding about the assembly, not a band to widen"
        )


@complex_only
def test_the_superposed_accepted_power_reproduces_step_1(superposition_case):
    """**(1b-ii)** the ccw drive's ``P_acc`` is still 3.014424803e-03 W.

    A regression pin, not a measurement: the same four solves through the same
    path must return the same watt, so the printed single-drive numbers beside
    it are read on the run step 1's 11.6% was read on.  rtol 1e-9 is the
    9-significant-digit precision the record was stored at.
    """
    accepted = superposition_case["power"]["ccw"]["accepted"]
    assert accepted == pytest.approx(
        STEP1_SUPERPOSED_ACCEPTED_W, rel=STEP1B_ACCEPTED_RTOL
    ), (
        f"the ccw drive accepts {accepted:.9e} W, not step 1's "
        f"{STEP1_SUPERPOSED_ACCEPTED_W:.9e} W — these are not the solves the "
        "11.6% residual was measured on, and the single-drive numbers printed "
        "beside it do not speak to it"
    )


@complex_only
def test_zeroing_the_reflection_diagonal_breaks_the_power_wave_identity(
    superposition_case,
):
    """Negative control for (1b-i), ceiling computed before the assertion.

    Deleting ``S_kk`` from drive k's column removes the port's own reflection
    from the accepted power, so ``P_acc,k`` grows by exactly
    ``½|a_k|²|S_kk|²`` — a miss of ``|S_kk|²/(1 − Σ_i|S_ik|²)`` against
    ``P_net,k``.  That ceiling is computed from the assembled 4×4 in the
    fixture and printed; here it is asserted *as the prediction* (the control's
    measured miss must equal it, which is only true if (1b-i) itself holds) and
    the floor claimed is ``STEP1B_CONTROL_MIN_MISS``, 1000× the band.  Nothing
    larger is claimed than the number S itself produces.
    """
    for pid, q in superposition_case["single_power"].items():
        ceiling = q["control_ceiling"]
        assert ceiling >= STEP1B_CONTROL_MIN_MISS, (
            f"[{pid}] the control's own closed-form miss is {ceiling:.6e}, "
            f"below the {STEP1B_CONTROL_MIN_MISS:.0e} floor this test claims — "
            "the control cannot separate anything on this fixture and the "
            "floor, not the control, is what is wrong"
        )
        assert q["control_miss"] >= STEP1B_CONTROL_MIN_MISS, (
            f"[{pid}] zeroing S_kk = {abs(q['s_kk']):.6f} moves P_acc,k to "
            f"{q['control_acc']:.9e} W, only {q['control_miss']:.6e} from "
            f"P_net = {q['net']:.9e} W — the identity does not see the port's "
            "own reflection, so passing it says nothing"
        )
        assert q["control_miss"] == pytest.approx(
            ceiling, rel=2.0 * STEP1B_POWER_WAVE_RTOL
        ), (
            f"[{pid}] the control misses by {q['control_miss']:.9e} but S alone "
            f"predicts |S_kk|²/(1 − Σ|S_ik|²) = {ceiling:.9e}; the perturbation "
            "is not the one this control claims to make"
        )
