# Distilled migration map, 0.7.2 → 0.11.0.post0

Verified against fetched release notes (see `release-notes.md`) and the
0.11 demos (see `idioms-0.11.md`). The 0.10 layer is a known gap —
introspect the container. Repo hit list compiled 2026-08-18 against the
tree at `OPS-18` trigger time.

## Confirmed old → new

| 0.7.2 idiom (ours) | 0.11 idiom | Since |
|---|---|---|
| `dolfinx.io.gmshio` module | `from dolfinx.io import gmsh as gmshio` | ≤ 0.11 (0.10 gap — confirm) |
| `model_to_mesh(...)` returns a tuple `(mesh, cell_tags, facet_tags)` | returns a **`MeshData` object**: `.mesh`, `.cell_tags`, `.facet_tags`, `.ridge_tags`, `.peak_tags` | ≤ 0.11 |
| `fem.petsc.LinearProblem(a, L, bcs=..., petsc_options=...)` | adds **required-in-practice `petsc_options_prefix=`**; `petsc_options` dict still accepted; `"ksp_error_if_not_converged": True` is the demo default | 0.11 |
| `Function.vector` | `Function.x.petsc_vec` | 0.9 (old name removed) |
| `fem.set_bc(b.array, bcs)` | `[bc.set(b.array) for bc in bcs]` | 0.9 |
| `apply_lifting(..., scale=)` | `apply_lifting(..., alpha=)` | 0.9 |
| `fem.FunctionSpace` (capitalized class-style ctor) | removed outright; only `fem.functionspace` factory | 0.8 (we already use the factory — verify no stragglers) |
| UFL element ctors taking `gdim` | `gdim` removed; `value_shape` lives on the function space | 0.8 |
| `dolfinx.cpp.fem.petsc.discrete_gradient` (cpp namespace) | public wrap exists from 0.8 (`dolfinx.fem` namespace family — introspect exact location) | 0.8 |
| pybind11 `dolfinx.cpp.*` layout | **nanobind** rebuild — every direct `dolfinx.cpp.*` touch must be re-pointed at public API | 0.8 |
| `write_meshtags(tags, x)` signatures | tags written individually with explicit `geometry_xpath` (see idioms) | by 0.11 |

## Structural changes without a one-line rename

- **Form constructor restructured** (0.8): integral data moved into a
  struct; affects only code constructing `Form` objects manually.
- **Mesh/topology MPI communicators split** (0.8): code assuming
  `mesh.comm is topology.comm` must be re-audited — this is a
  rank-safety class of bug (CLAUDE.md hard rule territory).
- **PETSc fully optional** (0.9): imports of `dolfinx.fem.petsc` are
  lazier; import errors surface differently.
- **`mesh.refine` returns cell + facet relations** (0.9): meshtag
  transfer across refinement is now first-class (relevant to any future
  h-ladder tooling).
- **`Function.interpolate_nonmatching`** (0.9): dedicated non-matching
  interpolation entry point.
- **New solver surface** (0.11): SuperLU_DIST behind `LinearProblem`
  (second distributed direct solver besides MUMPS — relevant to the
  `TH-11` step-5b memory wall); SNES uses PETSc context objects.
- **ADIOS2 → 2.12.1** (0.11): the docker h5py/ADIOS2 plumbing in
  `OPS-18` step 1 must re-verify against the new image's libraries.
- **VTX/VTK I/O**: complex values stored correctly (0.8), DG-0 support
  (0.8), arbitrary-degree cells (0.8), arbitrary-length tensors (0.9),
  path handling + unique-name checks (0.11). Our `EX-14`/`EX-17`
  round-trip gates re-verify this for free in the `OPS-18` step-3
  re-gate.

## Repo-specific hit list (where step 2 will actually land)

- `src/fem_em_solver/io/mesh.py` — gmshio import path; **tuple
  unpacking of `model_to_mesh` breaks hard** (now `MeshData`);
  `write_meshtags` xpath signatures; `GhostMode` defaults re-verify.
- `src/fem_em_solver/core/time_harmonic.py` + `core/solvers.py` — any
  `Function.vector`, `set_bc`, `apply_lifting(scale=)`; `LinearProblem`
  prefix; DG output-space construction (`("DG", degree, (3,))` style —
  survives, but sits on the 0.8 value_shape reshuffle).
- `post/evaluation.py` (parallel point eval) — nanobind rebuild of any
  `dolfinx.cpp.*` access; `interpolate_nonmatching` may simplify it.
- `docker/` + `/usr/local/bin/dolfinx-complex-mode` +
  compose `PYTHONPATH` — `OPS-18` step 1 items; Python minor and
  variant dir may both change.
- Anything importing `dolfinx.cpp.fem.petsc.discrete_gradient`
  (planned `TH-13`-class iterative work) — use the public wrap.

## Migration discipline

Breakage in this span is **loud** (imports and signatures fail fast);
the silent-drift risk concentrates in quadrature defaults and element
construction — which is exactly what the `OPS-18` step-3 re-gate
catches. A gated number that moves is a finding, never a band
adjustment.
