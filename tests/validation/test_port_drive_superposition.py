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

* **(iii) the drive-level power identity — re-pointed by `PORT-16` step 2.**
  The terminal form ``|P_acc − P_vol|/P_acc ≤ POWER_BALANCE_BAND`` was a
  deliberate red at 11.648% (ccw).  `PORT-16` step 1 attributed that residual:
  it is the sheets' Cauchy–Schwarz deficit — ~0.98% of *supplied* power on every
  single drive — read against ``P_acc``, a ~13× smaller denominator.  The
  2026-09-06 weekly review ruled the drive-level use of the band **retired, not
  widened**, and what is asserted here now, on the same superposed field, is the
  pair step 1 proved on the singles: **(i)** the exact discrete identity
  ``P_src,exact(w) = P_vol(w) + P_sheet,exact(w)`` at the imported
  ``DISCRETE_IDENTITY_RTOL`` (1e-6), and **(ii)** the attribution
  ``P_acc(w) − P_vol(w) = C(w) − sheets_terminal(w)`` at the imported
  ``ATTRIBUTION_RTOL`` (1e-1).  The 11.648% and the item's 1e-3 are **printed**
  beside ``POWER_BALANCE_BAND`` as records and asserted nowhere on the
  superposed drives; the band keeps its value and its single-drive asserts
  ((iv) below) untouched.  The generalisation of step 1's helpers to a weight
  vector is itself gated at ``w = e_k`` to 1e-12.  The **blind sum**
  ``Σ_k |w_k|²P_k`` — the same accounting with the cross terms dropped — is
  printed beside it, and asserted to miss only when the in-run cross-term share
  exceeds 10× the band.

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

``POWER_BALANCE_BAND`` was **not** re-pointed by step 1b — the §7 disposition
rule named the next review as the actor, on these printed numbers.  That review
ran on 2026-09-06 and ruled (see (iii) above): the band's *drive-level* use is
retired, its value and its single-drive asserts stand unchanged, and nothing
here or anywhere else widens it.

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

import os
import resource
import time
from dataclasses import replace

import numpy as np
import pytest
from mpi4py import MPI

from fem_em_solver.ports import run_n_port_sparameter_sweep, superpose_drives
from fem_em_solver.ports.definitions import PortDefinition
from fem_em_solver.post import magnetic_flux_density_from_e, mean_sar, project_to_cg1

from tests.complex_mode import complex_only
from tests.mesh.test_birdcage_port_sheets import SHEET_IFACE
from tests.validation.test_birdcage_b1_plus_map import (  # noqa: F401 — imported bands/helpers
    CG1_RECORD_RTOL,
    C4_COVARIANCE_BAND,
    MIN_SAMPLE_POINTS,
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
from tests.validation.test_port_birdcage_four_port import (
    REFERENCE_IMPEDANCE_OHM,
    TERMINATED_PORT_IMPEDANCE_OHM,
    build_four_port_sweep,
)
from tests.validation.test_port_birdcage_lumped_column import (
    CONDUCTOR_CELL_TAG,
    PHANTOM_CELL_TAG,
)

# The item's pre-stated power figure.  **Printed, never asserted**: it is below
# this fixture's own single-drive accounting floor (9.795751e-03), so asserting
# it would be asserting that the superposed accounting beats the single-drive
# one.  Since `PORT-16` step 2 *neither* it nor ``POWER_BALANCE_BAND`` is
# asserted on the superposed drives — both are printed beside the terminal
# residual as records, and the assertions there are the exact identity and its
# attribution.
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


def _step1():
    """`PORT-16` step 1's module, imported **lazily and read-only**.

    A module-level import would be a cycle:
    ``test_birdcage_power_identity`` imports :func:`_loss_power_w` from *this*
    module (its line 162), and pytest collects it first (alphabetical), so a
    top-level ``from tests.validation.test_birdcage_power_identity import ...``
    here would resolve against a half-initialised module and fail on collection
    order rather than on physics.  Deferring the import to call time removes the
    order dependence without touching the step-1 module at all — no helper
    signature in it changes, and nothing here writes to it.
    """
    from tests.validation import test_birdcage_power_identity as step1

    return step1


def _exact_shares_w(sweep, e_w, w_by_pid, omega, *, step1):
    """Step 1's exact accounting, generalised to a **weight vector** by linearity.

    The superposed drive ``E_w = Σ_k w_k E_k`` is the Galerkin solution of
    ``a(E_w, v) = Σ_s w_s L_s(v)`` — the four solves share one operator, so the
    weighted sum of the right-hand sides is the right-hand side of the weighted
    sum.  Sheet ``s`` of that drive therefore carries the impressed source
    ``w_s V_src``, which is spelled here as ``replace(spec.sheet(driven=True),
    source_voltage_v=w_s·V_src)`` — the *same* frozen ``LumpedPortSheet`` step 1
    builds, with the one field the weights touch scaled.  Consequences:

    * ``P_sheet,exact(w) = Σ_s ½Re(Y_s)∫|n̂×E_w|²`` — the sheet **bilinear** term
      does not read ``source_voltage_v`` at all, so this is step 1's helper on
      the superposed field, unweighted.
    * ``C(w) = Σ_s ½Re(Y_s)∫|E_t,w + w_s E_src,s ĥ|²`` — the Cauchy–Schwarz
      ceiling, which *does* read it.
    * ``P_src,exact(w) = Im(Σ_s w_s L_s(E_w))/(2ωμ₀) = Σ_s Im(w_s L_s(E_w))/(2ωμ₀)``.
      ``Im`` is additive, and ``L_s`` is **linear** in ``source_voltage_v``, so
      the weighted source functional is the plain sum of step 1's
      ``_source_power_w`` over the *scaled* sheets.  No new primitive, no
      signature change, and no hand-written form: the trap the step-1 window 1
      log recorded (a transcribed sign, ``rel dev`` exactly 2.000e+00) cannot
      recur because the sign is never re-transcribed here.

    ``w = e_k`` collapses every line above to step 1's own single-drive call,
    which is what
    :func:`test_the_unit_weight_generalisation_reproduces_step_1s_exact_shares`
    asserts at 1e-12.
    """
    specs = {spec.port_id: spec for spec in sweep["specs"]}
    sheets = {
        pid: replace(
            specs[pid].sheet(driven=True),
            source_voltage_v=complex(w_by_pid[pid]) * complex(specs[pid].drive_voltage_v),
        )
        for pid in w_by_pid
    }
    field = {
        pid: step1._sheet_field_dissipation_w(sweep, sheet, e_w, omega)
        for pid, sheet in sheets.items()
    }
    ceiling = {
        pid: step1._sheet_total_field_dissipation_w(sweep, sheet, e_w)
        for pid, sheet in sheets.items()
    }
    p_src = float(
        sum(step1._source_power_w(sweep, sheet, e_w, omega) for sheet in sheets.values())
    )
    return {
        "sheet_field": field,
        "sheet_ceiling": ceiling,
        "sheet_field_total": float(sum(field.values())),
        "sheet_ceiling_total": float(sum(ceiling.values())),
        "p_src": p_src,
    }


# The `w = e_k` control on the generalisation above.  The superposed field at a
# unit weight vector is drive k's own array bit for bit (asserted separately in
# ``test_a_unit_weight_vector_returns_that_drives_own_field``) and the scaled
# sheets are then literally ``spec.sheet(driven=(pid == k))``, so the two paths
# assemble identical forms — 1e-12 is the bound, bit-for-bit the expectation.
UNIT_WEIGHT_CONTROL_RTOL = 1.0e-12


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
    step1 = _step1()
    s_matrix = np.asarray(result.s_matrix, dtype=np.complex128)
    single_power = {}
    unit_weight_control = {}
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

        # --- `PORT-16` step 2, the control of the generalisation ------------
        # ``w = e_k`` through the weighted path vs step 1's own single-drive
        # call on the *same* stored solve.
        unit_by_pid = {p: (1.0 + 0.0j if p == pid else 0.0j) for p in port_ids}
        generalised = _exact_shares_w(
            sweep, drive_k.e_complex, unit_by_pid, omega, step1=step1
        )
        reference = step1._exact_shares(
            sweep,
            {"omega": omega, "fields": result.fields[pid], "driven": pid},
        )
        unit_weight_control[pid] = {
            key: (float(generalised[key]), float(reference[key]))
            for key in ("p_src", "sheet_field_total", "sheet_ceiling_total")
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

    # --- `PORT-16` step 2: the exact identity and its attribution, on the
    # superposed drive itself.  Ruling (2) of the 2026-09-06 weekly review
    # retired the *terminal* form of (iii) here — it read the fixture's own
    # ~1%-of-supplied Cauchy-Schwarz deficit against a 13x smaller denominator,
    # so it measured the denominator.  What replaces it are the two statements
    # step 1 proved on the single drives, re-asked of the superposed field.
    exact_w = {}
    for sense in ("ccw", "cw"):
        drive = drives[sense]
        w_by_pid = {pid: complex(drive.weights[i]) for i, pid in enumerate(port_ids)}
        ex = _exact_shares_w(sweep, drive.e_complex, w_by_pid, omega, step1=step1)
        p_vol = float(power[sense]["volume"])
        sheets_terminal = float(
            sum(
                step1._terminal_sheet_powers(
                    {"currents": drive.currents}, TERMINATED_PORT_IMPEDANCE_OHM
                ).values()
            )
        )
        accepted = float(power[sense]["accepted"])
        attribution_lhs = accepted - p_vol
        attribution_rhs = ex["sheet_ceiling_total"] - sheets_terminal
        ex.update(
            p_vol=p_vol,
            sheets_terminal=sheets_terminal,
            accepted=accepted,
            identity_dev=abs(ex["p_src"] - p_vol - ex["sheet_field_total"])
            / abs(ex["p_src"]),
            attribution_lhs=attribution_lhs,
            attribution_rhs=attribution_rhs,
            attribution_dev=abs(attribution_lhs - attribution_rhs)
            / abs(attribution_lhs),
        )
        exact_w[sense] = ex

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
                f"(PRINTED, ASSERTED NOWHERE since `PORT-16` step 2; the "
                f"terminal form's Cauchy-Schwarz deficit against a "
                f"drive-dependent denominator, cf. POWER_BALANCE_BAND "
                f"{POWER_BALANCE_BAND:.0e} which keeps its single-drive "
                f"asserts); against the item's {PRINTED_POWER_TARGET:.0e} it is "
                f"{p['residual'] / PRINTED_POWER_TARGET:.2f}x\n"
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
        print(
            "    [PORT-16 step2] (i) the exact discrete power identity on the "
            "*superposed* drive: P_src,exact(w) = P_vol(w) + P_sheet,exact(w) "
            f"(ASSERTED rel <= {step1.DISCRETE_IDENTITY_RTOL:g})",
            flush=True,
        )
        for sense in ("ccw", "cw"):
            ex = exact_w[sense]
            print(
                f"        {sense}  P_src,exact {ex['p_src']:.9e} W   "
                f"P_vol {ex['p_vol']:.9e} W   "
                f"P_sheet,exact {ex['sheet_field_total']:.9e} W   "
                f"rel dev {ex['identity_dev']:.3e}",
                flush=True,
            )
        print(
            "    [PORT-16 step2] (ii) the attribution: P_acc(w) - P_vol(w) = "
            "C(w) - sheets_terminal(w), C = sum_s 1/2 Re(Y_s) int "
            "|E_t,w + w_s E_src,s h|^2 dA "
            f"(ASSERTED rel <= {step1.ATTRIBUTION_RTOL:g})",
            flush=True,
        )
        for sense in ("ccw", "cw"):
            ex = exact_w[sense]
            print(
                f"        {sense}  P_acc {ex['accepted']:.9e} W   "
                f"P_vol {ex['p_vol']:.9e} W   "
                f"P_acc - P_vol {ex['attribution_lhs']:.9e} W   "
                f"C {ex['sheet_ceiling_total']:.9e} W   "
                f"sheets_terminal {ex['sheets_terminal']:.9e} W   "
                f"C - sheets_terminal {ex['attribution_rhs']:.9e} W   "
                f"rel dev {ex['attribution_dev']:.3e}",
                flush=True,
            )
        print(
            "    [PORT-16 step2] control of the generalisation: w = e_k vs "
            "step 1's own single-drive `_exact_shares` (ASSERTED rel <= "
            f"{UNIT_WEIGHT_CONTROL_RTOL:g})",
            flush=True,
        )
        for pid in port_ids:
            fields = unit_weight_control[pid]
            print(
                f"        {pid}  "
                + "   ".join(
                    f"{key} {gen:.9e} vs {ref:.9e} (rel dev "
                    f"{abs(gen - ref) / abs(ref):.3e})"
                    for key, (gen, ref) in fields.items()
                ),
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
        "exact_w": exact_w,
        "unit_weight_control": unit_weight_control,
        "discrete_identity_rtol": float(step1.DISCRETE_IDENTITY_RTOL),
        "attribution_rtol": float(step1.ATTRIBUTION_RTOL),
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
    """**(iii)**, re-pointed by `PORT-16` step 2 at the *exact* discrete identity.

    What this used to assert was the **terminal** form
    ``|P_acc − P_vol|/P_acc ≤ POWER_BALANCE_BAND``, a deliberate red at 11.648%
    (ccw, `20260905T004202Z_POST-6.log:1915–1917`).  `PORT-16` step 1 then
    measured what that 11.6% is: the fixture's terminal sheet power
    ``½|I|²Re Z_p`` is the *uniform-field lower bound* on the dissipation the
    sheet's own constitutive law deposits, short of it by the sheets'
    Cauchy–Schwarz deficit — ~0.98% of supplied power on every single drive,
    reproduced to 1e-13 (`20260907T051231Z_PORT-16.log:1917–1920`).  Read
    against ``P_acc``, a denominator ~13× smaller than supplied, that same
    absolute deficit is ~11.6%.  The 2026-09-06 weekly review therefore ruled
    the drive-level use of the band **retired, not widened**: an assertion that
    re-reads a known deficit against a drive-dependent denominator measures the
    denominator.  ``POWER_BALANCE_BAND`` keeps its value and its single-drive
    asserts in this module (:func:`test_the_single_drive_power_residuals_reproduce_step_1`)
    and everywhere else; the terminal residual is *printed* beside it here as a
    record and asserted nowhere on the superposed drives.

    What is asserted instead, on the same superposed field ``E_w``:

    **(i)** ``P_src,exact(w) = P_vol(w) + P_sheet,exact(w)`` at the imported
    ``DISCRETE_IDENTITY_RTOL`` (1e-6).  This is the real part of
    ``a(E_w, E_w) = L_w(E_w)`` — the weak form tested with its own solution, an
    exactness statement about the *assembly* under superposition, not a
    discretisation reading.  Step 1 measured it at 1e-14 class on the four
    single drives; if it fails here while holding there, the sheet terms do not
    superpose as written and the finding is a cross-term in the impressed field.

    **(ii)** the attribution ``P_acc(w) − P_vol(w) = C(w) − sheets_terminal(w)``
    at the imported ``ATTRIBUTION_RTOL`` (1e-1), with ``C`` the Cauchy–Schwarz
    ceiling summed over the four sheets, each carrying its own ``w_s E_src,s``.
    Unlike (i) this is not arithmetic on one side: the left is an S-matrix
    reading minus a volume integral, the right a facet integral minus a terminal
    reading.  It says the whole of the printed 11.6% is the deficit step 1
    named, on a drive none of step 1's solves is.
    """
    for sense in ("ccw", "cw"):
        p = superposition_case["power"][sense]
        ex = superposition_case["exact_w"][sense]
        assert p["accepted"] > 0.0, (
            f"[{sense}] the drive accepts {p['accepted']:.9e} W — a passive "
            "structure cannot deliver power back through every port at once"
        )
        assert ex["p_src"] > 0.0, (
            f"[{sense}] P_src,exact is {ex['p_src']:.9e} W — the weighted source "
            "functional is not delivering power into the structure"
        )
        assert ex["identity_dev"] <= superposition_case["discrete_identity_rtol"], (
            f"[{sense}] the exact discrete power identity misses by "
            f"{ex['identity_dev']:.6e} against "
            f"{superposition_case['discrete_identity_rtol']:g} — "
            f"P_src,exact {ex['p_src']:.9e} W, P_vol {ex['p_vol']:.9e} W, "
            f"P_sheet,exact {ex['sheet_field_total']:.9e} W.  It closes at 1e-14 "
            "on every single drive, so a miss here says the sheet terms do not "
            "superpose as written (a cross-term in the impressed field), not "
            "that the tolerance is wrong"
        )
        assert ex["attribution_rhs"] > 0.0, (
            f"[{sense}] the Cauchy-Schwarz deficit C - sheets_terminal is "
            f"{ex['attribution_rhs']:.9e} W — it must be positive, the terminal "
            "form is a lower bound"
        )
        assert ex["attribution_dev"] <= superposition_case["attribution_rtol"], (
            f"[{sense}] the attribution misses by {ex['attribution_dev']:.6e} "
            f"against {superposition_case['attribution_rtol']:g} — "
            f"P_acc - P_vol = {ex['attribution_lhs']:.9e} W against "
            f"C - sheets_terminal = {ex['attribution_rhs']:.9e} W "
            f"(C {ex['sheet_ceiling_total']:.9e} W, sheets_terminal "
            f"{ex['sheets_terminal']:.9e} W).  The drive-level residual is then "
            "*not* the single drives' Cauchy-Schwarz deficit and something else "
            "enters under superposition"
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
def test_the_unit_weight_generalisation_reproduces_step_1s_exact_shares(
    superposition_case,
):
    """`PORT-16` step 2's control: ``w = e_k`` is step 1's single drive.

    :func:`_exact_shares_w` generalises step 1's three exact quantities to a
    weight vector by linearity, and every conclusion drawn from it on the
    superposed drive rests on that generalisation being the identity at a unit
    weight.  Here it is asserted: ``P_src,exact``, ``P_sheet,exact`` and ``C``
    computed through the weighted path on ``superpose_drives(result, e_k)``
    against ``test_birdcage_power_identity._exact_shares`` on drive k's own
    stored solve.  Same field (asserted bit-for-bit elsewhere), same sheets,
    same package form builders — 1e-12 is a bound on an expectation of exactness,
    and a miss localises the defect in the *weighting*, not in the physics, before
    any superposed number is believed.
    """
    for pid, fields in superposition_case["unit_weight_control"].items():
        for key, (generalised, reference) in fields.items():
            assert reference != 0.0, f"[{pid}] step 1's {key} is exactly zero"
            deviation = abs(generalised - reference) / abs(reference)
            assert deviation <= UNIT_WEIGHT_CONTROL_RTOL, (
                f"[{pid}] the weighted path reads {key} = {generalised:.12e} W at "
                f"w = e_k where step 1's single-drive path reads "
                f"{reference:.12e} W, {deviation:.3e} apart against "
                f"{UNIT_WEIGHT_CONTROL_RTOL:g} — the generalisation to a weight "
                "vector is not the identity on a unit vector, so nothing it says "
                "about the superposed drive can be read"
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


# ===========================================================================
# `POST-6` step 3 — the 32-port ccw quadrature drive on `PORT-13`'s fixture
# ===========================================================================
#
# **What.**  The 16-leg / 32-ring-port high-pass rung is built by
# ``_build_ring_context`` (imported from `PORT-13` step 3's matrix module, never
# copied), all 32 drives are solved once through
# ``run_n_port_sparameter_sweep(keep_fields=True)`` under `PORT-19`'s factor-reuse
# default, and the m = 1 quadrature pattern is formed through
# ``ports.superpose_drives``.
#
# **Weights.**  One port per 22.5 deg slot on each ring, located from the
# **measured** azimuth and the measured sign of the sheet centre's ``z`` — no
# ordinal arithmetic.  The phase is ``quadrature_phase_weights`` (the single
# source of the ``e^{∓jkπ/2}`` convention) evaluated at the *fractional*
# quadrature index ``k·22.5/90``, i.e. ``e^{∓jφ_k}``.  Each ring port drives along
# its own ``φ̂``, and the m = 1 mode is odd under ``z → −z`` (uniform transverse
# ``B`` is a pseudovector), so its ring currents at one azimuth are equal and
# opposite on the two rings: the bottom-ring weights carry a ``−1``.  That sign
# does not enter (i)–(iii) — all three hold for either sign by symmetry alone —
# so it is stated, not gated.
#
# **Anchors (asserted).**  (i) C16 invariance of the CG1 ``|B₁⁺|`` map: the
# relative L2 between ``|B₁⁺|_ccw(R_m x)`` and ``|B₁⁺|_ccw(x)`` at every rotation
# m·22.5 deg, m = 1…15, the **worst** of the fifteen within the imported
# ``C4_COVARIANCE_BAND`` (5%, `WF-6`'s).  Compared at rotated **points**, never by
# facet index — the ring-sheet triangulation is two-state under the rotation
# (`GEO-26` step 3, `EX-45`).  (ii) the mirror identity ``|B₁⁻|_cw(Mx)`` vs
# ``|B₁⁺|_ccw(x)``, mirror in the plane through the reference port's azimuth,
# same band.  (iii) `PORT-16`'s exact discrete identity
# ``P_src,exact(w) = P_vol(w) + P_sheet,exact(w)`` on the superposed ccw field at
# ``DISCRETE_IDENTITY_RTOL``, through the weighted helper above.
#
# **Negative control.**  On *this* fixture the mis-paired comparison
# ``|B₁⁺|_cw(Mx)`` vs ``|B₁⁺|_ccw(x)`` has no record, so it is **predicted and
# printed, never asserted** (§9 rule (e)): the prediction is formed from the ccw
# field alone, ``|B₁⁻|_ccw(x)`` vs ``|B₁⁺|_ccw(x)``, which the mirror identity says
# the cw reading must equal.  The asserted control is the one a record backs —
# the 4-leg ``RECORDED_CW_SPREAD`` with its ``CW_SEPARATION_FACTOR``.
#
# **Selected by environment only** (``FEM_EM_POST6_STEP3=1``), never by ``-k``;
# unset, the 32-port tests skip and the 4-leg module runs as before.
#
# **Scope.**  10 MHz, degree 1, one fixture; no homogeneity, absolute or Larmor
# claim.
STEP3_ENV = "FEM_EM_POST6_STEP3"
STEP3_ORIENTATION = "ring_gap_phi_hat_plus"


def _step3_on():
    return os.environ.get(STEP3_ENV, "").strip() == "1"


def _step3_imports():
    """The ring fixture and the cw record, imported **lazily and read-only**.

    Same reason as :func:`_step1`: a module-level import of the ring modules or
    of `WF-6`'s closed-form module reaches ``test_birdcage_power_identity``,
    which imports :func:`_loss_power_w` back from this half-initialised module
    (collection error on the first step-3 run,
    ``20260913T184909Z_POST-6-step3.log:116``).
    """
    from types import SimpleNamespace

    from tests.validation import test_birdcage_b1_plus_closed_form as closed_form
    from tests.validation import test_port_birdcage_ring_matrix as ring

    return SimpleNamespace(
        AZIMUTH_MATCH_DEG=ring.AZIMUTH_MATCH_DEG,
        AZIMUTH_STEP_DEG=ring.AZIMUTH_STEP_DEG,
        CELL_COUNT_BAND=ring.CELL_COUNT_BAND,
        RING_LONGITUDINAL_SCALED_CELL_RECORD=ring.RING_LONGITUDINAL_SCALED_CELL_RECORD,
        SCALED_LEG_COUNT=ring.SCALED_LEG_COUNT,
        build_ring_context=ring._build_ring_context,
        CW_SEPARATION_FACTOR=closed_form.CW_SEPARATION_FACTOR,
        RECORDED_CW_SPREAD=closed_form.RECORDED_CW_SPREAD,
    )


def _ring_quadrature_slots(sheets):
    """``(azimuth_ref_deg, {pid: (slot k, ring sign)})`` from measured geometry.

    The reference is the lowest-ordinal **top-ring** port; ``k`` is its 22.5 deg
    slot, asserted on the grid to ``AZIMUTH_MATCH_DEG``, and each ring must fill
    all sixteen slots exactly once.
    """
    names = _step3_imports()
    SCALED_LEG_COUNT = names.SCALED_LEG_COUNT
    AZIMUTH_STEP_DEG = names.AZIMUTH_STEP_DEG
    AZIMUTH_MATCH_DEG = names.AZIMUTH_MATCH_DEG
    top = [s for s in sheets if s["z"] > 0.0]
    bottom = [s for s in sheets if s["z"] < 0.0]
    assert len(top) == len(bottom) == SCALED_LEG_COUNT, (
        f"measured {len(top)} top / {len(bottom)} bottom ring ports, not "
        f"{SCALED_LEG_COUNT} each"
    )
    az_ref = float(min(top, key=lambda s: s["ordinal"])["azimuth_deg"])
    slots = {}
    for s in sheets:
        turns = ((float(s["azimuth_deg"]) - az_ref) % 360.0) / AZIMUTH_STEP_DEG
        nearest = round(turns)
        residual_deg = abs(turns - nearest) * AZIMUTH_STEP_DEG
        assert residual_deg < AZIMUTH_MATCH_DEG, (
            f"P{s['ordinal']} at {s['azimuth_deg']:.9f} deg is {residual_deg:.3e} deg "
            f"off the {AZIMUTH_STEP_DEG} deg grid referenced at {az_ref:.9f} deg"
        )
        slots[f"P{s['ordinal']}"] = (
            int(nearest) % SCALED_LEG_COUNT,
            1.0 if s["z"] > 0.0 else -1.0,
        )
    for sign in (1.0, -1.0):
        ks = sorted(k for k, sg in slots.values() if sg == sign)
        assert ks == list(range(SCALED_LEG_COUNT)), (
            f"ring sign {sign:+.0f} fills slots {ks}, not each of 0…"
            f"{SCALED_LEG_COUNT - 1} once"
        )
    return az_ref, slots


def _build_ring_quadrature_case():
    """One 32-drive field-keeping sweep on the ring rung; both senses; CG1 reads.

    Lifted out of the ``ring_quadrature_case`` fixture below so a caller
    outside pytest collection (an example script; the `ANS-1` rule) can build
    the same case without pytest's fixture machinery. Additive only — the
    fixture is now a thin wrapper that keeps its environment-gated skip and
    calls this. No behaviour changed (`EX-55`, 2026-09-14).
    """
    names = _step3_imports()
    SCALED_LEG_COUNT = names.SCALED_LEG_COUNT
    AZIMUTH_STEP_DEG = names.AZIMUTH_STEP_DEG
    RING_LONGITUDINAL_SCALED_CELL_RECORD = names.RING_LONGITUDINAL_SCALED_CELL_RECORD
    RECORDED_CW_SPREAD = names.RECORDED_CW_SPREAD
    CW_SEPARATION_FACTOR = names.CW_SEPARATION_FACTOR
    t_start = time.perf_counter()
    built = names.build_ring_context()
    comm = built["comm"]
    ctx = built["ctx"]

    def say(msg):
        if comm.rank == 0:
            print(f"[POST-6 step3] {msg}", flush=True)

    say(
        f"built the ring rung: {built['cells']} cells (record "
        f"{RING_LONGITUDINAL_SCALED_CELL_RECORD}), {len(built['sheets'])} ring "
        f"ports, {time.perf_counter() - t_start:.2f} s at -n {comm.size}"
    )

    specs = ctx["specs"]
    port_defs = [
        PortDefinition(
            port_id=spec.port_id,
            positive_tag=int(spec.facet_tag),
            negative_tag=CONDUCTOR_CELL_TAG,
            orientation=STEP3_ORIENTATION,
            z0_ohm=REFERENCE_IMPEDANCE_OHM,
        )
        for spec in specs
    ]
    comm.Barrier()
    t0 = time.perf_counter()
    result = run_n_port_sparameter_sweep(
        ctx["solver"].problem,
        port_defs,
        lumped_sheet_ports=specs,
        lumped_sheet_facet_tags=ctx["tags_f"],
        keep_fields=True,
    )
    comm.Barrier()
    t_sweep = time.perf_counter() - t0
    port_ids = list(result.port_ids)
    say(f"32-drive sweep (PORT-19 reuse default, keep_fields) {t_sweep:.2f} s")

    az_ref, slots = _ring_quadrature_slots(built["sheets"])
    ks = np.array(
        [slots[pid][0] * AZIMUTH_STEP_DEG / QUADRATURE_STEP_DEG for pid in port_ids]
    )
    ring_sign = np.array([slots[pid][1] for pid in port_ids])
    weights = {
        sense: ring_sign * quadrature_phase_weights(ks, sense) for sense in ("ccw", "cw")
    }
    drives = {
        sense: superpose_drives(result, weights[sense], name=f"E_ring_{sense}")
        for sense in weights
    }

    sweep = {
        "mesh": ctx["msh"],
        "cell_tags": ctx["cell_tags"],
        "facet_tags": ctx["tags_f"],
        "specs": specs,
    }
    points = _sample_points(sweep)

    comm.Barrier()
    t0 = time.perf_counter()
    cg1 = {
        sense: project_to_cg1(drives[sense].b_complex, name=f"B_ring_{sense}_cg1")
        for sense in drives
    }
    comm.Barrier()
    t_proj = time.perf_counter() - t0
    say(f"two CG1 projections {t_proj:.2f} s; {points.shape[0]} sample points")

    comm.Barrier()
    t0 = time.perf_counter()
    rotations = tuple(range(1, SCALED_LEG_COUNT))
    ccw_reads = {0: _read_senses(cg1["ccw"], points)}
    for m in rotations:
        ccw_reads[m] = _read_senses(
            cg1["ccw"], _rotate_z(points, np.radians(m * AZIMUTH_STEP_DEG))
        )
    cw_plus_mx, cw_minus_mx, cw_valid = _read_senses(
        cg1["cw"], _mirror_xy(points, az_ref)
    )
    mask = np.logical_and.reduce([r[2] for r in ccw_reads.values()] + [cw_valid])
    comm.Barrier()
    t_eval = time.perf_counter() - t0

    plus_x, minus_x = ccw_reads[0][0], ccw_reads[0][1]
    c16 = {m: _relative_l2(ccw_reads[m][0], plus_x, mask) for m in rotations}
    worst_m = max(c16, key=c16.get)
    mirror = _relative_l2(cw_minus_mx, plus_x, mask)
    control = _relative_l2(cw_plus_mx, plus_x, mask)
    predicted_control = _relative_l2(minus_x, plus_x, mask)

    # (iii) the exact discrete identity on the superposed ccw field.
    comm.Barrier()
    t0 = time.perf_counter()
    omega = 2.0 * np.pi * float(result.frequency_hz)
    step1 = _step1()
    drive = drives["ccw"]
    w_by_pid = {pid: complex(drive.weights[i]) for i, pid in enumerate(port_ids)}
    ex = _exact_shares_w(sweep, drive.e_complex, w_by_pid, omega, step1=step1)
    phantom, conductor = _loss_power_w(
        sweep, drive.e_complex, result.fields[port_ids[0]].sigma_field
    )
    p_vol = float(phantom + conductor)
    identity_dev = abs(ex["p_src"] - p_vol - ex["sheet_field_total"]) / abs(ex["p_src"])
    comm.Barrier()
    t_power = time.perf_counter() - t0

    rss_gib = float(
        comm.allreduce(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, op=MPI.SUM)
    ) / (1024.0 * 1024.0)
    n_valid = int(np.count_nonzero(mask))
    worst = c16[worst_m]

    if comm.rank == 0:
        print(
            f"\n[POST-6 step3] 32-port ccw quadrature on the PORT-13 ring rung: "
            f"{built['cells']} cells, f = {result.frequency_hz:.3e} Hz, degree 1, "
            f"z0 = {drive.z0_ohm:.3e} Ohm, reference port azimuth {az_ref:.6f} deg, "
            f"{n_valid}/{points.shape[0]} sample points valid on every image",
            flush=True,
        )
        for m in rotations:
            print(
                f"[POST-6 step3]   (i) C16 R_{m:<2d} ({m * AZIMUTH_STEP_DEG:6.1f} deg) "
                f"|B1+|_ccw(Rx) vs |B1+|_ccw(x): {c16[m] * 100:.4f}%",
                flush=True,
            )
        print(
            f"[POST-6 step3] (i) worst C16 spread {worst * 100:.4f}% at R_{worst_m} "
            f"(ASSERTED <= C4_COVARIANCE_BAND {C4_COVARIANCE_BAND * 100:.1f}%)\n"
            f"[POST-6 step3] (ii) mirror |B1-|_cw(Mx) vs |B1+|_ccw(x): "
            f"{mirror * 100:.4f}% (ASSERTED <= {C4_COVARIANCE_BAND * 100:.1f}%)\n"
            f"[POST-6 step3] (iii) exact identity rel dev {identity_dev:.3e} "
            f"(ASSERTED <= DISCRETE_IDENTITY_RTOL {step1.DISCRETE_IDENTITY_RTOL:g}): "
            f"P_src,exact {ex['p_src']:.9e} W = P_vol {p_vol:.9e} W (phantom "
            f"{phantom:.9e}, conductor {conductor:.9e}) + P_sheet,exact "
            f"{ex['sheet_field_total']:.9e} W; package P_acc {drive.accepted_power_w:.9e} W "
            f"(printed, not asserted)\n"
            f"[POST-6 step3] negative control (PREDICTED, never asserted): cw "
            f"mis-paired |B1+|_cw(Mx) vs |B1+|_ccw(x) measured {control * 100:.4f}% vs "
            f"predicted {predicted_control * 100:.4f}% (|B1-|_ccw(x) vs |B1+|_ccw(x), "
            f"ccw field only); cw factor over the worst C16 spread measured "
            f"{control / worst:.2f}x vs predicted {predicted_control / worst:.2f}x "
            f"(4-leg record {RECORDED_CW_SPREAD * 100:.4f}%, bar "
            f"{CW_SEPARATION_FACTOR:.0f}x there); mean |B1+|_ccw "
            f"{float(np.mean(plus_x[mask])):.6e} T, mean |B1-|_ccw "
            f"{float(np.mean(minus_x[mask])):.6e} T\n"
            f"[POST-6 step3] PRICE: 32-drive sweep {t_sweep:.2f} s, projections "
            f"{t_proj:.2f} s, {len(ccw_reads) + 1} point evaluations {t_eval:.2f} s, "
            f"power identity {t_power:.2f} s, fixture {time.perf_counter() - t_start:.2f} s "
            f"wall at -n {comm.size}; summed ru_maxrss {rss_gib:.3f} GiB",
            flush=True,
        )

    return {
        "cells": int(built["cells"]),
        "port_ids": port_ids,
        "weights": weights,
        "ring_sign": ring_sign,
        "n_valid": n_valid,
        "c16": c16,
        "worst_m": worst_m,
        "mirror": mirror,
        "control": control,
        "predicted_control": predicted_control,
        "identity_dev": float(identity_dev),
        "identity_rtol": float(step1.DISCRETE_IDENTITY_RTOL),
        # Additive (`EX-55`): the mesh/tags/fields a caller needs to write a
        # ParaView artifact or a setup figure — no existing key touched.
        "mesh": ctx["msh"],
        "cell_tags": ctx["cell_tags"],
        "facet_tags": ctx["tags_f"],
        "drives": drives,
        "cg1": cg1,
        "frequency_hz": float(result.frequency_hz),
        "z0_ohm": float(drive.z0_ohm.real),
        "sheets": built["sheets"],
    }


@pytest.fixture(scope="module")
def ring_quadrature_case():
    if not _step3_on():
        pytest.skip(
            f"{STEP3_ENV} unset: the 32-port step-3 drive is a heavy -n 8 window "
            "selected by environment only"
        )
    return _build_ring_quadrature_case()


@complex_only
def test_step3_the_ring_drive_came_off_the_port13_fixture(ring_quadrature_case):
    """The rung is `GEO-26` step 2's record, 32 ports, and the read is populated."""
    names = _step3_imports()
    RING_LONGITUDINAL_SCALED_CELL_RECORD = names.RING_LONGITUDINAL_SCALED_CELL_RECORD
    CELL_COUNT_BAND = names.CELL_COUNT_BAND
    SCALED_LEG_COUNT = names.SCALED_LEG_COUNT
    c = ring_quadrature_case
    ratio = c["cells"] / RING_LONGITUDINAL_SCALED_CELL_RECORD
    assert abs(ratio - 1.0) < CELL_COUNT_BAND, (
        f"{c['cells']} cells against the record {RING_LONGITUDINAL_SCALED_CELL_RECORD}"
    )
    assert len(c["port_ids"]) == 2 * SCALED_LEG_COUNT
    assert c["n_valid"] >= MIN_SAMPLE_POINTS, (
        f"only {c['n_valid']} sample points are valid on every rotated/mirrored image"
    )
    for sense, w in c["weights"].items():
        assert np.allclose(np.abs(w), 1.0, rtol=0.0, atol=1e-12), sense


@complex_only
def test_step3_the_ccw_ring_drive_is_c16_invariant(ring_quadrature_case):
    """**(i)** worst of the fifteen C16 images inside the imported 5% band."""
    c = ring_quadrature_case
    worst = c["c16"][c["worst_m"]]
    assert worst <= C4_COVARIANCE_BAND, (
        f"|B1+|_ccw is not C16-invariant: R_{c['worst_m']} reads {worst * 100:.4f}% "
        f"against the imported {C4_COVARIANCE_BAND * 100:.1f}% band (§9 negative "
        "result: known-issues entry, row stays 🟡)"
    )


@complex_only
def test_step3_the_ring_drive_mirror_identity(ring_quadrature_case):
    """**(ii)** ``|B₁⁻|_cw(Mx)`` equals ``|B₁⁺|_ccw(x)`` inside the imported band."""
    c = ring_quadrature_case
    assert c["mirror"] <= C4_COVARIANCE_BAND, (
        f"the mirror identity reads {c['mirror'] * 100:.4f}% against the imported "
        f"{C4_COVARIANCE_BAND * 100:.1f}% band"
    )


@complex_only
def test_step3_the_ring_drive_power_identity_closes(ring_quadrature_case):
    """**(iii)** `PORT-16`'s exact discrete identity on the superposed ccw field."""
    c = ring_quadrature_case
    assert c["identity_dev"] <= c["identity_rtol"], (
        f"P_src,exact − P_vol − P_sheet,exact misses by {c['identity_dev']:.6e} of "
        f"P_src against DISCRETE_IDENTITY_RTOL {c['identity_rtol']:g}"
    )


@complex_only
def test_the_four_leg_cw_control_reproduces_its_record_with_its_separation(
    superposition_case,
):
    """The asserted negative control: the 4-leg cw reading a record backs.

    The mis-paired ``|B₁⁺|_cw(Mx)`` vs ``|B₁⁺|_ccw(x)`` reproduces
    ``RECORDED_CW_SPREAD`` at ``CG1_RECORD_RTOL`` and clears
    ``CW_SEPARATION_FACTOR`` × the ccw C4 reading on the same superposed drive.
    """
    names = _step3_imports()
    RECORDED_CW_SPREAD = names.RECORDED_CW_SPREAD
    CW_SEPARATION_FACTOR = names.CW_SEPARATION_FACTOR
    identities = superposition_case["package_identities"]
    control = identities["control |B1+|_cw(Mx) vs |B1+|_ccw(x)"]
    c4 =identities["(a) C4 |B1+|_ccw(Rx) vs |B1+|_ccw(x)"]
    assert control == pytest.approx(RECORDED_CW_SPREAD, rel=CG1_RECORD_RTOL), (
        f"the 4-leg cw control reads {control * 100:.6f}%, not the recorded "
        f"{RECORDED_CW_SPREAD * 100:.4f}%"
    )
    assert control >= CW_SEPARATION_FACTOR * c4, (
        f"the cw control {control * 100:.4f}% is not {CW_SEPARATION_FACTOR:.0f}x the "
        f"ccw C4 reading {c4 * 100:.4f}%"
    )
