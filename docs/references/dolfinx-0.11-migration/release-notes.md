# Upstream release-note summaries (fetched 2026-08-18)

Condensed from github.com/FEniCS/dolfinx releases and the curated
fenicsproject.org blog. Quotes are from the upstream notes.

## v0.8.0

- Deprecated `fem.FunctionSpace` **removed**; only the `functionspace`
  factory remains.
- "Remove gdim input to UFL elements, move value_shape to function
  space."
- Python bindings migrated **pybind11 → nanobind**; PETSc made optional
  in the C++ layer; "Let PETSc choose default LU solver within
  NewtonSolver."
- "Simplify Form constructor by adding a struct for integral data";
  mixed-domain assembly for vector and facet integrals; mixed-domain
  coefficient packing.
- "Split mesh and mesh topology MPI communicators."
- I/O: "Implement VTK I/O for arbitrary degree tetrahedron cells" (and
  hex); "Support DG-0 functions in VTXWriter"; complex values now
  "stored correctly in VTXWriter".
- New Python wraps: `discrete_gradient`,
  `create_nonmatching_meshes_interpolation_data`,
  `entities_to_geometry`; `transpose_dofmap` exposed;
  "Speed up non-matching interpolation data and add extrapolation
  parameter"; mesh creation from Basix elements.

## v0.9.0 (release notes + curated blog)

- `dolfinx.fem.Function.vector` → **`Function.x.petsc_vec`** (old
  removed; avoids MPI communicator duplication).
- `fem.set_bc(b.array, bcs)` → **`[bc.set(b.array) for bc in bcs]`**.
- `apply_lifting`: **`scale` → `alpha`**.
- Codimension-1 mixed-domain assembly; vertex submeshes;
  `ufl.MixedFunctionSpace` + `ufl.extract_blocks` for block forms;
  `dolfinx.fem.compile_form` (data-independent compilation).
- `dolfinx.mesh.refine` returns cell and facet relations (meshtag
  transfer); custom partitioners; 1D refinement.
- `Function.interpolate_nonmatching` added; interpolation matrices
  without PETSc; builds and runs **without petsc4py**; Windows support;
  `dx` and `dx(i)` allowed in the same form; arbitrary-length
  tensor output in VTKFile/VTXWriter/XDMFFile; deprecated PETSc Vec
  access removed.

## v0.10.0 — **GAP**

The GitHub release page did not render its notes when fetched and no
curated blog post exists; the GitHub API fetch 404'd. Patch releases
v0.10.0.post2–post5 are build/test fixes (ADIOS2 ≥ 2.11 build, pytest 9,
Python 3.14, minor test bugs). **0.10-era API changes must be discovered
by introspection against the installed 0.11 container** — the
migration-map's "confirm" flags mark where this matters.

## v0.11.0 (+ v0.11.0.post0)

- New solver surface: **SuperLU_DIST support with a dedicated
  `LinearProblem` class**; SNES integration reworked to use PETSc
  context objects; `LinearProblem` takes `petsc_options_prefix` (see
  idioms).
- `FunctionSpace.dofmap(s)` interface aligned/standardized.
- Linear algebra: `MatrixCSR` transpose; zero-entry removal in sparse
  matmul.
- Mesh: expanded VTK cell types; create meshes by interpolating
  existing geometry; topology-construction threading + radix-sort /
  collision-detection speedups (faster mesh builds).
- I/O: VTXWriter filesystem-path handling and unique-name checks;
  **ADIOS2 → 2.12.1**.
- v0.11.0.post0 is a docs-only patch (MathJax rendering) — it exists,
  which is what qualifies 0.11 under the `OPS-18` lag policy.
