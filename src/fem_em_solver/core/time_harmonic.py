"""Time-harmonic (frequency-domain) Maxwell solver.

Solves the complex curl-curl equation in the ``e^{+jωt}`` convention

.. math::

    ∇×(μᵣ⁻¹ ∇×E) − k₀² ε_c E = −jωμ₀ J,
    ε_c = εᵣ − j σ/(ω ε₀),   k₀² = ω² μ₀ ε₀

with N1curl elements and a MUMPS direct solve (`TH-1` steps 1–3). The former
``E = −jωA`` magnetostatic proxy is gone; see PROJECT_PLAN §2.1 for why it was
never a Maxwell solve.

**This module requires the complex DolfinX build.** ``ε_c`` and the load are
complex, and in a real build the imaginary parts are silently discarded rather
than raising, so :meth:`TimeHarmonicSolver.solve` refuses to run in real mode.
Run with ``source /usr/local/bin/dolfinx-complex-mode`` (see
``tests/environment/test_complex_mode.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Optional, Sequence

import numpy as np
import ufl
import dolfinx
from dolfinx import fem
from dolfinx.fem.petsc import LinearProblem
from petsc4py import PETSc

from ..materials import GelledSalinePhantomMaterial
from ..utils.constants import EPSILON_0, MU_0
from .source_projection import remove_gradient_content
from .solvers import (
    DEFAULT_GAUGE_PENALTY,
    LinearSolveDiagnostics,
    MagnetostaticSolver,
)


class TimeHarmonicBoundaryCondition(str, Enum):
    """Supported time-harmonic boundary-condition modes (MVP set)."""

    NATURAL = "natural"
    PEC_ZERO_TANGENTIAL_A = "pec_zero_tangential_a"


def normalize_boundary_condition(
    value: TimeHarmonicBoundaryCondition | str,
) -> TimeHarmonicBoundaryCondition:
    """Normalize/validate boundary-condition mode from enum or string."""
    if isinstance(value, TimeHarmonicBoundaryCondition):
        return value

    normalized = str(value).strip().lower()
    for candidate in TimeHarmonicBoundaryCondition:
        if normalized == candidate.value:
            return candidate

    valid = ", ".join(repr(mode.value) for mode in TimeHarmonicBoundaryCondition)
    raise ValueError(
        "TimeHarmonicProblem.boundary_condition must be one of "
        f"{valid}; got {value!r}"
    )


@dataclass(frozen=True)
class HomogeneousMaterial:
    """Homogeneous linear material properties for MVP frequency-domain solves."""

    sigma: float
    epsilon_r: float
    mu_r: float = 1.0

    def validate(self, *, context: str = "material") -> None:
        """Validate scalar material properties and raise actionable errors."""
        if not np.isfinite(self.sigma) or self.sigma < 0:
            raise ValueError(f"{context}.sigma must be finite and non-negative (S/m), got {self.sigma!r}")
        if not np.isfinite(self.epsilon_r) or self.epsilon_r <= 0:
            raise ValueError(
                f"{context}.epsilon_r must be finite and positive (relative permittivity), got {self.epsilon_r!r}"
            )
        if not np.isfinite(self.mu_r) or self.mu_r <= 0:
            raise ValueError(
                f"{context}.mu_r must be finite and positive (relative permeability), got {self.mu_r!r}"
            )


@dataclass(frozen=True)
class TimeHarmonicProblem:
    """Container for minimal time-harmonic solve inputs."""

    mesh: dolfinx.mesh.Mesh
    frequency_hz: float
    material: HomogeneousMaterial
    frequency_unit: str = "Hz"
    material_map: Optional[Mapping[int, HomogeneousMaterial]] = None
    cell_tags: Optional[dolfinx.mesh.MeshTags] = None
    facet_tags: Optional[dolfinx.mesh.MeshTags] = None
    phantom_material: Optional[GelledSalinePhantomMaterial] = None
    phantom_tag: int = 3
    boundary_condition: TimeHarmonicBoundaryCondition | str = TimeHarmonicBoundaryCondition.NATURAL
    dirichlet_e_field: Optional[Callable] = None
    solver_petsc_options: Optional[Mapping[str, object]] = None
    collect_solver_diagnostics: bool = False


@dataclass
class TimeHarmonicFields:
    """Frequency-domain electric field represented as real/imag vector fields.

    ``e_real``/``e_imag`` are DG-interpolated split parts of the solved phasor
    (kept so downstream chunks keep working); ``e_complex`` is the N1curl
    solution itself, which is what any analytic gate should compare against.
    In complex mode every ``fem.Function`` is complex-valued, so ``e_real``
    carries the real part with a zero imaginary part, not a real dtype.
    """

    e_real: fem.Function
    e_imag: fem.Function
    frequency_hz: float
    sigma_field: Optional[fem.Function] = None
    epsilon_r_field: Optional[fem.Function] = None
    mu_r_field: Optional[fem.Function] = None
    boundary_condition: TimeHarmonicBoundaryCondition = TimeHarmonicBoundaryCondition.NATURAL
    dirichlet_dof_count: int = 0
    solve_diagnostics: Optional[LinearSolveDiagnostics] = None
    e_complex: Optional[fem.Function] = None

    @property
    def omega(self) -> float:
        return float(2.0 * np.pi * self.frequency_hz)


def _validate_material_map_tags(
    mesh: dolfinx.mesh.Mesh,
    cell_tags: Optional[dolfinx.mesh.MeshTags],
    material_map: Mapping[int, HomogeneousMaterial],
) -> None:
    """Every tag a material_map names must exist in the mesh's cell tags.

    ``cell_tags.values`` is **rank-local**: a subdomain small enough to live
    entirely on one rank is simply absent from every other rank's array, so the
    unreduced check rejects a perfectly valid map on some ranks and accepts it
    on others.  That is worse than a wrong answer — the ranks then disagree
    about whether to enter the solve, and the ones that do hang in the first
    collective until the harness timeout kills them.  (Measured: PORT-1 step
    3b-xiii, `20260808T003238Z_PORT-1-step3bxiii-ladder-n2.log` — a material
    map over the two 1 mm gap boxes, valid globally, raised "Known tags:
    [1, 2, 3]" on one of two ranks and cost the run 601 s to a 246 s test
    session.)  The tag *set* is a global property of the mesh, so it is
    reduced before it is tested.
    """
    if cell_tags is None:
        raise ValueError(
            "material_map requires problem.cell_tags so each requested tag can be assigned a material"
        )

    local_tags = {int(tag) for tag in np.asarray(cell_tags.values)}
    known_tags = set().union(*mesh.comm.allgather(local_tags))
    missing_tags = sorted(int(tag) for tag in material_map if int(tag) not in known_tags)
    if missing_tags:
        raise ValueError(
            "material_map references tags that do not exist in problem.cell_tags: "
            f"{missing_tags}. Known tags: {sorted(known_tags)}"
        )


def build_mu_r_field(
    mesh: dolfinx.mesh.Mesh,
    default_material: HomogeneousMaterial,
    *,
    cell_tags: Optional[dolfinx.mesh.MeshTags] = None,
    material_map: Optional[Mapping[int, HomogeneousMaterial]] = None,
) -> fem.Function:
    """Build the DG0 μᵣ(x) field the curl-curl term and the Poynting flux share.

    Split out of :func:`build_material_fields` rather than added to its
    two-tuple return so no existing caller changes shape (`POST-3` step 5).
    μᵣ is still declared per material — one scalar per tag — so
    :meth:`HomogeneousMaterial.validate` keeps rejecting a non-scalar μᵣ; what
    becomes piecewise is the *field assembled from* those scalars.

    ``phantom_material`` takes no part here: the gelled-saline phantom is
    non-magnetic, so phantom cells keep ``default_material.mu_r``.
    """
    q0 = fem.functionspace(mesh, ("DG", 0))
    mu_r_field = fem.Function(q0, name="mu_r")
    mu_values = mu_r_field.x.array
    mu_values[:] = float(default_material.mu_r)

    if material_map:
        _validate_material_map_tags(mesh, cell_tags, material_map)
        for tag, tagged_material in material_map.items():
            tagged_material.validate(context=f"material_map[{int(tag)}]")
            tag_cells = cell_tags.indices[cell_tags.values == int(tag)]
            for cell in tag_cells:
                mu_values[q0.dofmap.cell_dofs(int(cell))] = float(tagged_material.mu_r)

    mu_r_field.x.scatter_forward()
    return mu_r_field


def build_material_fields(
    mesh: dolfinx.mesh.Mesh,
    default_material: HomogeneousMaterial,
    *,
    cell_tags: Optional[dolfinx.mesh.MeshTags] = None,
    material_map: Optional[Mapping[int, HomogeneousMaterial]] = None,
    phantom_material: Optional[GelledSalinePhantomMaterial] = None,
    phantom_tag: int = 3,
) -> tuple[fem.Function, fem.Function]:
    """Build DG0 material property fields with optional phantom-tag override.

    Returns
    -------
    sigma_field, epsilon_r_field
        DG0 scalar fields assigned cell-wise across the mesh.
    """

    q0 = fem.functionspace(mesh, ("DG", 0))
    sigma_field = fem.Function(q0, name="sigma")
    epsilon_r_field = fem.Function(q0, name="epsilon_r")

    sigma_values = sigma_field.x.array
    epsilon_values = epsilon_r_field.x.array

    sigma_values[:] = float(default_material.sigma)
    epsilon_values[:] = float(default_material.epsilon_r)

    if material_map:
        _validate_material_map_tags(mesh, cell_tags, material_map)

        for tag, tagged_material in material_map.items():
            tagged_material.validate(context=f"material_map[{int(tag)}]")
            tag_cells = cell_tags.indices[cell_tags.values == int(tag)]
            for cell in tag_cells:
                dofs = q0.dofmap.cell_dofs(int(cell))
                sigma_values[dofs] = float(tagged_material.sigma)
                epsilon_values[dofs] = float(tagged_material.epsilon_r)

    if phantom_material is not None:
        phantom_material.validate()
        if cell_tags is None:
            raise ValueError("phantom_material requires problem.cell_tags to assign phantom-tagged cells")

        if material_map and int(phantom_tag) in {int(tag) for tag in material_map}:
            raise ValueError(
                f"phantom_tag={phantom_tag} is assigned in both material_map and phantom_material; choose one assignment path"
            )

        phantom_cells = cell_tags.indices[cell_tags.values == int(phantom_tag)]
        if phantom_cells.size == 0:
            raise ValueError(
                f"phantom_material requested but no cells found for phantom_tag={phantom_tag}"
            )

        for cell in phantom_cells:
            dofs = q0.dofmap.cell_dofs(int(cell))
            sigma_values[dofs] = float(phantom_material.sigma)
            epsilon_values[dofs] = float(phantom_material.epsilon_r)

    sigma_field.x.scatter_forward()
    epsilon_r_field.x.scatter_forward()
    return sigma_field, epsilon_r_field


def require_complex_mode(context: str = "time-harmonic solve") -> None:
    """Raise unless PETSc scalars are complex.

    A real build does not fail on ``ε_c = εᵣ − jσ/(ωε₀)`` — it drops the
    imaginary part and returns a lossless answer, which is the exact class of
    silent defect §2.1 is about. Refuse instead.
    """
    if not np.issubdtype(np.dtype(PETSc.ScalarType), np.complexfloating):
        raise RuntimeError(
            f"{context} requires the complex DolfinX build, but PETSc.ScalarType "
            f"is {np.dtype(PETSc.ScalarType)}. Run "
            "'source /usr/local/bin/dolfinx-complex-mode' first; in real mode "
            "the imaginary part of the complex permittivity would be discarded "
            "silently."
        )


class TimeHarmonicSolver:
    """Complex frequency-domain curl-curl solver (`TH-1`).

    Assembles ``∫ μᵣ⁻¹(∇×E)·(∇×v̄) − k₀² ε_c E·v̄ dx = −jωμ₀ ∫ J·v̄ dx`` on
    N1curl elements and solves it directly with MUMPS. Requires the complex
    DolfinX build; see :func:`require_complex_mode`.
    """

    def __init__(self, problem: TimeHarmonicProblem, degree: int = 1):
        self.problem = problem
        self.degree = degree
        self.mesh = problem.mesh
        self._fields: Optional[TimeHarmonicFields] = None
        self._function_space: Optional[fem.FunctionSpace] = None
        # The last solve's solenoidal projection (None when it was off or the
        # solve had no source); keeps ψ and χ alive for the assembled form.
        self._projection = None

    def function_space(self) -> fem.FunctionSpace:
        """N1curl space the E-field is solved in (cached, shared with BCs)."""
        if self._function_space is None:
            self._function_space = fem.functionspace(self.mesh, ("N1curl", self.degree))
        return self._function_space

    def build_boundary_conditions(
        self,
    ) -> tuple[list, TimeHarmonicBoundaryCondition, int]:
        """Build BC objects from selected mode and return diagnostics.

        PEC constrains the tangential trace of E on the exterior boundary — to
        zero, or to ``problem.dirichlet_e_field`` when one is supplied (that is
        how an analytic gate imposes a known total field on a truncation box).
        NATURAL leaves the boundary term alone, which is PMC.
        """
        mode = normalize_boundary_condition(self.problem.boundary_condition)

        if mode == TimeHarmonicBoundaryCondition.NATURAL:
            return [], mode, 0

        v_space = self.function_space()
        fdim = self.mesh.topology.dim - 1
        self.mesh.topology.create_connectivity(fdim, self.mesh.topology.dim)
        exterior_facets = dolfinx.mesh.exterior_facet_indices(self.mesh.topology)
        exterior_dofs = fem.locate_dofs_topological(v_space, fdim, exterior_facets)

        boundary_value = fem.Function(v_space)
        if self.problem.dirichlet_e_field is None:
            boundary_value.x.array[:] = 0.0
        else:
            boundary_value.interpolate(self.problem.dirichlet_e_field)
        bcs = [fem.dirichletbc(boundary_value, exterior_dofs)]
        return bcs, mode, int(exterior_dofs.size)

    def solve(
        self,
        current_density: Optional[Callable] = None,
        subdomain_id: Optional[int] = None,
        subdomain_ids: Optional[Sequence[int]] = None,
        gauge_penalty: float = DEFAULT_GAUGE_PENALTY,
        project_source: bool = True,
        extra_bilinear_terms: Optional[Sequence[Callable]] = None,
        extra_linear_terms: Optional[Sequence[Callable]] = None,
    ) -> TimeHarmonicFields:
        """Solve the complex curl-curl problem and return the phasor E-field.

        ``gauge_penalty`` is accepted for call-site compatibility and ignored:
        at ω > 0 the operator acts as ``−k₀²ε_c`` on the gradient subspace, so
        there is no null space to price and a penalty would only add error
        (PROJECT_PLAN §7, `TH-1` formulation notes).

        ``project_source`` (default **on**, `PORT-1` step 2f) drives with the
        CG1-weakly-solenoidal part ``J′ = J − ∇ψ`` of ``current_density``
        instead of ``J`` itself; see
        :func:`~fem_em_solver.core.source_projection.remove_gradient_content`.
        The discrete gradient content of a prescribed loop current is what made
        the port diagonal capacitive (``Im Z₁₁ = −41.09 Ω`` unprojected against
        ``+7.44 Ω`` projected, Grover ``+6.82 Ω``), so a port drive wants it
        removed.  Pass ``project_source=False`` when the prescribed ``J`` *is*
        the physics rather than a stand-in for a port — a manufactured MMS
        source, or a diagnosis that pins unprojected numbers.  It costs one CG1
        Poisson solve (~2 s on the 120k-cell port fixture) and is a no-op when
        ``current_density`` is ``None``.

        ``extra_bilinear_terms`` / ``extra_linear_terms`` (`PORT-9` step 1) are
        surface terms a *port model* adds to the assembled forms — each a
        callable ``f(trial, test) -> ufl form`` resp. ``g(test) -> ufl form``,
        called with this solver's own ``TrialFunction``/``TestFunction`` so the
        arguments match the volume form's.  The lumped-port sheet of
        :mod:`fem_em_solver.ports.lumped` is the one caller; the hook exists
        because a resistive-sheet BC is a term in ``a``, not a Dirichlet
        condition or a volume source, and there was no way to reach ``a`` from
        outside.  Both default to ``None``, in which case the assembled forms
        are bit-identical to what every gated record was measured on.
        """
        material = self.problem.material
        if not np.isfinite(self.problem.frequency_hz) or self.problem.frequency_hz <= 0:
            raise ValueError(f"frequency_hz must be finite and positive (Hz), got {self.problem.frequency_hz!r}")
        if self.problem.frequency_unit.strip().lower() != "hz":
            raise ValueError(
                "TimeHarmonicProblem.frequency_unit must be 'Hz'. "
                f"Received {self.problem.frequency_unit!r}; convert to Hz before solving."
            )
        if self.problem.frequency_hz > 1e12:
            raise ValueError(
                f"frequency_hz={self.problem.frequency_hz:.6e} is unexpectedly high for this solver API. "
                "If you passed angular frequency, convert using f = omega / (2*pi)."
            )

        material.validate(context="material")

        if self.problem.phantom_material is not None:
            if abs(self.problem.phantom_material.frequency_hz - self.problem.frequency_hz) > 1e-9:
                raise ValueError(
                    "phantom_material.frequency_hz must match TimeHarmonicProblem.frequency_hz"
                )

        sigma_field, epsilon_r_field = build_material_fields(
            self.mesh,
            material,
            cell_tags=self.problem.cell_tags,
            material_map=self.problem.material_map,
            phantom_material=self.problem.phantom_material,
            phantom_tag=self.problem.phantom_tag,
        )
        mu_r_field = build_mu_r_field(
            self.mesh,
            material,
            cell_tags=self.problem.cell_tags,
            material_map=self.problem.material_map,
        )

        # After the input validation above, so a bad frequency_unit or an
        # unknown material_map tag still reports itself in either build.
        require_complex_mode()

        omega = 2.0 * np.pi * self.problem.frequency_hz
        v_space = self.function_space()
        v = ufl.TestFunction(v_space)
        a = self.bilinear_form(sigma_field, epsilon_r_field, mu_r_field=mu_r_field)

        bcs, selected_bc, dirichlet_dof_count = self.build_boundary_conditions()

        current = None if current_density is None else current_density(ufl.SpatialCoordinate(self.mesh))
        if current is None:
            zero = fem.Constant(self.mesh, np.zeros(3, dtype=PETSc.ScalarType))
            L = ufl.inner(zero, v) * ufl.dx
        else:
            # ufl.inner conjugates the test function — using ufl.dot here would
            # silently flip the e^{+jωt} convention.
            load_factor = fem.Constant(self.mesh, PETSc.ScalarType(-1j * omega * MU_0))
            if project_source:
                # J′ has support everywhere (∇ψ does), so the tag restriction
                # moves into the integrand as a DG0 indicator and the load is
                # assembled on the whole domain — same integrand cell for cell.
                self._projection = remove_gradient_content(
                    self.mesh,
                    current,
                    cell_tags=self.problem.cell_tags,
                    subdomain_ids=self._normalized_subdomain_ids(
                        subdomain_id=subdomain_id, subdomain_ids=subdomain_ids
                    ),
                )
                L = load_factor * ufl.inner(self._projection.current, v) * ufl.dx
            else:
                self._projection = None
                L = load_factor * ufl.inner(current, v) * self._current_measure(
                    subdomain_id=subdomain_id, subdomain_ids=subdomain_ids
                )

        # Port-model surface terms (`PORT-9` step 1).  A fresh
        # TrialFunction/TestFunction on the same space compares equal to the
        # ones `bilinear_form` built — UFL Arguments are identified by (space,
        # number, part) — so the sums below are single well-formed forms.
        if extra_bilinear_terms:
            e_trial = ufl.TrialFunction(v_space)
            for term in extra_bilinear_terms:
                a = a + term(e_trial, v)
        if extra_linear_terms:
            for term in extra_linear_terms:
                L = L + term(v)

        options = {
            "ksp_type": "preonly",
            "pc_type": "lu",
            "pc_factor_mat_solver_type": "mumps",
        }
        if self.problem.solver_petsc_options:
            options.update(dict(self.problem.solver_petsc_options))

        # `OPS-18` step 3: dolfinx 0.11 makes `petsc_options_prefix` a required
        # keyword — the options dict is inserted into the PETSc database under
        # it, so each call site needs its own so two solvers cannot collide.
        problem = LinearProblem(
            a,
            L,
            bcs=bcs,
            petsc_options=options,
            petsc_options_prefix="fem_em_time_harmonic_",
        )
        # `MAT-6` step 10a: keep the LinearProblem reachable so a caller can
        # query the factorization's own statistics (MUMPS INFOG/RINFOG live on
        # `solver.getPC().getFactorMatrix()`, which is discarded with `problem`
        # otherwise).  Diagnostic access only — nothing in the solve path reads
        # this attribute.
        #
        # Tradeoff, stated because this subsystem is memory-tight: holding the
        # `LinearProblem` also holds its MUMPS factor, which step 10a measured
        # at 1.6e9 entries (~37 GB effectively used across 8 ranks on the
        # 697 401-cell fixture).  Before this line that memory was released
        # when `problem` fell out of scope at the end of `solve`; now it lives
        # until the solver is dropped or re-solved, so peak usage of the
        # post-solve interpolation block rises by the factor's size.  If a
        # `MAT-6`-scale run ever hits the container cap here, the fix is to
        # extract INFOG/RINFOG into `diagnostics` at solve time and drop the
        # handle, not to grow the cap.
        self._linear_problem = problem

        # `OPS-12`: without this the KSP records nothing and every
        # `residual_history` on this path came back empty, so `residual_trend`
        # was permanently `unavailable` — the magnetostatic path has always
        # armed it (see `MagnetostaticSolver.solve`) and this one did not.
        if self.problem.collect_solver_diagnostics:
            try:
                problem.solver.setConvergenceHistory()
            except Exception:
                pass

        e_complex = problem.solve()
        e_complex.name = "E"
        e_complex.x.scatter_forward()

        diagnostics = None
        if self.problem.collect_solver_diagnostics:
            diagnostics = MagnetostaticSolver._extract_ksp_diagnostics(problem.solver)

        dg = fem.functionspace(self.mesh, ("DG", self.degree, (3,)))
        e_dg = fem.Function(dg, name="E_dg")
        e_dg.interpolate(e_complex)

        e_real = fem.Function(dg, name="E_real")
        e_real.x.array[:] = np.real(e_dg.x.array)
        e_imag = fem.Function(dg, name="E_imag")
        e_imag.x.array[:] = np.imag(e_dg.x.array)
        e_real.x.scatter_forward()
        e_imag.x.scatter_forward()

        self._fields = TimeHarmonicFields(
            e_real=e_real,
            e_imag=e_imag,
            frequency_hz=self.problem.frequency_hz,
            sigma_field=sigma_field,
            epsilon_r_field=epsilon_r_field,
            mu_r_field=mu_r_field,
            boundary_condition=selected_bc,
            dirichlet_dof_count=dirichlet_dof_count,
            solve_diagnostics=diagnostics,
            e_complex=e_complex,
        )
        return self._fields

    def bilinear_form(
        self,
        sigma_field: fem.Function,
        epsilon_r_field: fem.Function,
        *,
        mu_r_field: Optional[fem.Function] = None,
    ):
        """Sesquilinear form ``∫ μᵣ⁻¹(∇×E)·(∇×v̄) − k₀² ε_c E·v̄ dx``.

        Split out of :meth:`solve` so the operator can be assembled and probed
        on its own (matrix symmetry, conditioning) without a right-hand side.
        ``ufl.inner`` conjugates its SECOND argument in complex mode — that is
        what makes the form sesquilinear; ``ufl.dot`` would flip the sign
        convention silently (pinned in ``tests/environment/test_complex_mode.py``).

        ``mu_r_field`` is the DG0 μᵣ(x) of `POST-3` step 5; passing ``None``
        falls back to the uniform ``problem.material.mu_r``, which is what a
        caller assembling the operator on its own gets.  The *same* field must
        also reach ``H = ∇×E/(−jωμ₀μᵣ)`` in the Poynting flux leg — a piecewise
        μᵣ in only one of the two makes the power identity vacuous.
        """
        require_complex_mode("TimeHarmonicSolver.bilinear_form")
        omega = 2.0 * np.pi * self.problem.frequency_hz
        k0_squared = omega * omega * MU_0 * EPSILON_0
        epsilon_c = epsilon_r_field - 1j * sigma_field / (omega * EPSILON_0)
        mu_r_inv = (
            1.0 / float(self.problem.material.mu_r)
            if mu_r_field is None
            else 1.0 / mu_r_field
        )

        v_space = self.function_space()
        e_trial = ufl.TrialFunction(v_space)
        v = ufl.TestFunction(v_space)
        return (
            mu_r_inv * ufl.inner(ufl.curl(e_trial), ufl.curl(v)) * ufl.dx
            - k0_squared * ufl.inner(epsilon_c * e_trial, v) * ufl.dx
        )

    @staticmethod
    def _normalized_subdomain_ids(
        *,
        subdomain_id: Optional[int] = None,
        subdomain_ids: Optional[Sequence[int]] = None,
    ) -> Optional[Sequence[int]]:
        """The two spellings of the source restriction collapsed into one.

        ``None`` means "whole domain" — shared by the load measure and by the
        projection's indicator so the two can never disagree about which cells
        carry the source.
        """
        if subdomain_id is not None and subdomain_ids is not None:
            raise ValueError("Use either subdomain_id or subdomain_ids, not both")
        if subdomain_ids is None and subdomain_id is not None:
            return [subdomain_id]
        return subdomain_ids

    def _current_measure(
        self,
        *,
        subdomain_id: Optional[int] = None,
        subdomain_ids: Optional[Sequence[int]] = None,
    ):
        """Integration measure for the source term (whole domain or tagged cells)."""
        subdomain_ids = self._normalized_subdomain_ids(
            subdomain_id=subdomain_id, subdomain_ids=subdomain_ids
        )
        if subdomain_ids is None:
            return ufl.dx
        if self.problem.cell_tags is None:
            raise ValueError("subdomain_id(s) requested but problem.cell_tags is None")
        return ufl.Measure(
            "dx",
            domain=self.mesh,
            subdomain_data=self.problem.cell_tags,
            subdomain_id=tuple(int(tag) for tag in subdomain_ids),
        )

    def projection(self):
        """The last solve's :class:`GradientProjection`, or ``None``.

        ``None`` means the solve had no source or ran with
        ``project_source=False``.  Exposed so a caller that needs the *driven*
        current ``I′`` — which is not the prescribed ``I`` once ``∇ψ`` is
        subtracted — can integrate the same ``J′`` the load was built from
        instead of rebuilding the recipe.
        """
        return self._projection

    def fields(self) -> TimeHarmonicFields:
        """Return last computed fields."""
        if self._fields is None:
            raise RuntimeError("Call solve() before requesting fields")
        return self._fields
