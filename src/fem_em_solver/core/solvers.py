"""
Magnetostatic solver using magnetic vector potential formulation.

The governing equation is:
    ∇ × (μ⁻¹ ∇ × A) = J

Where:
    A = magnetic vector potential [Wb/m]
    B = ∇ × A = magnetic flux density [T]
    H = μ⁻¹B = magnetic field intensity [A/m]
    J = current density [A/m²]
    μ = permeability [H/m]

Weak form:
    ∫ μ⁻¹ (∇ × A) · (∇ × v) dx = ∫ J · v dx

Boundary conditions:
    - Dirichlet: A × n = g (tangential A specified)
    - Natural: (∇ × A) × n = 0 (magnetic insulation)
"""

from typing import Optional, Callable, Union, List, Sequence, Mapping, Any
from enum import Enum
import warnings
import numpy as np
import basix.ufl
from dataclasses import dataclass

import dolfinx
import ufl
from dolfinx import fem, mesh, io
from dolfinx.fem.petsc import LinearProblem
from ufl import curl, inner, dx, TrialFunction, TestFunction
from mpi4py import MPI
from petsc4py import PETSc
import gmsh

from ..utils.constants import MU_0

# Coefficient of the gauge-regularisation term added to the curl-curl operator
# to remove its gradient null space (see MagnetostaticSolver.solve).
#
# Was 1e-3, which is below the numerically safe window and silently corrupts
# results. The penalty fixes the magnitude of the null-space component of A as
# |A_gradient| ~ 1/gauge; at 1e-3 that part runs ~9 orders larger than the
# physical field. B = curl(A) annihilates a gradient exactly in exact
# arithmetic, but in floating point the physical signal is swamped. Measured on
# the straight-wire fixture at N1curl degree 2, h=0.003: 920% error at 1e-3,
# 19.6% at 1e0. Degree 1 hides the problem (24.84% vs 24.67%) because its null
# space is smaller -- so raising the element degree without raising this was a
# trap.
#
# B is insensitive to the exact value across at least 1e0..1e6, verified on two
# independent geometries (straight wire and Helmholtz two-torus). 1.0 sits in
# that window with margin on the low side, where the failure is catastrophic.
DEFAULT_GAUGE_PENALTY = 1.0

# MAG-16. Largest |Im W| / |Re W| the magnetostatic energy may carry before
# compute_magnetic_energy() refuses to reduce it to a real number. The energy is
# real by construction and the measured ratio in the complex build is exactly
# 0.0 (coarse straight wire, -n 2, both gauges, 2026-08-05,
# 20260805T213201Z_MAG-16-probe-complex-prefix.log), so this bound is pure
# headroom against a future formulation change rather than a fitted tolerance.
ENERGY_IMAG_RTOL = 1e-8


def exterior_dirichlet_bc(V: fem.FunctionSpace, field: Callable) -> fem.DirichletBC:
    """Constrain an H(curl) space to an analytic field on the exterior boundary.

    The natural condition of the curl-curl form is ``n × (μ⁻¹ curl A) = 0``,
    i.e. ``n × H = 0``, which on a truncation boundary is a physical statement
    (a perfect magnetic conductor) rather than a neutral one — for a wire
    carrying net axial current it directly contradicts Ampère's law and puts a
    floor under the achievable error (MAG-13). Imposing a known ``A`` on that
    boundary instead makes the continuum limit of the discrete problem the
    analytic field.

    Constraining *all* exterior dofs of the interpolant imposes its tangential
    trace, which is the only part an H(curl) Dirichlet condition can carry.

    Parameters
    ----------
    V : fem.FunctionSpace
        H(curl) (N1curl) space of the unknown.
    field : callable
        Field in dolfinx interpolation convention: takes ``x`` of shape
        ``(3, n)`` and returns the vector field of shape ``(3, n)``. Note this
        is the transpose of the ``(n, 3)`` convention used by
        ``utils.analytical`` — adapt at the call site.

    Returns
    -------
    fem.DirichletBC
        Suitable for ``MagnetostaticSolver.solve(bc_functions=[bc])``.
    """
    domain = V.mesh
    fdim = domain.topology.dim - 1
    domain.topology.create_connectivity(fdim, domain.topology.dim)
    exterior_facets = dolfinx.mesh.exterior_facet_indices(domain.topology)
    exterior_dofs = fem.locate_dofs_topological(V, fdim, exterior_facets)

    g = fem.Function(V)
    g.interpolate(field)
    return fem.dirichletbc(g, exterior_dofs)


class GaugeContaminationWarning(UserWarning):
    """A is dominated by its gradient null space; B may be roundoff-corrupted."""


class GaugeMethod(str, Enum):
    """How the curl-curl operator's gradient null space is handled.

    PENALTY
        Add ``gauge * inner(A, v) * dx``. Cheap, but it *prices* the null space
        rather than removing it: A retains a gradient component of magnitude
        ~1/gauge, and B = curl(A) recovers the physical field only through
        cancellation. Too small a penalty destroys that cancellation silently
        (see MAG-10). Requires choosing a parameter that has no physical meaning.

    LAGRANGE
        Mixed formulation, solving for (A, p) in H(curl) x H1:

            int mu^-1 (curl A).(curl v) dx + int grad(p).v dx = int J.v dx
            int A.grad(q) dx                                   = 0

        p is a Lagrange multiplier enforcing the Coulomb gauge div(A) = 0
        weakly. The null space is *removed*, not penalised, so A comes out
        physically scaled and there is no cancellation to lose. **No parameter.**

        Measured on the straight-wire fixture (h=0.003, 88k cells, 8 ranks):

            degree 1: 24.67% error, max|A| = 1.6e-09,  5.0 s
            degree 2: 19.59% error, max|A| = 1.6e-09,  214.6 s

        versus penalty at the correct 1e0 (24.67% / 19.59%, max|A| ~ 5e1) and at
        the old 1e-3 default (24.87% / **133.77%**, max|A| up to 1.7e07). The
        saddle point reaches the right answer at both degrees without being told
        anything, and its A is ~10 orders smaller -- the gradient component is
        gone rather than suppressed.

        Costs roughly 2x the penalty at degree 1 and 7.5x at degree 2, since the
        mixed system is larger and indefinite.

        A non-zero multiplier is itself a diagnostic: p != 0 means the applied
        current is not compatible (div J != 0, or J.n != 0 on the boundary).
    """

    PENALTY = "penalty"
    LAGRANGE = "lagrange"



@dataclass
class MagnetostaticProblem:
    """Container for magnetostatic problem parameters."""
    mesh: dolfinx.mesh.Mesh
    cell_tags: Optional[dolfinx.mesh.MeshTags] = None
    facet_tags: Optional[dolfinx.mesh.MeshTags] = None
    mu: Union[float, Callable] = MU_0


@dataclass(frozen=True)
class LinearSolveDiagnostics:
    """Best-effort PETSc linear solve diagnostics for health monitoring."""

    ksp_type: str
    pc_type: str
    converged_reason: int
    iterations: int
    residual_norm: float
    residual_history: tuple[float, ...]
    residual_trend: str

    @property
    def converged(self) -> bool:
        """True when PETSc converged reason indicates success (> 0)."""
        return self.converged_reason > 0


def classify_residual_trend(residual_history: Sequence[float]) -> str:
    """Classify residual progression for compact diagnostics.

    Definition (exact, no tolerance). Let ``d`` be the first differences of the
    history and ``f = |{i : d_i <= 0}| / |d|`` the *decrease fraction* — the
    share of iterations that did not increase the residual. The label is a
    function of ``f`` alone:

    ==========================  =========================
    condition                   label
    ==========================  =========================
    ``len(history) == 0``       ``unavailable``
    ``len(history) == 1``       ``single-sample``
    non-finite or negative      ``invalid``
    ``f == 1``                  ``monotone-decrease``
    ``f > 0.5``                 ``mostly-decreasing``
    ``f == 0.5``                ``mixed``
    ``f < 0.5``                 ``mostly-increasing``
    ==========================  =========================

    The three non-monotone labels partition by the sign of ``f - 0.5``, which
    is what their names mean: "mostly decreasing" is a strict majority of
    non-increasing steps, "mostly increasing" a strict majority of increasing
    ones, and "mixed" the tie. `OPS-12` adjudicated this against the previous
    thresholds (``f >= 0.75`` / ``f >= 0.5``), which were undocumented and
    asymmetric — they gave increases a band of width 0.5 and decreases 0.25, so
    a history that decreased on two of every three iterations was reported
    ``mixed``, and no history of four or fewer samples could reach
    ``mostly-decreasing`` at all. Nothing in the docstring or the label names
    licensed that asymmetry, so the classifier moved, not the test.

    Parameters
    ----------
    residual_history:
        Sequence of finite non-negative residual norms collected per iteration.
    """
    if len(residual_history) == 0:
        return "unavailable"
    if len(residual_history) == 1:
        return "single-sample"

    history = np.asarray(residual_history, dtype=np.float64)
    if not np.isfinite(history).all() or np.any(history < 0):
        return "invalid"

    deltas = np.diff(history)
    decrease_fraction = float(np.count_nonzero(deltas <= 0.0)) / float(len(deltas))

    if np.all(deltas <= 0.0):
        return "monotone-decrease"
    if decrease_fraction > 0.5:
        return "mostly-decreasing"
    if decrease_fraction == 0.5:
        return "mixed"
    return "mostly-increasing"


class MagnetostaticSolver:
    """Solver for magnetostatic problems using vector potential formulation.
    
    This solver computes the magnetic vector potential A, from which
    B = ∇ × A and H = μ⁻¹B can be derived.
    
    Parameters
    ----------
    problem : MagnetostaticProblem
        Problem definition including mesh and material properties
    degree : int, optional
        Polynomial degree of Nedelec elements (default: 1)
    """
    
    def __init__(self, problem: MagnetostaticProblem, degree: int = 1):
        self.problem = problem
        self.degree = degree
        self.mesh = problem.mesh
        self.mu = problem.mu
        
        # Create function space (H(curl) - Nedelec elements)
        self.V = fem.functionspace(self.mesh, ("N1curl", degree))
        
        # Solution field
        self.A = fem.Function(self.V, name="A")
        self._solved = False
        self._last_solve_diagnostics: Optional[LinearSolveDiagnostics] = None
        
    @property
    def last_solve_diagnostics(self) -> Optional[LinearSolveDiagnostics]:
        """Return diagnostics from the most recent linear solve, if requested."""
        return self._last_solve_diagnostics

    @staticmethod
    def _extract_ksp_diagnostics(ksp) -> Optional[LinearSolveDiagnostics]:
        """Extract best-effort PETSc KSP diagnostics."""
        if ksp is None:
            return None

        try:
            history_raw = ksp.getConvergenceHistory()
            history = tuple(float(value) for value in history_raw)
        except Exception:
            history = tuple()

        try:
            residual_norm = float(ksp.getResidualNorm())
        except Exception:
            residual_norm = float("nan")

        return LinearSolveDiagnostics(
            ksp_type=str(ksp.getType()),
            pc_type=str(ksp.getPC().getType()),
            converged_reason=int(ksp.getConvergedReason()),
            iterations=int(ksp.getIterationNumber()),
            residual_norm=residual_norm,
            residual_history=history,
            residual_trend=classify_residual_trend(history),
        )

    def solve(self, current_density: Optional[Callable] = None, 
              bc_functions: Optional[List] = None,
              subdomain_id: Optional[int] = None,
              subdomain_ids: Optional[Sequence[int]] = None,
              gauge_penalty: float = DEFAULT_GAUGE_PENALTY,
              gauge: Union[GaugeMethod, str] = GaugeMethod.PENALTY,
              petsc_options: Optional[Mapping[str, Any]] = None,
              collect_solver_diagnostics: bool = False) -> fem.Function:
        """Solve the magnetostatic problem.
        
        Parameters
        ----------
        current_density : callable, optional
            Function returning J(x) for any point x.
            If None, assumes J = 0 (no sources).
        bc_functions : list, optional
            List of Dirichlet BC functions
        subdomain_id : int, optional
            If provided, restricts current density integration to cells
            with this tag (requires cell_tags in problem).
        subdomain_ids : Sequence[int], optional
            If provided, restricts current density integration to the union
            of these cell tags (requires cell_tags in problem).
            Mutually exclusive with ``subdomain_id``.
        gauge_penalty : float, optional
            Small regularization term added to remove the nullspace in
            pure curl-curl problems (default: 1e-3).
        petsc_options : mapping, optional
            PETSc KSP/PC options override. Defaults to direct solve
            (``ksp_type=preonly``, ``pc_type=lu``).
        collect_solver_diagnostics : bool, optional
            If True, request PETSc convergence history and expose
            ``last_solve_diagnostics`` for residual trend summaries.

        Returns
        -------
        fem.Function
            Magnetic vector potential A
        """
        # Define trial and test functions
        A_trial = TrialFunction(self.V)
        v = TestFunction(self.V)
        
        # Permeability (could be spatially varying)
        if callable(self.mu):
            mu = self.mu(ufl.SpatialCoordinate(self.mesh))
        else:
            mu = fem.Constant(self.mesh, PETSc.ScalarType(self.mu))
        mu_inv = 1.0 / mu
        
        # Bilinear form: a(A, v) = ∫ μ⁻¹ (∇ × A) · (∇ × v) dx
        # Add tiny gauge regularization to remove nullspace.
        # NB: not named `gauge` -- that is the method-selection parameter.
        gauge_const = fem.Constant(self.mesh, PETSc.ScalarType(gauge_penalty))
        a = inner(mu_inv * curl(A_trial), curl(v)) * dx + gauge_const * inner(A_trial, v) * dx
        
        # Linear form: L(v) = ∫ J · v dx
        if subdomain_id is not None and subdomain_ids is not None:
            raise ValueError("Use either subdomain_id or subdomain_ids, not both")

        if subdomain_ids is None and subdomain_id is not None:
            subdomain_ids = [subdomain_id]

        if current_density is not None:
            x = ufl.SpatialCoordinate(self.mesh)
            J = current_density(x)
        else:
            J = fem.Constant(self.mesh, np.zeros(3, dtype=PETSc.ScalarType))

        # Apply boundary conditions
        bcs = []
        if bc_functions is not None:
            bcs = bc_functions

        gauge_method = GaugeMethod(gauge) if not isinstance(gauge, GaugeMethod) else gauge
        if gauge_method is GaugeMethod.LAGRANGE:
            self.A = self._solve_lagrange(mu_inv, J, subdomain_ids, bcs, petsc_options)
            self._solved = True
            return self.A

        L = self._build_load_form(v, J, subdomain_ids)

        # Solve
        options = {"ksp_type": "preonly", "pc_type": "lu"}
        if petsc_options:
            options.update(dict(petsc_options))

        problem = LinearProblem(
            a,
            L,
            bcs=bcs,
            petsc_options=options,
            petsc_options_prefix="fem_em_magnetostatic_",
        )

        if collect_solver_diagnostics:
            try:
                problem.solver.setConvergenceHistory()
            except Exception:
                pass

        self.A = problem.solve()
        self._solved = True
        self._last_solve_diagnostics = self._extract_ksp_diagnostics(problem.solver)

        self._warn_if_gauge_contaminated(gauge_penalty)

        return self.A

    def _pin_multiplier_dofs(self, W, W1):
        """Locate exactly one dof of the multiplier space, globally agreed.

        With q free in H1 the constraint annihilates constants, so p is fixed only
        up to an additive constant and one dof must be pinned. Every rank has to
        agree on which one, hence the reduction on distance to the global
        bounding-box corner.

        Note a point constraint on an H1 function is not H1-stable in 3D, so the
        multiplier carries an arbitrary offset (its *spread* is the meaningful
        quantity). This does not affect A: only grad(p) enters the A equation.
        """
        comm = self.mesh.comm

        xg = self.mesh.geometry.x
        local_min = xg.min(axis=0) if xg.shape[0] else np.full(3, np.inf)
        corner = np.array([comm.allreduce(local_min[i], op=MPI.MIN) for i in range(3)])

        coords = W1.tabulate_dof_coordinates()
        best = (
            float(np.min(np.linalg.norm(coords - corner, axis=1)))
            if coords.shape[0]
            else np.inf
        )
        # Deterministic owner election with scalar reductions only. MPI.MINLOC over
        # a pickled Python tuple is not reliably consistent across ranks -- if two
        # ranks disagree on the winner they bcast with different roots and
        # deadlock, mesh-dependently.
        best_global = comm.allreduce(best, op=MPI.MIN)
        candidate = comm.rank if best == best_global else comm.size
        owner = comm.allreduce(candidate, op=MPI.MIN)
        if owner >= comm.size:  # no rank holds a finite candidate
            return [np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)]

        # Broadcast the chosen point, then let *every* rank run the location call.
        # fem.locate_dofs_geometrical is collective: invoking it under
        # `if comm.rank == owner` deadlocks. That deadlock is rank-count dependent
        # -- it completes at 2 ranks and hangs at 4 -- so it will not show up in a
        # single-rank test.
        target = None
        if comm.rank == owner and coords.shape[0]:
            target = coords[int(np.argmin(np.linalg.norm(coords - corner, axis=1)))]
        target = comm.bcast(target, root=owner)

        if target is None:
            return [np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)]

        found = fem.locate_dofs_geometrical(
            (W.sub(1), W1),
            lambda x: np.isclose(x[0], target[0])
            & np.isclose(x[1], target[1])
            & np.isclose(x[2], target[2]),
        )
        # Ranks that share the point (ghosts) constrain the same physical dof, so
        # letting each keep its own match stays consistent.
        return [
            np.asarray(found[0][:1], dtype=np.int32),
            np.asarray(found[1][:1], dtype=np.int32),
        ]

    def _build_load_form(self, test_function, J, subdomain_ids):
        """Assemble the RHS against a given test function.

        Built per test function rather than by substituting arguments into a
        finished form: ufl.replace() across two different function spaces does not
        do what it looks like it does -- it produces a form that hangs in the
        compiler rather than raising.
        """
        if subdomain_ids is None:
            return inner(J, test_function) * dx

        if self.problem.cell_tags is None:
            raise ValueError("subdomain_id(s) requested but problem.cell_tags is None")

        L = 0
        for tag in subdomain_ids:
            dx_sub = ufl.Measure(
                "dx",
                domain=self.mesh,
                subdomain_data=self.problem.cell_tags,
                subdomain_id=int(tag),
            )
            L += inner(J, test_function) * dx_sub
        return L

    def _solve_lagrange(self, mu_inv, J, subdomain_ids, bcs, petsc_options):
        """Saddle-point solve enforcing the Coulomb gauge with a multiplier.

        Returns the H(curl) component; the multiplier is kept on the instance as
        ``last_gauge_multiplier`` for diagnostics.
        """
        if bcs:
            raise ValueError(
                "GaugeMethod.LAGRANGE does not yet support Dirichlet conditions on A; "
                "the multiplier space would need matching constraints."
            )

        cell = self.mesh.basix_cell()
        curl_el = basix.ufl.element("N1curl", cell, self.degree)
        lag_el = basix.ufl.element("Lagrange", cell, self.degree)
        W = fem.functionspace(self.mesh, basix.ufl.mixed_element([curl_el, lag_el]))

        (A_trial, p_trial) = ufl.TrialFunctions(W)
        (v, q) = ufl.TestFunctions(W)

        a = (
            inner(mu_inv * curl(A_trial), curl(v)) * dx
            + inner(ufl.grad(p_trial), v) * dx
            + inner(A_trial, ufl.grad(q)) * dx
        )

        L = self._build_load_form(v, J, subdomain_ids)

        W1, _ = W.sub(1).collapse()
        zero = fem.Function(W1)
        zero.x.array[:] = 0.0
        pin = [fem.dirichletbc(zero, self._pin_multiplier_dofs(W, W1), W.sub(1))]

        options = {
            "ksp_type": "preonly",
            "pc_type": "lu",
            # The saddle-point system is indefinite; MUMPS handles it reliably.
            "pc_factor_mat_solver_type": "mumps",
        }
        if petsc_options:
            options.update(dict(petsc_options))

        problem = LinearProblem(
            a,
            L,
            bcs=pin,
            petsc_options=options,
            petsc_options_prefix="fem_em_mixed_saddle_",
        )
        w = problem.solve()

        self._last_solve_diagnostics = self._extract_ksp_diagnostics(problem.solver)
        self.last_gauge_multiplier = w.sub(1).collapse()
        return w.sub(0).collapse()

    def gauge_multiplier_spread(self) -> float:
        """Range of the Coulomb-gauge multiplier, or nan if none was computed.

        A spread far from zero means the applied current is not compatible with
        the curl-curl operator -- ``div J != 0`` somewhere, or ``J.n != 0`` on the
        boundary (a conductor whose current enters or leaves through the domain
        face). Only meaningful after a ``GaugeMethod.LAGRANGE`` solve.
        """
        p = getattr(self, "last_gauge_multiplier", None)
        if p is None:
            return float("nan")

        comm = self.mesh.comm
        arr = p.x.array
        hi = comm.allreduce(float(arr.max()) if arr.size else -np.inf, op=MPI.MAX)
        lo = comm.allreduce(float(arr.min()) if arr.size else np.inf, op=MPI.MIN)
        return float(hi - lo)

    def _warn_if_gauge_contaminated(self, gauge_penalty: float) -> float:
        """Warn when the gauge penalty is below the numerically safe window.

        The penalty leaves a gradient null-space component in A whose magnitude
        scales as 1/gauge_penalty. ``B = curl(A)`` cancels a gradient exactly in
        exact arithmetic, but once that component is orders larger than the
        physical field, floating-point cancellation destroys B.

        This failure is silent through every other channel: the default solver is
        a direct LU, so PETSc reports converged with residual 0.0 even when the
        result is off by a factor of ten. Measured at N1curl degree 2, h=0.003,
        gauge 1e-3: 920% field error, KSP reason 4, residual 0.0.

        The check is on the *parameter*, not the solution. A solution-based
        metric was tried first -- ``||A|| / (L * ||curl A||)``, on the reasoning
        that a physical potential satisfies |A| ~ |B|*L -- but it does not
        discriminate: that ratio is ~5e8 for a known-good solve on this fixture,
        and degree 1 at gauge 1e-3 carries a similarly large ratio while
        remaining accurate to within 0.2% of the well-conditioned answer. The
        catastrophe needs a large null-space component *and* degree-2
        conditioning, so no threshold on the ratio alone separates good from bad
        without false alarms. The ratio is still computed and returned for
        diagnostics; it is simply not used as a trigger.

        Returns ``||A|| / (L * ||curl A||)`` (``inf`` if ``curl A`` vanishes,
        ``nan`` if it could not be evaluated).
        """
        if gauge_penalty < DEFAULT_GAUGE_PENALTY:
            warnings.warn(
                f"gauge_penalty={gauge_penalty:.3e} is below the validated floor "
                f"of {DEFAULT_GAUGE_PENALTY:g}. The penalty controls the gradient "
                "null space of the curl-curl operator; too small a value lets it "
                "dominate A and corrupt B = curl(A) through round-off. Measured "
                "at N1curl degree 2, h=0.003: 920% field error at 1e-3 versus "
                "19.6% at 1e0. B is insensitive across 1e0..1e6, so there is no "
                "accuracy reason to go lower. Note the linear solve reports "
                "success regardless -- a direct LU always converges.",
                GaugeContaminationWarning,
                stacklevel=3,
            )

        try:
            comm = self.mesh.comm
            a_sq = fem.assemble_scalar(fem.form(inner(self.A, self.A) * dx))
            c_sq = fem.assemble_scalar(fem.form(inner(curl(self.A), curl(self.A)) * dx))
            a_norm = np.sqrt(max(comm.allreduce(a_sq, op=MPI.SUM), 0.0))
            c_norm = np.sqrt(max(comm.allreduce(c_sq, op=MPI.SUM), 0.0))
        except Exception:
            return float("nan")

        # Characteristic domain length, used to make the ratio dimensionless.
        try:
            extents = self.mesh.geometry.x
            local_span = float(np.max(extents) - np.min(extents)) if extents.size else 0.0
            length = comm.allreduce(local_span, op=MPI.MAX)
        except Exception:
            length = 0.0

        if length <= 0.0 or not np.isfinite(a_norm):
            return float("nan")

        if c_norm <= 0.0:
            return float("inf")

        return float(a_norm / (length * c_norm))
    
    def compute_b_field(self) -> fem.Function:
        """Compute magnetic flux density B = ∇ × A.
        
        Returns
        -------
        fem.Function
            B-field in DG space (discontinuous Galerkin)
        """
        if not self._solved:
            raise RuntimeError("Must call solve() before computing B-field")
        
        # B = curl(A) needs to be interpolated to appropriate space
        # Use DG space for B (discontinuous, vector-valued)
        DG = fem.functionspace(self.mesh, ("DG", self.degree, (3,)))
        B = fem.Function(DG, name="B")
        
        # Project curl(A) onto DG space
        B_expr = fem.Expression(curl(self.A), DG.element.interpolation_points())
        B.interpolate(B_expr)
        
        return B
    
    def compute_h_field(self) -> fem.Function:
        """Compute magnetic field intensity H = B/μ.
        
        Returns
        -------
        fem.Function
            H-field in DG space
        """
        B = self.compute_b_field()
        
        DG = fem.functionspace(self.mesh, ("DG", self.degree, (3,)))
        H = fem.Function(DG, name="H")
        
        if callable(self.mu):
            x = ufl.SpatialCoordinate(self.mesh)
            mu = self.mu(x)
        else:
            mu = fem.Constant(self.mesh, PETSc.ScalarType(self.mu))

        H_expr = fem.Expression(B / mu, DG.element.interpolation_points())
        H.interpolate(H_expr)
        
        return H
    
    def compute_magnetic_energy(self) -> float:
        """Compute total magnetic energy in the domain.
        
        W = ½ ∫ B · H dx = ½ ∫ μ⁻¹ |∇ × A|² dx

        Collective: every rank must call this together; the result is the
        global energy, identical on all ranks.

        Returns
        -------
        float
            Magnetic energy [Joules]
        """
        if not self._solved:
            raise RuntimeError("Must call solve() before computing energy")

        if callable(self.mu):
            x = ufl.SpatialCoordinate(self.mesh)
            mu_inv = 1.0 / self.mu(x)
        else:
            mu_inv = 1.0 / self.mu

        energy_expr = 0.5 * inner(mu_inv * curl(self.A), curl(self.A)) * dx
        # assemble_scalar returns only this rank's contribution; without the
        # reduction every parallel caller saw ~1/n_ranks of the energy (MAG-11).
        local_energy = fem.assemble_scalar(fem.form(energy_expr))
        total_energy = self.mesh.comm.allreduce(local_energy, op=MPI.SUM)

        # MAG-16: in the complex build every fem.Function is complex, so this
        # scalar is complex-typed even though the integrand is real by
        # construction -- ufl.inner conjugates its second argument, making it
        # mu^-1|curl A|^2/2. Take the real part, never abs(): abs() would
        # silently absorb both a spurious imaginary part and a negative real
        # one rather than failing. Measured |Im|/|Re| on the coarse
        # straight-wire fixture at -n 2, both gauges, 2026-08-05: exactly 0.0
        # (the magnetostatic load is real, so A has no imaginary part).
        real_energy = float(np.real(total_energy))
        imag_energy = float(np.imag(total_energy))
        if abs(imag_energy) > ENERGY_IMAG_RTOL * abs(real_energy):
            raise ValueError(
                f"magnetic energy has a non-negligible imaginary part: "
                f"{total_energy!r} (|Im|/|Re| = "
                f"{abs(imag_energy) / abs(real_energy) if real_energy else float('inf'):.3e} "
                f"> {ENERGY_IMAG_RTOL:g}). W = 1/2 int mu^-1|curl A|^2 is real "
                "by construction, so this is a formulation or assembly defect, "
                "not a rounding artifact -- do not discard it."
            )

        return real_energy
    
    def evaluate_at_points(self, points: np.ndarray, field: str = "A") -> np.ndarray:
        """Evaluate field at specific points.

        Collective: every rank must call this together. Each point must lie
        inside the mesh; a point no rank can locate raises ValueError rather
        than returning a silently wrong value.

        Parameters
        ----------
        points : np.ndarray
            Array of shape (n_points, 3) with coordinates
        field : str
            Field to evaluate: "A", "B", or "H"

        Returns
        -------
        np.ndarray
            Field values at points, shape (n_points, 3)
        """
        if field == "A":
            f = self.A
        elif field == "B":
            f = self.compute_b_field()
        elif field == "H":
            f = self.compute_h_field()
        else:
            raise ValueError(f"Unknown field: {field}")

        # Function.eval(points, cells) requires cells[i] to be the cell
        # containing points[i]. The previous np.arange(n) evaluated each point
        # in an arbitrary cell, extrapolating basis functions far outside
        # their support -- the same defect MAG-7 removed from the tests
        # (MAG-12). Route through the collision-based machinery instead.
        from ..post.evaluation import evaluate_vector_field_parallel

        pts = np.asarray(points, dtype=np.float64)
        values, valid = evaluate_vector_field_parallel(f, pts, comm=self.mesh.comm)
        if not np.all(valid):
            missing = np.flatnonzero(~valid)
            raise ValueError(
                f"{missing.size}/{pts.shape[0]} points lie outside the mesh; "
                f"first missing indices: {missing[:5].tolist()}"
            )
        return values
    
    def save_to_vtk(self, filename: str, fields: Optional[List[str]] = None):
        """Save solution to VTK file for visualization.
        
        Parameters
        ----------
        filename : str
            Output filename (.pvd or .vtu)
        fields : list, optional
            List of fields to save: ["A", "B", "H"]
        """
        if fields is None:
            fields = ["A"]
        
        # Write to file
        with io.VTKFile(self.mesh.comm, filename, "w") as vtk:
            if "A" in fields:
                vtk.write_function(self.A)
            if "B" in fields:
                vtk.write_function(self.compute_b_field())
            if "H" in fields:
                vtk.write_function(self.compute_h_field())
