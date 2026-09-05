"""`POST-6` step 1 — the package-level multi-port drive (HFSS *Edit Sources*).

`WF-6` step 2 built a quadrature drive once, for four ports at fixed
``e^{∓jkπ/2}``, **inside a test module**: it superposed the four DG0 ``B``
fields with a phase pattern and read ``|B₁⁺|``.  Nothing package-level took *N*
stored single-drive solves and an arbitrary complex weight vector, which is
what a tuned 32-port drive and any asymmetric drive need.  This module is that
entry point.

**Why superposition is exact here, not an approximation.**  One
:func:`~fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep` on the
lumped-sheet route solves ``A x_k = f_k`` with *one* operator ``A`` — every
port's sheet carries the same linear law ``V = V_src − I·Z_p`` in every solve,
and the only thing that changes between drives is which sheet also carries the
impressed source, i.e. the right-hand side.  A linear system with a fixed
operator and ``N`` right-hand sides superposes exactly, so the field of all
ports driven with complex amplitudes ``w_k`` **is** ``Σ_k w_k E_k``, on the
drives' own N1curl space — no interpolation, no projection, no DG0 detour.
(The DG0 sum in `WF-6` step 2's fixture is the *readout* precedent, not the
field one: it superposes the derived ``B``, which is legitimate because
``B = ∇×E/(−jω)`` is linear, but it is a post-processing convenience rather
than the drive itself.)

**What the terminal quantities are.**  ``V_i = V_src,i − I_i·Z_p,i`` is affine
in the drive only in appearance: ``V_src,i`` in solve ``k`` is ``δ_ik V_src``,
which is itself linear in the drive vector, so the weighted sums of the
single-drive ``V`` and ``I`` are the combined drive's ``V`` and ``I`` exactly.

**Accepted power.**  With the sweep's power-wave convention (peak phasors,
``a = (V + z₀I)/(2√z₀)``, ``b = (V − z₀I)/(2√z₀)``) the incident amplitude of
drive ``k`` is read off that solve's own driven port, exactly as
:func:`~fem_em_solver.ports.sparameters._assemble_sparameter_matrix` reads it,
and the combined drive's incident vector is ``a = w ⊙ a_unit``.  ``b = S a``
by linearity of the field, so

    ``P_acc = ½ (‖a‖² − ‖b‖²) = ½ aᴴ (I − SᴴS) a``

is the real power crossing the reference planes into the structure — for the
lumped-sheet fixture, the volume loss ``½∫σ|E|²`` of the *superposed* field
over everything the sheets do not dissipate.  That equality is the drive-level
power identity `POST-6` step 1 gates in
``tests/validation/test_port_drive_superposition.py``; nothing in this module
asserts it.

**Scope.**  A drive, not a tuning: this module chooses no weights, matches no
port, and makes no claim about the absolute accuracy of the fields it combines.
Its arithmetic is exact given the stored solves; everything physical about the
result is inherited from them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional, Sequence, Union

import numpy as np

from ..post.faraday import magnetic_flux_density_from_e
from .sparameters import SParameterSweepResult, _power_waves

__all__ = ["SuperposedDrive", "superpose_drives"]


@dataclass(frozen=True)
class SuperposedDrive:
    """One multi-port drive formed from stored single-drive solves.

    ``e_complex`` and ``b_complex`` are fresh ``Function`` objects (N1curl and
    DG0 respectively); ``voltages``/``currents`` are the combined terminal
    quantities keyed by port id; ``incident_waves``/``reflected_waves`` are the
    power-wave vectors in ``port_ids`` order at ``z0_ohm``.
    """

    port_ids: tuple[str, ...]
    weights: np.ndarray
    frequency_hz: float
    omega_rad_per_s: float
    z0_ohm: float
    e_complex: object
    b_complex: object
    voltages: dict[str, complex]
    currents: dict[str, complex]
    incident_waves: np.ndarray
    reflected_waves: np.ndarray
    accepted_power_w: float
    available_power_w: float


def _weight_vector(port_ids: Sequence[str], weights) -> np.ndarray:
    """``weights`` as a complex vector in ``port_ids`` order.

    A mapping is accepted because a caller that thinks in port ids should not
    have to know the sweep's column order; a sequence must match it exactly.
    """
    if isinstance(weights, Mapping):
        missing = [pid for pid in port_ids if pid not in weights]
        if missing:
            raise ValueError(f"no drive weight given for ports: {missing}")
        extra = [pid for pid in weights if pid not in port_ids]
        if extra:
            raise ValueError(f"drive weights for ports not in the sweep: {extra}")
        vector = np.array([complex(weights[pid]) for pid in port_ids], dtype=np.complex128)
    else:
        vector = np.asarray(weights, dtype=np.complex128).reshape(-1)
        if vector.size != len(port_ids):
            raise ValueError(
                f"weights has {vector.size} entries for {len(port_ids)} ports "
                f"{list(port_ids)}"
            )
    if not np.all(np.isfinite(vector.real)) or not np.all(np.isfinite(vector.imag)):
        raise ValueError("weights contains non-finite values")
    if np.all(vector == 0.0):
        raise ValueError("every drive weight is zero: there is no drive to superpose")
    return vector


def superpose_drives(
    sweep_result: SParameterSweepResult,
    weights: Union[Sequence[complex], Mapping[str, complex]],
    *,
    z0_ohm: Optional[float] = None,
    name: str = "E_superposed",
) -> SuperposedDrive:
    """Drive every port at once with complex amplitudes ``weights``.

    ``sweep_result`` must come from
    :func:`~fem_em_solver.ports.sparameters.run_n_port_sparameter_sweep` run with
    ``keep_fields=True`` — the stored per-drive ``E`` phasors are the whole
    input.  ``weights`` is one complex amplitude per port, either in the sweep's
    own ``port_ids`` order or as a ``{port_id: w}`` mapping.

    Returns a :class:`SuperposedDrive` with the combined field, the combined
    terminal quantities, and the accepted power ``½ aᴴ(I − SᴴS)a``.  Nothing is
    normalised: ``weights = (1, 0, …)`` reproduces drive 1 exactly, array for
    array.
    """
    if sweep_result.fields is None:
        raise ValueError(
            "this sweep kept no fields: call run_n_port_sparameter_sweep(..., "
            "keep_fields=True) to superpose its drives"
        )
    if sweep_result.is_placeholder:
        raise ValueError(
            "refusing to superpose placeholder-model drives: the per-port "
            "quantities of the PORT-0 coupling heuristic are not a solved field"
        )

    port_ids = tuple(sweep_result.port_ids)
    missing = [pid for pid in port_ids if pid not in sweep_result.fields]
    if missing:
        raise ValueError(f"the sweep kept no field for drives: {missing}")

    w = _weight_vector(port_ids, weights)

    # --- the field: one function space, a weighted sum of dof arrays ---------
    #
    # ``fields`` holds the solver's ``TimeHarmonicFields`` per drive; a bare
    # ``Function`` is accepted too, so a caller may hand in phasors from any
    # source that shares the space.
    drives = [
        getattr(sweep_result.fields[pid], "e_complex", sweep_result.fields[pid])
        for pid in port_ids
    ]
    space = drives[0].function_space
    # Each solve builds its *own* ``functionspace`` object on the same mesh, so
    # the check is on the mesh and the element (and the local dof count), never
    # on object identity — the first run of `POST-6` step 1 failed on exactly
    # that mistake (`20260905T003909Z_POST-6.log:3871`).
    for pid, field in zip(port_ids, drives):
        other = field.function_space
        if (
            other.mesh is not space.mesh
            or other.ufl_element() != space.ufl_element()
            or np.asarray(field.x.array).shape != np.asarray(drives[0].x.array).shape
        ):
            raise ValueError(
                f"drive '{pid}' lives in a different function space from drive "
                f"'{port_ids[0]}'; these solves do not share one operator and "
                "their superposition is not a drive of one problem"
            )
    from dolfinx import fem  # local: keep the import cost off module import

    e_sum = fem.Function(space, name=name)
    acc = np.zeros_like(np.asarray(e_sum.x.array))
    for weight, field in zip(w, drives):
        acc += complex(weight) * np.asarray(field.x.array)
    e_sum.x.array[:] = acc
    e_sum.x.scatter_forward()

    omega = 2.0 * np.pi * float(sweep_result.frequency_hz)
    b_sum = magnetic_flux_density_from_e(e_sum, omega, name=f"B_of_{name}")

    # --- the terminal quantities: weighted sums of the single-drive ones -----
    voltages: dict[str, complex] = {}
    currents: dict[str, complex] = {}
    for pid in port_ids:
        v = 0.0 + 0.0j
        i = 0.0 + 0.0j
        for weight, driven in zip(w, port_ids):
            response = sweep_result.excitation_results[driven].responses[pid]
            v += complex(weight) * complex(response.voltage_v)
            i += complex(weight) * complex(response.current_a)
        voltages[pid] = v
        currents[pid] = i

    # --- the power waves and the accepted power -----------------------------
    #
    # ``a_unit[k]`` is the incident amplitude drive k's *own* driven port
    # carries in its own solve — the same reading `_assemble_sparameter_matrix`
    # normalises S by, so ``b = S a`` is consistent with the S it is applied to
    # by construction rather than by assumption.
    if z0_ohm is None:
        references = {
            float(sweep_result.excitation_results[pid].responses[pid].termination_ohm)
            for pid in port_ids
        }
        if len(references) != 1:
            raise ValueError(
                "the ports carry different reference impedances "
                f"{sorted(references)}; pass z0_ohm explicitly"
            )
        z0 = references.pop()
    else:
        z0 = float(z0_ohm)

    a_unit = np.array(
        [
            _power_waves(
                complex(sweep_result.excitation_results[pid].responses[pid].voltage_v),
                complex(sweep_result.excitation_results[pid].responses[pid].current_a),
                z0,
            )[0]
            for pid in port_ids
        ],
        dtype=np.complex128,
    )
    a_vector = w * a_unit
    s_matrix = np.asarray(sweep_result.s_matrix, dtype=np.complex128)
    b_vector = s_matrix @ a_vector

    # Peak-phasor convention throughout the solver, hence the ½: the available
    # power of a source of amplitude ``V_src`` into ``z0`` is ``|V_src|²/(8z0)``
    # and ``½|a|²`` is exactly that.
    available = 0.5 * float(np.sum(np.abs(a_vector) ** 2))
    accepted = 0.5 * float(
        np.real(np.vdot(a_vector, a_vector) - np.vdot(b_vector, b_vector))
    )

    return SuperposedDrive(
        port_ids=port_ids,
        weights=w,
        frequency_hz=float(sweep_result.frequency_hz),
        omega_rad_per_s=omega,
        z0_ohm=z0,
        e_complex=e_sum,
        b_complex=b_sum,
        voltages=voltages,
        currents=currents,
        incident_waves=a_vector,
        reflected_waves=b_vector,
        accepted_power_w=accepted,
        available_power_w=available,
    )
