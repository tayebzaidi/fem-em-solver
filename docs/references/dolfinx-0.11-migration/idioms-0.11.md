# Verbatim 0.11 idioms (from upstream demos, tag v0.11.0)

Excerpted 2026-08-18 from `python/demo/demo_poisson.py` and
`python/demo/demo_gmsh.py` at tag v0.11.0 (FEniCS/dolfinx, LGPL-3.0);
excerpts kept minimal for internal migration reference.

## Solve pattern (`demo_poisson.py`)

```python
from mpi4py import MPI
from petsc4py.PETSc import ScalarType
import numpy as np
import ufl
from dolfinx import fem, io, mesh
from dolfinx.fem.petsc import LinearProblem

V = fem.functionspace(msh, ("Lagrange", 1))

tdim = msh.topology.dim
fdim = tdim - 1
facets = mesh.locate_entities_boundary(
    msh, dim=fdim,
    marker=lambda x: np.isclose(x[0], 0.0) | np.isclose(x[0], 2.0),
)
dofs = fem.locate_dofs_topological(V=V, entity_dim=fdim, entities=facets)
bc = fem.dirichletbc(value=ScalarType(0), dofs=dofs, V=V)

problem = LinearProblem(
    a, L,
    bcs=[bc],
    petsc_options_prefix="demo_poisson_",
    petsc_options={"ksp_type": "preonly", "pc_type": "lu",
                   "ksp_error_if_not_converged": True},
)
uh = problem.solve()
```

Notes for our migration: `petsc_options_prefix` is new and used by every
demo; `ksp_error_if_not_converged` is the demo default — adopt it, it is
the same honesty guard our harness wants (a direct solve that failed
must raise, not return garbage).

## Gmsh interop (`demo_gmsh.py`)

```python
from dolfinx.io import XDMFFile
from dolfinx.io import gmsh as gmshio

mesh_data = gmshio.model_to_mesh(model, comm, rank=0)

mesh_data.mesh          # the dolfinx mesh
mesh_data.cell_tags
mesh_data.facet_tags
mesh_data.ridge_tags    # 1D markers (new)
mesh_data.peak_tags     # 0D markers (new)
```

**This is the breaking change for `io/mesh.py`:** 0.7.2's
`model_to_mesh` returned a tuple; 0.11 returns a `MeshData` object, and
the import path moved from `dolfinx.io.gmshio` to
`dolfinx.io.gmsh`.

## XDMF tag output

```python
with XDMFFile(mesh_data.mesh.comm, filename, mode) as file:
    file.write_mesh(mesh_data.mesh)
    if mesh_data.facet_tags is not None:
        file.write_meshtags(
            mesh_data.facet_tags, mesh_data.mesh.geometry,
            geometry_xpath=f"/Xdmf/Domain/Grid[@Name='{name}']/Geometry",
        )
```

Tags are written individually with an explicit `geometry_xpath`. Our
mesh-cache round-trip gate (`TH-11` step 5a pattern) re-verifies tag
preservation after this port.
