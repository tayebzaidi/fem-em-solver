"""Example (`EX-26`): the Poynting power-balance audit — where the watts go.

Every other example in this repository reports a **field**: a magnitude, an
error against a closed form, an S-parameter, a mesh. None of them audits
**power**. This one does, and it is the output quantity the MRI-RF-safety slice
ultimately routes through — SAR is a volume power integral, coil loading is a
resistance, and both are only as trustworthy as the solve's power accounting.

The instrument is ``fem_em_solver.post.poynting_power_balance``, gated by
`POST-3` (2026-07-31) and extended by `POST-5` step 4 (2026-08-19) to the
**driven** case. Poynting's theorem for ``e^{+jωt}`` phasors, real part:

    −∮ ½Re(E×H̄)·n̂ dS  =  ½∫σ|E|²dV  +  ½Re∫E·J̄ dV
        boundary flux        Ohmic loss     impressed source

The third term is the one `POST-5` added, and the reason it exists is worth the
whole example: scoring a *driven* domain against the source-free two-term form
is scoring the wrong identity, and on the smoke fixture below that omission was
the entire O(100%) "imbalance" the gate carried as a strict xfail for two days
(116.7465% → 16.7465%). The lesson generalizes past this repo — a power residual
is only evidence about the solve once the identity being scored is the one the
domain actually satisfies.

The run audits **two fixtures**, chosen because they sit on opposite sides of
that distinction:

* the **driven** time-harmonic smoke fixture (`OPS-17` step 2 / `POST-5`
  steps 1–4) — an axial current in a saline cylinder. Three terms, all
  nonzero. The three-term residual **16.7465%** is inside the fixture's
  pre-stated 25% band; the two-term residual on the same solved field is
  printed and asserted at **116.7465%**, i.e. the misreading kept computable
  by design as ``two_term_relative_imbalance``.
* the **source-free** `TH-6` lossy plane wave (`POST-3` step 1) — wall-driven
  by the exact closed form, J = 0 everywhere. Two terms, residual **8.185716%**
  on the 12³ rung, and each leg is additionally scored against *its own*
  closed form (`POST-5` step 3's per-leg construction). Handing the same call
  an explicit ``J = 0`` moves **no digit** and reports a source term of
  exactly ``0.0`` — the step-4 control that keeps "the missing source term
  explained the smoke fixture" a statement about drives rather than a licence
  the helper now grants every solve.

Everything gated is **imported** from the tests that closed it
(``tests/solver/test_time_harmonic_smoke.py``,
``tests/validation/test_poynting_balance.py`` and the `TH-6` module beneath
it) — the fixtures, the drives, the bands, the separation factor and the
analytic legs. Only the two recorded residuals the gates hold as printed
output rather than as named constants are restated here, with provenance and
unloosened.

Scope, deliberately narrow: this is a **demonstration of the audit**, not an
explanation of it. The smoke fixture's remaining 16.7465% is quoted as gated —
it is the boundary curl trace's discretisation error at ~9 cells per in-medium
wavelength (`POST-5` step 3 measured that leg at 8.1205% against its closed
form on the 12³ `TH-6` rung) — and no band moves here. No SAR number, no coil,
no loading claim.

Run it through the example runner (the ``th:`` group sources the complex build
automatically; a real build raises)::

    ./run_examples.sh -e th:8 -n 2 -t 400

Output lands in ``examples/time_harmonic/paraview_output``: two combined XDMF
files, ``poynting_audit_driven_smoke_combined.xdmf`` and
``poynting_audit_th6_plane_wave_combined.xdmf``, each carrying ``E``, ``B`` and
the **real Poynting vector** ``½Re(E×H̄)`` as a cell field. In the complex build
the XDMF writer splits every attribute into ``real_<name>`` / ``imag_<name>``
(correct writer behaviour — see the `OPS-21` known-issues entry), so in ParaView
the Poynting field is ``real_S_poynting``: glyph it to see the power flow the
boundary integral above is summing.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI

from dolfinx import default_scalar_type, fem

from fem_em_solver.core import (
    HomogeneousMaterial,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
)
from fem_em_solver.io.paraview_utils import (
    adopt_host_ownership,
    write_xdmf_with_tags,
)
from fem_em_solver.post.power_balance import poynting_power_balance
from fem_em_solver.utils.constants import MU_0

# The gated fixtures live in the tests that closed `POST-3`/`POST-5`; the §7
# `EX-26` entry requires importing them rather than restating them. The runner
# puts only ``src`` on PYTHONPATH, so the repo root goes on sys.path (the route
# `EX-19`/`EX-25` take).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.solver.test_time_harmonic_smoke import (  # noqa: E402
    AXIAL_RECORD_DISSIPATED_W,
    AXIAL_RECORD_IMBALANCE,
    AXIAL_RECORD_NET_INWARD_W,
    AXIAL_RECORD_SOURCE_W,
    AXIAL_RECORD_THREE_TERM,
    BLIND_SEPARATION_THREE_TERM,
    EPSILON_R,
    FREQUENCY_HZ,
    LADDER_RESOLUTIONS,
    POYNTING_IMBALANCE_MAX,
    SIGMA,
    SIGMA_BLIND,
    _smoke_mesh,
)
from tests.validation.test_poynting_balance import (  # noqa: E402
    OMEGA as TH6_OMEGA,
    POST5_STEP3_LEG_BAND,
    SIGMA as TH6_SIGMA,
    _analytic_legs,
    _solve_th6_fields,
)
from tests.validation.test_lossy_plane_wave import (  # noqa: E402
    BOX_L,
    MU_R as TH6_MU_R,
)

#: The `TH-6` 12³ rung's source-free residual, and the per-leg errors beside it.
#: `POST-3` step 1 and `POST-5` step 3 both hold these as *printed* output, not
#: as named constants (log ``20260819T123438Z_POST-5-step3.log``, and identical
#: on every `POST-3` gate log back to 20260731), so they are restated here with
#: provenance and asserted — anchors, never targets.
TH6_RECORD_IMBALANCE = 0.08185716
TH6_RECORD_FLUX_ERROR = 0.081205
TH6_RECORD_DISSIPATED_ERROR = 0.000711

#: The `TH-6` rung this example audits. `POST-3`'s coarse rung; 10 368 cells.
TH6_N = 12
TH6_CELLS = 10368

#: Reproduction band on every record above — the `EX-19`/`EX-25` precedent,
#: unchanged. The example runs the gates' own fixtures, on the gates' own
#: meshes, at the gates' own rank count, so agreement to round-off is what is
#: expected; 1% relative allows for mesh-generator and Krylov run-to-run noise
#: while being far tighter than any physics change could hide behind (the two
#: identities scored on the driven fixture are 7× apart).
REPRODUCTION_BAND = 0.01

OUTPUT_DIR = Path(__file__).resolve().parent / "paraview_output"

#: The `POST-5` step-4 dict keys that must be bit-identical between a
#: source-free call and the same call handed ``J = 0`` exactly.
UNMOVED_KEYS = (
    "dissipated_power_w",
    "net_inward_power_w",
    "reactive_inward_power_var",
    "power_scale_w",
    "relative_imbalance",
    "two_term_power_scale_w",
    "two_term_relative_imbalance",
)


def _check_record(label: str, measured: float, record: float) -> float:
    """Relative distance from a record, asserted inside ``REPRODUCTION_BAND``."""
    drift = abs(measured - record) / abs(record)
    assert drift < REPRODUCTION_BAND, (
        f"{label}: this run measured {measured:.6g} against the recorded "
        f"{record:.6g}, a drift of {drift:.2%} outside the "
        f"{REPRODUCTION_BAND:.0%} reproduction band. The example runs the "
        f"gate's own fixture on the gate's own mesh, so a drift this large "
        f"means the example path and the gate are no longer the same "
        f"computation — that is a finding about one of them, not a band to "
        f"widen"
    )
    return drift


def _audit_table(label: str, balance: dict) -> None:
    """The four rows of the audit, and the two residuals scored on them."""
    print(f"\n[audit] {label}")
    print(
        f"  boundary flux   -oint 1/2 Re(E x Hbar).n dS = "
        f"{balance['net_inward_power_w']:>13.6e} W  (into the domain)"
    )
    print(
        f"  Ohmic loss       1/2 int sigma |E|^2 dV     = "
        f"{balance['dissipated_power_w']:>13.6e} W"
    )
    print(
        f"  impressed source 1/2 Re int E.conj(J) dV    = "
        f"{balance['source_power_w']:>13.6e} W"
    )
    print(
        f"  reactive flux   -oint 1/2 Im(E x Hbar).n dS = "
        f"{balance['reactive_inward_power_var']:>13.6e} var  (reported, not scored)"
    )
    print(
        f"  residual, identity scored : {balance['relative_imbalance']:>10.4%}  "
        f"(scale {balance['power_scale_w']:.6e} W)"
    )
    print(
        f"  residual, two-term form   : "
        f"{balance['two_term_relative_imbalance']:>10.4%}  "
        f"(scale {balance['two_term_power_scale_w']:.6e} W)"
    )


def _paraview_fields(msh, e_complex, omega: float, mu_r: float):
    """CG1 ``E``, and DG0 ``B`` and real Poynting vector, from a solved phasor.

    ``E`` is interpolated into CG1 and split into real/imaginary parts the way
    `EX-19`/`EX-25` do (XDMF cannot carry N1curl at any order). ``B`` and ``S``
    both route through ``curl E``, which for degree-1 N1curl is **cell-wise
    constant**, so they are exported as DG0 rather than smoothed onto vertices —
    the cell field is the honest resolution of the quantity, and it is the same
    ``H = curl E/(−jωμ₀μᵣ)`` reconstruction the boundary integral above uses.
    """
    v_cg = fem.functionspace(msh, ("Lagrange", 1, (3,)))
    e_cg = fem.Function(v_cg, name="E_phasor")
    e_cg.interpolate(e_complex)
    e_cg.x.scatter_forward()

    e_re = fem.Function(v_cg, name="E_real")
    e_re.x.array[:] = np.real(e_cg.x.array)
    e_im = fem.Function(v_cg, name="E_imag")
    e_im.x.array[:] = np.imag(e_cg.x.array)

    s_cg = fem.functionspace(msh, ("Lagrange", 1))
    e_mag = fem.Function(s_cg, name="E_magnitude")
    components = np.abs(e_cg.x.array.reshape(-1, 3))
    e_mag.x.array[:] = np.sqrt(np.sum(components * components, axis=1))

    w_dg = fem.functionspace(msh, ("DG", 0, (3,)))
    curl_e = ufl.curl(e_complex)
    # B = curl E / (-j omega) from Faraday's law, and H = B/(mu_0 mu_r); the
    # Poynting vector is then 1/2 E x conj(H), whose *real* part is the power
    # flow the boundary leg integrates.
    b_ufl = curl_e / (-1j * omega)
    h_ufl = curl_e / (-1j * omega * MU_0 * mu_r)
    s_ufl = 0.5 * ufl.cross(e_complex, ufl.conj(h_ufl))

    b_fn = fem.Function(w_dg, name="B_phasor")
    b_fn.interpolate(fem.Expression(b_ufl, w_dg.element.interpolation_points()))
    b_re = fem.Function(w_dg, name="B_real")
    b_re.x.array[:] = np.real(b_fn.x.array)

    s_fn = fem.Function(w_dg, name="S_complex")
    s_fn.interpolate(fem.Expression(s_ufl, w_dg.element.interpolation_points()))
    s_re = fem.Function(w_dg, name="S_poynting")
    s_re.x.array[:] = np.real(s_fn.x.array)

    for f in (e_re, e_im, e_mag, b_re, s_re):
        f.x.scatter_forward()
    return {
        "E_real": e_re,
        "E_imag": e_im,
        "E_magnitude": e_mag,
        "B_real": b_re,
        "S_poynting": s_re,
    }


def _export(stem: str, msh, cell_tags, e_complex, omega: float, mu_r: float,
            comm: MPI.Comm) -> Path:
    """Combined XDMF carrying E, B and the real Poynting vector."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    xdmf_path, _ = write_xdmf_with_tags(
        OUTPUT_DIR / stem,
        msh,
        cell_tags,
        _paraview_fields(msh, e_complex, omega, mu_r),
        comm=comm,
    )
    adopt_host_ownership(OUTPUT_DIR, comm=comm)
    return xdmf_path


def _driven_smoke_leg(comm: MPI.Comm) -> dict:
    """The driven fixture: three terms, and the two-term misreading beside it.

    The mesh, the material, the drive and the source measure are `POST-5`
    step 4's, imported — ``_smoke_mesh`` at the record rung of its own h-ladder.
    """
    mesh, cell_tags, facet_tags = _smoke_mesh(LADDER_RESOLUTIONS[0], comm)
    problem = TimeHarmonicProblem(
        mesh=mesh,
        frequency_hz=FREQUENCY_HZ,
        material=HomogeneousMaterial(sigma=SIGMA, epsilon_r=EPSILON_R, mu_r=1.0),
        cell_tags=cell_tags,
        facet_tags=facet_tags,
    )
    solver = TimeHarmonicSolver(problem, degree=1)

    # The axial drive, and the measure the solver assembles it on: the source
    # term is a volume integral over the region J actually lives in (tag 1, the
    # inner conductor), and handing the balance any other measure scores a
    # different identity.
    j_expr = ufl.as_vector([0.0, 0.0, 1.0])
    fields = solver.solve(
        current_density=lambda x: j_expr, subdomain_id=1, gauge_penalty=1e-3
    )
    dx_source = ufl.Measure("dx", domain=mesh, subdomain_data=cell_tags)(1)

    honest = poynting_power_balance(
        fields.e_complex,
        omega=fields.omega,
        sigma=SIGMA,
        current_density=j_expr,
        source_measure=dx_source,
        comm=comm,
    )
    # Negative control on the physics rather than on the identity: the same
    # solved field scored as if the medium were lossless. The boundary flux and
    # the source term are unchanged and the volume leg collapses to exactly
    # zero, so a genuinely balanced solve must fail the very band it passes.
    blind = poynting_power_balance(
        fields.e_complex,
        omega=fields.omega,
        sigma=SIGMA_BLIND,
        current_density=j_expr,
        source_measure=dx_source,
        comm=comm,
    )
    ncells = comm.allreduce(
        mesh.topology.index_map(mesh.topology.dim).size_local, op=MPI.SUM
    )
    return {
        "mesh": mesh,
        "cell_tags": cell_tags,
        "fields": fields,
        "honest": honest,
        "blind": blind,
        "ncells": int(ncells),
    }


def _plane_wave_leg(comm: MPI.Comm) -> dict:
    """The source-free fixture: two terms, each scored against its closed form.

    Then the `POST-5` step-4 control — the same call handed an explicit
    ``J = 0`` must move no digit and report exactly ``0.0`` W of source power.
    The zero drive is a ``fem.Constant``, not a literal ``ufl.as_vector`` of
    zeros: a literal folds to a domain-less UFL zero and the helper
    short-circuits it, and the point of the control is that the integral is
    *assembled* (known-issues 2026-08-17, `OPS-17` step-2 defect 4).
    """
    msh, _, fields = _solve_th6_fields(TH6_N, TH6_SIGMA)

    source_free = poynting_power_balance(
        fields.e_complex, omega=TH6_OMEGA, sigma=TH6_SIGMA, mu_r=TH6_MU_R, comm=comm
    )
    zero_j = fem.Constant(msh, np.zeros(3, dtype=default_scalar_type))
    with_zero_source = poynting_power_balance(
        fields.e_complex,
        omega=TH6_OMEGA,
        sigma=TH6_SIGMA,
        mu_r=TH6_MU_R,
        current_density=zero_j,
        comm=comm,
    )
    ncells = comm.allreduce(
        msh.topology.index_map(msh.topology.dim).size_local, op=MPI.SUM
    )
    exact = _analytic_legs()
    return {
        "mesh": msh,
        "fields": fields,
        "source_free": source_free,
        "with_zero_source": with_zero_source,
        "exact": exact,
        "flux_error": abs(source_free["net_inward_power_w"] - exact["flux_w"])
        / exact["flux_w"],
        "dissipated_error": abs(
            source_free["dissipated_power_w"] - exact["dissipated_w"]
        )
        / exact["dissipated_w"],
        "ncells": int(ncells),
    }


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
        print("EX-26 — Poynting power-balance audit: where the watts go")
        print("=" * 72)
        print(
            f"\n[identity] -oint 1/2 Re(E x Hbar).n dS = 1/2 int sigma|E|^2 dV"
            f" + 1/2 Re int E.conj(J) dV"
            f"\n           boundary flux            Ohmic loss"
            f"          impressed source"
            f"\n[instrument] fem_em_solver.post.poynting_power_balance — POST-3"
            f" (2026-07-31), third term added by POST-5 step 4 (2026-08-19)"
            f"\n[fixtures] a DRIVEN cylinder (three terms) and a SOURCE-FREE"
            f" plane wave (two terms), both imported from their gates",
            flush=True,
        )

    # ---- leg 1: the driven fixture ------------------------------------------
    driven = _driven_smoke_leg(comm)
    honest, blind = driven["honest"], driven["blind"]

    if comm.rank == 0:
        print(
            f"\n[fixture] driven smoke cylinder: axial J = z_hat A/m^2 in the "
            f"inner conductor (tag 1), sigma = {SIGMA} S/m, eps_r = "
            f"{EPSILON_R}, f = {FREQUENCY_HZ / 1e6:.2f} MHz, h = "
            f"{LADDER_RESOLUTIONS[0]} m => {driven['ncells']} cells "
            f"(~9 cells per in-medium wavelength)"
        )
        _audit_table(
            "driven cylinder, three-term identity (the one this domain satisfies)",
            honest,
        )

    # The gate: the three-term residual inside the fixture's pre-stated band.
    assert honest["relative_imbalance"] < POYNTING_IMBALANCE_MAX, (
        f"real power in through the boundary "
        f"({honest['net_inward_power_w']:.6e} W) and the power delivered to "
        f"the medium (Ohmic {honest['dissipated_power_w']:.6e} W + impressed "
        f"source {honest['source_power_w']:.6e} W) disagree by "
        f"{honest['relative_imbalance']:.4%}, outside the pre-stated "
        f"{POYNTING_IMBALANCE_MAX:.0%} band for this coarse fixture"
    )

    # ---- the negative control: the identity nobody should have scored --------
    #
    # The EX-18 inverted-assertion pattern, and here it is the §5.4 capability
    # statement itself. The two-term reading on the *same solved field* is the
    # misreading POST-5 step 4 corrected; it stays computable by design, and
    # asserting that it FAILS the very band the three-term reading passes is
    # what makes "the source term was the whole imbalance" a measurement rather
    # than a story.
    assert honest["two_term_relative_imbalance"] > POYNTING_IMBALANCE_MAX, (
        f"the source-free two-term reading of this DRIVEN fixture came in at "
        f"{honest['two_term_relative_imbalance']:.4%}, inside the "
        f"{POYNTING_IMBALANCE_MAX:.0%} band the three-term reading is gated on "
        f"— the two identities have stopped being distinguishable here and the "
        f"example demonstrates nothing"
    )
    assert blind["dissipated_power_w"] == 0.0, (
        f"the sigma-blind control dissipated {blind['dissipated_power_w']:.6e} "
        f"W at sigma = 0 exactly; the volume leg must vanish identically, not "
        f"approximately"
    )
    assert blind["relative_imbalance"] > (
        BLIND_SEPARATION_THREE_TERM * honest["relative_imbalance"]
    ), (
        f"scoring the same field with sigma = 0 gave a residual of only "
        f"{blind['relative_imbalance']:.4%} against the honest solve's "
        f"{honest['relative_imbalance']:.4%} — under the pre-registered "
        f"{BLIND_SEPARATION_THREE_TERM:.1f}x separation, so the audit is not "
        f"sensitive to the loss it is accounting for"
    )

    drifts = {
        "three-term residual": _check_record(
            "[driven] three-term residual",
            honest["relative_imbalance"],
            AXIAL_RECORD_THREE_TERM,
        ),
        "two-term residual": _check_record(
            "[driven] two-term residual",
            honest["two_term_relative_imbalance"],
            AXIAL_RECORD_IMBALANCE,
        ),
        "Ohmic loss": _check_record(
            "[driven] Ohmic loss",
            honest["dissipated_power_w"],
            AXIAL_RECORD_DISSIPATED_W,
        ),
        "boundary flux": _check_record(
            "[driven] boundary flux",
            honest["net_inward_power_w"],
            AXIAL_RECORD_NET_INWARD_W,
        ),
        "source power": _check_record(
            "[driven] impressed-source power",
            honest["source_power_w"],
            AXIAL_RECORD_SOURCE_W,
        ),
    }

    if comm.rank == 0:
        print(
            f"\n[control] the SAME solved field scored two ways: three-term "
            f"{honest['relative_imbalance']:.4%} (inside the unmoved "
            f"{POYNTING_IMBALANCE_MAX:.0%} band) against two-term "
            f"{honest['two_term_relative_imbalance']:.4%} (asserted to miss it) "
            f"— the impressed source carries "
            f"{abs(honest['source_power_w']) / honest['power_scale_w']:.1%} of "
            f"the largest term in the identity, so omitting it is not a "
            f"correction, it is the whole reading"
        )
        print(
            f"[control] sigma-blind (lossless medium, same field): volume leg "
            f"exactly {blind['dissipated_power_w']:.1f} W, residual "
            f"{blind['relative_imbalance']:.4%} = "
            f"{blind['relative_imbalance'] / honest['relative_imbalance']:.2f}x "
            f"the honest reading, against the pre-registered "
            f"{BLIND_SEPARATION_THREE_TERM:.1f}x floor"
        )
        for name, drift in drifts.items():
            print(f"[record] driven {name}: drift {drift:.2e} vs the POST-5 "
                  f"record, band {REPRODUCTION_BAND:.0%}")

    # ---- leg 2: the source-free fixture -------------------------------------
    wave = _plane_wave_leg(comm)
    source_free, with_zero = wave["source_free"], wave["with_zero_source"]
    exact = wave["exact"]

    if comm.rank == 0:
        print(
            f"\n[fixture] TH-6 lossy plane wave: {BOX_L} m box at {TH6_N}^3 => "
            f"{wave['ncells']} cells, sigma = {TH6_SIGMA} S/m, wall-driven by "
            f"the exact closed form. J = 0 everywhere, so the two-term identity "
            f"is the right one and is the stronger check"
        )
        _audit_table(
            "TH-6 plane wave, source-free two-term identity", source_free
        )
        print(
            f"\n[legs] each leg against its OWN closed form (POST-5 step 3): "
            f"analytic flux = {exact['flux_w']:.6e} W, analytic dissipation = "
            f"{exact['dissipated_w']:.6e} W (equal identically, by "
            f"2*alpha*beta = omega*mu0*sigma)"
        )
        print(
            f"  boundary flux error {wave['flux_error']:.4%}, Ohmic loss error "
            f"{wave['dissipated_error']:.4%}, band "
            f"{POST5_STEP3_LEG_BAND:.0%} — the residual above is the boundary "
            f"leg's discretisation error, not a cancellation"
        )

    assert wave["ncells"] == TH6_CELLS, (
        f"the TH-6 {TH6_N}^3 rung meshed to {wave['ncells']} cells, not the "
        f"recorded {TH6_CELLS} — the fixture moved under the records"
    )
    # Both legs scored against closed forms, at the band POST-5 step 3
    # pre-registered. The volume leg is the control: a boundary-leg reading
    # attributes nothing unless the volume leg hits its own closed form.
    assert wave["dissipated_error"] < POST5_STEP3_LEG_BAND, (
        f"the volume leg misses its own closed form by "
        f"{wave['dissipated_error']:.4%}, outside the "
        f"{POST5_STEP3_LEG_BAND:.0%} band — the control failed, so the "
        f"boundary-leg reading ({wave['flux_error']:.4%}) attributes nothing"
    )
    assert wave["flux_error"] < POST5_STEP3_LEG_BAND, (
        f"the boundary leg {source_free['net_inward_power_w']:.6e} W misses "
        f"its closed form {exact['flux_w']:.6e} W by {wave['flux_error']:.4%}, "
        f"outside the pre-registered {POST5_STEP3_LEG_BAND:.0%} band while the "
        f"volume leg is inside at {wave['dissipated_error']:.4%}"
    )
    assert source_free["net_inward_power_w"] > 0.0, (
        f"net real power flows *out* of a passive lossy box "
        f"({source_free['net_inward_power_w']:.4e} W) — the e^{{+jwt}} "
        f"convention is conjugated somewhere between Faraday's law and the flux"
    )

    # ---- the POST-5 step-4 control: J = 0 is exactly zero, and moves nothing -
    assert with_zero["source_power_w"] == 0.0, (
        f"the impressed-source term assembled to "
        f"{with_zero['source_power_w']:.6e} W on a source-free fixture at "
        f"J = 0 exactly; it must vanish identically, not approximately"
    )
    assert source_free["source_power_w"] == 0.0, (
        f"omitting current_density must report exactly zero source power, got "
        f"{source_free['source_power_w']:.6e} W"
    )
    for key in UNMOVED_KEYS:
        assert with_zero[key] == source_free[key], (
            f"teaching the helper the source term moved {key} on a J = 0 "
            f"fixture: {source_free[key]!r} -> {with_zero[key]!r}"
        )
    # And the source-free path must still *be* the two-term identity, digit for
    # digit — this is what keeps the POST-3 gates meaning what they did.
    assert source_free["relative_imbalance"] == (
        source_free["two_term_relative_imbalance"]
    )

    wave_drifts = {
        "residual": _check_record(
            "[TH-6] source-free residual",
            source_free["relative_imbalance"],
            TH6_RECORD_IMBALANCE,
        ),
        "boundary-leg error": _check_record(
            "[TH-6] boundary-leg error vs closed form",
            wave["flux_error"],
            TH6_RECORD_FLUX_ERROR,
        ),
        "Ohmic-leg error": _check_record(
            "[TH-6] Ohmic-leg error vs closed form",
            wave["dissipated_error"],
            TH6_RECORD_DISSIPATED_ERROR,
        ),
    }

    if comm.rank == 0:
        print(
            f"\n[control] J = 0 passed explicitly: source term "
            f"{with_zero['source_power_w']:.1f} W exactly, and all "
            f"{len(UNMOVED_KEYS)} other quantities bit-identical to the "
            f"source-free call ({source_free['relative_imbalance']:.6%} both "
            f"ways). Adding the third term to the helper granted this "
            f"source-free solve nothing"
        )
        for name, drift in wave_drifts.items():
            print(f"[record] TH-6 {name}: drift {drift:.2e} vs the POST-3/"
                  f"POST-5 record, band {REPRODUCTION_BAND:.0%}")

    # ---- ParaView -----------------------------------------------------------
    driven_path = _export(
        "poynting_audit_driven_smoke_combined",
        driven["mesh"],
        driven["cell_tags"],
        driven["fields"].e_complex,
        driven["fields"].omega,
        1.0,
        comm,
    )
    wave_path = _export(
        "poynting_audit_th6_plane_wave_combined",
        wave["mesh"],
        None,
        wave["fields"].e_complex,
        TH6_OMEGA,
        TH6_MU_R,
        comm,
    )

    if comm.rank == 0:
        print(f"\n[paraview] wrote {driven_path} "
              f"({driven['ncells']} cells, driven cylinder)")
        print(f"[paraview] wrote {wave_path} "
              f"({wave['ncells']} cells, TH-6 plane wave)")
        print(
            f"[paraview] the complex build's XDMF writer splits attributes into "
            f"`real_*`/`imag_*` (correct behaviour, OPS-21 known-issues entry), "
            f"so the fields are `real_E_magnitude`, `real_B_real`, and "
            f"`real_S_poynting` — the last is the real Poynting vector "
            f"1/2 Re(E x Hbar), cell-wise constant because curl of a degree-1 "
            f"N1curl field is. Glyph `real_S_poynting` to see the power flow "
            f"the boundary integral sums: it points inward through the wall of "
            f"the plane-wave box everywhere, and away from the conductor in the "
            f"driven cylinder."
            f"\n\nAll assertions hold on both fixtures. Total elapsed "
            f"{time.perf_counter() - started:.1f} s.",
            flush=True,
        )


if __name__ == "__main__":
    main()
